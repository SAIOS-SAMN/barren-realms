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
    def test_the_deepest_minds_keep_the_hub(self):
        depth = {"civ:Core": 400.0, "civ:Rim": 0.4}
        with mock.patch.object(gateways, "home_exposure", lambda k, w: depth[w]), \
                mock.patch.object(gateways, "travels_as_information", lambda k, w: False):
            self.assertEqual(gateways.hub_keeper(None, {"civ:Rim": 1, "civ:Core": 5}), "civ:Core")

    def test_minds_that_travel_as_information_take_any_wave(self):
        depth = {"civ:Core": 400.0, "civ:Rim": 0.4}
        with mock.patch.object(gateways, "home_exposure", lambda k, w: depth[w]), \
                mock.patch.object(gateways, "travels_as_information", lambda k, w: w == "civ:Rim"):
            self.assertEqual(gateways.hub_keeper(None, {"civ:Rim": 1, "civ:Core": 5}), "civ:Rim")


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
        before = settling.held(k, "civ:A", 1.0001)
        b["room"] = 1e10
        self.assertAlmostEqual(settling.held(k, "civ:A", 1.0001) - before, 1e10 * b["share"], delta=1.0)


if __name__ == "__main__":
    unittest.main()
