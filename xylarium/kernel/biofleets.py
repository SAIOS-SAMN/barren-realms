"""
xylarium.kernel.biofleets: Living Bio-Fleet Swarms & Tactical Standing Doctrines.

Implements living, genetically cultured bio-vessels (Void Mantas, Chitin Swarmers,
Abyssal Leviathans) that adapt armor resistances to damage, and assigns standing tactical
fleet doctrines (Convoy Escort, Orbital Pickets, Autonomous Swarm Harvesters).
"""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Sector


BIO_VESSEL_CLASSES = {
    "VOID_MANTA": {
        "name": "Void Manta Bio-Scout",
        "description": "High-agility pelagic bio-vessel with bioluminescent sensor baffles and sub-light reflex pods.",
        "cost_credits": 12000,
        "cost_metabolites": {"BIO_CHITIN": 2, "CRYOPROTECTANT": 2},
        "base_hp": 80,
        "base_regen": 8,
        "speed_factor": 1.5,
        "role": "RECON",
    },
    "CHITIN_SWARMER": {
        "name": "Chitin Swarmer Interceptor",
        "description": "Adaptive strike craft with layered chitin carapace that evolves resistance to kinetic and energy trauma.",
        "cost_credits": 24000,
        "cost_metabolites": {"BIO_CHITIN": 5, "XENOPROTEIN": 3},
        "base_hp": 160,
        "base_regen": 14,
        "speed_factor": 1.2,
        "role": "ESCORT",
    },
    "ABYSSAL_LEVIATHAN": {
        "name": "Abyssal Leviathan Bio-Dreadnought",
        "description": "Superheavy trans-somatic bio-ship grown with piezo-enzymes and radiotrophic melanin. Survives dimensional shear.",
        "cost_credits": 65000,
        "cost_metabolites": {"BIO_CHITIN": 10, "PIEZO_ENZYME": 4, "RADIOTROPHIC_MELANIN": 4},
        "base_hp": 450,
        "base_regen": 30,
        "speed_factor": 0.9,
        "role": "CAPITAL",
    },
}

FLEET_DOCTRINES = [
    "CONVOY_ESCORT",           # Escorts trade haulers, eliminates pirate ambush chance
    "ORBITAL_PICKET",          # Stations over world to repel siege assaults and enforce tariffs
    "AUTONOMOUS_SWARM_HARVEST",# Autonomously sweeps asteroid belts for minerals and returns to nursery
    "AUTONOMOUS_HARVESTER",    # Equivalent alias
]
TACTICAL_DOCTRINES = FLEET_DOCTRINES


@dataclass
class BioVessel:
    id: str
    vessel_class: str
    name: str
    owner_id: str
    sector_id: int
    current_hp: int
    max_hp: int
    regen_rate: int
    damage_adapted: Dict[str, float] = field(default_factory=lambda: {
        "KINETIC": 0.0,
        "THERMAL": 0.0,
        "PLASMIC": 0.0,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "vessel_class": self.vessel_class,
            "name": self.name,
            "owner_id": self.owner_id,
            "sector_id": self.sector_id,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "regen_rate": self.regen_rate,
            "damage_adapted": dict(self.damage_adapted),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BioVessel":
        return cls(**data)


@dataclass
class BioFleetWing:
    id: str
    name: str
    owner_id: str
    sector_id: int
    doctrine: str = "ORBITAL_PICKET"
    target_ref: Optional[str] = None   # Target hauler ID, planet ID, or belt ID
    vessels: List[BioVessel] = field(default_factory=list)

    def total_combat_rating(self) -> int:
        return sum(v.current_hp for v in self.vessels)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "owner_id": self.owner_id,
            "sector_id": self.sector_id,
            "doctrine": self.doctrine,
            "target_ref": self.target_ref,
            "vessels": [v.to_dict() for v in self.vessels],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BioFleetWing":
        d = dict(data)
        v_list = [BioVessel.from_dict(v) for v in d.pop("vessels", [])]
        wing = cls(**d)
        wing.vessels = v_list
        return wing


class BioFleetsManager:
    """
    Manages living bio-armadas, adaptive carapace evolution, and standing operational doctrines.
    """

    def __init__(self):
        self.wings: Dict[str, BioFleetWing] = {}
        self.next_vessel_id: int = 1
        self.next_wing_id: int = 101

    def culture_bio_vessel(
        self,
        kernel: Any,
        captain: Captain,
        vessel_class: str,
        wing_id: Optional[str] = None,
    ) -> ActionResult:
        """
        Cultures an evolving bio-vessel from xenobiological metabolites.
        """
        vc_up = vessel_class.strip().upper()
        if vc_up not in BIO_VESSEL_CLASSES:
            return ActionResult(
                success=False,
                action=ActionType.BIOFLEET_CULTURE_HULL,
                message=f"Invalid bio-vessel class '{vessel_class}'. Available: {', '.join(BIO_VESSEL_CLASSES.keys())}",
            )

        spec = BIO_VESSEL_CLASSES[vc_up]

        # Check credits
        cost_cr = spec["cost_credits"]
        if captain.credits < cost_cr:
            return ActionResult(
                success=False,
                action=ActionType.BIOFLEET_CULTURE_HULL,
                message=f"Insufficient credits for bio-incubation vat allocation ({captain.credits:,}/{cost_cr:,} Cr).",
            )

        # Check metabolites (or fallback to raw ORGANICS)
        cost_met = spec["cost_metabolites"]
        for met, req in cost_met.items():
            in_hold = captain.ship.cargo.elements.get(met, 0)
            if in_hold < req:
                org_held = captain.ship.cargo.organics + captain.ship.cargo.elements.get("ORGANICS", 0)
                if org_held >= req * 5:
                    continue
                return ActionResult(
                    success=False,
                    action=ActionType.BIOFLEET_CULTURE_HULL,
                    message=f"Insufficient xenobiological metabolite [{met}] in scientific holds ({in_hold}/{req} required, or {req*5} Organics).",
                )

        # Deduct
        captain.credits -= cost_cr
        for met, req in cost_met.items():
            in_hold = captain.ship.cargo.elements.get(met, 0)
            if in_hold >= req:
                captain.ship.cargo.elements[met] -= req
                if captain.ship.cargo.elements[met] <= 0:
                    del captain.ship.cargo.elements[met]
            else:
                org_needed = req * 5
                if captain.ship.cargo.organics >= org_needed:
                    captain.ship.cargo.organics -= org_needed
                elif "ORGANICS" in captain.ship.cargo.elements:
                    captain.ship.cargo.elements["ORGANICS"] -= org_needed
                    if captain.ship.cargo.elements["ORGANICS"] <= 0:
                        del captain.ship.cargo.elements["ORGANICS"]

        # Create vessel
        v_id = f"BIO-{self.next_vessel_id:04d}"
        self.next_vessel_id += 1
        vessel = BioVessel(
            id=v_id,
            vessel_class=vc_up,
            name=f"{spec['name']} #{v_id}",
            owner_id=captain.id,
            sector_id=captain.sector_id,
            current_hp=spec["base_hp"],
            max_hp=spec["base_hp"],
            regen_rate=spec["base_regen"],
        )

        # Place into wing
        if wing_id and wing_id in self.wings:
            wing = self.wings[wing_id]
        else:
            w_id = f"WING-{self.next_wing_id}"
            self.next_wing_id += 1
            wing = BioFleetWing(
                id=w_id,
                name=f"Bio-Swarm Fleet {w_id} ({captain.name})",
                owner_id=captain.id,
                sector_id=captain.sector_id,
                doctrine="ORBITAL_PICKET",
                target_ref=f"Sector-{captain.sector_id}",
            )
            self.wings[w_id] = wing

        wing.vessels.append(vessel)

        msg = (
            f"LIVING HULL CULTURED: {vessel.name} incubated successfully! "
            f"Allocated to {wing.name} (Strength: {wing.total_combat_rating()} HP, Doctrine: {wing.doctrine})."
        )

        return ActionResult(
            success=True,
            action=ActionType.BIOFLEET_CULTURE_HULL,
            message=msg,
            data={"vessel": vessel.to_dict(), "wing_id": wing.id},
        )

    def assign_doctrine(
        self,
        kernel: Any,
        captain: Captain,
        wing_id: str,
        doctrine: str,
        target_ref: Optional[str] = None,
    ) -> ActionResult:
        """
        Assigns standing operational doctrine to a bio-fleet wing.
        """
        if wing_id not in self.wings:
            return ActionResult(
                success=False,
                action=ActionType.BIOFLEET_ASSIGN_DOCTRINE,
                message=f"Bio-fleet wing '{wing_id}' not found.",
            )

        wing = self.wings[wing_id]
        if wing.owner_id != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.BIOFLEET_ASSIGN_DOCTRINE,
                message="You do not command this bio-fleet wing.",
            )

        doc_up = doctrine.strip().upper()
        if doc_up not in FLEET_DOCTRINES:
            return ActionResult(
                success=False,
                action=ActionType.BIOFLEET_ASSIGN_DOCTRINE,
                message=f"Invalid doctrine '{doctrine}'. Options: {', '.join(FLEET_DOCTRINES)}",
            )

        wing.doctrine = doc_up
        wing.target_ref = target_ref or f"Sector-{captain.sector_id}"

        msg = f"TACTICAL DOCTRINE ASSIGNED: {wing.name} reassigned to [{doc_up}] (Target: {wing.target_ref})."

        return ActionResult(
            success=True,
            action=ActionType.BIOFLEET_ASSIGN_DOCTRINE,
            message=msg,
            data=wing.to_dict(),
        )

    def tick(self, kernel: Any) -> None:
        """
        Applies passive regeneration and doctrine execution for bio-fleet wings.
        """
        for wing in self.wings.values():
            for v in wing.vessels:
                if v.current_hp < v.max_hp:
                    v.current_hp = min(v.max_hp, v.current_hp + v.regen_rate)

            if wing.doctrine in ["AUTONOMOUS_SWARM_HARVEST", "AUTONOMOUS_HARVESTER"]:
                # Autonomous harvest yield for owner
                owner = kernel.captains.get(wing.owner_id)
                if owner:
                    harvest_yield = len(wing.vessels) * 2
                    owner.credits += harvest_yield * 18
                    owner.ship.cargo.elements["ORGANICS"] = owner.ship.cargo.elements.get("ORGANICS", 0) + harvest_yield

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wings": {k: v.to_dict() for k, v in self.wings.items()},
            "next_vessel_id": self.next_vessel_id,
            "next_wing_id": self.next_wing_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BioFleetsManager":
        mgr = cls()
        mgr.next_vessel_id = data.get("next_vessel_id", 1)
        mgr.next_wing_id = data.get("next_wing_id", 101)
        for k, v in data.get("wings", {}).items():
            mgr.wings[k] = BioFleetWing.from_dict(v)
        return mgr
