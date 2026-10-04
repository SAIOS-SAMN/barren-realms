"""
A people's alignment is read from its deeds: unbounded, faded as their telling fades, never pinned at an edge; peoples
are read against each other by their deeds; a relic mind comes to hold what its finders hold, and keeps its silence
when nothing is worth doing.
"""

import math
import random
import unittest

from xylarium.kernel import alignment, cohabit, decide, knowledge, memory, relics, technology
from xylarium.kernel.engine import GameKernel


def _civ(a=0.0):
    from types import SimpleNamespace
    return SimpleNamespace(alignment=a, deeds=None)


class TestDeeds(unittest.TestCase):
    def test_no_people_is_pinned_and_weight_is_kept(self):
        a, b = _civ(), _civ()
        for _ in range(100):
            alignment.people_shift(a, 0.12)
        for _ in range(300):
            alignment.people_shift(b, 0.12)
        self.assertLess(a.alignment, 1.0 + 1e-9)
        self.assertGreater(alignment.deeds_of(b), alignment.deeds_of(a))   # two histories, never one reading

    def test_old_deeds_fade_as_their_telling_does(self):
        a = _civ()
        alignment.people_shift(a, 2.0)
        alignment.fade(a, 1.0)
        self.assertAlmostEqual(alignment.deeds_of(a), 2.0 * (1.0 - memory.TELL_ERR), places=6)

    def test_deep_time_drift_is_bounded_and_unbiased(self):
        from xylarium.kernel import annals
        rng = random.Random(3)
        r = 1.0 - memory.TELL_ERR
        vals = []
        for _ in range(2000):
            c = _civ()
            alignment.fade(c, 10 ** 6)
            alignment.people_shift(c, rng.gauss(0.0, annals.ALIGN_DRIFT * math.sqrt(1.0 / (1.0 - r * r))))
            vals.append(c.alignment)
        self.assertLess(max(abs(v) for v in vals), 0.5)
        self.assertLess(abs(sum(vals) / len(vals)), 0.01)

    def test_a_set_alignment_is_honoured(self):
        a = _civ()
        alignment.people_shift(a, 1.0)
        a.alignment = -0.5
        self.assertAlmostEqual(math.tanh(alignment.deeds_of(a)), -0.5, places=4)


class TestRelicMindLeaning(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.p = max((p for s in self.k.sectors.values() for p in s.planets if p.population > 0
                      and p.civilization is not None), key=lambda p: p.population)
        self.who = knowledge.holder_of_planet(self.p)
        technology.stats(self.k)["of"].setdefault(self.who, {}).update({"computation": 1, "robotics": 1})
        knowledge.learn(self.k, self.who, "information", 10 ** 7)

    def _wake(self, makers_alignment, prey):
        self.p.ruins = {"relics": {"makers": "Elders", "mind": {"name": "civ:Elder Mind", "metab": "biotic",
                                                                "alignment": makers_alignment, "vocab": [],
                                                                "prey_plans": prey}}}
        relics._dig(self.k, self.who, [self.p])
        relics._minds(self.k)                                  # it takes a body
        return next(c for c in cohabit.communities(self.p) if c.get("relic_mind"))

    def test_it_comes_to_hold_what_its_finders_hold(self):
        from xylarium.kernel import contact
        alignment.set_people(self.p.civilization, 0.6)
        mind = self._wake(-0.9, [])
        contact.stats(self.k)["familiarity"][contact._key("civ:Elder Mind", self.who)] = 1.0
        before = math.atanh(-0.9)
        relics._minds(self.k)
        self.assertGreater(mind["deeds"], before)

    def test_it_keeps_its_silence_when_nothing_is_worth_doing(self):
        alignment.set_people(self.p.civilization, 0.0)
        mind = self._wake(0.0, [])
        relics._minds(self.k)
        self.assertEqual(mind["choice"], "silence")


if __name__ == "__main__":
    unittest.main()
