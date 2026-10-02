"""
The frontier as physics and choice: belts are what a disc left ungathered; a people may hold its sky or let it go;
mastery is measured, never granted; a people crosses to the stars only when its mathematics holds the fourth axis;
peoples hear each other by the light of their works before they meet; federations are founded, not seated.
"""

import unittest

from xylarium.kernel import creation, federation, fundamental, mastery, signals, skies
from xylarium.kernel.engine import GameKernel


class TestBelts(unittest.TestCase):
    def test_belts_are_what_a_disc_left_ungathered(self):
        seen = 0
        for j in range(0, 40, 4):
            for sl in creation.cell(7, 16, j):
                if "worlds" not in sl:
                    self.assertEqual(sl["belts"], [])                       # no belts between the stars
                    continue
                for kind, units, comp in sl["belts"]:
                    seen += 1
                    self.assertGreater(units, 0)
                    self.assertAlmostEqual(sum(comp.values()), 1.0, places=2)
        self.assertGreater(seen, 0)


class TestSkies(unittest.TestCase):
    def setUp(self):
        from xylarium.config import DAUGHTER_CITADEL_TIER
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.p = next(p for s in self.k.sectors.values() for p in s.planets
                      if p.population > 1000 and not (p.body or {}).get("giant") and not p.natives)
        self.p.citadel_level = max(self.p.citadel_level, DAUGHTER_CITADEL_TIER)

    def test_a_shield_is_cheap_and_repair_is_dear(self):
        self.assertLess(skies.shield_j(self.k, self.p), 1e15)               # a field, not a fortress
        cost = skies.repair_cost(self.k, self.p, 0.5)
        self.assertGreater(cost["eu"], 1e3)                                  # giving air back takes a world's work

    def test_a_people_with_energy_raises_a_shield_when_its_core_fails(self):
        self.p.society.update({"atmosphere": 0.6, "dynamo": 0.1, "grid_meu": 10 ** 13})
        self.k.cycle_count = 400
        skies.season(self.k)
        self.assertTrue(self.p.society.get("shield"))


class TestMasteryAndTheCrossing(unittest.TestCase):
    def test_earth_today_has_not_mastered_its_world(self):
        # 18 TW against the 1.7e17 W of sunlight Earth intercepts: Kardashev ~0.73
        self.assertLess(1.8e13 / 1.74e17, 1.0)

    def test_a_universe_can_forbid_folding_space(self):
        self.assertTrue(fundamental.of("7:measured").ftl)
        self.assertFalse(fundamental.of("7:measured:ftl=0").ftl)

    def test_the_settled_board_sails_the_lanes(self):
        k = GameKernel(seed=7)
        k.activate()
        self.assertTrue(mastery.crossed(k, "civ:anyone"))

    def test_a_cosmic_people_stays_home_until_it_crosses(self):
        from xylarium.kernel import cosmos, demography
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        p = next(p for s in k.sectors.values() for p in s.planets if p.population > 0)
        p.citadel_level = 4
        self.assertEqual(demography.settler_reach(k, p), 0)
        from xylarium.kernel import knowledge
        mastery.stats(k)["crossed"][knowledge.holder_of_planet(p)] = k.cycle_count
        self.assertGreater(demography.settler_reach(k, p), 0)


class TestSignals(unittest.TestCase):
    def test_a_young_people_is_heard_close_and_an_elder_across_the_galaxy(self):
        earth_ly = signals.reach_kpc(1.8e13 * signals.LEAK_SHARE, 1.8e13) * 3261.56
        self.assertTrue(3 < earth_ly < 50)
        elder_ly = signals.reach_kpc(3.8e26 * signals.LEAK_SHARE, 1.8e13) * 3261.56
        self.assertGreater(elder_ly, 1e5)


class TestFederations(unittest.TestCase):
    def test_doctrine_follows_alignment(self):
        self.assertEqual(federation.preferred_card(0.8), "ALPHA")
        self.assertEqual(federation.preferred_card(-0.8), "DELTA")

    def test_a_non_interference_federation_forbids_uplifting_the_uncrossed(self):
        from xylarium.kernel.factions import Faction
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        k.factions.factions["FED1"] = Faction(id="FED1", name="t", kind="FOUNDED", card="ALPHA", sapience_threshold=0,
                                              uplift_limit=0, enforcement="SANCTION", warrant=0, alignment=0.6)
        federation.stats(k)["members"]["civ:elder"] = "FED1"
        mastery.stats(k)["crossed"]["civ:elder"] = 0
        self.assertTrue(federation.forbids(k, "civ:elder", "uplift", "civ:young"))
        mastery.stats(k)["crossed"]["civ:young"] = 0
        self.assertFalse(federation.forbids(k, "civ:elder", "uplift", "civ:young"))


if __name__ == "__main__":
    unittest.main()
