"""
Xylarium orbits: a world's orbit in all its dimensions - its shape, its tilt, its spin - and the moons a giant
gathers.

A circular, coplanar orbit is a collapse: three of a Keplerian orbit's six elements thrown away. Here every world
keeps its six (semi-major axis, eccentricity, inclination, the node and perihelion's directions, its phase) and a
spin vector (a period and an obliquity), and each is what physics made it:

  ECCENTRICITY  a young system stirs its own planets up toward the speed of escape from its largest body (Safronov:
                e ~ v_esc / v_orb), and passing stars stir them more in a crowded neighbourhood; only orbits that
                do not cross survive (half the gap to a neighbour bounds each), so packed systems are calm and a
                lone giant may be wild. A neighbour forces an eccentricity on its fellow for ever (Laplace-Lagrange:
                ~5/4 x their semi-major axes' ratio x its own). The host's tides damp the rest (Goldreich & Soter:
                tau_e = 4/63 (Q / k2) (m / M) (a / R)^5 / n).
  INCLINATION   stirred with the eccentricity, half as much (equipartition of random velocities).
  SPIN          a world is born spinning at a share of its break-up rate; its host's tides brake it until it is
                locked, face to its host (Gladman et al. 1996: t = w a^6 I Q / (3 G M^2 k2 R^5)).
  OBLIQUITY     giant impacts leave a spin axis pointing anywhere (isotropic); a locked world's settles upright.
  MOONS         a giant gathers about a ten-thousandth of its mass into regular moons (Canup & Ward 2006), shared
                among a few that migrate inward through its disc into a chain of resonances - each forcing an
                eccentricity on its neighbour (mass ratio / distance from exact resonance), so its tides never
                stop (Io, Europa, Ganymede).
"""

import math
from typing import Any, Dict, List

from xylarium.kernel import interior as I

STIR = 0.5                      # Rayleigh scale of eccentricity in units of v_esc / v_orb of the system's largest body
                                # (Safronov self-stirring, damped by the disc; declared)
FLYBY_STIR = 0.02               # eccentricity a unit-density neighbourhood's passing stars add at 1 AU (~ a^1.5)
MOON_SHARE = 1.0e-4             # a giant's regular moons over its mass (Canup & Ward 2006)
MOONS_MAX = 4
MOON_MIN = 1.0e-4               # unit masses: smaller moonlets are not worlds
INNER_MOON_RADII = (5.0, 10.0)  # the innermost regular moon's orbit, in its giant's radii (inside, tides tear it)
RESONANCE_RATIO = 2.0 ** (2.0 / 3.0)    # 2:1 period ratio between neighbours in the chain
RESONANCE_OFFSET = (1.0e-3, 1.0e-1)     # how far from exact resonance (log-uniform): the luck of migration
SPIN_SHARE = (0.1, 0.5)         # birth spin as a share of break-up
INERTIA = 0.33                  # moment of inertia factor of a differentiated world


def _rayleigh(rng: Any, sigma: float) -> float:
    return sigma * math.sqrt(-2.0 * math.log(max(1e-12, 1.0 - rng.random())))


def v_orb(host_kg: float, a_m: float) -> float:
    return math.sqrt(I.G_SI * host_kg / a_m)


def v_esc(mass: float, radius: float) -> float:
    return math.sqrt(2.0 * I.G_SI * mass * I.M_EARTH_KG / (radius * I.R_EARTH_M))


def circularise_gyr(host_kg: float, a_m: float, mass: float, radius: float, icy: bool) -> float:
    """Tidal damping time of eccentricity (Gyr)."""
    m = mass * I.M_EARTH_KG
    n = math.sqrt(I.G_SI * host_kg / a_m ** 3)
    k2 = I.love_number(mass, radius, icy)
    return (4.0 / 63.0) * (I.TIDAL_Q / k2) * (m / host_kg) * (a_m / (radius * I.R_EARTH_M)) ** 5 / n / I.GYR_S


def lock_gyr(host_kg: float, a_m: float, mass: float, radius: float, icy: bool, spin0: float) -> float:
    """Time for the host's tides to brake a world's spin (rad/s) to lock (Gyr)."""
    m, r = mass * I.M_EARTH_KG, radius * I.R_EARTH_M
    k2 = I.love_number(mass, radius, icy)
    return spin0 * a_m ** 6 * INERTIA * m * r * r * I.TIDAL_Q / (3.0 * I.G_SI * host_kg ** 2 * k2 * r ** 5) / I.GYR_S


def eccentricity(e0: float, e_forced: float, tau: float, t: float) -> float:
    if tau <= 0:
        return e_forced
    return e_forced + (e0 - e_forced) * math.exp(-max(0.0, t) / tau)


def system(star_kg: float, worlds: List[Dict[str, Any]], env: float, rng: Any) -> List[Dict[str, Any]]:
    """Orbital elements and spins for a star's worlds (each: a_au, mass, radius, icy), innermost first."""
    big = max(worlds, key=lambda w: w["mass"]) if worlds else None
    ve = v_esc(big["mass"], big["radius"]) if big else 0.0
    out = []
    for n, w in enumerate(worlds):
        a_m = w["a_au"] * I.AU_M
        sigma = STIR * min(1.0, ve / v_orb(star_kg, a_m)) + FLYBY_STIR * env * w["a_au"] ** 1.5
        gaps = []
        for k in (n - 1, n + 1):
            if 0 <= k < len(worlds):
                a1, a2 = sorted((w["a_au"], worlds[k]["a_au"]))
                gaps.append((a2 - a1) / (a2 + a1))
        cap = min(gaps) / 2.0 if gaps else 0.9           # only orbits that never cross survive
        e0 = min(cap, _rayleigh(rng, sigma))
        inc = _rayleigh(rng, sigma / 2.0)
        out.append({"e0": e0, "inc": min(math.pi / 2, inc), "node": 2 * math.pi * rng.random(),
                    "peri": 2 * math.pi * rng.random(), "obliquity": math.acos(2.0 * rng.random() - 1.0),
                    "spin_share": SPIN_SHARE[0] + (SPIN_SHARE[1] - SPIN_SHARE[0]) * rng.random()})
    for n, w in enumerate(worlds):                        # what each neighbour forces (Laplace-Lagrange, leading term)
        f = 0.0
        for k in (n - 1, n + 1):
            if 0 <= k < len(worlds):
                ratio = min(w["a_au"], worlds[k]["a_au"]) / max(w["a_au"], worlds[k]["a_au"])
                f = max(f, 1.25 * ratio * out[k]["e0"])
        out[n]["e_forced"] = min(out[n]["e0"], f) if out[n]["e0"] > 0 else f
    for n, w in enumerate(worlds):
        out[n].update(spin(star_kg, w["a_au"] * I.AU_M, w, out[n]))
    return out


def spin(host_kg: float, a_m: float, w: Dict[str, Any], el: Dict[str, Any]) -> Dict[str, Any]:
    """The world's spin at birth, the time its host takes to lock it, and its eccentricity's damping time."""
    m, r = w["mass"] * I.M_EARTH_KG, w["radius"] * I.R_EARTH_M
    breakup = math.sqrt(I.G_SI * m / r ** 3)
    spin0 = el["spin_share"] * breakup
    return {"spin0": spin0, "lock_gyr": lock_gyr(host_kg, a_m, w["mass"], w["radius"], w.get("icy", False), spin0),
            "tau_e": circularise_gyr(host_kg, a_m, w["mass"], w["radius"], w.get("icy", False))}


def at(host_kg: float, a_m: float, el: Dict[str, Any], t: float) -> Dict[str, Any]:
    """A world's orbit and spin at an age t (Gyr): its eccentricity, whether locked, its day (s) and obliquity."""
    e = eccentricity(el["e0"], el["e_forced"], el["tau_e"], t)
    n = math.sqrt(I.G_SI * host_kg / a_m ** 3)
    locked = t >= el["lock_gyr"]
    if locked:
        w_now, obl = n, 0.0
    else:
        w_now = el["spin0"] - (el["spin0"] - n) * t / max(1e-12, el["lock_gyr"])
        obl = el["obliquity"]
    return {"e": e, "locked": locked, "day_s": 2 * math.pi / max(1e-12, w_now), "year_s": 2 * math.pi / n,
            "obliquity": obl, "inc": el["inc"], "node": el["node"], "peri": el["peri"]}


def moons(giant_mass: float, giant_radius: float, ice_share: float, rng: Any) -> List[Dict[str, Any]]:
    """A giant's regular moons: their masses (a stick broken among a few), radii (rock and ice), orbits in its radii
    (a 2:1 chain outward from the innermost) and the eccentricity each neighbour forces."""
    budget = giant_mass * MOON_SHARE
    count = 1 + int(rng.random() * MOONS_MAX)
    shares, left = [], 1.0
    for _ in range(count - 1):
        s = left * rng.random()
        shares.append(s)
        left -= s
    shares.append(left)
    masses = [budget * s for s in shares]
    a0 = INNER_MOON_RADII[0] * (INNER_MOON_RADII[1] / INNER_MOON_RADII[0]) ** rng.random()
    out = []
    for k, m in enumerate(masses):
        a_r = a0 * RESONANCE_RATIO ** k
        rho = 1.0 / (1.0 - ice_share + ice_share * 5.5)      # ice is ~5.5x less dense than a unit world's mean
        radius = (m * rho) ** (1.0 / 3.0)
        out.append({"mass": m, "radius": radius, "a_radii": a_r, "icy": ice_share > 0.2})
    for k, mn in enumerate(out):
        f = 0.0
        for j in (k - 1, k + 1):
            if 0 <= j < len(out):
                delta = RESONANCE_OFFSET[0] * (RESONANCE_OFFSET[1] / RESONANCE_OFFSET[0]) ** rng.random()
                f = max(f, (out[j]["mass"] / giant_mass) / delta)     # the neighbour's mass over the giant's
        mn["e_forced"] = min(0.1, f)
        mn["obliquity"] = 0.0
    return [m for m in out if m["mass"] >= MOON_MIN]
