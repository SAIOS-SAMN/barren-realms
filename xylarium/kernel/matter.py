"""
Xylarium matter: every unit of every commodity is somewhere, and changes only through a declared process.

The same discipline as money (ledger.py), applied to matter:

  * The census counts every stock of every commodity - in holds, port warehouses, colony silos and refined
    reserves, the ground (element deposits), asteroid belts, wreck debris, trade haulers and imperial
    tithe manifests.
  * The ledger records every declared source (a harvest, a mine face, a stellar wind implanting He-3, a
    fabrication that makes equipment) and every declared sink (a meal, a citadel's upkeep, radioactive decay,
    a fabrication that consumes its inputs). A conversion is a sink of its inputs and a source of its outputs.
  * The law: for every commodity, the change in the census equals sources minus sinks. Matter moved between
    holders (trade, freight, piracy, smuggling) changes nothing; matter appearing from nowhere, or vanishing
    into nowhere, breaks the law and names the place it happened.
  * Sources and sinks are kept side by side and never netted (mycelium's metabolism): entropy (extraction,
    decay, consumption) and syntropy (growth, fabrication, regeneration) are two histories, and their ratio
    per region is what tells a living economy from one running down.

Belt rock is counted as its own commodity ("BELT_ROCK"); mining a belt converts rock into the elements it
yields (a declared conversion). Ground deposits are counted per element ("in_ground").
"""

import functools
from collections import defaultdict
from typing import Any, Dict, Optional, Tuple

CORE = ("ORE", "ORGANICS", "EQUIPMENT")


class MatterLedger:
    def __init__(self) -> None:
        self.sources: Dict[Tuple[str, str], int] = defaultdict(int)
        self.sinks: Dict[Tuple[str, str], int] = defaultdict(int)

    def source(self, kind: str, commodity: str, qty: int) -> None:
        if qty:
            self.sources[(kind, key(commodity))] += int(qty)

    def sink(self, kind: str, commodity: str, qty: int) -> None:
        if qty:
            self.sinks[(kind, key(commodity))] += int(qty)

    def net(self) -> Dict[str, int]:
        out: Dict[str, int] = defaultdict(int)
        for (_, c), v in self.sources.items():
            out[c] += v
        for (_, c), v in self.sinks.items():
            out[c] -= v
        return dict(out)

    def to_dict(self) -> Dict[str, Any]:
        return {"sources": [[k, c, v] for (k, c), v in sorted(self.sources.items())],
                "sinks": [[k, c, v] for (k, c), v in sorted(self.sinks.items())]}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MatterLedger":
        m = cls()
        for k, c, v in d.get("sources", []):
            m.sources[(k, c)] = int(v)
        for k, c, v in d.get("sinks", []):
            m.sinks[(k, c)] = int(v)
        return m


ACTIVE: Optional[MatterLedger] = None


def set_active(ledger: Optional[MatterLedger]) -> None:
    global ACTIVE
    ACTIVE = ledger


def source(kind: str, commodity: str, qty: int) -> None:
    if ACTIVE is not None:
        ACTIVE.source(kind, commodity, qty)


def sink(kind: str, commodity: str, qty: int) -> None:
    if ACTIVE is not None:
        ACTIVE.sink(kind, commodity, qty)


def key(commodity: str) -> str:
    c = str(commodity)
    return c.upper() if c.upper() in CORE else c


def census(kernel: Any) -> Dict[str, Dict[str, int]]:
    """Every stock of every commodity: {commodity: {holder_kind: units, "total": units}}."""
    out: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def add(comm: str, where: str, qty: Any) -> None:
        q = int(qty or 0)
        if q:
            k = key(comm)
            out[k][where] += q
            out[k]["total"] += q

    from xylarium.kernel.propulsion import fuel_of
    for cap in kernel.captains.values():
        add(fuel_of(cap.ship) or "H", "bunkers", getattr(cap.ship, "fuel", 0))
        cg = cap.ship.cargo
        add("ORE", "holds", cg.ore)
        add("ORGANICS", "holds", cg.organics)
        add("EQUIPMENT", "holds", cg.equipment)
        for el, n in cg.elements.items():
            add(el, "holds", n)
    for sec in kernel.sectors.values():
        if sec.port is not None:
            for comm, n in sec.port.stock.items():
                add(comm, "ports", n)
        for p in sec.planets:
            add("ORE", "silos", p.ore_silo)
            add("ORGANICS", "silos", p.organics_silo)
            for el, n in p.element_reserves.items():
                add(el, "reserves", n)
            for el, n in p.element_deposits.items():
                add(el, "in_ground", n)
            for comm, n in ((getattr(p, "natives", None) or {}).get("tribute") or {}).items():
                add(comm, "native_tribute", n)
            for comm, n in getattr(p, "tithe_manifest", {}).items():
                if comm != "MANPOWER":                     # drafted people are not matter
                    add(comm, "tithes", n)
        for b in getattr(sec, "belts", []):
            add("BELT_ROCK", "belts", b.get("reserve", 0))
        add("H", "sector_gas", getattr(sec, "gas", 0))
        for d in getattr(sec, "debris", []):
            for comm, n in d.get("cargo", {}).items():
                add(comm, "debris", n)
    banking = getattr(kernel, "banking", None)
    for bank in (getattr(banking, "banks", {}) or {}).values():
        for comm, n in getattr(bank, "warehouse", {}).items():
            add(comm, "bank_warehouses", n)
    mm = getattr(kernel, "market_manager", None)
    if mm is not None:
        for h in getattr(mm, "trade_haulers", {}).values():
            for comm, n in getattr(h, "cargo", {}).items():
                add(comm, "haulers", n)
    return {k: dict(v) for k, v in out.items()}


def totals(kernel: Any) -> Dict[str, int]:
    return {k: v.get("total", 0) for k, v in census(kernel).items()}


# ---------------------------------------------------------------------- declared changes on attributes
def produce(obj: Any, attr: str, commodity: str, qty: int, kind: str, cap: Optional[int] = None) -> int:
    """Adds up to ``qty`` (never beyond ``cap``) and declares what was actually made. Storage never destroys:
    what has no room is simply not produced (or, for a transfer, not moved)."""
    have = int(getattr(obj, attr) or 0)
    room = qty if cap is None else max(0, min(qty, cap - have))
    if room > 0:
        setattr(obj, attr, have + room)
        source(kind, commodity, room)
    return room


def consume(obj: Any, attr: str, commodity: str, qty: int, kind: str) -> int:
    """Removes up to ``qty`` and declares it used up (eaten, burned, built into something outside the census)."""
    have = int(getattr(obj, attr) or 0)
    take = max(0, min(qty, have))
    if take > 0:
        setattr(obj, attr, have - take)
        sink(kind, commodity, take)
    return take


def declared(kind: str):
    """For rare events that bring matter into or out of the galaxy (a cluster charted, a ship commissioned,
    a reward found, a respawn kit issued): whatever the event creates or consumes beyond what it already
    declares is booked under ``kind``. Frequent processes declare their own flows explicitly instead."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            from xylarium.kernel import ledger
            k = ledger.active_kernel()
            if k is None or ACTIVE is None:
                return fn(*a, **kw)
            before, n0 = totals(k), ACTIVE.net()
            try:
                return fn(*a, **kw)
            finally:
                after, n1 = totals(k), ACTIVE.net()
                # every commodity counted or declared: one made and destroyed within the event (worlds charted and
                # engulfed at once) is in neither census, but its inner declarations must still be balanced
                for c in set(before) | set(after) | set(n0) | set(n1):
                    d = (after.get(c, 0) - before.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0))
                    if d > 0:
                        source(kind, c, d)
                    elif d < 0:
                        sink(kind, c, -d)
        return wrapper
    return deco


def commission(captain: Any, kind: str = "commissioning") -> None:
    """A new ship enters the galaxy with stores aboard: declare its starting cargo (a source)."""
    cg = captain.ship.cargo
    for comm, q in (("ORE", cg.ore), ("ORGANICS", cg.organics), ("EQUIPMENT", cg.equipment)):
        source(kind, comm, q)
    for el, q in cg.elements.items():
        source(kind, el, q)
    # a new hull leaves the yard with its drive bunker full
    from xylarium.kernel.propulsion import bunker_capacity
    from xylarium.kernel.propulsion import fuel_of
    top = bunker_capacity(captain.ship) - getattr(captain.ship, "fuel", 0)
    if top > 0 and fuel_of(captain.ship):
        captain.ship.fuel = getattr(captain.ship, "fuel", 0) + top
        source(kind, fuel_of(captain.ship), top)


# ---------------------------------------------------------------------- audit mode
def audit(kernel: Any) -> None:
    """Optional per-cycle audit (kernel.matter_audit = True): records any undeclared change - the cycle, the
    commodity and the amount - in the audit's violations (violations(kernel)), rather than crashing a live game."""
    if ACTIVE is None:
        return
    t, n = totals(kernel), ACTIVE.net()
    from xylarium.kernel import state
    rec = state.of(kernel, "matter_audit")
    base = rec.get("base")
    now = {c: t.get(c, 0) - n.get(c, 0) for c in set(t) | set(n)}
    if base is not None:
        for c in set(now) | set(base):
            d = now.get(c, 0) - base.get(c, 0)
            if d:
                v = rec["violations"]
                v.append({"cycle": kernel.cycle_count, "commodity": c, "undeclared": d})
                del v[:-200]
    rec["base"] = now


def violations(kernel: Any) -> list:
    from xylarium.kernel import state
    return state.of(kernel, "matter_audit")["violations"]


from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="matter_audit", state=lambda: {"base": None, "violations": []}))
