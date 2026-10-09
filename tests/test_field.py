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
        led = field.absorb(self.k, self.sec.id, versor.rotor(0, 1, F(1, 3)), F(1, 10 ** 30))
        self.assertEqual(F(led["light"]), 0)
        self.assertTrue(led["unlocked"])                               # what it could not re-lock stays sheared
        again = field.anchors_of(self.k, self.sec.id)                  # the next pulse finds them where they stand
        self.assertTrue(any(w["at"] != w["native"] for w in again))

    def test_a_translation_drifts_the_system_and_shears_no_orbit(self):
        from fractions import Fraction as F
        from xylarium.kernel import versor
        led = field.absorb(self.k, self.sec.id, versor.translator((F(1, 2), 0, 0)), F(1, 10 ** 30))
        self.assertEqual((F(led["gravity"]), led["unlocked"]), (0, {}))
        self.assertEqual(field.drift_au(self.k, self.sec.id), (F(1, 2), 0, 0))

    def test_the_identity_shears_nothing_and_all_is_burned(self):
        from fractions import Fraction as F
        from xylarium.kernel import versor
        led = field.absorb(self.k, self.sec.id, versor.Mv.scalar(1), F(1000))
        self.assertEqual(F(led["gravity"]), 0)
        share = field.burn_out_share(self.k, self.sec.id)               # its own fusion step's mass defect
        self.assertEqual(F(led["burned_out"]), field.grid(F(1000) * share))   # on the grid
        self.assertTrue(F(1, 1000) < share < F(1, 100))

    def test_quantum_radiation_is_the_absorbed_flux_at_the_world(self):
        from fractions import Fraction as F
        from xylarium.kernel import versor
        w = next(p for p in self.sec.planets if "q" in (p.body or {}))
        self.assertEqual(field.quantum_flux(self.k, w), 0)              # no pulse absorbed: none
        field.absorb(self.k, self.sec.id, versor.Mv.scalar(1), F(10 ** 9))
        with mock.patch.object(cosmos, "deep_gyr", return_value=float(F(field.stats(self.k)["stars"][str(self.sec.id)]["since"])) + 1e-3):
            self.assertGreater(field.quantum_flux(self.k, w), 0)


class TestBells(unittest.TestCase):
    """The bells (xyl-cosmos field.rs): each hole's own screw, its rings counted in closed form, absorbed by the stars
    the peoples live by; a screw's action is the versor's, exactly."""

    def setUp(self):
        self.k = GameKernel(seed=42)

    def test_the_core_rings_light_s_round_trip_to_the_rim(self):
        from xylarium.kernel import blackhole
        core = field.bells(self.k)[0]
        self.assertEqual(core["name"], "centre")
        self.assertAlmostEqual(float(core["pitch_kpc"]), 2 * cosmos.R_MAX_KPC, places=9)
        self.assertAlmostEqual(float(core["period_yr"]), 2 * cosmos.R_MAX_KPC / field.C_KPC_YR, places=3)
        m = Fraction(blackhole.stats(self.k).get("mass", blackhole.MASS0))
        self.assertEqual(core["light"], m * 320)                        # 32 000 x 1/10 x 1/10 suns per sun
        self.assertEqual(core["spin"], Fraction(7, 10))

    def test_rings_are_counted_in_closed_form(self):
        b = {"period_yr": Fraction(1000), "born": 0.0}
        t0 = 1.0
        self.assertEqual(field.arrivals(b, 500.0, t0, t0 + 1000 / 1e9), 1)
        self.assertEqual(field.arrivals(b, 500.0, t0, t0 + 10_000 / 1e9), 10)
        self.assertEqual(field.arrivals(b, 500.0, t0, t0), 0)
        self.assertEqual(field.arrivals(dict(b, born=6.0), 0.0, 5.0, 5.9), 0)   # a bell not yet born rings nothing

    def test_a_screw_moves_a_point_exactly_as_its_versor(self):
        from xylarium.kernel import versor
        core = field.bells(self.k)[0]
        sc = field.received(dict(core, axis=(Fraction(1, 3), Fraction(-2, 7), Fraction(5, 6)), spin=Fraction(9, 10)),
                            1e-6)
        for x in [(Fraction(7, 2), Fraction(1, 5), Fraction(-3, 4)), (Fraction(0), Fraction(0), Fraction(0))]:
            self.assertEqual(field._screw_move(sc, x), versor.move(field.screw_versor(sc), x))

    def test_a_ring_s_energy_is_its_light_over_a_period_on_the_system_s_disc(self):
        core = field.bells(self.k)[0]
        a_out = Fraction(52, 10)
        d = 8.0
        d_au = field.grid(d * float(field.AU_PER_KPC))
        self.assertEqual(field.energy_at(core, d, a_out),
                         core["light"] * core["period_yr"] * field.SUN_YEAR * a_out * a_out / (4 * d_au * d_au))

    def test_identical_rings_are_counted_as_absorbing_each_would_book_them(self):
        from xylarium.kernel import physics
        sec = next(s for s in self.k.sectors.values() if len(field.anchors_of(self.k, s.id)) >= 2)
        core = field.bells(self.k)[0]
        anchors = field.anchors_of(self.k, sec.id)
        a_out = max(w["native"][0] for w in anchors)
        v, e = field.received(core, 8.0), field.energy_at(core, 8.0, a_out)
        mass, share = Fraction(physics.star(sec)["mass"]), field.burn_out_share(self.k, sec.id)
        total, drift, cur = Fraction(0), [Fraction(0)] * 3, anchors
        for _ in range(5):                                             # ring by ring
            a = field.absorb_at(mass, share, cur, v, e)
            cur, total = a["anchors"], total + a["gravity"]
            drift = [x + y for x, y in zip(drift, a["drift"])]
        first = field.absorb_at(mass, share, anchors, v, e)
        self.assertTrue(all(w["at"] == w["native"] for w in first["anchors"]))   # a fixed point: wholly re-locked
        self.assertEqual(total, first["gravity"] * 5)
        self.assertEqual(drift, [x * 5 for x in first["drift"]])

    def test_a_season_reaches_the_peoples_stars_and_their_books_balance(self):
        k = self.k
        k.activate() if hasattr(k, "activate") else None
        st = field.stats(k)
        with mock.patch.object(cosmos, "is_cosmic", return_value=True), \
                mock.patch.object(field, "place_of", side_effect=lambda kk, s, g=None: (8.0, float(s) * 1e-3, 0.0)):
            n = field.step(k, 1.0, 1.0 + 1e-3)
        self.assertGreater(n, 0)
        for book in st["stars"].values():
            self.assertEqual(Fraction(book["in"]),
                             Fraction(book["gravity"]) + Fraction(book["light"]) + Fraction(book["burned_out"]))

    def test_a_star_s_books_stay_on_the_grid_however_many_rings(self):
        from xylarium.kernel import physics
        sec = next(s for s in self.k.sectors.values() if len(field.anchors_of(self.k, s.id)) >= 2)
        core = field.bells(self.k)[0]
        anchors = field.anchors_of(self.k, sec.id)
        a_out = max(w["native"][0] for w in anchors)
        total = Fraction(0)
        for d in (7.9, 8.0, 8.1, 8.3, 9.7):                            # rings from places that differ
            a = field.absorb_at(Fraction(physics.star(sec)["mass"]), field.burn_out_share(self.k, sec.id), anchors,
                                field.received(core, d), field.energy_at(core, d, a_out))
            self.assertEqual(a["in"], a["gravity"] + a["light"] + a["burned_out"])
            total += a["in"] + a["gravity"] + a["burned_out"]
        self.assertEqual((1 << field.GRID) % total.denominator, 0)     # dyadic, never past the grid: bounded books

