"""
Two eras on one clock: the deep era runs fast while the architects lay the board; once the universe is opened to live
play the clock is the captains' - a clock year is a standard year - and no seat moves it. A served universe that was
down catches up what its orbits ran meanwhile.
"""
import random
import unittest

from xylarium.kernel import ages, clocks, cosmos, roles, tempo


class TestEras(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        random.seed(5)
        cls.k = roles.start_progenitor(7, "Observer", pick=0, pace="neighbourly")

    def test_opening_locks_the_clock_to_the_captains(self):
        k = self.k
        self.assertFalse(cosmos.live(k))
        before = cosmos.deep_gyr(k)
        rec = cosmos.open_universe(k, "a test")
        self.assertTrue(cosmos.live(k))
        self.assertAlmostEqual(rec["epoch"], before, places=9)            # deep time runs on, unbroken
        self.assertEqual(cosmos.ruler(k), cosmos.LIVE_YEARS_PER_YEAR)
        for _ in range(100):                                              # a clock year, its seasons and all
            k.tick_simulation()
        self.assertEqual(cosmos.ruler(k), cosmos.LIVE_YEARS_PER_YEAR)     # no watched people slows or speeds it
        self.assertAlmostEqual((cosmos.deep_gyr(k) - before) * 1e9, 1.0, places=6)   # a clock year: a year
        who = next(iter(tempo.seated(k)), None)
        if who:
            clocks.look_away(k, who, 1e6)                                 # a seat looking away moves nothing
            self.assertEqual(cosmos.ruler(k), cosmos.LIVE_YEARS_PER_YEAR)
        self.assertIs(cosmos.open_universe(k, "again"), cosmos.opened(k))  # opened once


class TestServer(unittest.TestCase):
    def test_a_server_that_was_down_catches_up(self):
        from bridge import daemon

        class K:
            def __init__(self):
                self.state, self.ticks = {}, 0

            def tick_simulation(self):
                self.ticks += 1
        k = K()
        k.state["server"] = {"wall": 1000.0}
        ran = daemon.catch_up(k, now=1000.0 + 3.5 * daemon.TICK_S)
        self.assertEqual((ran, k.ticks), (3, 3))
        self.assertGreater(k.state["server"]["wall"], 1000.0)


if __name__ == "__main__":
    unittest.main()
