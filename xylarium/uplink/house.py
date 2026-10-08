"""
Xylarium uplink house: barren-realms' ancients' house relaying its seats to the minds on the hyphae (seat wire v1).

Each turn of the relay (`turn`): post the SEATS listing when it changes; read the house's mail for TAKE and CALL;
answer a TAKE with TAKEN (seats.take); apply a CALL through the game's own doors (seats.call) and answer it with an
OUTCOME; and post each held seat's PERCEPT when its beat comes round, with the built-in mind's counsel. The game
side is seats.py; the bytes are seat_wire.py. In-game names travel as Keys (sha256), mapped back here.
"""

import hashlib
import os
import struct
from fractions import Fraction
from typing import Any, Callable, Dict, List, Optional, Tuple

from xylarium.uplink import anastome as an
from xylarium.uplink import seat_wire as w

REASON = {"ok": 0, "no such seat": 1, "held by another mind": 2, "not this mind's seat": 3, "no such function": 4,
          "refused in the game": 5, "bad signature": 6, "unknown name": 7}
MOTIONS = ("Rotate90", "Rotate180", "Rotate270", "FlipH", "FlipV", "Transpose")


def state(kernel: Any) -> Dict[str, Any]:
    from xylarium.kernel import seats
    return seats.stats(kernel).setdefault("wire", {"numbers": {}, "mail_seq": 0, "epoch": 0, "listed": None,
                                                   "beats": {}, "seq": 0})


def numbered(kernel: Any) -> List[Dict[str, Any]]:
    """The seats with stable wire numbers (u32), assigned once and kept."""
    from xylarium.kernel import seats
    st = state(kernel)
    out = seats.seats(kernel)
    for s in out:
        s["n"] = st["numbers"].setdefault(s["id"], len(st["numbers"]) + 1)
    return out


def names(kernel: Any) -> Dict[bytes, str]:
    """Every in-game name a call may carry, by its Key: peoples, realms, houses, wars."""
    from xylarium.kernel import relations, stewardship
    pool = set(relations._peoples(kernel)) | set(stewardship.realms(kernel))
    for k in ("dynasties", "realmwars"):
        if k in kernel.state:
            pool |= set(kernel.state[k].get("houses", {}) or {}) | set(kernel.state[k].get("wars", {}) or {})
    return {w.name_key(n): n for n in pool}


def kwargs_of(kernel: Any, fn: str, args: List[Tuple[int, Any]]) -> Optional[Dict[str, Any]]:
    """A call's typed args as the game's order arguments; None where a Key names nothing the game holds."""
    nm = names(kernel)

    def name(i: int) -> Optional[str]:
        return nm.get(bytes(args[i][1])) if i < len(args) and args[i][0] == w.KEY else None
    if fn in ("send", "recall", "claim"):
        return {"realm": name(0)} if name(0) else None
    if fn == "grant":
        return {"house": name(0)} if name(0) else None
    if fn in ("ascend", "quarantine"):
        return {"people": name(0)} if name(0) else None
    if fn == "fold":
        return {"war": name(0), "deed": "fold" if len(args) < 2 or args[1][1] else "yield"} if name(0) else None
    if fn == "handle":
        return {"how": w.HANDLE[int(args[0][1]) % len(w.HANDLE)]}
    if fn == "forge":
        return {"anchor": int(args[0][1]), "target": int(args[1][1])}
    if fn == "fortify":
        return {"sector": int(args[0][1]), "units": Fraction(args[1][1])}
    if fn == "answer":
        steps: List[Dict[str, Any]] = []
        for _, c in args:
            c = int(c)
            if 1 <= c <= 6:
                steps.append({"motion": MOTIONS[c - 1]})
            elif c >= 0x100:
                frm, to = divmod(c - 0x100, 16)
                if steps and "hue" in steps[-1]:
                    steps[-1]["hue"].append((frm, to))
                else:
                    steps.append({"hue": [(frm, to)]})
        return {"steps": steps}
    return {}


def percept_records(kernel: Any, p: Dict[str, Any]) -> Tuple[list, list]:
    """A seat's percept as typed records and counsel."""
    from xylarium.kernel import ascendance
    from xylarium.kernel import crystal as C
    recs: list = []
    counsel: list = []
    ruling = {"pending": 0, "ascended": 1, "quarantine": 2}
    for who, r in (p.get("petitions") or {}).items():
        recs.append((1, [(w.KEY, w.name_key(who)), (w.COUNT, ruling.get(r["ruling"], 0))]))
        for i, b in enumerate(ascendance.BOOKS):
            pair = (r.get("books") or {}).get(b)
            if pair:
                recs.append((2, [(w.KEY, w.name_key(who)), (w.COUNT, i), (w.Q_, Fraction(pair["syntropic"])),
                                 (w.Q_, Fraction(pair["entropic"]))]))
    if p.get("role") == "ancients":
        from xylarium.kernel import intellect
        recs += [(3, [(w.COUNT, op)]) for op in intellect.vocabulary(kernel, p["on"]) if isinstance(op, int)]
    if p.get("task"):
        recs.append((4, [(w.KEY, hashlib.sha256(bytes.fromhex(p["task"]["id"])).digest())]))
    for realm in p.get("realms") or []:
        recs.append((5, [(w.KEY, w.name_key(realm))]))
    for c in p.get("counsel") or []:
        if c.get("call") in ("ascend", "quarantine"):
            pair = ((p["petitions"].get(c["people"]) or {}).get("books") or {}).get(c.get("lead") or "", {})
            worth, cost = (Fraction(pair["entropic"]), Fraction(pair["syntropic"])) if pair else (0, 0)
            counsel.append((w.FN_ID[c["call"]], [(w.KEY, w.name_key(c["people"]))], worth, cost))
        elif c.get("call") == "answer":
            codes = []
            ops = dict(zip(MOTIONS, C.FRAME_OPS))
            for st in c["steps"]:
                if "motion" in st:
                    codes.append((w.COUNT, ops[st["motion"]]))
                else:
                    codes += [(w.COUNT, 0x100 + 16 * a + b) for a, b in st["hue"]]
            counsel.append((w.FN_ID["answer"], codes, 0, 0))
    return recs, counsel


def turn(kernel: Any, speak: Callable[[bytes], bytes], mail: Callable[[], List[Tuple[int, int, bytes]]]) -> Dict[str, int]:
    """One turn of the relay. `speak` posts an act and returns the hypha's reply; `mail` returns the house's new
    (seq, sub-kind, act) since its last read."""
    from xylarium.kernel import seats
    house, domain = an.key("ancients"), an.vk(an.key("domain"))
    st = state(kernel)
    listing = numbered(kernel)
    by_n = {s["n"]: s for s in listing}
    did = {"listed": 0, "taken": 0, "outcomes": 0, "percepts": 0}
    sig = [(s["n"], s["role"], s["on"], s["beat"], tuple(s["functions"])) for s in listing]
    if st["listed"] != repr(sig):
        st["epoch"] += 1
        speak(w.seats_post(house, domain, st["epoch"], listing))
        st["listed"] = repr(sig)
        did["listed"] = 1
    for seq, sub, act in mail():
        st["mail_seq"] = max(st["mail_seq"], seq)
        if sub == w.TAKE:
            t = w.read_take(act)
            if t is None or t["domain"] != domain:
                continue
            s = by_n.get(t["seat"])
            res = {"ok": False, "why": "no such seat"} if s is None else \
                {"ok": False, "why": "bad signature"} if not t["ok"] else seats.take(kernel, s["id"], t["mind"].hex())
            reason = 0 if res["ok"] else REASON.get(res.get("why", ""), REASON["held by another mind"])
            speak(w.taken_post(house, domain, t["seat"], t["mind"], res["ok"], reason))
            did["taken"] += 1
        elif sub == w.CALL:
            c = w.read_call(act)
            if c is None or c["domain"] != domain:
                continue
            s = by_n.get(c["seat"])
            fn = w.FUNCTIONS.get(c["fn"], (None,))[0]
            if s is None:
                res, reason = {"ok": False}, REASON["no such seat"]
            elif not c["ok"]:
                res, reason = {"ok": False}, REASON["bad signature"]
            elif fn is None:
                res, reason = {"ok": False}, REASON["no such function"]
            else:
                kw = kwargs_of(kernel, fn, c["args"])
                if kw is None:
                    res, reason = {"ok": False}, REASON["unknown name"]
                else:
                    res = seats.call(kernel, s["id"], c["mind"].hex(), fn, **kw)
                    reason = 0 if res.get("ok") else (REASON["not this mind's seat"]
                                                     if "not held by this mind" in str(res.get("why")) else
                                                     REASON["refused in the game"])
            deed = hashlib.sha256(repr((c["ref"], res)).encode()).digest()
            speak(w.outcome_post(house, domain, c["seat"], c["mind"], c["ref"], bool(res.get("ok")), reason, deed))
            did["outcomes"] += 1
    for s in listing:
        mind = seats.holder(kernel, s["id"])          # read now: a TAKE this turn binds before its first beat
        if not mind:
            continue
        last = st["beats"].get(s["id"])
        if last is not None and kernel.cycle_count - last < Fraction(s["beat"]):
            continue
        p = seats.percept(kernel, s["id"]) or {}
        recs, counsel = percept_records(kernel, p)
        st["seq"] += 1
        speak(w.percept_post(house, domain, s["n"], bytes.fromhex(mind), kernel.cycle_count, st["seq"], recs, counsel))
        st["beats"][s["id"]] = kernel.cycle_count
        did["percepts"] += 1
    return did


def on_hypha(kernel: Any, addr: str) -> Optional[Dict[str, int]]:
    """One relay turn against a hypha: posts spoken to it, the house's mail read from it. None where the hypha does
    not speak the seat wire (silence to the act)."""
    host, port = addr.rsplit(":", 1)
    where = (host, int(port))
    reader = an.key("ancients")
    probe = an.speak(where, w.read_mail(reader, state(kernel)["mail_seq"], os.urandom(32)), timeout=10)
    items = w.read_mail_reply(probe) if probe else None
    if items is None:
        return None
    return turn(kernel, lambda act: an.speak(where, act, timeout=10), lambda: items)
