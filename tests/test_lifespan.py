"""
A people is born, grows, ages and dies by its species' physics; its health resilience sets how many reach old age
and how many are born; its crowd diseases live on it by the same laws; its dead return to the world or warm it;
its eminent are named, mourned and in time forgotten; it turns over, and turning over is what changes its mind;
and it counts its age by three clocks.
"""

import math
import unittest

from xylarium.kernel import (clock, cosmos, culture, fertility, history, knowledge, lifespan, matter, staples,
                             syntropy)
from xylarium.kernel.engine import GameKernel


def _people():
    k = GameKernel(seed=7, genesis="cosmic")
    k.activate()
    p = next(p for p in k.sectors[1].planets if p.civilization)
    return k, p, knowledge.holder_of_planet(p)


class TestLifeHistory(unittest.TestCase):
    def test_spans_are_the_species_generation_and_earth_reads_true(self):
        # a K-strategist of Earth's pace: ~28-year generation, ~70-year life, longest ~120
        gen = fertility.generation_years("K", 1.0)
        self.assertAlmostEqual(gen * lifespan.LIFE_MEDIAN_GEN, 70, delta=2)
        self.assertAlmostEqual(gen * lifespan.LIFE_MAX_GEN, 120, delta=3)
        k, p, h = _people()
        e = lifespan.expectancy_years(k, p, health=1.0)
        self.assertGreater(e, fertility.generation_of(k, p) * lifespan.LIFE_MEDIAN_GEN - 1e-6)
        self.assertLess(lifespan.expectancy_years(k, p, health=0.5), e)               # ill health shortens it

    def test_a_people_ages_and_dies_and_turns_over(self):
        k, p, h = _people()
        for _ in range(40):
            k.cycle_count += 25
            lifespan.quarter(k)
        c = lifespan.cohorts(p)
        self.assertAlmostEqual(sum(c.values()), 1.0, places=3)
        self.assertGreater(lifespan.died(k, h), 0)
        self.assertGreater(p.society["life"]["ancestors"], 0)
        self.assertFalse(lifespan.turned_over(k, h, lifespan.died(k, h), p.population))
        self.assertTrue(lifespan.turned_over(k, h, lifespan.died(k, h) - p.population, p.population))


class TestHealth(unittest.TestCase):
    def test_thr_is_the_chance_to_reach_old_age_and_scales_fertility(self):
        k, p, h = _people()
        p.society["self_sufficiency"] = 1.0
        well = lifespan.thr(k, p)
        p.society["self_sufficiency"] = 0.5
        self.assertAlmostEqual(lifespan.thr(k, p), well * 0.5, places=6)
        p.society["life"] = {"thr": 0.5}
        f_sick, _ = fertility.fertility(k, p)
        p.society["life"] = {"thr": 1.0}
        f_well, _ = fertility.fertility(k, p)
        self.assertAlmostEqual(f_sick, f_well * 0.5, places=6)                         # TFR x THR

    def test_crowd_diseases_need_a_critical_community_and_grow_milder(self):
        k, p, h = _people()
        ccs = lifespan.critical_community(k, p)
        p.population = int(ccs * 0.5)
        self.assertEqual(lifespan.disease(k, p)["endemic"], 0.0)
        p.population = int(ccs * 4)
        d0 = lifespan.disease(k, p)
        self.assertEqual(d0["endemic"], 1.0)
        self.assertAlmostEqual(d0["cfr"], lifespan.CFR_VIRGIN)
        k.cycle_count += int(fertility.generation_of(k, p) * 100 * 2)
        self.assertLess(lifespan.disease(k, p)["cfr"], d0["cfr"] * 0.2)               # co-evolved toward mildness


class TestTheDead(unittest.TestCase):
    def test_the_dead_return_to_the_world_declared(self):
        k, p, h = _people()
        p.society["life"] = {}
        t0, n0 = matter.totals(k), k.matter.net()
        held = staples.held(p, staples.of(k, p))
        lifespan._bury(k, p, 100_000)
        self.assertGreater(staples.held(p, staples.of(k, p)), held)
        t1, n1 = matter.totals(k), k.matter.net()
        self.assertEqual({c: d for c in set(t1) | set(n1)
                          if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}, {})

    def test_what_a_people_believes_of_its_dead_decides_their_rest(self):
        k, p, h = _people()
        culture.stats(k)["peoples"][h] = {"stance": "sacred"}
        self.assertEqual(lifespan.practice(k, p), "rest")
        culture.stats(k)["peoples"][h] = {"stance": "silence"}
        self.assertIn(lifespan.practice(k, p), ("pyre", "return"))

    def test_the_eminent_are_named_mourned_and_forgotten(self):
        k, p, h = _people()
        history.event(k, "TURNING", "The test people turn toward growth", actors=[h], planet=p)
        lifespan.quarter(k)
        rec = lifespan.stats(k)["peoples"][h]
        self.assertTrue(any(f["role"] == "leader" for f in rec["eminent"]))
        fig = next(f for f in rec["eminent"] if f["role"] == "leader")
        k.cycle_count = fig["dies"] + 1
        lifespan.quarter(k)
        self.assertTrue(any(e["kind"] == "EPITAPH" for e in history.stats(k)["recent"]))
        self.assertIn(fig["name"], [f["name"] for f in lifespan.remembered(k, h)])
        for _ in range(400):                                            # generations pass
            k.cycle_count += 25 * 40
            lifespan._eminent(k, h, [p], rec)
        self.assertNotIn(fig["name"], [f["name"] for f in lifespan.remembered(k, h)])


class TestTurnover(unittest.TestCase):
    def test_knowledge_fades_with_its_knowers(self):
        k, p, h = _people()
        lifespan.stats(k)["peoples"][h] = {"expectancy": 20.0, "died": 0}
        short = knowledge.forgetting(k, h)
        lifespan.stats(k)["peoples"][h] = {"expectancy": 300.0, "died": 0}
        long_ = knowledge.forgetting(k, h)
        self.assertGreater(short, long_)
        lifespan.stats(k)["peoples"][h] = {"expectancy": knowledge.HUMAN_LIFE_YEARS, "died": 0}
        self.assertAlmostEqual(knowledge.forgetting(k, h), 0.15, places=6)            # Earth's measured rate

    def test_the_fork_is_weighed_again_when_the_people_has_replaced_itself(self):
        from unittest import mock
        from xylarium.kernel import sustenance
        k, p, h = _people()
        p.citadel_level = sustenance.DAUGHTER_CITADEL_TIER
        lifespan.stats(k)["peoples"][h] = {"died": 10.0}
        with mock.patch.object(syntropy, "room_in_reach", return_value=0):
            syntropy.fork(k, p)
        self.assertFalse(syntropy.due(k, p))
        lifespan.stats(k)["peoples"][h]["died"] = 10.0 + p.population
        self.assertTrue(syntropy.due(k, p))


class TestClocks(unittest.TestCase):
    def test_a_people_is_old_by_three_clocks(self):
        k, p, h = _people()
        k.cycle_count += 3000
        age = clock.age_of_people(k, p)
        self.assertAlmostEqual(age["years"], 30.0, places=1)
        self.assertAlmostEqual(age["local_years"], 3000 / float(clock.year_of(k, p)), places=1)
        self.assertAlmostEqual(age["galactic_myr"], 30.0 * cosmos.ruler(k) / 1e6, places=2)


if __name__ == "__main__":
    unittest.main()
