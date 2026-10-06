"""
Xylarium concentration: how a world's flows gather what its formation scattered - the form-building half of its
matter, beside the dispersal thermodynamics describes.

A world's elements are laid down dispersed: each a fraction x of its host (rock for what condenses into rock, ice for
what freezes out). Left alone, they stay dispersed and dispersal only runs on. But a world with flows - a mantle that
melts and rises, water driven through hot rock, rivers sorting what erosion frees, life changing what dissolves and
what settles - builds concentrations against that: veins, placers, layered intrusions, banded beds. A deposit is the
standing form those flows keep, the way a convection cell is: it lasts while the flow lasts, and it is rebuilt at
the flow's pace when it is taken.

  CHANNELS  each from the world's own physics (worlds.py, interior.py), 0 .. 1:
              magmatic       melting and re-melting its mantle: 1 - exp(-processed) (how many times its heat could
                             have melted its mantle)
              hydrothermal   liquid driven through hot rock: a liquid solvent anywhere on or in it (under ice too) x
                             1 - exp(-q / q_unit), q its surface heat flow
              placer         flowing liquid at its surface sorting by density: surface liquid x the same heat term
                             (the relief that tectonics raises for rivers to wear)
              biological     living chemistry changing what dissolves and what settles (redox): life on it
  AFFINITY  which flows gather an element is its chemistry (Goldschmidt's classes, read from its bonds; an element
            whose oxides are all gases leaves the rock as air): lithophile
            (its oxide holds its oxygen harder than iron's: magmatic, placer), chalcophile (it takes sulphur over
            oxygen: hydrothermal, biological), siderophile (it holds neither: hydrothermal, placer, biological - and
            most of it sank with the iron), atmophile (a gas at a world's warmth: no rock flow gathers it; its
            reservoir is the air and the ice).
  CRUST     melting carries what does not fit mantle crystals up into a crust, by its measured partition
            coefficient D (batch melting: 1 / (D + F (1 - D)), F the share the world melts where it melts) - uranium
            and thorium rise tens of times; nickel stays below.
  GRADE     the flows close part of the log-distance from dispersed to pure: grade = x^(1 - k/2), k = 1 - prod(1 - k_c)
            over the element's channels. With every channel running, a deposit reaches x^(1/2): measured ore grades
            follow about that across ten decades of abundance (iron at ~50% from 5% in rock, copper at ~0.6% from
            27 ppm, uranium at ~0.2% from 1 ppm). A world with no flows holds only its dispersed x.
  RENEWAL   a taken deposit is rebuilt toward its standing grade at the pace of its flows - the replenishment a
            world gives (geology.py), and none where the flows have stopped.
"""

import functools
import math
from typing import Any, Dict, List, Optional

GRADE_REACH = 0.5               # share of the log-distance to purity a world's saturated flows close (measured ore
                                # grades against crustal abundance; see above)
FEO_PER_O = -272.0              # kJ/mol: iron's oxide, the line between lithophile and the rest (Goldschmidt)

# bulk partition coefficients between mantle rock and its melt (measured; Workman & Hart 2005 and compilations):
# below 1 an element prefers the melt and rises into a crust; above 1 it stays in the mantle
PARTITION_D = {"U": 0.0014, "Th": 0.001, "K": 0.0018, "Ba": 0.0003, "Ra": 0.0003, "Pb": 0.014, "Ti": 0.04,
               "Na": 0.03, "Ca": 0.3, "Al": 0.1, "Si": 0.9, "Fe": 1.0, "Mg": 3.0, "Cr": 3.0, "Ni": 10.0}
MIN_MELT = 0.01                 # a melt cannot leave its rock below ~1% porosity (melt connectivity)

_CLASS_CHANNELS = {"lithophile": ("magmatic", "placer"), "chalcophile": ("hydrothermal", "biological"),
                   "siderophile": ("hydrothermal", "placer", "biological"), "atmophile": ()}


# ---------------------------------------------------------------------- affinity
@functools.lru_cache(maxsize=None)
def affinity(sym: str) -> str:
    """An element's (or a compound's) Goldschmidt class, read from its bonds."""
    from xylarium.kernel import substances as S
    if sym in S.COMPOUNDS:
        origin = S.COMPOUNDS[sym].get("origin")
        return {"ice": "atmophile", "mineral": "lithophile", "deep": "lithophile", "core": "siderophile",
                "biogenic": "biogenic", "photochemical": "atmophile", "stellar": "atmophile"}.get(origin, "lithophile")
    e = S.element(sym)
    if e is None:
        return "lithophile"
    base = S.SUPERHEAVY[sym][2] if sym in S.SUPERHEAVY else sym.split("-")[0]
    eb = S.element(base) or e
    if eb["group"] == 18 or (eb["boil"] < 300 and base != "O"):
        return "atmophile"
    if base == "Fe":
        return "siderophile"
    per_o = None
    sulphide = False
    oxides_gas = []
    for c in S.COMPOUNDS.values():
        f = c["f"]
        if set(f) == {base, "O"}:
            v = c["dH"] / f["O"]
            per_o = v if per_o is None else min(per_o, v)
            oxides_gas.append(c["boil"] < 300)
        if set(f) == {base, "S"}:
            sulphide = True
    if oxides_gas and all(oxides_gas):
        return "atmophile"                                # its oxides are gases: it leaves the rock as air
    if per_o is not None:
        if per_o < FEO_PER_O:
            return "lithophile"
        return "chalcophile" if sulphide else "siderophile"
    chi = eb.get("chi")
    if chi is not None and chi < 1.7:
        return "lithophile"                               # gives its electrons to oxygen readily
    return "chalcophile" if 11 <= eb["group"] <= 16 else "siderophile"


# ---------------------------------------------------------------------- channels
@functools.lru_cache(maxsize=1)
def _q_unit() -> float:
    from xylarium.kernel import hydromagnetics
    return float(hydromagnetics._unit().get("q") or 0.02)


def channels(w: Dict[str, Any], media: Optional[List[Dict[str, Any]]] = None, living: bool = False) -> Dict[str, float]:
    """A world's concentrating flows, each 0 .. 1, from its own physics."""
    heat = 1.0 - math.exp(-max(0.0, float(w.get("q") or 0.0)) / _q_unit())
    media = media or []
    liquid_any = bool(w.get("seas")) or any(m.get("solvent") not in ("melt", "plasma") for m in media)
    liquid_surface = bool(w.get("seas")) or any(m.get("where") == "surface" and m.get("solvent") not in
                                                 ("melt", "plasma") for m in media)
    return {"magmatic": 1.0 - math.exp(-max(0.0, float(w.get("processed") or 0.0))),
            "hydrothermal": heat if liquid_any else 0.0,
            "placer": heat if liquid_surface else 0.0,
            "biological": 1.0 if living else 0.0}


def strength(sym: str, ch: Dict[str, float]) -> float:
    """How strongly a world's flows gather an element: 1 - prod(1 - k_c) over its class's channels."""
    cls = affinity(sym)
    if cls == "biogenic":
        return ch.get("biological", 0.0)
    keep = 1.0
    for c in _CLASS_CHANNELS.get(cls, ()):
        keep *= 1.0 - ch.get(c, 0.0)
    return 1.0 - keep


def grade(x: float, k: float) -> float:
    """The standing grade of a deposit: the flows close a share of the log-distance from dispersed to pure."""
    x = min(1.0, max(x, 1e-300))
    return x ** (1.0 - GRADE_REACH * max(0.0, min(1.0, k)))


# ---------------------------------------------------------------------- the host each is dispersed in
@functools.lru_cache(maxsize=None)
def _hosts() -> Dict[str, float]:
    from xylarium.kernel import substances as S
    ab = lambda k: S.element(k)["abund"]
    rock = sum(S.molar_mass(k) * ab(k) for k in ("O", "Mg", "Si", "Fe", "Ni", "S", "Al", "Ca", "Na"))
    from xylarium.kernel import worlds
    ices = sum(worlds.ICE_PER_ROCK.values()) * rock
    return {"rock": rock, "ice": ices}


def dispersed(sym: str) -> float:
    """The mass fraction x of a good in the host it is laid down in, at the galaxy's abundances."""
    from xylarium.kernel import substances as S
    h = _hosts()
    cls = affinity(sym)
    host = h["ice"] if cls == "atmophile" else h["rock"]
    m = S.molar_mass(sym) or 30.0
    if cls == "biogenic":
        return 1.0                                        # what life makes, it makes whole
    return min(1.0, m * S.abundance(sym) / max(1e-300, host))


def melt_fraction(w: Dict[str, Any]) -> float:
    """How much of its mantle a world melts where it melts: its mantle's temperature between rock's solidus and
    liquidus (worlds.MELT_K, interior.LIQUIDUS_K), never below the share a melt needs to leave its rock."""
    from xylarium.kernel import interior, worlds
    t = float(w.get("t_int") or 0.0)
    f = (t - worlds.MELT_K) / max(1.0, interior.LIQUIDUS_K - worlds.MELT_K)
    return max(MIN_MELT, min(1.0, f))


def crustal(sym: str, w: Dict[str, Any], ch: Dict[str, float]) -> float:
    """A good's fraction in a world's crust: its dispersed share, carried up into the crust by melting as far as it
    prefers the melt (batch melting: 1 / (D + F (1 - D))) and as far as the world has melted (its magmatic flow)."""
    x = dispersed(sym)
    if affinity(sym) != "lithophile":
        return x
    from xylarium.kernel import substances as S
    base = S.SUPERHEAVY[sym][2] if sym in S.SUPERHEAVY else sym
    d = PARTITION_D.get(base)
    if d is None:
        return x
    f = melt_fraction(w)
    rise = 1.0 / (d + f * (1.0 - d))
    return min(1.0, x * (1.0 + ch.get("magmatic", 0.0) * (rise - 1.0)))


def of_planet(kernel: Any, planet: Any) -> Dict[str, float]:
    """A world's concentrating flows now."""
    from xylarium.kernel import worlds
    st = worlds.state_of_planet(kernel, planet)
    living = getattr(planet, "population", 0) > 0 or bool(getattr(planet, "natives", None))
    return channels(st["world"], st.get("media"), living)
