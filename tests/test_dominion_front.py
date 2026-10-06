"""
A dominion settles no faster than its front: the systems within one hop per settlement, cut by the disc, never more
than the galaxy holds; its fall shared over the worlds it holds along that growth.
"""
import unittest

from xylarium.kernel import annals


class TestDominionFront(unittest.TestCase):
    N_SUN = 0.1 / annals.STARS_PER_SYSTEM

    def cap(self, x):
        return max(1.0, annals._systems_within(self.N_SUN, annals.front_pc(self.N_SUN, x)))

    def test_front_crosses_the_disc_in_tens_of_myr(self):
        # the galaxy's systems are within reach after ~1e6 generations: ~25 Myr at 25-year generations
        x = 1.0
        while self.cap(x) < annals.galaxy_systems():
            x *= 1.1
        self.assertTrue(5.0 < x * 25.0 / 1e6 < 50.0, x)

    def test_never_more_than_the_galaxy(self):
        self.assertEqual(self.cap(1e9), annals.galaxy_systems())
        self.assertTrue(1e11 < annals.galaxy_systems() < 1e12)

    def test_volume_continuous_at_the_disc(self):
        h = annals.DISC_HALF_THICKNESS_PC
        self.assertAlmostEqual(annals._systems_within(1.0, h - 1e-6), annals._systems_within(1.0, h + 1e-6), delta=1e-6 * annals._systems_within(1.0, h))

    def test_hazard_and_its_inverse_agree(self):
        f = annals.FALL_PER_GENERATION
        ran, until = annals._dominion_hazard(f, 1.0, 1e6, self.cap)
        self.assertIsNone(until)
        self.assertAlmostEqual(ran, f / annals.DOMINION_PER_GENERATION, delta=0.01 * ran)
        need = 0.5 * ran
        got, t = annals._dominion_hazard(f, 1.0, 1e6, self.cap, need)
        self.assertAlmostEqual(annals._dominion_hazard(f, 1.0, t, self.cap)[0], need, delta=1e-3 * need)

    def test_a_bound_dominion_runs_more_hazard(self):
        f = annals.FALL_PER_GENERATION
        free = annals._dominion_hazard(f, 1.0, 1e4, lambda t: 1e30)[0]
        held = annals._dominion_hazard(f, 1.0, 1e4, lambda t: 10.0)[0]
        self.assertGreater(held, free)


if __name__ == "__main__":
    unittest.main()
