"""
Unit and integration tests for the Full-Spectrum Rank & Clade Progression Matrix,
Clade-Specific Starting Profiles, Ship Hull Gating, and Federal Defense Turret Interception.
"""

import unittest
from xylarium.config import PHYLOGENY_TIER_EXPERIENCE
import os
from xylarium.config import (
    CLADE_RANK_MATRIX,
    STARTING_BACKGROUNDS,
    RANK_PROMOTION_THRESHOLDS,
    SHIP_CATALOG,
    VC_SYNDICATES,
)
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import (
    Captain,
    ActionType,
    SecurityLevel,
)
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer


class TestCladeRankMatrix(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.player_id = "test_commander"

    def test_clade_matrix_configuration_integrity(self):
        """Verifies that all 5 clades exist and contain 4 progression tiers each."""
        expected_clades = ["BIOTIC", "ANARCHY", "PLASMIC", "LITHIC", "CRYOGENIC"]
        for c in expected_clades:
            self.assertIn(c, CLADE_RANK_MATRIX)
            clade_data = CLADE_RANK_MATRIX[c]
            self.assertIn("tiers", clade_data)
            self.assertEqual(len(clade_data["tiers"]), 4)

            # Check Tier 1 and Tier 4 titles
            t1 = clade_data["tiers"][1]["title"]
            t4 = clade_data["tiers"][4]["title"]
            self.assertTrue(len(t1) > 0)
            self.assertTrue(len(t4) > 0)

        # Specific canonical titles
        self.assertEqual(CLADE_RANK_MATRIX["BIOTIC"]["tiers"][1]["title"], "Scrap-Apprentice")
        self.assertEqual(CLADE_RANK_MATRIX["BIOTIC"]["tiers"][4]["title"], "Galactic Archon")
        self.assertEqual(CLADE_RANK_MATRIX["ANARCHY"]["tiers"][1]["title"], "Void Drifter")
        self.assertEqual(CLADE_RANK_MATRIX["ANARCHY"]["tiers"][4]["title"], "Shadow Hegemon")
        self.assertEqual(CLADE_RANK_MATRIX["PLASMIC"]["tiers"][1]["title"], "Spark-Bound")
        self.assertEqual(CLADE_RANK_MATRIX["PLASMIC"]["tiers"][4]["title"], "Corona Sovereign")
        self.assertEqual(CLADE_RANK_MATRIX["LITHIC"]["tiers"][1]["title"], "Core-Driller")
        self.assertEqual(CLADE_RANK_MATRIX["LITHIC"]["tiers"][4]["title"], "Litharch")
        self.assertEqual(CLADE_RANK_MATRIX["CRYOGENIC"]["tiers"][1]["title"], "Zero-Kelvin Novice")
        self.assertEqual(CLADE_RANK_MATRIX["CRYOGENIC"]["tiers"][4]["title"], "Absolute Zero Mind")

    def test_starting_backgrounds_initialization(self):
        """Verifies starting bottom-feeder backgrounds initialize with custom ships, debts, and sectors."""
        # 1. Scrapper (Biotic)
        p_scrapper = self.kernel.register_player("p_scrapper", "Scrapper Jax", background="scrapper")
        self.assertEqual(p_scrapper.clade, "BIOTIC")
        self.assertEqual(p_scrapper.rank_tier, 1)
        self.assertEqual(p_scrapper.rank_title, "Scrap-Apprentice")
        self.assertEqual(p_scrapper.credits, 800)
        self.assertEqual(p_scrapper.debt, 500)
        self.assertEqual(p_scrapper.ship.cargo.capacity, 30)

        # 2. Void Drifter (Anarchy)
        p_outlaw = self.kernel.register_player("p_outlaw", "Renegade Vex", background="void_drifter")
        self.assertEqual(p_outlaw.clade, "ANARCHY")
        self.assertEqual(p_outlaw.rank_tier, 1)
        self.assertEqual(p_outlaw.rank_title, "Void Drifter")
        self.assertEqual(p_outlaw.credits, 400)
        self.assertEqual(p_outlaw.debt, 1000)
        self.assertEqual(p_outlaw.bounty, 500)
        self.assertEqual(p_outlaw.sector_id, 75)  # Starts out in deep void
        self.assertEqual(p_outlaw.ship.shields, 75)

        # 3. Core Driller (Lithic)
        p_lith = self.kernel.register_player("p_lith", "Driller Stone", background="core_driller")
        self.assertEqual(p_lith.clade, "LITHIC")
        self.assertEqual(p_lith.rank_title, "Core-Driller")
        self.assertEqual(p_lith.ship.cargo.capacity, 40)
        self.assertEqual(p_lith.debt, 800)

        # 4. Zero Kelvin (Cryogenic)
        p_cryo = self.kernel.register_player("p_cryo", "Rime Novice", background="zero_kelvin")
        self.assertEqual(p_cryo.clade, "CRYOGENIC")
        self.assertEqual(p_cryo.rank_title, "Zero-Kelvin Novice")
        self.assertEqual(p_cryo.credits, 700)
        self.assertEqual(p_cryo.debt, 600)

    def test_rank_promotion_invariant_checks_and_ascension(self):
        """Verifies promotion qualification checks and progression through all 4 tiers."""
        player = self.kernel.register_player(self.player_id, "Captain Solo", clade="BIOTIC")
        self.assertEqual(player.rank_tier, 1)
        self.assertEqual(player.rank_title, "Scrap-Apprentice")

        # 1. Initially cannot promote to Tier 2 (insufficient crystals, exp, cr)
        can_p, msg, info = player.can_promote(self.kernel)
        self.assertFalse(can_p)
        self.assertIn("locked", msg.lower())
        self.assertGreater(len(info["reasons"]), 0)

        # Attempting dispatch fails
        res_fail = self.kernel.dispatch(self.player_id, ActionType.RANK_PROMOTE)
        self.assertFalse(res_fail.success)
        self.assertEqual(player.rank_tier, 1)

        # 2. Fulfill Tier 2 criteria: exp >= tier-2 pacing gate, credit_rating >= 540, crystals >= 1, debt-to-equity <= 1.0
        player.experience_score = PHYLOGENY_TIER_EXPERIENCE[2] + 50
        player.credit_rating = 580
        player.grown_basis.append({"rcf_sig": "RCF-01", "name": "Basis Crystal Alpha"})
        player.debt = 0

        can_p, msg, info = player.can_promote(self.kernel)
        self.assertTrue(can_p)
        self.assertIn("Eligible for ascension", msg)

        # Promote to Tier 2
        res_t2 = self.kernel.dispatch(self.player_id, ActionType.RANK_PROMOTE)
        self.assertTrue(res_t2.success)
        self.assertEqual(player.rank_tier, 2)
        self.assertEqual(player.rank_title, "Journeyman Hauler")
        self.assertIn("Journeyman Hauler", res_t2.message)
        # Verify endowment rewards
        self.assertGreaterEqual(player.credits, 1500 + 2500)

        # 3. Promote to Tier 3: Corporate Director
        # Needs: exp >= tier-3 pacing gate, credit_rating >= 660, crystals >= 3, net_equity >= 50000, rep >= 65.0
        player.experience_score = PHYLOGENY_TIER_EXPERIENCE[3] + 100
        player.credit_rating = 680
        player.credits = 60000
        player.grown_basis.append({"rcf_sig": "RCF-02", "name": "Basis Crystal Beta"})
        player.grown_basis.append({"rcf_sig": "RCF-03", "name": "Basis Crystal Gamma"})
        player.faction_reputation["Federation"] = 70.0

        res_t3 = self.kernel.dispatch(self.player_id, ActionType.RANK_PROMOTE)
        self.assertTrue(res_t3.success)
        self.assertEqual(player.rank_tier, 3)
        self.assertEqual(player.rank_title, "Corporate Director")

        # 4. Promote to Tier 4: Galactic Archon
        # Needs: exp >= 1500, credit_rating >= 760, crystals >= 6, net_equity >= 200000, rep >= 80.0
        player.experience_score = PHYLOGENY_TIER_EXPERIENCE[4] + 100
        player.credit_rating = 780
        player.credits = 250000
        player.grown_basis.extend([
            {"rcf_sig": "RCF-04", "name": "Crystal 4"},
            {"rcf_sig": "RCF-05", "name": "Crystal 5"},
            {"rcf_sig": "RCF-06", "name": "Crystal 6"},
        ])
        player.faction_reputation["Federation"] = 85.0

        res_t4 = self.kernel.dispatch(self.player_id, ActionType.RANK_PROMOTE)
        self.assertTrue(res_t4.success)
        self.assertEqual(player.rank_tier, 4)
        self.assertEqual(player.rank_title, "Galactic Archon")

        # 5. At Tier 4, already max rank
        can_p, msg, info = player.can_promote(self.kernel)
        self.assertFalse(can_p)
        self.assertTrue(info["max_rank"])
        res_max = self.kernel.dispatch(self.player_id, ActionType.RANK_PROMOTE)
        self.assertFalse(res_max.success)
        self.assertIn("Apex Sovereign", res_max.message)

    def test_shipyard_hull_tier_gating(self):
        """Verifies that Federal Shipyard gates hull upgrades behind rank tiers."""
        player = self.kernel.register_player(self.player_id, "Commander Shepard", clade="BIOTIC")
        player.sector_id = 1
        player.credits = 100000
        self.assertEqual(player.rank_tier, 1)

        # 1. Tier 1 player cannot commission Merchant Cruiser (requires Tier 2)
        res_mc_fail = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Merchant Cruiser")
        self.assertFalse(res_mc_fail.success)
        self.assertIn("requires Rank Tier 2 authorization", res_mc_fail.message)
        self.assertEqual(player.ship.ship_type, "Scout Ship")

        # 2. Promote to Tier 2
        player.rank_tier = 2
        res_mc_ok = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Merchant Cruiser")
        self.assertTrue(res_mc_ok.success)
        self.assertEqual(player.ship.ship_type, "Merchant Cruiser")
        self.assertEqual(player.ship.cargo.capacity, 60)

        # 3. Cannot commission Star Frigate (requires Tier 3)
        res_frigate_fail = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Star Frigate")
        self.assertFalse(res_frigate_fail.success)
        self.assertIn("requires Rank Tier 3 authorization", res_frigate_fail.message)

        # 4. Promote to Tier 3 -> commission Star Frigate
        player.rank_tier = 3
        res_frigate_ok = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Star Frigate")
        self.assertTrue(res_frigate_ok.success)
        self.assertEqual(player.ship.ship_type, "Star Frigate")

        # 5. Cannot commission Dreadnought Battlecruiser (requires Tier 4)
        res_dread_fail = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Dreadnought Battlecruiser")
        self.assertFalse(res_dread_fail.success)
        self.assertIn("requires Rank Tier 4 authorization", res_dread_fail.message)

        # 6. Promote to Tier 4 -> commission Dreadnought
        player.rank_tier = 4
        res_dread_ok = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Dreadnought Battlecruiser")
        self.assertTrue(res_dread_ok.success)
        self.assertEqual(player.ship.ship_type, "Dreadnought Battlecruiser")
        self.assertEqual(player.ship.cargo.capacity, 180)

    def test_federal_defense_turret_engagement_and_transponder_forgery(self):
        """Verifies Federal defense turrets engage outlaw signatures unless bypassed by forged transponder."""
        outlaw = self.kernel.register_player(self.player_id, "Blackbeard", background="void_drifter")
        self.assertEqual(outlaw.clade, "ANARCHY")
        self.assertEqual(outlaw.rank_title, "Void Drifter")
        self.assertFalse(outlaw.forged_transponder)

        # Move to Sector 1 (Federal Stardock)
        outlaw.sector_id = 1
        outlaw.ship.shields = 100
        sec1 = self.kernel.sectors[1]

        # 1. Trading at Federation port triggers automated defense turrets
        res_trade_blocked = self.kernel.dispatch(
            self.player_id,
            ActionType.TRADE,
            type="BUY",
            commodity="ORE",
            amount=5,
        )
        self.assertFalse(res_trade_blocked.success)
        self.assertIn("Federal automated defense turrets detected an unauthorized outlaw signature", res_trade_blocked.message)
        # Defense turrets inflicted 25 damage
        self.assertEqual(outlaw.ship.shields, 75)

        # 2. Accessing shipyard or bank also repelled by turrets
        res_shipyard_blocked = self.kernel.dispatch(
            self.player_id,
            ActionType.SHIPYARD_PURCHASE,
            item="shields",
        )
        self.assertFalse(res_shipyard_blocked.success)
        self.assertEqual(outlaw.ship.shields, 50)

        # 3. Forging a spoofed Federal Transponder Chit in Cartography Lab
        outlaw.credits = 5000
        outlaw.cartography_fragments.append({
            "fragment_id": "FRAG-TEST",
            "name": "Starmap Fragment 01",
            "sector_source": 10,
        })

        res_forge = self.kernel.dispatch(
            self.player_id,
            ActionType.CARTOGRAPHY_FORGE_CHIT,
            mode="transponder",
        )
        self.assertTrue(res_forge.success)
        self.assertTrue(outlaw.forged_transponder)
        self.assertIn("FORGED_TRANSPONDER", outlaw.unlocked_secrets)
        self.assertIn("spoofed Federal Transponder Chit", res_forge.message)

        # 4. Now that transponder is spoofed, defense turrets stand down
        res_trade_ok = self.kernel.dispatch(
            self.player_id,
            ActionType.TRADE,
            type="BUY",
            commodity="ORE",
            amount=5,
        )
        self.assertTrue(res_trade_ok.success)
        # Shields did not take damage
        self.assertEqual(outlaw.ship.shields, 50)
        self.assertEqual(outlaw.ship.cargo.ore, 5)

    def test_clade_serialization_and_persistence(self):
        """Verifies clade attributes and rank status are fully serialized to/from JSON."""
        player = self.kernel.register_player(self.player_id, "Coronal Pyre", background="spark_bound")
        player.rank_tier = 2
        player.forged_transponder = True
        player.unlocked_secrets.append("FORGED_TRANSPONDER")

        p_dict = player.to_dict()
        self.assertEqual(p_dict["clade"], "PLASMIC")
        self.assertEqual(p_dict["rank_tier"], 2)
        self.assertEqual(p_dict["rank_title"], "Flux Warden")
        self.assertEqual(p_dict["background"], "spark_bound")
        self.assertTrue(p_dict["forged_transponder"])

        # Reconstruct from dict
        reconstructed = Captain.from_dict(p_dict)
        self.assertEqual(reconstructed.clade, "PLASMIC")
        self.assertEqual(reconstructed.rank_tier, 2)
        self.assertEqual(reconstructed.rank_title, "Flux Warden")
        self.assertTrue(reconstructed.forged_transponder)

        # Test full universe save/load
        save_file = "test_clade_save.json"
        try:
            StatePersistence.save_to_file(self.kernel, save_file)
            loaded_kernel = StatePersistence.load_from_file(save_file)
            loaded_player = loaded_kernel.get_player(self.player_id)
            self.assertIsNotNone(loaded_player)
            self.assertEqual(loaded_player.clade, "PLASMIC")
            self.assertEqual(loaded_player.rank_tier, 2)
            self.assertEqual(loaded_player.rank_title, "Flux Warden")
            self.assertTrue(loaded_player.forged_transponder)
        finally:
            if os.path.exists(save_file):
                os.remove(save_file)

    def test_renderer_profile_and_hud_output(self):
        """Verifies HUD and Captain Profile screen render dynamic rank badges and ascension status."""
        player = self.kernel.register_player(self.player_id, "Glacial Mind", background="zero_kelvin")
        view = self.kernel.get_player_view(self.player_id)

        hud_output = TerminalRenderer.render_hud(view)
        self.assertIn("Zero-Kelvin Novice", hud_output)
        self.assertIn("T1", hud_output)

        profile_output = TerminalRenderer.render_captain_profile_screen(view)
        self.assertIn("Zero-Kelvin Novice", profile_output)
        self.assertIn("CRYOGENIC", profile_output)
        self.assertIn("CLADE RANK PROGRESSION & INVARIANT ASCENSION MATRIX", profile_output)
        self.assertIn("[P]romote Rank", profile_output)


if __name__ == "__main__":
    unittest.main()
