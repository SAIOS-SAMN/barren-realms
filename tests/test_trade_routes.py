"""
Unit and integration tests for Trade Route and Arbitrage Optimization engine.
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, CommodityType
from xylarium.kernel.routes import TradeRouteOptimizer
from xylarium.client.renderer import TerminalRenderer


class TestTradeRouteOptimizer(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=1337)
        self.player = self.kernel.register_player("trader_test", "Captain Trader")

    def test_circular_arbitrage_ranking(self):
        """Verify circular arbitrage finder identifies profitable loops ranked by efficiency."""
        routes = TradeRouteOptimizer.find_circular_arbitrage(
            self.kernel,
            cargo_capacity=30,
            max_hops=4,
            min_efficiency=5.0
        )
        self.assertGreater(len(routes), 0)

        # Check ranking
        for i in range(len(routes) - 1):
            self.assertGreaterEqual(
                routes[i].efficiency_cr_per_turn,
                routes[i + 1].efficiency_cr_per_turn
            )

        # Verify top route properties
        top = routes[0]
        self.assertGreater(top.total_profit, 0)
        self.assertGreater(top.round_trip_turns, 0)
        self.assertGreater(top.warp_hops, 0)
        self.assertEqual(len(top.path), top.warp_hops + 1)
        self.assertTrue(top.leg_ab is not None or top.leg_ba is not None)

    def test_local_export_opportunities(self):
        """Verify finding export routes starting from current sector."""
        ops = TradeRouteOptimizer.find_local_opportunities(
            self.kernel,
            origin_sector_id=1,
            cargo_capacity=30,
            max_hops=5
        )
        self.assertGreater(len(ops), 0)

        top_op = ops[0]
        self.assertEqual(top_op.origin_sector, 1)
        self.assertGreater(top_op.unit_margin, 0)
        self.assertGreater(top_op.est_profit, 0)
        from xylarium.config import COMMODITY_CONFIG
        self.assertIn(top_op.commodity, COMMODITY_CONFIG)
        self.assertEqual(top_op.path[0], 1)
        self.assertEqual(top_op.path[-1], top_op.dest_sector)

    def test_colony_supply_routes(self):
        """Verify finding supply corridors for player-owned colonies."""
        # Find first planet in the universe and assign ownership to player
        planet = next(p for sec in self.kernel.sectors.values() for p in sec.planets)
        planet.owner_id = self.player.id
        colony_sec = planet.sector_id

        runs = TradeRouteOptimizer.find_colony_supply_routes(
            self.kernel,
            self.player,
            max_hops=8
        )
        self.assertGreater(len(runs), 0)

        for run in runs:
            self.assertEqual(run.planet_sector, colony_sec)
            self.assertIn(run.resource_needed, ["ORE", "ORGANICS"])
            self.assertGreater(run.available_stock, 0)
            self.assertGreater(run.buy_price, 0)
            self.assertEqual(run.path[0], run.source_sector)
            self.assertEqual(run.path[-1], colony_sec)

    def test_galactic_market_spreads(self):
        """Verify galactic ticker computes spreads across all 24+ commodities and elements."""
        spreads = TradeRouteOptimizer.get_galactic_spreads(self.kernel)
        self.assertGreater(len(spreads), 10)

        commodities_seen = {s.commodity for s in spreads}
        self.assertTrue({"ORE", "ORGANICS", "EQUIPMENT"}.issubset(commodities_seen))

        for s in spreads:
            self.assertGreater(s.gross_spread, 0)
            self.assertLessEqual(s.lowest_sell_price, s.highest_buy_price)
            self.assertGreater(len(s.path), 0)
            self.assertEqual(s.path[0], s.lowest_sell_sector)
            self.assertEqual(s.path[-1], s.highest_buy_sector)

    def test_kernel_dispatch_optimize_routes_free_turns(self):
        """Verify querying trade routes via dispatch costs 0 turns and returns clean data."""
        starting_turns = self.player.turns_left
        res = self.kernel.dispatch(self.player.id, ActionType.OPTIMIZE_ROUTES, mode="circular")
        self.assertTrue(res.success)
        self.assertEqual(res.turns_spent, 0)
        self.assertEqual(self.player.turns_left, starting_turns)
        self.assertIn("routes", res.data)
        self.assertGreater(len(res.data["routes"]), 0)

    def test_renderer_outputs(self):
        """Verify ANSI rendering functions format data without crashing."""
        view = self.kernel.get_player_view(self.player.id)
        menu_str = TerminalRenderer.render_trade_routes_menu(view)
        self.assertIn("TRADE ROUTE & ARBITRAGE OPTIMIZER", menu_str)

        routes = TradeRouteOptimizer.find_circular_arbitrage(self.kernel, cargo_capacity=30, max_hops=3)
        circ_str = TerminalRenderer.render_circular_arbitrage(routes, 1)
        self.assertIn("CIRCULAR ARBITRAGE RADAR", circ_str)

        ops = TradeRouteOptimizer.find_local_opportunities(self.kernel, 1, cargo_capacity=30)
        loc_str = TerminalRenderer.render_local_opportunities(ops, 1)
        self.assertIn("HIGH-YIELD EXPORTS FROM SECTOR 001", loc_str)

        spreads = TradeRouteOptimizer.get_galactic_spreads(self.kernel)
        spread_str = TerminalRenderer.render_galactic_ticker(spreads)
        self.assertIn("INTERSTELLAR COMMODITY MARKET TICKER", spread_str)

    def test_bulk_density_stack_multipliers(self):
        """Verify bulk density stack multipliers for Volatiles (5x), Metals (4x), Organics (2x), Exotics (1x)."""
        from xylarium.config import get_commodity_stack_multiplier
        self.assertEqual(get_commodity_stack_multiplier("H"), 5)
        self.assertEqual(get_commodity_stack_multiplier("H2O"), 5)
        self.assertEqual(get_commodity_stack_multiplier("Xe"), 5)
        self.assertEqual(get_commodity_stack_multiplier("Fe"), 4)
        self.assertEqual(get_commodity_stack_multiplier("Ti"), 4)
        self.assertEqual(get_commodity_stack_multiplier("ORE"), 4)
        self.assertEqual(get_commodity_stack_multiplier("ORGANICS"), 2)
        self.assertEqual(get_commodity_stack_multiplier("EQUIPMENT"), 1)
        self.assertEqual(get_commodity_stack_multiplier("U"), 1)
        self.assertEqual(get_commodity_stack_multiplier("M4_WARP_CORE"), 1)

    def test_category_filtered_arbitrage(self):
        """Verify category filtering isolates specific commodity classes."""
        v_routes = TradeRouteOptimizer.find_circular_arbitrage(
            self.kernel, cargo_capacity=30, max_hops=4, category="VOLATILES"
        )
        self.assertGreater(len(v_routes), 0)
        for r in v_routes:
            if r.leg_ab:
                self.assertIn(r.leg_ab.commodity, ["H", "He-3", "C", "H2O", "Xe", "ORGANICS"])
            if r.leg_ba:
                self.assertIn(r.leg_ba.commodity, ["H", "He-3", "C", "H2O", "Xe", "ORGANICS"])

        m_routes = TradeRouteOptimizer.find_circular_arbitrage(
            self.kernel, cargo_capacity=30, max_hops=4, category="METALS"
        )
        self.assertGreater(len(m_routes), 0)
        for r in m_routes:
            if r.leg_ab:
                self.assertIn(r.leg_ab.commodity, ["ORE", "Fe", "Ti", "Si", "Ni", "Cu", "AdL"])
            if r.leg_ba:
                self.assertIn(r.leg_ba.commodity, ["ORE", "Fe", "Ti", "Si", "Ni", "Cu", "AdL"])

    def test_element_specific_radar(self):
        """Verify targeted element radar focuses specifically on requested element."""
        fe_routes = TradeRouteOptimizer.find_element_radar(
            self.kernel, commodity="Fe", cargo_capacity=30, max_hops=6
        )
        self.assertGreater(len(fe_routes), 0)
        for r in fe_routes:
            self.assertTrue(
                (r.leg_ab and r.leg_ab.commodity == "Fe") or (r.leg_ba and r.leg_ba.commodity == "Fe")
            )


if __name__ == "__main__":
    unittest.main()

