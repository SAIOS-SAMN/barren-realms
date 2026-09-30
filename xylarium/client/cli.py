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
from xylarium.kernel.routes import TradeRouteOptimizer
from xylarium.persistence.store import StatePersistence


class TerminalClient:
    """Manages the interactive terminal loop and player input dispatch."""

    def __init__(
        self,
        kernel: GameKernel,
        player_id: str = "player_1",
        player_name: str = "Captain Solo",
        save_file: str = "xylarium_save.json"
    ):
        self.kernel = kernel
        self.save_file = save_file
        self.running = True

        # Ensure player exists in kernel
        player = self.kernel.get_player(player_id)
        if not player:
            human_caps = [c for c in self.kernel.captains.values() if not c.is_ai]
            if human_caps:
                self.player_id = human_caps[0].id
            else:
                self.player_id = player_id
                self.kernel.register_player(player_id=self.player_id, player_name=player_name)
        else:
            self.player_id = player_id
        self.port_cat_page = 0

    def clear_screen(self) -> None:
        """Clear terminal screen for clean BBS redraws."""
        # Print ANSI clear code
        print("\033[2J\033[H", end="")

    def run(self) -> None:
        """Main game loop."""
        self.clear_screen()
        print(TITLE_BANNER)
        player = self.kernel.get_player(self.player_id)
        if not player:
            player = self.kernel.register_player(self.player_id, "Captain Solo")
        pname = player.name if player else "Captain"
        print(f"Booting Xylarium BBS Kernel... Welcome, Captain {pname}!\n")

        while self.running:
            view = self.kernel.get_player_view(self.player_id)
            if not view:
                print(c_red("Error: Player session lost."))
                break

            # A lineage that has ended commands nothing: read its epitaph, then begin anew
            lin = view.get("lineage")
            if lin and lin.get("status") != "ACTIVE":
                self._lineage_ended(lin)
                continue

            print(TerminalRenderer.render_hud(view))
            if view.get("mode") == "EMPIRE":
                # Empire Building Mode: the sovereign dashboard, no cockpit clutter
                self._empire_mode(view)
                continue

            # Fly Ship Mode: the tactical cockpit
            print(TerminalRenderer.render_sector(view, category_page=self.port_cat_page))
            self._prompt_action(view)

    # ------------------------------------------------------------------ Empire Building Mode
    def _set_mode(self, mode: str) -> None:
        self.kernel.set_command_mode(self.player_id, mode)
        self.clear_screen()

    def _empire_mode(self, view: Dict[str, Any]) -> None:
        dash = self.kernel.empire_dashboard(self.player_id)
        print(TerminalRenderer.render_empire_hub(dash))
        try:
            choice = input(bold(c_white("Empire Command [1-5/F/L/Q] > "))).strip().upper()
        except (KeyboardInterrupt, EOFError):
            self._do_quit()
            return
        if choice in ("F", "X", "FLY", "B", "BACK"):
            self._set_mode("FLY")
        elif choice in ("Q", "QUIT"):
            self._do_quit()
        elif choice in ("L", "LIBRARY"):
            self._prompt_library()
        elif choice == "1":
            self._empire_card(TerminalRenderer.render_empire_colonies, dash,
                              {"C": ("colony operations console (tax harvest, auto-warp, civics)", self._prompt_empire_console)})
        elif choice == "2":
            self._empire_card(TerminalRenderer.render_empire_fleets, dash,
                              {"H": ("hauler command console", self._prompt_fleet_console)})
        elif choice == "3":
            self._empire_card(TerminalRenderer.render_empire_routes, dash,
                              {"O": ("route optimizer & arbitrage desk", self._prompt_trade_routes)})
        elif choice == "4":
            self._empire_card(TerminalRenderer.render_empire_diplomacy, dash, {
                "T": ("treaties & ideology", self._prompt_ideology),
                "P": ("the Galactic Policy Deck", lambda v: print(TerminalRenderer.render_doctrine(
                    v, [dict(f.hand, dogma=f.dogma) for f in self.kernel.factions.factions.values()]))),
                "A": ("your alignment", lambda v: print(TerminalRenderer.render_alignment(
                    v, self.kernel.get_player(self.player_id).alignment_record))),
            })
        elif choice == "5":
            self._empire_card(TerminalRenderer.render_empire_treasury, dash, {
                "S": ("ISSE stock exchange & freight board", self._prompt_exchange),
                "V": ("venture capital desk", self._prompt_vc_desk),
                "X": ("FX currency desk", self._prompt_fx_desk),
                "K": ("credit profile & dossier", self._prompt_captain_profile),
                "B": ("federations, central banks & clearing union", lambda v: self._show_banking()),
            })
        elif choice:
            print(c_red("Choose 1-5, F to return to the flight deck, L for the Library, or Q to quit."))

    def _show_banking(self) -> None:
        fxm = self.kernel.fx_market
        fx = {"rates": {cur: fxm.rate(cur) for cur in fxm.pools},
              "cross": {k: (p["b"] / p["a"]) for k, p in getattr(fxm, "cross_pools", {}).items()}}
        tip = self.kernel.settlement.blocks[-1] if self.kernel.settlement.blocks else {}
        print(TerminalRenderer.render_banking(self.kernel.banking.summary(self.kernel), fx, tip))

    def _empire_card(self, render, dash: Dict[str, Any], desks: Dict[str, Any]) -> None:
        """One category of the sovereign dashboard, with the desks that act on it."""
        self.clear_screen()
        print(render(dash))
        menu = " │ ".join(f"{c_gold('[' + k + ']')} {label}" for k, (label, _) in desks.items())
        try:
            raw = input(f"\n{menu} │ Enter back > ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            return
        if raw in desks:
            view = self.kernel.get_player_view(self.player_id)
            desks[raw][1](view)
            try:
                input(c_gray("Enter to return to the sovereign console..."))
            except (KeyboardInterrupt, EOFError):
                pass
        self.clear_screen()

    # ------------------------------------------------------------------ lineage
    def _lineage_ended(self, lin: Dict[str, Any]) -> None:
        self.clear_screen()
        print(TerminalRenderer.render_lineage_extinct(lin))
        StatePersistence.save_to_file(self.kernel, self.save_file)
        try:
            again = input(c_gold("Found a new lineage in a new universe? (y/N) > ")).strip().lower()
        except (KeyboardInterrupt, EOFError):
            again = "n"
        if again != "y":
            self.running = False
            return
        import random as _random
        kernel, pid = lineage_genesis(seed=_random.randint(1, 10 ** 6), legacy_file=self.kernel.legacy_file)
        self.kernel, self.player_id = kernel, pid
        StatePersistence.save_to_file(self.kernel, self.save_file)
        self.clear_screen()

    # Multi-letter command words -> canonical command (single letter or word-only command)
    WORD_COMMANDS = {
        **{w: "EXCHANGE_DESK" for w in ["EXCHANGE", "STOCK", "STOCKS", "FREIGHT"]},
        **{w: "FLEET_DESK" for w in ["FLEET", "HAULER", "HAULERS", "LOGISTICS"]},
        **{w: "EMPIRE" for w in ["EMPIRE_MODE", "SOVEREIGN", "BRE"]},
        **{w: "RETIRE" for w in ["RETIRE", "ABDICATE"]},
        **{w: "CLONE" for w in ["CLONE", "CLONES", "VATS"]},
        **{w: "I" for w in ["IMPERIAL", "EMPIRE", "DOMINION", "ASSET", "ASSETS"]},
        **{w: "G" for w in ["COG", "COGNITION", "GOV", "IAE", "THINK"]},
        **{w: "TECH" for w in ["TECH", "ANOMALY", "RESEARCH"]},
        "NEXT": "N",
        **{w: "J" for w in ["JUMP", "WARP_JUMP"]},
        **{w: "X" for w in ["CARTOGRAPHY", "STARMAP", "MAP", "PUZZLE"]},
        **{w: "K" for w in ["PROFILE", "DOSSIER", "CREDIT", "FICO"]},
        **{w: "CLADOGRAM" for w in ["CLADOGRAM", "DAG", "TREE", "PHYLOGENY", "ASCENSION"]},
        **{w: "D" for w in ["DIPLO", "TREATY", "TREATIES", "IDEOLOGY"]},
        **{w: "Y" for w in ["ALCH", "ALCHEMY", "TRANSMUTE"]},
        **{w: "W" for w in ["ORBIT", "RADAR", "ASTRO", "EPHEMERIS"]},
        **{w: "SENATE" for w in ["SENATE", "SEN", "GOV_SENATE", "VOTE", "OFFICES"]},
        **{w: "SURFACE" for w in ["SURFACE", "GRID", "DISTRICT", "INVADE"]},
        **{w: "REST" for w in ["REST", "QUARTERS"]},
        **{w: "S" for w in ["BANK", "LOAN", "REPAY"]},
        **{w: "SCAN" for w in ["SCAN", "PROBE"]},
        **{w: "RUINS" for w in ["RUINS", "SURVEY", "ARCHAEOLOGY"]},
        **{w: "DIG" for w in ["DIG", "EXCAVATE"]},
        **{w: "SHORE" for w in ["SHORE"]},
        **{w: "ARTIFACTS" for w in ["ARTIFACTS", "ARTIFACT", "RELICS", "ANTIQUITIES", "CURIO"]},
        **{w: "PERMIT" for w in ["PERMIT"]},
        **{w: "MINE" for w in ["MINE", "MINING", "DRILL"]},
        **{w: "SALVAGE" for w in ["SALVAGE", "WRECK", "DEBRIS"]},
        **{w: "SENTRY" for w in ["SENTRY", "SENTRIES", "DEPLOY", "PICKET"]},
        **{w: "RECALL" for w in ["RECALL", "RETRIEVE"]},
        **{w: "FX" for w in ["FX", "FOREX", "CURRENCY", "CURRENCIES"]},
        **{w: "NATIVES" for w in ["NATIVES", "NATIVE", "LOCALS", "CONTACT", "UPLIFT"]},
        **{w: "LIBRARY" for w in ["L", "LIBRARY", "LIB", "CHRONICLE", "CHRONICLES", "HISTORY", "LORE"]},
        **{w: "WRITE" for w in ["WRITE", "JOURNAL", "LOG"]},
        **{w: "ALIGN" for w in ["ALIGN", "ALIGNMENT", "KARMA", "CONSCIENCE"]},
        **{w: "DOCTRINE" for w in ["DOCTRINE", "POLICY", "DIRECTIVE", "DECK", "PRIME"]},
        **{w: "BANKS" for w in ["BANKS", "BANKING", "FEDERATIONS", "FEDS", "CLEARING", "CENTRAL"]},
    }

    def _prompt_action(self, view: Dict[str, Any]) -> None:
        """Displays main command prompt and dispatches player selection."""
        sector = view.get("sector", {})
        has_port = sector.get("port") is not None
        has_planets = len(sector.get("planets", [])) > 0
        has_captains = len(sector.get("captains", [])) > 0
        in_fed_central = (sector.get("id") == 1)

        has_anom = len(sector.get("anomalies", [])) > 0
        has_jump = "JUMP_DRIVE" in view.get("unlocked_techs", [])

        # Build options
        opts = [
            f"{c_gold('[M]')}ove",
            f"{c_gold('[T]')}rade" if has_port else f"{c_gray('[T]rade')}",
            f"{c_gold('[P]')}lanet" if has_planets else f"{c_gray('[P]lanet')}",
            f"{c_gold('[A]')}ttack" if (has_captains or has_planets) else f"{c_gray('[A]ttack')}",
            f"{c_gold('[S]')}hipyard" if in_fed_central else f"{c_gray('[S]hipyard')}",
            f"{c_gold('[C]')}omputer",
            f"{c_gold('[O]')}ptimize",
            bold(c_gold('[E]')) + c_gold("mpire mode"),
            f"{c_gold('[I]')}mperial",
            f"{c_gold('[G]')}ov/Cog",
            f"{c_gold('[N]')} Anomaly" if has_anom else (f"{c_gold('[N]')} Next Cat" if has_port else f"{c_magenta('[N]')} Tech"),
            f"{c_cyan('[J]')}ump" if has_jump else f"{c_gray('[J]ump')}",
            f"{c_gold('[X]')} Cartography",
            f"{c_gold('[K]')} Profile",
            f"{c_gold('[R]')}adio",
            f"{c_gold('[H]')}elp",
            f"{c_gold('[Q]')}uit"
        ]

        print(f"\n{bold(c_cyan('Command Dispatch:'))} " + " │ ".join(opts))
        print(c_gray("  Deep space & money: SCAN │ MINE │ SALVAGE │ SENTRY │ RECALL │ FX (currency desk)"))
        print(c_gray("  Archaeology: RUINS (survey) │ DIG │ SHORE (dig + shoring) │ ARTIFACTS │ PERMIT (at Sol)"))
        print(c_gray("  Cosmos: NATIVES (locals) │ DOCTRINE (policy deck) │ ALIGN (Light/Dark) │ [L]IBRARY │ WRITE (your log)"))
        print(c_gray("  Lineage: [E]mpire mode │ FLEET │ STOCK │ BANKS │ CLONE (Sol vats) │ RETIRE"))
        try:
            choice = input(f"{bold(c_white('Command [M/T/P/A/S/C/O/E/I/G/N/J/X/K/R/H/Q] > '))}").strip().upper()
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

        # Full-word commands are resolved before first-letter dispatch; otherwise
        # e.g. "CLADOGRAM" would open the [C]omputer and "QUARTERS" would [Q]uit.
        choice = self.WORD_COMMANDS.get(choice, choice)
        if choice == "CLADOGRAM":
            self._prompt_cladogram(view)
            return
        if choice == "TECH":
            self._prompt_research_anomaly(view)
            return
        if choice == "SENATE":
            self._prompt_senate(view)
            return
        if choice == "SURFACE":
            self._prompt_surface(view)
            return
        if choice == "REST":
            res = self.kernel.dispatch(self.player_id, ActionType.REST)
            self._print_result(res)
            return
        simple = {"SCAN": ActionType.SCAN_SPACE, "MINE": ActionType.MINE_ASTEROIDS,
                  "SALVAGE": ActionType.SALVAGE_DEBRIS, "RECALL": ActionType.RECALL_SENTRIES,
                  "RUINS": ActionType.SURVEY_RUINS, "DIG": ActionType.EXCAVATE}
        if choice in simple:
            res = self.kernel.dispatch(self.player_id, simple[choice])
            self._print_result(res)
            return
        if choice == "SHORE":
            self._print_result(self.kernel.dispatch(self.player_id, ActionType.EXCAVATE, shore=True))
            return
        if choice == "PERMIT":
            self._print_result(self.kernel.dispatch(self.player_id, ActionType.BANK_TRANSACTION, sub_action="antiquities_permit"))
            return
        if choice == "ARTIFACTS":
            self._prompt_artifacts()
            return
        if choice == "SENTRY":
            self._prompt_sentries(view)
            return
        if choice == "FX":
            self._prompt_fx_desk(view)
            return
        if choice == "NATIVES":
            self._prompt_natives()
            return
        if choice == "BANKS":
            self._show_banking()
            return
        if choice == "EXCHANGE_DESK":
            self._prompt_exchange(view)
            return
        if choice == "FLEET_DESK":
            self._prompt_fleet_console(view)
            return
        if choice == "EMPIRE":
            self._set_mode("EMPIRE")
            return
        if choice == "CLONE":
            self._print_result(self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="clone"))
            return
        if choice == "RETIRE":
            try:
                sure = input(c_red("Retire your lineage? Its record will be sealed and control will end. Type RETIRE > ")).strip().upper()
            except (KeyboardInterrupt, EOFError):
                return
            if sure == "RETIRE":
                self._print_result(self.kernel.dispatch(self.player_id, ActionType.RETIRE_LINEAGE, confirm=True))
            return
        if choice == "LIBRARY":
            self._prompt_library()
            return
        if choice == "WRITE":
            self._prompt_write()
            return
        if choice == "ALIGN":
            cap = self.kernel.get_player(self.player_id)
            print(TerminalRenderer.render_alignment(view, cap.alignment_record))
            return
        if choice == "DOCTRINE":
            auths = [dict(f.hand, dogma=f.dogma) for f in self.kernel.factions.factions.values()]
            print(TerminalRenderer.render_doctrine(view, auths))
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
        elif cmd == "O":
            self._prompt_trade_routes(view)
        elif cmd == "E":
            self._set_mode("EMPIRE")
        elif cmd == "F":
            print(c_cyan("You are on the flight deck. [E] opens Empire mode; FLEET opens the hauler console."))
        elif cmd == "I":
            self._prompt_empire_console(view)
        elif cmd == "G":
            self._prompt_cognition(view)
        elif cmd == "N":
            if has_anom:
                self._prompt_research_anomaly(view)
            elif has_port:
                self.port_cat_page += 1
            else:
                self._prompt_research_anomaly(view)
        elif cmd == "J":
            self._prompt_jump_warp(view)
        elif cmd == "X":
            self._prompt_cartography(view)
        elif cmd == "K":
            self._prompt_captain_profile(view)
        elif cmd == "D":
            self._prompt_ideology(view)
        elif cmd == "Y":
            self._prompt_alchemy(view)
        elif cmd == "W":
            self._prompt_astronomy(view)
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

    def _prompt_natives(self) -> None:
        """Dealings with non-spacefaring locals, under the doctrine in force here."""
        while True:
            view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_natives(view))
            natives = view.get("cosmos", {}).get("natives", [])
            if not natives:
                return
            try:
                raw = input(c_gold("O observe │ C contact │ T trade │ U uplift │ U2 uplift two ages │ P protect │ "
                                   "COL collect │ X exploit │ Enter exit > ")).strip().upper()
            except (KeyboardInterrupt, EOFError):
                return
            if not raw:
                return
            subs = {"O": "observe", "C": "contact", "T": "trade", "U": "uplift", "P": "protect",
                    "COL": "collect", "X": "exploit", "CONVERT": "convert"}
            leap = 1
            if raw.startswith("U") and raw[1:].isdigit():
                leap, raw = int(raw[1:]), "U"
            sub = subs.get(raw)
            if sub is None:
                print(c_red("Unknown dealing."))
                continue
            self._print_result(self.kernel.dispatch(self.player_id, ActionType.NATIVE_INTERACT, sub_action=sub,
                                                    planet_id=natives[0]["planet_id"], leap=leap))

    def _prompt_library(self) -> None:
        """The Galactic Library: browse chronicles by kind, subject or text; read entries by id."""
        filters: Dict[str, Any] = {"page": 0}
        while True:
            res = self.kernel.dispatch(self.player_id, ActionType.LIBRARY_BROWSE, **filters)
            if not res.success:
                self._print_result(res)
                return
            d = res.data
            print(TerminalRenderer.render_library(d["entries"], d["total"], d["page"], d.get("counts", {})))
            try:
                raw = input(c_gold("CHR-#### read │ N/P page │ K <kind> (log/annals/field/decree/genesis/history/personal) │ "
                                   "S <name> │ F <text> │ Enter exit > ")).strip()
            except (KeyboardInterrupt, EOFError):
                return
            if not raw:
                return
            up = raw.upper()
            if up.startswith("CHR-"):
                r = self.kernel.dispatch(self.player_id, ActionType.LIBRARY_BROWSE, entry_id=up)
                if r.success:
                    print(TerminalRenderer.render_chronicle_entry(r.data["entry"]))
                    input(c_gray("Enter to return to the stacks..."))
                else:
                    self._print_result(r)
            elif up == "N":
                filters["page"] += 1
            elif up == "P":
                filters["page"] = max(0, filters["page"] - 1)
            elif up.startswith("K "):
                kinds = {"LOG": "CAPTAINS_LOG", "ANNALS": "PLANETARY_ANNALS", "FIELD": "FIELD_NOTES",
                         "DECREE": "FACTION_DECREE", "GENESIS": "GENESIS_MANIFESTO", "HISTORY": "GALACTIC_HISTORY",
                         "PERSONAL": "PERSONAL_LOG"}
                filters = {"page": 0, "kind": kinds.get(up[2:].strip(), up[2:].strip())}
            elif up.startswith("S "):
                filters = {"page": 0, "subject": raw[2:].strip()}
            elif up.startswith("F "):
                filters = {"page": 0, "text": raw[2:].strip()}
            else:
                print(c_red("Unknown library command."))

    def _prompt_write(self) -> None:
        """Write your own chronicle entry: an expedition log, life on your world, the journey so far."""
        try:
            title = input(c_gold("Title of your entry: ")).strip()
            print(c_gray("Write your entry (a single line; the Library keeps up to 2,000 characters):"))
            text = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            return
        self._print_result(self.kernel.dispatch(self.player_id, ActionType.CHRONICLE_WRITE, title=title, text=text))

    def _prompt_artifacts(self) -> None:
        """Artifact collection: curio-desk offers here, sell antiquities, or study tech relics."""
        from xylarium.kernel.archaeology import ArchaeologyManager
        while True:
            cap = self.kernel.get_player(self.player_id)
            sector = self.kernel.sectors[cap.sector_id]
            print(f"\n{bold(c_cyan('ARTIFACT COLLECTION'))} ({len(cap.artifacts)} piece(s))")
            if not cap.artifacts:
                print(c_gray("  Nothing yet. Survey ruins (RUINS) and excavate (DIG) with Equipment as tools."))
                return
            for i, a in enumerate(cap.artifacts, 1):
                price, reason = ArchaeologyManager.offer(a, sector, self.kernel)
                offer = c_gold(f"offer {price:,} {sector.port.currency}") if not reason else c_gray(reason[:52])
                print(f"  [{i}] {a['name']} - {a['kind'].replace('_', ' ').lower()}, {a['era_name']}, "
                      f"condition {a['condition']:.0%}, {a['provenance']} │ {offer}")
            try:
                raw = input(c_gold("S<n> sell │ ST<n> study relic │ SA sell all antiquities │ Enter exit > ")).strip().upper()
            except (KeyboardInterrupt, EOFError):
                return
            if not raw:
                return
            if raw == "SA":
                self._print_result(self.kernel.dispatch(self.player_id, ActionType.SELL_ARTIFACT, artifact_id="ALL"))
                continue
            kind, num = (ActionType.STUDY_ARTIFACT, raw[2:]) if raw.startswith("ST") else (ActionType.SELL_ARTIFACT, raw[1:])
            if num.isdigit() and 1 <= int(num) <= len(cap.artifacts):
                self._print_result(self.kernel.dispatch(self.player_id, kind, artifact_id=cap.artifacts[int(num) - 1]["id"]))
            else:
                print(c_red("Choose an artifact number."))

    def _prompt_sentries(self, view: Dict[str, Any]) -> None:
        """Deploys fighters from the bay as a sentry picket over the current sector."""
        fighters = view.get("player", {}).get("ship", {}).get("fighters", 0)
        try:
            raw = input(f"Fighters to deploy as sentries (0-{fighters}, Enter to cancel): ").strip()
        except (KeyboardInterrupt, EOFError):
            return
        if not raw:
            return
        if not raw.isdigit():
            print(c_red("Enter a number of fighters."))
            return
        res = self.kernel.dispatch(self.player_id, ActionType.DEPLOY_SENTRIES, amount=int(raw))
        self._print_result(res)

    def _prompt_fx_desk(self, view: Dict[str, Any]) -> None:
        """ISSE foreign-exchange desk: live rates, wallet, and currency swaps through the liquidity pools."""
        while True:
            fresh = self.kernel.get_player_view(self.player_id)
            fxv = fresh.get("fx", {})
            print(f"\n{bold(c_cyan('ISSE FOREIGN EXCHANGE DESK'))} - constant-product liquidity pools, 0.3% swap fee")
            sol_balance = fresh.get("credits", 0)
            print(f"  Wallet: {c_gold(f'{sol_balance:,} SOL')}"
                  + "".join(f" │ {c_gold(f'{amt:,} {cur}')}" for cur, amt in fxv.get("wallet", {}).items()))
            for cur, rate in fxv.get("rates", {}).items():
                drift = fxv.get("drift", {}).get(cur, 1.0)
                trend = c_red(f"weakened {100 * (drift - 1):.1f}%") if drift > 1 else c_green(f"strengthened {100 * (1 - drift):.1f}%")
                print(f"  1 SOL = {rate:,.4f} {cur}   ({trend} vs genesis price level)")
            print(f"  Local currency here: {c_cyan(fxv.get('local_currency', 'SOL'))}")
            try:
                raw = input(c_gold("Exchange as '<amount> <FROM> <TO>' (e.g. 500 SOL VOID), or Enter to exit > ")).strip().upper()
            except (KeyboardInterrupt, EOFError):
                return
            if not raw:
                return
            parts = raw.split()
            if len(parts) != 3 or not parts[0].isdigit():
                print(c_red("Format: <amount> <FROM> <TO>"))
                continue
            res = self.kernel.dispatch(self.player_id, ActionType.FX_EXCHANGE,
                                       amount=int(parts[0]), from_currency=parts[1], to_currency=parts[2])
            self._print_result(res)

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
        self.port_cat_page = 0
        result = self.kernel.dispatch(self.player_id, ActionType.MOVE, destination=dest)
        if not result.success:
            print(c_red(f"Navigation Error: {result.message}"))
        else:
            self.clear_screen()
            print(c_green(f"✔ {result.message}"))

    def _prompt_trade(self, view: Dict[str, Any]) -> None:
        """Handle port trading loop with hierarchical category tab navigation."""
        sector = view.get("sector", {})
        if not sector.get("port"):
            print(c_red("No trade port in this sector!"))
            return

        active_cat = "1"
        while True:
            view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_trade_screen(view, active_category=active_cat))
            try:
                cmd = input(f"{c_gold('Trade Command [B/S/1-5/X] > ')}").strip()
            except (KeyboardInterrupt, EOFError):
                break

            cmd_upper = cmd.upper()
            if not cmd or cmd_upper in ["X", "EXIT", "Q"]:
                self.clear_screen()
                break

            if cmd_upper in ["1", "2", "3", "4", "5"]:
                active_cat = cmd_upper
                continue

            parts = cmd.split()
            action = parts[0].upper()
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
                print(c_gold("Usage: B <commodity> <amount> (e.g. 'B Fe 10', 'B H2O 20') or [1-5] to switch category tab."))

    def _normalize_commodity(self, text: str) -> str:
        text = text.strip()
        t_upper = text.upper()
        if t_upper in ["ORE", "1"]:
            return "ORE"
        elif t_upper in ["ORGANICS", "ORG", "2"]:
            return "ORGANICS"
        elif t_upper in ["EQUIPMENT", "EQ", "EQP", "3"]:
            return "EQUIPMENT"

        from xylarium.config import COMMODITY_CONFIG
        for comm_key, cfg in COMMODITY_CONFIG.items():
            if t_upper == comm_key.upper():
                return comm_key
            if t_upper == cfg.get("symbol", "").upper():
                return comm_key
            if text.lower() == cfg.get("name", "").lower():
                return comm_key

        return text

    def _prompt_fleet_console(self, view: Dict[str, Any]) -> None:
        """Interactive Fleet Management and Automated Haulage Dashboard."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_fleet_control_console(fresh_view))
            try:
                cmd = input(f"{c_gold('Fleet Control Command [C/R/E/H/S/V/X] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd or cmd in ["X", "EXIT", "Q", "BACK"]:
                self.clear_screen()
                break

            action = cmd[0]
            if action == "C":
                # Commission Hauler
                from xylarium.config import SPECIALIZED_HULLS
                print(c_cyan("\nAvailable Specialized Hulls:"))
                hull_keys = list(SPECIALIZED_HULLS.keys())
                for i, k in enumerate(hull_keys, 1):
                    h_cfg = SPECIALIZED_HULLS[k]
                    print(f"  [{i}] {h_cfg['name']} ({k}): {h_cfg['holds']} holds, {h_cfg['price']:,} Cr")

                try:
                    h_choice = input(f"Choose Hull Class [1-{len(hull_keys)}] (default 1: STANDARD): ").strip()
                    if h_choice.isdigit() and 1 <= int(h_choice) <= len(hull_keys):
                        selected_hull = hull_keys[int(h_choice) - 1]
                    elif h_choice in SPECIALIZED_HULLS:
                        selected_hull = h_choice
                    else:
                        selected_hull = "STANDARD"

                    orig = int(input("Origin Spaceport Sector (e.g. 1): ").strip() or "1")
                    dest = int(input("Destination Spaceport Sector (e.g. 30): ").strip() or "30")
                    outb = input("Outbound Commodity to transport (e.g. Fe, H2O, EQUIPMENT): ").strip() or "EQUIPMENT"
                    retc = input("Return Commodity to transport (e.g. Organics, Ore, He-3): ").strip() or "ORGANICS"
                    h_name = input("Hauler Call-Sign / Name (optional): ").strip()

                    outb_norm = self._normalize_commodity(outb)
                    retc_norm = self._normalize_commodity(retc)

                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.HAULER_COMMISSION,
                        hull_class=selected_hull,
                        origin_sector=orig,
                        dest_sector=dest,
                        commodity_outbound=outb_norm,
                        commodity_return=retc_norm,
                        name=h_name if h_name else None,
                    )
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid sector number or input."))

            elif action == "R":
                # Reassign Route
                try:
                    hid = input("Trade Hauler ID to reassign (e.g. HAUL-101): ").strip().upper()
                    orig = int(input("New Origin Spaceport Sector: ").strip())
                    dest = int(input("New Destination Spaceport Sector: ").strip())
                    outb = input("Outbound Commodity: ").strip()
                    retc = input("Return Commodity: ").strip()

                    outb_norm = self._normalize_commodity(outb)
                    retc_norm = self._normalize_commodity(retc)

                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.HAULER_ASSIGN_ROUTE,
                        hauler_id=hid,
                        origin_sector=orig,
                        dest_sector=dest,
                        commodity_outbound=outb_norm,
                        commodity_return=retc_norm,
                    )
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid input."))

            elif action == "E":
                # Escort Wings Assign/Recall
                try:
                    hid = input("Hauler ID (e.g. HAUL-101): ").strip().upper()
                    sub = input("[A]ssign fighters from flagship or [R]ecall fighters? ").strip().upper()
                    mode = "assign" if sub.startswith("A") else "recall"
                    cnt = int(input("Number of fighter wings: ").strip())
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.FLEET_ASSIGN_ESCORT,
                        hauler_id=hid,
                        count=cnt,
                        mode=mode,
                    )
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid fighter wing count."))

            elif action == "H":
                # Halt / Recall Hauler
                try:
                    hid = input("Hauler ID to halt/recall (e.g. HAUL-101): ").strip().upper()
                    tsec = int(input("Recall target sector (default 1): ").strip() or "1")
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.FLEET_RECALL,
                        hauler_id=hid,
                        target_sector=tsec,
                    )
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid sector number."))

            elif action == "S":
                # Scrap / Decommission Hauler
                hid = input("Hauler ID to scrap for 50% refund (e.g. HAUL-101): ").strip().upper()
                conf = input(f"Confirm scrapping {hid} [Y/N]? ").strip().upper()
                if conf == "Y":
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.HAULER_DECOMMISSION,
                        hauler_id=hid,
                    )
                    self._print_result(res)

            elif action == "V":
                # Venture Capital Desk
                self._prompt_vc_desk(fresh_view)

            else:
                print(c_gold("Valid commands: [C]ommission, [R]eassign, [E]scort, [H]alt, [S]crap, [V]enture Capital, [X] Exit"))

    def _prompt_vc_desk(self, view: Dict[str, Any]) -> None:
        """Interactive Venture Capital and Debt Syndicate Console."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_vc_investment_desk(fresh_view))
            try:
                choice = input(f"{c_gold('VC Desk Command [1-3 / R / X] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not choice or choice in ["X", "EXIT", "Q", "BACK"]:
                self.clear_screen()
                break

            if choice in ["1", "2", "3"]:
                syn_keys = ["SOL_ANGEL", "AEGIS_VENTURES", "VOSS_CAPITAL"]
                syn_id = syn_keys[int(choice) - 1]
                res = self.kernel.dispatch(
                    self.player_id,
                    ActionType.VC_APPLY,
                    syndicate_id=syn_id,
                )
                self._print_result(res)
            elif choice.startswith("R") or "REPAY" in choice:
                parts = choice.split()
                try:
                    if len(parts) >= 2:
                        amt = int(parts[1])
                    else:
                        amt = int(input("Credits to pay toward outstanding VC debt: ").strip())
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.VC_REPAY,
                        amount=amt,
                    )
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid credit amount."))
            else:
                print(c_gold("Select [1-3] to apply for funding, [R]epay to pay down debt, or [X] to exit."))

    def _prompt_cladogram(self, view: Dict[str, Any]) -> None:
        """Interactive Phylogenetic Ascension Cladogram, Branch Gravitation, and Canopy Matrix."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_phylogenetic_cladogram(fresh_view))
            try:
                choice = input(f"{c_gold('Cladogram Command [A / O / G / X] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not choice or choice in ["X", "EXIT", "Q", "BACK"]:
                self.clear_screen()
                break
            elif choice in ["A", "ASCEND", "PROMOTE", "CRYSTALLIZE"]:
                phylo = fresh_view.get("phylogeny", {})
                eval_data = phylo.get("ascension_eval", {})
                best_b = eval_data.get("best_branch")
                target_id = best_b.get("id") if best_b else None
                res = self.kernel.dispatch(self.player_id, ActionType.PHYLOGENY_ASCEND, target_node_id=target_id)
                if res.success:
                    print(c_green(f"\n{res.message}"))
                else:
                    print(c_red(f"\n{res.message}"))
                try:
                    input(c_gray("Press Enter to continue..."))
                except (KeyboardInterrupt, EOFError):
                    pass
            elif choice in ["O", "OVERRIDE", "CANOPY"]:
                res = self.kernel.dispatch(self.player_id, ActionType.CANOPY_OVERRIDE)
                if res.success:
                    print(c_green(f"\n{res.message}"))
                else:
                    print(c_red(f"\n{res.message}"))
                try:
                    input(c_gray("Press Enter to continue..."))
                except (KeyboardInterrupt, EOFError):
                    pass
            elif choice in ["G", "CHIMERA", "GRAFT"]:
                phylo = fresh_view.get("phylogeny", {})
                eval_data = phylo.get("ascension_eval", {})
                chims = eval_data.get("chimeric_available", [])
                if not chims:
                    print(c_red("\nNo lateral Precursor Chimerism grafts are currently available for your node."))
                    try:
                        input(c_gray("Press Enter to continue..."))
                    except (KeyboardInterrupt, EOFError):
                        pass
                    continue
                target_h = chims[0]["id"]
                res = self.kernel.dispatch(
                    self.player_id,
                    ActionType.CARTOGRAPHY_FORGE_CHIT,
                    mode="chimera",
                    hybrid_node_id=target_h,
                )
                if res.success:
                    print(c_green(f"\n{res.message}"))
                else:
                    print(c_red(f"\n{res.message}"))
                try:
                    input(c_gray("Press Enter to continue..."))
                except (KeyboardInterrupt, EOFError):
                    pass
            else:
                self.clear_screen()
                break

    def _prompt_captain_profile(self, view: Dict[str, Any]) -> None:
        """Interactive Captain Dossier, Credit Risk, and Financial Integrity Console."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_captain_profile_screen(fresh_view))
            try:
                choice = input(f"{c_gold('Dossier Command [P / C / O / G / V / E / X] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not choice or choice in ["X", "EXIT", "Q", "BACK"]:
                self.clear_screen()
                break
            elif choice in ["P", "PROMOTE", "ASCEND"]:
                res = self.kernel.dispatch(self.player_id, ActionType.PHYLOGENY_ASCEND)
                if not res.success:
                    # Fallback to rank promote for invariant checks
                    res = self.kernel.dispatch(self.player_id, ActionType.RANK_PROMOTE)
                if res.success:
                    print(c_green(f"\n{res.message}"))
                else:
                    print(c_red(f"\n{res.message}"))
                try:
                    input(c_gray("Press Enter to continue..."))
                except (KeyboardInterrupt, EOFError):
                    pass
            elif choice in ["C", "CLADOGRAM", "DAG", "TREE", "PHYLOGENY"]:
                self._prompt_cladogram(fresh_view)
            elif choice in ["O", "OVERRIDE", "CANOPY"]:
                res = self.kernel.dispatch(self.player_id, ActionType.CANOPY_OVERRIDE)
                if res.success:
                    print(c_green(f"\n{res.message}"))
                else:
                    print(c_red(f"\n{res.message}"))
                try:
                    input(c_gray("Press Enter to continue..."))
                except (KeyboardInterrupt, EOFError):
                    pass
            elif choice in ["G", "CHIMERA", "GRAFT"]:
                self._prompt_cladogram(fresh_view)
            elif choice in ["V", "VC", "SYNDICATE"]:
                self._prompt_vc_desk(fresh_view)
            elif choice in ["E", "EXCHANGE", "STOCK", "STOCKS"]:
                self._prompt_exchange(fresh_view)
            else:
                self.clear_screen()
                break

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
            elif action_key == "K":
                garrison = planet.get("security_operatives", 0)
                ship_ops = fresh_view.get("player", {}).get("operatives", 0)
                print(f"Colony Counter-Intel Garrison: {garrison} agents │ Shipboard Agents: {ship_ops}")
                try:
                    sub = input("[S]tation operatives or [W]ithdraw operatives? ").strip().upper()
                    if sub.startswith("S"):
                        amt = int(input("Operatives to station as colony security: ").strip())
                        res = self.kernel.dispatch(self.player_id, ActionType.STATION_SECURITY, planet_id=planet["id"], mode="station", amount=amt)
                        self._print_result(res)
                    elif sub.startswith("W"):
                        amt = int(input("Operatives to withdraw to ship: ").strip())
                        res = self.kernel.dispatch(self.player_id, ActionType.STATION_SECURITY, planet_id=planet["id"], mode="withdraw", amount=amt)
                        self._print_result(res)
                except ValueError:
                    print(c_red("Invalid operative count."))
            elif action_key == "E":
                self._prompt_covert_op(fresh_view, target_type="PLANET", target_id=planet["id"], target_name=planet["name"])
            elif action_key == "V":
                self._prompt_civilization(fresh_view, planet)
            else:
                print(c_red("Invalid colony command option."))

    def _prompt_civilization(self, view: Dict[str, Any], planet: Dict[str, Any]) -> None:
        """Handle interaction with indigenous / colony civilization and periodic elements."""
        while True:
            self.clear_screen()
            fresh_view = self.kernel.get_player_view(self.player_id)
            planet_list = fresh_view.get("sector", {}).get("planets", [])
            p_match = next((p for p in planet_list if p["id"] == planet["id"]), None)
            if not p_match:
                break

            print(TerminalRenderer.render_civilization_screen(fresh_view, p_match))
            try:
                cmd = input(f"{c_gold('Civilization Action > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd or cmd in ["B", "BACK", "X", "EXIT"]:
                self.clear_screen()
                break

            act = cmd[0]
            if act == "C":
                try:
                    w_str = input("Credits to fund civic work (5 Cr = +1% progress, default 50): ").strip()
                    work_pts = int(w_str) // 5 if w_str else 10
                    ore_str = input("Ore to contribute for construction (default 0): ").strip()
                    ore_amt = int(ore_str) if ore_str else 0
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.PLANET_CIVIC_CONTRIBUTE,
                        planet_id=p_match["id"],
                        work_points=work_pts,
                        ore_amount=ore_amt
                    )
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid numbers entered."))
            elif act == "L":
                try:
                    elem_id = input("Element ID to load into ship (e.g. stelalith, chitinium, cryogenite): ").strip().lower()
                    amt_str = input("Units to load: ").strip()
                    amt = int(amt_str) if amt_str else 1
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.PLANET_ELEMENT_TRANSFER,
                        planet_id=p_match["id"],
                        element_id=elem_id,
                        direction="to_ship",
                        amount=amt
                    )
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid amount."))
            elif act == "O":
                try:
                    elem_id = input("Element ID to offload into planetary vault: ").strip().lower()
                    amt_str = input("Units to offload: ").strip()
                    amt = int(amt_str) if amt_str else 1
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.PLANET_ELEMENT_TRANSFER,
                        planet_id=p_match["id"],
                        element_id=elem_id,
                        direction="to_planet",
                        amount=amt
                    )
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid amount."))
            else:
                print(c_red("Unknown civilization action."))

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
                    print(f"\n{bold(c_cyan('Select Tactical Maneuver:'))}")
                    print(f"  {c_gold('[1]')} Full Combat Volley (Standard engagement - 2 Turns)")
                    print(f"  {c_gold('[2]')} Tactical Wing (Commit custom fighter wing - 2 Turns)")
                    print(f"  {c_gold('[3]')} Evasive Warp Escape (Emergency wormhole burn - 1 Turn)")
                    print(f"  {c_gold('[4]')} Sue for Truce / Bribe (Offer credit tribute to disengage - 1 Turn)")
                    print(f"  {c_gold('[5]')} Covert Black Ops (Deploy secret operatives on covert mission - 1 Turn)")
                    t_choice = input(f"Combat Order [1-5] (default 1): ").strip()
                    if t_choice == "2":
                        try:
                            f_num = int(input("Fighters to commit to the strike wing: ").strip())
                        except ValueError:
                            f_num = None
                        res = self.kernel.dispatch(self.player_id, ActionType.ATTACK_SHIP, target_id=t_id, tactic="volley", fighters=f_num)
                    elif t_choice == "3":
                        res = self.kernel.dispatch(self.player_id, ActionType.ATTACK_SHIP, target_id=t_id, tactic="evade")
                    elif t_choice == "4":
                        try:
                            b_amt_str = input("Credit tribute to offer (default 25% of balance, min 150): ").strip()
                            b_amt = int(b_amt_str) if b_amt_str else None
                        except ValueError:
                            b_amt = None
                        res = self.kernel.dispatch(self.player_id, ActionType.ATTACK_SHIP, target_id=t_id, tactic="bribe", bribe_amount=b_amt)
                    elif t_choice == "5":
                        self._prompt_covert_op(view, target_type="SHIP", target_id=t_id, target_name=t_id)
                        return
                    else:
                        res = self.kernel.dispatch(self.player_id, ActionType.ATTACK_SHIP, target_id=t_id, tactic="volley")
                else:
                    print(f"\n{bold(c_cyan('Select Colony Assault Order:'))}")
                    print(f"  {c_gold('[1]')} Orbital Bombardment (Standard siege - 2 Turns)")
                    print(f"  {c_gold('[2]')} Covert Black Ops Infiltration (Vault siphon / Shield sabotage / Bio-contaminate - 1 Turn)")
                    c_choice = input("Assault Order [1-2] (default 1): ").strip()
                    if c_choice == "2":
                        self._prompt_covert_op(view, target_type="PLANET", target_id=t_id, target_name=t_id)
                        return
                    res = self.kernel.dispatch(self.player_id, ActionType.ATTACK_PLANET, planet_id=t_id)
                self._print_result(res)
            else:
                print(c_red("Invalid selection."))
        except (KeyboardInterrupt, EOFError):
            return

    def _prompt_covert_op(self, view: Dict[str, Any], target_type: str, target_id: str, target_name: str) -> None:
        """Handle execution of a covert black ops mission against a target."""
        player = view.get("player", {})
        ops_avail = player.get("operatives", 0)
        print(f"\n{bold(c_magenta('═══════════════ [ BLACK OPS INTELLIGENCE TERMINAL ] ═══════════════'))}")
        print(f"Target: {c_white(target_name)} ({target_type}) │ Field Operatives Available: {c_gold(str(ops_avail))}")
        print("Select Mission Type:")
        print(f"  {c_gold('[1]')} Classified Telemetry Recon (Min 1 Op)")
        print(f"  {c_gold('[2]')} Vault / Asset Siphon (Min 2 Ops - Siphon Credits)")
        print(f"  {c_gold('[3]')} Shield Grid Sabotage (Min 2 Ops - Collapse Deflectors)")
        if target_type == "PLANET":
            print(f"  {c_gold('[4]')} Biosphere Contamination & Morale Destabilization (Min 3 Ops)")
        print(f"  {c_gold('[X]')} Cancel Infiltration")

        try:
            m_choice = input(f"{c_gold('Select Operation [1-4 / X] > ')}").strip().upper()
            if not m_choice or m_choice in ["X", "EXIT", "BACK"]:
                return

            op_map = {"1": "recon", "2": "siphon", "3": "sabotage", "4": "destabilize"}
            if m_choice not in op_map:
                print(c_red("Invalid mission selection."))
                return

            op_type = op_map[m_choice]
            if op_type == "destabilize" and target_type != "PLANET":
                print(c_red("Destabilization is only applicable to planetary colonies."))
                return

            op_cnt_str = input(f"Operatives to commit to '{op_type}' mission: ").strip()
            op_cnt = int(op_cnt_str) if (op_cnt_str and op_cnt_str.isdigit()) else 1

            res = self.kernel.dispatch(
                self.player_id,
                ActionType.COVERT_OP,
                target_type=target_type,
                target_id=target_id,
                op_type=op_type,
                operatives=op_cnt
            )
            self._print_result(res)
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
                choice = input(f"{c_gold('Shipyard Order [1-9 / B / R] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not choice or choice in ["X", "EXIT"]:
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
            elif choice in ["7", "BANK"]:
                print(f"\n{bold(c_cyan('═══════════════ [ FEDERAL BANK OF SOL ] ═══════════════'))}")
                print(f"  {c_gold('[1]')} Request Emergency Relief Loan (1,000 Cr + 15% surcharge = 1,150 Cr debt)")
                print(f"  {c_gold('[2]')} Repay Outstanding Federal Debt")
                print(f"  {c_gold('[3]')} Settle Legal Restitution (Clear Bounties & Corporate Embargoes)")
                print(f"  {c_gold('[B]')} Back to Shipyard")
                try:
                    b_sel = input(f"{c_gold('Bank Option [1/2/3/B] > ')}").strip().upper()
                    if b_sel == "1":
                        res = self.kernel.dispatch(self.player_id, ActionType.BANK_TRANSACTION, sub_action="loan")
                        self._print_result(res)
                    elif b_sel == "2":
                        amt_str = input("Repayment amount (or Enter for maximum possible): ").strip()
                        amt = int(amt_str) if (amt_str and amt_str.isdigit()) else None
                        res = self.kernel.dispatch(self.player_id, ActionType.BANK_TRANSACTION, sub_action="repay", amount=amt)
                        self._print_result(res)
                    elif b_sel == "3":
                        res = self.kernel.dispatch(self.player_id, ActionType.BANK_TRANSACTION, sub_action="restitution")
                        self._print_result(res)
                except (KeyboardInterrupt, EOFError):
                    pass
            elif choice in ["8", "R", "REST"]:
                res = self.kernel.dispatch(self.player_id, ActionType.REST)
                self._print_result(res)
            elif choice in ["9", "AGENCY", "SPY", "OPERATIVES"]:
                try:
                    op_cnt = int(input("Field operatives to recruit (500 Cr/ea): ").strip())
                    res = self.kernel.dispatch(self.player_id, ActionType.RECRUIT_OPERATIVES, amount=op_cnt)
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid operative count."))
            elif choice in ["B", "BACK"]:
                self.clear_screen()
                break
            else:
                print(c_red("Invalid shipyard order."))

    def _prompt_nav_computer(self, view: Dict[str, Any]) -> None:
        """Handle BFS navigation computer pathfinding and trade route analysis."""
        curr_sec = view.get("sector", {}).get("id", 1)
        print(f"\n{bold(c_cyan('═══════════════ [ HYPER-NAV & FLIGHT COMPUTER ] ═══════════════'))}")
        print(f"  {c_gold('[1]')} Manual Sector BFS Course Plot (Sector 1-100)")
        print(f"  {c_gold('[2]')} Launch Trade Route & Arbitrage Optimizer")
        print(f"  {c_gold('[X]')} Return to Main Bridge Prompt")
        try:
            mode = input(f"{c_gold('Nav Computer Mode [1/2/X] > ')}").strip().upper()
            if not mode or mode in ["X", "EXIT", "BACK"]:
                return
            if mode == "2" or mode == "O":
                self._prompt_trade_routes(view)
                return

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

    def _prompt_trade_routes(self, view: Dict[str, Any]) -> None:
        """Interactive Trade Route & Arbitrage Command Center."""
        def _handle_route_autopilot(routes: List[Any], c_sec: int) -> bool:
            if not routes:
                input(c_gold("Press Enter to continue..."))
                return False
            try:
                sel = input(f"{c_gold(f'Plot course to route [1-{len(routes)}] (or Enter to back) > ')}").strip()
                if sel and sel.isdigit():
                    r_idx = int(sel) - 1
                    if 0 <= r_idx < len(routes):
                        chosen = routes[r_idx]
                        target = chosen.sector_a if c_sec != chosen.sector_a else chosen.sector_b
                        path = self.kernel.find_path(c_sec, target)
                        print(TerminalRenderer.render_nav_computer(c_sec, target, path))
                        if len(path) > 1:
                            conf = input(f"{c_gold(f'Engage autopilot to Sector {target:03d} (First hop: {path[1]:03d})? [Y/N] > ')}").strip().upper()
                            if conf == "Y":
                                self._do_move(path[1])
                                return True
            except (KeyboardInterrupt, EOFError):
                pass
            return False

        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            player = self.kernel.get_player(self.player_id)
            if not player:
                break
            curr_sec = player.sector_id
            cargo_cap = player.ship.cargo.capacity

            print(TerminalRenderer.render_trade_routes_menu(fresh_view))
            try:
                choice = input(f"{c_gold('Trade Optimizer Command [1-9 / X] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not choice or choice in ["X", "EXIT", "Q", "BACK"]:
                self.clear_screen()
                break

            if choice == "1":
                # All High-Yield Loops (Global scan across all 24+ commodities)
                routes = TradeRouteOptimizer.find_circular_arbitrage(
                    self.kernel, cargo_capacity=cargo_cap, max_hops=4, category="ALL"
                )
                print(TerminalRenderer.render_circular_arbitrage(routes, curr_sec, title="CIRCULAR ARBITRAGE: ALL 24+ COMMODITIES"))
                if _handle_route_autopilot(routes, curr_sec):
                    break

            elif choice == "2":
                # Volatiles & Gases (5x Density: H, He-3, C, H2O, Xe)
                routes = TradeRouteOptimizer.find_circular_arbitrage(
                    self.kernel, cargo_capacity=cargo_cap, max_hops=4, category="VOLATILES"
                )
                print(TerminalRenderer.render_circular_arbitrage(routes, curr_sec, title="CIRCULAR ARBITRAGE: VOLATILES & GASES (5x DENSITY)"))
                if _handle_route_autopilot(routes, curr_sec):
                    break

            elif choice == "3":
                # Structural Metals & Ores (4x Density: Fe, Ti, Si, Ni, Cu, Ore)
                routes = TradeRouteOptimizer.find_circular_arbitrage(
                    self.kernel, cargo_capacity=cargo_cap, max_hops=4, category="METALS"
                )
                print(TerminalRenderer.render_circular_arbitrage(routes, curr_sec, title="CIRCULAR ARBITRAGE: STRUCTURAL METALS & ORES (4x DENSITY)"))
                if _handle_route_autopilot(routes, curr_sec):
                    break

            elif choice == "4":
                # Fissionables & Exotics (1x Density: U, Pt, SpR, Cryogenite, etc.)
                routes = TradeRouteOptimizer.find_circular_arbitrage(
                    self.kernel, cargo_capacity=cargo_cap, max_hops=4, category="EXOTICS"
                )
                print(TerminalRenderer.render_circular_arbitrage(routes, curr_sec, title="CIRCULAR ARBITRAGE: FISSIONABLES & EXOTICS (1x DENSITY)"))
                if _handle_route_autopilot(routes, curr_sec):
                    break

            elif choice == "5":
                # Manufactured Components (1x Density: Equipment, M1-M4 Warp Cores)
                routes = TradeRouteOptimizer.find_circular_arbitrage(
                    self.kernel, cargo_capacity=cargo_cap, max_hops=4, category="MANUFACTURED"
                )
                print(TerminalRenderer.render_circular_arbitrage(routes, curr_sec, title="CIRCULAR ARBITRAGE: MANUFACTURED COMPONENTS (1x DENSITY)"))
                if _handle_route_autopilot(routes, curr_sec):
                    break

            elif choice == "6":
                # Element-Specific Radar
                try:
                    elem_in = input(f"{c_gold('Enter Element / Commodity Symbol (e.g. H2O, U, Fe, ORE, Xe, SpR) > ')}").strip()
                except (KeyboardInterrupt, EOFError):
                    continue
                if not elem_in:
                    continue
                routes = TradeRouteOptimizer.find_element_radar(
                    self.kernel, commodity=elem_in, cargo_capacity=cargo_cap, max_hops=8
                )
                print(TerminalRenderer.render_circular_arbitrage(routes, curr_sec, title=f"TARGETED ELEMENT RADAR: {elem_in.upper()}"))
                if _handle_route_autopilot(routes, curr_sec):
                    break

            elif choice == "7":
                # Local High-Yield Departures
                ops = TradeRouteOptimizer.find_local_opportunities(
                    self.kernel, curr_sec, cargo_capacity=cargo_cap, max_hops=5
                )
                print(TerminalRenderer.render_local_opportunities(ops, curr_sec))
                if ops:
                    try:
                        sel = input(f"{c_gold(f'Plot export delivery course [1-{len(ops)}] (or Enter to back) > ')}").strip()
                        if sel and sel.isdigit():
                            o_idx = int(sel) - 1
                            if 0 <= o_idx < len(ops):
                                chosen_op = ops[o_idx]
                                print(TerminalRenderer.render_nav_computer(curr_sec, chosen_op.dest_sector, chosen_op.path))
                                if len(chosen_op.path) > 1:
                                    conf = input(f"{c_gold(f'Engage autopilot to Sector {chosen_op.dest_sector:03d} (First hop: {chosen_op.path[1]:03d})? [Y/N] > ')}").strip().upper()
                                    if conf == "Y":
                                        self._do_move(chosen_op.path[1])
                                        break
                    except (KeyboardInterrupt, EOFError):
                        pass
                else:
                    input(c_gold("Press Enter to continue..."))

            elif choice == "8":
                # Colony Supply Corridors
                runs = TradeRouteOptimizer.find_colony_supply_routes(self.kernel, player, max_hops=8)
                print(TerminalRenderer.render_colony_supply_routes(runs))
                if runs:
                    try:
                        sel = input(f"{c_gold(f'Plot course to supplier port [1-{len(runs)}] (or Enter to back) > ')}").strip()
                        if sel and sel.isdigit():
                            r_idx = int(sel) - 1
                            if 0 <= r_idx < len(runs):
                                chosen_run = runs[r_idx]
                                path_to_supplier = self.kernel.find_path(curr_sec, chosen_run.source_sector)
                                print(TerminalRenderer.render_nav_computer(curr_sec, chosen_run.source_sector, path_to_supplier))
                                if len(path_to_supplier) > 1:
                                    conf = input(f"{c_gold(f'Engage autopilot to Supplier in Sector {chosen_run.source_sector:03d} (First hop: {path_to_supplier[1]:03d})? [Y/N] > ')}").strip().upper()
                                    if conf == "Y":
                                        self._do_move(path_to_supplier[1])
                                        break
                    except (KeyboardInterrupt, EOFError):
                        pass
                else:
                    input(c_gold("Press Enter to continue..."))

            elif choice == "9":
                # Interstellar Commodity Ticker
                spreads = TradeRouteOptimizer.get_galactic_spreads(self.kernel)
                print(TerminalRenderer.render_galactic_ticker(spreads))
                input(c_gold("Press Enter to return to Trade Optimizer..."))

    def _prompt_research_anomaly(self, view: Dict[str, Any]) -> None:
        """Interactive Tech Tree breakthroughs & Cosmic Anomaly investigation matrix."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            self.clear_screen()
            print(TerminalRenderer.render_tech_tree_screen(fresh_view))

            sector_anoms = fresh_view.get("sector", {}).get("anomalies", [])
            if sector_anoms:
                print(f"\n{bold(c_magenta('──[ LOCAL COSMIC ANOMALIES IN THIS SECTOR ]' + '─' * 33))}")
                for a in sector_anoms:
                    s_tag = c_green("[SOLVED]") if a.get("status") == "SOLVED" else c_magenta("[UNSOLVED]")
                    print(f"  ► {s_tag} {bold(c_white(a['name']))} [{c_gold(a['id'])}] - Target Freq: {a.get('puzzle_target')}")

            print(f"\n{bold(c_cyan('Cognitive Command:'))} "
                  f"{c_gold('[1-5]')} Commission Project │ "
                  f"{c_gold('[I]')}nvestigate Anomaly │ "
                  f"{c_gold('[B]')}ack to Bridge")
            try:
                cmd = input(f"{bold(c_white('Research Action [1-5 / I / B] > '))}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd or cmd in ["B", "BACK", "Q", "QUIT", "EXIT"]:
                self.clear_screen()
                break

            tech_keys = list(fresh_view.get("tech_tree", {}).keys())
            if cmd.isdigit():
                idx = int(cmd) - 1
                if 0 <= idx < len(tech_keys):
                    t_key = tech_keys[idx]
                    res = self.kernel.dispatch(self.player_id, ActionType.RESEARCH_SELECT, tech_key=t_key)
                    self._print_result(res)
                    input(c_gold("Press Enter to continue..."))
                else:
                    print(c_red("Invalid technology index."))
                    input(c_gold("Press Enter to continue..."))

            elif cmd in ["I", "ANOMALY", "INVESTIGATE"]:
                if not sector_anoms:
                    print(c_red("No cosmic anomalies detected in current sector orbit."))
                    input(c_gold("Press Enter to continue..."))
                    continue

                target_anom = sector_anoms[0]
                self.clear_screen()
                print(TerminalRenderer.render_anomaly_screen(fresh_view, target_anom))
                try:
                    a_choice = input(f"{c_gold('Decoding Method [1/2/B] > ')}").strip().upper()
                except (KeyboardInterrupt, EOFError):
                    break

                if a_choice == "1":
                    freq_in = input(f"Enter Harmonic Resonance Frequency [Target: {target_anom.get('puzzle_target')}]: ").strip()
                    val = int(freq_in) if freq_in.isdigit() else 0
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.ANOMALY_INVESTIGATE,
                        anomaly_id=target_anom["id"],
                        solve_inputs={"mode": "solve", "value": val}
                    )
                    self._print_result(res)
                    input(c_gold("Press Enter to continue..."))
                elif a_choice == "2":
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.ANOMALY_INVESTIGATE,
                        anomaly_id=target_anom["id"],
                        solve_inputs={"mode": "catalyst"}
                    )
                    self._print_result(res)
                    input(c_gold("Press Enter to continue..."))

    def _prompt_jump_warp(self, view: Dict[str, Any]) -> None:
        """Hyper-dimensional Jump Drive transit across space & outer clusters."""
        unlocked = view.get("unlocked_techs", [])
        if "JUMP_DRIVE" not in unlocked:
            print(c_red("Hyper-Dimensional Jump Drive is not installed. Commission and unlock JUMP_DRIVE in research [N]."))
            input(c_gold("Press Enter to continue..."))
            return

        curr_sec = view.get("sector", {}).get("id", 1)
        clusters = view.get("minted_clusters", [1])
        print(f"\n{bold(c_cyan('══════════════ [ HYPER-DIMENSIONAL JUMP DRIVE ] ══════════════'))}")
        print(f"Current Position: Sector {curr_sec:03d} │ Transit Capacitors: 250 Credits")
        print(f"Charted Clusters: {clusters} (Cluster 1: Sol Core 1-100, Cluster 2: Perseus Veil 101-140, Cluster 3: Cygnus Spiral 141-180)")
        print(f"Crossing outer frontiers procedurally mints new star clusters on demand (The Observation Law)!\n")

        try:
            dest_in = input(f"{c_gold('Enter Destination Sector ID (e.g. 1-180) [or Enter to cancel] > ')}").strip()
            if not dest_in or not dest_in.isdigit():
                return
            dest = int(dest_in)
            res = self.kernel.dispatch(self.player_id, ActionType.JUMP_WARP, destination=dest)
            self._print_result(res)
            input(c_gold("Press Enter to continue..."))
            self.clear_screen()
        except (KeyboardInterrupt, EOFError):
            return

    def _prompt_cognition(self, view: Dict[str, Any]) -> None:
        """Interactive loop for the Dual-Seat Cognition Engine console (iae::think)."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            self.clear_screen()
            print(TerminalRenderer.render_cognitive_console(fresh_view))
            try:
                cmd = input(f"\n{c_gold('Cognition Command [A=Automate Step, Q=Quit] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd or cmd in ["Q", "QUIT", "EXIT"]:
                self.clear_screen()
                break

            if cmd in ["A", "AUTO", "AUTOMATE", "THINK"]:
                res = self.kernel.dispatch(self.player_id, ActionType.COGNITIVE_AUTOMATE)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))
            else:
                print(c_red(f"Unknown command: '{cmd}'. [A]utomate Step or [Q]uit."))
                input(c_gold("Press Enter to continue..."))

    def _prompt_empire_console(self, view: Dict[str, Any]) -> None:
        """Interactive loop for Imperial Dominion & Asset Registry console."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            self.clear_screen()
            print(TerminalRenderer.render_empire_console(fresh_view))
            try:
                cmd = input(f"\n{c_gold('Imperial Command [T/W/C/R/D/Q] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd or cmd in ["Q", "QUIT", "EXIT"]:
                self.clear_screen()
                break

            parts = cmd.split()
            action = parts[0]

            if action in ["T", "TAX", "HARVEST"]:
                planets = fresh_view.get("owned_planets", [])
                if not planets:
                    print(c_red("You do not govern any sovereign colonies."))
                    input(c_gold("Press Enter to continue..."))
                    continue

                total_harvested = 0
                for p_data in planets:
                    p_id = p_data.get("id")
                    sec_id = p_data.get("sector_id")
                    sec = self.kernel.sectors.get(sec_id)
                    if sec:
                        for p in sec.planets:
                            if p.id == p_id and p.owner_id == self.player_id:
                                res = self.kernel.dispatch(self.player_id, ActionType.PLANET_TAX, planet_id=p_id)
                                if res.success and res.data:
                                    total_harvested += res.data.get("tax_collected", 0)

                if total_harvested > 0:
                    print(c_green(f"✔ DOMINION TAX HARVEST: Dispatched tax collectors across all colonies. Collected +{total_harvested:,} Credits into treasury!"))
                else:
                    print(c_gold("Colony vaults are currently depleted. Taxes accrue every world simulation tick."))
                input(c_gold("Press Enter to continue..."))

            elif action in ["W", "WARP", "COURSE"]:
                planets = fresh_view.get("owned_planets", [])
                if not planets:
                    print(c_red("You do not govern any sovereign colonies."))
                    input(c_gold("Press Enter to continue..."))
                    continue

                if len(parts) >= 2 and parts[1].isdigit():
                    target_sec = int(parts[1])
                elif len(planets) == 1:
                    target_sec = planets[0]["sector_id"]
                else:
                    try:
                        p_choice = input(f"Enter target colony sector (or Enter to cancel): ").strip()
                        if not p_choice or not p_choice.isdigit():
                            continue
                        target_sec = int(p_choice)
                    except (KeyboardInterrupt, EOFError):
                        continue

                captain = self.kernel.get_player(self.player_id)
                path = self.kernel.find_path(captain.sector_id, target_sec)
                if path:
                    print(c_cyan(f"BFS Warp Trajectory to Sector {target_sec:03d} ({len(path)-1} hops): " + " -> ".join([f"{s:03d}" for s in path])))
                    confirm = input(f"Engage auto-warp along this corridor? (y/N): ").strip().lower()
                    if confirm == "y":
                        for step_sec in path[1:]:
                            if captain.turns_left <= 0:
                                print(c_red("Out of turns! Warp sequence halted."))
                                break
                            res = self.kernel.dispatch(self.player_id, ActionType.MOVE, destination=step_sec)
                            if not res.success:
                                print(c_red(f"Warp interdicted: {res.message}"))
                                break
                        print(c_green(f"Arrived at Sector {captain.sector_id:03d}."))
                        input(c_gold("Press Enter to return to main navigation..."))
                        self.clear_screen()
                        break
                else:
                    print(c_red(f"No warp trajectory found to Sector {target_sec}."))
                input(c_gold("Press Enter to continue..."))

            elif action in ["C", "COMMISSION"]:
                try:
                    h_name = input("Hauler Ship Name (e.g. 'Starlight Express'): ").strip()
                    orig_str = input("Origin Sector [e.g. 1]: ").strip()
                    dest_str = input("Destination Sector [e.g. 30]: ").strip()
                    outbound = input("Outbound Cargo [EQUIPMENT/ORE/ORGANICS]: ").strip()
                    ret_comm = input("Return Cargo [ORGANICS/ORE/EQUIPMENT]: ").strip()

                    orig = int(orig_str) if orig_str.isdigit() else 1
                    dest = int(dest_str) if dest_str.isdigit() else 30
                    out_norm = self._normalize_commodity(outbound)
                    ret_norm = self._normalize_commodity(ret_comm)

                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.HAULER_COMMISSION,
                        name=h_name,
                        origin_sector=orig,
                        dest_sector=dest,
                        commodity_outbound=out_norm,
                        commodity_return=ret_norm,
                    )
                    if res.success:
                        print(c_green(f"✔ {res.message}"))
                    else:
                        print(c_red(f"Commissioning Denied: {res.message}"))
                except (ValueError, KeyboardInterrupt, EOFError) as e:
                    print(c_red(f"Error: {e}"))
                input(c_gold("Press Enter to continue..."))

            elif action in ["R", "REASSIGN", "ROUTE"]:
                haulers = fresh_view.get("trade_haulers", [])
                if not haulers:
                    print(c_red("You do not own any trade haulers to reassign."))
                    input(c_gold("Press Enter to continue..."))
                    continue

                try:
                    hid = input("Enter Hauler ID [e.g. HAUL-101]: ").strip().upper()
                    orig_str = input("New Origin Sector: ").strip()
                    dest_str = input("New Destination Sector: ").strip()
                    outbound = input("New Outbound Cargo [EQUIPMENT/ORE/ORGANICS]: ").strip()
                    ret_comm = input("New Return Cargo [ORGANICS/ORE/EQUIPMENT]: ").strip()

                    orig = int(orig_str) if orig_str.isdigit() else 1
                    dest = int(dest_str) if dest_str.isdigit() else 30
                    out_norm = self._normalize_commodity(outbound)
                    ret_norm = self._normalize_commodity(ret_comm)

                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.HAULER_ASSIGN_ROUTE,
                        hauler_id=hid,
                        origin_sector=orig,
                        dest_sector=dest,
                        commodity_outbound=out_norm,
                        commodity_return=ret_norm,
                    )
                    if res.success:
                        print(c_green(f"✔ {res.message}"))
                    else:
                        print(c_red(f"Route Reassignment Denied: {res.message}"))
                except (ValueError, KeyboardInterrupt, EOFError) as e:
                    print(c_red(f"Error: {e}"))
                input(c_gold("Press Enter to continue..."))

            elif action in ["D", "DECOMMISSION", "SCRAP"]:
                haulers = fresh_view.get("trade_haulers", [])
                if not haulers:
                    print(c_red("You do not own any trade haulers to decommission."))
                    input(c_gold("Press Enter to continue..."))
                    continue

                try:
                    hid = input("Enter Hauler ID to scrap [e.g. HAUL-101]: ").strip().upper()
                    confirm = input(f"Scrap {hid} for 2,000 Credits refund? (y/N): ").strip().lower()
                    if confirm == "y":
                        res = self.kernel.dispatch(
                            self.player_id,
                            ActionType.HAULER_DECOMMISSION,
                            hauler_id=hid,
                        )
                        if res.success:
                            print(c_green(f"✔ {res.message}"))
                        else:
                            print(c_red(f"Scrap Denied: {res.message}"))
                except (KeyboardInterrupt, EOFError):
                    pass
                input(c_gold("Press Enter to continue..."))
            else:
                print(c_red(f"Unknown Imperial command: '{cmd}'. Use T, W, C, R, D, or Q."))
                input(c_gold("Press Enter to continue..."))

    def _prompt_exchange(self, view: Dict[str, Any]) -> None:
        """Interactive Interstellar Stock Exchange & Freight Haulage Command Center."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            player = self.kernel.get_player(self.player_id)
            if not player:
                break

            print(TerminalRenderer.render_stock_market_screen(fresh_view))
            print(f"\n{bold(c_cyan('ISSE Exchange Terminal:'))} "
                  f"{c_gold('[B]')}uy │ {c_gold('[S]')}ell │ {c_gold('[K]')} Short/Cover │ "
                  f"{c_gold('[M]')} Corporate Machine │ {c_gold('[F]')}reight Board │ "
                  f"{c_gold('[I]')}PO │ {c_gold('[T]')}akeover & Boardroom │ {c_gold('[R]')}eturn")
            try:
                choice = input(f"{bold(c_white('Exchange Command [B/S/K/M/F/I/T/R] > '))}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not choice or choice in ["R", "RETURN", "BACK", "Q", "EXIT"]:
                self.clear_screen()
                break

            if choice == "B":
                self._prompt_stock_buy(fresh_view)
            elif choice == "S":
                self._prompt_stock_sell(fresh_view)
            elif choice in ["K", "SHORT", "COVER"]:
                self._prompt_stock_short_cover(fresh_view)
            elif choice in ["M", "MACHINE", "CORP"]:
                self._prompt_corporate_machine(fresh_view)
            elif choice == "F":
                self._prompt_freight_board(fresh_view)
            elif choice == "I":
                self._prompt_colony_ipo(fresh_view)
            elif choice in ["T", "TAKEOVER", "BOARD", "BOARDROOM"]:
                self._prompt_boardroom(fresh_view)
            else:
                print(c_red(f"Unknown command: '{choice}'."))

    def _prompt_boardroom(self, view: Dict[str, Any]) -> None:
        """Interactive Corporate Takeover & Boardroom Governance Terminal."""
        current_ticker = ""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            player = self.kernel.get_player(self.player_id)
            if not player:
                break

            print(TerminalRenderer.render_boardroom_screen(fresh_view, current_ticker))
            market = fresh_view.get("market", {})
            companies = market.get("companies", [])
            comp_map = {c["ticker"]: c for c in companies}

            # Resolve active ticker
            if not current_ticker or current_ticker not in comp_map:
                portfolio = market.get("portfolio", {})
                owned = [t for t in portfolio if t in comp_map]
                current_ticker = owned[0] if owned else (companies[0]["ticker"] if companies else "VOSS")

            active_comp = comp_map.get(current_ticker)
            if not active_comp:
                break

            is_chairman = (active_comp.get("chairman_id") == self.player_id)
            tot_shares = active_comp.get("total_shares", 10000)
            owned_shares = market.get("portfolio", {}).get(current_ticker, 0)
            ownership_pct = (owned_shares / tot_shares) * 100 if tot_shares > 0 else 0.0

            opts = []
            if is_chairman:
                opts.extend([
                    f"{c_gold('[D]')}isburse Dividend",
                    f"{c_gold('[R]')}estructure Industry",
                    f"{c_gold('[E]')}mbargo Captain",
                    f"{c_gold('[S]')}trip Assets",
                    f"{c_gold('[A]')}ctivate Poison Pill",
                    f"{c_gold('[W]')} Set Sector Tariff",
                ])
            else:
                if ownership_pct > 50.0:
                    opts.append(f"{bold(c_gold('[T]akeover Hostile Coup'))}")
                elif ownership_pct >= 25.0:
                    opts.append(f"{c_gold('[P]')}roxy Fight Campaign (4k Cr)")
                else:
                    opts.append(f"{c_gray('Acquire 25%+ on ISSE to launch bid')}")

            opts.extend([f"{c_gold('[C]')}hange Corp", f"{c_gold('[B]')}ack"])

            print(f"\n{bold(c_cyan('Boardroom Directives:'))} " + " │ ".join(opts))
            try:
                choice = input(f"{bold(c_white('Boardroom Command > '))}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not choice or choice in ["B", "BACK", "R", "RETURN", "Q"]:
                self.clear_screen()
                break

            if choice == "C":
                new_t = input(f"{c_gold('Enter Company Ticker to inspect > ')}").strip().upper()
                if new_t in comp_map:
                    current_ticker = new_t
                else:
                    print(c_red(f"Ticker '{new_t}' not recognized."))
                    input(c_gold("Press Enter to continue..."))

            elif choice in ["T", "TAKEOVER"]:
                res = self.kernel.dispatch(self.player_id, ActionType.CORPORATE_TAKEOVER, ticker=current_ticker)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif choice in ["P", "PROXY"]:
                res = self.kernel.dispatch(self.player_id, ActionType.PROXY_FIGHT, ticker=current_ticker)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif choice in ["D", "DIVIDEND"]:
                res = self.kernel.dispatch(self.player_id, ActionType.BOARD_VOTE, ticker=current_ticker, mandate="SPECIAL_DIVIDEND")
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif choice in ["R", "RESTRUCTURE"]:
                print("Select New Core Industry: 1: MINING, 2: AGRICULTURE, 3: MANUFACTURING, 4: EXOTIC_ELEMENTS")
                i_choice = input(f"{c_gold('Industry [1-4] > ')}").strip()
                i_map = {"1": "MINING", "2": "AGRICULTURE", "3": "MANUFACTURING", "4": "EXOTIC_ELEMENTS"}
                new_ind = i_map.get(i_choice, "MANUFACTURING")
                res = self.kernel.dispatch(self.player_id, ActionType.BOARD_VOTE, ticker=current_ticker, mandate="CHANGE_INDUSTRY", industry=new_ind)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif choice in ["E", "EMBARGO"]:
                target = input(f"{c_gold('Enter Captain ID to embargo (e.g. ai_malakor) > ')}").strip()
                if target:
                    res = self.kernel.dispatch(self.player_id, ActionType.BOARD_VOTE, ticker=current_ticker, mandate="CORPORATE_EMBARGO", target_id=target)
                    self._print_result(res)
                    input(c_gold("Press Enter to continue..."))

            elif choice in ["S", "STRIP"]:
                confirm = input(f"{c_red('Extract 25% of corporate treasury as Chairman bonus? (Reduces stock price) [Y/N] > ')}").strip().upper()
                if confirm == "Y":
                    res = self.kernel.dispatch(self.player_id, ActionType.BOARD_VOTE, ticker=current_ticker, mandate="STRIP_ASSETS")
                    self._print_result(res)
                    input(c_gold("Press Enter to continue..."))

            elif choice in ["A", "PILL"]:
                res = self.kernel.dispatch(self.player_id, ActionType.POISON_PILL, ticker=current_ticker)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif choice in ["W", "TARIFF"]:
                try:
                    sec_num = active_comp["sector_id"]
                    t_val = int(input(f"{c_gold(f'Enter Sector customs transit tariff % [0-50] (Current: Sec {sec_num:03d}) > ')}").strip())
                    res = self.kernel.dispatch(self.player_id, ActionType.SET_TARIFF, sector_id=sec_num, tariff_pct=t_val)
                    self._print_result(res)
                except ValueError:
                    print(c_red("Tariff must be an integer between 0 and 50."))
                input(c_gold("Press Enter to continue..."))

    def _prompt_stock_short_cover(self, view: Dict[str, Any]) -> None:
        """Prompt to execute a Bear Raid short sale or cover an existing short position."""
        market = view.get("market", {})
        companies = market.get("companies", [])
        short_positions = market.get("short_positions", {})
        print(f"\n{bold(c_magenta('══════════════ [ ISSE SHORT SELLING & BEAR RAIDS ] ══════════════'))}")
        print("Borrow shares from market float to bet against corporate valuation (50% margin required).")
        print(f"  {c_gold('[1]')} Short Sell Stock (Bear Raid - Borrow and Sell Float)")
        print(f"  {c_gold('[2]')} Cover Short Position (Buy Back & Release Collateral)")
        print(f"  {c_gold('[B]')} Back to Exchange")
        try:
            choice = input(f"{c_gold('Select Short Action [1/2/B] > ')}").strip().upper()
            if not choice or choice in ["B", "BACK"]:
                return

            if choice == "1":
                ticker = input(f"{c_gold('Enter ticker symbol to short sell (e.g. VOSS, ADME) > ')}").strip().upper()
                if not ticker:
                    return
                comp = next((c for c in companies if c["ticker"] == ticker), None)
                if not comp:
                    print(c_red(f"Company '{ticker}' not found on the exchange."))
                    return

                price = comp["share_price"]
                cash = view.get("player", {}).get("credits", 0)
                max_short = (cash * 2) // price if price > 0 else 0
                print(f"Ticker: {bold(c_gold(ticker))} │ Market Price: {price} Cr │ Margin Required: 50% ({price // 2} Cr/share) │ Max Short: {max_short:,}")
                amt_str = input(f"{c_gold(f'Quantity of shares to short sell [1-{max_short}] (default 100) > ')}").strip()
                amt = int(amt_str) if (amt_str and amt_str.isdigit()) else 100
                res = self.kernel.dispatch(self.player_id, ActionType.STOCK_SHORT, ticker=ticker, amount=amt)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif choice == "2":
                if not short_positions:
                    print(c_red("You do not have any open short positions."))
                    input(c_gold("Press Enter to continue..."))
                    return

                ticker = input(f"{c_gold(f'Enter ticker to cover {list(short_positions.keys())} > ')}").strip().upper()
                if not ticker or ticker not in short_positions:
                    print(c_red(f"No active short position in '{ticker}'."))
                    return

                open_sh = short_positions[ticker]["shares"]
                amt_str = input(f"{c_gold(f'Quantity of shares to buy back & cover [1-{open_sh}] (default all: {open_sh}) > ')}").strip()
                amt = int(amt_str) if (amt_str and amt_str.isdigit()) else open_sh
                res = self.kernel.dispatch(self.player_id, ActionType.STOCK_COVER, ticker=ticker, amount=amt)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))
        except (KeyboardInterrupt, EOFError):
            return

    def _prompt_corporate_machine(self, view: Dict[str, Any]) -> None:
        """Command deck for Sales Executives, PR Marketing Campaigns, and Trade Council Lobbying."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            player = self.kernel.get_player(self.player_id)
            if not player:
                break

            print(TerminalRenderer.render_corporate_machine_screen(fresh_view))
            print(f"\n{bold(c_cyan('Corporate Machine Operations:'))}")
            print(f"  {c_gold('[1]')} Hire Sales Executive (2,500 Cr)")
            print(f"  {c_gold('[2]')} Dispatch / Move Sales Executive")
            print(f"  {c_gold('[3]')} Launch Positive PR Media Campaign (3,000 Cr)")
            print(f"  {c_gold('[4]')} Launch Smear Campaign Against Competitor (4,500 Cr)")
            print(f"  {c_gold('[5]')} Contribute to Trade Council Lobbying Pool")
            print(f"  {c_gold('[6]')} Enact Interstellar Regulatory Legislation (Senate Bill)")
            print(f"  {c_gold('[B]')} Back to Exchange")
            try:
                choice = input(f"{bold(c_white('Corporate Operation [1-6 / B] > '))}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not choice or choice in ["B", "BACK", "R", "RETURN"]:
                break

            market = fresh_view.get("market", {})
            companies = market.get("companies", [])
            controlled = [c for c in companies if c.get("chairman_id") == self.player_id or c.get("founder_id") == self.player_id]

            if choice == "1":
                if not controlled:
                    print(c_red("Must be Chairman or Founder of a corporation to hire sales executives."))
                    input(c_gold("Press Enter to continue..."))
                    continue
                avail_tickers = [c["ticker"] for c in controlled]
                ticker = input(f"{c_gold(f'Enter Corporate Ticker to hire for {avail_tickers} > ')}").strip().upper()
                name = input(f"{c_gold('Enter Executive Name (or Enter for auto-generated) > ')}").strip()
                res = self.kernel.dispatch(self.player_id, ActionType.EXECUTIVE_HIRE, ticker=ticker, name=name)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif choice == "2":
                my_execs = market.get("executives", [])
                if not my_execs:
                    print(c_red("You do not employ any sales executives."))
                    input(c_gold("Press Enter to continue..."))
                    continue
                my_exec_ids = [e["id"] for e in my_execs]
                exec_id = input(f"{c_gold(f'Enter Executive ID to move {my_exec_ids} > ')}").strip().upper()
                try:
                    dest_sec = int(input(f"{c_gold('Enter Destination Sector ID > ')}").strip())
                    res = self.kernel.dispatch(self.player_id, ActionType.EXECUTIVE_MOVE, exec_id=exec_id, destination=dest_sec)
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid sector ID."))
                input(c_gold("Press Enter to continue..."))

            elif choice == "3":
                if not controlled:
                    print(c_red("Must be Chairman or Founder of a corporation to launch PR campaigns."))
                    input(c_gold("Press Enter to continue..."))
                    continue
                avail_tickers = [c["ticker"] for c in controlled]
                ticker = input(f"{c_gold(f'Enter Corporate Ticker for Positive PR blitz {avail_tickers} > ')}").strip().upper()
                res = self.kernel.dispatch(self.player_id, ActionType.MARKETING_CAMPAIGN, ticker=ticker, campaign_type="POSITIVE")
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif choice == "4":
                if not controlled:
                    print(c_red("Must be Chairman or Founder of a corporation to launch marketing ops."))
                    input(c_gold("Press Enter to continue..."))
                    continue
                avail_tickers = [c["ticker"] for c in controlled]
                ticker = input(f"{c_gold(f'Enter Your Corporate Ticker {avail_tickers} > ')}").strip().upper()
                target_ticker = input(f"{c_gold('Enter Rival Ticker to Smear & Sabotage > ')}").strip().upper()
                res = self.kernel.dispatch(self.player_id, ActionType.MARKETING_CAMPAIGN, ticker=ticker, campaign_type="SMEAR", target_ticker=target_ticker)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif choice == "5":
                try:
                    amt = int(input(f"{c_gold('Credits to inject into Interstellar Trade Council lobbying pool > ')}").strip())
                    res = self.kernel.dispatch(self.player_id, ActionType.LOBBY_CONTRIBUTE, amount=amt)
                    self._print_result(res)
                except ValueError:
                    print(c_red("Invalid credit amount."))
                input(c_gold("Press Enter to continue..."))

            elif choice == "6":
                print("Select Regulatory Bill to Enact:")
                print("  1: SUBSIDY (+5,000 Cr quarterly federal grant to sponsor company)")
                print("  2: TARIFF_SANCTIONS (Impose 30% customs surcharge on rival shipments)")
                print("  3: CORE_EMBARGO (Ban rival company from trading in Federation Core Sectors 1-10)")
                b_sel = input(f"{c_gold('Select Bill [1-3] > ')}").strip()
                b_map = {"1": "SUBSIDY", "2": "TARIFF_SANCTIONS", "3": "CORE_EMBARGO"}
                bill_type = b_map.get(b_sel, "SUBSIDY")
                sponsor_ticker = input(f"{c_gold('Sponsoring Corporation Ticker (or Enter for personal) > ')}").strip().upper() or None
                target_ticker = None
                if bill_type in ["TARIFF_SANCTIONS", "CORE_EMBARGO"]:
                    target_ticker = input(f"{c_gold('Target Rival Corporation Ticker > ')}").strip().upper()
                res = self.kernel.dispatch(
                    self.player_id,
                    ActionType.COUNCIL_VOTE,
                    bill_type=bill_type,
                    sponsor_ticker=sponsor_ticker,
                    target_ticker=target_ticker
                )
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

    def _prompt_stock_buy(self, view: Dict[str, Any]) -> None:
        """Prompt to purchase shares on the ISSE."""
        market = view.get("market", {})
        companies = market.get("companies", [])
        if not companies:
            print(c_red("No companies listed on the exchange."))
            return

        ticker = input(f"{c_gold('Enter ticker symbol to buy (e.g. VOSS, ADME, SHBI) > ')}").strip().upper()
        if not ticker:
            return

        comp = next((c for c in companies if c["ticker"] == ticker), None)
        if not comp:
            print(c_red(f"Company with ticker '{ticker}' not found."))
            return

        price = comp["share_price"]
        avail = comp.get("available_shares", 0)
        cash = view.get("player", {}).get("credits", 0)
        max_affordable = cash // price if price > 0 else 0
        max_buy = min(avail, max_affordable)

        print(f"Ticker: {bold(c_gold(ticker))} │ Price: {price} Cr/share │ Available Float: {avail:,} │ Max Affordable: {max_buy:,}")
        amt_str = input(f"{c_gold(f'Quantity of shares to buy [1-{max_buy}] (default 100) > ')}").strip()
        if not amt_str:
            amt = min(100, max_buy) if max_buy > 0 else 0
        elif amt_str.isdigit():
            amt = int(amt_str)
        else:
            print(c_red("Invalid quantity."))
            return

        if amt <= 0:
            print(c_red("Order quantity must be greater than zero."))
            return

        res = self.kernel.dispatch(self.player_id, ActionType.STOCK_BUY, ticker=ticker, amount=amt)
        self._print_result(res)
        input(c_gold("Press Enter to continue..."))

    def _prompt_stock_sell(self, view: Dict[str, Any]) -> None:
        """Prompt to liquidate owned shares on the ISSE."""
        market = view.get("market", {})
        portfolio = market.get("portfolio", {})
        if not portfolio:
            print(c_red("You do not hold any corporate shares."))
            input(c_gold("Press Enter to continue..."))
            return

        ticker = input(f"{c_gold('Enter ticker symbol to liquidate > ')}").strip().upper()
        if not ticker:
            return

        owned = portfolio.get(ticker, 0)
        if owned <= 0:
            print(c_red(f"You hold 0 shares of '{ticker}'."))
            return

        amt_str = input(f"{c_gold(f'Quantity of shares to sell [1-{owned}] (default all: {owned}) > ')}").strip()
        if not amt_str:
            amt = owned
        elif amt_str.isdigit():
            amt = int(amt_str)
        else:
            print(c_red("Invalid quantity."))
            return

        res = self.kernel.dispatch(self.player_id, ActionType.STOCK_SELL, ticker=ticker, amount=amt)
        self._print_result(res)
        input(c_gold("Press Enter to continue..."))

    def _prompt_colony_ipo(self, view: Dict[str, Any]) -> None:
        """Prompt to float an Initial Public Offering (IPO) for a sovereign colonized world."""
        sector = view.get("sector", {})
        planets = sector.get("planets", [])
        my_planets = [p for p in planets if p.get("owner_id") == self.player_id]

        if not my_planets:
            print(c_red("Must be docked at a planetary colony you govern (Citadel Tier 1+) to float an IPO."))
            input(c_gold("Press Enter to continue..."))
            return

        target_planet = my_planets[0]
        target_name = target_planet.get("name", "Colony")
        sec_num = sector.get("id", 1)
        if target_planet.get("citadel_tier", 0) < 1:
            print(c_red(f"Colony {target_name} requires Citadel Tier 1+ Redoubt to float an IPO (Current: Tier {target_planet.get('citadel_tier', 0)})."))
            input(c_gold("Press Enter to continue..."))
            return

        print(f"\n{bold(c_cyan(f'=== INITIAL PUBLIC OFFERING: {target_name} (Sector {sec_num:03d}) ==='))}")
        print("Mints 10,000 corporate shares. Founder retains 6,000 (60%). 4,000 shares floated to raise capital into planetary vault.")
        print("Listing Fee: 3,000 Credits.")

        name = input(f"{c_gold('Enter Enterprise Name (e.g. Avalon Extraction Corp) > ')}").strip()
        if not name:
            name = f"{target_name} Enterprises"

        ticker = input(f"{c_gold('Enter Stock Ticker Symbol (3-5 capital letters) > ')}").strip().upper()
        if not ticker or len(ticker) < 3 or len(ticker) > 5:
            print(c_red("Invalid ticker. Must be 3-5 letters."))
            return

        print("Select Core Industry:")
        print("  1: MINING (Heavy metals & ore extraction)")
        print("  2: AGRICULTURE (Biotic foods & hydroponics)")
        print("  3: MANUFACTURING (Equipment & hull dynamics)")
        print("  4: EXOTIC_ELEMENTS (Periodic table synth & refined matter)")
        ind_choice = input(f"{c_gold('Industry [1-4] > ')}").strip()
        ind_map = {"1": "MINING", "2": "AGRICULTURE", "3": "MANUFACTURING", "4": "EXOTIC_ELEMENTS"}
        industry = ind_map.get(ind_choice, "MINING")

        res = self.kernel.dispatch(
            self.player_id,
            ActionType.COMPANY_IPO,
            planet_id=target_planet["id"],
            name=name,
            ticker=ticker,
            industry=industry,
        )
        self._print_result(res)
        input(c_gold("Press Enter to continue..."))

    def _prompt_freight_board(self, view: Dict[str, Any]) -> None:
        """Galactic Freight Haulage and Delivery Command Center."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            player = self.kernel.get_player(self.player_id)
            if not player:
                break

            print(TerminalRenderer.render_freight_board_screen(fresh_view))
            print(f"\n{bold(c_cyan('Freight Dispatch:'))} "
                  f"{c_gold('[A]')}ccept Contract │ {c_gold('[P]')}lot Course │ {c_gold('[D]')}eliver Cargo │ {c_gold('[R]')}eturn")
            try:
                choice = input(f"{bold(c_white('Freight Action [A/P/D/R] > '))}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not choice or choice in ["R", "RETURN", "BACK", "Q"]:
                self.clear_screen()
                break

            if choice == "A":
                open_contracts = fresh_view.get("market", {}).get("open_contracts", [])
                if not open_contracts:
                    print(c_red("No open contracts available."))
                    continue
                cid_in = input(f"{c_gold('Enter Contract ID to accept (e.g. FRT-101 or 1-12) > ')}").strip().upper()
                if not cid_in:
                    continue
                target_cid = cid_in
                if cid_in.isdigit():
                    idx = int(cid_in) - 1
                    if 0 <= idx < len(open_contracts):
                        target_cid = open_contracts[idx]["id"]

                res = self.kernel.dispatch(self.player_id, ActionType.FREIGHT_ACCEPT, contract_id=target_cid)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif choice == "P":
                # Plot course to freight contract origin or destination
                open_contracts = fresh_view.get("market", {}).get("open_contracts", [])
                active_contracts = fresh_view.get("market", {}).get("active_contracts", [])
                all_c = active_contracts + open_contracts
                if not all_c:
                    print(c_red("No available or active contracts to plot."))
                    input(c_gold("Press Enter to continue..."))
                    continue

                cid_in = input(f"{c_gold('Enter Contract ID or # to plot course > ')}").strip().upper()
                if not cid_in:
                    continue
                target_c = None
                if cid_in.isdigit():
                    idx = int(cid_in) - 1
                    if 0 <= idx < len(all_c):
                        target_c = all_c[idx]
                else:
                    target_c = next((c for c in all_c if c["id"] == cid_in), None)

                if not target_c:
                    print(c_red(f"Contract '{cid_in}' not found."))
                    input(c_gold("Press Enter to continue..."))
                    continue

                curr_sec = fresh_view.get("sector", {}).get("id", 1)
                # If active, destination is target. If open, origin is target unless already there.
                if target_c["status"] == "IN_TRANSIT" or curr_sec == target_c["origin_sector"]:
                    target_sec = target_c["destination_sector"]
                    target_label = f"Destination: {target_c['destination_name']} (Sector {target_sec:03d})"
                else:
                    target_sec = target_c["origin_sector"]
                    target_label = f"Origin: {target_c['origin_name']} (Sector {target_sec:03d})"

                path = self.kernel.find_path(curr_sec, target_sec)
                print(TerminalRenderer.render_nav_computer(curr_sec, target_sec, path))
                print(f"Contract {target_c['id']} ──► Course locked to {target_label}")
                if len(path) > 1:
                    conf = input(f"{c_gold(f'Engage autopilot jump to Sector {target_sec:03d} (First hop: {path[1]:03d})? [Y/N] > ')}").strip().upper()
                    if conf == "Y":
                        self._do_move(path[1])
                        break
                else:
                    input(c_gold("Press Enter to continue..."))

            elif choice == "D":
                active = fresh_view.get("market", {}).get("active_contracts", [])
                if not active:
                    print(c_red("You do not have any active freight contracts in transit."))
                    input(c_gold("Press Enter to continue..."))
                    continue

                curr_planets = fresh_view.get("sector", {}).get("planets", [])
                if not curr_planets:
                    print(c_red("No colony in this sector to verify cargo delivery."))
                    input(c_gold("Press Enter to continue..."))
                    continue

                default_cid = active[0]["id"]
                cid_in = input(f"{c_gold(f'Enter Contract ID to deliver [{default_cid}] > ')}").strip().upper()
                if not cid_in:
                    cid_in = default_cid

                planet_id = curr_planets[0]["id"]
                res = self.kernel.dispatch(self.player_id, ActionType.FREIGHT_DELIVER, contract_id=cid_in, planet_id=planet_id)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

    def _prompt_cartography(self, view: Dict[str, Any]) -> None:
        """Interactive Cartography Lab & Starmap Puzzle Matrix console."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            self.clear_screen()
            print(TerminalRenderer.render_cartography_screen(fresh_view))

            cart_data = fresh_view.get("cartography", {})
            active_p = cart_data.get("active_puzzle")
            p_id = active_p.get("puzzle_id") if active_p else None

            try:
                cmd_line = input(f"\n{bold(c_white('Cartography Command [S/R/B/P/K/T/D/F/C/V/Q] > '))}")
            except (KeyboardInterrupt, EOFError):
                break

            cmd_parts = cmd_line.strip().split()
            if not cmd_parts:
                continue

            cmd = cmd_parts[0].upper()
            if cmd in ["Q", "QUIT", "EXIT", "BACK"]:
                self.clear_screen()
                break

            elif cmd in ["S", "SCAN"]:
                frags = cart_data.get("fragments", [])
                if not frags:
                    print(c_red("No starmap fragments in cargo hold. Acquire via broker [C]hit or deep-space [V] Salvage."))
                    input(c_gold("Press Enter to continue..."))
                    continue

                frag_id = None
                if len(cmd_parts) > 1 and cmd_parts[1].isdigit():
                    f_idx = int(cmd_parts[1]) - 1
                    if 0 <= f_idx < len(frags):
                        frag_id = frags[f_idx].get("id")
                elif len(frags) == 1:
                    frag_id = frags[0].get("id")
                else:
                    print("Select fragment to scan:")
                    for idx, f in enumerate(frags, 1):
                        print(f"  [{idx}] {f.get('name')} ({f.get('rarity')})")
                    f_sel = input(f"{c_gold('Fragment # to scan [1-' + str(len(frags)) + '] > ')}").strip()
                    if f_sel.isdigit() and 1 <= int(f_sel) <= len(frags):
                        frag_id = frags[int(f_sel) - 1].get("id")

                res = self.kernel.dispatch(self.player_id, ActionType.CARTOGRAPHY_SCAN, fragment_id=frag_id, puzzle_id=p_id)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif cmd in ["R", "ROTATE"]:
                r, c = None, None
                if len(cmd_parts) >= 3 and cmd_parts[1].isdigit() and cmd_parts[2].isdigit():
                    r, c = int(cmd_parts[1]), int(cmd_parts[2])
                else:
                    coords = input(f"{c_gold('Enter node coordinates to rotate (row col, 0-2 e.g. 0 1) > ')}").strip().split()
                    if len(coords) >= 2 and coords[0].isdigit() and coords[1].isdigit():
                        r, c = int(coords[0]), int(coords[1])

                if r is not None and c is not None:
                    res = self.kernel.dispatch(self.player_id, ActionType.CARTOGRAPHY_ROTATE, row=r, col=c, puzzle_id=p_id)
                    self._print_result(res)
                else:
                    print(c_red("Invalid coordinates. Must specify row and column between 0 and 2."))
                input(c_gold("Press Enter to continue..."))

            elif cmd in ["B", "BRIDGE"]:
                r1, c1, r2, c2 = None, None, None, None
                if len(cmd_parts) >= 5 and all(p.isdigit() for p in cmd_parts[1:5]):
                    r1, c1, r2, c2 = int(cmd_parts[1]), int(cmd_parts[2]), int(cmd_parts[3]), int(cmd_parts[4])
                else:
                    coords = input(f"{c_gold('Enter two adjacent nodes to bridge (r1 c1 r2 c2, e.g. 0 1 0 2) > ')}").strip().split()
                    if len(coords) >= 4 and all(p.isdigit() for p in coords[:4]):
                        r1, c1, r2, c2 = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])

                if None not in (r1, c1, r2, c2):
                    res = self.kernel.dispatch(self.player_id, ActionType.CARTOGRAPHY_BRIDGE, r1=r1, c1=c1, r2=r2, c2=c2, puzzle_id=p_id)
                    self._print_result(res)
                else:
                    print(c_red("Invalid coordinates. Must specify r1 c1 r2 c2."))
                input(c_gold("Press Enter to continue..."))

            elif cmd in ["P", "PICK", "PUZZLE"]:
                all_p = cart_data.get("all_puzzles", [])
                if not all_p:
                    print(c_red("No starmap puzzles available."))
                    input(c_gold("Press Enter to continue..."))
                    continue

                print("\nAvailable Cartographic Matrices:")
                for idx, p in enumerate(all_p, 1):
                    act_tag = c_green("[ACTIVE]") if p.get("is_active") else c_gray("[SELECT]")
                    print(f"  [{idx}] {act_tag} {p.get('name')} -> Unlocks: {p.get('target_title')} ({p.get('progress_pct', 0)}%)")

                p_choice = input(f"{c_gold('Select Matrix [1-' + str(len(all_p)) + '] > ')}").strip()
                if p_choice.isdigit() and 1 <= int(p_choice) <= len(all_p):
                    target_pid = all_p[int(p_choice) - 1]["puzzle_id"]
                    res = self.kernel.dispatch(self.player_id, ActionType.CARTOGRAPHY_SELECT, puzzle_id=target_pid)
                    self._print_result(res)
                else:
                    print(c_red("Invalid selection."))
                input(c_gold("Press Enter to continue..."))

            elif cmd in ["K", "CATALYZE"]:
                elem = cmd_parts[1].upper() if len(cmd_parts) > 1 else None
                amt = int(cmd_parts[2]) if len(cmd_parts) > 2 and cmd_parts[2].isdigit() else 5
                res = self.kernel.dispatch(self.player_id, ActionType.CARTOGRAPHY_CATALYZE, puzzle_id=p_id, element=elem, amount=amt)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif cmd in ["T", "TOLL"]:
                print("\nOrbital Toll Gate Command:")
                print("  [D] Deploy new toll satellite on unlocked shortcut (5,000 Cr)")
                print("  [F] Configure transit fee on an existing toll gate")
                t_choice = input(f"{c_gold('Toll Action [D/F] > ')}").strip().upper()
                if t_choice == "D":
                    sec_choice = input(f"{c_gold('Shortcut ID to toll [SMUGGLER_SHORTCUT / GHOST_NEXUS] > ')}").strip() or "SMUGGLER_SHORTCUT"
                    fee_in = input(f"{c_gold('Transit Fee (100-2,500 Cr, default 500) > ')}").strip()
                    fee = int(fee_in) if fee_in.isdigit() else 500
                    res = self.kernel.dispatch(self.player_id, ActionType.TOLL_GATE_DEPLOY, shortcut_id=sec_choice, toll_fee=fee)
                    self._print_result(res)
                elif t_choice == "F":
                    gid = input(f"{c_gold('Toll Gate ID (e.g. TOLL-100) > ')}").strip().upper()
                    fee_in = input(f"{c_gold('New Transit Fee (100-2,500 Cr) > ')}").strip()
                    fee = int(fee_in) if fee_in.isdigit() else 500
                    res = self.kernel.dispatch(self.player_id, ActionType.TOLL_GATE_SET_FEE, gate_id=gid, toll_fee=fee)
                    self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif cmd in ["D", "DRONE", "PROBE"]:
                target_in = input(f"{c_gold('Target Frontier Sector for Deep-Space Survey Probe (default 61) > ')}").strip()
                t_sec = int(target_in) if target_in.isdigit() else 61
                res = self.kernel.dispatch(self.player_id, ActionType.SURVEY_PROBE_LAUNCH, target_sector=t_sec)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif cmd in ["F", "FORGE"]:
                print("\nCartographic Espionage & Forgery Counter-Intel:")
                print("  [S] Sell forged chit to shady port broker (+3,000 Cr profit)")
                print("  [P] Plant fake coordinates in rival star-vault (ambush rival in Anarchy)")
                f_mode = input(f"{c_gold('Forgery Mode [S/P] > ')}").strip().upper()
                mode_str = "plant" if f_mode == "P" else "sell"
                rival = None
                if mode_str == "plant":
                    rival = input(f"{c_gold('Target Rival Captain ID (or press Enter for random AI) > ')}").strip() or None
                res = self.kernel.dispatch(self.player_id, ActionType.CARTOGRAPHY_FORGE_CHIT, mode=mode_str, target_rival_id=rival)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif cmd in ["C", "CHIT", "BROKER"]:
                res = self.kernel.dispatch(self.player_id, ActionType.CARTOGRAPHY_BUY_CHIT)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            elif cmd in ["V", "SALVAGE"]:
                res = self.kernel.dispatch(self.player_id, ActionType.CARTOGRAPHY_SALVAGE)
                self._print_result(res)
                input(c_gold("Press Enter to continue..."))

            else:
                print(c_red(f"Unknown cartography command '{cmd}'. [S/R/B/P/K/T/D/F/C/V/Q]"))
                input(c_gold("Press Enter to continue..."))

    def _prompt_radio(self) -> None:
        """Handle sending a subspace radio broadcast."""
        try:
            msg = input(f"{c_cyan('Subspace Radio Broadcast > ')}").strip()
            if msg:
                res = self.kernel.dispatch(self.player_id, ActionType.RADIO_BROADCAST, text=msg)
                print(c_green("✔ Broadcast dispatched across subspace channels."))
        except (KeyboardInterrupt, EOFError):
            return

    def _prompt_ideology(self, view: Dict[str, Any]) -> None:
        """Handle diplomacy, treaties, and famine aid."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_ideology_screen(fresh_view))
            try:
                cmd = input(f"{c_gold('Diplomacy Command [P/S/D/Q] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd or cmd in ["Q", "QUIT", "B", "BACK"]:
                self.clear_screen()
                break

            if cmd == "P":
                try:
                    target = input("Target Entity / Rival Captain ID: ").strip()
                    ttype = input("Treaty Type (NON_AGGRESSION, TRADE_ACCORD, DEFENSIVE_PACT, ALLIANCE): ").strip().upper()
                    if not ttype:
                        ttype = "NON_AGGRESSION"
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.IDEOLOGY_TREATY_PROPOSE,
                        target_id=target,
                        treaty_type=ttype,
                    )
                    self._print_result(res)
                except (KeyboardInterrupt, EOFError):
                    break
            elif cmd == "S":
                try:
                    tid = input("Treaty ID to sign and ratify: ").strip()
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.IDEOLOGY_TREATY_SIGN,
                        treaty_id=tid,
                    )
                    self._print_result(res)
                except (KeyboardInterrupt, EOFError):
                    break
            elif cmd == "D":
                try:
                    pid = input("Colony Planet ID (or Enter for local world): ").strip()
                    units = int(input("Crates of Organics to dispatch as relief aid (e.g. 20): ").strip() or "20")
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.IDEOLOGY_AID_DISPATCH,
                        planet_id=pid,
                        food_units=units,
                    )
                    self._print_result(res)
                except (ValueError, KeyboardInterrupt, EOFError):
                    print(c_red("Invalid input."))

    def _prompt_alchemy(self, view: Dict[str, Any]) -> None:
        """Handle Precursor transmutation and matter balance."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_alchemy_screen(fresh_view))
            try:
                cmd = input(f"{c_gold('Alchemy Command [T/A/Q] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd or cmd in ["Q", "QUIT", "B", "BACK"]:
                self.clear_screen()
                break

            if cmd == "T":
                try:
                    rec_id = input("Recipe ID to synthesize (e.g. ADAMANT_LODE, SPIRAL_RIME): ").strip().upper()
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.ALCHEMY_TRANSMUTE,
                        recipe_id=rec_id,
                    )
                    self._print_result(res)
                except (KeyboardInterrupt, EOFError):
                    break
            elif cmd == "A":
                all_recs = fresh_view.get("alchemy", {}).get("all_recipes", [])
                print(f"\n{bold(c_cyan('ALL CANONICAL PRECURSOR RECIPES:'))}")
                for r in all_recs:
                    print(f"  ► {c_gold(r['id'])}: {r['name']} -> +{r['output_qty']} [{r['output_element']}] (Req: {r.get('required_tech') or 'None'})")
                input(c_gold("\nPress Enter to continue..."))

    def _prompt_astronomy(self, view: Dict[str, Any]) -> None:
        """Handle planetary orbital ephemeris and astrodynamic radar."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_astronomy_screen(fresh_view))
            try:
                cmd = input(f"{c_gold('Astronomy Command [W/R/Q] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd or cmd in ["Q", "QUIT", "B", "BACK"]:
                self.clear_screen()
                break

            if cmd == "W":
                planets = fresh_view.get("sector", {}).get("planets", [])
                if len(planets) < 2:
                    print(c_red("Transit window requires at least 2 planetary bodies in system."))
                    continue
                p1 = self.kernel.get_planet(planets[0]["id"])
                p2 = self.kernel.get_planet(planets[1]["id"])
                if p1 and p2 and hasattr(self.kernel, "astronomy_manager"):
                    win = self.kernel.astronomy_manager.compute_transit_window(p1, p2)
                    print(f"\n{bold(c_cyan('ASTRODYNAMIC TRANSIT WINDOW:'))} {p1.name} ◄─► {p2.name}")
                    print(f"  Effective Distance D_eff: {c_gold(f'{win.effective_distance_au:.3f} AU')}")
                    print(f"  Transit Multiplier: {c_green(f'{win.transit_multiplier:.2f}x')} [{win.window_grade}]")
                    print(f"  Angular Phase Delta: {win.delta_angle_deg:.1f}°")
                    print(f"  Cycles to Conjunction: {win.cycles_to_next_conjunction} cycles\n")
                    input(c_gold("Press Enter to continue..."))

    def _prompt_senate(self, view: Dict[str, Any]) -> None:
        """Handle Imperial Senate elections and Edicts."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_senate_screen(fresh_view))
            try:
                cmd = input(f"{c_gold('Senate Command [C/V/E/Q] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd or cmd in ["Q", "QUIT", "B", "BACK"]:
                self.clear_screen()
                break

            if cmd == "C":
                try:
                    office = input("Office to campaign for (CHANCELLOR, FLEET_ADMIRAL, MASTER_OF_COIN, HIGH_INQUISITOR): ").strip().upper()
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.SENATE_CAMPAIGN,
                        office=office,
                    )
                    self._print_result(res)
                except (KeyboardInterrupt, EOFError):
                    break
            elif cmd == "V":
                try:
                    office = input("Office ballot: ").strip().upper()
                    cand = input("Candidate ID to vote for: ").strip()
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.SENATE_VOTE,
                        office=office,
                        candidate_id=cand,
                    )
                    self._print_result(res)
                except (KeyboardInterrupt, EOFError):
                    break
            elif cmd == "E":
                try:
                    office = input("Office jurisdiction: ").strip().upper()
                    edict = input("Edict name (SOL_STIMULUS_REBATE, MARTIAL_LAW_PICKET, UNIVERSAL_TARIFF, PRECURSOR_DECLASSIFICATION): ").strip().upper()
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.SENATE_ENACT_EDICT,
                        office=office,
                        edict=edict,
                    )
                    self._print_result(res)
                except (KeyboardInterrupt, EOFError):
                    break

    def _prompt_surface(self, view: Dict[str, Any], planet_id: Optional[str] = None) -> None:
        """Handle 8x8 planetary surface district development and ground assault."""
        while True:
            fresh_view = self.kernel.get_player_view(self.player_id)
            print(TerminalRenderer.render_surface_screen(fresh_view, planet_id))
            try:
                cmd = input(f"{c_gold('Surface Command [B/D/R/I/Q] > ')}").strip().upper()
            except (KeyboardInterrupt, EOFError):
                break

            if not cmd or cmd in ["Q", "QUIT", "BACK"]:
                self.clear_screen()
                break

            if cmd == "B":
                try:
                    x = int(input("Surface X coordinate (0-7): ").strip())
                    y = int(input("Surface Y coordinate (0-7): ").strip())
                    print("Available Districts: HABITATION_DOME, HYDROPONIC_SPIRE, MANTLE_BORE, GEOTHERMAL_DYNAMO, ELEMENT_REFINERY, CITADEL_FORTRESS, MILITARY_BARRACKS")
                    dist = input("District Type: ").strip().upper()
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.SURFACE_BUILD_DISTRICT,
                        planet_id=planet_id,
                        x=x,
                        y=y,
                        district=dist,
                    )
                    self._print_result(res)
                except (ValueError, KeyboardInterrupt, EOFError):
                    print(c_red("Invalid coordinates."))
            elif cmd == "D":
                try:
                    x = int(input("Surface X coordinate (0-7): ").strip())
                    y = int(input("Surface Y coordinate (0-7): ").strip())
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.SURFACE_DEMOLISH_DISTRICT,
                        planet_id=planet_id,
                        x=x,
                        y=y,
                    )
                    self._print_result(res)
                except (ValueError, KeyboardInterrupt, EOFError):
                    print(c_red("Invalid coordinates."))
            elif cmd == "R":
                try:
                    divs = int(input("Assault troop divisions to recruit (250 Cr + 5 Ore/div): ").strip())
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.SURFACE_RECRUIT_TROOPS,
                        planet_id=planet_id,
                        divisions=divs,
                    )
                    self._print_result(res)
                except (ValueError, KeyboardInterrupt, EOFError):
                    print(c_red("Invalid division count."))
            elif cmd == "I":
                try:
                    divs = int(input("Assault divisions to drop onto planet: ").strip())
                    res = self.kernel.dispatch(
                        self.player_id,
                        ActionType.SURFACE_INVADE,
                        planet_id=planet_id,
                        divisions=divs,
                    )
                    self._print_result(res)
                except (ValueError, KeyboardInterrupt, EOFError):
                    print(c_red("Invalid drop division count."))

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


def lineage_genesis(seed: int, player_name: Optional[str] = None, clade: Optional[str] = None,
                    background: Optional[str] = None, legacy_file: Optional[str] = None,
                    interactive: bool = True):
    """
    Lineage Genesis: a new universe bound to exactly one player lineage. The founder chooses a
    clade and background (their biology and origins are then fixed for the life of the kernel).
    Returns (kernel, player_id).
    """
    from xylarium.config import LINEAGE_CLADES, STARTING_BACKGROUNDS, CLADE_RANK_MATRIX, LINEAGE_LEGACY_FILE
    from xylarium.kernel import lineage as lineage_mod
    if interactive:
        print(bold(c_cyan("\n=== LINEAGE GENESIS ===")))
        print(c_gray("Your lineage is bound to this universe for its whole life. Choose its biology and its origins."))
        for i, c in enumerate(LINEAGE_CLADES, 1):
            info = CLADE_RANK_MATRIX.get(c, {})
            print(f"  {c_gold(f'[{i}]')} {info.get('name', c):<24} {c_gray(info.get('description', '')[:52])}")
        try:
            raw = input(c_gold("Clade [1] > ")).strip()
            clade = LINEAGE_CLADES[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(LINEAGE_CLADES) else (clade or LINEAGE_CLADES[0])
            fits = [b for b, d in STARTING_BACKGROUNDS.items() if d["clade"] == clade]
            if fits:
                print(c_gray("Origins open to this clade:"))
                for i, b in enumerate(fits, 1):
                    print(f"  {c_gold(f'[{i}]')} {STARTING_BACKGROUNDS[b]['name']}: {c_gray(STARTING_BACKGROUNDS[b]['description'][:58])}")
                print(f"  {c_gold('[0]')} Unaffiliated captain (standard charter)")
                raw = input(c_gold("Origin [0] > ")).strip()
                background = fits[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(fits) else None
            name = input(c_gold(f"Founder's name [{player_name or 'Captain Solo'}] > ")).strip()
            player_name = name or player_name or "Captain Solo"
        except (KeyboardInterrupt, EOFError):
            clade, background, player_name = clade or "BIOTIC", background, player_name or "Captain Solo"
    kernel = GameKernel(seed=seed)
    kernel.single_lineage = True
    kernel.legacy_file = legacy_file or LINEAGE_LEGACY_FILE
    remembered = lineage_mod.import_hall(kernel, kernel.legacy_file)
    player_id = "player_1"
    kernel.register_player(player_id, player_name or "Captain Solo", clade=clade, background=background, bind_lineage=True)
    if interactive:
        house = kernel.lineage["house"]
        print(c_green(f"The {house} is founded ({clade.title() if clade else 'Biotic'} clade)."
                      + (f" The Library remembers {remembered} lineage(s) before yours." if remembered else "")))
    return kernel, player_id


def run_interactive_cli(player_name: str = "Captain Solo", save_file: str = "xylarium_save.json", seed: int = 42) -> None:
    """Bootstraps universe or loads save, and launches interactive terminal client."""
    kernel = None
    if os.path.exists(save_file):
        kernel = StatePersistence.load_from_file(save_file)
    player_id = "player_1"
    if not kernel:
        kernel, player_id = lineage_genesis(seed, player_name)
    else:
        if not kernel.get_player(player_id):
            human_caps = [c for c in kernel.captains.values() if not c.is_ai]
            if human_caps:
                player_id = human_caps[0].id
            else:
                kernel.register_player(player_id, player_name)
    client = TerminalClient(kernel=kernel, player_id=player_id, player_name=player_name, save_file=save_file)
    client.run()

