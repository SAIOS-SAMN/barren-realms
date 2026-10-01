"""
Xylarium chemistry: one periodic table for the whole universe, what each world came to hold of it, and how a
people digs its way into it.

THE UNIVERSAL TABLE (TABLE). Every element carries the physics that decides where it ends up: nucleon mass A, density,
condensation temperature (the temperature below which it is solid in a forming system), cosmic abundance (atoms
per million of silicon), its period (LINE: how deep it lies - how much a people must understand to reach it) and
its group (LANE: its bonding character, which repeats down a group). Real elements carry measured values (Lodders
2003 condensation temperatures, solar abundances); the exotics of the Netstratum almanac carry values read from
their own five axes (period, group, phase), so they obey the same gates.

WHAT A WORLD HOLDS is not chosen; it is what survives four gates of its own formation, in order (each can only
remove), and why an element is missing is remembered:

    ladder         its star's lineage reaches only so deep into the table: an M dwarf's nebula was enriched to
                   period 3, a G star's to 5, a heavy star's or a stellar remnant's to all of them  -> never_made
    retention      it stays only if the world can hold it: escape energy x nucleon mass against formation
                   temperature (Jeans: a heavy cold world keeps hydrogen; a small hot one loses its water)  -> escaped
    condensation   it was solid where the world formed (formation temperature below its condensation point),
                   or the world is a giant holding it as gas                                                  -> too_hot
    differentiation  what is denser than the world sinks toward its core in proportion to how far the world
                   melted (its heat); what sinks entirely is out of reach                                        -> sunk

Then its regional richness: a weight per stretch of the galaxy and chemistry family, so neighbouring systems share
what their region is rich in, the galaxy as a whole is even, and no world holds everything.

DISCOVERY IS DIGGING. A people knows an element only once it has found it: in its own worlds' ground (the homeworld
is the first denominator), its reserves, its holds, what it trades for. Each quarter, for each element it has
encountered but not understood, the chance of understanding it is its thought (knowledge.effort, impeded by its
society) x how far its materials knowledge reaches at that depth (the learning curve, scaled by the period) x the
pull of what it already knows of that group (extrapolating down a group). Deep elements are buried treasure: some
peoples never dig that far.

CHEMISTRY follows: a recipe is open to a people only when it knows every element it takes, and its minds can hold
a composition of that many parts (its fluid intelligence: planar rung -> parts it can compose).
"""

import math
import random
import zlib
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import laws, matter

# symbol: (name, A, density g/cc, condensation K, abundance per 1e6 Si, period, group, family)
_REAL = {
    "H": ("Hydrogen", 1, 0.09, 5, 2.8e10, 1, 1, "volatile"),
    "He-3": ("Helium-3", 3, 0.12, 3, 4.5e5, 1, 18, "noble"),
    "C": ("Carbon", 12, 2.26, 40, 1.0e7, 2, 14, "volatile"),
    "H2O": ("Water", 18, 1.0, 182, 1.4e7, 2, 16, "ice"),
    "Si": ("Silicon", 28, 2.33, 1310, 1.0e6, 3, 14, "metal"),
    "Ti": ("Titanium", 48, 4.5, 1582, 2.4e3, 4, 4, "metal"),
    "Fe": ("Iron", 56, 7.87, 1334, 8.4e5, 4, 8, "metal"),
    "Ni": ("Nickel", 59, 8.9, 1353, 4.8e4, 4, 10, "metal"),
    "Cu": ("Copper", 64, 8.96, 1037, 5.3e2, 4, 11, "metal"),
    "Xe": ("Xenon", 131, 3.6, 69, 4.7, 5, 18, "noble"),
    "Pt": ("Platinum", 195, 21.4, 1408, 1.4, 6, 10, "metal"),
    "U": ("Uranium", 238, 19.1, 1610, 0.009, 7, 3, "fissile"),
}
_PHASE_TC = {1: 40, 2: 400, 3: 1200, 4: 1700}       # the almanac's phase axis as a condensation point


def _exotic(line: int, lane: int, phase: int) -> Tuple[int, float, float, float]:
    """An exotic's physics from its almanac axes: heavier and denser down the table, rarer the deeper."""
    return 30 * line, 2.0 + 2.0 * line, _PHASE_TC.get(phase, 400), 10.0 ** (4 - line)


def _build() -> Dict[str, Dict[str, Any]]:
    from xylarium.kernel.elements import CANONICAL_ELEMENTS
    table = {}
    for sym, (name, a, rho, tc, ab, line, lane, fam) in _REAL.items():
        table[sym] = {"name": name, "A": a, "rho": rho, "tc": tc, "abund": ab, "line": line, "lane": lane,
                      "family": fam}
    for eid, e in CANONICAL_ELEMENTS.items():
        a, rho, tc, ab = _exotic(e.line, e.lane, e.phase)
        table[eid] = {"name": e.name, "A": a, "rho": rho, "tc": tc, "abund": ab, "line": e.line, "lane": e.lane,
                      "family": "exotic"}
    for eid, (line, lane, phase) in {"AdL": (6, 6, 4), "SpR": (7, 9, 4)}.items():   # the deepest lodes
        a, rho, tc, ab = _exotic(line, lane, phase)
        table[eid] = {"name": eid, "A": a, "rho": rho, "tc": tc, "abund": ab, "line": line, "lane": lane,
                      "family": "exotic"}
    return table


TABLE = _build()
RETENTION = 6.0                 # escape energy x A / T (Earth = 1, 1, 1) a world needs to keep an element:
                                # Earth keeps water (A 18) and loses helium (A 3) and hydrogen (A 1)
DEPOSIT_UNIT = 20               # units per decade of cosmic abundance, per Earth crust
REGIONAL = [1 / 2, 2 / 3, 3 / 4, 7 / 8, 1, 9 / 8, 5 / 4, 3 / 2]
FOUND = 1                       # periods every people knows from its first fire and first tool (line <= FOUND)


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "chemistry")


# ---------------------------------------------------------------------- the gates
def ladder(sector: Any) -> int:
    """How deep into the table a system's nebula was enriched: by its star's lineage."""
    label = (getattr(sector, "star_type", None) or "G-class").lower()
    if "brown dwarf" in label:
        return 3                                           # a failed star made nothing deep
    if any(w in label for w in ("white dwarf", "precursor", "neutron", "remnant", "pulsar")):
        return 7                                           # a dead star's lineage seeded everything
    from xylarium.kernel import physics
    m = float(physics.star(sector)["mass"])
    return 3 if m < 0.5 else 4 if m < 0.9 else 5 if m < 1.4 else 6 if m < 2.5 else 7


def region_weight(sector: Any, family: str) -> float:
    cell = getattr(sector, "id", 0) // 8
    return REGIONAL[zlib.crc32(f"{cell}:{family}".encode()) % len(REGIONAL)]


def inventory(kernel: Any, sector: Any, planet: Any) -> Tuple[Dict[str, int], Dict[str, str]]:
    """What a world holds of the universal table, and why it lacks what it lacks."""
    from xylarium.kernel import geology, physics
    b = physics.body(planet)
    mass = float(b.get("mass", 1))
    radius = float(b.get("radius", 1)) or 1.0
    giant = bool(b.get("giant")) or planet.planet_type == "GAS_GIANT"
    t_form = laws.stefan_boltzmann_temperature(float(physics.planet_flux(sector, planet)))
    t_rel = t_form / laws.T_EARTH
    esc = float(physics.escape_energy(planet)) or 1e-6
    rho_p = 5.51 * mass / (radius ** 3)
    melt = min(1.0, geology.heat(planet))                # how far the world differentiated
    depth = ladder(sector)
    held: Dict[str, int] = {}
    why: Dict[str, str] = {}
    for sym, e in TABLE.items():
        if e["line"] > depth:
            why[sym] = "never_made"
            continue
        if not giant and esc * e["A"] / t_rel < RETENTION:
            why[sym] = "escaped"
            continue
        if not (t_form <= e["tc"] or giant):
            why[sym] = "too_hot"
            continue
        if giant and e["rho"] > 1.5:
            why[sym] = "sunk"                              # a giant's heavy elements are in its core, beyond reach
            continue
        excess = max(0.0, e["rho"] / rho_p - 1.0)
        reach = 1.0 - melt * excess / (1.0 + excess)
        if reach < 0.05:
            why[sym] = "sunk"
            continue
        size = math.sqrt(min(mass, 400.0))                 # a crust's reach grows with the world, not its whole mass
        units = DEPOSIT_UNIT * max(0.0, math.log10(e["abund"]) + 3) * size * reach * region_weight(sector, e["family"])
        held[sym] = max(5, int(units))                     # where it survives, a trace is always there to find
    return held, why


def survey(kernel: Any) -> None:
    """Every world not yet surveyed has its holdings read from the table and its own formation; a re-survey of an
    older universe declares what changed."""
    st = stats(kernel)
    for sec in kernel.sectors.values():
        if getattr(sec, "kind", "SYSTEM") != "SYSTEM":
            continue
        for p in sec.planets:
            if p.society.get("chem_surveyed") or not getattr(p, "body", None):
                continue
            held, why = inventory(kernel, sec, p)
            for sym in set(held) | {s for s in p.element_deposits if s in TABLE}:
                old, new = p.element_deposits.get(sym, 0), held.get(sym, 0)
                if new > old:
                    matter.source("planetary_survey", sym, new - old)
                elif old > new:
                    matter.sink("planetary_survey", sym, old - new)
                if new:
                    p.element_deposits[sym] = new
                else:
                    p.element_deposits.pop(sym, None)
            p.society["chem_surveyed"] = True
            p.society["withheld"] = why
            st["surveyed"] += 1


# ---------------------------------------------------------------------- discovery
def known(kernel: Any, holder: Optional[str]) -> List[str]:
    if not holder:
        return []
    st = stats(kernel)
    if holder not in st["known"]:
        seed = {s for s, e in TABLE.items() if e["line"] <= FOUND}
        if holder.startswith("civ:"):
            for sec in kernel.sectors.values():
                for p in sec.planets:
                    civ = getattr(p, "civilization", None)
                    if civ is not None and f"civ:{civ.name}" == holder:
                        seed |= set(getattr(civ, "discovered_elements", []) or [])
        st["known"][holder] = sorted(s for s in seed if s in TABLE)
    return st["known"][holder]


def knows(kernel: Any, holder: Optional[str], sym: str) -> bool:
    return sym not in TABLE or sym in known(kernel, holder)


def _encountered(kernel: Any, holder: str, worlds: List[Any]) -> set:
    out = set()
    for p in worlds:
        out |= {s for s, n in p.element_deposits.items() if n > 0 and s in TABLE}
        out |= {s for s, n in p.element_reserves.items() if n > 0 and s in TABLE}
    if holder.startswith("captain:"):
        cap = kernel.captains.get(holder.partition(":")[2])
        if cap is not None:
            out |= {s for s, n in cap.ship.cargo.elements.items() if n > 0 and s in TABLE}
    return out


def _discover(kernel: Any, holder: str, worlds: List[Any], effort_q: float) -> List[str]:
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge
    st = stats(kernel)
    have = set(known(kernel, holder))
    rng = random.Random(zlib.crc32(f"chem:{holder}:{kernel.cycle_count}".encode()))
    thought = 1.0 - math.exp(-effort_q)
    exp = knowledge.experience(kernel, holder, "materials")
    found = []
    for sym in sorted(_encountered(kernel, holder, worlds) - have):
        e = TABLE[sym]
        reach = laws.mastery(exp, KNOWLEDGE_UNIT * e["line"])            # deeper periods need far more
        kin = sum(1 for s in have if TABLE[s]["lane"] == e["lane"])      # what it knows of the group
        if rng.random() < min(1.0, thought * reach * (1 + kin)):
            found.append(sym)
            have.add(sym)
    if found:
        st["known"][holder] = sorted(have)
        st["discoveries"] += len(found)
        for p in worlds:
            civ = getattr(p, "civilization", None)
            if civ is not None and p.owner_id is None:
                for sym in found:
                    if sym not in civ.discovered_elements:
                        civ.discovered_elements.append(sym)
        knowledge.learn(kernel, holder, "materials", sum(TABLE[s]["line"] for s in found) / 2.0, "discovery")
    return found


# ---------------------------------------------------------------------- chemistry
def max_parts(kernel: Any, holder: Optional[str]) -> int:
    """How many distinct parts a people's minds can compose: two by instinct, one more for each three planar
    rungs it has climbed."""
    from xylarium.kernel import intellect
    g = intellect.gauge(kernel, holder) if holder else {}
    return 2 + int(g.get("2", 0)) // 3


def can_make(kernel: Any, holder: Optional[str], product: str) -> bool:
    from xylarium.config import COMMODITY_CONFIG
    recipe = (COMMODITY_CONFIG.get(product) or {}).get("recipe") or {}
    if not recipe:
        return True
    if len(recipe) > max_parts(kernel, holder):
        return False
    return all(knows(kernel, holder, s) for s in recipe)


def missing_for(kernel: Any, holder: Optional[str], inputs: Dict[str, int]) -> List[str]:
    return [s for s in inputs if not knows(kernel, holder, s)]


# ---------------------------------------------------------------------- the quarter
def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import intellect
    survey(kernel)
    logs = []
    for holder, rec in intellect._peoples(kernel).items():
        found = _discover(kernel, holder, rec["worlds"], rec["effort"])
        if found and getattr(kernel, "event_bus", None) and any(TABLE[s]["line"] >= 5 for s in found):
            deep = ", ".join(TABLE[s]["name"] for s in found if TABLE[s]["line"] >= 5)
            logs.append(f"[CHEMISTRY] {holder.partition(':')[2]} has dug deep enough to understand {deep}.")
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    sizes = [len(v) for v in st["known"].values()]
    deepest = {}
    for h, v in st["known"].items():
        deepest[h] = max((TABLE[s]["line"] for s in v if s in TABLE), default=0)
    by_depth: Dict[int, int] = {}
    for d in deepest.values():
        by_depth[d] = by_depth.get(d, 0) + 1
    return {"surveyed": st["surveyed"], "discoveries": st["discoveries"],
            "known_mean": round(sum(sizes) / len(sizes), 2) if sizes else 0, "peoples_by_deepest_period": by_depth}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="chemistry",
    state=lambda: {"known": {}, "surveyed": 0, "discoveries": 0},
    season=quarter,
    genesis=survey,
    summary=summary,
))
