"""
A steward's endowments: tithes reach its line's fund; each year it sets aside its realm's growth for the arrivals and
turns it into goods held in escrow; at a people's ascension the goods go onto a dock of its own, and its money is
listed once its currency board has issued it against them. Money is only ever moved - never made - by any of it.
"""
import random
import unittest
from unittest import mock

from xylarium.kernel import endowments, ledger


def _total_sol(k):
    return ledger.money_supply(k).get("SOL", {}).get("total", 0)


class TestEndowments(unittest.TestCase):
    def setUp(self):
        from xylarium.kernel.engine import GameKernel
        random.seed(5)
        self.k = GameKernel(seed=7)
        self.k.activate()

    def _sol_port(self):
        return next(s.port for s in sorted(self.k.sectors.values(), key=lambda s: s.id)
                    if s.port is not None and getattr(s.port, "currency", "SOL") == "SOL"
                    and all(s.port.stock.get(c, 0) > 50 for c in endowments.BASKET))

    def test_a_tithe_reaches_the_fund_and_the_money_supply_holds(self):
        cap = next(iter(self.k.captains.values()))
        before = _total_sol(self.k)
        cap.credits -= 1000
        endowments.credit(self.k, "civ:Line", 1000)
        self.assertEqual(_total_sol(self.k), before)
        self.assertEqual(endowments.sol(endowments.stats(self.k)["funds"]["civ:Line"]), 1000)

    def test_an_escrow_buys_goods_at_the_ports_prices_and_no_money_is_made(self):
        port = self._sol_port()
        esc = {"line": "civ:Line", "sol": 3000.0, "goods": {}, "since": 0}
        endowments.stats(self.k)["escrows"]["civ:New"] = esc
        before, stock = _total_sol(self.k), {c: port.stock[c] for c in endowments.BASKET}
        endowments._buy(self.k, esc)
        self.assertGreater(sum(esc["goods"].values()), 0)                       # resources, held for the arrival
        self.assertLess(endowments.sol(esc), 3000)
        self.assertAlmostEqual(_total_sol(self.k), before, delta=1)            # SOL moved to the port, not made
        self.assertLess(sum(port.stock[c] for c in endowments.BASKET), sum(stock.values()))

    def test_ascension_puts_the_goods_on_a_dock_of_its_own(self):
        home = next(p for s in sorted(self.k.sectors.values(), key=lambda s: s.id) if s.port is None
                    for p in s.planets)
        endowments.stats(self.k)["escrows"]["civ:New"] = {"line": "civ:Line", "sol": 500.0,
                                                          "goods": {"ORE": 40, "ORGANICS": 25}, "since": 0}
        before = _total_sol(self.k)
        with mock.patch("xylarium.kernel.spheres._home", lambda k, w: home):
            self.assertIsNotNone(endowments.release(self.k, "civ:New"))
        port = self.k.sectors[home.sector_id].port
        self.assertIsNotNone(port)                                              # a dock of its own
        self.assertGreaterEqual(port.stock.get("ORE", 0), 40)                   # the goods on its shelves
        self.assertIn("civ:New", endowments.stats(self.k)["listing"])           # its listing waits on its money
        self.assertAlmostEqual(_total_sol(self.k), before, delta=1)

    def test_its_money_is_listed_at_its_fair_rate_and_no_money_is_made(self):
        home = next(p for s in sorted(self.k.sectors.values(), key=lambda s: s.id) if s.port is not None
                    for p in s.planets)
        port = self.k.sectors[home.sector_id].port
        home.currency = port.currency = "NEW"                                  # a newly ascended people's money,
        port.treasury = 10000                                                   # issued on its dock, not yet listed
        endowments.stats(self.k)["listing"]["civ:New"] = {"sol": 800.0, "line": "civ:Line", "since": 0}
        before = {c: ledger.money_supply(self.k).get(c, {}).get("total", 0) for c in ("SOL", home.currency)}
        with mock.patch("xylarium.kernel.spheres._home", lambda k, w: home), \
                mock.patch("xylarium.kernel.backing.fair", lambda k, c: 2.0):
            self.assertIsNotNone(endowments._list(self.k, "civ:New"))
        pool = self.k.fx_market.pools[home.currency]
        self.assertAlmostEqual(pool["local"] / pool["sol"], 2.0, delta=0.01)    # at its fair rate
        after = {c: ledger.money_supply(self.k).get(c, {}).get("total", 0) for c in ("SOL", home.currency)}
        for c in before:
            self.assertAlmostEqual(after[c], before[c], delta=1)                # both sides moved, nothing made


if __name__ == "__main__":
    unittest.main()
