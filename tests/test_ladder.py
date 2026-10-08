"""
The ladder: a people stands on the highest rung whose evidence exists, each rung citing its record - the evidence
moves it, its absence does not; the court's rungs read UNMEASURED, never inferred.
"""

import unittest

from xylarium.kernel import ascendance, hypha, ladder, spheres, stewardship, transit
from xylarium.kernel.engine import GameKernel


class TestLadder(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        spheres.ensure(self.k)
        self.realm = stewardship.realms(self.k)[0]
        self.who = next(w for w in spheres.stats(self.k)["nets"] if spheres.presence(self.k, self.realm) != w)

    def test_with_no_evidence_a_people_is_unaware_and_the_court_rungs_are_unmeasured(self):
        top, cites = ladder.rung(self.k, self.who)
        self.assertEqual(top, "unaware")
        self.assertIn("unmeasured", cites["hears_anastome"])
        self.assertIn("unmeasured", cites["speaks_anastome"])

    def test_a_petition_moves_it_to_petitions_and_a_reading_cites_observed(self):
        ascendance.petition(self.k, self.who, self.realm)
        top, cites = ladder.rung(self.k, self.who)
        self.assertEqual(top, "petitions")
        self.assertNotIn("observed", cites)                       # not read yet: no evidence of a reading
        ascendance.stats(self.k)["of"][self.who]["books"] = {"order": {}}
        self.assertEqual(ladder.rung(self.k, self.who)[1]["observed"]["realm"], self.realm)

    def test_a_receipt_with_it_as_payer_moves_it_to_rides_the_roads(self):
        a, b = sorted(self.k.sectors)[:2]
        transit.in_game(self.k, a, "civ:someone-else", "civ:keeper", 5, "SOL", "1-2")
        self.assertNotEqual(ladder.rung(self.k, self.who)[0], "rides_the_roads")
        transit.in_game(self.k, a, self.who, "civ:keeper", 5, "SOL", "1-2")
        top, cites = ladder.rung(self.k, self.who)
        self.assertEqual(top, "rides_the_roads")
        self.assertEqual(cites["rides_the_roads"]["ref"], "1-2")

    def test_only_a_progenitor_line_with_its_own_road_on_the_hypha_builds_roads(self):
        from unittest import mock
        hypha._append(self.k, "SOL", "pouw", "captain:1", self.who, 5, "SOL", "1-2", self.who)
        self.assertNotEqual(ladder.rung(self.k, self.who)[0], "builds_roads")      # no line: a road is not enough
        with mock.patch("xylarium.kernel.board.progenitors", return_value={self.who: {"name": "L"}}):
            top, cites = ladder.rung(self.k, self.who)
        self.assertEqual(top, "builds_roads")
        self.assertEqual(cites["builds_roads"]["road"], "1-2")

    def test_a_change_of_rung_is_written_to_the_annals(self):
        from xylarium.kernel import history
        ascendance.petition(self.k, self.who, self.realm)
        self.k.cycle_count = (self.k.cycle_count // 400 + 1) * 400
        ladder.season(self.k)
        self.assertTrue(any(e.get("kind") == "RUNG" for e in history.of_people(self.k, self.who)))


if __name__ == "__main__":
    unittest.main()
