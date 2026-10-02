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

import json
import weakref
from typing import Any, Dict, List, Optional

RECENT = 2000                   # events kept in the kernel (the file keeps them all)
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


def _age(kernel: Any) -> str:
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
    st["next"] += 1
    sid = sector_id if sector_id is not None else (getattr(planet, "sector_id", None) if planet is not None else None)
    cyc = int(getattr(kernel, "cycle_count", 0))
    rec = {"id": f"H-{st['next']:06d}", "cycle": cyc, "year": round(cyc / 100.0, 2), "age": _age(kernel),
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
    return rec


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
            "peoples": len(st["by_people"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="history",
    state=lambda: {"next": 0, "recent": [], "counts": {}, "by_people": {}},
    summary=summary,
))
