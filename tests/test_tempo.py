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

    def test_a_rising_people_keeps_its_own_clock_and_the_galaxy_runs_on(self):
        from xylarium.kernel import clocks, knowledge, relations
        who = sorted(relations._peoples(self.k))[0]
        self.assertTrue(clocks.own(self.k, who))
        self.assertLess(clocks.rate(self.k, who), cosmos.ceiling(self.k))     # its history's pace
        self.assertGreaterEqual(clocks.rate(self.k, who), 1.0)
        self.assertEqual(tempo.desired(self.k), cosmos.ceiling(self.k))       # it does not hold the galaxy back
        self.k.cycle_count = 1000
        self.assertLess(clocks.now(self.k, who), cosmos.deep_gyr(self.k))      # its world lives at its own pace
        home = max(relations._peoples(self.k)[who], key=lambda p: p.population)
        self.assertEqual(cosmos.deep_gyr(self.k, sector_id=home.sector_id), clocks.now(self.k, who))
        clocks.sync(self.k, who, "met another people")
        self.assertFalse(clocks.own(self.k, who))
        self.assertEqual(cosmos.deep_gyr(self.k, sector_id=home.sector_id), cosmos.deep_gyr(self.k))

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
