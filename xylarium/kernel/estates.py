"""
Xylarium estates: the deep era's money. A people lived by the annals (its world folded, never stepped) still works
and still has its few - and what they take is real goods, coined at par.

  THE TAKE     each stretch the annals live, a people under rule yields its output (its numbers x its output a head,
               the same measure the live era taxes: demography._tax_per_head_quarter) and its few take their share
               of it (rent.choose: the same law its history is judged by).
  IN GOODS     the take is in its people's reserve BASKET (backing.basket: what one of them needs to live a year at
               home - food, bodies, walls - by mass), each good in its share of the basket's worth at the money's
               own ports - drawn from the world's own ground, then its stores (transfers, never made from nothing),
               so a world's estate is bounded by what it holds. Where its ports price none of the basket, the money's
               single commodity (regimes: its currency board's backing at par) as before.
  AT PAR       the board buys that commodity at its bid and issues the money for it into the world's treasury
               (ledger.mint): money only ever against real goods, the closed loop the live era keeps.

An ancient house is such an estate: its people's, at the core, the first to fill (board.ancient_peoples). What it
holds is what its lines can spend - on its stewards, its operatives, its trade (progenitor operatives; steward
trade).
"""

from fractions import Fraction
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
    got = _accrue_basket(kernel, who, home, cur, b, rho, years)
    if got is not None:
        return got
    bid = Fraction(b["par"]) * (1 - Fraction(str(FX_FEE)))       # exact at the seam: the bid a mint pays on
    if bid <= 0:
        return 0
    want = Fraction(rho * output_a_year(kernel, home) * years) / bid  # the take, in units of the commodity
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


def _draw(home: Any, good: str, n: int) -> int:
    """Up to n of a good from the world's own ground, then its stores - a transfer (it goes to the board's
    warehouse, which the census counts): nothing declared."""
    got = 0
    have = int(home.element_deposits.get(good, 0))
    take = min(have, n)
    if take > 0:
        home.element_deposits[good] = have - take
        got += take
    stores = (("ore_silo",) if good == "ORE" else ("organics_silo",) if good == "ORGANICS" else ())
    for attr in stores:
        if got >= n:
            break
        have = int(getattr(home, attr, 0) or 0)
        take = min(have, n - got)
        if take > 0:
            setattr(home, attr, have - take)
            got += take
    if got < n:
        have = int((home.element_reserves or {}).get(good, 0))
        take = min(have, n - got)
        if take > 0:
            home.element_reserves[good] = have - take
            got += take
    return got


def _accrue_basket(kernel: Any, who: str, home: Any, cur: str, board: Dict[str, Any], rho: float,
                   years: float) -> Optional[int]:
    """The take drawn as the people's reserve basket; None where its ports price none of it."""
    from xylarium.kernel import backing, ledger
    from xylarium.kernel.economy import EconomyManager
    from xylarium.kernel.regimes import FX_FEE
    bk = backing.basket(kernel, who)
    if not bk:
        return None
    prices: Dict[str, float] = {}
    for good in bk["units"]:
        ps = [EconomyManager.get_unit_prices(sec.port, good)[1] for sec in kernel.sectors.values()
              if sec.port is not None and sec.port.currency == cur and sec.port.sells.get(good)]
        ps = [p for p in ps if p > 0]
        if ps:
            prices[good] = Fraction(sum(Fraction(x) for x in ps), len(ps))
    worth = {g: Fraction(bk["units"][g]) * p for g, p in prices.items()}
    whole = sum(worth.values())
    if whole <= 0:
        return None
    want = Fraction(rho * output_a_year(kernel, home) * years)  # the take, in its money
    bank = board["bank"]
    pay = 0
    drawn: Dict[str, int] = {}
    for good in sorted(worth):
        bid = prices[good] * (1 - Fraction(str(FX_FEE)))
        units = _draw(home, good, int(want * worth[good] / whole / bid))
        if units <= 0:
            continue
        bank.warehouse[good] = bank.warehouse.get(good, 0) + units
        drawn[good] = units
        pay += int(units * bid)
    if pay <= 0:
        return 0
    home.treasury += pay
    ledger.mint("estate_issue", pay, cur)
    rec = stats(kernel)["of"].setdefault(who, {"issued": 0, "units": 0, "currency": cur, "commodity": "basket"})
    rec["issued"] += pay
    rec["units"] += sum(drawn.values())
    rec["basket"] = {g: int(rec.get("basket", {}).get(g, 0)) + n for g, n in drawn.items()}
    return pay


def summary(kernel: Any) -> Dict[str, Any]:
    of = stats(kernel)["of"]
    return {"estates": len(of), "issued": {w: r["issued"] for w, r in sorted(of.items())}}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="estates", state=lambda: {"of": {}}, summary=summary))
