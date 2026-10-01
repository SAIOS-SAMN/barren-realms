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

The genesis reserves belong to the exchange itself ("isse"). Money only moves between holders and pools: a
deposit or withdrawal is a transfer, never a mint or burn.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import decide, fx as fx_mod, laws

ISSE = "isse"
PROVIDE_SHARE = 0.25          # of a provider's spare it commits to one pool in a quarter (a position, not all-in)


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
def read(kernel: Any) -> None:
    """Each quarter: every pool's fee yield and log-rate volatility, from what happened."""
    st = stats(kernel)
    fxm = kernel.fx_market
    for cur in fxm.pools:
        fees = float(fxm.fees_collected.get(cur, 0.0))
        earned = fees - st["last_fees"].get(cur, fees)
        st["last_fees"][cur] = fees
        st["yield"][cur] = round(earned / max(1.0, _value_sol(kernel, cur)), 6)
        hist = st["rates"].setdefault(cur, [])
        hist.append(fxm.rate(cur))
        del hist[:-8]                                      # two years of quarter-end rates
        if len(hist) >= 3:
            logs = [math.log(b / a) for a, b in zip(hist, hist[1:]) if a > 0 and b > 0]
            mean = sum(logs) / len(logs)
            st["vol"][cur] = round(math.sqrt(sum((x - mean) ** 2 for x in logs) / max(1, len(logs) - 1)), 6)


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
    def give_local(n): who.home_cash += n
    local = max(0, who.home_cash) if home == cur else 0
    return max(0, who.treasury), local, take_sol, take_local, give_sol, give_local


def _spare(kernel: Any, who: Any, kind: str) -> float:
    """SOL a provider can commit: a captain's cash beyond its working reserve, a company's beyond a quarter's
    operating needs (its last quarter's revenue)."""
    if kind == "captain":
        from xylarium.config import AI_INVEST_RESERVE
        from xylarium.kernel.cognition import temperament
        return who.credits - AI_INVEST_RESERVE * temperament(who, kernel)["caution"]
    return who.treasury - max(1000, getattr(who, "quarterly_revenue", 0))


def quarter(kernel: Any) -> List[str]:
    read(kernel)
    st = stats(kernel)
    fxm = kernel.fx_market
    for holder, who, kind in _providers(kernel):
        m = decide.mind_of_captain(kernel, who) if kind == "captain" else decide.mind(kernel, "biotic")
        spare = _spare(kernel, who, kind)
        options = []
        for cur in fxm.pools:
            excess = net_yield(kernel, cur) - decide.rate(kernel, "SOL")
            held = st["positions"][cur].get(holder, 0.0)
            if excess < 0 and held > 0:
                # holding loses against waiting: the position's shortfall over the horizon is the reason to leave
                loss = decide.worth(kernel, -excess * share_value_sol(kernel, cur, held), m)
                options.append(decide.option(f"withdraw:{cur}", 0.0, loss, cur=cur, shares=held))
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
    return {"depth_sol": {c: int(_value_sol(kernel, c)) for c in fxm.pools},
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
