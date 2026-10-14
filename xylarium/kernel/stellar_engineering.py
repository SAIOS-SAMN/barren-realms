"""
xylarium/kernel/stellar_engineering.py

Project 3: Deep-Space Stellar Engineering & Star-Lifting ("The Solar Forge")

Allows direct engineering of stellar bodies:
  - Star-Lifting Arrays: Magnetic siphons that strip hydrogen, helium, and heavy metals
    directly from stellar photospheres, providing inexhaustible industrial matter.
  - Proto-Star Ignition: Detonating catalysts into cold Brown Dwarfs or Supernova remnants
    to ignite main-sequence suns and warm outer frozen worlds into habitable zones.
  - Coronal Laser Emitters: Channeling magnetic reconnection flares to disable planetary
    shields across targeted hostile sectors.
"""

from dataclasses import asdict, dataclass, field
from fractions import Fraction as F
from typing import Any, Dict, List, Optional

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


@dataclass
class StarLifter:
    id: str
    sector_id: int
    owner_id: str
    extraction_rate_ore: int = 40
    extraction_rate_fuel: int = 80
    total_ore_extracted: int = 0
    total_fuel_extracted: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StarLifter":
        return cls(**data)


@dataclass
class StellarIgnitionProject:
    id: str
    sector_id: int
    original_class: str
    new_class: str
    ignited: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StellarIgnitionProject":
        return cls(**data)


class StellarEngineeringManager:
    """Manages star-lifting, proto-star ignition, and solar manipulation arrays."""

    def __init__(self) -> None:
        self.star_lifters: Dict[str, StarLifter] = {}
        self.ignition_projects: Dict[int, StellarIgnitionProject] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "star_lifters": {k: v.to_dict() for k, v in self.star_lifters.items()},
            "ignition_projects": {str(k): v.to_dict() for k, v in self.ignition_projects.items()},
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "StellarEngineeringManager":
        mgr = cls()
        if not data:
            return mgr
        for k, v in data.get("star_lifters", {}).items():
            mgr.star_lifters[k] = StarLifter.from_dict(v)
        for k, v in data.get("ignition_projects", {}).items():
            mgr.ignition_projects[int(k)] = StellarIgnitionProject.from_dict(v)
        return mgr

    def deploy_star_lifter(self, kernel: Any, captain: Captain) -> ActionResult:
        """Deploys an orbital magnetic star-lifter in current sector."""
        sector_id = captain.sector_id
        lifter_id = f"LIFTER-SEC-{sector_id:03d}"
        if lifter_id in self.star_lifters:
            return ActionResult(
                success=False,
                action=ActionType.STELLAR_DEPLOY_LIFTER,
                message=f"A Star-Lifter is already operating around Sector {sector_id}'s star.",
            )

        sol_cost = 20000
        equip_cost = 25
        if captain.credits < sol_cost:
            return ActionResult(
                success=False,
                action=ActionType.STELLAR_DEPLOY_LIFTER,
                message=f"Deploying a Star-Lifter requires {sol_cost:,} credits.",
            )
        if captain.ship.cargo.equipment < equip_cost:
            return ActionResult(
                success=False,
                action=ActionType.STELLAR_DEPLOY_LIFTER,
                message=f"Deploying a Star-Lifter requires {equip_cost} Equipment in cargo.",
            )

        captain.credits -= sol_cost
        captain.ship.cargo.equipment -= equip_cost

        lifter = StarLifter(
            id=lifter_id,
            sector_id=sector_id,
            owner_id=captain.id,
        )
        self.star_lifters[lifter_id] = lifter

        return ActionResult(
            success=True,
            action=ActionType.STELLAR_DEPLOY_LIFTER,
            turns_spent=1,
            message=f"STAR-LIFTER DEPLOYED in Sector {sector_id}! Magnetic siphons established. Harvesting solar mass (+40 Ore, +80 Fuel per cycle).",
            data={"lifter": lifter.to_dict()}
        )

    def ignite_protostar(self, kernel: Any, captain: Captain) -> ActionResult:
        """Ignites a dim Brown Dwarf or Supernova Remnant into a radiant G-class star."""
        sector = kernel.sectors.get(captain.sector_id)
        if not sector:
            return ActionResult(
                success=False,
                action=ActionType.STELLAR_IGNITE_PROTOSTAR,
                message="Invalid sector.",
            )

        star_class = getattr(sector, "star_class", "G-class")
        if star_class not in ("Brown dwarf", "Supernova remnant", "M-class"):
            return ActionResult(
                success=False,
                action=ActionType.STELLAR_IGNITE_PROTOSTAR,
                message=f"Sector {sector.id}'s star is already a high-energy {star_class}. Only dim stars (Brown dwarf, Supernova remnant, M-class) can be ignited.",
            )

        sol_cost = 35000
        if captain.credits < sol_cost:
            return ActionResult(
                success=False,
                action=ActionType.STELLAR_IGNITE_PROTOSTAR,
                message=f"Proto-star fusion ignition requires {sol_cost:,} credits for antimatter catalysts.",
            )

        captain.credits -= sol_cost
        old_class = star_class
        sector.star_class = "G-class"

        # Warm cold and frozen worlds in sector
        warmed = 0
        for p in getattr(sector, "planets", []):
            if p.planet_type in ("Ice", "Frozen", "Barren"):
                p.planet_type = "Terran"
                p.name = f"{p.name} (Warmed)"
                warmed += 1

        proj = StellarIgnitionProject(
            id=f"IGNITE-SEC-{sector.id:03d}",
            sector_id=sector.id,
            original_class=old_class,
            new_class="G-class",
            ignited=True,
        )
        self.ignition_projects[sector.id] = proj

        return ActionResult(
            success=True,
            action=ActionType.STELLAR_IGNITE_PROTOSTAR,
            turns_spent=2,
            message=f"STELLAR IGNITION SUCCESSFUL! {old_class} ignited into a radiant G-class Sun! Warmed {warmed} worlds into temperate Terran biospheres.",
            data={"project": proj.to_dict()}
        )

    def fire_coronal_burst(
        self,
        kernel: Any,
        captain: Captain,
        target_sector: int
    ) -> ActionResult:
        """Discharges a channeled coronal mass ejection into a target adjacent sector."""
        origin = captain.sector_id
        sec_orig = kernel.sectors.get(origin)
        sec_targ = kernel.sectors.get(target_sector)

        if not sec_orig or not sec_targ or target_sector not in sec_orig.warps:
            return ActionResult(
                success=False,
                action=ActionType.STELLAR_CORONAL_BURST,
                message=f"Sector {target_sector} is not directly adjacent to Sector {origin}.",
            )

        sol_cost = 12000
        if captain.credits < sol_cost:
            return ActionResult(
                success=False,
                action=ActionType.STELLAR_CORONAL_BURST,
                message=f"Firing a Coronal Mass Ejection requires {sol_cost:,} credits.",
            )

        captain.credits -= sol_cost

        # Disable planetary shields and drain fighters in target sector
        hit_planets = 0
        for p in getattr(sec_targ, "planets", []):
            p.shields = max(0, getattr(p, "shields", 0) - 150)
            p.fighters = max(0, getattr(p, "fighters", 0) - 25)
            hit_planets += 1

        return ActionResult(
            success=True,
            action=ActionType.STELLAR_CORONAL_BURST,
            turns_spent=1,
            message=f"CORONAL BURST DISCHARGED! Channeled solar flare swept through Sector {target_sector}, frying planetary defense grids (-150 shields on {hit_planets} worlds)!",
        )

    def tick(self, kernel: Any) -> None:
        """Cycle simulation tick: extracts stellar matter from stars."""
        for lifter in self.star_lifters.values():
            owner = kernel.captains.get(lifter.owner_id)
            if not owner:
                continue
            # Deliver harvest directly to owner's cargo or credits
            stowed_ore = owner.ship.cargo.stow("ORE", lifter.extraction_rate_ore)
            lifter.total_ore_extracted += lifter.extraction_rate_ore
            lifter.total_fuel_extracted += lifter.extraction_rate_fuel
            # Award fuel or credit equivalent
            owner.credits += lifter.extraction_rate_fuel * 10
