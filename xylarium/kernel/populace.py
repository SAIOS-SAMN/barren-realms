"""
Xylarium populace: the galaxy grows with the people who play it, and is never empty.

  * Captains are commissioned by the worlds that can build them. Every world with shipyards can keep a hull of its
    own in service, so the lanes are as busy as the galaxy's industry: few where peoples are still bound to their
    homeworlds, many where they are spacefaring. Every human beyond the base company (BASE_HUMANS) makes room for
    AI_PER_HUMAN more, so the lanes stay as busy per explorer as they are by themselves.
  * Room to explore. Every human past the base is owed SYSTEMS_PER_EXPLORER star systems of frontier: when the
    charted galaxy runs short, the next cluster is charted at its edge. New clusters attach to the periphery with
    new sector ids and new warps; no existing system, lane or sector id ever changes.
  * The frontier is peopled. A new cluster already carries native societies (universe.furnish_sectors); the most
    advanced of them take first flight at once (FRONTIER_SOVEREIGNS), so every cluster has spacefaring
    civilizations with their own stardocks and governments to meet, trade with and quarrel with.
  * The Imperial heartland is settled (factions.found_great_powers): every habitable free world of its systems holds
    an Imperial colony, so the Imperium is an established realm and not a scatter of banners.
"""

from typing import Any, List

BASE_HUMANS = 8                 # the human company the galaxy is designed around
AI_PER_HUMAN = 2                # autonomous captains per human beyond it
SYSTEMS_PER_EXPLORER = 10       # star systems of frontier owed to each human beyond it
FRONTIER_SOVEREIGNS = 2         # natives of a new cluster that take first flight at its charting


def humans(kernel: Any) -> List[Any]:
    return [c for c in kernel.captains.values() if not c.is_ai]


def extra_humans(kernel: Any) -> int:
    return max(0, len(humans(kernel)) - BASE_HUMANS)


def shipyards(kernel: Any) -> int:
    """Peopled worlds whose yards can build and keep a starship (sustenance.yards)."""
    from xylarium.kernel import sustenance
    return sum(1 for s in kernel.sectors.values() for p in s.planets
               if p.population > 0 and not getattr(p, "natives", None) and sustenance.yards(p))


def ai_capacity(kernel: Any) -> int:
    """How many autonomous captains the galaxy's industry keeps in service: a hull per shipyard world, and room
    for the extra humans' company."""
    return shipyards(kernel) + AI_PER_HUMAN * extra_humans(kernel)


def captain_capacity(kernel: Any) -> int:
    return ai_capacity(kernel) + len(humans(kernel))


def room_for_ai(kernel: Any) -> bool:
    return sum(1 for c in kernel.captains.values() if c.is_ai) < ai_capacity(kernel)


def room_for_captain(kernel: Any) -> bool:
    """Room for one more autonomous captain (humans never count against the hulls the galaxy builds itself)."""
    return room_for_ai(kernel)


def systems(kernel: Any) -> int:
    return sum(1 for s in kernel.sectors.values() if getattr(s, "kind", "") == "SYSTEM")


def on_player_joined(kernel: Any) -> List[str]:
    """A human joins: if the charted galaxy no longer holds enough frontier for everyone, chart the next cluster."""
    logs: List[str] = []
    rm = getattr(kernel, "research_manager", None)
    rec = state.of(kernel, "populace")
    if rec["base_systems"] is None:
        rec["base_systems"] = systems(kernel)               # the galaxy as the first company found it
    base = rec["base_systems"]
    if rm is None or extra_humans(kernel) <= 0:
        return logs
    while systems(kernel) < base + SYSTEMS_PER_EXPLORER * extra_humans(kernel):
        index = 2
        while index in rm.minted_clusters:
            index += 1
        ok, msg, _ = rm.mint_frontier_cluster(kernel, index)
        if not ok:
            break
        logs.append(f"[FRONTIER] {msg}")
    return logs


def seed_cluster(kernel: Any, sector_ids: List[int]) -> List[str]:
    """The most advanced native societies of a newly charted cluster take first flight: it has civilizations."""
    from xylarium.kernel.natives import NativeManager
    logs: List[str] = []
    peoples = [p for sid in sector_ids for p in kernel.sectors[sid].planets if getattr(p, "natives", None)]
    peoples.sort(key=lambda p: (-p.natives.get("stage", 0), -p.natives.get("sapience", 0.0), p.id))
    for p in peoples[:FRONTIER_SOVEREIGNS]:
        name = p.natives.get("name", p.name)
        NativeManager.first_flight(kernel, p)
        if getattr(p, "civilization", None) is not None:
            logs.append(f"[FRONTIER] The {name} of {p.name} already sail the new cluster's lanes.")
    return logs


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="populace", state=lambda: {"base_systems": None}))
