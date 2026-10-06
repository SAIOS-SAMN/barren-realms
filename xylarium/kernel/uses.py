"""
Xylarium uses: what a good is to a people - read from the people's own body and world, never declared for it.

A good is only matter: an element or a compound, with its phase at a temperature and pressure. What it is FOR
depends on who meets it. The same water is the air and blood of a people whose chemistry runs in it, the rock of a
people whose bodies are colder than its freezing point, and a vapour to a people whose bodies are hotter than it
boils. Nothing here names a people's needs; the physics of its body and its world decides them.

  BODY       a minded people's chemistry runs in a solvent and keeps its body at that solvent's best (worlds.
             body_temperature: the middle of its liquid range) - recorded when its mind arose (cosmos.select), or
             read from a world of its own whose media fit its chemistry, or from the region its chemistry names
             (worlds.region, inverted) where a single solvent falls in it - with nothing known of its world's air,
             among those liquid at one bar (an assumption, said here, for peoples placed without a world of their
             chemistry; cryogenic peoples stay unread, their candidates all being liquid at one bar).
  MEDIUM     the matter its chemistry runs in. The good that holds it is the one creation lays that matter down as
             (creation._composition): water ice as H2O, the nitrogen ices (ammonia, nitrogen) as cryogenite, a
             world's rock as ORE, a giant's hydrogen as H. (The carbon ices are laid down with solid carbon, and no
             good holds them as a liquid yet: a people born in methane takes its medium from its own world.) A people that houses its kind away from its world - homes, domes, ships - holds its
             medium there: its households want it and its domes are filled with it.
  STRUCTURE  what can hold a shape where it stands: matter solid at the temperature it stands at (a building on a
             world, at the world's surface; a hull holding its people, at their body temperature). Metals and rock
             are solid nearly everywhere a body can live; water ice is rock to a body colder than ice melts; a
             people whose solvent is molten rock builds with what stays solid in its furnace. Which of the solids a
             people builds with is what is cheapest to it - its own world's and its port's - not a recipe.

Melting points are measured data (1 bar), as the element abundances are; an element without one holds a shape below
its solid point in the universal table (chemistry.TABLE - its condensation temperature; the exotics' read from their
almanac phase). A people builds only with what its world holds and what it has come to understand (chemistry.known):
an element is dug, then understood, then built with.
"""

from typing import Any, Dict, List, Optional, Tuple

# measured melting points at 1 bar (K): the data of each real substance a good is made of
MELT_K = {"Fe": 1811.0, "Ti": 1941.0, "Ni": 1728.0, "Cu": 1358.0, "Si": 1687.0, "Pt": 2041.0, "U": 1405.0,
          "C": 3915.0, "NaCl": 1074.0, "Xe": 161.4, "H": 14.0, "He-3": 0.3}
# the volatile each volatile good is made of (worlds.VOLATILES carries its phase curve)
VOLATILE_OF = {"H2O": "H2O", "cryogenite": "NH3"}
# the good each solvent's matter is laid down as (creation._composition). The carbon ices (methane, carbon monoxide
# and dioxide) are laid down with carbon in the solid C good: no good holds them as liquids yet, so a people whose
# chemistry runs in them keeps its medium from its own world until there is one
MEDIUM_GOOD = {"H2O": "H2O", "NH3": "cryogenite", "N2": "cryogenite", "melt": "ORE", "plasma": "H"}
# ORE is a world's silicate rock: the mantle its magnesium, silicon and oxygen condense into (worlds.SOLIDS - MgSiO3
# as the abundances give it), melting where rock melts (worlds.MELT_K). Every people knows the rock it stands on.
ROCK = "ORE"


def _region_solvents(metab: str) -> List[str]:
    """The solvents whose chemistry, held at its own best temperature, falls in a metabolism's region of chemistry
    space - the inverse of worlds.region, read from it rather than written beside it."""
    from xylarium.kernel import worlds
    out = []
    for solvent in list(worlds.VOLATILES) + ["melt", "plasma"]:
        t = worlds.body_temperature(solvent)
        for where, dark in (("surface", False), ("under_ice", True), ("deep", True)):
            m = {"solvent": solvent, "where": where, "t": t, "dark": dark}
            if worlds.region(m) == metab and solvent not in out:
                out.append(solvent)
    return out


def body(kernel: Any, planet: Any) -> Optional[Dict[str, Any]]:
    """A world's people's chemistry: its solvent and the temperature its bodies keep - None where it cannot be read.
    Read from what was recorded when its mind arose; else from a world of its own whose media fit its chemistry (its
    homeworld is one); else from the region its chemistry names, where only one solvent falls in it."""
    from xylarium.kernel import biosphere, relations, sustenance, worlds
    civ = getattr(planet, "civilization", None)
    traits = getattr(civ, "traits", None) or {}
    if traits.get("solvent") and traits.get("body_t"):
        return {"solvent": traits["solvent"], "t": float(traits["body_t"])}
    if planet is None or getattr(planet, "population", 0) <= 0:
        return None
    metab = biosphere.metabolism_of(kernel, planet)
    people = sustenance.people_of(planet)
    own = [planet] + [w for w in (relations._peoples(kernel).get(people) or []) if w is not planet] if people else [planet]
    for w in own:
        try:
            med = worlds.best(worlds.of_planet(kernel, w), metab)
        except Exception:
            med = None
        if med:
            return {"solvent": med["solvent"], "t": float(worlds.body_temperature(med["solvent"]))}
    only = _region_solvents(metab)
    if len(only) > 1:                 # nothing known of its world's pressure: those liquid without needing pressure
        only = [x for x in only if x in ("melt", "plasma")
                or worlds.phase(x, worlds.body_temperature(x), 1.0) == "liquid"]
    if len(only) == 1:
        return {"solvent": only[0], "t": float(worlds.body_temperature(only[0]))}
    return None


def medium(kernel: Any, planet: Any) -> Optional[str]:
    """The good that holds a people's medium, or None where no good does (or no people lives there)."""
    b = body(kernel, planet)
    return MEDIUM_GOOD.get(b["solvent"]) if b else None


def melt_k(good: str) -> Optional[float]:
    """The temperature a good stops holding its shape at (1 bar), or None where its matter is not known to."""
    from xylarium.kernel import worlds
    if good in VOLATILE_OF:
        return float(worlds.VOLATILES[VOLATILE_OF[good]]["phase"][0])        # its triple point
    if good == "ORE":
        return float(worlds.MELT_K)
    if good in MELT_K:
        return MELT_K[good]
    from xylarium.kernel import chemistry
    e = chemistry.TABLE.get(good)                  # the universal table's own solid point (its condensation)
    return float(e["tc"]) if e is not None else None


def solid_at(good: str, t: float) -> bool:
    m = melt_k(good)
    return m is not None and t < m


def structural(t: float, kernel: Any = None, holder: Optional[str] = None) -> List[str]:
    """The goods that hold a shape at a temperature: matter, not made things (the elements and minerals the galaxy
    laid down, supply.goods, and rock) - and, for a people, only those it has come to understand (chemistry.known:
    an element is dug before it is built with)."""
    from xylarium.kernel import chemistry, supply
    out = [g for g in [ROCK] + supply.goods() if solid_at(g, t)]
    if kernel is not None and holder and "chemistry" in getattr(kernel, "state", {}):
        out = [g for g in out if g == ROCK or chemistry.knows(kernel, holder, g)]
    return out


def holder_of(planet: Any) -> Optional[str]:
    from xylarium.kernel import knowledge
    return knowledge.holder_of_planet(planet)


def _cost(kernel: Any, planet: Any, good: str) -> float:
    """What a unit of a good costs a world: from its own stores nothing but the digging; from its port, the port's
    price (landed where brought in)."""
    from xylarium.kernel.economy import EconomyManager
    port = getattr(kernel.sectors.get(planet.sector_id), "port", None)
    if port is None or not port.sells.get(good):
        return float("inf")
    return float(EconomyManager.get_unit_prices(port, good)[1] or float("inf"))


def build_with(kernel: Any, planet: Any, t: float, units: int) -> List[Tuple[str, int]]:
    """The materials a structure standing at temperature t is built from at a world: the cheapest solids there -
    its own stores first (what it holds most of), then its port's shelves - until `units` are found. Empty where it
    cannot be built."""
    port = getattr(kernel.sectors.get(planet.sector_id), "port", None)
    options = []
    for g in structural(t, kernel, holder_of(planet)):
        own = int((planet.element_reserves or {}).get(g, 0)) + (int(planet.ore_silo or 0) if g == "ORE" else 0)
        shelf = int(port.stock.get(g, 0)) if port is not None else 0
        if own + shelf > 0:
            options.append((0.0 if own else _cost(kernel, planet, g), -(own + shelf), g, own + shelf))
    out: List[Tuple[str, int]] = []
    left = units
    for _, _, g, have in sorted(options):                     # cheapest; among its own, what it holds most of
        if left <= 0:
            break
        take = min(have, left)
        out.append((g, take))
        left -= take
    return out if left <= 0 else []


def summary(kernel: Any) -> Dict[str, Any]:
    """What the peoples are made of: how many keep each medium."""
    out: Dict[str, int] = {}
    if hasattr(kernel, "sectors"):
        for s in kernel.sectors.values():
            for w in s.planets:
                if w.population > 0:
                    b = body(kernel, w)
                    key = b["solvent"] if b else "unknown"
                    out[key] = out.get(key, 0) + 1
    return {"media": out}
