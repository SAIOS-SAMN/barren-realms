"""
xylarium.kernel.megastructures: Deep-Space Megastructures, Derelict Salvage & Relic Physics.

Implements high-tier astro-engineering megaprojects (Dyson Swarms, Orbital Skyhooks,
Matrioshka Brains), procedural precursor space hulk boarding expeditions, and exotic
relic artifacts governed by non-singular spacetime physics.
"""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


MEGASTRUCTURE_CATALOG = {
    "DYSON_SWARM": {
        "name": "Stellar Photovoltaic Dyson Swarm",
        "description": "Orbital constellation of high-efficiency solar collector mirrors orbiting a star.",
        "cost_credits": 60000,
        "cost_elements": {"Fe": 80, "Si": 60},
        "effects": {"shield_grid_bonus_mw": 250, "solar_power_gw": 500.0, "antimatter_catalysis": True},
    },
    "ORBITAL_SKYHOOK": {
        "name": "Planetary Momentum-Exchange Skyhook",
        "description": "Tether superstructure in sub-orbital sweep cutting launch delta-v fuel costs to zero.",
        "cost_credits": 40000,
        "cost_elements": {"Ti": 70, "Fe": 50},
        "effects": {"zero_liftoff_burn": True, "port_throughput_boost_pct": 40.0},
    },
    "MATRIOSHKA_BRAIN": {
        "name": "Cryogenic Matrioshka Computing Cluster",
        "description": "Zero-kelvin nested computational shells surrounding a dead ember star to model deep reality.",
        "cost_credits": 90000,
        "cost_elements": {"Si": 100, "Ti": 50, "U": 25},
        "effects": {"research_points_per_cycle": 35, "epistemic_resonance_boost": 0.25},
    },
}


RELIC_ARTIFACTS = {
    "METRIC_LENS_CRYSTAL": {
        "name": "Riemannian Metric Lens Crystal",
        "description": "Exotic crystalline lens bending spacetime metric geodesics. Reduces hyperspace jump transit time by 50%.",
        "slot": "SHIP_CORE",
        "market_value": 25000,
    },
    "ZERO_POINT_SIPHON": {
        "name": "Quantum Vacuum Zero-Point Siphon",
        "description": "Torsion Casimir resonator tapping quantum ground state. Passively recharges +15 MW shield capacitor per cycle.",
        "slot": "SHIELD_MANIFOLD",
        "market_value": 30000,
    },
    "EPISTEMIC_CODEX_TABLET": {
        "name": "Progenitor Epistemic Codex Tablet",
        "description": "Crystalline tablet containing non-abelian SU(2) tensor axioms from Aeon 0. Grants +300 science research points.",
        "slot": "COGNITIVE_LAB",
        "market_value": 35000,
    },
}


@dataclass
class MegastructureProject:
    id: str
    structure_type: str
    name: str
    sector_id: int
    target_id: str             # star or planet ID
    builder_id: str
    progress_pct: float = 0.0
    status: str = "CONSTRUCTING" # "CONSTRUCTING", "OPERATIONAL"
    created_cycle: int = 0
    completed_cycle: Optional[int] = None
    effects: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "structure_type": self.structure_type,
            "name": self.name,
            "sector_id": self.sector_id,
            "target_id": self.target_id,
            "builder_id": self.builder_id,
            "progress_pct": round(self.progress_pct, 2),
            "status": self.status,
            "created_cycle": self.created_cycle,
            "completed_cycle": self.completed_cycle,
            "effects": dict(self.effects),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MegastructureProject":
        return cls(**data)


@dataclass
class DerelictSpaceHulk:
    id: str
    name: str
    sector_id: int
    hull_type: str              # "PRECURSOR_DREADNOUGHT", "CRYSTALLINE_LAB_ARK", "VOID_CONTAINMENT_BARGE"
    hazard_level: int = 2       # 1 to 5
    hazard_type: str = "RADIATION_LEAK" # "RADIATION_LEAK", "SUPERCOOLED_VACUUM", "CHRONO_SHEAR"
    salvaged: bool = False
    relic_stored: Optional[str] = "METRIC_LENS_CRYSTAL"
    raw_scrap: int = 50

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "sector_id": self.sector_id,
            "hull_type": self.hull_type,
            "hazard_level": self.hazard_level,
            "hazard_type": self.hazard_type,
            "salvaged": self.salvaged,
            "relic_stored": self.relic_stored,
            "raw_scrap": self.raw_scrap,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DerelictSpaceHulk":
        return cls(**data)


class MegastructuresManager:
    """
    Manages astro-engineering megastructures, derelict precursor hulks, and relic artifact physics.
    """

    def __init__(self):
        self.megastructures: Dict[str, MegastructureProject] = {}
        self.derelicts: Dict[str, DerelictSpaceHulk] = {}
        self.next_mega_id: int = 1
        self.next_hulk_id: int = 101

    @property
    def projects(self) -> Dict[str, MegastructureProject]:
        return self.megastructures

    @projects.setter
    def projects(self, val: Dict[str, MegastructureProject]) -> None:
        self.megastructures = val

    def seed_initial_derelicts(self, kernel: Any) -> None:
        """Seeds precursor space hulks across asteroid belts and frontier sectors."""
        relic_keys = list(RELIC_ARTIFACTS.keys())
        hulk_types = ["PRECURSOR_DREADNOUGHT", "CRYSTALLINE_LAB_ARK", "VOID_CONTAINMENT_BARGE"]
        hazards = ["RADIATION_LEAK", "SUPERCOOLED_VACUUM", "CHRONO_SHEAR"]

        # Seed 8 derelict hulks across the galaxy
        seed_sectors = [7, 12, 19, 27, 35, 48, 62, 85]
        for i, sid in enumerate(seed_sectors):
            if sid > len(kernel.sectors):
                continue
            h_id = f"HULK-{self.next_hulk_id}"
            self.next_hulk_id += 1
            hulk = DerelictSpaceHulk(
                id=h_id,
                name=f"Derelict Space Hulk {h_id} [{kernel.sectors[sid].name}]",
                sector_id=sid,
                hull_type=hulk_types[i % len(hulk_types)],
                hazard_level=(i % 3) + 1,
                hazard_type=hazards[i % len(hazards)],
                salvaged=False,
                relic_stored=relic_keys[i % len(relic_keys)],
                raw_scrap=random.randint(40, 90),
            )
            self.derelicts[h_id] = hulk

    def construct_megastructure(
        self,
        kernel: Any,
        captain: Captain,
        structure_type: str,
        target_id: Optional[str] = None,
    ) -> ActionResult:
        """
        Commences or contributes to an astro-engineering megastructure project.
        """
        st_up = structure_type.strip().upper()
        if st_up not in MEGASTRUCTURE_CATALOG:
            return ActionResult(
                success=False,
                action=ActionType.MEGASTRUCTURE_CONSTRUCT,
                message=f"Invalid megastructure type '{structure_type}'. Options: {', '.join(MEGASTRUCTURE_CATALOG.keys())}",
            )

        spec = MEGASTRUCTURE_CATALOG[st_up]
        sec_id = captain.sector_id

        # Verify credits
        c_cost = spec["cost_credits"] // 4  # Paid in quarterly tranches
        if captain.credits < c_cost:
            return ActionResult(
                success=False,
                action=ActionType.MEGASTRUCTURE_CONSTRUCT,
                message=f"Insufficient credits for engineering tranche ({captain.credits:,}/{c_cost:,} Cr required).",
            )

        # Verify elements
        cost_elems = spec["cost_elements"]
        for el, req in cost_elems.items():
            tranche_req = max(1, req // 4)
            in_hold = captain.ship.cargo.elements.get(el, 0) + captain.ship.cargo.elements.get(el.lower(), 0)
            if in_hold < tranche_req:
                return ActionResult(
                    success=False,
                    action=ActionType.MEGASTRUCTURE_CONSTRUCT,
                    message=f"Insufficient [{el}] in cargo holds ({in_hold}/{tranche_req} required for construction tranche).",
                )

        # Deduct tranche costs
        captain.credits -= c_cost
        for el, req in cost_elems.items():
            tranche_req = max(1, req // 4)
            if el in captain.ship.cargo.elements:
                captain.ship.cargo.elements[el] -= tranche_req
                if captain.ship.cargo.elements[el] <= 0:
                    del captain.ship.cargo.elements[el]
            elif el.lower() in captain.ship.cargo.elements:
                captain.ship.cargo.elements[el.lower()] -= tranche_req
                if captain.ship.cargo.elements[el.lower()] <= 0:
                    del captain.ship.cargo.elements[el.lower()]

        # Find existing project in sector or instantiate new one
        existing_proj = None
        for p in self.megastructures.values():
            if p.sector_id == sec_id and p.structure_type == st_up and p.status == "CONSTRUCTING":
                existing_proj = p
                break

        if existing_proj is None:
            p_id = f"MEGA-{self.next_mega_id:03d}"
            self.next_mega_id += 1
            existing_proj = MegastructureProject(
                id=p_id,
                structure_type=st_up,
                name=f"{spec['name']} ({kernel.sectors[sec_id].name})",
                sector_id=sec_id,
                target_id=target_id or f"Sector-{sec_id}",
                builder_id=captain.id,
                progress_pct=25.0,
                status="CONSTRUCTING",
                created_cycle=kernel.cycle_count,
                effects=spec["effects"],
            )
            self.megastructures[p_id] = existing_proj
            msg = f"ASTRO-ENGINEERING COMMENCED: {existing_proj.name} laid down! Tranche funded: 25.0% complete."
        else:
            existing_proj.progress_pct = min(100.0, existing_proj.progress_pct + 25.0)
            msg = f"CONSTRUCTION ADVANCED: {existing_proj.name} progress: {existing_proj.progress_pct:.1f}%."

        if existing_proj.progress_pct >= 100.0:
            existing_proj.status = "OPERATIONAL"
            existing_proj.completed_cycle = kernel.cycle_count
            msg += f" {existing_proj.name} is now FULLY OPERATIONAL! Active effects: {list(existing_proj.effects.keys())}."
            if hasattr(captain, "adjust_reputation"):
                captain.adjust_reputation("Federation", 10.0)

        return ActionResult(
            success=True,
            action=ActionType.MEGASTRUCTURE_CONSTRUCT,
            message=msg,
            data=existing_proj.to_dict(),
        )

    def board_derelict(
        self,
        kernel: Any,
        captain: Captain,
        hulk_id: str,
    ) -> ActionResult:
        """
        Boards an ancient precursor space hulk in the sector, tackling hazards
        and salvaging exotic relic artifacts.
        """
        if hulk_id not in self.derelicts:
            return ActionResult(
                success=False,
                action=ActionType.DERELICT_BOARD_EXPEDITION,
                message=f"Derelict Space Hulk '{hulk_id}' not found in cluster registry.",
            )

        hulk = self.derelicts[hulk_id]
        if captain.sector_id != hulk.sector_id:
            return ActionResult(
                success=False,
                action=ActionType.DERELICT_BOARD_EXPEDITION,
                message=f"You must navigate to Sector {hulk.sector_id:03d} to board {hulk.name}.",
            )

        if hulk.salvaged:
            return ActionResult(
                success=False,
                action=ActionType.DERELICT_BOARD_EXPEDITION,
                message=f"{hulk.name} has already been completely salvaged and picked clean.",
            )

        # Hazard check
        hazard_shield_drain = hulk.hazard_level * 15
        if captain.ship.shields < hazard_shield_drain:
            return ActionResult(
                success=False,
                action=ActionType.DERELICT_BOARD_EXPEDITION,
                message=f"Hull shields insufficient ({captain.ship.shields}/{hazard_shield_drain} MW) to breach {hulk.hazard_type} environmental field.",
            )

        captain.ship.shields = max(0, captain.ship.shields - hazard_shield_drain)
        hulk.salvaged = True

        # Salvage scrap elements
        scrap = hulk.raw_scrap
        captain.ship.cargo.elements["Fe"] = captain.ship.cargo.elements.get("Fe", 0) + (scrap // 2)
        captain.ship.cargo.elements["Ti"] = captain.ship.cargo.elements.get("Ti", 0) + (scrap // 4)

        # Salvage Relic Artifact
        relic_key = hulk.relic_stored
        relic_name = "Exotic Precursor Relic"
        if relic_key and relic_key in RELIC_ARTIFACTS:
            relic_name = RELIC_ARTIFACTS[relic_key]["name"]
            captain.ship.cargo.elements[relic_key] = captain.ship.cargo.elements.get(relic_key, 0) + 1
            # Apply active benefit
            if relic_key == "ZERO_POINT_SIPHON":
                captain.ship.max_shields += 25
                captain.ship.shields += 25
            elif relic_key == "EPISTEMIC_CODEX_TABLET":
                if hasattr(captain, "research_points"):
                    captain.research_points = getattr(captain, "research_points", 0) + 300

        msg = (
            f"BOARDING EXPEDITION SUCCESS: Breached {hulk.name}! "
            f"Overcame {hulk.hazard_type} (-{hazard_shield_drain} MW shields). "
            f"Salvaged +{scrap} scrap metals and recovered {relic_name} [{relic_key}]!"
        )

        return ActionResult(
            success=True,
            action=ActionType.DERELICT_BOARD_EXPEDITION,
            message=msg,
            data={"hulk_id": hulk_id, "relic": relic_key, "scrap": scrap},
        )

    def tick(self, kernel: Any) -> None:
        """Applies active effects of operational megastructures."""
        for mega in self.megastructures.values():
            if mega.status == "OPERATIONAL":
                eff = mega.effects
                if "research_points_per_cycle" in eff:
                    owner = kernel.captains.get(mega.builder_id)
                    if owner and hasattr(owner, "research_points"):
                        owner.research_points = getattr(owner, "research_points", 0) + eff["research_points_per_cycle"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "megastructures": {k: v.to_dict() for k, v in self.megastructures.items()},
            "derelicts": {k: v.to_dict() for k, v in self.derelicts.items()},
            "next_mega_id": self.next_mega_id,
            "next_hulk_id": self.next_hulk_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MegastructuresManager":
        mgr = cls()
        mgr.next_mega_id = data.get("next_mega_id", 1)
        mgr.next_hulk_id = data.get("next_hulk_id", 101)
        for k, v in data.get("megastructures", {}).items():
            mgr.megastructures[k] = MegastructureProject.from_dict(v)
        for k, v in data.get("derelicts", {}).items():
            mgr.derelicts[k] = DerelictSpaceHulk.from_dict(v)
        return mgr
