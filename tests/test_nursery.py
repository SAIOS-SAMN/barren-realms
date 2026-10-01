"""
Meaning, nurseries, blight and the viability gate: each people's biology has a ceiling, technology can lift it only
while it is fed, density breeds plague, and only a people sustaining itself sends settler fleets.
"""

import math
import random
import unittest

from xylarium.config import MEANING_FLOOR, NURSERIES, VIABILITY_QUARTERS
from xylarium.kernel import demography, fertility, matter, nursery
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply


def fresh(seed=7, rseed=211):
    random.seed(rseed)
    k = GameKernel(seed=seed)
    k.activate()
    return k


def world_of(kernel, strat):
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population > 0 and not p.natives and fertility.strategy(kernel, p) == strat:
                return p
    return None


def money(k):
    return {c: b["total"] for c, b in money_supply(k).items()}


def undeclared(k, t0, n0):
    t1, n1 = matter.totals(k), k.matter.net()
    return {c: d for c in set(t0) | set(t1) | set(n1)
            if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}


class TestMeaning(unittest.TestCase):
    def setUp(self):
        self.k = fresh()
        self.w = world_of(self.k, "K")

    def test_discovery_lifts_and_fades(self):
        w, k = self.w, self.k
        base, _ = fertility.meaning(k, w)
        fertility.discovered(k, planet=w)
        lifted, parts = fertility.meaning(k, w)
        self.assertAlmostEqual(lifted - base, 0.25, places=3)
        k.cycle_count += 1000
        self.assertEqual(fertility.meaning(k, w)[1]["discovery"], 0.0)

    def test_comfortable_quiet_decays_toward_the_floor(self):
        w, k = self.w, self.k
        w.society["lux_access"] = 0.9
        w.society["founded_cycle"] = 0
        k.cycle_count = 5000
        w.society["discovery_cycle"] = -10 ** 9
        mu, parts = fertility.meaning(k, w)
        self.assertLess(mu, 1.0)
        self.assertGreater(parts["stagnation"], 0)
        self.assertGreaterEqual(mu, MEANING_FLOOR)
        w.society["lux_access"] = 0.1                       # a poor world is not satiated
        self.assertEqual(fertility.meaning(k, w)[1]["stagnation"], 0.0)

    def test_the_rebound_after_a_crisis(self):
        w, k = self.w, self.k
        w.society["rebound_until"] = k.cycle_count + 200
        self.assertEqual(fertility.meaning(k, w)[1]["rebound"], 0.30)

    def test_meaning_weighs_as_much_as_births_are_a_choice(self):
        k = self.k
        r = world_of(k, "r")
        if r is None:
            self.skipTest("no r-strategist world on this seed")
        f0, _ = fertility.fertility(k, r)
        fertility.discovered(k, planet=r)
        f1, _ = fertility.fertility(k, r)
        self.assertAlmostEqual(f0, f1, places=6)            # a clutch is not a decision


class TestNursery(unittest.TestCase):
    def test_artificial_wombs_lift_a_transitioned_people_and_cost_what_they_use(self):
        k = fresh()
        w = world_of(k, "K")
        w.society.update(basket_fill=1.0, lux_access=1.0)
        w.citadel_level = 3
        w.treasury, w.ore_silo, w.organics_silo = 200_000, 5_000, 100_000
        before, _ = fertility.natural(k, w)
        m0, t0, n0 = money(k), matter.totals(k), k.matter.net()
        nursery.build(k, w)
        self.assertIsNone(nursery.upkeep(k, w))
        self.assertTrue(nursery.online(w))
        after, parts = fertility.natural(k, w)
        self.assertGreater(after, before)
        self.assertEqual(parts.get("nursery"), 1.0)
        self.assertEqual(m0, money(k))
        self.assertEqual(undeclared(k, t0, n0), {})

    def test_unfed_it_goes_dark_and_the_brood_is_lost(self):
        k = fresh()
        w = world_of(k, "K")
        w.society["nursery"] = {"kind": "K", "built": 0, "online": True}
        w.organics_silo, w.treasury = 0, 0
        from xylarium.kernel.colony import ColonyManager
        port = ColonyManager._contractor_port(w, k)
        if port is not None:
            port.stock["ORGANICS"] = 0
        pop = w.population
        log = nursery.upkeep(k, w)
        self.assertIsNotNone(log)
        self.assertFalse(nursery.online(w))
        self.assertLess(w.population, pop)
        self.assertEqual(fertility.natural(k, w)[1].get("nursery"), None)

    def test_a_world_without_the_engineering_cannot_build(self):
        k = fresh()
        w = world_of(k, "K")
        w.citadel_level = 1
        if w.civilization is not None:
            w.civilization.tech_level = 1
        w.treasury, w.ore_silo = 10 ** 6, 10 ** 4
        with self.assertRaises(ValueError):
            nursery.build(k, w)

    def test_a_foundry_nursery_feeds_lithic_budding(self):
        k = fresh()
        w = world_of(k, "lithic")
        if w is None:
            self.skipTest("no lithic world on this seed")
        w.element_reserves.pop("Fe", None)
        w.element_reserves.pop("Ti", None)
        w.ore_silo = 0
        before, _ = fertility.natural(k, w)
        w.society["nursery"] = {"kind": "lithic", "built": 0, "online": True}
        after, parts = fertility.natural(k, w)
        self.assertEqual(parts["metal"], 1.0)
        self.assertGreater(after, before)


class TestBlight(unittest.TestCase):
    def test_final_size_solves_the_sir_relation(self):
        self.assertEqual(nursery.final_size(0.9), 0.0)
        z = nursery.final_size(2.0)
        self.assertAlmostEqual(z, 1 - math.exp(-2.0 * z), places=9)
        self.assertAlmostEqual(z, 0.7968, places=3)

    def test_a_crowded_r_world_is_struck_and_the_granary_rot_is_declared(self):
        k = fresh()
        w = world_of(k, "r")
        if w is None:
            self.skipTest("no r-strategist world on this seed")
        w.population = int(demography.housing_cap(w, k) * 1.2)
        w.organics_silo = 10_000
        self.assertGreater(nursery.r0(k, w), 1.0)
        t0, n0 = matter.totals(k), k.matter.net()
        struck = None
        for q in range(40):
            k.cycle_count += 25
            struck = nursery.blight(k, w) or struck
        self.assertIsNotNone(struck)
        self.assertTrue(fertility.stressed(k, w) or nursery.stats(k)["blights"] > 0)
        self.assertEqual(undeclared(k, t0, n0), {})

    def test_sanitation_lowers_transmission(self):
        k = fresh()
        w = world_of(k, "r")
        if w is None:
            self.skipTest("no r-strategist world on this seed")
        w.population = int(demography.housing_cap(w, k) * 0.95)
        bare = nursery.r0(k, w)
        w.society["nursery"] = {"kind": "r", "built": 0, "online": True}
        self.assertAlmostEqual(nursery.r0(k, w), bare * NURSERIES["r"]["r0"])
        self.assertLess(nursery.r0(k, w), 1.0)


class TestViability(unittest.TestCase):
    def test_a_people_not_sustaining_itself_sends_no_fleet(self):
        k = fresh()
        home = next(p for p in k.sectors[1].planets if p.population > 0)
        home.citadel_level, home.population = 3, 200_000
        home.treasury, home.ore_silo, home.organics_silo = 500_000, 5_000, 50_000
        home.last_daughter_quarter = -10 ** 6
        home.society["viable_quarters"] = VIABILITY_QUARTERS - 1
        self.assertIsNone(demography.send_settlers(k, home))
        self.assertEqual(nursery.stats(k)["gated"], 1)
        home.society["fertility"] = 1.1
        nursery.track_viability(home)
        self.assertTrue(nursery.viable(home))

    def test_the_seeding_kit_limits_the_fleet(self):
        k = fresh()
        home = next(p for p in k.sectors[1].planets if p.population > 0)
        home.organics_silo = 0
        from xylarium.kernel.colony import ColonyManager
        port = ColonyManager._contractor_port(home, k)
        if port is not None:
            port.stock["ORGANICS"] = 0
        self.assertEqual(nursery.kit_room(k, home, "biotic", 20_000), 0)
        from xylarium.kernel.luxury import _reserve
        home.organics_silo = _reserve(k, home, "ORGANICS")   # the granary's own two seasons are not for the fleet
        self.assertEqual(nursery.kit_room(k, home, "biotic", 20_000), 0)
        home.organics_silo += 100                             # 10 per thousand: enough for 10,000
        self.assertEqual(nursery.kit_room(k, home, "biotic", 20_000), 10_000)


if __name__ == "__main__":
    unittest.main()
