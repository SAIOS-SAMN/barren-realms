"""
Fibres: warp lanes with an antisymmetric flow ledger, development, economies of scale, fibre distance.
"""

import unittest

from xylarium.kernel import fibres
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType


class TestFibres(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=7)
        self.cap = self.kernel.register_player("hauler", "Hauler")
        self.kernel.tick_simulation = lambda: None

    def shuttle(self, a, b, n, ore=20):
        cap = self.cap
        for _ in range(n):
            cap.ship.cargo.ore = ore
            fibres.record(self.kernel, cap, a, b)
            cap.ship.cargo.ore = 0
            fibres.record(self.kernel, cap, b, a)

    def test_the_flow_ledger_is_antisymmetric(self):
        a, b = 1, self.kernel.sectors[1].warps[0]
        self.shuttle(a, b, 3)
        self.assertGreater(fibres.net_flow(self.kernel, a, b), 0)          # goods went a -> b, returned empty
        self.assertEqual(fibres.net_flow(self.kernel, a, b), -fibres.net_flow(self.kernel, b, a))
        self.assertLess(fibres.divergence(self.kernel, b), 0)                # b is a net importer

    def test_busy_lanes_get_cheaper_relative_to_the_galaxy(self):
        a, b = 1, self.kernel.sectors[1].warps[0]
        c = next(w for w in self.kernel.sectors[b].warps if w != a)
        self.shuttle(a, b, 30)
        self.shuttle(b, c, 3)
        fibres.season(self.kernel)
        busy, quiet = fibres.cost(self.kernel, a, b), fibres.cost(self.kernel, b, c)
        self.assertLess(busy, quiet)
        self.assertGreaterEqual(busy, fibres.MIN_COST)
        # Scale invariance: ten times the traffic everywhere changes nothing
        st = fibres.state(self.kernel)
        st["dev"] = {k: v * 10 for k, v in st["dev"].items()}
        st["mean"] = fibres.mean_development(self.kernel)
        self.assertAlmostEqual(fibres.cost(self.kernel, a, b), busy)

    def test_trunk_routes_pull_remote_ports_closer(self):
        port_sec = max((s for s in self.kernel.sectors.values() if s.port is not None),
                       key=lambda s: s.port.remoteness)
        before = port_sec.port.remoteness
        path = self.kernel.find_path(1, port_sec.id)
        for a, b in zip(path, path[1:]):
            self.shuttle(a, b, 40)
        fibres.season(self.kernel)
        self.assertLess(port_sec.port.remoteness, before)

    def test_crews_cost_less_along_a_developed_fibre(self):
        cap = self.cap
        a = cap.sector_id
        b = self.kernel.sectors[a].warps[0]
        self.shuttle(a, b, 50)
        fibres.season(self.kernel)
        cap.wages_due = 0
        self.kernel.dispatch("hauler", ActionType.MOVE, destination=b)
        cheap = cap.wages_due
        self.assertLess(cheap, self.kernel.crew_wage(cap))

    def test_routes_bend_around_a_spacetime_shock_and_return_as_it_radiates_away(self):
        k = self.kernel
        # find two sectors with at least two distinct routes
        for a in k.sectors:
            for b in k.sectors:
                if a >= b:
                    continue
                path = k.find_path(a, b)
                if len(path) < 3:
                    continue
                first_lane = (path[0], path[1])
                fibres.shock(k, *first_lane, kappa=50.0)
                detour = k.find_path(a, b)
                if detour and detour != path:
                    self.assertNotEqual((detour[0], detour[1]), first_lane)
                    while fibres.state(k).get("shock"):
                        fibres.relax(k)
                    self.assertEqual(k.find_path(a, b), path)     # the shock has radiated away
                    return
                fibres.state(k)["shock"] = {}
                fibres._bump(k)
        self.skipTest("no alternative route found")

    def test_singularities_evaporate_with_lifetime_growing_as_mass_cubed(self):
        def lifetime(mass):
            fibres.singularity(self.kernel, 5, mass)
            seasons = 0
            while "5" in fibres.state(self.kernel).get("singularities", {}):
                fibres.relax(self.kernel)
                seasons += 1
            return seasons
        small, big = lifetime(2.0), lifetime(4.0)
        self.assertAlmostEqual(big / small, 8.0, delta=1.5)          # (4/2)^3


if __name__ == "__main__":
    unittest.main()
