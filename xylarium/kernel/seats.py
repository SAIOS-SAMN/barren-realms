"""
Xylarium seats: the house relay's game side - the seats a mind outside the game may take, what each perceives, the
calls it may make, and what came of them (Concordance 3.8; the seat surface the universes share).

Mycelium-client minds seat at the COUNCIL OF THE ANCIENTS only (Concordance 3.9): each ancients' house seats its
council, which earns mu by court work. The progenitors' parliaments and the stewards' realms play in game - no
network mind sits there. The house posts its seats, binds a mind to one (TAKE: one mind per seat, by its verifying
key), posts each seat's PERCEPT on the seat's own beat, applies the mind's CALLs, and keeps each OUTCOME as a deed
on the seat's books. The wire (the acts on the hypha) is the seam this module is spoken through; every number
here is exact.

  ancients     an ancients' house (court.py): its council has ONE SEAT PER WORLD the house holds (operator,
               3.9) - it grows as the ancients expand; each seat is put a court task when it has none
               (court.hand_tasks); its mind answers with "answer" - its own rule's tape and its outputs - filed under
               the ancients' reserve key (puzzle solving is the minds')
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional

FUNCTIONS = {"ancients": ("answer",)}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "seats")


def pid(vk_hex: str, seat_id: str) -> str:
    """The game's name for a mind in a seat: its key, short, at that seat - one mind may hold many seats, and each is
    its own player in the game (its realm, its line, its books), all signed by the one key."""
    return f"mind:{vk_hex[:16]}@{seat_id}"


def _q(x: Any) -> str:
    return str(Fraction(x))


# ---------------------------------------------------------------------- SEATS
def seats(kernel: Any) -> List[Dict[str, Any]]:
    """Every seat a mind may take: id, role, what it stands on, its functions, its beat (cycles), who holds it."""
    from xylarium.kernel import court
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    held = stats(kernel)["held"]
    out: List[Dict[str, Any]] = []
    from xylarium.kernel import relations
    worlds = relations._peoples(kernel)
    for house in court.houses(kernel):                    # the council of the ancients: the only seats network minds
        for w in sorted(worlds.get(house) or [], key=lambda p: p.id):   # take (3.9) - one seat for every world the
            out.append({"id": f"ancients:{house}@{w.id}", "role": "ancients", "on": house, "world": w.id,   # house
                        "beat": _q(4 * FISCAL_QUARTER_CYCLES)})   # holds: the council grows as the ancients do
    for s in out:
        s["functions"] = list(FUNCTIONS[s["role"]])
        s["held_by"] = held.get(s["id"])
    return out


def _seat(kernel: Any, seat_id: str) -> Optional[Dict[str, Any]]:
    return next((s for s in seats(kernel) if s["id"] == seat_id), None)


# ---------------------------------------------------------------------- TAKE
def take(kernel: Any, seat_id: str, vk_hex: str, lapsed: bool = False) -> Dict[str, Any]:
    """Bind a mind to a seat - one mind per seat. A seat whose mind has LAPSED (gone silent on it: the relay's
    measure) is taken from it by another mind that asks."""
    s = _seat(kernel, seat_id)
    if s is None:
        return {"ok": False, "why": f"no seat {seat_id}"}
    held = stats(kernel)["held"]
    if held.get(seat_id) not in (None, vk_hex) and not lapsed:
        return {"ok": False, "why": "the seat is held by another mind"}
    p = pid(vk_hex, seat_id)
    held[seat_id] = vk_hex
    from xylarium.kernel import inputs
    inputs.record(kernel, ["seat", seat_id, "take"], [vk_hex])          # an input: a mind takes its seat
    return {"ok": True, "seat": seat_id, "as": p}


def release_unseatable(kernel: Any) -> List[str]:
    """Seats a network mind may no longer hold (Concordance 3.9: minds seat at the ancients' councils only) are
    released, and the game's own play takes them back: a progenitor line's player, a realm's steward, their roles
    and bindings - each release an input. Returns the seats released."""
    from xylarium.kernel import board, inputs, roles, stewardship
    st = stats(kernel)
    out = []
    offered = {x["id"] for x in seats(kernel)}
    for seat_id, vk_hex in list(st["held"].items()):
        if seat_id in offered:
            continue
        house = seat_id[len("ancients:"):].split("@")[0] if seat_id.startswith("ancients:") else None
        if house is not None:                             # a council seat before seats were per world: the house's
            home = next((x["id"] for x in seats(kernel) if x["on"] == house and x["id"] not in st["held"]), None)
            if home is not None and "@" not in seat_id:   # first free world's seat keeps its mind
                st["held"][home] = vk_hex
                if seat_id in st["tasks"]:
                    st["tasks"][home] = st["tasks"].pop(seat_id)
            st["held"].pop(seat_id, None)
            st["tasks"].pop(seat_id, None)
            if home is None or "@" in seat_id:            # a world the house no longer holds: its seat is gone
                inputs.record(kernel, ["seat", seat_id, "release"], [vk_hex])
                out.append(seat_id)
            continue
        p = pid(vk_hex, seat_id)
        role, _, on = seat_id.partition(":")
        if role == "progenitor":
            line = (board.stats(kernel).get("progenitors") or {}).get(on)
            if line is not None and line.get("player") == p:
                line.pop("player", None)
            st["lines"].pop(p, None)
        elif role == "steward":
            stw = stewardship.stats(kernel)["stewards"]
            if stw.get(on) == p:
                stw.pop(on, None)
        roles.stats(kernel)["of"].pop(p, None)
        st["held"].pop(seat_id, None)
        st["tasks"].pop(seat_id, None)
        inputs.record(kernel, ["seat", seat_id, "release"], [vk_hex])
        out.append(seat_id)
    return out


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
    """What the seat perceives now, exact: the court's task before it, if any."""
    s = _seat(kernel, seat_id)
    if s is None:
        return None
    rec: Dict[str, Any] = {"seat": seat_id, "role": s["role"], "on": s["on"], "cycle": kernel.cycle_count,
                           "functions": s["functions"], "counsel": []}
    task = task_of(kernel, seat_id)
    if task is not None:                                   # the court's task before it: the mind's own to solve
        rec["task"] = {"id": task["id"].hex(), "train": task["train"], "test": task["test"]}
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
        out = command.dispatch(kernel, pid(vk_hex, seat_id), function, **args)
    if s is not None:
        _outcome(kernel, seat_id, function, args, out)
        from xylarium.kernel import inputs
        inputs.record(kernel, ["seat", seat_id, "call", function],      # an input: a seated mind's call
                      [vk_hex] + [args[k].hex() if isinstance(args[k], bytes) else str(args[k]) for k in sorted(args)])
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
    if an.retry(v):                                        # not judged yet: the task stays, the answer is re-filed
        stats(kernel)["tasks"][s["id"]]["pending"] = {"tape": args["tape"].hex(), "outputs": args["outputs"].hex()}
        return {"ok": False, "why": "not judged yet - re-filed next stroke", "retry": True}
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
