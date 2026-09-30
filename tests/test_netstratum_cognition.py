"""
Comprehensive Test Suite for the Netstratum Dual-Seat Cognition Engine (iae::think).
Validates Seat 1 (SURVIVE), Seat 2 (ARC), Cognitive Metabolism, RCF Invariant Hashes,
O(1) Grown-Basis Recall, Colony Divergence Vectors, and Strict 80-Column Terminal Rendering.
"""

import unittest
import tempfile
import os
import re

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import (
    Captain,
    Planet,
    Sector,
    SecurityLevel,
    ActionType,
    ActionResult,
    Port,
    PortClass,
    Ship,
    CargoHold,
)
from xylarium.kernel.cognition import (
    rcf_hash,
    LedgerEntry,
    LedgerBook,
    DivergenceVector,
    CognitiveDeed,
    SeatSurvive,
    SeatArc,
    CognitiveOrgan,
)
from xylarium.kernel.civilization import Civilization
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer


class TestSeatSurvive(unittest.TestCase):
    """Test Suite 1: Seat 1 - SURVIVE (Material Cochains & Empire Equilibrium)."""

    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.captain = self.kernel.register_player("survive_tester", "Captain Cochain")

    def test_five_canonical_ledger_books_peeling(self):
        """Validates that Seat SURVIVE accurately peels the five canonical ledger books."""
        self.captain.ship.cargo.organics = 0   # an empty pantry: the ration book must show a deficit
        books = SeatSurvive.peel_books(self.captain, self.kernel)
        self.assertIn("RATION", books)
        self.assertIn("THERMAL", books)
        self.assertIn("SECURITY", books)
        self.assertIn("MATTER", books)
        self.assertIn("LEISURE", books)

        ration = books["RATION"]
        self.assertFalse(ration.is_closed)
        self.assertEqual(ration.name, "RATION")
        self.assertGreater(ration.total_deficit, 0)

    def test_species_metabolic_demands(self):
        """Different biological and mineral lineages have distinct metabolic ration requirements."""
        # Biotic human
        self.captain.metabolism = "biotic"
        b_books = SeatSurvive.peel_books(self.captain, self.kernel)
        self.assertIn("ORGANICS", b_books["RATION"].entries)
        self.assertIn("H2O", b_books["RATION"].entries)

        # Mineral / Lithophage
        self.captain.metabolism = "mineral"
        m_books = SeatSurvive.peel_books(self.captain, self.kernel)
        self.assertIn("ORE", m_books["RATION"].entries)
        self.assertIn("SI", m_books["RATION"].entries)

        # Plasmic
        self.captain.metabolism = "plasmic"
        p_books = SeatSurvive.peel_books(self.captain, self.kernel)
        self.assertIn("H", p_books["RATION"].entries)
        self.assertIn("HE-3", p_books["RATION"].entries)

    def test_divergence_vector_tensor(self):
        """Verifies exact cochain divergence tensor computation: div(Delta)_i = Have_i - Owe_i."""
        self.captain.metabolism = "biotic"
        self.captain.ship.cargo.organics = 2
        self.captain.ship.cargo.elements["H2O"] = 1
        self.captain.ship.cargo.elements["SpR"] = 5

        div = SeatSurvive.compute_divergence_vector(self.captain, self.kernel)
        self.assertIsInstance(div, DivergenceVector)
        self.assertFalse(div.is_balanced)

        # Deficits on Organics and H2O
        self.assertGreater(div.deficit("ORGANICS"), 0)
        self.assertGreater(div.deficit("H2O"), 0)

        # Surplus on SpR
        self.assertGreater(div.surplus("SpR"), 0)

        acute_k, acute_v = div.acute_deficit()
        self.assertIn(acute_k, ["ORGANICS", "H2O", "CREDITS"])

    def test_ration_deficit_dictates_purchase_or_forage(self):
        """The Residual Names the Deed: unclosed ration deficits command food purchase or foraging."""
        # In port with organics: purchase
        self.captain.ship.cargo.organics = 0
        self.captain.sector_id = 1
        self.captain.credits = 500
        books = SeatSurvive.peel_books(self.captain, self.kernel)
        deed = SeatSurvive.reduce_survival(self.captain, books, self.kernel)
        self.assertIsNotNone(deed)
        self.assertEqual(deed.seat, "SURVIVE")
        self.assertEqual(deed.deed_name, "PURCHASE_RATIONS")
        self.assertEqual(deed.action_type, ActionType.TRADE)

        # In anarchy without a port and with money: fly to a port that sells rations
        sec_anarchy = next(s for s in self.kernel.sectors.values() if s.security == SecurityLevel.ANARCHY and not s.port)
        self.captain.sector_id = sec_anarchy.id
        books_anarchy = SeatSurvive.peel_books(self.captain, self.kernel)
        deed_anarchy = SeatSurvive.reduce_survival(self.captain, books_anarchy, self.kernel)
        self.assertIsNotNone(deed_anarchy)
        self.assertEqual(deed_anarchy.deed_name, "SEEK_RATION_PORT")

        # ...and only a truly broke captain forages the Deep Void for salvage
        self.captain.credits = 20
        self.captain.fx_wallet = {}
        self.captain.portfolio = {}
        books_broke = SeatSurvive.peel_books(self.captain, self.kernel)
        deed_broke = SeatSurvive.reduce_survival(self.captain, books_broke, self.kernel)
        self.assertEqual(deed_broke.deed_name, "FORAGE_DEEP_VOID")
        self.assertEqual(deed_broke.action_type, ActionType.CARTOGRAPHY_SALVAGE)

    def test_tax_harvesting_as_matter_reduction(self):
        """When liquid credits are deficient, Matter Book commands tax harvesting from owned colonies."""
        # Satisfy rations so Matter reduction takes priority
        self.captain.ship.cargo.organics = 20
        self.captain.ship.cargo.elements["H2O"] = 20
        self.captain.credits = 200  # acute credit deficit

        # Create owned colony in current sector with treasury
        sec = self.kernel.sectors[self.captain.sector_id]
        planet = Planet(id="TEST-COLONY", name="Aegis IV", sector_id=sec.id, owner_id=self.captain.id, treasury=12000)
        sec.planets.append(planet)

        books = SeatSurvive.peel_books(self.captain, self.kernel)
        deed = SeatSurvive.reduce_survival(self.captain, books, self.kernel)
        self.assertIsNotNone(deed)
        self.assertEqual(deed.action_type, ActionType.PLANET_TAX)
        self.assertEqual(deed.deed_name, "COLLECT_COLONIAL_TAXES")
        self.assertEqual(deed.parameters["planet_id"], "TEST-COLONY")


class TestSeatArc(unittest.TestCase):
    """Test Suite 2: Seat 2 - ARC (Spatial Navigation & Cartographic Decryption)."""

    def setUp(self):
        self.kernel = GameKernel(seed=84)
        self.captain = self.kernel.register_player("arc_tester", "Navigator Gauss")

    def test_rcf_hash_conjugacy_invariance(self):
        """Netstratum Core Law: isomorphic coordinate matrices yield identical RCF hashes under cyclic permutation."""
        # 3x3 matrix representing star vector angles
        matrix_a = [
            [{"is_revealed": True, "vector_angle": 0, "sector_val": 10}, {"is_revealed": True, "vector_angle": 90, "sector_val": 20}],
            [{"is_revealed": True, "vector_angle": 180, "sector_val": 30}, {"is_revealed": True, "vector_angle": 270, "sector_val": 40}],
        ]
        # Rotated 90 degrees (cyclic shift)
        matrix_b = [
            [{"is_revealed": True, "vector_angle": 90, "sector_val": 20}, {"is_revealed": True, "vector_angle": 180, "sector_val": 30}],
            [{"is_revealed": True, "vector_angle": 270, "sector_val": 40}, {"is_revealed": True, "vector_angle": 0, "sector_val": 10}],
        ]

        hash_a = rcf_hash(matrix_a)
        hash_b = rcf_hash(matrix_b)
        self.assertEqual(hash_a, hash_b, "Cyclic permutation of vector nodes must preserve RCF conjugacy hash.")

    def test_grid_pair_peeling_and_breakthrough_synthesis(self):
        """ARC peels alignment and bridge residuals until complete, generating CERT-ARC-."""
        puzzle = self.kernel.cartography_manager.puzzles.get("PUZZLE-NEXUS")
        self.assertIsNotNone(puzzle)

        # Unaligned node triggers vector rotation
        puzzle.grid_nodes[0][0]["is_revealed"] = True
        puzzle.grid_nodes[0][0]["vector_angle"] = 0
        puzzle.grid_nodes[0][0]["target_angle"] = 90

        deed = SeatArc.peel_puzzle(self.captain, "PUZZLE-NEXUS", self.kernel)
        self.assertIsNotNone(deed)
        self.assertEqual(deed.seat, "ARC")
        self.assertEqual(deed.action_type, ActionType.CARTOGRAPHY_ROTATE)

        # Fully align all nodes and link all bridges
        for row in puzzle.grid_nodes:
            for n in row:
                n["is_revealed"] = True
                n["vector_angle"] = n["target_angle"]
        for k in puzzle.grid_bridges:
            puzzle.grid_bridges[k] = True

        solve_deed = SeatArc.peel_puzzle(self.captain, "PUZZLE-NEXUS", self.kernel)
        self.assertIsNotNone(solve_deed)
        self.assertEqual(solve_deed.action_type, ActionType.CARTOGRAPHY_SOLVE)
        self.assertTrue(solve_deed.certificate.startswith("CERT-ARC-"))

    def test_ghost_sector_permanent_unlock(self):
        """Solving an anomaly writes the certificate and permanently unlocks Ghost Sector 105 in universe graph."""
        puzzle = self.kernel.cartography_manager.puzzles.get("PUZZLE-NEXUS")
        for row in puzzle.grid_nodes:
            for n in row:
                n["is_revealed"] = True
                n["vector_angle"] = n["target_angle"]
        for k in puzzle.grid_bridges:
            puzzle.grid_bridges[k] = True

        solve_deed = SeatArc.peel_puzzle(self.captain, "PUZZLE-NEXUS", self.kernel)
        res = CognitiveOrgan._execute_deed(solve_deed, self.captain, self.kernel)
        self.assertTrue(res.success)
        self.assertIn("GHOST_NEXUS", self.captain.unlocked_secrets)
        self.assertIn(105, self.kernel.sectors)
        self.assertIn(105, self.kernel.sectors[78].warps)


class TestCognitiveMetabolismAndGrownBasis(unittest.TestCase):
    """Test Suite 3: Cognitive Metabolism Gating & O(1) Grown-Basis Recall."""

    def setUp(self):
        self.kernel = GameKernel(seed=126)
        self.captain = self.kernel.register_player("meta_tester", "Captain Turing")

    def test_starvation_restricts_bandwidth_to_survival(self):
        """Starving entities cannot allocate cognitive energy to Seat ARC decryption."""
        # Empty cargo hold and low credits -> starvation
        self.captain.ship.cargo.organics = 0
        self.captain.ship.cargo.elements["H2O"] = 0
        self.captain.credits = 50

        # Run cognitive organ
        res = CognitiveOrgan.think(self.captain, self.kernel)
        # Should NOT execute ARC actions
        self.assertNotEqual(res.action, ActionType.CARTOGRAPHY_SOLVE)
        self.assertNotEqual(res.action, ActionType.CARTOGRAPHY_ROTATE)
        self.assertNotEqual(res.action, ActionType.CARTOGRAPHY_SCAN)

    def test_metabolic_surplus_spills_over_to_arc(self):
        """When survival books are closed and capital is abundant, thought spills over to Seat ARC."""
        self.captain.ship.cargo.organics = 50
        self.captain.ship.cargo.elements["H2O"] = 50
        self.captain.credits = 10000

        puzzle = self.kernel.cartography_manager.puzzles.get("PUZZLE-NEXUS")
        puzzle.grid_nodes[0][0]["is_revealed"] = True
        puzzle.grid_nodes[0][0]["vector_angle"] = 0
        puzzle.grid_nodes[0][0]["target_angle"] = 90

        # Execute think cycle
        res = CognitiveOrgan.think(self.captain, self.kernel)
        self.assertTrue(res.success)
        # Spilled over into cartography or high-capital expansion
        self.assertIn(res.action, [
            ActionType.CARTOGRAPHY_ROTATE,
            ActionType.CARTOGRAPHY_SCAN,
            ActionType.CARTOGRAPHY_BRIDGE,
            ActionType.CARTOGRAPHY_SOLVE,
            ActionType.PLANET_CLAIM,
            ActionType.STOCK_BUY,
            ActionType.SHIPYARD_PURCHASE,   # commissioning a larger hull is high-capital expansion too
            ActionType.MOVE,
        ])

    def test_o1_grown_basis_recall(self):
        """Thinking Changes the Thinker: previously crystallized invariants are recalled in O(1) time."""
        puzzle = self.kernel.cartography_manager.puzzles.get("PUZZLE-NEXUS")
        sig = rcf_hash(puzzle.grid_nodes)
        cert = f"CERT-ARC-{sig[:12].upper()}"

        # Inject solved crystal into captain's grown_basis
        self.captain.grown_basis.append({
            "seat": "ARC",
            "deed": "SYNTHESIZE_CARTOGRAPHIC_BREAKTHROUGH",
            "coordinate": "PUZZLE-NEXUS",
            "rcf_sig": sig,
            "certificate": cert,
        })

        deed = SeatArc.peel_puzzle(self.captain, "PUZZLE-NEXUS", self.kernel)
        self.assertIsNotNone(deed)
        self.assertEqual(deed.deed_name, "RECALL_SOLVED_CARTOGRAPHY_INVARIANT")
        self.assertEqual(deed.action_type, ActionType.CARTOGRAPHY_SOLVE)
        self.assertEqual(deed.residual_magnitude, 0.0)


class TestColonyDivergenceAndRelief(unittest.TestCase):
    """Test Suite 4: Planetary Colony Cochains & Relief Logistics."""

    def setUp(self):
        self.kernel = GameKernel(seed=168)
        self.captain = self.kernel.register_player("colony_tester", "Governor Keynes")
        self.planet = self.kernel.sectors[1].planets[0] if self.kernel.sectors[1].planets else Planet(
            id="COL-01", name="New Terra", sector_id=1, owner_id=self.captain.id, population=5000
        )
        self.planet.owner_id = self.captain.id
        if self.planet not in self.kernel.sectors[1].planets:
            self.kernel.sectors[1].planets.append(self.planet)

    def test_planet_divergence_vector_identifies_water_deficit(self):
        """Planetary divergence cochains detect acute biological and hydration deficits."""
        self.planet.population = 8000
        self.planet.organics_silo = 5
        self.planet.element_reserves["H2O"] = 2

        div = SeatSurvive.compute_divergence_vector(self.planet, self.kernel)
        self.assertGreater(div.deficit("H2O"), 0)
        self.assertGreater(div.deficit("ORGANICS"), 0)

    def test_captain_relieves_colony_deficit_from_cargo(self):
        """When an owned colony is deficient and captain carries cargo, SURVIVE transfers supplies."""
        self.captain.sector_id = self.planet.sector_id
        # Feed captain so captain is stable and close credit deficit
        self.captain.ship.cargo.organics = 40
        self.captain.ship.cargo.elements["H2O"] = 20
        self.captain.credits = 3000

        # Starve colony, empty treasury so tax harvesting is not commanded
        self.planet.treasury = 0
        self.planet.organics_silo = 0
        self.planet.element_reserves["H2O"] = 0

        books = SeatSurvive.peel_books(self.captain, self.kernel)
        deed = SeatSurvive.reduce_survival(self.captain, books, self.kernel)
        self.assertIsNotNone(deed)
        self.assertEqual(deed.deed_name, "RELIEVE_COLONY_DEFICIT")
        self.assertIn(deed.action_type, [ActionType.PLANET_CARGO_TRANSFER, ActionType.PLANET_ELEMENT_TRANSFER])

    def test_planetary_cognitive_organ_think(self):
        """Colonies run iae::think directly to reinforce shields, recruit garrisons, or extract reserves."""
        # Unreinforced shields
        self.planet.shields = 0
        self.planet.max_shields = 100
        self.planet.treasury = 5000
        self.planet.organics_silo = 500
        self.planet.element_reserves["H2O"] = 200

        res = CognitiveOrgan.think(self.planet, self.kernel)
        self.assertTrue(res.success)
        self.assertIn(res.action, [
            ActionType.PLANET_BUILD_SHIELD,
            ActionType.PLANET_RECRUIT_FIGHTERS,
            ActionType.PLANET_INVEST,
            ActionType.PLANET_UPGRADE_CITADEL,
            ActionType.PLANET_ELEMENT_TRANSFER,
        ])
        self.assertGreater(len(self.planet.grown_basis), 0)


class TestEmergentEmpires(unittest.TestCase):
    """Test Suite 5: Emergent AI Personalities & Species Taxonomy."""

    def setUp(self):
        self.kernel = GameKernel(seed=210)

    def test_ai_captains_species_and_metabolism_initialization(self):
        """AI captains emerge with diverse biological/mineral species and metabolic regimes."""
        captains = self.kernel.captains
        malakor = next((c for c in captains.values() if "Malakor" in c.name), None)
        voss = next((c for c in captains.values() if "Voss" in c.name), None)
        vane = next((c for c in captains.values() if "Vane" in c.name), None)
        ironclaw = next((c for c in captains.values() if "Ironclaw" in c.name), None)

        self.assertIsNotNone(malakor)
        self.assertEqual(malakor.species, "hypobiotid-voidsleeper")
        self.assertEqual(malakor.metabolism, "mineral")

        self.assertIsNotNone(voss)
        self.assertEqual(voss.species, "bimaniform-flatlander")
        self.assertEqual(voss.metabolism, "mineral")

        self.assertIsNotNone(vane)
        self.assertEqual(vane.species, "ailuroform-primus")
        self.assertEqual(vane.metabolism, "biotic")

        self.assertIsNotNone(ironclaw)
        self.assertEqual(ironclaw.species, "actinoform-vanguard")
        self.assertEqual(ironclaw.metabolism, "plasmic")

    def test_ai_think_loop_runs_emergent_turns(self):
        """All autonomous AI captains execute iae::think turns cleanly across multiple cycles."""
        for c in self.kernel.captains.values():
            if c.is_ai:
                res = CognitiveOrgan.think(c, self.kernel)
                self.assertIsInstance(res, ActionResult)


class TestCognitiveConsoleAndRenderer(unittest.TestCase):
    """Test Suite 6: Cognitive Console & Strict 80-Column Terminal Compliance."""

    def setUp(self):
        self.kernel = GameKernel(seed=252)
        self.captain = self.kernel.register_player("render_tester", "Captain Terminal")

    def test_render_cognitive_console_column_width(self):
        """Strict ANSI/ASCII compliance: every line in render_cognitive_console must be <= 80 columns."""
        view = self.kernel.get_player_view(self.captain.id)
        rendered = TerminalRenderer.render_cognitive_console(view)
        self.assertTrue(len(rendered) > 0)

        lines = rendered.split("\n")
        ansi_regex = re.compile(r'\x1b\[[0-9;]*m')
        for idx, line in enumerate(lines):
            raw = ansi_regex.sub('', line)
            self.assertLessEqual(
                len(raw),
                80,
                f"Line {idx+1} exceeded 80 characters ({len(raw)} chars): '{raw}'"
            )

    def test_console_contains_five_ledger_books_and_divergence(self):
        """Rendered console contains all 5 canonical ledger books and divergence tensor."""
        view = self.kernel.get_player_view(self.captain.id)
        rendered = TerminalRenderer.render_cognitive_console(view)
        self.assertIn("RATION", rendered)
        self.assertIn("THERMAL", rendered)
        self.assertIn("SECURITY", rendered)
        self.assertIn("MATTER", rendered)
        self.assertIn("LEISURE", rendered)
        self.assertIn("COCHAIN DIVERGENCE TENSOR", rendered)
        self.assertIn("GROWN_BASIS", rendered)


class TestCognitivePersistence(unittest.TestCase):
    """Test Suite 7: Full Serialization & Persistence Across Game Saves."""

    def test_captain_and_planet_grown_basis_serialization(self):
        """Verify grown_basis and species attributes round-trip through to_dict and from_dict."""
        ship = Ship(ship_type="Merchant Cruiser", cargo=CargoHold(capacity=50), shields=100, max_shields=100, fighters=10)
        captain = Captain(
            id="cap_007",
            name="Agent 007",
            is_ai=False,
            personality=None,
            ship=ship,
            credits=5000,
            sector_id=1,
            turns_left=100,
            species="chitinous-swarm",
            metabolism="biotic",
            grown_basis=[{
                "seat": "ARC",
                "deed": "SYNTHESIZE_CARTOGRAPHIC_BREAKTHROUGH",
                "coordinate": "PUZZLE-VAULT",
                "certificate": "CERT-ARC-TEST999",
            }]
        )
        c_dict = captain.to_dict()
        self.assertEqual(c_dict["species"], "chitinous-swarm")
        self.assertEqual(c_dict["metabolism"], "biotic")
        self.assertEqual(len(c_dict["grown_basis"]), 1)

        restored_c = Captain.from_dict(c_dict)
        self.assertEqual(restored_c.species, "chitinous-swarm")
        self.assertEqual(restored_c.metabolism, "biotic")
        self.assertEqual(len(restored_c.grown_basis), 1)
        self.assertEqual(restored_c.grown_basis[0]["certificate"], "CERT-ARC-TEST999")

        # Planet
        planet = Planet(
            id="P-PERSIST",
            name="Persist Prime",
            sector_id=1,
            grown_basis=[{"seat": "SURVIVE", "deed": "REINFORCE_PLANETARY_SHIELDS"}]
        )
        p_dict = planet.to_dict()
        restored_p = Planet.from_dict(p_dict)
        self.assertEqual(len(restored_p.grown_basis), 1)

        # Civilization
        civ = Civilization(
            name="Emergent Union",
            species_name="Chitinous Swarm",
            class_code=1,
            sigil="※",
            clade="hypobiotid",
            metabolism="biotic",
            disposition="expansionist",
            motto="Synthesize or Perish",
            grown_basis=[{"seat": "SURVIVE", "deed": "DEEP_SYNTHESIS"}]
        )
        civ_dict = civ.to_dict()
        restored_civ = Civilization.from_dict(civ_dict)
        self.assertEqual(len(restored_civ.grown_basis), 1)

    def test_state_persistence_save_load(self):
        """StatePersistence preserves all cognitive attributes and grown_basis on disk."""
        kernel = GameKernel(seed=333)
        player = kernel.register_player("persist_cap", "Captain Stored")
        player.species = "actinoform-vanguard"
        player.metabolism = "plasmic"
        player.grown_basis.append({
            "seat": "ARC",
            "deed": "RECALL_SOLVED_CARTOGRAPHY_INVARIANT",
            "certificate": "CERT-ARC-PERSIST123"
        })

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            save_path = f.name

        try:
            ok = StatePersistence.save_to_file(kernel, save_path)
            self.assertTrue(ok)
            loaded_kernel = StatePersistence.load_from_file(save_path)
            self.assertIsNotNone(loaded_kernel)
            loaded_player = loaded_kernel.captains.get(player.id)
            self.assertIsNotNone(loaded_player)
            self.assertEqual(loaded_player.species, "actinoform-vanguard")
            self.assertEqual(loaded_player.metabolism, "plasmic")
            self.assertEqual(len(loaded_player.grown_basis), 1)
            self.assertEqual(loaded_player.grown_basis[0]["certificate"], "CERT-ARC-PERSIST123")
        finally:
            if os.path.exists(save_path):
                os.remove(save_path)


class TestPlayerAutomation(unittest.TestCase):
    """Test Suite 8: Player Automation via ActionType.COGNITIVE_AUTOMATE."""

    def setUp(self):
        self.kernel = GameKernel(seed=444)
        self.player = self.kernel.register_player("auto_player", "Captain Automation")

    def test_player_cognitive_automate_dispatch(self):
        """Player can dispatch ActionType.COGNITIVE_AUTOMATE through the kernel."""
        # Ensure player has turns and supplies
        self.player.turns_left = 10
        self.player.ship.cargo.organics = 20
        self.player.ship.cargo.elements["H2O"] = 20
        self.player.credits = 2500

        res = self.kernel.dispatch(self.player.id, ActionType.COGNITIVE_AUTOMATE)
        self.assertIsInstance(res, ActionResult)
        self.assertTrue(res.success)


if __name__ == "__main__":
    unittest.main()
