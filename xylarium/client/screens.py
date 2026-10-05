"""
Xylarium client screens for the newer systems: the advisor, realms and government, the ship workbench, drives
and fuel cells, commercial stations, and VIP charters.

Each screen is a pure `render_*` function (kernel state -> text, easy to test) and a `prompt_*` loop that reads
the player's input and dispatches commands through the kernel, exactly as the AI does. The terminal client maps
command words to these screens through SCREENS.
"""

from typing import Any, Callable, Dict, List, Optional

from xylarium.client.ansi import bold, c_cyan, c_gold, c_gray, c_green, c_magenta, c_red, c_white
from xylarium.kernel.models import ActionType


def _ask(prompt: str) -> Optional[str]:
    try:
        return input(c_gold(prompt)).strip()
    except (KeyboardInterrupt, EOFError):
        return None


def _rule(title: str) -> str:
    return "\n" + bold(c_cyan(f"== {title} " + "=" * max(0, 70 - len(title))))


# ---------------------------------------------------------------------- the advisor
def render_advisor(adv: Dict[str, Any]) -> str:
    labels = {"alerts": "ALERTS", "here": "HERE AND NOW", "ship": "YOUR SHIP", "worlds": "YOUR WORLDS",
              "polity": "WHO GOVERNS HERE", "ventures": "VENTURES"}
    lines = [_rule(f"ADVISOR - Sector {adv.get('sector', '?')}")]
    n = 0
    for key, label in labels.items():
        ops = adv["sections"].get(key) or []
        if not ops:
            continue
        lines.append(bold(c_white(f"  {label}")))
        for o in ops:
            n += 1
            value = c_green(f" ~{o['value_sol']:,} SOL") if o["value_sol"] else ""
            head = c_red(o["title"]) if o["urgent"] else c_white(o["title"])
            lines.append(f"  {c_gold(f'{n:>2}.')} {head}{value}")
            lines.append(f"      {c_gray(o['detail'])}")
            lines.append(f"      {c_cyan('> ' + o['command'])}")
    if n == 0:
        lines.append(c_gray("  Nothing presses here. Try another system, or open the Library for ideas."))
    return "\n".join(lines)


def _numbered(adv: Dict[str, Any]) -> List[Dict[str, Any]]:
    order = ["alerts", "here", "ship", "worlds", "polity", "ventures"]
    return [o for k in order for o in (adv["sections"].get(k) or [])]


def _execute(cli: Any, op: Dict[str, Any]) -> None:
    """Take an opportunity: direct commands are dispatched; the rest open the screen that handles them."""
    words = op["command"].split()
    head = words[0].upper() if words else ""
    kernel, pid = cli.kernel, cli.player_id
    if head == "TRADE" and len(words) >= 4 and words[1] == "BUY":
        cli._print_result(kernel.dispatch(pid, ActionType.TRADE, type="BUY", commodity=words[2], amount=int(words[3])))
    elif head == "FREIGHT_ACCEPT" and len(words) >= 2:
        cli._print_result(kernel.dispatch(pid, ActionType.FREIGHT_ACCEPT, contract_id=words[1]))
    elif head == "CHARTER":
        cli._print_result(kernel.dispatch(pid, ActionType.CHARTER_ACCEPT))
    elif head == "DRIVE" and len(words) >= 2 and not words[1].startswith("("):
        cli._print_result(kernel.dispatch(pid, ActionType.DRIVE_REFIT, drive=words[1]))
    elif head in SCREENS:
        SCREENS[head](cli)
    else:
        print(c_gray(f"  Open it from the command line: {op['command']}"))


def prompt_advisor(cli: Any) -> None:
    from xylarium.kernel import advisor
    while True:
        adv = advisor.advise(cli.kernel, cli.player_id)
        print(render_advisor(adv))
        raw = _ask("Take opportunity # (Enter to exit) > ")
        if not raw or not raw.isdigit():
            return
        ops = _numbered(adv)
        i = int(raw) - 1
        if 0 <= i < len(ops):
            _execute(cli, ops[i])


# ---------------------------------------------------------------------- realms and government
def render_realms(kernel: Any, captain: Any) -> str:
    from xylarium.kernel import government, realms
    sector = kernel.sectors[captain.sector_id]
    kind, gov = government.government_of(kernel, sector)
    realm = realms.realm_of_sector(kernel, sector.id)
    here = (gov.name if kind == "faction" else realm["name"] if realm else f"the people of {gov.name}"
            ) if kind != "syndicate" else "no government (a syndicate free port)"
    lines = [_rule("REALMS & GOVERNMENT"), f"  This system is governed by {bold(c_white(here))}."]
    port = sector.port
    if port is not None:
        lines.append(c_gray(f"  Its starport {port.name} is bound to {port.leisure.get('host_type', '?')} world "
                            f"{port.leisure.get('host', '?')} and run by {port.leisure.get('owner', '?')}."))
    lines.append(bold(c_white("\n  BUDGET OFFICES")))
    offices = government.offices(kernel)
    for fid, o in offices.items():
        f = kernel.factions.factions.get(fid)
        if f is None:
            continue
        vault = sum(kernel.fx_market.to_sol_value(c, a) for c, a in f.vault.items())
        holder = kernel.captains.get(o.get("holder")) if o.get("holder") else None
        who = holder.name if holder else "its steward (automated)"
        shares = government.shares_for(kernel, fid)
        split = " ".join(f"{k[:5]} {v:.0%}" for k, v in shares.items())
        mine = c_green("  <- YOU") if holder is not None and holder.id == captain.id else ""
        lines.append(f"  {fid:<11} treasury {vault:>11,.0f} SOL  held by {who}{mine}")
        lines.append(c_gray(f"              {'hand-set' if not o.get('auto', True) else 'by alignment'}: {split}"))
    lines.append(c_gray("  The Federation's office goes to the Senate's Master of Coin (SENATE); the Compact's to its top"
                        " lobbyist (LOBBY_CONTRIBUTE)."))
    rs = sorted(realms.realms(kernel).values(), key=lambda r: -len(r["systems"]))
    lines.append(bold(c_white(f"\n  REALMS ({len(rs)}, claiming {len(realms.claims(kernel))} systems)")))
    for r in rs[:10]:
        people = sum((kernel.get_planet(p).population if kernel.get_planet(p) else 0) for p in r["worlds"])
        seat = kernel.get_planet(r["capital"])
        mark = c_green(" (here)") if realm is not None and realm["id"] == r["id"] else ""
        lines.append(f"  {r['name'][:34]:<34} {len(r['systems']):>3} systems {len(r['worlds']):>3} worlds "
                     f"{people:>10,} people  seat {seat.name if seat else '?'}{mark}")
    return "\n".join(lines)


def prompt_realms(cli: Any) -> None:
    from xylarium.kernel import government
    kernel, pid = cli.kernel, cli.player_id
    while True:
        print(render_realms(kernel, kernel.captains[pid]))
        print(c_gray("  [B]udget (set shares) | [A]uto (hand back to the steward) | [G]rant to a world | Enter to exit"))
        cmd = (_ask("Realms > ") or "").upper()
        if not cmd:
            return
        if cmd in ("B", "A", "G"):
            fid = (_ask(f"Office ({', '.join(government.BUDGETED)}) > ") or "").upper()
            if cmd == "A":
                cli._print_result(kernel.dispatch(pid, ActionType.BUDGET_SET, government=fid, auto=True))
            elif cmd == "B":
                raw = _ask("Shares for grants endowment security infrastructure (e.g. 40 10 30 20) > ") or ""
                parts = raw.split()
                if len(parts) == 4 and all(p.replace(".", "", 1).isdigit() for p in parts):
                    kw = dict(zip(government.CATEGORIES, (float(p) for p in parts)))
                    cli._print_result(kernel.dispatch(pid, ActionType.BUDGET_SET, government=fid, **kw))
            else:
                world = _ask("World id or name > ") or ""
                amount = _ask("Amount (SOL) > ") or "0"
                planet = kernel.get_planet(world)
                if planet is not None and amount.isdigit():
                    cli._print_result(kernel.dispatch(pid, ActionType.GOVERNMENT_GRANT, government=fid,
                                                      planet_id=planet.id, amount=int(amount)))


# ---------------------------------------------------------------------- the workbench
def render_workbench(kernel: Any, captain: Any, spec: Optional[Dict[str, Any]] = None) -> str:
    from xylarium.config import SHIP_FRAMES, SHIP_MODULES
    from xylarium.kernel import shipdesign
    lines = [_rule("SHIP WORKBENCH")]
    lines.append(bold(c_white("  FRAMES")) + c_gray("  (volume budget, structural mass, price, rank)"))
    for name, f in SHIP_FRAMES.items():
        ok = c_green("*") if getattr(captain, "rank_tier", 1) >= f["min_tier"] else " "
        lines.append(f"  {ok} {name:<10} vol {f['volume']:>4}  mass {f['mass']:>4}  {f['price']:>7,} Cr  tier {f['min_tier']}")
    lines.append(bold(c_white("  MODULES")) + c_gray("  (per unit: volume, mass, power +gen/-draw, price, gives)"))
    for name, m in SHIP_MODULES.items():
        gives = ", ".join(f"{k} {v}" for k, v in m["gives"].items())
        who = f" for {'/'.join(m['for'])}" if m.get("for") else ""
        lines.append(f"    {name:<14} vol {m['volume']:>2} mass {m['mass']:>4} pow {m['power']:>5} {m['price']:>5} Cr  {gives}{who}")
    if spec is not None:
        lines.append(render_spec(spec))
    mine = [d for d in shipdesign.designs(kernel).values() if d["designer"] == captain.id]
    if mine:
        lines.append(bold(c_white("\n  YOUR DESIGNS")))
        for d in mine:
            lines.append(f"    {d['name']:<28} {d['frame']:<9} {d['drive']:<5} holds {d['holds']:>4} berths {d['berths']:>3} "
                         f"built {d.get('built', 0)}  royalty {d['royalty']:.0%}")
    return "\n".join(lines)


def render_spec(spec: Dict[str, Any]) -> str:
    lines = [bold(c_white("\n  DRAFT")) + c_gray(f"  {spec['frame']} on a {spec['drive']} cell: " +
                                                  ", ".join(f"{k} x{v}" for k, v in spec["modules"].items()))]
    lines.append(f"    holds {spec['holds']}  tank {spec['tank']}  shields {spec['max_shields']}  fighters "
                 f"{spec['max_fighters']}  berths {spec['berths']}  mining +{spec['mining']}")
    lines.append(f"    mass {spec['mass']}  power {spec['power']:+}  volume {spec['volume']:g}  "
                 f"{'sluggish (2 turns a jump)' if spec['move_turns'] > 1 else 'full pace'}  price {spec['price']:,} Cr")
    if spec.get("comfort"):
        lines.append(f"    comfort by guest biology: " + ", ".join(f"{m} {v:.0%}" for m, v in spec["comfort"].items()))
    for f in spec.get("faults", []):
        lines.append(c_red(f"    ! {f}"))
    return "\n".join(lines)


def _parse_modules(raw: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for part in raw.replace(",", " ").split():
        if "=" in part:
            k, _, v = part.partition("=")
            if v.isdigit():
                out[k.strip().lower()] = int(v)
    return out


def prompt_workbench(cli: Any) -> None:
    from xylarium.kernel import propulsion, shipdesign
    kernel, pid = cli.kernel, cli.player_id
    spec = None
    while True:
        captain = kernel.captains[pid]
        print(render_workbench(kernel, captain, spec))
        print(c_gray("  [D]raft by role | [C]ustom layout | [R]egister the draft | [B]uild a design at this yard | Enter"))
        cmd = (_ask("Workbench > ") or "").upper()
        if not cmd:
            return
        if cmd == "D":
            role = (_ask("Role (hauler, miner, liner, warship) > ") or "hauler").lower()
            frame = (_ask("Frame (corvette, frigate, cruiser, capital, leviathan) > ") or "frigate").lower()
            guests = (_ask("Guests' biology for decks (biotic, cryogenic, plasmic, mineral, umbral; Enter = yours) > ")
                      or getattr(captain, "metabolism", "biotic"))
            drive = propulsion.choose_fuel(kernel, captain.sector_id, getattr(captain, "metabolism", "biotic"),
                                           getattr(captain, "rank_tier", 1), captain.cosmic_alignment)
            if role not in shipdesign.ROLES or frame not in __import__("xylarium.config", fromlist=["SHIP_FRAMES"]).SHIP_FRAMES:
                print(c_red("  Unknown role or frame."))
                continue
            spec = shipdesign.evaluate(frame, shipdesign.draft(frame, role, guests, drive), drive)
        elif cmd == "C":
            frame = (_ask("Frame > ") or "").lower()
            mods = _parse_modules(_ask("Modules as name=count (e.g. drive=2 reactor=1 tank=8 hold=90) > ") or "")
            drive = _ask("Fuel cell (H, C, H2O, He-3, Xe, U, WARP) > ") or "H"
            spec = shipdesign.evaluate(frame, mods, drive)
        elif cmd == "R":
            if spec is None or spec.get("faults"):
                print(c_red("  Draft a sound design first."))
                continue
            name = _ask("Name the design > ") or ""
            royalty = _ask("Royalty others pay you (0-20%, Enter = 5) > ") or "5"
            cli._print_result(kernel.dispatch(pid, ActionType.SHIP_DESIGN, name=name, frame=spec["frame"],
                                              modules=spec["modules"], drive=spec["drive"],
                                              royalty=float(royalty) / 100.0 if royalty.replace(".", "", 1).isdigit() else 0.05))
        elif cmd == "B":
            name = _ask("Design to build > ") or ""
            cli._print_result(kernel.dispatch(pid, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name=name))


# ---------------------------------------------------------------------- drives
def render_drives(kernel: Any, captain: Any) -> str:
    from xylarium.config import FUEL_CELLS, FUEL_TRADITION
    from xylarium.kernel import propulsion
    sector = kernel.sectors[captain.sector_id]
    share = propulsion._abundance(kernel, sector.id)
    now = propulsion.drive_key(captain.ship)
    want = propulsion.choose_fuel(kernel, sector.id, getattr(captain, "metabolism", "biotic") or "biotic",
                                  getattr(captain, "rank_tier", 1), captain.cosmic_alignment,
                                  float((getattr(captain, "traits", None) or {}).get("fuel_lessons", 0.0)))
    tradition = FUEL_TRADITION.get(getattr(captain, "metabolism", "biotic"), "H")
    lines = [_rule("DRIVES & FUEL CELLS")]
    fuel = propulsion.fuel_of(captain.ship)
    lines.append(f"  Your {captain.ship.ship_type} flies a {bold(FUEL_CELLS.get(now, FUEL_CELLS['H'])['name'])}: "
                 f"bunker {captain.ship.fuel}/{propulsion.bunker_capacity(captain.ship)} {fuel or ''}, "
                 f"a jump burns {propulsion.burn_for(captain.ship) if fuel else 0}.")
    lines.append(c_gray("  cell   v_e   tier  part                 abundant here  "))
    for f, cell in FUEL_CELLS.items():
        marks = []
        if f == now:
            marks.append(c_cyan("flying"))
        if f == want:
            marks.append(c_green("your reckoning prefers"))
        if f == tradition:
            marks.append(c_magenta("your people's tradition"))
        ab = f"{share.get(f, 0.0):>6.1%}" if f != "WARP" else "     -"
        lines.append(f"  {f:<6} {str(cell.get('v_e') or '-'):>5}  {cell['min_tier']:>4}  {str(cell.get('part') or '-'):<20} "
                     f"{ab}  {' '.join(marks)}")
    lines.append(c_gray("  Reaction mass per jump falls as 1/v_e. What is abundant nearby is cheap to bunker; a cell the"
                        " galaxy lacks leaves you coasting."))
    return "\n".join(lines)


def prompt_drives(cli: Any) -> None:
    kernel, pid = cli.kernel, cli.player_id
    print(render_drives(kernel, kernel.captains[pid]))
    raw = _ask("Refit to cell (Enter to exit) > ")
    if raw:
        cli._print_result(kernel.dispatch(pid, ActionType.DRIVE_REFIT, drive=raw))


# ---------------------------------------------------------------------- stations and charters
def render_stations(kernel: Any, captain: Any) -> str:
    from xylarium.kernel import tourism
    sector = kernel.sectors[captain.sector_id]
    lines = [_rule(f"ORBITAL STATIONS - Sector {sector.id}")]
    for p in sector.planets:
        st = tourism.station(p)
        if st is not None:
            owner = kernel.captains.get(st["owner"])
            lines.append(f"  {p.name:<24} station of {owner.name if owner else '?'}: {st['berths']:,} berths, "
                         f"{st.get('receipts', 0):,} {p.currency} taken so far")
        elif p.population > 0:
            lines.append(f"  {p.name:<24} no station - {p.society.get('turned_away', 0):,} travellers turned away "
                         f"last season; build ~{tourism.station_cost(p):,} {p.currency}")
    lines.append(c_gray("  A station is private: its owner keeps the takings, less the system government's commercial tax."))
    open_here = [c for c in tourism.charters(kernel).values()
                 if c["status"] == "OPEN" and c["origin_sector"] == sector.id]
    if open_here:
        lines.append(bold(c_white(f"\n  VIP CHARTERS POSTED HERE (your berths: {tourism.berths(captain.ship)})")))
        for c in open_here:
            lines.append(f"  {c['id']}: {c['party']} {c.get('guests', '')} guests to {c['dest_name']} "
                         f"(Sector {c['dest_sector']}) for up to {c['escrow']:,} {c['currency']}")
    return "\n".join(lines)


def prompt_stations(cli: Any) -> None:
    kernel, pid = cli.kernel, cli.player_id
    captain = kernel.captains[pid]
    print(render_stations(kernel, captain))
    raw = (_ask("[B]uild a station over a world | [C]harter: sign on | Enter > ") or "").upper()
    if raw == "B":
        world = _ask("World name > ") or ""
        planet = next((p for p in kernel.sectors[captain.sector_id].planets if p.name.lower() == world.lower()), None)
        if planet is not None:
            cli._print_result(kernel.dispatch(pid, ActionType.STATION_BUILD, planet_id=planet.id))
    elif raw == "C":
        cli._print_result(kernel.dispatch(pid, ActionType.CHARTER_ACCEPT))


def render_peoples(kernel: Any, captain: Any) -> str:
    """The known peoples by what they eat: how many, how far they reach, whether they feed themselves."""
    from xylarium.kernel import staples, sustenance
    lines = [_rule("THE PEOPLES OF THE KNOWN SECTORS - by what they eat")]
    lines.append(c_cyan("  METABOLISM   STAPLE      PEOPLES  OFF-WORLD   PEOPLE      WORLDS SECTORS  FEEDS ITSELF  STATES"))
    for metab, m in sorted(sustenance.census(kernel).items(), key=lambda kv: -kv[1]["people"]):
        states = ", ".join(f"{k} {v}" for k, v in sorted(m["states"].items(), key=lambda kv: -kv[1]))
        tone = c_green if m["self_sufficiency"] >= 1.0 else (c_gold if m["self_sufficiency"] >= 0.7 else c_red)
        lines.append(f"  {metab:<12} {m['staple']:<10} {m['peoples']:>7} {m['off_world']:>9} {m['people']:>10,} "
                     f"{m['worlds']:>7} {m['sectors']:>7}  {tone(format(m['self_sufficiency'], '.0%')):>12}  {states}")
    st = sustenance.stats(kernel)
    lines.append(c_gray(f"  Food wars: {len(st['wars'])} active, {st['wars_begun']} begun, {st['wars_ended']} ended; "
                        f"{st['raids']} raids ({st['repulsed']} repulsed); relief sent {st['relief']} times "
                        f"({st['relief_units']:,} units); {st['exodus']} exodus fleets."))
    for war in list(st["wars"].values())[:6]:
        lines.append(c_red(f"    {sustenance.people_name(kernel, war['a'])} -> {sustenance.people_name(kernel, war['b'])}"
                           f" over {war['staple']}: {war['raids']} raids, {war['seized']:,} seized"))
    mine = kernel.get_planets_owned_by(captain.id)
    if mine:
        lines.append(bold(c_white("\n  YOUR WORLDS")))
        for p in mine:
            soc = p.society
            lines.append(f"  {p.name:<24} eats {staples.of(kernel, p):<9} stores {staples.stores(kernel, p):>7,}  "
                         f"self-sufficiency {soc.get('self_sufficiency', 1.0):>5.0%}  "
                         f"{(soc.get('sustenance') or 'secure').upper()}")
    lines.append(c_gray("  A people that cannot feed itself expands if it can sail and find open worlds, or takes food "
                        "from others if it cannot. Grain is no relief to a people that drinks ice."))
    return "\n".join(lines)


def prompt_peoples(cli: Any) -> None:
    print(render_peoples(cli.kernel, cli.kernel.captains[cli.player_id]))
    _ask("Enter to return > ")


def prompt_progress(cli: Any) -> None:
    from xylarium.kernel import roles
    print(roles.render_progress(roles.progress(cli.kernel, cli.player_id)))
    _ask("Enter to return > ")


def prompt_publish(cli: Any) -> None:
    """The press: this universe's annals as books, a volume per people, each one's genre read from its record."""
    import os
    from xylarium.kernel import press
    k = cli.kernel
    out = os.path.join("runs", "annals", f"seed{getattr(k, 'seed', 0)}-year{k.cycle_count // 100}")
    cat = press.publish(press.of_kernel(k), out, f"The Annals, as of year {k.cycle_count // 100:,}")
    print(c_gray(f"  {len(cat)} volumes written to {out}/ (index.md is the catalogue)."))
    for c in cat[:10]:
        print(f"  {c['genre']:<16} {c['volume']:<28} {c['events']:>5} events")
    _ask("Enter to return > ")


def prompt_realm(cli: Any) -> None:
    """The ruler's dashboard: every world it governs, how near each is to rising, and how it is governed."""
    from xylarium.kernel import roles
    kernel, pid = cli.kernel, cli.player_id
    while True:
        r = roles.realm(kernel, pid)
        if r is None:
            print(c_gray("You rule no realm. (The Steward's seat is taken at a new game.)"))
            return
        print(roles.render_realm(r))
        print(c_gray("  [R]ule (change how much your few take) | [W]orld (set course to one) | Enter to exit"))
        cmd = (_ask("Realm > ") or "").upper()
        if not cmd:
            return
        if cmd == "R":
            for i, f in enumerate(roles.RULE_FORMS, 1):
                print(f"  [{i}] {f['name']} - {f['blurb']}")
            raw = _ask("Rule > ") or ""
            if raw.isdigit() and 1 <= int(raw) <= len(roles.RULE_FORMS):
                print(roles.set_take(kernel, pid, roles.RULE_FORMS[int(raw) - 1]["key"]))
        elif cmd == "W":
            name = (_ask("World name > ") or "").lower()
            w = next((w for w in r["worlds"] if w["name"].lower().startswith(name)), None) if name else None
            if w is not None:
                path = kernel.find_path(kernel.get_player(pid).sector_id, w["sector"]) or []
                for step in path[1:]:                       # warp there, hop by hop, until a hop is refused
                    res = kernel.dispatch(pid, ActionType.MOVE, destination=step)
                    if not res.success:
                        cli._print_result(res)
                        break
                print(c_gray(f"  You are in sector {kernel.get_player(pid).sector_id}."))


SCREENS: Dict[str, Callable[[Any], None]] = {
    "ADVISOR": prompt_advisor,
    "REALM": prompt_realm,
    "PUBLISH": prompt_publish,
    "PROGRESS": prompt_progress,
    "REALMS": prompt_realms,
    "WORKBENCH": prompt_workbench,
    "DRIVE": prompt_drives,
    "STATION": prompt_stations,
    "CHARTER": prompt_stations,
    "PEOPLES": prompt_peoples,
}


def _markets(cli: Any) -> None:
    from xylarium.client.markets import prompt_markets
    prompt_markets(cli)


for _word in ("MARKETS", "MARKET", "MKT", "$"):
    SCREENS[_word] = _markets
