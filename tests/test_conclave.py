"""
tests/test_conclave.py

Comprehensive test suite for Project Landing 3:
Pan-Galactic Conclave & Interstellar Law.
"""

import unittest
from unittest.mock import MagicMock
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, AIPersonality
from xylarium.kernel.conclave import PanGalacticConclaveManager, ConclaveResolution, STANDARD_RESOLUTIONS
from xylarium.client.renderer import TerminalRenderer
from xylarium.persistence.store import StatePersistence


class TestPanGalacticConclave(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.captain_id = "cap_player"
        self.kernel.register_player(self.captain_id, "Speaker Valerius")
        self.captain = self.kernel.get_player(self.captain_id)
        self.captain.turns = 300
        self.mgr = self.kernel.conclave_manager

    def test_calculate_voting_weight(self):
        # Base weight starts at 10
        base_weight = self.mgr.calculate_voting_weight(self.kernel, self.captain_id)
        self.assertGreaterEqual(base_weight, 10)

        # Increase credits and fighters
        self.captain.credits += 250000  # +5 votes
        self.captain.ship.fighters += 50  # +5 votes
        boosted_weight = self.mgr.calculate_voting_weight(self.kernel, self.captain_id)
        self.assertEqual(boosted_weight, base_weight + 10)

    def test_sponsor_resolution(self):
        # Invalid key fails
        res_fail = self.kernel.dispatch(
            self.captain_id,
            ActionType.CONCLAVE_SPONSOR_RESOLUTION,
            resolution_key="RES_DOOMSDAY_MADNESS",
        )
        self.assertFalse(res_fail.success)

        # Valid sponsorship
        res_ok = self.kernel.dispatch(
            self.captain_id,
            ActionType.CONCLAVE_SPONSOR_RESOLUTION,
            resolution_key="RES_SYNTROPIC_CONCORDAT",
        )
        self.assertTrue(res_ok.success)
        self.assertEqual(len(self.mgr.proposals), 1)

        prop = list(self.mgr.proposals.values())[0]
        self.assertEqual(prop.key, "RES_SYNTROPIC_CONCORDAT")
        self.assertGreater(prop.votes_for, 0)
        self.assertGreaterEqual(prop.votes_against, 0)

    def test_vote_and_passage_effect(self):
        # Sponsor resolution
        self.kernel.dispatch(
            self.captain_id,
            ActionType.CONCLAVE_SPONSOR_RESOLUTION,
            resolution_key="RES_SYNTROPIC_CONCORDAT",
        )
        prop_id = list(self.mgr.proposals.keys())[0]

        # Give captain enough weight to pass in one vote
        self.captain.credits += 5000000  # 100 extra votes
        vote_res = self.kernel.dispatch(
            self.captain_id,
            ActionType.CONCLAVE_CAST_VOTE,
            resolution_id=prop_id,
            in_favor=True,
        )
        self.assertTrue(vote_res.success)
        self.assertIn("HAS PASSED", vote_res.message)

        # Ensure law is active and removed from proposals
        self.assertIn("RES_SYNTROPIC_CONCORDAT", self.mgr.active_laws)
        self.assertNotIn(prop_id, self.mgr.proposals)

    def test_sanctuary_worlds_effect(self):
        # Seed a clade first
        sec = self.kernel.sectors[self.captain.sector_id]
        if not sec.planets:
            from xylarium.kernel.models import Planet
            sec.planets.append(Planet(id=999, name="Verdant IV", sector_id=sec.id, planet_type="EARTH"))
        planet = sec.planets[0]

        clade = self.kernel.clade_nursery_manager.register_seeded_clade(
            kernel=self.kernel,
            progenitor_id=self.captain_id,
            planet=planet,
            clade_name="Aurelians",
        )
        clade.reverence_pct = 50.0
        initial_rev = clade.reverence_pct

        # Directly enact Sanctuary Worlds Act
        res = ConclaveResolution(
            id="RES-099",
            key="RES_SANCTUARY_WORLDS",
            name="The Sanctuary Worlds Act",
            description="Grants extraterritorial legal protection to nascent nursery worlds.",
            sponsor_id=self.captain_id,
        )
        self.mgr._apply_passed_law_effect(self.kernel, res)
        self.assertEqual(clade.reverence_pct, initial_rev + 20.0)

    def test_anti_piracy_effect(self):
        # Find or create a pirate captain
        pirate = None
        for c in self.kernel.captains.values():
            if getattr(c, "personality", None) and c.personality == AIPersonality.PIRATE:
                pirate = c
                break
        if not pirate:
            from xylarium.kernel.models import Captain, Ship
            pirate = Captain(
                id="cap_pirate_test",
                name="Blackbeard Corsair",
                sector_id=1,
                credits=1000,
                ship=Ship(name="Raider"),
                personality=AIPersonality.PIRATE,
                bounty=10000,
            )
            self.kernel.captains[pirate.id] = pirate

        old_bounty = pirate.bounty
        res = ConclaveResolution(
            id="RES-098",
            key="RES_ANTI_PIRACY",
            name="Galactic Anti-Piracy Mobilization",
            description="Deploys joint hegemony patrols; doubles bounties.",
            sponsor_id=self.captain_id,
        )
        self.mgr._apply_passed_law_effect(self.kernel, res)
        self.assertEqual(pirate.bounty, int(old_bounty * 2.0) + 5000)

    def test_enforce_sanctions(self):
        rival_id = "cap_pirate" if "cap_pirate" in self.kernel.captains else list(self.kernel.captains.keys())[1]
        rival = self.kernel.captains[rival_id]
        initial_rating = rival.credit_rating

        sanc_res = self.kernel.dispatch(
            self.captain_id,
            ActionType.CONCLAVE_ENFORCE_SANCTIONS,
            target_captain_id=rival_id,
        )
        self.assertTrue(sanc_res.success)
        self.assertIn(self.captain_id, rival.embargoed_by)
        self.assertEqual(rival.credit_rating, max(100, initial_rating - 75))

    def test_serialization_and_persistence(self):
        import tempfile
        import os

        # Add a law and a proposal
        self.mgr.active_laws["RES_FREE_NAVIGATION"] = ConclaveResolution(
            id="RES-001",
            key="RES_FREE_NAVIGATION",
            name="Free Navigation Accords",
            description="Test accords",
            sponsor_id="cap_player",
            status="PASSED",
        )
        self.mgr.proposals["RES-002"] = ConclaveResolution(
            id="RES-002",
            key="RES_ANTI_PIRACY",
            name="Anti-Piracy",
            description="Test anti piracy",
            sponsor_id="cap_trader",
            votes_for=30,
            votes_against=15,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "conclave_save.json")
            saved = StatePersistence.save_to_file(self.kernel, path)
            self.assertTrue(saved)

            loaded = StatePersistence.load_from_file(path)
            self.assertIsNotNone(loaded)
            self.assertTrue(hasattr(loaded, "conclave_manager"))
            self.assertIn("RES_FREE_NAVIGATION", loaded.conclave_manager.active_laws)
            self.assertIn("RES-002", loaded.conclave_manager.proposals)
            self.assertEqual(loaded.conclave_manager.proposals["RES-002"].votes_for, 30)

    def test_renderer_output(self):
        self.mgr.active_laws["RES_FREE_NAVIGATION"] = ConclaveResolution(
            id="RES-001",
            key="RES_FREE_NAVIGATION",
            name="Free Navigation Accords",
            description="Standardizes trade lanes and prohibits predatory tolls.",
            sponsor_id="cap_player",
            status="PASSED",
            passed_cycle=5,
        )
        view = self.kernel.get_player_view(self.captain_id)
        rendered = TerminalRenderer.render_conclave_screen(view)
        self.assertIn("PAN-GALACTIC CONCLAVE & INTERSTELLAR LAW", rendered)
        self.assertIn("Free Navigation Accords", rendered)
        self.assertIn("Your Parliamentary Voting Weight", rendered)


if __name__ == "__main__":
    unittest.main()
