"""
Xylarium lifeline: life on a world is a running process; the schedule is only its forecast.

The Big Bang fixes every world's trajectory (creation.py): its star, its orbit, its air and seas at each age. Life on
it is not part of that trajectory - it is living things, climbing rung by rung on the world's own stream of chance
(life.climb). The schedule (creation.schedule) resolves each world's climb ahead along its undisturbed trajectory:
what its life would do if nothing interfered. That is a forecast, and it holds only while nothing does.

When a mind acts on a world (imprint.py: a strike, a breaking, its air taken or given, its ground reworked), the
world's life is re-resolved from that moment, from the world as it now stands:

  ENDED     the world no longer holds a living medium (its air gone, the world broken apart): the climb stops at
            the rung it had reached, and the mind it would have raised never comes (LIFE_ENDED)
  REDRAWN   it still holds one: the rungs already climbed are kept, and the rest of the climb is drawn afresh from
            now, on the world's stream at that moment (each rung an exponential wait, so the waits from now have the
            same law as before - but not the same draws: the disturbance changed the living things' future, never
            the world's physics). If the new climb no longer reaches a mind within the world's window, or the
            world as it will be then cannot feed a people, none comes.

The forecast is never consulted by any mind in play; it is how the engine keeps the undisturbed galaxy without
living every world year by year.
"""

from typing import Any, Dict, List, Optional, Tuple


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "lifeline")


def key(cell: Any, k: int, w: int) -> str:
    return f"{int(cell[0])},{int(cell[1])}:{int(k)}:{int(w)}"


def key_of(rec: Dict[str, Any]) -> str:
    return key(rec["cell"], rec["k"], rec.get("w", 0))


def _forecast(seed: Any) -> Dict[str, Dict[str, Any]]:
    from xylarium.kernel import creation
    ck = ("lifeline_index", seed)
    if ck not in creation._CACHE:
        creation._CACHE[ck] = {key_of(m): m for m in creation.schedule(seed)["minds"]}
    return creation._CACHE[ck]


def locate(kernel: Any, planet: Any) -> Optional[Tuple[Tuple[int, int], int, int]]:
    from xylarium.kernel import cosmos
    g = cosmos.stats(kernel)["place"].get(str(planet.sector_id))
    sec = kernel.sectors.get(planet.sector_id)
    if not g or "cell" not in g or sec is None or planet not in sec.planets:
        return None
    return (int(g["cell"][0]), int(g["cell"][1])), int(g["k"]), sec.planets.index(planet)


def current(kernel: Any, k: str) -> Optional[Dict[str, Any]]:
    """The mind a world's life is now headed for (None: none, or its life has ended)."""
    from xylarium.kernel import cosmos
    st = stats(kernel)
    if k in st["ended"]:
        return None
    if k in st["redrawn"]:
        return st["redrawn"][k]
    return _forecast(cosmos.cosmos_seed(kernel)).get(k)


def overridden(kernel: Any, rec: Dict[str, Any]) -> bool:
    """Is this forecast mind no longer what its world's life is headed for?"""
    if "lifeline" not in getattr(kernel, "state", {}) or rec.get("redrawn") is not None:
        return False
    k = key_of(rec)
    st = stats(kernel)
    return k in st["ended"] or k in st["redrawn"]


def due(kernel: Any, now: float) -> List[Dict[str, Any]]:
    """Redrawn minds whose time has come (taken off the list as they are handed over)."""
    if "lifeline" not in getattr(kernel, "state", {}):
        return []
    st = stats(kernel)
    out = sorted((r for r in st["redrawn"].values() if r["epoch"] <= now + 1e-12 and not r.get("woke")),
                 key=lambda r: (r["epoch"], key_of(r)))
    for r in out:
        r["woke"] = True
    return out


def _holds_life(kernel: Any, planet: Any, metab: str) -> bool:
    from xylarium.kernel import worlds
    soc = planet.society
    if soc.get("shattered") is not None or float(soc.get("atmosphere", 1.0)) <= 0.0:
        return False
    try:
        return worlds.best(worlds.of_planet(kernel, planet), metab) is not None
    except Exception:
        return True


def disturb(kernel: Any, planet: Any, cause: str) -> Optional[str]:
    """A mind has acted on this world: re-resolve its life from now, from the world as it now stands."""
    from xylarium.kernel import cosmos, creation, history, life, scheduler
    if kernel is None or not hasattr(kernel, "sectors") or not cosmos.is_cosmic(kernel):
        return None
    if planet.population > 0 or getattr(planet, "civilization", None) is not None:
        return None                                       # a people lives there: its own story, not its life's
    loc = locate(kernel, planet)
    if loc is None:
        return None
    cell, ks, w = loc
    k = key(cell, ks, w)
    rec = current(kernel, k)
    if rec is None:
        return None
    now = cosmos.deep_gyr(kernel)
    if rec["epoch"] <= now:
        return None                                       # it has already woken (or its waking is being handed over)
    st = stats(kernel)
    reached = sum(1 for t in rec["steps"] if t <= now)
    if not _holds_life(kernel, planet, rec["metab"]):
        st["ended"][k] = {"cycle": kernel.cycle_count, "cause": cause, "rung": reached}
        st["redrawn"].pop(k, None)
        history.event(kernel, "LIFE_ENDED", f"Life on {planet.name} ends at its rung {reached}",
                      planet=planet, actors=[],
                      cause=f"{cause}: the world no longer holds a living medium",
                      data={"rung": reached, "of": len(rec["steps"])})
        return "ended"
    seed = cosmos.cosmos_seed(kernel)
    slot = creation.cell(seed, *cell)[ks]
    lin = (creation.system_life(seed, cell[0], cell[1], ks, slot) or [None] * (w + 1))[w]
    if not lin or lin["region"] != rec["metab"]:
        return None
    horizon = min(float(lin["end"]), creation.HORIZON_GYR)
    rng = scheduler.rng(kernel, "lifeline", k, kernel.cycle_count)
    got = life.climb(rng, lin["means"][reached:], now, horizon, float("inf"), lin["mu"])
    times = got["times"]
    if len(times) < len(lin["means"]) - reached or \
            creation.foragers(creation.world_at(seed, slot, slot["worlds"][w], times[-1] if times else now),
                              rec["metab"], slot) < creation.VIABLE:
        st["ended"][k] = {"cycle": kernel.cycle_count, "cause": cause, "rung": reached, "lives_on": True}
        st["redrawn"].pop(k, None)
        return "no mind"
    st["redrawn"][k] = dict(rec, epoch=round(times[-1], 6), steps=list(rec["steps"][:reached]) + times,
                            redrawn=kernel.cycle_count, woke=False)
    st["count"] += 1
    return "redrawn"


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"redrawn": len(st["redrawn"]), "ended": len(st["ended"]), "disturbances": st["count"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="lifeline", state=lambda: {"redrawn": {}, "ended": {}, "count": 0},
                             summary=summary))
