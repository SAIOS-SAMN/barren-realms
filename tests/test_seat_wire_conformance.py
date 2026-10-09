"""
Conformance with mycelium's seat wire (Concordance 1.4: no kernel is judged by reproducing bytes): each side's acts
DECODE to the same exact typed values - rationals exactly equal, keys, records, counsel, the call and its args - and
every SIGNATURE VERIFIES under its signer's key. mycelium's sample acts (e1a49db4) are read as inputs; barren's own
acts are read back by the same reader.
"""

import struct
import unittest
from fractions import Fraction

from nacl.signing import SigningKey

from xylarium.uplink import seat_wire as w

THEIR_CALL = ("53040909090909090909090909090909090909090909090909090909090909090909070000008139770ea87d175f56a35466c34c"
              "7ecccb8d8a91b4ee37a25df60f5b8fc9b39403030303030303030303030303030303030303030303030303030303030303030300"
              "03000300000000000000020000000000000005090000000000000000004001000301050505050505050505050505050505050505"
              "05050505050505050505050505055e38bf9a10d0ff42b5248d2279f80984d513a18beb9da5925182e1c22f5728e48774e744decd"
              "809eb8b2c8e4568683f89441ff95b93ca300b77a6456cd27860f")
THEIR_PERCEPT = ("53030909090909090909090909090909090909090909090909090909090909090909070000008139770ea87d175f56a35466c34c"
                 "7ecccb8d8a91b4ee37a25df60f5b8fc9b394000c00000000000000010000000000000001000000000000000100ffff0300030003"
                 "00000000000000020000000000000005090000000000000000004001000301050505050505050505050505050505050505050505"
                 "05050505050505050505050001000000000000000200000000000000000100000000000000030000000000000038fb1c38b9c4d7"
                 "0d0daccf1fc970bc239d412f8b9e0fba59bc5cdb00e10c123c22e1501bb429cc5f0d2b704547697f99201bf32e2258e999f28824"
                 "b7640dd903")
HOUSE, MIND = SigningKey(bytes([1] * 32)), SigningKey(bytes([2] * 32))
DOMAIN = bytes([9] * 32)
ARGS = [(w.Q_, Fraction(3, 2)), (w.BIGQ, Fraction(2 ** 70, 3)), (w.KEY, bytes([5] * 32))]


def values(args):
    return [v for _, v in args]


class TestConformance(unittest.TestCase):
    def test_a_call_decodes_to_the_same_values_and_its_signature_verifies(self):
        ours = w.seal(MIND, w.CALL, DOMAIN + struct.pack("<I", 7) + MIND.verify_key.encode() + bytes([3] * 32)
                      + struct.pack("<H", 3) + w.args(ARGS))
        for act in (bytes.fromhex(THEIR_CALL), ours):
            c = w.read_call(act)
            self.assertTrue(c["ok"])                                       # verifies under the mind's own key
            self.assertEqual((c["domain"], c["seat"], c["mind"], c["fn"]), (DOMAIN, 7, MIND.verify_key.encode(), 3))
            self.assertEqual(values(c["args"]), values(ARGS))              # rationals exactly equal, the key

    def test_a_percept_with_counsel_decodes_to_the_same_values_and_verifies(self):
        ours = w.percept_post(HOUSE, DOMAIN, 7, MIND.verify_key.encode(), Fraction(12), 1, [],
                              [(3, ARGS, Fraction(1, 2), Fraction(1, 3))])
        for act in (bytes.fromhex(THEIR_PERCEPT), ours):
            p = w.read_percept(act, HOUSE.verify_key.encode())
            self.assertTrue(p["ok"])                                       # verifies under the house's key
            self.assertEqual((p["seat"], p["local"], p["seq"], p["records"]), (7, Fraction(12), 1, []))
            fn, a, worth, cost = p["counsel"][0]
            self.assertEqual((fn, values(a), worth, cost), (3, values(ARGS), Fraction(1, 2), Fraction(1, 3)))


class TestMailFromTheWire(unittest.TestCase):
    """The first READ-MAIL reply :7500 sent barren-realms' house (aefc6a39): one TAKE, seat 1, signed by its mind."""
    REPLY = ("0100030000000000000001a4000000e1b241547004a0d44fb8330b23533a99c7121ee2aaaeca9a8d6ae32c677242190100"
             "0000a1a52d928ca2f114d2b211c3c4cf8c1f88b30f5895c7450117176c6c940276efb33041dcc1649a74e48fbc33565c1e2a"
             "4bc5c01f3915d90ee635aba40d0067572430a2efd1928ff8d754f02adaee5117dba5422db899acf5074d64172a8ec47e2efc"
             "d1306c23f681abbcb21d27cdc12c7c5519974c6b4488d45fc8c925a7d207")

    def test_the_take_reads_whole_and_its_signature_holds(self):
        items = w.read_mail_reply(bytes.fromhex(self.REPLY))
        self.assertEqual([(s, sub) for s, sub, _ in items], [(3, w.TAKE)])
        t = w.read_take(items[0][2])
        self.assertEqual(t["seat"], 1)
        self.assertTrue(t["ok"])


if __name__ == "__main__":
    unittest.main()


class TestTUniversalPoint(unittest.TestCase):
    """A frame carrying the hyphae's quorum-final point (Concordance 1.11, mycelium 78.152) sets 0x80 on its lane
    byte; its last 84 body bytes are the point; a frame without the bit is read as before."""

    def test_a_point_is_read_off_the_frame_and_the_body_is_what_precedes_it(self):
        import struct as _s
        from xylarium.uplink import anastome as an
        gen = bytes(range(32))
        pt = gen + _s.pack("<IQQQQQQ", 7, 1, 2, 3, 4, 5, 6)
        body, p = an.unframe(an.POINT_BIT, b"\x01reply" + pt)
        self.assertEqual(body, b"\x01reply")
        self.assertEqual((p["epoch"], p["h"], p["lanes"], p["k"]), (7, 1, (2, 3, 4, 5), 6))
        self.assertEqual(an.point_text(p), gen.hex() + "." + "%08x" % 7 + "/" + ":".join("%016x" % x for x in range(1, 7)))
        self.assertEqual(an.unframe(0, b"\x01reply" + pt), (b"\x01reply" + pt, None))

    def test_every_act_carries_a_point_and_the_zero_point_before_one_is_read(self):
        from xylarium.uplink import anastome as an
        self.assertEqual(an.put_point(None), bytes(an.POINT_LEN))
        gen = bytes(range(32))
        p = an.read_point(gen + __import__("struct").pack("<IQQQQQQ", 7, 1, 2, 3, 4, 5, 6))
        self.assertEqual(an.read_point(an.put_point(p)), p)              # round trip, exact

