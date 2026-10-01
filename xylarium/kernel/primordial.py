"""
Xylarium primordial genesis: every people begins on the world it was born on.

The settled genesis opens on a galaxy already spacefaring - starports in most systems, AI houses with fleets, the
Imperium and the Choir enthroned, companies listed, realms drawn. The primordial genesis opens before all that:

  * every civilization lives on its homeworld (Sol's peoples included), at citadel 0 - no shipyards, no ships - and
    numbers what its world feeds before industry (its citadel-0 carrying capacity), not an arbitrary draw;
  * there are no starports, no companies, no great powers, no genesis realms, no autonomous captains;
  * the worlds, their stars, crusts and biospheres, the natives and the ruins of older peoples are as they are;
  * the money institutions exist (the Reserve, the federations' banks, the exchange) with their founding stakes.

Everything after is emergence: councils raise citadels when the room is worth it; a world with yards commissions a
ship when the trade it would carry is worth the hull, and founds the dock it needs; daughter worlds, realms, firms,
waystations and the charted universe follow (observation.py). The live runner measures when each first happens.
"""

from typing import Any


def is_primordial(kernel: Any) -> bool:
    return ((getattr(kernel, "state", None) or {}).get("genesis") or {}).get("mode") in ("primordial", "forager")


def settle(kernel: Any) -> None:
    """Unbuild the spacefaring galaxy before its money baseline is read: ports, companies, Sol's yards."""
    from xylarium.kernel import demography
    for sec in kernel.sectors.values():
        sec.port = None
        sec.captains = []
        for p in sec.planets:
            if p.population > 0 and not getattr(p, "natives", None):
                p.citadel_level = 0
                p.habitats = 0
                p.owner_id = None
                # an evolved people stands at what its world feeds before industry (its citadel-0 capacity)
                p.population = max(300, demography.housing_cap(p, kernel))
                p.shields = min(p.shields, 100)
                p.fighters = min(p.fighters, 10)
    _ordinary_sol(kernel)
    mm = kernel.market_manager
    mm.companies.clear()
    mm.contracts.clear()
    kernel.captains.clear()
    kernel.state["genesis"]["firsts"] = {}
    if kernel.state["genesis"].get("mode") == "forager":
        from xylarium.kernel import ways
        ways.forage(kernel)                            # and further back: foragers, before fields and states


def first(kernel: Any, what: str, who: str) -> None:
    """Record the first time something happens in a primordial universe (the baseline the user asked for)."""
    g = (getattr(kernel, "state", None) or {}).get("genesis")
    if not g or g.get("mode") not in ("primordial", "forager"):
        return
    firsts = g.setdefault("firsts", {})
    if what not in firsts:
        firsts[what] = {"cycle": kernel.cycle_count, "year": round(kernel.cycle_count / 100.0, 2), "who": who}


def _ordinary_sol(kernel: Any) -> None:
    """Terra is one homeworld among many - its vault, guns and garrison drawn as every founding people's are
    (universe.py's founding polities) - and Luna is a barren moon no one has settled yet."""
    import random
    from xylarium.config import PRICE_LEVEL
    sol = kernel.sectors.get(1)
    if sol is None:
        return
    rng = random.Random(kernel.seed * 977 + 1)
    for p in sol.planets:
        if p.id == "planet_1":
            p.treasury = int(rng.randint(200, 1200) * PRICE_LEVEL.get(p.currency, 1.0))
            p.shields, p.max_shields = rng.randint(50, 150), 150
            p.fighters = rng.randint(10, 40)
            p.garrison_troops = rng.randint(15, 40)
            p.ore_silo, p.organics_silo = rng.randint(20, 100), rng.randint(20, 100)
        elif p.population > 0:
            p.population, p.civilization, p.treasury = 0, None, 0
            p.shields = p.fighters = p.garrison_troops = 0
