"""
Unit tests for Cargo Cost Basis tracking, Imperial Dominion Asset Registry,
and Automated Trade Fleets (Trade Haulers).
"""

import unittest
import os
import tempfile
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, CommodityType
from xylarium.kernel.economy import EconomyManager
from xylarium.client.renderer import TerminalRenderer
from xylarium.persistence.store import StatePersistence


class TestCargoCostBasis(unittest.TestCase):
    """Tests weighted-average cost basis calculation on cargo hold transactions."""

    def setUp(self):
        self.kernel = GameKernel(seed=123)
        # Haulers run between starports; pick the first real port beyond Sol on this board
        self.dest_port = next(sec.id for sec in sorted(self.kernel.sectors.values(), key=lambda x: x.id) if sec.id > 1 and sec.port)
        self.player = self.kernel.register_player("test_player", "Test Captain")
        self.player.credits = 50000

    def test_single_purchase_sets_cost_basis(self):
        # Move to sector 1 which has stardock port
        sector = self.kernel.sectors[1]
        res = self.kernel.dispatch(
            "test_player",
            ActionType.TRADE,
            type="BUY",
            commodity="ORE",
            amount=10
        )
        self.assertTrue(res.success)
        self.assertEqual(self.player.ship.cargo.ore, 10)
        unit_price = res.data["unit_price"]
        self.assertAlmostEqual(self.player.ship.cargo.cost_basis["ore"], float(unit_price), places=1)

    def test_weighted_average_cost_basis(self):
        sector = self.kernel.sectors[1]
        port = sector.port
        self.assertIsNotNone(port)

        # Initial buy: 10 units
        res1 = self.kernel.dispatch("test_player", ActionType.TRADE, type="BUY", commodity="ORE", amount=10)
        p1 = res1.data["unit_price"]

        # Second buy: 10 units at new (higher) price
        res2 = self.kernel.dispatch("test_player", ActionType.TRADE, type="BUY", commodity="ORE", amount=10)
        p2 = res2.data["unit_price"]

        expected_basis = round(((10 * p1) + (10 * p2)) / 20, 1)
        self.assertEqual(self.player.ship.cargo.ore, 20)
        self.assertAlmostEqual(self.player.ship.cargo.cost_basis["ore"], expected_basis, places=1)

    def test_sell_reports_profit_and_clears_basis_on_empty(self):
        # Buy 10 Ore
        res_buy = self.kernel.dispatch("test_player", ActionType.TRADE, type="BUY", commodity="ORE", amount=10)
        cost_ea = res_buy.data["unit_price"]

        # Warp to another sector or sell back at Stardock
        # In Stardock, selling gives payout and reports profit in message and data
        res_sell = self.kernel.dispatch("test_player", ActionType.TRADE, type="SELL", commodity="ORE", amount=10)
        self.assertTrue(res_sell.success)
        self.assertEqual(self.player.ship.cargo.ore, 0)
        # Basis resets to 0.0 when inventory is completely liquidated
        self.assertEqual(self.player.ship.cargo.cost_basis["ore"], 0.0)
        self.assertIn("cost_basis", res_sell.data)
        self.assertIn("profit_per_unit", res_sell.data)
        self.assertIn("net_profit", res_sell.data)


class TestEmpireDominionAndHaulers(unittest.TestCase):
    """Tests Imperial Dominion Console, Colony Warp Visibility, and Automated Trade Fleets."""

    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.dest_port = next(sec.id for sec in sorted(self.kernel.sectors.values(), key=lambda x: x.id) if sec.id > 1 and sec.port)
        self.player = self.kernel.register_player("captain_emp", "Emperor Solo")
        self.player.credits = 100000

    def test_colony_ownership_reflected_in_view_and_warps(self):
        # Claim a planet in Sector 2
        sec2 = self.kernel.sectors[2]
        if not sec2.planets:
            # Pick a sector with planets
            target_sec = None
            for s in self.kernel.sectors.values():
                if s.planets and s.id != 1:
                    target_sec = s
                    break
            self.assertIsNotNone(target_sec)
        else:
            target_sec = sec2

        planet = target_sec.planets[0]
        planet.owner_id = self.player.id
        planet.name = "New Avalon"

        # Position player in a neighboring sector connected to target_sec
        neighbor_id = list(target_sec.warps)[0]
        self.player.sector_id = neighbor_id

        view = self.kernel.get_player_view("captain_emp")
        # Check owned_planets in view
        owned = view.get("owned_planets", [])
        self.assertEqual(len(owned), 1)
        self.assertEqual(owned[0]["name"], "New Avalon")
        self.assertEqual(owned[0]["sector_id"], target_sec.id)

        # Check warp flags in neighbor sector
        neighbor_warps = view["sector"]["warps"]
        target_warp_entry = [w for w in neighbor_warps if w["sector_id"] == target_sec.id][0]
        self.assertTrue(target_warp_entry["has_my_planet"])
        self.assertEqual(target_warp_entry["my_planet_name"], "New Avalon")

        # Test sector rendering includes colony badge
        rendered_sec = TerminalRenderer.render_sector(view)
        self.assertIn("My Colony: New Avalon", rendered_sec)

    def test_commission_and_manage_trade_hauler(self):
        # Commission a hauler between Sector 1 and the first starport beyond Sol
        res = self.kernel.dispatch(
            "captain_emp",
            ActionType.HAULER_COMMISSION,
            name="Void Clipper",
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="EQUIPMENT",
            commodity_return="ORGANICS",
        )
        self.assertTrue(res.success)
        self.assertEqual(self.player.credits, 96000)  # 100,000 - 4,000
        self.assertEqual(len(self.player.trade_haulers), 1)
        hauler_id = self.player.trade_haulers[0]
        hauler = self.kernel.market_manager.trade_haulers[hauler_id]
        self.assertEqual(hauler.name, "Void Clipper")
        self.assertEqual(hauler.origin_sector, 1)
        self.assertEqual(hauler.dest_sector, self.dest_port)

        # Reassign route
        res_re = self.kernel.dispatch(
            "captain_emp",
            ActionType.HAULER_ASSIGN_ROUTE,
            hauler_id=hauler_id,
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="ORE",
            commodity_return="EQUIPMENT",
        )
        self.assertTrue(res_re.success)
        self.assertEqual(hauler.commodity_outbound, "ORE")

        # View hauler in player view
        view = self.kernel.get_player_view("captain_emp")
        haulers_in_view = view.get("trade_haulers", [])
        self.assertEqual(len(haulers_in_view), 1)
        self.assertEqual(haulers_in_view[0]["id"], hauler_id)

        # Render Empire console
        rendered_console = TerminalRenderer.render_empire_console(view)
        self.assertIn("IMPERIAL DOMINION & ASSET REGISTRY CONSOLE", rendered_console)
        self.assertIn("Void Clipper", rendered_console)
        self.assertIn(hauler_id, rendered_console)

        # Decommission hauler
        res_dec = self.kernel.dispatch(
            "captain_emp",
            ActionType.HAULER_DECOMMISSION,
            hauler_id=hauler_id,
        )
        self.assertTrue(res_dec.success)
        self.assertEqual(self.player.credits, 98000)  # +2,000 refund
        self.assertEqual(len(self.player.trade_haulers), 0)
        self.assertNotIn(hauler_id, self.kernel.market_manager.trade_haulers)

    def test_automated_trade_hauler_cycle_yield(self):
        # Commission hauler between Sector 1 (Stardock, sells all) and the first starport beyond Sol
        res = self.kernel.dispatch(
            "captain_emp",
            ActionType.HAULER_COMMISSION,
            name="Iron Mule",
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="EQUIPMENT",
            commodity_return="ORGANICS",
        )
        self.assertTrue(res.success)
        hauler_id = self.player.trade_haulers[0]
        hauler = self.kernel.market_manager.trade_haulers[hauler_id]

        initial_credits = self.player.credits
        # Trigger market tick which runs haulers
        self.kernel.market_manager.tick_trade_haulers(self.kernel)

        # Check that hauler executed trades if profitable
        if hauler.trips_completed > 0:
            self.assertGreater(hauler.lifetime_profit, 0)
            self.assertGreater(self.player.credits, initial_credits)

    def test_empire_and_hauler_state_persistence(self):
        # Buy cargo to establish cost basis
        self.kernel.dispatch("captain_emp", ActionType.TRADE, type="BUY", commodity="ORE", amount=15)
        # Commission hauler
        self.kernel.dispatch(
            "captain_emp",
            ActionType.HAULER_COMMISSION,
            name="Titan Courier",
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="EQUIPMENT",
            commodity_return="ORGANICS",
        )
        hauler_id = self.player.trade_haulers[0]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            filepath = tf.name

        try:
            saved = StatePersistence.save_to_file(self.kernel, filepath)
            self.assertTrue(saved)

            loaded_kernel = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(loaded_kernel)

            loaded_player = loaded_kernel.get_player("captain_emp")
            self.assertIsNotNone(loaded_player)
            self.assertEqual(loaded_player.ship.cargo.ore, 15)
            self.assertGreater(loaded_player.ship.cargo.cost_basis["ore"], 0.0)

            self.assertEqual(len(loaded_player.trade_haulers), 1)
            self.assertIn(hauler_id, loaded_kernel.market_manager.trade_haulers)
            loaded_hauler = loaded_kernel.market_manager.trade_haulers[hauler_id]
            self.assertEqual(loaded_hauler.name, "Titan Courier")
            self.assertEqual(loaded_hauler.origin_sector, 1)
            self.assertEqual(loaded_hauler.dest_sector, self.dest_port)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


if __name__ == "__main__":
    unittest.main()
