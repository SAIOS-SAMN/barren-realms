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


class TestStarAbsorbs(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        self.sec = next(s for s in self.k.sectors.values() if len(s.planets) >= 2)

    def test_what_a_pulse_brings_in_equals_light_plus_gravity_plus_burning_out(self):
        from fractions import Fraction as F
        from xylarium.kernel import versor
        pulse = versor.screw(0, 1, F(1, 50), (0, 0, F(1, 1000)))     # a small twist with a pitch
        led = field.absorb(self.k, self.sec.id, pulse, F(10 ** 6))
        parts = sum(F(led[k]) for k in ("gravity", "light", "burned_out"))
        self.assertEqual(parts, F(led["in"]))                          # conserved, exactly
        self.assertGreater(F(led["gravity"]), 0)                       # its worlds' orbits held

    def test_a_pulse_too_weak_to_relock_leaves_its_worlds_sheared(self):
        from fractions import Fraction as F
        from xylarium.kernel import versor
        led = field.absorb(self.k, self.sec.id, versor.translator((F(1, 2), 0, 0)), F(1, 10 ** 30))
        self.assertEqual(F(led["light"]), 0)
        self.assertTrue(led["unlocked"])                               # what it could not re-lock stays sheared

    def test_the_identity_shears_nothing_and_all_is_burned(self):
        from fractions import Fraction as F
        from xylarium.kernel import versor
        led = field.absorb(self.k, self.sec.id, versor.Mv.scalar(1), F(1000))
        self.assertEqual(F(led["gravity"]), 0)
        self.assertEqual(F(led["burned_out"]), F(7))                   # its burning's mass defect
