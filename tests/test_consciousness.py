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


if __name__ == "__main__":
    unittest.main()
