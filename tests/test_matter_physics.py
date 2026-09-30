"""
Matter physics: propulsion, yards, fabrication and slag, landfill, geology - each conserving the census.
"""

import random
import unittest
from fractions import Fraction as F

from xylarium.kernel import geology, matter, physics, propulsion
from xylarium.kernel.economy import EconomyManager
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType


def undeclared(kernel, t0, n0):
    t1, n1 = matter.totals(kernel), kernel.matter.net()
    return {c: d for c in set(t0) | set(t1) | set(n1)
            if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}


class TestPropulsion(unittest.TestCase):
    def setUp(self):
        random.seed(81)
        self.kernel = GameKernel(seed=7)
        self.kernel.tick_simulation = lambda: None
        self.cap = self.kernel.register_player("pilot", "Pilot")

    def test_heavier_ships_burn_more_and_exhaust_stays_in_the_sector(self):
        cap = self.cap
        light = propulsion.burn_for(cap.ship)
        cap.ship.cargo.ore = 200
        cap.ship.cargo.capacity = 400
        self.assertGreater(propulsion.burn_for(cap.ship), light)
        t0, n0 = matter.totals(self.kernel), self.kernel.matter.net()
        origin = self.kernel.sectors[cap.sector_id]
        gas = origin.gas
        dest = origin.warps[0]
        self.kernel.dispatch("pilot", ActionType.MOVE, destination=dest)
        self.assertGreater(origin.gas, gas)
        self.assertEqual(undeclared(self.kernel, t0, n0), {})

    def test_an_empty_bunker_coasts_slowly_rather_than_deadlocking(self):
        cap = self.cap
        cap.ship.fuel = 0
        dest = self.kernel.sectors[cap.sector_id].warps[0]
        res = self.kernel.dispatch("pilot", ActionType.MOVE, destination=dest)
        self.assertTrue(res.success)
        self.assertTrue(res.data.get("coasted"))
        self.assertGreater(res.turns_spent, 1)

    def test_bunkering_buys_the_ports_hydrogen(self):
        cap = self.cap
        sec = next(s for s in self.kernel.sectors.values() if s.port is not None)
        EconomyManager.ensure_port_inventory(sec.port)
        sec.port.stock["H"] = 500
        cap.ship.fuel = 0
        credits, till = cap.credits, sec.port.treasury
        got = propulsion.bunker(self.kernel, cap, sec)
        self.assertGreater(got, 0)
        self.assertEqual(sec.port.stock["H"], 500 - got)
        self.assertLess(cap.credits, credits)
        self.assertGreater(sec.port.treasury, till)


class TestYardsAndIndustry(unittest.TestCase):
    def setUp(self):
        random.seed(83)
        self.kernel = GameKernel(seed=7)
        self.kernel.activate()

    def test_old_hulls_are_melted_down_and_titanium_is_substituted(self):
        sol = self.kernel.sectors[1]
        EconomyManager.ensure_port_inventory(sol.port)
        sol.port.stock["Ti"] = 0
        sol.port.stock["Fe"] = 10_000
        t0, n0 = matter.totals(self.kernel), self.kernel.matter.net()
        iron = propulsion.refit(self.kernel, sol, "Scout Ship", "Merchant Cruiser")
        self.assertFalse(iron)                                  # iron stood in for the missing titanium
        self.assertEqual(undeclared(self.kernel, t0, n0), {})
        sol.port.stock["Fe"] = 0
        sol.port.stock["Ti"] = 0
        self.assertTrue(propulsion.refit(self.kernel, sol, "Scout Ship", "Merchant Cruiser"))   # short: iron frame

    def test_fabrication_needs_inputs_and_leaves_slag(self):
        port = next(s.port for s in self.kernel.sectors.values() if s.port is not None and s.port.sells.get("EQUIPMENT"))
        EconomyManager.ensure_port_inventory(port)
        port.stock["EQUIPMENT"] = 0
        port.stock["ORE"] = 0
        EconomyManager.tick_port(port)
        self.assertEqual(port.stock["EQUIPMENT"], 0)            # nothing from nothing
        port.stock["ORE"] = 100
        t0, n0 = matter.totals(self.kernel), self.kernel.matter.net()
        EconomyManager.tick_port(port)
        self.assertGreater(port.stock["EQUIPMENT"], 0)
        self.assertEqual(undeclared(self.kernel, t0, n0), {})

    def test_tailings_weigh_on_a_worlds_living_space(self):
        from xylarium.kernel import biosphere
        w = next(p for s in self.kernel.sectors.values() for p in s.planets
                 if p.civilization is not None and p.population > 0 and not p.natives)
        k0 = biosphere.carrying_capacity(self.kernel, w)
        w.element_deposits["TAILINGS"] = int(geology.TAILINGS_TOLERANCE_PER_AREA * float(physics.surface_area(w)))
        self.assertAlmostEqual(biosphere.carrying_capacity(self.kernel, w) / k0, 0.5, delta=0.02)


class TestGeology(unittest.TestCase):
    def setUp(self):
        random.seed(85)
        self.kernel = GameKernel(seed=7)
        self.kernel.activate()

    def test_a_season_of_geology_conserves_the_census(self):
        t0, n0 = matter.totals(self.kernel), self.kernel.matter.net()
        for _ in range(8):
            geology.quarter(self.kernel)
        self.assertEqual(undeclared(self.kernel, t0, n0), {})
        self.assertGreater(geology.stats(self.kernel)["implanted"], 0)   # starlight feeds airless regolith

    def test_uranium_decays_on_its_half_life(self):
        w = next(p for s in self.kernel.sectors.values() for p in s.planets if getattr(p, "body", None))
        w.element_deposits["U"] = 100_000
        seasons = geology.URANIUM_HALF_LIFE_YEARS * 4
        for _ in range(seasons // 8):
            geology.quarter(self.kernel)
        left = w.element_deposits.get("U", 0) / 100_000
        self.assertAlmostEqual(left, 0.5 ** (1 / 8), delta=0.01)

    def test_mining_draws_down_the_crust_and_heat_renews_it(self):
        w = next(p for s in self.kernel.sectors.values() for p in s.planets if geology.crust_capacity(p) > 0)
        cap = geology.crust_capacity(w)
        got = geology.mine_crust(w, 1000)
        self.assertEqual(w.element_deposits["ORE"], cap - got)
        geology._world_season(self.kernel, self.kernel.sectors[w.sector_id], w, geology.stats(self.kernel))
        self.assertGreaterEqual(w.element_deposits["ORE"], cap - got)


if __name__ == "__main__":
    unittest.main()
