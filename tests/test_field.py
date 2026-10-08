"""
The field engine: a bell's front is computed once when it rings - by its earliest carrier - and reaches each place
when the cosmic clock passes its arrival, handed to the law that takes its kind; the field's value is closed form.
"""

import unittest
from fractions import Fraction
from unittest import mock

from xylarium.kernel import cosmos, field, geometry
from xylarium.kernel.engine import GameKernel

PLACES = {1: (8.0, 0.0, 0.0), 2: (8.0, 3.0, 0.0), 3: (8.0, 30.0, 0.0)}


class TestField(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        self.now = [1.0]
        self.patches = [mock.patch.object(field, "place_of", side_effect=lambda k, s, g=None: PLACES.get(s)),
                        mock.patch.object(cosmos, "deep_gyr", side_effect=lambda k, *a, **kw: self.now[0])]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.got = []
        field.HANDLERS["test"] = lambda k, src, arr: self.got.append(arr["sector"])

    def test_a_front_reaches_each_place_when_its_light_arrives_and_not_before(self):
        n = field.ring(self.k, {"kind": "test", "at": PLACES[1], "t": 1.0, "strength": 1.0}, [2, 3])
        self.assertEqual(n, 2)
        near, far = (1.0 + geometry.light_gyr(PLACES[1], PLACES[s]) for s in (2, 3))
        self.now[0] = (near + far) / 2
        field.pump(self.k)
        self.assertEqual(self.got, [2])                      # the near world has it; the far one does not yet
        self.now[0] = far
        field.pump(self.k)
        self.assertEqual(self.got, [2, 3])
        self.assertEqual(field.pump(self.k), 0)              # each arrival once

    def test_arrival_times_enter_the_kernel_exact(self):
        field.ring(self.k, {"kind": "test", "at": PLACES[1], "t": 1.0}, [2])
        _, t, _, _ = field.stats(self.k)["queue"][0]
        self.assertIsInstance(Fraction(t), Fraction)

    def test_the_field_is_closed_form_and_zero_before_the_front(self):
        field.ring(self.k, {"kind": "test", "at": PLACES[1], "t": 1.0, "strength": 2.0, "tau": 0.5}, [2])
        here = PLACES[2]
        arrive = 1.0 + geometry.light_gyr(PLACES[1], here)
        self.assertEqual(field.value(self.k, here, arrive - 1e-9), 0.0)
        self.assertAlmostEqual(field.value(self.k, here, arrive), 2.0 / 3.0, places=6)


if __name__ == "__main__":
    unittest.main()
