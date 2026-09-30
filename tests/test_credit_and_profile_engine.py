"""
Comprehensive unit and integration test suite for:
- Captain Profile, Credit Rating (FICO 300-850), and Experience Score (Ξ)
- Social Cohesion & Faction Reputation Vector (Federation, Corporate, Pirate, Indigenous)
- Computational Financial Risk Engine: Dynamic Net Equity & Borrowing Capacity
- Gated Institutional Financing: VC Syndicates with Dynamic Risk-Priced Multipliers & Royalties
- Gated Advanced Economics: Hostile Corporate Takeovers & Dynamic Margin Short Selling
- Surface District Periodic Element Catalysis & Autonomous Colony Governor Automation
- Terminal ANSI Dossier & Dynamic Investment Desk UI Renderers
"""

import unittest
from xylarium.config import (
    VC_SYNDICATES,
    TAKEOVER_MIN_CREDIT,
    TAKEOVER_MIN_EXP,
    SHORT_MIN_CREDIT,
    CREDIT_TIER_THRESHOLDS,
)
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Captain, Planet
from xylarium.kernel.surface import SurfaceManager, DistrictType, TerrainType
from xylarium.client.renderer import TerminalRenderer


class TestCreditAndProfileEngine(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.player_id = "test_player"
        self.player = self.kernel.register_player(self.player_id, "Captain Sterling")
        self.player.sector_id = 1
        self.player.credits = 10000

    def test_captain_profile_initialization_and_helpers(self):
        """Verify initial credit rating, experience score, and boundary clamping."""
        self.assertEqual(self.player.credit_rating, 500)
        self.assertEqual(self.player.experience_score, 100)
        self.assertEqual(self.player.credit_tier, "SUBPRIME")
        self.assertEqual(self.player.faction_reputation["Federation"], 50.0)
        self.assertEqual(self.player.loan_repayment_history, 0)
        self.assertEqual(self.player.freight_deliveries_completed, 0)

        # Clamping bounds: 300 to 850
        self.player.adjust_credit_rating(500)
        self.assertEqual(self.player.credit_rating, 850)
        self.assertEqual(self.player.credit_tier, "PRIME_ALPHA")

        self.player.adjust_credit_rating(-1000)
        self.assertEqual(self.player.credit_rating, 300)
        self.assertEqual(self.player.credit_tier, "DISTRESSED")

        # Experience and reputation
        self.player.adjust_experience(50)
        self.assertEqual(self.player.experience_score, 150)
        self.player.adjust_experience(-500)
        self.assertEqual(self.player.experience_score, 0)

        self.player.adjust_reputation("Corporate", 30.0)
        self.assertEqual(self.player.faction_reputation["Corporate"], 80.0)
        self.player.adjust_reputation("Corporate", 50.0)
        self.assertEqual(self.player.faction_reputation["Corporate"], 100.0)

    def test_captain_profile_serialization(self):
        """Test to_dict and from_dict round-trip preservation."""
        self.player.credit_rating = 720
        self.player.experience_score = 450
        self.player.loan_repayment_history = 4
        self.player.freight_deliveries_completed = 12
        self.player.default_history = 1
        self.player.faction_reputation["Federation"] = 85.5

        data = self.player.to_dict()
        self.assertEqual(data["credit_rating"], 720)
        self.assertEqual(data["credit_tier"], "TIER_1_SECURE")
        self.assertEqual(data["experience_score"], 450)
        self.assertEqual(data["loan_repayment_history"], 4)
        self.assertEqual(data["freight_deliveries_completed"], 12)
        self.assertEqual(data["default_history"], 1)

        restored = Captain.from_dict(data)
        self.assertEqual(restored.credit_rating, 720)
        self.assertEqual(restored.credit_tier, "TIER_1_SECURE")
        self.assertEqual(restored.experience_score, 450)
        self.assertEqual(restored.loan_repayment_history, 4)
        self.assertEqual(restored.freight_deliveries_completed, 12)
        self.assertEqual(restored.default_history, 1)
        self.assertEqual(restored.faction_reputation["Federation"], 85.5)

    def test_net_equity_calculation(self):
        """Verify dynamic mark-to-market Net Equity calculation across multiple asset classes."""
        mm = self.kernel.market_manager
        # Initial: credits (10,000) + ship price (Scout = 0/default 1000 min) = 11,000
        equity = mm.calculate_net_equity(self.player, self.kernel)
        self.assertGreaterEqual(equity, 10000)

        # Buy shares to increase equity
        self.player.credits = 50000
        self.kernel.dispatch(self.player_id, ActionType.STOCK_BUY, ticker="ADME", amount=500)
        equity_with_shares = mm.calculate_net_equity(self.player, self.kernel)
        self.assertGreaterEqual(equity_with_shares, 49000)

        # Add debt liability
        self.player.debt = 20000
        equity_with_debt = mm.calculate_net_equity(self.player, self.kernel)
        self.assertLess(equity_with_debt, equity_with_shares)

    def test_dynamic_borrowing_terms_risk_pricing(self):
        """Verify dynamic borrowing terms vary with credit rating and Net Equity."""
        mm = self.kernel.market_manager
        self.player.credits = 100000

        # Liquidity alone is not a track record: facilities are sized to realized revenue
        terms_no_history = mm.calculate_borrowing_terms(self.player, "SOL_ANGEL", self.kernel)
        self.assertFalse(terms_no_history["eligible"])
        self.assertEqual(terms_no_history["trailing_revenue"], 0)

        self.player.revenue_history = [[self.kernel.cycle_count, 20000]]

        # Baseline credit score 500
        terms_500 = mm.calculate_borrowing_terms(self.player, "SOL_ANGEL", self.kernel)
        self.assertTrue(terms_500["eligible"])
        self.assertLessEqual(terms_500["facility_ceiling"], 20000 * 3)
        self.assertEqual(terms_500["multiplier"], 1.20)
        self.assertEqual(terms_500["royalty_pct"], 6.0)

        # Prime credit score 750
        self.player.credit_rating = 750
        terms_750 = mm.calculate_borrowing_terms(self.player, "SOL_ANGEL", self.kernel)
        self.assertGreater(terms_750["max_borrowing_power"], terms_500["max_borrowing_power"])
        self.assertLess(terms_750["multiplier"], terms_500["multiplier"])
        self.assertLess(terms_750["royalty_pct"], terms_500["royalty_pct"])

        # Subprime credit score 350
        self.player.credit_rating = 350
        terms_350 = mm.calculate_borrowing_terms(self.player, "SOL_ANGEL", self.kernel)
        self.assertFalse(terms_350["eligible"])  # SOL_ANGEL requires min CR 450
        self.assertGreater(terms_350["royalty_pct"], terms_500["royalty_pct"])

    def test_vc_syndicate_gated_prerequisites(self):
        """Verify institutional VC syndicates enforce credit and experience gates."""
        # 1. Novice player (CR 500, Exp 100) attempts to access AEGIS_VENTURES (requires CR 600, Exp 200)
        res_aegis = self.kernel.dispatch(self.player_id, ActionType.VC_APPLY, syndicate_id="AEGIS_VENTURES")
        self.assertFalse(res_aegis.success)
        self.assertIn("requires a minimum Credit Rating of 600", res_aegis.message)

        # 2. Player with high CR (750) but insufficient experience (100 < 500) rejected by VOSS_CAPITAL
        self.player.credit_rating = 750
        res_voss = self.kernel.dispatch(self.player_id, ActionType.VC_APPLY, syndicate_id="VOSS_CAPITAL")
        self.assertFalse(res_voss.success)
        self.assertIn("requires an established commercial track record", res_voss.message)

        # 3. A rookie with cash but no revenue history or rank authority is sized out
        self.player.credits = 250000
        self.player.experience_score = 600
        res_rookie = self.kernel.dispatch(self.player_id, ActionType.VC_APPLY, syndicate_id="VOSS_CAPITAL")
        self.assertFalse(res_rookie.success)

        # 4. Qualified player (Tier 3 authority, proven trailing revenue) secures VOSS_CAPITAL
        self.player.rank_tier = 3
        self.player.revenue_history = [[self.kernel.cycle_count, 100000]]
        res_voss_ok = self.kernel.dispatch(self.player_id, ActionType.VC_APPLY, syndicate_id="VOSS_CAPITAL")
        self.assertTrue(res_voss_ok.success)
        self.assertEqual(self.player.vc_active_syndicate, "VOSS_CAPITAL")
        self.assertGreater(self.player.vc_debt, 0)

        # 5. Discharge debt awards credit score, experience, and reputation
        init_cr = self.player.credit_rating
        init_exp = self.player.experience_score
        res_repay = self.kernel.dispatch(self.player_id, ActionType.VC_REPAY, amount=self.player.vc_debt)
        self.assertTrue(res_repay.success)
        self.assertEqual(self.player.vc_debt, 0)
        self.assertEqual(self.player.credit_rating, min(850, init_cr + 35))
        self.assertGreater(self.player.experience_score, init_exp)
        self.assertEqual(self.player.loan_repayment_history, 1)

    def test_gated_hostile_takeover_enforcement(self):
        """Hostile takeovers are locked out without institutional credit and experience standing."""
        adme = self.kernel.market_manager.companies["ADME"]
        majority_shares = (adme.total_shares // 2) + 100
        self.player.portfolio["ADME"] = majority_shares

        # Novice standing: CR 500, Exp 100, Net Equity 10,000 Cr (< 250,000 Cr)
        self.player.credit_rating = 500
        self.player.experience_score = 100
        self.player.credits = 1000

        res_coup = self.kernel.dispatch(self.player_id, ActionType.CORPORATE_TAKEOVER, ticker="ADME")
        self.assertFalse(res_coup.success)
        self.assertIn("ISSE REGULATORY LOCKOUT", res_coup.message)
        self.assertNotEqual(adme.chairman_id, self.player_id)

        # Elevate standing to qualify: CR >= 650, Exp >= 500
        self.player.credit_rating = 650
        self.player.experience_score = 500
        res_coup_ok = self.kernel.dispatch(self.player_id, ActionType.CORPORATE_TAKEOVER, ticker="ADME")
        self.assertTrue(res_coup_ok.success)
        self.assertEqual(adme.chairman_id, self.player_id)
        self.assertIn("MAJORITY SHAREHOLDER COUP", self.kernel.event_bus.get_recent_radio(1)[0].text)

    def test_gated_short_selling_and_dynamic_margin(self):
        """Short selling requires minimum credit score and scales collateral margin ratio."""
        adme = self.kernel.market_manager.companies["ADME"]

        # Distressed credit rating (< 450) locked out
        self.player.credit_rating = 350
        res_fail = self.kernel.dispatch(self.player_id, ActionType.STOCK_SHORT, ticker="ADME", amount=100)
        self.assertFalse(res_fail.success)
        self.assertIn("ISSE MARGIN DESK LOCKOUT", res_fail.message)

        # Restored credit rating (750 Prime) allows shorting with reduced margin collateral (25%)
        self.player.credit_rating = 750
        self.player.credits = 50000
        price = adme.share_price
        amount = 100
        gross_value = amount * price
        expected_margin = int(gross_value * 0.25)  # 25% margin for Prime

        res_ok = self.kernel.dispatch(self.player_id, ActionType.STOCK_SHORT, ticker="ADME", amount=amount)
        self.assertTrue(res_ok.success)
        pos = self.player.short_positions["ADME"]
        self.assertEqual(pos["collateral"], expected_margin)

    def test_surface_district_catalysis_and_governor_automation(self):
        """Test periodic element reserve catalysis and autonomous governor deficit reaction."""
        sec = self.kernel.sectors[1]
        planet = Planet(
            id="p_auto_colony",
            sector_id=1,
            name="New Carthage",
            owner_id=self.player_id,
            treasury=15000,
            organics_silo=0,  # Unclosed ration deficit!
            ore_silo=50,
            element_reserves={"H2O": 10, "Fe": 10},
        )
        sec.planets.append(planet)

        # 1. Tick surface: Autonomous governor must detect organics deficit and zone Hydroponic Spire
        SurfaceManager.tick_surface(planet)
        grid = SurfaceManager.ensure_surface_grid(planet)
        has_hydro = any(t.district == DistrictType.HYDROPONIC_SPIRE for t in grid.tiles)
        self.assertTrue(has_hydro)
        self.assertLess(planet.treasury, 15000)

        # 2. Catalysis: Second tick with active Hydroponic Spire should consume H2O to boost organics
        initial_h2o = planet.element_reserves["H2O"]
        SurfaceManager.tick_surface(planet)
        self.assertLess(planet.element_reserves["H2O"], initial_h2o)
        self.assertGreater(planet.organics_silo, 0)

    def test_ui_renderers(self):
        """Verify Captain Dossier and Dynamic VC desk screens render without exception."""
        view = self.kernel.get_player_view(self.player_id)

        # Dossier view
        dossier_text = TerminalRenderer.render_captain_profile_screen(view)
        self.assertIn("CAPTAIN DOSSIER & FINANCIAL INTEGRITY PROFILE", dossier_text)
        self.assertIn("Credit Rating:", dossier_text)
        self.assertIn("NET SOVEREIGN EQUITY", dossier_text)
        self.assertIn("SOCIAL COHESION & FACTION REPUTATION", dossier_text)

        # VC desk view
        vc_text = TerminalRenderer.render_vc_investment_desk(view)
        self.assertIn("INTERSTELLAR VENTURE CAPITAL DESK", vc_text)
        self.assertIn("INSTITUTIONAL SYNDICATES", vc_text)


if __name__ == "__main__":
    unittest.main()
