"""
A people not yet among the stars keeps no banking entries; what it is remembered for is what it thinks is out there,
the hurdles it passes, what it imagines and the art it makes - each derived from its own sky, body, mathematics
and creed.
"""

import unittest

from xylarium.kernel import culture, history, institutions
from xylarium.kernel.engine import GameKernel


class TestCulture(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.p = next(p for s in self.k.sectors.values() for p in s.planets if p.population > 0)

    def test_an_unlinked_peoples_money_is_counted_not_told(self):
        p = self.p
        p.society["way"] = "state"
        institutions.found_currency(self.k, p)
        kinds = [e["kind"] for e in history.stats(self.k)["recent"]]
        self.assertNotIn("COINAGE", kinds)
        self.assertIn("COINAGE", history.stats(self.k)["muted"])
        self.assertIn("FIRST", kinds)                                       # the milestone itself is history

    def test_cosmology_follows_knowledge_creed_and_company(self):
        from xylarium.kernel import contact, knowledge
        h = knowledge.holder_of_planet(self.p)
        self.p.civilization.dogma = 0.9
        self.assertEqual(culture.cosmology(self.k, h, self.p)["stance"], "sacred")
        self.p.civilization.dogma = 0.0
        knowledge.learn(self.k, h, "information", 100)
        self.assertEqual(culture.cosmology(self.k, h, self.p)["stance"], "silence")
        contact.stats(self.k)["familiarity"][contact._key(h, "civ:Other")] = 0.5
        self.assertEqual(culture.cosmology(self.k, h, self.p)["stance"], "plural")

    def test_art_takes_its_symmetries_from_the_peoples_mathematics(self):
        from xylarium.kernel import crystal as C, intellect, knowledge
        h = knowledge.holder_of_planet(self.p)
        intellect.stats(self.k)["vocab"][h] = [C.ROT90]
        self.assertIn("never mirror", culture.art(self.p, self.k, h)["symmetry"])
        intellect.stats(self.k)["vocab"][h] = [C.ROT90, C.FLIPH]
        self.assertIn("turn and mirror", culture.art(self.p, self.k, h)["symmetry"])

    def test_a_generation_of_seasons_tells_its_culture_once(self):
        for _ in range(8):
            self.k.cycle_count += 25
            culture.quarter(self.k)
        kinds = [e["kind"] for e in history.stats(self.k)["recent"]]
        self.assertEqual(kinds.count("PHILOSOPHY"), 1)
        self.assertLessEqual(kinds.count("IMAGINATION"), 1)


if __name__ == "__main__":
    unittest.main()
