"""
Xylarium court: the hyphae's registry tasks, relayed to the seated minds (Concordance 3.8, 4, 6.2a).

ALL PUZZLE SOLVING IS THE MYCELIUM-CLIENT MINDS' (operator ruling, 2026-10-09): a kernel grows no crystals to solve
court tasks. The house pulls a task under the ANCIENTS' reserve key and puts it before a seated mind that has none
(a PERCEPT, record kind 4 [Key(citation)]); the mind answers with fn 1 [Bytes(its rule's tape), Bytes(the test
outputs)], and the house files it under the reserve key - the court pays the ancients' reserve, in mu. A task left
unanswered PATIENCE cycles is let go. Every answer is a deed on the seat's house's books: closed (bounty or floor,
its mu) or refused (the court's reason). The same shape as xylarium-kernel's house.rs (fn 1 SOLVE).

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


PATIENCE = 600                  # cycles a task waits before its seat before it is let go (house.rs)


def hand_tasks(kernel: Any, speak: Any) -> int:
    """Put a court task before every seated mind that has none, and let go a task left past its patience. `speak`
    posts an act to the hypha and returns its reply. Returns how many were handed."""
    from xylarium.kernel import seats
    from xylarium.uplink import anastome as an
    tasks = seats.stats(kernel)["tasks"]
    st = stats(kernel)
    for sid, t in list(tasks.items()):
        if kernel.cycle_count - int(t.get("since", kernel.cycle_count)) > PATIENCE:
            tasks.pop(sid)
            st["let_go"] = st.get("let_go", 0) + 1
    for sid, t in list(tasks.items()):                        # an answer not judged yet: filed again, as it was
        if t.get("pending"):
            s = next((x for x in seats.seats(kernel) if x["id"] == sid), None)
            if s is not None:
                seats._answer(kernel, s, {"tape": bytes.fromhex(t["pending"]["tape"]),
                                          "outputs": bytes.fromhex(t["pending"]["outputs"])})
    handed = 0
    for s in seats.seats(kernel):
        if not s["held_by"] or s["id"] in tasks:
            continue
        task = an.read_task(speak(an.task_request(an.key("ancients"))))
        if task is None or not task["train"] or not task["test"]:
            break                                          # the registry's book is settled: no task is no work
        seats.hold_task(kernel, s["id"], task)
        handed += 1
    st["handed"] = st.get("handed", 0) + handed
    return handed


def season(kernel: Any) -> List[str]:
    """The court is met by the seated minds, on the house relay's beat (house.turn): the year adds nothing here."""
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)["of"]
    return {"houses": len(st), "closed": sum(r["closed"] for r in st.values()),
            "refused": sum(r["refused"] for r in st.values()), "handed": stats(kernel).get("handed", 0),
            "let_go": stats(kernel).get("let_go", 0)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="court", state=lambda: {"of": {}}, season=season, summary=summary))
