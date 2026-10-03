"""
A steward is one voice in a people's mind: it sees no further than the people, it urges and cautions and draws
options into attention, and how much it is heeded is learned from what heeding it brought. It never chooses.
"""

import unittest

from xylarium.kernel import decide, knowledge, learning, steward
from xylarium.kernel.engine import GameKernel


class TestSteward(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.p = max((p for s in self.k.sectors.values() for p in s.planets), key=lambda p: p.population)
        self.who = knowledge.holder_of_planet(self.p)
        self.m = decide.mind_of_planet(self.k, self.p)

    def _opts(self):
        return [decide.option("works", 0.0, 100.0, aim="deepen"), decide.option("settle", 0.0, 90.0, aim="grow"),
                decide.option("muster", 0.0, 10.0, aim="secure"), decide.option("feast", 0.0, 5.0)]

    def test_silent_steward_changes_nothing(self):
        o = self._opts()[0]
        self.assertEqual(steward.weight(self.k, self.who, o, 3), 1.0)

    def test_urging_and_caution_weigh_through_heed(self):
        steward.guide(self.k, self.who, "progenitor", aim="grow", caution=["works"])
        works, settle, _, feast = self._opts()
        self.assertGreater(steward.weight(self.k, self.who, settle, 2), 1.0)
        self.assertLess(steward.weight(self.k, self.who, works, 2), 1.0)
        self.assertEqual(steward.weight(self.k, self.who, feast, 2), 1.0)
        w0 = steward.weight(self.k, self.who, settle, 2)
        rec = learning._rec(self.k, self.who)                 # heeding it served this people well
        rec["var"], rec["n"] = 1.0, 4.0
        rec["opts"][steward.voice(self.k, self.who)] = {"adv": 2.0, "n": 4.0}
        self.assertGreater(steward.weight(self.k, self.who, settle, 2), w0)
        rec["opts"][steward.voice(self.k, self.who)] = {"adv": -2.0, "n": 4.0}   # it failed them
        self.assertLess(steward.weight(self.k, self.who, settle, 2), w0)

    def test_a_steward_draws_an_overlooked_option_into_attention(self):
        steward.guide(self.k, self.who, "progenitor", consider=["feast"])
        opts = self._opts()
        ranked = sorted(opts, key=lambda o: -o["value"])
        kept = steward.attend(self.k, self.who, opts, 2, ranked)
        self.assertEqual([o["name"] for o in kept], ["works", "feast"])

    def test_the_people_still_chooses(self):
        steward.guide(self.k, self.who, "progenitor", aim="secure")
        picks = {decide.choose(self.k, self._opts(), self.m, n)["name"] for n in range(40)}
        self.assertNotIn("muster", picks)          # a tenth the worth: one voice cannot carry it
        self.assertTrue(picks)

    def test_the_steward_sees_what_the_people_sees(self):
        steward.guide(self.k, self.who, "progenitor", aim="deepen")
        view = steward.perceive(self.k, self.who)
        self.assertEqual(view["guidance"]["aim"], "deepen")
        self.assertIn("heed", view)


if __name__ == "__main__":
    unittest.main()


class TestStewardIntelligence(unittest.TestCase):
    def test_an_intelligence_steward_urges_what_a_longer_view_would_choose(self):
        from xylarium.kernel import relations, steward_ai
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        steward_ai.enlist_all(k)
        k.cycle_count = 100
        steward_ai.season(k)
        for holder in relations._peoples(k):
            g = steward.of(k, holder)
            self.assertIsNotNone(g)
            self.assertTrue(g["steward"].startswith("ai:"))
            self.assertIn(g["aim"], steward.AIMS)
        self.assertGreaterEqual(steward_ai.summary(k)["stewarded"], 1)
