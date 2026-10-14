"""
xylarium/kernel/relic_foundry.py

Project Landing 1: The Syntropic Relic Foundry & Modular Artifact Engineering.

Elevates Precursor archaeology from descriptive relics into modular engineering:
  - Crystalline Relic Components:
    Tesseract Matrices, Tachyon Resonators, Entanglement Prisms, Zero-Point Dynamos,
    Chrono-Crystals, and Void Polarizers.
  - Masterwork Blueprints:
    1. Chrono-Slipdrive (Flagship module: zero-burn warp jumps & phase shields).
    2. Planetary World Engine (Planetary megastructure: 1.0 habitability, zero decoherence).
    3. Dimensional Coherence Anchor (Sector field: suppresses metric storms & collapses).
    4. Void Bridge Capacitor (Super-component required for Extragalactic Void Bridges).
    5. Syntropic Harvest Catalyst (Progenitor node: generates vast syntropy & credit yield).
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
import random
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


COMPONENT_TYPES = [
    "TESSERACT_MATRIX",
    "TACHYON_RESONATOR",
    "ENTANGLEMENT_PRISM",
    "ZERO_POINT_DYNAMO",
    "CHRONO_CRYSTAL",
    "VOID_POLARIZER",
]

BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    "CHRONO_SLIPDRIVE": {
        "name": "Chrono-Slipdrive",
        "category": "SHIP_EQUIPMENT",
        "cost_credits": 35000,
        "requirements": {
            "TESSERACT_MATRIX": 1,
            "TACHYON_RESONATOR": 2,
            "CHRONO_CRYSTAL": 1,
        },
        "description": "Zero-burn trans-sector phase displacement drive and +200 flagship shield capacity.",
    },
    "PLANETARY_WORLD_ENGINE": {
        "name": "Planetary World Engine",
        "category": "PLANETARY_STRUCTURE",
        "cost_credits": 50000,
        "requirements": {
            "ZERO_POINT_DYNAMO": 1,
            "ENTANGLEMENT_PRISM": 2,
            "TESSERACT_MATRIX": 1,
        },
        "description": "Permanently immunizes colony from decoherence, sets habitability to 1.0, and fortifies citadel (+1,000).",
    },
    "DIMENSIONAL_COHERENCE_ANCHOR": {
        "name": "Dimensional Coherence Anchor",
        "category": "SECTOR_BEACON",
        "cost_credits": 40000,
        "requirements": {
            "ENTANGLEMENT_PRISM": 2,
            "VOID_POLARIZER": 2,
            "ZERO_POINT_DYNAMO": 1,
        },
        "description": "Anchors sector spacetime metric: suppresses hyperlane torsion storms and soothes entropy strain (-40).",
    },
    "VOID_BRIDGE_CAPACITOR": {
        "name": "Void Bridge Capacitor",
        "category": "EXTRAGALACTIC_COMPONENT",
        "cost_credits": 60000,
        "requirements": {
            "VOID_POLARIZER": 2,
            "TESSERACT_MATRIX": 2,
            "TACHYON_RESONATOR": 1,
        },
        "description": "Sub-spatial megastructure accumulator necessary to bridge across the Extragalactic Void.",
    },
    "SYNTROPIC_HARVEST_CATALYST": {
        "name": "Syntropic Harvest Catalyst",
        "category": "PROGENITOR_DEVICE",
        "cost_credits": 45000,
        "requirements": {
            "CHRONO_CRYSTAL": 2,
            "ZERO_POINT_DYNAMO": 1,
            "ENTANGLEMENT_PRISM": 1,
        },
        "description": "Progenitor reactor generating +500 Syntropic Resilience and +1,000 credits per cycle.",
    },
}


@dataclass
class MasterworkArtifact:
    id: str
    blueprint_id: str
    name: str
    category: str
    owner_id: str
    equipped_to: Optional[str] = None  # "FLAGSHIP", "PLANET:<id>", "SECTOR:<id>"
    installed_sector: Optional[int] = None
    created_cycle: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MasterworkArtifact:
        return cls(**data)


class RelicFoundryManager:
    """Manages Precursor artifact component inventories, blueprint forging,
    and live installation across ships, worlds, and star sectors."""

    def __init__(self) -> None:
        # owner_id -> {component_name: count}
        self.inventories: Dict[str, Dict[str, int]] = {}
        # artifact_id -> MasterworkArtifact
        self.artifacts: Dict[str, MasterworkArtifact] = {}
        self.counter: int = 1

    def get_inventory(self, owner_id: str) -> Dict[str, int]:
        if owner_id not in self.inventories:
            self.inventories[owner_id] = {c: 0 for c in COMPONENT_TYPES}
        return self.inventories[owner_id]

    def grant_component(self, owner_id: str, component: str, count: int = 1) -> None:
        inv = self.get_inventory(owner_id)
        if component in inv:
            inv[component] += count

    def analyze_archaeological_finds(self, kernel: Any, captain: Captain) -> ActionResult:
        """Transmutes raw Precursor relics, excavation debris, or equipment into calibrated components."""
        inv = self.get_inventory(captain.id)
        relics_count = len(getattr(captain, "relics", []))
        artifacts_count = len(getattr(captain, "artifacts", []))

        gains: Dict[str, int] = {}
        # Grant components based on relics and exploration history
        rng = random.Random(kernel.seed + captain.turns + len(self.artifacts))
        pool = list(COMPONENT_TYPES)

        # Baseline extraction from active relics/artifacts or equipment
        conversions = max(2, relics_count + artifacts_count // 2)
        if captain.ship.cargo.equipment >= 5:
            captain.ship.cargo.equipment -= 5
            conversions += 2

        for _ in range(conversions):
            comp = rng.choice(pool)
            inv[comp] = inv.get(comp, 0) + 1
            gains[comp] = gains.get(comp, 0) + 1

        summary = ", ".join(f"{v}x {k}" for k, v in gains.items())
        kernel.action_logs.append(f"[FOUNDRY] Analyzed relic matrices: Refined {summary}.")

        return ActionResult(
            success=True,
            action=ActionType.FOUNDRY_ANALYZE,
            turns_spent=1,
            message=f"PRECURSOR ANALYSIS COMPLETE: Refined {summary} into quantum component inventory.",
            data={"gains": gains, "inventory": inv},
        )

    def forge_artifact(
        self,
        kernel: Any,
        captain: Captain,
        blueprint_id: str,
    ) -> ActionResult:
        """Forges a singular Masterwork Precursor Artifact from required components."""
        bp_key = blueprint_id.upper().strip()
        if bp_key not in BLUEPRINTS:
            return ActionResult(
                success=False,
                action=ActionType.FOUNDRY_FORGE,
                message=f"Unknown blueprint '{blueprint_id}'. Valid blueprints: {list(BLUEPRINTS.keys())}.",
            )

        bp = BLUEPRINTS[bp_key]
        cost = bp["cost_credits"]
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.FOUNDRY_FORGE,
                message=f"Forging '{bp['name']}' requires {cost:,} credits.",
            )

        inv = self.get_inventory(captain.id)
        reqs = bp["requirements"]
        missing = []
        for c_name, c_needed in reqs.items():
            if inv.get(c_name, 0) < c_needed:
                missing.append(f"{c_name} (Need {c_needed}, Have {inv.get(c_name, 0)})")

        if missing:
            return ActionResult(
                success=False,
                action=ActionType.FOUNDRY_FORGE,
                message=f"Missing required Precursor components: {', '.join(missing)}.",
            )

        # Consume credits and components
        captain.credits -= cost
        for c_name, c_needed in reqs.items():
            inv[c_name] -= c_needed

        art_id = f"ART-{bp_key}-{self.counter:03d}"
        self.counter += 1

        artifact = MasterworkArtifact(
            id=art_id,
            blueprint_id=bp_key,
            name=bp["name"],
            category=bp["category"],
            owner_id=captain.id,
            created_cycle=kernel.cycle_count,
        )
        self.artifacts[art_id] = artifact

        if hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender="SYNTROPIC_FOUNDRY",
                text=f"Masterwork Precursor Artifact '{artifact.name}' [{art_id}] has been forged by Captain {captain.name}!",
                channel="COSMIC_BROADCAST",
            )
        kernel.action_logs.append(f"[FOUNDRY] Forged '{artifact.name}' [{art_id}].")

        return ActionResult(
            success=True,
            action=ActionType.FOUNDRY_FORGE,
            turns_spent=2,
            message=f"MASTERWORK ARTIFACT FORGED: '{artifact.name}' [{art_id}] assembled in Foundry! Ready for deployment.",
            data={"artifact": artifact.to_dict()},
        )

    def equip_artifact(
        self,
        kernel: Any,
        captain: Captain,
        artifact_id: str,
        target_id: Optional[str] = None,
    ) -> ActionResult:
        """Installs/equips a forged artifact onto flagship, colony planet, or sector."""
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            return ActionResult(
                success=False,
                action=ActionType.FOUNDRY_EQUIP,
                message=f"Artifact '{artifact_id}' not found.",
            )

        if artifact.owner_id != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.FOUNDRY_EQUIP,
                message="You do not own this artifact.",
            )

        cat = artifact.category
        if cat == "SHIP_EQUIPMENT":
            artifact.equipped_to = "FLAGSHIP"
            captain.ship.shields += 200
            captain.ship.max_shields += 200
            msg = f"{artifact.name} installed on Flagship! (+200 Shields, Chrono displacement enabled)."

        elif cat == "PLANETARY_STRUCTURE":
            pid = target_id
            if not pid and kernel.sectors.get(captain.sector_id) and kernel.sectors[captain.sector_id].planets:
                pid = kernel.sectors[captain.sector_id].planets[0].id
            planet = kernel.get_planet(pid)
            if not planet:
                return ActionResult(
                    success=False,
                    action=ActionType.FOUNDRY_EQUIP,
                    message=f"Colony planet '{pid}' not found.",
                )
            artifact.equipped_to = f"PLANET:{planet.id}"
            planet.habitability = 1.0
            planet.citadel_level += 2
            planet.shields += 500
            # Immunize from decoherence if manager exists
            if hasattr(kernel, "decoherence_manager") and planet.id in kernel.decoherence_manager.records:
                kernel.decoherence_manager.records[planet.id].decoherence_index = 0.0
                kernel.decoherence_manager.records[planet.id].status = "STABLE"
            msg = f"{artifact.name} anchored on {planet.name}! Habitability locked to 1.0, citadel fortified."

        elif cat == "SECTOR_BEACON":
            sid = int(target_id) if target_id and target_id.isdigit() else captain.sector_id
            artifact.equipped_to = f"SECTOR:{sid}"
            artifact.installed_sector = sid
            # Reduce entropy strain if epoch manager exists
            if hasattr(kernel, "epoch_manager"):
                rec = kernel.epoch_manager.get_or_create_record(captain.id)
                rec.entropy_strain = max(0.0, rec.entropy_strain - 40.0)
                rec.syntropic_resilience += 50.0
            msg = f"{artifact.name} activated in Sector {sid}! Spacetime metric anchored, local entropy strain reduced (-40)."

        elif cat == "EXTRAGALACTIC_COMPONENT":
            artifact.equipped_to = "VOID_BRIDGE_ACCUMULATOR"
            msg = f"{artifact.name} energized as Void Bridge Core Accumulator! Ready for extragalactic transit."

        elif cat == "PROGENITOR_DEVICE":
            artifact.equipped_to = "PROGENITOR_LATTICE"
            if hasattr(kernel, "epoch_manager"):
                rec = kernel.epoch_manager.get_or_create_record(captain.id)
                rec.syntropic_resilience += 100.0
            msg = f"{artifact.name} integrated into Progenitor Syntropic Lattice! (+100 Syntropic Resilience)."

        else:
            artifact.equipped_to = "ACTIVE"
            msg = f"{artifact.name} deployed."

        kernel.action_logs.append(f"[FOUNDRY] Equipped '{artifact.name}' -> {artifact.equipped_to}.")
        return ActionResult(
            success=True,
            action=ActionType.FOUNDRY_EQUIP,
            turns_spent=1,
            message=msg,
            data={"artifact": artifact.to_dict()},
        )

    def dismantle_artifact(
        self,
        kernel: Any,
        captain: Captain,
        artifact_id: str,
    ) -> ActionResult:
        """Dismantles an artifact to recover half of its component materials."""
        artifact = self.artifacts.get(artifact_id)
        if not artifact or artifact.owner_id != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.FOUNDRY_DISMANTLE,
                message=f"Artifact '{artifact_id}' not found or unowned.",
            )

        bp = BLUEPRINTS.get(artifact.blueprint_id, {})
        reqs = bp.get("requirements", {})
        inv = self.get_inventory(captain.id)
        refunds: Dict[str, int] = {}

        for c_name, count in reqs.items():
            recovered = max(1, count // 2)
            inv[c_name] = inv.get(c_name, 0) + recovered
            refunds[c_name] = recovered

        del self.artifacts[artifact_id]
        summary = ", ".join(f"{v}x {k}" for k, v in refunds.items())

        return ActionResult(
            success=True,
            action=ActionType.FOUNDRY_DISMANTLE,
            turns_spent=1,
            message=f"ARTIFACT DISMANTLED: Salvaged {summary} into component vault.",
            data={"recovered": refunds},
        )

    def tick(self, kernel: Any) -> None:
        """Cycle tick: yields dividends and passive syntropy from active artifacts."""
        for art in self.artifacts.values():
            if art.blueprint_id == "SYNTROPIC_HARVEST_CATALYST" and art.equipped_to:
                owner = kernel.captains.get(art.owner_id)
                if owner:
                    owner.credits += 1000
                if hasattr(kernel, "epoch_manager"):
                    rec = kernel.epoch_manager.get_or_create_record(art.owner_id)
                    rec.syntropic_resilience += 15.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inventories": {k: dict(v) for k, v in self.inventories.items()},
            "artifacts": {k: v.to_dict() for k, v in self.artifacts.items()},
            "counter": self.counter,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RelicFoundryManager:
        mgr = cls()
        mgr.counter = int(data.get("counter", 1))
        mgr.inventories = {k: dict(v) for k, v in data.get("inventories", {}).items()}
        for k, v in data.get("artifacts", {}).items():
            mgr.artifacts[k] = MasterworkArtifact.from_dict(v)
        return mgr
