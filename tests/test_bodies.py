"""
Bodies and peoples from physics: a minded body runs at its chemistry's best temperature, so its metabolism,
generation and thought follow that chemistry's pace; what feeds a people is the energy reaching its chemistry; a crowd
disease's critical community and lethality come from transmission dynamics; and a people's ways are named in its own
chemistry's terms.
"""

import unittest

from xylarium.kernel import biosphere, laws, lifespan, ways, worlds


class TestBodies(unittest.TestCase):
    def test_a_body_runs_at_its_chemistrys_best(self):
        self.assertGreater(worlds.body_pace("H2O"), worlds.body_pace("CH4"))
        self.assertGreater(worlds.body_pace("plasma"), worlds.body_pace("H2O"))
        hot = biosphere.metabolic_factor("plasmic", "K", body_t=worlds.body_temperature("plasma"))
        cold = biosphere.metabolic_factor("cryogenic", "K", body_t=worlds.body_temperature("CH4"))
        self.assertGreater(hot, cold)                                                    # hot bodies burn fast
        warm = laws.cognition("biotic", body_t=worlds.body_temperature("H2O"))
        icy = laws.cognition("cryogenic", body_t=worlds.body_temperature("N2"))
        self.assertGreater(warm["speed"], icy["speed"])
        self.assertGreater(icy["depth"], warm["depth"])                                 # cold minds deep


class TestEnergyFeeds(unittest.TestCase):
    def test_a_dark_sea_carries_far_fewer_than_a_lit_one(self):
        sun = {"mass": "1", "luminosity": "1"}
        lit = worlds.best(worlds.media(7, sun, 1.0, 1.0, 1.0, False, 1.0, 8.2, 4.6))
        dark = worlds.best(worlds.media(7, sun, 15.0, 1.0, 1.0, False, 1.0, 8.2, 4.6))
        self.assertGreater(lit["energy"], dark["energy"] * 100)                         # sunlight against a world's heat


class TestDisease(unittest.TestCase):
    def test_the_critical_community_grows_with_the_hosts_generation(self):
        class P:
            civilization = None
            society = {}
            owner_id = None
        from unittest import mock
        from xylarium.kernel import fertility
        with mock.patch.object(fertility, "generation_of", return_value=10.0):
            short = lifespan.critical_community(None, P())
        with mock.patch.object(fertility, "generation_of", return_value=40.0):
            long_ = lifespan.critical_community(None, P())
        self.assertAlmostEqual(long_ / short, 4.0)
        self.assertEqual(lifespan.CFR_VIRGIN, 0.5)                                        # the trade-off's optimum


class TestWords(unittest.TestCase):
    def test_ways_are_named_in_a_peoples_own_terms(self):
        class C:
            traits = {"solvent": "H2O", "sense": "heat and pressure"}

        class P:
            civilization = C()
        self.assertIn("vent", ways.words(P())["tend"])
        C.traits = {"solvent": "plasma", "sense": "fields"}
        self.assertIn("field", ways.words(P())["tend"])
        C.traits = {"solvent": "H2O", "sense": "light"}
        self.assertIn("fields", ways.words(P())["tend"])


if __name__ == "__main__":
    unittest.main()
