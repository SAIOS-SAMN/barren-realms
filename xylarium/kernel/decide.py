"""
Xylarium decide: one rule for every agent that chooses - councils, captains, firms.

An option is anything an agent could do now, priced in the same field everyone sees: what it costs today and what
it is worth over time, both in SOL. The agent takes the option whose worth most exceeds its cost - no thresholds,
no scripted priorities - and sees the future through its own mind (laws.cognition):

    worth   a flow per quarter, discounted at the agent's money's policy rate (the price of waiting) over the
            agent's planning horizon, which shrinks as its thermal noise grows (a hot mind's forecasts blur sooner)
    noise   its judgement errs in proportion to its thermal noise: a cold, deep people chooses the same way twice;
            a plasmic one sometimes doesn't

Nothing is chosen at a loss; doing nothing is always an option worth zero.
"""

import random
import zlib
from typing import Any, Callable, Dict, List, Optional

from xylarium.kernel import laws

BASE_HORIZON_QUARTERS = 40      # a mind at Earth's temperature plans a decade ahead
JUDGEMENT_ERROR = 0.1           # at noise 1, an agent misjudges an option's net worth by about a tenth of the best


def _rng(*parts: Any) -> random.Random:
    return random.Random(zlib.crc32(":".join(str(p) for p in parts).encode()))


def mind(kernel: Any, metabolism: Optional[str]) -> Dict[str, float]:
    return laws.cognition(metabolism or "biotic")


def _steadied(kernel: Any, m: Dict[str, float], holder: Optional[str]) -> Dict[str, float]:
    """A people's fluid intelligence (intellect.py) steadies its judgement: noise falls - and the planning horizon
    lengthens - by its share of the ladders climbed."""
    from xylarium.kernel import intellect
    phi = intellect.fluid(kernel, holder)
    if phi <= 0:
        return m
    return dict(m, noise=m["noise"] / (1.0 + phi), fluid=phi)


def mind_of_planet(kernel: Any, planet: Any) -> Dict[str, float]:
    from xylarium.kernel import biosphere, knowledge
    return _steadied(kernel, mind(kernel, biosphere.metabolism_of(kernel, planet)), knowledge.holder_of_planet(planet))


def mind_of_captain(kernel: Any, captain: Any) -> Dict[str, float]:
    return _steadied(kernel, mind(kernel, getattr(captain, "metabolism", None)), f"captain:{captain.id}")


def rate(kernel: Any, currency: str) -> float:
    """The price of waiting a quarter in this money: its central bank's policy rate."""
    bank = getattr(getattr(kernel, "banking", None), "banks", {}).get(currency)
    return float(getattr(bank, "policy_rate", 0.0) or 0.0) if bank is not None else 0.01


def worth(kernel: Any, flow_per_quarter: float, m: Dict[str, float], currency: str = "SOL") -> float:
    """A flow's present worth to this mind: discounted at its money's rate over its planning horizon."""
    return laws.present_value(flow_per_quarter, laws.horizon(m["noise"], BASE_HORIZON_QUARTERS), rate(kernel, currency))


def option(name: str, cost: float, value: float, act: Optional[Callable[[], Any]] = None, **data: Any) -> Dict[str, Any]:
    return {"name": name, "cost": float(cost), "value": float(value), "act": act, **data}


def choose(kernel: Any, options: List[Dict[str, Any]], m: Dict[str, float], *salt: Any) -> Optional[Dict[str, Any]]:
    """The option worth most over its cost, as this mind judges it; None if nothing is worth doing."""
    if not options:
        return None
    nets = [o["value"] - o["cost"] for o in options]
    scale = max(abs(n) for n in nets) or 1.0
    rng = _rng("decide", kernel.cycle_count, *salt)
    best, best_seen = None, 0.0
    for o, n in zip(options, nets):
        seen = n + rng.gauss(0.0, JUDGEMENT_ERROR * m["noise"] * scale)
        if seen > best_seen:
            best, best_seen = o, seen
    if best is not None:
        st = stats(kernel)
        st["chosen"][best["name"]] = st["chosen"].get(best["name"], 0) + 1
    return best


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "decide")


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="decide", state=lambda: {"chosen": {}},
                             summary=lambda k: {"chosen": dict(stats(k)["chosen"])}))
