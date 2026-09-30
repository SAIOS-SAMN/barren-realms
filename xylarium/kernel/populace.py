"""
Xylarium populace: the galaxy grows with the people who play it, and is never empty.

  * AI to balance the humans. The galaxy is designed around a base company of human captains (BASE_HUMANS); every
    human beyond it makes room for AI_PER_HUMAN more autonomous captains (houses, traders, corsairs), so the lanes
    stay as busy per explorer as they were designed to be.
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

from xylarium.config import MAX_AI_CAPTAINS

BASE_HUMANS = 8                 # the human company the galaxy is designed around
AI_PER_HUMAN = 2                # autonomous captains per human beyond it
SYSTEMS_PER_EXPLORER = 10       # star systems of frontier owed to each human beyond it
FRONTIER_SOVEREIGNS = 2         # natives of a new cluster that take first flight at its charting


def humans(kernel: Any) -> List[Any]:
    return [c for c in kernel.captains.values() if not c.is_ai]


def extra_humans(kernel: Any) -> int:
    return max(0, len(humans(kernel)) - BASE_HUMANS)


def ai_capacity(kernel: Any) -> int:
    """How many autonomous captains the galaxy carries for the humans it has."""
    return MAX_AI_CAPTAINS + AI_PER_HUMAN * extra_humans(kernel)


def captain_capacity(kernel: Any) -> int:
    """Total captains (for checks that count everyone): the AI capacity plus the extra humans themselves."""
    return ai_capacity(kernel) + extra_humans(kernel)


def room_for_ai(kernel: Any) -> bool:
    return sum(1 for c in kernel.captains.values() if c.is_ai) < ai_capacity(kernel)


def room_for_captain(kernel: Any) -> bool:
    return len(kernel.captains) < captain_capacity(kernel)


def systems(kernel: Any) -> int:
    return sum(1 for s in kernel.sectors.values() if getattr(s, "kind", "") == "SYSTEM")


def on_player_joined(kernel: Any) -> List[str]:
    """A human joins: if the charted galaxy no longer holds enough frontier for everyone, chart the next cluster."""
    logs: List[str] = []
    rm = getattr(kernel, "research_manager", None)
    base = getattr(kernel, "_base_systems", None)
    if base is None:
        base = kernel._base_systems = systems(kernel)       # the galaxy as the first company found it
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
