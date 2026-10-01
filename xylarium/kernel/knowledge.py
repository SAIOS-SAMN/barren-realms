"""
Xylarium knowledge: what a people knows, how it learns, and what that lets it do. There is no tech tree.

Knowledge is a stock per people (a civilization, a captain's colonies, a faction) in four domains - energy,
materials, biology, information - measured in knowledge units (a thousand minds' year of free thought at Earth's
temperature). Each quarter a world adds to its people's stocks:

    effort = thousands of people x free labour x leisure x depth of mind
      free labour   1 - 1/self-sufficiency: the share of hands its harvest no longer needs (none while it is short)
      leisure       1 + luxury access: provided-for households think
      depth         laws.cognition: Landauer and kinetics at the people's substrate temperature

and directs it where its people's own troubles are - hunger and failing births to biology, a dying crust or empty
ore silo to materials, a degraded grid to energy, trade to information - over a floor of curiosity, plus any focus
its rulers set. Dogma can freeze it; the Imperium permits half. Every stock depreciates 15% a year (R&D capital).

A capability is a process (config PROCESSES) whose cost falls along Wright's learning curve as the people's
knowledge in its domain grows: mastery = 1 - (1 + K / KNOWLEDGE_UNIT)^-b, b = -log2(0.8). Nothing unlocks; a jump
drive, an artificial womb or a sanitation works is available at any knowledge and becomes worth having as its
mastery rises - species and polities come to know different things because they need and value different things.
"""

from typing import Any, Dict, List, Optional

from xylarium.config import KNOWLEDGE_UNIT, PROCESSES
from xylarium.kernel import laws

DOMAINS = ("energy", "materials", "biology", "information")
CURIOSITY = 0.25                 # the floor of undirected inquiry, as a share of one domain's pull


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "knowledge")


def holder_of_planet(planet: Any) -> Optional[str]:
    from xylarium.kernel import sustenance
    return sustenance.people_of(planet)


def holder_of_captain(captain: Any) -> str:
    return f"captain:{captain.id}"


def stocks(kernel: Any, holder: Optional[str]) -> Dict[str, float]:
    if not holder:
        return {d: 0.0 for d in DOMAINS}
    st = stats(kernel)["stocks"]
    return st.setdefault(holder, {d: 0.0 for d in DOMAINS})


def experience(kernel: Any, holder: Optional[str], domain: str) -> float:
    """What a people's knowledge is worth in practice: its stock, carried further by its fluid intelligence
    (intellect.py) - a mind that solves harder problems learns more from the same experience."""
    from xylarium.kernel import intellect
    return stocks(kernel, holder).get(domain, 0.0) * (1.0 + intellect.fluid(kernel, holder))


def mastery(kernel: Any, holder: Optional[str], process: str) -> float:
    """How far this people has learned a process, 0 .. 1."""
    return laws.mastery(experience(kernel, holder, PROCESSES[process]["domain"]), KNOWLEDGE_UNIT)


def cost_multiplier(kernel: Any, holder: Optional[str], process: str) -> float:
    return laws.wright(experience(kernel, holder, PROCESSES[process]["domain"]), KNOWLEDGE_UNIT)


def captain_mastery(kernel: Any, captain: Any, process: str) -> float:
    return mastery(kernel, holder_of_captain(captain), process)


def learn(kernel: Any, holder: Optional[str], domain: str, units: float, why: str = "research") -> None:
    if not holder or units <= 0 or domain not in DOMAINS:
        return
    s = stocks(kernel, holder)
    s[domain] = s.get(domain, 0.0) + units
    made = stats(kernel)["made"]
    made[why] = round(made.get(why, 0.0) + units, 3)


def focus(kernel: Any, holder: str, domain: Optional[str]) -> None:
    """A ruler's direction of inquiry (players and AI owners): the domain gets a full share of pull more."""
    f = stats(kernel)["focus"]
    if domain in DOMAINS:
        f[holder] = domain
    else:
        f.pop(holder, None)


def discovery_domain(process: Optional[str]) -> str:
    """The domain a relic's or anomaly's reward speaks to (its old tech name or process), else information."""
    from xylarium.config import LEGACY_TECH_PROCESS
    proc = LEGACY_TECH_PROCESS.get(process or "", process)
    return PROCESSES.get(proc or "", {}).get("domain", "information")


# ---------------------------------------------------------------------- where a people's mind goes
def pulls(kernel: Any, planet: Any) -> Dict[str, float]:
    """What this world's troubles ask of its thinkers."""
    soc = planet.society
    ss = float(soc.get("self_sufficiency", 1.0) or 1.0)
    fp = soc.get("fertility_parts") or {}
    bio = max(0.0, 1.0 - ss) + max(0.0, 1.0 - float(fp.get("unstressed", 1.0) or 1.0))
    if fp.get("strategy") == "r":
        from xylarium.kernel import nursery
        bio += max(0.0, nursery.r0(kernel, planet) - 1.0)
    crust = (planet.element_deposits or {}).get("ORE")
    materials = max(0.0, 1.0 - planet.ore_silo / 600.0)
    if crust is not None:
        from xylarium.kernel import geology
        cap = geology.crust_capacity(planet)
        materials += max(0.0, 1.0 - crust / cap) if cap else 0.0       # a mined-out crust
    energy = (1.0 - float(soc.get("readiness", 1.0) or 1.0)) + (1.0 if soc.get("degraded") else 0.0)
    information = min(1.0, float(soc.get("lux_access", 0.0) or 0.0))         # a trading, provided-for people
    return {"energy": energy, "materials": materials, "biology": bio, "information": information}


def effort(kernel: Any, planet: Any) -> float:
    """Knowledge units this world thinks up in a year."""
    from xylarium.config import ZEALOT_RD_FREEZE_DOGMA
    from xylarium.kernel import biosphere
    soc = planet.society
    ss = float(soc.get("self_sufficiency", 1.0) or 1.0)
    free = max(0.0, 1.0 - 1.0 / ss) if ss > 0 else 0.0
    leisure = 1.0 + laws.clamp(float(soc.get("lux_access", 0.0) or 0.0))
    depth = laws.cognition(biosphere.metabolism_of(kernel, planet))["depth"]
    e = planet.population / 1000.0 * free * leisure * depth
    civ = getattr(planet, "civilization", None)
    faction = getattr(planet, "faction_id", None) or (getattr(civ, "faction_id", None) if civ is not None else None)
    if civ is not None and float(getattr(civ, "dogma", 0.0) or 0.0) > ZEALOT_RD_FREEZE_DOGMA:
        return 0.0                          # inquiry branded heresy
    if faction == "IMPERIUM":
        e *= 0.5                            # only the sanctioned sciences of the ancient rites
    return e


def quarter(kernel: Any) -> List[str]:
    st = stats(kernel)
    years = _quarter() / 100.0
    before = {h: sum(s.values()) for h, s in st["stocks"].items()}
    for holder, s in st["stocks"].items():          # forgetting first: knowledge unused decays
        for d in DOMAINS:
            s[d] = round(laws.depreciate(s.get(d, 0.0), years), 4)
    for sec in kernel.sectors.values():
        for planet in sec.planets:
            if planet.population <= 0 or getattr(planet, "natives", None):
                continue
            holder = holder_of_planet(planet)
            if not holder:
                continue
            units = effort(kernel, planet) * years
            if units <= 0:
                continue
            pull = pulls(kernel, planet)
            chosen = st["focus"].get(holder)
            weights = {d: CURIOSITY + pull[d] + (1.0 if d == chosen else 0.0) for d in DOMAINS}
            total = sum(weights.values())
            for d, w in weights.items():
                learn(kernel, holder, d, units * w / total)
    # each people's annual knowledge growth rate (read by fertility.meaning as progress)
    import math
    growth = st.setdefault("growth", {})
    for holder, s in st["stocks"].items():
        t0, t1 = before.get(holder, 0.0), sum(s.values())
        growth[holder] = round(math.log((t1 + KNOWLEDGE_UNIT) / (t0 + KNOWLEDGE_UNIT)) / years, 5)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    by: Dict[str, Dict[str, float]] = {}
    for holder, s in st["stocks"].items():
        kind = holder.partition(":")[0]
        b = by.setdefault(kind, {d: 0.0 for d in DOMAINS})
        for d in DOMAINS:
            b[d] = max(b[d], s.get(d, 0.0))
    leaders = {d: max(st["stocks"].items(), key=lambda kv: kv[1].get(d, 0.0))[0] if st["stocks"] else None
               for d in DOMAINS}
    return {"holders": len(st["stocks"]), "max_by_kind": {k: {d: round(v, 1) for d, v in b.items()}
                                                          for k, b in by.items()},
            "leaders": leaders, "made": dict(st["made"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="knowledge",
    state=lambda: {"stocks": {}, "focus": {}, "made": {}},
    season=quarter,
    summary=summary,
))
