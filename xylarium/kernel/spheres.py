"""
Xylarium spheres: realms as spheres of influence - grown by the networks of the peoples who fold space, met where
they touch.

THE NETWORK. A people that has crossed (mastery.py: it can open a passage between the stars) keeps a network - the
passages it holds open, a spacing guild's lanes. A fold is a null flow (clocks.fold): it costs no time, so distance is
not what bounds a network. Energy is: each passage costs E_BRIDGE_J, and a people can open as many as the power it
puts to work (mastery.power_w) over the years of its own clock pays for. Its reach is the farthest system its passages
hold - no cap: a people that commands more power, longer, reaches farther. The ancients' networks are the oldest and,
fed by the longest histories, the widest: those are the progenitors' (board.py), who keep the flow between realms.

THE ORDER OF ARRIVAL. A network opens its passages nearest first (the galaxy's proper distance from its home; on the
settled board, the lanes' hops), and a system is held by whichever network reached it first - the same causal law
that settles a fold war (realmwars.py). A sphere of influence is what a network holds.

REALMS. A network's systems are cut into realms by its stewards' terms: everything it reached in one term of its
sender is one realm, a shell of the sphere - numbered in the order founded, never renumbered. A term is its sender's own generation
(fertility.py), read in the realm's clock (geometry.lapse at the realm's seat against the sender's home): a line near
the core, whose clocks run slow, keeps its stewards long as the outer realms count time. Stewards keep the flow
inside a realm (stewardship.py); the network's people - for the ancients, their progenitors - keep it between them.

CONTACT. When a passage reaches a system another network already holds, the two meet at once, and how they meet is
the style of the one arriving, read from what both are:
  war           its doctrine (federation.preferred_card of its whole-history alignment) stands two apart from what
                it reads in the other (or either takes, DELTA): it means to take what it found
  conglomerate  its senior sovereign's lead is wealth: the networks share their flow and trade
  alliance      its lead is security: they stand together, each keeping its own
  federation    otherwise: the realms are kept together - each sends a steward into the other's
A bond (any but war) lets each network's passages run through the other's systems without taking them. War is a
realm war (realmwars.py): the contested system goes to whichever takes it, and progenitor lines on both sides draw
the progenitors in.

TWO FRONTS. The ancients' networks spread outward from the core; the young peoples of the outer disc build theirs as
they cross, and the meetings happen on the seam between them (summary: where each contact lies from the core).
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

YEAR_S = 3.15576e7
ORDINALS = ("First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth")
BONDS = ("federation", "conglomerate", "alliance")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "spheres")


# ---------------------------------------------------------------------- names
def realm_id(who: str, ring: int) -> str:
    return f"{who.split(':', 1)[-1]}#{ring}"


def realm_name(rid: str) -> str:
    name, _, ring = rid.rpartition("#")
    if not ring.isdigit():
        return f"the realm {rid}"
    n = int(ring)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    nth = ORDINALS[n - 1] if 1 <= n <= len(ORDINALS) else f"{n}{suffix}"
    return f"the {nth} Reach of the {name}"


# ---------------------------------------------------------------------- who folds space
def crossed(kernel: Any, who: str) -> bool:
    from xylarium.kernel import annals, mastery
    if not who.startswith("civ:"):
        return False
    return mastery.crossed(kernel, who) or \
        "crossed" in ((annals.stats(kernel)["of"].get(who) or {}).get("passed", []) if "annals" in kernel.state else [])


def _home(kernel: Any, who: str) -> Optional[Any]:
    from xylarium.kernel import relations
    ws = relations._peoples(kernel).get(who) or []
    return max(ws, key=lambda w: (w.population, w.id)) if ws else None


def _years(kernel: Any, who: str) -> float:
    """A people's own years now: its clock in a cosmic universe (proper time), the lived years on the settled board."""
    from xylarium.kernel import clocks, cosmos
    if cosmos.is_cosmic(kernel):
        return clocks.now(kernel, who) * 1e9
    return kernel.cycle_count / 100.0


def generation(kernel: Any, who: str) -> float:
    from xylarium.kernel import fertility
    home = _home(kernel, who)
    return max(1.0, fertility.generation_of(kernel, home)) if home is not None else 1.0


def _lapse(kernel: Any, sector_id: Optional[int]) -> Optional[float]:
    from xylarium.kernel import cosmos
    if sector_id is None or not cosmos.is_cosmic(kernel):
        return None
    p = cosmos.position(kernel, sector_id)
    return p["lapse"] if p else None


def term_years(kernel: Any, rid: str) -> float:
    """A realm's steward's term, in the realm's own years: its sender's generation, read through the clocks - the
    realm's seat's lapse against the sender's home's (on the settled board, one clock for all)."""
    r = stats(kernel)["realms"].get(rid)
    if r is None:
        return 1.0
    net = stats(kernel)["nets"].get(r["presence"]) or {}
    gen = float(net.get("gen") or generation(kernel, r["presence"]))
    seat, home = _lapse(kernel, r["seat"]), _lapse(kernel, net.get("home"))
    return gen * (seat / home) if seat and home else gen


# ---------------------------------------------------------------------- the order a network opens its passages
def _order(kernel: Any, home: int) -> List[int]:
    """Every charted system, nearest first from a home: proper distance in a galaxy, the lanes' hops on the board."""
    from xylarium.kernel import cache, cosmos, universe

    def build() -> List[int]:
        if cosmos.is_cosmic(kernel):
            ds = [(cosmos.distance_kpc(kernel, home, s), s) for s in kernel.sectors]
            return [s for d, s in sorted((d, s) for d, s in ds if d is not None)]
        hops = universe.warp_distances(kernel.sectors, home)
        return [s for _, s in sorted((d, s) for s, d in hops.items())]
    if not hasattr(kernel, "caches"):
        return build()
    return cache.stamped(kernel, "sphere_order", home, (len(kernel.sectors), kernel.cycle_count // 10000), build)


def distance(kernel: Any, a: int, b: int) -> float:
    from xylarium.kernel import cosmos, universe
    if cosmos.is_cosmic(kernel):
        d = cosmos.distance_kpc(kernel, a, b)
        return d if d is not None else float("inf")
    return float(universe.warp_distances(kernel.sectors, a).get(b, float("inf")))


# ---------------------------------------------------------------------- holding
def owner(kernel: Any, sector_id: int) -> Optional[str]:
    """The realm that holds a system (the first network to reach it), if any."""
    return stats(kernel)["owner"].get(str(sector_id))


def presence(kernel: Any, rid: Optional[str]) -> Optional[str]:
    r = stats(kernel)["realms"].get(rid) if rid else None
    return r["presence"] if r else None


def bond(kernel: Any, a: str, b: str) -> Optional[Dict[str, Any]]:
    return stats(kernel)["bonds"].get("|".join(sorted((a, b))))


def _realm_for(kernel: Any, who: str, net: Dict[str, Any], sector_id: int) -> str:
    """The realm a newly reached system joins: the shell of the network's present term - a new realm founded when a
    term has passed since the last (numbered in the order they were founded; the term each began in is kept)."""
    st = stats(kernel)
    term = 1 + int(max(0.0, _years(kernel, who) - net["t0"]) // float(net["gen"]))
    if net.get("term") == term and net.get("rid") in st["realms"]:
        return net["rid"]
    n = int(net.get("n", 0)) + 1
    rid = realm_id(who, n)
    net["term"], net["rid"], net["n"] = term, rid, n
    st["realms"][rid] = {"id": rid, "presence": who, "ring": n, "term": term, "seat": sector_id,
                         "since": kernel.cycle_count, "sectors": []}
    from xylarium.kernel import history
    history.event(kernel, "REALM_FOUNDED", f"{realm_name(rid)} is founded", actors=[who],
                  cause=("its network's first passages" if n == 1 else
                         f"its network grows on, {term - 1} of its stewards' terms after its first"),
                  data={"realm": rid, "seat": sector_id})
    return rid


def _hold(kernel: Any, who: str, net: Dict[str, Any], sector_id: int) -> str:
    rid = _realm_for(kernel, who, net, sector_id)
    st = stats(kernel)
    st["owner"][str(sector_id)] = rid
    st["v"] = st.get("v", 0) + 1                             # who holds what has changed
    st["realms"][rid]["sectors"].append(sector_id)
    net["held"].append(sector_id)
    d = distance(kernel, net["home"], sector_id)
    if d != float("inf"):
        net["radius"] = max(float(net.get("radius", 0.0)), d)
    return rid


def transfer(kernel: Any, sector_id: int, to_who: str) -> None:
    """A system taken in war goes to the taker's present realm."""
    st = stats(kernel)
    old = owner(kernel, sector_id)
    if old and old in st["realms"]:
        r = st["realms"][old]
        if sector_id in r["sectors"]:
            r["sectors"].remove(sector_id)
        prev = st["nets"].get(r["presence"])
        if prev and sector_id in prev["held"]:
            prev["held"].remove(sector_id)
    st["owner"].pop(str(sector_id), None)
    st["v"] = st.get("v", 0) + 1
    net = st["nets"].get(to_who)
    if net is not None:
        _hold(kernel, to_who, net, sector_id)


# ---------------------------------------------------------------------- contact
def style(kernel: Any, who: str, other: str) -> str:
    """How a people meets a held system: the style of the one arriving, read from what both are."""
    from xylarium.config import POLICY_ORDER
    from xylarium.kernel import alignment, federation, polity, reputation
    mine, theirs = _home(kernel, who), _home(kernel, other)
    own = alignment.doctrine(mine.civilization) if mine is not None and mine.civilization is not None else 0.0
    seen = reputation.read(kernel, who, other)
    if seen is None:
        seen = alignment.doctrine(theirs.civilization) if theirs is not None and theirs.civilization is not None \
            else 0.0
    ca, cb = federation.preferred_card(own), federation.preferred_card(seen)
    if abs(POLICY_ORDER.index(ca) - POLICY_ORDER.index(cb)) >= 2 or ca == "DELTA":
        return "war"
    recs = polity.of_people(kernel, who) if "polity" in kernel.state else []
    if recs:
        senior = min(recs, key=lambda s: (s["since"], s["id"]))
        from xylarium.kernel import mindcore as mc
        lead = mc.lead(polity.chain(kernel, senior, {senior["id"]: polity.field(kernel, senior)}), polity.BOOKS)
        if lead is not None and lead[1] == "wealth":
            return "conglomerate"
        if lead is not None and lead[1] == "security":
            return "alliance"
    return "federation"


def _contact(kernel: Any, who: str, sector_id: int, logs: List[str]) -> None:
    """A passage reaches a system another network holds: they meet now - a bond, or a realm war."""
    from xylarium.kernel import history, polity, realmwars, relations
    st = stats(kernel)
    held_by = owner(kernel, sector_id)
    other = presence(kernel, held_by)
    if other is None or other == who:
        return
    key = "|".join(sorted((who, other)))
    if key in st["bonds"] or any(w["status"] == "open" and {w.get("presence_a"), w.get("presence_b")} == {who, other}
                                 for w in realmwars.stats(kernel)["wars"].values()):
        return
    how = style(kernel, who, other)
    net = st["nets"][who]
    mine = _realm_for(kernel, who, net, sector_id)
    st["contacts"].append({"a": who, "b": other, "kind": how, "cycle": kernel.cycle_count, "sector": sector_id,
                           "r_kpc": _r(kernel, sector_id)})
    na, nb = who.split(":", 1)[-1], other.split(":", 1)[-1]
    if how == "war":
        w = realmwars.declare(kernel, mine, held_by, who, sector_id)
        w["presence_a"], w["presence_b"] = who, other
        logs.append(f"[CONTACT] The {na} reach {realm_name(held_by)} and make war for it.")
        return
    st["bonds"][key] = {"kind": how, "a": who, "b": other, "since": kernel.cycle_count, "sector": sector_id}
    if who.startswith("civ:") and other.startswith("civ:"):
        relations.pacts(kernel).setdefault(relations._pair(who, other), {"since": kernel.cycle_count, "by": how})
    ra = polity.of_people(kernel, who) if "polity" in kernel.state else []
    rb = polity.of_people(kernel, other) if "polity" in kernel.state else []
    if ra and rb and how in ("conglomerate", "alliance"):
        a = min(ra, key=lambda s: (s["since"], s["id"]))
        b = min(rb, key=lambda s: (s["since"], s["id"]))
        t = polity.treaty(kernel, a["id"], b["id"])
        kind = "trade" if how == "conglomerate" else "defense"
        if t is None or t["kind"] != kind:
            polity._make(kernel, a, b, kind, f"their networks met: a {how}")
    title = {"federation": "federate", "conglomerate": "join their networks in a conglomerate",
             "alliance": "ally"}[how]
    history.event(kernel, how.upper(), f"The {na} and the {nb} {title}", actors=[who, other],
                  cause=f"the {na}'s passages reached {realm_name(held_by)}", data={"sector": sector_id, "kind": how})
    logs.append(f"[CONTACT] The {na} and the {nb} {title}.")


def _r(kernel: Any, sector_id: int) -> Optional[float]:
    from xylarium.kernel import cosmos
    p = cosmos.position(kernel, sector_id) if cosmos.is_cosmic(kernel) else None
    return round(p["r"], 4) if p else None


# ---------------------------------------------------------------------- the networks grow
def _begin(kernel: Any, who: str, logs: List[str]) -> None:
    home = _home(kernel, who)
    if home is None:
        return
    st = stats(kernel)
    st["nets"][who] = net = {"home": home.sector_id, "since": kernel.cycle_count, "t0": _years(kernel, who),
                             "t": _years(kernel, who), "owed": "0", "held": [], "radius": 0.0,
                             "gen": generation(kernel, who)}
    if owner(kernel, home.sector_id) is None:
        _hold(kernel, who, net, home.sector_id)
    else:
        _contact(kernel, who, home.sector_id, logs)            # it crosses inside another's sphere: they meet now


def grow(kernel: Any, who: str, net: Dict[str, Any], logs: List[str]) -> None:
    """Its power over the years since last paid in passages, each opened to the nearest system it does not hold."""
    from xylarium.kernel import mastery, relations
    now = _years(kernel, who)
    worlds = relations._peoples(kernel).get(who) or []
    if not worlds:
        return
    paid = Fraction(max(0.0, mastery.power_w(kernel, worlds) * (now - float(net["t"])) * YEAR_S)) / \
        Fraction(mastery.E_BRIDGE_J)
    from xylarium.kernel import transit
    paid += transit.drain_revenue(kernel, who)              # what its lanes collected pays for more of them
    net["t"] = now
    owed = Fraction(net["owed"]) + paid
    if owed < 1:
        net["owed"] = str(owed)
        return
    held = set(net["held"])
    blocked = False
    for s in _order(kernel, net["home"]):
        if owed < 1:
            break
        if s in held:
            continue
        rid = owner(kernel, s)
        if rid is None:
            _hold(kernel, who, net, s)
            owed -= 1
            continue
        other = presence(kernel, rid)
        if other == who:
            continue
        if bond(kernel, who, other) is not None:
            continue                                         # a bonded network's systems: the flow runs through
        _contact(kernel, who, s, logs)
        owed -= 1
        if bond(kernel, who, other) is None:
            blocked = True                                   # at war on this front: it presses no further this year
            break
    # what it could not spend is held for later (stored power); with nothing left within its charts to reach, the
    # whole passages it could not open are banked as energy (transit.py: a line forges throats from that bank)
    if blocked:
        net["owed"] = str(owed)
    else:
        net["bank_j"] = float(net.get("bank_j", 0.0)) + int(owed) * mastery.E_BRIDGE_J
        net["owed"] = str(owed - int(owed))


def season(kernel: Any) -> List[str]:
    """Once a year: the peoples that fold space begin their networks, and every network grows by its power."""
    from xylarium.kernel import polity, relations
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    logs: List[str] = []
    ensure(kernel, logs)
    st = stats(kernel)
    living = relations._peoples(kernel)
    for who in sorted(st["nets"]):
        if who in living:
            grow(kernel, who, st["nets"][who], logs)
        elif st["nets"][who]["held"]:
            lapse(kernel, who, logs)
    return logs


def lapse(kernel: Any, who: str, logs: List[str]) -> None:
    """A people that has fallen holds nothing: its passages close, its realms lapse, its systems are no one's - the
    next network to reach them holds them (no war is fought with the dead)."""
    from xylarium.kernel import history
    st = stats(kernel)
    net = st["nets"][who]
    for sid in list(net["held"]):
        rid = st["owner"].pop(str(sid), None)
        if rid in st["realms"] and sid in st["realms"][rid]["sectors"]:
            st["realms"][rid]["sectors"].remove(sid)
    n = len(net["held"])
    net["held"] = []
    st["v"] = st.get("v", 0) + 1
    for k in [k for k, b in st["bonds"].items() if who in (b["a"], b["b"])]:
        st["bonds"].pop(k)
    history.event(kernel, "REALM_LAPSES", f"The realms of the {who.split(':', 1)[-1]} lapse",
                  cause=f"its people has fallen: its passages close and its {n} systems are no one's")
    logs.append(f"[SPHERES] The {who.split(':', 1)[-1]} are gone: {n} systems are no one's.")


def ensure(kernel: Any, logs: Optional[List[str]] = None) -> None:
    """Every crossed people has a network (begun at its home)."""
    from xylarium.kernel import relations
    st = stats(kernel)
    for who in sorted(relations._peoples(kernel)):
        if who not in st["nets"] and crossed(kernel, who):
            _begin(kernel, who, logs if logs is not None else [])


# ---------------------------------------------------------------------- readings
def realms(kernel: Any) -> List[str]:
    if not hasattr(kernel, "state"):
        return []
    ensure(kernel)
    return sorted(r for r, rec in stats(kernel)["realms"].items() if rec["sectors"])


def radius(kernel: Any, who: str) -> float:
    net = stats(kernel)["nets"].get(who) if hasattr(kernel, "state") else None
    return float(net.get("radius", 0.0)) if net else 0.0


def kind_of(kernel: Any, who: str) -> str:
    """'progenitor' for an ancient people's network (its progenitor line keeps it), else 'young'."""
    from xylarium.kernel import board
    line = board.progenitors(kernel).get(who)
    return "progenitor" if line is not None and line.get("ancient") is not None else "young"


def fronts(kernel: Any) -> Dict[str, Any]:
    """The two fronts and their seam: each network's reach and where it lies from the core, by kind; and each
    contact by the kinds that met and where (kpc from the core, in a galaxy)."""
    from xylarium.kernel import cosmos
    st = stats(kernel)
    out: Dict[str, Any] = {"progenitor": [], "young": [], "seam": []}
    for who, net in sorted(st["nets"].items()):
        p = cosmos.position(kernel, net["home"]) if cosmos.is_cosmic(kernel) else None
        out[kind_of(kernel, who)].append({"people": who, "systems": len(net["held"]), "reach": net["radius"],
                                         "home_r_kpc": round(p["r"], 4) if p else None})
    for c in st["contacts"]:
        out["seam"].append({"kinds": sorted((kind_of(kernel, c["a"]), kind_of(kernel, c["b"]))), "met": c["kind"],
                            "r_kpc": c.get("r_kpc"), "cycle": c["cycle"]})
    return out


def render(kernel: Any) -> str:
    st = stats(kernel)
    f = fronts(kernel)
    lines = ["=== THE SPHERES ===",
             f"  Progenitor networks: {len(f['progenitor'])}; young networks: {len(f['young'])}; "
             f"meetings on the seam: {sum(1 for s in f['seam'] if s['kinds'] == ['progenitor', 'young'])} "
             f"of {len(f['seam'])}"]
    for who, net in sorted(st["nets"].items(), key=lambda kv: -len(kv[1]["held"])):
        if not net["held"]:
            continue
        rs = sorted({owner(kernel, s) for s in net["held"]} - {None})
        lines.append(f"  The {who.split(':', 1)[-1]}: {len(net['held'])} systems, reach {net['radius']:.3g}, "
                     f"{len(rs)} realm(s)")
    for b in st["bonds"].values():
        lines.append(f"  {b['kind']}: the {b['a'].split(':', 1)[-1]} and the {b['b'].split(':', 1)[-1]}")
    return "\n".join(lines)


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    kinds: Dict[str, int] = {}
    for c in st["contacts"]:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    return {"networks": len(st["nets"]), "realms": len([r for r in st["realms"].values() if r["sectors"]]),
            "held": len(st["owner"]), "contacts": kinds, "bonds": len(st["bonds"]),
            "seam": sum(1 for c in st["contacts"] if {kind_of(kernel, c["a"]), kind_of(kernel, c["b"])}
                        == {"progenitor", "young"})}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="spheres",
    state=lambda: {"nets": {}, "owner": {}, "realms": {}, "bonds": {}, "contacts": []},
    season=season,
    summary=summary,
))
