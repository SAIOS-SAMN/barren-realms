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

Each biology passes Carter's hard steps (4; Watson 2008) on its own dice - each an exponential wait of mean
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

# ---------------------------------------------------------------------- minds
HARD_STEPS = 4                  # Carter (1983) and Watson (2008) read ~4 off Earth's one history: now drawn per universe
STEP_GYR = 10.0                 # the old Earth-read mean wait (retired: settled galaxies only)
STEPS_RANGE = (3, 6)            # hard steps from chemistry to a mind: drawn per universe (one history fixes nothing)
STEP_LOG_RANGE = (-2.0, 0.0)    # log10 Gyr: a step's mean wait at unit pace, full richness, ample energy (drawn)
ENERGY_HALF = 0.01              # flux units (~3 W/m^2: about what a biosphere fixes of full sunlight) at which a
                                # chemistry's progress is half energy-limited (declared)
ORIGIN_GYR = 0.1                # life is abundant: it arises within ~0.1 Gyr of chemistry wherever a solvent is,
                                # slower as that chemistry is slower and poorer (declared: the universe's life law)
TRANSFER_GYR = 0.05             # life carried between the worlds of a region by impact ejecta (declared)
HARDEN = 0.25                   # each extinction a lineage survives makes it hardier: later steps come sooner and
                                # blows land softer by this share (declared)
EXTINCTIONS_PER_GYR = 2.0       # life-resetting impacts per Gyr at unit stellar density (declared): flybys and the
                                # tide shake comets loose in proportion to the neighbourhood's stars
SUN_MS_GYR = 10.0               # main-sequence life of a solar-mass star; ~ M^-2.5
CRUST_GYR = 0.6                 # a rocky world's crust settles and its bombardment ends
STERILISE_AT_R0 = 0.1           # chance a fully molecular biosphere at R0 is sterilised over its window
HORIZON_GYR = 30.0              # deep time the schedule looks ahead to
CURVE_STEP = 0.25               # Gyr between points of the expectation curve
METALS_NEED = {"biotic": 1.0, "mineral": 1.0, "cryogenic": 0.5, "umbral": 1.0, "plasmic": 0.0}
MOLECULAR = {"biotic": 1.0, "mineral": 0.5, "cryogenic": 0.5, "umbral": 0.5, "plasmic": 0.0}
SETTLED_GYR = 3.0               # a world's chemistry is read once its crust, air and seas have settled (declared)
VIABLE = 500                    # Franklin's 50/500 rule: the number that keeps a people's evolutionary potential

_CACHE: Dict[Tuple[int, int], Dict[str, Any]] = {}       # (seed, cell) -> the cell; (seed,) -> the schedule


def _rng(seed: int, *parts: Any) -> random.Random:
    from xylarium.kernel import scheduler
    return random.Random(scheduler.stream(SimpleNamespace(seed=seed), *parts))


# ---------------------------------------------------------------------- the Big Bang
UNIVERSES = {                   # the kind of Big Bang chosen at genesis: centres the seed's draw is made about
    "measured": {"sigma8": 1.0, "f_baryon": 1.0},      # about our own universe's (Planck 2018)
    "lush": {"sigma8": 1.3, "f_baryon": 1.5},          # lumpier and richer in baryons: stars sooner, more of them, and
                                                       # more metals made early - a universe more abundant in life
}


def universe(kernel: Any) -> Any:
    """The creation key of a kernel's universe: its seed, and the kind of Big Bang chosen at its genesis."""
    kind = ((getattr(kernel, "state", None) or {}).get("genesis") or {}).get("universe") or "measured"
    return kernel.seed if kind == "measured" else f"{kernel.seed}:{kind}"


def big_bang(seed: Any) -> Dict[str, float]:
    """This universe's initial conditions and what follows from them (seed may carry its kind: '7:lush')."""
    key = ("bb", seed)
    if key in _CACHE:
        return _CACHE[key]
    kind = UNIVERSES.get(str(seed).partition(":")[2] or "measured", UNIVERSES["measured"])
    rng = _rng(seed, "big bang")
    s8 = SIGMA8 * kind["sigma8"] * 10.0 ** rng.gauss(0.0, SPREAD_DEX)
    fb = F_BARYON * kind["f_baryon"] * 10.0 ** rng.gauss(0.0, SPREAD_DEX)
    closed = abs(rng.gauss(0.0, FLATNESS)) + FLATNESS / 20.0             # Omega - 1 > 0: a 3-sphere
    steps = STEPS_RANGE[0] + int(rng.random() * (STEPS_RANGE[1] - STEPS_RANGE[0] + 1))
    step_gyr = 10.0 ** (STEP_LOG_RANGE[0] + rng.random() * (STEP_LOG_RANGE[1] - STEP_LOG_RANGE[0]))
    out = {"sigma8": round(s8, 4), "f_baryon": round(fb, 4), "omega_minus_1": round(closed, 6),
           "assembly": round((SIGMA8 / s8) ** COLLAPSE, 4),               # epochs of formation, over ours
           "stars": round(fb / F_BARYON, 4),                              # stars per volume, over ours
           "curvature_mpc": round(C_KMS / H0_KMS_MPC / math.sqrt(closed), 1),
           "steps": steps, "step_gyr": round(step_gyr, 5)}
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
def luminosity(mass: float) -> float:
    """Main-sequence light from mass (the measured piecewise relation): faint and slow-burning below half a sun,
    steepest around a sun, flattening toward the Eddington limit for the heaviest."""
    if mass < 0.43:
        return 0.23 * mass ** 2.3
    if mass < 2.0:
        return mass ** 4.0
    if mass < 55.0:
        return 1.4 * mass ** 3.5
    return 32000.0 * mass


def imf(u: float, z: float, born: Optional[float] = None) -> float:
    """A star's mass from Kroupa's two slopes, the break moved by its gas's metals and by the warmth of the young
    universe: no cloud is colder than the cosmic background, 2.725 K x (1 + z), and a warmer cloud's Jeans mass is
    larger (~ T^1.5) - the early stars were heavier and hotter (inverse transform)."""
    mb = KROUPA_BREAK * max(z, 1e-3) ** -JEANS_Z
    if born is not None:
        floor = 2.725 / max(1e-3, scale_factor(born))
        mb *= max(1.0, floor / CLOUD_K) ** 1.5
    lo, hi = IMF_MIN, IMF_MAX
    mb = min(max(mb, lo * 1.01), hi * 0.99)
    a1, a2 = 1.0 - KROUPA_LOW, 1.0 - KROUPA_HIGH
    w1 = (mb ** a1 - lo ** a1) / a1                      # mass function continuous at the break
    w2 = mb ** (KROUPA_HIGH - KROUPA_LOW) * (hi ** a2 - mb ** a2) / a2
    x = u * (w1 + w2)
    if x < w1:
        return (lo ** a1 + a1 * x) ** (1.0 / a1)
    return (mb ** a2 + a2 * (x - w1) / mb ** (KROUPA_HIGH - KROUPA_LOW)) ** (1.0 / a2)


def _spec(mass: float, companion: float = 0.0) -> Dict[str, str]:
    """A star's exact physics from its own mass (not its class's): m = sqrt(M) to a hundredth (orbits), its light
    from the mass-luminosity relation; a companion adds its mass and its own light."""
    from fractions import Fraction
    m1 = Fraction(max(1, round(math.sqrt(mass) * 100)), 100)
    total, lum = m1 * m1, Fraction(luminosity(float(m1 * m1))).limit_denominator(10 ** 8)
    if companion > 0:
        m2 = Fraction(max(1, round(math.sqrt(companion) * 100)), 100)
        total, lum = total + m2 * m2, lum + Fraction(luminosity(float(m2 * m2))).limit_denominator(10 ** 8)
    m = Fraction(max(1, round(math.sqrt(float(total)) * 100)), 100)
    lum = lum.limit_denominator(10 ** 6)
    return {"m": f"{m.numerator}/{m.denominator}", "mass": f"{total.numerator}/{total.denominator}",
            "luminosity": f"{lum.numerator}/{lum.denominator}"}


def _star(mass: float, binary: bool) -> str:
    if binary:
        return "Binary pair"
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
    n0 = -math.log(1.0 - SYSTEMS_SHARE_R0)
    out = []
    for k in range(SLOTS):
        rng = _rng(seed, "creation", i, j, k)
        r = cosmos.ring_radius(i) + (rng.random() - 0.5) * cosmos.CELL_KPC * 0.4
        theta0 = cosmos.cell_theta(i, j) + (rng.random() - 0.5) * 2 * math.pi / cosmos.slots(i) * 0.4
        names = (rng.randrange(8), rng.randrange(8))
        slot: Dict[str, Any] = {"k": k, "r": round(r, 4), "theta0": round(theta0, 6), "names": names}
        if rng.random() >= 1.0 - math.exp(-n0 * cosmos.density(r) * bb["stars"]):
            slot["belts"] = []
            if rng.random() < BELT_CHANCE:
                slot["belts"].append((rng.choice(sorted(BELT_TYPES)), rng.randint(*BELT_RESERVE_RANGE)))
                if rng.random() < 0.25:
                    slot["belts"].append((rng.choice(sorted(BELT_TYPES)), rng.randint(*BELT_RESERVE_RANGE)))
            out.append(slot)
            continue
        born = first_stars(seed) + rng.expovariate(1.0 / infall_gyr(seed, r))
        z = metals_at(seed, r, born)
        mass = imf(rng.random(), z, born)                # Kroupa, heavier in metal-poor gas and a warmer young sky
        binary = rng.random() < BINARY_SHARE
        companion = mass * (0.1 + 0.9 * rng.random()) if binary else 0.0     # mass ratios flat (Raghavan 2010)
        star_type = _star(mass, binary)
        spec = _spec(mass, companion)
        sec = SimpleNamespace(star=spec, star_type=star_type)
        worlds = []
        from fractions import Fraction as _F
        from xylarium.kernel import worlds as W
        for n, (q, body, _) in enumerate(physics.lay_out_system(sec, rng.randint(*SYSTEM_PLANETS), rng)):
            # the world its orbit built: its size, layers and ices from the disc's elements (worlds.form); the layout
            # gives only its orbit, spin and tilt
            a_au = float(_F(str(body["q"]))) ** 2
            made = W.form(spec, a_au, z, cosmos.density(r), _rng(seed, "form", i, j, k, n))
            body = dict(body, mass=physics._s(_F(made["mass"]).limit_denominator(10 ** 6)),
                        radius=physics._s(_F(made["radius"]).limit_denominator(10 ** 6)), giant=made["giant"])
            state = W.build(seed, spec, a_au, made["radius"], made["mass"], made["giant"], z, r, SETTLED_GYR,
                            made["ices"])
            ptype = W.label(state)
            deps = _deposits_for(ptype, rng)
            for el in deps:
                enrich = 1.0 if el in PRIMORDIAL else z / max(1e-9, cosmos.metals(r))   # made by then, over today
                deps[el] = int(round(deps[el] * cosmos.abundance(el, r) * enrich))
            media = W.media(seed, spec, a_au, made["radius"], made["mass"], made["giant"], z, r, SETTLED_GYR,
                            world=state)
            worlds.append({"q": q, "body": body, "type": ptype, "deposits": deps, "ices": made["ices"],
                           "layers": {kk: round(v, 4) for kk, v in made["layers"].items()},
                           "media": [{kk: m[kk] for kk in ("solvent", "where", "region", "richness", "pace")}
                                     | {"energy": round(m["energy"], 5), "t": round(m["t"], 1)} for m in media]})
        slot.update({"star": star_type, "spec": spec, "born": round(born, 6), "z": round(z, 4), "worlds": worlds,
                     "mass": float(physics.star(sec)["mass"])})
        out.append(slot)
    _CACHE[key] = out
    return out


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
    from xylarium.kernel import biosphere, ways
    b = world.get("body") or {}
    radius = float(Fraction(str(b.get("radius", 1))))
    area = radius * radius * (float(biosphere.GIANT_LIVING_BAND) if b.get("giant") else 1.0)
    season = 0.5 if b.get("locked") else 1.0 - int(b.get("tilt", 0)) / 90.0
    from xylarium.kernel import physics, worlds as W
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


def lifetime(slot: Dict[str, Any]) -> float:
    """A star's main-sequence life (Gyr): its fuel over its burn - mass over light, a sun's ten billion years."""
    from fractions import Fraction
    spec = slot.get("spec") or {}
    m = float(Fraction(str(spec.get("mass", slot.get("mass", 1)))))
    lum = float(Fraction(str(spec.get("luminosity", 1)))) if spec else luminosity(m)
    return SUN_MS_GYR * m / max(1e-9, lum)


def chemistries(seed: int, slot: Dict[str, Any], world: Dict[str, Any]) \
        -> List[Tuple[str, float, float, float, float, float]]:
    """(region, mean wait per hard step, survival, window end, extinctions per Gyr, energy factor) for each chemistry
    the world's physics allows (worlds.py): a step's rate is the chemistry's pace x its richness x the energy
    reaching it. The first step - life itself - is chemistry and time, not throughput: it waits mean x energy
    factor; the later ones (complexity, a mind) need the biomass energy feeds."""
    cosmos = _disc()
    bb = big_bang(seed)
    out = []
    by: Dict[str, Dict[str, Any]] = {}
    for m in world.get("media", []):
        if m["region"] not in by or m["richness"] * m["energy"] > by[m["region"]]["richness"] * \
                by[m["region"]]["energy"]:
            by[m["region"]] = m
    star_end = slot["born"] + lifetime(slot)
    density = cosmos.density(slot["r"]) * bb["stars"]
    for region in sorted(by):
        m = by[region]
        rate = m["pace"] * m["richness"] * m["energy"] / (m["energy"] + ENERGY_HALF)
        if rate <= 0:
            continue
        dark = m["where"] in ("under_ice", "deep")
        end = float("inf") if dark else star_end         # a dark sea runs on its world's heat, not its star
        hazard = STERILISE_AT_R0 * density * MOLECULAR.get(region, 1.0) * (0.5 if dark else 1.0)
        ef = m["energy"] / (m["energy"] + ENERGY_HALF)
        out.append((region, bb["step_gyr"] / rate, math.exp(-hazard), end, EXTINCTIONS_PER_GYR * density, ef))
    return out


def lineage(seed: int, i: int, j: int, k: int, w: int, slot: Dict[str, Any], world: Dict[str, Any],
            seeded: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
    """A world's life, as the seed's dice give it: for each chemistry, the hard steps it passes and when (a step is
    progress an extinction can undo; the first, life itself, is never undone), its setbacks, and whether it was
    sterilised. The furthest lineage (soonest, at a tie) is the world's life.
    Life is abundant: it arises soon wherever a solvent is (ORIGIN_GYR, slower for slow, poor chemistry), and once one
    world of a region has it, the region's others with the same chemistry receive it (seeded: region -> epoch).
    Each extinction survived hardens the lineage: its later steps come sooner and its next blows land softer."""
    bb = big_bang(seed)
    n = bb["steps"]
    t0 = slot["born"] + CRUST_GYR
    if t0 >= HORIZON_GYR:
        return None
    best = None
    for region, mean, live, end, mu, ef in chemistries(seed, slot, world):
        rng = _rng(seed, "life", i, j, k, w, region)
        horizon = min(end, HORIZON_GYR)
        steril = t0 + rng.random() * (horizon - t0) if rng.random() >= live and horizon > t0 else float("inf")
        t, times, setbacks = t0, [], 0
        chem = bb["step_gyr"] / max(1e-12, mean * ef)               # pace x richness of this chemistry
        for step in range(n):
            hard = 1.0 + HARDEN * setbacks
            if step == 0:
                need = rng.expovariate(1.0 / (ORIGIN_GYR / math.sqrt(max(1e-6, chem))))   # life: chemistry and time
                if seeded and region in seeded:
                    need = min(need, max(0.0, seeded[region] - t0))   # or carried here from a neighbour
            else:
                need = rng.expovariate(hard / mean)
            if step == 0 or mu <= 0:
                t += need
            else:
                while t < horizon:
                    x = rng.expovariate(mu / hard)
                    if x >= need:
                        t += need
                        break
                    t += x
                    setbacks += 1
                    hard = 1.0 + HARDEN * setbacks
            if t > horizon or t > steril:
                break
            times.append(round(t, 6))
        rec = {"region": region, "steps": times, "setbacks": setbacks, "sterilised": steril < horizon,
               "mean": mean, "mu": mu, "live": live, "end": end}
        if best is None or (len(times), -(times[-1] if times else 0)) > (len(best["steps"]),
                                                                         -(best["steps"][-1] if best["steps"] else 0)):
            best = rec
    return best


def region_life(seed: Any, i: int, j: int) -> Dict[str, float]:
    """When life of each chemistry could first reach the worlds of a cell: its earliest origin there, plus the
    transfer time - life that exists outside will exist inside."""
    key = ("region_life", seed, i, j)
    if key in _CACHE:
        return _CACHE[key]
    first: Dict[str, float] = {}
    for slot in cell(seed, i, j):
        for w, world in enumerate(slot.get("worlds", [])):
            lin = lineage(seed, i, j, slot["k"], w, slot, world)
            if lin and lin["steps"]:
                first[lin["region"]] = min(first.get(lin["region"], float("inf")), lin["steps"][0])
    _CACHE[key] = {r: t + TRANSFER_GYR for r, t in first.items()}
    return _CACHE[key]


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
        "fertility.py", "../config.py")


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


def _compute(seed: int) -> Dict[str, Any]:
    cosmos = _disc()
    n = big_bang(seed)["steps"]
    minds: List[Dict[str, Any]] = []
    npts = int(HORIZON_GYR / CURVE_STEP) + 1
    curve = [0.0] * npts
    bins: Dict[Tuple[Any, ...], int] = {}
    life = {"worlds": 0, "alive": 0, "stages": [0] * (n + 1)}
    for (i, j) in cosmos.cells():
        seeded = region_life(seed, i, j)
        for slot in cell(seed, i, j):
            if "worlds" not in slot:
                continue
            t0 = slot["born"] + CRUST_GYR
            if t0 >= HORIZON_GYR:
                continue
            for w, world in enumerate(slot["worlds"]):
                life["worlds"] += 1
                lin = lineage(seed, i, j, slot["k"], w, slot, world, seeded)
                if lin is None:
                    continue
                life["stages"][len(lin["steps"])] += 1
                if lin["steps"]:
                    life["alive"] += 1
                if len(lin["steps"]) == n and foragers(world, lin["region"], slot) >= VIABLE:
                    minds.append({"cell": [i, j], "k": slot["k"], "w": w, "epoch": lin["steps"][-1],
                                  "metab": lin["region"], "mass": round(slot["mass"], 3),
                                  "steps": lin["steps"], "setbacks": lin["setbacks"]})
                # the expectation: each chemistry's chance of a mind by each epoch (resets lengthen the later steps)
                terms = []
                for region, mean, live, end, mu, ef in chemistries(seed, slot, world):
                    if foragers(world, region, slot) < VIABLE:
                        continue
                    later = (math.exp(min(50.0, mu * mean)) - 1.0) / mu if mu > 0 else mean
                    eff = (mean * ef + (n - 1) * later) / n
                    terms.append((region, round(math.log(eff) * 100), round(live, 3),
                                  npts if end >= HORIZON_GYR else int(math.ceil(end / CURVE_STEP))))
                if terms:
                    key = (int(math.ceil(t0 / CURVE_STEP)),) + tuple(terms)
                    bins[key] = bins.get(key, 0) + 1
    for key in sorted(bins, key=repr):
        c0, terms, cnt = key[0], key[1:], bins[key]
        for c in range(c0, npts):
            miss = 1.0
            for region, lm, live, ce in terms:
                miss *= 1.0 - _erlang_n((min(c, ce) - c0) * CURVE_STEP / math.exp(lm / 100.0), n) * live
            curve[c] += cnt * (1.0 - miss)
    minds.sort(key=lambda e: (e["epoch"], e["cell"], e["k"], e["w"]))
    return {"minds": minds, "curve": [round(x, 2) for x in curve], "life": life}


def limits(seed: Any, every: int = 7) -> Dict[str, Any]:
    """What stops life in a universe, world by world (a sample of its cells): the first gate each world fails - no
    solvent at all, a chemistry too poor in bonds and elements, too little energy reaching it, kinetics too slow, its
    star dying first, sterilised - and how far the rest got. The audit for choosing a stronger or richer Big Bang."""
    cosmos = _disc()
    out = {"worlds": 0, "no_solvent": 0, "poor_chemistry": 0, "starved": 0, "slow": 0, "star_died": 0,
           "sterilised": 0, "stalled": 0, "minds": 0, "by_region": {}}
    n = big_bang(seed)["steps"]
    for (i, j) in cosmos.cells()[::every]:
        for slot in cell(seed, i, j):
            for w, world in enumerate(slot.get("worlds", [])):
                if slot["born"] + CRUST_GYR >= HORIZON_GYR:
                    continue
                out["worlds"] += 1
                chems = chemistries(seed, slot, world)
                if not world.get("media"):
                    out["no_solvent"] += 1
                    continue
                lin = lineage(seed, i, j, slot["k"], w, slot, world, region_life(seed, i, j))
                if lin is None or not chems:
                    out["poor_chemistry"] += 1
                    continue
                out["by_region"][lin["region"]] = out["by_region"].get(lin["region"], 0) + 1
                if len(lin["steps"]) == n:
                    out["minds"] += 1
                    continue
                m = max((md for md in world["media"] if md["region"] == lin["region"]),
                        key=lambda md: md["richness"] * md["energy"])
                energy = m["energy"] / (m["energy"] + ENERGY_HALF)
                if lin["sterilised"]:
                    out["sterilised"] += 1
                elif lin["end"] < HORIZON_GYR and (not lin["steps"] or lin["steps"][-1] < lin["end"]) and \
                        lin["mean"] * n > lin["end"] - slot["born"]:
                    out["star_died"] += 1
                elif m["richness"] < 0.05:
                    out["poor_chemistry"] += 1
                elif energy < 0.2:
                    out["starved"] += 1
                elif m["pace"] < 0.05:
                    out["slow"] += 1
                else:
                    out["stalled"] += 1
    return out


def after(seed: int, last: Optional[List[Any]], n: int) -> List[Dict[str, Any]]:
    """The next n minds after the one keyed last ([epoch, cell, k, w])."""
    minds = schedule(seed)["minds"]
    if last is None:
        return minds[:n]
    keys = [(m["epoch"], m["cell"], m["k"], m["w"]) for m in minds]
    at = bisect.bisect_right(keys, (last[0], list(last[1]), last[2], last[3]))
    return minds[at:at + n]
