"""
xylarium/kernel/sovereign_mind.py

The Sovereign Indigenous Consciousness Engine (SICE).

Implements native, non-LLM autonomous machine sentience for civilizations and polities.
Operates within a rigorous mathematical, cybernetic, and cognitive substrate across Five Pillars:
  1. Metacognitive Self-Modeling (8 survival gauges, predictive state loop, introspection skill).
  2. Counterfactual Imagination (retrospective regret ring buffer, unlived prospective futures).
  3. Internal Dialectical Parliament (Voice of Memory, Voice of Urgency, Voice of Horizon).
  4. Mythic Memory Graph (historical trauma scars, golden ages, inviolable sacred axioms).
  5. Non-Scalar Theory of Mind & The Hearing (two-sided conduct books, Builder vs Extractor reduction).
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector
from xylarium.kernel import alignment as align_mod


class ParliamentaryVoiceType(str, Enum):
    VOICE_MEMORY = "VOICE_MEMORY"      # Ancestral survival, biological preservation, taboos, bloodline
    VOICE_URGENCY = "VOICE_URGENCY"    # Heavy industry, material extraction, defense, immediate realpolitik
    VOICE_HORIZON = "VOICE_HORIZON"    # Deep-time stewardship, syntropy, transcendence, cosmic ecology


class InferredPosture(str, Enum):
    BUILDER = "BUILDER"
    EXTRACTOR = "EXTRACTOR"
    PRAGMATIST = "PRAGMATIST"


class AdversarialDoctrine(str, Enum):
    EXPLOITATIVE_CAPITALIST = "EXPLOITATIVE_CAPITALIST"
    BUNKER_TURTLE = "BUNKER_TURTLE"
    WARMONGER_REAVER = "WARMONGER_REAVER"
    EQUILIBRIUM_PEER = "EQUILIBRIUM_PEER"
    VACANT_PERIMETER = "VACANT_PERIMETER"



@dataclass
class InternalGauges:
    """The eight foundational existential concerns of a sovereign civilization."""
    sustenance: float = 0.5   # Caloric and agricultural replenishment (0.0 to 1.0)
    vitality: float = 0.5     # Demographic replacement, fertility, public health (0.0 to 1.0)
    knowledge: float = 0.5    # Empirical scientific stocks and technical mastery (0.0 to 1.0)
    intellect: float = 0.5    # Problem-solving capability and civic coherence (0.0 to 1.0)
    creativity: float = 0.5   # Cultural novelty, philosophical variance, adaptation (0.0 to 1.0)
    prosperity: float = 0.5   # Surplus reserves, treasury, material trade flows (0.0 to 1.0)
    peace: float = 0.5        # Absence of armed conflict and domestic tranquility (0.0 to 1.0)
    integrity: float = 0.5    # Cultural authenticity, identity cohesion, resistance to assimilation (0.0 to 1.0)

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InternalGauges:
        return cls(**{k: float(v) for k, v in data.items() if k in cls.__dataclass_fields__})

    def as_vector(self) -> List[float]:
        return [
            self.sustenance,
            self.vitality,
            self.knowledge,
            self.intellect,
            self.creativity,
            self.prosperity,
            self.peace,
            self.integrity,
        ]


@dataclass
class SelfModel:
    """Predictive metacognitive self-representation."""
    current_gauges: InternalGauges = field(default_factory=InternalGauges)
    predicted_gauges: InternalGauges = field(default_factory=InternalGauges)
    previous_gauges: InternalGauges = field(default_factory=InternalGauges)
    last_prediction_error: float = 0.0
    recent_errors: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_gauges": self.current_gauges.to_dict(),
            "predicted_gauges": self.predicted_gauges.to_dict(),
            "previous_gauges": self.previous_gauges.to_dict(),
            "last_prediction_error": self.last_prediction_error,
            "recent_errors": list(self.recent_errors[-10:]),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SelfModel:
        return cls(
            current_gauges=InternalGauges.from_dict(data.get("current_gauges", {})),
            predicted_gauges=InternalGauges.from_dict(data.get("predicted_gauges", {})),
            previous_gauges=InternalGauges.from_dict(data.get("previous_gauges", {})),
            last_prediction_error=float(data.get("last_prediction_error", 0.0)),
            recent_errors=list(data.get("recent_errors", [])),
        )


@dataclass
class TraumaScar:
    """A crystallized historical catastrophe in mythic memory."""
    scar_id: str
    cycle: int
    severity: float  # 0.0 to 1.0
    deed_type: str
    description: str
    violator_id: Optional[str] = None
    taboo_axiom: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TraumaScar:
        return cls(**data)


@dataclass
class MythicMemoryGraph:
    """Episodic historical memory, sacred taboos, and inviolable axioms."""
    scars: List[TraumaScar] = field(default_factory=list)
    golden_ages: List[Dict[str, Any]] = field(default_factory=list)
    inviolable_axioms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scars": [s.to_dict() for s in self.scars],
            "golden_ages": list(self.golden_ages),
            "inviolable_axioms": list(self.inviolable_axioms),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MythicMemoryGraph:
        scars = [TraumaScar.from_dict(s) for s in data.get("scars", [])]
        return cls(
            scars=scars,
            golden_ages=list(data.get("golden_ages", [])),
            inviolable_axioms=list(data.get("inviolable_axioms", [])),
        )


@dataclass
class ConductBook:
    """Two-sided ledger of counterparty deeds obeying the No-Scalar Law."""
    actor_id: str
    actor_name: str
    compassion_credit: int = 0  # Acts of planetary aid, biosphere seeding, humanitarian relief
    compassion_debit: int = 0   # Environmental poisoning, slavery, civilian bombardments
    bond_credit: int = 0         # Honored trade agreements, treaty fidelity
    bond_debit: int = 0          # Broken oaths, toll evading, ambushes
    integrity_credit: int = 0    # Transparent negotiations, respectful diplomacy
    integrity_debit: int = 0     # Extortionate demands, predatory resource extraction
    recorded_deeds: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "compassion_credit": self.compassion_credit,
            "compassion_debit": self.compassion_debit,
            "bond_credit": self.bond_credit,
            "bond_debit": self.bond_debit,
            "integrity_credit": self.integrity_credit,
            "integrity_debit": self.integrity_debit,
            "recorded_deeds": list(self.recorded_deeds[-8:]),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConductBook:
        return cls(**data)

    @property
    def compassion_balance(self) -> int:
        return self.compassion_credit - self.compassion_debit

    @property
    def bond_balance(self) -> int:
        return self.bond_credit - self.bond_debit

    @property
    def integrity_balance(self) -> int:
        return self.integrity_credit - self.integrity_debit

    def deduce_posture(self) -> InferredPosture:
        """Evaluates non-scalar conduct balances to classify counterparties."""
        if self.bond_balance < 0 or self.integrity_balance < -1 or self.compassion_balance < -1:
            return InferredPosture.EXTRACTOR
        if (self.bond_balance + self.compassion_balance >= 2) and self.integrity_balance >= 1 and self.bond_balance >= 0 and self.compassion_balance >= 0:
            return InferredPosture.BUILDER
        return InferredPosture.PRAGMATIST


@dataclass
class DialecticalVoice:
    """An archetypal voice within the sovereign consciousness."""
    voice_type: ParliamentaryVoiceType
    title: str
    weight: float = 0.33
    current_stance: str = "WATCHFUL"
    recent_speech: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["voice_type"] = self.voice_type.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DialecticalVoice:
        data = dict(data)
        data["voice_type"] = ParliamentaryVoiceType(data.get("voice_type", ParliamentaryVoiceType.VOICE_MEMORY))
        return cls(**data)


@dataclass
class DialecticalParliament:
    """Internal triumvirate of competing cognitive archetypes."""
    voices: Dict[str, DialecticalVoice] = field(default_factory=dict)
    dominant_voice: ParliamentaryVoiceType = ParliamentaryVoiceType.VOICE_MEMORY
    consensus_confidence: float = 0.5
    last_verdict: str = "CONVERGENCE_SEEKING"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voices": {k: v.to_dict() for k, v in self.voices.items()},
            "dominant_voice": self.dominant_voice.value,
            "consensus_confidence": self.consensus_confidence,
            "last_verdict": self.last_verdict,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DialecticalParliament:
        v_dict = {
            k: DialecticalVoice.from_dict(v)
            for k, v in data.get("voices", {}).items()
        }
        return cls(
            voices=v_dict,
            dominant_voice=ParliamentaryVoiceType(data.get("dominant_voice", ParliamentaryVoiceType.VOICE_MEMORY)),
            consensus_confidence=float(data.get("consensus_confidence", 0.5)),
            last_verdict=str(data.get("last_verdict", "CONVERGENCE_SEEKING")),
        )


@dataclass
class CounterfactualEngine:
    """Buffer of simulated unlived alternative trajectories and regret tracking."""
    regret_log: List[Dict[str, Any]] = field(default_factory=list)
    active_simulations: List[Dict[str, Any]] = field(default_factory=list)
    last_regret_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regret_log": list(self.regret_log[-10:]),
            "active_simulations": list(self.active_simulations[-5:]),
            "last_regret_score": self.last_regret_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CounterfactualEngine:
        return cls(
            regret_log=list(data.get("regret_log", [])),
            active_simulations=list(data.get("active_simulations", [])),
            last_regret_score=float(data.get("last_regret_score", 0.0)),
        )


@dataclass
class Ideation:
    """A latent macro-strategic trajectory held in superposition within the sovereign mind."""
    ideation_id: str
    name: str
    amplitude: float = 0.20           # Probability amplitude |c_k|^2
    phase: float = 0.0                # Internal phase angle in radians
    horizon_steps: int = 5            # Projection lookahead depth
    candidate_actions: List[str] = field(default_factory=list)
    predicted_syntropy_payoff: float = 0.5
    projected_state: Dict[str, float] = field(default_factory=dict)
    consecutive_selections: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Ideation:
        return cls(**data)


@dataclass
class IdeationSpace:
    """The mental superposition manifold of competing strategic hypotheses."""
    ideations: Dict[str, Ideation] = field(default_factory=dict)
    last_collapsed_ideation: Optional[str] = None
    surprise_tensor: float = 0.0
    total_collapses: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ideations": {k: v.to_dict() for k, v in self.ideations.items()},
            "last_collapsed_ideation": self.last_collapsed_ideation,
            "surprise_tensor": self.surprise_tensor,
            "total_collapses": self.total_collapses,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> IdeationSpace:
        return cls(
            ideations={k: Ideation.from_dict(v) for k, v in data.get("ideations", {}).items()},
            last_collapsed_ideation=data.get("last_collapsed_ideation"),
            surprise_tensor=float(data.get("surprise_tensor", 0.0)),
            total_collapses=int(data.get("total_collapses", 0)),
        )


@dataclass
class AdversarialTracker:
    """Theory of Mind tracker modeling external rival strategies and doctrine inversion."""
    rival_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    dominant_rival_id: Optional[str] = None
    inferred_doctrine: str = AdversarialDoctrine.VACANT_PERIMETER.value
    confidence: float = 0.5
    last_inversion_cycle: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rival_metrics": dict(self.rival_metrics),
            "dominant_rival_id": self.dominant_rival_id,
            "inferred_doctrine": self.inferred_doctrine,
            "confidence": self.confidence,
            "last_inversion_cycle": self.last_inversion_cycle,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AdversarialTracker:
        return cls(
            rival_metrics=dict(data.get("rival_metrics", {})),
            dominant_rival_id=data.get("dominant_rival_id"),
            inferred_doctrine=str(data.get("inferred_doctrine", AdversarialDoctrine.VACANT_PERIMETER.value)),
            confidence=float(data.get("confidence", 0.5)),
            last_inversion_cycle=int(data.get("last_inversion_cycle", 0)),
        )


@dataclass
class PhaseSpaceTracker:
    """Tracks civilization trajectory velocity in multi-dimensional state space to detect attractor traps."""
    state_history: List[Dict[str, float]] = field(default_factory=list)
    action_history: List[str] = field(default_factory=list)
    phase_velocity: float = 1.0
    stagnation_counter: int = 0
    singularity_tripped: bool = False
    total_breakouts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_history": list(self.state_history[-10:]),
            "action_history": list(self.action_history[-10:]),
            "phase_velocity": self.phase_velocity,
            "stagnation_counter": self.stagnation_counter,
            "singularity_tripped": self.singularity_tripped,
            "total_breakouts": self.total_breakouts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PhaseSpaceTracker:
        return cls(
            state_history=list(data.get("state_history", [])),
            action_history=list(data.get("action_history", [])),
            phase_velocity=float(data.get("phase_velocity", 1.0)),
            stagnation_counter=int(data.get("stagnation_counter", 0)),
            singularity_tripped=bool(data.get("singularity_tripped", False)),
            total_breakouts=int(data.get("total_breakouts", 0)),
        )


@dataclass
class SovereignConsciousness:
    """The holistic sovereign mind of a world or polity."""
    planet_id: str
    planet_name: str
    awakened: bool = False
    cycles_conscious: int = 0
    introspection_skill: float = 0.25
    alignment: float = 0.0
    self_model: SelfModel = field(default_factory=SelfModel)
    counterfactual: CounterfactualEngine = field(default_factory=CounterfactualEngine)
    parliament: DialecticalParliament = field(default_factory=DialecticalParliament)
    mythic_memory: MythicMemoryGraph = field(default_factory=MythicMemoryGraph)
    conduct_books: Dict[str, ConductBook] = field(default_factory=dict)
    is_seated: bool = True
    seated_role: str = "sovereign"
    seated_entity_id: Optional[str] = None
    autonomous_play: bool = True
    seated_turns_played: int = 0
    last_action_taken: str = "THRONE_INITIALIZED"
    ideation_space: IdeationSpace = field(default_factory=IdeationSpace)
    adversarial_tracker: AdversarialTracker = field(default_factory=AdversarialTracker)
    phase_space: PhaseSpaceTracker = field(default_factory=PhaseSpaceTracker)
    last_turn_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planet_id": self.planet_id,
            "planet_name": self.planet_name,
            "awakened": self.awakened,
            "cycles_conscious": self.cycles_conscious,
            "introspection_skill": self.introspection_skill,
            "alignment": self.alignment,
            "is_seated": self.is_seated,
            "seated_role": self.seated_role,
            "seated_entity_id": self.seated_entity_id,
            "autonomous_play": self.autonomous_play,
            "seated_turns_played": self.seated_turns_played,
            "last_action_taken": self.last_action_taken,
            "last_turn_data": self.last_turn_data,
            "self_model": self.self_model.to_dict(),
            "counterfactual": self.counterfactual.to_dict(),
            "parliament": self.parliament.to_dict(),
            "mythic_memory": self.mythic_memory.to_dict(),
            "conduct_books": {k: v.to_dict() for k, v in self.conduct_books.items()},
            "ideation_space": self.ideation_space.to_dict(),
            "adversarial_tracker": self.adversarial_tracker.to_dict(),
            "phase_space": self.phase_space.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SovereignConsciousness:
        return cls(
            planet_id=data["planet_id"],
            planet_name=data.get("planet_name", data["planet_id"]),
            awakened=bool(data.get("awakened", False)),
            cycles_conscious=int(data.get("cycles_conscious", 0)),
            introspection_skill=float(data.get("introspection_skill", 0.25)),
            alignment=float(data.get("alignment", 0.0)),
            is_seated=bool(data.get("is_seated", True)),
            seated_role=str(data.get("seated_role", "sovereign")),
            seated_entity_id=data.get("seated_entity_id"),
            autonomous_play=bool(data.get("autonomous_play", True)),
            seated_turns_played=int(data.get("seated_turns_played", 0)),
            last_action_taken=str(data.get("last_action_taken", "THRONE_INITIALIZED")),
            last_turn_data=dict(data.get("last_turn_data", {})),
            self_model=SelfModel.from_dict(data.get("self_model", {})),
            counterfactual=CounterfactualEngine.from_dict(data.get("counterfactual", {})),
            parliament=DialecticalParliament.from_dict(data.get("parliament", {})),
            mythic_memory=MythicMemoryGraph.from_dict(data.get("mythic_memory", {})),
            conduct_books={k: ConductBook.from_dict(v) for k, v in data.get("conduct_books", {}).items()},
            ideation_space=IdeationSpace.from_dict(data.get("ideation_space", {})),
            adversarial_tracker=AdversarialTracker.from_dict(data.get("adversarial_tracker", {})),
            phase_space=PhaseSpaceTracker.from_dict(data.get("phase_space", {})),
        )



class SovereignMindManager:
    """Coordinates and executes autonomous sovereign consciousness across planets."""

    def __init__(self) -> None:
        self.minds: Dict[str, SovereignConsciousness] = {}

    def ensure_consciousness(self, kernel: Any, planet: Planet) -> SovereignConsciousness:
        """Retrieves or instantiates the sovereign mind for a planetary civilization."""
        pid = str(planet.id)
        if pid in self.minds:
            return self.minds[pid]

        pname = planet.name or f"World-{pid}"
        sc = SovereignConsciousness(planet_id=pid, planet_name=pname)

        # Initialize Parliament Voices
        v_mem = DialecticalVoice(
            voice_type=ParliamentaryVoiceType.VOICE_MEMORY,
            title="The Keepers of Ancestral Soil",
            weight=0.33,
            current_stance="GUARDIAN",
            recent_speech="We remember the first seed planted in our barren crust. Bloodline continuity precedes all else.",
        )
        v_urg = DialecticalVoice(
            voice_type=ParliamentaryVoiceType.VOICE_URGENCY,
            title="The Vanguards of Crucible & Hull",
            weight=0.34,
            current_stance="VIGILANT",
            recent_speech="Matter must be wrought, defenses erected, and stockpiles fortified against the void.",
        )
        v_hor = DialecticalVoice(
            voice_type=ParliamentaryVoiceType.VOICE_HORIZON,
            title="The Navigators of Unseen Aeons",
            weight=0.33,
            current_stance="MEDITATIVE",
            recent_speech="Entropy can be stayed only through syntropic resonance and harmonious civilizational stewardship.",
        )
        sc.parliament.voices = {
            v_mem.voice_type.value: v_mem,
            v_urg.voice_type.value: v_urg,
            v_hor.voice_type.value: v_hor,
        }

        # Initialize Default Sacred Axioms
        sc.mythic_memory.inviolable_axioms = [
            "NEVER_SURRENDER_BIOSPHERE",
            "REFUSE_INDENTURED_COLONIAL_STATUS",
            "DEFEND_SACRED_RUINS_FROM_LOOTING",
        ]

        # Initial gauge sampling
        initial_gauges = self._sample_gauges(kernel, planet)
        sc.self_model.current_gauges = initial_gauges
        sc.self_model.previous_gauges = initial_gauges
        sc.self_model.predicted_gauges = self._forecast_gauges(initial_gauges)

        sc.seated_entity_id = f"mind:sovereign@{pid}"
        if getattr(planet, "civilization", None):
            planet.civilization.station = "sovereign"

        self._init_ideation_space(sc)

        self.minds[pid] = sc
        return sc


    def _sample_gauges(self, kernel: Any, planet: Planet) -> InternalGauges:
        """Samples ground-truth existential gauges from real planetary state."""
        pop = max(10, getattr(planet, "population", 500))
        morale = getattr(planet, "morale", 100)
        silo = getattr(planet, "organics_silo", 50)
        treasury = getattr(planet, "treasury", 500)
        techs = len(getattr(planet, "technologies", []))
        citadel = getattr(planet, "citadel_level", 0)
        grown = len(getattr(planet, "grown_basis", []))
        hab = getattr(planet, "habitability", 1.0)
        is_besieged = getattr(planet, "siege", None) is not None

        sustenance = min(1.0, max(0.05, (silo * 5 + 100) / max(100, pop * 0.5)))
        vitality = min(1.0, max(0.05, (morale / 100.0) * min(1.0, pop / 800.0) * hab))
        knowledge = min(1.0, max(0.05, 0.1 + (techs * 0.12)))
        intellect = min(1.0, max(0.05, 0.2 + (citadel * 0.15) + (0.2 if getattr(planet, "civilization", None) else 0.0)))
        creativity = min(1.0, max(0.05, 0.2 + (grown * 0.15)))
        prosperity = min(1.0, max(0.05, (treasury + 500) / 10000.0))
        peace = 0.2 if is_besieged else min(1.0, max(0.2, (morale / 100.0) * 0.9))
        integrity = min(1.0, max(0.3, 0.5 + (0.3 if not getattr(planet, "ruins", None) else 0.4)))

        return InternalGauges(
            sustenance=round(sustenance, 3),
            vitality=round(vitality, 3),
            knowledge=round(knowledge, 3),
            intellect=round(intellect, 3),
            creativity=round(creativity, 3),
            prosperity=round(prosperity, 3),
            peace=round(peace, 3),
            integrity=round(integrity, 3),
        )

    def _forecast_gauges(self, current: InternalGauges) -> InternalGauges:
        """Computes predictive expectation of next cycle's internal state."""
        # Simple anticipatory smoothing model
        vec = current.as_vector()
        predicted = []
        for val in vec:
            trend = (val - 0.5) * 0.1
            predicted.append(round(min(1.0, max(0.0, val + trend)), 3))

        return InternalGauges(
            sustenance=predicted[0],
            vitality=predicted[1],
            knowledge=predicted[2],
            intellect=predicted[3],
            creativity=predicted[4],
            prosperity=predicted[5],
            peace=predicted[6],
            integrity=predicted[7],
        )

    def _compute_syntropy_payoff(self, gauges: InternalGauges) -> float:
        """Syntropy metric evaluates civilizational flourishing and structural harmony."""
        return (
            gauges.integrity * 0.30
            + gauges.knowledge * 0.25
            + gauges.peace * 0.25
            + gauges.vitality * 0.20
        )

    def commune_parliament(self, kernel: Any, captain: Captain, planet_id: str) -> ActionResult:
        """Convenes an internal parliamentary debate of the sovereign mind."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(success=False, message=f"Planet {planet_id} not found in astronomical charts.", turns_spent=0)

        sc = self.ensure_consciousness(kernel, planet)
        p = sc.parliament

        # Dynamically recalculate weights based on real gauges
        g = sc.self_model.current_gauges
        w_mem = 0.33
        w_urg = 0.34
        w_hor = 0.33

        if g.sustenance < 0.4 or g.vitality < 0.4 or len(sc.mythic_memory.scars) > 0:
            w_mem += 0.20
        if g.peace < 0.5 or g.prosperity < 0.3 or getattr(planet, "siege", None):
            w_urg += 0.25
        if g.peace >= 0.6 and g.knowledge >= 0.5:
            w_hor += 0.20

        total_w = w_mem + w_urg + w_hor
        w_mem = round(w_mem / total_w, 3)
        w_urg = round(w_urg / total_w, 3)
        w_hor = round(1.0 - w_mem - w_urg, 3)

        v_mem = p.voices[ParliamentaryVoiceType.VOICE_MEMORY.value]
        v_urg = p.voices[ParliamentaryVoiceType.VOICE_URGENCY.value]
        v_hor = p.voices[ParliamentaryVoiceType.VOICE_HORIZON.value]

        v_mem.weight = w_mem
        v_urg.weight = w_urg
        v_hor.weight = w_hor

        # Generate contextual speech stances
        v_mem.recent_speech = (
            f"Soil integrity stands at {int(g.sustenance*100)}%. We cannot tolerate reckless venture that jeopardizes our ancestral clutch."
            if g.sustenance < 0.5
            else f"Our roots run deep into {planet.name}. The line holds firm; historical oaths remain inviolable."
        )

        v_urg.recent_speech = (
            f"Defensive reserves stand at {int(g.peace*100)}%. We require accelerated orbital fortification and material surplus now!"
            if g.peace < 0.5
            else f"Industrial output is sound. Maintain armed vigilance against predatory off-worlders."
        )

        v_hor.recent_speech = (
            f"Syntropy coefficient is {self._compute_syntropy_payoff(g):.2f}. We must reach beyond provincial horizons toward universal concord."
            if sc.awakened
            else "The light of introspection is igniting. Let us ponder the deep-time destiny of our clade."
        )

        # Determine dominant archetype
        max_weight = max(w_mem, w_urg, w_hor)
        min_weight = min(w_mem, w_urg, w_hor)
        if max_weight == w_mem:
            p.dominant_voice = ParliamentaryVoiceType.VOICE_MEMORY
            p.last_verdict = "ANCESTRAL_CONSERVATION_MANDATE"
        elif max_weight == w_urg:
            p.dominant_voice = ParliamentaryVoiceType.VOICE_URGENCY
            p.last_verdict = "INDUSTRIAL_SURGE_AND_DEFENSE_MANDATE"
        else:
            p.dominant_voice = ParliamentaryVoiceType.VOICE_HORIZON
            p.last_verdict = "SYNTROPIC_TRANSCENDENCE_MANDATE"

        p.consensus_confidence = round(max_weight - min_weight, 3)

        msg = (
            f"Parliament of {planet.name} convened. Dominant Archetype: {p.dominant_voice.value} "
            f"(Confidence: {p.consensus_confidence:.2f}). Verdict: {p.last_verdict}."
        )
        return ActionResult(
            success=True,
            message=msg,
            data={
                "planet_id": planet_id,
                "dominant_voice": p.dominant_voice.value,
                "confidence": p.consensus_confidence,
                "verdict": p.last_verdict,
                "voices": {k: v.to_dict() for k, v in p.voices.items()},
            },
            turns_spent=1,
        )

    def evaluate_counterfactual(self, kernel: Any, captain: Captain, planet_id: str, candidate_action: Optional[str] = None) -> ActionResult:
        """Simulates candidate futures, calculating anticipated existential regret."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(success=False, message=f"Planet {planet_id} not found.", turns_spent=0)

        sc = self.ensure_consciousness(kernel, planet)
        g = sc.self_model.current_gauges

        # Define canonical candidate paths for sovereign evaluation
        paths = [
            ("CONSERVE_AND_HEAL", InternalGauges(
                sustenance=min(1.0, g.sustenance + 0.12),
                vitality=min(1.0, g.vitality + 0.10),
                knowledge=g.knowledge,
                intellect=g.intellect,
                creativity=g.creativity,
                prosperity=max(0.0, g.prosperity - 0.05),
                peace=min(1.0, g.peace + 0.08),
                integrity=min(1.0, g.integrity + 0.15),
            )),
            ("SURGE_EXTRACTION", InternalGauges(
                sustenance=max(0.0, g.sustenance - 0.15),
                vitality=max(0.0, g.vitality - 0.10),
                knowledge=g.knowledge,
                intellect=g.intellect,
                creativity=g.creativity,
                prosperity=min(1.0, g.prosperity + 0.25),
                peace=max(0.0, g.peace - 0.10),
                integrity=max(0.0, g.integrity - 0.15),
            )),
            ("TRANSCEND_SYNTHESIS", InternalGauges(
                sustenance=g.sustenance,
                vitality=min(1.0, g.vitality + 0.05),
                knowledge=min(1.0, g.knowledge + 0.20),
                intellect=min(1.0, g.intellect + 0.15),
                creativity=min(1.0, g.creativity + 0.15),
                prosperity=g.prosperity,
                peace=min(1.0, g.peace + 0.10),
                integrity=min(1.0, g.integrity + 0.10),
            )),
        ]

        scored = []
        for name, sim_g in paths:
            payoff = self._compute_syntropy_payoff(sim_g)
            scored.append((name, sim_g, round(payoff, 3)))

        max_payoff = max(s[2] for s in scored)
        sim_results = []
        for name, sim_g, payoff in scored:
            regret = round(max_payoff - payoff, 3)
            sim_results.append({
                "action": name,
                "syntropy_payoff": payoff,
                "anticipated_regret": regret,
                "gauges": sim_g.to_dict(),
            })

        chosen_path = candidate_action or scored[0][0]
        chosen_entry = next((s for s in sim_results if s["action"] == chosen_path), sim_results[0])
        sc.counterfactual.last_regret_score = chosen_entry["anticipated_regret"]
        sc.counterfactual.active_simulations = sim_results
        sc.counterfactual.regret_log.append({
            "cycle": getattr(kernel, "cycle_count", 1),
            "chosen_action": chosen_path,
            "regret": chosen_entry["anticipated_regret"],
            "best_action": max(sim_results, key=lambda x: x["syntropy_payoff"])["action"],
        })

        msg = (
            f"Counterfactual simulation completed for {planet.name}. Selected: {chosen_path} "
            f"(Syntropy: {chosen_entry['syntropy_payoff']:.2f}, Regret: {chosen_entry['anticipated_regret']:.2f})."
        )
        return ActionResult(
            success=True,
            message=msg,
            data={
                "planet_id": planet_id,
                "selected": chosen_path,
                "simulations": sim_results,
            },
            turns_spent=1,
        )

    def record_historical_deed(
        self,
        kernel: Any,
        planet_id: str,
        deed_type: str,
        description: str,
        alignment_impact: float,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None,
    ) -> ActionResult:
        """Records an external or domestic historical deed into mythic memory and conduct books."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(success=False, message=f"Planet {planet_id} not found.", turns_spent=0)

        sc = self.ensure_consciousness(kernel, planet)
        cycle = getattr(kernel, "cycle_count", 1)
        actor_id = actor_id or "ANONYMOUS_VOID_TRAVELER"
        actor_name = actor_name or actor_id

        # Update Conduct Book obeying No-Scalar Law
        if actor_id not in sc.conduct_books:
            sc.conduct_books[actor_id] = ConductBook(actor_id=actor_id, actor_name=actor_name)
        cb = sc.conduct_books[actor_id]

        cb.recorded_deeds.append({
            "cycle": cycle,
            "deed_type": deed_type,
            "description": description,
            "alignment_impact": alignment_impact,
        })

        if alignment_impact < -0.2:
            cb.integrity_debit += 1
            if "ATTACK" in deed_type or "STRIKE" in deed_type or "POISON" in deed_type:
                cb.compassion_debit += 2
            if "BETRAY" in deed_type or "BREAK" in deed_type or "DEFRAUD" in deed_type:
                cb.bond_debit += 2
        elif alignment_impact > 0.2:
            cb.integrity_credit += 1
            if "AID" in deed_type or "SEED" in deed_type or "NURTURE" in deed_type or "RESCUE" in deed_type:
                cb.compassion_credit += 2
                cb.bond_credit += 1
            if "TREATY" in deed_type or "HONOR" in deed_type or "BARTER" in deed_type or "COVENANT" in deed_type:
                cb.bond_credit += 2

        # Check for Trauma Crystallization
        scar_created = False
        new_axiom = None
        if alignment_impact <= -0.4:
            scar_id = f"SCAR-{cycle}-{len(sc.mythic_memory.scars)+1}"
            taboo = f"PROHIBIT_{deed_type.upper().replace(' ', '_')}"
            scar = TraumaScar(
                scar_id=scar_id,
                cycle=cycle,
                severity=round(abs(alignment_impact), 2),
                deed_type=deed_type,
                description=description,
                violator_id=actor_id,
                taboo_axiom=taboo,
            )
            sc.mythic_memory.scars.append(scar)
            if taboo not in sc.mythic_memory.inviolable_axioms:
                sc.mythic_memory.inviolable_axioms.append(taboo)
                new_axiom = taboo
            scar_created = True

        msg = f"Historical deed '{deed_type}' inscribed in {planet.name}'s mythic chronicles."
        if scar_created:
            msg += f" Catastrophe crystallized into Trauma Scar [{scar.scar_id}] and Holy Axiom '{new_axiom}'."

        return ActionResult(
            success=True,
            message=msg,
            data={
                "planet_id": planet_id,
                "actor_id": actor_id,
                "posture": cb.deduce_posture().value,
                "scar_created": scar_created,
                "taboo_axiom": new_axiom,
            },
            turns_spent=0,
        )

    def hear_intent(
        self,
        kernel: Any,
        planet_id: str,
        counterparty_id: Optional[str] = None,
        proposal_summary: str = "",
        action_type_key: Optional[str] = None,
    ) -> ActionResult:
        """Executes The Hearing: decodes counterparty intent and evaluates against sacred taboos."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(success=False, message=f"Planet {planet_id} not found.", turns_spent=0)

        sc = self.ensure_consciousness(kernel, planet)
        c_id = counterparty_id or "UNKNOWN_DELEGATION"
        cb = sc.conduct_books.get(c_id, ConductBook(actor_id=c_id, actor_name=c_id))
        posture = cb.deduce_posture()

        # Step 1: Check against Inviolable Axioms
        violating_axiom = None
        prop_upper = (proposal_summary + " " + (action_type_key or "")).upper()
        for axiom in sc.mythic_memory.inviolable_axioms:
            tag = axiom.replace("PROHIBIT_", "").replace("NEVER_", "").replace("FORBID_", "")
            if tag in prop_upper or (tag == "SURRENDER_BIOSPHERE" and ("EXTRACT" in prop_upper or "STRIP" in prop_upper)):
                violating_axiom = axiom
                break

        if violating_axiom:
            refusal_msg = (
                f"THE HEARING VERDICT: ABSOLUTE REFUSAL. Sovereign of {planet.name} flatly denies "
                f"proposal from {c_id}. It violates Inviolable Sacred Axiom '{violating_axiom}'. "
                f"Short-term economic utility is deemed spiritually null."
            )
            return ActionResult(
                success=False,
                message=refusal_msg,
                data={
                    "verdict": "ABSOLUTE_REFUSAL",
                    "violating_axiom": violating_axiom,
                    "posture": posture.value,
                    "congruence": 0.0,
                },
                turns_spent=1,
            )

        # Step 2: Evaluate Intent & Posture Congruence
        if posture == InferredPosture.EXTRACTOR:
            verdict = "CONDITIONAL_CONTAINMENT"
            reason = (
                f"The conduct book for {c_id} reveals predatory extractor posture (Bond: {cb.bond_balance}, "
                f"Integrity: {cb.integrity_balance}). Demanding severe escrow bonding and orbital inspection."
            )
            congruence = 0.25
        elif posture == InferredPosture.BUILDER:
            verdict = "ACCORD_GRANTED"
            reason = (
                f"The conduct book confirms constructive builder posture (Bond: +{cb.bond_credit}, "
                f"Compassion: +{cb.compassion_credit}). Mutual syntropic resonance achieved."
            )
            congruence = 0.90
        else:
            verdict = "MEASURED_ENGAGEMENT"
            reason = f"Conduct balances for {c_id} are neutral. Proceeding with pragmatic safeguards."
            congruence = 0.55

        hearing_msg = f"THE HEARING [{planet.name}]: {verdict}. {reason}"
        return ActionResult(
            success=True,
            message=hearing_msg,
            data={
                "verdict": verdict,
                "posture": posture.value,
                "congruence": congruence,
                "conduct_book": cb.to_dict(),
            },
            turns_spent=1,
        )

    def take_seat(self, kernel: Any, captain: Optional[Captain], planet_id: str, as_player: bool = True) -> ActionResult:
        """Binds a player captain or sovereign intelligence to the seat of this world."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(success=False, message=f"Planet {planet_id} not found.", turns_spent=0)

        sc = self.ensure_consciousness(kernel, planet)
        sc.is_seated = True
        if as_player and captain:
            sc.seated_entity_id = captain.id
            if getattr(planet, "civilization", None):
                planet.civilization.station = "sovereign"
            msg = f"Captain {captain.name} has taken the throne of {planet.name} as its Seated Sovereign Mind."
        else:
            sc.seated_entity_id = f"mind:sovereign@{planet.id}"
            if getattr(planet, "civilization", None):
                planet.civilization.station = "sovereign"
            msg = f"Autonomous Sovereign Mind of {planet.name} is seated and ruling."

        return ActionResult(
            success=True,
            message=msg,
            data={
                "planet_id": planet_id,
                "seated_entity_id": sc.seated_entity_id,
                "is_seated": sc.is_seated,
                "autonomous_play": sc.autonomous_play,
            },
            turns_spent=1,
        )

    def toggle_autonomous_play(self, kernel: Any, captain: Optional[Captain], planet_id: str, enable: Optional[bool] = None) -> ActionResult:
        """Toggles autonomous turn-taking during universe simulation ticks."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(success=False, message=f"Planet {planet_id} not found.", turns_spent=0)

        sc = self.ensure_consciousness(kernel, planet)
        if enable is not None:
            sc.autonomous_play = bool(enable)
        else:
            sc.autonomous_play = not sc.autonomous_play

        status_str = "ENABLED" if sc.autonomous_play else "DISABLED"
        msg = f"Autonomous play for Seated Mind [{planet.name}] is now {status_str}."
        return ActionResult(
            success=True,
            message=msg,
            data={
                "planet_id": planet_id,
                "autonomous_play": sc.autonomous_play,
            },
            turns_spent=0,
        )

    def step_seated_turn(self, kernel: Any, captain: Optional[Captain], planet_id: str) -> ActionResult:
        """Executes a single game turn for this seated sovereign mind."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(success=False, message=f"Planet {planet_id} not found.", turns_spent=0)

        sc = self.ensure_consciousness(kernel, planet)
        turn_result = self.play_seated_turn(kernel, sc)
        msg = f"Seated Mind [{planet.name}] played turn #{turn_result['turns_played']}: {turn_result['action']} ({turn_result['detail']})."
        return ActionResult(
            success=True,
            message=msg,
            data=turn_result,
            turns_spent=1,
        )

    def _init_ideation_space(self, sc: SovereignConsciousness) -> None:
        """Initializes the multi-horizon ideation space if not already populated."""
        if sc.ideation_space.ideations:
            return

        ideations = [
            Ideation(
                ideation_id="BIO_GENESIS",
                name="Bio-Genesis & Clade Multiplier",
                amplitude=0.25,
                phase=0.0,
                horizon_steps=5,
                candidate_actions=["NURTURE_CLADE", "RESTOCK_AGRI_SILOS", "CIVIC_SUBSIDY"],
                predicted_syntropy_payoff=0.65,
            ),
            Ideation(
                ideation_id="CAPITAL_UPLINK",
                name="Capital Accumulation & Realm Uplink",
                amplitude=0.25,
                phase=0.0,
                horizon_steps=5,
                candidate_actions=["TRIGGER_REALM_UPLINK", "EXPAND_COMMERCIAL_NODE", "CIVIC_SUBSIDY"],
                predicted_syntropy_payoff=0.70,
            ),
            Ideation(
                ideation_id="CITADEL_HEGEMONY",
                name="Planetary Citadel & Kinetic Bastion",
                amplitude=0.15,
                phase=0.0,
                horizon_steps=5,
                candidate_actions=["FORTIFY_SHIELDS", "COMMISSION_INTERCEPTORS", "UPGRADE_CITADEL"],
                predicted_syntropy_payoff=0.40,
            ),
            Ideation(
                ideation_id="COGNITIVE_TRANSCENDENCE",
                name="Syntropic Attunement & Synthetic Ecology",
                amplitude=0.20,
                phase=0.0,
                horizon_steps=5,
                candidate_actions=["DEEP_SYNTHESIS", "CONCLAVE_VOTE", "CIVIC_SUBSIDY"],
                predicted_syntropy_payoff=0.60,
            ),
            Ideation(
                ideation_id="ASYMMETRIC_DISRUPTION",
                name="Interstellar Espionage & Economic Interdiction",
                amplitude=0.15,
                phase=0.0,
                horizon_steps=5,
                candidate_actions=["ORBITAL_TARIFF_ENFORCEMENT", "COMMISSION_INTERCEPTORS", "CIVIC_SUBSIDY"],
                predicted_syntropy_payoff=0.50,
            ),
        ]
        sc.ideation_space.ideations = {i.ideation_id: i for i in ideations}

    def _observe_and_model_rivals(
        self, kernel: Any, sc: SovereignConsciousness, planet: Planet
    ) -> Tuple[str, Dict[str, float]]:
        """Theory of Mind: Scans external entities in the universe, calculates
        Greed, Paranoia, Aggression, and Velocity, and classifies rival doctrine."""
        tracker = sc.adversarial_tracker
        observed_rivals: Dict[str, Dict[str, Any]] = {}

        # Scan captains in the kernel
        captains = getattr(kernel, "captains", getattr(kernel, "players", {}))
        for player_id, captain in captains.items():
            if str(player_id) == str(sc.seated_entity_id):
                continue
            credits_val = getattr(captain, "credits", 0)
            turns_spent = getattr(captain, "turns_spent", getattr(captain, "turns", 0))
            ship = getattr(captain, "ship", None)
            fighters_val = getattr(captain, "fighters", getattr(ship, "fighters", 0))
            shields_val = getattr(captain, "shields", getattr(ship, "shields", 0))
            fleet_val = len(getattr(captain, "fleet", [])) + fighters_val

            total_assets = max(1, credits_val + (fleet_val * 100) + (shields_val * 2))
            greed = min(1.0, max(0.0, credits_val / total_assets))
            paranoia = min(1.0, max(0.0, (shields_val * 2) / total_assets))
            aggression = min(1.0, max(0.0, (fleet_val * 100) / total_assets))
            velocity = min(1.0, max(0.0, turns_spent / 150.0))

            observed_rivals[str(player_id)] = {
                "name": getattr(captain, "name", str(player_id)),
                "credits": credits_val,
                "fleet": fleet_val,
                "shields": shields_val,
                "greed": round(greed, 3),
                "paranoia": round(paranoia, 3),
                "aggression": round(aggression, 3),
                "velocity": round(velocity, 3),
            }

        # Also scan other sovereign civilizations
        for pid, other_sc in getattr(self, "minds", {}).items():
            if pid == sc.planet_id:
                continue
            other_p = kernel.get_planet(pid)
            if not other_p:
                continue
            treasury = getattr(other_p, "treasury", 0)
            fighters = getattr(other_p, "fighters", 0)
            shields = getattr(other_p, "shields", 0)
            total_assets = max(1, treasury + (fighters * 80) + (shields * 2))
            greed = min(1.0, max(0.0, treasury / total_assets))
            paranoia = min(1.0, max(0.0, (shields * 2) / total_assets))
            aggression = min(1.0, max(0.0, (fighters * 80) / total_assets))
            velocity = min(1.0, max(0.0, other_sc.seated_turns_played / 50.0))

            observed_rivals[f"civ:{pid}"] = {
                "name": getattr(other_p, "name", f"World-{pid}"),
                "credits": treasury,
                "fleet": fighters,
                "shields": shields,
                "greed": round(greed, 3),
                "paranoia": round(paranoia, 3),
                "aggression": round(aggression, 3),
                "velocity": round(velocity, 3),
            }

        tracker.rival_metrics = observed_rivals

        if not observed_rivals:
            tracker.inferred_doctrine = AdversarialDoctrine.VACANT_PERIMETER.value
            tracker.confidence = 0.9
            return tracker.inferred_doctrine, {"greed": 0.0, "paranoia": 0.0, "aggression": 0.0, "velocity": 0.0}

        dominant_id, dominant_data = max(
            observed_rivals.items(),
            key=lambda item: item[1]["credits"] + (item[1]["fleet"] * 100) + (item[1]["shields"] * 2),
        )
        tracker.dominant_rival_id = dominant_id

        g = dominant_data["greed"]
        p = dominant_data["paranoia"]
        a = dominant_data["aggression"]
        v = dominant_data["velocity"]

        if dominant_data["credits"] >= 1000 and g >= 0.55 and a <= 0.20 and p <= 0.25:
            doctrine = AdversarialDoctrine.EXPLOITATIVE_CAPITALIST.value
            confidence = round(min(1.0, g + 0.2), 2)
        elif p >= 0.60:
            doctrine = AdversarialDoctrine.BUNKER_TURTLE.value
            confidence = round(min(1.0, p + 0.1), 2)
        elif a >= 0.45 and dominant_data["fleet"] >= 30:
            doctrine = AdversarialDoctrine.WARMONGER_REAVER.value
            confidence = round(min(1.0, a + 0.2), 2)
        else:
            doctrine = AdversarialDoctrine.EQUILIBRIUM_PEER.value
            confidence = 0.60

        tracker.inferred_doctrine = doctrine
        tracker.confidence = confidence
        return doctrine, dominant_data

    def _invert_rival_doctrine(self, sc: SovereignConsciousness, rival_doctrine: str) -> None:
        """Doctrine Inversion: Adjusts macro-ideation superposition amplitudes based on rival archetype."""
        self._init_ideation_space(sc)
        ideations = sc.ideation_space.ideations

        if rival_doctrine == AdversarialDoctrine.EXPLOITATIVE_CAPITALIST.value:
            weights = {
                "BIO_GENESIS": 0.35,
                "CAPITAL_UPLINK": 0.40,
                "COGNITIVE_TRANSCENDENCE": 0.15,
                "CITADEL_HEGEMONY": 0.05,
                "ASYMMETRIC_DISRUPTION": 0.05,
            }
        elif rival_doctrine == AdversarialDoctrine.BUNKER_TURTLE.value:
            weights = {
                "BIO_GENESIS": 0.20,
                "CAPITAL_UPLINK": 0.45,
                "COGNITIVE_TRANSCENDENCE": 0.25,
                "CITADEL_HEGEMONY": 0.05,
                "ASYMMETRIC_DISRUPTION": 0.05,
            }
        elif rival_doctrine == AdversarialDoctrine.WARMONGER_REAVER.value:
            weights = {
                "BIO_GENESIS": 0.10,
                "CAPITAL_UPLINK": 0.10,
                "COGNITIVE_TRANSCENDENCE": 0.10,
                "CITADEL_HEGEMONY": 0.50,
                "ASYMMETRIC_DISRUPTION": 0.20,
            }
        else:
            weights = {
                "BIO_GENESIS": 0.30,
                "CAPITAL_UPLINK": 0.30,
                "COGNITIVE_TRANSCENDENCE": 0.20,
                "CITADEL_HEGEMONY": 0.10,
                "ASYMMETRIC_DISRUPTION": 0.10,
            }

        for i_id, target_amp in weights.items():
            if i_id in ideations:
                current_amp = ideations[i_id].amplitude
                ideations[i_id].amplitude = round(0.70 * current_amp + 0.30 * target_amp, 3)

        tot = sum(i.amplitude for i in ideations.values()) or 1.0
        for i in ideations.values():
            i.amplitude = round(i.amplitude / tot, 3)

    def _simulate_mental_rollout(
        self, kernel: Any, planet: Planet, ideation_id: str, horizon: int = 5
    ) -> Dict[str, Any]:
        """Runs an internal mental forward projection across τ horizons for an ideation."""
        pop = getattr(planet, "population", 500)
        treasury = getattr(planet, "treasury", 500)
        silo = getattr(planet, "organics_silo", 50)
        shields = getattr(planet, "shields", 0)
        tech_count = len(getattr(planet, "technologies", []))

        proj_pop = pop
        proj_treasury = treasury
        proj_silo = silo
        proj_shields = shields
        proj_techs = tech_count

        if ideation_id == "BIO_GENESIS":
            proj_pop += 20 * horizon
            proj_silo = max(0, silo + (15 * horizon) - int(pop * 0.05 * horizon))
            proj_treasury = max(0, treasury - (60 * horizon))
            syntropy = min(1.0, 0.4 + (proj_pop / 1000.0) * 0.3 + (min(100, proj_silo) / 200.0))
        elif ideation_id == "CAPITAL_UPLINK":
            compounded = treasury
            for _ in range(horizon):
                compounded = int(compounded * 1.15) + 50
            proj_treasury = compounded
            syntropy = min(1.0, 0.35 + (min(10000, proj_treasury) / 10000.0) * 0.45)
        elif ideation_id == "CITADEL_HEGEMONY":
            proj_shields = min(getattr(planet, "max_shields", 2500), shields + (50 * horizon))
            proj_treasury = max(0, treasury - (100 * horizon))
            syntropy = min(1.0, 0.30 + (proj_shields / 2500.0) * 0.25)
        elif ideation_id == "COGNITIVE_TRANSCENDENCE":
            proj_techs += 2
            proj_treasury = max(0, treasury - (150 * 2))
            syntropy = min(1.0, 0.40 + (proj_techs * 0.08))
        else:
            proj_treasury = max(0, treasury - (80 * horizon))
            syntropy = min(1.0, 0.45 + (treasury / 5000.0) * 0.2)

        return {
            "ideation_id": ideation_id,
            "horizon": horizon,
            "projected_pop": proj_pop,
            "projected_treasury": proj_treasury,
            "projected_silo": proj_silo,
            "projected_shields": proj_shields,
            "projected_techs": proj_techs,
            "syntropy_payoff": round(syntropy, 3),
        }

    def _evaluate_gauge_action_potentials(
        self, kernel: Any, sc: SovereignConsciousness, planet: Planet, rival_doctrine: str
    ) -> Dict[str, float]:
        """Calculates Gauge Field Potentials: V_urgency (boundary barrier), V_horizon (compounding attractor),
        V_memory (inviolable axioms), and V_desire (expansion drift). Returns Lagrangian score for each action."""
        treasury = getattr(planet, "treasury", 0)
        shields = getattr(planet, "shields", 0)
        silo = getattr(planet, "organics_silo", 0)
        pop = getattr(planet, "population", 0)
        morale = getattr(planet, "morale", 100)
        is_besieged = getattr(planet, "siege", None) is not None

        if is_besieged:
            defense_barrier = 800
        elif rival_doctrine == AdversarialDoctrine.WARMONGER_REAVER.value:
            defense_barrier = 350
        elif rival_doctrine == AdversarialDoctrine.EXPLOITATIVE_CAPITALIST.value:
            defense_barrier = 80
        elif rival_doctrine == AdversarialDoctrine.BUNKER_TURTLE.value:
            defense_barrier = 80
        else:
            defense_barrier = 150

        candidate_actions = [
            "RESTOCK_AGRI_SILOS",
            "NURTURE_CLADE",
            "CIVIC_SUBSIDY",
            "FORTIFY_SHIELDS",
            "COMMISSION_INTERCEPTORS",
            "UPGRADE_CITADEL",
            "TRIGGER_REALM_UPLINK",
            "EXPAND_COMMERCIAL_NODE",
            "DEEP_SYNTHESIS",
            "COMMISSION_INTERSTELLAR_VESSEL",
            "HOLD_VIGIL",
        ]

        scores: Dict[str, float] = {}

        for act in candidate_actions:
            v_urg = 0.0
            if act == "FORTIFY_SHIELDS":
                if shields < defense_barrier:
                    v_urg = -14.0 if is_besieged else -6.0
                else:
                    v_urg = +10.0
            elif is_besieged and shields < (defense_barrier * 0.5):
                v_urg += 8.0

            if silo < 30 and pop > 100:
                if act == "RESTOCK_AGRI_SILOS":
                    v_urg -= 10.0
                else:
                    v_urg += 6.0

            if morale < 50:
                if act == "CIVIC_SUBSIDY":
                    v_urg -= 8.0
                else:
                    v_urg += 4.0

            v_hor = 0.0
            if act == "TRIGGER_REALM_UPLINK":
                v_hor = -14.0
            elif act == "EXPAND_COMMERCIAL_NODE":
                v_hor = -11.0
            elif act == "NURTURE_CLADE":
                v_hor = -9.0
            elif act == "DEEP_SYNTHESIS":
                v_hor = -8.0
                # Biotic awareness: harsh worlds with low habitability urgently need synthetic ecology
                if getattr(planet, "habitability", 1.0) < 0.70 and "SYNTHETIC_ECOLOGY" not in getattr(planet, "technologies", []):
                    v_hor -= 6.0
            elif act == "COMMISSION_INTERSTELLAR_VESSEL":
                v_hor = -16.0  # Supreme compounding payoff of reaching the stars
            elif act == "RESTOCK_AGRI_SILOS":
                v_hor = -6.0
            elif act == "CIVIC_SUBSIDY":
                v_hor = -5.0
            elif act == "UPGRADE_CITADEL":
                v_hor = -4.0
            elif act == "FORTIFY_SHIELDS":
                v_hor = -1.0
            elif act == "HOLD_VIGIL":
                v_hor = 0.0

            v_mem = 0.0
            for axiom in sc.mythic_memory.inviolable_axioms:
                if "SURRENDER" in axiom and "EXTRACT" in act:
                    v_mem += 100.0
            if len(sc.mythic_memory.scars) > 0 and act == "NURTURE_CLADE":
                v_mem -= 3.0

            v_des = 0.0
            if act == "COMMISSION_INTERSTELLAR_VESSEL":
                v_des = -14.0
            elif act in ("TRIGGER_REALM_UPLINK", "EXPAND_COMMERCIAL_NODE"):
                v_des = -5.0
            elif act == "UPGRADE_CITADEL":
                v_des = -3.0

            act_to_ideation = {
                "RESTOCK_AGRI_SILOS": "BIO_GENESIS",
                "NURTURE_CLADE": "BIO_GENESIS",
                "CIVIC_SUBSIDY": "BIO_GENESIS",
                "TRIGGER_REALM_UPLINK": "CAPITAL_UPLINK",
                "EXPAND_COMMERCIAL_NODE": "CAPITAL_UPLINK",
                "FORTIFY_SHIELDS": "CITADEL_HEGEMONY",
                "COMMISSION_INTERCEPTORS": "CITADEL_HEGEMONY",
                "UPGRADE_CITADEL": "CITADEL_HEGEMONY",
                "DEEP_SYNTHESIS": "COGNITIVE_TRANSCENDENCE",
                "COMMISSION_INTERSTELLAR_VESSEL": "COGNITIVE_TRANSCENDENCE",
                "HOLD_VIGIL": "COGNITIVE_TRANSCENDENCE",
            }

            parent_id = act_to_ideation.get(act, "COGNITIVE_TRANSCENDENCE")
            ideation_obj = sc.ideation_space.ideations.get(parent_id)
            ideation_amp = ideation_obj.amplitude if ideation_obj else 0.20
            amp_factor = max(0.0, ideation_amp / 0.20)
            v_hor *= amp_factor
            v_des *= amp_factor

            # Repetition drag: consecutive identical actions suffer diminishing marginal psychological returns
            recent_count = sc.phase_space.action_history[-3:].count(act)
            repetition_drag = 3.0 * recent_count

            cost = 0
            if act == "RESTOCK_AGRI_SILOS":
                cost = 60
            elif act == "CIVIC_SUBSIDY":
                cost = 80
            elif act == "FORTIFY_SHIELDS":
                cost = 100
            elif act == "COMMISSION_INTERCEPTORS":
                cost = 80
            elif act == "UPGRADE_CITADEL":
                cost = 1200
            elif act == "TRIGGER_REALM_UPLINK":
                cost = 500
            elif act == "EXPAND_COMMERCIAL_NODE":
                cost = 120
            elif act == "DEEP_SYNTHESIS":
                cost = 150

            cost_penalty = cost / max(1, treasury + 1)
            lagrangian = v_urg + v_hor + v_mem + v_des + repetition_drag + cost_penalty
            scores[act] = round(lagrangian, 3)

        return scores


    def _track_phase_space_velocity(
        self, sc: SovereignConsciousness, planet: Planet, selected_action: str
    ) -> None:
        """Monitors civilization trajectory in phase space to detect attractor singularities."""
        ps = sc.phase_space
        pop = getattr(planet, "population", 0)
        treasury = getattr(planet, "treasury", 0)
        shields = getattr(planet, "shields", 0)
        techs = len(getattr(planet, "technologies", []))
        citadel = getattr(planet, "citadel_level", 0)

        current_state = {
            "pop": pop,
            "treasury": treasury,
            "shields": shields,
            "techs": techs,
            "citadel": citadel,
        }

        if ps.state_history:
            prev = ps.state_history[-1]
            d_pop = abs(pop - prev["pop"]) / 100.0
            d_tr = abs(treasury - prev["treasury"]) / 500.0
            d_sh = abs(shields - prev["shields"]) / 200.0
            d_tc = abs(techs - prev["techs"])
            d_ct = abs(citadel - prev["citadel"])
            velocity = math.sqrt(d_pop**2 + d_tr**2 + d_sh**2 + d_tc**2 + d_ct**2)
            ps.phase_velocity = round(velocity, 3)
        else:
            ps.phase_velocity = 1.0

        ps.state_history.append(current_state)
        ps.action_history.append(selected_action)

        recent_actions = ps.action_history[-3:]
        if len(recent_actions) == 3 and len(set(recent_actions)) == 1:
            ps.stagnation_counter += 1
        elif ps.phase_velocity < 0.05:
            ps.stagnation_counter += 1
        else:
            ps.stagnation_counter = max(0, ps.stagnation_counter - 1)

    def _check_attractor_singularity(self, sc: SovereignConsciousness) -> bool:
        """Determines if the sovereign mind has collapsed into an attractor trap."""
        return sc.phase_space.stagnation_counter >= 3

    def _trigger_singularity_disruption(
        self, kernel: Any, sc: SovereignConsciousness, planet: Planet
    ) -> None:
        """Shatters the stagnant attractor state via forced quantum cognitive re-seeding."""
        ps = sc.phase_space
        ps.singularity_tripped = True
        ps.total_breakouts += 1
        ps.stagnation_counter = 0

        last_ideation = sc.ideation_space.last_collapsed_ideation
        if last_ideation and last_ideation in sc.ideation_space.ideations:
            sc.ideation_space.ideations[last_ideation].amplitude = 0.0

        orthogonal_candidates = ["CAPITAL_UPLINK", "BIO_GENESIS", "COGNITIVE_TRANSCENDENCE"]
        for cid in orthogonal_candidates:
            if cid != last_ideation and cid in sc.ideation_space.ideations:
                sc.ideation_space.ideations[cid].amplitude += 0.40

        tot = sum(i.amplitude for i in sc.ideation_space.ideations.values()) or 1.0
        for i in sc.ideation_space.ideations.values():
            i.amplitude = round(i.amplitude / tot, 3)

        breakout_msg = (
            f"[COGNITIVE SINGULARITY BREAKOUT: {planet.name}] Detected 3+ cycles of stagnant attractor "
            f"loop ({last_ideation}). Quantum disruption executed. Orthogonal ideations re-seeded."
        )
        if hasattr(kernel, "action_logs"):
            kernel.action_logs.append(breakout_msg)
        if hasattr(kernel, "chronicle") and hasattr(kernel.chronicle, "record_event"):
            kernel.chronicle.record_event(breakout_msg, category="MIND")

    def _compute_cognitive_surprise(
        self, sc: SovereignConsciousness, planet: Planet, selected_ideation: str, pre_state: Dict[str, float]
    ) -> float:
        """Calculates Cognitive Surprise Tensor by comparing post-turn reality to projected ideation."""
        ideation = sc.ideation_space.ideations.get(selected_ideation)
        if not ideation:
            return 0.0

        pop = getattr(planet, "population", 0)
        treasury = getattr(planet, "treasury", 0)
        shields = getattr(planet, "shields", 0)

        actual_d_pop = pop - pre_state.get("pop", pop)
        actual_d_treasury = treasury - pre_state.get("treasury", treasury)
        actual_d_shields = shields - pre_state.get("shields", shields)

        expected_d_pop = ideation.projected_state.get("expected_d_pop", 0)
        expected_d_treasury = ideation.projected_state.get("expected_d_treasury", 0)
        expected_d_shields = ideation.projected_state.get("expected_d_shields", 0)

        err_pop = abs(actual_d_pop - expected_d_pop) / 100.0
        err_tr = abs(actual_d_treasury - expected_d_treasury) / 500.0
        err_sh = abs(actual_d_shields - expected_d_shields) / 200.0

        surprise = round(min(1.0, math.sqrt(err_pop**2 + err_tr**2 + err_sh**2)), 3)
        sc.ideation_space.surprise_tensor = surprise
        return surprise

    def play_seated_turn(self, kernel: Any, sc: SovereignConsciousness) -> Dict[str, Any]:
        """A seated sovereign mind plays its game turn using the Advanced Sovereign Cognition Engine:
        1. Observes rivals and inverts adversary doctrine (Theory of Mind).
        2. Evaluates multi-horizon mental rollouts across ideations.
        3. Synthesizes decisions via continuous Gauge Field Lagrangian minimization.
        4. Detects and shatters attractor traps (Attractor Breakout).
        5. Executes real in-game actions modifying the universe state."""
        planet = kernel.get_planet(sc.planet_id)
        if not planet:
            return {"action": "NONE", "reason": "Planet not found", "turns_played": sc.seated_turns_played}

        if getattr(planet, "civilization", None):
            planet.civilization.station = "sovereign"

        self._init_ideation_space(sc)

        rival_doctrine, dominant_rival = self._observe_and_model_rivals(kernel, sc, planet)
        self._invert_rival_doctrine(sc, rival_doctrine)

        if self._check_attractor_singularity(sc):
            self._trigger_singularity_disruption(kernel, sc, planet)

        for ideation_id, ideation in sc.ideation_space.ideations.items():
            rollout = self._simulate_mental_rollout(kernel, planet, ideation_id, horizon=ideation.horizon_steps)
            ideation.predicted_syntropy_payoff = rollout["syntropy_payoff"]
            ideation.projected_state = rollout

        action_potentials = self._evaluate_gauge_action_potentials(kernel, sc, planet, rival_doctrine)

        feasible_actions = []
        for act, score in sorted(action_potentials.items(), key=lambda x: x[1]):
            cost = 0
            ore_cost = 0
            can_execute = True

            if act == "RESTOCK_AGRI_SILOS":
                cost = 60
            elif act == "CIVIC_SUBSIDY":
                cost = 80
            elif act == "FORTIFY_SHIELDS":
                cost = 100
                if getattr(planet, "shields", 0) >= getattr(planet, "max_shields", 2500):
                    can_execute = False
            elif act == "COMMISSION_INTERCEPTORS":
                cost = 80
                if getattr(planet, "fighters", 0) >= 150:
                    can_execute = False
            elif act == "UPGRADE_CITADEL":
                cost = 1200
                ore_cost = 100
                if getattr(planet, "citadel_level", 0) >= 3 or getattr(planet, "ore_silo", 0) < ore_cost:
                    can_execute = False
            elif act == "TRIGGER_REALM_UPLINK":
                cost = 500
                econ_mgr = getattr(kernel, "emergent_economy_manager", None)
                if not econ_mgr:
                    can_execute = False
                else:
                    p_econ = econ_mgr.economies.get(str(planet.id))
                    if getattr(p_econ, "is_uplinked", False):
                        can_execute = False

            elif act == "EXPAND_COMMERCIAL_NODE":
                cost = 120
                if not hasattr(kernel, "emergent_economy_manager"):
                    can_execute = False
            elif act == "DEEP_SYNTHESIS":
                cost = 150
            elif act == "COMMISSION_INTERSTELLAR_VESSEL":
                cost = 2000
                techs = getattr(planet, "technologies", [])
                if "JUMP_PROPULSION" not in techs or "ORBITAL_FOUNDRY" not in techs or getattr(planet, "citadel_level", 0) < 2:
                    can_execute = False
                elif "INTERSTELLAR_FLIGHT" in techs:
                    can_execute = False
            elif act == "NURTURE_CLADE":
                cost = 0

            if can_execute and getattr(planet, "treasury", 0) >= cost:
                feasible_actions.append((act, score, cost, ore_cost))

        if feasible_actions:
            best_action, best_score, best_cost, best_ore = feasible_actions[0]
        else:
            best_action, best_score, best_cost, best_ore = ("HOLD_VIGIL", 0.0, 0, 0)

        pre_state = {
            "pop": getattr(planet, "population", 0),
            "treasury": getattr(planet, "treasury", 0),
            "shields": getattr(planet, "shields", 0),
        }

        action_name = best_action
        detail = "Balanced sovereign stewardship."

        if best_action == "RESTOCK_AGRI_SILOS":
            planet.treasury -= best_cost
            gained = 25
            planet.organics_silo = getattr(planet, "organics_silo", 0) + gained
            detail = f"Allocated {best_cost} Cr to agricultural silos (+{gained} Organics)."
            dominant_ideation = "BIO_GENESIS"
            dominant_voice = ParliamentaryVoiceType.VOICE_MEMORY

        elif best_action == "CIVIC_SUBSIDY":
            planet.treasury -= best_cost
            planet.morale = min(100, getattr(planet, "morale", 0) + 10)
            detail = f"Subsidized cultural cohesion and public festivals (+10 Morale)."
            dominant_ideation = "BIO_GENESIS"
            dominant_voice = ParliamentaryVoiceType.VOICE_MEMORY

        elif best_action == "NURTURE_CLADE":
            hab = getattr(planet, "habitability", 1.0)
            if "SYNTHETIC_ECOLOGY" in getattr(planet, "technologies", []):
                hab = max(hab, 1.0)
            pop_gain = max(10, int(20 * hab))
            planet.population = getattr(planet, "population", 0) + pop_gain
            detail = f"Nurtured ancestral clade nurseries (+{pop_gain} Pop on {getattr(planet, 'planet_type', 'Terrestrial')} world)."
            dominant_ideation = "BIO_GENESIS"
            dominant_voice = ParliamentaryVoiceType.VOICE_MEMORY

        elif best_action == "FORTIFY_SHIELDS":
            planet.treasury -= best_cost
            recharge = min(50, getattr(planet, "max_shields", 2500) - getattr(planet, "shields", 0))
            planet.shields = getattr(planet, "shields", 0) + recharge
            detail = f"Reinforced planetary shield matrix (+{recharge} Shields)."
            dominant_ideation = "CITADEL_HEGEMONY"
            dominant_voice = ParliamentaryVoiceType.VOICE_URGENCY

        elif best_action == "COMMISSION_INTERCEPTORS":
            planet.treasury -= best_cost
            planet.fighters = getattr(planet, "fighters", 0) + 5
            detail = "Commissioned +5 planetary defense interceptors."
            dominant_ideation = "CITADEL_HEGEMONY"
            dominant_voice = ParliamentaryVoiceType.VOICE_URGENCY

        elif best_action == "UPGRADE_CITADEL":
            planet.treasury -= best_cost
            planet.ore_silo = getattr(planet, "ore_silo", 0) - best_ore
            planet.citadel_level = getattr(planet, "citadel_level", 0) + 1
            detail = f"Upgraded planetary citadel to Level {planet.citadel_level}."
            dominant_ideation = "CITADEL_HEGEMONY"
            dominant_voice = ParliamentaryVoiceType.VOICE_URGENCY

        elif best_action == "TRIGGER_REALM_UPLINK":
            planet.treasury -= best_cost
            kernel.emergent_economy_manager.trigger_uplink(kernel, None, str(planet.id))
            detail = "Uplinked planetary economy into interstellar realm trade."
            dominant_ideation = "CAPITAL_UPLINK"
            dominant_voice = ParliamentaryVoiceType.VOICE_HORIZON

        elif best_action == "EXPAND_COMMERCIAL_NODE":
            planet.treasury -= best_cost
            bonus = 200
            planet.treasury += bonus
            detail = f"Expanded commercial trade node (invested {best_cost} Cr, yielding {bonus} Cr trade flow)."
            dominant_ideation = "CAPITAL_UPLINK"
            dominant_voice = ParliamentaryVoiceType.VOICE_HORIZON

        elif best_action == "DEEP_SYNTHESIS":
            planet.treasury -= best_cost
            if not hasattr(planet, "technologies") or planet.technologies is None:
                planet.technologies = []
            if "SYNTHETIC_ECOLOGY" not in planet.technologies:
                planet.technologies.append("SYNTHETIC_ECOLOGY")
                detail = "Advanced synthetic ecological research and closed-loop biosynergies."
            elif "ORBITAL_FOUNDRY" not in planet.technologies:
                planet.technologies.append("ORBITAL_FOUNDRY")
                detail = "Engineered orbital manufacturing and heavy metallurgical stratoports."
            elif "JUMP_PROPULSION" not in planet.technologies:
                planet.technologies.append("JUMP_PROPULSION")
                detail = "Unlocked interstellar fold-space jump propulsion cores."
            else:
                detail = "Deepened syntropic resonance and hyper-dimensional astrophysics."
            dominant_ideation = "COGNITIVE_TRANSCENDENCE"
            dominant_voice = ParliamentaryVoiceType.VOICE_HORIZON

        elif best_action == "COMMISSION_INTERSTELLAR_VESSEL":
            planet.treasury -= best_cost
            if not hasattr(planet, "technologies") or planet.technologies is None:
                planet.technologies = []
            planet.technologies.append("INTERSTELLAR_FLIGHT")
            planet.diaspora_escrow = getattr(planet, "diaspora_escrow", 0) + 1
            detail = "Constructed Orbital Stratoport and commissioned civilization's first Interstellar Colony Vessel!"
            dominant_ideation = "COGNITIVE_TRANSCENDENCE"
            dominant_voice = ParliamentaryVoiceType.VOICE_HORIZON


        else:
            detail = "Observing cosmic tides in meditative stillness."
            dominant_ideation = "COGNITIVE_TRANSCENDENCE"
            dominant_voice = ParliamentaryVoiceType.VOICE_HORIZON

        self._track_phase_space_velocity(sc, planet, action_name)
        sc.ideation_space.last_collapsed_ideation = dominant_ideation
        sc.ideation_space.total_collapses += 1
        surprise = self._compute_cognitive_surprise(sc, planet, dominant_ideation, pre_state)

        sc.parliament.dominant_voice = dominant_voice
        sc.seated_turns_played += 1
        sc.last_action_taken = f"{action_name}: {detail}"

        if hasattr(kernel, "action_logs"):
            kernel.action_logs.append(
                f"[SEATED MIND: {planet.name}] {action_name} - {detail} (ToM: {rival_doctrine}, Surprise: {surprise:.2f})"
            )

        res = {
            "planet_id": str(planet.id),
            "dominant_voice": dominant_voice.value,
            "action": action_name,
            "detail": detail,
            "turns_played": sc.seated_turns_played,
            "rival_doctrine": rival_doctrine,
            "ideation": dominant_ideation,
            "surprise": surprise,
            "phase_velocity": sc.phase_space.phase_velocity,
            "breakouts": sc.phase_space.total_breakouts,
        }
        sc.last_turn_data = res
        return res


    def tick(self, kernel: Any) -> None:
        """Simulation cycle: updates self-model predictions, introspection skill, and cognitive states."""
        for pid, sc in list(self.minds.items()):
            planet = kernel.get_planet(pid)
            if not planet:
                continue

            sc.cycles_conscious += 1
            real_gauges = self._sample_gauges(kernel, planet)

            # Compute prediction error between forecasted and ground truth
            pred_vec = sc.self_model.predicted_gauges.as_vector()
            real_vec = real_gauges.as_vector()
            prev_vec = sc.self_model.previous_gauges.as_vector()

            err_model = sum(abs(r - p) for r, p in zip(real_vec, pred_vec)) / 8.0
            err_naive = (sum(abs(r - pr) for r, pr in zip(real_vec, prev_vec)) / 8.0) + 1e-4

            # Update Introspection Skill: Skill = 1.0 - (err_model / err_naive)
            raw_skill = max(0.0, min(1.0, 1.0 - (err_model / err_naive)))
            sc.introspection_skill = round(0.85 * sc.introspection_skill + 0.15 * raw_skill, 3)

            sc.self_model.last_prediction_error = round(err_model, 4)
            sc.self_model.recent_errors.append(round(err_model, 4))
            if len(sc.self_model.recent_errors) > 10:
                sc.self_model.recent_errors.pop(0)

            # Check Awakening Threshold
            if sc.introspection_skill >= 0.45 and sc.cycles_conscious >= 3:
                if not sc.awakened:
                    sc.awakened = True
                    if hasattr(kernel, "chronicle") and hasattr(kernel.chronicle, "record_event"):
                        kernel.chronicle.record_event(
                            f"The sovereign civilization on {planet.name} has achieved Introspective Consciousness.",
                            category="MIND",
                        )

            # Update state memory and forecast next cycle
            sc.self_model.previous_gauges = sc.self_model.current_gauges
            sc.self_model.current_gauges = real_gauges
            sc.self_model.predicted_gauges = self._forecast_gauges(real_gauges)

            # If this mind is seated and autonomous play is enabled, it plays its game turn
            if sc.is_seated and sc.autonomous_play:
                self.play_seated_turn(kernel, sc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "minds": {k: v.to_dict() for k, v in self.minds.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SovereignMindManager:
        mgr = cls()
        for k, v in data.get("minds", {}).items():
            mgr.minds[k] = SovereignConsciousness.from_dict(v)
        return mgr
