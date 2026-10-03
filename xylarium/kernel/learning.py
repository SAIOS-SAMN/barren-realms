"""
Xylarium learning: every mind remembers what its choices brought it, and chooses by that next time.

A council or a captain chooses by valuing its options (decide.py). Those values are its first guesses - what the
option should be worth, reckoned from what it can see. Learning is what turns guesses into judgement: each year a
mind sets what it did against how it fared, and every kind of choice it made that year is credited with how much
better or worse the mind did than it usually does (its own baseline - not anyone else's). An option that has served
it is valued higher next time; one that has failed it, lower - by exp(its learned advantage over its typical
swing), so a lesson's weight grows with how sure the mind is of it. Memory fades as knowledge does
(laws.KNOWLEDGE_DEPRECIATION): what served a people three generations ago weighs little now.

How it fares is its own measure: a people by its syntropy (syntropy.index: capacity, knowledge, worlds), a captain
by the log of what it holds. Nothing outside the mind tells it what is good.

ATTENTION. A mind weighs only as many options at once as its thought allows (attention): two for a mind that has
climbed no ladder, one more for each rung of fluid intelligence it holds (intellect.fluid), one more if it knows
itself (introspect.py). Asked to choose among more, it weighs those it first judges worth most - so a young people
overlooks what an elder would have seen.
"""

import math
from typing import Any, Dict, List, Optional

LESSON_CAP = 2.0                # a lesson can move a value by at most e^2 either way


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "learning")


def _rec(kernel: Any, holder: str) -> Dict[str, Any]:
    return stats(kernel)["of"].setdefault(holder, {"opts": {}, "pending": [], "score_at": None, "s0": None,
                                                   "mean": 0.0, "var": 0.0, "n": 0.0})


def record(kernel: Any, holder: Optional[str], name: str) -> None:
    if not holder or kernel is None or not hasattr(kernel, "state"):
        return
    pending = _rec(kernel, holder)["pending"]
    if name not in pending:
        pending.append(name)


def multiplier(kernel: Any, holder: Optional[str], name: str) -> float:
    """How much more (or less) this mind values an option of this kind for what such choices have brought it."""
    if not holder or kernel is None or "learning" not in getattr(kernel, "state", {}):
        return 1.0
    rec = stats(kernel)["of"].get(holder)
    if not rec:
        return 1.0
    o = rec["opts"].get(name)
    if not o or o["n"] <= 0:
        return 1.0
    spread = math.sqrt(max(1e-12, rec["var"])) + 1e-9
    sure = o["n"] / (o["n"] + 1.0)
    return math.exp(max(-LESSON_CAP, min(LESSON_CAP, o["adv"] / spread * sure)))


def attention(m: Dict[str, Any]) -> int:
    """How many options a mind can weigh at once."""
    return 2 + int(4.0 * float(m.get("fluid", 0.0) or 0.0)) + (1 if float(m.get("self_knowledge", 0.0) or 0.0) > 0
                                                               else 0)


def outcome(kernel: Any, holder: str) -> Optional[float]:
    """How a mind is faring, by its own measure."""
    if holder.startswith("captain:"):
        cap = kernel.captains.get(holder.split(":", 1)[1])
        if cap is None:
            return None
        held = float(cap.credits)
        fx = getattr(kernel, "fx_market", None)
        for cur, amt in (getattr(cap, "fx_wallet", None) or {}).items():
            try:
                held += fx.to_sol_value(cur, amt) if fx is not None else 0.0
            except Exception:
                pass
        return math.log1p(max(0.0, held))
    from xylarium.kernel import syntropy
    worlds = syntropy._peoples(kernel).get(holder)
    if not worlds:
        return None
    return syntropy.index(kernel, holder, worlds)["S"]


def season(kernel: Any) -> List[str]:
    """Once a year every mind sets what it did against how it fared."""
    from xylarium.kernel import laws
    if (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    keep = 1.0 - laws.KNOWLEDGE_DEPRECIATION
    for holder in list(st["of"]):
        rec = st["of"][holder]
        now = outcome(kernel, holder)
        if now is None:
            st["of"].pop(holder)                              # a mind that is no more learns nothing
            continue
        if rec["s0"] is not None and rec["score_at"] is not None:
            years = max(1e-3, (kernel.cycle_count - rec["score_at"]) / 100.0)
            d = (now - rec["s0"]) / years
            n = rec["n"] * keep + 1.0                         # its own baseline: how it usually fares
            delta = d - rec["mean"]
            rec["mean"] += delta / n
            rec["var"] = (rec["var"] * (n - 1.0) + delta * (d - rec["mean"])) / n
            for name in rec["pending"]:
                o = rec["opts"].setdefault(name, {"adv": 0.0, "n": 0.0})
                w = o["n"] * keep + 1.0
                o["adv"] = (o["adv"] * o["n"] * keep + (d - rec["mean"])) / w
                o["n"] = w
            rec["n"] = n
            st["lessons"] += len(rec["pending"])
        rec["pending"], rec["s0"], rec["score_at"] = [], now, kernel.cycle_count
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"minds": len(st["of"]), "lessons": st["lessons"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="learning", state=lambda: {"of": {}, "lessons": 0}, season=season,
                             summary=summary))
