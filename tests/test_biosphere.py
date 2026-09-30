"""
The biosphere: carrying capacity, food and growth derived from a world's physics.
"""

import unittest
from fractions import Fraction as F

from xylarium.kernel import biosphere, physics
from xylarium.kernel.engine import GameKernel


class TestBiosphere(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # a universe with a free temperate world to experiment on
        for seed in (7, 3, 11, 42, 1337, 99):
            cls.kernel = GameKernel(seed=seed)
            if any(p.planet_type == "TERRESTRIAL" and p.population == 0 and not p.natives and p.civilization is None
                   for s in cls.kernel.sectors.values() for p in s.planets):
                break
        cls.kernel.activate()
        cls.world_id = next(p.id for s in cls.kernel.sectors.values() for p in s.planets
                            if p.planet_type == "TERRESTRIAL" and p.population == 0 and not p.natives
                            and p.civilization is None)

    def world(self, **kw):
        w = self.kernel.get_planet(self.world_id)
        w.population, w.habitats, w.growth_carry = 0, 0, None
        for k, v in kw.items():
            setattr(w, k, v)
        return w

    def test_light_fit_peaks_at_the_optimum_and_is_symmetric(self):
        w = self.world()
        self.assertEqual(biosphere.light_fit("biotic", F(1), w), 1)
        self.assertEqual(biosphere.light_fit("biotic", F(4), w), biosphere.light_fit("biotic", F(1, 4), w))
        self.assertLess(biosphere.light_fit("biotic", F(4), w), 1)

    def test_bigger_worlds_feed_more(self):
        w = self.world()
        base = dict(w.body)
        small = biosphere.carrying_capacity(self.kernel, w, citadel=1, habitats=0, metabolism="biotic")
        w.body = dict(base, radius="3/2")
        big = biosphere.carrying_capacity(self.kernel, w, citadel=1, habitats=0, metabolism="biotic")
        w.body = base
        self.assertAlmostEqual(big / small, float((F(3, 2) / physics.body(w)["radius"]) ** 2), places=3)

    def test_technology_multiplies_the_harvest(self):
        w = self.world()
        k1 = biosphere.carrying_capacity(self.kernel, w, citadel=1, habitats=0, metabolism="biotic")
        k3 = biosphere.carrying_capacity(self.kernel, w, citadel=3, habitats=0, metabolism="biotic")
        self.assertGreater(k3, 5 * k1)

    def test_a_people_grows_no_faster_than_its_farms(self):
        w = self.world()
        base = dict(w.body)
        w.body = dict(base, tilt=45)            # a harsh tilt halves the growing season
        rate = biosphere.growth_rate(self.kernel, w)
        self.assertLessEqual(rate, biosphere.food_rate(self.kernel, w))
        w.body = base

    def test_over_capacity_a_people_shrinks_and_births_carry_exactly(self):
        w = self.world(habitats=2, owner_id=None)
        k = biosphere.carrying_capacity(self.kernel, w)
        w.population = k * 2
        self.assertLess(biosphere.births(self.kernel, w, k), 0)
        w.population = 1000
        w.growth_carry = None
        total = sum(biosphere.births(self.kernel, w, k) for _ in range(100))
        carry = int(w.growth_carry)
        self.assertTrue(0 <= carry < biosphere.MICRO)
        self.assertGreater(total, 0)

    def test_every_founding_people_can_feed_itself_on_its_homeworld(self):
        for s in self.kernel.sectors.values():
            for p in s.planets:
                if p.civilization is not None and p.population > 0 and not p.natives:
                    self.assertGreater(biosphere.carrying_capacity(self.kernel, p), 0, p.name)

    def test_locked_worlds_farm_only_their_terminator(self):
        w = self.world()
        base = dict(w.body)
        w.body = dict(base, locked=True)
        self.assertEqual(biosphere.season(w), F(1, 2))
        w.body = base


if __name__ == "__main__":
    unittest.main()
