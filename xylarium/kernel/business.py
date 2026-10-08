"""
Xylarium business: the economy as each seat sees it - and what each seat may build in it.

Nothing here makes money or goods; it reads what the laws already do (supply.py, demand.py, commerce.py,
exchanges.py, fxroutes.py) and puts it in front of the seat that can act on it:

  CAPTAIN (the trader, the financier)   the goods dearest here against their source (exotic index), the currency
                 routes in reach and what each is worth after its trip, the goods wanted nearby and what their import
                 orders pay - and the escort a world here would lend. It acts with its own hands: trade, freight,
                 the desk (an exchange's rate where one stands), an escort (HIRE_ESCORT).
  SOVEREIGN (the corporate machine of a people)   its people's model (regime, controls, rent, openness, balance),
                 what its worlds bought and sold, the goods they want and cannot get, and the exchanges its
                 councils founded - and it may found one itself at a port of its worlds (found_exchange), paying the
                 capital the place's flow asks for.
  STEWARD (the realm's book)   its realm's exchanges and their gaps against the federation, the routes flown through
                 them, what its ports carried in, and the worlds wanting what they cannot get at home.
"""

from typing import Any, Dict, List, Optional
from xylarium.kernel.fx import hub as _hub


def _sol(kernel: Any, cur: str, amount: float) -> float:
    fx = getattr(kernel, "fx_market", None)
    return amount if cur == _hub() or fx is None else fx.to_sol_value(cur, amount)


# ---------------------------------------------------------------------- the captain
def captain_book(kernel: Any, captain: Any, reach: int = 6) -> Dict[str, Any]:
    from xylarium.kernel import exchanges, fxroutes, supply, topology
    here = captain.sector_id
    dist = topology.hops(kernel, here, reach)
    exotic = []
    for sid, d in dist.items():
        port = getattr(kernel.sectors.get(sid), "port", None)
        for comm, rec in sorted((getattr(port, "landed", None) or {}).items()) if port is not None else []:
            exotic.append({"sector": sid, "hops": d, "good": comm, "landed": rec[0], "source": rec[1],
                           "index": round(float(rec[0]) / max(1e-9, float(rec[2])), 2)})
    exotic.sort(key=lambda e: -e["index"])
    routes = [{"value_per_turn": round(v, 1), **{k: p[k] for k in ("cur", "at", "other", "dir", "sol", "hazard")}}
              for v, p in sorted(fxroutes.options(kernel, captain, dist), key=lambda vp: -vp[0])]
    wanted = []
    mm = getattr(kernel, "market_manager", None)
    for c in (mm.contracts.values() if mm else []):
        if c.status == "OPEN" and c.origin_sector in dist:
            wanted.append({"contract": c.id, "good": c.commodity, "amount": c.amount, "to": c.destination_name,
                           "pays_sol": round(_sol(kernel, c.currency, c.payout_credits))})
    wanted.sort(key=lambda w: -w["pays_sol"])
    sec = kernel.sectors.get(here)
    guard = [{"planet": w.id, "name": w.name, "spare": max(0, int(w.fighters) - 1)}
             for w in getattr(sec, "planets", []) if w.population > 0 and w.fighters > 1]
    ex = exchanges.at(kernel, here)
    return {"exotic": exotic[:10], "routes": routes[:5], "wanted": wanted[:10], "escorts_here": guard,
            "exchange_here": ({"cur": ex["cur"], "rate": round(exchanges.rate(ex), 4),
                               "federation": round(kernel.fx_market.rate(ex["cur"]), 4)} if ex else None),
            "purse_sol": round(fxroutes.purse_sol(kernel, captain)), "escort": fxroutes.escort(captain)}


# ---------------------------------------------------------------------- the sovereign
def sovereign_book(kernel: Any, people: str) -> Dict[str, Any]:
    from xylarium.kernel import commerce, demand, exchanges, relations
    worlds = relations._peoples(kernel).get(people) or []
    ids = {w.id for w in worlds}
    wants: Dict[str, int] = {}
    for w in worlds:
        for comm, n in demand.wants(w).items():
            wants[comm] = wants.get(comm, 0) + n
    founded = [{"sector": int(sid), "cur": ex["cur"], "rate": round(exchanges.rate(ex), 4),
                "depth_sol": round(exchanges.side(ex, "sol"))}
               for sid, ex in exchanges.stats(kernel)["of"].items() if ex.get("founder") in ids] \
        if "exchanges" in kernel.state else []
    return {"model": commerce.model(kernel, people) if "commerce" in kernel.state else {},
            "traded": (commerce.stats(kernel)["peoples"].get(people) if "commerce" in kernel.state else None),
            "wants": wants, "exchanges": founded}


def found_exchange(kernel: Any, people: str, sector_id: int) -> Dict[str, Any]:
    """A sovereign founds an exchange at a port of its worlds: its council there pays the capital the place's flow
    asks for (exchanges.py) - its own choice, not its council's weighing."""
    from xylarium.kernel import exchanges, relations
    sec = kernel.sectors.get(int(sector_id))
    if sec is None or sec.port is None:
        return {"ok": False, "why": "no port there"}
    mine = {w.id for w in relations._peoples(kernel).get(people) or []}
    if not any(w.id in mine for w in sec.planets):
        return {"ok": False, "why": "none of your worlds is in that system"}
    if exchanges.at(kernel, sec.id) is not None:
        return {"ok": False, "why": "an exchange already stands there"}
    flow = exchanges.stats(kernel)["last_flow"].get(str(sec.id)) or exchanges.stats(kernel)["flow"].get(str(sec.id))
    if not flow or flow[0] <= 0:
        return {"ok": False, "why": "no money passes through there yet: an exchange there would earn nothing"}
    logs: List[str] = []
    ok = exchanges._found(kernel, sec, list(flow), logs, chosen=True)   # the sovereign chose; no council weighs it
    return {"ok": ok, "why": None if ok else "its council's vault cannot hold the capital", "logs": logs}


# ---------------------------------------------------------------------- the steward
def steward_book(kernel: Any, realm: str) -> Dict[str, Any]:
    from xylarium.kernel import demand, exchanges, spheres
    r = spheres.stats(kernel)["realms"].get(realm) if "spheres" in kernel.state else None
    sectors = set(r["sectors"]) if r else set()
    fx = kernel.fx_market
    exs = [{"sector": int(sid), "cur": ex["cur"], "rate": round(exchanges.rate(ex), 4),
            "gap": round(exchanges.rate(ex) / max(1e-9, fx.rate(ex["cur"])) - 1.0, 4)}
           for sid, ex in exchanges.stats(kernel)["of"].items() if int(sid) in sectors] \
        if "exchanges" in kernel.state else []
    wanting = {w.name: demand.wants(w) for sid in sectors if sid in kernel.sectors
               for w in kernel.sectors[sid].planets if w.population > 0 and demand.wants(w)}
    return {"exchanges": exs, "wanting": dict(list(wanting.items())[:20]),
            "carried": dict(demand.stats(kernel).get("carried", {})) if "demand" in kernel.state else {}}
