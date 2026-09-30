"""
Xylarium: Money ledger.

The economy is closed: money may only enter circulation through *declared* faucets
(colony production taxed into vaults, credit creation by lenders, discovery rewards,
new charters, genesis of newly charted clusters) and leave through declared or
implicit sinks (consumption of NPC goods & services: shipyards, upkeep, fees).
Every faucet calls ``mint``; the playtest harness and the conservation tests assert
that the money supply never grows by more than the declared mints.
"""

from collections import Counter
from typing import Any, Dict, Optional


class MoneyLedger:
    def __init__(self) -> None:
        self.minted: Counter = Counter()   # (source, currency) -> amount
        self.burned: Counter = Counter()

    def mint(self, source: str, amount: int, currency: str = "SOL") -> None:
        if amount > 0:
            self.minted[(source, currency)] += int(amount)

    def burn(self, sink: str, amount: int, currency: str = "SOL") -> None:
        if amount > 0:
            self.burned[(sink, currency)] += int(amount)

    def totals(self, currency: str) -> Dict[str, int]:
        return {
            "minted": sum(v for (s, c), v in self.minted.items() if c == currency),
            "burned": sum(v for (s, c), v in self.burned.items() if c == currency),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "minted": [[s, c, v] for (s, c), v in self.minted.items()],
            "burned": [[s, c, v] for (s, c), v in self.burned.items()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MoneyLedger":
        led = cls()
        for s, c, v in data.get("minted", []):
            led.minted[(s, c)] = int(v)
        for s, c, v in data.get("burned", []):
            led.burned[(s, c)] = int(v)
        return led


ACTIVE_LEDGER: Optional[MoneyLedger] = None


def set_active(ledger: Optional[MoneyLedger]) -> None:
    global ACTIVE_LEDGER
    ACTIVE_LEDGER = ledger


def mint(source: str, amount: int, currency: str = "SOL") -> None:
    if ACTIVE_LEDGER is not None:
        ACTIVE_LEDGER.mint(source, amount, currency)


def burn(sink: str, amount: int, currency: str = "SOL") -> None:
    if ACTIVE_LEDGER is not None:
        ACTIVE_LEDGER.burn(sink, amount, currency)


def money_supply(kernel: Any) -> Dict[str, Dict[str, int]]:
    """
    Every money stock in the universe, per currency:
      captains (SOL credits + fx wallets), colony vaults, company treasuries (SOL),
      starport treasuries, the Federal Reserve (SOL, incl. bounty escrow),
      freight/extraction escrow, and ISSE FX pool reserves.
    Transfers between stocks leave these totals unchanged; changes are mints or burns.
    """
    supply: Dict[str, Dict[str, int]] = {}

    def add(cur: str, stock: str, amount: float) -> None:
        bucket = supply.setdefault(cur, {})
        bucket[stock] = bucket.get(stock, 0) + int(amount)

    for c in kernel.captains.values():
        add("SOL", "captains", c.credits)
        for cur, amt in getattr(c, "fx_wallet", {}).items():
            add(cur, "captains", amt)
    for s in kernel.sectors.values():
        for p in s.planets:
            add(getattr(p, "currency", "SOL"), "planet_vaults", p.treasury)
            ruins = getattr(p, "ruins", None)
            if ruins and ruins.get("hoard"):
                add(ruins.get("hoard_currency") or "SOL", "buried_hoards", ruins["hoard"])
        if s.port is not None:
            add(getattr(s.port, "currency", "SOL"), "port_treasuries", getattr(s.port, "treasury", 0))
    mm = kernel.market_manager
    for comp in mm.companies.values():
        add("SOL", "company_treasuries", getattr(comp, "treasury", 0))
    for c in mm.contracts.values():
        if c.status in ("OPEN", "IN_TRANSIT") and getattr(c, "escrow_amount", 0):
            add(getattr(c, "currency", "SOL"), "contract_escrow", c.escrow_amount)
    fed = getattr(kernel, "federal_reserve", None)
    if fed is not None:
        add("SOL", "federal_reserve", fed.total_holdings)
    fxm = getattr(kernel, "fx_market", None)
    if fxm is not None:
        for cur, amt in fxm.pool_holdings().items():
            add(cur, "fx_pools", amt)
    banking = getattr(kernel, "banking", None)
    if banking is not None:
        for cur, bank in banking.banks.items():
            if cur != "SOL" and bank.reserves:          # SOL's central bank is the Federal Reserve (counted above)
                add(cur, "central_banks", bank.reserves)
    factions = getattr(kernel, "factions", None)
    if factions is not None:
        for f in factions.factions.values():
            for cur, amt in f.vault.items():
                add(cur, "faction_vaults", amt)
    for cur, bucket in supply.items():
        bucket["total"] = sum(v for k, v in bucket.items() if k != "total")
    return supply


def supply_in_sol(kernel: Any, supply: Optional[Dict[str, Dict[str, int]]] = None) -> float:
    """Aggregate money supply valued in SOL at live ISSE mid rates."""
    supply = supply or money_supply(kernel)
    fxm = getattr(kernel, "fx_market", None)
    total = 0.0
    for cur, bucket in supply.items():
        total += bucket["total"] if (cur == "SOL" or fxm is None) else fxm.to_sol_value(cur, bucket["total"])
    return total


class MonetaryPolicy:
    """
    Regional monetary authorities (one per currency) run a fiscal rule each fiscal quarter:
    the money-supply target is the genesis supply plus declared new territory. When supply
    runs above target - or a regional currency trades weak against its genesis level - public
    services absorb more of colony tax (austerity withdraws money); below target they ease.
    The resulting factor scales colony services, the declared sink paired with colony tax.
    """

    def __init__(self) -> None:
        self.targets: Dict[str, float] = {}
        self.factors: Dict[str, float] = {}
        self.history: Dict[str, list] = {}

    def factor(self, currency: str) -> float:
        return self.factors.get(currency, 1.0)

    def update(self, kernel: Any) -> None:
        from xylarium.config import POLICY_SUPPLY_ELASTICITY, POLICY_FX_ELASTICITY, POLICY_FACTOR_BOUNDS
        supply = money_supply(kernel)
        territory: Dict[str, int] = {}
        for (src, cur), v in kernel.ledger.minted.items():
            if src in ("cluster_genesis", "ghost_sector_genesis"):
                territory[cur] = territory.get(cur, 0) + v
        fxm = getattr(kernel, "fx_market", None)
        lo, hi = POLICY_FACTOR_BOUNDS
        for cur, bucket in supply.items():
            if cur not in self.targets:
                self.targets[cur] = float(bucket["total"])  # first reading = genesis supply
            target = self.targets[cur] + territory.get(cur, 0)
            ratio = bucket["total"] / max(1.0, target)
            factor = ratio ** POLICY_SUPPLY_ELASTICITY
            if fxm is not None and cur != "SOL":
                factor *= fxm.price_level_drift(cur) ** POLICY_FX_ELASTICITY
            factor = max(lo, min(hi, factor))
            self.factors[cur] = round(factor, 4)
            self.history.setdefault(cur, []).append(round(factor, 3))
            self.history[cur] = self.history[cur][-40:]

    def to_dict(self) -> Dict[str, Any]:
        return {"targets": dict(self.targets), "factors": dict(self.factors), "history": dict(self.history)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonetaryPolicy":
        mp = cls()
        mp.targets = {k: float(v) for k, v in data.get("targets", {}).items()}
        mp.factors = {k: float(v) for k, v in data.get("factors", {}).items()}
        mp.history = {k: list(v) for k, v in data.get("history", {}).items()}
        return mp


ACTIVE_POLICY: Optional[MonetaryPolicy] = None


def set_active_policy(policy: Optional[MonetaryPolicy]) -> None:
    global ACTIVE_POLICY
    ACTIVE_POLICY = policy


def policy_factor(currency: str) -> float:
    return ACTIVE_POLICY.factor(currency) if ACTIVE_POLICY is not None else 1.0
