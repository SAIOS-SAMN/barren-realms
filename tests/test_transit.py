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

    def test_a_fallen_keepers_throat_lies_dormant_and_open_until_a_master_salvages_it(self):
        transit.open_throat(self.k, self.a, self.b, "civ:Gone", "forged", 1.0, "test")
        transit.stats(self.k)["masters"]["civ:Gone"] = 0
        transit._heirs(self.k, [])
        w = transit.worm(self.k, self.a, self.b)
        self.assertTrue(w["dormant"] is not None and w["owner"] is None)   # unused, it holds - no one keeps it
        self.assertFalse(transit.refuses(self.k, self.cap, self.a, self.b))  # a progenitor wormhole: dormant, open
        self.assertNotIn("civ:Gone", transit.stats(self.k)["masters"])
        spheres.ensure(self.k)
        end, heir = next((int(s), spheres.presence(self.k, r)) for s, r in sorted(spheres.stats(self.k)["owner"].items()))
        transit.open_throat(self.k, end, self.b, "civ:Gone", "forged", 1.0, "test")
        transit.stats(self.k)["masters"][heir] = 1
        transit._heirs(self.k, [])
        self.assertEqual(transit.worm(self.k, end, self.b)["owner"], heir)  # salvaged: its mouth is in their network

    def test_an_unready_hand_on_a_dormant_mouth_collapses_the_string_through_it(self):
        a, m, c = sorted(self.k.sectors)[:3]
        for x, y in ((a, m), (m, c)):
            w = transit.open_throat(self.k, x, y, "civ:Gone", "forged", 1.0, "test")
            w.update(owner=None, keeper="civ:Gone", dormant=0, handling="closed")
        n = transit.collapse_mouth(self.k, a, "test")
        self.assertEqual(n, 2)                                    # a-m fell, and m's only other throat was dormant
        self.assertIsNone(transit.worm(self.k, m, c))

    def test_mouths_are_black_holes(self):
        sid = sorted(self.k.sectors)[3]
        self.k.sectors[sid].star_type = "Black hole remnant"
        self.assertEqual(transit.mouths(self.k)[sid]["kind"], "stellar")


class TestHypha(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)

    def test_the_chain_answers_for_itself_and_a_changed_receipt_breaks_it(self):
        from xylarium.kernel import hypha
        hypha.append(self.k, "SOL", "pouw", "captain:a", "civ:B", 120, "SOL", ref="1-3")
        hypha.append(self.k, "SOL", "pouw", "captain:c", "civ:B", 30, "SOL", ref="1-3")
        self.assertTrue(hypha.verify(self.k, "SOL"))
        hypha.stats(self.k)["chains"]["SOL"]["rows"][0]["amount"] = "1"
        self.assertFalse(hypha.verify(self.k, "SOL"))

    def test_a_fold_writes_each_identitys_net_and_the_chain_goes_on(self):
        from fractions import Fraction
        from xylarium.kernel import hypha
        hypha.append(self.k, "SOL", "pouw", "captain:a", "civ:B", 120, "SOL")
        hypha.append(self.k, "SOL", "pouw", "civ:B", "captain:a", 20, "SOL")
        head = hypha.stats(self.k)["chains"]["SOL"]["head"]
        rec = hypha.fold(self.k, "SOL")
        c = hypha.stats(self.k)["chains"]["SOL"]
        self.assertEqual(rec["ref"], head)                        # the fold cites the prefix it closed
        self.assertEqual(Fraction(c["net"]["civ:B"]), 100)        # closed circulation vanishes in the net
        self.assertEqual(Fraction(c["net"]["captain:a"]), -100)
        self.assertEqual(c["height"], 3)
        hypha.append(self.k, "SOL", "pouw", "captain:a", "civ:B", 5, "SOL")
        self.assertTrue(hypha.verify(self.k, "SOL"))

    def test_a_settlement_is_a_proof_of_useful_work_on_the_keepers_reserve(self):
        from xylarium.kernel import hypha
        spheres.ensure(self.k)
        who = next(iter(spheres.stats(self.k)["nets"]))
        a = spheres.stats(self.k)["nets"][who]["home"]
        b = next(w for w in self.k.sectors[a].warps if w in self.k.sectors)
        transit.settle(self.k, who, "captain:x", a, b, 50.0, 10.0)
        cur = spheres._home(self.k, who).currency
        rows = hypha.stats(self.k)["chains"][cur]["rows"]
        self.assertEqual((rows[-1]["kind"], rows[-1]["payee"], rows[-1]["ref"]), ("pouw", who, transit.key(a, b)))


class TestAllTrafficPays(unittest.TestCase):
    def test_flows_pay_what_a_lane_charges_and_a_war_blockades_it(self):
        k = GameKernel(seed=42)
        spheres.ensure(k)
        a = sorted(k.sectors)[0]
        b = next(w for w in k.sectors[a].warps if w in k.sectors)
        with mock.patch.object(transit, "charge_cr", return_value=("civ:Keeper", 7.0, 3.0)):
            self.assertEqual(transit.flow_passage(k, "captain:x", a, b, transits=4), 40.0)
            self.assertEqual(transit.flow_passage(k, "civ:Keeper", a, b), 0.0)     # its own pass free
        with mock.patch.object(transit, "owner", return_value="civ:Keeper"), \
                mock.patch.object(transit, "at_war", side_effect=lambda kk, x, y: {x, y} == {"civ:Keeper", "civ:Foe"}):
            self.assertTrue(transit.blocks(k, "civ:Foe", a, b))
            self.assertFalse(transit.blocks(k, "civ:Friend", a, b))


if __name__ == "__main__":
    unittest.main()
