"""
The laws beneath the funnel: a universe's few dimensionless constants and what follows from them (fundamental.py),
a world's interior heat and tides (interior.py), its orbit in all six elements and its spin (orbits.py), curved
space and slowed clocks (geometry.py), and life as information written against erasure (life.py). Our universe's
laws reproduce our measurements to within their physics; other laws move every layer together.
"""

import math
import unittest

from xylarium.kernel import creation, fundamental, geometry, interior, life, orbits, worlds

SUN = {"mass": "1", "luminosity": "1"}


class TestFundamental(unittest.TestCase):
    def test_our_laws_are_the_unit_of_every_scale(self):
        L = fundamental.of(7)
        self.assertTrue(L.ours)
        for v in (L.chem, L.star_mass, L.star_lum, L.star_life, L.star_radius, L.density, L.coincidence()):
            self.assertAlmostEqual(v, 1.0, places=12)
        self.assertEqual(L.tag(), "")

    def test_the_creation_key_carries_the_laws(self):
        L = fundamental.of("7:measured:alpha=1.05,alpha_G=0.8")
        self.assertAlmostEqual(L.ratios["alpha"], 1.05)
        self.assertAlmostEqual(L.ratios["alpha_G"], 0.8)
        self.assertGreater(L.star_mass, 1.0)                               # weaker gravity: heavier stars
        self.assertGreater(fundamental.of("7:measured:alpha=1.05").chem, 1.0)   # stronger bonds: hotter boiling
        self.assertEqual(creation.big_bang("7:measured:alpha=1.05")["sigma8"], creation.big_bang(7)["sigma8"])

    def test_stronger_electromagnetism_moves_every_layer_together(self):
        L = fundamental.Laws({"alpha": 1.05})
        self.assertGreater(worlds.boiling("H2O", 1.0, L), worlds.boiling("H2O", 1.0))
        self.assertGreater(worlds.body_temperature("H2O", L), worlds.body_temperature("H2O"))
        self.assertGreater(L.star_life, 1.0)                               # a star's opacity rises: it burns slower
        self.assertGreater(interior.half_life("U238", L), 10 * interior.half_life("U238"))   # Gamow's barrier
        self.assertEqual(interior.half_life("K40", L), interior.half_life("K40"))            # beta decay: not alpha's
        self.assertLess(L.coincidence(), 1.0)                              # starlight colder than its chemistry

    def test_starlight_drives_chemistry_only_in_its_colours(self):
        sun, red, blue = worlds.band(5772), worlds.band(3000), worlds.band(20000)
        self.assertTrue(0.4 < sun["drive"] < 0.7)
        self.assertLess(red["drive"], sun["drive"])                        # a red dwarf's light is mostly warmth
        self.assertGreater(blue["break"], sun["break"])                    # a hot star's breaks bonds


class TestInterior(unittest.TestCase):
    def test_the_solar_system_from_rock_physics(self):
        inv = interior.inventory(None, 8.0, interior.SUN_BORN_GYR, 1.0, fundamental.OUR_LAWS)
        earth = interior.evolve(1.0, 1.0, 0.32, inv, 4.57, 250, laws=fundamental.OUR_LAWS)
        mars = interior.evolve(0.107, 0.53, 0.24, inv, 4.57, 210, laws=fundamental.OUR_LAWS)
        young_mars = interior.evolve(0.107, 0.53, 0.24, inv, 0.5, 210, laws=fundamental.OUR_LAWS)
        moon = interior.evolve(0.0123, 0.27, 0.02, inv, 4.57, 250, laws=fundamental.OUR_LAWS)
        self.assertTrue(0.03 < earth["q"] < 0.12)                          # W/m^2 (measured 0.087)
        self.assertTrue(0.015 < earth["q_rad"] < 0.06)                     # ~20 TW radiogenic
        self.assertLess(mars["q"], earth["q"])
        self.assertGreater(young_mars["field"], 0.5)                       # Mars had a dynamo once
        self.assertEqual(moon["field"], 0.0)

    def test_tides_heat_moons_in_resonance(self):
        io = interior.tidal_w(1.898e27, 4.217e8, 0.0041, 0.015, 0.286, False)
        europa = interior.tidal_w(1.898e27, 6.709e8, 0.009, 0.008, 0.245, True)
        self.assertTrue(5e11 < io < 1e13)                                  # TW scale
        self.assertTrue(1e11 < europa < 5e12)
        self.assertEqual(interior.tidal_w(1.898e27, 6.709e8, 0.0, 0.008, 0.245, True), 0.0)

    def test_a_young_galaxy_is_rich_in_short_lived_isotopes(self):
        early = interior.inventory(None, 8.0, 2.0, 1.0, fundamental.OUR_LAWS)
        late = interior.inventory(None, 8.0, 12.0, 1.0, fundamental.OUR_LAWS)
        self.assertGreater(early["U235"] / early["U238"], late["U235"] / late["U238"])


class TestOrbits(unittest.TestCase):
    def test_packed_systems_are_calm_and_only_non_crossing_orbits_survive(self):
        import random
        star = interior.M_SUN_KG
        ws = [{"a_au": a, "mass": 1.0, "radius": 1.0} for a in (0.5, 0.7, 1.0, 1.4)]
        els = orbits.system(star, ws, 1.0, random.Random(3))
        for n, el in enumerate(els):
            for k in (n - 1, n + 1):
                if 0 <= k < len(ws):
                    a1, a2 = sorted((ws[n]["a_au"], ws[k]["a_au"]))
                    self.assertLessEqual(el["e0"], (a2 - a1) / (a2 + a1) / 2 + 1e-12)

    def test_close_worlds_of_small_stars_lock(self):
        el = {"e0": 0.0, "e_forced": 0.0, "spin_share": 0.3, "obliquity": 1.0, "inc": 0.0, "node": 0.0, "peri": 0.0}
        w = {"mass": 1.0, "radius": 1.0}
        near = dict(el, **orbits.spin(0.2 * interior.M_SUN_KG, 0.05 * interior.AU_M, w, el))
        far = dict(el, **orbits.spin(interior.M_SUN_KG, 1.0 * interior.AU_M, w, el))
        self.assertTrue(orbits.at(0.2 * interior.M_SUN_KG, 0.05 * interior.AU_M, near, 3.0)["locked"])
        self.assertFalse(orbits.at(interior.M_SUN_KG, interior.AU_M, far, 3.0)["locked"])

    def test_giants_gather_moons(self):
        import random
        ms = orbits.moons(318.0, 11.0, 0.5, random.Random(5))
        self.assertTrue(ms)
        self.assertLess(sum(m["mass"] for m in ms), 318.0 * orbits.MOON_SHARE * 1.0001)


class TestGeometry(unittest.TestCase):
    def test_space_is_a_sphere_and_close_by_it_is_flat(self):
        r = geometry.radius_kpc(7)
        a, b = geometry.embed([1000.0, 0, 0], r), geometry.embed([0, 1000.0, 0], r)
        self.assertAlmostEqual(geometry.arc_kpc(a, b, r), math.hypot(1000, 1000), delta=0.01)
        far = geometry.embed([math.pi * r, 0, 0], r)                       # half way round: the antipode
        self.assertAlmostEqual(geometry.arc_kpc(geometry.embed([0, 0, 0], r), far, r), math.pi * r, delta=1.0)

    def test_clocks_run_slow_in_the_well_and_rulers_stretch(self):
        self.assertLess(geometry.lapse(0.5), geometry.lapse(14.0))
        self.assertLess(1.0 - geometry.lapse(0.5), 1e-4)                   # but only by parts in a million
        self.assertGreater(geometry.proper_kpc([8, 0, 0], [-8, 0, 0]), 16.0)

    def test_old_stars_ride_further_from_the_plane(self):
        young = geometry.vertical(8.0, 1.0, 0.5, 0.0)
        old = geometry.vertical(8.0, 10.0, 0.5, 0.0)
        self.assertGreater(old["amp_kpc"], young["amp_kpc"])
        self.assertLess(old["exposure"], young["exposure"])


class TestLifeAsInformation(unittest.TestCase):
    def test_rungs_come_from_the_chemistry(self):
        water = life.ladder({"solvent": "H2O", "t": 290, "richness": 0.4, "energy": 0.3}, 5e14)
        methane = life.ladder({"solvent": "CH4", "t": 100, "richness": 0.4, "energy": 0.001}, 5e14)
        self.assertTrue(water["complete"] and methane["complete"])
        self.assertLess(len(water["steps"]), len(methane["steps"]))        # weaker bonds: more proofreading
        self.assertIsNone(life.ladder({"solvent": "plasma", "t": 1e4, "richness": 0.01, "energy": 1.0}, 5e14))

    def test_no_universe_draws_how_common_life_is(self):
        for name in ("ORIGIN_GYR", "HARDEN", "TRANSFER_GYR", "ENERGY_HALF", "STEPS_RANGE", "STEP_LOG_RANGE"):
            self.assertFalse(hasattr(creation, name), name)

    def test_the_sum_of_waits(self):
        self.assertAlmostEqual(life.sum_cdf([1.0], 1.0), 1 - math.exp(-1), places=6)
        self.assertLess(life.sum_cdf([1.0, 1.0], 1.0), life.sum_cdf([1.0], 1.0))


if __name__ == "__main__":
    unittest.main()
