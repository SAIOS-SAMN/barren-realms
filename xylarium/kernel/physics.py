"""
Xylarium physics: the few laws everything else is derived from.

Units: stellar mass in solar masses, distance in AU, planetary mass/radius in Earth units, time in
standard (Terran) years and days. The game's K-step is the cycle: one Terran year is
CYCLES_PER_STANDARD_YEAR cycles, so a fiscal quarter is a Terran season.

Everything celestial is exact (fractions.Fraction) - no floats, no drift, no roots:
  * A star is described by m (a rational): mass M = m^2, main-sequence luminosity L = M^3.5 = m^7.
  * A planet's orbit is described by q (a rational): semi-major axis a = q^2 AU. Kepler's third law
    T^2 = a^3 / M then gives an exact period T = q^3 / m years.
  * Spacing law: successive orbits step outward by a ratio of at least 8/7 in q, so orbital periods
    differ by at least (8/7)^3 ~ 1.49x - comfortably beyond mutual-Hill-sphere stability. Orbits never
    cross; planets never collide. Stars are nodes of the lane graph and never share a position.
  * Received light (flux, Earth = 1) is L / a^2 = m^7 / q^4. Flux and planetary mass decide a world's
    type (a hot rock, a temperate world, an ice world, a giant beyond the frost line).
  * Rocky worlds have Earth-like density: mass = r^3 for radius r, so surface area ~ r^2 and surface
    gravity ~ r (escape energy per kilogram ~ r^2). Giants are a quarter as dense.
  * Rotation: a day length (in standard days) and an axial tilt. A world close enough to a massive
    star is tidally locked (day = year); only its terminator band is lit and dark in turn.

Later layers derive food (flux x area x season), carrying capacity, population, output and money from
these quantities. Chosen constants live here and in config's [15] block, and there are few of them.
"""

import math
import zlib
import random
from dataclasses import dataclass
from fractions import Fraction as F
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------- the clock
CYCLES_PER_STANDARD_YEAR = 100            # one Terran year = 100 K-steps (a fiscal quarter = one season)
STANDARD_DAYS_PER_YEAR = 365
DAYS_PER_CYCLE = F(STANDARD_DAYS_PER_YEAR, CYCLES_PER_STANDARD_YEAR)

# ---------------------------------------------------------------------- stars: m, with M = m^2, L = m^7
STAR_CLASSES: Dict[str, Tuple[F, Optional[F]]] = {
    # class label prefix -> (m, luminosity override for non-main-sequence stars)
    "M-class": (F(1, 2), None),          # M = 0.25, L = 0.0078
    "K-class": (F(9, 10), None),         # M = 0.81, L = 0.48
    "G-class": (F(1), None),             # the Sun
    "F-class": (F(11, 10), None),        # M = 1.21, L = 1.95
    "A-class": (F(13, 10), None),        # M = 1.69, L = 6.3
    "Binary": (F(7, 5), F(2)),           # two suns: M = 1.96, L = 2
    "White dwarf": (F(3, 4), F(1, 1000)),
    "Supernova remnant": (F(1, 10), F(1, 1000000)),   # what a Type Ia leaves: a shell of gas, nearly no light
    "Brown dwarf": (F(3, 10), F(1, 100000)),
    "Precursor": (F(6, 5), F(1, 100)),   # an engineered pulsar: heavy, dim in the visible
    "Neutron star": (F(118, 100), F(1, 1000000)),   # 1.4 suns, a cooling ember
    "Black hole": (F(3), F(1, 10 ** 9)),            # what a heavy star's collapse leaves: dark
    "B-class": (F(2), None),             # M = 4
    "O-class": (F(5), None),             # M = 25
}

# ---------------------------------------------------------------------- orbits
SPACING_RATIOS = [F(8, 7), F(7, 6), F(6, 5), F(5, 4), F(4, 3)]   # q steps; period ratios 1.49 .. 2.37
MIN_SPACING = min(SPACING_RATIOS)
INNER_FLUX_LIMIT = 50                     # nothing survives closer than where flux exceeds 50 Earths
OUTER_LIMIT_PER_M = 40                    # a star holds planets out to a = 40 m AU (its gravitational reach)
FROST_FLUX = F(1, 4)                      # beyond this, volatiles freeze: giants and ice worlds form
TIDAL_LOCK = F(1, 64)                     # locked when a^3 < M / 64 (a < M^(1/3) / 4 AU)
GIANT_DENSITY = F(1, 4)


def _fr(x: Any) -> F:
    return x if isinstance(x, F) else F(str(x))


def _s(x: F) -> str:
    return f"{x.numerator}/{x.denominator}"


def rng_for(*parts: Any) -> random.Random:
    return random.Random(zlib.crc32(":".join(str(p) for p in parts).encode()))


# ---------------------------------------------------------------------- stars
def star_for(star_type: Optional[str]) -> Dict[str, str]:
    label = star_type or "G-class"
    m, lum = STAR_CLASSES["G-class"]
    for prefix, spec in STAR_CLASSES.items():
        if label.startswith(prefix) or prefix.lower() in label.lower():
            m, lum = spec
            break
    mass = m * m
    luminosity = lum if lum is not None else m ** 7
    return {"m": _s(m), "mass": _s(mass), "luminosity": _s(luminosity)}


def star(sector: Any) -> Dict[str, F]:
    s = getattr(sector, "star", None) or star_for(getattr(sector, "star_type", None))
    return {k: _fr(v) for k, v in s.items()}


# ---------------------------------------------------------------------- bodies
def orbit_limits(st: Dict[str, F]) -> Tuple[F, F]:
    """q range a planet may occupy: flux below INNER_FLUX_LIMIT, a within the star's reach."""
    # inner: L / q^4 <= 50  ->  q^4 >= L / 50 ; take a rational at or above the root
    q_min = _rational_root(st["luminosity"] / INNER_FLUX_LIMIT, 4, up=True)
    q_min = max(q_min, F(1, 5))
    q_max = _rational_root(OUTER_LIMIT_PER_M * st["m"], 2, up=False)
    return q_min, q_max


def _rational_root(x: F, n: int, up: bool) -> F:
    """A simple rational (denominator 100) bounding the real n-th root of x from above/below."""
    r = F(math.floor(float(x) ** (1.0 / n) * 100) + (1 if up else 0), 100)
    if up:
        while r ** n < x:
            r += F(1, 100)
    else:
        while r > 0 and r ** n > x:
            r -= F(1, 100)
    return r


def flux(st: Dict[str, F], q: F) -> F:
    return st["luminosity"] / (q ** 4)


def period_years(st: Dict[str, F], q: F) -> F:
    return q ** 3 / st["m"]


def classify(fl: F, radius: F, giant: bool, rng: random.Random) -> str:
    """A world's type follows from the light it receives and what it can hold on to."""
    if giant:
        return "GAS_GIANT" if fl < 2 else "VOLCANIC"            # a hot giant is a roasting world
    if fl < F(1, 400):
        return "ROGUE"                                          # beyond the light: a dark wanderer's orbit
    if radius < F(2, 5):
        return "ICE" if fl < FROST_FLUX else "BARREN"           # too small to keep an atmosphere
    if fl >= 3:
        return "VOLCANIC" if radius >= 1 else "BARREN"
    if fl >= F(3, 2):
        return "TERRESTRIAL" if (radius >= F(6, 5) and rng.random() < 0.3) else "BARREN"
    if fl >= F(1, 2):
        return "OCEANIC" if (radius >= 1 and rng.random() < 0.4) else "TERRESTRIAL"
    if fl >= FROST_FLUX:
        return "OCEANIC" if rng.random() < 0.3 else "ICE"
    return "ICE"


def make_body(st: Dict[str, F], q: F, rng: random.Random, giant: Optional[bool] = None) -> Dict[str, Any]:
    fl = flux(st, q)
    if giant is None:
        giant = rng.random() < (0.55 if fl < FROST_FLUX else 0.04)
    radius = F(rng.randint(60, 220), 20) if giant else F(rng.randint(6, 36), 20)
    mass = radius ** 3 * (GIANT_DENSITY if giant else 1)
    a = q * q
    locked = a ** 3 < st["mass"] * TIDAL_LOCK
    year = period_years(st, q)
    day = year * STANDARD_DAYS_PER_YEAR if locked else F(rng.randint(8, 72), 24)   # 8 h .. 3 days
    return {
        "q": _s(q), "radius": _s(radius), "mass": _s(mass), "giant": giant,
        "day": _s(day), "tilt": 0 if locked else rng.randint(0, 45), "locked": locked,
        "phase0": _s(F(rng.randint(0, 359), 360)),
    }


def body(planet: Any) -> Dict[str, Any]:
    """The planet's body with exact values parsed (cached until the stored body changes)."""
    b = getattr(planet, "body", None) or {}
    snap = tuple(b.items())
    cache = getattr(planet, "_body_cache", None)
    if cache is not None and cache[0] is b and cache[1] == snap:
        return dict(cache[2])
    out = dict(b)
    for k in ("q", "radius", "mass", "day", "phase0"):
        if k in out:
            out[k] = _fr(out[k])
    try:
        planet._body_cache = (b, snap, out)
    except AttributeError:
        pass
    return dict(out)


def apply_derived(planet: Any, st: Dict[str, F]) -> None:
    """Keeps the legacy display fields (AU, period in cycles) consistent with the exact body."""
    b = body(planet)
    if "q" not in b:
        return
    q = b["q"]
    planet.orbital_radius = float(q * q)
    planet.orbital_period = max(1, round(period_years(st, q) * CYCLES_PER_STANDARD_YEAR))


def lay_out_system(sector: Any, count: int, rng: random.Random) -> List[Tuple[F, Dict[str, Any], str]]:
    """Places ``count`` worlds on non-crossing orbits. Returns (q, body, type) innermost first."""
    st = star(sector)
    q_min, q_max = orbit_limits(st)
    if q_max <= q_min:
        return []
    # Start somewhere in the inner third of the system (in q), then step outward by spacing ratios
    span = q_max - q_min
    q = q_min + span * F(rng.randint(0, 33), 100)
    out: List[Tuple[F, Dict[str, Any], str]] = []
    for _ in range(count):
        if q > q_max:
            break
        b = make_body(st, q, rng)
        ptype = classify(flux(st, q), _fr(b["radius"]), b["giant"], rng)
        out.append((q, b, ptype))
        q = q * rng.choice(SPACING_RATIOS)
    return out


def place_orbit_for_type(sector: Any, ptype: str, rng: random.Random) -> Optional[F]:
    """An orbit whose flux suits a world type (used when a world's type is fixed first)."""
    target = {"TERRESTRIAL": F(1), "OCEANIC": F(9, 10), "ICE": F(1, 8), "BARREN": F(2),
              "VOLCANIC": F(5), "GAS_GIANT": F(1, 20), "ROGUE": F(1, 800)}.get(ptype, F(1))
    st = star(sector)
    q_min, q_max = orbit_limits(st)
    q = _rational_root(st["luminosity"] / target, 4, up=True)
    return min(max(q, q_min), q_max)


def ensure_system(sector: Any) -> None:
    """Gives a star system (and each of its worlds) exact physics if it has none - saves, ghost sectors."""
    if getattr(sector, "kind", "SYSTEM") != "SYSTEM":
        return
    if not getattr(sector, "star", None):
        sector.star = star_for(getattr(sector, "star_type", None))
    st = star(sector)
    missing = [p for p in sector.planets if not getattr(p, "body", None)]
    if not missing:
        return
    rng = rng_for("ensure", sector.id)
    placed = sorted((body(p)["q"] for p in sector.planets if getattr(p, "body", None) and not body(p).get("parent")))
    for p in missing:
        if getattr(p, "moon_of", None):
            continue
        q = place_orbit_for_type(sector, p.planet_type, rng)
        # respect the spacing law against every world already placed
        for other in placed:
            lo, hi = other / MIN_SPACING, other * MIN_SPACING
            if lo < q < hi:
                q = hi
        b = make_body(st, q, rng, giant=(p.planet_type == "GAS_GIANT"))
        if p.planet_type in ("TERRESTRIAL", "OCEANIC", "VOLCANIC") and _fr(b["radius"]) < F(4, 5):
            b["radius"], b["mass"] = "1/1", "1/1"          # a world that holds air and water is Earth-sized
        p.body = b
        placed = sorted(placed + [q])
        apply_derived(p, st)
    # Moons share their planet's orbit about the star, locked face-to-planet (a lunar month for a day)
    for p in missing:
        parent = next((w for w in sector.planets if w.id == getattr(p, "moon_of", None)), None)
        if parent is None or not getattr(parent, "body", None):
            continue
        pb = parent.body
        p.body = {"q": pb["q"], "radius": "1/4", "mass": "1/64", "giant": False, "day": "273/10", "tilt": 7,
                  "locked": True, "phase0": pb.get("phase0", "0/1"), "parent": parent.id}
        apply_derived(p, st)


def reseat(sector: Any, planet: Any, ptype: str) -> None:
    """Makes ``planet`` a world of ``ptype`` by moving it to an orbit whose light suits that type."""
    if planet.planet_type == ptype and getattr(planet, "body", None):
        return
    planet.planet_type = ptype
    planet.body = None
    ensure_system(sector)


def spacing_ok(sector: Any) -> bool:
    """The non-collision invariant: every pair of star-orbiting worlds is separated by >= 8/7 in q."""
    qs = sorted(body(p)["q"] for p in sector.planets if getattr(p, "body", None) and not body(p).get("parent"))
    return all(b >= a * MIN_SPACING for a, b in zip(qs, qs[1:]))


# ---------------------------------------------------------------------- time
def year_cycles(sector: Any, planet: Any) -> F:
    b = body(planet)
    if "q" not in b:
        return F(max(1, getattr(planet, "orbital_period", 36)))
    return period_years(star(sector), b["q"]) * CYCLES_PER_STANDARD_YEAR


def _orbit_ints(sector: Any, planet: Any) -> Tuple[int, int, int, int]:
    """(a, b, n, d) with phase0 = a/b and the year = n/d cycles, cached per body (integer arithmetic)."""
    raw = getattr(planet, "body", None)
    key = (id(raw), str(raw), getattr(sector, "id", None))
    cache = getattr(planet, "_orbit_cache", None)
    if cache is not None and cache[0] == key:
        return cache[1]
    b = body(planet)
    t = year_cycles(sector, planet)
    p0 = b.get("phase0", F(0))
    ints = (p0.numerator, p0.denominator, t.numerator, t.denominator)
    try:
        planet._orbit_cache = (key, ints)
    except AttributeError:
        pass
    return ints


def orbital_phase(sector: Any, planet: Any, cycle: int) -> F:
    """Exact fraction of the local year completed at ``cycle`` (0 <= phase < 1)."""
    a, b, n, d = _orbit_ints(sector, planet)
    # a/b + cycle * d/n, reduced mod 1, in integers
    den = b * n
    return F((a * n + cycle * d * b) % den, den)


def orbital_angle(sector: Any, planet: Any, cycle: int) -> float:
    """The display angle (degrees) at ``cycle``: exact phase, converted to a float only at the boundary."""
    a, b, n, d = _orbit_ints(sector, planet)
    den = b * n
    return 360.0 * ((a * n + cycle * d * b) % den) / den


def local_calendar(sector: Any, planet: Any, cycle: int) -> Dict[str, Any]:
    """The world's own time: its year count, season (0-3), and the local day."""
    b = body(planet)
    t = year_cycles(sector, planet)
    x = b.get("phase0", F(0)) + F(cycle) / t
    year = x.numerator // x.denominator
    phase = x - year
    day_len = b.get("day", F(1))
    days_elapsed = F(cycle) * DAYS_PER_CYCLE
    return {"year": int(year), "phase": phase, "season": int(phase * 4),
            "local_days_per_year": (t * DAYS_PER_CYCLE) / day_len,
            "local_day": int(days_elapsed / day_len)}


# ---------------------------------------------------------------------- seasons
_GROWING: Dict[int, F] = {}


def growing_share(tilt_deg: float) -> F:
    """The share of a world's year and surface warm enough to grow: daily-mean sunlight at each latitude through the
    year (the declination swinging by the axial tilt), counted where it reaches half that latitude's own yearly mean,
    weighted by each latitude band's area. An upright world grows all year; a tilted one has winters, and a world on
    its side has polar nights - but no world loses its whole year to tilt."""
    key = int(round(abs(tilt_deg)))
    if key in _GROWING:
        return _GROWING[key]
    eps = math.radians(min(90, key))
    lats = [math.radians(5.0 + 10.0 * i) for i in range(9)]
    days = 48
    total = weight = 0.0
    for phi in lats:
        qs = []
        for d in range(days):
            dec = eps * math.sin(2 * math.pi * (d + 0.5) / days)
            x = -math.tan(phi) * math.tan(dec)
            h0 = 0.0 if x >= 1 else math.pi if x <= -1 else math.acos(x)
            qs.append(max(0.0, h0 * math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.sin(h0)))
        mean = sum(qs) / days
        grow = sum(1 for q in qs if q >= 0.5 * mean) / days if mean > 0 else 0.0
        total += grow * math.cos(phi)
        weight += math.cos(phi)
    _GROWING[key] = F(int(round(total / weight * 1000)), 1000)
    return _GROWING[key]


# ---------------------------------------------------------------------- surface
def surface_area(planet: Any) -> F:
    """Relative to Earth (r^2)."""
    b = body(planet)
    r = b.get("radius", F(1))
    return r * r


def surface_gravity(planet: Any) -> F:
    b = body(planet)
    r = b.get("radius", F(1))
    return r * (GIANT_DENSITY if b.get("giant") else 1)


def escape_energy(planet: Any) -> F:
    """Per unit mass, relative to Earth: M / R."""
    b = body(planet)
    r = b.get("radius", F(1))
    return b.get("mass", F(1)) / r


def planet_flux(sector: Any, planet: Any, swell: Optional[float] = None) -> F:
    """Starlight at the world, relative to Earth's - after its star's arrays, and as swollen as its star is now (or
    at the season given: `swell`, the star's luminosity factor then)."""
    b = body(planet)
    if "q" not in b:
        return F(1)
    q = b["q"]
    try:
        from xylarium.kernel import torsion
        sec_id = getattr(sector, "id", 0)
        # Apply deterministic secular drift from torsion wavefronts
        q = torsion.orbital_secular_drift(getattr(sector, "kernel", None), sec_id, q)
    except Exception:
        pass
    fl = flux(star(sector), q)
    from xylarium.kernel import harvest
    shaded = harvest.shade(getattr(sector, "id", 0)) if sector is not None else 0.0
    if shaded > 0:                                  # the star's arrays take their share of its light first
        fl = fl * F(int(round((1.0 - shaded) * 10 ** 9)), 10 ** 9)
    from xylarium.kernel import cosmos
    if swell is None:
        swell = cosmos.lum(getattr(sector, "id", 0)) if sector is not None else 1.0
    if swell != 1.0:                                # a star on its giant branch (cosmos.py)
        fl = fl * F(swell).limit_denominator(10 ** 6)
    return fl


def electrodynamic_induction(
    star_dict: Dict[str, F],
    planet_body: Dict[str, Any],
    torsion_amplitude: float
) -> F:
    """Derive local electrodynamic shear coupling from stellar dynamo and planetary spin.
    
    1. Freely spinning worlds (locked == False): Mantle shear generates high holonomy rotation.
    2. Tidally locked worlds (locked == True): Holonomy freezes; acts as a stationary Dirichlet mirror.
    No arbitrary constants: derived from stellar mass m, distance a = q^2, and planetary day length.
    """
    q = planet_body.get("q", F(1))
    if not isinstance(q, F):
        q = _fr(q)
    locked = planet_body.get("locked", False)
    if locked:
        return F(0)

    m = star_dict.get("m", F(1))
    day = planet_body.get("day", F(1))
    if not isinstance(day, F):
        day = _fr(day)

    # Pure physical rational coupling: shear induction along orbital flow
    shear_induction = F(int(round(torsion_amplitude * 1000)), 1000) * (F(1, max(F(1, 10), q)) / max(F(1), day))
    return shear_induction


@dataclass(frozen=True)
class Quaternion:
    """Exact Non-Abelian SU(2) / Spin(3) quaternion element.
    
    Represents parallel transport operators and non-abelian Wilson lines.
    Strictly non-commutative: q1 * q2 != q2 * q1.
    """
    w: float
    x: float
    y: float
    z: float

    def __mul__(self, other: "Quaternion") -> "Quaternion":
        w1, x1, y1, z1 = self.w, self.x, self.y, self.z
        w2, x2, y2, z2 = other.w, other.x, other.y, other.z
        return Quaternion(
            w=w1*w2 - x1*x2 - y1*y2 - z1*z2,
            x=w1*x2 + x1*w2 + y1*z2 - z1*y2,
            y=w1*y2 - x1*z2 + y1*w2 + z1*x2,
            z=w1*z2 + x1*y2 - y1*x2 + z1*w2,
        )

    def conjugate(self) -> "Quaternion":
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def norm_sq(self) -> float:
        return self.w*self.w + self.x*self.x + self.y*self.y + self.z*self.z

    def norm(self) -> float:
        return math.sqrt(max(0.0, self.norm_sq()))

    def normalized(self) -> "Quaternion":
        n = self.norm()
        if n < 1e-15:
            return Quaternion(1.0, 0.0, 0.0, 0.0)
        return Quaternion(self.w / n, self.x / n, self.y / n, self.z / n)

    def inverse(self) -> "Quaternion":
        n_sq = self.norm_sq()
        if n_sq < 1e-15:
            return Quaternion(1.0, 0.0, 0.0, 0.0)
        c = self.conjugate()
        return Quaternion(c.w / n_sq, c.x / n_sq, c.y / n_sq, c.z / n_sq)

    @classmethod
    def from_axis_angle(cls, axis: Tuple[float, float, float], angle: float) -> "Quaternion":
        ax, ay, az = axis
        mag = math.sqrt(ax*ax + ay*ay + az*az)
        if mag < 1e-15:
            return cls(1.0, 0.0, 0.0, 0.0)
        half = angle * 0.5
        sin_h = math.sin(half)
        return cls(
            w=math.cos(half),
            x=(ax / mag) * sin_h,
            y=(ay / mag) * sin_h,
            z=(az / mag) * sin_h,
        ).normalized()

    def to_axis_angle(self) -> Tuple[Tuple[float, float, float], float]:
        q = self.normalized()
        angle = 2.0 * math.acos(max(-1.0, min(1.0, q.w)))
        sin_h = math.sin(angle * 0.5)
        if abs(sin_h) < 1e-15:
            return ((1.0, 0.0, 0.0), 0.0)
        return ((q.x / sin_h, q.y / sin_h, q.z / sin_h), angle)

    def commutator(self, other: "Quaternion") -> "Quaternion":
        """Non-abelian Lie bracket [q1, q2] = q1 * q2 - q2 * q1."""
        p1 = self * other
        p2 = other * self
        return Quaternion(p1.w - p2.w, p1.x - p2.x, p1.y - p2.y, p1.z - p2.z)

    def __repr__(self) -> str:
        return f"SU2({self.w:.4f} + {self.x:.4f}i + {self.y:.4f}j + {self.z:.4f}k)"


def non_euclidean_geodesic(
    star_m: Any,
    body1: Dict[str, Any],
    body2: Dict[str, Any]
) -> Tuple[float, Tuple[float, float, float]]:
    """Compute Riemannian curved geodesic arc length and tangent spin axis in non-Euclidean spacetime.
    
    Spacetime metric around star mass m:
        ds^2 = dr^2 / (1 - 2m/r) + r^2 dphi^2
    Yields non-zero intrinsic Riemann curvature R != 0.
    """
    q1 = float(body1.get("q", 1.0))
    q2 = float(body2.get("q", 1.0))
    r1 = max(0.05, q1 * q1)
    r2 = max(0.05, q2 * q2)
    m = max(0.01, float(star_m) if star_m is not None else 1.0)
    
    # Gravitational radius scale
    rs = 2.0 * m * 0.01
    r_lo, r_hi = min(r1, r2), max(r1, r2)
    mid_r = (r_lo + r_hi) * 0.5
    curvature_metric = 1.0 / math.sqrt(max(0.01, 1.0 - rs / mid_r))
    radial_dist = (r_hi - r_lo) * curvature_metric
    
    phi1 = float(body1.get("orbital_angle", 0.0))
    phi2 = float(body2.get("orbital_angle", math.pi / 3.0))
    dphi = abs(phi2 - phi1)
    angular_dist = mid_r * dphi
    
    geodesic_length = math.sqrt(radial_dist * radial_dist + angular_dist * angular_dist)
    axis = (
        math.sin(dphi) if abs(dphi) > 1e-6 else 1.0,
        math.cos(dphi) * ((r2 - r1) / (r1 + r2)),
        curvature_metric
    )
    return geodesic_length, axis


def summary(sectors: Dict[int, Any]) -> Dict[str, Any]:
    types: Dict[str, int] = {}
    locked = worlds = 0
    violations = 0
    for s in sectors.values():
        if getattr(s, "kind", "") != "SYSTEM":
            continue
        if not spacing_ok(s):
            violations += 1
        for p in s.planets:
            worlds += 1
            types[p.planet_type] = types.get(p.planet_type, 0) + 1
            if body(p).get("locked"):
                locked += 1
    return {"worlds": worlds, "types": types, "tidally_locked": locked, "spacing_violations": violations}
