"""
Planetary colonization and management engine for Xylarium.
Modeled after Barren Realms Elite (BRE) and Solar Realms Elite (SRE).
"""

from typing import Dict, Any, Optional
from xylarium.config import CITADEL_CONFIG
from xylarium.kernel.models import Planet, Captain, ActionResult, ActionType


class ColonyManager:
    """Handles planetary claiming, investments, citadel upgrades, and colony production."""

    @classmethod
    def claim_planet(cls, captain: Captain, planet: Planet) -> ActionResult:
        """Claim an uninhabited/unowned planet."""
        if planet.owner_id is not None:
            if planet.owner_id == captain.id:
                return ActionResult(
                    success=False,
                    action=ActionType.PLANET_CLAIM,
                    message=f"You already own {planet.name}.",
                )
            return ActionResult(
                success=False,
                action=ActionType.PLANET_CLAIM,
                message=f"{planet.name} is already colonized by another captain ({planet.owner_id}). You must invade!",
            )

        planet.owner_id = captain.id
        msg = f"Colony claimed! {planet.name} is now under the sovereignty of {captain.name}."
        captain.score += 100

        return ActionResult(
            success=True,
            action=ActionType.PLANET_CLAIM,
            message=msg,
            turns_spent=1,
            data={"planet_id": planet.id, "owner_id": captain.id},
            logs=[msg]
        )

    @classmethod
    def collect_taxes(cls, captain: Captain, planet: Planet) -> ActionResult:
        """Transfer accumulated taxes from colony treasury to ship credits."""
        if planet.owner_id != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_TAX,
                message=f"You do not govern {planet.name}.",
            )

        collected = planet.treasury
        if collected <= 0:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_TAX,
                message=f"Treasury on {planet.name} is currently empty.",
            )

        planet.treasury = 0
        captain.credits += collected
        captain.score += max(1, collected // 50)
        msg = f"Collected {collected:,} Credits from {planet.name}'s planetary treasury."

        return ActionResult(
            success=True,
            action=ActionType.PLANET_TAX,
            message=msg,
            turns_spent=0,
            data={"collected": collected, "captain_credits": captain.credits},
            logs=[msg]
        )

    @classmethod
    def invest_population(cls, captain: Captain, planet: Planet, investment_credits: int) -> ActionResult:
        """Invest credits to attract colonists and expand planetary housing."""
        if planet.owner_id != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_INVEST,
                message=f"You do not govern {planet.name}.",
            )

        if investment_credits <= 0:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_INVEST,
                message="Investment amount must be positive.",
            )

        if captain.credits < investment_credits:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_INVEST,
                message=f"Insufficient funds! You have {captain.credits:,} Cr.",
            )

        # 5 credits per new colonist
        new_colonists = investment_credits // 5
        captain.credits -= investment_credits
        planet.population += new_colonists
        msg = f"Invested {investment_credits:,} Cr into {planet.name}. Gained +{new_colonists:,} colonists! (Total: {planet.population:,})"

        return ActionResult(
            success=True,
            action=ActionType.PLANET_INVEST,
            message=msg,
            turns_spent=1,
            data={"new_colonists": new_colonists, "total_population": planet.population},
            logs=[msg]
        )

    @classmethod
    def build_shields(cls, captain: Captain, planet: Planet, points: int) -> ActionResult:
        """Construct planetary shield generators."""
        if planet.owner_id != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_BUILD_SHIELD,
                message=f"You do not govern {planet.name}.",
            )

        cfg = CITADEL_CONFIG.get(planet.citadel_level, CITADEL_CONFIG[0])
        max_s = cfg["max_shields"]

        available_space = max(0, max_s - planet.shields)
        if available_space <= 0:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_BUILD_SHIELD,
                message=f"Planetary shield grid at maximum capacity ({max_s}). Upgrade Citadel for higher capacity.",
            )

        points = min(points, available_space)
        cost_cr = points * 10
        cost_ore = max(1, points // 10)

        if captain.credits < cost_cr:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_BUILD_SHIELD,
                message=f"Requires {cost_cr:,} Cr. You have {captain.credits:,} Cr.",
            )

        if captain.ship.cargo.ore < cost_ore and planet.ore_silo < cost_ore:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_BUILD_SHIELD,
                message=f"Requires {cost_ore} Ore in ship cargo or planetary silo.",
            )

        # Deduct ore
        if planet.ore_silo >= cost_ore:
            planet.ore_silo -= cost_ore
        else:
            captain.ship.cargo.ore -= cost_ore

        captain.credits -= cost_cr
        planet.shields += points
        msg = f"Reinforced {planet.name} shields by +{points} MW for {cost_cr:,} Cr and {cost_ore} Ore. (Current: {planet.shields}/{max_s})"

        return ActionResult(
            success=True,
            action=ActionType.PLANET_BUILD_SHIELD,
            message=msg,
            turns_spent=1,
            data={"shields_added": points, "total_shields": planet.shields},
            logs=[msg]
        )

    @classmethod
    def recruit_fighters(cls, captain: Captain, planet: Planet, count: int) -> ActionResult:
        """Purchase and station defense fighters in orbital planetary garrison."""
        if planet.owner_id != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_RECRUIT_FIGHTERS,
                message=f"You do not govern {planet.name}.",
            )

        cfg = CITADEL_CONFIG.get(planet.citadel_level, CITADEL_CONFIG[0])
        max_f = cfg["max_fighters"]

        available_slots = max(0, max_f - planet.fighters)
        if available_slots <= 0:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_RECRUIT_FIGHTERS,
                message=f"Planetary garrison is at full capacity ({max_f} fighters). Upgrade Citadel to expand hangar bays.",
            )

        count = min(count, available_slots)
        cost_cr = count * 60

        if captain.credits < cost_cr:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_RECRUIT_FIGHTERS,
                message=f"Requires {cost_cr:,} Cr for {count} fighters. You have {captain.credits:,} Cr.",
            )

        captain.credits -= cost_cr
        planet.fighters += count
        msg = f"Stationed {count} Defense Fighters on {planet.name} for {cost_cr:,} Cr. (Total Garrison: {planet.fighters}/{max_f})"

        return ActionResult(
            success=True,
            action=ActionType.PLANET_RECRUIT_FIGHTERS,
            message=msg,
            turns_spent=1,
            data={"fighters_added": count, "total_fighters": planet.fighters},
            logs=[msg]
        )

    @classmethod
    def upgrade_citadel(cls, captain: Captain, planet: Planet) -> ActionResult:
        """Advance Citadel Tier to unlock higher defense caps and taxation multipliers."""
        if planet.owner_id != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_UPGRADE_CITADEL,
                message=f"You do not govern {planet.name}.",
            )

        next_level = planet.citadel_level + 1
        if next_level not in CITADEL_CONFIG:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_UPGRADE_CITADEL,
                message=f"Citadel is already at maximum rank: {CITADEL_CONFIG[planet.citadel_level]['name']}.",
            )

        cfg = CITADEL_CONFIG[next_level]
        cost_cr = cfg["upgrade_cost"]
        cost_ore = cfg["upgrade_ore"]

        if captain.credits < cost_cr:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_UPGRADE_CITADEL,
                message=f"Citadel upgrade requires {cost_cr:,} Cr. You have {captain.credits:,} Cr.",
            )

        available_ore = captain.ship.cargo.ore + planet.ore_silo
        if available_ore < cost_ore:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_UPGRADE_CITADEL,
                message=f"Requires {cost_ore} Ore for construction. Available across ship/silo: {available_ore}.",
            )

        # Deduct ore
        ore_needed = cost_ore
        if planet.ore_silo >= ore_needed:
            planet.ore_silo -= ore_needed
        else:
            ore_needed -= planet.ore_silo
            planet.ore_silo = 0
            captain.ship.cargo.ore -= ore_needed

        captain.credits -= cost_cr
        planet.citadel_level = next_level
        planet.max_shields = cfg["max_shields"]

        msg = (
            f"CITADEL UPGRADED! {planet.name} has advanced to Tier {next_level}: "
            f"'{cfg['name']}'! Max Shields: {cfg['max_shields']}, Max Fighters: {cfg['max_fighters']}."
        )
        captain.score += 250

        return ActionResult(
            success=True,
            action=ActionType.PLANET_UPGRADE_CITADEL,
            message=msg,
            turns_spent=1,
            data={"citadel_level": next_level, "citadel_name": cfg["name"]},
            logs=[msg]
        )

    @classmethod
    def transfer_cargo(
        cls,
        captain: Captain,
        planet: Planet,
        commodity: str,
        direction: str,  # 'to_planet' or 'to_ship'
        amount: int
    ) -> ActionResult:
        """Transfer Ore/Organics between ship hold and planetary silos."""
        commodity = commodity.upper()
        if commodity not in ["ORE", "ORGANICS"]:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_CARGO_TRANSFER,
                message="Planets only store bulk raw commodities (Ore and Organics).",
            )

        if amount <= 0:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_CARGO_TRANSFER,
                message="Transfer amount must be positive.",
            )

        if direction == "to_planet":
            current_hold = captain.ship.cargo.ore if commodity == "ORE" else captain.ship.cargo.organics
            if amount > current_hold:
                return ActionResult(
                    success=False,
                    action=ActionType.PLANET_CARGO_TRANSFER,
                    message=f"You only have {current_hold} units of {commodity} in your ship hold.",
                )

            if commodity == "ORE":
                captain.ship.cargo.ore -= amount
                planet.ore_silo += amount
            else:
                captain.ship.cargo.organics -= amount
                planet.organics_silo += amount

            msg = f"Transferred {amount} units of {commodity} from ship to {planet.name} silo."
        else:
            current_silo = planet.ore_silo if commodity == "ORE" else planet.organics_silo
            if amount > current_silo:
                return ActionResult(
                    success=False,
                    action=ActionType.PLANET_CARGO_TRANSFER,
                    message=f"Planetary silo only holds {current_silo} units of {commodity}.",
                )

            if captain.ship.cargo.available_space < amount:
                return ActionResult(
                    success=False,
                    action=ActionType.PLANET_CARGO_TRANSFER,
                    message=f"Insufficient ship cargo holds! Free space: {captain.ship.cargo.available_space}.",
                )

            if commodity == "ORE":
                planet.ore_silo -= amount
                captain.ship.cargo.ore += amount
            else:
                planet.organics_silo -= amount
                captain.ship.cargo.organics += amount

            msg = f"Loaded {amount} units of {commodity} from {planet.name} silo to ship hold."

        return ActionResult(
            success=True,
            action=ActionType.PLANET_CARGO_TRANSFER,
            message=msg,
            turns_spent=0,
            logs=[msg]
        )

    @classmethod
    def tick_colony(cls, planet: Planet) -> Dict[str, Any]:
        """
        Simulate colony economic yield for a world tick:
        - Taxes generated based on population & citadel tier.
        - Raw ore & organics mined.
        - Population growth.
        """
        if not planet.owner_id:
            return {}

        cfg = CITADEL_CONFIG.get(planet.citadel_level, CITADEL_CONFIG[0])
        tax_mult = cfg["tax_multiplier"]

        # Tax formula: approx 0.15 Cr per colonist per tick * citadel multiplier
        tax_yield = int((planet.population * 0.15) * tax_mult)
        planet.treasury = min(500000, planet.treasury + tax_yield)

        # Mining yields
        ore_mined = max(1, int(planet.population * 0.02))
        organics_harvested = max(1, int(planet.population * 0.015))
        planet.ore_silo = min(5000, planet.ore_silo + ore_mined)
        planet.organics_silo = min(5000, planet.organics_silo + organics_harvested)

        # Population natural growth (+2%)
        pop_growth = int(planet.population * 0.02)
        planet.population += pop_growth

        return {
            "planet_id": planet.id,
            "tax_yield": tax_yield,
            "ore_mined": ore_mined,
            "organics_harvested": organics_harvested,
            "pop_growth": pop_growth,
        }
