"""
Where the traffic goes, a dock follows: arrivals are counted, a portless lane is valued off the docks that exist,
and a founded waystation opens with empty shelves on its founder's capital - nothing minted, nothing conjured.
"""

import random
import unittest

from xylarium.kernel import intellect, matter, waystations
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply


def fresh(rseed=31):
    random.seed(rseed)
    k = GameKernel(seed=7)
    k.activate()
    return k


def money(k):
    return {c: b["total"] for c, b in money_supply(k).items()}


def portless(k):
    return next(s for s in k.sectors.values() if s.port is None and s.id != 1)


class TestWaystations(unittest.TestCase):
    def test_arrivals_are_counted_where_they_land(self):
        k = fresh()
        waystations.arrive(k, 5)
        waystations.arrive(k, 5)
        self.assertEqual(waystations.stats(k)["traffic"]["5"], 2)

    def test_founding_moves_capital_and_conjures_nothing(self):
        k = fresh()
        sec = portless(k)
        cap = next(c for c in k.captains.values() if getattr(c, "is_ai", False) and not c.faction_id)
        cap.credits += 10 ** 6
        m0, t0 = money(k), matter.totals(k)
        waystations.found(k, sec, cap, 50_000)
        self.assertIsNotNone(sec.port)
        self.assertEqual(sum(sec.port.stock.values()), 0)                     # empty shelves
        self.assertEqual(m0, money(k))
        self.assertEqual(t0, matter.totals(k))

    def test_a_dock_pays_its_founder_from_growth_only(self):
        k = fresh()
        sec = portless(k)
        cap = next(c for c in k.captains.values() if getattr(c, "is_ai", False) and not c.faction_id)
        cap.credits += 10 ** 6
        waystations.found(k, sec, cap, 50_000)
        rec = waystations.stats(k)["docks"][str(sec.id)]
        waystations._pay_founders(k)
        self.assertEqual(rec.get("paid", 0), 0)                               # no growth, no dividend
        sec.port.treasury += 1000
        m0 = money(k)
        waystations._pay_founders(k)
        self.assertEqual(rec["paid"], 500)
        self.assertEqual(m0, money(k))

    def test_a_dock_trades_in_the_money_of_those_who_live_around_it(self):
        k = fresh()
        sec = next(s for s in k.sectors.values() if s.port is None and s.id != 1
                   and any(p.population > 0 and not p.natives for p in s.planets))
        world = max((p for p in sec.planets if p.population > 0), key=lambda p: p.population)
        cap = next(c for c in k.captains.values() if getattr(c, "is_ai", False) and not c.faction_id)
        cap.credits += 10 ** 6
        waystations.found(k, sec, cap, 50_000)
        self.assertEqual(sec.port.currency, world.currency)
        other = next(c for c in ("FRN", "THR", "SOL") if c != world.currency)
        sec.port.currency = other                                             # its people changed money
        m0 = money(k)
        waystations._rehome(k)
        self.assertEqual(sec.port.currency, world.currency)
        self.assertEqual(m0, money(k))

    def test_a_relic_cannot_hand_the_fourth_axis_to_a_people_without_the_third(self):
        k = fresh()
        for i in range(400):
            got = intellect.relic_crystal(k, f"civ:reader{i}", f"relic-{i}")
            if got is not None:
                self.assertLess(intellect.RANK_OF.get(got, 2), 4)


if __name__ == "__main__":
    unittest.main()
