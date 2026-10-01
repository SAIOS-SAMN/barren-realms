"""
Xylarium: federations, central banks, and the Galactic Clearing Union.

There is no single reserve currency. Each federation of solar systems issues its own money
and runs its own central bank; above them sits a clearing union, not a bigger bank.

Federations (one per currency)
------------------------------
  SOL   Terran Federation      - the Federal Reserve is its central bank
  FRN   Frontier Compact       - the Compact Reserve Bank
  THR   Aurelian Imperium      - the Imperial Treasury
  VOID  Deep Void Syndicate    - the Black Bourse

Each central bank has a real balance sheet (reserves in its own money, loans outstanding),
a policy rate, and a governor: an AI delegate with a persona and a cosmic alignment. Light
governors lend fairly and cap interest so a port can't be buried; Dark governors charge a
usury spread and let debts compound.

What a central bank does each fiscal quarter
--------------------------------------------
  1. Keeps its currency orderly at the ISSE. If its exchange pool is stuffed with its money
     (captains dumping it: the currency is weak), the bank buys it back into reserves; if the
     pool runs short, it sells reserves into the pool. Every intervention is booked in the
     clearing union as a STAMP entry against the ISSE.
  2. Lends reserves to starports running dry (frontier outposts included), at its rate, and
     collects repayment from their later surpluses. Priced credit, not grants.

The Galactic Clearing Union
---------------------------
STAMP is the union's unit of account (after netstratum's 32_STAMP_MARKET): a sealed claim
between central banks and exchanges, never circulating money. Every entry is double-entry,
so the union's accounts always sum to zero - a conservation law the harness checks. Following
Keynes's clearing-union design, a bank's STAMP position feeds its lending rate: a federation
that keeps repatriating its currency (a persistent deficit) lends dearer. The union's council
of governors reviews its rules each era; a Light majority softens the deficit penalty.

Money here only moves between existing stocks (bank reserves, ISSE pools, port treasuries).
Founding reserves are set at genesis, before the money supply's baseline reading.
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import (
    PRICE_LEVEL,
    FX_POOL_SEED,
    PORT_START_TREASURY,
    STARDOCK_START_TREASURY,
    CENTRAL_BANK_FOUNDING_RESERVES,
    CENTRAL_BANK_RESERVE_FLOOR,
    CLEARING_BAND,
    CLEARING_INTERVENTION_RATE,
    POLICY_RATE_BASE,
    POLICY_RATE_DEFICIT_SLOPE,
    GOVERNOR_DARK_SPREAD,
    GOVERNOR_LIGHT_DISCOUNT,
    CREDIT_TRIGGER_SHARE,
    CREDIT_LINE_SHARE,
    CREDIT_CAP_SHARE,
    CREDIT_REPAY_SHARE,
    CREDIT_LIGHT_INTEREST_CAP,
    CREDIT_WRITE_OFF_MULTIPLE,
    CREDIT_INCOME_QUARTERS,
    CREDIT_DARK_PRUDENCE,
    CENTRAL_BANK_RESERVE_CEILING,
    CENTRAL_BANK_OMO_RATE,
)

FEDERATIONS = {
    "SOL": {"federation": "Terran Federation", "bank": "Federal Reserve of the Terran Federation", "authority": "FEDERATION",
            "governor": "Chair Amaranth Okoye"},
    "FRN": {"federation": "Frontier Compact", "bank": "Compact Reserve Bank", "authority": "COMPACT",
            "governor": "Governor Silas Venn"},
    "THR": {"federation": "Aurelian Imperium", "bank": "Imperial Treasury of the Throne", "authority": "IMPERIUM",
            "governor": "Lord Exchequer Castor Vale"},
    "VOID": {"federation": "Deep Void Syndicate", "bank": "Black Bourse", "authority": "NONE",
             "governor": "The Broker Called Nine"},
}
EXCHANGES = {
    "SOL": "ISSE Sol Central", "FRN": "ISSE Frontier Bourse", "THR": "ISSE Throne Exchange",
    "VOID": "ISSE Void Market", "GALACTIC": "Galactic ISSE",
}
ISSE_MEMBER = "ISSE"


@dataclass
class CentralBank:
    currency: str
    name: str
    federation: str
    governor: str
    alignment: float
    reserves: int = 0                               # own-currency reserves (SOL's live in the Federal Reserve)
    loans: Dict[str, Dict[str, int]] = field(default_factory=dict)   # borrower id -> {"principal", "debt"}
    policy_rate: float = POLICY_RATE_BASE           # per fiscal quarter
    stats: Dict[str, int] = field(default_factory=dict)
    paid_rate: float = 0.0                          # what deposits actually earned last quarter
    fx_reserves: Dict[str, int] = field(default_factory=dict)   # other moneys it holds (SOL lent by a neighbour...)
    warehouse: Dict[str, int] = field(default_factory=dict)     # commodity reserves behind a reserve-backed money

    def bump(self, key: str, amount: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + int(amount)

    @property
    def loans_outstanding(self) -> int:
        return sum(l["debt"] for l in self.loans.values())

    def to_dict(self) -> Dict[str, Any]:
        return {"currency": self.currency, "name": self.name, "federation": self.federation,
                "governor": self.governor, "alignment": self.alignment, "reserves": self.reserves,
                "loans": {k: dict(v) for k, v in self.loans.items()}, "policy_rate": self.policy_rate,
                "stats": dict(self.stats), "paid_rate": self.paid_rate, "fx_reserves": dict(self.fx_reserves),
                "warehouse": dict(self.warehouse)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CentralBank":
        b = cls(currency=d["currency"], name=d["name"], federation=d["federation"], governor=d["governor"],
                alignment=float(d["alignment"]), reserves=int(d.get("reserves", 0)),
                policy_rate=float(d.get("policy_rate", POLICY_RATE_BASE)),
                paid_rate=float(d.get("paid_rate", 0.0)),
                fx_reserves={k: int(v) for k, v in d.get("fx_reserves", {}).items()},
                warehouse={k: int(v) for k, v in d.get("warehouse", {}).items()})
        b.loans = {k: {kk: int(vv) for kk, vv in v.items()} for k, v in d.get("loans", {}).items()}
        b.stats = {k: int(v) for k, v in d.get("stats", {}).items()}
        return b


class BankingSystem:
    def __init__(self) -> None:
        self.banks: Dict[str, CentralBank] = {}
        self.stamp: Dict[str, float] = {}           # clearing-union accounts (sum to zero)
        self.deficit_slope: float = POLICY_RATE_DEFICIT_SLOPE
        self.last_council_cycle: int = 0
        self.council_history: List[List[Any]] = []

    # ------------------------------------------------------------------ genesis
    def found(self, kernel: Any) -> None:
        """Seats each federation's central bank with founding reserves (genesis, before the money baseline)."""
        from xylarium.kernel.alignment import genesis_value
        from xylarium.config import AUTHORITIES
        rng = random.Random(kernel.seed * 613 + 29)
        for cur, spec in FEDERATIONS.items():
            if cur != "SOL" and cur not in kernel.fx_market.pools:
                continue
            base_align = AUTHORITIES.get(spec["authority"], {}).get("alignment", 0.0)
            bank = CentralBank(
                currency=cur, name=spec["bank"], federation=spec["federation"], governor=spec["governor"],
                alignment=round(max(-1.0, min(1.0, base_align + genesis_value(rng) * 0.5)), 3),
                reserves=0 if cur == "SOL" else int(CENTRAL_BANK_FOUNDING_RESERVES * PRICE_LEVEL.get(cur, 1.0)),
            )
            self.banks[cur] = bank
            self.stamp[cur] = 0.0
        self.stamp[ISSE_MEMBER] = 0.0

    # ------------------------------------------------------------------ reserves (SOL = the Federal Reserve)
    def reserves(self, kernel: Any, bank: CentralBank) -> int:
        return kernel.federal_reserve.treasury if bank.currency == "SOL" else bank.reserves

    def _adjust(self, kernel: Any, bank: CentralBank, delta: int) -> None:
        if bank.currency == "SOL":
            kernel.federal_reserve.treasury += delta
        else:
            bank.reserves += delta

    def reserve_floor(self, bank: CentralBank) -> int:
        return int(CENTRAL_BANK_RESERVE_FLOOR * PRICE_LEVEL.get(bank.currency, 1.0))

    # ------------------------------------------------------------------ clearing
    def _book(self, debtor: str, creditor: str, stamp_value: float) -> None:
        """Double-entry STAMP claim: ``debtor`` owes ``creditor``. The union's accounts always net to zero."""
        self.stamp[debtor] = self.stamp.get(debtor, 0.0) - stamp_value
        self.stamp[creditor] = self.stamp.get(creditor, 0.0) + stamp_value

    @staticmethod
    def stamp_value(cur: str, amount: float) -> float:
        """STAMP is valued at genesis parity: one STAMP = one genesis SOL of purchasing power."""
        return amount / PRICE_LEVEL.get(cur, 1.0)

    def _intervene(self, kernel: Any, bank: CentralBank, receipts: Any) -> None:
        """Keeps the bank's money orderly in the ISSE pools (its local side, or - for SOL - the SOL side)."""
        fxm = kernel.fx_market
        pools = ([(cur, "sol", FX_POOL_SEED[cur][0]) for cur in fxm.pools if cur in FX_POOL_SEED]
                 if bank.currency == "SOL" else [(bank.currency, "local", FX_POOL_SEED[bank.currency][1])])
        for pool_cur, side, genesis in pools:
            pool = fxm.pools.get(pool_cur)
            if pool is None:
                continue
            held = pool[side]
            if held > genesis * CLEARING_BAND:
                # The pool is stuffed with our money: buy it back into reserves (the currency firms)
                amount = int((held - genesis * CLEARING_BAND) * CLEARING_INTERVENTION_RATE)
                if amount <= 0:
                    continue
                pool[side] -= amount
                self._adjust(kernel, bank, amount)
                value = self.stamp_value(bank.currency, amount)
                self._book(bank.currency, ISSE_MEMBER, value)
                bank.bump("absorbed", amount)
                receipts.add(kernel, "clearing_absorb", EXCHANGES.get(pool_cur, ISSE_MEMBER), bank.name,
                             amount, bank.currency, f"{pool_cur} pool {side} side above band")
            elif held < genesis / CLEARING_BAND:
                # The pool is short of our money: sell reserves into it
                amount = int((genesis / CLEARING_BAND - held) * CLEARING_INTERVENTION_RATE)
                amount = min(amount, max(0, self.reserves(kernel, bank) - self.reserve_floor(bank)))
                if amount <= 0:
                    continue
                pool[side] += amount
                self._adjust(kernel, bank, -amount)
                value = self.stamp_value(bank.currency, amount)
                self._book(ISSE_MEMBER, bank.currency, value)
                bank.bump("injected", amount)
                receipts.add(kernel, "clearing_inject", bank.name, EXCHANGES.get(pool_cur, ISSE_MEMBER),
                             amount, bank.currency, f"{pool_cur} pool {side} side below band")

    # ------------------------------------------------------------------ deposits
    def _deposit_interest(self, kernel: Any, bank: CentralBank) -> None:
        """A regional central bank pays its policy rate on the balances captains hold in its money, out of its
        reserves above the floor (pro rata when they fall short): a transfer, nothing minted. This is how a
        bank defends its currency - a high rate pays people to hold it."""
        if bank.currency == "SOL" or bank.policy_rate <= 0:
            return
        holders = [(c, c.fx_wallet.get(bank.currency, 0)) for c in kernel.captains.values()
                   if c.fx_wallet.get(bank.currency, 0) > 0]
        owed = sum(int(b * bank.policy_rate) for _, b in holders)
        can = max(0, bank.reserves - self.reserve_floor(bank))
        if owed <= 0 or can <= 0:
            return
        scale = min(1.0, can / owed)
        paid = 0
        for cap, bal in holders:
            amt = int(bal * bank.policy_rate * scale)
            if amt > 0:
                cap.fx_wallet[bank.currency] = bal + amt
                paid += amt
        bank.reserves -= paid
        bank.bump("deposit_interest", paid)
        bank.paid_rate = round(bank.policy_rate * scale, 5)

    def paid_rate(self, currency: str) -> float:
        """What holding this money actually earned last quarter (the policy rate, unless reserves fell short)."""
        bank = self.banks.get(currency)
        return float(getattr(bank, "paid_rate", 0.0) or 0.0) if bank is not None else 0.0

    # ------------------------------------------------------------------ credit
    def rate_for(self, bank: CentralBank) -> float:
        """Policy rate: base, plus the clearing union's deficit penalty, plus the governor's temperament."""
        position = self.stamp.get(bank.currency, 0.0)
        scale = CENTRAL_BANK_FOUNDING_RESERVES
        deficit_penalty = self.deficit_slope * max(0.0, -position) / scale
        rate = POLICY_RATE_BASE + deficit_penalty
        if bank.alignment <= -0.15:
            rate += GOVERNOR_DARK_SPREAD * (-bank.alignment)
        elif bank.alignment >= 0.15:
            rate = max(0.0, rate - GOVERNOR_LIGHT_DISCOUNT * bank.alignment)
        return round(rate, 5)

    def _credit(self, kernel: Any, bank: CentralBank, receipts: Any) -> None:
        from xylarium.kernel import regimes
        bank.policy_rate = regimes.rate(kernel, bank, self.rate_for(bank))
        if not regimes.lends(kernel, bank.currency):
            return
        for sec in kernel.sectors.values():
            port = sec.port
            if port is None or port.currency != bank.currency:
                continue
            key = f"port:{sec.id}"
            baseline = int((STARDOCK_START_TREASURY if sec.id == 1 else PORT_START_TREASURY)
                           * PRICE_LEVEL.get(bank.currency, 1.0))
            loan = bank.loans.get(key)
            # Interest accrues on what is owed; a Light governor caps it so no port is buried
            if loan:
                interest = int(loan["debt"] * bank.policy_rate)
                if bank.alignment >= 0.15:
                    interest = min(interest, max(0, int(loan["principal"] * (1 + CREDIT_LIGHT_INTEREST_CAP)) - loan["debt"]))
                loan["debt"] += max(0, interest)
                # Repay from surplus above the working baseline
                if port.treasury > baseline:
                    pay = min(loan["debt"], int((port.treasury - baseline) * CREDIT_REPAY_SHARE))
                    if pay > 0:
                        port.treasury -= pay
                        self._adjust(kernel, bank, pay)
                        loan["debt"] -= pay
                        repaid_principal = min(loan["principal"], pay)
                        loan["principal"] -= repaid_principal
                        bank.bump("repaid", pay)
                        receipts.add(kernel, "loan_repayment", port.name, bank.name, pay, bank.currency, key)
                if loan["debt"] <= 0:
                    bank.loans.pop(key, None)
                elif loan["debt"] > baseline * CREDIT_WRITE_OFF_MULTIPLE:
                    # Past saving: the bank writes the loan off (the money already moved; the claim dies)
                    bank.bump("written_off", loan["debt"])
                    receipts.add(kernel, "loan_write_off", bank.name, port.name, loan["debt"], bank.currency, key)
                    bank.loans.pop(key, None)
            # A port running dry draws on its federation's credit line - but only against the income its
            # region actually pays it: credit bridges a bad season, it doesn't bankroll a port with no economy
            if port.treasury < baseline * CREDIT_TRIGGER_SHARE:
                owed = bank.loans.get(key, {}).get("debt", 0)
                prudence = CREDIT_DARK_PRUDENCE if bank.alignment <= -0.15 else 1.0
                capacity = port.regional_income * CREDIT_INCOME_QUARTERS * prudence
                room = int(min(baseline * CREDIT_CAP_SHARE, capacity)) - owed
                lend = min(int(baseline * CREDIT_LINE_SHARE), room,
                           max(0, self.reserves(kernel, bank) - self.reserve_floor(bank)))
                if lend > 0:
                    port.treasury += lend
                    self._adjust(kernel, bank, -lend)
                    row = bank.loans.setdefault(key, {"principal": 0, "debt": 0})
                    row["principal"] += lend
                    row["debt"] += lend
                    bank.bump("lent", lend)
                    receipts.add(kernel, "loan_advance", bank.name, port.name, lend, bank.currency, key)

    # ------------------------------------------------------------------ public works
    def _public_works(self, kernel: Any, bank: CentralBank, supply_total: int, receipts: Any) -> None:
        """
        Open market operations: reserves beyond the ceiling are idle money. The bank spends a share of
        the excess on public works across its federation's populated worlds (vaults, pro rata population),
        returning trapped liquidity to circulation. A transfer - nothing is minted.
        """
        from xylarium.kernel import regimes
        if bank.currency == "SOL" or not regimes.spends(kernel, bank.currency):
            return  # the Federal Reserve's treasury also underwrites insurance, bounties and relief
        ceiling = int(supply_total * CENTRAL_BANK_RESERVE_CEILING)
        excess = self.reserves(kernel, bank) - max(ceiling, self.reserve_floor(bank))
        if excess <= 0:
            return
        spend = int(excess * CENTRAL_BANK_OMO_RATE)
        worlds = [p for s in kernel.sectors.values() for p in s.planets
                  if p.population > 0 and p.currency == bank.currency]
        if spend <= 0 or not worlds:
            return
        pop = sum(p.population for p in worlds) or 1
        paid = 0
        for p in worlds:
            share = int(spend * p.population / pop)
            p.treasury += share
            paid += share
        self._adjust(kernel, bank, -paid)
        bank.bump("public_works", paid)
        receipts.add(kernel, "public_works", bank.name, f"{bank.federation} worlds", paid, bank.currency,
                     f"reserves above {CENTRAL_BANK_RESERVE_CEILING:.0%} of supply")

    # ------------------------------------------------------------------ council
    def _council(self, kernel: Any) -> Optional[str]:
        """Each era the governors review the clearing rules; the union's mood follows their alignment."""
        from xylarium.config import POLICY_REVIEW_INTERVAL
        if kernel.cycle_count - self.last_council_cycle < POLICY_REVIEW_INTERVAL or not self.banks:
            return None
        self.last_council_cycle = kernel.cycle_count
        mood = sum(b.alignment for b in self.banks.values()) / len(self.banks)
        old = self.deficit_slope
        if mood >= 0.15:
            self.deficit_slope = max(POLICY_RATE_DEFICIT_SLOPE * 0.5, self.deficit_slope * 0.85)
        elif mood <= -0.15:
            self.deficit_slope = min(POLICY_RATE_DEFICIT_SLOPE * 2.0, self.deficit_slope * 1.15)
        self.council_history.append([kernel.cycle_count, round(mood, 3), round(self.deficit_slope, 5)])
        self.council_history = self.council_history[-20:]
        if abs(self.deficit_slope - old) > 1e-9:
            chron = getattr(kernel, "chronicle", None)
            if chron is not None:
                verb = "softens" if self.deficit_slope < old else "hardens"
                chron.record(kernel, "FACTION_DECREE", "CLEARING_UNION", "Galactic Clearing Union",
                             f"The Clearing Accord of Cycle {kernel.cycle_count}",
                             f"THE GALACTIC CLEARING UNION ANNOUNCES. The council of governors {verb} the deficit "
                             f"penalty to {self.deficit_slope:.4f} (council mood {mood:+.2f}). "
                             + ("Deficit federations may borrow more cheaply." if verb == "softens"
                                else "Federations living beyond their means will pay for it."),
                             tags=["clearing", "banking", "policy"], alignment=mood, author="Galactic Clearing Union")
            return f"[CLEARING] Council sets deficit penalty {self.deficit_slope:.4f} (mood {mood:+.2f})."
        return None

    # ------------------------------------------------------------------ quarter
    def quarter(self, kernel: Any) -> List[str]:
        from xylarium.kernel.ledger import money_supply
        receipts = kernel.settlement
        logs: List[str] = []
        supply = money_supply(kernel)
        for bank in self.banks.values():
            # (no pool interventions toward genesis depth: what a pool holds is what its traders and providers
            # leave in it - regimes.py governs what each polity chooses to do instead)
            self._credit(kernel, bank, receipts)
            self._deposit_interest(kernel, bank)
            self._public_works(kernel, bank, supply.get(bank.currency, {}).get("total", 0), receipts)
        note = self._council(kernel)
        if note:
            logs.append(note)
        return logs

    # ------------------------------------------------------------------ views
    def clearing_imbalance(self) -> float:
        return round(sum(self.stamp.values()), 6)

    def summary(self, kernel: Any) -> Dict[str, Any]:
        from xylarium.kernel.alignment import band
        return {
            "banks": [{
                "currency": b.currency, "bank": b.name, "federation": b.federation, "governor": b.governor,
                "alignment": b.alignment, "band": band(b.alignment), "reserves": self.reserves(kernel, b),
                "loans_outstanding": b.loans_outstanding, "borrowers": len(b.loans),
                "policy_rate_q": b.policy_rate, "stamp_position": round(self.stamp.get(b.currency, 0.0), 2),
                "exchange": EXCHANGES.get(b.currency), "stats": dict(b.stats),
            } for b in self.banks.values()],
            "isse_stamp_position": round(self.stamp.get(ISSE_MEMBER, 0.0), 2),
            "clearing_imbalance": self.clearing_imbalance(),
            "deficit_slope": self.deficit_slope,
            "exchanges": dict(EXCHANGES),
        }

    # ------------------------------------------------------------------ persistence
    def to_dict(self) -> Dict[str, Any]:
        return {"banks": {k: b.to_dict() for k, b in self.banks.items()}, "stamp": dict(self.stamp),
                "deficit_slope": self.deficit_slope, "last_council_cycle": self.last_council_cycle,
                "council_history": [list(x) for x in self.council_history]}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BankingSystem":
        bs = cls()
        bs.banks = {k: CentralBank.from_dict(v) for k, v in d.get("banks", {}).items()}
        bs.stamp = {k: float(v) for k, v in d.get("stamp", {}).items()}
        bs.deficit_slope = float(d.get("deficit_slope", POLICY_RATE_DEFICIT_SLOPE))
        bs.last_council_cycle = int(d.get("last_council_cycle", 0))
        bs.council_history = [list(x) for x in d.get("council_history", [])]
        return bs
