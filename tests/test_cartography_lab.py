"""
Unit tests for the Cartography Lab & Starmap Puzzle Matrix in Xylarium.
Covers chart fragment collection, interactive cartographic decryption,
secret ghost sector unlocks, pathfinding traversal, persistence, and ASCII UI rendering.
"""

import os
import re
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, SecurityLevel, Captain, AIPersonality, PortClass
from xylarium.kernel.cartography import FRAGMENT_TEMPLATES
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer


class TestCartographyFragments(unittest.TestCase):
    """Test fragment collection via broker chits, deep-space salvage, and pirate combat."""

    def setUp(self):
        self.kernel = GameKernel(seed=101)
        self.player = self.kernel.register_player("tester", "Test Captain")

    def test_buy_broker_chit_success(self):
        """Captains can buy encrypted starmap chits from shady brokers in ports."""
        self.player.credits = 5000
        initial_frags = len(self.player.cartography_fragments)

        res = self.kernel.dispatch(self.player.id, ActionType.CARTOGRAPHY_BUY_CHIT)
        self.assertTrue(res.success)
        self.assertEqual(len(self.player.cartography_fragments), initial_frags + 1)
        self.assertEqual(self.player.credits, 3000)  # 2000 Cr chit price
        self.assertIn("fragment", res.data)

    def test_buy_broker_chit_insufficient_credits(self):
        """Broker refuses to sell chits if captain has insufficient credits."""
        self.player.credits = 500
        res = self.kernel.dispatch(self.player.id, ActionType.CARTOGRAPHY_BUY_CHIT)
        self.assertFalse(res.success)
        self.assertIn("Insufficient credits", res.message)

    def test_salvage_deep_space_anarchy_success(self):
        """Captains can salvage abandoned drifting hulks in lawless Anarchy sectors."""
        # Find or place captain in Anarchy sector (61-100)
        anarchy_sec = next(s for s in self.kernel.sectors.values() if s.security == SecurityLevel.ANARCHY)
        self.player.sector_id = anarchy_sec.id
        self.player.turns_left = 5
        init_turns = self.player.turns_left

        res = self.kernel.dispatch(self.player.id, ActionType.CARTOGRAPHY_SALVAGE)
        self.assertTrue(res.success)
        self.assertEqual(self.player.turns_left, init_turns - 1)
        self.assertGreater(self.player.credits, 0)

    def test_salvage_rejected_in_safe_sectors(self):
        """Salvage search fails in Federation Core and Borderland sectors."""
        fed_sec = next(s for s in self.kernel.sectors.values() if s.security == SecurityLevel.FEDERATION)
        self.player.sector_id = fed_sec.id
        res = self.kernel.dispatch(self.player.id, ActionType.CARTOGRAPHY_SALVAGE)
        self.assertFalse(res.success)
        self.assertIn("lawless Anarchy sectors", res.message)

    def test_pirate_combat_fragment_drop(self):
        """Defeating a pirate ship awards a corrupted starmap fragment."""
        from xylarium.kernel.models import Ship, CargoHold
        pirate = Captain(
            id="pirate_corsair",
            name="Void Corsair",
            ship=Ship(
                ship_type="Corsair",
                cargo=CargoHold(capacity=30),
                shields=100,
                max_shields=100,
                fighters=15,
            ),
            credits=1500,
            turns_left=10,
            is_ai=True,
            personality=AIPersonality.PIRATE,
            sector_id=self.player.sector_id,
        )
        sector = self.kernel.sectors[self.player.sector_id]
        frag = self.kernel.cartography_manager.award_pirate_drop(self.player, pirate, sector, self.kernel)
        self.assertIsNotNone(frag)
        self.assertIn(frag, self.player.cartography_fragments)


class TestCartographyMatrixOperations(unittest.TestCase):
    """Test interactive cartographic matrix operations: scan, rotate, bridge, energy."""

    def setUp(self):
        self.kernel = GameKernel(seed=101)
        self.player = self.kernel.register_player("tester", "Test Captain")
        self.puzzle = self.kernel.cartography_manager.puzzles["PUZZLE-NEXUS"]

    def test_scan_fragment_decodes_node(self):
        """Scanning a fragment reveals an unrevealed node and updates progress."""
        # Give player a matching fragment
        frag = dict(FRAGMENT_TEMPLATES[0])
        self.player.cartography_fragments.append(frag)

        unrevealed_before = sum(1 for row in self.puzzle.grid_nodes for n in row if not n["is_revealed"])
        init_applied = self.puzzle.fragments_applied

        res = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_SCAN,
            fragment_id=frag["id"],
            puzzle_id="PUZZLE-NEXUS"
        )
        self.assertTrue(res.success)
        self.assertEqual(self.puzzle.fragments_applied, init_applied + 1)
        unrevealed_after = sum(1 for row in self.puzzle.grid_nodes for n in row if not n["is_revealed"])
        self.assertEqual(unrevealed_after, unrevealed_before - 1)
        self.assertNotIn(frag, self.player.cartography_fragments)

    def test_rotate_node(self):
        """Rotating a node turns its signal vector by 90 degrees and consumes energy."""
        node = self.puzzle.grid_nodes[0][1]
        initial_angle = node["vector_angle"]
        initial_energy = self.puzzle.energy_left

        res = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_ROTATE,
            row=0,
            col=1,
            puzzle_id="PUZZLE-NEXUS"
        )
        self.assertTrue(res.success)
        self.assertEqual(node["vector_angle"], (initial_angle + 90) % 360)
        self.assertEqual(self.puzzle.energy_left, initial_energy - 1)

    def test_bridge_vector(self):
        """Bridging two adjacent nodes establishes an active vector conduit."""
        # PUZZLE-VAULT has a broken bridge at 0,1-0,2
        vault_puzzle = self.kernel.cartography_manager.puzzles["PUZZLE-VAULT"]
        self.assertFalse(vault_puzzle.grid_bridges["0,1-0,2"])

        res = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_BRIDGE,
            r1=0,
            c1=1,
            r2=0,
            c2=2,
            puzzle_id="PUZZLE-VAULT"
        )
        self.assertTrue(res.success)
        self.assertTrue(vault_puzzle.grid_bridges["0,1-0,2"])

    def test_energy_depletion_and_turn_recharge(self):
        """Energy depletion consumes captain turns or blocks actions, and recharges on maintenance."""
        self.puzzle.energy_left = 1
        self.player.turns_left = 2

        # Rotate consumes last energy unit
        res1 = self.kernel.dispatch(self.player.id, ActionType.CARTOGRAPHY_ROTATE, row=0, col=1)
        self.assertTrue(res1.success)
        self.assertEqual(self.puzzle.energy_left, 0)

        # Next rotate consumes 1 captain turn to recharge
        res2 = self.kernel.dispatch(self.player.id, ActionType.CARTOGRAPHY_ROTATE, row=0, col=1)
        self.assertTrue(res2.success)
        self.assertEqual(self.player.turns_left, 1)

        # Maintenance recharges all puzzle energy
        self.puzzle.energy_left = 0
        self.kernel.process_turn_maintenance()
        self.assertEqual(self.puzzle.energy_left, self.puzzle.energy_max)

    def test_select_puzzle_matrix(self):
        """Captains can switch active cartography decryption targets."""
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_SELECT,
            puzzle_id="PUZZLE-VAULT"
        )
        self.assertTrue(res.success)
        self.assertEqual(self.player.active_cartography_puzzle, "PUZZLE-VAULT")
        self.assertEqual(self.kernel.cartography_manager.active_puzzle_id, "PUZZLE-VAULT")


class TestSecretSectorUnlocks(unittest.TestCase):
    """Test permanent unlocking of Ghost Sectors and Smuggler Shortcuts upon matrix solution."""

    def setUp(self):
        self.kernel = GameKernel(seed=101)
        self.player = self.kernel.register_player("tester", "Test Captain")

    def test_solve_nexus_unlocks_ghost_sector_105(self):
        """Solving PUZZLE-NEXUS unlocks Ghost Sector 105 (Black-Market Nexus / The Shadow Exchange)."""
        res = self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-NEXUS", self.kernel)
        self.assertTrue(res.success)
        self.assertIn("GHOST_NEXUS", self.player.unlocked_secrets)

        # Verify Ghost Sector 105
        self.assertIn(105, self.kernel.sectors)
        sec_105 = self.kernel.sectors[105]
        self.assertTrue(sec_105.is_secret)
        self.assertIn(78, sec_105.warps)
        self.assertIn(65, sec_105.warps)

        # Verify bidirectional links from 78 and 65 to 105
        self.assertIn(105, self.kernel.sectors[78].warps)
        self.assertIn(105, self.kernel.sectors[65].warps)

        # Verify port with 300% trade premium
        self.assertIsNotNone(sec_105.port)
        self.assertEqual(sec_105.port.name, "The Shadow Exchange")
        self.assertEqual(sec_105.port.port_class, PortClass.CLASS_8_BBB)

    def test_solve_vault_unlocks_ghost_sector_106(self):
        """Solving PUZZLE-VAULT unlocks Ghost Sector 106 (Aethelgard Prime Precursor Vault)."""
        res = self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-VAULT", self.kernel)
        self.assertTrue(res.success)
        self.assertIn("PRECURSOR_VAULT", self.player.unlocked_secrets)

        # Verify Ghost Sector 106
        self.assertIn(106, self.kernel.sectors)
        sec_106 = self.kernel.sectors[106]
        self.assertTrue(sec_106.is_secret)
        self.assertIn(88, sec_106.warps)
        self.assertIn(92, sec_106.warps)

        # Verify planetary body with Citadel Tier 4, 25k vault credits, 5000 Adamant Lode
        self.assertEqual(len(sec_106.planets), 1)
        planet = sec_106.planets[0]
        self.assertEqual(planet.name, "Aethelgard Prime")
        self.assertEqual(planet.citadel_level, 4)
        self.assertEqual(planet.treasury, 25000)
        self.assertEqual(planet.element_deposits.get("adamant_lode", 0), 5000)

    def test_solve_shortcut_links_sectors_10_and_70(self):
        """Solving PUZZLE-SHORTCUT opens permanent bidirectional wormhole between 010 and 070."""
        # Verify 10 and 70 are initially NOT connected
        self.assertNotIn(70, self.kernel.sectors[10].warps)
        self.assertNotIn(10, self.kernel.sectors[70].warps)

        res = self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-SHORTCUT", self.kernel)
        self.assertTrue(res.success)
        self.assertIn("SMUGGLER_SHORTCUT", self.player.unlocked_secrets)

        # Verify direct link established
        self.assertIn(70, self.kernel.sectors[10].warps)
        self.assertIn(10, self.kernel.sectors[70].warps)

    def test_pathfinding_uses_unlocked_shortcut(self):
        """BFS shortest path finding immediately utilizes newly unlocked wormhole shortcut."""
        path_before = self.kernel.find_path(10, 70)
        self.assertGreater(len(path_before), 2)

        # Unlock shortcut
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-SHORTCUT", self.kernel)

        path_after = self.kernel.find_path(10, 70)
        self.assertEqual(path_after, [10, 70])


class TestCartographyPersistence(unittest.TestCase):
    """Test full save and load serialization of CartographyManager state."""

    def setUp(self):
        self.kernel = GameKernel(seed=101)
        self.player = self.kernel.register_player("tester", "Test Captain")

    def test_cartography_save_and_load(self):
        """Verify cartography manager, puzzles, fragments, and secrets persist across save/load."""
        # Unlock one secret and add fragments
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-NEXUS", self.kernel)
        frag = dict(FRAGMENT_TEMPLATES[1])
        self.player.cartography_fragments.append(frag)
        self.player.active_cartography_puzzle = "PUZZLE-VAULT"

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            filepath = tf.name

        try:
            saved = StatePersistence.save_to_file(self.kernel, filepath)
            self.assertTrue(saved)

            loaded_kernel = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(loaded_kernel)
            self.assertTrue(hasattr(loaded_kernel, "cartography_manager"))

            # Verify unlocked secrets
            loaded_player = loaded_kernel.get_player(self.player.id)
            self.assertIn("GHOST_NEXUS", loaded_player.unlocked_secrets)
            self.assertEqual(loaded_player.active_cartography_puzzle, "PUZZLE-VAULT")
            self.assertEqual(len(loaded_player.cartography_fragments), 1)
            self.assertEqual(loaded_player.cartography_fragments[0]["id"], frag["id"])

            # Verify sector 105 exists in loaded universe
            self.assertIn(105, loaded_kernel.sectors)
            self.assertEqual(loaded_kernel.sectors[105].name, "The Black-Market Nexus")
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


class TestCartographyTerminalRenderer(unittest.TestCase):
    """Test terminal ANSI/ASCII rendering of Cartography screens and 80-column compliance."""

    def setUp(self):
        self.kernel = GameKernel(seed=101)
        self.player = self.kernel.register_player("tester", "Test Captain")

    def test_render_cartography_screen_unsolved(self):
        """Renders unsolved cartography matrix cleanly without exceptions."""
        view = self.kernel.get_player_view(self.player.id)
        rendered = TerminalRenderer.render_cartography_screen(view)
        self.assertIn("CARTOGRAPHIC DECRYPTION MATRIX", rendered)
        self.assertIn("Sector Vectors & Decryption Telemetry", rendered)
        self.assertIn("Commands:", rendered)

    def test_render_cartography_screen_decrypted(self):
        """Renders decrypted cartography matrix with unlocked secrets."""
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-NEXUS", self.kernel)
        view = self.kernel.get_player_view(self.player.id)
        rendered = TerminalRenderer.render_cartography_screen(view)
        self.assertIn("Black-Market Nexus", rendered)
        self.assertIn("Sector 105", rendered)

    def test_renderer_column_width_compliance(self):
        """Verify all lines in rendered output strictly comply with <= 80 character width."""
        view = self.kernel.get_player_view(self.player.id)
        rendered = TerminalRenderer.render_cartography_screen(view)
        ansi_regex = re.compile(r"\x1b\[[0-9;]*m")

        for line_num, raw_line in enumerate(rendered.split("\n"), 1):
            clean_line = ansi_regex.sub("", raw_line)
            self.assertLessEqual(
                len(clean_line),
                80,
                f"Line {line_num} exceeds 80 characters (Length: {len(clean_line)}): '{clean_line}'"
            )


if __name__ == "__main__":
    unittest.main()
