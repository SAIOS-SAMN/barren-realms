"""
tests/test_advanced_sovereign_cognition.py

Comprehensive verification suite for the Advanced Sovereign Cognition Engine (ASCE):
1. Ideation Superposition & Multi-Horizon Mental Rollouts (Pillar 1).
2. Adversarial Theory of Mind & Opponent Doctrine Inversion (Pillar 2).
3. Continuous Gauge-Based Field Physics for Dialectical Synthesis (Pillar 3).
4. Meta-Cognitive Attractor-State Breakout & Singularity Disruption (Pillar 4).
5. Anti-Turtling Verification in Head-to-Head Confrontation.
6. Full Serialization & Persistence Round-Trip Conformance.
"""

import tempfile
import os
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Planet
from xylarium.kernel.sovereign_mind import (
    AdversarialDoctrine,
    IdeationSpace,
    InferredPosture,
    InternalGauges,
    ParliamentaryVoiceType,
    SovereignMindManager,
)
from xylarium.persistence.store import StatePersistence


class TestAdvancedSovereignCognition(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=9999)
        self.captain_id = "cap_asce"
        self.kernel.register_player(self.captain_id, "Captain ASCE")
        self.captain = self.kernel.get_player(self.captain_id)
        self.captain.turns = 200
        self.captain.credits = 50000
        self.mgr: SovereignMindManager = self.kernel.sovereign_mind_manager

        self.sec = self.kernel.sectors[self.captain.sector_id]
        if not self.sec.planets:
            self.sec.planets.append(
                Planet(id=f"P-{self.sec.id}-99", name="Verdant Throneworld", sector_id=self.sec.id, population=800)
            )
        self.planet = self.sec.planets[0]
        self.planet.treasury = 2000
        self.planet.shields = 0
        self.planet.max_shields = 2500

    def test_ideation_space_and_mental_rollouts(self):
        """Pillar 1: Ideation Superposition & Multi-Horizon Mental Rollouts."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)
        self.assertIsNotNone(sc.ideation_space)
        ideations = sc.ideation_space.ideations
        self.assertEqual(len(ideations), 5)
        self.assertIn("BIO_GENESIS", ideations)
        self.assertIn("CAPITAL_UPLINK", ideations)
        self.assertIn("CITADEL_HEGEMONY", ideations)
        self.assertIn("COGNITIVE_TRANSCENDENCE", ideations)
        self.assertIn("ASYMMETRIC_DISRUPTION", ideations)

        # Check amplitudes sum to 1.0
        total_amp = sum(i.amplitude for i in ideations.values())
        self.assertAlmostEqual(total_amp, 1.0, places=2)

        # Run mental rollout for CAPITAL_UPLINK
        rollout = self.mgr._simulate_mental_rollout(self.kernel, self.planet, "CAPITAL_UPLINK", horizon=5)
        self.assertEqual(rollout["ideation_id"], "CAPITAL_UPLINK")
        self.assertGreater(rollout["projected_treasury"], self.planet.treasury)
        self.assertGreaterEqual(rollout["syntropy_payoff"], 0.0)

    def test_theory_of_mind_doctrine_classification(self):
        """Pillar 2: Theory of Mind & Adversarial Doctrine Classification."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)
        self.captain.credits = 0
        self.captain.fighters = 0
        self.captain.shields = 0

        # Case A: Rapidly expanding capitalist rival with zero fleet & zero shields
        rival_cap = self.kernel.register_player("cap_capitalist", "Baron Greed")
        rival_cap.credits = 15000

        rival_cap.fighters = 0
        rival_cap.shields = 0
        rival_cap.turns_spent = 50

        doctrine, metrics = self.mgr._observe_and_model_rivals(self.kernel, sc, self.planet)
        self.assertEqual(doctrine, AdversarialDoctrine.EXPLOITATIVE_CAPITALIST.value)
        self.assertGreater(metrics["greed"], 0.6)
        self.assertLess(metrics["paranoia"], 0.2)
        self.assertLess(metrics["aggression"], 0.2)

        # Case B: Defensive Bunker Turtle rival (total assets > 13300 so dominant over default AI warlords)
        rival_cap.credits = 1000
        rival_cap.shields = 10000
        rival_cap.fighters = 0
        doctrine_turtle, metrics_t = self.mgr._observe_and_model_rivals(self.kernel, sc, self.planet)
        self.assertEqual(doctrine_turtle, AdversarialDoctrine.BUNKER_TURTLE.value)
        self.assertGreater(metrics_t["paranoia"], 0.6)

        # Case C: Warmonger Reaver rival
        rival_cap.credits = 1000
        rival_cap.shields = 100
        rival_cap.fighters = 250
        doctrine_reaver, metrics_r = self.mgr._observe_and_model_rivals(self.kernel, sc, self.planet)
        self.assertEqual(doctrine_reaver, AdversarialDoctrine.WARMONGER_REAVER.value)
        self.assertGreater(metrics_r["aggression"], 0.4)


    def test_doctrine_inversion_anti_turtling(self):
        """Pillar 2 & 3: Doctrine Inversion actively breaks turtling against capitalist rivals."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)

        # Register unfortified capitalist rival
        rival = self.kernel.register_player("cap_merchant", "Hyper Capitalist")
        rival.credits = 25000
        rival.fighters = 0
        rival.shields = 0

        # Perform doctrine inversion
        self.mgr._invert_rival_doctrine(sc, AdversarialDoctrine.EXPLOITATIVE_CAPITALIST.value)

        # Verify citadel hegemony amplitude was heavily suppressed
        citadel_amp = sc.ideation_space.ideations["CITADEL_HEGEMONY"].amplitude
        capital_amp = sc.ideation_space.ideations["CAPITAL_UPLINK"].amplitude
        bio_amp = sc.ideation_space.ideations["BIO_GENESIS"].amplitude

        self.assertLess(citadel_amp, 0.15)
        self.assertGreater(capital_amp, citadel_amp)
        self.assertGreater(bio_amp, citadel_amp)

        # Sovereign plays turn: should NOT spend money on shields once minimal baseline is met
        self.planet.shields = 100  # already above minimal safe barrier for capitalist rival
        self.planet.treasury = 1500

        turn_result = self.mgr.play_seated_turn(self.kernel, sc)
        self.assertNotEqual(turn_result["action"], "FORTIFY_SHIELDS")
        self.assertIn(turn_result["action"], ["RESTOCK_AGRI_SILOS", "NURTURE_CLADE", "CIVIC_SUBSIDY", "EXPAND_COMMERCIAL_NODE", "TRIGGER_REALM_UPLINK", "DEEP_SYNTHESIS"])

    def test_gauge_field_lagrangian_barrier_potential(self):
        """Pillar 3: Gauge barrier potential V_urgency repels over-fortification."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)

        # When shields are high and no threat exists
        self.planet.shields = 2000
        self.planet.treasury = 1500
        potentials = self.mgr._evaluate_gauge_action_potentials(
            self.kernel, sc, self.planet, AdversarialDoctrine.EXPLOITATIVE_CAPITALIST.value
        )

        # FORTIFY_SHIELDS should have a heavy positive repulsion penalty (wasting capital)
        self.assertGreater(potentials["FORTIFY_SHIELDS"], 0.0)

        # Economic or demographic compounding actions should have negative potential (strong attractors)
        self.assertLess(potentials["NURTURE_CLADE"], potentials["FORTIFY_SHIELDS"])
        self.assertLess(potentials["RESTOCK_AGRI_SILOS"], potentials["FORTIFY_SHIELDS"])

    def test_attractor_singularity_and_breakout(self):
        """Pillar 4: Attractor-State Breakout & Singularity Disruption."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)

        # Artificially inject identical repeating actions into phase space history
        sc.phase_space.action_history = ["FORTIFY_SHIELDS", "FORTIFY_SHIELDS", "FORTIFY_SHIELDS"]
        sc.phase_space.stagnation_counter = 3
        sc.ideation_space.last_collapsed_ideation = "CITADEL_HEGEMONY"

        self.assertTrue(self.mgr._check_attractor_singularity(sc))

        # Trigger disruption
        self.mgr._trigger_singularity_disruption(self.kernel, sc, self.planet)

        # Verify stagnant ideation suppressed to 0 and orthogonal ideations re-seeded
        self.assertEqual(sc.ideation_space.ideations["CITADEL_HEGEMONY"].amplitude, 0.0)
        self.assertGreater(sc.ideation_space.ideations["CAPITAL_UPLINK"].amplitude, 0.20)
        self.assertTrue(sc.phase_space.singularity_tripped)
        self.assertEqual(sc.phase_space.total_breakouts, 1)

    def test_cognitive_surprise_tensor(self):
        """Pillar 1: Cognitive Surprise Tensor calculation."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)
        pre_state = {"pop": 500, "treasury": 1000, "shields": 0}

        surprise = self.mgr._compute_cognitive_surprise(sc, self.planet, "BIO_GENESIS", pre_state)
        self.assertGreaterEqual(surprise, 0.0)
        self.assertLessEqual(surprise, 1.0)
        self.assertEqual(sc.ideation_space.surprise_tensor, surprise)

    def test_asce_state_persistence_round_trip(self):
        """Full StatePersistence round-trip for all ASCE structures."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)
        sc.ideation_space.last_collapsed_ideation = "CAPITAL_UPLINK"
        sc.adversarial_tracker.inferred_doctrine = AdversarialDoctrine.EXPLOITATIVE_CAPITALIST.value
        sc.phase_space.total_breakouts = 2

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            save_path = tf.name

        try:
            saved = StatePersistence.save_to_file(self.kernel, save_path)
            self.assertTrue(saved)

            loaded = StatePersistence.load_from_file(save_path)
            self.assertIsNotNone(loaded)
            loaded_sc = loaded.sovereign_mind_manager.minds.get(str(self.planet.id))
            self.assertIsNotNone(loaded_sc)
            self.assertEqual(loaded_sc.ideation_space.last_collapsed_ideation, "CAPITAL_UPLINK")
            self.assertEqual(loaded_sc.adversarial_tracker.inferred_doctrine, AdversarialDoctrine.EXPLOITATIVE_CAPITALIST.value)
            self.assertEqual(loaded_sc.phase_space.total_breakouts, 2)
            self.assertEqual(len(loaded_sc.ideation_space.ideations), 5)
        finally:
            if os.path.exists(save_path):
                os.remove(save_path)


if __name__ == "__main__":
    unittest.main()
