"""
Xylarium currency routes: money carried from where it is cheap to where it is dear - and the risk of carrying it.

A local exchange's rate is its place's own (exchanges.py); the federation's is the same at every other port. A captain
converts where it is docked: at a port with an exchange for that money, through the exchange; anywhere else, at the
federation's rate. So a gap between a place's rate and the federation's is worth flying money across:

  BUY LOCAL    where a place's money is cheap there (more of it per SOL than the federation gives), buy it there with
               SOL, carry it out, and sell it at any other port at the federation's rate;
  SELL LOCAL   where it is dear there, buy it at any other port and sell it there.

How much: as much as brings the place's pool to the federation's rate (constant product: the SOL side at
sqrt(k / r_F)), as far as the captain's purse allows. What it is worth to a captain: the gain, as its risk on the way
lets it keep it, less what the trip burns (a typical hop's, each hop), over the turns it takes. A shallow exchange's
gap may not be worth the trip: it stays open until a deeper flow, or a nearer trader, makes it worth closing. A route closes the gap it profits from - the trade that arbitrages a market is
the trade that integrates it.

MONEY ABOARD is cargo: a captain carrying a purse is worth a pirate's while (crime.py weighs a wallet as it weighs
credits), and a ship destroyed loses half its purse - every money in it - to the victor (combat.py).

ESCORTS AND LOCAL SECURITY. A captain about to carry money through hazard may hire a world's government to sail with it:
fighters from the world's garrison, at the price of what they are expected to lose on the way (what a world pays to
station a fighter, times the route's hazard - the share a trip there does not keep), paid to the world's vault. They
fight beside the captain (combat.py: an escort's fighters stand in the line and take losses first) and return home,
what is left of them, when the route ends.
"""

import math
from typing import Any, Dict, List, Optional, Tuple
from xylarium.kernel.fx import hub as _hub

FIGHTER_PRICE = 60               # what a world pays to station one fighter (colony.recruit_fighters)
HAZARD = {"FEDERATION": 0.0, "BORDERLAND": 0.15, "ANARCHY": 0.4}   # share a trip does not keep (cognition's discount)


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "fxroutes")


# ---------------------------------------------------------------------- the desk where one is docked
def exchange(kernel: Any, captain: Any, sector_id: Optional[int], from_cur: str, to_cur: str,
             amount: int) -> Tuple[bool, str, int]:
    """A captain's conversion where it is docked: through the place's exchange if it keeps one of the two moneys,
    else at the federation's rate."""
    from xylarium.kernel import exchanges, fx, ledger, regimes
    from_cur, to_cur = from_cur.upper(), to_cur.upper()
    ex = exchanges.at(kernel, sector_id)
    if ex is None or ex["cur"] not in (from_cur, to_cur):
        return kernel.fx_market.exchange(captain, from_cur, to_cur, amount)
    if from_cur == to_cur or amount <= 0:
        return False, "Choose two different currencies and a positive amount.", 0
    if fx.balance(captain, from_cur) < amount:
        return False, f"Insufficient {from_cur}: you hold {fx.balance(captain, from_cur):,}.", 0
    if regimes.controlled(ledger.active_kernel(), from_cur):
        return False, f"The {from_cur} is under capital controls: its exchange is closed to holders.", 0
    fx.debit(captain, from_cur, amount)
    out = exchanges.convert_at(kernel, sector_id, from_cur, to_cur, amount)
    fx.credit(captain, to_cur, out)
    return True, (f"Local exchange at sector {sector_id}: {amount:,} {from_cur} for {out:,} {to_cur} "
                  f"(its rate {exchanges.rate(ex):.4f} {ex['cur']}/SOL, the federation's "
                  f"{kernel.fx_market.rate(ex['cur']):.4f})."), out


# ---------------------------------------------------------------------- money aboard
def purse_sol(kernel: Any, captain: Any) -> float:
    """What a captain carries in foreign money, in SOL."""
    fx = getattr(kernel, "fx_market", None)
    if fx is None:
        return 0.0
    return sum(fx.to_sol_value(c, a) for c, a in (getattr(captain, "fx_wallet", {}) or {}).items() if a > 0)


def plunder_purse(attacker: Any, defender: Any) -> Dict[str, int]:
    """A destroyed ship's victor takes half of every money in its purse."""
    from xylarium.kernel import fx
    took: Dict[str, int] = {}
    for cur, amt in list((getattr(defender, "fx_wallet", {}) or {}).items()):
        half = int(amt) // 2
        if half > 0:
            fx.debit(defender, cur, half)
            fx.credit(attacker, cur, half)
            took[cur] = half
    return took


# ---------------------------------------------------------------------- escorts
def escort(captain: Any) -> Optional[Dict[str, Any]]:
    return (getattr(captain, "escort", None) or None)


def escort_fighters(captain: Any) -> int:
    e = escort(captain)
    return int(e["fighters"]) if e else 0


def escort_fee(kernel: Any, fighters: int, hazard: str) -> int:
    return int(math.ceil(fighters * FIGHTER_PRICE * HAZARD.get(hazard, 0.15)))


def hire(kernel: Any, captain: Any, planet: Any, fighters: int, until: int, hazard: str) -> Tuple[bool, str]:
    """A world's government lends fighters from its garrison to sail with a captain, for the price of what they are
    expected to lose on the way - paid to its vault (in its money, bought with the captain's SOL)."""
    if escort(captain):
        return False, "An escort already sails with you."
    fighters = min(int(fighters), max(0, int(planet.fighters) - 1))
    if fighters <= 0 or planet.population <= 0:
        return False, f"{planet.name} has no fighters to spare."
    fee = max(1, escort_fee(kernel, fighters, hazard))
    if captain.credits < fee:
        return False, f"An escort of {fighters} costs {fee:,} Cr."
    captain.credits -= fee
    fx = kernel.fx_market
    planet.treasury += fee if planet.currency == _hub() else fx.convert(_hub(), planet.currency, fee)[0]
    planet.fighters -= fighters
    captain.escort = {"fighters": fighters, "from": planet.id, "until": int(until)}
    st = stats(kernel)
    st["escorts"] += 1
    st["escort_fees"] += fee
    return True, f"{planet.name} sends {fighters} fighters to sail with you ({fee:,} Cr)."


def release(kernel: Any, captain: Any) -> None:
    """The route is over: what is left of the escort goes home."""
    e = escort(captain)
    if not e:
        return
    home = kernel.get_planet(e["from"])
    if home is not None:
        home.fighters += int(e["fighters"])
    captain.escort = None


def wear_escort(captain: Any, lost: int) -> int:
    """An escort takes a fight's losses first; returns what it did not absorb."""
    e = escort(captain)
    if not e or lost <= 0:
        return lost
    take = min(int(e["fighters"]), int(lost))
    e["fighters"] = int(e["fighters"]) - take
    return lost - take


def tick(kernel: Any) -> None:
    """Escorts whose time is up go home."""
    for c in kernel.captains.values():
        e = escort(c)
        if e and kernel.cycle_count >= int(e["until"]):
            release(kernel, c)


# ---------------------------------------------------------------------- the route a captain weighs
def _hazard(kernel: Any, path: List[int]) -> str:
    worst = "FEDERATION"
    for sid in path:
        sec = kernel.sectors.get(sid)
        h = getattr(getattr(sec, "security", None), "value", "FEDERATION") if sec is not None else "FEDERATION"
        if HAZARD.get(h, 0.0) > HAZARD.get(worst, 0.0):
            worst = h
    return worst


def gain(kernel: Any, ex: Dict[str, Any], budget_sol: float) -> Tuple[str, float, float]:
    """What a route through an exchange is worth: (direction, SOL put in, SOL expected back), at its size."""
    from xylarium.kernel import exchanges
    fx = kernel.fx_market
    cur = ex["cur"]
    r_f, r_l = fx.rate(cur), exchanges.rate(ex)
    fee = exchanges._fee(kernel, cur) + fx.fee(cur)
    sol, loc = float(ex["sol"]), float(ex["local"])
    k = sol * loc
    if r_l > r_f * (1.0 + fee):                               # cheap here: buy it here, sell it at the federation
        s = min(budget_sol, max(0.0, math.sqrt(k / r_f) - sol))
        x = loc - k / (sol + s * (1.0 - exchanges._fee(kernel, cur)))
        back = x / r_f * (1.0 - fx.fee(cur))
        return "buy_local", s, back
    if r_l * (1.0 + fee) < r_f:                               # dear here: bring it from the federation, sell it here
        target_loc = math.sqrt(k * r_f)
        x = min(max(0.0, target_loc - loc), budget_sol * r_f)
        s = x / r_f / (1.0 - fx.fee(cur))
        back = sol - k / (loc + x * (1.0 - exchanges._fee(kernel, cur)))
        return "sell_local", s, back
    return "none", 0.0, 0.0


def options(kernel: Any, captain: Any, dist: Dict[int, int]) -> List[Tuple[float, Dict[str, Any]]]:
    """Every currency route in reach, as a captain values it: the gain over the turns, as the route's hazard keeps it."""
    from xylarium.kernel import exchanges
    if "exchanges" not in getattr(kernel, "state", {}) or getattr(kernel, "fx_market", None) is None:
        return []
    budget = float(captain.credits) * 0.5                     # half its purse: what a careful trader commits
    out = []
    for sid, ex in exchanges.stats(kernel)["of"].items():
        at = int(sid)
        if at not in dist or budget <= 0:
            continue
        direction, s, back = gain(kernel, ex, budget)
        if direction == "none" or s <= 0 or back <= s:
            continue
        from xylarium.kernel import topology
        near = topology.hops(kernel, at, 6)                    # the nearest other port: where the federation's rate is
        other = next((o for o, _ in sorted(near.items(), key=lambda kv: (kv[1], kv[0]))
                      if o != at and o in kernel.sectors and kernel.sectors[o].port is not None
                      and exchanges.at(kernel, o) is None), None)
        if other is None:
            continue
        legs = kernel.find_path(at, other) or [at, other]
        hz = _hazard(kernel, legs)
        hops = dist[at] + max(1, len(legs) - 1)
        turns = hops + 2
        keep = 1.0 - HAZARD.get(hz, 0.15)
        from xylarium.kernel import transit
        burn = hops * transit._typical_hop(kernel)            # what the trip costs to fly
        value = ((back - s) * keep - burn) / turns
        out.append((value, {"kind": "fx", "cur": ex["cur"], "at": at, "other": other, "dir": direction,
                            "sol": int(s), "stage": 0, "hazard": hz}))
    return out


def step(kernel: Any, captain: Any, plan: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """The next act of a currency route: ('move', {to}), ('fx', {from, to, amount}), ('escort', {...}) or None when it
    is over. Stage 0 buys the money where the plan says (the exchange, or the federation for a sell-local route);
    stage 1 carries it and sells it."""
    cur, at, other = plan["cur"], int(plan["at"]), int(plan["other"])
    buy_at, sell_at = (at, other) if plan["dir"] == "buy_local" else (other, at)
    here = captain.sector_id
    if plan["stage"] == 2:                                    # sold: the route is over
        done(kernel, captain, plan, float(captain.credits) - float(plan.get("credits0", captain.credits))
             + float(plan.get("sol", 0)))
        return None
    if plan["stage"] == 0:
        if here != buy_at:
            return "move", {"to": buy_at}
        amount = min(int(plan["sol"]), int(captain.credits))
        if amount <= 0:
            return None
        plan["credits0"] = int(captain.credits)
        plan["sol"] = amount
        plan["stage"] = 1
        return "fx", {"from": _hub(), "to": cur, "amount": amount}
    held = int((getattr(captain, "fx_wallet", {}) or {}).get(cur, 0))
    if held <= 0:                                             # lost on the way (or never bought)
        release(kernel, captain)
        return None
    if here != sell_at:
        if not escort(captain) and plan.get("hazard") != "FEDERATION" and not plan.get("escort_tried"):
            plan["escort_tried"] = True
            sec = kernel.sectors.get(here)
            world = max((w for w in getattr(sec, "planets", []) if w.population > 0 and w.fighters > 1),
                        key=lambda w: w.fighters, default=None)
            if world is not None and captain.ship.fighters < purse_sol(kernel, captain) / FIGHTER_PRICE / 10:
                return "escort", {"planet_id": world.id, "fighters": min(world.fighters // 2, 20),
                                  "hazard": plan.get("hazard", "BORDERLAND")}
        return "move", {"to": sell_at}
    plan["stage"] = 2
    return "fx", {"from": cur, "to": _hub(), "amount": held}


def done(kernel: Any, captain: Any, plan: Dict[str, Any], back_sol: float) -> None:
    """A route's last conversion: the escort goes home and the route is counted."""
    st = stats(kernel)
    st["routes"] += 1
    st["carried_sol"] += float(plan.get("sol", 0))
    st["gained_sol"] = float(st.get("gained_sol", 0.0)) + back_sol - float(plan.get("sol", 0))
    release(kernel, captain)


def season(kernel: Any) -> List[str]:
    tick(kernel)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"routes": st["routes"], "carried_sol": round(st["carried_sol"]),
            "gained_sol": round(float(st.get("gained_sol", 0.0))), "escorts": st["escorts"],
            "escort_fees": st["escort_fees"], "purses_plundered": st["plundered"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="fxroutes",
    state=lambda: {"routes": 0, "carried_sol": 0.0, "gained_sol": 0.0, "escorts": 0, "escort_fees": 0,
                   "plundered": 0},
    season=season,
    summary=summary,
))
