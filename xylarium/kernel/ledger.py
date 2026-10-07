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
from typing import Any, Dict, List, Optional


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
            if getattr(p, "diaspora_escrow", 0):
                add(getattr(p, "currency", "SOL"), "diaspora_escrow", p.diaspora_escrow)
            if getattr(p, "household_purse", 0):
                add(getattr(p, "currency", "SOL"), "households", p.household_purse)
            owed = (getattr(p, "society", None) or {}).get("tribute_escrow", 0)
            if owed:
                add(getattr(p, "currency", "SOL"), "tribute_escrow", owed)
            ruins = getattr(p, "ruins", None)
            if ruins and ruins.get("hoard"):
                add(ruins.get("hoard_currency") or "SOL", "buried_hoards", ruins["hoard"])
        if s.port is not None:
            add(getattr(s.port, "currency", "SOL"), "port_treasuries", getattr(s.port, "treasury", 0))
    mm = kernel.market_manager
    for comp in mm.companies.values():
        add("SOL", "company_treasuries", getattr(comp, "treasury", 0))
        if getattr(comp, "home_cash", 0):
            add(comp.home_currency or "SOL", "company_treasuries", comp.home_cash)
    for c in mm.contracts.values():
        if c.status in ("OPEN", "IN_TRANSIT") and getattr(c, "escrow_amount", 0):
            add(getattr(c, "currency", "SOL"), "contract_escrow", c.escrow_amount)
    from xylarium.kernel import tourism
    for ch in (tourism.charters(kernel) if hasattr(kernel, "state") else {}).values():
        if ch["status"] in ("OPEN", "IN_TRANSIT"):
            add(ch["currency"], "contract_escrow", ch["escrow"])
    fed = getattr(kernel, "federal_reserve", None)
    if fed is not None:
        add("SOL", "federal_reserve", fed.total_holdings)
    fxm = getattr(kernel, "fx_market", None)
    if fxm is not None:
        for cur, amt in fxm.pool_holdings().items():
            add(cur, "fx_pools", amt)
        for cur, amt in (getattr(fxm, "unsettled", None) or {}).items():
            add(cur, "fx_unsettled", amt)               # payments the house holds until a market lists their money
    from xylarium.kernel import exchanges
    for cur, amt in exchanges.holdings(kernel).items():
        add(cur, "local_exchanges", amt)
    banking = getattr(kernel, "banking", None)
    if banking is not None:
        for cur, bank in banking.banks.items():
            if cur != "SOL" and bank.reserves:          # SOL's central bank is the Federal Reserve (counted above)
                add(cur, "central_banks", bank.reserves)
            for other, amt in getattr(bank, "fx_reserves", {}).items():
                if amt:
                    add(other, "central_banks", amt)
    from xylarium.kernel import endowments
    held = endowments.holdings(kernel)
    if held:
        add("SOL", "steward_funds", held)
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


def expected_output(kernel: Any) -> Dict[str, float]:
    """Each region's annual real output at genesis, from its worlds' physics (harvest + ore, base prices, local)."""
    from xylarium.config import COMMODITY_CONFIG, PRICE_LEVEL
    from xylarium.kernel import biosphere
    org, ore = COMMODITY_CONFIG["ORGANICS"]["base_price"], COMMODITY_CONFIG["ORE"]["base_price"]
    out: Dict[str, float] = {}
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population <= 0 or getattr(p, "natives", None):
                continue
            k = biosphere.carrying_capacity(kernel, p)
            per_cycle = min(p.population * 5 // 4, k) / 1000.0 * org + max(1, int(p.population * 0.02)) * ore
            out[p.currency] = out.get(p.currency, 0.0) + per_cycle * 100 * PRICE_LEVEL.get(p.currency, 1.0)
    return out


def endow_exchange_depth(kernel: Any) -> None:
    """
    Genesis: the federation exchanges hold liquidity in proportion to the real economies they serve. The ISSE's
    SOL is shared among the regional pools by each region's output (in SOL value); each pool's local side is set
    at the currency's defined price level. The SOL is conserved; the local liquidity is a declared endowment.
    """
    from xylarium.config import PRICE_LEVEL
    fxm = getattr(kernel, "fx_market", None)
    if fxm is None or not fxm.pools:
        return
    y = expected_output(kernel)
    y_sol = {cur: y.get(cur, 0.0) / PRICE_LEVEL.get(cur, 1.0) for cur in fxm.pools}
    mean = sum(y_sol.values()) / len(y_sol) if y_sol else 0.0
    weights = {cur: max(v, mean / 4) for cur, v in y_sol.items()}      # even a quiet region needs a market
    total_w = sum(weights.values()) or 1.0
    sol_total = sum(p["sol"] for p in fxm.pools.values())
    assigned = 0
    curs = sorted(fxm.pools)
    for i, cur in enumerate(curs):
        pool = fxm.pools[cur]
        sol = int(sol_total * weights[cur] / total_w) if i < len(curs) - 1 else int(sol_total - assigned)
        assigned += sol
        local = int(sol * PRICE_LEVEL.get(cur, 1.0))
        d_local = local - int(pool["local"])
        pool["sol"], pool["local"] = sol, local
        if d_local > 0:
            mint("exchange_endowment", d_local, cur)
        elif d_local < 0:
            burn("exchange_endowment", -d_local, cur)
    d_sol = int(sol_total) - assigned
    if d_sol:
        (burn if d_sol > 0 else mint)("exchange_endowment", abs(d_sol), "SOL")


class MonetaryPolicy:
    """
    Regional monetary authorities, one per currency, keep the quantity equation M V = P Y.

      * Y is real output: the value (at base prices and the region's genesis price level) of what the
        region's worlds harvest and mine, summed over the last standard year (four seasons).
      * V is not chosen: it is measured once, from the genesis money supply M0 and the first full year's
        output Y0 (V = P Y0 / M0). With V and P held, the money the economy needs is M* = M0 x Y / Y0 -
        money grows exactly as the real economy grows, and a stable price level follows.
      * Each season the authority closes a quarter of the gap (M* - M) - the whole gap over one year - by
        setting how much of the governments' tax public services withdraw (a declared burn) or, when
        colony earnings alone cannot supply what the economy needs, by a fiscal transfer to households
        (a declared mint). No elasticities, no bounds: the clock sets the pace, output sets the target.
    """

    def __init__(self) -> None:
        self.targets: Dict[str, float] = {}      # M0: genesis supply per currency
        self.output0: Dict[str, float] = {}      # Y0: first full year's output
        self.current: Dict[str, float] = {}      # this season's M* (reporting)
        self.factors: Dict[str, float] = {}      # withdraw share: services / government tax
        self.history: Dict[str, list] = {}
        self.output_q: Dict[str, float] = {}     # output accumulating this season
        self.output_seasons: Dict[str, list] = {}  # the last four seasons' output
        self.earnings_q: Dict[str, float] = {}   # colony earnings minted this season
        self.gov_q: Dict[str, float] = {}        # of which the governments' share
        self.transfers: Dict[str, int] = {}      # cumulative fiscal transfers (reporting)
        self.services_q: Dict[str, float] = {}   # services actually withdrawn this season
        self.transfer_q: Dict[str, float] = {}   # transfer made at the start of this season
        self.last_supply: Dict[str, float] = {}  # supply at the last season's close
        self.output_total: Dict[str, float] = {}     # cumulative real output (reporting)
        self.earnings_total: Dict[str, float] = {}   # cumulative colony earnings: GDP by the income approach

    def factor(self, currency: str) -> float:
        return self.factors.get(currency, 1.0)

    def record_output(self, currency: str, value: float) -> None:
        self.output_q[currency] = self.output_q.get(currency, 0.0) + value
        self.output_total[currency] = self.output_total.get(currency, 0.0) + value

    def record_earnings(self, currency: str, total: float, government: float) -> None:
        self.earnings_q[currency] = self.earnings_q.get(currency, 0.0) + total
        self.earnings_total[currency] = self.earnings_total.get(currency, 0.0) + total
        self.gov_q[currency] = self.gov_q.get(currency, 0.0) + government

    def record_income(self, currency: str, amount: float) -> None:
        """Other factor income the worlds earn (export sales, port payroll and purchases): reporting only."""
        self.earnings_total[currency] = self.earnings_total.get(currency, 0.0) + amount

    def record_services(self, currency: str, amount: float) -> None:
        self.services_q[currency] = self.services_q.get(currency, 0.0) + amount

    def annual_output(self, currency: str) -> float:
        seasons = self.output_seasons.get(currency, [])
        return sum(seasons) if len(seasons) >= 4 else 0.0

    def target(self, currency: str, supply: float) -> float:
        m0 = self.targets.get(currency, supply)
        y0, y = self.output0.get(currency), self.annual_output(currency)
        return m0 * y / y0 if (y0 and y) else m0

    def update(self, kernel: Any) -> None:
        supply = money_supply(kernel)
        from xylarium.kernel import institutions
        for cur, bucket in supply.items():
            if not institutions.issued(kernel, cur):
                continue                                    # no one has founded this money yet
            m = float(bucket["total"])
            if cur not in self.targets:
                self.targets[cur] = m                       # first reading = genesis supply M0
            # close the season's output books
            seasons = self.output_seasons.setdefault(cur, [])
            if cur in self.output_q or seasons:
                seasons.append(self.output_q.get(cur, 0.0))
                del seasons[:-4]
            if cur not in self.output0 and len(seasons) >= 4 and self.annual_output(cur) > 0:
                self.output0[cur] = self.annual_output(cur)  # first full year: V is measured
            target = self.target(cur, m)
            self.current[cur] = round(target)
            earned, gov = self.earnings_q.get(cur, 0.0), self.gov_q.get(cur, 0.0)
            # Everything else that moved this money last season (faction spending, tithes, other declared
            # burns and mints) is measured, not guessed: the season's change minus the colony circuit's own
            last_m = self.last_supply.get(cur)
            colony_net = earned - self.services_q.get(cur, 0.0) + self.transfer_q.get(cur, 0.0)
            other = (m - last_m) - colony_net if last_m is not None else 0.0
            self.last_supply[cur] = m
            from xylarium.kernel import regimes
            self.transfer_q[cur] = 0.0
            if not regimes.steers(kernel, cur):
                # this polity chose not to steer its money: services keep the share they had when it chose
                frozen = regimes.stats(kernel).get("frozen_factor", {}).get(cur, self.factors.get(cur, 1.0))
                self.factors[cur] = frozen
                self.history.setdefault(cur, []).append(round(frozen, 3))
                self.history[cur] = self.history[cur][-40:]
                continue
            gap = (target - m) / 4.0                        # a quarter of the gap per season
            needed = gap - other                            # the colony circuit must also offset the rest
            withdraw = earned - needed                      # what services must burn for that net injection
            if withdraw >= 0:
                self.factors[cur] = round(withdraw / gov, 4) if gov > 0 else 1.0
            else:
                self.factors[cur] = 0.0
                self._transfer(kernel, cur, int(-withdraw))
            self.history.setdefault(cur, []).append(round(self.factors[cur], 3))
            self.history[cur] = self.history[cur][-40:]
        self.output_q, self.earnings_q, self.gov_q, self.services_q = {}, {}, {}, {}

    def _transfer(self, kernel: Any, cur: str, amount: int) -> None:
        """Fiscal transfer: new money reaches households by population (declared mint)."""
        worlds = [p for s in kernel.sectors.values() for p in s.planets
                  if p.population > 0 and p.currency == cur and not getattr(p, "natives", None)]
        people = sum(p.population for p in worlds)
        if amount <= 0 or people <= 0:
            return
        paid = 0
        for p in worlds:
            share = amount * p.population // people
            p.household_purse += share
            paid += share
        if paid:
            mint("fiscal_transfer", paid, cur)
            self.transfers[cur] = self.transfers.get(cur, 0) + paid
            self.transfer_q[cur] = self.transfer_q.get(cur, 0.0) + paid

    def to_dict(self) -> Dict[str, Any]:
        return {"targets": dict(self.targets), "output0": dict(self.output0), "factors": dict(self.factors),
                "history": dict(self.history), "output_q": dict(self.output_q),
                "output_seasons": {k: list(v) for k, v in self.output_seasons.items()},
                "earnings_q": dict(self.earnings_q), "gov_q": dict(self.gov_q), "transfers": dict(self.transfers),
                "services_q": dict(self.services_q), "transfer_q": dict(self.transfer_q),
                "last_supply": dict(self.last_supply),
                "output_total": dict(self.output_total), "earnings_total": dict(self.earnings_total)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonetaryPolicy":
        mp = cls()
        mp.targets = {k: float(v) for k, v in data.get("targets", {}).items()}
        mp.output0 = {k: float(v) for k, v in data.get("output0", {}).items()}
        mp.factors = {k: float(v) for k, v in data.get("factors", {}).items()}
        mp.history = {k: list(v) for k, v in data.get("history", {}).items()}
        mp.output_q = {k: float(v) for k, v in data.get("output_q", {}).items()}
        mp.output_seasons = {k: [float(x) for x in v] for k, v in data.get("output_seasons", {}).items()}
        mp.earnings_q = {k: float(v) for k, v in data.get("earnings_q", {}).items()}
        mp.gov_q = {k: float(v) for k, v in data.get("gov_q", {}).items()}
        mp.transfers = {k: int(v) for k, v in data.get("transfers", {}).items()}
        mp.services_q = {k: float(v) for k, v in data.get("services_q", {}).items()}
        mp.transfer_q = {k: float(v) for k, v in data.get("transfer_q", {}).items()}
        mp.last_supply = {k: float(v) for k, v in data.get("last_supply", {}).items()}
        mp.output_total = {k: float(v) for k, v in data.get("output_total", {}).items()}
        mp.earnings_total = {k: float(v) for k, v in data.get("earnings_total", {}).items()}
        return mp


ACTIVE_POLICY: Optional[MonetaryPolicy] = None
ACTIVE_KERNEL: Any = None


def set_active_kernel(kernel: Any) -> None:
    global ACTIVE_KERNEL
    ACTIVE_KERNEL = kernel


def active_kernel() -> Any:
    return ACTIVE_KERNEL


def pay_service(amount_sol: int, sector_id: Optional[int] = None, institution: Optional[str] = None) -> None:
    """
    Nothing is thrown away: SOL a captain or company spends on a service reaches whoever provides it - the
    starport of the sector where it was bought (cleared into local money), Sol Stardock when bought where
    there is none, or - for institutions (``institution`` given: lobbying, jump gates, salvage) - the
    Federal Reserve's treasury.
    """
    kernel = ACTIVE_KERNEL
    if amount_sol <= 0 or kernel is None:
        return
    if institution is not None and getattr(kernel, "federal_reserve", None) is not None:
        kernel.federal_reserve.receive(int(amount_sol), institution)
        return
    sec = kernel.sectors.get(sector_id) if sector_id is not None else None
    port = sec.port if (sec is not None and sec.port is not None) else kernel.sectors[1].port
    if port is None:
        kernel.federal_reserve.receive(int(amount_sol), "services")
        return
    from xylarium.kernel import fx
    if port.currency != "SOL" and fx.ACTIVE_FX is not None:
        port.treasury += fx.ACTIVE_FX.swap_sol_to(port.currency, int(amount_sol))
    else:
        port.treasury += int(amount_sol)


def set_active_policy(policy: Optional[MonetaryPolicy]) -> None:
    global ACTIVE_POLICY
    ACTIVE_POLICY = policy


def policy_factor(currency: str) -> float:
    return ACTIVE_POLICY.factor(currency) if ACTIVE_POLICY is not None else 1.0
