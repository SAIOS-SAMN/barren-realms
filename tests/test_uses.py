"""
Uses: a good is matter; what it is for comes from the people who meet it. A people's medium is what its chemistry runs
in; what it builds with is what holds a shape at the temperature it stands at - so ammonia-born builders raise ice,
water-born ones cannot, and a plasma-born people has no matter that holds a shape at all.
"""

import random
import unittest
from unittest import mock

from xylarium.kernel import tourism, uses, worlds
from xylarium.kernel.engine import GameKernel


class TestUses(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        self.k.activate()
        self.w = max((p for s in self.k.sectors.values() for p in s.planets if p.population > 0),
                     key=lambda p: p.population)

    def test_what_holds_a_shape_is_read_from_the_temperature_it_stands_at(self):
        ammonia = worlds.body_temperature("NH3")
        water = worlds.body_temperature("H2O")
        self.assertIn("H2O", uses.structural(ammonia))           # water ice is rock to an ammonia-born body
        self.assertNotIn("H2O", uses.structural(water))          # and melts at a water-born body's warmth
        self.assertIn("Fe", uses.structural(water))
        self.assertEqual(uses.structural(worlds.body_temperature("plasma")), [])   # nothing holds in plasma
        self.assertNotIn("Fe", uses.structural(worlds.body_temperature("melt")))   # iron melts in a melt-born body

    def test_a_medium_is_the_good_its_matter_is_laid_down_as(self):
        self.assertEqual(uses.MEDIUM_GOOD["H2O"], "H2O")
        self.assertEqual(uses.MEDIUM_GOOD["NH3"], "cryogenite")
        self.assertNotIn("CH4", uses.MEDIUM_GOOD)                # no good holds methane as a liquid yet

    def test_a_body_is_read_from_its_people_never_declared(self):
        civ = self.w.civilization
        was = getattr(civ, "traits", None)
        civ.traits = {"solvent": "NH3", "body_t": 218.0}           # recorded when its mind arose
        try:
            self.assertEqual(uses.body(self.k, self.w), {"solvent": "NH3", "t": 218.0})
            self.assertEqual(uses.medium(self.k, self.w), "cryogenite")
        finally:
            civ.traits = was
        self.assertIn("H2O", uses._region_solvents("biotic"))
        self.assertEqual(uses._region_solvents("plasmic"), ["plasma"])

    def test_a_hull_is_built_from_the_cheapest_matter_that_holds_at_its_peoples_warmth(self):
        port = self.k.sectors[self.w.sector_id].port
        if port is None:
            self.skipTest("no yards here")
        for g in uses.structural(218.0):
            self.w.element_reserves.pop(g, None)
        self.w.ore_silo = 0
        self.w.element_reserves["H2O"] = 500                      # its own ice
        hull = uses.build_with(self.k, self.w, 218.0, 90)
        self.assertEqual(hull, [("H2O", 90)])                    # its own ice, nothing bought
        water_hull = uses.build_with(self.k, self.w, worlds.body_temperature("H2O"), 90)
        self.assertNotIn("H2O", [g for g, _ in water_hull])

    def test_a_dome_holds_its_peoples_own_medium(self):
        from xylarium.kernel import demand
        self.w.society["surface_grid"] = None
        self.w.element_reserves.pop("cryogenite", None)
        self.w.society.pop("wants", None)
        with mock.patch.object(tourism, "resorts", return_value=1), \
                mock.patch.object(uses, "body", return_value={"solvent": "NH3", "t": 218.0}):
            tourism._fill_resorts(self.k, self.w)
        self.assertTrue(self.w.society.get("resort_dry"))
        self.assertIn("cryogenite", demand.wants(self.w))        # its dome wants ammonia ices, not water
        self.assertNotIn("H2O", demand.wants(self.w))


if __name__ == "__main__":
    unittest.main()
