"""
The universe is determined by its seed and its laws; only minds are probabilistic. A physical season - stars, orbits,
climate, interiors, the galaxy around - draws no chance at run time: not from the shared stream, and not from any
stream keyed to the clock. Its initial conditions are the seed's (keyed by place, never by when anyone looks).
"""

import random
import unittest
from unittest import mock

from xylarium.kernel import scheduler, subsystem
from xylarium.kernel.engine import GameKernel

PHYSICAL = ("cosmos", "climate", "cluster", "sphere", "blackhole", "geology", "physics", "energy", "signals",
            "mastery")
GLOBAL = ("random", "gauss", "uniform", "choice", "choices", "randint", "randrange", "expovariate", "shuffle",
          "sample")


class TestTheUniverseDoesNotDraw(unittest.TestCase):
    def test_physical_seasons_draw_no_chance(self):
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        drawn = []

        def refuse(name):
            def f(*a, **kw):
                drawn.append(("shared", name))
                raise AssertionError(f"a physical season drew random.{name}")
            return f

        real_rng = scheduler.rng

        def watched(kernel, *parts):
            if kernel.cycle_count in parts:
                drawn.append(("clock", parts[:2]))
            return real_rng(kernel, *parts)

        patches = [mock.patch.object(random, n, refuse(n)) for n in GLOBAL] + \
                  [mock.patch.object(scheduler, "rng", watched)]
        for p in patches:
            p.start()
        try:
            for year in range(1, 5):
                k.cycle_count = year * 100
                for name in PHYSICAL:
                    sub = subsystem.get(name)
                    if sub is not None and sub.season is not None:
                        sub.season(k)
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(drawn, [])


if __name__ == "__main__":
    unittest.main()
