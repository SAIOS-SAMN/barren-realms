"""
A primordial universe starts with every people on its homeworld; ships come from yards; the exchange prices its
service with no floor or ceiling; idle money carries a cost; and hierarchies are contracts both sides accept.
"""

import random
import unittest

from xylarium.kernel import decide, liquidity, populace, prices, primordial, relations
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply


def money(k):
    return {c: b["total"] for c, b in money_supply(k).items()}


class TestPrimordialGenesis(unittest.TestCase):
    def setUp(self):
        random.seed(61)
        self.k = GameKernel(seed=7, genesis="primordial")
        self.k.activate()

    def test_nothing_is_spacefaring_at_the_start(self):
        k = self.k
        self.assertTrue(primordial.is_primordial(k))
        self.assertEqual(sum(1 for s in k.sectors.values() if s.port is not None), 0)
        self.assertEqual(len(k.captains), 0)
        self.assertEqual(len(k.market_manager.companies), 0)
        worlds = [p for s in k.sectors.values() for p in s.planets if p.population > 0]
        self.assertTrue(worlds)
        self.assertTrue(all(p.citadel_level == 0 and not p.faction_id for p in worlds))
        self.assertEqual(populace.ai_capacity(k), 0)              # no yards, no hulls in service

    def test_terra_is_an_ordinary_homeworld(self):
        terra = self.k.get_planet("planet_1")
        self.assertLessEqual(terra.treasury, 1200)
        self.assertLessEqual(terra.fighters, 40)

    def test_a_world_with_yards_commissions_a_ship_and_its_dock(self):
        import zlib
        from xylarium.config import DAUGHTER_CITADEL_TIER
        from xylarium.kernel.colony import ColonyManager
        from unittest import mock
        k = self.k
        w = max((p for s in k.sectors.values() for p in s.planets if p.population > 0), key=lambda p: p.population)
        w.citadel_level = DAUGHTER_CITADEL_TIER
        w.treasury = 10 ** 6
        k.cycle_count = zlib.crc32(w.id.encode()) % 25
        m0 = money(k)
        with mock.patch.object(decide, "choose", lambda kk, opts, m, *salt: opts[0]):
            cap = ColonyManager.check_planetary_spaceflight(k, w)
        self.assertIsNotNone(cap)
        self.assertIsNotNone(k.sectors[w.sector_id].port)
        self.assertIn("first_starship", k.state["genesis"]["firsts"])
        self.assertEqual(m0, money(k))


class TestLiquidityAndCarry(unittest.TestCase):
    def setUp(self):
        random.seed(63)
        self.k = GameKernel(seed=7)
        self.k.activate()

    def test_the_fee_is_a_share_below_one_however_deep_and_idle_the_pool(self):
        cur = next(iter(self.k.fx_market.pools))
        liquidity.stats(self.k)["vol"][cur] = 0.5          # violent rates: providing is dear
        for _ in range(40):
            fee = liquidity.price_service(self.k, cur, volume_q=1.0)
        self.assertGreater(fee, 0.0)
        self.assertLess(fee, 1.0)

    def test_inflation_makes_idle_cash_cost_something(self):
        st = prices._st(self.k)
        st["hist"]["SOL"] = [1.0, 1.02, 1.04, 1.06, 1.08]
        self.assertGreater(prices.carry(self.k, "SOL"), 0.0)
        m = decide.mind(self.k, "biotic")
        idle = decide.option("put_to_work", 100.0, 100.0, cash=100.0, currency="SOL")
        self.assertIsNotNone(decide.choose(self.k, [idle], dict(m, noise=1e-9), "carry"))   # break-even + carry wins


class TestRelations(unittest.TestCase):
    def setUp(self):
        random.seed(67)
        self.k = GameKernel(seed=7)
        self.k.activate()

    def test_family_and_roots(self):
        relations.ties(self.k)["civ:A"] = {"patron": "civ:B", "tribute_sol": 1.0, "since": 0, "paid": 0.0}
        relations.ties(self.k)["civ:B"] = {"patron": "civ:C", "tribute_sol": 1.0, "since": 0, "paid": 0.0}
        self.assertEqual(relations.root(self.k, "civ:A"), "civ:C")
        self.assertTrue(relations.family(self.k, "civ:A", "civ:C"))
        self.assertFalse(relations.family(self.k, "civ:A", "civ:D"))

    def test_a_worlds_stores_are_lost_at_most_once(self):
        k = self.k
        by = relations._peoples(k)
        sub, worlds = next(iter(by.items()))
        loss, _ = relations.threat(k, sub, worlds, by, {}, base=1.0)
        from xylarium.kernel import staples
        from xylarium.config import COMMODITY_CONFIG, PRICE_LEVEL
        cap = sum(staples.surplus(k, w, staples.of(k, w)) * COMMODITY_CONFIG.get(staples.of(k, w), {}).get(
            "base_price", 20) * PRICE_LEVEL.get(w.currency, 1.0) for w in worlds)
        self.assertLessEqual(loss, cap + 1e-6)

    def test_tribute_moves_money_and_conserves_it(self):
        k = self.k
        by = relations._peoples(k)
        (a, wa), (b, wb) = list(by.items())[:2]
        for w in wa:
            w.treasury = 10 ** 6
        relations.ties(k)[a] = {"patron": b, "tribute_sol": 1000.0, "since": 0, "paid": 0.0}
        m0 = money(k)
        k.cycle_count = 25                                   # a season, not a year's review
        relations.quarter(k)
        self.assertEqual(m0, money(k))
        self.assertGreater(relations.ties(k)[a]["paid"], 0)


if __name__ == "__main__":
    unittest.main()
