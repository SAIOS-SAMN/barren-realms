"""
Unit tests for Xylarium Espionage & Covert Operations.
Tests operative recruitment, counter-intelligence garrisoning, covert operations
(recon, siphon, sabotage, destabilize), detection/leaks, and state persistence.
"""

import unittest
from xylarium.config import CITADEL_UPKEEP
from unittest.mock import patch
import os
import tempfile

from xylarium.config import OPERATIVE_COST_CREDITS, TURN_COST_COVERT_OP
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import Planet, ActionType
from xylarium.persistence.store import StatePersistence


class TestEspionageSuite(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel()
        self.sectors = self.kernel.sectors
        self.player = self.kernel.register_player("c_test", "SpyMaster")
        self.player.credits = 20000
        self.player.turns_left = 100
        self.player.operatives = 0

    def test_recruit_operatives_at_sector_1(self):
        """Player can recruit secret operatives at Sol Central (Sector 1)."""
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.RECRUIT_OPERATIVES,
            amount=5
        )
        self.assertTrue(res.success)
        self.assertEqual(self.player.operatives, 5)
        self.assertEqual(self.player.credits, 20000 - (5 * OPERATIVE_COST_CREDITS))

    def test_recruit_operatives_rejected_insufficient_credits(self):
        """Recruitment fails if player lacks required credits."""
        self.player.credits = 100
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.RECRUIT_OPERATIVES,
            amount=2
        )
        self.assertFalse(res.success)
        self.assertIn("requires", res.message)
        self.assertEqual(self.player.operatives, 0)

    def test_recruit_operatives_outside_sector_1_requires_tier_1_colony(self):
        """Recruitment outside Sector 1 requires an owned Citadel Tier 1+ colony."""
        # Move to sector 2 without an owned colony
        self.player.sector_id = 2
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.RECRUIT_OPERATIVES,
            amount=2
        )
        self.assertFalse(res.success)
        self.assertIn("requires Sol Central Stardock", res.message)

        # Place owned Tier 1 Citadel on Sector 2
        sec2 = self.sectors[2]
        planet = Planet(
            id="p_citadel",
            name="Fortress Test",
            sector_id=2,
            owner_id=self.player.id,
            citadel_level=1
        )
        sec2.planets.append(planet)

        res2 = self.kernel.dispatch(
            self.player.id,
            ActionType.RECRUIT_OPERATIVES,
            amount=2
        )
        self.assertTrue(res2.success)
        self.assertEqual(self.player.operatives, 2)

    def test_station_and_withdraw_security_operatives(self):
        """Captain can station operatives on colony as counter-intel and withdraw them."""
        sec = self.sectors[1]
        planet = Planet(
            id="p_colony",
            name="Outpost Alpha",
            sector_id=1,
            owner_id=self.player.id,
            citadel_level=1,
            security_operatives=0
        )
        sec.planets.append(planet)
        self.player.operatives = 10

        # Station 4 operatives
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.STATION_SECURITY,
            planet_id="p_colony",
            amount=4,
            mode="station"
        )
        self.assertTrue(res.success)
        self.assertEqual(planet.security_operatives, 4)
        self.assertEqual(self.player.operatives, 6)

        # Withdraw 2 operatives
        res_with = self.kernel.dispatch(
            self.player.id,
            ActionType.STATION_SECURITY,
            planet_id="p_colony",
            amount=2,
            mode="withdraw"
        )
        self.assertTrue(res_with.success)
        self.assertEqual(planet.security_operatives, 2)
        self.assertEqual(self.player.operatives, 8)

    def test_station_security_rejected_unowned_planet(self):
        """Cannot station operatives on a planet owned by someone else."""
        sec = self.sectors[1]
        planet = Planet(
            id="p_enemy",
            name="Enemy Redoubt",
            sector_id=1,
            owner_id="c_other",
            security_operatives=0
        )
        sec.planets.append(planet)
        self.player.operatives = 5

        res = self.kernel.dispatch(
            self.player.id,
            ActionType.STATION_SECURITY,
            planet_id="p_enemy",
            amount=2,
            mode="station"
        )
        self.assertFalse(res.success)
        self.assertIn("do not govern", res.message)

    def test_covert_op_recon_on_planet(self):
        """Recon op gathers telemetry data on rival colony."""
        sec = self.sectors[10]
        colony = Planet(
            id="p_target",
            name="Target World",
            sector_id=10,
            owner_id="c_rival",
            citadel_level=2,
            population=12000,
            morale=85,
            shields=400,
            treasury=50000,
            security_operatives=2
        )
        sec.planets.append(colony)
        self.player.operatives = 5
        init_turns = self.player.turns_left

        with patch("random.random", return_value=0.01):  # Guarantee success and no detection
            res = self.kernel.dispatch(
                self.player.id,
                ActionType.COVERT_OP,
                target_type="PLANET",
                target_id="p_target",
                op_type="recon",
                operatives=2
            )

        self.assertTrue(res.success)
        self.assertEqual(self.player.turns_left, init_turns - TURN_COST_COVERT_OP)
        self.assertIn("intel", res.data)
        intel = res.data["intel"]
        self.assertEqual(intel["treasury"], 50000)
        self.assertEqual(intel["population"], 12000)
        self.assertEqual(intel["shields"], 400)
        self.assertEqual(intel["citadel_level"], 2)

    def test_covert_op_siphon_on_planet(self):
        """Siphon op drains credits from a planetary vault into player treasury."""
        sec = self.sectors[15]
        colony = Planet(
            id="p_rich",
            name="Rich Goldmine",
            sector_id=15,
            owner_id="c_rival",
            treasury=100000
        )
        sec.planets.append(colony)
        self.player.operatives = 5
        init_credits = self.player.credits

        with patch("random.random", return_value=0.01):
            with patch("random.uniform", return_value=0.25):  # 25% siphoned = 25,000 Cr
                res = self.kernel.dispatch(
                    self.player.id,
                    ActionType.COVERT_OP,
                    target_type="PLANET",
                    target_id="p_rich",
                    op_type="siphon",
                    operatives=3
                )

        self.assertTrue(res.success)
        self.assertEqual(res.data["siphoned_credits"], 25000)
        # The vault lost at least the siphoned 25% (the world tick may also move upkeep/consumer spending)
        self.assertLessEqual(colony.treasury, 75000 + 150)
        # Siphoned funds arrive in the colony's own currency (offshore wallet if non-SOL)
        from xylarium.kernel.fx import balance
        if colony.currency == "SOL":
            wages = self.kernel.crew_wage(self.player) if self.kernel.sectors[self.player.sector_id].port else 0
            self.assertEqual(self.player.credits, init_credits + 25000 - wages)
        else:
            self.assertEqual(balance(self.player, colony.currency), 25000)

    def test_covert_op_sabotage_on_ship(self):
        """Sabotage op disrupts deflector shield matrix of rival starship."""
        target_cap = self.kernel.register_player("c_rival_ship", "Target Cruiser")
        target_cap.ship.shields = 800
        target_cap.ship.max_shields = 800
        self.player.operatives = 5

        with patch("random.random", return_value=0.01):
            with patch("random.uniform", return_value=0.50):  # 50% damage = 400 MW
                res = self.kernel.dispatch(
                    self.player.id,
                    ActionType.COVERT_OP,
                    target_type="SHIP",
                    target_id="c_rival_ship",
                    op_type="sabotage",
                    operatives=3
                )

        self.assertTrue(res.success)
        self.assertEqual(res.data["shield_damage"], 400)
        self.assertEqual(target_cap.ship.shields, 400)

    def test_covert_op_destabilize_on_planet(self):
        """Destabilize op poisons organics stores and damages colony morale."""
        sec = self.sectors[20]
        colony = Planet(
            id="p_agri",
            name="Agri World",
            sector_id=20,
            owner_id="c_rival",
            morale=90,
            organics_silo=100
        )
        sec.planets.append(colony)
        self.player.operatives = 5

        with patch("random.random", return_value=0.01):
            with patch("random.randint", return_value=30):
                res = self.kernel.dispatch(
                    self.player.id,
                    ActionType.COVERT_OP,
                    target_type="PLANET",
                    target_id="p_agri",
                    op_type="destabilize",
                    operatives=3
                )

        self.assertTrue(res.success)
        self.assertEqual(res.data["lost_organics"], 50)
        self.assertEqual(res.data["morale_hit"], 30)
        self.assertAlmostEqual(colony.organics_silo, 50, delta=10)
        self.assertAlmostEqual(colony.morale, 60, delta=5)

    def test_covert_op_failure_inflicts_casualties_and_radio_alert(self):
        """Failed operation causes operative casualties and broadcasts security alert."""
        sec = self.sectors[25]
        colony = Planet(
            id="p_guarded",
            name="Iron Keep",
            sector_id=25,
            owner_id="c_rival",
            citadel_level=3,
            security_operatives=20
        )
        sec.planets.append(colony)
        self.player.operatives = 6

        with patch("random.random", return_value=0.99):  # Guarantee failure
            with patch("random.randint", return_value=3):   # 3 casualties
                res = self.kernel.dispatch(
                    self.player.id,
                    ActionType.COVERT_OP,
                    target_type="PLANET",
                    target_id="p_guarded",
                    op_type="siphon",
                    operatives=4
                )

        self.assertFalse(res.success)
        self.assertEqual(res.data["casualties"], 3)
        self.assertEqual(self.player.operatives, 3)
        self.assertIn("COUNTER-INTEL", [m.sender for m in self.kernel.event_bus.get_recent_radio()])

    def test_espionage_persistence(self):
        """Operative counts on Captain and Planet survive serialization round-trip."""
        sec = self.sectors[1]
        planet = Planet(
            id="p_persist",
            name="Spy Haven",
            sector_id=1,
            owner_id=self.player.id,
            security_operatives=14
        )
        sec.planets.append(planet)
        self.player.operatives = 27

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            self.assertTrue(StatePersistence.save_to_file(self.kernel, temp_path))
            restored = StatePersistence.load_from_file(temp_path)
            self.assertIsNotNone(restored)

            loaded_player = restored.captains[self.player.id]
            self.assertEqual(loaded_player.operatives, 27)

            loaded_sec = restored.sectors[1]
            loaded_planet = next(p for p in loaded_sec.planets if p.id == "p_persist")
            self.assertEqual(loaded_planet.security_operatives, 14)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
