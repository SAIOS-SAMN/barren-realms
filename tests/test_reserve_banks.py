"""
The ancients' reserve banks (5.1a): a house's bank takes in the mu its house earned at the court, once and exactly;
mu moves only between ancients' houses; the federation reads every member's reserve, lane by lane.
"""

import unittest
from fractions import Fraction
from unittest import mock

from xylarium.kernel import court, reserve_banks
from xylarium.kernel.engine import GameKernel


class TestReserveBanks(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        homes = [p for s in self.k.sectors.values() for p in s.planets if p.population > 0 and p.civilization][:2]
        self.hs = {"civ:A": homes[0], "civ:B": homes[1]}
        self.p = mock.patch.object(reserve_banks, "houses", return_value=self.hs)
        self.p.start()
        self.addCleanup(self.p.stop)

    def _year(self):
        self.k.cycle_count = (self.k.cycle_count // 100 + 1) * 100
        reserve_banks.season(self.k)

    def test_the_mu_a_house_earns_is_its_reserve_taken_in_once(self):
        court.stats(self.k)["of"]["civ:A"] = {"met": 1, "closed": 1, "refused": 0, "beyond": 0,
                                               "mu": ["0", "6", "0", "1/3"]}
        self._year()
        self._year()                                                        # read again: nothing new
        self.assertEqual(reserve_banks.reserve(self.k, "civ:A"), [0, 6, 0, Fraction(1, 3)])

    def test_mu_moves_only_between_ancients_houses(self):
        reserve_banks.bank(self.k, "civ:A")["reserve"] = ["0", "6", "0", "0"]
        self.assertFalse(reserve_banks.transfer(self.k, "civ:A", "civ:Young", [0, 1, 0, 0])["ok"])
        self.assertFalse(reserve_banks.transfer(self.k, "civ:A", "civ:B", [0, 7, 0, 0])["ok"])   # more than held
        self.assertTrue(reserve_banks.transfer(self.k, "civ:A", "civ:B", [0, 2, 0, 0])["ok"])
        self.assertEqual(reserve_banks.federal(self.k)["reserve"], ["0", "6", "0", "0"])        # the lineage keeps it


if __name__ == "__main__":
    unittest.main()
