"""
Matter: every unit of every commodity is somewhere, and changes only through declared processes.
"""

import random
import unittest

from xylarium.kernel import matter
from xylarium.kernel.engine import GameKernel


class TestMatterLedger(unittest.TestCase):
    def test_a_living_universe_conserves_every_commodity(self):
        import simulate_playtest as sp
        random.seed(7)
        k = GameKernel(seed=7)
        rng = random.Random(7)
        bots = sp.make_players(k, rng)
        stats = sp.RunStats()
        real = k.tick_simulation
        k.tick_simulation = lambda: None
        k.matter_audit = True
        t0, n0 = matter.totals(k), k.matter.net()
        for _ in range(250):
            for b in bots:
                b.act(k, stats)
            real()
        t1, n1 = matter.totals(k), k.matter.net()
        broken = {c: (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)) for c in set(t0) | set(t1) | set(n1)}
        self.assertEqual({c: d for c, d in broken.items() if d}, {})
        self.assertEqual(getattr(k, "matter_violations", []), [])
        self.assertGreater(k.matter.sources[("harvest", "ORGANICS")], 0)     # the ledger is alive

    def test_storage_never_destroys(self):
        class Silo:
            ore_silo = 4990
        s = Silo()
        m = matter.MatterLedger()
        matter.set_active(m)
        try:
            made = matter.produce(s, "ore_silo", "ORE", 50, "mine_face", cap=5000)
        finally:
            matter.set_active(None)
        self.assertEqual((made, s.ore_silo, m.sources[("mine_face", "ORE")]), (10, 5000, 10))

    def test_a_derelict_keeps_its_hold_as_salvage(self):
        from xylarium.kernel.nullspace import NullSpaceManager
        k = GameKernel(seed=3)
        k.activate()
        cap = k.register_player("gone", "Gone")
        cap.ship.cargo.ore = 12
        cap.ship.cargo.elements["Fe"] = 4
        before = matter.totals(k)
        NullSpaceManager.abandon_hold(k.sectors[cap.sector_id], cap, k.cycle_count)
        self.assertEqual(before, matter.totals(k))
        self.assertEqual(cap.ship.cargo.ore, 0)


if __name__ == "__main__":
    unittest.main()
