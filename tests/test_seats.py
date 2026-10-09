"""
The house relay's game side (Concordance 3.9): network minds seat at the COUNCIL OF THE ANCIENTS only - one mind
per seat, each seat its own player; calls come only from the mind that holds the seat and only within its role;
every call is an outcome on the seat's books; a seated mind is handed the court task, and its own answer is filed
under the ancients' reserve. The progenitors' and stewards' seats are not offered, and any held is released.
"""

import os
import struct
import unittest
from unittest import mock

from xylarium.kernel import board, court, seats, spheres, stewardship
from xylarium.kernel.engine import GameKernel
from xylarium.uplink import anastome as an

VK, OTHER = "ab" * 32, "cd" * 32
HOUSE, OTHER_HOUSE = "civ:Elder", "civ:Younger"


class TestSeats(unittest.TestCase):
    def setUp(self):
        from xylarium.kernel import relations
        self.k = GameKernel(seed=42)
        spheres.ensure(self.k)
        w = [p for s in self.k.sectors.values() for p in s.planets][:3]
        self.worlds = {HOUSE: w[:2], OTHER_HOUSE: w[2:3]}                   # the Elder hold two worlds, the Younger one
        for p in (mock.patch.object(court, "houses", return_value=[HOUSE, OTHER_HOUSE]),
                  mock.patch.object(relations, "_peoples", return_value=self.worlds)):
            p.start()
            self.addCleanup(p.stop)
        self.seat = f"ancients:{HOUSE}@{w[0].id}"
        self.other = f"ancients:{OTHER_HOUSE}@{w[2].id}"

    def test_a_council_has_one_seat_per_world_its_house_holds(self):
        self.assertEqual({s["id"] for s in seats.seats(self.k)},
                         {f"ancients:{HOUSE}@{p.id}" for p in self.worlds[HOUSE]} | {self.other})
        realm = stewardship.realms(self.k)[0]
        self.assertFalse(seats.take(self.k, f"steward:{realm}", VK)["ok"])          # no network mind in a realm

    def test_one_mind_per_seat_and_one_mind_may_hold_two_councils_each_its_own_player(self):
        self.assertTrue(seats.take(self.k, self.seat, VK)["ok"])
        self.assertFalse(seats.take(self.k, self.seat, OTHER)["ok"])
        self.assertTrue(seats.take(self.k, self.other, VK)["ok"])
        self.assertNotEqual(seats.pid(VK, self.seat), seats.pid(VK, self.other))

    def test_a_council_seat_from_before_worlds_moves_to_a_world_of_its_house(self):
        seats.stats(self.k)["held"][f"ancients:{HOUSE}"] = VK               # one seat per house, as it was
        seats.release_unseatable(self.k)
        held = seats.stats(self.k)["held"]
        self.assertEqual(list(held.values()), [VK])
        self.assertTrue(next(iter(held)).startswith(f"ancients:{HOUSE}@"))

    def test_calls_come_only_from_the_seated_mind_and_within_its_role(self):
        seats.take(self.k, self.seat, VK)
        self.assertEqual(seats.call(self.k, self.seat, OTHER, "answer")["why"], "the seat is not held by this mind")
        self.assertIn("no function", seats.call(self.k, self.seat, VK, "forge")["why"])
        self.assertEqual(seats.stats(self.k)["books"][self.seat]["calls"], 2)

    def test_a_progenitor_or_steward_seat_held_before_the_ruling_is_released_to_the_game(self):
        realm = stewardship.realms(self.k)[0]
        p = seats.pid(VK, f"steward:{realm}")
        stewardship.stats(self.k)["stewards"][realm] = p
        seats.stats(self.k)["held"][f"steward:{realm}"] = VK
        self.assertEqual(seats.release_unseatable(self.k), [f"steward:{realm}"])
        self.assertIsNone(stewardship.steward_of(self.k, realm))                  # the realm's own steward again
        self.assertEqual(set(seats.stats(self.k)["held"]), set())

    def test_an_answer_not_judged_yet_keeps_its_task_and_is_filed_again(self):
        house = HOUSE
        task = {"id": bytes(range(32)), "train": [([[1]], [[1]])], "test": [[[2]]]}
        deferred = bytes([2]) + bytes(8) + bytes(32) + b"\0\0"            # the hypha's deferral: try again
        unread = bytes([3]) + struct.pack("<4Q", 0, 0, 0, 0)               # SOLVE_UNREAD: not judged yet
        replies = [deferred, unread, bytes([2]) + struct.pack("<4Q", 0, 1, 0, 0)]
        sent = []
        with mock.patch.object(court, "houses", return_value=[house]), \
                mock.patch.dict(os.environ, {court.ENDPOINT_ENV: "127.0.0.1:1"}), \
                mock.patch("xylarium.uplink.anastome.speak", side_effect=lambda a, act, **kw: sent.append(act)
                           or replies.pop(0)):
            seat = self.seat
            seats.take(self.k, seat, VK)
            seats.hold_task(self.k, seat, task)
            got = seats.call(self.k, seat, VK, "answer", tape=b"T", outputs=b"\x01O")
            self.assertTrue(got.get("retry"))
            self.assertIsNotNone(seats.task_of(self.k, seat))              # kept before its seat
            with mock.patch.object(an, "read_task", return_value=None):
                court.hand_tasks(self.k, lambda act: b"")                  # next stroke: filed again, unread
                self.assertIsNotNone(seats.task_of(self.k, seat))
                court.hand_tasks(self.k, lambda act: b"")                  # and again: judged, a bounty
        self.assertEqual(sent[0], sent[1])                                 # the same answer, re-filed
        self.assertEqual(sent[1], sent[2])
        self.assertEqual(court.stats(self.k)["of"][house]["closed"], 1)
        self.assertIsNone(seats.task_of(self.k, seat))

    def test_a_seated_minds_answer_is_filed_under_the_ancients_reserve(self):
        house = HOUSE
        task = {"id": bytes(range(32)), "train": [([[1, 1, 2]], [[1], [1], [2]])], "test": [[[3, 4]]]}
        sent = []
        with mock.patch.object(court, "houses", return_value=[house]), \
                mock.patch.dict(os.environ, {court.ENDPOINT_ENV: "127.0.0.1:1"}), \
                mock.patch("xylarium.uplink.anastome.speak", side_effect=lambda a, act, **kw: sent.append(act) or
                           bytes([2]) + struct.pack("<4Q", 0, 1, 0, 0)):
            seat = self.seat
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
