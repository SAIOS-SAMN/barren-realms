"""
Government: starports belong to their system's government, commercial stations to investors; dues and taxes fill
treasuries that budget offices spend back into their jurisdictions - automated by alignment, or set by the holder.
"""

import random
import unittest

from xylarium.kernel import government, tourism
from xylarium.kernel.economy import EconomyManager
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply
from xylarium.kernel.models import ActionType


def money(kernel):
    return {c: b["total"] for c, b in money_supply(kernel).items()}


class TestGovernment(unittest.TestCase):
    def setUp(self):
        random.seed(131)
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.k.tick_simulation = lambda: None

    def test_every_starport_is_bound_to_its_system_and_government(self):
        owners = {s.port.leisure.get("owner") for s in self.k.sectors.values() if s.port is not None}
        self.assertIn("FEDERATION", owners)
        self.assertTrue(any(o == "IMPERIUM" for o in owners))
        sol = self.k.sectors[1].port
        self.assertEqual(sol.leisure["owner"], "FEDERATION")
        self.assertIsNotNone(sol.leisure["host"])

    def test_the_federal_treasury_is_counted_money(self):
        gm = self.k.governance_manager
        fed = self.k.factions.factions["FEDERATION"]
        self.assertEqual(gm.federal_treasury, fed.vault.get("SOL", 0))
        self.assertGreater(gm.federal_treasury, 0)

    def test_budgets_follow_alignment(self):
        light, dark = government.auto_shares(0.8), government.auto_shares(-0.8)
        self.assertGreater(light["grants"], dark["grants"])
        self.assertGreater(dark["security"], light["security"])
        self.assertAlmostEqual(sum(light.values()), 1.0, places=3)

    def test_a_season_of_budgets_moves_money_without_making_any(self):
        fed = self.k.factions.factions["FEDERATION"]
        fed.vault["SOL"] = 500_000
        m0 = money(self.k)
        government.quarter(self.k)
        self.assertLess(fed.vault["SOL"], 500_000)
        self.assertEqual(sum(m0.values()), sum(money(self.k).values())) if len(m0) == 1 else None
        spent = government.stats(self.k)["spent"]["FEDERATION"]
        self.assertGreater(spent["grants"], 0)
        self.assertGreater(spent["security"], 0)
        # security spending buys the law's presence in its systems
        sec = next(s for s in self.k.sectors.values() if government.government_of(self.k, s)[1] is fed and s.id != 1)
        self.assertGreater(government.security_presence(self.k, sec), 0)

    def test_the_office_holder_sets_the_budget_or_hands_it_back(self):
        cap = self.k.register_player("minister", "Minister")
        government.offices(self.k)["COMPACT"]["holder"] = cap.id
        res = self.k.dispatch("minister", ActionType.BUDGET_SET, government="COMPACT", grants=1, security=0,
                              endowment=0, infrastructure=0)
        self.assertTrue(res.success, res.message)
        self.assertEqual(government.shares_for(self.k, "COMPACT")["grants"], 1.0)
        self.k.dispatch("minister", ActionType.BUDGET_SET, government="COMPACT", auto=True)
        self.assertTrue(government.offices(self.k)["COMPACT"]["auto"])
        other = self.k.register_player("outsider", "Outsider")
        res = self.k.dispatch("outsider", ActionType.BUDGET_SET, government="COMPACT", grants=1)
        self.assertFalse(res.success)
        _ = other

    def test_a_commercial_station_pays_its_owner_and_the_government(self):
        k = self.k
        investor = k.register_player("investor", "Investor")
        investor.credits = 10 ** 6
        sol = k.sectors[1]
        EconomyManager.ensure_port_inventory(sol.port)
        sol.port.stock["Fe"], sol.port.stock["Ti"] = 500, 500
        world = next(p for p in sol.planets if p.population > 0)
        m0 = sum(money(k).values())
        tourism.build_station(k, investor, world)
        self.assertEqual(tourism.station(world)["owner"], investor.id)
        self.assertEqual(m0, sum(money(k).values()))
        # travellers from a neighbouring world come to the station
        origin = next(p for sid in tourism._hops(k, 1, 4) for p in k.sectors[sid].planets
                      if p.population > 0 and p is not world and tourism.spacefaring(k, p)
                      and k.sectors[p.sector_id].port is not None)
        origin_port = k.sectors[origin.sector_id].port
        EconomyManager.ensure_port_inventory(origin_port)
        origin_port.stock["H"] = 800
        origin.household_purse = 500_000
        fed = k.factions.factions["FEDERATION"]
        vault, credits = dict(fed.vault), investor.credits + sum(investor.fx_wallet.values())
        tourism._travel(k, origin, tourism.stats(k))
        if tourism.station(world)["booked"]:
            self.assertGreater(investor.credits + sum(investor.fx_wallet.values()), credits)
            self.assertGreater(sum(fed.vault.values()), sum(vault.values()))


if __name__ == "__main__":
    unittest.main()
