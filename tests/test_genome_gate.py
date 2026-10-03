"""
A people crosses to other stars only once it can rewrite its own genome for another sun - unless its life holds no
genome at all. Once among the stars, a people that rewrites itself fits each world it settles.
"""

import unittest
from unittest import mock

from xylarium.kernel import biosphere, knowledge, mastery, technology
from xylarium.kernel.engine import GameKernel


class TestGenomeGate(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.p = max((p for s in self.k.sectors.values() for p in s.planets), key=lambda p: p.population)
        self.who = knowledge.holder_of_planet(self.p)

    def test_no_crossing_without_genetics(self):
        self.assertFalse(mastery.genome_ready(self.k, self.who, [self.p]))
        technology.stats(self.k)["of"].setdefault(self.who, {})["genetics"] = 1
        self.assertTrue(mastery.genome_ready(self.k, self.who, [self.p]))

    def test_life_without_a_genome_is_not_held_back(self):
        with mock.patch.object(biosphere, "metabolism_of", lambda k, p: "plasmic"):
            self.assertTrue(mastery.genome_ready(self.k, self.who, [self.p]))

    def test_an_engineering_people_among_the_stars_fits_new_worlds(self):
        self.assertFalse(biosphere.engineers_itself(self.k, self.p))
        technology.stats(self.k)["of"].setdefault(self.who, {})["genetics"] = 1
        mastery.stats(self.k)["crossed"][self.who] = self.k.cycle_count
        self.assertTrue(biosphere.engineers_itself(self.k, self.p))
        self.assertEqual(biosphere.land(self.k, self.p)["chemistry"], 1)


if __name__ == "__main__":
    unittest.main()
