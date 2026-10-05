"""
Xylarium zones: where something is there to see - the places the engine steps, and the places it only evaluates.

Every world's physics that is a closed-form function of time (its orbit, its star's life) needs no stepping: it is
computed on demand, wherever it is read, and gives the same answer whenever it is read. Only stepped state must be
advanced every tick - and the work of a tick need only visit the places where stepped state lives or is watched:

  * PEOPLED: sectors with a living world (a people's world, a captain's holding).
  * WATCHED: those, and every sector with a port - where ships trade and someone looks up at the sky.

Both are read once a cycle (memoised), so the many laws that ask "is anyone here?" ask a set, not the map. A zone
never changes what is true: a law that skips a place on its account must be one whose work there would do nothing
(no people to move, no sky anyone reads but on demand).
"""

from typing import Any, FrozenSet


def _scan(kernel: Any) -> tuple:
    peopled, watched = set(), set()
    for sid, sec in kernel.sectors.items():
        if getattr(sec, "port", None) is not None:
            watched.add(sid)
        for q in sec.planets:
            if q.population > 0 or q.owner_id:
                peopled.add(sid)
                watched.add(sid)
                break
    return frozenset(peopled), frozenset(watched)


def _both(kernel: Any) -> tuple:
    if not hasattr(kernel, "caches"):
        return _scan(kernel)
    from xylarium.kernel import cache
    return cache.memo(kernel, "zones", "both", lambda: _scan(kernel), epoch=kernel.cycle_count)


def peopled(kernel: Any) -> FrozenSet[int]:
    """Sectors with a living or held world, this cycle."""
    return _both(kernel)[0]


def watched(kernel: Any) -> FrozenSet[int]:
    """Sectors with a living or held world or a port, this cycle."""
    return _both(kernel)[1]
