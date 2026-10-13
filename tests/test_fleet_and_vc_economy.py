"""
Comprehensive unit and integration test suite for:
- Interstellar Venture Capital Syndicates & Debt-Equity Financing
- Specialized Hauler Classes & Cargo Compatibility Validation
- Hierarchical 24-Element Periodic Table & Manufactured Goods Commerce
- Multi-Hauler Fleet Management, Escort Wings, Wear & Tear, and Autonomous Tick
"""

import unittest
from xylarium.config import COMMODITY_CONFIG, COMMODITY_CATEGORIES, SPECIALIZED_HULLS, VC_SYNDICATES
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Port, PortClass, TradeHauler
from xylarium.kernel.economy import EconomyManager
from xylarium.client.renderer import TerminalRenderer


class TestFleetAndVCEconomy(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        # Haulers run between starports; pick the first real port beyond Sol on this board
        self.dest_port = next(sec.id for sec in sorted(self.kernel.sectors.values(), key=lambda x: x.id) if sec.id > 1 and sec.port)
        self.player_id = "test_player"
        self.player = self.kernel.register_player(self.player_id, "Captain Sterling")
        # Start at Sector 1 Stardock Central
        self.player.sector_id = 1
        self.player.credits = 100000
        # Established captain: VC facilities are sized to rank authority and realized revenue
        self.player.rank_tier = 2
        self.player.revenue_history = [[self.kernel.cycle_count, 20000]]

    def test_vc_syndicate_application_and_repayment(self):
        """Test applying for VC funding, debt recording, and voluntary repayment."""
        # 1. Successful application for SOL_ANGEL (50,000 Cr, 1.20x mult = 60,000 Cr debt)
        init_credits = self.player.credits
        res = self.kernel.dispatch(self.player_id, ActionType.VC_APPLY, syndicate_id="SOL_ANGEL")
        self.assertTrue(res.success)
        self.assertEqual(self.player.vc_active_syndicate, "SOL_ANGEL")
        self.assertEqual(self.player.credits, init_credits + 50000)
        self.assertEqual(self.player.vc_debt, 60000)
        self.assertEqual(self.player.vc_royalty_pct, 6.0)
        self.assertEqual(self.player.vc_principal_paid, 0)

        # 2. Cannot take another VC note while debt is active
        res_fail = self.kernel.dispatch(self.player_id, ActionType.VC_APPLY, syndicate_id="AEGIS_VENTURES")
        self.assertFalse(res_fail.success)
        self.assertIn("Active venture covenant", res_fail.message)

        # 3. Partial manual repayment
        res_repay = self.kernel.dispatch(self.player_id, ActionType.VC_REPAY, amount=20000)
        self.assertTrue(res_repay.success)
        self.assertEqual(self.player.vc_debt, 40000)
        self.assertEqual(self.player.vc_principal_paid, 20000)

        # 4. Full repayment settlement
        res_settle = self.kernel.dispatch(self.player_id, ActionType.VC_REPAY, amount=50000)
        self.assertTrue(res_settle.success)
        self.assertEqual(self.player.vc_debt, 0)
        self.assertIsNone(self.player.vc_active_syndicate)
        self.assertEqual(self.player.vc_royalty_pct, 0.0)

    def test_vc_location_restriction(self):
        """Test that VC funding is only offered at Sector 1 Stardock."""
        self.player.sector_id = 10
        res = self.kernel.dispatch(self.player_id, ActionType.VC_APPLY, syndicate_id="AEGIS_VENTURES")
        self.assertFalse(res.success)
        self.assertIn("Sector 001 Stardock", res.message)

    def test_specialized_hull_commissioning_and_cargo_compatibility(self):
        """Test hull class commissioning and strict cargo compatibility validation."""
        # 1. Incompatible cargo: Cryo-Tanker cannot carry heavy structural metals (Iron)
        res_incompat = self.kernel.dispatch(
            self.player_id,
            ActionType.HAULER_COMMISSION,
            hull_class="CRYO_TANKER",
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="Fe",
            commodity_return="H2O",
        )
        self.assertFalse(res_incompat.success)
        self.assertIn("Outbound Cargo Incompatible", res_incompat.message)

        # 2. Compatible cargo: Cryo-Tanker carrying volatile liquids/gases (He-3 and H2O)
        res_compat = self.kernel.dispatch(
            self.player_id,
            ActionType.HAULER_COMMISSION,
            hull_class="CRYO_TANKER",
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="He-3",
            commodity_return="H2O",
            name="CryoHauler-01"
        )
        self.assertTrue(res_compat.success)
        hauler_data = res_compat.data.get("hauler", {})
        self.assertEqual(hauler_data.get("hull_class"), "CRYO_TANKER")
        self.assertEqual(hauler_data.get("capacity"), 80)
        hauler_id = hauler_data.get("id")

        # 3. Route reassignment compatibility validation
        res_reassign_fail = self.kernel.dispatch(
            self.player_id,
            ActionType.HAULER_ASSIGN_ROUTE,
            hauler_id=hauler_id,
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="AdL",  # Incompatible with CRYO_TANKER
            commodity_return="H2O",
        )
        self.assertFalse(res_reassign_fail.success)

        # 4. Valid route reassignment
        res_reassign_ok = self.kernel.dispatch(
            self.player_id,
            ActionType.HAULER_ASSIGN_ROUTE,
            hauler_id=hauler_id,
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="Xe",  # Compatible volatile gas
            commodity_return="H",    # Compatible volatile gas
        )
        self.assertTrue(res_reassign_ok.success)

    def test_hauler_escort_fighter_wings_and_recall(self):
        """Test assigning and recalling fighter wings and recalling haulers."""
        self.player.ship.fighters = 20
        res_comm = self.kernel.dispatch(
            self.player_id,
            ActionType.HAULER_COMMISSION,
            hull_class="STANDARD",
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="EQUIPMENT",
            commodity_return="ORGANICS",
        )
        self.assertTrue(res_comm.success)
        hauler_id = res_comm.data["hauler"]["id"]

        # Assign 5 escort fighters
        res_assign = self.kernel.dispatch(
            self.player_id,
            ActionType.FLEET_ASSIGN_ESCORT,
            hauler_id=hauler_id,
            count=5,
            mode="assign"
        )
        self.assertTrue(res_assign.success)
        self.assertEqual(self.player.ship.fighters, 15)
        hauler = self.kernel.market_manager.trade_haulers[hauler_id]
        self.assertEqual(hauler.escort_fighters, 5)

        # Recall 2 escort fighters
        res_recall_f = self.kernel.dispatch(
            self.player_id,
            ActionType.FLEET_ASSIGN_ESCORT,
            hauler_id=hauler_id,
            count=2,
            mode="recall"
        )
        self.assertTrue(res_recall_f.success)
        self.assertEqual(self.player.ship.fighters, 17)
        self.assertEqual(hauler.escort_fighters, 3)

        # Recall hauler to Sector 1
        res_recall_h = self.kernel.dispatch(
            self.player_id,
            ActionType.FLEET_RECALL,
            hauler_id=hauler_id,
            target_sector=1
        )
        self.assertTrue(res_recall_h.success)

    def test_hauler_scrapping_and_fighter_recovery(self):
        """Test decommission refund and recovery of deployed escort fighters."""
        self.player.ship.fighters = 10
        res_comm = self.kernel.dispatch(
            self.player_id,
            ActionType.HAULER_COMMISSION,
            hull_class="BULK_FREIGHTER",  # 18,000 Cr, 50% refund = 9,000 Cr
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="Fe",
            commodity_return="ORE",
        )
        self.assertTrue(res_comm.success)
        hauler_id = res_comm.data["hauler"]["id"]

        # Assign 4 fighters
        self.kernel.dispatch(self.player_id, ActionType.FLEET_ASSIGN_ESCORT, hauler_id=hauler_id, count=4, mode="assign")
        self.assertEqual(self.player.ship.fighters, 6)

        credits_before = self.player.credits
        res_decom = self.kernel.dispatch(self.player_id, ActionType.HAULER_DECOMMISSION, hauler_id=hauler_id)
        self.assertTrue(res_decom.success)
        self.assertEqual(self.player.credits, credits_before + 9000)
        self.assertEqual(self.player.ship.fighters, 10)  # Fighters safely returned to flagship
        self.assertNotIn(hauler_id, self.kernel.market_manager.trade_haulers)

    def test_hauler_autonomous_tick_and_vc_royalty_skim(self):
        """Test autonomous circuit trade yields and VC debt royalty amortization."""
        # Player secures 50,000 Cr from SOL_ANGEL (debt: 60,000 Cr, 6% royalty)
        self.kernel.dispatch(self.player_id, ActionType.VC_APPLY, syndicate_id="SOL_ANGEL")
        self.assertEqual(self.player.vc_debt, 60000)

        # Commission hauler between Sector 1 (Stardock) and the first starport beyond Sol
        res_comm = self.kernel.dispatch(
            self.player_id,
            ActionType.HAULER_COMMISSION,
            hull_class="STANDARD",
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="EQUIPMENT",
            commodity_return="ORGANICS",
        )
        hauler_id = res_comm.data["hauler"]["id"]
        hauler = self.kernel.market_manager.trade_haulers[hauler_id]
        hauler.current_path = []  # Set to terminal to trigger circuit trade

        # Run hauler tick
        logs = self.kernel.market_manager.tick_trade_haulers(self.kernel)
        self.assertGreater(hauler.lifetime_profit, 0)
        self.assertGreater(self.player.vc_principal_paid, 0)
        self.assertLess(self.player.vc_debt, 60000)

    def test_hierarchical_commodity_trading_and_cost_basis(self):
        """Test trading 24-element periodic commodities and manufactured components."""
        port = self.kernel.sectors[1].port  # Sector 1 buys and sells all commodities
        self.assertIsNotNone(port)
        self.player.ship.cargo.organics = 0  # empty hold (no starter rations) for exact hold math

        # 1. Buy granular structural metal: Titanium (Ti)
        res_buy_ti = EconomyManager.execute_buy(self.player, port, "Ti", 10)
        self.assertTrue(res_buy_ti.success)
        self.assertEqual(self.player.ship.cargo.elements.get("Ti"), 10)
        ti_price = res_buy_ti.data["unit_price"]
        self.assertEqual(self.player.ship.cargo.cost_basis.get("ti"), ti_price)

        # 2. Buy volatile gas: Helium-3 (He-3)
        res_buy_he3 = EconomyManager.execute_buy(self.player, port, "He-3", 5)
        self.assertTrue(res_buy_he3.success)
        self.assertEqual(self.player.ship.cargo.elements.get("He-3"), 5)

        # 3. Buy manufactured component: M1_SUPERCONDUCTOR
        res_buy_m1 = EconomyManager.execute_buy(self.player, port, "M1_SUPERCONDUCTOR", 2)
        self.assertTrue(res_buy_m1.success)
        self.assertEqual(self.player.ship.cargo.elements.get("M1_SUPERCONDUCTOR"), 2)

        # Total holds correctly counted
        self.assertEqual(self.player.ship.cargo.total_used, 10 + 5 + 2)

        # 4. Sell Titanium back to port
        res_sell_ti = EconomyManager.execute_sell(self.player, port, "Ti", 10)
        self.assertTrue(res_sell_ti.success)
        self.assertNotIn("Ti", self.player.ship.cargo.elements)
        self.assertEqual(self.player.ship.cargo.cost_basis.get("ti"), 0.0)

    def test_port_catalog_categorization(self):
        """Test get_port_catalog filtering by commodity category."""
        port = self.kernel.sectors[1].port
        cat_volatiles = EconomyManager.get_port_catalog(port, category="VOLATILES")
        for comm, data in cat_volatiles.items():
            self.assertEqual(data["category"], "VOLATILES")

        cat_metals = EconomyManager.get_port_catalog(port, category="METALS")
        for comm, data in cat_metals.items():
            self.assertEqual(data["category"], "METALS")

        cat_all = EconomyManager.get_port_catalog(port)
        self.assertGreater(len(cat_all), 20)

    def test_client_rendering_and_views(self):
        """Test terminal renderer for hierarchical trade, VC desk, and fleet console."""
        view = self.kernel.get_player_view(self.player_id)
        self.assertIn("trade_haulers", view)
        self.assertIn("vc_debt", view)
        self.assertIn("vc_syndicates", view)
        self.assertIn("specialized_hulls", view)

        # Render trade tabs
        trade_rendered = TerminalRenderer.render_trade_screen(view, active_category="1")
        self.assertIn("VOLATILES", trade_rendered)

        trade_rendered_metals = TerminalRenderer.render_trade_screen(view, active_category="2")
        self.assertIn("METALS", trade_rendered_metals)

        # Render VC desk
        vc_rendered = TerminalRenderer.render_vc_investment_desk(view)
        self.assertIn("INTERSTELLAR VENTURE CAPITAL DESK", vc_rendered)
        self.assertIn("Sol Guild Angel Syndicate", vc_rendered)

        # Render Fleet console
        fleet_rendered = TerminalRenderer.render_fleet_control_console(view)
        self.assertIn("MULTI-HAULER FLEET CONTROL CONSOLE", fleet_rendered)
        self.assertIn("COMMISSION SPECIALIZED HULL CLASSES", fleet_rendered)
        self.assertIn("[N]aval Security", fleet_rendered)
        self.assertIn("[D]erivative Hedge", fleet_rendered)

    def test_asteroid_harvester_lifecycle_and_offload(self):
        """Test commissioning Asteroid Harvester, resource extraction from belts, return transit, and port offload."""
        belt_sec = next((s for s in self.kernel.sectors.values() if s.belts and s.id != 1), None)
        if belt_sec is None:
            belt_sec = self.kernel.sectors[2]
            belt_sec.belts = [{"id": "BELT-002-1", "reserve": 500, "composition": {"ORE": 1.0}}]

        self.player.credits = 100000
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.HAULER_COMMISSION,
            hull_class="ASTEROID_HARVESTER",
            origin_sector=1,
            dest_sector=belt_sec.id,
            commodity_outbound="ORE",
            commodity_return="ORE",
            name="RockCrusher-1",
        )
        self.assertTrue(res.success, res.message)
        hid = res.data["hauler"]["id"]
        hauler = self.kernel.market_manager.trade_haulers[hid]
        self.assertEqual(hauler.hull_class, "ASTEROID_HARVESTER")
        self.assertEqual(hauler.capacity, 120)

        # 1. Simulate arrival at the asteroid belt extraction sector
        hauler.sector_id = belt_sec.id
        hauler.current_path = []
        logs = self.kernel.market_manager.tick_trade_haulers(self.kernel)
        self.assertIn("ORE", hauler.cargo)
        self.assertGreater(hauler.cargo["ORE"], 0)
        self.assertTrue(any("HARVESTER EXTRACTION" in l for l in logs))

        # 2. Simulate return to home spaceport at Sector 1
        initial_cr = self.player.credits
        hauler.sector_id = 1
        hauler.current_path = []
        logs_return = self.kernel.market_manager.tick_trade_haulers(self.kernel)
        self.assertEqual(hauler.cargo.get("ORE", 0), 0)  # Cargo offloaded
        self.assertGreater(hauler.lifetime_profit, 0)
        self.assertGreater(self.player.credits, initial_cr)
        self.assertTrue(any("HARVESTER OFFLOAD" in l for l in logs_return))
        # Turnaround path set back towards extraction destination
        self.assertEqual(hauler.status, "IN_TRANSIT")

    def test_deep_space_miner_lifecycle_and_offload(self):
        """Test Deep Space Miner ramscooping in unported deep space sectors, return transit, and port offload."""
        deep_sec = next((s for s in self.kernel.sectors.values() if s.id > 1 and not s.port and not s.belts), None)
        if deep_sec is None:
            deep_sec = self.kernel.sectors[max(self.kernel.sectors.keys())]
            deep_sec.port = None

        self.player.credits = 100000
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.HAULER_COMMISSION,
            hull_class="DEEP_SPACE_MINER",
            origin_sector=1,
            dest_sector=deep_sec.id,
            commodity_outbound="He-3",
            commodity_return="He-3",
            name="VoidScoop-1",
        )
        self.assertTrue(res.success, res.message)
        hid = res.data["hauler"]["id"]
        hauler = self.kernel.market_manager.trade_haulers[hid]
        self.assertTrue(hauler.wormhole_enabled)

        # 1. Simulate arrival in deep space sector
        hauler.sector_id = deep_sec.id
        hauler.current_path = []
        logs = self.kernel.market_manager.tick_trade_haulers(self.kernel)
        self.assertIn("He-3", hauler.cargo)
        self.assertGreater(hauler.cargo["He-3"], 0)
        self.assertTrue(any("DEEP SPACE MINER" in l for l in logs))

        # 2. Simulate return to origin sector 1
        initial_cr = self.player.credits
        hauler.sector_id = 1
        hauler.current_path = []
        logs_return = self.kernel.market_manager.tick_trade_haulers(self.kernel)
        self.assertEqual(hauler.cargo.get("He-3", 0), 0)
        self.assertGreater(hauler.lifetime_profit, 0)
        self.assertGreater(self.player.credits, initial_cr)
        self.assertTrue(any("HARVESTER OFFLOAD" in l for l in logs_return))

    def test_fleet_contract_security_escort(self):
        """Test contracting naval defense escort patrols (Levels 1-5) via kernel dispatch."""
        res_comm = self.kernel.dispatch(
            self.player_id,
            ActionType.HAULER_COMMISSION,
            hull_class="STANDARD",
            origin_sector=1,
            dest_sector=self.dest_port,
            commodity_outbound="EQUIPMENT",
            commodity_return="ORGANICS",
        )
        self.assertTrue(res_comm.success)
        hid = res_comm.data["hauler"]["id"]
        hauler = self.kernel.market_manager.trade_haulers[hid]

        # Contract Level 3 escort
        self.player.credits = 50000
        res_sec = self.kernel.dispatch(
            self.player_id,
            ActionType.FLEET_CONTRACT_SECURITY,
            hauler_id=hid,
            security_level=3,
        )
        self.assertTrue(res_sec.success, res_sec.message)
        self.assertEqual(hauler.security_escort, 3)
        cost = res_sec.data["cost"]
        self.assertEqual(cost, 7500)
        self.assertEqual(self.player.credits, 50000 - cost)

        # Invalid security level bounds
        res_sec_invalid = self.kernel.dispatch(
            self.player_id,
            ActionType.FLEET_CONTRACT_SECURITY,
            hauler_id=hid,
            security_level=6,
        )
        self.assertFalse(res_sec_invalid.success)

    def test_hedge_derivative_short_and_cover(self):
        """Test hedging long-haul fleet assets against depreciation via ISSE short sales and covers."""
        companies = list(self.kernel.market_manager.companies.values())
        self.assertTrue(len(companies) > 0)
        comp = companies[0]
        ticker = comp.ticker

        self.player.credits = 100000
        self.player.credit_rating = 600

        # 1. Short sell to hedge
        res_short = self.kernel.dispatch(
            self.player_id,
            ActionType.HEDGE_DERIVATIVE,
            company_ticker=ticker,
            shares=50,
            hedge_type="SHORT",
        )
        self.assertTrue(res_short.success, res_short.message)
        self.assertIn(ticker, self.player.short_positions)
        self.assertEqual(self.player.short_positions[ticker]["shares"], 50)

        # 2. Cover short position
        res_cover = self.kernel.dispatch(
            self.player_id,
            ActionType.HEDGE_DERIVATIVE,
            company_ticker=ticker,
            shares=50,
            hedge_type="COVER",
        )
        self.assertTrue(res_cover.success, res_cover.message)
        self.assertEqual(self.player.short_positions.get(ticker, {}).get("shares", 0), 0)


if __name__ == "__main__":
    unittest.main()
