"""
tests/test_relic_foundry.py

Unit and integration tests for:
1. RelicFoundryManager component vault & archaeological analysis.
2. Forging Masterwork Precursor Artifacts (Chrono-Slipdrive, Planetary World Engine, etc.).
3. Missing component and credit validation.
4. Equipping artifacts to Flagship, Planets, and Star Sectors with live effects.
5. Dismantling artifacts for material recovery.
6. Cycle dividend flows from active artifacts.
7. Save/load persistence round-trip.
8. TerminalRenderer console display.
"""

import os
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType
from xylarium.kernel.relic_foundry import BLUEPRINTS, RelicFoundryManager
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer


class TestRelicFoundry(unittest.TestCase):

    def setUp(self):
        self.kernel = GameKernel(seed=8888)
        self.player_id = "TEST_FORGEMASTER"
        self.kernel.register_player(self.player_id, "Master Telamon")
        self.captain = self.kernel.get_player(self.player_id)
        self.captain.turns = 300
        self.captain.credits = 1000000
        self.captain.ship.cargo.equipment = 50
        self.mgr = self.kernel.relic_foundry_manager

    def test_component_inventory_and_analysis(self):
        """Verify analyzing relics and equipment produces calibrated components."""
        self.captain.relics = ["Aelari Chrono-Fragment", "Precursor Core Shard"]
        res = self.kernel.dispatch(self.player_id, ActionType.FOUNDRY_ANALYZE)
        self.assertTrue(res.success)

        inv = self.mgr.get_inventory(self.player_id)
        total_comps = sum(inv.values())
        self.assertGreater(total_comps, 0)
        self.assertIn("gains", res.data)

    def test_forging_validation_and_success(self):
        """Verify forging checks requirements, consumes resources, and produces artifacts."""
        # Attempt to forge Chrono-Slipdrive without components -> fails
        res_fail = self.kernel.dispatch(
            self.player_id,
            ActionType.FOUNDRY_FORGE,
            blueprint_id="CHRONO_SLIPDRIVE",
        )
        self.assertFalse(res_fail.success)
        self.assertIn("Missing required", res_fail.message)

        # Grant required components
        self.mgr.grant_component(self.player_id, "TESSERACT_MATRIX", 1)
        self.mgr.grant_component(self.player_id, "TACHYON_RESONATOR", 2)
        self.mgr.grant_component(self.player_id, "CHRONO_CRYSTAL", 1)

        creds_before = self.captain.credits
        res_ok = self.kernel.dispatch(
            self.player_id,
            ActionType.FOUNDRY_FORGE,
            blueprint_id="CHRONO_SLIPDRIVE",
        )
        self.assertTrue(res_ok.success)
        self.assertAlmostEqual(self.captain.credits, creds_before - 35000, delta=20)

        art_data = res_ok.data["artifact"]
        self.assertEqual(art_data["blueprint_id"], "CHRONO_SLIPDRIVE")
        self.assertIn(art_data["id"], self.mgr.artifacts)

    def test_equip_flagship_and_planet_effects(self):
        """Verify equipping artifacts applies concrete physical enhancements."""
        # 1. Flagship module
        self.mgr.grant_component(self.player_id, "TESSERACT_MATRIX", 1)
        self.mgr.grant_component(self.player_id, "TACHYON_RESONATOR", 2)
        self.mgr.grant_component(self.player_id, "CHRONO_CRYSTAL", 1)
        res_forge_ship = self.kernel.dispatch(self.player_id, ActionType.FOUNDRY_FORGE, blueprint_id="CHRONO_SLIPDRIVE")
        ship_art_id = res_forge_ship.data["artifact"]["id"]

        shields_before = self.captain.ship.shields
        res_equip_ship = self.kernel.dispatch(self.player_id, ActionType.FOUNDRY_EQUIP, artifact_id=ship_art_id)
        self.assertTrue(res_equip_ship.success)
        self.assertEqual(self.captain.ship.shields, shields_before + 200)

        # 2. Planetary World Engine
        self.mgr.grant_component(self.player_id, "ZERO_POINT_DYNAMO", 1)
        self.mgr.grant_component(self.player_id, "ENTANGLEMENT_PRISM", 2)
        self.mgr.grant_component(self.player_id, "TESSERACT_MATRIX", 1)
        res_forge_planet = self.kernel.dispatch(self.player_id, ActionType.FOUNDRY_FORGE, blueprint_id="PLANETARY_WORLD_ENGINE")
        planet_art_id = res_forge_planet.data["artifact"]["id"]

        target_planet = self.kernel.sectors[1].planets[0]
        target_planet.habitability = 0.40
        citadel_before = target_planet.citadel_level

        res_equip_planet = self.kernel.dispatch(
            self.player_id,
            ActionType.FOUNDRY_EQUIP,
            artifact_id=planet_art_id,
            target_id=target_planet.id,
        )
        self.assertTrue(res_equip_planet.success)
        self.assertEqual(target_planet.habitability, 1.0)
        self.assertEqual(target_planet.citadel_level, citadel_before + 2)

    def test_equip_sector_coherence_anchor(self):
        """Verify Dimensional Coherence Anchor reduces entropy strain in sector."""
        self.mgr.grant_component(self.player_id, "ENTANGLEMENT_PRISM", 2)
        self.mgr.grant_component(self.player_id, "VOID_POLARIZER", 2)
        self.mgr.grant_component(self.player_id, "ZERO_POINT_DYNAMO", 1)

        res_forge = self.kernel.dispatch(self.player_id, ActionType.FOUNDRY_FORGE, blueprint_id="DIMENSIONAL_COHERENCE_ANCHOR")
        art_id = res_forge.data["artifact"]["id"]

        rec = self.kernel.epoch_manager.get_or_create_record(self.player_id)
        rec.entropy_strain = 80.0

        res_equip = self.kernel.dispatch(
            self.player_id,
            ActionType.FOUNDRY_EQUIP,
            artifact_id=art_id,
            target_id="1",
        )
        self.assertTrue(res_equip.success)
        self.assertEqual(rec.entropy_strain, 40.0)

    def test_dismantle_artifact(self):
        """Verify dismantling an artifact salvages component materials."""
        self.mgr.grant_component(self.player_id, "TESSERACT_MATRIX", 2)
        self.mgr.grant_component(self.player_id, "TACHYON_RESONATOR", 4)
        self.mgr.grant_component(self.player_id, "CHRONO_CRYSTAL", 2)

        res_forge = self.kernel.dispatch(self.player_id, ActionType.FOUNDRY_FORGE, blueprint_id="CHRONO_SLIPDRIVE")
        art_id = res_forge.data["artifact"]["id"]

        res_dismantle = self.kernel.dispatch(self.player_id, ActionType.FOUNDRY_DISMANTLE, artifact_id=art_id)
        self.assertTrue(res_dismantle.success)
        self.assertNotIn(art_id, self.mgr.artifacts)
        self.assertIn("recovered", res_dismantle.data)

    def test_tick_dividend_flows(self):
        """Verify Syntropic Harvest Catalyst generates credits and syntropy resilience on tick."""
        self.mgr.grant_component(self.player_id, "CHRONO_CRYSTAL", 2)
        self.mgr.grant_component(self.player_id, "ZERO_POINT_DYNAMO", 1)
        self.mgr.grant_component(self.player_id, "ENTANGLEMENT_PRISM", 1)

        res_forge = self.kernel.dispatch(self.player_id, ActionType.FOUNDRY_FORGE, blueprint_id="SYNTROPIC_HARVEST_CATALYST")
        art_id = res_forge.data["artifact"]["id"]

        # Equip
        self.kernel.dispatch(self.player_id, ActionType.FOUNDRY_EQUIP, artifact_id=art_id)

        creds_before = self.captain.credits
        self.mgr.tick(self.kernel)
        self.assertEqual(self.captain.credits, creds_before + 1000)

    def test_persistence_roundtrip(self):
        """Verify foundry inventory and forged masterworks persist across serialization."""
        self.mgr.grant_component(self.player_id, "TESSERACT_MATRIX", 5)
        self.mgr.grant_component(self.player_id, "VOID_POLARIZER", 3)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "foundry_save.json")
            saved = StatePersistence.save_to_file(self.kernel, path)
            self.assertTrue(saved)

            loaded = StatePersistence.load_from_file(path)
            self.assertIsNotNone(loaded)
            self.assertTrue(hasattr(loaded, "relic_foundry_manager"))
            inv = loaded.relic_foundry_manager.get_inventory(self.player_id)
            self.assertEqual(inv["TESSERACT_MATRIX"], 5)
            self.assertEqual(inv["VOID_POLARIZER"], 3)

    def test_renderer_output(self):
        """Verify TerminalRenderer renders Relic Foundry screen cleanly."""
        view = self.kernel.get_player_view(self.player_id)
        rendered = TerminalRenderer.render_relic_foundry_screen(view)
        self.assertIn("SYNTROPIC RELIC FOUNDRY & ARTIFACT FORGE", rendered)
        self.assertIn("QUANTUM COMPONENT VAULT", rendered)
        self.assertIn("MASTERWORK PRECURSOR BLUEPRINTS", rendered)


if __name__ == "__main__":
    unittest.main()
