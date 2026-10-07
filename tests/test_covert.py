"""
Quarantine and covert statecraft: a people its steward holds at home makes no open contact - no meeting, no treaty -
and the works its books make a danger are interdicted (found, but stopped). What reaches it reaches it covertly:
exploiters of its stores, those who would keep it down, smugglers - each its own council's choice, weighed against its
conscience and the watch; caught, it is sanctioned by the realm.
"""

import random
import unittest
from unittest import mock

from xylarium.kernel import (ascendance, covert, decide, knowledge, polity, relations, spheres, staples, technology,
                             transit)
from xylarium.kernel.engine import GameKernel


def _accept(k, opts, m, *salt):
    return opts[0]


class TestQuarantineAndCovert(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=42)
        spheres.ensure(self.k)
        for _ in range(100):
            self.k.tick_simulation()
        peoples = sorted(p for p, ws in relations._peoples(self.k).items() if p.startswith("civ:") and ws)
        self.target, self.actor = peoples[0], peoples[1]
        realm = next(iter(spheres.stats(self.k)["realms"]), "R-1")
        ascendance.stats(self.k)["of"][self.target] = {"realm": realm, "ruling": "quarantine", "since": 0,
                                                       "ruled": self.k.cycle_count, "rulings": 1, "mind": {},
                                                       "hosts": [], "books": {}}
        self.home = spheres._home(self.k, self.actor)
        self.tw = spheres._home(self.k, self.target)

    def test_a_quarantined_people_makes_no_open_contact(self):
        self.assertTrue(ascendance.isolated(self.k, self.target, self.actor))
        self.assertFalse(ascendance.isolated(self.k, self.target, self.target))     # its own kin
        a = {"id": "S-A", "people": self.target, "name": "A", "polity": "A", "realm": "x", "ended": False}
        b = {"id": "S-B", "people": self.actor, "name": "B", "polity": "B", "realm": "y", "ended": False}
        polity.sovereigns(self.k).update({"S-A": a, "S-B": b})
        polity.stats(self.k)["treaties"]["S-A|S-B"] = {"a": "S-A", "b": "S-B", "kind": "trade", "since": 0}
        polity._bend(self.k)
        self.assertNotIn("S-A|S-B", polity.stats(self.k)["treaties"])             # the open treaty lapses

    def test_works_a_book_in_deficit_makes_dangerous_are_interdicted_until_ascended(self):
        technology.stats(self.k)["of"].setdefault(self.target, {})["cyber"] = 0
        rec = ascendance.stats(self.k)["of"][self.target]
        rec["books"] = {"minds": "1/2"}
        ascendance._interdict(self.k, self.target, rec, None)
        self.assertTrue(technology.found(self.k, self.target, "cyber"))
        self.assertFalse(technology.has(self.k, self.target, "cyber"))           # found, but stopped
        rec["ruling"] = "ascended"
        ascendance._interdict(self.k, self.target, rec, None)
        self.assertTrue(technology.has(self.k, self.target, "cyber"))

    def test_the_watch_catches_as_far_as_its_mastery_outweighs_the_operators(self):
        with mock.patch.object(covert, "_info", side_effect=lambda k, w: {"op": 3.0, "w": 1.0}.get(w, 0.0)):
            self.assertAlmostEqual(covert.catch(self.k, "op", ["w"]), 0.25)
            self.assertAlmostEqual(covert.catch(self.k, "op", ["w", "w"]), 0.25)   # one watcher, counted once
            self.assertEqual(covert.catch(self.k, "op", []), 0.0)                    # unwatched

    def _lots(self):
        comm = "ORE"
        staples.move(self.tw, comm, staples.reserve(self.k, self.tw, comm) + 1000 - staples.held(self.tw, comm))
        return comm

    def test_an_unseen_exploiter_carries_off_the_surplus_and_its_history_darkens(self):
        comm = self._lots()
        worlds = relations._peoples(self.k)[self.target]
        def held():
            return sum(staples.held(w, comm) for w in worlds) + staples.held(self.home, comm)
        total = held()
        civ = self.home.civilization
        dark = float(getattr(civ, "dark", 0.0) or 0.0) if civ is not None else 0.0
        with mock.patch.object(decide, "choose", side_effect=_accept), \
                mock.patch.object(covert, "_route_cost", return_value=(1, 0.0)), \
                mock.patch.object(covert, "_caught", return_value=False):
            got = covert.exploit(self.k, self.actor, self.home, self.target, [])
        self.assertGreater(got, 0)
        self.assertEqual(staples.surplus(self.k, self.tw, comm), 0)
        self.assertEqual(held(), total)                                             # carried, not made
        if civ is not None:
            self.assertGreater(float(civ.dark), dark)                                # the truth, seen or not

    def test_a_caught_exploiter_takes_nothing_and_is_sanctioned_by_the_realm(self):
        comm = self._lots()
        held = staples.held(self.tw, comm)
        with mock.patch.object(decide, "choose", side_effect=_accept), \
                mock.patch.object(covert, "_route_cost", return_value=(1, 0.0)), \
                mock.patch.object(covert, "_watch", return_value=(["civ:Keeper"], "civ:Keeper", None)), \
                mock.patch.object(covert, "_caught", return_value=True):
            self.assertEqual(covert.exploit(self.k, self.actor, self.home, self.target, []), 0.0)
        self.assertEqual(staples.held(self.tw, comm), held)
        self.assertTrue(covert.sanctioned(self.k, self.actor, "civ:Keeper"))
        a = sorted(self.k.sectors)[0]
        b = next(w for w in self.k.sectors[a].warps if w in self.k.sectors)
        with mock.patch.object(transit, "owner", return_value="civ:Keeper"):
            self.assertTrue(transit.blocks(self.k, self.actor, a, b))                # its lanes turn it back

    def test_the_light_does_not_profit_by_taking(self):
        self._lots()
        with mock.patch.object(covert, "_route_cost", return_value=(1, 0.0)), \
                mock.patch.object(covert, "_light", return_value=1.0), \
                mock.patch.object(covert, "_caught", return_value=False):
            self.assertEqual(covert.exploit(self.k, self.actor, self.home, self.target, []), 0.0)

    def test_a_stifler_erases_its_share_of_the_years_learning(self):
        covert.stats(self.k)["taken"][self.actor] = {self.target: 10_000.0}
        now = knowledge.stocks(self.k, self.target)
        covert.stats(self.k)["known"][self.target] = {d: v for d, v in now.items()}
        now["information"] = now.get("information", 0.0) + 10.0                   # this year's learning
        before = now["information"]
        with mock.patch.object(decide, "choose", side_effect=_accept), \
                mock.patch.object(covert, "_info", side_effect=lambda k, w: 3.0 if w == self.actor else 1.0), \
                mock.patch.object(covert, "_caught", return_value=False):
            share = covert.stifle(self.k, self.actor, self.home, self.target, [])
        self.assertAlmostEqual(share, 0.75)
        self.assertAlmostEqual(knowledge.stocks(self.k, self.target)["information"], before - 7.5)


if __name__ == "__main__":
    unittest.main()
