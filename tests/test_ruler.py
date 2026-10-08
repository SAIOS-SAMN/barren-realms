"""The rulers read 1 against themselves: the Sun's birth gas holds exactly the measured isotope inventory (bulk
silicate Earth), and the unit world every field is measured by is built of the Sun's own metals."""

import math
import unittest

from xylarium.kernel import cosmos, hydromagnetics, interior


class TestRuler(unittest.TestCase):
    def test_the_suns_birth_gas_holds_the_measured_inventory(self):
        inv = interior.inventory(None, cosmos.R0_KPC, interior.SUN_BORN_GYR, 1.0)
        for iso, (t_half, _, today, _) in interior.ISOTOPES.items():
            at_birth = today * math.exp(interior.SOLAR_AGE_GYR / (t_half / math.log(2.0)))
            self.assertAlmostEqual(inv[iso] / at_birth, 1.0, places=12)

    def test_the_unit_world_reads_one_against_itself(self):
        u = hydromagnetics._unit()
        self.assertAlmostEqual(hydromagnetics.moment(u), 1.0, places=12)
        self.assertAlmostEqual(u["q_cmb"], 0.0251755, places=6)          # the two kernels' shared ruler
        self.assertAlmostEqual(u["q_ad"], 0.0239142, places=6)


if __name__ == "__main__":
    unittest.main()
