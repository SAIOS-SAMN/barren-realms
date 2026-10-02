"""
Planetary colonization and management engine for Xylarium.
Modeled after Barren Realms Elite (BRE) and Solar Realms Elite (SRE).
"""

import random
import zlib
from typing import Dict, Any, Optional
from xylarium.config import (
    CITADEL_CONFIG,
    COMMODITY_CONFIG,
    HOUSEHOLD_INCOME_SHARE,
    COUNCIL_WORKS_SHARE,
    SHIP_CATALOG,
    PORT_START_TREASURY,
    PLANETARY_SPACEFLIGHT_COST,
    CITADEL_UPKEEP,
    COLONY_TAX_PER_CAPITA,
    PRICE_LEVEL,
    COLONY_VAULT_CAP,
    UPKEEP_ARREARS_MORALE_PENALTY,
    COLONY_KIT_CREDITS,
    COLONY_KIT_EQUIPMENT,
    COLONY_KIT_COLONISTS,
    COLONY_LEVY_SHARE,
    COLONY_LEVY_INTERVAL,
    COLONY_KIT_ORGANICS,
    DIASPORA_HOUSING_THRESHOLD,
    DIASPORA_CROWDED_CYCLES,
    DIASPORA_TAX_SHARE,
    COLONY_CLAIM_TIER_UNSETTLED,
    COLONY_CLAIM_TIER_ESTABLISHED,
    COLONY_CLAIM_ESTABLISHED_MIN_CR,
    COLONY_CLAIM_TIER_INHABITED,
    COLONY_CLAIM_INDIGENOUS_MIN_REP,
    XP_INDUSTRY_CITADEL,
    XP_INDUSTRY_DISTRICT,
    XP_GOVERNANCE_HEALTHY_TAX,
)
from xylarium.kernel import matter
from xylarium.kernel.models import (
    Planet,
    Captain,
    ActionResult,
    ActionType,
    Ship,
    CargoHold,
    AIPersonality,
)
from xylarium.kernel.civilization import CivilizationIntelligenceEngine, CIVIC_PROJECTS
from xylarium.kernel.elements import PeriodicTable
from xylarium.kernel.experience import ExperienceManager


_BASE_ORE = COMMODITY_CONFIG["ORE"]["base_price"]


def is_indigenous_natives(planet: Planet) -> bool:
    return bool(getattr(planet, "natives", None))


class ColonyManager:
    """Handles planetary claiming, investments, citadel upgrades, and colony production."""

    @classmethod
    def _pay_local(cls, planet: Planet, kernel: Optional[Any], amount: int) -> None:
        """What a colony already paid out of its vault goes to the region's contractors (not the void)."""
        if amount <= 0:
            return
        port = cls._contractor_port(planet, kernel)
        if port is not None:
            port.treasury += amount
        elif kernel is not None:
            from xylarium.kernel import ledger
            ledger.burn("colony_construction", amount, planet.currency)

    @classmethod
    def _pay_contractor_sol(cls, planet: Planet, sol_amount: int, to_vault: bool = False) -> None:
        """A captain's SOL spent on a world goes to its contractors (or its vault), cleared into local money."""
        if sol_amount <= 0:
            return
        from xylarium.kernel import ledger, fx as fx_mod
        kernel = ledger.active_kernel()
        target = planet if to_vault else cls._contractor_port(planet, kernel)
        if target is None:
            ledger.burn("colony_construction", sol_amount, "SOL")
            return
        cur = planet.currency if to_vault else target.currency
        if cur != "SOL" and fx_mod.ACTIVE_FX is not None:
            target.treasury += fx_mod.ACTIVE_FX.swap_sol_to(cur, sol_amount)
        else:
            target.treasury += sol_amount

    @staticmethod
    def _contractor_port(planet: Planet, kernel: Optional[Any]) -> Optional[Any]:
        """The starport that services a colony's citadel: its own system's, else the nearest of its money."""
        if kernel is None:
            return None
        from xylarium.kernel import cache, topology

        def find():
            return topology.nearest(kernel, planet.sector_id, 3,
                                    lambda sec: sec.port is not None and sec.port.currency == planet.currency)
        sid = cache.memo(kernel, "contractor_port", planet.id, find, max_age=500)
        port = kernel.sectors[sid].port if sid is not None else None
        if port is not None and port.currency != planet.currency:
            # the remembered port has since come to trade in another money (a dock rehomed): find one that pays
            sid = find()
            cache._bucket(kernel, "contractor_port", None, 500)[planet.id] = sid
            port = kernel.sectors[sid].port if sid is not None else None
        return port if (port is not None and port.currency == planet.currency) else None

    @classmethod
    def claim_requirements(cls, captain: Captain, planet: Planet, sector: Optional[Any] = None,
                           kernel: Optional[Any] = None) -> Optional[str]:
        """
        Staged colony founding. Returns None when the captain may found a colony here,
        otherwise the reason they may not:
          * uninhabited world, unclaimed system  -> Tier 1 + colony kit
          * system where another sovereign holds a world -> Tier 2 + settlement charter (credit rating)
          * indigenous-inhabited world -> Tier 3 + indigenous treaty standing (or invade)
        """
        tier = getattr(captain, "rank_tier", 1)
        from xylarium.kernel.universe import habitability
        hab = habitability(getattr(captain, "metabolism", "biotic"), getattr(planet, "planet_type", "TERRESTRIAL"))
        inhabited = planet.population > 0 and getattr(planet, "civilization", None) is not None
        if inhabited and getattr(planet.civilization, "name", "") == "Terran Federation":
            return f"{planet.name} is a Federal Core World: its sovereignty is not open to annexation."
        if getattr(planet, "faction_id", None):
            return f"{planet.name} flies the banner of a great power; it is taken by war, not by charter."
        natives = getattr(planet, "natives", None)
        if natives:
            # Settling a native world displaces its people: lawful only where the doctrine permits exploitation
            allowed = False
            if kernel is not None and sector is not None and getattr(kernel, "factions", None) is not None:
                from xylarium.config import POLICY_CARDS
                allowed = "exploit" in POLICY_CARDS[kernel.factions.hand_for(sector)["card"]]["allows"]
            if not allowed:
                return (f"{planet.name} is home to the {natives['name']}, a non-spacefaring people. The doctrine "
                        f"here forbids displacing them (see NATIVES for lawful dealings).")
        if not inhabited and hab <= 0:
            return (
                f"{planet.name} is a {planet.planet_type.replace('_', ' ').lower()} world: uninhabitable for "
                f"{getattr(captain, 'metabolism', 'biotic')} biology. Seek a world suited to your lineage."
            )
        if inhabited:
            rep = getattr(captain, "faction_reputation", {}).get("Indigenous", 50.0)
            if tier < COLONY_CLAIM_TIER_INHABITED or rep < COLONY_CLAIM_INDIGENOUS_MIN_REP:
                return (
                    f"{planet.name} is home to an indigenous civilization. Annexation requires Rank Tier "
                    f"{COLONY_CLAIM_TIER_INHABITED} and Indigenous standing >= {COLONY_CLAIM_INDIGENOUS_MIN_REP:.0f} "
                    f"(you: Tier {tier}, standing {rep:.0f}) - or a ground invasion."
                )
        # Established presence: another sovereign's colony or an indigenous civilization in the system
        established = sector is not None and any(
            (p.owner_id and p.owner_id != captain.id)
            or (p.owner_id is None and p.population > 0 and getattr(p, "civilization", None) is not None)
            for p in getattr(sector, "planets", []) if p.id != planet.id
        )
        if established:
            cr = getattr(captain, "credit_rating", 500)
            if tier < COLONY_CLAIM_TIER_ESTABLISHED or cr < COLONY_CLAIM_ESTABLISHED_MIN_CR:
                return (
                    f"Sector {sector.id:03d} already hosts a sovereign colony. A Federal settlement charter requires "
                    f"Rank Tier {COLONY_CLAIM_TIER_ESTABLISHED} and credit rating >= {COLONY_CLAIM_ESTABLISHED_MIN_CR} "
                    f"(you: Tier {tier}, rating {cr})."
                )
        if tier < COLONY_CLAIM_TIER_UNSETTLED:
            return f"Colony founding requires Rank Tier {COLONY_CLAIM_TIER_UNSETTLED}."
        if captain.credits < COLONY_KIT_CREDITS:
            return f"A colony kit (colonists and habitat modules) costs {COLONY_KIT_CREDITS:,} Cr. You have {captain.credits:,} Cr."
        if captain.ship.cargo.unbonded("EQUIPMENT") < COLONY_KIT_EQUIPMENT:
            return (
                f"Founding a colony consumes {COLONY_KIT_EQUIPMENT} Equipment for habitat modules "
                f"(unbonded in hold: {captain.ship.cargo.unbonded('EQUIPMENT')})."
            )
        return None

    @classmethod
    def claim_planet(cls, captain: Captain, planet: Planet, sector: Optional[Any] = None,
                     kernel: Optional[Any] = None) -> ActionResult:
        """Found a colony on an unowned planet, subject to staged founding requirements."""
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

        blocker = cls.claim_requirements(captain, planet, sector, kernel)
        if blocker:
            return ActionResult(success=False, action=ActionType.PLANET_CLAIM, message=blocker)
        displaced = None
        if getattr(planet, "natives", None) and kernel is not None:
            from xylarium.kernel.natives import NativeManager
            from xylarium.kernel import alignment
            displaced = planet.natives["name"]
            NativeManager.collapse(kernel, planet, f"displaced by {captain.name}'s settlers")
            alignment.deed(kernel, captain, "native_exploit", scale=1.5)

        # Colony kit is consumed: credits to outfitters, equipment into habitat modules
        captain.credits -= COLONY_KIT_CREDITS
        cls._pay_contractor_sol(planet, COLONY_KIT_CREDITS)
        matter.consume(captain.ship.cargo, "equipment", "EQUIPMENT", COLONY_KIT_EQUIPMENT, "colony_kit")   # built into habitats
        if planet.population <= 0:
            from xylarium.kernel.universe import habitability
            planet.habitability = habitability(getattr(captain, "metabolism", "biotic"), planet.planet_type)
            planet.population = COLONY_KIT_COLONISTS
            from xylarium.kernel import staples          # the colonists land with stores of their own staple
            staples.add(planet, staples.of_metabolism(getattr(captain, "metabolism", "biotic")),
                        COLONY_KIT_ORGANICS, "colony_kit")
        planet.owner_id = captain.id
        msg = (
            f"Colony founded! {planet.name} is now under the sovereignty of {captain.name} "
            f"(colony kit: {COLONY_KIT_CREDITS:,} Cr + {COLONY_KIT_EQUIPMENT} Equipment)."
        )
        if displaced:
            msg += f" The {displaced} were displaced; their cities are ruins now."
        captain.score += 100
        ExperienceManager.award(captain, "industry", XP_INDUSTRY_CITADEL, None, key=f"found:{planet.id}")

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

        # Sovereign levy: a governor draws a share of the vault once per fiscal quarter;
        # the rest stays to run the colony (imports, services, upkeep, development).
        from xylarium.kernel import ledger as _ledger
        cycle = getattr(_ledger.ACTIVE_LEDGER, "cycle_hint", 0) if _ledger.ACTIVE_LEDGER is not None else 0
        last = getattr(planet, "last_levy_cycle", -10 ** 9)
        if cycle - last < COLONY_LEVY_INTERVAL:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_TAX,
                message=f"{planet.name}'s sovereign levy was already drawn this fiscal quarter "
                        f"(next in {COLONY_LEVY_INTERVAL - (cycle - last)} cycles).",
            )
        collected = int(planet.treasury * COLONY_LEVY_SHARE)
        if collected <= 0:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_TAX,
                message=f"Treasury on {planet.name} is currently empty.",
            )

        planet.treasury -= collected
        planet.last_levy_cycle = cycle
        from xylarium.kernel.fx import credit
        credit(captain, planet.currency, collected)
        captain.score += max(1, collected // 50)
        ExperienceManager.record_revenue(captain, collected)
        if planet.morale >= 60:
            ExperienceManager.award(captain, "governance", XP_GOVERNANCE_HEALTHY_TAX, None, key=f"tax:{planet.id}")
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

        cfg = CITADEL_CONFIG.get(planet.citadel_level, CITADEL_CONFIG[0])
        from xylarium.kernel import demography
        max_pop = demography.housing_cap(planet)

        if planet.population >= max_pop:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_INVEST,
                message=f"{planet.name} is at its carrying capacity: its land and Tier {planet.citadel_level} ({cfg['name']}) agriculture feed {max_pop:,} people. Raise the citadel or dig habitats to feed more.",
            )

        # 5 credits per new colonist
        new_colonists = investment_credits // 5
        if planet.population + new_colonists > max_pop:
            new_colonists = max_pop - planet.population
            investment_credits = new_colonists * 5

        captain.credits -= investment_credits
        cls._pay_contractor_sol(planet, investment_credits, to_vault=True)   # settlement grants land in the vault
        planet.population += new_colonists
        msg = f"Invested {investment_credits:,} Cr into {planet.name}. Gained +{new_colonists:,} colonists! (Total: {planet.population:,} / Cap: {max_pop:,})"

        return ActionResult(
            success=True,
            action=ActionType.PLANET_INVEST,
            message=msg,
            turns_spent=1,
            data={"new_colonists": new_colonists, "total_population": planet.population, "max_population": max_pop},
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

        if captain.ship.cargo.unbonded("ORE") < cost_ore and planet.ore_silo < cost_ore:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_BUILD_SHIELD,
                message=f"Requires {cost_ore} Ore in ship cargo or planetary silo.",
            )

        # Deduct ore
        if planet.ore_silo >= cost_ore:
            matter.consume(planet, "ore_silo", "ORE", cost_ore, "construction")
        else:
            matter.consume(captain.ship.cargo, "ore", "ORE", cost_ore, "construction")

        captain.credits -= cost_cr
        cls._pay_contractor_sol(planet, cost_cr)
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
        cls._pay_contractor_sol(planet, cost_cr)
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

        available_ore = captain.ship.cargo.unbonded("ORE") + planet.ore_silo
        if available_ore < cost_ore:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_UPGRADE_CITADEL,
                message=f"Requires {cost_ore} Ore for construction. Available across ship/silo: {available_ore}.",
            )

        # Deduct ore
        ore_needed = cost_ore
        if planet.ore_silo >= ore_needed:
            matter.consume(planet, "ore_silo", "ORE", ore_needed, "construction")
        else:
            ore_needed -= matter.consume(planet, "ore_silo", "ORE", planet.ore_silo, "construction")
            matter.consume(captain.ship.cargo, "ore", "ORE", ore_needed, "construction")

        captain.credits -= cost_cr
        cls._pay_contractor_sol(planet, cost_cr)
        planet.citadel_level = next_level
        planet.max_shields = cfg["max_shields"]
        ExperienceManager.award(captain, "industry", XP_INDUSTRY_CITADEL, None, key=f"citadel:{planet.id}:{next_level}")

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
            current_hold = captain.ship.cargo.unbonded(commodity)
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

            if not captain.ship.cargo.can_fit(commodity, amount):
                max_u = captain.ship.cargo.available_units_for(commodity)
                return ActionResult(
                    success=False,
                    action=ActionType.PLANET_CARGO_TRANSFER,
                    message=f"Insufficient ship cargo holds! Free capacity for {commodity}: {max_u} units.",
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
    def tick_colony(
        cls,
        planet: Planet,
        event_bus: Optional[Any] = None,
        kernel: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Simulate colony economic yield for a world tick:
        - Taxes generated based on population & citadel tier.
        - Raw ore & organics mined.
        - Population growth.
        - Civilization intelligence loop: tension δ = demand - supply, civic projects, and periodic table research.
        - Planetary spaceflight (Civiligenesis) when citadel tier >= 2, pop >= 10k, vault >= 15k Cr.
        """
        civ_intel = None
        if (planet.population > 0 and not planet.owner_id and getattr(planet, "civilization", None) is None
                and not getattr(planet, "natives", None)):
            # settlers left with no one to answer to (no captain, no nation - a banner alone is not a people) are a
            # people of their own, and live or starve as one
            from xylarium.kernel import biosphere
            planet.faction_id = None
            planet.civilization = CivilizationIntelligenceEngine.create_civilization({
                "name": f"Free {planet.name.split()[0]}", "species_name": "settlers", "clade": "unknown",
                "class_code": 1, "sigil": "✧",
                "metabolism": biosphere.metabolism_of(kernel, planet), "disposition": "industry",
                "motto": "no one came back for us", "station": "unseated", "tech_level": 2})
        if getattr(planet, "civilization", None):
            civ_intel = CivilizationIntelligenceEngine.tick_civilization(
                planet.civilization, planet, event_bus
            )

        is_indigenous = (planet.owner_id is None and getattr(planet, "civilization", None) is not None)
        if not planet.owner_id and not is_indigenous:
            if civ_intel:
                return {"planet_id": planet.id, "civilization": civ_intel}
            return {}

        cfg = CITADEL_CONFIG.get(planet.citadel_level, CITADEL_CONFIG[0])
        # Carrying capacity is derived from the world's physics and technology (biosphere.py). Worlds under
        # population controls hold their numbers below it.
        from xylarium.kernel import demography
        max_pop = demography.growth_ceiling(planet)
        tax_mult = cfg["tax_multiplier"]

        # 1. Food and people (biosphere.py): the world eats, and - fed - grows logistically toward what its
        # land can carry, never faster than its farms can add food. Over capacity, it shrinks.
        # Each people eats its own staple (staples.py): organics, ore, ice or hydrogen.
        from xylarium.kernel import biosphere, staples
        required_food = biosphere.consumption(planet)
        famine = False
        famine_loss = 0
        soc = planet.society
        soc["need_q"] = soc.get("need_q", 0) + required_food            # read each quarter by sustenance.py

        if staples.stores(kernel, planet) >= required_food:
            staples.eat(kernel, planet, required_food)
            planet.morale = min(100, planet.morale + 2)
            pop_growth = biosphere.births(kernel, planet, max_pop)
            if pop_growth > 0 and "occupation" in soc:           # the occupied bear children as they comply
                from xylarium.kernel import occupation
                pop_growth = int(pop_growth * occupation.births_factor(kernel, planet))
            planet.population = max(1, planet.population + pop_growth)
        else:
            # Famine penalty: population decline and morale crash
            deficit = required_food - staples.eat(kernel, planet, required_food)
            soc["short_q"] = soc.get("short_q", 0) + deficit
            famine = True
            if kernel is not None:
                from xylarium.kernel import fertility
                fertility.mark(planet, "famine", kernel.cycle_count)
            famine_loss = max(0, min(planet.population - 100, max(5, deficit * 200)))
            planet.population -= famine_loss          # down to a last hundred, never up from below it
            planet.morale = max(10, planet.morale - 15)
            pop_growth = -famine_loss
            # a remnant its own land cannot feed (its measured harvest short of even its need) does not linger:
            # it dies, and its town is ruins. A colony not yet measured is still bringing in its first harvest.
            from xylarium.kernel.archaeology import ArchaeologyManager
            fed = soc.get("self_sufficiency")
            if (is_indigenous or (fed is not None and float(fed) < 1.0)) and \
                    ArchaeologyManager.check_collapse(planet, True, kernel):
                return {"planet_id": planet.id, "collapsed": True}

        # 1b. Housing crowding & diaspora threshold tracking
        from xylarium.kernel import demography
        h_cap = demography.housing_cap(planet, kernel)
        food_stable = (not famine and staples.stores(kernel, planet) >= required_food)
        if h_cap > 0 and planet.population >= int(h_cap * DIASPORA_HOUSING_THRESHOLD) and food_stable:
            planet.crowded_cycles = getattr(planet, "crowded_cycles", 0) + 1
        else:
            planet.crowded_cycles = 0

        # 2. Colony budget. Gross tax is collected every cycle (scaled by the currency's price level,
        # morale, and vault headroom); citadel upkeep and public services are paid out of gross tax
        # first and savings second. Only the net surplus reaches the vault; a deficit drains it.
        # Services scale with the regional monetary authority's fiscal rule (austerity vs. easing).
        from xylarium.kernel import ledger
        level = PRICE_LEVEL.get(planet.currency, 1.0)
        vault_cap = COLONY_VAULT_CAP * level
        morale_factor = max(0.1, planet.morale / 100.0)
        headroom = max(0.0, (vault_cap - planet.treasury) / vault_cap)
        # What the colony earns is split: households keep their share (their purse, spent at the region's
        # starports each quarter - see demography.households); the government taxes the rest. Public
        # services withdraw the share of that tax the regional authority sets each season to keep
        # M V = P Y (ledger.MonetaryPolicy): money grows with real output, no faster.
        withdraw = ledger.policy_factor(planet.currency)
        share = HOUSEHOLD_INCOME_SHARE
        from xylarium.kernel.fertility import tax_factor
        from xylarium.kernel import energy, occupation, society, ways
        earnings = planet.population * COLONY_TAX_PER_CAPITA * level * tax_mult * morale_factor * tax_factor(planet) \
            * energy.output_factor(planet) \
            * ways.taxable(planet) \
            * (occupation.compliance(kernel, planet) if "occupation" in soc else 1.0) \
            * society.output_factor(planet)                   # those under arms do not work (society.py)
        household_income = int(earnings * share)
        if household_income > 0:
            ledger.mint("colony_tax", household_income, planet.currency)
            planet.household_purse += household_income
        tax_yield = int(earnings * (1.0 - share) * headroom)
        diaspora_cut = 0
        if getattr(planet, "crowded_cycles", 0) > DIASPORA_CROWDED_CYCLES and tax_yield > 0:
            diaspora_cut = int(tax_yield * DIASPORA_TAX_SHARE)
            if diaspora_cut > 0:
                ledger.mint("colony_tax", diaspora_cut, planet.currency)
                planet.diaspora_escrow = getattr(planet, "diaspora_escrow", 0) + diaspora_cut
                tax_yield -= diaspora_cut
        if ledger.ACTIVE_POLICY is not None:
            ledger.ACTIVE_POLICY.record_earnings(planet.currency, household_income + diaspora_cut + tax_yield,
                                                 earnings * (1.0 - share))   # the base services are measured on
        upkeep = {"credits": 0, "ore": 0} if ways.stateless(planet) else \
            CITADEL_UPKEEP.get(planet.citadel_level, CITADEL_UPKEEP[0])
        upkeep_credits = int(upkeep["credits"] * level)
        # Withdrawal is measured against the government's earnings before the vault taper: a full vault
        # pays no new tax, but it is exactly the savings the authority must be able to reach
        services_due = int(earnings * (1.0 - share) * withdraw)
        # A crowded world that is still building puts part of its public budget into works (housing,
        # citadel) instead of current services - the council spends it next quarter (demography.develop)
        from xylarium.kernel import demography
        if demography.building(planet):
            services_due = int(services_due * (1.0 - COUNCIL_WORKS_SHARE))
        # Tribute owed to a patron is paid out of tax ahead of services (relations.py sets it aside here)
        services_due = max(0, services_due - int(soc.get("tribute_tick", 0)))
        # Withdrawal takes what the budget can bear (this cycle's tax and a tenth of savings); it does not
        # push a solvent colony into arrears - the authority sees the shortfall and asks again next season
        services_due = min(services_due, max(0, tax_yield + planet.treasury // 10 - upkeep_credits))
        spending = upkeep_credits + services_due
        upkeep_paid = (tax_yield + planet.treasury >= spending) and planet.ore_silo >= upkeep["ore"]
        if upkeep_paid:
            matter.consume(planet, "ore_silo", "ORE", upkeep["ore"], "citadel_upkeep")
            soc["fiscal_acc"] = soc.get("fiscal_acc", 0) + tax_yield        # the tax it actually took (relations)
            # Taxes and public services are the fiscal pair (declared mint / burn) ...
            net = tax_yield - services_due
            if net >= 0:
                ledger.mint("colony_tax", net, planet.currency)
            else:
                ledger.burn("public_services", -net, planet.currency)
            planet.treasury += net
            # ... while citadel upkeep is paid to contractors: the region's starport, not the void
            planet.treasury -= upkeep_credits
            aside = min(int(soc.get("tribute_tick", 0)), max(0, planet.treasury))
            if aside > 0:                                 # tribute leaves the vault as it is collected: not the council's
                planet.treasury -= aside
                soc["tribute_escrow"] = soc.get("tribute_escrow", 0) + aside
            contractor = cls._contractor_port(planet, kernel)
            if contractor is not None:
                contractor.treasury += upkeep_credits
            else:
                ledger.burn("citadel_upkeep", upkeep_credits, planet.currency)
            # (A full vault no longer destroys money: tax already tapers to nothing as the vault fills, and the
            # regional authority's services withdrawal is the one sink - a second, level-triggered burn fed back
            # into the authority's feed-forward and pumped money through households without end.)
            services = services_due
        else:
            # Arrears: everything available is spent, the gap erodes morale
            ledger.burn("public_services", planet.treasury, planet.currency)
            services = tax_yield + planet.treasury
            planet.treasury = 0
            planet.morale = max(10, planet.morale - UPKEEP_ARREARS_MORALE_PENALTY)
            ledger.mint("colony_tax", tax_yield, planet.currency)
            ledger.burn("public_services", tax_yield, planet.currency)
        if ledger.ACTIVE_POLICY is not None:
            ledger.ACTIVE_POLICY.record_services(planet.currency, services)

        # 3. Mining yields
        ore_mined = max(1, int(planet.population * 0.02))
        food_harvested = biosphere.harvest(kernel, planet, demography.housing_cap(planet, kernel))
        from xylarium.kernel import geology
        ore_mined = geology.mine_crust(planet, ore_mined)          # out of the world's own crust
        food_harvested = staples.harvest(kernel, planet, food_harvested)   # the people's own staple
        soc["harvest_q"] = soc.get("harvest_q", 0) + food_harvested
        # Real output (the Y of M V = P Y): what was harvested (in food units) and mined, at base prices and
        # price level
        if ledger.ACTIVE_POLICY is not None and not is_indigenous_natives(planet) and not ways.stateless(planet):
            ledger.ACTIVE_POLICY.record_output(planet.currency, (food_harvested * staples.FOOD_UNIT_VALUE
                                                                 + ore_mined * _BASE_ORE) * level)

        # 4. Autonomous Planetary Counter-Intelligence Garrison
        # Fortified colonies (Citadel Tier 1+) allocate vault revenue to defense operatives
        max_sec = cfg.get("max_security", 5 * planet.citadel_level)
        recruited_sec = 0
        if planet.citadel_level >= 1 and planet.security_operatives < max_sec:
            # Recruit if treasury is healthy or during security lockout
            if planet.treasury >= 3000 or (planet.security_lockout > 0 and planet.treasury >= 1000):
                planet.treasury -= 500
                cls._pay_local(planet, kernel, 500)
                planet.security_operatives += 1
                recruited_sec = 1

        # Decrement security lockout countdown if active
        if planet.security_lockout > 0:
            planet.security_lockout -= 1

        if kernel is not None and planet.owner_id in getattr(kernel, "captains", {}):
            ExperienceManager.check_colony_growth(kernel.captains[planet.owner_id], planet, kernel)

        res = {
            "planet_id": planet.id,
            "upkeep_paid": upkeep_paid,
            "tax_yield": tax_yield,
            "public_services": services,
            "ore_mined": ore_mined,
            "organics_harvested": food_harvested,          # in food units of the people's staple
            "staple": staples.of(kernel, planet) if kernel is not None else "ORGANICS",
            "pop_growth": pop_growth,
            "famine": famine,
            "famine_loss": famine_loss,
            "morale": planet.morale,
            "population": planet.population,
            "max_population": max_pop,
            "security_operatives": planet.security_operatives,
            "security_lockout": planet.security_lockout,
            "recruited_sec": recruited_sec,
        }
        if civ_intel:
            res["civilization"] = civ_intel

        # 5. Citadel upgrades for indigenous and AI worlds are the colony council's (demography.develop)

        # 6. Planetary Spaceflight (Civiligenesis) - Vector 2
        launched_cap = None
        if kernel:
            launched_cap = cls.check_planetary_spaceflight(kernel, planet, event_bus)
        if launched_cap:
            res["spaceflight_launched"] = launched_cap.name

        return res

    @classmethod
    def check_planetary_spaceflight(
        cls,
        kernel: Any,
        planet: Planet,
        event_bus: Optional[Any] = None,
    ) -> Optional[Captain]:
        """
        Vector 2: Planetary Spaceflight (Civiligenesis).
        A world whose yards can build a starship (sustenance.yards) commissions one of its own when the trade it
        would carry - its surplus out, its shortfalls in, at the carrier's share of their value that import
        orders pay - is worth the hull to its council (decide.py). One hull in service per world.
        """
        from xylarium.kernel import populace, sustenance
        if not kernel or getattr(planet, "natives", None) or not sustenance.yards(planet):
            return None
        if (kernel.cycle_count % 25) != (zlib.crc32(planet.id.encode()) % 25):
            return None                                   # the council sits once a season
        active_id = getattr(planet, "active_indigenous_captain_id", None)
        if active_id and active_id in kernel.captains:
            return None
        if planet.treasury < PLANETARY_SPACEFLIGHT_COST or not populace.room_for_ai(kernel):
            return None
        from xylarium.config import COLONY_IMPORT_UNIT_PREMIUM, COMMODITY_CONFIG, PRICE_LEVEL
        from xylarium.kernel import decide, staples
        level = PRICE_LEVEL.get(planet.currency, 1.0)
        food = staples.of(kernel, planet)
        moved = 0.0
        for comm in {food, "ORE", *planet.element_reserves.keys()}:
            base = COMMODITY_CONFIG.get(comm, {}).get("base_price", 0) * level
            out = staples.surplus(kernel, planet, comm)
            short = max(0, staples.reserve(kernel, planet, comm) - staples.held(planet, comm)) if comm == food else 0
            moved += (out + short) * base
        hull = SHIP_CATALOG.get("Merchant Cruiser", {}).get("holds", 60)
        carried_q = min(moved, hull * 25 * level * 10)          # what one hull can move in a season
        worth = decide.worth(kernel, carried_q * (COLONY_IMPORT_UNIT_PREMIUM - 1.0), decide.mind_of_planet(kernel, planet),
                             planet.currency)
        # a ship needs a dock: a system with none gets one with its first hull (waystations.found, a transfer)
        from xylarium.kernel import primordial, waystations
        sec = kernel.sectors.get(planet.sector_id)
        dock_sol = 0.0
        if sec is not None and sec.port is None:
            rate_sol = kernel.fx_market.rate(planet.currency) if planet.currency != "SOL" else 1.0
            dock_sol = PORT_START_TREASURY * level / max(1e-9, rate_sol) / 3
        dock_local = dock_sol * (kernel.fx_market.rate(planet.currency) if planet.currency != "SOL" else 1.0)
        if planet.treasury < PLANETARY_SPACEFLIGHT_COST + dock_local:
            return None
        if decide.choose(kernel, [decide.option("commission_ship", PLANETARY_SPACEFLIGHT_COST + dock_local, worth,
                                                cash=PLANETARY_SPACEFLIGHT_COST + dock_local, currency=planet.currency)],
                         decide.mind_of_planet(kernel, planet), planet.id, "ship") is None:
            return None
        from xylarium.kernel import institutions
        if institutions.founding(kernel) and planet.currency not in kernel.fx_market.pools:
            line = institutions.found_exchange(kernel, "the first starport opens")   # the lanes need a clearing house
            if line:
                kernel.action_logs.append(line)
            institutions._open_pool(kernel, planet.currency)
            if planet.currency not in kernel.fx_market.pools or planet.treasury < PLANETARY_SPACEFLIGHT_COST + dock_local:
                return None
        if dock_sol > 0:
            kernel.action_logs.append(waystations.found(kernel, sec, planet, dock_sol))
            primordial.first(kernel, "first_starport", planet.name)
        primordial.first(kernel, "first_starship", planet.name)

        # Deduct commissioning cost (local money). Part of it becomes the crew's operating float,
        # cleared into SOL through the ISSE FX desk; the rest is spent building the vessel.
        from xylarium.kernel import fx as fx_mod
        rate = fx_mod.ACTIVE_FX.rate(planet.currency) if (fx_mod.ACTIVE_FX and planet.currency != "SOL") else 1.0
        planet.treasury -= PLANETARY_SPACEFLIGHT_COST
        float_local = min(PLANETARY_SPACEFLIGHT_COST // 2, int(4000 * rate))
        cls._pay_local(planet, kernel, PLANETARY_SPACEFLIGHT_COST - float_local)   # the yard that built the ship
        crew_float = (fx_mod.ACTIVE_FX.swap_to_sol(planet.currency, float_local)
                      if (fx_mod.ACTIVE_FX and planet.currency != "SOL") else float_local)
        planet.last_spaceflight_cycle = kernel.cycle_count

        civ = getattr(planet, "civilization", None)
        if civ:
            civ_name = civ.name
            species_name = civ.species_name
            metabolism = civ.metabolism
        else:
            civ_name = planet.name
            species_name = "bimaniform-flatlander"
            metabolism = "mineral"

        # Personality & Hull based on metabolism
        if metabolism == "biotic":
            personality = AIPersonality.TRADER
            ship_class = "Merchant Cruiser"
        elif metabolism == "plasmic":
            personality = AIPersonality.MERCENARY
            ship_class = "Star Frigate"
        elif metabolism == "umbral":
            personality = AIPersonality.TRADER
            ship_class = "Scout Ship"
        else:  # mineral
            personality = AIPersonality.INDUSTRIALIST
            ship_class = "Star Frigate"

        ship_cfg = SHIP_CATALOG.get(ship_class, SHIP_CATALOG["Scout Ship"])
        cargo = CargoHold(capacity=ship_cfg["holds"])

        if metabolism == "biotic":
            cargo.organics = 20
            cargo.elements["H2O"] = 15
        elif metabolism == "mineral":
            cargo.ore = 20
            cargo.elements["Si"] = 15
        elif metabolism == "plasmic":
            cargo.elements["H"] = 20
            cargo.elements["He-3"] = 15
        elif metabolism == "umbral":
            cargo.organics = 10
            cargo.ore = 10
            cargo.elements["umbrite"] = 5

        cap_id = f"indigenous_{planet.id}_{kernel.cycle_count}"
        planet.active_indigenous_captain_id = cap_id

        # Clean name: e.g. "Stillcold Emissary Avalon"
        cap_name = f"{civ_name} Emissary {planet.name.split()[0]}"

        clade_by_metab = {
            "biotic": "BIOTIC",
            "mineral": "LITHIC",
            "plasmic": "PLASMIC",
            "cryogenic": "CRYOGENIC",
            "umbral": "ANARCHY",
        }
        cap_clade = clade_by_metab.get(metabolism, "BIOTIC")
        if "Cryo" in species_name or "still" in species_name:
            cap_clade = "CRYOGENIC"
        elif "lith" in species_name:
            cap_clade = "LITHIC"

        new_cap = Captain(
            id=cap_id,
            name=cap_name,
            is_ai=True,
            personality=personality,
            credits=crew_float,
            sector_id=planet.sector_id,
            species=species_name,
            metabolism=metabolism,
            clade=cap_clade,
            rank_tier=1,
            turns_left=200,
            ship=Ship(
                ship_type=ship_class,
                cargo=cargo,
                shields=ship_cfg["max_shields"],
                max_shields=ship_cfg["max_shields"],
                fighters=ship_cfg["max_fighters"],
            )
        )

        kernel.captains[cap_id] = new_cap
        matter.commission(new_cap)
        if planet.sector_id in kernel.sectors:
            kernel.sectors[planet.sector_id].captains.append(cap_id)

        if event_bus:
            event_bus.broadcast_radio(
                sender=planet.name,
                text=f"CIVILIGENESIS: Planetary civilization {civ_name} on {planet.name} has achieved spaceflight! Starship '{cap_name}' [{species_name}] launched into Sector {planet.sector_id:03d}.",
                channel="SYSTEM",
                sector_id=planet.sector_id,
            )
        kernel.action_logs.append(
            f"[CIVILIGENESIS] {civ_name} launched starship {cap_name} ({species_name}) into Sector {planet.sector_id:03d}."
        )
        return new_cap

    @classmethod
    def contribute_civic(
        cls,
        captain: Captain,
        planet: Planet,
        work_points: int,
        ore_amount: int = 0
    ) -> ActionResult:
        """
        Contribute funding and ore to the planetary civilization's current civic project.
        Accelerates project completion and awards captain score and civilization goodwill.
        """
        civ = getattr(planet, "civilization", None)
        if not civ or not civ.current_project:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_CIVIC_CONTRIBUTE,
                message=f"No active civic works commissioned on {planet.name}.",
            )

        if work_points <= 0 and ore_amount <= 0:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_CIVIC_CONTRIBUTE,
                message="Must provide credits or ore to fund civic construction.",
            )

        cost_cr = work_points * 5
        if captain.credits < cost_cr:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_CIVIC_CONTRIBUTE,
                message=f"Civic funding requires {cost_cr:,} Cr. You have {captain.credits:,} Cr.",
            )

        if ore_amount > 0 and captain.ship.cargo.unbonded("ORE") < ore_amount:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_CIVIC_CONTRIBUTE,
                message=f"Requires {ore_amount} Ore. Ship hold only contains {captain.ship.cargo.ore} Ore.",
            )

        captain.credits -= cost_cr
        cls._pay_contractor_sol(planet, cost_cr, to_vault=True)   # civic works are paid through the world's budget
        if ore_amount > 0:
            captain.ship.cargo.ore -= ore_amount
            planet.ore_silo += ore_amount                  # the colony's works draw on it from the silo

        total_work = work_points + (ore_amount * 2)
        civ.project_progress += total_work
        completed = False

        if civ.project_progress >= 100:
            completed_project = civ.current_project
            civ.civic_projects[completed_project] = civ.civic_projects.get(completed_project, 0) + 1
            CivilizationIntelligenceEngine._apply_project_effects(completed_project, planet)
            completed = True
            civ.current_project = CivilizationIntelligenceEngine.next_project(civ, planet, completed_project)
            civ.project_progress = 0
            captain.score += 200
            msg = (
                f"PROJECT COMPLETED! Contributed {cost_cr:,} Cr / {ore_amount} Ore to {civ.name}. "
                f"Completed '{completed_project}'! Next: '{civ.current_project}'."
            )
        else:
            captain.score += max(5, total_work // 2)
            msg = (
                f"Contributed to {civ.name}'s project '{civ.current_project}': +{total_work}% progress "
                f"(Status: {civ.project_progress}/100%)."
            )

        return ActionResult(
            success=True,
            action=ActionType.PLANET_CIVIC_CONTRIBUTE,
            message=msg,
            turns_spent=1,
            data={
                "project": civ.current_project,
                "progress": civ.project_progress,
                "completed": completed,
            },
            logs=[msg]
        )

    @classmethod
    def transfer_elements(
        cls,
        captain: Captain,
        planet: Planet,
        element_id: str,
        direction: str,
        amount: int
    ) -> ActionResult:
        """
        Transfer rare periodic elements between captain's cargo hold and planetary reserves.
        """
        element_id = element_id.lower()
        elem = PeriodicTable.get_element(element_id)
        elem_name = elem.name if elem else element_id.capitalize()

        if amount <= 0:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_ELEMENT_TRANSFER,
                message="Transfer amount must be greater than zero.",
            )

        reserves = getattr(planet, "element_reserves", {})

        if direction == "to_planet":
            in_hold = captain.ship.cargo.unbonded(element_id)
            if amount > in_hold:
                return ActionResult(
                    success=False,
                    action=ActionType.PLANET_ELEMENT_TRANSFER,
                    message=f"You only have {in_hold} units of {elem_name} in your hold.",
                )
            captain.ship.cargo.elements[element_id] -= amount
            if captain.ship.cargo.elements[element_id] == 0:
                del captain.ship.cargo.elements[element_id]
            reserves[element_id] = reserves.get(element_id, 0) + amount
            msg = f"Offloaded {amount} units of {elem_name} into {planet.name}'s elemental vault."
        else:
            in_vault = reserves.get(element_id, 0)
            if amount > in_vault:
                return ActionResult(
                    success=False,
                    action=ActionType.PLANET_ELEMENT_TRANSFER,
                    message=f"Planetary vault only has {in_vault} units of {elem_name}.",
                )
            if not captain.ship.cargo.can_fit(element_id, amount):
                max_u = captain.ship.cargo.available_units_for(element_id)
                return ActionResult(
                    success=False,
                    action=ActionType.PLANET_ELEMENT_TRANSFER,
                    message=f"Insufficient cargo holds! Available space for {elem_name}: {max_u} units.",
                )
            reserves[element_id] -= amount
            captain.ship.cargo.elements[element_id] = captain.ship.cargo.elements.get(element_id, 0) + amount
            msg = f"Loaded {amount} units of {elem_name} from {planet.name} into ship hold."

        return ActionResult(
            success=True,
            action=ActionType.PLANET_ELEMENT_TRANSFER,
            message=msg,
            turns_spent=0,
            data={"element_id": element_id, "amount": amount, "direction": direction},
            logs=[msg]
        )
