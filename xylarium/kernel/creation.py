"""
Xylarium creation: everything the Big Bang fixes, as a pure function of the universe's seed.

Nothing here reads the map, the clock or who has witnessed what. Each cell of the galaxy is created by a function
of the seed and the cell's own coordinates, so what is found in a region is the same whoever finds it, whenever,
in whatever order; and the minds that will arise are computed from the very worlds those cells hold.

THE BIG BANG. Each universe draws its initial conditions once, about the measured values (Planck 2018):

  sigma8      the amplitude of the matter fluctuations (0.811). Lumpier matter collapses sooner: a structure
              forms when its linear overdensity, growing as t^(2/3) in the matter era, reaches 1.686 - so the
              epochs of first stars and of the disc's assembly scale as (0.811 / sigma8)^1.5.
  f_b         the baryon fraction (Omega_b / Omega_m, 0.157): the share of matter that can become stars. The
              stars a region holds - and the supernovae that sterilise its worlds - scale with it.
  Omega - 1   the curvature. Every universe here is closed (a 3-sphere: go far enough and you come back), its
              curvature drawn about the measured flatness (|Omega_k| < 0.002); its radius is c / H0 / sqrt(Omega - 1).

How lively a universe is - how soon and how many minds arise - is the outcome of these, not a setting. The pace
(cosmos.PACES) is only its tempo: how much deep time a clock year stands for.

THE EXPANSION is one law for every universe, fixed in time (flat Lambda-CDM with the measured H0 and Omega_m;
the curvature is too slight to change it): a(t) = (Omega_m / Omega_L)^(1/3) sinh^(2/3)(1.5 sqrt(Omega_L) H0 t).
Space expands whether or not anyone watches; what grows with watching is the charted map.

A CELL'S STARS. A 0.5 kpc cell holds millions of stars; its 40 sectors are the ones that matter to the game, each a
sample volume. A sector holds a star with the Poisson chance 1 - exp(-n), n rising with the disc's stellar density
(n at R0 is the measured share of systems in the settled galaxy, 0.28). Its star's birth is drawn from the ring's
star-formation history: gas falls in on the inside-out timescale tau(r) = 1.033 r - 1.267 Gyr (Chiappini, Matteucci
& Romano 2001) and forms stars as it arrives - an exponential after the first stars - so the core is born at once
and the rim is still making stars long after today: systems emerge over deep time, each on its own date, fixed now.
Its mass is drawn from Salpeter's IMF - each star its own, its light from its own mass (L = M^3.5), not its
class's; a third have a companion (Raghavan et al. 2010), its mass ratio drawn flat, the pair's light added. Its
planets are what their orbits gathered of the disc's elements (worlds.form): rock and metal everywhere, each ice beyond
its own line, grown to the isolation mass and by giant impacts, wrapped in gas where a core passed the critical mass
before the disc dispersed - so giants follow the star's metals as they are observed to (Fischer & Valenti 2005). A star is born with
the metals its ring had made by then (the age-metallicity relation: the share of the ring's stars already formed,
over today's share), and its worlds' deposits carry them; hydrogen and helium are the Big Bang's own.

MINDS. Every world of every system in the galaxy that can feed a viable people (Franklin's 500, as foragers on its
living area through its seasons) is a candidate, for every biology that can live on it, and each biology has its
own needs:

  metals      the share of its chemistry built of elements stars make: carbon-and-water life and lattice minds
              need rocky worlds (1); ice-dwellers need oxygen, which the first massive stars made almost at once
              (1/2); minds of the dark run on radiogenic heat - uranium, the heaviest (1); plasmic minds are
              hydrogen and helium, the Big Bang's own, and need none (0): they can wake first, near the core.
  molecular   how much of its chemistry ionising radiation breaks - the supernova sterilisation hazard scales
              with it: complex molecules (1), shielded under ice or bound in lattices (1/2), plasma (0).
  window      its star's main-sequence life (10 Gyr x M^-2.5); a rogue world's dark biology waits on no star.

Each biology passes Carter's hard steps (4; Watson 2008) on its own initial conditions - each an exponential wait of mean
10 Gyr / (fit x metals^need) - after the crust settles; the first to finish (inside the window, unsterilised) is the
world's mind. The expectation of all of it is the audit curve.
"""

import bisect
import json
import math
import os
import random
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------- the Big Bang (measured values as rulers)
SIGMA8 = 0.811                  # Planck 2018
F_BARYON = 0.157                # Omega_b / Omega_m, Planck 2018
OMEGA_M = 0.311                 # matter density today (Planck 2018)
H0_KMS_MPC = 67.7               # Hubble constant (Planck 2018)
FLATNESS = 0.002                # |Omega_k| allowed by measurement: the spread of the curvature drawn
SPREAD_DEX = 0.1                # each universe's sigma8 and f_b are drawn this many dex about the measured
C_KMS = 299792.458
KM_S_MPC_PER_GYR = 1.0227e-3    # 1 km/s/Mpc in 1/Gyr
FIRST_STARS_GYR = 0.3           # in our universe: the oldest stars measured are ~13.5 Gyr old
TODAY_GYR = 13.8                # our universe's age: the epoch today's measurements were made at (a ruler)
COLLAPSE = 1.5                  # t_collapse ~ sigma8^-1.5 (linear growth ~ t^(2/3) to delta_c = 1.686)

# ---------------------------------------------------------------------- stars and their worlds
SLOTS = 40                      # sectors per cell
SYSTEMS_SHARE_R0 = 0.28         # share of sectors holding a star at R0 (the settled galaxy, measured: a ruler)
IMF_SLOPE = -1.35               # Salpeter (1955), dN/dlogM ~ M^-1.35 - the slope above Kroupa's break
IMF_MIN, IMF_MAX = 0.08, 60.0   # solar masses: the hydrogen-burning limit to the heaviest stars common in a disc
KROUPA_LOW = 1.3                # Kroupa (2001): dN/dM ~ M^-1.3 below the break, M^-2.3 above
KROUPA_HIGH = 2.3
KROUPA_BREAK = 0.5              # solar masses, at solar metallicity
CLOUD_K = 10.0                  # K: a star-forming cloud's temperature where the background does not hold it up
JEANS_Z = 0.3                   # the break rises as metals fall: metal-poor gas cools less, is hotter, and collapses
                                # into heavier stars (Jeans mass ~ T^1.5; declared exponent)
BINARY_SHARE = 1.0 / 3.0        # Raghavan et al. 2010
CLASSES = [(0.45, "M-class red dwarf"), (0.9, "K-class orange dwarf"), (1.1, "G-class yellow dwarf"),
           (1.43, "F-class white star"), (2.1, "A-class blue-white star"), (16.0, "B-class blue star"),
           (float("inf"), "O-class blue giant")]       # names by mass; each star keeps its own mass and light
PRIMORDIAL = ("H", "He-3")      # made in the Big Bang: no gradient of enrichment

BELT_INNER = (0.40, 0.63)       # a giant's resonances keep a zone inside its orbit from gathering into a planet: the
                                # main belt's span over Jupiter's orbit (2.1-3.3 / 5.2 AU)
BELT_OUTER = (1.0, 1.6)         # beyond the outermost world, the disc's edge never gathered (the Kuiper belt's 30-48 AU)
DEPLETION_INNER = 4.0e-4        # what a giant's resonances leave of a belt's primordial solids (the main belt: ~5e-4
                                # Earth masses of an MMSN's ~1.2; Petit et al. 2001 - declared)
DEPLETION_OUTER = 1.0e-2        # what migration and scattering leave of an outer belt (declared, the Kuiper belt's)
COMET_SHARE = 0.05              # of the solids a giant scatters, the share flung out to a star's comet cloud (declared)
UNITS_PER_EARTH_MASS = 2.0e6    # mining units in an Earth mass of rock (a ruler: a main belt holds ~1,000)


def _disc_mass(L: Any, slot: Dict[str, Any], z: float, a1: float, a2: float) -> float:
    """Solids the disc held between a1 and a2 AU (Earth masses): Sigma ~ a^-3/2 normalised as worlds.form does."""
    from xylarium.kernel import worlds as W
    s = W.star_of(slot["spec"], L)
    sigma1 = W.MMSN_ROCK * max(0.0, z) * s["mass"]
    return 4.0 * math.pi * sigma1 * (1.496e13 ** 2) * (math.sqrt(a2) - math.sqrt(a1)) / 5.972e27


def _composition(L: Any, slot: Dict[str, Any], r: float, a_mid: float, z: float) -> Tuple[str, Dict[str, float]]:
    """What a belt is made of: the solids that condensed where it formed - metal and silicate everywhere, each ice
    beyond its own line (worlds.condensed); the heaviest elements as the galaxy spread them (cosmos.abundance)."""
    from xylarium.kernel import worlds as W
    s = W.star_of(slot["spec"], L)
    t_form = W.T_UNIT * (s["lum"] / max(1e-6, a_mid) ** 2) ** 0.25
    ices = W.condensed(t_form, L)
    ice = sum(ices.values())
    rock = 1.0 / (1.0 + ice)
    metal, silicate = W.SOLIDS["core"] * rock, (1.0 - W.SOLIDS["core"]) * rock
    cos = _disc()
    out = {"Fe": metal * 0.9, "Ni": metal * 0.08, "Pt": metal * 0.002 * cos.abundance("Pt", r),
           "Si": silicate * 0.5, "ORE": silicate * 0.48, "Ti": silicate * 0.02 * cos.abundance("Ti", r)}
    carbon = sum(ices.get(sp, 0.0) for sp in ("CO2", "CO", "CH4")) / (1.0 + ice)
    if ices.get("H2O"):
        out["H2O"] = ices["H2O"] / (1.0 + ice)
    if carbon:
        out["C"] = carbon
    nitro = sum(ices.get(sp, 0.0) for sp in ("NH3", "N2")) / (1.0 + ice)
    if nitro:
        out["cryogenite"] = nitro
    total = sum(out.values())
    out = {k2: round(v / total, 4) for k2, v in out.items() if v / total >= 0.0005}
    kind = ("ICE" if out.get("H2O", 0) >= 0.3 else "CARBONACEOUS" if out.get("C", 0) >= 0.1 else
            "METALLIC" if out.get("Fe", 0) + out.get("Ni", 0) >= 0.4 else "SILICATE")
    return kind, out


def _belts(L: Any, slot: Dict[str, Any], r: float, z: float) -> Tuple[List[Tuple[str, int, Dict[str, float]]],
                                                                    Dict[str, float]]:
    """A system's belts: the disc's solids that never became worlds - inside a giant's orbit where its resonances
    stirred them too fast to gather (and cleared most), and beyond the outermost world where the disc thinned out -
    each made of what condensed where it lay; and its comet cloud, what its giants flung outward, kept as the
    neighbourhood's passing stars allow. A system without giants has no inner belt; one without worlds, none."""
    from fractions import Fraction
    planets = [w for w in slot.get("worlds", []) if "host" not in w]
    if not planets:
        return [], {}
    orbit = [(float(Fraction(str(w["body"]["q"]))) ** 2, bool(w["body"].get("giant")),
              float(Fraction(str(w["body"]["mass"])))) for w in planets]
    belts = []
    giants = [o for o in orbit if o[1]]
    if giants:
        a_g = min(a for a, g, _ in giants)
        lo, hi = a_g * BELT_INNER[0], a_g * BELT_INNER[1]
        if not any(lo <= a <= hi for a, _, _ in orbit):            # no world took that ground
            mass = _disc_mass(L, slot, z, lo, hi) * DEPLETION_INNER
            kind, comp = _composition(L, slot, r, (lo + hi) / 2, z)
            belts.append((kind, mass, comp))
    a_out = max(a for a, _, _ in orbit)
    lo, hi = a_out * BELT_OUTER[0], a_out * BELT_OUTER[1]
    kind, comp = _composition(L, slot, r, (lo + hi) / 2, z)
    belts.append((kind, _disc_mass(L, slot, z, lo, hi) * DEPLETION_OUTER, comp))
    out = [(kind, int(round(m * UNITS_PER_EARTH_MASS)), comp) for kind, m, comp in belts
           if m * UNITS_PER_EARTH_MASS >= 50]
    comets = {}
    if giants:
        scattered = sum(m for _, _, m in giants) * 0.1                 # the solids around a giant's feeding zone
        kept = math.exp(-_disc().density(r) * float((slot.get("vertical") or {}).get("exposure", 1.0)))
        _, cc = _composition(L, slot, r, 30.0 * max(1.0, a_out), z)
        comets = {"mass_earth": round(scattered * COMET_SHARE * kept, 5), "composition": cc}
    return out, comets


# ---------------------------------------------------------------------- minds (life.py holds life's own laws)
SUN_MS_GYR = 10.0               # main-sequence life of a solar-mass star; ~ M^-2.5
CRUST_GYR = 0.6                 # a rocky world's crust settles and its bombardment ends
HORIZON_GYR = 30.0              # deep time the schedule looks ahead to
CURVE_STEP = 0.25               # Gyr between points of the expectation curve
SETTLED_GYR = 3.0               # a world's chemistry is read once its crust, air and seas have settled (declared)
VIABLE = 500                    # Franklin's 50/500 rule: the number that keeps a people's evolutionary potential

_CACHE: Dict[Tuple[int, int], Dict[str, Any]] = {}       # (seed, cell) -> the cell; (seed,) -> the schedule


def origin(seed: Any) -> Any:
    """The part of a creation key its initial conditions are drawn from: the seed and its kind of Big Bang, not its
    laws - the same universe rebuilt under other laws starts from the same initial conditions (fundamental.py)."""
    parts = str(seed).split(":")
    if len(parts) <= 2:
        return seed
    return int(parts[0]) if parts[1] in ("", "measured") and parts[0].lstrip("-").isdigit() else ":".join(parts[:2])


def _rng(seed: Any, *parts: Any) -> random.Random:
    from xylarium.kernel import scheduler
    return random.Random(scheduler.stream(SimpleNamespace(seed=origin(seed)), *parts))


# ---------------------------------------------------------------------- the Big Bang
UNIVERSES = {                   # the kind of Big Bang chosen at genesis: centres the seed's draw is made about
    "measured": {"sigma8": 1.0, "f_baryon": 1.0},      # about our own universe's (Planck 2018)
    "lush": {"sigma8": 1.3, "f_baryon": 1.5},          # lumpier and richer in baryons: stars sooner, more of them, and
                                                       # more metals made early - a universe more abundant in life
}


def universe(kernel: Any) -> Any:
    """The creation key of a kernel's universe: its seed, the kind of Big Bang chosen at its genesis, and the laws
    its progenitors wrote it under ('measured:alpha=1.01' - fundamental.py)."""
    kind = ((getattr(kernel, "state", None) or {}).get("genesis") or {}).get("universe") or "measured"
    return kernel.seed if kind == "measured" else f"{kernel.seed}:{kind}"


def laws(seed: Any) -> Any:
    from xylarium.kernel import fundamental
    return fundamental.of(seed)


def big_bang(seed: Any) -> Dict[str, float]:
    """This universe's initial conditions and what follows from them (seed may carry its kind: '7:lush')."""
    key = ("bb", seed)
    if key in _CACHE:
        return _CACHE[key]
    parts = str(seed).split(":")
    kind = UNIVERSES.get(parts[1] if len(parts) > 1 and parts[1] else "measured", UNIVERSES["measured"])
    rng = _rng(seed, "big bang")
    s8 = SIGMA8 * kind["sigma8"] * 10.0 ** rng.gauss(0.0, SPREAD_DEX)
    fb = F_BARYON * kind["f_baryon"] * 10.0 ** rng.gauss(0.0, SPREAD_DEX)
    closed = abs(rng.gauss(0.0, FLATNESS)) + FLATNESS / 20.0             # Omega - 1 > 0: a 3-sphere
    out = {"sigma8": round(s8, 4), "f_baryon": round(fb, 4), "omega_minus_1": round(closed, 6),
           "assembly": round((SIGMA8 / s8) ** COLLAPSE, 4),               # epochs of formation, over ours
           "stars": round(fb / F_BARYON, 4),                              # stars per volume, over ours
           "curvature_mpc": round(C_KMS / H0_KMS_MPC / math.sqrt(closed), 1)}
    _CACHE[key] = out
    return out


def first_stars(seed: int) -> float:
    return FIRST_STARS_GYR * big_bang(seed)["assembly"]


# ---------------------------------------------------------------------- the expansion (one law, fixed in time)
def _h0() -> float:
    return H0_KMS_MPC * KM_S_MPC_PER_GYR


def scale_factor(t_gyr: float) -> float:
    """a(t), 1 today in our universe: flat Lambda-CDM with the measured H0 and Omega_m."""
    ol = 1.0 - OMEGA_M
    return (OMEGA_M / ol) ** (1.0 / 3.0) * math.sinh(1.5 * math.sqrt(ol) * _h0() * max(1e-9, t_gyr)) ** (2.0 / 3.0)


def hubble(t_gyr: float) -> float:
    """H(t) in km/s/Mpc."""
    a = scale_factor(t_gyr)
    return H0_KMS_MPC * math.sqrt(OMEGA_M / a ** 3 + (1.0 - OMEGA_M))


def comoving_light_mpc(t_emit: float, t_obs: float, steps: int = 400) -> float:
    """The comoving distance light covers between two epochs: c / a(t) dt, integrated."""
    if t_obs <= t_emit:
        return 0.0
    h = (t_obs - t_emit) / steps
    c_mpc_per_gyr = C_KMS * 1.0227e-3                    # c in Mpc per Gyr (306.6)
    s = 0.0
    for n in range(steps):
        s += h / scale_factor(t_emit + (n + 0.5) * h)
    return c_mpc_per_gyr * s


# ---------------------------------------------------------------------- the disc's rulers (cosmos's)
def _disc():
    from xylarium.kernel import cosmos
    return cosmos


def infall_gyr(seed: int, r: float) -> float:
    """The ring's star-formation timescale: Chiappini's infall, scaled by this universe's assembly."""
    return max(FIRST_STARS_GYR, 1.033 * r - 1.267) * big_bang(seed)["assembly"]


def formed_share(seed: int, r: float, t: float) -> float:
    """The share of the ring's stars formed by epoch t."""
    t1 = first_stars(seed)
    return 0.0 if t <= t1 else 1.0 - math.exp(-(t - t1) / infall_gyr(seed, r))


def _formed_share_ours(r: float, t: float) -> float:
    return 0.0 if t <= FIRST_STARS_GYR else 1.0 - math.exp(-(t - FIRST_STARS_GYR) / max(FIRST_STARS_GYR,
                                                                                           1.033 * r - 1.267))


def metals_at(seed: int, r: float, t: float) -> float:
    """Metallicity (solar = 1) of gas at radius r and epoch t: today's measured gradient, scaled by the share of the
    ring's stars made by then over the share made by today in ours (the age-metallicity relation)."""
    today = _formed_share_ours(r, TODAY_GYR)
    # more baryons, more stars, more of the gas processed into metals (declared: metals scale with the stars made)
    return _disc().metals(r) * formed_share(seed, r, t) / max(1e-9, today) * big_bang(seed)["stars"]


# ---------------------------------------------------------------------- a cell
def luminosity(mass: float, laws: Any = None) -> float:
    """Main-sequence light from mass (the measured piecewise relation, in its universe's stellar scales -
    fundamental.py): faint and slow-burning below half a sun, steepest around a sun, flattening toward the
    Eddington limit for the heaviest."""
    if laws is not None and not laws.ours:
        return laws.star_lum * luminosity(mass / laws.star_mass)
    if mass < 0.43:
        return 0.23 * mass ** 2.3
    if mass < 2.0:
        return mass ** 4.0
    if mass < 55.0:
        return 1.4 * mass ** 3.5
    return 32000.0 * mass


def cloud_k(r: Optional[float] = None, born: Optional[float] = None, laws: Any = None) -> float:
    """A star-forming cloud's temperature: its dust is held at what the starlight around it gives (T ~ U^(1/6) for
    dust whose emissivity rises as frequency squared), and never colder than the cosmic background, 2.725 K x (1 + z):
    near the crowded centre and in the young universe, clouds are warmer. CLOUD_K at R0 today is the ruler, its
    chemistry's cooling scaled with the laws."""
    t = CLOUD_K * (laws.chem if laws is not None else 1.0)
    if r is not None:
        t *= _disc().density(r) ** (1.0 / 6.0)
    if born is not None:
        t = max(t, 2.725 / max(1e-3, scale_factor(born)))
    return t


def imf(u: float, z: float, born: Optional[float] = None, laws: Any = None, r: Optional[float] = None) -> float:
    """A star's mass from Kroupa's two slopes, the break at the Jeans mass of its cloud: heavier in metal-poor gas
    (it cools less), in warm clouds (~ T^1.5) - near the centre, where starlight crowds, and in the young universe,
    whose background light no cloud is colder than - so the early stars and the core's were heavier and hotter
    (inverse transform). The hydrogen-burning limit, the break and the heaviest stars move with the laws."""
    jeans = laws.jeans if laws is not None else 1.0
    chem = laws.chem if laws is not None else 1.0
    mb = KROUPA_BREAK * jeans * max(z, 1e-3) ** -JEANS_Z
    if born is not None or r is not None:
        mb *= (cloud_k(r, born, laws) / (CLOUD_K * chem)) ** 1.5
    lo = IMF_MIN * (laws.star_min if laws is not None else 1.0)
    hi = IMF_MAX * (laws.star_mass if laws is not None else 1.0)
    mb = min(max(mb, lo * 1.01), hi * 0.99)
    a1, a2 = 1.0 - KROUPA_LOW, 1.0 - KROUPA_HIGH
    w1 = (mb ** a1 - lo ** a1) / a1                      # mass function continuous at the break
    w2 = mb ** (KROUPA_HIGH - KROUPA_LOW) * (hi ** a2 - mb ** a2) / a2
    x = u * (w1 + w2)
    if x < w1:
        return (lo ** a1 + a1 * x) ** (1.0 / a1)
    return (mb ** a2 + a2 * (x - w1) / mb ** (KROUPA_HIGH - KROUPA_LOW)) ** (1.0 / a2)


def _spec(mass: float, companion: float = 0.0, laws: Any = None) -> Dict[str, str]:
    """A star's exact physics from its own mass (not its class's): m = sqrt(M) to a hundredth (orbits), its light
    from the mass-luminosity relation; a companion adds its mass and its own light."""
    from fractions import Fraction
    m1 = Fraction(max(1, round(math.sqrt(mass) * 100)), 100)
    total, lum = m1 * m1, Fraction(luminosity(float(m1 * m1), laws)).limit_denominator(10 ** 8)
    if companion > 0:
        m2 = Fraction(max(1, round(math.sqrt(companion) * 100)), 100)
        total, lum = total + m2 * m2, lum + Fraction(luminosity(float(m2 * m2), laws)).limit_denominator(10 ** 8)
    m = Fraction(max(1, round(math.sqrt(float(total)) * 100)), 100)
    lum = lum.limit_denominator(10 ** 6)
    return {"m": f"{m.numerator}/{m.denominator}", "mass": f"{total.numerator}/{total.denominator}",
            "luminosity": f"{lum.numerator}/{lum.denominator}"}


def _star(mass: float, binary: bool, laws: Any = None) -> str:
    if binary:
        return "Binary pair"
    mass = mass / (laws.star_mass if laws is not None else 1.0)     # a class is a share of its universe's star scale
    for edge, label in CLASSES:
        if mass < edge:
            return label
    return CLASSES[-1][1]


def cell(seed: int, i: int, j: int) -> List[Dict[str, Any]]:
    """The cell's SLOTS sample volumes, as the Big Bang made them: a star or none, its birth, its worlds."""
    key = (seed, i, j)
    if key in _CACHE:
        return _CACHE[key]
    from xylarium.config import BELT_CHANCE, BELT_RESERVE_RANGE, BELT_TYPES, SYSTEM_PLANETS
    from xylarium.kernel import physics
    from xylarium.kernel.universe import _deposits_for
    cosmos = _disc()
    bb = big_bang(seed)
    L = laws(seed)
    n0 = -math.log(1.0 - SYSTEMS_SHARE_R0)
    out = []
    for k in range(SLOTS):
        rng = _rng(seed, "creation", i, j, k)
        r = cosmos.ring_radius(i) + (rng.random() - 0.5) * cosmos.CELL_KPC * 0.4
        theta0 = cosmos.cell_theta(i, j) + (rng.random() - 0.5) * 2 * math.pi / cosmos.slots(i) * 0.4
        names = (rng.randrange(8), rng.randrange(8))
        slot: Dict[str, Any] = {"k": k, "r": round(r, 4), "theta0": round(theta0, 6), "names": names}
        if rng.random() >= 1.0 - math.exp(-n0 * cosmos.density(r) * bb["stars"]):
            # the space between stars: its rock was gathered by the stars that formed (its initial conditions are drawn as they
            # were, so every star's own draws stay where they were)
            if rng.random() < BELT_CHANCE:
                rng.choice(sorted(BELT_TYPES)), rng.randint(*BELT_RESERVE_RANGE)
                if rng.random() < 0.25:
                    rng.choice(sorted(BELT_TYPES)), rng.randint(*BELT_RESERVE_RANGE)
            slot["belts"] = []
            out.append(slot)
            continue
        born = first_stars(seed) + rng.expovariate(1.0 / infall_gyr(seed, r))
        z = metals_at(seed, r, born)
        mass = imf(rng.random(), z, born, L, r)          # Kroupa, its break at its cloud's Jeans mass
        binary = rng.random() < BINARY_SHARE
        companion = mass * (0.1 + 0.9 * rng.random()) if binary else 0.0     # mass ratios flat (Raghavan 2010)
        star_type = _star(mass, binary, L)
        spec = _spec(mass, companion, L)
        sec = SimpleNamespace(star=spec, star_type=star_type)
        slot.update({"star": star_type, "spec": spec, "born": round(born, 6), "z": round(z, 4),
                     "mass": float(physics.star(sec)["mass"])})
        from xylarium.kernel import geometry
        vr = _rng(seed, "vertical", i, j, k)             # its orbit through the disc's plane, heated as it ages
        v = geometry.vertical(r, SETTLED_GYR, vr.random(), 2 * math.pi * vr.random())
        slot["vertical"] = {kk: round(v[kk], 5) for kk in ("amp_kpc", "vz_kms", "period_myr", "exposure", "phase")}
        slot["worlds"] = _worlds(seed, L, i, j, k, slot, sec, r, z, born, rng)
        slot["belts"], slot["comets"] = _belts(L, slot, r, z)
        out.append(slot)
    _CACHE[key] = out
    return out


def _worlds(seed: Any, L: Any, i: int, j: int, k: int, slot: Dict[str, Any], sec: Any, r: float, z: float,
            born: float, rng: random.Random) -> List[Dict[str, Any]]:
    """A star's worlds as physics made them: each orbit's planet (worlds.form), every orbit's six elements and every
    world's spin (orbits.py), each giant's regular moons, then each world's interior, air, seas and chemistry at the
    settled age (worlds.build: its heat from its star's isotopes, its formation and its host's tides)."""
    from fractions import Fraction as _F
    from xylarium.config import SYSTEM_PLANETS
    from xylarium.kernel import interior, orbits, physics
    from xylarium.kernel import worlds as W
    from xylarium.kernel.universe import _deposits_for
    cosmos = _disc()
    spec = sec.star
    env = cosmos.density(r)
    star_kg = float(_F(spec["mass"])) * interior.M_SUN_KG
    laid = physics.lay_out_system(sec, rng.randint(*SYSTEM_PLANETS), rng)
    made, info = [], []
    for n, (q, body, _) in enumerate(laid):
        a_au = float(_F(str(body["q"]))) ** 2
        m = W.form(spec, a_au, z, env, _rng(seed, "form", i, j, k, n), L)
        made.append(m)
        info.append({"a_au": a_au, "mass": m["mass"], "radius": m["radius"], "icy": m["layers"]["ices"] > 0.2})
    els = orbits.system(star_kg, info, env, _rng(seed, "orbits", i, j, k))
    worlds: List[Dict[str, Any]] = []

    def world(body: Dict[str, Any], mm: Dict[str, Any], a_au: float, orbit: Dict[str, Any], host: Optional[int],
              wrng: random.Random) -> Dict[str, Any]:
        state = W.build(seed, spec, a_au, mm["radius"], mm["mass"], mm["giant"], z, r, SETTLED_GYR, mm["ices"],
                        born=born, orbit=orbit, core=mm["layers"]["core"] / max(1e-9, 1.0 - mm["layers"]["envelope"]))
        ptype = W.label(state)
        deps = _deposits_for(ptype, wrng)
        for el in deps:
            enrich = 1.0 if el in PRIMORDIAL else z / max(1e-9, cosmos.metals(r))   # made by then, over today
            deps[el] = int(round(deps[el] * cosmos.abundance(el, r) * enrich))
        media = W.media(seed, spec, a_au, mm["radius"], mm["mass"], mm["giant"], z, r, SETTLED_GYR, world=state)
        rec = {"q": body["q"], "body": body, "type": ptype, "deposits": deps, "ices": mm["ices"],
               "layers": {kk: round(v, 4) for kk, v in mm["layers"].items()},
               "interior": {"q_w_m2": round(state.get("q", 0.0), 5), "tidal_w_m2": round(state.get("q_tide", 0.0), 5),
                            "field": state["field"], "t_int": state.get("t_int")},
               "media": [{kk: md[kk] for kk in ("solvent", "where", "region", "richness", "pace")}
                         | {"energy": round(md["energy"], 6), "t": round(md["t"], 1)} for md in media]}
        if host is not None:
            rec["host"] = host
        # what a world in play needs to be rebuilt as its star changes (worlds.of_planet)
        rec["make"] = {"born": born, "core": mm["layers"]["core"] / max(1e-9, 1.0 - mm["layers"]["envelope"]),
                       "orbit": {"host_kg": orbit["host_kg"], "a_m": orbit["a_m"], "obliquity": orbit["obliquity"],
                                 "el": {kk: orbit["el"][kk] for kk in ("e0", "e_forced", "tau_e")}}}
        return rec

    for n, ((q, body, _), mm, el) in enumerate(zip(laid, made, els)):
        a_au = info[n]["a_au"]
        a_m = a_au * interior.AU_M
        now = orbits.at(star_kg, a_m, el, SETTLED_GYR)
        tilt = math.degrees(min(now["obliquity"], math.pi - now["obliquity"]))
        body = dict(body, mass=physics._s(_F(mm["mass"]).limit_denominator(10 ** 6)),
                    radius=physics._s(_F(mm["radius"]).limit_denominator(10 ** 6)), giant=mm["giant"],
                    locked=now["locked"], tilt=int(round(tilt)),
                    day=physics._s(_F(now["day_s"] / 86400.0).limit_denominator(10 ** 4)),
                    e=round(now["e"], 5), inc=round(now["inc"], 5), node=round(now["node"], 5),
                    peri=round(now["peri"], 5), obliquity=round(now["obliquity"], 5))
        orbit = {"host_kg": star_kg, "a_m": a_m, "el": el, "obliquity": now["obliquity"]}
        worlds.append(world(body, mm, a_au, orbit, None, rng))
        parent = len(worlds) - 1
        if not mm["giant"]:
            continue
        mrng = _rng(seed, "moons", i, j, k, n)
        ice_share = sum(mm["ices"].values()) / (1.0 + sum(mm["ices"].values()))
        g_kg = mm["mass"] * interior.M_EARTH_KG
        for moon in orbits.moons(mm["mass"], mm["radius"], ice_share, mrng):
            am = moon["a_radii"] * mm["radius"] * interior.R_EARTH_M
            mel = {"e0": moon["e_forced"], "e_forced": moon["e_forced"], "tau_e": 0.0, "obliquity": 0.0}
            period_days = 2 * math.pi * math.sqrt(am ** 3 / (interior.G_SI * g_kg)) / 86400.0
            share = moon["icy"] and ice_share or 0.0
            mm_moon = {"mass": moon["mass"], "radius": moon["radius"], "giant": False,
                       "ices": {sp: v for sp, v in mm["ices"].items()},
                       "layers": {"core": W.SOLIDS["core"] * (1 - share), "mantle": (1 - W.SOLIDS["core"]) * (1 - share),
                                  "ices": share, "envelope": 0.0}}
            mbody = {"q": body["q"], "radius": physics._s(_F(moon["radius"]).limit_denominator(10 ** 6)),
                     "mass": physics._s(_F(moon["mass"]).limit_denominator(10 ** 8)), "giant": False,
                     "day": physics._s(_F(period_days).limit_denominator(10 ** 4)), "tilt": 0, "locked": True,
                     "phase0": body.get("phase0", "0/1"), "parent": parent, "e": round(moon["e_forced"], 5),
                     "a_host_radii": round(moon["a_radii"], 3)}
            worlds.append(world(mbody, mm_moon, a_au, {"host_kg": g_kg, "a_m": am, "el": mel, "obliquity": 0.0},
                                parent, mrng))
    return worlds


# ---------------------------------------------------------------------- minds
def _erlang(x: float) -> float:
    """P(4 exponential steps of mean 1 are done by x)."""
    if x <= 0:
        return 0.0
    return 1.0 - math.exp(-x) * (1.0 + x + x * x / 2.0 + x * x * x / 6.0)


def foragers(world: Dict[str, Any], metabolism: str = "biotic", slot: Optional[Dict[str, Any]] = None) -> float:
    """How many foragers the world feeds once a people has evolved there (biosphere.py before its works, one link up
    the food chain: ways.py): its living area x its seasons x the energy reaching its chemistry (light through its
    sky, or heat from below: worlds.py) - divided among bodies by what each burns (biosphere.metabolic_factor at its
    chemistry's own temperature, Damuth's law): a variable world - a tilted axis, a flaring red dwarf - breeds small
    r-strategists (cosmos.arise), a steady one large K-strategists."""
    from fractions import Fraction
    from xylarium.config import PEOPLE_PER_EARTH_AREA
    from xylarium.kernel import biosphere, physics, ways
    b = world.get("body") or {}
    radius = float(Fraction(str(b.get("radius", 1))))
    area = radius * radius * (float(biosphere.GIANT_LIVING_BAND) if b.get("giant") else 1.0)
    season = 0.5 if b.get("locked") else float(physics.growing_share(int(b.get("tilt", 0))))
    from xylarium.kernel import worlds as W
    med = W.best(world.get("media") or [], metabolism)
    if world.get("media") is not None and med is None:
        return 0.0
    fit = med["energy"] if med else 1.0                  # what reaches its chemistry, flux units
    body_t = W.body_temperature(med["solvent"]) if med else None
    star = (slot or {}).get("spec") or physics.star_for((slot or {}).get("star"))
    q = Fraction(str(b.get("q", 1)))
    flux = float(Fraction(star["luminosity"]) / q ** 4)
    gravity = radius * (float(physics.GIANT_DENSITY) if b.get("giant") else 1.0)
    strat = "r" if (int(b.get("tilt", 0)) > 23 or float(Fraction(star["mass"])) < 0.5) else "K"
    # a minded people takes the whole of what its chemistry's energy offers (the leap of cognition: biosphere._reckon)
    return (PEOPLE_PER_EARTH_AREA * area * season * fit * ways.TROPHIC_EFFICIENCY
            / biosphere.metabolic_factor(metabolism, strat, home_flux=flux, home_gravity=gravity, body_t=body_t))


def world_at(seed: Any, slot: Dict[str, Any], world: Dict[str, Any], epoch: float) -> Dict[str, Any]:
    """A world as it is at an epoch - its media read at its star's age then (worlds.world_age's quarter-Gyr steps,
    the same the game reads a world in play at) - for judging what a mind waking then can live on."""
    from fractions import Fraction
    from xylarium.kernel import worlds as W
    age = max(CRUST_GYR, round((epoch - slot["born"]) / W.AGE_STEP_GYR) * W.AGE_STEP_GYR)
    mk = world.get("make") or {}
    b = world["body"]
    if not mk or "host" in world and not b:
        return world
    a_au = float(Fraction(str(b["q"]))) ** 2
    args = (seed, slot["spec"], a_au, float(Fraction(str(b["radius"]))), float(Fraction(str(b["mass"]))),
            bool(b.get("giant")), slot["z"], slot["r"], age, world.get("ices"))
    w = W.build(*args, born=mk.get("born"), orbit=mk.get("orbit"), core=mk.get("core"))
    ms = W.media(*args, world=w)
    return dict(world, media=[{kk: m[kk] for kk in ("solvent", "where", "region", "richness", "pace")}
                              | {"energy": round(m["energy"], 6), "t": round(m["t"], 1)} for m in ms])


def lifetime(slot: Dict[str, Any], laws: Any = None) -> float:
    """A star's main-sequence life (Gyr): its fuel over its burn - mass x the share hydrogen gives up fusing over
    light, a sun's ten billion years in ours."""
    from fractions import Fraction
    spec = slot.get("spec") or {}
    m = float(Fraction(str(spec.get("mass", slot.get("mass", 1)))))
    lum = float(Fraction(str(spec.get("luminosity", 1)))) if spec else luminosity(m, laws)
    return SUN_MS_GYR * (laws.nuclear if laws is not None else 1.0) * m / max(1e-9, lum)


def area_m2(world: Dict[str, Any]) -> float:
    """The area a world's life has: its surface (a giant's habitable band of its envelope)."""
    from fractions import Fraction
    from xylarium.kernel import biosphere, interior
    b = world.get("body") or {}
    r = float(Fraction(str(b.get("radius", 1)))) * interior.R_EARTH_M
    return 4.0 * math.pi * r * r * (float(biosphere.GIANT_LIVING_BAND) if b.get("giant") else 1.0)


def exposure(slot: Dict[str, Any]) -> float:
    """How much of its orbit a star spends in the crowded plane of the disc (1 for a star that never leaves it)."""
    return float((slot.get("vertical") or {}).get("exposure", 1.0))


def chemistries(seed: Any, slot: Dict[str, Any], world: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Each chemistry the world's physics allows that can copy itself at all (life.ladder): its best medium's ladder
    to a mind, the chance it is never sterilised, when its window ends (its star's death; never, for a sea in the
    dark), and its rate of life-ending impacts - all from the world, its star and its place in the galaxy."""
    from xylarium.kernel import life
    cosmos = _disc()
    bb = big_bang(seed)
    L = laws(seed)
    by: Dict[str, Dict[str, Any]] = {}
    for m in world.get("media", []):
        if m["region"] not in by or m["richness"] * m["energy"] > by[m["region"]]["richness"] * \
                by[m["region"]]["energy"]:
            by[m["region"]] = m
    # a lit world's window closes as its star leaves the main sequence: the giant branch's swelling light boils its
    # seas (cosmos.AGEING_SHARE - the same branch the game's stars climb)
    star_end = slot["born"] + lifetime(slot, L) * (1.0 - cosmos.AGEING_SHARE)
    crowd = cosmos.density(slot["r"]) * bb["stars"] * exposure(slot)
    area = area_m2(world)
    out = []
    for region in sorted(by):
        m = by[region]
        lad = life.ladder(m, area, L)
        if lad is None or not lad["steps"]:
            continue
        dark = m["where"] in ("under_ice", "deep")
        end = float("inf") if dark else star_end         # a dark sea runs on its world's heat, not its star
        window = min(HORIZON_GYR, end) - slot["born"]
        hazard = life.STERILISE_AT_R0 * crowd * window / 10.0 * (0.5 if dark else 1.0)
        out.append({"region": region, "ladder": lad, "live": math.exp(-hazard), "end": end,
                    "mu": life.EXTINCTIONS_PER_GYR * crowd})
    return out


def lineage(seed: Any, i: int, j: int, k: int, w: int, slot: Dict[str, Any], world: Dict[str, Any],
            seeded: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
    """A world's life, as the seed's initial conditions give it: for each chemistry, the rungs it climbs and when (each step an
    exponential wait of its ladder's mean; an impact sends a lineage back to the start of its current rung - life
    itself, once begun, is never undone), and whether it was sterilised. The furthest lineage (soonest, at a tie)
    is the world's life. seeded: region -> the epoch life of that chemistry could arrive from a neighbour."""
    from xylarium.kernel import life
    t0 = slot["born"] + CRUST_GYR
    if t0 >= HORIZON_GYR:
        return None
    best = None
    for ch in chemistries(seed, slot, world):
        region, steps, mu = ch["region"], ch["ladder"]["steps"], ch["mu"]
        rng = _rng(seed, "life", i, j, k, w, region)
        horizon = min(ch["end"], HORIZON_GYR)
        steril = t0 + rng.random() * (horizon - t0) if rng.random() >= ch["live"] and horizon > t0 else float("inf")
        got = life.climb(rng, [x["mean_gyr"] for x in steps], t0, horizon, steril, mu,
                         seeded.get(region) if seeded else None)
        times, setbacks = got["times"], got["setbacks"]
        rec = {"region": region, "steps": times, "n": len(steps), "complete": ch["ladder"]["complete"],
               "setbacks": setbacks, "sterilised": steril < horizon, "mu": mu, "live": ch["live"], "end": ch["end"],
               "eps0": ch["ladder"]["eps0"], "means": [x["mean_gyr"] for x in steps]}
        mind = rec["complete"] and len(times) == rec["n"]
        key = (mind, len(times) / max(1, rec["n"]), -(times[-1] if times else 0))
        if best is None or key > best[0]:
            best = (key, rec)
    return best[1] if best else None


def system_life(seed: Any, i: int, j: int, k: int, slot: Dict[str, Any]) -> List[Optional[Dict[str, Any]]]:
    """Every world of a system's life, with what its neighbours carry to it: rock an impact throws off one world
    reaches the others in about a million of its orbits (life.transfer_gyr) - microbes travel, minds do not."""
    from fractions import Fraction
    from xylarium.kernel import life
    key = ("system_life", seed, i, j, k)
    if key in _CACHE:
        return _CACHE[key]
    ws = slot.get("worlds") or []
    first = [lineage(seed, i, j, k, w, slot, world) for w, world in enumerate(ws)]
    star = float(slot.get("mass", 1.0))
    arrivals: List[Dict[str, float]] = [{} for _ in ws]
    for w, lin in enumerate(first):
        if not lin or not lin["steps"]:
            continue
        a_au = float(Fraction(str(ws[w]["body"].get("q", 1)))) ** 2
        when = lin["steps"][0] + life.transfer_gyr(a_au, star)
        for v in range(len(ws)):
            if v != w:
                arrivals[v][lin["region"]] = min(arrivals[v].get(lin["region"], float("inf")), when)
    out = [lineage(seed, i, j, k, w, slot, world, arrivals[w]) if arrivals[w] else first[w]
           for w, world in enumerate(ws)]
    _CACHE[key] = out
    return out


def _erlang_n(x: float, n: int) -> float:
    if x <= 0:
        return 0.0
    term, total = 1.0, 1.0
    for kk in range(1, n):
        term *= x / kk
        total += term
    return 1.0 - math.exp(-x) * total


CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runs",
                         "creation")
LAWS = ("creation.py", "cosmos.py", "physics.py", "universe.py", "scheduler.py", "worlds.py", "biosphere.py",
        "fertility.py", "fundamental.py", "interior.py", "orbits.py", "geometry.py", "life.py", "../config.py")


def laws_digest() -> str:
    """The laws creation follows, as a digest of their source: a schedule kept under other laws is another universe."""
    if "digest" not in _CACHE:
        import hashlib
        h = hashlib.sha1()
        here = os.path.dirname(os.path.abspath(__file__))
        for name in LAWS:
            with open(os.path.join(here, name), "rb") as f:
                h.update(name.encode() + f.read())
        _CACHE["digest"] = h.hexdigest()[:10]
    return _CACHE["digest"]


def schedule(seed: int) -> Dict[str, Any]:
    """Every mind the galaxy raises before HORIZON_GYR, on the worlds the cells hold, with its expectation curve.
    Computed once per universe (and kept on disk under the laws' digest: it is a pure function of the seed)."""
    key = ("schedule", seed)
    if key in _CACHE:
        return _CACHE[key]
    path = os.path.join(CACHE_DIR, laws_digest(), f"seed{seed}.json")
    try:
        with open(path) as f:
            _CACHE[key] = json.load(f)
        return _CACHE[key]
    except (OSError, ValueError):
        pass
    out = _compute(seed)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w") as f:
            json.dump(out, f)
        os.replace(tmp, path)
    except OSError:
        pass
    _CACHE[key] = out
    return out


# ---------------------------------------------------------------------- the galaxy worked out
def _terms(seed: Any, slot: Dict[str, Any], world: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Each chemistry of a world that could raise a people: its ladder's mean and spread to a mind (impacts lengthen
    the later steps), the chance it is never sterilised, and when its window closes."""
    out = []
    for ch in chemistries(seed, slot, world):
        if not ch["ladder"]["complete"] or foragers(world, ch["region"], slot) < VIABLE:
            continue
        mu = ch["mu"]
        means = [x["mean_gyr"] if n == 0 or mu <= 0 else (math.exp(min(50.0, mu * x["mean_gyr"])) - 1.0) / mu
                 for n, x in enumerate(ch["ladder"]["steps"])]
        out.append({"region": ch["region"], "means": means, "m1": sum(means), "m2": sum(x * x for x in means),
                    "live": ch["live"], "end": ch["end"]})
    return out


def _cell_life(seed: Any, i: int, j: int, npts: int) -> Dict[str, Any]:
    """One cell's share of the galaxy's minds and expectation - a pure function of the seed and the cell."""
    from xylarium.kernel import life
    out = {"minds": [], "bins": {}, "worlds": 0, "alive": 0, "stages": [0] * (life.MAX_RUNGS + 1), "rungs": {}}
    for slot in cell(seed, i, j):
        if "worlds" not in slot:
            continue
        t0 = slot["born"] + CRUST_GYR
        if t0 >= HORIZON_GYR:
            continue
        lins = system_life(seed, i, j, slot["k"], slot)
        for w, world in enumerate(slot["worlds"]):
            out["worlds"] += 1
            lin = lins[w]
            if lin is None:
                continue
            out["stages"][len(lin["steps"])] += 1
            out["rungs"][lin["n"]] = out["rungs"].get(lin["n"], 0) + 1
            if lin["steps"]:
                out["alive"] += 1
            if lin["complete"] and len(lin["steps"]) == lin["n"] and \
                    foragers(world_at(seed, slot, world, lin["steps"][-1]), lin["region"], slot) >= VIABLE:
                out["minds"].append({"cell": [i, j], "k": slot["k"], "w": w, "epoch": lin["steps"][-1],
                                     "metab": lin["region"], "mass": round(slot["mass"], 3),
                                     "steps": lin["steps"], "setbacks": lin["setbacks"]})
            # the expectation: each chemistry's chance of a mind by each epoch (impacts lengthen the later steps)
            terms = [(round(math.log(x["m1"]) * 50), round(math.log(x["m2"]) * 50), round(x["live"], 3),
                      npts if x["end"] >= HORIZON_GYR else int(math.ceil(x["end"] / CURVE_STEP)))
                     for x in _terms(seed, slot, world)]
            if terms:
                key = (int(math.ceil(t0 / CURVE_STEP)),) + tuple(terms)
                out["bins"][key] = out["bins"].get(key, 0) + 1
    return out


def _cells_life(args: Tuple[Any, List[Tuple[int, int]], int]) -> List[Dict[str, Any]]:
    seed, cs, npts = args
    return [_cell_life(seed, i, j, npts) for i, j in cs]


WORKERS = max(1, min(8, (os.cpu_count() or 1)))   # the machine's cores, for the one-time working out (any count
                                                  # gives the same galaxy: each cell is its own pure function)


def _compute(seed: Any) -> Dict[str, Any]:
    """Every cell of the galaxy worked out world by world - the Big Bang's initial conditions, once per universe.
    Cells are independent, so they are worked out in parallel and merged in the cells' own order."""
    from xylarium.kernel import life
    npts = int(HORIZON_GYR / CURVE_STEP) + 1
    cs = list(_disc().cells())
    chunks = [cs[n::WORKERS * 4] for n in range(WORKERS * 4)]
    per: List[Dict[str, Any]] = []
    if WORKERS > 1:
        try:
            import multiprocessing as mp
            from concurrent.futures import ProcessPoolExecutor
            with ProcessPoolExecutor(WORKERS, mp_context=mp.get_context("fork")) as ex:
                for got in ex.map(_cells_life, [(seed, ch, npts) for ch in chunks]):
                    per.extend(got)
        except Exception:
            per = []
    if not per:
        per = _cells_life((seed, cs, npts))
    minds: List[Dict[str, Any]] = []
    curve = [0.0] * npts
    bins: Dict[Tuple[Any, ...], int] = {}
    stages = [0] * (life.MAX_RUNGS + 1)
    rungs: Dict[int, int] = {}
    tally = {"worlds": 0, "alive": 0, "stages": stages, "rungs": rungs}
    for c in per:
        minds.extend(c["minds"])
        tally["worlds"] += c["worlds"]
        tally["alive"] += c["alive"]
        for n, x in enumerate(c["stages"]):
            stages[n] += x
        for n, x in c["rungs"].items():
            rungs[n] = rungs.get(n, 0) + x
        for key, x in c["bins"].items():
            bins[key] = bins.get(key, 0) + x
    for key in sorted(bins, key=repr):
        c0, terms, cnt = key[0], key[1:], bins[key]
        for c in range(c0, npts):
            miss = 1.0
            for lm1, lm2, live, ce in terms:
                m1, m2 = math.exp(lm1 / 50.0), math.exp(lm2 / 50.0)
                shape, scale = m1 * m1 / m2, m2 / m1
                miss *= 1.0 - life.gamma_cdf(shape, (min(c, ce) - c0) * CURVE_STEP / scale) * live
            curve[c] += cnt * (1.0 - miss)
    minds.sort(key=lambda e: (e["epoch"], e["cell"], e["k"], e["w"]))
    return {"minds": minds, "curve": [round(x, 2) for x in curve], "life": tally}


def limits(seed: Any, every: int = 7) -> Dict[str, Any]:
    """What stops life in a universe, world by world (a sample of its cells): the first gate each world fails - no
    solvent at all; a solvent whose bonds cannot copy faithfully (life.fidelity); a ladder too long for the time it
    has; its star dying first; sterilised; too few bodies fed to make a people - and how far the rest got. The
    audit for choosing other laws or a richer Big Bang."""
    cosmos = _disc()
    out = {"worlds": 0, "no_solvent": 0, "cannot_copy": 0, "star_died": 0, "sterilised": 0, "too_slow": 0,
           "unfed": 0, "minds": 0, "alive": 0, "by_region": {}, "rungs": {}, "epochs": []}
    for (i, j) in cosmos.cells()[::every]:
        for slot in cell(seed, i, j):
            if not slot.get("worlds") or slot["born"] + CRUST_GYR >= HORIZON_GYR:
                continue
            lins = system_life(seed, i, j, slot["k"], slot)
            for w, world in enumerate(slot["worlds"]):
                out["worlds"] += 1
                if not world.get("media"):
                    out["no_solvent"] += 1
                    continue
                lin = lins[w]
                if lin is None:
                    out["cannot_copy"] += 1
                    continue
                out["by_region"][lin["region"]] = out["by_region"].get(lin["region"], 0) + 1
                out["rungs"][lin["n"]] = out["rungs"].get(lin["n"], 0) + 1
                if lin["steps"]:
                    out["alive"] += 1
                if lin["complete"] and len(lin["steps"]) == lin["n"]:
                    if foragers(world_at(seed, slot, world, lin["steps"][-1]), lin["region"], slot) >= VIABLE:
                        out["minds"] += 1
                        out["epochs"].append([round(lin["steps"][-1], 4), slot["r"], lin["region"]])
                    else:
                        out["unfed"] += 1
                elif lin["sterilised"]:
                    out["sterilised"] += 1
                elif lin["end"] < HORIZON_GYR and sum(lin["means"]) > lin["end"] - slot["born"]:
                    out["star_died"] += 1
                else:
                    out["too_slow"] += 1
    return out


def after(seed: int, last: Optional[List[Any]], n: int) -> List[Dict[str, Any]]:
    """The next n minds after the one keyed last ([epoch, cell, k, w])."""
    minds = schedule(seed)["minds"]
    if last is None:
        return minds[:n]
    keys = [(m["epoch"], m["cell"], m["k"], m["w"]) for m in minds]
    at = bisect.bisect_right(keys, (last[0], list(last[1]), last[2], last[3]))
    return minds[at:at + n]
