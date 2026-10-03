"""
Xylarium tempo: how fast deep time runs for each clock year - set by the living, not chosen.

The universe's truth is a function of deep time (creation.py, worlds.py); the clock is only the camera that films
it, and its speed changes nothing it films. So it runs as fast as it can without stepping over what the living are
in the middle of - the rule an integrator follows (a Courant condition): no clock year may hold more than a share
(1 / FRAMES) of the shortest wait any living people has to its next turning - the next bridge of its history
(annals.SPANS, in its own generations, at its own minds' pace) or its fall, whichever it expects sooner. A people
whose world holds it from the sky has no next bridge, only its fall; a people among the stars is not waiting on a
bridge, and does not hold the clock back. With no people in the middle of its history, deep time runs at the pace
chosen at genesis (cosmos.ceiling): the galaxy turns fast between minds and slows to watch each one rise.

Changes of rate are kept as segments (cosmos.set_rate), so deep time is exactly accumulated; a change smaller than
a factor of two is not worth a new segment.
"""

import math
from typing import Any, Dict, List, Optional

FRAMES = 10.0                   # clock years the camera gives the shortest turning in view (a resolution, declared)


def wait_years(kernel: Any, who: str, home: Any) -> Optional[float]:
    """The years a living people expects to wait for its next turning (None: it holds nothing back)."""
    from xylarium.kernel import annals, fertility
    stage = annals._stage(kernel, who, home)
    if stage == "crossed":
        return None
    gen = max(1.0, fertility.generation_of(kernel, home))
    nxt = annals.STAGES.index(stage) + 1
    fall = gen / annals.FALL_PER_GENERATION
    if annals.STAGES[nxt] == "yards" and not annals._can_reach_orbit(kernel, who, home):
        return fall
    from xylarium.kernel import technology
    if annals.STAGES[nxt] == "works" and not technology.embodied(kernel, who, home):
        return min(fall, annals.EMBODIMENT_SPAN / annals._speed(kernel, home) * gen)
    return min(fall, annals.SPANS[annals.STAGES[nxt]] / annals._speed(kernel, home) * gen)


def desired(kernel: Any) -> float:
    from xylarium.kernel import cosmos, syntropy
    top = cosmos.ceiling(kernel)
    waits = []
    for who, worlds in syntropy._peoples(kernel).items():
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
    from xylarium.kernel import cosmos
    want = desired(kernel)
    if want < cosmos.ruler(kernel):
        cosmos.set_rate(kernel, want)
        stats(kernel)["changes"] += 1


def season(kernel: Any) -> List[str]:
    """Once a year the clock is set to the living."""
    from xylarium.kernel import cosmos
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // 25) % 4:
        return []
    want = desired(kernel)
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
