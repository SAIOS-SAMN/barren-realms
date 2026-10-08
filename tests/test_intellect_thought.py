"""
A people at its land's limit still thinks by living: intellect's thought (its ladders' budget and its chance to find
a crystal) counts lived thought as well as its free hands' - the same thought technology counts.
"""

import unittest
from unittest import mock

from xylarium.kernel import intellect, knowledge
from xylarium.kernel.engine import GameKernel


class TestIntellectThought(unittest.TestCase):
    def test_a_people_with_no_free_hands_still_thinks(self):
        k = GameKernel(seed=42)
        with mock.patch.object(knowledge, "effort", return_value=0.0):
            peoples = intellect._peoples(k)
        self.assertTrue(peoples)
        self.assertGreater(sum(rec["effort"] for rec in peoples.values()), 0.0)   # lived thought, with no surplus


if __name__ == "__main__":
    unittest.main()


class TestOneThoughtLaw(unittest.TestCase):
    def test_a_coarse_step_and_fine_steps_agree(self):
        year = knowledge.chance(50.0, 1.0)
        quarter = knowledge.chance(50.0, 0.25)
        self.assertAlmostEqual(1.0 - (1.0 - quarter) ** 4, year)      # four quarters are a year
