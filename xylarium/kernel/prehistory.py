"""
Xylarium prehistory: what the elder peoples of a galaxy did before a younger world woke - at the level of history,
cheap enough to run across billions of years and many universes.

The full engine lives a people's history year by year; it cannot live four billion years of a galaxy's. Here every
mind the Big Bang's schedule gives the galaxy (creation.schedule: where, when) is given a life at the level of
history, from a handful of rates the progenitors declare as ranges - the same rates the full engine's own runs are
there to measure (tools/elders.py reads its live runs where they have them):

  CROSSING   how long after waking it crosses to the stars (mastery.py), or that it never does;
  LIFETIME   how long it lasts before it falls (a constant hazard: no people is promised a future);
  EXPANSION  how fast its reach grows once it has crossed (folded space, hops by hops);
  DOCTRINE   what it does with the young it finds - its alignment, drawn, read as federation.preferred_card;
  SETTLING   how soon, once its reach covers a system, it settles there - and, living there, holds that system's
             skies (skies.py: a people living on a world keeps its air).

The galaxy turns while they live: each home rides its own ring (cosmos.omega) and a system's distance from it changes
as the inner rings overtake the outer. What comes out, for any system at any time: who could have reached it, who
did, what they kept (a green world held green), what they left when they fell (ruins), whether they struck, and
whether its sky is quiet when its own mind looks up.
"""

import math
import random
from typing import Any, Dict, List, Optional, Tuple

PRIORS = {                                   # (low, high, scale) - the progenitors' declared ranges
    "cross_log10_yr": (3.0, 7.0, "lin"),     # years from waking to crossing
    "never_cross": (0.1, 0.9, "lin"),        # share of peoples that never cross
    "fall_per_gyr": (0.01, 10.0, "log"),     # a people's hazard of falling
    "reach_kpc_per_myr": (1.0e-3, 1.0, "log"),   # how fast a crossed people's reach grows
    "alignment_sd": (0.1, 0.6, "lin"),       # the spread of peoples' alignments
    "settle_per_myr": (1.0e-3, 1.0, "log"),  # how soon a people settles a system its reach covers
    "war_per_contact": (0.0, 0.5, "lin"),    # the chance two peoples of opposed doctrines meeting at a system war
}


def draw(rng: random.Random) -> Dict[str, float]:
    out = {}
    for k, (lo, hi, sc) in PRIORS.items():
        u = rng.random()
        out[k] = math.exp(math.log(lo) + u * (math.log(hi) - math.log(lo))) if sc == "log" else lo + u * (hi - lo)
    return out


def homes(seed: Any, horizon: float) -> List[Dict[str, float]]:
    """Every mind of the galaxy before an epoch: when it woke, its ring and its starting angle. The witnessed cells'
    minds are worked out (creation.witnessed); each stands for the unobserved cells like it - as many more as the
    witnessed share is short of the whole, on its ring, at its epoch, at angles the seed's dice give them."""
    from xylarium.kernel import creation
    out = []
    per = 1.0 / creation.share_witnessed(seed)
    owed = 0.0
    for n, m in enumerate(creation.schedule(seed)["minds"]):
        if m["epoch"] > horizon:
            break
        slot = creation.cell(seed, *m["cell"])[m["k"]]
        out.append({"epoch": m["epoch"], "r": slot["r"], "theta0": slot["theta0"]})
        owed += per - 1.0
        rng = random.Random(f"{seed}:unseen-home:{n}")
        while owed >= 1.0:
            owed -= 1.0
            out.append({"epoch": m["epoch"], "r": slot["r"], "theta0": rng.random() * 2.0 * math.pi})
    out.sort(key=lambda h: h["epoch"])
    return out


def _angle(r: float, theta0: float, t_gyr: float) -> float:
    from xylarium.kernel import cosmos
    return theta0 + cosmos.omega(r) * t_gyr * 1000.0


def distance(a: Tuple[float, float], b: Tuple[float, float], t: float) -> float:
    """kpc between two systems on their rings at epoch t (each turning at its own rate)."""
    ta, tb = _angle(a[0], a[1], t), _angle(b[0], b[1], t)
    return math.sqrt(a[0] ** 2 + b[0] ** 2 - 2 * a[0] * b[0] * math.cos(ta - tb))


def lives(elders: List[Dict[str, float]], p: Dict[str, float], rng: random.Random) -> List[Dict[str, Any]]:
    """Each elder's history: when it crossed (or not), when it fell, its doctrine."""
    from xylarium.kernel import federation
    out = []
    for e in elders:
        crosses = rng.random() >= p["never_cross"]
        cross = e["epoch"] + 10.0 ** (p["cross_log10_yr"] + rng.gauss(0.0, 0.5)) / 1e9 if crosses else float("inf")
        fall = e["epoch"] + rng.expovariate(p["fall_per_gyr"])
        a = max(-1.0, min(1.0, rng.gauss(0.0, p["alignment_sd"])))
        out.append({**e, "cross": cross, "fall": fall, "card": federation.preferred_card(a), "alignment": a})
    return out


def reach_kpc(life: Dict[str, Any], p: Dict[str, float], t: float) -> float:
    if t < life["cross"] or t > life["fall"]:
        return 0.0
    return min(40.0, p["reach_kpc_per_myr"] * (t - life["cross"]) * 1000.0)


def visit(lives_: List[Dict[str, Any]], p: Dict[str, float], target: Tuple[float, float], t0: float, t1: float,
          rng: random.Random, steps: int = 12) -> List[Dict[str, Any]]:
    """Who reached a system between t0 and t1, and who settled it: (elder, first in reach, settled at or None)."""
    out = []
    for life in lives_:
        if life["cross"] > t1 or life["fall"] < t0:
            continue
        first, settled = None, None
        for n in range(steps + 1):
            t = t0 + (t1 - t0) * n / steps
            if reach_kpc(life, p, t) >= distance((life["r"], life["theta0"]), target, t):
                first = t
                break
        if first is None:
            continue
        stay = min(t1, life["fall"]) - first
        wait = rng.expovariate(p["settle_per_myr"]) / 1000.0
        if wait <= stay:
            settled = first + wait
        out.append({"life": life, "first": first, "settled": settled})
    return out


def sol(seed: Any, p: Dict[str, float], rng: random.Random, sol_born: float, mars_green: List[List[float]],
        now: float, elders: Optional[List[Dict[str, float]]] = None) -> Dict[str, Any]:
    """Our own system's history at the level of history, under one draw of the rates: a Sun born at sol_born on the
    8 kpc ring (its angle drawn), Mars green over mars_green (Gyr after the Sun's birth), its mind at now."""
    from xylarium.kernel import cosmos
    target = (cosmos.R0_KPC, 2.0 * math.pi * rng.random())
    elders = elders if elders is not None else homes(seed, now)
    ls = lives([e for e in elders if e["epoch"] < now], p, rng)
    seen = visit(ls, p, target, sol_born, now, rng)
    out = {"elders": len(ls), "crossed": sum(1 for x in ls if x["cross"] < now),
           "reached": len(seen), "settled": sum(1 for v in seen if v["settled"] is not None)}
    # Mars while it was green: who was living in the system then, and whether they held its air
    kept, struck = False, False
    if mars_green:
        g0, g1 = sol_born + mars_green[0][0], sol_born + mars_green[-1][1]
        there = [v for v in seen if v["settled"] is not None and v["settled"] <= g1 and v["life"]["fall"] > g0]
        kept = any(v["life"]["fall"] > g1 for v in there)               # living there past the thaw's end, it held it
        cards = {v["life"]["card"] for v in seen if v["first"] <= g1 and v["life"]["fall"] > g0}
        if "DELTA" in cards and cards & {"ALPHA", "BETA", "GAMMA"} and rng.random() < p["war_per_contact"]:
            struck = True
    ruins = sum(1 for v in seen if v["settled"] is not None and v["life"]["fall"] < now)
    present = [v for v in seen if v["life"]["fall"] > now and v["first"] <= now]
    loud = [v for v in present if v["life"]["card"] in ("GAMMA", "DELTA")]
    out.update({"mars_kept_green": kept, "mars_struck": struck, "ruins": ruins, "elders_present": len(present),
                "quiet_sky": not loud, "watchers": sum(1 for v in present if v["life"]["card"] in ("ALPHA", "BETA"))})
    return out
