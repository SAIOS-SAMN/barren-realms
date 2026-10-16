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
from fractions import Fraction
from typing import Any, Dict, Optional, Tuple

from xylarium.config import CURRENCIES, FX_POOL_SEED, FX_FEE, PRICE_LEVEL

LEGACY_HUB = "SOL"   # the settled board's exchange unit, founded with that board (its founders' name, kept as data)


def hub() -> Optional[str]:
    """The live exchange's unit (its identity), or None where no exchange has been founded yet."""
    return ACTIVE_FX.hub if ACTIVE_FX is not None else LEGACY_HUB
import os as _os
FX_TRACE: Optional[Dict[str, Dict[str, float]]] = {} if _os.environ.get("XYL_FX_TRACE") else None


def currency_for_security(security: Any) -> str:
    zone = getattr(security, "value", security)
    for code, info in CURRENCIES.items():
        if info["zone"] == zone:
            return code
    return hub()


def exact(v: Any) -> Fraction:
    """A pool's balance, exact (Concordance 9.1a): a pool's reserves cross every seam (the money supply, the block's
    state root), so they are Fractions - a float's own binary value where one is handed in, never rounded."""
    return v if isinstance(v, Fraction) else Fraction(v)


class FXMarket:
    def __init__(self) -> None:
        self.hub: Optional[str] = LEGACY_HUB     # the unit every pool pairs with (None until an exchange is founded)
        self.pools: Dict[str, Dict[str, Fraction]] = {
            cur: {"sol": exact(s), "local": exact(l)} for cur, (s, l) in FX_POOL_SEED.items()
        }
        self.volume_sol: Dict[str, float] = {cur: 0.0 for cur in self.pools}
        self.fees: Dict[str, float] = {cur: FX_FEE for cur in self.pools}   # each exchange prices its own service
        self.fees_collected: Dict[str, float] = {cur: 0.0 for cur in self.pools}
        # Galactic ISSE: direct cross pairs between federation currencies (no SOL hop), seeded at parity
        from xylarium.config import CROSS_POOL_SEED_SOL_VALUE
        locals_ = sorted(self.pools)
        self.cross_pools: Dict[str, Dict[str, Any]] = {}
        for i, a in enumerate(locals_):
            for b in locals_[i + 1:]:
                self.cross_pools[f"{a}/{b}"] = {
                    "ca": a, "cb": b,
                    "a": exact(CROSS_POOL_SEED_SOL_VALUE) * exact(PRICE_LEVEL.get(a, 1.0)),
                    "b": exact(CROSS_POOL_SEED_SOL_VALUE) * exact(PRICE_LEVEL.get(b, 1.0)),
                }
        self.cross_volume: Dict[str, float] = {k: 0.0 for k in self.cross_pools}

    # ------------------------------------------------------------------ quotes
    def rate(self, cur: str) -> float:
        """Mid rate: local units per 1 SOL."""
        if cur == self.hub or cur not in self.pools:
            return 1.0
        p = self.pools[cur]
        return float(p["local"] / p["sol"])                 # a quote for the legacy float simulation

    def set_rate(self, cur: str, new_rate: float) -> None:
        """Sets the mid rate by adjusting local units relative to sol reserve."""
        if cur == self.hub or cur not in self.pools or new_rate <= 0:
            return
        p = self.pools[cur]
        p["local"] = p["sol"] * exact(new_rate)

    def to_sol_value(self, cur: str, amount: float) -> float:
        return amount if cur == self.hub else amount / self.rate(cur)

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

    def fee(self, cur: str) -> float:
        return self.fees.get(cur, FX_FEE)

    def swap_sol_to(self, cur: str, sol_in: int) -> int:
        if FX_TRACE is not None:
            self._trace(cur, sol_in)
        p = self.pools[cur]
        k = p["sol"] * p["local"]
        eff = sol_in * (1 - exact(self.fee(cur)))
        out = math.floor(p["local"] - k / (p["sol"] + eff))       # exact constant product, floored once
        p["sol"] += sol_in
        p["local"] -= out
        self.volume_sol[cur] += sol_in
        self.fees_collected[cur] += sol_in * self.fee(cur)
        return out

    def swap_to_sol(self, cur: str, local_in: int) -> int:
        p = self.pools[cur]
        k = p["sol"] * p["local"]
        eff = local_in * (1 - exact(self.fee(cur)))
        out = math.floor(p["sol"] - k / (p["local"] + eff))       # exact constant product, floored once
        if FX_TRACE is not None:
            self._trace(cur, -out)
        p["local"] += local_in
        p["sol"] -= out
        self.volume_sol[cur] += out
        self.fees_collected[cur] += local_in * self.fee(cur) / self.rate(cur)
        return out

    def sol_needed_for(self, cur: str, local_out: int) -> Optional[int]:
        p = self.pools[cur]
        if local_out >= p["local"] * 0.5:
            return None  # would drain the pool
        k = p["sol"] * p["local"]
        eff = k / (p["local"] - local_out) - p["sol"]
        return math.ceil(eff / (1 - exact(self.fee(cur)))) + 1

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
        return math.floor(p[side_out] - k / (p[side_in] + amount * (1 - exact(FX_FEE))))

    def quote_via_sol(self, from_cur: str, to_cur: str, amount: int) -> int:
        """What routing through the two federation exchanges (and SOL) would pay, without trading."""
        def out_of(pool_in: float, pool_out: float, x: float, fee: float) -> float:
            return pool_out - pool_in * pool_out / (pool_in + x * (1 - fee))
        sol = amount if from_cur == self.hub else out_of(self.pools[from_cur]["local"], self.pools[from_cur]["sol"], amount,
                                                    self.fee(from_cur))
        if to_cur == self.hub:
            return int(sol)
        return int(out_of(self.pools[to_cur]["sol"], self.pools[to_cur]["local"], sol, self.fee(to_cur)))

    def value_in(self, from_cur: str, to_cur: str, amount: float) -> float:
        """What an amount of one money fetches in another through the pools (fees and depth), unrounded - how a mind
        carries a sum into its own unit of account. 0 where no pool carries either money."""
        if from_cur == to_cur or amount == 0:
            return float(amount)
        if not self.can_convert(from_cur, to_cur):
            return 0.0
        sign = 1.0 if amount > 0 else -1.0
        x = abs(float(amount))

        def out_of(pool_in: float, pool_out: float, v: float, fee: float) -> float:
            return pool_out - pool_in * pool_out / (pool_in + v * (1 - fee))
        hubv = x if from_cur == self.hub else out_of(self.pools[from_cur]["local"], self.pools[from_cur]["sol"], x,
                                                     self.fee(from_cur))
        if to_cur == self.hub:
            return sign * hubv
        return sign * out_of(self.pools[to_cur]["sol"], self.pools[to_cur]["local"], hubv, self.fee(to_cur))

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

    def can_convert(self, from_cur: str, to_cur: str) -> bool:
        """Is there a market between these moneys? (A money issued before any exchange lists it has none.)"""
        return from_cur == to_cur or all(c == self.hub or c in self.pools for c in (from_cur, to_cur))

    def convert(self, from_cur: str, to_cur: str, amount: int) -> Tuple[int, str]:
        """Best execution across the federation exchanges and the Galactic ISSE. Returns (out, venue).
        A money no exchange lists is listed the first time a payment needs it (institutions: its issuers' deposit);
        if it cannot be, the house holds the payment unsettled - nothing is made or lost - and nothing arrives."""
        if from_cur == to_cur:
            return amount, "none"
        from xylarium.kernel import ledger
        kernel = getattr(ledger, "ACTIVE_KERNEL", None)
        for c in (from_cur, to_cur):
            if c != self.hub and c not in self.pools and kernel is not None and kernel.fx_market is self:
                from xylarium.kernel import institutions
                institutions._open_pool(kernel, c)
        if not self.can_convert(from_cur, to_cur):
            self.unsettled = getattr(self, "unsettled", {})
            self.unsettled[from_cur] = self.unsettled.get(from_cur, 0) + amount
            return 0, "unsettled"
        if self.hub not in (from_cur, to_cur):
            direct = self.quote_cross(from_cur, to_cur, amount)
            if direct is not None and direct > self.quote_via_sol(from_cur, to_cur, amount):
                return self.swap_cross(from_cur, to_cur, amount), "Galactic ISSE"
        sol = amount if from_cur == self.hub else self.swap_to_sol(from_cur, amount)
        out = sol if to_cur == self.hub else self.swap_sol_to(to_cur, sol)
        return out, "federation exchanges via SOL"

    # ------------------------------------------------------------------ captain desk
    def exchange(self, captain: Any, from_cur: str, to_cur: str, amount: int) -> Tuple[bool, str, int]:
        from_cur, to_cur = from_cur.upper(), to_cur.upper()
        if from_cur == to_cur or amount <= 0:
            return False, "Choose two different currencies and a positive amount.", 0
        for c in (from_cur, to_cur):
            if c != self.hub and c not in self.pools:
                return False, f"Unknown currency '{c}'. Listed: {', '.join([self.hub or ''] + sorted(self.pools))}.", 0
        if balance(captain, from_cur) < amount:
            return False, f"Insufficient {from_cur}: you hold {balance(captain, from_cur):,}.", 0
        from xylarium.kernel import ledger, regimes
        if regimes.controlled(ledger.active_kernel(), from_cur):
            return False, f"The {from_cur} is under capital controls: its exchange is closed to holders.", 0
        debit(captain, from_cur, amount)
        out, venue = self.convert(from_cur, to_cur, amount)
        credit(captain, to_cur, out)
        return True, (
            f"ISSE FX: exchanged {amount:,} {from_cur} for {out:,} {to_cur} on the {venue} "
            f"(mid {self.rate(to_cur) / self.rate(from_cur):.4f} {to_cur}/{from_cur}, "
            f"fee {self.fee(to_cur if to_cur != self.hub else from_cur):.2%})."
        ), out

    def ensure_local(self, captain: Any, cur: str, needed: int) -> bool:
        """Auto-converts a SOL shortfall into local currency for a purchase. Returns True if covered."""
        if cur == self.hub:
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

    def black_market(self, kernel: Any, captain: Any, cur: str, amt: int) -> int:
        """Convert controlled money through smugglers: they charge what their own risk is worth - the law's
        presence where the captain stands - paid to the relay port (the lawless one of that money nearest it);
        the rest clears through the pool as any swap does. It is an offence, filed where it happened."""
        from xylarium.kernel import law, topology
        sector = kernel.sectors.get(captain.sector_id)
        risk = min(0.9, law.presence(kernel, sector)) if sector is not None else 0.5
        relay = None
        for sid in sorted(topology.hops(kernel, captain.sector_id, 8).items(), key=lambda kv: kv[1]):
            sec = kernel.sectors[sid[0]]
            if sec.port is not None and sec.port.currency == cur and law.presence(kernel, sec) < 0.2:
                relay = sec.port
                break
        if relay is None:
            return 0                                       # no smugglers this side of the law
        cut = int(amt * risk)
        debit(captain, cur, amt)
        relay.treasury += cut
        sol = self.swap_to_sol(cur, amt - cut)
        captain.credits += sol
        law.file(kernel, "smuggling", captain, sector, int(sol), None, note=f"{amt:,} {cur} past controls")
        from xylarium.kernel import regimes
        rs = regimes.stats(kernel)
        rs["smuggled_sol"] = rs.get("smuggled_sol", 0) + sol
        return sol

    def expected_depreciation(self, kernel: Any, cur: str) -> float:
        """A holder's forecast of how fast this money loses value against SOL a quarter: relative purchasing power -
        the gap between its measured inflation and SOL's (prices.py). A reading of fundamentals, not of the rate's
        own recent path, so a fall does not feed on itself."""
        if kernel is None:
            return 0.0
        from xylarium.kernel import prices
        return prices.inflation(kernel, cur) - prices.inflation(kernel, self.hub)

    def advantage(self, kernel: Any, cur: str) -> float:
        """Uncovered interest parity, as a holder sees it: what this money pays a quarter (its central bank's
        deposit rate) less what it is expected to lose against SOL."""
        if kernel is None:
            return -1.0
        return kernel.banking.paid_rate(cur) - self.expected_depreciation(kernel, cur)

    def share_to_convert(self, kernel: Any, captain: Any, cur: str) -> float:
        """How much of a balance a holder converts to SOL. Converting costs the pool's fee now; holding costs the
        expected shortfall every quarter of the holder's own horizon. It converts nothing while holding is cheaper
        and a share growing with how far it is past that - each mind seeing the shortfall through its own error,
        so holders do not all move at once."""
        import math as _m
        import random as _r
        from xylarium.kernel import decide, laws, liquidity
        adv = self.advantage(kernel, cur)
        vol = max(1e-4, liquidity.stats(kernel)["vol"].get(cur, 0.0)) if kernel is not None else 1.0
        m = decide.mind_of_captain(kernel, captain) if kernel is not None else laws.cognition("biotic")
        seen = adv + _r.Random(f"fx:{captain.id}:{getattr(kernel, 'cycle_count', 0)}").gauss(0.0, m["noise"] * vol)
        if seen >= 0:
            return 0.0
        horizon = decide.horizon(m)
        lost = laws.present_value(-seen, horizon, 0.0)            # what a unit held loses over the horizon
        fee = self.fee(cur)
        return 0.0 if lost <= fee else 1.0 - _m.exp(-(lost - fee) / max(1e-3, fee))

    def repatriate(self, captain: Any, threshold_sol: float, keep: Optional[set] = None, kernel: Any = None) -> int:
        """Converts foreign balances worth more than ``threshold_sol`` back into SOL - except the money of the
        region the captain is working in (``keep``), and - when the kernel is known - only the share its expected
        return no longer justifies holding (share_to_convert)."""
        total = 0
        for cur, amt in list(captain.fx_wallet.items()):
            if keep and cur in keep:
                continue
            from xylarium.kernel import regimes
            if regimes.controlled(kernel, cur):
                # the exchange is closed to its holders; a captain who has made its peace with the Dark finds
                # the smugglers at the deep-void relays instead
                if kernel is not None and getattr(captain, "cosmic_alignment", 0.0) < 0 and amt > 0:
                    total += self.black_market(kernel, captain, cur, amt)
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
    def pool_holdings(self) -> Dict[str, Fraction]:
        """Every pool's reserves by money, exact - never cut to whole units."""
        out: Dict[str, Fraction] = {self.hub: Fraction(0)} if self.hub is not None else {}
        for cur, p in self.pools.items():
            out[self.hub] += exact(p["sol"])
            out[cur] = out.get(cur, Fraction(0)) + exact(p["local"])
        for p in getattr(self, "cross_pools", {}).values():
            out[p["ca"]] = out.get(p["ca"], Fraction(0)) + exact(p["a"])
            out[p["cb"]] = out.get(p["cb"], Fraction(0)) + exact(p["b"])
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {"hub": self.hub, "pools": {c: {k: str(v) for k, v in p.items()} for c, p in self.pools.items()},
                "volume_sol": dict(self.volume_sol), "fees_collected": dict(self.fees_collected),
                "fees": dict(self.fees),
                "cross_pools": {k: dict(p, a=str(p["a"]), b=str(p["b"])) for k, p in self.cross_pools.items()},
                "cross_volume": dict(self.cross_volume),
                "unsettled": {c: int(v) for c, v in (getattr(self, "unsettled", None) or {}).items()}}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FXMarket":
        fx = cls()
        fx.hub = data.get("hub", LEGACY_HUB)  # a save from before the hub was data: the settled board's unit
        if "pools" in data:
            fx.pools = {}                     # exactly the pools saved (a founding universe may have none yet)
        for c, p in data.get("pools", {}).items():
            fx.pools[c] = {"sol": exact(p["sol"]), "local": exact(p["local"])}
        fx.volume_sol.update({c: float(v) for c, v in data.get("volume_sol", {}).items()})
        fx.fees_collected.update({c: float(v) for c, v in data.get("fees_collected", {}).items()})
        fx.fees.update({c: float(v) for c, v in data.get("fees", {}).items()})
        if "cross_pools" in data:
            fx.cross_pools = {k: {"ca": p["ca"], "cb": p["cb"], "a": exact(p["a"]), "b": exact(p["b"])}
                              for k, p in data["cross_pools"].items()}
        else:
            fx.cross_pools = {}   # a pre-Galactic-ISSE save: no cross pairs appear out of nowhere
        fx.cross_volume = {k: float(v) for k, v in data.get("cross_volume", {}).items()}
        fx.unsettled = {c: int(v) for c, v in data.get("unsettled", {}).items()}
        return fx


# ---------------------------------------------------------------------- wallets
def balance(captain: Any, cur: str) -> int:
    return int(captain.credits) if cur == hub() else int(captain.fx_wallet.get(cur, 0))


def credit(captain: Any, cur: str, amount: int) -> None:
    if amount <= 0:
        return
    if cur == hub():
        captain.credits += amount
    else:
        captain.fx_wallet[cur] = captain.fx_wallet.get(cur, 0) + amount


def debit(captain: Any, cur: str, amount: int) -> None:
    if amount <= 0:
        return
    if cur == hub():
        captain.credits -= amount
    else:
        captain.fx_wallet[cur] = captain.fx_wallet.get(cur, 0) - amount
        if captain.fx_wallet[cur] == 0:
            captain.fx_wallet.pop(cur, None)


def net_worth(captain: Any, market: Optional["FXMarket"] = None) -> Dict[str, float]:
    """What a captain holds, in the reserve currency (SOL): its SOL, every regional balance at the ISSE's mid rate,
    and the cargo in its holds at what it paid (cost basis, kept in SOL)."""
    m = market or ACTIVE_FX
    wallets = {cur: (m.to_sol_value(cur, amt) if m is not None else 0.0)
               for cur, amt in (captain.fx_wallet or {}).items() if amt}
    cargo = getattr(getattr(captain, "ship", None), "cargo", None)
    goods = 0.0
    if cargo is not None:
        for key, basis in (getattr(cargo, "cost_basis", None) or {}).items():
            if basis and not str(key).endswith("_sol"):
                goods += float(basis) * float(cargo.held(key.upper()) if hasattr(cargo, "held") else 0)
    total = float(captain.credits) + sum(wallets.values()) + goods
    return {"sol": float(captain.credits), "wallets": {c: round(v, 1) for c, v in wallets.items()},
            "cargo": round(goods, 1), "total": round(total, 1)}


@contextmanager
def settle_in(captain: Any, cur: str):
    """
    Temporarily presents the captain's balance in ``cur`` as ``captain.credits`` so
    single-currency trade code settles in the port's local money.
    """
    if cur == hub():
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
