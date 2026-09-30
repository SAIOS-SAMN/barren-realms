"""
Tactical combat engine for Xylarium.
Handles ship-to-ship tactical engagements and planetary orbital sieges (BRE/SRE style).
"""

import random
from typing import Dict, Any, List, Optional
from xylarium.kernel import matter
from xylarium.kernel.models import (
    Captain,
    Sector,
    Planet,
    SecurityLevel,
    ActionResult,
    ActionType,
    Ship,
    CargoHold,
)
from xylarium.config import (
    SHIP_CATALOG,
    RESPAWN_KIT,
    XP_COMBAT_BASE,
    HOSTILE_ACT_BOUNTY,
    HOSTILE_ACT_REP_PENALTY,
)
from xylarium.kernel.experience import ExperienceManager


def _starter_cargo(captain: Captain) -> CargoHold:
    cargo = CargoHold(capacity=RESPAWN_KIT["holds"])
    metab = getattr(captain, "metabolism", "biotic")
    if metab == "mineral":
        cargo.ore = 5
        cargo.elements["Si"] = 2
    elif metab == "plasmic":
        cargo.elements["H"] = 5
        cargo.elements["He-3"] = 2
    else:
        cargo.organics = 5
        cargo.elements["H2O"] = 3
    return cargo


def _eject_to_sol(captain: Captain, kernel: Optional[Any], credit_loss_frac: float = 0.0) -> int:
    """
    Hull loss: the escape pod reaches Sol Central, where the captain is issued a
    Scout escape craft with the respawn kit and starter rations. Sector rosters stay
    consistent, bonded freight is forfeited with the lost hold, a share of liquid
    credits is lost, and an insured hull pays its claim from the Federal Reserve.
    No cash floors: recovery money comes from insurance, not from minting.
    Returns the insurance payout.
    """
    old_sec = captain.sector_id
    # Bonded freight is settled first (the issuer's goods are repossessed); then what remains of the hold
    # breaks up with the hull
    if kernel is not None and hasattr(kernel, "market_manager"):
        kernel.market_manager.forfeit_freight(captain, kernel)
    if kernel is not None and getattr(captain, "charter", None):
        from xylarium.kernel import tourism
        tourism.intercept(kernel, None, captain)          # lost with the hull: the escrow is refunded
    if kernel is not None and old_sec in kernel.sectors:
        from xylarium.kernel.nullspace import NullSpaceManager
        NullSpaceManager.create_debris(kernel.sectors[old_sec], captain, kernel.cycle_count)
    else:
        cg = captain.ship.cargo
        for comm, q in (("ORE", cg.ore), ("ORGANICS", cg.organics), ("EQUIPMENT", cg.equipment), *cg.elements.items()):
            matter.sink("vaporized", comm, q)
    captain.sector_id = 1
    if kernel is not None:
        if old_sec in kernel.sectors and captain.id in kernel.sectors[old_sec].captains:
            kernel.sectors[old_sec].captains.remove(captain.id)
        if 1 in kernel.sectors and captain.id not in kernel.sectors[1].captains:
            kernel.sectors[1].captains.append(captain.id)

    scout = SHIP_CATALOG.get("Scout Ship", {})
    captain.ship.ship_type = "Scout Ship"
    if captain.ship.fuel:
        from xylarium.kernel.propulsion import fuel_of
        matter.sink("vaporized", fuel_of(captain.ship) or "H", captain.ship.fuel)
        captain.ship.fuel = 0
    captain.ship.drive, captain.ship.core_wear = "H", 0        # the escape craft has only a torch
    captain.ship.max_shields = scout.get("max_shields", 100)
    captain.ship.shields = RESPAWN_KIT["shields"]
    captain.ship.fighters = RESPAWN_KIT["fighters"]
    captain.ship.cargo = _starter_cargo(captain)     # the old hold went to the debris field
    matter.commission(captain, "respawn_kit")
    if credit_loss_frac > 0:
        lost = int(max(0, captain.credits) * credit_loss_frac)
        captain.credits -= lost
        # The wreck's strongbox is recovered by the Federal salvage service (nothing is thrown away)
        from xylarium.kernel import ledger
        ledger.pay_service(lost, institution="wreck_salvage")

    fed = getattr(kernel, "federal_reserve", None) if kernel is not None else None
    payout = fed.pay_hull_claim(captain, kernel.cycle_count) if fed else 0
    if kernel is not None:
        from xylarium.kernel import lineage
        note = lineage.on_hull_loss(kernel, captain)
        if captain.is_ai and not captain.faction_id:
            note = lineage.npc_hull_loss(kernel, captain) or note
        if note and getattr(kernel, "event_bus", None):
            kernel.action_logs.append(note)
            kernel.event_bus.broadcast_radio(sender="SOL-CLONE-VATS", text=note, channel="SYSTEM", sector_id=1)
    return payout


def _award_victory(victor: Captain, victor_power: float, loser_power: float, loser_id: str, kernel: Optional[Any]) -> None:
    """Combat Xi scales with the opponent's strength; farming much weaker targets earns ~nothing."""
    ratio = max(0.0, min(2.0, loser_power / max(1.0, victor_power)))
    ExperienceManager.award(victor, "combat", XP_COMBAT_BASE * ratio, kernel, key=f"kill:{loser_id}")


class CombatManager:
    """Resolves ship-to-ship battles and planetary assaults."""

    @classmethod
    def resolve_ship_battle(
        cls,
        attacker: Captain,
        defender: Captain,
        sector: Sector,
        fighters_to_commit: Optional[int] = None,
        tactic: str = "volley",
        bribe_amount: Optional[int] = None,
        escape_sector: Optional[int] = None,
        kernel: Optional[Any] = None,
    ) -> ActionResult:
        """
        Rules of engagement around the firefight itself:
          * Null space between systems is open space - fights there are lawful.
          * Opening fire inside a star system with a starport or inhabited world on a
            captain who is not a wanted outlaw is a hostile act: a Federal warrant is
            issued and Federation/Corporate standing drops.
          * A defender's sentry picket in the sector joins the defence and shares losses.
        """
        from xylarium.kernel.nullspace import NullSpaceManager
        hostile_act = (
            tactic not in ("bribe", "surrender")
            and sector.security != SecurityLevel.FEDERATION
            and sector.is_protected_space
            and defender.bounty <= 0
        )
        borrowed = NullSpaceManager.borrow_sentries(sector, defender)
        fighters_before = defender.ship.fighters
        defender.ship.fighters += borrowed
        try:
            res = cls._resolve_core(attacker, defender, sector, fighters_to_commit, tactic,
                                    bribe_amount, escape_sector, kernel)
        finally:
            if borrowed:
                if defender.sector_id == sector.id:
                    NullSpaceManager.settle_sentries(sector, defender, borrowed, fighters_before)
                else:
                    sector.sentries.pop(defender.id, None)  # picket annihilated with the hull
        if res.success and hostile_act:
            attacker.bounty += HOSTILE_ACT_BOUNTY
            attacker.bounty_placed_by = "Federal Prosecutor"
            attacker.adjust_reputation("Federation", -HOSTILE_ACT_REP_PENALTY)
            attacker.adjust_reputation("Corporate", -HOSTILE_ACT_REP_PENALTY / 2)
            warrant = (f"[HOSTILE ACT] {attacker.name} opened fire inside the {sector.name} system: "
                       f"Federal warrant +{HOSTILE_ACT_BOUNTY:,} Cr issued.")
            res.logs = (res.logs or []) + [warrant]
            if kernel is not None and getattr(kernel, "event_bus", None):
                kernel.event_bus.broadcast_radio(sender="FED-PROSECUTOR", text=warrant, channel="ALERT", sector_id=sector.id)
        return res

    @classmethod
    def _resolve_core(
        cls,
        attacker: Captain,
        defender: Captain,
        sector: Sector,
        fighters_to_commit: Optional[int] = None,
        tactic: str = "volley",
        bribe_amount: Optional[int] = None,
        escape_sector: Optional[int] = None,
        kernel: Optional[Any] = None,
    ) -> ActionResult:
        """
        Executes a tactical combat round between two captains in the same sector.
        Supports tactics:
          - 'volley': Standard firefight exchange
          - 'evade' / 'flee': Attempt emergency warp escape to adjacent sector
          - 'bribe' / 'surrender': Offer credit tribute to negotiate immediate truce
        """
        logs: List[str] = []
        att_power0 = attacker.ship.fighters + attacker.ship.shields / 10.0
        def_power0 = defender.ship.fighters + defender.ship.shields / 10.0

        # 1. Check Federation Law
        if sector.security == SecurityLevel.FEDERATION:
            msg = (
                f"[FEDNAV ALERT] Unauthorized weapons discharge detected in Sector {sector.id}! "
                f"Federal patrol cruisers lock tractor beams and disrupt combat."
            )
            return ActionResult(
                success=False,
                action=ActionType.ATTACK_SHIP,
                message=msg,
                turns_spent=0,
                logs=[msg]
            )

        if attacker.sector_id != defender.sector_id:
            return ActionResult(
                success=False,
                action=ActionType.ATTACK_SHIP,
                message="Target is not in the same sector.",
            )

        # 2. Handle Truce / Bribe Tactic
        tactic_norm = (tactic or "volley").lower().strip()
        if tactic_norm in ["bribe", "surrender"]:
            tribute = bribe_amount if bribe_amount is not None else max(150, int(attacker.credits * 0.25))
            if attacker.credits < tribute:
                return ActionResult(
                    success=False,
                    action=ActionType.ATTACK_SHIP,
                    message=f"Insufficient funds! Truce requires {tribute:,} Cr, but you only have {attacker.credits:,} Cr.",
                )
            if tribute < 100:
                return ActionResult(
                    success=False,
                    action=ActionType.ATTACK_SHIP,
                    message="Truce offer rejected: Minimum tribute is 100 Credits.",
                )

            attacker.credits -= tribute
            defender.credits += tribute
            logs.append(f"COMMUNICATIONS LINK: {attacker.name} transmits emergency truce signal to {defender.name}.")
            logs.append(f">> Transferred {tribute:,} Credits tribute to {defender.name}'s account.")
            logs.append(f">> {defender.name}: 'A wise captain knows when to buy their life. Stand down weapons.'")
            logs.append(f"Hostilities ceased. Both ships disengage.")
            return ActionResult(
                success=True,
                action=ActionType.ATTACK_SHIP,
                message=f"Truce negotiated with {defender.name} for {tribute:,} Credits.",
                turns_spent=1,
                logs=logs,
                data={"bribe_paid": tribute}
            )

        # 3. Handle Evasive Warp Escape Tactic
        if tactic_norm in ["evade", "flee"]:
            candidates = [w for w in sector.warps if w != sector.id]
            if not candidates:
                return ActionResult(
                    success=False,
                    action=ActionType.ATTACK_SHIP,
                    message="No viable wormhole lanes available for warp escape in this sector!",
                )

            escape_dest = escape_sector if (escape_sector in candidates) else random.choice(candidates)
            escape_chance = 0.75 + (0.15 if attacker.ship.shields > 50 else 0.0)

            if random.random() <= escape_chance:
                # Successful escape
                if kernel:
                    if attacker.id in sector.captains:
                        sector.captains.remove(attacker.id)
                    attacker.sector_id = escape_dest
                    dest_sec = kernel.sectors.get(escape_dest)
                    if dest_sec and attacker.id not in dest_sec.captains:
                        dest_sec.captains.append(attacker.id)

                logs.append(f"TACTICAL ENGAGEMENT: {attacker.name} engages emergency warp drive to evade {defender.name}!")
                logs.append(f">> Sub-light thrusters overclocked! Wormhole jump to Sector {escape_dest:03d} successful!")
                return ActionResult(
                    success=True,
                    action=ActionType.ATTACK_SHIP,
                    message=f"Emergency warp escape successful! Jumped to Sector {escape_dest:03d}.",
                    turns_spent=1,
                    logs=logs,
                    data={"evaded": True, "dest_sector": escape_dest}
                )
            else:
                # Failed escape: Defender gets free volley
                logs.append(f"TACTICAL ENGAGEMENT: {attacker.name} attempts emergency warp escape from {defender.name}!")
                logs.append(f">> Drive core stalled! Evasive maneuver FAILED!")
                def_power = int(defender.ship.fighters * random.uniform(8.0, 14.0)) + random.randint(10, 25)

                if attacker.ship.shields > 0:
                    if def_power <= attacker.ship.shields:
                        attacker.ship.shields -= def_power
                        logs.append(f"<< Return fire hits {attacker.name}'s shields for {def_power} MW (Remaining: {attacker.ship.shields}).")
                    else:
                        overflow = def_power - attacker.ship.shields
                        logs.append(f"<< Return fire CRIPPLED {attacker.name}'s shields! {overflow} damage penetrated!")
                        attacker.ship.shields = 0
                        att_lost = min(attacker.ship.fighters, max(1, overflow // 20))
                        attacker.ship.fighters -= att_lost
                        logs.append(f"<< {attacker.name} lost {att_lost} fighters in the counter-strike.")
                else:
                    att_lost = min(attacker.ship.fighters, max(1, def_power // 20))
                    attacker.ship.fighters -= att_lost
                    logs.append(f"<< Return fire incinerated {att_lost} of {attacker.name}'s fighters.")

                attacker_destroyed = (attacker.ship.shields <= 0 and attacker.ship.fighters <= 0)
                if attacker_destroyed:
                    logs.append(f"*** YOUR SHIP WAS DESTROYED! Emergency escape pod ejected towards Sol Federation Central. ***")
                    _eject_to_sol(attacker, kernel, credit_loss_frac=0.5)
                    _award_victory(defender, def_power0, att_power0, attacker.id, kernel)
                    return ActionResult(
                        success=True,
                        action=ActionType.ATTACK_SHIP,
                        message=f"Catastrophic defeat during retreat! Your ship was destroyed by {defender.name}.",
                        turns_spent=1,
                        data={"evaded": False, "attacker_destroyed": True},
                        logs=logs
                    )

                return ActionResult(
                    success=True,
                    action=ActionType.ATTACK_SHIP,
                    message=f"Evasive escape failed! Suffered {def_power} MW return fire from {defender.name}.",
                    turns_spent=1,
                    data={"evaded": False, "attacker_destroyed": False},
                    logs=logs
                )

        # 4. Standard Volley Firefight
        att_fighters = attacker.ship.fighters if fighters_to_commit is None else min(attacker.ship.fighters, fighters_to_commit)
        if att_fighters <= 0 and attacker.ship.shields <= 0:
            return ActionResult(
                success=False,
                action=ActionType.ATTACK_SHIP,
                message="Your ship has no fighters or shields operational to engage!",
            )

        def_fighters = defender.ship.fighters

        logs.append(f"TACTICAL ENGAGEMENT: {attacker.name} opens fire on {defender.name} in Sector {sector.id}!")
        logs.append(f">> Attacker: {attacker.ship.ship_type} | Shields: {attacker.ship.shields} | Fighters: {att_fighters}")
        logs.append(f">> Defender: {defender.ship.ship_type} | Shields: {defender.ship.shields} | Fighters: {def_fighters}")

        # Damage calculation
        # Each fighter deals ~8-14 damage
        att_power = int(att_fighters * random.uniform(8.0, 14.0)) + random.randint(15, 35)
        def_power = int(def_fighters * random.uniform(8.0, 14.0)) + random.randint(10, 25)
        # Heavy broadside batteries (Gothic Battle-Cruisers, Fanatic Boarding Vessels)
        att_power = int(att_power * SHIP_CATALOG.get(attacker.ship.ship_type, {}).get("broadside", 1.0))
        def_power = int(def_power * SHIP_CATALOG.get(defender.ship.ship_type, {}).get("broadside", 1.0))

        # 1. Attacker damages Defender
        if defender.ship.shields > 0:
            if att_power <= defender.ship.shields:
                defender.ship.shields -= att_power
                logs.append(f">> {defender.name}'s shields absorb {att_power} MW of blaster fire (Remaining: {defender.ship.shields}).")
            else:
                overflow = att_power - defender.ship.shields
                logs.append(f">> {defender.name}'s SHIELDS COLLAPSED! {overflow} overflow damage breaches the hull!")
                defender.ship.shields = 0
                fighters_lost = min(defender.ship.fighters, max(1, overflow // 20))
                defender.ship.fighters -= fighters_lost
                logs.append(f">> {defender.name} lost {fighters_lost} fighters in the blast wave.")
        else:
            fighters_lost = min(defender.ship.fighters, max(1, att_power // 20))
            defender.ship.fighters -= fighters_lost
            logs.append(f">> Direct hit on {defender.name}! Lost {fighters_lost} fighters.")

        # 2. Defender counter-attacks Attacker
        if attacker.ship.shields > 0:
            if def_power <= attacker.ship.shields:
                attacker.ship.shields -= def_power
                logs.append(f"<< Return fire hits {attacker.name}'s shields for {def_power} MW (Remaining: {attacker.ship.shields}).")
            else:
                overflow = def_power - attacker.ship.shields
                logs.append(f"<< Return fire CRIPPLED {attacker.name}'s shields! {overflow} damage penetrated!")
                attacker.ship.shields = 0
                att_lost = min(attacker.ship.fighters, max(1, overflow // 20))
                attacker.ship.fighters -= att_lost
                logs.append(f"<< {attacker.name} lost {att_lost} fighters in the counter-strike.")
        else:
            att_lost = min(attacker.ship.fighters, max(1, def_power // 20))
            attacker.ship.fighters -= att_lost
            logs.append(f"<< Return fire incinerated {att_lost} of {attacker.name}'s fighters.")

        # 3. Check for destruction
        defender_destroyed = (defender.ship.shields <= 0 and defender.ship.fighters <= 0)
        attacker_destroyed = (attacker.ship.shields <= 0 and attacker.ship.fighters <= 0)

        data = {
            "att_shields": attacker.ship.shields,
            "att_fighters": attacker.ship.fighters,
            "def_shields": defender.ship.shields,
            "def_fighters": defender.ship.fighters,
            "defender_destroyed": defender_destroyed,
            "attacker_destroyed": attacker_destroyed,
        }

        if defender_destroyed:
            bounty_cr = defender.credits // 2
            defender.credits -= bounty_cr
            attacker.credits += bounty_cr
            attacker.score += 500

            # Salvage cargo
            salvage_ore = defender.ship.cargo.ore // 2
            salvage_org = defender.ship.cargo.organics // 2
            salvage_eq = defender.ship.cargo.equipment // 2

            # The victor hauls it out of the wreck (the rest drifts into the debris field when the hull is lost)
            space = attacker.ship.cargo.available_space
            take_ore = min(space, salvage_ore)
            attacker.ship.cargo.ore += take_ore
            defender.ship.cargo.ore -= take_ore
            space = attacker.ship.cargo.available_space
            take_org = min(space, salvage_org)
            attacker.ship.cargo.organics += take_org
            defender.ship.cargo.organics -= take_org
            space = attacker.ship.cargo.available_space
            take_eq = min(space, salvage_eq)
            attacker.ship.cargo.equipment += take_eq
            defender.ship.cargo.equipment -= take_eq

            logs.append(f"*** ENEMY DESTROYED! {defender.name}'s ship breaks apart into stardust! ***")
            logs.append(f"*** Plundered {bounty_cr:,} Credits and salvaged cargo from the wreckage! ***")

            # VIPs aboard a lost liner are held for ransom by the victor
            if kernel is not None and getattr(defender, "charter", None):
                from xylarium.kernel import tourism
                note = tourism.intercept(kernel, attacker, defender)
                if note:
                    logs.append(note)
            # Respawn defender at Fed Central in escape pod / scout
            _eject_to_sol(defender, kernel)
            _award_victory(attacker, att_power0, def_power0, defender.id, kernel)

            return ActionResult(
                success=True,
                action=ActionType.ATTACK_SHIP,
                message=f"Victory! Destroyed {defender.name} and pillaged {bounty_cr:,} Credits!",
                turns_spent=2,
                data=data,
                logs=logs
            )

        if attacker_destroyed:
            logs.append(f"*** YOUR SHIP WAS DESTROYED! Emergency escape pod ejected towards Sol Federation Central. ***")
            _eject_to_sol(attacker, kernel, credit_loss_frac=0.5)
            _award_victory(defender, def_power0, att_power0, attacker.id, kernel)

            return ActionResult(
                success=True,
                action=ActionType.ATTACK_SHIP,
                message=f"Catastrophic defeat! Your ship was destroyed by {defender.name}.",
                turns_spent=2,
                data=data,
                logs=logs
            )

        logs.append(f"Combat round completed. Both captains disengage to assess damage.")
        return ActionResult(
            success=True,
            action=ActionType.ATTACK_SHIP,
            message=f"Engaged {defender.name}. Enemy Shields: {defender.ship.shields}, Fighters: {defender.ship.fighters}.",
            turns_spent=2,
            data=data,
            logs=logs
        )

    @classmethod
    def attack_planet(
        cls,
        attacker: Captain,
        planet: Planet,
        sector: Sector,
        kernel: Optional[Any] = None,
    ) -> ActionResult:
        """
        Orbital bombardment and planetary assault on a colonized planet.
        """
        logs: List[str] = []

        if sector.security == SecurityLevel.FEDERATION:
            msg = "[FEDNAV] Orbital bombardment is strictly prohibited in Federation Sectors!"
            return ActionResult(
                success=False,
                action=ActionType.ATTACK_PLANET,
                message=msg,
                turns_spent=0,
                logs=[msg]
            )

        if planet.owner_id is None:
            return ActionResult(
                success=False,
                action=ActionType.ATTACK_PLANET,
                message=f"{planet.name} is uninhabited. Use [C]laim Colony to take it peacefully.",
            )

        if planet.owner_id == attacker.id:
            return ActionResult(
                success=False,
                action=ActionType.ATTACK_PLANET,
                message=f"You cannot bombard your own colony ({planet.name})!",
            )

        logs.append(f"ORBITAL STRIKE: {attacker.name} enters high orbit around {planet.name} (Governor: {planet.owner_id})!")
        logs.append(f">> Planetary Shields: {planet.shields}/{planet.max_shields} | Defense Fighters: {planet.fighters}")

        att_power = int(attacker.ship.fighters * random.uniform(9.0, 15.0)) + random.randint(20, 50)
        def_power = int(planet.fighters * random.uniform(8.0, 13.0)) + random.randint(15, 30)
        if planet.society.get("degraded"):
            # A world that cannot fuel its defences fights at half its readiness-weighted strength
            r = float(planet.society.get("readiness", 0.0))
            def_power = int(def_power * (0.5 + 0.5 * r))
            logs.append(f">> {planet.name} broadcasts a DEGRADED beacon: its batteries fire at reduced power.")

        # 1. Attacker strikes planetary defense grid
        if planet.shields > 0:
            if att_power <= planet.shields:
                planet.shields -= att_power
                logs.append(f">> Planetary shields absorbed {att_power} MW of orbital bombardment (Remaining: {planet.shields}).")
            else:
                overflow = att_power - planet.shields
                planet.shields = 0
                logs.append(f">> PLANETARY SHIELDS OVERLOADED AND COLLAPSED!")
                fighters_lost = min(planet.fighters, max(1, overflow // 25))
                planet.fighters -= fighters_lost
                logs.append(f">> Orbital bombs wiped out {fighters_lost} defense fighters in the hangars.")
        else:
            fighters_lost = min(planet.fighters, max(1, att_power // 20))
            planet.fighters -= fighters_lost
            pop_loss = min(planet.population // 4, max(5, att_power // 10))
            planet.population = max(100, planet.population - pop_loss)
            if kernel is not None:
                from xylarium.kernel import fertility
                fertility.mark(planet, "bombarded", kernel.cycle_count)
            logs.append(f">> Direct bombardment destroyed {fighters_lost} fighters and caused {pop_loss} civilian casualties.")

        # 2. Planetary ground guns fire back at attacker
        if attacker.ship.shields > 0:
            if def_power <= attacker.ship.shields:
                attacker.ship.shields -= def_power
                logs.append(f"<< Planetary anti-orbital batteries struck ship shields for {def_power} MW (Remaining: {attacker.ship.shields}).")
            else:
                overflow = def_power - attacker.ship.shields
                attacker.ship.shields = 0
                att_lost = min(attacker.ship.fighters, max(1, overflow // 20))
                attacker.ship.fighters -= att_lost
                logs.append(f"<< Ship shields depleted! Anti-air flak took down {att_lost} fighters.")
        else:
            att_lost = min(attacker.ship.fighters, max(1, def_power // 20))
            attacker.ship.fighters -= att_lost
            logs.append(f"<< Surface missiles tore through your hull! Lost {att_lost} fighters.")

        # 3. Check for Planet Conquest
        if planet.shields <= 0 and planet.fighters <= 0:
            old_owner = planet.owner_id
            planet.owner_id = attacker.id
            plunder = planet.treasury
            planet.treasury = 0
            from xylarium.kernel.fx import credit
            credit(attacker, planet.currency, plunder)
            attacker.score += 800

            logs.append(f"*** PLANETARY VICTORY! Ground defenses have capitulated! ***")
            logs.append(f"*** {planet.name} has been conquered from {old_owner}! ***")
            logs.append(f"*** Plundered {plunder:,} Credits from the planetary vaults! ***")

            return ActionResult(
                success=True,
                action=ActionType.ATTACK_PLANET,
                message=f"Conquered {planet.name}! Claimed planetary sovereignty and {plunder:,} Cr!",
                turns_spent=2,
                logs=logs
            )

        if attacker.ship.shields <= 0 and attacker.ship.fighters <= 0:
            logs.append(f"*** Planetary defense cannons shot down your flagship! Escape pod fleeing to Sector 1. ***")
            _eject_to_sol(attacker, kernel)

            return ActionResult(
                success=True,
                action=ActionType.ATTACK_PLANET,
                message="Assault failed! Ship was shot down by planetary defenses.",
                turns_spent=2,
                logs=logs
            )

        logs.append(f"Bombardment run complete. Planet defenses remain active.")
        return ActionResult(
            success=True,
            action=ActionType.ATTACK_PLANET,
            message=f"Bombardment inflicted heavy damage. Planetary Shields: {planet.shields}, Fighters: {planet.fighters}.",
            turns_spent=2,
            logs=logs
        )
