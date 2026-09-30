"""
Money from real output: the regional authorities keep M V = P Y, with V measured at genesis.
"""

import random
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import MonetaryPolicy, money_supply


class TestQuantityEquation(unittest.TestCase):
    def test_velocity_is_measured_after_the_first_year_and_money_follows_output(self):
        mp = MonetaryPolicy()
        mp.targets["FRN"] = 1000.0
        for _ in range(4):
            mp.record_output("FRN", 50.0)
            mp.output_seasons.setdefault("FRN", []).append(mp.output_q.pop("FRN"))
        mp.output0["FRN"] = mp.annual_output("FRN")          # Y0 = 200 -> V = P*200/1000
        self.assertEqual(mp.target("FRN", 1000.0), 1000.0)
        mp.output_seasons["FRN"] = [100.0] * 4                # the real economy doubles
        self.assertEqual(mp.target("FRN", 1000.0), 2000.0)    # so does the money it needs

    def test_a_short_economy_is_supplied_by_transfers_to_households(self):
        random.seed(61)
        k = GameKernel(seed=42)
        mp = k.monetary_policy
        cur = "VOID"
        m = money_supply(k)[cur]["total"]
        mp.targets[cur] = float(m)
        mp.output0[cur] = 100.0
        mp.output_seasons[cur] = [50.0, 50.0, 50.0]           # the next season closes a year of output 200
        mp.output_q[cur] = 50.0
        purses = sum(p.household_purse for s in k.sectors.values() for p in s.planets if p.currency == cur)
        mp.update(k)                                          # M* = 2 M: a quarter of the gap is transferred
        after = money_supply(k)[cur]["total"]
        self.assertAlmostEqual(after - m, m / 4, delta=m * 0.01)
        self.assertEqual(mp.factor(cur), 0.0)                 # services withdraw nothing while money is short
        self.assertGreater(sum(p.household_purse for s in k.sectors.values() for p in s.planets
                               if p.currency == cur), purses)

    def test_an_overfull_economy_withdraws_through_services(self):
        mp = MonetaryPolicy()
        k = GameKernel(seed=42)
        m = money_supply(k)["FRN"]["total"]
        mp.targets["FRN"] = m / 2.0                           # half the money the economy has
        mp.record_earnings("FRN", 1000.0, 600.0)
        mp.update(k)
        self.assertGreater(mp.factor("FRN"), 1.0)             # withdraw more than the season's tax


if __name__ == "__main__":
    unittest.main()
