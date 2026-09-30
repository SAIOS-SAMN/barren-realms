"""
Xylarium propulsion: moving mass costs reaction mass.

  * Every hull has a drive bunker of hydrogen (sized to the hull), separate from its cargo holds.
  * A jump burns reaction mass in proportion to what is being moved - the hull and its cargo:
    burn = 1 + (hull holds + cargo carried) / BURN_MASS_PER_UNIT. A Bulk Goliath hauling ore burns far more
    than a Scout running light, so heavy bulk runs carry a real fuel cost.
  * The exhaust does not vanish: it drifts in the sector where it was burned (the sector's background gas),
    counted in the matter census, and mining lasers scoop it back up in null space.
  * Ships bunker at any starport that stocks hydrogen, paying the port in its own money (like crew wages).
  * With an empty bunker a ship can still jump - coasting on reserve cells - but the passage takes longer
    (extra turns). Nothing deadlocks; running dry is just slow and expensive in time.
"""

from typing import Any, Optional

from xylarium.config import SHIP_CATALOG

BURN_MASS_PER_UNIT = 50      # tonnes (holds + cargo units) moved one jump per unit of reaction mass
COAST_EXTRA_TURNS = 2        # the cost of a jump on reserve cells


def bunker_capacity(ship: Any) -> int:
    return int(SHIP_CATALOG.get(ship.ship_type, {}).get("holds", 30))


def burn_for(ship: Any) -> int:
    holds = SHIP_CATALOG.get(ship.ship_type, {}).get("holds", 30)
    cg = ship.cargo
    carried = cg.ore + cg.organics + cg.equipment + sum(cg.elements.values())
    return 1 + int((holds + carried) // BURN_MASS_PER_UNIT)


def jump(kernel: Any, captain: Any, origin: Any) -> int:
    """Burns reaction mass for a jump out of ``origin``. Returns the extra turns (0, or coasting)."""
    ship = captain.ship
    need = burn_for(ship)
    if getattr(ship, "fuel", 0) >= need:
        ship.fuel -= need
        origin.gas = getattr(origin, "gas", 0) + need
        _stats(kernel)["burned"] += need
        return 0
    if ship.fuel > 0:
        origin.gas = getattr(origin, "gas", 0) + ship.fuel
        _stats(kernel)["burned"] += ship.fuel
        ship.fuel = 0
    _stats(kernel)["coasted"] += 1
    return COAST_EXTRA_TURNS


def bunker(kernel: Any, captain: Any, sector: Any) -> int:
    """Top up the bunker from the port's hydrogen, paid for in SOL cleared into the port's money."""
    port = getattr(sector, "port", None)
    if port is None:
        return 0
    ship = captain.ship
    want = bunker_capacity(ship) - getattr(ship, "fuel", 0)
    have = port.stock.get("H", 0)
    if want <= 0 or have <= 0:
        return 0
    from xylarium.kernel.economy import EconomyManager
    from xylarium.kernel import fx
    _, price = EconomyManager.get_unit_prices(port, "H")
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
    port.stock["H"] = have - units
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
        s = kernel.propulsion_stats = {"burned": 0, "bunkered": 0, "coasted": 0}
    return s


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
