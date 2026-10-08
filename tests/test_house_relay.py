"""
The house relay on the seat wire: a mind's signed TAKE is answered TAKEN and binds the seat; its signed CALL goes
through the game's doors and is answered OUTCOME with the call's ref; a held seat's PERCEPT is posted on its beat;
a CALL signed by another key is refused and changes nothing.
"""

import os
import struct
import unittest

from nacl.signing import SigningKey

from xylarium.kernel import ascendance, seats, spheres, stewardship
from xylarium.kernel.engine import GameKernel
from xylarium.uplink import anastome as an, house, seat_wire as w


class TestHouseRelay(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        spheres.ensure(self.k)
        self.realm = stewardship.realms(self.k)[0]
        self.mind = SigningKey(bytes(range(32)))
        self.domain = an.vk(an.key("domain"))
        self.posted, self.inbox = [], []

    def _turn(self):
        mail, self.inbox = self.inbox, []
        return house.turn(self.k, lambda act: self.posted.append(act) or b"\x01", lambda: mail)

    def _seat_n(self):
        return next(s["n"] for s in house.numbered(self.k) if s["id"] == f"steward:{self.realm}")

    def _act(self, sub, fields, key=None):
        return w.seal(key or self.mind, sub, fields)

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
        who = next(x for x in spheres.stats(self.k)["nets"] if spheres.presence(self.k, self.realm) != x)
        ascendance.petition(self.k, who, self.realm)
        call = self._act(w.CALL, self.domain + struct.pack("<I", n) + vk + os.urandom(32)
                         + struct.pack("<H", w.FN_ID["quarantine"]) + w.args([(w.KEY, w.name_key(who))]))
        self.inbox, self.posted = [(2, w.CALL, call)], []
        self._turn()
        out = next(a for a in self.posted if a[1] == w.OUTCOME)
        self.assertEqual(out[2 + 32 + 4 + 32:2 + 32 + 4 + 32 + 32], w.call_ref(call))
        self.assertEqual(out[2 + 32 + 4 + 32 + 32], 1)                   # applied
        self.assertEqual(ascendance.ruling(self.k, who), "quarantine")

    def test_a_call_signed_by_another_key_is_refused(self):
        n, vk = self._seat_n(), self.mind.verify_key.encode()
        seats.take(self.k, f"steward:{self.realm}", vk.hex())
        who = next(x for x in spheres.stats(self.k)["nets"] if spheres.presence(self.k, self.realm) != x)
        ascendance.petition(self.k, who, self.realm)
        forged = self._act(w.CALL, self.domain + struct.pack("<I", n) + vk + os.urandom(32)
                           + struct.pack("<H", w.FN_ID["quarantine"]) + w.args([(w.KEY, w.name_key(who))]),
                           key=SigningKey(bytes(32)))
        self.inbox = [(1, w.CALL, forged)]
        self._turn()
        out = next(a for a in self.posted if a[1] == w.OUTCOME)
        self.assertEqual(out[2 + 32 + 4 + 32 + 32], 0)
        self.assertEqual(ascendance.ruling(self.k, who), "pending")


if __name__ == "__main__":
    unittest.main()
