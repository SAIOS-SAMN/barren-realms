"""
Xylarium covert: what reaches a people that no open contact reaches - statecraft in the dark.

A quarantined people (ascendance.py) makes no open contact: no meeting, no treaty, no trade beyond its own kin. That
does not make it unreachable. It can be seen (the universe is not a dark forest); it can be sailed to; and those who
sail to it in secret answer only to whoever catches them. Three operations emerge, each a people's own council's
choice (decide.choose) - never a fixed chance - and each judged by its whole cost:

  EXPLOIT   take what a quarantined people's worlds hold beyond what they keep (staples.surplus): their resources,
            carried off by a people that can reach them. Worth: the goods at the market's price. A taking: its value
            in lives is written into the taker's history (dark) whether or not anyone sees it.
  STIFLE    a people that profits from another's quarantine (it has exploited it) may keep it down: erase what it
            learned this year - as far as the stifler's information mastery outweighs its own (A / (A + T)). Worth:
            the exploitation it protects, over its horizon. Dark, as the taking it guards.
  SMUGGLE   a trade a lane bars (a blockade, an embargo) or a quarantine closes (commerce.py) may still move: the
            buyer judges the goods' worth against their price and what it stands to lose if caught.

CONSCIENCE. Taking and stifling cost a council what its people's character makes of them: the Light counts the whole
of what it takes as a cost (it never profits by it), absolute darkness nothing - as the realm-war reckoning counts
the order it destroys (realmwars.weigh).

THE WATCH (the steward's counter-operation). Who can catch an operation: the people it is done to, and the stewards
of the realm it is done in - the envoys of its keeper and of its keeper's federation partners, never the operator's
own (a keeper that preys on its own wards answers to its partners' stewards, or to no one but its victims) - each as
far as its information mastery outweighs the operator's,
W / (W + A); caught if either catches it. Whether it is caught is this universe's own truth (the seed's stream,
scheduler.rng), not a die: the operator weighs the chance; what happens, happens.

CAUGHT. The operation fails (exploit: nothing taken; smuggle: the goods are seized by the watcher); the victim and the
keeper witness it (reputation: lives taken); and the realm SANCTIONS the operator for a steward's term: every lane its
keeper's web holds turns it back (transit.blocks). A covert power that is never caught pays only its conscience.
"""

from typing import Any, Dict, List, Optional, Tuple

KINDS = ("exploit", "stifle", "smuggle")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "covert")


# ---------------------------------------------------------------------- the watch
def _info(kernel: Any, who: Optional[str]) -> float:
    from xylarium.kernel import knowledge
    if not who or "knowledge" not in getattr(kernel, "state", {}):
        return 0.0
    return float(knowledge.experience(kernel, who, "information"))


def catch(kernel: Any, actor: str, watchers: List[Optional[str]]) -> float:
    """The chance an operation is caught: each watcher as far as its information mastery outweighs the operator's."""
    a = _info(kernel, actor)
    miss = 1.0
    for w in {x for x in watchers if x and x != actor}:
        t = _info(kernel, w)
        miss *= 1.0 - (t / (t + a) if t + a > 0 else 0.5)
    return 1.0 - miss


def _caught(kernel: Any, p: float, *salt: Any) -> bool:
    from xylarium.kernel import scheduler
    return scheduler.rng(kernel, "covert", kernel.cycle_count, *salt).random() < p


def sanctioned(kernel: Any, who: Optional[str], holder: Optional[str]) -> bool:
    """Is a people under a realm's sanction where this lane's holder stands in that realm keeper's web?"""
    if not who or not holder or "covert" not in getattr(kernel, "state", {}):
        return False
    from xylarium.kernel import realmwars
    for s in stats(kernel)["sanctions"].get(who, []):
        if s["until"] > kernel.cycle_count and (holder == s["keeper"] or holder in realmwars._web(kernel, s["keeper"])):
            return True
    return False


def _watch(kernel: Any, target: str, actor: str) -> Tuple[List[str], Optional[str], Optional[str]]:
    """Who keeps watch over a people the stewards hold at home: the stewards of its realm - the envoys of its keeper and
    of its keeper's federation partners (stewardship.senders_of) - save the operator's own. -> (watchers, the one that
    sanctions, the realm)."""
    from xylarium.kernel import ascendance, stewardship
    rec = ascendance.stats(kernel)["of"].get(target) if "ascendance" in kernel.state else None
    if rec is None:
        return [], None, None
    eyes = [w for w in stewardship.senders_of(kernel, rec["realm"]) if w != actor]
    return eyes, (eyes[0] if eyes else None), rec["realm"]


def _expose(kernel: Any, actor: str, victim: Optional[str], keeper: Optional[str], kind: str, value: float,
            realm: Optional[str], logs: List[str]) -> None:
    from xylarium.kernel import alignment, history, reputation, spheres, stewardship
    home = spheres._home(kernel, actor)
    lives = alignment.lives_of_sol(kernel, value, home)
    for w in (victim, keeper):
        reputation.witness(kernel, w, actor, dark=lives)
    if keeper:
        span = stewardship.span_cycles(kernel, realm) if realm else 4 * _quarter()
        stats(kernel)["sanctions"].setdefault(actor, []).append(
            {"keeper": keeper, "realm": realm, "until": kernel.cycle_count + span, "for": kind})
    stats(kernel)["caught"][kind] = stats(kernel)["caught"].get(kind, 0) + 1
    history.event(kernel, "COVERT_EXPOSED", f"The {actor.split(':', 1)[-1]} caught at {kind}"
                  + (f" against the {victim.split(':', 1)[-1]}" if victim else ""),
                  actors=[actor] + ([victim] if victim else []), cause="the watch caught it: the realm sanctions it",
                  data={"kind": kind, "value": round(value, 1), "keeper": keeper})
    logs.append(f"[COVERT] The {actor.split(':', 1)[-1]} are caught at {kind}; sanctioned"
                + (f" by {stewardship.realm_name(realm)}." if realm else "."))


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


# ---------------------------------------------------------------------- what an operation costs its council
def _light(kernel: Any, who: str) -> float:
    """1 the Light (it counts all it takes as a cost), 0 absolute darkness (nothing)."""
    from xylarium.kernel import alignment, spheres
    home = spheres._home(kernel, who)
    civ = getattr(home, "civilization", None) if home is not None else None
    return (1.0 + alignment.character(civ)) / 2.0 if civ is not None else 0.5


def _exposure(kernel: Any, who: str, realm: Optional[str]) -> float:
    """What a sanction would cost a people: its trade (a year of commerce bought and sold) over the term it lasts."""
    if "commerce" not in getattr(kernel, "state", {}):
        return 0.0
    from xylarium.kernel import commerce, stewardship
    t = commerce.stats(kernel)["peoples"].get(who, {})
    years = stewardship.span_cycles(kernel, realm) / (4.0 * _quarter()) if realm else 1.0
    return float(t.get("sold", 0.0) + t.get("bought", 0.0)) * years


def _route_cost(kernel: Any, a: Any, b: Any) -> Tuple[Optional[int], float]:
    from xylarium.kernel import relations, sustenance, transit
    hops = relations._hops_between(kernel, a, b)
    if hops is None or hops > sustenance.reach(kernel, a):
        return None, 0.0
    return hops, hops * transit._typical_hop(kernel)


# ---------------------------------------------------------------------- the operations
def _held_down(kernel: Any) -> List[str]:
    from xylarium.kernel import ascendance
    if "ascendance" not in kernel.state:
        return []
    return sorted(w for w, r in ascendance.stats(kernel)["of"].items() if r["ruling"] == "quarantine")


def _operators(kernel: Any) -> List[Tuple[str, Any]]:
    """Every free people that can sail: its seat."""
    from xylarium.kernel import ascendance, relations, spheres, sustenance
    out = []
    for who in sorted(relations._peoples(kernel)):
        if not who.startswith("civ:") or not ascendance.free(kernel, who):
            continue
        home = spheres._home(kernel, who)
        if home is not None and sustenance.yards(home):
            out.append((who, home))
    return out


def exploit(kernel: Any, actor: str, home: Any, target: str, logs: List[str]) -> float:
    """Weigh, and perhaps carry off, what a quarantined people holds beyond what it keeps. Returns the SOL taken."""
    from xylarium.kernel import alignment, commerce, decide, history, relations, staples, sustenance, transit
    worlds = relations._peoples(kernel).get(target) or []
    if not worlds:
        return 0.0
    hops, fuel = _route_cost(kernel, home, worlds[0])
    if hops is None:
        return 0.0
    lots = [(w, c, staples.surplus(kernel, w, c)) for w in worlds for c in commerce._goods(kernel, w)]
    lots = [(w, c, q) for w, c, q in lots if q > 0]
    value = sum(q * transit.price(kernel, c) for _, c, q in lots)
    if value <= 0:
        return 0.0
    eyes, keeper, realm = _watch(kernel, target, actor)
    p = catch(kernel, actor, [target] + eyes)
    m = decide.mind_of_planet(kernel, home)
    cost = fuel + _light(kernel, actor) * value + p * _exposure(kernel, actor, realm)
    if decide.choose(kernel, [decide.option("exploit", cost, (1 - p) * value)], m, actor, target, "exploit") is None:
        return 0.0
    st = stats(kernel)
    st["tried"]["exploit"] = st["tried"].get("exploit", 0) + 1
    if _caught(kernel, p, actor, target, "exploit"):
        _expose(kernel, actor, target, keeper, "exploit", value, realm, logs)
        return 0.0
    for w, c, q in lots:
        staples.move(w, c, -q)
        staples.move(home, c, q)
    sustenance.flow_civ(home, dark=alignment.lives_of_sol(kernel, value, home), why="covert")
    st["done"]["exploit"] = st["done"].get("exploit", 0) + 1
    st["taken"].setdefault(actor, {})[target] = round(value, 1)
    history.event(kernel, "EXPLOITED", f"The {target.split(':', 1)[-1]}'s stores carried off in secret",
                  actors=[actor, target], cause="a quarantined people makes no open contact; a covert one is unseen",
                  data={"value": round(value, 1), "covert": True})
    logs.append(f"[COVERT] Unseen hands carry off {value:,.0f} SOL of the {target.split(':', 1)[-1]}'s stores.")
    return value


def stifle(kernel: Any, actor: str, home: Any, target: str, logs: List[str]) -> float:
    """A people that profits from another's quarantine may keep it down: erase what it learned this year, as far as
    its own information mastery outweighs the target's. Returns the share of the year's learning erased."""
    from xylarium.kernel import alignment, decide, history, knowledge, sustenance
    take = stats(kernel)["taken"].get(actor, {}).get(target, 0.0)
    if take <= 0:
        return 0.0
    was = stats(kernel)["known"].get(target)
    now = knowledge.stocks(kernel, target)
    gained = {d: now.get(d, 0.0) - was.get(d, 0.0) for d in now} if was else {}
    if not gained or sum(max(0.0, g) for g in gained.values()) <= 0:
        return 0.0
    a, t = _info(kernel, actor), _info(kernel, target)
    share = a / (a + t) if a + t > 0 else 0.5
    eyes, keeper, realm = _watch(kernel, target, actor)
    p = catch(kernel, actor, [target] + eyes)
    m = decide.mind_of_planet(kernel, home)
    worth = decide.worth(kernel, take / 4.0, m)                     # the exploitation it protects, over its horizon
    cost = _light(kernel, actor) * worth + p * _exposure(kernel, actor, realm)
    if decide.choose(kernel, [decide.option("stifle", cost, (1 - p) * share * worth)], m, actor, target,
                     "stifle") is None:
        return 0.0
    st = stats(kernel)
    st["tried"]["stifle"] = st["tried"].get("stifle", 0) + 1
    if _caught(kernel, p, actor, target, "stifle"):
        _expose(kernel, actor, target, keeper, "stifle", take, realm, logs)
        return 0.0
    for d, g in gained.items():
        if g > 0:
            now[d] = now[d] - g * share
    sustenance.flow_civ(home, dark=alignment.lives_of_sol(kernel, share * take, home), why="covert")
    st["done"]["stifle"] = st["done"].get("stifle", 0) + 1
    history.event(kernel, "STIFLED", f"What the {target.split(':', 1)[-1]} learned this year is undone",
                  actors=[actor, target], cause="a power that profits from their quarantine keeps them down, unseen",
                  data={"share": round(share, 3), "covert": True})
    logs.append(f"[COVERT] The {target.split(':', 1)[-1]} lose {share:.0%} of a year's learning to unseen hands.")
    return share


def smuggle(kernel: Any, buyer: str, seller: str, bw: Any, sw: Any, comm: str, q: int, worth: float, unit: float,
            logs: Optional[List[str]] = None) -> int:
    """A trade its route bars, moved in secret - if the buyer judges the goods worth what it stands to lose."""
    from xylarium.kernel import ascendance, commerce, decide, staples, transit
    path = kernel.find_path(sw.sector_id, bw.sector_id) or []
    watchers = {transit.owner(kernel, a, b) for a, b in zip(path, path[1:])
                if transit.blocks(kernel, buyer, a, b) or transit.blocks(kernel, seller, a, b)}
    realm = None
    for who in (buyer, seller):
        if ascendance.ruling(kernel, who) == "quarantine":
            eyes, _, realm = _watch(kernel, who, buyer)
            watchers.update(eyes)
    watchers.discard(None)
    watchers.discard(buyer)
    p = catch(kernel, buyer, sorted(watchers))
    rate = commerce._rate(kernel, bw.currency)
    q = min(q, int(float(bw.treasury) / rate / max(1e-9, unit)))
    if q <= 0:
        return 0
    m = decide.mind_of_planet(kernel, bw)
    cost = q * unit + p * _exposure(kernel, buyer, realm)
    if decide.choose(kernel, [decide.option("smuggle", cost, (1 - p) * q * worth)], m, bw.id, sw.id, comm,
                     "smuggle") is None:
        return 0
    st = stats(kernel)
    st["tried"]["smuggle"] = st["tried"].get("smuggle", 0) + 1
    if _caught(kernel, p, buyer, seller, comm, "smuggle"):
        seizer = sorted(watchers)[0] if watchers else None
        from xylarium.kernel import spheres
        at = spheres._home(kernel, seizer) if seizer else None
        if at is not None:
            staples.move(sw, comm, -q)
            staples.move(at, comm, q)                                # the goods seized by the watch
        _expose(kernel, buyer, None, seizer, "smuggle", q * unit, realm, logs if logs is not None else [])
        return 0
    price = int(q * unit * rate)
    bw.treasury -= price
    sw.treasury += commerce._to(kernel, bw.currency, sw.currency, price)
    staples.move(sw, comm, -q)
    staples.move(bw, comm, q)
    st["done"]["smuggle"] = st["done"].get("smuggle", 0) + 1
    st["smuggled"] += q * unit
    return q


def season(kernel: Any) -> List[str]:
    """Once a year: every free people that can sail weighs the quarantined peoples within its reach - to exploit, and
    to keep down what it exploits; what each target learned is noted for the next year."""
    from xylarium.kernel import knowledge, polity
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    logs: List[str] = []
    st = stats(kernel)
    targets = _held_down(kernel)
    if targets:
        for actor, home in _operators(kernel):
            for target in targets:
                if target == actor:
                    continue
                stifle(kernel, actor, home, target, logs)
                exploit(kernel, actor, home, target, logs)
    st["known"] = {t: dict(knowledge.stocks(kernel, t)) for t in targets} if "knowledge" in kernel.state else {}
    for who in list(st["sanctions"]):
        st["sanctions"][who] = [s for s in st["sanctions"][who] if s["until"] > kernel.cycle_count]
        if not st["sanctions"][who]:
            st["sanctions"].pop(who)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"tried": dict(st["tried"]), "done": dict(st["done"]), "caught": dict(st["caught"]),
            "sanctioned": sorted(st["sanctions"]), "smuggled": round(st["smuggled"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="covert",
    state=lambda: {"tried": {}, "done": {}, "caught": {}, "sanctions": {}, "taken": {}, "known": {}, "smuggled": 0.0},
    season=season,
    summary=summary,
))
