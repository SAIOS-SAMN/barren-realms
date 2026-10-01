"""
Xylarium ages: where a universe begins, and who the player is in it.

A new player may drop into any age. Each is either its own genesis or a universe run forward on the clock until a
measured milestone first happens in it (genesis.firsts) - never a timer: the age of first flight begins when some
people first commissions a hull, in whatever year that is in this universe.

  forager      every people forages on its homeworld (ways.py)             genesis "forager"
  agrarian     every people a young state at citadel 0 (primordial.py)     genesis "primordial"
  first_flight the agrarian universe, run until the first starship         primordial -> first_starship
  spacefaring  a galaxy already among the stars (TradeWars console)        genesis "settled"

Before spaceflight the player is a STEWARD: bound to one people's homeworld, with no ship. The steward may do what
the people's own council could - point its inquiry, set its growth, take up farming, found a state, raise works -
each only when the people's physics allows it (a state needs a surplus that can bear it; works need a treasury).
The council still decides what the steward leaves to it. When the steward's people commissions its first hull, the
steward may become its first captain, and the console opens. "Wake me when" runs the clock until something happens
to the steward's people.
"""

from typing import Any, Callable, Dict, List, Optional

AGES: List[Dict[str, Any]] = [
    {"key": "forager", "name": "Age of Foragers", "genesis": "forager", "until": None,
     "blurb": "Bands living off the wild. No fields, no states, no money. Centuries before anyone sows."},
    {"key": "agrarian", "name": "Age of Fields", "genesis": "primordial", "until": None,
     "blurb": "Young states on their homeworlds: councils, granaries, taxes. Nobody has left the ground."},
    {"key": "first_flight", "name": "Age of First Flight", "genesis": "primordial", "until": "first_starship",
     "blurb": "The first hull has just risen from some world's yards. The lanes are empty."},
    {"key": "spacefaring", "name": "Age of the Lanes", "genesis": "settled", "until": None,
     "blurb": "A galaxy already among the stars: ports, houses, great powers. You are a captain (TradeWars)."},
]
FAST_FORWARD_YEARS = 600        # a universe that has not reached the milestone by then is handed over as it is


def age(key: str) -> Dict[str, Any]:
    return next(a for a in AGES if a["key"] == key)


def begin(seed: int, key: str, progress: Optional[Callable[[int, Dict[str, Any]], None]] = None) -> Any:
    """A universe at the start of this age (run forward on the clock to its milestone if it has one)."""
    from xylarium.kernel.engine import GameKernel
    a = age(key)
    kernel = GameKernel(seed=seed, genesis=a["genesis"])
    kernel.activate()
    kernel.state.setdefault("genesis", {})["age"] = key
    until = a.get("until")
    if until:
        firsts = kernel.state["genesis"].setdefault("firsts", {})
        while until not in firsts and kernel.cycle_count < FAST_FORWARD_YEARS * 100:
            kernel.tick_simulation()
            if progress is not None and kernel.cycle_count % 100 == 0:
                progress(kernel.cycle_count, firsts)
        kernel.state["genesis"]["handed_over"] = {"cycle": kernel.cycle_count, "reached": until in firsts}
    return kernel


# ---------------------------------------------------------------------- the steward
def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "ages")


def peoples(kernel: Any) -> List[Any]:
    """The homeworlds a steward may take up: every people's most populous world."""
    from xylarium.kernel import knowledge
    best: Dict[str, Any] = {}
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population <= 0 or getattr(p, "natives", None) or getattr(p, "civilization", None) is None:
                continue
            h = knowledge.holder_of_planet(p)
            if h not in best or p.population > best[h].population:
                best[h] = p
    return sorted(best.values(), key=lambda p: (-p.population, p.id))


def bind(kernel: Any, player_id: str, name: str, planet: Any) -> None:
    stats(kernel)["stewards"][player_id] = {"planet": planet.id, "name": name, "since": kernel.cycle_count}
    planet.society["steward"] = player_id


def homeworld(kernel: Any, player_id: str) -> Optional[Any]:
    rec = stats(kernel)["stewards"].get(player_id)
    return kernel.get_planet(rec["planet"]) if rec else None


def status(kernel: Any, player_id: str) -> Dict[str, Any]:
    from xylarium.kernel import biosphere, knowledge, sustenance, ways
    p = homeworld(kernel, player_id)
    if p is None:
        return {}
    h = knowledge.holder_of_planet(p)
    st = knowledge.stocks(kernel, h)
    return {"world": p.name, "people": getattr(p.civilization, "name", p.name), "year": kernel.cycle_count // 100,
            "population": p.population, "room": biosphere.carrying_capacity(kernel, p), "way": ways.way(p),
            "crop_share": round(ways.k_factor(kernel, p), 3), "surplus": round(ways.surplus(kernel, p), 3),
            "domestication": round(ways.domestication(kernel, p), 3), "citadel": p.citadel_level,
            "treasury": p.treasury, "morale": p.morale, "yards": bool(sustenance.yards(p)),
            "focus": knowledge.stats(kernel)["focus"].get(h), "knowledge": {d: round(v, 1) for d, v in st.items()},
            "policy": getattr(p, "growth_policy", None) or "expand",
            "firsts": dict((kernel.state.get("genesis") or {}).get("firsts", {}))}


def act(kernel: Any, player_id: str, what: str, arg: Optional[str] = None) -> str:
    """A steward's decision for its people, where the people's physics allows it."""
    from xylarium.config import HOUSEHOLD_INCOME_SHARE
    from xylarium.kernel import demography, knowledge, ways
    p = homeworld(kernel, player_id)
    if p is None:
        return "You steward no people."
    h = knowledge.holder_of_planet(p)
    if what == "focus":
        knowledge.focus(kernel, h, arg)
        return f"Your people's inquiry turns to {arg or 'whatever their needs call for'}."
    if what == "policy":
        if arg not in demography.POLICIES:
            return f"Policies: {', '.join(demography.POLICIES)}."
        p.growth_policy = arg
        return f"Your people will {'grow into their land' if arg == 'expand' else 'hold their numbers steady'}."
    if what == "farm":
        if ways.way(p) != "forage":
            return "Your people already farm."
        p.society["way"] = "farm"
        ways._refresh(kernel, p)
        return "Your people sow their first fields. Their crops are half-wild; they will breed them year by year."
    if what == "state":
        if ways.way(p) != "farm":
            return "Only a farming people can found a state."
        if ways.surplus(kernel, p) < 1.0 - HOUSEHOLD_INCOME_SHARE:
            return (f"Their harvests leave a surplus of {ways.surplus(kernel, p):.0%} - a state would take "
                    f"{1.0 - HOUSEHOLD_INCOME_SHARE:.0%}. Breed the crops further first.")
        p.society["way"] = "state"
        return "A council, a granary, a tax: your people found a state."
    if what == "works":
        if ways.stateless(p):
            return "Without a state there is no treasury to build with."
        msg = demography._works(kernel, p)
        return msg or "The council weighed its works and found none worth their price this season."
    return "Unknown decision."


def wake_when(kernel: Any, player_id: str, max_years: int = 50) -> List[str]:
    """Run the clock until something happens to the steward's people (or max_years pass): what happened."""
    p = homeworld(kernel, player_id)
    if p is None:
        return []
    from xylarium.kernel import sustenance

    def watch() -> tuple:
        return p.society.get("way"), p.citadel_level, bool(sustenance.yards(p)), p.population > 0
    firsts = (kernel.state.get("genesis") or {}).setdefault("firsts", {})
    before, known = watch(), set(firsts)
    start, events = kernel.cycle_count, []
    name = getattr(p.civilization, "name", p.name)
    while kernel.cycle_count - start < max_years * 100:
        last = kernel.action_logs[-1] if kernel.action_logs else None
        kernel.tick_simulation()
        mine = [l for l in _since(kernel.action_logs, last) if name in l or p.name in l]
        new_firsts = [f"{k.replace('_', ' ')} ({v['who']})" for k, v in firsts.items() if k not in known]
        now = watch()
        if mine or new_firsts or now != before:
            events = mine[-5:] + [f"FIRST: {f}" for f in new_firsts]
            if now != before and not events:
                events = [f"{name}: way {now[0]}, citadel {now[1]}, yards {'raised' if now[2] else 'none'}"]
            break
    return events or [f"{max_years} quiet years pass."]


def _since(logs: Any, last: Any) -> List[str]:
    """The lines appended to a (bounded) log after `last` (found by identity, from the end)."""
    lines = list(logs)
    if last is None:
        return lines
    for i in range(len(lines) - 1, -1, -1):
        if lines[i] is last:
            return lines[i + 1:]
    return lines


def first_captain(kernel: Any, player_id: str, name: str) -> Optional[Any]:
    """The steward's people has yards: the steward becomes its first captain, its ship at the homeworld."""
    from xylarium.kernel import biosphere, sustenance
    p = homeworld(kernel, player_id)
    if p is None or not sustenance.yards(p):
        return None
    cap = kernel.register_player(player_id, name)
    old = kernel.sectors.get(cap.sector_id)
    if old is not None and cap.id in old.captains:
        old.captains.remove(cap.id)
    cap.sector_id = p.sector_id
    kernel.sectors[p.sector_id].captains.append(cap.id)
    cap.metabolism = biosphere.metabolism_of(kernel, p)
    stats(kernel)["stewards"][player_id]["captain"] = cap.id
    return cap


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="ages", state=lambda: {"stewards": {}}))


def shape(kernel: Any, player_id: str, asked: Dict[str, float]) -> Optional[Dict[str, float]]:
    """The Progenitor's hand at genesis: before the first season, a steward may set its people's genome (the
    six axes, as designer.py builds them, in full). Its trade-offs are physics; the world selects from then on."""
    from xylarium.kernel import designer
    p = homeworld(kernel, player_id)
    if p is None or kernel.cycle_count > 0:
        return None
    got = designer.build(kernel, None, asked, full=True)
    p.society["genome"] = dict(got)
    return got
