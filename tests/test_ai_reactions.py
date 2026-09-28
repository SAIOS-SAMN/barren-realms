"""
Unit tests for Context-Aware AI Reactions via EventBus.
Verifies:
1. Territorial Encroachment: Cynthia Voss reacts to close-range colonization.
2. Predatory Tracking: Warlord Malakor hunts high-value cargo holds.
3. Bounty Recognition: Ironclaw Rake rewards pirate kills with direct credit payouts.
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType


class TestContextAwareAIReactions(unittest.TestCase):

    def setUp(self):
        self.kernel = GameKernel(seed=123)
        self.player = self.kernel.register_player("tester", "Tester")

    def test_territorial_encroachment_voss(self):
        """When player claims a planet near Voss territory, Voss sends a corporate cease-and-desist."""
        voss = self.kernel.captains["ai_voss"]
        voss_sec = voss.home_sector

        # Find an unowned planet within 1-3 hops from Voss's home sector
        target_planet = None
        target_sector = None
        for s_id, s in self.kernel.sectors.items():
            if s.planets and s.planets[0].owner_id is None:
                path = self.kernel.find_path(voss_sec, s_id)
                if path and 1 <= len(path) - 1 <= 3:
                    target_planet = s.planets[0]
                    target_sector = s
                    break

        self.assertIsNotNone(target_planet, "Expected an unowned planet within 3 hops of Voss")
        self.player.sector_id = target_sector.id

        # Claim the planet
        res = self.kernel.dispatch("tester", ActionType.PLANET_CLAIM, planet_id=target_planet.id)
        self.assertTrue(res.success)

        # Check subspace radio for Voss's warning
        radio_msgs = self.kernel.event_bus.get_recent_radio(10)
        voss_msgs = [m for m in radio_msgs if m.sender == voss.name]
        self.assertTrue(len(voss_msgs) > 0, "Expected a radio warning from Cynthia Voss")
        self.assertIn("falls within Voss Heavy Industries charter space", voss_msgs[0].text)

    def test_predatory_tracking_malakor(self):
        """When player carries high-value cargo into the borderlands/anarchy, Malakor begins hunting them."""
        malakor = self.kernel.captains["ai_malakor"]
        malakor.sector_id = 90  # Deep void
        malakor.hunt_target_sector = None

        # Give player 30 units of Equipment
        self.player.ship.cargo.capacity = 50
        self.player.ship.cargo.equipment = 30
        self.player.sector_id = 15  # Borderlands (sector > 10)

        # Move to an adjacent border sector
        dest = self.kernel.sectors[15].warps[0]
        res = self.kernel.dispatch("tester", ActionType.MOVE, destination=dest)
        self.assertTrue(res.success)

        # Malakor should now be locked onto the player's sector!
        self.assertEqual(malakor.hunt_target_sector, dest)

    def test_bounty_recognition_ironclaw(self):
        """When player neutralizes a pirate, Ironclaw Rake sends a commendation and pays out 5,000 Credits."""
        ironclaw = self.kernel.captains["ai_ironclaw"]
        malakor = self.kernel.captains["ai_malakor"]

        # Place player and Malakor in Sector 75 (Anarchy)
        self.player.sector_id = 75
        self.player.credits = 1000
        self.player.ship.shields = 500
        self.player.ship.fighters = 200

        malakor.sector_id = 75
        malakor.ship.shields = 1
        malakor.ship.fighters = 0
        if "ai_malakor" not in self.kernel.sectors[75].captains:
            self.kernel.sectors[75].captains.append("ai_malakor")

        # Attack and destroy Malakor
        res = self.kernel.dispatch("tester", ActionType.ATTACK_SHIP, target_id="ai_malakor")
        self.assertTrue(res.success)
        self.assertTrue(res.data.get("defender_destroyed"))

        # Check that player received the 5,000 Cr bounty from Ironclaw
        # Base credit plunder + 5000 bounty
        self.assertGreaterEqual(self.player.credits, 6000)

        # Check radio transmission from Ironclaw
        radio_msgs = self.kernel.event_bus.get_recent_radio(10)
        ironclaw_msgs = [m for m in radio_msgs if m.sender == ironclaw.name]
        self.assertTrue(len(ironclaw_msgs) > 0, "Expected a radio commendation from Ironclaw Rake")
        self.assertIn("Confirmed kill on outlaw", ironclaw_msgs[0].text)


if __name__ == "__main__":
    unittest.main()
