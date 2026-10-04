"""
Waste: what a people's work leaves in its world, kept by the world's own seas and sky, felt through its own
greenhouse and its people's own tuning - no world's story written in.
"""

import random
import unittest

from xylarium.kernel import waste, worlds
from xylarium.kernel.engine import GameKernel


class TestWaste(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        random.seed(5)
        cls.k = GameKernel(seed=7)
        cls.k.activate()
        cls.terra = next(p for s in cls.k.sectors.values() for p in s.planets if p.name.lower().startswith("terra"))
        cls.w = worlds.state_of_planet(cls.k, cls.terra)["world"]

    def test_seas_take_up_part_of_a_soluble_gas_and_none_of_one_that_rains_out(self):
        self.assertLess(waste.kept_share(self.w, "CO2"), 1.0)
        self.assertGreater(waste.kept_share(self.w, "CO2"), 0.0)
        self.assertEqual(waste.kept_share(self.w, "H2O"), 0.0)          # it condenses at this world's temperature
        dry = dict(self.w, seas={})
        self.assertEqual(waste.kept_share(dry, "CO2"), 1.0)            # no seas: the sky keeps it all

    def test_a_kept_greenhouse_gas_warms_the_world_and_its_own_seas_warm_it_further(self):
        r = waste.warming(self.w, {"CO2": 3e-4})
        self.assertGreater(r, 1.0)
        no_feedback = dict(self.w, seas={})
        self.assertLess(waste.warming(no_feedback, {"CO2": 3e-4}), r)  # the sea's vapour answers the warmth

    def test_waste_heat_warms_and_nothing_added_changes_nothing(self):
        self.assertEqual(waste.warming(self.w, {}), 1.0)
        self.assertGreater(waste.warming(self.w, {}, heat_w_m2=1.0), 1.0)

    def test_the_room_lost_is_read_through_the_peoples_own_tuning(self):
        if self.terra.civilization is None:
            self.skipTest("no people on Terra")
        self.assertEqual(waste.room(self.k, self.terra, 1.0), 1.0)
        self.assertNotEqual(waste.room(self.k, self.terra, 1.05), 1.0)


if __name__ == "__main__":
    unittest.main()
