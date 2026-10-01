"""
Xylarium liquidation: how a company ends, and what its ending sets in motion.

A company that cannot go on (enterprise.py decides when: four losing quarters) is wound up in order. Every step is
a transfer between holders that already exist - nothing is minted, nothing vanishes:

  1. THE ESTATE   What it holds: its cash in its home money, the SOL it raised on the exchange, and whatever its
                  plant fetched at auction (enterprise.py sells it to a rival first). Its open orders were voided
                  and their escrow came home before this.
  2. THE PRICE    The estate's worth per share, in SOL: what every claim on the company is settled at.
  3. RECEIVABLES  The margin desk's loans against its own shares are called. The collateral is seized first (the
                  borrower's shares in it, at the liquidation price), then the borrower's cash; what is still owed
                  is a default - filed at law, written off, the borrower's name ruined.
  4. DERIVATIVES  Open shorts are closed at the liquidation price: the short seller buys back what was borrowed
                  (into the estate) and the margin desk releases the collateral. A short against a failing firm is
                  where its fall pays someone. A seller who cannot cover defaults like a borrower.
  5. THE WATERFALL What is left goes to the shareholders pro rata - captains' wallets, the founding people's
                  share to its world's vault - in both monies; the unsold float's part returns to the home world and
                  the SOL residue escheats to the Reserve.

Each liquidation is recorded with what it recovered, who defaulted and what the shorts made: the knock-on of one
failure, readable by every other mind deciding whether to lend, short or found.
"""

from typing import Any, Dict, List, Optional, Tuple


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "liquidation")


def _sol(kernel: Any, cur: str, amount: float) -> float:
    return kernel.fx_market.to_sol_value(cur, amount) if cur != "SOL" else float(amount)


def _world(kernel: Any, comp: Any):
    return kernel.get_planet(comp.planet_id) if getattr(comp, "planet_id", None) else None


def price(kernel: Any, comp: Any) -> float:
    """The estate's worth per share in SOL: its SOL and its home cash, over the shares outstanding."""
    worth = max(0, comp.treasury) + _sol(kernel, comp.home_currency, max(0, comp.home_cash))
    return worth / max(1, comp.total_shares)


def _default(kernel: Any, cap: Any, ticker: str, owed: int, what: str) -> None:
    from xylarium.kernel import law
    st = stats(kernel)
    st["defaults"] += 1
    st["written_off_sol"] += owed
    cap.credit_rating = max(300, getattr(cap, "credit_rating", 500) - 150)
    law.file(kernel, "default", cap, kernel.sectors.get(cap.sector_id), owed, {"kind": "company", "id": ticker})
    chron = getattr(kernel, "chronicle", None)
    if chron is not None:
        chron.record(kernel, "RUIN", cap.id, cap.name, f"The Ruin of {cap.name}",
                     f"When {ticker} was wound up its receivers called in {what}; {cap.name} could not pay "
                     f"{owed:,} Cr of it.", tags=["ruin", "liquidation"],
                     alignment=getattr(cap, "cosmic_alignment", None))


def _call_loans(kernel: Any, comp: Any, p: float, rec: Dict[str, Any]) -> None:
    """Receivables: margin loans against the company's shares, called - collateral, then cash, then default."""
    ticker = comp.ticker
    for cap in kernel.captains.values():
        owed = (getattr(cap, "margin_loans", {}) or {}).pop(ticker, 0)
        if owed <= 0:
            continue
        held = cap.portfolio.get(ticker, 0)
        seize = min(held, int(owed // p) + 1) if p > 0 else 0
        if seize > 0:                         # the collateral is taken at what it is worth
            cap.portfolio[ticker] = held - seize
            rec["seized_shares"] = rec.get("seized_shares", 0) + seize
            owed -= min(owed, int(seize * p))
        cash = min(max(0, cap.credits), owed)
        cap.credits -= cash
        comp.treasury += cash
        rec["loans_recovered_sol"] = rec.get("loans_recovered_sol", 0) + cash
        owed -= cash
        if owed > 0:
            rec["defaulted_sol"] = rec.get("defaulted_sol", 0) + owed
            _default(kernel, cap, ticker, owed, "its margin loans")


def _close_shorts(kernel: Any, comp: Any, p: float, rec: Dict[str, Any]) -> None:
    """Derivatives: every open short bought back at the liquidation price; the margin desk releases the collateral."""
    ticker = comp.ticker
    fed = getattr(kernel, "federal_reserve", None)
    for cap in kernel.captains.values():
        pos = (getattr(cap, "short_positions", {}) or {}).pop(ticker, None)
        if not pos:
            continue
        collateral = min(int(pos.get("collateral", 0)), fed.treasury if fed is not None else 0)
        if fed is not None and collateral > 0:
            fed.treasury -= collateral
            fed.stats["margin_released"] = fed.stats.get("margin_released", 0) + collateral
            cap.credits += collateral
        cost = int(pos["shares"] * p)
        paid = min(max(0, cap.credits), cost)
        cap.credits -= paid
        comp.treasury += paid
        pnl = int(pos["shares"] * (pos.get("entry_price", 0) - p))
        rec["shorts_closed"] = rec.get("shorts_closed", 0) + 1
        rec["short_pnl_sol"] = rec.get("short_pnl_sol", 0) + pnl
        stats(kernel)["short_pnl_sol"] += pnl
        if cost - paid > 0:
            rec["defaulted_sol"] = rec.get("defaulted_sol", 0) + cost - paid
            _default(kernel, cap, ticker, cost - paid, "the shares it had sold short")


def _claims(kernel: Any, comp: Any, founder: Optional[Tuple[Any, int]]) -> List[Tuple[str, Any, int]]:
    out = [("captain", cap, n) for cap in kernel.captains.values()
           if (n := (getattr(cap, "portfolio", {}) or {}).get(comp.ticker, 0)) > 0]
    if founder is not None and founder[1] > 0:
        out.append(("world", founder[0], founder[1]))
    return out


def _distribute(kernel: Any, comp: Any, founder: Optional[Tuple[Any, int]], rec: Dict[str, Any]) -> None:
    """The waterfall: what is left, pro rata to every share outstanding, in both monies."""
    from xylarium.kernel import fx
    total = max(1, comp.total_shares)
    home, sol = max(0, comp.home_cash), max(0, comp.treasury)
    paid_home = paid_sol = 0
    for kind, who, n in _claims(kernel, comp, founder):
        h, s = home * n // total, sol * n // total
        if kind == "world":
            # a people's share comes home to its vault, in its own money
            who.treasury += h + (kernel.fx_market.swap_sol_to(who.currency, s) if (s > 0 and who.currency != "SOL")
                                 else s)
        else:
            if h > 0:
                if comp.home_currency == "SOL":
                    who.credits += h
                else:
                    fx.credit(who, comp.home_currency, h)
            who.credits += s
        paid_home += h
        paid_sol += s
    comp.home_cash -= paid_home
    comp.treasury -= paid_sol
    rec["paid_out_sol"] = round(_sol(kernel, comp.home_currency, paid_home) + paid_sol, 1)
    world = _world(kernel, comp)
    if comp.home_cash > 0 and world is not None and world.currency == comp.home_currency:
        world.treasury += comp.home_cash          # the unsold float's and seized shares' part: home
        comp.home_cash = 0
    if comp.home_cash > 0:                        # no home of that money left: through the exchange to the Reserve
        comp.treasury += kernel.fx_market.swap_to_sol(comp.home_currency, comp.home_cash) \
            if comp.home_currency != "SOL" else comp.home_cash
        comp.home_cash = 0
    if comp.treasury > 0:
        kernel.federal_reserve.receive(comp.treasury, "escheat")
        comp.treasury = 0


def liquidate(kernel: Any, ticker: str, cause: str, founder: Optional[Tuple[Any, int]] = None,
              auction: str = "") -> Dict[str, Any]:
    """Wind a company up: price the estate, call its loans, close the shorts on it, pay out, delist."""
    mm = kernel.market_manager
    comp = mm.companies[ticker]
    rec: Dict[str, Any] = {"cycle": kernel.cycle_count, "ticker": ticker, "name": comp.name, "cause": cause,
                           "auction": auction}
    p = price(kernel, comp)
    rec["price_sol"] = round(p, 4)
    rec["estate_sol"] = round(p * max(1, comp.total_shares), 1)
    _call_loans(kernel, comp, p, rec)
    _close_shorts(kernel, comp, p, rec)
    _distribute(kernel, comp, founder, rec)
    for cap in kernel.captains.values():
        (getattr(cap, "portfolio", {}) or {}).pop(ticker, None)
    for ex in getattr(mm, "executives", {}).values():
        if getattr(ex, "company_ticker", None) == ticker:
            ex.active = False
    del mm.companies[ticker]
    st = stats(kernel)
    st["liquidations"] += 1
    st["recent"] = (st["recent"] + [rec])[-12:]
    world = _world(kernel, comp)
    if getattr(kernel, "event_bus", None):
        kernel.event_bus.broadcast_radio(
            sender="ISSE-RECEIVER",
            text=f"LIQUIDATION: {comp.name} ({ticker}) wound up - {rec['paid_out_sol']:,.0f} SOL to its holders"
                 + (f", {rec['shorts_closed']} shorts closed" if rec.get("shorts_closed") else "")
                 + (f", {rec['defaulted_sol']:,} SOL in defaults" if rec.get("defaulted_sol") else "") + ".",
            channel="COMM-1", sector_id=world.sector_id if world is not None else 1)
    return rec


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"liquidations": st["liquidations"], "defaults": st["defaults"],
            "written_off_sol": st["written_off_sol"], "short_pnl_sol": st["short_pnl_sol"],
            "recent": [{k: r.get(k) for k in ("ticker", "cause", "price_sol", "paid_out_sol", "shorts_closed",
                                               "defaulted_sol")} for r in st["recent"][-3:]]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="liquidation",
    state=lambda: {"liquidations": 0, "defaults": 0, "written_off_sol": 0, "short_pnl_sol": 0, "recent": []},
    summary=summary,
))
