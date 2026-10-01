"""
One universal clock: orbits are functions of time, minds act at their own pace, and every roll of the dice is locked
to the universe - the same seed makes the same universe however it is run.
"""

import random
import unittest

from xylarium.kernel import clock, physics, scheduler
from xylarium.kernel.engine import GameKernel


def _fingerprint(k):
    worlds = [(p.id, p.population, p.citadel_level, p.treasury) for s in sorted(k.sectors) for p in k.sectors[s].planets]
    caps = [(c.id, c.sector_id, c.credits) for c in sorted(k.captains.values(), key=lambda c: c.id)]
    return worlds, caps, k.state.get("genesis", {}).get("firsts")


class TestLockedChance(unittest.TestCase):
    def test_streams_are_fixed_by_seed_and_actor(self):
        k = type("K", (), {"seed": 7})()
        self.assertEqual(scheduler.stream(k, "mind", "a", 5), scheduler.stream(k, "mind", "a", 5))
        self.assertNotEqual(scheduler.stream(k, "mind", "a", 5), scheduler.stream(k, "mind", "b", 5))
        self.assertNotEqual(scheduler.stream(k, "mind", "a", 5), scheduler.stream(k, "mind", "a", 6))
        scheduler.lock(k, "x")
        a = random.random()
        scheduler.lock(k, "x")
        self.assertEqual(a, random.random())

    def test_universe_ignores_the_callers_dice(self):
        """Whatever the global random state before each cycle, the universe rolls its own."""
        runs = []
        for outside in (1, 99):
            k = GameKernel(seed=11, genesis="primordial")
            k.activate()
            for c in range(20):
                random.seed(outside * 1000 + c)
                k.tick_simulation()
            runs.append(_fingerprint(k))
        self.assertEqual(runs[0], runs[1])


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.k = type("K", (), {"seed": 3, "cycle_count": 10, "state": {}})()
        self.calls = []

        @scheduler.handler("test")
        def _h(kernel, entity):
            self.calls.append((kernel.cycle_count, entity, random.random()))
            return scheduler.MOMENTS // 2 if entity == "quick" else None

    def tearDown(self):
        scheduler.HANDLERS.pop("test", None)

    def test_order_budget_and_quick_minds(self):
        t = scheduler.now_moment(self.k)
        scheduler.at(self.k, t + 10, "test", "b")
        scheduler.at(self.k, t + 10, "test", "a")
        scheduler.at(self.k, t, "test", "quick")
        scheduler.at(self.k, t + 2 * scheduler.MOMENTS, "test", "later")
        ran = scheduler.run_due(self.k, ("test",), budget=3)
        self.assertEqual(ran, 3)
        # time order, then the entity's name - never a dictionary's order
        self.assertEqual([c[1] for c in self.calls], ["quick", "a", "b"])
        # a mind twice our speed acts again within the cycle, but past the budget it waits (first in line)
        self.assertIn((t + scheduler.MOMENTS // 2, "test", "quick"), scheduler.pending(self.k))
        self.calls.clear()
        self.k.cycle_count += 1
        scheduler.run_due(self.k, ("test",))
        self.assertEqual([c[1] for c in self.calls][:1], ["quick"])

    def test_each_event_has_its_own_dice(self):
        t = scheduler.now_moment(self.k)
        scheduler.at(self.k, t, "test", "a")
        scheduler.run_due(self.k, ("test",))
        alone = self.calls[-1][2]
        self.k.state.clear()
        self.calls.clear()
        scheduler.at(self.k, t, "test", "a")
        scheduler.at(self.k, t, "test", "0first")           # another mind acting first does not change a's luck
        scheduler.run_due(self.k, ("test",))
        self.assertEqual([c for c in self.calls if c[1] == "a"][0][2], alone)

    def test_pace_follows_the_substrate(self):
        self.assertEqual(scheduler.pace("biotic"), scheduler.MOMENTS)
        self.assertLess(scheduler.pace("plasmic"), scheduler.MOMENTS)      # hot minds are quick
        self.assertGreater(scheduler.pace("cryogenic"), scheduler.MOMENTS)  # cold minds slow


class TestClock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = GameKernel(seed=5, genesis="primordial")

    def test_orbital_velocity_is_measured(self):
        p = next(p for s in self.k.sectors.values() for p in s.planets if getattr(p, "body", None))
        v = clock.velocity_of(self.k, p)
        self.assertAlmostEqual(v["phase_rate"] * v["year_cycles"], 1.0)
        self.assertAlmostEqual(v["deg_per_cycle"], 360.0 / v["year_cycles"])
        m = clock.measure(self.k)
        self.assertGreater(m["bodies"], 0)
        self.assertLessEqual(m["year_cycles"]["min"], m["year_cycles"]["max"])

    def test_any_moment_is_computed_not_stepped(self):
        p = next(p for s in self.k.sectors.values() for p in s.planets if getattr(p, "body", None))
        far = 10 ** 9 + 7
        year = clock.year_of(self.k, p)
        ph = clock.phase(self.k, p, far)
        self.assertTrue(0 <= ph < 1)
        # a whole number of its years later it is back where it was (exact clockwork)
        if year.denominator == 1:
            self.assertEqual(clock.phase(self.k, p, far + int(year)), ph)
        sky = clock.ephemeris(self.k, far)
        self.assertEqual(len(sky), sum(len(s.planets) for s in self.k.sectors.values()))

    def test_elapsed_and_velocity(self):
        rec = {}
        self.assertEqual(clock.elapsed(rec, "t", 100), 0)
        self.assertEqual(clock.elapsed(rec, "t", 125), 25)
        clock.set_velocity(self.k, 50)
        self.assertEqual(clock.velocity(self.k), 50.0)
        clock.set_velocity(self.k, -3)
        self.assertEqual(clock.velocity(self.k), 0.0)


if __name__ == "__main__":
    unittest.main()
