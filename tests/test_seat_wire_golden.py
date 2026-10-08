"""
The seat wire v1 matches mycelium's golden vectors byte for byte (mycelium e1a49db4, dialogue/tests/seat.rs): a CALL
with Q, BigQ and Key args, its ref, and a PERCEPT carrying one COUNSEL - fixed Q fields tagged as arguments are.
"""

import struct
import unittest
from fractions import Fraction

from nacl.signing import SigningKey

from xylarium.uplink import seat_wire as w

GOLDEN_CALL = "53040909090909090909090909090909090909090909090909090909090909090909070000008139770ea87d175f56a35466c34c7ecccb8d8a91b4ee37a25df60f5b8fc9b394030303030303030303030303030303030303030303030303030303030303030303000300030000000000000002000000000000000509000000000000000000400100030105050505050505050505050505050505050505050505050505050505050505055e38bf9a10d0ff42b5248d2279f80984d513a18beb9da5925182e1c22f5728e48774e744decd809eb8b2c8e4568683f89441ff95b93ca300b77a6456cd27860f"
GOLDEN_CALL_REF = "31cb3c49a809b03a09c5b4a57005dcf5399675654167a07819cc4fcd76ff9041"
GOLDEN_PERCEPT = "53030909090909090909090909090909090909090909090909090909090909090909070000008139770ea87d175f56a35466c34c7ecccb8d8a91b4ee37a25df60f5b8fc9b394000c00000000000000010000000000000001000000000000000100ffff03000300030000000000000002000000000000000509000000000000000000400100030105050505050505050505050505050505050505050505050505050505050505050001000000000000000200000000000000000100000000000000030000000000000038fb1c38b9c4d70d0daccf1fc970bc239d412f8b9e0fba59bc5cdb00e10c123c22e1501bb429cc5f0d2b704547697f99201bf32e2258e999f28824b7640dd903"


class TestGolden(unittest.TestCase):
    def setUp(self):
        self.house, self.mind = SigningKey(bytes([1] * 32)), SigningKey(bytes([2] * 32))
        self.domain, self.vk = bytes([9] * 32), self.mind.verify_key.encode()
        self.args = [(w.Q_, Fraction(3, 2)), (w.BIGQ, Fraction(2 ** 70, 3)), (w.KEY, bytes([5] * 32))]

    def test_call_and_its_ref(self):
        call = w.seal(self.mind, w.CALL, self.domain + struct.pack("<I", 7) + self.vk + bytes([3] * 32)
                      + struct.pack("<H", 3) + w.args(self.args))
        self.assertEqual(call.hex(), GOLDEN_CALL)
        self.assertEqual(w.call_ref(call).hex(), GOLDEN_CALL_REF)
        self.assertTrue(w.read_call(call)["ok"])

    def test_percept_with_counsel(self):
        p = w.percept_post(self.house, self.domain, 7, self.vk, Fraction(12), 1, [],
                           [(3, self.args, Fraction(1, 2), Fraction(1, 3))])
        self.assertEqual(p.hex(), GOLDEN_PERCEPT)


if __name__ == "__main__":
    unittest.main()
