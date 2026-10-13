"""
Ideology and Dual Cohesion Ledger Engine for Xylarium.
Ported from Netstratum 09_IDEOLOGY and 25_STANDING.
Social thermodynamics over four deterministic behavioral ledgers:
- Compassion: Humanitarian relief given in famine vs drawn
- Resonance: Bilateral bond flow vs severance load
- Integrity: Contracts and covenants fulfilled vs breached
- Morality: Fair value returned vs predatory piracy extracted
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import time

from xylarium.config import (
    IDEOLOGY_RATIO_MIN_TREATY,
    IDEOLOGY_RATIO_SANCTION,
    IDEOLOGY_FAMINE_AID_SYNTROPY,
    IDEOLOGY_CONTRACT_BREACH_ENTROPY,
    IDEOLOGY_PIRACY_ENTROPY,
)
from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet


class TreatyType(str, Enum):
    NON_AGGRESSION = "NON_AGGRESSION"
    TRADE_ACCORD = "TRADE_ACCORD"
    DEFENSIVE_PACT = "DEFENSIVE_PACT"
    ALLIANCE = "ALLIANCE"
    SANCTION = "SANCTION"
    BILATERAL_TRADE_COMPACT = "BILATERAL_TRADE_COMPACT"


@dataclass
class CohesionLedger:
    """
    Four-axis dual ledger tracking exact physical deeds between two entities.
    Every axis pairs syntropic (cooperative/constructive) and entropic (destructive/extractive) counters.
    """
    compassion_syntropic: float = 0.0
    compassion_entropic: float = 0.0
    resonance_syntropic: float = 0.0
    resonance_entropic: float = 0.0
    integrity_syntropic: float = 0.0
    integrity_entropic: float = 0.0
    morality_syntropic: float = 0.0
    morality_entropic: float = 0.0

    def get_axis_ratio(self, axis: str) -> float:
        """Returns syntropic / (syntropic + entropic) in [0.0, 1.0]. Defaults to 0.50 if unbooked."""
        if axis == "compassion":
            s, e = self.compassion_syntropic, self.compassion_entropic
        elif axis == "resonance":
            s, e = self.resonance_syntropic, self.resonance_entropic
        elif axis == "integrity":
            s, e = self.integrity_syntropic, self.integrity_entropic
        elif axis == "morality":
            s, e = self.morality_syntropic, self.morality_entropic
        else:
            return 0.50

        total = s + e
        if total <= 0:
            return 0.50
        return round(s / total, 3)

    @property
    def overall_syntropy(self) -> float:
        """Composite social alignment ratio across all four axes."""
        ratios = [
            self.get_axis_ratio("compassion"),
            self.get_axis_ratio("resonance"),
            self.get_axis_ratio("integrity"),
            self.get_axis_ratio("morality"),
        ]
        return round(sum(ratios) / len(ratios), 3)

    def stress_energy_tensor(self) -> List[List[float]]:
        """Construct the 4x4 Cohesion Stress-Energy Tensor T_ab across behavioral axes."""
        # Vector of net signed deed flux: (syntropic - entropic)
        v = [
            self.compassion_syntropic - self.compassion_entropic,
            self.resonance_syntropic - self.resonance_entropic,
            self.integrity_syntropic - self.integrity_entropic,
            self.morality_syntropic - self.morality_entropic,
        ]
        # Outer product T_ab = v_a * v_b with self-interaction trace
        tensor = [[round(v[i] * v[j] + (1.0 if i == j else 0.0), 3) for j in range(4)] for i in range(4)]
        return tensor

    @property
    def manifold_volume(self) -> float:
        """Compute the continuous 4-volume of the relationship manifold sqrt(det(T + I)).
        
        Distinguishes rich, multi-faceted alliances from flat 1D transactional alignments.
        """
        # Magnitudes along the 4 independent orthogonal axes
        mags = [
            1.0 + abs(self.compassion_syntropic - self.compassion_entropic),
            1.0 + abs(self.resonance_syntropic - self.resonance_entropic),
            1.0 + abs(self.integrity_syntropic - self.integrity_entropic),
            1.0 + abs(self.morality_syntropic - self.morality_entropic),
        ]
        vol = mags[0] * mags[1] * mags[2] * mags[3]
        return round(vol, 3)

    def record_deed(self, axis: str, amount: float, is_syntropic: bool) -> None:
        if amount <= 0:
            return
        if axis == "compassion":
            if is_syntropic:
                self.compassion_syntropic += amount
            else:
                self.compassion_entropic += amount
        elif axis == "resonance":
            if is_syntropic:
                self.resonance_syntropic += amount
            else:
                self.resonance_entropic += amount
        elif axis == "integrity":
            if is_syntropic:
                self.integrity_syntropic += amount
            else:
                self.integrity_entropic += amount
        elif axis == "morality":
            if is_syntropic:
                self.morality_syntropic += amount
            else:
                self.morality_entropic += amount

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compassion_syntropic": self.compassion_syntropic,
            "compassion_entropic": self.compassion_entropic,
            "resonance_syntropic": self.resonance_syntropic,
            "resonance_entropic": self.resonance_entropic,
            "integrity_syntropic": self.integrity_syntropic,
            "integrity_entropic": self.integrity_entropic,
            "morality_syntropic": self.morality_syntropic,
            "morality_entropic": self.morality_entropic,
            "overall_syntropy": self.overall_syntropy,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CohesionLedger":
        return cls(
            compassion_syntropic=float(data.get("compassion_syntropic", 0.0)),
            compassion_entropic=float(data.get("compassion_entropic", 0.0)),
            resonance_syntropic=float(data.get("resonance_syntropic", 0.0)),
            resonance_entropic=float(data.get("resonance_entropic", 0.0)),
            integrity_syntropic=float(data.get("integrity_syntropic", 0.0)),
            integrity_entropic=float(data.get("integrity_entropic", 0.0)),
            morality_syntropic=float(data.get("morality_syntropic", 0.0)),
            morality_entropic=float(data.get("morality_entropic", 0.0)),
        )


@dataclass
class Treaty:
    id: str
    signatory_a: str
    signatory_b: str
    treaty_type: TreatyType
    signed_cycle: int
    duration_cycles: int = 150
    tariff_discount_pct: int = 15
    active: bool = True
    mining_concession: bool = False
    joint_security: bool = False
    bilateral_quota_commodity: Optional[str] = None
    bilateral_quota_units: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signatory_a": self.signatory_a,
            "signatory_b": self.signatory_b,
            "treaty_type": self.treaty_type.value,
            "signed_cycle": self.signed_cycle,
            "duration_cycles": self.duration_cycles,
            "tariff_discount_pct": self.tariff_discount_pct,
            "active": self.active,
            "mining_concession": self.mining_concession,
            "joint_security": self.joint_security,
            "bilateral_quota_commodity": self.bilateral_quota_commodity,
            "bilateral_quota_units": self.bilateral_quota_units,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Treaty":
        return cls(
            id=data["id"],
            signatory_a=data["signatory_a"],
            signatory_b=data["signatory_b"],
            treaty_type=TreatyType(data["treaty_type"]),
            signed_cycle=data["signed_cycle"],
            duration_cycles=data.get("duration_cycles", 150),
            tariff_discount_pct=data.get("tariff_discount_pct", 15),
            active=data.get("active", True),
            mining_concession=bool(data.get("mining_concession", False)),
            joint_security=bool(data.get("joint_security", False)),
            bilateral_quota_commodity=data.get("bilateral_quota_commodity"),
            bilateral_quota_units=int(data.get("bilateral_quota_units", 0)),
        )


class IdeologyManager:
    """
    Governs social thermodynamics, empirical diplomacy, and interstellar treaty networks.
    """

    def __init__(self):
        # Key: (min(id_a, id_b), max(id_a, id_b))
        self.ledgers: Dict[Tuple[str, str], CohesionLedger] = {}
        self.treaties: Dict[str, Treaty] = {}
        self.next_treaty_id: int = 1

    def _pair_key(self, a: str, b: str) -> Tuple[str, str]:
        return (a, b) if a <= b else (b, a)

    def get_ledger(self, entity_a: str, entity_b: str) -> CohesionLedger:
        key = self._pair_key(entity_a, entity_b)
        if key not in self.ledgers:
            self.ledgers[key] = CohesionLedger()
        return self.ledgers[key]

    def record_deed(
        self,
        actor_id: str,
        target_id: str,
        axis: str,
        amount: float,
        is_syntropic: bool,
    ) -> None:
        """Records an ideological deed between two entities."""
        ledger = self.get_ledger(actor_id, target_id)
        ledger.record_deed(axis, amount, is_syntropic)

    def get_standing(self, entity_a: str, entity_b: str) -> float:
        """Returns overall syntropic ratio in [0.0, 1.0]."""
        return self.get_ledger(entity_a, entity_b).overall_syntropy

    def get_summary(self, entity_id: str) -> Dict[str, Any]:
        """Provides summary of all cohesion ledgers and active treaties involving entity_id."""
        rel_ledgers = {}
        for (a, b), ledger in self.ledgers.items():
            if a == entity_id or b == entity_id:
                other = b if a == entity_id else a
                rel_ledgers[other] = {
                    "standing": round(ledger.overall_syntropy, 2),
                    "compassion": round(ledger.get_axis_ratio("compassion"), 2),
                    "resonance": round(ledger.get_axis_ratio("resonance"), 2),
                    "integrity": round(ledger.get_axis_ratio("integrity"), 2),
                    "morality": round(ledger.get_axis_ratio("morality"), 2),
                    "ledger": ledger.to_dict(),
                }

        my_treaties = [
            t.to_dict() for t in self.treaties.values()
            if (t.signatory_a == entity_id or t.signatory_b == entity_id) and t.active
        ]

        return {
            "entity_id": entity_id,
            "relationships": rel_ledgers,
            "active_treaties": my_treaties,
            "total_treaties": len(my_treaties),
        }

    def dispatch_famine_aid(
        self,
        sender_id: Optional[str] = None,
        planet_id: Optional[str] = None,
        amount_organics: int = 20,
        kernel: Any = None,
        captain: Any = None,
        target_planet: Any = None,
        food_units: Optional[int] = None,
    ) -> ActionResult:
        """
        Humanitarian relief: Dispatch food crates from ship hold to a starving colony.
        Awards syntropic points on the Compassion axis and lifts planetary morale.
        """
        if captain is not None:
            sender = captain
        elif kernel and sender_id:
            sender = kernel.captains.get(sender_id)
        else:
            sender = None

        if not sender:
            return ActionResult(False, ActionType.IDEOLOGY_AID_DISPATCH, "Captain not found.")

        if food_units is not None:
            amount_organics = food_units

        if target_planet is None and kernel and planet_id:
            for sec in kernel.sectors.values():
                for p in sec.planets:
                    if p.id == planet_id:
                        target_planet = p
                        break
                if target_planet:
                    break

        if not target_planet:
            return ActionResult(False, ActionType.IDEOLOGY_AID_DISPATCH, "Target colony not found.")

        if sender.sector_id != target_planet.sector_id:
            return ActionResult(
                False,
                ActionType.IDEOLOGY_AID_DISPATCH,
                f"You must be in Sector {target_planet.sector_id:03d} to dispatch aid to {target_planet.name}.",
            )

        # Aid is the recipient people's own staple: grain is no relief to a people that drinks ice
        from xylarium.kernel import staples
        food = staples.of(kernel, target_planet) if kernel is not None else "ORGANICS"
        if sender.ship.cargo.unbonded(food) < amount_organics or amount_organics <= 0:
            return ActionResult(
                False,
                ActionType.IDEOLOGY_AID_DISPATCH,
                f"The people of {target_planet.name} eat {food}: you hold {sender.ship.cargo.unbonded(food)} "
                f"unbonded ({amount_organics} offered).",
            )

        # Transfer food
        cargo = sender.ship.cargo
        if food == "ORGANICS":
            cargo.organics -= amount_organics
        elif food == "ORE":
            cargo.ore -= amount_organics
        else:
            cargo.elements[food] = cargo.elements.get(food, 0) - amount_organics
            if cargo.elements[food] <= 0:
                cargo.elements.pop(food, None)
        staples.move(target_planet, food, amount_organics)       # aid is delivered whole
        target_planet.morale = min(100, target_planet.morale + 15)

        recipient_id = target_planet.owner_id if target_planet.owner_id else f"civ_{target_planet.name}"
        # Record syntropic deed on Compassion axis
        self.record_deed(
            sender.id,
            recipient_id,
            "compassion",
            IDEOLOGY_FAMINE_AID_SYNTROPY * (amount_organics / 10.0),
            is_syntropic=True,
        )

        msg = f"HUMANITARIAN RELIEF: Dispatched {amount_organics} crates of Organics to {target_planet.name}! Morale rose to {target_planet.morale}%."
        if kernel and getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(
                sender=sender.name,
                text=msg,
                channel="COMM-1",
                sector_id=target_planet.sector_id,
            )
        if kernel and hasattr(kernel, "action_logs"):
            kernel.action_logs.append(f"[RELIEF] {sender.name} provided famine aid to {target_planet.name}.")

        return ActionResult(
            True,
            ActionType.IDEOLOGY_AID_DISPATCH,
            msg,
            data={"organics_delivered": amount_organics, "planet_morale": target_planet.morale},
        )

    def propose_treaty(
        self,
        proposer_id: Optional[str] = None,
        recipient_id: Optional[str] = None,
        treaty_type: TreatyType = TreatyType.NON_AGGRESSION,
        kernel: Any = None,
        proposer: Any = None,
        target_id: Optional[str] = None,
        duration: int = 150,
        captains: Optional[List[Any]] = None,
    ) -> ActionResult:
        """
        Propose a bilateral diplomatic treaty based on empirical cohesion ledger standing.
        Refuses if syntropic ratio is below threshold.
        """
        if proposer is not None:
            proposer_cap = proposer
            proposer_id = proposer.id
        elif kernel and proposer_id:
            proposer_cap = kernel.captains.get(proposer_id)
        else:
            proposer_cap = None

        if target_id is not None:
            recipient_id = target_id

        if captains:
            cap_map = {c.id: c for c in captains}
            recipient_cap = cap_map.get(recipient_id)
            if not proposer_cap and proposer_id in cap_map:
                proposer_cap = cap_map[proposer_id]
        elif kernel and recipient_id:
            recipient_cap = kernel.captains.get(recipient_id)
        else:
            recipient_cap = None

        if not proposer_cap:
            return ActionResult(False, ActionType.IDEOLOGY_TREATY_PROPOSE, "Proposer captain not found.")
        if not recipient_id:
            return ActionResult(False, ActionType.IDEOLOGY_TREATY_PROPOSE, "Target recipient required.")

        recipient_name = recipient_cap.name if recipient_cap else recipient_id

        standing = self.get_standing(proposer_id, recipient_id)
        if standing < IDEOLOGY_RATIO_MIN_TREATY and treaty_type in [TreatyType.DEFENSIVE_PACT, TreatyType.ALLIANCE]:
            return ActionResult(
                False,
                ActionType.IDEOLOGY_TREATY_PROPOSE,
                f"PROPOSAL REFUSED: Social syntropy ratio is {standing:.2f} (Minimum required: {IDEOLOGY_RATIO_MIN_TREATY:.2f}). Prove integrity through honest trade and deeds first.",
            )

        pair = self._pair_key(proposer_id, recipient_id)
        for t in self.treaties.values():
            if self._pair_key(t.signatory_a, t.signatory_b) == pair and t.treaty_type == treaty_type and t.active:
                return ActionResult(False, ActionType.IDEOLOGY_TREATY_PROPOSE, f"{treaty_type.value} already active between signatories.")

        tid = f"treaty_{self.next_treaty_id}"
        self.next_treaty_id += 1

        cycle = kernel.cycle_count if kernel else 0
        new_treaty = Treaty(
            id=tid,
            signatory_a=proposer_id,
            signatory_b=recipient_id,
            treaty_type=treaty_type,
            signed_cycle=cycle,
            duration_cycles=duration,
        )
        self.treaties[tid] = new_treaty

        # Rewarded with resonance on both ends
        self.record_deed(proposer_id, recipient_id, "resonance", 20.0, is_syntropic=True)

        msg = f"TREATY ENACTED: {proposer_cap.name} and {recipient_name} signed {treaty_type.value}! (+15% trade tariff discount applied across mutual holdings)."
        if kernel and getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(
                sender="FED-DIPLO",
                text=msg,
                channel="SYSTEM",
                sector_id=1,
            )
        if kernel and hasattr(kernel, "action_logs"):
            kernel.action_logs.append(f"[TREATY] {proposer_cap.name} and {recipient_name} signed {treaty_type.value}.")

        return ActionResult(
            True,
            ActionType.IDEOLOGY_TREATY_PROPOSE,
            msg,
            data={"treaty_id": tid, "treaty_type": treaty_type.value},
        )

    def sign_treaty(
        self,
        recipient_id: Optional[str] = None,
        treaty_id: str = "",
        kernel: Any = None,
        signer: Any = None,
    ) -> ActionResult:
        """Ratifies and signs an active or pending treaty."""
        signer_id = signer.id if signer else recipient_id
        if treaty_id not in self.treaties:
            return ActionResult(False, ActionType.IDEOLOGY_TREATY_SIGN, f"Treaty ID '{treaty_id}' not found.")
        treaty = self.treaties[treaty_id]
        if signer_id and signer_id not in [treaty.signatory_a, treaty.signatory_b]:
            return ActionResult(False, ActionType.IDEOLOGY_TREATY_SIGN, "You are not a named signatory of this treaty.")
        newly_ratified = not treaty.active
        treaty.active = True
        if newly_ratified and kernel is not None:
            from xylarium.kernel.experience import ExperienceManager
            from xylarium.config import XP_GOVERNANCE_TREATY
            for party_id in (treaty.signatory_a, treaty.signatory_b):
                party = kernel.captains.get(party_id) if hasattr(kernel, "captains") else None
                if party:
                    ExperienceManager.award(party, "governance", XP_GOVERNANCE_TREATY, kernel, key=f"treaty:{treaty_id}")
        return ActionResult(
            True,
            ActionType.IDEOLOGY_TREATY_SIGN,
            f"Treaty {treaty_id} ratified and active.",
            data=treaty.to_dict(),
        )

    def negotiate_civilization_compact(
        self,
        proposer_id: str,
        civilization_name: str,
        terms: Optional[Dict[str, Any]] = None,
        kernel: Any = None,
    ) -> ActionResult:
        """
        Negotiates a bilateral trade compact with a sovereign planetary civilization.
        Evaluates SU(2) epistemic worldview resonance, moral standing, and treaty covenants:
        - 100% tariff exemption in territorial sectors
        - Exclusive or authorized mining concessions in planetary asteroid belts
        - Mutual naval escort defense against raiders
        """
        if not kernel:
            return ActionResult(False, ActionType.TRADE_COMPACT_NEGOTIATE, "Simulation kernel required.")

        proposer_cap = kernel.captains.get(proposer_id)
        if not proposer_cap:
            return ActionResult(False, ActionType.TRADE_COMPACT_NEGOTIATE, "Proposer captain not found.")

        # Locate civilization across all charted worlds
        c_query = civilization_name.strip().lower()
        target_civ = None
        target_world = None
        for sec in kernel.sectors.values():
            for pl in sec.planets:
                civ = getattr(pl, "civilization", None)
                if civ and (c_query in civ.name.lower() or civ.name.lower() in c_query):
                    target_civ = civ
                    target_world = pl
                    break
            if target_civ:
                break

        if not target_civ:
            return ActionResult(
                False,
                ActionType.TRADE_COMPACT_NEGOTIATE,
                f"Civilization '{civilization_name}' could not be located in charted space.",
            )

        civ_entity_id = f"civ:{target_civ.name}"

        # Check existing active compact
        pair = self._pair_key(proposer_id, civ_entity_id)
        for t in self.treaties.values():
            if self._pair_key(t.signatory_a, t.signatory_b) == pair and t.treaty_type == TreatyType.BILATERAL_TRADE_COMPACT and t.active:
                return ActionResult(
                    False,
                    ActionType.TRADE_COMPACT_NEGOTIATE,
                    f"Active Bilateral Trade Compact already in effect with {target_civ.name} (Treaty {t.id}).",
                )

        # Evaluate SU(2) Epistemic Resonance
        onto = getattr(target_civ, "epistemic_ontology", None)
        resonance = 0.5
        if onto and hasattr(onto, "quaternion"):
            from xylarium.kernel import physics
            q_civ = onto.quaternion()
            rot_z = (hash(proposer_cap.id) % 360) * (3.14159 / 180.0)
            q_cap = physics.Quaternion.from_axis_angle((0.0, 0.0, 1.0), rot_z)
            q_rel = q_cap.conjugate() * q_civ
            resonance = max(-1.0, min(1.0, q_rel.w))

        standing = self.get_standing(proposer_id, civ_entity_id)

        # Rejection only if severe epistemic polarization and low standing
        if resonance < -0.70 and standing < 0.30:
            return ActionResult(
                False,
                ActionType.TRADE_COMPACT_NEGOTIATE,
                f"COMPACT REJECTED: The Council of {target_civ.name} rejected terms due to severe epistemic dissonance "
                f"(SU(2) Holonomy Resonance: {resonance:.2f}, Standing: {standing:.2f}). Enhance cooperation first.",
                data={"resonance": resonance, "standing": standing},
            )

        # Parse terms
        terms = terms or {}
        duration = int(terms.get("duration", 200))
        quota_comm = terms.get("quota_commodity", "ORE")
        quota_units = int(terms.get("quota_units", 100))

        tid = f"compact_{self.next_treaty_id}"
        self.next_treaty_id += 1

        compact = Treaty(
            id=tid,
            signatory_a=proposer_id,
            signatory_b=civ_entity_id,
            treaty_type=TreatyType.BILATERAL_TRADE_COMPACT,
            signed_cycle=kernel.cycle_count,
            duration_cycles=duration,
            tariff_discount_pct=100,
            active=True,
            mining_concession=True,
            joint_security=True,
            bilateral_quota_commodity=quota_comm,
            bilateral_quota_units=quota_units,
        )
        self.treaties[tid] = compact

        # Reward syntropic deeds on ledger (+40.0 resonance, +25.0 integrity)
        self.record_deed(proposer_id, civ_entity_id, "resonance", 40.0, is_syntropic=True)
        self.record_deed(proposer_id, civ_entity_id, "integrity", 25.0, is_syntropic=True)

        from xylarium.kernel.experience import ExperienceManager
        ExperienceManager.award(proposer_cap, "governance", 25, kernel, key=f"compact:{tid}")

        msg = (
            f"BILATERAL TRADE COMPACT RATIFIED: {proposer_cap.name} and the {target_civ.name} "
            f"concluded diplomatic accords! Granted 100% tariff exemption, mining concessions in {target_world.name}'s system, "
            f"and mutual naval security escorts. (Resonance: {resonance:.2f}, Standing: {standing:.2f})"
        )
        if kernel.event_bus:
            kernel.event_bus.broadcast_radio(
                sender="DIPLO-ACCORD",
                text=msg,
                channel="SYSTEM",
                sector_id=target_world.sector_id,
            )
        if hasattr(kernel, "action_logs"):
            kernel.action_logs.append(f"[DIPLOMACY] {msg}")

        return ActionResult(
            True,
            ActionType.TRADE_COMPACT_NEGOTIATE,
            msg,
            data={"treaty": compact.to_dict(), "resonance": resonance, "civilization": target_civ.name},
        )

    def tick_ideology(self, kernel: Any) -> None:
        """Advance treaty expiration and autonomous diplomatic alignment."""
        cur_cycle = kernel.cycle_count
        for tid, t in list(self.treaties.items()):
            if t.active and cur_cycle - t.signed_cycle >= t.duration_cycles:
                t.active = False
                sig_a = kernel.captains.get(t.signatory_a)
                sig_b = kernel.captains.get(t.signatory_b)
                name_a = sig_a.name if sig_a else t.signatory_a
                name_b = sig_b.name if sig_b else t.signatory_b
                if kernel.event_bus:
                    kernel.event_bus.broadcast_radio(
                        sender="FED-DIPLO",
                        text=f"TREATY SUNSET: {t.treaty_type.value} between {name_a} and {name_b} has expired.",
                        channel="SYSTEM",
                        sector_id=1,
                    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ledgers": {
                f"{k[0]}|{k[1]}": v.to_dict()
                for k, v in self.ledgers.items()
            },
            "treaties": {tid: t.to_dict() for tid, t in self.treaties.items()},
            "next_treaty_id": self.next_treaty_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IdeologyManager":
        mgr = cls()
        mgr.next_treaty_id = data.get("next_treaty_id", 1)
        for k_str, l_data in data.get("ledgers", {}).items():
            parts = k_str.split("|")
            if len(parts) == 2:
                mgr.ledgers[(parts[0], parts[1])] = CohesionLedger.from_dict(l_data)
        for tid, t_data in data.get("treaties", {}).items():
            mgr.treaties[tid] = Treaty.from_dict(t_data)
        return mgr
