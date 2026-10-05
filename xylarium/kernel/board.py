"""
Xylarium board: the minds above the realms - the watcher (T1), who sees across them, and the progenitor (T0), who
folds space and time to settle what no steward can - by the mind core (mindcore.py).

THE WATCHER'S BOOKS (its sites: the realms, and the appeals between them):
  lives    lives taken within each realm, against those its stewards' rulings have stopped
  appeals  lives taken between the parties of each appeal since it went up (what waits on the progenitors)
Once a year the watcher brings the appeal deepest in its books before the progenitors (within one book, the deepest
first) - the order of the progenitors' attention, never a verdict.

THE PROGENITOR'S BOOKS (its sites: the board):
  appeals     what the watcher has brought before it
  minds       the minds the universe was expected to raise by now / those it has raised
  unsheltered lives that died with their suns, or in extinctions, in the span / lives carried to safety
A progenitor seated by a player reads these books and decides. Where none is seated, the ancients' own progenitor
line - the first mind's line, older than every realm - seals what the watcher brings before it: its seal stands for
good and joins the parties' worldlines. What a seal did is read the next year as the lives still taken between the
parties: a crystal if it stopped them, else a wall (the seal itself cannot be undone - the ancients' laws are above).
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import mindcore as mc

WATCHER_BOOKS = ("appeals", "lives")
PROGENITOR_BOOKS = ("appeals", "minds", "unsheltered")
SHELTER_KINDS = ("PERISHED", "EXTINCTION", "ABANDONED")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "board")


def _line(kernel: Any, key: str, seat: str) -> Dict[str, Any]:
    st = stats(kernel)
    rec = st.get(key)
    if rec is None:
        from xylarium.kernel import scheduler
        from xylarium.kernel.natives import _name
        rec = st[key] = {"name": _name(scheduler.rng(kernel, seat, "line")), "since": kernel.cycle_count,
                         "seat": seat, "mind": mc.new_mind(), "acts": 0}
    return rec


def watcher_books(kernel: Any) -> mc.Chain:
    from xylarium.kernel import stewardship
    need: List[Tuple[str, str, Any]] = []
    have: List[Tuple[str, str, Any]] = []
    span = 100 * stewardship.RULING_YEARS
    for realm in stewardship.realms(kernel):
        res = stewardship.books(kernel, realm)
        taken = sum((v for (s, b), v in res.items() if b in ("lives", "young") and v > 0), Fraction(0))
        need.append((realm, "lives", taken))
        have.append((realm, "lives", sum(1 for r in stewardship.stats(kernel)["rulings"].values()
                                          if r["realm"] == realm and r["cycle"] >= kernel.cycle_count - span)))
    for r in stewardship.stats(kernel)["appeals"]:
        need.append((r["id"], "appeals", stewardship._stake_since(kernel, r["a"], r["b"], r["cycle"]) + 1))
    return mc.residual(mc.measure(need), mc.measure(have))


def progenitor_books(kernel: Any) -> mc.Chain:
    from xylarium.kernel import cosmos, history, stewardship
    need: List[Tuple[str, str, Any]] = []
    have: List[Tuple[str, str, Any]] = []
    for r in stewardship.stats(kernel)["appeals"]:
        if r.get("before"):
            need.append((r["id"], "appeals", stewardship._stake_since(kernel, r["a"], r["b"], r["cycle"]) + 1))
    for r in stewardship.stats(kernel)["rulings"].values():
        if str(r.get("sealed_by", "")).startswith("ancients:"):          # what its seals have not stopped
            need.append((r["id"], "sealed", stewardship._stake_since(kernel, r["a"], r["b"], r["sealed_at"])))
    if cosmos.is_cosmic(kernel):
        need.append(("board", "minds", mc.q(cosmos.expected_by(kernel, cosmos.deep_gyr(kernel)))))
        have.append(("board", "minds", cosmos.stats(kernel).get("arisen", 0)))
    since = kernel.cycle_count - 100 * stewardship.RULING_YEARS
    lost = sum(float(e.get("magnitude") or 0) for e in history.stats(kernel)["recent"]
               if e.get("kind") in SHELTER_KINDS and e.get("cycle", 0) >= since)
    carried = sum(float(e.get("magnitude") or 0) for e in history.stats(kernel)["recent"]
                  if e.get("kind") in ("RESCUE", "EXODUS") and e.get("cycle", 0) >= since)
    need.append(("board", "unsheltered", lost))
    have.append(("board", "unsheltered", carried))
    return mc.residual(mc.measure(need), mc.measure(have))


def seated_progenitor(kernel: Any) -> Optional[str]:
    from xylarium.kernel import roles
    return next((pid for pid, r in roles.stats(kernel).get("of", {}).items() if r == "progenitor"), None)


def season(kernel: Any) -> List[str]:
    """Once a year: the watcher brings the deepest appeal before the progenitors; where no player holds the
    progenitor's seat, the ancients' line seals the deepest appeal before it, and reads what its last seal did."""
    from xylarium.kernel import stewardship
    if (kernel.cycle_count // 25) % 4 or "stewardship" not in getattr(kernel, "state", {}):
        return []
    logs: List[str] = []
    w = _line(kernel, "watcher", "watcher")
    wres = watcher_books(kernel)
    entry = mc.lead({k: v for k, v in wres.items() if k[1] == "appeals"}, WATCHER_BOOKS, deepest=True)
    if entry is not None:
        rec = next((r for r in stewardship.stats(kernel)["appeals"] if r["id"] == entry[0]), None)
        if rec is not None and not rec.get("before"):
            rec["before"] = kernel.cycle_count
            w["acts"] += 1
            logs.append(f"[WATCHER] {w['name']} brings {rec['id']} ({rec['kind']}: {rec['a'].split(':', 1)[-1]} / "
                        f"{rec['b'].split(':', 1)[-1]}) before the progenitors.")
    if seated_progenitor(kernel) is not None:
        return logs                                            # a seated progenitor decides for itself
    p = _line(kernel, "progenitor", "progenitor")
    pres = progenitor_books(kernel)
    mc.seal(p["mind"], pres)
    entry = mc.lead(pres, PROGENITOR_BOOKS, deepest=True)
    if entry is not None and entry[1] == "appeals":
        res = stewardship._seal(kernel, f"ancients:{p['name']}", entry[0])
        if res.get("ok"):
            mc.intend(p["mind"], (entry[0], "sealed"), pres[entry], "seal", "appeal")   # read next year
            p["acts"] += 1
            r = res["ruling"]
            logs.append(f"[PROGENITOR] {p['name']} of the ancients seals the {r['kind']} between the "
                        f"{r['a'].split(':', 1)[-1]} and the {r['b'].split(':', 1)[-1]}.")
    return logs


def render(kernel: Any) -> str:
    """The board as the progenitors read it."""
    lines = ["=== THE BOARD ==="]
    for name, res, order in (("Watcher", watcher_books(kernel), WATCHER_BOOKS),
                             ("Progenitor", progenitor_books(kernel), PROGENITOR_BOOKS)):
        lines.append(f"  {name}'s books:")
        for book in order:
            for (site, b), v in sorted(res.items()):
                if b == book:
                    lines.append(f"    {book:<12} {site:<10} {float(v):>+14,.1f}")
    return "\n".join(lines)


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {k: {"name": v["name"], "acts": v["acts"]} for k, v in st.items() if isinstance(v, dict) and "name" in v}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="board", state=lambda: {}, season=season, summary=summary))
