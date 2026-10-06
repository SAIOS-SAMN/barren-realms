"""
The galaxy makes its own elements, and they settle by weight.

Success criteria, from the formulas alone (gas falling in inside-out, stars forming per orbit, four nucleosynthesis
channels on their own clocks, fountains mixing by weight, winds, the inward drift, the centre's capture and return),
calibrated at one point - the gas the Sun formed from:
  - heavy elements drop first: they stay nearer where they were made, so their gradients are steepest;
  - light elements flow out toward the rim;
  - the core is enriched first, the rim last (inside-out);
  - the early galaxy is rich in what massive stars make at once, and the Type Ia iron comes later;
  - the iron gradient the formulas give is the one measured, without being put in;
  - the Big Bang's own matter is everywhere the same;
  - every unit of metal made is booked somewhere.
"""

import unittest

from xylarium.kernel import enrichment as E


class TestEnrichment(unittest.TestCase):
    T = E.cosmos_today()

    def test_the_sun_is_the_one_calibration(self):
        for s in ("O", "Fe", "U"):
            self.assertAlmostEqual(E.relative(None, s, 8.0, E._sun_birth()), 1.0, places=6)

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
        early = 2.0
        self.assertGreater(E.relative(None, "Fe", 3.0, early), 3 * E.relative(None, "Fe", 14.0, early))
        self.assertLess(E.relative(None, "Fe", 8.0, 1.0), E.relative(None, "Fe", 8.0, self.T))   # ages enrich

    def test_massive_stars_first_white_dwarfs_later(self):
        o_fe = lambda t: E.relative(None, "O", 8.0, t) / E.relative(None, "Fe", 8.0, t)
        self.assertGreater(o_fe(1.0), 1.5)                                 # the young galaxy: oxygen-rich
        self.assertAlmostEqual(o_fe(E._sun_birth()), 1.0, places=6)
        self.assertLess(o_fe(self.T), 1.0)                                 # the Type Ia iron catches up

    def test_the_big_bangs_matter_is_everywhere_the_same(self):
        for r in (2.0, 8.0, 14.0):
            self.assertEqual(E.relative(None, "H", r, 1.0), 1.0)
            self.assertEqual(E.relative(None, "He-3", r, self.T), 1.0)

    def test_every_unit_made_is_booked(self):
        b = E.budget(None)
        self.assertAlmostEqual(sum(v for k, v in b.items() if k != "made"), 1.0, places=6)
        self.assertGreater(b["horizon"], 0.0)                              # some crossed to a child universe
        self.assertGreater(b["outflow"], 0.0)                              # some the winds took

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
