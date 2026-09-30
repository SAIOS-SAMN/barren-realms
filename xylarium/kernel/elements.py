"""
The Periodic Table of Elements for Xylarium.
Ported from Netstratum (/opt/netstratum/engine/cfe/src/almanac/periodic.rs and 31_ELEMENT_COMMERCE.md).

Five-Axis Periodic Coordinate System:
  LINE  (1..=7)  Depth / Pressure required to refine (refines_at = line / 7.0)
  LANE  (1..=10) Group / Character -> recurring valence (binds = lane if lane <= 5 else 11 - lane)
  SHELL (1..=4)  Binding Geometry / Arity (arity = 1 + shell, 2..=5 bodies)
  PHASE (1..=4)  Workable State (1: Cold/Cryo, 2: Mesic/Ambient, 3: Furnace/Thermal, 4: Refractory)
  SPIN  (0..=1)  Chirality / Handedness (0: Left/Dextro, 1: Right/Laevo)

Total Cells: 7 * 10 * 4 * 4 * 2 = 2,240 cells.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import hashlib

# Periodic Axis Constants
LINES: int = 7
LANES: int = 10
SHELLS: int = 4
PHASES: int = 4
SPINS: int = 2
CELLS: int = LINES * LANES * SHELLS * PHASES * SPINS  # 2,240

PHASE_NAMES = {
    1: "Cryogenic",
    2: "Mesic",
    3: "Furnace",
    4: "Refractory",
}

FAMILY_NAMES = {
    1: "Lithic",
    2: "Biotic",
    3: "Cryo",
    4: "Plasmic",
    5: "Umbral",
    6: "Refractory",
    7: "Resonant",
}


@dataclass(frozen=True)
class PeriodicElement:
    """Represents an element on the 5-axis periodic table."""
    element_id: str
    name: str
    symbol: str
    line: int       # 1..=7
    lane: int       # 1..=10
    shell: int      # 1..=4
    phase: int      # 1..=4
    spin: int       # 0..=1
    description: str = ""

    @property
    def refines_at(self) -> float:
        """Pressure / tech fraction required to refine this element (0.142 to 1.0)."""
        return round(self.line / float(LINES), 3)

    @property
    def binds(self) -> int:
        """Valence folds at the half: 1..=5 rising, then back down."""
        return self.lane if self.lane <= (LANES // 2) else (LANES + 1 - self.lane)

    @property
    def arity(self) -> int:
        """How many elements enter a compound of this geometry: 1 + shell (2..=5)."""
        return 1 + self.shell

    @property
    def phase_name(self) -> str:
        return PHASE_NAMES.get(self.phase, "Unknown")

    @property
    def family_name(self) -> str:
        return FAMILY_NAMES.get(self.line, "General")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "name": self.name,
            "symbol": self.symbol,
            "line": self.line,
            "lane": self.lane,
            "shell": self.shell,
            "phase": self.phase,
            "spin": self.spin,
            "refines_at": self.refines_at,
            "binds": self.binds,
            "arity": self.arity,
            "phase_name": self.phase_name,
            "family_name": self.family_name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PeriodicElement":
        return cls(
            element_id=data["element_id"],
            name=data["name"],
            symbol=data["symbol"],
            line=data["line"],
            lane=data["lane"],
            shell=data["shell"],
            phase=data["phase"],
            spin=data["spin"],
            description=data.get("description", ""),
        )


# Canonical Netstratum Primary Elements
CANONICAL_ELEMENTS: Dict[str, PeriodicElement] = {
    "stelalith": PeriodicElement(
        element_id="stelalith",
        name="Stelalith",
        symbol="Stl",
        line=3,
        lane=4,
        shell=2,
        phase=2,
        spin=0,
        description="Deep crystalline mineral found in planetary mantles, revered by lithophage polities."
    ),
    "umbrite": PeriodicElement(
        element_id="umbrite",
        name="Umbrite",
        symbol="Umb",
        line=5,
        lane=8,
        shell=3,
        phase=1,
        spin=1,
        description="Dark cold-condensate element formed in deep void anomalies, essential for umbral metabolisms."
    ),
    "cryogenite": PeriodicElement(
        element_id="cryogenite",
        name="Cryogenite",
        symbol="Crg",
        line=2,
        lane=2,
        shell=1,
        phase=1,
        spin=0,
        description="Cryogenic superconductive ice used for thermal banking and hyper-computing arrays."
    ),
    "pyrosite": PeriodicElement(
        element_id="pyrosite",
        name="Pyrosite",
        symbol="Pyr",
        line=4,
        lane=7,
        shell=2,
        phase=3,
        spin=0,
        description="High-temperature furnace element harvested from coronal flares and deep magma chambers."
    ),
    "aetherium": PeriodicElement(
        element_id="aetherium",
        name="Aetherium",
        symbol="Aeth",
        line=6,
        lane=9,
        shell=4,
        phase=4,
        spin=1,
        description="Sublime refractory radiant compound capable of stabilizing hyper-dimensional shield barriers."
    ),
    "chitinium": PeriodicElement(
        element_id="chitinium",
        name="Chitinium",
        symbol="Cht",
        line=1,
        lane=3,
        shell=1,
        phase=2,
        spin=0,
        description="Calcified bio-crystalline resin secreted by biotic swarms, resilient and lightweight."
    ),
    "ferrolattice": PeriodicElement(
        element_id="ferrolattice",
        name="Ferrolattice",
        symbol="Flt",
        line=2,
        lane=5,
        shell=2,
        phase=2,
        spin=0,
        description="High-valence bonded magnetic metal alloy serving as structural foundation for heavy starcraft."
    ),
    "void_resin": PeriodicElement(
        element_id="void_resin",
        name="Void-Resin",
        symbol="Vrs",
        line=4,
        lane=2,
        shell=3,
        phase=1,
        spin=1,
        description="Anhydrous cold polymer synthesized by void-sleepers to seal atmospheric ruptures."
    ),
    "sol_plasma": PeriodicElement(
        element_id="sol_plasma",
        name="Sol-Plasma",
        symbol="Spl",
        line=5,
        lane=6,
        shell=1,
        phase=3,
        spin=0,
        description="Energized ionic substance from star coronas powering heavy weapon capacitors."
    ),
    "mirror_glass": PeriodicElement(
        element_id="mirror_glass",
        name="Mirror-Glass",
        symbol="Mrg",
        line=7,
        lane=10,
        shell=4,
        phase=4,
        spin=1,
        description="Apex refractory lattice exhibiting perfect topological reflection across all wavelengths."
    ),
}


class PeriodicTable:
    """Manager and catalog for the 5-axis periodic table of elements."""

    _catalog: Dict[str, PeriodicElement] = dict(CANONICAL_ELEMENTS)

    @classmethod
    def get_element(cls, element_id: str) -> Optional[PeriodicElement]:
        return cls._catalog.get(element_id.lower())

    @classmethod
    def all_canonical(cls) -> List[PeriodicElement]:
        return list(cls._catalog.values())

    @classmethod
    def generate_from_hash(cls, seed_key: str) -> PeriodicElement:
        """
        Deterministically reads an element from a hash string, exactly like Netstratum's
        `periodic_of(element: &[u8; 32])` which draws bytes 3..=7 for the 5 axes.
        """
        digest = hashlib.sha256(seed_key.encode("utf-8")).digest()
        line = 1 + (digest[3] % LINES)
        lane = 1 + (digest[4] % LANES)
        shell = 1 + (digest[5] % SHELLS)
        phase = 1 + (digest[6] % PHASES)
        spin = digest[7] % SPINS

        elem_id = f"el_{line}_{lane}_{shell}_{phase}_{spin}"
        if elem_id in cls._catalog:
            return cls._catalog[elem_id]

        p_name = PHASE_NAMES.get(phase, "Mesic")
        f_name = FAMILY_NAMES.get(line, "Lithic")
        name = f"{p_name} {f_name}-{line}{lane}"
        symbol = f"{f_name[:2]}{line}{lane}"

        element = PeriodicElement(
            element_id=elem_id,
            name=name,
            symbol=symbol,
            line=line,
            lane=lane,
            shell=shell,
            phase=phase,
            spin=spin,
            description=f"5-Axis Element [Line {line}, Lane {lane}, Shell {shell}, Phase {phase}, Spin {spin}]."
        )
        cls._catalog[elem_id] = element
        return element

    @classmethod
    def get_elements_for_metabolism(cls, metabolism: str) -> List[PeriodicElement]:
        """Returns primary elements favored by a specific metabolism."""
        metabolism = metabolism.lower()
        if metabolism == "mineral":
            return [cls._catalog["stelalith"], cls._catalog["ferrolattice"]]
        elif metabolism == "biotic":
            return [cls._catalog["chitinium"], cls._catalog["cryogenite"]]
        elif metabolism == "plasmic":
            return [cls._catalog["pyrosite"], cls._catalog["sol_plasma"]]
        elif metabolism == "umbral":
            return [cls._catalog["umbrite"], cls._catalog["void_resin"]]
        return [cls._catalog["stelalith"], cls._catalog["chitinium"]]
