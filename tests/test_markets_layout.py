"""
The markets hub lays every ledger out the same way - LEDGER, LOCAL, BRIDGED, YOURS, ACTIONS - inside the frame.
"""

import random
import re
import unittest

from xylarium.client.markets import TABS, WIDTH, render_markets
from xylarium.kernel.engine import GameKernel

ANSI = re.compile(r"\x1b\[[0-9;]*m")


class TestMarketsLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        random.seed(81)
        cls.k = GameKernel(seed=7)
        cls.k.activate()
        cls.cap = cls.k.register_player("viewer", "Viewer")
        for _ in range(60):
            cls.k.tick_simulation()

    def test_every_tab_has_the_same_bands_in_the_same_order(self):
        for _, tab in TABS:
            plain = ANSI.sub("", render_markets(self.k, self.cap, tab))
            idx = [plain.find(f"  {b}") for b in ("LEDGER", "LOCAL", "BRIDGED", "YOURS", "ACTIONS")]
            self.assertTrue(all(i >= 0 for i in idx), tab)
            self.assertEqual(idx, sorted(idx), tab)

    def test_every_line_fits_the_frame(self):
        for _, tab in TABS:
            plain = ANSI.sub("", render_markets(self.k, self.cap, tab))
            longest = max(len(line.rstrip()) for line in plain.splitlines())
            self.assertLessEqual(longest, WIDTH, tab)

    def test_the_hub_answers_to_its_words(self):
        from xylarium.client import screens
        for word in ("MARKETS", "MARKET", "MKT", "$"):
            self.assertIn(word, screens.SCREENS)


if __name__ == "__main__":
    unittest.main()
