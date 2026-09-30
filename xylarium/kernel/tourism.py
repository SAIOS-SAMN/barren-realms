"""
Xylarium tourism: provided-for peoples travel to what they cannot find at home.

Resorts
  * Pleasure Domes ([RC] RESORT_DOME surface districts): a colony council raises one on an open tile when its
    people are provided for and it can pay the region's contractors; more as its beds fill. A dome drinks
    water each season (pools, gardens, spas) and closes while dry. Receipts go to the world's vault.
  * Orbital leisure stations: a starport that has carried tourists for several seasons builds one from its own
    treasury, paying the region's households as builders and consuming hull metal; receipts go to the port
    (and on to the region through its payroll).

Tier 1 - mass tourism (an abstracted flow along the lanes)
  Households of spacefaring worlds spend part of what is left after the basket and luxuries on travel. They
  go where it is novel (another people, another sky), safe (the law's presence) and near (fewer jumps), up to
  the beds available. A quarter of each fare pays the origin port's carriers, who burn hydrogen for every
  hundred passenger-jumps (exhaust stays in the origin sector: a transfer); the rest is spent at the resort,
  converted through the exchanges into its money. The trips develop the lanes they cross (fibres).
  With no hydrogen at the origin port, fewer tourists can travel.

Tier 2 - VIP charters (physical passengers)
  Rich worlds post charters: a party of VIPs, a destination resort, and a fare escrowed from the households.
  A captain docked at the origin with enough berths (a liner's staterooms, or a tenth of any hull's holds)
  signs on and flies them; the escrow is paid on arrival. A pirate who destroys a liner with VIPs aboard
  holds them for ransom (a share of the escrow; the rest is refunded). Unflown charters expire and refund.
"""

import zlib
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import (
    CHARTER_EXPIRY_CYCLES,
    CHARTER_FARE_PER_VIP_HOP,
    CHARTER_MIN_PURSE,
    CHARTER_PARTY,
    CHARTER_RANSOM_SHARE,
    DAUGHTER_CITADEL_TIER,
    ORBITAL_BERTHS_PER_STATION,
    ORBITAL_STATION_COST,
    ORBITAL_STATION_MIN_FLOW,
    PRICE_LEVEL,
    RESORT_BEDS,
    RESORT_COST,
    RESORT_H2O_PER_QUARTER,
    RESORT_ORE,
    SHIP_CATALOG,
    TOURISM_FARE_SHARE,
    TOURISM_PURSE_SHARE,
    TOURISM_RADIUS,
    TOURIST_H_PER_HUNDRED_HOPS,
    TOURIST_SPEND_PER_HEAD,
)
from xylarium.kernel import matter

STATION_METAL = {"Fe": 60, "Ti": 30}


def _hash(*parts: Any) -> int:
    return zlib.crc32(":".join(str(p) for p in parts).encode())


def stats(kernel: Any) -> Dict[str, Any]:
    s = getattr(kernel, "tourism_stats", None)
    if s is None:
        s = kernel.tourism_stats = {"trips": 0, "spend_sol": 0.0, "fares_sol": 0.0, "h_burned": 0,
                                    "resorts_built": 0, "stations_built": 0, "h_short_trips": 0,
                                    "charters": {"posted": 0, "flown": 0, "ransomed": 0, "expired": 0,
                                                 "paid_sol": 0.0, "ransom_sol": 0.0}}
    return s


def _sol(cur: str, amount: float) -> float:
    from xylarium.kernel import fx
    return fx.ACTIVE_FX.to_sol_value(cur, amount) if (fx.ACTIVE_FX is not None and cur != "SOL") else float(amount)


def _convert(kernel: Any, from_cur: str, to_cur: str, amount: int) -> int:
    if from_cur == to_cur or amount <= 0:
        return amount
    out, _ = kernel.fx_market.convert(from_cur, to_cur, amount)
    return out


# ---------------------------------------------------------------------- resorts
def resorts(planet: Any) -> int:
    g = planet.surface_grid
    if not g:
        return 0
    return sum(1 for t in g.get("tiles", []) if t.get("district") == "RESORT_DOME")


def beds(planet: Any) -> int:
    """Open beds this season: domes that had their water."""
    return resorts(planet) * RESORT_BEDS if not planet.society.get("resort_dry") else 0


def berths(ship: Any) -> int:
    spec = SHIP_CATALOG.get(ship.ship_type, {})
    return int(spec.get("berths", spec.get("holds", 25) // 10))


def spacefaring(kernel: Any, planet: Any) -> bool:
    """Can this world's people travel? Colonies of captains can, and civilizations with a yard."""
    if planet.population <= 0 or getattr(planet, "natives", None):
        return False
    return planet.owner_id is not None or planet.citadel_level >= DAUGHTER_CITADEL_TIER or bool(planet.metropole_id)


def _build_resort(kernel: Any, planet: Any, st: Dict[str, Any]) -> Optional[str]:
    from xylarium.kernel import demography, luxury
    from xylarium.kernel.surface import SurfaceManager, DistrictType, TerrainType
    if not demography.self_governed(planet, kernel) or not luxury.provided_for(kernel, planet):
        return None
    n = resorts(planet)
    if n >= max(1, planet.citadel_level):
        return None
    if n > 0 and planet.society.get("occupancy", 0.0) < 0.8:
        return None                                          # build more only when the beds are full
    if kernel.sectors[planet.sector_id].port is None:
        return None
    level = PRICE_LEVEL.get(planet.currency, 1.0)
    cost = int(RESORT_COST * level)
    reserve = int(demography.DEMOGRAPHY_COUNCIL_RESERVE * level)
    if planet.treasury < cost + reserve or planet.ore_silo < RESORT_ORE + 600:
        return None
    grid = SurfaceManager.ensure_surface_grid(planet)
    empty = [t for t in grid.tiles if t.district == DistrictType.EMPTY]
    if not empty:
        return None
    pick = [t for t in empty if t.terrain in (TerrainType.GLACIAL_LAKE, TerrainType.PLAINS)] or empty
    tile = pick[_hash(planet.id, n) % len(pick)]
    tile.district = DistrictType.RESORT_DOME
    planet.surface_grid = grid.to_dict()
    demography._pay_contractor(kernel, planet, cost)
    matter.consume(planet, "ore_silo", "ORE", RESORT_ORE, "construction")
    st["resorts_built"] += 1
    return f"[TOURISM] {planet.name} opened a Pleasure Dome ({n + 1} on the world)."


def _water_resorts(kernel: Any, planet: Any) -> None:
    n = resorts(planet)
    if n <= 0:
        return
    need = n * RESORT_H2O_PER_QUARTER
    have = planet.element_reserves.get("H2O", 0)
    if have >= need:
        planet.element_reserves["H2O"] = have - need
        matter.sink("resort_upkeep", "H2O", need)
        planet.society.pop("resort_dry", None)
    else:
        planet.society["resort_dry"] = True


def _build_station(kernel: Any, sec: Any, st: Dict[str, Any]) -> Optional[str]:
    port = sec.port
    lz = port.leisure
    if lz.get("berths", 0) > 0 or lz.get("flow_seasons", 0) < ORBITAL_STATION_MIN_FLOW:
        return None
    from xylarium.config import PORT_START_TREASURY, PORT_OPEX_FLOOR
    level = PRICE_LEVEL.get(port.currency, 1.0)
    cost = int(ORBITAL_STATION_COST * level)
    floor = int(PORT_START_TREASURY * level * PORT_OPEX_FLOOR)
    if port.treasury < cost + floor:
        return None
    if any(port.stock.get(m, 0) < q for m, q in STATION_METAL.items()):
        return None
    builders = [p for p in sec.planets if p.population > 0 and not getattr(p, "natives", None)]
    if not builders:
        return None
    # The region's households build it (wages are a transfer); the hull metal comes from the port's warehouse
    port.treasury -= cost
    share = cost // len(builders)
    for i, p in enumerate(builders):
        pay = share + (cost - share * len(builders) if i == 0 else 0)
        p.household_purse += _convert(kernel, port.currency, p.currency, pay)
    for m, q in STATION_METAL.items():
        port.stock[m] -= q
        matter.sink("construction", m, q)
    lz["berths"] = ORBITAL_BERTHS_PER_STATION
    lz["built_cycle"] = kernel.cycle_count
    st["stations_built"] += 1
    return f"[TOURISM] {port.name} opened an orbital leisure station ({ORBITAL_BERTHS_PER_STATION:,} berths)."


# ---------------------------------------------------------------------- tier 1: mass tourism
def _hops(kernel: Any, origin: int, radius: int) -> Dict[int, int]:
    dist, frontier = {origin: 0}, [origin]
    while frontier:
        nxt = []
        for sid in frontier:
            if dist[sid] >= radius:
                continue
            for w in kernel.sectors[sid].warps:
                if w in kernel.sectors and w not in dist:
                    dist[w] = dist[sid] + 1
                    nxt.append(w)
        frontier = nxt
    return dist


def destinations(kernel: Any, planet: Any) -> List[Tuple[float, str, Any, int]]:
    """(attraction, kind, place, hops) for resorts in reach: novel, safe and near first."""
    from xylarium.kernel import biosphere, law, fx
    home = biosphere.metabolism_of(kernel, planet)
    out: List[Tuple[float, str, Any, int]] = []

    def cheapness(cur: str) -> float:
        """How far the traveller's money goes there: a weakened currency abroad is a cheap holiday, a weakened
        one at home an expensive one (the exchanges' drift from genesis price levels)."""
        if fx.ACTIVE_FX is None or cur == planet.currency:
            return 1.0
        return fx.ACTIVE_FX.price_level_drift(cur) / fx.ACTIVE_FX.price_level_drift(planet.currency)
    for sid, hops in _hops(kernel, planet.sector_id, TOURISM_RADIUS).items():
        sec = kernel.sectors[sid]
        safety = 0.5 + 0.5 * law.presence(kernel, sec)
        near = 1.0 / (1 + hops)
        for w in sec.planets:
            cap = beds(w) - w.society.get("booked", 0)
            if w is planet or cap <= 0:
                continue
            novelty = (1.5 if biosphere.metabolism_of(kernel, w) != home else 0.5) * (
                1.2 if w.planet_type != planet.planet_type else 1.0)
            out.append((cap * novelty * safety * near * cheapness(w.currency), "resort", w, hops))
        port = sec.port
        if port is not None and port.leisure.get("berths", 0) > 0 and sid != planet.sector_id:
            cap = port.leisure["berths"] - port.leisure.get("booked", 0)
            if cap > 0:
                out.append((cap * safety * near * cheapness(port.currency), "station", port, hops))
    out.sort(key=lambda d: -d[0])
    return out[:3]


def _travel(kernel: Any, planet: Any, st: Dict[str, Any]) -> None:
    if not spacefaring(kernel, planet):
        return
    budget = int(planet.household_purse * TOURISM_PURSE_SHARE)
    if budget <= 0:
        return
    dests = destinations(kernel, planet)
    if not dests:
        return
    origin_sec = kernel.sectors[planet.sector_id]
    port = origin_sec.port
    if port is None:
        return
    level = PRICE_LEVEL.get(planet.currency, 1.0)
    per_head = max(1, int(TOURIST_SPEND_PER_HEAD * level))
    total_attr = sum(d[0] for d in dests)
    from xylarium.kernel import fibres
    for attr, kind, place, hops in dests:
        spend = int(budget * attr / total_attr)
        trips = spend // per_head
        booked = place.society.get("booked", 0) if kind == "resort" else place.leisure.get("booked", 0)
        cap = (beds(place) if kind == "resort" else place.leisure["berths"]) - booked
        trips = min(trips, cap)
        if trips <= 0:
            continue
        # The carriers need reaction mass: a hundred passenger-jumps burn one unit of the port's hydrogen
        h_need = (trips * max(1, hops) * TOURIST_H_PER_HUNDRED_HOPS + 99) // 100
        h_have = port.stock.get("H", 0)
        if h_have < h_need:
            flown = trips * h_have // max(1, h_need)
            st["h_short_trips"] += trips - flown
            trips, h_need = flown, h_have
        if trips <= 0:
            continue
        bill = trips * per_head
        fare = int(bill * TOURISM_FARE_SHARE)
        planet.household_purse -= bill
        port.treasury += fare
        port.stock["H"] = port.stock.get("H", 0) - h_need
        origin_sec.gas = getattr(origin_sec, "gas", 0) + h_need       # the exhaust drifts in the origin system
        st["h_burned"] += h_need
        stay = bill - fare
        if kind == "resort":
            place.treasury += _convert(kernel, planet.currency, place.currency, stay)
            place.society["booked"] = booked + trips
            place.society["receipts"] = place.society.get("receipts", 0) + stay
        else:
            place.treasury += _convert(kernel, planet.currency, place.currency, stay)
            place.leisure["booked"] = booked + trips
        port.leisure["traffic"] = port.leisure.get("traffic", 0) + trips
        if kind == "station":
            place.leisure["traffic"] = place.leisure.get("traffic", 0) + trips
        dest_sid = place.sector_id
        path = kernel.find_path(planet.sector_id, dest_sid) if dest_sid != planet.sector_id else []
        spend_sol = _sol(planet.currency, bill)
        for a, b in zip(path, path[1:]):
            fibres.record_flow(kernel, a, b, spend_sol)
        st["trips"] += trips
        st["spend_sol"] += spend_sol
        st["fares_sol"] += _sol(planet.currency, fare)


# ---------------------------------------------------------------------- tier 2: VIP charters
def charters(kernel: Any) -> Dict[str, Dict[str, Any]]:
    c = getattr(kernel, "charters", None)
    if c is None:
        c = kernel.charters = {}
    return c


def _post_charter(kernel: Any, planet: Any, st: Dict[str, Any]) -> None:
    if not spacefaring(kernel, planet) or kernel.sectors[planet.sector_id].port is None:
        return
    if _sol(planet.currency, planet.household_purse) < CHARTER_MIN_PURSE:
        return
    book = charters(kernel)
    if any(c["origin_planet"] == planet.id and c["status"] in ("OPEN", "IN_TRANSIT") for c in book.values()):
        return
    dests = [d for d in destinations(kernel, planet) if d[3] > 0]
    if not dests:
        return
    _, kind, place, hops = dests[0]
    lo, hi = CHARTER_PARTY
    party = lo + _hash(planet.id, kernel.cycle_count) % (hi - lo + 1)
    level = PRICE_LEVEL.get(planet.currency, 1.0)
    escrow = int(party * hops * CHARTER_FARE_PER_VIP_HOP * level)
    if escrow <= 0 or planet.household_purse < escrow * 2:
        return
    planet.household_purse -= escrow
    cid = f"VIP-{planet.id[-6:]}-{kernel.cycle_count}"
    book[cid] = {"id": cid, "origin_planet": planet.id, "origin_sector": planet.sector_id,
                 "dest_sector": place.sector_id, "dest_name": getattr(place, "name", "?"), "party": party,
                 "escrow": escrow, "currency": planet.currency, "status": "OPEN", "captain": None,
                 "posted": kernel.cycle_count}
    st["charters"]["posted"] += 1


def _refund(kernel: Any, c: Dict[str, Any], amount: int) -> None:
    origin = kernel.get_planet(c["origin_planet"]) if hasattr(kernel, "get_planet") else None
    if origin is not None:
        origin.household_purse += _convert(kernel, c["currency"], origin.currency, amount)
    else:
        from xylarium.kernel import ledger
        ledger.pay_service(int(_sol(c["currency"], amount)), institution="charter_refund")


def accept(kernel: Any, captain: Any, sector: Any) -> Optional[str]:
    """A captain docked at a charter's origin with the berths for its party signs on."""
    if captain.charter or getattr(captain, "frozen_by", None):
        return None
    room = berths(captain.ship)
    for c in charters(kernel).values():
        if c["status"] == "OPEN" and c["origin_sector"] == sector.id and c["party"] <= room:
            c["status"], c["captain"], c["accepted"] = "IN_TRANSIT", captain.id, kernel.cycle_count
            captain.charter = c["id"]
            return c["id"]
    return None


def arrive(kernel: Any, captain: Any) -> Optional[str]:
    """Called after every jump: a charter reaching its destination pays its escrow to the captain."""
    cid = getattr(captain, "charter", None)
    if not cid:
        return None
    c = charters(kernel).get(cid)
    if c is None or c["status"] != "IN_TRANSIT":
        captain.charter = None
        return None
    if captain.sector_id != c["dest_sector"]:
        return None
    from xylarium.kernel.fx import credit
    credit(captain, c["currency"], c["escrow"])
    st = stats(kernel)
    st["charters"]["flown"] += 1
    st["charters"]["paid_sol"] += _sol(c["currency"], c["escrow"])
    c["status"] = "DELIVERED"
    captain.charter = None
    return f"[CHARTER] {captain.name} delivered {c['party']} VIPs to {c['dest_name']} for {c['escrow']:,} {c['currency']}."


def intercept(kernel: Any, pirate: Optional[Any], liner: Any) -> Optional[str]:
    """A liner lost with VIPs aboard: its attacker holds them for ransom; the rest is refunded."""
    cid = getattr(liner, "charter", None)
    if not cid:
        return None
    liner.charter = None
    c = charters(kernel).get(cid)
    if c is None or c["status"] != "IN_TRANSIT":
        return None
    st = stats(kernel)
    ransom = int(c["escrow"] * CHARTER_RANSOM_SHARE) if pirate is not None else 0
    if ransom > 0:
        from xylarium.kernel.fx import credit
        credit(pirate, c["currency"], ransom)
        st["charters"]["ransomed"] += 1
        st["charters"]["ransom_sol"] += _sol(c["currency"], ransom)
        c["status"] = "RANSOMED"
        from xylarium.kernel import law
        sec = kernel.sectors.get(liner.sector_id)
        if sec is not None:
            law.file(kernel, "kidnapping", pirate, sec, int(_sol(c["currency"], ransom)),
                     {"kind": "planet", "id": c["origin_planet"]})
    else:
        c["status"] = "LOST"
    _refund(kernel, c, c["escrow"] - ransom)
    return f"[CHARTER] {c['party']} VIPs aboard {liner.name}'s liner were " + (
        f"taken for a {ransom:,} {c['currency']} ransom." if ransom else "lost with the hull.")


def ai_turn(kernel: Any, captain: Any, sector: Any) -> bool:
    """An autonomous captain with VIPs aboard flies them to their resort; one docked at an origin signs on."""
    from xylarium.kernel.models import ActionType
    if not captain.charter:
        if not captain.faction_id:
            accept(kernel, captain, sector)
        if not captain.charter:
            return False
    c = charters(kernel).get(captain.charter)
    if c is None or c["status"] != "IN_TRANSIT":
        captain.charter = None
        return False
    path = kernel.find_path(sector.id, c["dest_sector"])
    if not path or len(path) < 2:
        return False
    res = kernel.dispatch(captain.id, ActionType.MOVE, destination=path[1])
    return bool(getattr(res, "success", False))


def _expire(kernel: Any, st: Dict[str, Any]) -> None:
    for c in charters(kernel).values():
        age = kernel.cycle_count - c["posted"]
        if c["status"] == "OPEN" and age > CHARTER_EXPIRY_CYCLES:
            c["status"] = "EXPIRED"
            _refund(kernel, c, c["escrow"])
            st["charters"]["expired"] += 1
        elif c["status"] == "IN_TRANSIT" and age > 2 * CHARTER_EXPIRY_CYCLES:
            cap = kernel.captains.get(c["captain"])
            if cap is not None and cap.charter == c["id"]:
                cap.charter = None
            c["status"] = "EXPIRED"
            _refund(kernel, c, c["escrow"])
            st["charters"]["expired"] += 1
    book = charters(kernel)
    for cid in [k for k, c in book.items() if c["status"] not in ("OPEN", "IN_TRANSIT")
                and kernel.cycle_count - c["posted"] > CHARTER_EXPIRY_CYCLES]:
        del book[cid]


# ---------------------------------------------------------------------- the quarter
def quarter(kernel: Any) -> List[str]:
    """Resorts are raised and watered, stations built, tourists travel, charters are posted and expire."""
    logs: List[str] = []
    st = stats(kernel)
    from xylarium.kernel import ledger
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population <= 0 or getattr(p, "natives", None):
                continue
            # last season's occupancy, then a fresh season of bookings
            cap = resorts(p) * RESORT_BEDS
            if cap:
                p.society["occupancy"] = round(p.society.get("booked", 0) / cap, 3)
                # Resort services are real output (the Y of M V = P Y)
                if ledger.ACTIVE_POLICY is not None and p.society.get("booked", 0):
                    ledger.ACTIVE_POLICY.record_output(p.currency, p.society["booked"] * TOURIST_SPEND_PER_HEAD
                                                       * PRICE_LEVEL.get(p.currency, 1.0))
            p.society["booked"] = 0
            log = _build_resort(kernel, p, st)
            if log:
                logs.append(log)
            _water_resorts(kernel, p)
        port = sec.port
        if port is not None:
            lz = port.leisure
            if lz.get("traffic", 0) > 0:
                lz["flow_seasons"] = lz.get("flow_seasons", 0) + 1
            if lz.get("booked") and ledger.ACTIVE_POLICY is not None:
                ledger.ACTIVE_POLICY.record_output(port.currency, lz["booked"] * TOURIST_SPEND_PER_HEAD
                                                   * PRICE_LEVEL.get(port.currency, 1.0))
            lz["traffic"] = 0
            lz["booked"] = 0
            log = _build_station(kernel, sec, st)
            if log:
                logs.append(log)
    for sec in kernel.sectors.values():
        for p in sec.planets:
            _travel(kernel, p, st)
            _post_charter(kernel, p, st)
    _expire(kernel, st)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    domes = sum(resorts(p) for s in kernel.sectors.values() for p in s.planets)
    stations = sum(1 for s in kernel.sectors.values() if s.port is not None and s.port.leisure.get("berths"))
    open_ch = sum(1 for c in charters(kernel).values() if c["status"] in ("OPEN", "IN_TRANSIT"))
    return {**st, "domes": domes, "stations": stations, "charters_open": open_ch}
