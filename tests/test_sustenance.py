"""
Staples and sustenance: each people eats its own staple, its harvest and its famine are in that staple, and a
people that cannot feed itself expands, takes from others, or is relieved - with every unit of food accounted for.
"""

import random
import unittest

from xylarium.kernel import matter, staples, sustenance
from xylarium.kernel.colony import ColonyManager
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply
from xylarium.kernel.models import ActionType


def fresh(rseed=307):
    random.seed(rseed)
    k = GameKernel(seed=7)
    k.activate()
    return k


def civ_world(k, metabolism=None, exclude=()):
    for s in k.sectors.values():
        for p in s.planets:
            if (p.owner_id is None and p.civilization is not None and p.population > 0 and not p.natives
                    and s.id != 1 and p not in exclude):
                if metabolism:
                    p.civilization.metabolism = metabolism
                return p
    raise AssertionError("no civilization world")


def money(k):
    return {c: b["total"] for c, b in money_supply(k).items()}


def undeclared(k, t0, n0):
    t1, n1 = matter.totals(k), k.matter.net()
    return {c: d for c in set(t0) | set(t1) | set(n1)
            if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}


class TestStaples(unittest.TestCase):
    def test_each_metabolism_eats_its_own_staple(self):
        self.assertEqual(staples.of_metabolism("biotic"), "ORGANICS")
        self.assertEqual(staples.of_metabolism("mineral"), "ORE")
        self.assertEqual(staples.of_metabolism("cryogenic"), "H2O")
        self.assertEqual(staples.of_metabolism("plasmic"), "H")

    def test_a_plasmic_people_eats_hydrogen_and_starves_without_it_whatever_its_granary_holds(self):
        k = fresh()
        w = civ_world(k, "plasmic")
        w.organics_silo = 10_000
        w.element_reserves["H"] = 0
        t0, n0 = matter.totals(k), k.matter.net()
        pop = w.population
        ColonyManager.tick_colony(w, kernel=k)
        self.assertEqual(w.organics_silo, 10_000)              # grain is nothing to them
        self.assertLess(w.population, pop + 1)
        self.assertGreater(w.society.get("short_q", 0), 0)     # a famine in hydrogen
        self.assertEqual(undeclared(k, t0, n0), {})

    def test_a_plasmic_harvest_is_hydrogen(self):
        k = fresh()
        w = civ_world(k, "plasmic")
        w.element_reserves["H"] = 10_000
        before = w.element_reserves["H"]
        t0, n0 = matter.totals(k), k.matter.net()
        for _ in range(5):
            ColonyManager.tick_colony(w, kernel=k)
        self.assertGreater(w.society.get("harvest_q", 0), 0)
        self.assertNotEqual(w.element_reserves["H"], before)
        self.assertEqual(undeclared(k, t0, n0), {})

    def test_lithotrophs_graze_the_crust(self):
        k = fresh()
        w = civ_world(k, "mineral")
        w.element_deposits["ORE"] = 1_000_000
        crust = w.element_deposits["ORE"]
        t0, n0 = matter.totals(k), k.matter.net()
        ColonyManager.tick_colony(w, kernel=k)
        self.assertLess(w.element_deposits["ORE"], crust)
        self.assertEqual(undeclared(k, t0, n0), {})

    def test_famine_aid_must_be_what_they_eat(self):
        k = fresh()
        w = civ_world(k, "cryogenic")
        cap = k.register_player("donor", "Donor")
        cap.sector_id = w.sector_id
        cap.ship.cargo.organics = 20
        res = k.dispatch("donor", ActionType.IDEOLOGY_AID_DISPATCH, planet_id=w.id, food_units=10)
        self.assertFalse(res.success)
        self.assertIn("H2O", res.message)


class TestSustenance(unittest.TestCase):
    def _hungry(self, k, w, metab="plasmic"):
        food = staples.of_metabolism(metab)
        staples.move(w, food, -staples.held(w, food))
        w.society.update(need_q=1000, harvest_q=100, short_q=0, self_sufficiency=0.1)
        return food

    def test_a_hungry_world_without_yards_is_stranded(self):
        k = fresh()
        w = civ_world(k, "plasmic")
        w.citadel_level = 1
        self._hungry(k, w)
        g = sustenance.read(k, w)
        self.assertEqual(g["state"], "stranded")

    def test_with_yards_and_nowhere_open_it_is_pressed_and_raids(self):
        k = fresh()
        w = civ_world(k, "plasmic")
        w.citadel_level = 3
        food = self._hungry(k, w)
        for s in k.sectors.values():                       # nothing open anywhere
            for p in s.planets:
                if p.owner_id is None and p.population <= 0 and p.civilization is None:
                    p.faction_id = p.faction_id or "IMPERIUM"
        victim = civ_world(k, exclude=(w,))
        if victim.sector_id != w.sector_id:
            k.sectors[victim.sector_id].planets.remove(victim)
            victim.sector_id = w.sector_id
            k.sectors[w.sector_id].planets.append(victim)
        staples.move(victim, food, 50_000)
        w.garrison_troops, victim.garrison_troops, victim.fighters = 10_000, 0, 0
        g = sustenance.read(k, w)
        self.assertEqual(g["state"], "pressed")
        m0, t0, n0 = money(k), matter.totals(k), k.matter.net()
        align = w.civilization.alignment
        log = sustenance.raid(k, w, g)
        self.assertIsNotNone(log)
        self.assertIn("seized", log)
        self.assertGreater(staples.held(w, food), 0)
        self.assertLess(w.civilization.alignment, align)      # necessity still darkens
        self.assertEqual(len(sustenance.stats(k)["wars"]), 1)
        self.assertEqual(m0, money(k))
        self.assertEqual(undeclared(k, t0, n0), {})

    def test_luminous_neighbours_relieve_the_hungry(self):
        k = fresh()
        w = civ_world(k, "plasmic")
        food = self._hungry(k, w)
        donor = civ_world(k, exclude=(w,))
        donor.civilization = type(donor.civilization)(**{**donor.civilization.__dict__})
        donor.civilization.metabolism, donor.civilization.alignment = "plasmic", 0.8
        donor.citadel_level = 4
        donor.owner_id = None
        if donor.sector_id != w.sector_id:
            k.sectors[donor.sector_id].planets.remove(donor)
            donor.sector_id = w.sector_id
            k.sectors[w.sector_id].planets.append(donor)
        staples.move(donor, food, 100_000)
        g = sustenance.read(k, w)
        t0, n0 = matter.totals(k), k.matter.net()
        log = sustenance.relieve(k, w, g)
        self.assertIsNotNone(log)
        self.assertGreater(staples.held(w, food), 0)
        self.assertEqual(undeclared(k, t0, n0), {})

    def test_the_census_counts_peoples_by_what_they_eat(self):
        k = fresh()
        c = sustenance.census(k)
        self.assertIn("biotic", c)
        self.assertEqual(c["biotic"]["staple"], "ORGANICS")
        self.assertGreater(c["biotic"]["people"], 0)


class TestColonistsReadTheLand(unittest.TestCase):
    def test_a_biotic_colonist_sees_no_food_on_a_gas_giant(self):
        from xylarium.kernel.cognition import SeatGrow
        k = fresh()
        cap = k.register_player("farmer", "Farmer")
        giant = next(p for s in k.sectors.values() for p in s.planets if p.planet_type == "GAS_GIANT")
        land = next(p for s in k.sectors.values() for p in s.planets if p.planet_type == "TERRESTRIAL")
        self.assertEqual(SeatGrow.feeds(cap, giant, k), 0)
        self.assertGreater(SeatGrow.feeds(cap, land, k), 0)


if __name__ == "__main__":
    unittest.main()
