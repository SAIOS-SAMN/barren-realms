"""
Comprehensive unit tests for the Cartography Lab & Starmap Puzzle Matrix Expansions.
Covers:
1. Cartographic Monopolies & Smuggling Cartels:
   - Orbital toll gate deployment on unlocked shortcuts (Sector 10<->70, Ghost Sector 105, 106)
   - Autonomous fee collection from traversing rival captains & AI haulers
   - Picket drone defense firing on unauthorized or underfunded travelers (-35 shields)
   - Dynamic toll fee reconfiguration and ownership validation
   - Forged starmap chit synthesis: broker sale profit and rival vault baiting into pirate ambushes
2. Elemental Reagents & Artifact Catalysis (The Periodic Puzzle Layer):
   - Precursor Cipher Zeta-9 (PUZZLE-VAULT) catalytic requirements (Spiral Rime Crystals [SpR], Enriched Uranium [U])
   - Cargo hold reagent injection and tech equipment fallback
   - Cryocoherent Stillcold species cryogenic cooling bonus
   - Quantum lock dissolution and +20% decryption surge
3. Automated Survey Drones & Frontier Probe Fleets:
   - Commissioning Deep-Space Survey Probes at Stardock
   - Autonomous frontier space sweeping and navigation telemetry
   - Automated fragment harvesting beamed directly to owner
   - Micrometeorite hazard handling and LOST_SIGNAL states
4. Cartographic Espionage & Vault Heists:
   - Covert ops 'cartographic_heist' against rival captains and planetary vaults
   - Starmap fragment exfiltration and coordinate theft
   - Intel bounties and ISSE market volatility impacts
5. State Persistence & Full Roundtrip Serialization:
   - Toll gates, survey probes, and puzzle catalysis state serialization
6. Terminal Renderer Expansions & 80-Column Compliance.
"""

import os
import re
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import (
    ActionType,
    SecurityLevel,
    Captain,
    Ship,
    CargoHold,
    AIPersonality,
    TollGate,
    SurveyProbe,
    PortClass,
    Planet,
)
from xylarium.kernel.cartography import FRAGMENT_TEMPLATES
from xylarium.config import (
    TOLL_GATE_DEPLOY_COST_CREDITS,
    SURVEY_PROBE_COST_CREDITS,
    FORGED_CHIT_SYNTH_COST,
    FORGED_CHIT_BROKER_VALUE,
)
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer


class TestTollGatesAndMonopolies(unittest.TestCase):
    """Test orbital toll gate deployment, transit fee collection, drone defenses, and forged chits."""

    def setUp(self):
        self.kernel = GameKernel(seed=202)
        self.player = self.kernel.register_player("tycoon", "Baron Vane")
        self.player.credits = 50000

        # Create a rival captain
        self.rival = Captain(
            id="rival_trader",
            name="Capt. Malakor",
            is_ai=True,
            personality=AIPersonality.TRADER,
            ship=Ship(
                ship_type="Merchant Hauler",
                cargo=CargoHold(capacity=100),
                shields=100,
                max_shields=100,
                fighters=20,
            ),
            credits=10000,
            turns_left=20,
            sector_id=10,
        )
        self.kernel.captains[self.rival.id] = self.rival

    def test_deploy_toll_gate_requires_unlocked_shortcut(self):
        """Cannot deploy a toll satellite on a corridor the player has not unlocked."""
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_DEPLOY,
            shortcut_id="SMUGGLER_SHORTCUT",
            toll_fee=500,
        )
        self.assertFalse(res.success)
        self.assertIn("shortcuts or ghost sectors you have decrypted", res.message)

    def test_deploy_toll_gate_success(self):
        """Successfully deploys an orbital toll gate on an unlocked shortcut."""
        # Unlock shortcut first
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-SHORTCUT", self.kernel)
        self.assertIn("SMUGGLER_SHORTCUT", self.player.unlocked_secrets)

        init_credits = self.player.credits
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_DEPLOY,
            shortcut_id="SMUGGLER_SHORTCUT",
            toll_fee=600,
        )
        self.assertTrue(res.success)
        self.assertEqual(self.player.credits, init_credits - TOLL_GATE_DEPLOY_COST_CREDITS)
        self.assertEqual(len(self.player.toll_gates), 1)

        gate_id = self.player.toll_gates[0]
        gate = self.kernel.cartography_manager.toll_gates[gate_id]
        self.assertEqual(gate.owner_id, self.player.id)
        self.assertEqual(gate.sector_a, 10)
        self.assertEqual(gate.sector_b, 70)
        self.assertEqual(gate.toll_fee, 600)
        self.assertTrue(gate.active)

    def test_duplicate_toll_gate_rejected(self):
        """Cannot deploy a second toll satellite on the same shortcut corridor."""
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-SHORTCUT", self.kernel)
        self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_DEPLOY,
            shortcut_id="SMUGGLER_SHORTCUT",
            toll_fee=500,
        )
        # Attempt to deploy another gate on the same shortcut
        res2 = self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_DEPLOY,
            shortcut_id="SMUGGLER_SHORTCUT",
            toll_fee=750,
        )
        self.assertFalse(res2.success)
        self.assertIn("already operational", res2.message)

    def test_toll_transit_collection(self):
        """Rival captain traversing the toll corridor pays fee to gate owner."""
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-SHORTCUT", self.kernel)
        self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_DEPLOY,
            shortcut_id="SMUGGLER_SHORTCUT",
            toll_fee=500,
        )
        gate_id = self.player.toll_gates[0]
        gate = self.kernel.cartography_manager.toll_gates[gate_id]

        owner_credits_before = self.player.credits
        rival_credits_before = self.rival.credits

        # Move rival across 10 -> 70
        fee_paid = self.kernel.cartography_manager.check_toll_transit(
            self.rival, from_sec=10, to_sec=70, kernel=self.kernel
        )
        self.assertEqual(fee_paid, 500)
        self.assertEqual(self.rival.credits, rival_credits_before - 500)
        self.assertEqual(self.player.credits, owner_credits_before + 500)
        self.assertEqual(gate.total_revenue, 500)
        self.assertEqual(gate.total_transits, 1)

    def test_toll_transit_bidirectional(self):
        """Toll is collected traveling in either direction (70 -> 10 as well as 10 -> 70)."""
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-SHORTCUT", self.kernel)
        self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_DEPLOY,
            shortcut_id="SMUGGLER_SHORTCUT",
            toll_fee=400,
        )
        fee_paid = self.kernel.cartography_manager.check_toll_transit(
            self.rival, from_sec=70, to_sec=10, kernel=self.kernel
        )
        self.assertEqual(fee_paid, 400)

    def test_owner_travels_toll_free(self):
        """The gate owner traverses their own toll corridor free of charge."""
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-SHORTCUT", self.kernel)
        self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_DEPLOY,
            shortcut_id="SMUGGLER_SHORTCUT",
            toll_fee=500,
        )
        owner_credits = self.player.credits
        fee_paid = self.kernel.cartography_manager.check_toll_transit(
            self.player, from_sec=10, to_sec=70, kernel=self.kernel
        )
        self.assertEqual(fee_paid, 0)
        self.assertEqual(self.player.credits, owner_credits)

    def test_insufficient_credits_intercepted_by_picket_drones(self):
        """Traveler without sufficient credits is attacked by picket defense drones (-35 shields)."""
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-SHORTCUT", self.kernel)
        self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_DEPLOY,
            shortcut_id="SMUGGLER_SHORTCUT",
            toll_fee=1000,
        )
        self.rival.credits = 200  # Insufficient for 1000 Cr toll
        init_shields = self.rival.ship.shields

        fee_result = self.kernel.cartography_manager.check_toll_transit(
            self.rival, from_sec=10, to_sec=70, kernel=self.kernel
        )
        self.assertEqual(fee_result, -1)
        self.assertEqual(self.rival.ship.shields, init_shields - 35)

    def test_set_toll_fee(self):
        """Owner can reconfigure its toll fee - any it chooses; none set returns it to what the shortcut is worth."""
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-SHORTCUT", self.kernel)
        self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_DEPLOY,
            shortcut_id="SMUGGLER_SHORTCUT",
            toll_fee=500,
        )
        gate_id = self.player.toll_gates[0]

        # Valid update
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_SET_FEE,
            gate_id=gate_id,
            toll_fee=1200,
        )
        self.assertTrue(res.success)
        self.assertEqual(self.kernel.cartography_manager.toll_gates[gate_id].toll_fee, 1200)

        # No cap: an owner's price is its own (the market answers it - passers go round)
        res_high = self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_SET_FEE,
            gate_id=gate_id,
            toll_fee=9999,
        )
        self.assertTrue(res_high.success)
        self.assertEqual(self.kernel.cartography_manager.toll_gates[gate_id].toll_fee, 9999)

        # None set: what the shortcut is worth to each passer (transit.gate_fee)
        self.kernel.dispatch(self.player.id, ActionType.TOLL_GATE_SET_FEE, gate_id=gate_id, toll_fee=0)
        gate = self.kernel.cartography_manager.toll_gates[gate_id]
        from xylarium.kernel import transit
        self.rival.credits = 10 ** 9
        expect = transit.gate_fee(self.kernel, self.rival, gate)
        paid = self.kernel.cartography_manager.check_toll_transit(self.rival, from_sec=10, to_sec=70, kernel=self.kernel)
        self.assertEqual(paid, expect)

        # Non-owner cannot update
        res_rival = self.kernel.cartography_manager.set_toll_fee(self.rival, gate_id, 300)
        self.assertFalse(res_rival.success)
        self.assertIn("Cannot modify toll rates of a gate you do not own", res_rival.message)


class TestForgedStarmapChits(unittest.TestCase):
    """Test synthesizing forged starmap chits, selling to brokers, and baiting rivals into ambushes."""

    def setUp(self):
        self.kernel = GameKernel(seed=303)
        self.player = self.kernel.register_player("forger", "Test Forger")
        self.player.credits = 10000

        self.rival = Captain(
            id="target_ai",
            name="Capt. Voss",
            is_ai=True,
            personality=AIPersonality.INDUSTRIALIST,
            ship=Ship(
                ship_type="Cruiser",
                cargo=CargoHold(capacity=50),
                shields=100,
                max_shields=100,
                fighters=25,
            ),
            credits=5000,
            turns_left=10,
            sector_id=1,
        )
        self.kernel.captains[self.rival.id] = self.rival

    def test_forge_chit_requires_fragment(self):
        """Forging requires at least 1 genuine starmap fragment to corrupt."""
        self.player.cartography_fragments = []
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_FORGE_CHIT,
            mode="sell"
        )
        self.assertFalse(res.success)
        self.assertIn("requires 1 genuine starmap fragment", res.message)

    def test_forge_chit_requires_credits(self):
        """Forging requires sufficient credits for neural synthesis chips."""
        self.player.cartography_fragments = [dict(FRAGMENT_TEMPLATES[0])]
        self.player.credits = 100
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_FORGE_CHIT,
            mode="sell"
        )
        self.assertFalse(res.success)
        self.assertIn("Credits", res.message)

    def test_forge_chit_sell_mode(self):
        """Mode 'sell' sells counterfeit chit to shady broker for net profit."""
        self.player.cartography_fragments = [dict(FRAGMENT_TEMPLATES[0])]
        init_credits = self.player.credits

        res = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_FORGE_CHIT,
            mode="sell"
        )
        self.assertTrue(res.success)
        self.assertEqual(len(self.player.cartography_fragments), 0)
        # Expected credits: init - FORGED_CHIT_SYNTH_COST + FORGED_CHIT_BROKER_VALUE
        expected = init_credits - FORGED_CHIT_SYNTH_COST + FORGED_CHIT_BROKER_VALUE
        self.assertEqual(self.player.credits, expected)
        self.assertIn("sold to port broker", res.message.lower())

    def test_forge_chit_plant_mode_ambushes_rival(self):
        """Mode 'plant' baits rival into Anarchy pirate ambush and inflicts shield damage."""
        self.player.cartography_fragments = [dict(FRAGMENT_TEMPLATES[0])]
        init_credits = self.player.credits
        rival_init_shields = self.rival.ship.shields

        res = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_FORGE_CHIT,
            mode="plant",
            target_rival_id=self.rival.id
        )
        self.assertTrue(res.success)
        self.assertEqual(len(self.player.cartography_fragments), 0)
        self.assertLess(self.rival.ship.shields, rival_init_shields)
        self.assertIn("ambushed", res.message.lower())
        # The ambush pays in salvaged hull scrap, not minted credits
        self.assertEqual(self.player.credits, init_credits - FORGED_CHIT_SYNTH_COST)
        self.assertGreater(self.player.ship.cargo.held("Fe"), 0)


class TestElementalCatalysis(unittest.TestCase):
    """Test periodic elemental catalysis of Precursor Cipher Zeta-9 (PUZZLE-VAULT)."""

    def setUp(self):
        self.kernel = GameKernel(seed=404)
        self.player = self.kernel.register_player("chemist", "Alchemist")
        self.player.credits = 10000
        self.puzzle = self.kernel.cartography_manager.puzzles["PUZZLE-VAULT"]

    def test_vault_puzzle_requires_reagents(self):
        """PUZZLE-VAULT initializes with required reagents and catalysis locked."""
        self.assertIn("SpR", self.puzzle.required_reagents)
        self.assertIn("U", self.puzzle.required_reagents)
        self.assertFalse(self.puzzle.is_catalyzed)

    def test_decryption_incomplete_without_catalysis(self):
        """Even if all grid nodes are revealed and aligned, decryption remains incomplete without catalysis."""
        # Reveal and align all nodes and bridges
        for row in self.puzzle.grid_nodes:
            for node in row:
                node["is_revealed"] = True
                node["vector_angle"] = node["target_angle"]
        for k in self.puzzle.grid_bridges:
            self.puzzle.grid_bridges[k] = True

        self.assertFalse(self.puzzle.is_catalyzed)
        self.assertFalse(self.puzzle.is_decryption_complete())

    def test_catalyze_from_cargo_elements(self):
        """Injecting rare periodic elements from cargo hold satisfies catalysis requirements."""
        self.player.ship.cargo.elements["U"] = 5
        self.player.ship.cargo.elements["SpR"] = 5

        # Partial injection of U
        res1 = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_CATALYZE,
            puzzle_id="PUZZLE-VAULT",
            element="U",
            amount=5
        )
        self.assertTrue(res1.success)
        self.assertEqual(self.puzzle.applied_reagents["U"], 5)
        self.assertFalse(self.puzzle.is_catalyzed)

        # Full injection with SpR
        res2 = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_CATALYZE,
            puzzle_id="PUZZLE-VAULT",
            element="SpR",
            amount=5
        )
        self.assertTrue(res2.success)
        self.assertEqual(self.puzzle.applied_reagents["SpR"], 5)
        self.assertTrue(self.puzzle.is_catalyzed)
        self.assertIn("Quantum lock dissolved", res2.message)

    def test_tech_equipment_fallback_for_uranium(self):
        """If elemental U is absent, tech equipment in cargo can fulfill Uranium catalysis."""
        self.player.ship.cargo.elements["SpR"] = 5
        self.player.ship.cargo.equipment = 10

        res = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_CATALYZE,
            puzzle_id="PUZZLE-VAULT",
            element="U",
            amount=5
        )
        self.assertTrue(res.success)
        self.assertEqual(self.puzzle.applied_reagents["U"], 5)
        self.assertEqual(self.player.ship.cargo.equipment, 5)

    def test_species_cryogenic_bonus(self):
        """Cryocoherent Stillcold species automatically fulfills Spiral Rime (SpR) cryogenic requirement."""
        self.player.species = "Stillcold Cryocoherent"
        self.player.ship.cargo.elements["U"] = 5

        # When running catalysis, SpR is automatically fulfilled
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.CARTOGRAPHY_CATALYZE,
            puzzle_id="PUZZLE-VAULT",
            element="U",
            amount=5
        )
        self.assertTrue(res.success)
        self.assertEqual(self.puzzle.applied_reagents["SpR"], 5)
        self.assertEqual(self.puzzle.applied_reagents["U"], 5)
        self.assertTrue(self.puzzle.is_catalyzed)


class TestSurveyProbeFleets(unittest.TestCase):
    """Test commissioning autonomous Deep-Space Survey Probes and frontier sweeps."""

    def setUp(self):
        self.kernel = GameKernel(seed=505)
        self.player = self.kernel.register_player("explorer", "Explorer One")
        self.player.credits = 25000

    def test_launch_survey_probe_success(self):
        """Commissioning a probe deducts credits and registers probe telemetry."""
        init_credits = self.player.credits
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.SURVEY_PROBE_LAUNCH,
            target_sector=75
        )
        self.assertTrue(res.success)
        self.assertEqual(self.player.credits, init_credits - SURVEY_PROBE_COST_CREDITS)
        self.assertEqual(len(self.player.survey_probes), 1)

        probe_id = self.player.survey_probes[0]
        probe = self.kernel.cartography_manager.survey_probes[probe_id]
        self.assertEqual(probe.owner_id, self.player.id)
        self.assertEqual(probe.status, "SCANNING")
        self.assertEqual(probe.shields, 50)

    def test_tick_survey_probes_autonomous_movement(self):
        """Probes autonomously warp between adjacent sectors during simulation ticks."""
        self.kernel.dispatch(
            self.player.id,
            ActionType.SURVEY_PROBE_LAUNCH,
            target_sector=75
        )
        probe_id = self.player.survey_probes[0]
        probe = self.kernel.cartography_manager.survey_probes[probe_id]
        initial_sector = probe.current_sector

        # Advance world simulation ticks
        for _ in range(5):
            self.kernel.cartography_manager.tick_survey_probes(self.kernel)

        self.assertGreater(len(probe.sectors_surveyed), 1)
        self.assertIn(probe.current_sector, self.kernel.sectors)

    def test_probe_fragment_harvesting_in_anarchy(self):
        """Probes surveying lawless Anarchy sectors harvest starmap fragments and beam them to owner."""
        self.kernel.dispatch(
            self.player.id,
            ActionType.SURVEY_PROBE_LAUNCH,
            target_sector=75
        )
        probe_id = self.player.survey_probes[0]
        probe = self.kernel.cartography_manager.survey_probes[probe_id]

        # Place probe in Sector 75 (Deep Anarchy where all warps are in Anarchy)
        probe.current_sector = 75
        probe.sectors_surveyed = [75]

        # Mock random to guarantee discovery
        import random
        orig_random = random.Random.random

        def mock_random(inst):
            return 0.1  # Triggers 35% chance for fragment drop
        random.Random.random = mock_random

        try:
            logs = self.kernel.cartography_manager.tick_survey_probes(self.kernel)
            self.assertGreater(probe.fragments_found, 0)
            self.assertGreater(len(self.player.cartography_fragments), 0)
            self.assertTrue(any("PROBE DISCOVERY" in log for log in logs))
        finally:
            random.Random.random = orig_random

    def test_probe_hazard_micrometeorite_damage(self):
        """Probes taking critical shield damage transition to LOST_SIGNAL."""
        self.kernel.dispatch(
            self.player.id,
            ActionType.SURVEY_PROBE_LAUNCH,
            target_sector=75
        )
        probe_id = self.player.survey_probes[0]
        probe = self.kernel.cartography_manager.survey_probes[probe_id]
        probe.shields = 10  # Low shields
        probe.current_sector = 75
        probe.sectors_surveyed = [75]

        import random
        orig_random = random.Random.random
        orig_randint = random.Random.randint

        def mock_random(inst):
            return 0.05  # Triggers 10% micrometeorite hazard
        def mock_randint(inst, a, b):
            return 20  # Deals 20 dmg, destroying 10 shields
        random.Random.random = mock_random
        random.Random.randint = mock_randint

        try:
            logs = self.kernel.cartography_manager.tick_survey_probes(self.kernel)
            self.assertEqual(probe.shields, 0)
            self.assertEqual(probe.status, "LOST_SIGNAL")
            self.assertTrue(any("Signal lost" in log for log in logs))
        finally:
            random.Random.random = orig_random
            random.Random.randint = orig_randint


class TestCartographicEspionage(unittest.TestCase):
    """Test covert operation 'cartographic_heist' against rival data vaults."""

    def setUp(self):
        self.kernel = GameKernel(seed=606)
        self.player = self.kernel.register_player("spymaster", "Agent Zero")
        self.player.credits = 50000
        self.player.operatives = 10

        # Create rival with fragments and secret coordinates
        self.rival = Captain(
            id="rival_exec",
            name="Cynthia Voss",
            is_ai=True,
            personality=AIPersonality.INDUSTRIALIST,
            ship=Ship(
                ship_type="Battleship",
                cargo=CargoHold(capacity=60),
                shields=150,
                max_shields=150,
                fighters=30,
            ),
            credits=20000,
            turns_left=15,
            sector_id=1,
            operatives=0,
            unlocked_secrets=["GHOST_NEXUS"],
            cartography_fragments=[dict(FRAGMENT_TEMPLATES[0]), dict(FRAGMENT_TEMPLATES[1])],
        )
        self.kernel.captains[self.rival.id] = self.rival

    def test_cartographic_heist_minimum_operatives(self):
        """Operation requires at least 3 operatives."""
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.COVERT_OP,
            target_type="SHIP",
            target_id=self.rival.id,
            op_type="cartographic_heist",
            operatives=2,
        )
        self.assertFalse(res.success)
        self.assertIn("minimum of 3 operatives", res.message)

    def test_cartographic_heist_success(self):
        """Successful heist exfiltrates chart fragments, secret coordinates, and earns an intel bounty."""
        import random
        orig_random = random.random
        random.random = lambda: 0.1  # Guarantee success

        try:
            init_frags = len(self.player.cartography_fragments)
            init_credits = self.player.credits

            res = self.kernel.dispatch(
                self.player.id,
                ActionType.COVERT_OP,
                target_type="SHIP",
                target_id=self.rival.id,
                op_type="cartographic_heist",
                operatives=5,
            )
            self.assertTrue(res.success)
            self.assertGreater(len(self.player.cartography_fragments), init_frags)
            self.assertIn("GHOST_NEXUS", self.player.unlocked_secrets)
            self.assertGreater(self.player.credits, init_credits)
            self.assertIn("stolen_fragments", res.data)
            self.assertIn("intel_bounty", res.data)
        finally:
            random.random = orig_random


class TestExpansionsPersistence(unittest.TestCase):
    """Test persistence of toll gates, survey probes, and catalytic puzzle states."""

    def setUp(self):
        self.kernel = GameKernel(seed=707)
        self.player = self.kernel.register_player("archivist", "Archivist Prime")
        self.player.credits = 50000

    def test_full_expansions_save_and_load(self):
        """Save and load universe state with active toll gates, survey probes, and catalyzed puzzle."""
        # 1. Setup shortcut and deploy toll gate
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-SHORTCUT", self.kernel)
        self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_DEPLOY,
            shortcut_id="SMUGGLER_SHORTCUT",
            toll_fee=750,
        )
        gate_id = self.player.toll_gates[0]
        gate = self.kernel.cartography_manager.toll_gates[gate_id]
        gate.total_revenue = 1500
        gate.total_transits = 2

        # 2. Launch survey probe
        self.kernel.dispatch(
            self.player.id,
            ActionType.SURVEY_PROBE_LAUNCH,
            target_sector=80,
        )
        probe_id = self.player.survey_probes[0]
        probe = self.kernel.cartography_manager.survey_probes[probe_id]
        probe.fragments_found = 3
        probe.shields = 35

        # 3. Catalyze PUZZLE-VAULT
        vault = self.kernel.cartography_manager.puzzles["PUZZLE-VAULT"]
        vault.applied_reagents = {"SpR": 5, "U": 5}
        vault.is_catalyzed = True

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            filepath = tf.name

        try:
            saved = StatePersistence.save_to_file(self.kernel, filepath)
            self.assertTrue(saved)

            loaded = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(loaded)
            self.assertTrue(hasattr(loaded, "cartography_manager"))

            # Verify Toll Gate
            self.assertIn(gate_id, loaded.cartography_manager.toll_gates)
            loaded_gate = loaded.cartography_manager.toll_gates[gate_id]
            self.assertEqual(loaded_gate.toll_fee, 750)
            self.assertEqual(loaded_gate.total_revenue, 1500)
            self.assertEqual(loaded_gate.total_transits, 2)
            self.assertEqual(loaded_gate.sector_a, 10)
            self.assertEqual(loaded_gate.sector_b, 70)

            # Verify Survey Probe
            self.assertIn(probe_id, loaded.cartography_manager.survey_probes)
            loaded_probe = loaded.cartography_manager.survey_probes[probe_id]
            self.assertEqual(loaded_probe.fragments_found, 3)
            self.assertEqual(loaded_probe.shields, 35)
            self.assertEqual(loaded_probe.status, "SCANNING")

            # Verify PUZZLE-VAULT Catalysis
            loaded_vault = loaded.cartography_manager.puzzles["PUZZLE-VAULT"]
            self.assertTrue(loaded_vault.is_catalyzed)
            self.assertEqual(loaded_vault.applied_reagents.get("SpR"), 5)
            self.assertEqual(loaded_vault.applied_reagents.get("U"), 5)

        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


class TestTerminalRendererExpansions(unittest.TestCase):
    """Test renderer displaying catalytic reagents, toll gates, and survey probes with strict 80-column compliance."""

    def setUp(self):
        self.kernel = GameKernel(seed=808)
        self.player = self.kernel.register_player("viewer", "View Captain")
        self.player.credits = 50000

    def test_render_expansions_and_80_col_compliance(self):
        """Render cartography screen containing toll gates, probes, and catalytic reagents within 80 columns."""
        # 1. Select PUZZLE-VAULT
        self.kernel.dispatch(self.player.id, ActionType.CARTOGRAPHY_SELECT, puzzle_id="PUZZLE-VAULT")

        # 2. Deploy toll gate
        self.kernel.cartography_manager.solve_puzzle(self.player, "PUZZLE-SHORTCUT", self.kernel)
        self.kernel.dispatch(
            self.player.id,
            ActionType.TOLL_GATE_DEPLOY,
            shortcut_id="SMUGGLER_SHORTCUT",
            toll_fee=500,
        )

        # 3. Launch survey probe
        self.kernel.dispatch(self.player.id, ActionType.SURVEY_PROBE_LAUNCH, target_sector=65)

        view = self.kernel.get_player_view(self.player.id)
        rendered = TerminalRenderer.render_cartography_screen(view)

        # Check content exists
        self.assertIn("Periodic Catalytic Reagents", rendered)
        self.assertIn("Orbital Toll Gates & Revenue", rendered)
        self.assertIn("Autonomous Survey Drones", rendered)

        # Check 80-column compliance
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
