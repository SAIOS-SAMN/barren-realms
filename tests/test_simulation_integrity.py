"""
Regression tests for long-horizon simulation integrity issues surfaced by
simulate_playtest.py: sector roster desync on ship destruction, bonded freight
lost with a destroyed hold, expired contracts clogging manifests, unbounded
contract/hauler growth, unchecked cargo deposits, and surface grid caching.
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.combat import _eject_to_sol
from xylarium.kernel.market import (
    FreightContract, CONTRACT_RETENTION_CYCLES, MAX_TRADE_HAULERS_PER_CAPTAIN,
    PRICE_HISTORY_RETENTION, RESOLUTION_HISTORY_RETENTION,
)
from xylarium.kernel.models import CargoHold
from xylarium.kernel.surface import SurfaceManager


def make_contract(cid: str, courier_id=None, status="OPEN", expiry=10, amount=5) -> FreightContract:
    return FreightContract(
        id=cid, company_ticker="VOSS", issuer_name="Voss", origin_sector=1, origin_name="Sol",
        destination_sector=2, destination_planet_id="p", destination_name="Dest", commodity="ORE",
        amount=amount, payout_credits=100, shares_reward=0, hazard_level="FEDERATION",
        created_cycle=0, expiry_cycle=expiry, accepted_by=courier_id, status=status,
    )


class TestSimulationIntegrity(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=1337)
        self.cap = self.kernel.register_player("integrity", "Integrity Tester")

    def _move_to(self, sector_id: int) -> None:
        self.kernel.sectors[self.cap.sector_id].captains.remove(self.cap.id)
        self.cap.sector_id = sector_id
        self.kernel.sectors[sector_id].captains.append(self.cap.id)

    def test_ejection_keeps_sector_rosters_consistent(self):
        self._move_to(42)
        _eject_to_sol(self.cap, self.kernel)
        self.assertEqual(self.cap.sector_id, 1)
        self.assertIn(self.cap.id, self.kernel.sectors[1].captains)
        self.assertNotIn(self.cap.id, self.kernel.sectors[42].captains)

    def test_ejection_forfeits_bonded_freight(self):
        mm = self.kernel.market_manager
        mm.contracts["FRT-T1"] = make_contract("FRT-T1", self.cap.id, "IN_TRANSIT", expiry=10_000)
        self.cap.active_contracts = ["FRT-T1"]
        _eject_to_sol(self.cap, self.kernel)
        self.assertEqual(self.cap.active_contracts, [])
        self.assertEqual(mm.contracts["FRT-T1"].status, "EXPIRED")

    def test_expired_contract_released_from_manifest_then_pruned(self):
        mm = self.kernel.market_manager
        mm.contracts["FRT-T2"] = make_contract("FRT-T2", self.cap.id, "IN_TRANSIT", expiry=self.kernel.cycle_count)
        self.cap.active_contracts = ["FRT-T2"]
        self.kernel.cycle_count += 1
        mm.tick_market(self.kernel)
        self.assertEqual(mm.contracts["FRT-T2"].status, "EXPIRED")
        self.assertNotIn("FRT-T2", self.cap.active_contracts)

        self.kernel.cycle_count += CONTRACT_RETENTION_CYCLES + 1
        mm.tick_market(self.kernel)
        self.assertNotIn("FRT-T2", mm.contracts)

    def test_trade_hauler_fleet_is_capped(self):
        mm = self.kernel.market_manager
        self.cap.credits = 10_000_000
        results = [mm.commission_trade_hauler(self.cap, kernel=self.kernel)[0]
                   for _ in range(MAX_TRADE_HAULERS_PER_CAPTAIN + 3)]
        owned = sum(1 for h in mm.trade_haulers.values() if h.owner_id == self.cap.id)
        self.assertLessEqual(owned, MAX_TRADE_HAULERS_PER_CAPTAIN)
        self.assertFalse(results[-1])

    def test_market_histories_are_bounded(self):
        mm = self.kernel.market_manager
        comp = next(iter(mm.companies.values()))
        comp.price_history.extend(range(PRICE_HISTORY_RETENTION * 3))
        mm.trade_council.resolution_history.extend(f"bill {i}" for i in range(RESOLUTION_HISTORY_RETENTION * 3))
        mm.tick_market(self.kernel)
        self.assertLessEqual(len(comp.price_history), PRICE_HISTORY_RETENTION + 5)
        self.assertLessEqual(len(mm.trade_council.resolution_history), RESOLUTION_HISTORY_RETENTION + 5)

    def test_cargo_stow_never_exceeds_capacity(self):
        hold = CargoHold(capacity=10)
        stowed = hold.stow("ORE", 1000)
        self.assertGreater(stowed, 0)
        self.assertLessEqual(hold.holds_used, hold.capacity + 1e-6)
        self.assertEqual(hold.stow("H2O", 50), 0)

    def test_surface_grid_cache_invalidates_on_write_back(self):
        planet = next(p for s in self.kernel.sectors.values() for p in s.planets)
        grid = SurfaceManager.ensure_surface_grid(planet)
        self.assertIs(SurfaceManager.ensure_surface_grid(planet), grid)
        planet.surface_grid = grid.to_dict()
        self.assertIsNot(SurfaceManager.ensure_surface_grid(planet), grid)


if __name__ == "__main__":
    unittest.main()
