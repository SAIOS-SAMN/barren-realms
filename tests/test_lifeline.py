"""
Life on a world is a running process; the schedule is its forecast while nothing interferes. A mind acting on a
world re-resolves its life from the world as it now stands: ended where no living medium is left, otherwise its
climbed rungs kept and the rest drawn afresh.
"""

import unittest

from xylarium.kernel import cosmos, imprint, lifeline
from xylarium.kernel.engine import GameKernel


class TestLifeline(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.st = cosmos.stats(self.k)
        self.nxt = self.st["minds"][1]
        sid = cosmos.build_slot(self.k, tuple(self.nxt["cell"]), int(self.nxt["k"]))
        self.world = self.k.sectors[sid].planets[self.nxt["w"]]

    def _to(self, epoch):
        self.k.cycle_count = int((epoch - self.st["epoch0"]) * 1e9 / cosmos.ruler(self.k) * 100) + 1
        cosmos._due(self.k)

    def test_a_broken_world_never_raises_its_forecast_mind(self):
        imprint.record(self.k, self.world, "shattered", "Raider", air_set=0.0, type="BARREN")
        self.assertIn(lifeline.key_of(self.nxt), lifeline.stats(self.k)["ended"])
        self._to(self.nxt["epoch"])
        self.assertEqual(self.st["arisen"], 1)
        self.assertIsNone(self.world.civilization)

    def test_a_disturbed_world_keeps_its_rungs_and_draws_the_rest_afresh(self):
        imprint.record(self.k, self.world, "stripped", "Raider", air_scale=0.9)
        got = lifeline.stats(self.k)["redrawn"].get(lifeline.key_of(self.nxt)) or \
            lifeline.stats(self.k)["ended"].get(lifeline.key_of(self.nxt))
        self.assertIsNotNone(got)
        if "steps" in got:
            now = cosmos.deep_gyr(self.k)
            kept = [t for t in self.nxt["steps"] if t <= now]
            self.assertEqual(got["steps"][:len(kept)], kept)
            self.assertGreaterEqual(got["epoch"], round(now, 6))
            self.assertTrue(lifeline.overridden(self.k, self.nxt))

    def test_an_undisturbed_world_follows_its_forecast(self):
        self.assertFalse(lifeline.overridden(self.k, self.nxt))
        self._to(self.nxt["epoch"])
        self.assertEqual(self.st["arisen"], 2)


if __name__ == "__main__":
    unittest.main()
