"""
Xylarium endowments: what a realm's steward holds for the peoples of its realm, and gives each when it ascends.

THE FUND. A line's stewards keep one fund, in SOL: the tithes every passer pays the progenitors who keep the roads
(transit.settle) come to it, through the exchanges - money that already circulates, moved; nothing is minted.

WATCHING GROWTH. Each year the steward reads every people of its realm (constellations.py): its numbers then and
now, and so how fast it is growing. The realm's growth over a steward's term is what the fund may set aside that term
- a realm that does not grow sets nothing aside.

ESCROWS, AS RESOURCES, FOR ARRIVALS. What a term sets aside is shared among the realm's arrivals - its peoples not yet
ascended, and the minds due to wake in its constellations within the term - and each share is turned into goods,
bought at the ports that trade in SOL at their own prices (the steward pays; the port's shelves give): ore, organics
and equipment, what a new dock needs on its shelves. The goods leave the market for the steward's escrow (a declared
sink to the matter ledger) and wait. A mind's escrow passes to the people it becomes when it wakes.

ASCENSION. When a steward lets a people ascend, its escrow is released at its home:
  - a dock, if its system has none (waystations.found) - the goods go onto its shelves, on the market;
  - its money: its currency board buys its own commodity from that dock at par (regimes: a money is issued only
    against goods), so the people's money comes into being backed by what the steward brought;
  - its listing: once its dock holds its own money, the steward opens its pool on the exchange - the escrow's SOL on
    one side, the dock's own money on the other at its fair rate (backing.fair: the goods behind it) - and its money
    trades: the realm's ledger lists it.
"""

import math
from typing import Any, Dict, List, Optional
from xylarium.kernel.fx import hub as _hub

BASKET = ("ORE", "ORGANICS", "EQUIPMENT")        # what a new dock's shelves are stocked with (a waystation's trade)


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "endowments")


def credit(kernel: Any, line: Optional[str], sol: float) -> None:
    """Money comes to a line's fund (a tithe, already converted to SOL)."""
    if not line or sol <= 0:
        return
    f = stats(kernel)["funds"].setdefault(line, {"sol": 0.0, "in": 0.0})
    f["sol"] += float(sol)
    f["in"] += float(sol)


def holdings(kernel: Any) -> float:
    """The SOL the stewards hold: their funds, what their escrows have not yet spent on goods, and what waits on a
    listing."""
    if kernel is None or "endowments" not in getattr(kernel, "state", {}):
        return 0.0
    st = stats(kernel)
    return (sum(f["sol"] for f in st["funds"].values()) + sum(e["sol"] for e in st["escrows"].values())
            + sum(r["sol"] for r in st["listing"].values()))


# ---------------------------------------------------------------------- watching the realm grow
def _watch(kernel: Any, peoples: Dict[str, List[Any]]) -> None:
    """Each year: every people's numbers, and how fast they grow (per year, since its last reading)."""
    g = stats(kernel)["growth"]
    now = kernel.cycle_count
    for who, worlds in peoples.items():
        n = float(sum(p.population for p in worlds))
        rec = g.get(who)
        if rec is not None and n > 0 and rec["pop"] > 0 and now > rec["at"]:
            years = (now - rec["at"]) / 100.0
            rec["rate"] = math.log(n / rec["pop"]) / years
        g[who] = {"pop": n, "at": now, "rate": (rec or {}).get("rate", 0.0)}


def _realm_peoples(kernel: Any, peoples: Dict[str, List[Any]]) -> Dict[str, List[str]]:
    """Each line's realm peoples (constellations.realm_of their homes)."""
    from xylarium.kernel import constellations
    out: Dict[str, List[str]] = {}
    for who, worlds in peoples.items():
        home = max(worlds, key=lambda p: (p.population, p.id))
        line = constellations.line_of_realm(kernel, constellations.realm_of(kernel, home.sector_id))
        if line:
            out.setdefault(line, []).append(who)
    return out


def _arrivals(kernel: Any, line: str, members: List[str], term_gyr: float) -> List[str]:
    """Whom a line's stewards prepare for: its realms' peoples not yet ascended (not the line itself), and the minds
    due to wake in its constellations within a term."""
    from xylarium.kernel import ascendance, constellations, cosmos
    out = [w for w in members if w != line and ascendance.ruling(kernel, w) != "ascended"]
    t = cosmos.deep_gyr(kernel)
    for m in cosmos.stats(kernel).get("minds") or []:
        e = float(m.get("epoch", 0.0))
        if t <= e <= t + term_gyr and m.get("cell") is not None:
            cell = f"{int(m['cell'][0])},{int(m['cell'][1])}"
            rid = constellations.stats(kernel).get("of_cell", {}).get(cell)
            if constellations.line_of_realm(kernel, rid) == line:
                out.append(f"mind:{cell}:{int(m['k'])}")
    return out


def _growth(kernel: Any, members: List[str]) -> float:
    """The realm's growth per year: its peoples' rates, weighted by their numbers (only growth: a shrinking realm
    sets nothing aside)."""
    g = stats(kernel)["growth"]
    n = sum(g[w]["pop"] for w in members if w in g)
    if n <= 0:
        return 0.0
    return max(0.0, sum(g[w]["pop"] * g[w]["rate"] for w in members if w in g) / n)


def _buy(kernel: Any, esc: Dict[str, Any]) -> None:
    """An escrow's SOL turned into goods at the ports that trade in SOL, at their own prices."""
    from xylarium.kernel import matter
    from xylarium.kernel.economy import EconomyManager
    for sec in sorted(kernel.sectors.values(), key=lambda s: s.id):
        port = sec.port
        if port is None or getattr(port, "currency", _hub()) != _hub():
            continue
        for comm in BASKET:
            share = esc["sol"] / max(1, len(BASKET))
            _, sell = EconomyManager.get_unit_prices(port, comm)
            have = int(port.stock.get(comm, 0))
            if not sell or sell <= 0 or have <= 0 or share < sell:
                continue
            q = int(min(have, share // sell))
            if q <= 0:
                continue
            pay = int(q * sell)
            port.stock[comm] = have - q
            port.treasury += pay
            esc["sol"] -= pay
            esc["goods"][comm] = esc["goods"].get(comm, 0) + q
            matter.sink("endowment_escrow", comm, q)
        if esc["sol"] < 1.0:
            break


def _rekey_minds(kernel: Any, peoples: Dict[str, List[Any]]) -> None:
    """A mind's escrow passes to the people it became when it woke."""
    from xylarium.kernel import cosmos
    esc = stats(kernel)["escrows"]
    for who, worlds in peoples.items():
        home = max(worlds, key=lambda p: (p.population, p.id))
        g = cosmos.stats(kernel)["place"].get(str(home.sector_id)) or {}
        if "cell" not in g:
            continue
        key = f"mind:{int(g['cell'][0])},{int(g['cell'][1])}:{int(g.get('k', 0))}"
        if key in esc and who not in esc:
            esc[who] = esc.pop(key)


def season(kernel: Any, peoples: Dict[str, List[Any]]) -> List[str]:
    """Once a year (from the annals, after the realms are read): watch the realms grow, set aside each term's share
    of the growth for the arrivals, turn it into goods; list the moneys of peoples endowed whose docks now hold their
    own money."""
    from xylarium.kernel import spheres
    logs: List[str] = []
    st = stats(kernel)
    _watch(kernel, peoples)
    _rekey_minds(kernel, peoples)
    for line, members in sorted(_realm_peoples(kernel, peoples).items()):
        fund = st["funds"].get(line)
        if not fund or fund["sol"] <= 0:
            continue
        from xylarium.kernel import fertility
        term_years = spheres.generation(kernel, line) if line != "elders" else fertility.generation_years()
        arrivals = _arrivals(kernel, line, members, term_years / 1e9)
        if not arrivals:
            continue
        # a year's part of the term's share of the realm's growth
        part = min(1.0, _growth(kernel, members) * term_years) / max(1.0, term_years)
        budget = fund["sol"] * part
        if budget < len(arrivals):
            continue
        fund["sol"] -= budget
        for who in arrivals:
            esc = st["escrows"].setdefault(who, {"line": line, "sol": 0.0, "goods": {}, "since": kernel.cycle_count})
            esc["sol"] += budget / len(arrivals)
            _buy(kernel, esc)
    for who in sorted(st["listing"]):
        line = _list(kernel, who)
        if line:
            logs.append(line)
    return logs


# ---------------------------------------------------------------------- ascension
def release(kernel: Any, who: str) -> Optional[str]:
    """A people ascends: its steward's escrow goes to its home - a dock if it has none, the goods on its shelves (its
    currency board issues its money against them), and its listing once that money exists."""
    from xylarium.kernel import history, matter, spheres, waystations
    st = stats(kernel)
    esc = st["escrows"].pop(who, None)
    if esc is None:
        return None
    home = spheres._home(kernel, who)
    sec = kernel.sectors.get(home.sector_id) if home is not None else None
    if sec is None:
        st["escrows"][who] = esc                          # nowhere to deliver it yet
        return None
    if sec.port is None:
        waystations.found(kernel, sec, home, 0.0)         # the steward's dock: no capital but what it brings
    for comm, q in sorted(esc["goods"].items()):
        sec.port.stock[comm] = sec.port.stock.get(comm, 0) + int(q)
        matter.source("endowment_escrow", comm, int(q))
    st["listing"][who] = {"sol": float(esc["sol"]), "line": esc["line"], "since": kernel.cycle_count}
    st["released"] = st.get("released", 0) + 1
    name = who.split(":", 1)[-1]
    history.event(kernel, "ENDOWED", f"The {name} are endowed on their ascension", actors=[who], planet=home,
                  cause=f"their steward's escrow - {sum(esc['goods'].values())} lots of goods on a dock of their own, "
                        f"and {esc['sol']:.0f} SOL toward their money's listing",
                  data={"goods": dict(esc["goods"]), "sol": round(esc["sol"], 2), "line": esc["line"]})
    return f"[ENDOWMENT] The {name} are endowed on their ascension."


def _list(kernel: Any, who: str) -> Optional[str]:
    """Open an endowed people's money on the exchange once its dock holds some of it: the escrow's SOL against a share
    of the dock's own money (both moved, nothing minted)."""
    from xylarium.config import FX_FEE
    from xylarium.kernel import history, institutions, spheres
    st = stats(kernel)
    rec = st["listing"][who]
    home = spheres._home(kernel, who)
    if home is None:
        st["listing"].pop(who)
        return None
    cur = home.currency
    fxm = kernel.fx_market
    if _hub() is None:
        return None                                       # no exchange founded yet: nothing to list it on
    if cur == _hub() or cur in fxm.pools:
        st["listing"].pop(who)
        return None
    sec = kernel.sectors.get(home.sector_id)
    port = sec.port if sec is not None else None
    if port is None or getattr(port, "currency", None) != cur or port.treasury <= 0 or rec["sol"] < 1.0:
        return None                                       # its money is not yet issued against its goods
    from xylarium.kernel import backing
    fair = backing.fair(kernel, cur)                       # its units per SOL, from the goods behind it
    if not fair or fair <= 0:
        return None
    sol = min(float(rec["sol"]), port.treasury / fair)     # the escrow's SOL against its money at that rate
    local = int(sol * fair)
    if local <= 0 or sol < 1.0:
        return None
    port.treasury -= local
    rec["sol"] -= sol                                      # what the pool did not need stays with the steward
    fxm.pools[cur] = {"sol": sol, "local": float(local)}
    fxm.volume_sol.setdefault(cur, 0.0)
    fxm.fees.setdefault(cur, FX_FEE)
    fxm.fees_collected.setdefault(cur, 0.0)
    institutions.stats(kernel)["pools"][cur] = {"sol": int(sol), "local": local, "opened": kernel.cycle_count,
                                               "by": rec["line"]}
    credit(kernel, rec["line"], rec["sol"])                # the remainder back to the fund
    st["listing"].pop(who)
    name = who.split(":", 1)[-1]
    history.event(kernel, "LISTED", f"The money of the {name} is listed", actors=[who],
                  cause=f"their steward set {sol:.0f} SOL beside {local} of their own money on the exchange",
                  data={"currency": cur, "sol": round(sol, 2), "local": local})
    return f"[ENDOWMENT] The {cur} of the {name} is listed on the realm's exchange."


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"funds_sol": round(sum(f["sol"] for f in st["funds"].values()), 2), "escrows": len(st["escrows"]),
            "escrow_goods": sum(sum(e["goods"].values()) for e in st["escrows"].values()),
            "released": st.get("released", 0), "awaiting_listing": len(st["listing"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="endowments",
                             state=lambda: {"funds": {}, "escrows": {}, "growth": {}, "listing": {}, "released": 0},
                             summary=summary))
