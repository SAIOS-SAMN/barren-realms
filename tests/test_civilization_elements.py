"""
Unit test suite for Netstratum Species Taxon, 5-Axis Periodic Elements,
and Civilization Intelligence Loop in Xylarium.
"""

import unittest
import os
import tempfile
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, CargoHold
from xylarium.kernel.elements import PeriodicTable, PeriodicElement, LINES, LANES, SHELLS, PHASES, SPINS
from xylarium.kernel.civilization import (
    Civilization,
    CivilizationIntelligenceEngine,
    FOUNDING_POLITIES,
    CLASS_ARCHETYPES,
    LEGACY_CLADES,
    CIVIC_PROJECTS,
)
from xylarium.client.renderer import TerminalRenderer
from xylarium.persistence.store import StatePersistence


class TestPeriodicElements(unittest.TestCase):
    """The almanac is a view over measured matter (substances.py): every coordinate read, none declared."""

    def test_the_table_runs_from_hydrogen_past_the_islands(self):
        from xylarium.kernel import substances
        self.assertEqual(LINES, 8)                                   # period 8: the superheavies past 118
        self.assertEqual(LANES, 18)
        self.assertEqual(substances.period(26), 4)
        self.assertEqual(substances.group(26), 8)                    # iron
        self.assertEqual(substances.group(118), 18)                  # oganesson closes the noble group
        self.assertEqual(substances.group(114), 14)                  # flerovium sits under lead
        self.assertEqual(substances.group(92), 3)                    # the actinides fold into group 3

    def test_the_almanacs_names_are_the_real_things_they_describe(self):
        stelalith = PeriodicTable.get_element("stelalith")
        self.assertEqual(stelalith.shell, 3)                         # Mg, Si, O: bridgmanite
        self.assertEqual(stelalith.arity, 4)
        self.assertEqual(stelalith.phase_name, "Refractory")
        self.assertEqual(stelalith.spin, 0)
        chitin = PeriodicTable.get_element("chitinium")
        self.assertEqual(chitin.spin, 1)                             # what life makes is chiral
        umbrite = PeriodicTable.get_element("umbrite")
        self.assertEqual((umbrite.line, umbrite.lane), (8, 2))       # eka-radium: Z 120
        self.assertEqual(umbrite.binds, 2)
        rime = PeriodicTable.get_element("SpR")
        self.assertEqual(rime.binds, 0)                              # the last noble group
        self.assertEqual(PeriodicTable.get_element("mirror_glass").refines_at, 1.0)

    def test_binding_energy_peaks_near_iron(self):
        from xylarium.kernel import substances
        per = {s: substances.binding_per_nucleon(s) for s in ("H", "C", "O", "Fe", "U", "AdL")}
        self.assertAlmostEqual(per["Fe"], 8.8, delta=0.15)          # measured 8.79 MeV
        self.assertGreater(per["Fe"], per["C"])
        self.assertGreater(per["Fe"], per["U"])
        self.assertGreater(per["U"], per["AdL"])                     # past iron, heavier binds less per nucleon

    def test_what_a_chemistry_holds_in_its_hands_is_what_is_solid_at_its_warmth(self):
        from xylarium.kernel import uses
        for metab in ("biotic", "mineral", "cryogenic"):
            elems = PeriodicTable.get_elements_for_metabolism(metab)
            t = max(__import__("xylarium.kernel.worlds", fromlist=["x"]).body_temperature(x)
                    for x in uses._region_solvents(metab))
            for e in elems:
                self.assertTrue(uses.solid_at(e.element_id, t), (metab, e.element_id))
        self.assertEqual(PeriodicTable.get_elements_for_metabolism("plasmic"), [])   # nothing holds in plasma

    def test_metals_free_from_their_ores_in_the_order_their_bonds_allow(self):
        from xylarium.kernel import substances
        cu, fe = substances.reduction_t("CuO"), substances.reduction_t("FeO")
        self.assertIsNotNone(cu)
        self.assertLess(cu, fe)                                      # copper frees long before iron
        ti = substances.reduction_t("TiO2")
        self.assertGreater(ti, fe + 800)                             # titanium needs a furnace near 2000 K
        self.assertLess(substances.reduction_t("TiO2", "Mg"), cu + 1)   # magnesium takes its oxygen cold (Kroll)


class TestSpeciesTaxonAndPolities(unittest.TestCase):
    """Verifies the 13 Class Tiers, Clades, and Netstratum Founding Polities."""

    def test_13_class_tiers_archetypes(self):
        """Ensure all 13 Netstratum class archetypes and sigils are present."""
        self.assertEqual(len(CLASS_ARCHETYPES), 14)  # 0..=13
        self.assertEqual(CLASS_ARCHETYPES[1], ("⬡", "biotic-swarm"))
        self.assertEqual(CLASS_ARCHETYPES[2], ("◈", "geodic-lithovore"))
        self.assertEqual(CLASS_ARCHETYPES[4], ("≋", "telepathic-resonant"))
        self.assertEqual(CLASS_ARCHETYPES[7], ("▲", "apex-solitary"))
        self.assertEqual(CLASS_ARCHETYPES[12], ("❄", "thermal-banker"))
        self.assertEqual(CLASS_ARCHETYPES[13], ("☯", "mirror-form"))

    def test_legacy_clades_vocabulary(self):
        """Verify legacy clade words 1..=20 from Netstratum."""
        self.assertEqual(LEGACY_CLADES[1], "ailuroform")
        self.assertEqual(LEGACY_CLADES[2], "bimaniform")
        self.assertEqual(LEGACY_CLADES[3], "cryocoherens")
        self.assertEqual(LEGACY_CLADES[4], "lithophage")
        self.assertEqual(LEGACY_CLADES[5], "hypobiotid")
        self.assertEqual(LEGACY_CLADES[19], "draconiform")
        self.assertEqual(LEGACY_CLADES[20], "metamorphid")

    def test_founding_polities_roster(self):
        """Verify canonical founding polities from polities.rs are seeded."""
        names = [p["name"] for p in FOUNDING_POLITIES]
        self.assertIn("Tunborn", names)
        self.assertIn("Sylvane", names)
        self.assertIn("Forgeborn", names)
        self.assertIn("Corebound", names)
        self.assertIn("Stillcold", names)
        self.assertIn("Coronal Choir", names)
        self.assertIn("Umbrid", names)
        self.assertIn("Slagborn", names)
        self.assertIn("Vitreous Hex", names)
        self.assertIn("Frostwright", names)

        # Check Tunborn exact Netstratum spec
        tunborn = next(p for p in FOUNDING_POLITIES if p["name"] == "Tunborn")
        self.assertEqual(tunborn["clade"], "hypobiotid")
        self.assertEqual(tunborn["metabolism"], "mineral")
        self.assertEqual(tunborn["disposition"], "expansionist")
        self.assertEqual(tunborn["station"], "progenitor")
        self.assertEqual(tunborn["motto"], "the dark between stars is a bed, not a wall")

        # Check Sylvane exact Netstratum spec
        sylvane = next(p for p in FOUNDING_POLITIES if p["name"] == "Sylvane")
        self.assertEqual(sylvane["class_code"], 7)
        self.assertEqual(sylvane["sigil"], "▲")
        self.assertEqual(sylvane["clade"], "ailuroform")
        self.assertEqual(sylvane["metabolism"], "biotic")
        self.assertEqual(sylvane["disposition"], "epicurean")


class TestCivilizationIntelligenceLoop(unittest.TestCase):
    """Verifies the homological economy, metabolic tension, civic works, and research."""

    def setUp(self):
        self.kernel = GameKernel(seed=123)
        self.player = self.kernel.register_player("archon", "Archon")
        self.player.credits = 10000

        # Find planet with civilization
        self.planet = None
        for s in self.kernel.sectors.values():
            if s.planets and s.planets[0].civilization is not None:
                self.planet = s.planets[0]
                break

        self.assertIsNotNone(self.planet)
        self.assertIsNotNone(self.planet.civilization)

    def test_planets_seeded_with_civilizations_and_elements(self):
        """Inhabited worlds carry a civilization and refined reserves; frontier worlds are
        uninhabited, civilization-free, but still carry elemental veins for settlers."""
        frontier = 0
        for s in self.kernel.sectors.values():
            for p in s.planets:
                self.assertTrue(len(p.element_deposits) > 0)
                if p.population == 0 and p.owner_id is None:
                    frontier += 1
                    self.assertIsNone(p.civilization)
                    continue
                self.assertIsNotNone(p.civilization)
                self.assertTrue(len(p.element_reserves) > 0)
                self.assertTrue(p.civilization.class_code in CLASS_ARCHETYPES)
        self.assertGreater(frontier, 0)

    def test_metabolic_tension_evaluation(self):
        """Tests metabolic demand loads calculation and tension vector."""
        civ = self.planet.civilization
        loads = CivilizationIntelligenceEngine.evaluate_metabolic_loads(civ, 1500)
        self.assertTrue(len(loads) >= 2)

        # Starve planet of silo resources
        self.planet.ore_silo = 0
        self.planet.organics_silo = 0
        self.planet.element_reserves = {}

        civ_res = CivilizationIntelligenceEngine.tick_civilization(civ, self.planet)
        # Should report tension deficit
        self.assertTrue(any(v > 0 for v in civ_res["tension_vector"].values()))
        self.assertTrue(len(civ.trade_urgency) > 0)

    def test_satisfied_tension_advances_civic_works_and_research(self):
        """When metabolic needs are met, surplus drives civic projects and periodic table research."""
        civ = self.planet.civilization
        civ.current_project = "Deep Mantle Siphon"
        civ.project_progress = 0
        civ.research_points = 0

        # Stock ample supplies
        self.planet.ore_silo = 500
        self.planet.organics_silo = 500
        for elem in civ.discovered_elements:
            self.planet.element_reserves[elem] = 100

        init_ore = self.planet.ore_silo
        civ_res = CivilizationIntelligenceEngine.tick_civilization(civ, self.planet)

        self.assertTrue(civ_res["project_advanced"])
        self.assertGreater(civ.project_progress, 0)
        self.assertGreater(civ.research_points, 0)
        # Used a small amount of ore for civic project construction
        self.assertLessEqual(self.planet.ore_silo, init_ore)

    def test_civic_project_completion_effects(self):
        """Completing a civic project applies permanent improvements to the planet."""
        civ = self.planet.civilization
        civ.current_project = "Solar Mirror Array"
        civ.project_progress = 95
        init_shields = self.planet.max_shields

        # Stock supplies
        self.planet.ore_silo = 200
        self.planet.organics_silo = 200
        for elem in civ.discovered_elements:
            self.planet.element_reserves[elem] = 100

        civ_res = CivilizationIntelligenceEngine.tick_civilization(civ, self.planet)
        self.assertEqual(civ_res["project_completed"], "Solar Mirror Array")
        self.assertIn("Solar Mirror Array", civ.civic_projects)
        # Solar Mirror Array adds +100 max shields
        self.assertEqual(self.planet.max_shields, init_shields + 100)
        # Progress reset for next project
        self.assertEqual(civ.project_progress, 0)
        self.assertNotEqual(civ.current_project, "Solar Mirror Array")

    def test_elemental_vein_extraction(self):
        """Civilizations extract the periodic elements they have dug their way to - and only those."""
        civ = self.planet.civilization
        self.planet.element_deposits["stelalith"] = 100
        self.planet.element_reserves["stelalith"] = 5
        civ.tech_level = 3  # High enough to refine line 3 elements
        civ.discovered_elements = [e for e in civ.discovered_elements if e != "stelalith"]
        unknown = CivilizationIntelligenceEngine.tick_civilization(civ, self.planet)
        self.assertNotIn("stelalith", unknown["extracted_elements"])
        self.assertNotIn("stelalith", civ.discovered_elements)
        civ.discovered_elements.append("stelalith")

        civ_res = CivilizationIntelligenceEngine.tick_civilization(civ, self.planet)
        self.assertIn("stelalith", civ_res["extracted_elements"])
        self.assertGreater(civ_res["extracted_elements"]["stelalith"], 0)
        self.assertGreater(self.planet.element_reserves["stelalith"], 5)
        self.assertLess(self.planet.element_deposits["stelalith"], 100)


class TestKernelIntegrationAndPlayerActions(unittest.TestCase):
    """Verifies player dispatch for civic contributions and element transfers."""

    def setUp(self):
        self.kernel = GameKernel(seed=777)
        self.player = self.kernel.register_player("commodore", "Commodore")
        self.player.credits = 10000

        # Move to sector with a planet
        self.target_sector = None
        self.planet = None
        for s in self.kernel.sectors.values():
            if s.planets:
                self.target_sector = s
                self.planet = s.planets[0]
                break

        self.player.sector_id = self.target_sector.id

    def test_player_contribute_civic_project(self):
        """Player invests credits and ore into the civilization's civic project."""
        civ = self.planet.civilization
        civ.project_progress = 10
        self.player.ship.cargo.ore = 20
        self.player.credits = 5000

        initial_silo = self.planet.ore_silo
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.PLANET_CIVIC_CONTRIBUTE,
            planet_id=self.planet.id,
            work_points=15,  # Costs 15 * 5 = 75 Cr
            ore_amount=5,
        )
        self.assertTrue(res.success)
        wages = self.kernel.crew_wage(self.player) if self.kernel.sectors[self.player.sector_id].port else 0
        self.assertEqual(self.player.credits, 5000 - 75 - wages)   # crew wages paid ashore
        self.assertEqual(self.player.ship.cargo.ore, 15)
        self.assertGreater(self.planet.ore_silo, initial_silo)
        # 15 work + 10 ore work = +25 progress (+ autonomous civ progress from tick_simulation)
        self.assertGreaterEqual(civ.project_progress, 10 + 25)

    def test_element_transfer_to_ship_and_to_planet(self):
        """Player transfers periodic elements between planetary reserves and ship cargo hold."""
        self.planet.element_reserves["stelalith"] = 25
        self.player.ship.cargo.capacity = 30
        self.player.ship.cargo.ore = 0
        self.player.ship.cargo.organics = 0  # empty hold (no starter rations) for exact hold math

        # Load 5 units of stelalith into ship
        res = self.kernel.dispatch(
            self.player.id,
            ActionType.PLANET_ELEMENT_TRANSFER,
            planet_id=self.planet.id,
            element_id="stelalith",
            direction="to_ship",
            amount=5,
        )
        self.assertTrue(res.success)
        self.assertEqual(self.planet.element_reserves["stelalith"], 20)
        self.assertEqual(self.player.ship.cargo.elements.get("stelalith"), 5)
        self.assertEqual(self.player.ship.cargo.total_used, 5)

        # Offload 2 units back to planet
        res2 = self.kernel.dispatch(
            self.player.id,
            ActionType.PLANET_ELEMENT_TRANSFER,
            planet_id=self.planet.id,
            element_id="stelalith",
            direction="to_planet",
            amount=2,
        )
        self.assertTrue(res2.success)
        self.assertEqual(self.planet.element_reserves["stelalith"], 22)
        self.assertEqual(self.player.ship.cargo.elements.get("stelalith"), 3)

    def test_cargo_hold_capacity_enforces_elements(self):
        """Cargo hold accounts for periodic elements and bulk density multipliers."""
        hold = CargoHold(capacity=10, ore=5, organics=2, equipment=1, elements={"stelalith": 2})
        self.assertEqual(hold.total_used, 10)
        # 5 ore (4x density: 1.25 holds) + 2 org (2x: 1.0) + 1 eq (1x: 1.0) + 2 stelalith (1x: 2.0) = 5.25 holds
        self.assertEqual(hold.available_space, 4)
        full_hold = CargoHold(capacity=10, equipment=10)
        self.assertEqual(full_hold.available_space, 0)

    def test_persistence_round_trip_with_civilizations_and_elements(self):
        """StatePersistence preserves civilizations, element veins, reserves, and ship holds."""
        self.planet.element_reserves["umbrite"] = 42
        self.planet.civilization.tech_level = 4
        self.planet.civilization.era_index = 2
        self.player.ship.cargo.elements["cryogenite"] = 7

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            saved = StatePersistence.save_to_file(self.kernel, filepath)
            self.assertTrue(saved)

            loaded_kernel = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(loaded_kernel)

            loaded_sec = loaded_kernel.sectors[self.target_sector.id]
            loaded_planet = loaded_sec.planets[0]
            self.assertEqual(loaded_planet.element_reserves.get("umbrite"), 42)
            self.assertEqual(loaded_planet.civilization.tech_level, 4)
            self.assertEqual(loaded_planet.civilization.era_index, 2)
            self.assertEqual(loaded_planet.civilization.era_name, "Radiant Ascendant")

            loaded_player = loaded_kernel.captains[self.player.id]
            self.assertEqual(loaded_player.ship.cargo.elements.get("cryogenite"), 7)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_renderer_outputs(self):
        """TerminalRenderer renders civilization and periodic table almanac cleanly."""
        view = self.kernel.get_player_view(self.player.id)
        planet_data = view["sector"]["planets"][0]

        civ_screen = TerminalRenderer.render_civilization_screen(view, planet_data)
        self.assertIn("NETSTRATUM CIVILIZATION & PERIODIC TABLE ALMANAC", civ_screen)
        self.assertIn("PERIODIC TABLE OF ELEMENTS", civ_screen)
        self.assertIn("METABOLIC TENSION", civ_screen)

        planet_screen = TerminalRenderer.render_planet_screen(view, planet_data)
        self.assertIn("Civilization:", planet_screen)
        self.assertIn("Civic Works:", planet_screen)


if __name__ == "__main__":
    unittest.main()
