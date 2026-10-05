"""
Xylarium offices: the minds of the offices below the sovereign (T4-T9) - a ship and a specialization - by the mind
core (mindcore.py).

A captain's survival books (cognition.SeatSurvive: ration, thermal, security, matter, leisure) are read first, in
that order - a crew is fed, its hull whole and its guns enough before anything else. Beyond survival, each office
has its own order of the books a captain grows by, and the growth it may take is each serving one book:

  trade    arbitrage between ports          (the trader's book: holds to fill with what is cheap here and dear there)
  haul     freight contracts                (logistics: cargo others need carried)
  matter   mining the belts                 (the developer's raw stock)
  works    settling and building            (the developer's works)
  unknown  digging the past, reading ruins  (intelligence: what is not yet known)
  money    capital put to work              (the financier's: money idle in hand or in foreign wallets)

Need orders: the office's first book that any option can serve leads, and within that one book the option that
delivers most is taken - options serving different books are never weighed against each other in one number.
What a plan delivered, per turn, when it closes (cognition.track_plan) is sealed in the office's mind: a crystal
for that book, or a wall - so an office that has learned which of its books pays turns there first.

Players' offices are theirs (roles.OFFICES); a captain of the realm's own crews holds the office its calling is.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import mindcore as mc

FAMILY = {"haul": "trade", "liquidate": "trade", "freight": "haul", "extract": "matter", "mine": "matter",
          "settle": "works", "upgrade": "works", "dig": "unknown", "invest": "money"}   # cognition's plan kinds
ORDER = {
    "trader": ("trade", "haul", "matter", "works", "unknown"),
    "developer": ("works", "matter", "trade", "haul", "unknown"),
    "financier": ("money", "trade", "haul", "matter", "works", "unknown"),
    "defender": ("haul", "trade", "matter", "works", "unknown"),
    "intelligence": ("unknown", "trade", "haul", "matter", "works"),
    "logistics": ("haul", "trade", "matter", "works", "unknown"),
}
CALLING = {"trader": "trader", "industrialist": "developer", "mercenary": "defender", "pirate": "defender",
           "crusader": "defender", "imperial": "logistics"}


def office(kernel: Any, captain: Any) -> str:
    """The office a captain holds: a player's chosen one, else its crew's calling."""
    from xylarium.kernel import roles
    if "roles" in getattr(kernel, "state", {}):
        o = roles.office_of(kernel, captain.id)
        if o is not None:
            return o["key"]
    return CALLING.get(str(getattr(getattr(captain, "personality", None), "value", "trader")), "trader")


def mind(kernel: Any, captain: Any) -> Dict[str, Any]:
    """An office's mind, kept with the realm's record (it outlives a save; a successor in the seat inherits it)."""
    minds = state.of(kernel, "offices")["minds"] if kernel is not None and hasattr(kernel, "state") else {}
    return minds.setdefault(str(captain.id), mc.new_mind())


def family(plan: Dict[str, Any]) -> str:
    return FAMILY.get(str(plan.get("kind", "")), "trade")


def choose(kernel: Any, captain: Any, options: List[Tuple[float, Dict[str, Any], Any]]) -> Optional[Tuple[float, Dict[str, Any], Any]]:
    """Need orders: the office's books in its order - a book a crystal says pays comes before one walled - and the
    first any option serves leads; within that book, the option delivering most. Nothing that delivers nothing."""
    by: Dict[str, List[Tuple[float, Dict[str, Any], Any]]] = {}
    for o in options:
        if o[0] > 0:
            by.setdefault(family(o[1]), []).append(o)
    if not by:
        return None
    m = mind(kernel, captain)
    order = list(ORDER.get(office(kernel, captain), ORDER["trader"]))
    paid = [b for b in order if mc.recall(m, ("self", b), Fraction(1)) is not None]
    walled = [b for b in order if b in mc.walls(m, mc.shape(("self", b), Fraction(1)))]
    ranked = paid + [b for b in order if b not in paid and b not in walled] + [b for b in order if b in walled]
    for book in ranked + sorted(set(by) - set(ranked)):
        if book in by:
            return max(by[book], key=lambda o: o[0])
    return None


def learn(kernel: Any, captain: Any, kind: str, rate: float) -> None:
    """A plan closed: what it delivered a turn is sealed for its book - a crystal if it paid, else a wall."""
    m = mind(kernel, captain)
    entry = ("self", FAMILY.get(kind, "trade"))
    mc.intend(m, entry, Fraction(1), entry[1])
    paid = mc.q(rate) if rate > 0 else Fraction(0)
    mc.seal(m, {entry: Fraction(1) - paid})


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="offices", state=lambda: {"minds": {}}))
