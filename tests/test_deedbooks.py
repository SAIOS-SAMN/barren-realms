"""
The five deed books a steward reads beside a petition: each a PAIR from receipted deeds (syntropic against entropic,
read whole), in deficit only where its entropic side exceeds its syntropic side - never a ratio, never a gate.
"""

import unittest
from fractions import Fraction
from types import SimpleNamespace
from unittest import mock

from xylarium.kernel import crystal as C
from xylarium.kernel import deedbooks
from xylarium.kernel.engine import GameKernel


def _k():
    k = GameKernel(seed=42)
    k.activate()
    return k


class TestPairs(unittest.TestCase):
    def test_a_pair_is_in_deficit_only_when_its_entropic_side_is_larger(self):
        self.assertFalse(deedbooks._pair(3, 2)["deficit"])
        self.assertTrue(deedbooks._pair(2, 3)["deficit"])
        self.assertFalse(deedbooks._pair(0, 0)["deficit"])
        self.assertEqual(deedbooks._pair(Fraction(1, 3), 0)["syntropic"], "1/3")       # exact, its own unit


class TestCoherence(unittest.TestCase):
    def test_deeds_are_read_against_the_doctrine_the_people_tells(self):
        k = _k()
        deeds = {a: (Fraction(0), Fraction(0)) for a in deedbooks.AXES}
        deeds["compassion"] = (Fraction(1), Fraction(5))                 # it made war five times, kept peace once
        civ = SimpleNamespace()
        with mock.patch.object(deedbooks, "_deeds", lambda kernel, who: deeds), \
                mock.patch.object(deedbooks, "_home", lambda kernel, who: SimpleNamespace(civilization=civ)):
            with mock.patch("xylarium.kernel.alignment.doctrine", lambda c: 0.5):        # tells the Light
                self.assertTrue(deedbooks.coherence(k, "civ:A")["compassion"]["deficit"])
            with mock.patch("xylarium.kernel.alignment.doctrine", lambda c: -0.5):       # tells the Dark
                self.assertFalse(deedbooks.coherence(k, "civ:A")["compassion"]["deficit"])


class TestGrasp(unittest.TestCase):
    def test_grasp_is_what_it_shares_against_what_it_lacks_of_the_others_group(self):
        k = _k()
        vocab = {"civ:A": [C.ROT90], "civ:B": [C.ROT90, C.FLIPH, C.FLIP_STACK]}
        with mock.patch("xylarium.kernel.intellect.vocabulary", lambda kernel, who: vocab[who]):
            g = deedbooks.grasp(k, "civ:A", ["civ:B"])
        self.assertFalse(g["two_way_time"])                              # it cannot read the stack backwards
        pair = g["of"]["civ:B"]
        ga, gb = deedbooks.group(vocab["civ:A"]), deedbooks.group(vocab["civ:B"])
        self.assertEqual((int(pair["syntropic"]), int(pair["entropic"])), (len(ga & gb), len(gb - ga)))
        self.assertTrue(pair["deficit"])                                # B's order is wider than A can follow
        self.assertEqual(len(ga), 4)                                    # the quarter turns alone: C4
        self.assertEqual(len(gb), 8 * 2)                                # D4 x a stack read both ways


class TestFutility(unittest.TestCase):
    def test_war_deaths_book_as_want_or_appetite_by_what_its_reach_held(self):
        k = _k()
        home = SimpleNamespace(population=1000, element_deposits={"ORGANICS": 10 ** 9}, element_reserves={},
                               ore_silo=0, organics_silo=0)
        bk = {"units": {"ORGANICS": Fraction(1, 10)}}
        with mock.patch("xylarium.kernel.encircle.deaths", lambda kernel: {"civ:A": {"war:encirclement": 40}}), \
                mock.patch("xylarium.kernel.relations._peoples", lambda kernel: {"civ:A": [home]}), \
                mock.patch("xylarium.kernel.backing.basket", lambda kernel, who: bk):
            out = deedbooks.futility(k, "civ:A")
        self.assertEqual((out["syntropic"], out["entropic"]), ("0", "40"))   # it held plenty: a war of appetite
        self.assertTrue(out["deficit"])


class TestReading(unittest.TestCase):
    def test_the_reading_holds_every_book_and_the_strategy_beside_them(self):
        k = _k()
        from xylarium.kernel import relations
        who = sorted(relations._peoples(k))[0]
        r = deedbooks.read(k, who, [])
        for b in ("coherence", "loop", "grasp", "awareness", "expansion", "futility", "strategy"):
            self.assertIn(b, r)
        self.assertIn("syntropic", r["awareness"])                      # pairs, never a single score


if __name__ == "__main__":
    unittest.main()
