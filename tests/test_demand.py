"""
Demand: water-life eats salt with its food (its own beds, its stores, its port), and health reads the share met;
what a world cannot get at home it wants, and a port (or, without one, the world's own office) brings it from the
good's landed source - the source paid its price and haul, nothing minted.
"""

import random
import unittest
from unittest import mock

from xylarium.kernel import biosphere, demand, ledger, lifespan, supply
from xylarium.kernel.engine import GameKernel


class TestDemand(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        self.k.activate()
        self.w = max((p for s in self.k.sectors.values() for p in s.planets if p.population > 0),
                     key=lambda p: p.population)

    def test_water_life_eats_salt_from_its_own_beds_first(self):
        self.w.element_reserves.pop("NaCl", None)
        self.w.society.pop("halite_dug", None)
        with mock.patch.object(biosphere, "metabolism_of", return_value="biotic"), \
                mock.patch.object(supply, "_halite_cached", return_value=10 ** 6):
            met = demand.diet(self.k, self.w)
        self.assertEqual(met, 1.0)
        self.assertGreater(self.w.society.get("halite_dug", 0), 0)
        self.assertNotIn("NaCl", demand.wants(self.w))

    def test_a_world_with_no_salt_wants_it_and_its_health_falls(self):
        self.w.element_reserves.pop("NaCl", None)
        sec = self.k.sectors[self.w.sector_id]
        if sec.port is not None:
            sec.port.stock["NaCl"] = 0
        before = lifespan.thr(self.k, self.w)
        with mock.patch.object(biosphere, "metabolism_of", return_value="biotic"), \
                mock.patch.object(supply, "_halite_cached", return_value=0):
            for _ in range(8):
                demand.diet(self.k, self.w)
        self.assertGreater(demand.wants(self.w).get("NaCl", 0), 0)
        self.assertLess(demand.salt_share(self.w), 0.5)
        self.assertLess(lifespan.thr(self.k, self.w), before)

    def test_life_that_needs_no_sodium_eats_none(self):
        with mock.patch.object(biosphere, "metabolism_of", return_value="mineral"):
            self.assertEqual(demand.diet(self.k, self.w), 1.0)
        self.assertEqual(demand.salt_share(self.w), 1.0)

    def test_a_want_is_the_standing_shortfall_and_landing_answers_it(self):
        self.w.society.pop("wants", None)
        demand.want(self.w, "Fe", 5)
        demand.want(self.w, "Fe", 3)
        self.assertEqual(demand.wants(self.w), {"Fe": 5})            # renewed, not piled up
        demand.answered(self.w, "Fe", 5)
        self.assertEqual(demand.wants(self.w), {})

    def test_a_port_brings_what_its_worlds_want_and_money_only_moves(self):
        sec = self.k.sectors[self.w.sector_id]
        port = sec.port
        if port is None:
            self.skipTest("no port here")
        src = next(s for s in self.k.sectors.values() if s.port is not None and s.id != sec.id
                   and self.k.find_path(s.id, sec.id))
        src.port.stock["NaCl"] = 500
        port.stock["NaCl"] = 0
        port.treasury = 10 ** 7
        demand.want(self.w, "NaCl", 40)
        before = {c: v["total"] for c, v in ledger.money_supply(self.k).items()}
        with mock.patch.object(supply, "best", return_value=(20.0, src.id, 10.0)):
            got = demand.carry(self.k, sec)
        self.assertGreater(got, 0)
        self.assertEqual(port.stock["NaCl"], got)
        self.assertEqual(src.port.stock["NaCl"], 500 - got)
        after = {c: v["total"] for c, v in ledger.money_supply(self.k).items()}
        if port.currency == src.port.currency:
            self.assertEqual(before.get(port.currency), after.get(port.currency))   # paid, not minted


if __name__ == "__main__":
    unittest.main()
