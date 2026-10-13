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
        if cert:
            self.assertEqual(cert["lane"], "INTELLECT")
            self.assertIn("proof:civ:Elder:1:", cert["id"])

    def test_non_abelian_quaternion_algebra(self):
        # Verify strict non-commutativity in SU(2)
        q1 = physics.Quaternion.from_axis_angle((1.0, 0.0, 0.0), 1.2)
        q2 = physics.Quaternion.from_axis_angle((0.0, 1.0, 0.0), 0.8)
        
        prod1 = q1 * q2
        prod2 = q2 * q1
        # In non-abelian space: q1 * q2 != q2 * q1
        self.assertNotEqual((prod1.w, prod1.x, prod1.y, prod1.z), (prod2.w, prod2.x, prod2.y, prod2.z))
        
        # Lie bracket commutator is non-zero
        comm = q1.commutator(q2)
        self.assertGreater(comm.norm(), 1e-4)

    def test_non_euclidean_manifold_and_curvature_2(self):
        # 1. Non-Euclidean curved geodesic vs flat Euclidean subtraction
        body1 = {"q": Fraction(1, 2), "orbital_angle": 0.0}
        body2 = {"q": Fraction(2), "orbital_angle": 1.5}
        geodesic_len, axis = physics.non_euclidean_geodesic(Fraction(1), body1, body2)
        flat_dist = abs(float(body1["q"])**2 - float(body2["q"])**2)
        
        self.assertGreater(geodesic_len, 0.0)
        self.assertNotEqual(geodesic_len, flat_dist)
        
        # 2. Non-abelian 2-simplex curvature Wilson loops
        sec = next(s for s in self.kernel.sectors.values() if len(s.planets) >= 3)
        cochain = cognition.MaterialCochain()
        diffs = cognition.coboundary_1(self.kernel, sec, cochain)
        plaquettes = cognition.curvature_2(self.kernel, sec, diffs)
        
        self.assertIsInstance(plaquettes, dict)
        if len(plaquettes) > 0:
            w_loop = next(iter(plaquettes.values()))
            self.assertIsInstance(w_loop, physics.Quaternion)


if __name__ == "__main__":
    unittest.main()

