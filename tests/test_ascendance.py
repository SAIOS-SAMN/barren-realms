"""
Ascendance: a people that crosses inside a realm another keeps petitions its steward, who reads it in need-ordered
books against the worst the realm already holds, and charters it among the stars or holds it at home - read again
every term. Held at home, its ships go no further than its own system, its network does not grow, and no one may
make war on it.
"""

import random
import unittest
from unittest import mock

from xylarium.kernel import ascendance, spheres, stewardship, transit
from xylarium.kernel.engine import GameKernel


class TestAscendance(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        spheres.ensure(self.k)
        self.realm = stewardship.realms(self.k)[0]
        self.who = next(w for w in spheres.stats(self.k)["nets"] if spheres.presence(self.k, self.realm) != w)

    def test_a_people_is_read_in_every_book_against_the_worst_the_realm_holds(self):
        res = ascendance.books(self.k, self.who, self.realm)
        for (site, book), v in res.items():
            self.assertEqual(site, self.who)
            self.assertIn(book, ascendance.BOOKS)
        m = ascendance.measures(self.k, self.who)
        self.assertEqual(set(m), set(ascendance.BOOKS))

    def test_a_held_people_stays_home_and_no_one_may_make_war_on_it(self):
        from xylarium.kernel import realmwars
        ascendance.petition(self.k, self.who, self.realm)
        self.assertEqual(ascendance.ruling(self.k, self.who), "pending")
        ascendance.rule(self.k, self.who, "quarantine", "test")
        home = spheres._home(self.k, self.who).sector_id
        away = next(s for s in sorted(self.k.sectors) if s != home)
        self.assertTrue(ascendance.confined(self.k, self.who, home, away))
        self.assertFalse(ascendance.confined(self.k, self.who, away, home))     # it may come home
        self.assertFalse(ascendance.free(self.k, self.who))
        other = spheres.presence(self.k, self.realm)
        self.assertFalse(realmwars.weigh(self.k, other, self.who, home)["war"])  # the steward shields it
        ascendance.rule(self.k, self.who, "chartered", "test")
        self.assertTrue(ascendance.free(self.k, self.who))

    def test_the_steward_charters_only_what_is_in_balance_and_reads_again_each_term(self):
        ascendance.petition(self.k, self.who, self.realm)
        rec = ascendance.stats(self.k)["of"][self.who]
        with mock.patch.object(ascendance, "books", return_value={}):
            self.k.cycle_count = (self.k.cycle_count // 100 + 1) * 100
            ascendance.season(self.k)
        self.assertEqual(rec["ruling"], "chartered")
        with mock.patch.object(ascendance, "books", return_value={(self.who, "sufficiency"): ascendance.mc.q(0.5)}):
            self.k.cycle_count = (self.k.cycle_count // 100 + 1) * 100
            ascendance.season(self.k)
        self.assertEqual(rec["ruling"], "chartered")                  # not yet a term since: no new reading
        self.k.cycle_count += stewardship.span_cycles(self.k, self.realm) + 100
        self.k.cycle_count -= self.k.cycle_count % 100
        with mock.patch.object(ascendance, "books", return_value={(self.who, "sufficiency"): ascendance.mc.q(0.5)}):
            ascendance.season(self.k)
        self.assertEqual((rec["ruling"], rec["lead"]), ("quarantine", "sufficiency"))

    def test_a_player_who_keeps_the_realm_rules_for_it(self):
        from xylarium.kernel import command
        ascendance.petition(self.k, self.who, self.realm)
        stewardship.seat_steward(self.k, "keeper", "Keeper", self.realm)
        self.assertTrue(command.dispatch(self.k, "keeper", "quarantine", people=self.who)["ok"])
        self.assertEqual(ascendance.ruling(self.k, self.who), "quarantine")
        self.assertTrue(command.dispatch(self.k, "keeper", "charter", people=self.who)["ok"])
        self.assertTrue(ascendance.free(self.k, self.who))


if __name__ == "__main__":
    unittest.main()
