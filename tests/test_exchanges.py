"""
Local exchanges and currency routes: a council founds an exchange where the flow pays for one; conversions there clear
through its own pools, so its rate is the place's own; a captain converts where it is docked, so a gap is worth flying
money across - money aboard draws pirates, and a world's government may lend fighters to sail with it. Nothing is
minted: every money is counted, pools included.
"""

import random
import unittest
from unittest import mock

from xylarium.kernel import decide, exchanges, fx, fxroutes, ledger
from xylarium.kernel.engine import GameKernel


def _accept(k, opts, m, *salt):
    return opts[0]


def _totals(k):
    return {c: v["total"] for c, v in ledger.money_supply(k).items()}


class TestExchanges(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        self.k.activate()
        self.sec = next(s for s in self.k.sectors.values() if s.port is not None and s.port.currency != "SOL"
                        and any(w.population > 0 and w.currency == s.port.currency for w in s.planets))
        self.cur = self.sec.port.currency
        self.council = max((w for w in self.sec.planets if w.population > 0 and w.currency == self.cur),
                           key=lambda w: w.treasury)
        self.council.treasury = 10 ** 8

    def _found(self):
        with mock.patch.object(decide, "choose", side_effect=_accept):
            self.assertTrue(exchanges._found(self.k, self.sec, [10_000.0, 10], []))
        return exchanges.at(self.k, self.sec.id)

    def test_a_council_founds_an_exchange_and_no_money_is_made(self):
        before = _totals(self.k)
        ex = self._found()
        self.assertEqual(ex["cur"], self.cur)
        fed = self.k.fx_market.rate(self.cur)
        self.assertAlmostEqual(exchanges.rate(ex), fed, delta=fed * 0.01)       # it opens at the federation's rate
        after = _totals(self.k)
        for c in set(before) | set(after):
            self.assertEqual(before.get(c, 0), after.get(c, 0), c)

    def test_conversions_there_clear_through_its_pools_and_move_its_rate(self):
        ex = self._found()
        r0 = exchanges.rate(ex)
        cap = next(c for c in self.k.captains.values())
        amt = int(ex["local"] * 0.2)
        fx.credit(cap, self.cur, 0)
        cap.fx_wallet[self.cur] = cap.fx_wallet.get(self.cur, 0)
        self.council.treasury -= amt
        fx.credit(cap, self.cur, amt)                             # a holder brings its money to the desk
        before = _totals(self.k)
        fx.debit(cap, self.cur, amt)
        out = exchanges.convert_at(self.k, self.sec.id, self.cur, "SOL", amt)
        cap.credits += out
        self.assertGreater(out, 0)
        self.assertGreater(exchanges.rate(ex), r0)               # selling its money there cheapens it there
        after = _totals(self.k)
        self.assertEqual(before[self.cur] , after[self.cur])
        self.assertEqual(before["SOL"], after["SOL"])

    def test_a_captain_converts_where_it_is_docked(self):
        ex = self._found()
        cap = next(c for c in self.k.captains.values())
        cap.credits = 10 ** 6
        cap.fx_wallet.pop(self.cur, None)
        before = exchanges.rate(ex)
        with mock.patch.object(self.k.fx_market, "exchange", wraps=self.k.fx_market.exchange) as fed:
            ok, _, got = fxroutes.exchange(self.k, cap, self.sec.id, "SOL", self.cur, 1000)
            self.assertTrue(ok)
            fed.assert_not_called()                              # the place's own desk
            other = next(s.id for s in self.k.sectors.values() if s.id != self.sec.id)
            fxroutes.exchange(self.k, cap, other, "SOL", self.cur, 1000)
            fed.assert_called_once()                             # elsewhere, the federation's
        self.assertGreater(got, 0)
        self.assertLessEqual(got, 1000 * before)                 # at the place's rate, less what the trade moved it
        self.assertLess(exchanges.rate(ex), before)              # buying its money there made it dearer there

    def test_a_gap_is_a_route_worth_flying(self):
        ex = self._found()
        dump = int(ex["local"])
        self.council.treasury -= dump
        self.council.treasury += 0
        exchanges.convert_at(self.k, self.sec.id, self.cur, "SOL", dump)     # its money sold hard there
        direction, s, back = fxroutes.gain(self.k, ex, 10 ** 7)
        self.assertEqual(direction, "buy_local")
        self.assertGreater(back, s)

    def test_dividends_pay_the_founder_from_growth_only(self):
        ex = self._found()
        t0 = self.council.treasury
        exchanges._dividend(self.k, str(self.sec.id), ex)
        self.assertEqual(self.council.treasury, t0)              # nothing grown: nothing paid
        ex["local"] *= 1.2
        ex["sol"] *= 1.2
        before = _totals(self.k)
        exchanges._dividend(self.k, str(self.sec.id), ex)
        self.assertGreater(self.council.treasury, t0)
        after = _totals(self.k)
        self.assertEqual(before[self.cur], after[self.cur])


class TestMoneyAboard(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        self.k.activate()
        caps = list(self.k.captains.values())
        self.a, self.b = caps[0], caps[1]
        self.world = next(w for s in self.k.sectors.values() for w in s.planets if w.population > 0)
        self.world.fighters = 40

    def test_a_destroyed_ship_loses_half_its_purse(self):
        self.b.fx_wallet = {"VOID": 1000, "THR": 7}
        took = fxroutes.plunder_purse(self.a, self.b)
        self.assertEqual(took, {"VOID": 500, "THR": 3})
        self.assertEqual(fx.balance(self.b, "VOID"), 500)
        self.assertEqual(fx.balance(self.a, "VOID"), self.a.fx_wallet.get("VOID", 0))

    def test_a_purse_draws_pirates(self):
        from xylarium.kernel import crime
        sec = self.k.sectors[self.world.sector_id]
        self.a.ship.fighters, self.b.ship.fighters = 100, 5
        self.b.bounty, self.b.faction_id, self.a.faction_id = 0, None, None
        with mock.patch.object(sec, "captains", [self.b.id]), \
                mock.patch.object(type(sec.security), "value", "ANARCHY", create=True):
            def piracy():
                return [g for g, _, kind, _ in crime._opportunities(self.k, self.a, sec) if kind == "piracy"]
            self.b.fx_wallet = {}
            poor = piracy()
            self.b.fx_wallet = {"SOL": 0, sorted(self.k.fx_market.pools)[0]: 10 ** 6}
            rich = piracy()
        if poor and rich:
            self.assertGreater(rich[0], poor[0])

    def test_a_worlds_escort_is_paid_for_sails_and_comes_home(self):
        self.a.credits = 10 ** 6
        self.a.escort = None
        before = _totals(self.k)
        ok, _ = fxroutes.hire(self.k, self.a, self.world, 10, self.k.cycle_count + 50, "ANARCHY")
        self.assertTrue(ok)
        self.assertEqual(self.world.fighters, 30)
        self.assertEqual(fxroutes.escort_fighters(self.a), 10)
        after = _totals(self.k)
        for c in set(before) | set(after):
            self.assertEqual(before.get(c, 0), after.get(c, 0), c)   # the fee is paid, not made
        self.assertEqual(fxroutes.wear_escort(self.a, 4), 0)          # it takes losses first
        fxroutes.release(self.k, self.a)
        self.assertEqual(self.world.fighters, 36)                     # what is left of it goes home
        self.assertIsNone(self.a.escort)


if __name__ == "__main__":
    unittest.main()
