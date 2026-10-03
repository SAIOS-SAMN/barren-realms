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

    def test_a_rising_people_slows_the_clock(self):
        self.assertLess(tempo.desired(self.k), cosmos.ceiling(self.k))
        self.assertGreaterEqual(tempo.desired(self.k), 1.0)

    def test_deep_time_is_continuous_through_a_change_of_rate(self):
        self.k.cycle_count = 400
        before = cosmos.deep_gyr(self.k)
        cosmos.set_rate(self.k, 50.0)
        self.assertAlmostEqual(cosmos.deep_gyr(self.k), before, places=12)
        self.k.cycle_count = 500
        self.assertAlmostEqual(cosmos.deep_gyr(self.k) - before, 50.0 / 1e9, places=15)
        self.assertEqual(cosmos.cycle_at(self.k, cosmos.deep_gyr(self.k, 450)), 450)
        self.assertAlmostEqual(cosmos.deep_gyr(self.k, 200), cosmos.stats(self.k)["epoch0"] +
                               2.0 * cosmos.ceiling(self.k) / 1e9, places=12)


if __name__ == "__main__":
    unittest.main()
