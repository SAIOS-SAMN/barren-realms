"""
Xylarium monetary regimes: each polity chooses how its money is governed. We are agnostic.

The universe provides laws - conservation, the physics of goods, the exchanges - and the ability to choose. It
does not provide a correct path. Every currency's polity (its central bank and governor) runs one regime:

    central_bank   discretion: a policy rate it sets, interest on deposits, credit to its ports, public works,
                   and the output-tracking authority (ledger.MonetaryPolicy) steering its supply
    algorithmic    a published rule and nothing else: the authority's output rule, a fixed base rate
    reserve        a currency board: its money is a claim on a commodity at par, issued when the bank buys the
                   commodity and retired when it sells it; ports arbitrage against the par each quarter, which
                   pins the commodity's local price and anchors the rate through trade
    free           no issuer steers anything: no rate, no credit, no authority; money is what earnings and
                   spending leave behind

and may close its exchange to its own holders (capital controls) - a choice, like any other.

How a polity chooses: each year its governor weighs staying against each alternative by what holding money under
each regime has actually earned its holders - the log return of the currency's value plus the interest it paid,
less half its variance (expected log growth), pooled across every currency that has run that regime (an untried
regime is expected to do as money typically does) - through its own mind's judgement (decide.py). Nothing labels
a regime good or bad; a polity doing worse than money typically does has a reason to try another way.

What follows from a choice is measured, not assigned (alignment.measure):
    * money grown faster than real output takes purchasing power from those who cannot leave it - households,
      colony vaults, ports, and captains too when controls bar their exit: that loss is harm to the governor
    * help given to a neighbour in trouble is help

When a polity's money fails it - its holders' value falling while it has nothing left to defend with - it may ask
its neighbours for help: governors willing (luminous enough to share, holding SOL to lend) lend it SOL, which it
spends buying its own money back in its pool; the loan is repaid when it recovers. Failure is history, not a bug.
"""

import math
from fractions import Fraction
from typing import Any, Dict, List, Optional

from xylarium.config import COMMODITY_CONFIG, FX_FEE, POLICY_RATE_BASE, RELIEF_LIGHT_THRESHOLD
from xylarium.kernel import decide, laws, ledger
from xylarium.kernel.fx import hub as _hub

REGIMES = ("central_bank", "algorithmic", "reserve", "free")
REVIEW_QUARTERS = 4                 # a governor reviews its regime once a year
HISTORY = 16                        # quarters of returns remembered per currency (four years)


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    st = state.of(kernel, "regimes")
    for cur in kernel.banking.banks:
        st["by_currency"].setdefault(cur, {"regime": "central_bank", "since": 0, "controls": False,
                                           "returns": [], "commodity": None, "par": 0.0})
    return st


def regime(kernel: Any, cur: str) -> str:
    st = state.of(kernel, "regimes")
    return (st["by_currency"].get(cur) or {}).get("regime", "central_bank")


def controlled(kernel: Any, cur: str) -> bool:
    """Capital controls: holders of this money may not convert it out."""
    if kernel is None or not hasattr(kernel, "state"):
        return False
    st = kernel.state.get("regimes")
    return bool(st and (st["by_currency"].get(cur) or {}).get("controls"))


def steers(kernel: Any, cur: str) -> bool:
    """Whether the output-tracking authority steers this money's supply (central bank and algorithmic rule)."""
    return regime(kernel, cur) in ("central_bank", "algorithmic")


def rate(kernel: Any, bank: Any, discretionary: float) -> float:
    r = regime(kernel, bank.currency)
    if r == "central_bank":
        return discretionary
    if r == "algorithmic":
        return POLICY_RATE_BASE
    return 0.0


def lends(kernel: Any, cur: str) -> bool:
    return regime(kernel, cur) in ("central_bank", "algorithmic")


def spends(kernel: Any, cur: str) -> bool:
    return regime(kernel, cur) == "central_bank"


# ---------------------------------------------------------------------- what holding the money earned
def _value_change(kernel: Any, cur: str, st: Dict[str, Any]) -> float:
    """Log change of the money's SOL value this quarter (SOL against the mean of the others)."""
    fxm = kernel.fx_market
    last = st.setdefault("last_rates", {})
    if cur == _hub():
        moves = []
        for c in fxm.pools:
            r0, r1 = last.get(c), fxm.rate(c)
            if r0 and r1 > 0:
                moves.append(math.log(r1 / r0))          # others weakening is SOL strengthening
        return sum(moves) / len(moves) if moves else 0.0
    r0, r1 = last.get(cur), fxm.rate(cur)
    return -math.log(r1 / r0) if (r0 and r1 > 0) else 0.0


def _record_returns(kernel: Any) -> None:
    st = stats(kernel)
    fxm = kernel.fx_market
    pooled = st.setdefault("pooled", {r: [] for r in REGIMES})
    for cur, rec in st["by_currency"].items():
        ret = _value_change(kernel, cur, st) + kernel.banking.paid_rate(cur)
        rec["returns"].append(round(ret, 6))
        del rec["returns"][:-HISTORY]
        pool = pooled.setdefault(rec["regime"], [])
        pool.append(round(ret, 6))
        del pool[:-HISTORY * 4]
    st["last_rates"] = {c: fxm.rate(c) for c in fxm.pools}


def growth(returns: List[float]) -> Optional[float]:
    """Expected log growth of holding: mean - variance / 2 (None with too little to judge by)."""
    if len(returns) < 4:
        return None
    m = sum(returns) / len(returns)
    var = sum((x - m) ** 2 for x in returns) / (len(returns) - 1)
    return m - var / 2.0


def stderr(returns: List[float]) -> float:
    """How uncertain that estimate is: the standard error of the mean."""
    n = len(returns)
    if n < 2:
        return float("inf")
    m = sum(returns) / n
    return math.sqrt(sum((x - m) ** 2 for x in returns) / (n - 1) / n)


# ---------------------------------------------------------------------- choosing
def review(kernel: Any) -> List[str]:
    """Each governor's yearly choice of regime - and of controls - by its own mind."""
    st = stats(kernel)
    logs = []
    if (kernel.cycle_count // _quarter()) % REVIEW_QUARTERS:
        return logs
    for cur, rec in st["by_currency"].items():
        bank = kernel.banking.banks[cur]
        if cur != _hub() and cur not in kernel.fx_market.pools:
            continue                              # a money with no market cannot be judged by its holders' returns
        m = decide.mind(kernel, "biotic")
        own = growth(rec["returns"])
        if own is None or len(rec["returns"]) < 4:
            continue                              # a year of returns before a governor judges its own
        options = []
        everything = [x for pool in st["pooled"].values() for x in pool]
        for r in REGIMES:
            if r == rec["regime"]:
                continue
            evidence = st["pooled"].get(r, [])
            if growth(evidence) is None:
                evidence = everything          # untried: expected to do as money typically does
            seen = growth(evidence)
            if seen is None or len(evidence) < 4:
                continue                       # no year of evidence for the alternative: nothing to move on
            # a rational governor moves only on evidence: the gain must clear the comparison's standard error
            doubt = math.sqrt(stderr(rec["returns"]) ** 2 + stderr(evidence) ** 2)
            options.append(decide.option(f"regime:{r}", decide.worth(kernel, doubt, m),
                                         decide.worth(kernel, seen - own, m), regime=r))
        pick = decide.choose(kernel, options, m, cur, "regime")
        if pick is not None:
            logs.append(adopt(kernel, cur, pick["regime"]))
        # Controls are a governor's character as much as its arithmetic: a governor who weighs its holders'
        # freedom (alignment >= 0) never bars the door; one who doesn't closes it while its money bleeds
        fleeing = kernel.fx_market.advantage(kernel, cur) < 0 if cur != _hub() else False
        want = bank.alignment < 0 and fleeing
        if want != rec["controls"]:
            rec["controls"] = want
            logs.append(f"[MONEY] {bank.name} {'imposes' if want else 'lifts'} capital controls on {cur}.")
    return logs


def adopt(kernel: Any, cur: str, new: str) -> str:
    st = stats(kernel)
    rec = st["by_currency"][cur]
    old = rec["regime"]
    rec["regime"], rec["since"] = new, kernel.cycle_count
    rec["returns"] = []                                   # a regime is judged on its own record
    bank = kernel.banking.banks[cur]
    if new == "reserve":
        rec["commodity"], rec["par"] = _money_commodity(kernel, cur)
    if new in ("reserve", "free") and kernel.monetary_policy is not None:
        st.setdefault("frozen_factor", {})[cur] = kernel.monetary_policy.factor(cur)
    chron = getattr(kernel, "chronicle", None)
    if chron is not None:
        chron.record(kernel, "MONETARY_REGIME", cur, bank.name, f"The {bank.name} turns to {new.replace('_', ' ')}",
                     f"Its money had served its holders poorly under {old.replace('_', ' ')}. The governor chose "
                     f"{new.replace('_', ' ')}" + (f", backing each unit with {rec['commodity']} at par "
                                                   f"{rec['par']:.2f}." if new == "reserve" else "."),
                     tags=["money", "regime"], alignment=bank.alignment, author=bank.name)
    st["switches"] += 1
    return f"[MONEY] {bank.name} ({cur}) changes regime: {old} -> {new}."


def _money_commodity(kernel: Any, cur: str):
    """The commodity its ports hold the most of by value becomes the money's backing, at today's price."""
    from xylarium.kernel.economy import EconomyManager
    worth: Dict[str, float] = {}
    prices: Dict[str, List[int]] = {}
    for sec in kernel.sectors.values():
        port = sec.port
        if port is None or port.currency != cur:
            continue
        for comm, n in list(port.stock.items()):           # pricing a good may shelve a key for it
            if n <= 0 or COMMODITY_CONFIG.get(comm, {}).get("category") in ("WASTE", "LUXURY"):
                continue
            _, sell = EconomyManager.get_unit_prices(port, comm)
            if sell > 0:
                worth[comm] = worth.get(comm, 0.0) + n * sell
                prices.setdefault(comm, []).append(sell)
    if not worth:
        return "ORE", float(COMMODITY_CONFIG["ORE"]["base_price"])
    comm = max(worth, key=worth.get)
    ps = sorted(prices[comm])
    return comm, float(ps[len(ps) // 2])


# ---------------------------------------------------------------------- a currency board's arbitrage
def _board(kernel: Any, cur: str, rec: Dict[str, Any]) -> None:
    """The bank buys its commodity at par less the fee and sells it at par plus the fee; every port of its money
    arbitrages against that until the gap closes or someone runs short. Money is issued and retired only here."""
    from xylarium.kernel.economy import EconomyManager
    bank = kernel.banking.banks[cur]
    comm, par = rec["commodity"], rec["par"]
    if not comm or par <= 0:
        return
    bid, ask = par * (1 - FX_FEE), par * (1 + FX_FEE)
    st = stats(kernel)
    for sec in kernel.sectors.values():
        port = sec.port
        if port is None or port.currency != cur:
            continue
        for _ in range(20):                                # in lots, re-pricing as the stock moves
            port_buy, port_sell = EconomyManager.get_unit_prices(port, comm)
            lot = 10
            if port_buy and port_buy < bid and port.stock.get(comm, 0) >= lot:
                # the port sells its stock to the bank: new money issued against the commodity
                pay = int(bid * lot)
                port.stock[comm] -= lot
                bank.warehouse[comm] = bank.warehouse.get(comm, 0) + lot
                port.treasury += pay
                ledger.mint("reserve_issue", pay, cur)
                st["issued"][cur] = st["issued"].get(cur, 0) + pay
            elif port_sell and port_sell > ask and bank.warehouse.get(comm, 0) >= lot \
                    and port.treasury >= int(ask * lot):
                # the port buys from the bank: money retired against the commodity
                pay = int(ask * lot)
                bank.warehouse[comm] -= lot
                port.stock[comm] = port.stock.get(comm, 0) + lot
                port.treasury -= pay
                ledger.burn("reserve_redeem", pay, cur)
                st["retired"][cur] = st["retired"].get(cur, 0) + pay
            else:
                break


# ---------------------------------------------------------------------- consequences
def _non_exit_balances(kernel: Any, cur: str, controls: bool) -> float:
    """Money in hands that cannot leave it: households, vaults and ports - and captains' when controls bar them."""
    total = 0.0
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.currency == cur:
                total += max(0, p.treasury) + max(0, getattr(p, "household_purse", 0))
        if sec.port is not None and sec.port.currency == cur:
            total += max(0, sec.port.treasury)
    if controls:
        for c in kernel.captains.values():
            total += max(0, c.credits if cur == _hub() else c.fx_wallet.get(cur, 0))
    return total


def _measure_debasement(kernel: Any) -> None:
    """Money grown beyond what real output needs (M/M* rising) takes purchasing power from those who cannot leave
    it; money brought back toward it (M/M* falling) restores it. Measured both ways, so noise nets out and only a
    sustained debasement - or a sustained restoration - moves a governor."""
    from xylarium.kernel import alignment
    st = stats(kernel)
    supply = ledger.money_supply(kernel)
    prev = st.setdefault("prev_ratio", {})
    pol = kernel.monetary_policy
    for cur, rec in st["by_currency"].items():
        m = float(supply.get(cur, {}).get("total", 0))
        target = float((pol.current or {}).get(cur, 0)) if pol is not None else 0.0
        if m <= 0 or target <= 0:
            continue
        ratio = m / target
        r0, prev[cur] = prev.get(cur), ratio
        if not r0:
            continue
        excess = math.log(ratio / r0)
        held = _non_exit_balances(kernel, cur, rec["controls"])
        if held <= 0:
            continue
        moved = excess * held
        value = kernel.fx_market.to_sol_value(cur, abs(moved)) if cur != _hub() else abs(moved)
        held_sol = kernel.fx_market.to_sol_value(cur, held) if cur != _hub() else held
        shift = (alignment.measure(kernel, harmed_sol=value, relative_to=held_sol) if excess > 0
                 else alignment.measure(kernel, helped_sol=value, relative_to=held_sol))
        bank = kernel.banking.banks[cur]
        bank.alignment = round(max(-1.0, min(1.0, bank.alignment + shift)), 4)
        st["debased_sol"][cur] = str(Fraction(st["debased_sol"].get(cur, 0)) + Fraction(value if excess > 0 else -value))


# ---------------------------------------------------------------------- help between neighbours
def _sol_of(kernel: Any, bank: Any) -> int:
    return kernel.federal_reserve.treasury if bank.currency == _hub() else bank.fx_reserves.get(_hub(), 0)


def _take_sol(kernel: Any, bank: Any, n: int) -> None:
    if bank.currency == _hub():
        kernel.federal_reserve.treasury -= n
    else:
        bank.fx_reserves[_hub()] = bank.fx_reserves.get(_hub(), 0) - n


def _give_sol(kernel: Any, bank: Any, n: int) -> None:
    if bank.currency == _hub():
        kernel.federal_reserve.treasury += n
    else:
        bank.fx_reserves[_hub()] = bank.fx_reserves.get(_hub(), 0) + n


def distressed(kernel: Any, cur: str) -> bool:
    """Its money is failing its holders - early enough that help can still reach a working exchange:
    its slide is real (depreciation beyond what it pays, by more than the rate's own quarterly noise), or its pool
    has thinned to under a quarter of its two-year median depth (trade about to lock up), and it holds no SOL of
    its own to defend with."""
    if cur == _hub():
        return False
    from xylarium.kernel import liquidity
    bank = kernel.banking.banks[cur]
    lq = liquidity.stats(kernel)
    sigma = lq["vol"].get(cur, 0.0)
    sliding = kernel.fx_market.expected_depreciation(kernel, cur) - kernel.banking.paid_rate(cur) > sigma
    depths = lq.setdefault("depth_hist", {}).get(cur, [])
    if cur not in kernel.fx_market.pools:
        return False                                      # it has no market to be distressed in yet
    now = kernel.fx_market.pools[cur]["sol"]
    thinning = len(depths) >= 4 and now < 0.25 * sorted(depths)[len(depths) // 2]
    return (sliding or thinning) and _sol_of(kernel, bank) <= 0


def _help(kernel: Any) -> List[str]:
    from xylarium.kernel import alignment
    st = stats(kernel)
    logs = []
    banks = kernel.banking.banks
    for cur in list(banks):
        if not distressed(kernel, cur):
            continue
        borrower = banks[cur]
        pool = kernel.fx_market.pools.get(cur)
        if pool is None:
            continue
        need = int(pool["sol"] * 0.1)                       # a tenth of its pool's SOL side
        for hcur, helper in banks.items():
            if hcur == cur or helper.alignment < RELIEF_LIGHT_THRESHOLD:
                continue
            spare = _sol_of(kernel, helper) - (kernel.banking.reserve_floor(helper) if hcur == _hub() else 0)
            give = min(need, max(0, spare) // 2)
            if give <= 0:
                continue
            _take_sol(kernel, helper, give)
            bought = kernel.fx_market.swap_sol_to(cur, give)     # spent buying its own money back
            borrower.reserves += bought
            key = f"{hcur}>{cur}"
            st["loans"][key] = st["loans"].get(key, 0) + give
            helper.alignment = round(min(1.0, helper.alignment + alignment.measure(kernel, helped_sol=give)), 4)
            st["help_given"] += 1
            logs.append(f"[MONEY] {helper.name} lends {give:,} SOL to {borrower.name}, which buys back "
                        f"{bought:,} {cur} to steady its money.")
            chron = getattr(kernel, "chronicle", None)
            if chron is not None:
                chron.record(kernel, "MONETARY_AID", cur, helper.name, f"{helper.name} stands behind the {cur}",
                             f"The {cur} was failing its holders and {borrower.name} had nothing left to defend "
                             f"it with. {helper.name} lent {give:,} SOL.", tags=["money", "aid"],
                             alignment=helper.alignment, author=helper.name)
            break
    # repayment: a recovered borrower sells reserves for SOL to pay back what it owes
    for key, owed in list(st["loans"].items()):
        hcur, _, cur = key.partition(">")
        borrower, helper = banks.get(cur), banks.get(hcur)
        if borrower is None or helper is None or owed <= 0 or distressed(kernel, cur):
            continue
        spare = borrower.reserves - kernel.banking.reserve_floor(borrower) * 2
        if spare <= 0:
            continue
        local = min(spare, int(owed * kernel.fx_market.rate(cur)))
        sol = kernel.fx_market.swap_to_sol(cur, local)
        borrower.reserves -= local
        _give_sol(kernel, helper, sol)
        st["loans"][key] = owed - sol
        if st["loans"][key] <= 0:
            st["loans"].pop(key)
            logs.append(f"[MONEY] {borrower.name} has repaid {helper.name}.")
    return logs


# ---------------------------------------------------------------------- the quarter
def quarter(kernel: Any) -> List[str]:
    st = stats(kernel)
    _record_returns(kernel)
    for cur, rec in st["by_currency"].items():
        if rec["regime"] == "reserve":
            _board(kernel, cur, rec)
    _measure_debasement(kernel)
    logs = _help(kernel)
    logs += review(kernel)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"regimes": {c: r["regime"] for c, r in st["by_currency"].items()},
            "controls": [c for c, r in st["by_currency"].items() if r["controls"]],
            "growth": {c: (round(g, 5) if (g := growth(r["returns"])) is not None else None)
                       for c, r in st["by_currency"].items()},
            "governors": {c: kernel.banking.banks[c].alignment for c in st["by_currency"]},
            "switches": st["switches"], "help_given": st["help_given"], "loans": dict(st["loans"]),
            "debased_sol": dict(st["debased_sol"]), "issued": dict(st["issued"]), "retired": dict(st["retired"]),
            "smuggled_sol": st.get("smuggled_sol", 0)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="regimes",
    state=lambda: {"by_currency": {}, "pooled": {}, "switches": 0, "help_given": 0, "loans": {},
                   "debased_sol": {}, "issued": {}, "retired": {}},
    season=quarter,
    summary=summary,
))
