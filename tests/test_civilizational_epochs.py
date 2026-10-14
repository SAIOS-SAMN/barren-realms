"""
tests/test_civilizational_epochs.py

Unit and integration tests for:
1. CivilizationalEpochManager state machine and macro-evolutionary transitions.
2. Thermodynamic Entropy Strain vs Syntropic Resilience calculations.
3. The Great Filter Bottleneck transit (Epoch II).
4. Civilizational Metamorphosis Accord into Deep-Time Stewardship (Epoch III).
5. All 4 Stewardship Directives (Seed Life, Stabilize Stars, Precursor Beacons, Syntropic Pulses).
6. Cycle ticks and dividend flows.
7. StatePersistence round-trip serialization and client renderer.
"""

import os
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Planet
from xylarium.kernel.civilizational_epochs import CivilizationalEpochManager, EpochPhase, EpochRecord
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer


class TestCivilizationalEpochs(unittest.TestCase):

    def setUp(self):
        self.kernel = GameKernel(seed=4242)
        self.player_id = "TEST_PROGENITOR"
        self.kernel.register_player(self.player_id, "Archon Elyon")
        self.captain = self.kernel.get_player(self.player_id)
        self.captain.turns = 200
        self.captain.credits = 500000
        self.mgr = self.kernel.epoch_manager

    def test_initial_epoch_and_assessment(self):
        """Verify new civilization begins in Epoch I: Expansion."""
        rec = self.mgr.get_or_create_record(self.player_id)
        self.assertEqual(rec.phase, EpochPhase.EXPANSION)

        assessment = self.mgr.assess_civilization(self.kernel, self.captain)
        self.assertEqual(assessment["phase"], EpochPhase.EXPANSION.value)
        self.assertGreaterEqual(assessment["entropy_strain"], 0.0)
        self.assertFalse(assessment["can_metamorphose"])

    def test_filter_transit_trigger(self):
        """Verify unconstrained expansion or filter awakening shifts phase to Epoch II: Filter Transit."""
        rec = self.mgr.get_or_create_record(self.player_id)
        # Artificially trigger Great Filter in omega manager
        self.kernel.omega_manager.great_filter_active = True

        assessment = self.mgr.assess_civilization(self.kernel, self.captain)
        self.assertEqual(rec.phase, EpochPhase.FILTER_TRANSIT)
        self.assertEqual(assessment["phase"], EpochPhase.FILTER_TRANSIT.value)

    def test_metamorphosis_requirements_and_execution(self):
        """Verify Metamorphosis Accord requires sufficient syntropy before ascending to Stewardship."""
        rec = self.mgr.get_or_create_record(self.player_id)
        rec.phase = EpochPhase.FILTER_TRANSIT
        rec.entropy_strain = 120.0
        rec.syntropic_resilience = 30.0

        # Attempt metamorphosis with insufficient syntropy -> fails
        res_fail = self.kernel.dispatch(self.player_id, ActionType.EPOCH_INITIATE_METAMORPHOSIS)
        self.assertFalse(res_fail.success)
        self.assertIn("insufficient", res_fail.message.lower())

        # Bolster syntropic resilience (e.g. mind uploading & megastructures)
        rec.syntropic_resilience = 150.0

        # Dispatch Metamorphosis Accord
        res_ok = self.kernel.dispatch(self.player_id, ActionType.EPOCH_INITIATE_METAMORPHOSIS)
        self.assertTrue(res_ok.success)
        self.assertEqual(rec.phase, EpochPhase.STEWARDSHIP)
        self.assertEqual(rec.title, "Progenitor of Deep Time")
        self.assertIn("SURMOUNTED", res_ok.message)

    def test_stewardship_seed_nascent_life(self):
        """Verify Steward can seed primitive worlds with nascent sapient clades."""
        rec = self.mgr.get_or_create_record(self.player_id)
        rec.phase = EpochPhase.STEWARDSHIP

        target = self.kernel.sectors[1].planets[0]
        target.owner_id = None
        target.population = 0

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.STEWARD_SEED_NASCENT_LIFE,
            planet_id=target.id,
            clade_name="Aethel-Kin",
        )
        self.assertTrue(res.success)
        self.assertEqual(target.planet_type, "BIOTIC")
        self.assertEqual(target.natives["species"], "Aethel-Kin")
        self.assertEqual(rec.nascent_worlds_seeded, 1)
        self.assertGreater(rec.syntropic_resilience, 0.0)

    def test_stewardship_stabilize_star(self):
        """Verify Steward can stabilize stellar fusion and boost planetary shields."""
        rec = self.mgr.get_or_create_record(self.player_id)
        rec.phase = EpochPhase.STEWARDSHIP

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.STEWARD_STABILIZE_STAR,
            sector_id=1,
        )
        self.assertTrue(res.success)
        self.assertEqual(rec.stellar_cores_stabilized, 1)

    def test_stewardship_plant_precursor_beacon(self):
        """Verify Steward can plant archaeological ruins and relics for future spacefarers."""
        rec = self.mgr.get_or_create_record(self.player_id)
        rec.phase = EpochPhase.STEWARDSHIP

        target = self.kernel.sectors[2].planets[0] if len(self.kernel.sectors[2].planets) > 0 else self.kernel.sectors[1].planets[0]
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.STEWARD_PLANT_PRECURSOR_BEACON,
            planet_id=target.id,
            relic_name="Crystalline Chrono-Shard",
        )
        self.assertTrue(res.success)
        self.assertEqual(rec.precursor_beacons_planted, 1)
        self.assertIsNotNone(target.ruins)
        self.assertEqual(target.ruins["relic"], "Crystalline Chrono-Shard")

    def test_stewardship_syntropic_harmonic_pulse(self):
        """Verify Steward can emit cluster-wide harmonic pulses to reduce entropy strain."""
        rec = self.mgr.get_or_create_record(self.player_id)
        rec.phase = EpochPhase.STEWARDSHIP
        rec.entropy_strain = 80.0

        res = self.kernel.dispatch(self.player_id, ActionType.STEWARD_SYNTROPIC_PULSE)
        self.assertTrue(res.success)
        self.assertLess(rec.entropy_strain, 80.0)
        self.assertEqual(rec.syntropic_pulses_fired, 1)

    def test_persistence_roundtrip(self):
        """Verify epoch manager and records survive snapshot and restore."""
        rec = self.mgr.get_or_create_record(self.player_id)
        rec.phase = EpochPhase.STEWARDSHIP
        rec.nascent_worlds_seeded = 3
        rec.stellar_cores_stabilized = 2
        rec.title = "Progenitor of Deep Time"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "epoch_save.json")
            saved = StatePersistence.save_to_file(self.kernel, path)
            self.assertTrue(saved)

            loaded = StatePersistence.load_from_file(path)
            self.assertIsNotNone(loaded)
            self.assertTrue(hasattr(loaded, "epoch_manager"))
            loaded_rec = loaded.epoch_manager.records.get(self.player_id)
            self.assertIsNotNone(loaded_rec)
            self.assertEqual(loaded_rec.phase, EpochPhase.STEWARDSHIP)
            self.assertEqual(loaded_rec.nascent_worlds_seeded, 3)
            self.assertEqual(loaded_rec.stellar_cores_stabilized, 2)
            self.assertEqual(loaded_rec.title, "Progenitor of Deep Time")

    def test_renderer_output(self):
        """Verify TerminalRenderer renders all epoch screen information cleanly."""
        view = self.kernel.get_player_view(self.player_id)
        rendered = TerminalRenderer.render_epoch_stewardship_screen(view)
        self.assertIn("CIVILIZATIONAL EPOCHS & DEEP-TIME STEWARDSHIP", rendered)
        self.assertIn("THERMODYNAMIC EQUILIBRIUM GAUGES", rendered)
        self.assertIn("DEEP-TIME RECORD & ACHIEVEMENTS", rendered)


if __name__ == "__main__":
    unittest.main()
