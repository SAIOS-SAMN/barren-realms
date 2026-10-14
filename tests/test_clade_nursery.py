"""
tests/test_clade_nursery.py

Unit and integration tests for:
1. CladeNurseryManager registration of seeded nascent sapient species.
2. Evolutionary stage progression (PRE_TOOL -> WARP_SOVEREIGN).
3. Celestial Guidance directives (Ecological Harmony, Martial Defense, Technological Uplift).
4. Divine protection and reverence locking.
5. Autonomous graduation into full spacefaring civilizations.
6. Persistence save/load serialization.
7. TerminalRenderer console output.
"""

import os
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType
from xylarium.kernel.clade_nursery import CladeNurseryManager, EvolutionaryStage
from xylarium.kernel.civilizational_epochs import EpochPhase
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer


class TestCladeNursery(unittest.TestCase):

    def setUp(self):
        self.kernel = GameKernel(seed=9999)
        self.player_id = "TEST_PROGENITOR_NURSE"
        self.kernel.register_player(self.player_id, "Elder Oron")
        self.captain = self.kernel.get_player(self.player_id)
        self.captain.turns = 300
        self.captain.credits = 1000000
        self.mgr = self.kernel.clade_nursery_manager
        # Set epoch to STEWARDSHIP to allow seeding
        rec = self.kernel.epoch_manager.get_or_create_record(self.player_id)
        rec.phase = EpochPhase.STEWARDSHIP

    def test_automatic_clade_registration_on_seed(self):
        """Verify seeding nascent life registers the clade in the Nursery registry."""
        target = self.kernel.sectors[1].planets[0]
        target.owner_id = None
        target.population = 0

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.STEWARD_SEED_NASCENT_LIFE,
            planet_id=target.id,
            clade_name="Lithovore-Swarm",
        )
        self.assertTrue(res.success)
        self.assertEqual(len(self.mgr.clades), 1)

        clade = list(self.mgr.clades.values())[0]
        self.assertEqual(clade.name, "Lithovore-Swarm")
        self.assertEqual(clade.stage, EvolutionaryStage.PRE_TOOL)
        self.assertEqual(clade.progenitor_id, self.player_id)

    def test_impart_guidance_uplift_and_defense(self):
        """Verify Progenitor directives accelerate evolution and fortify homeworld."""
        target = self.kernel.sectors[1].planets[0]
        target.owner_id = None
        self.kernel.dispatch(self.player_id, ActionType.STEWARD_SEED_NASCENT_LIFE, planet_id=target.id, clade_name="Chrono-Children")
        clade = list(self.mgr.clades.values())[0]

        # 1. Technological Uplift -> advances stage
        res_uplift = self.kernel.dispatch(
            self.player_id,
            ActionType.NURSERY_IMPART_GUIDANCE,
            clade_id=clade.id,
            directive="TECHNOLOGICAL_UPLIFT",
        )
        self.assertTrue(res_uplift.success)
        self.assertEqual(clade.stage, EvolutionaryStage.TRIBAL_NEOLITHIC)

        # 2. Martial Defense -> bolsters citadel and fighters
        res_defense = self.kernel.dispatch(
            self.player_id,
            ActionType.NURSERY_IMPART_GUIDANCE,
            clade_id=clade.id,
            directive="MARTIAL_DEFENSE",
        )
        self.assertTrue(res_defense.success)
        self.assertEqual(clade.guidance_directive, "MARTIAL_DEFENSE")

    def test_defend_clade_intervention(self):
        """Verify Progenitor direct defensive intervention locks reverence to 100%."""
        target = self.kernel.sectors[1].planets[0]
        target.owner_id = None
        self.kernel.dispatch(self.player_id, ActionType.STEWARD_SEED_NASCENT_LIFE, planet_id=target.id, clade_name="Solar-Aura")
        clade = list(self.mgr.clades.values())[0]

        res = self.kernel.dispatch(self.player_id, ActionType.NURSERY_DEFEND_CLADE, clade_id=clade.id)
        self.assertTrue(res.success)
        self.assertEqual(clade.reverence_pct, 100.0)
        self.assertEqual(clade.theology, "DIVINE_PROTECTOR")

    def test_deep_time_cycle_ticks_and_graduation(self):
        """Verify clades evolve through time and graduate to WARP_SOVEREIGN."""
        target = self.kernel.sectors[1].planets[0]
        target.owner_id = None
        self.kernel.dispatch(self.player_id, ActionType.STEWARD_SEED_NASCENT_LIFE, planet_id=target.id, clade_name="Deep-Striders")
        clade = list(self.mgr.clades.values())[0]

        # Advance cycles
        clade.cycles_lived = 44
        clade.stage = EvolutionaryStage.EARLY_SPACEFLIGHT

        self.mgr.tick(self.kernel)
        self.assertEqual(clade.stage, EvolutionaryStage.WARP_SOVEREIGN)
        self.assertGreaterEqual(target.citadel_level, 2)

    def test_persistence_roundtrip(self):
        """Verify clades survive serialization and deserialization."""
        target = self.kernel.sectors[1].planets[0]
        target.owner_id = None
        self.kernel.dispatch(self.player_id, ActionType.STEWARD_SEED_NASCENT_LIFE, planet_id=target.id, clade_name="Void-Born")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "nursery_save.json")
            saved = StatePersistence.save_to_file(self.kernel, path)
            self.assertTrue(saved)

            loaded = StatePersistence.load_from_file(path)
            self.assertIsNotNone(loaded)
            self.assertTrue(hasattr(loaded, "clade_nursery_manager"))
            self.assertEqual(len(loaded.clade_nursery_manager.clades), 1)
            clade = list(loaded.clade_nursery_manager.clades.values())[0]
            self.assertEqual(clade.name, "Void-Born")

    def test_renderer_output(self):
        """Verify TerminalRenderer renders Nursery screen cleanly."""
        target = self.kernel.sectors[1].planets[0]
        target.owner_id = None
        self.kernel.dispatch(self.player_id, ActionType.STEWARD_SEED_NASCENT_LIFE, planet_id=target.id, clade_name="Aethel-Kin")

        view = self.kernel.get_player_view(self.player_id)
        rendered = TerminalRenderer.render_clade_nursery_screen(view)
        self.assertIn("DEEP-TIME NURSERY & CLADE PHYLOGENY", rendered)
        self.assertIn("Aethel-Kin", rendered)


if __name__ == "__main__":
    unittest.main()
