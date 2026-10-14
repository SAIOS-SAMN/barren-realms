"""
tests/test_emergent_economy.py

Comprehensive test suite for:
Emergent Civilizational Economics & Multi-Planetary Realm Uplink Engine.
"""

import os
import tempfile
import unittest

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Planet
from xylarium.kernel.emergent_economy import EmergentEconomyManager, MonetaryTier, EconomicMetabolism
from xylarium.client.renderer import TerminalRenderer
from xylarium.persistence.store import StatePersistence


class TestEmergentEconomy(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=8888)
        self.captain_id = "cap_econ"
        self.kernel.register_player(self.captain_id, "Trader Thorne")
        self.captain = self.kernel.get_player(self.captain_id)
        self.captain.turns = 300
        self.captain.credits = 500000
        self.mgr = self.kernel.emergent_economy_manager

        # Ensure captain has cargo for barter tests
        self.captain.ship.cargo.equipment = 20
        self.captain.ship.cargo.organics = 10

        # Create/find a test world
        self.sec = self.kernel.sectors[self.captain.sector_id]
        if not self.sec.planets:
            self.sec.planets.append(
                Planet(id=f"P-{self.sec.id}-1", name="Verdant Cradle", sector_id=self.sec.id, population=2000)
            )
        self.planet = self.sec.planets[0]

    def test_ensure_economy_and_monetary_tier(self):
        econ = self.mgr.ensure_economy(self.kernel, self.planet)
        self.assertIsNotNone(econ)
        self.assertEqual(econ.planet_id, str(self.planet.id))
        self.assertIn("ORGANICS", econ.barter_inventory)

    def test_barter_exchange(self):
        econ = self.mgr.ensure_economy(self.kernel, self.planet)
        initial_organics = self.captain.ship.cargo.organics
        initial_equipment = self.captain.ship.cargo.equipment
        planet_organics = econ.barter_inventory["ORGANICS"]

        # Barter 5 equipment for organics
        res = self.kernel.dispatch(
            self.captain_id,
            ActionType.EMERGENT_BARTER_EXCHANGE,
            planet_id=str(self.planet.id),
            offered_good="EQUIPMENT",
            offered_qty=5,
            requested_good="ORGANICS",
        )
        self.assertTrue(res.success)
        self.assertEqual(self.captain.ship.cargo.equipment, initial_equipment - 5)
        self.assertGreater(self.captain.ship.cargo.organics, initial_organics)
        self.assertLess(econ.barter_inventory["ORGANICS"], planet_organics)

    def test_nurture_builder_metabolism(self):
        econ = self.mgr.ensure_economy(self.kernel, self.planet)
        initial_hab = self.planet.habitability

        res = self.kernel.dispatch(
            self.captain_id,
            ActionType.EMERGENT_NURTURE_BUILDER,
            planet_id=str(self.planet.id),
            investment_credits=50000,
        )
        self.assertTrue(res.success)
        self.assertEqual(econ.metabolism, EconomicMetabolism.BUILDER)
        self.assertGreaterEqual(econ.reinvestment_rate, 0.6)
        self.assertGreater(self.planet.habitability, initial_hab)

    def test_extract_resources_dark_deed(self):
        econ = self.mgr.ensure_economy(self.kernel, self.planet)
        initial_hab = self.planet.habitability
        initial_credits = self.captain.credits

        res = self.kernel.dispatch(
            self.captain_id,
            ActionType.EMERGENT_EXTRACT_RESOURCES,
            planet_id=str(self.planet.id),
        )
        self.assertTrue(res.success)
        self.assertEqual(econ.metabolism, EconomicMetabolism.EXTRACTOR)
        self.assertGreater(econ.ecological_strain, 0.0)
        self.assertLess(self.planet.habitability, initial_hab)
        # Verify looted value
        self.assertGreater(self.captain.credits, initial_credits)

    def test_trigger_realm_uplink(self):
        # Configure world at domestic fiat stage, ready for realm uplink
        self.planet.population = 15000
        econ = self.mgr.ensure_economy(self.kernel, self.planet)
        econ.is_uplinked = False
        econ.monetary_tier = MonetaryTier.PLANETARY_FIAT

        res = self.kernel.dispatch(
            self.captain_id,
            ActionType.EMERGENT_TRIGGER_UPLINK,
            planet_id=str(self.planet.id),
        )
        self.assertTrue(res.success)
        self.assertTrue(econ.is_uplinked)
        self.assertEqual(econ.monetary_tier, MonetaryTier.INTERSTELLAR_UPLINK)
        self.assertIsNotNone(econ.local_currency_code)
        self.assertGreater(self.planet.treasury, 0)
        self.assertGreaterEqual(econ.trade_routes_count, 1)

    def test_simulation_tick_evolution(self):
        econ = self.mgr.ensure_economy(self.kernel, self.planet)
        econ.metabolism = EconomicMetabolism.BUILDER
        econ.ecological_strain = 10.0

        # Tick simulation
        self.mgr.tick(self.kernel)
        self.assertLess(econ.ecological_strain, 10.0)

    def test_persistence_save_load(self):
        econ = self.mgr.ensure_economy(self.kernel, self.planet)
        econ.metabolism = EconomicMetabolism.BUILDER
        econ.reinvestment_rate = 0.85
        econ.is_uplinked = True
        econ.monetary_tier = MonetaryTier.INTERSTELLAR_UPLINK

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "emergent_economy_save.json")
            saved = StatePersistence.save_to_file(self.kernel, save_path)
            self.assertTrue(saved)

            loaded = StatePersistence.load_from_file(save_path)
            self.assertIsNotNone(loaded)
            self.assertTrue(hasattr(loaded, "emergent_economy_manager"))
            loaded_econ = loaded.emergent_economy_manager.economies.get(str(self.planet.id))
            self.assertIsNotNone(loaded_econ)
            self.assertEqual(loaded_econ.metabolism, EconomicMetabolism.BUILDER)
            self.assertEqual(loaded_econ.monetary_tier, MonetaryTier.INTERSTELLAR_UPLINK)
            self.assertTrue(loaded_econ.is_uplinked)

    def test_renderer_screen(self):
        self.mgr.ensure_economy(self.kernel, self.planet)
        view = self.kernel.get_player_view(self.captain_id)
        rendered = TerminalRenderer.render_emergent_economy_screen(view)
        self.assertIn("EMERGENT CIVILIZATIONAL ECONOMICS & REALM UPLINK", rendered)
        self.assertIn("MONETARY EVOLUTION LADDER", rendered)
        self.assertIn(self.planet.name, rendered)


if __name__ == "__main__":
    unittest.main()
