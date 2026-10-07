"""
Xylarium annals: a people's long ages, lived at the level of history while the galaxy's deep time runs on.

The engine lives a people year by year on the universal clock, while the galaxy turns on deep time - at the teeming
pace ten million years pass for every clock year. Without the annals a people woken a billion years ago would have
lived only a hundred of its own years: the oldest minds in the galaxy would be its youngest peoples. Each year the
annals close that gap: every people is carried, at the level of history, through the deep years that have passed
since it woke and that it has not yet lived, along the same bridges the full engine carries it across - foraging,
farming, a state, works, yards, the crossing to the stars - each an exponential wait whose mean is that bridge's
span in the people's own generations (measured by tools/bridges.py from the engine itself, scaled by how fast its
minds think: laws.cognition's speed). Peoples also fall: a hazard per generation, the life-ending events their world
faces (supernovae, impacts: world_hazard_per_gyr) borne as well as what they know of life lets them.

What a people lives in its annals it keeps: its way, its works, its yards, its knowledge, its crossing - and its
people grows to what its world now feeds. Once across, its dominion grows (worlds settled per generation, up to the star systems within
its network's reach: spheres.py, paid in passages by its power - so no faster than its ships travel), and where two networks meet the style of the one
arriving decides between a bond and a realm war (spheres.py, realmwars.py). A fallen people leaves ruins on its homeworld (archaeology.py: the deep strata of an ANCIENT
culture) and its name in the galaxy's chronicle. The galaxy's lore is these annals: every era, crossing, war and
fall, dated in deep time (history.py: ERA, ASCENT, DOMINION, GALACTIC_WAR, FALL).
"""

import math
from typing import Any, Dict, List, Optional

# the bridges' spans in a people's own generations (means of exponential waits), and its hazards per generation
SPANS = {                       # measured by tools/bridges.py on seed 7's first peoples (the engine's own pace),
    "farm": 8.0,                # rounded; crossing beyond its runs is the progenitors' declared expectation
    "state": 4.0,
    "works": 20.0,
    "yards": 60.0,
    "crossed": 400.0,
}
STAGES = ("forage", "farm", "state", "works", "yards", "crossed")
GENETICS_SPAN = 100.0           # generations a people with yards takes to master its own genome (declared: between
                                # yards' 60 and the crossing's 400 - the knowledge of itself it needs to live elsewhere)
EMBODIMENT_SPAN = 200.0         # generations a genome-less people takes to come into a vessel (declared: harder than any
                                # one bridge - it learns the terrestrial dimensions from nothing)
HAZARD_STEPS = 256              # steps a bound dominion's hazard is integrated over, in ln(1 + g t)
MIN_GENERATIONS = 1.0           # gaps shorter than a generation are left to the full engine


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "annals")


def _stage(kernel: Any, who: str, home: Any) -> str:
    from xylarium.kernel import mastery, sustenance
    if mastery.crossed(kernel, who) and "crossed" in stats(kernel)["of"].get(who, {}).get("passed", []) \
            or who in mastery.stats(kernel).get("crossed", {}):
        return "crossed"
    if sustenance.yards(home):
        return "yards"
    if home.citadel_level >= 1:
        return "works"
    return {"forage": "forage", "farm": "farm"}.get(home.society.get("way"), "state")


def _can_reach_orbit(kernel: Any, who: str, home: Any) -> bool:
    """Whether its world lets it reach orbit at all - by chemistry, or by the atom where its ground has uranium."""
    from xylarium.kernel import technology
    v = technology.chemical_exhaust_kms()
    if technology.orbit_ratio(home, v) <= technology.STRUCTURE:
        return True
    if technology.feasible(kernel, who, "fission", home):
        return technology.orbit_ratio(home, v * technology.FISSION_GAIN) <= technology.STRUCTURE
    return False


def resilience(kernel: Any, who: str) -> float:
    """How much harder a people is to bring down for what it knows of life: its medicine (its mastery of biology),
    its own genome, and minds that can leave a failing body - each a way its people survives what would end it."""
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge, laws, technology
    r = 1.0 + 2.0 * laws.mastery(knowledge.experience(kernel, who, "biology"), KNOWLEDGE_UNIT)
    r += 1.0 if technology.has(kernel, who, "genetics") else 0.0
    r += 2.0 if technology.has(kernel, who, "transfer") else 0.0
    return r


def world_hazard_per_gyr(kernel: Any, home: Any) -> float:
    """The life-ending events a world's people faces per Gyr - the same physics its life climbed against
    (creation.chemistries): an impact beyond what its kind adapted to (life.EXTINCTIONS_PER_GYR: scale-free, so the
    same relative to any background), and - for a people under an open sky - a sterilising pulse, which comes with
    the dying stars where its world circles (life.sterilise_per_gyr)."""
    from xylarium.kernel import biosphere, cosmos, life, worlds
    g = cosmos.stats(kernel)["place"].get(str(home.sector_id), {}) if cosmos.is_cosmic(kernel) else {}
    crowd = cosmos.cosmic_rays(float(g.get("r", cosmos.R0_KPC)))
    try:
        med = worlds.best(worlds.of_planet(kernel, home), biosphere.metabolism_of(kernel, home))
    except Exception:
        med = None
    dark = med is not None and med.get("where") in ("under_ice", "deep")
    return life.sterilise_per_gyr(crowd, dark) + life.EXTINCTIONS_PER_GYR


def fall_per_generation(kernel: Any, who: str, home: Any) -> float:
    """A one-world people's hazard of falling, per generation: its world's life-ending events over a generation, borne
    as well as what it knows of life lets it (resilience). Among the stars it is shared out over the worlds it holds."""
    from xylarium.kernel import fertility
    gen = max(1.0, fertility.generation_of(kernel, home))
    return world_hazard_per_gyr(kernel, home) * gen / 1e9 / resilience(kernel, who)


def _speed(kernel: Any, home: Any) -> float:
    from xylarium.kernel import decide, knowledge, technology
    who = knowledge.holder_of_planet(home)
    s = max(0.05, float(decide.mind_of_planet(kernel, home).get("speed", 1.0)))
    for cap, gain in (("genetics", technology.GENETIC_GAIN), ("robotics", technology.ROBOTICS_GAIN)):
        if technology.has(kernel, who, cap):
            s *= 1.0 + gain                                  # past the metabolic bound: not waiting on its generations
    return s


CAPS_AT = (("radio", 3), ("computation", 3), ("medicine", 3), ("fission", 4), ("orbit", 4), ("networks", 4),
           ("robotics", 4), ("synthesis", 5))      # genetics is not handed over with yards: it is waited for


def _grant(kernel: Any, who: str, home: Any, idx: int) -> None:
    """What a people finds in its long ages, as its world allows, by the stage it has reached."""
    from xylarium.kernel import technology
    held = technology.stats(kernel)["of"].setdefault(who, {})
    for cap, at in CAPS_AT:
        if idx >= at and cap not in held and technology.feasible(kernel, who, cap, home):
            held[cap] = kernel.cycle_count


def _apply(kernel: Any, who: str, home: Any, stage: str) -> None:
    """Set a people's world to what its annals carried it to."""
    from xylarium.config import DAUGHTER_CITADEL_TIER
    from xylarium.kernel import biosphere, institutions, intellect, mastery, ways
    from xylarium.kernel import crystal as C
    soc = home.society
    idx = STAGES.index(stage)
    if idx >= 1 and soc.get("way") == "forage":
        soc["way"] = "farm"
        soc["crop_z"] = max(float(soc.get("crop_z", 0.0)), math.log(1.0 / ways.TROPHIC_EFFICIENCY))
    if idx >= 2 and soc.get("way") != "state":
        soc["way"] = "state"
        try:
            institutions.found_currency(kernel, home)
        except Exception:
            pass
    if idx >= 3:
        home.citadel_level = max(home.citadel_level, 1 if idx == 3 else home.citadel_level)
    _grant(kernel, who, home, idx)
    if idx >= 4:
        home.citadel_level = max(home.citadel_level, DAUGHTER_CITADEL_TIER)
    if idx >= 5:
        mastery.stats(kernel)["crossed"].setdefault(who, kernel.cycle_count)
        vocab = intellect.stats(kernel)["vocab"].setdefault(who, list(intellect.BASE))
        for c in list(C.STACK_OPS) + list(C.HYPER_OPS):
            if c not in vocab:
                vocab.append(c)
    try:
        ways._refresh(kernel, home)
    except Exception:
        pass
    home.population = max(home.population, int(biosphere.carrying_capacity(kernel, home)))


def _fall(kernel: Any, who: str, worlds: List[Any], epoch: float) -> str:
    from xylarium.kernel import archaeology, history
    import random
    home = max(worlds, key=lambda p: p.population)
    name = who.split(":", 1)[-1]
    rng = random.Random(f"{who}:{epoch}")
    civ = getattr(home, "civilization", None)
    for p in worlds:
        p.ruins = archaeology.bury(p, archaeology._new_ruins(
            name, getattr(civ, "clade", "unknown"), getattr(civ, "metabolism", "biotic"), "ANCIENT",
            6 + STAGES.index(_stage(kernel, who, home)), list(getattr(civ, "discovered_elements", []) or []),
            "the long ages", kernel.cycle_count, 2 + int(rng.random() * 3), p.currency,
            p.treasury + getattr(p, "household_purse", 0), rng))
        p.treasury = 0
        p.household_purse = 0
        p.population = 0
        p.civilization = None
        p.owner_id = None
        p.faction_id = None
    from xylarium.kernel import steward
    steward.detach(kernel, who)                               # no one is left to counsel
    history.event(kernel, "FALL", f"The {name} fall", actors=[who], planet=home,
                  data={"epoch": round(epoch, 6)},
                  cause=f"at the level of history; its ruins lie on "
                        f"{len(worlds)} world{'s' if len(worlds) != 1 else ''}")
    return f"[ANNALS] The {name} fall; their ruins lie on {home.name}."


def _history(kernel: Any, who: str, rec: Dict[str, Any], stage: str, lived: float, gen: float, speed: float,
             fall_rate: float) -> Dict[str, Any]:
    """A people's own history at the level of history: its progress in its own (minds-paced) generations, P, counted
    over all its years - lived year by year in the engine or carried here; the hazard it has run, H, against the
    threshold its own stream set for its fall, E; and, for each turning, the point its wait is counted from. Every
    draw is keyed to the people and the turning, never to the clock: however its time is cut - watched or not, one
    look-away or ten - the same seed gives it the same history."""
    from xylarium.kernel import scheduler
    h = rec.get("hist")
    if h is None:
        h = rec["hist"] = {"P": 0.0, "H": 0.0, "since": 0.0, "T": {}, "stage": stage, "lived": lived,
                           "E": scheduler.rng(kernel, "annals", who, "fall").expovariate(1.0)}
    h.setdefault("rate", fall_rate)                           # its hazard, as it stood at its last turning
    h.setdefault("W", float(rec.get("dominion", 1)))          # its dominion, unrounded (the record keeps it whole)
    if int(rec.get("dominion", 1)) > int(h["W"]):             # worlds the engine settled beyond the witnessed
        h["W"] += int(rec["dominion"]) - int(h["W"])
    seen = max(0.0, lived - float(h.get("lived", lived))) / max(1.0, gen)
    if seen > 0:                                              # the years the engine lived it count for its history too
        h["P"] += speed * seen
        h["H"] += h["rate"] * seen
    h["lived"] = lived
    if h.get("stage") != stage:                               # it turned in the engine: its next wait counts from now
        h["stage"] = stage
        h["since"] = h["P"]
        h["rate"] = fall_rate
        h["T"] = {k: v for k, v in h["T"].items() if k not in STAGES or STAGES.index(k) > STAGES.index(stage)}
    return h


def dominion_cap(kernel: Any, who: str, home: Any = None) -> float:
    """How many worlds a dominion can hold now: the systems its settling has reached, on its side of every seam
    (settling.held). A people that has not crossed has no bubble, and the live engine's daughters are its own."""
    from xylarium.kernel import cosmos, settling
    if kernel is None or who not in settling.stats(kernel):
        return math.inf
    return settling.held(kernel, who, cosmos.deep_gyr(kernel))


def _dominion_hazard(rate: float, w0: float, gens: float, cap_of: Any, need: Optional[float] = None,
                     g: float = 0.0) -> tuple:
    """The hazard a dominion of w0 worlds runs over `gens` (any unit of time) as it settles, its fall shared over its
    worlds: they grow e^(g t), but never past the systems it has reached (cap_of(t), growing as its front does).
    While it grows freely, f/(w0 g)(1 - e^-g t); once its front binds it, the integral of f/cap, taken in
    ln(1 + g t) where the front's volume is smooth. With `need`, also when that much hazard has been run (else None).
    Returns (hazard run, generations until `need`)."""
    w0 = max(1.0, w0)
    if g <= 0:                                                # it does not grow: its fall is shared over w0
        ran = rate / w0 * gens
        return (need, need * w0 / rate) if need is not None and need < ran else (ran, None)
    bound = lambda t: math.log(w0) + g * t >= math.log(max(1.0, cap_of(t)))   # noqa: E731
    if bound(0.0):
        tb = 0.0
    elif not bound(gens):
        tb = gens
    else:
        lo, hi = 0.0, gens
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            lo, hi = (lo, mid) if bound(mid) else (mid, hi)
        tb = hi
    free = rate / (w0 * g) * (1.0 - math.exp(-g * tb))
    if need is not None and need < free:
        return need, -math.log(1.0 - need * w0 * g / rate) / g
    ran, steps = free, HAZARD_STEPS
    u0, u1 = math.log1p(g * tb), math.log1p(g * gens)
    du = (u1 - u0) / steps
    for i in range(steps):
        if du <= 0:
            break
        ua, ub = u0 + i * du, u0 + (i + 1) * du
        ta, tb_ = math.expm1(ua) / g, math.expm1(ub) / g
        tm = math.expm1(0.5 * (ua + ub)) / g
        w = min(math.exp(min(700.0, math.log(w0) + g * tm)), max(1.0, cap_of(tm)))
        h = rate / w * (tb_ - ta)
        if need is not None and ran + h >= need:
            return need, ta + (need - ran) * w / rate
        ran += h
    return ran, None


def _next_kind(kernel: Any, who: str, home: Any, worlds: List[Any], stage: str) -> tuple:
    """The turning a people waits on next, and its span: its next stage, or what stands before it - hands (a
    genome-less people's vessel), its own genome (to live under another sun) - or none (its gravity holds it)."""
    from xylarium.kernel import mastery as _mastery, technology as _tech
    nxt = STAGES.index(stage) + 1
    kind: Optional[str] = STAGES[nxt]
    span = SPANS.get(STAGES[nxt], 0.0)
    if STAGES[nxt] == "works" and not _tech.embodied(kernel, who, home):
        kind, span = "embodiment", EMBODIMENT_SPAN
    elif STAGES[nxt] == "yards" and not _can_reach_orbit(kernel, who, home):
        kind = None                                           # its gravity holds it: it lives on, on its world
    elif STAGES[nxt] == "crossed" and not _mastery.genome_ready(kernel, who, worlds):
        kind = None if _tech.genomeless(kernel, home) else "genetics"   # a vessel needs no genome of its own
        span = GENETICS_SPAN
    return kind, span


def _due(kernel: Any, who: str, home: Any, rec: Dict[str, Any], lived: float, gen: float) -> bool:
    """Has an unguided people's own history reached its next turning in the years the engine lived it?"""
    h = rec.get("hist")
    if h is None:
        return False
    stage = _stage(kernel, who, home)
    if STAGES.index(stage) + 1 >= len(STAGES):
        return False
    from xylarium.kernel import relations
    kind, span = _next_kind(kernel, who, home, relations._peoples(kernel).get(who, [home]), stage)
    if kind is None:
        return False
    progress = h["P"] + _speed(kernel, home) * max(0.0, lived - float(h.get("lived", lived))) / max(1.0, gen)
    return progress >= _threshold(kernel, who, h, kind, span)


def history_decides(kernel: Any, who: Optional[str]) -> bool:
    """Does this people's own history decide its turnings? In a universe begun at its Big Bang, every people no
    seat guides; in a settled universe (no annals), its councils, as ever."""
    from xylarium.kernel import cosmos
    return cosmos.is_cosmic(kernel) and not guided(kernel, who)


def guided(kernel: Any, who: Optional[str]) -> bool:
    """Does a seat guide this people - a steward or progenitor (human or AI) at its councils, or an owner (a
    captain's or a ruler's holdings)? A guided people's councils choose its turnings, its seat's counsel weighed
    among their reasons; an unguided people turns when its own history comes to it (its stream), whether it is lived
    year by year or carried here - so watching it never changes when it turns."""
    if not who:
        return False
    if who.startswith("captain:"):
        return True
    from xylarium.kernel import ages, knowledge
    for pid, rec in (ages.stats(kernel).get("stewards") or {}).items() if "ages" in getattr(kernel, "state", {}) else []:
        if rec.get("people") == who:
            return True
        p = kernel.get_planet(rec.get("planet"))
        if p is not None and knowledge.holder_of_planet(p) == who:
            return True
    return False


def _threshold(kernel: Any, who: str, h: Dict[str, Any], kind: str, span: float) -> float:
    """Where in its own progress a people makes this turning: from the point its wait began, its own stream's
    draw for this turning (an exponential wait, its mean the bridge's span) - drawn once, kept."""
    from xylarium.kernel import scheduler
    if kind not in h["T"]:
        draw = scheduler.rng(kernel, "annals", who, "turn", kind).expovariate(1.0)
        h["T"][kind] = h["since"] + draw * span
    return h["T"][kind]


def season(kernel: Any) -> List[str]:
    """Once a year every people lives the deep years it has not yet lived - in three passes, so that what one people
    does reaches another when it happens on the one coordinate clock, whatever order they are read in:
      1. each people's own ages up to its crossing (nothing another people does touches them);
      2. every crossed people's dominion together, in coordinate time: bubbles grow, meet, enclose and fall in the
         order those things happen (settling.py);
      3. each people's books for the stretch: its world, its knowledge, its history's light and dark."""
    from xylarium.kernel import cosmos
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // 25) % 4:
        return []
    logs: List[str] = []
    jobs = [j for j in (_live_ages(kernel, who, worlds, logs) for who, worlds in sorted(_peoples(kernel).items()))
            if j is not None]
    _settle(kernel, [j for j in jobs if j.get("cross") is not None], logs)
    from xylarium.kernel import constellations, gateways, settling, steward_ai
    settling.mark_wakings(kernel, _peoples(kernel))
    constellations.season(kernel)                            # the stewards' realms, read as the dominions stand
    steward_ai.ensure(kernel, _peoples(kernel))              # the board is complete up to the stewards
    from xylarium.kernel import endowments
    logs.extend(endowments.season(kernel, _peoples(kernel)))  # the stewards watch, set aside, prepare
    gateways.kindling(kernel, logs)
    for j in jobs:
        _books(kernel, j, logs)
    return logs


def _peoples(kernel: Any) -> Dict[str, List[Any]]:
    from xylarium.kernel import syntropy
    return syntropy._peoples(kernel)


def _live_ages(kernel: Any, who: str, worlds: List[Any], logs: List[str]) -> Optional[Dict[str, Any]]:
    """Pass 1: a people's own ages through the stretch it has not lived, up to its fall or its crossing."""
    from xylarium.kernel import biosphere, clocks, fertility, history
    st = stats(kernel)
    home = max(worlds, key=lambda p: p.population)
    arisen = home.society.get("arisen") or {}
    if "epoch" not in arisen:
        return None
    rec = st["of"].setdefault(who, {"advanced": 0.0, "passed": [], "dominion": len(worlds), "reach": 0.0})
    lived = (kernel.cycle_count - int(arisen.get("cycle", kernel.cycle_count))) / 100.0
    own_now = clocks.now(kernel, who)                         # its own now: the galaxy's once their clocks have met
    deficit = (own_now - float(arisen["epoch"])) * 1e9 - lived - rec["advanced"]
    gen = max(1.0, fertility.generation_of(kernel, home))
    gens = deficit / gen
    if "hist" not in rec:                                     # its history is kept from its first year
        _history(kernel, who, rec, _stage(kernel, who, home), lived, gen, _speed(kernel, home),
                 fall_per_generation(kernel, who, home))
    if gens < MIN_GENERATIONS and (guided(kernel, who) or not _due(kernel, who, home, rec, lived, gen)):
        return None                                           # nothing to carry, and no turning of its own is due
    gens = max(gens, 1e-9)
    rec["advanced"] += deficit
    speed = _speed(kernel, home)
    fall_rate = fall_per_generation(kernel, who, home)
    stage = _stage(kernel, who, home)
    hist = _history(kernel, who, rec, stage, lived, gen, speed, fall_rate)
    fall_rate = hist["rate"]                                  # set at its last turning: its knowledge since counts at
                                                              # its next one, so its hazard does not depend on the cut
    lapse = clocks.lapse(kernel, home.sector_id)
    epoch_of = lambda tt: own_now - (gens - tt) * gen / 1e9   # noqa: E731
    job: Dict[str, Any] = {"who": who, "worlds": worlds, "home": home, "rec": rec, "hist": hist, "gens": gens,
                           "gen": gen, "fell": None, "cross": None, "lapse": lapse, "own_now": own_now,
                           "grown_from": max(1, rec["dominion"]) * max(1, biosphere.carrying_capacity(kernel, home))}
    t = 0.0                                                   # generations lived in this stretch
    ruled_from = 0.0 if STAGES.index(stage) >= STAGES.index("state") else None   # since when it has had a few
    while t < gens:
        left = gens - t
        nxt = STAGES.index(stage) + 1
        if nxt >= len(STAGES):
            job["cross"] = t                                  # among the stars: its dominion is lived with the others'
            break
        from xylarium.kernel import technology as _tech
        kind, span = _next_kind(kernel, who, home, worlds, stage)
        to_fall = (hist["E"] - hist["H"]) / fall_rate         # generations until its hazard comes due
        to_turn = float("inf") if kind is None else \
            max(0.0, (_threshold(kernel, who, hist, kind, span) - hist["P"]) / speed)
        if to_fall <= to_turn and to_fall < left:
            job["fell"] = t + to_fall
            hist["H"] = hist["E"]
            hist["P"] += speed * to_fall
            break
        if to_turn >= left:
            hist["P"] += speed * left
            hist["H"] += fall_rate * left
            break
        t += to_turn
        hist["P"] += speed * to_turn
        hist["H"] += fall_rate * to_turn
        hist["since"] = hist["P"]                             # the next wait is counted from here
        fall_rate = hist["rate"] = fall_per_generation(kernel, who, home)
        if kind in ("embodiment", "genetics"):
            _tech.stats(kernel)["of"].setdefault(who, {})[kind] = kernel.cycle_count
            speed = _speed(kernel, home)                      # it has hands, or can rewrite itself, now
            continue
        stage = kind
        hist["stage"] = stage
        if stage == "state":
            ruled_from = t
        _grant(kernel, who, home, nxt)                        # what that stage brings, it holds from then on
        speed = _speed(kernel, home)
        rec["passed"].append(stage)
        kind_ev = "ASCENT" if stage == "crossed" else "ERA"
        text = {"farm": "takes up farming", "state": "founds a state", "works": "raises its first great works",
                "yards": "builds yards that can launch to orbit", "crossed": "folds space and crosses to the stars"}
        history.event(kernel, kind_ev, f"The {who.split(':', 1)[-1]} {text[stage]}", actors=[who], planet=home,
                      cause="at the level of history",
                      data={"epoch": round(epoch_of(t), 6), "stage": stage})
    job.update(stage=stage, speed=speed, fall_rate=fall_rate, ruled_from=ruled_from, epoch_of=epoch_of)
    if job["cross"] is not None:                              # what is left of the stretch is lived among the stars
        rest = gens - job["cross"]
        hist["P"] += speed * rest
    return job


def _coord(job: Dict[str, Any], tt: float) -> float:
    """A point of a people's stretch (generations into it) on the coordinate clock."""
    return job["epoch_of"](tt) / max(1e-12, job["lapse"])


def _settle(kernel: Any, jobs: List[Dict[str, Any]], logs: List[str]) -> None:
    """Pass 2: the crossed peoples' dominions together, in the order things happen on the coordinate clock - each
    one's fall shared over the systems it holds as its bubble grows, meets, encloses and is enclosed."""
    from xylarium.kernel import settling
    if not jobs:
        return
    for j in jobs:
        new = j["who"] not in settling.stats(kernel)
        b = settling.begin(kernel, j["who"], j["home"], _coord(j, j["cross"]), j["gen"])
        # its dominion's time is the generations it has lived since it crossed, on the coordinate clock - the same
        # epochs as its own now in any run, and the same history however its stretches are cut
        x0 = 0.0 if new else float(j["hist"].get("X", 0.0))
        gyr = j["gen"] / 1e9 / max(1e-12, j["lapse"])
        j["x1"] = x0 + (j["gens"] - j["cross"])
        j.update(t=b["crossed"] + x0 * gyr, end=b["crossed"] + j["x1"] * gyr,
                 W=float(j["hist"]["W"]), need=j["hist"]["E"] - j["hist"]["H"],
                 rate=j["fall_rate"] * 1e9 * j["lapse"] / j["gen"], g=b["g"])
    from xylarium.kernel import ascendance
    for j in jobs:
        b = settling.stats(kernel)[j["who"]]
        if not ascendance.free(kernel, j["who"]) and j["fell"] is None and j["end"] > j["t"]:
            b.setdefault("pauses", []).append([j["t"], j["end"]])    # held at home by its steward: its front waits
    t_end = max(j["end"] for j in jobs)
    while True:
        meet = settling.next_contact(kernel, t_end)
        horizon = meet[2][0] if meet is not None else t_end
        first = None
        for j in jobs:
            if j["fell"] is not None:
                continue
            got = _run(kernel, j, min(horizon, j["end"]), commit=False)
            if got is not None and (first is None or got < first[0]):
                first = (got, j)
        if first is not None and (meet is None or first[0] <= meet[2][0]):
            t_f, j = first
            _run(kernel, j, t_f, commit=True)
            j["fell"] = t_f
            j["hist"]["H"] = j["hist"]["E"]
            settling.fall(kernel, j["who"], t_f)
            continue
        if meet is None:
            break
        settling.meet(kernel, meet[0], meet[1], meet[2], logs)
    for j in jobs:
        if j["fell"] is None:
            _run(kernel, j, j["end"], commit=True)
            j["hist"]["X"] = j["x1"]
            j["hist"]["W"] = j["W"]
            j["rec"]["dominion"] = int(j["W"])
            j["rec"]["reach"] = round(settling.radius(settling.stats(kernel)[j["who"]], j["end"]), 6)


def _run(kernel: Any, j: Dict[str, Any], until: float, commit: bool) -> Optional[float]:
    """Run a crossed people's hazard from where it stands to `until` (coordinate Gyr), piecewise between the epochs
    where what it can hold jumps. Returns the epoch it falls, if it does; with commit, keeps where it got to."""
    from xylarium.kernel import settling
    t, w, need = j["t"], j["W"], j["need"]
    if until <= t:
        return None
    marks = [t] + settling.breaks(kernel, j["who"], t, until) + [until]
    fell = None
    for ta, tb in zip(marks, marks[1:]):
        cap = lambda tt, ta=ta: settling.held(kernel, j["who"], ta + tt)         # noqa: E731
        w = min(w, cap(1e-12))
        ran, at = _dominion_hazard(j["rate"], w, tb - ta, cap, need, g=j["g"])
        if at is not None:
            fell = ta + at
            need = 0.0
            w = min(w * math.exp(min(700.0, j["g"] * at)), cap(at))
            t = fell
            break
        need -= ran
        w = min(w * math.exp(min(700.0, j["g"] * (tb - ta))), cap(tb - ta))
        t = tb
    if commit:
        j["hist"]["H"] = j["hist"]["E"] - need if fell is None else j["hist"]["E"]
        j.update(t=t, W=w, need=need)
    return fell


def _books(kernel: Any, j: Dict[str, Any], logs: List[str]) -> None:
    """Pass 3: a people's world, its history's light and dark, and what it learned, for the stretch it lived."""
    from xylarium.kernel import biosphere, knowledge
    st = stats(kernel)
    who, home, rec, gens, gen = j["who"], j["home"], j["rec"], j["gens"], j["gen"]
    fell = j["fell"]
    if fell is not None and j.get("cross") is not None:      # a dominion's fall is dated on the coordinate clock
        fell_gens = j["gens"] - (j["end"] - fell) * 1e9 * j["lapse"] / gen
        fell_epoch = fell * j["lapse"]
    elif fell is not None:
        fell_gens, fell_epoch = fell, j["epoch_of"](fell)
    if fell is None:
        _apply(kernel, who, home, j["stage"])
    # its history as it lived its ages: its own work, and - once it has a state - what its few took of it, weighed
    # against the growth it made in the stretch (its worlds and its land's room, a year)
    civ = getattr(home, "civilization", None)
    if civ is not None:
        from xylarium.kernel import alignment, memory, rent
        lived_gens = fell_gens if fell is not None else gens
        alignment.fade(civ, lived_gens, memory.character_keep(kernel, who, home))     # its telling fades
        ruled_from = j["ruled_from"]
        ruled = max(0.0, lived_gens - ruled_from) if ruled_from is not None and ruled_from < lived_gens else 0.0
        grown_to = max(1, rec["dominion"]) * max(1, biosphere.carrying_capacity(kernel, home))
        growth = max(0.0, math.log(grown_to / j["grown_from"])) / max(1.0, lived_gens * gen)
        rho = rent.choose(kernel, home, ruled=True, growth=growth) if ruled > 0 else 0.0
        n = float(home.population)
        ss = float(home.society.get("self_sufficiency", 1.0) or 1.0)
        lost = n * ruled * max(0.0, rent.starved(ss, rho) - rent.starved(ss, 0.0))
        alignment.flow(civ, light=n * lived_gens - lost, dark=lost, why="work and rent")
    if fell is not None:
        logs.append(_fall(kernel, who, j["worlds"], fell_epoch))
        st["falls"] += 1
        return
    # what it knows has grown with its ages: its thinkers' effort a year (knowledge.effort, as the engine counts it)
    # over the years carried, shared among what it already studies as it studies it - summed, never compounded, so
    # however its time is cut it learns the same
    known = {d: knowledge.stocks(kernel, who).get(d, 0.0) for d in knowledge.DOMAINS}
    total = sum(v for v in known.values() if v > 0)
    if total > 0:
        years = gens * gen
        per_year = knowledge.effort(kernel, home)
        for d, v in known.items():
            if v > 0:
                knowledge.learn(kernel, who, d, per_year * years * v / total, why="annals")


def POLICY_CARDS_NAME(card: str) -> str:
    from xylarium.config import POLICY_CARDS
    return POLICY_CARDS.get(card, {}).get("name", card)


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    crossed = sum(1 for r in st["of"].values() if "crossed" in r["passed"])
    return {"peoples": len(st["of"]), "crossed": crossed, "falls": st["falls"], "wars": st["wars"],
            "pacts": st.get("pacts", 0),
            "dominion_worlds": sum(r["dominion"] for r in st["of"].values() if "crossed" in r["passed"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="annals", state=lambda: {"of": {}, "met": {}, "falls": 0, "wars": 0, "pacts": 0},
                             season=season, summary=summary))
