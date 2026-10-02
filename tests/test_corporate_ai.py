"""
Unit test suite for Autonomous Corporate AI Strategy in Xylarium.
Tests:
- Director Cynthia Voss autonomous Poison Pill triggering against hostile raiders
- Autonomous sovereign sector tariff enforcement
- Autonomous sales executive recruitment and regional expansion
- Interstellar Trade Council lobbying and subsidy enactment
- Corporate public relations recovery and rival smear campaigns
- Autonomous trader freight contract acceptance and equity investments
- Autonomous pirate weaponized short selling
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType
from xylarium.kernel.ai import AIManager


class TestAutonomousCorporateAI(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=999)
        self.player_id = "raider_x"
        self.captain = self.kernel.register_player(self.player_id, "Captain Raider")
        self.captain.credits = 100000

        self.voss = self.kernel.captains["ai_voss"]
        self.voss.credits = 25000

    def test_voss_autonomous_poison_pill_trigger(self):
        """When a raider accumulates >30% shares, Cynthia Voss triggers a defensive Poison Pill."""
        comp = self.kernel.market_manager.companies["VOSS"]
        initial_shares = comp.total_shares
        self.assertFalse(comp.poison_pill_active)

        # Raider acquires 35% of VOSS shares
        needed_shares = int(comp.total_shares * 0.35)
        self.captain.portfolio["VOSS"] = needed_shares

        # Execute AI turn for Voss
        AIManager.execute_turn(self.kernel, self.voss)

        # Verify poison pill defense was triggered
        self.assertTrue(comp.poison_pill_active)
        self.assertEqual(comp.poison_pill_uses, 0)
        self.assertGreater(comp.total_shares, initial_shares)
        self.assertEqual(comp.total_shares, initial_shares + int(initial_shares * 0.25))

    def test_voss_autonomous_sector_tariff(self):
        """Cynthia Voss autonomously enforces customs tariffs on her fortified HQ sector."""
        comp = self.kernel.market_manager.companies["VOSS"]
        # Locate Voss's HQ planet
        hq_planet = None
        for s in self.kernel.sectors.values():
            for p in s.planets:
                if p.owner_id == self.voss.id:
                    hq_planet = p
                    break
            if hq_planet:
                break

        self.assertIsNotNone(hq_planet)
        self.assertEqual(hq_planet.sector_tariff_pct, 0)

        # Run AI turn
        AIManager.execute_turn(self.kernel, self.voss)

        # Verify tariff was enacted
        self.assertGreater(hq_planet.sector_tariff_pct, 0)
        self.assertEqual(hq_planet.sector_tariff_pct, 20)

    def test_voss_autonomous_sales_executive_recruitment(self):
        """Cynthia Voss recruits corporate sales executives to expand market penetration."""
        comp = self.kernel.market_manager.companies["VOSS"]
        initial_execs = len(comp.sales_executives)

        # Run AI turn
        AIManager.execute_turn(self.kernel, self.voss)

        # Verify executive was hired
        self.assertGreater(len(comp.sales_executives), initial_execs)
        new_exec_id = comp.sales_executives[-1]
        self.assertIn(new_exec_id, self.kernel.market_manager.executives)
        exec_obj = self.kernel.market_manager.executives[new_exec_id]
        self.assertEqual(exec_obj.company_ticker, "VOSS")
        self.assertEqual(exec_obj.owner_id, self.voss.id)

    def test_voss_autonomous_trade_council_subsidy(self):
        """Cynthia Voss lobbies the Trade Council and passes a federal corporate subsidy."""
        comp = self.kernel.market_manager.companies["VOSS"]
        tc = self.kernel.market_manager.trade_council

        # Prime lobbying funds
        tc.lobbying_funds["VOSS"] = 3000

        # Run AI turn
        AIManager.execute_turn(self.kernel, self.voss)

        # Verify bill was enacted
        has_subsidy = any(
            r["bill_type"] == "SUBSIDY" and r["sponsor"] == "VOSS"
            for r in tc.active_resolutions
        )
        self.assertTrue(has_subsidy)

    def test_voss_autonomous_pr_campaign(self):
        """Cynthia Voss launches positive media campaigns when consumer trust drops below 60%."""
        comp = self.kernel.market_manager.companies["VOSS"]
        comp.consumer_trust = 45

        # Run AI turn
        AIManager.execute_turn(self.kernel, self.voss)

        # Verify consumer trust increased
        self.assertGreaterEqual(comp.consumer_trust, 65)

    def test_trader_autonomous_freight_and_stock_purchases(self):
        """Autonomous trader captains accept open freight contracts and buy ISSE shares."""
        trader = None
        for c in self.kernel.captains.values():
            if c.is_ai and c.personality and c.personality.value == "trader":
                trader = c
                break

        self.assertIsNotNone(trader)
        trader.credits = 15000
        # This test is about commerce: no native society in the trader's system to study instead
        for p in self.kernel.sectors[trader.sector_id].planets:
            p.natives = None

        # Seed an open freight contract in trader's sector
        cid = f"FRT-{self.kernel.market_manager.next_contract_id}"
        self.kernel.market_manager.next_contract_id += 1
        from xylarium.kernel.market import FreightContract
        dest_sec = trader.sector_id + 1 if trader.sector_id < 100 else 1
        contract = FreightContract(
            id=cid,
            company_ticker="VOSS",
            issuer_name="Voss Heavy Industries",
            origin_sector=trader.sector_id,
            origin_name="Local Port",
            destination_sector=dest_sec,
            destination_planet_id="planet_dest",
            destination_name="Dest World",
            commodity="ORE",
            amount=10,
            payout_credits=3000,
            shares_reward=10,
            hazard_level="FEDERATION",
            created_cycle=self.kernel.cycle_count,
            expiry_cycle=self.kernel.cycle_count + 50,
            status="OPEN",
        )
        self.kernel.market_manager.contracts[cid] = contract

        # A few of its turns: a trader's own mind may first refit or sail for a better market, but commerce follows
        for _ in range(16):
            AIManager.execute_turn(self.kernel, trader)
            if trader.active_contracts or trader.portfolio:
                break

        # Trader should accept contract or purchase stock
        self.assertTrue(len(trader.active_contracts) > 0 or len(trader.portfolio) > 0)

    def test_pirate_autonomous_short_selling(self):
        """Pirates short corporate shares before attacking target colony worlds."""
        pirate = None
        for c in self.kernel.captains.values():
            if c.is_ai and c.personality and c.personality.value == "pirate":
                pirate = c
                break

        self.assertIsNotNone(pirate)
        pirate.credits = 10000

        # Place pirate in sector with an enemy planet
        voss = self.kernel.captains["ai_voss"]
        voss_sec = None
        for s in self.kernel.sectors.values():
            for p in s.planets:
                if p.owner_id == voss.id and s.security.value != "FEDERATION":
                    voss_sec = s
                    break
            if voss_sec:
                break

        if voss_sec:
            pirate.sector_id = voss_sec.id
            if pirate.id not in voss_sec.captains:
                voss_sec.captains.append(pirate.id)

            AIManager.execute_turn(self.kernel, pirate)
            # Check if pirate took a short position or attacked
            self.assertTrue(len(pirate.short_positions) > 0 or pirate.score > 0)


if __name__ == "__main__":
    unittest.main()
