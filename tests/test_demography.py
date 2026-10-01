"""
Demography: on-planet growth and housing technology, the choice between settler fleets and population
controls, households as starport customers, and the frontier opening as peoples fill the galaxy.
"""

import os
import random
import tempfile
import unittest

from xylarium.config import CITADEL_CONFIG, HABITATS_MAX_BY_TIER, STEADY_STATE_SHARE
from xylarium.kernel import demography, topology
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply
from xylarium.kernel.models import ActionType
from xylarium.persistence.store import StatePersistence


def totals(kernel):
    return {c: b["total"] for c, b in money_supply(kernel).items()}


def civ_world(kernel):
    """An indigenous spacefaring world with a starport of its money in reach."""
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.owner_id is None and p.civilization is not None and p.population > 0 and not p.natives:
                if demography._markets(kernel, p):
                    return p
    raise AssertionError("no indigenous world with a regional starport")


class TestHousingAndCouncils(unittest.TestCase):
    def setUp(self):
        random.seed(51)
        self.kernel = GameKernel(seed=42)
        self.kernel.activate()
        self.world = civ_world(self.kernel)

    def test_habitats_add_enclosed_farmland(self):
        from fractions import Fraction
        from xylarium.config import PEOPLE_PER_EARTH_AREA, TECH_YIELD, HABITAT_AREA
        w = self.world
        w.habitats = 0
        base = demography.housing_cap(w)
        w.habitats = 2
        added = PEOPLE_PER_EARTH_AREA * Fraction(TECH_YIELD[w.citadel_level]) * 2 * Fraction(HABITAT_AREA)
        self.assertAlmostEqual(demography.housing_cap(w) - base, int(added), delta=1)

    def test_a_crowded_world_builds_and_pays_its_contractors(self):
        w = self.world
        w.citadel_level = max(CITADEL_CONFIG)          # nothing left to raise: it digs
        w.habitats = 0
        w.population = demography.housing_cap(w)
        w.treasury = 500_000
        w.ore_silo = 5000
        w.works_ready_cycle = 0
        w.growth_policy = "expand"                     # its settler fleet has just sailed: the council digs
        w.last_daughter_quarter = self.kernel.cycle_count // demography._quarter_len()
        before = totals(self.kernel)
        demography.develop(self.kernel, w)
        self.assertEqual(w.habitats, 1)
        self.assertLess(w.treasury, 500_000)
        self.assertGreater(w.works_ready_cycle, self.kernel.cycle_count)      # construction takes time
        self.assertEqual(before, totals(self.kernel))                          # paid to the region, not the void
        demography.develop(self.kernel, w)
        self.assertEqual(w.habitats, 1)                                        # crews still busy

    def test_councils_raise_citadels_before_digging_further(self):
        w = self.world
        w.citadel_level = 1
        w.habitats = HABITATS_MAX_BY_TIER[1]
        w.population = demography.housing_cap(w)
        w.treasury, w.ore_silo, w.works_ready_cycle = 500_000, 5000, 0
        demography.develop(self.kernel, w)
        self.assertEqual(w.citadel_level, 2)


class TestTheChoice(unittest.TestCase):
    def setUp(self):
        random.seed(53)
        self.kernel = GameKernel(seed=42)
        self.kernel.activate()
        self.world = civ_world(self.kernel)
        w = self.world
        w.citadel_level = max(CITADEL_CONFIG)
        w.habitats = HABITATS_MAX_BY_TIER[w.citadel_level]
        w.population = demography.housing_cap(w)
        w.treasury, w.ore_silo, w.works_ready_cycle = 500_000, 5000, 0

    def test_population_controls_hold_numbers_below_housing(self):
        w = self.world
        w.growth_policy = None
        w.civilization.alignment = 0.9                  # a luminous, steady people
        entries = self.kernel.chronicle.next_id
        demography.develop(self.kernel, w)
        self.assertEqual(w.growth_policy, "steady")
        self.assertEqual(demography.growth_ceiling(w), int(demography.housing_cap(w) * STEADY_STATE_SHARE))
        self.assertGreater(self.kernel.chronicle.next_id, entries)          # the Covenant of Enough is recorded

    def test_expansionists_found_a_daughter_world_in_reach(self):
        w = self.world
        w.growth_policy = "expand"
        # make sure there is a free, habitable world next door
        from xylarium.kernel.universe import habitability
        metab = demography.metabolism_of(self.kernel, w)
        target = None
        for sid in topology.reach(self.kernel, w.sector_id, 3):
            for p in self.kernel.sectors[sid].planets:
                if demography.free_world(p) and habitability(metab, p.planet_type) >= 0.3:
                    target = p
                    break
            if target:
                break
        if target is None:
            self.skipTest("no free habitable world in reach on this seed")
        pop = w.population
        w.society["viable_quarters"] = 8                     # a people sustaining itself (nursery.viable)
        before = totals(self.kernel)
        demography.send_settlers(self.kernel, w)
        daughters = [p for s in self.kernel.sectors.values() for p in s.planets if p.metropole_id == w.id]
        self.assertEqual(len(daughters), 1)
        d = daughters[0]
        self.assertEqual(w.population + d.population, pop)                     # people move; none appear
        self.assertIs(d.civilization, w.civilization)                          # the same people on two worlds
        self.assertEqual(before, totals(self.kernel))


class TestHouseholdsAndFrontier(unittest.TestCase):
    def setUp(self):
        random.seed(57)
        self.kernel = GameKernel(seed=42)
        self.kernel.activate()

    def test_households_buy_their_basket_from_regional_ports(self):
        w = civ_world(self.kernel)
        w.household_purse = 200_000
        ports = demography._markets(self.kernel, w)
        till = sum(p.treasury for p in ports)
        stock = sum(p.stock.get("ORGANICS", 0) for p in ports)
        before = totals(self.kernel)
        demography.households(self.kernel)
        self.assertGreater(sum(p.treasury for p in ports), till)
        self.assertLess(sum(p.stock.get("ORGANICS", 0) for p in ports), stock)
        self.assertEqual(before, totals(self.kernel))

    def test_worlds_sell_their_surplus_to_regional_ports(self):
        w = civ_world(self.kernel)
        ports = [p for p in demography._markets(self.kernel, w) if p.buys.get("ORE")]
        if not ports:
            self.skipTest("no ore-buying port in reach on this seed")
        for p in ports:
            p.treasury += 200_000
            p.stock["ORE"] = 0
        w.ore_silo, purse = 5000, w.household_purse
        before = totals(self.kernel)
        demography.exports(self.kernel)
        self.assertLess(w.ore_silo, 5000)
        self.assertGreater(w.household_purse, purse)                 # producers are paid
        self.assertEqual(before, totals(self.kernel))

    def test_settler_pressure_opens_a_new_cluster(self):
        rm = self.kernel.research_manager
        rm.minted_clusters = [1, 2, 3] if 3 in rm.minted_clusters else rm.minted_clusters
        sectors = len(self.kernel.sectors)
        demography.frontier_state(self.kernel)["pressure"] = 99
        demography.stats(self.kernel)["last_cluster_cycle"] = -10 ** 6
        demography.frontier(self.kernel)
        self.assertGreater(len(self.kernel.sectors), sectors)
        self.assertEqual(demography.frontier_state(self.kernel)["pressure"], 0)

    def test_players_choose_their_worlds_policy_and_it_persists(self):
        cap = self.kernel.register_player("gov", "Governor")
        w = civ_world(self.kernel)
        w.owner_id = cap.id
        self.kernel.tick_simulation = lambda: None
        res = self.kernel.dispatch("gov", ActionType.POPULATION_POLICY, planet_id=w.id, policy="STEADY")
        self.assertTrue(res.success, res.message)
        self.assertEqual(w.growth_policy, "steady")
        w.habitats, w.household_purse = 2, 1234
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "s.json")
            self.assertTrue(StatePersistence.save_to_file(self.kernel, path))
            loaded = StatePersistence.load_from_file(path)
        lw = loaded.get_planet(w.id)
        self.assertEqual((lw.growth_policy, lw.habitats, lw.household_purse), ("steady", 2, 1234))

    def test_diaspora_threshold_diverts_tax_and_funds_settlers(self):
        from xylarium.kernel.colony import ColonyManager
        w = civ_world(self.kernel)
        w.population = int(demography.housing_cap(w) * 0.96)
        w.crowded_cycles = 51
        w.organics_silo = 50000
        w.treasury = 500
        w.diaspora_escrow = 0
        ColonyManager.tick_colony(w, self.kernel)
        self.assertGreater(w.diaspora_escrow, 0)
        # Fund settler ship from escrow
        w.diaspora_escrow = 20_000
        w.society["viable_quarters"] = 8
        before_settle = totals(self.kernel)
        log = demography.send_settlers(self.kernel, w)
        self.assertIsNotNone(log)
        self.assertEqual(before_settle, totals(self.kernel))


if __name__ == "__main__":
    unittest.main()


class TestSettlerReach(unittest.TestCase):
    def test_reach_grows_with_the_yards_and_the_fuel_cell(self):
        random.seed(171)
        k = GameKernel(seed=7)
        k.activate()
        w = next(p for s in k.sectors.values() for p in s.planets if p.population > 0 and not p.natives)
        w.citadel_level = 2
        w.society["fuel"], w.society["fuel_reckoned"] = "H", k.cycle_count
        torch = demography.settler_reach(k, w)
        w.society["fuel"] = "He-3"
        self.assertEqual(demography.settler_reach(k, w), 2 * torch)     # sqrt(v_e = 4)
        w.citadel_level = 3
        self.assertGreater(demography.settler_reach(k, w), 2 * torch)


class TestDomedSettlement(unittest.TestCase):
    def test_a_fleet_with_yards_domes_a_hostile_world_and_pays_for_it(self):
        from xylarium.kernel import matter
        from xylarium.kernel.ledger import money_supply
        random.seed(173)
        k = GameKernel(seed=7)
        k.activate()
        home = next(p for p in k.sectors[1].planets if p.population > 0)        # biotic Terra
        for s in k.sectors.values():                                            # nothing green left to settle
            for p in s.planets:
                if demography.free_world(p) and p.planet_type in ("TERRESTRIAL", "OCEANIC"):
                    p.planet_type = "BARREN"
        home.citadel_level, home.population = 3, 200_000
        home.treasury, home.ore_silo = 500_000, 5_000
        home.last_daughter_quarter = -10 ** 6
        home.society["viable_quarters"] = 8
        m0 = {c: b["total"] for c, b in money_supply(k).items()}
        t0, n0 = matter.totals(k), k.matter.net()
        log = demography.send_settlers(k, home)
        self.assertIsNotNone(log)
        daughter = next(p for s in k.sectors.values() for p in s.planets if p.metropole_id == home.id)
        self.assertGreaterEqual(daughter.habitats, 1)                           # they live under a dome
        self.assertEqual(demography.stats(k)["domed_daughters"], 1)
        self.assertEqual(m0, {c: b["total"] for c, b in money_supply(k).items()})
        t1, n1 = matter.totals(k), k.matter.net()
        self.assertEqual({c: d for c in set(t0) | set(t1) | set(n1)
                          if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}, {})
