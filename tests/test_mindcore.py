"""
The mind core: one reduction for every intelligence - residual, drain, verdict, lead, seal, hearing, conduct.
"""

import unittest
from fractions import Fraction

from xylarium.kernel import mindcore as mc


class TestReduction(unittest.TestCase):
    def test_a_residual_is_signed_and_never_summed(self):
        need = mc.measure([("self", "food", 10), ("self", "wealth", 3)])
        have = mc.measure([("self", "food", 4), ("self", "wealth", 5)])
        r = mc.residual(need, have)
        self.assertEqual(r, {("self", "food"): Fraction(6), ("self", "wealth"): Fraction(-2)})

    def test_the_first_deficit_in_the_layers_order_leads(self):
        r = mc.measure([("self", "wealth", 9), ("self", "food", 1), ("self", "room", -4)])
        self.assertEqual(mc.lead(r, ("food", "room", "wealth")), ("self", "food"))
        self.assertIsNone(mc.lead(mc.measure([("self", "room", -1)]), ("food", "room")))

    def test_a_deed_that_delivers_is_sealed_and_drains_the_next_time(self):
        m = mc.new_mind()
        r = mc.measure([("self", "food", 6)])
        v = mc.verdict(m, r)
        self.assertEqual(v["reading"], mc.GENERATION_GAP)                 # nothing known answers it
        mc.intend(m, ("self", "food"), Fraction(6), "trade")
        self.assertEqual(mc.seal(m, mc.measure([("self", "food", 2)])), "crystal")   # it delivered 4
        self.assertEqual(mc.recall(m, ("self", "food"), Fraction(5)), "trade")
        v = mc.verdict(m, mc.measure([("self", "food", 4)]))
        self.assertEqual(v["reading"], mc.ACCOUNTED)                      # 4 owed, 4 drained
        v = mc.verdict(m, mc.measure([("self", "food", 7)]))
        self.assertEqual(v["reading"], mc.COMPOSITION_GAP)                # known shape, 3 carried
        self.assertEqual(v["left"][("self", "food")], Fraction(3))

    def test_a_deed_that_delivers_nothing_is_a_wall(self):
        m = mc.new_mind()
        mc.intend(m, ("self", "security"), Fraction(5), "peace")
        self.assertEqual(mc.seal(m, mc.measure([("self", "security", 5)])), "wall")
        self.assertIn("peace", mc.walls(m, mc.shape(("self", "security"), Fraction(5))))

    def test_hearing_adopts_only_what_is_understood_and_never_copies_the_speaker(self):
        a, b = mc.new_mind(), mc.new_mind()
        a["crystals"]["self|food|+"] = {"deed": "trade", "delivers": "8"}
        self.assertEqual(mc.hear(b, "self|food|+", a["crystals"]["self|food|+"], Fraction(1, 4)), "learned")
        self.assertEqual(Fraction(b["crystals"]["self|food|+"]["delivers"]), Fraction(2))
        self.assertEqual(mc.hear(b, "self|food|+", a["crystals"]["self|food|+"], 1), "understood")
        self.assertEqual(Fraction(a["crystals"]["self|food|+"]["delivers"]), Fraction(8))

    def test_conduct_is_read_per_axis_and_absent_where_nothing_has_passed(self):
        ba, bb = {}, {}
        self.assertIsNone(mc.reading(ba, "b")["integrity"])
        mc.record(ba, bb, "a", "b", "integrity", syntropic=3, entropic=1)
        self.assertEqual(mc.reading(ba, "b")["integrity"], Fraction(3, 4))
        self.assertEqual(mc.reading(bb, "a")["integrity"], Fraction(3, 4))
        self.assertIsNone(mc.reading(ba, "b")["compassion"])
