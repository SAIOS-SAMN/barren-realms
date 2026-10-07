"""Who is ancient, and who was first, is the seed's - read from the whole schedule, never from the window of minds about
to wake, so it never drifts as the clock runs."""

import unittest

from xylarium.kernel import cosmos, roles
from xylarium.kernel.engine import GameKernel


class TestAncientsDoNotDrift(unittest.TestCase):
    def test_the_window_moving_changes_nothing(self):
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        before = (roles.ancients(k), roles.first_minds(k))
        cosmos.stats(k)["minds"] = cosmos.stats(k)["minds"][len(cosmos.stats(k)["minds"]) // 2:]   # the window slides
        self.assertEqual((roles.ancients(k), roles.first_minds(k)), before)


if __name__ == "__main__":
    unittest.main()
