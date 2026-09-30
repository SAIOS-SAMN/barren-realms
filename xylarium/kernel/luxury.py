"""
Xylarium luxury: what a provided-for people makes for pleasure, and what it craves from elsewhere.

  * Four super-types, each a traded commodity (config LUXURY_TYPES): sensory stimulants (stress and morale),
    resonant artifacts (piezo-crystal chimes; lift research), exotic ephemera (perishable gastronomy; they
    spoil, so they move fast) and precursor curios (vanity relics that soak up elite money).
  * A world's signature luxury is chosen by its council from what it holds in abundance - the super-type
    whose input (by the people's metabolism) is most plentiful on the world, weighted by the species'
    affinity and by ruins for curios - and it is named for its people and its world ("Neth Flarelight
    Nectar"). The name is flavour; the commodity is the type, so ports and haulers trade it like any good.
  * Crafting is a conversion of held matter: one unit of the input becomes one unit of luxury (the labour is
    the value added). Only a provided-for world crafts (its basket filled, no famine or bombardment).
  * Demand is inverse to local availability: households want each luxury in proportion to their comfort,
    and want their own signature half as much (they make it). They buy the rest from the region's ports with
    part of the purse left after the basket. Luxury access (share of wants met) lifts morale and, for
    K-strategists, compresses fertility (fertility.py).
  * Surplus luxuries above the world's reserve are exported to the region's ports (demography.exports).
"""

import math
import zlib
from typing import Any, Dict, List, Optional

from xylarium.config import (
    COMMODITY_CONFIG,
    EPHEMERA_SPOILAGE,
    LUXURY_AFFINITY,
    LUXURY_CRAFT_PER_THOUSAND,
    LUXURY_PURSE_SHARE,
    LUXURY_TYPES,
    LUXURY_WANT_PER_THOUSAND,
    LUXURY_WORLD_BIAS,
    PRICE_LEVEL,
)
from xylarium.kernel import matter

_ADJECTIVE = {"TERRESTRIAL": ["Verdant", "Rainroot", "Meadow"], "OCEANIC": ["Tidal", "Brine", "Deepwater"],
              "ICE": ["Rime", "Glacier", "Stillcold"], "VOLCANIC": ["Ember", "Caldera", "Ashen"],
              "BARREN": ["Dust", "Regolith", "Hollow"], "GAS_GIANT": ["Flarelight", "Stormband", "Cloudsea"],
              "ROGUE": ["Nightwander", "Starless", "Drift"]}
_NOUN = {"LUX_STIMULANT": ["Nectar", "Incense", "Resin"], "LUX_RESONANT": ["Chimes", "Lattice", "Singing Glass"],
         "LUX_EPHEMERA": ["Bloom", "Caviar", "Spore Wine"], "LUX_CURIO": ["Reliquary", "Idols", "Star-Maps"]}


def _hash(*parts: Any) -> int:
    return zlib.crc32(":".join(str(p) for p in parts).encode())


# ---------------------------------------------------------------------- holdings
def held(planet: Any, comm: str) -> int:
    if comm == "ORGANICS":
        return planet.organics_silo
    if comm == "ORE":
        return planet.ore_silo
    return planet.element_reserves.get(comm, 0)


def _reserve(kernel: Any, planet: Any, comm: str) -> int:
    """What the world keeps of an input for itself: two seasons' food, its works' ore, a reserve of elements."""
    from xylarium.kernel import biosphere
    from xylarium.kernel.demography import ELEMENT_RESERVE_KEPT, _quarter_len
    if comm == "ORGANICS":
        return 2 * _quarter_len() * biosphere.consumption(planet)
    if comm == "ORE":
        return 600
    return ELEMENT_RESERVE_KEPT


def _take(planet: Any, comm: str, n: int, kind: str) -> None:
    if comm == "ORGANICS":
        matter.consume(planet, "organics_silo", "ORGANICS", n, kind)
    elif comm == "ORE":
        matter.consume(planet, "ore_silo", "ORE", n, kind)
    else:
        planet.element_reserves[comm] = planet.element_reserves.get(comm, 0) - n
        matter.sink(kind, comm, n)


# ---------------------------------------------------------------------- the signature
def people_name(kernel: Any, planet: Any) -> str:
    civ = getattr(planet, "civilization", None)
    if civ is not None and planet.owner_id is None:
        return civ.name.split()[-1] if civ.name else planet.name
    return planet.name.split()[0]


def _input(planet: Any, t: str, metab: str) -> Optional[str]:
    """The first of the type's inputs (for this people) that the world holds; else its first choice."""
    options = LUXURY_TYPES[t]["inputs"].get(metab) or []
    for comm in options:
        if held(planet, comm) > 0:
            return comm
    return options[0] if options else None


def signature(kernel: Any, planet: Any) -> Optional[Dict[str, str]]:
    """The luxury this world crafts: what its world lends itself to, its people's affinity, and what it holds
    (a world with ruins turns to curios); named for its people and its world."""
    from xylarium.kernel import biosphere
    metab = biosphere.metabolism_of(kernel, planet)
    soc = planet.society
    cur = soc.get("luxury")
    if cur and cur.get("metabolism") == metab:
        comm = _input(planet, cur["type"], metab)
        if comm and comm != cur.get("input") and held(planet, comm) > 0:
            cur["input"] = comm
        return cur
    bias = LUXURY_WORLD_BIAS.get(planet.planet_type, {})
    best, score = None, -1.0
    for t in LUXURY_TYPES:
        comm = _input(planet, t, metab)
        if not comm:
            continue
        s = bias.get(t, 1.0) * (1.3 if LUXURY_AFFINITY.get(metab) == t else 1.0)
        s *= 1.0 if held(planet, comm) > 0 else 0.3
        if t == "LUX_CURIO" and getattr(planet, "ruins", None):
            s *= 2.0
        s += (_hash(planet.id, t) % 30) / 100.0             # each world's own taste
        if s > score:
            best, score = t, s
    if best is None:
        return None
    h = _hash(planet.id, best)
    adj = _ADJECTIVE.get(planet.planet_type, ["Far"])
    noun = _NOUN[best]
    soc["luxury"] = {"type": best, "metabolism": metab, "input": _input(planet, best, metab),
                     "name": f"{people_name(kernel, planet)} {adj[h % len(adj)]} {noun[(h >> 4) % len(noun)]}"}
    return soc["luxury"]


# ---------------------------------------------------------------------- the order book
LUX_STOCK_SEASONS = 2          # a port keeps two seasons of what its households buy
LUX_STOCK_MIN = 20             # ...and a shelf's worth to find out whether anyone will


def port_target(port: Any, t: str, kernel: Any = None) -> int:
    """A shopkeeper stocks for its customers: a season of what its catchment's households would want, or two
    seasons of what it actually sold (to households and to captains), whichever is more."""
    sales = float((port.leisure.get("lux_sales") or {}).get(t, 0.0))
    catchment = int((port.leisure.get("lux_catchment") or {}).get(t, 0))
    target = max(LUX_STOCK_MIN, catchment, int(LUX_STOCK_SEASONS * sales))
    mult = council_bid_multiplier(port, t, kernel)
    if mult > 1.0:
        target = max(target, int(40 * mult))
    return target


def port_room(port: Any, t: str, kernel: Any = None) -> int:
    return max(0, port_target(port, t, kernel) - port.stock.get(t, 0))


def record_sale(port: Any, t: str, units: int) -> None:
    q = port.leisure.setdefault("lux_q", {})
    q[t] = q.get(t, 0) + units


def _close_sales(port: Any) -> None:
    """Each season a port's luxury sales become its smoothed demand (what it will stock next season)."""
    q = port.leisure.pop("lux_q", {}) or {}
    sales = port.leisure.setdefault("lux_sales", {})
    for t in LUXURY_TYPES:
        sales[t] = round(0.5 * float(sales.get(t, 0.0)) + 0.5 * q.get(t, 0), 2)


def orders(kernel: Any, planet: Any, t: str) -> int:
    """What a world's workshops can sell next season: room on its region's shelves plus its own households' use,
    less what it already holds. Luxuries are crafted to order - perishable ones especially."""
    from xylarium.kernel import demography
    shelves = sum(port_room(p, t, kernel) for p in demography._markets(kernel, planet))
    comfort = float(planet.society.get("basket_fill", 0.0))
    own = int(planet.population / 1000.0 * LUXURY_WANT_PER_THOUSAND * 0.5 * comfort)
    return max(0, shelves + own - planet.element_reserves.get(t, 0))


def provided_for(kernel: Any, planet: Any) -> bool:
    from xylarium.kernel import fertility
    return planet.society.get("basket_fill", 0.0) >= 0.8 and not fertility.stressed(kernel, planet)


# ---------------------------------------------------------------------- crafting
def stats(kernel: Any) -> Dict[str, Any]:
    s = getattr(kernel, "luxury_stats", None)
    if s is None:
        s = kernel.luxury_stats = {"crafted": {}, "bought": {}, "own_use": 0, "spend": {}, "spend_sol": 0.0,
                                   "spoiled": 0, "want": 0, "met": 0}
    return s


def _market_value(kernel: Any, planet: Any, t: str) -> float:
    """What the region's ports pay for a luxury (the best bid in reach, in the world's money)."""
    from xylarium.kernel import demography
    from xylarium.kernel.economy import EconomyManager
    bids = [EconomyManager.get_unit_prices(p, t)[0] for p in demography._markets(kernel, planet)
            if p.buys.get(t) and p.stock.get(t, 0) < p.max_stock.get(t, 600)]
    return float(max(bids)) if bids else 0.0


def reconsider(kernel: Any, planet: Any) -> Optional[str]:
    """Once a year the council reads the market: if another luxury its world can make fetches clearly more
    (x the world's own leaning), its workshops turn to it. Supply follows the region's wants."""
    from xylarium.kernel import biosphere
    sig = signature(kernel, planet)
    if sig is None:
        return None
    soc = planet.society
    if kernel.cycle_count - soc.get("lux_reviewed", -10 ** 9) < 4 * _quarter():
        return None
    soc["lux_reviewed"] = kernel.cycle_count
    metab = biosphere.metabolism_of(kernel, planet)
    bias = LUXURY_WORLD_BIAS.get(planet.planet_type, {})

    def worth(t: str) -> float:
        comm = _input(planet, t, metab)
        if not comm or held(planet, comm) <= _reserve(kernel, planet, comm):
            return 0.0
        return _market_value(kernel, planet, t) * bias.get(t, 1.0) * (1.3 if LUXURY_AFFINITY.get(metab) == t else 1.0)

    now = worth(sig["type"])
    best = max(LUXURY_TYPES, key=worth)
    if best != sig["type"] and worth(best) > 1.25 * now:
        h = _hash(planet.id, best)
        adj = _ADJECTIVE.get(planet.planet_type, ["Far"])
        noun = _NOUN[best]
        soc["luxury"] = {"type": best, "metabolism": metab, "input": _input(planet, best, metab),
                         "name": f"{people_name(kernel, planet)} {adj[h % len(adj)]} {noun[(h >> 4) % len(noun)]}"}
        stats(kernel)["switches"] = stats(kernel).get("switches", 0) + 1
        return soc["luxury"]["name"]
    return None


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def craft(kernel: Any, planet: Any) -> int:
    """A provided-for world turns part of its abundance into its signature luxury - while it sells."""
    if planet.population <= 0 or getattr(planet, "natives", None) or not provided_for(kernel, planet):
        return 0
    reconsider(kernel, planet)
    sig = signature(kernel, planet)
    if sig is None:
        return 0
    wanted = orders(kernel, planet, sig["type"])
    if wanted <= 0:
        return 0                     # nothing on order: the workshops rest
    from xylarium.kernel.fertility import tax_factor
    tier = max(1, planet.citadel_level)
    units = min(wanted, int(planet.population / 1000.0 * LUXURY_CRAFT_PER_THOUSAND * tier * tax_factor(planet)))
    comm = sig["input"]
    units = min(units, max(0, held(planet, comm) - _reserve(kernel, planet, comm)))
    if units <= 0:
        return 0
    _take(planet, comm, units, "luxury_craft")
    t = sig["type"]
    planet.element_reserves[t] = planet.element_reserves.get(t, 0) + units
    matter.source("luxury_craft", t, units)
    st = stats(kernel)
    st["crafted"][t] = st["crafted"].get(t, 0) + units
    # Crafted goods are real output (the Y of M V = P Y), at base price and the region's price level
    from xylarium.kernel import ledger
    if ledger.ACTIVE_POLICY is not None:
        ledger.ACTIVE_POLICY.record_output(planet.currency, units * COMMODITY_CONFIG[t]["base_price"]
                                           * PRICE_LEVEL.get(planet.currency, 1.0))
    return units


# ---------------------------------------------------------------------- households
def shop(kernel: Any, planet: Any, ports: List[Any]) -> None:
    """After the basket: households use their own signature and buy the luxuries they cannot make."""
    from xylarium.kernel.economy import EconomyManager
    from xylarium.kernel.fertility import luxury_factor
    from xylarium.kernel import fx
    st = stats(kernel)
    soc = planet.society
    comfort = float(soc.get("basket_fill", 0.0))
    if comfort < 0.5 or planet.population <= 0:
        soc["lux_access"] = round(0.5 * float(soc.get("lux_access", 0.0)), 3)
        return
    sig = signature(kernel, planet)
    own = sig["type"] if sig else None
    budget = int(planet.household_purse * LUXURY_PURSE_SHARE)
    want_total = met_total = 0
    unmet = planet.society.setdefault("luxury_unmet_quarters", {})
    for t in LUXURY_TYPES:
        scarcity = 0.5 if t == own else 1.0                  # nobody craves what they make
        want = int(planet.population / 1000.0 * LUXURY_WANT_PER_THOUSAND * comfort * scarcity * luxury_factor(planet))
        if want <= 0:
            unmet[t] = 0
            continue
        want_total += want
        if t == own:
            use = min(want, planet.element_reserves.get(t, 0))
            if use > 0:
                planet.element_reserves[t] -= use
                matter.sink("households_luxury", t, use)
                st["own_use"] += use
                met_total += use
            if use < want:
                unmet[t] = unmet.get(t, 0) + 1
            else:
                unmet[t] = 0
            continue
        need = want
        for port in sorted(ports, key=lambda p: -p.stock.get(t, 0)):
            if need <= 0 or budget <= 0:
                break
            have = port.stock.get(t, 0)
            if have <= 0:
                continue
            _, full_price = EconomyManager.get_unit_prices(port, t)
            if full_price <= 0:
                continue
            price = min(full_price, int(round(COMMODITY_CONFIG[t]["base_price"] * 1.25 * PRICE_LEVEL.get(port.currency, 1.0))))
            units = min(need, have, budget // max(1, price))
            if units <= 0:
                continue
            bill = units * price
            planet.household_purse -= bill
            port.treasury += bill
            port.stock[t] = have - units
            record_sale(port, t, units)
            matter.sink("households_luxury", t, units)
            port.regional_income = round(port.regional_income + 0.3 * bill, 2)
            budget -= bill
            need -= units
            met_total += units
            st["bought"][t] = st["bought"].get(t, 0) + units
            st["spend"][planet.currency] = st["spend"].get(planet.currency, 0) + bill
            st["spend_sol"] += fx.ACTIVE_FX.to_sol_value(planet.currency, bill) if (
                fx.ACTIVE_FX is not None and planet.currency != "SOL") else bill
        if need > 0 and budget > 0:
            from xylarium.kernel import demography
            ext_ports = [kernel.sectors[sid].port for sid in demography._reach(kernel, planet.sector_id, 5)
                         if kernel.sectors[sid].port is not None and kernel.sectors[sid].port.currency == planet.currency
                         and kernel.sectors[sid].port not in ports]
            for port in sorted(ext_ports, key=lambda p: -p.stock.get(t, 0)):
                if need <= 0 or budget <= 0:
                    break
                have = port.stock.get(t, 0)
                if have <= 0:
                    continue
                _, full_price = EconomyManager.get_unit_prices(port, t)
                if full_price <= 0:
                    continue
                price = min(full_price, int(round(COMMODITY_CONFIG[t]["base_price"] * 1.5 * PRICE_LEVEL.get(port.currency, 1.0))))
                units = min(need, have, budget // max(1, price))
                if units <= 0:
                    continue
                bill = units * price
                planet.household_purse -= bill
                port.treasury += bill
                port.stock[t] = have - units
                record_sale(port, t, units)
                matter.sink("households_luxury", t, units)
                port.regional_income = round(port.regional_income + 0.3 * bill, 2)
                budget -= bill
                need -= units
                met_total += units
                st["bought"][t] = st["bought"].get(t, 0) + units
                st["spend"][planet.currency] = st["spend"].get(planet.currency, 0) + bill
                st["spend_sol"] += fx.ACTIVE_FX.to_sol_value(planet.currency, bill) if (
                    fx.ACTIVE_FX is not None and planet.currency != "SOL") else bill
        if need > 0:
            unmet[t] = unmet.get(t, 0) + 1
        else:
            unmet[t] = 0
    st["want"] += want_total
    st["met"] += met_total
    access = met_total / want_total if want_total else 0.0
    soc["lux_access"] = round(0.5 * float(soc.get("lux_access", 0.0)) + 0.5 * access, 3)
    if access >= 0.5:
        planet.morale = min(100, planet.morale + 1)


# ---------------------------------------------------------------------- dynamic council bidding
def council_bid_multiplier(port: Any, t: str, kernel: Any = None) -> float:
    """When a luxury want remains unsatisfied for >= 3 consecutive quarters, the planetary council
    increases purchase price premium logarithmically, creating margin spreads that divert free AI traders
    toward luxury fulfillment."""
    if kernel is None:
        from xylarium.kernel import ledger
        kernel = ledger.active_kernel()
    if kernel is None:
        return 1.0
    max_unmet = 0
    sec = kernel.sectors.get(port.sector_id)
    if sec:
        for p in sec.planets:
            if p.population > 0 and not getattr(p, "natives", None):
                u = (p.society.get("luxury_unmet_quarters") or {}).get(t, 0)
                if u > max_unmet:
                    max_unmet = u
    # Check nearby planets in regional catchment (within 3 warps)
    for sid in getattr(kernel.sectors.get(port.sector_id), "warps", []):
        s = kernel.sectors.get(sid)
        if s:
            for p in s.planets:
                if p.population > 0 and not getattr(p, "natives", None):
                    u = (p.society.get("luxury_unmet_quarters") or {}).get(t, 0)
                    if u > max_unmet:
                        max_unmet = u
    if max_unmet < 3:
        return 1.0
    return min(3.0, 1.0 + math.log(1.0 + (max_unmet - 2) * 0.8))


# ---------------------------------------------------------------------- the quarter
def _catchments(kernel: Any) -> None:
    """Each port's households' wants for each luxury (full wants: they buy what they don't make)."""
    from xylarium.kernel import demography
    want: Dict[int, Dict[str, int]] = {}
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population <= 0 or getattr(p, "natives", None):
                continue
            comfort = float(p.society.get("basket_fill", 0.0))
            n = int(p.population / 1000.0 * LUXURY_WANT_PER_THOUSAND * comfort)
            if n <= 0:
                continue
            markets = demography._markets(kernel, p)
            if not markets:
                continue
            share = max(1, int(math.ceil(n / len(markets))))
            for port in markets:
                w = want.setdefault(port.sector_id, {})
                for t in LUXURY_TYPES:
                    w[t] = w.get(t, 0) + share
    for sec in kernel.sectors.values():
        if sec.port is not None:
            sec.port.leisure["lux_catchment"] = want.get(sec.id, {})


def quarter(kernel: Any) -> List[str]:
    """Crafting on every provided-for world, and perishable ephemera spoil wherever they are stored."""
    st = stats(kernel)
    _catchments(kernel)
    # 1. On planets:
    for sec in kernel.sectors.values():
        for planet in sec.planets:
            craft(kernel, planet)
            have = planet.element_reserves.get("LUX_EPHEMERA", 0)
            rot = int(have * EPHEMERA_SPOILAGE)
            if rot > 0:
                planet.element_reserves["LUX_EPHEMERA"] = have - rot
                matter.sink("spoiled", "LUX_EPHEMERA", rot)
                st["spoiled"] += rot
        # 2. In ports:
        port = sec.port
        if port is not None:
            _close_sales(port)
            have = port.stock.get("LUX_EPHEMERA", 0)
            has_market = bool((port.leisure.get("lux_catchment") or {}).get("LUX_EPHEMERA", 0))
            spoil_rate = EPHEMERA_SPOILAGE if has_market else min(0.10, EPHEMERA_SPOILAGE * 2)
            rot = int(have * spoil_rate)
            if rot > 0:
                port.stock["LUX_EPHEMERA"] = have - rot
                matter.sink("spoiled", "LUX_EPHEMERA", rot)
                st["spoiled"] += rot
    # 3. In transit (ships):
    for captain in kernel.captains.values():
        ship = getattr(captain, "ship", None)
        if ship is None or not getattr(ship, "cargo", None):
            continue
        have = ship.cargo.elements.get("LUX_EPHEMERA", 0)
        if have <= 0:
            continue
        has_cryo = (
            getattr(ship, "has_cryo_containment", False)
            or getattr(ship, "stasis_pod", False)
            or getattr(ship, "hull_class", "") == "CRYO_TANKER"
            or getattr(ship, "ship_type", "") == "CRYO_TANKER"
        )
        mult = 0.20 if has_cryo else 1.0
        rot = int(have * EPHEMERA_SPOILAGE * mult)
        if rot > 0:
            ship.cargo.elements["LUX_EPHEMERA"] = have - rot
            matter.sink("spoiled", "LUX_EPHEMERA", rot)
            st["spoiled"] += rot
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    sigs: Dict[str, int] = {}
    examples: List[str] = []
    for sec in kernel.sectors.values():
        for p in sec.planets:
            lx = p.society.get("luxury") if p.population > 0 else None
            if lx:
                sigs[lx["type"]] = sigs.get(lx["type"], 0) + 1
                if len(examples) < 4:
                    examples.append(f"{lx['name']} ({lx['type'][4:].lower()}, {p.name})")
    return {**st, "signatures": sigs, "examples": examples,
            "access": round(st["met"] / st["want"], 3) if st["want"] else 0.0}
