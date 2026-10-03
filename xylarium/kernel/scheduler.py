"""
Xylarium scheduler: minds act when they get to it, and their chances are locked to the universe.

EVENTS. A mind acts at its own cadence, not on the engine's: a captain's next turn comes 1/speed cycles after its
last, where speed is its substrate's kinetic pace (laws.cognition: hot minds are quick, cold minds slow). A turn
that changes nothing - no move, no trade, no money, no turns spent - means the mind has nothing to do yet, and it
looks again twice as late, up to once a fiscal quarter (when the books it answers to change); any turn that does
something resets it to its own pace. The queue is ordered by (time, kind, entity): exact, and the same however the
dictionaries holding the captains happen to iterate. Time inside a cycle is counted in MOMENTS, so a mind six
times as quick as ours acts six times a cycle.

The engine's compute budget (config.AI_TURN_BUDGET) caps how many minds act in one cycle; the rest are not
dropped, they are first in line the next cycle (they are the most overdue).

LOCKED-IN CHANCE. The universe is deterministic; minds are probabilistic - but every draw comes from a stream fixed by
(universe seed, what is acting, when). lock() seeds the stream before each mind's turn, each phase of the cycle and
each season: the same universe replays identically at any velocity, and a change to one mind's choices does not
shift another's luck. stream() gives the same seed for code that keeps its own random.Random.
"""

import hashlib
import heapq
import random
from typing import Any, Callable, Dict, List, Optional, Tuple

MOMENTS = 1000                     # a cycle, divided: when within it a quick mind acts


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "scheduler")


# ---------------------------------------------------------------------- locked-in chance
def stream(kernel: Any, *parts: Any) -> int:
    """A 64-bit seed fixed by the universe's seed and what is drawing (independent of PYTHONHASHSEED)."""
    key = "|".join(str(p) for p in (getattr(kernel, "seed", 0),) + parts).encode()
    return int.from_bytes(hashlib.blake2b(key, digest_size=8).digest(), "big")


def lock(kernel: Any, *parts: Any) -> None:
    """Seed the stream of chance for what acts next."""
    random.seed(stream(kernel, *parts))


def rng(kernel: Any, *parts: Any) -> random.Random:
    return random.Random(stream(kernel, *parts))


# ---------------------------------------------------------------------- the queue
HANDLERS: Dict[str, Callable[[Any, str], Optional[int]]] = {}


def handler(kind: str) -> Callable:
    """Register what an event of this kind does: fn(kernel, entity) -> moments until its next event, or None."""
    def wrap(fn: Callable[[Any, str], Optional[int]]) -> Callable:
        HANDLERS[kind] = fn
        return fn
    return wrap


def at(kernel: Any, moment: int, kind: str, entity: str) -> None:
    heapq.heappush(stats(kernel)["queue"], [int(moment), kind, str(entity)])


def now_moment(kernel: Any) -> int:
    return int(kernel.cycle_count) * MOMENTS


def pending(kernel: Any, kind: Optional[str] = None) -> List[Tuple[int, str, str]]:
    return sorted(tuple(e) for e in stats(kernel)["queue"] if kind is None or e[1] == kind)


def run_due(kernel: Any, kinds: Tuple[str, ...], budget: Optional[int] = None) -> int:
    """Run every event of these kinds due by the end of this cycle, in time order, each with its own stream;
    at most `budget` of them (the rest stay first in line)."""
    st = stats(kernel)
    q = st["queue"]
    end = now_moment(kernel) + MOMENTS
    ran, held = 0, []
    while q and q[0][0] < end:
        ev = heapq.heappop(q)
        t, kind, entity = ev
        if kind not in kinds:
            held.append(ev)
            continue
        if budget is not None and ran >= budget:
            held.append(ev)
            st["deferred"] = st.get("deferred", 0) + 1
            break
        lock(kernel, kind, entity, t)
        nxt = HANDLERS[kind](kernel, entity)
        ran += 1
        if nxt is not None:
            # never twice in a moment; a mind overdue from the budget takes its next turn from now
            heapq.heappush(q, [max(t, now_moment(kernel)) + max(1, int(nxt)), kind, entity])
    for ev in held:
        heapq.heappush(q, ev)
    st["ran"] = st.get("ran", 0) + ran
    return ran


# ---------------------------------------------------------------------- minds
_SPEED: Dict[str, float] = {}


def pace(metabolism: Optional[str]) -> int:
    """Moments between a mind's turns at its own kinetic pace (1 cycle for a mind at Earth's temperature)."""
    m = metabolism or "biotic"
    if m not in _SPEED:
        from xylarium.kernel import laws
        _SPEED[m] = laws.cognition(m)["speed"]
    return max(1, int(round(MOMENTS / max(1e-6, _SPEED[m]))))


def _quarter_moments() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES * MOMENTS


def _fingerprint(captain: Any) -> Tuple:
    ship = getattr(captain, "ship", None)
    cargo = getattr(ship, "cargo", None)
    return (captain.sector_id, captain.credits, captain.turns_left, getattr(cargo, "holds_used", None),
            getattr(ship, "fighters", None), getattr(ship, "shields", None), getattr(captain, "active_research", None))


def wake(kernel: Any, captain_id: str) -> None:
    """Something happened to this mind: it takes its next turn at its own pace again."""
    stats(kernel)["idle"].pop(str(captain_id), None)


@handler("mind")
def _mind_turn(kernel: Any, cid: str) -> Optional[int]:
    cap = kernel.captains.get(cid)
    st = stats(kernel)
    if cap is None or not cap.is_ai:
        st["minds"].pop(cid, None)
        st["idle"].pop(cid, None)
        return None
    from xylarium.kernel.ai import AIManager
    before = _fingerprint(cap)
    AIManager.execute_turn(kernel, cap)
    idle = st["idle"]
    if _fingerprint(cap) == before:
        idle[cid] = idle.get(cid, 0) + 1
        st["idle_turns"] = st.get("idle_turns", 0) + 1
    else:
        idle.pop(cid, None)
    base = pace(getattr(cap, "metabolism", None))
    return min(_quarter_moments(), base << min(idle.get(cid, 0), 16))


def minds(kernel: Any) -> int:
    """This cycle's captains' turns: newly seen AI captains join the queue now; the due ones act."""
    from xylarium.config import AI_TURN_BUDGET
    st = stats(kernel)
    known = st["minds"]
    t = now_moment(kernel)
    for cap in sorted((c for c in kernel.captains.values() if c.is_ai and c.id not in known), key=lambda c: c.id):
        # minds are not synchronised: each first wakes at its own phase within its own pace
        first = t + stream(kernel, "phase", cap.id) % pace(getattr(cap, "metabolism", None))
        known[cap.id] = first
        at(kernel, first, "mind", cap.id)
    return run_due(kernel, ("mind",), AI_TURN_BUDGET)


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    idle = st["idle"]
    return {"queued": len(st["queue"]), "minds": len(st["minds"]), "ran": st.get("ran", 0),
            "deferred": st.get("deferred", 0), "idle_turns": st.get("idle_turns", 0),
            "resting_minds": sum(1 for v in idle.values() if v > 0)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="scheduler",
    state=lambda: {"queue": [], "minds": {}, "idle": {}, "ran": 0, "deferred": 0, "idle_turns": 0},
    summary=summary,
))
