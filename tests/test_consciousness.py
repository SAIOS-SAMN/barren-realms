"""
Consciousness on the H lane (3.9): a council produces what its court closures discharged on the fourth lane; its
house's parliament carries it out over the throats, keeping exp(-span / lambda) per hop (lambda the core bell's
wavelength); the peoples reached receive equal parts of what arrives; what is lost is booked as dissipated.
"""

import math
import unittest
from fractions import Fraction as F
from unittest import mock

from xylarium.kernel import consciousness, court, field
from xylarium.kernel.engine import GameKernel


class TestConsciousness(unittest.TestCase):
    def test_a_council_produces_its_closures_h_lane_once(self):
        k = GameKernel(seed=42)
        court.stats(k)["of"]["civ:Elder"] = {"mu": ["5", "0", "0", "9"]}
        self.assertEqual(consciousness.produced(k, "civ:Elder"), 9)
        self.assertEqual(consciousness.produced(k, "civ:Elder"), 0)          # read once

    def test_a_handoff_keeps_less_the_longer_the_span(self):
        lam = field.wavelength_kpc()
        self.assertAlmostEqual(float(consciousness.kept(lam)), math.exp(-1), places=12)
        self.assertGreater(consciousness.kept(1.0), consciousness.kept(10.0))

    def test_what_is_carried_arrives_in_equal_parts_less_the_span_and_the_rest_is_dissipated(self):
        k = GameKernel(seed=42)
        court.stats(k)["of"]["civ:Elder"] = {"mu": ["0", "0", "0", "12"]}
        shares = {"civ:Elder": F(1), "civ:Far": F(1, 2)}
        with mock.patch.object(court, "houses", return_value=["civ:Elder"]), \
                mock.patch("xylarium.kernel.board.progenitors", return_value={"civ:Elder": {}}), \
                mock.patch.object(consciousness, "reach", return_value=shares):
            k.cycle_count = 0
            consciousness.season(k)
        st = consciousness.stats(k)
        self.assertEqual((F(st["received"]["civ:Elder"]), F(st["received"]["civ:Far"])), (6, 3))
        self.assertEqual(F(st["dissipated"]), 3)                              # made 12 = 6 + 3 received + 3 lost

    def test_what_a_people_holds_lifts_its_fluid_against_its_own_information(self):
        from xylarium.kernel import knowledge
        k = GameKernel(seed=42)
        with mock.patch.object(knowledge, "stocks", return_value={"information": 3.0, "craft": 10.0}), \
                mock.patch("xylarium.kernel.intellect.fluid", return_value=0.0):
            self.assertEqual(consciousness.gain(k, "civ:Far"), 0.0)
            self.assertEqual(knowledge.experience(k, "civ:Far", "craft"), 10.0)
            consciousness.stats(k)["held"]["civ:Far"] = "1"
            self.assertAlmostEqual(consciousness.gain(k, "civ:Far"), 0.25)       # 1 / (1 + 3)
            self.assertAlmostEqual(knowledge.experience(k, "civ:Far", "craft"), 12.5)
        with mock.patch.object(knowledge, "stocks", return_value={"information": 3.0, "craft": 10.0}), \
                mock.patch("xylarium.kernel.intellect.fluid", return_value=0.5):
            self.assertAlmostEqual(knowledge.experience(k, "civ:Far", "craft"), 10 * (1 + 1 - 0.5 * 0.75))

    def test_what_is_held_fades_at_the_peoples_forgetting_rate(self):
        from xylarium.kernel import cosmos, knowledge
        k = GameKernel(seed=42)
        st = consciousness.stats(k)
        st["held"]["civ:Far"] = "8"
        with mock.patch.object(cosmos, "is_cosmic", return_value=True), \
                mock.patch.object(knowledge, "forgetting", return_value=0.1):
            with mock.patch.object(cosmos, "deep_gyr", return_value=1.0):
                consciousness._fade(k)                                        # the first reading sets the clock
            self.assertEqual(F(st["held"]["civ:Far"]), 8)
            with mock.patch.object(cosmos, "deep_gyr", return_value=1.0 + 2e-9):
                consciousness._fade(k)                                        # two years on
        self.assertAlmostEqual(float(F(st["held"]["civ:Far"])), 8 * math.exp(-0.2), places=9)

    def test_lines_whose_throats_connect_sit_in_one_parliament(self):
        from xylarium.kernel import transit
        k = GameKernel(seed=42)
        worms = {"1-2": {"a": 1, "b": 2, "owner": "civ:A"}, "2-3": {"a": 2, "b": 3, "owner": "civ:B"},
                 "7-8": {"a": 7, "b": 8, "owner": "civ:C"}, "3-9": {"a": 3, "b": 9, "owner": "civ:D", "dormant": 5}}
        with mock.patch.object(transit, "stats", return_value={"worms": worms}):
            p = consciousness.parliaments(k)
            self.assertEqual(p["civ:A"], frozenset({"civ:A", "civ:B"}))
            self.assertEqual(p["civ:C"], frozenset({"civ:C"}))
            self.assertNotIn("civ:D", p)                                      # a dormant throat joins nothing
            del worms["2-3"]
            self.assertEqual(consciousness.parliaments(k)["civ:A"], frozenset({"civ:A"}))   # the link lost: split


if __name__ == "__main__":
    unittest.main()
