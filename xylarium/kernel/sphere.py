"""
Xylarium sphere: the universe as a closed 3-sphere of galactic clusters - a formula until someone looks.

Every universe here is closed (creation.big_bang: Omega - 1 > 0). Its space is the 3-sphere of comoving radius
R = c / H0 / sqrt(Omega - 1): finite, without edge - go far enough in any direction and you come back, the far
side of the sphere (its antipode) pi R away. Its galaxy groups and clusters are scattered through it at the measured
number density of haloes above 10^13 suns (~1e-4 per cubic Mpc; Tinker et al. 2008), each with a mass from the halo
mass function (a power law of slope -1.9 cut off at 2e15 suns). Only the nearest NEAREST are drawn - in order of
distance, by inverting the sphere's own volume (2 pi R^3 (x - sin 2x / 2), x the angle round it), so no cluster's
place depends on another's - and each sits at a point of the sphere, so its distance is the arc between the two.

THE EXPANSION is creation's one law, fixed in time: comoving places stand still and the distances between them
grow as a(t). Light crosses comoving distance at c / a(t): a mind's signal from a cluster arrives when the
conformal time since it woke equals the distance. Space here is dominated by its vacuum energy later on, so
conformal time converges: beyond the event horizon (~5 Gpc of comoving distance still crossable from today) light
emitted now never arrives. Signals from far clusters were sent early or never come.

MINDS ELSEWHERE. A cluster raises minds by the home galaxy's own law (cosmos's expectation curve), scaled by its
stars (halo mass x the stellar share of a cluster, ~1%, relative to the home galaxy's); its first mind's epoch is
drawn from that expectation (P(none by t) = e^-lambda(t)). Its signal is heard when its light arrives - once a home
people has charted the sky beyond its own cluster (cluster.py).

The black holes at every galaxy's heart bounce what they swallow (Einstein-Cartan: blackhole.py); in that theory our
own Big Bang is such a bounce, so each is the seed of a universe of its own - the tier beyond this one, waiting.
"""

import bisect
import math
from typing import Any, Dict, List, Optional

N_DENSITY = 1.0e-4              # haloes above 1e13 suns per comoving Mpc^3 (Tinker et al. 2008, h = 0.68)
M_MIN_HALO = 1.0e13             # a galaxy group's halo, suns
M_CUT_HALO = 2.0e15             # the mass function's cut-off (the richest clusters)
SLOPE = -1.9                    # dn/dM ~ M^-1.9 below the cut-off
STAR_SHARE = 0.01               # a cluster's stars over its halo (abundance matching, cluster scale)
NEAREST = 64                    # clusters drawn: the nearest, in order
CONFORMAL_GRID = 0.05           # Gyr between points of the conformal-time table
CONFORMAL_TO = 200.0            # Gyr: far enough that conformal time has converged


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "sphere")


def _rng(kernel: Any, *parts: Any):
    from xylarium.kernel import scheduler
    return scheduler.rng(kernel, "sphere", *parts)


# ---------------------------------------------------------------------- conformal time (light on comoving space)
_ETA: Dict[str, List[float]] = {}


def _eta_table() -> List[float]:
    """eta(t) = integral of c / a(t) dt, comoving Mpc, on a grid from the Big Bang."""
    if "t" not in _ETA:
        from xylarium.kernel import creation
        c = creation.C_KMS * creation.KM_S_MPC_PER_GYR                      # Mpc per Gyr
        out, s = [0.0], 0.0
        n = int(CONFORMAL_TO / CONFORMAL_GRID)
        for i in range(n):
            t = (i + 0.5) * CONFORMAL_GRID
            s += c * CONFORMAL_GRID / creation.scale_factor(t)
            out.append(s)
        _ETA["t"] = out
    return _ETA["t"]


def eta(t_gyr: float) -> float:
    tab = _eta_table()
    x = max(0.0, t_gyr) / CONFORMAL_GRID
    i = min(len(tab) - 2, int(x))
    return tab[i] + (tab[i + 1] - tab[i]) * (x - i)


def arrival(t_emit: float, chi_mpc: float) -> Optional[float]:
    """When light sent at t_emit from chi comoving Mpc away arrives (None: never - beyond the event horizon)."""
    tab = _eta_table()
    want = eta(t_emit) + chi_mpc
    if want > tab[-1]:
        return None
    i = bisect.bisect_left(tab, want)
    lo, hi = tab[i - 1], tab[i]
    return (i - 1 + (want - lo) / max(1e-12, hi - lo)) * CONFORMAL_GRID


def event_horizon_mpc(t_gyr: float) -> float:
    """Comoving distance light sent now can still cross, ever."""
    return _eta_table()[-1] - eta(t_gyr)


# ---------------------------------------------------------------------- the sphere and its clusters
def _volume(x: float, r: float) -> float:
    """Comoving volume within angle x of a point on the 3-sphere of radius r."""
    return 2.0 * math.pi * r ** 3 * (x - math.sin(2.0 * x) / 2.0)


def _angle_for(v: float, r: float) -> float:
    lo, hi = 0.0, math.pi
    for _ in range(60):
        mid = (lo + hi) / 2
        if _volume(mid, r) < v:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _halo_mass(rng: Any) -> float:
    a1 = SLOPE + 1.0
    while True:
        u = rng.random()
        m = (M_MIN_HALO ** a1 + u * ((50 * M_CUT_HALO) ** a1 - M_MIN_HALO ** a1)) ** (1.0 / a1)
        if rng.random() < math.exp(-m / M_CUT_HALO):
            return m


def _first_mind(kernel: Any, scale: float, rng: Any) -> Optional[float]:
    """The epoch of a cluster's first mind: lambda(t) = the home galaxy's expectation x scale reaches -ln u."""
    from xylarium.kernel import cosmos
    curve = cosmos.stats(kernel).get("curve") or []
    need = -math.log(max(1e-300, rng.random()))
    prev = 0.0
    for c, lam in enumerate(curve):
        lam *= scale
        if lam >= need:
            frac = (need - prev) / max(1e-12, lam - prev)
            return (c - 1 + frac) * cosmos.CURVE_STEP if c else 0.0
        prev = lam
    return None


def genesis(kernel: Any) -> None:
    """Lay out the nearest clusters on the sphere (at the epoch the first mind arises: cosmos.genesis)."""
    from xylarium.kernel import cluster, creation
    from xylarium.kernel.natives import _name
    st = stats(kernel)
    bb = creation.big_bang(creation.universe(kernel))
    r = bb["curvature_mpc"]
    st["radius_mpc"] = r
    st["circumference_mpc"] = round(2 * math.pi * r, 1)
    home_stars = cluster.HOME_MASS
    rng = _rng(kernel, "nearest")
    v, out = 0.0, []
    for n in range(NEAREST):
        v += rng.expovariate(N_DENSITY)                            # the next cluster outward: a Poisson process
        x = _angle_for(v, r)
        g = _rng(kernel, "cluster", n)
        m = _halo_mass(g)
        # a point at angle x from home, in a direction uniform on the 2-sphere
        cz, ph = 2 * g.random() - 1.0, 2 * math.pi * g.random()
        sz = math.sqrt(1 - cz * cz)
        point = [math.cos(x), math.sin(x) * sz * math.cos(ph), math.sin(x) * sz * math.sin(ph), math.sin(x) * cz]
        scale = m * STAR_SHARE * bb["stars"] / home_stars
        mind = _first_mind(kernel, scale, g)
        chi = x * r
        heard = arrival(mind, chi) if mind is not None else None
        out.append({"name": _name(g), "halo": float(f"{m:.3g}"), "chi_mpc": round(chi, 2),
                    "point": [round(c, 9) for c in point], "first_mind": None if mind is None else round(mind, 4),
                    "heard_at": None if heard is None else round(heard, 4), "heard": False})
    st["clusters"] = out


def distance(kernel: Any, a: List[float], b: List[float]) -> float:
    """The comoving distance between two points of the sphere: the arc, the shorter way round."""
    from xylarium.kernel import geometry
    return geometry.arc_kpc(a, b, float(stats(kernel).get("radius_mpc") or 0.0))   # Mpc in, Mpc out


def proper_mpc(kernel: Any, chi_mpc: float, at_gyr: Optional[float] = None) -> float:
    """Comoving distance as it is at an epoch: stretched by the expansion."""
    from xylarium.kernel import cosmos, creation
    t = cosmos.deep_gyr(kernel) if at_gyr is None else at_gyr
    return chi_mpc * creation.scale_factor(t)


# ---------------------------------------------------------------------- the season
def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import cluster, cosmos, history, primordial
    if not cosmos.is_cosmic(kernel):
        return []
    st = stats(kernel)
    if not st.get("clusters") or not cluster.stats(kernel).get("charted"):
        return []
    now = cosmos.deep_gyr(kernel)
    logs = []
    for c in st["clusters"]:
        if c["heard"] or c["heard_at"] is None or c["heard_at"] > now:
            continue
        c["heard"] = True
        far = proper_mpc(kernel, c["chi_mpc"])
        history.event(kernel, "SIGNAL", f"A signal from beyond the cluster: {c['name']}",
                      cause=f"a mind arose there {c['first_mind']:.2f} Gyr after the Big Bang; its light crossed "
                            f"{c['chi_mpc']:.0f} Mpc of expanding space ({far:.0f} Mpc now)",
                      data={"cluster": c["name"], "chi_mpc": c["chi_mpc"], "halo": c["halo"]})
        primordial.first(kernel, "first_signal_beyond_the_cluster", c["name"])
        logs.append(f"[COSMOS] A signal from {c['name']}, {far:.0f} Mpc away: someone else, long ago.")
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    from xylarium.kernel import cosmos
    st = stats(kernel)
    cs = st.get("clusters") or []
    if not cs:
        return {}
    now = cosmos.deep_gyr(kernel)
    return {"radius_mpc": st["radius_mpc"], "circumference_mpc": st["circumference_mpc"],
            "nearest_mpc": cs[0]["chi_mpc"], "drawn": len(cs), "heard": sum(1 for c in cs if c["heard"]),
            "will_be_heard": sum(1 for c in cs if c["heard_at"] is not None),
            "event_horizon_mpc": round(event_horizon_mpc(now), 1)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="sphere",
    state=lambda: {"clusters": [], "radius_mpc": 0.0, "circumference_mpc": 0.0},
    season=quarter,
    summary=summary,
))
