"""
Xylarium cluster: the galactic cluster around the home galaxy - a formula until it is witnessed.

The home galaxy is simulated (cosmos.py); its cluster's other galaxies are analytic objects, fixed by the seed:

  GALAXIES   GALAXIES_IN_CLUSTER of them, stellar masses drawn from the measured galaxy stellar mass function (a
             Schechter function, alpha -1.2, M* 5e10 solar masses, down to dwarfs of 1e8), placed through a
             Local-Group-sized volume (radius 1.5 Mpc) about the cluster's barycentre, each on a circular orbit at the
             speed the cluster's mass gives at its radius - closed form, as the galaxy's own stars are.
  MERGER     the most massive companion falls toward the home galaxy from rest on its free-fall time,
             (pi/2) sqrt(r^3 / 2G(M1 + M2)) with both galaxies' haloes (stellar mass x the measured halo-to-stellar
             ratio): a Local-Group pair meets in ~5-7 Gyr - inside a long game at a neighbourly pace.
  MINDS      each galaxy raises minds by the same law the home galaxy does (cosmos.schedule's expectation curve),
             scaled by its stellar mass and by its metals (the mass-metallicity relation, Z ~ M^0.3: small galaxies
             are metal-poor, and rocky worlds need metals); the minds are drawn from the seed and never placed.

Witnessing: a home people that first reaches space charts the cluster (its observatories leave the atmosphere). A
mind in another galaxy is heard once its light has crossed the distance - and the rule at this tier boundary is
written down: light between galaxies travels on deep time (cosmos.ruler), so Andromeda's 2.5 million years of light
take ~2.5 clock years at the neighbourly pace. Every charting, first signal and the merger are ledger events.
"""

import bisect
import heapq
import math
from typing import Any, Dict, List, Optional

ALPHA = -1.2                    # galaxy stellar mass function slope (Baldry et al. 2012)
M_STAR = 5.0e10                 # its knee, solar masses
M_MIN = 1.0e8                   # the dwarfs counted
HOME_MASS = 6.0e10              # the home galaxy's stellar mass (a Milky Way, a data point)
CLUSTER_KPC = 1500.0            # the cluster's radius (the Local Group's)
HALO_TO_STARS = 30.0            # a galaxy's halo mass over its stellar mass (abundance matching, Milky Way scale)
G_KPC = 4.30091e-6              # G in kpc (km/s)^2 / solar mass
GYR_PER_KPC_PER_KMS = 0.9778    # 1 kpc / (1 km/s) in Gyr
LIGHT_YEARS_PER_KPC = 3261.56
MZ_SLOPE = 0.3                  # metallicity ~ stellar mass^0.3 (Tremonti et al. 2004)
SIGNAL_TALLY = 200              # minds kept per galaxy (the earliest), enough for every signal a game will hear


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "cluster")


def _rng(kernel: Any, *parts: Any):
    from xylarium.kernel import scheduler
    return scheduler.rng(kernel, "cluster", *parts)


def _schechter(rng: Any) -> float:
    """A stellar mass from the Schechter function above M_MIN (rejection against the power law)."""
    while True:
        # sample the power law x^ALPHA on [x0, 10]; accept with e^-x
        x0, x1 = M_MIN / M_STAR, 10.0
        a1 = ALPHA + 1.0
        u = rng.random()
        x = (x0 ** a1 + u * (x1 ** a1 - x0 ** a1)) ** (1.0 / a1)
        if rng.random() < math.exp(-x):
            return x * M_STAR


def genesis(kernel: Any) -> None:
    """Lay out the home cluster at the epoch the first mind arises (cosmos.genesis)."""
    from xylarium.kernel import cosmos
    from xylarium.kernel.natives import _name
    st = stats(kernel)
    rng = _rng(kernel, "layout")
    gals = [{"name": "the home galaxy", "mass": HOME_MASS, "r": 0.0, "pos": [0.0, 0.0, 0.0], "home": True}]
    for n in range(cosmos.GALAXIES_IN_CLUSTER - 1):
        m = _schechter(rng)
        r = CLUSTER_KPC * rng.random() ** (1.0 / 3.0)
        cz = 2 * rng.random() - 1.0
        ph = 2 * math.pi * rng.random()
        sz = math.sqrt(1 - cz * cz)
        gals.append({"name": _name(_rng(kernel, "name", n)), "mass": round(m, -6),
                     "pos": [round(r * sz * math.cos(ph), 2), round(r * sz * math.sin(ph), 2), round(r * cz, 2)],
                     "r": round(r, 2)})
    total = sum(g["mass"] for g in gals) * HALO_TO_STARS
    for i, g in enumerate(gals):
        d = math.dist(g["pos"], [0.0, 0.0, 0.0])
        g["dist_kpc"] = round(d, 2)
        g["v_kms"] = round(math.sqrt(G_KPC * total / max(50.0, g["r"] or d or 50.0)), 2)
        g["metals"] = round(min(1.0, (g["mass"] / HOME_MASS) ** MZ_SLOPE), 4)
        g["scale"] = round(g["mass"] / HOME_MASS * g["metals"], 6)
    st["galaxies"] = gals
    # the merger: the most massive companion falls from rest toward the home galaxy
    comp = max(range(1, len(gals)), key=lambda i: gals[i]["mass"])
    r, m2 = gals[comp]["dist_kpc"], (HOME_MASS + gals[comp]["mass"]) * HALO_TO_STARS
    t_ff = math.pi / 2 * math.sqrt(r ** 3 / (2 * G_KPC * m2)) * GYR_PER_KPC_PER_KMS
    st["merger"] = {"with": comp, "epoch": round(float(cosmos.stats(kernel)["epoch0"]) + t_ff, 4), "done": False,
                    "free_fall_gyr": round(t_ff, 3)}
    _draw_minds(kernel)


def _draw_minds(kernel: Any) -> None:
    """Each galaxy's minds: the home galaxy's expectation curve, scaled; epochs by inverse transform."""
    from xylarium.kernel import cosmos
    st = stats(kernel)
    curve = cosmos.stats(kernel).get("curve") or [0.0]
    step = cosmos.CURVE_STEP
    for i, g in enumerate(st["galaxies"]):
        if g.get("home"):
            continue
        rng = _rng(kernel, "minds", i)
        lam = curve[-1] * g["scale"]
        # Poisson count up to the horizon, then each epoch by inverting the (scaled) curve
        n, p, L = 0, rng.random(), math.exp(-min(700.0, lam))
        if lam > 50:                                       # normal approximation for large expectations
            n = max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
        else:
            while p > L:
                n += 1
                p *= rng.random()
        epochs = []
        for _ in range(n):                                 # every mind, by inverse transform on the curve
            u = rng.random() * curve[-1]
            k = bisect.bisect_left(curve, u)
            k = min(max(k, 1), len(curve) - 1)
            lo = curve[k - 1]
            frac = (u - lo) / max(1e-12, curve[k] - lo)
            epochs.append((k - 1 + frac) * step)
        g["minds"] = [round(e, 5) for e in heapq.nsmallest(SIGNAL_TALLY, epochs)]
        g["minds_by_horizon"] = n
        g["heard"] = 0


def light_gyr(dist_kpc: float) -> float:
    return dist_kpc * LIGHT_YEARS_PER_KPC / 1.0e9


def position(kernel: Any, i: int, cycle: Optional[int] = None) -> Optional[List[float]]:
    """A galaxy's place in the cluster (kpc) at a clock cycle: a circular orbit about the barycentre, closed form."""
    from xylarium.kernel import cosmos
    gals = stats(kernel).get("galaxies") or []
    if not (0 <= i < len(gals)):
        return None
    g = gals[i]
    if g.get("home") or not g["r"]:
        return list(g["pos"])
    t_myr = (cosmos.deep_gyr(kernel, cycle) - float(cosmos.stats(kernel)["epoch0"])) * 1000.0
    om = g["v_kms"] / g["r"] / GYR_PER_KPC_PER_KMS / 1000.0          # rad per Myr
    x, y, z = g["pos"]
    c, s = math.cos(om * t_myr), math.sin(om * t_myr)
    return [round(x * c - y * s, 2), round(x * s + y * c, 2), z]


# ---------------------------------------------------------------------- the season
def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import cosmos, history, primordial
    if not cosmos.is_cosmic(kernel):
        return []
    st = stats(kernel)
    if not st.get("galaxies"):
        return []
    logs: List[str] = []
    now = cosmos.deep_gyr(kernel)
    firsts = ((kernel.state.get("genesis") or {}).get("firsts") or {})
    if not st["charted"] and "first_starship" in firsts:
        st["charted"] = kernel.cycle_count
        who = firsts["first_starship"]["who"]
        big = sorted(st["galaxies"][1:], key=lambda g: -g["mass"])[:3]
        history.event(kernel, "CLUSTER_CHARTED", f"The {who} chart the galaxies beyond their own", actors=[who],
                      cause="observatories above the air",
                      text="Beyond the home galaxy: " + ", ".join(
                          f"{g['name']} ({g['mass']:.1e} suns, {g['dist_kpc'] / 1000:.2f} Mpc)" for g in big)
                      + f", and {len(st['galaxies']) - 4} more.")
        primordial.first(kernel, "first_cluster_charted_beyond", who)
        logs.append(f"[COSMOS] The {who} chart the {len(st['galaxies']) - 1} galaxies of their cluster.")
    if st["charted"]:
        for g in st["galaxies"][1:]:
            due = [e for e in g.get("minds", []) if e + light_gyr(g["dist_kpc"]) <= now]
            if len(due) > g.get("heard", 0):
                if g.get("heard", 0) == 0:
                    history.event(kernel, "SIGNAL", f"A signal from {g['name']}",
                                  cause=f"a mind arose there {light_gyr(g['dist_kpc']) * 1000:.1f} Myr of light ago",
                                  data={"galaxy": g["name"], "dist_kpc": g["dist_kpc"]})
                    primordial.first(kernel, "first_signal_beyond", g["name"])
                    logs.append(f"[COSMOS] A signal from {g['name']}: someone else is there.")
                g["heard"] = len(due)
    m = st["merger"]
    if not m["done"] and now >= m["epoch"]:
        m["done"] = True
        g = st["galaxies"][m["with"]]
        history.event(kernel, "GALAXIES_MERGE", f"The home galaxy and {g['name']} meet",
                      cause=f"bound together, they fell {g['dist_kpc'] / 1000:.2f} Mpc in {m['free_fall_gyr']:.2f} Gyr",
                      magnitude=g["mass"])
        logs.append(f"[COSMOS] The home galaxy and {g['name']} meet.")
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    gals = st.get("galaxies") or []
    if not gals:
        return {}
    from xylarium.kernel import cosmos
    m = st["merger"]
    return {"galaxies": len(gals), "charted": bool(st["charted"]),
            "minds_elsewhere_by_horizon": sum(g.get("minds_by_horizon", 0) for g in gals[1:]),
            "galaxies_heard": sum(1 for g in gals[1:] if g.get("heard")),
            "merger_with": gals[m["with"]]["name"], "merger_in_gyr": round(m["epoch"] - cosmos.deep_gyr(kernel), 3)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="cluster",
    state=lambda: {"galaxies": [], "merger": {}, "charted": 0},
    season=quarter,
    summary=summary,
))
