"""
tests/test_emergent_spaceflight.py

Comprehensive test suite verifying the four pillars of emergent spaceflight:
1. Physical Emergence: Biome escape velocity (v_esc) scaling, ore/organics/treasury silos, orbital gantry requirements.
2. Epistemic Emergence: Continuous mathematical deciphering of propulsion tensor equations via intellect & knowledge.
3. Cognitive Emergence: Overcoming terrestrial soil dogma (VOICE_MEMORY/VOICE_URGENCY) via the Axiom of the Stellar Horizon.
4. Multi-Wave Diaspora: Abolishment of artificial lockouts, generational staging turnaround, and recursive daughter colony expansion.
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import Planet
from xylarium.kernel.sovereign_mind import SovereignMindManager, ParliamentaryVoiceType


class TestEmergentSpaceflight(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=4242)
        self.mgr: SovereignMindManager = self.kernel.sovereign_mind_manager
        self.sec = self.kernel.sectors[1]

    def test_physical_gravity_well_and_material_scaling(self):
        """Pillar 1: Physical escape velocity and material silo scaling across biomes."""
        # Low-gravity Barren moon (g_factor = 0.35)
        p_barren = Planet(id="p-barren", name="Barren Rock", sector_id=1, planet_type="BARREN")
        reqs_barren = self.mgr._get_orbital_launch_requirements(p_barren)
        self.assertEqual(reqs_barren["g_factor"], 0.35)
        self.assertEqual(reqs_barren["required_ore"], 28) # int(80 * 0.35)
        self.assertEqual(reqs_barren["required_organics"], 60) # 50 * 1.2 harsh biome
        self.assertEqual(reqs_barren["required_credits"], 525)

        # High-gravity Volcanic world (g_factor = 1.15)
        p_volcanic = Planet(id="p-volc", name="Magma Prime", sector_id=1, planet_type="VOLCANIC")
        reqs_volc = self.mgr._get_orbital_launch_requirements(p_volcanic)
        self.assertEqual(reqs_volc["g_factor"], 1.15)
        self.assertEqual(reqs_volc["required_ore"], 92) # int(80 * 1.15)
        self.assertEqual(reqs_volc["required_organics"], 50)
        self.assertEqual(reqs_volc["required_credits"], 1725)

        # Standard Terrestrial world (g_factor = 1.00)
        p_terra = Planet(id="p-terra", name="Terra Novum", sector_id=1, planet_type="TERRESTRIAL")
        reqs_terra = self.mgr._get_orbital_launch_requirements(p_terra)
        self.assertEqual(reqs_terra["g_factor"], 1.00)
        self.assertEqual(reqs_terra["required_ore"], 80)
        self.assertEqual(reqs_terra["required_organics"], 50)
        self.assertEqual(reqs_terra["required_credits"], 1500)

        # Infrastructure check: requires Citadel L2 or ORBITAL_FOUNDRY
        p_terra.citadel_level = 1
        p_terra.technologies = []
        p_terra.ore_silo = 500
        p_terra.organics_silo = 500
        p_terra.treasury = 5000
        reqs = self.mgr._get_orbital_launch_requirements(p_terra)
        self.assertFalse(reqs["has_gantry"])
        self.assertFalse(reqs["can_build"])

        p_terra.citadel_level = 2
        reqs = self.mgr._get_orbital_launch_requirements(p_terra)
        self.assertTrue(reqs["has_gantry"])
        self.assertTrue(reqs["can_build"])

    def test_epistemic_continuous_mathematical_deciphering(self):
        """Pillar 2: Continuous tensor equation deciphering over research epochs."""
        p = Planet(id="p-epistemic", name="Aethelgard", sector_id=1, population=1200)
        p.citadel_level = 2
        p.technologies = []
        sc = self.mgr.ensure_consciousness(self.kernel, p)

        # Tech sequence: SYNTHETIC_ECOLOGY -> ORBITAL_FOUNDRY -> JUMP_PROPULSION -> INTERSTELLAR_FLIGHT
        target, d_math, breakthrough = self.mgr._decipher_epistemic_progress(self.kernel, sc, p, focus=True)
        self.assertEqual(target, "SYNTHETIC_ECOLOGY")
        self.assertGreater(d_math, 0.3)
        self.assertIn("SYNTHETIC_ECOLOGY", p.epistemic_progress)

        # Advance until breakthrough
        while "SYNTHETIC_ECOLOGY" not in p.technologies:
            self.mgr._decipher_epistemic_progress(self.kernel, sc, p, focus=True)

        self.assertIn("SYNTHETIC_ECOLOGY", p.technologies)

        # Next target should be ORBITAL_FOUNDRY
        target2, _, _ = self.mgr._decipher_epistemic_progress(self.kernel, sc, p, focus=True)
        self.assertEqual(target2, "ORBITAL_FOUNDRY")

    def test_cognitive_stellar_awakening_and_soil_dogma(self):
        """Pillar 3: Overcoming terrestrial insularity (soil dogma) to believe in the stars."""
        p = Planet(id="p-cradle", name="Cradle World", sector_id=1, population=300)
        sc = self.mgr.ensure_consciousness(self.kernel, p)

        # Initial ground-bound state: low population, no orbital tech, no stellar axiom
        sc.self_model.current_gauges.knowledge = 0.20
        sc.self_model.current_gauges.intellect = 0.20
        sc.introspection_skill = 0.20
        sc.ideation_space.ideations["COGNITIVE_TRANSCENDENCE"].amplitude = 0.10

        self.assertFalse(self.mgr._check_stellar_awakening(sc, p))
        self.assertNotIn("AXIOM_OF_THE_STELLAR_HORIZON", sc.mythic_memory.inviolable_axioms)

        # Soil dogma imposes heavy memory penalty on attempting interstellar flight
        potentials_unawakened = self.mgr._evaluate_gauge_action_potentials(self.kernel, sc, p, "DEFENSIVE")
        
        # Now trigger the demographic/intellectual paradigm shift (pop reaches 1000)
        p.population = 1050
        self.assertTrue(self.mgr._check_stellar_awakening(sc, p))
        self.assertIn("AXIOM_OF_THE_STELLAR_HORIZON", sc.mythic_memory.inviolable_axioms)

        # Once awakened, cosmic desire pulls toward the stars
        potentials_awakened = self.mgr._evaluate_gauge_action_potentials(self.kernel, sc, p, "DEFENSIVE")
        # Awakened mind has significantly lower (more favorable) Lagrangian potential for interstellar flight
        self.assertLess(potentials_awakened["COMMISSION_INTERSTELLAR_VESSEL"], potentials_unawakened["COMMISSION_INTERSTELLAR_VESSEL"])

    def test_multi_wave_interstellar_diaspora_and_daughter_colony(self):
        """Pillar 4: Multi-wave expeditions without artificial lockouts & daughter colony emergence."""
        mother = Planet(
            id="p-mother",
            name="Mother Sol",
            sector_id=1,
            population=2500,
            treasury=10000,
            ore_silo=500,
            organics_silo=500,
            citadel_level=2,
            technologies=["SYNTHETIC_ECOLOGY", "ORBITAL_FOUNDRY", "JUMP_PROPULSION", "INTERSTELLAR_FLIGHT"],
        )
        self.sec.planets.append(mother)

        # Empty frontier candidate
        frontier = Planet(
            id="p-frontier-99",
            name="Frontier Dawn",
            sector_id=1,
            population=0,
            owner_id=None,
        )
        self.sec.planets.append(frontier)

        sc_mother = self.mgr.ensure_consciousness(self.kernel, mother)
        self.mgr._check_stellar_awakening(sc_mother, mother)
        self.kernel.cycle_count = 100
        mother.last_diaspora_cycle = 50 # > 12 cycles ago

        # Mother commissions wave 1
        initial_ore = mother.ore_silo
        initial_pop = mother.population
        res1 = self.mgr.play_seated_turn(self.kernel, sc_mother)
        self.assertEqual(res1["action"], "COMMISSION_INTERSTELLAR_VESSEL")
        self.assertEqual(mother.diaspora_escrow, 1)
        self.assertEqual(mother.last_diaspora_cycle, 100)
        self.assertLess(mother.ore_silo, initial_ore)
        self.assertEqual(mother.population, initial_pop - 100) # 100 pioneers embarked

        # Process expedition to settle frontier
        expedition = self.mgr._process_diaspora_expedition(self.kernel, sc_mother, mother)
        self.assertIsNotNone(expedition)
        self.assertEqual(expedition["daughter_planet"], frontier.name)
        self.assertEqual(frontier.population, 250)
        self.assertEqual(frontier.owner_id, str(mother.id))
        self.assertEqual(frontier.metropole_id, str(mother.id))
        self.assertIn("INTERSTELLAR_FLIGHT", frontier.technologies)

        # Verify daughter colony mind is seated and awakened
        daughter_sc = self.mgr.minds.get(str(frontier.id))
        self.assertIsNotNone(daughter_sc)
        self.assertTrue(daughter_sc.is_seated)
        self.assertIn("AXIOM_OF_THE_STELLAR_HORIZON", daughter_sc.mythic_memory.inviolable_axioms)

        # Generational cooldown verification: Mother cannot launch in cycle 105 (< 12 cycles)
        self.kernel.cycle_count = 105
        res_cooldown = self.mgr.play_seated_turn(self.kernel, sc_mother)
        self.assertNotEqual(res_cooldown["action"], "COMMISSION_INTERSTELLAR_VESSEL")

        # Multi-wave emergence: At cycle 115 (> 12 cycles), mother launches Wave 2!
        self.kernel.cycle_count = 115
        frontier2 = Planet(id="p-frontier-100", name="Frontier Horizon", sector_id=1, population=0, owner_id=None)
        self.sec.planets.append(frontier2)

        res_wave2 = self.mgr.play_seated_turn(self.kernel, sc_mother)
        self.assertEqual(res_wave2["action"], "COMMISSION_INTERSTELLAR_VESSEL")
        self.assertEqual(mother.diaspora_escrow, 1)


if __name__ == "__main__":
    unittest.main()
