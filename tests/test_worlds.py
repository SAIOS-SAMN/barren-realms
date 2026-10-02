"""
Worlds as physics makes them: an atmosphere is gathered, outgassed and lost; climate balances light, greenhouse,
weathering and the runaway limit; solvents are read off phase diagrams. The Solar System is a test of the laws,
not a fit: Venus runs away, Earth keeps liquid seas under a thin nitrogen sky, Mars is stripped and frozen, and a
giant holds a deep plasma.
"""

import unittest

from xylarium.kernel import worlds

SUN = {"mass": "1", "luminosity": "1"}


def _w(a, r, m, giant=False, star=SUN, age=4.6, z=1.0, kpc=8.2):
    return worlds.build(7, star, a, r, m, giant, z, kpc, age), worlds.media(7, star, a, r, m, giant, z, kpc, age)


class TestTheSolarSystemAsATest(unittest.TestCase):
    def test_venus_runs_away_earth_keeps_seas_mars_is_stripped(self):
        venus, vm = _w(0.723, 0.95, 0.815)
        earth, em = _w(1.0, 1.0, 1.0)
        mars, mm = _w(1.524, 0.53, 0.107)
        self.assertGreater(venus["t_surf"], 500)
        self.assertGreater(venus["p_bar"], 30)
        self.assertTrue(250 < earth["t_surf"] < 330)
        self.assertIn("H2O", earth["seas"])
        self.assertTrue(0.1 < earth["p_bar"] < 10)
        self.assertGreater(earth["air"].get("N2", 0), earth["air"].get("CO2", 0))       # weathering drew it down
        self.assertLess(mars["p_bar"], 0.01)
        self.assertLess(mars["t_surf"], 250)
        self.assertEqual({m["region"] for m in em}, {"biotic"})

    def test_a_giant_holds_a_deep_plasma(self):
        _, ms = _w(5.2, 11.2, 318, giant=True)
        self.assertEqual([m["solvent"] for m in ms], ["plasma"])

    def test_phase_diagrams(self):
        self.assertEqual(worlds.phase("H2O", 300, 1.0), "liquid")
        self.assertEqual(worlds.phase("H2O", 400, 1.0), "gas")
        self.assertEqual(worlds.phase("H2O", 400, 10.0), "liquid")                      # pressure raises boiling
        self.assertEqual(worlds.phase("CO2", 250, 1.0), "gas")                           # sublimes at one bar
        self.assertEqual(worlds.phase("CO2", 250, 20.0), "liquid")
        self.assertEqual(worlds.phase("N2", 700, 100.0), "supercritical")
        self.assertEqual(worlds.phase("CH4", 100, 1.5), "liquid")

    def test_richer_chemistry_inside_a_solvents_own_range(self):
        _, em = _w(1.0, 1.0, 1.0)
        _, vm = _w(0.723, 0.95, 0.815)
        self.assertGreater(max(m["richness"] for m in em), max(m["richness"] for m in vm) * 5)


if __name__ == "__main__":
    unittest.main()
