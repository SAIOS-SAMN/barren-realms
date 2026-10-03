"""
A people's institutions: gauges a steward can set, a creed raised by blows it cannot explain and worn down by what
it comes to know, myths told in the terms of its own sky, civil strife when more would rise than are under arms,
and trades that grow with its market.
"""

import unittest

from xylarium.kernel import knowledge, society
from xylarium.kernel.engine import GameKernel


def _people(k):
    return society._peoples(k)[0]


class TestSociety(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="primordial")
        self.k.activate()
        self.p = _people(self.k)

    def test_a_steward_sets_gauges_and_the_council_leaves_them(self):
        society.set_gauge(self.p, "levy", 0.2)
        society.set_gauge(self.p, "temple", 0.9)
        society.quarter(self.k)
        self.assertEqual(society.gauges(self.p)["levy"], 0.2)
        self.assertEqual(society.gauges(self.p)["temple"], 0.9)
        self.assertAlmostEqual(society.output_factor(self.p), 0.8)
        with self.assertRaises(KeyError):
            society.set_gauge(self.p, "tyranny", 1.0)

    def test_unexplained_blows_raise_the_creed_and_make_myths(self):
        self.p.civilization.dogma = 0.0
        self.p.society["famine_cycle"] = self.k.cycle_count
        society.quarter(self.k)
        self.assertGreater(self.p.civilization.dogma, 0.0)
        from xylarium.kernel import memory
        myths = memory.myths(self.k, knowledge.holder_of_planet(self.p))
        self.assertEqual([m["kind"] for m in myths][:1], ["famine"])
        self.assertIn("sun", myths[0]["text"])

    def test_knowledge_wears_the_creed_down(self):
        self.p.civilization.dogma = 0.8
        self.p.society["info_seen"] = 0.0
        knowledge.learn(self.k, knowledge.holder_of_planet(self.p), "information", 10 ** 4)
        society.set_gauge(self.p, "temple", 0.8)
        society._believe(self.k, self.p, 25.0)
        self.assertLess(self.p.civilization.dogma, 0.2)

    def test_more_rising_than_under_arms_is_civil_strife(self):
        p = self.p
        p.society["self_sufficiency"] = 0.2
        p.civilization.dogma = 0.0
        p.morale = 10
        society.set_gauge(p, "levy", 0.0)
        before, treasury, purse = p.population, p.treasury, p.household_purse
        line = society._strife(self.k, p, society.stress(self.k, p), 25.0)
        self.assertIsNotNone(line)
        self.assertLessEqual(p.population, before)
        self.assertEqual(p.treasury + p.household_purse, treasury + purse)     # plundered, not destroyed
        self.assertIsNone(society._strife(self.k, p, society.stress(self.k, p), 25.0))   # an exhausted generation

    def test_trades_grow_with_the_market(self):
        society.set_gauge(self.p, "commerce", 1.0)
        many = society.trades(self.k, self.p)
        society.set_gauge(self.p, "commerce", 0.0)
        self.assertEqual(society.trades(self.k, self.p), 0)
        self.assertGreater(many, 0)


if __name__ == "__main__":
    unittest.main()
