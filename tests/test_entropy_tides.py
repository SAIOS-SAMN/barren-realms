"""
tests/test_entropy_tides.py

Comprehensive test suite for Project Landing 5:
Cosmic Entropy Tides & The Inflationary Genesis Loop.
"""

import os
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType
from xylarium.kernel.entropy_tides import EntropyTidesManager, CosmicPhysicalConstants
from xylarium.kernel.civilizational_epochs import EpochPhase
from xylarium.client.renderer import TerminalRenderer
from xylarium.persistence.store import StatePersistence


class TestEntropyTides(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=777)
        self.captain_id = "cap_genesis"
        self.kernel.register_player(self.captain_id, "Archon Solon")
        self.captain = self.kernel.get_player(self.captain_id)
        self.captain.turns = 300
        self.captain.credits = 10000000
        self.mgr = self.kernel.entropy_tides_manager

    def test_entropy_tick_creep(self):
        initial = self.mgr.entropy_level
        self.mgr.tick(self.kernel)
        self.assertGreater(self.mgr.entropy_level, initial)

    def test_purge_entropy_with_credits_and_syntropy(self):
        self.mgr.entropy_level = 50.0

        # Purge with credits
        res = self.kernel.dispatch(
            self.captain_id,
            ActionType.ENTROPY_PURGE_PULSE,
        )
        self.assertTrue(res.success)
        self.assertLess(self.mgr.entropy_level, 50.0)

        # Purge with syntropic resilience
        rec = self.kernel.epoch_manager.get_or_create_record(self.captain_id)
        rec.syntropic_resilience = 60.0
        res2 = self.kernel.dispatch(
            self.captain_id,
            ActionType.ENTROPY_PURGE_PULSE,
        )
        self.assertTrue(res2.success)
        self.assertEqual(rec.syntropic_resilience, 40.0)

    def test_attune_cosmic_constants(self):
        attune_res = self.kernel.dispatch(
            self.captain_id,
            ActionType.ENTROPY_ATTUNE_METRIC,
            matter_density=1.5,
            syntropic_affinity=2.0,
            hyperlane_percolation=1.2,
        )
        self.assertTrue(attune_res.success)
        self.assertEqual(self.mgr.constants.matter_density, 1.5)
        self.assertEqual(self.mgr.constants.syntropic_affinity, 2.0)
        self.assertEqual(self.mgr.constants.hyperlane_percolation, 1.2)

    def test_trigger_inflationary_genesis(self):
        # Set epoch to stewardship and attune constants
        rec = self.kernel.epoch_manager.get_or_create_record(self.captain_id)
        rec.phase = EpochPhase.STEWARDSHIP
        rec.syntropic_resilience = 120.0
        self.mgr.entropy_level = 80.0

        gen_res = self.kernel.dispatch(
            self.captain_id,
            ActionType.INFLATIONARY_GENESIS,
        )
        self.assertTrue(gen_res.success)
        self.assertEqual(self.mgr.genesis_generation, 2)
        self.assertAlmostEqual(self.mgr.entropy_level, 5.0, delta=1.0)
        self.assertEqual(len(self.mgr.genesis_history), 1)

        history_entry = self.mgr.genesis_history[0]
        self.assertEqual(history_entry["generation"], 1)
        self.assertEqual(history_entry["creator_captain"], self.captain.name)

        # Check universe ruins rebranded with player's ancient name
        ruins_found = False
        for sec in self.kernel.sectors.values():
            for p in sec.planets:
                if getattr(p, "ruins", None):
                    self.assertIn("Archon Solon", p.ruins["culture"])
                    ruins_found = True
                    break
            if ruins_found:
                break
        self.assertTrue(ruins_found)

    def test_persistence_save_load(self):
        self.mgr.entropy_level = 42.5
        self.mgr.genesis_generation = 3
        self.mgr.constants.matter_density = 1.75

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "entropy_tides_save.json")
            saved = StatePersistence.save_to_file(self.kernel, save_path)
            self.assertTrue(saved)

            loaded = StatePersistence.load_from_file(save_path)
            self.assertIsNotNone(loaded)
            self.assertTrue(hasattr(loaded, "entropy_tides_manager"))
            self.assertEqual(loaded.entropy_tides_manager.genesis_generation, 3)
            self.assertAlmostEqual(loaded.entropy_tides_manager.entropy_level, 42.5)
            self.assertEqual(loaded.entropy_tides_manager.constants.matter_density, 1.75)

    def test_renderer_screen(self):
        view = self.kernel.get_player_view(self.captain_id)
        rendered = TerminalRenderer.render_entropy_tides_screen(view)
        self.assertIn("COSMIC ENTROPY TIDES & THE INFLATIONARY GENESIS LOOP", rendered)
        self.assertIn("GLOBAL ENTROPY STRAIN", rendered)
        self.assertIn("ATTUNED PHYSICAL LAWS", rendered)
        self.assertIn("ANCESTRAL GENESIS ARCHIVES", rendered)


if __name__ == "__main__":
    unittest.main()
