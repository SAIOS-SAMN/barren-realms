"""
A pool's fee is felt out every quarter on the trade last seen - not frozen where it stood when trade stopped - and a
withdrawal that would move nothing takes no shares and counts as nothing.
"""

import unittest
from unittest import mock

from xylarium.kernel import liquidity
from xylarium.kernel.engine import GameKernel


class TestReprice(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=42)
        self.fxm = self.k.fx_market
        self.cur = sorted(self.fxm.pools)[0]
        liquidity.stats(self.k)

    def test_a_quarter_with_no_trade_still_reprices_on_the_trade_last_seen(self):
        liquidity.stats(self.k).setdefault("volume_seen", {})[self.cur] = 1000.0
        with mock.patch.object(liquidity, "price_service") as ps:
            liquidity.read(self.k)                      # no volume this quarter
        self.assertTrue(any(c.args[1] == self.cur and c.args[2] == 1000.0 for c in ps.call_args_list))

    def test_a_withdrawal_that_moves_nothing_takes_no_shares(self):
        st = liquidity.stats(self.k)
        holder = next(iter(st["positions"][self.cur]))
        before = (st["shares"][self.cur], st["withdrawals"])
        got = liquidity.withdraw(self.k, holder, self.cur, st["shares"][self.cur] * 1e-30, lambda x: None, lambda x: None)
        self.assertEqual(got, (0, 0))
        self.assertEqual((st["shares"][self.cur], st["withdrawals"]), before)


if __name__ == "__main__":
    unittest.main()
