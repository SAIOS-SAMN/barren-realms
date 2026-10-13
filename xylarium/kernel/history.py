"""
Xylarium history: the ledger of everything that happened, across the ages - the record content is made from.

Every event worth telling - a mind arising, first contact, a war over food, a people turning on itself, a world
taken and a world rising, fields sown and states founded, a myth told, a first anywhere in the galaxy - is written
once, as data, the moment it happens:

    id        H-000001, in order
    when      the clock cycle and year, the deep-time epoch (Gyr since the galaxy began forming) and the age
    what      a kind, a title, a telling (text), its cause and its magnitude (people, stores, lives)
    who       the peoples (and captains) involved
    where     the world and system, and - in a cosmic universe - its place in the galaxy at that moment
              (cosmos.position: kpc from the centre, the angle it had turned to)
    refs      the earlier events it answers (a legend names the war it remembers, a myth the myth it retells)

The kernel keeps the recent window and an index of each people's events; a runner gives the ledger a file
(`sink`), and every event is appended to it as one JSON line - nothing is ever summarised away. tools/history.py
reads it back: a people's annals, an age's chronicle, a book, or a screenplay of scenes in space and time for a
replay.
"""

import hashlib
import json
import math
import re
import weakref
from typing import Any, Dict, List, Optional

RECENT = 2000                   # events kept in the kernel (the file keeps them all)
MONEY_KINDS = ("MONETARY_REGIME", "MONETARY_UNION", "COINAGE", "FACTION_DECREE")
WHERE_SOMEONE_IS = ("LANE_OPEN", "LANE_CLOSE")
SKY_KINDS = ("STAR_BORN", "STAR_AGEING", "STAR_DEATH")
PER_PEOPLE = 300                # events indexed per people in the kernel


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "history")


_SINKS: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()     # the runner's file for each kernel (not state)


def sink(kernel: Any, path: Optional[str]) -> None:
    """Give the ledger a file: every event from now on is appended to it (a new file first takes everything the
    kernel still holds, from genesis on)."""
    import os
    _SINKS[kernel] = path
    if path and not os.path.exists(path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as f:
            for rec in stats(kernel)["recent"]:
                f.write(json.dumps(rec, default=str) + "\n")


def _age(kernel: Any, actors: Optional[List[str]] = None, planet: Any = None) -> str:
    """The age an event belongs to. In a universe made by physics, it is its own people's age in its own terms
    (ways.era); an event no people owns belongs to the galaxy's own epoch. The settled galaxy keeps its calendar."""
    from xylarium.kernel import cosmos
    if cosmos.is_cosmic(kernel):
        from xylarium.kernel import ways
        home = planet if planet is not None and getattr(planet, "civilization", None) is not None else None
        if home is None:
            names = {a.split(":", 1)[1] for a in (actors or []) if str(a).startswith("civ:")}
            if names:
                home = next((p for s in kernel.sectors.values() for p in s.planets
                             if p.population > 0 and getattr(getattr(p, "civilization", None), "name", None) in names),
                            None)
        if home is not None:
            return ways.era(home)
        return f"{cosmos.deep_gyr(kernel):.3f} Gyr after the Big Bang"
    firsts = ((getattr(kernel, "state", None) or {}).get("genesis") or {}).get("firsts") or {}
    for key, name in (("first_empire", "Age of the Lanes"), ("first_starship", "Age of First Flight"),
                      ("first_state", "Age of Fields"), ("first_mind", "Age of Foragers"),
                      ("first_farms", "Age of Foragers")):
        if key in firsts:
            return name
    return "Before Minds"


def event(kernel: Any, kind: str, title: str, actors: Optional[List[str]] = None, planet: Any = None,
          sector_id: Optional[int] = None, magnitude: float = 0, cause: str = "", text: str = "",
          refs: Optional[List[str]] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if kernel is None or not hasattr(kernel, "state"):
        return {}
    st = stats(kernel)
    if _muted(kernel, kind, list(actors or [])):
        st["muted"][kind] = st["muted"].get(kind, 0) + 1         # counted, not told (culture.py)
        return {}
    st["next"] += 1
    sid = sector_id if sector_id is not None else (getattr(planet, "sector_id", None) if planet is not None else None)
    cyc = int(getattr(kernel, "cycle_count", 0))
    rec = {"id": f"H-{st['next']:06d}", "cycle": cyc, "year": round(cyc / 100.0, 2), "age": _age(kernel, actors, planet),
           "kind": kind, "title": title, "actors": list(actors or []), "magnitude": magnitude, "cause": cause,
           "text": text, "refs": list(refs or []), "sector": sid,
           "planet": getattr(planet, "id", None) if planet is not None else None,
           "planet_name": getattr(planet, "name", None) if planet is not None else None}
    from xylarium.kernel import cosmos
    if cosmos.is_cosmic(kernel):
        rec["deep_gyr"] = round(cosmos.deep_gyr(kernel), 6)
        if sid is not None:
            rec["galactic"] = cosmos.position(kernel, sid)
    if data:
        rec["data"] = data
    recent = st["recent"]
    recent.append(rec)
    prev_root = str(st.get("history_root", "genesis"))
    st["history_root"] = hashlib.sha256(f"{prev_root}:{rec['id']}:{rec['kind']}:{rec['cycle']}".encode()).hexdigest()
    del recent[:-RECENT]
    st["counts"][kind] = st["counts"].get(kind, 0) + 1
    for a in rec["actors"]:
        ids = st["by_people"].setdefault(a, [])
        ids.append(rec["id"])
        del ids[:-PER_PEOPLE]
    path = _SINKS.get(kernel)
    if path:
        with open(path, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    from xylarium.kernel import memory
    memory.witness(kernel, rec)                        # what its peoples lived through, they may keep (their own record)
    return rec


# ---------------------------------------------------------------------- telling: dates in the reader's own years
_GYR_TEXT = re.compile(r"(at the level of history, )?,?\s*\d+(\.\d+)? Gyr (after the Big Bang|into the galaxy)[,:;]?\s*")


def when_gyr(rec: Dict[str, Any]) -> Optional[float]:
    """When an event happened on the one coordinate clock: the epoch its annals dated it to, else when it was
    written."""
    got = (rec.get("data") or {}).get("epoch")
    if got is None:
        got = rec.get("deep_gyr")
    return float(got) if got is not None else None


def galactic_year_gyr() -> float:
    """One turn of the galaxy at the Sun's radius: 2 pi R0 / V (Gyr) - the year of a reader with no world."""
    from xylarium.kernel import cosmos, geometry
    return 2.0 * math.pi * cosmos.R0_KPC / cosmos.V_FLAT_KMS * geometry.GYR_PER_KPC_PER_KMS


def _count(n: float) -> str:
    n = abs(n)
    for size, word in ((1e12, "trillion"), (1e9, "billion"), (1e6, "million"), (1e3, "thousand")):
        if n >= size:
            v = n / size
            return f"{v:.1f} {word}" if v < 10 else f"{v:.0f} {word}"
    return f"{n:,.0f}"


def _home_of(kernel: Any, reader: Optional[str]) -> Any:
    if not reader:
        return None
    from xylarium.kernel import relations
    worlds = relations._peoples(kernel).get(reader) or []
    return max(worlds, key=lambda p: (p.population, p.id)) if worlds else None


def tell(kernel: Any, rec: Dict[str, Any], reader: Optional[str] = None) -> str:
    """When an event happened, told to a reader in its own years: turns of its own world about its star, counted
    back from its own now on its own clock - and, before its people woke, how long before. With no reader (or one
    with no world), in turns of the galaxy."""
    from xylarium.kernel import cosmos
    epoch = when_gyr(rec)
    if epoch is None or not cosmos.is_cosmic(kernel):
        return f"year {rec.get('year', 0):,}"
    home = _home_of(kernel, reader)
    if home is None:
        turns = epoch / galactic_year_gyr()
        return f"{_count(turns)} turns of the galaxy after the Big Bang"
    from xylarium.kernel import clocks, physics
    sec = kernel.sectors.get(home.sector_id)
    year = float(physics.year_cycles(sec, home)) / physics.CYCLES_PER_STANDARD_YEAR if sec is not None else 1.0
    lapse = clocks.lapse(kernel, home.sector_id)
    ago = (clocks.now(kernel, reader) - epoch * lapse) * 1e9 / max(1e-12, year)
    world = home.name
    if abs(ago) < 1.0:
        told = f"this turn of {world}"
    elif ago > 0:
        told = f"{_count(ago)} turns of {world} about its star ago"
    else:
        told = f"{_count(-ago)} turns of {world} about its star from now"
    woke = (home.society.get("arisen") or {}).get("epoch")
    if woke is not None and epoch < float(woke):
        before = (float(woke) - epoch) * lapse * 1e9 / max(1e-12, year)
        told += f", {_count(before)} before the {reader.split(':', 1)[-1]} woke"
    return told


def chronicle(kernel: Any, reader: Optional[str] = None, about: Optional[str] = None,
              kinds: Optional[List[str]] = None, limit: int = 60) -> List[str]:
    """The galaxy's history as a reader would read it: oldest first, each event dated in the reader's own years."""
    recs = of_people(kernel, about) if about else list(stats(kernel)["recent"])
    recs = [r for r in recs if (not kinds or r["kind"] in kinds) and when_gyr(r) is not None]
    recs.sort(key=lambda r: (when_gyr(r), r["id"]))
    out = []
    for r in recs[-limit:]:
        cause = _GYR_TEXT.sub("", r.get("cause") or "").strip()
        out.append(f"{tell(kernel, r, reader)}: {r['title']}." + (f" ({cause})" if cause else ""))
    return out


def _muted(kernel: Any, kind: str, actors: List[str]) -> bool:
    """A people not yet among the stars keeps no banking or currency entries: its money matters to no one but itself
    until it trades on the exchange (institutions.py, culture.py). The galaxy's histories wait for someone to be in it."""
    from xylarium.kernel import culture, institutions
    if not institutions.founding(kernel):
        return False
    if kind in MONEY_KINDS:
        if not institutions.stats(kernel)["exchange"]:
            return True
        civs = [a for a in actors if str(a).startswith("civ:")]
        return bool(civs) and not any(culture.is_linked(kernel, a) for a in civs)
    if kind == "GALACTIC_HISTORY":
        return not culture.linked_peoples(kernel)
    if kind in WHERE_SOMEONE_IS:                       # the galaxy's weather, told where someone linked lives
        civs = [a for a in actors if str(a).startswith("civ:")]
        return not any(culture.is_linked(kernel, a) for a in civs)
    if kind in SKY_KINDS:                              # a star's birth or death no one lives by: told once anyone
        return not actors and not culture.linked_peoples(kernel)      # is among the stars to see it
    return False


def find(kernel: Any, event_id: str) -> Optional[Dict[str, Any]]:
    for rec in reversed(stats(kernel)["recent"]):
        if rec["id"] == event_id:
            return rec
    return None


def of_people(kernel: Any, people: str) -> List[Dict[str, Any]]:
    ids = set(stats(kernel)["by_people"].get(people, []))
    return [r for r in stats(kernel)["recent"] if r["id"] in ids]


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"events": st["next"], "by_kind": dict(sorted(st["counts"].items(), key=lambda kv: -kv[1])[:12]),
            "peoples": len(st["by_people"]), "muted": dict(st.get("muted", {}))}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="history",
    state=lambda: {"next": 0, "recent": [], "counts": {}, "by_people": {}, "muted": {}},
    summary=summary,
))
