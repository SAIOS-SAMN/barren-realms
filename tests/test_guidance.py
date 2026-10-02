"""
Elder peoples choose what they do for younger ones (teach, seed, nothing) - weighed by their own minds and how much
they value strangers' lives; the universe is a closed 3-sphere of clusters whose signals cross expanding space; and
every species eats by what its body burns.
"""

import math
import unittest

from xylarium.kernel import (biosphere, contact, cosmos, creation, culture, exodus, guidance, knowledge, sphere,
                             sustenance)
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.market import FISCAL_QUARTER_CYCLES


def _two_peoples():
    k = GameKernel(seed=7, genesis="cosmic")
    k.activate()
    st = cosmos.stats(k)
    m = creation.schedule(7)["minds"][1]
    k.cycle_count = int((m["epoch"] - st["epoch0"]) * 1e9 / cosmos.ruler(k) * 100) + 1
    cosmos._due(k)
    a, b = [p for s in k.sectors.values() for p in s.planets if p.civilization][:2]
    ha, hb = exodus._holder(a), exodus._holder(b)
    a.citadel_level = sustenance.DAUGHTER_CITADEL_TIER
    culture.stats(k)["linked"] = [ha]
    for d in knowledge.DOMAINS:
        knowledge.stocks(k, ha)[d] = 50.0
    contact.stats(k)["familiarity"][contact._key(ha, hb)] = 0.9
    cosmos.entered(k, a.sector_id)
    k.cycle_count = (k.cycle_count // (4 * FISCAL_QUARTER_CYCLES) + 1) * 4 * FISCAL_QUARTER_CYCLES
    return k, a, b, ha, hb


class TestGuidance(unittest.TestCase):
    def test_a_people_of_the_light_teaches_when_it_is_worth_it_and_one_of_the_dark_never(self):
        from unittest import mock
        k, a, b, ha, hb = _two_peoples()
        b.population = 10 ** 7                                   # many lives to lift
        with mock.patch.object(contact, "intelligibility", return_value=1.0):
            a.civilization.alignment = -0.5
            self.assertEqual(guidance.quarter(k), [])
            self.assertEqual(sum(knowledge.stocks(k, hb).values()), 0.0)
            a.civilization.alignment = 0.9
            logs = guidance.quarter(k)
        self.assertTrue(any("teach" in l for l in logs), logs)
        self.assertGreater(sum(knowledge.stocks(k, hb).values()), 0.0)
        self.assertGreater(a.civilization.alignment, 0.9)                                 # help, toward the Light
        self.assertEqual(guidance.stats(k)["uplifts"], 1)

    def test_what_is_taught_is_bounded_by_understanding(self):
        k, a, b, ha, hb = _two_peoples()
        lesson = guidance.teaching(k, ha, hb)
        u = contact.intelligibility(k, ha, hb)
        for d in knowledge.DOMAINS:
            self.assertAlmostEqual(lesson[d], 50.0 * u)


class TestClosedUniverse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = GameKernel(seed=7, genesis="cosmic")
        cls.k.activate()

    def test_clusters_lie_outward_on_the_sphere_and_distance_wraps(self):
        st = sphere.stats(self.k)
        cs = st["clusters"]
        self.assertEqual(len(cs), sphere.NEAREST)
        self.assertEqual([c["chi_mpc"] for c in cs], sorted(c["chi_mpc"] for c in cs))
        home = [1.0, 0.0, 0.0, 0.0]
        self.assertAlmostEqual(sphere.distance(self.k, home, cs[3]["point"]), cs[3]["chi_mpc"], delta=0.05)
        antipode = [-1.0, 0.0, 0.0, 0.0]
        self.assertAlmostEqual(sphere.distance(self.k, home, antipode), math.pi * st["radius_mpc"], delta=1.0)
        self.assertAlmostEqual(st["circumference_mpc"], 2 * math.pi * st["radius_mpc"], delta=1.0)

    def test_light_crosses_expanding_space_and_far_light_never_arrives(self):
        t = sphere.arrival(5.0, 100.0)
        self.assertGreater(t, 5.0)
        self.assertLess(t, sphere.arrival(5.0, 1000.0))
        self.assertIsNone(sphere.arrival(13.8, sphere.event_horizon_mpc(13.8) * 1.01))
        self.assertIsNotNone(sphere.arrival(13.8, sphere.event_horizon_mpc(13.8) * 0.99))
        self.assertGreater(sphere.proper_mpc(self.k, 10.0, 13.8), sphere.proper_mpc(self.k, 10.0, 5.0))


class TestMetabolism(unittest.TestCase):
    def test_need_is_bound_to_the_homeworld_and_its_star(self):
        f = biosphere.metabolic_factor
        self.assertGreater(f("biotic", "K", home_gravity=0.5), f("biotic", "K", home_gravity=2.0))  # square-cube
        self.assertAlmostEqual(f("biotic", "K", home_gravity=0.5) / f("biotic", "K", home_gravity=1.0),
                               0.5 ** -2.25, places=3)                                  # M ~ g^-3, B ~ M^(3/4)
        self.assertGreater(f("biotic", "K", home_flux=4.0), f("biotic", "K", home_flux=0.25))     # a brighter sun
        self.assertEqual(f("plasmic", "K", home_gravity=0.5), f("plasmic", "K", home_gravity=2.0))  # no frame

    def test_need_follows_body_and_chemistry_and_the_land_divides_its_yield(self):
        self.assertAlmostEqual(biosphere.metabolic_factor("biotic", "K"), 1.0, places=2)
        self.assertLess(biosphere.metabolic_factor("biotic", "r"), 0.2)                   # small bodies eat little
        self.assertGreater(biosphere.metabolic_factor("plasmic", "plasmic"), 1.0)          # hot chemistry burns fast
        self.assertLess(biosphere.metabolic_factor("umbral", "K"), 1.0)                     # cold, slow
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        p = next(p for p in k.sectors[1].planets if p.civilization)
        cap = biosphere.carrying_capacity(k, p)
        f = biosphere.need_factor(p, k)
        yield_per_cycle = cap * f                                                           # Damuth: bodies x need
        p.civilization.clade = "ailuroform" if p.civilization.clade != "ailuroform" else "cnidiform"
        cap2 = biosphere.carrying_capacity(k, p)
        self.assertAlmostEqual(cap2 * biosphere.need_factor(p, k), yield_per_cycle, delta=yield_per_cycle * 0.01 + 2)


if __name__ == "__main__":
    unittest.main()
