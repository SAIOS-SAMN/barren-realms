"""
Cartography Lab & Starmap Puzzle Engine for Xylarium.
Manages chart fragment collection, interactive cartographic matrix decryption,
and permanent unlocking of Ghost Sectors and Smuggler Shortcuts.
"""

import random
from typing import Dict, List, Optional, Any, Tuple
from xylarium.kernel.models import (
    ActionType,
    ActionResult,
    Captain,
    Sector,
    Port,
    Planet,
    PortClass,
    SecurityLevel,
    AIPersonality,
    TollGate,
    SurveyProbe,
)
from xylarium.config import (
    COMMODITY_CONFIG,
    TOLL_GATE_DEPLOY_COST_CREDITS,
    TOLL_GATE_DEFAULT_FEE,
    SURVEY_PROBE_COST_CREDITS,
    FORGED_CHIT_SYNTH_COST,
    FORGED_CHIT_BROKER_VALUE,
)


# Canonical Starmap Fragments
FRAGMENT_TEMPLATES = [
    {
        "id": "FRAG-ALPHA-78",
        "name": "Corrupted Starmap Fragment Alpha [Grid 078]",
        "target_puzzle": "PUZZLE-NEXUS",
        "fragment_type": "CORRUPTED_SLATE",
        "rarity": "RARE",
        "description": "Scorched navigational crystal containing partial vector telemetry for Sector 078.",
    },
    {
        "id": "FRAG-BETA-78",
        "name": "Smuggler Frequency Chit Beta [Nexus Relay]",
        "target_puzzle": "PUZZLE-NEXUS",
        "fragment_type": "DATA_CHIT",
        "rarity": "UNCOMMON",
        "description": "Encrypted smuggler telemetry with hyper-lane harmonic coordinates.",
    },
    {
        "id": "FRAG-GAMMA-09",
        "name": "Precursor Glyph Tablet Gamma [Zeta-9]",
        "target_puzzle": "PUZZLE-VAULT",
        "fragment_type": "GLYPH_TABLET",
        "rarity": "LEGENDARY",
        "description": "Resonant metallic slate inscribed with quantum coordinate glyphs from a forgotten era.",
    },
    {
        "id": "FRAG-DELTA-09",
        "name": "Archaic Vault Telemetry Slate Delta",
        "target_puzzle": "PUZZLE-VAULT",
        "fragment_type": "GLYPH_TABLET",
        "rarity": "RARE",
        "description": "Ancient structural schematic indicating an untouched Precursor vault redoubt.",
    },
    {
        "id": "FRAG-EPSILON-10",
        "name": "Void Relay Black Box Epsilon [Bypass Corridor]",
        "target_puzzle": "PUZZLE-SHORTCUT",
        "fragment_type": "TELEMETRY_LOG",
        "rarity": "RARE",
        "description": "Recovered smuggler black box mapping a stable Einstein-Rosen bridge bypassing Anarchy.",
    },
    {
        "id": "FRAG-UNIVERSAL",
        "name": "Uncalibrated Astrogation Slate [Wildcard]",
        "target_puzzle": "UNIVERSAL",
        "fragment_type": "DATA_CHIT",
        "rarity": "COMMON",
        "description": "Decrypted stellar chart fragment compatible with any cartographic decryption matrix.",
    },
]



MAX_HELD_FRAGMENTS = 40   # A chart locker holds this many fragments; the oldest are traded away or lost


def stow_fragment(captain: Any, fragment: Dict[str, Any]) -> None:
    """Adds a starmap fragment to a captain's locker, bounded so lockers don't grow without limit."""
    held = captain.cartography_fragments
    held.append(fragment)
    if len(held) > MAX_HELD_FRAGMENTS:
        del held[: len(held) - MAX_HELD_FRAGMENTS]


class CartographyPuzzle:
    """Represents an interactive 3x3 cartographic decryption matrix."""

    def __init__(
        self,
        puzzle_id: str,
        name: str,
        target_unlock: str,
        target_title: str,
        target_sector_hint: str,
        fragments_required: int = 5,
        energy_max: int = 3,
    ):
        self.puzzle_id = puzzle_id
        self.name = name
        self.target_unlock = target_unlock
        self.target_title = target_title
        self.target_sector_hint = target_sector_hint
        self.fragments_required = fragments_required
        self.fragments_applied = 0
        self.energy_max = energy_max
        self.energy_left = energy_max
        self.status = "UNSOLVED"  # "UNSOLVED", "DECRYPTED"
        self.core_vector = "[001]"
        self.target_frequency = 1420
        self.required_reagents: Dict[str, int] = {}
        self.applied_reagents: Dict[str, int] = {}
        self.is_catalyzed: bool = True

        # 3x3 Grid of nodes: (row, col)
        # Each node has: label, sector_val, is_anchor, is_revealed, vector_angle (0, 90, 180, 270), target_angle
        self.grid_nodes: List[List[Dict[str, Any]]] = []
        self.grid_bridges: Dict[str, bool] = {}
        self._initialize_grid()

    def _initialize_grid(self) -> None:
        if self.puzzle_id == "PUZZLE-NEXUS":
            # Grid matches the iconic design mockup:
            # [ A ] ─── ( ? ) ────── ( 042 )
            #   │        │             │
            #  ( ?) ──── ( 065 ) ───── ( ? )
            #   │        │             │
            # [ 014 ] ── ( ? ) ───── [ 088 ]
            self.grid_nodes = [
                [
                    {"row": 0, "col": 0, "label": "[ A ]", "sector_val": 1, "is_anchor": True, "is_revealed": True, "vector_angle": 0, "target_angle": 0},
                    {"row": 0, "col": 1, "label": "( ? )", "sector_val": 78, "is_anchor": False, "is_revealed": False, "vector_angle": 90, "target_angle": 0},
                    {"row": 0, "col": 2, "label": "( 042 )", "sector_val": 42, "is_anchor": False, "is_revealed": True, "vector_angle": 0, "target_angle": 0},
                ],
                [
                    {"row": 1, "col": 0, "label": "( ? )", "sector_val": 33, "is_anchor": False, "is_revealed": False, "vector_angle": 180, "target_angle": 0},
                    {"row": 1, "col": 1, "label": "( 065 )", "sector_val": 65, "is_anchor": False, "is_revealed": True, "vector_angle": 0, "target_angle": 0},
                    {"row": 1, "col": 2, "label": "( ? )", "sector_val": 54, "is_anchor": False, "is_revealed": False, "vector_angle": 270, "target_angle": 0},
                ],
                [
                    {"row": 2, "col": 0, "label": "[ 014 ]", "sector_val": 14, "is_anchor": True, "is_revealed": True, "vector_angle": 0, "target_angle": 0},
                    {"row": 2, "col": 1, "label": "( ? )", "sector_val": 71, "is_anchor": False, "is_revealed": False, "vector_angle": 90, "target_angle": 0},
                    {"row": 2, "col": 2, "label": "[ 088 ]", "sector_val": 88, "is_anchor": True, "is_revealed": True, "vector_angle": 0, "target_angle": 0},
                ],
            ]
            # Horizontal and vertical bridges
            self.grid_bridges = {
                "0,0-0,1": True,
                "0,1-0,2": True,
                "1,0-1,1": True,
                "1,1-1,2": True,
                "2,0-2,1": True,
                "2,1-2,2": True,
                "0,0-1,0": True,
                "1,0-2,0": True,
                "0,1-1,1": True,
                "1,1-2,1": True,
                "0,2-1,2": True,
                "1,2-2,2": True,
            }
        elif self.puzzle_id == "PUZZLE-VAULT":
            self.grid_nodes = [
                [
                    {"row": 0, "col": 0, "label": "[ Z ]", "sector_val": 9, "is_anchor": True, "is_revealed": True, "vector_angle": 0, "target_angle": 0},
                    {"row": 0, "col": 1, "label": "( ? )", "sector_val": 88, "is_anchor": False, "is_revealed": False, "vector_angle": 180, "target_angle": 0},
                    {"row": 0, "col": 2, "label": "( 050 )", "sector_val": 50, "is_anchor": False, "is_revealed": True, "vector_angle": 90, "target_angle": 0},
                ],
                [
                    {"row": 1, "col": 0, "label": "( ? )", "sector_val": 92, "is_anchor": False, "is_revealed": False, "vector_angle": 270, "target_angle": 0},
                    {"row": 1, "col": 1, "label": "( 106 )", "sector_val": 106, "is_anchor": False, "is_revealed": False, "vector_angle": 90, "target_angle": 0},
                    {"row": 1, "col": 2, "label": "( ? )", "sector_val": 63, "is_anchor": False, "is_revealed": False, "vector_angle": 180, "target_angle": 0},
                ],
                [
                    {"row": 2, "col": 0, "label": "[ 022 ]", "sector_val": 22, "is_anchor": True, "is_revealed": True, "vector_angle": 0, "target_angle": 0},
                    {"row": 2, "col": 1, "label": "( ? )", "sector_val": 75, "is_anchor": False, "is_revealed": False, "vector_angle": 90, "target_angle": 0},
                    {"row": 2, "col": 2, "label": "[ 099 ]", "sector_val": 99, "is_anchor": True, "is_revealed": True, "vector_angle": 0, "target_angle": 0},
                ],
            ]
            self.grid_bridges = {
                "0,0-0,1": True,
                "0,1-0,2": False,  # Broken link to bridge
                "1,0-1,1": True,
                "1,1-1,2": True,
                "2,0-2,1": True,
                "2,1-2,2": True,
                "0,0-1,0": True,
                "1,0-2,0": True,
                "0,1-1,1": True,
                "1,1-2,1": True,
                "0,2-1,2": True,
                "1,2-2,2": True,
            }
        else:  # PUZZLE-SHORTCUT
            self.grid_nodes = [
                [
                    {"row": 0, "col": 0, "label": "[ 010 ]", "sector_val": 10, "is_anchor": True, "is_revealed": True, "vector_angle": 0, "target_angle": 0},
                    {"row": 0, "col": 1, "label": "( ? )", "sector_val": 25, "is_anchor": False, "is_revealed": False, "vector_angle": 90, "target_angle": 0},
                    {"row": 0, "col": 2, "label": "( 035 )", "sector_val": 35, "is_anchor": False, "is_revealed": True, "vector_angle": 180, "target_angle": 0},
                ],
                [
                    {"row": 1, "col": 0, "label": "( ? )", "sector_val": 45, "is_anchor": False, "is_revealed": False, "vector_angle": 90, "target_angle": 0},
                    {"row": 1, "col": 1, "label": "( 055 )", "sector_val": 55, "is_anchor": False, "is_revealed": True, "vector_angle": 270, "target_angle": 0},
                    {"row": 1, "col": 2, "label": "( ? )", "sector_val": 65, "is_anchor": False, "is_revealed": False, "vector_angle": 90, "target_angle": 0},
                ],
                [
                    {"row": 2, "col": 0, "label": "[ 030 ]", "sector_val": 30, "is_anchor": True, "is_revealed": True, "vector_angle": 0, "target_angle": 0},
                    {"row": 2, "col": 1, "label": "( ? )", "sector_val": 68, "is_anchor": False, "is_revealed": False, "vector_angle": 180, "target_angle": 0},
                    {"row": 2, "col": 2, "label": "[ 070 ]", "sector_val": 70, "is_anchor": True, "is_revealed": True, "vector_angle": 0, "target_angle": 0},
                ],
            ]
            self.grid_bridges = {
                "0,0-0,1": True,
                "0,1-0,2": True,
                "1,0-1,1": False,  # Broken link
                "1,1-1,2": True,
                "2,0-2,1": True,
                "2,1-2,2": True,
                "0,0-1,0": True,
                "1,0-2,0": True,
                "0,1-1,1": True,
                "1,1-2,1": True,
                "0,2-1,2": True,
                "1,2-2,2": True,
            }

    def get_progress_pct(self) -> int:
        """Calculates current decryption percentage (0% to 100%)."""
        if self.status == "DECRYPTED":
            return 100

        total_nodes = 9
        revealed_nodes = sum(1 for row in self.grid_nodes for n in row if n["is_revealed"])
        aligned_nodes = sum(1 for row in self.grid_nodes for n in row if n["vector_angle"] == n["target_angle"])
        total_bridges = len(self.grid_bridges)
        active_bridges = sum(1 for b in self.grid_bridges.values() if b)

        if self.required_reagents:
            node_score = (revealed_nodes / total_nodes) * 30.0
            align_score = (aligned_nodes / total_nodes) * 30.0
            bridge_score = (active_bridges / total_bridges) * 20.0
            reagent_score = 20.0 if self.is_catalyzed else sum(
                min(1.0, self.applied_reagents.get(r, 0) / max(1, req)) * (20.0 / len(self.required_reagents))
                for r, req in self.required_reagents.items()
            )
            pct = int(round(node_score + align_score + bridge_score + reagent_score))
        else:
            node_score = (revealed_nodes / total_nodes) * 40.0
            align_score = (aligned_nodes / total_nodes) * 40.0
            bridge_score = (active_bridges / total_bridges) * 20.0
            pct = int(round(node_score + align_score + bridge_score))

        return min(99, pct)

    def is_decryption_complete(self) -> bool:
        """Returns True if all nodes revealed, vectors aligned, bridges active, and reagents catalyzed."""
        all_revealed = all(n["is_revealed"] for row in self.grid_nodes for n in row)
        all_aligned = all(n["vector_angle"] == n["target_angle"] for row in self.grid_nodes for n in row)
        all_bridged = all(self.grid_bridges.values())
        reagents_met = self.is_catalyzed if self.required_reagents else True
        return all_revealed and all_aligned and all_bridged and reagents_met

    def to_dict(self) -> Dict[str, Any]:
        return {
            "puzzle_id": self.puzzle_id,
            "name": self.name,
            "target_unlock": self.target_unlock,
            "target_title": self.target_title,
            "target_sector_hint": self.target_sector_hint,
            "fragments_required": self.fragments_required,
            "fragments_applied": self.fragments_applied,
            "energy_max": self.energy_max,
            "energy_left": self.energy_left,
            "status": self.status,
            "core_vector": self.core_vector,
            "target_frequency": self.target_frequency,
            "progress_pct": self.get_progress_pct(),
            "grid_nodes": [[dict(n) for n in row] for row in self.grid_nodes],
            "grid_bridges": dict(self.grid_bridges),
            "required_reagents": dict(self.required_reagents),
            "applied_reagents": dict(self.applied_reagents),
            "is_catalyzed": self.is_catalyzed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CartographyPuzzle":
        p = cls(
            puzzle_id=data["puzzle_id"],
            name=data["name"],
            target_unlock=data["target_unlock"],
            target_title=data["target_title"],
            target_sector_hint=data["target_sector_hint"],
            fragments_required=data.get("fragments_required", 5),
            energy_max=data.get("energy_max", 3),
        )
        p.fragments_applied = data.get("fragments_applied", 0)
        p.energy_left = data.get("energy_left", p.energy_max)
        p.status = data.get("status", "UNSOLVED")
        p.core_vector = data.get("core_vector", "[001]")
        p.target_frequency = data.get("target_frequency", 1420)
        if "grid_nodes" in data:
            p.grid_nodes = [[dict(n) for n in row] for row in data["grid_nodes"]]
        if "grid_bridges" in data:
            p.grid_bridges = dict(data["grid_bridges"])
        p.required_reagents = dict(data.get("required_reagents", {}))
        p.applied_reagents = dict(data.get("applied_reagents", {}))
        p.is_catalyzed = data.get("is_catalyzed", True if not p.required_reagents else False)
        return p


class CartographyManager:
    """Manages starmap puzzle state, fragment drops, decryption, toll gates, survey probes, and secret unlocks."""

    def __init__(self):
        self.puzzles: Dict[str, CartographyPuzzle] = {}
        self.active_puzzle_id: str = "PUZZLE-NEXUS"
        self.unlocked_secrets: List[str] = []
        self.toll_gates: Dict[str, TollGate] = {}
        self.survey_probes: Dict[str, SurveyProbe] = {}
        self.probe_counter: int = 100
        self.gate_counter: int = 100
        self._init_default_puzzles()

    def _init_default_puzzles(self) -> None:
        self.puzzles["PUZZLE-NEXUS"] = CartographyPuzzle(
            puzzle_id="PUZZLE-NEXUS",
            name="Sector 078 Anomaly Matrix",
            target_unlock="GHOST_NEXUS",
            target_title="Black-Market Nexus [Ghost Sector 105]",
            target_sector_hint="Sector 078 Anomaly / Sector 065",
            fragments_required=5,
            energy_max=3,
        )
        vault = CartographyPuzzle(
            puzzle_id="PUZZLE-VAULT",
            name="Precursor Cipher Zeta-9",
            target_unlock="PRECURSOR_VAULT",
            target_title="Precursor Salvage Vault [Ghost Sector 106]",
            target_sector_hint="Sector 088 Precursor Ruins / Sector 092",
            fragments_required=5,
            energy_max=3,
        )
        vault.required_reagents = {"SpR": 5, "U": 5}
        vault.applied_reagents = {"SpR": 0, "U": 0}
        vault.is_catalyzed = False
        self.puzzles["PUZZLE-VAULT"] = vault

        self.puzzles["PUZZLE-SHORTCUT"] = CartographyPuzzle(
            puzzle_id="PUZZLE-SHORTCUT",
            name="Void Relay Bypass Matrix",
            target_unlock="SMUGGLER_SHORTCUT",
            target_title="Smuggler Shortcut [Sector 010 <-> 070 Bypass]",
            target_sector_hint="Sector 010 (Border) <-> Sector 070 (Anarchy)",
            fragments_required=4,
            energy_max=3,
        )

    def scan_fragment(self, captain: Captain, puzzle_id: Optional[str] = None, kernel: Any = None) -> ActionResult:
        """Consumes a collected chart fragment to reveal an encrypted node in the matrix."""
        pid = puzzle_id or self.active_puzzle_id
        if pid not in self.puzzles:
            return ActionResult(success=False, action=ActionType.CARTOGRAPHY_SCAN, message=f"Unknown puzzle matrix '{pid}'.")

        puzzle = self.puzzles[pid]
        if puzzle.status == "DECRYPTED":
            return ActionResult(success=False, action=ActionType.CARTOGRAPHY_SCAN, message="Matrix is already fully decrypted.")

        # Check captain fragment inventory
        matching_frags = [
            f for f in captain.cartography_fragments
            if f.get("target_puzzle") in [pid, "UNIVERSAL"]
        ]
        if not matching_frags:
            # Check any fragment
            if captain.cartography_fragments:
                frag_to_use = captain.cartography_fragments[0]
            else:
                return ActionResult(
                    success=False,
                    action=ActionType.CARTOGRAPHY_SCAN,
                    message="No starmap fragments in inventory! Salvage pirate wrecks, search drifting hulks, or buy chits at ports.",
                )
        else:
            frag_to_use = matching_frags[0]

        # Find first unrevealed node
        unrevealed = [
            n for row in puzzle.grid_nodes for n in row
            if not n["is_revealed"]
        ]
        if not unrevealed:
            return ActionResult(
                success=False,
                action=ActionType.CARTOGRAPHY_SCAN,
                message="All nodes in this matrix have already been revealed! Rotate nodes and bridge vectors to align.",
            )

        target_node = unrevealed[0]
        target_node["is_revealed"] = True
        s_val = target_node.get("sector_val", 42)
        target_node["label"] = f"( {s_val:03d} )"
        puzzle.fragments_applied += 1
        captain.cartography_fragments.remove(frag_to_use)

        log_msg = f"[CARTOGRAPHY] Scanned {frag_to_use['name']}! Decrypted Node ({target_node['row']},{target_node['col']}) -> Sector {s_val:03d}."
        if kernel and hasattr(kernel, "action_logs"):
            kernel.action_logs.append(log_msg)

        # Check if this completed the decryption
        if puzzle.is_decryption_complete():
            return self.solve_puzzle(captain, pid, kernel)

        return ActionResult(
            success=True,
            action=ActionType.CARTOGRAPHY_SCAN,
            message=f"Fragment scanned successfully! Decrypted Node ({target_node['row']},{target_node['col']}) -> Sector {s_val:03d}. Progress: {puzzle.get_progress_pct()}%.",
            logs=[log_msg],
            data=puzzle.to_dict(),
        )

    def rotate_node(self, captain: Captain, row: int, col: int, puzzle_id: Optional[str] = None, kernel: Any = None) -> ActionResult:
        """Rotates a node vector by 90 degrees."""
        pid = puzzle_id or self.active_puzzle_id
        if pid not in self.puzzles:
            return ActionResult(success=False, action=ActionType.CARTOGRAPHY_ROTATE, message=f"Unknown puzzle matrix '{pid}'.")

        puzzle = self.puzzles[pid]
        if puzzle.status == "DECRYPTED":
            return ActionResult(success=False, action=ActionType.CARTOGRAPHY_ROTATE, message="Matrix is already fully decrypted.")

        if not (0 <= row <= 2 and 0 <= col <= 2):
            return ActionResult(success=False, action=ActionType.CARTOGRAPHY_ROTATE, message="Node coordinate out of bounds (0-2 required).")

        node = puzzle.grid_nodes[row][col]
        if puzzle.energy_left <= 0:
            if captain.turns_left > 0:
                captain.turns_left -= 1
                puzzle.energy_left = puzzle.energy_max
            else:
                return ActionResult(success=False, action=ActionType.CARTOGRAPHY_ROTATE, message="Matrix capacitor energy depleted. Turns needed to recharge.")

        puzzle.energy_left -= 1
        node["vector_angle"] = (node["vector_angle"] + 90) % 360
        is_aligned = (node["vector_angle"] == node["target_angle"])
        align_str = "ALIGNED with Core Vector [001]" if is_aligned else f"{node['vector_angle']}°"

        if puzzle.is_decryption_complete():
            return self.solve_puzzle(captain, pid, kernel)

        return ActionResult(
            success=True,
            action=ActionType.CARTOGRAPHY_ROTATE,
            message=f"Node ({row},{col}) rotated to {align_str}. Progress: {puzzle.get_progress_pct()}%. Energy: {puzzle.energy_left}/{puzzle.energy_max}.",
            data=puzzle.to_dict(),
        )

    def bridge_vector(self, captain: Captain, r1: int, c1: int, r2: int, c2: int, puzzle_id: Optional[str] = None, kernel: Any = None) -> ActionResult:
        """Bridges or links a vector gap between two adjacent nodes."""
        pid = puzzle_id or self.active_puzzle_id
        if pid not in self.puzzles:
            return ActionResult(success=False, action=ActionType.CARTOGRAPHY_BRIDGE, message=f"Unknown puzzle matrix '{pid}'.")

        puzzle = self.puzzles[pid]
        if puzzle.status == "DECRYPTED":
            return ActionResult(success=False, action=ActionType.CARTOGRAPHY_BRIDGE, message="Matrix is already fully decrypted.")

        k1 = f"{r1},{c1}-{r2},{c2}"
        k2 = f"{r2},{c2}-{r1},{c1}"
        bridge_key = k1 if k1 in puzzle.grid_bridges else (k2 if k2 in puzzle.grid_bridges else None)

        if not bridge_key:
            return ActionResult(success=False, action=ActionType.CARTOGRAPHY_BRIDGE, message=f"No valid vector connection between ({r1},{c1}) and ({r2},{c2}).")

        if puzzle.energy_left <= 0:
            if captain.turns_left > 0:
                captain.turns_left -= 1
                puzzle.energy_left = puzzle.energy_max
            else:
                return ActionResult(success=False, action=ActionType.CARTOGRAPHY_BRIDGE, message="Capacitor energy depleted. Turns needed to recharge.")

        puzzle.energy_left -= 1
        puzzle.grid_bridges[bridge_key] = True

        if puzzle.is_decryption_complete():
            return self.solve_puzzle(captain, pid, kernel)

        return ActionResult(
            success=True,
            action=ActionType.CARTOGRAPHY_BRIDGE,
            message=f"Vector conduit bridged between ({r1},{c1}) and ({r2},{c2})! Progress: {puzzle.get_progress_pct()}%. Energy: {puzzle.energy_left}/{puzzle.energy_max}.",
            data=puzzle.to_dict(),
        )

    def solve_puzzle(self, captain: Captain, puzzle_id: str, kernel: Any) -> ActionResult:
        """Permanently unlocks the secret Ghost Sector or Smuggler Shortcut in the universe graph."""
        puzzle = self.puzzles[puzzle_id]
        first_solve = puzzle.status != "DECRYPTED"
        puzzle.status = "DECRYPTED"
        puzzle.fragments_applied = puzzle.fragments_required
        if first_solve:
            from xylarium.kernel.experience import ExperienceManager
            from xylarium.config import XP_SCIENCE_PUZZLE
            ExperienceManager.award(captain, "science", XP_SCIENCE_PUZZLE, kernel, key=f"puzzle:{puzzle_id}")

        # Mark all nodes revealed & aligned
        for row in puzzle.grid_nodes:
            for n in row:
                n["is_revealed"] = True
                n["vector_angle"] = n["target_angle"]
        for k in puzzle.grid_bridges:
            puzzle.grid_bridges[k] = True

        unlock_id = puzzle.target_unlock
        if unlock_id not in captain.unlocked_secrets:
            captain.unlocked_secrets.append(unlock_id)
        if unlock_id not in self.unlocked_secrets:
            self.unlocked_secrets.append(unlock_id)

        unlock_message = ""
        log_message = ""

        if unlock_id == "GHOST_NEXUS":
            # Unlock Sector 105: Black-Market Nexus
            sec_105 = Sector(
                id=105,
                name="The Black-Market Nexus",
                security=SecurityLevel.ANARCHY,
                warps=[78, 65],
                port=Port(
                    sector_id=105,
                    name="The Shadow Exchange",
                    port_class=PortClass.CLASS_8_BBB,
                    stock={
                        "ORE": 500, "ORGANICS": 500, "EQUIPMENT": 500,
                        "H": 500, "He-3": 500, "C": 500, "H2O": 500, "Xe": 500,
                        "Fe": 500, "Ti": 500, "Si": 500, "Ni": 500, "Cu": 500, "AdL": 250,
                        "U": 250, "Pt": 250, "SpR": 250, "cryogenite": 250, "stelalith": 250,
                        "umbrite": 250, "chitinium": 250, "pyrosite": 250, "aetherium": 250, "ferrolattice": 250,
                        "M1_SUPERCONDUCTOR": 200, "M2_BIOSPHERE_PACK": 200, "M3_ENGINE_MANIFOLD": 200, "M4_WARP_CORE": 200
                    },
                    max_stock={k: 2500 for k in COMMODITY_CONFIG},
                    buys={k: True for k in COMMODITY_CONFIG},
                    sells={k: True for k in COMMODITY_CONFIG},
                ),
                planets=[],
                cluster_name="Smuggler Hollows",
                is_secret=True,
                secret_id="GHOST_NEXUS",
                kind="SYSTEM",
                star_type="Brown dwarf (uncharted)",
            )
            sec_105.port.currency = "VOID"
            sec_105.port.remoteness = 12
            sec_105.port.treasury = 200_000
            from xylarium.kernel import ledger
            ledger.mint("ghost_sector_genesis", sec_105.port.treasury, "VOID")
            if kernel:
                kernel.sectors[105] = sec_105
                if 105 not in kernel.sectors[78].warps:
                    kernel.sectors[78].warps.append(105)
                    kernel.sectors[78].warps.sort()
                if 105 not in kernel.sectors[65].warps:
                    kernel.sectors[65].warps.append(105)
                    kernel.sectors[65].warps.sort()

            unlock_message = (
                "★ CARTOGRAPHIC BREAKTHROUGH: Black-Market Nexus Discovered! "
                "Permanently unlocked Sector 105 tucked between Sectors 078 & 065. "
                "The Shadow Exchange port pays 300% premiums for rare periodic elements!"
            )
            log_message = "[SECRET UNLOCKED] Ghost Sector 105 (The Black-Market Nexus) mapped to navigation graph!"

        elif unlock_id == "PRECURSOR_VAULT":
            # Unlock Sector 106: Precursor Salvage Vault
            vault_planet = Planet(
                id="planet_106",
                sector_id=106,
                name="Aethelgard Prime",
                owner_id=None,
                population=2500,
                shields=500,
                max_shields=500,
                fighters=100,
                citadel_level=4,
                treasury=25000,
                ore_silo=500,
                organics_silo=500,
                element_deposits={
                    "AdL": 5000,
                    "adamant_lode": 5000,
                    "stelalith": 3500,
                    "cryogenite": 2000,
                    "pyrosite": 1500,
                    "umbrite": 1200,
                },
                element_reserves={
                    "AdL": 500,
                    "adamant_lode": 500,
                    "stelalith": 200,
                },
            )
            sec_106 = Sector(
                id=106,
                name="Precursor Salvage Vault",
                security=SecurityLevel.ANARCHY,
                warps=[88, 92],
                port=None,
                planets=[vault_planet],
                cluster_name="The Forgotten Frontier",
                is_secret=True,
                secret_id="PRECURSOR_VAULT",
                kind="SYSTEM",
                star_type="Precursor-engineered pulsar",
            )
            vault_planet.currency = "VOID"
            vault_planet.planet_type = "BARREN"
            from xylarium.kernel import ledger
            ledger.mint("ghost_sector_genesis", vault_planet.treasury, "VOID")
            if kernel:
                kernel.sectors[106] = sec_106
                if 106 not in kernel.sectors[88].warps:
                    kernel.sectors[88].warps.append(106)
                    kernel.sectors[88].warps.sort()
                if 106 not in kernel.sectors[92].warps:
                    kernel.sectors[92].warps.append(106)
                    kernel.sectors[92].warps.sort()

            unlock_message = (
                "★ CARTOGRAPHIC BREAKTHROUGH: Precursor Salvage Vault Discovered! "
                "Sector 106 unlocked with planet Aethelgard Prime: untouched 25,000 Cr vault "
                "and 5,000 Adamant Lode block deposits!"
            )
            log_message = "[SECRET UNLOCKED] Ghost Sector 106 (Precursor Salvage Vault) mapped to navigation graph!"

        elif unlock_id == "SMUGGLER_SHORTCUT":
            # Connect Sector 10 and Sector 70 directly
            if kernel:
                if 70 not in kernel.sectors[10].warps:
                    kernel.sectors[10].warps.append(70)
                    kernel.sectors[10].warps.sort()
                if 10 not in kernel.sectors[70].warps:
                    kernel.sectors[70].warps.append(10)
                    kernel.sectors[70].warps.sort()

            unlock_message = (
                "★ CARTOGRAPHIC BREAKTHROUGH: Smuggler Shortcut Established! "
                "Permanently linked Sector 010 (Borderlands) directly to Sector 070 (Deep Anarchy). "
                "Merchant haulers can now bypass 5 dangerous pirate sectors instantly!"
            )
            log_message = "[SHORTCUT UNLOCKED] Direct hyperspace bypass mapped between Sector 010 and Sector 070!"

        captain.score += 500
        captain.credits += 5000
        from xylarium.kernel import ledger
        ledger.mint("discovery_reward", 5000)

        if kernel and hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender="ASTROGATION-BUREAU",
                text=f"COSMIC DISCOVERY: Captain {captain.name} solved {puzzle.name}! New deep-space coordinates registered across navigation relays.",
                channel="EXPLORATION",
                sector_id=captain.sector_id
            )
            kernel.action_logs.append(log_message)

        return ActionResult(
            success=True,
            action=ActionType.CARTOGRAPHY_SOLVE,
            message=unlock_message,
            logs=[log_message],
            data=puzzle.to_dict(),
        )

    def buy_broker_chit(self, captain: Captain, kernel: Any = None) -> ActionResult:
        """Buy an encrypted starmap chit from shady brokers in Borderland or Anarchy ports."""
        price = 2000
        if captain.credits < price:
            return ActionResult(
                success=False,
                action=ActionType.CARTOGRAPHY_BUY_CHIT,
                message=f"Insufficient credits. Shady data broker demands {price:,} Cr for encrypted starmap chit.",
            )

        captain.credits -= price
        # Pick template based on active puzzle
        unsolved_puzzles = [p.puzzle_id for p in self.puzzles.values() if p.status != "DECRYPTED"]
        target_p = unsolved_puzzles[0] if unsolved_puzzles else "UNIVERSAL"
        matching_templates = [t for t in FRAGMENT_TEMPLATES if t["target_puzzle"] in [target_p, "UNIVERSAL"]]
        tmpl = random.choice(matching_templates if matching_templates else FRAGMENT_TEMPLATES)

        chit = dict(tmpl)
        chit["purchased_cycle"] = getattr(kernel, "cycle_count", 1) if kernel else 1
        stow_fragment(captain, chit)

        log_msg = f"[BROKER DEAL] Acquired {chit['name']} for {price:,} Cr from port data broker."
        if kernel and hasattr(kernel, "action_logs"):
            kernel.action_logs.append(log_msg)

        return ActionResult(
            success=True,
            action=ActionType.CARTOGRAPHY_BUY_CHIT,
            message=f"Purchased {chit['name']} from shady broker for {price:,} Cr! Added to Cartography inventory.",
            logs=[log_msg],
            data={"fragment": chit, "credits": captain.credits},
        )

    def salvage_deep_space(self, captain: Captain, kernel: Any = None) -> ActionResult:
        """Search drifting hulks and deep-void salvage in Anarchy sectors."""
        sec_id = captain.sector_id
        sec = kernel.sectors.get(sec_id) if kernel else None
        if not sec or sec.security != SecurityLevel.ANARCHY:
            return ActionResult(
                success=False,
                action=ActionType.CARTOGRAPHY_SALVAGE,
                message="Deep-void hulk salvage can only be performed in lawless Anarchy sectors (Sectors 061-100).",
            )

        if captain.turns_left < 1:
            return ActionResult(
                success=False,
                action=ActionType.CARTOGRAPHY_SALVAGE,
                message="Deep-space salvage search requires 1 turn.",
            )

        rng = random.Random()
        # 75% chance to find a fragment
        if rng.random() < 0.75:
            unsolved_puzzles = [p.puzzle_id for p in self.puzzles.values() if p.status != "DECRYPTED"]
            target_p = unsolved_puzzles[0] if unsolved_puzzles else "UNIVERSAL"
            matching_templates = [t for t in FRAGMENT_TEMPLATES if t["target_puzzle"] in [target_p, "UNIVERSAL"]]
            tmpl = random.choice(matching_templates if matching_templates else FRAGMENT_TEMPLATES)
            frag = dict(tmpl)
            stow_fragment(captain, frag)
            scrap_cr = captain.ship.cargo.stow("Fe", rng.randint(6, 20)) + captain.ship.cargo.stow("Ti", rng.randint(2, 8))
            log_msg = f"[DEEP-VOID SALVAGE] Discovered drifting derelict in Sector {sec_id:03d}! Salvaged {frag['name']} and {scrap_cr} units of hull scrap."
            if kernel and hasattr(kernel, "action_logs"):
                kernel.action_logs.append(log_msg)
            return ActionResult(
                success=True,
                action=ActionType.CARTOGRAPHY_SALVAGE,
                turns_spent=1,
                message=f"Salvage search successful! Recovered {frag['name']} and {scrap_cr} units of Fe/Ti hull scrap.",
                logs=[log_msg],
                data={"fragment": frag, "scrap_credits": scrap_cr},
            )
        else:
            scrap_cr = captain.ship.cargo.stow("Fe", rng.randint(3, 10))
            msg = f"Derelict hull picked clean by scavengers. Salvaged {scrap_cr} units of raw structural scrap."
            return ActionResult(
                success=True,
                action=ActionType.CARTOGRAPHY_SALVAGE,
                turns_spent=1,
                message=msg,
                data={"scrap_credits": scrap_cr},
            )

    def award_pirate_drop(self, captain: Captain, target: Captain, sector: Sector, kernel: Any = None) -> Optional[Dict[str, Any]]:
        """Drops a corrupted starmap fragment when defeating a pirate ship in combat."""
        if target.personality and target.personality.value == "pirate":
            unsolved_puzzles = [p.puzzle_id for p in self.puzzles.values() if p.status != "DECRYPTED"]
            target_p = unsolved_puzzles[0] if unsolved_puzzles else "UNIVERSAL"
            matching = [t for t in FRAGMENT_TEMPLATES if t["target_puzzle"] in [target_p, "UNIVERSAL"]]
            frag = dict(random.choice(matching if matching else FRAGMENT_TEMPLATES))
            stow_fragment(captain, frag)
            log_msg = f"[PIRATE SALVAGE] Recovered encrypted starmap fragment '{frag['name']}' from the burning wreckage of {target.name}!"
            if kernel and hasattr(kernel, "action_logs"):
                kernel.action_logs.append(log_msg)
            return frag
        return None

    def recharge_energy(self) -> None:
        """Recharges capacitor energy for all active puzzles on turn maintenance."""
        for p in self.puzzles.values():
            p.energy_left = p.energy_max

    def catalyze_puzzle(
        self,
        captain: Captain,
        puzzle_id: Optional[str] = None,
        element: Optional[str] = None,
        amount: int = 5,
        kernel: Any = None
    ) -> ActionResult:
        """Injects rare periodic elements as catalytic reagents to energize Precursor matrix conduits."""
        pid = puzzle_id or self.active_puzzle_id
        if pid not in self.puzzles:
            return ActionResult(success=False, action=ActionType.CARTOGRAPHY_CATALYZE, message=f"Unknown puzzle '{pid}'.")

        puzzle = self.puzzles[pid]
        if not puzzle.required_reagents:
            return ActionResult(
                success=False,
                action=ActionType.CARTOGRAPHY_CATALYZE,
                message=f"Matrix '{puzzle.name}' does not require elemental catalysis."
            )

        if puzzle.is_catalyzed:
            return ActionResult(
                success=False,
                action=ActionType.CARTOGRAPHY_CATALYZE,
                message=f"Matrix '{puzzle.name}' has already undergone elemental catalysis."
            )

        # Check for species bonus: Cryogenic species (Stillcold) get free cryogenic cooling
        species = getattr(captain, "species", "")
        if "Stillcold" in species or "Cryo" in species or (captain.personality and captain.personality.value == "cryogenic"):
            if "SpR" in puzzle.required_reagents and puzzle.applied_reagents.get("SpR", 0) < puzzle.required_reagents["SpR"]:
                puzzle.applied_reagents["SpR"] = puzzle.required_reagents["SpR"]
                if kernel and hasattr(kernel, "action_logs"):
                    kernel.action_logs.append("[SPECIES CATALYSIS] Cryocoherent biology naturally supercooled matrix conduits (Free SpR fulfilled).")

        alias_map = {
            "URANIUM": "U", "ENRICHED_URANIUM": "U", "FISSIONABLE": "U",
            "SPIRAL_RIME": "SpR", "CRYSTAL": "SpR", "CRYOGENITE": "SpR",
            "ADAMANT": "AdL", "ADAMANT_LODE": "AdL", "HE-3": "He-3", "HELIUM-3": "He-3"
        }

        cargo_elems = captain.ship.cargo.elements
        injected_any = False
        injected_summary = []

        target_elems = [element.upper()] if element else list(puzzle.required_reagents.keys())

        for req_raw in target_elems:
            req_key = alias_map.get(req_raw.upper(), req_raw)
            matched_p_key = next((k for k in puzzle.required_reagents if k.upper() == req_key.upper()), None)
            if not matched_p_key:
                continue

            needed = puzzle.required_reagents[matched_p_key] - puzzle.applied_reagents.get(matched_p_key, 0)
            if needed <= 0:
                continue

            cargo_key = next((k for k in cargo_elems if k.upper() == req_key.upper() or k.upper() == matched_p_key.upper()), None)
            avail = cargo_elems.get(cargo_key, 0) if cargo_key else 0

            if avail <= 0 and hasattr(captain.ship.cargo, "equipment") and matched_p_key == "U" and captain.ship.cargo.unbonded("EQUIPMENT") >= needed:
                to_inject = min(amount, needed, captain.ship.cargo.unbonded("EQUIPMENT"))
                captain.ship.cargo.equipment -= to_inject
                puzzle.applied_reagents[matched_p_key] = puzzle.applied_reagents.get(matched_p_key, 0) + to_inject
                injected_any = True
                injected_summary.append(f"{to_inject}x {matched_p_key} (from Tech Equipment)")
            elif avail > 0:
                to_inject = min(amount, needed, avail)
                cargo_elems[cargo_key] -= to_inject
                puzzle.applied_reagents[matched_p_key] = puzzle.applied_reagents.get(matched_p_key, 0) + to_inject
                injected_any = True
                injected_summary.append(f"{to_inject}x {matched_p_key}")

        if not injected_any:
            req_str = ", ".join([f"{k}: {puzzle.applied_reagents.get(k, 0)}/{v}" for k, v in puzzle.required_reagents.items()])
            return ActionResult(
                success=False,
                action=ActionType.CARTOGRAPHY_CATALYZE,
                message=f"Insufficient catalytic reagents in cargo hold. Required elements: [{req_str}]."
            )

        all_satisfied = all(
            puzzle.applied_reagents.get(k, 0) >= v
            for k, v in puzzle.required_reagents.items()
        )
        if all_satisfied:
            puzzle.is_catalyzed = True
            log_msg = f"[CATALYSIS BREAKTHROUGH] Matrix '{puzzle.name}' energized! Quantum lock released (+20% decryption surge)."
            if kernel and hasattr(kernel, "action_logs"):
                kernel.action_logs.append(log_msg)
            if kernel and hasattr(kernel, "event_bus"):
                kernel.event_bus.broadcast_radio("LAB-AI", log_msg, channel="SCIENCE", sector_id=captain.sector_id)
            return ActionResult(
                success=True,
                action=ActionType.CARTOGRAPHY_CATALYZE,
                message=f"Catalysis successful! Injected {', '.join(injected_summary)}. Quantum lock dissolved! Progress: {puzzle.get_progress_pct()}%.",
                logs=[log_msg],
                data=puzzle.to_dict(),
            )

        req_str = ", ".join([f"{k}: {puzzle.applied_reagents.get(k, 0)}/{v}" for k, v in puzzle.required_reagents.items()])
        msg = f"Injected {', '.join(injected_summary)}. Current catalytic status: [{req_str}]."
        return ActionResult(
            success=True,
            action=ActionType.CARTOGRAPHY_CATALYZE,
            message=msg,
            data=puzzle.to_dict(),
        )

    def deploy_toll_gate(
        self,
        captain: Captain,
        shortcut_id: str = "SMUGGLER_SHORTCUT",
        toll_fee: int = 500,
        kernel: Any = None
    ) -> ActionResult:
        """Deploys an automated orbital toll satellite on an unlocked secret shortcut or ghost sector."""
        valid_targets = {
            "SMUGGLER_SHORTCUT": (10, 70, "Sector 010 <-> Sector 070 Bypass"),
            "GHOST_NEXUS": (78, 105, "Sector 078 <-> Sector 105 Nexus"),
            "PRECURSOR_VAULT": (88, 106, "Sector 088 <-> Sector 106 Vault"),
        }

        matched_key = None
        for k, v in valid_targets.items():
            if k == shortcut_id or str(v[0]) in str(shortcut_id) or str(v[1]) in str(shortcut_id):
                matched_key = k
                break

        if not matched_key or matched_key not in captain.unlocked_secrets:
            return ActionResult(
                success=False,
                action=ActionType.TOLL_GATE_DEPLOY,
                message="Toll satellites can only be deployed on shortcuts or ghost sectors you have decrypted and unlocked."
            )

        sec_a, sec_b, name = valid_targets[matched_key]
        gate_exists = any(
            (tg.sector_a == sec_a and tg.sector_b == sec_b) or (tg.sector_a == sec_b and tg.sector_b == sec_a)
            for tg in self.toll_gates.values() if tg.active
        )
        if gate_exists:
            return ActionResult(
                success=False,
                action=ActionType.TOLL_GATE_DEPLOY,
                message=f"An active toll satellite is already operational on the {name} corridor."
            )

        cost = TOLL_GATE_DEPLOY_COST_CREDITS
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.TOLL_GATE_DEPLOY,
                message=f"Deploying an orbital toll satellite requires {cost:,} Credits. (Current: {captain.credits:,} Cr)."
            )

        captain.credits -= cost
        gate_id = f"TOLL-{self.gate_counter}"
        self.gate_counter += 1

        toll_fee = max(100, min(2500, toll_fee))
        gate = TollGate(
            id=gate_id,
            owner_id=captain.id,
            sector_a=sec_a,
            sector_b=sec_b,
            toll_fee=toll_fee,
            drones=30,
            active=True,
            created_cycle=getattr(kernel, "cycle_count", 1) if kernel else 1,
        )
        self.toll_gates[gate_id] = gate
        captain.toll_gates.append(gate_id)

        log_msg = f"[TOLL SATELLITE] Deployed orbital toll gate {gate_id} on {name}! Fee: {toll_fee} Cr per transit."
        if kernel and hasattr(kernel, "action_logs"):
            kernel.action_logs.append(log_msg)
        if kernel and hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender=captain.name,
                text=f"COMMERCE NOTICE: Orbital toll satellite active on Sector {sec_a:03d}<->{sec_b:03d} corridor. Transit fee: {toll_fee} Cr.",
                channel="COMMERCE",
                sector_id=sec_a,
            )

        return ActionResult(
            success=True,
            action=ActionType.TOLL_GATE_DEPLOY,
            message=f"Orbital toll gate {gate_id} commissioned on {name}! Charging {toll_fee} Cr per transit.",
            logs=[log_msg],
            data=gate.to_dict(),
        )

    def set_toll_fee(
        self,
        captain: Captain,
        gate_id: str,
        new_fee: int
    ) -> ActionResult:
        """Configures the transit fee on an owned toll gate."""
        if gate_id not in self.toll_gates:
            return ActionResult(success=False, action=ActionType.TOLL_GATE_SET_FEE, message=f"Toll gate '{gate_id}' not found.")

        gate = self.toll_gates[gate_id]
        if gate.owner_id != captain.id:
            return ActionResult(success=False, action=ActionType.TOLL_GATE_SET_FEE, message="Cannot modify toll rates of a gate you do not own.")

        clamped = max(100, min(2500, new_fee))
        gate.toll_fee = clamped
        return ActionResult(
            success=True,
            action=ActionType.TOLL_GATE_SET_FEE,
            message=f"Toll rate for {gate_id} updated to {clamped:,} Credits per transit.",
            data=gate.to_dict(),
        )

    def check_toll_transit(
        self,
        traveler: Captain,
        from_sec: int,
        to_sec: int,
        kernel: Any = None
    ) -> int:
        """
        Intercepts transit across toll routes.
        Returns:
          0: No toll (or traveler is owner)
          > 0: Toll paid
          -1: Intercepted by picket drones (insufficient credits or hostile)
        """
        for gate in self.toll_gates.values():
            if not gate.active:
                continue
            matches = (
                (gate.sector_a == from_sec and gate.sector_b == to_sec) or
                (gate.sector_a == to_sec and gate.sector_b == from_sec)
            )
            if matches:
                if gate.owner_id == traveler.id:
                    return 0

                fee = gate.toll_fee
                owner = kernel.captains.get(gate.owner_id) if kernel else None

                if traveler.credits >= fee:
                    traveler.credits -= fee
                    if owner:
                        owner.credits += fee
                    gate.total_revenue += fee
                    gate.total_transits += 1

                    log_msg = f"[TOLL GATE] {traveler.name} paid {fee:,} Cr toll on Sector {from_sec:03d}<->{to_sec:03d} corridor."
                    if kernel and hasattr(kernel, "action_logs"):
                        kernel.action_logs.append(log_msg)
                    return fee
                else:
                    traveler.ship.shields = max(0, traveler.ship.shields - 35)
                    log_msg = f"[TOLL INTERCEPTION] {traveler.name} attempted to bypass toll gate without {fee:,} Cr! Picket drones fired (-35 shields)."
                    if kernel and hasattr(kernel, "action_logs"):
                        kernel.action_logs.append(log_msg)
                    return -1
        return 0

    def forge_starmap_chit(
        self,
        captain: Captain,
        mode: str = "sell",
        target_rival_id: Optional[str] = None,
        kernel: Any = None,
        **kwargs
    ) -> ActionResult:
        """
        Manufactures a forged or booby-trapped starmap chit, or lateral Precursor Chimera.
        Mode 'sell': Sells to shady port broker for 3,000 Cr profit.
        Mode 'plant': Infiltrates rival data vault or Anarchy relay to bait rival haulers into an ambush.
        Mode 'transponder': Forges a spoofed Federal Transponder Chit allowing outlaws to bypass Core defense turrets.
        Mode 'chimera': Synthesizes a lateral Precursor Chimerism graft bridging biological lineages.
        """
        is_chimera = mode.lower() in ["chimera", "precursor_chimera", "graft"]
        if is_chimera:
            from xylarium.kernel.phylogeny import PHYLOGENY_MANAGER
            hybrid_node_id = kwargs.get("hybrid_node_id") or kwargs.get("target_hybrid_id") or target_rival_id or "chimera_absolute_zero_alchemist"
            ok, msg = PHYLOGENY_MANAGER.check_chimera_requirements(captain, hybrid_node_id)
            if not ok:
                return ActionResult(success=False, action=ActionType.CARTOGRAPHY_FORGE_CHIT, message=msg)

        cost = FORGED_CHIT_SYNTH_COST
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.CARTOGRAPHY_FORGE_CHIT,
                message=f"Forging starmap telemetry requires {cost:,} Credits in neural decryption chips.",
            )

        if not captain.cartography_fragments:
            return ActionResult(
                success=False,
                action=ActionType.CARTOGRAPHY_FORGE_CHIT,
                message="Forging a fake chart requires 1 genuine starmap fragment to corrupt.",
            )

        captain.credits -= cost
        corrupted_frag = captain.cartography_fragments.pop(0)

        if is_chimera:
            ok, msg = PHYLOGENY_MANAGER.graft_precursor_chimera(captain, hybrid_node_id, kernel)
            if ok:
                log_msg = f"[PRECURSOR CHIMERA] {captain.name} grafted {hybrid_node_id} via Cartography Lab!"
                if kernel and hasattr(kernel, "action_logs"):
                    kernel.action_logs.append(log_msg)
                return ActionResult(
                    success=True,
                    action=ActionType.CARTOGRAPHY_FORGE_CHIT,
                    message=msg,
                    logs=[log_msg],
                    data={"hybrid_node_id": hybrid_node_id, "corrupted_fragment": corrupted_frag},
                )
            else:
                captain.credits += cost
                captain.cartography_fragments.insert(0, corrupted_frag)
                return ActionResult(
                    success=False,
                    action=ActionType.CARTOGRAPHY_FORGE_CHIT,
                    message=msg,
                )

        elif mode.lower() in ["transponder", "spoof", "transponder_chit"]:
            if "FORGED_TRANSPONDER" not in captain.unlocked_secrets:
                captain.unlocked_secrets.append("FORGED_TRANSPONDER")
            captain.forged_transponder = True
            log_msg = f"[CARTOGRAPHY LAB] Forged spoofed Federal Transponder Chit from {corrupted_frag.get('name', 'nav fragment')}! Core automated defense turrets bypassed."
            if kernel and hasattr(kernel, "action_logs"):
                kernel.action_logs.append(log_msg)
            return ActionResult(
                success=True,
                action=ActionType.CARTOGRAPHY_FORGE_CHIT,
                message="Successfully forged a spoofed Federal Transponder Chit! Automated Core defense turrets will now recognize your transponder as a licensed merchant vessel.",
                logs=[log_msg],
                data={"unlocked_secret": "FORGED_TRANSPONDER", "corrupted_fragment": corrupted_frag},
            )

        elif mode == "plant" and kernel:
            anarchy_secs = [s.id for s in kernel.sectors.values() if s.security == SecurityLevel.ANARCHY]
            ambush_sec = random.choice(anarchy_secs) if anarchy_secs else 77

            rival_name = "Rival Merchant Fleet"
            if target_rival_id and target_rival_id in kernel.captains:
                rival = kernel.captains[target_rival_id]
                rival.ship.shields = max(0, rival.ship.shields - 50)
                rival_name = rival.name
            else:
                ai_caps = [c for c in kernel.captains.values() if c.is_ai]
                if ai_caps:
                    rival = random.choice(ai_caps)
                    rival.ship.shields = max(0, rival.ship.shields - 40)
                    rival_name = rival.name

            bounty = captain.ship.cargo.stow("Fe", 10) + captain.ship.cargo.stow("Ti", 5)
            log_msg = f"[ESPIONAGE AMBUSH] Placed forged chart in {rival_name}'s star-vault! Rival warped into pirate ambush in Sector {ambush_sec:03d} ({bounty} units salvage)."
            if kernel and hasattr(kernel, "action_logs"):
                kernel.action_logs.append(log_msg)
            if kernel and hasattr(kernel, "event_bus"):
                kernel.event_bus.broadcast_radio(
                    "PIRATE-NET",
                    f"AMBUSH CONFIRMED: {rival_name} walked into our crosshairs in Sector {ambush_sec:03d} thanks to corrupted nav coordinates!",
                    channel="COMM-1",
                    sector_id=ambush_sec
                )

            return ActionResult(
                success=True,
                action=ActionType.CARTOGRAPHY_FORGE_CHIT,
                message=f"Forged chart successfully planted! {rival_name} ambushed in Sector {ambush_sec:03d}. Salvaged {bounty} units of scrap.",
                logs=[log_msg],
                data={"target": rival_name, "ambush_sector": ambush_sec, "salvage": bounty, "corrupted_fragment": corrupted_frag},
            )
        else:
            # The shady broker is a starport fixer: paid out of the local port's treasury in local money
            broker_sec = kernel.sectors.get(captain.sector_id) if kernel else None
            broker_port = broker_sec.port if broker_sec else None
            from xylarium.kernel import fx as fx_mod
            rate = fx_mod.ACTIVE_FX.rate(broker_port.currency) if (broker_port and fx_mod.ACTIVE_FX) else 1.0
            local_payout = int(FORGED_CHIT_BROKER_VALUE * rate)
            if broker_port is None or broker_port.treasury < local_payout:
                captain.credits += cost
                captain.cartography_fragments.insert(0, corrupted_frag)
                return ActionResult(
                    success=False,
                    action=ActionType.CARTOGRAPHY_FORGE_CHIT,
                    message="No broker here can pay for a forged chart: dock at a liquid starport.",
                )
            broker_port.treasury -= local_payout
            fx_mod.credit(captain, broker_port.currency, local_payout)
            payout = FORGED_CHIT_BROKER_VALUE
            log_msg = f"[COUNTERFEIT SALE] Sold forged starmap chit to shady port broker for {payout:,} Cr (Net: +{payout - cost:,} Cr)!"
            if kernel and hasattr(kernel, "action_logs"):
                kernel.action_logs.append(log_msg)

            return ActionResult(
                success=True,
                action=ActionType.CARTOGRAPHY_FORGE_CHIT,
                message=f"Forged starmap chit sold to port broker for {payout:,} Cr! (Net profit: +{payout - cost:,} Cr).",
                logs=[log_msg],
                data={"credits": captain.credits, "profit": payout - cost, "corrupted_fragment": corrupted_frag},
            )

    def execute_chimeric_graft(
        self,
        captain: Captain,
        hybrid_node_id: str,
        kernel: Any = None,
    ) -> ActionResult:
        """Directly synthesizes a Precursor Chimeric graft in the Cartography Lab."""
        from xylarium.kernel.phylogeny import PHYLOGENY_MANAGER
        ok, msg = PHYLOGENY_MANAGER.graft_precursor_chimera(captain, hybrid_node_id, kernel)
        if ok:
            log_msg = f"[PRECURSOR CHIMERA] {captain.name} synthesized lateral graft [{hybrid_node_id}]!"
            if kernel and hasattr(kernel, "action_logs"):
                kernel.action_logs.append(log_msg)
            return ActionResult(
                success=True,
                action=ActionType.CARTOGRAPHY_FORGE_CHIT,
                message=msg,
                logs=[log_msg],
                data={"hybrid_node_id": hybrid_node_id},
            )
        return ActionResult(
            success=False,
            action=ActionType.CARTOGRAPHY_FORGE_CHIT,
            message=msg,
        )

    def launch_survey_probe(
        self,
        captain: Captain,
        target_sector: int = 61,
        kernel: Any = None
    ) -> ActionResult:
        """Launches an autonomous unmanned deep-space survey probe to sweep frontier space for anomalies and fragments."""
        cost = SURVEY_PROBE_COST_CREDITS
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.SURVEY_PROBE_LAUNCH,
                message=f"Commissioning a Deep-Space Survey Probe requires {cost:,} Credits.",
            )

        captain.credits -= cost
        probe_id = f"PROBE-{self.probe_counter}"
        self.probe_counter += 1

        probe = SurveyProbe(
            id=probe_id,
            owner_id=captain.id,
            current_sector=captain.sector_id,
            target_sector=target_sector,
            shields=50,
            max_shields=50,
            status="SCANNING",
            sectors_surveyed=[captain.sector_id],
            launched_cycle=getattr(kernel, "cycle_count", 1) if kernel else 1,
        )
        self.survey_probes[probe_id] = probe
        captain.survey_probes.append(probe_id)

        log_msg = f"[SURVEY PROBE] Launched {probe_id} from Sector {captain.sector_id:03d} targeting frontier Sector {target_sector:03d}!"
        if kernel and hasattr(kernel, "action_logs"):
            kernel.action_logs.append(log_msg)

        return ActionResult(
            success=True,
            action=ActionType.SURVEY_PROBE_LAUNCH,
            message=f"Deep-Space Survey Probe {probe_id} deployed into orbital transit! Autonomously surveying frontier space.",
            logs=[log_msg],
            data=probe.to_dict(),
        )

    def tick_survey_probes(self, kernel: Any = None) -> List[str]:
        """Advances autonomous survey probes each turn/cycle: sweeps sectors, harvests fragments, reports telemetry."""
        logs = []
        if not kernel:
            return logs

        for probe in list(self.survey_probes.values()):
            if probe.status == "LOST_SIGNAL":
                continue

            sec = kernel.sectors.get(probe.current_sector)
            if not sec or not sec.warps:
                continue

            unvisited = [w for w in sec.warps if w not in probe.sectors_surveyed]
            next_sec_id = random.choice(unvisited if unvisited else sec.warps)
            probe.current_sector = next_sec_id
            probe.sectors_surveyed.append(next_sec_id)
            if len(probe.sectors_surveyed) > 20:
                probe.sectors_surveyed = probe.sectors_surveyed[-20:]

            target_sec = kernel.sectors.get(next_sec_id)
            is_anarchy_or_frontier = (target_sec and target_sec.security == SecurityLevel.ANARCHY) or next_sec_id >= 60

            rng = random.Random()
            if is_anarchy_or_frontier and rng.random() < 0.35:
                owner = kernel.captains.get(probe.owner_id)
                unsolved = [p.puzzle_id for p in self.puzzles.values() if p.status != "DECRYPTED"]
                target_p = unsolved[0] if unsolved else "UNIVERSAL"
                matching = [t for t in FRAGMENT_TEMPLATES if t["target_puzzle"] in [target_p, "UNIVERSAL"]]
                frag = dict(random.choice(matching if matching else FRAGMENT_TEMPLATES))

                if owner:
                    stow_fragment(owner, frag)
                    probe.fragments_found += 1
                    msg = f"[PROBE DISCOVERY] Survey Probe {probe.id} scanned Sector {next_sec_id:03d} and recovered {frag['name']}!"
                    logs.append(msg)
                    if hasattr(kernel, "action_logs"):
                        kernel.action_logs.append(msg)
                    if hasattr(kernel, "event_bus"):
                        kernel.event_bus.broadcast_radio("TELEMETRY", msg, channel="EXPLORATION", sector_id=next_sec_id)

            if is_anarchy_or_frontier and rng.random() < 0.10:
                dmg = rng.randint(10, 20)
                probe.shields = max(0, probe.shields - dmg)
                if probe.shields == 0:
                    probe.status = "LOST_SIGNAL"
                    msg = f"[PROBE TELEMETRY] Survey Probe {probe.id} sustained critical micrometeorite damage in Sector {next_sec_id:03d}. Signal lost."
                    logs.append(msg)
                    if hasattr(kernel, "action_logs"):
                        kernel.action_logs.append(msg)

        return logs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_puzzle_id": self.active_puzzle_id,
            "unlocked_secrets": list(self.unlocked_secrets),
            "puzzles": {pid: p.to_dict() for pid, p in self.puzzles.items()},
            "toll_gates": {gid: tg.to_dict() for gid, tg in self.toll_gates.items()},
            "survey_probes": {pid: sp.to_dict() for pid, sp in self.survey_probes.items()},
            "probe_counter": self.probe_counter,
            "gate_counter": self.gate_counter,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CartographyManager":
        mgr = cls()
        mgr.active_puzzle_id = data.get("active_puzzle_id", "PUZZLE-NEXUS")
        mgr.unlocked_secrets = list(data.get("unlocked_secrets", []))
        mgr.probe_counter = data.get("probe_counter", 100)
        mgr.gate_counter = data.get("gate_counter", 100)
        if "puzzles" in data:
            mgr.puzzles = {
                pid: CartographyPuzzle.from_dict(p_data)
                for pid, p_data in data["puzzles"].items()
            }
        if "toll_gates" in data:
            mgr.toll_gates = {
                gid: TollGate.from_dict(tg_data)
                for gid, tg_data in data["toll_gates"].items()
            }
        if "survey_probes" in data:
            mgr.survey_probes = {
                sp_id: SurveyProbe.from_dict(sp_data)
                for sp_id, sp_data in data["survey_probes"].items()
            }
        return mgr
