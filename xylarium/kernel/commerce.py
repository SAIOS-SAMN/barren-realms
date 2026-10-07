"""
Xylarium commerce: trade between peoples - what a treaty of trade actually moves.

A treaty of trade between two sovereigns (polity.py) is a promise; commerce is what it delivers. Once a year, for
every such treaty, each side's worlds that hold LESS than they keep of a good (staples.reserve: two seasons of their
people's staple, their works' ore, a reserve of every element) are offered what the other side's worlds hold BEYOND
what they keep - the deepest want first, the largest surplus first. Goods move; money moves back. Nothing is minted:
the goods are a transfer between holders, the money passes through the exchanges.

  PRICE     the seller's own port's, as the buyer has HEARD it (news.py: word travels at light's speed - near, as it
            stands; far, as its long mean), or the market's mean where the seller keeps no port - fixed in a forward
            contract when the deal is struck: the seller takes it only if it is no less than its own port would pay.
            In SOL, paid in the buyer's money, converted at the exchanges into the seller's (fx.convert): a plain
            transfer, payer to payee, at the buyer's port. A people that buys more than it sells sells
            its own money to do it, and its money weakens; its imports grow dearer until they balance. That is how
            economic models meet: through the exchanges, not by decree.
  ROUTE     the convoy sails the geodesic from the seller's system to the buyer's and pays every lane's keeper its
            toll and tithe (transit.flow_passage, settled through transit.settle - a receipt on the hypha ledger).
            A lane that turns the buyer or the seller back (a blockade, an embargo, a steward's quarantine) closes the
            route: the good does not move, unless it is smuggled (covert.py).
  WORTH     what a unit is worth to the buyer: its staple, the output its eaters make while fed (a world's output per
            unit it eats); any other good, what it would pay at its own port. Its council buys as far as that worth
            exceeds every real cost (decide.choose), and its treasury pays: the contract price, the route, the risk
            of the road (fxroutes: the share a trip through borderland or anarchy does not keep) and the age of what
            it heard (news.age_cost: the drift the price can make over the word's light-time).
  BROKERED  beyond treaties, a line's stewards broker its realms' trade with the line's own house (the ancient people
            whose line stewards them: constellations), core and realm each buying what the other spares.
  TARIFF    a sovereign whose first need is wealth (polity: its residual leads with the wealth book) takes, on what its
            worlds import, half the gain they make over the price and route (the surplus split evenly, as relations
            splits a tribute) - into its capital's treasury. A sovereign whose people are hungry does not tax bread.

What a treaty delivered is what moved: the sovereign's books (polity.delivered) read last year's commerce, so a trade
that moves nothing - a partner whose surplus is not this people's food - is sealed as a wall, not a crystal.

MODELS. Each people's economic model is read from its measures, never assigned (model()): its money's regime and
controls (regimes.py), how much of the many's product its few take against what they will bear (rent.py), how open
it is (its trade against its output), and its balance (what it sold less what it bought).
"""

from typing import Any, Dict, List, Optional, Tuple

YEAR_KEEP = 4                                                   # years of commerce kept per pair


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "commerce")


def _pair(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def _goods(kernel: Any, w: Any) -> List[str]:
    from xylarium.kernel import staples
    out = [staples.of(kernel, w), "ORE"]
    return out + sorted(k for k in (w.element_reserves or {}) if k not in out)


def _worth(kernel: Any, w: Any, comm: str) -> Optional[float]:
    """What a unit of a good is worth to the world that wants it, in SOL: its staple, the output its eaters make
    while fed; any other good, what its own port sells it at."""
    from xylarium.kernel import biosphere, relations, staples
    if comm == staples.of(kernel, w):
        return relations._output_sol(kernel, [w]) / max(1, biosphere.consumption(w) * _quarter())
    port = getattr(kernel.sectors.get(w.sector_id), "port", None)
    if port is None:
        return None
    from xylarium.kernel.economy import EconomyManager
    sells = EconomyManager.get_unit_prices(port, comm)[1]
    return float(sells) if sells > 0 else None


def _route(kernel: Any, src: int, dst: int, buyer: str, seller: str) -> Optional[List[Tuple[int, int]]]:
    """The convoy's lanes, or None if a lane on it turns the buyer or the seller back - or a steward holds either
    at home (a quarantined people trades with no one beyond its own system, openly)."""
    from xylarium.kernel import ascendance, transit
    if src == dst:
        return []
    if any(ascendance.ruling(kernel, who) in ("quarantine", "pending") for who in (buyer, seller)):
        return None
    path = kernel.find_path(src, dst) or []
    if len(path) < 2:
        return None
    hops = list(zip(path, path[1:]))
    for a, b in hops:
        for who in (buyer, seller):
            if transit.blocks(kernel, who, a, b):
                return None
    return hops


def _rate(kernel: Any, cur: str) -> float:
    fx = getattr(kernel, "fx_market", None)
    return fx.rate(cur) if fx is not None else 1.0


def _to(kernel: Any, src_cur: str, dst_cur: str, amount: int) -> int:
    fx = getattr(kernel, "fx_market", None)
    if src_cur == dst_cur or fx is None or amount <= 0:
        return amount
    return fx.convert(src_cur, dst_cur, amount)[0]


def _taxes(kernel: Any, rec: Dict[str, Any]) -> bool:
    """A sovereign whose first need is wealth (and whose people are not hungry) levies a tariff."""
    from xylarium.kernel import polity
    res = polity.residual(kernel, rec)
    return bool(res) and res[0] == "wealth"


def _ship(kernel: Any, buyer: Dict[str, Any], seller: Dict[str, Any], bw: Any, sw: Any, comm: str, want: int,
          capital: Optional[Any], tariff: bool, rec: Dict[str, Any]) -> int:
    """One lot from a seller's world to a buyer's: priced, routed, judged, paid. Returns the units moved."""
    from xylarium.kernel import decide, staples, transit
    have = staples.surplus(kernel, sw, comm)
    q = min(want, have)
    if q <= 0:
        return 0
    worth = _worth(kernel, bw, comm)
    if worth is None:
        return 0
    hops = _route(kernel, sw.sector_id, bw.sector_id, buyer["people"], seller["people"])
    if hops is None:
        rec["closed"] += 1                                    # closed openly: it moves covertly, or not at all
        from xylarium.kernel import covert
        got = covert.smuggle(kernel, buyer["people"], seller["people"], bw, sw, comm, q, worth,
                             transit.price(kernel, comm))
        rec["smuggled"] = rec.get("smuggled", 0) + got
        return got
    from xylarium.kernel import fxroutes, news
    from xylarium.kernel.economy import EconomyManager
    port = getattr(kernel.sectors.get(sw.sector_id), "port", None)     # a world with no port has no price to hear
    word = news.heard(kernel, bw.sector_id, sw.sector_id, comm) if port is not None else None
    if word is None:
        return 0                                              # no word of its price has reached the buyer: not bought
    unit, age, sigma = word
    floor = float(EconomyManager.get_unit_prices(port, comm)[0]) if port is not None else 0.0
    if floor > 0 and unit < floor:
        return 0                                              # the seller's own port pays more: it keeps its goods
    path = [sw.sector_id] + [b for _, b in hops]
    risk = unit * fxroutes.HAZARD.get(fxroutes._hazard(kernel, path), 0.0)     # what the road does not keep
    stale = news.age_cost(unit, age, sigma)                   # what acting on old word costs
    tolls = [(a, b, transit.flow_passage(kernel, buyer["people"], a, b)) for a, b in hops]
    route = sum(t for _, _, t in tolls)
    gain = worth - unit - route / q - risk - stale
    if _moneyless(kernel, bw):
        return _barter(kernel, buyer, bw, sw, comm, q, unit, worth, risk, stale, hops, route, rec)
    duty = gain / 2.0 if tariff and gain > 0 and capital is not None and capital is not bw else 0.0
    rate = _rate(kernel, bw.currency)
    afford = (float(bw.treasury) / rate - route) / max(1e-9, unit + duty)
    q = min(q, int(afford))
    if q <= 0:
        return 0
    m = decide.mind_of_planet(kernel, bw)
    if decide.choose(kernel, [decide.option("import", q * (unit + duty + risk + stale) + route, q * worth)], m,
                     bw.id, sw.id, comm, "import") is None:
        return 0
    price = int(q * unit * rate)
    bw.treasury -= price
    from xylarium.kernel import exchanges
    earned = exchanges.convert_at(kernel, bw.sector_id, bw.currency, sw.currency, price)
    sw.treasury += earned
    for a, b, owed in tolls:
        if owed <= 0:
            continue
        holder, toll, tithe = transit.charge_cr(kernel, a, b)
        local = int(owed * rate)
        bw.treasury -= local
        transit.settle(kernel, holder, buyer["people"], a, b, toll, tithe, paid=(local, bw.currency))
    if duty:
        levied = int(q * duty * rate)
        bw.treasury -= levied
        capital.treasury += _to(kernel, bw.currency, capital.currency, levied)
        rec["tariff"] += q * duty
    _send(kernel, sw, bw, comm, q, hops)                      # a forward: paid now at the price struck, landed when
                                                              # the haul is sailed, with the word of where it sailed from
    sol = q * unit
    rec["value"] += sol
    rec["tolls"] += route
    rec["stale"] = rec.get("stale", 0.0) + q * stale
    if stale > 0:                                             # what old word cost this buyer on this port's goods
        key = f"{buyer['people']}|{sw.sector_id}"
        sb = stats(kernel).setdefault("stale_by", {})
        sb[key] = round(sb.get(key, 0.0) + q * stale, 6)
    rec["risk"] = rec.get("risk", 0.0) + q * risk
    rec["units"][comm] = rec["units"].get(comm, 0) + q
    side = rec["flows"].setdefault(f"{seller['id']}>{buyer['id']}", {"value": 0.0, "food": 0, "earned": 0})
    side["value"] += sol
    side["earned"] += earned
    if comm == staples.of(kernel, bw):
        side["food"] += q
    return q


def _moneyless(kernel: Any, w: Any) -> bool:
    """A world whose people has struck no money of its own (institutions: weighed, never staged) settles in goods."""
    from xylarium.kernel import institutions
    return institutions.founding(kernel) and w.currency not in institutions.stats(kernel).get("currencies", {})


def _send(kernel: Any, frm: Any, to: Any, comm: str, q: int, hops: List[Tuple[int, int]]) -> None:
    """Goods from one world to another: at once within a system, else aboard a counted convoy for the haul."""
    from xylarium.kernel import comms, staples
    staples.move(frm, comm, -q)
    if hops:
        stats(kernel).setdefault("in_transit", []).append({"to": to.id, "from": frm.id, "comm": comm, "q": q,
                                                          "due": kernel.cycle_count + len(hops),
                                                          "sector": to.sector_id,
                                                          "word": comms.own(kernel, frm.sector_id)})
    else:
        staples.move(to, comm, q)


def _barter(kernel: Any, buyer: Dict[str, Any], bw: Any, sw: Any, comm: str, q: int, unit: float, worth: float,
            risk: float, stale: float, hops: List[Tuple[int, int]], route: float, rec: Dict[str, Any]) -> int:
    """A people with no money pays in goods - only where the double coincidence holds: something it spares that the
    seller lacks (Jevons). Both lots travel, each counted; nothing is minted, no money moves. A road whose keepers
    want money it cannot pay is closed to it."""
    import math
    from xylarium.kernel import decide, news, staples
    if route > 0:
        return 0
    offer = None
    for g in sorted(_goods(kernel, bw)):
        if g == comm:
            continue
        spare = staples.surplus(kernel, bw, g)
        lack = staples.reserve(kernel, sw, g) - staples.held(sw, g)
        word = news.heard(kernel, bw.sector_id, sw.sector_id, g) or news.heard(kernel, bw.sector_id, bw.sector_id, g)
        if spare > 0 and lack > 0 and word and word[0] > 0:
            offer = (g, spare, lack, word[0])
            break
    if offer is None:
        return 0                                                  # no coincidence of wants: no trade
    g, spare, lack, price_g = offer
    q = min(q, int(min(spare, lack) * price_g / max(1e-9, unit)))
    if q <= 0:
        return 0
    pay = int(math.ceil(q * unit / price_g))
    m = decide.mind_of_planet(kernel, bw)
    if decide.choose(kernel, [decide.option("barter", q * (unit + risk + stale), q * worth)], m,
                     bw.id, sw.id, comm, "barter") is None:
        return 0
    _send(kernel, sw, bw, comm, q, hops)
    _send(kernel, bw, sw, g, pay, list(reversed(hops)))
    rec["value"] += q * unit
    rec["barter"] = rec.get("barter", 0.0) + q * unit
    rec["units"][comm] = rec["units"].get(comm, 0) + q
    return q


def trade(kernel: Any, buyer: Dict[str, Any], seller: Dict[str, Any], rec: Dict[str, Any]) -> int:
    """A year's trade one way under a treaty: the buyer's wants met from the seller's surpluses."""
    from xylarium.kernel import polity, staples
    bworlds = polity._worlds_of(kernel, buyer)
    sworlds = polity._worlds_of(kernel, seller)
    if not bworlds or not sworlds:
        return 0
    realm = polity._polities(kernel).get(buyer["realm"])
    capital = kernel.get_planet(realm["capital"]) if realm else None
    tariff = _taxes(kernel, buyer)
    wants = []
    for w in bworlds:
        for comm in _goods(kernel, w):
            lack = staples.reserve(kernel, w, comm) - staples.held(w, comm)
            if lack > 0:
                wants.append((lack, w.id, w, comm))
    moved = 0
    for lack, _, bw, comm in sorted(wants, key=lambda x: (-x[0], x[1])):
        for sw in sorted(sworlds, key=lambda s: (-staples.surplus(kernel, s, comm), s.id)):
            if lack <= 0:
                break
            got = _ship(kernel, buyer, seller, bw, sw, comm, lack, capital, tariff, rec)
            lack -= got
            moved += got
    return moved


def delivered(kernel: Any, rec_id: str, partner_id: str) -> Optional[Dict[str, Any]]:
    """What last year's commerce brought a sovereign from a partner - food units and the money its sales earned - or
    None where no year of commerce has yet been measured between them."""
    if "commerce" not in getattr(kernel, "state", {}):
        return None
    y = stats(kernel)["last"].get(_pair(rec_id, partner_id))
    if y is None:
        return None
    came = y["flows"].get(f"{partner_id}>{rec_id}", {})
    went = y["flows"].get(f"{rec_id}>{partner_id}", {})
    return {"food": came.get("food", 0), "earned": went.get("earned", 0)}


def model(kernel: Any, people: str) -> Dict[str, Any]:
    """A people's economic model, read from its measures."""
    from xylarium.kernel import regimes, relations, rent
    worlds = relations._peoples(kernel).get(people) or []
    if not worlds:
        return {}
    cap = max(worlds, key=lambda w: (w.population, w.id))
    pop = sum(w.population for w in worlds) or 1
    take = sum(rent.of(w) * w.population for w in worlds) / pop
    bear = sum(rent.bearable(kernel, w) * w.population for w in worlds) / pop
    t = stats(kernel)["peoples"].get(people, {"sold": 0.0, "bought": 0.0})
    out = 4 * relations._output_sol(kernel, worlds)
    return {"regime": regimes.regime(kernel, cap.currency), "controls": regimes.controlled(kernel, cap.currency),
            "rent": round(take, 3), "bearable": round(bear, 3), "extractive": take > bear,
            "openness": round((t["sold"] + t["bought"]) / out, 4) if out > 0 else 0.0,
            "balance": round(t["sold"] - t["bought"], 1)}


def _brokered(kernel: Any, sov: Dict[str, Dict[str, Any]], year: Dict[str, Any]) -> List[Tuple[Dict[str, Any],
                                                                                         Dict[str, Any]]]:
    """The pairs a line's stewards broker: each line's house (its ancient people's sovereign) with every people its
    realms hold (constellations: the realm of each people's home, laid by that line) - where no treaty already moves
    their goods."""
    from xylarium.kernel import board, constellations, relations
    if "constellations" not in getattr(kernel, "state", {}):
        return []
    by_people: Dict[str, Dict[str, Any]] = {}
    for rec in sov.values():
        if not rec.get("ended"):
            by_people.setdefault(rec["people"], rec)
    out = []
    peoples = relations._peoples(kernel)
    for line in sorted(board.progenitors(kernel)):
        house = by_people.get(line)
        if house is None:
            continue
        for who in sorted(peoples):
            if who == line or who not in by_people or not peoples[who]:
                continue
            home = max(peoples[who], key=lambda p: (p.population, p.id))
            if constellations.line_of_realm(kernel, constellations.realm_of(kernel, home.sector_id)) != line:
                continue
            other = by_people[who]
            if _pair(house["id"], other["id"]) not in year:
                out.append((house, other))
    return out


def land(kernel: Any) -> int:
    """Convoys whose haul is sailed land their goods: with the buyer, or - its world gone - back with the seller, or
    adrift where it was bound (debris) if neither stands. Returns the units landed."""
    from xylarium.kernel import staples
    st = stats(kernel)
    keep, landed = [], 0
    for lot in st["in_transit"]:
        if lot["due"] > kernel.cycle_count:
            keep.append(lot)
            continue
        to = kernel.get_planet(lot["to"]) or kernel.get_planet(lot["from"])
        if to is not None:
            staples.move(to, lot["comm"], lot["q"])
            from xylarium.kernel import comms
            comms.land(kernel, to.sector_id, lot.get("word") or {})
        else:
            sec = kernel.sectors.get(lot["sector"])
            if sec is None:
                keep.append(lot)
                continue
            sec.debris = list(getattr(sec, "debris", []) or []) + [{"cargo": {lot["comm"]: lot["q"]}}]
        landed += lot["q"]
    st["in_transit"] = keep
    return landed


def in_transit(kernel: Any) -> Dict[str, int]:
    """Goods aboard the convoys, by good (the matter census counts them)."""
    out: Dict[str, int] = {}
    if "commerce" not in getattr(kernel, "state", {}):
        return out
    for lot in stats(kernel).get("in_transit", []):
        out[lot["comm"]] = out.get(lot["comm"], 0) + int(lot["q"])
    return out


def season(kernel: Any) -> List[str]:
    """Each season, convoys land; once a year, after the sovereigns have made their treaties, every treaty of trade
    - and every pair a line's stewards broker - moves its goods."""
    from xylarium.kernel import polity
    stats(kernel).setdefault("in_transit", [])
    land(kernel)
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    st = stats(kernel)
    sov = polity.sovereigns(kernel)
    year: Dict[str, Any] = {}
    peoples: Dict[str, Dict[str, float]] = {}
    for key, t in sorted(polity.stats(kernel)["treaties"].items()):
        if t["kind"] != "trade":
            continue
        a, b = sov.get(t["a"]), sov.get(t["b"])
        if a is None or b is None or a.get("ended") or b.get("ended"):
            continue
        rec = {"value": 0.0, "tolls": 0.0, "tariff": 0.0, "closed": 0, "units": {}, "flows": {}}
        trade(kernel, a, b, rec)
        trade(kernel, b, a, rec)
        year[_pair(a["id"], b["id"])] = rec
    for a, b in _brokered(kernel, sov, year):                # a line's stewards broker its realms' trade with its house
        rec = {"value": 0.0, "tolls": 0.0, "tariff": 0.0, "closed": 0, "units": {}, "flows": {}, "brokered": True}
        trade(kernel, a, b, rec)
        trade(kernel, b, a, rec)
        year[_pair(a["id"], b["id"])] = rec
    for rec in year.values():
        for flow, f in rec["flows"].items():
            s_id, b_id = flow.split(">")
            peoples.setdefault(sov[s_id]["people"], {"sold": 0.0, "bought": 0.0})["sold"] += f["value"]
            peoples.setdefault(sov[b_id]["people"], {"sold": 0.0, "bought": 0.0})["bought"] += f["value"]
    st["last"] = year
    st["peoples"] = peoples
    total = sum(r["value"] for r in year.values())
    st["history"].append({"cycle": kernel.cycle_count, "value": round(total, 1),
                          "tolls": round(sum(r["tolls"] for r in year.values()), 1),
                          "tariff": round(sum(r["tariff"] for r in year.values()), 1),
                          "closed": sum(r["closed"] for r in year.values()),
                          "treaties": len(year), "moving": sum(1 for r in year.values() if r["value"] > 0)})
    del st["history"][:-YEAR_KEEP]
    st["traded"] += total
    if not total:
        return []
    return [f"[COMMERCE] {sum(1 for r in year.values() if r['value'] > 0)} of {len(year)} trade treaties moved "
            f"{total:,.0f} SOL of goods this year."]


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"traded": round(st["traded"]), "last_year": st["history"][-1] if st["history"] else None}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="commerce",
    state=lambda: {"last": {}, "peoples": {}, "history": [], "traded": 0.0, "in_transit": []},
    season=season,
    summary=summary,
))
