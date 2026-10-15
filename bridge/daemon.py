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
        tick_interval: float = TICK_S,
        enable_seated_minds: bool = False,
        observer_mode: bool = False,
        max_cycles: Optional[int] = None,
    ):
        self.kernel = kernel
        self.host = host
        self.ws_port = ws_port
        self.telnet_port = telnet_port
        self.save_file = save_file
        self.enable_telnet = enable_telnet and (telnet_port is not None and telnet_port > 0)
        self.enable_ws = enable_ws and (ws_port is not None and ws_port > 0)
        self.tick_interval = tick_interval
        self.enable_seated_minds = enable_seated_minds
        self.observer_mode = observer_mode
        self.max_cycles = max_cycles
        self.ws_gateway = WebSocketGateway(kernel, host=host, port=ws_port) if self.enable_ws else None
        self.telnet_server = TelnetServer(kernel, host=host, port=telnet_port) if self.enable_telnet else None
        self._shutdown_event = asyncio.Event()

        if self.enable_seated_minds:
            self._initialize_seated_minds()

    def _initialize_seated_minds(self) -> None:
        """Awakens and seats autonomous sovereign minds on primary civilizational worlds."""
        candidates = [
            p for s in self.kernel.sectors.values() for p in s.planets
            if p.population >= 5000
        ]
        candidates.sort(key=lambda p: getattr(p, "population", 0), reverse=True)
        selected = candidates[:4] if candidates else [p for s in self.kernel.sectors.values() for p in s.planets if p.population > 0][:3]

        print(bold(c_gold("\n[INITIALIZING SEATED SOVEREIGN COGNITION IN DAEMON]")))
        for p in selected:
            sc = self.kernel.sovereign_mind_manager.ensure_consciousness(self.kernel, p)
            self.kernel.sovereign_mind_manager.take_seat(self.kernel, None, str(p.id), as_player=False)
            self.kernel.sovereign_mind_manager.toggle_autonomous_play(self.kernel, None, str(p.id), enable=True)
            print(f"  ★ Seated Mind online: {bold(c_cyan(p.name))} ({p.planet_type}, Pop: {p.population:,})")
        print()

    def _report_observer_state(self, cycle: int) -> None:
        """Renders live telemetry of all seated sovereign minds evolving in the universe."""
        minds = self.kernel.sovereign_mind_manager.minds
        seated = {pid: sc for pid, sc in minds.items() if sc.is_seated and sc.autonomous_play}
        if not seated:
            return

        print(bold(c_cyan(f"\n╔══════════════════════════════════════════════════════════════════════════════╗")))
        print(bold(c_cyan(f"║ [OBSERVER] UNIVERSAL TICK CYCLE {cycle:05d} │ ACTIVE SEATED SOVEREIGNS: {len(seated)}   ║")))
        print(bold(c_cyan(f"╠══════════════════════════════════════════════════════════════════════════════╣")))
        for pid, sc in seated.items():
            p = self.kernel.get_planet(pid)
            if not p:
                continue
            t_data = getattr(sc, "last_turn_data", {})
            action = t_data.get("action", sc.last_action_taken)
            detail = t_data.get("detail", "")
            voice = t_data.get("dominant_voice", sc.parliament.dominant_voice.value)
            ideation = t_data.get("ideation", getattr(sc.ideation_space, "last_collapsed_ideation", "NONE"))
            tom = t_data.get("rival_doctrine", getattr(sc.adversarial_tracker, "inferred_doctrine", "UNKNOWN"))
            techs = ", ".join(getattr(p, "technologies", [])) or "None"
            pop = getattr(p, "population", 0)
            treasury = getattr(p, "treasury", 0)
            food = getattr(p, "organics_silo", 0)
            ore = getattr(p, "ore_silo", 0)
            citadel = getattr(p, "citadel_level", 1)
            vessel = "Yes" if "INTERSTELLAR_FLIGHT" in getattr(p, "technologies", []) else "No"

            print(f"║  ► {c_gold(bold(p.name))} ({p.planet_type}, Sec {p.sector_id}) │ {c_cyan('Pop')}: {pop:,} │ {c_cyan('Treasury')}: {treasury:,} Cr │ {c_cyan('Citadel')}: L{citadel}")
            print(f"║      {c_gray('Reserves')}: Food: {food} │ Ore: {ore} │ {c_gray('Interstellar')}: {c_green(vessel)} │ {c_gray('Techs')}: {c_green(techs)}")
            print(f"║      {c_gray('Cognition')}: ToM: {c_gold(tom)} │ Ideation: {c_cyan(ideation)} │ Voice: {voice}")
            print(f"║      {c_gray('Action')}:    {bold(action)} -> {c_gray(detail)}")
            print(c_cyan("╟──────────────────────────────────────────────────────────────────────────────╢"))
        print(bold(c_cyan(f"╚══════════════════════════════════════════════════════════════════════════════╝\n")))

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
        print(f"║  {bold('Continuous Clock')}:  {c_green(f'Active (TICK_S={self.tick_interval:.1f}s, Orbit & Economy Recycling)')}     ║")
        if self.enable_seated_minds:
            print(f"║  {bold('Seated Cognition')}:  {c_gold('ACTIVE (Autonomous Sovereign Minds Governing Worlds)')}     ║")
        if self.observer_mode:
            print(f"║  {bold('Observer Stream')}:   {c_green('ACTIVE (Real-time telemetry logging enabled)')}             ║")
        print(bold(c_cyan("╚══════════════════════════════════════════════════════════════════════════════╝\n")))
        print(c_green("Runtime running. Press Ctrl+C to save state and terminate.\n"))

        # Background world tick task
        tick_task = asyncio.create_task(self._ambient_universe_ticker())

        try:
            await self._shutdown_event.wait()
        finally:
            tick_task.cancel()
            await self.stop()

    async def _ambient_universe_ticker(self) -> None:
        """The universe's one clock: a cycle every tick_interval of wall time."""
        cycles_run = 0
        while not self._shutdown_event.is_set():
            await asyncio.sleep(self.tick_interval)
            self.kernel.tick_simulation()
            cycles_run += 1
            stamp(self.kernel)
            if self.observer_mode:
                self._report_observer_state(self.kernel.cycle_count)
            if self.max_cycles and cycles_run >= self.max_cycles:
                self.trigger_shutdown()
                break

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
    tick_interval: float = TICK_S,
    enable_seated_minds: bool = False,
    observer_mode: bool = False,
    max_cycles: Optional[int] = None,
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
        parser.add_argument("--tick-interval", type=float, default=TICK_S, help=f"Seconds per universe simulation cycle (default: {TICK_S:.1f})")
        parser.add_argument("--seated-minds", action="store_true", default=False, help="Seat autonomous sovereign minds on primary homeworlds")
        parser.add_argument("--observer", action="store_true", default=False, help="Stream real-time observer telemetry of seated minds")
        parser.add_argument("--max-cycles", type=int, default=None, help="Optional max simulation cycles to run")

        args = parser.parse_args()
        host = args.host
        ws_port = args.ws_port
        telnet_port = args.telnet_port
        save_file = args.save
        seed = args.seed
        enable_telnet = args.enable_telnet
        enable_ws = not args.no_ws
        tick_interval = args.tick_interval
        enable_seated_minds = args.seated_minds
        observer_mode = args.observer or args.seated_minds
        max_cycles = args.max_cycles
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
        enable_ws=enable_ws,
        tick_interval=tick_interval,
        enable_seated_minds=enable_seated_minds,
        observer_mode=observer_mode,
        max_cycles=max_cycles,
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
