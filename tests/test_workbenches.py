"""
Unit and integration test suite for Xylarium Advanced Workbenches & In-Game Minigames:
1. Technologies Workbench (Harmonic Resonance & Capability Perks)
2. Stock Markets Workbench (Synthetic Index Basket, Leverage & ISSE Arbitrage)
3. FX Markets Workbench (Reserve Currency Basket Balancing & Peg Corridor Defense)
4. Diplomacies Workbench (SU(2) Epistemic Resonance & 5-Clause Interstellar Treaties)
5. Starcraft Workbench (Subsystem Power Grid Harmonics & Living Bio-Chitin Hull Culturing)
6. Docks & Logistics Workbench (M/M/c Queueing Theory & Spaceport Turnaround Optimization)
7. Satellites Workbench (Walker-Delta T/P/F Geometry & Planetary Payloads)
8. Cyclical Production Simulation Integration & State Persistence
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Planet, Captain
from xylarium.kernel.workbenches import (
    calc_tech_resonance,
    calc_market_index,
    calc_fx_corridor,
    calc_diplomatic_resonance,
    calc_starcraft_tuning,
    calc_dock_logistics,
    calc_satellite_constellation,
    is_capability_unlocked,
)


class TestWorkbenches(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.player_id = "captain_turing"
        self.player = self.kernel.register_player(self.player_id, "Captain Turing")
        self.player.sector_id = 1
        self.player.credits = 100000

        # Ensure planet in current sector
        self.sector = self.kernel.sectors[1]
        if not self.sector.planets:
            self.sector.planets.append(
                Planet(
                    id="P-WB-01",
                    sector_id=1,
                    name="Syntropy Prime",
                    planet_type="TERRESTRIAL",
                    owner_id=self.player_id,
                )
            )
        self.planet = self.sector.planets[0]

    def test_capability_gating(self):
        """Test strict technology capability gating across workbenches."""
        # Clean player tech
        self.player.technologies = []
        self.player.rank_tier = 0

        # Attempt tech tune on fission without having fission
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_TECH_TUNE,
            capability="fission",
            frequency=5.0,
            flux=5.0,
            efficiency=5.0,
        )
        self.assertFalse(res.success)
        self.assertIn("has not been discovered", res.message)

        # Grant fission
        self.player.technologies.append("fission")
        self.assertTrue(is_capability_unlocked(self.player, "fission", self.kernel))

    def test_tech_workbench_resonance(self):
        """Test harmonic resonance calibration minigame and deterministic target lock."""
        self.player.technologies.append("fission")

        # 1. Inspect native targets for fission
        calc = calc_tech_resonance("fission", 5.0, 5.0, 5.0)
        w_star = calc["w_target"]
        phi_star = calc["phi_target"]
        eta_star = calc["eta_target"]

        # 2. Submit exact resonant frequencies
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_TECH_TUNE,
            capability="fission",
            frequency=w_star,
            flux=phi_star,
            efficiency=eta_star,
        )
        self.assertTrue(res.success)
        self.assertIn("HARMONIC RESONANCE LOCKED", res.message)
        self.assertGreaterEqual(res.data["q_score"], 0.95)
        self.assertEqual(res.data["grade"], "PERFECT_HARMONIC")
        self.assertIn("reactor_output_bonus", res.data["perks"])

        # Verify state persistence on captain
        wb_tech = self.player.workbenches.get("technologies", {}).get("fission")
        self.assertIsNotNone(wb_tech)
        self.assertTrue(wb_tech["is_locked"])

    def test_market_workbench_index(self):
        """Test algorithmic ETF index basket backtesting and Sharpe ratio registration on ISSE."""
        self.player.technologies.append("computation")

        # Test index creation with balanced weights and 1.5x leverage
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_MARKET_TUNE,
            index_name="ALPHA-INDEX",
            basket=["ORE", "EQUIPMENT", "EXOTICS"],
            weights=[0.3, 0.4, 0.3],
            leverage=1.5,
            spread_threshold=0.02,
        )
        self.assertTrue(res.success)
        self.assertIn("ISSE ETF LISTING APPROVED", res.message)
        self.assertGreaterEqual(res.data["sharpe_ratio"], 1.20)
        self.assertGreater(res.data["cycle_dividend"], 0)

        # Verify captain holds registered index
        indices = self.player.workbenches.get("market_indices", {})
        self.assertIn("ALPHA-INDEX", indices)
        self.assertTrue(indices["ALPHA-INDEX"]["is_listed"])

    def test_fx_workbench_corridor_defense(self):
        """Test currency reserve basket balancing and peg corridor defense."""
        self.player.technologies.append("networks")
        self.player.fx_wallet["TERRA"] = 1000

        # Deploy peg corridor around current live rate
        live_rate = float(self.kernel.fx_market.rate("TERRA"))
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_FX_TUNE,
            anchor_currency="SOL",
            peg_currency="TERRA",
            corridor_min=live_rate - 0.05,
            corridor_max=live_rate + 0.05,
            reserve_allocation_pct=0.40,
        )
        self.assertTrue(res.success)
        self.assertIn("PEG CORRIDOR DEFENDED", res.message)
        self.assertGreaterEqual(res.data["stability_score"], 0.70)
        self.assertGreater(res.data["daily_carry_yield"], 0)

        # Verify state stored
        pegs = self.player.workbenches.get("fx_pegs", {})
        self.assertIn("SOL_TERRA", pegs)
        self.assertTrue(pegs["SOL_TERRA"]["is_defended"])

    def test_diplomacy_workbench_su2_treaty(self):
        """Test SU(2) epistemic holonomy alignment and bilateral treaty ratification."""
        self.player.technologies.append("radio")

        # Negotiate balanced treaty clauses
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_DIPLOMACY_TUNE,
            civ_name="Zephyrian Enclave",
            tariff_reduction_pct=25.0,
            escort_wings=2,
            mining_concessions="SHARED",
            scientific_exchange_pct=25.0,
            migration_quota=150,
        )
        self.assertTrue(res.success)
        self.assertIn("DIPLOMATIC CONCORD RATIFIED", res.message)
        self.assertGreaterEqual(res.data["su2_resonance"], 0.65)
        self.assertTrue(res.data["perks"]["non_aggression_pact"])

        # Verify captain treaty registry
        treaties = self.player.workbenches.get("diplomacy_treaties", {})
        self.assertIn("Zephyrian Enclave", treaties)
        self.assertTrue(treaties["Zephyrian Enclave"]["is_ratified"])

    def test_starcraft_workbench_harmonics_and_living_hull(self):
        """Test power grid balancing and living bio-chitin hull culturing."""
        self.player.technologies.append("orbit")
        initial_max_shields = self.player.ship.max_shields

        # Add BIO_CHITIN to cargo
        self.player.ship.cargo.elements["BIO_CHITIN"] = 2
        self.assertEqual(self.player.ship.cargo.held("BIO_CHITIN"), 2)

        # Tune power grid and culture living hull
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_STARCRAFT_TUNE,
            weapons_pct=25.0,
            kinetic_pct=20.0,
            shields_pct=35.0,
            drives_pct=20.0,
            living_material="BIO_CHITIN",
        )
        self.assertTrue(res.success)
        self.assertIn("STARCRAFT GRID HARMONIZED", res.message)
        self.assertIn("Living Hull cultured", res.message)
        self.assertTrue(res.data["living_hull_active"])

        # Verify 1 unit of BIO_CHITIN consumed
        self.assertEqual(self.player.ship.cargo.held("BIO_CHITIN"), 1)

        # Verify max shields increased from harmonic factor
        self.assertGreaterEqual(self.player.ship.max_shields, initial_max_shields)

    def test_dock_logistics_mmc_queueing(self):
        """Test spaceport berth allocation and M/M/c queueing turnaround optimization."""
        self.player.technologies.append("orbit")

        # Tune dock with 4 berths and high fuel throughput
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_DOCK_TUNE,
            planet_id=self.planet.id,
            crane_automation_berths=4,
            fuel_hydrant_throughput=50.0,
            docking_fee_rate=80,
            express_lane=True,
        )
        self.assertTrue(res.success)
        self.assertIn("SPACEPORT LOGISTICS OPTIMIZED", res.message)
        self.assertLess(res.data["traffic_intensity_rho"], 0.92)
        self.assertTrue(res.data["is_stable"])
        self.assertGreater(res.data["port_revenue_per_cycle"], 0)

        # Verify planet society and captain storage
        self.assertIn("dock_logistics", self.planet.society.get("workbenches", {}))
        self.assertIn(self.planet.id, self.player.workbenches.get("dock_logistics", {}))

    def test_satellite_constellation_walker_delta(self):
        """Test Walker-Delta constellation geometry and specialized orbital payload."""
        self.player.technologies.append("orbit")
        initial_shields = self.planet.max_shields

        # Deploy 24/4/1 DEFENSE constellation at 1200 km
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_SATELLITE_TUNE,
            planet_id=self.planet.id,
            payload_type="DEFENSE",
            total_satellites=24,
            orbital_planes=4,
            phase_factor=1,
            altitude_km=1200.0,
        )
        self.assertTrue(res.success)
        self.assertIn("WALKER-DELTA CONSTELLATION DEPLOYED", res.message)
        self.assertGreaterEqual(res.data["surface_coverage"], 0.75)
        self.assertTrue(res.data["is_operational"])

        # Verify planetary defense shields boosted
        self.assertGreater(self.planet.max_shields, initial_shields)
        self.assertIn("DEFENSE", self.planet.society.get("workbenches", {}).get("constellations", {}))

    def test_simulation_tick_passive_yields(self):
        """Test live production simulation tick advances dividends, carry yields, and self-repair."""
        self.player.technologies.extend(["computation", "networks", "orbit"])

        # 1. Register ETF index
        self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_MARKET_TUNE,
            index_name="YIELD-ETF",
            basket=["ORE", "EQUIPMENT"],
            weights=[0.5, 0.5],
            leverage=2.0,
        )
        start_credits = self.player.credits

        # 2. Defend FX peg
        self.player.fx_wallet["CYGNUS"] = 100
        self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_FX_TUNE,
            anchor_currency="SOL",
            peg_currency="CYGNUS",
            corridor_min=0.90,
            corridor_max=1.10,
            reserve_allocation_pct=0.50,
        )
        start_cygnus = self.player.fx_wallet.get("CYGNUS", 0)

        # 3. Setup living hull self-repair
        self.player.ship.cargo.elements["BIO_CHITIN"] = 1
        self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_STARCRAFT_TUNE,
            weapons_pct=25.0, kinetic_pct=25.0, shields_pct=25.0, drives_pct=25.0,
            living_material="BIO_CHITIN",
        )
        # Damage shields intentionally
        self.player.ship.shields = 20

        # Advance world simulation tick
        self.kernel.tick_simulation()

        # Verify passive stock dividend received
        self.assertGreater(self.player.credits, start_credits)

        # Verify passive FX carry return deposited
        self.assertGreater(self.player.fx_wallet.get("CYGNUS", 0), start_cygnus)

        # Verify living hull regenerated shields
        self.assertGreater(self.player.ship.shields, 20)

    def test_state_persistence(self):
        """Test complete serialization and deserialization of workbench state on Captain."""
        self.player.technologies.append("computation")
        self.kernel.dispatch(
            self.player_id,
            ActionType.WORKBENCH_MARKET_TUNE,
            index_name="PERSIST-ETF",
            basket=["ORE", "EXOTICS"],
            weights=[0.5, 0.5],
            leverage=1.2,
        )
        self.assertIn("PERSIST-ETF", self.player.workbenches.get("market_indices", {}))

        # Serialize
        data = self.player.to_dict()
        self.assertIn("workbenches", data)
        self.assertIn("market_indices", data["workbenches"])

        # Deserialize
        restored_cap = Captain.from_dict(data)
        self.assertIn("market_indices", restored_cap.workbenches)
        self.assertIn("PERSIST-ETF", restored_cap.workbenches["market_indices"])


if __name__ == "__main__":
    unittest.main()
