"""
The three clocks kept in step: a span in a place's own years is lived at that place's pace (own years per clock
year), so a steward's term at a seat whose clock runs fast passes in fewer clock cycles than one at a seat whose clock
runs slow - and the engine lives it a frame (a clock year of seasons) at a time. On the settled board one clock serves
all.
"""

import unittest
from unittest import mock

from xylarium.kernel import clocks, cosmos, spheres, stewardship
from xylarium.kernel.engine import GameKernel


class TestClockSync(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)

    def test_one_clock_for_all_on_the_settled_board(self):
        self.assertEqual(clocks.pace(self.k, 1), 1.0)
        self.assertEqual(clocks.cycles_of(self.k, 3.0, 1), 300.0)
        self.assertEqual(clocks.years_of(self.k, 300, 1), 3.0)

    def test_a_span_is_lived_at_its_places_pace(self):
        rates = {5: 110.0, 6: 1.0}
        with mock.patch.object(cosmos, "is_cosmic", return_value=True), \
                mock.patch.object(clocks, "place_rate", side_effect=lambda k, s: rates.get(s)):
            fast, slow = clocks.cycles_of(self.k, 17.0, 5), clocks.cycles_of(self.k, 17.0, 6)
            self.assertAlmostEqual(fast, 17.0 / 110.0 * 100)               # ~15 cycles: within one frame
            self.assertAlmostEqual(slow, 1700.0)
            self.assertAlmostEqual(clocks.years_of(self.k, fast, 5), 17.0)  # and back: the same own years
            self.assertEqual(clocks.lived_span(self.k, 17.0, 5), clocks.frame_cycles())   # never under a frame
            self.assertEqual(clocks.lived_span(self.k, 17.0, 6), 1700.0)

    def test_a_stewards_term_and_its_successions_follow_its_seats_clock(self):
        rid = "R-test"
        with mock.patch.object(stewardship, "term_years", return_value=17.0), \
                mock.patch.object(stewardship, "_seat", return_value=5), \
                mock.patch.object(cosmos, "is_cosmic", return_value=True), \
                mock.patch.object(clocks, "place_rate", return_value=110.0):
            self.assertEqual(stewardship.span_cycles(self.k, rid), 100)
            m = {"id": "E", "name": "Old", "realm": rid, "sender": "civ:X", "since": 0, "generation": 1,
                 "player": None}
            self.k.cycle_count = 100
            stewardship._succeed_envoy(self.k, m)
        self.assertEqual(m["generation"], 1 + int(100 / (17.0 / 110.0 * 100)))  # every term its seat's clock ran

    def test_a_peoples_ledger_takes_a_receipt_for_each_of_its_own_years(self):
        rec = {"h": 0}
        self.assertEqual(clocks.receipts(rec, 1.0), 1)                      # its first receipt
        self.assertEqual(clocks.receipts(rec, 1.0 + 25.5e-9), 25)           # 25.5 own years: 25, half carried
        self.assertEqual(clocks.receipts(rec, 1.0 + 26.0e-9), 1)            # the carried half and half a year
        self.assertEqual(rec["h"], 27)


if __name__ == "__main__":
    unittest.main()
