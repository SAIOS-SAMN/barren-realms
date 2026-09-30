"""
Society: fertility by reproductive strategy, natal cards, luxury, tourism and charters, and the drive ladder -
each conserving money and matter.
"""

import random
import unittest

from xylarium.kernel import biosphere, fertility, luxury, matter, propulsion, tourism
from xylarium.kernel.economy import EconomyManager
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply
from xylarium.kernel.models import ActionType


def money(kernel):
    return {c: b["total"] for c, b in money_supply(kernel).items()}


def undeclared(kernel, t0, n0):
    t1, n1 = matter.totals(kernel), kernel.matter.net()
    return {c: d for c in set(t0) | set(t1) | set(n1)
            if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}


def peopled(kernel, pred=lambda p: True):
    return next(p for s in kernel.sectors.values() for p in s.planets
                if p.population > 1000 and not p.natives and (p.owner_id or p.civilization) and pred(p))


class TestFertility(unittest.TestCase):
    def setUp(self):
        random.seed(101)
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.k.tick_simulation = lambda: None
        self.w = peopled(self.k, lambda p: p.civilization is not None)

    def test_strategy_follows_clade_then_metabolism(self):
        civ = self.w.civilization
        civ.clade = "mycotiform"
        self.assertEqual(fertility.strategy(self.k, self.w), "r")
        civ.clade = "bimaniform"
        self.assertEqual(fertility.strategy(self.k, self.w), "K")
        civ.clade = "unrecorded"
        civ.metabolism = "mineral"
        self.assertEqual(fertility.strategy(self.k, self.w), "lithic")

    def test_luxury_compresses_a_K_people_and_food_multiplies_an_r_people(self):
        self.w.civilization.clade = "bimaniform"
        self.w.society.update(basket_fill=1.0, lux_access=0.0)
        poor, _ = fertility.natural(self.k, self.w)
        self.w.society["lux_access"] = 1.0
        rich, _ = fertility.natural(self.k, self.w)
        self.assertLess(rich, poor)
        self.assertLess(rich, 1.0)                              # the demographic transition
        self.w.civilization.clade = "hexasocial"
        self.w.organics_silo = 0
        lean, _ = fertility.natural(self.k, self.w)
        self.w.organics_silo = 10 ** 7
        fat, _ = fertility.natural(self.k, self.w)
        self.assertGreater(fat, lean)
        self.assertGreater(fat, 1.5)

    def test_famine_and_bombardment_collapse_fertility(self):
        f0, _ = fertility.fertility(self.k, self.w)
        fertility.mark(self.w, "famine", self.k.cycle_count)
        f1, parts = fertility.fertility(self.k, self.w)
        self.assertTrue(parts["stressed"])
        self.assertLessEqual(f1 / f0, 0.3)

    def test_below_replacement_a_people_settles_under_its_land(self):
        k = demography_cap = biosphere.carrying_capacity(self.k, self.w)
        self.w.population = int(k * 0.8)
        self.w.society["fertility"] = 0.5
        births = sum(biosphere.births(self.k, self.w, demography_cap) for _ in range(50))
        self.assertLess(births, 0)                              # above its equilibrium (0.5 K): it shrinks
        self.w.society["fertility"] = 1.0
        self.assertGreater(sum(biosphere.births(self.k, self.w, demography_cap) for _ in range(50)), 0)

    def test_natal_cards(self):
        owner = self.k.register_player("gov", "Gov")
        w = self.w
        w.owner_id = owner.id
        with self.assertRaises(ValueError):
            fertility.set_natal(self.k, owner, w, "hatching")   # the Pyre's alone
        f0, _ = fertility.fertility(self.k, w)
        fertility.set_natal(self.k, owner, w, "propagation")
        f1, _ = fertility.fertility(self.k, w)
        self.assertAlmostEqual(f1 / f0, 1.4, places=3)
        eat = biosphere.consumption(w)
        w.society.pop("natal")
        self.assertLess(biosphere.consumption(w), eat)          # propagation feeds more mouths
        fertility.set_natal(self.k, owner, w, "ascetic")
        self.assertLessEqual(fertility.fertility(self.k, w)[0], 1.0)

    def test_sacred_hatching_turns_food_into_fanatics(self):
        w = self.w
        w.society["natal"] = "hatching"
        w.organics_silo = 1_000_000
        troops = w.garrison_troops
        t0, n0 = matter.totals(self.k), self.k.matter.net()
        fertility._hatch(self.k, w, fertility.stats(self.k))
        self.assertGreater(w.garrison_troops, troops)
        self.assertEqual(undeclared(self.k, t0, n0), {})


class TestLuxury(unittest.TestCase):
    def setUp(self):
        random.seed(103)
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.k.tick_simulation = lambda: None

    def test_crafting_is_a_declared_conversion(self):
        w = peopled(self.k)
        w.society["basket_fill"] = 1.0
        w.organics_silo = w.ore_silo = 10 ** 6
        w.element_reserves.update({"Si": 10 ** 5, "Ti": 10 ** 5, "H2O": 10 ** 5, "H": 10 ** 5})
        t0, n0 = matter.totals(self.k), self.k.matter.net()
        made = luxury.craft(self.k, w)
        self.assertGreater(made, 0)
        self.assertIn(w.society["luxury"]["type"], w.element_reserves)
        self.assertEqual(undeclared(self.k, t0, n0), {})

    def test_households_buy_what_they_cannot_make_and_money_only_moves(self):
        from xylarium.kernel import demography
        w = peopled(self.k, lambda p: demography._markets(self.k, p))
        w.society["basket_fill"] = 1.0
        own = luxury.signature(self.k, w)["type"]
        other = next(t for t in ("LUX_CURIO", "LUX_RESONANT", "LUX_STIMULANT", "LUX_EPHEMERA") if t != own)
        ports = demography._markets(self.k, w)
        for p in ports:
            EconomyManager.ensure_port_inventory(p)
            p.stock[own] = p.stock[other] = 500
        w.household_purse = 10 ** 6
        m0 = money(self.k)
        t0, n0 = matter.totals(self.k), self.k.matter.net()
        luxury.shop(self.k, w, ports)
        self.assertGreater(luxury.stats(self.k)["bought"].get(other, 0), 0)
        self.assertEqual(luxury.stats(self.k)["bought"].get(own, 0), 0)    # nobody craves what they make
        self.assertEqual(m0, money(self.k))
        self.assertEqual(undeclared(self.k, t0, n0), {})


class TestTourism(unittest.TestCase):
    def setUp(self):
        random.seed(107)
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.k.tick_simulation = lambda: None
        self.sol = self.k.sectors[1]
        self.origin = next(p for p in self.sol.planets if p.population > 0)
        # a resort a few jumps away
        from xylarium.kernel.surface import SurfaceManager, DistrictType
        reach = tourism._hops(self.k, 1, 3)
        self.resort = next(p for sid in sorted(reach, key=reach.get) for p in self.k.sectors[sid].planets
                           if reach[sid] >= 1)
        grid = SurfaceManager.ensure_surface_grid(self.resort)
        grid.tiles[0].district = DistrictType.RESORT_DOME
        self.resort.surface_grid = grid.to_dict()
        self.resort.element_reserves["H2O"] = 1000
        EconomyManager.ensure_port_inventory(self.sol.port)
        self.sol.port.stock["H"] = 800

    def test_mass_tourism_moves_money_and_burns_the_ports_hydrogen(self):
        self.origin.household_purse = 200_000
        m0 = money(self.k)
        t0, n0 = matter.totals(self.k), self.k.matter.net()
        treasury = self.resort.treasury
        tourism._travel(self.k, self.origin, tourism.stats(self.k))
        self.assertGreater(tourism.stats(self.k)["trips"], 0)
        self.assertGreater(self.resort.treasury, treasury)
        self.assertEqual(undeclared(self.k, t0, n0), {})
        m1 = money(self.k)
        self.assertEqual(sum(m0.values()), sum(m1.values())) if self.resort.currency == self.origin.currency else None

    def test_a_charter_is_escrowed_flown_and_paid(self):
        self.origin.household_purse = 10 ** 6
        m0 = money(self.k)
        tourism._post_charter(self.k, self.origin, tourism.stats(self.k))
        book = tourism.charters(self.k)
        self.assertEqual(len(book), 1)
        self.assertEqual(m0, money(self.k))                     # the escrow is still money
        c = next(iter(book.values()))
        cap = self.k.register_player("liner", "Liner")
        cap.ship.ship_type = "Aegis Pleasure Cruiser"
        self.assertEqual(tourism.accept(self.k, cap, self.sol), c["id"])
        credits = cap.credits
        path = self.k.find_path(1, c["dest_sector"])
        for nxt in path[1:]:
            cap.turns_left = 100
            self.k.dispatch("liner", ActionType.MOVE, destination=nxt)
        self.assertEqual(c["status"], "DELIVERED")
        self.assertGreater(cap.credits + sum(cap.fx_wallet.values()), credits)

    def test_a_pirate_holds_the_vips_for_ransom(self):
        self.origin.household_purse = 10 ** 6
        tourism._post_charter(self.k, self.origin, tourism.stats(self.k))
        c = next(iter(tourism.charters(self.k).values()))
        liner = self.k.register_player("liner", "Liner")
        pirate = self.k.register_player("pirate", "Pirate")
        liner.ship.ship_type = "Aegis Pleasure Cruiser"
        self.assertEqual(tourism.accept(self.k, liner, self.sol), c["id"])
        m0 = money(self.k)
        tourism.intercept(self.k, pirate, liner)
        self.assertEqual(c["status"], "RANSOMED")
        self.assertIsNone(liner.charter)
        self.assertEqual(sum(m0.values()), sum(money(self.k).values())) if c["currency"] == "SOL" else None


class TestDrives(unittest.TestCase):
    def setUp(self):
        random.seed(109)
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.k.tick_simulation = lambda: None
        self.cap = self.k.register_player("pilot", "Pilot")
        self.sol = self.k.sectors[1]
        EconomyManager.ensure_port_inventory(self.sol.port)

    def test_he3_drive_burns_a_quarter_and_warp_burns_nothing_until_the_core_fails(self):
        cap = self.cap
        cap.rank_tier = 3
        cap.credits = 10 ** 6
        h_burn = propulsion.burn_for(cap.ship)
        self.sol.port.stock["M3_ENGINE_MANIFOLD"] = 5
        self.sol.port.stock["M4_WARP_CORE"] = 5
        self.sol.port.stock["He-3"] = 500
        t0, n0 = matter.totals(self.k), self.k.matter.net()
        propulsion.refit_drive(self.k, cap, self.sol, "HE3")
        self.assertEqual(propulsion.fuel_of(cap.ship), "He-3")
        self.assertEqual(propulsion.burn_for(cap.ship), -(-h_burn // 4))
        propulsion.jump(self.k, cap, self.sol)
        self.assertEqual(undeclared(self.k, t0, n0), {})
        propulsion.refit_drive(self.k, cap, self.sol, "WARP")
        self.assertEqual(propulsion.bunker_capacity(cap.ship), 0)
        for _ in range(400):
            self.assertEqual(propulsion.jump(self.k, cap, self.sol), 0)
        self.assertEqual(cap.ship.drive, "H")                    # the core burned out: back on the torch
        self.assertEqual(undeclared(self.k, t0, n0), {})

    def test_gas_giants_are_hydrogen_wells(self):
        from xylarium.kernel import physics
        sec = next(s for s in self.k.sectors.values() if s.port is not None
                   and any(physics.body(p).get("giant") for p in s.planets))
        EconomyManager.ensure_port_inventory(sec.port)
        sec.port.stock["H"] = 0
        t0, n0 = matter.totals(self.k), self.k.matter.net()
        propulsion.skim_wells(self.k)
        self.assertGreater(sec.port.stock["H"], 0)
        self.assertEqual(undeclared(self.k, t0, n0), {})

    def test_a_world_without_hydrogen_raises_a_degraded_beacon(self):
        w = peopled(self.k, lambda p: p.fighters > 0)
        w.element_reserves["H"] = 0
        sec = self.k.sectors[w.sector_id]
        if sec.port is not None:
            EconomyManager.ensure_port_inventory(sec.port)
            sec.port.stock["H"] = 0
        propulsion.quarter(self.k)
        self.assertTrue(w.society.get("degraded"))
        w.element_reserves["H"] = 10 ** 6
        propulsion.quarter(self.k)
        self.assertFalse(w.society.get("degraded"))


if __name__ == "__main__":
    unittest.main()
