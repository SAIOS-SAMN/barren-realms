"""
Classic RFC 854 Telnet / TCP Socket Server for the Xylarium Mycelium Bridge.
Allows remote network terminals to log straight into the live MUD universe via port 2002.
"""

import asyncio
from typing import Optional, Dict, Any, Set
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType
from xylarium.client.renderer import TerminalRenderer
from xylarium.client.ansi import (
    TITLE_BANNER, c_cyan, c_gold, c_green, c_red, c_white, bold
)


TELNET_WELCOME_BANNER = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        XYLARIUM BBS DOOR - TELNET NODE (RFC 854 on PORT 2002)                ║
║        TradeWars 2002 x Barren Realms Elite x Solar Realms Elite             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


class TelnetSession:
    """Represents a remote Telnet terminal session."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, kernel: GameKernel):
        self.reader = reader
        self.writer = writer
        self.kernel = kernel
        self.player_id: Optional[str] = None
        self.running = True

    async def write_text(self, text: str) -> None:
        """Writes UTF-8 text with standard Telnet CRLF line endings."""
        # Convert standalone \n to \r\n for raw Telnet terminal compliance
        normalized = text.replace("\r\n", "\n").replace("\n", "\r\n")
        self.writer.write(normalized.encode("utf-8", errors="replace"))
        await self.writer.drain()

    async def read_line(self, prompt: str = "") -> str:
        """Prompts and reads a line of input, stripping Telnet IAC sequences."""
        if prompt:
            await self.write_text(prompt)
        raw_line = await self.reader.readline()
        if not raw_line:
            self.running = False
            return ""

        # Filter out Telnet IAC commands (0xFF ...)
        cleaned = bytearray()
        i = 0
        while i < len(raw_line):
            if raw_line[i] == 0xFF:
                # Skip 3-byte IAC sequences
                i += 3
            else:
                cleaned.append(raw_line[i])
                i += 1

        return cleaned.decode("utf-8", errors="replace").strip()

    async def run(self) -> None:
        """Session main loop."""
        try:
            await self.write_text("\033[2J\033[H")
            await self.write_text(TITLE_BANNER)
            await self.write_text(TELNET_WELCOME_BANNER)

            # Prompt for Handle
            handle = await self.read_line(f"\n{bold(c_cyan('Enter your Captain Handle > '))} ")
            if not handle or not self.running:
                return

            self.player_id = f"telnet_{handle.lower().replace(' ', '_')}"
            if not self.kernel.get_player(self.player_id):
                self.kernel.register_player(self.player_id, handle)

            await self.write_text(f"\n{c_green('✔ Telemetry linked. Initializing HUD...')}\n")
            await asyncio.sleep(0.5)

            # Main interactive prompt loop
            while self.running:
                view = self.kernel.get_player_view(self.player_id)
                if not view:
                    break

                # Clear and render HUD + Sector
                await self.write_text("\033[2J\033[H")
                await self.write_text(TerminalRenderer.render_hud(view) + "\n")
                await self.write_text(TerminalRenderer.render_sector(view) + "\n")

                # Command prompt
                cmd = await self.read_line(f"\n{bold(c_white('Telnet Command [M/T/P/A/S/C/R/H/Q] > '))} ")
                if not self.running:
                    break

                cmd = cmd.strip().upper()
                if not cmd:
                    continue

                if cmd in ["Q", "QUIT", "9"]:
                    await self.write_text(c_gold("\nDisconnecting from Xylarium Telnet Node. Safe travels, Captain!\r\n"))
                    break

                await self._dispatch_command(cmd, view)

        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            self.running = False
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass

    async def _dispatch_command(self, cmd: str, view: Dict[str, Any]) -> None:
        """Dispatches commands over Telnet connection."""
        action_key = cmd[0]

        # Direct number movement (e.g. typing "2" to warp to Sector 2)
        if cmd.isdigit():
            dest = int(cmd)
            res = self.kernel.dispatch(self.player_id, ActionType.MOVE, destination=dest)
            if not res.success:
                await self.write_text(c_red(f"\nNavigation Error: {res.message}\r\n"))
                await asyncio.sleep(1.0)
            return

        if action_key == "M" or cmd == "1":
            warps = view.get("sector", {}).get("warps", [])
            warp_ids = [w["sector_id"] for w in warps]
            warp_str = ", ".join([f"{w:03d}" for w in warp_ids])
            dest_str = await self.read_line(f"Warp destination [{warp_str}]: ")
            if dest_str.isdigit():
                res = self.kernel.dispatch(self.player_id, ActionType.MOVE, destination=int(dest_str))
                if not res.success:
                    await self.write_text(c_red(f"\nNavigation Error: {res.message}\r\n"))
                    await asyncio.sleep(1.0)

        elif action_key == "T" or cmd == "2":
            await self._run_telnet_trade(view)

        elif action_key == "P" or cmd == "3":
            await self._run_telnet_planet(view)

        elif action_key == "A" or cmd == "4":
            await self._run_telnet_attack(view)

        elif action_key == "S" or cmd == "5":
            await self._run_telnet_shipyard(view)

        elif action_key == "C" or cmd == "6":
            curr_sec = view.get("sector", {}).get("id", 1)
            target_str = await self.read_line("Destination Sector for BFS Plot [1-100]: ")
            if target_str.isdigit():
                target = int(target_str)
                path = self.kernel.find_path(curr_sec, target)
                await self.write_text(TerminalRenderer.render_nav_computer(curr_sec, target, path) + "\r\n")
                await self.read_line(c_gold("Press Enter to continue... "))

        elif action_key == "R" or cmd == "7":
            msg = await self.read_line(c_cyan("Subspace Radio Broadcast > "))
            if msg:
                self.kernel.dispatch(self.player_id, ActionType.RADIO_BROADCAST, text=msg)

        elif action_key == "H" or cmd == "8":
            await self.write_text("\033[2J\033[H")
            await self.write_text(TerminalRenderer.render_help() + "\r\n")
            await self.read_line(c_gold("Press Enter to return to navigation... "))

        else:
            await self.write_text(c_red(f"\nUnknown command: '{cmd}'. Press H for help.\r\n"))
            await asyncio.sleep(1.0)

    async def _run_telnet_trade(self, view: Dict[str, Any]) -> None:
        """Interactive trading sub-menu over Telnet."""
        if not view.get("sector", {}).get("port"):
            await self.write_text(c_red("\nNo trade port in this sector!\r\n"))
            await asyncio.sleep(1.0)
            return

        while self.running:
            fresh_view = self.kernel.get_player_view(self.player_id)
            await self.write_text("\033[2J\033[H")
            await self.write_text(TerminalRenderer.render_trade_screen(fresh_view) + "\r\n")
            t_cmd = await self.read_line(c_gold("Trade Command [B/S/X] > "))
            if not t_cmd or t_cmd.upper() in ["X", "EXIT", "Q"]:
                break

            parts = t_cmd.split()
            act = parts[0].upper()
            if act in ["B", "BUY"] and len(parts) >= 3:
                comm = parts[1].upper()
                if comm in ["1", "ORE"]: comm = "ORE"
                elif comm in ["2", "ORG", "ORGANICS"]: comm = "ORGANICS"
                elif comm in ["3", "EQ", "EQUIPMENT"]: comm = "EQUIPMENT"
                try:
                    amt = int(parts[2])
                    res = self.kernel.dispatch(self.player_id, ActionType.TRADE, type="BUY", commodity=comm, amount=amt)
                    msg = c_green(f"✔ {res.message}") if res.success else c_red(f"Denied: {res.message}")
                    await self.write_text(f"\n{msg}\r\n")
                    await asyncio.sleep(1.2)
                except ValueError:
                    pass
            elif act in ["S", "SELL"] and len(parts) >= 3:
                comm = parts[1].upper()
                if comm in ["1", "ORE"]: comm = "ORE"
                elif comm in ["2", "ORG", "ORGANICS"]: comm = "ORGANICS"
                elif comm in ["3", "EQ", "EQUIPMENT"]: comm = "EQUIPMENT"
                try:
                    amt = int(parts[2])
                    res = self.kernel.dispatch(self.player_id, ActionType.TRADE, type="SELL", commodity=comm, amount=amt)
                    msg = c_green(f"✔ {res.message}") if res.success else c_red(f"Denied: {res.message}")
                    await self.write_text(f"\n{msg}\r\n")
                    await asyncio.sleep(1.2)
                except ValueError:
                    pass

    async def _run_telnet_planet(self, view: Dict[str, Any]) -> None:
        """Planetary operations over Telnet."""
        planets = view.get("sector", {}).get("planets", [])
        if not planets:
            await self.write_text(c_red("\nNo planetary bodies in this sector.\r\n"))
            await asyncio.sleep(1.0)
            return

        planet = planets[0]
        while self.running:
            fresh_view = self.kernel.get_player_view(self.player_id)
            planet_list = fresh_view.get("sector", {}).get("planets", [])
            if not planet_list:
                break
            planet = planet_list[0]

            await self.write_text("\033[2J\033[H")
            await self.write_text(TerminalRenderer.render_planet_screen(fresh_view, planet) + "\r\n")
            p_cmd = await self.read_line(c_gold("Colony Command > "))
            if not p_cmd or p_cmd.upper() in ["B", "BACK", "X", "EXIT"]:
                break

            key = p_cmd.upper()[0]
            if key == "C":
                res = self.kernel.dispatch(self.player_id, ActionType.PLANET_CLAIM, planet_id=planet["id"])
                await self._show_result(res)
            elif key == "T":
                res = self.kernel.dispatch(self.player_id, ActionType.PLANET_TAX, planet_id=planet["id"])
                await self._show_result(res)
            elif key == "I":
                cr_str = await self.read_line("Credits to invest in population: ")
                if cr_str.isdigit():
                    res = self.kernel.dispatch(self.player_id, ActionType.PLANET_INVEST, planet_id=planet["id"], credits=int(cr_str))
                    await self._show_result(res)
            elif key == "S":
                pts_str = await self.read_line("Shield points to build: ")
                if pts_str.isdigit():
                    res = self.kernel.dispatch(self.player_id, ActionType.PLANET_BUILD_SHIELD, planet_id=planet["id"], points=int(pts_str))
                    await self._show_result(res)
            elif key == "U":
                res = self.kernel.dispatch(self.player_id, ActionType.PLANET_UPGRADE_CITADEL, planet_id=planet["id"])
                await self._show_result(res)

    async def _run_telnet_attack(self, view: Dict[str, Any]) -> None:
        """Tactical attack menu over Telnet."""
        captains = view.get("sector", {}).get("captains", [])
        if not captains:
            await self.write_text(c_red("\nNo target vessels in this sector.\r\n"))
            await asyncio.sleep(1.0)
            return

        target = captains[0]
        res = self.kernel.dispatch(self.player_id, ActionType.ATTACK_SHIP, target_id=target["id"])
        await self._show_result(res)

    async def _run_telnet_shipyard(self, view: Dict[str, Any]) -> None:
        """Shipyard operations over Telnet."""
        if view.get("sector", {}).get("id") != 1:
            await self.write_text(c_red("\nFederation Shipyard is at Sector 1.\r\n"))
            await asyncio.sleep(1.0)
            return

        fresh_view = self.kernel.get_player_view(self.player_id)
        await self.write_text("\033[2J\033[H")
        await self.write_text(TerminalRenderer.render_shipyard_screen(fresh_view) + "\r\n")
        choice = await self.read_line(c_gold("Shipyard Order [1-5 / B] > "))
        if choice == "1":
            res = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="shields")
            await self._show_result(res)
        elif choice == "2":
            f_qty = await self.read_line("Quantity of combat fighters: ")
            if f_qty.isdigit():
                res = self.kernel.dispatch(self.player_id, ActionType.SHIPYARD_PURCHASE, item="fighters", amount=int(f_qty))
                await self._show_result(res)

    async def _show_result(self, res) -> None:
        """Helper to display result logs."""
        color = c_green if res.success else c_red
        await self.write_text(f"\n{color(res.message)}\r\n")
        await asyncio.sleep(1.5)


class TelnetServer:
    """Manages the RFC 854 Telnet socket listener."""

    def __init__(self, kernel: GameKernel, host: str = "0.0.0.0", port: int = 2002):
        self.kernel = kernel
        self.host = host
        self.port = port
        self.server: Optional[asyncio.Server] = None
        self.sessions: Set[TelnetSession] = set()

    async def start(self) -> None:
        """Starts the Telnet TCP listener."""
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)

    async def stop(self) -> None:
        """Terminates Telnet server and closes all active terminal sessions."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        for session in list(self.sessions):
            session.running = False
        self.sessions.clear()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        session = TelnetSession(reader, writer, self.kernel)
        self.sessions.add(session)
        try:
            await session.run()
        finally:
            self.sessions.discard(session)
