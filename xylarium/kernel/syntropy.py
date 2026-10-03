"""
Xylarium syntropy: the population-technology saddle, measured for every people - and the fork it puts to them.

A people of N on land that carries K(A) at what it knows (A) grows and learns together (Kremer 1993, with Malthus
and Boserup inside it):

    dN/dt = r N (1 - N / K(A)) - emigration - restraint
    dA/dt = thinking(N, free labour, leisure, depth) - delta A          (knowledge.py: delta = 15% a year)

Standing still is not a resting place. Where N sits at K and its thinking only replaces what depreciates, the
system is at a saddle: pushed toward more free labour (a surplus, a new world, a meeting) A grows, K follows and N
with it - the long acceleration of history, toward the stars; pushed the other way, depreciation wins, K falls
under N - overshoot, strife, famine. Every people drifts off the saddle one way or the other. Which way is its own
choice; the laws only make standing still impossible.

THE INDEX. Each people's syntropy is S = ln K + ln(1 + A) + ln W - its capacity, its knowledge and its worlds -
measured every season; its slope (per year, smoothed over a generation) says which way it is moving. A sustained
change of sign is a turning in its history (TURNING): toward growth, or toward decline.

THE FORK. Once a generation a council with yards weighs, through its own mind (decide.choose: its horizon, its
noise), the paths off a crowded world:

  outward  the room within its fleets' reach - the empty worlds its own biology can live on - worth the lives they
           would hold (demography.value_of_room), at the cost of the hulls that carry its daughters there;
  enough   live within its world under the Ascetic Mandate: the productivity frugality gives (config NATAL_POLICIES)
           on its whole people, at the cost of the room it will not grow into.

Nothing tilts it but what it sees: a people with empty worlds within reach and the yards to reach them tends
outward, one ringed by nothing it can live on tends to enough - and either may misjudge. The choice is re-weighed
every generation, so no covenant is forever.
"""

import math
from typing import Any, Dict, List



def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "syntropy")


def _peoples(kernel: Any) -> Dict[str, List[Any]]:
    from xylarium.kernel import knowledge
    out: Dict[str, List[Any]] = {}
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population > 0 and getattr(p, "civilization", None) is not None and not getattr(p, "natives", None):
                h = knowledge.holder_of_planet(p)
                if h:
                    out.setdefault(h, []).append(p)
    return out


def index(kernel: Any, holder: str, worlds: List[Any]) -> Dict[str, float]:
    """S and its parts for one people now."""
    from xylarium.kernel import biosphere, knowledge
    k = sum(max(1, biosphere.carrying_capacity(kernel, p)) for p in worlds)
    a = sum(knowledge.experience(kernel, holder, d) for d in knowledge.DOMAINS)
    n = sum(p.population for p in worlds)
    return {"S": math.log(k) + math.log1p(a) + math.log(max(1, len(worlds))), "K": k, "A": a, "N": n,
            "W": len(worlds), "crowding": n / max(1, k)}


def reading(kernel: Any, holder: str) -> Dict[str, Any]:
    return dict(stats(kernel)["peoples"].get(holder, {}))


# ---------------------------------------------------------------------- the fork
def room_in_reach(kernel: Any, planet: Any) -> int:
    """How many of its own kind the empty worlds its fleets reach would carry (at its own works)."""
    from xylarium.kernel import biosphere, demography, topology
    reach = demography.settler_reach(kernel, planet)
    if reach <= 0:
        return 0
    metab = biosphere.metabolism_of(kernel, planet)
    room = 0
    for sid in topology.reach(kernel, planet.sector_id, reach):
        sec = kernel.sectors.get(sid)
        if sec is None:
            continue
        for w in sec.planets:
            if w.population > 0 or getattr(w, "civilization", None) is not None or w.owner_id:
                continue
            room += biosphere.carrying_capacity(kernel, w, citadel=planet.citadel_level, metabolism=metab)
    return room


def fork(kernel: Any, planet: Any, record: bool = True) -> str:
    """The council's choice off a crowded world: 'expand' (outward) or 'steady' (enough). With record False, only
    what it would choose (another people's mind, modelled: counsel.py) - nothing is kept."""
    from xylarium.config import NATAL_POLICIES, PLANETARY_SPACEFLIGHT_COST, PRICE_LEVEL, DAUGHTER_EMIGRANTS_MAX
    from xylarium.kernel import decide, demography
    m = decide.mind_of_planet(kernel, planet)
    level = PRICE_LEVEL.get(planet.currency, 1.0)
    room = room_in_reach(kernel, planet)
    hulls = math.ceil(room / DAUGHTER_EMIGRANTS_MAX) if room else 0
    out_value = demography.value_of_room(kernel, planet, room, m)
    out_cost = hulls * PLANETARY_SPACEFLIGHT_COST * level
    frugal = NATAL_POLICIES["ascetic"].get("productivity", 1.0) - 1.0
    enough_value = decide.worth(kernel, frugal * planet.population * demography._tax_per_head_quarter(planet), m,
                                planet.currency)
    enough_cost = out_value if room else 0.0                 # the room it will not grow into
    tally = dict(decide.stats(kernel)["chosen"])
    best = decide.choose(kernel, [decide.option("expand", out_cost, out_value, aim="grow"),
                                  decide.option("steady", enough_cost, enough_value, aim="hold")], m, planet.id, "fork")
    choice = best["name"] if best is not None else "steady"
    if not record:
        decide.stats(kernel)["chosen"] = tally
        return choice
    st = stats(kernel)
    st["forks"][choice] = st["forks"].get(choice, 0) + 1
    was = (planet.society.get("fork") or {}).get("choice")
    from xylarium.kernel import knowledge, lifespan
    planet.society["fork"] = {"cycle": kernel.cycle_count, "choice": choice, "was": was, "room": room,
                              "died": lifespan.died(kernel, knowledge.holder_of_planet(planet)),
                              "outward": round(out_value - out_cost, 1), "enough": round(enough_value - enough_cost, 1)}
    return choice


def due(kernel: Any, planet: Any) -> bool:
    """Whether the council weighs its fork again: once a generation."""
    from xylarium.kernel import fertility
    from xylarium.kernel import knowledge, lifespan
    rec = planet.society.get("fork") or {}
    if rec.get("cycle") is None:
        return True
    holder = knowledge.holder_of_planet(planet)
    if "died" in rec and lifespan.died(kernel, holder) > 0:          # a new generation of minds weighs it again
        return lifespan.turned_over(kernel, holder, rec["died"], planet.population)
    return kernel.cycle_count - int(rec["cycle"]) >= fertility.generation_of(kernel, planet) * 100


# ---------------------------------------------------------------------- the season
def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import fertility, history
    st = stats(kernel)
    logs: List[str] = []
    seen = st["peoples"]
    peoples = _peoples(kernel)
    for holder, worlds in sorted(peoples.items()):
        now = index(kernel, holder, worlds)
        rec = seen.get(holder)
        if rec is None:
            seen[holder] = dict(now, slope=0.0, cycle=kernel.cycle_count, sign=0, since=kernel.cycle_count)
            continue
        years = max(1e-6, (kernel.cycle_count - rec["cycle"]) / 100.0)
        slope = (now["S"] - rec["S"]) / years
        gen = fertility.generation_of(kernel, max(worlds, key=lambda p: (p.population, p.id)))
        w = min(1.0, years / max(years, gen))                  # smoothed over its own generation
        smooth = (1 - w) * rec["slope"] + w * slope
        sign = (smooth > 0) - (smooth < 0)
        rec.update(now, slope=round(smooth, 6), cycle=kernel.cycle_count)
        # a turning is a change of direction that has held for a generation
        if sign != rec["sign"]:
            if sign != rec.get("pending", rec["sign"]):
                rec["pending"], rec["pending_since"] = sign, kernel.cycle_count
            elif kernel.cycle_count - rec["pending_since"] >= gen * 100 and sign != 0:
                rec["sign"], rec["since"] = sign, kernel.cycle_count
                rec.pop("pending", None)
                name = holder.split(":", 1)[-1]
                way = "growth" if sign > 0 else "decline"
                history.event(kernel, "TURNING", f"The {name} turn toward {way}", actors=[holder],
                              planet=max(worlds, key=lambda p: (p.population, p.id)),
                              cause=f"their capacity, knowledge and reach together, {smooth:+.4f} a year",
                              data={"S": round(now["S"], 4), "slope": round(smooth, 6),
                                    "crowding": round(now["crowding"], 3)})
                logs.append(f"[SYNTROPY] The {name} turn toward {way}.")
        else:
            rec.pop("pending", None)
    for gone in [h for h in seen if h not in peoples]:
        seen.pop(gone)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    ps = st["peoples"]
    if not ps:
        return {}
    return {"growing": sum(1 for r in ps.values() if r["slope"] > 0),
            "declining": sum(1 for r in ps.values() if r["slope"] < 0), "forks": dict(st["forks"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="syntropy",
    state=lambda: {"peoples": {}, "forks": {}},
    season=quarter,
    summary=summary,
))
