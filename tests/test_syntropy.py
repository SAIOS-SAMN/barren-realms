"""
The population-technology saddle: every people's syntropy (capacity, knowledge, worlds) is measured and its slope
read; a direction held for a generation is a turning in its history; and the fork off a crowded world - outward or
enough - is the council's own priced choice, weighed again each generation.
"""

import unittest
from unittest import mock

from xylarium.kernel import cosmos, demography, history, knowledge, sustenance, syntropy
from xylarium.kernel.engine import GameKernel


def _people():
    k = GameKernel(seed=7, genesis="cosmic")
    k.activate()
    p = next(p for p in k.sectors[1].planets if p.civilization)
    return k, p, knowledge.holder_of_planet(p)


class TestIndex(unittest.TestCase):
    def test_the_index_rises_with_capacity_knowledge_and_worlds(self):
        k, p, h = _people()
        a = syntropy.index(k, h, [p])
        knowledge.learn(k, h, "biology", 50.0)
        b = syntropy.index(k, h, [p])
        self.assertGreater(b["S"], a["S"])
        self.assertAlmostEqual(a["crowding"], p.population / a["K"])

    def test_a_direction_held_for_a_generation_is_a_turning(self):
        from xylarium.kernel import fertility
        k, p, h = _people()
        syntropy.quarter(k)
        gen_cycles = int(fertility.generation_of(k, p) * 100)
        step = 100
        for i in range(gen_cycles // step + 3):
            k.cycle_count += step
            knowledge.learn(k, h, "information", 5.0)               # it keeps learning: syntropic
            syntropy.quarter(k)
        self.assertGreater(syntropy.reading(k, h)["slope"], 0)
        turnings = [e for e in history.stats(k)["recent"] if e["kind"] == "TURNING"]
        self.assertTrue(turnings and "growth" in turnings[-1]["title"])


class TestFork(unittest.TestCase):
    def test_room_in_reach_draws_outward_and_none_draws_enough(self):
        k, p, h = _people()
        p.citadel_level = sustenance.DAUGHTER_CITADEL_TIER
        with mock.patch.object(syntropy, "room_in_reach", return_value=0):
            self.assertEqual(syntropy.fork(k, p), "steady")
        with mock.patch.object(syntropy, "room_in_reach", return_value=10 ** 7), \
                mock.patch.object(demography, "value_of_room", return_value=10 ** 9):
            self.assertEqual(syntropy.fork(k, p), "expand")
        self.assertEqual(p.society["fork"]["choice"], "expand")

    def test_no_covenant_is_forever(self):
        from xylarium.kernel import fertility
        k, p, h = _people()
        p.citadel_level = sustenance.DAUGHTER_CITADEL_TIER
        with mock.patch.object(syntropy, "room_in_reach", return_value=0):
            syntropy.fork(k, p)
        self.assertFalse(syntropy.due(k, p))
        k.cycle_count += int(fertility.generation_of(k, p) * 100) + 1
        self.assertTrue(syntropy.due(k, p))
        p.growth_policy = "steady"
        p.population = demography.housing_cap(p, k)                                     # crowded again
        with mock.patch.object(syntropy, "room_in_reach", return_value=10 ** 7), \
                mock.patch.object(demography, "value_of_room", return_value=10 ** 9):
            demography.develop(k, p)
        self.assertEqual(p.growth_policy, "expand")                                   # weighed again, outward


if __name__ == "__main__":
    unittest.main()
