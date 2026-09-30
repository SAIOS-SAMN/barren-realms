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
    f = getattr(kernel, "fibres", None)
    if f is None:
        f = kernel.fibres = {"dev": {}, "q": {}, "net": {}, "passages": 0, "seasons": 0}
    return f


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
    for k in set(dev) | set(st["q"]):
        v = dev.get(k, 0.0) * SEASON_MEMORY + st["q"].get(k, 0.0)
        if v < 1.0:
            dev.pop(k, None)
        else:
            dev[k] = round(v, 3)
    st["q"] = {}
    st["seasons"] += 1
    st["mean"] = mean_development(kernel)
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
