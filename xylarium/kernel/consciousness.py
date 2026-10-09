"""
Xylarium consciousness: what the ancients' councils make, the progenitors' parliaments carry and the peoples receive
(operator rulings 2026-10-09, Concordance 3.9; measured on the H - information - lane).

  PRODUCED   by a council (an ancients' house's seated minds): the H-lane discharge its minds' judged court
             closures carried (court.py's deeds: the mu the court paid, its fourth lane), and - owed until the hypha
             sells it - the mu it spends on the hypha's intelligence at the court's read price.
  CARRIED    by the house's progenitor line, its PARLIAMENT, out over the throats its network keeps: from the
             house's home, each throat a hop, and at every hop a share is lost - kept exp(-span / lambda) across a
             span of `span` kpc, lambda the core bell's wavelength (field.wavelength_kpc: light's round trip to the
             rim, the field's own coherence length) - derived from the span, never declared. Each handoff transduces
             it into the receiver's terms; what is lost is booked as dissipated.
  RECEIVED   by every people the network reaches (its home and the far ends of its throats), an equal part of what
             arrives there - held, and FADING at the people's own forgetting rate (knowledge.forgetting: it must
             keep arriving - a flow, never a grant). What it holds lifts its FLUID INTELLIGENCE (coordinator's
             ruling): gain = held / (held + its information knowledge), both information - dimensionless and
             saturating (a people that knows little is lifted most; none passes 1); joined with the fluid it proves
             by its own work as 1 - (1 - proven)(1 - gain), so knowledge.experience = stock x (1 + fluid) reads it.
             The bridge, one H unit = one knowledge unit of information, is DECLARED until derived.
  PARLIAMENTS are emergent: every progenitor line whose throats join one connected network sits in that
             network's parliament - two lines whose throats link are one parliament; they merge as their networks
             connect and split if a link is lost. A council's consciousness goes out over its house's parliament.
"""

import heapq
import math
from fractions import Fraction
from typing import Any, Dict, List, Tuple

H = 3                           # the lanes are S, G, T, H: consciousness rides the fourth


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "consciousness")


def produced(kernel: Any, house: str) -> Fraction:
    """What a council has produced since it was last read: its court closures' H-lane discharge."""
    from xylarium.kernel import court
    st = stats(kernel)
    total = Fraction(((court.stats(kernel)["of"].get(house) or {}).get("mu") or ["0"] * 4)[H])
    seen = Fraction(st.setdefault("read", {}).get(house, "0"))
    st["read"][house] = str(total)
    return max(Fraction(0), total - seen)


def kept(span_kpc: float) -> Fraction:
    """The share a handoff across a throat of `span_kpc` keeps: exp(-span / lambda), on the grid."""
    from xylarium.kernel import field
    return field.grid(math.exp(-span_kpc / field.wavelength_kpc()))


def parliaments(kernel: Any) -> Dict[str, frozenset]:
    """Each progenitor line's parliament: the lines whose living throats join one connected network with its own."""
    from xylarium.kernel import transit
    parent: Dict[Any, Any] = {}

    def find(x: Any) -> Any:
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    lines = set()
    for w in transit.stats(kernel)["worms"].values():
        who = w.get("builders") or w.get("owner")
        if not who or w.get("dormant") is not None:
            continue
        lines.add(who)
        for end in (w["a"], w["b"]):                      # a line joins the systems its throats open on
            parent[find(("line", who))] = find(("sys", end))
    out: Dict[str, frozenset] = {}
    for who in lines:
        root = find(("line", who))
        out[who] = frozenset(l for l in lines if find(("line", l)) == root)
    return out


def reach(kernel: Any, line: str) -> Dict[str, Fraction]:
    """The peoples a line's parliament reaches over its throats, each with the share that reaches it (the best path
    from the house's home: shares multiply hop by hop)."""
    from xylarium.kernel import cosmos, relations, spheres, transit
    home = spheres._home(kernel, line)
    if home is None:
        return {}
    members = parliaments(kernel).get(line, frozenset({line}))
    worms = [w for w in transit.stats(kernel)["worms"].values()
             if (w.get("builders") or w.get("owner")) in members and w.get("dormant") is None]
    adj: Dict[int, List[Tuple[int, Fraction]]] = {}
    for w in worms:
        d = cosmos.distance_kpc(kernel, w["a"], w["b"])
        if d is None:
            continue
        k = kept(float(d))
        adj.setdefault(w["a"], []).append((w["b"], k))
        adj.setdefault(w["b"], []).append((w["a"], k))
    best: Dict[int, Fraction] = {home.sector_id: Fraction(1)}
    heap = [(-1.0, home.sector_id)]
    while heap:
        _, s = heapq.heappop(heap)
        for t, k in adj.get(s, ()):
            share = best[s] * k
            if share > best.get(t, Fraction(0)):
                best[t] = share
                heapq.heappush(heap, (-float(share), t))
    out: Dict[str, Fraction] = {}
    for who, worlds in relations._peoples(kernel).items():
        got = max((best.get(w.sector_id, Fraction(0)) for w in worlds), default=Fraction(0))
        if got > 0:
            out[who] = got
    return out


def gain(kernel: Any, who: str) -> float:
    """What the consciousness a people holds adds to its fluid intelligence: held / (held + its information
    knowledge) - 0 where it holds none."""
    from xylarium.kernel import knowledge
    if not hasattr(kernel, "state") or "consciousness" not in kernel.state:
        return 0.0
    held = float(Fraction((stats(kernel).get("held") or {}).get(who, "0")))
    if held <= 0:
        return 0.0
    return held / (held + max(0.0, knowledge.stocks(kernel, who).get("information", 0.0)))


def _fade(kernel: Any) -> None:
    """What every people holds fades at its own forgetting rate, over the years since it was last read."""
    from xylarium.kernel import cosmos, field, knowledge, polity
    st = stats(kernel)
    now = float(cosmos.deep_gyr(kernel)) * 1e9 if cosmos.is_cosmic(kernel) else \
        kernel.cycle_count / (4 * polity._quarter())                 # in years
    years = max(0.0, now - float(st.get("faded_at", now)))
    st["faded_at"] = now
    held = st.setdefault("held", {})
    for who in list(held):
        left = Fraction(held[who]) * field.grid(math.exp(-knowledge.forgetting(kernel, who) * years))
        if left > 0:
            held[who] = str(left)
        else:
            held.pop(who)


def season(kernel: Any) -> List[str]:
    """Once a year: what each people holds fades; each council's new consciousness goes out over its house's
    parliament to the peoples it reaches."""
    from xylarium.kernel import board, court, polity
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    st = stats(kernel)
    _fade(kernel)
    lines = board.progenitors(kernel)
    for house in court.houses(kernel):
        made = produced(kernel, house)
        if made <= 0:
            continue
        st["made"] = str(Fraction(st.get("made", "0")) + made)
        shares = reach(kernel, house) if house in lines else {house: Fraction(1)}
        if not shares:
            shares = {house: Fraction(1)}
        part = made / len(shares)
        rec = st.setdefault("received", {})
        lost = Fraction(0)
        held = st.setdefault("held", {})
        for who, share in sorted(shares.items()):
            rec[who] = str(Fraction(rec.get(who, "0")) + part * share)
            held[who] = str(Fraction(held.get(who, "0")) + part * share)
            lost += part * (1 - share)
        st["dissipated"] = str(Fraction(st.get("dissipated", "0")) + lost)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"made": st.get("made", "0"), "dissipated": st.get("dissipated", "0"),
            "peoples_reached": len(st.get("received") or {})}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="consciousness", state=lambda: {"read": {}, "received": {}, "held": {}},
                             season=season, summary=summary))
