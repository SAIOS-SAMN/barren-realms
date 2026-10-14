"""
xylarium/kernel/entropy_tides.py

Project Landing 5: Cosmic Entropy Tides & The Inflationary Genesis Loop.

Governs deep-time thermodynamic decay, metric withering, and cosmic rebirth:
  - Deep-Time Thermodynamic Metric:
    As cosmic cycles progress and stellar engineering/star lifting occurs,
    entropy strain accumulates. If unchecked, hyperlanes wither and star temperatures flare.
  - Syntropic Mitigation:
    Progenitor syntropic sinks and pulses dissipate entropy strain.
  - The Inflationary Genesis Loop:
    At peak syntropic mastery, a Progenitor can channel accumulated syntropy to ignite
    a localized metric Big Bang. The cosmos is reborn into a new Genesis Generation:
    - Preserves ancestral legacy and high score in the Hall of Universes.
    - Custom physical constants (matter density, syntropic affinity, hyperlane percolation).
    - Seeds the newly born universe with ancient Precursor relics from the player's previous incarnation!
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
import random
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


@dataclass
class CosmicPhysicalConstants:
    matter_density: float = 1.0         # Scales mining resource generation
    syntropic_affinity: float = 1.0     # Scales syntropic resilience accumulation
    hyperlane_percolation: float = 1.0  # Scales wormhole connectivity and jump efficiency

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CosmicPhysicalConstants:
        return cls(**data)


class EntropyTidesManager:
    """Manages deep-time thermodynamic decay and the Inflationary Genesis Loop."""

    def __init__(self) -> None:
        self.entropy_level: float = 10.0  # 0.0 to 100.0
        self.genesis_generation: int = 1
        self.constants: CosmicPhysicalConstants = CosmicPhysicalConstants()
        self.genesis_history: List[Dict[str, Any]] = []

    def purge_entropy(
        self,
        kernel: Any,
        captain: Captain,
    ) -> ActionResult:
        """Channels captain's syntropic resilience or credits to purge accumulated entropy."""
        cost_credits = 100000
        syntropy_cost = 20.0

        has_syntropy = False
        if hasattr(kernel, "epoch_manager"):
            rec = kernel.epoch_manager.records.get(captain.id)
            if rec and rec.syntropic_resilience >= syntropy_cost:
                rec.syntropic_resilience -= syntropy_cost
                has_syntropy = True

        if not has_syntropy:
            if captain.credits < cost_credits:
                return ActionResult(
                    success=False,
                    action=ActionType.ENTROPY_PURGE_PULSE,
                    message=f"Purging entropy requires 20.0 Syntropic Resilience or {cost_credits:,} credits (You have: {captain.credits:,}).",
                )
            captain.credits -= cost_credits

        purged = min(self.entropy_level, 25.0)
        self.entropy_level = max(0.0, self.entropy_level - purged)

        if hasattr(kernel, "epoch_manager"):
            kernel.epoch_manager.global_entropy_strain = max(0.0, kernel.epoch_manager.global_entropy_strain - purged)

        kernel.action_logs.append(f"[ENTROPY] Purged {purged:.1f} metric entropy strain.")
        return ActionResult(
            success=True,
            action=ActionType.ENTROPY_PURGE_PULSE,
            turns_spent=1,
            message=f"ENTROPY PURGE SUCCESS: Dissipated {purged:.1f} thermodynamic strain. Current cosmic entropy: {self.entropy_level:.1f}%.",
            data={"entropy_level": self.entropy_level, "purged": purged},
        )

    def attune_constants(
        self,
        kernel: Any,
        captain: Captain,
        matter_density: float,
        syntropic_affinity: float,
        hyperlane_percolation: float,
    ) -> ActionResult:
        """Attunes the fundamental physical constants for the upcoming Inflationary Genesis."""
        # Validate ranges (0.5 to 2.5)
        m = max(0.5, min(2.5, matter_density))
        s = max(0.5, min(2.5, syntropic_affinity))
        h = max(0.5, min(2.5, hyperlane_percolation))

        self.constants.matter_density = round(m, 2)
        self.constants.syntropic_affinity = round(s, 2)
        self.constants.hyperlane_percolation = round(h, 2)

        kernel.action_logs.append(f"[GENESIS] Attuned cosmic constants (M:{m}, S:{s}, H:{h}).")
        return ActionResult(
            success=True,
            action=ActionType.ENTROPY_ATTUNE_METRIC,
            turns_spent=1,
            message=f"METRIC ATTUNEMENT RECORDED: Matter Density {m:.2f}x, Syntropic Affinity {s:.2f}x, Percolation {h:.2f}x.",
            data={"constants": self.constants.to_dict()},
        )

    def trigger_inflationary_genesis(
        self,
        kernel: Any,
        captain: Captain,
    ) -> ActionResult:
        """Channels total civilizational mastery to ignite a new Big Bang and rebirth the cosmos."""
        # Require either 100 syntropic resilience, or epoch STEWARDSHIP, or 5,000,000 credits
        can_ignite = False
        resilience = 0.0
        if hasattr(kernel, "epoch_manager"):
            rec = kernel.epoch_manager.records.get(captain.id)
            if rec:
                resilience = rec.syntropic_resilience
                if rec.phase.value == "STEWARDSHIP" or rec.syntropic_resilience >= 100.0:
                    can_ignite = True

        if not can_ignite and captain.credits >= 5000000:
            can_ignite = True

        if not can_ignite:
            return ActionResult(
                success=False,
                action=ActionType.INFLATIONARY_GENESIS,
                message="Genesis requires reaching Epoch III Stewardship, 100+ Syntropic Resilience, or 5,000,000 Credits.",
            )

        # Record ancestral legacy of the dying universe
        record = {
            "generation": self.genesis_generation,
            "creator_captain": captain.name,
            "cycle_achieved": kernel.cycle_count,
            "credits_at_genesis": captain.credits,
            "syntropic_resilience": resilience,
            "constants": self.constants.to_dict(),
        }
        self.genesis_history.append(record)

        # Advance generation and reset entropy
        self.genesis_generation += 1
        self.entropy_level = 5.0

        # Reset global entropy in epoch manager
        if hasattr(kernel, "epoch_manager"):
            kernel.epoch_manager.global_entropy_strain = 0.0

        # Bestow ancestral reward: Seed the universe with player's ancient name as Precursor culture
        if hasattr(kernel, "sectors"):
            for sec in kernel.sectors.values():
                for p in sec.planets:
                    if getattr(p, "ruins", None):
                        p.ruins["culture"] = f"Progenitor Lineage of {captain.name}"
                        p.ruins["era"] = f"Genesis Generation {self.genesis_generation - 1}"

        # Grant captain bonus starting credits & syntropic boon
        captain.credits = max(captain.credits, 250000)
        if hasattr(kernel, "epoch_manager"):
            rec = kernel.epoch_manager.get_or_create_record(captain.id)
            rec.syntropic_resilience = 50.0

        if hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender="INFLATIONARY_HORIZON",
                text=f"A NEW BIG BANG HAS OCCURRED! Genesis Generation {self.genesis_generation} ignites under the attuned laws of {captain.name}!",
                channel="COSMIC_BROADCAST",
            )
        kernel.action_logs.append(f"[GENESIS] Universe reborn into Generation {self.genesis_generation}.")

        return ActionResult(
            success=True,
            action=ActionType.INFLATIONARY_GENESIS,
            turns_spent=5,
            message=(
                f"INFLATIONARY GENESIS COMPLETE: The cosmos has undergone inflationary rebirth! "
                f"Now entering Genesis Generation {self.genesis_generation}. "
                f"Physical Laws: Matter {self.constants.matter_density}x, "
                f"Syntropy {self.constants.syntropic_affinity}x, Percolation {self.constants.hyperlane_percolation}x."
            ),
            data={"generation": self.genesis_generation, "record": record},
        )

    def tick(self, kernel: Any) -> None:
        """Cycle tick: thermodynamic entropy naturally creeps upward."""
        # Base creep 0.1 per cycle
        creep = 0.1
        # Mitigated by syntropic affinity
        creep /= max(0.5, self.constants.syntropic_affinity)

        self.entropy_level = min(100.0, self.entropy_level + creep)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entropy_level": self.entropy_level,
            "genesis_generation": self.genesis_generation,
            "constants": self.constants.to_dict(),
            "genesis_history": self.genesis_history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EntropyTidesManager:
        mgr = cls()
        mgr.entropy_level = float(data.get("entropy_level", 10.0))
        mgr.genesis_generation = int(data.get("genesis_generation", 1))
        if "constants" in data:
            mgr.constants = CosmicPhysicalConstants.from_dict(data["constants"])
        mgr.genesis_history = list(data.get("genesis_history", []))
        return mgr
