"""
Xylarium rent: the few and the many - what a people's rulers take from its own, and why.

A people without a state has no few: what its hands make, its hands keep (Boehm: bands level their would-be
rulers). A state can hold a surplus, and those who hold it can take a share of the many's product beyond any work of
their own - the RENT (0..1). What they take is chosen once a generation by the few themselves (decide.choose,
through their people's own mind), and bounded by two things only:

  what the many bear   the rent leaves the many only (1 - rent) of their harvest: their self-sufficiency falls by
                       it, and with it their immiseration and their order's legitimacy (society.stress). Past the
                       share that would carry a rising (society.MOBILISED, or the levy that holds them down), the
                       many rise and the few lose everything (society._strife overturns the order: the rent ends).
                       A creed (dogma) legitimises what hunger would not: belief lets the few take more.
  their own horizon    the many think with the hands their harvest frees (knowledge.effort: 1 - 1/self-sufficiency);
                       what the few take, the many do not think with, and the people grows slower. Over a horizon of
                       H years at growth g, the few's take is worth rent x (e^(g H) - 1) / g (Olson 1993: the
                       stationary bandit). A short horizon takes all the many will bear; a long one, in a people that
                       grows, takes about 1 / (g H) - its share of a larger whole is worth more than all of a small one.

So greed is the short horizon: a people's minds choose it, as they choose everything, and nothing in the laws forbids
it - but every life's worth of product it takes is written into its history (alignment.flow: dark), every life's
worth its many keep is written as made (light), and the history is read over the people's whole span.
"""

import math
from typing import Any, Dict, List, Optional

LEVELS = 20                     # rents a council weighs: 0, 1/20 .. 19/20 of the many's product


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "rent")


def of(planet: Any) -> float:
    """The share of the many's product its few take now."""
    soc = getattr(planet, "society", None) or {}
    return float(soc.get("rent", 0.0) or 0.0)


def commons(planet: Any, ss: Optional[float] = None) -> float:
    """The many's self-sufficiency: their harvest against their need, after the few's take."""
    if ss is None:
        ss = float((getattr(planet, "society", None) or {}).get("self_sufficiency", 1.0) or 1.0)
    return ss * (1.0 - of(planet))


def _rising(kernel: Any, planet: Any, ss: float, rho: float) -> float:
    """society.stress's rising, were the few to take `rho`."""
    from xylarium.kernel import biosphere
    ssc = ss * (1.0 - rho)
    crowd = min(1.0, planet.population / max(1, biosphere.carrying_capacity(kernel, planet)))
    mmp = max(0.0, 1.0 - ssc) * crowd
    dogma = float(getattr(planet.civilization, "dogma", 0.0) or 0.0)
    emp = 1.0 - max(dogma, min(1.0, ssc))
    sfd = 1.0 - max(0.0, min(100.0, float(planet.morale))) / 100.0
    return mmp * emp * (0.5 + 0.5 * sfd)


def bearable(kernel: Any, planet: Any, ss: Optional[float] = None) -> float:
    """The most the few can take before the many rise (bisection on society.stress's rising)."""
    from xylarium.kernel import society
    if ss is None:
        ss = float(planet.society.get("self_sufficiency", 1.0) or 1.0)
    line = max(society.gauges(planet)["levy"], society.MOBILISED)
    if _rising(kernel, planet, ss, 0.0) > line:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _rising(kernel, planet, ss, mid) <= line else (lo, mid)
    return lo


def _free(ss: float, rho: float) -> float:
    ssc = ss * (1.0 - rho)
    return max(0.0, 1.0 - 1.0 / ssc) if ssc > 0 else 0.0


def worth(rho: float, g: float, years: float) -> float:
    """What the few gain over `years` taking `rho` of a product growing at `g` a year (in years of today's product)."""
    gh = min(50.0, g * years)
    return rho * (math.expm1(gh) / g if g > 1e-12 else years)


def choose(kernel: Any, planet: Any, ruled: bool = False) -> float:
    """The few weigh what to take, through their people's mind; returns the rent they set. (`ruled`: the annals know
    the people has a state though its world's way is not yet written.)"""
    from xylarium.kernel import decide, knowledge, syntropy, ways
    soc = planet.society
    if (ways.stateless(planet) and not ruled) or planet.civilization is None:
        soc["rent"] = 0.0
        return 0.0
    ss = float(soc.get("self_sufficiency", 1.0) or 1.0)
    now = of(planet)
    holder = knowledge.holder_of_planet(planet)
    g_now = max(0.0, float((syntropy.stats(kernel)["peoples"].get(holder) or {}).get("slope", 0.0) or 0.0))
    free_now = _free(ss, now)
    m = decide.mind_of_planet(kernel, planet)
    years = decide.horizon(m) / 4.0
    cap = bearable(kernel, planet, ss)
    options: List[Dict[str, Any]] = []
    for i in range(LEVELS):
        rho = i / LEVELS
        g = g_now * (_free(ss, rho) / free_now) if free_now > 0 else g_now
        v = worth(rho, g, years)
        # past what the many bear, they rise within the generation: the few lose what they would have taken
        options.append(decide.option("rent", v if rho > cap else 0.0, v, rho=rho))
    got = decide.choose(kernel, options, m, holder, "rent")
    rho = float(got["rho"]) if got is not None else 0.0
    soc["rent"] = round(rho, 4)
    soc["rent_cycle"] = kernel.cycle_count
    stats(kernel)["chosen"] += 1
    return rho


def season(kernel: Any, planet: Any, gens: float, gen_years: float) -> None:
    """Once a generation the few choose again; every season the people's own work is written into its history - what
    the many keep as made, what the few take as taken."""
    from xylarium.kernel import alignment, ways
    soc = planet.society
    if ways.stateless(planet):
        soc["rent"] = 0.0
    elif kernel.cycle_count - int(soc.get("rent_cycle", -10 ** 12)) >= gen_years * 100:
        choose(kernel, planet)
    rho = of(planet)
    n = float(planet.population) * max(0.0, gens)
    alignment.flow(planet.civilization, light=n * (1.0 - rho), dark=n * rho)


def prehistory(kernel: Any, planet: Any) -> None:
    """A people placed into the world already grown (a genesis, a founding, a scenario) brings its past with it: the
    ages it has passed through, each for its measured span (annals.SPANS, in its own generations), its own work all
    the while - and, since it has had a state, what its few take now (`choose`). Its history is written once, so
    that it weighs what a people of its age weighs; it is never drawn."""
    from xylarium.kernel import alignment, annals, knowledge
    civ = getattr(planet, "civilization", None)
    if civ is None or planet.population <= 0:
        return
    stage = annals._stage(kernel, knowledge.holder_of_planet(planet) or "", planet)
    reached = annals.STAGES[1:annals.STAGES.index(stage) + 1]
    lived = sum(annals.SPANS[s] for s in reached)
    ruled = sum(annals.SPANS[s] for s in reached if annals.STAGES.index(s) > annals.STAGES.index("state"))
    rho = choose(kernel, planet, ruled=True) if ruled > 0 else 0.0
    n = float(planet.population)
    for key in ("light", "dark", "told_light", "told_dark"):
        setattr(civ, key, 0.0)
    alignment.flow(civ, light=n * (lived - ruled * rho), dark=n * ruled * rho)


def overturned(kernel: Any, planet: Any) -> None:
    """The many have risen: the few who took are gone, and their take with them."""
    planet.society["rent"] = 0.0
    planet.society["rent_cycle"] = kernel.cycle_count
    stats(kernel)["risings"] += 1


def summary(kernel: Any) -> Dict[str, Any]:
    """What the few take across the peoples, and how the peoples' histories and tellings read."""
    from xylarium.kernel import alignment
    worlds = [p for s in kernel.sectors.values() for p in s.planets
              if p.population > 0 and getattr(p, "civilization", None) is not None and not getattr(p, "natives", None)]
    rents = [of(p) for p in worlds]
    chars = [alignment.character(p.civilization) for p in worlds]
    gaps = [alignment.gap(p.civilization) for p in worlds]
    n = max(1, len(worlds))
    st = stats(kernel)
    return {"chosen": st["chosen"], "risings": st["risings"], "mean_rent": round(sum(rents) / n, 4),
            "light": sum(1 for a in chars if a >= alignment.NEUTRAL_EDGE),
            "dark": sum(1 for a in chars if a <= -alignment.NEUTRAL_EDGE),
            "mean_gap": round(sum(gaps) / n, 4)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="rent",
    state=lambda: {"chosen": 0, "risings": 0},
    summary=summary,
))
