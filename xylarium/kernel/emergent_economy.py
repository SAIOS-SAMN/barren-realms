"""
xylarium/kernel/emergent_economy.py

Emergent Civilizational Economics & Multi-Planetary Realm Uplink Engine.

Models the organic bottom-up evolution of planetary economies:
  1. Monetary Tiers:
     - PRE_MONETARY_BARTER: Subsistence gift/barter economy. Cannot use or comprehend fiat credits.
     - COMMODITY_MONEY: Internal standard of value based on physical stores (grain, ingots, shells).
     - PLANETARY_FIAT: Dedicated local planetary currency and sovereign domestic treasury.
     - INTERSTELLAR_UPLINK: Multi-planetary spacefaring economy; uplinks into realm trade routes,
       seeds ISSE Automated Market Maker (AMM) liquidity pools, and issues sovereign bonds.
  2. Economic Metabolism & Cosmic Alignment:
     - BUILDER (Light / Syntropic, Alignment >= +0.3):
       Reinvests surplus into biosphere renewal, carrying capacity, public infrastructure,
       and sustainable production. Low entropy strain.
     - EXTRACTOR (Dark / Entropic, Alignment <= -0.3):
       Mercantilist resource strip-mining, short-term military/industrial surges, rapid
       depletion of minerals, severe ecological strain and collapse risk.
     - PRAGMATIST (Neutral, -0.3 < Alignment < +0.3):
       Balanced, adaptive trade posture.
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector
from xylarium.kernel import alignment as align_mod


class MonetaryTier(str, Enum):
    PRE_MONETARY_BARTER = "PRE_MONETARY_BARTER"
    COMMODITY_MONEY = "COMMODITY_MONEY"
    PLANETARY_FIAT = "PLANETARY_FIAT"
    INTERSTELLAR_UPLINK = "INTERSTELLAR_UPLINK"


class EconomicMetabolism(str, Enum):
    BUILDER = "BUILDER"
    EXTRACTOR = "EXTRACTOR"
    PRAGMATIST = "PRAGMATIST"


@dataclass
class PlanetaryEconomy:
    planet_id: str
    planet_name: str
    sector_id: int
    monetary_tier: MonetaryTier = MonetaryTier.PRE_MONETARY_BARTER
    metabolism: EconomicMetabolism = EconomicMetabolism.PRAGMATIST
    local_currency_code: Optional[str] = None
    local_treasury: int = 0
    barter_inventory: Dict[str, int] = field(default_factory=lambda: {"ORGANICS": 200, "ORE": 100, "EQUIPMENT": 10})
    reinvestment_rate: float = 0.5  # Builders >= 0.6, Extractors <= 0.2
    ecological_strain: float = 0.0  # 0.0 to 100.0
    is_uplinked: bool = False
    uplink_cycle: Optional[int] = None
    trade_routes_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["monetary_tier"] = self.monetary_tier.value
        d["metabolism"] = self.metabolism.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PlanetaryEconomy:
        data = dict(data)
        data["monetary_tier"] = MonetaryTier(data.get("monetary_tier", MonetaryTier.PRE_MONETARY_BARTER))
        data["metabolism"] = EconomicMetabolism(data.get("metabolism", EconomicMetabolism.PRAGMATIST))
        return cls(**data)


class EmergentEconomyManager:
    """Manages the bottom-up emergence of single-world economies into interstellar realm trade."""

    def __init__(self) -> None:
        self.economies: Dict[str, PlanetaryEconomy] = {}
        self.counter: int = 1

    def ensure_economy(self, kernel: Any, planet: Planet) -> PlanetaryEconomy:
        """Retrieves or instantiates the emergent economic profile for a planetary body."""
        pid = str(planet.id)
        if pid in self.economies:
            return self.economies[pid]

        # Determine initial monetary tier from civilization or native stage
        tier = MonetaryTier.PRE_MONETARY_BARTER
        metabolism = EconomicMetabolism.PRAGMATIST
        reinvestment = 0.5

        natives = getattr(planet, "natives", None)
        civ = getattr(planet, "civilization", None)

        if civ:
            # Established civilization
            align = float(getattr(civ, "alignment", 0.0) or 0.0)
            if align >= 0.25:
                metabolism = EconomicMetabolism.BUILDER
                reinvestment = 0.75
            elif align <= -0.25:
                metabolism = EconomicMetabolism.EXTRACTOR
                reinvestment = 0.15

            if civ.era_index >= 2 or planet.citadel_level >= 2:
                tier = MonetaryTier.INTERSTELLAR_UPLINK
            elif civ.era_index >= 1:
                tier = MonetaryTier.PLANETARY_FIAT
            else:
                tier = MonetaryTier.COMMODITY_MONEY
        elif natives:
            stage = int(natives.get("stage", 0))
            if stage <= 2:
                tier = MonetaryTier.PRE_MONETARY_BARTER
            elif stage <= 4:
                tier = MonetaryTier.COMMODITY_MONEY
            else:
                tier = MonetaryTier.PLANETARY_FIAT
        else:
            # Player or colony world
            if planet.citadel_level >= 1 or planet.population >= 5000:
                tier = MonetaryTier.INTERSTELLAR_UPLINK
            else:
                tier = MonetaryTier.COMMODITY_MONEY

        curr_code = f"CR-{planet.name[:4].upper()}" if tier in (MonetaryTier.PLANETARY_FIAT, MonetaryTier.INTERSTELLAR_UPLINK) else None
        uplinked = (tier == MonetaryTier.INTERSTELLAR_UPLINK)

        econ = PlanetaryEconomy(
            planet_id=pid,
            planet_name=planet.name,
            sector_id=planet.sector_id,
            monetary_tier=tier,
            metabolism=metabolism,
            local_currency_code=curr_code,
            local_treasury=planet.treasury,
            reinvestment_rate=reinvestment,
            is_uplinked=uplinked,
            uplink_cycle=kernel.cycle_count if uplinked else None,
        )
        self.economies[pid] = econ
        return econ

    def barter_exchange(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str,
        offered_good: str,
        offered_qty: int,
        requested_good: str,
    ) -> ActionResult:
        """Physical commodity barter with a pre-monetary or commodity-money civilization."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.EMERGENT_BARTER_EXCHANGE,
                message=f"Planet '{planet_id}' not found.",
            )

        econ = self.ensure_economy(kernel, planet)
        good_in = offered_good.upper().strip()
        good_out = requested_good.upper().strip()

        # Validate captain has the physical goods in ship cargo
        cargo = captain.ship.cargo
        avail = getattr(cargo, good_in.lower(), 0)
        if avail < offered_qty or offered_qty <= 0:
            return ActionResult(
                success=False,
                action=ActionType.EMERGENT_BARTER_EXCHANGE,
                message=f"You do not possess {offered_qty} {good_in} in your ship's cargo (Have: {avail}).",
            )

        # Validate planet has requested good in barter inventory
        stock = econ.barter_inventory.get(good_out, 0)
        # Exchange ratio based on utility: Equipment/medicines highly prized (1:3 or 1:2)
        ratio = 1.0
        if good_in == "EQUIPMENT" and good_out in ["ORGANICS", "ORE"]:
            ratio = 3.0
        elif good_in in ["ORGANICS", "ORE"] and good_out == "EQUIPMENT":
            ratio = 0.33

        expected_return = max(1, int(offered_qty * ratio))
        if stock < expected_return:
            return ActionResult(
                success=False,
                action=ActionType.EMERGENT_BARTER_EXCHANGE,
                message=f"{planet.name} barter stock lacks {expected_return} {good_out} (Available: {stock}).",
            )

        # Execute physical swap
        setattr(cargo, good_in.lower(), avail - offered_qty)
        current_out = getattr(cargo, good_out.lower(), 0)
        setattr(cargo, good_out.lower(), current_out + expected_return)

        econ.barter_inventory[good_in] = econ.barter_inventory.get(good_in, 0) + offered_qty
        econ.barter_inventory[good_out] -= expected_return

        # Barter increases economic sophistication and mutual trust
        align_mod.deed(kernel, captain, "fair_barter_exchange")
        captain.adjust_reputation("Indigenous", 5.0)

        msg = f"BARTER COMPLETED: Traded {offered_qty} {good_in} for {expected_return} {good_out} with the people of {planet.name}."
        kernel.action_logs.append(f"[BARTER] {captain.name} completed physical barter on {planet.name}.")

        return ActionResult(
            success=True,
            action=ActionType.EMERGENT_BARTER_EXCHANGE,
            turns_spent=1,
            message=msg,
            data={"traded_in": {good_in: offered_qty}, "received": {good_out: expected_return}},
        )

    def nurture_builder(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str,
        investment_credits: int = 50000,
    ) -> ActionResult:
        """Nurtures the civilization toward a BUILDER (Syntropic/Light) economic metabolism."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.EMERGENT_NURTURE_BUILDER,
                message=f"Planet '{planet_id}' not found.",
            )

        if captain.credits < investment_credits or investment_credits <= 0:
            return ActionResult(
                success=False,
                action=ActionType.EMERGENT_NURTURE_BUILDER,
                message=f"Requires {investment_credits:,} credits to sponsor sustainable infrastructure.",
            )

        captain.credits -= investment_credits
        econ = self.ensure_economy(kernel, planet)

        # Shift economic metabolism toward BUILDER
        econ.metabolism = EconomicMetabolism.BUILDER
        econ.reinvestment_rate = min(1.0, econ.reinvestment_rate + 0.25)
        econ.ecological_strain = max(0.0, econ.ecological_strain - 15.0)
        planet.habitability = min(1.5, planet.habitability + 0.05)
        planet.morale = min(100, planet.morale + 10)

        # Light Alignment Deed
        align_mod.deed(kernel, captain, "sponsor_builder_civilization")
        if hasattr(captain, "cosmic_alignment"):
            captain.cosmic_alignment = min(1.0, captain.cosmic_alignment + 0.05)

        kernel.action_logs.append(f"[BUILDER] {captain.name} nurtured Syntropic Builder metabolism on {planet.name}.")
        return ActionResult(
            success=True,
            action=ActionType.EMERGENT_NURTURE_BUILDER,
            turns_spent=1,
            message=f"BUILDER METABOLISM NURTURED: {planet.name} adopts syntropic circular economy. Reinvestment rate: {int(econ.reinvestment_rate*100)}%.",
            data={"metabolism": econ.metabolism.value, "reinvestment": econ.reinvestment_rate},
        )

    def extract_resources(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str,
    ) -> ActionResult:
        """Aggressive resource strip-mining (EXTRACTOR / Dark / Entropic act)."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.EMERGENT_EXTRACT_RESOURCES,
                message=f"Planet '{planet_id}' not found.",
            )

        econ = self.ensure_economy(kernel, planet)
        econ.metabolism = EconomicMetabolism.EXTRACTOR
        econ.reinvestment_rate = max(0.05, econ.reinvestment_rate - 0.2)
        econ.ecological_strain = min(100.0, econ.ecological_strain + 25.0)

        # Extract heavy minerals directly into captain holds
        ore_looted = 50
        captain.ship.cargo.stow("ore", ore_looted)
        captain.credits += 15000

        # Environmental degradation
        planet.habitability = max(0.2, planet.habitability - 0.1)
        planet.morale = max(10, planet.morale - 25)

        # Dark Alignment Deed
        align_mod.deed(kernel, captain, "predatory_resource_extraction")
        if hasattr(captain, "cosmic_alignment"):
            captain.cosmic_alignment = max(-1.0, captain.cosmic_alignment - 0.08)

        kernel.action_logs.append(f"[EXTRACTOR] {captain.name} strip-mined {planet.name} for short-term profit.")
        return ActionResult(
            success=True,
            action=ActionType.EMERGENT_EXTRACT_RESOURCES,
            turns_spent=1,
            message=f"PREDATORY EXTRACTION: Looted {ore_looted} Ore and 15,000 Cr. {planet.name} suffers ecological strain (+25%).",
            data={"ore_looted": ore_looted, "strain": econ.ecological_strain},
        )

    def trigger_uplink(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str,
    ) -> ActionResult:
        """Formalizes the Realm Uplink for a qualifying single-world civilization."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.EMERGENT_TRIGGER_UPLINK,
                message=f"Planet '{planet_id}' not found.",
            )

        econ = self.ensure_economy(kernel, planet)
        if econ.is_uplinked:
            return ActionResult(
                success=False,
                action=ActionType.EMERGENT_TRIGGER_UPLINK,
                message=f"{planet.name} is already uplinked into realm trade networks.",
            )

        # Qualification check: Population >= 10,000 OR Citadel Level >= 1 OR MonetaryTier == PLANETARY_FIAT
        qualifies = (
            planet.population >= 10000
            or planet.citadel_level >= 1
            or econ.monetary_tier == MonetaryTier.PLANETARY_FIAT
        )
        if not qualifies:
            return ActionResult(
                success=False,
                action=ActionType.EMERGENT_TRIGGER_UPLINK,
                message=f"{planet.name} does not yet meet spacefaring graduation criteria (Requires 10k Pop or Citadel Outpost).",
            )

        # Formalize the Uplink
        econ.monetary_tier = MonetaryTier.INTERSTELLAR_UPLINK
        econ.is_uplinked = True
        econ.uplink_cycle = kernel.cycle_count
        if not econ.local_currency_code:
            econ.local_currency_code = f"CR-{planet.name[:4].upper()}"

        # Seed initial exchange parity and sovereign counterparty status
        endowment = 100000
        planet.treasury += endowment
        econ.local_treasury = planet.treasury

        # Open sovereign trade counterparty
        econ.trade_routes_count = 2

        if hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender="ISSE_EXCHANGE",
                text=f"SOVEREIGN REALM UPLINK: {planet.name} has entered interstellar commerce! Currency '{econ.local_currency_code}' listed on ISSE exchange.",
                channel="COSMIC_BROADCAST",
            )
        kernel.action_logs.append(f"[UPLINK] {planet.name} achieved full Realm Uplink into interstellar trade routes.")

        return ActionResult(
            success=True,
            action=ActionType.EMERGENT_TRIGGER_UPLINK,
            turns_spent=1,
            message=f"REALM UPLINK COMPLETE: {planet.name} is now a sovereign counterparty in interstellar trade. Listed currency: {econ.local_currency_code}.",
            data={"currency": econ.local_currency_code, "treasury": planet.treasury},
        )

    def tick(self, kernel: Any) -> None:
        """Cycle tick: evolves monetary tiers, ecological strain, and checks multi-planetary status."""
        for sec in kernel.sectors.values():
            for planet in getattr(sec, "planets", []):
                pid = str(planet.id)
                if pid not in self.economies:
                    continue

                econ = self.economies[pid]

                # 1. Builder vs Extractor ecological metabolism dynamics
                if econ.metabolism == EconomicMetabolism.BUILDER:
                    # Circular economy steadily soothes ecological strain
                    econ.ecological_strain = max(0.0, econ.ecological_strain - 0.2)
                    planet.habitability = min(1.5, planet.habitability + 0.002)
                    econ.barter_inventory["ORGANICS"] = econ.barter_inventory.get("ORGANICS", 0) + 5
                elif econ.metabolism == EconomicMetabolism.EXTRACTOR:
                    # Relentless strip-mining accumulates ecological strain
                    econ.ecological_strain = min(100.0, econ.ecological_strain + 0.4)
                    if econ.ecological_strain > 75.0:
                        planet.habitability = max(0.2, planet.habitability - 0.005)
                        planet.morale = max(10, planet.morale - 1)

                # 2. Natural Monetary Tier advancement
                if econ.monetary_tier == MonetaryTier.PRE_MONETARY_BARTER:
                    if planet.population >= 5000:
                        econ.monetary_tier = MonetaryTier.COMMODITY_MONEY
                elif econ.monetary_tier == MonetaryTier.COMMODITY_MONEY:
                    if planet.population >= 15000:
                        econ.monetary_tier = MonetaryTier.PLANETARY_FIAT
                        if not econ.local_currency_code:
                            econ.local_currency_code = f"CR-{planet.name[:4].upper()}"

                # 3. Multi-planetary Realm Uplink check
                if not econ.is_uplinked:
                    # Check if civilization or owner holds worlds across 2+ sectors or has citadel >= 1
                    owner = getattr(planet, "owner_id", None)
                    multi_world = False
                    if owner:
                        owned_count = sum(
                            1 for s in kernel.sectors.values()
                            for p in getattr(s, "planets", [])
                            if getattr(p, "owner_id", None) == owner
                        )
                        multi_world = (owned_count >= 2)

                    if multi_world or planet.citadel_level >= 1 or planet.population >= 25000:
                        econ.monetary_tier = MonetaryTier.INTERSTELLAR_UPLINK
                        econ.is_uplinked = True
                        econ.uplink_cycle = kernel.cycle_count
                        if not econ.local_currency_code:
                            econ.local_currency_code = f"CR-{planet.name[:4].upper()}"
                        econ.trade_routes_count = max(1, econ.trade_routes_count + 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "economies": {k: v.to_dict() for k, v in self.economies.items()},
            "counter": self.counter,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EmergentEconomyManager:
        mgr = cls()
        mgr.counter = int(data.get("counter", 1))
        for k, v in data.get("economies", {}).items():
            mgr.economies[k] = PlanetaryEconomy.from_dict(v)
        return mgr
