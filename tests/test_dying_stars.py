"""
Stars live and die by their physics: a giant branch that burns the fields and pours out light, then a white dwarf or
a Type Ia supernova. Peoples that know enough foresee it; governments with ships must carry their people away, and
answer for those they leave; the galactic centre recycles what dies within the bulge.
"""

import unittest

from xylarium.kernel import biosphere, blackhole, cosmos, exodus, history, knowledge, matter, sustenance
from xylarium.kernel.engine import GameKernel


def _undeclared(k, t0, n0):
    t1, n1 = matter.totals(k), k.matter.net()
    return {c: d for c in set(t0) | set(t1) | set(n1) if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}


class TestDyingStars(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.p = next(p for s in self.k.sectors.values() for p in s.planets if p.population > 0)
        self.sid = self.p.sector_id

    def _at(self, gyr):
        st = cosmos.stats(self.k)
        st["minds"] = []                                     # no new minds in this test: one star's story
        self.k.cycle_count = int((gyr - st["epoch0"]) * 1e9 / cosmos.ruler(self.k) * 100)

    def test_a_giant_burns_its_fields_and_pours_out_light(self):
        born, ends = cosmos.star_life(self.k, self.sid)
        k0 = biosphere.carrying_capacity(self.k, self.p)
        self._at(ends - 0.01 * (ends - born))
        cosmos.quarter(self.k)
        self.assertGreater(cosmos.lum(self.sid), 100.0)                               # near the giant branch tip
        self.assertLess(biosphere.carrying_capacity(self.k, self.p), k0 / 10)

    def test_a_government_with_ships_carries_its_people_and_one_without_them_is_mourned(self):
        p, k = self.p, self.k
        p.society["way"], p.citadel_level = "state", 3
        knowledge.learn(k, knowledge.holder_of_planet(p), "energy", 400)
        self.assertTrue(sustenance.yards(p))
        p.society["exodus_ordered"] = True
        born, ends = cosmos.star_life(k, self.sid)
        t0, n0 = matter.totals(k), k.matter.net()
        self._at(ends - 0.09 * (ends - born))
        cosmos.quarter(k)
        exodus.quarter(k)
        self.assertEqual(p.population, 0)
        self.assertGreater(exodus.summary(k)["moved"], 0)
        self._at(ends + 0.001)
        cosmos.quarter(k)
        self.assertEqual(k.sectors[self.sid].star_type, "White dwarf remnant")
        self.assertEqual(exodus.summary(k)["abandoned"], 0)
        self.assertEqual(_undeclared(k, t0, n0), {})

    def test_leaving_them_behind_is_harm(self):
        p, k = self.p, self.k
        p.society["way"], p.citadel_level = "state", 3
        knowledge.learn(k, knowledge.holder_of_planet(p), "energy", 400)
        p.society["evac_could"], p.society["evac_moved"] = 10 ** 6, 0          # it could have, and did not
        a0 = float(getattr(p.civilization, "alignment", 0.0) or 0.0)
        exodus.perished(k, p, p.population, "white_dwarf")
        self.assertGreater(exodus.summary(k)["abandoned"], 0)
        kinds = [e["kind"] for e in history.stats(k)["recent"]]
        self.assertIn("ABANDONED", kinds)

    def test_the_centre_recycles_what_dies_in_the_bulge(self):
        k = self.k
        t0, n0 = matter.totals(k), k.matter.net()
        blackhole.capture(k, {"Fe": 300}, "a test star", made=True)
        blackhole.quarter(k)
        self.assertGreater(blackhole.luminosity(k), 1e5)                              # it shines as it feeds
        self.assertEqual(_undeclared(k, t0, n0), {})


if __name__ == "__main__":
    unittest.main()
