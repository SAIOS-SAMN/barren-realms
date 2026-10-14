#!/usr/bin/env python3
"""
Main launcher for Xylarium: Classic BBS Door Game & MUD Kernel.
Combines TradeWars 2002, Barren Realms Elite (BRE), and Solar Realms Elite (SRE).
"""

import sys
import os
import argparse

# Ensure module path is accessible
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType
from xylarium.client.cli import TerminalClient
from xylarium.persistence.store import StatePersistence
from xylarium.client.ansi import c_cyan, c_gold, c_gray, c_green, c_red, bold


def main():
    parser = argparse.ArgumentParser(
        description="Xylarium: Classic BBS Space Door Game & MUD Kernel",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-n", "--name", type=str, default="Captain Solo", help="Your Captain name (default: Captain Solo)")
    parser.add_argument("-s", "--seed", type=int, default=42, help="Universe deterministic generation seed (default: 42)")
    parser.add_argument("-l", "--load", type=str, default="xylarium_save.json", help="Save file to load from")
    parser.add_argument("--new", action="store_true", help="Start a new game even if save file exists")
    parser.add_argument("--demo", action="store_true", help="Run a quick automated kernel simulation pass")
    parser.add_argument("--runtime", action="store_true", help="Launch headless runtime engine that loads universe and runs ambient continuous simulation")
    parser.add_argument("--bridge", action="store_true", help="Launch Mycelium Bridge Daemon")
    parser.add_argument("--enable-telnet", action="store_true", default=False, help="Enable legacy Telnet BBS door (default: disabled, no telnet)")
    parser.add_argument("--no-ws", action="store_true", default=False, help="Disable WebSocket API gateway")
    parser.add_argument("--progenitor", action="store_true", help="Take the progenitors' seat: write laws, begin, watch")
    parser.add_argument("--ws-port", type=int, default=8765, help="WebSocket port (default: 8765)")
    parser.add_argument("--telnet-port", type=int, default=2002, help="Telnet port if enabled (default: 2002)")

    args = parser.parse_args()
    if args.progenitor:
        from xylarium.client import progenitor
        progenitor.run(args.seed, save=lambda k: StatePersistence.save_to_file(k, args.load))
        return

    kernel = None
    save_file = args.load

    # Attempt to load save unless --new is specified
    if not args.new and os.path.exists(save_file):
        print(f"Loading game state from {save_file}...")
        kernel = StatePersistence.load_from_file(save_file)
        if kernel:
            print(c_green("Save state loaded successfully."))

    player_id = "player_1"
    headless = args.demo or args.bridge or args.runtime
    single_player = not headless
    if not kernel:
        print(f"Generating new deterministic universe (Seed: {args.seed})...")
        if single_player:
            # The first question of a new universe: which seat to take (kernel/roles.py)
            from xylarium.client import roles as roles_ui
            from xylarium.client import steward as steward_ui
            seat = roles_ui.choose_role()
            if seat == "captain":
                # Lineage Genesis: this save is bound to one lineage for its whole life; it berths at Tradewards
                from xylarium.client.cli import lineage_genesis
                from xylarium.kernel import roles
                kernel, player_id = lineage_genesis(args.seed, args.name)
                roles.seat_captain(kernel, player_id, roles_ui.choose_office())
                roles_ui.announce_tradewards(kernel, player_id)
            elif seat == "sovereign":
                from xylarium.client import ruler as ruler_ui
                kernel, player_id = ruler_ui.begin(args.seed, args.name, player_id)
                if kernel is None:
                    return
            elif seat == "steward":
                from xylarium.client import realm as realm_ui
                kernel = realm_ui.begin(args.seed, args.name, player_id)
                realm_ui.run(kernel, player_id, save=lambda: StatePersistence.save_to_file(kernel, save_file))
                return
            elif seat == "progenitor":
                from xylarium.client import ancient as ancient_ui
                ancient_ui.begin(args.seed, args.name, player_id,
                                 save=lambda k: StatePersistence.save_to_file(k, save_file))
                return
            else:
                key = steward_ui.choose_age(args.seed)
                if key == "classic":
                    from xylarium.client.cli import lineage_genesis
                    kernel, player_id = lineage_genesis(args.seed, args.name)
                else:
                    kernel = _begin_steward(args, key, player_id, save_file)
                    if kernel is None:
                        return
        else:
            kernel = GameKernel(seed=args.seed)
            kernel.register_player(player_id=player_id, player_name=args.name)
    else:
        from xylarium.kernel import ages
        if single_player and ages.stats(kernel)["stewards"].get(player_id) and not kernel.get_player(player_id):
            from xylarium.client import steward as steward_ui
            if steward_ui.run(kernel, player_id, args.name, save=lambda: StatePersistence.save_to_file(
                    kernel, save_file)) is None:
                return
        player = kernel.get_player(player_id)
        if not player:
            human_caps = [c for c in kernel.captains.values() if not c.is_ai]
            if human_caps:
                player_id = human_caps[0].id
                print(f"Resuming campaign as {human_caps[0].name} ({player_id}).")
            else:
                kernel.register_player(player_id=player_id, player_name=args.name)
                print(f"Enrolled new captain {args.name} into the active universe.")

    if single_player and kernel is not None:
        from xylarium.config import LINEAGE_LEGACY_FILE
        from xylarium.kernel import lineage as lineage_mod
        kernel.legacy_file = LINEAGE_LEGACY_FILE
        if kernel.lineage is None and kernel.get_player(player_id) is not None:
            # Saves from before lineages: the captain on file becomes the save's lineage
            kernel.single_lineage = True
            lineage_mod.found(kernel, kernel.get_player(player_id))

    if args.demo:
        print(bold(c_cyan("\n=== RUNNING XYLARIUM DEMO HEADLESS PASS ===")))
        view = kernel.get_player_view(player_id)
        print(f"Player: {view['player']['name']} | Sector: {view['sector']['id']} | Credits: {view['player']['credits']}")
        print(f"Warps available: {[w['sector_id'] for w in view['sector']['warps']]}")
        
        # Warp to adjacent sector
        dest = view['sector']['warps'][0]['sector_id']
        print(f"Navigating to Sector {dest}...")
        res = kernel.dispatch(player_id, ActionType.MOVE, destination=dest)
        print(f"Result: {res.message}")

        view2 = kernel.get_player_view(player_id)
        print(f"New Sector: {view2['sector']['id']} ({view2['sector']['name']}) - Security: {view2['sector']['security']}")
        if view2['sector']['port']:
            print(f"Docked at Port: {view2['sector']['port']['name']}")
            print("Port Catalog:")
            for comm, info in view2['sector']['port']['catalog'].items():
                print(f"  {comm}: Buys={info['port_buys']} @ {info['buy_price']} Cr | Sells={info['port_sells']} @ {info['sell_price']} Cr | Stock={info['stock']}")
        print(f"Simulation cycle advanced to: {kernel.cycle_count}")
        print(f"Recent radio broadcasts:")
        for r in kernel.event_bus.get_recent_radio(4):
            print(f"  [{r.sender}]: {r.text}")
        print(c_green("Demo pass complete! Kernel is verified and fully operational."))
        return

    if args.runtime or args.bridge:
        import asyncio
        from bridge.daemon import BridgeDaemon
        daemon = BridgeDaemon(
            kernel=kernel,
            host="0.0.0.0",
            ws_port=args.ws_port,
            telnet_port=args.telnet_port,
            save_file=save_file,
            enable_telnet=args.enable_telnet,
            enable_ws=not args.no_ws
        )
        try:
            asyncio.run(daemon.start())
        except KeyboardInterrupt:
            asyncio.run(daemon.stop())
        return

    # Start interactive terminal client
    client = TerminalClient(kernel=kernel, player_id=player_id, player_name=args.name, save_file=save_file)
    client.run()


def _begin_steward(args, key, player_id, save_file):
    """A universe at the start of a pre-spaceflight age, the player the steward of one people. Returns the kernel
    once the steward takes ship (the console opens), or None if they saved and quit."""
    from xylarium.client import steward as steward_ui
    from xylarium.kernel import ages
    age = ages.age(key)
    print(c_gray(f"Running the universe of seed {args.seed} on its clock to the {age['name']}..."))

    def progress(cycle, firsts):
        if cycle % 1000 == 0:
            latest = max(firsts.items(), key=lambda kv: kv[1]["cycle"])[0].replace("_", " ") if firsts else "-"
            print(c_gray(f"  year {cycle // 100}: {len(firsts)} firsts so far (latest: {latest})"), flush=True)
    pace = steward_ui.choose_pace()
    kernel = ages.begin(args.seed, key, progress, pace=pace)
    print(c_green(f"  You step in at year {kernel.cycle_count // 100}."))
    planet = steward_ui.choose_people(kernel)
    ages.bind(kernel, player_id, args.name, planet)
    if kernel.cycle_count == 0:
        steward_ui.progenitor(kernel, player_id)
    save = lambda: StatePersistence.save_to_file(kernel, save_file)
    cap = steward_ui.run(kernel, player_id, args.name, save=save)
    return kernel if cap is not None else None


if __name__ == "__main__":
    main()
