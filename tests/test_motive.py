"""
Minds choose; they do not roll for what they want. A captain's fights, trips and dealings are valued options
(Lanchester odds, prizes, warrants, distance); a people's next civic work is what its world needs most.
"""

import unittest

from xylarium.kernel import motive
from xylarium.kernel.civilization import CivilizationIntelligenceEngine
from xylarium.kernel.engine import GameKernel


class TestFights(unittest.TestCase):
    def test_lanchester_square_law(self):
        self.assertAlmostEqual(motive.odds(10, 10), 0.5)
        self.assertAlmostEqual(motive.odds(20, 10), 0.8)
        self.assertEqual(motive.odds(0, 5), 0.0)

    def test_a_weak_rich_target_is_worth_more_than_a_strong_poor_one(self):
        k = GameKernel(seed=21)
        k.activate()
        ais = [c for c in k.captains.values() if c.is_ai]
        me, a, b = ais[0], ais[1], ais[2]
        sec = k.sectors[me.sector_id]
        me.ship.fighters, me.ship.shields = 100, 200
        a.ship.fighters, a.ship.shields, a.credits, a.bounty = 5, 0, 20000, 0
        b.ship.fighters, b.ship.shields, b.credits, b.bounty = 400, 400, 100, 0
        fa, fb = motive.fight(k, me, a, sec), motive.fight(k, me, b, sec)
        self.assertGreater(fa["value"] - fa["cost"], 0)
        self.assertLess(fb["value"] - fb["cost"], 0)
        self.assertGreater(fa["value"] - fa["cost"], fb["value"] - fb["cost"])

    def test_nowhere_worth_going_means_staying(self):
        k = GameKernel(seed=21)
        k.activate()
        me = next(c for c in k.captains.values() if c.is_ai)
        sec = k.sectors[me.sector_id]
        self.assertIsNone(motive.destination(k, me, sec, score=lambda sid: 0.0))
        far = max(sec.warps)
        self.assertEqual(motive.destination(k, me, sec, score=lambda sid: 1e6 if sid == far else 0.0), far)


class _Civ:
    def __init__(self, urgent):
        self.trade_urgency = urgent


class _World:
    population, morale, treasury, siege = 100000, 95, 499999, None


class TestCivicChoice(unittest.TestCase):
    def test_a_people_short_of_ore_digs_for_it(self):
        w = _World()
        self.assertEqual(CivilizationIntelligenceEngine.next_project(_Civ({"ORE": 50}), w), "Deep Mantle Siphon")

    def test_a_hungry_unhappy_people_secures_its_food(self):
        w = _World()
        w.morale = 10
        pick = CivilizationIntelligenceEngine.next_project(_Civ({}), w)
        self.assertIn(pick, ("Cryo-Vault", "Biome Spire"))
        self.assertEqual(pick, CivilizationIntelligenceEngine.next_project(_Civ({}), w))   # the same world, the same choice


if __name__ == "__main__":
    unittest.main()
