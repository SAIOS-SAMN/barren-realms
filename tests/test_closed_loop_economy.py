"""
Regression tests for the closed-loop economy, syntropic AI seat, scoped experience,
realistic gating, Federal Reserve (insurance, relief, antitrust, bounties), bonded
freight, captain metabolism, and outlaw black-market harbors.
"""

import unittest

from xylarium.config import (
    BANK_LOAN_AMOUNT,
    CITADEL_UPKEEP,
    COLONY_VAULT_CAP,
    INSURANCE_PAYOUT,
    RESPAWN_KIT,
    XP_NEW_SECTOR,
    XP_WINDOW_SOFT_CAP,
    VC_RANK_CEILING,
)
from xylarium.kernel.colony import ColonyManager
from xylarium.kernel.combat import _eject_to_sol
from xylarium.kernel.cognition import CognitiveOrgan, SeatGrow
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.experience import ExperienceManager
from xylarium.kernel.market import FreightContract
from xylarium.kernel.models import ActionType, SecurityLevel


def money_total(kernel: GameKernel) -> int:
    mm = kernel.market_manager
    return (
        sum(c.credits for c in kernel.captains.values())
        + sum(p.treasury for s in kernel.sectors.values() for p in s.planets)
        + sum(c.treasury for c in mm.companies.values())
        + kernel.federal_reserve.total_holdings
        + sum(c.escrow_amount for c in mm.contracts.values() if c.status in ("OPEN", "IN_TRANSIT"))
    )


class TestExperienceDomains(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=7)
        self.cap = self.kernel.register_player("xp", "Xp Tester")

    def test_repeat_decay_and_soft_cap(self):
        first = ExperienceManager.award(self.cap, "commerce", 8, self.kernel, key="route-a")
        second = ExperienceManager.award(self.cap, "commerce", 8, self.kernel, key="route-a")
        self.assertEqual(first, 8)
        self.assertEqual(second, 4)
        for i in range(40):
            ExperienceManager.award(self.cap, "science", 10, self.kernel, key=f"k{i}")
        earned = self.cap.xp_window["earned"]
        # Past the soft cap each award is quartered, so the window total stays well below 40 x 10
        self.assertLess(earned, XP_WINDOW_SOFT_CAP + (400 - XP_WINDOW_SOFT_CAP) * 0.25 + 12)

    def test_starving_crews_learn_nothing(self):
        self.cap.hunger = 2
        self.assertEqual(ExperienceManager.award(self.cap, "navigation", 5, self.kernel), 0)

    def test_navigation_xp_only_for_new_sectors(self):
        start = self.cap.experience_domains.get("navigation", 0)
        dest = self.kernel.sectors[1].warps[0]
        self.kernel.dispatch("xp", ActionType.MOVE, destination=dest)
        after_first = self.cap.experience_domains.get("navigation", 0)
        self.assertGreaterEqual(after_first - start, XP_NEW_SECTOR)
        self.kernel.dispatch("xp", ActionType.MOVE, destination=1)
        self.kernel.dispatch("xp", ActionType.MOVE, destination=dest)
        self.assertEqual(self.cap.experience_domains.get("navigation", 0), after_first)


class TestFreightEscrowAndBonds(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=11)
        self.mm = self.kernel.market_manager
        self.cap = self.kernel.register_player("courier", "Courier")

    def _contract(self) -> FreightContract:
        planet = next(p for s in self.kernel.sectors.values() for p in s.planets if p.population > 0)
        comp = next(iter(self.mm.companies.values()))
        comp.treasury -= 800
        c = FreightContract(
            id="FRT-ESC", company_ticker=comp.ticker, issuer_name=comp.name, origin_sector=1, origin_name="Sol",
            destination_sector=planet.sector_id, destination_planet_id=planet.id, destination_name=planet.name,
            commodity="ORE", amount=5, payout_credits=800, shares_reward=0, hazard_level="FEDERATION",
            created_cycle=0, expiry_cycle=500, escrow_source=f"company:{comp.ticker}", escrow_amount=800,
        )
        self.mm.contracts[c.id] = c
        return c

    def test_company_contracts_are_escrowed_not_minted(self):
        comp = next(iter(self.mm.companies.values()))
        comp.treasury = 100000
        before = money_total(self.kernel)
        created = self.mm.generate_freight_contracts(self.kernel)
        self.assertEqual(money_total(self.kernel), before)
        self.assertTrue(all(c.escrow_amount == c.payout_credits for c in created))

    def test_bonded_cargo_cannot_be_sold_and_delivery_conserves_money(self):
        c = self._contract()
        self.cap.sector_id = 1
        self.assertTrue(self.mm.accept_freight_contract(self.cap, c.id)[0])
        self.assertEqual(self.cap.ship.cargo.bonded_units("ORE"), 5)
        res = self.kernel.dispatch("courier", ActionType.TRADE, type="SELL", commodity="ORE", amount=5)
        self.assertFalse(res.success)
        self.assertIn("bonded", res.message)

        before = money_total(self.kernel)
        planet = self.kernel.get_planet(c.destination_planet_id)
        self.cap.sector_id = c.destination_sector
        ok, _, _ = self.mm.deliver_freight_contract(self.cap, c.id, planet)
        self.assertTrue(ok)
        self.assertEqual(money_total(self.kernel), before)
        self.assertEqual(self.cap.ship.cargo.bonded_units("ORE"), 0)

    def test_accepting_freight_buys_the_goods_from_the_origin_port(self):
        c = self._contract()
        port = self.kernel.sectors[1].port
        port.stock["ORE"] = 500
        port_before, stock_before = port.treasury, port.stock["ORE"]
        from xylarium.kernel.ledger import money_supply
        supply_before = {cur: b["total"] for cur, b in money_supply(self.kernel).items()}
        self.cap.sector_id = 1
        self.assertTrue(self.mm.accept_freight_contract(self.cap, c.id)[0])
        self.assertGreater(port.treasury, port_before)        # the origin port is paid for the goods
        self.assertEqual(port.stock["ORE"], stock_before - 5)  # ...and ships them
        self.assertEqual(c.payout_credits, c.escrow_amount)    # the rest of the escrow is the haul fee
        supply_after = {cur: b["total"] for cur, b in money_supply(self.kernel).items()}
        self.assertEqual(supply_before, supply_after)          # a transfer, not new money

    def test_voided_contract_refunds_escrow_and_repossesses_goods(self):
        c = self._contract()
        comp = self.mm.companies[c.company_ticker]
        self.cap.sector_id = 1
        self.mm.accept_freight_contract(self.cap, c.id)
        # On acceptance part of the escrow bought the goods at the origin port; the rest is the haul fee
        remaining = c.escrow_amount
        self.assertLessEqual(remaining, 800)
        treasury_before = comp.treasury
        self.mm.void_contract(c, self.kernel)
        self.assertEqual(comp.treasury, treasury_before + remaining)
        self.assertEqual(self.cap.ship.cargo.ore, 0)
        self.assertNotIn(c.id, self.cap.active_contracts)

    def test_colony_imports_are_paid_from_the_colony_vault(self):
        planet = next(p for s in self.kernel.sectors.values() for p in s.planets if p.population > 0)
        planet.organics_silo = 0
        planet.treasury = 50000
        before = money_total(self.kernel)
        created = [c for c in self.mm.generate_colony_imports(self.kernel) if c.destination_planet_id == planet.id]
        self.assertTrue(created)
        self.assertLess(planet.treasury, 50000)
        self.assertEqual(money_total(self.kernel), before)


class TestColonyFiscalModel(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=5)
        self.planet = next(p for s in self.kernel.sectors.values() for p in s.planets if p.population > 0)
        self.planet.population = 20000
        self.planet.organics_silo = 4000
        self.planet.ore_silo = 1000
        self.planet.citadel_level = 2

    def test_tax_tapers_toward_vault_cap(self):
        self.planet.treasury = 10000
        low = ColonyManager.tick_colony(self.planet)["tax_yield"]
        self.planet.treasury = int(COLONY_VAULT_CAP * 0.95)
        high = ColonyManager.tick_colony(self.planet)["tax_yield"]
        self.assertGreater(low, high * 5)

    def test_upkeep_burns_credits_and_ore(self):
        self.planet.treasury = 10000
        ore_before = self.planet.ore_silo
        res = ColonyManager.tick_colony(self.planet)
        self.assertTrue(res["upkeep_paid"])
        self.assertEqual(self.planet.treasury, 10000 - CITADEL_UPKEEP[2]["credits"] + res["tax_yield"]
                         - res["public_services"] - (500 if res["recruited_sec"] else 0))
        self.assertLess(self.planet.ore_silo, ore_before + res["ore_mined"])


class TestFederalReserve(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=3)
        self.fed = self.kernel.federal_reserve
        self.cap = self.kernel.register_player("fed", "Fed Tester")

    def test_insured_hull_loss_pays_claim_and_replaces_hull(self):
        self.cap.ship.ship_type = "Merchant Cruiser"
        self.cap.credits = 0
        reserve = self.fed.treasury
        payout = _eject_to_sol(self.cap, self.kernel)
        self.assertEqual(payout, INSURANCE_PAYOUT)
        self.assertEqual(self.cap.credits, INSURANCE_PAYOUT)
        self.assertEqual(self.fed.treasury, reserve - INSURANCE_PAYOUT)
        self.assertEqual(self.cap.ship.ship_type, "Scout Ship")
        self.assertEqual(self.cap.ship.cargo.capacity, RESPAWN_KIT["holds"])
        self.assertEqual(self.cap.ship.fighters, RESPAWN_KIT["fighters"])

    def test_uninsured_hull_loss_has_no_cash_floor(self):
        self.cap.insurance_paid_through = -1
        self.cap.credits = 40
        _eject_to_sol(self.cap, self.kernel, credit_loss_frac=0.5)
        self.assertEqual(self.cap.credits, 20)

    def test_premiums_move_credits_into_the_reserve(self):
        self.cap.credits = 10000
        before = money_total(self.kernel)
        reserve = self.fed.treasury
        self.fed.collect_premiums(self.kernel)
        self.assertGreater(self.fed.treasury, reserve)
        self.assertEqual(money_total(self.kernel), before)

    def test_antitrust_surtax_on_dominant_captain(self):
        for c in self.kernel.captains.values():
            c.credits = 1000
        self.cap.credits = 5_000_000
        reserve = self.fed.treasury
        self.fed.fiscal_quarter(self.kernel)
        self.assertLess(self.cap.credits, 5_000_000)
        self.assertGreater(self.fed.treasury + sum(self.fed.bounty_escrow.values()), reserve)

    def test_public_bounty_escrow_settles_claims_without_minting(self):
        outlaw = self.kernel.register_player("outlaw", "Outlaw", clade="ANARCHY")
        outlaw.bounty = 1000
        self.fed.fiscal_quarter(self.kernel)
        self.assertGreater(self.fed.bounty_escrow.get("outlaw", 0), 0)
        before = self.fed.total_holdings
        paid = self.fed.settle_bounty("outlaw", outlaw.bounty)
        self.assertEqual(self.fed.total_holdings, before - paid)

    def test_relief_loan_is_lent_from_reserve(self):
        self.cap.sector_id = 1
        self.cap.credits = 10
        reserve = self.fed.treasury
        res = self.kernel.dispatch("fed", ActionType.BANK_TRANSACTION, sub_action="loan")
        self.assertTrue(res.success)
        self.assertEqual(self.fed.treasury, reserve - BANK_LOAN_AMOUNT)


class TestGatingAndMetabolism(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=9)

    def test_clade_sets_metabolism_and_starter_rations(self):
        lith = self.kernel.register_player("lith", "Lith", clade="LITHIC")
        plas = self.kernel.register_player("plas", "Plas", clade="PLASMIC")
        self.assertEqual(lith.metabolism, "mineral")
        self.assertEqual(lith.ship.cargo.ore, 10)
        self.assertEqual(plas.metabolism, "plasmic")
        self.assertEqual(plas.ship.cargo.held("H"), 10)

    def test_crews_eat_and_go_hungry(self):
        cap = self.kernel.register_player("eater", "Eater")
        cap.ship.cargo.organics = 1
        self.kernel._consume_rations()
        self.assertEqual(cap.ship.cargo.organics, 0)
        self.assertEqual(cap.hunger, 0)
        shields = cap.ship.shields
        self.kernel._consume_rations()
        self.assertEqual(cap.hunger, 1)
        self.assertLess(cap.ship.shields, shields)

    def test_hungry_crew_eats_as_soon_as_rations_come_aboard(self):
        cap = self.kernel.register_player("eater", "Eater")
        port_sec = next(s for s in self.kernel.sectors.values()
                        if s.port and s.port.sells.get("ORGANICS") and s.port.stock.get("ORGANICS", 0) > 5)
        self.kernel.sectors[cap.sector_id].captains.remove(cap.id)
        cap.sector_id = port_sec.id
        port_sec.captains.append(cap.id)
        cap.ship.cargo.organics = 0
        cap.hunger = 3
        cap.credits = 50000
        res = self.kernel.dispatch("eater", ActionType.TRADE, type="BUY", commodity="ORGANICS", amount=5)
        self.assertTrue(res.success, res.message)
        self.assertEqual(cap.hunger, 0)
        self.assertEqual(cap.ship.cargo.organics, 4)

    def test_rookie_vc_facility_is_small(self):
        cap = self.kernel.register_player("rookie", "Rookie")
        cap.credits = 50000
        cap.revenue_history = [[0, 2000]]
        terms = self.kernel.market_manager.calculate_borrowing_terms(cap, "SOL_ANGEL", self.kernel)
        self.assertLessEqual(terms["facility_ceiling"], min(6000, VC_RANK_CEILING[1]))

    def test_established_system_requires_charter(self):
        cap = self.kernel.register_player("settler", "Settler")
        cap.credits = 10000
        cap.ship.cargo.equipment = 20
        sector = next(s for s in self.kernel.sectors.values() if s.planets)
        target = sector.planets[0]
        if len(sector.planets) == 1:
            from xylarium.kernel.models import Planet
            target = Planet(id="p_extra", sector_id=sector.id, name="Extra", population=0)
            sector.planets.append(target)
            sector.planets[0].owner_id = "someone_else"
        else:
            sector.planets[1].owner_id = "someone_else"
        target.owner_id = None
        target.population = 0
        target.civilization = None
        reason = ColonyManager.claim_requirements(cap, target, sector)
        self.assertIsNotNone(reason)
        self.assertIn("settlement charter", reason)


class TestShipyardAndAutomation(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=13)
        self.cap = self.kernel.register_player("pilot", "Pilot")

    def test_partial_shield_recharge(self):
        self.cap.sector_id = 1
        self.cap.ship.shields = 0
        self.cap.credits = 60
        res = self.kernel.dispatch("pilot", ActionType.SHIPYARD_PURCHASE, item="shields")
        self.assertTrue(res.success)
        self.assertEqual(self.cap.ship.shields, 20)
        self.assertEqual(self.cap.credits, 0)

    def test_black_market_refit_in_anarchy(self):
        harbor = next(s for s in self.kernel.sectors.values() if s.security == SecurityLevel.ANARCHY and s.port)
        self.kernel.sectors[self.cap.sector_id].captains.remove("pilot")
        self.cap.sector_id = harbor.id
        harbor.captains.append("pilot")
        self.cap.ship.fighters = 0
        self.cap.credits = 1000
        res = self.kernel.dispatch("pilot", ActionType.SHIPYARD_PURCHASE, item="fighters", amount=5)
        self.assertTrue(res.success)
        self.assertLess(self.cap.credits, 1000 - 5 * 45)
        hull = self.kernel.dispatch("pilot", ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Merchant Cruiser")
        self.assertFalse(hull.success)

    def test_automation_costs_turns(self):
        self.cap.turns_left = 50
        self.kernel.dispatch("pilot", ActionType.COGNITIVE_AUTOMATE)
        self.assertLess(self.cap.turns_left, 50)
        self.cap.turns_left = 0
        res = self.kernel.dispatch("pilot", ActionType.COGNITIVE_AUTOMATE)
        self.assertFalse(res.success)


class TestSyntropicSeat(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=21)
        self.ai = next(c for c in self.kernel.captains.values() if c.is_ai)

    def test_observes_ports_into_price_memory(self):
        port_sector = next(s for s in self.kernel.sectors.values() if s.port)
        SeatGrow.observe_port(self.ai, port_sector, self.kernel)
        self.assertIn(str(port_sector.id), self.ai.price_memory)

    def test_sells_cargo_at_profit(self):
        sector = self.kernel.sectors[1]
        self.ai.ship.cargo.ore = 20
        # Arbitrage plans remember their unit cost in SOL; a cheap buy is sold at a profit
        self.ai.active_plan = {"kind": "haul", "commodity": "ORE", "dest": 1, "since": 0, "unit_cost_sol": 1.0}
        deed = SeatGrow._sell_here(self.ai, sector, min_margin=1.05, only="ORE")
        self.assertIsNotNone(deed)
        self.assertEqual(deed.deed_name, "SELL_AT_PROFIT")

    def test_failed_deed_cools_down_instead_of_repeating(self):
        cap = self.ai
        cap.deed_cooldowns["RECHARGE_SHIELD_GRID"] = self.kernel.cycle_count + 10
        cap.ship.shields = 0
        cap.sector_id = 1
        cap.credits = 5000
        res = CognitiveOrgan.think(cap, self.kernel)
        self.assertNotEqual(getattr(res, "action", None), ActionType.SHIPYARD_PURCHASE)


if __name__ == "__main__":
    unittest.main()
