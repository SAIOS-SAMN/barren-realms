"""
Autonomous AI Agent Client Loop for Xylarium.
Connects via WebSocket, parses player_view, evaluates personality-driven heuristics,
and dispatches real-time actions over the network bridge.
"""

import asyncio
import json
import random
import sys
import os
import base64
import struct
from urllib.parse import urlparse
from typing import Dict, Any, Optional

from xylarium.client.ansi import (
    c_cyan, c_gold, c_green, c_red, c_magenta, c_white, c_gray, bold,
    BRIGHT_WHITE, BRIGHT_CYAN, BRIGHT_YELLOW, BRIGHT_GREEN, BRIGHT_RED, RESET
)

# Optional external websockets support with zero-dependency stdlib fallback
try:
    import websockets
    HAS_WEBSOCKETS_PKG = True
except ImportError:
    HAS_WEBSOCKETS_PKG = False


class StdlibWebSocketClient:
    """Zero-dependency RFC 6455 async WebSocket client."""

    def __init__(self, uri: str):
        parsed = urlparse(uri)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 8765
        self.path = parsed.path or "/ws"
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.closed = False

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        raw_key = base64.b64encode(random.randbytes(16))
        req = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {raw_key.decode()}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.writer.write(req.encode("utf-8"))
        await self.writer.drain()

        # Read HTTP 101 Switching Protocols headers
        while True:
            line = await self.reader.readline()
            if not line or line == b"\r\n":
                break

    async def send(self, data_str: str) -> None:
        if self.closed:
            return
        payload = data_str.encode("utf-8")
        mask = random.randbytes(4)
        masked = bytearray(len(payload))
        for i in range(len(payload)):
            masked[i] = payload[i] ^ mask[i % 4]

        length = len(payload)
        header = bytearray([0x81])
        if length <= 125:
            header.append(0x80 | length)
        elif length <= 65535:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))

        self.writer.write(header + mask + masked)
        await self.writer.drain()

    async def recv(self) -> str:
        while True:
            head = await self.reader.readexactly(2)
            opcode = head[0] & 0x0F
            has_mask = bool(head[1] & 0x80)
            payload_len = head[1] & 0x7F
            if payload_len == 126:
                ext = await self.reader.readexactly(2)
                payload_len = struct.unpack("!H", ext)[0]
            elif payload_len == 127:
                ext = await self.reader.readexactly(8)
                payload_len = struct.unpack("!Q", ext)[0]

            mask_key = b""
            if has_mask:
                mask_key = await self.reader.readexactly(4)

            payload = await self.reader.readexactly(payload_len)
            if has_mask:
                unmasked = bytearray(payload_len)
                for i in range(payload_len):
                    unmasked[i] = payload[i] ^ mask_key[i % 4]
                payload = unmasked

            if opcode == 0x8:  # Close
                self.closed = True
                raise ConnectionResetError("WebSocket closed by server")
            elif opcode == 0x9:  # Ping
                self.writer.write(bytearray([0x8A, 0]))
                await self.writer.drain()
                continue
            elif opcode == 0x1:  # Text
                return payload.decode("utf-8")

    async def close(self) -> None:
        self.closed = True
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def connect_ws(uri: str):
    """Returns an async context manager for WebSocket connections."""
    if HAS_WEBSOCKETS_PKG:
        return websockets.connect(uri)
    return StdlibWebSocketClient(uri)


class AIAgentClient:
    """Autonomous AI rival captain that runs as a dedicated client process."""

    def __init__(
        self,
        uri: str = "ws://127.0.0.1:8765/ws",
        name: str = "AIAgent",
        personality: str = "trader",
        tick_rate: float = 2.0,
        headless: bool = False
    ):
        self.uri = uri
        self.name = name
        self.personality = personality.lower()
        self.tick_rate = tick_rate
        self.headless = headless
        self.running = True
        self.step_count = 0
        self.last_action_desc = "Initializing telemetry"

    async def run(self) -> None:
        """Connects to server and executes autonomous decision loop."""
        print(f"[{self.name}] Connecting to Xylarium Gateway at {self.uri}...")

        try:
            async with connect_ws(self.uri) as websocket:
                # 1. Read initial server handshake ACK if present
                try:
                    init_ack = await asyncio.wait_for(websocket.recv(), timeout=1.5)
                except asyncio.TimeoutError:
                    pass

                # 2. Register Captain Handle
                await websocket.send(json.dumps({
                    "action": "REGISTER",
                    "name": self.name,
                    "personality": self.personality
                }))
                reg_resp_raw = await websocket.recv()
                reg_resp = json.loads(reg_resp_raw)
                player_id = reg_resp.get("player_id", self.name)
                print(c_green(f"✔ [{self.name}] Registered successfully as ID: {player_id}"))

                # 3. Autonomous Turn Loop
                while self.running:
                    try:
                        # Request current view
                        await websocket.send(json.dumps({"action": "VIEW", "player_id": player_id}))
                        view_raw = await websocket.recv()
                        view_data = json.loads(view_raw)

                        # Filter out stream events to get view
                        while view_data.get("type") == "STREAM_EVENT":
                            view_raw = await websocket.recv()
                            view_data = json.loads(view_raw)

                        view = view_data.get("view", view_data)

                        # Evaluate personality heuristic
                        action_payload = self.decide_action(view)
                        if action_payload:
                            action_payload["player_id"] = player_id
                            await websocket.send(json.dumps(action_payload))
                            res_raw = await websocket.recv()
                            while json.loads(res_raw).get("type") == "STREAM_EVENT":
                                res_raw = await websocket.recv()
                            res = json.loads(res_raw)

                            result_info = res.get("result", {})
                            msg = result_info.get("message", "Executed")
                            self.last_action_desc = msg

                            if not self.headless:
                                self._render_agent_dashboard(view, action_payload, msg)
                            else:
                                print(f"[{self.name} ({self.personality.upper()})] Action: {msg}")

                        self.step_count += 1
                        await asyncio.sleep(self.tick_rate)

                    except (ConnectionResetError, asyncio.CancelledError):
                        print(f"[{self.name}] Server connection terminated.")
                        break

        except Exception as e:
            print(c_red(f"[{self.name}] Connection failed: {e}"))

    def decide_action(self, view: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluates tactical state and returns next action payload."""
        player = view.get("player", {})
        sector_info = view.get("sector", {})
        sector_id = sector_info.get("id", view.get("sector", 1))
        turns = player.get("turns_left", view.get("turns", 50))
        credits = player.get("credits", view.get("credits", 1000))
        cargo = player.get("ship", {}).get("cargo", {})
        warps = view.get("adjacent_sectors", [w["sector_id"] for w in sector_info.get("warps", [])])
        port = sector_info.get("port")
        planets = sector_info.get("planets", [])
        captains = sector_info.get("captains", [])

        if turns <= 0 or not warps:
            return None

        # 1. TRADER HEURISTIC
        if self.personality == "trader":
            # If at port, check if we have cargo to sell
            if port:
                cat = port.get("catalog", {})
                for comm in ["ORE", "ORGANICS", "EQUIPMENT"]:
                    held = cargo.get(comm.lower(), 0)
                    if held > 0 and cat.get(comm, {}).get("port_buys"):
                        return {"action": "DISPATCH", "command": "TRADE", "params": {"type": "SELL", "commodity": comm, "amount": held}}

                # Buy cheap goods if we have free holds
                free_space = cargo.get("available", 20)
                if free_space > 0:
                    for comm in ["ORE", "ORGANICS", "EQUIPMENT"]:
                        comm_data = cat.get(comm, {})
                        if comm_data.get("port_sells") and comm_data.get("stock", 0) > 20:
                            price = comm_data.get("sell_price", 100)
                            if credits >= price * 5:
                                buy_amt = min(free_space, credits // price, 15)
                                if buy_amt > 0:
                                    return {"action": "DISPATCH", "command": "TRADE", "params": {"type": "BUY", "commodity": comm, "amount": buy_amt}}

            # Otherwise warp along trading routes
            dest = random.choice(warps)
            return {"action": "DISPATCH", "command": f"M {dest}"}

        # 2. PIRATE HEURISTIC
        elif self.personality == "pirate":
            # If target ship present and outside Fed Core, attack!
            sec_level = sector_info.get("security", "FEDERATION")
            if captains and sec_level != "FEDERATION":
                target = random.choice(captains)
                return {"action": "DISPATCH", "command": "ATTACK_SHIP", "params": {"target_id": target["id"]}}

            # If rival planet present outside Fed Core, raid!
            if planets and sec_level != "FEDERATION":
                target_p = planets[0]
                if target_p.get("owner_id") and target_p.get("owner_id") != player.get("id"):
                    return {"action": "DISPATCH", "command": "ATTACK_PLANET", "params": {"planet_id": target_p["id"]}}

            # Warp towards deeper anarchy sectors
            anarchy_warps = [w for w in warps if w > 50]
            dest = random.choice(anarchy_warps) if anarchy_warps else random.choice(warps)
            return {"action": "DISPATCH", "command": f"M {dest}"}

        # 3. INDUSTRIALIST HEURISTIC
        elif self.personality == "industrialist":
            # If unowned planet in sector: claim colony!
            if planets:
                p = planets[0]
                if not p.get("owner_id"):
                    return {"action": "DISPATCH", "command": "PLANET_CLAIM", "params": {"planet_id": p["id"]}}
                elif p.get("owner_id") == player.get("id"):
                    # Upgrade or reinforce
                    if credits >= 3000 and p.get("citadel_level", 0) < 3:
                        return {"action": "DISPATCH", "command": "PLANET_UPGRADE_CITADEL", "params": {"planet_id": p["id"]}}
                    elif credits >= 500:
                        return {"action": "DISPATCH", "command": "PLANET_BUILD_SHIELD", "params": {"planet_id": p["id"], "points": 20}}

            dest = random.choice(warps)
            return {"action": "DISPATCH", "command": f"M {dest}"}

        # 4. MERCENARY HEURISTIC
        elif self.personality == "mercenary":
            sec_level = sector_info.get("security", "FEDERATION")
            if captains and sec_level != "FEDERATION":
                for c in captains:
                    if c.get("personality") == "pirate":
                        return {"action": "DISPATCH", "command": "ATTACK_SHIP", "params": {"target_id": c["id"]}}

            dest = random.choice(warps)
            return {"action": "DISPATCH", "command": f"M {dest}"}

        # Fallback wander
        return {"action": "DISPATCH", "command": f"M {random.choice(warps)}"}

    def _render_agent_dashboard(self, view: Dict[str, Any], action: Dict[str, Any], result_msg: str) -> None:
        """Renders live ASCII telemetry dashboard for the autonomous agent."""
        player = view.get("player", {})
        sector = view.get("sector", {})
        s_id = sector.get("id", 1)
        sec_str = sector.get("security", "FEDERATION")
        turns = player.get("turns_left", 0)
        credits = player.get("credits", 0)
        ship = player.get("ship", {})

        print(f"\033[2J\033[H", end="")
        print(f"{bold(c_cyan('╔══════════════════════════════════════════════════════════════════════════════╗'))}")
        print(f"║ {c_gold(f'AGENT NODE:')} {bold(c_white(self.name))} [{c_magenta(self.personality.upper())}] │ Step: {self.step_count} │ Turns: {c_gold(str(turns))} ║")
        print(f"║ Sector: {c_gold(f'#{s_id:03d}')} [{sec_str}] │ Credits: {c_gold(f'{credits:,} Cr')} │ Ship: {ship.get('ship_type', 'Scout')} ║")
        print(f"{bold(c_cyan('╚══════════════════════════════════════════════════════════════════════════════╝'))}")
        print(f"\n{bold(c_white('► COGNITIVE TRACE:'))}")
        print(f"  {c_gray('Dispatch:')} {c_cyan(str(action.get('command')))}")
        print(f"  {c_gray('Result:')}   {c_green(result_msg)}")
        print(f"  {c_gray('Status:')}   {c_gold('Observing universe and awaiting next simulation tick...')}\n")
