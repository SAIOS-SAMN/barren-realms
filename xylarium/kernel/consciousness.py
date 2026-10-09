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
             arrives there - as FLUID INTELLIGENCE, multiplying how far its knowledge reaches (knowledge.experience =
             stock x (1 + fluid)). How an amount on the H lane becomes a share of fluid is owed (asked of the
             coordinator); until ruled it is booked, not yet applied.
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


def reach(kernel: Any, line: str) -> Dict[str, Fraction]:
    """The peoples a line's parliament reaches over its throats, each with the share that reaches it (the best path
    from the house's home: shares multiply hop by hop)."""
    from xylarium.kernel import cosmos, relations, spheres, transit
    home = spheres._home(kernel, line)
    if home is None:
        return {}
    worms = [w for w in transit.stats(kernel)["worms"].values()
             if (w.get("builders") or w.get("owner")) == line and w.get("dormant") is None]
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


def season(kernel: Any) -> List[str]:
    """Once a year: each council's new consciousness goes out over its house's parliament to the peoples it reaches."""
    from xylarium.kernel import board, court, polity
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    st = stats(kernel)
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
        for who, share in sorted(shares.items()):
            rec[who] = str(Fraction(rec.get(who, "0")) + part * share)
            lost += part * (1 - share)
        st["dissipated"] = str(Fraction(st.get("dissipated", "0")) + lost)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"made": st.get("made", "0"), "dissipated": st.get("dissipated", "0"),
            "peoples_reached": len(st.get("received") or {})}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="consciousness", state=lambda: {"read": {}, "received": {}}, season=season,
                             summary=summary))
