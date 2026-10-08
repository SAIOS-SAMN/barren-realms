"""
Pulses as exact versors of Cl(4,1): bent (translated), rotated, twisted (screwed - its pitch the wavelength) and
flipped (reflected, an odd versor); a loop of pulses that fails to close carries torsion.
"""

import unittest
from fractions import Fraction as F

from xylarium.kernel import versor as V


class TestVersor(unittest.TestCase):
    def test_bent_rotated_flipped_exactly(self):
        self.assertEqual(V.move(V.translator((F(1, 2), 0, 0)), (1, 2, 3)), (F(3, 2), 2, 3))
        self.assertEqual(V.move(V.rotor(0, 1, 1), (1, 0, 0)), (0, -1, 0))        # a quarter turn, rational
        self.assertEqual(V.move(V.reflection((1, 0, 0)), (1, 2, 3)), (-1, 2, 3))  # flipped: odd

    def test_a_closed_loop_has_no_torsion_and_a_screw_loop_carries_its_pitch(self):
        self.assertEqual(V.torsion([V.rotor(0, 1, 1)] * 4), (0, 0, 0))
        self.assertEqual(V.torsion([V.screw(0, 1, 1, (0, 0, F(1, 4)))] * 4), (0, 0, 1))   # one full turn: the pitch

    def test_a_versor_crosses_the_wire_exact(self):
        s = V.screw(0, 1, F(1, 3), (0, 0, F(2, 7)))
        self.assertEqual(V.from_wire(V.to_wire(s)), s)


if __name__ == "__main__":
    unittest.main()
