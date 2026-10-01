"""
Xylarium: Regional currencies and the ISSE foreign-exchange desk.

Each security zone runs its own money: Federation space settles in SOL (the reserve
currency captains hold as ``credits``), the Borderland in Frontier Scrip (FRN) and
Anarchy space in Void Marks (VOID). Ports, colony vaults, company treasuries and
freight escrow are denominated in their region's currency; captains hold foreign
balances in ``fx_wallet``.

The ISSE makes markets through constant-product liquidity pools (x * y = k) pairing
SOL with each regional currency. Pool reserves are real money: trade flows move the
reserves and therefore the rate, and swap fees stay in the pool as liquidity.
"""

import math
from contextlib import contextmanager
from typing import Any, Dict, Optional, Tuple

from xylarium.config import CURRENCIES, FX_POOL_SEED, FX_FEE, PRICE_LEVEL

SOL = "SOL"
import os as _os
FX_TRACE: Optional[Dict[str, Dict[str, float]]] = {} if _os.environ.get("XYL_FX_TRACE") else None


def currency_for_security(security: Any) -> str:
    zone = getattr(security, "value", security)
    for code, info in CURRENCIES.items():
        if info["zone"] == zone:
            return code
    return SOL


class FXMarket:
    def __init__(self) -> None:
        self.pools: Dict[str, Dict[str, float]] = {
            cur: {"sol": float(s), "local": float(l)} for cur, (s, l) in FX_POOL_SEED.items()
        }
        self.volume_sol: Dict[str, float] = {cur: 0.0 for cur in self.pools}
        self.fees_collected: Dict[str, float] = {cur: 0.0 for cur in self.pools}
        # Galactic ISSE: direct cross pairs between federation currencies (no SOL hop), seeded at parity
        from xylarium.config import CROSS_POOL_SEED_SOL_VALUE
        locals_ = sorted(self.pools)
        self.cross_pools: Dict[str, Dict[str, Any]] = {}
        for i, a in enumerate(locals_):
            for b in locals_[i + 1:]:
                self.cross_pools[f"{a}/{b}"] = {
                    "ca": a, "cb": b,
                    "a": float(CROSS_POOL_SEED_SOL_VALUE * PRICE_LEVEL.get(a, 1.0)),
                    "b": float(CROSS_POOL_SEED_SOL_VALUE * PRICE_LEVEL.get(b, 1.0)),
                }
        self.cross_volume: Dict[str, float] = {k: 0.0 for k in self.cross_pools}

    # ------------------------------------------------------------------ quotes
    def rate(self, cur: str) -> float:
        """Mid rate: local units per 1 SOL."""
        if cur == SOL or cur not in self.pools:
            return 1.0
        p = self.pools[cur]
        return p["local"] / p["sol"]

    def to_sol_value(self, cur: str, amount: float) -> float:
        return amount if cur == SOL else amount / self.rate(cur)

    def price_level_drift(self, cur: str) -> float:
        """How far the live rate has moved from the genesis price level (>1: local currency weakened)."""
        return self.rate(cur) / PRICE_LEVEL.get(cur, 1.0)

    # ------------------------------------------------------------------ swaps
    def _trace(self, cur: str, sol_net: float) -> None:
        """XYL_FX_TRACE=1: net SOL into each pool (+) or out of it (-), by the calling site (diagnostics only)."""
        import sys
        f = sys._getframe(2)
        while f is not None and f.f_code.co_filename.endswith("fx.py"):
            f = f.f_back
        where = f"{f.f_code.co_filename.rsplit('/', 1)[-1]}:{f.f_code.co_name}" if f is not None else "?"
        t = FX_TRACE.setdefault(cur, {})
        t[where] = t.get(where, 0.0) + sol_net

    def swap_sol_to(self, cur: str, sol_in: int) -> int:
        if FX_TRACE is not None:
            self._trace(cur, sol_in)
        p = self.pools[cur]
        k = p["sol"] * p["local"]
        eff = sol_in * (1 - FX_FEE)
        out = int(math.floor(p["local"] - k / (p["sol"] + eff)))
        p["sol"] += sol_in
        p["local"] -= out
        self.volume_sol[cur] += sol_in
        self.fees_collected[cur] += sol_in * FX_FEE
        return out

    def swap_to_sol(self, cur: str, local_in: int) -> int:
        p = self.pools[cur]
        k = p["sol"] * p["local"]
        eff = local_in * (1 - FX_FEE)
        out = int(math.floor(p["sol"] - k / (p["local"] + eff)))
        if FX_TRACE is not None:
            self._trace(cur, -out)
        p["local"] += local_in
        p["sol"] -= out
        self.volume_sol[cur] += out
        self.fees_collected[cur] += local_in * FX_FEE / self.rate(cur)
        return out

    def sol_needed_for(self, cur: str, local_out: int) -> Optional[int]:
        p = self.pools[cur]
        if local_out >= p["local"] * 0.5:
            return None  # would drain the pool
        k = p["sol"] * p["local"]
        eff = k / (p["local"] - local_out) - p["sol"]
        return int(math.ceil(eff / (1 - FX_FEE))) + 1

    # ------------------------------------------------------------------ Galactic ISSE cross pairs
    def _cross(self, from_cur: str, to_cur: str) -> Optional[Tuple[str, str, str]]:
        """(pair key, side paid in, side paid out) for a direct pair, if one is listed."""
        for key in (f"{from_cur}/{to_cur}", f"{to_cur}/{from_cur}"):
            pool = self.cross_pools.get(key)
            if pool:
                return (key, "a", "b") if pool["ca"] == from_cur else (key, "b", "a")
        return None

    def quote_cross(self, from_cur: str, to_cur: str, amount: int) -> Optional[int]:
        route = self._cross(from_cur, to_cur)
        if not route:
            return None
        key, side_in, side_out = route
        p = self.cross_pools[key]
        k = p[side_in] * p[side_out]
        return int(math.floor(p[side_out] - k / (p[side_in] + amount * (1 - FX_FEE))))

    def quote_via_sol(self, from_cur: str, to_cur: str, amount: int) -> int:
        """What routing through the two federation exchanges (and SOL) would pay, without trading."""
        def out_of(pool_in: float, pool_out: float, x: float) -> float:
            return pool_out - pool_in * pool_out / (pool_in + x * (1 - FX_FEE))
        sol = amount if from_cur == SOL else out_of(self.pools[from_cur]["local"], self.pools[from_cur]["sol"], amount)
        if to_cur == SOL:
            return int(sol)
        return int(out_of(self.pools[to_cur]["sol"], self.pools[to_cur]["local"], sol))

    def swap_cross(self, from_cur: str, to_cur: str, amount: int) -> int:
        key, side_in, side_out = self._cross(from_cur, to_cur)
        p = self.cross_pools[key]
        out = self.quote_cross(from_cur, to_cur, amount)
        p[side_in] += amount
        p[side_out] -= out
        self.cross_volume[key] = self.cross_volume.get(key, 0.0) + self.to_sol_value(from_cur, amount)
        return out

    def reanchor_cross(self, rate: float) -> Dict[str, float]:
        """
        The Galactic ISSE and the federation exchanges are one house: each fiscal quarter it rebalances its
        own books so a cross pair's price moves ``rate`` of the way toward the rate the SOL hub implies.
        The cross pool keeps its depth (constant product); the difference in each currency is moved between
        the cross pool and that currency's federation pool - an internal transfer, nothing minted or burned.
        Returns each pair's gap before the rebalance.
        """
        gaps: Dict[str, float] = {}
        for key, p in self.cross_pools.items():
            ca, cb = p["ca"], p["cb"]
            if ca not in self.pools or cb not in self.pools or p["a"] <= 0 or p["b"] <= 0:
                continue
            implied = self.rate(cb) / self.rate(ca)          # b per a, through SOL
            ratio = p["b"] / p["a"]
            gaps[key] = round(ratio / implied - 1, 4)
            new_ratio = ratio * (implied / ratio) ** rate
            k = p["a"] * p["b"]
            da = int(round(math.sqrt(k / new_ratio) - p["a"]))
            db = int(round(math.sqrt(k * new_ratio) - p["b"]))
            la, lb = self.pools[ca]["local"], self.pools[cb]["local"]
            # Never move more than a tenth of a federation pool's depth in one quarter
            if da > 0 and da > la * 0.1 or db > 0 and db > lb * 0.1:
                scale = min((la * 0.1) / da if da > 0 else 1.0, (lb * 0.1) / db if db > 0 else 1.0)
                da, db = int(da * scale), int(db * scale)
            p["a"] += da
            self.pools[ca]["local"] -= da
            p["b"] += db
            self.pools[cb]["local"] -= db
        return gaps

    def convert(self, from_cur: str, to_cur: str, amount: int) -> Tuple[int, str]:
        """Best execution across the federation exchanges and the Galactic ISSE. Returns (out, venue)."""
        if from_cur == to_cur:
            return amount, "none"
        if SOL not in (from_cur, to_cur):
            direct = self.quote_cross(from_cur, to_cur, amount)
            if direct is not None and direct > self.quote_via_sol(from_cur, to_cur, amount):
                return self.swap_cross(from_cur, to_cur, amount), "Galactic ISSE"
        sol = amount if from_cur == SOL else self.swap_to_sol(from_cur, amount)
        out = sol if to_cur == SOL else self.swap_sol_to(to_cur, sol)
        return out, "federation exchanges via SOL"

    # ------------------------------------------------------------------ captain desk
    def exchange(self, captain: Any, from_cur: str, to_cur: str, amount: int) -> Tuple[bool, str, int]:
        from_cur, to_cur = from_cur.upper(), to_cur.upper()
        if from_cur == to_cur or amount <= 0:
            return False, "Choose two different currencies and a positive amount.", 0
        for c in (from_cur, to_cur):
            if c != SOL and c not in self.pools:
                return False, f"Unknown currency '{c}'. Listed: {', '.join(CURRENCIES)}.", 0
        if balance(captain, from_cur) < amount:
            return False, f"Insufficient {from_cur}: you hold {balance(captain, from_cur):,}.", 0
        debit(captain, from_cur, amount)
        out, venue = self.convert(from_cur, to_cur, amount)
        credit(captain, to_cur, out)
        return True, (
            f"ISSE FX: exchanged {amount:,} {from_cur} for {out:,} {to_cur} on the {venue} "
            f"(mid {self.rate(to_cur) / self.rate(from_cur):.4f} {to_cur}/{from_cur}, fee {FX_FEE:.1%})."
        ), out

    def ensure_local(self, captain: Any, cur: str, needed: int) -> bool:
        """Auto-converts a SOL shortfall into local currency for a purchase. Returns True if covered."""
        if cur == SOL:
            return captain.credits >= needed
        short = needed - captain.fx_wallet.get(cur, 0)
        if short <= 0:
            return True
        sol_in = self.sol_needed_for(cur, short)
        if sol_in is None or captain.credits < sol_in:
            return False
        captain.credits -= sol_in
        credit(captain, cur, self.swap_sol_to(cur, sol_in))
        return captain.fx_wallet.get(cur, 0) >= needed

    def expected_depreciation(self, kernel: Any, cur: str) -> float:
        """A holder's forecast of how fast this money loses value against SOL a quarter: the mean log change of
        its quarter-end rate over the last two years (liquidity.py reads them)."""
        import math as _m
        from xylarium.kernel import liquidity
        hist = liquidity.stats(kernel)["rates"].get(cur, [])
        if len(hist) < 2:
            return 0.0
        steps = [_m.log(b / a) for a, b in zip(hist, hist[1:]) if a > 0 and b > 0]
        return sum(steps) / len(steps) if steps else 0.0

    def advantage(self, kernel: Any, cur: str) -> float:
        """Uncovered interest parity, as a holder sees it: what this money pays a quarter (its central bank's
        deposit rate) less what it is expected to lose against SOL."""
        if kernel is None:
            return -1.0
        return kernel.banking.paid_rate(cur) - self.expected_depreciation(kernel, cur)

    def share_to_convert(self, kernel: Any, captain: Any, cur: str) -> float:
        """How much of a balance a holder converts to SOL: none while holding pays; past that, a share growing with
        the shortfall measured in its own judgement's error (laws.cognition noise x the money's volatility) - so
        holders with different minds and seen through a noisy market do not all move at once."""
        import math as _m
        import random as _r
        from xylarium.kernel import laws, liquidity
        adv = self.advantage(kernel, cur)
        vol = max(1e-4, liquidity.stats(kernel)["vol"].get(cur, 0.0)) if kernel is not None else 1.0
        noise = laws.cognition(getattr(captain, "metabolism", None) or "biotic")["noise"]
        seen = adv + _r.Random(f"fx:{captain.id}:{getattr(kernel, 'cycle_count', 0)}").gauss(0.0, noise * vol)
        return 0.0 if seen >= 0 else 1.0 - _m.exp(seen / vol)

    def repatriate(self, captain: Any, threshold_sol: float, keep: Optional[set] = None, kernel: Any = None) -> int:
        """Converts foreign balances worth more than ``threshold_sol`` back into SOL - except the money of the
        region the captain is working in (``keep``), and - when the kernel is known - only the share its expected
        return no longer justifies holding (share_to_convert)."""
        total = 0
        for cur, amt in list(captain.fx_wallet.items()):
            if keep and cur in keep:
                continue
            if kernel is not None:
                amt = int(amt * self.share_to_convert(kernel, captain, cur))
            if cur in self.pools and amt > 0 and self.to_sol_value(cur, amt) > threshold_sol:
                debit(captain, cur, amt)
                sol = self.swap_to_sol(cur, amt)
                captain.credits += sol
                total += sol
        return total

    @staticmethod
    def working_currencies(kernel: Any, captain: Any) -> set:
        """The money a captain keeps: its region's (where it is), and its faction's own."""
        keep = set()
        sec = kernel.sectors.get(captain.sector_id) if kernel is not None else None
        if sec is not None:
            keep.add(sec.port.currency if sec.port is not None else currency_for_security(sec.security))
        fid = getattr(captain, "faction_id", None)
        factions = getattr(kernel, "factions", None)
        if fid and factions is not None and fid in factions.factions:
            keep.add(factions.factions[fid].currency)
        return keep

    # ------------------------------------------------------------------ persistence
    def pool_holdings(self) -> Dict[str, int]:
        out = {SOL: 0}
        for cur, p in self.pools.items():
            out[SOL] += int(p["sol"])
            out[cur] = out.get(cur, 0) + int(p["local"])
        for p in getattr(self, "cross_pools", {}).values():
            out[p["ca"]] = out.get(p["ca"], 0) + int(p["a"])
            out[p["cb"]] = out.get(p["cb"], 0) + int(p["b"])
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {"pools": {c: dict(p) for c, p in self.pools.items()},
                "volume_sol": dict(self.volume_sol), "fees_collected": dict(self.fees_collected),
                "cross_pools": {k: dict(p) for k, p in self.cross_pools.items()},
                "cross_volume": dict(self.cross_volume)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FXMarket":
        fx = cls()
        for c, p in data.get("pools", {}).items():
            fx.pools[c] = {"sol": float(p["sol"]), "local": float(p["local"])}
        fx.volume_sol.update({c: float(v) for c, v in data.get("volume_sol", {}).items()})
        fx.fees_collected.update({c: float(v) for c, v in data.get("fees_collected", {}).items()})
        if "cross_pools" in data:
            fx.cross_pools = {k: {"ca": p["ca"], "cb": p["cb"], "a": float(p["a"]), "b": float(p["b"])}
                              for k, p in data["cross_pools"].items()}
        else:
            fx.cross_pools = {}   # a pre-Galactic-ISSE save: no cross pairs appear out of nowhere
        fx.cross_volume = {k: float(v) for k, v in data.get("cross_volume", {}).items()}
        return fx


# ---------------------------------------------------------------------- wallets
def balance(captain: Any, cur: str) -> int:
    return int(captain.credits) if cur == SOL else int(captain.fx_wallet.get(cur, 0))


def credit(captain: Any, cur: str, amount: int) -> None:
    if amount <= 0:
        return
    if cur == SOL:
        captain.credits += amount
    else:
        captain.fx_wallet[cur] = captain.fx_wallet.get(cur, 0) + amount


def debit(captain: Any, cur: str, amount: int) -> None:
    if amount <= 0:
        return
    if cur == SOL:
        captain.credits -= amount
    else:
        captain.fx_wallet[cur] = captain.fx_wallet.get(cur, 0) - amount
        if captain.fx_wallet[cur] == 0:
            captain.fx_wallet.pop(cur, None)


@contextmanager
def settle_in(captain: Any, cur: str):
    """
    Temporarily presents the captain's balance in ``cur`` as ``captain.credits`` so
    single-currency trade code settles in the port's local money.
    """
    if cur == SOL:
        yield
        return
    sol_balance = captain.credits
    captain.credits = captain.fx_wallet.get(cur, 0)
    try:
        yield
    finally:
        local = captain.credits
        captain.credits = sol_balance
        if local:
            captain.fx_wallet[cur] = local
        else:
            captain.fx_wallet.pop(cur, None)


ACTIVE_FX: Optional[FXMarket] = None


def set_active(fx: Optional[FXMarket]) -> None:
    global ACTIVE_FX
    ACTIVE_FX = fx
