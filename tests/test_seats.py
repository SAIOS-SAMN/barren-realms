"""
The house relay's game side: a mind takes a seat (one mind per seat) and the built-in mind steps aside; its percept
carries the built-in mind's counsel; its calls go through the game's own doors, only from the mind that holds the
seat and only within its role; every call is an outcome on the seat's books; a seated ancients' mind is handed the
court task; its own answer is filed under the ancients' reserve.
"""

import os
import unittest
from unittest import mock

from xylarium.kernel import ascendance, court, seats, spheres, stewardship
from xylarium.kernel.engine import GameKernel
import struct

from xylarium.uplink import anastome as an

VK, OTHER = "ab" * 32, "cd" * 32


class TestSeats(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        spheres.ensure(self.k)
        self.realm = stewardship.realms(self.k)[0]
        self.seat = f"steward:{self.realm}"

    def test_one_mind_per_seat_and_the_built_in_mind_steps_aside(self):
        self.assertIsNone(stewardship.steward_of(self.k, self.realm))
        self.assertTrue(seats.take(self.k, self.seat, VK)["ok"])
        self.assertEqual(stewardship.steward_of(self.k, self.realm), seats.pid(VK, self.seat))    # a player's seat now
        self.assertFalse(seats.take(self.k, self.seat, OTHER)["ok"])

    def test_one_mind_holds_two_realms_and_each_seat_is_its_own_player(self):
        other = stewardship.realms(self.k)[1]
        self.assertTrue(seats.take(self.k, self.seat, VK)["ok"])
        self.assertTrue(seats.take(self.k, f"steward:{other}", VK)["ok"])          # the same key, a second seat
        self.assertEqual(stewardship.realm_held(self.k, seats.pid(VK, self.seat)), self.realm)
        self.assertEqual(stewardship.realm_held(self.k, seats.pid(VK, f"steward:{other}")), other)

    def test_calls_come_only_from_the_seated_mind_and_within_its_role(self):
        seats.take(self.k, self.seat, VK)
        self.assertEqual(seats.call(self.k, self.seat, OTHER, "withdraw")["why"], "the seat is not held by this mind")
        self.assertIn("no function", seats.call(self.k, self.seat, VK, "forge")["why"])
        who = next(w for w in spheres.stats(self.k)["nets"] if spheres.presence(self.k, self.realm) != w)
        ascendance.petition(self.k, who, self.realm)
        self.assertTrue(seats.call(self.k, self.seat, VK, "quarantine", people=who)["ok"])
        self.assertEqual(ascendance.ruling(self.k, who), "quarantine")
        self.assertEqual(seats.stats(self.k)["books"][self.seat]["calls"], 3)

    def test_a_stewards_percept_carries_the_built_in_minds_counsel(self):
        who = next(w for w in spheres.stats(self.k)["nets"] if spheres.presence(self.k, self.realm) != w)
        ascendance.petition(self.k, who, self.realm)
        ascendance.stats(self.k)["of"][who]["books"] = ascendance.books(self.k, who, self.realm)
        p = seats.percept(self.k, self.seat)
        self.assertIn(who, p["petitions"])
        self.assertEqual(p["counsel"][0]["people"], who)
        self.assertIn(p["counsel"][0]["call"], ("ascend", "quarantine"))

    def test_a_seated_minds_answer_is_filed_under_the_ancients_reserve(self):
        house = "civ:Elder"
        task = {"id": bytes(range(32)), "train": [([[1, 1, 2]], [[1], [1], [2]])], "test": [[[3, 4]]]}
        sent = []
        with mock.patch.object(court, "houses", return_value=[house]), \
                mock.patch.dict(os.environ, {court.ENDPOINT_ENV: "127.0.0.1:1"}), \
                mock.patch("xylarium.uplink.anastome.speak", side_effect=lambda a, act, **kw: sent.append(act) or
                           bytes([2]) + struct.pack("<4Q", 0, 1, 0, 0)):
            seat = f"ancients:{house}"
            self.assertTrue(seats.take(self.k, seat, VK)["ok"])
            seats.hold_task(self.k, seat, task)
            self.assertFalse(seats.call(self.k, seat, VK, "answer")["ok"])     # no tape: the answer does not read
            got = seats.call(self.k, seat, VK, "answer", tape=b"RULE-TAPE", outputs=b"\x01OUT")
        self.assertTrue(got["ok"])
        self.assertEqual(sent[0], an.solve_raw(an.key("ancients"), task["id"], b"\x01OUT", b"RULE-TAPE"))
        self.assertEqual(court.stats(self.k)["of"][house]["closed"], 1)
        self.assertIsNone(seats.task_of(self.k, seat))

if __name__ == "__main__":
    unittest.main()
