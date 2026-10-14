"""
xylarium/kernel/clade_nursery.py

Project Landing 2: The Deep-Time Nursery & Clade Phylogeny ("The Children of the Stars").

Connects directly to the Progenitor's Deep-Time Stewardship:
  - Tracks primitive sapient species seeded on prebiotic worlds across deep cosmic time.
  - Evolutionary Stages:
    PRE_TOOL -> TRIBAL_NEOLITHIC -> INDUSTRIAL_STEAM -> ATOMIC_ENERGY -> EARLY_SPACEFLIGHT -> WARP_SOVEREIGN.
  - Cultural & Theological Divergence:
    Species develop reverence, worship elder creator gods, or assert defiant independence.
  - Autonomous Expansion:
    Upon achieving WARP_SOVEREIGN status, the clade becomes a full spacefaring realm,
    spreading across adjacent star systems and deciphering the player's Precursor Beacons.
  - Progenitor Directives:
    Technological Uplift, Ecological Harmony, and Celestial Defense.
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
import random
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


class EvolutionaryStage(str, Enum):
    PRE_TOOL = "PRE_TOOL"
    TRIBAL_NEOLITHIC = "TRIBAL_NEOLITHIC"
    INDUSTRIAL_STEAM = "INDUSTRIAL_STEAM"
    ATOMIC_ENERGY = "ATOMIC_ENERGY"
    EARLY_SPACEFLIGHT = "EARLY_SPACEFLIGHT"
    WARP_SOVEREIGN = "WARP_SOVEREIGN"


STAGE_ORDER = [
    EvolutionaryStage.PRE_TOOL,
    EvolutionaryStage.TRIBAL_NEOLITHIC,
    EvolutionaryStage.INDUSTRIAL_STEAM,
    EvolutionaryStage.ATOMIC_ENERGY,
    EvolutionaryStage.EARLY_SPACEFLIGHT,
    EvolutionaryStage.WARP_SOVEREIGN,
]


@dataclass
class CladeRecord:
    id: str
    name: str
    origin_planet_id: str
    origin_sector_id: int
    progenitor_id: str
    stage: EvolutionaryStage = EvolutionaryStage.PRE_TOOL
    population: int = 1000
    reverence_pct: float = 100.0  # 0.0 (defiant) to 100.0 (divine worship)
    theology: str = "CREATOR_WORSHIP"
    cycles_lived: int = 0
    colonized_planets: List[str] = field(default_factory=list)
    guidance_directive: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "origin_planet_id": self.origin_planet_id,
            "origin_sector_id": self.origin_sector_id,
            "progenitor_id": self.progenitor_id,
            "stage": self.stage.value if isinstance(self.stage, EvolutionaryStage) else str(self.stage),
            "population": self.population,
            "reverence_pct": round(self.reverence_pct, 1),
            "theology": self.theology,
            "cycles_lived": self.cycles_lived,
            "colonized_planets": list(self.colonized_planets),
            "guidance_directive": self.guidance_directive,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CladeRecord:
        raw_stage = data.get("stage", EvolutionaryStage.PRE_TOOL.value)
        try:
            stage = EvolutionaryStage(raw_stage)
        except ValueError:
            stage = EvolutionaryStage.PRE_TOOL

        return cls(
            id=data["id"],
            name=data["name"],
            origin_planet_id=data["origin_planet_id"],
            origin_sector_id=int(data["origin_sector_id"]),
            progenitor_id=data["progenitor_id"],
            stage=stage,
            population=int(data.get("population", 1000)),
            reverence_pct=float(data.get("reverence_pct", 100.0)),
            theology=data.get("theology", "CREATOR_WORSHIP"),
            cycles_lived=int(data.get("cycles_lived", 0)),
            colonized_planets=list(data.get("colonized_planets", [])),
            guidance_directive=data.get("guidance_directive"),
        )


class CladeNurseryManager:
    """Manages deep-time evolution of seeded young sapient civilizations."""

    def __init__(self) -> None:
        self.clades: Dict[str, CladeRecord] = {}
        self.counter: int = 1

    def register_seeded_clade(
        self,
        kernel: Any,
        progenitor_id: str,
        planet: Planet,
        clade_name: str,
    ) -> CladeRecord:
        """Called automatically when a Progenitor seeds nascent life on a world."""
        clade_id = f"CLADE-{self.counter:03d}"
        self.counter += 1

        record = CladeRecord(
            id=clade_id,
            name=clade_name,
            origin_planet_id=planet.id,
            origin_sector_id=planet.sector_id,
            progenitor_id=progenitor_id,
            stage=EvolutionaryStage.PRE_TOOL,
            population=getattr(planet, "population", 1000) or 1000,
            colonized_planets=[planet.id],
        )
        self.clades[clade_id] = record
        return record

    def impart_guidance(
        self,
        kernel: Any,
        captain: Captain,
        clade_id: str,
        directive: str,
    ) -> ActionResult:
        """Transmits telepathic or orbital guidance to shape the young clade's destiny."""
        clade = self.clades.get(clade_id)
        if not clade:
            return ActionResult(
                success=False,
                action=ActionType.NURSERY_IMPART_GUIDANCE,
                message=f"Clade '{clade_id}' not found in nursery registry.",
            )

        if clade.progenitor_id != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.NURSERY_IMPART_GUIDANCE,
                message="Only the Progenitor who seeded this clade may impart celestial directives.",
            )

        directive_key = directive.upper().strip()
        valid = ["ECOLOGICAL_HARMONY", "MARTIAL_DEFENSE", "TECHNOLOGICAL_UPLIFT"]
        if directive_key not in valid:
            return ActionResult(
                success=False,
                action=ActionType.NURSERY_IMPART_GUIDANCE,
                message=f"Unknown directive '{directive}'. Valid directives: {valid}.",
            )

        cost = 15000
        if directive_key == "TECHNOLOGICAL_UPLIFT":
            cost = 30000

        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.NURSERY_IMPART_GUIDANCE,
                message=f"Imparting '{directive_key}' requires {cost:,} credits in orbital beacon transmission.",
            )

        captain.credits -= cost
        clade.guidance_directive = directive_key
        clade.reverence_pct = min(100.0, clade.reverence_pct + 15.0)

        # Apply immediate effect
        planet = kernel.get_planet(clade.origin_planet_id)
        if directive_key == "TECHNOLOGICAL_UPLIFT":
            idx = STAGE_ORDER.index(clade.stage)
            if idx < len(STAGE_ORDER) - 1:
                clade.stage = STAGE_ORDER[idx + 1]
                msg = f"CELESTIAL UPLIFT: {clade.name} has advanced to the {clade.stage.value} era!"
            else:
                msg = f"{clade.name} is already at peak warp sovereignty."

        elif directive_key == "ECOLOGICAL_HARMONY":
            if planet:
                planet.habitability = min(1.0, planet.habitability + 0.15)
            if hasattr(kernel, "epoch_manager"):
                rec = kernel.epoch_manager.get_or_create_record(captain.id)
                rec.syntropic_resilience += 20.0
            msg = f"ECOLOGICAL HARMONY: Biosphere on {planet.name if planet else 'homeworld'} enriched! Syntropy +20."

        elif directive_key == "MARTIAL_DEFENSE":
            if planet:
                planet.citadel_level += 2
                planet.shields += 400
                planet.fighters += 50
            msg = f"MARTIAL FORTIFICATION: Planetary citadels and defense orbital platforms deployed for {clade.name}."

        kernel.action_logs.append(f"[NURSERY] Imparted {directive_key} to {clade.name}.")
        return ActionResult(
            success=True,
            action=ActionType.NURSERY_IMPART_GUIDANCE,
            turns_spent=1,
            message=msg,
            data={"clade": clade.to_dict()},
        )

    def defend_clade(
        self,
        kernel: Any,
        captain: Captain,
        clade_id: str,
    ) -> ActionResult:
        """Progenitor intervention: dispels pirate raids or hostile incursions targeting the nursery world."""
        clade = self.clades.get(clade_id)
        if not clade:
            return ActionResult(
                success=False,
                action=ActionType.NURSERY_DEFEND_CLADE,
                message=f"Clade '{clade_id}' not found.",
            )

        planet = kernel.get_planet(clade.origin_planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.NURSERY_DEFEND_CLADE,
                message="Homeworld not found.",
            )

        planet.shields = min(planet.max_shields * 2, planet.shields + 500)
        planet.fighters += 30
        clade.reverence_pct = 100.0
        clade.theology = "DIVINE_PROTECTOR"

        if hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender="PROGENITOR_SHIELD",
                text=f"Progenitor {captain.name} has cast a divine protective barrier over {planet.name} [{clade.name}]!",
                channel="COSMIC_BROADCAST",
            )
        kernel.action_logs.append(f"[NURSERY] Defended nursery world {planet.name} for clade {clade.name}.")

        return ActionResult(
            success=True,
            action=ActionType.NURSERY_DEFEND_CLADE,
            turns_spent=1,
            message=f"DIVINE PROTECTION ANCHORED: Planetary shields fortified (+500) for {clade.name}. Reverence locked to 100%.",
            data={"planet": planet.name, "reverence": clade.reverence_pct},
        )

    def tick(self, kernel: Any) -> None:
        """Cycle tick: advances clade evolutionary ages and population growth."""
        for clade in self.clades.values():
            clade.cycles_lived += 1
            # Population growth
            growth_rate = 1.05 if clade.guidance_directive == "ECOLOGICAL_HARMONY" else 1.02
            clade.population = int(clade.population * growth_rate)

            # Natural evolutionary progression across deep time
            idx = STAGE_ORDER.index(clade.stage)
            thresholds = {
                EvolutionaryStage.PRE_TOOL: 5,
                EvolutionaryStage.TRIBAL_NEOLITHIC: 12,
                EvolutionaryStage.INDUSTRIAL_STEAM: 20,
                EvolutionaryStage.ATOMIC_ENERGY: 30,
                EvolutionaryStage.EARLY_SPACEFLIGHT: 45,
            }

            needed = thresholds.get(clade.stage, 9999)
            if clade.cycles_lived >= needed and idx < len(STAGE_ORDER) - 1:
                clade.stage = STAGE_ORDER[idx + 1]
                if hasattr(kernel, "event_bus"):
                    kernel.event_bus.broadcast_radio(
                        sender="NURSERY_BEACON",
                        text=f"The young species '{clade.name}' has achieved {clade.stage.value} civilization status!",
                        channel="COSMIC_BROADCAST",
                    )
                kernel.action_logs.append(f"[NURSERY] {clade.name} advanced to {clade.stage.value}.")

                # When achieving WARP_SOVEREIGN, they found their first interstellar spaceport
                if clade.stage == EvolutionaryStage.WARP_SOVEREIGN:
                    planet = kernel.get_planet(clade.origin_planet_id)
                    if planet:
                        planet.citadel_level = max(2, planet.citadel_level)
                        planet.population = max(5000, planet.population)
                    if hasattr(kernel, "epoch_manager"):
                        rec = kernel.epoch_manager.get_or_create_record(clade.progenitor_id)
                        rec.syntropic_resilience += 50.0  # Child civ graduating grants vast syntropy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clades": {k: v.to_dict() for k, v in self.clades.items()},
            "counter": self.counter,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CladeNurseryManager:
        mgr = cls()
        mgr.counter = int(data.get("counter", 1))
        for k, v in data.get("clades", {}).items():
            mgr.clades[k] = CladeRecord.from_dict(v)
        return mgr
