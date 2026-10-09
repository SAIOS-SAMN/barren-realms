"""
The ancients' air leaks at the rate their world's own model loses it; they replace it from their stores of their
medium's good (a hold slot's mass a unit), and what they cannot cover lowers the air they stand in - never below the
world's untended path. Mu held on a world dissipates at the share of its air that world loses a year: its value to the hypha as the
connection tax, its matter left there as inverse-mu.
"""

import unittest
from fractions import Fraction as F
from unittest import mock

from xylarium.kernel import cargo, leak, reserve_banks, uses, worlds
from xylarium.kernel.engine import GameKernel


def _state(age, air_bar):
    return {"args": (None, None, 1.0, 1.0, 1.0, False, 1.0, 8.0, age, None), "world": {"radius": 1.0, "g": 1.0,
                                                                                       "air": {"N2": air_bar}}}


class TestLeak(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        self.w = next(p for s in self.k.sectors.values() for p in s.planets if p.civilization is not None)
        self.ages = [(1.00, 1.0)]
        p = mock.patch.object(worlds, "state_of_planet", side_effect=lambda k, pl, *a, **kw: _state(*self.ages[-1]))
        p.start()
        self.addCleanup(p.stop)

    def test_a_bar_of_air_on_an_earth_weighs_what_earths_does(self):
        kg = sum(leak.air_kg({"radius": 1.0, "g": 1.0, "air": {"N2": 1.0}}).values())
        self.assertAlmostEqual(kg / 5.15e18, 1.0, places=1)            # Earth's atmosphere: 5.15e18 kg

    def test_the_rate_is_read_off_the_model_as_it_ages_and_a_world_gaining_air_leaks_nothing(self):
        self.assertEqual(leak.rate(self.k, self.w)["kg_yr"], "0")      # first read: no rate yet
        self.ages.append((1.01, 0.99))
        r = leak.rate(self.k, self.w)
        one_bar = sum(leak.air_kg({"radius": 1.0, "g": 1.0, "air": {"N2": 1.0}}).values())
        self.assertAlmostEqual(float(F(r["kg_yr"])), one_bar * 0.01 / 1e7, delta=one_bar * 1e-12)
        self.ages.append((1.02, 1.5))
        self.assertEqual(leak.rate(self.k, self.w)["kg_yr"], "0")

    def _clock(self, gyr):
        return mock.patch("xylarium.kernel.cosmos.deep_gyr", return_value=gyr)

    def test_stores_replace_the_leak_and_an_empty_store_lets_the_air_fall_to_its_untended_path(self):
        with mock.patch.object(uses, "medium", return_value="H2O"), \
                mock.patch("xylarium.kernel.cosmos.is_cosmic", return_value=True):
            with self._clock(1.0):
                leak.rate(self.k, self.w)
                leak.hold(self.k, self.w)
            self.ages.append((1.01, 0.99))
            self.w.element_reserves["H2O"] = 10 ** 12                  # stores enough to replace it
            with self._clock(1.0 + 1e-6):                              # a thousand years on
                rec = leak.hold(self.k, self.w)
            self.assertEqual(F(rec["held_kg"]), F(rec["native_kg"]))    # held whole
            self.assertGreater(F(rec["consumed_kg"]), 0)
            self.assertLess(F(rec["carry_kg"]), cargo.unit_kg("H2O"))  # a slot's remainder, carried
            self.w.element_reserves["H2O"] = 0
            with self._clock(1.1):                                     # 100 million years, nothing to replace it
                rec = leak.hold(self.k, self.w)
            floor = F(leak.rate(self.k, self.w)["air_kg"])
            self.assertEqual(F(rec["held_kg"]), floor)                  # no lower than its untended path
            self.assertGreater(F(rec["short_kg"]), 0)

    def test_mu_held_on_a_world_dissipates_at_its_air_loss_share_and_recycles(self):
        b = reserve_banks.bank(self.k, "civ:House")
        b["reserve"], b["held_at"] = ["1000", "0", "0", "0"], self.w.id
        self.w.society["_leak"] = {"age": 1.0, "air_kg": "100", "kg_yr": "1", "share_yr": str(F(1, 100000))}
        with mock.patch.object(leak, "rate", return_value=self.w.society["_leak"]):
            left = leak.demurrage(self.k, "civ:House", F(1000))
        self.assertEqual(left[0], F(1000) - F(1000) * F(1000, 100000))
        self.assertEqual(F(b["tax_owed"][0]), F(10))                    # its value: the hypha's connection tax
        self.assertEqual(F(self.w.society["inverse_mu"]["lanes"][0]), F(10))   # its matter: inverse-mu, left here
        self.w.society["_leak"]["share_yr"] = "0"                       # a world that holds its air holds its mu
        with mock.patch.object(leak, "rate", return_value=self.w.society["_leak"]):
            self.assertEqual(leak.demurrage(self.k, "civ:House", F(1000))[0], left[0])


    def test_an_ancients_world_keeps_a_season_of_its_leak_and_commerce_wants_it(self):
        from xylarium.kernel import commerce, staples
        self.w.society["air_hold"] = {"years_last": "1000"}
        self.w.society["_leak"] = {"kg_yr": str(F(cargo.unit_kg("H2O")) * 3 / 1000)}   # three slots a thousand years
        with mock.patch.object(uses, "medium", return_value="H2O"):
            self.assertEqual(leak.keep_units(self.k, self.w, "H2O"), 3)
            self.assertEqual(leak.keep_units(self.k, self.w, "ORE"), 0)
            self.assertGreaterEqual(staples.reserve(self.k, self.w, "H2O"), 3)
            self.assertIn("H2O", commerce._goods(self.k, self.w))


class TestCargo(unittest.TestCase):
    def test_a_unit_is_a_hold_slot_of_the_good_at_its_measured_density(self):
        self.assertEqual(cargo.unit_kg("H2O"), F("33.2") * 1000)        # water at 1 g/cc
        self.assertEqual(cargo.unit_kg("cryogenite"), F("33.2") * F("0.68") * 1000)   # ammonia
        self.assertIsNone(cargo.unit_kg("no such good"))


if __name__ == "__main__":
    unittest.main()
