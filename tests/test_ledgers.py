"""
Understanding, knowledge and the unearned: a stage's grant is held unearned and nothing is built on it until a people's
understanding earns it; the annals carry lived understanding through a people's deep years even with no free hands;
the ledgers line up in one reading.
"""

import unittest
from unittest import mock

from xylarium.kernel import annals, knowledge, ledgers, technology
from xylarium.kernel.engine import GameKernel


class TestLedgers(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        self.home = next(p for s in self.k.sectors.values() for p in s.planets if p.population > 0
                         and p.civilization is not None)
        self.who = knowledge.holder_of_planet(self.home)
        technology.stats(self.k)["of"].pop(self.who, None)

    def _season(self):
        self.k.cycle_count = (self.k.cycle_count // 100 + 1) * 100
        with mock.patch.object(technology, "feasible", return_value=True):
            technology.season(self.k)

    def test_a_stage_grant_is_unearned_and_nothing_is_built_on_it(self):
        technology.grant(self.k, self.who, "radio")
        technology.grant(self.k, self.who, "computation")
        self.assertEqual(technology.unearned(self.k, self.who), {"radio": "stage", "computation": "stage"})
        self.assertTrue(technology.has(self.k, self.who, "radio"))                  # usable
        with mock.patch("xylarium.kernel.laws.mastery", return_value=1.0), \
                mock.patch.object(knowledge, "effort", return_value=1e9):
            self._season()                                   # every finding certain - but networks rests on the two
        self.assertFalse(technology.found(self.k, self.who, "networks"))             # not built on the unearned

    def test_understanding_earns_what_it_held(self):
        technology.grant(self.k, self.who, "radio")
        with mock.patch("xylarium.kernel.laws.mastery", return_value=1.0), \
                mock.patch.object(knowledge, "effort", return_value=1e9):
            self._season()
        self.assertNotIn("radio", technology.unearned(self.k, self.who))
        self.assertIn("radio", ledgers.read(self.k, self.who)["knowledge"]["built"])

    def test_the_annals_carry_lived_understanding_with_no_free_hands(self):
        for d in knowledge.DOMAINS:
            knowledge.stocks(self.k, self.who)[d] = 0.0
        job = {"who": self.who, "home": self.home, "worlds": [self.home], "gens": 4.0, "gen": 25.0, "fell": None,
               "stage": "crossed", "ruled_from": None, "grown_from": 1, "rec": {"dominion": 1},
               "epoch_of": lambda t: 0.0}
        with mock.patch.object(annals, "_apply"), mock.patch.object(knowledge, "effort", return_value=0.0):
            annals._books(self.k, job, [])
        self.assertGreater(sum(knowledge.stocks(self.k, self.who).values()), 0.0)

    def test_the_ledgers_line_up(self):
        technology.grant(self.k, self.who, "fission")
        r = ledgers.read(self.k, self.who)
        self.assertEqual(set(r), {"understanding", "knowledge", "unearned"})
        self.assertEqual(r["unearned"], {"fission": "stage"})
        self.assertNotIn("fission", r["knowledge"]["built"])


if __name__ == "__main__":
    unittest.main()
