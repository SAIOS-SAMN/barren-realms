"""
Regression tests for single-lineage kernels (Lineage Genesis, backup clones, seat succession,
extinction and the Hall of Lineages) and the dual command modes (Fly Ship vs Empire).
"""

import builtins
import io
import os
import random
import tempfile
import unittest
from contextlib import redirect_stdout

from xylarium.config import LINEAGE_CLONE_PRICE, LINEAGE_MAX_CLONES, LINEAGE_START_CLONES
from xylarium.kernel import lineage
from xylarium.kernel.combat import _eject_to_sol
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply
from xylarium.kernel.models import ActionType
from xylarium.persistence.store import StatePersistence


def _single_kernel(tmp: str, seed: int = 42) -> GameKernel:
    kernel = GameKernel(seed=seed)
    kernel.single_lineage = True
    kernel.legacy_file = os.path.join(tmp, "hall.json")
    kernel.register_player("player_1", "Ada Vance", clade="LITHIC", bind_lineage=True)
    return kernel


class TestSingleLineageKernel(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.tmp = tempfile.mkdtemp()
        self.kernel = _single_kernel(self.tmp)
        self.cap = self.kernel.get_player("player_1")

    def test_genesis_binds_exactly_one_lineage(self):
        lin = self.kernel.lineage
        self.assertEqual(lin["player_id"], "player_1")
        self.assertEqual(lin["clade"], "LITHIC")
        self.assertEqual(lin["clones"], LINEAGE_START_CLONES)
        with self.assertRaises(lineage.LineageLocked):
            self.kernel.register_player("player_2", "Interloper")

    def test_multi_captain_kernels_are_unaffected(self):
        kernel = GameKernel(seed=42)
        kernel.register_player("a", "A")
        kernel.register_player("b", "B")
        self.assertIsNone(kernel.lineage)

    def test_hull_losses_spend_clones_then_end_the_lineage(self):
        for expected in range(LINEAGE_START_CLONES - 1, -1, -1):
            _eject_to_sol(self.cap, self.kernel)
            self.assertEqual(self.kernel.lineage["clones"], expected)
            self.assertEqual(self.kernel.lineage["status"], "ACTIVE")
        _eject_to_sol(self.cap, self.kernel)
        lin = self.kernel.lineage
        self.assertEqual(lin["status"], "EXTINCT")
        self.assertIn("no backup clones", lin["cause"])
        self.assertIn("HERE ENDS THE HOUSE OF VANCE", lin["epitaph"])
        self.assertEqual(self.kernel.chronicle.entries[-1]["kind"], "LINEAGE_LEGACY")
        res = self.kernel.dispatch("player_1", ActionType.MOVE, destination=self.kernel.sectors[1].warps[0])
        self.assertFalse(res.success)
        self.assertIn("has ended", res.message)
        self.assertTrue(self.kernel.dispatch("player_1", ActionType.LIBRARY_BROWSE).success)
        # The Hall of Lineages outlives the kernel: a new universe's Library remembers
        hall = lineage.load_hall(self.kernel.legacy_file)
        self.assertEqual(len(hall), 1)
        fresh = GameKernel(seed=7)
        self.assertEqual(lineage.import_hall(fresh, self.kernel.legacy_file), 1)
        self.assertEqual(fresh.chronicle.entries[-1]["kind"], "LINEAGE_LEGACY")

    def test_fallen_home_colony_moves_the_seat_or_ends_the_lineage(self):
        worlds = [p for s in self.kernel.sectors.values() for p in s.planets
                  if p.owner_id is None and p.population == 0 and not p.natives and not p.faction_id][:2]
        for w in worlds:
            w.owner_id = "player_1"
            w.population = 500
        lineage.on_colony_founded(self.kernel, self.cap, worlds[0])
        self.assertEqual(self.kernel.lineage["home_colony"], worlds[0].id)
        worlds[0].owner_id = "ai_malakor"
        self.assertIn("SEAT TRANSFERRED", lineage.check_seat(self.kernel))
        self.assertEqual(self.kernel.lineage["home_colony"], worlds[1].id)
        worlds[1].owner_id = "ai_malakor"
        self.assertIn("EXTINCTION", lineage.check_seat(self.kernel))
        self.assertEqual(self.kernel.lineage["status"], "EXTINCT")

    def test_backup_clones_are_grown_at_sol_and_paid_to_the_stardock(self):
        self.cap.credits = LINEAGE_CLONE_PRICE * 3
        before = {c: b["total"] for c, b in money_supply(self.kernel).items()}
        res = self.kernel.dispatch("player_1", ActionType.SHIPYARD_PURCHASE, item="clone")
        self.assertTrue(res.success, res.message)
        self.assertEqual(self.kernel.lineage["clones"], LINEAGE_START_CLONES + 1)
        after = {c: b["total"] for c, b in money_supply(self.kernel).items()}
        self.assertEqual(before["SOL"], after["SOL"])  # a transfer to the stardock, not a burn
        self.kernel.lineage["clones"] = LINEAGE_MAX_CLONES
        self.assertFalse(self.kernel.dispatch("player_1", ActionType.SHIPYARD_PURCHASE, item="clone").success)

    def test_retirement_needs_confirmation_and_seals_the_record(self):
        self.assertFalse(self.kernel.dispatch("player_1", ActionType.RETIRE_LINEAGE).success)
        res = self.kernel.dispatch("player_1", ActionType.RETIRE_LINEAGE, confirm=True)
        self.assertTrue(res.success)
        self.assertEqual(self.kernel.lineage["status"], "RETIRED")

    def test_lineage_and_mode_survive_save_and_load(self):
        self.kernel.set_command_mode("player_1", "EMPIRE")
        path = os.path.join(self.tmp, "save.json")
        self.assertTrue(StatePersistence.save_to_file(self.kernel, path))
        loaded = StatePersistence.load_from_file(path)
        self.assertTrue(loaded.single_lineage)
        self.assertEqual(loaded.lineage["house"], "House of Vance")
        self.assertEqual(loaded.get_player("player_1").command_mode, "EMPIRE")
        with self.assertRaises(lineage.LineageLocked):
            loaded.register_player("player_2", "Interloper")


class TestEmpireMode(unittest.TestCase):
    def setUp(self):
        random.seed(9)
        self.tmp = tempfile.mkdtemp()
        self.kernel = _single_kernel(self.tmp)

    def test_dashboard_covers_the_five_sovereign_categories(self):
        dash = self.kernel.empire_dashboard("player_1")
        for key in ("colonies", "fleets", "routes", "diplomacy", "treasury", "rivals", "lineage"):
            self.assertIn(key, dash)
        self.assertNotIn("player_1", [r["id"] for r in dash["rivals"]])
        self.assertTrue(any(p["id"] == "IMPERIUM" for p in dash["diplomacy"]["powers"]))

    def test_mode_toggle_is_validated(self):
        self.assertTrue(self.kernel.set_command_mode("player_1", "empire"))
        self.assertEqual(self.kernel.get_player_view("player_1")["mode"], "EMPIRE")
        self.assertFalse(self.kernel.set_command_mode("player_1", "GODMODE"))

    def test_terminal_client_walks_both_modes(self):
        from xylarium.client.cli import TerminalClient
        client = TerminalClient(self.kernel, "player_1", save_file=os.path.join(self.tmp, "cli.json"))
        client.clear_screen = lambda: None
        script = iter(["E", "1", "", "2", "", "3", "", "4", "", "5", "", "F", "Q"])
        real_input = builtins.input
        builtins.input = lambda prompt="": next(script)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                client.run()
        finally:
            builtins.input = real_input
        out = buf.getvalue()
        self.assertIn("SOVEREIGN COMMAND OF THE HOUSE OF VANCE", out)
        for card in ("COLONIES & PLANETARY WORLDS", "FLEETS & SHIP ASSIGNMENTS", "TRADE ROUTES & ARBITRAGE",
                     "DIPLOMACY, POWERS & WARS", "TREASURY & FINANCIAL VAULTS"):
            self.assertIn(card, out)
        self.assertEqual(self.kernel.get_player("player_1").command_mode, "FLY")


if __name__ == "__main__":
    unittest.main()


class TestNpcLineages(unittest.TestCase):
    def setUp(self):
        random.seed(21)
        self.kernel = GameKernel(seed=42)

    def test_founding_houses_are_seated_at_genesis(self):
        names = {h["name"] for h in self.kernel.npc_lineages.values()}
        self.assertIn("House Malakor", names)
        self.assertEqual(self.kernel.captains["ai_malakor"].house_id,
                         next(h["id"] for h in self.kernel.npc_lineages.values() if h["name"] == "House Malakor"))
        self.assertEqual(lineage.house_of(self.kernel, self.kernel.captains["ai_malakor"])["creed"], "outlaw")

    def test_cleaved_offshoots_are_cadet_branches_of_their_house(self):
        from xylarium.kernel.ai import AIManager
        vane = self.kernel.captains["ai_vane"]
        vane.credits = 50000
        vane.grown_basis = [{}] * 30
        child = AIManager.check_cognitive_cleaving(self.kernel, vane)
        self.assertIsNotNone(child)
        self.assertEqual(child.house_id, vane.house_id)
        house = lineage.house_of(self.kernel, vane)
        self.assertEqual(house["branches"], 1)
        self.assertEqual(house["generation"], 2)

    def test_a_member_lost_with_empty_vats_dies_and_the_estate_passes_on(self):
        malakor = self.kernel.captains["ai_malakor"]
        house = lineage.house_of(self.kernel, malakor)
        worlds = self.kernel.get_planets_owned_by(malakor.id)
        before = {c: b["total"] for c, b in money_supply(self.kernel).items()}
        house["clones"] = 0
        _eject_to_sol(malakor, self.kernel)
        lineage.npc_tick(self.kernel)
        self.assertNotIn("ai_malakor", self.kernel.captains)
        self.assertEqual(house["status"], "EXTINCT")          # a house of one: its only member fell
        self.assertIn("HERE ENDS HOUSE MALAKOR", house["epitaph"])
        for w in worlds:
            self.assertIsNone(w.owner_id)                      # no heir: the worlds go free
            self.assertIsNotNone(w.civilization)
        after = {c: b["total"] for c, b in money_supply(self.kernel).items()}
        self.assertEqual(before["SOL"], after["SOL"])          # the purse escheats to the Reserve, not destroyed
        self.assertEqual(self.kernel.chronicle.entries[-1]["kind"], "LINEAGE_LEGACY")

    def test_a_house_survives_while_an_heir_lives(self):
        from xylarium.kernel.ai import AIManager
        vane = self.kernel.captains["ai_vane"]
        vane.credits = 50000
        vane.grown_basis = [{}] * 30
        child = AIManager.check_cognitive_cleaving(self.kernel, vane)
        house = lineage.house_of(self.kernel, vane)
        house["clones"] = 0
        heir_before = child.credits
        _eject_to_sol(vane, self.kernel)
        purse = vane.credits  # after any hull-insurance claim
        lineage.npc_tick(self.kernel)
        self.assertNotIn("ai_vane", self.kernel.captains)
        self.assertEqual(house["status"], "ACTIVE")
        self.assertEqual(child.credits, heir_before + purse)

    def test_outlaw_creed_keeps_pirates_raiding(self):
        from xylarium.kernel.ai import AIManager
        malakor = self.kernel.captains["ai_malakor"]
        malakor.cosmic_alignment = 0.0
        sec = next(s for s in self.kernel.sectors.values() if s.is_protected_space and s.security.value != "FEDERATION")
        mark = self.kernel.register_player("mark", "Mark")
        for c in (malakor, mark):
            self.kernel.sectors[c.sector_id].captains.remove(c.id)
            c.sector_id = sec.id
            sec.captains.append(c.id)
        mark.credits = 10000
        mark.ship.fighters = 1
        malakor.ship.fighters = 80
        self.assertTrue(AIManager._keep_outlaw_creed(self.kernel, malakor, sec))
        self.assertLess(mark.credits, 10000)                   # shaken down, not shot, under the port's guns
        self.assertLess(malakor.cosmic_alignment, 0.0)


class TestVoidCorsairs(unittest.TestCase):
    def test_the_void_breeds_a_new_outlaw_house_when_none_survive(self):
        random.seed(3)
        kernel = GameKernel(seed=42)
        for h in kernel.npc_lineages.values():
            if h["creed"] == "outlaw":
                for m in list(h["members"]):
                    kernel.captains[m].alignment_record["house_death"] = "test"
        kernel.cycle_count = 500
        before = {c: b["total"] for c, b in money_supply(kernel).items()}
        lineage.npc_tick(kernel)
        outlaws = [h for h in kernel.npc_lineages.values() if h["creed"] == "outlaw" and h["status"] == "ACTIVE"]
        self.assertEqual(len(outlaws), 1)
        self.assertEqual(outlaws[0]["origin"], "void")
        after = {c: b["total"] for c, b in money_supply(kernel).items()}
        self.assertEqual(before, after)  # a salvaged hull and an empty purse: nothing minted
