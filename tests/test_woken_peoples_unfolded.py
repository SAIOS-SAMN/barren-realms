"""
Every woken people lives by every law: in a universe begun at its Big Bang, a people no seat watches is not folded
off the engine's map - its world is ticked and every season sees it.
"""

import unittest
from unittest import mock

from xylarium.kernel import annals, cosmos, zones
from xylarium.kernel.engine import GameKernel


class TestWokenPeoplesUnfolded(unittest.TestCase):
    def test_an_unwatched_people_in_a_big_bang_universe_is_not_folded(self):
        k = GameKernel(seed=42)
        world = next(p for s in k.sectors.values() for p in s.planets if p.population > 0 and p.civilization)
        with mock.patch.object(cosmos, "is_cosmic", return_value=True), \
                mock.patch.object(annals, "history_decides", return_value=True):
            self.assertEqual(zones.folded_peoples(k), frozenset())
            self.assertFalse(zones.is_folded(k, world))


if __name__ == "__main__":
    unittest.main()
