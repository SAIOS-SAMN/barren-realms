"""
A people comes to know itself when its forecasts of itself beat the guess that nothing changes for a generation;
knowing itself steadies its judgement; and the steward's counsel sees only as far as its people's minds can -
breadth from the rungs they have climbed, a self-model once they know themselves, other minds after that.
"""

import unittest

from xylarium.kernel import ages, counsel, decide, fertility, history, introspect, knowledge
from xylarium.kernel.engine import GameKernel


def _people():
    k = GameKernel(seed=7, genesis="cosmic")
    k.activate()
    p = next(p for p in k.sectors[1].planets if p.civilization)
    return k, p, knowledge.holder_of_planet(p)


class TestSelfKnowledge(unittest.TestCase):
    def test_a_people_whose_self_forecasts_beat_the_naive_guess_for_a_generation_knows_itself(self):
        k, p, h = _people()
        rec = {}
        gen = int(fertility.generation_of(k, p) * 100)
        g = {x: 0.2 for x in introspect.GAUGES}
        steps = gen // 100 + 5
        for i in range(steps):
            g = {x: min(1.0, v + 0.005) for x, v in g.items()}            # its fortunes trend: learnable
            introspect._forecast(k, h, rec, g, p)
            rec["forecast"] = {x: min(1.0, v + 0.005) for x, v in g.items()}  # a mind that reads its trend well
            k.cycle_count += 100
        self.assertGreater(rec["skill"], 0)
        self.assertTrue(rec.get("introspective"))
        self.assertTrue(any(e["kind"] == "INTROSPECTION" and "know themselves" in e["title"]
                            for e in history.stats(k)["recent"]))

    def test_knowing_itself_steadies_its_judgement(self):
        k, p, h = _people()
        before = decide.mind_of_planet(k, p)["noise"]
        introspect.stats(k)["peoples"][h] = {"skill": 0.5, "introspective": 1}
        after = decide.mind_of_planet(k, p)["noise"]
        self.assertAlmostEqual(after, before * 0.5, places=6)


class TestCounsel(unittest.TestCase):
    def test_the_counsel_sees_as_far_as_the_people_can(self):
        k, p, h = _people()
        c = counsel.counsel(k, p)
        self.assertEqual(c["rungs"], 1)
        self.assertEqual(len(c["plans"]), 1)                                              # a young mind: one plan
        self.assertIsNone(c["self"])                                                      # no self-model yet
        self.assertIsNone(c["others"])
        self.assertGreater(c["foresight"]["years"], 0)
        from xylarium.kernel import intellect
        intellect.stats(k)["gauge"][h] = {"2": 4, "3": 3, "4": 0}
        introspect.stats(k)["peoples"][h] = {"skill": 0.4, "introspective": 1, "forecast": {"peace": 0.9},
                                             "gauges": {x: 0.5 for x in introspect.GAUGES},
                                             "aspirations": {x: 1.0 for x in introspect.GAUGES}}
        c = counsel.counsel(k, p)
        self.assertEqual(c["rungs"], 4)
        self.assertEqual(len(c["plans"]), 2 + 3)                                          # both paths, three goals
        self.assertAlmostEqual(sum(x["chance"] for x in c["plans"] if x["net"] is not None), 1.0, places=2)
        self.assertEqual(c["self"]["skill"], 0.4)
        self.assertEqual(c["others"], [])                                                 # it has met no one

    def test_the_counsel_changes_nothing(self):
        k, p, h = _people()
        before = (dict(decide.stats(k)["chosen"]), p.society.get("fork"))
        ages.bind(k, "steward-1", "test", p)
        text = ages.act(k, "steward-1", "counsel")
        self.assertIn("rung", text)
        self.assertEqual((dict(decide.stats(k)["chosen"]), p.society.get("fork")), before)


if __name__ == "__main__":
    unittest.main()
