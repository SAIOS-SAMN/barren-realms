"""
Xylarium court: the hyphae's registry tasks, met in the world by the ancients' minds (Concordance 3.8, 4, 6.2a).

Only the ancients are connected to the tubes: a court task reaches an ANCIENTS' HOUSE (board.ancient_peoples), once a
year of its thinking, as a puzzle met in its world. Its mind answers it the way it climbs its own ladders
(intellect.py): it reads the coordinate off the train pairs and DECOMPACTS it into a program over the crystals its
people holds - no search, nothing it has not learned. It fails where its crystals cannot express the coordinate, or
where the work (every cell through the frame orbit and each op it writes) exceeds the thought it has in the year.
A program it can write is checked at home on every train pair, translated into the court's steps (each crystal a
rigid motion of the grid, a recolouring a hue map: uplink.mind.steps_of), minted and judged at home by barren-solve,
and submitted signed with the ANCIENTS' key - the court pays the ancients, in mu. Every meeting is a deed on the
house's books: closed (bounty or floor, its mu), refused (the court's reason), or beyond it (by name).

Younger peoples meet no court task: they climb their own ladders in the world (intellect.forge), judged there.
The court is reached only where an endpoint is named (XYL_HYPHA, "host:port"); with none, no traffic leaves.
"""

import os
from fractions import Fraction
from typing import Any, Dict, List, Optional

ENDPOINT_ENV = "XYL_HYPHA"


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "court")


def endpoint() -> Optional[str]:
    return os.environ.get(ENDPOINT_ENV) or None


def houses(kernel: Any) -> List[str]:
    """The ancients' houses: the only minds the court is reached by."""
    from xylarium.kernel import board
    try:
        return sorted(board.ancient_peoples(kernel))
    except Exception:
        return []


def _thought(kernel: Any, house: str) -> float:
    """Operations of thought the house has in a year (intellect's measure)."""
    from xylarium.kernel import intellect
    rec = intellect._peoples(kernel).get(house)
    return rec["effort"] * intellect.OPS_PER_UNIT * 4 if rec else 0.0


def _grid(g: List[List[int]]) -> tuple:
    return tuple(tuple(int(c) for c in row) for row in g)


def meet(kernel: Any, house: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """The house's mind meets a court task: its own program, or why it has none. -> {"program", "steps",
    "outputs"} or {"beyond": reason}."""
    from xylarium.kernel import crystal as C
    from xylarium.kernel import intellect
    from xylarium.uplink import mind
    train = [(_grid(a), _grid(b)) for a, b in task["train"]]
    tests = [_grid(t) for t in task["test"]]
    if not train or not tests:
        return {"beyond": "no family to read"}
    program = intellect.decompact(intellect.vocabulary(kernel, house), {"rank": 2, "train": train, "test": tests[0]})
    if not program:
        return {"beyond": "its crystals cannot express the coordinate"}
    words = intellect.expand(program)
    cells = sum(len(g) * len(g[0]) for pair in train for g in pair) + sum(len(t) * len(t[0]) for t in tests)
    work = cells * (len(C.D4) + len(words))
    if work > _thought(kernel, house):
        return {"beyond": "the work exceeds its year's thought", "work": work}
    if any(C.run(words, a) != b for a, b in train):
        return {"beyond": "its program misreads a train pair"}
    steps = mind.steps_of(words)
    if steps is None:
        return {"beyond": "its program has no form in the court's language"}
    outs = [C.run(words, t) for t in tests]
    if any(o is None for o in outs):
        return {"beyond": "its program makes no grid of a test"}
    return {"program": words, "steps": steps, "work": work, "outputs": [[list(r) for r in o] for o in outs]}


def _deed(kernel: Any, house: str, kind: str, data: Dict[str, Any]) -> None:
    from xylarium.kernel import history
    rec = stats(kernel)["of"].setdefault(house, {"met": 0, "closed": 0, "refused": 0, "beyond": 0,
                                                  "mu": ["0", "0", "0", "0"]})
    rec["met"] += 1
    rec[kind] += 1
    if data.get("mu"):
        rec["mu"] = [str(Fraction(a) + Fraction(b)) for a, b in zip(rec["mu"], data["mu"])]
    history.event(kernel, "COURT", f"The {house.split(':', 1)[-1]} meet a court task: {kind}", actors=[house],
                  cause=data.get("why") or data.get("verdict") or "", data=data)


def season(kernel: Any) -> List[str]:
    """Once a year of thinking: each ancients' house meets the court task the registry hands it."""
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    if (kernel.cycle_count // FISCAL_QUARTER_CYCLES) % 4:
        return []
    addr = endpoint()
    if addr is None:
        return []
    from xylarium.uplink import anastome as an
    from xylarium.uplink import mind
    host, port = addr.rsplit(":", 1)
    logs: List[str] = []
    for house in houses(kernel):
        try:
            task = an.read_task(an.speak((host, int(port)), an.task_request(an.key("ancients"))))
        except Exception as e:                             # the hypha is another node: its fault never stops ours
            logs.append(f"[COURT] the hypha did not answer: {type(e).__name__}: {e}")
            break
        if task is None or not task["train"] or not task["test"]:
            break                                          # the registry's book is settled: an empty reply is no task
        from xylarium.kernel import seats
        if "seats" in kernel.state and seats.holder(kernel, f"ancients:{house}"):
            seats.hold_task(kernel, f"ancients:{house}", task)       # its seated mind answers it (seats.call)
            continue
        got = meet(kernel, house, task)
        if "beyond" in got:
            _deed(kernel, house, "beyond", {"why": got["beyond"]})
            continue
        v = mind.submit(addr, os.path.join(an.KEYS, "ancients.ed25519"), task, got["steps"], got["outputs"])
        kind = "closed" if v.get("verdict") in ("bounty", "floor") else "refused"
        _deed(kernel, house, kind, {"verdict": v.get("verdict"), "why": v.get("why"), "mu": v.get("mu"),
                                    "steps": got["steps"]})
        logs.append(f"[COURT] The {house.split(':', 1)[-1]}: {kind} ({v.get('verdict')}).")
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)["of"]
    return {"houses": len(st), "closed": sum(r["closed"] for r in st.values()),
            "beyond": sum(r["beyond"] for r in st.values())}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="court", state=lambda: {"of": {}}, season=season, summary=summary))
