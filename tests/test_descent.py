"""Descent: who came from whom, who can still breed, what an edit must bridge - and plasticity slowing a line."""

import math
import random
import unittest
from unittest import mock

from xylarium.kernel import descent, genome, knowledge
from xylarium.kernel.engine import GameKernel


def fresh(rseed=11):
    random.seed(rseed)
    k = GameKernel(seed=7)
    k.activate()
    return k


def civ_worlds(k):
    return [p for s in k.sectors.values() for p in s.planets
            if p.population > 0 and p.civilization is not None and p.owner_id is None and not p.natives]


def _daughter(k):
    """A world of the home people's that drifts far enough to become another people (genome.speciate)."""
    home = civ_worlds(k)[0]
    w = next(p for s in k.sectors.values() for p in s.planets
             if p.population <= 0 and p.owner_id is None and not p.natives and p.civilization is None)
    w.civilization, w.population = home.civilization, 2000
    parent = knowledge.holder_of_planet(home)
    genome.of(home)
    genome.of(w)["temperature"] = 5.0
    genome.quarter(k)
    return parent, knowledge.holder_of_planet(w), home, w


class TestLines(unittest.TestCase):
    def test_a_people_that_woke_on_its_own_world_is_its_own_root(self):
        k = fresh()
        who = knowledge.holder_of_planet(civ_worlds(k)[0])
        self.assertEqual(descent.line(k, who)["root"], who)
        self.assertIsNone(descent.line(k, who)["parent"])

    def test_a_people_split_from_another_keeps_its_root_and_chemistry(self):
        k = fresh()
        parent, child, _, _ = _daughter(k)
        self.assertNotEqual(parent, child)
        rec = descent.line(k, child)
        self.assertEqual(rec["root"], descent.line(k, parent)["root"])
        self.assertEqual(rec["parent"], parent)
        self.assertEqual(rec["chemistry"], descent.line(k, parent)["chemistry"])


class TestKinship(unittest.TestCase):
    def test_kin_breed_less_as_they_drift_apart(self):
        k = fresh()
        parent, child, home, w = _daughter(k)
        rel = descent.kinship(k, parent, child)
        self.assertEqual(rel["relation"], "kin")
        self.assertAlmostEqual(rel["viability"], math.exp(-(rel["distance"] / genome.SPECIATION_SD) ** 2))
        genome.of(w)["temperature"] = 9.0                       # further still
        self.assertLess(descent.kinship(k, parent, child)["viability"], rel["viability"])

    def test_another_chemistry_is_alien_and_nothing_bridges_it(self):
        k = fresh()
        a = knowledge.holder_of_planet(civ_worlds(k)[0])
        descent.stats(k)["of"]["civ:Other"] = {"root": "civ:Other", "parent": None, "split": None,
                                              "chemistry": "plasmic" if descent.line(k, a)["chemistry"] != "plasmic"
                                              else "biotic"}
        self.assertEqual(descent.kinship(k, a, "civ:Other")["relation"], "alien")
        with mock.patch.object(knowledge, "mastery", return_value=1.0):
            self.assertIsNone(descent.bridge(k, a, a, "civ:Other"))

    def test_separate_roots_of_one_chemistry_need_an_edit_to_breed(self):
        k = fresh()
        a = knowledge.holder_of_planet(civ_worlds(k)[0])
        chem = descent.line(k, a)["chemistry"]
        descent.stats(k)["of"]["civ:Other"] = {"root": "civ:Other", "parent": None, "split": None, "chemistry": chem}
        with mock.patch.object(descent, "_body_distance", return_value=4.0):
            rel = descent.kinship(k, a, "civ:Other")
            self.assertEqual((rel["relation"], rel["viability"]), ("unrelated", 0.0))
            self.assertIsNone(descent.bridge(k, a, a, "civ:Other"))              # it cannot edit genomes yet
            with mock.patch.object(knowledge, "mastery", return_value=1.0), \
                    mock.patch.object(knowledge, "cost_multiplier", return_value=1.0):
                near = descent.bridge(k, a, a, "civ:Other")["cost"]
            with mock.patch.object(descent, "_body_distance", return_value=8.0), \
                    mock.patch.object(knowledge, "mastery", return_value=1.0), \
                    mock.patch.object(knowledge, "cost_multiplier", return_value=1.0):
                far = descent.bridge(k, a, a, "civ:Other")["cost"]
        self.assertGreater(far, near)


class TestPlasticity(unittest.TestCase):
    def test_a_plastic_people_is_pulled_more_slowly_toward_its_light(self):
        k = fresh()
        w = civ_worlds(k)[0]
        x0 = genome._flux_ratio(k, w)
        if x0 is None:
            self.skipTest("plasmic world")
        moved = {}
        for shield in (1.0, 4.0):
            genome.of(w)["light"] = math.log(x0) - 1.0
            with mock.patch.object(genome, "plasticity", return_value=shield), \
                    mock.patch.object(genome, "_rng", return_value=random.Random(0)):
                genome.evolve(k, w)
            moved[shield] = genome.of(w)["light"] - (math.log(x0) - 1.0)
        self.assertGreater(abs(moved[1.0]), abs(moved[4.0]))

    def test_a_shielded_sea_is_not_plastic(self):
        k = fresh()
        w = civ_worlds(k)[0]
        self.assertGreaterEqual(genome.plasticity(k, w), 1.0)


if __name__ == "__main__":
    unittest.main()
