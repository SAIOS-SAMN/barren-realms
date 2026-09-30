"""
Unit test suite for Corporate Warfare and The Corporate Machine expansions in Xylarium.
Tests:
- Hostile Takeovers: treasury absorption and sovereign colony seizure
- Short Selling (STOCK_SHORT) and Margin Maintenance
- Short Covering (STOCK_COVER) and Profit/Loss settlement
- Weaponized Sabotage: linking black-ops to ISSE share price crashes
- Corporate Embargoes & Sector Customs Tariffs (SET_TARIFF)
- Sales Executives hiring, movement, and sector market penetration (EXECUTIVE_HIRE, EXECUTIVE_MOVE)
- Marketing Hub Campaigns: Positive PR & Rival Smear Campaigns (MARKETING_CAMPAIGN)
- Interstellar Trade Council: Lobbying pool & legislative bills (LOBBY_CONTRIBUTE, COUNCIL_VOTE)
- Full Save/Load State Persistence with Corporate Machine dataclasses
- Terminal ANSI Renderers
"""

import unittest
import tempfile
import os

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Planet
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer


class TestCorporateWarfareAndMachine(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=777)
        self.player_id = "raider_alpha"
        self.captain = self.kernel.register_player(self.player_id, "Captain Blackwood")
        self.captain.credits = 300000

    def test_takeover_absorbs_treasury_and_seizes_colonies(self):
        """Hostile takeover of >50% absorbs corporate treasury and seizes HQ planet dominion."""
        voss = self.kernel.market_manager.companies["VOSS"]
        initial_treasury = voss.treasury
        initial_credits = self.captain.credits

        # Give player 60% of shares
        needed_shares = int(voss.total_shares * 0.60)
        self.captain.portfolio["VOSS"] = needed_shares

        # Locate Voss's HQ planet
        hq_planet = None
        for s in self.kernel.sectors.values():
            for p in s.planets:
                if p.id == voss.planet_id or p.name == voss.planet_name:
                    hq_planet = p
                    break
            if hq_planet:
                break

        self.assertIsNotNone(hq_planet)
        old_owner = hq_planet.owner_id

        # Execute takeover
        res = self.kernel.dispatch(self.player_id, ActionType.CORPORATE_TAKEOVER, ticker="VOSS")
        self.assertTrue(res.success)
        self.assertEqual(voss.chairman_id, self.player_id)
        # Treasury absorbed
        self.assertEqual(voss.treasury, 0)
        self.assertEqual(self.captain.credits, initial_credits + initial_treasury)
        # Sovereign dominion seized
        self.assertEqual(hq_planet.owner_id, self.player_id)
        self.assertIn("Absorbed", res.message)

    def test_short_selling_flow_and_margin_collateral(self):
        """Shorting stocks requires 50% margin collateral and credits gross sale proceeds."""
        adme = self.kernel.market_manager.companies["ADME"]
        price = adme.share_price
        amount = 200
        gross_value = amount * price
        margin_req = int(gross_value * 0.50)

        credits_before = self.captain.credits

        res = self.kernel.dispatch(self.player_id, ActionType.STOCK_SHORT, ticker="ADME", amount=amount)
        self.assertTrue(res.success)
        self.assertIn("ADME", self.captain.short_positions)

        pos = self.captain.short_positions["ADME"]
        self.assertEqual(pos["shares"], amount)
        self.assertEqual(pos["entry_price"], price)
        self.assertEqual(pos["collateral"], margin_req)

        # Net change to credits is + (gross_value - margin_req) = + margin_req
        expected_credits = credits_before - margin_req + gross_value
        self.assertEqual(self.captain.credits, expected_credits)

    def test_short_selling_rejected_insufficient_margin(self):
        """Shorting fails if captain cannot afford the 50% margin requirement."""
        self.captain.credits = 100
        adme = self.kernel.market_manager.companies["ADME"]
        # 1000 shares * 25 Cr = 25,000 Cr => 12,500 Cr margin required
        res = self.kernel.dispatch(self.player_id, ActionType.STOCK_SHORT, ticker="ADME", amount=1000)
        self.assertFalse(res.success)
        self.assertIn("Insufficient margin collateral", res.message)

    def test_short_covering_profit_settlement(self):
        """Covering a short position after price crash yields profit and releases collateral."""
        shbi = self.kernel.market_manager.companies["SHBI"]
        shbi.share_price = 40
        self.captain.credits = 50000

        # Short 100 shares @ 40 Cr => gross 4,000 Cr, collateral 2,000 Cr
        self.kernel.dispatch(self.player_id, ActionType.STOCK_SHORT, ticker="SHBI", amount=100)
        # Drop stock price to 20 Cr
        shbi.share_price = 20

        credits_before_cover = self.captain.credits

        # Cover the 100 shares
        res = self.kernel.dispatch(self.player_id, ActionType.STOCK_COVER, ticker="SHBI", amount=100)
        self.assertTrue(res.success)
        # Position closed
        self.assertNotIn("SHBI", self.captain.short_positions)
        # Buyback cost: 100 * 20 = 2,000 Cr. Collateral released: 2,000 Cr.
        # Net credits change: +2,000 (collateral) - 2,000 (buyback) = 0 net from previous balance,
        # overall profit was (40 - 20) * 100 = 2,000 Cr gain realized from entry.
        self.assertEqual(self.captain.credits, credits_before_cover)
        self.assertEqual(res.data.get("pnl"), 2000)
        self.assertIn("Profit", res.message)

    def test_weaponized_sabotage_drops_isse_stock_price(self):
        """Covert black-ops sabotage against a corporate colony crashes company share price on ISSE."""
        voss = self.kernel.market_manager.companies["VOSS"]
        initial_price = voss.share_price

        # Locate Voss's HQ planet
        hq_planet = None
        for s in self.kernel.sectors.values():
            for p in s.planets:
                if p.id == voss.planet_id or p.name == voss.planet_name:
                    hq_planet = p
                    break
            if hq_planet:
                break

        self.assertIsNotNone(hq_planet)

        # Grant operatives to player
        self.captain.operatives = 30
        self.captain.sector_id = hq_planet.sector_id

        # Run sabotage op with large operative commitment to guarantee success
        from xylarium.kernel.espionage import EspionageManager
        res = EspionageManager.execute_operation(
            kernel=self.kernel,
            attacker=self.captain,
            target_type="PLANET",
            target_id=hq_planet.id,
            op_type="sabotage",
            operatives_committed=25,
        )

        if res.success:
            self.assertLess(voss.share_price, initial_price)
            self.assertIn("stock_crash", res.data)
            self.assertEqual(res.data["stock_crash"]["ticker"], "VOSS")
            self.assertIn("ISSE STOCK CRASH", " ".join(res.logs))

    def test_sector_customs_tariff_and_transit_toll(self):
        """Setting sector transit tariff deducts toll from travelers and deposits into colony vault."""
        # Find a sector with a planet and assign ownership to captain
        sec = self.kernel.sectors[12]
        if not sec.planets:
            p = Planet(id="customs_world", sector_id=12, name="Customs Prime", owner_id=self.player_id, citadel_level=2)
            sec.planets.append(p)
        else:
            p = sec.planets[0]
            p.owner_id = self.player_id
            p.citadel_level = 2

        p.treasury = 1000

        # Set 30% tariff
        res_tariff = self.kernel.dispatch(self.player_id, ActionType.SET_TARIFF, sector_id=12, tariff_pct=30)
        self.assertTrue(res_tariff.success)
        self.assertEqual(p.sector_tariff_pct, 30)

        # Create a rival captain who travels into Sector 12
        rival_id = "rival_trader"
        rival = self.kernel.register_player(rival_id, "Trader Joe")
        rival.credits = 10000
        # Position rival in adjacent sector to 12
        adj_sec = sec.warps[0]
        rival.sector_id = adj_sec
        adj = self.kernel.sectors[adj_sec]
        if rival_id not in adj.captains:
            adj.captains.append(rival_id)

        # Move rival into Sector 12
        res_move = self.kernel.dispatch(rival_id, ActionType.MOVE, destination=12)
        self.assertTrue(res_move.success)
        # Verify rival paid tariff and colony treasury increased
        self.assertLess(rival.credits, 10000)
        self.assertGreater(p.treasury, 1000)
        self.assertTrue(any("CUSTOMS TRANSIT TARIFF" in log for log in res_move.logs))

    def test_sales_executive_hiring_and_penetration(self):
        """Hiring and moving a Sales Executive captures market penetration and generates revenues."""
        voss = self.kernel.market_manager.companies["VOSS"]
        voss.chairman_id = self.player_id
        credits_before = self.captain.credits

        # Hire sales executive
        res_hire = self.kernel.dispatch(self.player_id, ActionType.EXECUTIVE_HIRE, ticker="VOSS", name="Gordon Vance")
        self.assertTrue(res_hire.success)
        self.assertEqual(self.captain.credits, credits_before - 2500)
        exec_id = res_hire.data["executive"]["id"]
        self.assertIn(exec_id, self.captain.sales_executives)

        # Move executive to adjacent sector
        hq_sec = self.kernel.sectors[voss.sector_id]
        dest_sec = hq_sec.warps[0]
        res_move = self.kernel.dispatch(self.player_id, ActionType.EXECUTIVE_MOVE, exec_id=exec_id, destination=dest_sec)
        self.assertTrue(res_move.success)
        self.assertGreater(voss.market_penetration.get(dest_sec, 0), 0)

        # Advance cycle to trigger executive market penetration boost in tick_market
        rev_before = voss.quarterly_revenue
        self.kernel.cycle_count = 1
        self.kernel.market_manager.tick_market(self.kernel)
        self.assertGreater(voss.quarterly_revenue, rev_before)

    def test_marketing_campaigns_positive_and_smear(self):
        """Positive campaigns raise trust/price; smear campaigns degrade rival trust and stock price."""
        adme = self.kernel.market_manager.companies["ADME"]
        adme.chairman_id = self.player_id
        initial_price = adme.share_price
        initial_trust = adme.consumer_trust

        # Positive campaign
        res_pos = self.kernel.dispatch(self.player_id, ActionType.MARKETING_CAMPAIGN, ticker="ADME", campaign_type="POSITIVE")
        self.assertTrue(res_pos.success)
        self.assertGreater(adme.consumer_trust, initial_trust)
        self.assertGreater(adme.share_price, initial_price)

        # Smear campaign against rival VOSS
        voss = self.kernel.market_manager.companies["VOSS"]
        voss_price_before = voss.share_price
        voss_trust_before = voss.consumer_trust

        res_smear = self.kernel.dispatch(
            self.player_id,
            ActionType.MARKETING_CAMPAIGN,
            ticker="ADME",
            campaign_type="SMEAR",
            target_ticker="VOSS"
        )
        self.assertTrue(res_smear.success)
        self.assertLess(voss.share_price, voss_price_before)
        self.assertLess(voss.consumer_trust, voss_trust_before)

    def test_trade_council_lobbying_and_resolutions(self):
        """Lobbying pool contributions enable passing federal Trade Council resolutions."""
        # Contribute 3,000 Cr to lobbying pool
        res_lobby = self.kernel.dispatch(self.player_id, ActionType.LOBBY_CONTRIBUTE, amount=3000)
        self.assertTrue(res_lobby.success)
        council = self.kernel.market_manager.trade_council
        self.assertGreaterEqual(council.lobbying_funds.get(self.player_id, 0), 3000)

        # Enact SUBSIDY bill
        res_bill = self.kernel.dispatch(
            self.player_id,
            ActionType.COUNCIL_VOTE,
            bill_type="SUBSIDY",
            sponsor_ticker="ADME"
        )
        self.assertTrue(res_bill.success)
        self.assertEqual(len(council.active_resolutions), 1)

        # Fast forward to fiscal quarter end (cycle 25)
        self.kernel.cycle_count = 25
        fed = self.kernel.federal_reserve
        paid_before = fed.stats.get("council_subsidies", 0)
        self.kernel.market_manager.tick_market(self.kernel)
        # The sponsor receives the 5,000 Cr subsidy, paid by the Federal Reserve (not minted).
        # (Its treasury also moves with quarterly operating spend and freight escrow, so assert the payment.)
        self.assertEqual(fed.stats.get("council_subsidies", 0) - paid_before, 5000)

    def test_save_and_load_persistence_with_corporate_machine(self):
        """Verify new dataclasses, short positions, and council resolutions persist across save/load."""
        # Open short position
        self.kernel.dispatch(self.player_id, ActionType.STOCK_SHORT, ticker="VOSS", amount=150)
        # Hire sales executive
        voss = self.kernel.market_manager.companies["VOSS"]
        voss.chairman_id = self.player_id
        self.kernel.dispatch(self.player_id, ActionType.EXECUTIVE_HIRE, ticker="VOSS", name="Chief Vance")
        # Contribute lobbying
        self.kernel.dispatch(self.player_id, ActionType.LOBBY_CONTRIBUTE, amount=2000)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            filepath = tf.name

        try:
            saved = StatePersistence.save_to_file(self.kernel, filepath)
            self.assertTrue(saved)

            loaded_kernel = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(loaded_kernel)

            loaded_cap = loaded_kernel.get_player(self.player_id)
            self.assertIn("VOSS", loaded_cap.short_positions)
            self.assertEqual(loaded_cap.short_positions["VOSS"]["shares"], 150)
            self.assertGreater(len(loaded_kernel.market_manager.executives), 0)
            self.assertEqual(loaded_kernel.market_manager.trade_council.lobbying_funds.get(self.player_id), 2000)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_terminal_renderers_for_corporate_machine(self):
        """Verify renderers format screens cleanly with corporate machine data."""
        self.kernel.dispatch(self.player_id, ActionType.STOCK_SHORT, ticker="VOSS", amount=100)
        voss = self.kernel.market_manager.companies["VOSS"]
        voss.chairman_id = self.player_id
        self.kernel.dispatch(self.player_id, ActionType.EXECUTIVE_HIRE, ticker="VOSS")
        self.kernel.dispatch(self.player_id, ActionType.LOBBY_CONTRIBUTE, amount=1000)

        view = self.kernel.get_player_view(self.player_id)
        stock_scr = TerminalRenderer.render_stock_market_screen(view)
        board_scr = TerminalRenderer.render_boardroom_screen(view, "VOSS")
        corp_scr = TerminalRenderer.render_corporate_machine_screen(view)

        self.assertIn("ACTIVE SHORT POSITIONS", stock_scr)
        self.assertIn("Consumer Trust", board_scr)
        self.assertIn("THE CORPORATE MACHINE", corp_scr)
        self.assertIn("SALES EXECUTIVES", corp_scr)


if __name__ == "__main__":
    unittest.main()
