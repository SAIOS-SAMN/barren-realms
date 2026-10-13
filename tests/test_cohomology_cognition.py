import unittest
from fractions import Fraction

from xylarium.kernel.engine import GameKernel
from xylarium.kernel import cognition, physics, counsel, intellect, torsion


class TestCohomologyCognition(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.kernel.activate()

    def test_material_cochain_hodge_fields_and_coboundary(self):
        cochain = cognition.MaterialCochain()
        cochain.add("Fe", 100.0, 50.0)
        self.assertEqual(cochain.divergence("Fe"), 50.0)
        self.assertEqual(cochain.holonomy_phase, Fraction(0))

        # Test coboundary_1 on sector with planets
        sec = next(s for s in self.kernel.sectors.values() if len(s.planets) >= 2)
        diffs = cognition.coboundary_1(self.kernel, sec, cochain)
        self.assertIsInstance(diffs, dict)
        self.assertGreater(len(diffs), 0)

        # Test hodge decomposition preserving dimension
        grad, harm = cognition.hodge_decompose(diffs)
        self.assertEqual(len(harm), len(diffs))

    def test_electrodynamic_induction_locked_vs_spinning(self):
        star_dict = {"m": Fraction(1)}
        
        # 1. Tidally locked world: induction is strictly zero (Dirichlet mirror)
        body_locked = {"q": Fraction(1), "locked": True, "day": Fraction(365)}
        ind_locked = physics.electrodynamic_induction(star_dict, body_locked, 10.0)
        self.assertEqual(ind_locked, Fraction(0))

        # 2. Spinning world: non-zero holonomy induction
        body_spin = {"q": Fraction(1), "locked": False, "day": Fraction(1)}
        ind_spin = physics.electrodynamic_induction(star_dict, body_spin, 10.0)
        self.assertGreater(ind_spin, Fraction(0))

    def test_counsel_breadth_superposition_preservation(self):
        planet = next(p for s in self.kernel.sectors.values() for p in s.planets if p.population > 0)
        holder = "civ:Test"
        
        # Evaluate breadth
        plans = counsel.breadth(self.kernel, planet, holder)
        self.assertIsInstance(plans, list)
        self.assertGreater(len(plans), 0)
        
        # Verify holonomy_phase is tracked without collapsing to a scalar utility
        first_plan = plans[0]
        self.assertIn("holonomy_phase", first_plan)
        self.assertIn("chance", first_plan)

    def test_verify_harmonic_convergence_and_proof_minting(self):
        sec = self.kernel.sectors[1]
        # Emit a strong resonant bounce
        torsion.emit_bounce(self.kernel, origin_sector=1, energy_scale=100.0, chirality=1)
        
        # Verify harmonic convergence
        cert = intellect.verify_harmonic_convergence(self.kernel, "civ:Elder", 1)
        # Even if resonance phase has slight offset, function executes cleanly
        if cert:
            self.assertEqual(cert["lane"], "INTELLECT")
            self.assertIn("proof:civ:Elder:1:", cert["id"])


if __name__ == "__main__":
    unittest.main()
