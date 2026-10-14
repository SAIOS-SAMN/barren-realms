"""
xylarium/kernel/omega_protocol.py

Project 5: Kardashev Type III Cosmic Ascendance ("The Omega Protocol")

The ultimate deep-time endgame:
  - Mind Uploading & Digital Consciousness: Transcending biological flesh into distributed
    stellar compute substrates, eliminating food and water needs while generating vast syntropy.
  - Metric Torsion Fields: Locally rewriting physical constants (gravitational constant G,
    speed of light c) to grant sector invulnerability and zero-burn jump navigation.
  - The Precursor Great Filter Awakening: Confronting the ancient cosmic filter that
    extinguished the Ancients in deep time.
"""

from dataclasses import asdict, dataclass, field
import random
from typing import Any, Dict, List, Optional

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


@dataclass
class AscendanceMatrix:
    owner_id: str
    uploaded_population: int = 0
    kardashev_level: float = 1.0
    syntropy_yield_per_cycle: int = 500

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AscendanceMatrix":
        return cls(**data)


@dataclass
class MetricTorsionField:
    id: str
    sector_id: int
    owner_id: str
    gravity_mod: float = 0.5  # Reduces local gravity well friction
    lightspeed_mod: float = 2.0  # Doubles local communication & reaction speed

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricTorsionField":
        return cls(**data)


class OmegaProtocolManager:
    """Manages Kardashev ascendance, metric torsion, and the Great Filter endgame."""

    def __init__(self) -> None:
        self.ascendance_matrices: Dict[str, AscendanceMatrix] = {}
        self.torsion_fields: Dict[int, MetricTorsionField] = {}
        self.great_filter_active: bool = False
        self.filter_threat_level: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ascendance_matrices": {k: v.to_dict() for k, v in self.ascendance_matrices.items()},
            "torsion_fields": {str(k): v.to_dict() for k, v in self.torsion_fields.items()},
            "great_filter_active": self.great_filter_active,
            "filter_threat_level": self.filter_threat_level,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "OmegaProtocolManager":
        mgr = cls()
        if not data:
            return mgr
        for k, v in data.get("ascendance_matrices", {}).items():
            mgr.ascendance_matrices[k] = AscendanceMatrix.from_dict(v)
        for k, v in data.get("torsion_fields", {}).items():
            mgr.torsion_fields[int(k)] = MetricTorsionField.from_dict(v)
        mgr.great_filter_active = data.get("great_filter_active", False)
        mgr.filter_threat_level = data.get("filter_threat_level", 0.0)
        return mgr

    def upload_population(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str
    ) -> ActionResult:
        """Uploads physical population of a colony into post-biological consciousness."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.OMEGA_UPLOAD_POPULATION,
                message=f"Planet '{planet_id}' not found.",
            )

        pop = getattr(planet, "population", 0)
        if pop <= 0:
            return ActionResult(
                success=False,
                action=ActionType.OMEGA_UPLOAD_POPULATION,
                message=f"{planet.name} has no biological population to transcend.",
            )

        cost = 30000
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.OMEGA_UPLOAD_POPULATION,
                message=f"Constructing the transcendence neural lattice requires {cost:,} credits.",
            )

        captain.credits -= cost
        uploaded = pop
        planet.population = 0  # Physical bodies dissolved into digital substrate

        matrix = self.ascendance_matrices.setdefault(captain.id, AscendanceMatrix(owner_id=captain.id))
        matrix.uploaded_population += uploaded
        matrix.kardashev_level = min(3.0, matrix.kardashev_level + 0.15)
        matrix.syntropy_yield_per_cycle += uploaded // 10

        return ActionResult(
            success=True,
            action=ActionType.OMEGA_UPLOAD_POPULATION,
            turns_spent=2,
            message=f"OMEGA TRANSCENDENCE COMPLETE: {uploaded:,} citizens of {planet.name} uploaded into the distributed substrate! Kardashev Level {matrix.kardashev_level:.2f}.",
            data={"matrix": matrix.to_dict()}
        )

    def anchor_metric_torsion(
        self,
        kernel: Any,
        captain: Captain,
    ) -> ActionResult:
        """Locally warps physical metric tensors in the captain's sector."""
        sector_id = captain.sector_id
        if sector_id in self.torsion_fields:
            return ActionResult(
                success=False,
                action=ActionType.OMEGA_METRIC_TORSION,
                message=f"A Metric Torsion Field is already anchored in Sector {sector_id}.",
            )

        cost = 45000
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.OMEGA_METRIC_TORSION,
                message=f"Anchoring a Metric Torsion Field requires {cost:,} credits.",
            )

        captain.credits -= cost
        tf = MetricTorsionField(
            id=f"TORSION-SEC-{sector_id:03d}",
            sector_id=sector_id,
            owner_id=captain.id,
        )
        self.torsion_fields[sector_id] = tf

        # Fortify all owned planets in sector
        for p in getattr(kernel.sectors.get(sector_id), "planets", []):
            p.shields = getattr(p, "shields", 0) + 500

        return ActionResult(
            success=True,
            action=ActionType.OMEGA_METRIC_TORSION,
            turns_spent=1,
            message=f"METRIC TORSION FIELD ANCHORED in Sector {sector_id}! Local spacetime rewritten. Defense grids fortified (+500 Shields).",
            data={"field": tf.to_dict()}
        )

    def awaken_great_filter(
        self,
        kernel: Any,
        captain: Captain
    ) -> ActionResult:
        """Awakens the ancient cosmic Great Filter reckoning across the galaxy."""
        if self.great_filter_active:
            return ActionResult(
                success=False,
                action=ActionType.OMEGA_AWAKEN_FILTER,
                message="The Great Filter is already awakened and scouring known space!",
            )

        self.great_filter_active = True
        self.filter_threat_level = 0.50

        if hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender="DEEP_TIME_BEACON",
                text="[WARNING: THE GREAT FILTER HAS AWAKENED] Primordial entropy vectors detected across all galactic sectors!",
                channel="COSMIC_BROADCAST",
            )
        kernel.action_logs.append("[OMEGA PROTOCOL] The Great Filter has awakened! Galactic civilization faces the final test.")

        return ActionResult(
            success=True,
            action=ActionType.OMEGA_AWAKEN_FILTER,
            turns_spent=2,
            message="THE GREAT FILTER IS UNLEASHED! Deep-time cosmological reckoning initiated across all sectors.",
        )

    def tick(self, kernel: Any) -> None:
        """Cycle tick: awards transcendence syntropy and advances endgame."""
        for matrix in self.ascendance_matrices.values():
            owner = kernel.captains.get(matrix.owner_id)
            if owner:
                owner.credits += matrix.syntropy_yield_per_cycle
