"""
Xylarium annals: a people's long ages, lived at the level of history while the galaxy's deep time runs on.

The engine lives a people year by year on the universal clock, while the galaxy turns on deep time - at the teeming
pace ten million years pass for every clock year. Without the annals a people woken a billion years ago would have
lived only a hundred of its own years: the oldest minds in the galaxy would be its youngest peoples. Each year the
annals close that gap: every people is carried, at the level of history, through the deep years that have passed
since it woke and that it has not yet lived, along the same bridges the full engine carries it across - foraging,
farming, a state, works, yards, the crossing to the stars - each an exponential wait whose mean is that bridge's
span in the people's own generations (measured by tools/bridges.py from the engine itself, scaled by how fast its
minds think: laws.cognition's speed). Peoples also fall: a hazard per generation, measured the same way.

What a people lives in its annals it keeps: its way, its works, its yards, its knowledge, its crossing - and its
people grows to what its world now feeds. Once across, its dominion grows (worlds settled per generation, up to the star systems within
its network's reach: spheres.py, paid in passages by its power - so no faster than its ships travel), and where two networks meet the style of the one
arriving decides between a bond and a realm war (spheres.py, realmwars.py). A fallen people leaves ruins on its homeworld (archaeology.py: the deep strata of an ANCIENT
culture) and its name in the galaxy's chronicle. The galaxy's lore is these annals: every era, crossing, war and
fall, dated in deep time (history.py: ERA, ASCENT, DOMINION, GALACTIC_WAR, FALL).
"""

import functools
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
FALL_PER_GENERATION = 2.0e-4    # a one-world people's hazard of falling, per generation (declared: a mean of ~5,000
                                # generations); among the stars it is shared out over the worlds it holds
DOMINION_PER_GENERATION = 0.01  # worlds a crossed people settles per generation, per world it holds (declared)
STARS_PER_SYSTEM = 4.0 / 3.0    # a third of systems are binaries (creation.BINARY_SHARE)
DISC_HALF_THICKNESS_PC = 300.0  # the thin disc's scale height (measured): a reach wider than it settles a slab
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
    history.event(kernel, "FALL", f"The {name} fall", actors=[who], planet=home,
                  cause=f"{epoch:.3f} Gyr after the Big Bang, at the level of history; its ruins lie on "
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


def _systems_per_pc3(kernel: Any, home: Any = None) -> float:
    """Star systems per pc^3 where a people began (encounters.components: disc, bulge and nucleus)."""
    from xylarium.kernel import cosmos, encounters
    r = cosmos.R0_KPC
    if home is not None and kernel is not None and cosmos.is_cosmic(kernel):
        g = cosmos.stats(kernel)["place"].get(str(home.sector_id)) or {}
        r = float(g.get("r", r))
    return sum(n for n, _ in encounters.components(r)) / STARS_PER_SYSTEM


@functools.lru_cache(maxsize=1)
def galaxy_systems() -> float:
    """Every star system the galaxy holds: its exponential disc (2 pi R_d^2 Sigma(0)), bulge and nuclear cluster, at the
    Kroupa mean star and a third of systems binaries."""
    from xylarium.kernel import cosmos, encounters, geometry
    suns = 2.0 * math.pi * cosmos.R_D_KPC ** 2 * geometry.surface_density(0.0) + encounters.BULGE_M + encounters.NUCLEUS_M
    return suns / encounters.MEAN_STAR / STARS_PER_SYSTEM


def _systems_within(n: float, reach_pc: float) -> float:
    """The systems within reach_pc: a sphere cut by the disc's thickness (exact: 2 pi H (R^2 - H^2/3) once wider),
    and never more than the galaxy holds."""
    h = DISC_HALF_THICKNESS_PC
    v = 4.0 / 3.0 * math.pi * reach_pc ** 3 if reach_pc <= h else 2.0 * math.pi * h * (reach_pc ** 2 - h * h / 3.0)
    return min(n * v, galaxy_systems())


def front_pc(n: float, since: float) -> float:
    """How far a people's settling front has come `since` generations after it crossed: each settlement is a hop to
    the nearest system (n^-1/3), and it settles at DOMINION_PER_GENERATION - so the front moves a hop for each
    settlement it can make, and no faster than that (at the Sun's density and 25-year generations ~1.7 pc per
    2,500 years: the disc's 10 kpc in some 15 Myr)."""
    return n ** (-1.0 / 3.0) * (1.0 + DOMINION_PER_GENERATION * max(0.0, since))


def dominion_cap(kernel: Any, who: str, home: Any = None, since: Optional[float] = None) -> float:
    """How many worlds a dominion can hold: the star systems within its settling front (front_pc, `since` its
    crossing - by default as far as its annals have carried it), or within its network's reach where the engine has
    built one (spheres.radius); never less than the worlds it already holds."""
    from xylarium.kernel import spheres
    n = _systems_per_pc3(kernel, home)
    rec = (stats(kernel)["of"].get(who) or {}) if kernel is not None else {}
    if since is None:
        since = float((rec.get("hist") or {}).get("X", 0.0))
    reach_pc = max(front_pc(n, since), spheres.radius(kernel, who) * 1000.0 if kernel is not None else 0.0)
    return max(1.0, float(rec.get("dominion", 1)), _systems_within(n, reach_pc))


def _dominion_hazard(rate: float, w0: float, gens: float, cap_of: Any, need: Optional[float] = None) -> tuple:
    """The hazard a dominion of w0 worlds runs over `gens` generations as it settles, its fall shared over its worlds:
    they grow e^(g t), but never past the systems its front has reached (cap_of(t), growing as the front does).
    While it grows freely, f/(w0 g)(1 - e^-g t); once its front binds it, the integral of f/cap, taken in
    ln(1 + g t) where the front's volume is smooth. With `need`, also when that much hazard has been run (else None).
    Returns (hazard run, generations until `need`)."""
    g, w0 = DOMINION_PER_GENERATION, max(1.0, w0)
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
    ran, steps = free, 256
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
    """Once a year every people lives the deep years it has not yet lived."""
    from xylarium.kernel import cosmos, fertility, history, knowledge, scheduler, sustenance, syntropy
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    now = cosmos.deep_gyr(kernel)
    logs: List[str] = []
    peoples = syntropy._peoples(kernel)
    for who in sorted(peoples):
        worlds = peoples[who]
        home = max(worlds, key=lambda p: p.population)
        arisen = home.society.get("arisen") or {}
        if "epoch" not in arisen:
            continue
        rec = st["of"].setdefault(who, {"advanced": 0.0, "passed": [], "dominion": len(worlds), "reach": 0.0})
        lived = (kernel.cycle_count - int(arisen.get("cycle", kernel.cycle_count))) / 100.0
        from xylarium.kernel import clocks
        own_now = clocks.now(kernel, who)                     # its own now: the galaxy's once their clocks have met
        deficit = (own_now - float(arisen["epoch"])) * 1e9 - lived - rec["advanced"]
        gen = max(1.0, fertility.generation_of(kernel, home))
        gens = deficit / gen
        if "hist" not in rec:                                 # its history is kept from its first year
            _history(kernel, who, rec, _stage(kernel, who, home), lived, gen, _speed(kernel, home),
                     FALL_PER_GENERATION / resilience(kernel, who))
        if gens < MIN_GENERATIONS and (guided(kernel, who) or not _due(kernel, who, home, rec, lived, gen)):
            continue                                          # nothing to carry, and no turning of its own is due
        gens = max(gens, 1e-9)
        rec["advanced"] += deficit
        speed = _speed(kernel, home)
        fall_rate = FALL_PER_GENERATION / resilience(kernel, who)
        stage = _stage(kernel, who, home)
        hist = _history(kernel, who, rec, stage, lived, gen, speed, fall_rate)
        fall_rate = hist["rate"]                              # set at its last turning: its knowledge since counts at
                                                              # its next one, so its hazard does not depend on the cut
        t = 0.0                                               # generations lived in this stretch
        epoch_of = lambda tt: own_now - (gens - tt) * gen / 1e9   # noqa: E731
        fell = None
        crossed_at = 0.0 if stage == "crossed" else None
        ruled_from = 0.0 if STAGES.index(stage) >= STAGES.index("state") else None   # since when it has had a few
        while t < gens:
            left = gens - t
            nxt = STAGES.index(stage) + 1
            if nxt >= len(STAGES):
                # among the stars a people falls only if all its worlds do: its hazard is the one-world hazard over
                # its dominion, which grows as it settles - H = f / (W0 g) (1 - e^-g T) over what is left of T
                need = hist["E"] - hist["H"]
                x0 = hist.get("X", 0.0) if crossed_at == 0.0 and t == 0.0 else 0.0
                hist["X"] = x0
                from xylarium.kernel import spheres
                n_sys = _systems_per_pc3(kernel, home)
                net_pc = spheres.radius(kernel, who) * 1000.0
                floor = max(1.0, float(rec.get("dominion", 1)))
                ran, until = _dominion_hazard(fall_rate, hist["W"], left, lambda tt: max(
                    floor, _systems_within(n_sys, max(net_pc, front_pc(n_sys, x0 + tt)))), need)
                if until is not None:
                    fell = t + until
                    hist["H"] = hist["E"]
                else:
                    hist["H"] += ran
                hist["P"] += speed * left
                break
            from xylarium.kernel import technology as _tech
            kind, span = _next_kind(kernel, who, home, worlds, stage)
            to_fall = (hist["E"] - hist["H"]) / fall_rate     # generations until its hazard comes due
            to_turn = float("inf") if kind is None else \
                max(0.0, (_threshold(kernel, who, hist, kind, span) - hist["P"]) / speed)
            if to_fall <= to_turn and to_fall < left:
                fell = t + to_fall
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
            hist["since"] = hist["P"]                         # the next wait is counted from here
            fall_rate = hist["rate"] = FALL_PER_GENERATION / resilience(kernel, who)
            if kind in ("embodiment", "genetics"):
                _tech.stats(kernel)["of"].setdefault(who, {})[kind] = kernel.cycle_count
                speed = _speed(kernel, home)                  # it has hands, or can rewrite itself, now
                continue
            stage = kind
            hist["stage"] = stage
            if stage == "state":
                ruled_from = t
            _grant(kernel, who, home, nxt)                    # what that stage brings, it holds from then on
            speed = _speed(kernel, home)
            rec["passed"].append(stage)
            if stage == "crossed":
                crossed_at = t
            kind_ev = "ASCENT" if stage == "crossed" else "ERA"
            text = {"farm": "takes up farming", "state": "founds a state", "works": "raises its first great works",
                    "yards": "builds yards that can launch to orbit", "crossed": "folds space and crosses to the stars"}
            history.event(kernel, kind_ev, f"The {who.split(':', 1)[-1]} {text[stage]}", actors=[who], planet=home,
                          cause=f"at the level of history, {epoch_of(t):.4f} Gyr after the Big Bang",
                          data={"epoch": round(epoch_of(t), 6), "stage": stage})
        from xylarium.kernel import biosphere
        grown_from = max(1, rec["dominion"]) * max(1, biosphere.carrying_capacity(kernel, home))
        if fell is None:
            if stage == "crossed":
                since = max(0.0, gens - (crossed_at or 0.0))
                hist["X"] = hist.get("X", 0.0) + since            # generations its front has been moving
                hist["W"] = min(dominion_cap(kernel, who, home, since=hist["X"]),
                                hist["W"] * math.exp(min(50.0, DOMINION_PER_GENERATION * since)))
                rec["dominion"] = int(hist["W"])
                from xylarium.kernel import spheres
                rec["reach"] = spheres.radius(kernel, who)       # its network's reach, paid in passages (spheres.py)
            _apply(kernel, who, home, stage)
        # its history as it lived its ages: its own work, and - once it has a state - what its few took of it, weighed
        # against the growth it made in the stretch (its worlds and its land's room, a year)
        civ = getattr(home, "civilization", None)
        if civ is not None:
            from xylarium.kernel import alignment, memory, rent
            lived_gens = fell if fell is not None else gens
            alignment.fade(civ, lived_gens, memory.character_keep(kernel, who, home))     # its telling fades
            ruled = max(0.0, lived_gens - ruled_from) if ruled_from is not None and ruled_from < lived_gens else 0.0
            grown_to = max(1, rec["dominion"]) * max(1, biosphere.carrying_capacity(kernel, home))
            growth = max(0.0, math.log(grown_to / grown_from)) / max(1.0, lived_gens * gen)
            rho = rent.choose(kernel, home, ruled=True, growth=growth) if ruled > 0 else 0.0
            n = float(home.population)
            ss = float(home.society.get("self_sufficiency", 1.0) or 1.0)
            lost = n * ruled * max(0.0, rent.starved(ss, rho) - rent.starved(ss, 0.0))
            alignment.flow(civ, light=n * lived_gens - lost, dark=lost, why="work and rent")
        if fell is not None:
            logs.append(_fall(kernel, who, worlds, epoch_of(fell)))
            st["falls"] += 1
            continue
        # what it knows has grown with its ages: its thinkers' effort a year (knowledge.effort, as the engine counts
        # it) over the years carried, shared among what it already studies as it studies it - summed, never
        # compounded, so however its time is cut it learns the same
        known = {d: knowledge.stocks(kernel, who).get(d, 0.0) for d in knowledge.DOMAINS}
        total = sum(v for v in known.values() if v > 0)
        if total > 0:
            years = gens * gen
            per_year = knowledge.effort(kernel, home)
            for d, v in known.items():
                if v > 0:
                    knowledge.learn(kernel, who, d, per_year * years * v / total, why="annals")
    return logs


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
