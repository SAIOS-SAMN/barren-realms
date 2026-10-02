"""
Xylarium signals: peoples hear one another before they meet - by the light their works leak.

Every people that uses power leaks a share of it as light someone else could catch: radio and radar, the glow of its
cities and industry, the waste heat of its works (LEAK_SHARE, declared: Earth leaks ~1e9 W of radio against ~2e13 W
used). A listener catches it if the flux reaching it - leak / (4 pi d^2), d the proper distance through the galaxy's
curved space (geometry) - beats what its instruments resolve, and its instruments grow with what it puts to work: a
people's apertures, like its other works, scale with its power (S_MIN at the power of a single radio telescope,
falling as the listener's power over it). And light takes time: a signal heard now left d / c ago, so a listener
hears a people only once that people has been leaking for that long.

What hearing does: the listener knows the other exists, roughly how much power it commands (mastery.py), and where -
the first word of every relation between them (federation.py reads it); the ledger tells it (FIRST_SIGNAL). Hearing
is not meeting: no ship has crossed, no word is understood (contact.py measures that), nothing can yet be traded.
"""

import math
from typing import Any, Dict, List

LEAK_SHARE = 5.0e-5             # share of a people's power leaked as detectable light (declared: Earth's radio
                                # leakage over its power use)
S_MIN_W_M2 = 1.0e-26            # flux a single great radio telescope resolves over a narrow band (W/m^2; Arecibo-class)
S_MIN_POWER_W = 1.0e13          # the power of a people that builds one such instrument (Earth's, at Arecibo's time)
LY_PER_KPC = 3261.56
M_PER_KPC = 3.0857e19


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "signals")


def reach_kpc(leak_w: float, listener_w: float) -> float:
    """How far a leak of leak_w is heard by a listener commanding listener_w."""
    s_min = S_MIN_W_M2 * S_MIN_POWER_W / max(1.0, listener_w)
    return math.sqrt(max(0.0, leak_w) / (4.0 * math.pi * s_min)) / M_PER_KPC


def heard(kernel: Any, listener: str) -> Dict[str, Any]:
    return stats(kernel)["heard"].get(listener, {})


def season(kernel: Any) -> List[str]:
    """Once a year every people listens."""
    from xylarium.kernel import cosmos, history, mastery
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    ps = mastery.peoples(kernel)
    power = {who: mastery.power_w(kernel, ws) for who, ws in ps.items()}
    homes = {who: mastery.home(ws) for who, ws in ps.items()}
    since = st["since"]
    for who in ps:
        since.setdefault(who, kernel.cycle_count)             # when it began to leak (first seen with works)
    now_years = kernel.cycle_count / 100.0 * cosmos.ruler(kernel)   # deep years since the clock began
    logs: List[str] = []
    for a in ps:
        for b in ps:
            if a == b or b in st["heard"].get(a, {}):
                continue
            ha, hb = homes[a], homes[b]
            if ha.sector_id == hb.sector_id:
                d = 0.0
            else:
                d = cosmos.distance_kpc(kernel, ha.sector_id, hb.sector_id)
                if d is None:
                    continue
            if d > reach_kpc(power[b] * LEAK_SHARE, power[a]):
                continue
            leaking_years = now_years - since[b] / 100.0 * cosmos.ruler(kernel)
            if leaking_years < d * LY_PER_KPC:                   # its first light has not arrived yet
                continue
            st["heard"].setdefault(a, {})[b] = {"cycle": kernel.cycle_count, "kpc": round(d, 4),
                                                "power_w": float(f"{power[b]:.3g}")}
            st["count"] += 1
            history.event(kernel, "FIRST_SIGNAL", f"{a.split(':', 1)[-1]} hears {b.split(':', 1)[-1]}",
                          sector_id=ha.sector_id, actors=[a, b],
                          cause=f"the light of its works, {d * LY_PER_KPC:,.0f} light years away",
                          data={"kpc": round(d, 4)})
            logs.append(f"[SIGNALS] {a.split(':', 1)[-1]} hears another people across {d * LY_PER_KPC:,.0f} light years.")
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"heard_pairs": st["count"], "listeners": len(st["heard"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="signals", state=lambda: {"heard": {}, "since": {}, "count": 0}, season=season,
                             summary=summary))
