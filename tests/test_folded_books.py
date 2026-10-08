"""
A folded people's books (annals pass 3) gauge its world by the harvest law rather than a default, and a people that
studies nothing yet shares its first learning across every domain rather than learning nothing for ever.
"""

import unittest
from unittest import mock

from xylarium.kernel import annals, biosphere, knowledge
from xylarium.kernel.engine import GameKernel


class TestFoldedBooks(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        self.home = next(p for s in self.k.sectors.values() for p in s.planets if p.population > 0
                         and p.civilization is not None)
        self.who = knowledge.holder_of_planet(self.home)
        self.home.society.pop("self_sufficiency", None)
        self.job = {"who": self.who, "home": self.home, "worlds": [self.home], "gens": 2.0, "gen": 25.0,
                    "fell": None, "stage": "crossed", "ruled_from": None, "grown_from": 1,
                    "rec": {"dominion": 1}, "epoch_of": lambda t: 0.0}

    def _books(self):
        with mock.patch.object(annals, "_apply"), mock.patch.object(knowledge, "effort", return_value=10.0):
            annals._books(self.k, self.job, [])

    def test_a_carried_world_is_gauged_by_the_harvest_law(self):
        k = biosphere.carrying_capacity(self.k, self.home)
        self.home.population = k
        self._books()
        self.assertEqual(self.home.society["self_sufficiency"], 1.0)          # at what its land carries: fed, no more
        self.home.population = max(1, k // 2)
        self._books()
        self.assertEqual(self.home.society["self_sufficiency"], 1.25)         # its farmers feed a quarter more

    def test_a_people_that_studies_nothing_learns_across_every_domain(self):
        for d in knowledge.DOMAINS:
            knowledge.stocks(self.k, self.who)[d] = 0.0
        self._books()
        self.assertTrue(all(v > 0 for v in knowledge.stocks(self.k, self.who).values()))


if __name__ == "__main__":
    unittest.main()
