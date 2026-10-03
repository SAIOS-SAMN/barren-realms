"""
Xylarium steward intelligence: a steward that is not a player - an intelligence set to guide a people.

It is held to everything a steward is (steward.py): it sees only what its people can see, it speaks only through
its people's own weighing, and it is heeded only as far as heeding it has served them. What it brings is patience:
it weighs the same five aims its people's council weighs (strategy.py: grow, deepen, secure, hold, reach) from the
same counsel, but over a horizon PATIENCE times its people's own, and with a steadier judgement - so it urges what
a people that could see as far ahead would choose. When the counsel shows its people's sun dying within that
horizon, it brings the exodus before the council (consider). Whether any of it is taken up is the people's.

A steward intelligence is enlisted for a people (enlist), or for every people as it arises (enlist_all: set at
genesis by a progenitor, or by a run).
"""

from typing import Any, Dict, List

PATIENCE = 4.0                  # how many of its people's planning horizons a steward intelligence looks ahead (declared)
STEADINESS = 0.5                # its judgement's noise over its people's (declared: a clearer mind, not a perfect one)


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "steward_ai")


def enlist(kernel: Any, holder: str, name: str = "steward") -> None:
    from xylarium.kernel import steward
    steward.attach(kernel, holder, f"ai:{name}")


def enlist_all(kernel: Any, on: bool = True) -> None:
    stats(kernel)["all"] = bool(on)


def _ours(kernel: Any) -> List[str]:
    from xylarium.kernel import steward
    if "steward" not in getattr(kernel, "state", {}):
        return []
    return [h for h, g in steward.stats(kernel)["guides"].items() if str(g.get("steward", "")).startswith("ai:")]


def season(kernel: Any) -> List[str]:
    """Once a year each steward intelligence reads its people and speaks."""
    from xylarium.kernel import cosmos, decide, relations, steward, strategy
    if (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    by = relations._peoples(kernel)
    if st["all"]:
        for holder in by:
            if steward.of(kernel, holder) is None:
                enlist(kernel, holder)
    for holder in _ours(kernel):
        worlds = by.get(holder)
        if not worlds:
            continue
        home = max(worlds, key=lambda p: p.population)
        m = decide.mind_of_planet(kernel, home)
        far = dict(m, horizon_q=decide.horizon(m) * PATIENCE, noise=m["noise"] * STEADINESS, holder=None)
        worths = strategy._worths(kernel, holder, worlds, by, far)
        opts = [decide.option(a, 0.0, worths[a]) for a in steward.AIMS]
        pick = decide.choose(kernel, opts, far, "steward_ai", holder)
        g = steward.of(kernel, holder)
        if pick is not None and g is not None and g["aim"] != pick["name"]:
            steward.guide(kernel, holder, g["steward"], aim=pick["name"])
            st["urged"] += 1
        years = cosmos.years_left(kernel, home.sector_id) if cosmos.is_cosmic(kernel) else None
        if years is not None and g is not None and years * 4.0 < decide.horizon(far):
            steward.counsel_more(kernel, holder, g["steward"], ["exodus", "rescue"])
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    from xylarium.kernel import steward
    ours = _ours(kernel)
    heeds = [steward.heed(kernel, h) for h in ours]
    return {"stewarded": len(ours), "urged": stats(kernel)["urged"],
            "mean_heed": round(sum(heeds) / len(heeds), 3) if heeds else None,
            "heeded": sum(steward.of(kernel, h)["heeded"] for h in ours if steward.of(kernel, h))}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="steward_ai", state=lambda: {"all": False, "urged": 0}, season=season,
                             summary=summary))
