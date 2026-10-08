"""The deep era's money: what a ruled people's few take is real goods out of its ground, coined at par."""

import random
import unittest

from xylarium.kernel import estates, matter, regimes
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply


def fresh():
    random.seed(5)
    k = GameKernel(seed=42)
    k.activate()
    return k


def _peopled(k):
    return next(p for s in k.sectors.values() for p in s.planets
                if p.population > 0 and p.civilization is not None and not p.natives)


def _with_board(k, home):
    cur = home.currency
    if cur not in k.banking.banks:
        from xylarium.kernel.banking import CentralBank
        k.banking.banks[cur] = CentralBank(currency=cur, name="Treasury", federation="x", governor="g",
                                           alignment=0.0, reserves=0)
    regimes.stats(k)
    regimes.adopt(k, cur, "reserve")
    return regimes.stats(k)["by_currency"][cur]


def _totals(k):
    return {c: b["total"] for c, b in money_supply(k).items()}


class TestEstates(unittest.TestCase):
    def test_the_take_is_mined_and_coined_at_par(self):
        k = fresh()
        home = _peopled(k)
        rec = _with_board(k, home)
        comm = rec["commodity"]
        home.element_deposits[comm] = 10_000
        money0, matter0, net0 = _totals(k), matter.totals(k), k.matter.net()
        bank0 = k.banking.banks[home.currency].warehouse.get(comm, 0)
        pay = estates.accrue(k, "civ:X", home, 0.1, 10.0)
        self.assertGreater(pay, 0)
        moved = k.banking.banks[home.currency].warehouse.get(comm, 0) - bank0
        self.assertEqual(10_000 - home.element_deposits[comm], moved)        # out of its ground, into the board
        self.assertEqual(_totals(k)[home.currency] - money0[home.currency], pay)    # money only for those goods
        self.assertEqual(matter.totals(k), matter0)                              # nothing made from nothing
        self.assertEqual(k.matter.net(), net0)

    def test_an_estate_is_bounded_by_what_its_ground_holds(self):
        k = fresh()
        home = _peopled(k)
        comm = _with_board(k, home)["commodity"]
        home.element_deposits[comm] = 7
        estates.accrue(k, "civ:X", home, 0.5, 1e9)
        self.assertEqual(home.element_deposits[comm], 0)
        self.assertEqual(estates.stats(k)["of"]["civ:X"]["units"], 7)

    def test_no_board_no_take_and_no_rule_no_take(self):
        k = fresh()
        home = _peopled(k)
        self.assertEqual(estates.accrue(k, "civ:X", home, 0.0, 10.0), 0)
        if home.currency in k.banking.banks:
            regimes.adopt(k, home.currency, "central_bank")
        self.assertEqual(estates.accrue(k, "civ:X", home, 0.2, 10.0), 0)

    def test_a_peoples_take_is_its_reserve_basket(self):
        from xylarium.kernel import backing, knowledge, spheres
        k = fresh()
        home = _peopled(k)
        who = knowledge.holder_of_planet(home)
        self.assertIs(spheres._home(k, who), home)
        _with_board(k, home)
        bk = backing.basket(k, who)
        self.assertIsNotNone(bk)
        self.assertIn("shielding", bk["owed"])                                  # honest about what is unmeasured
        for good in bk["units"]:
            home.element_deposits[good] = 10_000
        money0, matter0, net0 = _totals(k), matter.totals(k), k.matter.net()
        bank = k.banking.banks[home.currency]
        before = {g: bank.warehouse.get(g, 0) for g in bk["units"]}
        pay = estates.accrue(k, who, home, 0.1, 10.0)
        if backing.basket_value(k, bk, home.currency) is None:
            self.skipTest("its ports price none of its basket")
        self.assertGreater(pay, 0)
        drawn = estates.stats(k)["of"][who]["basket"]
        self.assertGreaterEqual(len(drawn), 1)                                  # drawn as a basket, good by good
        for g, n in drawn.items():
            self.assertEqual(bank.warehouse.get(g, 0) - before[g], n)           # each into the board's warehouse
        self.assertEqual(_totals(k)[home.currency] - money0[home.currency], pay)   # money only against those goods
        self.assertEqual(matter.totals(k), matter0)                              # transfers: nothing made
        self.assertEqual(k.matter.net(), net0)

    def test_the_food_term_is_reckoned_by_mass_from_physics(self):
        from xylarium.kernel import backing
        self.assertAlmostEqual(backing.food_energy_j_per_kg("ORGANICS", "H2O") / 1.556e7, 1.0, places=2)   # carbon fixed in water
        self.assertIsNone(backing.food_energy_j_per_kg("ORGANICS", "NH3"))      # another solvent: owed
        self.assertIsNone(backing.food_energy_j_per_kg("H"))                     # owed, never invented


if __name__ == "__main__":
    unittest.main()
