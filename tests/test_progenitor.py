"""
The progenitor's own chronicle: written under their name into the annals, kept whole, never a people's memory.
"""

import random
import unittest

from xylarium.kernel import memory, progenitor
from xylarium.kernel.engine import GameKernel


class TestProgenitorChronicle(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()

    def test_an_entry_is_kept_under_its_authors_name_and_no_people_remembers_it(self):
        e = progenitor.write(self.k, "The Progenitor", "On the laws", "Every deed is counted in lives.",
                             about=["civ:Turenol"])
        self.assertEqual(e["n"], 1)
        self.assertEqual(progenitor.entries(self.k, "The Progenitor")[0]["title"], "On the laws")
        self.assertIn("On the laws", progenitor.render(self.k))
        self.assertNotIn("PROGENITOR", memory.WITNESSED)                # the steward's record, not a people's

    def test_an_entry_needs_a_name(self):
        with self.assertRaises(ValueError):
            progenitor.write(self.k, "", "untitled", "")


if __name__ == "__main__":
    unittest.main()
