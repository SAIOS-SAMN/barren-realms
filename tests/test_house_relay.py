"""
The house relay on the seat wire: a mind's signed TAKE of an ancients' council seat is answered TAKEN and binds the
seat; its signed CALL is answered OUTCOME with the call's ref; a held seat's PERCEPT is posted on its beat; a CALL
signed by another key is refused and changes nothing; seats a network mind may no longer hold are released (3.9).
"""

import os
import struct
import unittest
from unittest import mock

from nacl.signing import SigningKey

from xylarium.kernel import court, seats, spheres
from xylarium.kernel.engine import GameKernel
from xylarium.uplink import anastome as an, house, seat_wire as w

HOUSE = "civ:Elder"
TASK = {"id": bytes(range(32)), "train": [([[1]], [[1]])], "test": [[[2]]]}


def _council(test, k):
    from xylarium.kernel import relations
    world = next(p for s in k.sectors.values() for p in s.planets)
    for p in (mock.patch.object(court, "houses", return_value=[HOUSE]),
              mock.patch.object(relations, "_peoples", return_value={HOUSE: [world]}),
              mock.patch.object(house, "genesis", return_value=None)):     # no recut: the live genesis is not ours
        p.start()
        test.addCleanup(p.stop)
    return f"ancients:{HOUSE}@{world.id}"


class TestHouseRelay(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        spheres.ensure(self.k)
        self.seat_id = _council(self, self.k)
        self.mind = SigningKey(bytes(range(32)))
        self.domain = an.vk(an.key("domain"))
        self.posted, self.inbox = [], []

    def _turn(self):
        mail, self.inbox = self.inbox, []
        return house.turn(self.k, lambda act: self.posted.append(act) or b"\x01", lambda: mail)

    def _seat_n(self):
        return next(s["n"] for s in house.numbered(self.k) if s["id"] == self.seat_id)

    def _act(self, sub, fields, key=None):
        return w.seal(key or self.mind, sub, fields)

    def _answer(self, n, vk, key=None):
        return self._act(w.CALL, self.domain + struct.pack("<I", n) + vk + os.urandom(32)
                         + struct.pack("<H", w.FN_ID["answer"]) + w.args([(w.BYTES, b"tape"), (w.BYTES, b"\x01out")]),
                         key=key)

    def test_take_call_outcome_and_percept(self):
        self._turn()
        self.assertEqual(self.posted[0][1], w.SEATS)
        n, vk = self._seat_n(), self.mind.verify_key.encode()
        self.inbox = [(1, w.TAKE, self._act(w.TAKE, self.domain + struct.pack("<I", n) + vk + os.urandom(32)))]
        self.posted = []
        self._turn()
        taken = next(a for a in self.posted if a[1] == w.TAKEN)
        self.assertEqual(taken[-64 - 3], 1)                               # ok
        self.assertTrue(any(a[1] == w.PERCEPT for a in self.posted))      # the held seat perceives on its beat
        seats.hold_task(self.k, self.seat_id, TASK)
        call = self._answer(n, vk)
        self.inbox, self.posted = [(2, w.CALL, call)], []
        bounty = bytes([2]) + struct.pack("<4Q", 0, 3, 0, 0)
        with mock.patch.dict(os.environ, {court.ENDPOINT_ENV: "127.0.0.1:1"}), \
                mock.patch.object(an, "speak", return_value=bounty):
            self._turn()
        out = next(a for a in self.posted if a[1] == w.OUTCOME)
        self.assertEqual(out[2 + 32 + 4 + 32:2 + 32 + 4 + 32 + 32], w.call_ref(call))
        self.assertEqual(out[2 + 32 + 4 + 32 + 32], 1)                   # applied: the court closed it
        self.assertEqual(court.stats(self.k)["of"][HOUSE]["closed"], 1)

    def test_a_call_signed_by_another_key_is_refused(self):
        n, vk = self._seat_n(), self.mind.verify_key.encode()
        seats.take(self.k, self.seat_id, vk.hex())
        seats.hold_task(self.k, self.seat_id, TASK)
        self.inbox = [(1, w.CALL, self._answer(n, vk, key=SigningKey(bytes(32))))]
        self._turn()
        out = next(a for a in self.posted if a[1] == w.OUTCOME)
        self.assertEqual(out[2 + 32 + 4 + 32 + 32], 0)
        self.assertIsNotNone(seats.task_of(self.k, self.seat_id))   # nothing changed

    def test_only_the_ancients_council_seats_are_listed_and_others_are_released(self):
        self.assertEqual({s["role"] for s in house.numbered(self.k)}, {"ancients"})
        seats.stats(self.k)["held"]["progenitor:civ:Elder"] = "ab" * 32      # held before the ruling
        self._turn()
        self.assertNotIn("progenitor:civ:Elder", seats.stats(self.k)["held"])


class TestAnswerWithTape(unittest.TestCase):
    def test_bytes_args_round_trip_and_answer_carries_the_tape(self):
        a = w.args([(w.BYTES, b"tape-bytes"), (w.BYTES, b"\x01\x01\x00\x01\x00\x07")])
        got, _ = w.read_args(a, 0)
        self.assertEqual(got[0], (w.BYTES, b"tape-bytes"))
        k = GameKernel(seed=42)
        self.assertEqual(house.kwargs_of(k, "answer", got), {"tape": b"tape-bytes", "outputs": b"\x01\x01\x00\x01\x00\x07"})
        self.assertEqual(house.kwargs_of(k, "answer", [(w.COUNT, 6)]), {})     # fn 1 is the minds' tape, never steps
        self.assertEqual(w.FUNCTIONS[1], ("answer", (w.BYTES, w.BYTES)))        # house.rs: [Bytes(tape), Bytes(outputs)]


class TestMailOnce(unittest.TestCase):
    def test_a_take_handed_back_again_is_answered_once(self):
        k = GameKernel(seed=42)
        spheres.ensure(k)
        seat_id = _council(self, k)
        mind = SigningKey(bytes(range(32)))
        n = next(s["n"] for s in house.numbered(k) if s["id"] == seat_id)
        take = w.seal(mind, w.TAKE, an.vk(an.key("domain")) + struct.pack("<I", n) + mind.verify_key.encode()
                      + os.urandom(32))
        posted = []
        for _ in range(3):                                            # a box that ignores the cursor hands it back
            house.turn(k, lambda act: posted.append(act) or b"\x01", lambda: [(5, w.TAKE, take)])
        self.assertEqual(sum(1 for a in posted if a[1] == w.TAKEN), 1)


class TestCursor(unittest.TestCase):
    def test_the_cursor_follows_the_last_read_even_when_a_restarted_hypha_counts_from_one(self):
        k = GameKernel(seed=42)
        spheres.ensure(k)
        house.state(k)["mail_seq"] = 1582                                 # the old hypha's count
        house.turn(k, lambda act: b"\x01", lambda: [(3, w.CALL, b"\x53\x04x"), (4, w.CALL, b"\x53\x04y")])
        self.assertEqual(house.state(k)["mail_seq"], 4)                   # its box drains by this cursor


class TestMailEpoch(unittest.TestCase):
    def test_v14_read_mail_is_signed_and_its_reply_carries_the_relays_epoch(self):
        reader = an.key("ancients")
        act = w.read_mail_epoch(reader, 7, 99, bytes(32))
        self.assertEqual((act[1], struct.unpack_from("<QQ", act, 34)), (w.READ_MAIL_EPOCH, (7, 99)))
        self.assertTrue(w.opened(act, reader.verify_key.encode()))
        reply = bytes([1]) + struct.pack("<QQ", 5, 12) + struct.pack("<H", 0)
        self.assertEqual(w.read_mail_epoch_reply(reply), (5, 12, []))
        self.assertIsNone(w.read_mail_epoch_reply(bytes([0, 3])))          # a refusal is no mail


class TestRecut(unittest.TestCase):
    def test_a_new_genesis_lists_anew_and_reads_mail_from_the_start(self):
        from unittest import mock
        k = GameKernel(seed=42)
        spheres.ensure(k)
        posted = []
        with mock.patch.object(house, "genesis", return_value="old"):
            house.turn(k, lambda act: posted.append(act) or b"\x01", lambda: [])
            house.state(k)["mail_seq"] = 99
            posted.clear()
            house.turn(k, lambda act: posted.append(act) or b"\x01", lambda: [])
        self.assertFalse(any(a[1] == w.SEATS for a in posted))            # the same hypha: listed already
        with mock.patch.object(house, "genesis", return_value="new"):
            house.turn(k, lambda act: posted.append(act) or b"\x01", lambda: [])
        self.assertTrue(any(a[1] == w.SEATS for a in posted))             # a recut: listed anew
        self.assertEqual(house.state(k)["mail_seq"], 0)
