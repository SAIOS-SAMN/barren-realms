"""
tests/test_massive_five_projects.py

Comprehensive test suite verifying the 5 Massive Universe Projects:
1. Dynamic Hyperlane & Wormhole Engineering (WormholeEngineeringManager)
2. Grand Hegemony AI & Galactic Total War (HegemonyAIManager)
3. Deep-Space Stellar Engineering & Star-Lifting (StellarEngineeringManager)
4. Shadow Corporations & Covert Infiltration (ShadowOpsManager)
5. Kardashev Type III Cosmic Ascendance (OmegaProtocolManager)
6. StatePersistence save/load roundtrip across all 5 systems.
"""

import os
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Planet
from xylarium.persistence.store import StatePersistence


class TestMassiveFiveProjects(unittest.TestCase):

    def setUp(self):
        self.kernel = GameKernel(seed=777)
        self.player_id = "COMMANDER_TEST"
        self.kernel.register_player(self.player_id, "Archon Valerius")
        self.captain = self.kernel.get_player(self.player_id)
        self.captain.turns = 500
        self.captain.credits = 10000000
        self.captain.ship.cargo.capacity = 1000
        self.captain.ship.cargo.equipment = 50
        self.captain.ship.cargo.ore = 50

    # =========================================================================
    # PROJECT 1: Dynamic Hyperlane & Wormhole Engineering
    # =========================================================================
    def test_wormhole_engineering_jump_gate_and_tolls(self):
        # Pick two disconnected sectors
        orig = 10
        targ = 55
        self.captain.sector_id = orig
        sec_orig = self.kernel.sectors[orig]
        sec_targ = self.kernel.sectors[targ]
        if targ in sec_orig.warps:
            sec_orig.warps.remove(targ)
        if orig in sec_targ.warps:
            sec_targ.warps.remove(orig)

        # 1. Construct Jump Gate
        res_gate = self.kernel.dispatch(
            self.player_id,
            ActionType.GATE_CONSTRUCT,
            target_sector=targ
        )
        self.assertTrue(res_gate.success)
        self.assertIn(targ, sec_orig.warps)
        self.assertIn(orig, sec_targ.warps)

        # 2. Deploy Toll Buoy
        res_toll = self.kernel.dispatch(
            self.player_id,
            ActionType.TOLL_BUOY_DEPLOY,
            toll_fee=300
        )
        self.assertTrue(res_toll.success)
        self.assertIn(orig, self.kernel.wormhole_manager.toll_buoys)

        # 3. Collapse Wormhole
        res_collapse = self.kernel.dispatch(
            self.player_id,
            ActionType.WORMHOLE_COLLAPSE,
            target_sector=targ
        )
        self.assertTrue(res_collapse.success)
        self.assertNotIn(targ, sec_orig.warps)
        self.assertNotIn(orig, sec_targ.warps)

    # =========================================================================
    # PROJECT 2: Grand Hegemony AI & Galactic Total War
    # =========================================================================
    def test_hegemony_ai_armadas_and_sieges(self):
        # Verify initial great powers seeded
        self.assertIn("IMPERIUM", self.kernel.hegemony_manager.factions)
        self.assertIn("CHOIR", self.kernel.hegemony_manager.factions)
        self.assertIn("SYNDICATE", self.kernel.hegemony_manager.factions)

        # Enlist mercenary strike
        res_strike = self.kernel.dispatch(
            self.player_id,
            ActionType.HEGEMONY_ENLIST_STRIKE,
            faction_id="IMPERIUM",
            target_sector=16
        )
        self.assertTrue(res_strike.success)
        self.assertIn("armada", res_strike.data)

        # Run tick to advance armadas and siege
        self.kernel.hegemony_manager.tick(self.kernel)

    # =========================================================================
    # PROJECT 3: Deep-Space Stellar Engineering & Star-Lifting
    # =========================================================================
    def test_stellar_engineering_lifters_and_ignition(self):
        # 1. Deploy Star-Lifter in Sector 2
        self.captain.sector_id = 2
        res_lifter = self.kernel.dispatch(
            self.player_id,
            ActionType.STELLAR_DEPLOY_LIFTER
        )
        self.assertTrue(res_lifter.success)
        self.assertIn("LIFTER-SEC-002", self.kernel.stellar_manager.star_lifters)

        # Test Star-Lifter tick harvest
        ore_before = self.captain.ship.cargo.ore
        self.kernel.stellar_manager.tick(self.kernel)
        self.assertGreater(self.captain.ship.cargo.ore, ore_before)

        # 2. Proto-star ignition in a dim sector
        sec_dim = self.kernel.sectors[75]
        sec_dim.star_class = "Brown dwarf"
        sec_dim.planets = [Planet(id="P-FROZEN-75", name="Kryos", sector_id=75, planet_type="Frozen")]
        self.captain.sector_id = 75

        res_ignite = self.kernel.dispatch(
            self.player_id,
            ActionType.STELLAR_IGNITE_PROTOSTAR
        )
        self.assertTrue(res_ignite.success)
        self.assertEqual(sec_dim.star_class, "G-class")
        self.assertEqual(sec_dim.planets[0].planet_type, "Terran")

        # 3. Coronal Burst on adjacent sector
        adj = sec_dim.warps[0] if sec_dim.warps else 1
        if adj not in sec_dim.warps:
            sec_dim.warps.append(adj)
        res_burst = self.kernel.dispatch(
            self.player_id,
            ActionType.STELLAR_CORONAL_BURST,
            target_sector=adj
        )
        self.assertTrue(res_burst.success)

    # =========================================================================
    # PROJECT 4: Shadow Corporations & Covert Infiltration
    # =========================================================================
    def test_shadow_ops_sabotage_and_false_flags(self):
        # 1. Incorporate Shadow Company
        res_shell = self.kernel.dispatch(
            self.player_id,
            ActionType.SHADOW_INCORPORATE_SHELL,
            name="Ghost Protocol Syndicate"
        )
        self.assertTrue(res_shell.success)
        self.assertIn("shell", res_shell.data)

        # 2. Plant Sleeper Cell on colony
        p = self.kernel.sectors[1].planets[0]
        p.shields = 500
        p.treasury = 50000

        res_sleeper = self.kernel.dispatch(
            self.player_id,
            ActionType.SHADOW_PLANT_SLEEPER,
            planet_id=p.id
        )
        self.assertTrue(res_sleeper.success)

        # 3. Sabotage Grid
        res_grid = self.kernel.dispatch(
            self.player_id,
            ActionType.SHADOW_EXECUTE_SABOTAGE,
            planet_id=p.id,
            target="GRID"
        )
        self.assertTrue(res_grid.success)
        self.assertLess(p.shields, 500)

        # 4. Treasury Siphon
        res_siphon = self.kernel.dispatch(
            self.player_id,
            ActionType.SHADOW_EXECUTE_SABOTAGE,
            planet_id=p.id,
            target="TREASURY"
        )
        self.assertTrue(res_siphon.success)
        self.assertLess(p.treasury, 50000)

        # 5. False-Flag Strike
        res_ff = self.kernel.dispatch(
            self.player_id,
            ActionType.SHADOW_FALSE_FLAG_STRIKE,
            target_sector=15,
            framed_faction="CHOIR"
        )
        self.assertTrue(res_ff.success)

    # =========================================================================
    # PROJECT 5: Kardashev Type III Cosmic Ascendance
    # =========================================================================
    def test_omega_protocol_ascendance_and_great_filter(self):
        # 1. Upload colony population
        p = self.kernel.sectors[1].planets[0]
        p.population = 10000

        res_upload = self.kernel.dispatch(
            self.player_id,
            ActionType.OMEGA_UPLOAD_POPULATION,
            planet_id=p.id
        )
        self.assertTrue(res_upload.success)
        self.assertEqual(p.population, 0)
        self.assertIn(self.player_id, self.kernel.omega_manager.ascendance_matrices)
        matrix = self.kernel.omega_manager.ascendance_matrices[self.player_id]
        self.assertGreaterEqual(matrix.kardashev_level, 1.15)

        # 2. Anchor Metric Torsion Field
        self.captain.sector_id = 1
        res_torsion = self.kernel.dispatch(
            self.player_id,
            ActionType.OMEGA_METRIC_TORSION
        )
        self.assertTrue(res_torsion.success)
        self.assertIn(1, self.kernel.omega_manager.torsion_fields)

        # 3. Awaken Great Filter
        res_filter = self.kernel.dispatch(
            self.player_id,
            ActionType.OMEGA_AWAKEN_FILTER
        )
        self.assertTrue(res_filter.success)
        self.assertTrue(self.kernel.omega_manager.great_filter_active)

    # =========================================================================
    # PERSISTENCE: Save/Load Roundtrip
    # =========================================================================
    def test_massive_five_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "massive_save.json")
            saved = StatePersistence.save_to_file(self.kernel, filepath)
            self.assertTrue(saved)

            loaded_kernel = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(loaded_kernel)

            # Check that all 5 managers exist and retain initialized state
            self.assertTrue(hasattr(loaded_kernel, "wormhole_manager"))
            self.assertTrue(hasattr(loaded_kernel, "hegemony_manager"))
            self.assertTrue(hasattr(loaded_kernel, "stellar_manager"))
            self.assertTrue(hasattr(loaded_kernel, "shadow_manager"))
            self.assertTrue(hasattr(loaded_kernel, "omega_manager"))

            self.assertIn("IMPERIUM", loaded_kernel.hegemony_manager.factions)


if __name__ == "__main__":
    unittest.main()
