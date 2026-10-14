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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planet_id": self.planet_id,
            "planet_name": self.planet_name,
            "awakened": self.awakened,
            "cycles_conscious": self.cycles_conscious,
            "introspection_skill": self.introspection_skill,
            "alignment": self.alignment,
            "self_model": self.self_model.to_dict(),
            "counterfactual": self.counterfactual.to_dict(),
            "parliament": self.parliament.to_dict(),
            "mythic_memory": self.mythic_memory.to_dict(),
            "conduct_books": {k: v.to_dict() for k, v in self.conduct_books.items()},
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
            self_model=SelfModel.from_dict(data.get("self_model", {})),
            counterfactual=CounterfactualEngine.from_dict(data.get("counterfactual", {})),
            parliament=DialecticalParliament.from_dict(data.get("parliament", {})),
            mythic_memory=MythicMemoryGraph.from_dict(data.get("mythic_memory", {})),
            conduct_books={k: ConductBook.from_dict(v) for k, v in data.get("conduct_books", {}).items()},
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
