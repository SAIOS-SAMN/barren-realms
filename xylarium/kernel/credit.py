"""
Xylarium credit: leverage, margin calls and ruin - where temperament becomes fortune.

  * Appetite. A captain's temperament (cognition.temperament) sets how much it will borrow: leverage =
    risk / caution - 1, between 0 and 2 (a cautious mind borrows nothing; a reckless one borrows twice its
    stake). No threshold picks the gamblers - the traits do.
  * The margin desk. A company's idle cash is lent to captains buying its own shares (the broker's margin
    account): the loan is a transfer from the company treasury to the captain, and the shares bought are its
    collateral. Idle corporate hoards go to work; nothing is minted.
  * Interest. Each fiscal quarter the borrower pays the Sol central bank's policy rate to the lending company
    (a transfer); what it cannot pay is added to the debt.
  * Margin calls. When the collateral's value falls below 125% of the debt, shares are sold back to the
    company until it is covered again (the sale proceeds repay the loan). When nothing is left, the rest is a
    default: the company writes the claim off, the borrower's credit is ruined, and the Library remembers.
  * Retained earnings. A company holding cash beyond a year of its own outflows (operating spend + dividends
    + lending) pays a quarter of the excess each season to its home world's treasury - a levy that returns
    hoards to the regional budgets the monetary authorities can reach.
"""

from typing import Any, Dict, List, Optional

MAINTENANCE = 1.25          # collateral must stay worth 125% of the loan (the desk's own safety margin)


def appetite(kernel: Any, captain: Any) -> float:
    from xylarium.kernel.cognition import temperament
    t = temperament(captain, kernel)
    return max(0.0, min(2.0, t.get("risk", 1.0) / max(0.2, t.get("caution", 1.0)) - 1.0))


def debt(captain: Any) -> int:
    return sum(getattr(captain, "margin_loans", {}).values())


def lend(kernel: Any, captain: Any, ticker: str, stake: int) -> int:
    """Before a share purchase: the company's margin desk lends ``appetite x stake`` against the shares."""
    comp = kernel.market_manager.companies.get(ticker)
    lev = appetite(kernel, captain)
    from xylarium.kernel import liquidation
    if comp is None or lev <= 0 or stake <= 0 or getattr(captain, "credit_rating", 500) < 450 \
            or liquidation.distressed(kernel, ticker):
        return 0                                  # the desk does not lend against a company in distress
    from xylarium.config import COMPANY_OPEX_RESERVE
    idle = comp.treasury - max(_buffer(comp), COMPANY_OPEX_RESERVE)
    amount = int(min(stake * lev, max(0, idle)))
    if amount <= 0:
        return 0
    comp.treasury -= amount
    captain.credits += amount
    captain.margin_loans[ticker] = captain.margin_loans.get(ticker, 0) + amount
    _stats(kernel)["lent"] += amount
    return amount


def _buffer(comp: Any) -> int:
    """A year of the company's own outflows (operating spend and dividends): what it keeps as liquidity."""
    return int(4 * (getattr(comp, "last_outflow_q", 0) or 0))


def _stats(kernel: Any) -> Dict[str, int]:
    return state.of(kernel, "credit")


def quarter(kernel: Any) -> List[str]:
    """Interest, margin calls, defaults; then the retained-earnings levy."""
    logs: List[str] = []
    mm = kernel.market_manager
    st = _stats(kernel)
    rate = 0.01
    banking = getattr(kernel, "banking", None)
    if banking is not None and "SOL" in banking.banks:
        rate = banking.banks["SOL"].policy_rate
    for cap in list(kernel.captains.values()):
        loans = getattr(cap, "margin_loans", None)
        if not loans:
            continue
        for ticker in list(loans):
            comp = mm.companies.get(ticker)
            if comp is None:
                loans.pop(ticker)
                continue
            owed = loans[ticker]
            interest = int(owed * rate)
            paid = min(interest, max(0, cap.credits))
            cap.credits -= paid
            comp.treasury += paid
            loans[ticker] = owed + (interest - paid)
            st["interest"] += paid
            log = _margin_check(kernel, cap, comp)
            if log:
                logs.append(log)
    for comp in mm.companies.values():
        _levy(kernel, comp)
    return logs


def _margin_check(kernel: Any, cap: Any, comp: Any) -> Optional[str]:
    mm = kernel.market_manager
    st = _stats(kernel)
    ticker = comp.ticker
    owed = cap.margin_loans.get(ticker, 0)
    held = cap.portfolio.get(ticker, 0)
    if owed <= 0:
        cap.margin_loans.pop(ticker, None)
        return None
    if held * comp.share_price >= owed * MAINTENANCE:
        return None
    # Margin call: sell shares back to the company until covered (proceeds repay the loan)
    st["margin_calls"] += 1
    need_value = owed * MAINTENANCE - held * comp.share_price
    to_sell = held if comp.share_price <= 0 else min(held, int(need_value / max(1, comp.share_price * (MAINTENANCE - 1))) + 1)
    if to_sell > 0:
        before = cap.credits
        ok, _, _ = mm.sell_shares(cap, ticker, to_sell)
        proceeds = cap.credits - before if ok else 0
        repay = min(proceeds, owed)
        cap.credits -= repay
        comp.treasury += repay
        owed -= repay
    # What the captain's own cash can cover, it covers
    cash = min(max(0, cap.credits), owed if cap.portfolio.get(ticker, 0) == 0 else 0)
    cap.credits -= cash
    comp.treasury += cash
    owed -= cash
    if owed > 0 and cap.portfolio.get(ticker, 0) == 0:
        # Default: the claim is written off (it was never money - only a promise); the name is ruined
        st["defaults"] += 1
        st["written_off"] += owed
        cap.margin_loans.pop(ticker, None)
        cap.credit_rating = max(300, getattr(cap, "credit_rating", 500) - 150)
        st["ruined"] = (st["ruined"] + [cap.id])[-20:]
        chron = getattr(kernel, "chronicle", None)
        if chron is not None:
            chron.record(kernel, "RUIN", cap.id, cap.name, f"The Ruin of {cap.name}",
                         f"{cap.name} borrowed against {ticker} and the market turned. The margin desk sold them out; "
                         f"{owed:,} Cr of debt went unpaid.", tags=["ruin", "speculation"],
                         alignment=getattr(cap, "cosmic_alignment", None))
        from xylarium.kernel import law
        law.file(kernel, "default", cap, kernel.sectors.get(cap.sector_id), owed, {"kind": "company", "id": ticker})
        return f"[CREDIT] {cap.name} defaulted on {owed:,} Cr of {ticker} margin debt."
    cap.margin_loans[ticker] = owed
    if owed <= 0:
        cap.margin_loans.pop(ticker, None)
    return None


def _levy(kernel: Any, comp: Any) -> None:
    """Cash beyond a year of the company's own outflows returns, a quarter a season, to its home world."""
    lent = sum(c.margin_loans.get(comp.ticker, 0) for c in kernel.captains.values())
    excess = comp.treasury - _buffer(comp) - lent
    if excess <= 0 or _buffer(comp) <= 0:
        return
    amount = excess // 4
    home = kernel.get_planet(comp.planet_id) if getattr(comp, "planet_id", None) else None
    if home is None or amount <= 0:
        return
    comp.treasury -= amount
    from xylarium.kernel import fx
    if home.currency != "SOL" and fx.ACTIVE_FX is not None:
        home.treasury += fx.ACTIVE_FX.swap_sol_to(home.currency, amount)
    else:
        home.treasury += amount
    _stats(kernel)["levied"] += amount


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="credit",
    state=lambda: {"lent": 0, "interest": 0, "margin_calls": 0, "defaults": 0, "written_off": 0, "levied": 0,
                   "ruined": []},
    season=quarter,
    summary=lambda kernel: dict(_stats(kernel)),
))
