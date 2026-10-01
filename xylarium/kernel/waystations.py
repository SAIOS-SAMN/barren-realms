"""
Xylarium waystations: where the traffic goes, a dock follows.

At genesis most systems got a starport and the rest did not; null space got none. From then on, ports are founded
by the economy itself. Every arrival is counted where it lands (deeds: after a MOVE). Each year, for every portless
sector - a system no one built a dock in, or a null-space relay on a busy lane - the value of a waystation there is
measured, not assumed: the traffic it would serve, times what a visit is worth to a dock, read off the docks that
exist (the median of their retail income per visit). Whoever is there to found it - the council of a peopled world
in that system, or a captain whose own route passes through - founds it when that value, discounted by its own mind
at its money's policy rate, beats what the dock costs. Competition follows: a busier lane draws more docks, and
docks that share a lane share its traffic.

A founded waystation opens with empty shelves and the founder's capital as its working treasury (a transfer); it
buys what it sells from those who pass. Half of what its treasury grows beyond that capital is paid to its founder
each year - a dock is an investment. Nothing is minted and no goods appear: its stock is whatever it is brought.
"""

from typing import Any, Dict, List, Optional

from xylarium.config import COMMODITY_CONFIG, PORT_START_TREASURY, PRICE_LEVEL
from xylarium.kernel import decide

FOUNDER_SHARE = 0.5          # of the treasury's growth beyond its capital paid to the founder each year


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "waystations")


def arrive(kernel: Any, sector_id: int) -> None:
    """Called after every successful move: one arrival counted where it landed."""
    t = stats(kernel)["traffic"]
    key = str(sector_id)
    t[key] = t.get(key, 0) + 1


def visit_value(kernel: Any) -> float:
    """What a visit is worth to a dock, in SOL: the median, over docks with traffic, of retail income per visit."""
    st = stats(kernel)
    vals = []
    for sid, n in st["last_traffic"].items():
        sec = kernel.sectors.get(int(sid))
        if sec is None or sec.port is None or n <= 0:
            continue
        inc = float(getattr(sec.port, "regional_income", 0.0) or 0.0)
        cur = sec.port.currency
        inc_sol = kernel.fx_market.to_sol_value(cur, inc) if cur != "SOL" else inc
        vals.append(inc_sol / n)
    vals.sort()
    return vals[len(vals) // 2] if vals else 0.0


def _founder(kernel: Any, sec: Any) -> Optional[Any]:
    """Who is there to build it: the richest council of a peopled world in the system, else the richest AI
    captain in the sector."""
    worlds = [p for p in sec.planets if p.population > 0 and not getattr(p, "natives", None)
              and (p.owner_id is None or getattr(kernel.captains.get(p.owner_id), "is_ai", False))]
    if worlds:
        return max(worlds, key=lambda p: kernel.fx_market.to_sol_value(p.currency, p.treasury)
                   if p.currency != "SOL" else p.treasury)
    caps = [kernel.captains[c] for c in sec.captains if c in kernel.captains
            and getattr(kernel.captains[c], "is_ai", False) and not kernel.captains[c].faction_id]
    return max(caps, key=lambda c: c.credits) if caps else None


def found(kernel: Any, sec: Any, founder: Any, capital_sol: float) -> str:
    from xylarium.kernel.fx import currency_for_security
    from xylarium.kernel.models import Port, PortClass
    fxm = kernel.fx_market
    cur = currency_for_security(sec.security)
    # the founder's capital becomes the dock's working treasury, in the dock's own money (through the exchange)
    if hasattr(founder, "population"):                                       # a world's council
        own = int(capital_sol * (fxm.rate(founder.currency) if founder.currency != "SOL" else 1.0))
        founder.treasury -= own
        if founder.currency == cur:
            local = own
        else:
            sol = fxm.swap_to_sol(founder.currency, own) if founder.currency != "SOL" else own
            local = fxm.swap_sol_to(cur, sol) if cur != "SOL" else sol
        owner = f"planet:{founder.id}"
        who = founder.name
    else:                                                                    # a captain
        founder.credits -= int(capital_sol)
        local = kernel.fx_market.swap_sol_to(cur, int(capital_sol)) if cur != "SOL" else int(capital_sol)
        owner = f"captain:{founder.id}"
        who = founder.name
    comms = [c for c, cfg in COMMODITY_CONFIG.items() if cfg.get("category") != "WASTE"]
    port = Port(sector_id=sec.id, name=f"{who.split()[0]}'s Waystation #{sec.id}", port_class=PortClass.CLASS_8_BBB,
                stock={c: 0 for c in comms}, max_stock={c: 400 for c in comms},
                buys={c: True for c in comms}, sells={c: True for c in comms}, treasury=int(local), currency=cur)
    sec.port = port
    st = stats(kernel)
    st["docks"][str(sec.id)] = {"owner": owner, "capital": int(local), "since": kernel.cycle_count}
    st["founded"] += 1
    return f"[WAYSTATION] {who} founds {port.name} in Sector {sec.id:03d} on a lane that needed one."


def _pay_founders(kernel: Any) -> None:
    from xylarium.kernel import fx
    st = stats(kernel)
    for sid, rec in st["docks"].items():
        sec = kernel.sectors.get(int(sid))
        port = sec.port if sec is not None else None
        if port is None:
            continue
        growth = port.treasury - rec["capital"]
        pay = int(growth * FOUNDER_SHARE)
        if pay <= 0:
            continue
        kind, _, oid = rec["owner"].partition(":")
        if kind == "planet":
            world = kernel.get_planet(oid)
            if world is None or world.currency != port.currency:
                continue
            world.treasury += pay
        else:
            cap = kernel.captains.get(oid)
            if cap is None:
                continue
            if port.currency == "SOL":
                cap.credits += pay
            else:
                fx.credit(cap, port.currency, pay)
        port.treasury -= pay
        rec["paid"] = rec.get("paid", 0) + pay


def quarter(kernel: Any) -> List[str]:
    st = stats(kernel)
    st["last_traffic"] = dict(st["traffic"])
    st["traffic"] = {}
    if (kernel.cycle_count // _quarter()) % 4:
        return []
    _pay_founders(kernel)
    logs = []
    value = visit_value(kernel)
    if value <= 0:
        return logs
    for sid, n in st["last_traffic"].items():
        sec = kernel.sectors.get(int(sid))
        if sec is None or sec.port is not None or n <= 0 or int(sid) == 1:
            continue
        founder = _founder(kernel, sec)
        if founder is None:
            continue
        from xylarium.kernel.fx import currency_for_security
        cur = currency_for_security(sec.security)
        capital = PORT_START_TREASURY * PRICE_LEVEL.get(cur, 1.0) / max(1e-9, kernel.fx_market.rate(cur)
                                                                      if cur != "SOL" else 1.0) / 3
        afford = (founder.credits if hasattr(founder, "credits") else
                  (kernel.fx_market.to_sol_value(founder.currency, founder.treasury) if founder.currency != "SOL"
                   else founder.treasury))
        if afford < capital * 2:
            continue
        m = decide.mind_of_planet(kernel, founder) if hasattr(founder, "population") else \
            decide.mind_of_captain(kernel, founder)
        worth = decide.worth(kernel, n * value, m)
        if decide.choose(kernel, [decide.option("found_waystation", capital, worth)], m, sid, "dock") is None:
            continue
        logs.append(found(kernel, sec, founder, capital))
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    busiest = sorted(st["last_traffic"].items(), key=lambda kv: -kv[1])[:5]
    return {"founded": st["founded"], "docks": len(st["docks"]), "visit_value_sol": round(visit_value(kernel), 2),
            "busiest": busiest,
            "portless_with_traffic": sum(1 for sid, n in st["last_traffic"].items()
                                         if n > 0 and kernel.sectors.get(int(sid)) is not None
                                         and kernel.sectors[int(sid)].port is None)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="waystations",
    state=lambda: {"traffic": {}, "last_traffic": {}, "docks": {}, "founded": 0},
    season=quarter,
    summary=summary,
))
