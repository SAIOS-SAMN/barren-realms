"""
The Imperial Senate & High Offices of the Union for Xylarium.
Ported from Netstratum 30_OFFICES_AND_RAILS and 49_TAXATION.
Manages democratic/oligarchic governance of the Sol Federation,
four High Offices of State, electoral cycles, voting rights, and systemic Edicts.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import time

from xylarium.config import (
    SENATE_ELECTION_INTERVAL,
    SENATE_OFFICE_TERM_LENGTH,
    SENATE_CAMPAIGN_FEE,
    SENATE_EDICT_COOLDOWN,
)
from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet


class SenateOffice(str, Enum):
    CHANCELLOR = "CHANCELLOR"              # Head of Government; diplomatic & economic leader
    FLEET_ADMIRAL = "FLEET_ADMIRAL"        # Supreme Commander of Federal Navy; security & borders
    MASTER_OF_COIN = "MASTER_OF_COIN"      # Minister of the Treasury & ISSE Trade Oversight
    HIGH_INQUISITOR = "HIGH_INQUISITOR"    # Director of Espionage, Science & Precursor Secrets


class SenateEdict(str, Enum):
    UNIVERSAL_TARIFF = "UNIVERSAL_TARIFF"                    # Adjusts market tariffs across Federation
    MARTIAL_LAW_PICKET = "MARTIAL_LAW_PICKET"                # Deploys Federal Gunboats to suppress piracy
    SOL_STIMULUS_REBATE = "SOL_STIMULUS_REBATE"              # Distributes federal surplus to colonies & captains
    PRECURSOR_DECLASSIFICATION = "PRECURSOR_DECLASSIFICATION"# Declassifies precursor vaults (-25% research cost)


@dataclass
class HighOfficeHolder:
    office: SenateOffice
    incumbent_id: Optional[str]
    incumbent_name: str
    elected_cycle: int
    term_expires_cycle: int
    last_edict_cycle: int = -999

    def to_dict(self) -> Dict[str, Any]:
        return {
            "office": self.office.value,
            "incumbent_id": self.incumbent_id,
            "incumbent_name": self.incumbent_name,
            "elected_cycle": self.elected_cycle,
            "term_expires_cycle": self.term_expires_cycle,
            "last_edict_cycle": self.last_edict_cycle,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HighOfficeHolder":
        return cls(
            office=SenateOffice(data["office"]),
            incumbent_id=data.get("incumbent_id"),
            incumbent_name=data.get("incumbent_name", "Vacant"),
            elected_cycle=data.get("elected_cycle", 0),
            term_expires_cycle=data.get("term_expires_cycle", 60),
            last_edict_cycle=data.get("last_edict_cycle", -999),
        )


@dataclass
class ActiveEdict:
    edict: SenateEdict
    enacted_by_office: SenateOffice
    enacted_by_id: str
    enacted_by_name: str
    enacted_cycle: int
    duration_cycles: int
    magnitude: float
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edict": self.edict.value,
            "enacted_by_office": self.enacted_by_office.value,
            "enacted_by_id": self.enacted_by_id,
            "enacted_by_name": self.enacted_by_name,
            "enacted_cycle": self.enacted_cycle,
            "duration_cycles": self.duration_cycles,
            "magnitude": self.magnitude,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActiveEdict":
        return cls(
            edict=SenateEdict(data["edict"]),
            enacted_by_office=SenateOffice(data["enacted_by_office"]),
            enacted_by_id=data["enacted_by_id"],
            enacted_by_name=data["enacted_by_name"],
            enacted_cycle=data["enacted_cycle"],
            duration_cycles=data["duration_cycles"],
            magnitude=data["magnitude"],
            description=data["description"],
        )


class SenateManager:
    """
    Simulates the Imperial Senate:
    Tracks office holders, open campaigns, voting tallies, active imperial edicts,
    and the central federal treasury.
    """

    def __init__(
        self,
        offices: Optional[Dict[str, HighOfficeHolder]] = None,
        candidates: Optional[Dict[str, List[str]]] = None,
        votes: Optional[Dict[str, Dict[str, float]]] = None,
        active_edicts: Optional[List[ActiveEdict]] = None,
        federal_treasury: int = 100000,
        current_cycle: int = 0,
        next_election_cycle: int = SENATE_ELECTION_INTERVAL,
    ):
        # The federal treasury is the Federation's vault (counted money, government.py) once bound to a kernel
        self.kernel: Any = None
        self._treasury: int = federal_treasury
        self.current_cycle: int = current_cycle
        self.next_election_cycle: int = next_election_cycle

        # Default starting incumbents if none provided
        if offices is None:
            self.offices: Dict[str, HighOfficeHolder] = {
                SenateOffice.CHANCELLOR.value: HighOfficeHolder(
                    office=SenateOffice.CHANCELLOR,
                    incumbent_id="npc_voss",
                    incumbent_name="Director Cynthia Voss",
                    elected_cycle=0,
                    term_expires_cycle=SENATE_OFFICE_TERM_LENGTH,
                ),
                SenateOffice.FLEET_ADMIRAL.value: HighOfficeHolder(
                    office=SenateOffice.FLEET_ADMIRAL,
                    incumbent_id="npc_thorne",
                    incumbent_name="Admiral Marcus Thorne",
                    elected_cycle=0,
                    term_expires_cycle=SENATE_OFFICE_TERM_LENGTH,
                ),
                SenateOffice.MASTER_OF_COIN.value: HighOfficeHolder(
                    office=SenateOffice.MASTER_OF_COIN,
                    incumbent_id="npc_mercer",
                    incumbent_name="Auditor Elias Mercer",
                    elected_cycle=0,
                    term_expires_cycle=SENATE_OFFICE_TERM_LENGTH,
                ),
                SenateOffice.HIGH_INQUISITOR.value: HighOfficeHolder(
                    office=SenateOffice.HIGH_INQUISITOR,
                    incumbent_id="npc_khor",
                    incumbent_name="Inquisitor Valen Khor",
                    elected_cycle=0,
                    term_expires_cycle=SENATE_OFFICE_TERM_LENGTH,
                ),
            }
        else:
            self.offices = offices

        # office -> list of candidate captain IDs
        self.candidates: Dict[str, List[str]] = candidates if candidates is not None else {
            o.value: [] for o in SenateOffice
        }
        # office -> {candidate_id: total_vote_weight}
        self.votes: Dict[str, Dict[str, float]] = votes if votes is not None else {
            o.value: {} for o in SenateOffice
        }
        self.active_edicts: List[ActiveEdict] = active_edicts if active_edicts is not None else []

    def bind(self, kernel: Any, genesis: bool = False) -> None:
        """Back the federal treasury with the Federation's vault. At genesis the founding treasury is placed there
        (genesis stock, before the money baseline); a loaded game's vault is already restored with the factions."""
        self.kernel = kernel
        fed = kernel.factions.factions.get("FEDERATION") if (kernel is not None and hasattr(kernel, "factions")) else None
        if fed is not None and genesis:
            fed.vault["SOL"] = fed.vault.get("SOL", 0) + self._treasury

    def _fed(self) -> Any:
        k = self.kernel
        return k.factions.factions.get("FEDERATION") if k is not None and hasattr(k, "factions") else None

    @property
    def federal_treasury(self) -> int:
        fed = self._fed()
        return int(fed.vault.get("SOL", 0)) if fed is not None else self._treasury

    @federal_treasury.setter
    def federal_treasury(self, value: int) -> None:
        fed = self._fed()
        if fed is not None:
            fed.vault["SOL"] = int(value)
        else:
            self._treasury = int(value)

    def _pay_planet(self, planet: Any, sol: int) -> None:
        """A SOL payout to a world lands in its own money (cleared through the exchanges)."""
        cur = getattr(planet, "currency", "SOL")
        if cur != "SOL" and self.kernel is not None:
            sol = self.kernel.fx_market.swap_sol_to(cur, sol)
        planet.treasury += sol

    def to_dict(self) -> Dict[str, Any]:
        return {
            "federal_treasury": self.federal_treasury,
            "current_cycle": self.current_cycle,
            "next_election_cycle": self.next_election_cycle,
            "offices": {k: v.to_dict() for k, v in self.offices.items()},
            "candidates": {k: list(v) for k, v in self.candidates.items()},
            "votes": {k: dict(v) for k, v in self.votes.items()},
            "active_edicts": [e.to_dict() for e in self.active_edicts],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SenateManager":
        offices = {}
        for k, v in data.get("offices", {}).items():
            offices[k] = HighOfficeHolder.from_dict(v)

        edicts = [ActiveEdict.from_dict(e) for e in data.get("active_edicts", [])]

        return cls(
            offices=offices,
            candidates=data.get("candidates", {}),
            votes=data.get("votes", {}),
            active_edicts=edicts,
            federal_treasury=data.get("federal_treasury", 100000),
            current_cycle=data.get("current_cycle", 0),
            next_election_cycle=data.get("next_election_cycle", SENATE_ELECTION_INTERVAL),
        )

    def calculate_voting_weight(self, captain: Captain, owned_planets: List[Planet]) -> float:
        """
        Calculates democratic/oligarchic voting weight for a captain.
        Based on net worth, personal score, and governed planetary populations.
        """
        credits_weight = captain.credits / 1000.0
        score_weight = captain.score / 100.0
        pop_weight = sum([p.population for p in owned_planets]) / 500.0
        return max(1.0, round(credits_weight + score_weight + pop_weight, 2))

    def register_candidate(self, captain: Captain, office: SenateOffice) -> ActionResult:
        """
        Files candidacy for High Office, deducting the official campaign filing fee.
        """
        if captain.credits < SENATE_CAMPAIGN_FEE:
            return ActionResult(
                success=False,
                message=f"Insufficient credits for campaign filing fee ({captain.credits}/{SENATE_CAMPAIGN_FEE} Cr).",
                action_type=ActionType.SENATE_CAMPAIGN,
            )

        office_key = office.value
        if office_key not in self.candidates:
            self.candidates[office_key] = []

        if captain.id in self.candidates[office_key]:
            return ActionResult(
                success=False,
                message=f"Captain {captain.name} is already an active candidate for {office.name}.",
                action_type=ActionType.SENATE_CAMPAIGN,
            )

        captain.credits -= SENATE_CAMPAIGN_FEE
        self.federal_treasury += SENATE_CAMPAIGN_FEE
        self.candidates[office_key].append(captain.id)

        # Initialize candidate in vote tally
        if office_key not in self.votes:
            self.votes[office_key] = {}
        if captain.id not in self.votes[office_key]:
            self.votes[office_key][captain.id] = 0.0

        return ActionResult(
            success=True,
            message=f"Candidacy filed! {captain.name} is on the ballot for High Office: {office.name}. (Fee: {SENATE_CAMPAIGN_FEE} Cr)",
            action_type=ActionType.SENATE_CAMPAIGN,
            data={"office": office.value, "candidate_id": captain.id},
        )

    def cast_vote(
        self,
        voter: Captain,
        office: SenateOffice,
        candidate_id: str,
        owned_planets: List[Planet],
    ) -> ActionResult:
        """
        Casts voting weight behind a registered candidate for High Office.
        """
        office_key = office.value
        cands = self.candidates.get(office_key, [])
        if candidate_id not in cands:
            return ActionResult(
                success=False,
                message=f"Candidate ID '{candidate_id}' is not on the ballot for {office.name}.",
                action_type=ActionType.SENATE_VOTE,
            )

        weight = self.calculate_voting_weight(voter, owned_planets)
        if office_key not in self.votes:
            self.votes[office_key] = {}

        self.votes[office_key][candidate_id] = self.votes[office_key].get(candidate_id, 0.0) + weight

        return ActionResult(
            success=True,
            message=f"Voted cast! {voter.name} pledged {weight:.1f} electoral weight for candidate in {office.name}.",
            action_type=ActionType.SENATE_VOTE,
            data={"office": office.value, "candidate_id": candidate_id, "weight": weight},
        )

    def enact_edict(
        self,
        captain: Captain,
        office: SenateOffice,
        edict: SenateEdict,
        captains: List[Captain],
        planets: List[Planet],
    ) -> ActionResult:
        """
        Proclaims an imperial edict from an elected High Office.
        """
        holder = self.offices.get(office.value)
        if not holder or holder.incumbent_id != captain.id:
            return ActionResult(
                success=False,
                message=f"Forbidden: You do not hold the High Office of {office.name}.",
                action_type=ActionType.SENATE_ENACT_EDICT,
            )

        if (self.current_cycle - holder.last_edict_cycle) < SENATE_EDICT_COOLDOWN:
            cooldown_left = SENATE_EDICT_COOLDOWN - (self.current_cycle - holder.last_edict_cycle)
            return ActionResult(
                success=False,
                message=f"Office cooldown active. You must wait {cooldown_left} more cycles before enacting another edict.",
                action_type=ActionType.SENATE_ENACT_EDICT,
            )

        # Validate edict matches office jurisdiction
        valid_edicts = {
            SenateOffice.CHANCELLOR: [SenateEdict.SOL_STIMULUS_REBATE],
            SenateOffice.FLEET_ADMIRAL: [SenateEdict.MARTIAL_LAW_PICKET],
            SenateOffice.MASTER_OF_COIN: [SenateEdict.UNIVERSAL_TARIFF],
            SenateOffice.HIGH_INQUISITOR: [SenateEdict.PRECURSOR_DECLASSIFICATION],
        }

        if edict not in valid_edicts.get(office, []):
            return ActionResult(
                success=False,
                message=f"The office of {office.name} does not hold jurisdiction over edict {edict.name}.",
                action_type=ActionType.SENATE_ENACT_EDICT,
            )

        # Execute edict effects
        holder.last_edict_cycle = self.current_cycle

        if edict == SenateEdict.SOL_STIMULUS_REBATE:
            # Distribute 25% of federal treasury to all captains and colonies
            pool = int(self.federal_treasury * 0.25)
            self.federal_treasury -= pool
            num_targets = len(captains) + len(planets)
            payout = pool // max(1, num_targets)
            for c in captains:
                c.credits += payout
            for p in planets:
                self._pay_planet(p, payout)
            self.federal_treasury -= pool - payout * num_targets     # the rounding stays in the treasury

            active = ActiveEdict(
                edict=edict,
                enacted_by_office=office,
                enacted_by_id=captain.id,
                enacted_by_name=captain.name,
                enacted_cycle=self.current_cycle,
                duration_cycles=20,
                magnitude=payout,
                description=f"Sol Stimulus Rebate: Distributed {pool:,} Cr ({payout:,} Cr per recipient) to all citizens.",
            )
            self.active_edicts.append(active)
            return ActionResult(
                success=True,
                message=f"Proclamation issued! {active.description}",
                action_type=ActionType.SENATE_ENACT_EDICT,
                data=active.to_dict(),
            )

        elif edict == SenateEdict.MARTIAL_LAW_PICKET:
            cost = 15000
            self.federal_treasury = max(0, self.federal_treasury - cost)
            for p in planets:
                p.garrison_troops += 10
                p.fighters += 15

            active = ActiveEdict(
                edict=edict,
                enacted_by_office=office,
                enacted_by_id=captain.id,
                enacted_by_name=captain.name,
                enacted_cycle=self.current_cycle,
                duration_cycles=30,
                magnitude=15.0,
                description="Martial Law Picket: Federal naval escorts deployed across all sectors. Garrisons reinforced.",
            )
            self.active_edicts.append(active)
            return ActionResult(
                success=True,
                message=f"Naval Directive enacted! {active.description}",
                action_type=ActionType.SENATE_ENACT_EDICT,
                data=active.to_dict(),
            )

        elif edict == SenateEdict.UNIVERSAL_TARIFF:
            # Adjusts tariff by +3%
            active = ActiveEdict(
                edict=edict,
                enacted_by_office=office,
                enacted_by_id=captain.id,
                enacted_by_name=captain.name,
                enacted_cycle=self.current_cycle,
                duration_cycles=40,
                magnitude=0.03,
                description="Universal Commerce Tariff: Federal trade levy enacted (+3% tariff revenues channeled to treasury).",
            )
            self.active_edicts.append(active)
            return ActionResult(
                success=True,
                message=f"Treasury Act signed! {active.description}",
                action_type=ActionType.SENATE_ENACT_EDICT,
                data=active.to_dict(),
            )

        elif edict == SenateEdict.PRECURSOR_DECLASSIFICATION:
            # -25% research and discovery bonuses
            active = ActiveEdict(
                edict=edict,
                enacted_by_office=office,
                enacted_by_id=captain.id,
                enacted_by_name=captain.name,
                enacted_cycle=self.current_cycle,
                duration_cycles=40,
                magnitude=0.25,
                description="Precursor Archive Declassification: Subsidized research costs by 25% across all facilities.",
            )
            self.active_edicts.append(active)
            return ActionResult(
                success=True,
                message=f"Inquisitorial Warrant sealed! {active.description}",
                action_type=ActionType.SENATE_ENACT_EDICT,
                data=active.to_dict(),
            )

        return ActionResult(
            success=False,
            message="Unknown Senate Edict.",
            action_type=ActionType.SENATE_ENACT_EDICT,
        )

    def tick_senate(self, captains: List[Captain]) -> List[str]:
        """
        Advances the legislative cycle:
        - Expired edicts are retired
        - Electoral ballots are counted when cycle reaches next_election_cycle
        """
        events = []
        self.current_cycle += 1

        # 1. Prune expired edicts
        retained_edicts = []
        for e in self.active_edicts:
            if (self.current_cycle - e.enacted_cycle) >= e.duration_cycles:
                events.append(f"Imperial Edict Expired: {e.edict.value} ({e.description})")
            else:
                retained_edicts.append(e)
        self.active_edicts = retained_edicts

        # 2. Check election cycle
        if self.current_cycle >= self.next_election_cycle:
            events.extend(self._resolve_elections(captains))
            self.next_election_cycle = self.current_cycle + SENATE_ELECTION_INTERVAL

        return events

    def _resolve_elections(self, captains: List[Captain]) -> List[str]:
        """
        Counts ballots and inaugurates winners for each High Office.
        """
        events = []
        cap_lookup = {c.id: c for c in captains}

        for office_key, cand_list in self.candidates.items():
            holder = self.offices[office_key]
            tally = self.votes.get(office_key, {})

            if tally:
                # Winner is candidate with highest vote weight
                winner_id = max(tally.keys(), key=lambda cid: tally[cid])
                winner_votes = tally[winner_id]
                winner_name = cap_lookup[winner_id].name if winner_id in cap_lookup else winner_id

                holder.incumbent_id = winner_id
                holder.incumbent_name = winner_name
                holder.elected_cycle = self.current_cycle
                holder.term_expires_cycle = self.current_cycle + SENATE_OFFICE_TERM_LENGTH
                events.append(
                    f"ELECTION RESULT: {winner_name} elected {office_key} with {winner_votes:.1f} electoral votes!"
                )
            else:
                # No votes or candidates: incumbent retains or an NPC emerges
                events.append(f"ELECTION RESULT: {holder.incumbent_name} reconfirmed as {office_key} (uncontested).")
                holder.elected_cycle = self.current_cycle
                holder.term_expires_cycle = self.current_cycle + SENATE_OFFICE_TERM_LENGTH

            # Reset ballot for next cycle
            self.candidates[office_key] = []
            self.votes[office_key] = {}

        return events

    def get_active_edict_magnitude(self, edict: SenateEdict) -> float:
        """Returns the cumulative magnitude of an active edict, or 0.0 if not active."""
        for e in self.active_edicts:
            if e.edict == edict:
                return e.magnitude
        return 0.0
