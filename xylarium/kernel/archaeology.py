"""
Xylarium: Archaeology - the afterlife of dead civilizations.

When a civilization dies (famine collapse) its world becomes a ruin: the population is
gone, the culture's record is buried in strata, and its treasury becomes a buried hoard
(existing money, now underground - it stays in the money supply and can only be dug up).
Genesis also seeds ancient precursor ruins on uninhabited worlds: deep, technologically
rich, and holding no spendable money (their currency died with them).

Captains SURVEY ruins, EXCAVATE stratum by stratum (tools = equipment; deeper strata are
older and richer but destabilize the site - cave-ins damage the ship and destroy finds;
shoring costs more tools), and recover:
  * TECH RELICS  - study them (destroyed in analysis) for research and possible breakthroughs,
                   or sell them to collectors;
  * ANTIQUITIES  - sell at starport curio desks (paid from the port treasury, in local money);
  * precious materials from the culture's element knowledge;
  * buried hoard money (recent collapses only), in the dead civilization's currency.

Provenance matters: digs on your own world, on sites in systems with no living sovereign, or
under a Federal Antiquities Permit are licensed. Otherwise finds are looted: Federation
collectors refuse them, and only the Anarchy black market will fence them, at a discount.
"""

import zlib
import random
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import matter
from xylarium.config import (
    ARCH_PRECURSOR_CULTURES,
    ARCH_PRECURSOR_SHARE,
    ARCH_COLLAPSE_POPULATION,
    ARCH_DIG_EQUIPMENT,
    ARCH_SHORE_EQUIPMENT,
    ARCH_PERMIT_FEE,
    ARCH_FED_COLLECTOR_PREMIUM,
    ARCH_BLACK_MARKET_DISCOUNT,
    ARCH_EXOTICISM_PER_HOP,
    ARCH_EXOTICISM_MAX,
    PRICE_LEVEL,
    XP_SCIENCE_ANOMALY,
)
from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector, SecurityLevel
from xylarium.kernel.experience import ExperienceManager

ERA_NAMES = {1: "Late Collapse", 2: "Classical", 3: "Formative", 4: "Primordial", 5: "Precursor Deep Time"}
ANTIQUITY_FORMS = ["votive figurine", "glyph tablet", "ceremonial mask", "reliquary", "star chart mosaic",
                   "burial crown", "resonance bell", "seal cylinder", "ancestor idol", "mural fragment"]
RELIC_FORMS = ["field lattice core", "navigation prism", "coherence engine", "bio-forge seed",
               "phonon memory stack", "gravitic keel shard", "cipher loom", "fusion reliquary"]


def bury(planet: Any, new: Dict[str, Any]) -> Dict[str, Any]:
    """New ruins are laid over any older ones: an older hoard stays in the ground (nothing is thrown away)."""
    old = getattr(planet, "ruins", None)
    if not old or not old.get("hoard"):
        return new
    if not new.get("hoard"):
        new["hoard"], new["hoard_currency"] = old["hoard"], old.get("hoard_currency")
    elif (old.get("hoard_currency") or "SOL") == (new.get("hoard_currency") or "SOL"):
        new["hoard"] += old["hoard"]
    else:
        from xylarium.kernel import fx
        out, _ = fx.ACTIVE_FX.convert(old.get("hoard_currency") or "SOL", new.get("hoard_currency") or "SOL", old["hoard"])
        new["hoard"] += out
    new["strata"] = list(new.get("strata", [])) + list(old.get("strata", []))
    return new


def _new_ruins(culture: str, clade: str, metabolism: str, era: str, tech_level: int, elements: List[str],
               cause: str, cycle: int, strata: int, hoard_currency: Optional[str], hoard: int,
               rng: random.Random) -> Dict[str, Any]:
    return {
        "culture": culture, "clade": clade, "metabolism": metabolism, "era": era,
        "tech_level": tech_level, "elements": list(elements), "cause": cause, "collapsed_cycle": cycle,
        "strata": [{"depth": d + 1, "richness": round(0.6 + 0.25 * d + rng.random() * 0.3, 2),
                    "finds_left": rng.randint(3, 6) + d} for d in range(strata)],
        "dug_depth": 0, "stability": 1.0, "surveyed_by": [],
        "hoard_currency": hoard_currency, "hoard": int(hoard),
    }


class ArchaeologyManager:
    # ------------------------------------------------------------------ genesis & collapse
    @staticmethod
    def seed_precursor_ruins(sectors: Dict[int, Sector], rng: random.Random) -> int:
        """Ancient precursor cultures left ruins on a share of today's uninhabited worlds."""
        placed = 0
        for sec in sectors.values():
            for p in sec.planets:
                if p.population > 0 or p.owner_id or sec.id == 1 or getattr(p, "ruins", None):
                    continue
                if rng.random() >= ARCH_PRECURSOR_SHARE:
                    continue
                culture = rng.choice(ARCH_PRECURSOR_CULTURES)
                p.ruins = _new_ruins(
                    culture["name"], culture["clade"], culture["metabolism"], "ANCIENT",
                    rng.randint(6, 9), culture["elements"], "precursor", 0, rng.randint(3, 5), None, 0, rng,
                )
                placed += 1
        return placed

    @staticmethod
    def check_collapse(planet: Planet, famine: bool, kernel: Any = None) -> Optional[str]:
        """A starving civilization that falls below the viability threshold dies; its world becomes ruins."""
        civ = getattr(planet, "civilization", None)
        if not famine or planet.population > ARCH_COLLAPSE_POPULATION:
            return None
        if civ is None:                       # a colony of no nation starves the same way: its settlers' town
            from types import SimpleNamespace
            from xylarium.kernel import biosphere
            civ = SimpleNamespace(name=f"Settlers of {planet.name}", clade="unknown", tech_level=3,
                                  metabolism=biosphere.metabolism_of(kernel, planet) if kernel is not None
                                  else "biotic", discovered_elements=[])
        rng = random.Random(zlib.crc32(f"{planet.id}:{getattr(kernel, 'cycle_count', 0)}".encode()))
        cycle = getattr(kernel, "cycle_count", 0)
        planet.ruins = bury(planet, _new_ruins(
            civ.name, getattr(civ, "clade", "unknown"), getattr(civ, "metabolism", "biotic"), "RECENT",
            int(getattr(civ, "tech_level", 3)), list(getattr(civ, "discovered_elements", [])),
            "famine", cycle, rng.randint(1, 2), planet.currency,
            planet.treasury + planet.household_purse + getattr(planet, "diaspora_escrow", 0), rng,
        ))
        # The vault, diaspora escrow and households' savings are buried with the city: same money, now underground
        planet.treasury = 0
        planet.household_purse = 0
        planet.diaspora_escrow = 0
        planet.population = 0
        planet.civilization = None
        planet.owner_id = None
        planet.faction_id = None                  # a dead world is no one's
        planet.morale = 0
        msg = (f"CIVILIZATION LOST: famine has ended the {planet.ruins['culture']} on {planet.name}. "
               f"Its cities are silent; archaeologists may now survey the ruins.")
        if kernel is not None:
            from xylarium.kernel import history
            history.event(kernel, "EXTINCTION", f"The {civ.name} of {planet.name} are gone", actors=[f"civ:{civ.name}"],
                          planet=planet, cause="famine below the last viable number", text=msg)
        if kernel is not None and getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(sender="XENO-ARCHIVE", text=msg, channel="COMM-1", sector_id=planet.sector_id)
        return msg

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _ruin_here(captain: Captain, sector: Sector, planet_id: Optional[str]) -> Optional[Planet]:
        sites = [p for p in sector.planets if getattr(p, "ruins", None)]
        if planet_id:
            sites = [p for p in sites if p.id == planet_id or p.name == planet_id]
        # Untargeted: prefer sites this captain may actually dig (abandoned or their own), with strata left
        sites.sort(key=lambda p: (
            not (p.owner_id in (None, captain.id) and (p.population == 0 or p.owner_id == captain.id)),
            p.ruins["dug_depth"] >= len(p.ruins["strata"]),
        ))
        return sites[0] if sites else None

    @staticmethod
    def provenance(captain: Captain, planet: Planet, sector: Sector) -> str:
        if planet.owner_id == captain.id:
            return "licensed"
        if "FED_ANTIQUITIES" in getattr(captain, "permits", []):
            return "licensed"
        living_sovereign = any(
            (p.owner_id and p.owner_id != captain.id) or (p.population > 0 and getattr(p, "civilization", None))
            for p in sector.planets if p.id != planet.id
        )
        return "unlicensed" if (living_sovereign or sector.security == SecurityLevel.FEDERATION) else "licensed"

    @staticmethod
    def appraisal(artifact: Dict[str, Any]) -> int:
        """Base value in SOL: age (depth), culture sophistication, condition, and kind."""
        base = 180 if artifact["kind"] == "ANTIQUITY" else 320
        age = 1.0 + 0.45 * (artifact["stratum"] - 1) + (0.6 if artifact["era"] == "ANCIENT" else 0.0)
        return int(base * age * (0.6 + 0.08 * artifact["tech_level"]) * artifact["condition"])

    # ------------------------------------------------------------------ actions
    @classmethod
    def survey(cls, captain: Captain, sector: Sector, planet_id: Optional[str], kernel: Any = None) -> ActionResult:
        planet = cls._ruin_here(captain, sector, planet_id)
        if planet is None:
            return ActionResult(success=False, action=ActionType.SURVEY_RUINS, message="No ruins in this system.")
        r = planet.ruins
        if captain.id not in r["surveyed_by"]:
            r["surveyed_by"].append(captain.id)
            ExperienceManager.award(captain, "science", 6, kernel, key=f"survey:{planet.id}")
        left = sum(s["finds_left"] for s in r["strata"][r["dug_depth"]:])
        hoard = (f" Ground-penetrating scans suggest a buried treasury ({r['hoard_currency']})." if r["hoard"] > 0 else "")
        msg = (f"RUINS SURVEY - {planet.name}: {r['culture']} ({r['era'].lower()} {r['clade']} culture, tech level "
               f"{r['tech_level']}, lost to {r['cause']}). Strata {r['dug_depth'] + 1}-{len(r['strata'])} open, ~{left} finds "
               f"remain. Site stability {r['stability']:.0%}. Provenance: {cls.provenance(captain, planet, sector)}.{hoard}")
        return ActionResult(success=True, action=ActionType.SURVEY_RUINS, message=msg, turns_spent=1,
                            data={"planet_id": planet.id, "ruins": dict(r)})

    @classmethod
    def excavate(cls, captain: Captain, sector: Sector, planet_id: Optional[str], shore: bool = False,
                 kernel: Any = None) -> ActionResult:
        planet = cls._ruin_here(captain, sector, planet_id)
        if planet is None:
            return ActionResult(success=False, action=ActionType.EXCAVATE, message="No ruins in this system.")
        if planet.owner_id and planet.owner_id != captain.id:
            return ActionResult(success=False, action=ActionType.EXCAVATE,
                                message=f"{planet.name} is sovereign territory: its owner has not licensed your dig.")
        if planet.population > 0 and planet.owner_id != captain.id:
            people = getattr(getattr(planet, "civilization", None), "name", "the inhabitants")
            return ActionResult(success=False, action=ActionType.EXCAVATE,
                                message=f"The ruins lie beneath living cities: {people} forbid excavation of their ancestral ground.")
        r = planet.ruins
        if captain.id not in r["surveyed_by"]:
            return ActionResult(success=False, action=ActionType.EXCAVATE, message="Survey the ruins before breaking ground.")
        if r["dug_depth"] >= len(r["strata"]):
            return ActionResult(success=False, action=ActionType.EXCAVATE, message="The site is exhausted to bedrock.")
        tools = ARCH_DIG_EQUIPMENT + (ARCH_SHORE_EQUIPMENT if shore else 0)
        if captain.ship.cargo.unbonded("EQUIPMENT") < tools:
            return ActionResult(success=False, action=ActionType.EXCAVATE,
                                message=f"Excavation needs {tools} Equipment (tools{' and shoring' if shore else ''}) in your hold.")
        captain.ship.cargo.equipment -= tools
        matter.sink("excavation_tools", "EQUIPMENT", tools)       # worn out and left in the trench
        if shore:
            r["stability"] = min(1.0, r["stability"] + 0.35)

        rng = random.Random(random.getrandbits(32))   # drawn from the seeded stream: reproducible
        stratum = r["strata"][r["dug_depth"]]
        logs: List[str] = []
        # Cave-in risk grows as the site destabilizes
        if rng.random() > r["stability"]:
            lost = min(stratum["finds_left"], rng.randint(1, 2))
            stratum["finds_left"] -= lost
            damage = min(captain.ship.shields, 20)
            captain.ship.shields -= damage
            r["stability"] = min(1.0, r["stability"] + 0.15)  # the collapse settles the pit
            msg = (f"CAVE-IN at {planet.name}! Stratum {stratum['depth']} slumped: {lost} find(s) crushed, "
                   f"landing gear damaged (-{damage} shields). Shore the pit before going deeper.")
            if stratum["finds_left"] <= 0:
                r["dug_depth"] += 1
            return ActionResult(success=True, action=ActionType.EXCAVATE, message=msg, turns_spent=1, data={"cave_in": True})

        r["stability"] = max(0.3, r["stability"] - (0.04 + 0.03 * stratum["depth"]))
        prov = cls.provenance(captain, planet, sector)
        finds: List[Dict[str, Any]] = []
        n = 1 + (1 if rng.random() < stratum["richness"] - 0.5 else 0)
        for _ in range(min(n, stratum["finds_left"])):
            stratum["finds_left"] -= 1
            relic_chance = 0.15 + 0.07 * r["tech_level"] + 0.05 * stratum["depth"]
            kind = "TECH_RELIC" if rng.random() < relic_chance else "ANTIQUITY"
            form = rng.choice(RELIC_FORMS if kind == "TECH_RELIC" else ANTIQUITY_FORMS)
            artifact = {
                "id": f"ART-{planet.id}-{stratum['depth']}-{rng.randint(1000, 9999)}",
                "name": f"{r['culture']} {form}",
                "kind": kind, "culture": r["culture"], "era": r["era"], "stratum": stratum["depth"],
                "era_name": ERA_NAMES.get(stratum["depth"] + (2 if r["era"] == "ANCIENT" else 0), "Deep Time"),
                "tech_level": r["tech_level"], "condition": round(rng.uniform(0.35, 1.0), 2),
                "provenance": prov, "origin_sector": planet.sector_id,
                "elements": list(r["elements"]),
            }
            artifact["appraisal_sol"] = cls.appraisal(artifact)
            captain.artifacts.append(artifact)
            finds.append(artifact)
        # Precious materials from the culture's element knowledge
        if r["elements"] and rng.random() < 0.6:
            elem = rng.choice(r["elements"])
            got = captain.ship.cargo.stow(elem, rng.randint(2, 6) * stratum["depth"])
            matter.source("excavation", elem, got)                 # a dead city's stores, out of the ground
            if got:
                logs.append(f"{got} {elem}")
        # Buried hoard: the dead city's treasury, recovered a cache at a time (a transfer, not new money)
        if r["hoard"] > 0 and r["era"] == "RECENT":
            cache = min(r["hoard"], max(1, int(r["hoard"] * rng.uniform(0.15, 0.4))))
            r["hoard"] -= cache
            from xylarium.kernel.fx import credit
            credit(captain, r["hoard_currency"], cache)
            logs.append(f"buried treasury cache {cache:,} {r['hoard_currency']}")
        if stratum["finds_left"] <= 0:
            r["dug_depth"] += 1
            logs.append(f"stratum {stratum['depth']} exhausted")
        ExperienceManager.award(captain, "science", 3 + stratum["depth"], kernel, key=f"dig:{planet.id}")

        found = ", ".join(f"{a['name']} [{a['kind'].replace('_', ' ').lower()}, {a['condition']:.0%}]" for a in finds) or "no artifacts"
        extra = ("; " + "; ".join(logs)) if logs else ""
        loot = " (UNLICENSED - looted provenance)" if prov == "unlicensed" and finds else ""
        return ActionResult(
            success=True, action=ActionType.EXCAVATE, turns_spent=1,
            message=f"EXCAVATION {planet.name} stratum {stratum['depth']}: {found}{extra}{loot}. "
                    f"Site stability {r['stability']:.0%}.",
            data={"finds": finds},
        )

    @classmethod
    def offer(cls, artifact: Dict[str, Any], sector: Sector, kernel: Any) -> Tuple[int, Optional[str]]:
        """Local-currency price a starport's curio desk will pay, or a refusal reason."""
        port = sector.port
        if port is None:
            return 0, "No curio desk here: sell antiquities at a starport."
        zone = sector.security
        if artifact["provenance"] == "unlicensed" and zone != SecurityLevel.ANARCHY:
            return 0, "Collectors here require provenance. Looted pieces only move through Anarchy black markets."
        mult = 1.0
        if zone == SecurityLevel.FEDERATION:
            mult = ARCH_FED_COLLECTOR_PREMIUM
        elif zone == SecurityLevel.ANARCHY and artifact["provenance"] == "unlicensed":
            mult = ARCH_BLACK_MARKET_DISCOUNT
        hops = 0
        if kernel is not None and artifact.get("origin_sector") in kernel.sectors:
            path = kernel.find_path(artifact["origin_sector"], sector.id)
            hops = max(0, len(path) - 1) if path else 0
        mult *= 1.0 + min(ARCH_EXOTICISM_MAX, ARCH_EXOTICISM_PER_HOP * hops)
        from xylarium.kernel.fx import ACTIVE_FX
        level = PRICE_LEVEL.get(port.currency, 1.0)
        if ACTIVE_FX is not None and port.currency != "SOL":
            level = ACTIVE_FX.rate(port.currency)
        return int(artifact["appraisal_sol"] * mult * level), None

    @classmethod
    def sell(cls, captain: Captain, sector: Sector, artifact_id: Optional[str], kernel: Any = None) -> ActionResult:
        pool = [a for a in captain.artifacts if artifact_id in (None, "ALL", a["id"])]
        if artifact_id is None or artifact_id == "ALL":
            pool = [a for a in pool if a["kind"] == "ANTIQUITY"] or pool
        if not pool:
            return ActionResult(success=False, action=ActionType.SELL_ARTIFACT, message="No such artifact in your collection.")
        port = sector.port
        sold, refused, total = [], [], 0
        from xylarium.kernel.fx import credit
        for art in list(pool):
            price, reason = cls.offer(art, sector, kernel)
            if reason:
                refused.append(reason)
                continue
            if port.treasury < price:
                refused.append(f"{port.name}'s curio desk cannot afford {art['name']} today.")
                continue
            port.treasury -= price
            credit(captain, port.currency, price)
            captain.artifacts.remove(art)
            ExperienceManager.record_revenue(captain, int(art["appraisal_sol"]), kernel)
            sold.append(f"{art['name']} ({price:,} {port.currency})")
            total += price
        if not sold:
            return ActionResult(success=False, action=ActionType.SELL_ARTIFACT, message=refused[0] if refused else "Nothing sold.")
        return ActionResult(success=True, action=ActionType.SELL_ARTIFACT, turns_spent=0,
                            message=f"CURIO DESK: sold {', '.join(sold)} for {total:,} {port.currency}.",
                            data={"total": total, "currency": port.currency})

    @classmethod
    def study(cls, captain: Captain, artifact_id: Optional[str], kernel: Any = None) -> ActionResult:
        relics = [a for a in captain.artifacts if a["kind"] == "TECH_RELIC" and artifact_id in (None, a["id"])]
        if not relics:
            return ActionResult(success=False, action=ActionType.STUDY_ARTIFACT, message="No tech relic to study.")
        relic = max(relics, key=lambda a: a["tech_level"] * a["condition"])
        captain.artifacts.remove(relic)
        points = int((6 + 3 * relic["tech_level"] + 4 * relic["stratum"]) * relic["condition"])
        msg_extra = ""
        if kernel is not None:
            # a relic is someone else's materials science, read back out of the metal
            from xylarium.config import RESEARCH_POINTS_PER_UNIT
            from xylarium.kernel import fertility, knowledge
            units = points / RESEARCH_POINTS_PER_UNIT
            knowledge.learn(kernel, knowledge.holder_of_captain(captain), "materials", units, "relics")
            fertility.discovered(kernel, captain=captain)
            msg_extra = f" {units:.1f} units of materials knowledge recovered."
            from xylarium.kernel import crystal, intellect       # and the crystal its makers last wrote
            got = intellect.relic_crystal(kernel, knowledge.holder_of_captain(captain), relic.get("id", ""))
            if got is not None:
                msg_extra += f" Its makers' {crystal.NAMES.get(got, got)} crystal is yours."
        for elem in relic.get("elements", [])[:1]:
            msg_extra += f" Metallurgical notes on {elem} recovered."
        ExperienceManager.award(captain, "science", XP_SCIENCE_ANOMALY, kernel, key=f"relic:{relic['culture']}")
        return ActionResult(success=True, action=ActionType.STUDY_ARTIFACT, turns_spent=1,
                            message=f"RELIC ANALYSIS: {relic['name']} (tech level {relic['tech_level']}) disassembled for study: "
                                    f"+{points} research.{msg_extra}",
                            data={"research_points": points})

    @staticmethod
    def buy_permit(captain: Captain, sector: Sector, kernel: Any) -> ActionResult:
        if sector.id != 1:
            return ActionResult(success=False, action=ActionType.BANK_TRANSACTION,
                                message="Federal Antiquities Permits are issued at Sol Central.")
        if "FED_ANTIQUITIES" in captain.permits:
            return ActionResult(success=False, action=ActionType.BANK_TRANSACTION, message="You already hold a permit.")
        if captain.credits < ARCH_PERMIT_FEE:
            return ActionResult(success=False, action=ActionType.BANK_TRANSACTION,
                                message=f"A Federal Antiquities Permit costs {ARCH_PERMIT_FEE:,} SOL.")
        captain.credits -= ARCH_PERMIT_FEE
        kernel.federal_reserve.receive(ARCH_PERMIT_FEE, "antiquities_permits")
        captain.permits.append("FED_ANTIQUITIES")
        return ActionResult(success=True, action=ActionType.BANK_TRANSACTION,
                            message=f"Federal Antiquities Permit issued ({ARCH_PERMIT_FEE:,} SOL): your digs now carry provenance.")
