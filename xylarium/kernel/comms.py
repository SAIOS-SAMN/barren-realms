"""
Xylarium comms: word never outruns what carries it.

Every system keeps a VIEW of every port's prices it has heard of - each entry stamped with the cycle the word left
its port. A port always knows its own prices as they stand. Everything else arrives with something physical:

  RUMOUR    word rides the goods themselves: a convoy landing (commerce) brings its seller's prices as they stood
            when it sailed.
  COURIER   word rides real traffic: every ship that arrives at a port trades views with it - what it heard where it
            has been for what the port has heard - newest word kept (arrive). No phantom ship: only captains,
            haulers and convoys that actually sailed carry anything.
  LIGHT     a signal's light-time (signals.py) is the floor only where no lane, fold or gateway joins two places -
            within a play-span it carries no market word between systems, so nothing here waits on it.
  RELAYS    a line whose people has the capability (technology: "relays") may keep relay POSTS on its realms' lanes:
            built from counted goods (EQUIPMENT bought at a port with the line's fund, held in the post), with
            upkeep burned from that fund each quarter. A post carries word across its lane one hop per jump time
            (a cycle), continuously - the gain is the steady feed, not a speed beyond the ships'. A post goes dark
            when its upkeep goes unpaid or its lane is closed to its keeper (war, blockade): that link falls back to
            couriers and rumour. Posts of different lines join only where their peoples speak one protocol
            (contact.protocol: the emergent standard); at a seam, word is re-carried by courier.

A view's age is what a trader pays for acting on it (news.age_cost); a far port heard of by nothing is not heard at
all - and goods not priced are not bought.

Information is a market. A line whose network carries a port's word may SELL a FEED of it to a sovereign people
beyond its standard: each relay cycle the port's word, as the network holds it, reaches the buyer's home system. The
buyer weighs it against what old word cost it on that port's goods last year (commerce's stale_by); the fee is the
network's upkeep shared among its feeds (cost, no margin), paid each quarter through the exchanges into the line's
fund - a transfer, never a mint. No goods move: information is not matter, and it is never faster than its channel.
A line that withholds its word from a buyer (one it sanctions, is at war with, or holds at home) may still be TAPPED:
the buyer weighs the same feed plus what being caught would cost it (covert.py's watch: the line's eyes against its
own information mastery); caught, it is exposed and sanctioned like any covert operation.
"""

from typing import Any, Dict, List, Optional, Tuple
from xylarium.kernel.fx import hub as _hub

POST_HOLDS = 25                  # a relay post is a parked scout-class hull: its holds in EQUIPMENT (config catalog)

# Channels are data. Each kind: the capability that lets a people build it (technology: reached by its own path, no
# order), the counted goods an end is built from, its upkeep (a share of what it cost, burned each quarter at its
# money's rate), what it joins ("lane": a warp lane's two systems), and how long word takes across one join
# ("hop": a lane's jump time - one cycle). A new kind - photonic arrays, a throat's relay, anything a people learns
# to build - is a new entry here, never a new path in the code; its latency is never a constant beyond the
# physics of what it is.
CHANNELS: Dict[str, Dict[str, Any]] = {
    "relays": {"cap": "relays", "goods": {"EQUIPMENT": POST_HOLDS}, "joins": "lane", "latency": "hop"},
}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "comms")


def _key(sid: int, comm: str) -> str:
    return f"{sid}|{comm}"


def _lane(a: int, b: int) -> str:
    return f"{min(a, b)}|{max(a, b)}"


def own(kernel: Any, sid: int) -> Dict[str, List[int]]:
    """A port's own prices as they stand, stamped now."""
    from xylarium.kernel.economy import EconomyManager
    sec = kernel.sectors.get(sid)
    port = getattr(sec, "port", None)
    if port is None:
        return {}
    out = {}
    for comm in sorted(port.stock):
        buy, sell = EconomyManager.get_unit_prices(port, comm)
        if sell and sell > 0:
            out[_key(sid, comm)] = [int(sell), int(kernel.cycle_count), int(buy or 0)]   # [sells at, when, pays]
    return out


def merge(dst: Dict[str, List[int]], src: Dict[str, List[int]]) -> int:
    """Newer word wins; returns how many entries were renewed."""
    n = 0
    for k, entry in src.items():
        got = dst.get(k)
        if got is None or got[1] < entry[1]:
            dst[k] = list(entry)
            n += 1
    return n


def view(kernel: Any, sid: int) -> Dict[str, List[int]]:
    """What a system has heard (its port's own word renewed as it stands)."""
    v = stats(kernel)["views"].setdefault(str(sid), {})
    v.update(own(kernel, sid))
    return v


def arrive(kernel: Any, carrier: str, sid: int) -> None:
    """A ship arrives: where there is a port, it and the port trade what they have heard."""
    sec = kernel.sectors.get(sid)
    if sec is None or getattr(sec, "port", None) is None or not hasattr(kernel, "state"):
        return
    v = view(kernel, sid)
    c = stats(kernel)["carried"].setdefault(carrier, {})
    merge(v, c)
    merge(c, v)
    _arrived(kernel, carrier, sid)


def land(kernel: Any, sid: int, word: Dict[str, List[int]]) -> None:
    """Goods land with the word of where they were bought."""
    if word:
        merge(view(kernel, sid), word)


def heard(kernel: Any, at: int, port_sid: int, comm: str) -> Optional[Tuple[int, int]]:
    """A port's price of a good as heard at system `at`: (price, the cycle the word left), or None if no word of it
    has ever arrived."""
    if at == port_sid:
        got = own(kernel, port_sid).get(_key(port_sid, comm))
        return (got[0], got[1]) if got else None
    got = stats(kernel)["views"].get(str(at), {}).get(_key(port_sid, comm))
    return (got[0], got[1]) if got else None


def known_to(kernel: Any, captain: Any, sid: int, comm: str) -> Optional[Tuple[int, int, int]]:
    """A port's prices of a good as a captain knows them: (pays, sells at, age in cycles) - live where it stands;
    elsewhere the freshest word it carries or its present port holds. None if no word has reached it."""
    from xylarium.kernel.economy import EconomyManager
    if captain.sector_id == sid:
        port = getattr(kernel.sectors.get(sid), "port", None)
        if port is None:
            return None
        buy, sell = EconomyManager.get_unit_prices(port, comm)
        return int(buy or 0), int(sell or 0), 0
    key = _key(sid, comm)
    st = stats(kernel)
    cands = [st["carried"].get(f"captain:{captain.id}", {}).get(key),
             st["views"].get(str(captain.sector_id), {}).get(key)]
    best = max((c for c in cands if c), key=lambda c: c[1], default=None)
    if best is None:
        return None
    return (int(best[2]) if len(best) > 2 else 0), int(best[0]), int(kernel.cycle_count - best[1])


def sol(kernel: Any, sid: int, price: float, units: int = 1) -> float:
    """What a port's price really fetches, per unit, in the exchange's unit of account (institutions.hub_unit): the
    lot's proceeds through the pool (its fee and depth: fx.quote_via_sol), not a quoted rate."""
    from xylarium.kernel import institutions
    hub = institutions.hub_unit(kernel)
    port = getattr(kernel.sectors.get(sid), "port", None)
    cur = getattr(port, "currency", hub) if port is not None else hub
    if cur == hub or price <= 0:
        return float(price)
    fx = getattr(kernel, "fx_market", None)
    n = max(1, int(units))
    try:
        if fx is None or not fx.can_convert(cur, hub):
            return 0.0                                          # no market carries its money: it fetches nothing
        return float(fx.quote_via_sol(cur, hub, int(price * n))) / n
    except Exception:
        return 0.0


def best_heard_bid(kernel: Any, captain: Any, comm: str, exclude: Optional[int] = None) -> float:
    """The best price, in SOL, any port the captain has word of pays for a good - live where it stands, elsewhere the
    freshest it carries or its present port holds (0 if none)."""
    st = stats(kernel)
    words: Dict[str, List[int]] = {}
    for v in (st["carried"].get(f"captain:{captain.id}", {}), st["views"].get(str(captain.sector_id), {})):
        for k, e in v.items():
            if k.endswith(f"|{comm}") and (k not in words or words[k][1] < e[1]):
                words[k] = e
    best = 0.0
    for k, e in words.items():
        sid = int(k.split("|", 1)[0])
        if sid == exclude or len(e) < 3 or e[2] <= 0:
            continue
        best = max(best, sol(kernel, sid, e[2]))
    here = known_to(kernel, captain, captain.sector_id, comm) if captain.sector_id != exclude else None
    if here is not None and here[0] > 0:
        best = max(best, sol(kernel, captain.sector_id, here[0]))
    return best


def plan(kernel: Any, captain: Any, sid: int, expected: float, age: int) -> None:
    """A trader sets out on word: what it expects there, and how old that word is (measured on arrival)."""
    stats(kernel).setdefault("plans", {})[str(captain.id)] = {"to": int(sid), "expected": round(expected, 4),
                                                              "age": int(age), "at": int(kernel.cycle_count)}


def _arrived(kernel: Any, carrier: str, sid: int) -> None:
    """A trader that set out on word reaches its port: what it finds there, against what it expected."""
    if not carrier.startswith("captain:"):
        return
    st = stats(kernel)
    p = st.get("plans", {}).get(carrier.split(":", 1)[1])
    if p is None or p["to"] != sid:
        return
    cap = kernel.captains.get(carrier.split(":", 1)[1])
    if cap is None:
        return
    from xylarium.kernel import motive
    found = motive.prospects(kernel, cap, sid, "trader")             # now it stands there: live prices
    t = st.setdefault("trips", {"n": 0, "expected": 0.0, "found": 0.0, "age": 0})
    t["n"] += 1
    t["expected"] = round(t["expected"] + p["expected"], 4)
    t["found"] = round(t["found"] + found, 4)
    t["age"] += p["age"]
    st["plans"].pop(carrier.split(":", 1)[1], None)


# ---------------------------------------------------------------------- relays
def _protocol(kernel: Any, holder: Optional[str]) -> Optional[str]:
    from xylarium.kernel import contact
    try:
        return contact.protocol(kernel, holder) if holder else None
    except Exception:
        return None


def _keeper_of(kernel: Any, sid: int) -> Optional[str]:
    """The line whose realm a system lies in (constellations), if read."""
    from xylarium.kernel import constellations
    if "constellations" not in getattr(kernel, "state", {}):
        return None
    try:
        return constellations.line_of_realm(kernel, constellations.realm_of(kernel, sid))
    except Exception:
        return None


def latency_cycles(kernel: Any, post: Dict[str, Any], a: int, b: int) -> int:
    """How many cycles word takes across one post's join, by its channel's rule (never zero)."""
    rule = CHANNELS.get(post.get("channel", "relays"), CHANNELS["relays"])["latency"]
    if rule == "hop":
        return 1                                                      # a lane's jump time
    if rule == "light":
        from xylarium.kernel import news
        return max(1, int(round(news.light_years(kernel, a, b) * 100)))
    return 1


def _ends(lane: str) -> Tuple[int, int]:
    a, b = lane.split(":", 1)[-1].split("|")
    return int(a), int(b)


def relay(kernel: Any, tick: int = 0) -> int:
    """One cycle of the networks: word crosses every live post whose latency this cycle completes - one join - within
    its keeper's network, and passes to a port's own view where the port's realm speaks the keeper's protocol.
    Returns the entries renewed."""
    st = stats(kernel)
    nets = st["nets"]
    renewed = 0
    for lane, post in sorted(st["posts"].items()):
        if post.get("dark"):
            continue
        keeper = post["keeper"]
        net = nets.setdefault(keeper, {})
        a, b = _ends(lane)
        if tick % latency_cycles(kernel, post, a, b):
            continue
        va, vb = net.setdefault(str(a), {}), net.setdefault(str(b), {})
        tongue = _protocol(kernel, keeper)
        for sid, nv in ((a, va), (b, vb)):
            port_line = _keeper_of(kernel, sid)
            if getattr(kernel.sectors.get(sid), "port", None) is not None and \
                    (port_line in (None, keeper) or _protocol(kernel, port_line) == tongue):
                pv = view(kernel, sid)
                renewed += merge(nv, pv) + merge(pv, nv)
        snap_a, snap_b = dict(va), dict(vb)                   # one hop a cycle: from what each end held before
        renewed += merge(va, snap_b) + merge(vb, snap_a)
    return renewed


def post_cost_sol(kernel: Any, channel: str = "relays") -> float:
    """An end's goods at their price (its channel's goods, valued at backing.value_sol)."""
    from xylarium.kernel import backing
    return sum(n * float(backing.value_sol(kernel, c) or 0.0) for c, n in CHANNELS[channel]["goods"].items())


def _staleness(kernel: Any, a: int, b: int) -> float:
    """What acting on the word each end has of the other costs, as a share of its price (news.age_cost per unit),
    averaged over what they have heard of each other - 1 where they have heard nothing."""
    from xylarium.kernel import news
    shares = []
    now = kernel.cycle_count
    for here, there in ((a, b), (b, a)):
        v = stats(kernel)["views"].get(str(here), {})
        for k, entry in v.items():
            stamp = entry[1]
            if not k.startswith(f"{there}|"):
                continue
            sigma = news.sigma(kernel, there, k.split("|", 1)[1])
            shares.append(news.age_cost(1.0, (now - stamp) / 100.0, sigma))
    return sum(shares) / len(shares) if shares else 1.0


def build(kernel: Any) -> List[str]:
    """Once a year, each line whose people keeps the relays capability weighs a post on each busy lane of its realms
    it has none on: what fresher word would save the goods crossing it (their flow x its staleness) against the
    post's goods and upkeep over its horizon (decide.choose). Paid from the line's fund; the equipment is bought
    at a port in the fund's money and held in the post."""
    from fractions import Fraction
    from xylarium.config import POLICY_RATE_BASE
    from xylarium.kernel import endowments, relations
    st = stats(kernel)
    logs: List[str] = []
    peoples = relations._peoples(kernel)
    fund = endowments.stats(kernel)["funds"] if "endowments" in getattr(kernel, "state", {}) else {}
    for channel, spec in sorted(CHANNELS.items()):
        cost = post_cost_sol(kernel, channel)
        if cost > 0 and spec["joins"] == "lane":
            logs += _build_on_lanes(kernel, channel, spec, cost, peoples, fund)
    return logs


def _build_on_lanes(kernel: Any, channel: str, spec: Dict[str, Any], cost: float, peoples: Dict[str, Any],
                    fund: Dict[str, Any]) -> List[str]:
    from fractions import Fraction
    from xylarium.config import POLICY_RATE_BASE
    from xylarium.kernel import board, decide, fibres, technology
    st = stats(kernel)
    logs: List[str] = []
    for line in sorted(board.progenitors(kernel)):
        if not technology.has(kernel, line, spec["cap"]) or line not in fund or not peoples.get(line):
            continue
        home = max(peoples[line], key=lambda p: (p.population, p.id))
        m = decide.mind_of_planet(kernel, home)
        dev = fibres.state(kernel)["dev"]
        for lane_key, flow in sorted(dev.items(), key=lambda kv: (-kv[1], kv[0])):
            try:
                a, b = (int(x) for x in str(lane_key).split("-")[:2])     # fibres.key
            except ValueError:
                continue
            lane = f"{channel}:{_lane(a, b)}"
            if lane in st["posts"] or _keeper_of(kernel, a) != line:
                continue
            if fund[line]["sol"] < cost:
                break
            value = decide.worth(kernel, float(flow) * _staleness(kernel, a, b), m)
            upkeep = decide.worth(kernel, cost * POLICY_RATE_BASE, m)
            if decide.choose(kernel, [decide.option(f"{channel}_post", cost + upkeep, value)], m,
                             line, lane, "post") is None:
                continue
            goods = spec["goods"]
            sol_port = next((s.port for s in sorted(kernel.sectors.values(), key=lambda s: s.id)
                             if s.port is not None and s.port.currency == _hub()
                             and all(s.port.stock.get(c, 0) >= n for c, n in goods.items())), None)
            if sol_port is None:
                break                                             # no port sells its goods: nothing is built
            paid = int(cost)
            fund[line]["sol"] -= paid                             # the fund pays the port that sells them (a transfer)
            sol_port.treasury += paid
            for c, n in goods.items():
                sol_port.stock[c] -= n                            # the goods leave the port's shelves, into the post
            st["posts"][lane] = {"keeper": line, "channel": channel, "built": kernel.cycle_count, "goods": dict(goods),
                                 "upkeep": str(Fraction(paid) * Fraction(POLICY_RATE_BASE)), "dark": False}
            logs.append(f"[COMMS] The {line.split(':', 1)[-1]} raise a {channel} post on {lane}.")
    return logs


def upkeep(kernel: Any) -> None:
    """Each quarter every live post's upkeep is burned from its keeper's fund; a post unpaid, or on a lane closed to
    its keeper, goes dark (its goods stay in it, counted)."""
    from fractions import Fraction
    from xylarium.kernel import endowments, ledger, transit
    st = stats(kernel)
    fund = endowments.stats(kernel)["funds"] if "endowments" in getattr(kernel, "state", {}) else {}
    for lane, post in sorted(st["posts"].items()):
        a, b = _ends(lane)
        closed = transit.blocks(kernel, post["keeper"], a, b) or transit.blocks(kernel, post["keeper"], b, a)
        due = int(Fraction(post["upkeep"]))
        f = fund.get(post["keeper"])
        if closed or f is None or f["sol"] < due:
            post["dark"] = True
            continue
        f["sol"] -= due
        ledger.burn("relay_upkeep", due, _hub())
        post["dark"] = False


def posts_goods(kernel: Any) -> Dict[str, int]:
    """Goods held in relay posts (the matter census counts them)."""
    out: Dict[str, int] = {}
    if "comms" not in getattr(kernel, "state", {}):
        return out
    for post in stats(kernel)["posts"].values():
        for comm, n in post.get("goods", {}).items():
            out[comm] = out.get(comm, 0) + int(n)
    return out


def season(kernel: Any) -> List[str]:
    """Each quarter: upkeep, then the quarter's cycles of relaying (one hop a cycle); once a year: lines weigh new
    posts."""
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    upkeep(kernel)
    pay_feeds(kernel)
    if stats(kernel)["posts"]:
        for tick in range(FISCAL_QUARTER_CYCLES):
            relay(kernel, tick)
            deliver(kernel)
    if (kernel.cycle_count // FISCAL_QUARTER_CYCLES) % 4:
        return []
    return build(kernel) + subscribe(kernel)


# ---------------------------------------------------------------------- feeds (information is a market)
def _net_has(kernel: Any, line: str, port_sid: int) -> bool:
    """Does a line's live network carry word of this port?"""
    for v in stats(kernel)["nets"].get(line, {}).values():
        if any(k.startswith(f"{port_sid}|") for k in v):
            return True
    return False


def _withholds(kernel: Any, line: str, buyer: str) -> bool:
    """A line keeps its word from a people it sanctions, is at war with, or holds at home."""
    from xylarium.kernel import ascendance, covert
    if ascendance.ruling(kernel, buyer) in ("quarantine", "pending"):
        return True
    try:
        if covert.sanctioned(kernel, buyer, line):
            return True
    except Exception:
        pass
    wars = (getattr(kernel, "state", {}).get("realmwars") or {}).get("wars") or {}
    return any(w.get("status") == "open" and {line, buyer} <= {w.get("by"), w.get("sender"), w.get("taker")}
               for w in wars.values())


def _upkeep_of(kernel: Any, line: str) -> float:
    from fractions import Fraction
    return float(sum(Fraction(p["upkeep"]) for p in stats(kernel)["posts"].values()
                     if p["keeper"] == line and not p.get("dark")))


def subscribe(kernel: Any) -> List[str]:
    """Once a year, each sovereign people weighs a feed of each port whose old word cost it last year, from a line whose
    network carries that port's word - openly where the line deals with it, covertly where it does not."""
    from fractions import Fraction
    from xylarium.kernel import commerce, covert, decide, polity, spheres
    st = stats(kernel)
    logs: List[str] = []
    stale_by = commerce.stats(kernel).get("stale_by", {}) if "commerce" in kernel.state else {}
    if not stale_by or not st["posts"]:
        return logs
    lines = sorted({p["keeper"] for p in st["posts"].values() if not p.get("dark")})
    taken = {(f["buyer"], f["port"]) for f in st["feeds"].values()}
    people = {r["people"] for r in polity.sovereigns(kernel).values() if not r.get("ended")}
    for key, cost_year in sorted(stale_by.items()):
        buyer, port_sid = key.split("|")[0], int(key.split("|")[1])
        if buyer not in people or (buyer, port_sid) in taken:
            continue
        home = spheres._home(kernel, buyer)
        if home is None:
            continue
        for line in lines:
            if line == buyer or not _net_has(kernel, line, port_sid):
                continue
            n_feeds = sum(1 for f in st["feeds"].values() if f["provider"] == line)
            fee = _upkeep_of(kernel, line) / (1 + n_feeds)
            m = decide.mind_of_planet(kernel, home)
            value = decide.worth(kernel, cost_year / 4.0, m)
            covertly = _withholds(kernel, line, buyer)
            risk = 0.0
            if covertly:
                p = covert.catch(kernel, buyer, [line])
                risk = p * covert._exposure(kernel, buyer, None)
            if decide.choose(kernel, [decide.option("tap" if covertly else "feed",
                                                    decide.worth(kernel, fee, m) + risk, value)],
                             m, buyer, line, port_sid, "feed") is None:
                continue
            fid = f"{buyer}>{port_sid}@{line}"
            st["feeds"][fid] = {"buyer": buyer, "at": home.sector_id, "provider": line, "port": port_sid,
                                "fee": str(Fraction(fee)), "since": kernel.cycle_count, "covert": covertly}
            if covertly and covert._caught(kernel, covert.catch(kernel, buyer, [line]), buyer, line, "tap"):
                covert._expose(kernel, buyer, line, line, "tap", cost_year, None, logs)
                st["feeds"].pop(fid, None)
                break
            logs.append(f"[COMMS] The {buyer.split(':', 1)[-1]} {'tap' if covertly else 'buy'} the word of port "
                        f"{port_sid} from the {line.split(':', 1)[-1]}'s network.")
            break
    return logs


def pay_feeds(kernel: Any) -> None:
    """Each quarter every open feed's fee passes from the buyer's home treasury, through the exchanges, into the
    provider's fund (a transfer); a tap pays nothing to its victim (its cost was the risk); a feed unpaid lapses."""
    from fractions import Fraction
    from xylarium.kernel import endowments, exchanges, spheres
    st = stats(kernel)
    for fid, f in sorted(st["feeds"].items()):
        if f["covert"]:
            continue
        home = spheres._home(kernel, f["buyer"])
        fee = int(Fraction(f["fee"]))
        if home is None or home.treasury < fee:
            st["feeds"].pop(fid, None)
            continue
        if fee <= 0:
            continue
        home.treasury -= fee
        sol = exchanges.convert_at(kernel, home.sector_id, home.currency, _hub(), fee)
        endowments.credit(kernel, f["provider"], sol)


def deliver(kernel: Any) -> int:
    """A relay cycle's feeds: the port's word, as the provider's network holds it, into the buyer's home view."""
    st = stats(kernel)
    n = 0
    for f in st["feeds"].values():
        net = st["nets"].get(f["provider"], {})
        word = {}
        for v in net.values():
            word.update({k: e for k, e in v.items() if k.startswith(f"{f['port']}|")
                         and (k not in word or word[k][1] < e[1])})
        if word:
            n += merge(st["views"].setdefault(str(f["at"]), {}), word)
    return n


def market_readout(kernel: Any) -> Dict[str, Any]:
    """What the word is doing to the markets: the spread of each good's price across the ports (max/min - 1, from the
    ports' own boards), the traders' trips (expected on word, found on arrival, the gap, the word's mean age) and the
    live posts."""
    from xylarium.kernel.economy import EconomyManager
    spreads = {}
    for comm in ("ORE", "ORGANICS", "EQUIPMENT"):
        ps = [EconomyManager.get_unit_prices(s.port, comm)[1] for s in kernel.sectors.values()
              if s.port is not None and s.port.stock.get(comm, 0) > 0]
        ps = [p for p in ps if p and p > 0]
        if len(ps) > 1:
            spreads[comm] = round(max(ps) / min(ps) - 1.0, 4)
    t = stats(kernel).get("trips", {"n": 0, "expected": 0.0, "found": 0.0, "age": 0})
    n = max(1, t["n"])
    return {"spread": spreads, "trips": t["n"], "expected_mean": round(t["expected"] / n, 2),
            "found_mean": round(t["found"] / n, 2), "gap_mean": round((t["expected"] - t["found"]) / n, 2),
            "word_age_mean_cycles": round(t["age"] / n, 2),
            "posts": sum(1 for p in stats(kernel)["posts"].values() if not p.get("dark")),
            "feeds": sum(1 for f in stats(kernel).get("feeds", {}).values() if not f["covert"]),
            "taps": sum(1 for f in stats(kernel).get("feeds", {}).values() if f["covert"])}


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"views": len(st["views"]), "carriers": len(st["carried"]), "market": market_readout(kernel),
            "posts": sum(1 for p in st["posts"].values() if not p.get("dark")),
            "dark_posts": sum(1 for p in st["posts"].values() if p.get("dark"))}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="comms", state=lambda: {"views": {}, "carried": {}, "posts": {}, "nets": {},
                                                          "feeds": {}},
                             season=season, summary=summary))
