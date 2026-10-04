"""
Unit and integration tests for the Mycelium Bridge (WebSocket Gateway & Telnet Server).
"""

import unittest
import asyncio
import hashlib
import base64
import json
import struct
from xylarium.kernel.engine import GameKernel
from bridge.websocket_server import WebSocketGateway, WS_GUID
from bridge.telnet_server import TelnetServer


class TestMyceliumBridge(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.kernel = GameKernel(seed=999)
        self.ws_port = 8799
        self.telnet_port = 2099
        self.ws_gateway = WebSocketGateway(self.kernel, host="127.0.0.1", port=self.ws_port)
        self.telnet_server = TelnetServer(self.kernel, host="127.0.0.1", port=self.telnet_port)
        await self.ws_gateway.start()
        await self.telnet_server.start()

    async def asyncTearDown(self):
        await self.ws_gateway.stop()
        await self.telnet_server.stop()

    async def test_websocket_gateway_protocol(self):
        """Verify RFC 6455 handshake, REGISTER, VIEW, and DISPATCH over WebSocket."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.ws_port)

        # 1. Send WebSocket HTTP Upgrade
        raw_key = b"dGhlIHNhbXBsZSBub25jZQ=="
        request = (
            f"GET /ws HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.ws_port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {raw_key.decode()}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        writer.write(request.encode("utf-8"))
        await writer.drain()

        # Read HTTP 101 Response lines without overreading into WebSocket frames
        resp_lines = []
        while True:
            line = await reader.readline()
            if not line or line == b"\r\n":
                break
            resp_lines.append(line)

        resp_text = b"".join(resp_lines)
        self.assertIn(b"101 Switching Protocols", resp_text)
        expected_accept = base64.b64encode(hashlib.sha1(raw_key + WS_GUID.encode("utf-8")).digest()).decode()
        self.assertIn(f"Sec-WebSocket-Accept: {expected_accept}".encode(), resp_text)

        # Helper to read unmasked server WS frame
        async def read_ws_json():
            head = await reader.readexactly(2)
            payload_len = head[1] & 0x7F
            if payload_len == 126:
                ext = await reader.readexactly(2)
                payload_len = struct.unpack("!H", ext)[0]
            elif payload_len == 127:
                ext = await reader.readexactly(8)
                payload_len = struct.unpack("!Q", ext)[0]
            data = await reader.readexactly(payload_len)
            return json.loads(data.decode("utf-8"))

        # Helper to send masked client WS frame
        async def send_ws_json(payload_dict):
            payload = json.dumps(payload_dict).encode("utf-8")
            mask = b"\x12\x34\x56\x78"
            masked = bytearray(len(payload))
            for i in range(len(payload)):
                masked[i] = payload[i] ^ mask[i % 4]
            header = bytearray([0x81, 0x80 | len(payload)]) + mask
            writer.write(header + masked)
            await writer.drain()

        # Read connection ACK frame
        ack = await read_ws_json()
        self.assertEqual(ack.get("type"), "CONNECTION_ESTABLISHED")

        # 2. Test REGISTER action
        await send_ws_json({"action": "REGISTER", "name": "Agent Smith", "player_id": "agent_smith"})
        reg_resp = await read_ws_json()
        self.assertEqual(reg_resp.get("status"), "ok")
        self.assertEqual(reg_resp.get("player_id"), "agent_smith")
        self.assertEqual(reg_resp.get("view", {}).get("player", {}).get("name"), "Agent Smith")

        # 3. Test VIEW action
        await send_ws_json({"action": "VIEW", "player_id": "agent_smith"})
        view_resp = await read_ws_json()
        self.assertEqual(view_resp.get("status"), "ok")
        from xylarium.kernel import roles
        self.assertEqual(view_resp.get("view", {}).get("sector", {}).get("id"),
                         roles.tradewards(self.kernel)["sector"])        # a new captain berths at Tradewards

        # 4. Test DISPATCH action (MOVE to connected sector)
        warps = view_resp.get("view", {}).get("sector", {}).get("warps", [])
        dest_sector = warps[0]["sector_id"]
        await send_ws_json({
            "action": "DISPATCH",
            "player_id": "agent_smith",
            "command": "MOVE",
            "params": {"destination": dest_sector}
        })
        move_resp = await read_ws_json()
        self.assertEqual(move_resp.get("status"), "ok")
        self.assertTrue(move_resp.get("result", {}).get("success"))
        self.assertEqual(move_resp.get("view", {}).get("sector", {}).get("id"), dest_sector)

        writer.close()
        await writer.wait_closed()

    async def test_telnet_server_connection(self):
        """Verify Telnet node accepts connection, prompts for handle, and initializes session."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.telnet_port)

        # Read banner up to Handle prompt
        banner = b""
        while b"Enter your Captain Handle >" not in banner:
            chunk = await reader.read(512)
            if not chunk:
                break
            banner += chunk

        self.assertIn(b"XYLARIUM BBS DOOR - TELNET NODE", banner)

        # Send handle
        writer.write(b"Spock\r\n")
        await writer.drain()

        # Read telemetry linked and command prompt
        hud_output = b""
        while b"Command [M/T/P/A/S/C/R/H/Q] >" not in hud_output:
            chunk = await reader.read(512)
            if not chunk:
                break
            hud_output += chunk

        self.assertIn(b"XYLARIUM BBS", hud_output)
        self.assertIn(b"Credits:", hud_output)

        # Send Quit
        writer.write(b"Q\r\n")
        await writer.drain()

        # Read goodbye message
        goodbye = b""
        while b"Disconnecting" not in goodbye:
            chunk = await reader.read(512)
            if not chunk:
                break
            goodbye += chunk
        self.assertIn(b"Disconnecting", goodbye)

        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    unittest.main()
