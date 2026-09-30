"""
Law: jurisdictions and presence, the docket, courts that recall money, warrants and freezes.
"""

import random
import unittest

from xylarium.kernel import law
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply
from xylarium.kernel.models import ActionType


def totals(kernel):
    return {c: b["total"] for c, b in money_supply(kernel).items()}


class TestLaw(unittest.TestCase):
    def setUp(self):
        random.seed(91)
        self.kernel = GameKernel(seed=7)
        self.kernel.activate()
        self.kernel.tick_simulation = lambda: None
        self.crook = self.kernel.register_player("crook", "Crook")
        self.mark = self.kernel.register_player("mark", "Mark")
        self.sol = self.kernel.sectors[1]

    def test_presence_is_highest_under_sols_guns_and_nil_in_anarchy(self):
        anarchy = next(s for s in self.kernel.sectors.values()
                       if law.authority(self.kernel, s) is not None and law.authority(self.kernel, s).id == "NONE")
        self.assertGreater(law.presence(self.kernel, self.sol), 0.7)
        self.assertEqual(law.presence(self.kernel, anarchy), 0.0)
        self.assertIsNone(law.file(self.kernel, "piracy", self.crook, anarchy, 5000, {"kind": "captain", "id": "mark"}))
        self.assertGreater(law.docket(self.kernel)["stats"]["haven"], 0)

    def test_a_conviction_recalls_money_from_the_wallet_to_victim_and_court(self):
        case = None
        for i in range(20):                         # presence at Sol is high but not certain
            case = law.file(self.kernel, "theft", self.crook, self.sol, 1000, {"kind": "captain", "id": "mark"})
            if case:
                break
        self.assertIsNotNone(case)
        self.crook.credits = 5000
        mark_before = self.mark.credits
        before = totals(self.kernel)
        law.quarter(self.kernel)
        self.assertEqual(before, totals(self.kernel))                  # transfers only
        self.assertEqual(self.mark.credits, mark_before + 1000)       # restitution
        self.assertEqual(self.crook.credits, 3000)                    # restitution + fine
        self.assertEqual(case["status"], "CLOSED")

    def test_void_savings_are_beyond_a_foreign_court(self):
        self.crook.credits = 0
        self.crook.fx_wallet["VOID"] = 1_000_000
        got = law.garnish(self.kernel, self.crook, 5000, "FEDERATION", "SOL")
        self.assertEqual(got, 0)
        self.assertEqual(self.crook.fx_wallet["VOID"], 1_000_000)

    def test_an_unpaid_judgment_freezes_trade_and_posts_a_bounty(self):
        case = None
        for i in range(20):
            case = law.file(self.kernel, "fraud", self.crook, self.sol, 4000, {"kind": "port", "id": 1})
            if case:
                break
        self.crook.credits = 0
        law.quarter(self.kernel)
        self.assertEqual(case["status"], "WARRANT")
        self.assertIn("FEDERATION", self.crook.frozen_by)
        self.assertGreater(self.crook.bounty, 0)
        self.kernel.sectors[self.crook.sector_id].captains.remove(self.crook.id)
        self.crook.sector_id = 1
        self.sol.captains.append(self.crook.id)
        res = self.kernel.dispatch("crook", ActionType.TRADE, type="BUY", commodity="ORE", amount=1)
        self.assertFalse(res.success)
        self.assertIn("FROZEN", res.message)
        # paying up lifts the freeze
        self.crook.credits = 100_000
        law.quarter(self.kernel)
        self.assertEqual(case["status"], "CLOSED")
        self.assertNotIn("FEDERATION", self.crook.frozen_by)

    def test_the_docket_balances(self):
        for i in range(40):
            law.file(self.kernel, "theft", self.crook, self.sol, 500, {"kind": "captain", "id": "mark"})
        self.crook.credits = 7000
        law.quarter(self.kernel)
        st = law.docket(self.kernel)["stats"]
        self.assertEqual(st["judged_sol"], st["recovered_sol"] + st["outstanding_sol"] + st["written_off_sol"])


if __name__ == "__main__":
    unittest.main()
