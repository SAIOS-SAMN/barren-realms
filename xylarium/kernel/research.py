"""
Cognitive Metabolism, Breakthrough Tech Tree, and Procedural Cosmic Anomalies.
Implements the Netstratum two-tier cognitive economy (Rations vs. Leisure)
and the Observation Law (procedurally minting frontier clusters on demand).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import random

from xylarium.kernel import matter
from xylarium.kernel.models import (
    Captain,
    Sector,
    Planet,
    Port,
    SecurityLevel,
    PortClass,
    ActionResult,
    ActionType,
)
from xylarium.kernel.elements import PeriodicTable


# There is no tech tree: capabilities are processes learned with knowledge (knowledge.py, config PROCESSES).
from xylarium.config import LEGACY_TECH_PROCESS, PROCESSES, RESEARCH_POINTS_PER_UNIT  # noqa: E402


@dataclass
class CosmicAnomaly:
    id: str
    sector_id: int
    name: str
    anomaly_type: str              # "PRECURSOR_BEACON", "COLLAPSED_DYSON_RELIC", "TESSERACT_RIFT"
    difficulty: int = 1            # 1 to 5
    puzzle_type: str = "HARMONIC_ALIGNMENT" # "HARMONIC_ALIGNMENT", "RCF_CONJUGACY_MATRIX", "THERMAL_EQUILIBRIUM"
    status: str = "UNDISCOVERED"   # "UNDISCOVERED", "INVESTIGATING", "SOLVED"
    solved_by: Optional[str] = None
    reward_tech: Optional[str] = None
    reward_research: int = 100
    reward_credits: int = 5000
    reward_elements: Dict[str, int] = field(default_factory=dict)
    description: str = ""
    puzzle_target: int = 42

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sector_id": self.sector_id,
            "name": self.name,
            "anomaly_type": self.anomaly_type,
            "difficulty": self.difficulty,
            "puzzle_type": self.puzzle_type,
            "status": self.status,
            "solved_by": self.solved_by,
            "reward_tech": self.reward_tech,
            "reward_research": self.reward_research,
            "reward_credits": self.reward_credits,
            "reward_elements": dict(self.reward_elements),
            "description": self.description,
            "puzzle_target": self.puzzle_target,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CosmicAnomaly":
        return cls(
            id=data["id"],
            sector_id=data["sector_id"],
            name=data["name"],
            anomaly_type=data.get("anomaly_type", "PRECURSOR_BEACON"),
            difficulty=data.get("difficulty", 1),
            puzzle_type=data.get("puzzle_type", "HARMONIC_ALIGNMENT"),
            status=data.get("status", "UNDISCOVERED"),
            solved_by=data.get("solved_by"),
            reward_tech=data.get("reward_tech"),
            reward_research=data.get("reward_research", 100),
            reward_credits=data.get("reward_credits", 5000),
            reward_elements=dict(data.get("reward_elements", {})),
            description=data.get("description", ""),
            puzzle_target=data.get("puzzle_target", 42),
        )


class ResearchManager:
    """
    Oversees the Two-Tier Cognitive Economy, breakthrough technology minting,
    cosmic anomaly investigations, and lazy procedural frontier cluster expansion.
    """

    def __init__(self):
        self.anomalies: Dict[str, CosmicAnomaly] = {}
        self.next_anomaly_id: int = 101
        self.minted_clusters: List[int] = [1]  # 1 = Sol Federation Core

    def seed_initial_anomalies(self, kernel: Any) -> None:
        """Seed initial cosmic anomalies in deep-void anarchy sectors (61-100)."""
        anom_specs = [
            ("ANOM-101", 68, "Precursor Resonance Monolith", "PRECURSOR_BEACON", "HARMONIC_ALIGNMENT", "CLOAKING_GRID", 35),
            ("ANOM-102", 77, "Collapsed Dyson Swarm Relic", "COLLAPSED_DYSON_RELIC", "THERMAL_EQUILIBRIUM", "NANITE_DRYDOCK", 50),
            ("ANOM-103", 89, "Tesseract Slipstream Rift", "TESSERACT_RIFT", "RCF_CONJUGACY_MATRIX", "JUMP_DRIVE", 42),
            ("ANOM-104", 95, "Crystalline Progenitor Matrix", "PRECURSOR_BEACON", "HARMONIC_ALIGNMENT", "BIO_SYNTHESIZER", 60),
            ("ANOM-105", 99, "Apex Gravitational Archive", "COLLAPSED_DYSON_RELIC", "RCF_CONJUGACY_MATRIX", "ORBITAL_FOUNDRY", 75),
        ]
        for aid, sec_id, name, a_type, p_type, r_tech, target in anom_specs:
            if sec_id in kernel.sectors and aid not in self.anomalies:
                anom = CosmicAnomaly(
                    id=aid,
                    sector_id=sec_id,
                    name=name,
                    anomaly_type=a_type,
                    difficulty=3,
                    puzzle_type=p_type,
                    status="UNDISCOVERED",
                    reward_tech=r_tech,
                    reward_research=100,
                    reward_credits=7500,
                    reward_elements={"cryogenite": 15, "stelalith": 15, "umbrite": 10},
                    description=f"Ancient alien relic exhibiting high-dimensional {p_type.replace('_', ' ').lower()} signature.",
                    puzzle_target=target,
                )
                self.anomalies[aid] = anom
                sec = kernel.sectors[sec_id]
                if not hasattr(sec, "anomalies"):
                    sec.anomalies = []
                sec.anomalies.append(aid)

    def select_research(self, captain: Captain, tech_key: str, kernel: Any = None) -> Tuple[bool, str]:
        """Direct the inquiry of a captain's people: a domain (ENERGY, MATERIALS, BIOLOGY, INFORMATION), or the
        domain of a named capability. Nothing is unlocked - knowledge in the domain grows faster."""
        from xylarium.kernel import knowledge, ledger
        key = (tech_key or "").strip()
        domain = key.lower() if key.lower() in knowledge.DOMAINS else None
        if domain is None:
            proc = LEGACY_TECH_PROCESS.get(key.upper(), key.lower())
            domain = PROCESSES.get(proc, {}).get("domain")
        if domain is None:
            return False, (f"Unknown inquiry '{tech_key}'. Direct your people's thinkers to a domain: "
                           f"{', '.join(d.upper() for d in knowledge.DOMAINS)}.")
        kernel = kernel or ledger.active_kernel()
        knowledge.focus(kernel, knowledge.holder_of_captain(captain), domain)
        captain.active_research = domain
        return True, (f"INQUIRY DIRECTED: your colonies' thinkers turn to {domain.upper()}. Capabilities in that "
                      f"domain grow cheaper and stronger as knowledge accumulates.")

    def tick_cognitive_metabolism(self, kernel: Any) -> List[str]:
        """
        Advances Two-Tier Cognitive Economy:
        1. Colonies with surplus population and exotic/luxury element reserves enter Deep Cognition.
        2. Consumes 1 luxury element unit as a receipted draw to generate +15 Cognitive Momentum / Research Points.
        3. Advances active breakthrough research.
        4. Applies unlocked breakthrough passive effects (Nanite repairs, Bio-synthesizers, etc.).
        """
        logs = []
        if not kernel:
            return logs

        # 1. Planetary Deep Cognition & Research Minting
        for sec in kernel.sectors.values():
            for planet in sec.planets:
                if not planet.owner_id:
                    continue

                owner = kernel.captains.get(planet.owner_id)
                if not owner:
                    continue

                reserves = getattr(planet, "element_reserves", {})
                # Check for luxury/exotic element surplus (cryogenite, stelalith, chitinium, umbrite, pyrosite, aetherium)
                luxury_candidates = [
                    k for k, v in reserves.items()
                    if v > 0 and k in ["cryogenite", "stelalith", "chitinium", "umbrite", "pyrosite", "aetherium", "ferrolattice"]
                ]

                if luxury_candidates and planet.population >= 400 and planet.morale >= 50:
                    # Draw 1 unit of leisure element
                    chosen_elem = random.choice(luxury_candidates)
                    reserves[chosen_elem] -= 1
                    matter.sink("deep_cognition", chosen_elem, 1)     # a luxury used up in study
                    # study turns a luxury into knowledge for the owner's people, in their chosen domain
                    from xylarium.kernel import knowledge
                    holder = knowledge.holder_of_captain(owner)
                    domain = knowledge.stats(kernel)["focus"].get(holder, "information")
                    knowledge.learn(kernel, holder, domain, 15 / RESEARCH_POINTS_PER_UNIT, "deep_cognition")

                # Bio-synthesis: ore transposed into organics, as fast as the owner's people have learned it
                from xylarium.kernel import knowledge
                units = int(5 * knowledge.captain_mastery(kernel, owner, "bio_synthesis"))
                if units > 0 and planet.ore_silo >= units and planet.organics_silo <= 5000 - units:
                    matter.consume(planet, "ore_silo", "ORE", units, "bio_synthesis")
                    matter.produce(planet, "organics_silo", "ORGANICS", units, "bio_synthesis")

        # 2. Captain passive tech benefits
        from xylarium.kernel import knowledge
        for cap in kernel.captains.values():
            # Nanite repair: swarms as capable as the captain's people's materials science
            m = knowledge.captain_mastery(kernel, cap, "nanite_repair")
            if m <= 0:
                continue
            if cap.ship.shields < cap.ship.max_shields:
                cap.ship.shields = min(cap.ship.max_shields, cap.ship.shields + int(15 * m))
            if random.Random(f"nanite:{cap.id}:{kernel.cycle_count}").random() < m:
                cap.ship.fighters = min(100, cap.ship.fighters + 1)

        return logs

    def investigate_anomaly(
        self,
        captain: Captain,
        sector: Sector,
        anomaly_id: str,
        kernel: Any,
        solve_inputs: Optional[Dict[str, Any]] = None,
    ) -> ActionResult:
        """
        Investigates and attempts to decode/solve a Cosmic Anomaly.
        Can be solved via harmonic tuning parameters, RCF similarity reduction,
        or committing exotic element catalyst / research points.
        """
        if anomaly_id not in self.anomalies:
            return ActionResult(
                success=False,
                action=ActionType.ANOMALY_INVESTIGATE,
                message=f"Anomaly '{anomaly_id}' not found in galactic sensor log.",
            )

        anom = self.anomalies[anomaly_id]
        if anom.sector_id != sector.id:
            return ActionResult(
                success=False,
                action=ActionType.ANOMALY_INVESTIGATE,
                message=f"Anomaly '{anom.name}' is located in Sector {anom.sector_id:03d}. You are in Sector {sector.id:03d}.",
            )

        if anom.status == "SOLVED":
            return ActionResult(
                success=False,
                action=ActionType.ANOMALY_INVESTIGATE,
                message=f"Anomaly '{anom.name}' has already been decoded and solved by {anom.solved_by or 'another captain'}.",
            )

        solve_inputs = solve_inputs or {}
        # Puzzle resolution logic
        solved = False
        solve_mode = solve_inputs.get("mode", "catalyst")

        if solve_mode == "solve":
            val = int(solve_inputs.get("value", 0))
            if val == anom.puzzle_target:
                solved = True
            else:
                return ActionResult(
                    success=False,
                    action=ActionType.ANOMALY_INVESTIGATE,
                    message=f"Harmonic calibration failed! Resonance frequency {val} did not match the Progenitor matrix ({anom.puzzle_target}).",
                )
        else:
            # Catalyst mode: Commit 500 Cr and 5 exotic element units, or use research points
            cost_cr = 1000
            if captain.credits < cost_cr:
                return ActionResult(
                    success=False,
                    action=ActionType.ANOMALY_INVESTIGATE,
                    message=f"Decoding {anom.name} requires {cost_cr:,} Cr in computational sensor scans. You have {captain.credits:,} Cr.",
                )
            captain.credits -= cost_cr
            from xylarium.kernel import ledger as _ledger
            _ledger.pay_service(cost_cr, captain.sector_id)   # the survey crews and instruments
            solved = True

        if solved:
            anom.status = "SOLVED"
            anom.solved_by = captain.name
            captain.credits += anom.reward_credits
            from xylarium.kernel import ledger
            ledger.mint("discovery_reward", anom.reward_credits)
            from xylarium.kernel.experience import ExperienceManager
            from xylarium.config import XP_SCIENCE_ANOMALY
            ExperienceManager.award(captain, "science", XP_SCIENCE_ANOMALY, kernel, key=f"anomaly:{anom.id}")
            captain.score += 750

            # What the anomaly teaches: knowledge in the domain its precursors worked in
            unlocked_tech_msg = ""
            if kernel is not None:
                from xylarium.kernel import fertility, knowledge
                domain = knowledge.discovery_domain(anom.reward_tech)
                units = (anom.reward_research + 100) / RESEARCH_POINTS_PER_UNIT
                knowledge.learn(kernel, knowledge.holder_of_captain(captain), domain, units, "anomaly")
                fertility.discovered(kernel, captain=captain)
                unlocked_tech_msg = f" Its precursors' {domain} - {units:.0f} units of knowledge - is yours."

            # Deposit exotic elements into cargo hold if space permits
            for elem_name, qty in anom.reward_elements.items():
                matter.source("anomaly_reward", elem_name, captain.ship.cargo.stow(elem_name, qty))

            msg = (
                f"ANOMALY DECODED: Successfully unlocked '{anom.name}' ({anom.id})! "
                f"Awarded +{anom.reward_credits:,} Credits and +{anom.reward_research} Research Points.{unlocked_tech_msg}"
            )
            if kernel and kernel.event_bus:
                kernel.event_bus.broadcast_radio(
                    sender="SCIENCE-DIRECTORATE",
                    text=f"GALACTIC DISCOVERY: Captain {captain.name} has solved ancient cosmic anomaly '{anom.name}' in Sector {sector.id:03d}!",
                    channel="SYSTEM",
                    sector_id=sector.id,
                )

            return ActionResult(
                success=True,
                action=ActionType.ANOMALY_INVESTIGATE,
                message=msg,
                turns_spent=1,
                logs=[msg],
                data={"anomaly": anom.to_dict(), "reward_credits": anom.reward_credits, "reward_tech": anom.reward_tech},
            )

        return ActionResult(
            success=False,
            action=ActionType.ANOMALY_INVESTIGATE,
            message="Investigation completed without resolution.",
        )

    @matter.declared("cluster_genesis")
    def mint_frontier_cluster(self, kernel: Any, cluster_index: int) -> Tuple[bool, str, List[int]]:
        """
        The Observation Law (Netstratum 13_GALAXY):
        Procedurally mints and links a new star cluster on demand when an explorer crosses the frontier.
        Cluster 2: 'The Perseus Veil' (Sectors 201-240)
        Cluster 3: 'The Cygnus Spiral' (Sectors 241-280)
        (Sectors 101-199 are reserved for secret/ghost sectors unlocked by cartography.)
        """
        if cluster_index in self.minted_clusters:
            return False, f"Cluster {cluster_index} is already chartered in the galactic star-chart.", []

        rng = random.Random(kernel.seed + cluster_index * 1337)
        if cluster_index == 2:
            cluster_name = "The Perseus Veil"
            start_id = 201
            end_id = 240
            anchor_sectors = list(range(91, 101)) # Bridge from Deep Void 91-100
        elif cluster_index == 3:
            cluster_name = "The Cygnus Spiral"
            start_id = 241
            end_id = 280
            anchor_sectors = list(range(231, 241))
        else:
            cluster_name = f"Outer Expanse {cluster_index}"
            start_id = 201 + (cluster_index - 2) * 40
            end_id = start_id + 39
            anchor_sectors = list(range(start_id - 10, start_id))

        new_sector_ids = list(range(start_id, end_id + 1))
        adjectives = ["Veiled", "Obsidian", "Cosmic", "Tesseract", "Supernova", "Prismatic", "Hyperion", "Eclipse"]
        nouns = ["Rift", "Spire", "Shoals", "Chasm", "Nexus", "Matrix", "Sanctum", "Abyss"]

        # Create new sectors
        for s_id in new_sector_ids:
            name = f"{rng.choice(adjectives)} {rng.choice(nouns)} #{s_id}"
            sec = Sector(
                id=s_id,
                name=name,
                security=SecurityLevel.ANARCHY,
                warps=[],
                port=None,
                planets=[],
                captains=[],
            )
            sec.cluster_name = cluster_name
            kernel.sectors[s_id] = sec

        # Connect new sectors internally using spanning tree + random loops
        for i in range(len(new_sector_ids) - 1):
            s_a = new_sector_ids[i]
            s_b = new_sector_ids[i + 1]
            kernel.sectors[s_a].warps.append(s_b)
            kernel.sectors[s_b].warps.append(s_a)

        # Cross-stitch extra warps
        for s_id in new_sector_ids:
            candidates = [x for x in new_sector_ids if x != s_id and x not in kernel.sectors[s_id].warps]
            if candidates:
                cand = rng.choice(candidates)
                if len(kernel.sectors[s_id].warps) < 4:
                    kernel.sectors[s_id].warps.append(cand)
                    kernel.sectors[cand].warps.append(s_id)

        # Bridge anchor sectors from previous cluster
        for anchor in anchor_sectors[:4]:
            if anchor in kernel.sectors:
                entry_sec = rng.choice(new_sector_ids[:5])
                kernel.sectors[anchor].warps.append(entry_sec)
                kernel.sectors[entry_sec].warps.append(anchor)

        # Sort warps
        for s_id in new_sector_ids:
            kernel.sectors[s_id].warps = sorted(list(set(kernel.sectors[s_id].warps)))
        from xylarium.kernel import topology
        topology.changed(kernel)

        # Lay out star systems and null space exactly like the core galaxy
        from xylarium.kernel.universe import furnish_sectors
        from xylarium.kernel import ledger
        furnish_sectors(kernel.sectors, new_sector_ids, rng, kernel.seed, found_polities=False, force_system=None)
        for s_id in new_sector_ids:
            port = kernel.sectors[s_id].port
            if port is not None:
                # Newly charted outposts are lightly capitalized; their working capital is declared new money
                from xylarium.config import FRONTIER_PORT_CAPITAL_FACTOR
                port.treasury = int(port.treasury * FRONTIER_PORT_CAPITAL_FACTOR)
                ledger.mint("cluster_genesis", port.treasury, port.currency)

        # The frontier's richest worlds: uninhabited planets with exotic veins
        exotic = [p for s_id in new_sector_ids for p in kernel.sectors[s_id].planets]
        rng.shuffle(exotic)
        for p in exotic[:4]:
            p.element_deposits.update({
                "cryogenite": rng.randint(250, 600),
                "stelalith": rng.randint(200, 500),
                "umbrite": rng.randint(150, 400),
                "aetherium": rng.randint(100, 300),
            })

        # Seed 2 Cosmic Anomalies in the new cluster
        anom_a_id = f"ANOM-{self.next_anomaly_id}"
        self.next_anomaly_id += 1
        anom_sec_a = rng.choice(new_sector_ids)
        anom_a = CosmicAnomaly(
            id=anom_a_id,
            sector_id=anom_sec_a,
            name=f"Tesseract Core of {cluster_name}",
            anomaly_type="TESSERACT_RIFT",
            difficulty=4,
            puzzle_type="RCF_CONJUGACY_MATRIX",
            status="UNDISCOVERED",
            reward_tech="JUMP_DRIVE",
            reward_research=150,
            reward_credits=10000,
            reward_elements={"cryogenite": 30, "aetherium": 20},
            description="Deep spatial fold connecting to the ancient precursor lattice.",
            puzzle_target=88,
        )
        self.anomalies[anom_a_id] = anom_a
        kernel.sectors[anom_sec_a].anomalies.append(anom_a_id)

        self.minted_clusters.append(cluster_index)
        # The frontier is peopled: its most advanced natives already sail its lanes
        from xylarium.kernel import populace
        for log in populace.seed_cluster(kernel, new_sector_ids):
            if hasattr(kernel, "action_logs"):
                kernel.action_logs.append(log)
        msg = f"OBSERVATION LAW ENCLOSED: Explorer has crossed the charted frontier! Minted new star cluster '{cluster_name}' (Sectors {start_id:03d}-{end_id:03d}) with {len(new_sector_ids)} sectors."
        if kernel.event_bus:
            kernel.event_bus.broadcast_radio(
                sender="PROGENITOR-NAV",
                text=f"ASTRONAVIGATION UPDATE: Frontier cluster '{cluster_name}' (Sectors {start_id}-{end_id}) has entered the universal star-chart.",
                channel="SYSTEM",
                sector_id=1,
            )
        return True, msg, new_sector_ids

    def jump_warp(self, captain: Captain, destination: int, kernel: Any) -> ActionResult:
        """
        Executes hyper-dimensional Jump Drive transit across distant sectors.
        Bypasses standard adjacency, allowing instant warp to any charted sector
        or expanding into uncharted clusters!
        """
        # Folding space costs what the captain's people's energy science has not yet learned away
        from xylarium.kernel import knowledge
        m = knowledge.captain_mastery(kernel, captain, "jump_drive")
        if m <= 0:
            return ActionResult(
                success=False,
                action=ActionType.JUMP_WARP,
                message="Your people know nothing yet of folding space: build energy knowledge (RESEARCH ENERGY).",
            )

        if destination <= 0:
            return ActionResult(
                success=False,
                action=ActionType.JUMP_WARP,
                message="Invalid destination sector coordinate.",
            )

        # Check if destination requires minting the next frontier cluster
        if destination > 200 and destination not in kernel.sectors:
            if destination <= 240 and 2 not in self.minted_clusters:
                self.mint_frontier_cluster(kernel, 2)
            elif destination <= 280 and 3 not in self.minted_clusters:
                if 2 not in self.minted_clusters:
                    self.mint_frontier_cluster(kernel, 2)
                self.mint_frontier_cluster(kernel, 3)

        if destination not in kernel.sectors:
            return ActionResult(
                success=False,
                action=ActionType.JUMP_WARP,
                message=f"Sector {destination} lies beyond current charted space.",
            )

        cost_cr = jump_cost(kernel, captain)
        if captain.credits < cost_cr:
            return ActionResult(
                success=False,
                action=ActionType.JUMP_WARP,
                message=f"Jump drive transit capacitors require {cost_cr} Credits. You have {captain.credits} Cr.",
            )

        old_sec = captain.sector_id
        captain.credits -= cost_cr
        from xylarium.kernel import ledger as _ledger
        _ledger.pay_service(cost_cr, institution="jump_gates")   # the gate authority
        if captain.id in kernel.sectors[old_sec].captains:
            kernel.sectors[old_sec].captains.remove(captain.id)

        captain.sector_id = destination
        if captain.id not in kernel.sectors[destination].captains:
            kernel.sectors[destination].captains.append(captain.id)

        msg = f"HYPER-DIMENSIONAL JUMP ENGAGED: Folded spacetime from Sector {old_sec:03d} to Sector {destination:03d} ({kernel.sectors[destination].name})!"
        return ActionResult(
            success=True,
            action=ActionType.JUMP_WARP,
            message=msg,
            turns_spent=1,
            logs=[msg],
            data={"from_sector": old_sec, "to_sector": destination},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomalies": {aid: a.to_dict() for aid, a in self.anomalies.items()},
            "next_anomaly_id": self.next_anomaly_id,
            "minted_clusters": list(self.minted_clusters),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchManager":
        mgr = cls()
        mgr.anomalies = {
            aid: CosmicAnomaly.from_dict(a_data)
            for aid, a_data in data.get("anomalies", {}).items()
        }
        mgr.next_anomaly_id = data.get("next_anomaly_id", 101)
        mgr.minted_clusters = list(data.get("minted_clusters", [1]))
        return mgr


def jump_cost(kernel: Any, captain: Any) -> int:
    """Capacitor charge for a fold: 250 Cr at full mastery of the drive, more as mastery falls (1 / mastery)."""
    from xylarium.kernel import knowledge
    m = knowledge.captain_mastery(kernel, captain, "jump_drive")
    return int(250 / m) if m > 0 else 10 ** 9
