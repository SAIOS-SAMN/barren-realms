"""
Xylarium propulsion: moving mass costs reaction mass - and what a people burns is a choice with consequences.

  * Every hull has a drive bunker, separate from its cargo holds. A jump burns reaction mass in proportion to
    what is being moved - the hull and its cargo - divided by the drive's exhaust velocity:
    burn = ceil((1 + (hull holds + cargo) / BURN_MASS_PER_UNIT) / v_e).
  * Fuel cells (config FUEL_CELLS): hydrogen fusion torch (every hull's first drive), hydrocarbon cells,
    nuclear-thermal steam, helium-3 fusion, xenon ion (efficient but slow: an extra turn per jump), fission
    pulse, and the warp stabilizer (no reaction mass; the core wears out after core_life jumps and the hull falls
    back on its torch). Hydrogen exhaust drifts in the sector (the sector's gas, in the census); every other
    propellant is consumed (a declared sink).
  * Choosing a cell is algorithmic (choose_fuel), never hardcoded per species:
        score(f) = sqrt(v_e) x abundance(f)^r x tradition(f)^(1-r)
    abundance is each propellant's share of what lies in reach (starport stocks, the ground, gas-giant wells),
    tradition is what the people's biology has always burned (FUEL_TRADITION), and r - clear-sightedness - rises
    with alignment (the Light reads the galaxy as it is; the Dark keeps its ways) and with every lesson learned by
    coasting dry. A misaligned people keeps building oil engines on a water world: an evolutionary bottleneck
    that leaves it fuel-starved and DEGRADED, until the lessons turn it.
  * Hydrogen wells: every gas giant is one. A starport in a giant's system skims its atmosphere each season -
    SKIM_ENERGY_PER_SEASON lifts gas out of the giant's gravity well, so a lighter giant yields more - and a
    share of what comes up is helium-3 (config [17]).
  * Ships bunker at any starport that stocks their propellant, paying the port in its own money.
  * With an empty bunker a ship can still jump - coasting on reserve cells - but the passage takes longer.
  * Readiness: a world's defence grid runs on its people's chosen fuel. A world with too little of it in reach
    broadcasts a DEGRADED beacon and fights at reduced strength - degraded civilizations are easier to conquer.
"""

import math
from typing import Any, Dict, Optional

from xylarium.config import (
    DEFENSE_H_PER_FIGHTER,
    DEGRADED_READINESS,
    DRIVE_INSTALL_FEE,
    FUEL_CELLS,
    FUEL_REACH,
    FUEL_TRADITION,
    SHIP_CATALOG,
    SKIM_ENERGY_PER_SEASON,
    SKIM_HE3_SHARE,
)
from xylarium.kernel import hulls
from xylarium.kernel import matter, topology

BURN_MASS_PER_UNIT = 50      # tonnes (holds + cargo units) moved one jump per unit of reaction mass (torch)
COAST_EXTRA_TURNS = 2        # the cost of a jump on reserve cells
_LEGACY = {"HE3": "He-3", **{k.upper(): k for k in FUEL_CELLS}}


def drive_key(ship: Any) -> str:
    d = getattr(ship, "drive", "H") or "H"
    return _LEGACY.get(d, d)


def drive_of(ship: Any) -> dict:
    return FUEL_CELLS.get(drive_key(ship), FUEL_CELLS["H"])


def fuel_of(ship: Any) -> Optional[str]:
    """The commodity in this hull's drive bunker (None for a warp drive)."""
    k = drive_key(ship)
    return None if k == "WARP" else k


def bunker_capacity(ship: Any) -> int:
    d = drive_of(ship)
    if not d.get("v_e"):
        return 0
    cfg = hulls.spec(ship)
    if cfg.get("tank") is not None and cfg.get("designer"):
        return int(cfg["tank"])                              # a drawn design carries the tanks it was drawn with
    holds = int(cfg.get("holds", 30))
    return max(1, int(holds / max(1.0, d["v_e"])))          # same range per hold for every cell


def burn_for(ship: Any) -> int:
    cfg = hulls.spec(ship)
    hull = cfg.get("mass") if cfg.get("designer") else cfg.get("holds", 30)   # a drawn design's own mass
    cg = ship.cargo
    carried = cg.ore + cg.organics + cg.equipment + sum(cg.elements.values())
    mass = 1 + int((hull + carried) // BURN_MASS_PER_UNIT)
    v_e = drive_of(ship).get("v_e") or 1.0
    return max(1, math.ceil(mass / v_e))


def jump(kernel: Any, captain: Any, origin: Any) -> int:
    """Burns reaction mass (or core life) for a jump out of ``origin``. Returns the extra turns."""
    ship = captain.ship
    d = drive_of(ship)
    st = _stats(kernel)
    if not d.get("v_e"):                                       # warp: no reaction mass, the core wears
        ship.core_wear = getattr(ship, "core_wear", 0) + 1
        st["warp_jumps"] += 1
        if ship.core_wear >= d.get("core_life", 400):
            ship.drive, ship.core_wear, ship.fuel = "H", 0, 0   # burned out: back on the torch, bunker dry
            st["cores_burned_out"] += 1
        return 0
    fuel = fuel_of(ship)
    need = burn_for(ship)
    burn = min(need, getattr(ship, "fuel", 0))
    if burn > 0:
        ship.fuel -= burn
        if fuel == "H":
            origin.gas = getattr(origin, "gas", 0) + burn       # hydrogen exhaust drifts where it was burned
        else:
            matter.sink("propellant", fuel, burn)               # fused, fissioned, ionized or burned away
        st["burned"] += burn
        by = st["burned_by_fuel"]
        by[fuel] = by.get(fuel, 0) + burn
    extra = int(d.get("extra_turns", 0))
    if burn >= need:
        return extra
    st["coasted"] += 1
    lessons = captain.traits if isinstance(getattr(captain, "traits", None), dict) else None
    if lessons is not None:
        lessons["fuel_lessons"] = round(lessons.get("fuel_lessons", 0.0) + 0.02, 3)   # running dry teaches
    return COAST_EXTRA_TURNS + extra


def bunker(kernel: Any, captain: Any, sector: Any) -> int:
    """Top up the bunker from the port's stock of this drive's propellant, paid in SOL cleared into the port's money."""
    port = getattr(sector, "port", None)
    ship = captain.ship
    fuel = fuel_of(ship)
    if port is None or not fuel:
        return 0
    want = bunker_capacity(ship) - getattr(ship, "fuel", 0)
    have = port.stock.get(fuel, 0)
    if want <= 0 or have <= 0:
        return 0
    from xylarium.kernel.economy import EconomyManager
    from xylarium.kernel import fx
    _, price = EconomyManager.get_unit_prices(port, fuel)
    if price <= 0:
        return 0
    price_sol = fx.ACTIVE_FX.to_sol_value(port.currency, price) if (fx.ACTIVE_FX and port.currency != "SOL") else price
    affordable = int(max(0, captain.credits - 200) // max(1e-9, price_sol))
    units = min(want, have, affordable)
    if units <= 0:
        return 0
    cost_sol = max(1, int(round(units * price_sol)))
    captain.credits -= cost_sol
    kernel._stardock_revenue(sector, cost_sol)
    port.stock[fuel] = have - units
    ship.fuel = getattr(ship, "fuel", 0) + units
    _stats(kernel)["bunkered"] += units
    return units


def scoop(sector: Any, captain: Any, limit: int = 10) -> int:
    """Mining lasers in null space also gather drifting exhaust gas into the hold."""
    gas = getattr(sector, "gas", 0)
    if gas <= 0:
        return 0
    got = captain.ship.cargo.stow("H", min(gas, limit))
    sector.gas = gas - got
    return got


def _stats(kernel: Any) -> dict:
    s = getattr(kernel, "propulsion_stats", None)
    if s is None:
        s = kernel.propulsion_stats = {}
    for k in ("burned", "bunkered", "coasted", "warp_jumps", "cores_burned_out", "skimmed_h", "skimmed_he3",
              "degraded_worlds"):
        s.setdefault(k, 0)
    for k in ("burned_by_fuel", "refits", "civ_fuels"):
        s.setdefault(k, {})
    return s


# ---------------------------------------------------------------------- choosing a fuel cell
def _abundance(kernel: Any, sector_id: int) -> Dict[str, float]:
    """Each propellant's share of what lies in reach: starport stocks, what the ground holds, and gas-giant wells."""
    from xylarium.kernel import physics
    cache = getattr(kernel, "_fuel_abundance", None)
    season = kernel.cycle_count // 25
    if cache is None or cache.get("_season") != season:
        cache = kernel._fuel_abundance = {"_season": season}
    if sector_id in cache:
        return cache[sector_id]
    fuels = [f for f in FUEL_CELLS if f != "WARP"]
    have = {f: 0.0 for f in fuels}
    for sid in topology.reach(kernel, sector_id, FUEL_REACH):
        sec = kernel.sectors[sid]
        if sec.port is not None:
            for f in fuels:
                have[f] += sec.port.stock.get(f, 0)
        for p in sec.planets:
            for f in fuels:
                have[f] += p.element_deposits.get(f, 0) / 100.0 + p.element_reserves.get(f, 0)
            if physics.body(p).get("giant") or p.planet_type == "GAS_GIANT":
                lift = SKIM_ENERGY_PER_SEASON / max(1.0, float(physics.escape_energy(p)))
                have["H"] += 4 * lift
                have["He-3"] += 4 * lift / SKIM_HE3_SHARE
    total = sum(have.values()) or 1.0
    cache[sector_id] = {f: v / total for f, v in have.items()}
    return cache[sector_id]


def clear_sight(alignment: float, lessons: float = 0.0) -> float:
    """How far a mind reads the galaxy as it is rather than as its tradition says: the Light sees, the Dark keeps
    its ways, and hard lessons (coasting dry) open anyone's eyes."""
    return max(0.1, min(1.0, 0.5 + 0.5 * alignment + lessons))


def choose_fuel(kernel: Any, sector_id: int, metabolism: str, tier: int, alignment: float,
                lessons: float = 0.0) -> str:
    share = _abundance(kernel, sector_id)
    r = clear_sight(alignment, lessons)
    tradition = FUEL_TRADITION.get(metabolism, "H")
    best, best_s = "H", -1.0
    for f, cell in FUEL_CELLS.items():
        if f == "WARP" or cell["min_tier"] > tier:
            continue
        s = math.sqrt(cell["v_e"]) * (share.get(f, 0.0) + 1e-4) ** r * (1.0 if f == tradition else 0.2) ** (1 - r)
        if s > best_s:
            best, best_s = f, s
    return best


# ---------------------------------------------------------------------- drive refits
def can_refit(kernel: Any, captain: Any, sector: Any, drive: str) -> Optional[str]:
    """Why this hull cannot take this drive here (None if it can)."""
    d = FUEL_CELLS.get(_LEGACY.get(str(drive).upper(), drive))
    port = getattr(sector, "port", None)
    if d is None:
        return "Unknown drive (" + ", ".join(FUEL_CELLS) + ")."
    drive = _LEGACY.get(str(drive).upper(), drive)
    if drive_key(captain.ship) == drive:
        return "That drive is already installed."
    if port is None:
        return "Drives are installed at a starport's yard."
    if getattr(captain, "rank_tier", 1) < d["min_tier"]:
        return f"The {d['name']} needs rank tier {d['min_tier']}."
    part = d.get("part")
    if part and port.stock.get(part, 0) < 1:
        return f"{port.name} has no {part} in its warehouse."
    return None


def refit_cost_sol(kernel: Any, sector: Any, drive: str) -> int:
    from xylarium.kernel.economy import EconomyManager
    from xylarium.kernel import fx
    part = FUEL_CELLS[_LEGACY.get(str(drive).upper(), drive)].get("part")
    if not part:
        return DRIVE_INSTALL_FEE
    port = sector.port
    _, price = EconomyManager.get_unit_prices(port, part)
    price_sol = fx.ACTIVE_FX.to_sol_value(port.currency, price) if (fx.ACTIVE_FX and port.currency != "SOL") else price
    return int(price_sol) + DRIVE_INSTALL_FEE


def refit_drive(kernel: Any, captain: Any, sector: Any, drive: str) -> str:
    """Install a new drive: the part comes out of the yard's warehouse, the old bunker's fuel goes back into it."""
    drive = _LEGACY.get(str(drive).upper(), drive)
    why = can_refit(kernel, captain, sector, drive)
    if why:
        raise ValueError(why)
    cost = refit_cost_sol(kernel, sector, drive)
    if captain.credits < cost:
        raise ValueError(f"The refit costs {cost:,} Cr.")
    port, ship = sector.port, captain.ship
    old = fuel_of(ship)
    if old and ship.fuel > 0:
        port.stock[old] = port.stock.get(old, 0) + ship.fuel
    ship.fuel = 0
    part = FUEL_CELLS[drive].get("part")
    if part:
        port.stock[part] -= 1
        matter.sink("drive_install", part, 1)                 # the part is built into the hull
    captain.credits -= cost
    kernel._stardock_revenue(sector, cost)
    ship.drive, ship.core_wear = drive, 0
    refits = _stats(kernel)["refits"]
    refits[drive] = refits.get(drive, 0) + 1
    bunker(kernel, captain, sector)
    return f"{FUEL_CELLS[drive]['name']} installed at {port.name} for {cost:,} Cr."


def consider_refit(kernel: Any, captain: Any, sector: Any) -> Optional[str]:
    """A docked autonomous captain reckons its fuel cell (warp first if it can): it refits when the cell its
    reckoning prefers clearly beats the one it flies, and it can afford the work three times over."""
    if not captain.is_ai or captain.faction_id:
        return None
    from xylarium.kernel.cognition import temperament
    traits = temperament(captain, kernel)
    if kernel.cycle_count - int(traits.get("fuel_reckoned", -10 ** 9)) < 100:
        return None
    traits["fuel_reckoned"] = kernel.cycle_count
    tier = getattr(captain, "rank_tier", 1)
    if drive_key(captain.ship) == "WARP":
        return None
    if tier >= FUEL_CELLS["WARP"]["min_tier"] and can_refit(kernel, captain, sector, "WARP") is None \
            and captain.credits >= 3 * refit_cost_sol(kernel, sector, "WARP"):
        return refit_drive(kernel, captain, sector, "WARP")
    lessons = float(traits.get("fuel_lessons", 0.0))
    metab = getattr(captain, "metabolism", "biotic") or "biotic"
    want = choose_fuel(kernel, sector.id, metab, tier, captain.cosmic_alignment, lessons)
    if want == drive_key(captain.ship) or can_refit(kernel, captain, sector, want) is not None:
        return None
    if captain.credits < 3 * refit_cost_sol(kernel, sector, want):
        return None
    return refit_drive(kernel, captain, sector, want)


# ---------------------------------------------------------------------- hydrogen wells and readiness
def skim_wells(kernel: Any) -> None:
    """Each season, every starport in a gas giant's system skims its atmosphere (up to its warehouse room)."""
    from xylarium.kernel import physics
    st = _stats(kernel)
    for sec in kernel.sectors.values():
        port = sec.port
        if port is None:
            continue
        giants = [p for p in sec.planets if physics.body(p).get("giant") or p.planet_type == "GAS_GIANT"]
        if not giants:
            continue
        lift = sum(SKIM_ENERGY_PER_SEASON / max(1.0, float(physics.escape_energy(g))) for g in giants)
        he3 = int(lift) // SKIM_HE3_SHARE
        h = int(lift) - he3
        for comm, q in (("H", h), ("He-3", he3)):
            room = port.max_stock.get(comm, 800) - port.stock.get(comm, 0)
            q = min(q, max(0, room))
            if q > 0:
                port.stock[comm] = port.stock.get(comm, 0) + q
                matter.source("gas_giant_skim", comm, q)
                st["skimmed_h" if comm == "H" else "skimmed_he3"] += q


def world_fuel(kernel: Any, planet: Any) -> str:
    """The fuel a world's people build their engines and defence grid for, reckoned once a year."""
    soc = planet.society
    if soc.get("fuel") and kernel.cycle_count - soc.get("fuel_reckoned", -10 ** 9) < 100:
        return soc["fuel"]
    from xylarium.kernel import biosphere
    civ = getattr(planet, "civilization", None)
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    align = float(getattr(civ, "alignment", 0.0) or 0.0) if (civ is not None and owner is None) else \
        float(getattr(owner, "cosmic_alignment", 0.0) or 0.0)
    soc["fuel"] = choose_fuel(kernel, planet.sector_id, biosphere.metabolism_of(kernel, planet),
                              max(1, planet.citadel_level), align, float(soc.get("fuel_lessons", 0.0)))
    soc["fuel_reckoned"] = kernel.cycle_count
    return soc["fuel"]


def readiness(kernel: Any, planet: Any) -> float:
    """The world's fuel in reach (its reserve and its system's port) against what its defences burn."""
    fuel = world_fuel(kernel, planet)
    v_e = FUEL_CELLS.get(fuel, FUEL_CELLS["H"])["v_e"] or 1.0
    need = max(1, int(planet.fighters * DEFENSE_H_PER_FIGHTER / v_e))
    sec = kernel.sectors.get(planet.sector_id)
    port_f = sec.port.stock.get(fuel, 0) if (sec is not None and sec.port is not None) else 0
    return min(1.0, (planet.element_reserves.get(fuel, 0) + port_f) / need)


def quarter(kernel: Any) -> list:
    """Wells are skimmed; every governed world reads its readiness and raises or lowers its DEGRADED beacon."""
    logs = []
    skim_wells(kernel)
    st = _stats(kernel)
    degraded = 0
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population <= 0 or getattr(p, "natives", None) or (p.owner_id is None and p.civilization is None):
                continue
            r = readiness(kernel, p)
            was = bool(p.society.get("degraded"))
            now = r < DEGRADED_READINESS
            p.society["readiness"] = round(r, 3)
            if now:
                p.society["degraded"] = True
                p.society["fuel_lessons"] = round(p.society.get("fuel_lessons", 0.0) + 0.05, 3)   # scarcity teaches
                degraded += 1
            else:
                p.society.pop("degraded", None)
            if now and not was and getattr(kernel, "event_bus", None):
                kernel.event_bus.broadcast_radio(sender=p.name, channel="COMM-1", sector_id=p.sector_id,
                                                 text=f"DEGRADED BEACON: {p.name} cannot fuel its defences "
                                                      f"({p.society.get('fuel')}, readiness {r:.0%}).")
                logs.append(f"[DEGRADED] {p.name} raised a DEGRADED beacon (readiness {r:.0%}).")
    st["degraded_worlds"] = degraded
    fuels: Dict[str, int] = {}
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.society.get("fuel") and p.population > 0:
                fuels[p.society["fuel"]] = fuels.get(p.society["fuel"], 0) + 1
    st["civ_fuels"] = fuels
    return logs


# ---------------------------------------------------------------------- the yards: hulls are matter too
def hull_metal(ship_type: str, kernel: Any = None) -> tuple:
    """Iron and titanium in a hull (the same metal a wreck leaves as scrap). A drawn design carries its own bill
    of materials."""
    from xylarium.config import HULL_SCRAP_PER_1000_CR
    cfg = hulls.lookup(kernel, ship_type) or {}
    mats = cfg.get("materials")
    if mats:
        return max(1, int(mats.get("Fe", 0))), max(0, int(mats.get("Ti", 0)))
    value = cfg.get("price", 0)
    fe = max(2, int(value / 1000 * HULL_SCRAP_PER_1000_CR))
    return fe, max(1, fe // 2)


def refit(kernel: Any, yard_sector: Any, old_type: str, new_type: str) -> bool:
    """A hull upgrade: the old hull is melted down into the yard's warehouse, the new one is built from the
    yard's metal - titanium substituted by twice the iron when short. If even the iron runs out, the yard
    still delivers, as a heavier iron-frame build with less hold space. Returns True for an iron frame."""
    from xylarium.kernel import matter, topology
    port = getattr(yard_sector, "port", None)
    if port is None:
        return False
    from xylarium.kernel.economy import EconomyManager
    EconomyManager.ensure_port_inventory(port)
    fe_old, ti_old = hull_metal(old_type, kernel)
    port.stock["Fe"] = port.stock.get("Fe", 0) + fe_old
    port.stock["Ti"] = port.stock.get("Ti", 0) + ti_old
    matter.source("hull_meltdown", "Fe", fe_old)
    matter.source("hull_meltdown", "Ti", ti_old)
    fe_need, ti_need = hull_metal(new_type, kernel)
    ti_used = min(ti_need, port.stock.get("Ti", 0))
    fe_need += 2 * (ti_need - ti_used)                      # substitution: iron for the missing titanium
    fe_used = min(fe_need, port.stock.get("Fe", 0))
    port.stock["Ti"] = port.stock.get("Ti", 0) - ti_used
    port.stock["Fe"] = port.stock.get("Fe", 0) - fe_used
    matter.sink("shipbuilding", "Ti", ti_used)
    matter.sink("shipbuilding", "Fe", fe_used)
    si_need = int(((hulls.lookup(kernel, new_type) or {}).get("materials") or {}).get("Si", 0))
    si_used = min(si_need, port.stock.get("Si", 0))           # shields, reactors and lasers are silicon
    if si_used:
        port.stock["Si"] -= si_used
        matter.sink("shipbuilding", "Si", si_used)
    return fe_used < fe_need
