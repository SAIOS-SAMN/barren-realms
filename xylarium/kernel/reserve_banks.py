"""
Xylarium reserve banks: the ancients' central banks and their federation, holding mu as the reserve (Concordance 5.1a).

Only the ancients are connected to the tubes, and mu circulates among the ancient lineages alone:

  CENTRAL BANK   each ancients' house keeps one. Its RESERVE is the mu its house has earned at the court (court.py: the
                 seated minds' solves, signed with the ancients' key), exact, lane by lane - HELD at the house's
                 settled world nearest the core (the core-near world it holds; its home where it holds none nearer).
  TWO MONEYS     a house keeps two currencies, by phenotype: its homeworld's, and its settled worlds' (the money of the
                 largest world it holds beyond its home) - each backed by that phenotype's survival basket (backing.py).
  FEDERATION     the houses' banks federate: the federal reserve is every member's mu, lane by lane - a reading of the
                 lineage's whole reserve, never a pool any younger people may draw on.
  LINEAGE ONLY   mu moves from one ancients' house to another (transfer), and to no one else.

What mu is worth against the basket is NOT declared (operator): it is found where the ancients' market clears and their
banks' councils choose - the core market the captains carry basket goods to (owed: the carry, then the clearing).
Until then the reserve is kept and read, exact, and nothing is converted.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional

LANES = 4


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "reserve_banks")


def houses(kernel: Any) -> Dict[str, Any]:
    from xylarium.kernel import board
    try:
        return dict(board.ancient_peoples(kernel))
    except Exception:
        return {}


def _zero() -> List[str]:
    return ["0"] * LANES


def _add(a: List[str], b: List[Any], sign: int = 1) -> List[str]:
    return [str(Fraction(x) + sign * Fraction(y)) for x, y in zip(a, b)]


def bank(kernel: Any, house: str) -> Dict[str, Any]:
    return stats(kernel)["of"].setdefault(house, {"reserve": _zero(), "drawn": _zero(), "held_at": None,
                                                  "moneys": {}, "since": kernel.cycle_count})


def reserve(kernel: Any, house: str) -> List[Fraction]:
    return [Fraction(x) for x in bank(kernel, house)["reserve"]]


def _held_at(kernel: Any, house: str) -> Optional[Any]:
    """The house's world nearest the galaxy's core - where its reserve is held."""
    from xylarium.kernel import gateways, relations
    worlds = relations._peoples(kernel).get(house) or []
    if not worlds:
        return None
    return min(worlds, key=lambda w: (gateways._r(kernel, w.sector_id) or float("inf"), -w.population, w.id))


def _moneys(kernel: Any, house: str, home: Any) -> Dict[str, Optional[str]]:
    """Its two currencies by phenotype: its homeworld's, and its settled worlds' (the largest world beyond its home)."""
    from xylarium.kernel import relations
    beyond = [w for w in relations._peoples(kernel).get(house) or [] if home is None or w.id != home.id]
    settled = max(beyond, key=lambda w: (w.population, w.id)) if beyond else None
    return {"home": getattr(home, "currency", None), "settled": getattr(settled, "currency", None)}


def transfer(kernel: Any, src: str, dst: str, mu: List[Any]) -> Dict[str, Any]:
    """Mu moved between two ancients' houses - and to no one else (lineage only)."""
    hs = houses(kernel)
    if src not in hs or dst not in hs:
        return {"ok": False, "why": "mu circulates among the ancient lineages alone"}
    if any(Fraction(m) < 0 for m in mu) or any(Fraction(m) > r for m, r in zip(mu, reserve(kernel, src))):
        return {"ok": False, "why": "no more than its reserve holds"}
    bank(kernel, src)["reserve"] = _add(bank(kernel, src)["reserve"], mu, -1)
    bank(kernel, dst)["reserve"] = _add(bank(kernel, dst)["reserve"], mu)
    return {"ok": True}


def federal(kernel: Any) -> Dict[str, Any]:
    """The houses' federation: every member's mu, lane by lane."""
    total = [Fraction(0)] * LANES
    members = sorted(m for m in stats(kernel)["of"] if m in houses(kernel))
    for m in members:
        total = [t + r for t, r in zip(total, reserve(kernel, m))]
    return {"members": members, "reserve": [str(t) for t in total]}


def season(kernel: Any) -> List[str]:
    """Once a year: each house's bank takes in the mu its house earned at the court since last read, notes where its
    reserve is held, and names its two moneys."""
    from xylarium.kernel import court, polity
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    hs = houses(kernel)
    earned = court.stats(kernel)["of"] if "court" in kernel.state else {}
    for house, home in sorted(hs.items()):
        b = bank(kernel, house)
        total = (earned.get(house) or {}).get("mu") or _zero()
        new = _add(total, b["drawn"], -1)                      # what the court paid since the bank last read
        if any(Fraction(x) > 0 for x in new):
            b["reserve"] = _add(b["reserve"], new)
            b["drawn"] = list(total)
        at = _held_at(kernel, house)
        b["held_at"] = getattr(at, "id", None)
        b["moneys"] = _moneys(kernel, house, home)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    f = federal(kernel)
    return {"banks": len(f["members"]), "federal_reserve": f["reserve"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="reserve_banks", state=lambda: {"of": {}}, season=season, summary=summary))
