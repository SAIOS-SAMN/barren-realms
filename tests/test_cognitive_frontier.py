"""
Unit tests for the Two-Tier Cognitive Economy, Breakthrough Tech Tree,
Cosmic Anomalies, Lazy Procedural Frontier Clusters (The Observation Law),
and Autonomous AI "Mint vs. Raid" Dilemma in Xylarium.
"""

import unittest
import tempfile
import os

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, AIPersonality, SecurityLevel
from xylarium.kernel.research import TECH_TREE, CosmicAnomaly
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer


class TestCognitiveMetabolismAndTechTree(unittest.TestCase):
    """Test Suite 1: Two-Tier Cognitive Economy & Breakthrough Unlocks."""

    def setUp(self):
        self.kernel = GameKernel(seed=101)
        self.player = self.kernel.register_player("tester", "Test Captain")

    def test_commission_active_research(self):
        """Captains can commission active research breakthrough projects."""
        res = self.kernel.dispatch(self.player.id, ActionType.RESEARCH_SELECT, tech_key="JUMP_DRIVE")
        self.assertTrue(res.success)
        self.assertEqual(self.player.active_research, "JUMP_DRIVE")

        # Duplicate commission of already unlocked tech should fail once unlocked
        self.player.technologies.append("JUMP_DRIVE")
        res2 = self.kernel.dispatch(self.player.id, ActionType.RESEARCH_SELECT, tech_key="JUMP_DRIVE")
        self.assertFalse(res2.success)

    def test_planetary_deep_cognition_yields_research(self):
        """Colonies with luxury element reserves enter Deep Cognition, advancing research."""
        # Find a planet in the universe and colonize it
        planet = next(p for s in self.kernel.sectors.values() for p in s.planets)
        planet.owner_id = self.player.id
        planet.population = 800
        planet.morale = 90
        # Tier 2 Exotic/Luxury elements: Cryogenite, Stelalith, Chitinium, etc.
        planet.element_reserves = {"cryogenite": 5, "stelalith": 3}

        # Commission research
        self.player.active_research = "BIO_SYNTHESIZER"
        self.player.research_progress = 0

        # Advance cognitive metabolism
        initial_cryo = planet.element_reserves["cryogenite"]
        initial_stela = planet.element_reserves["stelalith"]
        self.kernel.research_manager.tick_cognitive_metabolism(self.kernel)

        # 1 unit consumed, research advanced by +15 RP
        curr_total = planet.element_reserves["cryogenite"] + planet.element_reserves["stelalith"]
        self.assertEqual(curr_total, (initial_cryo + initial_stela) - 1)
        self.assertEqual(self.player.research_progress, 15)

    def test_research_completion_unlocks_technology(self):
        """Reaching breakthrough threshold unlocks technology and resets active project."""
        planet = next(p for s in self.kernel.sectors.values() for p in s.planets)
        planet.owner_id = self.player.id
        planet.population = 600
        planet.morale = 80
        planet.element_reserves = {"cryogenite": 10}

        self.player.active_research = "BIO_SYNTHESIZER"
        cost = TECH_TREE["BIO_SYNTHESIZER"]["cost_research"]
        self.player.research_progress = cost - 10  # 1 tick will push it over

        self.kernel.research_manager.tick_cognitive_metabolism(self.kernel)

        self.assertIn("BIO_SYNTHESIZER", self.player.technologies)
        self.assertIn("BIO_SYNTHESIZER", planet.technologies)
        self.assertIsNone(self.player.active_research)
        self.assertEqual(self.player.research_progress, 0)

    def test_passive_tech_effects(self):
        """Unlocked technologies exert persistent metabolic and defense benefits."""
        # 1. Nanite Drydock: repairs shields and replenishes fighters
        self.player.technologies.append("NANITE_DRYDOCK")
        self.player.ship.shields = 50
        self.player.ship.max_shields = 100
        self.player.ship.fighters = 5

        self.kernel.research_manager.tick_cognitive_metabolism(self.kernel)
        self.assertEqual(self.player.ship.shields, 65)  # +15 MW
        self.assertEqual(self.player.ship.fighters, 6)   # +1 fighter

        # 2. Bio-Synthesizer: converts surplus Ore to Organics on colonies
        planet = next(p for s in self.kernel.sectors.values() for p in s.planets)
        planet.owner_id = self.player.id
        planet.ore_silo = 50
        planet.organics_silo = 20
        self.player.technologies.append("BIO_SYNTHESIZER")

        self.kernel.research_manager.tick_cognitive_metabolism(self.kernel)
        self.assertEqual(planet.ore_silo, 45)
        self.assertEqual(planet.organics_silo, 25)


class TestCosmicAnomalies(unittest.TestCase):
    """Test Suite 2: Cosmic Precursor Relics and Anomaly Investigations."""

    def setUp(self):
        self.kernel = GameKernel(seed=202)
        self.player = self.kernel.register_player("explorer", "Explorer Jane")

    def test_initial_anomalies_seeded_in_anarchy(self):
        """Initial precursor anomalies are seeded across deep void sectors."""
        anoms = self.kernel.research_manager.anomalies
        self.assertGreaterEqual(len(anoms), 5)
        self.assertIn("ANOM-101", anoms)
        a101 = anoms["ANOM-101"]
        self.assertEqual(a101.sector_id, 68)
        self.assertIn("ANOM-101", self.kernel.sectors[68].anomalies)

    def test_investigate_anomaly_wrong_sector_rejected(self):
        """Cannot investigate an anomaly located in another sector."""
        self.player.sector_id = 1
        res = self.kernel.dispatch(self.player.id, ActionType.ANOMALY_INVESTIGATE, anomaly_id="ANOM-101")
        self.assertFalse(res.success)
        self.assertIn("Sector 068", res.message)

    def test_investigate_anomaly_puzzle_solution(self):
        """Solving harmonic resonance frequency unlocks anomaly, tech, and bounty."""
        self.player.sector_id = 68
        self.kernel.sectors[68].captains.append(self.player.id)
        a101 = self.kernel.research_manager.anomalies["ANOM-101"]

        # Wrong frequency fails
        res_fail = self.kernel.dispatch(
            self.player.id,
            ActionType.ANOMALY_INVESTIGATE,
            anomaly_id="ANOM-101",
            solve_inputs={"mode": "solve", "value": 999}
        )
        self.assertFalse(res_fail.success)

        # Correct frequency succeeds
        initial_cr = self.player.credits
        res_ok = self.kernel.dispatch(
            self.player.id,
            ActionType.ANOMALY_INVESTIGATE,
            anomaly_id="ANOM-101",
            solve_inputs={"mode": "solve", "value": a101.puzzle_target}
        )
        self.assertTrue(res_ok.success)
        self.assertEqual(a101.status, "SOLVED")
        self.assertEqual(a101.solved_by, self.player.name)
        self.assertEqual(self.player.credits, initial_cr + a101.reward_credits)
        self.assertIn(a101.reward_tech, self.player.technologies)

    def test_investigate_anomaly_catalyst_mode(self):
        """Computational catalyst probe spends credits to decrypt anomaly."""
        self.player.sector_id = 77
        self.kernel.sectors[77].captains.append(self.player.id)
        self.player.credits = 5000
        a102 = self.kernel.research_manager.anomalies["ANOM-102"]

        res = self.kernel.dispatch(
            self.player.id,
            ActionType.ANOMALY_INVESTIGATE,
            anomaly_id="ANOM-102",
            solve_inputs={"mode": "catalyst"}
        )
        self.assertTrue(res.success)
        self.assertEqual(a102.status, "SOLVED")
        self.assertIn("NANITE_DRYDOCK", self.player.technologies)


class TestFrontierObservationLaw(unittest.TestCase):
    """Test Suite 3: Lazy Procedural Frontier Clusters & Jump Drive."""

    def setUp(self):
        self.kernel = GameKernel(seed=303)
        self.player = self.kernel.register_player("navigator", "Navigator Jack")

    def test_mint_cluster_2_perseus_veil(self):
        """Observation Law mints Cluster 2 (The Perseus Veil, Sectors 201-240; 101-199 are reserved for ghost sectors)."""
        rm = self.kernel.research_manager
        ok, msg, new_secs = rm.mint_frontier_cluster(self.kernel, 2)
        self.assertTrue(ok)
        self.assertEqual(len(new_secs), 40)
        self.assertIn(201, self.kernel.sectors)
        self.assertIn(240, self.kernel.sectors)

        # Check cluster name assigned
        sec_101 = self.kernel.sectors[201]
        self.assertEqual(sec_101.cluster_name, "The Perseus Veil")

        # Check bridge lanes from anchor sectors (91-100)
        has_bridge = any(
            any(w >= 201 for w in self.kernel.sectors[anc].warps)
            for anc in range(91, 101)
        )
        self.assertTrue(has_bridge)

        # Check uncharted planets with exotic deposits seeded
        planets_in_veil = [
            p for s_id in new_secs for p in self.kernel.sectors[s_id].planets
        ]
        self.assertGreater(len(planets_in_veil), 0)
        self.assertTrue(any("cryogenite" in p.element_deposits for p in planets_in_veil))
        # The new cluster follows the same physical layout: systems separated by null space
        kinds = {self.kernel.sectors[s].kind for s in new_secs}
        self.assertEqual(kinds, {"SYSTEM", "NULL"})

    def test_jump_warp_drive_navigation(self):
        """Jump Drive allows hyper-dimensional transit and auto-mints frontier space."""
        self.player.technologies.append("JUMP_DRIVE")
        self.player.credits = 1000
        self.player.sector_id = 1

        # Jump to charted sector 42
        res = self.kernel.dispatch(self.player.id, ActionType.JUMP_WARP, destination=42)
        self.assertTrue(res.success)
        self.assertEqual(self.player.sector_id, 42)

        # Jump to uncharted frontier sector 215 (auto-mints Cluster 2!)
        res_frontier = self.kernel.dispatch(self.player.id, ActionType.JUMP_WARP, destination=215)
        self.assertTrue(res_frontier.success)
        self.assertEqual(self.player.sector_id, 215)
        self.assertIn(2, self.kernel.research_manager.minted_clusters)
        self.assertIn(215, self.kernel.sectors)

    def test_reaching_perimeter_triggers_observation_law(self):
        """Moving to perimeter sector 99 automatically charters Cluster 2."""
        # Connect sector 1 to 99 for direct test move
        self.kernel.sectors[1].warps.append(99)
        self.kernel.sectors[99].warps.append(1)

        self.assertNotIn(2, self.kernel.research_manager.minted_clusters)
        res = self.kernel.dispatch(self.player.id, ActionType.MOVE, destination=99)
        self.assertTrue(res.success)
        self.assertEqual(self.player.sector_id, 99)
        self.assertIn(2, self.kernel.research_manager.minted_clusters)
        self.assertIn(201, self.kernel.sectors)


class TestAIMintVsRaid(unittest.TestCase):
    """Test Suite 4: Autonomous AI 'Mint vs Raid' Decision Loops."""

    def setUp(self):
        self.kernel = GameKernel(seed=404)
        self.player = self.kernel.register_player("human", "Human Trader")

    def test_ai_captains_commission_personality_research(self):
        """AI rivals commission breakthrough research tailored to their personality."""
        voss = self.kernel.captains["ai_voss"]
        malakor = self.kernel.captains["ai_malakor"]
        vane = self.kernel.captains["ai_vane"]
        ironclaw = self.kernel.captains["ai_ironclaw"]

        # Run 1 simulation tick to trigger AI turns
        self.kernel.tick_simulation()

        self.assertIsNotNone(voss.active_research)
        self.assertIn(voss.active_research, ["ORBITAL_FOUNDRY", "BIO_SYNTHESIZER", "NANITE_DRYDOCK"])

        self.assertIsNotNone(malakor.active_research)
        self.assertIn(malakor.active_research, ["CLOAKING_GRID", "JUMP_DRIVE", "NANITE_DRYDOCK"])

        self.assertIsNotNone(vane.active_research)
        self.assertIn(vane.active_research, ["JUMP_DRIVE", "BIO_SYNTHESIZER", "ORBITAL_FOUNDRY"])

        self.assertIsNotNone(ironclaw.active_research)
        self.assertIn(ironclaw.active_research, ["NANITE_DRYDOCK", "CLOAKING_GRID", "JUMP_DRIVE"])

    def test_ai_cracks_relic_in_sector(self):
        """AI captains investigate and solve anomalies when present in sector."""
        voss = self.kernel.captains["ai_voss"]
        voss.credits = 10000
        voss.sector_id = 68
        self.kernel.sectors[68].captains.append(voss.id)
        a101 = self.kernel.research_manager.anomalies["ANOM-101"]

        self.kernel.tick_simulation()
        self.assertEqual(a101.status, "SOLVED")


class TestCognitiveFrontierPersistenceAndRenderer(unittest.TestCase):
    """Test Suite 5: Persistence and ANSI Screen Renders."""

    def test_research_state_persists(self):
        """ResearchManager, anomalies, and active breakthroughs persist across save/load."""
        kernel1 = GameKernel(seed=505)
        p = kernel1.register_player("persist_tester", "Captain Persist")
        p.active_research = "CLOAKING_GRID"
        p.research_progress = 45
        p.technologies.append("JUMP_DRIVE")
        kernel1.research_manager.mint_frontier_cluster(kernel1, 2)
        kernel1.research_manager.anomalies["ANOM-101"].status = "SOLVED"

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            filepath = tf.name

        try:
            saved = StatePersistence.save_to_file(kernel1, filepath)
            self.assertTrue(saved)

            kernel2 = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(kernel2)
            p2 = kernel2.get_player("persist_tester")
            self.assertEqual(p2.active_research, "CLOAKING_GRID")
            self.assertEqual(p2.research_progress, 45)
            self.assertIn("JUMP_DRIVE", p2.technologies)
            self.assertIn(2, kernel2.research_manager.minted_clusters)
            self.assertEqual(kernel2.research_manager.anomalies["ANOM-101"].status, "SOLVED")
            self.assertIn(201, kernel2.sectors)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_tech_tree_and_anomaly_renderers(self):
        """Verify terminal screen renderers execute cleanly without formatting exceptions."""
        kernel = GameKernel(seed=606)
        p = kernel.register_player("render_tester", "Captain Render")
        view = kernel.get_player_view(p.id)

        hud = TerminalRenderer.render_hud(view)
        self.assertIn("XYLARIUM BBS", hud)

        sec_screen = TerminalRenderer.render_sector(view)
        self.assertIn("Federation Core", sec_screen)

        tech_screen = TerminalRenderer.render_tech_tree_screen(view)
        self.assertIn("COGNITIVE ECONOMY", tech_screen)
        self.assertIn("Hyper-Dimensional Jump Drive", tech_screen)

        a101 = kernel.research_manager.anomalies["ANOM-101"]
        anom_screen = TerminalRenderer.render_anomaly_screen(view, a101.to_dict())
        self.assertIn("Precursor Resonance Monolith", anom_screen)
        self.assertIn("Target: 35", anom_screen)


if __name__ == "__main__":
    unittest.main()
