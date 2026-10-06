"""
Xylarium transit: the lanes the networks hold open, what passing them costs, and the wormholes of the Einstein-Cartan
fabric - the spacing guild's trade.

LANES AND THEIR TOLLS. A passage into a system a network holds (spheres.py) is that network's to charge - inside its
sphere, its own lanes; across a border, the crossing pays the network it enters - and its people take a toll from
those who pass. No fee is laid down. What a passage is worth is set by the
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
other galaxy's centre (across the void) - each kept dark until a ship passes it, the observation that puts that
galaxy's heart on the map. Through the bounce a ship is carried on the torsion's own repulsion, its mass undistorted,
its clock dilated: a throat is crossed in one hop, as cheap to travel as the cheapest lane - and paid for by its
tithe.

  MASTERY   a people that folds space rides a stellar black hole's throat (gateways.py); the fold itself stays within
            its cell, so every road past it runs through the mouths. The centre's throat - the hub - is kept by the
            master whose minds evolved deepest in the centre's wave (or travel as information): the core's ancients,
            by where they are. A master holds every throat whose mouth its network reaches, the hub's keeper the centre's
  HANDLING  its own choice, by its needs: closed while it is at war, guarded (its own and its bonded only) while
            its sovereign's first need is security, else tolled by the toll law; a player's progenitor sets its own
            - open (only what the throat cost), tolled, guarded or closed (command.py)
  TITHE     the bounce carries a ship the throat's whole span in one passage - the torsion its accelerant, the
            dilation its clock, the ship's mass undistorted - and the throat is held open again by the folds it
            stands in for: every passer pays the progenitors who keep it, for their ancients, a passage's energy for
            each lane's length the throat spans (time as distance), at energy's price
  DORMANCY  a throat needs upkeep only when a mass passes (its tithe): when its keeper's people falls it does not
            collapse but lies dormant, closed, until a master reaching one of its mouths salvages it - or a people
            that folds space without the bounce tries its mouth and destabilises it, collapsing every throat strung
            through it, on through every mouth whose throats were all dormant (_heirs, collapse_mouth)
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
            if port is None or len(getattr(port, "stock", None) or {}) < len(COMMODITY_CONFIG):
                continue                                     # a reading never charters a port's inventory
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
    """Who a passage from a into b pays: a throat's keeper; else the network that holds b - the system it arrives in
    (inside a network, its own; across a border, the one it enters: a crossing pays where it lands) - or no one."""
    w = worm(kernel, a, b)
    if w is not None:
        return w.get("owner")
    from xylarium.kernel import spheres
    return spheres.presence(kernel, spheres.owner(kernel, b))


def _payer(kernel: Any, captain: Any) -> Optional[str]:
    from xylarium.kernel import stewardship
    return stewardship.party(kernel, f"captain:{captain.id}")


def _free(kernel: Any, payer: Optional[str], holder: str) -> bool:
    from xylarium.kernel import spheres
    if payer == holder:
        return True
    b = spheres.bond(kernel, payer, holder) if payer else None
    return b is not None and b["kind"] in FREE_BONDS


def at_war(kernel: Any, x: Optional[str], y: Optional[str]) -> bool:
    """Are two peoples at war (a realm war between them, open)?"""
    if not x or not y or x == y or "realmwars" not in getattr(kernel, "state", {}):
        return False
    from xylarium.kernel import realmwars
    return any(w["status"] == "open" and {w.get("taker"), w.get("holder")} == {x, y}
               for w in realmwars.stats(kernel)["wars"].values())


def blocks(kernel: Any, payer: Optional[str], a: int, b: int) -> bool:
    """A blockade: a lane's holder turns back the ships of a people it is at war with - and an embargo: a holder
    whose doctrine forbids taking turns back a people waging a war of taking (borders.py); and a realm's sanction:
    a people caught at covert work is turned back by every lane its keeper's web holds (covert.py)."""
    holder = owner(kernel, a, b)
    if holder is None or not payer or holder == payer:
        return False
    from xylarium.kernel import covert
    return at_war(kernel, holder, payer) or (aggressor(kernel, payer) and _abhorrent_to(kernel, holder)) \
        or covert.sanctioned(kernel, payer, holder)


def aggressor(kernel: Any, who: Optional[str]) -> bool:
    """Is a people waging a war of taking (an open realm war, as the taker)?"""
    if not who or "realmwars" not in getattr(kernel, "state", {}):
        return False
    from xylarium.kernel import realmwars
    return any(w["status"] == "open" and w.get("taker") == who for w in realmwars.stats(kernel)["wars"].values())


def _abhorrent_to(kernel: Any, holder: str) -> bool:
    from xylarium.kernel import realmwars
    return realmwars._abhors(kernel, holder)


def refuses(kernel: Any, captain: Any, a: int, b: int) -> bool:
    """A guarded throat turns back all but its holder's own and its bonded; a closed one, everyone; and any lane
    held by a people at war turns back its enemy's ships (a blockade)."""
    from xylarium.kernel import ascendance
    payer = _payer(kernel, captain)
    if blocks(kernel, payer, a, b) or ascendance.confined(kernel, payer, a, b):
        return True                                          # a blockade; or a people a steward holds at home
    w = worm(kernel, a, b)
    if w is None:
        return False
    if w.get("handling") == "closed":
        return True
    if w.get("handling") == "guarded":
        from xylarium.kernel import spheres
        payer = _payer(kernel, captain)
        return not (payer == w.get("owner") or (payer and spheres.bond(kernel, payer, w.get("owner")) is not None))
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
    st = fibres.state(kernel)                                 # lanes develop over years: read once a year, and anew
    version = (st.get("version", 0), st.get("seasons", 0) // 4, len(kernel.sectors),   # when the map or space changes
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
                nd = d + fibres.base_lane_cost(kernel, s, w)
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
        return {"owner": holder, "toll": 0.0, "floor": 0.0, "ceiling": 0.0, "tithe": 0.0}
    rec = lane(kernel, a, b)
    floor = max(0.0, rec["cost_cr"] - rec["collected"]) / max(1, rec["last_year"])
    around = _around(kernel, a, b)
    if around == float("inf"):
        ceiling = fibres.cargo_value(captain) + hop_value(kernel, captain)      # no way round: all it carries
    else:
        ceiling = max(0.0, around - fibres.base_lane_cost(kernel, a, b)) * hop_value(kernel, captain)
    w = worm(kernel, a, b)
    if w is not None and w.get("handling") == "open":
        toll = min(floor, ceiling)
    else:
        toll = min(ceiling, floor + max(0.0, ceiling - floor) / 2.0)
    return {"owner": holder, "toll": toll, "floor": floor, "ceiling": ceiling, "tithe": tithe_cr(kernel, a, b)}


def on_passage(kernel: Any, captain: Any, a: int, b: int) -> int:
    """A ship passes a lane: it pays the lane's holder what the lane is worth to it (what it can)."""
    q = quote(kernel, captain, a, b)
    if not q["owner"]:
        return 0
    tithe = int(min(q["tithe"], max(0, captain.credits)))       # the bounce's upkeep first: the throat must hold
    captain.credits -= tithe
    amt = int(min(q["toll"], max(0, captain.credits)))
    captain.credits -= amt
    settle(kernel, q["owner"], f"captain:{captain.id}", a, b, amt, tithe)
    if (amt or tithe) and hasattr(kernel, "action_logs"):
        kernel.action_logs.append(f"[TRANSIT] {captain.name} pays the {q['owner'].split(':', 1)[-1]} {amt:,} Cr "
                                  f"toll" + (f" and {tithe:,} Cr tithe for the bounce" if tithe else "")
                                  + f" to pass {a}<->{b}.")
    return amt + tithe


def settle(kernel: Any, holder: str, payer: str, a: int, b: int, toll: float, tithe: float = 0.0,
           transits: int = 1, paid: Optional[Tuple[int, str]] = None) -> None:
    """A passage paid for (by a ship, a hauler, or a flow of passengers): the lane's traffic counted, the money into
    its keeper's treasury in the keeper's own money (the reserve its lane is paid in - converted through the
    exchanges), and the receipt on the hypha ledger: the passage delivered, a proof of useful work."""
    from xylarium.kernel import hypha, spheres
    rec = lane(kernel, a, b)
    rec["transits"] += transits
    rec["year"] += transits
    st = stats(kernel)
    if tithe > 0:
        st.setdefault("tithes", {})[holder] = st["tithes"].get(holder, 0.0) + tithe
        st["tithed"] = st.get("tithed", 0.0) + tithe
    if toll > 0:
        rec["collected"] += toll
        st["revenue"][holder] = st["revenue"].get(holder, 0.0) + toll
        st["paid"] += toll
    total = int(toll + tithe)
    if total <= 0 and not paid:
        return
    got, cur = _pay_owner(kernel, holder, *(paid if paid else (total, "SOL")))   # the payer's own money, exchanged
    hypha.append(kernel, cur, "pouw", payer, holder, got, cur, ref=key(a, b))


def reserves(kernel: Any) -> Dict[str, str]:
    """The reserve currencies: the ancients' own moneys (each living progenitor line's people's), which every passage
    through a progenitor's lane or throat settles in - federations convert into them at the exchanges. A settled
    board's elders keep SOL. -> {currency: people}."""
    from xylarium.kernel import board, spheres
    out: Dict[str, str] = {}
    for who, line in board.progenitors(kernel).items():
        home = spheres._home(kernel, who) if line.get("ancient") else None
        if home is not None:
            out[home.currency] = who
    return out or {"SOL": "elders"}


def charge_cr(kernel: Any, a: int, b: int) -> Tuple[Optional[str], float, float]:
    """What a passer from outside the holder's bonds pays to pass a lane, in SOL: (holder, toll, tithe) - priced for
    a typical passer (the median crew's hop)."""
    w = worm(kernel, a, b)
    holder = w.get("owner") if w is not None else owner(kernel, a, b)
    if holder is None:
        return None, 0.0, 0.0
    from xylarium.kernel import fibres
    hv = _typical_hop(kernel)
    rec = stats(kernel)["lanes"].get(key(a, b))
    cost_cr = rec["cost_cr"] if rec else (float(w["cost_cr"]) if w else passage_cr(kernel))
    floor = max(0.0, cost_cr - (rec["collected"] if rec else 0.0)) / max(1, rec["last_year"] if rec else 1)
    around = _around(kernel, a, b)
    saving = (float("inf") if around == float("inf") else
              max(0.0, around - fibres.base_lane_cost(kernel, a, b)) * hv)
    if saving == float("inf"):
        toll = floor
    elif w is not None and w.get("handling") == "open":
        toll = min(floor, saving)
    else:
        toll = min(saving, floor + max(0.0, saving - floor) / 2.0)
    return holder, toll, tithe_cr(kernel, a, b)


def flow_passage(kernel: Any, payer: Optional[str], a: int, b: int, transits: int = 1) -> float:
    """What a flow pays to pass a lane (haulers, passengers): its charge per passage times the passages - nothing
    for the keeper's own and its free bonds. Returns the SOL owed (the caller takes it from whoever pays)."""
    holder, toll, tithe = charge_cr(kernel, a, b)
    if holder is None or _free(kernel, payer, holder):
        return 0.0
    return (toll + tithe) * transits


def _pay_owner(kernel: Any, who: str, amount: int, currency: str = "SOL") -> Tuple[int, str]:
    """Into the holder's capital world's treasury, in its money."""
    from xylarium.kernel import spheres
    home = spheres._home(kernel, who)
    fx = getattr(kernel, "fx_market", None)
    if home is None:
        from xylarium.kernel import ledger
        sol = amount if currency == "SOL" or fx is None else fx.convert(currency, "SOL", amount)[0]
        ledger.pay_service(sol, institution="transit")
        return sol, "SOL"
    if home.currency != currency and fx is not None:
        got, _ = fx.convert(currency, home.currency, amount)  # a money no exchange lists yet is listed, or held
        home.treasury += got
        return got, home.currency
    home.treasury += amount
    return amount, currency


# ---------------------------------------------------------------------- the bounce's upkeep, and what routes see
def _mean_lane_kpc(kernel: Any) -> Optional[float]:
    """How far one lane carries in this galaxy, on the mean: the proper length of its charted lanes."""
    from xylarium.kernel import cache, cosmos
    if not cosmos.is_cosmic(kernel):
        return None

    def build() -> Optional[float]:
        got = []
        for sid, sec in sorted(kernel.sectors.items()):
            for w in sec.warps:
                if sid < w and worm(kernel, sid, w) is None:
                    d = cosmos.distance_kpc(kernel, sid, w)
                    if d:
                        got.append(d)
        return sum(got) / len(got) if got else None
    if not hasattr(kernel, "caches"):
        return build()
    return cache.memo(kernel, "transit_lane_kpc", "mean", build, epoch=(len(kernel.sectors), kernel.cycle_count // 2500))


def span_kpc(kernel: Any, w: Dict[str, Any]) -> Optional[float]:
    """The proper distance a throat spans: to another galaxy, its distance across the void; to the centre, how far
    the other mouth lies from it; else between its mouths."""
    from xylarium.kernel import cluster, cosmos
    a, b = w["a"], w["b"]
    gals = cluster.stats(kernel).get("galaxies") or []
    for s in (a, b):
        if 0 < s - MOUTH_BASE < len(gals):
            return float(gals[s - MOUTH_BASE]["dist_kpc"])
    if MOUTH_BASE in (a, b):
        other = b if a == MOUTH_BASE else a
        p = cosmos.position(kernel, other)
        return float(p["r"]) if p else None
    return cosmos.distance_kpc(kernel, a, b)


def tithe_cr(kernel: Any, a: int, b: int) -> float:
    """The bounce's upkeep for one passage, tithed to the progenitors who keep the throat for their ancients: the
    bounce carries a ship the throat's whole span in one passage (its torsion the accelerant, the dilation its
    clock), and the throat is held open again by the folds it stands in for - a passage's energy for every lane's
    length it spans (time as distance), at energy's price."""
    w = worm(kernel, a, b)
    if w is None:
        return 0.0
    lane_kpc = _mean_lane_kpc(kernel)
    span = span_kpc(kernel, w)
    if lane_kpc and span:
        hops = span / lane_kpc
    else:
        around = _around(kernel, a, b)                       # on a board with no galaxy's geometry: the hops it replaces
        hops = around if around != float("inf") else 1.0
    return passage_cr(kernel) * max(1.0, hops)


def _typical_hop(kernel: Any) -> float:
    """What a hop costs a typical passer: the median of what the crews in the galaxy burn."""
    from xylarium.kernel import cache

    def build() -> float:
        vals = sorted(hop_value(kernel, c) for c in kernel.captains.values())
        return vals[len(vals) // 2] if vals else passage_cr(kernel)
    if not hasattr(kernel, "caches"):
        return build()
    return cache.memo(kernel, "transit_hop", "median", build, epoch=kernel.cycle_count // 25)


def charge_hops(kernel: Any, a: int, b: int) -> float:
    """What a passer from outside the holder's bonds pays to pass a lane - its toll and a throat's tithe - in the hops
    that money would buy a typical passer: the weight a route gives what a lane charges."""
    if not hasattr(kernel, "state"):
        return 0.0
    holder, toll, tithe = charge_cr(kernel, a, b)
    if holder is None or toll + tithe <= 0:
        return 0.0
    hv = _typical_hop(kernel)
    return (toll + tithe) / hv if hv > 0 else 0.0


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
        if x in kernel.sectors and y not in kernel.sectors[x].warps:
            kernel.sectors[x].warps.append(y)               # a mouth not yet witnessed gets its way back when it is
    w = st["worms"][k] = {"a": a, "b": b, "owner": who, "kind": kind, "opened": kernel.cycle_count,
                          "cost_cr": float(cost_cr), "handling": handling_of(kernel, who)}
    topology.changed(kernel)
    fibres._bump(kernel)
    history.event(kernel, "WORMHOLE", f"A throat opens between {_name(kernel, a)} and {_name(kernel, b)}",
                  actors=[who] if who.startswith("civ:") else [], sector_id=a,
                  cause=why, data={"a": a, "b": b, "kind": kind, "handling": w["handling"]})
    return w


def _name(kernel: Any, sid: int) -> str:
    """A mouth's name - a galaxy's heart not yet witnessed is known only by its galaxy."""
    if sid in kernel.sectors:
        return kernel.sectors[sid].name
    from xylarium.kernel import cluster
    gals = cluster.stats(kernel).get("galaxies") or []
    i = sid - MOUTH_BASE
    return f"the unwitnessed heart of {gals[i]['name']}" if 0 < i < len(gals) else f"sector {sid}"


def admits(kernel: Any, captain: Any, a: int, b: int) -> bool:
    """May this ship pass from a to b? Not through a throat its holder bars it from. Passing a throat into a galaxy
    no one has witnessed is the observation that puts its heart on the map (inverse compaction: until a ship arrives,
    the galaxy is its formula)."""
    if refuses(kernel, captain, a, b):
        return False
    if b not in kernel.sectors and worm(kernel, a, b) is not None:
        i = b - MOUTH_BASE
        if _galaxy_sector(kernel, i) is None:
            return False
        if a not in kernel.sectors[b].warps:
            kernel.sectors[b].warps.append(a)
        from xylarium.kernel import cluster, history, topology
        cluster.stats(kernel)["charted"] = cluster.stats(kernel).get("charted") or kernel.cycle_count
        topology.changed(kernel)
        g = cluster.stats(kernel)["galaxies"][i]
        history.event(kernel, "GALAXY_REACHED", f"{captain.name} passes the bounce into {g['name']}", sector_id=b,
                      actors=[f"captain:{captain.id}"],
                      cause=f"through the core's throat, {g['dist_kpc']:,.0f} kpc across the void in one passage: "
                            f"the first witness of that galaxy's heart", data={"galaxy": g["name"]})
    return True


def handling_of(kernel: Any, who: str) -> str:
    """How a people handles its throats, by its own needs - unless its player has chosen: closed while it is at war
    (nothing comes through), guarded while its sovereign's first need is its security, tolled otherwise (the toll law
    itself asks nothing where the throat has paid for itself and saves no one anything)."""
    from xylarium.kernel import mindcore, polity, realmwars
    chosen = stats(kernel)["handling"].get(who)
    if chosen:
        return chosen
    if "realmwars" in kernel.state and any(w["status"] == "open" and who in (w.get("taker"), w.get("holder"))
                                           for w in realmwars.stats(kernel)["wars"].values()):
        return "closed"
    recs = polity.of_people(kernel, who) if "polity" in kernel.state else []
    if recs:
        s = min(recs, key=lambda r: (r["since"], r["id"]))
        lead = mindcore.lead(polity.chain(kernel, s, {s["id"]: polity.field(kernel, s)}), polity.BOOKS)
        if lead is not None and lead[1] == "security":
            return "guarded"
    return "tolled"


def _masters(kernel: Any, logs: List[str]) -> None:
    """A people that folds space rides the bounce of a stellar black hole (gateways.py: the torsion carries a mass
    undistorted). The centre's throat - the hub - is the progenitors' first contest, fought through the peoples they
    steward: the line whose networks carry the most of the galaxy keeps it, through a people that bears its wave
    (gateways.hub_contest); it passes when another line's networks outgrow it, or its keeper falls."""
    from xylarium.kernel import cosmos, gateways, history, spheres
    if not cosmos.is_cosmic(kernel):
        return
    st = stats(kernel)
    for who in sorted(spheres.stats(kernel)["nets"]):
        if who in st["masters"] or not spheres.crossed(kernel, who):
            continue
        st["masters"][who] = kernel.cycle_count
        home = spheres._home(kernel, who)
        history.event(kernel, "BOUNCE_MASTERED", f"The {who.split(':', 1)[-1]} learn to pass the bounce",
                      actors=[who], planet=home,
                      cause="it folds space: past its fold's reach it rides a black hole's throat on the torsion's "
                            "repulsion, mass undistorted, clock dilated",
                      data={"exposure": round(gateways.home_exposure(kernel, who), 3)})
        logs.append(f"[WORMHOLE] The {who.split(':', 1)[-1]} master the bounce.")
    keeper = gateways.hub_keeper(kernel, st["masters"])
    if keeper != st.get("hub"):
        old = st.get("hub")
        st["hub"] = keeper
        if keeper is not None:
            history.event(kernel, "HUB_KEPT", f"The {keeper.split(':', 1)[-1]} keep the galaxy's hub",
                          actors=[keeper] + ([old] if old else []),
                          cause="of the lines whose peoples bear the centre's wave, theirs carries the most of the "
                                "galaxy"
                                + (f" - it passes from the {old.split(':', 1)[-1]}" if old else ""),
                          data={"exposure": round(gateways.home_exposure(kernel, keeper), 3)})
            for w in st["worms"].values():
                if MOUTH_BASE in (w["a"], w["b"]) and w.get("kind") in ("long_haul", "intergalactic") \
                        and w.get("owner") == old:
                    w["owner"], w["handling"] = keeper, handling_of(kernel, keeper)


def _natural(kernel: Any, logs: List[str]) -> None:
    """Each master holds the throats whose mouths its network reaches: its stars' holes to the centre, and the centre
    to the other galaxies' centres."""
    from xylarium.kernel import cluster, spheres
    st = stats(kernel)
    if not st["masters"]:
        return
    centre = _centre_sector(kernel)
    first = st.get("hub") or min(st["masters"], key=lambda w: (st["masters"][w], w))   # the hub's keeper
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
        g = MOUTH_BASE + i                                   # its heart stays a formula until a ship passes (admits)
        if key(centre, g) not in st["worms"]:
            open_throat(kernel, centre, g, first, "intergalactic", passage_cr(kernel),
                        f"galaxies are spheres stacked on their bounces: the core's throat reaches toward "
                        f"{gals[i]['name']}, unwitnessed")
            logs.append(f"[WORMHOLE] A throat across the void opens toward {gals[i]['name']}.")


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


def _heirs(kernel: Any, logs: List[str]) -> None:
    """A throat needs upkeep only when a mass passes it (its tithe): unkept, it does not collapse - it goes DORMANT,
    impassable, holding until someone comes. A living master whose network reaches one of its mouths (any master, at
    the centre) SALVAGES it. A people that folds space but has not mastered the bounce, finding a dormant mouth in
    its network, tries it - and, not knowing how to ride the bounce, destabilises the mouth: every throat strung
    through it collapses, and the collapse runs on through every mouth whose remaining throats were all dormant."""
    from xylarium.kernel import history, relations, spheres
    st = stats(kernel)
    living = relations._peoples(kernel)
    for who in [w for w in st["masters"] if w not in living]:
        st["masters"].pop(who)
        history.event(kernel, "BOUNCE_LOST", f"The {who.split(':', 1)[-1]}'s mastery of the bounce dies with them",
                      cause="its people has fallen")
    for k, w in sorted(st["worms"].items()):
        if w.get("owner") and w["owner"] not in living:
            w["keeper"], w["owner"], w["handling"], w["dormant"] = w["owner"], None, "closed", kernel.cycle_count
            history.event(kernel, "WORMHOLE_DORMANT", f"The throat between {_name(kernel, w['a'])} and "
                          f"{_name(kernel, w['b'])} falls dormant", cause=f"the {w['keeper'].split(':', 1)[-1]} who "
                          f"kept it are gone; unused, it holds - impassable until someone comes", data={"throat": k})
    for k, w in sorted(st["worms"].items()):
        if k not in st["worms"] or w.get("dormant") is None:
            continue
        heir = None
        tamperer = None
        for end in (w["a"], w["b"]):
            holder = spheres.presence(kernel, spheres.owner(kernel, end))
            if holder in st["masters"]:
                heir = holder
            elif holder is not None and holder in living and end != MOUTH_BASE and end in mouths(kernel):
                tamperer = tamperer or (holder, end)
        if heir is None and MOUTH_BASE in (w["a"], w["b"]) and st["masters"]:
            from xylarium.kernel import gateways
            heir = gateways.hub_keeper(kernel, st["masters"])
        if heir is not None:
            w["owner"], w["handling"] = heir, handling_of(kernel, heir)
            w.pop("dormant", None)
            history.event(kernel, "WORMHOLE_SALVAGED", f"The {heir.split(':', 1)[-1]} salvage the throat the "
                          f"{w.get('keeper', '?').split(':', 1)[-1]} kept", actors=[heir],
                          cause="a dormant throat, its mouth in their network, and they know the bounce",
                          data={"throat": k})
            logs.append(f"[WORMHOLE] The {heir.split(':', 1)[-1]} salvage a throat of the "
                        f"{w.get('keeper', '?').split(':', 1)[-1]}.")
        elif tamperer is not None:
            who, mouth = tamperer
            history.event(kernel, "THROAT_TAMPERED", f"The {who.split(':', 1)[-1]} try the dormant mouth at "
                          f"{_name(kernel, mouth)}", actors=[who],
                          cause="they fold space but have not mastered the bounce: the mouth destabilises")
            n = collapse_mouth(kernel, mouth, f"the {who.split(':', 1)[-1]}, unready, destabilised it")
            logs.append(f"[WORMHOLE] The {who.split(':', 1)[-1]} try a dormant mouth; {n} throats collapse.")


def collapse_mouth(kernel: Any, mouth: int, why: str, seen: Optional[set] = None) -> int:
    """A destabilised mouth: every throat through it collapses; the collapse runs on through each other mouth whose
    remaining throats were all dormant (strung together, nothing holding them). Returns how many fell."""
    from xylarium.kernel import history, topology
    st = stats(kernel)
    seen = seen if seen is not None else set()
    if mouth in seen:
        return 0
    seen.add(mouth)
    fallen = 0
    others = []
    for k, w in sorted(st["worms"].items()):
        if mouth not in (w["a"], w["b"]):
            continue
        for x, y in ((w["a"], w["b"]), (w["b"], w["a"])):
            if x in kernel.sectors and y in kernel.sectors[x].warps:
                kernel.sectors[x].warps.remove(y)
        st["worms"].pop(k)
        st["collapsed"] = st.get("collapsed", 0) + 1
        fallen += 1
        others.append(w["b"] if w["a"] == mouth else w["a"])
        history.event(kernel, "WORMHOLE_COLLAPSE", f"The throat between {_name(kernel, w['a'])} and "
                      f"{_name(kernel, w['b'])} collapses", sector_id=w["a"] if w["a"] in kernel.sectors else None,
                      cause=why, data={"throat": k})
    topology.changed(kernel)
    for o in others:
        rest = [w for w in st["worms"].values() if o in (w["a"], w["b"])]
        if rest and all(w.get("dormant") is not None for w in rest):
            fallen += collapse_mouth(kernel, o, "the collapse ran on along a string of dormant throats", seen)
    return fallen


def season(kernel: Any) -> List[str]:
    """Once a year: each lane's year of traffic closes; a fallen keeper's throats pass on or collapse; masters of the
    bounce arise; throats open; lines forge."""
    from xylarium.kernel import polity
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    st = stats(kernel)
    for rec in st["lanes"].values():
        rec["last_year"], rec["year"] = rec["year"], 0
    logs: List[str] = []
    _heirs(kernel, logs)
    _masters(kernel, logs)
    _natural(kernel, logs)
    _forging(kernel, logs)
    return logs


def render(kernel: Any) -> str:
    st = stats(kernel)
    lines = ["=== TRANSIT ===", f"  Tolls paid: {st['paid']:,.0f} Cr; tithes {st.get('tithed', 0.0):,.0f} Cr; a "
                                 f"passage's energy is worth {passage_cr(kernel):,.1f} Cr now",
             "  Reserve currencies: " + ", ".join(f"{c} (the {w.split(':', 1)[-1]})" for c, w in reserves(kernel).items())]
    for who, c in sorted(st["masters"].items(), key=lambda kv: kv[1]):
        lines.append(f"  Masters of the bounce: the {who.split(':', 1)[-1]} ({handling_of(kernel, who)})")
    for w in st["worms"].values():
        lines.append(f"  {w['kind']} throat {_name(kernel, w['a'])} <-> {_name(kernel, w['b'])}: "
                     + (f"the {w['owner'].split(':', 1)[-1]}'s, {w['handling']}" if w.get("owner") else
                        f"dormant (the {str(w.get('keeper', '?')).split(':', 1)[-1]}'s)"))
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
    kinds["dormant"] = sum(1 for w in st["worms"].values() if w.get("dormant") is not None)
    return {"paid_cr": round(st["paid"]), "tithed_cr": round(st.get("tithed", 0.0)),
            "tolled_lanes": sum(1 for r in st["lanes"].values() if r["collected"] > 0),
            "masters": sorted(st["masters"]), "throats": kinds, "forged": st["forged"],
            "collapsed": st.get("collapsed", 0)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="transit",
    state=lambda: {"lanes": {}, "worms": {}, "masters": {}, "revenue": {}, "handling": {}, "paid": 0.0,
                   "forged": 0, "tithes": {}, "tithed": 0.0},
    season=season,
    summary=summary,
))
