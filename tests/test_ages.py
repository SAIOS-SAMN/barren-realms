"""
A new player may begin in any age: foragers, fields, first flight (run forward to the first starship - in whatever
year it comes in that universe), or the lanes. Before spaceflight the player stewards one people, within its
physics; when its yards rise the steward may take ship.
"""

import unittest

from xylarium.kernel import ages, sustenance, ways


class TestAges(unittest.TestCase):
    def test_the_ages_in_order(self):
        self.assertEqual([a["key"] for a in ages.AGES], ["forager", "agrarian", "first_flight", "spacefaring"])

    def test_a_forager_steward_decides_within_physics(self):
        k = ages.begin(3, "forager")
        self.assertEqual(k.state["genesis"]["mode"], "forager")
        home = ages.peoples(k)[0]
        ages.bind(k, "p1", "Steward", home)
        self.assertIsNotNone(ages.shape(k, "p1", {"tolerance": 0.3}))
        self.assertAlmostEqual(home.society["genome"]["tolerance"], 0.3)
        self.assertIn("state", ages.act(k, "p1", "state"))           # foragers cannot found a state
        self.assertIn("fields", ages.act(k, "p1", "farm"))
        self.assertEqual(ways.way(home), "farm")
        self.assertIn("surplus", ages.act(k, "p1", "state"))          # half-wild crops cannot bear one yet
        k.tick_simulation()
        self.assertIsNone(ages.shape(k, "p1", {"tolerance": 1.0}))     # the Progenitor's hand is only at genesis

    def test_wake_me_when_returns_what_happened(self):
        k = ages.begin(3, "agrarian")
        ages.bind(k, "p1", "Steward", ages.peoples(k)[0])
        self.assertTrue(ages.wake_when(k, "p1", max_years=5))

    def test_first_flight_hands_over_at_the_first_starship_and_the_steward_takes_ship(self):
        k = ages.begin(7, "first_flight")
        firsts = k.state["genesis"]["firsts"]
        self.assertIn("first_starship", firsts)
        self.assertEqual(k.state["genesis"]["handed_over"]["cycle"], k.cycle_count)
        flying = next(p for p in ages.peoples(k) if sustenance.yards(p))
        ages.bind(k, "p1", "Steward", flying)
        cap = ages.first_captain(k, "p1", "First Captain")
        self.assertIsNotNone(cap)
        self.assertEqual(cap.sector_id, flying.sector_id)


if __name__ == "__main__":
    unittest.main()
