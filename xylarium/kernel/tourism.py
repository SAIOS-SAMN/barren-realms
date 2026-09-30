"""
Xylarium tourism: provided-for peoples travel to what they cannot find at home.

Resorts
  * Pleasure Domes ([RC] RESORT_DOME surface districts): a colony council raises one on an open tile when its
    people are provided for and it can pay the region's contractors; more as its beds fill. A dome drinks
    water each season (pools, gardens, spas) and closes while dry. Receipts go to the world's vault.
  * Commercial orbital stations (private property - the starport is the government's, government.py): an investor
    builds one at a world whose beds turn travellers away, paying the region's builders and the hull metal; its
    receipts go to the owner, less the commercial tax to the system's government.

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
from xylarium.kernel import matter, topology

STATION_METAL = {"Fe": 60, "Ti": 30}


def _hash(*parts: Any) -> int:
    return zlib.crc32(":".join(str(p) for p in parts).encode())


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "tourism")["stats"]


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
    from xylarium.kernel import hulls
    spec = hulls.spec(ship)
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


def station(planet: Any) -> Optional[Dict[str, Any]]:
    return planet.society.get("station")


def station_cost(planet: Any) -> int:
    return int(ORBITAL_STATION_COST * PRICE_LEVEL.get(planet.currency, 1.0))


def build_station(kernel: Any, investor: Any, planet: Any) -> str:
    """A private orbital station at a world: the investor pays the region's builders (a transfer) and the hull
    metal comes out of the system starport's warehouse (a declared sink); the station is the investor's."""
    if station(planet) is not None:
        raise ValueError(f"{planet.name} already has an orbital station.")
    if planet.population <= 0 or getattr(planet, "natives", None):
        raise ValueError("Stations are built over peopled worlds (their guests need somewhere to go).")
    sec = kernel.sectors[planet.sector_id]
    port = sec.port
    if port is None or any(port.stock.get(m, 0) < q for m, q in STATION_METAL.items()):
        raise ValueError("The system's yards lack the hull metal (Fe, Ti) for a station.")
    from xylarium.kernel import fx
    cost_local = station_cost(planet)
    cost_sol = int(_sol(planet.currency, cost_local)) + 1
    if investor.credits < cost_sol:
        raise ValueError(f"A station at {planet.name} costs {cost_sol:,} Cr.")
    investor.credits -= cost_sol
    # the region's builders are paid (households of the world; the port's contractors take the rest)
    local = _convert(kernel, "SOL", planet.currency, cost_sol)
    planet.household_purse += local // 2
    port.treasury += _convert(kernel, planet.currency, port.currency, local - local // 2)
    for m, q in STATION_METAL.items():
        port.stock[m] -= q
        matter.sink("construction", m, q)
    planet.society["station"] = {"owner": investor.id, "berths": ORBITAL_BERTHS_PER_STATION,
                                 "built": kernel.cycle_count, "receipts": 0, "booked": 0}
    stats(kernel)["stations_built"] += 1
    _ = fx
    return f"{investor.name} opened a commercial orbital station over {planet.name} ({ORBITAL_BERTHS_PER_STATION:,} berths)."


def _invest(kernel: Any, st: Dict[str, Any]) -> Optional[str]:
    """Where travellers were turned away last season, an investor with patient capital builds a station."""
    from xylarium.kernel.cognition import temperament
    wanted = [p for s in kernel.sectors.values() for p in s.planets
              if p.society.get("turned_away", 0) > ORBITAL_BERTHS_PER_STATION // 4 and station(p) is None
              and p.population > 0 and not getattr(p, "natives", None)]
    if not wanted:
        return None
    site = max(wanted, key=lambda p: p.society.get("turned_away", 0))
    cost_sol = _sol(site.currency, station_cost(site))
    investors = [c for c in kernel.captains.values() if c.is_ai and not c.faction_id and c.credits >= 4 * cost_sol
                 and temperament(c, kernel).get("horizon", 1.0) >= 1.0]
    if not investors:
        return None
    who = max(investors, key=lambda c: c.credits * temperament(c, kernel).get("horizon", 1.0))
    try:
        return "[TOURISM] " + build_station(kernel, who, site)
    except ValueError:
        return None


# ---------------------------------------------------------------------- tier 1: mass tourism
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
    for sid, hops in topology.hops(kernel, planet.sector_id, TOURISM_RADIUS).items():
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
        for w in sec.planets:
            stn = station(w)
            if stn is None or w is planet:
                continue
            cap = stn["berths"] - stn.get("booked", 0)
            if cap > 0:
                out.append((cap * safety * near * cheapness(w.currency), "station", w, hops))
    out.sort(key=lambda d: -d[0])
    return out[:3]


def site_for(kernel: Any, planet: Any) -> Optional[Any]:
    """Where this world's travellers would most like to go if there were beds: a peopled world in reach, novel
    and safe and near - the investor's signal when demand goes unmet."""
    from xylarium.kernel import biosphere, law
    home = biosphere.metabolism_of(kernel, planet)
    best, score = None, 0.0
    for sid, hops in topology.hops(kernel, planet.sector_id, TOURISM_RADIUS).items():
        sec = kernel.sectors[sid]
        for w in sec.planets:
            if w is planet or w.population <= 0 or getattr(w, "natives", None) or sec.port is None:
                continue
            sc = (1.5 if biosphere.metabolism_of(kernel, w) != home else 0.5) * (
                1.2 if w.planet_type != planet.planet_type else 1.0) * (0.5 + 0.5 * law.presence(kernel, sec)) / (1 + hops)
            if sc > score:
                best, score = w, sc
    return best


def _travel(kernel: Any, planet: Any, st: Dict[str, Any]) -> None:
    if not spacefaring(kernel, planet):
        return
    budget = int(planet.household_purse * TOURISM_PURSE_SHARE)
    if budget <= 0:
        return
    origin_sec = kernel.sectors[planet.sector_id]
    port = origin_sec.port
    if port is None:
        return
    level = PRICE_LEVEL.get(planet.currency, 1.0)
    per_head = max(1, int(TOURIST_SPEND_PER_HEAD * level))
    dests = destinations(kernel, planet)
    wanted_trips = budget // per_head
    placed = sum(max(0, (beds(d[2]) - d[2].society.get("booked", 0)) if d[1] == "resort"
                     else station(d[2])["berths"] - station(d[2]).get("booked", 0)) for d in dests)
    if wanted_trips > placed:
        site = site_for(kernel, planet)
        if site is not None:
            site.society["turned_away"] = site.society.get("turned_away", 0) + wanted_trips - placed
    if not dests:
        return
    total_attr = sum(d[0] for d in dests)
    from xylarium.kernel import fibres
    for attr, kind, place, hops in dests:
        spend = int(budget * attr / total_attr)
        trips = spend // per_head
        stn = station(place) if kind == "station" else None
        booked = place.society.get("booked", 0) if kind == "resort" else stn.get("booked", 0)
        cap = (beds(place) if kind == "resort" else stn["berths"]) - booked
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
            # a commercial station: the owner's receipts, less the commercial tax to the system's government
            local = _convert(kernel, planet.currency, place.currency, stay)
            from xylarium.kernel import government
            tax = int(local * government.COMMERCIAL_TAX)
            if government.pay_government(kernel, kernel.sectors[place.sector_id], place.currency, tax,
                                         "commercial_tax") == "none":
                tax = 0
            owner = kernel.captains.get(stn["owner"])
            if owner is not None:
                from xylarium.kernel.fx import credit
                credit(owner, place.currency, local - tax)
            else:
                place.treasury += local - tax                      # an heirless station's takings go to the world
            stn["booked"] = booked + trips
            stn["receipts"] = stn.get("receipts", 0) + local - tax
            st["station_receipts_sol"] = st.get("station_receipts_sol", 0.0) + _sol(place.currency, local - tax)
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
    return state.of(kernel, "tourism")["charters"]


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
    from xylarium.kernel import biosphere
    book[cid] = {"id": cid, "origin_planet": planet.id, "origin_sector": planet.sector_id,
                 "guests": biosphere.metabolism_of(kernel, planet),
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
    # The escrow is the full fare for a ship built for these guests; a hull without decks for their biology earns
    # half of it, and the rest goes back to the guests' households
    from xylarium.kernel.fx import credit
    from xylarium.kernel import shipdesign
    fit = shipdesign.comfort_fit(captain.ship, c.get("guests", "biotic"))
    pay = int(c["escrow"] * (0.5 + 0.5 * fit))
    credit(captain, c["currency"], pay)
    if c["escrow"] - pay > 0:
        _refund(kernel, c, c["escrow"] - pay)
    st = stats(kernel)
    st["charters"]["flown"] += 1
    st["charters"]["paid_sol"] += _sol(c["currency"], pay)
    st["charters"]["comfort_sum"] = st["charters"].get("comfort_sum", 0.0) + fit
    c["status"] = "DELIVERED"
    captain.charter = None
    return f"[CHARTER] {captain.name} delivered {c['party']} VIPs to {c['dest_name']} for {pay:,} {c['currency']} (comfort {fit:.0%})."


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
            stn = station(p)
            if stn is not None:
                if stn.get("booked") and ledger.ACTIVE_POLICY is not None:
                    ledger.ACTIVE_POLICY.record_output(p.currency, stn["booked"] * TOURIST_SPEND_PER_HEAD
                                                       * PRICE_LEVEL.get(p.currency, 1.0))
                stn["booked"] = 0
    log = _invest(kernel, st)
    if log:
        logs.append(log)
    for sec in kernel.sectors.values():
        for p in sec.planets:
            p.society.pop("turned_away", None)
    for sec in kernel.sectors.values():
        for p in sec.planets:
            _travel(kernel, p, st)
            _post_charter(kernel, p, st)
    _expire(kernel, st)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    domes = sum(resorts(p) for s in kernel.sectors.values() for p in s.planets)
    stations = sum(1 for s in kernel.sectors.values() for p in s.planets if station(p) is not None)
    open_ch = sum(1 for c in charters(kernel).values() if c["status"] in ("OPEN", "IN_TRANSIT"))
    return {**st, "domes": domes, "stations": stations, "charters_open": open_ch}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="tourism",
    state=lambda: {"stats": {"trips": 0, "spend_sol": 0.0, "fares_sol": 0.0, "h_burned": 0, "resorts_built": 0,
                             "stations_built": 0, "h_short_trips": 0,
                             "charters": {"posted": 0, "flown": 0, "ransomed": 0, "expired": 0,
                                          "paid_sol": 0.0, "ransom_sol": 0.0}},
                   "charters": {}},
    season=quarter,
    summary=summary,
))
