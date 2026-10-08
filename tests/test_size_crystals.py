"""
The size crystals (mycelium 78.143 Scale and Crop): a people that holds them reads a change of size off its family -
by decompaction, never search - and its program is said in the court's steps; one that does not cannot.
"""

import unittest

from xylarium.kernel import crystal as C
from xylarium.kernel import intellect
from xylarium.uplink import mind

G = ((1, 2), (3, 4))
SCENE = ((0, 0, 0, 0), (0, 5, 5, 0), (0, 5, 1, 0), (0, 0, 0, 0))


class TestSizeCrystals(unittest.TestCase):
    def test_scale_is_read_both_ways_and_checked_cell_for_cell(self):
        up = C.scaled(G, 3, 1)
        self.assertEqual(C.read_scale([(G, up)]), (3, 1))
        self.assertEqual(C.read_scale([(up, G)]), (1, 3))
        self.assertIsNone(C.read_scale([(G, ((1, 1, 2, 2), (1, 1, 2, 2), (3, 3, 4, 9), (3, 3, 4, 4)))]))

    def test_crop_is_the_one_body_of_its_hue(self):
        self.assertEqual(C.read_crop([(SCENE, ((5, 5), (5, 1)))]), 5)
        self.assertIsNone(C.cropped(((5, 0, 5),), 5))                  # two bodies: no one extent

    def test_only_a_people_holding_the_crystal_writes_the_program(self):
        task = {"rank": 2, "train": [(G, C.scaled(G, 2, 1))], "test": G}
        self.assertIsNone(intellect.decompact([C.ROT90], task))
        prog = intellect.decompact([C.ROT90, C.SCALE], task)
        self.assertEqual(prog, [(C.SCALE, 2, 1)])
        self.assertEqual(mind.steps_of(prog), [{"scale": [2, 1]}])
        crop = intellect.decompact([C.ROT90, C.CROP], {"rank": 2, "train": [(SCENE, ((5, 5), (5, 1)))], "test": SCENE})
        self.assertEqual(mind.steps_of(crop), [{"select_hue": 5}, {"crop": "body"}])


if __name__ == "__main__":
    unittest.main()
