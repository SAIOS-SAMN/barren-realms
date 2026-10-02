"""
Xylarium: Null space - the deep space between star systems.

Null sectors hold no starports or worlds; ships warp through them, and that is
where industry and piracy meet. Captains scan for asteroid belts, mine them into
their holds (yield depends on the hull), salvage debris fields left by destroyed
ships, and deploy sentry fighters to protect mining operations. Belts regenerate
slowly; debris disperses after DEBRIS_LIFETIME cycles.
"""

import random
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import (
    MINING_YIELD,
    MINING_YIELD_DEFAULT,
    BELT_REGEN_RATE,
    DEBRIS_CARGO_SHARE,
    DEBRIS_LIFETIME,
    HULL_SCRAP_PER_1000_CR,
    SHIP_CATALOG,
)
from xylarium.kernel import hulls
from xylarium.kernel import matter
from xylarium.kernel.models import ActionResult, ActionType, Captain, Sector
from xylarium.kernel.experience import ExperienceManager

XP_BELT_DISCOVERY = 4
XP_MINING = 1
XP_SALVAGE = 2


class NullSpaceManager:
    # ------------------------------------------------------------------ scanning
    @staticmethod
    def scan(captain: Captain, sector: Sector, kernel: Any = None) -> ActionResult:
        found = []
        for belt in sector.belts:
            if belt["id"] not in captain.scanned_belts:
                captain.scanned_belts.append(belt["id"])
                ExperienceManager.award(captain, "science", XP_BELT_DISCOVERY, kernel, key=f"belt:{belt['id']}")
            mix = ", ".join(f"{k} {int(v * 100)}%" for k, v in sorted(belt["composition"].items(), key=lambda kv: -kv[1]))
            found.append(f"{belt['id']} [{belt['type']}] reserve {belt['reserve']:,}/{belt['max_reserve']:,} ({mix})")
        debris = [f"{d['id']} (from {d.get('source', 'unknown hull')}): " + ", ".join(f"{k} {v}" for k, v in d["cargo"].items())
                  for d in sector.debris]
        hostiles = [cid for cid in sector.captains if cid != captain.id]
        lines = [f"DEEP-SPACE SCAN of Sector {sector.id:03d}:"]
        lines += [f"  Asteroid belt {b}" for b in found] or ["  No asteroid belts detected."]
        lines += [f"  Debris field {d}" for d in debris]
        if sector.sentries:
            lines.append("  Sentry picket: " + ", ".join(f"{owner} x{n}" for owner, n in sector.sentries.items()))
        if hostiles:
            lines.append(f"  Contacts: {len(hostiles)} vessel(s) in sector.")
        return ActionResult(success=True, action=ActionType.SCAN_SPACE, message="\n".join(lines), turns_spent=1,
                            data={"belts": [dict(b) for b in sector.belts], "debris": [dict(d) for d in sector.debris]})

    # ------------------------------------------------------------------ mining
    @staticmethod
    def mining_yield(captain: Captain) -> int:
        cfg = hulls.spec(captain.ship)
        if cfg.get("designer"):
            return MINING_YIELD_DEFAULT + int(cfg.get("mining", 0))       # a drawn design mines with its lasers
        return MINING_YIELD.get(captain.ship.ship_type, MINING_YIELD_DEFAULT)

    @classmethod
    def mine(cls, captain: Captain, sector: Sector, belt_id: Optional[str] = None, kernel: Any = None) -> ActionResult:
        if not sector.belts:
            return ActionResult(success=False, action=ActionType.MINE_ASTEROIDS,
                                message="No asteroid belt here: belts are what a system's disc left ungathered.")
        belts = [b for b in sector.belts if (belt_id is None or b["id"] == belt_id)]
        belts = [b for b in belts if b["id"] in captain.scanned_belts]
        if not belts:
            return ActionResult(success=False, action=ActionType.MINE_ASTEROIDS,
                                message="Scan the sector first: mining lasers need a surveyed belt (SCAN_SPACE).")
        belt = max(belts, key=lambda b: b["reserve"])
        if belt["reserve"] <= 0:
            return ActionResult(success=False, action=ActionType.MINE_ASTEROIDS,
                                message=f"Belt {belt['id']} is exhausted; it will regenerate slowly.")
        budget = min(cls.mining_yield(captain), int(belt["reserve"]))
        mined: Dict[str, int] = {}
        for elem, share in sorted(belt["composition"].items(), key=lambda kv: -kv[1]):
            want = max(1, int(round(budget * share)))
            got = captain.ship.cargo.stow(elem, min(want, budget - sum(mined.values())))
            if got:
                mined[elem] = got
            if sum(mined.values()) >= budget:
                break
        total = sum(mined.values())
        if total <= 0:
            return ActionResult(success=False, action=ActionType.MINE_ASTEROIDS,
                                message="Ore holds are full. Return to port or deliver your work order.")
        from xylarium.kernel import propulsion
        scooped = propulsion.scoop(sector, captain)            # drifting exhaust gathered with the rock
        if scooped:
            mined["H"] = mined.get("H", 0)                       # (a transfer from the sector's gas)
        belt["reserve"] -= total
        # Mining is a conversion: belt rock becomes the elements the lasers pulled out of it
        matter.sink("mined", "BELT_ROCK", total)
        for elem, q in mined.items():
            matter.source("mined", elem, q)
        from xylarium.config import COMMODITY_CONFIG
        value = sum(q * COMMODITY_CONFIG.get(e, {}).get("base_price", 10) for e, q in mined.items())
        ExperienceManager.award(captain, "industry", min(4.0, max(XP_MINING, (value / 300) ** 0.5)), kernel,
                                key=f"mine:{belt['id']}")
        return ActionResult(
            success=True, action=ActionType.MINE_ASTEROIDS, turns_spent=1,
            message=f"Mining lasers extracted {total} units from {belt['id']}: " + ", ".join(f"{k} {v}" for k, v in mined.items())
                    + f". Belt reserve {belt['reserve']:,}/{belt['max_reserve']:,}.",
            data={"mined": mined, "belt": belt["id"]},
        )

    # ------------------------------------------------------------------ debris & salvage
    @staticmethod
    def abandon_hold(sector: Optional[Sector], captain: Captain, cycle: int, reason: str = "derelict") -> None:
        """A ship that leaves the galaxy with its hold aboard (its captain dead, its commission struck) becomes a
        derelict: the whole hold drifts as a salvageable debris field in its sector (nothing is thrown away)."""
        cargo = captain.ship.cargo
        spill: Dict[str, int] = {}
        for core in ("ORE", "ORGANICS", "EQUIPMENT"):
            if getattr(cargo, core.lower()) > 0:
                spill[core] = getattr(cargo, core.lower())
        for elem, qty in cargo.elements.items():
            if qty > 0:
                spill[elem] = qty
        if getattr(captain.ship, "fuel", 0) > 0:
            spill["H"] = spill.get("H", 0) + captain.ship.fuel      # the bunker drifts with the wreck
            captain.ship.fuel = 0
        cargo.ore = cargo.organics = cargo.equipment = 0
        cargo.elements = {}
        cargo.bonded = {}
        if not spill:
            return
        if sector is None:
            for comm, q in spill.items():
                matter.sink("lost_with_ship", comm, q)
            return
        sector.debris.append({"id": f"DERELICT-{sector.id:03d}-{cycle}-{random.randint(100, 999)}", "cargo": spill,
                              "created": cycle, "source": f"{captain.name}'s {reason} {captain.ship.ship_type}"})

    @staticmethod
    def create_debris(sector: Sector, captain: Captain, cycle: int) -> Optional[Dict[str, Any]]:
        """A destroyed hull scatters part of its hold and its own scrap metal into space."""
        cargo = captain.ship.cargo
        spill: Dict[str, int] = {}
        for core in ("ORE", "ORGANICS", "EQUIPMENT"):
            units = int(getattr(cargo, core.lower()) * DEBRIS_CARGO_SHARE)
            if units > 0:
                spill[core] = units
        for elem, qty in cargo.elements.items():
            units = int(qty * DEBRIS_CARGO_SHARE)
            if units > 0:
                spill[elem] = units
        # What the explosion vaporized: the hold's share that did not survive as debris (the hull is lost next)
        for core in ("ORE", "ORGANICS", "EQUIPMENT"):
            matter.sink("vaporized", core, getattr(cargo, core.lower()) - spill.get(core, 0))
        for elem, qty in cargo.elements.items():
            matter.sink("vaporized", elem, qty - spill.get(elem, 0))
        # The drive bunker ruptures: a share drifts as gas-laden debris, the rest burns in the explosion
        fuel = getattr(captain.ship, "fuel", 0)
        if fuel > 0:
            from xylarium.kernel.propulsion import fuel_of
            fk = fuel_of(captain.ship) or "H"
            kept = int(fuel * DEBRIS_CARGO_SHARE)
            if kept:
                spill[fk] = spill.get(fk, 0) + kept
            matter.sink("vaporized", fk, fuel - kept)
            captain.ship.fuel = 0
        # The hull itself becomes scrap metal (hull mass is not in the census until it breaks apart)
        hull_value = hulls.spec(captain.ship).get("price", 0)
        scrap = max(2, int(hull_value / 1000 * HULL_SCRAP_PER_1000_CR))
        spill["Fe"] = spill.get("Fe", 0) + scrap
        spill["Ti"] = spill.get("Ti", 0) + max(1, scrap // 2)
        matter.source("hull_scrap", "Fe", scrap)
        matter.source("hull_scrap", "Ti", max(1, scrap // 2))
        field = {"id": f"DEBRIS-{sector.id:03d}-{cycle}-{random.randint(100, 999)}", "cargo": spill,
                 "created": cycle, "source": f"{captain.name}'s {captain.ship.ship_type}"}
        sector.debris.append(field)
        return field

    @staticmethod
    def salvage(captain: Captain, sector: Sector, kernel: Any = None) -> ActionResult:
        if not sector.debris:
            return ActionResult(success=False, action=ActionType.SALVAGE_DEBRIS, message="No debris field in this sector.")
        taken: Dict[str, int] = {}
        for field in list(sector.debris):
            for comm, qty in list(field["cargo"].items()):
                got = captain.ship.cargo.stow(comm, qty)
                if got:
                    taken[comm] = taken.get(comm, 0) + got
                    field["cargo"][comm] -= got
                    if field["cargo"][comm] <= 0:
                        field["cargo"].pop(comm)
            if not field["cargo"]:
                sector.debris.remove(field)
        if not taken:
            return ActionResult(success=False, action=ActionType.SALVAGE_DEBRIS, message="Holds are full; nothing salvaged.")
        ExperienceManager.award(captain, "industry", XP_SALVAGE, kernel, key=f"salvage:{sector.id}")
        return ActionResult(success=True, action=ActionType.SALVAGE_DEBRIS, turns_spent=1,
                            message="Salvage crews recovered: " + ", ".join(f"{k} {v}" for k, v in taken.items()),
                            data={"salvaged": taken})

    # ------------------------------------------------------------------ sentries
    @staticmethod
    def deploy_sentries(captain: Captain, sector: Sector, amount: int) -> ActionResult:
        amount = int(amount)
        if amount <= 0 or captain.ship.fighters < amount:
            return ActionResult(success=False, action=ActionType.DEPLOY_SENTRIES,
                                message=f"Deploy between 1 and {captain.ship.fighters} fighters.")
        captain.ship.fighters -= amount
        sector.sentries[captain.id] = sector.sentries.get(captain.id, 0) + amount
        return ActionResult(success=True, action=ActionType.DEPLOY_SENTRIES, turns_spent=1,
                            message=f"Deployed {amount} sentry fighters over Sector {sector.id:03d} "
                                    f"(picket strength {sector.sentries[captain.id]}).")

    @staticmethod
    def recall_sentries(captain: Captain, sector: Sector) -> ActionResult:
        from xylarium.config import SHIP_CATALOG as CAT
        deployed = sector.sentries.get(captain.id, 0)
        if deployed <= 0:
            return ActionResult(success=False, action=ActionType.RECALL_SENTRIES, message="You have no sentries here.")
        bay = CAT.get(captain.ship.ship_type, {}).get("max_fighters", 20)
        back = min(deployed, max(0, bay - captain.ship.fighters))
        captain.ship.fighters += back
        remaining = deployed - back
        if remaining:
            sector.sentries[captain.id] = remaining
        else:
            sector.sentries.pop(captain.id, None)
        return ActionResult(success=True, action=ActionType.RECALL_SENTRIES, turns_spent=0,
                            message=f"Recalled {back} sentries to the fighter bay ({remaining} remain on station).")

    @staticmethod
    def picket_engages_intruder(captain: Captain, sector: Sector) -> Optional[str]:
        """Sentries open fire on wanted outlaws entering the sector they guard."""
        if not sector.sentries or captain.bounty <= 0:
            return None
        pickets = sum(n for owner, n in sector.sentries.items() if owner != captain.id)
        if pickets <= 0:
            return None
        losses = min(captain.ship.fighters, max(1, pickets // 2))
        captain.ship.fighters -= losses
        shield_hit = min(captain.ship.shields, pickets * 2)
        captain.ship.shields -= shield_hit
        attrition = max(1, losses // 3)
        for owner in list(sector.sentries):
            if owner == captain.id:
                continue
            cut = min(sector.sentries[owner], attrition)
            sector.sentries[owner] -= cut
            attrition -= cut
            if sector.sentries[owner] <= 0:
                sector.sentries.pop(owner)
            if attrition <= 0:
                break
        return f">> SENTRY PICKET ENGAGED: wanted vessel took fire (-{losses} fighters, -{shield_hit} shields)."

    @staticmethod
    def borrow_sentries(sector: Sector, defender: Captain) -> int:
        """Sentries fight alongside their owner when attacked in the sector they guard."""
        return sector.sentries.get(defender.id, 0)

    @staticmethod
    def settle_sentries(sector: Sector, defender: Captain, borrowed: int, fighters_before: int) -> None:
        if borrowed <= 0:
            return
        survivors = defender.ship.fighters
        pool = fighters_before + borrowed
        surviving_ratio = survivors / pool if pool else 0
        sentries_left = int(borrowed * surviving_ratio)
        defender.ship.fighters = survivors - sentries_left
        if sentries_left > 0:
            sector.sentries[defender.id] = sentries_left
        else:
            sector.sentries.pop(defender.id, None)

    # ------------------------------------------------------------------ world tick
    @staticmethod
    def tick(kernel: Any) -> None:
        cycle = kernel.cycle_count
        for sec in kernel.sectors.values():
            for belt in sec.belts:
                if belt["reserve"] < belt["max_reserve"]:
                    grow = min(belt["max_reserve"] - belt["reserve"], max(1, int(belt["max_reserve"] * BELT_REGEN_RATE)))
                    belt["reserve"] += grow
                    matter.source("collisional_grinding", "BELT_ROCK", grow)
            if sec.debris:
                keep = []
                for d in sec.debris:
                    if cycle - d.get("created", cycle) < DEBRIS_LIFETIME and d["cargo"]:
                        keep.append(d)
                        continue
                    # A dispersing wreck drifts into the sector's belt as rock (or out of the census into the dark)
                    units = sum(d["cargo"].values())
                    for comm, q in d["cargo"].items():
                        matter.sink("debris_dispersed", comm, q)
                    if sec.belts and units:
                        sec.belts[0]["reserve"] += units
                        matter.source("debris_accreted", "BELT_ROCK", units)
                sec.debris = keep
