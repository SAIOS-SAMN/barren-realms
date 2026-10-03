"""
Xylarium clocks: there is no one "now" - each people keeps its own, and clocks meet when peoples do.

Physics has no universal present: every place's clock runs at its own rate, and what happens far away has no
agreed order with what happens here until a signal joins them. The engine keeps one clock only for what the galaxy
itself does - its stars forming, its minds waking, its deep turning (cosmos.deep_gyr) - and that clock runs at the
pace chosen at genesis.

A people no one else can yet observe keeps a clock of its own. It runs at the pace of its own history (tempo: a
few frames to each of its turnings), and its world reads it: its star's age, its climate's swing, its world's
ageing (cosmos.deep_gyr with a place) - so a rising people lives its history in full while the galaxy runs on, and
no one people holds the galaxy back.

Clocks meet when peoples interact, and only then must they: when a people hears another's light or is heard
(signals), meets one (contact), or crosses to the stars (mastery) - from then on others can see it, and it joins
the galactic now. Its clock is set to the galaxy's (CLOCKS_MEET), the years its history had not yet lived are lived
at the level of history (annals), and it shares one now with everyone it can reach. Orbits are closed-form
functions of time, exact whatever clock reads them.

Its clock is kept as segments of constant rate, as the galaxy's is (cosmos.set_rate), so every people's time is
exactly accumulated.
"""

from typing import Any, Dict, List, Optional


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "clocks")


def _rec(kernel: Any, who: Optional[str]) -> Optional[Dict[str, Any]]:
    if not who or kernel is None or "clocks" not in getattr(kernel, "state", {}):
        return None
    return stats(kernel)["peoples"].get(who)


def own(kernel: Any, who: Optional[str]) -> bool:
    """Does this people keep its own clock (no one has yet observed it)?"""
    rec = _rec(kernel, who)
    return rec is not None and not rec["synced"]


def now(kernel: Any, who: Optional[str], cycle: Optional[int] = None) -> float:
    """The people's own now (Gyr since the Big Bang); the galaxy's once its clock has met the others'."""
    from xylarium.kernel import cosmos
    rec = _rec(kernel, who)
    c = kernel.cycle_count if cycle is None else cycle
    if rec is None or rec["synced"]:
        return cosmos.deep_gyr(kernel, c)
    seg = rec["segs"][0]
    for s in rec["segs"]:
        if s[0] <= c:
            seg = s
    return float(seg[1]) + (c - seg[0]) / 100.0 * float(seg[2]) / 1.0e9


def rate(kernel: Any, who: Optional[str]) -> float:
    from xylarium.kernel import cosmos
    rec = _rec(kernel, who)
    return float(rec["segs"][-1][2]) if rec is not None and not rec["synced"] else cosmos.ruler(kernel)


def set_rate(kernel: Any, who: str, years_per_year: float) -> None:
    rec = _rec(kernel, who)
    if rec is None or rec["synced"]:
        return
    c = kernel.cycle_count
    g = now(kernel, who, c)
    if rec["segs"][-1][0] == c:
        rec["segs"][-1] = [c, g, float(years_per_year)]
    else:
        rec["segs"].append([c, g, float(years_per_year)])


def begin(kernel: Any, who: str, home: Any) -> None:
    """A mind has woken: it starts its own clock at the galaxy's now, at its own history's pace."""
    from xylarium.kernel import cosmos, tempo
    if "clocks" not in getattr(kernel, "state", {}) and not hasattr(kernel, "state"):
        return
    st = stats(kernel)
    if who in st["peoples"]:
        return
    st["peoples"][who] = {"segs": [[kernel.cycle_count, cosmos.deep_gyr(kernel), cosmos.ceiling(kernel)]],
                          "synced": False, "sectors": [home.sector_id]}
    w = tempo.wait_years(kernel, who, home)
    set_rate(kernel, who, _pace(kernel, w))
    st["places"][str(home.sector_id)] = who


def _pace(kernel: Any, wait: Optional[float]) -> float:
    from xylarium.kernel import cosmos, tempo
    if wait is None:
        return cosmos.ceiling(kernel)
    return min(cosmos.ceiling(kernel), max(1.0, wait / tempo.FRAMES))


def place_now(kernel: Any, sector_id: int, cycle: Optional[int] = None) -> Optional[float]:
    """The now of a place a people keeps its own clock in (None: the place reads the galaxy's)."""
    if kernel is None or "clocks" not in getattr(kernel, "state", {}):
        return None
    who = stats(kernel)["places"].get(str(sector_id))
    if who is None or not own(kernel, who):
        return None
    return now(kernel, who, cycle)


def place_rate(kernel: Any, sector_id: int) -> Optional[float]:
    if kernel is None or "clocks" not in getattr(kernel, "state", {}):
        return None
    who = stats(kernel)["places"].get(str(sector_id))
    return rate(kernel, who) if who is not None and own(kernel, who) else None


def sync(kernel: Any, who: str, why: str) -> None:
    """Its clock meets the galaxy's: from now on it shares the galactic now."""
    from xylarium.kernel import cosmos, history
    rec = _rec(kernel, who)
    if rec is None or rec["synced"]:
        return
    lag = (cosmos.deep_gyr(kernel) - now(kernel, who)) * 1e9
    rec["synced"] = True
    rec["met"] = {"cycle": kernel.cycle_count, "why": why, "lag_years": round(lag)}
    st = stats(kernel)
    st["meetings"] += 1
    for sid in rec.get("sectors", []):
        if st["places"].get(str(sid)) == who:
            st["places"].pop(str(sid))
    history.event(kernel, "CLOCKS_MEET", f"The {who.split(':', 1)[-1]} join the galaxy's now", actors=[who],
                  cause=f"{why}: its own {lag:,.0f} years behind the galaxy's are lived at the level of history",
                  data={"lag_years": round(lag), "why": why})


def season(kernel: Any) -> List[str]:
    """Once a year: each people keeping its own clock is paced to its history, and any that others can now see
    joins the galaxy's now."""
    from xylarium.kernel import contact, cosmos, mastery, relations, signals, tempo
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    by = relations._peoples(kernel)
    met = contact.contacts(kernel, by)
    heard = signals.stats(kernel).get("heard", {}) if "signals" in kernel.state else {}
    for who, rec in list(st["peoples"].items()):
        if rec["synced"]:
            continue
        worlds = by.get(who)
        if not worlds:
            rec["synced"] = True                              # it is gone: nothing keeps its clock
            continue
        why = None
        if mastery.crossed(kernel, who):
            why = "it crossed to the stars"
        elif met.get(who):
            why = "it met another people"
        elif heard.get(who) or any(who in h for h in heard.values()):
            why = "its light and another's met"
        if why:
            sync(kernel, who, why)
            continue
        rec["sectors"] = sorted({p.sector_id for p in worlds})
        for sid in rec["sectors"]:
            st["places"][str(sid)] = who
        home = max(worlds, key=lambda p: p.population)
        want = _pace(kernel, tempo.wait_years(kernel, who, home))
        have = rate(kernel, who)
        if max(want / have, have / want) >= 2.0:
            set_rate(kernel, who, want)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    own_n = [w for w, r in st["peoples"].items() if not r["synced"]]
    return {"own_clocks": len(own_n), "meetings": st["meetings"],
            "paces": {w.split(":", 1)[-1]: round(rate(kernel, w), 1) for w in own_n}}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="clocks", state=lambda: {"peoples": {}, "places": {}, "meetings": 0},
                             season=season, summary=summary))
