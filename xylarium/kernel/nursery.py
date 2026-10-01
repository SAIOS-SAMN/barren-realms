"""
Xylarium nurseries: the technological leaps that carry a people past its own biology, and the biology that holds
a fast breeder back.

Every reproductive strategy (fertility.py) has a ceiling its biology sets: a K people's transition under comfort,
a lithic people's metal and tectonic heat, a Stillcold people's light, a plasmic people's star. Each can build one
district that lifts it (config NURSERIES) - artificial wombs, a foundry nursery, a deep-cold vault, a confinement
ring. Nothing gates it: how much it lifts is the people's mastery of the process (knowledge.py - artificial
gestation, foundry budding, deep refrigeration, magnetic confinement, sanitation), and its inputs fall along the
same learning curve. A council builds one when the decision rule finds it worth more than it costs - the people it
lets the world sustain (or the blight deaths it averts) at their tax value, over the council's horizon, against
its price and its upkeep. It works only while fed: a nursery buys its inputs every quarter from the world's own
stocks or its contractor port, and a quarter without them leaves it dark and its brood lost.

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
    COLONY_TAX_PER_CAPITA,
    COMMODITY_CONFIG,
    HABITAT_COST,
    HABITAT_ORE,
    NURSERIES,
    PRICE_LEVEL,
    SEED_KIT,
    VIABILITY_FERTILITY,
    VIABILITY_QUARTERS,
)
from xylarium.kernel import laws, matter


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


def process(kernel: Any, planet: Any, strat: Optional[str] = None) -> str:
    return f"nursery_{strat or strategy(kernel, planet)}"


def mastery(kernel: Any, planet: Any, strat: Optional[str] = None) -> float:
    """How much this people's nursery can lift its biology: its mastery of the process."""
    from xylarium.kernel import knowledge
    return knowledge.mastery(kernel, knowledge.holder_of_planet(planet), process(kernel, planet, strat))


def _multiplier(kernel: Any, planet: Any, strat: Optional[str] = None) -> float:
    from xylarium.kernel import knowledge
    return knowledge.cost_multiplier(kernel, knowledge.holder_of_planet(planet), process(kernel, planet, strat))


def why_not(kernel: Any, planet: Any) -> Optional[str]:
    """Why this world cannot build its nursery now (None: it can)."""
    if has(planet):
        return f"{planet.name} already has its {design(kernel, planet)['name']}."
    if planet.population <= 0:
        return f"{planet.name} has no people."
    if planet.treasury < cost(planet, kernel) or planet.ore_silo < HABITAT_ORE:
        return f"it costs {cost(planet, kernel):,} {planet.currency} and {HABITAT_ORE} ore."
    return None


def cost(planet: Any, kernel: Any = None) -> int:
    """A habitat's price, falling along the learning curve of the people's knowledge of the process."""
    mult = _multiplier(kernel, planet) if kernel is not None else 1.0
    return int(HABITAT_COST * PRICE_LEVEL.get(planet.currency, 1.0) * mult)


def build(kernel: Any, planet: Any) -> str:
    """Raise the world's nursery: a habitat's price to the contractor and a habitat's ore."""
    why = why_not(kernel, planet)
    if why is not None:
        raise ValueError(why)
    from xylarium.kernel.demography import _pay_contractor
    _pay_contractor(kernel, planet, cost(planet, kernel))
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
    need = planet.population / 1000.0 * d["per_thousand"] * _multiplier(kernel, planet, n.get("kind"))
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


def _tax_per_head_quarter(planet: Any) -> float:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return COLONY_TAX_PER_CAPITA * PRICE_LEVEL.get(planet.currency, 1.0) * FISCAL_QUARTER_CYCLES


def _upkeep_per_quarter(kernel: Any, planet: Any) -> float:
    d = design(kernel, planet)
    comm = _resolve(kernel, planet, d["inputs"][0][0])
    price = COMMODITY_CONFIG.get(comm, {}).get("base_price", 20) * PRICE_LEVEL.get(planet.currency, 1.0)
    return planet.population / 1000.0 * d["per_thousand"] * _multiplier(kernel, planet) * price


def gain(kernel: Any, planet: Any) -> float:
    """People a quarter the nursery is worth to this world, at its people's mastery: the extra people it lets the
    world sustain, or for an r people the expected blight deaths it averts."""
    from xylarium.kernel import demography, fertility
    strat = strategy(kernel, planet)
    soc = planet.society
    if strat == "r":
        r_now = r0(kernel, planet, ignore_works=True)
        r_with = r_now * (1.0 - mastery(kernel, planet, "r"))

        def deaths(r: float) -> float:
            return (1.0 - 1.0 / r) * final_size(r) * BLIGHT_FATALITY * planet.population if r > 1.0 else 0.0
        return deaths(r_now) - deaths(r_with)
    saved = soc.get("nursery")
    soc["nursery"] = {"kind": strat, "online": True}
    f_with, _ = fertility.fertility(kernel, planet)
    soc.pop("nursery")
    f_without, _ = fertility.fertility(kernel, planet)
    if saved is not None:
        soc["nursery"] = saved
    cap = demography.housing_cap(planet, kernel)
    return max(0.0, cap * (min(1.0, f_with) - min(1.0, f_without)))


def appraise(kernel: Any, planet: Any) -> Dict[str, float]:
    """What the nursery is worth to this world and what it costs, both in its money today."""
    from xylarium.kernel import decide
    m = decide.mind_of_planet(kernel, planet)
    worth = decide.worth(kernel, gain(kernel, planet) * _tax_per_head_quarter(planet), m, planet.currency)
    upkeep_pv = decide.worth(kernel, _upkeep_per_quarter(kernel, planet), m, planet.currency)
    return {"worth": worth, "cost": cost(planet, kernel) + upkeep_pv, "mind": m}


def consider(kernel: Any, planet: Any) -> Optional[str]:
    """A council's choice, by the one decision rule: build the nursery if it is worth more than it costs."""
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    if owner is not None and not getattr(owner, "is_ai", False):
        return None                      # players build theirs by command
    if has(planet) or planet.population <= 0 or why_not(kernel, planet) is not None:
        return None
    from xylarium.kernel import decide
    a = appraise(kernel, planet)
    pick = decide.choose(kernel, [decide.option("build_nursery", a["cost"], a["worth"])], a["mind"], planet.id)
    if pick is None:
        return None
    return f"[NURSERY] {build(kernel, planet)}"


# ---------------------------------------------------------------------- blight
def r0(kernel: Any, planet: Any, ignore_works: bool = False) -> float:
    from xylarium.kernel import demography
    k = max(1, demography.housing_cap(planet, kernel))
    r = (planet.population / k) / BLIGHT_DENSITY
    if not ignore_works and online(planet) and planet.society["nursery"].get("kind") == "r":
        r *= 1.0 - mastery(kernel, planet, "r")           # sanitation as good as the people's biology
    return r


def final_size(r: float) -> float:
    return laws.final_size(r)


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
