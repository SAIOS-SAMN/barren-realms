"""
Nothing is thrown away: services reach their providers, hoards stay buried, markets have counterparties.
"""

import random
import unittest

from xylarium.kernel import ledger
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply


def totals(kernel):
    return {c: b["total"] for c, b in money_supply(kernel).items()}


class TestConservation(unittest.TestCase):
    def setUp(self):
        random.seed(71)
        self.kernel = GameKernel(seed=42)
        self.kernel.activate()
        self.cap = self.kernel.register_player("payer", "Payer")
        self.cap.credits = 100_000

    def test_a_service_is_paid_to_its_provider(self):
        before = totals(self.kernel)
        self.cap.credits -= 5000
        regional = next(s for s in self.kernel.sectors.values() if s.port and s.port.currency != "SOL")
        ledger.pay_service(5000, regional.id)
        self.cap.credits -= 700
        ledger.pay_service(700, institution="jump_gates")
        # SOL paid to a regional port is cleared into its money at the exchange: every currency's supply is
        # unchanged (SOL: wallet -> pool; local: pool -> port)
        self.assertEqual(before, totals(self.kernel))

    def test_new_ruins_keep_the_hoard_already_buried(self):
        from xylarium.kernel.archaeology import bury, _new_ruins
        p = next(pl for s in self.kernel.sectors.values() for pl in s.planets)
        rng = random.Random(1)
        p.ruins = _new_ruins("Old Ones", "x", "biotic", "ANCIENT", 2, [], "time", 0, 1, p.currency, 4000, rng)
        before = totals(self.kernel)
        p.ruins = bury(p, _new_ruins("New Ones", "y", "biotic", "RECENT", 1, [], "famine", 1, 1, None, 0, rng))
        self.assertEqual(p.ruins["hoard"], 4000)
        self.assertEqual(before, totals(self.kernel))

    def test_short_selling_has_a_counterparty(self):
        mm = self.kernel.market_manager
        ticker, comp = next(iter(mm.companies.items()))
        comp.treasury += 50_000
        self.cap.credit_rating = 800
        before = totals(self.kernel)
        ok, msg, _ = mm.short_sell(self.cap, ticker, 100, self.kernel)
        self.assertTrue(ok, msg)
        self.assertEqual(before, totals(self.kernel))
        ok, msg, _ = mm.cover_short(self.cap, ticker, None, self.kernel)
        self.assertTrue(ok, msg)
        self.assertEqual(before, totals(self.kernel))

    def test_faction_crews_are_paid_in_their_realms_money(self):
        fm = self.kernel.factions
        zeal = fm.factions.get("ZEALOT")
        if zeal is None or not fm.worlds(self.kernel, "ZEALOT"):
            self.skipTest("no Pyre on this seed")
        zeal.vault[zeal.currency] = zeal.vault.get(zeal.currency, 0) + 10_000_000
        zeal.fleet = []
        before = totals(self.kernel)
        fleet_before = set(zeal.fleet)
        logs = fm._commission_crusader(self.kernel, zeal)
        self.assertTrue(logs, "a crusader should have been commissioned")
        self.assertEqual(before, totals(self.kernel))
        crew = self.kernel.captains[next(c for c in zeal.fleet if c not in fleet_before)]
        self.assertGreater(crew.fx_wallet.get(zeal.currency, 0), 0)   # the faith pays in its own money

if __name__ == "__main__":
    unittest.main()
