"""
Xylarium advisor: what a captain can do where it stands, and what is worth doing.

The universe offers many careers (docs/GAME.md) and most of them are invisible from a single sector's scan. The
advisor reads the same world the captain lives in - prices, contracts, charters, governments, the captain's own
worlds - and returns concrete opportunities, each with the command that takes it and its value in SOL where one
can be estimated. Human players see it as the ADVISOR screen; autonomous captains can read the same list.

Nothing here changes the world: it is a read-only lens.
"""

from typing import Any, Dict, List, Optional

from xylarium.config import PROCESSES
from xylarium.kernel import hulls, topology

TRADE_REACH = 3              # jumps within which a sale is worth planning from here
TOP_TRADES = 3


def _sol(kernel: Any, cur: str, amount: float) -> float:
    fxm = getattr(kernel, "fx_market", None)
    return fxm.to_sol_value(cur, amount) if (fxm is not None and cur != "SOL") else float(amount)


def _op(kind: str, title: str, detail: str, command: str, value: float = 0.0, urgent: bool = False) -> Dict[str, Any]:
    return {"kind": kind, "title": title, "detail": detail, "command": command, "value_sol": int(value),
            "urgent": urgent}


# ---------------------------------------------------------------------- where you stand
def spendable(kernel: Any, captain: Any, cur: str) -> float:
    """What a captain can spend at a port of `cur`, in SOL: its SOL (which the desk converts on the spot) and what
    it already holds in the port's own money."""
    from xylarium.kernel import fx
    local = captain.fx_wallet.get(cur, 0) if cur != "SOL" else 0
    m = fx.ACTIVE_FX or getattr(kernel, "fx_market", None)
    return float(captain.credits) + (m.to_sol_value(cur, local) if (m is not None and local) else 0.0)


def idle_money(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    """Money sitting in a region's currency the captain is not working in: worth converting (or holding, if that
    money pays better than SOL - the desk shows both)."""
    from xylarium.kernel import fx
    m = fx.ACTIVE_FX or getattr(kernel, "fx_market", None)
    here = sector.port.currency if sector.port is not None else None
    out = []
    for cur, amt in (captain.fx_wallet or {}).items():
        if cur == here or amt <= 0 or m is None:
            continue
        sol = m.to_sol_value(cur, amt)
        if sol >= 100:
            out.append(_op("money", f"{amt:,} {cur} idle (~{sol:,.0f} SOL)",
                           f"convert at the ISSE desk to spend it here, or hold it if {cur} pays better",
                           "FX", sol * 0.01))
    return out


def trades(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    """The best buy-here, sell-within-reach runs, by margin x what the hold and the warehouse allow."""
    port = sector.port
    if port is None:
        return []
    from xylarium.kernel.economy import EconomyManager
    EconomyManager.ensure_port_inventory(port)
    space = captain.ship.cargo.available_space
    if space <= 0:
        return []
    hops = topology.hops(kernel, sector.id, TRADE_REACH)
    markets = [(sid, d, kernel.sectors[sid].port) for sid, d in hops.items()
               if sid != sector.id and kernel.sectors[sid].port is not None]
    runs = []
    for comm, sells in port.sells.items():
        stock = port.stock.get(comm, 0)
        if not sells or stock <= 0:
            continue
        _, buy_at = EconomyManager.get_unit_prices(port, comm)
        if buy_at <= 0:
            continue
        cost = _sol(kernel, port.currency, buy_at)
        best = None
        for sid, d, other in markets:
            if not other.buys.get(comm):
                continue
            sell_at, _ = EconomyManager.get_unit_prices(other, comm)
            margin = _sol(kernel, other.currency, sell_at) - cost
            if margin > 0 and (best is None or margin / (1 + d) > best[0] / (1 + best[1])):
                best = (margin, d, other)
        if best is None:
            continue
        units = min(space, stock, int(max(0, spendable(kernel, captain, port.currency) - 500) // max(1.0, cost)))
        if units <= 0:
            continue
        margin, d, other = best
        runs.append(_op("trade", f"Buy {comm} here, sell at {other.name} ({d} jump{'s' if d != 1 else ''})",
                        f"{units} units at ~{margin:,.0f} SOL margin each (bought at {buy_at} {port.currency})",
                        f"TRADE BUY {comm} {units}", margin * units / (1 + d)))
    runs.sort(key=lambda o: -o["value_sol"])
    return runs[:TOP_TRADES]


def contracts(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    out = []
    mm = getattr(kernel, "market_manager", None)
    free = captain.ship.cargo.available_space
    for c in (mm.contracts.values() if mm is not None else []):
        if c.status != "OPEN" or c.amount > free:
            continue
        here = c.destination_sector if c.kind == "EXTRACTION" else c.origin_sector
        if here != sector.id:
            continue
        out.append(_op("freight", f"{c.kind.title()} contract {c.id}: {c.amount} {c.commodity} to {c.destination_name}",
                       f"pays {c.payout_credits:,} {c.currency} on delivery (hazard {c.hazard_level})",
                       f"FREIGHT_ACCEPT {c.id}", _sol(kernel, c.currency, c.payout_credits)))
    out.sort(key=lambda o: -o["value_sol"])
    return out[:3]


def charters(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    from xylarium.kernel import shipdesign, tourism
    room = tourism.berths(captain.ship)
    out = []
    for c in tourism.charters(kernel).values():
        if c["status"] != "OPEN" or c["origin_sector"] != sector.id:
            continue
        fit = shipdesign.comfort_fit(captain.ship, c.get("guests", "biotic"))
        pay = c["escrow"] * (0.5 + 0.5 * fit)
        if c["party"] > room:
            out.append(_op("charter", f"VIP charter to {c['dest_name']}: {c['party']} {c.get('guests', '')} guests",
                           f"needs {c['party']} berths - your {captain.ship.ship_type} has {room}. A liner drawn for "
                           f"{c.get('guests', 'these')} guests earns the full {c['escrow']:,} {c['currency']}",
                           "WORKBENCH (draw a liner)", 0.0))
            continue
        out.append(_op("charter", f"VIP charter to {c['dest_name']}: {c['party']} {c.get('guests', '')} guests",
                       f"pays {int(pay):,} {c['currency']} (comfort fit {fit:.0%} - decks for their biology pay more)",
                       f"CHARTER (sign on here, then fly to Sector {c['dest_sector']})", _sol(kernel, c["currency"], pay)))
    return out


def drive(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    """What the fuel cell reckoning prefers here, against what the hull flies."""
    from xylarium.config import FUEL_CELLS
    from xylarium.kernel import propulsion
    now = propulsion.drive_key(captain.ship)
    lessons = float((getattr(captain, "traits", None) or {}).get("fuel_lessons", 0.0))
    want = propulsion.choose_fuel(kernel, sector.id, getattr(captain, "metabolism", "biotic") or "biotic",
                                  getattr(captain, "rank_tier", 1), captain.cosmic_alignment, lessons)
    fuel = propulsion.fuel_of(captain.ship)
    low = fuel is not None and captain.ship.fuel < propulsion.burn_for(captain.ship)
    out = []
    if low:
        stock = sector.port.stock.get(fuel, 0) if sector.port is not None else 0
        out.append(_op("drive", f"Bunker low: {captain.ship.fuel} {fuel} aboard, a jump burns "
                                f"{propulsion.burn_for(captain.ship)}",
                       "empty bunkers coast (two extra turns a jump)" + (f"; this port has {stock} {fuel}" if stock else
                                                                        "; this port has none - find a well"),
                       "dock at a port that stocks your fuel", 0.0, urgent=True))
    if want != now and now != "WARP":
        why = propulsion.can_refit(kernel, captain, sector, want)
        cost = propulsion.refit_cost_sol(kernel, sector, want) if (why is None and sector.port is not None) else 0
        out.append(_op("drive", f"Refit to a {FUEL_CELLS[want]['name']}",
                       (f"{want} is what is abundant in reach (v_e {FUEL_CELLS[want]['v_e']}x a hydrogen torch); "
                        f"refit here for {cost:,} Cr") if why is None else f"{FUEL_CELLS[want]['name']}: {why}",
                       f"DRIVE {want}" if why is None else "DRIVE (see fuel cells)", 0.0))
    return out


def politics(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    from xylarium.kernel import government, realms
    out = []
    kind, gov = government.government_of(kernel, sector)
    realm = realms.realm_of_sector(kernel, sector.id)
    who = (gov.name if kind == "faction" else (realm["name"] if realm else f"the people of {gov.name}")
           if kind == "civ" else "no one (a syndicate free port)")
    out.append(_op("polity", f"This system is governed by {who}",
                   "its starport pays dues to its government; stations here pay commercial tax" if kind != "syndicate"
                   else "the port keeps what it earns; no court reaches here", "REALMS", 0.0))
    for fid, o in government.offices(kernel).items():
        if o.get("holder") == captain.id:
            out.append(_op("polity", f"You hold the {fid} budget office",
                           "set its budget by hand, hand it back to the steward, or direct a grant", "REALMS", 0.0,
                           urgent=True))
    return out


def worlds(kernel: Any, captain: Any) -> List[Dict[str, Any]]:
    """Your worlds' alarms: fuel-starved defences, famine, unmet luxuries, a people at its choice."""
    from xylarium.kernel import demography, fertility
    out = []
    for p in kernel.get_planets_owned_by(captain.id):
        soc = p.society
        if soc.get("degraded"):
            out.append(_op("world", f"{p.name} broadcasts a DEGRADED beacon",
                           f"its defences run on {soc.get('fuel', 'H')} and it has too little in reach "
                           f"(readiness {soc.get('readiness', 0):.0%}): easier to conquer", "PLANET", 0.0, urgent=True))
        if fertility.stressed(kernel, p):
            out.append(_op("world", f"{p.name} is under stress (famine or bombardment)",
                           "its fertility has fallen to a quarter; feed it and shield it", "PLANET", 0.0, urgent=True))
        unmet = [t for t, q in (soc.get("luxury_unmet_quarters") or {}).items() if q >= 3]
        if unmet:
            out.append(_op("world", f"{p.name} has gone without {', '.join(t[4:].lower() for t in unmet)}",
                           "its council is bidding up the price: haul some in", "TRADE", 0.0))
        from xylarium.kernel import nursery, staples
        food, state = staples.of(kernel, p), soc.get("sustenance")
        if state == "pressed":
            out.append(_op("world", f"{p.name} cannot feed its people and has nowhere open to go",
                           f"it eats {food}; stores {staples.stores(kernel, p):,}. Haul {food} in, or RAID the richest "
                           f"holder in reach (it will cost you in the Light)", "POPULATION (World # RAID)", 0.0,
                           urgent=True))
        elif state == "stranded":
            out.append(_op("world", f"{p.name} is hungry and has no yards to reach other worlds",
                           f"it eats {food}; bring {food} in by freight, or raise its citadel to Tier 2 to build ships",
                           "TRADE", 0.0, urgent=True))
        elif state == "expanding":
            out.append(_op("world", f"{p.name} is hungry, but open worlds lie in reach",
                           f"it eats {food}: an exodus fleet will carry its people where they can eat", "POPULATION",
                           0.0))
        fp = soc.get("fertility_parts") or {}
        n = soc.get("nursery")
        name = nursery.design(kernel, p)["name"]
        if n and not n.get("online"):
            out.append(_op("world", f"{p.name}'s {name} is dark",
                           "its inputs ran out and its brood was lost; stock them (or let the port's traders) to relight it",
                           "POPULATION", 0.0, urgent=True))
        elif fp.get("strategy") == "r" and not n and nursery.r0(kernel, p) > 1.0:
            out.append(_op("world", f"{p.name} is crowded past the blight threshold (R0 {nursery.r0(kernel, p):.2f})",
                           f"a plague may kill and rot its granary; {name} lowers transmission",
                           "POPULATION (World # NURSERY)", 0.0, urgent=True))
        elif fp.get("strategy") != "r" and not n and float(fp.get("unstressed", 1.0)) < 1.0:
            why = nursery.why_not(kernel, p)
            a = nursery.appraise(kernel, p)
            dom = PROCESSES[nursery.process(kernel, p)]["domain"]
            out.append(_op("world", f"{p.name}'s people are below replacement (fertility {fp.get('unstressed', 0):.2f}, "
                                    f"meaning {fp.get('meaning', 1.0):.2f})",
                           f"a {name} at your {nursery.mastery(kernel, p):.0%} mastery of {dom} is worth "
                           f"~{a['worth']:,.0f} against ~{a['cost']:,.0f} {p.currency}" + (f" - {why}" if why else "")
                           + f"; more {dom} knowledge makes it stronger and cheaper",
                           "POPULATION (World # NURSERY)" if a["worth"] > a["cost"] else f"RESEARCH {dom.upper()}", 0.0))
        eq = demography.equilibrium(p, kernel)
        if p.citadel_level >= 2 and not p.growth_policy and eq and p.population >= eq * demography.SETTLE_PRESSURE:
            out.append(_op("world", f"{p.name}'s people are ready to choose",
                           "EXPAND sends settler fleets (domes on hostile worlds); STEADY holds its numbers in peace",
                           "POPULATION", 0.0))
    return out


def ventures(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    """Longer plays: stations where travellers are turned away, ships to draw, worlds to claim."""
    from xylarium.kernel import tourism
    out = []
    for p in sector.planets:
        if tourism.station(p) is None and p.population > 0 and p.society.get("turned_away", 0) > 0:
            cost = _sol(kernel, p.currency, tourism.station_cost(p))
            out.append(_op("venture", f"Travellers are turned away at {p.name}",
                           f"{p.society['turned_away']:,} trips found no bed last season; a station costs ~{cost:,.0f} Cr "
                           f"and its owner keeps the takings (less 12% commercial tax)", "STATION", 0.0))
    if getattr(captain, "rank_tier", 1) >= 2 and captain.credits >= 30_000:
        out.append(_op("venture", "Draw your own ship on the workbench",
                       "frames and modules held to volume, power and mass; others who build it pay you a royalty",
                       "WORKBENCH", 0.0))
    return out


def advise(kernel: Any, captain_id: str) -> Dict[str, Any]:
    captain = kernel.captains.get(captain_id)
    if captain is None:
        return {"sections": {}}
    sector = kernel.sectors[captain.sector_id]
    sections = {
        "alerts": [o for o in drive(kernel, captain, sector) + worlds(kernel, captain) if o["urgent"]],
        "here": trades(kernel, captain, sector) + contracts(kernel, captain, sector) + charters(kernel, captain, sector)
        + idle_money(kernel, captain, sector),
        "ship": [o for o in drive(kernel, captain, sector) if not o["urgent"]],
        "worlds": [o for o in worlds(kernel, captain) if not o["urgent"]],
        "polity": politics(kernel, captain, sector),
        "ventures": ventures(kernel, captain, sector),
    }
    return {"sector": sector.id, "sections": sections}


def best(kernel: Any, captain_id: str) -> Optional[Dict[str, Any]]:
    """The single most valuable concrete opportunity (for autonomous captains and the HUD's hint line)."""
    adv = advise(kernel, captain_id)
    pool = [o for ops in adv["sections"].values() for o in ops if o["value_sol"] > 0]
    return max(pool, key=lambda o: o["value_sol"]) if pool else None
