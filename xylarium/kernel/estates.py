"""
Xylarium estates: the deep era's money. A people lived by the annals (its world folded, never stepped) still works
and still has its few - and what they take is real goods, coined at par.

  THE TAKE     each stretch the annals live, a people under rule yields its output (its numbers x its output a head,
               the same measure the live era taxes: demography._tax_per_head_quarter) and its few take their share
               of it (rent.choose: the same law its history is judged by).
  IN GOODS     the take is in the money's own commodity (regimes: its currency board's backing at par) - mined out
               of the world's own crust (a transfer from its deposits, never made from nothing), so a world's estate
               is bounded by what its ground holds and its heat renews (geology, which runs folded).
  AT PAR       the board buys that commodity at its bid and issues the money for it into the world's treasury
               (ledger.mint): money only ever against real goods, the closed loop the live era keeps.

An ancient house is such an estate: its people's, at the core, the first to fill (board.ancient_peoples). What it
holds is what its lines can spend - on its stewards, its operatives, its trade (progenitor operatives; steward
trade).
"""

from typing import Any, Dict, Optional
from xylarium.kernel.fx import hub as _hub


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "estates")


def _board(kernel: Any, cur: str) -> Optional[Dict[str, Any]]:
    """Its money's currency board, if it keeps one: (commodity, par) and the bank holding the backing."""
    from xylarium.kernel import regimes
    banks = getattr(getattr(kernel, "banking", None), "banks", {}) or {}
    if cur not in banks:
        return None
    rec = regimes.stats(kernel)["by_currency"].get(cur) or {}
    if rec.get("regime") != "reserve" or not rec.get("commodity") or float(rec.get("par") or 0.0) <= 0:
        return None
    return {"commodity": rec["commodity"], "par": float(rec["par"]), "bank": banks[cur]}


def output_a_year(kernel: Any, home: Any) -> float:
    """A world's output a year, in its own money: its numbers x its output a head (the measure the live era taxes)."""
    from xylarium.kernel import demography
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    quarters = 100.0 / FISCAL_QUARTER_CYCLES
    return float(home.population) * demography._tax_per_head_quarter(home) * quarters


def accrue(kernel: Any, who: str, home: Any, rho: float, years: float) -> int:
    """A stretch of rule lived in the annals: its few's take (rho of its output over `years`) mined from the world's
    crust in its money's commodity, sold to its board at the bid, the money issued into its treasury. Returns the
    money issued (0 where it keeps no board of its own, takes nothing, or its ground holds none)."""
    from xylarium.kernel import ledger
    from xylarium.kernel.regimes import FX_FEE
    if rho <= 0 or years <= 0 or home is None or home.population <= 0:
        return 0
    cur = getattr(home, "currency", _hub())
    b = _board(kernel, cur)
    if b is None:
        return 0
    bid = b["par"] * (1.0 - FX_FEE)
    want = rho * output_a_year(kernel, home) * years / max(1e-9, bid)     # the take, in units of the commodity
    comm = b["commodity"]
    have = int(home.element_deposits.get(comm, 0))
    units = int(min(have, want))
    if units <= 0:
        return 0
    home.element_deposits[comm] = have - units                 # out of its own ground (a transfer: geology.py)
    bank = b["bank"]
    bank.warehouse[comm] = bank.warehouse.get(comm, 0) + units
    pay = int(units * bid)
    home.treasury += pay
    ledger.mint("estate_issue", pay, cur)
    rec = stats(kernel)["of"].setdefault(who, {"issued": 0, "units": 0, "currency": cur, "commodity": comm})
    rec["issued"] += pay
    rec["units"] += units
    return pay


def summary(kernel: Any) -> Dict[str, Any]:
    of = stats(kernel)["of"]
    return {"estates": len(of), "issued": {w: r["issued"] for w, r in sorted(of.items())}}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="estates", state=lambda: {"of": {}}, summary=summary))
