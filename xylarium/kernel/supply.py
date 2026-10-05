"""
Xylarium supply: what a system holds, what it lacks, and what it costs to bring - the economy read from the elements
the galaxy made.

Every element was spread by the galaxy that made it (cosmos.abundance: heavy elements stay near the core, light
ones reach furthest) and laid into worlds by their formation (creation.py). A port trades the elements and minerals
its system holds and buys what it lacks - nothing is chartered by lot.

  HELD      a world holds what lies in its deposits and its reserves - and, of salt, what its seas left (halite).
  CHARTER   a port SELLS a good its system holds, stocked as the system's holding stands against the galaxy's typical
            producer's (S / (S + S_typical)); it BUYS a good its system lacks, or that its peopled worlds use.
  LANDED    each year, from every port that holds a good, the cheapest delivery to every other port: the source's own
            price, plus the haul - per unit per hop, the larger of what its mass costs to move (a hop's burn for a
            hold full of ore, scaled by the good's atomic mass against ore's: heavy elements cost most to carry
            outward) and what its bulk costs (a hold of it holds fewer units). An importer prices the good at its
            landed cost, and its distance from the source is in that price; the Sol-centred gradient is not applied.
  EXOTIC    a good's exotic index at a port: what it costs landed there over what it costs where it is held. Nothing is
            declared exotic; the galaxy's distribution of the elements decides it.

SALT (halite). A world's crust holds chlorine as the Sun's abundances give it (5,240 atoms per million silicon -
Lodders 2003), scaled by its star's metals and chlorine's own spread through the galaxy (it is lighter than iron,
so it reaches further). What the world degassed went to its seas; where seas evaporate (their vapour pressure over
the air's weight) or have been lost altogether, the dissolved salt is laid down as halite - NaCl, sodium being ten
times as common as chlorine, so chlorine sets the amount. A world that never had liquid seas, an ice world and a
giant hold none.
"""

import heapq
from typing import Any, Dict, List, Optional, Tuple

TRIAD = ("ORE", "ORGANICS", "EQUIPMENT")                         # the tri-commodity ports keep their classes
PHYSICAL = ("METALS", "VOLATILES", "EXOTICS", "MINERALS")         # goods the galaxy's elements make
NACL_PER_CL = 58.44 / 35.45                                       # halite's mass per unit of chlorine in it


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "supply")


def goods() -> List[str]:
    from xylarium.config import COMMODITY_CONFIG
    return [c for c, cfg in COMMODITY_CONFIG.items() if cfg.get("category") in PHYSICAL and c not in TRIAD]


# ---------------------------------------------------------------------- salt
def _silicate_per_si() -> float:
    from xylarium.kernel import worlds as W
    a = W.ABUNDANCE
    return (24.3 * a["Mg"] + 28.1 * a["Si"] + 16.0 * 3 * a["Si"]) / a["Si"]


def chlorine_share() -> float:
    """Chlorine's mass share of a world's rock at the Sun's abundances."""
    from xylarium.kernel import worlds as W
    return W.ABUNDANCE["Cl"] / W.ABUNDANCE["Si"] * 35.45 / _silicate_per_si()


def halite(kernel: Any, planet: Any) -> int:
    """The salt a world's seas have laid down (units), from its physics: none on a world that never had seas."""
    from xylarium.kernel import cosmos, geology, worlds as W
    rock = geology.crust_capacity(planet)
    if rock <= 0:
        return 0
    try:
        st = W.state_of_planet(kernel, planet)
    except Exception:
        return 0
    w, args = st["world"], st["args"]
    if w.get("giant"):
        return 0
    z, r = float(args[6]), float(args[7])
    t, p = float(w.get("t_surf", 0.0)), max(1e-9, float(w.get("p_bar", 0.0)))
    seas = w.get("seas") or {}
    liquid = "H2O" in seas and W.phase("H2O", t, p) == "liquid"
    lost = "H2O" in (w.get("ices") or {}) and float(w.get("escaped", 0.0)) > 0.5 and not seas.get("H2O")
    if liquid:
        laid = min(1.0, W.saturation("H2O", t) / p)                # what evaporation leaves in its basins
    elif lost:
        laid = 1.0                                                   # seas gone: their salt is all salt flat
    else:
        return 0
    enrich = z / max(1e-9, cosmos.metals(r)) * cosmos.abundance("Cl", r)
    cl = rock * chlorine_share() * enrich * float(w.get("degassed", 0.0))
    return int(cl * NACL_PER_CL * laid)


# ---------------------------------------------------------------------- what a system holds
def held(kernel: Any, planet: Any, comm: str) -> int:
    got = int((planet.element_deposits or {}).get(comm, 0)) + int((planet.element_reserves or {}).get(comm, 0))
    if comm == "NaCl":
        got += max(0, _halite_cached(kernel, planet) - int(planet.society.get("halite_dug", 0) or 0))
    return max(0, got)


def _halite_cached(kernel: Any, planet: Any) -> int:
    from xylarium.kernel import worlds as W
    key = (round(W.world_age(kernel, planet), 2), planet.planet_type)
    rec = planet.society.get("_halite") if isinstance(getattr(planet, "society", None), dict) else None
    if rec and tuple(rec.get("key", ())) == key:
        return int(rec["n"])
    n = halite(kernel, planet)
    if isinstance(getattr(planet, "society", None), dict):
        planet.society["_halite"] = {"key": list(key), "n": n}
    return n


def system(kernel: Any, sector_id: int, comm: str) -> int:
    sec = kernel.sectors.get(sector_id)
    return sum(held(kernel, w, comm) for w in sec.planets) if sec is not None else 0


def typical(kernel: Any, comm: str) -> float:
    """The galaxy's typical producer of a good: the median holding of the systems that hold any."""
    from xylarium.kernel import cache

    def build() -> float:
        got = sorted(s for s in (system(kernel, sid, comm) for sid in kernel.sectors) if s > 0)
        return float(got[len(got) // 2]) if got else 0.0
    if not hasattr(kernel, "caches"):
        return build()
    return cache.memo(kernel, "supply_typical", comm, build, epoch=kernel.cycle_count // 400)


def charter(kernel: Any, port: Any, comm: str, max_s: int) -> Tuple[bool, bool, int]:
    """A port's charter for a good, from its system: (buys, sells, founding stock)."""
    s = system(kernel, port.sector_id, comm)
    sec = kernel.sectors.get(port.sector_id)
    peopled = sec is not None and any(w.population > 0 for w in sec.planets)
    sells = s > 0
    buys = not sells or peopled
    k = typical(kernel, comm)
    stock = int(max_s * s / (s + k)) if sells and s + k > 0 else 0
    return buys, sells, stock


# ---------------------------------------------------------------------- landed cost
def _hold(kernel: Any) -> float:
    """A typical ship's holds (the median of the captains' ships)."""
    caps = sorted(float(getattr(getattr(c.ship, "cargo", None), "capacity", 0) or 0)
                  for c in getattr(kernel, "captains", {}).values() if getattr(c, "ship", None) is not None)
    caps = [c for c in caps if c > 0]
    if caps:
        return caps[len(caps) // 2]
    from xylarium.config import PLAYER_STARTING_HOLDS
    return float(PLAYER_STARTING_HOLDS)


def per_hop(kernel: Any, comm: str) -> float:
    """What hauling one unit a hop costs (SOL): by its mass against a hold of ore's, or by its bulk - the larger."""
    from xylarium.config import get_commodity_stack_multiplier as stack
    from xylarium.kernel import cosmos, transit
    hop, hold = transit._typical_hop(kernel), _hold(kernel)
    by_mass = hop * cosmos.mass_of(comm) / cosmos.mass_of("ORE") / (hold * stack("ORE"))
    by_bulk = hop / (hold * stack(comm))
    return max(by_mass, by_bulk)


def _source_price(kernel: Any, port: Any, comm: str) -> float:
    """What a holding port sells a good at, in SOL."""
    from xylarium.kernel import prices
    from xylarium.kernel.economy import EconomyManager
    sells = EconomyManager.get_unit_prices(port, comm)[1]
    return float(sells) / max(1e-9, prices.level(getattr(port, "currency", "SOL"), kernel))


def landed(kernel: Any, comm: str) -> Dict[int, Tuple[float, int]]:
    """Every port's cheapest delivery of a good: sector -> (landed SOL per unit, source sector)."""
    hop = per_hop(kernel, comm)
    best: Dict[int, Tuple[float, int]] = {}
    heap: List[Tuple[float, int, int]] = []
    for sid, sec in kernel.sectors.items():
        port = sec.port
        if port is not None and port.sells.get(comm) and port.stock.get(comm, 0) > 0:
            c = _source_price(kernel, port, comm)
            heap.append((c, sid, sid))
    heapq.heapify(heap)
    while heap:
        c, sid, src = heapq.heappop(heap)
        if sid in best:
            continue
        best[sid] = (c, src)
        for nb in kernel.sectors[sid].warps:
            if nb in kernel.sectors and nb not in best:
                heapq.heappush(heap, (c + hop, nb, src))
    return best


def exotic(kernel: Any, port: Any, comm: str) -> Optional[float]:
    """A good's exotic index at a port: landed cost there over what it costs at its source."""
    rec = (getattr(port, "landed", None) or {}).get(comm)
    if not rec:
        return None
    return float(rec[0]) / max(1e-9, float(rec[2]))


def _dig(kernel: Any, planet: Any, comm: str, n: int) -> int:
    """Take up to n units of a good from a world's ground (a transfer; salt is dug from its beds - declared)."""
    from xylarium.kernel import matter
    took = 0
    dep = int((planet.element_deposits or {}).get(comm, 0))
    if dep > 0:
        q = min(n, dep)
        planet.element_deposits[comm] = dep - q
        took += q
    if comm == "NaCl" and took < n:
        q = min(n - took, held(kernel, planet, comm) - int((planet.element_deposits or {}).get(comm, 0))
                - int((planet.element_reserves or {}).get(comm, 0)))
        if q > 0:
            planet.society["halite_dug"] = int(planet.society.get("halite_dug", 0) or 0) + q
            matter.source("evaporite", "NaCl", q)
            took += q
    return took


def restock(kernel: Any) -> None:
    """A port whose system holds a good fills its shelves from the ground, to the level its holding supports (as
    its charter set it): the richest world first. Mined out, it stops."""
    for sid, sec in kernel.sectors.items():
        port = sec.port
        if port is None:
            continue
        for comm in goods():
            s = system(kernel, sid, comm)
            if s <= 0:
                continue
            want = int(port.max_stock.get(comm, 0) * s / (s + typical(kernel, comm))) - port.stock.get(comm, 0)
            for w in sorted(sec.planets, key=lambda p: (-held(kernel, p, comm), p.id)):
                if want <= 0:
                    break
                got = _dig(kernel, w, comm, want)
                port.stock[comm] = port.stock.get(comm, 0) + got
                want -= got


def recharter(kernel: Any) -> None:
    """Every port's charter read again from its system: it sells what its system holds (or still has in stock) and
    buys what it lacks or its people use - what is mined out stops being sold once the shelves are empty."""
    from xylarium.kernel.economy import EconomyManager
    for sid, sec in kernel.sectors.items():
        port = sec.port
        if port is None:
            continue
        EconomyManager.ensure_port_inventory(port)
        peopled = any(w.population > 0 for w in sec.planets)
        for comm in goods():
            s = system(kernel, sid, comm)
            port.sells[comm] = s > 0 or port.stock.get(comm, 0) > 0
            port.buys[comm] = s <= 0 or peopled


def season(kernel: Any) -> List[str]:
    """Once a year: every port's charter read again, its shelves filled from its system's ground, and its landed cost
    of every good it does not hold."""
    from xylarium.kernel import polity
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    st = stats(kernel)
    recharter(kernel)
    restock(kernel)
    top: List[Tuple[float, str, int]] = []
    for comm in goods():
        got = landed(kernel, comm)
        src_cost = {sid: c for sid, (c, src) in got.items() if sid == src}
        for sid, sec in kernel.sectors.items():
            port = sec.port
            if port is None:
                continue
            land = getattr(port, "landed", None)
            if land is None:
                port.landed = land = {}
            rec = got.get(sid)
            if rec is None or rec[1] == sid:
                land.pop(comm, None)                                  # held here, or out of every source's reach
                continue
            c, src = rec
            land[comm] = [round(c, 3), src, round(src_cost.get(src, c), 3)]
            top.append((c / max(1e-9, src_cost.get(src, c)), comm, sid))
    top.sort(reverse=True)
    st["exotic"] = [{"good": g, "sector": s, "index": round(i, 2)} for i, g, s in top[:12]]
    st["seasons"] += 1
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"most_exotic": st.get("exotic", [])[:5], "seasons": st["seasons"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="supply",
    state=lambda: {"exotic": [], "seasons": 0},
    season=season,
    summary=summary,
))
