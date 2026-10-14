"""
tests/test_precursor_decoherence.py

Unit and integration tests for:
1. Directed percolation & smooth scale-height equations in settling.py.
2. Correlated catastrophe hazard scaling in annals.py.
3. Precursor deep-core excavations in archaeology.py and live action dispatch.
4. ColonialDecoherenceManager imperial horizon mechanics & stabilization.
5. Save/load persistence.
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Planet
from xylarium.kernel.colonial_decoherence import ColonialDecoherenceManager, ColonialDecoherenceRecord
from xylarium.kernel import settling, annals, archaeology
from xylarium.persistence.store import StatePersistence


class TestUniverseEquationsAndDecoherence(unittest.TestCase):

    def setUp(self):
        self.kernel = GameKernel(seed=1337)
        self.player_id = "TEST_CAPTAIN"
        self.kernel.register_player(self.player_id, "Commander Vaelen")
        self.captain = self.kernel.get_player(self.player_id)
        self.captain.turns = 500
        self.captain.credits = 100000
        self.captain.ship.cargo.equipment = 50

    def test_directed_percolation_and_smooth_scale_height(self):
        """Verify upgraded front_speed directed percolation and smooth _cut_fraction."""
        home = self.kernel.sectors[1].planets[0]
        # Front speed should return positive velocity bounded by C
        v = settling.front_speed(self.kernel, home, hop=0.01, gens_per_gyr=100.0)
        self.assertGreater(v, 0.0)
        self.assertLessEqual(v, settling.C_KPC_PER_GYR)

        # Smooth scale height cut fraction
        f_sub = settling._cut_fraction(0.1, 0.2)
        f_trans = settling._cut_fraction(0.25, 0.3)
        f_supra = settling._cut_fraction(0.5, 0.8)
        self.assertTrue(0.0 <= f_sub <= 1.0)
        self.assertTrue(0.0 <= f_trans <= 1.0)
        self.assertTrue(0.0 <= f_supra <= 1.0)

    def test_correlated_hazard_scaling(self):
        """Verify annals._dominion_hazard applies correlated hazard factor."""
        cap_fn = lambda t: 10.0
        # Single world vs multi-world
        h_single, _ = annals._dominion_hazard(rate=1.0, w0=1.0, gens=10.0, cap_of=cap_fn, g=0.0)
        h_multi, _ = annals._dominion_hazard(rate=1.0, w0=10.0, gens=10.0, cap_of=cap_fn, g=0.0)
        self.assertGreater(h_single, h_multi)
        # Because of correlated hazard w**0.85, 10 worlds shouldn't reduce hazard by full 10x
        ratio = h_single / h_multi
        self.assertLess(ratio, 10.0)
        self.assertGreater(ratio, 1.0)

    def test_precursor_excavation_live_action(self):
        """Verify excavating precursor ruins yields high-tier relics and spends equipment."""
        # Find or seed a planet with ruins
        target_planet = None
        for s in self.kernel.sectors.values():
            for p in getattr(s, "planets", []):
                if getattr(p, "ruins", None):
                    target_planet = p
                    break
            if target_planet:
                break
        
        if not target_planet:
            target_planet = self.kernel.sectors[1].planets[0]
            target_planet.ruins = {
                "culture": "Aelari Precursors",
                "era": "ANCIENT",
                "tech_level": 5,
                "stability": 0.9,
                "elements": ["TITANIUM", "PLATINUM"],
                "dug_depth": 0
            }

        # Move captain to planet's sector
        self.captain.sector_id = target_planet.sector_id
        equip_before = self.captain.ship.cargo.equipment

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.EXCAVATE_PRECURSOR,
            planet_id=target_planet.id,
        )
        self.assertTrue(res.success)
        self.assertEqual(self.captain.ship.cargo.equipment, equip_before - 5)
        self.assertIn("relic", res.data)
        self.assertGreater(len(self.captain.relics), 0)

    def test_colonial_decoherence_and_stabilization(self):
        """Verify colonial decoherence assessment, drift, and stabilization."""
        # Claim a planet in a distant sector
        distant_sec = self.kernel.sectors[42]
        if not distant_sec.planets:
            from xylarium.kernel.models import Planet
            distant_sec.planets.append(Planet(id="P-TEST-42", name="Nova Thule", sector_id=42, planet_type="Terran"))
        colony = distant_sec.planets[0]
        colony.owner_id = self.player_id
        colony.citadel_level = 1

        rec = self.kernel.decoherence_manager.assess_world(self.kernel, colony)
        self.assertIsNotNone(rec)
        self.assertGreater(rec.distance_hops, 0)

        # Move captain to colony sector to stabilize
        self.captain.sector_id = colony.sector_id
        rec.decoherence_index = 0.60
        rec.unrest = 55.0

        # Stabilize via RELAY
        res_relay = self.kernel.dispatch(
            self.player_id,
            ActionType.STABILIZE_DECOHERENCE,
            planet_id=colony.id,
            method="RELAY",
        )
        self.assertTrue(res_relay.success)
        self.assertLess(rec.decoherence_index, 0.60)

        # Stabilize via ENVOY
        res_envoy = self.kernel.dispatch(
            self.player_id,
            ActionType.STABILIZE_DECOHERENCE,
            planet_id=colony.id,
            method="ENVOY",
        )
        self.assertTrue(res_envoy.success)

        # Stabilize via PRECURSOR_CORE
        self.captain.relics = ["Precursor Coherence Engine Shard"]
        res_core = self.kernel.dispatch(
            self.player_id,
            ActionType.STABILIZE_DECOHERENCE,
            planet_id=colony.id,
            method="PRECURSOR_CORE",
        )
        self.assertTrue(res_core.success)
        self.assertEqual(rec.decoherence_index, 0.0)
        self.assertEqual(rec.status, "STABLE")

    def test_persistence_roundtrip(self):
        """Verify decoherence manager serializes and deserializes accurately."""
        p = self.kernel.sectors[1].planets[0]
        p.owner_id = self.player_id
        self.kernel.decoherence_manager.assess_world(self.kernel, p)

        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_save.json")
            saved = StatePersistence.save_to_file(self.kernel, filepath)
            self.assertTrue(saved)

            loaded_kernel = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(loaded_kernel)
            self.assertTrue(hasattr(loaded_kernel, "decoherence_manager"))
            self.assertIn(p.id, loaded_kernel.decoherence_manager.records)


if __name__ == "__main__":
    unittest.main()
