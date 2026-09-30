"""
Unit tests for Xylarium P1-P6 Critical Systems:
- P1: Turn Replenishment Maintenance & Stardock Rest
- P2: Shipyard Fighter Bay Capacity Cap Enforcement
- P3: Federal Bank Emergency Relief Loans & Debt Repayment
- P4: Colony Population Caps & Organics Famine Mechanics
- P5: Tactical Combat Round Options (Volley, Evade, Bribe)
- P6: AI Autonomous Maintenance, Re-arming & Tax Harvesting
"""

import unittest
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import (
    ActionType,
    AIPersonality,
    Captain,
    Planet,
    SecurityLevel,
    Ship,
    CargoHold,
)
from xylarium.kernel.colony import ColonyManager
from xylarium.kernel.combat import CombatManager
from xylarium.kernel.ai import AIManager
from xylarium.config import (
    PLAYER_MAX_TURNS,
    MAINTENANCE_INTERVAL_CYCLES,
    MAINTENANCE_TURNS_GRANTED,
    REST_COST_CREDITS,
    REST_TURNS_RESTORED,
    BANK_LOAN_AMOUNT,
    BANK_DEBT_TOTAL,
    BANK_EMERGENCY_THRESHOLD,
    CITADEL_CONFIG,
    SHIP_CATALOG,
)


class TestP1TurnReplenishment(unittest.TestCase):
    """P1: Turn replenishment maintenance and Stardock Officer Quarters."""

    def setUp(self):
        self.kernel = GameKernel()
        self.player = self.kernel.register_player("pilot_p1", "Captain Picard")

    def test_process_turn_maintenance(self):
        self.player.turns_left = 50
        self.kernel.process_turn_maintenance()
        self.assertEqual(self.player.turns_left, 50 + MAINTENANCE_TURNS_GRANTED)

        # Cap enforcement at PLAYER_MAX_TURNS
        self.player.turns_left = PLAYER_MAX_TURNS - 20
        self.kernel.process_turn_maintenance()
        self.assertEqual(self.player.turns_left, PLAYER_MAX_TURNS)

    def test_turn_maintenance_fires_on_cycle_interval(self):
        self.player.turns_left = 100
        initial_cycle = self.kernel.cycle_count
        # Set cycle_count to just before maintenance interval
        self.kernel.cycle_count = MAINTENANCE_INTERVAL_CYCLES - 1
        self.kernel.tick_simulation()
        self.assertEqual(self.player.turns_left, 100 + MAINTENANCE_TURNS_GRANTED)

    def test_rest_at_sector_1_stardock(self):
        self.player.sector_id = 1
        self.player.turns_left = 50
        self.player.credits = 2500

        res = self.kernel.dispatch(self.player.id, ActionType.REST)
        self.assertTrue(res.success)
        self.assertEqual(self.player.turns_left, 50 + REST_TURNS_RESTORED)
        self.assertEqual(self.player.credits, 2500 - REST_COST_CREDITS)

    def test_rest_prohibited_outside_sector_1(self):
        self.player.sector_id = 2
        self.player.credits = 2500
        res = self.kernel.dispatch(self.player.id, ActionType.REST)
        self.assertFalse(res.success)
        self.assertIn("Sector 1", res.message)

    def test_rest_rejected_insufficient_credits(self):
        self.player.sector_id = 1
        self.player.credits = 200
        res = self.kernel.dispatch(self.player.id, ActionType.REST)
        self.assertFalse(res.success)
        self.assertIn("requires 1,000 Credits", res.message)


class TestP2FighterCapEnforcement(unittest.TestCase):
    """P2: Fighter bay capacity enforcement at Shipyard."""

    def setUp(self):
        self.kernel = GameKernel()
        self.player = self.kernel.register_player("pilot_p2", "Captain Kirk")
        self.player.sector_id = 1
        self.player.credits = 10000

    def test_fighter_purchase_exceeding_capacity_rejected(self):
        # Scout Ship max fighters is 20
        self.player.ship.ship_type = "Scout Ship"
        self.player.ship.fighters = 15

        # Attempt to purchase 10 fighters (15 + 10 = 25 > 20)
        res = self.kernel.dispatch(self.player.id, ActionType.SHIPYARD_PURCHASE, item="fighters", amount=10)
        self.assertFalse(res.success)
        self.assertIn("Fighter bay capacity exceeded", res.message)
        self.assertEqual(self.player.ship.fighters, 15)
        self.assertEqual(self.player.credits, 10000)

    def test_fighter_purchase_within_capacity_succeeds(self):
        self.player.ship.ship_type = "Scout Ship"
        self.player.ship.fighters = 10

        # Purchase 10 fighters (10 + 10 = 20 <= 20)
        res = self.kernel.dispatch(self.player.id, ActionType.SHIPYARD_PURCHASE, item="fighters", amount=10)
        self.assertTrue(res.success)
        self.assertEqual(self.player.ship.fighters, 20)
        self.assertEqual(self.player.credits, 10000 - (10 * 45))


class TestP3FederalBankReliefLoans(unittest.TestCase):
    """P3: Bankruptcy safety net & Federal Bank relief loans."""

    def setUp(self):
        self.kernel = GameKernel()
        self.player = self.kernel.register_player("pilot_p3", "Captain Han")
        self.player.sector_id = 1

    def test_loan_denied_if_not_destitute(self):
        self.player.credits = 500  # >= BANK_EMERGENCY_THRESHOLD (100)
        res = self.kernel.dispatch(self.player.id, ActionType.BANK_TRANSACTION, sub_action="loan")
        self.assertFalse(res.success)
        self.assertIn("reserved for destitute captains", res.message)

    def test_loan_granted_for_destitute_captain(self):
        self.player.credits = 45  # < 100
        self.player.debt = 0
        res = self.kernel.dispatch(self.player.id, ActionType.BANK_TRANSACTION, sub_action="loan")
        self.assertTrue(res.success)
        self.assertEqual(self.player.credits, 45 + BANK_LOAN_AMOUNT)
        self.assertEqual(self.player.debt, BANK_DEBT_TOTAL)

    def test_bankruptcy_relief_allows_one_outstanding_loan(self):
        # A destitute captain with one unpaid relief loan may re-arm once more (bankruptcy exemption)
        self.player.credits = 50
        self.player.debt = BANK_DEBT_TOTAL
        reserve_before = self.kernel.federal_reserve.treasury
        res = self.kernel.dispatch(self.player.id, ActionType.BANK_TRANSACTION, sub_action="loan")
        self.assertTrue(res.success)
        # Relief is lent from the Federal Reserve, not minted
        self.assertEqual(self.kernel.federal_reserve.treasury, reserve_before - BANK_LOAN_AMOUNT)

    def test_loan_denied_past_relief_debt_ceiling(self):
        self.player.credits = 50
        self.player.debt = BANK_DEBT_TOTAL * 2
        res = self.kernel.dispatch(self.player.id, ActionType.BANK_TRANSACTION, sub_action="loan")
        self.assertFalse(res.success)
        self.assertIn("Relief credit exhausted", res.message)

    def test_debt_repayment_flow(self):
        self.player.credits = 2000
        self.player.debt = 1150

        # Partial repayment
        res = self.kernel.dispatch(self.player.id, ActionType.BANK_TRANSACTION, sub_action="repay", amount=500)
        self.assertTrue(res.success)
        self.assertEqual(self.player.credits, 1500)
        self.assertEqual(self.player.debt, 650)

        # Full repayment of remaining balance
        res = self.kernel.dispatch(self.player.id, ActionType.BANK_TRANSACTION, sub_action="repay")
        self.assertTrue(res.success)
        self.assertEqual(self.player.credits, 1500 - 650)
        self.assertEqual(self.player.debt, 0)


class TestP4ColonyCapsAndFamine(unittest.TestCase):
    """P4: Citadel population caps and Organics food consumption/famine."""

    def setUp(self):
        self.kernel = GameKernel()
        self.player = self.kernel.register_player("pilot_p4", "Governor Tarkin")
        self.planet = None
        for s in self.kernel.sectors.values():
            for p in s.planets:
                if p.owner_id is None:
                    self.planet = p
                    break
            if self.planet:
                break
        self.assertIsNotNone(self.planet)
        self.planet.owner_id = self.player.id
        self.planet.citadel_level = 0  # Tier 0 max pop is 2,500
        self.planet.treasury = 1000    # Upkeep funded so food mechanics are measured in isolation

    def test_citadel_population_cap_enforced(self):
        self.planet.population = 2400
        self.player.credits = 5000

        # Invest 1,000 Cr -> requests +200 colonists, but cap only allows +100
        res = ColonyManager.invest_population(self.player, self.planet, 1000)
        self.assertTrue(res.success)
        self.assertEqual(self.planet.population, 2500)

        # Next investment rejected
        res2 = ColonyManager.invest_population(self.player, self.planet, 500)
        self.assertFalse(res2.success)
        self.assertIn("Housing cap reached", res2.message)

    def test_colony_organics_consumption_and_natural_growth(self):
        self.planet.population = 2000
        self.planet.organics_silo = 50
        self.planet.morale = 90

        yield_data = ColonyManager.tick_colony(self.planet)
        self.assertFalse(yield_data["famine"])
        # Consumes max(1, 2000 // 1000) = 2 Organics
        self.assertEqual(self.planet.organics_silo, 50 - 2 + yield_data["organics_harvested"])
        self.assertGreater(self.planet.morale, 90)
        self.assertGreater(yield_data["pop_growth"], 0)

    def test_unpaid_upkeep_halts_taxes_and_erodes_morale(self):
        self.planet.treasury = 0
        self.planet.organics_silo = 50
        self.planet.morale = 90
        self.planet.citadel_level = 2  # upkeep that a tiny colony's tax cannot cover
        self.planet.population = 500
        yield_data = ColonyManager.tick_colony(self.planet)
        self.assertFalse(yield_data["upkeep_paid"])
        # Gross tax was collected and fully spent on arrears; nothing reaches the vault
        self.assertEqual(self.planet.treasury, 0)
        self.assertLess(self.planet.morale, 92)

    def test_colony_famine_triggers_population_loss_and_morale_drop(self):
        self.planet.population = 3000
        self.planet.organics_silo = 0  # Silo empty
        self.planet.morale = 100

        yield_data = ColonyManager.tick_colony(self.planet)
        self.assertTrue(yield_data["famine"])
        self.assertGreater(yield_data["famine_loss"], 0)
        self.assertLess(self.planet.population, 3000)
        self.assertEqual(self.planet.morale, 85)  # -15 morale crash


class TestP5TacticalCombat(unittest.TestCase):
    """P5: Tactical combat options (volley, evade, bribe)."""

    def setUp(self):
        self.kernel = GameKernel()
        self.attacker = self.kernel.register_player("pilot_att", "Attacker")
        self.defender = self.kernel.register_player("pilot_def", "Defender")
        self.sector = self.kernel.sectors[30]  # Anarchy sector
        self.attacker.sector_id = 30
        self.defender.sector_id = 30
        self.sector.captains = [self.attacker.id, self.defender.id]

    def test_tactical_bribe_truce(self):
        self.attacker.credits = 2000
        self.defender.credits = 500

        res = self.kernel.dispatch(
            self.attacker.id,
            ActionType.ATTACK_SHIP,
            target_id=self.defender.id,
            tactic="bribe",
            bribe_amount=400,
        )
        self.assertTrue(res.success)
        self.assertIn("Truce negotiated", res.message)
        self.assertEqual(self.attacker.credits, 1600)
        self.assertEqual(self.defender.credits, 900)
        self.assertEqual(res.turns_spent, 1)

    def test_tactical_evasive_escape(self):
        target_escape = self.sector.warps[0]
        res = self.kernel.dispatch(
            self.attacker.id,
            ActionType.ATTACK_SHIP,
            target_id=self.defender.id,
            tactic="evade",
            escape_sector=target_escape,
        )
        self.assertTrue(res.success)
        self.assertEqual(res.turns_spent, 1)
        if res.data.get("evaded"):
            self.assertEqual(self.attacker.sector_id, target_escape)
            self.assertIn("Emergency warp escape successful", res.message)


class TestP6AIMaintenance(unittest.TestCase):
    """P6: AI maintenance, re-arming and colony tax harvesting heuristics."""

    def setUp(self):
        self.kernel = GameKernel()
        self.malakor = self.kernel.captains["ai_malakor"]
        self.voss = self.kernel.captains["ai_voss"]

    def test_ai_rearming_at_stardock(self):
        # Place Malakor at Sector 1 Stardock critically depleted
        self.malakor.sector_id = 1
        self.malakor.ship.shields = 0
        self.malakor.ship.fighters = 5
        self.malakor.credits = 50  # Destitute!
        self.malakor.debt = 0

        # Execute AI cycle
        AIManager.execute_turn(self.kernel, self.malakor)

        # Malakor should have taken loan and recharged/re-armed
        self.assertGreater(self.malakor.debt, 0)
        self.assertGreater(self.malakor.ship.shields, 0)
        self.assertGreater(self.malakor.ship.fighters, 5)

    def test_ai_colony_tax_harvesting(self):
        # Set up a colony owned by Cynthia Voss with uncollected taxes
        sec = self.kernel.sectors[17]
        planet = sec.planets[0]
        planet.owner_id = self.voss.id
        planet.treasury = 3500

        self.voss.sector_id = 17
        self.voss.credits = 1000  # Low credits

        AIManager.execute_turn(self.kernel, self.voss)

        # Voss should draw the sovereign levy (20% of the vault, in the colony's regional currency)
        from xylarium.kernel.fx import balance
        self.assertLess(planet.treasury, 3500)
        if planet.currency == "SOL":
            self.assertGreater(self.voss.credits, 1000)
        else:
            self.assertGreater(balance(self.voss, planet.currency), 0)


class TestP1P6Persistence(unittest.TestCase):
    """Verify serialization and deserialization of P1-P6 fields (debt, morale)."""

    def test_save_and_load_with_debt_and_morale(self):
        import tempfile
        import os
        from xylarium.persistence.store import StatePersistence

        kernel = GameKernel(seed=123)
        player = kernel.register_player("debtor_dan", "Dan")
        player.debt = 1150
        player.credits = 500

        planet = kernel.sectors[1].planets[0] if kernel.sectors[1].planets else None
        if not planet:
            for s in kernel.sectors.values():
                if s.planets:
                    planet = s.planets[0]
                    break
        self.assertIsNotNone(planet)
        planet.morale = 65

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            filepath = tf.name

        try:
            self.assertTrue(StatePersistence.save_to_file(kernel, filepath))
            restored = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(restored)

            restored_player = restored.get_player("debtor_dan")
            self.assertIsNotNone(restored_player)
            self.assertEqual(restored_player.debt, 1150)
            self.assertEqual(restored_player.credits, 500)

            restored_planet = None
            for s in restored.sectors.values():
                for p in s.planets:
                    if p.id == planet.id:
                        restored_planet = p
                        break
                if restored_planet:
                    break

            self.assertIsNotNone(restored_planet)
            self.assertEqual(restored_planet.morale, 65)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


if __name__ == "__main__":
    unittest.main()
