"""
A company wound up in order: its loans called, its shorts closed at what it is worth, the rest to its holders -
every unit of money moved, none made or lost.
"""

import random
import unittest

from xylarium.kernel import enterprise, liquidation
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply


def money(k):
    return {c: b["total"] for c, b in money_supply(k).items()}


def failing_firm(k):
    for w in (p for s in k.sectors.values() for p in s.planets
              if p.population > 0 and p.civilization is not None and p.owner_id is None and not p.natives):
        if enterprise._port(k, w) is not None:
            w.treasury = 10 ** 6
            enterprise.found(k, w, "EQUIPMENT", 10)
            ticker = next(iter(enterprise.stats(k)["firms"]))
            return w, ticker, k.market_manager.companies[ticker]
    return None, None, None


class TestLiquidation(unittest.TestCase):
    def setUp(self):
        random.seed(51)
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.world, self.ticker, self.comp = failing_firm(self.k)
        if self.comp is None:
            self.skipTest("no world with a port of its money")
        caps = [c for c in self.k.captains.values()]
        self.holder, self.borrower, self.shorter = caps[0], caps[1], caps[2]
        self.comp.treasury = 40_000
        self.comp.home_cash = 0
        self.comp.total_shares = 1000
        self.holder.portfolio[self.ticker] = 300
        self.borrower.portfolio[self.ticker] = 100
        self.borrower.margin_loans[self.ticker] = 50_000           # far more than its collateral is worth
        self.borrower.credits = 1_000
        self.shorter.credits = 0
        self.k.federal_reserve.receive(20_000, "margin_escrow")   # what the short seller posted
        self.k.market_manager.companies[self.ticker].treasury += 0
        self.shorter.short_positions[self.ticker] = {"ticker": self.ticker, "shares": 200, "entry_price": 100,
                                                     "collateral": 20_000, "margin_rate": 0.5}

    def test_it_conserves_every_money(self):
        m0 = money(self.k)
        liquidation.liquidate(self.k, self.ticker, "test")
        self.assertEqual(m0, money(self.k))
        self.assertNotIn(self.ticker, self.k.market_manager.companies)

    def test_shorts_are_paid_by_the_fall_and_their_collateral_released(self):
        liquidation.liquidate(self.k, self.ticker, "test")
        self.assertNotIn(self.ticker, self.shorter.short_positions)
        p = 40_000 / 1000
        self.assertEqual(self.shorter.credits, 20_000 - int(200 * p))      # collateral back, cover paid
        self.assertGreater(liquidation.stats(self.k)["short_pnl_sol"], 0)

    def test_an_unpayable_margin_loan_is_called_and_defaults(self):
        rating = getattr(self.borrower, "credit_rating", 500)
        rec = liquidation.liquidate(self.k, self.ticker, "test")
        self.assertNotIn(self.ticker, self.borrower.margin_loans)
        self.assertNotIn(self.ticker, self.borrower.portfolio)              # collateral seized
        self.assertEqual(self.borrower.credits, 0)                         # cash taken toward the debt
        self.assertGreater(rec["defaulted_sol"], 0)
        self.assertLess(self.borrower.credit_rating, rating)

    def test_holders_share_what_is_left(self):
        before = self.holder.credits
        liquidation.liquidate(self.k, self.ticker, "test")
        self.assertGreater(self.holder.credits, before)
        self.assertNotIn(self.ticker, self.holder.portfolio)


if __name__ == "__main__":
    unittest.main()
