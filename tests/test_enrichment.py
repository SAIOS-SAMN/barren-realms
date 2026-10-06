"""
The galaxy makes its own elements, and they settle by weight.

Success criteria, from the formulas alone (gas falling in inside-out, stars forming per orbit, four nucleosynthesis
channels on their own clocks, fountains mixing by weight, winds, the inward drift, the centre's capture and return),
calibrated to the measured gas at the Sun's radius today (young B stars) - the Sun itself a prediction:
  - heavy elements drop first: they stay nearer where they were made, so their gradients are steepest;
  - light elements flow out toward the rim;
  - the core is enriched first, the rim last (inside-out);
  - the early galaxy is rich in what massive stars make at once, and the Type Ia iron comes later;
  - the iron gradient the formulas give is the one measured, without being put in;
  - the Big Bang's own matter is everywhere the same;
  - every unit of metal made is somewhere in the flow: stars, gas, the halo raining back, the child universe;
  - the Sun's composition is found in the model's gas somewhere in the disc 4.57 Gyr ago.
"""

import unittest

from xylarium.kernel import enrichment as E


class TestEnrichment(unittest.TestCase):
    T = E.cosmos_today()

    def test_the_yields_are_set_by_todays_local_gas(self):
        import math
        for s, dex in (("O", 0.07), ("Fe", 0.02), ("N", -0.04)):
            self.assertAlmostEqual(math.log10(E.relative(None, s, 8.0, self.T)), dex, places=6)

    def test_the_suns_birth_gas_is_found_in_the_model(self):
        f = E.sun_birth()
        self.assertLess(f["rms_dex"], 0.1)                                 # a place matches it within ~0.1 dex
        self.assertTrue(4.0 <= f["r_kpc"] <= 10.0, f["r_kpc"])              # and it is in the disc, near us

    def test_stars_burn_hydrogen_as_the_metals_rise(self):
        self.assertAlmostEqual(E.relative(None, "H", 8.0, E._sun_birth()) * (E.X_PRIMORDIAL - 3 * E.Z_SUN),
                               E.X_PRIMORDIAL - 3 * E.Z_SUN * E.metals(None, 8.0, E._sun_birth()), places=9)
        self.assertLess(E.relative(None, "H", 2.0, self.T), E.relative(None, "H", 14.0, self.T))
        self.assertGreater(E.relative(None, "He", 2.0, self.T), E.relative(None, "He", 14.0, self.T))

    def test_heavy_elements_drop_first(self):
        g = {s: E.gradient(None, s, self.T) for s in ("O", "Si", "Fe", "Pt", "U", "AdL")}
        for s, v in g.items():
            self.assertLess(v, 0.0, s)                                     # richer toward the core
        self.assertLess(g["Si"], g["O"])
        self.assertLess(g["Fe"], g["Si"])
        self.assertLess(g["Pt"], g["Fe"])
        self.assertLess(g["U"], g["Pt"])
        self.assertLess(g["AdL"], g["U"])

    def test_light_elements_flow_out_to_the_rim(self):
        reach = {s: E.relative(None, s, 14.0, self.T) / E.relative(None, s, 8.0, self.T) for s in ("O", "Fe", "U")}
        self.assertGreater(reach["O"], reach["Fe"])
        self.assertGreater(reach["Fe"], reach["U"])

    def test_the_measured_iron_gradient_comes_out_without_being_put_in(self):
        self.assertAlmostEqual(E.gradient(None, "Fe", self.T), -0.06, delta=0.02)   # the Milky Way's disc

    def test_the_core_is_enriched_first(self):
        def half_solar(r):
            t = 0.1
            while t <= self.T:
                if E.relative(None, "Fe", r, t) >= 0.5:
                    return t
                t += E.DT_GYR
            return float("inf")
        self.assertLess(half_solar(3.0), half_solar(8.0))                  # inside-out: the core first ...
        self.assertLess(half_solar(8.0), half_solar(13.0))                 # ... the rim last
        self.assertLess(E.relative(None, "Fe", 8.0, 1.0), E.relative(None, "Fe", 8.0, self.T))   # ages enrich

    def test_massive_stars_first_white_dwarfs_later(self):
        o_fe = lambda t: E.relative(None, "O", 8.0, t) / E.relative(None, "Fe", 8.0, t)
        self.assertGreater(o_fe(1.0), 1.5)                                 # the young galaxy: oxygen-rich
        self.assertGreater(o_fe(2.0), o_fe(6.0))
        self.assertGreater(o_fe(6.0), o_fe(self.T))                        # the Type Ia iron catches up

    def test_the_big_bangs_matter_is_everywhere_the_same_until_stars_change_it(self):
        before = 0.1                                                       # before the first stars
        first = E.relative(None, "H", 2.0, before)
        for r in (2.0, 8.0, 14.0):
            self.assertAlmostEqual(E.relative(None, "H", r, before), first)
            self.assertEqual(E.relative(None, "He-3", r, self.T), 1.0)
        self.assertNotAlmostEqual(E.relative(None, "H", 2.0, self.T), E.relative(None, "H", 14.0, self.T))

    def test_every_unit_made_is_booked(self):
        b = E.budget(None)
        self.assertAlmostEqual(sum(v for k, v in b.items() if k != "made"), 1.0, places=6)
        self.assertGreater(b["horizon"], 0.0)                              # some crossed to a child universe
        self.assertGreater(b["locked"], b["gas"])                          # most of it is in stars, as measured

    def test_another_universe_runs_the_same_yields_through_its_own_history(self):
        slow = (2.0, 0.3, 1.0)                                             # a universe that assembles twice as slowly
        here = E._key(None)
        a = E._run(slow)
        b = E._run(here)
        n = int(round(2.0 / E.DT_GYR))
        made_a = sum(sum(a["metal"][n][k]) for k in a["metal"][n])
        made_b = sum(sum(b["metal"][n][k]) for k in b["metal"][n])
        self.assertLess(made_a, made_b)                                    # it has made less by the same epoch


if __name__ == "__main__":
    unittest.main()
