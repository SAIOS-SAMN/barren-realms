"""
Minds learn from what their choices brought them, by their own measure; they weigh only as many options as their
thought allows.
"""

import unittest

from xylarium.kernel import learning
from xylarium.kernel.engine import GameKernel


class TestLearning(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7)
        self.k.activate()

    def test_a_choice_that_served_is_valued_higher(self):
        rec = learning._rec(self.k, "people:test")
        rec["var"], rec["n"] = 1.0, 3.0
        rec["opts"]["good"] = {"adv": 1.0, "n": 3.0}
        rec["opts"]["bad"] = {"adv": -1.0, "n": 3.0}
        self.assertGreater(learning.multiplier(self.k, "people:test", "good"), 1.0)
        self.assertLess(learning.multiplier(self.k, "people:test", "bad"), 1.0)
        self.assertEqual(learning.multiplier(self.k, "people:test", "untried"), 1.0)
        self.assertEqual(learning.multiplier(self.k, None, "good"), 1.0)

    def test_attention_grows_with_thought(self):
        self.assertEqual(learning.attention({}), 2)
        self.assertGreater(learning.attention({"fluid": 1.0, "self_knowledge": 0.5}), learning.attention({}))

    def test_a_year_credits_what_was_chosen(self):
        cap = next(iter(self.k.captains.values()))
        me = f"captain:{cap.id}"
        learning.record(self.k, me, "TRADE")
        self.k.cycle_count = 0
        learning.season(self.k)                         # sets the baseline
        learning.record(self.k, me, "TRADE")
        cap.credits += 1000.0
        self.k.cycle_count = 100
        learning.season(self.k)
        self.assertIn("TRADE", learning.stats(self.k)["of"][me]["opts"])
        self.assertGreater(learning.summary(self.k)["lessons"], 0)


if __name__ == "__main__":
    unittest.main()
