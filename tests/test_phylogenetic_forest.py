"""
Unit and integration tests for the Phylogenetic Forest of Ascension (Cladogram DAG Engine).
Tests 4D Cochain Flux tracking, No-Scalar dot-product gravitation, biological root divergence,
lateral Precursor Chimerism grafting, and Apex Sovereign Canopy Invariant Overrides.
"""

import unittest
from xylarium.config import PHYLOGENY_TIER_EXPERIENCE
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Captain, Ship, CargoHold
from xylarium.kernel.phylogeny import PHYLOGENY_MANAGER, CochainFlux, PhylogeneticNode


class TestPhylogeneticForest(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.manager = PHYLOGENY_MANAGER
        self.player_id = "test_phylogeny_captain"

    def test_cochain_flux_normalization(self):
        """Verifies 4D Cochain Flux vector accumulates activity and normalizes to 1.0 exact-rational fractions."""
        flux = CochainFlux()
        self.assertEqual(flux.normalized(), {"mass": 0.25, "thermodynamic": 0.25, "exotic": 0.25, "entropic": 0.25})

        flux.record_activity(mass_delta=80.0, thermo_delta=10.0, exotic_delta=10.0, entropic_delta=0.0)
        norm = flux.normalized()
        self.assertAlmostEqual(sum(norm.values()), 1.0, places=3)
        self.assertEqual(norm["mass"], 0.8)
        self.assertEqual(norm["thermodynamic"], 0.1)
        self.assertEqual(norm["exotic"], 0.1)
        self.assertEqual(norm["entropic"], 0.0)

        # Test dictionary round-trip
        data = flux.to_dict()
        reconstructed = CochainFlux.from_dict(data)
        self.assertEqual(reconstructed.mass, 80.0)
        self.assertEqual(reconstructed.thermodynamic, 10.0)

    def test_biological_roots_assignment(self):
        """Verifies that captains automatically inherit distinct primordial root nodes based on species and clade."""
        # 1. Biotic / Humanoid
        cap_bio = self.kernel.register_player("bio_1", "Sol Trader", clade="BIOTIC", species="human-sol")
        self.assertEqual(cap_bio.phylogeny_node_id, "root_biotic")
        self.assertEqual(cap_bio.rank_title, "Scrap-Apprentice")
        self.assertEqual(cap_bio.rank_role, "Scout Salvager")

        # 2. Lithic / Lithomorph
        cap_lith = self.kernel.register_player("lith_1", "Endolithid Mason", clade="LITHIC", species="lithic-silicon")
        self.assertEqual(cap_lith.phylogeny_node_id, "root_lithic")
        self.assertEqual(cap_lith.rank_title, "Core-Driller")
        self.assertEqual(cap_lith.rank_role, "Deep-Mantle Excavator")

        # 3. Plasmic / Coronal
        cap_plasm = self.kernel.register_player("plasm_1", "Actinoid Spark", clade="PLASMIC", species="plasmic-solar")
        self.assertEqual(cap_plasm.phylogeny_node_id, "root_plasmic")
        self.assertEqual(cap_plasm.rank_title, "Spark-Bound")

        # 4. Cryogenic / Stillcold
        cap_cryo = self.kernel.register_player("cryo_1", "Stillcold Logic", clade="CRYOGENIC", species="cryocoherent-still")
        self.assertEqual(cap_cryo.phylogeny_node_id, "root_cryo")
        self.assertEqual(cap_cryo.rank_title, "Zero-Kelvin Novice")

        # 5. Anarchy / Outlaw
        cap_anar = self.kernel.register_player("anar_1", "Void Marauder", clade="ANARCHY", species="human-outlaw")
        self.assertEqual(cap_anar.phylogeny_node_id, "root_anarchy")
        self.assertEqual(cap_anar.rank_title, "Void Drifter")

    def test_dot_product_branch_gravitation(self):
        """Verifies that rolling activity flux naturally pitches captain towards affinity-matched DAG branches."""
        player = self.kernel.register_player(self.player_id, "Divergence Seeker", clade="BIOTIC")
        self.assertEqual(player.phylogeny_node_id, "root_biotic")

        # Heavily trade bulk mass (Ore, Fe)
        self.manager.record_activity_flux(player, mass_delta=100.0, thermo_delta=5.0, exotic_delta=10.0, entropic_delta=0.0)
        affinities_mass = self.manager.compute_branch_affinities(player)
        # Biotic roots branch into biotic_supercargo (mass 0.50) and biotic_scribe (exotic 0.60)
        self.assertGreater(affinities_mass["biotic_supercargo"], affinities_mass["biotic_scribe"])

        # Shift behavior completely to exotic finance and treaties
        player.cochain_flux = CochainFlux().to_dict()
        self.manager.record_activity_flux(player, mass_delta=5.0, thermo_delta=5.0, exotic_delta=90.0, entropic_delta=0.0)
        affinities_exotic = self.manager.compute_branch_affinities(player)
        self.assertGreater(affinities_exotic["biotic_scribe"], affinities_exotic["biotic_supercargo"])

    def test_phylogenetic_ascension_dispatch_and_crystallization(self):
        """Verifies ActionType.PHYLOGENY_ASCEND crystallizes branch divergence and grants endowments."""
        player = self.kernel.register_player(self.player_id, "Ascending Scholar", clade="BIOTIC")

        # Attempt ascension before meeting invariants
        res_fail = self.kernel.dispatch(self.player_id, ActionType.PHYLOGENY_ASCEND)
        self.assertFalse(res_fail.success)
        self.assertIn("Ascension invariants unmet", res_fail.message)

        # Qualify player for Tier 2 Epistemic Scribe
        player.experience_score = PHYLOGENY_TIER_EXPERIENCE[2] + 50
        player.credit_rating = 580
        player.grown_basis.append({"rcf_sig": "RCF-01", "name": "Basis Crystal Alpha"})
        self.manager.record_activity_flux(player, mass_delta=0.0, thermo_delta=0.0, exotic_delta=100.0, entropic_delta=0.0)

        res_ok = self.kernel.dispatch(self.player_id, ActionType.PHYLOGENY_ASCEND, target_node_id="biotic_scribe")
        self.assertTrue(res_ok.success)
        self.assertEqual(player.phylogeny_node_id, "biotic_scribe")
        self.assertEqual(player.rank_tier, 2)
        self.assertEqual(player.rank_title, "Epistemic Scribe")
        self.assertEqual(player.rank_role, "Syntropic Ledger Chronicler")
        self.assertIn("biotic_scribe", player.unlocked_phylogeny_nodes)
        self.assertGreater(player.credits, 1500)

    def test_precursor_chimerism_lateral_grafting(self):
        """Verifies lateral Precursor Chimerism synthesized via Cartography Lab consumes catalytic specs."""
        player = self.kernel.register_player(self.player_id, "Alchemical Transhumanist", clade="BIOTIC")
        # Advance to Corporate Director (Tier 3 parent for Absolute-Zero Alchemist)
        player.phylogeny_node_id = "biotic_director"
        player.rank_tier = 3

        # Graft without catalytic materials should fail
        res_no_mats = self.kernel.dispatch(
            self.player_id,
            ActionType.CARTOGRAPHY_FORGE_CHIT,
            mode="chimera",
            hybrid_node_id="chimera_absolute_zero_alchemist",
        )
        self.assertFalse(res_no_mats.success)
        self.assertIn("CHIMERIC SYNTHESIS FAILED", res_no_mats.message)

        # Provide Uranium and Cryogenite in holds + genuine fragment
        player.ship.cargo.elements["U"] = 10
        player.ship.cargo.elements["cryogenite"] = 15
        player.cartography_fragments.append({"id": "FRAG-TEST", "name": "Ancient Cipher Fragment"})
        player.credits = 10000

        res_graft = self.kernel.dispatch(
            self.player_id,
            ActionType.CARTOGRAPHY_FORGE_CHIT,
            mode="chimera",
            hybrid_node_id="chimera_absolute_zero_alchemist",
        )
        self.assertTrue(res_graft.success)
        self.assertEqual(player.phylogeny_node_id, "chimera_absolute_zero_alchemist")
        self.assertEqual(player.rank_title, "Absolute-Zero Alchemist")
        self.assertEqual(player.clade, "CHIMERA")
        self.assertIn("chimera_absolute_zero_alchemist", player.chimeric_grafts)

        # Verify materials consumed
        self.assertEqual(player.ship.cargo.elements.get("U", 0), 0)
        self.assertEqual(player.ship.cargo.elements.get("cryogenite", 0), 0)

    def test_canopy_invariant_overrides_physics_rewrites(self):
        """Verifies Tier 4 Apex Sovereign leaf nodes grant reality-rewriting canopy overrides."""
        # 1. Tectonic Litharch: SEISMIC_MANIFOLD_COLLAPSE
        player_lith = self.kernel.register_player("apex_lith", "Gorgon Core", clade="LITHIC")
        player_lith.phylogeny_node_id = "lith_litharch"
        player_lith.rank_tier = 4
        player_lith.sector_id = 45

        res_seismic = self.kernel.dispatch("apex_lith", ActionType.CANOPY_OVERRIDE)
        self.assertTrue(res_seismic.success)
        self.assertIn("SEISMIC MANIFOLD COLLAPSE", res_seismic.message)
        self.assertEqual(player_lith.active_canopy_override, "SEISMIC_MANIFOLD_COLLAPSE")
        # Collapsed planetary shields in sector
        sec_45 = self.kernel.sectors[45]
        for p in sec_45.planets:
            self.assertEqual(p.shields, 0)

        # 2. Absolute Zero Mind: ENTROPY_ZERO_EQUILIBRIUM
        player_cryo = self.kernel.register_player("apex_cryo", "Zero Entity", clade="CRYOGENIC")
        player_cryo.phylogeny_node_id = "cryo_absolute_zero_mind"
        player_cryo.rank_tier = 4

        res_freeze = self.kernel.dispatch("apex_cryo", ActionType.CANOPY_OVERRIDE)
        self.assertTrue(res_freeze.success)
        self.assertIn("ENTROPY ZERO EQUILIBRIUM", res_freeze.message)
        self.assertEqual(player_cryo.active_canopy_override, "ENTROPY_ZERO_EQUILIBRIUM")

        # 3. Shadow Hegemon: SUBSPACE_SIGNATURE_SPOOF
        player_pirate = self.kernel.register_player("apex_pirate", "Khorne Reaver", clade="ANARCHY")
        player_pirate.phylogeny_node_id = "anarchy_shadow_hegemon"
        player_pirate.rank_tier = 4
        player_pirate.sector_id = 88

        res_spoof = self.kernel.dispatch("apex_pirate", ActionType.CANOPY_OVERRIDE)
        self.assertTrue(res_spoof.success)
        self.assertIn("SUBSPACE SIGNATURE SPOOF", res_spoof.message)
        self.assertEqual(player_pirate.active_canopy_override, "SUBSPACE_SIGNATURE_SPOOF")

        # 4. Galactic Archon: IMPERIAL_SENATE_MONOPOLY
        player_archon = self.kernel.register_player("apex_archon", "Baron Rothschild", clade="BIOTIC")
        player_archon.phylogeny_node_id = "biotic_archon"
        player_archon.rank_tier = 4
        init_cr = player_archon.credits

        res_senate = self.kernel.dispatch("apex_archon", ActionType.CANOPY_OVERRIDE)
        self.assertTrue(res_senate.success)
        self.assertIn("IMPERIAL SENATE MONOPOLY", res_senate.message)
        self.assertEqual(player_archon.credits, init_cr + 25000)

        # 5. Corona Sovereign: THERMODYNAMIC_SUPERNOVA_CATALYSIS
        player_plasma = self.kernel.register_player("apex_plasma", "Solar Flare", clade="PLASMIC")
        player_plasma.phylogeny_node_id = "plasmic_corona_sovereign"
        player_plasma.rank_tier = 4
        player_plasma.turns_left = 50

        res_supernova = self.kernel.dispatch("apex_plasma", ActionType.CANOPY_OVERRIDE)
        self.assertTrue(res_supernova.success)
        self.assertIn("THERMODYNAMIC SUPERNOVA CATALYSIS", res_supernova.message)
        self.assertEqual(player_plasma.turns_left, 150)

    def test_ascii_cladogram_radar_rendering(self):
        """Verifies the ASCII Cladogram Radar renders valid diagnostic strings with affinities."""
        player = self.kernel.register_player(self.player_id, "Radar Pilot", clade="BIOTIC")
        ascii_view = self.manager.render_ascii_cladogram(player)
        self.assertIn("PHYLOGENETIC ASCENSION CLADOGRAM", ascii_view)
        self.assertIn("Lineage Clade: [BIOTIC]", ascii_view)
        self.assertIn("SCRAP-APPRENTICE", ascii_view)
        self.assertIn("Rolling Action Flux Vector", ascii_view)

        # Full player view includes phylogeny snapshot
        p_view = self.kernel.get_player_view(self.player_id)
        self.assertIn("phylogeny", p_view)
        self.assertEqual(p_view["phylogeny"]["current_node"]["id"], "root_biotic")
        self.assertIn("affinities", p_view["phylogeny"])

    def test_ascension_rejects_non_gravitating_or_skip_tier_targets(self):
        """Ascension is emergent: only the flux-pitched natural child may crystallize."""
        player = self.kernel.register_player(self.player_id, "Tier Skipper", clade="BIOTIC")
        player.experience_score = 5000
        player.credit_rating = 900
        player.credits = 1_000_000
        player.grown_basis.extend({"rcf_sig": f"RCF-{i}"} for i in range(10))
        self.manager.record_activity_flux(player, mass_delta=100.0)

        res_skip = self.kernel.dispatch(self.player_id, ActionType.PHYLOGENY_ASCEND, target_node_id="biotic_archon")
        self.assertFalse(res_skip.success)
        self.assertEqual(player.phylogeny_node_id, "root_biotic")

        res_against = self.kernel.dispatch(self.player_id, ActionType.PHYLOGENY_ASCEND, target_node_id="biotic_scribe")
        self.assertFalse(res_against.success)
        self.assertIn("does not pitch toward", res_against.message)

    def test_chimera_not_reachable_by_natural_ascension(self):
        """Lateral hybrids never appear as natural branches; they must be grafted."""
        player = self.kernel.register_player(self.player_id, "Director", clade="BIOTIC")
        player.phylogeny_node_id = "biotic_director"
        player.rank_tier = 3
        self.manager.record_activity_flux(player, thermo_delta=100.0)
        affinities = self.manager.compute_branch_affinities(player)
        self.assertNotIn("chimera_absolute_zero_alchemist", affinities)
        self.assertIn("biotic_archon", affinities)

    def test_non_trade_actions_record_flux(self):
        """Successful non-trade actions feed their flux signature into the cochain window."""
        player = self.kernel.register_player(self.player_id, "Flux Tracker", clade="ANARCHY")
        before = player.cochain_flux.get("total_cycles_tracked", 0)
        self.manager.record_action_flux(player, "ATTACK_SHIP")
        self.assertEqual(player.cochain_flux["total_cycles_tracked"], before + 1)
        self.assertGreater(player.cochain_flux["entropic"], 0.0)
        self.assertIsNone(self.manager.record_action_flux(player, "SCAN"))

    def test_rolling_window_lets_behavior_repitch_branch(self):
        """Old flux decays so sustained new behavior re-pitches the gravitating branch."""
        player = self.kernel.register_player(self.player_id, "Repitcher", clade="BIOTIC")
        self.manager.record_activity_flux(player, mass_delta=1000.0)
        for _ in range(300):
            self.manager.record_activity_flux(player, exotic_delta=10.0)
        aff = self.manager.compute_branch_affinities(player)
        self.assertGreater(aff["biotic_scribe"], aff["biotic_supercargo"])

    def test_entropy_zero_bypasses_federation_turrets(self):
        """ENTROPY_ZERO_EQUILIBRIUM hides an outlaw from Core defense turrets."""
        player = self.kernel.register_player("zero_outlaw", "Cold Outlaw", clade="ANARCHY")
        sector = self.kernel.sectors[1]
        self.assertIsNotNone(self.kernel._check_federation_turrets(player, sector, ActionType.TRADE))
        player.active_canopy_override = "ENTROPY_ZERO_EQUILIBRIUM"
        self.assertIsNone(self.kernel._check_federation_turrets(player, sector, ActionType.TRADE))

    def test_save_load_round_trip_keeps_phylogeny(self):
        """Loaded kernels have a phylogeny manager and preserve captain lineage state."""
        import os
        import tempfile
        from xylarium.persistence.store import StatePersistence

        player = self.kernel.register_player(self.player_id, "Persisted", clade="LITHIC")
        self.manager.record_activity_flux(player, mass_delta=42.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "save.json")
            self.assertTrue(StatePersistence.save_to_file(self.kernel, path))
            loaded = StatePersistence.load_from_file(path)
        self.assertIsNotNone(loaded)
        self.assertIs(loaded.phylogeny_manager, self.manager)
        cap = loaded.get_player(self.player_id)
        self.assertEqual(cap.phylogeny_node_id, "root_lithic")
        self.assertAlmostEqual(cap.cochain_flux["mass"], 42.0)
        view = loaded.get_player_view(self.player_id)
        self.assertEqual(view["phylogeny"]["current_node"]["id"], "root_lithic")


if __name__ == "__main__":
    unittest.main()
