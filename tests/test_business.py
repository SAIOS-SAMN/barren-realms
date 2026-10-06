"""
Business: each seat's book of the economy (what is dear here, what routes are open, what is wanted, its model, its
exchanges, its salt) - and a sovereign's own order to found an exchange at a port of its worlds, paying the capital
the place's flow asks for. Books only read; the order moves money, never makes it.
"""

import random
import unittest

from xylarium.kernel import business, command, exchanges, ledger, relations
from xylarium.kernel.engine import GameKernel


class TestBusiness(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        self.k.activate()
        for _ in range(100):
            self.k.tick_simulation()

    def test_a_captains_book_reads_the_economy_around_it(self):
        cap = next(iter(self.k.captains.values()))
        book = business.captain_book(self.k, cap)
        for key in ("exotic", "routes", "wanted", "escorts_here", "exchange_here", "purse_sol", "escort"):
            self.assertIn(key, book)
        for e in book["exotic"]:
            self.assertGreaterEqual(e["index"], 0.0)

    def test_a_sovereigns_book_and_its_exchange(self):
        def port_of_its_money(ws):
            return next((self.k.sectors[w.sector_id] for w in ws if w.population > 0
                         and self.k.sectors[w.sector_id].port is not None
                         and self.k.sectors[w.sector_id].port.currency == w.currency and w.currency != "SOL"), None)
        people, sec = next(((p, port_of_its_money(ws)) for p, ws in sorted(relations._peoples(self.k).items())
                            if ws and port_of_its_money(ws) is not None), (None, None))
        if people is None:
            self.skipTest("no people keeps a port of its own money")
        book = business.sovereign_book(self.k, people)
        for key in ("model", "traded", "wants", "exchanges"):
            self.assertIn(key, book)
        exchanges.stats(self.k)["last_flow"].pop(str(sec.id), None)
        exchanges.stats(self.k)["flow"].pop(str(sec.id), None)
        self.assertFalse(business.found_exchange(self.k, people, sec.id)["ok"])     # no flow, nothing to earn
        exchanges.stats(self.k)["last_flow"][str(sec.id)] = [500.0, 5]
        for w in sec.planets:
            w.treasury = max(w.treasury, 10 ** 8)
        before = {c: v["total"] for c, v in ledger.money_supply(self.k).items()}
        got = business.found_exchange(self.k, people, sec.id)
        self.assertTrue(got["ok"], got)
        self.assertIsNotNone(exchanges.at(self.k, sec.id))
        after = {c: v["total"] for c, v in ledger.money_supply(self.k).items()}
        for c in set(before) | set(after):
            self.assertEqual(before.get(c, 0), after.get(c, 0), c)               # capital moved, none made
        self.assertFalse(business.found_exchange(self.k, people, sec.id)["ok"])     # one stands already

    def test_only_a_seated_sovereign_may_order_an_exchange(self):
        cap = next(iter(self.k.captains.values()))
        got = command.dispatch(self.k, cap.id, "exchange", sector=cap.sector_id)
        self.assertFalse(got["ok"])

    def test_a_stewards_book(self):
        from xylarium.kernel import spheres, stewardship
        spheres.ensure(self.k)
        realms = stewardship.realms(self.k)
        if not realms:
            self.skipTest("no realm yet")
        book = business.steward_book(self.k, realms[0])
        for key in ("exchanges", "wanting", "carried"):
            self.assertIn(key, book)


if __name__ == "__main__":
    unittest.main()
