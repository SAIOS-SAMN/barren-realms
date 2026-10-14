"""
xylarium/kernel/conclave.py

Project Landing 3: The Pan-Galactic Conclave & Interstellar Law ("The League of Worlds").

Dynamic interstellar governance where sovereign realms, corporate syndicates,
and ancient Progenitors clash over binding galactic policy:
  - Dynamic Voting Weight:
    Calculated from GDP (treasury/credits), fleet tonnage, and Progenitor syntropic authority.
  - Binding Galactic Resolutions:
    1. The Syntropic Concordat (outlaws reckless metric tearing, reducing global entropy).
    2. The Sanctuary Worlds Act (protects primitive nursery worlds from sovereign exploitation).
    3. The Free Navigation Accords (caps wormhole tolls and harmonizes trade).
    4. Anti-Piracy Mobilization (mandates joint armadas and doubles bounties).
    5. Precursor Non-Proliferation (restricts rogue excavation of high-tier ruins).
  - Interstellar Sanctions & Diplomatic Pressure.
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
import random
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


STANDARD_RESOLUTIONS: Dict[str, Dict[str, Any]] = {
    "RES_SYNTROPIC_CONCORDAT": {
        "name": "The Syntropic Concordat",
        "description": "Outlaws unshielded star-lifting and metric torsion tearing; soothes galactic entropy strain (-25).",
        "category": "ECOLOGY",
    },
    "RES_SANCTUARY_WORLDS": {
        "name": "The Sanctuary Worlds Act",
        "description": "Grants extraterritorial legal protection to nascent nursery worlds, penalizing foreign exploiters.",
        "category": "STEWARDSHIP",
    },
    "RES_FREE_NAVIGATION": {
        "name": "Free Navigation Accords",
        "description": "Standardizes trade lanes and prohibits predatory wormhole gate tolls in high-traffic sectors.",
        "category": "COMMERCE",
    },
    "RES_ANTI_PIRACY": {
        "name": "Galactic Anti-Piracy Mobilization",
        "description": "Deploys joint hegemony patrols to outer rim sectors; doubles bounties on criminal captains.",
        "category": "SECURITY",
    },
    "RES_PRECURSOR_TREATY": {
        "name": "Precursor Non-Proliferation Treaty",
        "description": "Restricts unauthorized deep-core weaponization of ancient Precursor archaeological relics.",
        "category": "ARCHAEOLOGY",
    },
}


@dataclass
class ConclaveResolution:
    id: str
    key: str
    name: str
    description: str
    sponsor_id: str
    votes_for: int = 0
    votes_against: int = 0
    status: str = "PROPOSED"  # "PROPOSED", "PASSED", "REJECTED"
    passed_cycle: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConclaveResolution:
        return cls(**data)


class PanGalacticConclaveManager:
    """Manages the Pan-Galactic Assembly, voting weights, and binding galactic directives."""

    def __init__(self) -> None:
        self.active_laws: Dict[str, ConclaveResolution] = {}
        self.proposals: Dict[str, ConclaveResolution] = {}
        self.session_cycle: int = 1
        self.counter: int = 1

    def calculate_voting_weight(self, kernel: Any, captain_id: str) -> int:
        """Calculates voting weight based on GDP, armada defense, and Progenitor syntropy."""
        captain = kernel.captains.get(captain_id)
        if not captain:
            return 10

        weight = 10
        # Economic power: 1 vote per 50,000 credits
        weight += captain.credits // 50000

        # Military power: fleet fighters and planetary citadels
        weight += captain.ship.fighters // 10
        for s in kernel.sectors.values():
            for p in getattr(s, "planets", []):
                if getattr(p, "owner_id", None) == captain_id:
                    weight += p.citadel_level * 5

        # Progenitor power: uploaded population & syntropic resilience
        if hasattr(kernel, "epoch_manager"):
            rec = kernel.epoch_manager.records.get(captain_id)
            if rec:
                weight += int(rec.syntropic_resilience // 10)
                if rec.phase.value == "STEWARDSHIP":
                    weight += 50  # Ancient moral authority veto weighting

        return max(10, weight)

    def sponsor_resolution(
        self,
        kernel: Any,
        captain: Captain,
        resolution_key: str,
    ) -> ActionResult:
        """Sponsors a new resolution before the Pan-Galactic Assembly."""
        key = resolution_key.upper().strip()
        if key not in STANDARD_RESOLUTIONS:
            return ActionResult(
                success=False,
                action=ActionType.CONCLAVE_SPONSOR_RESOLUTION,
                message=f"Unknown resolution '{resolution_key}'. Valid resolutions: {list(STANDARD_RESOLUTIONS.keys())}.",
            )

        if key in self.active_laws:
            return ActionResult(
                success=False,
                action=ActionType.CONCLAVE_SPONSOR_RESOLUTION,
                message=f"'{STANDARD_RESOLUTIONS[key]['name']}' is already active galactic law.",
            )

        res_id = f"RES-{self.counter:03d}"
        self.counter += 1

        bp = STANDARD_RESOLUTIONS[key]
        resolution = ConclaveResolution(
            id=res_id,
            key=key,
            name=bp["name"],
            description=bp["description"],
            sponsor_id=captain.id,
        )

        # Automatic initial sponsor vote
        v_weight = self.calculate_voting_weight(kernel, captain.id)
        resolution.votes_for += v_weight

        self.proposals[res_id] = resolution

        if hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender="CONCLAVE_SPEAKER",
                text=f"A new galactic bill '{resolution.name}' has been proposed by {captain.name} with {v_weight} sponsor votes!",
                channel="COSMIC_BROADCAST",
            )
        kernel.action_logs.append(f"[CONCLAVE] Sponsored resolution '{resolution.name}'.")

        return ActionResult(
            success=True,
            action=ActionType.CONCLAVE_SPONSOR_RESOLUTION,
            turns_spent=1,
            message=f"RESOLUTION SPONSORED: '{resolution.name}' [{res_id}] placed on the Assembly floor with {v_weight} initial votes.",
            data={"resolution": resolution.to_dict()},
        )

    def cast_vote(
        self,
        kernel: Any,
        captain: Captain,
        resolution_id: str,
        in_favor: bool = True,
    ) -> ActionResult:
        """Casts parliamentary voting weight on an active resolution proposal."""
        res = self.proposals.get(resolution_id)
        if not res:
            return ActionResult(
                success=False,
                action=ActionType.CONCLAVE_CAST_VOTE,
                message=f"Resolution proposal '{resolution_id}' not found on the Assembly floor.",
            )

        weight = self.calculate_voting_weight(kernel, captain.id)
        if in_favor:
            res.votes_for += weight
        else:
            res.votes_against += weight

        # Evaluate if bill passes (threshold 100 net votes)
        if res.votes_for >= 100 and res.votes_for > res.votes_against:
            res.status = "PASSED"
            res.passed_cycle = kernel.cycle_count
            self.active_laws[res.key] = res
            del self.proposals[resolution_id]

            self._apply_passed_law_effect(kernel, res)
            msg = f"VOTE RECORDED: Resolution '{res.name}' HAS PASSED INTO BINDING GALACTIC LAW!"
        elif res.votes_against >= 100 and res.votes_against > res.votes_for:
            res.status = "REJECTED"
            del self.proposals[resolution_id]
            msg = f"VOTE RECORDED: Resolution '{res.name}' has been rejected by the Assembly."
        else:
            msg = f"VOTE RECORDED: Added {weight} votes {'FOR' if in_favor else 'AGAINST'} '{res.name}'. Current tally: {res.votes_for} For / {res.votes_against} Against."

        kernel.action_logs.append(f"[CONCLAVE] Voted on '{res.name}'.")
        return ActionResult(
            success=True,
            action=ActionType.CONCLAVE_CAST_VOTE,
            turns_spent=1,
            message=msg,
            data={"resolution": res.to_dict()},
        )

    def _apply_passed_law_effect(self, kernel: Any, res: ConclaveResolution) -> None:
        """Applies physical and macroeconomic effects of passed galactic laws."""
        if res.key == "RES_SYNTROPIC_CONCORDAT":
            if hasattr(kernel, "epoch_manager"):
                kernel.epoch_manager.global_entropy_strain = max(0.0, kernel.epoch_manager.global_entropy_strain - 25.0)
                for rec in kernel.epoch_manager.records.values():
                    rec.entropy_strain = max(0.0, rec.entropy_strain - 25.0)

        elif res.key == "RES_SANCTUARY_WORLDS":
            if hasattr(kernel, "clade_nursery_manager"):
                for clade in kernel.clade_nursery_manager.clades.values():
                    clade.reverence_pct = min(100.0, clade.reverence_pct + 20.0)

        elif res.key == "RES_ANTI_PIRACY":
            # Boost bounties across all AI pirate captains
            for cap in kernel.captains.values():
                if getattr(cap, "personality", None) and cap.personality.value == "pirate":
                    cap.bounty = int(cap.bounty * 2.0) + 5000

        if hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender="CONCLAVE_GAZETTE",
                text=f"[NEW GALACTIC LAW ENACTED] '{res.name}' is now binding across all 100 sectors of the cluster!",
                channel="COSMIC_BROADCAST",
            )

    def enforce_sanctions(
        self,
        kernel: Any,
        captain: Captain,
        target_captain_id: str,
    ) -> ActionResult:
        """Enacts economic trade embargo and sanctions against a rival rogue faction."""
        target = kernel.captains.get(target_captain_id)
        if not target:
            return ActionResult(
                success=False,
                action=ActionType.CONCLAVE_ENFORCE_SANCTIONS,
                message=f"Target Captain '{target_captain_id}' not found.",
            )

        if captain.id not in target.embargoed_by:
            target.embargoed_by.append(captain.id)

        target.credit_rating = max(100, target.credit_rating - 75)
        kernel.action_logs.append(f"[CONCLAVE] Enacted Assembly sanctions against {target.name}.")

        return ActionResult(
            success=True,
            action=ActionType.CONCLAVE_ENFORCE_SANCTIONS,
            turns_spent=1,
            message=f"CONCLAVE SANCTIONS IMPOSED: Embargo placed on {target.name}. Trade credit rating downgraded (-75).",
            data={"target": target.name, "credit_rating": target.credit_rating},
        )

    def tick(self, kernel: Any) -> None:
        """Cycle tick: AI factions cast votes on open proposals."""
        self.session_cycle += 1
        for p_id, res in list(self.proposals.items()):
            # Simulate voting from major AI factions
            rng = random.Random(kernel.seed + self.session_cycle + hash(p_id))
            ai_votes = rng.randint(5, 20)
            if rng.random() > 0.35:
                res.votes_for += ai_votes
            else:
                res.votes_against += ai_votes

            # Auto-resolution check
            if res.votes_for >= 100 and res.votes_for > res.votes_against:
                res.status = "PASSED"
                res.passed_cycle = kernel.cycle_count
                self.active_laws[res.key] = res
                del self.proposals[p_id]
                self._apply_passed_law_effect(kernel, res)
            elif res.votes_against >= 100 and res.votes_against > res.votes_for:
                res.status = "REJECTED"
                del self.proposals[p_id]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_laws": {k: v.to_dict() for k, v in self.active_laws.items()},
            "proposals": {k: v.to_dict() for k, v in self.proposals.items()},
            "session_cycle": self.session_cycle,
            "counter": self.counter,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PanGalacticConclaveManager:
        mgr = cls()
        mgr.session_cycle = int(data.get("session_cycle", 1))
        mgr.counter = int(data.get("counter", 1))
        for k, v in data.get("active_laws", {}).items():
            mgr.active_laws[k] = ConclaveResolution.from_dict(v)
        for k, v in data.get("proposals", {}).items():
            mgr.proposals[k] = ConclaveResolution.from_dict(v)
        return mgr
