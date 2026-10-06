"""
Backing: a money is a claim on the goods its own people hold. Its backing is those goods' worth in SOL (never through
its own rate); its fair rate is SOL's goods per unit over its own; the goods route moves a strayed rate halfway back,
by swaps and moved goods only; and a world leaves a money only when the goods behind each unit thin beyond the noise.
"""

import random
import unittest
from unittest import mock

from xylarium.kernel import backing, ledger
from xylarium.kernel.engine import GameKernel


def _money(k):
    return {c: v["total"] for c, v in ledger.money_supply(k).items()}


def _goods(k):
    out = {}
    for s in k.sectors.values():
        if s.port is not None:
            for c, q in s.port.stock.items():
                out[c] = out.get(c, 0) + q
    return out


class TestBacking(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        self.k.activate()
        for _ in range(25):
            self.k.tick_simulation()
        self.cur = sorted(self.k.fx_market.pools)[0]

    def test_fair_rate_is_sols_goods_per_unit_over_its_own(self):
        m = backing.measure(self.k)
        sol, own = m["SOL"]["per_unit"], m[self.cur]["per_unit"]
        self.assertGreater(sol, 0)
        self.assertGreater(own, 0)
        self.assertAlmostEqual(m[self.cur]["fair"], sol / own)

    def test_a_moneys_goods_are_never_valued_through_its_own_rate(self):
        from xylarium.kernel import cache
        cache.clear(self.k)
        before = backing.measure(self.k)[self.cur]["backing_sol"]
        pool = self.k.fx_market.pools[self.cur]
        pool["local"] *= 10                                   # its market crashes; its goods have not changed
        cache.clear(self.k)
        after = backing.measure(self.k)[self.cur]["backing_sol"]
        self.assertAlmostEqual(before, after, delta=abs(before) * 1e-6 + 1)

    def test_the_goods_route_moves_a_strayed_rate_back_and_mints_nothing(self):
        fx = self.k.fx_market
        backing.stats(self.k)["of"] = backing.measure(self.k)
        r = fx.rate(self.cur)
        backing.stats(self.k)["of"][self.cur]["fair"] = r * 3.0            # it claims more than its goods
        for s in self.k.sectors.values():
            if s.port is not None:
                s.port.treasury = max(s.port.treasury, 10 ** 7)
        money, goods = _money(self.k), _goods(self.k)
        gaps = backing.arbitrage(self.k)
        self.assertLess(gaps[self.cur], 0)
        self.assertGreater(fx.rate(self.cur), r)                           # it falls toward its goods
        self.assertLess(fx.rate(self.cur), r * 3.0)
        after = _money(self.k)
        for c in set(money) | set(after):
            self.assertEqual(money.get(c, 0), after.get(c, 0), c)          # swaps, not mints
        self.assertEqual(goods, _goods(self.k))                            # goods moved, not made

    def test_no_one_leaves_over_noise_or_a_neighbours_growth(self):
        st = backing.stats(self.k)
        st["per_unit"][self.cur] = [2.0, 2.05, 1.98, 2.02, 1.99, 2.01, 2.0, 1.97, 2.03]
        self.assertIsNone(backing._falling(self.k, self.cur))
        st["per_unit"][self.cur] = [2.9, 2.8, 2.7, 2.6, 2.5, 2.35, 2.2, 2.05, 1.9]
        self.assertGreater(backing._falling(self.k, self.cur), 0)

    def test_a_world_that_leaves_converts_at_the_market_and_mints_nothing(self):
        w = next(p for s in self.k.sectors.values() for p in s.planets
                 if p.population > 0 and p.currency == self.cur)
        w.treasury = max(w.treasury, 10_000)
        money = _money(self.k)
        self.assertTrue(backing.leave(self.k, w, "SOL", []))
        self.assertEqual(w.currency, "SOL")
        after = _money(self.k)
        for c in set(money) | set(after):
            self.assertEqual(money.get(c, 0), after.get(c, 0), c)


if __name__ == "__main__":
    unittest.main()
