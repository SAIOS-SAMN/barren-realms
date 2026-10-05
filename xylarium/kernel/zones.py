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
    "steward": {WORLD: 0},                    # a realm's steward: the worlds of the peoples whose disputes it hears
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


def observers(kernel: Any, seated: bool = False) -> Dict[str, Set[int]]:
    """Each seat's anchors: the sectors it stands in or holds. `seated`: only the players' seats (human or AI) -
    the observers a people unfolds for; its own worlds, its stations and the realm's roaming crews do not count."""
    from xylarium.kernel import ages, roles
    out: Dict[str, Set[int]] = {k: set() for k in ASPECT}
    for sid, sec in ({} if seated else kernel.sectors).items():
        if getattr(sec, "port", None) is not None:
            out["station"].add(sid)
        if any(q.population > 0 or q.owner_id or getattr(q, "natives", None) for q in sec.planets):
            out["people"].add(sid)
    try:
        if not seated:
            from xylarium.kernel import harvest
            out["station"] |= {int(s) for s in harvest.stats(kernel).get("shade", {})}   # arrays stand round a star
    except Exception:
        pass
    seats = roles.stats(kernel)["of"] if "roles" in getattr(kernel, "state", {}) else {}
    realms = roles.stats(kernel).get("realms", {}) if seats else {}
    offices = roles.stats(kernel).get("office", {}) if seats else {}
    for cid, cap in getattr(kernel, "captains", {}).items():
        seat = seats.get(cid)
        if seated and seat is None:
            continue                                      # a crew of the realm, not a player's seat
        if seat in ("sovereign", "steward") and cid in realms:
            out["sovereign"].add(cap.sector_id)
            for wid in realms[cid]["worlds"]:
                w = kernel.get_planet(wid)
                if w is not None:
                    out["sovereign"].add(w.sector_id)
        elif offices.get(cid) in ASPECT:
            out[offices[cid]].add(cap.sector_id)          # an office that sees further than a ship's next lanes
        else:
            out["office"].add(cap.sector_id)
    if "stewardship" in getattr(kernel, "state", {}):
        from xylarium.kernel import relations, stewardship
        by = relations._peoples(kernel)
        for realm, pid in stewardship.stats(kernel)["stewards"].items():
            for d in stewardship.disputes(kernel, realm):     # a steward's attention: where it is called to rule
                for who in (d["a"], d["b"]):
                    out["steward"] |= {w.sector_id for w in by.get(who, [])}
    if "ages" in getattr(kernel, "state", {}):
        for pid in ages.stats(kernel).get("stewards", {}):
            home = ages.homeworld(kernel, pid)
            if home is not None:
                out["progenitor"].add(home.sector_id)
    return out


def _levels(kernel: Any, seated: bool = False) -> Dict[int, int]:
    lv: Dict[int, int] = {}
    for seat, anchors in observers(kernel, seated).items():
        for level, lanes in ASPECT[seat].items():
            for sid in _ring(kernel, anchors, lanes):
                if lv.get(sid, CHARTED) < level:
                    lv[sid] = level
    return lv


def _quarter_of(kernel: Any) -> int:
    """The zones are read once a quarter (the season's laws see the realm as it was opened at its start)."""
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return kernel.cycle_count // FISCAL_QUARTER_CYCLES


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
    return cache.memo(kernel, "zones", "all", scan, epoch=_quarter_of(kernel))


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


# ---------------------------------------------------------------------- folded peoples
# The laws that carry or catch up what is folded see folded worlds; every other seasonal law runs without them.
SEES_FOLDED = {"tempo", "clocks", "cosmos", "annals", "blackhole", "exodus", "geology", "board", "spheres", "transit"}


def folded_peoples(kernel: Any) -> FrozenSet[str]:
    """Peoples held folded this cycle: in a universe begun at its Big Bang, every people whose own history decides its
    turnings (annals.history_decides: no seat guides it) and none of whose worlds lies where a player's seat - human
    or AI, of any tier - holds the realm open to the worlds. A folded people lives at the level of history alone:
    the annals carry its years, its turnings, its falls and its dominion; when a seat comes near it opens, its worlds
    as its history has made them, and the engine takes up its seasons."""
    if ALL_OPEN or not hasattr(kernel, "caches"):
        return frozenset()
    from xylarium.kernel import cache

    def scan() -> FrozenSet[str]:
        from xylarium.kernel import annals, cosmos, relations
        if not cosmos.is_cosmic(kernel):
            return frozenset()
        open_ = {sid for sid, lv in _levels(kernel, seated=True).items() if lv >= WORLD}
        out = set()
        for who, worlds in relations._peoples(kernel).items():
            if annals.history_decides(kernel, who) and not any(w.sector_id in open_ for w in worlds):
                out.add(who)
        return frozenset(out)
    return cache.memo(kernel, "zones", "folded_peoples", scan, epoch=_quarter_of(kernel))


def folded_worlds(kernel: Any) -> FrozenSet[str]:
    if ALL_OPEN or not hasattr(kernel, "caches"):
        return frozenset()
    from xylarium.kernel import cache

    def scan() -> FrozenSet[str]:
        from xylarium.kernel import relations
        peoples = folded_peoples(kernel)
        by = relations._peoples(kernel)
        return frozenset(w.id for who in peoples for w in by.get(who, []))
    return cache.memo(kernel, "zones", "folded_worlds", scan, epoch=_quarter_of(kernel))


def is_folded(kernel: Any, planet: Any) -> bool:
    return planet is not None and planet.id in folded_worlds(kernel)


class hidden:
    """While the engine's own seasonal laws run, folded worlds are not on the map they walk; they are put back as
    they were (worlds a law adds or removes meanwhile are kept or dropped)."""

    def __init__(self, kernel: Any) -> None:
        self.kernel = kernel
        self.saved: Dict[int, Any] = {}

    CACHES = ("relations_peoples", "planet_index", "peopled_worlds")   # read from the map: read again

    def _forget(self) -> None:
        for name in self.CACHES:
            getattr(self.kernel, "caches", {}).pop(name, None)

    def __enter__(self) -> "hidden":
        _memo(self.kernel)                                # the quarter's zones are read from the whole map
        fw = folded_worlds(self.kernel)
        if not fw:
            return self
        self._forget()
        for sid, sec in self.kernel.sectors.items():
            if any(p.id in fw for p in sec.planets):
                orig = sec.planets
                self.saved[sid] = (orig, [p for p in orig if p.id in fw])
                sec.planets = [p for p in orig if p.id not in fw]
        return self

    def __exit__(self, *exc: Any) -> None:
        for sid, (orig, folded) in self.saved.items():
            sec = self.kernel.sectors.get(sid)
            if sec is None:
                continue
            shown = sec.planets
            keep = set(id(p) for p in shown) | set(id(p) for p in folded)
            merged = [p for p in orig if id(p) in keep] + [p for p in shown if all(p is not q for q in orig)]
            orig[:] = merged
            sec.planets = orig
        if self.saved:
            self._forget()
        self.saved = {}


def summary(kernel: Any) -> Dict[str, Any]:
    counts: Dict[int, int] = {}
    for sid in kernel.sectors:
        lv = level(kernel, sid)
        counts[lv] = counts.get(lv, 0) + 1
    return {"levels": {str(k): v for k, v in sorted(counts.items())}}
