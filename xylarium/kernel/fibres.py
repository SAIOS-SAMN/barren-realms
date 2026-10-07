"""
Xylarium fibres: the warp lanes as the galaxy's connective tissue, with economies of scale.

  * Every passage along a lane is recorded: the traffic (the ship plus the base value of its cargo) adds
    to the lane's throughput, and the goods' value is booked on an antisymmetric flow ledger - what goes
    a -> b is minus what goes b -> a - so each lane carries a signed net flow and a sector's net export
    is the divergence of the flows around it.
  * A lane's development is the memory of its traffic: each season it keeps three quarters of what it had
    and adds the season's throughput (so a steadily used lane settles at four seasons' traffic).
  * Economies of scale: a lane's transit cost is 1 / (1 + development / the mean travelled lane's). There
    is no chosen reference volume - a lane is cheap relative to the galaxy's other lanes, so the law is the
    same in a small galaxy or a large one. Crews still eat: cost never falls below a quarter.
  * Fibre distance: the cheapest route cost from Sol over developed lanes. Busy fibres pull remote ports
    closer - their regional price gradient (manufactures dearer and raw goods cheaper with distance) eases
    along the trunk routes, so linked regions converge.
  * Curvature. Spacetime can be disturbed: a shock puts curvature kappa on a lane, and a singularity (mass M)
    curves every lane touching its sector. A lane's geodesic cost is fibre cost x (1 + kappa), so routes bend
    around damage. Disturbances obey their physics: a shock radiates away (gravitational waves), halving each
    season; a singularity evaporates (Hawking), losing mass as 1/M^2 - so its lifetime grows as M^3, and a
    small one flares out within seasons while a large one reshapes the map for good.
  * Geodesics: every route in the galaxy (captains, freight, haulers, the route optimizer) follows the
    cheapest path under these costs; paths are cached until costs change.
"""

import heapq
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import COMMODITY_CONFIG

MIN_COST = 0.25
SEASON_MEMORY = 0.75
SHIP_TRAFFIC = 10.0          # a passage counts as a little traffic even with an empty hold


def key(a: int, b: int) -> str:
    return f"{min(a, b)}-{max(a, b)}"


def state(kernel: Any) -> Dict[str, Any]:
    return _state.of(kernel, "fibres")


def cargo_value(captain: Any) -> float:
    cargo = captain.ship.cargo
    v = cargo.ore * COMMODITY_CONFIG["ORE"]["base_price"] + cargo.organics * COMMODITY_CONFIG["ORGANICS"]["base_price"]
    v += cargo.equipment * COMMODITY_CONFIG["EQUIPMENT"]["base_price"]
    for el, n in cargo.elements.items():
        v += n * COMMODITY_CONFIG.get(el, {}).get("base_price", 0)
    return float(v)


def record(kernel: Any, captain: Any, a: int, b: int) -> None:
    st = state(kernel)
    k = key(a, b)
    goods = cargo_value(captain)
    st["q"][k] = st["q"].get(k, 0.0) + SHIP_TRAFFIC + goods
    sign = 1.0 if a < b else -1.0                  # orientation low -> high
    st["net"][k] = st["net"].get(k, 0.0) + sign * goods
    st["passages"] += 1


def record_flow(kernel: Any, a: int, b: int, value: float) -> None:
    """Passenger traffic along a lane (tourism): develops it like goods, carried from a to b."""
    st = state(kernel)
    k = key(a, b)
    st["q"][k] = st["q"].get(k, 0.0) + value
    st["net"][k] = st["net"].get(k, 0.0) + (1.0 if a < b else -1.0) * value


def net_flow(kernel: Any, a: int, b: int) -> float:
    """Signed goods value moved a -> b (antisymmetric: net_flow(a, b) == -net_flow(b, a))."""
    v = state(kernel)["net"].get(key(a, b), 0.0)
    return v if a < b else -v


def divergence(kernel: Any, sector_id: int) -> float:
    """Net goods value that left a sector along its lanes (its net export)."""
    sec = kernel.sectors[sector_id]
    return sum(net_flow(kernel, sector_id, w) for w in sec.warps if w in kernel.sectors)


def mean_development(kernel: Any) -> float:
    """The typical travelled lane's development (lanes nobody uses don't dilute it)."""
    dev = state(kernel)["dev"]
    return sum(dev.values()) / len(dev) if dev else 0.0


def lane_count(kernel: Any) -> int:
    return sum(len(s.warps) for s in kernel.sectors.values()) // 2 or 1


def cost(kernel: Any, a: int, b: int) -> float:
    st = state(kernel)
    mean = st.get("mean", 0.0)
    if mean <= 0:
        return 1.0
    return max(MIN_COST, 1.0 / (1.0 + st["dev"].get(key(a, b), 0.0) / mean))


def season(kernel: Any) -> None:
    """Close the season: lanes remember three quarters of their development and add this season's traffic."""
    st = state(kernel)
    dev = st["dev"]
    for k in sorted(set(dev) | set(st["q"])):                  # never hash order
        v = dev.get(k, 0.0) * SEASON_MEMORY + st["q"].get(k, 0.0)
        if v < 1.0:
            dev.pop(k, None)
        else:
            dev[k] = round(v, 3)
    st["q"] = {}
    st["seasons"] += 1
    st["mean"] = mean_development(kernel)
    relax(kernel)
    reprice_remoteness(kernel)


def fibre_distances(kernel: Any, origin: int = 1) -> Dict[int, float]:
    dist: Dict[int, float] = {origin: 0.0}
    heap: List[Tuple[float, int]] = [(0.0, origin)]
    while heap:
        d, sid = heapq.heappop(heap)
        if d > dist.get(sid, float("inf")):
            continue
        for w in kernel.sectors[sid].warps:
            if w not in kernel.sectors:
                continue
            nd = d + cost(kernel, sid, w)
            if nd < dist.get(w, float("inf")):
                dist[w] = nd
                heapq.heappush(heap, (nd, w))
    return dist


def reprice_remoteness(kernel: Any) -> None:
    """A port's remoteness is its fibre distance from Sol: developed trunk routes bring regions closer."""
    dist = fibre_distances(kernel, 1)
    for sid, sec in kernel.sectors.items():
        if sec.port is not None and sid in dist and sid != 105:
            sec.port.remoteness = round(dist[sid], 3)


def summary(kernel: Any) -> Dict[str, Any]:
    st = state(kernel)
    dev = sorted(st["dev"].items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in dev) or 1.0
    top = max(1, lane_count(kernel) // 10)
    return {
        "passages": st["passages"],
        "developed_lanes": len(dev),
        "lanes": lane_count(kernel),
        "trunk_share": round(sum(v for _, v in dev[:top]) / total, 3),
        "trunks": [(k, round(v)) for k, v in dev[:5]],
        "cheapest_cost": round(min((cost(kernel, *map(int, k.split("-"))) for k, _ in dev[:1]), default=1.0), 3),
    }


# ---------------------------------------------------------------------- curvature & geodesics
HAWKING_K = 1.0     # mass-loss constant: dM/dseason = -K / M^2 (a unit singularity lasts a third of a season)


def curvature(kernel: Any, a: int, b: int) -> float:
    st = state(kernel)
    k = st.get("shock", {}).get(key(a, b), 0.0)
    holes = st.get("singularities", {})
    return k + holes.get(str(a), 0.0) + holes.get(str(b), 0.0)


def shock(kernel: Any, a: int, b: int, kappa: float) -> None:
    """A spacetime shock on a lane (a weapon, a collapse): adds curvature that radiates away."""
    st = state(kernel)
    st.setdefault("shock", {})[key(a, b)] = st.get("shock", {}).get(key(a, b), 0.0) + float(kappa)
    _bump(kernel)


def singularity(kernel: Any, sector_id: int, mass: float) -> None:
    """A singularity in a sector (mass in curvature units): every lane touching it bends until it evaporates."""
    st = state(kernel)
    holes = st.setdefault("singularities", {})
    holes[str(sector_id)] = holes.get(str(sector_id), 0.0) + float(mass)
    _bump(kernel)


def relax(kernel: Any) -> None:
    """A season passes: shocks halve (radiated away), singularities evaporate (dM = -K/M^2, integrated exactly:
    M^3 falls by 3K per season)."""
    st = state(kernel)
    changed = False
    for k in list(st.get("shock", {})):
        v = st["shock"][k] / 2.0
        if v < 0.01:
            st["shock"].pop(k)
        else:
            st["shock"][k] = v
        changed = True
    for sid in list(st.get("singularities", {})):
        m3 = st["singularities"][sid] ** 3 - 3.0 * HAWKING_K
        if m3 <= 0:
            st["singularities"].pop(sid)
        else:
            st["singularities"][sid] = m3 ** (1.0 / 3.0)
        changed = True
    if changed:
        _bump(kernel)


def _bump(kernel: Any) -> None:
    st = state(kernel)
    st["version"] = st.get("version", 0) + 1


def base_lane_cost(kernel: Any, a: int, b: int) -> float:
    """What a lane costs to travel, before anyone's toll: development, curvature, the shear's stretch - or, for a
    wormhole's throat, one hop through the bounce."""
    from xylarium.kernel import cosmos, transit               # a lane between rings stretches as the galaxy shears
    w = transit.worm_cost(kernel, a, b)
    if w is not None:
        return w
    return cost(kernel, a, b) * (1.0 + curvature(kernel, a, b)) * cosmos.stretch(kernel, a, b)


def lane_cost(kernel: Any, a: int, b: int) -> float:
    """What a lane costs a route: travelling it, and what its holder charges a passer (toll and a throat's tithe,
    in the hops that money would buy - transit.charge_hops) - so routes weigh tolls as passers pay them."""
    from xylarium.kernel import transit
    return base_lane_cost(kernel, a, b) + transit.charge_hops(kernel, a, b)


def geodesic(kernel: Any, start: int, goal: int) -> List[int]:
    """The cheapest path under fibre costs and curvature (a list of sector ids, start..goal; [] if none).
    Lane costs are computed once per cost version; each start's whole shortest-path tree is cached."""
    if start == goal:
        return [start]
    st = state(kernel)
    version = (st.get("version", 0), st.get("seasons", 0), len(kernel.sectors),
               sum(len(sec.warps) for sec in kernel.sectors.values()))   # new lanes (shortcuts) invalidate
    def adjacency() -> Dict[int, List[Tuple[int, float]]]:
        return {sid: [(w, lane_cost(kernel, sid, w)) for w in sec.warps if w in kernel.sectors]
                for sid, sec in kernel.sectors.items()}
    adj = cache.memo(kernel, "geodesic", "_adj", adjacency, epoch=version)
    tree = cache.memo(kernel, "geodesic", ("tree", start), lambda: _shortest_tree(adj, start), epoch=version)
    dist, prev = tree
    if goal not in dist:
        return []
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    return path


def _shortest_tree(adj: Dict[int, List[Tuple[int, float]]], start: int) -> Tuple[Dict[int, float], Dict[int, int]]:
    """Dijkstra from ``start``; ties go to fewer hops (deterministic)."""
    dist: Dict[int, float] = {start: 0.0}
    hops: Dict[int, int] = {start: 0}
    prev: Dict[int, int] = {}
    heap: List[Tuple[float, int, int]] = [(0.0, 0, start)]
    while heap:
        d, h, sid = heapq.heappop(heap)
        if d > dist.get(sid, float("inf")) + 1e-12:
            continue
        for w, c in adj.get(sid, ()):
            nd = d + c
            old = dist.get(w, float("inf"))
            if nd < old - 1e-12 or (abs(nd - old) <= 1e-12 and h + 1 < hops.get(w, 10 ** 9)):
                dist[w] = nd
                hops[w] = h + 1
                prev[w] = sid
                heapq.heappush(heap, (nd, h + 1, w))
    return dist, prev


from xylarium.kernel import cache  # noqa: E402
from xylarium.kernel import state as _state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402


def _season(kernel: Any) -> List[str]:
    season(kernel)
    return []


register_subsystem(Subsystem(
    name="fibres",
    state=lambda: {"dev": {}, "q": {}, "net": {}, "passages": 0, "seasons": 0},
    season=_season,
    summary=summary,
))
