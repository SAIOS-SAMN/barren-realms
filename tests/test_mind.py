"""
A mind is a kind, not a quantity: its world chose its senses, body and way of living together, and those choose
what it learns first, how it holds what it knows, and how soon it comes to its own heredity. Every people learns
from the day it wakes.
"""

import unittest

from xylarium.kernel import annals, knowledge, mind, technology
from xylarium.kernel.engine import GameKernel


class TestMind(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.p = max((p for s in self.k.sectors.values() for p in s.planets), key=lambda p: p.population)
        self.who = knowledge.holder_of_planet(self.p)

    def test_the_first_people_is_an_aquatic_collective(self):
        prof = mind.profile(self.k, self.p)
        self.assertTrue(prof["aquatic"])
        self.assertEqual(prof["collective"], 1.0)
        self.assertGreater(prof["affinity"]["biology"], prof["affinity"]["information"])   # biology before the sky

    def test_foragers_learn_from_the_day_they_wake(self):
        self.assertEqual(self.p.society.get("way", "forage"), "forage")
        self.assertGreater(knowledge.lived(self.k, self.p), 0.0)
        before = sum(knowledge.stocks(self.k, self.who).values())
        self.k.cycle_count = 25
        knowledge.quarter(self.k)
        self.assertGreater(sum(knowledge.stocks(self.k, self.who).values()), before)

    def test_a_self_rewriting_mind_comes_to_genetics_without_machines(self):
        held = technology.stats(self.k)["of"].setdefault(self.who, {})
        held["medicine"] = 1
        self.assertNotIn("computation", held)
        self.assertGreaterEqual(mind.profile(self.k, self.p)["plastic"], technology.PLASTIC_GENETICS)
        self.assertTrue(technology.feasible(self.k, self.who, "genetics", self.p))

    def test_what_a_people_knows_of_life_makes_it_harder_to_bring_down(self):
        r0 = annals.resilience(self.k, self.who)
        technology.stats(self.k)["of"].setdefault(self.who, {})["genetics"] = 1
        self.assertGreater(annals.resilience(self.k, self.who), r0)


if __name__ == "__main__":
    unittest.main()
