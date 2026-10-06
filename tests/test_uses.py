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


class TestHulls(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        self.k.activate()

    def test_a_crews_hull_is_what_holds_at_its_warmth_and_melts_back_to_itself(self):
        from xylarium.kernel import chemistry, matter, propulsion
        from xylarium.kernel.economy import EconomyManager
        cap = next(iter(self.k.captains.values()))
        cap.metabolism = "cryogenic"
        sol = self.k.sectors[cap.sector_id] if self.k.sectors[cap.sector_id].port else self.k.sectors[1]
        EconomyManager.ensure_port_inventory(sol.port)
        for g in uses.structural(0.0):
            sol.port.stock[g] = 0
        sol.port.stock["H2O"] = 10_000                           # only ice on the shelves
        chemistry.stats(self.k)["known"][f"captain:{cap.id}"] = sorted(chemistry.TABLE)
        self.assertLess(uses.captain_body(self.k, cap)["t"], 273.16)
        short = propulsion.refit(self.k, sol, cap.ship.ship_type, "Merchant Cruiser", cap.ship, cap)
        self.assertFalse(short)
        self.assertEqual(set(cap.ship.hull_matter), {"H2O"})      # an ice hull for a cold-blooded crew
        built = cap.ship.hull_matter["H2O"]
        before = sol.port.stock["H2O"]
        propulsion.refit(self.k, sol, "Merchant Cruiser", "Merchant Cruiser", cap.ship, cap)
        self.assertEqual(sol.port.stock["H2O"], before + built - sum(cap.ship.hull_matter.values()))

    def test_a_district_is_built_of_what_holds_where_it_stands_and_returns_as_itself(self):
        from xylarium.kernel import chemistry
        from xylarium.kernel.surface import SurfaceManager, DistrictType
        w = max((p for s in self.k.sectors.values() for p in s.planets if p.population > 0),
                key=lambda p: p.population)
        cap = next(iter(self.k.captains.values()))
        w.owner_id = cap.id
        cap.credits = 10 ** 6
        for g in uses.structural(0.0):
            w.element_reserves.pop(g, None)
        w.ore_silo = 0
        port = self.k.sectors[w.sector_id].port
        if port is not None:
            for g in uses.structural(0.0):
                port.stock[g] = 0
        w.element_reserves["H2O"] = 500
        chemistry.stats(self.k)["known"][uses.holder_of(w)] = sorted(chemistry.TABLE)
        grid = SurfaceManager.ensure_surface_grid(w)
        tile = next(t for t in grid.tiles if t.district == DistrictType.EMPTY)
        with mock.patch.object(uses, "site_t", return_value=218.0):           # a cold people on a cold world
            r = SurfaceManager.build_district(cap, w, tile.x, tile.y, DistrictType.HYDROPONIC_SPIRE)
        self.assertTrue(r.success, r.message)
        self.assertEqual(w.society["built_of"][f"{tile.x},{tile.y}"], {"H2O": 25})
        self.assertEqual(w.element_reserves["H2O"], 475)
        r = SurfaceManager.demolish_district(cap, w, tile.x, tile.y)
        self.assertEqual(r.data["salvage_matter"], {"H2O": 12})              # its ice back, not ore
        with mock.patch.object(uses, "site_t", return_value=worlds.body_temperature("H2O")):
            r = SurfaceManager.build_district(cap, w, tile.x, tile.y, DistrictType.HYDROPONIC_SPIRE)
        self.assertFalse(r.success)                                          # ice melts at a water-born site

    def test_a_citadel_is_mended_with_what_it_is_made_of(self):
        w = max((p for s in self.k.sectors.values() for p in s.planets if p.population > 0),
                key=lambda p: p.population)
        w.society["citadel_of"] = {"H2O": 120, "ORE": 5}
        self.assertEqual(uses.wears(self.k, w), "H2O")
        w.element_reserves["H2O"] = 10
        self.assertEqual(uses.take(w, "H2O", 3, "citadel_upkeep"), 3)
        self.assertEqual(w.element_reserves["H2O"], 7)
        w.society.pop("citadel_of")
        with mock.patch.object(uses, "site_t", return_value=worlds.body_temperature("plasma")):
            self.assertIsNone(uses.wears(self.k, w))                     # nothing holds: no walls to mend


if __name__ == "__main__":
    unittest.main()
