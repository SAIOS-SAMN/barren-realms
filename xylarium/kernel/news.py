"""
Xylarium news: what a place knows of another's prices is what light has carried from it.

A price is heard, never seen: the word of it leaves its port and arrives a light-time later (signals: the proper
distance over light's speed; a relay, once a people builds one, would shorten it). A trader weighs a far market on
what it last heard, and that word is old.

  MEMORY    every open port's price of every good it shelves is followed season by season: its latest, its long
            mean (the running mean of its log price since first heard), and how much it moves (the running variance
            of its seasonal log change) - kept as a few numbers a pair, nothing tuned.
  HEARD     what a place has heard of a market is what has reached it (comms.py): word carried by ships, convoys and
            relay posts, stamped with the cycle it left - never faster than its carrier.
  AGE       what that word's age costs: the drift a price makes over it, one deviation of its own moves scaled to the
            age (sigma sqrt(age)) - the premium a trader pays for acting on old news, and the gap a nearer, faster
            trader profits from.
"""

import math
from typing import Any, Dict, Optional, Tuple

LY_PER_KPC = 3261.56            # light years in a kiloparsec (signals.py)


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "news")


def _seasons_per_year() -> float:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return 100.0 / FISCAL_QUARTER_CYCLES


def season(kernel: Any) -> None:
    """Each season: every open port's price of every good on its shelves, followed (running moments, exact counts)."""
    from xylarium.kernel.economy import EconomyManager
    mem = stats(kernel)["mem"]
    for sid, sec in sorted(kernel.sectors.items()):
        port = getattr(sec, "port", None)
        if port is None:
            continue
        for comm in sorted(port.stock):
            sell = EconomyManager.get_unit_prices(port, comm)[1]
            if not sell or sell <= 0:
                continue
            x = math.log(float(sell))
            key = f"{sid}|{comm}"
            m = mem.get(key)
            if m is None:
                mem[key] = {"n": 1, "mean": x, "last": x, "rn": 0, "rmean": 0.0, "rm2": 0.0, "at": kernel.cycle_count}
                continue
            m["n"] += 1
            m["mean"] += (x - m["mean"]) / m["n"]                           # running mean of the log price
            r = x - m["last"]                                               # this season's log change
            m["rn"] += 1
            d = r - m["rmean"]
            m["rmean"] += d / m["rn"]
            m["rm2"] += d * (r - m["rmean"])                                # Welford: running variance of changes
            m["last"], m["at"] = x, kernel.cycle_count
    return None


def sigma(kernel: Any, port_sid: int, comm: str) -> float:
    """A port's price's yearly deviation of log change (0 where it has not been followed long enough)."""
    m = stats(kernel)["mem"].get(f"{port_sid}|{comm}")
    if m is None or m["rn"] < 2:
        return 0.0
    return math.sqrt(m["rm2"] / (m["rn"] - 1) * _seasons_per_year())


def light_years(kernel: Any, a: int, b: int) -> float:
    """How long word takes between two systems (years): their proper distance over light's speed."""
    if a == b:
        return 0.0
    from xylarium.kernel import cosmos
    try:
        d = cosmos.distance_kpc(kernel, a, b)
    except Exception:
        d = None
    return float(d) * LY_PER_KPC if d else 0.0


def heard(kernel: Any, at: int, port_sid: int, comm: str) -> Optional[Tuple[float, float, float]]:
    """A port's price of a good as heard at system `at` - the word that has reached it (comms.py: carried by ships,
    convoys and relay posts, never faster than they go): (price, the word's age in years, its yearly deviation of
    log change). None if no word of it has ever arrived."""
    from xylarium.kernel import comms
    got = comms.heard(kernel, at, port_sid, comm)
    if got is None:
        return None
    price, stamp = got
    return float(price), max(0.0, (kernel.cycle_count - stamp) / 100.0), sigma(kernel, port_sid, comm)


def age_cost(price: float, age_years: float, sigma: float) -> float:
    """What acting on a word this old costs a unit: the drift one deviation of the price's own moves makes over the
    age, price (e^(sigma sqrt(age)) - 1)."""
    if age_years <= 0 or sigma <= 0:
        return 0.0
    return price * (math.exp(sigma * math.sqrt(age_years)) - 1.0)


def summary(kernel: Any) -> Dict[str, Any]:
    return {"followed": len(stats(kernel)["mem"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="news", state=lambda: {"mem": {}}, season=season, summary=summary))
