"""
ASCII / ANSI rendering engine for Xylarium terminal client.
Displays persistent HUD, Sector scans, Port trading tables, and Colony operations.
"""

from typing import Dict, Any, List
from xylarium.client.ansi import (
    c_cyan, c_gold, c_green, c_red, c_magenta, c_white, c_gray, c_blue, bold,
    BRIGHT_WHITE, BRIGHT_CYAN, BRIGHT_YELLOW, BRIGHT_GREEN, BRIGHT_RED,
    BRIGHT_MAGENTA, BRIGHT_BLACK, RESET, BOLD
)
from xylarium.config import CITADEL_CONFIG, SHIP_CATALOG


def _render_bar(curr: int, maximum: int, length: int = 10, fill_char: str = "█", empty_char: str = "░") -> str:
    """Renders a simple ASCII progress bar."""
    if maximum <= 0:
        return empty_char * length
    pct = max(0.0, min(1.0, curr / maximum))
    fill_len = int(round(pct * length))
    return f"[{fill_char * fill_len}{empty_char * (length - fill_len)}]"


class TerminalRenderer:
    """Formats game state data into high-contrast BBS terminal layouts."""

    @classmethod
    def render_hud(cls, view: Dict[str, Any]) -> str:
        """Renders the top persistent status HUD."""
        player = view.get("player", {})
        sector = view.get("sector", {})
        ship = player.get("ship", {})
        cargo = ship.get("cargo", {})

        s_id = sector.get("id", 1)
        sec_level = sector.get("security", "FEDERATION")

        # Security badge color
        if sec_level == "FEDERATION":
            sec_badge = c_green("● FEDERATION CORE")
        elif sec_level == "BORDERLAND":
            sec_badge = c_gold("▲ THE BORDERLANDS")
        else:
            sec_badge = c_red("☠ DEEP VOID (ANARCHY)")

        # Turns and credits
        turns = player.get("turns_left", 0)
        credits = player.get("credits", 0)
        ship_type = ship.get("ship_type", "Scout")
        score = player.get("score", 0)

        # Shields and cargo
        shields = ship.get("shields", 0)
        max_shields = ship.get("max_shields", 100)
        shield_bar = _render_bar(shields, max_shields, length=8)
        shield_str = c_cyan(f"{shield_bar} {shields}/{max_shields}")

        fighters = ship.get("fighters", 0)
        fighter_str = c_red(f"{fighters}")

        used_holds = cargo.get("used", 0)
        cap_holds = cargo.get("capacity", 30)
        ore = cargo.get("ore", 0)
        org = cargo.get("organics", 0)
        eq = cargo.get("equipment", 0)

        line_sep = c_blue("═" * 78)

        hud = [
            f"╔{line_sep}╗",
            (
                f"║ {c_cyan('XYLARIUM BBS')} │ Sector: {c_gold(f'{s_id:03d}')} [{sec_badge}] "
                f"│ Cycle: {c_white(str(view.get('cycle', 0)))} "
                f"│ Turns: {c_gold(str(turns))} ║"
            ),
            f"╠{line_sep}╣",
            (
                f"║ Credits: {c_gold(f'{credits:,} Cr')} │ Ship: {c_white(ship_type)} "
                f"│ Shields: {shield_str} │ Fighters: {fighter_str} ║"
            ),
            (
                f"║ Holds: {c_cyan(f'[{used_holds}/{cap_holds}]')} "
                f"({c_gold(f'Ore:{ore}')}, {c_green(f'Org:{org}')}, {c_magenta(f'Eq:{eq}')}) "
                f"│ Score: {c_white(f'{score:,}')} "
                f"│ Free Holds: {c_white(str(cargo.get('available', 0)))} ║"
            ),
            f"╚{line_sep}╝"
        ]
        return "\n".join(hud)

    @classmethod
    def render_sector(cls, view: Dict[str, Any]) -> str:
        """Renders the current sector view, ports, planets, warps, and other captains."""
        sector = view.get("sector", {})
        s_id = sector.get("id", 1)
        name = sector.get("name", "Unknown Sector")
        port = sector.get("port")
        planets = sector.get("planets", [])
        captains = sector.get("captains", [])
        warps = sector.get("warps", [])
        logs = view.get("logs", [])
        radio = view.get("radio", [])

        out = []

        # Sector Title
        out.append(f"\n{c_cyan('SECTOR')} {c_gold(f'#{s_id:03d}')}: {bold(c_white(name))}")

        # Warp Lanes
        warp_strs = []
        for w in warps:
            w_id = w["sector_id"]
            flags = []
            if w["security"] == "FEDERATION":
                flags.append("Fed")
            elif w["security"] == "ANARCHY":
                flags.append("Anarchy")
            if w["has_port"]:
                flags.append("Port")
            if w["has_planet"]:
                flags.append("Planet")
            flag_str = f" ({', '.join(flags)})" if flags else ""
            warp_strs.append(f"{c_gold(f'({w_id:03d})')}{c_gray(flag_str)}")
        out.append(f"  {bold('Wormhole Warps:')} " + "  ".join(warp_strs))

        # Port Summary
        if port:
            p_name = port["name"]
            p_class = port["port_class"]
            out.append(f"\n  {c_cyan('► TRADE PORT:')} {c_white(p_name)} [Class {p_class}]")
            cat = port.get("catalog", {})
            port_items = []
            for comm, info in cat.items():
                if info["port_buys"]:
                    port_items.append(f"{info['name']}: {c_green('BUYS')} @ {info['buy_price']} Cr (Stock: {info['stock']})")
                elif info["port_sells"]:
                    port_items.append(f"{info['name']}: {c_gold('SELLS')} @ {info['sell_price']} Cr (Stock: {info['stock']})")
            out.append("    " + " | ".join(port_items))
        else:
            out.append(f"\n  {c_gray('► No trade port in this sector.')}")

        # Planetary Bodies
        if planets:
            for p in planets:
                p_name = p["name"]
                owner = p.get("owner_id")
                if not owner:
                    status = c_green("[UNCLAIMED - Available for Colonization]")
                elif owner == view["player"]["id"]:
                    status = c_cyan(f"[YOUR COLONY - Level {p['citadel_level']} Citadel]")
                else:
                    status = c_red(f"[RIVAL COLONY - Governor: {owner}]")

                citadel_name = CITADEL_CONFIG.get(p.get("citadel_level", 0), {}).get("name", "Outpost")
                p_pop = p.get("population", 0)
                p_treasury = p.get("treasury", 0)
                out.append(
                    f"  {c_gold('► PLANET:')} {bold(c_white(p_name))} {status}\n"
                    f"    Citadel: {c_white(citadel_name)} │ Pop: {c_gold(f'{p_pop:,}')} │ "
                    f"Shields: {c_cyan(str(p.get('shields', 0)))}/{p.get('max_shields', 200)} │ "
                    f"Garrison: {c_red(str(p.get('fighters', 0)))} Fighters │ "
                    f"Vault: {c_gold(f'{p_treasury:,} Cr')}"
                )
        else:
            out.append(f"  {c_gray('► No planetary bodies in orbital scan.')}")

        # Other Captains Present
        if captains:
            out.append(f"\n  {c_red('► SHIPS DETECTED IN SECTOR:')}")
            for c in captains:
                badge = c_red("[PIRATE]") if c["personality"] == "pirate" else c_gold(f"[{c['personality'].upper()}]")
                out.append(
                    f"    {badge} {bold(c_white(c['name']))} piloting a {c['ship_type']} "
                    f"(Shields: {c_cyan(str(c['shields']))}, Fighters: {c_red(str(c['fighters']))})"
                )

        # Recent Subspace Radio Feed
        if radio:
            out.append(f"\n{c_blue('──[ Subspace Radio Feed ]' + '─' * 55)}")
            for r in radio[-3:]:
                sender = c_gold(f"[{r['sender']}]")
                txt = c_gray(r['text'])
                out.append(f"  {sender}: {txt}")

        # Recent Action Logs
        if logs:
            out.append(f"{c_blue('──[ Tactical Logs ]' + '─' * 62)}")
            for l in logs[-2:]:
                out.append(f"  {c_cyan('»')} {l}")

        return "\n".join(out)

    @classmethod
    def render_trade_screen(cls, view: Dict[str, Any]) -> str:
        """Renders the detailed port trading interface."""
        sector = view.get("sector", {})
        port = sector.get("port")
        player = view.get("player", {})
        cargo = player.get("ship", {}).get("cargo", {})

        if not port:
            return c_red("Error: No trade port present in this sector.")

        player_credits = player.get("credits", 0)
        lines = [
            f"\n{bold(c_cyan('═══════════════ [ PORT TRADING TERMINAL ] ═══════════════'))}",
            f"Port: {c_white(port['name'])}  │  Class: {c_gold(port['port_class'])}",
            f"Your Credits: {c_gold(f'{player_credits:,} Cr')}  │  Available Holds: {c_cyan(str(cargo.get('available', 0)))}",
            "-" * 72,
            f"{'Commodity':<14} {'Port Mode':<10} {'Stock':<10} {'Price':<12} {'In Hold':<10}",
            "-" * 72,
        ]

        cat = port.get("catalog", {})
        for comm_id, comm_data in cat.items():
            name = comm_data["name"]
            stock = comm_data["stock"]
            in_hold = cargo.get(comm_id.lower(), 0)

            if comm_data["port_buys"]:
                mode = c_green("BUYS")
                price = c_gold(f"{comm_data['buy_price']} Cr")
            elif comm_data["port_sells"]:
                mode = c_cyan("SELLS")
                price = c_gold(f"{comm_data['sell_price']} Cr")
            else:
                mode = c_gray("NONE")
                price = c_gray("--")

            lines.append(f"{name:<14} {mode:<19} {str(stock):<10} {price:<21} {str(in_hold):<10}")

        lines.append("-" * 72)
        lines.append(
            f"Commands: {c_gold('[B]uy <Comm> <Amount>')}  │  {c_gold('[S]ell <Comm> <Amount>')}  │  {c_gold('[X] Exit Port')}"
        )
        return "\n".join(lines)

    @classmethod
    def render_planet_screen(cls, view: Dict[str, Any], planet: Dict[str, Any]) -> str:
        """Renders the BRE/SRE Planetary Command Center."""
        player = view.get("player", {})
        p_id = planet.get("id")
        p_name = planet.get("name")
        owner = planet.get("owner_id")
        is_owner = (owner == player.get("id"))
        citadel_lvl = planet.get("citadel_level", 0)
        citadel_info = CITADEL_CONFIG.get(citadel_lvl, CITADEL_CONFIG[0])

        p_pop = planet.get("population", 0)
        p_treasury = planet.get("treasury", 0)
        est_yield = int(p_pop * 0.15 * citadel_info["tax_multiplier"])
        lines = [
            f"\n{bold(c_gold('═══════════════ [ PLANETARY COMMAND REDOUBT ] ═══════════════'))}",
            f"Colony: {bold(c_white(p_name))}  │  Sector: {planet.get('sector_id')}",
            f"Sovereignty: {c_cyan('YOU') if is_owner else (c_red(owner) if owner else c_green('UNINHABITED'))}",
            "-" * 72,
            f"Citadel Tier:      {c_white(str(citadel_lvl))} - {bold(citadel_info['name'])}",
            f"Population:        {c_gold(f'{p_pop:,}')} Colonists (Yield: ~{est_yield} Cr/cycle)",
            f"Treasury Vault:    {c_gold(f'{p_treasury:,} Cr')} (Available for collection)",
            f"Planetary Shields: {c_cyan(str(planet.get('shields', 0)))} / {planet.get('max_shields', 200)} MW",
            f"Garrison Fighters: {c_red(str(planet.get('fighters', 0)))} / {citadel_info['max_fighters']} Wings",
            f"Mineral Silo:      {c_gold(str(planet.get('ore_silo', 0)))} Ore",
            f"Biosphere Silo:    {c_green(str(planet.get('organics_silo', 0)))} Organics",
            "-" * 72,
        ]

        if not owner:
            lines.append(f"Options: {c_gold('[C]laim Planet')} (Establish colony)  │  {c_gold('[B]ack to Orbit')}")
        elif is_owner:
            lines.append(
                f"Management:\n"
                f"  {c_gold('[T]ax Collection')}     (Transfer vault credits to ship)\n"
                f"  {c_gold('[I]nvest Population')}   (Spend credits to attract colonists)\n"
                f"  {c_gold('[S]hield Construction')} (Build planetary shields: 10 Cr + Ore)\n"
                f"  {c_gold('[F]ighter Bay')}        (Recruit garrison fighters: 60 Cr/ea)\n"
                f"  {c_gold('[U]pgrade Citadel')}    (Advance Citadel tier for higher caps)\n"
                f"  {c_gold('[D]eposit Cargo')}      (Transfer Ore/Organics from ship to silo)\n"
                f"  {c_gold('[W]ithdraw Cargo')}     (Transfer Ore/Organics from silo to ship)\n"
                f"  {c_gold('[B]ack to Orbit')}"
            )
        else:
            lines.append(
                f"Hostile Colony!\n"
                f"  {c_red('[A]ttack / Invade Planet')} (Begin orbital bombardment)\n"
                f"  {c_gold('[B]ack to Orbit')}"
            )

        return "\n".join(lines)

    @classmethod
    def render_shipyard_screen(cls, view: Dict[str, Any]) -> str:
        """Renders the Federation Stardock Shipyard (Sector 1)."""
        player = view.get("player", {})
        ship = player.get("ship", {})
        cr = player.get("credits", 0)

        lines = [
            f"\n{bold(c_cyan('═══════════════ [ FEDERATION NAVAL SHIPYARD ] ═══════════════'))}",
            f"Location: Sol Federation Central (Sector 1)  │  Your Credits: {c_gold(f'{cr:,} Cr')}",
            f"Current Ship: {c_white(ship.get('ship_type'))} (Shields: {ship.get('shields')}/{ship.get('max_shields')}, Fighters: {ship.get('fighters')})",
            "-" * 72,
            f"Maintenance & Munitions:",
            f"  {c_gold('[1]')} Recharge Energy Shields to 100% (3 Cr per MW needed)",
            f"  {c_gold('[2]')} Commission Combat Fighters (45 Cr per fighter)",
            "-" * 72,
            f"Available Hull Classes:",
        ]

        for idx, (s_name, s_data) in enumerate(SHIP_CATALOG.items(), start=3):
            price_str = f"{s_data['price']:,} Cr" if s_data['price'] > 0 else "Default"
            lines.append(
                f"  {c_gold(f'[{idx}]')} {bold(c_white(s_name)):<26} Price: {c_gold(price_str):<12} "
                f"Holds: {s_data['holds']:<4} Shields: {s_data['max_shields']:<5} Fighters: {s_data['max_fighters']}\n"
                f"      {c_gray(s_data['description'])}"
            )

        lines.append("-" * 72)
        lines.append(f"Select option number or {c_gold('[B]ack to Stardock')}:")
        return "\n".join(lines)

    @classmethod
    def render_nav_computer(cls, start: int, target: int, path: List[int]) -> str:
        """Renders BFS course plotting for the navigation computer."""
        lines = [
            f"\n{bold(c_cyan('═══════════════ [ HYPER-NAV COMPUTER BFS ] ═══════════════'))}",
            f"Current Sector: {start:03d}  │  Destination: {target:03d}",
        ]
        if not path:
            lines.append(c_red("NO VIABLE WARP PATH DETECTED! Sectors are disconnected."))
        else:
            warp_hops = len(path) - 1
            path_str = " -> ".join([c_gold(f"({s:03d})") for s in path])
            lines.append(f"Course plotted: {warp_hops} warp hops required ({warp_hops} turns):")
            lines.append(f"  {path_str}")
        lines.append("-" * 72)
        return "\n".join(lines)

    @classmethod
    def render_help(cls) -> str:
        """Renders classic BBS door game guide and mechanics."""
        return f"""
{bold(c_gold("══════════════════════ [ XYLARIUM BBS COMMAND GUIDE ] ══════════════════════"))}
{c_cyan("OBJECTIVE:")}
  Amass credits, dominate trade routes, colonize rich planets, defend your
  territory from rival AI captains (Traders, Pirates, MegaCorp Oligarchs),
  and build an interstellar empire across 100 sectors!

{c_cyan("COMMAND DISPATCH:")}
  {c_gold("[M]ove")}     - Warp to an adjacent sector via wormholes (Cost: 1 Turn).
  {c_gold("[T]rade")}    - Dock at the local port to buy/sell Ore, Organics, Equipment (1 Turn).
  {c_gold("[P]lanet")}   - Orbit and manage planetary colonies: tax, shields, citadels (1 Turn).
  {c_gold("[A]ttack")}   - Engage rival ships or bombard planetary defense grids (2 Turns).
  {c_gold("[S]hipyard")} - Upgrade hulls, recharge shields, purchase fighters (Sector 1 only).
  {c_gold("[C]omputer")} - Plot warp courses, calculate BFS shortest routes, sector scans.
  {c_gold("[R]adio")}    - Broadcast subspace message across universe comm channels.
  {c_gold("[H]elp")}     - Display this tactical manual.
  {c_gold("[Q]uit")}     - Save game state and exit to BBS door prompt.

{c_cyan("DYNAMIC COMMODITY TRADING (TradeWars 2002 Model):")}
  - Ports buy and sell commodities dynamically based on stock and port class.
  - Buying goods depletes port inventory, driving prices UP.
  - Selling goods floods port inventory, driving prices DOWN.
  - Ports replenish and consume goods each game cycle, creating moving arbitrage waves.

{c_cyan("PLANETARY COLONIZATION (BRE & SRE Model):")}
  - Land on unowned planets to claim them as sovereign territory.
  - Build Planetary Shields and Garrison Fighters to repel orbital bombardments.
  - Upgrade your Citadel Tier (Outpost -> Redoubt -> Stronghold -> Imperial Citadel)
    to multiply colonist tax yields and increase defense caps.

{c_cyan("SECURITY ZONES:")}
  - {c_green("Sectors 001-010 (Federation Core):")} Protected by FedNav. Combat strictly forbidden.
  - {c_gold("Sectors 011-060 (The Borderlands):")} Mixed security. Moderate hazard, steady trade.
  - {c_red("Sectors 061-100 (Deep Void Anarchy):")} Lawless! Pirate havens, high risk and reward!
{"-" * 78}
"""
