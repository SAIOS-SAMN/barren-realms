"""
Unit test suite verifying all 5 core Netstratum/BBS game systems in Xylarium:
1. Dual Cohesion & Ideological Alignment Engine (Social Thermodynamics)
2. Precursor Alchemy & Elemental Transmutation (Closed Matter Loop)
3. Orbital Ephemeris & Dynamic Transit Windows (Astrodynamics)
4. The Imperial Senate & High Offices of the Union (Galactic Governance)
5. Surface Hex/District Grid & Ground Invasion Warfare (The Colony Loop)
"""

import unittest
import os
import tempfile
from typing import Dict, Any

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, ActionResult, Planet, Captain, Ship, CargoHold
from xylarium.kernel.ideology import IdeologyManager, TreatyType, CohesionLedger
from xylarium.kernel.alchemy import AlchemyManager, ALCHEMY_RECIPES
from xylarium.kernel.astronomy import AstronomyManager
from xylarium.kernel.governance import SenateManager, SenateOffice, SenateEdict
from xylarium.kernel.surface import SurfaceManager, DistrictType, TerrainType, SurfaceGrid
from xylarium.persistence.store import StatePersistence
from xylarium.client.renderer import TerminalRenderer


class TestAllFiveSystems(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=1337)
        self.player_id = "test_player"
        self.kernel.register_player(self.player_id, "Commander Shepard")
        self.player = self.kernel.get_player(self.player_id)
        self.player.credits = 100000

    # =========================================================================
    # SYSTEM 1: IDEOLOGY & COHESION LEDGERS (Social Thermodynamics)
    # =========================================================================
    def test_ideology_cohesion_ledger_and_deeds(self):
        mgr = self.kernel.ideology_manager
        rival_id = "ai_trader"

        # Initial ratio defaults to 0.50 (neutral)
        self.assertEqual(mgr.get_standing(self.player_id, rival_id), 0.50)

        # Record syntropic deed on integrity
        mgr.record_deed(self.player_id, rival_id, "integrity", 20.0, is_syntropic=True)
        standing = mgr.get_standing(self.player_id, rival_id)
        self.assertGreater(standing, 0.50)

        # Record entropic deed on morality
        mgr.record_deed(self.player_id, rival_id, "morality", 30.0, is_syntropic=False)
        ledger = mgr.get_ledger(self.player_id, rival_id)
        self.assertEqual(ledger.integrity_syntropic, 20.0)
        self.assertEqual(ledger.morality_entropic, 30.0)

    def test_ideology_treaty_proposal_and_signing(self):
        rival_id = "ai_vane"
        # Propose Non-Aggression treaty (allowed at baseline 0.50)
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.IDEOLOGY_TREATY_PROPOSE,
            target_id=rival_id,
            treaty_type=TreatyType.NON_AGGRESSION.value,
        )
        self.assertTrue(res.success)
        treaty_id = res.data["treaty_id"]

        # Ratify / sign treaty
        res_sign = self.kernel.dispatch(
            rival_id,
            ActionType.IDEOLOGY_TREATY_SIGN,
            treaty_id=treaty_id,
        )
        self.assertTrue(res_sign.success)
        self.assertIn(treaty_id, self.kernel.ideology_manager.treaties)
        self.assertTrue(self.kernel.ideology_manager.treaties[treaty_id].active)

    def test_ideology_high_tier_treaty_refused_when_syntropy_low(self):
        rival_id = "ai_trader"
        # Record heavy entropic deeds to sink standing
        self.kernel.ideology_manager.record_deed(self.player_id, rival_id, "morality", 100.0, is_syntropic=False)
        self.assertLess(self.kernel.ideology_manager.get_standing(self.player_id, rival_id), 0.65)

        # Attempt to propose defensive pact
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.IDEOLOGY_TREATY_PROPOSE,
            target_id=rival_id,
            treaty_type=TreatyType.DEFENSIVE_PACT.value,
        )
        self.assertFalse(res.success)
        self.assertIn("PROPOSAL REFUSED", res.message)

    def test_ideology_famine_relief_aid_dispatch(self):
        # Find a planet in player's current sector or move player to a sector with a planet
        target_planet = self.kernel.get_all_planets()[0]
        self.player.sector_id = target_planet.sector_id
        self.kernel.sectors[target_planet.sector_id].captains.append(self.player.id)

        # Give player organics cargo
        self.player.ship.cargo.organics = 50
        initial_morale = target_planet.morale
        initial_silo = target_planet.organics_silo

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.IDEOLOGY_AID_DISPATCH,
            planet_id=target_planet.id,
            food_units=20,
        )
        self.assertTrue(res.success)
        self.assertEqual(self.player.ship.cargo.organics, 30)
        self.assertEqual(target_planet.organics_silo, initial_silo + 20)
        self.assertGreaterEqual(target_planet.morale, initial_morale)

    # =========================================================================
    # SYSTEM 2: PRECURSOR ALCHEMY & MATTER BALANCE (Transmutation)
    # =========================================================================
    def test_alchemy_recipe_synthesis(self):
        # Setup materials for ADAMANT_LODE (Fe: 3, Ti: 2, catalyst: U -> AdL: 1)
        from xylarium.kernel import knowledge
        self.kernel.activate()
        knowledge.learn(self.kernel, knowledge.holder_of_captain(self.player), "materials", 50)
        self.player.ship.cargo.elements["Fe"] = 10
        self.player.ship.cargo.elements["Ti"] = 10
        self.player.ship.cargo.elements["U"] = 5
        self.player.credits = 10000

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.ALCHEMY_TRANSMUTE,
            recipe_id="ADAMANT_LODE",
        )
        self.assertTrue(res.success)
        self.assertEqual(self.player.ship.cargo.elements["AdL"], 1)
        self.assertEqual(self.player.ship.cargo.elements["Fe"], 7)
        self.assertEqual(self.player.ship.cargo.elements["Ti"], 8)
        self.assertEqual(self.player.ship.cargo.elements["U"], 5)  # Catalyst is not consumed

        # Check heat accumulation
        heat = self.kernel.alchemy_manager.get_heat(self.player_id)
        self.assertGreater(heat, 0.0)

    def test_alchemy_cryo_cooling_and_reactor_overheat_containment(self):
        from xylarium.kernel import knowledge
        self.kernel.activate()
        knowledge.learn(self.kernel, knowledge.holder_of_captain(self.player), "materials", 50)
        self.player.ship.cargo.elements["Fe"] = 20
        self.player.ship.cargo.elements["Ti"] = 20
        self.player.ship.cargo.elements["U"] = 5
        self.player.ship.cargo.elements["cryogenite"] = 2  # Coolant

        # Set heat near cap
        self.kernel.alchemy_manager.heat_accumulated[self.player_id] = 18.0

        # Transmute: will trigger cryo-coolant consumption
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.ALCHEMY_TRANSMUTE,
            recipe_id="ADAMANT_LODE",
        )
        self.assertTrue(res.success)
        self.assertEqual(self.player.ship.cargo.elements["cryogenite"], 1)

    # =========================================================================
    # SYSTEM 3: ORBITAL EPHEMERIS & DYNAMIC TRANSIT WINDOWS (Astrodynamics)
    # =========================================================================
    def test_astronomy_ephemeris_and_keplerian_ticks(self):
        planets = self.kernel.get_all_planets()
        self.assertGreater(len(planets), 0)
        p = planets[0]
        initial_angle = p.orbital_angle

        # Tick astronomy
        self.kernel.astronomy_manager.tick([p])
        self.assertNotEqual(p.orbital_angle, initial_angle)

        pos = self.kernel.astronomy_manager.compute_position(p)
        self.assertEqual(pos.planet_id, p.id)
        self.assertIsNotNone(pos.x)
        self.assertIsNotNone(pos.y)
        self.assertIn("Quadrant", pos.phase_label)

    def test_astronomy_transit_window_scaling(self):
        p1 = Planet(id="p1", sector_id=1, name="Terra", orbital_radius=1.0, orbital_angle=0.0, orbital_period=30)
        p2 = Planet(id="p2", sector_id=1, name="Mars", orbital_radius=1.5, orbital_angle=0.0, orbital_period=60)

        # Perfect conjunction (angle delta = 0.0) -> CHEAP window
        win_cheap = self.kernel.astronomy_manager.compute_transit_window(p1, p2)
        self.assertAlmostEqual(win_cheap.transit_multiplier, 0.60, places=2)
        self.assertIn("CHEAP", win_cheap.window_grade)

        # Perfect opposition (angle delta = 180.0) -> DEAR window
        p2.orbital_angle = 180.0
        win_dear = self.kernel.astronomy_manager.compute_transit_window(p1, p2)
        self.assertAlmostEqual(win_dear.transit_multiplier, 1.75, places=2)
        self.assertIn("DEAR", win_dear.window_grade)
        self.assertGreater(win_dear.effective_distance_au, win_cheap.effective_distance_au)

    # =========================================================================
    # SYSTEM 4: THE IMPERIAL SENATE & HIGH OFFICES (Galactic Governance)
    # =========================================================================
    def test_senate_campaign_and_voting(self):
        gov = self.kernel.governance_manager
        initial_treasury = gov.federal_treasury

        # File candidacy for CHANCELLOR
        res = self.kernel.dispatch(
            self.player_id,
            ActionType.SENATE_CAMPAIGN,
            office=SenateOffice.CHANCELLOR.value,
        )
        self.assertTrue(res.success)
        self.assertEqual(gov.federal_treasury, initial_treasury + 5000)
        self.assertIn(self.player_id, gov.candidates[SenateOffice.CHANCELLOR.value])

        # Cast votes
        res_vote = self.kernel.dispatch(
            self.player_id,
            ActionType.SENATE_VOTE,
            office=SenateOffice.CHANCELLOR.value,
            candidate_id=self.player_id,
        )
        self.assertTrue(res_vote.success)
        self.assertGreater(gov.votes[SenateOffice.CHANCELLOR.value][self.player_id], 0.0)

    def test_senate_election_resolution_and_edict_enactment(self):
        gov = self.kernel.governance_manager
        # Register and vote
        self.kernel.dispatch(self.player_id, ActionType.SENATE_CAMPAIGN, office=SenateOffice.CHANCELLOR.value)
        self.kernel.dispatch(self.player_id, ActionType.SENATE_VOTE, office=SenateOffice.CHANCELLOR.value, candidate_id=self.player_id)

        # Advance cycle to election interval
        gov.next_election_cycle = gov.current_cycle + 1
        gov.tick_senate(list(self.kernel.captains.values()))

        # Verify player inaugurated as CHANCELLOR
        chancellor_holder = gov.offices[SenateOffice.CHANCELLOR.value]
        self.assertEqual(chancellor_holder.incumbent_id, self.player_id)

        # Enact imperial edict (SOL_STIMULUS_REBATE)
        old_credits = self.player.credits
        res_edict = self.kernel.dispatch(
            self.player_id,
            ActionType.SENATE_ENACT_EDICT,
            office=SenateOffice.CHANCELLOR.value,
            edict=SenateEdict.SOL_STIMULUS_REBATE.value,
        )
        self.assertTrue(res_edict.success)
        self.assertGreater(self.player.credits, old_credits)
        self.assertEqual(len(gov.active_edicts), 1)

    # =========================================================================
    # SYSTEM 5: SURFACE DISTRICT GRID & GROUND INVASIONS (The Colony Loop)
    # =========================================================================
    def test_surface_grid_building_and_adjacency_yields(self):
        planet = self.kernel.get_all_planets()[0]
        planet.owner_id = self.player_id
        planet.ore_silo = 500
        self.player.credits = 50000

        grid = SurfaceManager.ensure_surface_grid(planet)
        tile = grid.get_tile(2, 2)
        tile.district = DistrictType.EMPTY

        # Build Mantle Bore at (2, 2)
        res_mine = self.kernel.dispatch(
            self.player_id,
            ActionType.SURFACE_BUILD_DISTRICT,
            planet_id=planet.id,
            x=2,
            y=2,
            district=DistrictType.MANTLE_BORE.value,
        )
        self.assertTrue(res_mine.success)

        # Build Element Refinery at (2, 3) (adjacent)
        res_ref = self.kernel.dispatch(
            self.player_id,
            ActionType.SURFACE_BUILD_DISTRICT,
            planet_id=planet.id,
            x=2,
            y=3,
            district=DistrictType.ELEMENT_REFINERY.value,
        )
        self.assertTrue(res_ref.success)

        # Calculate yields with adjacency
        fresh_grid = SurfaceManager.ensure_surface_grid(planet)
        yields = fresh_grid.calculate_yields(planet)
        self.assertGreater(yields["ore"], 15.0)  # Benefited from adjacency or level
        self.assertGreater(yields["refinery_units"], 2)

    def test_surface_demolition_and_salvage(self):
        planet = self.kernel.get_all_planets()[0]
        planet.owner_id = self.player_id
        planet.ore_silo = 500
        self.player.credits = 50000

        self.kernel.dispatch(
            self.player_id,
            ActionType.SURFACE_BUILD_DISTRICT,
            planet_id=planet.id,
            x=4,
            y=4,
            district=DistrictType.HABITATION_DOME.value,
        )
        old_credits = self.player.credits

        # Demolish
        res_demo = self.kernel.dispatch(
            self.player_id,
            ActionType.SURFACE_DEMOLISH_DISTRICT,
            planet_id=planet.id,
            x=4,
            y=4,
        )
        self.assertTrue(res_demo.success)
        self.assertGreater(self.player.credits, old_credits)

    def test_surface_troop_recruitment_and_ground_invasion(self):
        planet = self.kernel.get_all_planets()[0]
        planet.owner_id = self.player_id
        planet.ore_silo = 500
        self.player.credits = 50000

        # Build Military Barracks
        self.kernel.dispatch(
            self.player_id,
            ActionType.SURFACE_BUILD_DISTRICT,
            planet_id=planet.id,
            x=0,
            y=0,
            district=DistrictType.MILITARY_BARRACKS.value,
        )

        # Recruit 50 assault divisions
        res_rec = self.kernel.dispatch(
            self.player_id,
            ActionType.SURFACE_RECRUIT_TROOPS,
            planet_id=planet.id,
            divisions=50,
        )
        self.assertTrue(res_rec.success)
        self.assertEqual(self.player.troops, 50)

        # Find target foreign planet
        target_planet = self.kernel.get_all_planets()[1]
        target_planet.owner_id = "enemy_warlord"
        target_planet.garrison_troops = 10
        target_planet.treasury = 5000

        # Move player to target planet sector
        self.player.sector_id = target_planet.sector_id
        self.kernel.sectors[target_planet.sector_id].captains.append(self.player.id)

        # Execute ground assault drop-pod invasion
        res_invade = self.kernel.dispatch(
            self.player_id,
            ActionType.SURFACE_INVADE,
            planet_id=target_planet.id,
            divisions=40,
        )
        self.assertTrue(res_invade.success)
        self.assertEqual(target_planet.owner_id, self.player_id)
        self.assertIn("GROUND INVASION SUCCESSFUL", res_invade.message)

    # =========================================================================
    # PERSISTENCE & CLIENT VIEWS
    # =========================================================================
    def test_full_roundtrip_persistence_all_five_systems(self):
        # Mutate data in each system
        self.kernel.ideology_manager.record_deed(self.player_id, "ai_trader", "resonance", 42.0, is_syntropic=True)
        self.kernel.alchemy_manager.heat_accumulated[self.player_id] = 14.5
        all_planets = self.kernel.get_all_planets()
        all_planets[0].orbital_angle = 123.4
        self.kernel.governance_manager.federal_treasury = 250000

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            save_path = f.name

        try:
            saved = StatePersistence.save_to_file(self.kernel, save_path)
            self.assertTrue(saved)

            loaded_kernel = StatePersistence.load_from_file(save_path)
            self.assertIsNotNone(loaded_kernel)

            # Validate each system restored accurately
            self.assertEqual(loaded_kernel.ideology_manager.get_ledger(self.player_id, "ai_trader").resonance_syntropic, 42.0)
            self.assertEqual(loaded_kernel.alchemy_manager.get_heat(self.player_id), 14.5)
            self.assertEqual(loaded_kernel.get_all_planets()[0].orbital_angle, 123.4)
            self.assertEqual(loaded_kernel.governance_manager.federal_treasury, 250000)
            self.assertIsNotNone(loaded_kernel.surface_manager)
        finally:
            if os.path.exists(save_path):
                os.remove(save_path)

    def test_renderer_screens_execute_cleanly(self):
        target_planet = self.kernel.get_all_planets()[0]
        self.player.sector_id = target_planet.sector_id
        view = self.kernel.get_player_view(self.player_id)

        screen_ideo = TerminalRenderer.render_ideology_screen(view)
        self.assertIn("SOCIAL THERMODYNAMICS", screen_ideo)

        screen_alch = TerminalRenderer.render_alchemy_screen(view)
        self.assertIn("PRECURSOR TRANSMUTATION", screen_alch)

        screen_astro = TerminalRenderer.render_astronomy_screen(view)
        self.assertIn("KEPLERIAN ORBITAL EPHEMERIS", screen_astro)

        screen_senate = TerminalRenderer.render_senate_screen(view)
        self.assertIn("THE IMPERIAL SENATE", screen_senate)

        screen_surf = TerminalRenderer.render_surface_screen(view)
        self.assertIn("PLANETARY SURFACE & DISTRICT GRID", screen_surf)


if __name__ == "__main__":
    unittest.main()
