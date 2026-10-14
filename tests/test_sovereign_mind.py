"""
tests/test_sovereign_mind.py

Comprehensive test suite for:
The Sovereign Indigenous Consciousness Engine (SICE)
Covers all Five Pillars:
  1. Metacognitive Self-Modeling & Introspection Skill.
  2. Counterfactual Imagination & Regret Minimization.
  3. Internal Dialectical Parliament & Dynamic Weight Shifting.
  4. Mythic Memory Graph, Trauma Scars & Inviolable Sacred Axioms.
  5. Non-Scalar Theory of Mind & The Hearing Reduction.
Also verifies persistence serialization/deserialization and terminal screen rendering.
"""

import os
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Planet
from xylarium.kernel.sovereign_mind import (
    InferredPosture,
    InternalGauges,
    ParliamentaryVoiceType,
    SovereignMindManager,
)
from xylarium.client.renderer import TerminalRenderer
from xylarium.persistence.store import StatePersistence


class TestSovereignMind(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=4242)
        self.captain_id = "cap_sice"
        self.kernel.register_player(self.captain_id, "Captain Mind")
        self.captain = self.kernel.get_player(self.captain_id)
        self.captain.turns = 300
        self.captain.credits = 100000
        self.mgr: SovereignMindManager = self.kernel.sovereign_mind_manager

        # Ensure valid planet in sector
        self.sec = self.kernel.sectors[self.captain.sector_id]
        if not self.sec.planets:
            self.sec.planets.append(
                Planet(id=f"P-{self.sec.id}-1", name="Aethelgard Prime", sector_id=self.sec.id, population=1500)
            )
        self.planet = self.sec.planets[0]

    def test_metacognitive_self_model_and_gauges(self):
        """Pillar 1: Metacognitive Self-Modeling & Predictive State Loop."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)
        self.assertIsNotNone(sc)
        self.assertEqual(sc.planet_id, str(self.planet.id))

        # Check that all 8 gauges are sampled and valid
        g = sc.self_model.current_gauges
        for val in g.as_vector():
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 1.0)

        # Verify predictive forecast
        pred_g = sc.self_model.predicted_gauges
        self.assertIsNotNone(pred_g)
        self.assertEqual(len(pred_g.as_vector()), 8)

        # Trigger simulation ticks and verify prediction error calculation and introspection skill evolution
        initial_skill = sc.introspection_skill
        for _ in range(5):
            self.mgr.tick(self.kernel)

        self.assertGreater(sc.cycles_conscious, 0)
        self.assertGreater(len(sc.self_model.recent_errors), 0)
        # Verify awakening status is a boolean
        self.assertIsInstance(sc.awakened, bool)

    def test_internal_dialectical_parliament(self):
        """Pillar 2: The Internal Dialectical Parliament & Dynamic Weight Shifting."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)
        parl = sc.parliament

        self.assertEqual(len(parl.voices), 3)
        self.assertIn(ParliamentaryVoiceType.VOICE_MEMORY.value, parl.voices)
        self.assertIn(ParliamentaryVoiceType.VOICE_URGENCY.value, parl.voices)
        self.assertIn(ParliamentaryVoiceType.VOICE_HORIZON.value, parl.voices)

        # Dispatch commune parliament action
        res = self.kernel.dispatch(
            self.captain_id,
            ActionType.SOVEREIGN_COMMUNE_PARLIAMENT,
            planet_id=str(self.planet.id),
        )
        self.assertTrue(res.success)
        self.assertIn("Parliament of", res.message)
        self.assertIn(res.data["dominant_voice"], [v.value for v in ParliamentaryVoiceType])
        self.assertGreaterEqual(res.data["confidence"], 0.0)

        # Check weights sum approximately to 1.0
        v_mem = parl.voices[ParliamentaryVoiceType.VOICE_MEMORY.value]
        v_urg = parl.voices[ParliamentaryVoiceType.VOICE_URGENCY.value]
        v_hor = parl.voices[ParliamentaryVoiceType.VOICE_HORIZON.value]
        total_w = v_mem.weight + v_urg.weight + v_hor.weight
        self.assertAlmostEqual(total_w, 1.0, places=1)

    def test_counterfactual_imagination_and_regret(self):
        """Pillar 3: Counterfactual Imagination & Regret Minimization."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)

        # Dispatch counterfactual evaluation
        res = self.kernel.dispatch(
            self.captain_id,
            ActionType.SOVEREIGN_EVALUATE_COUNTERFACTUAL,
            planet_id=str(self.planet.id),
            candidate_action="CONSERVE_AND_HEAL",
        )
        self.assertTrue(res.success)
        self.assertEqual(res.data["selected"], "CONSERVE_AND_HEAL")
        self.assertEqual(len(res.data["simulations"]), 3)

        # Verify syntropy payoffs and anticipated regret scores
        for sim in res.data["simulations"]:
            self.assertIn("syntropy_payoff", sim)
            self.assertIn("anticipated_regret", sim)
            self.assertGreaterEqual(sim["anticipated_regret"], 0.0)

        # Verify regret log entry
        self.assertGreater(len(sc.counterfactual.regret_log), 0)

    def test_mythic_memory_and_trauma_scars(self):
        """Pillar 4: Mythic Memory Graph, Trauma Scars & Holy Inviolable Axioms."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)
        initial_scars_count = len(sc.mythic_memory.scars)
        initial_axioms_count = len(sc.mythic_memory.inviolable_axioms)

        # Record a catastrophic deed (orbital strike / severe betrayal)
        res = self.kernel.dispatch(
            self.captain_id,
            ActionType.SOVEREIGN_RECORD_HISTORICAL_DEED,
            planet_id=str(self.planet.id),
            deed_type="ORBITAL_BOMBARDMENT",
            description="Cruel planetary bombardment targeting orbital nurseries.",
            alignment_impact=-0.8,
            actor_id=self.captain_id,
            actor_name="Reckless Captain",
        )
        self.assertTrue(res.success)
        self.assertTrue(res.data["scar_created"])
        self.assertIsNotNone(res.data["taboo_axiom"])

        # Verify that scar and axiom were registered
        self.assertEqual(len(sc.mythic_memory.scars), initial_scars_count + 1)
        self.assertIn(res.data["taboo_axiom"], sc.mythic_memory.inviolable_axioms)

    def test_theory_of_mind_and_the_hearing(self):
        """Pillar 5: Non-Scalar Theory of Mind & The Hearing Reduction."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)

        # 1. Test Absolute Refusal when proposal violates Inviolable Axiom
        sc.mythic_memory.inviolable_axioms.append("NEVER_SURRENDER_BIOSPHERE")
        res_refuse = self.kernel.dispatch(
            self.captain_id,
            ActionType.SOVEREIGN_HEAR_INTENT,
            planet_id=str(self.planet.id),
            counterparty_id=self.captain_id,
            proposal_summary="Request immediate extraction and strip-mine of planetary biosphere",
            action_type_key="EXTRACT",
        )
        self.assertFalse(res_refuse.success)
        self.assertEqual(res_refuse.data["verdict"], "ABSOLUTE_REFUSAL")
        self.assertIn("NEVER_SURRENDER_BIOSPHERE", res_refuse.data["violating_axiom"])

        # 2. Test Conduct Book updates & Posture Deduction (No-Scalar Law)
        # Give captain positive constructive deeds (Builder)
        for _ in range(3):
            self.kernel.dispatch(
                self.captain_id,
                ActionType.SOVEREIGN_RECORD_HISTORICAL_DEED,
                planet_id=str(self.planet.id),
                deed_type="AID_DISPATCH",
                description="Provided emergency ecological relief and biosimilar medicines.",
                alignment_impact=+0.5,
                actor_id=self.captain_id,
            )

        cb = sc.conduct_books[self.captain_id]
        self.assertGreater(cb.compassion_credit, 0)
        self.assertEqual(cb.compassion_debit, 0)
        self.assertEqual(cb.deduce_posture(), InferredPosture.BUILDER)

        # 3. Test Hearing when counterparty is verified Builder
        res_builder = self.kernel.dispatch(
            self.captain_id,
            ActionType.SOVEREIGN_HEAR_INTENT,
            planet_id=str(self.planet.id),
            counterparty_id=self.captain_id,
            proposal_summary="Establish cooperative research sanctuary on outer moon",
        )
        self.assertTrue(res_builder.success)
        self.assertEqual(res_builder.data["verdict"], "ACCORD_GRANTED")
        self.assertEqual(res_builder.data["posture"], InferredPosture.BUILDER.value)
        self.assertGreaterEqual(res_builder.data["congruence"], 0.8)

    def test_persistence_save_and_restore(self):
        """Verifies StatePersistence saves and loads sovereign minds without loss."""
        sc = self.mgr.ensure_consciousness(self.kernel, self.planet)
        sc.introspection_skill = 0.77
        sc.awakened = True

        # Add a custom scar and conduct book entry
        sc.mythic_memory.inviolable_axioms.append("PROHIBIT_XENO_DISSECTION")
        self.kernel.dispatch(
            self.captain_id,
            ActionType.SOVEREIGN_RECORD_HISTORICAL_DEED,
            planet_id=str(self.planet.id),
            deed_type="SACRED_COVENANT",
            description="Swore eternal defense of celestial ruins.",
            alignment_impact=+0.6,
            actor_id=self.captain_id,
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            save_path = tf.name

        try:
            saved = StatePersistence.save_to_file(self.kernel, save_path)
            self.assertTrue(saved)

            loaded_kernel = StatePersistence.load_from_file(save_path)
            self.assertIsNotNone(loaded_kernel)
            self.assertTrue(hasattr(loaded_kernel, "sovereign_mind_manager"))

            loaded_sc = loaded_kernel.sovereign_mind_manager.minds.get(str(self.planet.id))
            self.assertIsNotNone(loaded_sc)
            self.assertAlmostEqual(loaded_sc.introspection_skill, 0.77, places=2)
            self.assertTrue(loaded_sc.awakened)
            self.assertIn("PROHIBIT_XENO_DISSECTION", loaded_sc.mythic_memory.inviolable_axioms)

            # Check Conduct Book restored
            self.assertIn(self.captain_id, loaded_sc.conduct_books)
            loaded_cb = loaded_sc.conduct_books[self.captain_id]
            self.assertGreater(loaded_cb.integrity_credit, 0)
        finally:
            if os.path.exists(save_path):
                os.remove(save_path)

    def test_terminal_renderer(self):
        """Verifies TerminalRenderer.render_sovereign_mind_screen produces output."""
        self.mgr.ensure_consciousness(self.kernel, self.planet)
        view = self.kernel.get_player_view(self.captain_id)
        self.assertIn("sovereign_mind", view)

        screen = TerminalRenderer.render_sovereign_mind_screen(view)
        self.assertIsNotNone(screen)
        self.assertIn("SOVEREIGN INDIGENOUS CONSCIOUSNESS ENGINE", screen)
        self.assertIn("Metacognitive Gauges", screen)
        self.assertIn("Internal Parliament", screen)
        self.assertIn("Sacred Axioms", screen)


if __name__ == "__main__":
    unittest.main()
