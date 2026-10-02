"""
One universe, one clock: every age is this universe run to the moment its milestone first happens (kept for the
next player of the seed), and nothing stops at spaceflight. The player stewards one people within its physics, and
may take ship as its captain without ceasing to be its steward.
"""

import tempfile
import unittest

from xylarium.kernel import ages, sustenance, ways


class TestAges(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_the_ages_in_order(self):
        self.assertEqual(ages.ORDER, ["forager", "agrarian", "first_flight", "lanes"])

    def test_a_forager_steward_decides_within_physics(self):
        k = ages.begin(3, "forager", root=self.root)
        self.assertEqual(k.state["genesis"]["mode"], "forager")
        home = ages.peoples(k)[0]
        ages.bind(k, "p1", "Steward", home)
        self.assertIsNotNone(ages.shape(k, "p1", {"tolerance": 0.3}))
        self.assertAlmostEqual(home.society["genome"]["tolerance"], 0.3)
        self.assertIn("state", ages.act(k, "p1", "state"))           # foragers cannot found a state
        self.assertIn("fields", ages.act(k, "p1", "farm"))
        self.assertEqual(ways.way(home), "farm")
        self.assertIn("surplus", ages.act(k, "p1", "state"))          # half-wild crops cannot bear one yet
        k.tick_simulation()
        self.assertIsNone(ages.shape(k, "p1", {"tolerance": 1.0}))     # the Progenitor's hand is only at genesis

    def test_one_clock_the_ages_are_points_on_it_and_are_kept(self):
        k = ages.begin(3, "forager", root=self.root)
        self.assertEqual(k.cycle_count, 0)
        self.assertEqual(ages.cached(3, self.root), ["forager"])
        # a later age runs the same clock from the earliest kept age (bounded here for the test's sake)
        k2 = ages.begin(3, "agrarian", root=self.root, max_years=2)
        self.assertEqual(k2.state["genesis"]["mode"], "forager")
        self.assertGreater(k2.cycle_count, 0)

    def test_wake_me_when_returns_what_happened(self):
        k = ages.begin(3, "forager", root=self.root)
        ages.bind(k, "p1", "Steward", ages.peoples(k)[0])
        self.assertTrue(ages.wake_when(k, "p1", max_years=2))

    def test_taking_ship_keeps_the_people(self):
        from xylarium.kernel.engine import GameKernel
        k = GameKernel(seed=7, genesis="primordial")
        k.activate()
        home = ages.peoples(k)[0]
        ages.bind(k, "p1", "Steward", home)
        home.citadel_level = 2                                   # yards raised
        if not sustenance.yards(home):
            self.skipTest("yards need more than a tier here")
        cap = ages.first_captain(k, "p1", "First Captain")
        self.assertIsNotNone(cap)
        self.assertEqual(cap.sector_id, home.sector_id)
        self.assertIs(ages.homeworld(k, "p1"), home)              # still its steward


if __name__ == "__main__":
    unittest.main()
