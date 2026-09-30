"""
Unit test suite for Hostile Corporate Takeovers, Boardroom Governance,
Poison Pill Defenses, and Proxy Fights in Xylarium.
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType
from xylarium.client.renderer import TerminalRenderer


class TestCorporateTakeoversSuite(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.player_id = "raider_1"
        self.captain = self.kernel.register_player(self.player_id, "Gordon Gekko")
        self.captain.credits = 500000

    def test_takeover_rejected_without_majority(self):
        """Takeover fails if player owns <= 50.0% of total shares."""
        # Buy only 1,000 shares of ADME (out of 20,000 = 5%)
        self.kernel.dispatch(self.player_id, ActionType.STOCK_BUY, ticker="ADME", amount=1000)
        res = self.kernel.dispatch(self.player_id, ActionType.CORPORATE_TAKEOVER, ticker="ADME")

        self.assertFalse(res.success)
        self.assertIn("majority stake (>50.0%)", res.message)
        adme = self.kernel.market_manager.companies["ADME"]
        self.assertNotEqual(adme.chairman_id, self.player_id)

    def test_takeover_succeeds_with_majority(self):
        """Holding >50% of shares allows successful hostile coup, ousting incumbent chairman."""
        company = self.kernel.market_manager.companies["ADME"]
        # Grant majority ownership
        needed = (company.total_shares // 2) + 100
        self.captain.portfolio["ADME"] = needed

        res = self.kernel.dispatch(self.player_id, ActionType.CORPORATE_TAKEOVER, ticker="ADME")
        self.assertTrue(res.success)
        self.assertEqual(company.chairman_id, self.player_id)
        self.assertIn("HOSTILE TAKEOVER SUCCESSFUL", res.message)
        self.assertGreaterEqual(self.captain.score, 1500)

    def test_cynthia_voss_retaliation_on_takeover(self):
        """Hostile takeover of Voss Heavy Industries (VOSS) triggers corporate bounty retaliation."""
        voss = self.kernel.market_manager.companies["VOSS"]
        initial_bounty = getattr(self.captain, "bounty", 0)

        # Grant majority stake in VOSS
        majority = (voss.total_shares // 2) + 1
        self.captain.portfolio["VOSS"] = majority

        res = self.kernel.dispatch(self.player_id, ActionType.CORPORATE_TAKEOVER, ticker="VOSS")
        self.assertTrue(res.success)
        self.assertEqual(voss.chairman_id, self.player_id)
        # Verify Cynthia Voss placed a 15,000 Cr bounty
        self.assertEqual(self.captain.bounty, initial_bounty + 15000)
        self.assertIn("corporate espionage bounty", res.message)

    def test_board_special_dividend(self):
        """Executive Chairman can disburse a 30% special dividend from company treasury."""
        comp = self.kernel.market_manager.companies["ADME"]
        comp.chairman_id = self.player_id
        comp.treasury = 50000
        self.captain.portfolio["ADME"] = comp.total_shares  # 100% owner for clean math
        credits_before = self.captain.credits

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.BOARD_VOTE,
            ticker="ADME",
            mandate="SPECIAL_DIVIDEND",
        )
        self.assertTrue(res.success)
        expected_div = int(50000 * 0.30)
        self.assertEqual(comp.treasury, 35000)
        self.assertEqual(self.captain.credits, credits_before + expected_div)
        self.assertEqual(comp.special_dividends_paid, expected_div)

    def test_board_restructure_industry(self):
        """Executive Chairman can reassign corporate core industry."""
        comp = self.kernel.market_manager.companies["ADME"]
        comp.chairman_id = self.player_id
        self.assertEqual(comp.industry, "MINING")

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.BOARD_VOTE,
            ticker="ADME",
            mandate="CHANGE_INDUSTRY",
            industry="EXOTIC_ELEMENTS",
        )
        self.assertTrue(res.success)
        self.assertEqual(comp.industry, "EXOTIC_ELEMENTS")

    def test_board_corporate_embargo(self):
        """Executive Chairman can declare a corporate embargo against a rival captain."""
        comp = self.kernel.market_manager.companies["ADME"]
        comp.chairman_id = self.player_id

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.BOARD_VOTE,
            ticker="ADME",
            mandate="CORPORATE_EMBARGO",
            target_id="ai_malakor",
        )
        self.assertTrue(res.success)
        self.assertIn("ai_malakor", comp.embargoed_captains)

        # Verify embargoed captain cannot accept contracts from ADME
        from xylarium.kernel.market import FreightContract
        test_c = FreightContract(
            id="FRT-999",
            company_ticker="ADME",
            issuer_name="Avalon Mantle",
            origin_sector=1,
            origin_name="Stardock",
            destination_sector=2,
            destination_planet_id="planet_2",
            destination_name="World 2",
            commodity="ORE",
            amount=5,
            payout_credits=500,
            shares_reward=5,
            hazard_level="FEDERATION",
            created_cycle=1,
            expiry_cycle=50,
        )
        self.kernel.market_manager.contracts["FRT-999"] = test_c

        malakor = self.kernel.get_player("ai_malakor")
        malakor.sector_id = 1
        malakor.ship.cargo.capacity = 100

        res_acc = self.kernel.dispatch("ai_malakor", ActionType.FREIGHT_ACCEPT, contract_id="FRT-999")
        self.assertFalse(res_acc.success)
        self.assertIn("Corporate Embargo", res_acc.message)

    def test_board_strip_assets(self):
        """Executive Chairman can extract 25% treasury as Chairman bonus, depressing stock price."""
        comp = self.kernel.market_manager.companies["ADME"]
        comp.chairman_id = self.player_id
        comp.treasury = 40000
        initial_price = comp.share_price
        initial_credits = self.captain.credits

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.BOARD_VOTE,
            ticker="ADME",
            mandate="STRIP_ASSETS",
        )
        self.assertTrue(res.success)
        loot = int(40000 * 0.25)
        self.assertEqual(comp.treasury, 30000)
        self.assertEqual(self.captain.credits, initial_credits + loot)
        self.assertEqual(comp.share_price, initial_price - 2)

    def test_non_chairman_cannot_call_board_vote(self):
        """Non-chairman captain is denied access to board mandates."""
        comp = self.kernel.market_manager.companies["VOSS"]
        self.assertNotEqual(comp.chairman_id, self.player_id)

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.BOARD_VOTE,
            ticker="VOSS",
            mandate="SPECIAL_DIVIDEND",
        )
        self.assertFalse(res.success)
        self.assertIn("Access Denied", res.message)

    def test_proxy_fight_victory(self):
        """Proxy fight succeeds when player owns >=25% and sentiment backs the challenger."""
        comp = self.kernel.market_manager.companies["SHBI"]
        # Give player 40% equity
        self.captain.portfolio["SHBI"] = int(comp.total_shares * 0.40)
        # Give company poor dividend history to rally public shares
        comp.last_dividend = 1
        comp.contracts_failed = 2
        self.captain.credits = 10000

        res = self.kernel.dispatch(self.player_id, ActionType.PROXY_FIGHT, ticker="SHBI")
        self.assertTrue(res.success)
        self.assertEqual(comp.chairman_id, self.player_id)
        self.assertIn("PROXY FIGHT VICTORY", res.message)

    def test_poison_pill_defense(self):
        """Poison pill mints 25% dilutive shares, reducing hostile raider percentage."""
        voss = self.kernel.market_manager.companies["VOSS"]
        initial_total = voss.total_shares

        res = self.kernel.dispatch(
            "ai_voss",
            ActionType.POISON_PILL,
            ticker="VOSS",
        )
        self.assertTrue(res.success)
        expected_new_total = initial_total + int(initial_total * 0.25)
        self.assertEqual(voss.total_shares, expected_new_total)
        self.assertTrue(voss.poison_pill_active)
        self.assertEqual(voss.poison_pill_uses, 0)

    def test_boardroom_renderer(self):
        """Verify render_boardroom_screen formats data cleanly."""
        view = self.kernel.get_player_view(self.player_id)
        scr = TerminalRenderer.render_boardroom_screen(view, "VOSS")
        self.assertIn("ISSE CORPORATE BOARDROOM", scr)
        self.assertIn("Voss Heavy Industries", scr)
        self.assertIn("EQUITY & VOTING POWER", scr)


if __name__ == "__main__":
    unittest.main()
