"""
Energy is conserved, traded where it is made, packed into fuel when spare; each people builds its own way of
catching it; and a core bored past its margin costs the world its air.
"""

import random
import unittest

from xylarium.kernel import energy, harvest, matter
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply


def money(k):
    return {c: b["total"] for c, b in money_supply(k).items()}


def industrial(k):
    return [p for s in k.sectors.values() for p in s.planets
            if p.population > 0 and not p.natives and p.citadel_level >= 1]


class TestEnergy(unittest.TestCase):
    def setUp(self):
        random.seed(71)
        self.k = GameKernel(seed=7)
        self.k.activate()

    def test_a_season_balances_energy_money_and_matter(self):
        k = self.k
        k.cycle_count = 100
        harvest.season(k)                                  # the endowment and a year's works
        t0, n0 = matter.totals(k), k.matter.net()
        m0 = money(k)
        energy.season(k)
        self.assertEqual(energy.residual(k), 0)
        self.assertEqual(m0, money(k))
        t1, n1 = matter.totals(k), k.matter.net()
        undeclared = {c: d for c in set(t0) | set(t1) | set(n1)
                      if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}
        self.assertEqual(undeclared, {})

    def test_an_industrial_world_short_of_energy_loses_its_industry(self):
        w = industrial(self.k)[0]
        w.society["energy_sufficiency"] = 0.0
        self.assertAlmostEqual(energy.output_factor(w), 1.0 - energy.industry_share(w))
        w.society["energy_sufficiency"] = 1.0
        self.assertEqual(energy.output_factor(w), 1.0)

    def test_spare_energy_becomes_hydrogen(self):
        k = self.k
        w = industrial(k)[0]
        w.element_reserves["H2O"] = 100
        h0 = w.element_reserves.get("H", 0)
        used = energy._pack_fuel(k, w, int(10 * energy.ELECTROLYSIS_EU * energy.MILLI))
        self.assertEqual(w.element_reserves["H"] - h0, 10)
        self.assertEqual(used, int(10 * energy.ELECTROLYSIS_EU * energy.MILLI))


class TestHarvest(unittest.TestCase):
    def setUp(self):
        random.seed(73)
        self.k = GameKernel(seed=7)
        self.k.activate()

    def test_peoples_build_from_what_they_know(self):
        from xylarium.kernel import chemistry, knowledge
        k = self.k
        worlds = industrial(k)
        a = worlds[0]
        ha = knowledge.holder_of_planet(a)
        b = next(w for w in worlds if knowledge.holder_of_planet(w) != ha)
        hb = knowledge.holder_of_planet(b)
        chemistry.stats(k)["known"][ha] = ["Si", "Cu", "H2O"]
        chemistry.stats(k)["known"][hb] = ["Ti", "Fe", "H"]
        da, db = harvest.design(k, ha, "field", a), harvest.design(k, hb, "field", b)
        self.assertNotEqual(set(da["inputs"]), set(db["inputs"]))
        self.assertNotEqual(da["name"], db["name"])
        chemistry.stats(k)["known"][ha] = ["H"]                     # knows no metal at all
        self.assertIsNone(harvest.design(k, ha, "field", a))
        self.assertEqual(harvest.crude(k, "field", a)["inputs"], {})  # but ore mirrors are always possible

    def test_a_core_bored_past_its_margin_loses_its_air_and_the_harm_is_counted(self):
        from xylarium.kernel import biosphere, geology
        k = self.k
        w = next(p for p in industrial(k) if geology.rocky(p) and not geology.airless(p))
        harvest.works(w)["tap"] = 20                                # a hundred percent of its core's flow
        k0 = biosphere.carrying_capacity(k, w)
        for _ in range(12):
            harvest._cores(k)
        self.assertLess(float(w.society["dynamo"]), 0.5)
        self.assertLess(float(w.society["atmosphere"]), 1.0)
        self.assertLess(biosphere.carrying_capacity(k, w), k0)
        self.assertGreater(harvest.stats(k)["people_unfed"], 0)
        harvest.works(w)["tap"] = 0                                 # the bores stop: the dynamo comes back
        for _ in range(60):
            harvest._cores(k)
        self.assertGreater(float(w.society["dynamo"]), 0.5)

    def test_a_shell_of_arrays_dims_the_worlds_beyond_it(self):
        from xylarium.kernel import physics
        k = self.k
        w = industrial(k)[0]
        sec = k.sectors[w.sector_id]
        before = physics.planet_flux(sec, w)
        harvest.stats(k)["arrays"][str(sec.id)] = {"civ:Builders": 10 ** 12}
        harvest._reshade(k)
        self.assertLess(physics.planet_flux(sec, w), before)


if __name__ == "__main__":
    unittest.main()
