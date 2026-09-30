"""
Xylarium topology: every question about the warp graph (docs/STANDARDS.md, S3).

Jump distances are breadth-first over each sector's warps in their stored order, so every caller sees the same
distances and the same tie order (nearest first, then discovery order). Anything that adds or removes warps
calls `changed(kernel)`, which advances the graph version that caches key on (cache.py).
"""

from typing import Any, Callable, Dict, List, Optional, Tuple


def _sectors(graph: Any) -> Dict[int, Any]:
    """A kernel, or a bare sector map (the universe is searched before any kernel exists)."""
    return graph.sectors if hasattr(graph, "sectors") else graph


def tree(kernel: Any, start: int, limit: int = 99) -> Tuple[Dict[int, int], Dict[int, Optional[int]]]:
    """Jump distances from ``start`` (up to ``limit``) and each sector's parent on a shortest route back."""
    dist: Dict[int, int] = {start: 0}
    parent: Dict[int, Optional[int]] = {start: None}
    frontier = [start]
    sectors = _sectors(kernel)
    while frontier:
        nxt = []
        for cur in frontier:
            if dist[cur] >= limit:
                continue
            for w in sectors[cur].warps:
                if w in sectors and w not in dist:
                    dist[w] = dist[cur] + 1
                    parent[w] = cur
                    nxt.append(w)
        frontier = nxt
    return dist, parent


def hops(kernel: Any, start: int, radius: int) -> Dict[int, int]:
    """Jump distances from ``start`` within ``radius``, in breadth-first order."""
    return tree(kernel, start, radius)[0]


def reach(kernel: Any, start: int, radius: int) -> List[int]:
    """Sectors within ``radius`` jumps, nearest first (ties in discovery order)."""
    dist = hops(kernel, start, radius)
    return sorted(dist, key=lambda s: dist[s])


def distances_to(kernel: Any, goal: int) -> Dict[int, int]:
    """Jump distance to ``goal`` from every sector that can reach it (breadth-first over reversed warps)."""
    sectors = _sectors(kernel)
    reverse: Dict[int, List[int]] = {}
    for s in sectors.values():
        for w in s.warps:
            reverse.setdefault(w, []).append(s.id)
    dist = {goal: 0}
    frontier = [goal]
    while frontier:
        nxt = []
        for sid in frontier:
            for src in reverse.get(sid, ()):
                if src not in dist and src in sectors:
                    dist[src] = dist[sid] + 1
                    nxt.append(src)
        frontier = nxt
    return dist


def nearest(kernel: Any, start: int, radius: int, want: Callable[[Any], bool]) -> Optional[int]:
    """The nearest sector within ``radius`` whose sector object satisfies ``want``."""
    for sid in reach(kernel, start, radius):
        if want(kernel.sectors[sid]):
            return sid
    return None


def first_hop(parent: Dict[int, Optional[int]], start: int, goal: int) -> Optional[int]:
    """The first jump from ``start`` on the route to ``goal`` in a ``tree`` parent map."""
    if goal not in parent or goal == start:
        return None
    node = goal
    while parent.get(node) is not None and parent[node] != start:
        node = parent[node]
    return node if parent.get(node) == start else None


def path(kernel: Any, start: int, goal: int) -> List[int]:
    """The fewest-jumps route from ``start`` to ``goal`` (both ends included), or [] if there is none."""
    if start == goal:
        return [start]
    _, parent = tree(kernel, start, 10 ** 9)
    if goal not in parent:
        return []
    route = [goal]
    while route[-1] != start:
        route.append(parent[route[-1]])
    return route[::-1]


def version(kernel: Any) -> int:
    return int(getattr(kernel, "graph_version", 0))


def changed(kernel: Any) -> None:
    """The warp graph changed (a cluster charted, a lane opened or closed): caches keyed on it go stale."""
    kernel.graph_version = version(kernel) + 1
