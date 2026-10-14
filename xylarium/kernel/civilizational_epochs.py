"""
xylarium/kernel/civilizational_epochs.py

Non-Terminal Macro-Evolution & Civilizational Epochal Transitions.

Realigns the cosmic endgame into an ongoing evolutionary continuum:
  - Epoch I: THE SOVEREIGN EXPANSION
    Territorial colonization, resource extraction, warp trade, and military hegemony.
    Bound by Landis percolation stalls and relativistic light-cone horizons.
  - Epoch II: THE GREAT FILTER (THE BOTTLENECK)
    Thermodynamic entropy strain, stellar exhaustion, and systemic colonial decoherence.
    Civilizations face the physical and ecological limits of unconstrained growth.
  - Epoch III: DEEP-TIME STEWARDSHIP (BECOMING THE ANCIENTS)
    Transcendence of the bottleneck through syntropic metamorphosis.
    The player transitions into the role of a Progenitor/Steward:
      1. Seeding young sapient clades on prebiotic worlds.
      2. Stabilizing dying stellar cores and tempering solar superflares.
      3. Planting Precursor Beacons and Relics for younger spacefarers.
      4. Discharging Syntropic Harmonic Pulses to soothe galactic entropy.
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


class EpochPhase(str, Enum):
    EXPANSION = "EXPANSION"
    FILTER_TRANSIT = "FILTER_TRANSIT"
    STEWARDSHIP = "STEWARDSHIP"


@dataclass
class EpochRecord:
    player_id: str
    phase: EpochPhase = EpochPhase.EXPANSION
    entropy_strain: float = 0.0
    syntropic_resilience: float = 0.0
    bottleneck_cycles: int = 0
    nascent_worlds_seeded: int = 0
    stellar_cores_stabilized: int = 0
    precursor_beacons_planted: int = 0
    syntropic_pulses_fired: int = 0
    title: str = "Sovereign Commander"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "phase": self.phase.value if isinstance(self.phase, EpochPhase) else str(self.phase),
            "entropy_strain": round(self.entropy_strain, 2),
            "syntropic_resilience": round(self.syntropic_resilience, 2),
            "bottleneck_cycles": self.bottleneck_cycles,
            "nascent_worlds_seeded": self.nascent_worlds_seeded,
            "stellar_cores_stabilized": self.stellar_cores_stabilized,
            "precursor_beacons_planted": self.precursor_beacons_planted,
            "syntropic_pulses_fired": self.syntropic_pulses_fired,
            "title": self.title,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EpochRecord:
        raw_phase = data.get("phase", EpochPhase.EXPANSION.value)
        try:
            phase = EpochPhase(raw_phase)
        except ValueError:
            phase = EpochPhase.EXPANSION

        return cls(
            player_id=data["player_id"],
            phase=phase,
            entropy_strain=float(data.get("entropy_strain", 0.0)),
            syntropic_resilience=float(data.get("syntropic_resilience", 0.0)),
            bottleneck_cycles=int(data.get("bottleneck_cycles", 0)),
            nascent_worlds_seeded=int(data.get("nascent_worlds_seeded", 0)),
            stellar_cores_stabilized=int(data.get("stellar_cores_stabilized", 0)),
            precursor_beacons_planted=int(data.get("precursor_beacons_planted", 0)),
            syntropic_pulses_fired=int(data.get("syntropic_pulses_fired", 0)),
            title=data.get("title", "Sovereign Commander"),
        )


class CivilizationalEpochManager:
    """Orchestrates civilizational macro-epochs, the Great Filter bottleneck,
    and post-filter deep-time stewardship."""

    def __init__(self) -> None:
        self.records: Dict[str, EpochRecord] = {}
        self.global_entropy_strain: float = 0.0
        self.global_syntropy_level: float = 0.0

    def get_or_create_record(self, player_id: str) -> EpochRecord:
        if player_id not in self.records:
            self.records[player_id] = EpochRecord(player_id=player_id)
        return self.records[player_id]

    def assess_civilization(self, kernel: Any, captain: Captain) -> Dict[str, Any]:
        """Evaluates thermodynamic entropy strain vs syntropic resilience for a realm."""
        rec = self.get_or_create_record(captain.id)

        # 1. Entropy calculation from territorial load & physical disruption
        owned_worlds = 0
        total_pop = 0
        decohered_worlds = 0

        for s in kernel.sectors.values():
            for p in getattr(s, "planets", []):
                if getattr(p, "owner_id", None) == captain.id:
                    owned_worlds += 1
                    total_pop += getattr(p, "population", 0)
                    if hasattr(kernel, "decoherence_manager"):
                        d_rec = kernel.decoherence_manager.records.get(p.id)
                        if d_rec and d_rec.decoherence_index >= 0.50:
                            decohered_worlds += 1

        active_lifters = 0
        if hasattr(kernel, "stellar_manager"):
            for sl in kernel.stellar_manager.star_lifters.values():
                if sl.owner_id == captain.id:
                    active_lifters += 1

        torsion_fields = 0
        uploaded_pop = 0
        filter_active = False
        if hasattr(kernel, "omega_manager"):
            filter_active = kernel.omega_manager.great_filter_active
            for tf in kernel.omega_manager.torsion_fields.values():
                if tf.owner_id == captain.id:
                    torsion_fields += 1
            matrix = kernel.omega_manager.ascendance_matrices.get(captain.id)
            if matrix:
                uploaded_pop = matrix.uploaded_population

        # Entropy strain formula:
        # Colonial sprawl + unconstrained star-lifting + unshielded torsion + decoherence
        entropy = (
            (owned_worlds * 6.0)
            + (active_lifters * 15.0)
            + (torsion_fields * 12.0)
            + (decohered_worlds * 18.0)
            + (captain.turns * 0.05)
        )
        if filter_active:
            entropy += 50.0

        # 2. Syntropic resilience calculation
        # Mind lattices + megastructures + terraformed biospheres + coherence stabilization
        megastructures = 0
        if hasattr(kernel, "megastructure_manager"):
            for m in kernel.megastructure_manager.structures.values():
                if m.owner_id == captain.id and m.stage >= 3:
                    megastructures += 1

        syntropy = (
            (uploaded_pop // 200 * 5.0)
            + (megastructures * 35.0)
            + (rec.nascent_worlds_seeded * 25.0)
            + (rec.stellar_cores_stabilized * 30.0)
            + (rec.syntropic_pulses_fired * 15.0)
            + (rec.precursor_beacons_planted * 20.0)
            + (captain.credits // 50000 * 2.0)
        )

        rec.entropy_strain = round(max(rec.entropy_strain, entropy), 2)
        if rec.phase == EpochPhase.FILTER_TRANSIT:
            rec.entropy_strain = max(100.0, rec.entropy_strain)
        rec.syntropic_resilience = round(max(rec.syntropic_resilience, syntropy), 2)

        # Automatic bottleneck trigger: unconstrained growth breaches thermodynamic limits
        if rec.phase == EpochPhase.EXPANSION and (rec.entropy_strain >= 100.0 or filter_active):
            rec.phase = EpochPhase.FILTER_TRANSIT
            rec.entropy_strain = max(100.0, rec.entropy_strain)
            rec.title = "Struggling Sovereign"
            if hasattr(kernel, "event_bus"):
                kernel.event_bus.broadcast_radio(
                    sender="CIVILIZATIONAL_MONITOR",
                    text=f"[CIVILIZATIONAL BOTTLENECK] Sovereign {captain.name}'s realm has breached the thermodynamic limit! The Great Filter transit has begun.",
                    channel="COSMIC_BROADCAST",
                )
            kernel.action_logs.append(f"[EPOCH TRANSIT] {captain.name} has entered Epoch II: The Great Filter Bottleneck.")

        can_metamorphose = (
            rec.phase == EpochPhase.FILTER_TRANSIT
            and rec.syntropic_resilience >= rec.entropy_strain
            and rec.syntropic_resilience >= 100.0
        )

        return {
            "player_id": captain.id,
            "phase": rec.phase.value,
            "title": rec.title,
            "entropy_strain": rec.entropy_strain,
            "syntropic_resilience": rec.syntropic_resilience,
            "can_metamorphose": can_metamorphose,
            "owned_worlds": owned_worlds,
            "uploaded_pop": uploaded_pop,
            "active_lifters": active_lifters,
            "megastructures": megastructures,
            "decohered_worlds": decohered_worlds,
            "nascent_worlds_seeded": rec.nascent_worlds_seeded,
            "stellar_cores_stabilized": rec.stellar_cores_stabilized,
            "precursor_beacons_planted": rec.precursor_beacons_planted,
        }

    def initiate_metamorphosis(self, kernel: Any, captain: Captain) -> ActionResult:
        """Surmounts the Great Filter hurdle, transitioning into Epoch III: Deep-Time Stewardship."""
        rec = self.get_or_create_record(captain.id)
        status = self.assess_civilization(kernel, captain)

        if rec.phase == EpochPhase.STEWARDSHIP:
            return ActionResult(
                success=False,
                action=ActionType.EPOCH_INITIATE_METAMORPHOSIS,
                message=f"{captain.name} has already undergone Civilizational Metamorphosis into Deep-Time Stewardship.",
            )

        if rec.phase != EpochPhase.FILTER_TRANSIT:
            return ActionResult(
                success=False,
                action=ActionType.EPOCH_INITIATE_METAMORPHOSIS,
                message="Metamorphosis Accord can only be initiated during Epoch II (Filter Transit).",
            )

        if rec.syntropic_resilience < rec.entropy_strain or rec.syntropic_resilience < 100.0:
            return ActionResult(
                success=False,
                action=ActionType.EPOCH_INITIATE_METAMORPHOSIS,
                message=f"Thermodynamic collapse imminent! Syntropic resilience ({rec.syntropic_resilience:.1f}) is insufficient to counter entropy strain ({rec.entropy_strain:.1f}) [Need >= {max(100.0, rec.entropy_strain):.1f}]. Upload minds or construct megastructures first.",
            )

        # Successful Metamorphosis!
        rec.phase = EpochPhase.STEWARDSHIP
        rec.title = "Progenitor of Deep Time"
        rec.entropy_strain = max(0.0, rec.entropy_strain - 50.0)

        # Deactivate destructive Filter state in omega manager if active
        if hasattr(kernel, "omega_manager"):
            kernel.omega_manager.great_filter_active = False

        if hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender="PROGENITOR_CHAMBER",
                text=f"[CIVILIZATIONAL METAMORPHOSIS COMPLETE] Sovereign {captain.name} has surmounted the Great Filter! Welcome to Epoch III: Deep-Time Stewardship.",
                channel="COSMIC_BROADCAST",
            )
        kernel.action_logs.append(f"[METAMORPHOSIS] {captain.name} transcended the Great Filter into Deep-Time Stewardship!")

        return ActionResult(
            success=True,
            action=ActionType.EPOCH_INITIATE_METAMORPHOSIS,
            turns_spent=3,
            message=(
                f"THE GREAT FILTER IS SURMOUNTED! {captain.name} has ascended to '{rec.title}'. "
                "You are no longer an exploitative sovereign; you are now the Ancient Precursor of this galaxy. "
                "Deep-Time Stewardship directives unlocked: Seed Nascent Life, Stabilize Stars, Plant Precursor Beacons, and Syntropic Pulses."
            ),
            data=rec.to_dict(),
        )

    def seed_nascent_life(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str,
        clade_name: Optional[str] = None,
    ) -> ActionResult:
        """Stewardship Directive: Seeds a prebiotic world with a young sapient clade."""
        rec = self.get_or_create_record(captain.id)
        if rec.phase != EpochPhase.STEWARDSHIP:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_SEED_NASCENT_LIFE,
                message="Seeding nascent civilizations requires Epoch III Deep-Time Stewardship.",
            )

        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_SEED_NASCENT_LIFE,
                message=f"Planet '{planet_id}' not found.",
            )

        if getattr(planet, "population", 0) > 0 and getattr(planet, "owner_id", None) != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_SEED_NASCENT_LIFE,
                message=f"{planet.name} already supports an inhabited civilization.",
            )

        cost = 25000
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_SEED_NASCENT_LIFE,
                message=f"Seeding primordial biology requires {cost:,} credits for genetic synthesis.",
            )

        captain.credits -= cost
        clade = clade_name or f"Neo-Clade of {planet.name}"
        planet.planet_type = "BIOTIC"
        planet.population = 1000
        planet.habitability = 0.95
        planet.natives = {
            "species": clade,
            "stage": "PRE_WARP",
            "temperament": "REVERENT",
            "reverence_for_progenitor": 100,
        }
        planet.owner_id = None  # Free primitive world under player's stewardship

        rec.nascent_worlds_seeded += 1
        rec.syntropic_resilience += 25.0
        rec.entropy_strain = max(0.0, rec.entropy_strain - 10.0)

        if hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender="PROGENITOR_NURSERY",
                text=f"A new sapient species ({clade}) has been seeded on {planet.name} under Progenitor stewardship.",
                channel="COSMIC_BROADCAST",
            )
        kernel.action_logs.append(f"[STEWARDSHIP] Seeded nascent species '{clade}' on {planet.name}.")

        return ActionResult(
            success=True,
            action=ActionType.STEWARD_SEED_NASCENT_LIFE,
            turns_spent=2,
            message=f"NASCENT CLADE SEEDED: The primordial seeds of '{clade}' now inhabit {planet.name}! Syntropic resilience +25.",
            data={"clade": clade, "planet": planet.name},
        )

    def stabilize_stellar_core(
        self,
        kernel: Any,
        captain: Captain,
        sector_id: Optional[int] = None,
    ) -> ActionResult:
        """Stewardship Directive: Injects syntropic stabilizers into a host star, calming flares and extending lifespan."""
        rec = self.get_or_create_record(captain.id)
        if rec.phase != EpochPhase.STEWARDSHIP:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_STABILIZE_STAR,
                message="Stellar Core Stabilization requires Epoch III Deep-Time Stewardship.",
            )

        sid = sector_id if sector_id is not None else captain.sector_id
        sec = kernel.sectors.get(sid)
        if not sec:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_STABILIZE_STAR,
                message=f"Sector {sid} not found.",
            )

        cost = 35000
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_STABILIZE_STAR,
                message=f"Stellar core stabilization requires {cost:,} credits in quantum containment catalysts.",
            )

        captain.credits -= cost
        # Fortify shields across all planets in sector
        for p in getattr(sec, "planets", []):
            p.shields = min(p.max_shields * 2, p.shields + 300)

        rec.stellar_cores_stabilized += 1
        rec.syntropic_resilience += 30.0
        rec.entropy_strain = max(0.0, rec.entropy_strain - 15.0)

        kernel.action_logs.append(f"[STEWARDSHIP] Stabilized the stellar fusion core of Sector {sid}.")
        return ActionResult(
            success=True,
            action=ActionType.STEWARD_STABILIZE_STAR,
            turns_spent=2,
            message=f"STELLAR CORE STABILIZED in Sector {sid}! Coronal equilibrium restored, solar superflares suppressed, planetary defense grids boosted.",
            data={"sector_id": sid, "stabilized_count": rec.stellar_cores_stabilized},
        )

    def plant_precursor_beacon(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str,
        relic_name: Optional[str] = None,
    ) -> ActionResult:
        """Stewardship Directive: Constructs an ancient Precursor Archaeological Site with a relic for future generations."""
        rec = self.get_or_create_record(captain.id)
        if rec.phase != EpochPhase.STEWARDSHIP:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_PLANT_PRECURSOR_BEACON,
                message="Planting Precursor Beacons requires Epoch III Deep-Time Stewardship.",
            )

        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_PLANT_PRECURSOR_BEACON,
                message=f"Planet '{planet_id}' not found.",
            )

        cost = 20000
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_PLANT_PRECURSOR_BEACON,
                message=f"Constructing a Precursor Beacon requires {cost:,} credits.",
            )

        relic = relic_name or "Syntropic Progenitor Monolith"
        captain.credits -= cost
        planet.ruins = {
            "culture": f"Progenitor Realm of {captain.name}",
            "era": "PROGENITOR",
            "tech_level": 5,
            "stability": 1.0,
            "elements": ["TITANIUM", "PLATINUM", "URANIUM"],
            "dug_depth": 0,
            "hoard": 15000,
            "relic": relic,
            "beacon_message": f"Left by {captain.name} for those who walk the stars in the ages yet to come.",
            "strata": [
                {"depth": 1, "richness": 1.5, "finds_left": 3, "hazard": 0.05, "elements": ["PLATINUM", "TITANIUM"]},
                {"depth": 2, "richness": 2.5, "finds_left": 2, "hazard": 0.10, "elements": ["URANIUM"]},
            ],
        }

        rec.precursor_beacons_planted += 1
        rec.syntropic_resilience += 20.0

        kernel.action_logs.append(f"[STEWARDSHIP] Planted Precursor Archaeological Beacon on {planet.name}.")
        return ActionResult(
            success=True,
            action=ActionType.STEWARD_PLANT_PRECURSOR_BEACON,
            turns_spent=1,
            message=f"PRECURSOR BEACON CONSTRUCTED on {planet.name}! Relic '{relic}' anchored deep within planetary bedrock.",
            data={"planet": planet.name, "relic": relic},
        )

    def syntropic_harmonic_pulse(
        self,
        kernel: Any,
        captain: Captain,
    ) -> ActionResult:
        """Stewardship Directive: Discharges cluster-wide syntropic resonance wave, reducing galactic entropy strain."""
        rec = self.get_or_create_record(captain.id)
        if rec.phase != EpochPhase.STEWARDSHIP:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_SYNTROPIC_PULSE,
                message="Syntropic Harmonic Pulses require Epoch III Deep-Time Stewardship.",
            )

        cost = 15000
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.STEWARD_SYNTROPIC_PULSE,
                message=f"Syntropic harmonic pulse requires {cost:,} credits in warp resonator tuning.",
            )

        captain.credits -= cost
        rec.entropy_strain = max(0.0, rec.entropy_strain - 35.0)
        rec.syntropic_pulses_fired += 1
        self.global_entropy_strain = max(0.0, self.global_entropy_strain - 20.0)

        # Fortify shields on captain's ship
        captain.ship.shields = min(captain.ship.max_shields, captain.ship.shields + 100)

        kernel.action_logs.append(f"[STEWARDSHIP] Emitted cluster-wide Syntropic Harmonic Pulse from Sector {captain.sector_id}.")
        return ActionResult(
            success=True,
            action=ActionType.STEWARD_SYNTROPIC_PULSE,
            turns_spent=1,
            message=f"SYNTROPIC HARMONIC PULSE DISCHARGED! Local entropy strain reduced (-35). Galactic warp lanes stabilized.",
            data={"entropy_strain": rec.entropy_strain, "pulses_fired": rec.syntropic_pulses_fired},
        )

    def tick(self, kernel: Any) -> None:
        """Cycle tick: applies subtle civilizational drift and advances stewardship syntropy."""
        for rec in self.records.values():
            if rec.phase == EpochPhase.FILTER_TRANSIT:
                rec.bottleneck_cycles += 1
                rec.entropy_strain += 1.5  # Ongoing thermodynamic pressure during bottleneck
            elif rec.phase == EpochPhase.STEWARDSHIP:
                # Stewards passively regenerate syntropy and soothe entropy
                rec.syntropic_resilience += 2.0
                rec.entropy_strain = max(0.0, rec.entropy_strain - 1.0)
                captain = kernel.captains.get(rec.player_id)
                if captain:
                    captain.credits += 200  # Deep-time stewardship dividend

    def to_dict(self) -> Dict[str, Any]:
        return {
            "records": {k: v.to_dict() for k, v in self.records.items()},
            "global_entropy_strain": self.global_entropy_strain,
            "global_syntropy_level": self.global_syntropy_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CivilizationalEpochManager:
        mgr = cls()
        mgr.global_entropy_strain = float(data.get("global_entropy_strain", 0.0))
        mgr.global_syntropy_level = float(data.get("global_syntropy_level", 0.0))
        for k, v in data.get("records", {}).items():
            mgr.records[k] = EpochRecord.from_dict(v)
        return mgr
