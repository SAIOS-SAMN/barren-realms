"""
A people's motto is its own: said in its own tongue, from the facts of its waking, with a translation - never the one
motto every people was once given. Kin peoples speak dialects of one tongue.
"""

import unittest
from types import SimpleNamespace

from xylarium.kernel import mottos


class TestMottos(unittest.TestCase):
    ICE = {"shape": "superorganism", "form": "swimming", "medium": "a dark NH3 under ice", "solvent": "NH3"}
    LAND = {"shape": "society", "form": "walking", "medium": "H2O surface", "solvent": "H2O"}
    ROGUE = SimpleNamespace(planet_type="ROGUE", sector_id=0)

    def test_the_motto_is_said_from_its_waking_with_its_translation(self):
        m = mottos.compose(None, "civ:Umor", self.ROGUE, self.ICE)
        self.assertEqual(m["gloss"], "we who are one swam toward the ice above us, out of the dark ammonia under the ice")
        self.assertNotIn("we looked up", mottos.motto(None, "civ:Umor", self.ROGUE, self.LAND))
        land = mottos.compose(None, "civ:Okishsha", self.ROGUE, self.LAND)["gloss"]
        self.assertEqual(land, "we walked toward the dark that has no sun, out of the water")

    def test_two_peoples_never_say_it_alike(self):
        a = mottos.compose(None, "civ:Umor", self.ROGUE, self.ICE)["said"]
        b = mottos.compose(None, "civ:Thish", self.ROGUE, self.ICE)["said"]
        self.assertNotEqual(a, b)                                   # one meaning, two tongues

    def test_a_daughter_speaks_a_dialect_of_its_parents_tongue(self):
        parent, daughter = mottos.tongue("civ:Renor"), mottos.tongue("civ:Renor of Veiled 012d")
        self.assertEqual(len(set(parent) - set(daughter)), 1)       # one sound gone, one come
        self.assertEqual(mottos.word("civ:Renor", "the ice above us"), mottos.word("civ:Renor", "the ice above us"))


if __name__ == "__main__":
    unittest.main()


class TestDaughterMotto(unittest.TestCase):
    def test_a_daughter_says_where_it_came(self):
        ice = TestMottos.ICE
        parent = mottos.motto(None, "civ:Renor", TestMottos.ROGUE, ice)
        daughter = mottos.motto(None, "civ:Renor of Veiled 012d", TestMottos.ROGUE, ice)
        self.assertNotEqual(parent, daughter)
        self.assertIn("came to Veiled 012d", daughter)
