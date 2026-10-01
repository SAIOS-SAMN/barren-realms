"""
Xylarium staples: what each people eats, and where its food is kept.

Every metabolism has its staple (config STAPLES): carbon life eats organics, lithotrophs graze ore from the crust,
Stillcold life drinks ice, plasmic life feeds on hydrogen. Food is counted in energy-equivalent units, so a thousand
people need FOOD_PER_THOUSAND units of their own staple a cycle whatever they are, and every harvest is valued as
food at the price of organics in real output (the Y of M V = P Y).

A world's staple is kept where that commodity already lives: organics in the granary (organics_silo), ore in the
ore silo, ice and hydrogen among its element reserves. A lithic people's granary is its ore silo, so its works and
its meals draw on the same pile; a plasmic world's food is the hydrogen a refuelling captain would buy.

Everything in the census stays in the census: harvests and meals are declared (matter.produce / consume), a
lithotroph's harvest is a transfer out of the crust (geology.mine_crust), and moving food between holders (raids,
relief, kits) is a transfer with nothing declared.
"""

from typing import Any, Optional

from xylarium.config import COMMODITY_CONFIG, STAPLES
from xylarium.kernel import matter

FOOD_UNIT_VALUE = COMMODITY_CONFIG["ORGANICS"]["base_price"]      # one food unit, in real output


def of_metabolism(metabolism: Optional[str]) -> str:
    return STAPLES.get(metabolism or "biotic", "ORGANICS")


def of(kernel: Any, planet: Any) -> str:
    """The staple of the people who live on (or govern) this world."""
    from xylarium.kernel import biosphere
    return of_metabolism(biosphere.metabolism_of(kernel, planet))


def held(planet: Any, comm: str) -> int:
    if comm == "ORGANICS":
        return int(planet.organics_silo or 0)
    if comm == "ORE":
        return int(planet.ore_silo or 0)
    return int(planet.element_reserves.get(comm, 0) or 0)


def stores(kernel: Any, planet: Any) -> int:
    return held(planet, of(kernel, planet))


def move(planet: Any, comm: str, n: int) -> None:
    """Change a world's holding by n - a transfer leg: the caller moves the units to or from another holder."""
    if comm == "ORGANICS":
        planet.organics_silo += n
    elif comm == "ORE":
        planet.ore_silo += n
    else:
        planet.element_reserves[comm] = planet.element_reserves.get(comm, 0) + n
        if planet.element_reserves[comm] <= 0:
            planet.element_reserves.pop(comm, None)


def add(planet: Any, comm: str, n: int, kind: str) -> int:
    """Produce n units into the holding (declared)."""
    if n <= 0:
        return 0
    if comm == "ORGANICS":
        return matter.produce(planet, "organics_silo", "ORGANICS", n, kind)
    if comm == "ORE":
        return matter.produce(planet, "ore_silo", "ORE", n, kind)
    move(planet, comm, n)
    matter.source(kind, comm, n)
    return n


def take(planet: Any, comm: str, n: int, kind: str) -> int:
    """Consume up to n units from the holding (declared); returns what was there to take."""
    n = min(max(0, n), held(planet, comm))
    if n <= 0:
        return 0
    if comm == "ORGANICS":
        return matter.consume(planet, "organics_silo", "ORGANICS", n, kind)
    if comm == "ORE":
        return matter.consume(planet, "ore_silo", "ORE", n, kind)
    move(planet, comm, -n)
    matter.sink(kind, comm, n)
    return n


def eat(kernel: Any, planet: Any, n: int) -> int:
    eaten = take(planet, of(kernel, planet), n, "eaten")
    from xylarium.kernel import biosphere
    excrete(planet, biosphere.metabolism_of(kernel, planet), eaten)
    return eaten


def excrete(planet: Any, metabolism: str, eaten: int) -> int:
    """What an eater gives back of what it ate - its chemistry's waste, into the world's stores (a declared
    conversion: the meal was a sink, the waste is a source), where any people whose staple it is can eat it."""
    from xylarium.config import METABOLIC_WASTE, WASTE_SHARE
    waste = METABOLIC_WASTE.get(metabolism)
    if not waste or eaten <= 0:
        return 0
    a, _, b = WASTE_SHARE.partition("/")
    carry = float(planet.society.get("waste_carry", 0.0)) + eaten * float(a) / float(b or 1)
    n = int(carry)
    planet.society["waste_carry"] = round(carry - n, 6)
    return add(planet, waste, n, "respiration") if n > 0 else 0


def harvest(kernel: Any, planet: Any, n: int) -> int:
    """The land's yield of the people's staple. Lithotrophs graze the crust (a transfer out of the ground);
    every other harvest is grown, condensed or skimmed from the world (declared)."""
    comm = of(kernel, planet)
    if n <= 0:
        return 0
    if comm == "ORE":
        from xylarium.kernel import geology
        return geology.mine_crust(planet, n)
    return add(planet, comm, n, "harvest")


def reserve(kernel: Any, planet: Any, comm: str) -> int:
    """What a world keeps of a commodity for itself: two seasons of its people's food if it is their staple,
    its works' ore, a reserve of every element."""
    from xylarium.kernel import biosphere
    from xylarium.kernel.demography import ELEMENT_RESERVE_KEPT, _quarter_len
    keep = 0
    if comm == of(kernel, planet):
        keep = 2 * _quarter_len() * biosphere.consumption(planet)
    if comm == "ORE":
        return max(keep, 600)
    if comm == "ORGANICS":
        return keep
    return max(keep, ELEMENT_RESERVE_KEPT)


def surplus(kernel: Any, planet: Any, comm: str) -> int:
    return max(0, held(planet, comm) - reserve(kernel, planet, comm))
