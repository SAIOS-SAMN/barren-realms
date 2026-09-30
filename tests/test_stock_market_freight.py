"""
Unit tests for the Interstellar Securities & Stock Exchange (ISSE),
Population-Founded Enterprises, and Galactic Freight Haulage Engine.
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType
from xylarium.kernel.market import Company, FreightContract, MarketManager, FISCAL_QUARTER_CYCLES
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer


class TestStockMarketAndFreight(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=1337)
        self.player_id = "test_player"
        self.captain = self.kernel.register_player(self.player_id, "Captain Enterprise")
        self.captain.credits = 100000

    def test_stock_market_initialization(self):
        """Verify ISSE initializes with flagship corporations across sectors."""
        mgr = self.kernel.market_manager
        self.assertGreaterEqual(len(mgr.companies), 5)
        self.assertIn("VOSS", mgr.companies)
        self.assertIn("ADME", mgr.companies)
        self.assertIn("SHBI", mgr.companies)

        voss = mgr.companies["VOSS"]
        self.assertEqual(voss.ticker, "VOSS")
        self.assertEqual(voss.industry, "MANUFACTURING")
        self.assertGreater(voss.share_price, 0)
        self.assertGreater(voss.available_shares, 0)
        self.assertGreater(voss.market_cap, 0)

    def test_stock_market_buy_shares(self):
        """Verify buying shares deducts credits, credits portfolio, and updates market."""
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.STOCK_BUY,
            ticker="VOSS",
            amount=200,
        )
        self.assertTrue(res.success)
        self.assertEqual(self.captain.portfolio.get("VOSS"), 200)
        self.assertLess(self.captain.credits, 100000)

        # Float reduced
        voss = self.kernel.market_manager.companies["VOSS"]
        self.assertEqual(voss.available_shares, 15000 - 200)

    def test_stock_market_buy_shares_insufficient_credits(self):
        """Buying more shares than affordable fails without deducting credits."""
        self.captain.credits = 10
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.STOCK_BUY,
            ticker="VOSS",
            amount=500,
        )
        self.assertFalse(res.success)
        self.assertEqual(self.captain.credits, 10)
        self.assertEqual(self.captain.portfolio.get("VOSS", 0), 0)

    def test_stock_market_sell_shares(self):
        """Liquidating shares returns net credits after 2% fee and restores float."""
        # First buy shares
        self.kernel.dispatch(self.player_id, ActionType.STOCK_BUY, ticker="ADME", amount=100)
        credits_after_buy = self.captain.credits

        adme = self.kernel.market_manager.companies["ADME"]
        price = adme.share_price

        res = self.kernel.dispatch(self.player_id, ActionType.STOCK_SELL, ticker="ADME", amount=50)
        self.assertTrue(res.success)
        self.assertEqual(self.captain.portfolio.get("ADME"), 50)

        # Verify net proceeds
        expected_gross = price * 50
        expected_fee = max(1, int(expected_gross * 0.02))
        expected_net = expected_gross - expected_fee
        self.assertEqual(self.captain.credits, credits_after_buy + expected_net)

    def test_colony_ipo_founding(self):
        """Player governor can float an IPO on a Citadel Tier 1+ colony to raise capital."""
        sec = next(s for s in self.kernel.sectors.values() if s.planets)
        planet = sec.planets[0]
        planet.owner_id = self.player_id
        planet.citadel_level = 1
        self.captain.sector_id = sec.id
        self.captain.credits = 10000
        planet.treasury = 5000

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.COMPANY_IPO,
            planet_id=planet.id,
            name="Avalon Mantle Corp",
            ticker="AMCR",
            industry="MINING",
        )
        self.assertTrue(res.success)
        self.assertIn("AMCR", self.kernel.market_manager.companies)

        # Founder holds 6,000 shares (60% majority)
        self.assertEqual(self.captain.portfolio.get("AMCR"), 6000)
        # Planet treasury credited with raised capital infusion
        self.assertGreater(planet.treasury, 5000)

    def test_colony_ipo_restrictions(self):
        """IPO fails if not sovereign governor or colony is unfortified."""
        sec = next(s for s in self.kernel.sectors.values() if s.planets)
        planet = sec.planets[0]
        planet.owner_id = "ai_malakor"
        self.captain.sector_id = sec.id

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.COMPANY_IPO,
            planet_id=planet.id,
            name="Rogue Enterprise",
            ticker="ROG",
            industry="MINING",
        )
        self.assertFalse(res.success)
        self.assertIn("sovereign governor", res.message)

    def test_population_enterprises_spawning(self):
        """Planets with population >= 600 organically form commercial corporations."""
        mgr = self.kernel.market_manager
        # Set a planet with high population
        sec = self.kernel.sectors[42]
        if not sec.planets:
            from xylarium.kernel.models import Planet
            sec.planets.append(Planet(id="planet_42", sector_id=42, name="Terranova", population=800))
        else:
            sec.planets[0].population = 800

        created = mgr.spawn_population_enterprises(self.kernel)
        self.assertGreater(len(created), 0)

    def test_freight_contract_lifecycle(self):
        """Test complete freight haulage: generation, acceptance, transport, and delivery."""
        mgr = self.kernel.market_manager
        new_contracts = mgr.generate_freight_contracts(self.kernel)
        self.assertGreater(len(new_contracts), 0)

        contract = new_contracts[0]
        cid = contract.id

        # Move captain to origin sector
        self.captain.sector_id = contract.origin_sector
        self.captain.ship.cargo.capacity = 100
        self.captain.ship.cargo.ore = 0
        self.captain.ship.cargo.organics = 0
        self.captain.ship.cargo.equipment = 0

        # 1. Accept contract
        res = self.kernel.dispatch(self.player_id, ActionType.FREIGHT_ACCEPT, contract_id=cid)
        self.assertTrue(res.success)
        self.assertIn(cid, self.captain.active_contracts)
        self.assertEqual(contract.status, "IN_TRANSIT")

        # Verify bonded cargo placed in hold
        comm = contract.commodity.upper()
        if comm == "ORE":
            self.assertGreaterEqual(self.captain.ship.cargo.ore, contract.amount)
        elif comm == "ORGANICS":
            self.assertGreaterEqual(self.captain.ship.cargo.organics, contract.amount)
        elif comm == "EQUIPMENT":
            self.assertGreaterEqual(self.captain.ship.cargo.equipment, contract.amount)

        # 2. Travel to destination sector
        self.captain.sector_id = contract.destination_sector
        dest_planet = next(
            p for p in self.kernel.sectors[contract.destination_sector].planets
            if p.id == contract.destination_planet_id
        )

        initial_credits = self.captain.credits
        initial_shares = self.captain.portfolio.get(contract.company_ticker, 0)

        # 3. Deliver contract
        res_del = self.kernel.dispatch(
            self.player_id,
            ActionType.FREIGHT_DELIVER,
            contract_id=cid,
            planet_id=dest_planet.id,
        )
        self.assertTrue(res_del.success)
        self.assertNotIn(cid, self.captain.active_contracts)
        self.assertEqual(contract.status, "COMPLETED")

        # Payout and equity shares credited
        self.assertEqual(self.captain.credits, initial_credits + contract.payout_credits)
        self.assertEqual(
            self.captain.portfolio.get(contract.company_ticker, 0),
            initial_shares + contract.shares_reward,
        )

    def test_freight_acceptance_checks(self):
        """Acceptance fails if not at origin sector or cargo holds full."""
        mgr = self.kernel.market_manager
        contracts = mgr.generate_freight_contracts(self.kernel)
        contract = contracts[0]

        # Put captain in a different sector
        self.captain.sector_id = contract.origin_sector + 1
        res = self.kernel.dispatch(self.player_id, ActionType.FREIGHT_ACCEPT, contract_id=contract.id)
        self.assertFalse(res.success)
        self.assertIn("Must be docked", res.message)

    def test_quarterly_dividend_distribution(self):
        """Quarterly dividend tick disburses credits to shareholders every 25 cycles."""
        # Buy shares in Voss; its home colony buys goods from it out of a healthy vault
        self.kernel.dispatch(self.player_id, ActionType.STOCK_BUY, ticker="VOSS", amount=500)
        voss = self.kernel.market_manager.companies["VOSS"]
        home = self.kernel.get_planet(voss.planet_id)
        home.treasury = 400000
        vault_before = home.treasury
        credits_before = self.captain.credits

        # Advance cycle to 25
        self.kernel.cycle_count = 25
        market_tick = self.kernel.market_manager.tick_market(self.kernel)

        self.assertTrue(market_tick["is_quarter_end"])
        self.assertGreater(market_tick["dividends_paid"], 0)
        self.assertGreater(self.captain.credits, credits_before)
        # Corporate income is a transfer from the colony, not minted
        self.assertLess(home.treasury, vault_before)

    def test_market_state_persistence(self):
        """Market companies and captain portfolio persist across save/load."""
        import tempfile
        import os

        self.kernel.dispatch(self.player_id, ActionType.STOCK_BUY, ticker="VOSS", amount=150)
        self.kernel.cycle_count = 14

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            filepath = tf.name

        try:
            saved = StatePersistence.save_to_file(self.kernel, filepath)
            self.assertTrue(saved)
            restored_kernel = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(restored_kernel)

            restored_cap = restored_kernel.get_player(self.player_id)
            self.assertEqual(restored_cap.portfolio.get("VOSS"), 150)
            self.assertIn("VOSS", restored_kernel.market_manager.companies)
            self.assertEqual(
                restored_kernel.market_manager.companies["VOSS"].share_price,
                self.kernel.market_manager.companies["VOSS"].share_price,
            )
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_market_screen_renderers(self):
        """Verify terminal screen renderers execute cleanly without formatting exceptions."""
        view = self.kernel.get_player_view(self.player_id)
        stock_scr = TerminalRenderer.render_stock_market_screen(view)
        freight_scr = TerminalRenderer.render_freight_board_screen(view)

        self.assertIn("INTERSTELLAR SECURITIES & STOCK EXCHANGE", stock_scr)
        self.assertIn("VOSS", stock_scr)
        self.assertIn("GALACTIC FREIGHT HAULAGE", freight_scr)


if __name__ == "__main__":
    unittest.main()
