"""
Supply: the economy read from the elements the galaxy made. A port sells what its system holds and buys what it
lacks; an importer prices a good at its landed cost - the source's price plus the haul, heavier goods dearer to
carry; salt is laid down where seas evaporate, and a world that never had seas holds none.
"""

import random
import unittest
from unittest import mock

from xylarium.kernel import cosmos, supply
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.economy import EconomyManager


class TestSupply(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        self.k.activate()
        self.ports = [s for s in self.k.sectors.values() if s.port is not None]

    def test_chlorine_is_read_from_the_suns_abundances(self):
        self.assertAlmostEqual(supply.chlorine_share(), 5.24e3 / 1e6 * 35.45 / supply._silicate_per_si())
        self.assertGreater(cosmos.scatter_length("Cl"), cosmos.scatter_length("Fe"))   # lighter: it reaches further
        self.assertGreater(cosmos.scatter_length("Fe"), cosmos.scatter_length("U"))

    def test_a_port_sells_what_its_system_holds_and_buys_what_it_lacks(self):
        port = self.ports[0].port
        with mock.patch.object(supply, "system", return_value=0):
            b, s, st = supply.charter(self.k, port, "Pt", 500)
        self.assertEqual((b, s, st), (True, False, 0))
        with mock.patch.object(supply, "system", return_value=100), \
                mock.patch.object(supply, "typical", return_value=100.0):
            b, s, st = supply.charter(self.k, port, "Pt", 500)
        self.assertTrue(s)
        self.assertEqual(st, 250)                                  # as rich as the typical producer: half full

    def test_heavier_goods_cost_more_to_haul(self):
        self.assertGreater(supply.per_hop(self.k, "U"), supply.per_hop(self.k, "Fe"))
        self.assertGreater(supply.per_hop(self.k, "Fe"), supply.per_hop(self.k, "Si") * 0.99)

    def test_landed_cost_grows_with_the_haul_from_the_nearest_source(self):
        src = self.ports[0]
        for s in self.ports:
            s.port.sells["Pt"], s.port.stock["Pt"] = s is src, (100 if s is src else 0)
        got = supply.landed(self.k, "Pt")
        hop = supply.per_hop(self.k, "Pt")
        base = got[src.id][0]
        self.assertEqual(got[src.id][1], src.id)
        for nb in src.warps:
            if nb in got:
                self.assertAlmostEqual(got[nb][0], base + hop)       # one hop out: the haul added once
                self.assertEqual(got[nb][1], src.id)

    def test_an_importer_prices_a_good_at_its_landed_cost(self):
        port = self.ports[1].port
        EconomyManager.ensure_port_inventory(port)
        port.sells["Pt"], port.stock["Pt"] = True, port.max_stock.get("Pt", 500) // 2
        cheap = EconomyManager.get_unit_prices(port, "Pt")[1]
        port.landed["Pt"] = [500.0, 0, 95.0]
        dear = EconomyManager.get_unit_prices(port, "Pt")[1]
        self.assertGreater(dear, cheap * 3)
        self.assertAlmostEqual(supply.exotic(self.k, port, "Pt"), 500.0 / 95.0)

    def test_salt_lies_only_where_seas_were(self):
        w = next(p for s in self.k.sectors.values() for p in s.planets if p.planet_type not in ("GAS_GIANT",))
        dry = {"world": {"giant": False, "t_surf": 300.0, "p_bar": 1.0, "seas": {}, "ices": {}, "escaped": 0.0,
                         "degassed": 0.5}, "args": (None,) * 6 + (1.0, 8.0)}
        wet = {"world": dict(dry["world"], seas={"H2O": 1.0}), "args": dry["args"]}
        from xylarium.kernel import geology, worlds
        with mock.patch.object(geology, "crust_capacity", return_value=10 ** 8):
            with mock.patch.object(worlds, "state_of_planet", return_value=dry):
                self.assertEqual(supply.halite(self.k, w), 0)
            with mock.patch.object(worlds, "state_of_planet", return_value=wet):
                self.assertGreater(supply.halite(self.k, w), 0)

    def test_digging_salt_is_declared_and_spends_the_beds(self):
        from xylarium.kernel import matter
        self.assertIsNotNone(matter.ACTIVE)
        w = next(p for s in self.k.sectors.values() for p in s.planets)
        w.society.pop("halite_dug", None)
        w.element_deposits.pop("NaCl", None)
        w.element_reserves.pop("NaCl", None)
        key = ("evaporite", matter.key("NaCl"))
        before = matter.ACTIVE.sources.get(key, 0)
        with mock.patch.object(supply, "_halite_cached", return_value=1000):
            self.assertEqual(supply._dig(self.k, w, "NaCl", 300), 300)
            self.assertEqual(supply.held(self.k, w, "NaCl"), 700)            # the beds spent
        self.assertEqual(matter.ACTIVE.sources[key] - before, 300)          # dug: declared


if __name__ == "__main__":
    unittest.main()
