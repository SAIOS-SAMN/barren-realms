"""
Xylarium seats: the house relay's game side - the seats a mind outside the game may take, what each perceives, the
calls it may make, and what came of them (Concordance 3.8; the seat surface the universes share).

Mycelium-client minds hold the ANCIENTS', PROGENITORS' and STEWARDS' seats (peoples grow by their own minds,
intellect.py; captains are for players who want the personal touch). Barren-realms' ancients' house posts its
seats, binds a mind to one (TAKE: one mind per seat, by its verifying key), posts each seat's PERCEPT on the seat's
own beat with the built-in mind's COUNSEL, applies the mind's CALLs through the same doors a player's orders use
(command.py), and keeps each OUTCOME as a deed on the seat's books. A taken seat is skipped by the built-in mind, as
a player's is. The wire (the acts on the hypha) is the seam this module is spoken through; every number here is exact.

  ancients     an ancients' house (court.py)
  every seat   is put a court task when it has none (court.hand_tasks); its mind answers with "answer" - its own
               rule's tape and its outputs - filed under the ancients' reserve key (puzzle solving is the minds')
  progenitor   a line: send, recall, fold, handle, forge (command.py) - beat: one of its people's generations
  steward      a realm: claim, withdraw, grant, ascend, quarantine, fortify - beat: its steward's term
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional

FUNCTIONS = {"ancients": ("answer",),
             "progenitor": ("answer", "send", "recall", "fold", "handle", "forge"),
             "steward": ("answer", "claim", "withdraw", "grant", "ascend", "quarantine", "fortify")}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "seats")


def pid(vk_hex: str) -> str:
    """The game's name for a mind holding a seat: its key, short."""
    return f"mind:{vk_hex[:16]}"


def _q(x: Any) -> str:
    return str(Fraction(x))


# ---------------------------------------------------------------------- SEATS
def seats(kernel: Any) -> List[Dict[str, Any]]:
    """Every seat a mind may take: id, role, what it stands on, its functions, its beat (cycles), who holds it."""
    from xylarium.kernel import board, clocks, court, spheres, stewardship
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    held = stats(kernel)["held"]
    out: List[Dict[str, Any]] = []
    for house in court.houses(kernel):
        out.append({"id": f"ancients:{house}", "role": "ancients", "on": house, "beat": _q(4 * FISCAL_QUARTER_CYCLES)})
    for line in sorted(board.progenitors(kernel)):
        beat = clocks.lived_span(kernel, spheres.generation(kernel, line)) if line.startswith("civ:") else 0
        out.append({"id": f"progenitor:{line}", "role": "progenitor", "on": line, "beat": _q(beat)})
    for realm in stewardship.realms(kernel):
        out.append({"id": f"steward:{realm}", "role": "steward", "on": realm,
                    "beat": _q(stewardship.span_cycles(kernel, realm))})
    for s in out:
        s["functions"] = list(FUNCTIONS[s["role"]])
        s["held_by"] = held.get(s["id"])
    return out


def _seat(kernel: Any, seat_id: str) -> Optional[Dict[str, Any]]:
    return next((s for s in seats(kernel) if s["id"] == seat_id), None)


# ---------------------------------------------------------------------- TAKE
def take(kernel: Any, seat_id: str, vk_hex: str) -> Dict[str, Any]:
    """Bind a mind to a seat - one mind per seat; the built-in mind steps aside as it does for a player."""
    from xylarium.kernel import board, roles, stewardship
    s = _seat(kernel, seat_id)
    if s is None:
        return {"ok": False, "why": f"no seat {seat_id}"}
    held = stats(kernel)["held"]
    if held.get(seat_id) not in (None, vk_hex):
        return {"ok": False, "why": "the seat is held by another mind"}
    p = pid(vk_hex)
    if s["role"] == "steward":
        stewardship.seat_steward(kernel, p, p, s["on"])
    elif s["role"] == "progenitor":
        line = board.progenitors(kernel)[s["on"]]
        line["player"] = p
        roles.stats(kernel)["of"][p] = "progenitor"
        stats(kernel)["lines"][p] = s["on"]
    held[seat_id] = vk_hex
    return {"ok": True, "seat": seat_id, "as": p}


def holder(kernel: Any, seat_id: str) -> Optional[str]:
    return stats(kernel)["held"].get(seat_id)


def hold_task(kernel: Any, seat_id: str, task: Dict[str, Any]) -> None:
    """A court task before a seated mind, kept until it answers or is let go (its id as hex, so the record saves)."""
    stats(kernel)["tasks"][seat_id] = {"id": task["id"].hex(), "train": task["train"], "test": task["test"],
                                       "since": kernel.cycle_count}


def task_of(kernel: Any, seat_id: str) -> Optional[Dict[str, Any]]:
    t = stats(kernel)["tasks"].get(seat_id)
    return None if t is None else dict(t, id=bytes.fromhex(t["id"]))


# ---------------------------------------------------------------------- PERCEPT
def percept(kernel: Any, seat_id: str) -> Optional[Dict[str, Any]]:
    """What the seat perceives now, exact, with the built-in mind's counsel: what it would do in the seat."""
    from xylarium.kernel import ascendance
    s = _seat(kernel, seat_id)
    if s is None:
        return None
    rec: Dict[str, Any] = {"seat": seat_id, "role": s["role"], "on": s["on"], "cycle": kernel.cycle_count,
                           "functions": s["functions"], "counsel": []}
    task = task_of(kernel, seat_id)
    if task is not None:                                   # the court's task before it: the mind's own to solve
        rec["task"] = {"id": task["id"].hex(), "train": task["train"], "test": task["test"]}
    if s["role"] == "steward":
        petitions = {w: r for w, r in ascendance.stats(kernel)["of"].items() if r["realm"] == s["on"]} \
            if "ascendance" in kernel.state else {}
        rec["petitions"] = {w: {"ruling": r["ruling"], "books": r.get("books"), "since": r["since"]}
                            for w, r in sorted(petitions.items())}
        sat = ascendance.seat(kernel, s["on"])
        for w, r in sorted(petitions.items()):
            if r.get("books") and sat is not None:
                verdict, lead = ascendance.judge(kernel, w, r, sat)
                rec["counsel"].append({"call": "ascend" if verdict == "ascended" else "quarantine", "people": w,
                                       "lead": lead})
    elif s["role"] == "progenitor":
        from xylarium.kernel import board, stewardship
        line = board.progenitors(kernel).get(s["on"]) or {}
        rec["line"] = {"name": line.get("name"), "standing": line.get("standing")}
        rec["realms"] = [r for r in stewardship.realms(kernel) if stewardship.covers(kernel, s["on"], r)]
    return rec


# ---------------------------------------------------------------------- CALL and OUTCOME
def call(kernel: Any, seat_id: str, vk_hex: str, function: str, **args: Any) -> Dict[str, Any]:
    """A seated mind's call, applied through the game's own doors; its outcome kept as a deed on the seat's books."""
    from xylarium.kernel import command
    s = _seat(kernel, seat_id)
    if s is None:
        out = {"ok": False, "why": f"no seat {seat_id}"}
    elif holder(kernel, seat_id) != vk_hex:
        out = {"ok": False, "why": "the seat is not held by this mind"}
    elif function not in FUNCTIONS[s["role"]]:
        out = {"ok": False, "why": f"no function '{function}' for a {s['role']}"}
    elif function == "answer":
        out = _answer(kernel, s, args)
    else:
        out = command.dispatch(kernel, pid(vk_hex), function, **args)
    if s is not None:
        _outcome(kernel, seat_id, function, args, out)
    return out


def _answer(kernel: Any, s: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """File a seated mind's answer to the task before its seat - its own rule's tape and its outputs, as ACT_SOLVE
    writes them - under the ancients' reserve key: the court pays the reserve."""
    from xylarium.kernel import court
    from xylarium.uplink import anastome as an
    task = task_of(kernel, s["id"])
    addr = court.endpoint()
    if task is None or addr is None:
        return {"ok": False, "why": "no court task before the seat" if task is None else "no hypha named"}
    if not args.get("tape") or not args.get("outputs"):
        return {"ok": False, "why": "the answer does not read"}
    host, port = addr.rsplit(":", 1)
    body = an.speak((host, int(port)), an.solve_raw(an.key("ancients"), task["id"], args["outputs"], args["tape"]))
    v = an.read_verdict(body)
    v["verdict"] = {2: "bounty", 1: "floor"}.get(v.get("code"), "nothing")
    kind = "closed" if v.get("verdict") in ("bounty", "floor") else "refused"
    court._deed(kernel, s["on"], kind, {"verdict": v.get("verdict"), "why": v.get("why"), "mu": v.get("mu"),
                                        "by": "seated mind"})
    stats(kernel)["tasks"].pop(s["id"], None)
    return {"ok": kind == "closed", "verdict": v.get("verdict"), "mu": v.get("mu"), "why": v.get("why")}


def _outcome(kernel: Any, seat_id: str, function: str, args: Dict[str, Any], out: Dict[str, Any]) -> None:
    from xylarium.kernel import history
    rec = stats(kernel)["books"].setdefault(seat_id, {"calls": 0, "done": 0, "refused": 0, "last": None})
    rec["calls"] += 1
    rec["done" if out.get("ok") else "refused"] += 1
    rec["last"] = {"function": function, "cycle": kernel.cycle_count, "ok": bool(out.get("ok")),
                   "why": out.get("why")}
    history.event(kernel, "SEAT_CALL", f"The {seat_id} seat calls {function}: {'done' if out.get('ok') else 'refused'}",
                  cause=str(out.get("why") or ""), data={"seat": seat_id, "function": function,
                                                         "args": {k: str(v) for k, v in args.items()}})


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"held": len(st["held"]), "calls": sum(b["calls"] for b in st["books"].values())}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="seats", state=lambda: {"held": {}, "lines": {}, "tasks": {}, "books": {}},
                             summary=summary))
