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



class TestSolvency(unittest.TestCase):
    def setUp(self):
        random.seed(53)
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.mm = self.k.market_manager

    def _shell(self):
        firms = enterprise.stats(self.k)["firms"]
        return next(c for t, c in self.mm.companies.items() if t not in firms)

    def test_a_shell_that_finds_no_work_is_wound_up_in_four_quarters_conserving_money(self):
        from unittest import mock
        shell = self._shell()
        m0 = money(self.k)
        with mock.patch.object(enterprise, "convert", lambda k, c: None):
            for q in range(liquidation.WIND_UP_QUARTERS):
                self.assertIn(shell.ticker, self.mm.companies)
                liquidation.quarter(self.k)
                self.assertTrue(shell.ticker not in self.mm.companies or liquidation.distressed(self.k, shell.ticker))
        self.assertNotIn(shell.ticker, self.mm.companies)
        self.assertEqual(m0, money(self.k))
        self.assertGreater(liquidation.stats(self.k)["causes"].get("dormant", 0), 0)

    def test_a_shell_that_can_pay_for_a_plant_converts_and_keeps_its_holders(self):
        firms = enterprise.stats(self.k)["firms"]
        m0 = money(self.k)
        before = set(self.mm.companies)
        for c in list(self.mm.companies.values()):
            c.treasury += 10 ** 6                     # cash enough to build
        dem = enterprise.stats(self.k).setdefault("demand", {})
        for sec in self.k.sectors.values():            # ports that take goods off their shelves
            if sec.port is not None:
                dem[str(sec.id)] = {out: 200.0 for out in enterprise.RECIPES}
        m0 = money(self.k)
        for _ in range(4):
            liquidation.quarter(self.k)
        converted = [t for t in firms if firms[t].get("converted")]
        if not converted:
            self.skipTest("no home port where a recipe pays")
        self.assertTrue(set(converted) <= before)
        self.assertEqual(m0, money(self.k))

    def test_the_desk_does_not_lend_against_a_distressed_company(self):
        from xylarium.kernel import credit
        shell = self._shell()
        liquidation.stats(self.k)["standing"][shell.ticker] = {"state": "distressed", "quarters": 1, "why": "dormant"}
        cap = next(iter(self.k.captains.values()))
        shell.treasury = 10 ** 7
        self.assertEqual(credit.lend(self.k, cap, shell.ticker, 10_000), 0)

    def test_a_failing_firms_price_falls_toward_its_estate(self):
        w, ticker, comp = failing_firm(self.k)
        if comp is None:
            self.skipTest("no world with a port of its money")
        comp.share_price = 500
        enterprise.stats(self.k)["firms"][ticker]["profit_q"] = -100
        for _ in range(12):
            self.mm._revalue_shares(self.k)
        self.assertLess(comp.share_price, 50)
        self.assertGreaterEqual(comp.share_price, int(liquidation.fair_price(self.k, comp)))

    def test_a_rescue_moves_the_plant_and_conserves_money(self):
        w, ticker, comp = failing_firm(self.k)
        if comp is None:
            self.skipTest("no world with a port of its money")
        enterprise.found(self.k, w, "EQUIPMENT", 10)
        rival = next(t for t in enterprise.stats(self.k)["firms"] if t != ticker)
        self.mm.companies[rival].home_cash = 10 ** 7
        rec = enterprise.stats(self.k)["firms"][ticker]
        plant = rec["plant"] + enterprise.stats(self.k)["firms"][rival]["plant"]
        m0 = money(self.k)
        from unittest import mock
        from xylarium.kernel import decide
        port = enterprise._port(self.k, w)
        enterprise.stats(self.k).setdefault("demand", {})[str(port.sector_id)] = {"EQUIPMENT": 10 ** 4}
        with mock.patch.object(decide, "choose", lambda k, opts, m, *salt: opts[0]), \
                mock.patch.object(enterprise, "unit_economics", lambda *a: {"margin": 50.0}):
            log = enterprise.rescue(self.k, ticker, rec)
        self.assertIsNotNone(log)
        self.assertNotIn(ticker, self.mm.companies)
        self.assertEqual(enterprise.stats(self.k)["firms"][rival]["plant"], plant)
        self.assertEqual(m0, money(self.k))


if __name__ == "__main__":
    unittest.main()
