"""
Comprehensive test suite for Xylarium MUD Kernel.
Verifies all 5 core requirements from the blueprint:
1. Terminal / ASCII HUD data model
2. Universe graph, warp reachability, and BFS pathfinding
3. Dynamic BBS economy & pricing curves
4. Planetary colonization (BRE/SRE style)
5. AI rival captain heuristics & radio broadcasts
6. Save / load state persistence
"""

import unittest
from xylarium.config import COLONY_KIT_CREDITS, COLONY_KIT_EQUIPMENT, CITADEL_UPKEEP
import os
import tempfile
from xylarium.config import TOTAL_SECTORS
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import (
    ActionType,
    CommodityType,
    SecurityLevel,
    PortClass,
    AIPersonality,
)
from xylarium.kernel.economy import EconomyManager
from xylarium.kernel.colony import ColonyManager
from xylarium.client.renderer import TerminalRenderer
from xylarium.persistence.store import StatePersistence


class TestUniverseGraph(unittest.TestCase):
    """Test 2: Universe Graph & Navigation."""

    def setUp(self):
        self.kernel = GameKernel(seed=1337)
        self.player = self.kernel.register_player("tester", "Tester")

    def test_total_sectors(self):
        self.assertEqual(len(self.kernel.sectors), TOTAL_SECTORS)

    def test_sector_1_stardock(self):
        sec1 = self.kernel.sectors[1]
        self.assertEqual(sec1.security, SecurityLevel.FEDERATION)
        self.assertIsNotNone(sec1.port)
        self.assertEqual(sec1.port.port_class, PortClass.STARDOCK)

    def test_all_sectors_reachable_from_sector_1(self):
        """Ensure BFS can reach every single sector from Sector 1."""
        for target in range(2, TOTAL_SECTORS + 1):
            path = self.kernel.find_path(1, target)
            self.assertTrue(len(path) > 1, f"Sector {target} is unreachable from Sector 1")
            self.assertEqual(path[0], 1)
            self.assertEqual(path[-1], target)

    def test_warp_bidirectionality(self):
        """Verify warp lanes are valid bidirectional connections."""
        for s_id, sec in self.kernel.sectors.items():
            self.assertGreaterEqual(len(sec.warps), 2)
            for w in sec.warps:
                self.assertIn(s_id, self.kernel.sectors[w].warps)

    def test_player_movement(self):
        """Moving to a connected sector consumes 1 turn and changes sector."""
        initial_sector = self.player.sector_id
        valid_dest = self.kernel.sectors[initial_sector].warps[0]
        initial_turns = self.player.turns_left

        res = self.kernel.dispatch("tester", ActionType.MOVE, destination=valid_dest)
        self.assertTrue(res.success)
        self.assertEqual(self.player.sector_id, valid_dest)
        self.assertEqual(self.player.turns_left, initial_turns - 1)

    def test_illegal_warp_rejected(self):
        """Moving to a non-neighboring sector fails without spending turns."""
        initial_turns = self.player.turns_left
        non_neighbor = 99
        if non_neighbor in self.kernel.sectors[self.player.sector_id].warps:
            non_neighbor = 98

        res = self.kernel.dispatch("tester", ActionType.MOVE, destination=non_neighbor)
        self.assertFalse(res.success)
        self.assertEqual(self.player.turns_left, initial_turns)


class TestDynamicEconomy(unittest.TestCase):
    """Test 3: BBS-Style Dynamic Economy."""

    def setUp(self):
        self.kernel = GameKernel(seed=42)
        self.player = self.kernel.register_player("trader_joe", "Trader Joe")
        # Give player abundant credits and empty holds
        self.player.credits = 10000

    def test_buying_depletes_stock_and_raises_price(self):
        """Buying from a port reduces inventory and increases subsequent sell price."""
        # Find a sector where port sells Ore
        target_sec = None
        for s in self.kernel.sectors.values():
            if s.port and s.port.sells.get("ORE") and s.port.stock.get("ORE", 0) >= 50:
                target_sec = s
                break

        self.assertIsNotNone(target_sec)
        self.player.sector_id = target_sec.id
        port = target_sec.port

        _, initial_sell_price = EconomyManager.get_unit_prices(port, "ORE")
        initial_stock = port.stock["ORE"]

        # Buy 20 units
        res = self.kernel.dispatch("trader_joe", ActionType.TRADE, type="BUY", commodity="ORE", amount=20)
        self.assertTrue(res.success)
        self.assertEqual(self.player.ship.cargo.ore, 20)
        self.assertEqual(port.stock["ORE"], initial_stock - 20)

        _, new_sell_price = EconomyManager.get_unit_prices(port, "ORE")
        # Scarcity raises or maintains high price
        self.assertGreaterEqual(new_sell_price, initial_sell_price)

    def test_selling_increases_stock_and_lowers_price(self):
        """Selling to a port increases inventory and decreases unit payout."""
        # Find a sector where port buys Ore
        target_sec = None
        for s in self.kernel.sectors.values():
            if s.port and s.port.buys.get("ORE"):
                target_sec = s
                break

        self.assertIsNotNone(target_sec)
        self.player.sector_id = target_sec.id
        port = target_sec.port

        # Give player 20 units of Ore
        self.player.ship.cargo.ore = 20
        initial_stock = port.stock["ORE"]
        initial_buy_price, _ = EconomyManager.get_unit_prices(port, "ORE")

        self.kernel.tick_simulation = lambda: None   # isolate the sale from the world tick it would trigger
        res = self.kernel.dispatch("trader_joe", ActionType.TRADE, type="SELL", commodity="ORE", amount=20)
        self.assertTrue(res.success)
        self.assertEqual(self.player.ship.cargo.ore, 0)
        self.assertEqual(port.stock["ORE"], initial_stock + 20)

        new_buy_price, _ = EconomyManager.get_unit_prices(port, "ORE")
        # Surplus lowers buy payout
        self.assertLessEqual(new_buy_price, initial_buy_price)

    def test_cargo_hold_capacity_enforced(self):
        """Player cannot buy more than ship hold capacity."""
        # Stardock sells everything
        self.player.sector_id = 1
        self.player.ship.cargo.capacity = 30
        self.player.ship.cargo.organics = 0     # no starter rations: exact hold arithmetic below
        self.player.ship.cargo.equipment = 25  # 25 equipment consumes 25 holds, leaving 5 free holds

        # Attempting to buy 10 equipment requires 10 holds, exceeding the 5 available
        res = self.kernel.dispatch("trader_joe", ActionType.TRADE, type="BUY", commodity="EQUIPMENT", amount=10)
        self.assertFalse(res.success)
        self.assertIn("Insufficient cargo holds", res.message)

        # Buying within capacity (e.g., 5 equipment) succeeds
        res_ok = self.kernel.dispatch("trader_joe", ActionType.TRADE, type="BUY", commodity="EQUIPMENT", amount=5)
        self.assertTrue(res_ok.success)


class TestPlanetaryColonization(unittest.TestCase):
    """Test 3b: BRE / SRE Planetary Colonization."""

    def setUp(self):
        self.kernel = GameKernel(seed=101)
        self.player = self.kernel.register_player("emperor", "Emperor")
        self.player.credits = 50000

        # Find an unowned planet
        self.planet = None
        self.planet_sector = None
        for s in self.kernel.sectors.values():
            for p in s.planets:
                if (p.owner_id is None and p.civilization is None and p.population == 0
                        and not p.natives and not p.faction_id):
                    self.planet = p
                    self.planet_sector = s
                    break
            if self.planet:
                break

        self.assertIsNotNone(self.planet)
        self.player.sector_id = self.planet_sector.id

    def _frontier_world(self):
        for s in self.kernel.sectors.values():
            others_present = any(p.owner_id or p.population > 0 for p in s.planets if p.population > 0 or p.owner_id)
            for p in s.planets:
                if (p.owner_id is None and p.population == 0 and not others_present
                        and p.planet_type in ("TERRESTRIAL", "OCEANIC")):  # habitable for biotic settlers
                    return s, p
        self.fail("Expected an unsettled frontier world")

    def test_claim_unowned_planet(self):
        """An outfitted rookie founds a colony on an unsettled frontier world; the colony kit is consumed."""
        sector, frontier = self._frontier_world()
        self.player.sector_id = sector.id
        self.player.credits = 10000
        self.player.ship.cargo.equipment = 15
        res = self.kernel.dispatch("emperor", ActionType.PLANET_CLAIM, planet_id=frontier.id)
        self.assertTrue(res.success, res.message)
        self.assertEqual(frontier.owner_id, "emperor")
        # (crew wages for the turn are paid ashore when the ship is at a port)
        wages = self.kernel.crew_wage(self.player) if self.kernel.sectors[sector.id].port else 0
        self.assertEqual(self.player.credits, 10000 - COLONY_KIT_CREDITS - wages)
        self.assertEqual(self.player.ship.cargo.equipment, 15 - COLONY_KIT_EQUIPMENT)
        self.assertGreater(frontier.population, 0)

    def test_rookie_cannot_annex_indigenous_world(self):
        """Indigenous-inhabited worlds need Tier 3 treaty standing (or invasion), not a claim."""
        self.player.credits = 10000
        self.player.ship.cargo.equipment = 15
        indigenous = next(p for s in self.kernel.sectors.values() for p in s.planets
                          if p.owner_id is None and p.population > 0 and p.civilization is not None
                          and p.civilization.name != "Terran Federation" and not p.faction_id)
        self.player.sector_id = indigenous.sector_id
        res = self.kernel.dispatch("emperor", ActionType.PLANET_CLAIM, planet_id=indigenous.id)
        self.assertFalse(res.success)
        self.assertIn("indigenous civilization", res.message)
        self.assertIsNone(indigenous.owner_id)

    def test_tax_collection(self):
        """Collecting taxes empties the treasury and credits the player."""
        self.planet.owner_id = "emperor"
        self.planet.treasury = 2500
        initial_cr = self.player.credits

        res = self.kernel.dispatch("emperor", ActionType.PLANET_TAX, planet_id=self.planet.id)
        self.assertTrue(res.success)
        # Sovereign levy: the governor draws 20% of the vault; the rest runs the colony
        from xylarium.kernel.fx import balance
        self.assertEqual(balance(self.player, self.planet.currency) - (initial_cr if self.planet.currency == "SOL" else 0), 500)
        # ...and only once per fiscal quarter
        self.assertFalse(self.kernel.dispatch("emperor", ActionType.PLANET_TAX, planet_id=self.planet.id).success)

    def test_invest_population_growth(self):
        """Investing credits increases planetary population."""
        self.planet.owner_id = "emperor"
        self.planet.habitats = 2              # enclosed farms, so the world can feed newcomers
        initial_pop = self.planet.population

        res = self.kernel.dispatch("emperor", ActionType.PLANET_INVEST, planet_id=self.planet.id, credits=1000)
        self.assertTrue(res.success)
        self.assertGreater(self.planet.population, initial_pop)

    def test_build_planetary_shields(self):
        """Building shields consumes credits/ore and raises shield grid."""
        self.planet.owner_id = "emperor"
        self.planet.shields = 50
        self.planet.max_shields = 200
        self.planet.ore_silo = 50

        res = self.kernel.dispatch("emperor", ActionType.PLANET_BUILD_SHIELD, planet_id=self.planet.id, points=50)
        self.assertTrue(res.success)
        self.assertEqual(self.planet.shields, 100)

    def test_upgrade_citadel_tier(self):
        """Advancing Citadel Tier increases max shields and defense caps."""
        self.planet.owner_id = "emperor"
        self.planet.citadel_level = 0
        self.planet.ore_silo = 100
        self.player.credits = 10000

        res = self.kernel.dispatch("emperor", ActionType.PLANET_UPGRADE_CITADEL, planet_id=self.planet.id)
        self.assertTrue(res.success)
        self.assertEqual(self.planet.citadel_level, 1)
        self.assertEqual(self.planet.max_shields, 500)

    def test_colony_turn_tick_yield(self):
        """World simulation ticks produce taxes and resources."""
        self.planet.owner_id = "emperor"
        self.planet.treasury = 1000   # Citadel upkeep must be funded for taxes to accrue
        self.planet.population = 2000
        self.planet.element_deposits["ORE"] = 10_000   # a crust to mine

        yield_data = ColonyManager.tick_colony(self.planet)
        self.assertTrue(yield_data["upkeep_paid"])
        self.assertGreater(yield_data["tax_yield"], 0)
        # Vault moves by the net budget: gross tax minus public services, after citadel upkeep
        upkeep = CITADEL_UPKEEP[self.planet.citadel_level]["credits"]
        self.assertEqual(self.planet.treasury,
                         1000 - upkeep + yield_data["tax_yield"] - yield_data["public_services"])
        self.assertGreater(self.planet.ore_silo, 0)
        self.assertGreater(yield_data["tax_yield"], 0)


class TestCombat(unittest.TestCase):
    """Test Tactical Combat & Orbital Sieges."""

    def setUp(self):
        self.kernel = GameKernel(seed=555)
        self.player = self.kernel.register_player("warrior", "Warrior")
        self.player.credits = 10000

    def test_federation_combat_prohibited(self):
        """Attacking in Sector 1 (Federation) is repelled by FedNav."""
        self.player.sector_id = 1
        # Place target in Sector 1
        target = self.kernel.captains["ai_vane"]
        target.sector_id = 1
        self.kernel.sectors[1].captains.append(target.id)

        res = self.kernel.dispatch("warrior", ActionType.ATTACK_SHIP, target_id="ai_vane")
        self.assertFalse(res.success)
        self.assertIn("FEDNAV ALERT", res.message)

    def test_ship_combat_in_anarchy(self):
        """Combat in Anarchy sectors resolves tactical exchanges."""
        self.player.sector_id = 80
        self.player.ship.fighters = 50
        self.player.ship.shields = 200

        target = self.kernel.captains["ai_malakor"]
        target.sector_id = 80
        self.kernel.sectors[80].captains.append(target.id)

        res = self.kernel.dispatch("warrior", ActionType.ATTACK_SHIP, target_id="ai_malakor")
        self.assertTrue(res.success)
        self.assertEqual(res.turns_spent, 2)
        self.assertIn("TACTICAL ENGAGEMENT", res.logs[0])


class TestAICaptains(unittest.TestCase):
    """Test 4: Autonomous AI Rival Captains."""

    def setUp(self):
        self.kernel = GameKernel(seed=777)
        self.player = self.kernel.register_player("solo", "Solo")

    def test_ai_captains_instantiated(self):
        """Verify 4 distinct rival captains exist in the universe."""
        ai_captains = [c for c in self.kernel.captains.values() if c.is_ai]
        self.assertEqual(len(ai_captains), 4)

        personalities = {c.personality for c in ai_captains}
        self.assertIn(AIPersonality.TRADER, personalities)
        self.assertIn(AIPersonality.PIRATE, personalities)
        self.assertIn(AIPersonality.INDUSTRIALIST, personalities)
        self.assertIn(AIPersonality.MERCENARY, personalities)

    def test_ai_simulation_ticks_execute(self):
        """Advancing the simulation executes AI turns without errors."""
        initial_cycle = self.kernel.cycle_count
        # Trigger world ticks
        for _ in range(5):
            self.kernel.tick_simulation()

        self.assertEqual(self.kernel.cycle_count, initial_cycle + 5)
        # Verify radio chatter has messages
        radio_msgs = self.kernel.event_bus.get_recent_radio(10)
        self.assertGreater(len(radio_msgs), 0)


class TestPersistence(unittest.TestCase):
    """Test 5 & 6: Save / Load State Persistence."""

    def test_save_and_load(self):
        kernel = GameKernel(seed=888)
        player = kernel.register_player("starbuck", "Starbuck")
        player.credits = 12345
        player.sector_id = 42

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            filepath = tf.name

        try:
            saved = StatePersistence.save_to_file(kernel, filepath)
            self.assertTrue(saved)

            restored = StatePersistence.load_from_file(filepath)
            self.assertIsNotNone(restored)
            self.assertEqual(len(restored.sectors), len(kernel.sectors))
            restored_player = restored.get_player("starbuck")
            self.assertIsNotNone(restored_player)
            self.assertEqual(restored_player.credits, 12345)
            self.assertEqual(restored_player.sector_id, 42)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


class TestTerminalRenderer(unittest.TestCase):
    """Test 1: Terminal / ASCII HUD and screens."""

    def test_hud_rendering(self):
        kernel = GameKernel(seed=999)
        kernel.register_player("pilot", "Pilot")
        view = kernel.get_player_view("pilot")

        hud_output = TerminalRenderer.render_hud(view)
        self.assertIn("XYLARIUM BBS", hud_output)
        self.assertIn("Sector:", hud_output)
        self.assertIn("001", hud_output)
        self.assertIn("Turns:", hud_output)
        self.assertIn("Credits:", hud_output)

        sector_output = TerminalRenderer.render_sector(view)
        self.assertIn("SECTOR", sector_output)
        self.assertIn("Wormhole Warps:", sector_output)
        self.assertIn("TRADE PORT", sector_output)

    def test_categorized_port_rendering(self):
        kernel = GameKernel(seed=42)
        kernel.register_player("pilot", "Pilot")
        view = kernel.get_player_view("pilot")

        import re
        strip_ansi = lambda s: re.sub(r'\x1b\[[0-9;]*m', '', s)

        # Page 0 (Default)
        sec_output_p0 = TerminalRenderer.render_sector(view, category_page=0)
        p0_clean = strip_ansi(sec_output_p0)
        self.assertIn("[1] VOLATILES & GASES:", p0_clean)
        self.assertIn("Hydrogen Fuel", p0_clean)
        self.assertIn("[2] STRUCTURAL METALS & ALLOYS:", p0_clean)
        self.assertIn("Raw Iron Ore", p0_clean)
        self.assertIn("[3] FISSIONABLES & EXOTICS: (Press [N] for Next Category)", p0_clean)

        # Tabular alignment check: ensure bullet, name, mode, price, stock
        self.assertIn("• Hydrogen Fuel      : BUYS @  8 Cr  (Stock: 850)", p0_clean)
        self.assertIn("• Raw Iron Ore       : BUYS @ 12 Cr  (Stock: 850)", p0_clean)

        # Ensure no line in the trade port section exceeds 80 columns
        port_lines = [l for l in p0_clean.split("\n") if "BUYS" in l or "SELLS" in l or "TRADE PORT" in l or "VOLATILES" in l or "METALS" in l or "----" in l]
        for line in port_lines:
            self.assertLessEqual(len(line), 80, f"Port line exceeds 80 characters: {line}")

        # Page 1
        sec_output_p1 = TerminalRenderer.render_sector(view, category_page=1)
        p1_clean = strip_ansi(sec_output_p1)
        self.assertIn("[3] FISSIONABLES & EXOTICS:", p1_clean)
        self.assertIn("Enriched Uranium", p1_clean)
        self.assertIn("[4] MANUFACTURED COMPONENTS:", p1_clean)
        self.assertIn("[5] CORE TRI-COMMODITIES: (Press [N] for Next Category)", p1_clean)

        # Page 2
        sec_output_p2 = TerminalRenderer.render_sector(view, category_page=2)
        p2_clean = strip_ansi(sec_output_p2)
        self.assertIn("[5] CORE TRI-COMMODITIES:", p2_clean)
        self.assertIn("Ore", p2_clean)
        self.assertIn("[1] VOLATILES & GASES: (Press [N] for Next Category)", p2_clean)

    def test_sector_without_port_rendering(self):
        kernel = GameKernel(seed=42)
        kernel.register_player("pilot", "Pilot")
        # Sector 9 has no trade port
        kernel.dispatch("pilot", ActionType.MOVE, destination=9)
        view = kernel.get_player_view("pilot")

        sector_output = TerminalRenderer.render_sector(view)
        self.assertIn("No trade port in this sector", sector_output)


if __name__ == "__main__":
    unittest.main()
