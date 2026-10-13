import unittest
from fractions import Fraction

from xylarium.kernel.engine import GameKernel
from xylarium.kernel import torsion, elements_continuum, elements, physics


class TestTorsionAndContinuum(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel()

    def test_torsion_bounce_emission_and_wavefront(self):
        # Initial state has zero bounces
        stats = torsion.stats(self.kernel)
        self.assertEqual(len(stats["bounces"]), 0)

        # Emit bounce at galactic core
        bounce = torsion.emit_bounce(
            self.kernel, origin_sector=1, energy_scale=50.0, chirality=1, source="galactic_core"
        )
        self.assertIn("bounce:1:", bounce["id"])
        self.assertEqual(len(stats["bounces"]), 1)

        # Evaluate wavefront at sector 1 and sector 5
        amp1, phase1, chir1 = torsion.eval_wavefront(self.kernel, 1)
        self.assertGreater(amp1, 0.0)
        self.assertEqual(chir1, 1)

    def test_orbital_secular_drift_determinism(self):
        q_init = Fraction(1, 1)
        # Without wavefront
        q_no_drift = torsion.orbital_secular_drift(self.kernel, 999, q_init)
        self.assertEqual(q_no_drift, q_init)

        # With wavefront
        torsion.emit_bounce(self.kernel, origin_sector=1, energy_scale=10.0, chirality=1)
        q_drifted = torsion.orbital_secular_drift(self.kernel, 1, q_init)
        self.assertIsInstance(q_drifted, Fraction)

    def test_118_elements_continuum(self):
        # Element 1 (Hydrogen - single proton has 0 binding energy)
        h = elements_continuum.get_element(1)
        self.assertEqual(h.symbol, "H")
        self.assertEqual(h.line, 1)
        self.assertGreaterEqual(h.binding_per_nucleon, 0.0)

        # Element 26 (Iron - tightly bound)
        fe = elements_continuum.get_element(26)
        self.assertEqual(fe.symbol, "Fe")
        self.assertAlmostEqual(fe.a, 55.845, places=1)
        self.assertGreater(fe.binding_per_nucleon, 8.0)

        # Element 114 (Flerovium - Island of Stability)
        fl = elements_continuum.get_element(114)
        self.assertEqual(fl.symbol, "Fl")
        self.assertGreater(fl.stability_factor, 1.0)

        # Element 118 (Oganesson)
        og = elements_continuum.get_element(118)
        self.assertEqual(og.symbol, "Og")
        self.assertEqual(og.line, 7)

    def test_observer_spectrum_sampling(self):
        # Sample spectrum without crashing
        spec = elements_continuum.sample_spectrum(
            self.kernel, sector_id=1, surface_temp_k=300.0, v_esc_relative=1.0
        )
        self.assertIsInstance(spec, dict)
        self.assertIn("Fe", spec)
        self.assertIn("Si", spec)

    def test_periodic_table_resolution(self):
        # Standard good
        el_c = elements.PeriodicTable.get_element("C")
        self.assertIsNotNone(el_c)
        self.assertEqual(el_c.symbol, "C")

        # Continuum element not in initial 24 GOODS (e.g. Gold Au or Xenon Xe)
        el_au = elements.PeriodicTable.get_element("Au")
        self.assertIsNotNone(el_au)
        self.assertEqual(el_au.symbol, "Au")


if __name__ == "__main__":
    unittest.main()
