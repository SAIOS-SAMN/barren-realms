"""
Comprehensive Unit & Integration Test Suite for Universe Expansions:
1. GalNet Newsfeed & Systemic Galactic Crises
2. Deep-Space Megastructures & Precursor Derelicts
3. Living Bio-Fleet Swarms & Tactical Doctrines
4. Biosphere Genesis & Planetary Terraforming
"""

import os
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer
from xylarium.kernel.megastructures import MEGASTRUCTURE_CATALOG, RELIC_ARTIFACTS
from xylarium.kernel.biofleets import BIO_VESSEL_CLASSES, TACTICAL_DOCTRINES


class TestUniverseExpansions(unittest.TestCase):
    def setUp(self):
        """Initializes a clean GameKernel with standard seed."""
        self.kernel = GameKernel(seed=1337)
        self.player_id = "test_player"
        self.kernel.register_player(self.player_id, "Commander Shepard")
        self.player = self.kernel.get_player(self.player_id)
        self.player.turns = 500
        self.player.credits = 10000000
        self.player.fx_wallet["SOL"] = 10000000

    # =========================================================================
    # VECTOR 1: GalNet Newsfeed & Systemic Galactic Crises
    # =========================================================================
    def test_crises_initial_seeding_and_newsfeed(self):
        mgr = self.kernel.crises_manager
        self.assertGreaterEqual(len(mgr.news_history), 2)
        self.assertGreaterEqual(len(mgr.active_crises), 1)

        crisis = list(mgr.active_crises.values())[0]
        self.assertEqual(crisis.crisis_type, "XENOPATHIC_CONTAGION")
        self.assertEqual(crisis.status, "ACTIVE")

    def test_crisis_relief_dispatch(self):
        mgr = self.kernel.crises_manager
        crisis = list(mgr.active_crises.values())[0]
        self.player.sector_id = crisis.sector_id

        # Stock hold with organics
        self.player.ship.cargo.elements["ORGANICS"] = 50

        req_needed = crisis.relief_required - crisis.relief_delivered
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.CRISIS_RELIEF_DISPATCH,
            crisis_id=crisis.id,
            commodity="ORGANICS",
            amount=req_needed,
        )
        self.assertTrue(res.success)
        self.assertGreaterEqual(crisis.relief_delivered, crisis.relief_required)
        self.assertIn(crisis.status, ["CONTAINED", "RESOLVED"])

    def test_spawn_and_tick_crises(self):
        mgr = self.kernel.crises_manager
        c = mgr.spawn_crisis(
            "SOLAR_SUPERFLARE",
            sector_id=1,
            cycle=self.kernel.cycle_count,
            severity=0.8,
            duration=3,
            kernel=self.kernel,
        )
        self.assertIn(c.id, mgr.active_crises)

        # Advance simulation ticks until crisis expires
        for _ in range(5):
            self.kernel.tick_simulation()

        self.assertNotIn(c.id, mgr.active_crises)

    # =========================================================================
    # VECTOR 2: Deep-Space Megastructures & Precursor Derelicts
    # =========================================================================
    def test_initial_derelicts_seeded(self):
        mgr = self.kernel.megastructures_manager
        self.assertGreaterEqual(len(mgr.derelicts), 3)

    def test_megastructure_construction_progression(self):
        self.player.sector_id = 1
        mgr = self.kernel.megastructures_manager

        # Endow captain with necessary materials for ORBITAL_SKYHOOK (Ti: 70, Fe: 50)
        self.player.ship.cargo.elements["Ti"] = 100
        self.player.ship.cargo.elements["Fe"] = 100

        # Tranche 1 (25%)
        res1 = self.kernel.dispatch(
            self.player_id,
            ActionType.MEGASTRUCTURE_CONSTRUCT,
            structure_type="ORBITAL_SKYHOOK",
        )
        self.assertTrue(res1.success)
        proj = list(mgr.megastructures.values())[-1]
        self.assertEqual(proj.progress_pct, 25.0)
        self.assertEqual(proj.status, "CONSTRUCTING")

        # Complete all 4 tranches to reach 100%
        for _ in range(3):
            self.kernel.dispatch(
                self.player_id,
                ActionType.MEGASTRUCTURE_CONSTRUCT,
                structure_type="ORBITAL_SKYHOOK",
            )

        self.assertEqual(proj.progress_pct, 100.0)
        self.assertEqual(proj.status, "OPERATIONAL")

    def test_derelict_boarding_and_relic_recovery(self):
        mgr = self.kernel.megastructures_manager
        hulk = list(mgr.derelicts.values())[0]
        self.player.sector_id = hulk.sector_id
        self.player.ship.shields = 500

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.DERELICT_BOARD_EXPEDITION,
            hulk_id=hulk.id,
        )
        self.assertTrue(res.success)
        self.assertTrue(hulk.salvaged)
        self.assertIn("Fe", self.player.ship.cargo.elements)

    # =========================================================================
    # VECTOR 3: Living Bio-Fleet Swarms & Tactical Doctrines
    # =========================================================================
    def test_culture_bio_vessels(self):
        mgr = self.kernel.biofleets_manager
        self.player.ship.cargo.elements["ORGANICS"] = 100

        # Culture a Chitin Swarmer
        res1 = self.kernel.dispatch(
            self.player_id,
            ActionType.BIOFLEET_CULTURE_HULL,
            vessel_class="CHITIN_SWARMER",
        )
        self.assertTrue(res1.success)
        self.assertGreaterEqual(len(mgr.wings), 1)
        wing = list(mgr.wings.values())[0]
        self.assertEqual(len(wing.vessels), 1)

        # Culture a Void Manta into the same wing
        res2 = self.kernel.dispatch(
            self.player_id,
            ActionType.BIOFLEET_CULTURE_HULL,
            vessel_class="VOID_MANTA",
            wing_id=wing.id,
        )
        self.assertTrue(res2.success)
        self.assertEqual(len(wing.vessels), 2)

    def test_assign_tactical_doctrine_and_tick(self):
        mgr = self.kernel.biofleets_manager
        self.player.ship.cargo.elements["ORGANICS"] = 50

        self.kernel.dispatch(
            self.player_id,
            ActionType.BIOFLEET_CULTURE_HULL,
            vessel_class="CHITIN_SWARMER",
        )
        wing = list(mgr.wings.values())[0]

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.BIOFLEET_ASSIGN_DOCTRINE,
            wing_id=wing.id,
            doctrine="AUTONOMOUS_HARVESTER",
        )
        self.assertTrue(res.success)
        self.assertEqual(wing.doctrine, "AUTONOMOUS_HARVESTER")

        # Tick simulation and verify harvester active
        self.kernel.tick_simulation()
        self.assertGreater(self.player.ship.cargo.elements.get("ORGANICS", 0), 0)

    # =========================================================================
    # VECTOR 4: Biosphere Genesis & Planetary Terraforming
    # =========================================================================
    def test_comet_bombardment_and_habitability(self):
        sec = self.kernel.sectors[self.player.sector_id]
        if not sec.planets:
            for s in self.kernel.sectors.values():
                if s.planets:
                    self.player.sector_id = s.id
                    sec = s
                    break

        planet = sec.planets[0]
        mgr = self.kernel.biosphere_genesis_manager
        rec = mgr.get_or_create_record(planet)
        old_hydro = rec.hydrosphere_pct
        old_p = rec.atmospheric_pressure_bar

        self.player.ship.cargo.elements["H2O"] = 20
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.TERRAFORM_BOMBARD_COMET,
            planet_id=planet.id,
            volatiles_payload=5,
        )
        self.assertTrue(res.success)
        self.assertGreater(rec.hydrosphere_pct, old_hydro)
        self.assertGreater(rec.atmospheric_pressure_bar, old_p)

    def test_deploy_mirror_and_seed_biosphere(self):
        sec = self.kernel.sectors[self.player.sector_id]
        if not sec.planets:
            for s in self.kernel.sectors.values():
                if s.planets:
                    self.player.sector_id = s.id
                    sec = s
                    break

        planet = sec.planets[0]
        mgr = self.kernel.biosphere_genesis_manager
        rec = mgr.get_or_create_record(planet)

        # Deploy orbital mirror
        self.player.ship.cargo.elements["EQUIPMENT"] = 20
        res_m = self.kernel.dispatch(
            self.player_id,
            ActionType.TERRAFORM_DEPLOY_MIRROR,
            planet_id=planet.id,
        )
        self.assertTrue(res_m.success)
        self.assertGreaterEqual(rec.mirrors_deployed, 1)

        # Seed biosphere
        self.player.ship.cargo.elements["ORGANICS"] = 20
        res_s = self.kernel.dispatch(
            self.player_id,
            ActionType.TERRAFORM_SEED_BIOSPHERE,
            planet_id=planet.id,
            taxon_sample="Lichen Biome Delta",
        )
        self.assertTrue(res_s.success)
        self.assertIn("Lichen Biome Delta", rec.seeded_taxa)
        self.assertGreater(rec.trophic_biomass, 0.0)

    def test_sentient_species_emergence_on_high_habitability(self):
        sec = self.kernel.sectors[self.player.sector_id]
        if not sec.planets:
            for s in self.kernel.sectors.values():
                if s.planets:
                    self.player.sector_id = s.id
                    sec = s
                    break

        planet = sec.planets[0]
        mgr = self.kernel.biosphere_genesis_manager
        rec = mgr.get_or_create_record(planet)

        # Tune to paradise habitability
        rec.atmospheric_pressure_bar = 1.0
        rec.hydrosphere_pct = 60.0
        rec.greenhouse_index = 1.0
        rec.trophic_biomass = 100.0
        rec.update_habitability()
        self.assertGreaterEqual(rec.habitability_score, 0.85)

        # Tick simulation
        self.kernel.tick_simulation()
        self.assertTrue(rec.indigenous_born)

    # =========================================================================
    # PERSISTENCE & CLIENT VIEWS
    # =========================================================================
    def test_persistence_roundtrip_expansions(self):
        self.kernel.crises_manager.publish_article(
            "SPECIAL ANNOUNCEMENT: Test Bulletin",
            "FINANCE",
            "Testing save serialization.",
            cycle=self.kernel.cycle_count,
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            filepath = tf.name

        try:
            saved = StatePersistence.save_to_file(self.kernel, filepath)
            self.assertTrue(saved)

            loaded = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(loaded)
            self.assertTrue(hasattr(loaded, "crises_manager"))
            self.assertTrue(hasattr(loaded, "megastructures_manager"))
            self.assertTrue(hasattr(loaded, "biofleets_manager"))
            self.assertTrue(hasattr(loaded, "biosphere_genesis_manager"))
            self.assertEqual(len(loaded.crises_manager.news_history), len(self.kernel.crises_manager.news_history))
            self.assertEqual(len(loaded.megastructures_manager.derelicts), len(self.kernel.megastructures_manager.derelicts))
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_terminal_screens_render_cleanly(self):
        view = self.kernel.get_player_view(self.player_id)
        self.assertIn("crises", view)
        self.assertIn("megastructures", view)
        self.assertIn("biofleets", view)
        self.assertIn("biosphere_genesis", view)

        s_galnet = TerminalRenderer.render_galnet_screen(view)
        self.assertIn("GALNET SUBSPACE WIRE", s_galnet)

        s_mega = TerminalRenderer.render_megastructures_screen(view)
        self.assertIn("DEEP-SPACE MEGASTRUCTURES", s_mega)

        s_bio = TerminalRenderer.render_biofleets_screen(view)
        self.assertIn("LIVING BIO-FLEET SWARMS", s_bio)

        s_terra = TerminalRenderer.render_terraforming_screen(view)
        self.assertIn("BIOSPHERE GENESIS", s_terra)


if __name__ == "__main__":
    unittest.main()
