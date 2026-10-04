"""
Xylarium sustenance: can a people feed itself, did it make it off its world, and where will it find food if not?

Every quarter each world's books are read - the staple its land harvested against what its people needed
(staples.py) - and smoothed into its self-sufficiency over a year. A world short of it whose stores would run out
within SUSTENANCE_RUNWAY_QUARTERS is hungry, and what a hungry people does depends on whether it can sail:

    secure      it feeds itself
    importer    it does not, but its stores and markets carry it
    expanding   hungry, with yards and open worlds in reach that it could eat on: its fleets go (an exodus
                sails even before the people is otherwise viable - famine is the oldest reason to emigrate)
    pressed     hungry, with yards and nowhere open to go: it takes food from others
    stranded    hungry, without yards: it can only take from its own system

A pressed or stranded people's council raids: the world in reach (or the starport - a hydration port, a fuel
dock) holding the most of its staple beyond the holder's own reserve, won with the odds of strength (garrison and
fighters against the defenders, or a port's law). Raids open wars over food, recorded in the chronicle and ended
by a long enough peace; necessity still darkens the raider (its civilization's alignment, or its owner's deed).
Hunger hardens a people; shared abundance lightens it: luminous peoples with a surplus of the same staple send
relief to hungry worlds in their reach, and giver and receiver both move toward the Light.

Players see the gauge and choose for themselves (POPULATION, then World # RAID); their worlds never raid alone.
Food only ever moves between holders here - nothing is created or destroyed.
"""

import random
import zlib
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import (
    DAUGHTER_CITADEL_TIER,
    DAUGHTER_MIN_HABITABILITY,
    FOOD_WAR_PEACE_QUARTERS,
    RELIEF_LIGHT_THRESHOLD,
    SUSTENANCE_RUNWAY_QUARTERS,
    SUSTENANCE_SMOOTHING,
)
from xylarium.kernel import staples, topology

HUNGRY = ("expanding", "pressed", "stranded")
RAIDERS = ("pressed", "stranded")


def _rng(*parts: Any) -> random.Random:
    return random.Random(zlib.crc32(":".join(str(p) for p in parts).encode()))


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "sustenance")


# ---------------------------------------------------------------------- peoples
def people_of(planet: Any) -> Optional[str]:
    """Who a world's people answer to: its owner, else its civilization, else its faction."""
    if planet.owner_id:
        return f"captain:{planet.owner_id}"
    civ = getattr(planet, "civilization", None)
    if civ is not None:
        return f"civ:{civ.name}"
    if getattr(planet, "faction_id", None):
        return f"faction:{planet.faction_id}"
    return None


def people_name(kernel: Any, key: Optional[str]) -> str:
    if not key:
        return "no one"
    kind, _, ident = key.partition(":")
    if kind == "captain":
        cap = kernel.captains.get(ident)
        return f"{cap.name}'s colonists" if cap is not None else ident
    if kind == "port":
        return ident
    return ident


def _alignment(kernel: Any, planet: Any) -> float:
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    if owner is not None:
        return float(getattr(owner, "cosmic_alignment", 0.0) or 0.0)
    civ = getattr(planet, "civilization", None)
    return float(getattr(civ, "alignment", 0.0) or 0.0) if civ is not None else 0.0


def _council(kernel: Any, planet: Any) -> bool:
    """Councils act for AI and indigenous worlds; players decide for their own."""
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    return owner is None or bool(getattr(owner, "is_ai", False))


def flow_civ(planet: Any, light: float = 0.0, dark: float = 0.0) -> None:
    """Lives a council-led people made or spared (light) or took (dark), into its history (alignment.flow)."""
    civ = getattr(planet, "civilization", None)
    if civ is not None and planet.owner_id is None:
        from xylarium.kernel import alignment
        alignment.flow(civ, light=light, dark=dark)


def yards(planet: Any) -> bool:
    """Yards that can launch: works enough - and, in a universe begun at its Big Bang, a people that can reach orbit
    from its own world at all (technology.py: its chemistry's or its atom's exhaust against its gravity)."""
    if planet.citadel_level < DAUGHTER_CITADEL_TIER:
        return False
    from xylarium.kernel import ledger
    k = ledger.active_kernel()
    if k is None or "technology" not in getattr(k, "state", {}):
        return True
    from xylarium.kernel import cosmos, mastery, technology
    if not cosmos.is_cosmic(k):
        return True
    who = people_of(planet)
    return technology.has(k, who, "orbit") or mastery.crossed(k, who)


def reach(kernel: Any, planet: Any) -> int:
    """How far this world's ships go: its settler fleets' reach with yards; its own system without."""
    if not yards(planet):
        return 0
    from xylarium.kernel import demography
    return demography.settler_reach(kernel, planet)


def open_worlds(kernel: Any, planet: Any) -> int:
    """Free worlds within this world's reach that its people could eat on (in the open, or under a dome)."""
    r = reach(kernel, planet)
    if r <= 0:
        return 0
    from xylarium.kernel import biosphere, cache, demography
    from xylarium.kernel.universe import habitability
    metab = biosphere.metabolism_of(kernel, planet)

    def count() -> int:
        n = 0
        for sid in topology.reach(kernel, planet.sector_id, r):
            for c in kernel.sectors[sid].planets:
                if demography.free_world(c) and (habitability(metab, c.planet_type) >= DAUGHTER_MIN_HABITABILITY
                                                 or c.planet_type != "GAS_GIANT" or metab == "plasmic"):
                    n += 1
        return n
    return cache.memo(kernel, "open_worlds", f"{planet.id}:{metab}:{r}", count, max_age=4 * _quarter())


# ---------------------------------------------------------------------- the gauge
def read(kernel: Any, planet: Any) -> Optional[Dict[str, Any]]:
    """Close the world's quarter: self-sufficiency, runway, hunger and its state."""
    soc = planet.society
    need = int(soc.pop("need_q", 0) or 0)
    harv = int(soc.pop("harvest_q", 0) or 0)
    short = int(soc.pop("short_q", 0) or 0)
    if need <= 0:
        return None
    ratio = harv / need
    prev = soc.get("self_sufficiency")
    ss = ratio if prev is None else prev + SUSTENANCE_SMOOTHING * (ratio - prev)
    soc["self_sufficiency"] = round(ss, 4)
    food = staples.of(kernel, planet)
    held = staples.held(planet, food)
    gap = max(0, need - harv)
    runway = held / gap if gap else float("inf")
    hungry = short > 0 or (ss < 1.0 and runway < SUSTENANCE_RUNWAY_QUARTERS)
    if not hungry:
        st = "secure" if ss >= 1.0 else "importer"
    elif not yards(planet):
        st = "stranded"
    elif open_worlds(kernel, planet) > 0:
        st = "expanding"
    else:
        st = "pressed"
    soc["sustenance"] = st
    return {"need": need, "harvest": harv, "short": short, "gap": gap, "staple": food, "held": held,
            "runway": runway, "state": st, "self_sufficiency": ss}


# ---------------------------------------------------------------------- relief and raids
def _targets(kernel: Any, planet: Any, food: str) -> List[Tuple[float, Any, Any, int]]:
    """(score, holder planet or None, port or None, seizable units) within the world's reach."""
    me = people_of(planet)
    hops = topology.hops(kernel, planet.sector_id, reach(kernel, planet))
    out = []
    for sid, d in hops.items():
        sec = kernel.sectors[sid]
        for w in sec.planets:
            if w is planet or people_of(w) == me or getattr(w, "natives", None) or relations.family(kernel, me, people_of(w)):
                continue                          # nor its patron, its tributaries, or anyone under the same root
            n = staples.surplus(kernel, w, food)
            if n > 0:
                out.append((n / (1.0 + d), w, None, n))
        port = sec.port
        if port is not None and port.stock.get(food, 0) > 0 and sid != 1:      # Sol's docks are untouchable
            n = port.stock.get(food, 0)
            out.append((n / (1.0 + d), None, port, n))
    out.sort(key=lambda t: -t[0])
    return out


def _strength(planet: Any) -> int:
    return max(0, int(planet.garrison_troops or 0)) + max(0, int(planet.fighters or 0))


def raid(kernel: Any, planet: Any, gauge: Optional[Dict[str, Any]] = None, plunder: bool = False) -> Optional[str]:
    """A hungry world takes its staple from the richest holder in its reach - if it wins the fight. A fed one may
    plunder: when the take, at its odds, is worth more to its council than the troops it expects to lose."""
    from xylarium.kernel import law
    st = stats(kernel)
    food = staples.of(kernel, planet)
    gap = (gauge or {}).get("gap") or max(1, (gauge or {}).get("need", 0))
    if not gauge:
        from xylarium.kernel import biosphere
        gap = biosphere.consumption(planet) * _quarter()
    want = int(gap * SUSTENANCE_RUNWAY_QUARTERS)
    targets = _targets(kernel, planet, food)
    if not targets or (want <= 0 and not plunder):
        return None
    _, victim, port, avail = targets[0]
    attack = _strength(planet)
    if victim is not None:
        defend = _strength(victim) + int(relations.shield(kernel, victim))     # its patron stands in the line
        where = kernel.sectors[victim.sector_id]
    else:
        where = kernel.sectors[port.sector_id]
        defend = int(100 * law.presence(kernel, where)) + 10
    if attack <= 0:
        return None
    if plunder:
        from xylarium.config import COMMODITY_CONFIG, PRICE_LEVEL, SURFACE_TROOP_RECRUIT_COST
        from xylarium.kernel import contact, decide
        want = avail
        level = PRICE_LEVEL.get(planet.currency, 1.0)
        gain = attack / (attack + defend) * avail * COMMODITY_CONFIG.get(food, {}).get("base_price", 20) * level
        loss = 0.1 * defend * SURFACE_TROOP_RECRUIT_COST * level
        them_people = people_of(victim) if victim is not None else None
        understood = contact.intelligibility(kernel, people_of(planet), them_people)
        m = contact.misread(decide.mind_of_planet(kernel, planet), understood)
        options = [decide.option("plunder", loss, gain)]
        if victim is not None:
            # parley: offer the victim protection for tribute instead - worth the tribute it would pay, as far as
            # the offer can be understood
            by = relations._peoples(kernel)
            t = relations._terms(kernel, them_people, people_of(planet), by, relations._pressed_share(kernel))
            if t is not None:
                rate = kernel.fx_market.rate(planet.currency) if planet.currency != "SOL" else 1.0
                options.append(decide.option("parley", 0.0, understood * t["tribute"] * rate))
        pick = decide.choose(kernel, options, m, planet.id, "plunder")
        if pick is None:
            return None
        if pick["name"] == "parley":
            contact.stats(kernel)["parleys"] += 1
            log = relations.offer(kernel, them_people, people_of(planet), relations._peoples(kernel))
            return log
        if loss > gain:
            contact.stats(kernel)["misread_raids"] += 1          # it would not have, had it understood its target
        st["plunders"] = st.get("plunders", 0) + 1
    st["raid_attempts_q"] = st.get("raid_attempts_q", 0) + 1
    by = st.setdefault("raids_by", {})
    by[people_of(planet) or "?"] = by.get(people_of(planet) or "?", 0) + 1
    # both sides bleed in proportion to the other's strength (Lanchester's linear law, a tenth per raid)
    planet.garrison_troops = max(0, planet.garrison_troops - int(0.1 * defend))
    if victim is not None:
        victim.garrison_troops = max(0, victim.garrison_troops - int(0.1 * attack))
    me, them = people_of(planet), (people_of(victim) if victim is not None else f"port:{port.name}")
    if _rng("food_raid", planet.id, kernel.cycle_count).random() >= attack / (attack + defend):
        st["repulsed"] += 1
        return f"[FOOD WAR] {people_name(kernel, me)} of {planet.name} raided for {food} and were driven off."
    take = min(want, avail)
    if victim is not None:
        staples.move(victim, food, -take)
        victim.morale = max(10, victim.morale - 5)
        victim.society["raided_cycle"] = kernel.cycle_count           # its council arms against it (society.py)
    else:
        port.stock[food] = port.stock.get(food, 0) - take
    staples.move(planet, food, take)                      # a transfer: the stores change hands
    st["raids"] += 1
    st["seized"][food] = st["seized"].get(food, 0) + take
    from xylarium.config import COMMODITY_CONFIG
    from xylarium.kernel import alignment
    taken = take * COMMODITY_CONFIG.get(food, {}).get("base_price", 20)
    # the stores change hands (a transfer); what the raid destroys is the hunger it leaves: the share of the take
    # the victim needed to keep its own people fed through the season (its reserve), in famine's arithmetic
    short = 0
    if victim is not None:
        short = min(take, max(0, staples.reserve(kernel, victim, food) - staples.held(victim, food)))
    starved = short * alignment.LIVES_PER_FOOD_UNIT
    if planet.owner_id:
        alignment.act(kernel, kernel.captains.get(planet.owner_id), "food_raid", harmed_sol=taken,
                      lives_lost=starved)
    else:
        flow_civ(planet, dark=starved)
        from xylarium.kernel import reputation          # the raided remember the whole take
        reputation.witness(kernel, them, me, dark=take * alignment.LIVES_PER_FOOD_UNIT)
    _war(kernel, planet, me, them, food, take, where.id)
    target = victim.name if victim is not None else f"the {port.name} docks"
    return f"[FOOD WAR] {people_name(kernel, me)} of {planet.name} seized {take:,} {food} from {target}."


def _war(kernel: Any, planet: Any, me: str, them: str, food: str, take: int, sector_id: int) -> None:
    st = stats(kernel)
    key = f"{me}>{them}"
    war = st["wars"].get(key)
    if war is None:
        war = st["wars"][key] = {"a": me, "b": them, "since": kernel.cycle_count, "raids": 0, "seized": 0,
                                 "staple": food}
        from xylarium.kernel import primordial
        primordial.first(kernel, "first_war", key)
        st["wars_begun"] += 1
        chron = getattr(kernel, "chronicle", None)
        if chron is not None:
            word = {"H2O": "Water", "H": "Hydrogen", "ORE": "Ore", "ORGANICS": "Grain"}.get(food, food)
            chron.record(kernel, "FOOD_WAR", planet.id, people_name(kernel, me),
                         f"The {word} War of {planet.name}",
                         f"Their harvests no longer fed them and no open world lay in reach. The people of "
                         f"{planet.name} went to take {food} from {people_name(kernel, them)}.",
                         sector_id=sector_id, tags=["sustenance", "war"], alignment=_alignment(kernel, planet))
    war["raids"] += 1
    war["seized"] += take
    war["last"] = kernel.cycle_count
    from xylarium.kernel import history
    history.event(kernel, "WAR" if war["raids"] == 1 else "RAID",
                  f"{people_name(kernel, me)} {'go to war with' if war['raids'] == 1 else 'raid'} {people_name(kernel, them)}",
                  actors=[me, them], planet=planet, sector_id=sector_id, magnitude=take,
                  cause=f"hunger: {food} the land no longer gave", data={"war": key, "raid": war["raids"]})


def _peace(kernel: Any) -> List[str]:
    st = stats(kernel)
    logs = []
    quiet = FOOD_WAR_PEACE_QUARTERS * _quarter()
    for key, war in list(st["wars"].items()):
        if kernel.cycle_count - war.get("last", war["since"]) >= quiet:
            del st["wars"][key]
            st["wars_ended"] += 1
            logs.append(f"[FOOD WAR] The war of {people_name(kernel, war['a'])} on {people_name(kernel, war['b'])} "
                        f"over {war['staple']} has ended ({war['raids']} raids, {war['seized']:,} seized).")
    return logs


def relieve(kernel: Any, planet: Any, gauge: Dict[str, Any]) -> Optional[str]:
    """Luminous peoples in reach holding the same staple send a hungry world what it lacks."""
    food = gauge["staple"]
    want = int(gauge["gap"] * SUSTENANCE_RUNWAY_QUARTERS) or int(gauge["need"])
    me = people_of(planet)
    best = None
    for sid, d in topology.hops(kernel, planet.sector_id, 6).items():
        for w in kernel.sectors[sid].planets:
            if w is planet or w.population <= 0 or not yards(w) or not _council(kernel, w):
                continue
            if _alignment(kernel, w) < RELIEF_LIGHT_THRESHOLD or reach(kernel, w) < d:
                continue
            # what it can share: half of what it holds beyond one season of its own (exports already sold the
            # rest of its surplus; a generous people dips into its own reserve)
            spare = max(0, staples.held(w, food) - staples.reserve(kernel, w, food) // 2) // 2
            if spare > 0 and (best is None or spare / (1 + d) > best[0]):
                best = (spare / (1 + d), w, spare)
    if best is None:
        return None
    _, donor, spare = best
    give = min(want, spare)
    staples.move(donor, food, -give)
    staples.move(planet, food, give)                      # a transfer: abundance shared
    st = stats(kernel)
    st["relief"] += 1
    st["relief_units"] += give
    from xylarium.config import COMMODITY_CONFIG
    from xylarium.kernel import alignment
    saved = give * alignment.LIVES_PER_FOOD_UNIT if gauge.get("short") else 0      # famine's own arithmetic
    helped = give * COMMODITY_CONFIG.get(food, {}).get("base_price", 20)
    if donor.owner_id:
        alignment.act(kernel, kernel.captains.get(donor.owner_id), "famine_aid", helped_sol=helped, lives_saved=saved)
    else:
        flow_civ(donor, light=saved)
    from xylarium.kernel import reputation
    reputation.witness(kernel, me, people_of(donor), light=saved)
    return (f"[RELIEF] {people_name(kernel, people_of(donor))} of {donor.name} sent {give:,} {food} to the hungry "
            f"of {planet.name} ({people_name(kernel, me)}).")


# ---------------------------------------------------------------------- the quarter
def quarter(kernel: Any) -> List[str]:
    logs: List[str] = []
    st = stats(kernel)
    gauges: List[Tuple[Any, Dict[str, Any]]] = []
    for sec in kernel.sectors.values():
        for planet in sec.planets:
            if planet.population <= 0 or getattr(planet, "natives", None):
                continue
            g = read(kernel, planet)
            if g is not None:
                gauges.append((planet, g))
    for planet, g in gauges:
        if g["state"] not in HUNGRY:
            continue
        st["hungry_quarters"] += 1
        log = relieve(kernel, planet, g)
        if log:
            logs.append(log)
            g["held"] = staples.held(planet, g["staple"])
            g["runway"] = g["held"] / g["gap"] if g["gap"] else float("inf")
            if g["runway"] >= SUSTENANCE_RUNWAY_QUARTERS:
                planet.society["sustenance"] = g["state"] = "importer"
                continue
                                                                        # scarcity hardens a people, as far as it bites
            from xylarium.kernel import introspect
            if _council(kernel, planet) and not introspect.restrained(kernel, planet):   # unless it chose peace
                log = raid(kernel, planet, g)
                if log:
                    logs.append(log)
    # the fed may still prey on the weak where their ships reach - a choice, weighed like any other
    from xylarium.kernel import introspect
    for planet, g in gauges:
        if g["state"] in HUNGRY or not yards(planet) or not _council(kernel, planet) or \
                introspect.restrained(kernel, planet):
            continue
        log = raid(kernel, planet, g, plunder=True)
        if log:
            logs.append(log)
    # the measured rate at which worlds attack, a season (what every people reads as its neighbours' threat)
    hist = st.setdefault("raid_rate_hist", [])
    hist.append(st.get("raid_attempts_q", 0) / max(1, len(gauges)))
    del hist[:-4]
    st["raid_attempts_q"] = 0
    logs += _peace(kernel)
    return logs


# ---------------------------------------------------------------------- census
def census(kernel: Any) -> Dict[str, Any]:
    """By metabolism: peoples, people, worlds, the sectors they reach, self-sufficiency and states."""
    from xylarium.kernel import biosphere
    out: Dict[str, Dict[str, Any]] = {}
    peoples: Dict[str, Dict[str, Any]] = {}
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population <= 0 or getattr(p, "natives", None):
                continue
            metab = biosphere.metabolism_of(kernel, p)
            m = out.setdefault(metab, {"staple": staples.of_metabolism(metab), "people": 0, "worlds": 0,
                                       "sectors": set(), "ss_sum": 0.0, "states": {}, "peoples": set()})
            m["people"] += p.population
            m["worlds"] += 1
            m["sectors"].add(sec.id)
            m["ss_sum"] += float(p.society.get("self_sufficiency", 1.0)) * p.population
            s = p.society.get("sustenance", "secure")
            m["states"][s] = m["states"].get(s, 0) + 1
            key = people_of(p)
            if key:
                m["peoples"].add(key)
                pe = peoples.setdefault(key, {"worlds": 0, "yards": False})
                pe["worlds"] += 1
                pe["yards"] = pe["yards"] or yards(p)
    for metab, m in out.items():
        keys = m.pop("peoples")
        m["sectors"] = len(m["sectors"])
        m["self_sufficiency"] = round(m.pop("ss_sum") / max(1, m["people"]), 3)
        m["peoples"] = len(keys)
        m["off_world"] = sum(1 for k in keys if peoples[k]["worlds"] > 1)      # made it off their first world
    return out


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"by_metabolism": census(kernel), "raids": st["raids"], "repulsed": st["repulsed"],
            "seized": dict(st["seized"]), "relief": st["relief"], "relief_units": st["relief_units"],
            "wars_active": len(st["wars"]), "wars_begun": st["wars_begun"], "wars_ended": st["wars_ended"],
            "hungry_quarters": st["hungry_quarters"], "exodus": st["exodus"]}


from xylarium.kernel import relations, state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="sustenance",
    state=lambda: {"raids": 0, "repulsed": 0, "seized": {}, "relief": 0, "relief_units": 0, "wars": {},
                   "wars_begun": 0, "wars_ended": 0, "hungry_quarters": 0, "exodus": 0},
    season=quarter,
    summary=summary,
))
