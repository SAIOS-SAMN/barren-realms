"""
Xylarium geometry: space as it is - curved - and no longer the flat sheet the engine once laid its galaxy on.

Two curvatures shape every distance and every clock here, one at each end of the scales:

THE UNIVERSE'S. Every universe is closed (creation.big_bang): its space is a 3-sphere of radius R = c / H0 /
sqrt(Omega - 1). A place is a point of that sphere (a unit 4-vector); the distance between two places is the arc
between them, R x the angle - never a straight line through a fourth dimension that is not there. A galaxy's
neighbourhood is laid on the sphere by the exponential map from the home galaxy's point: a step of length d in a
direction u lands at cos(d / R) home + sin(d / R) u. Go far enough in any direction and you come back.

MATTER'S. Mass bends space and slows time near it (general relativity in its weak-field form, exact to first order
in Phi / c^2 for the speeds and depths of a galaxy):

    ds^2 = -(1 + 2 Phi / c^2) c^2 dt^2 + (1 - 2 Phi / c^2) dl^2

  * a clock at rest in a potential well Phi (< 0) runs slow by sqrt(1 + 2 Phi / c^2); one moving at v slower again
    by sqrt(1 - v^2 / c^2): a star's own time, its local clock, against the universe's (docs/CLOCK.md);
  * a ruler laid across the well is longer: proper length is the coordinate length x (1 - Phi / c^2), integrated
    along the way (first order: the straight path and the geodesic agree);
  * light takes longer through the well than through flat space (Shapiro): an extra 2 |Phi| / c^3 per unit length.

The galaxy's potential is a disc's (2 pi G Sigma h ln cosh(z / h), giving every star its vertical oscillation through
the plane), a halo's (V^2 ln r: the flat rotation curve), and the central black hole's (-G M / r). How much any of
it matters is computed, not assumed: across the disc Phi / c^2 is ~1e-6 - a clock at the centre loses about a
second a week against one at the rim - and the universe's curvature is invisible below a few Gpc. The game's
travel, light and clocks are now measured on this geometry all the same: the flat sheet was a projection, and the
projection is now derived from the space instead of standing in for it.
"""

import math
from typing import Any, Dict, List, Optional, Sequence

C_KMS = 299792.458
G_KPC = 4.30091e-6              # G in kpc (km/s)^2 per solar mass
KPC_PER_LY = 1.0 / 3261.56
GYR_PER_KPC_PER_KMS = 0.9778    # 1 kpc / (1 km/s) in Gyr
LIGHT_GYR_PER_KPC = 3261.56e-9  # Gyr light takes to cross a kpc of flat space

# ---------------------------------------------------------------------- the galaxy's matter (Milky Way as data point)
V_HALO_KMS = 220.0              # the flat rotation speed the halo holds (cosmos.V_FLAT_KMS)
R_HALO_KPC = 250.0              # where the halo's potential is taken to vanish (its virial radius)
BH_SUNS = 4.0e6                 # the central black hole (Sgr A*)
DISC_H_KPC = 0.3                # the thin disc's scale height
RHO0_R0 = 0.1e9                 # suns per kpc^3 in the plane at R0 (stars and gas: the Oort limit, 0.1 per pc^3)
SIGMA_Z_10 = 20.0               # km/s: a 10-Gyr-old disc star's vertical speed spread at R0 (age-velocity relation,
                                # ~ age^0.5: Holmberg et al. 2009) - old stars ride further from the plane


def _cosmos():
    from xylarium.kernel import cosmos
    return cosmos


# ---------------------------------------------------------------------- the 3-sphere
def radius_kpc(seed: Any) -> float:
    """The curvature radius of a universe's space (kpc)."""
    from xylarium.kernel import creation
    return creation.big_bang(seed)["curvature_mpc"] * 1000.0


HOME = (1.0, 0.0, 0.0, 0.0)


def embed(local_kpc: Sequence[float], r_kpc: float, origin: Sequence[float] = HOME) -> List[float]:
    """A place a local displacement (x, y, z kpc) from origin, laid on the 3-sphere by the exponential map."""
    d = math.sqrt(sum(c * c for c in local_kpc))
    if d <= 0:
        return list(origin)
    u = [0.0] + [c / d for c in local_kpc]                 # the tangent direction at HOME
    if tuple(origin) != HOME:
        u = _transport(u, origin)
    a = d / r_kpc
    return [math.cos(a) * o + math.sin(a) * v for o, v in zip(origin, u)]


def _transport(u: List[float], origin: Sequence[float]) -> List[float]:
    """Carry a tangent vector at HOME to origin along the great circle between them (parallel transport)."""
    o = list(origin)
    cos_a = max(-1.0, min(1.0, o[0]))
    sin_a = math.sqrt(max(0.0, 1.0 - cos_a * cos_a))
    if sin_a < 1e-15:
        return u
    w = [x / sin_a for x in [0.0] + o[1:]]                  # the direction from HOME toward origin
    uw = sum(a * b for a, b in zip(u, w))
    e0 = [1.0, 0.0, 0.0, 0.0]
    # the component along the great circle turns with it; the rest is carried unchanged
    return [ui + uw * ((cos_a - 1.0) * wi - sin_a * ei) for ui, wi, ei in zip(u, w, e0)]


def arc_kpc(a: Sequence[float], b: Sequence[float], r_kpc: float) -> float:
    """The geodesic distance between two points of the 3-sphere: R x the angle between them."""
    dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))
    # for nearby points the chord is the better-conditioned measure of the angle
    if dot > 0.999999:
        chord = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        return 2.0 * r_kpc * math.asin(min(1.0, chord / 2.0))
    return r_kpc * math.acos(dot)


def local_kpc(seed: Any, a: Sequence[float], b: Sequence[float]) -> float:
    """The arc between two local displacements (kpc from home) once both are laid on the universe's sphere."""
    r = radius_kpc(seed)
    return arc_kpc(embed(a, r), embed(b, r), r)


# ---------------------------------------------------------------------- the galaxy's potential
def surface_density(r_kpc: float) -> float:
    """Suns per kpc^2 of the disc at r: the plane's density x twice its scale height, falling as the disc does."""
    return RHO0_R0 * 2.0 * DISC_H_KPC * _cosmos().density(r_kpc)


def potential(r_kpc: float, z_kpc: float = 0.0) -> float:
    """Phi in (km/s)^2: halo (flat rotation), disc (vertical), central black hole; zero at the halo's edge."""
    rs = math.sqrt(r_kpc * r_kpc + z_kpc * z_kpc)
    halo = V_HALO_KMS ** 2 * (math.log(max(1e-6, rs) / R_HALO_KPC) - 1.0) if rs < R_HALO_KPC else \
        -V_HALO_KMS ** 2 * R_HALO_KPC / rs
    disc = 2.0 * math.pi * G_KPC * surface_density(r_kpc) * DISC_H_KPC * math.log(math.cosh(z_kpc / DISC_H_KPC))
    hole = -G_KPC * BH_SUNS / max(1e-9, rs)
    return halo + disc + hole


def lapse(r_kpc: float, z_kpc: float = 0.0, v_kms: float = 0.0) -> float:
    """d(own time) / d(universal time) for a clock at (r, z) moving at v: gravity and motion both slow it."""
    return math.sqrt(max(0.0, 1.0 + 2.0 * potential(r_kpc, z_kpc) / C_KMS ** 2 - (v_kms / C_KMS) ** 2))


def _cyl(p: Sequence[float]):
    return math.sqrt(p[0] * p[0] + p[1] * p[1]), p[2]


def proper_kpc(a: Sequence[float], b: Sequence[float], samples: int = 16) -> float:
    """Proper length of the path between two galactocentric places (x, y, z kpc): the coordinate length x
    (1 - Phi / c^2), averaged along the way."""
    d = math.dist(a, b)
    if d <= 0:
        return 0.0
    s = 0.0
    for n in range(samples):
        f = (n + 0.5) / samples
        p = [x + (y - x) * f for x, y in zip(a, b)]
        s += 1.0 - potential(*_cyl(p)) / C_KMS ** 2
    return d * s / samples


def light_gyr(a: Sequence[float], b: Sequence[float], samples: int = 16) -> float:
    """Light's travel time between two galactocentric places: proper length over c, plus the Shapiro delay."""
    d = math.dist(a, b)
    if d <= 0:
        return 0.0
    s = 0.0
    for n in range(samples):
        f = (n + 0.5) / samples
        p = [x + (y - x) * f for x, y in zip(a, b)]
        s += 1.0 - 3.0 * potential(*_cyl(p)) / C_KMS ** 2   # (1 - Phi/c^2) length, (1 - 2 Phi/c^2) delay
    return d * s / samples * LIGHT_GYR_PER_KPC


# ---------------------------------------------------------------------- vertical motion through the disc
def vertical_frequency(r_kpc: float) -> float:
    """rad per Gyr: a star's oscillation through the plane, sqrt(4 pi G rho_0) for the local plane density."""
    rho0 = RHO0_R0 * _cosmos().density(r_kpc)
    return math.sqrt(4.0 * math.pi * G_KPC * rho0) / GYR_PER_KPC_PER_KMS


def vertical(r_kpc: float, age_gyr: float, u: float, phase: float) -> Dict[str, float]:
    """A star's vertical orbit: its speed through the plane drawn from the age-velocity relation at its ring (the
    spread scaling as the square root of the plane's surface density, for a fixed scale height), its amplitude
    from the plane's restoring pull, and the mean density it passes through over an oscillation relative to the
    plane's - where comets are shaken loose and supernovae go off (sech^2 profile, averaged over the orbit)."""
    sigma = SIGMA_Z_10 * math.sqrt(max(0.0, age_gyr) / 10.0) * math.sqrt(_cosmos().density(r_kpc))
    vz = sigma * math.sqrt(-2.0 * math.log(max(1e-12, 1.0 - u)))     # |v_z| (Rayleigh on the speed's magnitude)
    nu = vertical_frequency(r_kpc)                                     # rad / Gyr
    amp = vz / max(1e-9, nu * GYR_PER_KPC_PER_KMS)                     # kpc (harmonic, near the plane)
    n, s = 24, 0.0
    for k in range(n):
        z = amp * math.sin(2 * math.pi * (k + 0.5) / n)
        s += 1.0 / math.cosh(z / DISC_H_KPC) ** 2
    return {"amp_kpc": amp, "vz_kms": vz, "period_myr": 2 * math.pi / max(1e-9, nu) * 1000.0,
            "exposure": s / n, "phase": phase,
            "z_kpc": amp * math.sin(phase)}


def z_at(v: Dict[str, Any], t_gyr: float, r_kpc: float) -> float:
    """Height above the plane at a deep-time epoch (closed form)."""
    return v["amp_kpc"] * math.sin(v["phase"] + vertical_frequency(r_kpc) * t_gyr)


# ---------------------------------------------------------------------- within a system
def orbit_xyz(a_au: float, angle: float, inc: float = 0.0, node: float = 0.0) -> List[float]:
    """A place on an inclined orbit (AU): the angle along the orbit from its ascending node, tilted by inc about the
    line of nodes, the node turned by node from the system's reference direction."""
    x, y = a_au * math.cos(angle), a_au * math.sin(angle)
    y, z = y * math.cos(inc), y * math.sin(inc)
    return [x * math.cos(node) - y * math.sin(node), x * math.sin(node) + y * math.cos(node), z]


def separation_au(p1: Sequence[float], p2: Sequence[float], star_suns: float = 1.0) -> float:
    """Proper distance between two places in a system (AU): Schwarzschild's spatial stretch near the star (first
    order, rs / 2r, with rs ~ 2e-8 AU per sun) - immeasurably small, kept so that no distance is flat by fiat."""
    d = math.dist(p1, p2)
    rs = 1.974e-8 * star_suns
    mid = [(x + y) / 2.0 for x, y in zip(p1, p2)]
    r = max(1e-6, math.sqrt(sum(c * c for c in mid)))
    return d * (1.0 + rs / (2.0 * r))
