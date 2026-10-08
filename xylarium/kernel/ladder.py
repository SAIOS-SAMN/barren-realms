"""
Xylarium ladder: how far a people has come toward the network (Concordance 6.2; its floor, 6.2a) - read from
EVIDENCE only. A people stands on the highest rung whose evidence exists, each rung citing the record that shows it;
never a score, never a threshold. A rung whose evidence the prototype cannot hold (a court's judgement) reads
UNMEASURED, naming what is missing - it is never inferred.

  1 UNAWARE           the default
  2 OBSERVED          a seated steward has read its books (ascendance: its books, read)
  3 PETITIONS         its petition is on record, or a steward's cited ruling on it (quarantine or ascend)
  4 HEARS ANASTOME    the floor first - a court-judged ARC closure by one of its minds (6.2a) - then work entered
                      in the court's language: UNMEASURED here (no court in the prototype)
  5 RIDES THE ROADS   a transit receipt with it as payer, under a keeper's toll (the realm's books or the hypha)
  6 SPEAKS ANASTOME   its words admitted with derivations: UNMEASURED here (no court in the prototype)
  7 BUILDS ROADS      it is a progenitor line with a road of its own on the hypha - a toll appended under its house,
                      the ancients' uplink keeping it

A change of rung is written to the annals (history: RUNG).
"""

from typing import Any, Dict, List, Optional, Tuple

RUNGS = ("unaware", "observed", "petitions", "hears_anastome", "rides_the_roads", "speaks_anastome", "builds_roads")
UNMEASURED = {"hears_anastome": "a court-judged ARC closure by one of its minds (6.2a), then work entered in the "
                                "court's language - the prototype holds no court",
              "speaks_anastome": "its words admitted by the court with derivations - the prototype holds no court"}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "ladder")


def _petition(kernel: Any, who: str) -> Optional[Dict[str, Any]]:
    if "ascendance" not in getattr(kernel, "state", {}):
        return None
    from xylarium.kernel import ascendance
    return ascendance.stats(kernel)["of"].get(who)


def _observed(kernel: Any, who: str) -> Optional[Dict[str, Any]]:
    rec = _petition(kernel, who)
    if rec and rec.get("books"):
        return {"record": "ascendance", "realm": rec["realm"], "read": rec.get("ruled"), "books": sorted(rec["books"])}
    return None


def _petitions(kernel: Any, who: str) -> Optional[Dict[str, Any]]:
    rec = _petition(kernel, who)
    if rec is None:                                   # a petition once made is evidence, though withdrawn since
        from xylarium.kernel import history       # (an ancients' house withdraws its own: it answers to no younger line)
        ev = next((e for e in history.of_people(kernel, who) if e.get("kind") == "PETITION"), None)
        return {"record": "history.PETITION", "cycle": ev.get("cycle")} if ev else None
    ruling = (rec.get("deeds") or {}).get("ruling")
    if ruling:
        return {"record": "ascendance.ruling", "realm": rec["realm"], "verdict": ruling["verdict"],
                "by": ruling["by"], "cycle": ruling["cycle"]}
    return {"record": "ascendance.petition", "realm": rec["realm"], "since": rec["since"]}


def _rides(kernel: Any, who: str) -> Optional[Dict[str, Any]]:
    if "transit" in getattr(kernel, "state", {}):
        from xylarium.kernel import transit
        for realm, rec in sorted((transit.stats(kernel).get("in_game") or {}).items()):
            got = (rec.get("first_of") or {}).get(who)
            if got:
                return {"record": "transit.in_game", **got}
    for lane, row in _hypha_rows(kernel):
        if row.get("payer") == who and row.get("kind") == "pouw":
            return {"record": "hypha", "lane": lane, "height": row["height"], "hash": row["hash"]}
    return None


def _builds(kernel: Any, who: str) -> Optional[Dict[str, Any]]:
    from xylarium.kernel import board
    if who not in board.progenitors(kernel):
        return None
    for lane, row in _hypha_rows(kernel):
        if row.get("kind") == "pouw" and row.get("house") == who and row.get("payee") == who:
            return {"record": "hypha", "lane": lane, "height": row["height"], "hash": row["hash"], "road": row.get("ref")}
    return None


def _hypha_rows(kernel: Any) -> List[Tuple[str, Dict[str, Any]]]:
    if "hypha" not in getattr(kernel, "state", {}):
        return []
    from xylarium.kernel import hypha
    return [(lane, r) for lane, c in sorted(hypha.stats(kernel)["chains"].items()) for r in c["rows"]]


EVIDENCE = {"observed": _observed, "petitions": _petitions, "rides_the_roads": _rides, "builds_roads": _builds}


def rung(kernel: Any, who: str) -> Tuple[str, Dict[str, Any]]:
    """(the highest rung whose evidence exists, its citations): each rung with evidence cites its record; the
    rungs the prototype cannot measure are named UNMEASURED, with what is missing."""
    cites: Dict[str, Any] = {}
    top = "unaware"
    for r in RUNGS[1:]:
        if r in UNMEASURED:
            cites[r] = {"unmeasured": UNMEASURED[r]}
            continue
        ev = EVIDENCE[r](kernel, who)
        if ev is not None:
            cites[r] = ev
            top = r
    return top, cites


def season(kernel: Any) -> List[str]:
    """Once a year: each people's rung read; a change is written to the annals."""
    from xylarium.kernel import history, polity, relations
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    st = stats(kernel)["of"]
    logs: List[str] = []
    for who in sorted(relations._peoples(kernel)):
        top, cites = rung(kernel, who)
        if st.get(who) != top:
            was = st.get(who, "unaware")
            st[who] = top
            if top != was:
                history.event(kernel, "RUNG", f"The {who.split(':', 1)[-1]} stand on the rung: {top.replace('_', ' ')}",
                              actors=[who], cause=f"from {was.replace('_', ' ')}, on its evidence",
                              data={"rung": top, "was": was, "cites": cites.get(top)})
                logs.append(f"[LADDER] The {who.split(':', 1)[-1]}: {was} -> {top}.")
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    out: Dict[str, int] = {}
    for r in stats(kernel)["of"].values():
        out[r] = out.get(r, 0) + 1
    return {"rungs": out}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="ladder", state=lambda: {"of": {}}, season=season, summary=summary))
