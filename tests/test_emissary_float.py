"""
A people's emissary carries its people's own money as its crew's float - in its wallet - never forced through an
exchange (a shallow pool took it all: every emissary launched with nothing).
"""

import unittest
import zlib
from unittest import mock

from xylarium.kernel import colony, mastery, populace, sustenance
from xylarium.kernel.engine import GameKernel


class TestEmissaryFloat(unittest.TestCase):
    def test_the_float_is_its_peoples_money_in_its_wallet(self):
        k = GameKernel(seed=42)
        hub = k.fx_market.hub
        p = next(w for s in k.sectors.values() for w in s.planets
                 if w.population > 0 and w.civilization is not None and w.currency != hub and not w.natives)
        p.treasury = 10 ** 9
        p.active_indigenous_captain_id = None
        k.cycle_count = zlib.crc32(p.id.encode()) % 25
        with mock.patch.object(sustenance, "yards", return_value=True), \
                mock.patch.object(mastery, "crossed", return_value=True), \
                mock.patch.object(populace, "room_for_ai", return_value=True), \
                mock.patch.object(k.fx_market, "swap_to_sol", side_effect=AssertionError("no swap")):
            cap = colony.ColonyManager.check_planetary_spaceflight(k, p)
        self.assertIsNotNone(cap)
        self.assertGreater(cap.fx_wallet.get(p.currency, 0), 0)


if __name__ == "__main__":
    unittest.main()


class TestRefloat(unittest.TestCase):
    def test_a_stranded_hull_in_service_is_given_its_float_again(self):
        k = GameKernel(seed=42)
        hub = k.fx_market.hub
        p = next(w for s in k.sectors.values() for w in s.planets
                 if w.population > 0 and w.civilization is not None and w.currency != hub and not w.natives)
        p.treasury = 10 ** 9
        cap = next(iter(k.captains.values()))
        cap.credits, cap.fx_wallet = 0, {}
        paid = colony.ColonyManager._refloat(k, p, cap)
        self.assertGreater(paid, 0)
        self.assertEqual(cap.fx_wallet[p.currency], paid)
        self.assertEqual(p.treasury, 10 ** 9 - paid)                      # a transfer, nothing minted
        self.assertEqual(colony.ColonyManager._refloat(k, p, cap), 0)    # not while it holds money
