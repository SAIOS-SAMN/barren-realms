"""
Transit: the networks' lanes are tolled by what they are worth to the one passing (never a set fee); the Einstein-
Cartan fabric's throats join mouth to mouth, handled as their holders choose; progenitor lines forge throats from
the energy their networks bank.
"""

import random
import unittest
from unittest import mock

from xylarium.kernel import fibres, spheres, transit
from xylarium.kernel.engine import GameKernel


class TestTolls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        random.seed(5)
        cls.k = GameKernel(seed=42)
        for _ in range(2 * 100):
            cls.k.tick_simulation()
        cls.cap = next(c for c in cls.k.captains.values() if c.is_ai)

    def _held_lane(self):
        for sid, sec in sorted(self.k.sectors.items()):
            for w in sec.warps:
                if w in self.k.sectors and transit.owner(self.k, sid, w):
                    return sid, w
        self.skipTest("no network holds a lane yet")

    def test_a_toll_lies_between_what_the_lane_cost_and_what_it_saves(self):
        a, b = self._held_lane()
        with mock.patch.object(transit, "_payer", return_value="captain:nobody"), \
                mock.patch.object(transit, "_around", return_value=fibres.lane_cost(self.k, a, b) + 3):
            q = transit.quote(self.k, self.cap, a, b)
        self.assertLessEqual(q["toll"], q["ceiling"])                 # never more than going round
        self.assertAlmostEqual(q["ceiling"], 3 * transit.hop_value(self.k, self.cap), places=6)
        if q["ceiling"] > q["floor"]:
            self.assertAlmostEqual(q["toll"], q["floor"] + (q["ceiling"] - q["floor"]) / 2)

    def test_its_own_people_and_free_bonds_pass_free_and_a_lane_that_saves_nothing_costs_nothing(self):
        a, b = self._held_lane()
        holder = transit.owner(self.k, a, b)
        with mock.patch.object(transit, "_payer", return_value=holder):
            self.assertEqual(transit.quote(self.k, self.cap, a, b)["toll"], 0.0)
        rec = transit.lane(self.k, a, b)
        rec["collected"] = rec["cost_cr"]                             # paid off: no floor left
        with mock.patch.object(transit, "_payer", return_value="captain:nobody"), \
                mock.patch.object(transit, "_around", return_value=fibres.lane_cost(self.k, a, b)):
            self.assertEqual(transit.quote(self.k, self.cap, a, b)["toll"], 0.0)

    def test_what_a_network_collects_pays_for_its_passages(self):
        transit.stats(self.k)["revenue"]["civ:Test"] = 3 * transit.passage_cr(self.k)
        self.assertAlmostEqual(float(transit.drain_revenue(self.k, "civ:Test")), 3.0)
        self.assertEqual(transit.drain_revenue(self.k, "civ:Test"), 0)

    def test_a_fold_costs_the_energy_it_takes_at_energys_price(self):
        from xylarium.kernel import research
        with mock.patch.object(research, "can_fold", return_value=True), \
                mock.patch("xylarium.kernel.knowledge.captain_mastery", return_value=0.5):
            self.assertEqual(research.jump_cost(self.k, self.cap), max(1, int(transit.passage_cr(self.k) / 0.5)))


class TestThroats(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        self.cap = next(c for c in self.k.captains.values() if c.is_ai)
        self.a, self.b = sorted(self.k.sectors)[0], sorted(self.k.sectors)[-1]

    def test_a_throat_is_one_hop_through_the_bounce_and_its_holder_decides_who_passes(self):
        w = transit.open_throat(self.k, self.a, self.b, "civ:Holder", "forged", 1000.0, "test")
        self.assertIn(self.b, self.k.sectors[self.a].warps)
        w["handling"] = "tolled"
        self.assertEqual(fibres.lane_cost(self.k, self.a, self.b), fibres.MIN_COST)
        self.assertFalse(transit.refuses(self.k, self.cap, self.a, self.b))
        w["handling"] = "guarded"
        self.assertEqual(fibres.lane_cost(self.k, self.a, self.b), float("inf"))   # not on the shared routes
        self.assertTrue(transit.refuses(self.k, self.cap, self.a, self.b))
        with mock.patch.object(transit, "_payer", return_value="civ:Holder"):
            self.assertFalse(transit.refuses(self.k, self.cap, self.a, self.b))    # its own pass
        w["handling"] = "closed"
        with mock.patch.object(transit, "_payer", return_value="civ:Holder"):
            self.assertTrue(transit.refuses(self.k, self.cap, self.a, self.b))

    def test_an_open_throat_asks_only_what_it_cost(self):
        w = transit.open_throat(self.k, self.a, self.b, "civ:Holder", "forged", 1000.0, "test")
        w["handling"] = "open"
        with mock.patch.object(transit, "_payer", return_value="captain:x"):
            q = transit.quote(self.k, self.cap, self.a, self.b)
        self.assertEqual(q["toll"], min(q["floor"], q["ceiling"]))

    def test_a_line_forges_only_with_the_energy_its_network_banked(self):
        spheres.ensure(self.k)
        who = next(iter(spheres.stats(self.k)["nets"]))
        net = spheres.stats(self.k)["nets"][who]
        anchor, target = net["home"], next(s for s in sorted(self.k.sectors) if s != net["home"])
        cost = transit.forge_cost_j(self.k, who, anchor, target)
        net["bank_j"] = cost / 2
        self.assertIsNone(transit.forge(self.k, who, anchor, target, []))
        net["bank_j"] = cost * 1.5
        w = transit.forge(self.k, who, anchor, target, [])
        self.assertEqual(w["owner"], who)
        self.assertAlmostEqual(net["bank_j"], cost / 2)

    def test_mouths_are_black_holes(self):
        sid = sorted(self.k.sectors)[3]
        self.k.sectors[sid].star_type = "Black hole remnant"
        self.assertEqual(transit.mouths(self.k)[sid]["kind"], "stellar")


if __name__ == "__main__":
    unittest.main()
