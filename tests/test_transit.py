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
                mock.patch.object(transit, "_around", return_value=fibres.base_lane_cost(self.k, a, b) + 3):
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
                mock.patch.object(transit, "_around", return_value=fibres.base_lane_cost(self.k, a, b)):
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


class TestRoutesWeighTolls(unittest.TestCase):
    def test_a_route_goes_round_a_lane_whose_toll_costs_more_than_the_hops_it_saves(self):
        random.seed(5)
        k = GameKernel(seed=42)
        a = sorted(k.sectors)[0]
        b = next(w for w in k.sectors[a].warps if w in k.sectors)
        base = fibres.base_lane_cost(k, a, b)
        self.assertEqual(fibres.lane_cost(k, a, b), base + transit.charge_hops(k, a, b))
        with mock.patch.object(transit, "charge_hops", side_effect=lambda kk, x, y: 1e6 if {x, y} == {a, b} else 0.0):
            from xylarium.kernel import cache
            cache.clear(k)
            fibres._bump(k)
            path = fibres.geodesic(k, a, b)
        if transit._around(k, a, b) != float("inf"):
            self.assertNotEqual(path, [a, b])                 # it pays to go round


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
        self.assertEqual(fibres.base_lane_cost(self.k, self.a, self.b), fibres.MIN_COST)   # one hop through the bounce
        self.assertGreater(fibres.lane_cost(self.k, self.a, self.b), fibres.MIN_COST)     # routes weigh its tithe
        self.assertGreater(transit.tithe_cr(self.k, self.a, self.b), 0)
        self.assertFalse(transit.refuses(self.k, self.cap, self.a, self.b))
        w["handling"] = "guarded"
        self.assertEqual(fibres.base_lane_cost(self.k, self.a, self.b), float("inf"))   # not on the shared routes
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

    def test_a_galaxy_beyond_stays_unwitnessed_until_a_ship_passes(self):
        from xylarium.kernel import cluster
        gals = cluster.stats(self.k).get("galaxies") or []
        if len(gals) < 2:
            cluster.stats(self.k)["galaxies"] = [{"name": "home", "mass": 1, "dist_kpc": 0},
                                                 {"name": "Far", "mass": 1e10, "dist_kpc": 700.0}]
        heart = transit.MOUTH_BASE + 1
        transit.open_throat(self.k, self.a, heart, "civ:Holder", "intergalactic", 1.0, "test")
        self.assertNotIn(heart, self.k.sectors)                # a formula until witnessed
        self.assertTrue(transit.admits(self.k, self.cap, self.a, heart))
        self.assertIn(heart, self.k.sectors)                   # the passage is the observation
        self.assertIn(self.a, self.k.sectors[heart].warps)

    def test_a_fallen_keepers_throat_passes_to_a_living_master_or_collapses(self):
        transit.open_throat(self.k, self.a, self.b, "civ:Gone", "forged", 1.0, "test")
        transit.stats(self.k)["masters"]["civ:Gone"] = 0
        transit._heirs(self.k, [])
        self.assertIsNone(transit.worm(self.k, self.a, self.b))          # no one to hold the bounce open
        self.assertNotIn(self.b, self.k.sectors[self.a].warps)
        self.assertNotIn("civ:Gone", transit.stats(self.k)["masters"])
        spheres.ensure(self.k)
        heir = spheres.presence(self.k, spheres.owner(self.k, next(iter(sorted(
            int(s) for s in spheres.stats(self.k)["owner"])))))
        end = next(s for s in sorted(int(x) for x in spheres.stats(self.k)["owner"])
                   if spheres.presence(self.k, spheres.owner(self.k, s)) == heir)
        transit.open_throat(self.k, end, self.b, "civ:Gone", "forged", 1.0, "test")
        transit.stats(self.k)["masters"][heir] = 1
        transit._heirs(self.k, [])
        self.assertEqual(transit.worm(self.k, end, self.b)["owner"], heir)   # its mouth lies in the heir's network

    def test_mouths_are_black_holes(self):
        sid = sorted(self.k.sectors)[3]
        self.k.sectors[sid].star_type = "Black hole remnant"
        self.assertEqual(transit.mouths(self.k)[sid]["kind"], "stellar")


if __name__ == "__main__":
    unittest.main()
