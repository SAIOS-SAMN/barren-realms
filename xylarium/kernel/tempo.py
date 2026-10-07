"""
Xylarium tempo: how fast deep time runs for each clock year - the one camera the whole galaxy is filmed by.

The universe's truth is a function of deep time (creation.py, worlds.py); the clock is only the camera that films
it, and its speed changes nothing it films. So it runs as fast as it can without stepping over what the living are
in the middle of - the rule an integrator follows (a Courant condition): no clock year may hold more than a share
(1 / FRAMES) of the shortest wait any living people has to its next turning - the next bridge of its history
(annals.SPANS, in its own generations, at its own minds' pace) or its fall, whichever it expects sooner. A people
whose world holds it from the sky has no next bridge, only its fall; a people among the stars waits on its
dominion's next e-fold of settlement - so once any people is among the stars, the galaxy runs at the pace of its
expansion. With no people in the middle of its history, deep time runs at the pace
chosen at genesis (cosmos.ceiling): the galaxy turns fast between minds and slows to watch each one rise. It is one
rate for every place (clocks.py: a place's own time is its lapse times cosmic time): the worlds all spin on one
coordinated clock. It slows only for the peoples a seat watches - an input, the same however the engine holds the
rest - so what it films never depends on what is held folded.

Changes of rate are kept as segments (cosmos.set_rate), so deep time is exactly accumulated; a change smaller than
a factor of two is not worth a new segment.

All of that is the DEEP ERA. Once the universe is opened to live play (cosmos.open_universe) the camera is retired:
the clock is locked to the captains' scale - a clock year is a standard year - and no seat speeds it or slows it;
every seat above the captains acts on its own cadence on that one clock.
"""

import math
from typing import Any, Dict, List, Optional

FRAMES = 10.0                   # clock years the camera gives the shortest turning in view (a resolution, declared)


def wait_years(kernel: Any, who: str, home: Any) -> Optional[float]:
    """The years a living people expects to wait for its next turning (None: it holds nothing back)."""
    from xylarium.kernel import annals, fertility
    stage = annals._stage(kernel, who, home)
    gen = max(1.0, fertility.generation_of(kernel, home))
    if stage == "crossed":
        # among the stars its next turning is its dominion's next e-fold of settlement while it grows freely; once it
        # holds all its front reaches, its fall, shared over the worlds it holds (settling.py)
        from xylarium.kernel import settling
        w = float(((annals.stats(kernel)["of"].get(who) or {}).get("hist") or {}).get("W", 1.0))
        if who in settling.stats(kernel) and w >= annals.dominion_cap(kernel, who, home):
            return gen * w / annals.fall_per_generation(kernel, who, home)
        return gen / settling.settle_rate(kernel, home) / annals._speed(kernel, home)
    nxt = annals.STAGES.index(stage) + 1
    fall = gen / annals.fall_per_generation(kernel, who, home)
    if annals.STAGES[nxt] == "yards" and not annals._can_reach_orbit(kernel, who, home):
        return fall
    from xylarium.kernel import mastery
    if annals.STAGES[nxt] == "crossed" and not mastery.genome_ready(kernel, who, [home]):
        return min(fall, annals.GENETICS_SPAN / annals._speed(kernel, home) * gen)
    from xylarium.kernel import technology
    if annals.STAGES[nxt] == "works" and not technology.embodied(kernel, who, home):
        return min(fall, annals.EMBODIMENT_SPAN / annals._speed(kernel, home) * gen)
    return min(fall, annals.SPANS[annals.STAGES[nxt]] / annals._speed(kernel, home) * gen)


def seated(kernel: Any) -> set:
    """The peoples a seat watches (a player's or an AI's: ages.bind) - the same whatever the engine holds folded."""
    from xylarium.kernel import ages
    try:
        return {rec.get("people") for rec in (ages.stats(kernel).get("stewards") or {}).values() if rec.get("people")}
    except Exception:
        return set()


def desired(kernel: Any) -> float:
    """The camera's rate: as fast as the genesis pace allows, slowed to watch each people a seat watches through its
    next turning. Peoples no seat watches are carried by the annals at the level of history, as ever."""
    from xylarium.kernel import cosmos, syntropy
    top = cosmos.ceiling(kernel)
    waits = []
    watched = seated(kernel)
    for who, worlds in syntropy._peoples(kernel).items():
        if who not in watched:
            continue
        home = max(worlds, key=lambda p: p.population)
        if not (home.society.get("arisen") or {}):
            continue
        w = wait_years(kernel, who, home)
        if w is not None:
            waits.append(w)
    if not waits:
        return top
    return min(top, max(1.0, min(waits) / FRAMES))


def wake(kernel: Any) -> None:
    """A mind has arisen: the clock is set to the living at once - not a year later, when a year at the galaxy's
    pace would already have carried the new people through its whole history."""
    from xylarium.kernel import clocks, cosmos
    if cosmos.live(kernel):
        return                                                # the live era: the clock is the captains', always
    if clocks.away_pace(kernel):
        return                                                # its watcher has looked away; the annals carry it
    want = desired(kernel)
    if want < cosmos.ruler(kernel):
        cosmos.set_rate(kernel, want)
        stats(kernel)["changes"] += 1


def season(kernel: Any) -> List[str]:
    """Once a year the clock is set to the living."""
    from xylarium.kernel import cosmos
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // 25) % 4:
        return []
    if cosmos.live(kernel):                                   # the live era: locked to the captains' scale
        if cosmos.ruler(kernel) != cosmos.LIVE_YEARS_PER_YEAR:
            cosmos.set_rate(kernel, cosmos.LIVE_YEARS_PER_YEAR)
        return []
    want = desired(kernel)
    from xylarium.kernel import clocks
    coarse = clocks.away_pace(kernel)
    if coarse:
        want = max(want, coarse)                              # a watcher has looked away: the galaxy is filmed coarsely
    now = cosmos.ruler(kernel)
    if not cosmos.stats(kernel).get("tempo") or max(want / now, now / want) >= 2.0:
        cosmos.set_rate(kernel, want)
        stats(kernel)["changes"] += 1
    return []


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "tempo")


def summary(kernel: Any) -> Dict[str, Any]:
    from xylarium.kernel import cosmos
    return {"deep_years_per_year": cosmos.ruler(kernel), "changes": stats(kernel)["changes"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="tempo", state=lambda: {"changes": 0}, season=season, summary=summary))
