"""
The galaxy: inside-out star formation, elements sorted by mass (heavy near the core, light furthest), closed-form
galactic clockwork, minds arising from chemistry and biology by hard steps in their own years, a map materialised
only where minds and their reach witness it - and a history ledger that keeps all of it.
"""

import json
import os
import tempfile
import unittest

from xylarium.kernel import cosmos, history
from xylarium.kernel.engine import GameKernel


class TestGalaxyLaws(unittest.TestCase):
    def test_heavy_elements_stay_near_the_core_and_light_ones_reach_furthest(self):
        self.assertLess(cosmos.scatter_length("U"), cosmos.scatter_length("Fe"))
        self.assertLess(cosmos.scatter_length("Fe"), cosmos.scatter_length("C"))
        self.assertLess(cosmos.scatter_length("C"), cosmos.scatter_length("H"))
        self.assertAlmostEqual(cosmos.abundance("Fe", cosmos.R0_KPC), 1.0)
        self.assertGreater(cosmos.abundance("U", 2.0), cosmos.abundance("Fe", 2.0))      # the core is rich in heavies
        self.assertLess(cosmos.abundance("U", 14.0), cosmos.abundance("H", 14.0))        # the rim keeps the light
        # iron's gradient is the measured one: -0.06 dex per kpc
        import math
        self.assertAlmostEqual(math.log10(cosmos.abundance("Fe", 9.0)), -0.06 * 56.0 / 55.8, places=3)

    def test_inside_out_and_the_habitable_zone(self):
        self.assertLess(cosmos.formed_gyr(2.0), cosmos.formed_gyr(10.0))
        self.assertLess(cosmos.survival(1.0), cosmos.survival(8.0))                      # the core is deadly
        self.assertLess(cosmos.metals(14.0), cosmos.metals(8.0))                         # the rim is metal-poor

    def test_the_galaxy_turns_like_clockwork(self):
        self.assertAlmostEqual(cosmos.omega(4.0), 2 * cosmos.omega(8.0))                # a flat rotation curve
        period_myr = 2 * 3.141592653589793 / cosmos.omega(cosmos.R0_KPC)
        self.assertTrue(200 < period_myr < 250)                                          # the galactic year at R0

    def test_cells_tile_the_disc_and_touch_their_neighbours(self):
        cs = cosmos.cells()
        self.assertEqual(len(cs), len(set(cs)))
        for c in [(0, 0), (5, 3), (12, 40)]:
            for nb in cosmos.neighbours(*c):
                self.assertIn(c, cosmos.neighbours(*nb))


class TestShear(unittest.TestCase):
    def test_cells_on_neighbouring_rings_slide_apart(self):
        a = (15, 10)
        b = next(n for n in cosmos.neighbours(*a) if n[0] == 16 and cosmos.overlap(a, n, 0.0) > 0.5)
        self.assertGreater(cosmos.overlap(a, b, 0.0), 0)
        self.assertEqual(cosmos.overlap(a, b, 200.0), 0.0)                              # a few galactic years on
        later = [n for n in [(16, j) for j in range(cosmos.slots(16))] if cosmos.overlap(a, n, 200.0) > 0]
        self.assertTrue(later and b not in later)                                       # new neighbours face it

    def test_lanes_open_and_close_with_the_shear_and_stretch_between(self):
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        home = tuple(int(x) for x in cosmos.stats(k)["materialised"][0].split(","))
        cosmos.entered(k, 1)                                                            # see the cells around it
        across = [c for c in (tuple(int(x) for x in key.split(",")) for key in cosmos.stats(k)["materialised"])
                  if c[0] != home[0]]
        self.assertTrue(across)
        self.assertTrue(cosmos.stats(k)["cross"])
        lanes0 = dict(cosmos.stats(k)["cross"])
        k.cycle_count += 100 * 400                                                       # 400 clock years of shear
        cosmos._shear(k)
        self.assertNotEqual(lanes0, dict(cosmos.stats(k)["cross"]))
        for key, f in cosmos.stats(k)["stretch"].items():
            self.assertGreaterEqual(f, 1.0)


class TestPaceAndStars(unittest.TestCase):
    def test_the_pace_is_a_law_of_the_universe(self):
        gaps = {}
        for pace in ("lonely", "neighbourly", "teeming"):
            k = GameKernel(seed=7, genesis=f"cosmic:{pace}")
            self.assertEqual(cosmos.pace(k), pace)
            m = cosmos.stats(k)["minds"]
            gaps[pace] = (m[1]["epoch"] - m[0]["epoch"]) * 1e9 / cosmos.ruler(k)
        self.assertAlmostEqual(gaps["lonely"], 10 * gaps["neighbourly"], places=3)
        self.assertAlmostEqual(gaps["neighbourly"], 10 * gaps["teeming"], places=3)

    def test_stars_age_and_die_and_their_worlds_feed_no_one(self):
        from xylarium.kernel import biosphere
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        sid, life = next((s.id, cosmos.star_life(k, s.id)) for s in k.sectors.values()
                         if s.planets and cosmos.star_life(k, s.id) and cosmos.star_life(k, s.id)[1] > cosmos.deep_gyr(k))
        born, ends = life
        self.assertEqual(cosmos.star_factor(k, sid, born + 0.5 * (ends - born)), 1.0)
        self.assertAlmostEqual(cosmos.star_factor(k, sid, ends - 0.05 * (ends - born)), 0.5, places=6)
        self.assertEqual(cosmos.star_factor(k, sid, ends + 0.01), 0.0)
        p = k.sectors[sid].planets[0]
        p.society["star_k"] = 0.0
        self.assertEqual(biosphere.carrying_capacity(k, p), 0)


class TestMindsArise(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = GameKernel(seed=7, genesis="cosmic")
        cls.k.activate()

    def test_the_clock_starts_with_the_first_mind_and_nothing_else_is_placed(self):
        peoples = [p for s in self.k.sectors.values() for p in s.planets if p.population > 0]
        self.assertEqual(len(peoples), 1)
        self.assertEqual(peoples[0].society.get("way"), "forage")
        self.assertFalse(any(p.natives for s in self.k.sectors.values() for p in s.planets))
        st = cosmos.stats(self.k)
        self.assertAlmostEqual(cosmos.deep_gyr(self.k), st["epoch0"])
        self.assertEqual(len(self.k.sectors), 100)                                       # only the first witness's region

    def test_scales_are_audited_against_expectation(self):
        a = cosmos.audit(self.k)
        self.assertEqual(a["minds_arisen"], 1)
        self.assertLess(a["cells_charted"], a["cells_in_galaxy"] / 100)
        self.assertGreater(a["minds_by_present_universe"], a["minds_expected_by_now"])

    def test_the_schedule_is_the_seeds(self):
        again = cosmos.schedule(self.k)["minds"][:5]
        self.assertEqual(again, cosmos.stats(self.k)["minds"][:5])

    def test_a_later_mind_arises_in_its_own_year_and_witnesses_its_region(self):
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        nxt = cosmos.stats(k)["minds"][1]
        years = (nxt["epoch"] - cosmos.stats(k)["epoch0"]) * 1e9 / cosmos.ruler(k)
        k.cycle_count = int(years * 100) + 1
        lines = cosmos.quarter(k)
        self.assertTrue(any("A mind arises" in l for l in lines))
        self.assertEqual(cosmos.stats(k)["arisen"], 2)
        self.assertGreater(len(k.sectors), 100)


class TestHistoryLedger(unittest.TestCase):
    def test_every_event_is_kept_with_place_and_time_and_streamed(self):
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        path = os.path.join(tempfile.mkdtemp(), "h.jsonl")
        history.sink(k, path)
        with open(path) as f:
            first = [json.loads(l) for l in f]
        self.assertTrue(any(e["kind"] == "EMERGENCE" for e in first))                   # genesis is in the file
        emerged = next(e for e in first if e["kind"] == "EMERGENCE")
        self.assertIn("galactic", emerged)
        self.assertIn("deep_gyr", emerged)
        p = next(p for s in k.sectors.values() for p in s.planets if p.population > 0)
        history.event(k, "WAR", "a test war", actors=["civ:A", "civ:B"], planet=p, magnitude=5)
        with open(path) as f:
            self.assertEqual(json.loads(f.readlines()[-1])["title"], "a test war")

    def test_myths_compound_and_remember(self):
        from xylarium.kernel import knowledge, society
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        p = next(p for s in k.sectors.values() for p in s.planets if p.population > 0)
        holder = knowledge.holder_of_planet(p)
        war = history.event(k, "WAR", "the old war", actors=[holder, "civ:Other"], planet=p, magnitude=10 ** 7,
                            cause="hunger: ORGANICS")
        p.society["famine_cycle"] = k.cycle_count
        society.quarter(k)                                       # a first famine: a myth
        k.cycle_count += 100 * 200                               # generations later
        society._legends(k, p, 25.0)                             # the war becomes a legend, built on the myth
        myths = p.society["myths"]
        legend = myths[-1]
        self.assertTrue(legend["kind"].startswith("legend:war"))
        self.assertEqual(legend["remembers"], war["id"])
        self.assertEqual(legend["builds_on"], myths[-2]["id"])
        self.assertIn("as it was when", legend["text"])


if __name__ == "__main__":
    unittest.main()
