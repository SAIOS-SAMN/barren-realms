"""
Regression tests for the physical universe and the monetary system:
planet types & species genesis, star systems separated by null space, hostile acts,
debris & salvage, asteroid mining, sentries, extraction work orders, regional
currencies with the ISSE FX desk, port balance sheets, regional price gradients,
and closed-economy conservation (no undeclared money creation in any currency).
"""

import random
import unittest

from xylarium.config import HOSTILE_ACT_BOUNTY, PRICE_LEVEL
from xylarium.kernel.civilization import FOUNDING_POLITIES
from xylarium.kernel.colony import ColonyManager
from xylarium.kernel.combat import CombatManager, _eject_to_sol
from xylarium.kernel.economy import EconomyManager
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.fx import balance
from xylarium.kernel.ledger import money_supply
from xylarium.kernel.models import ActionType, SecurityLevel
from xylarium.kernel.nullspace import NullSpaceManager
from xylarium.kernel.universe import habitability, homeworld_type


def _move(kernel, cap, sector_id):
    old = kernel.sectors[cap.sector_id]
    if cap.id in old.captains:
        old.captains.remove(cap.id)
    cap.sector_id = sector_id
    kernel.sectors[sector_id].captains.append(cap.id)


class TestBoardAndGenesis(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)

    def test_star_systems_are_separated_by_null_space(self):
        sectors = self.kernel.sectors
        systems = [s for s in sectors.values() if s.kind == "SYSTEM" and s.id <= 100]
        self.assertGreater(len(systems), 15)
        self.assertEqual(sectors[1].kind, "SYSTEM")
        for sys_sec in systems:
            self.assertFalse(any(sectors[w].kind == "SYSTEM" for w in sys_sec.warps if w <= 100),
                             f"system {sys_sec.id} borders another system")
        for null in (s for s in sectors.values() if s.kind == "NULL"):
            self.assertIsNone(null.port)
            self.assertEqual(null.planets, [])
        self.assertTrue(any(s.belts for s in sectors.values() if s.kind == "NULL"))

    def test_species_arise_on_their_homeworld_type(self):
        by_name = {p["name"]: p for p in FOUNDING_POLITIES}
        homeworlds = [p for s in self.kernel.sectors.values() for p in s.planets if p.civilization is not None]
        self.assertGreaterEqual(len(homeworlds), 15)
        for planet in homeworlds:
            polity = by_name.get(planet.civilization.name)
            if polity:
                self.assertEqual(planet.planet_type, homeworld_type(polity))

    def test_uninhabited_worlds_exist_and_habitability_gates_settlement(self):
        frontier = [p for s in self.kernel.sectors.values() for p in s.planets if p.population == 0 and p.owner_id is None]
        self.assertGreater(len(frontier), 20)
        self.assertEqual(habitability("biotic", "GAS_GIANT"), 0.0)
        self.assertEqual(habitability("plasmic", "GAS_GIANT"), 1.0)
        cap = self.kernel.register_player("settler", "Settler")
        cap.credits = 10000
        cap.ship.cargo.equipment = 20
        giant = next((p for p in frontier if p.planet_type == "GAS_GIANT"), None)
        if giant is not None:
            reason = ColonyManager.claim_requirements(cap, giant, self.kernel.sectors[giant.sector_id])
            self.assertIn("uninhabitable", reason)

    def test_minted_clusters_do_not_collide_with_ghost_sectors(self):
        rm = self.kernel.research_manager
        ok, _, new_ids = rm.mint_frontier_cluster(self.kernel, 2)
        self.assertTrue(ok)
        self.assertTrue(all(200 < s <= 240 for s in new_ids))
        self.assertNotIn(105, self.kernel.sectors)


class TestNullSpaceIndustryAndCombat(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.cap = self.kernel.register_player("miner", "Miner", clade="LITHIC")
        self.belt_sector = next(s for s in self.kernel.sectors.values() if s.kind == "NULL" and s.belts)

    def test_scan_then_mine_fills_the_hold_and_depletes_the_belt(self):
        _move(self.kernel, self.cap, self.belt_sector.id)
        self.cap.turns_left = 100
        res = self.kernel.dispatch("miner", ActionType.MINE_ASTEROIDS)
        self.assertFalse(res.success)  # unsurveyed
        self.assertTrue(self.kernel.dispatch("miner", ActionType.SCAN_SPACE).success)
        belt = self.belt_sector.belts[0]
        reserve = belt["reserve"]
        used = self.cap.ship.cargo.holds_used
        res = self.kernel.dispatch("miner", ActionType.MINE_ASTEROIDS)
        self.assertTrue(res.success, res.message)
        self.assertLess(sum(b["reserve"] for b in self.belt_sector.belts), reserve + sum(b["reserve"] for b in self.belt_sector.belts[1:]) + 1)
        self.assertGreater(self.cap.ship.cargo.holds_used, used)

    def test_mining_barge_outproduces_a_scout(self):
        scout_yield = NullSpaceManager.mining_yield(self.cap)
        self.cap.ship.ship_type = "Mining Barge"
        self.assertGreater(NullSpaceManager.mining_yield(self.cap), scout_yield * 4)

    def test_destroyed_hull_leaves_salvageable_debris(self):
        _move(self.kernel, self.cap, self.belt_sector.id)
        self.cap.ship.cargo.ore = 20
        _eject_to_sol(self.cap, self.kernel)
        self.assertTrue(self.belt_sector.debris)
        salvor = self.kernel.register_player("salvor", "Salvor")
        _move(self.kernel, salvor, self.belt_sector.id)
        salvor.turns_left = 50
        res = self.kernel.dispatch("salvor", ActionType.SALVAGE_DEBRIS)
        self.assertTrue(res.success)
        self.assertGreater(salvor.ship.cargo.held("ORE") + salvor.ship.cargo.held("Fe"), 0)

    def test_hostile_act_inside_protected_system_but_not_in_null_space(self):
        attacker = self.kernel.register_player("raider", "Raider")
        victim = self.kernel.register_player("victim", "Victim")
        protected = next(s for s in self.kernel.sectors.values()
                         if s.is_protected_space and s.security != SecurityLevel.FEDERATION)
        for c in (attacker, victim):
            _move(self.kernel, c, protected.id)
        res = CombatManager.resolve_ship_battle(attacker, victim, protected, kernel=self.kernel)
        self.assertTrue(res.success)
        self.assertEqual(attacker.bounty, HOSTILE_ACT_BOUNTY)

        attacker.bounty = 0
        null = next(s for s in self.kernel.sectors.values() if s.kind == "NULL" and s.security != SecurityLevel.FEDERATION)
        for c in (attacker, victim):
            _move(self.kernel, c, null.id)
        victim.ship.shields, victim.ship.fighters = 100, 15
        CombatManager.resolve_ship_battle(attacker, victim, null, kernel=self.kernel)
        self.assertEqual(attacker.bounty, 0)

    def test_sentries_defend_their_owner_and_engage_wanted_intruders(self):
        _move(self.kernel, self.cap, self.belt_sector.id)
        self.cap.turns_left = 50
        self.cap.ship.fighters = 30
        self.assertTrue(self.kernel.dispatch("miner", ActionType.DEPLOY_SENTRIES, amount=20).success)
        self.assertEqual(self.belt_sector.sentries["miner"], 20)
        outlaw = self.kernel.register_player("outlaw", "Outlaw", clade="ANARCHY")
        outlaw.bounty = 1000
        outlaw.ship.fighters = 20
        adjacent = next(w for w in self.belt_sector.warps)
        _move(self.kernel, outlaw, adjacent)
        outlaw.turns_left = 50
        self.kernel.dispatch("outlaw", ActionType.MOVE, destination=self.belt_sector.id)
        self.assertLess(outlaw.ship.fighters, 20)
        self.assertTrue(self.kernel.dispatch("miner", ActionType.RECALL_SENTRIES).success)


class TestExtractionWorkOrders(unittest.TestCase):
    def setUp(self):
        random.seed(3)
        self.kernel = GameKernel(seed=42)
        self.mm = self.kernel.market_manager

    def test_colonies_post_extraction_orders_for_elements_they_consume(self):
        for s in self.kernel.sectors.values():
            for p in s.planets:
                if p.population > 0:
                    p.treasury = 60000
                    p.element_reserves = {}
        before = {c: b["total"] for c, b in money_supply(self.kernel).items()}
        orders = self.mm.generate_extraction_contracts(self.kernel)
        self.assertTrue(orders)
        after = {c: b["total"] for c, b in money_supply(self.kernel).items()}
        self.assertEqual(before, after)  # escrowed from vaults, not minted
        order = orders[0]
        self.assertEqual(order.kind, "EXTRACTION")
        self.assertTrue(self.kernel.sectors[order.origin_sector].is_null_space)

        # Sign at the colony, bring the mined element, get paid in the colony's currency
        cap = self.kernel.register_player("contractor", "Contractor")
        cap.ship.cargo.capacity = 200
        _move(self.kernel, cap, order.destination_sector)
        ok, msg, _ = self.mm.accept_freight_contract(cap, order.id)
        self.assertTrue(ok, msg)
        cap.ship.cargo.stow(order.commodity, order.amount)
        planet = self.kernel.get_planet(order.destination_planet_id)
        before_pay = balance(cap, order.currency)
        ok, msg, _ = self.mm.deliver_freight_contract(cap, order.id, planet)
        self.assertTrue(ok, msg)
        self.assertEqual(balance(cap, order.currency), before_pay + order.payout_credits)


class TestCurrenciesAndPorts(unittest.TestCase):
    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.fx = self.kernel.fx_market
        self.cap = self.kernel.register_player("trader", "Trader")
        self.cap.credits = 50000

    def test_amm_swaps_move_the_rate_and_charge_a_fee(self):
        rate0 = self.fx.rate("VOID")
        out = self.fx.swap_sol_to("VOID", 10000)
        self.assertLess(self.fx.rate("VOID"), rate0)  # buying VOID strengthens it
        back = self.fx.swap_to_sol("VOID", out)
        self.assertLess(back, 10000)  # round trip pays the fee

    def test_fx_desk_exchange(self):
        res = self.kernel.dispatch("trader", ActionType.FX_EXCHANGE, amount=1000, from_currency="SOL", to_currency="FRN")
        self.assertTrue(res.success)
        self.assertEqual(self.cap.credits, 49000)
        self.assertGreater(self.cap.fx_wallet["FRN"], 1700)

    def test_regional_port_settles_in_local_currency_through_its_treasury(self):
        port_sec = next(s for s in self.kernel.sectors.values()
                        if s.port and s.port.currency == "VOID" and s.port.sells.get("ORE"))
        port = port_sec.port
        _move(self.kernel, self.cap, port_sec.id)
        treasury0 = port.treasury
        res = EconomyManager.execute_buy(self.cap, port, "ORE", 5)
        self.assertTrue(res.success, res.message)
        self.assertGreater(port.treasury, treasury0)
        self.assertLess(self.cap.credits, 50000)  # SOL auto-converted into VOID

    def test_illiquid_port_cannot_buy_more_than_it_can_pay(self):
        port_sec = next(s for s in self.kernel.sectors.values() if s.port and s.port.buys.get("ORE"))
        port = port_sec.port
        unit, _ = EconomyManager.get_unit_prices(port, "ORE")
        port.treasury = unit * 3
        self.cap.ship.cargo.ore = 20
        res = EconomyManager.execute_sell(self.cap, port, "ORE", 20)
        self.assertTrue(res.success)
        self.assertEqual(self.cap.ship.cargo.ore, 17)
        port.treasury = 0
        self.assertFalse(EconomyManager.execute_sell(self.cap, port, "ORE", 5).success)

    def test_regional_gradient_manufactures_dearer_far_from_sol(self):
        near = self.kernel.sectors[1].port
        far = max((s.port for s in self.kernel.sectors.values() if s.port), key=lambda p: p.remoteness)
        near_f = EconomyManager.regional_factor(near, "MANUFACTURED") / PRICE_LEVEL[near.currency]
        far_f = EconomyManager.regional_factor(far, "MANUFACTURED") / PRICE_LEVEL[far.currency]
        raw_far = EconomyManager.regional_factor(far, "METALS") / PRICE_LEVEL[far.currency]
        self.assertGreater(far_f, near_f)
        self.assertLess(raw_far, 1.0)


class TestClosedEconomyConservation(unittest.TestCase):
    """The universe may only grow its money supply through declared faucets."""

    def test_no_undeclared_money_creation_over_a_living_universe(self):
        import simulate_playtest as sp
        random.seed(99)
        kernel = GameKernel(seed=99)
        rng = random.Random(99)
        bots = [sp.BotPlayer(kernel, clade, rng) for clade in sp.BOT_CLADES]
        stats = sp.RunStats()

        def snapshot():
            supply = {c: b["total"] for c, b in money_supply(kernel).items()}
            return supply, sp.ledger_net(kernel)

        supply0, ledger0 = snapshot()
        real_tick = kernel.tick_simulation
        kernel.tick_simulation = lambda: None
        for _ in range(200):
            for b in bots:
                b.act(kernel, stats)
            real_tick()
        supply1, ledger1 = snapshot()
        self.assertEqual(dict(stats.exceptions), {})
        for cur in set(supply0) | set(supply1):
            growth = supply1.get(cur, 0) - supply0.get(cur, 0)
            declared = ledger1.get(cur, 0) - ledger0.get(cur, 0)
            self.assertLessEqual(growth - declared, 0, f"{cur}: {growth - declared:+,} undeclared money created")


if __name__ == "__main__":
    unittest.main()


class TestMacroCirculation(unittest.TestCase):
    """Ports resell to their regions; the ISSE recycles excess reserves. Both are pure transfers."""

    def setUp(self):
        random.seed(17)
        self.kernel = GameKernel(seed=42)

    def _totals(self):
        return {c: b["total"] for c, b in money_supply(self.kernel).items()}

    def test_ports_resell_consumed_goods_to_their_region(self):
        mm = self.kernel.market_manager
        port_sec = next(s for s in self.kernel.sectors.values()
                        if s.port and mm._regional_worlds(self.kernel, s.id, s.port.currency, 3))
        port = port_sec.port
        port.consumed = {"ORE": 200}
        before_port = port.treasury
        before = self._totals()
        mm._port_retail(self.kernel)
        self.assertGreater(port.treasury, before_port)
        self.assertEqual(port.consumed, {})
        self.assertEqual(before, self._totals())   # vault -> port: nothing created or destroyed

    def test_isse_recycles_excess_reserves_home_and_strengthens_a_dumped_currency(self):
        fxm = self.kernel.fx_market
        pool = fxm.pools["FRN"]
        pool["local"] *= 2.0                        # captains have been dumping Frontier Scrip
        rate_before = fxm.rate("FRN")
        before = self._totals()
        self.kernel.market_manager._isse_recycle(self.kernel)
        self.assertLess(fxm.rate("FRN"), rate_before)  # fewer FRN per SOL: the currency strengthens
        self.assertGreater(fxm.recycled.get("FRN", 0), 0)
        self.assertEqual(before, self._totals())       # pool -> regional economy: a transfer
