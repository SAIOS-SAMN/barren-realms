"""
Xylarium zones: the realm held crumpled - folded everywhere, opened only where someone is there to see it.

Everything starts compacted. A region is held as its fold: what is closed-form in time (its star's life, its worlds'
orbits) is evaluated whenever it is read, and its stepped processes (a world's crust renewing, its air escaping, its
uranium decaying) wait, folded, with the season they were last brought to. Where an observer comes, the region opens
to the depth that observer sees; as it leaves, the region folds again. Like a sheet of paper crumpled from every side
and held by its smallest part: denser away from every observer, finer near them.

LEVELS. 0 folded (not yet charted - cosmos.materialise opens it), 1 charted (the system on the map: closed-form
physics only), 2 world (its worlds' stepped processes run season by season), 3 surface (its worlds' grounds).

OBSERVERS. Every seat, AI or human, by what it is: a people sees its own worlds; a station's people the sector it
stands in; and each player seat holds open what its office reaches - the ASPECT table: for each seat, how many lanes
around its anchors it holds each level open. A progenitor sees widest and coarsest (its people's worlds stepped, the
rest charted - closed form is enough to shape a board); a sovereign its realm and the borders it guards, and its own
worlds' grounds; an office (a ship) the sector it is in and the lanes it can take next.

THE LAW. Opening or folding a region never changes what is true there: a folded process is caught up, when it opens
or when anything reads or writes it (touch), by the very season function the open region runs, once for each season
it missed, each with that season's own conditions (geology.settle). So the aspect table is the architects' choice of
camera - a choice of what is computed when - never of what happens.
"""

from typing import Any, Dict, FrozenSet, Iterable, Set

FOLDED, CHARTED, WORLD, SURFACE = 0, 1, 2, 3

# what each seat holds open around its anchors: {level: lanes} (declared: the camera, not physics - see THE LAW)
ASPECT: Dict[str, Dict[int, int]] = {
    "progenitor": {WORLD: 0},                 # its people's worlds; the rest of the board it reads charted
    "sovereign": {WORLD: 1, SURFACE: 0},      # its realm and the borders it guards; its own worlds' grounds
    "office": {WORLD: 1},                     # a ship: its sector and the lanes it can take next
    "intelligence": {WORLD: 2},               # the intelligence office: what lies a lane further, unseen
    "people": {WORLD: 0},                     # a people lives on its worlds
    "station": {WORLD: 0},                    # a port's people, the sector it stands in
}

ALL_OPEN = False                              # tests: hold every charted region open (the stepped reference)


def _ring(kernel: Any, anchors: Iterable[int], lanes: int) -> Set[int]:
    seen = {a for a in anchors if a in kernel.sectors}
    frontier = set(seen)
    for _ in range(max(0, lanes)):
        nxt = set()
        for sid in frontier:
            for nb in getattr(kernel.sectors[sid], "warps", []) or []:
                if nb in kernel.sectors and nb not in seen:
                    nxt.add(nb)
        seen |= nxt
        frontier = nxt
    return seen


def observers(kernel: Any) -> Dict[str, Set[int]]:
    """Each seat's anchors: the sectors it stands in or holds."""
    from xylarium.kernel import ages, roles
    out: Dict[str, Set[int]] = {k: set() for k in ASPECT}
    for sid, sec in kernel.sectors.items():
        if getattr(sec, "port", None) is not None:
            out["station"].add(sid)
        if any(q.population > 0 or q.owner_id or getattr(q, "natives", None) for q in sec.planets):
            out["people"].add(sid)
    try:
        from xylarium.kernel import harvest
        out["station"] |= {int(s) for s in harvest.stats(kernel).get("shade", {})}   # arrays stand round a star
    except Exception:
        pass
    seats = roles.stats(kernel)["of"] if "roles" in getattr(kernel, "state", {}) else {}
    realms = roles.stats(kernel).get("realms", {}) if seats else {}
    offices = roles.stats(kernel).get("office", {}) if seats else {}
    for cid, cap in getattr(kernel, "captains", {}).items():
        seat = seats.get(cid)
        if seat == "steward" and cid in realms:
            out["sovereign"].add(cap.sector_id)
            for wid in realms[cid]["worlds"]:
                w = kernel.get_planet(wid)
                if w is not None:
                    out["sovereign"].add(w.sector_id)
        elif offices.get(cid) in ASPECT:
            out[offices[cid]].add(cap.sector_id)          # an office that sees further than a ship's next lanes
        else:
            out["office"].add(cap.sector_id)
    if "ages" in getattr(kernel, "state", {}):
        for pid in ages.stats(kernel).get("stewards", {}):
            home = ages.homeworld(kernel, pid)
            if home is not None:
                out["progenitor"].add(home.sector_id)
    return out


def _levels(kernel: Any) -> Dict[int, int]:
    lv: Dict[int, int] = {}
    for seat, anchors in observers(kernel).items():
        for level, lanes in ASPECT[seat].items():
            for sid in _ring(kernel, anchors, lanes):
                if lv.get(sid, CHARTED) < level:
                    lv[sid] = level
    return lv


def _memo(kernel: Any) -> Dict[str, Any]:
    def scan() -> Dict[str, Any]:
        peopled, watched = set(), set()
        for sid, sec in kernel.sectors.items():
            if getattr(sec, "port", None) is not None:
                watched.add(sid)
            for q in sec.planets:
                if q.population > 0 or q.owner_id or getattr(q, "natives", None):
                    peopled.add(sid)
                    watched.add(sid)
                    break
        return {"peopled": frozenset(peopled), "watched": frozenset(watched), "levels": None}
    if not hasattr(kernel, "caches"):
        return scan()
    from xylarium.kernel import cache
    return cache.memo(kernel, "zones", "all", scan, epoch=kernel.cycle_count)


def peopled(kernel: Any) -> FrozenSet[int]:
    """Sectors with a living or held world (natives too), this cycle."""
    return _memo(kernel)["peopled"]


def watched(kernel: Any) -> FrozenSet[int]:
    """Sectors with a living or held world or a port, this cycle."""
    return _memo(kernel)["watched"]


def level(kernel: Any, sector_id: int) -> int:
    """How far this sector is unfolded, this cycle."""
    if sector_id not in kernel.sectors:
        return FOLDED
    if ALL_OPEN:
        return SURFACE
    m = _memo(kernel)
    if m["levels"] is None:
        m["levels"] = _levels(kernel)
    return m["levels"].get(sector_id, CHARTED)


def open_at(kernel: Any, sector_id: int, at: int = WORLD) -> bool:
    return level(kernel, sector_id) >= at


def touch(kernel: Any, planet: Any) -> None:
    """Something reads or writes this world: bring its folded processes to now first (exactly as if they had run)."""
    from xylarium.kernel import geology
    geology.settle(kernel, planet)


def touch_sector(kernel: Any, sector_id: int) -> None:
    sec = kernel.sectors.get(sector_id)
    for p in (sec.planets if sec is not None else []):
        touch(kernel, p)


def settle_all(kernel: Any) -> None:
    """Bring every folded world to now (a save, an audit, a test)."""
    for sid in list(kernel.sectors):
        touch_sector(kernel, sid)


def summary(kernel: Any) -> Dict[str, Any]:
    counts: Dict[int, int] = {}
    for sid in kernel.sectors:
        lv = level(kernel, sid)
        counts[lv] = counts.get(lv, 0) + 1
    return {"levels": {str(k): v for k, v in sorted(counts.items())}}
