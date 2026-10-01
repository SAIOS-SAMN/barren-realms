"""
Xylarium liquidity: who stands behind the exchange rates, and why.

The ISSE's SOL pools are constant-product (fx.py). Their depth was set once at genesis; here it becomes something
the economy chooses. Anyone holding both sides - AI captains (SOL credits and foreign wallets) and companies (a SOL
treasury and home-money operating cash) - may provide liquidity: deposit both sides in the pool's own ratio (no
price impact) for a share of the pool, and withdraw a share for its part of both sides.

Why they would: a provider earns the pool's swap fees and bears its impermanent loss, which for a constant-product
pool is about sigma^2 / 8 a period for log-rate volatility sigma. Each quarter every pool's fee yield and volatility
are read from what happened; a provider deposits when fee yield - sigma^2/8 beats the price of waiting (its money's
policy rate) and withdraws when it falls short - judged by the one decision rule (decide.py). A shallow, busy,
volatile pool pays well and draws depth; depth lowers both volatility and yield until providing earns just the
rate. Nobody sets the depth.

The genesis reserves belong to the money authorities (held as "isse": the Reserve's SOL and each regional central
bank's own money), and they too are a provider: when providing pays less than waiting they withdraw their stake to
the Reserve and the bank, and put it back when a pool's yield draws it. No fee floor or ceiling: a pool's price is
what its providers need in its two monies, but never more than the traders' other road - turning money into goods
and back at the ports' own spreads. A hyperinflating money's bank rate and widening spreads drive its fee up by
themselves; a deep idle pool's providers leave until what remains earns its keep at the fee traders will pay. Money only moves between holders and pools: a
deposit or withdrawal is a transfer, never a mint or burn.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import decide, fx as fx_mod, laws

ISSE = "isse"
PROVIDE_SHARE = 0.25          # of a provider's spare (or position) it moves in one pool in a quarter: not all at once


def stats(kernel: Any) -> Dict[str, Any]:
    st = state.of(kernel, "liquidity")
    fxm = kernel.fx_market
    for cur, p in fxm.pools.items():
        if cur not in st["shares"]:
            st["shares"][cur] = float(p["sol"])           # one share per SOL-side unit at genesis, all the exchange's
            st["positions"][cur] = {ISSE: float(p["sol"])}
            st["last_fees"][cur] = float(fxm.fees_collected.get(cur, 0.0))
    return st


def _value_sol(kernel: Any, cur: str) -> float:
    p = kernel.fx_market.pools[cur]
    return 2.0 * p["sol"]                                  # both sides at the mid rate


def share_value_sol(kernel: Any, cur: str, shares: float) -> float:
    st = stats(kernel)
    return _value_sol(kernel, cur) * shares / max(1e-9, st["shares"][cur])


def position_value_sol(kernel: Any, holder: str) -> float:
    st = stats(kernel)
    return sum(share_value_sol(kernel, cur, pos.get(holder, 0.0)) for cur, pos in st["positions"].items())


# ---------------------------------------------------------------------- reading the pools
def hurdle(kernel: Any, cur: str) -> float:
    """What a provider of the SOL/cur pool could earn a quarter by waiting instead: half its capital is in each
    money, each earning its own bank's rate."""
    return 0.5 * (decide.rate(kernel, "SOL") + decide.rate(kernel, cur))


def spread(kernel: Any, cur: str) -> Optional[float]:
    """What turning this money into goods and back costs at its own ports: the median bid-ask spread over the goods
    its ports trade (1 - bid/ask). None where no port trades in it."""
    from xylarium.kernel.economy import EconomyManager
    spreads = []
    for sec in kernel.sectors.values():
        port = sec.port
        if port is None or port.currency != cur:
            continue
        for comm, sells in list((port.sells or {}).items()):
            if not sells:
                continue
            bid, ask = EconomyManager.get_unit_prices(port, comm)
            if bid > 0 and ask > 0:
                spreads.append(max(0.0, 1.0 - bid / ask))
    if not spreads:
        return None
    spreads.sort()
    return spreads[len(spreads) // 2]


def goods_route(kernel: Any, cur: str) -> Optional[float]:
    """A trader's alternative to swapping SOL for `cur`: buy goods in one money and sell them for the other - half
    each money's spread. The exchange cannot charge more than this: past it, trade goes through the goods."""
    a, b = spread(kernel, "SOL"), spread(kernel, cur)
    if a is None or b is None:
        return None
    return 0.5 * (a + b)


def price_service(kernel: Any, cur: str, volume_q: float) -> float:
    """The exchange prices a pool's swaps at what makes providing its liquidity break even - fee yield equal to the
    providers' hurdle plus the impermanent loss (sigma^2/8) - moving a quarter of the way (in log) each quarter, as
    any seller feels out a price. No floor and no ceiling: the local law (its rates) and the pool's own trade set it."""
    st = stats(kernel)
    fxm = kernel.fx_market
    sigma = st["vol"].get(cur, 0.0)
    need = hurdle(kernel, cur) + sigma * sigma / 8.0
    charge = need * _value_sol(kernel, cur) / max(1.0, volume_q)       # per unit of value moved
    breakeven = charge / (1.0 + charge)       # the same charge as a share of what a trader puts in: always below 1
    route = goods_route(kernel, cur)
    if route is not None:
        breakeven = min(breakeven, route)     # what the traders' other road costs bounds it; depth adjusts to it
    old = min(1.0 - 1e-9, max(1e-9, fxm.fee(cur)))
    odds = math.log(old / (1.0 - old))        # felt out in log-odds, a quarter of the way each quarter
    odds += 0.25 * (math.log(max(1e-9, breakeven) / max(1e-9, 1.0 - breakeven)) - odds)
    fxm.fees[cur] = round(1.0 / (1.0 + math.exp(-odds)), 7)
    return fxm.fees[cur]


def read(kernel: Any) -> None:
    """Each quarter: every pool's fee yield and log-rate volatility, from what happened; the exchange re-prices."""
    st = stats(kernel)
    fxm = kernel.fx_market
    last_vol = st.setdefault("last_volume", {})
    for cur in fxm.pools:
        vol_now = float(fxm.volume_sol.get(cur, 0.0))
        volume_q, last_vol[cur] = vol_now - last_vol.get(cur, vol_now), vol_now
        fees = float(fxm.fees_collected.get(cur, 0.0))
        earned = fees - st["last_fees"].get(cur, fees)
        st["last_fees"][cur] = fees
        st["yield"][cur] = round(earned / max(1.0, _value_sol(kernel, cur)), 6)
        hist = st["rates"].setdefault(cur, [])
        hist.append(fxm.rate(cur))
        del hist[:-8]                                      # two years of quarter-end rates
        depth = st.setdefault("depth_hist", {}).setdefault(cur, [])
        depth.append(fxm.pools[cur]["sol"])
        del depth[:-8]
        if len(hist) >= 3:
            logs = [math.log(b / a) for a, b in zip(hist, hist[1:]) if a > 0 and b > 0]
            mean = sum(logs) / len(logs)
            st["vol"][cur] = round(math.sqrt(sum((x - mean) ** 2 for x in logs) / max(1, len(logs) - 1)), 6)
        if volume_q > 0:
            price_service(kernel, cur, volume_q)


def net_yield(kernel: Any, cur: str) -> float:
    """What providing earns a quarter after its impermanent loss (sigma^2 / 8)."""
    st = stats(kernel)
    sigma = st["vol"].get(cur, 0.0)
    return st["yield"].get(cur, 0.0) - sigma * sigma / 8.0


# ---------------------------------------------------------------------- deposits and withdrawals
def deposit(kernel: Any, holder: str, cur: str, sol: int, take_sol, take_local) -> float:
    """Add `sol` SOL and its pool-ratio of local money for shares. take_* move the money out of the holder."""
    fxm = kernel.fx_market
    st = stats(kernel)
    p = fxm.pools[cur]
    local = int(sol * p["local"] / p["sol"])
    if sol <= 0 or local <= 0:
        return 0.0
    shares = st["shares"][cur] * sol / p["sol"]
    take_sol(sol)
    take_local(local)
    p["sol"] += sol
    p["local"] += local
    st["shares"][cur] += shares
    st["positions"][cur][holder] = st["positions"][cur].get(holder, 0.0) + shares
    st["deposits"] += 1
    st["deposited_sol"] += sol * 2
    return shares


def withdraw(kernel: Any, holder: str, cur: str, shares: float, give_sol, give_local) -> Tuple[int, int]:
    fxm = kernel.fx_market
    st = stats(kernel)
    held = st["positions"][cur].get(holder, 0.0)
    shares = min(shares, held)
    if shares <= 0:
        return 0, 0
    p = fxm.pools[cur]
    part = shares / st["shares"][cur]
    sol, local = int(p["sol"] * part), int(p["local"] * part)
    p["sol"] -= sol
    p["local"] -= local
    st["shares"][cur] -= shares
    st["positions"][cur][holder] = held - shares
    if st["positions"][cur][holder] <= 1e-9:
        st["positions"][cur].pop(holder, None)
    give_sol(sol)
    give_local(local)
    st["withdrawals"] += 1
    st["withdrawn_sol"] += sol * 2
    return sol, local


# ---------------------------------------------------------------------- the providers
def _providers(kernel: Any) -> List[Tuple[str, Any, str]]:
    out = []
    for cap in kernel.captains.values():
        if getattr(cap, "is_ai", False) and not cap.faction_id:
            out.append((f"captain:{cap.id}", cap, "captain"))
    mm = getattr(kernel, "market_manager", None)
    for comp in (getattr(mm, "companies", {}) or {}).values():
        out.append((f"company:{comp.ticker}", comp, "company"))
    return out


def _purse(kernel: Any, who: Any, kind: str, cur: str):
    """(sol available, local available, take_sol, take_local, give_sol, give_local) for a provider."""
    if kind == "authority":
        fed = kernel.federal_reserve
        bank = kernel.banking.banks.get(cur)

        def take_sol(n): fed.treasury -= n
        def give_sol(n): fed.treasury += n
        def take_local(n): bank.reserves -= n
        def give_local(n): bank.reserves += n
        local = max(0, bank.reserves - kernel.banking.reserve_floor(bank)) if bank is not None else 0
        return max(0, fed.treasury), local, take_sol, take_local, give_sol, give_local
    if kind == "captain":
        def take_sol(n): who.credits -= n
        def give_sol(n): who.credits += n
        def take_local(n): who.fx_wallet[cur] = who.fx_wallet.get(cur, 0) - n
        def give_local(n): who.fx_wallet[cur] = who.fx_wallet.get(cur, 0) + n
        return max(0, who.credits), max(0, who.fx_wallet.get(cur, 0)), take_sol, take_local, give_sol, give_local
    home = getattr(who, "home_currency", "") or "SOL"

    def take_sol(n): who.treasury -= n
    def give_sol(n): who.treasury += n
    def take_local(n): who.home_cash -= n

    def give_local(n):
        # what comes back is the pool's money; a company whose home money has since changed (a conversion, a
        # rescue) takes it home through the exchange, not as if it were its own
        if home == cur:
            who.home_cash += n
        elif home == "SOL":
            who.treasury += kernel.fx_market.swap_to_sol(cur, n)
        else:
            got, _ = kernel.fx_market.convert(cur, home, n)
            who.home_cash += got
    local = max(0, who.home_cash) if home == cur else 0
    return max(0, who.treasury), local, take_sol, take_local, give_sol, give_local


def _spare(kernel: Any, who: Any, kind: str) -> float:
    """SOL a provider can commit: a captain's cash beyond its working reserve, a company's beyond a quarter's
    operating needs (its last quarter's revenue)."""
    if kind == "authority":
        return float(max(0, kernel.federal_reserve.treasury))
    if kind == "captain":
        from xylarium.config import AI_INVEST_RESERVE
        from xylarium.kernel.cognition import temperament
        return who.credits - AI_INVEST_RESERVE * temperament(who, kernel)["caution"]
    return who.treasury - max(1000, getattr(who, "quarterly_revenue", 0))


def quarter(kernel: Any) -> List[str]:
    read(kernel)
    st = stats(kernel)
    fxm = kernel.fx_market
    providers = _providers(kernel) + [(ISSE, None, "authority")]
    for holder, who, kind in providers:
        m = decide.mind_of_captain(kernel, who) if kind == "captain" else decide.mind(kernel, "biotic")
        spare = _spare(kernel, who, kind)
        options = []
        for cur in fxm.pools:
            if kind == "authority" and kernel.banking.banks.get(cur) is None:
                continue
            excess = net_yield(kernel, cur) - hurdle(kernel, cur)
            held = st["positions"][cur].get(holder, 0.0)
            if excess < 0 and held > 0:
                # holding loses against waiting: the position's shortfall over the horizon is the reason to leave
                loss = decide.worth(kernel, -excess * share_value_sol(kernel, cur, held), m)
                # positions unwind as they were built, a share a season: a pool is thinned, never emptied
                options.append(decide.option(f"withdraw:{cur}", 0.0, loss * PROVIDE_SHARE, cur=cur,
                                             shares=held * PROVIDE_SHARE))
            if excess > 0 and spare > 0:
                sol_have, local_have, *_ = _purse(kernel, who, kind, cur)
                rate = fxm.rate(cur)
                sol = int(min(spare * PROVIDE_SHARE, sol_have, local_have / rate if rate > 0 else 0))
                if sol >= 100:
                    gain = decide.worth(kernel, excess * 2 * sol, m)
                    options.append(decide.option(f"provide:{cur}", 0.0, gain, cur=cur, sol=sol))
        pick = decide.choose(kernel, options, m, holder, "liquidity")
        if pick is None:
            continue
        cur = pick["cur"]
        _, _, take_sol, take_local, give_sol, give_local = _purse(kernel, who, kind, cur)
        if pick["name"].startswith("provide"):
            deposit(kernel, holder, cur, pick["sol"], take_sol, take_local)
        else:
            withdraw(kernel, holder, cur, pick["shares"], give_sol, give_local)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    fxm = kernel.fx_market
    return {"depth_sol": {c: int(_value_sol(kernel, c)) for c in fxm.pools}, "fee": dict(fxm.fees),
            "fee_yield_q": dict(st["yield"]), "vol_q": dict(st["vol"]),
            "providers": {c: len([h for h in pos if h != ISSE]) for c, pos in st["positions"].items()},
            "isse_share": {c: round(pos.get(ISSE, 0.0) / max(1e-9, st["shares"][c]), 3)
                           for c, pos in st["positions"].items()},
            "deposits": st["deposits"], "withdrawals": st["withdrawals"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="liquidity",
    state=lambda: {"shares": {}, "positions": {}, "last_fees": {}, "yield": {}, "vol": {}, "rates": {},
                   "deposits": 0, "withdrawals": 0, "deposited_sol": 0, "withdrawn_sol": 0},
    season=quarter,
    summary=summary,
))
