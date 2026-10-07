"""
Xylarium prices: every money's price level, and what holding it idle costs.

MV = PY. A money's price level moves with how far its supply has run ahead of what its economy produces: the
monetary authority's measured M / M* (ledger.MonetaryPolicy). For SOL - the numeraire, with no exchange rate to
read - that is the whole of it; for the regional monies the exchange rate already carries their supply relative to
SOL, so their level follows its drift from genesis, as before. Either way only part of the pressure reaches shop
prices (FX_PRICE_PASS_THROUGH), and prices are sticky: each quarter they close a quarter of the gap to that target
(in log), so a sudden excess is felt over seasons, not overnight.

Inflation is the measured change in that level. It is the carrying cost of idle money: a holder's cash buys less
each quarter by it, less whatever its deposits are paid (banking.paid_rate). Every choice that puts cash to work
avoids that cost (decide.choose reads carry()): under inflation hoarding loses to anything that pays; under
deflation waiting is rational. Nobody sets a rate of inflation - it is read.
"""

import math
from typing import Any, Dict

from xylarium.config import FX_PRICE_PASS_THROUGH, PRICE_LEVEL
from xylarium.kernel.fx import hub as _hub

STICKY = 0.25                 # the share of the gap to the target level closed each quarter (in log)


def _st(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "prices")


def _kernel(kernel: Any = None) -> Any:
    if kernel is not None:
        return kernel
    from xylarium.kernel import ledger
    return ledger.active_kernel()


def target(kernel: Any, cur: str) -> float:
    base = PRICE_LEVEL.get(cur, 1.0)
    if cur == _hub():
        pol = getattr(kernel, "monetary_policy", None)
        mstar = (getattr(pol, "current", {}) or {}).get(_hub())
        if not mstar:
            return base
        from xylarium.kernel.ledger import money_supply
        m = money_supply(kernel).get(_hub(), {}).get("total", 0)
        return base * max(1e-6, m / mstar) ** FX_PRICE_PASS_THROUGH
    fxm = getattr(kernel, "fx_market", None)
    if fxm is None or cur not in getattr(fxm, "pools", {}):
        return base
    return base * fxm.price_level_drift(cur) ** FX_PRICE_PASS_THROUGH


def level(cur: str, kernel: Any = None) -> float:
    """What goods cost in this money now (genesis level x its measured inflation since)."""
    k = _kernel(kernel)
    if k is None or "prices" not in getattr(k, "state", {}):
        if k is not None and cur != _hub():
            return target(k, cur)
        return PRICE_LEVEL.get(cur, 1.0)
    lv = _st(k)["level"].get(cur)
    if lv is not None:
        return lv
    return PRICE_LEVEL.get(cur, 1.0) if cur == _hub() else target(k, cur)


def inflation(kernel: Any, cur: str) -> float:
    """Measured inflation a quarter (log change of the price level, averaged over the last year)."""
    hist = _st(kernel)["hist"].get(cur) or []
    if len(hist) < 2:
        return 0.0
    return (math.log(hist[-1]) - math.log(hist[0])) / (len(hist) - 1)


def carry(kernel: Any, cur: str) -> float:
    """What idle money in `cur` loses a quarter: inflation less what its deposits are paid."""
    if kernel is None or "prices" not in getattr(kernel, "state", {}):
        return 0.0
    paid = 0.0
    banking = getattr(kernel, "banking", None)
    if banking is not None and hasattr(banking, "paid_rate"):
        paid = banking.paid_rate(cur)
    return inflation(kernel, cur) - paid


def quarter(kernel: Any) -> list:
    st = _st(kernel)
    curs = {_hub(), *getattr(kernel.fx_market, "pools", {}).keys()}
    for cur in curs:
        tgt = target(kernel, cur)
        # a money with no reading yet starts where its prices stood: SOL at its genesis level, the regional monies
        # at their exchange pass-through (what they were already charged at)
        old = st["level"].get(cur, PRICE_LEVEL.get(cur, 1.0) if cur == _hub() else tgt)
        new = math.exp(math.log(old) + STICKY * (math.log(tgt) - math.log(old)))
        st["level"][cur] = round(new, 6)
        h = st["hist"].setdefault(cur, [])
        h.append(new)
        del h[:-5]
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = _st(kernel)
    return {"level": {c: round(v, 3) for c, v in st["level"].items()},
            "inflation_q": {c: round(inflation(kernel, c), 4) for c in st["level"]}}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="prices", state=lambda: {"level": {}, "hist": {}}, season=quarter,
                             summary=summary))
