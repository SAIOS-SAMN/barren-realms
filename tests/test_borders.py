"""
Borders: a realm's steward reads its border book - the threat an unbonded neighbour's arms bring to each border system
against the works there and the keeper's own reach - and its keeper fortifies the deepest deficit, as far as its
council judges it worth and its treasury pays. Works stand at the front in the war reckoning and take a war's blows
first. A people waging a war of taking is embargoed by every people whose doctrine forbids taking.
"""

import random
import unittest
from unittest import mock

from xylarium.kernel import borders, realmwars, spheres, stewardship, transit
from xylarium.kernel.engine import GameKernel


class TestBorders(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        spheres.ensure(self.k)
        for _ in range(100):
            self.k.tick_simulation()
        self.realm = max(stewardship.realms(self.k), key=lambda r: len(spheres.stats(self.k)["realms"][r]["sectors"]))
        self.keeper = spheres.presence(self.k, self.realm)

    def test_a_frontier_with_no_bonds_shows_its_borders_and_their_deficits(self):
        with mock.patch.object(realmwars, "_web", side_effect=lambda k, who: {who}):    # no one is bound to it
            threats = borders.threats(self.k, self.realm)
            book = borders.book(self.k, self.realm)
        for sid, (threat, by) in threats.items():
            self.assertIn(sid, spheres.stats(self.k)["realms"][self.realm]["sectors"])
            self.assertNotEqual(by, self.keeper)
            self.assertGreaterEqual(threat, 0.0)
        self.assertEqual({int(s) for s, _ in book}, set(threats))

    def test_works_count_at_the_front_and_take_a_wars_blows_first(self):
        sid = spheres.stats(self.k)["realms"][self.realm]["sectors"][0]
        borders.stats(self.k)["forts"][str(sid)] = 50.0
        self.assertEqual(borders.wear(self.k, sid, 30.0), 0.0)               # absorbed by the works
        self.assertEqual(borders.fortification(self.k, sid), 20.0)
        self.assertEqual(borders.wear(self.k, sid, 30.0), 10.0)              # what they cannot take, the garrison does

    def test_a_keeper_fortifies_only_what_its_council_judges_worth_and_can_pay(self):
        from xylarium.kernel import decide
        sid = spheres.stats(self.k)["realms"][self.realm]["sectors"][0]
        home = spheres._home(self.k, self.keeper)
        home.treasury = 10 ** 9
        with mock.patch.object(decide, "choose", return_value=None):
            self.assertEqual(borders._fortify(self.k, self.realm, sid, 10.0, []), 0.0)
        with mock.patch.object(decide, "choose", side_effect=lambda k, opts, m, *s: opts[0]):
            built = borders._fortify(self.k, self.realm, sid, 10.0, [])
        self.assertEqual(built, 10.0)
        self.assertEqual(borders.fortification(self.k, sid), 10.0)
        home.treasury = 0
        with mock.patch.object(decide, "choose", side_effect=lambda k, opts, m, *s: opts[0]):
            self.assertEqual(borders._fortify(self.k, self.realm, sid, 10.0, []), 0.0)   # nothing to pay with

    def test_an_aggressor_is_embargoed_by_those_whose_doctrine_forbids_taking(self):
        a = sorted(self.k.sectors)[0]
        b = next(w for w in self.k.sectors[a].warps if w in self.k.sectors)
        with mock.patch.object(transit, "owner", return_value="civ:Keeper"), \
                mock.patch.object(transit, "aggressor", side_effect=lambda k, who: who == "civ:Raider"), \
                mock.patch.object(realmwars, "_abhors", return_value=True):
            self.assertTrue(transit.blocks(self.k, "civ:Raider", a, b))
            self.assertFalse(transit.blocks(self.k, "civ:Trader", a, b))
        with mock.patch.object(transit, "owner", return_value="civ:Keeper"), \
                mock.patch.object(transit, "aggressor", return_value=True), \
                mock.patch.object(realmwars, "_abhors", return_value=False):
            self.assertFalse(transit.blocks(self.k, "civ:Raider", a, b))     # a holder that takes too does not


if __name__ == "__main__":
    unittest.main()
