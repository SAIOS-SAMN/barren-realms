"""
Populace: the galaxy grows with its humans - more AI to balance them, new frontier at the edge (existing systems
untouched), frontier clusters with spacefaring peoples, and a settled Imperial heartland.
"""

import random
import unittest

from xylarium.kernel import populace
from xylarium.kernel.engine import GameKernel


class TestPopulace(unittest.TestCase):
    def setUp(self):
        random.seed(151)
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.k.tick_simulation = lambda: None

    def test_more_humans_bring_more_ai_room_and_new_frontier_without_moving_old_systems(self):
        k = self.k
        before = {sid: sorted(s.warps) for sid, s in k.sectors.items()}
        cap0 = populace.ai_capacity(k)
        for i in range(populace.BASE_HUMANS + 3):
            k.register_player(f"human{i}", f"Human {i}")
        self.assertEqual(populace.ai_capacity(k), cap0 + 3 * populace.AI_PER_HUMAN)
        self.assertGreaterEqual(populace.systems(k), k._base_systems + 3 * populace.SYSTEMS_PER_EXPLORER)
        for sid, warps in before.items():
            # an old system may gain a bridge to the new cluster, but never loses a lane or moves
            self.assertTrue(set(warps) <= set(k.sectors[sid].warps))

    def test_a_new_cluster_has_spacefaring_peoples(self):
        k = self.k
        ok, _, ids = k.research_manager.mint_frontier_cluster(k, 2)
        self.assertTrue(ok)
        civs = [p for sid in ids for p in k.sectors[sid].planets
                if p.civilization is not None and not p.natives and p.population > 0]
        natives = [p for sid in ids for p in k.sectors[sid].planets if p.natives]
        self.assertTrue(civs or not natives)

    def test_the_imperial_heartland_is_settled(self):
        f = self.k.factions.factions["IMPERIUM"]
        systems = [s for s in f.territory if self.k.sectors[s].kind == "SYSTEM"]
        self.assertGreater(len(f.worlds), len(systems))


if __name__ == "__main__":
    unittest.main()
