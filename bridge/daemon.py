"""
Mycelium Bridge Daemon for Xylarium.
Runs the concurrent WebSocket Gateway (JSON API) and Telnet Server (RFC 854)
on a shared asynchronous event loop.
"""

import asyncio
import signal
import sys
import os
import argparse
from typing import Optional

# Ensure module path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xylarium.kernel.engine import GameKernel
from xylarium.persistence.store import StatePersistence
from bridge.websocket_server import WebSocketGateway
from bridge.telnet_server import TelnetServer
from xylarium.client.ansi import c_cyan, c_gold, c_green, c_red, c_gray, bold


TICK_S = 30.0                   # wall seconds per cycle: the server's frame rate (an operator's setting, not physics)


def stamp(kernel: GameKernel) -> None:
    """Keep the wall time of the universe's last cycle with it."""
    import time
    kernel.state.setdefault("server", {})["wall"] = time.time()


def catch_up(kernel: GameKernel, now: Optional[float] = None) -> int:
    """A served universe that was down runs the cycles its clock owed meanwhile - the orbits did not wait. Returns how
    many it ran."""
    import time
    wall = (kernel.state.get("server") or {}).get("wall")
    if wall is None:
        return 0
    owed = int(max(0.0, (now if now is not None else time.time()) - float(wall)) // TICK_S)
    for i in range(owed):
        kernel.tick_simulation()
        if owed >= 100 and (i + 1) % 100 == 0:
            print(f"  caught up {i + 1:,} of {owed:,} cycles...")
    stamp(kernel)
    return owed


def serve(kernel: GameKernel) -> None:
    """A universe served is live: a cosmic one still in its deep era is opened (cosmos.open_universe), then caught up
    to now."""
    from xylarium.kernel import cosmos
    if cosmos.is_cosmic(kernel) and not cosmos.live(kernel):
        cosmos.open_universe(kernel, "its server")
    ran = catch_up(kernel)
    if ran:
        print(f"Caught up {ran:,} cycles the universe ran while the server was down.")
    stamp(kernel)


class BridgeDaemon:
    """Manages the lifecycle of both WebSocket and Telnet endpoints."""

    def __init__(
        self,
        kernel: GameKernel,
        host: str = "0.0.0.0",
        ws_port: int = 8765,
        telnet_port: Optional[int] = 2002,
        save_file: str = "xylarium_save.json",
        enable_telnet: bool = False,
        enable_ws: bool = True,
    ):
        self.kernel = kernel
        self.host = host
        self.ws_port = ws_port
        self.telnet_port = telnet_port
        self.save_file = save_file
        self.enable_telnet = enable_telnet and (telnet_port is not None and telnet_port > 0)
        self.enable_ws = enable_ws and (ws_port is not None and ws_port > 0)
        self.ws_gateway = WebSocketGateway(kernel, host=host, port=ws_port) if self.enable_ws else None
        self.telnet_server = TelnetServer(kernel, host=host, port=telnet_port) if self.enable_telnet else None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Starts network listeners and runs the background universe tick loop."""
        if self.ws_gateway:
            await self.ws_gateway.start()
        if self.telnet_server:
            await self.telnet_server.start()

        print(bold(c_cyan("\n╔══════════════════════════════════════════════════════════════════════════════╗")))
        print(bold(c_cyan("║                XYLARIUM RUNTIME ENGINE DAEMON ONLINE                         ║")))
        print(bold(c_cyan("╠══════════════════════════════════════════════════════════════════════════════╣")))
        if self.ws_gateway:
            print(f"║  {bold('WebSocket Gateway')}: {c_gold(f'ws://{self.host}:{self.ws_port}/ws')} (JSON API & Event Stream)  ║")
        else:
            print(f"║  {bold('WebSocket Gateway')}: {c_gray('DISABLED')}                                                ║")
        if self.telnet_server:
            print(f"║  {bold('Telnet Node')}:       {c_gold(f'telnet {self.host} {self.telnet_port}')} (RFC 854 Terminal Door)     ║")
        else:
            print(f"║  {bold('Telnet Node')}:       {c_gray('DISABLED (No Telnet Mode)')}                               ║")
        print(f"║  {bold('Continuous Clock')}:  {c_green(f'Active (TICK_S={TICK_S:.0f}s, Orbit & Economy Recycling)')}     ║")
        print(bold(c_cyan("╚══════════════════════════════════════════════════════════════════════════════╝\n")))
        print(c_green("Runtime running. Press Ctrl+C to save state and terminate.\n"))

        # Background world tick task (runs every 30 seconds to simulate ambient universe activity)
        tick_task = asyncio.create_task(self._ambient_universe_ticker())

        try:
            await self._shutdown_event.wait()
        finally:
            tick_task.cancel()
            await self.stop()

    async def _ambient_universe_ticker(self) -> None:
        """The universe's one clock: a cycle every TICK_S of wall time, whoever is connected. The wall time of the last
        cycle is kept with the universe, so a server that was down catches up what its orbits ran meanwhile."""
        while not self._shutdown_event.is_set():
            await asyncio.sleep(TICK_S)
            self.kernel.tick_simulation()
            stamp(self.kernel)

    async def stop(self) -> None:
        """Gracefully shuts down listeners and persists universe state."""
        print("\nStopping Mycelium Bridge listeners...")
        if self.ws_gateway:
            await self.ws_gateway.stop()
        if self.telnet_server:
            await self.telnet_server.stop()
        saved = StatePersistence.save_to_file(self.kernel, self.save_file)
        if saved:
            print(c_green(f"✔ Universe state saved to {self.save_file}."))
        print(c_gold("Bridge daemon safely terminated."))

    def trigger_shutdown(self) -> None:
        self._shutdown_event.set()


def run_daemon(
    host: Optional[str] = None,
    ws_port: Optional[int] = None,
    telnet_port: Optional[int] = None,
    save_file: Optional[str] = None,
    seed: int = 42,
    enable_telnet: bool = False,
    enable_ws: bool = True,
):
    if host is None or ws_port is None:
        parser = argparse.ArgumentParser(description="Xylarium Runtime Engine & Bridge Daemon")
        parser.add_argument("--host", type=str, default="0.0.0.0", help="Binding host address (default: 0.0.0.0)")
        parser.add_argument("--ws-port", type=int, default=8765, help="WebSocket port (default: 8765)")
        parser.add_argument("--telnet-port", type=int, default=2002, help="Telnet port if enabled (default: 2002)")
        parser.add_argument("--enable-telnet", action="store_true", default=False, help="Enable legacy Telnet BBS door (default: disabled)")
        parser.add_argument("--no-ws", action="store_true", default=False, help="Disable WebSocket API gateway")
        parser.add_argument("--seed", type=int, default=42, help="Universe seed (default: 42)")
        parser.add_argument("--save", type=str, default="xylarium_save.json", help="Save file path")

        args = parser.parse_args()
        host = args.host
        ws_port = args.ws_port
        telnet_port = args.telnet_port
        save_file = args.save
        seed = args.seed
        enable_telnet = args.enable_telnet
        enable_ws = not args.no_ws
    else:
        if save_file is None:
            save_file = "xylarium_save.json"

    kernel = None
    if os.path.exists(save_file):
        print(f"Loading universe from {save_file}...")
        kernel = StatePersistence.load_from_file(save_file)

    if not kernel:
        print(f"Bootstrapping new universe (Seed: {seed})...")
        kernel = GameKernel(seed=seed)

    serve(kernel)
    daemon = BridgeDaemon(
        kernel=kernel,
        host=host,
        ws_port=ws_port,
        telnet_port=telnet_port,
        save_file=save_file,
        enable_telnet=enable_telnet,
        enable_ws=enable_ws
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, daemon.trigger_shutdown)
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(daemon.start())
    except KeyboardInterrupt:
        loop.run_until_complete(daemon.stop())


if __name__ == "__main__":
    run_daemon()
