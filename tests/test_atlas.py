"""
The universe's throats on the hypha's MAP (78.154 LOCAL THROAT): each end's frame is an exact transvection of the
hyperbolic sheet (even, a versor, fixing e+, carrying the pole to the upper sheet) to the end's place; a multivector
is written as mycelium writes it; mapped throats are read again at every commit.
"""

import struct
import unittest
from fractions import Fraction as F
from unittest import mock

from xylarium.kernel import versor
from xylarium.uplink import atlas

R = F("124147.6")


class TestFrames(unittest.TestCase):
    def test_a_frame_carries_the_pole_exactly_to_its_place_on_the_upper_sheet(self):
        for p in ((8.0, 0.0, 0.0), (-3.25, 7.5, 0.125), (0.0, 0.0, 0.0)):
            f = atlas.frame_to(p, R)
            self.assertTrue(all(bin(m).count("1") % 2 == 0 for m in f.c))                     # even
            self.assertEqual((f * versor.Mv({atlas.EP: 1})).c, (versor.Mv({atlas.EP: 1}) * f).c)   # fixes e+
            v = atlas.place_of(f)
            self.assertEqual(v.c, atlas.sheet_point(p, R).c)                                 # its own place
            vv = (v * v).c
            self.assertEqual((vv.get(0), v.c.get(atlas.EM) > 0), (-1, True))                # on the upper sheet

    def test_a_multivector_is_written_as_mycelium_writes_it(self):
        m = versor.Mv({0: F(3, 2), 16: F(-1, 4)})
        b = atlas.mv_bytes(m)
        self.assertEqual(b[0], 0)                                                            # no base axis used
        self.assertEqual(b[1:6], bytes([1, 1, 3, 1, 2]))                                     # +3/2
        zero = bytes([0, 1, 0, 1, 1])
        self.assertEqual(b[6:6 + 5 * 15], zero * 15)                                         # masks 1..15: zero
        self.assertEqual(b[6 + 5 * 15:6 + 5 * 16], bytes([2, 1, 1, 1, 4]))                   # mask 16: -1/4
        self.assertEqual(atlas.mv_bytes(versor.Mv({1: 1}))[0], 1)                            # e1 used: n = 1


class TestMapping(unittest.TestCase):
    def test_throats_are_mapped_then_read_again_after_a_commit(self):
        from xylarium.kernel import cosmos, transit
        from xylarium.kernel.engine import GameKernel
        k = GameKernel(seed=42)
        transit.stats(k)["worms"] = {"1-2": {"a": 1, "b": 2, "kind": "forged", "builders": "civ:X"}}
        posted = []
        with mock.patch.object(cosmos, "position", return_value={"x": 8.0, "y": 0.0, "z": 0.0}), \
                mock.patch.object(cosmos, "cosmos_seed", return_value=42):
            got = atlas.map_throats(k, lambda act: posted.append(act) or b"\x01" + bytes(40), since_u=0)
            again = atlas.map_throats(k, lambda act: posted.append(act) or b"\x01" + bytes(40), since_u=0)
            later = atlas.map_throats(k, lambda act: posted.append(act) or b"\x01" + bytes(40), since_u=k.cycle_count + 1)
        self.assertEqual((got["mapped"], again["mapped"], later["mapped"]), (1, 0, 1))
        self.assertEqual((posted[0][0], posted[0][33:36]), (0x3E, bytes([0x80, 0, 14])))
        self.assertEqual(posted[0][36 + 84], 2)                                              # record kind 2


if __name__ == "__main__":
    unittest.main()
