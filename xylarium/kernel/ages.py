"""
Xylarium ages: one clock, from foragers to the lanes - and where a new player steps into it.

Every age is a point on the same run of the same universe. The clock starts when the galaxy's first mind arises
(genesis "cosmic": cosmos.py - minds arise from chemistry and biology, each in its own year) and runs: fields, states, works, yards, ships, empires come when the peoples' own
physics brings them, in whatever year that is in this universe. An age begins when its milestone first happens
anywhere (genesis.firsts) - and the galaxy is then wherever it got to: some peoples ahead, most behind, a sector
crowded or empty. Nothing stops at spaceflight; the clock simply goes on.

  forager      year 0: every people forages
  agrarian     the first state
  first_flight the first starship
  lanes        the first empire
  classic      a ready-made galaxy already among the stars (the settled genesis; the TradeWars console)

Running to a later age takes the clock time it takes; each age reached is kept (runs/eras/seed<N>/<age>.json), so
the next player of that seed steps in at once - the same universe, since the clock is lockstep (scheduler.py)
and the kept ages are filed under the kernel's own laws (a digest of its source).

A player is a STEWARD of one people, whatever the age: bound to its homeworld, deciding what its council could -
its inquiry, its growth, farming, a state, works, and its society's gauges (society.py) - each only as its physics
allows; the council decides what the steward leaves to it. When the people raises yards the steward may also take
ship as its captain (the console opens; HOMEWORLD returns to the people). "Wake me when" runs the clock until
something happens to the steward's people.
"""

import os
from typing import Any, Callable, Dict, List, Optional

AGES: List[Dict[str, Any]] = [
    {"key": "forager", "name": "Age of Foragers", "until": None,
     "blurb": "Year 0. Bands living off the wild: no fields, no states, no money. The whole clock is ahead of you."},
    {"key": "agrarian", "name": "Age of Fields", "until": "first_state",
     "blurb": "The first state has risen somewhere. Most peoples still forage; some sow."},
    {"key": "first_flight", "name": "Age of First Flight", "until": "first_starship",
     "blurb": "Some people's first hull has risen. Others are still in their fields - or their forests."},
    {"key": "lanes", "name": "Age of the Lanes", "until": "first_empire",
     "blurb": "The first empire: peoples with ships protect, prey, and tax. The galaxy is as advanced as it got."},
    {"key": "classic", "name": "Classic: a ready-made galaxy", "until": None, "genesis": "settled",
     "blurb": "Skip the history: a settled galaxy of ports, houses and great powers. You are a captain (TradeWars)."},
]
ORDER = [a["key"] for a in AGES if a["key"] != "classic"]
ERAS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runs", "eras")


def age(key: str) -> Dict[str, Any]:
    return next(a for a in AGES if a["key"] == key)


_VERSION: List[str] = []


def version() -> str:
    """The kernel's own laws, as a digest of its source: an age kept by other laws is another universe."""
    if not _VERSION:
        import hashlib
        h = hashlib.sha1()
        here = os.path.dirname(os.path.abspath(__file__))
        for d in (here, os.path.dirname(here)):
            for name in sorted(os.listdir(d)):
                if name.endswith(".py"):
                    with open(os.path.join(d, name), "rb") as f:
                        h.update(name.encode() + f.read())
        _VERSION.append(h.hexdigest()[:10])
    return _VERSION[0]


def _era_path(seed: int, key: str, root: Optional[str] = None, pace: str = "neighbourly") -> str:
    return os.path.join(root or ERAS_DIR, f"seed{seed}", version(), pace, f"{key}.json")


def cached(seed: int, root: Optional[str] = None, pace: str = "neighbourly") -> List[str]:
    """The ages of this seed (at this pace) already reached (and kept)."""
    return [k for k in ORDER if os.path.exists(_era_path(seed, k, root, pace))]


def begin(seed: int, key: str, progress: Optional[Callable[[int, Dict[str, Any]], None]] = None,
          root: Optional[str] = None, max_years: Optional[int] = None, pace: str = "neighbourly") -> Any:
    """The universe of this seed at the start of this age: the latest age already kept at or before it, run on the
    clock until the age's milestone first happens (keeping every age passed on the way)."""
    from xylarium.kernel.engine import GameKernel
    from xylarium.persistence.store import StatePersistence
    a = age(key)
    if a.get("genesis") == "settled":
        kernel = GameKernel(seed=seed, genesis="settled")
        kernel.activate()
        kernel.state.setdefault("genesis", {})["age"] = key
        return kernel
    target = ORDER.index(key)
    kernel = None
    for k in reversed(ORDER[:target + 1]):
        if os.path.exists(_era_path(seed, k, root, pace)):
            kernel = StatePersistence.load_from_file(_era_path(seed, k, root, pace))
            if kernel is not None:
                break
    if kernel is None:
        kernel = GameKernel(seed=seed, genesis=f"cosmic:{pace}")   # the clock starts when the first mind arises
        _keep(kernel, seed, "forager", root, pace)
    kernel.activate()
    firsts = kernel.state.setdefault("genesis", {}).setdefault("firsts", {})
    limit = (max_years if max_years is not None else 10 ** 6) * 100
    start = kernel.cycle_count
    for k in ORDER[1:target + 1]:
        until = age(k)["until"]
        while until not in firsts and kernel.cycle_count - start < limit:
            kernel.tick_simulation()
            if progress is not None and kernel.cycle_count % 100 == 0:
                progress(kernel.cycle_count, firsts)
        if until not in firsts:
            break
        if not os.path.exists(_era_path(seed, k, root, pace)):
            _keep(kernel, seed, k, root, pace)
    kernel.state["genesis"]["age"] = key
    return kernel


def _keep(kernel: Any, seed: int, key: str, root: Optional[str], pace: str = "neighbourly") -> None:
    from xylarium.persistence.store import StatePersistence
    path = _era_path(seed, key, root, pace)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    StatePersistence.save_to_file(kernel, path)


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
    from xylarium.kernel import biosphere, knowledge, society, sustenance, ways
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
            "gauges": dict(society.gauges(p)), "dogma": round(float(getattr(p.civilization, "dogma", 0.0) or 0.0), 3),
            "stress": dict(p.society.get("stress") or society.stress(kernel, p)),
            "trades": society.trades(kernel, p), "myths": list(p.society.get("myths", [])),
            "forecast": p.society.get("forecast"),
            "life": _life(kernel, p, h),
            "firsts": dict((kernel.state.get("genesis") or {}).get("firsts", {}))}


def _life(kernel: Any, p: Any, h: Optional[str]) -> Dict[str, Any]:
    """How long its people live, how healthy they are, how old they are by each clock, and whom they remember."""
    from xylarium.kernel import clock, lifespan
    life = dict(p.society.get("life") or {})
    return {"expectancy_years": life.get("expectancy"), "thr": life.get("thr"), "cohorts": lifespan.cohorts(p),
            "practice": life.get("practice"), "ancestors": life.get("ancestors", 0),
            "age": clock.age_of_people(kernel, p),
            "remembered": [f"{f['name']} ({f['role']})" for f in lifespan.remembered(kernel, h)[:5]]}


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
        from xylarium.kernel import institutions
        institutions.found_currency(kernel, p)
        return "A council, a granary, a tax: your people found a state."
    if what == "gauge":
        from xylarium.kernel import society
        try:
            key, _, val = (arg or "").partition("=")
            society.set_gauge(p, key.strip(), float(val))
        except (KeyError, ValueError):
            return f"Gauges: {', '.join(society.GAUGES)} - each 0 to 1 (e.g. temple=0.3)."
        return f"Your people's {key.strip()} is set to {society.gauges(p)[key.strip()]:.0%}."
    if what == "exodus":
        holder = knowledge.holder_of_planet(p)
        for s in kernel.sectors.values():
            for w in s.planets:
                if w.population > 0 and knowledge.holder_of_planet(w) == holder:
                    w.society["exodus_ordered"] = True
        return "Your council will carry every one of your people it can away from a dying sun, whatever it costs."
    if what == "counsel":
        from xylarium.kernel import counsel
        return counsel.render(counsel.counsel(kernel, p))
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
