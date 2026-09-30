"""
Unit tests for the Galactic Spawning & Speciation Pipeline in Xylarium.
Verifies Vector 1 (Cognitive Cleaving), Vector 2 (Planetary Spaceflight),
and Vector 3 (Corporate Enforcers & Bounty Hunter Spawning).
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, AIPersonality, Planet, Ship, CargoHold, Captain
from xylarium.kernel.ai import AIManager
from xylarium.kernel.colony import ColonyManager
from xylarium.kernel.civilization import CivilizationIntelligenceEngine, FOUNDING_POLITIES
from xylarium.config import (
    MAX_AI_CAPTAINS,
    CLEAVE_BASIS_THRESHOLD,
    CLEAVE_ENDOWMENT_CREDITS,
    PLANETARY_SPACEFLIGHT_CITADEL_TIER,
    PLANETARY_SPACEFLIGHT_POPULATION,
    PLANETARY_SPACEFLIGHT_VAULT,
    PLANETARY_SPACEFLIGHT_COST,
    CORPORATE_ENFORCER_TREASURY,
    CORPORATE_ENFORCER_COST,
)


class TestGalacticSpawningPipeline(unittest.TestCase):
    """Verifies all three vectors of autonomous agent generation and emergence."""

    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.player = self.kernel.register_player("pilot_test", "Test Captain")

    def test_vector1_cognitive_cleaving(self):
        """Vector 1: High-tier AI captains with >= 25 grown basis crystals cleave offshoot junior captains."""
        vane = self.kernel.captains["ai_vane"]
        vane.credits = 15000
        vane.technologies = ["JUMP_DRIVE", "CLOAKING_GRID", "NANITE_DRYDOCK", "BIO_SYNTHESIZER", "ORBITAL_FOUNDRY"]
        vane.grown_basis = [{"id": f"basis_{i}"} for i in range(CLEAVE_BASIS_THRESHOLD + 5)]

        initial_captain_count = len(self.kernel.captains)
        initial_vane_credits = vane.credits

        # Trigger cleaving check
        child_cap = AIManager.check_cognitive_cleaving(self.kernel, vane)
        self.assertIsNotNone(child_cap)
        self.assertIn(child_cap.id, self.kernel.captains)
        self.assertEqual(len(self.kernel.captains), initial_captain_count + 1)

        # Check endowment deduction
        self.assertEqual(vane.credits, initial_vane_credits - CLEAVE_ENDOWMENT_CREDITS)
        self.assertEqual(child_cap.credits, CLEAVE_ENDOWMENT_CREDITS)

        # Check child properties
        self.assertTrue(child_cap.is_ai)
        self.assertTrue(child_cap.name.startswith("Pioneer") or child_cap.name.startswith("Prefect") or child_cap.name.startswith("Sentinel") or child_cap.name.startswith("Envoy"))
        self.assertIn("Vane", child_cap.name)
        self.assertIsNotNone(child_cap.metabolism)
        self.assertGreater(child_cap.ship.cargo.total_used, 0)
        self.assertEqual(child_cap.sector_id, vane.sector_id)
        self.assertIn(child_cap.id, self.kernel.sectors[child_cap.sector_id].captains)

        # Immediate repeat should fail due to cooldown
        repeat_child = AIManager.check_cognitive_cleaving(self.kernel, vane)
        self.assertIsNone(repeat_child)

    def test_vector2_planetary_spaceflight_civiligenesis(self):
        """Vector 2: Indigenous civilizations on Citadel Tier 2+ worlds launch starships."""
        planet = self.kernel.sectors[4].planets[0] if self.kernel.sectors[4].planets else None
        if not planet:
            # Pick any sector with a planet
            for sec in self.kernel.sectors.values():
                if sec.planets:
                    planet = sec.planets[0]
                    break

        self.assertIsNotNone(planet)
        # Configure planet to meet civiligenesis thresholds
        planet.citadel_level = PLANETARY_SPACEFLIGHT_CITADEL_TIER
        planet.population = PLANETARY_SPACEFLIGHT_POPULATION + 2000
        planet.treasury = PLANETARY_SPACEFLIGHT_VAULT + 5000

        # Assign an indigenous civilization (e.g. Stillcold)
        pol_spec = FOUNDING_POLITIES[5]  # Stillcold (cryocoherens-still, biotic)
        planet.civilization = CivilizationIntelligenceEngine.create_civilization(pol_spec)

        initial_captain_count = len(self.kernel.captains)
        treasury_before = planet.treasury

        # Trigger civiligenesis check
        launched_cap = ColonyManager.check_planetary_spaceflight(self.kernel, planet, self.kernel.event_bus)
        self.assertIsNotNone(launched_cap)
        self.assertIn(launched_cap.id, self.kernel.captains)
        self.assertEqual(len(self.kernel.captains), initial_captain_count + 1)

        # Check treasury deduction
        self.assertEqual(planet.treasury, treasury_before - PLANETARY_SPACEFLIGHT_COST)

        # Check ship and taxon alignment
        self.assertEqual(launched_cap.species, "cryocoherens-still")
        self.assertEqual(launched_cap.metabolism, "biotic")
        self.assertEqual(launched_cap.sector_id, planet.sector_id)
        self.assertIn("Stillcold", launched_cap.name)
        self.assertEqual(launched_cap.personality, AIPersonality.TRADER)
        self.assertGreater(launched_cap.ship.cargo.organics, 0)
        self.assertIn(launched_cap.id, self.kernel.sectors[planet.sector_id].captains)

        # Immediate repeat should fail due to active captain / cooldown
        repeat_cap = ColonyManager.check_planetary_spaceflight(self.kernel, planet, self.kernel.event_bus)
        self.assertIsNone(repeat_cap)

    def test_vector3_corporate_enforcer_spawning(self):
        """Vector 3: ISSE corporations exceeding liquid reserve threshold commission security enforcers."""
        voss_corp = self.kernel.market_manager.companies["VOSS"]
        voss_corp.treasury = CORPORATE_ENFORCER_TREASURY + 10000

        initial_captain_count = len(self.kernel.captains)
        treasury_before = voss_corp.treasury

        spawned = self.kernel.market_manager.check_corporate_and_bounty_spawning(self.kernel)
        self.assertGreater(len(spawned), 0)
        self.assertIn("VOSS Enforcer", spawned[0])
        self.assertEqual(len(self.kernel.captains), initial_captain_count + len(spawned))
        # Commission cost plus the enforcer's 5,000 Cr operating float, both paid by the company
        self.assertEqual(voss_corp.treasury, treasury_before - CORPORATE_ENFORCER_COST - 5000)

        # Verify enforcer captain attributes
        enforcer_id = voss_corp.active_enforcer_id
        self.assertIsNotNone(enforcer_id)
        enforcer_cap = self.kernel.captains[enforcer_id]
        self.assertTrue(enforcer_cap.is_ai)
        self.assertEqual(enforcer_cap.ship.ship_type, "Star Frigate")
        self.assertGreaterEqual(enforcer_cap.ship.shields, 400)
        self.assertGreaterEqual(enforcer_cap.ship.fighters, 80)

    def test_vector3_federal_bounty_hunter_spawning(self):
        """Vector 3: Federal Bounty Office commissions bounty marshals when pirate threat is uncontained."""
        # Set cycle count to 150
        self.kernel.cycle_count = 150
        # Ensure there is an active pirate captain
        malakor = self.kernel.captains["ai_malakor"]
        self.assertEqual(malakor.personality, AIPersonality.PIRATE)

        # Remove any existing marshals
        for cid, c in list(self.kernel.captains.items()):
            if "Marshal" in c.name or "Hunter" in c.name:
                del self.kernel.captains[cid]

        spawned = self.kernel.market_manager.check_corporate_and_bounty_spawning(self.kernel)
        marshal_spawned = [s for s in spawned if "Fed Marshal" in s]
        self.assertGreater(len(marshal_spawned), 0)

        # Check marshal exists in sector 1
        marshal_cap = next(c for c in self.kernel.captains.values() if "Fed Marshal" in c.name)
        self.assertEqual(marshal_cap.sector_id, 1)
        self.assertEqual(marshal_cap.personality, AIPersonality.MERCENARY)
        self.assertEqual(marshal_cap.metabolism, "plasmic")

    def test_spawning_cap_safeguard(self):
        """Simulation honors MAX_AI_CAPTAINS cap to preserve execution throughput."""
        # Artificially fill captain roster up to MAX_AI_CAPTAINS
        dummy_ship = Ship(
            ship_type="Scout Ship",
            cargo=CargoHold(capacity=30),
            shields=100,
            max_shields=100,
            fighters=10,
        )
        for i in range(len(self.kernel.captains), MAX_AI_CAPTAINS + 5):
            cid = f"dummy_cap_{i}"
            self.kernel.captains[cid] = Captain(
                id=cid,
                name=f"Dummy {i}",
                is_ai=True,
                personality=AIPersonality.TRADER,
                ship=dummy_ship,
                credits=1000,
                sector_id=1,
                turns_left=100,
            )

        self.assertGreaterEqual(len(self.kernel.captains), MAX_AI_CAPTAINS)

        # Vector 1 should refuse
        vane = self.kernel.captains["ai_vane"]
        vane.credits = 50000
        vane.grown_basis = [{"id": f"b_{i}"} for i in range(50)]
        child = AIManager.check_cognitive_cleaving(self.kernel, vane)
        self.assertIsNone(child)

        # Vector 2 should refuse
        planet = next(sec.planets[0] for sec in self.kernel.sectors.values() if sec.planets)
        planet.citadel_level = 3
        planet.population = 50000
        planet.treasury = 50000
        launched = ColonyManager.check_planetary_spaceflight(self.kernel, planet)
        self.assertIsNone(launched)

        # Vector 3 should refuse
        spawned = self.kernel.market_manager.check_corporate_and_bounty_spawning(self.kernel)
        self.assertEqual(spawned, [])


if __name__ == "__main__":
    unittest.main()
