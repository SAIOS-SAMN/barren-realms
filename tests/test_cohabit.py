"""
Peoples share worlds in the niches their biology can use; what each is to the other is measured from what they
eat, give back and share - never assigned.
"""

import random
import unittest

from xylarium.kernel import cohabit, matter
from xylarium.kernel.engine import GameKernel


class Body:
    def __init__(self, ptype, giant=False):
        self.planet_type = ptype
        self.body = {"giant": giant}
        self.society = {}


class TestCohabit(unittest.TestCase):
    def test_niches_follow_physics(self):
        giant = Body("GAS_GIANT", giant=True)
        self.assertEqual(cohabit.niche(giant, "plasmic"), "depths")
        self.assertEqual(cohabit.niche(giant, "biotic"), "cloudtops")
        self.assertIsNone(cohabit.niche(giant, "mineral"))
        rock = Body("TERRESTRIAL")
        self.assertEqual(cohabit.niche(rock, "biotic"), "surface")
        self.assertEqual(cohabit.niche(rock, "mineral"), "crust")
        self.assertIsNone(cohabit.niche(rock, "cryogenic"))
        self.assertEqual(cohabit.niche(Body("ICE"), "cryogenic"), "ice")

    def test_relations_are_measured_from_chemistry(self):
        # Stillcold life eats the water carbon life breathes out, and breathes out hydrogen carbon life does not
        # eat: the Stillcold gain, the carbon people is unaffected (different niches, different staples)
        to_cryo = cohabit.effect("cryogenic", "ice", 1000, "biotic", "surface", 5000)
        to_bio = cohabit.effect("biotic", "surface", 1000, "cryogenic", "ice", 5000)
        self.assertGreater(to_cryo, 0)
        self.assertEqual(to_bio, 0)
        self.assertEqual(cohabit.kind_of(to_cryo, to_bio), "commensalism")
        # two carbon peoples on one surface compete
        a = cohabit.effect("biotic", "surface", 1000, "biotic", "surface", 500)
        self.assertLess(a, 0)
        self.assertEqual(cohabit.kind_of(a, a), "competition")

    def test_a_community_lives_on_its_niche_and_conserves_matter(self):
        random.seed(101)
        k = GameKernel(seed=7)
        k.activate()
        host = next(p for s in k.sectors.values() for p in s.planets if p.population > 0 and not p.natives
                    and cohabit.niche(p, "mineral") and cohabit.host_niche(k, p) != "crust")
        cohabit.communities(host).append({"people": "civ:Visitors", "metab": "mineral", "pop": 2000,
                                          "niche": "crust", "since": 0, "origin": "x"})
        t0, n0 = matter.totals(k), k.matter.net()
        k.cycle_count = 25
        cohabit.quarter(k)
        t1, n1 = matter.totals(k), k.matter.net()
        undeclared = {c: d for c in set(t0) | set(t1) | set(n1)
                      if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}
        self.assertEqual(undeclared, {})
        self.assertTrue(cohabit.communities(host))
        self.assertIn("kind", cohabit.communities(host)[0])


if __name__ == "__main__":
    unittest.main()
