"""
Zero-dependency RFC 6455 WebSocket Gateway for the Xylarium Mycelium Bridge.
Provides JSON dispatching, real-time player views, and event streaming via pure Python asyncio.
"""

import asyncio
import hashlib
import base64
import json
import struct
from typing import Dict, Any, Set, Optional
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType


WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WebSocketClient:
    """Represents a connected WebSocket client session."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.player_id: Optional[str] = None
        self.closed = False

    async def send_json(self, data: Dict[str, Any]) -> None:
        """Encodes and transmits an RFC 6455 unmasked text frame."""
        if self.closed:
            return
        payload = json.dumps(data).encode("utf-8")
        length = len(payload)

        # Header byte 1: FIN=1, Opcode=1 (Text) -> 0x81
        header = bytearray([0x81])

        # Payload length encoding
        if length <= 125:
            header.append(length)
        elif length <= 65535:
            header.append(126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(127)
            header.extend(struct.pack("!Q", length))

        try:
            self.writer.write(header + payload)
            await self.writer.drain()
        except Exception:
            self.closed = True

    async def read_frame(self) -> Optional[str]:
        """Reads and decodes an RFC 6455 client masked text frame."""
        try:
            head = await self.reader.readexactly(2)
        except (asyncio.IncompleteReadError, ConnectionResetError):
            return None

        byte1, byte2 = head[0], head[1]
        opcode = byte1 & 0x0F
        has_mask = bool(byte2 & 0x80)
        payload_len = byte2 & 0x7F

        # Close frame (0x8)
        if opcode == 0x8:
            return None

        # Extended payload length
        if payload_len == 126:
            ext_len = await self.reader.readexactly(2)
            payload_len = struct.unpack("!H", ext_len)[0]
        elif payload_len == 127:
            ext_len = await self.reader.readexactly(8)
            payload_len = struct.unpack("!Q", ext_len)[0]

        # Masking key
        mask_key = b""
        if has_mask:
            mask_key = await self.reader.readexactly(4)

        # Payload data
        payload = await self.reader.readexactly(payload_len)

        # Unmask payload
        if has_mask:
            unmasked = bytearray(payload_len)
            for i in range(payload_len):
                unmasked[i] = payload[i] ^ mask_key[i % 4]
            payload = unmasked

        return payload.decode("utf-8", errors="replace")

    def close(self) -> None:
        self.closed = True
        try:
            self.writer.close()
        except Exception:
            pass


class WebSocketGateway:
    """Manages WebSocket server lifecycle and dispatches messages to GameKernel."""

    def __init__(self, kernel: GameKernel, host: str = "0.0.0.0", port: int = 8765):
        self.kernel = kernel
        self.host = host
        self.port = port
        self.clients: Set[WebSocketClient] = set()
        self.server: Optional[asyncio.Server] = None
        # Subscribe to EventBus to broadcast live radio and sector events to all WS peers
        self.kernel.event_bus.subscribe(self._on_kernel_event)

    def _on_kernel_event(self, event_payload: Dict[str, Any]) -> None:
        """Broadcasts real-time events to all active WebSocket clients."""
        for client in list(self.clients):
            if not client.closed:
                asyncio.create_task(client.send_json({
                    "type": "STREAM_EVENT",
                    "event": event_payload.get("event"),
                    "data": event_payload.get("data")
                }))

    async def start(self) -> None:
        """Starts the WebSocket gateway TCP listener."""
        self.server = await asyncio.start_server(self._handle_connection, self.host, self.port)

    async def stop(self) -> None:
        """Closes all client connections and shuts down listener."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        for client in list(self.clients):
            client.close()
        self.clients.clear()

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handles HTTP upgrade handshake and initiates message loop."""
        # 1. Read HTTP Request
        request_lines = []
        while True:
            line = await reader.readline()
            if not line or line == b"\r\n":
                break
            request_lines.append(line.decode("utf-8", errors="replace").strip())

        if not request_lines:
            writer.close()
            return

        headers = {}
        for h in request_lines[1:]:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        # Check for WebSocket Upgrade
        sec_key = headers.get("sec-websocket-key")
        if not sec_key:
            # Not a websocket request
            writer.write(b"HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\n\r\nExpected WebSocket Upgrade.")
            await writer.drain()
            writer.close()
            return

        # 2. Compute Accept Key
        accept_raw = hashlib.sha1((sec_key + WS_GUID).encode("utf-8")).digest()
        accept_str = base64.b64encode(accept_raw).decode("utf-8")

        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_str}\r\n\r\n"
        )
        writer.write(response.encode("utf-8"))
        await writer.drain()

        # 3. Enter WebSocket Session
        client = WebSocketClient(reader, writer)
        self.clients.add(client)

        # Send initial handshake ACK
        await client.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to Xylarium Mycelium Bridge WebSocket Gateway.",
            "version": "1.0.0"
        })

        try:
            while not client.closed:
                msg = await client.read_frame()
                if msg is None:
                    break

                try:
                    payload = json.loads(msg)
                except Exception:
                    await client.send_json({"status": "error", "message": "Invalid JSON payload."})
                    continue

                await self._process_client_message(client, payload)
        finally:
            self.clients.discard(client)
            client.close()

    async def _process_client_message(self, client: WebSocketClient, payload: Dict[str, Any]) -> None:
        """Dispatches commands from WebSocket payload."""
        action = payload.get("action", "").upper()

        if action == "REGISTER":
            name = payload.get("name", "Remote Captain")
            sanitized_id = name.lower().replace(" ", "_").replace(".", "")
            p_id = payload.get("player_id", f"remote_{sanitized_id}")
            client.player_id = p_id
            captain = self.kernel.get_player(p_id)
            if not captain:
                captain = self.kernel.register_player(p_id, name)
            pers = payload.get("personality")
            if pers:
                try:
                    from xylarium.kernel.models import AIPersonality
                    captain.personality = AIPersonality(pers.lower())
                except Exception:
                    pass
            view = self.kernel.get_player_view(p_id)
            await client.send_json({
                "status": "ok",
                "action": "REGISTER",
                "player_id": p_id,
                "view": view
            })

        elif action == "VIEW":
            p_id = payload.get("player_id", client.player_id)
            if not p_id:
                await client.send_json({"status": "error", "message": "No player_id specified or registered."})
                return
            view = self.kernel.get_player_view(p_id)
            await client.send_json({
                "status": "ok",
                "action": "VIEW",
                "view": view
            })

        elif action == "DISPATCH":
            p_id = payload.get("player_id", client.player_id)
            cmd_str = payload.get("command", "").strip().upper()
            params = payload.get("params", {})

            if not p_id:
                await client.send_json({"status": "error", "message": "Must specify player_id."})
                return

            cmd_type = None
            if cmd_str.startswith("M ") or cmd_str.startswith("MOVE "):
                parts = cmd_str.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    cmd_type = ActionType.MOVE
                    params = {"destination": int(parts[1])}
            elif cmd_str in ["P", "PLANET"]:
                view = self.kernel.get_player_view(p_id)
                planets = view.get("sector", {}).get("planets", [])
                if planets:
                    p = planets[0]
                    if p.get("owner_id") is None:
                        cmd_type = ActionType.PLANET_CLAIM
                        params = {"planet_id": p["id"]}
                    elif p.get("owner_id") == p_id:
                        cmd_type = ActionType.PLANET_UPGRADE_CITADEL
                        params = {"planet_id": p["id"]}
                    else:
                        cmd_type = ActionType.ATTACK_PLANET
                        params = {"planet_id": p["id"]}
                else:
                    cmd_type = ActionType.SCAN
            else:
                try:
                    cmd_type = ActionType(cmd_str)
                except ValueError:
                    await client.send_json({"status": "error", "message": f"Unknown action: '{cmd_str}'."})
                    return

            res = self.kernel.dispatch(p_id, cmd_type, **params)
            new_view = self.kernel.get_player_view(p_id)

            await client.send_json({
                "status": "ok",
                "action": "DISPATCH",
                "command": cmd_str,
                "result": {
                    "success": res.success,
                    "message": res.message,
                    "turns_spent": res.turns_spent,
                    "data": res.data,
                    "logs": res.logs,
                },
                "view": new_view
            })

        else:
            await client.send_json({
                "status": "error",
                "message": f"Unsupported action: '{action}'. Use REGISTER, VIEW, or DISPATCH."
            })
