"""
Perception evolves from where a species lives: a yellow star seen through water gives three colours, a red dwarf's
fewer; a people in the dark senses heat and pressure; every channel is named in its own tongue.
"""

import unittest
from types import SimpleNamespace

from xylarium.kernel import perception as P


class TestPerception(unittest.TestCase):
    def test_colours_follow_the_star_and_the_medium(self):
        self.assertEqual(P.light_channels(1.0, "H2O")[0], 3)              # a yellow star through water
        self.assertLess(P.light_channels(0.3, "H2O")[0], 3)               # a red dwarf's light: fewer colours
        self.assertGreater(P.light_channels(1.5, "H2O")[0], 3)            # a hotter star: more
        self.assertEqual(P.light_channels(1.0, "H2O", surface=False), (0, None))

    def test_a_people_in_the_dark_senses_heat_and_pressure_in_its_own_words(self):
        rogue = SimpleNamespace(planet_type="ROGUE", sector_id=0)
        chans = P.channels(None, rogue, {"sense": "light", "solvent": "NH3", "medium": "a dark NH3 under ice"}, "civ:Umor")
        self.assertEqual([c["kind"] for c in chans], ["heat", "pressure"])
        self.assertTrue(all(c["name"] for c in chans))
        other = P.channels(None, rogue, {"sense": "light", "solvent": "NH3", "medium": "a dark NH3 under ice"}, "civ:Thish")
        self.assertNotEqual([c["name"] for c in chans], [c["name"] for c in other])     # its own words


if __name__ == "__main__":
    unittest.main()
