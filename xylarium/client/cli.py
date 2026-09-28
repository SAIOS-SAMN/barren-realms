"""
Interactive Terminal Client for Xylarium.
Provides classic BBS door game loop with letter/number-based command dispatch.
"""

import sys
import os
from typing import Optional, Dict, Any, List
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType
from xylarium.client.ansi import (
    TITLE_BANNER, c_cyan, c_gold, c_green, c_red, c_magenta, c_white, c_gray, bold
)
from xylarium.client.renderer import TerminalRenderer
from xylarium.persistence.store import StatePersistence


class TerminalClient:
    """Manages the interactive terminal loop and player input dispatch."""

    def __init__(self, kernel: GameKernel, player_id: str = "player_1", save_file: str = "xylarium_save.json"):
        self.kernel = kernel
        self.player_id = player_id
        self.save_file = save_file
        self.running = True

    def clear_screen(self) -> None:
        """Clear terminal screen for clean BBS redraws."""
        # Print ANSI clear code
        print("\033[2J\033[H", end="")

    def run(self) -> None:
        """Main game loop."""
        self.clear_screen()
        print(TITLE_BANNER)
        print(f"Booting Xylarium BBS Kernel... Welcome, Captain {self.kernel.get_player(self.player_id).name}!\n")

        while self.running:
            view = self.kernel.get_player_view(self.player_id)
            if not view:
                print(c_red("Error: Player session lost."))
                break

            # Render Persistent HUD and Sector scan
            print(TerminalRenderer.render_hud(view))
            print(TerminalRenderer.render_sector(view))

            # Render Command Prompt
            self._prompt_action(view)

    def _prompt_action(self, view: Dict[str, Any]) -> None:
        """Displays main command prompt and dispatches player selection."""
        sector = view.get("sector", {})
        has_port = sector.get("port") is not None
        has_planets = len(sector.get("planets", [])) > 0
        has_captains = len(sector.get("captains", [])) > 0
        in_fed_central = (sector.get("id") == 1)

        # Build options
        opts = [
            f"{c_gold('[M]')}ove",
            f"{c_gold('[T]')}rade" if has_port else f"{c_gray('[T]rade')}",
            f"{c_gold('[P]')}lanet" if has_planets else f"{c_gray('[P]lanet')}",
            f"{c_gold('[A]')}ttack" if (has_captains or has_planets) else f"{c_gray('[A]ttack')}",
            f"{c_gold('[S]')}hipyard" if in_fed_central else f"{c_gray('[S]hipyard')}",
            f"{c_gold('[C]')}omputer",
            f"{c_gold('[R]')}adio",
            f"{c_gold('[H]')}elp",
            f"{c_gold('[Q]')}uit"
        ]

        print(f"\n{bold(c_cyan('Command Dispatch:'))} " + " │ ".join(opts))
        try:
            choice = input(f"{bold(c_white('Command [M/T/P/A/S/C/R/H/Q] > '))}").strip().upper()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Xylarium...")
            self.running = False
            return

        if not choice:
            return

        # Direct sector number entry (e.g. user just types "42" to move to Sector 42)
        if choice.isdigit():
            dest = int(choice)
            self._do_move(dest)
            return

        cmd = choice[0]
        if cmd == "M" or choice == "1":
            self._prompt_move(view)
        elif cmd == "T" or choice == "2":
            self._prompt_trade(view)
        elif cmd == "P" or choice == "3":
            self._prompt_planet(view)
        elif cmd == "A" or choice == "4":
            self._prompt_attack(view)
        elif cmd == "S" or choice == "5":
            self._prompt_shipyard(view)
        elif cmd == "C" or choice == "6":
            self._prompt_nav_computer(view)
        elif cmd == "R" or choice == "7":
            self._prompt_radio()
        elif cmd == "H" or choice == "8":
            self.clear_screen()
            print(TerminalRenderer.render_help())
            input(c_gold("Press Enter to return to navigation..."))
            self.clear_screen()
        elif cmd == "Q" or choice == "9":
            self._do_quit()
        else:
            print(c_red(f"Unknown command: '{choice}'. Type 'H' for help."))

    def _prompt_move(self, view: Dict[str, Any]) -> None:
        """Handle move command."""
        warps = view.get("sector", {}).get("warps", [])
        warp_ids = [w["sector_id"] for w in warps]
        warp_list_str = ", ".join([f"{w:03d}" for w in warp_ids])
        try:
            dest_str = input(f"Warp destination [{warp_list_str}] (or Enter to cancel): ").strip()
            if not dest_str:
                return
            if not dest_str.isdigit():
                print(c_red("Destination must be a sector number."))
                return
            dest = int(dest_str)
            self._do_move(dest)
        except (KeyboardInterrupt, EOFError):
            return

    def _do_move(self, dest: int) -> None:
        result = self.kernel.dispatch(self.player_id, ActionType.MOVE, destination=dest)
        if not result.success:
            print(c_red(f"Navigation Error: {result.message}"))
        else:
            self.clear_screen()
            print(c_green(f"✔ {result.message}"))

    def _prompt_trade(self, view: Dict[str, Any]) -> None:
        """Handle port trading loop."""
        sector = view.get("sector", {})
        if not sector.get("port"):
            print(c_red("No trade port in this sector!"))
            return

        while True:
            view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_trade_screen(view))
            try:
                cmd = input(f"{c_gold('Trade Command [B/S/X] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd or cmd == "X" or cmd == "EXIT" or cmd == "Q":
                self.clear_screen()
                break

            parts = cmd.split()
            action = parts[0]
            if action in ["B", "BUY"] and len(parts) >= 3:
                comm = self._normalize_commodity(parts[1])
                try:
                    amt = int(parts[2])
                    res = self.kernel.dispatch(self.player_id, ActionType.TRADE, type="BUY", commodity=comm, amount=amt)
                    if res.success:
                        print(c_green(f"✔ {res.message}"))
                    else:
                        print(c_red(f"Trade Denied: {res.message}"))
                except ValueError:
                    print(c_red("Amount must be an integer."))
            elif action in ["S", "SELL"] and len(parts) >= 3:
                comm = self._normalize_commodity(parts[1])
                try:
                    amt = int(parts[2])
                    res = self.kernel.dispatch(self.player_id, ActionType.TRADE, type="SELL", commodity=comm, amount=amt)
                    if res.success:
                        print(c_green(f"✔ {res.message}"))
                    else:
                        print(c_red(f"Trade Denied: {res.message}"))
                except ValueError:
                    print(c_red("Amount must be an integer."))
            else:
                print(c_gold("Usage: B <commodity> <amount>  e.g. 'B ORE 10' or 'S ORGANICS 20'"))

    def _normalize_commodity(self, text: str) -> str:
        text = text.upper()
        if text.startswith("OR") and not text.startswith("ORE"):
            return "ORGANICS"
        elif text.startswith("ORE") or text == "1":
            return "ORE"
        elif text.startswith("ORG") or text == "2":
            return "ORGANICS"
        elif text.startswith("EQ") or text == "3":
            return "EQUIPMENT"
        return text

    def _prompt_planet(self, view: Dict[str, Any]) -> None:
        """Handle planetary colonization and management loop."""
        planets = view.get("sector", {}).get("planets", [])
        if not planets:
            print(c_red("No planetary bodies present in this sector."))
            return

        planet = planets[0]
        while True:
            # Refresh planet data from view
            fresh_view = self.kernel.get_player_view(self.player_id)
            planet_list = fresh_view.get("sector", {}).get("planets", [])
            if not planet_list:
                break
            planet = planet_list[0]

            print(TerminalRenderer.render_planet_screen(fresh_view, planet))
            try:
                p_cmd = input(f"{c_gold('Colony Command > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not p_cmd or p_cmd in ["B", "BACK", "X", "EXIT"]:
                self.clear_screen()
                break

            action_key = p_cmd[0]
            if action_key == "C":
                res = self.kernel.dispatch(self.player_id, ActionType.PLANET_CLAIM, planet_id=planet["id"])
                self._print_result(res)
            elif action_key == "T":
                res = self.kernel.dispatch(self.player_id, ActionType.PLANET_TAX, planet_id=planet["id"])
                self._print_result(res)
            elif action_key == "I":
                try:
                    cr_str = input("Credits to invest in population: ").strip()
                    cr = int(cr_str)
                    res = self.kernel.dispatch(self.player_id, ActionType.PLANET_INVEST, planet_id=planet["id"], credits=cr)
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid credit amount."))
            elif action_key == "S":
                try:
                    pts_str = input("Shield points to build (10 Cr + 0.1 Ore/pt): ").strip()
                    pts = int(pts_str)
                    res = self.kernel.dispatch(self.player_id, ActionType.PLANET_BUILD_SHIELD, planet_id=planet["id"], points=pts)
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid shield amount."))
            elif action_key == "F":
                try:
                    f_str = input("Defense fighters to recruit (60 Cr/ea): ").strip()
                    cnt = int(f_str)
                    res = self.kernel.dispatch(self.player_id, ActionType.PLANET_RECRUIT_FIGHTERS, planet_id=planet["id"], count=cnt)
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid count."))
            elif action_key == "U":
                res = self.kernel.dispatch(self.player_id, ActionType.PLANET_UPGRADE_CITADEL, planet_id=planet["id"])
                self._print_result(res)
            elif action_key == "D":
                try:
                    comm = input("Commodity to deposit (ORE/ORGANICS): ").strip().upper()
                    amt = int(input(f"Amount of {comm} to transfer to planet silo: ").strip())
                    res = self.kernel.dispatch(self.player_id, ActionType.PLANET_CARGO_TRANSFER, planet_id=planet["id"], commodity=comm, direction="to_planet", amount=amt)
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid amount."))
            elif action_key == "W":
                try:
                    comm = input("Commodity to withdraw (ORE/ORGANICS): ").strip().upper()
                    amt = int(input(f"Amount of {comm} to load into ship hold: ").strip())
                    res = self.kernel.dispatch(self.player_id, ActionType.PLANET_CARGO_TRANSFER, planet_id=planet["id"], commodity=comm, direction="to_ship", amount=amt)
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid amount."))
            elif action_key == "A":
                res = self.kernel.dispatch(self.player_id, ActionType.ATTACK_PLANET, planet_id=planet["id"])
                self._print_result(res)
            else:
                print(c_red("Invalid colony command option."))

    def _prompt_attack(self, view: Dict[str, Any]) -> None:
        """Handle tactical combat against rival captains or planets."""
        captains = view.get("sector", {}).get("captains", [])
        planets = view.get("sector", {}).get("planets", [])

        if not captains and not planets:
            print(c_red("No target vessels or planetary colonies to engage in this sector."))
            return

        print(bold(c_red("\n--- TACTICAL TARGET ACQUISITION ---")))
        target_list = []
        idx = 1
        for c in captains:
            print(f"  [{idx}] Attack Ship: {c['name']} ({c['ship_type']} - Shields: {c['shields']}, Fighters: {c['fighters']})")
            target_list.append(("SHIP", c["id"]))
            idx += 1
        for p in planets:
            if p.get("owner_id") != self.player_id:
                print(f"  [{idx}] Bombard Colony: {p['name']} (Owner: {p.get('owner_id', 'Uninhabited')})")
                target_list.append(("PLANET", p["id"]))
                idx += 1

        try:
            sel = input(f"Select target [1-{len(target_list)}] (or Enter to disengage): ").strip()
            if not sel or not sel.isdigit():
                return
            target_idx = int(sel) - 1
            if 0 <= target_idx < len(target_list):
                t_type, t_id = target_list[target_idx]
                if t_type == "SHIP":
                    res = self.kernel.dispatch(self.player_id, ActionType.ATTACK_SHIP, target_id=t_id)
                else:
                    res = self.kernel.dispatch(self.player_id, ActionType.ATTACK_PLANET, planet_id=t_id)
                self._print_result(res)
            else:
                print(c_red("Invalid selection."))
        except (KeyboardInterrupt, EOFError):
            return

    def _prompt_shipyard(self, view: Dict[str, Any]) -> None:
        """Handle Federation Shipyard operations in Sector 1."""
        if view.get("sector", {}).get("id") != 1:
            print(c_red("The Federation Shipyard is located exclusively at Sol Central (Sector 1)."))
            return

        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_shipyard_screen(fresh_view))
            try:
                choice = input(f"{c_gold('Shipyard Order [1-5 / B] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not choice or choice in ["B", "BACK", "X", "EXIT"]:
                self.clear_screen()
                break

            if choice == "1":
                res = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="shields")
                self._print_result(res)
            elif choice == "2":
                try:
                    f_qty = int(input("Quantity of fighters to purchase (45 Cr/ea): ").strip())
                    res = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="fighters", amount=f_qty)
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid quantity."))
            elif choice == "3":
                res = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Scout Ship")
                self._print_result(res)
            elif choice == "4":
                res = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Merchant Cruiser")
                self._print_result(res)
            elif choice == "5":
                res = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Star Frigate")
                self._print_result(res)
            elif choice == "6":
                res = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Dreadnought Battlecruiser")
                self._print_result(res)
            else:
                print(c_red("Invalid shipyard order."))

    def _prompt_nav_computer(self, view: Dict[str, Any]) -> None:
        """Handle BFS navigation computer pathfinding."""
        curr_sec = view.get("sector", {}).get("id", 1)
        try:
            target_str = input(f"Destination Sector for BFS Course Plot [1-100] (Current: {curr_sec:03d}): ").strip()
            if not target_str or not target_str.isdigit():
                return
            target = int(target_str)
            if not (1 <= target <= 100):
                print(c_red("Sector ID must be between 1 and 100."))
                return

            path = self.kernel.find_path(curr_sec, target)
            print(TerminalRenderer.render_nav_computer(curr_sec, target, path))
            input(c_gold("Press Enter to continue..."))
        except (KeyboardInterrupt, EOFError):
            return

    def _prompt_radio(self) -> None:
        """Handle sending a subspace radio broadcast."""
        try:
            msg = input(f"{c_cyan('Subspace Radio Broadcast > ')}").strip()
            if msg:
                res = self.kernel.dispatch(self.player_id, ActionType.RADIO_BROADCAST, text=msg)
                print(c_green("✔ Broadcast dispatched across subspace channels."))
        except (KeyboardInterrupt, EOFError):
            return

    def _print_result(self, res) -> None:
        """Helper to print ActionResult status."""
        if res.logs:
            for l in res.logs:
                print(c_cyan("» ") + l)
        elif res.message:
            color = c_green if res.success else c_red
            print(color(res.message))

    def _do_quit(self) -> None:
        """Save and terminate."""
        print("\nSaving sector data and captain logs...")
        saved = StatePersistence.save_to_file(self.kernel, self.save_file)
        if saved:
            print(c_green(f"✔ State successfully saved to {self.save_file}."))
        else:
            print(c_red("Warning: Could not write save state."))
        print(bold(c_gold("Thank you for playing Xylarium: The Barren Realms! Transmission terminated.")))
        self.running = False
