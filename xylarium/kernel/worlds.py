"""
Xylarium worlds: a planet, its atmosphere and oceans, and the chemistry they allow - from physics alone.

The atmosphere is one layer deeper than the planet and is built the same way: what was gathered when the world formed,
plus what its interior gives up over deep time, less what escapes to space. What the world can host follows: which
of its volatiles is liquid at its pressure and temperature (a solvent), how much chemistry those conditions allow,
what energy reaches it, and how fast its reactions run. Nothing here is read off Earth; Earth is one input the
functions can be given (docs/FUNNEL.md, docs/CONSTANTS.md).

  TEMPERATURE   radiative equilibrium at the star's light over the orbit squared (Stefan-Boltzmann), for an albedo
                that comes from what covers the world (ice and cloud bright, rock and ocean dark).
  FORMATION     a volatile is part of the world where it formed colder than its condensation point (Lodders 2003):
                water inside a world beyond its snow line, ammonia, carbon dioxide, methane and nitrogen further
                out. Inside the snow line a rocky world gets its volatiles late, by impact: in proportion to the
                comet flux its galactic neighbourhood shakes loose (stellar density: flybys and the tide).
  OUTGASSING    a rocky world's interior gives up its volatiles over deep time as fast as its heat drives it.
  ESCAPE        Jeans: a gas of molecular mass mu stays if lambda = G M mu m_H / (k T_exo R) is large; a hot upper
                atmosphere (heated by its star's ultraviolet, fiercer around young and small stars) and a light world
                lose the light gases first; a world with no field is stripped harder.
  PRESSURE      the retained gas's weight over the surface: P = M_atm g / A.
  GREENHOUSE    the grey-atmosphere law T = T_eq (1 + 3/4 tau)^(1/4), tau rising as the square root of the greenhouse
                gases' pressure - one fit across Venus, Earth and Mars together (declared) - with water vapour at
                saturation (a warmer world holds more); the climate is the warmest stable balance (worlds begin hot),
                and a steam sky rains out into oceans unless the world absorbs more light than a moist atmosphere
                can radiate (the runaway limit, ~282 W/m^2: Nakajima et al. 1992). Where liquid water meets rock,
                weathering draws carbon dioxide into carbonate until it balances outgassing - a thermostat.
  SOLVENTS      a volatile is liquid between its triple point and its boiling curve (Clausius-Clapeyron from its
                normal boiling point and heat of vaporisation) up to its critical point; above both critical
                temperature and pressure it is a dense supercritical fluid. Under an ice shell a world's own heat may
                keep a liquid ocean. A giant's deep envelope is plasma; a world above ~1400 K has seas of melt.
  CHEMISTRY     a solvent, the bonds it allows (bond energy against kT: stable enough to hold, weak enough to remake),
                how many elements can join it, the energy reaching it (light through its sky, its world's heat,
                chemical gradients from outgassing), and its pace: Eyring kinetics with activation energy scaled to its
                solvent's own range (declared) - cold seas react slowly, hot ones fast.

The engine's five metabolisms are names for regions of this space: surface liquid under light (biotic); cold seas of
methane, nitrogen or ammonia, or water under ice (cryogenic); hot melt and supercritical fluids (mineral); a giant's
plasma (plasmic); a liquid in the dark, fed by its world's heat (umbral).
"""

import math
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------- physical constants (laws and units)
T_UNIT = 278.0                  # K at flux 1 and albedo 0 (laws.T_EARTH: a unit, the flux unit's temperature)
GM_OVER_R_UNIT = 6.26e7         # J/kg: G M / R for a body of unit mass and radius (an Earth's: a unit)
K_OVER_MH = 8254.0              # J/(kg K): Boltzmann over the hydrogen mass
G_UNIT_PA_PER_MASSFRAC = 1.17e11  # Pa: the weight per area of a unit mass fraction on a unit body (M g / 4 pi R^2)
BAR = 1.0e5                     # Pa
KB_EV = 8.617e-5                # eV/K

# condensation in the nebula (K; Lodders 2003 and ices), molecular mass, and the solvent's phase diagram:
# (triple T K, triple P bar, normal boiling T K, critical T K, critical P bar, heat of vaporisation kJ/mol)
VOLATILES = {
    "H2O": {"cond": 182.0, "mu": 18.0, "phase": (273.16, 0.0061, 373.1, 647.1, 220.6, 40.7), "greenhouse": True},
    "NH3": {"cond": 131.0, "mu": 17.0, "phase": (195.4, 0.0608, 239.8, 405.5, 113.5, 23.3), "greenhouse": True},
    "CO2": {"cond": 72.0, "mu": 44.0, "phase": (216.6, 5.18, 194.7, 304.1, 73.8, 16.7), "greenhouse": True},
    "CH4": {"cond": 41.0, "mu": 16.0, "phase": (90.7, 0.117, 111.7, 190.6, 46.0, 8.2), "greenhouse": True},
    "N2": {"cond": 22.0, "mu": 28.0, "phase": (63.2, 0.125, 77.4, 126.2, 34.0, 5.6), "greenhouse": False},
    "CO": {"cond": 25.0, "mu": 28.0, "phase": (68.1, 0.154, 81.6, 132.9, 35.0, 6.0), "greenhouse": False},
}
# ---------------------------------------------------------------------- the elements a disc offers (formation)
# Solar abundances, atoms per million silicon (Lodders 2003): the star's own, scaled by its metallicity.
ABUNDANCE = {"O": 1.41e7, "C": 7.19e6, "N": 1.95e6, "Mg": 1.02e6, "Si": 1.0e6, "Fe": 8.38e5, "S": 4.45e5,
             "Ni": 4.78e4, "Na": 5.75e4, "Cl": 5.24e3}
CARBON_AS = {"CO": 0.5, "CO2": 0.2, "CH4": 0.3}         # how a cooling nebula holds its carbon (declared)
NITROGEN_AS = {"NH3": 0.5, "N2": 0.5}                   # and its nitrogen (declared)


def _solids() -> Dict[str, float]:
    """Mass of each condensate per unit of rock-and-metal, from the abundances: metal (iron, nickel, sulphide) sinks
    to a core, silicate (magnesium and silicon with three oxygens) is the mantle, and the oxygen, carbon and nitrogen
    left over make the ices - so the ice-to-rock ratio is the abundances' own, not chosen."""
    a = ABUNDANCE
    core = 56 * a["Fe"] + 59 * a["Ni"] + 32 * a["S"]
    mantle = 24 * a["Mg"] + 28 * a["Si"] + 16 * 3 * a["Si"]
    rock = core + mantle
    o_left = a["O"] - 3 * a["Si"] - a["C"] * (CARBON_AS["CO"] + 2 * CARBON_AS["CO2"])
    ices = {"H2O": 18 * max(0.0, o_left), "CO2": 44 * a["C"] * CARBON_AS["CO2"], "CH4": 16 * a["C"] * CARBON_AS["CH4"],
            "CO": 28 * a["C"] * CARBON_AS["CO"], "NH3": 17 * a["N"] * NITROGEN_AS["NH3"],
            "N2": 28 * a["N"] * NITROGEN_AS["N2"] / 2}
    return {"core": core / rock, **{k: v / rock for k, v in ices.items()}}


SOLIDS = _solids()
ICE_PER_ROCK = {k: v for k, v in SOLIDS.items() if k != "core"}
COMET = {"H2O": 1.0, "CO2": 0.1, "CO": 0.1, "CH4": 0.01, "NH3": 0.01, "N2": 0.005}   # comets' ices by mass
                                # (Mumma & Charnley 2011): mostly water - what impacts bring across the snow line
PHOTOLYSIS_UV = 0.03 * 0.065 * 1.4   # bond-breaking light (flux units) above which an atmosphere's ammonia and
                                # methane are broken within years: 0.03 of a Sun-like star's light at its ~6.5%
                                # bond-breaking share and middle-aged activity (declared; Titan, at ~0.01, keeps its methane)
MMSN_ROCK = 7.1                 # g/cm^2 of rock at 1 AU around a Sun (Hayashi 1981): the disc's calibration (declared)
GIANT_IMPACT_GROWTH = 8.0       # how many isolation masses an inner planet gathers by giant impacts (Kokubo 2006; ~5-10)
CRITICAL_CORE = 10.0            # unit masses: a core this heavy captures the disc's gas (Mizuno 1980)
DISC_LIFE_MYR = 3.0             # how long a disc keeps its gas (observed disc lifetimes, a few Myr)
GROWTH_MYR_5AU = 1.0            # a critical core's growth time at 5 AU in a unit disc (declared; ~ a^2 / Sigma)
DELIVERED = 1.0e-4              # volatiles an impact-fed rocky world gets per unit comet flux (declared)
OUTGAS_GYR = 1.0                # e-folding of a rocky interior's outgassing at unit heat (declared)
STRIP_RATE = 2.0e-6             # air (mass fraction) a unit world's sky has broken per Gyr under unit wind (declared)
TRANSPORT_BAR = 0.1             # a sky this thick carries heat poleward about as fast as the poles radiate it (declared:
                                # thin skies collapse onto their poles, Wordsworth et al. 2015)
FRAGMENT = {"H2O": 1.0, "NH3": 1.0, "CH4": 1.0, "CO2": 16.0, "CO": 14.0, "N2": 14.0}   # the lightest piece light
                                # breaks each into (in proton masses): water, ammonia and methane lose hydrogen
STRIP_PASSES = (0.25, 1.0 / 3.0, 0.5, 1.0)   # the wind's dose spent in quarters, the climate settling between them
HOT_EV = 2.5                    # eV a fragment of a broken molecule flies with (dissociative recombination of O2+)
WEATHER_E_K = 11.5              # silicate weathering's e-fold in temperature: R T^2 / Ea, Ea ~ 60 kJ/mol (lab kinetics)
WEATHER_SCALE = 1.0e-3          # bar of CO2 at which unit outgassing balances weathering at water's triple point
                                # (declared: the carbonate-silicate cycle's one free number)
JEANS_HOLD = 15.0               # lambda above which a gas is held over Gyr (escape negligible); ~2 is blow-off
THERMOSPHERE = 4.0              # exobase over equilibrium temperature at quiet ultraviolet (declared)
RUNAWAY_FLUX = 282.0 / 340.0    # a moist atmosphere radiates at most ~282 W/m^2 (Nakajima et al. 1992); in flux units
                                # absorbed (unit flux = 340 W/m^2 averaged over a sphere)
GREENHOUSE_TAU = 6.4            # tau per sqrt(bar) of greenhouse gas at a bar of air (declared: Venus, Earth and Mars
BROADENING = 0.2                # together); absorption lines widen with the whole air's pressure, tau ~ P^0.2
MELT_K = 1400.0                 # rock melts
GIANT_PLASMA_MASS = 10.0        # unit masses: a world that holds a hydrogen envelope deep enough to ionise
SOLVENT_BARRIER = 25.0          # activation energy in units of k x the solvent's own mid-liquid temperature (declared)
BOND_EV = {"covalent": 3.6, "silicate": 4.6, "melt_network": 1.0}   # backbone bonds, a melt's network (eV)
STRONG_KT = 40.0                # a backbone must outlast a structure: bond energy over kT above ~40 (h/kT e^40 ~ years)
WEAK_KT = 10.0                  # weak bonds hold yet flex near ~10 kT (Trouton: every liquid at its boiling point)
GEO_FLUX = 0.087 / 340.0       # the unit of heat flow per area (0.087 W/m^2), in flux units (interior.py computes it)
HEAT_UNIT_W = 0.087 * 4.0 * math.pi * 6.371e6 ** 2   # the unit of a world's heat (W): the unit flow over a unit world
GIANT_FLUX = 5.4 / 340.0        # a giant of 318 unit masses' internal heat per area (contraction; declared scaling ~M)
PLASMA_WINDOW = 0.002           # how much structure ionised matter can hold, against a bonded chemistry's best (declared)
PHOTO_LOW = 0.4                 # a photon that lifts an electron in a bonded molecule carries ~0.4 of a covalent bond or
                                # more (conjugated molecules' excitation gaps; declared): below it, light only warms
UNIT_G = 9.81                   # m/s^2: the unit of surface gravity
SUN_LIFE_GYR = 10.0             # a sun's main-sequence life (creation.SUN_MS_GYR)
LATENT_ROCK = 4.0e5             # J/kg: latent heat of melting silicate
MAGMA_DEGAS = 0.9               # share of a melted mantle's volatiles a freezing magma ocean gives to the air
                                # (Elkins-Tanton 2008; declared)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _laws(laws: Any = None) -> Any:
    if laws is not None:
        return laws
    from xylarium.kernel import fundamental
    return fundamental.current()


def _phase_of(species: str, laws: Any = None):
    """A volatile's phase diagram under a universe's laws: its temperatures and heat of vaporisation scale with the
    chemistry's energy (the Rydberg), its pressures with condensed matter's (fundamental.py); our values for ours."""
    L = laws if laws is not None else _laws(None)
    got = L.memo.get(species)
    if got is None:
        tt, pt, tb, tc, pc, l_kj = VOLATILES[species]["phase"]
        c, p = L.chem, L.pressure
        got = L.memo[species] = (tt * c, pt * p, tb * c, tc * c, pc * p, l_kj * c, p)
    return got


# ---------------------------------------------------------------------- a world's state
def star_of(spec: Dict[str, Any], laws: Any = None) -> Dict[str, float]:
    """A star's mass, light and surface temperature from its spec (main sequence: R ~ M^0.8, in its universe's
    stellar scales: fundamental.py)."""
    from fractions import Fraction
    L = _laws(laws)
    m = float(Fraction(str(spec.get("mass", 1))))
    lum = float(Fraction(str(spec.get("luminosity", 1))))
    radius = max(0.08, m / L.star_mass) ** 0.8 * L.star_radius
    t_eff = 5772.0 * (max(1e-9, lum) / radius ** 2) ** 0.25
    return {"mass": m, "lum": lum, "t_eff": t_eff}


def activity(star_mass: float, age_gyr: float) -> float:
    """A star's ultraviolet activity relative to a quiet one: saturated while young, longer for small stars."""
    spin_down = max(0.05, star_mass) ** 2          # small stars stay active far longer
    return 1.0 + 9.0 * math.exp(-max(0.0, age_gyr) * spin_down)


def dose(star_mass: float, age_gyr: float) -> float:
    """The activity a world has been under from its star's birth to an age (Gyr x activity): its young star's fury
    counts for what it was, not for what the star is now."""
    k = max(0.05, star_mass) ** 2
    t = max(0.0, age_gyr)
    return t + 9.0 * (1.0 - math.exp(-t * k)) / k


def condensed(t_form: float, laws: Any = None) -> Dict[str, float]:
    """Ices a world forming at t_form gathers, per unit rock."""
    c = _laws(laws).chem
    return {s: ICE_PER_ROCK[s] for s, v in VOLATILES.items() if t_form < v["cond"] * c}


def boiling(species: str, p_bar: float, laws: Any = None) -> float:
    """The boiling temperature of a volatile at pressure p (Clausius-Clapeyron), capped at its critical point."""
    tt, pt, tb, tc, pc, l_kj, pref = _phase_of(species, laws)
    if p_bar <= 0:
        return tt
    inv = 1.0 / tb - 8.314 / (l_kj * 1000.0) * math.log(p_bar / pref)
    return min(tc, 1.0 / inv) if inv > 0 else tc


def phase(species: str, t: float, p_bar: float, laws: Any = None) -> str:
    """'solid', 'liquid', 'gas' or 'supercritical' at (t, p)."""
    tt, pt, tb, tc, pc, _, _ = _phase_of(species, laws)
    if t >= tc and p_bar >= pc:
        return "supercritical"
    if t < tt:
        return "solid"
    if p_bar < pt:
        return "gas"
    return "liquid" if t <= boiling(species, p_bar, laws) else "gas"


def isolation_mass(star_mass: float, a_au: float, z: float, enrich: float = 1.0) -> float:
    """Earth masses an embryo gathers from its feeding zone before it stops (Kokubo & Ida 2002): the disc's solids
    (MMSN_ROCK at 1 AU, falling as a^-3/2), metals and the ices beyond their lines."""
    sigma1 = MMSN_ROCK * max(0.0, z) * star_mass * enrich
    return 0.16 * (sigma1 / 10.0) ** 1.5 * a_au ** 0.75 * max(0.08, star_mass) ** -0.5


def form(star: Dict[str, Any], a_au: float, z: float, env: float, rng: Any, laws: Any = None) -> Dict[str, Any]:
    """A planet as its orbit built it: the solids its stretch of disc offered (rock and metal everywhere; each ice
    beyond its own line), gathered to the isolation mass (Kokubo & Ida 2002), grown by giant impacts, and - if its core
    passed the critical mass - wrapped in the disc's gas. Its layers settle by density: a metal core, a silicate
    mantle, ices above, an envelope over all. Inside the snow line its ices come late, by impact, as its galactic
    neighbourhood shakes comets loose. Radius follows from mass and layers."""
    L = _laws(laws)
    s = star_of(star, L)
    zz = max(0.0, z)
    t_form = T_UNIT * (s["lum"] / max(1e-6, a_au) ** 2) ** 0.25
    ices = {sp: f * zz for sp, f in ICE_PER_ROCK.items() if t_form < VOLATILES[sp]["cond"] * L.chem}
    if "H2O" not in ices:                                # what comets bring across the snow line
        late = DELIVERED * env * zz
        ices = {sp: f * late for sp, f in COMET.items()}
        enrich = 1.0
    else:
        enrich = 1.0 + sum(ices.values())               # ices thicken the disc's solids beyond their lines
    m_iso = isolation_mass(s["mass"], a_au, zz, enrich)
    sigma1 = MMSN_ROCK * zz * s["mass"] * enrich         # the disc's solids normalised at 1 AU (falling as a^-3/2)
    core = m_iso * GIANT_IMPACT_GROWTH * math.exp(rng.gauss(0.0, 0.5))    # the luck of collisions
    envelope = 0.0
    # a core captures gas only if it reached the critical mass before the disc dispersed: growth slows steeply
    # outward (longer orbits, thinner disc), so far cores stay ice giants
    grow = GROWTH_MYR_5AU * (a_au / 5.0) ** 2 / max(1e-6, sigma1 / 10.0)
    if core >= CRITICAL_CORE and rng.random() < math.exp(-grow / DISC_LIFE_MYR):
        envelope = core * 10.0 ** (rng.random() * 1.5) * min(1.0, s["mass"])   # what gas the disc still had
    total = core + envelope
    ice_share = sum(ices.values()) / (1.0 + sum(ices.values()))
    squeeze = L.density ** (-1.0 / 3.0)                  # denser matter, smaller worlds of a mass
    if envelope > 0:
        radius = (11.0 * (1.0 - math.exp(-total / 30.0)) + core ** 0.27) * squeeze
    else:
        radius = core ** 0.27 * (1.0 + 0.4 * ice_share) * squeeze   # rock and metal ~ M^0.27; ices are puffier
    return {"mass": total, "radius": radius, "giant": envelope > 0, "ices": ices,
            "layers": {"core": SOLIDS["core"] * (1 - ice_share) * core / total,
                       "mantle": (1 - SOLIDS["core"]) * (1 - ice_share) * core / total,
                       "ices": ice_share * core / total, "envelope": envelope / total}}


YIELD_PA = {"rock": 1.0e8, "ice": 1.0e7}      # what rock and ice bear before they flow (Pa; the strength of cold
                                              # rock and of ice: measured)


def is_world(mass: float, radius: float, icy: bool, laws: Any = None) -> bool:
    """A world is a body its own gravity has pulled round: the pressure at its centre, (2 pi / 3) G rho^2 R^2, beyond
    what its rock (or ice) can bear. Smaller bodies keep the shapes they were broken into - rubble in the system's
    belts, not worlds. (Round from ~300 km across for rock and ice alike.)"""
    from xylarium.kernel import interior
    m = float(mass) * interior.M_EARTH_KG
    r = float(radius) * interior.R_EARTH_M
    if m <= 0.0 or r <= 0.0:
        return False
    rho = m / (4.0 / 3.0 * math.pi * r ** 3)
    strength = YIELD_PA["ice" if icy else "rock"] * _laws(laws).chem   # bonds scale with the universe's chemistry
    return 2.0 * math.pi / 3.0 * interior.G_SI * rho * rho * r * r >= strength


def label(w: Dict[str, Any]) -> str:
    """The display name of a world, from what it is."""
    if w["giant"]:
        return "GAS_GIANT"
    if w["flux"] < 1.0 / 400.0:
        return "ROGUE"
    if w["t_surf"] > 600.0:
        return "VOLCANIC"
    if "H2O" in w["seas"] and phase("H2O", w["t_surf"], max(w["p_bar"], 1e-9)) == "liquid":
        return "OCEANIC" if w["seas"]["H2O"] > 500.0 else "TERRESTRIAL"
    if w["seas"]:
        return "ICE"
    return "BARREN"


def build(seed: Any, star: Dict[str, Any], a_au: float, radius: float, mass: float, giant: bool, z: float,
          r_kpc: float, age_gyr: float, ices: Optional[Dict[str, float]] = None, born: Optional[float] = None,
          orbit: Optional[Dict[str, Any]] = None, core: Optional[float] = None) -> Dict[str, Any]:
    """The world as physics makes it at an age: its formation, interior, atmosphere and oceans, temperature and field.
    orbit (orbits.py) carries its host and elements: its eccentricity (the light it gets over a year, and the tides
    that heat it); born, its star's birth (the isotopes its rock was made with: interior.py)."""
    from xylarium.kernel import cosmos, fundamental, interior, orbits
    L = fundamental.of(seed) if seed is not None else _laws(None)
    s = star_of(star, L)
    e_now = 0.0
    if orbit:
        e_now = orbits.eccentricity(orbit["el"]["e0"], orbit["el"]["e_forced"], orbit["el"]["tau_e"], age_gyr)
    # a star brightens through its main sequence as its core's helium raises its weight per particle (Gough 1981): a
    # star's mass-light relation is read at 46% of its life (the Sun's now)
    life = SUN_LIFE_GYR * L.nuclear * s["mass"] / max(1e-9, s["lum"])
    bright = 1.0 / (1.0 + 0.4 * (1.0 - min(1.0, max(0.0, age_gyr) / life) / 0.46))
    flux = bright * s["lum"] / max(1e-6, a_au) ** 2 / math.sqrt(max(1e-6, 1.0 - e_now * e_now))   # a year's mean
    t_form = T_UNIT * (s["lum"] / max(1e-6, a_au) ** 2) ** 0.25    # the nebula's temperature where it formed
    env = cosmos.density(r_kpc)                                 # its neighbourhood: flybys, the tide, supernovae
    zz = max(0.0, z)
    if ices is None:                                           # a world laid out before formation was physics
        ices = {k: v * zz for k, v in condensed(t_form, L).items()}
        if not giant and "H2O" not in ices:
            ices = {sp: f * DELIVERED * env * zz for sp, f in COMET.items()}
    t_eq0 = T_UNIT * flux ** 0.25 * 0.7 ** 0.25
    if giant:                                           # an envelope with no surface: its cloud tops
        return {"flux": flux, "t_form": round(t_form, 1), "t_surf": round(t_eq0, 1), "p_bar": 1.0e3, "air": {},
                "seas": {}, "ices": ices, "heat": 0.0, "q": 0.0, "field": 0.0, "giant": True, "mass": mass,
                "radius": radius, "env": env, "star_t": s["t_eff"], "albedo": 0.3, "light": 0.0, "e": round(e_now, 4),
                "laws": L}
    # the interior: isotopes from its star's birth, warmth from its formation, tides from its host
    ice_share = sum(ices.values()) / (1.0 + sum(ices.values()))
    core = SOLIDS["core"] * (1.0 - ice_share) if core is None else core
    inv = interior.inventory(seed if born is not None else None, r_kpc,
                             born if born is not None else interior.SUN_BORN_GYR, zz, L)
    tide = None
    if orbit and orbit.get("host_kg"):
        el, host, a_m, icy = orbit["el"], orbit["host_kg"], orbit["a_m"], ice_share > 0.2
        tide = lambda t: interior.tidal_w(host, a_m, orbits.eccentricity(el["e0"], el["e_forced"], el["tau_e"], t),
                                          mass, radius, icy)
    inside = interior.evolve(mass, radius, core, inv, age_gyr, t_eq0, tide, ice_share > 0.2, L)
    heat = inside["heat_w"] / HEAT_UNIT_W                       # in units of a unit world's heat
    # degassed: what its magma ocean gave up as it froze - the share of the mantle its accretion melted, (3/5) G M / R
    # against the heat and latent heat that melts rock - then what its convecting heat has melted since
    accreted = 0.6 * GM_OVER_R_UNIT * mass / max(1e-6, radius)
    melted = min(1.0, accreted / (interior.CP_ROCK * interior.LIQUIDUS_K * L.chem + LATENT_ROCK * L.chem))
    out = 1.0 - (1.0 - MAGMA_DEGAS * melted) * math.exp(-inside["processed"])
    field = inside["field"]
    # escape: a hot exosphere under its star's ultraviolet, on a world of this mass and radius
    t_exo = THERMOSPHERE * t_eq0 * activity(s["mass"] / L.star_mass, age_gyr) ** 0.5 * (1.0 if field > 0 else 1.5)
    gm_r = GM_OVER_R_UNIT * mass / max(1e-6, radius)
    gas: Dict[str, float] = {}
    for sp, frac in ices.items():
        lam = gm_r * VOLATILES[sp]["mu"] / (K_OVER_MH / L.proton * max(1.0, t_exo))
        held = _clamp((lam - 2.0) / (JEANS_HOLD - 2.0))          # blow-off below ~2, held above ~15
        gas[sp] = frac * out * held
    uv = flux * band(s["t_eff"], L)["break"] * activity(s["mass"] / L.star_mass, age_gyr)
    if uv > PHOTOLYSIS_UV:                             # starlight's ultraviolet: nitrogen ends as N2, carbon as CO2
        for sp, to, ratio in (("NH3", "N2", 28.0 / 34.0), ("CH4", "CO2", 44.0 / 16.0), ("CO", "CO2", 44.0 / 28.0)):
            if sp in gas:
                gas[to] = gas.get(to, 0.0) + gas.pop(sp) * ratio
    # the star's wind and ultraviolet break molecules high in the air, and what they break flies off with a few eV (the
    # energy dissociative recombination releases - a chemistry energy); a product escapes if that beats its weight's
    # binding, mu m_H v_esc^2 / 2 (photochemical escape): light worlds lose their air, heavy ones keep it - lightest
    # gases first, a thick atmosphere losing a little, a thin one all
    wind = STRIP_RATE * flux * dose(s["mass"] / L.star_mass, age_gyr) / max(1e-6, mass)
    bind_ev = gm_r * 2.0 * 1.6726e-27 * L.proton / 1.602e-19       # per m_H: mu m_H v_esc^2 / 2 = mu m_H G M / R
    g = mass / max(1e-6, radius) ** 2
    to_bar = G_UNIT_PA_PER_MASSFRAC * mass * g / max(1e-6, radius) ** 2 / BAR
    hpm = heat / max(1e-6, mass)
    budget = [wind]

    def strip(air_now: Dict[str, float], share: float) -> None:
        """The wind breaks the molecules standing in the air in proportion to their share of it; the fragments fast
        enough fly off (the lightest most easily), and the molecule is gone from the world's inventory."""
        total = sum(air_now.values())
        spend = budget[0] * share
        if total <= 0 or spend <= 0:
            return
        for sp, pp in air_now.items():
            if sp not in gas:
                continue
            broken = spend * pp / total
            escape = math.exp(-bind_ev * FRAGMENT.get(sp, VOLATILES[sp]["mu"] / 2.0) / (HOT_EV * L.chem))
            gas[sp] -= min(gas[sp], pp / max(1e-12, to_bar), broken * escape)
        budget[0] -= spend
    obliquity = orbit["obliquity"] if orbit and orbit.get("obliquity") is not None else math.pi / 4.0
    held0 = sum(gas.values())                           # what it held before the wind broke any of it
    t_surf, p_bar, air, seas, albedo = _climate(gas, to_bar, flux, hpm, giant, L, obliquity)
    air0 = sum(air.values())                            # the standing air before the wind took any of it
    lightest = min((FRAGMENT.get(sp, VOLATILES[sp]["mu"] / 2.0) for sp in gas), default=1.0)
    reach = wind * math.exp(-bind_ev * lightest / (HOT_EV * L.chem))      # the most the wind could take
    for share in STRIP_PASSES:
        # what the climate holds aloft is what the wind can reach - a steam sky loses its hydrogen to space, and with
        # it its water; a thin sky goes whole - and the climate settles again on what is left
        if budget[0] <= 0 or not air or reach < 1e-4 * sum(gas.values()):
            break
        strip(air, share)
        t_surf, p_bar, air, seas, albedo = _climate(gas, to_bar, flux, hpm, giant, L, obliquity)
    return {"flux": flux, "t_form": round(t_form, 1), "t_surf": round(t_surf, 1), "p_bar": p_bar, "air": air,
            "seas": seas, "ices": ices, "heat": heat, "q": inside["q"], "q_tide": inside["q_tide"],
            "t_int": inside["t_int"], "field": round(field, 3), "giant": giant, "mass": mass, "radius": radius,
            "melted": melted, "processed": inside["processed"], "degassed": out, "wind": wind, "t_exo": t_exo,
            "escaped": round(1.0 - sum(gas.values()) / held0, 6) if held0 > 0 else 0.0,
            "air_escaped": round(max(0.0, 1.0 - p_bar / air0), 6) if air0 > 0 else 0.0,
            "env": env, "star_t": s["t_eff"], "albedo": round(albedo, 3), "e": round(e_now, 4), "g": g,
            "light": flux * (1.0 - albedo) * math.exp(-0.1 * p_bar ** 0.5), "laws": L}   # what reaches the surface


def saturation(species: str, t: float, laws: Any = None) -> float:
    """Vapour pressure over a volatile's liquid or ice at t (Clausius-Clapeyron from its triple point), bar."""
    tt, pt, _, _, _, l_kj, _ = _phase_of(species, laws)
    return pt * math.exp(l_kj * 1000.0 / 8.314 * (1.0 / tt - 1.0 / max(1.0, t)))


def _state(gas: Dict[str, float], to_bar: float, t: float, hpm: float, giant: bool, laws: Any = None):
    """The air and seas a world would have at surface temperature t."""
    L = _laws(laws)
    inv = {sp: f * to_bar for sp, f in gas.items()}
    air: Dict[str, float] = {}
    seas: Dict[str, float] = {}
    for sp, pp in inv.items():
        if sp in ("H2O", "NH3", "CH4", "CO2", "N2"):
            vap = min(pp, saturation(sp, t, L))         # what the air holds of it at saturation
            if vap > 0:
                air[sp] = vap
            if pp - vap > 0:
                seas[sp] = pp - vap
    p = sum(air.values())
    wet = "H2O" in seas and phase("H2O", t, max(p, 1e-9), L) == "liquid" and not giant
    if wet and "CO2" in air:
        # the carbonate-silicate cycle: where liquid water meets rock, weathering turns CO2 to carbonate until it
        # balances what the interior outgasses - faster the warmer (Walker, Hays & Kasting 1981)
        balance = WEATHER_SCALE * hpm ** 2 * math.exp(-2.0 * (t - _phase_of("H2O", L)[0]) / (WEATHER_E_K * L.chem))
        air["CO2"] = min(air["CO2"], max(1e-6, balance))
        seas.pop("CO2", None)                           # the rest is carbonate rock, not a sea
    return air, seas


def polar_share(obliquity: float) -> float:
    """A pole's year-round sunlight over the world's mean: 4 sin(obliquity) / pi (none for an upright world)."""
    return min(1.0, 4.0 * abs(math.sin(obliquity)) / math.pi)


def _cold_trap(air: Dict[str, float], seas: Dict[str, float], t: float, obliquity: float, laws: Any) -> None:
    """A world is not one temperature: its poles are colder by as much as its sky fails to carry heat to them (a
    thick sky evens them out). A gas whose frost point the pole is below freezes there - the air holds no more of it
    than the pole's ice allows (Mars's carbon dioxide caps)."""
    p = sum(air.values())
    carry = p / TRANSPORT_BAR
    t_pole = t * ((polar_share(obliquity) + carry) / (1.0 + carry)) ** 0.25
    for sp in ("CO2", "N2", "CH4", "NH3"):
        if sp in air:
            cap = saturation(sp, t_pole, laws)
            if air[sp] > cap:
                seas[sp] = seas.get(sp, 0.0) + air[sp] - cap      # frozen at the pole
                air[sp] = cap


def _climate(gas: Dict[str, float], to_bar: float, flux: float, hpm: float, giant: bool, laws: Any = None,
             obliquity: float = math.pi / 4.0):
    """Surface temperature, pressure, air, seas and albedo: the warmest stable state (worlds begin hot) at which
    the temperature the atmosphere makes is the temperature it was assumed at."""
    L = _laws(laws)
    runaway = RUNAWAY_FLUX * L.chem ** 4                # a moist sky's limit is water's own radiating temperature
    opacity = L.atom ** 2                               # molecules' cross-sections grow as atoms do

    def model(t: float):
        air, seas = _state(gas, to_bar, t, hpm, giant, L)
        _cold_trap(air, seas, t, obliquity, L)
        icy = sum(v for sp, v in seas.items() if t < _phase_of(sp, L)[0])
        albedo = 0.3 + 0.4 * _clamp(icy / (icy + 1.0)) if icy else 0.3
        gh = sum(v for sp, v in air.items() if VOLATILES[sp]["greenhouse"])
        t_eq = T_UNIT * flux ** 0.25 * (1.0 - albedo) ** 0.25
        tau = GREENHOUSE_TAU * math.sqrt(gh * opacity) * max(1e-9, sum(air.values())) ** BROADENING
        return t_eq * (1.0 + 0.75 * tau) ** 0.25, air, seas, albedo
    base = T_UNIT * flux ** 0.25 * 0.3 ** 0.25                # the coldest it could be: a bright, bare world
    grid = [max(15.0, base) * 1.08 ** i for i in range(40)]   # up to ~20x that: the thickest greenhouse
    vals = [model(t)[0] - t for t in grid]
    root = None
    for i in range(len(grid) - 1, 0, -1):                   # the warmest crossing from warming to cooling
        if vals[i - 1] >= 0 > vals[i]:
            _, _, seas_i, alb_i = model(grid[i])
            if gas.get("H2O", 0) > 0 and "H2O" not in seas_i and flux * (1.0 - alb_i) < runaway:
                continue                                    # below the runaway limit a steam sky rains out
            lo, hi = grid[i - 1], grid[i]
            for _ in range(16):
                mid = (lo + hi) / 2
                if model(mid)[0] - mid >= 0:
                    lo = mid
                else:
                    hi = mid
            root = hi                    # the cooling side: at a thermostat's pin (ice melting, weathering starting),
            break                        # the world sits liquid with what weathering leaves in its air
    if root is None:
        root = grid[0] if vals[0] < 0 else grid[-1]
    t, air, seas, albedo = model(root)
    return root, sum(air.values()), air, seas, albedo


# ---------------------------------------------------------------------- light by its colours
def planck_above(x: float) -> float:
    """The share of a black body's energy carried by photons above x kT."""
    if x <= 0:
        return 1.0
    if x > 60:
        return 0.0
    s = 0.0
    for n in range(1, 40):
        e = math.exp(-n * x)
        s += e * (x ** 3 / n + 3 * x * x / n ** 2 + 6 * x / n ** 3 + 6 / n ** 4)
        if e < 1e-12:
            break
    return min(1.0, 15.0 / math.pi ** 4 * s)


def band(t_eff: float, laws: Any = None) -> Dict[str, float]:
    """Starlight's colours against chemistry's: the share of a star's light whose photons can drive chemistry -
    enough to lift an electron (PHOTO_LOW of a covalent bond) but not enough to break one - and the share that
    breaks bonds (ultraviolet). Both bonds scale with the chemistry's energy (fundamental.py)."""
    bond = BOND_EV["covalent"] * _laws(laws).chem
    kt = KB_EV * max(1.0, t_eff)
    hi = planck_above(bond / kt)
    return {"drive": max(0.0, planck_above(PHOTO_LOW * bond / kt) - hi), "break": hi}


# ---------------------------------------------------------------------- chemistry from the world
def geothermal(w: Dict[str, Any]) -> float:
    """The world's own heat flowing out through each unit of its surface, in flux units (its heat over its area)."""
    return GEO_FLUX * w["heat"] / max(1e-6, w["radius"]) ** 2


def free_heat(w: Dict[str, Any], t_medium: float) -> float:
    """The work the world's heat can do for a chemistry at t_medium (flux units): its flow out through each unit of
    surface x Carnot's share between its interior and the medium."""
    t_hot = max(t_medium, float(w.get("t_int") or t_medium))
    return geothermal(w) * (1.0 - t_medium / max(1.0, t_hot))


def solvents(w: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every medium on the world a chemistry could run in, with its temperature and the free energy that reaches it
    (per unit area, in flux units: starlight of the colours that drive chemistry, through its sky; the work its own
    heat can do; a giant's slow contraction)."""
    from xylarium.kernel import interior
    L = w.get("laws") or _laws(None)
    out: List[Dict[str, Any]] = []
    t, p = w["t_surf"], max(w["p_bar"], 1e-9)
    drive = band(w.get("star_t", 5772.0), L)["drive"]
    light = w["light"] * drive
    for sp, amount in w["seas"].items():
        ph = phase(sp, t, p, L)
        if ph == "liquid" or ph == "supercritical":
            out.append({"solvent": sp, "where": "surface", "t": t, "energy": light + free_heat(w, t),
                        "amount": amount, "dark": False})
        elif ph == "solid" and sp in ("H2O", "NH3") and not w["giant"]:
            # a liquid ocean under an ice shell, where the world's heat (and tides) keep the shell's base melted: the
            # shell a heat flow can hold is thinner than the ice there is (water's ice; ammonia an antifreeze)
            t_under = _phase_of(sp, L)[0] + (5.0 * L.chem if sp == "H2O" else 0.0)
            layer_km = amount * BAR / (UNIT_G * max(1e-6, w.get("g", 1.0)) * 1000.0) / 1000.0
            q = float(w.get("q") or geothermal(w) * 340.0)
            if interior.shell_km(q, t, t_under) < layer_km:
                out.append({"solvent": sp, "where": "under_ice", "t": t_under, "energy": free_heat(w, t_under),
                            "amount": amount, "dark": True})
    for sp, pp in w["air"].items():
        if phase(sp, t, p, L) == "supercritical":
            out.append({"solvent": sp, "where": "supercritical", "t": t, "energy": light + free_heat(w, t),
                        "amount": pp, "dark": False})
    if not w["giant"] and t >= MELT_K * L.chem:
        out.append({"solvent": "melt", "where": "surface", "t": t, "energy": light + geothermal(w), "amount": 1.0,
                    "dark": False})
    if w["giant"] and w["mass"] >= GIANT_PLASMA_MASS:
        out.append({"solvent": "plasma", "where": "deep", "t": 1.0e4 * L.chem,
                    "energy": GIANT_FLUX * (w["mass"] / 318.0) * (11.0 / max(1.0, w["radius"])) ** 2,
                    "amount": 1.0, "dark": True})
    return out


def _mid(solvent: str, laws: Any = None) -> float:
    """The middle of a solvent's own liquid range (K)."""
    c = _laws(laws).chem
    if solvent == "melt":
        return 2000.0 * c
    if solvent == "plasma":
        return 1.0e4 * c
    tt, _, tb, tc, _, _, _ = _phase_of(solvent, laws)
    top = tb if tb > tt else tc                         # a solvent that sublimes at 1 bar is liquid only under pressure
    return (tt + min(top, tc)) / 2.0


def pace(solvent: str, t: float, laws: Any = None) -> float:
    """How fast a chemistry runs, relative to the unit temperature (Eyring: kT/h x exp(-Ea/kT), Ea scaled to its
    solvent's range): at the middle of its range a chemistry runs as its mid temperature over the unit; within its
    range, faster when warmer."""
    mid = _mid(solvent, laws)
    if solvent in VOLATILES:
        tt, _, _, tc, _, _, _ = _phase_of(solvent, laws)
        if t > tc:                                       # a supercritical fluid runs at its own temperature
            return t / T_UNIT
        t = max(tt, t)
    return (t / T_UNIT) * math.exp(SOLVENT_BARRIER * (1.0 - mid / max(1.0, t)))


def body_temperature(solvent: str, laws: Any = None) -> float:
    """A minded body keeps itself where its chemistry works best: the middle of its solvent's own liquid range
    (a bonded chemistry's thermostat; its world's weather is outside it)."""
    return _mid(solvent, laws)


def body_pace(solvent: str, laws: Any = None) -> float:
    """The pace of a body held at its chemistry's best (Eyring at the middle of its range: its temperature over the
    unit's)."""
    return body_temperature(solvent, laws) / T_UNIT


def region(m: Dict[str, Any], laws: Any = None) -> str:
    """The engine's name for a medium's region of chemistry space."""
    c = _laws(laws).chem
    s = m["solvent"]
    if s == "plasma":
        return "plasmic"
    if s == "melt" or m["where"] == "supercritical" or m["t"] > 450.0 * c:
        return "mineral"
    if m["dark"] and m["where"] == "under_ice" and s == "H2O":
        return "umbral"
    if m["t"] < 230.0 * c or s in ("CH4", "N2", "NH3"):
        return "cryogenic"
    return "biotic" if not m["dark"] else "umbral"


def weak_bond_ev(solvent: str, laws: Any = None) -> float:
    """The solvent's cohesion per molecule (eV): its heat of vaporisation over Avogadro (a melt's network bond)."""
    if solvent == "melt":
        return BOND_EV["melt_network"] * _laws(laws).chem
    if solvent == "plasma":
        return 0.0
    return _phase_of(solvent, laws)[5] * 1000.0 / 96485.0


def richness(w: Dict[str, Any], m: Dict[str, Any], z: float) -> float:
    """How much chemistry the medium allows, 0 .. 1: the elements that can join it (metals, carbon, nitrogen, the
    solvent's own) x a bond hierarchy - strong bonds that outlast a structure (bond energy over kT above ~40: a
    backbone's lifetime (h/kT) e^(E/kT) beyond years) and weak bonds that hold yet flex, on the solvent's own
    cohesion (its heat of vaporisation per molecule over kT near ~10 - Trouton's rule puts every liquid near its
    boiling point there, so any solvent inside its own liquid range has them; a fluid far above its critical point
    does not)."""
    L = w.get("laws") or _laws(None)
    t = max(1.0, m["t"])
    elements = 1.0 + min(1.0, z) + (1.0 if w["ices"].get("CO2") or w["ices"].get("CH4") else 0.0) + \
        (1.0 if w["ices"].get("NH3") or w["ices"].get("N2") or "N2" in w["air"] else 0.0)
    if m["solvent"] == "plasma":
        return _clamp(elements / 4.0) * PLASMA_WINDOW    # ionised matter holds no bonds: structure in fields
    strong_ev = (BOND_EV["silicate"] if m["solvent"] == "melt" else BOND_EV["covalent"]) * L.chem
    strong = 1.0 / (1.0 + math.exp(-(strong_ev / (KB_EV * t) - STRONG_KT) / 4.0))
    weak = math.exp(-((math.log(weak_bond_ev(m["solvent"], L) / (KB_EV * t)) - math.log(WEAK_KT)) / 0.6) ** 2)
    return _clamp(elements / 4.0) * strong * weak


def media(seed: Any, star: Dict[str, Any], a_au: float, radius: float, mass: float, giant: bool, z: float,
          r_kpc: float, age_gyr: float, ices: Optional[Dict[str, float]] = None,
          world: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Every chemistry the world allows, with its region, richness, energy and pace."""
    w = world or build(seed, star, a_au, radius, mass, giant, z, r_kpc, age_gyr, ices)
    L = w.get("laws") or _laws(None)
    out = []
    for m in solvents(w):
        m = dict(m, region=region(m, L), richness=round(richness(w, m, z), 4),
                 pace=round(pace(m["solvent"], m["t"], L), 4))
        out.append(m)
    return out


HISTORY_GYR = (0.3, 0.6, 1.0, 1.5, 2.0, 3.0, 4.5, 6.0, 8.0, 10.0)   # ages a world's history is read at (Gyr after
                                                                    # its star's birth)


def history(seed: Any, star: Dict[str, Any], a_au: float, radius: float, mass: float, giant: bool, z: float,
            r_kpc: float, ices: Optional[Dict[str, float]] = None, born: Optional[float] = None,
            orbit: Optional[Dict[str, Any]] = None, core: Optional[float] = None,
            ages: Any = HISTORY_GYR) -> List[Dict[str, Any]]:
    """A world through time - not one settled moment: at each age its interior (hotter young, cooling), its air (what
    its heat has outgassed, less what its star's fiercer youth has stripped), its climate and seas, and the media its
    chemistry could run in. A world can be green once and frozen later, or the other way about; each age is the same
    physics read at another time (build), with the star's own light at that age where the star swells (its main
    sequence brightening is the caller's: lum_at)."""
    out = []
    for age in ages:
        w = build(seed, star, a_au, radius, mass, giant, z, r_kpc, age, ices, born=born, orbit=orbit, core=core)
        ms = media(seed, star, a_au, radius, mass, giant, z, r_kpc, age, world=w)
        out.append({"age": age, "t_surf": w["t_surf"], "p_bar": w["p_bar"], "field": w["field"], "q": w.get("q", 0.0),
                    "air": dict(w["air"]), "seas": dict(w["seas"]), "media": ms,
                    "green": any(m["region"] == "biotic" for m in ms)})
    return out


def windows(hist: List[Dict[str, Any]], key: str = "green") -> List[List[float]]:
    """The spans of a world's history (Gyr after its star's birth) in which a state held: e.g. when it was green."""
    spans: List[List[float]] = []
    prev = None
    for n, h in enumerate(hist):
        if h[key]:
            start = h["age"] if n == 0 else (hist[n - 1]["age"] + h["age"]) / 2.0
            if prev is None or not hist[n - 1][key]:
                spans.append([start, h["age"]])
            spans[-1][1] = h["age"] if n == len(hist) - 1 else (h["age"] + hist[n + 1]["age"]) / 2.0
        prev = h
    return spans


def best(ms: List[Dict[str, Any]], metabolism: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """The richest medium (of a region, if asked)."""
    cands = [m for m in ms if metabolism is None or m["region"] == metabolism]
    return max(cands, key=lambda m: (m["richness"] * min(1.0, m["energy"]), m["solvent"])) if cands else None


def fit(ms: List[Dict[str, Any]], metabolism: str) -> float:
    """How well a world suits a region's chemistry, 0 .. 1 - what the hand-written habitability table was."""
    m = best(ms, metabolism)
    if m is None:
        return 0.0
    return _clamp(m["richness"] * (1.0 - math.exp(-m["energy"] / 0.1)))


# ---------------------------------------------------------------------- a planet in play
_STATES: Dict[Any, Any] = {}
AGE_STEP_GYR = 0.25             # a world in play is re-read as its star and interior age, a quarter-Gyr at a time


def world_age(kernel: Any, planet: Any) -> float:
    """The age a world in play is read at: in a universe begun at its Big Bang, its star's own age now (its light
    brightened, its interior cooled, its air gathered and lost since); elsewhere the settled age."""
    from xylarium.kernel import cosmos, creation
    if kernel is None or not cosmos.is_cosmic(kernel):
        return creation.SETTLED_GYR
    g = cosmos.stats(kernel)["place"].get(str(planet.sector_id), {})
    if "born" not in g:
        return creation.SETTLED_GYR
    age = cosmos.deep_gyr(kernel, sector_id=planet.sector_id) - float(g["born"])   # its place's own now
    return max(creation.CRUST_GYR, round(age / AGE_STEP_GYR) * AGE_STEP_GYR)


def state_of_planet(kernel: Any, planet: Any) -> Dict[str, Any]:
    """The world as physics makes it now (build): its air, seas, temperature, heat - for what acts on it in play."""
    from xylarium.kernel import cosmos, creation, physics
    sec = kernel.sectors.get(planet.sector_id) if kernel is not None else None
    g = cosmos.stats(kernel)["place"].get(str(planet.sector_id), {}) if kernel is not None and cosmos.is_cosmic(
        kernel) else {}
    b = physics.body(planet)
    age = world_age(kernel, planet)                      # its star's age now: the world as it has become
    swell = cosmos.lum(planet.sector_id) if kernel is not None and cosmos.is_cosmic(kernel) else 1.0
    seed = creation.universe(kernel) if kernel is not None else None
    key = (seed, planet.id, round(age, 2), planet.planet_type, round(swell, 3), str(b.get("radius")))
    got = _STATES.get(planet.id)
    if got and got[0] == key:
        return got[1]
    star = dict(getattr(sec, "star", None) or physics.star_for(getattr(sec, "star_type", None)))
    if swell != 1.0:                                     # its star as it shines now: a giant's glare boils its seas
        from fractions import Fraction
        star["luminosity"] = str(Fraction(star["luminosity"]) * Fraction(swell).limit_denominator(10 ** 6))
    z = creation.metals_at(seed, float(g.get("r", cosmos.R0_KPC)), float(g.get("born", 9.2))) if g else 1.0
    ices, make = None, {}
    if g and "cell" in g and sec is not None and planet in sec.planets:   # the world its orbit built (creation)
        made = creation.cell(seed, *g["cell"])[g["k"]].get("worlds") or []
        n = sec.planets.index(planet)
        if n < len(made):
            ices, make = made[n].get("ices"), made[n].get("make") or {}
    args = (seed, star, float(b.get("q", 1)) ** 2, float(b.get("radius", 1)), float(b.get("mass", 1)),
            bool(b.get("giant")), z, float(g.get("r", cosmos.R0_KPC)), age, ices)
    w = build(*args, born=make.get("born"), orbit=make.get("orbit"), core=make.get("core"))
    out = {"world": w, "media": media(*args, world=w), "key": [age, planet.planet_type, round(swell, 3)],
           "args": args, "make": make}
    _STATES[planet.id] = (key, out)
    return out


def of_planet(kernel: Any, planet: Any) -> List[Dict[str, Any]]:
    """The media of a planet on the map (cached on the world: its physics changes on deep time only)."""
    from xylarium.kernel import cosmos
    age = world_age(kernel, planet)
    swell = cosmos.lum(planet.sector_id) if kernel is not None and cosmos.is_cosmic(kernel) else 1.0
    key = (round(age, 2), planet.planet_type, round(swell, 3))
    cache = planet.society.get("_media")
    if cache and tuple(cache.get("key", ())) == key:
        return cache["media"]
    ms = state_of_planet(kernel, planet)["media"]
    planet.society["_media"] = {"key": list(key), "media": ms}
    return ms
