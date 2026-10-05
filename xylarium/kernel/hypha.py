"""
Xylarium hypha: the galactic banking ledger the banks uplink to - append-only, hash-chained, agnostic (after
mycelium's receipt chains, LEDGER_EPOCH_DESIGN.md, and its POW++ family, MU-RECURSION 78.33).

No people, bank or steward keeps it, and none can edit it: every settlement that crosses a progenitor's lane or a
throat of the fabric, and every claim the clearing union books between central banks (banking.py: STAMP), is a
RECEIPT appended to a LANE (a reserve currency's, or STAMP) - its height, its kind, who paid whom how much in which
money, and the hash of the receipt before it. A receipt's hash covers all of that, so the chain answers for itself:
anyone can re-derive it (verify), and a receipt changed anywhere breaks every hash after it.

  POUW      proof of useful work - a passage delivered: the toll or tithe a passer paid is the closure, and its
            receipt names it (the only arm of the family the realm mints today; POWC and POWR are named, not paid)
  FOLD      once a year, behind a fully final prefix (everything before the season is settled), each lane writes
            its net per identity - closed circulation vanishes in the net, exactly - and a fold receipt citing the
            prefix's head; heights go on across it and the chain never breaks. The hot rows are only those since the
            last fold; the folds keep what the chain was owed.

Reserve currencies: the money a progenitor's lane is paid in is its keeper's own - the ancients keep their own
currencies, and every federation that passes converts into one of them (transit.py settles through the exchanges).
"""

import hashlib
import json
from fractions import Fraction
from typing import Any, Dict, List, Optional

KINDS = ("pouw", "stamp", "fold")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "hypha")


def _hash(prev: str, body: Dict[str, Any]) -> str:
    return hashlib.sha256((prev + json.dumps(body, sort_keys=True, default=str)).encode()).hexdigest()


def _chain(kernel: Any, lane: str) -> Dict[str, Any]:
    return stats(kernel)["chains"].setdefault(lane, {"height": 0, "head": "genesis", "rows": [], "net": {},
                                                     "epochs": []})


def append(kernel: Any, lane: str, kind: str, payer: str, payee: str, amount: Any, currency: str,
           ref: Optional[str] = None) -> Dict[str, Any]:
    """A receipt on a lane: chained to the one before it."""
    c = _chain(kernel, lane)
    body = {"height": c["height"] + 1, "kind": kind, "payer": payer, "payee": payee, "amount": str(Fraction(amount)),
            "currency": currency, "cycle": int(getattr(kernel, "cycle_count", 0)), "ref": ref, "prev": c["head"]}
    rec = dict(body, hash=_hash(c["head"], body))
    c["rows"].append(rec)
    c["height"], c["head"] = rec["height"], rec["hash"]
    return rec


def verify(kernel: Any, lane: str) -> bool:
    """Re-derive the hot rows' chain: every hash from the row before it and its own body."""
    c = _chain(kernel, lane)
    prev = c["rows"][0]["prev"] if c["rows"] else c["head"]
    for r in c["rows"]:
        body = {k: v for k, v in r.items() if k != "hash"}
        if r["prev"] != prev or _hash(prev, body) != r["hash"]:
            return False
        prev = r["hash"]
    return not c["rows"] or prev == c["head"]


def fold(kernel: Any, lane: str) -> Optional[Dict[str, Any]]:
    """Behind the final prefix: each identity's net over it, a fold receipt citing its head; the prefix goes cold."""
    c = _chain(kernel, lane)
    rows = [r for r in c["rows"] if r["kind"] != "fold"]
    if not rows:
        return None
    net: Dict[str, Fraction] = {}
    for r in rows:
        a = Fraction(r["amount"])
        net[r["payer"]] = net.get(r["payer"], Fraction(0)) - a
        net[r["payee"]] = net.get(r["payee"], Fraction(0)) + a
    assert sum(net.values()) == 0                            # double entry: a lane's net is always nothing
    for who, v in net.items():
        if v:
            c["net"][who] = str(Fraction(c["net"].get(who, "0")) + v)
    head = c["head"]
    c["epochs"].append({"height": c["height"], "head": head, "rows": len(rows), "cycle": kernel.cycle_count})
    del c["epochs"][:-12]
    c["rows"] = []
    rec = append(kernel, lane, "fold", "ledger", "ledger", 0, lane, ref=head)
    c["rows"] = [rec]
    stats(kernel)["folds"] += 1
    return rec


def season(kernel: Any) -> List[str]:
    """Once a year: every lane folds behind the year's final prefix."""
    from xylarium.kernel import polity
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    for lane in sorted(stats(kernel)["chains"]):
        fold(kernel, lane)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"lanes": len(st["chains"]), "height": {k: c["height"] for k, c in sorted(st["chains"].items())},
            "folds": st["folds"], "verified": all(verify(kernel, k) for k in st["chains"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="hypha",
    state=lambda: {"chains": {}, "folds": 0},
    season=season,
    summary=summary,
))
