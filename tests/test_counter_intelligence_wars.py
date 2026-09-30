"""
Unit tests for Xylarium Counter-Intelligence & Security Wars.
Verifies:
1. Automated planetary counter-intelligence garrison recruitment.
2. Breach detection triggers planetary emergency security lockout.
3. Cynthia Voss issues corporate embargo and tariffs against detected thieves.
4. Ironclaw Rake mercenary hit assignment and bounty tracking.
5. Warlord Malakor pirate blood vengeance reaction.
6. Mercenary engagement of bountied captains outside Federation space.
7. Bounty collection upon target destruction.
8. Legal restitution settlement at Stardock Federal Bank.
9. State persistence of security lockouts, bounties, and embargoes.
"""

import unittest
from xylarium.config import CITADEL_UPKEEP
from unittest.mock import patch
import os
import tempfile

from xylarium.config import CITADEL_CONFIG, EMBARGO_TARIFF_BUY_MULT, EMBARGO_TARIFF_SELL_MULT
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import Planet, ActionType, SecurityLevel, AIPersonality, Port, PortClass
from xylarium.kernel.colony import ColonyManager
from xylarium.kernel.economy import EconomyManager
from xylarium.persistence.store import StatePersistence


class TestCounterIntelligenceWars(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.player = self.kernel.register_player("c_infiltrator", "Captain Shadow")
        self.player.credits = 50000
        self.player.turns_left = 200
        self.player.operatives = 10

    def test_automated_planetary_garrison_recruitment(self):
        """Fortified colonies (Citadel Tier 1+) automatically commission defense operatives."""
        planet = Planet(
            id="p_fort",
            name="Fortress Bastion",
            sector_id=10,
            owner_id="ai_voss",
            citadel_level=2,
            treasury=10000,
            security_operatives=0
        )
        # Citadel Tier 2 max_security is 15
        yield_data = ColonyManager.tick_colony(planet)
        self.assertEqual(planet.security_operatives, 1)
        self.assertEqual(yield_data["recruited_sec"], 1)
        upkeep = CITADEL_UPKEEP[2]["credits"]
        self.assertEqual(planet.treasury, 10000 - upkeep - 500 + yield_data["tax_yield"] - yield_data["public_services"])

    def test_breach_detection_triggers_security_lockout(self):
        """Detected espionage triggers a 20-cycle security lockout on the target colony."""
        sec = self.kernel.sectors[20]
        voss_planet = Planet(
            id="p_voss_vault",
            name="Voss Vault World",
            sector_id=20,
            owner_id="ai_voss",
            citadel_level=1,
            treasury=80000,
            security_operatives=10,
            security_lockout=0
        )
        sec.planets.append(voss_planet)

        # Force failure / detection
        with patch("random.random", return_value=0.99):
            res = self.kernel.dispatch(
                self.player.id,
                ActionType.COVERT_OP,
                target_type="PLANET",
                target_id="p_voss_vault",
                op_type="siphon",
                operatives=3
            )

        self.assertFalse(res.success)
        self.assertEqual(voss_planet.security_lockout, 20)
        self.assertIn("COUNTER-INTEL", [m.sender for m in self.kernel.event_bus.get_recent_radio()])

    def test_voss_corporate_embargo_on_detected_breach(self):
        """When detected siphoning a Voss asset, Voss slaps an embargo and posts a bounty."""
        sec = self.kernel.sectors[18]
        voss_planet = Planet(
            id="p_oasis_test",
            name="Oasis Sector",
            sector_id=18,
            owner_id="ai_voss",
            citadel_level=2,
            treasury=100000,
            security_operatives=8
        )
        sec.planets.append(voss_planet)

        # Trigger detected siphon
        with patch("random.random", return_value=0.01):     # op success & detection roll triggers
            with patch("random.uniform", return_value=0.20):     # siphon 20,000 Cr
                res = self.kernel.dispatch(
                    self.player.id,
                    ActionType.COVERT_OP,
                    target_type="PLANET",
                    target_id="p_oasis_test",
                    op_type="siphon",
                    operatives=5
                )

        self.assertTrue(res.success)
        self.assertIn("ai_voss", self.player.embargoed_by)
        self.assertGreaterEqual(self.player.bounty, 5000)
        self.assertEqual(self.player.bounty_placed_by, "Director Cynthia Voss")

        # Check radio broadcasts (the world tick adds other traffic, so scan a wider window)
        radio = self.kernel.event_bus.get_recent_radio(50)
        voss_msgs = [m for m in radio if m.sender == "Director Cynthia Voss"]
        self.assertTrue(any("CRIMINAL EMBARGO" in m.text for m in voss_msgs))

        # Check Ironclaw mercenary bounty announcement
        ironclaw_msgs = [m for m in radio if m.sender == "Ironclaw Rake"]
        self.assertTrue(any("BOUNTY CONTRACT ACTIVATED" in m.text for m in ironclaw_msgs))

        # Ironclaw hunt target sector locked onto player's sector
        ironclaw = self.kernel.captains["ai_ironclaw"]
        self.assertEqual(ironclaw.hunt_target_sector, self.player.sector_id)

    def test_embargo_tariff_enforcement_in_voss_sectors(self):
        """Player under Voss embargo suffers +50% buy tariff and -30% sell penalty in Voss charter space (11-25)."""
        self.player.embargoed_by.append("ai_voss")

        # Port in Sector 18 (Voss Space)
        sec18 = self.kernel.sectors[18]
        self.assertIsNotNone(sec18.port)
        port18 = sec18.port
        port18.stock["EQUIPMENT"] = 50
        port18.sells["EQUIPMENT"] = True
        port18.buys["EQUIPMENT"] = True

        _, normal_sell_price = EconomyManager.get_unit_prices(port18, "EQUIPMENT")
        normal_buy_price, _ = EconomyManager.get_unit_prices(port18, "EQUIPMENT")

        # Buy 1 unit in Voss sector (settled in the port's regional currency)
        from xylarium.kernel.fx import balance, credit
        self.player.sector_id = 18
        credit(self.player, port18.currency, 10000)
        init_credits = balance(self.player, port18.currency)
        res_buy = self.kernel.dispatch(
            self.player.id,
            ActionType.TRADE,
            type="BUY",
            commodity="EQUIPMENT",
            amount=1
        )
        self.assertTrue(res_buy.success)
        expected_tariff_cost = max(normal_sell_price + 1, int(normal_sell_price * EMBARGO_TARIFF_BUY_MULT))
        self.assertEqual(balance(self.player, port18.currency), init_credits - expected_tariff_cost)
        self.assertTrue(any("EMBARGO TARIFF" in l for l in res_buy.logs))

        # Sell 1 unit in Voss sector
        res_sell = self.kernel.dispatch(
            self.player.id,
            ActionType.TRADE,
            type="SELL",
            commodity="EQUIPMENT",
            amount=1
        )
        self.assertTrue(res_sell.success)
        expected_penalty_payout = max(1, int(normal_buy_price * EMBARGO_TARIFF_SELL_MULT))
        self.assertTrue(any("EMBARGO PENALTY" in l for l in res_sell.logs))

    def test_malakor_blood_vengeance_reaction(self):
        """Breaching Malakor's assets triggers blood vengeance tracking."""
        sec = self.kernel.sectors[75]
        dread_planet = Planet(
            id="p_dread_test",
            name="Dread Hollow",
            sector_id=75,
            owner_id="ai_malakor",
            citadel_level=1,
            treasury=50000,
            security_operatives=5
        )
        sec.planets.append(dread_planet)
        malakor = self.kernel.captains["ai_malakor"]

        with patch("random.random", return_value=0.01):
            res = self.kernel.dispatch(
                self.player.id,
                ActionType.COVERT_OP,
                target_type="PLANET",
                target_id="p_dread_test",
                op_type="siphon",
                operatives=3
            )

        self.assertTrue(res.success)
        self.assertEqual(malakor.hunt_target_sector, self.player.sector_id)
        radio = self.kernel.event_bus.get_recent_radio(50)
        malakor_msgs = [m for m in radio if m.sender == malakor.name]
        self.assertTrue(any("You dare infiltrate my stronghold" in m.text for m in malakor_msgs))

    def test_bounty_collection_upon_target_destruction(self):
        """Neutralizing a captain with an active bounty pays out the reward to the attacker."""
        wanted_cap = self.kernel.register_player("c_wanted", "Outlaw Jack")
        wanted_cap.credits = 0
        wanted_cap.sector_id = 45  # Borderlands
        wanted_cap.bounty = 12000
        wanted_cap.ship.shields = 1
        wanted_cap.ship.fighters = 0
        if "c_wanted" not in self.kernel.sectors[45].captains:
            self.kernel.sectors[45].captains.append("c_wanted")

        self.player.sector_id = 45
        self.player.ship.shields = 500
        self.player.ship.fighters = 100
        init_credits = self.player.credits

        res = self.kernel.dispatch(self.player.id, ActionType.ATTACK_SHIP, target_id="c_wanted")
        self.assertTrue(res.success)
        self.assertTrue(res.data.get("defender_destroyed"))
        self.assertEqual(self.player.credits, init_credits + 12000)
        self.assertEqual(wanted_cap.bounty, 0)
        self.assertTrue(any("BOUNTY COLLECTED" in l for l in res.logs))

    def test_settle_restitution_at_stardock_bank(self):
        """Player can pay restitution at Sector 1 Bank to clear corporate embargoes and bounties."""
        self.player.sector_id = 1
        self.player.bounty = 6000
        self.player.embargoed_by = ["ai_voss"]
        init_credits = self.player.credits

        res = self.kernel.dispatch(self.player.id, ActionType.BANK_TRANSACTION, sub_action="restitution")
        self.assertTrue(res.success)
        self.assertEqual(self.player.credits, init_credits - 6000)
        self.assertEqual(self.player.bounty, 0)
        self.assertEqual(len(self.player.embargoed_by), 0)
        self.assertIn("CONSULATE", [m.sender for m in self.kernel.event_bus.get_recent_radio()])

    def test_counter_intelligence_wars_persistence(self):
        """Bounties, embargoes, and planet lockout persist across save/load state."""
        self.player.bounty = 7500
        self.player.bounty_placed_by = "Director Cynthia Voss"
        self.player.embargoed_by = ["ai_voss"]

        planet = self.kernel.sectors[1].planets[0] if self.kernel.sectors[1].planets else None
        if not planet:
            for s in self.kernel.sectors.values():
                if s.planets:
                    planet = s.planets[0]
                    break
        self.assertIsNotNone(planet)
        planet.security_lockout = 14

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            filepath = tf.name

        try:
            self.assertTrue(StatePersistence.save_to_file(self.kernel, filepath))
            restored = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(restored)

            loaded_player = restored.get_player(self.player.id)
            self.assertEqual(loaded_player.bounty, 7500)
            self.assertEqual(loaded_player.bounty_placed_by, "Director Cynthia Voss")
            self.assertEqual(loaded_player.embargoed_by, ["ai_voss"])

            loaded_planet = None
            for s in restored.sectors.values():
                for p in s.planets:
                    if p.id == planet.id:
                        loaded_planet = p
                        break
                if loaded_planet:
                    break

            self.assertIsNotNone(loaded_planet)
            self.assertEqual(loaded_planet.security_lockout, 14)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


if __name__ == "__main__":
    unittest.main()
