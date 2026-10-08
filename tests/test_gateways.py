"""
The fold stays local - as far as the nearest black hole - and the black holes carry everything farther. The centre's
throat is kept by the minds that evolved deepest in its wave; a new singularity costs the lightest black hole's
mass-energy and the ancients' approval.
"""
import math
import unittest
from unittest import mock

from xylarium.kernel import gateways


class TestFold(unittest.TestCase):
    def test_the_core_is_thick_with_mouths(self):
        self.assertGreater(gateways._bh_share(0.2), gateways._bh_share(8.0))          # its clouds are warm: top-heavy
        self.assertGreater(gateways.black_holes_per_pc3(0.2), 100 * gateways.black_holes_per_pc3(8.0))

    def test_a_fold_reaches_as_far_as_the_nearest_black_hole(self):
        self.assertLess(gateways.fold_reach_pc(0.17), 2.0)
        self.assertTrue(3.0 < gateways.fold_reach_pc(8.0) < 15.0, gateways.fold_reach_pc(8.0))
        self.assertGreater(gateways.fold_reach_pc(12.0), gateways.fold_reach_pc(8.0))
        n = gateways.black_holes_per_pc3(8.0)
        self.assertAlmostEqual(gateways.fold_reach_pc(8.0), 0.554 * n ** (-1 / 3), places=9)

    def test_the_wave_falls_off_from_the_core(self):
        self.assertAlmostEqual(gateways.exposure(8.0), 1.0)
        self.assertAlmostEqual(gateways.exposure(4.0), 4.0)


class TestHub(unittest.TestCase):
    def _contest(self, homes, nets, lines, transfer=()):
        from xylarium.kernel import board, spheres, steward_ai
        from xylarium.kernel import cosmos                   # a home's place: its 3D distance from the centre
        with mock.patch.object(gateways, "_r", lambda k, sid: homes[sid]), \
                mock.patch.object(cosmos, "from_centre_kpc", lambda k, sid: homes[sid]), \
                mock.patch.object(spheres, "_home", lambda k, w: mock.Mock(sector_id=w)), \
                mock.patch.object(gateways, "travels_as_information", lambda k, w: w in transfer), \
                mock.patch.object(spheres, "stats", lambda k: {"nets": nets}), \
                mock.patch.object(board, "progenitors", lambda k: {w: {} for w, ln in lines.items() if ln is None}), \
                mock.patch.object(steward_ai, "line_of", lambda k, w: lines.get(w)):
            return gateways.hub_keeper(None, {w: 1 for w in nets}), gateways.hub_contest(None, {w: 1 for w in nets})

    def test_the_line_whose_networks_carry_most_keeps_the_hub_through_a_people_that_bears_it(self):
        homes = {"civ:Core": 0.2, "civ:Rim": 9.0, "civ:Client": 1.5}
        nets = {"civ:Core": {"held": [1]}, "civ:Rim": {"held": list(range(50))}, "civ:Client": {"held": [2, 3]}}
        keeper, contest = self._contest(homes, nets, {"civ:Core": None, "civ:Rim": None, "civ:Client": "civ:Rim"})
        self.assertEqual(keeper, "civ:Client")                       # the Rim's line, through its bulge-born ward
        self.assertEqual(contest[0][0], "civ:Rim")

    def test_no_one_keeps_the_hub_while_no_one_bears_it(self):
        homes = {"civ:Rim": 9.0}
        keeper, _ = self._contest(homes, {"civ:Rim": {"held": [1]}}, {})
        self.assertIsNone(keeper)

    def test_minds_that_travel_as_information_bear_any_wave(self):
        homes = {"civ:Rim": 9.0}
        keeper, _ = self._contest(homes, {"civ:Rim": {"held": [1]}}, {}, transfer=("civ:Rim",))
        self.assertEqual(keeper, "civ:Rim")


class TestKindling(unittest.TestCase):
    def test_a_singularity_costs_the_lightest_black_holes_mass_energy(self):
        self.assertAlmostEqual(gateways.kindle_cost_j() / 5.36e47, 1.0, places=2)
        type_iii = 4e37                                       # a galaxy's whole starlight, W
        years = gateways.kindle_cost_j() / type_iii / 3.156e7
        self.assertTrue(100 < years < 1000, years)            # centuries of a galaxy's light: empire work

    def test_dominions_that_met_in_a_bond_are_one_coalition(self):
        from tests.test_settling import _bubble, _galaxy
        k = _galaxy({1: (8.0, 0.0), 2: (8.0, 0.5), 3: (8.0, 2.0)})
        _bubble(k, "civ:A", 1, 1.0)
        _bubble(k, "civ:B", 2, 1.0)
        _bubble(k, "civ:C", 3, 1.0)
        from xylarium.kernel import settling
        st = settling.stats(k)
        st["civ:A"]["cuts"]["civ:B"] = {"by": "civ:B", "a": 1.0, "t": 1.1, "style": "federation"}
        st["civ:B"]["cuts"]["civ:A"] = {"by": "civ:A", "a": 1.0, "t": 1.1, "style": "federation"}
        st["civ:A"]["cuts"]["civ:C"] = {"by": "civ:C", "a": 1.0, "t": 1.1, "style": "standoff"}
        self.assertEqual(gateways.coalitions(k, 1.2), [("civ:A", "civ:B"), ("civ:C",)])

    def test_kindled_room_is_held_beyond_the_white_hole(self):
        from tests.test_settling import _bubble, _galaxy
        from xylarium.kernel import settling
        k = _galaxy({1: (8.0, 0.0)})
        b = _bubble(k, "civ:A", 1, 1.0)
        with mock.patch("xylarium.kernel.cosmos.cosmos_seed", lambda kernel: 7):
            before = settling.held(k, "civ:A", 1.0001)
            b["children"] = [{"n": 1, "epoch": 1.0001, "room": 1e10}]
            self.assertAlmostEqual(settling.held(k, "civ:A", 1.0001), before, delta=1.0)   # at its own Big Bang: none
            self.assertEqual(settling.room_to_come(k, b, 1.0001), 1e10)                   # all of it still to come
            self.assertGreater(settling.room_formed(k, b, 3.0), 0.1e10)                   # its stars are forming,
            self.assertLess(settling.room_to_come(k, b, 3.0), 0.9e10)                     # inside-out, over Gyr
            self.assertTrue(settling.forming(k, b, 3.0))


class TestKindledThroat(unittest.TestCase):
    def test_kindling_opens_a_throat_not_a_one_way_room(self):
        from xylarium.kernel import blackhole
        from xylarium.kernel.engine import GameKernel
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        from tests.test_settling import _bubble
        b = _bubble(k, "civ:A", next(iter(k.sectors)), 1.0)
        gateways.stats(k)["banks"]["civ:A"] = {"j": gateways.kindle_cost_j() * 2, "t": 0.0}
        with mock.patch.object(gateways, "coalitions", lambda kernel, t: [("civ:A",)]), \
                mock.patch.object(gateways, "_full", lambda kernel, w, t: True), \
                mock.patch.object(gateways, "approves", lambda kernel, m: True), \
                mock.patch.object(gateways, "coalition_power_w", lambda kernel, m: 0.0), \
                mock.patch("xylarium.kernel.history.event", lambda *a, **kw: {}):
            gateways.kindling(k, [])
        tid = b["children"][0]["throat"]
        thr = blackhole.stats(k)["throats"][tid]
        self.assertEqual(thr["kind"], "kindled")
        self.assertIn("civ:A", thr["keepers"]["near"])
        self.assertEqual(thr["keepers"]["near"], thr["keepers"]["far"])     # the same keepers on both faces


if __name__ == "__main__":
    unittest.main()
