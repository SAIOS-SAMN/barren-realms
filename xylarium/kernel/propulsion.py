"""
Xylarium propulsion: moving mass costs reaction mass - until a people learns not to need it.

  * Every hull has a drive bunker, separate from its cargo holds. A jump burns reaction mass in proportion to
    what is being moved - the hull and its cargo: burn = 1 + (hull holds + cargo carried) / BURN_MASS_PER_UNIT.
  * The drive ladder (config DRIVES). Nobody sensible runs their fleets forever on a scarce fuel:
      - Hydrogen fusion torch (every hull's first drive): burns hydrogen; the exhaust drifts in the sector where
        it was burned (the sector's background gas, in the census), and mining lasers scoop it back up.
      - Helium-3 fusion drive (an M3 engine manifold, rank tier 2): a quarter of the reaction mass, burned as
        He-3; fusion consumes it (a declared sink).
      - Warp stabilizer drive (an M4 warp core, rank tier 3): no reaction mass at all; the core wears with every
        jump and burns out after DRIVES["WARP"]["core_life"] of them, when the hull falls back on its torch.
    Drives are installed at a yard that stocks the part; the old bunker's fuel is returned to the warehouse.
  * Hydrogen wells: every gas giant is one. A starport in a giant's system skims its atmosphere each season -
    SKIM_ENERGY_PER_SEASON lifts gas out of the giant's gravity well, so a lighter giant yields more - and a
    share of what comes up is helium-3 (config [17]).
  * Ships bunker at any starport that stocks their fuel, paying the port in its own money (like crew wages).
  * With an empty bunker a ship can still jump - coasting on reserve cells - but the passage takes longer.
  * Readiness: a world's defence grid and fighters run on fusion. A world with too little hydrogen in reach
    broadcasts a DEGRADED beacon and fights at reduced strength - degraded civilizations are easier to conquer.
"""

from typing import Any, Optional

from xylarium.config import (
    DEFENSE_H_PER_FIGHTER,
    DEGRADED_READINESS,
    DRIVE_INSTALL_FEE,
    DRIVES,
    SHIP_CATALOG,
    SKIM_ENERGY_PER_SEASON,
    SKIM_HE3_SHARE,
)
from xylarium.kernel import matter

BURN_MASS_PER_UNIT = 50      # tonnes (holds + cargo units) moved one jump per unit of reaction mass
COAST_EXTRA_TURNS = 2        # the cost of a jump on reserve cells


def drive_of(ship: Any) -> dict:
    return DRIVES.get(getattr(ship, "drive", "H") or "H", DRIVES["H"])


def fuel_of(ship: Any) -> Optional[str]:
    """The commodity in this hull's drive bunker (None for a warp drive)."""
    return drive_of(ship).get("fuel")


def bunker_capacity(ship: Any) -> int:
    d = drive_of(ship)
    if not d.get("fuel"):
        return 0
    return int(SHIP_CATALOG.get(ship.ship_type, {}).get("holds", 30)) // d.get("bunker_div", 1)


def burn_for(ship: Any) -> int:
    holds = SHIP_CATALOG.get(ship.ship_type, {}).get("holds", 30)
    cg = ship.cargo
    carried = cg.ore + cg.organics + cg.equipment + sum(cg.elements.values())
    mass = 1 + int((holds + carried) // BURN_MASS_PER_UNIT)
    div = drive_of(ship).get("burn_div", 1)
    return -(-mass // div)


def jump(kernel: Any, captain: Any, origin: Any) -> int:
    """Burns reaction mass (or core life) for a jump out of ``origin``. Returns the extra turns (0, or coasting)."""
    ship = captain.ship
    d = drive_of(ship)
    st = _stats(kernel)
    if not d.get("fuel"):                                      # warp: no reaction mass, the core wears
        ship.core_wear = getattr(ship, "core_wear", 0) + 1
        st["warp_jumps"] += 1
        if ship.core_wear >= d.get("core_life", 400):
            ship.drive, ship.core_wear, ship.fuel = "H", 0, 0   # burned out: back on the torch, bunker dry
            st["cores_burned_out"] += 1
        return 0
    fuel = d["fuel"]
    need = burn_for(ship)
    burn = min(need, getattr(ship, "fuel", 0))
    if burn > 0:
        ship.fuel -= burn
        if fuel == "H":
            origin.gas = getattr(origin, "gas", 0) + burn       # hydrogen exhaust drifts where it was burned
        else:
            matter.sink("fusion", fuel, burn)                   # He-3 fuses away
        st["burned"] += burn
        if fuel != "H":
            st["he3_burned"] += burn
    if burn >= need:
        return 0
    st["coasted"] += 1
    return COAST_EXTRA_TURNS


def bunker(kernel: Any, captain: Any, sector: Any) -> int:
    """Top up the bunker from the port's stock of this drive's fuel, paid in SOL cleared into the port's money."""
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
    for k in ("burned", "bunkered", "coasted", "he3_burned", "warp_jumps", "cores_burned_out", "skimmed_h",
              "skimmed_he3", "refits_he3", "refits_warp", "degraded_worlds"):
        s.setdefault(k, 0)
    return s


# ---------------------------------------------------------------------- drive refits
def can_refit(kernel: Any, captain: Any, sector: Any, drive: str) -> Optional[str]:
    """Why this hull cannot take this drive here (None if it can)."""
    d = DRIVES.get(drive)
    port = getattr(sector, "port", None)
    if d is None or "part" not in d:
        return "Unknown drive (HE3 or WARP)."
    if getattr(captain.ship, "drive", "H") == drive:
        return "That drive is already installed."
    if port is None:
        return "Drives are installed at a starport's yard."
    if getattr(captain, "rank_tier", 1) < d["min_tier"]:
        return f"The {d['name']} needs rank tier {d['min_tier']}."
    if port.stock.get(d["part"], 0) < 1:
        return f"{port.name} has no {d['part']} in its warehouse."
    return None


def refit_cost_sol(kernel: Any, sector: Any, drive: str) -> int:
    from xylarium.kernel.economy import EconomyManager
    from xylarium.kernel import fx
    port = sector.port
    _, price = EconomyManager.get_unit_prices(port, DRIVES[drive]["part"])
    price_sol = fx.ACTIVE_FX.to_sol_value(port.currency, price) if (fx.ACTIVE_FX and port.currency != "SOL") else price
    return int(price_sol) + DRIVE_INSTALL_FEE


def refit_drive(kernel: Any, captain: Any, sector: Any, drive: str) -> str:
    """Install a new drive: the part comes out of the yard's warehouse, the old bunker's fuel goes back into it."""
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
    part = DRIVES[drive]["part"]
    port.stock[part] -= 1
    matter.sink("drive_install", part, 1)                     # the part is built into the hull
    captain.credits -= cost
    kernel._stardock_revenue(sector, cost)
    ship.drive, ship.core_wear = drive, 0
    _stats(kernel)["refits_he3" if drive == "HE3" else "refits_warp"] += 1
    bunker(kernel, captain, sector)
    return f"{DRIVES[drive]['name']} installed at {port.name} for {cost:,} Cr."


def consider_refit(kernel: Any, captain: Any, sector: Any) -> Optional[str]:
    """A docked autonomous captain who can afford it moves up the drive ladder (warp first)."""
    if not captain.is_ai or captain.faction_id:
        return None
    for drive in ("WARP", "HE3"):
        if drive == "HE3" and getattr(captain.ship, "drive", "H") == "WARP":
            return None
        if can_refit(kernel, captain, sector, drive) is None:
            if captain.credits >= 3 * refit_cost_sol(kernel, sector, drive):
                return refit_drive(kernel, captain, sector, drive)
    return None


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


def readiness(kernel: Any, planet: Any) -> float:
    """Hydrogen in reach (the world's reserve and its system's port) against what its defences burn."""
    need = max(1, planet.fighters * DEFENSE_H_PER_FIGHTER)
    sec = kernel.sectors.get(planet.sector_id)
    port_h = sec.port.stock.get("H", 0) if (sec is not None and sec.port is not None) else 0
    return min(1.0, (planet.element_reserves.get("H", 0) + port_h) / need)


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
                degraded += 1
            else:
                p.society.pop("degraded", None)
            if now and not was and getattr(kernel, "event_bus", None):
                kernel.event_bus.broadcast_radio(sender=p.name, channel="COMM-1", sector_id=p.sector_id,
                                                 text=f"DEGRADED BEACON: {p.name} cannot fuel its defences "
                                                      f"(readiness {r:.0%}).")
                logs.append(f"[DEGRADED] {p.name} raised a DEGRADED beacon (readiness {r:.0%}).")
    st["degraded_worlds"] = degraded
    return logs


# ---------------------------------------------------------------------- the yards: hulls are matter too
def hull_metal(ship_type: str) -> tuple:
    """Iron and titanium in a hull (the same metal a wreck leaves as scrap)."""
    from xylarium.config import HULL_SCRAP_PER_1000_CR
    value = SHIP_CATALOG.get(ship_type, {}).get("price", 0)
    fe = max(2, int(value / 1000 * HULL_SCRAP_PER_1000_CR))
    return fe, max(1, fe // 2)


def refit(kernel: Any, yard_sector: Any, old_type: str, new_type: str) -> bool:
    """A hull upgrade: the old hull is melted down into the yard's warehouse, the new one is built from the
    yard's metal - titanium substituted by twice the iron when short. If even the iron runs out, the yard
    still delivers, as a heavier iron-frame build with less hold space. Returns True for an iron frame."""
    from xylarium.kernel import matter
    port = getattr(yard_sector, "port", None)
    if port is None:
        return False
    from xylarium.kernel.economy import EconomyManager
    EconomyManager.ensure_port_inventory(port)
    fe_old, ti_old = hull_metal(old_type)
    port.stock["Fe"] = port.stock.get("Fe", 0) + fe_old
    port.stock["Ti"] = port.stock.get("Ti", 0) + ti_old
    matter.source("hull_meltdown", "Fe", fe_old)
    matter.source("hull_meltdown", "Ti", ti_old)
    fe_need, ti_need = hull_metal(new_type)
    ti_used = min(ti_need, port.stock.get("Ti", 0))
    fe_need += 2 * (ti_need - ti_used)                      # substitution: iron for the missing titanium
    fe_used = min(fe_need, port.stock.get("Fe", 0))
    port.stock["Ti"] = port.stock.get("Ti", 0) - ti_used
    port.stock["Fe"] = port.stock.get("Fe", 0) - fe_used
    matter.sink("shipbuilding", "Ti", ti_used)
    matter.sink("shipbuilding", "Fe", fe_used)
    return fe_used < fe_need
