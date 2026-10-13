"""
Xylarium elements: the periodic table as a people's almanac reads it - a view over substances.py, nothing declared.

The Netstratum five-axis almanac (line, lane, shell, phase, spin drawn from a hash) is retired: every coordinate is
now read from the matter itself.

  LINE   its period (from Z; for a compound, the deepest of what it is made of)
  LANE   its group (1-18; for a compound, its heaviest constituent's)
  SHELL  how many elements it is made of (1-4): a compound's arity is one more
  PHASE  its workable state at one bar, read from its melting point: cryogenic (below 150 K), mesic (below 600 K),
         furnace (below 1800 K), refractory
  SPIN   its handedness: what life makes is chiral (1); what physics lays down is not (0)
"""

import functools
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

LINES: int = 8
LANES: int = 18
SHELLS: int = 4
PHASES: int = 4
SPINS: int = 2

PHASE_NAMES = {1: "Cryogenic", 2: "Mesic", 3: "Furnace", 4: "Refractory"}
FAMILY_NAMES = {"metal": "Metal", "volatile": "Volatile", "noble": "Noble", "fissile": "Fissile", "ice": "Ice",
                "mineral": "Mineral", "organic": "Organic", "plasma": "Plasma", "exotic": "Superheavy"}
_VALENCE = {1: 1, 2: 2, 13: 3, 14: 4, 15: 3, 16: 2, 17: 1, 18: 0}
_PHASE_EDGES = (150.0, 600.0, 1800.0)


@dataclass(frozen=True)
class PeriodicElement:
    element_id: str
    name: str
    symbol: str
    line: int
    lane: int
    shell: int
    phase: int
    spin: int
    family: str = ""
    description: str = ""

    @property
    def refines_at(self) -> float:
        """How deep in the table it lies, as a share of the deepest period."""
        return round(self.line / float(LINES), 3)

    @property
    def binds(self) -> int:
        """Its typical valence, from its group (transition metals: two)."""
        return _VALENCE.get(self.lane, 2)

    @property
    def arity(self) -> int:
        return 1 + self.shell

    @property
    def phase_name(self) -> str:
        return PHASE_NAMES.get(self.phase, "Unknown")

    @property
    def family_name(self) -> str:
        return FAMILY_NAMES.get(self.family, "General")

    def to_dict(self) -> Dict[str, Any]:
        return {"element_id": self.element_id, "name": self.name, "symbol": self.symbol, "line": self.line,
                "lane": self.lane, "shell": self.shell, "phase": self.phase, "spin": self.spin,
                "refines_at": self.refines_at, "binds": self.binds, "arity": self.arity,
                "phase_name": self.phase_name, "family_name": self.family_name, "description": self.description}


def _phase_class(melt: float) -> int:
    return 1 + sum(1 for e in _PHASE_EDGES if melt >= e)


def _view(sym: str) -> Optional[PeriodicElement]:
    from xylarium.kernel import chemistry, substances
    s = substances.get(sym)
    t = chemistry.TABLE.get(sym)
    if s is None or t is None:
        return None
    parts = substances.constituents(sym)
    return PeriodicElement(element_id=sym, name=t["name"], symbol=sym, line=int(t["line"]), lane=int(t["lane"]),
                           shell=max(1, min(SHELLS, len(parts))), phase=_phase_class(float(s["melt"])),
                           spin=1 if s.get("origin") == "biogenic" else 0, family=t["family"],
                           description=s.get("as", ""))


class PeriodicTable:
    """The almanac: each good of the table, read from its matter."""

    @classmethod
    def get_element(cls, element_id: str) -> Optional[PeriodicElement]:
        from xylarium.kernel import chemistry
        if element_id in chemistry.TABLE:
            return _view(element_id)
        low = {k.lower(): k for k in chemistry.TABLE}
        if element_id.lower() in low:
            return _view(low[element_id.lower()])
        # Check 118+ continuum elements
        try:
            from xylarium.kernel import elements_continuum
            symbols_lower = [s.lower() for s in elements_continuum.PERIODIC_SYMBOLS]
            if element_id.lower() in symbols_lower:
                z = symbols_lower.index(element_id.lower())
                ce = elements_continuum.get_element(z)
                return PeriodicElement(
                    element_id=ce.symbol, name=ce.name, symbol=ce.symbol,
                    line=ce.line, lane=ce.lane, shell=1,
                    phase=1 if ce.condensation_k < 150 else (2 if ce.condensation_k < 600 else 3),
                    spin=0, family="Continuum", description=f"Atomic number {ce.z}"
                )
        except Exception:
            pass
        return None

    @classmethod
    def all_canonical(cls) -> List[PeriodicElement]:
        from xylarium.kernel import chemistry
        return [e for e in (_view(k) for k in chemistry.TABLE) if e is not None]

    @classmethod
    def get_elements_for_metabolism(cls, metabolism: str) -> List[PeriodicElement]:
        """What a chemistry can hold in its hands: the two most abundant goods solid at its own body temperature
        (uses.py: the warmest of its region's solvents) - read, not chosen for it."""
        from xylarium.kernel import worlds
        return list(_for_metabolism(metabolism.lower(), worlds._laws(None)))


@functools.lru_cache(maxsize=64)
def _for_metabolism(metabolism: str, laws: Any) -> tuple:              # laws: body temperatures are the universe's
    from xylarium.kernel import chemistry, uses, worlds
    cands = uses._region_solvents(metabolism) or ["H2O"]
    t = max(worlds.body_temperature(x) for x in cands)
    solid = [k for k, e in chemistry.TABLE.items() if e["origin"] != "stellar" and uses.solid_at(k, t)]
    solid.sort(key=lambda k: -chemistry.TABLE[k]["abund"])
    return tuple(e for e in (_view(k) for k in solid[:2]) if e is not None)
