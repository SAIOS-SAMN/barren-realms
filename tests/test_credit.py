"""
Credit: leverage by temperament, interest, margin calls, default and the retained-earnings levy.
"""

import random
import unittest

from xylarium.kernel import credit
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply


def totals(kernel):
    return {c: b["total"] for c, b in money_supply(kernel).items()}


class TestCredit(unittest.TestCase):
    def setUp(self):
        random.seed(73)
        self.kernel = GameKernel(seed=42)
        self.kernel.activate()
        self.cap = self.kernel.register_player("bold", "Bold")
        self.cap.credits = 50_000
        self.ticker, self.comp = next(iter(self.kernel.market_manager.companies.items()))
        self.comp.treasury += 500_000

    def gambler(self, risk=3.0, caution=1.0):
        self.cap.traits = {"calling": "trader", "thrift": 1.0, "ambition": 1.0, "caution": caution, "risk": risk,
                           "horizon": 1.0, "spend": 0.1}

    def test_the_cautious_borrow_nothing_and_the_bold_borrow_by_temperament(self):
        self.gambler(risk=0.8, caution=1.2)
        self.assertEqual(credit.lend(self.kernel, self.cap, self.ticker, 10_000), 0)
        self.gambler(risk=3.0, caution=1.0)
        before = totals(self.kernel)
        loan = credit.lend(self.kernel, self.cap, self.ticker, 10_000)
        self.assertEqual(loan, 20_000)                                  # leverage capped at 2x the stake
        self.assertEqual(self.cap.margin_loans[self.ticker], loan)
        self.assertEqual(before, totals(self.kernel))                   # the company's cash, lent: no minting

    def test_a_crash_calls_the_margin_and_can_ruin_the_borrower(self):
        self.gambler()
        mm = self.kernel.market_manager
        stake = 100 * self.comp.share_price
        loan = credit.lend(self.kernel, self.cap, self.ticker, stake)
        ok, msg, _ = mm.buy_shares(self.cap, self.ticker, (stake + loan) // self.comp.share_price)
        self.assertTrue(ok, msg)
        self.cap.credits = 0
        self.comp.share_price = max(1, self.comp.share_price // 10)     # the market turns
        before = totals(self.kernel)
        credit.quarter(self.kernel)
        self.assertEqual(before, totals(self.kernel))
        st = credit._stats(self.kernel)
        self.assertGreater(st["margin_calls"], 0)
        self.assertEqual(self.cap.portfolio.get(self.ticker, 0), 0)
        self.assertEqual(st["defaults"], 1)
        self.assertLess(self.cap.credit_rating, 500)

    def test_hoarded_corporate_cash_is_levied_to_the_home_world(self):
        self.comp.last_outflow_q = 1000
        home = self.kernel.get_planet(self.comp.planet_id)
        vault = home.treasury
        before = totals(self.kernel)
        credit._levy(self.kernel, self.comp)
        self.assertGreater(home.treasury, vault)
        self.assertEqual(before, totals(self.kernel))


if __name__ == "__main__":
    unittest.main()
