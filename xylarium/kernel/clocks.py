"""
Xylarium clocks: time in two directions - cosmic time, the gauge, and each place's own proper time - and a people's
time as the height of its ledger, ordered only where it is causally linked.

TWO TIMES. Our universe's time is two-dimensional, as the conformal embedding of spacetime holds it (Cl(4,2): two
time directions, one of them gauge). Cosmic time (cosmos.deep_gyr) is the gauge direction: it is what creation
reads - stars forming and dying, minds waking - and no one lives in it. Proper time is what lives: every place where
life has woken keeps a clock of its own (a PLACE: a star system), paced by the peoples that live there and running
at the galaxy's pace where no one does. A place's star, climate and world read its own clock (cosmos.deep_gyr with a
place). A clock never jumps: a place keeps its own reading through every change of pace, and two places need never
agree on a "now".

THE LEDGER. A people's time is not a coordinate but a height: one receipt for each year it lives, and wherever it is
causally linked to another - their ships or words meet (contact), its light and another's are heard (signals), it
folds space from one place to another - its next receipt cites the other's head:

    h = 1 + max(h_own, h_other)

So peoples are ordered only where they are linked; peoples never linked stay concurrent, permanently, and no
decision waits on an order between them. The ancients' millions of years and a young people's thousands are never
laid on one line: they meet where their worldlines meet, and from that act on they carry each other.

THE FOLD (null flow). Motion composes by one law, t1 (+) t2 = (t1 + t2) / (1 + k t1 t2), k the square of the
motion's plane (geometry.flow): turns (k < 0), boosts (k > 0, Einstein's addition), and the null flow (k = 0), where
amounts simply add. The fold is the null flow: no proper time passes for the one who folds, and the two places'
worldlines are linked by it (fold).
"""

from typing import Any, Dict, List, Optional


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "clocks")


def _on(kernel: Any) -> bool:
    return kernel is not None and "clocks" in getattr(kernel, "state", {})


# ---------------------------------------------------------------------- places: proper time
def _seg_now(segs: List[List[float]], c: float) -> float:
    seg = segs[0]
    for s in segs:
        if s[0] <= c:
            seg = s
    return float(seg[1]) + (c - seg[0]) / 100.0 * float(seg[2]) / 1.0e9


def place_now(kernel: Any, sector_id: int, cycle: Optional[int] = None) -> Optional[float]:
    """A place's own proper time (Gyr since the Big Bang); None where it keeps none yet (it reads cosmic time)."""
    if not _on(kernel):
        return None
    rec = stats(kernel)["places"].get(str(sector_id))
    if rec is None:
        return None
    return _seg_now(rec["segs"], kernel.cycle_count if cycle is None else cycle)


def place_rate(kernel: Any, sector_id: int) -> Optional[float]:
    if not _on(kernel):
        return None
    rec = stats(kernel)["places"].get(str(sector_id))
    return float(rec["segs"][-1][2]) if rec is not None else None


def _ensure_place(kernel: Any, sector_id: int) -> Dict[str, Any]:
    """A place begins keeping its own time where it stands: at the reading it had (cosmic time) - no jump."""
    from xylarium.kernel import cosmos
    places = stats(kernel)["places"]
    rec = places.get(str(sector_id))
    if rec is None:
        rec = places[str(sector_id)] = {"segs": [[kernel.cycle_count, cosmos.deep_gyr(kernel), cosmos.ceiling(kernel)]]}
    return rec


def _set_place_rate(kernel: Any, sector_id: int, years_per_year: float) -> None:
    rec = _ensure_place(kernel, sector_id)
    c = kernel.cycle_count
    if abs(float(rec["segs"][-1][2]) - years_per_year) < 1e-12:
        return
    g = _seg_now(rec["segs"], c)
    if rec["segs"][-1][0] == c:
        rec["segs"][-1] = [c, g, float(years_per_year)]
    else:
        rec["segs"].append([c, g, float(years_per_year)])


def set_pace(kernel: Any, sector_id: int, years_per_year: float) -> None:
    """Pace a place's clock from now on (the season re-paces it each year by its watchers)."""
    _set_place_rate(kernel, sector_id, years_per_year)


# ---------------------------------------------------------------------- peoples: the ledger
def _people(kernel: Any, who: Optional[str]) -> Optional[Dict[str, Any]]:
    if not who or not _on(kernel):
        return None
    return stats(kernel)["peoples"].get(who)


def own(kernel: Any, who: Optional[str]) -> bool:
    """Does this people keep its own time? Every living people does: there is no shared now."""
    return _people(kernel, who) is not None


def home_of(kernel: Any, who: Optional[str]) -> Optional[int]:
    rec = _people(kernel, who)
    return int(rec["home"]) if rec is not None and rec.get("home") is not None else None


def now(kernel: Any, who: Optional[str], cycle: Optional[int] = None) -> float:
    """A people's proper now: its home place's clock (cosmic time for a people that keeps none)."""
    from xylarium.kernel import cosmos
    home = home_of(kernel, who)
    got = place_now(kernel, home, cycle) if home is not None else None
    return got if got is not None else cosmos.deep_gyr(kernel, cycle)


def rate(kernel: Any, who: Optional[str]) -> float:
    from xylarium.kernel import cosmos
    home = home_of(kernel, who)
    got = place_rate(kernel, home) if home is not None else None
    return got if got is not None else cosmos.ruler(kernel)


def height(kernel: Any, who: Optional[str]) -> int:
    rec = _people(kernel, who)
    return int(rec.get("h", 0)) if rec is not None else 0


def begin(kernel: Any, who: str, home: Any) -> None:
    """A mind has woken: its place begins keeping its own time, and its ledger begins at height zero."""
    from xylarium.kernel import tempo
    if not who or not hasattr(kernel, "state"):
        return
    st = stats(kernel)
    if who in st["peoples"]:
        return
    _ensure_place(kernel, home.sector_id)
    st["peoples"][who] = {"home": home.sector_id, "h": 0, "links": {}}
    _set_place_rate(kernel, home.sector_id, _pace(kernel, tempo.wait_years(kernel, who, home)))


def link(kernel: Any, a: str, b: str, why: str) -> None:
    """Two peoples' worldlines meet: each one's next receipt cites the other's head."""
    from xylarium.kernel import history
    ra, rb = _people(kernel, a), _people(kernel, b)
    if ra is None or rb is None or a == b:
        return
    ha, hb = int(ra["h"]), int(rb["h"])
    ra["h"] = rb["h"] = 1 + max(ha, hb)
    first = b not in ra["links"]
    ra["links"][b] = rb["links"][a] = ra["h"]
    if first:
        stats(kernel)["meetings"] += 1
        history.event(kernel, "WORLDLINES_MEET", f"The worldlines of the {a.split(':', 1)[-1]} and the "
                      f"{b.split(':', 1)[-1]} meet", actors=[a, b],
                      cause=f"{why}: from this act each carries the other (heights {ha} and {hb} -> {ra['h']})",
                      data={"why": why, "heights": [ha, hb], "now": ra["h"]})


def fold(kernel: Any, who: str, from_sector: int, to_sector: int) -> None:
    """A null flow from one place to another: no proper time passes for the one who folds; both places keep
    their own clocks, and the people's ledger records the passage."""
    rec = _people(kernel, who)
    _ensure_place(kernel, to_sector)
    if rec is not None:
        rec["h"] = int(rec["h"]) + 1
    stats(kernel)["folds"] += 1


def _pace(kernel: Any, wait: Optional[float]) -> float:
    from xylarium.kernel import cosmos, tempo
    if wait is None:
        return cosmos.ceiling(kernel)
    return min(cosmos.ceiling(kernel), max(1.0, wait / tempo.FRAMES))


def season(kernel: Any) -> List[str]:
    """Once a year: every people writes its year's receipt, peoples in contact or within each other's hearing
    cite each other's heads, and every place is paced by the peoples living there (the galaxy's pace where none
    does)."""
    from xylarium.kernel import contact, cosmos, relations, signals, tempo
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    by = relations._peoples(kernel)
    paces: Dict[str, float] = {}
    for who, worlds in by.items():
        home = max(worlds, key=lambda p: p.population)
        rec = st["peoples"].get(who)
        if rec is None:                                       # a seeded or settled people begins its own ledger
            begin(kernel, who, home)
            rec = st["peoples"].get(who)
            if rec is None:
                continue
        rec["home"] = home.sector_id
        rec["h"] = int(rec["h"]) + 1                          # the year's receipt
        pace = _pace(kernel, tempo.wait_years(kernel, who, home))
        for w in worlds:
            _ensure_place(kernel, w.sector_id)
            key = str(w.sector_id)
            paces[key] = min(paces.get(key, pace), pace)      # a place is watched as closely as its closest watcher
    met = contact.contacts(kernel, by)
    for a, others in met.items():
        for b in others:
            if a < b:
                link(kernel, a, b, "their ships and words meet")
    heard = signals.stats(kernel).get("heard", {}) if "signals" in kernel.state else {}
    for a, got in heard.items():
        for b in got:
            if b != a and b not in (st["peoples"].get(a) or {}).get("links", {}):
                link(kernel, a, b, "the light of one reached the other")
    for sid in list(st["places"]):
        _set_place_rate(kernel, int(sid), paces.get(sid, cosmos.ceiling(kernel)))
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"places": len(st["places"]), "peoples": len(st["peoples"]), "meetings": st["meetings"],
            "folds": st["folds"],
            "heights": {w.split(":", 1)[-1]: r["h"] for w, r in sorted(st["peoples"].items())[:12]}}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="clocks", state=lambda: {"places": {}, "peoples": {}, "meetings": 0, "folds": 0},
                             season=season, summary=summary))
