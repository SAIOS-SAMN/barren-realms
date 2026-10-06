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

from typing import Optional, Any, Dict, List

PATIENCE = 4.0                  # how many of its people's planning horizons a steward intelligence looks ahead (declared)
STEADINESS = 0.5                # its judgement's noise over its people's (declared: a clearer mind, not a perfect one)


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "steward_ai")


def enlist(kernel: Any, holder: str, name: str = "steward") -> None:
    from xylarium.kernel import steward
    steward.attach(kernel, holder, f"ai:{name}")


def enlist_all(kernel: Any, on: bool = True) -> None:
    stats(kernel)["all"] = bool(on)


def line_steward(kernel: Any, holder: str, home: Any) -> str:
    """Whose steward stands beside a people: a people that crossed free keeps its own line; otherwise the line whose
    dominion covers its home - an ancient's progenitors, or a young people that sends its own (settling.settled_by:
    the first to settle there) - posted silently, before the people knew anyone was there; where no dominion
    reaches, the elders' line holds the place."""
    from xylarium.kernel import ascendance, cosmos, settling
    if "annals" in kernel.state and cosmos.is_cosmic(kernel):
        b = settling.stats(kernel).get(holder)
        if b is not None:                                  # it has crossed
            rec = ascendance.stats(kernel)["of"].get(holder) or {}
            under = settling.settled_by(kernel, home.sector_id, float(b["crossed"]))
            if rec.get("ruling") == "chartered" or under in (None, holder):
                return f"ai:line:{holder}"                # it crossed free, or was chartered: its own line
            return f"ai:line:{under}"                      # it crossed in another's ward: that line keeps it
        by = settling.settled_by(kernel, home.sector_id, cosmos.deep_gyr(kernel))
        if by is not None and by != holder:
            return f"ai:line:{by}"
    return "ai:line:elders"


def line_of(kernel: Any, holder: Optional[str]) -> Optional[str]:
    """The line that stewards a people (the people itself for a line's own), or None."""
    from xylarium.kernel import steward
    g = steward.of(kernel, holder) if holder else None
    sid = str((g or {}).get("steward") or "")
    return sid[len("ai:line:"):] if sid.startswith("ai:line:") else None


def ensure(kernel: Any, peoples: Any) -> None:
    """The board is complete up to the stewards: in a universe begun at its Big Bang every living people has a steward
    beside it - its own world folded or not (the annals, which see every people, call this each year). It is posted
    by the line whose dominion covers its home, silently - no meeting, no contact; when a line's dominion reaches a
    people the elders were keeping, the line takes the post. A player's own steward is never replaced."""
    from xylarium.kernel import cosmos, steward
    st = stats(kernel)
    on = st["all"] if st.get("all") is not None else cosmos.is_cosmic(kernel)
    if not on:
        return
    for holder in sorted(peoples):
        worlds = peoples[holder]
        if not worlds:
            continue
        home = max(worlds, key=lambda p: (p.population, p.id))
        g = steward.of(kernel, holder)
        current = str((g or {}).get("steward") or "")
        if g is not None and not current.startswith("ai:"):
            continue                                      # a player's steward
        want = line_steward(kernel, holder, home)
        if current != want:
            steward.attach(kernel, holder, want)["silent"] = True


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
    ensure(kernel, by)                                        # the open worlds' peoples; the annals see the rest
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
        from xylarium.kernel import fertility
        gen = max(1.0, fertility.generation_of(kernel, home))
        steady = g is not None and g["aim"] and (kernel.cycle_count - int(g.get("aim_since", 0))) / 100.0 < gen
        if pick is not None and g is not None and g["aim"] != pick["name"] and not steady:
            steward.guide(kernel, holder, g["steward"], aim=pick["name"])   # it keeps a course a generation, as a
            g["aim_since"] = kernel.cycle_count                              # council does
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

register_subsystem(Subsystem(name="steward_ai", state=lambda: {"all": None, "urged": 0}, season=season,
                             summary=summary))
