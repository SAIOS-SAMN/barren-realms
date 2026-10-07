"""Radiation as food and harm: the galaxy's cosmic rays, radiolysis, the split of erasing events, and the band a
people's home sets on where it can keep a colony."""

import unittest

from xylarium.kernel import cosmos, hydromagnetics, life, physics, settling, worlds


def _icy(r_kpc: float) -> dict:
    """A small airless icy world far from a sun-like star, at a galactocentric radius."""
    return worlds.build(None, dict(physics.star_for("G-class")), 5.2, 0.25, 0.008, False, 1.0, r_kpc, 4.57)


class TestCosmicRays(unittest.TestCase):
    def test_the_bulge_and_nucleus_count_not_just_the_disc(self):
        self.assertAlmostEqual(cosmos.cosmic_rays(cosmos.R0_KPC), 1.0, delta=0.05)
        self.assertGreater(cosmos.cosmic_rays(0.35), 5 * cosmos.density(0.35))
        self.assertGreater(cosmos.cosmic_rays(0.01), cosmos.cosmic_rays(0.35))
        self.assertLess(cosmos.cosmic_rays(12.0), 1.0)


class TestRadiolysis(unittest.TestCase):
    def test_radiation_feeds_more_where_the_stars_crowd(self):
        near_core, at_sun = hydromagnetics.radiolysis(_icy(0.01)), hydromagnetics.radiolysis(_icy(cosmos.R0_KPC))
        self.assertGreater(near_core, 1000 * at_sun)
        self.assertGreater(near_core, worlds.geothermal(_icy(0.01)))     # the nucleus's rays outfeed its heat
        self.assertLess(at_sun, 0.01 * worlds.geothermal(_icy(cosmos.R0_KPC)))

    def test_dose_parts_are_shares(self):
        parts = hydromagnetics.dose_parts(_icy(cosmos.R0_KPC))
        self.assertAlmostEqual(parts["stellar"] + parts["cosmic"], 1.0, places=6)


class TestErasingEvents(unittest.TestCase):
    def test_a_shielded_sea_is_never_sterilised_and_an_open_sky_is_more_where_stars_crowd(self):
        self.assertEqual(life.sterilise_per_gyr(1e6, dark=True), 0.0)
        self.assertGreater(life.sterilise_per_gyr(cosmos.cosmic_rays(0.35), False),
                           life.sterilise_per_gyr(cosmos.cosmic_rays(cosmos.R0_KPC), False))


class TestBand(unittest.TestCase):
    OUTER_OPEN = [cosmos.cosmic_rays(cosmos.R0_KPC), 0.0, 1.0, 0.95, 1.0]     # open-sky, from the Sun's radius
    CORE_OPEN = [cosmos.cosmic_rays(0.35), 0.0, 1.0, 0.95, 1.0]
    CORE_SEA = [cosmos.cosmic_rays(0.01), 0.75, 0.0, 0.0, 1.0]   # a dark sea fed mostly by the nucleus's rays

    def test_an_outer_people_keeps_little_of_the_core(self):
        self.assertEqual(settling.fit(self.OUTER_OPEN, cosmos.R0_KPC), 1.0)
        self.assertLess(settling.fit(self.OUTER_OPEN, 0.35), 0.5)
        self.assertLess(settling.fit(self.OUTER_OPEN, 0.01), 1e-6)

    def test_a_core_people_under_an_open_sky_finds_the_outer_galaxy_gentler(self):
        self.assertEqual(settling.fit(self.CORE_OPEN, cosmos.R0_KPC), 1.0)

    def test_a_people_fed_by_the_rays_starves_away_from_them(self):
        self.assertEqual(settling.fit(self.CORE_SEA, 0.01), 1.0)
        self.assertLess(settling.fit(self.CORE_SEA, cosmos.R0_KPC), 0.5)

    def test_plasticity_widens_what_it_keeps(self):
        plastic = list(self.OUTER_OPEN[:4]) + [2.0]
        self.assertGreater(settling.fit(plastic, 0.35), settling.fit(self.OUTER_OPEN, 0.35))

    def test_a_band_counts_fewer_systems_than_none(self):
        self.assertLess(settling.systems_in(cosmos.R0_KPC, 20.0, self.OUTER_OPEN),
                        settling.systems_in(cosmos.R0_KPC, 20.0))


if __name__ == "__main__":
    unittest.main()
