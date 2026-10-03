"""
The clock is the camera: deep time runs as fast as it can without stepping over a living people's next turning,
and is accumulated exactly through every change of rate.
"""

import unittest

from xylarium.kernel import cosmos, tempo
from xylarium.kernel.engine import GameKernel


class TestTempo(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()

    def test_every_place_keeps_its_own_time_and_peoples_meet_by_their_ledgers(self):
        from xylarium.kernel import clocks, relations
        who = sorted(relations._peoples(self.k))[0]
        home = max(relations._peoples(self.k)[who], key=lambda p: p.population)
        self.assertTrue(clocks.own(self.k, who))
        self.assertLess(clocks.rate(self.k, who), cosmos.ceiling(self.k))     # its history's pace
        self.assertEqual(tempo.desired(self.k), cosmos.ceiling(self.k))       # cosmic time runs on
        self.k.cycle_count = 1000
        self.assertLess(clocks.now(self.k, who), cosmos.deep_gyr(self.k))      # its place lives at its own pace
        self.assertEqual(cosmos.deep_gyr(self.k, sector_id=home.sector_id), clocks.now(self.k, who))
        before = clocks.now(self.k, who)
        clocks.set_pace(self.k, home.sector_id, cosmos.ceiling(self.k))
        self.assertAlmostEqual(clocks.now(self.k, who), before, places=12)     # a clock never jumps
        clocks.stats(self.k)["peoples"]["civ:Other"] = {"home": 999, "h": 7, "links": {}}
        clocks.link(self.k, who, "civ:Other", "their ships meet")
        self.assertEqual(clocks.height(self.k, who), 8)                        # h = 1 + max(own, other's)
        self.assertEqual(clocks.height(self.k, "civ:Other"), 8)

    def test_motion_composes_by_one_law(self):
        from xylarium.kernel import geometry
        self.assertAlmostEqual(geometry.flow(0.5, 0.5, 1.0), 0.8)            # Einstein's addition
        self.assertAlmostEqual(geometry.flow(1 / 7, 2 / 5, 0.0), 19 / 35)    # the null flow simply adds
        self.assertLess(geometry.flow(0.9, 0.9, 1.0), 1.0)                   # never light

    def test_deep_time_is_continuous_through_a_change_of_rate(self):
        rate0 = cosmos.ruler(self.k)                                     # set when the first mind woke
        self.k.cycle_count = 400
        before = cosmos.deep_gyr(self.k)
        cosmos.set_rate(self.k, 50.0)
        self.assertAlmostEqual(cosmos.deep_gyr(self.k), before, places=12)
        self.k.cycle_count = 500
        self.assertAlmostEqual(cosmos.deep_gyr(self.k) - before, 50.0 / 1e9, places=15)
        self.assertEqual(cosmos.cycle_at(self.k, cosmos.deep_gyr(self.k, 450)), 450)
        self.assertAlmostEqual(cosmos.deep_gyr(self.k, 200), cosmos.stats(self.k)["epoch0"] + 2.0 * rate0 / 1e9,
                               places=12)


if __name__ == "__main__":
    unittest.main()
