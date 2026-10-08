"""
Xylarium field: what moves through the universe, carried - not walked (docs/FIELD_ENGINE.md).

Every singularity is a BELL: it rings its own pulse (a Source - the bounce, its echo, a dying star, a jet, a word).
What a bell sends reaches a place at the earliest time a physical carrier can bring it (light through ordinary space,
with its Shapiro delay; a throat across its span) - computed ONCE when it rings, and queued in exact deep time. Each
tick the arrivals the cosmic clock has passed are handed to the laws that take them (handlers by kind). The field's
value at a place and time is closed form: every arrived front's strength over its distance, shaped by its pulse's
decay - no walk over worlds. Events are for EXTERNAL arrivals; a people's own dynamics are never frozen waiting for
them. The field is internal physics (floats); arrival times enter the kernel as exact Fractions of deep time.
"""

import heapq
import math
from fractions import Fraction
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

HANDLERS: Dict[str, Callable[[Any, Dict[str, Any], Dict[str, Any]], None]] = {}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "field")


def handles(kind: str) -> Callable:
    """Register the law that takes a kind's arrivals: f(kernel, source, arrival)."""
    def wrap(f: Callable) -> Callable:
        HANDLERS[kind] = f
        return f
    return wrap


def place_of(kernel: Any, sector_id: int, gyr: Optional[float] = None) -> Optional[Tuple[float, float, float]]:
    """A system's galactocentric place (kpc) now - or at a deep time, as its orbit carries it."""
    from xylarium.kernel import cosmos
    p = cosmos.position(kernel, sector_id)
    return (p["x"], p["y"], p["z"]) if p else None


def light_gyr(a: Sequence[float], b: Sequence[float]) -> float:
    from xylarium.kernel import geometry
    return geometry.light_gyr(a, b)


CARRIERS: List[Callable[[Any, Dict[str, Any], int, Sequence[float]], Optional[float]]] = []


def carrier(f: Callable) -> Callable:
    CARRIERS.append(f)
    return f


@carrier
def _light(kernel: Any, src: Dict[str, Any], sector_id: int, at: Sequence[float]) -> Optional[float]:
    """Light through ordinary space: its proper travel time, Shapiro delay and all."""
    return float(src["t"]) + light_gyr(src["at"], at)


def arrival(kernel: Any, src: Dict[str, Any], sector_id: int, at: Sequence[float]) -> Optional[float]:
    """The earliest a physical carrier brings the source's front to a place (deep Gyr), or None."""
    times = [t for t in (c(kernel, src, sector_id, at) for c in CARRIERS) if t is not None]
    return min(times) if times else None


def ring(kernel: Any, src: Dict[str, Any], targets: Iterable[int]) -> int:
    """A bell rings: its arrival at each target system is computed once, by its earliest carrier, and queued in exact
    deep time. Returns the arrivals queued."""
    st = stats(kernel)
    st["next"] += 1
    sid = f"S{st['next']}"
    src = dict(src, id=sid, t=str(Fraction(src["t"])), at=list(src["at"]))
    st["sources"][sid] = src
    n = 0
    for target in targets:
        at = place_of(kernel, target)
        if at is None:
            continue
        t = arrival(kernel, src, target, at)
        if t is None:
            continue
        heapq.heappush(st["queue"], [float(t), str(Fraction(t)), sid, int(target)])    # ordered; exact beside
        n += 1
    return n


def pump(kernel: Any) -> int:
    """Hand every arrival the cosmic clock has passed to the law that takes its kind. Returns arrivals delivered."""
    from xylarium.kernel import cosmos
    st = stats(kernel)
    q = st["queue"]
    if not q:
        return 0
    now = Fraction(cosmos.deep_gyr(kernel))
    done = 0
    while q and Fraction(q[0][1]) <= now:
        _, t, sid, target = heapq.heappop(q)
        src = st["sources"].get(sid)
        if src is None:
            continue
        f = HANDLERS.get(src["kind"])
        if f is not None:
            f(kernel, src, {"t": t, "sector": target})
        done += 1
        src["delivered"] = src.get("delivered", 0) + 1
    st["delivered"] = st.get("delivered", 0) + done
    _forget(st, now)
    return done


FADED = 14.0                    # e-folds after which a pulse is a millionth of itself: gone from the field


def _forget(st: Dict[str, Any], now: Fraction) -> None:
    """A source is dropped once every arrival is delivered and it adds nothing more: an event with no pulse at once,
    a pulse once it has died away (FADED e-folds past its ringing)."""
    live = {e[2] for e in st["queue"]}
    for sid, src in list(st["sources"].items()):
        if sid in live:
            continue
        tau = float(src.get("tau") or 0.0)
        if tau <= 0 or float(now) - float(Fraction(src["t"])) > FADED * tau:
            st["sources"].pop(sid, None)


def value(kernel: Any, at: Sequence[float], t: float) -> float:
    """The field at a place and deep time: the sum over every source whose front has reached it of its strength over
    its distance, shaped by its pulse's decay since its front arrived (e-fold tau, Gyr). Closed form - no walk."""
    st = stats(kernel)
    total = 0.0
    for src in st["sources"].values():
        t0 = float(Fraction(src["t"]))
        d = max(1e-6, math.dist(src["at"], at))
        arrived = t0 + light_gyr(src["at"], at)
        if t < arrived:
            continue
        tau = float(src.get("tau") or 0.0)
        if tau <= 0:
            continue                                     # an event, not a pulse: it adds to no field
        total += float(src.get("strength", 1.0)) / d * math.exp(-(t - arrived) / tau)
    return total


def season(kernel: Any) -> List[str]:
    """Each season the fronts the cosmic clock has passed reach their places (each keeps its exact arrival time)."""
    pump(kernel)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"sources": len(st["sources"]), "queued": len(st["queue"]), "delivered": st.get("delivered", 0)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="field", state=lambda: {"sources": {}, "queue": [], "next": 0, "delivered": 0},
                             season=season, summary=summary))
