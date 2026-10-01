"""
Xylarium nurseries: the technological leaps that carry a people past its own biology, and the biology that holds
a fast breeder back.

Every reproductive strategy (fertility.py) has a ceiling its biology sets: a K people's transition under comfort,
a lithic people's metal and tectonic heat, a Stillcold people's light, a plasmic people's star. Each can build one
district that lifts it (config NURSERIES) - artificial wombs, a foundry nursery, a deep-cold vault, a confinement
ring - but only while it is fed: a nursery buys its inputs every quarter from the world's own stocks or its
contractor port, and a quarter without them leaves it dark and its brood lost. High-tech fertility is only as
sound as the supply chain behind it.

r-strategists need no help to breed; their ceiling is disease. Density sets a pathogen's reproduction number, and
past the threshold a blight takes off (sanitation works lower it).

Settlement is earned the same way: a people sends settler fleets only after sustaining fertility above
replacement (VIABILITY_*), and each fleet carries its clade's seeding kit (SEED_KIT).

Money moves from the world's treasury to the port that sells it the inputs; matter is consumed with a declared
sink, or moved (seeding kits) from one holding to another.
"""

import math
import random
import zlib
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import (
    BLIGHT_DENSITY,
    BLIGHT_FATALITY,
    HABITAT_COST,
    HABITAT_ORE,
    NURSERIES,
    NURSERY_CITADEL_TIER,
    NURSERY_CIV_TECH,
    PRICE_LEVEL,
    SEED_KIT,
    VIABILITY_FERTILITY,
    VIABILITY_QUARTERS,
)
from xylarium.kernel import matter

TECH = "XENOGENESIS"


def _rng(*parts: Any) -> random.Random:
    return random.Random(zlib.crc32(":".join(str(p) for p in parts).encode()))


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "nursery")


# ---------------------------------------------------------------------- holdings and supply
def _held(planet: Any, comm: str) -> int:
    if comm == "ORGANICS":
        return planet.organics_silo
    if comm == "ORE":
        return planet.ore_silo
    return planet.element_reserves.get(comm, 0)


def _move(planet: Any, comm: str, n: int) -> None:
    """Change a world's holding by n (no declaration: the caller declares or the units go elsewhere)."""
    if comm == "ORGANICS":
        planet.organics_silo += n
    elif comm == "ORE":
        planet.ore_silo += n
    else:
        planet.element_reserves[comm] = planet.element_reserves.get(comm, 0) + n


def _resolve(kernel: Any, planet: Any, comm: str) -> str:
    if comm == "FUEL":
        from xylarium.kernel import propulsion
        return propulsion.world_fuel(kernel, planet)
    return comm


def supply(kernel: Any, planet: Any, inputs: List[Tuple[str, int]], need: float, kind: str,
           to: Any = None) -> float:
    """
    Draw ``need`` units of need from ``inputs`` (commodity, units per unit of need), in order: the world's own
    holdings beyond what it keeps for itself (two seasons' food, its works' ore, an element reserve - a nursery
    never eats the granary), then the contractor port's warehouse, paid from the treasury. Consumed (declared as
    ``kind``) unless ``to`` is given, in which case the units land in that world's holdings. Returns the need met.
    """
    from xylarium.kernel.colony import ColonyManager
    from xylarium.kernel.economy import EconomyManager
    from xylarium.kernel.staples import reserve
    left = float(need)
    port = ColonyManager._contractor_port(planet, kernel)
    for comm, per in inputs:
        if left <= 1e-9:
            break
        comm = _resolve(kernel, planet, comm)
        want = int(math.ceil(left * per))
        own = min(want, max(0, _held(planet, comm) - reserve(kernel, planet, comm)))
        if own > 0:
            _move(planet, comm, -own)
            if to is None:
                matter.sink(kind, comm, own)
            else:
                _move(to, comm, own)
            left -= own / per
            want -= own
        if want <= 0 or port is None or left <= 1e-9:
            continue
        have = port.stock.get(comm, 0)
        if have <= 0:
            continue
        _, price = EconomyManager.get_unit_prices(port, comm)
        if price <= 0:
            continue
        units = min(want, have, max(0, planet.treasury) // price)
        if units <= 0:
            continue
        planet.treasury -= units * price
        port.treasury += units * price
        port.stock[comm] = have - units
        if to is None:
            matter.sink(kind, comm, units)
        else:
            _move(to, comm, units)
        left -= units / per
    return max(0.0, float(need) - max(0.0, left))


# ---------------------------------------------------------------------- nurseries
def strategy(kernel: Any, planet: Any) -> str:
    from xylarium.kernel import fertility
    return fertility.strategy(kernel, planet)


def design(kernel: Any, planet: Any) -> Dict[str, Any]:
    return NURSERIES[strategy(kernel, planet)]


def has(planet: Any) -> bool:
    return bool(planet.society.get("nursery"))


def online(planet: Any) -> bool:
    n = planet.society.get("nursery")
    return bool(n) and bool(n.get("online"))


def why_not(kernel: Any, planet: Any) -> Optional[str]:
    """Why this world cannot build its nursery now (None: it can)."""
    if has(planet):
        return f"{planet.name} already has its {design(kernel, planet)['name']}."
    if planet.population <= 0:
        return f"{planet.name} has no people."
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    civ = getattr(planet, "civilization", None)
    knows = (planet.citadel_level >= NURSERY_CITADEL_TIER
             or (owner is not None and TECH in (getattr(owner, "technologies", None) or [])
                 and planet.citadel_level >= NURSERY_CITADEL_TIER - 1)
             or (owner is None and civ is not None and getattr(civ, "tech_level", 0) >= NURSERY_CIV_TECH))
    if not knows:
        return (f"a {design(kernel, planet)['name']} needs a Tier {NURSERY_CITADEL_TIER} citadel's engineering "
                f"(or Applied Xenogenesis and Tier {NURSERY_CITADEL_TIER - 1}).")
    if planet.treasury < cost(planet) or planet.ore_silo < HABITAT_ORE:
        return f"it costs {cost(planet):,} {planet.currency} and {HABITAT_ORE} ore."
    return None


def cost(planet: Any) -> int:
    return int(HABITAT_COST * PRICE_LEVEL.get(planet.currency, 1.0))


def build(kernel: Any, planet: Any) -> str:
    """Raise the world's nursery: a habitat's price to the contractor and a habitat's ore."""
    why = why_not(kernel, planet)
    if why is not None:
        raise ValueError(why)
    from xylarium.kernel.demography import _pay_contractor
    _pay_contractor(kernel, planet, cost(planet))
    matter.consume(planet, "ore_silo", "ORE", HABITAT_ORE, "construction")
    planet.society["nursery"] = {"kind": strategy(kernel, planet), "built": kernel.cycle_count, "online": True}
    stats(kernel)["built"] += 1
    return f"{planet.name} raised its {design(kernel, planet)['name']}."


def upkeep(kernel: Any, planet: Any) -> Optional[str]:
    """A quarter's inputs for the nursery; unfed it goes dark and its brood fails."""
    n = planet.society.get("nursery")
    if not n or planet.population <= 0:
        return None
    st = stats(kernel)
    d = NURSERIES.get(n.get("kind")) or design(kernel, planet)
    need = planet.population / 1000.0 * d["per_thousand"]
    got = supply(kernel, planet, d["inputs"], need, "nursery")
    if got + 1e-9 >= need:
        if not n.get("online"):
            st["relit"] += 1
        n["online"] = True
        return None
    was = n.get("online")
    n["online"] = False
    st["dark_quarters"] += 1
    if not was or n.get("kind") == "r":
        return None
    # the brood in the nursery is lost: a quarter's births at the people's biological rate
    from xylarium.kernel import biosphere
    rate = biosphere._profile(kernel, planet).get("birth_micro_per_cycle", 0) / 1_000_000.0
    lost = min(planet.population - 1, int(planet.population * rate * _quarter()))
    if lost > 0:
        planet.population -= lost
        st["brood_lost"] += lost
    return f"[NURSERY] {planet.name}'s {d['name']} went dark for want of supply: {lost:,} of its brood were lost."


def consider(kernel: Any, planet: Any) -> Optional[str]:
    """A council's choice: a people below replacement builds its nursery; an r people facing blight, its works."""
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    if owner is not None and not getattr(owner, "is_ai", False):
        return None                      # players build theirs by command
    if has(planet) or planet.population <= 0:
        return None
    strat = strategy(kernel, planet)
    if strat == "r":
        if r0(kernel, planet, ignore_works=True) <= 1.0:
            return None
    elif float(planet.society.get("fertility_parts", {}).get("unstressed", 1.0)) >= 1.0:
        return None
    from xylarium.config import DEMOGRAPHY_COUNCIL_RESERVE
    reserve = int(DEMOGRAPHY_COUNCIL_RESERVE * PRICE_LEVEL.get(planet.currency, 1.0))
    if why_not(kernel, planet) is not None or planet.treasury < cost(planet) + reserve:
        return None
    return f"[NURSERY] {build(kernel, planet)}"


# ---------------------------------------------------------------------- blight
def r0(kernel: Any, planet: Any, ignore_works: bool = False) -> float:
    from xylarium.kernel import demography
    k = max(1, demography.housing_cap(planet, kernel))
    r = (planet.population / k) / BLIGHT_DENSITY
    if not ignore_works and online(planet) and planet.society["nursery"].get("kind") == "r":
        r *= NURSERIES["r"]["r0"]
    return r


def final_size(r: float) -> float:
    """The share an epidemic infects: the root of z = 1 - exp(-R0 z) in (0, 1)."""
    if r <= 1.0:
        return 0.0
    z = 1.0 - 1.0 / r
    for _ in range(50):
        z = 1.0 - math.exp(-r * z)
    return z


def blight(kernel: Any, planet: Any) -> Optional[str]:
    """Once a quarter on an r world: a pathogen is introduced; past R0 = 1 it may take off."""
    r = r0(kernel, planet)
    if r <= 1.0:
        return None
    if _rng("blight", planet.id, kernel.cycle_count).random() >= 1.0 - 1.0 / r:
        return None
    from xylarium.kernel import fertility
    z = final_size(r)
    dead = min(planet.population - 1, int(planet.population * z * BLIGHT_FATALITY))
    rot = int(planet.organics_silo * z / 2)
    planet.population -= max(0, dead)
    matter.consume(planet, "organics_silo", "ORGANICS", rot, "blight")
    fertility.mark(planet, "blight", kernel.cycle_count)
    st = stats(kernel)
    st["blights"] += 1
    st["blight_dead"] += max(0, dead)
    return (f"[BLIGHT] A blight swept {planet.name} (R0 {r:.2f}, {z:.0%} infected): {dead:,} dead, "
            f"{rot:,} organics rotted.")


# ---------------------------------------------------------------------- viability and the seeding kit
def track_viability(planet: Any) -> None:
    soc = planet.society
    if float(soc.get("fertility", 0.0)) >= VIABILITY_FERTILITY:
        soc["viable_quarters"] = int(soc.get("viable_quarters", 0)) + 1
    else:
        soc["viable_quarters"] = 0


def viable(planet: Any) -> bool:
    return int(planet.society.get("viable_quarters", 0)) >= VIABILITY_QUARTERS


def kit_room(kernel: Any, planet: Any, metab: str, emigrants: int) -> int:
    """How many emigrants the clade's seeding kit can stock from the world's holdings and port (no purchase)."""
    inputs, per_thousand = SEED_KIT.get(metab, SEED_KIT["biotic"])
    from xylarium.kernel.colony import ColonyManager
    port = ColonyManager._contractor_port(planet, kernel)
    units = 0.0
    for comm, per in inputs:
        comm = _resolve(kernel, planet, comm)
        from xylarium.kernel.staples import reserve
        have = max(0, _held(planet, comm) - reserve(kernel, planet, comm)) + \
            (port.stock.get(comm, 0) if port is not None else 0)
        units += have / per
    return min(emigrants, int(units * 1000 / per_thousand))


def stock_kit(kernel: Any, planet: Any, daughter: Any, metab: str, emigrants: int) -> None:
    inputs, per_thousand = SEED_KIT.get(metab, SEED_KIT["biotic"])
    supply(kernel, planet, inputs, emigrants / 1000.0 * per_thousand, "seeding_kit", to=daughter)
    stats(kernel)["kits"] += 1


def summary(kernel: Any) -> Dict[str, Any]:
    st = dict(stats(kernel))
    by: Dict[str, Dict[str, int]] = {}
    for sec in kernel.sectors.values():
        for p in sec.planets:
            n = p.society.get("nursery") if p.population > 0 else None
            if n:
                b = by.setdefault(n.get("kind", "?"), {"worlds": 0, "online": 0})
                b["worlds"] += 1
                b["online"] += 1 if n.get("online") else 0
    st["nurseries"] = by
    return st


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="nursery",
    state=lambda: {"built": 0, "dark_quarters": 0, "relit": 0, "brood_lost": 0, "blights": 0, "blight_dead": 0,
                   "kits": 0, "gated": 0},
    summary=summary,
))
