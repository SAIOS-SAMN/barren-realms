"""
In a cosmic universe money, the exchange and the Reserve are founded by peoples: a state strikes its coin when it
founds itself, the exchange opens when two monies meet or the first starport opens, the Reserve when two banks
trade through the exchange. Before that there is nothing to circulate, and the money seasons do nothing.
"""

import unittest

from xylarium.kernel import institutions, ledger
from xylarium.kernel.engine import GameKernel


def _money(k):
    return {c: b["total"] for c, b in ledger.money_supply(k).items() if b["total"]}


class TestFounding(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.home = next(p for s in self.k.sectors.values() for p in s.planets if p.population > 0)

    def test_nothing_exists_before_anyone_founds_it(self):
        self.assertEqual(_money(self.k), {})
        self.assertEqual(self.k.banking.banks, {})
        self.assertEqual(self.k.fx_market.pools, {})
        self.assertFalse(institutions.reserve_founded(self.k))

    def test_a_state_strikes_its_coin_and_the_exchange_opens_with_deposits(self):
        p = self.home
        p.society["way"] = "state"
        self.assertIn("found their money", institutions.found_currency(self.k, p))
        cur = p.currency
        self.assertIn(cur, self.k.banking.banks)
        self.assertEqual(institutions.found_currency(self.k, p), None)              # once
        p.treasury = 40000
        before = p.treasury
        line = institutions.found_exchange(self.k, "the first starport opens")
        self.assertIsNotNone(line)
        pool = self.k.fx_market.pools[cur]
        self.assertEqual(before - p.treasury, pool["local"])                       # a deposit: moved, not made
        self.assertGreater(pool["sol"], 0)                                         # the house's unit, minted against it
        self.assertIsNone(institutions.found_reserve(self.k))                       # one bank: no Reserve yet

    def test_unfounded_moneys_are_not_governed(self):
        from xylarium.kernel import regimes
        for _ in range(400):
            self.k.tick_simulation()
        self.assertEqual(regimes.stats(self.k)["switches"], 0)


if __name__ == "__main__":
    unittest.main()
