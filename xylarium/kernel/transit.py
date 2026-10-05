"""
Xylarium transit: the lanes the networks hold open, what passing them costs, and the wormholes of the Einstein-Cartan
fabric - the spacing guild's trade.

LANES AND THEIR TOLLS. A lane whose two ends one network holds (spheres.py) is that network's: its people opened the
passage, and its people take a toll from those who pass. No fee is laid down. What a passage is worth is set by the
economies at stake:

  FLOOR     what holding the passage open cost its owner and has not yet been paid back: the energy of a passage
            (mastery.E_BRIDGE_J) at the price energy trades at (antimatter, the market's own price, per joule), less
            what the lane has collected, spread over the traffic it carried last year
  CEILING   what the lane saves the one passing: the cheapest way around it (fibres' lane costs, the lane itself
            removed) less the lane, in hops - each hop priced at what the passer's own drive burns (its fuel at the
            market's price; a warp core's wear) - or, where there is no way around, all it carries
  TOLL      between them, at the price that takes the most from a passer whose willingness falls evenly from the
            ceiling to nothing (the revenue-maximizing price under that demand: half way) - and never above the
            ceiling: no one pays more than going round. A rival network's way round caps it.

Peoples of the owning network, and its federation and conglomerate partners, pass free. What is paid goes to the
owner's capital world's treasury, in its money; and what a network collects pays for more passages (spheres.py): a
guild that carries traffic grows by it.

WORMHOLES. Where matter is dense enough that spin-torsion bounces it (Einstein-Cartan: the black holes, a sink here
and a white hole beyond - blackhole.py), the fabric has a mouth. The galactic centre is one; so is every black hole a
heavy star leaves (cosmos.BLACK_HOLE_SUNS); so is every other galaxy's centre - galaxies are spheres stacked on their
bounces. A throat joins mouth to mouth: each star's hole to its galaxy's centre (the long haul), the centre to every
other galaxy's centre (across the void). Through the bounce a ship is carried on the torsion's own repulsion, its
mass undistorted, its clock dilated: a throat is crossed in one hop, as cheap as the cheapest lane.

  MASTERY   no one passes a throat until a people devises how: an ancient people (board.ancient_peoples) - the core's
            first, whose own reach makes it to the core (its network's reach at least its home's distance from the
            centre) - masters the bounce. It holds every throat whose mouth its network reaches, and the centre's
  HANDLING  its own choice, read from what it is (federation.preferred_card of its whole-history doctrine):
            ALPHA open (only the floor: what the throat cost), BETA/GAMMA tolled (the toll law), DELTA guarded (its
            own and its bonded only). A player's progenitor sets its own (command.py)
  FORGING   a progenitor line may punch a stabilised throat of its own from a mouth its network holds to the
            busiest system of the galaxy it can reach (time as distance: where the most traffic loses the most hops
            going round). It costs a passage held open for each hop it replaces, every year of one of its stewards'
            terms - paid from the energy its network banks when it has nothing left within its charts to reach.
            The line decides by its own mind (mindcore): its book FLOW; the deed FORGE; what it delivered sealed.
"""

import heapq
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import mindcore as mc

MOUTH_BASE = 9_000_000          # sector ids for mouths beyond the charts: the centre, then the other galaxies' centres
HANDLING = {"ALPHA": "open", "BETA": "tolled", "GAMMA": "tolled", "DELTA": "guarded"}
FREE_BONDS = ("federation", "conglomerate")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "transit")


def key(a: int, b: int) -> str:
    return f"{min(a, b)}-{max(a, b)}"


# ---------------------------------------------------------------------- what things cost, by the market
def price(kernel: Any, commodity: str) -> float:
    """What a commodity trades at: the mean of the ports' own prices (mid of buy and sell), its listed price where
    nothing trades it."""
    from xylarium.config import COMMODITY_CONFIG
    from xylarium.kernel import cache
    from xylarium.kernel.economy import EconomyManager

    def build() -> float:
        got = []
        for sec in kernel.sectors.values():
            port = getattr(sec, "port", None)
            if port is None:
                continue
            try:
                buy, sell = EconomyManager.get_unit_prices(port, commodity)
            except Exception:
                continue
            if buy > 0 and sell > 0:
                got.append((buy + sell) / 2.0)
        return sum(got) / len(got) if got else float(COMMODITY_CONFIG.get(commodity, {}).get("base_price", 0) or 0)
    if not hasattr(kernel, "caches"):
        return build()
    return cache.memo(kernel, "transit_price", commodity, build, epoch=kernel.cycle_count // 25)


def credits_per_joule(kernel: Any) -> float:
    """Energy's price: antimatter's, over the energy a cell holds."""
    from xylarium.kernel import energy, mastery
    return price(kernel, "AM") / (energy.ANTIMATTER_EU * mastery._eu_j())


def passage_cr(kernel: Any) -> float:
    """What a passage's energy is worth at the market's price."""
    from xylarium.kernel import mastery
    return mastery.E_BRIDGE_J * credits_per_joule(kernel)


def hop_value(kernel: Any, captain: Any) -> float:
    """What a hop costs this passer: the reaction mass its drive burns at the market's price, or its warp core's
    wear (a core's price over the jumps it lasts)."""
    from xylarium.kernel import propulsion
    ship = captain.ship
    fuel = propulsion.fuel_of(ship)
    if fuel:
        return propulsion.burn_for(ship) * price(kernel, fuel)
    return price(kernel, "M4_WARP_CORE") / max(1, int(propulsion.drive_of(ship).get("core_life", 400)))


# ---------------------------------------------------------------------- who holds a lane
def worm(kernel: Any, a: int, b: int) -> Optional[Dict[str, Any]]:
    return stats(kernel)["worms"].get(key(a, b)) if hasattr(kernel, "state") else None


def owner(kernel: Any, a: int, b: int) -> Optional[str]:
    """A throat's holder; a lane's - the network holding both its ends - or no one."""
    w = worm(kernel, a, b)
    if w is not None:
        return w["owner"]
    from xylarium.kernel import spheres
    pa = spheres.presence(kernel, spheres.owner(kernel, a))
    pb = spheres.presence(kernel, spheres.owner(kernel, b))
    return pa if pa is not None and pa == pb else None


def _payer(kernel: Any, captain: Any) -> Optional[str]:
    from xylarium.kernel import stewardship
    return stewardship.party(kernel, f"captain:{captain.id}")


def _free(kernel: Any, payer: Optional[str], holder: str) -> bool:
    from xylarium.kernel import spheres
    if payer == holder:
        return True
    b = spheres.bond(kernel, payer, holder) if payer else None
    return b is not None and b["kind"] in FREE_BONDS


def refuses(kernel: Any, captain: Any, a: int, b: int) -> bool:
    """A guarded throat turns back all but its holder's own and its bonded; a closed one, everyone."""
    w = worm(kernel, a, b)
    if w is None:
        return False
    if w.get("handling") == "closed":
        return True
    if w.get("handling") == "guarded":
        from xylarium.kernel import spheres
        payer = _payer(kernel, captain)
        return not (payer == w["owner"] or (payer and spheres.bond(kernel, payer, w["owner"]) is not None))
    return False


def worm_cost(kernel: Any, a: int, b: int) -> Optional[float]:
    """A throat's cost to the galaxy's routes: the cheapest a lane can be - or none to the shared routes when it is
    guarded or closed (only its own pass, and they choose it themselves)."""
    w = worm(kernel, a, b)
    if w is None:
        return None
    from xylarium.kernel import fibres
    return float("inf") if w.get("handling") in ("guarded", "closed") else fibres.MIN_COST


# ---------------------------------------------------------------------- the toll
def _around(kernel: Any, a: int, b: int) -> float:
    """The cheapest way from a to b without the lane between them (fibres' costs), memoized per cost version."""
    from xylarium.kernel import cache, fibres
    st = fibres.state(kernel)
    version = (st.get("version", 0), st.get("seasons", 0), len(kernel.sectors),
               sum(len(sec.warps) for sec in kernel.sectors.values()))

    def build() -> float:
        dist = {a: 0.0}
        heap: List[Tuple[float, int]] = [(0.0, a)]
        while heap:
            d, s = heapq.heappop(heap)
            if s == b:
                return d
            if d > dist.get(s, float("inf")):
                continue
            for w in kernel.sectors[s].warps:
                if w not in kernel.sectors or {s, w} == {a, b}:
                    continue
                nd = d + fibres.lane_cost(kernel, s, w)
                if nd < dist.get(w, float("inf")):
                    dist[w] = nd
                    heapq.heappush(heap, (nd, w))
        return float("inf")
    if not hasattr(kernel, "caches"):
        return build()
    return cache.memo(kernel, "transit_around", key(a, b), build, epoch=version)


def lane(kernel: Any, a: int, b: int) -> Dict[str, Any]:
    st = stats(kernel)
    rec = st["lanes"].get(key(a, b))
    if rec is None:
        w = worm(kernel, a, b)
        rec = st["lanes"][key(a, b)] = {"cost_cr": float(w["cost_cr"]) if w else passage_cr(kernel),
                                        "collected": 0.0, "transits": 0, "year": 0, "last_year": 0}
    return rec


def quote(kernel: Any, captain: Any, a: int, b: int) -> Dict[str, Any]:
    """What passing a lane costs this passer, and why."""
    from xylarium.kernel import fibres
    holder = owner(kernel, a, b)
    if holder is None or _free(kernel, _payer(kernel, captain), holder):
        return {"owner": holder, "toll": 0.0, "floor": 0.0, "ceiling": 0.0}
    rec = lane(kernel, a, b)
    floor = max(0.0, rec["cost_cr"] - rec["collected"]) / max(1, rec["last_year"])
    around = _around(kernel, a, b)
    if around == float("inf"):
        ceiling = fibres.cargo_value(captain) + hop_value(kernel, captain)      # no way round: all it carries
    else:
        ceiling = max(0.0, around - fibres.lane_cost(kernel, a, b)) * hop_value(kernel, captain)
    w = worm(kernel, a, b)
    if w is not None and w.get("handling") == "open":
        toll = min(floor, ceiling)
    else:
        toll = min(ceiling, floor + max(0.0, ceiling - floor) / 2.0)
    return {"owner": holder, "toll": toll, "floor": floor, "ceiling": ceiling}


def on_passage(kernel: Any, captain: Any, a: int, b: int) -> int:
    """A ship passes a lane: it pays the lane's holder what the lane is worth to it (what it can)."""
    q = quote(kernel, captain, a, b)
    if not q["owner"]:
        return 0
    rec = lane(kernel, a, b)
    rec["transits"] += 1
    rec["year"] += 1
    amt = int(min(q["toll"], max(0, captain.credits)))
    if amt <= 0:
        return 0
    captain.credits -= amt
    _pay_owner(kernel, q["owner"], amt)
    rec["collected"] += amt
    st = stats(kernel)
    st["revenue"][q["owner"]] = st["revenue"].get(q["owner"], 0.0) + amt
    st["paid"] += amt
    if hasattr(kernel, "action_logs"):
        kernel.action_logs.append(f"[TRANSIT] {captain.name} pays the {q['owner'].split(':', 1)[-1]} {amt:,} Cr "
                                  f"to pass {a}<->{b}.")
    return amt


def _pay_owner(kernel: Any, who: str, amount: int) -> None:
    """Into the holder's capital world's treasury, in its money."""
    from xylarium.kernel import spheres
    home = spheres._home(kernel, who)
    if home is None:
        from xylarium.kernel import ledger
        ledger.pay_service(amount, institution="transit")
        return
    from xylarium.kernel.fx import ACTIVE_FX
    if home.currency != "SOL" and ACTIVE_FX is not None:
        home.treasury += ACTIVE_FX.swap_sol_to(home.currency, amount)
    else:
        home.treasury += amount


def drain_revenue(kernel: Any, who: str) -> Fraction:
    """What a network collected since last asked, in passages (it pays for more of them)."""
    st = stats(kernel)
    got = st["revenue"].pop(who, 0.0) if hasattr(kernel, "state") else 0.0
    per = passage_cr(kernel)
    return Fraction(got) / Fraction(per) if got > 0 and per > 0 else Fraction(0)


def gate_fee(kernel: Any, captain: Any, gate: Any) -> int:
    """A toll gate's fee where its owner has set none: the same law - its own cost unrecovered as the floor, what the
    shortcut saves this passer as the ceiling."""
    from xylarium.config import TOLL_GATE_DEPLOY_COST_CREDITS
    from xylarium.kernel import fibres
    floor = max(0.0, TOLL_GATE_DEPLOY_COST_CREDITS - float(gate.total_revenue)) / max(1, gate.total_transits)
    around = _around(kernel, gate.sector_a, gate.sector_b)
    ceiling = (fibres.cargo_value(captain) + hop_value(kernel, captain) if around == float("inf") else
               max(0.0, around - fibres.lane_cost(kernel, gate.sector_a, gate.sector_b)) * hop_value(kernel, captain))
    return int(min(ceiling, floor + max(0.0, ceiling - floor) / 2.0))


# ---------------------------------------------------------------------- the mouths and throats
def _centre_sector(kernel: Any) -> Optional[int]:
    """The galactic centre's mouth, put on the map when first reached (a cosmic galaxy only)."""
    from xylarium.kernel import cosmos
    if not cosmos.is_cosmic(kernel):
        return None
    return _mint(kernel, MOUTH_BASE, "The Galactic Centre", "the core's own black hole")


def _galaxy_sector(kernel: Any, i: int) -> Optional[int]:
    from xylarium.kernel import cluster
    gals = cluster.stats(kernel).get("galaxies") or []
    if i <= 0 or i >= len(gals):
        return None
    return _mint(kernel, MOUTH_BASE + i, f"The Heart of {gals[i]['name']}", f"the centre of {gals[i]['name']}")


def _mint(kernel: Any, sid: int, name: str, what: str) -> int:
    from xylarium.kernel.models import Sector, SecurityLevel
    if sid not in kernel.sectors:
        sec = Sector(id=sid, name=name, security=SecurityLevel.ANARCHY, warps=[], port=None, planets=[], captains=[])
        sec.kind, sec.star_type, sec.star = "NULL", "Black hole", None
        sec.cluster_name = what
        kernel.sectors[sid] = sec
    return sid


def mouths(kernel: Any) -> Dict[int, Dict[str, Any]]:
    """Where the fabric has a mouth: every black hole a heavy star left, the centre, the other galaxies' centres
    (those already put on the map)."""
    from xylarium.kernel import blackhole, cluster
    out: Dict[int, Dict[str, Any]] = {}
    for sid, sec in kernel.sectors.items():
        if "black hole remnant" in (getattr(sec, "star_type", "") or "").lower():
            out[sid] = {"kind": "stellar"}
    if MOUTH_BASE in kernel.sectors:
        out[MOUTH_BASE] = {"kind": "centre", "mass_suns": blackhole.stats(kernel).get("mass")}
    gals = cluster.stats(kernel).get("galaxies") or []
    for i in range(1, len(gals)):
        if MOUTH_BASE + i in kernel.sectors:
            out[MOUTH_BASE + i] = {"kind": "galaxy", "mass_suns": gals[i]["mass"], "galaxy": gals[i]["name"]}
    return out


def open_throat(kernel: Any, a: int, b: int, who: str, kind: str, cost_cr: float, why: str) -> Dict[str, Any]:
    """A throat joins two mouths on the map: a lane each way, held by `who`, handled as it chooses."""
    from xylarium.kernel import fibres, history, topology
    st = stats(kernel)
    k = key(a, b)
    if k in st["worms"]:
        return st["worms"][k]
    for x, y in ((a, b), (b, a)):
        if y not in kernel.sectors[x].warps:
            kernel.sectors[x].warps.append(y)
    w = st["worms"][k] = {"a": a, "b": b, "owner": who, "kind": kind, "opened": kernel.cycle_count,
                          "cost_cr": float(cost_cr), "handling": handling_of(kernel, who)}
    topology.changed(kernel)
    fibres._bump(kernel)
    history.event(kernel, "WORMHOLE", f"A throat opens between {kernel.sectors[a].name} and {kernel.sectors[b].name}",
                  actors=[who] if who.startswith("civ:") else [], sector_id=a,
                  cause=why, data={"a": a, "b": b, "kind": kind, "handling": w["handling"]})
    return w


def handling_of(kernel: Any, who: str) -> str:
    """How a people handles its throats, by what it is (its doctrine's card) - unless its player has chosen."""
    from xylarium.kernel import alignment, federation, spheres
    chosen = stats(kernel)["handling"].get(who)
    if chosen:
        return chosen
    home = spheres._home(kernel, who)
    civ = getattr(home, "civilization", None) if home is not None else None
    return HANDLING[federation.preferred_card(alignment.doctrine(civ) if civ is not None else 0.0)]


def _masters(kernel: Any, logs: List[str]) -> None:
    """An ancient people whose network reaches the core devises how to pass the bounce."""
    from xylarium.kernel import board, cosmos, history, spheres
    if not cosmos.is_cosmic(kernel):
        return
    st = stats(kernel)
    for who, home in board.ancient_peoples(kernel).items():
        if who in st["masters"] or not spheres.crossed(kernel, who):
            continue
        p = cosmos.position(kernel, home.sector_id)
        if p is None or spheres.radius(kernel, who) < p["r"]:
            continue                                         # its passages do not yet reach the core
        st["masters"][who] = kernel.cycle_count
        history.event(kernel, "BOUNCE_MASTERED", f"The {who.split(':', 1)[-1]} learn to pass the bounce",
                      actors=[who], planet=home,
                      cause="its passages reach the core: it devises how to ride the torsion's repulsion through a "
                            "black hole's throat, mass undistorted, clock dilated",
                      data={"handling": handling_of(kernel, who)})
        logs.append(f"[WORMHOLE] The {who.split(':', 1)[-1]} master the bounce: the throats are theirs to open.")


def _natural(kernel: Any, logs: List[str]) -> None:
    """Each master holds the throats whose mouths its network reaches: its stars' holes to the centre, and the centre
    to the other galaxies' centres."""
    from xylarium.kernel import cluster, spheres
    st = stats(kernel)
    if not st["masters"]:
        return
    centre = _centre_sector(kernel)
    first = min(st["masters"], key=lambda w: (st["masters"][w], w))      # the centre is the first master's
    for sid, m in mouths(kernel).items():
        if m["kind"] != "stellar" or key(sid, centre) in st["worms"]:
            continue
        holder = spheres.presence(kernel, spheres.owner(kernel, sid))
        if holder in st["masters"]:
            open_throat(kernel, sid, centre, holder, "long_haul", passage_cr(kernel),
                        "a heavy star's black hole and the core's, joined through the fabric")
            logs.append(f"[WORMHOLE] A long-haul throat opens from {kernel.sectors[sid].name} to the centre.")
    gals = cluster.stats(kernel).get("galaxies") or []
    for i in range(1, len(gals)):
        g = _galaxy_sector(kernel, i)
        if g is not None and key(centre, g) not in st["worms"]:
            open_throat(kernel, centre, g, first, "intergalactic", passage_cr(kernel),
                        f"galaxies are spheres stacked on their bounces: the core's throat reaches {gals[i]['name']}")
            logs.append(f"[WORMHOLE] A throat across the void opens to {gals[i]['name']}.")


# ---------------------------------------------------------------------- forging
def flow(kernel: Any, who: str, anchor: int) -> mc.Chain:
    """A line's book FLOW: from a mouth it holds, each busy system's traffic times the hops it loses going the long
    way round (time as distance) - signed, per system."""
    from xylarium.kernel import fibres
    dev = fibres.state(kernel)["dev"]
    by: Dict[int, float] = {}
    for k, v in dev.items():
        x, y = (int(s) for s in k.split("-"))
        for s in (x, y):
            by[s] = by.get(s, 0.0) + v
    out: mc.Chain = {}
    for s, traffic in sorted(by.items(), key=lambda kv: -kv[1])[:8]:
        if s == anchor or key(anchor, s) in stats(kernel)["worms"] or s not in kernel.sectors:
            continue
        lost = _around(kernel, anchor, s) if anchor in kernel.sectors else float("inf")
        if lost != float("inf") and lost > fibres.MIN_COST:
            out[(str(s), "flow")] = mc.q(traffic) * (mc.q(lost) - mc.q(fibres.MIN_COST))
    return out


def forge_cost_j(kernel: Any, who: str, anchor: int, target: int) -> float:
    """A passage held open for each hop the throat replaces, every year of one of its stewards' terms."""
    from xylarium.kernel import mastery, spheres
    hops = _around(kernel, anchor, target)
    return mastery.E_BRIDGE_J * max(1.0, hops) * spheres.generation(kernel, who)


def forge(kernel: Any, who: str, anchor: int, target: int, logs: List[str]) -> Optional[Dict[str, Any]]:
    from xylarium.kernel import spheres
    net = spheres.stats(kernel)["nets"].get(who)
    cost = forge_cost_j(kernel, who, anchor, target)
    if net is None or float(net.get("bank_j", 0.0)) < cost:
        return None
    net["bank_j"] = float(net["bank_j"]) - cost
    w = open_throat(kernel, anchor, target, who, "forged", cost * credits_per_joule(kernel),
                    f"the {who.split(':', 1)[-1]}'s progenitors punch a stabilised throat to where the traffic is")
    stats(kernel)["forged"] += 1
    logs.append(f"[WORMHOLE] The {who.split(':', 1)[-1]} forge a throat from {kernel.sectors[anchor].name} to "
                f"{kernel.sectors[target].name}.")
    return w


def _forging(kernel: Any, logs: List[str]) -> None:
    """Each master line not held by a player reads its FLOW from its nearest mouth and forges where it lacks most."""
    from xylarium.kernel import board, spheres
    st = stats(kernel)
    lines = board.progenitors(kernel)
    for who in sorted(st["masters"]):
        line = lines.get(who)
        if line is None or line.get("player"):
            continue
        held = set(spheres.stats(kernel)["nets"].get(who, {}).get("held", []))
        anchors = sorted(s for s in mouths(kernel) if s in held or s == MOUTH_BASE)
        if not anchors:
            continue
        m = line.setdefault("flow_mind", mc.new_mind())
        anchor = anchors[0]
        res = flow(kernel, who, anchor)
        mc.seal(m, res)
        entry = mc.lead(res, ("flow",), deepest=True)
        if entry is None or "forge" in mc.walls(m, mc.shape(entry, res[entry], "system")):
            continue
        if forge(kernel, who, anchor, int(entry[0]), logs) is not None:
            mc.intend(m, entry, res[entry], "forge", "system")


def season(kernel: Any) -> List[str]:
    """Once a year: each lane's year of traffic closes; masters of the bounce arise; throats open; lines forge."""
    from xylarium.kernel import polity
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    st = stats(kernel)
    for rec in st["lanes"].values():
        rec["last_year"], rec["year"] = rec["year"], 0
    logs: List[str] = []
    _masters(kernel, logs)
    _natural(kernel, logs)
    _forging(kernel, logs)
    return logs


def render(kernel: Any) -> str:
    st = stats(kernel)
    lines = ["=== TRANSIT ===", f"  Tolls paid: {st['paid']:,.0f} Cr; a passage's energy is worth "
                                 f"{passage_cr(kernel):,.1f} Cr now"]
    for who, c in sorted(st["masters"].items(), key=lambda kv: kv[1]):
        lines.append(f"  Masters of the bounce: the {who.split(':', 1)[-1]} ({handling_of(kernel, who)})")
    for w in st["worms"].values():
        lines.append(f"  {w['kind']} throat {kernel.sectors[w['a']].name} <-> {kernel.sectors[w['b']].name}: "
                     f"the {w['owner'].split(':', 1)[-1]}'s, {w['handling']}")
    busiest = sorted(st["lanes"].items(), key=lambda kv: -kv[1]["collected"])[:5]
    for k, rec in busiest:
        if rec["collected"] > 0:
            lines.append(f"  lane {k}: {rec['transits']} passages, {rec['collected']:,.0f} Cr collected")
    return "\n".join(lines)


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    kinds: Dict[str, int] = {}
    for w in st["worms"].values():
        kinds[w["kind"]] = kinds.get(w["kind"], 0) + 1
    return {"paid_cr": round(st["paid"]), "tolled_lanes": sum(1 for r in st["lanes"].values() if r["collected"] > 0),
            "masters": sorted(st["masters"]), "throats": kinds, "forged": st["forged"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="transit",
    state=lambda: {"lanes": {}, "worms": {}, "masters": {}, "revenue": {}, "handling": {}, "paid": 0.0,
                   "forged": 0},
    season=season,
    summary=summary,
))
