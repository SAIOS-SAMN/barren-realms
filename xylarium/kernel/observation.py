"""
Xylarium observation: the universe is as large as it has been seen to be, and grows as its peoples look further.

Beyond the charted edge lies the next cluster - deterministic from the universe's seed and its index, so what is
found there does not depend on who finds it or when. It is charted when it is observed:

  * a ship enters a sector on the charted edge (the anchors the next cluster attaches to), or folds space into the
    next cluster's own sector ids;
  * a world with shipyards has the edge within its settler fleets' reach (what its people can sail to, they have
    seen).

One cluster per observation, and only the next one: the universe grows at the speed its observers reach its edge -
fast where peoples are spacefaring and pressing outward, not at all where no one looks. No quota of clusters, no
pressure counter; the bound is the observers' own reach.
"""

from typing import Any, List, Optional


def _rm(kernel: Any):
    return getattr(kernel, "research_manager", None)


def next_index(kernel: Any) -> int:
    rm = _rm(kernel)
    i = 2
    while rm is not None and i in rm.minted_clusters:
        i += 1
    return i


def span(index: int) -> range:
    """The sector ids a cluster occupies (research.mint_frontier_cluster's layout)."""
    start = 201 + (index - 2) * 40
    return range(start, start + 40)


def edge(kernel: Any) -> range:
    """The charted sectors the next cluster attaches to."""
    i = next_index(kernel)
    if i == 2:
        return range(91, 101)
    start = span(i).start
    return range(start - 10, start)


def chart(kernel: Any, why: str) -> Optional[str]:
    rm = _rm(kernel)
    if rm is None:
        return None
    i = next_index(kernel)
    ok, msg, ids = rm.mint_frontier_cluster(kernel, i)
    if not ok:
        return None
    st = state.of(kernel, "observation")
    st["charted"].append({"cycle": kernel.cycle_count, "cluster": i, "sectors": len(ids), "by": why})
    from xylarium.kernel import primordial
    primordial.first(kernel, "first_cluster_charted", why)
    return f"[FRONTIER] {msg} (observed: {why})"


def arrived(kernel: Any, sector_id: int) -> Optional[str]:
    """A ship entered a sector: if it stands on the charted edge, it sees what lies beyond (in a cosmic universe:
    entering a cell for the first time, it sees the cells around it - cosmos.py)."""
    from xylarium.kernel import cosmos
    if cosmos.is_cosmic(kernel):
        return cosmos.entered(kernel, sector_id)
    if sector_id in edge(kernel):
        return chart(kernel, f"a ship reached Sector {sector_id:03d}")
    return None


def folding_into(kernel: Any, destination: int) -> Optional[str]:
    """A fold aimed at the next cluster's coordinates charts it; space beyond that has not been seen at all."""
    from xylarium.kernel import cosmos
    if cosmos.is_cosmic(kernel):
        return None                                   # a fold reaches only what has been witnessed
    if destination not in kernel.sectors and destination in span(next_index(kernel)):
        return chart(kernel, f"a fold toward Sector {destination:03d}")
    return None


def quarter(kernel: Any) -> List[str]:
    """Worlds with shipyards look as far as their settler fleets can sail."""
    from xylarium.kernel import cosmos, demography, sustenance, topology
    if cosmos.is_cosmic(kernel):
        return []                                     # cosmos.quarter does it, cell by cell
    rim = set(edge(kernel))
    if not rim or not (rim & set(kernel.sectors)):
        return []
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population <= 0 or getattr(p, "natives", None) or not sustenance.yards(p):
                continue
            if rim & set(topology.reach(kernel, p.sector_id, demography.settler_reach(kernel, p))):
                log = chart(kernel, f"the fleets of {p.name} sail to the edge")
                return [log] if log else []
    return []


def summary(kernel: Any) -> dict:
    st = state.of(kernel, "observation")
    rm = _rm(kernel)
    return {"clusters": len(rm.minted_clusters) if rm is not None else 0, "sectors": len(kernel.sectors),
            "charted": st["charted"][-3:]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="observation", state=lambda: {"charted": []}, season=quarter, summary=summary))
