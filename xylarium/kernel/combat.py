"""
Tactical combat engine for Xylarium.
Handles ship-to-ship tactical engagements and planetary orbital sieges (BRE/SRE style).
"""

import random
from typing import Dict, Any, List, Optional
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


class CombatManager:
    """Resolves ship-to-ship battles and planetary assaults."""

    @classmethod
    def resolve_ship_battle(
        cls,
        attacker: Captain,
        defender: Captain,
        sector: Sector,
        fighters_to_commit: Optional[int] = None
    ) -> ActionResult:
        """
        Executes a tactical combat round between two captains in the same sector.
        """
        logs: List[str] = []

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

        # Determine fighters committed
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

            space = attacker.ship.cargo.available_space
            take_ore = min(space, salvage_ore)
            attacker.ship.cargo.ore += take_ore
            space = attacker.ship.cargo.available_space
            take_org = min(space, salvage_org)
            attacker.ship.cargo.organics += take_org
            space = attacker.ship.cargo.available_space
            take_eq = min(space, salvage_eq)
            attacker.ship.cargo.equipment += take_eq

            logs.append(f"*** ENEMY DESTROYED! {defender.name}'s ship breaks apart into stardust! ***")
            logs.append(f"*** Plundered {bounty_cr:,} Credits and salvaged cargo from the wreckage! ***")

            # Respawn defender at Fed Central in escape pod / scout
            defender.sector_id = 1
            defender.ship.shields = 50
            defender.ship.fighters = 5
            defender.ship.cargo = CargoHold(capacity=25)

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
            attacker.sector_id = 1
            attacker.ship.shields = 50
            attacker.ship.fighters = 5
            attacker.ship.cargo = CargoHold(capacity=25)
            attacker.credits = max(100, attacker.credits // 2)

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
        sector: Sector
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
            attacker.credits += plunder
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
            attacker.sector_id = 1
            attacker.ship.shields = 50
            attacker.ship.fighters = 5
            attacker.ship.cargo = CargoHold(capacity=25)

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
