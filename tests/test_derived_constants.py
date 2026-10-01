"""
Nothing about Earth is assumed beyond its rulers: each world's core sets its own dynamo margin, each people's
biology its generation and horizon, each world's air whether fire exists - and the Terrans are measured, not used.
"""

import random
import unittest
from fractions import Fraction as F

from xylarium.kernel import decide, energy, fertility, harvest, mirror
from xylarium.kernel.engine import GameKernel


class Body:
    def __init__(self, mass, ptype="TERRESTRIAL"):
        self.body = {"mass": str(F(mass).limit_denominator(1000)), "radius": "1/1", "giant": False}
        self.planet_type = ptype
        self.society = {}


class TestDerived(unittest.TestCase):
    def test_each_core_sets_its_own_dynamo_margin(self):
        earth = harvest.dynamo_margin(Body(1))
        self.assertAlmostEqual(earth, 0.4, places=2)
        self.assertEqual(harvest.dynamo_margin(Body(0.107)), 0.0)                     # Mars-sized: already dead
        self.assertGreater(harvest.dynamo_margin(Body(1, "VOLCANIC")), earth)         # a hotter core spares more
        self.assertGreater(harvest.dynamo_margin(Body(5)), earth)                     # a larger one too

    def test_a_peoples_generation_follows_its_strategy_and_its_pace(self):
        self.assertLess(fertility.generation_years("r"), fertility.generation_years("K"))
        self.assertLess(fertility.generation_years("K", speed=2.0), fertility.generation_years("K", speed=1.0))
        hot, cold = decide.mind(None, "plasmic"), decide.mind(None, "cryogenic")
        self.assertLess(hot["horizon_q"], cold["horizon_q"])                         # quick lives plan shorter

    def test_fire_needs_air_and_a_biosphere(self):
        random.seed(91)
        k = GameKernel(seed=7)
        k.activate()
        from xylarium.kernel import geology
        w = next(p for s in k.sectors.values() for p in s.planets if p.population > 0 and not p.natives
                 and not geology.airless(p))
        self.assertEqual(energy.burns(k, w), w.civilization.metabolism in ("biotic", "umbral"))

    def test_the_terrans_are_measured_like_anyone(self):
        random.seed(93)
        k = GameKernel(seed=7, genesis="primordial")
        k.activate()
        s = mirror.summary(k)
        self.assertEqual(s["terrans"], "civ:Terran Federation")
        for key in ("energy", "predation", "intellect", "alignment", "horizon"):
            self.assertIn("percentile", s[key])


if __name__ == "__main__":
    unittest.main()
