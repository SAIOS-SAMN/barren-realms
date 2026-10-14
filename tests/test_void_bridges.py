"""
tests/test_void_bridges.py

Comprehensive test suite for Project Landing 4:
Extragalactic Void Bridges & Multi-Cluster Cosmos.
"""

import os
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType
from xylarium.kernel.void_bridges import VoidBridgeManager, EXTRAGALACTIC_CLUSTERS
from xylarium.client.renderer import TerminalRenderer
from xylarium.persistence.store import StatePersistence


class TestVoidBridges(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=1337)
        self.captain_id = "cap_astronav"
        self.kernel.register_player(self.captain_id, "Navigator Vael")
        self.captain = self.kernel.get_player(self.captain_id)
        self.captain.turns = 300
        self.captain.credits = 2000000
        self.mgr = self.kernel.void_bridge_manager

    def test_cluster_definitions(self):
        self.assertIn("CLUSTER_MAGELLANIC", EXTRAGALACTIC_CLUSTERS)
        self.assertIn("CLUSTER_GLOBULAR", EXTRAGALACTIC_CLUSTERS)
        self.assertIn("CLUSTER_SEYFERT", EXTRAGALACTIC_CLUSTERS)
        self.assertEqual(EXTRAGALACTIC_CLUSTERS["CLUSTER_SEYFERT"]["hazard_type"], "HAWKING_RADIATION")

    def test_commission_bridge_and_cluster_instantiation(self):
        # Commission bridge to Magellanic Stream
        res = self.kernel.dispatch(
            self.captain_id,
            ActionType.VOID_BRIDGE_COMMISSION,
            destination_cluster="CLUSTER_MAGELLANIC",
        )
        self.assertTrue(res.success)
        self.assertEqual(len(self.mgr.bridges), 1)

        bridge = list(self.mgr.bridges.values())[0]
        self.assertEqual(bridge.origin_sector_id, self.captain.sector_id)
        self.assertEqual(bridge.destination_cluster, "CLUSTER_MAGELLANIC")
        self.assertEqual(bridge.target_sector_id, 201)

        # Check sector 201 exists and has warps
        self.assertIn(201, self.kernel.sectors)
        mag_sec = self.kernel.sectors[201]
        self.assertEqual(mag_sec.cluster_name, "The Magellanic Stream")
        self.assertIn(self.captain.sector_id, mag_sec.warps)

    def test_transit_void_bridge(self):
        # Commission bridge to Seyfert Core
        self.kernel.dispatch(
            self.captain_id,
            ActionType.VOID_BRIDGE_COMMISSION,
            destination_cluster="CLUSTER_SEYFERT",
        )
        bridge = list(self.mgr.bridges.values())[0]
        bridge_id = bridge.id
        origin_sec = self.captain.sector_id

        # Transit to Seyfert Core
        self.captain.ship.shields = 100
        transit_res = self.kernel.dispatch(
            self.captain_id,
            ActionType.VOID_BRIDGE_TRANSIT,
            bridge_id=bridge_id,
        )
        self.assertTrue(transit_res.success)
        self.assertEqual(self.captain.sector_id, 401)
        self.assertEqual(bridge.transits_count, 1)
        # Hazard in Seyfert Core should have drained shields
        self.assertLess(self.captain.ship.shields, 100)

        # Transit back
        back_res = self.kernel.dispatch(
            self.captain_id,
            ActionType.VOID_BRIDGE_TRANSIT,
            bridge_id=bridge_id,
        )
        self.assertTrue(back_res.success)
        self.assertEqual(self.captain.sector_id, origin_sec)
        self.assertEqual(bridge.transits_count, 2)

    def test_survey_cluster(self):
        survey_res = self.kernel.dispatch(
            self.captain_id,
            ActionType.VOID_BRIDGE_SURVEY_CLUSTER,
            cluster_id="CLUSTER_GLOBULAR",
        )
        self.assertTrue(survey_res.success)
        self.assertIn("Omega Starburst Core", survey_res.message)
        self.assertIn("sectors", survey_res.data)
        self.assertGreater(survey_res.data["sectors"], 0)

    def test_bridge_maintenance_tick(self):
        self.kernel.dispatch(
            self.captain_id,
            ActionType.VOID_BRIDGE_COMMISSION,
            destination_cluster="CLUSTER_MAGELLANIC",
        )
        bridge = list(self.mgr.bridges.values())[0]
        bridge.coherence_integrity = 90.0

        self.mgr.tick(self.kernel)
        self.assertGreater(bridge.coherence_integrity, 90.0)

    def test_persistence_save_load(self):
        self.kernel.dispatch(
            self.captain_id,
            ActionType.VOID_BRIDGE_COMMISSION,
            destination_cluster="CLUSTER_SEYFERT",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "void_bridge_save.json")
            saved = StatePersistence.save_to_file(self.kernel, save_path)
            self.assertTrue(saved)

            loaded = StatePersistence.load_from_file(save_path)
            self.assertIsNotNone(loaded)
            self.assertTrue(hasattr(loaded, "void_bridge_manager"))
            self.assertEqual(len(loaded.void_bridge_manager.bridges), 1)
            b = list(loaded.void_bridge_manager.bridges.values())[0]
            self.assertEqual(b.destination_cluster, "CLUSTER_SEYFERT")
            self.assertIn(401, loaded.sectors)

    def test_renderer_screen(self):
        self.kernel.dispatch(
            self.captain_id,
            ActionType.VOID_BRIDGE_COMMISSION,
            destination_cluster="CLUSTER_MAGELLANIC",
        )
        view = self.kernel.get_player_view(self.captain_id)
        rendered = TerminalRenderer.render_void_bridges_screen(view)
        self.assertIn("EXTRAGALACTIC VOID BRIDGES & MULTI-CLUSTER COSMOS", rendered)
        self.assertIn("The Magellanic Stream", rendered)
        self.assertIn("Omega Starburst Core", rendered)
        self.assertIn("The Seyfert Active Core", rendered)


if __name__ == "__main__":
    unittest.main()
