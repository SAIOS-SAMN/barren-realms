"""
The physics layer: exact stars and orbits, non-crossing spacing, light, rotation and the clock.
"""

import os
import tempfile
import unittest
from fractions import Fraction as F

from xylarium.kernel import physics
from xylarium.kernel.engine import GameKernel
from xylarium.persistence.store import StatePersistence


def systems(kernel):
    return [s for s in kernel.sectors.values() if s.kind == "SYSTEM"]


class TestCelestialLaws(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernels = [GameKernel(seed=s) for s in (3, 7, 42, 1337)]

    def test_terra_defines_the_units(self):
        k = self.kernels[0]
        sol, terra = k.sectors[1], k.sectors[1].planets[0]
        self.assertEqual(physics.year_cycles(sol, terra), F(physics.CYCLES_PER_STANDARD_YEAR))
        self.assertEqual(physics.planet_flux(sol, terra), 1)
        self.assertEqual(terra.orbital_period, 100)

    def test_kepler_third_law_holds_exactly(self):
        for k in self.kernels:
            for sec in systems(k):
                st = physics.star(sec)
                for p in sec.planets:
                    b = physics.body(p)
                    a = b["q"] ** 2
                    t = physics.period_years(st, b["q"])
                    self.assertEqual(t * t * st["mass"], a ** 3, p.id)       # T^2 M = a^3, exactly

    def test_orbits_never_cross(self):
        for k in self.kernels:
            for sec in systems(k):
                self.assertTrue(physics.spacing_ok(sec), f"seed {k.seed} sector {sec.id}")

    def test_light_falls_off_outward_and_sets_the_climate(self):
        for k in self.kernels:
            for sec in systems(k):
                worlds = sorted((p for p in sec.planets if not physics.body(p).get("parent")),
                                key=lambda p: physics.body(p)["q"])
                fluxes = [physics.planet_flux(sec, p) for p in worlds]
                self.assertEqual(fluxes, sorted(fluxes, reverse=True))
                for p, fl in zip(worlds, fluxes):
                    if p.planet_type in ("TERRESTRIAL", "OCEANIC"):
                        self.assertTrue(F(1, 4) <= fl <= 3, f"{p.id} {p.planet_type} under flux {fl}")

    def test_locked_worlds_have_a_day_as_long_as_their_year(self):
        for k in self.kernels:
            for sec in systems(k):
                for p in sec.planets:
                    b = physics.body(p)
                    if b.get("locked") and not b.get("parent"):
                        self.assertEqual(b["day"], physics.period_years(physics.star(sec), b["q"]) * 365)

    def test_generation_is_deterministic(self):
        a, b = GameKernel(seed=99), GameKernel(seed=99)
        bodies = lambda k: [(p.id, p.body, p.planet_type) for s in systems(k) for p in s.planets]
        self.assertEqual(bodies(a), bodies(b))


class TestTheClock(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=7)

    def test_terra_turns_a_full_year_in_one_hundred_cycles(self):
        sol, terra = self.kernel.sectors[1], self.kernel.sectors[1].planets[0]
        self.assertEqual(physics.orbital_phase(sol, terra, 0), physics.orbital_phase(sol, terra, 100))
        cal = physics.local_calendar(sol, terra, 150)
        self.assertEqual((cal["year"], cal["season"]), (1, 2))
        self.assertEqual(cal["local_days_per_year"], 365)

    def test_the_sky_follows_the_exact_phase(self):
        for _ in range(30):
            self.kernel.tick_simulation()
        for sec in systems(self.kernel):
            for p in sec.planets:
                expect = float(physics.orbital_phase(sec, p, self.kernel.astronomy_manager.cycle_count)) * 360.0
                # exact wherever it is read: computed when seen, not redrawn each cycle for unwatched skies
                self.assertAlmostEqual(self.kernel.astronomy_manager.angle_now(p), expect, places=6)


class TestPersistence(unittest.TestCase):
    def test_bodies_survive_save_and_legacy_saves_are_given_physics(self):
        k = GameKernel(seed=11)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "s.json")
            self.assertTrue(StatePersistence.save_to_file(k, path))
            loaded = StatePersistence.load_from_file(path)
            for sid, sec in k.sectors.items():
                self.assertEqual([p.body for p in sec.planets], [p.body for p in loaded.sectors[sid].planets])
            # a universe saved before physics: strip every body and star, reload, and they are derived
            for sec in k.sectors.values():
                sec.star = None
                for p in sec.planets:
                    p.body = None
            self.assertTrue(StatePersistence.save_to_file(k, path))
            legacy = StatePersistence.load_from_file(path)
        for sec in systems(legacy):
            self.assertIsNotNone(sec.star)
            self.assertTrue(physics.spacing_ok(sec))
            for p in sec.planets:
                self.assertIsNotNone(p.body)


if __name__ == "__main__":
    unittest.main()
