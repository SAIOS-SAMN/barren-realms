"""
Xylarium lifespan: a people is born, grows, grows old and dies - and what it remembers of its dead.

Without death a people only grows: nothing turns over, nothing is lost to remember, nothing new is thought by new
minds. Each people's life history is its species' physics, on the universal clock (biology runs on chemical
kinetics, not on orbits; a people reckons its own age in its homeworld's years - clock.local_years):

  LIFE HISTORY  every span is a multiple of the species' generation (fertility.generation_of: ~ body mass^(1/4)
                over its chemistry's pace - the life-history invariants, Charnov 1993), each multiple read off one
                data point, Earth's people: maturity ~17 of a ~28-year generation (0.6), the end of the productive
                span ~48 (1.7), adult life expectancy ~70 (2.5), the longest lives ~120 (4.3).
  COHORTS       youth (born, fed, not yet working or bearing), prime (working, bearing, thinking, making), elders
                (the memory: they carry the mortality exit). Stable shares in a population that neither grows nor
                shrinks are the spans' own; a youth bulge or an ageing people departs from them, and what prime does
                (inquiry, births, work) is scaled by its share against the stable one.
  THR           total health resilience, 0 .. 1: the chance a newborn lives to old age - nutrition x air x its
                star's light x its world's cleanliness x how well its biome suits it x shelter x what its crowd
                diseases spare. Mortality before old age is -ln(THR) over the span to it; fertility is scaled by
                THR (TFR x THR).
  LONGEVITY     an elder's remaining span reaches from the median life (2.5 generations) toward the longest lives
                (4.3) as the people masters biology (knowledge.py: medicine), and shrinks with THR. The deaths its
                healing spares are its deeds, as the deaths its strife causes are (alignment: lives saved).
  DISEASE       crowd diseases are species too, living on the people: one persists only in a community above its
                critical size (Bartlett 1957: ~250,000 for measles in a people of Earth's generation; a faster-
                breeding people renews its susceptibles sooner, so its critical size scales with its generation).
                Above it the disease is endemic: R0 ~ N / critical size, each maturing cohort meets it (the
                epidemic's final size), and its lethality falls as host and pathogen co-evolve - e-fold a
                generation from virgin-soil lethality (~25%: Fiji's measles, 1875). Pathogens cross only between
                peoples of one chemistry: a first meeting with an endemic people of the same chemistry is a virgin-
                soil epidemic (EPIDEMIC).
  THE DEAD      a body is its species' mass; it returns to the world's stores as its people's staple (declared:
                decomposition) - unless the people burns it for its warmth (a pyre or bio-reactor, where its
                chemistry burns and it has works to use the heat: a declared energy source), at the cost of
                remembrance. Which it does follows from what it believes of its dead (culture.py): a people whose
                sky is a roof, or the eyes of the dead, lays them to rest; one that reads the lights as suns burns
                them if it can, else returns them to the ground.
  THE EMINENT   when a people turns, comes to know itself, founds its order, first farms or sends its first ship,
                the minds that carried it are remembered by name (EMINENT); they die on their own reckoning
                (EPITAPH), and their memory fades over generations - slower where the dead are laid to rest and
                where elders are many to tell of them - until no one remembers.

A people's TURNOVER is its cumulative dead against its number: a people has replaced itself when as many have died
as now live. Its beliefs, art and fork are weighed again at each turnover (culture.py, syntropy.py), and what it
knows fades as its knowers die (knowledge.py: the Earth-measured R&D depreciation, its human-mortality share
replaced by the people's own).
"""

import math
from typing import Any, Dict, List, Optional

MATURITY_GEN = 0.6              # first reproduction, in generations (Earth: ~17 of ~28 years)
ELDER_GEN = 1.7                 # end of the productive span (Earth: ~48)
LIFE_MEDIAN_GEN = 2.5           # adult life expectancy (Earth: ~70)
LIFE_MAX_GEN = 4.3              # the longest lives (Earth: ~120)
BODY_CYCLES = 13                # a body's mass in its own meals (Earth: ~70 kg over ~1.5 kg a day ~ 47 days ~ 13 cycles)
TROUGH = 330                    # the infected a crowd infection needs at its lowest ebb not to die out (declared)
INFECTION_YEARS = 0.04          # an infection's course in a body at unit pace (declared); it runs at the body's pace
CFR_VIRGIN = 0.5                # the virulence-transmission trade-off (Anderson & May 1982): with transmission rising as
                                # the square root of virulence, the pathogen's best virulence equals recovery plus
                                # death, so it kills half of those it meets in a host that has never adapted to it
EMINENT_KEPT = 12               # named dead a people keeps in its annals at once
EMINENT_ON = {"INTROSPECTION": "philosopher", "STATEHOOD": "lawgiver", "EXODUS": "captain", "UPLIFT": "teacher",
              "LEGEND": "hero", "FARMING": "founder", "TURNING": "leader", "PHILOSOPHY": "sage"}   # gravest first
FORGOTTEN = math.exp(-3)        # memory below this: no one remembers


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "lifespan")


def _q_years() -> float:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES / 100.0


def stable_shares(planet: Any = None) -> Dict[str, float]:
    """Cohort shares of a people that neither grows nor shrinks: its own spans (its elders' as its health and
    medicine make them) - a long-lived stable people is old, and that is no bulge."""
    elder = LIFE_MEDIAN_GEN - ELDER_GEN
    if planet is not None:
        elder = float((planet.society.get("life") or {}).get("elder_gen", elder))
    spans = {"youth": MATURITY_GEN, "prime": ELDER_GEN - MATURITY_GEN, "elder": max(1e-3, elder)}
    total = sum(spans.values())
    return {k: v / total for k, v in spans.items()}


def cohorts(planet: Any) -> Dict[str, float]:
    c = planet.society.get("cohorts")
    return dict(c) if c else stable_shares(planet)


def prime_factor(planet: Any) -> float:
    """What a people's working, bearing, thinking share is against a stable people's (1 when stable)."""
    return cohorts(planet)["prime"] / stable_shares(planet)["prime"]


def elder_factor(planet: Any) -> float:
    return cohorts(planet)["elder"] / stable_shares(planet)["elder"]


# ---------------------------------------------------------------------- health
def critical_community(kernel: Any, planet: Any) -> float:
    """The smallest people a crowd infection persists in (SIR with births): its trough of infected x the host's
    generation (how slowly new susceptibles are born) over the infection's course - both run at the host body's
    pace, so the pace cancels and only the body's size and life history remain."""
    from xylarium.kernel import biosphere, fertility
    t = biosphere.body_temperature(planet)
    pace = (t / 278.0) if t else 1.0
    return TROUGH * fertility.generation_of(kernel, planet) / (INFECTION_YEARS / pace)


def disease(kernel: Any, planet: Any) -> Dict[str, float]:
    """The crowd diseases living on this people: endemic or not, R0, the share each cohort meets, their lethality."""
    from xylarium.kernel import fertility, laws
    soc = planet.society
    ccs = critical_community(kernel, planet)
    n = planet.population
    if n <= ccs:
        soc.pop("endemic_since", None)
        return {"endemic": 0.0, "r0": n / ccs, "met": 0.0, "cfr": 0.0}
    since = soc.setdefault("endemic_since", kernel.cycle_count)
    gens = (kernel.cycle_count - since) / 100.0 / max(1e-6, fertility.generation_of(kernel, planet))
    cfr = CFR_VIRGIN * math.exp(-gens)                   # host and pathogen co-evolve toward mildness
    r0 = n / ccs
    return {"endemic": 1.0, "r0": r0, "met": laws.final_size(r0), "cfr": cfr}


def thr(kernel: Any, planet: Any) -> float:
    """Total health resilience: the chance a newborn lives to old age."""
    from xylarium.kernel import biosphere
    from xylarium.kernel.geology import pollution_factor
    soc = planet.society
    nutrition = min(1.0, float(soc.get("self_sufficiency", 1.0) or 1.0))
    air = min(1.0, float(soc.get("atmosphere", 1.0)))
    sun = max(0.0, min(1.0, float(soc.get("star_k", 1.0))))
    land = biosphere.land(kernel, planet)
    biome = min(1.0, float(land["chemistry"]))           # how its chemistry suits this ground (its light is its food)
    k = biosphere.carrying_capacity(kernel, planet)
    shelter = min(1.0, k / max(1, planet.population)) if k > 0 else 0.0
    d = disease(kernel, planet)
    spared = 1.0 - d["met"] * d["cfr"]
    return max(0.0, nutrition * air * sun * float(pollution_factor(planet)) * biome * shelter * spared)


def medicine(kernel: Any, planet: Any) -> float:
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge, laws, technology
    holder = knowledge.holder_of_planet(planet)
    m = laws.mastery(knowledge.experience(kernel, holder, "biology"), KNOWLEDGE_UNIT)
    if technology.has(kernel, holder, "genetics"):
        m = m + (1.0 - m) * technology.GENETIC_GAIN / (1.0 + technology.GENETIC_GAIN)   # it rewrites its own ageing
    return m


def expectancy_years(kernel: Any, planet: Any, health: Optional[float] = None) -> float:
    """Life expectancy at birth, in standard years: maturity through old age by THR, and an elder's span."""
    from xylarium.kernel import fertility
    gen = fertility.generation_of(kernel, planet)
    h = thr(kernel, planet) if health is None else health
    elder_span = (LIFE_MEDIAN_GEN - ELDER_GEN + (LIFE_MAX_GEN - LIFE_MEDIAN_GEN) * medicine(kernel, planet)) * h
    return gen * (ELDER_GEN * h + elder_span) if h > 0 else 0.0


def body_units(kernel: Any, planet: Any, deaths: float) -> float:
    """Staple units in the bodies of `deaths` of this people: a body is its species' mass (biosphere)."""
    from xylarium.config import FOOD_PER_THOUSAND
    from xylarium.kernel import biosphere
    mass = biosphere.body_mass(planet, kernel)
    return deaths / 1000.0 * FOOD_PER_THOUSAND * BODY_CYCLES * mass


# ---------------------------------------------------------------------- the season
def _holder(planet: Any) -> Optional[str]:
    from xylarium.kernel import knowledge
    return knowledge.holder_of_planet(planet)


def practice(kernel: Any, planet: Any) -> str:
    """What a people does with its dead, from what it believes of them: 'rest', 'pyre' or 'return'."""
    from xylarium.kernel import biosphere, culture, energy
    stance = (culture.stats(kernel)["peoples"].get(_holder(planet)) or {}).get("stance")
    if stance in (None, "roof", "sacred"):
        return "rest"
    burns = biosphere.metabolism_of(kernel, planet) in ("biotic", "umbral") and \
        float(planet.society.get("atmosphere", 1.0)) > 0 and energy.tier(planet) >= 1
    return "pyre" if burns else "return"


def _flows(kernel: Any, planet: Any, years: float) -> Dict[str, float]:
    """This season's deaths by cohort, and the cohorts' ageing, for a world's people."""
    from xylarium.kernel import fertility
    gen = max(1e-6, fertility.generation_of(kernel, planet))
    h = thr(kernel, planet)
    c = cohorts(planet)
    n = planet.population
    y, p, e = c["youth"] * n, c["prime"] * n, c["elder"] * n
    hazard = -math.log(max(1e-9, h)) / (ELDER_GEN * gen)              # dying before old age
    d = disease(kernel, planet)
    pox = d["met"] * d["cfr"] / (MATURITY_GEN * gen)                 # each maturing cohort meets the crowd disease
    elder_span = max(1e-3, (LIFE_MEDIAN_GEN - ELDER_GEN + (LIFE_MAX_GEN - LIFE_MEDIAN_GEN)
                            * medicine(kernel, planet)) * max(h, 1e-3) * gen)
    dy = y * (1 - math.exp(-(hazard + pox) * years))
    dp = p * (1 - math.exp(-hazard * years))
    de = e * (1 - math.exp(-years / elder_span))
    grown = (y - dy) * years / (MATURITY_GEN * gen)
    aged = (p - dp) * years / ((ELDER_GEN - MATURITY_GEN) * gen)
    # the healthy, unlearned reference: the deaths the people's own logistic balance already carries
    ref = e * (1 - math.exp(-years / ((LIFE_MEDIAN_GEN - ELDER_GEN) * gen)))
    return {"y": y, "p": p, "e": e, "dy": dy, "dp": dp, "de": de, "grown": grown, "aged": aged, "ref": ref,
            "thr": h, "disease": d, "elder_gen": elder_span / gen}


def _season_world(kernel: Any, planet: Any, years: float, rec: Dict[str, Any]) -> float:
    """Ages, kills and buries a world's people for the season; returns its dead."""
    soc = planet.society
    life = soc.setdefault("life", {})
    n0 = int(life.get("last_n", planet.population))
    f = _flows(kernel, planet, years)
    deaths = f["dy"] + f["dp"] + f["de"]
    excess = deaths - f["ref"]                       # what ill health (or medicine) adds to the balance's own dying
    born = max(0.0, planet.population - n0 + f["ref"])
    # ill health kills beyond what the people's own balance carries; medicine spares some of those it would
    if excess < 0 and medicine(kernel, planet) > 0:            # lives its own healing spares are its deeds too
        from xylarium.kernel import sustenance
        sustenance.flow_civ(planet, light=-excess)
    owed = excess + float(life.get("excess_carry", 0.0))
    take = max(-10 ** 12, min(int(owed), planet.population))
    life["excess_carry"] = round(owed - int(owed), 6)
    planet.population -= take
    y = max(0.0, f["y"] - f["dy"] - f["grown"] + born)
    p = max(0.0, f["p"] - f["dp"] + f["grown"] - f["aged"])
    e = max(0.0, f["e"] - f["de"] + f["aged"])
    total = y + p + e
    if total > 0:
        soc["cohorts"] = {"youth": round(y / total, 5), "prime": round(p / total, 5), "elder": round(e / total, 5)}
    life.update(last_n=planet.population, thr=round(f["thr"], 4), deaths_q=round(deaths, 1), born_q=round(born, 1),
                elder_gen=round(f["elder_gen"], 4),
                expectancy=round(expectancy_years(kernel, planet, f["thr"]), 2))
    life["ancestors"] = int(life.get("ancestors", 0)) + int(deaths)
    _bury(kernel, planet, deaths)
    return deaths


def _bury(kernel: Any, planet: Any, deaths: float) -> None:
    from xylarium.kernel import energy, staples
    if deaths <= 0:
        return
    units = body_units(kernel, planet, deaths) + float(planet.society["life"].get("body_carry", 0.0))
    whole = int(units)
    planet.society["life"]["body_carry"] = round(units - whole, 6)
    if whole <= 0:
        return
    how = practice(kernel, planet)
    planet.society["life"]["practice"] = how
    if how == "pyre":
        meu = int(whole * energy.CARBON_EU * energy.MILLI)          # its carbon burned for its warmth
        planet.society["grid_meu"] = int(planet.society.get("grid_meu", 0)) + meu
        energy.source(kernel, "funerary_pyre", meu)
    else:
        staples.add(planet, staples.of(kernel, planet), whole, "decomposition")    # back to the world's stores


# ---------------------------------------------------------------------- the eminent dead
def _eminent(kernel: Any, holder: str, worlds: List[Any], rec: Dict[str, Any]) -> List[str]:
    from xylarium.kernel import fertility, history, scheduler
    from xylarium.kernel.natives import _name
    logs: List[str] = []
    cap = max(worlds, key=lambda w: (w.population, w.id))
    gen = fertility.generation_of(kernel, cap)
    named = rec.setdefault("eminent", [])
    seen = rec.setdefault("seen_events", 0)
    people = holder.split(":", 1)[-1]
    # the era's candidates: what this people did since it last named one of its own
    for e in history.of_people(kernel, holder):
        n = int(e["id"].split("-")[1])
        if n > seen and e["kind"] in EMINENT_ON:
            cands = rec.setdefault("candidates", [])
            if e["id"] not in {c["id"] for c in cands}:
                cands.append({"id": e["id"], "kind": e["kind"], "title": e["title"], "cycle": e["cycle"]})
                del cands[:-16]
        rec["seen_events"] = max(rec["seen_events"], n)
    order = list(EMINENT_ON)
    cands = rec.get("candidates") or []
    pop = sum(w.population for w in worlds)
    # one name an era: when the people has replaced itself since it last named one, the mind behind the gravest
    if cands and (rec.get("named_died") is None or turned_over(kernel, holder, rec["named_died"], pop)):
        e = min(cands, key=lambda c: (order.index(c["kind"]), -c["cycle"]))
        rec["candidates"], rec["named_died"] = [], died(kernel, holder)
        role = EMINENT_ON[e["kind"]]
        name = _name(scheduler.rng(kernel, "eminent", holder, e["id"]))
        life = expectancy_years(kernel, cap)
        fig = {"name": name, "role": role, "for": e["title"], "event": e["id"], "born": e["cycle"] - int(
            ELDER_GEN * gen * 100 / 2), "dies": e["cycle"] + int(max(1.0, life - ELDER_GEN * gen / 2) * 100),
            "memory": 1.0, "dead": False}
        named.append(fig)
        if kernel.cycle_count < fig["dies"]:              # one already gone is remembered at once (EPITAPH, below)
            history.event(kernel, "EMINENT", f"{name}, {role} of the {people}", actors=[holder], planet=cap,
                          refs=[e["id"]], cause=e["title"], data={"name": name, "role": role})
    for fig in named:
        if not fig["dead"] and kernel.cycle_count >= fig["dies"]:
            fig["dead"] = True
            history.event(kernel, "EPITAPH", f"{fig['name']}, {fig['role']} of the {people}, is dead",
                          actors=[holder], planet=cap, refs=[fig["event"]],
                          text=f"The {people} remember {fig['name']}, who was there when {fig['for'].lower()}.")
            logs.append(f"[LIFE] The {people} mourn {fig['name']}, their {fig['role']}.")
    # memory fades over generations - slower where the dead are laid to rest and elders are many to tell of them
    years = max(0.0, (kernel.cycle_count - int(rec.get("faded", kernel.cycle_count))) / 100.0)
    rec["faded"] = kernel.cycle_count
    rest = 0.5 if cap.society.get("life", {}).get("practice", "rest") == "rest" else 1.0
    fade = years / max(1e-6, gen) * rest / max(0.25, elder_factor(cap))
    for fig in named:
        if fig["dead"]:
            fig["memory"] = round(fig["memory"] * math.exp(-fade), 5)
    rec["eminent"] = [f for f in named if f["memory"] >= FORGOTTEN][-EMINENT_KEPT:]
    return logs


def remembered(kernel: Any, holder: Optional[str]) -> List[Dict[str, Any]]:
    """The named dead a people still remembers, most remembered first."""
    rec = stats(kernel)["peoples"].get(holder or "") or {}
    return sorted((f for f in rec.get("eminent", []) if f["dead"]), key=lambda f: (-f["memory"], f["name"]))


# ---------------------------------------------------------------------- virgin soil
def _virgin_soil(kernel: Any, by: Dict[str, List[Any]]) -> List[str]:
    """New meetings between peoples of one chemistry carry the endemic diseases of one to the other."""
    from xylarium.kernel import biosphere, contact, history, laws
    st = stats(kernel)
    met = set(st.setdefault("met", []))
    logs: List[str] = []
    for key in sorted(contact.stats(kernel)["familiarity"]):
        if key in met:
            continue
        met.add(key)
        a, _, b = key.partition("|")
        if a not in by or b not in by:
            continue
        ca, cb = max(by[a], key=lambda w: w.population), max(by[b], key=lambda w: w.population)
        if biosphere.metabolism_of(kernel, ca) != biosphere.metabolism_of(kernel, cb):
            continue                                       # a pathogen lives in one chemistry
        for src, dst in ((ca, cb), (cb, ca)):
            if not src.society.get("endemic_since") or dst.society.get("endemic_since"):
                continue
            r0 = max(1.0, src.population / critical_community(kernel, src))
            dead = int(dst.population * laws.final_size(r0) * CFR_VIRGIN)
            if dead <= 0:
                continue
            dst.population -= dead
            dst.society["endemic_since"] = kernel.cycle_count     # now theirs too, from virgin soil
            who, whom = _holder(src) or "", _holder(dst) or ""
            history.event(kernel, "EPIDEMIC", f"The {whom.split(':')[-1]} sicken from meeting the "
                          f"{who.split(':')[-1]}", actors=[whom, who], planet=dst, magnitude=dead,
                          cause="the crowd diseases of a people of their own chemistry, on virgin soil")
            logs.append(f"[LIFE] {dead:,} of the {whom.split(':')[-1]} die of the strangers' sickness.")
    st["met"] = sorted(met)
    return logs


def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import knowledge
    st = stats(kernel)
    years = _q_years()
    by: Dict[str, List[Any]] = {}
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population > 0 and getattr(p, "civilization", None) is not None and not getattr(p, "natives", None):
                h = knowledge.holder_of_planet(p)
                if h:
                    by.setdefault(h, []).append(p)
    logs = _virgin_soil(kernel, by)
    for holder, worlds in sorted(by.items()):
        rec = st["peoples"].setdefault(holder, {"died": 0.0})
        dead = sum(_season_world(kernel, p, years, rec) for p in worlds if p.population > 0)
        rec["died"] = round(float(rec.get("died", 0.0)) + dead, 1)
        live = [p for p in worlds if p.population > 0]
        if live:
            rec["expectancy"] = round(sum(float(p.society["life"].get("expectancy", 0.0)) * p.population
                                          for p in live) / max(1, sum(p.population for p in live)), 2)
            logs += _eminent(kernel, holder, live, rec)
    for gone in [h for h in st["peoples"] if h not in by]:
        st["peoples"][gone]["gone"] = True
    return logs


# ---------------------------------------------------------------------- what others read
def died(kernel: Any, holder: Optional[str]) -> float:
    """A people's dead, all told (its turnover counter)."""
    if not holder or "lifespan" not in getattr(kernel, "state", {}):
        return 0.0
    return float((stats(kernel)["peoples"].get(holder) or {}).get("died", 0.0))


def turned_over(kernel: Any, holder: Optional[str], since_died: float, population: int) -> bool:
    """Whether a people has replaced itself since a mark: as many have died as now live."""
    return died(kernel, holder) - since_died >= max(1, population)


def expectancy(kernel: Any, holder: Optional[str]) -> Optional[float]:
    if not holder or "lifespan" not in getattr(kernel, "state", {}):
        return None
    return (stats(kernel)["peoples"].get(holder) or {}).get("expectancy")


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    live = {h: r for h, r in st["peoples"].items() if not r.get("gone")}
    if not live:
        return {}
    return {"peoples": len(live), "dead": int(sum(r.get("died", 0) for r in live.values())),
            "remembered": sum(1 for r in live.values() for f in r.get("eminent", []) if f["dead"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="lifespan",
    state=lambda: {"peoples": {}, "met": []},
    season=quarter,
    summary=summary,
))
