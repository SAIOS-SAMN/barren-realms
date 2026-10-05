"""
Xylarium demand: what peoples, docks, resorts and yards consume - and how a want that cannot be met at home becomes
trade.

  DIET      life whose solvent is water keeps its cells by sodium: a body eats salt with its food, sodium's share of
            a diet's mass as Earth's peoples show it (~5 g a day in ~0.7 kg of dry food: NA_DIET, a data point, not a
            dial). A world takes it from its own salt beds first (supply.halite), then its stores, then its system's
            port (paid from its vault). What its people get over what they need is its salt share; health reads it
            as it reads food (lifespan.thr).
  LEISURE   a pleasure dome drinks water; one that goes dry wants it (tourism.py).
  DOCKS     a station's hull metal comes from the system's yards - or from metal brought to the world (tourism.py).
  FUEL      ships buy reaction mass at the ports; where a port holds none its landed cost prices it (supply.py).

WANTS. Whatever a world cannot get at home it wants: the want is written on the world (society["wants"]). Its port
brings it (carry): it buys from the good's landed source (supply.py), paying the source its price, the source's
carriers the haul and the lanes' keepers their tolls - the trade as a flow along the lanes, as mass tourism is - and
the world buys it off the shelf. Its provisioning office also posts an import order, escrowed from its vault, priced
at the landed cost and a ship's trip (market.generate_colony_imports): the captains' side of the same trade. A want
is answered when the goods land.
"""

from typing import Any, Dict, List, Optional

NA_DIET = 0.007                  # salt's share of a water-based diet's mass (Earth: ~5 g a day in ~0.7 kg dry food)
SODIUM_LIFE = ("biotic", "umbral")   # life whose solvent is water


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "demand")


def want(planet: Any, comm: str, n: int) -> None:
    """A world is short n units of a good it cannot get at home (the provisioning office will order it). A want is
    the standing shortfall - renewed, not piled up - and goods landed answer it."""
    if n <= 0:
        return
    w = planet.society.setdefault("wants", {})
    w[comm] = max(int(w.get(comm, 0)), int(n))


def wants(planet: Any) -> Dict[str, int]:
    return dict((getattr(planet, "society", None) or {}).get("wants") or {})


def answered(planet: Any, comm: str, n: int) -> None:
    """Goods landed at a world answer its want."""
    w = (getattr(planet, "society", None) or {}).get("wants")
    if not w or comm not in w:
        return
    w[comm] = max(0, int(w[comm]) - int(n))
    if not w[comm]:
        w.pop(comm)


def salt_share(planet: Any) -> float:
    """The share of its people's salt need a world met (1 where its people do not need it)."""
    return float((getattr(planet, "society", None) or {}).get("salt", 1.0))


def _buy_at_port(kernel: Any, planet: Any, comm: str, n: int) -> int:
    """A world buys a good from its system's port with its vault, at the port's own price."""
    from xylarium.kernel.economy import EconomyManager
    sec = kernel.sectors.get(planet.sector_id)
    port = getattr(sec, "port", None)
    if port is None or n <= 0 or not port.sells.get(comm) or port.stock.get(comm, 0) <= 0:
        return 0
    unit = EconomyManager.get_unit_prices(port, comm)[1]
    if unit <= 0:
        return 0
    fx = getattr(kernel, "fx_market", None)
    rate = 1.0
    if port.currency != planet.currency and fx is not None:
        rate = fx.rate(planet.currency) / max(1e-9, fx.rate(port.currency))
    q = min(n, port.stock.get(comm, 0), int(max(0, planet.treasury) / max(1e-9, unit * rate)))
    if q <= 0:
        return 0
    pay = int(q * unit * rate)
    planet.treasury -= pay
    from xylarium.kernel import exchanges
    got = exchanges.convert_at(kernel, planet.sector_id, planet.currency, port.currency, pay)
    port.treasury += got
    port.stock[comm] -= q
    planet.element_reserves[comm] = planet.element_reserves.get(comm, 0) + q
    answered(planet, comm, q)
    return q


def _to_sol(kernel: Any, cur: str, amount: float) -> float:
    fx = getattr(kernel, "fx_market", None)
    return amount if cur == "SOL" or fx is None else fx.to_sol_value(cur, amount)


def _pay(kernel: Any, src_cur: str, dst: Any, amount: int, at: Any = None) -> None:
    """Pay from one money to a holder in its own - converted at the payer's place (its exchange, if it keeps one)."""
    from xylarium.kernel import exchanges
    dst.treasury += exchanges.convert_at(kernel, at, src_cur, dst.currency, amount)


def _bring(kernel: Any, buyer: Any, sector: Any, comm: str, n: int, payer: Optional[str], to_shelf: bool) -> int:
    """Buy n units of a good from its landed source and bring them here: the source port is paid its price, its
    carriers the haul, the lanes' keepers their tolls - from the buyer's treasury, in its money through the exchanges.
    The goods land on the buyer's shelves (a port) or in its stores (a world). Returns the units brought."""
    from xylarium.kernel import supply, transit
    rec = supply.best(kernel, comm, sector.id)
    if rec is None or rec[1] == sector.id:
        return 0
    src = kernel.sectors.get(int(rec[1]))
    sp = getattr(src, "port", None)
    if sp is None or sp.stock.get(comm, 0) <= 0:
        return 0
    path = kernel.find_path(src.id, sector.id) or []
    hops = max(1, len(path) - 1)
    per = supply.per_hop(kernel, comm)
    unit = float(rec[2]) + hops * per                                     # the source's price and the haul, SOL
    tolls = sum(transit.flow_passage(kernel, payer, a, b) for a, b in zip(path, path[1:]))
    budget = _to_sol(kernel, buyer.currency, max(0, buyer.treasury))
    q = min(n, sp.stock[comm], int(max(0.0, budget - tolls) / max(1e-9, unit)))
    if q <= 0:
        return 0
    rate = 1.0 / max(1e-12, _to_sol(kernel, buyer.currency, 1.0))          # local per SOL
    paid = int(q * float(rec[2]) * rate) + int(q * hops * per * rate)
    buyer.treasury -= paid
    _pay(kernel, buyer.currency, sp, paid, sector.id)                     # the source sells; its carriers haul
    for a, b in zip(path, path[1:]):
        owed = transit.flow_passage(kernel, payer, a, b)
        if owed > 0:
            holder, toll, tithe = transit.charge_cr(kernel, a, b)
            local = int(owed * rate)
            buyer.treasury -= local
            transit.settle(kernel, holder, payer or f"port:{sector.id}", a, b, toll, tithe, paid=(local, buyer.currency))
    sp.stock[comm] -= q
    if to_shelf:
        buyer.stock[comm] = buyer.stock.get(comm, 0) + q
        buyer.sells[comm] = True
    else:
        buyer.element_reserves[comm] = buyer.element_reserves.get(comm, 0) + q
        answered(buyer, comm, q)
    st = stats(kernel)
    st["carried"][comm] = st["carried"].get(comm, 0) + q
    return q


def carry(kernel: Any, sector: Any) -> int:
    """What a system's worlds want and cannot get at home is brought: by its port, to its shelves (the worlds buy it
    there); where the system has no port, by each world's own provisioning office, to its stores."""
    from xylarium.kernel import sustenance
    moved = 0
    port = sector.port
    if port is None:
        for w in sector.planets:
            for comm, n in sorted(wants(w).items()):
                moved += _bring(kernel, w, sector, comm, n, sustenance.people_of(w), to_shelf=False)
        return moved
    want_by: Dict[str, int] = {}
    payer = None
    for w in sector.planets:
        for comm, n in wants(w).items():
            want_by[comm] = want_by.get(comm, 0) + n
        payer = payer or (sustenance.people_of(w) if w.population > 0 else None)
    for comm, n in sorted(want_by.items()):
        short = n - port.stock.get(comm, 0)
        if short > 0:
            moved += _bring(kernel, port, sector, comm, short, payer, to_shelf=True)
    for w in sector.planets:                         # what its port could not afford, a world's own office brings
        for comm, n in sorted(wants(w).items()):
            if port.stock.get(comm, 0) <= 0:
                moved += _bring(kernel, w, sector, comm, n, sustenance.people_of(w), to_shelf=False)
    return moved


def diet(kernel: Any, planet: Any) -> float:
    """A quarter's salt for a water-life world: its own beds, its stores, its port - the rest wanted. Returns the share
    of the need met."""
    from xylarium.kernel import biosphere, matter, supply
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    if planet.population <= 0 or biosphere.metabolism_of(kernel, planet) not in SODIUM_LIFE:
        planet.society.pop("salt", None)
        return 1.0
    per_q = biosphere.consumption(planet) * FISCAL_QUARTER_CYCLES * NA_DIET
    carry = float(planet.society.get("salt_carry", 0.0)) + per_q
    need = int(carry)
    planet.society["salt_carry"] = round(carry - need, 6)
    keep = max(1, int(2 * per_q + 0.999))                              # two seasons in store, as its staple is kept
    have = int(planet.element_reserves.get("NaCl", 0))
    if have < need + keep:
        dug = supply._dig(kernel, planet, "NaCl", need + keep - have)    # its own beds
        planet.element_reserves["NaCl"] = have + dug
    have = int(planet.element_reserves.get("NaCl", 0))
    if have < need + keep:
        _buy_at_port(kernel, planet, "NaCl", need + keep - have)
    have = int(planet.element_reserves.get("NaCl", 0))
    if have - need < keep:
        want(planet, "NaCl", keep - max(0, have - need))
    if need <= 0:
        return salt_share(planet)
    eaten = min(need, have)
    if eaten:
        planet.element_reserves["NaCl"] = have - eaten
        if not planet.element_reserves["NaCl"]:
            planet.element_reserves.pop("NaCl")
        matter.sink("eaten", "NaCl", eaten)
    met = eaten / need
    share = 0.75 * salt_share(planet) + 0.25 * met                       # a year's memory, a season at a time
    planet.society["salt"] = round(share, 4)
    st = stats(kernel)
    st["salt_need"] += need
    st["salt_eaten"] += eaten
    return met


def season(kernel: Any) -> List[str]:
    """Every quarter: each water-life world eats its salt; then each port brings what its worlds want and lack."""
    worlds = [w for s in kernel.sectors.values() for w in s.planets if w.population > 0]
    for w in worlds:
        diet(kernel, w)
    for sec in kernel.sectors.values():
        if any(wants(w) for w in sec.planets):
            carry(kernel, sec)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    short = 0
    if hasattr(kernel, "sectors"):
        short = sum(1 for s in kernel.sectors.values() for w in s.planets
                    if w.population > 0 and salt_share(w) < 0.99)
    return {"salt_need": st["salt_need"], "salt_eaten": st["salt_eaten"], "worlds_short_of_salt": short,
            "carried": dict(st.get("carried", {}))}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="demand",
    state=lambda: {"salt_need": 0, "salt_eaten": 0, "carried": {}},
    season=season,
    summary=summary,
))
