"""
Xylarium exchanges: local markets for money, founded where the money passing through a place pays for one.

The galaxy's moneys meet at the federation exchanges (fx.py): one pool per money against SOL, the same rate from
every port. Where enough foreign money passes through one place - its peoples trading across currencies, buying
goods landed from elsewhere, paying tolls in reserve money - a LOCAL EXCHANGE pays its founder: it keeps its own
pools of the port's money against SOL, takes the exchanges' fee on every conversion made there, and its rate is the
place's own - it moves with what the place buys and sells.

  FLOW      every conversion made at a place is noted there (note): its value in SOL, and how many.
  DEPTH     a year of the place's conversions, held on each side: deep enough to clear what passes there in a
            year without the federation - as far as buying its SOL side at the federation moves that rate by no
            more than the fee (a council pays no more slippage than the trade it would earn on). That is the
            founder's capital, the place's money and SOL.
  FOUNDING  each year, a port whose flow is noted and has no exchange: the council of the richest world there that
            keeps the port's money weighs it (decide.choose) - the fees the flow would pay (fee x flow a quarter, over
            its horizon) against what its capital would earn waiting (its money's rate on it, over its horizon) - and
            founds it if its vault holds the capital. Its SOL side is bought at the federation exchanges and its own
            money's side matched to it at the federation's rate: it opens at the federation's price.
  RATE      conversions at a place with an exchange clear through its pools (convert_at); its rate drifts from the
            federation's with the place's own trade: a place that buys more than it sells sells its own money there,
            and it is cheapest there - but its founder keeps it within its bank's band of its money's fair rate,
            what the goods its people hold are worth (backing.py). The gap is a CURRENCY ROUTE: money bought cheap at one exchange is worth more
            at another - carried there in a hold, by whoever dares (fxroutes.py).
  DIVIDEND  each year half of what the pools have grown beyond the founder's capital (valued at their own mid) is paid
            to the founder, in its money - an exchange is an investment, like a dock (waystations.py).

Its pools are money, counted in the census (ledger.money_supply: "local_exchanges"); nothing is minted.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

SOL = "SOL"


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "exchanges")


def at(kernel: Any, sector_id: Optional[int]) -> Optional[Dict[str, Any]]:
    """The exchange at a place, if one is founded there."""
    if sector_id is None or kernel is None or "exchanges" not in getattr(kernel, "state", {}):
        return None
    return stats(kernel)["of"].get(str(sector_id))


def holdings(kernel: Any) -> Dict[str, int]:
    """Every local exchange's pools, per money (for the census)."""
    out: Dict[str, int] = {}
    if kernel is None or "exchanges" not in getattr(kernel, "state", {}):
        return out
    for ex in stats(kernel)["of"].values():
        out[SOL] = out.get(SOL, 0) + int(ex["sol"])
        out[ex["cur"]] = out.get(ex["cur"], 0) + int(ex["local"])
    return out


def _fee(kernel: Any, cur: str) -> float:
    return float(kernel.fx_market.fee(cur)) if getattr(kernel, "fx_market", None) is not None else 0.003


def note(kernel: Any, sector_id: Optional[int], sol_value: float) -> None:
    """A conversion made at a place: its value in SOL is counted there."""
    if sector_id is None or sol_value <= 0 or kernel is None or "exchanges" not in getattr(kernel, "state", {}):
        return
    f = stats(kernel)["flow"].setdefault(str(sector_id), [0.0, 0])
    f[0] += float(sol_value)
    f[1] += 1


def rate(ex: Dict[str, Any]) -> float:
    """An exchange's mid: its money per SOL."""
    return float(ex["local"]) / max(1e-9, float(ex["sol"]))


def _swap(ex: Dict[str, Any], side_in: str, amount: int, fee: float) -> int:
    """Constant-product swap into one side of an exchange's pools; the fee stays in the pool."""
    side_out = "local" if side_in == "sol" else "sol"
    k = float(ex["sol"]) * float(ex["local"])
    eff = amount * (1.0 - fee)
    out = int(math.floor(float(ex[side_out]) - k / (float(ex[side_in]) + eff)))
    out = max(0, min(out, int(ex[side_out]) - 1))
    ex[side_in] = float(ex[side_in]) + amount
    ex[side_out] = float(ex[side_out]) - out
    ex["fees_sol"] = float(ex.get("fees_sol", 0.0)) + (amount * fee if side_in == "sol" else amount * fee / rate(ex))
    return out


def convert_at(kernel: Any, sector_id: Optional[int], from_cur: str, to_cur: str, amount: int) -> int:
    """Convert at a place: through its exchange's pools where it keeps one of the two moneys (the other leg, if any,
    at the federation exchanges), else at the federation exchanges. The conversion is noted there."""
    fx = getattr(kernel, "fx_market", None)
    if from_cur == to_cur or amount <= 0:
        return amount
    if fx is not None:
        note(kernel, sector_id, fx.to_sol_value(from_cur, amount))
    ex = at(kernel, sector_id)
    if ex is None or ex["cur"] not in (from_cur, to_cur):
        return fx.convert(from_cur, to_cur, amount)[0] if fx is not None else amount
    fee = _fee(kernel, ex["cur"])
    if from_cur == ex["cur"]:
        sol = _swap(ex, "local", amount, fee)
        return sol if to_cur == SOL else fx.convert(SOL, to_cur, sol)[0]
    sol = amount if from_cur == SOL else fx.convert(from_cur, SOL, amount)[0]
    return _swap(ex, "sol", sol, fee)


def ensure_local(kernel: Any, captain: Any, sector_id: Optional[int], cur: str, needed: int) -> bool:
    """A captain short of a place's money for a purchase there buys it with SOL - at the place's exchange if it has
    one, else at the federation exchanges."""
    from xylarium.kernel import fx as fx_mod
    ex = at(kernel, sector_id)
    if ex is None or ex["cur"] != cur:
        return kernel.fx_market.ensure_local(captain, cur, needed)
    short = needed - captain.fx_wallet.get(cur, 0)
    if short <= 0:
        return True
    fee = _fee(kernel, cur)
    k = float(ex["sol"]) * float(ex["local"])
    if short >= float(ex["local"]) * 0.5:
        return kernel.fx_market.ensure_local(captain, cur, needed)
    sol_in = int(math.ceil((k / (float(ex["local"]) - short) - float(ex["sol"])) / (1.0 - fee))) + 1
    if captain.credits < sol_in:
        return False
    captain.credits -= sol_in
    note(kernel, sector_id, sol_in)
    fx_mod.credit(captain, cur, _swap(ex, "sol", sol_in, fee))
    return captain.fx_wallet.get(cur, 0) >= needed


def quote(kernel: Any, sector_id: int, cur: str) -> Optional[float]:
    """A place's own rate for a money (its money per SOL), or None where it keeps no exchange for it."""
    ex = at(kernel, sector_id)
    return rate(ex) if ex is not None and ex["cur"] == cur else None


# ---------------------------------------------------------------------- founding and dividends
def _typical(flow: List[float]) -> float:
    return float(flow[0]) / max(1, int(flow[1]))


def _found(kernel: Any, sec: Any, flow: List[float], logs: List[str], chosen: bool = False) -> bool:
    """Found an exchange at a port: weighed by its council (decide.choose) - or, chosen=True, by a seated sovereign
    who has decided (business.found_exchange)."""
    from xylarium.kernel import decide, history
    port = sec.port
    cur = port.currency
    if cur == SOL:
        return False                                          # SOL's own market is the federation's
    fx = kernel.fx_market
    council = max((w for w in sec.planets if w.population > 0 and w.currency == cur),
                  key=lambda w: (w.treasury, w.id), default=None)
    if council is None:
        return False
    fee = _fee(kernel, cur)
    pool = fx.pools.get(cur)
    # a year of the place's conversions, held on each side - but its SOL side is bought at the federation, and a
    # council pays no more than the fee in slippage for it: what moves the federation's rate by its fee at most
    afford = float(pool["sol"]) * (1.0 - 1.0 / math.sqrt(1.0 + fee)) if pool else 0.0
    depth_sol = min(float(flow[0]), afford)
    if depth_sol <= 0:
        return False
    mid = fx.rate(cur)
    capital_local = int(2 * depth_sol * mid)
    if council.treasury < capital_local:
        return False
    m = decide.mind_of_planet(kernel, council)
    fees_q = fee * float(flow[0]) / 4.0                       # a year's flow, a quarter's fees (SOL)
    waiting = depth_sol * 2 * decide.rate(kernel, cur)        # what the capital earns waiting, a quarter (SOL)
    if not chosen and decide.choose(kernel, [decide.option("exchange", decide.worth(kernel, waiting, m, cur),
                                                            decide.worth(kernel, fees_q, m, cur))],
                                    m, council.id, sec.id, "exchange") is None:
        return False
    half = capital_local // 2
    council.treasury -= half
    sol_side = fx.convert(cur, SOL, half)[0]                  # its SOL side, bought at the federation exchanges
    local_side = min(int(council.treasury), int(sol_side * fx.rate(cur)))   # opened at the federation's rate
    if sol_side <= 0 or local_side <= 0:
        council.treasury += fx.convert(SOL, cur, sol_side)[0] if sol_side > 0 else 0
        return False
    council.treasury -= local_side
    stats(kernel)["of"][str(sec.id)] = {"cur": cur, "sol": float(sol_side), "local": float(local_side),
                                        "seed_sol": float(sol_side), "seed_local": float(local_side),
                                        "founder": council.id, "since": kernel.cycle_count, "fees_sol": 0.0}
    stats(kernel)["founded"] += 1
    history.event(kernel, "EXCHANGE_FOUNDED", f"An exchange opens at {port.name}",
                  actors=[f"planet:{council.id}"], sector_id=sec.id,
                  cause="the money passing through pays for one", data={"depth_sol": round(depth_sol)})
    logs.append(f"[EXCHANGE] {council.name} founds an exchange at {port.name} ({cur}/SOL).")
    return True


def _keep(kernel: Any, ex: Dict[str, Any]) -> None:
    """The founding council keeps its pools near its money's fair rate (backing.py), moving its own money between
    its pools and its vault within the band its bank keeps (CLEARING_BAND) - the place's rate drifts with its trade,
    but no further from what its goods are worth."""
    from xylarium.config import CLEARING_BAND, CLEARING_INTERVENTION_RATE
    from xylarium.kernel import backing
    founder = kernel.get_planet(ex["founder"])
    fair = backing.fair(kernel, ex["cur"])
    if founder is None or not fair or founder.currency != ex["cur"]:
        return
    target = fair * float(ex["sol"])
    held = float(ex["local"])
    if held > target * CLEARING_BAND:                         # its money cheaper there than its goods: take some out
        amt = int((held - target * CLEARING_BAND) * CLEARING_INTERVENTION_RATE)
        ex["local"] = held - amt
        founder.treasury += amt
    elif held < target / CLEARING_BAND:                       # dearer than its goods: put some in
        amt = min(int((target / CLEARING_BAND - held) * CLEARING_INTERVENTION_RATE), max(0, int(founder.treasury)))
        ex["local"] = held + amt
        founder.treasury -= amt


def _dividend(kernel: Any, sid: str, ex: Dict[str, Any]) -> None:
    """Half of what the pools have grown beyond the founder's capital, valued at their own mid, to the founder."""
    founder = kernel.get_planet(ex["founder"])
    if founder is None:
        return
    mid = rate(ex)
    value = float(ex["local"]) + float(ex["sol"]) * mid
    seed = float(ex["seed_local"]) + float(ex["seed_sol"]) * mid
    if value <= seed:
        return
    share = 0.5 * (value - seed) / value
    loc, sol = int(float(ex["local"]) * share), int(float(ex["sol"]) * share)
    ex["local"] = float(ex["local"]) - loc
    ex["sol"] = float(ex["sol"]) - sol
    got = loc + (kernel.fx_market.convert(SOL, founder.currency, sol)[0] if sol > 0 else 0)
    founder.treasury += got


def season(kernel: Any) -> List[str]:
    """Once a year: exchanges founded where the flow pays for one, dividends paid, the year's flow begun afresh."""
    from xylarium.kernel import polity
    if (kernel.cycle_count // polity._quarter()) % 4 or getattr(kernel, "fx_market", None) is None:
        return []
    st = stats(kernel)
    logs: List[str] = []
    for sid, ex in list(st["of"].items()):
        _keep(kernel, ex)
        _dividend(kernel, sid, ex)
    for sid, flow in sorted(st["flow"].items(), key=lambda kv: -kv[1][0]):
        sec = kernel.sectors.get(int(sid))
        if sec is None or sec.port is None or sid in st["of"]:
            continue
        _found(kernel, sec, flow, logs)
    st["last_flow"] = {k: [round(v[0], 1), v[1]] for k, v in st["flow"].items()}
    st["flow"] = {}
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    fx = getattr(kernel, "fx_market", None)
    gaps = {}
    for sid, ex in st["of"].items():
        if fx is not None:
            gaps[sid] = round(rate(ex) / max(1e-9, fx.rate(ex["cur"])) - 1.0, 4)
    return {"exchanges": len(st["of"]), "founded": st["founded"], "gaps": gaps}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="exchanges",
    state=lambda: {"of": {}, "flow": {}, "last_flow": {}, "founded": 0},
    season=season,
    summary=summary,
))
