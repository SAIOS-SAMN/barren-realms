"""
Xylarium interior: the heat a world makes and loses - radioactive decay, the warmth it formed with, and the tides
its host raises in it - and what that heat does: drive its volcanoes, its magnetic field, the seas under its ice,
and the life that runs on its warmth in the dark.

RADIOGENIC. Uranium-238 and -235, thorium-232 and potassium-40 heat a rocky mantle as they decay. A world gets the
inventory its star's gas held when the star was born: what the ring's stars had made by then (the age-metallicity
relation), spread by mass (heavy uranium and thorium stay near the core: cosmos.abundance), and decayed since it
was made (each isotope's made over the ring's star-formation history, decaying all the while - a young galaxy is
rich in short-lived uranium-235 and potassium-40). The rulers are the bulk silicate Earth's measured abundances and
heat per kilogram, read back to the Sun's birth (Turcotte & Schubert 2002) - a measurement at one place and time,
not a template: every other world's inventory is computed from its own birth. An alpha decay's half-life rides on
its Gamow barrier, which scales with alpha (fundamental.py): a universe with stronger electromagnetism keeps its
uranium far longer and is warmed less by it.

SECULAR COOLING. A world forms hot - its rock crystallised from a magma ocean at its liquidus - and cools by
mantle convection: the heat a convecting layer passes is k dT (rho g alpha_th dT / (kappa eta Ra_c))^(1/3) per area
(boundary-layer theory: independent of the layer's depth), and its viscosity falls steeply with temperature
(Arrhenius creep) - a thermostat that holds a mantle near the temperature at which it passes its heat. Small worlds
hold little heat and cool soonest.

TIDES. A host flexes a world on an eccentric orbit: (21/2) (k2 / Q) G M^2 R^5 n e^2 / a^6 (Peale & Cassen 1979),
k2 the world's Love number from its rigidity and gravity. Tides also damp the eccentricity (orbits.py) and lock the
spin. A moon in resonance with its neighbours keeps its eccentricity forced and is heated for ever (Io, Europa);
a close planet of a small star is heated while its eccentricity lasts and by what its neighbours force.

What the heat does: the share of its mantle it has melted and degassed (outgassing), a dynamo where the core still
loses heat faster than it conducts along its adiabat (a field), and the heat flowing out through its floor and ice
(the energy of life in the dark: worlds.solvents).
"""

import math
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------- units
M_EARTH_KG = 5.972e24           # the unit mass (units, not a baseline: every value is computed in them)
R_EARTH_M = 6.371e6
M_SUN_KG = 1.989e30
AU_M = 1.496e11
G_SI = 6.674e-11
GYR_S = 3.156e16
UNIT_G = 9.81                   # m/s^2 at unit mass and radius
R_GAS = 8.314
FLUX_UNIT_W = 340.0             # W/m^2: the flux unit averaged over a sphere (worlds.py)

# ---------------------------------------------------------------------- the isotopes (measured)
# half-life (Gyr), heat per kg of the isotope (W/kg), kg per kg of mantle in the bulk silicate Earth today, alpha
# decay's Gamow term (ln of half-life x attempt rate; None for beta decay, which alpha does not set)
ISOTOPES = {
    "U238": (4.468, 9.46e-5, 20e-9 * 0.9928, 87.8),
    "U235": (0.704, 5.69e-4, 20e-9 * 0.0072, 86.0),
    "Th232": (14.05, 2.64e-5, 80e-9, 88.9),
    "K40": (1.248, 2.92e-5, 240e-6 * 1.17e-4, None),
}
ELEMENT = {"U238": "U", "U235": "U", "Th232": "U", "K40": "K"}   # thorium spreads as uranium does (by mass)
SOLAR_AGE_GYR = 4.57            # the bulk silicate Earth's abundances are read back this far: the Sun's birth
SUN_BORN_GYR = 9.2              # the Sun's birth after the Big Bang (13.8 - 4.57, rounded: cosmos's anchor)

# ---------------------------------------------------------------------- rock (laboratory measurements)
CP_ROCK = 1200.0                # J/(kg K): Dulong-Petit, 3k per atom over silicate's mean atomic mass
K_ROCK = 4.0                    # W/(m K): thermal conductivity of mantle rock
ALPHA_TH = 3.0e-5               # 1/K: thermal expansion
KAPPA = 1.0e-6                  # m^2/s: thermal diffusivity
RA_CRIT = 1000.0                # the critical Rayleigh number of a convecting layer (fluid dynamics)
ETA_REF = 1.0e21                # Pa s: mantle viscosity at T_REF (post-glacial rebound)
T_REF = 1600.0                  # K
CREEP_EA = 3.0e5                # J/mol: activation energy of olivine creep (a chemistry energy: scales with it)
LIQUIDUS_K = 1800.0             # K: rock's liquidus at a unit world's mid-mantle - where a magma ocean freezes
LIQUIDUS_MASS = 0.15            # its rise with pressure, ~ mass^0.15 (Simon-Glatzel, declared exponent)
RHO_ROCK = 4000.0               # kg/m^3: mantle rock at a unit world's pressure
BULK_ROCK = 1.3e11              # Pa: bulk modulus of mantle rock
RHO_ICE = 1000.0
MU_ROCK = 5.0e10                # Pa: rigidity of rock (sets the Love number)
MU_ICE = 4.0e9                  # of ice
TIDAL_Q = 100.0                 # dissipation: the share of tidal energy lost per cycle is 2 pi / Q (rock, ~10-500)
CP_IRON = 450.0                 # J/(kg K): iron, Dulong-Petit
RHO_CORE = 1.1e4                # kg/m^3: iron at a unit world's core pressure
IRON_LIQUIDUS_K = 4000.0        # K: iron melts at a unit world's core-mantle boundary pressure (diamond-anvil data)
IRON_PRESSURE = 0.3             # its rise with pressure (Simon-Glatzel, declared exponent): P ~ M^2 / R^4
K_CORE = 40.0                   # W/(m K): liquid iron's conductivity
ALPHA_CORE = 1.0e-5             # 1/K
L_IRON = 7.5e5                  # J/kg: latent heat of freezing iron
FREEZE_SPAN = 0.37              # an inner core freezes over the span between the liquidus at the core's top and centre,
                                # a share of its temperature (the liquidus rising faster with pressure than the adiabat)
K_ICE = 567.0                   # W/m: ice's conductivity is 567 / T (Petrenko & Whitworth)
STEPS = 10                      # integration steps per quarter of the age asked


def _laws(laws: Any = None) -> Any:
    from xylarium.kernel import fundamental
    return fundamental.current() if laws is None else laws


def half_life(iso: str, laws: Any = None) -> float:
    t, _, _, gamow = ISOTOPES[iso]
    return t if gamow is None else t * _laws(laws).half_life(gamow)


def _made_and_kept(tau: float, tau_f: float, span: float) -> float:
    """Of an isotope made at a rate falling as exp(-t / tau_f) over span Gyr, the share still there (decay tau)."""
    if span <= 0:
        return 1.0
    lf, li = 1.0 / tau_f, 1.0 / tau
    made = (1.0 - math.exp(-lf * span)) / lf
    if abs(li - lf) < 1e-9:
        kept = span * math.exp(-li * span)
    else:
        kept = (math.exp(-lf * span) - math.exp(-li * span)) / (li - lf)
    return kept / max(1e-12, made)


def inventory(seed: Any, r_kpc: float, born: float, z: float, laws: Any = None) -> Dict[str, float]:
    """Each isotope's mass per kg of mantle at a star's birth (z its metallicity, solar 1): the Sun-birth values
    scaled by its metals, uranium's and potassium's own spread by mass, and what decay left of what was made."""
    from xylarium.kernel import cosmos, creation
    L = _laws(laws)
    t1 = creation.first_stars(seed) if seed is not None else creation.FIRST_STARS_GYR
    tau_f = creation.infall_gyr(seed, r_kpc) if seed is not None else cosmos.formed_gyr(r_kpc)
    tau_f0 = cosmos.formed_gyr(cosmos.R0_KPC)
    out = {}
    for iso, (t_half, _, today, _) in ISOTOPES.items():
        tau0 = t_half / math.log(2.0)
        at_sun_birth = today * math.exp(SOLAR_AGE_GYR / tau0)
        sun_kept = _made_and_kept(tau0, tau_f0, SUN_BORN_GYR - creation.FIRST_STARS_GYR)
        tau = half_life(iso, L) / math.log(2.0)
        kept = _made_and_kept(tau, tau_f, born - t1)
        spread = cosmos.abundance(ELEMENT[iso], r_kpc) / cosmos.abundance("Fe", r_kpc)
        out[iso] = at_sun_birth * max(0.0, z) * spread * kept / max(1e-12, sun_kept)
    return out


def radiogenic_w_per_kg(inv: Dict[str, float], age: float, laws: Any = None) -> float:
    """Heat per kg of mantle at an age after the star's birth."""
    L = _laws(laws)
    h = 0.0
    for iso, c in inv.items():
        t_half, w_kg, _, _ = ISOTOPES[iso]
        th = half_life(iso, L)
        # the same decay energy (scaled by the nuclear force) released over a different half-life
        h += c * w_kg * (t_half / th) * L.nuclear * math.exp(-max(0.0, age) * math.log(2.0) / th)
    return h


def love_number(mass: float, radius: float, icy: bool) -> float:
    """k2 of a uniform elastic body: 1.5 / (1 + 19 mu / (2 rho g R))."""
    m, r = mass * M_EARTH_KG, radius * R_EARTH_M
    if m <= 0.0 or r <= 0.0:
        return 0.0                                   # nothing to raise a tide in: no self-gravity, no bulge
    rho = m / (4.0 / 3.0 * math.pi * r ** 3)
    g = G_SI * m / r ** 2
    mu = MU_ICE if icy else MU_ROCK
    return 1.5 / (1.0 + 19.0 * mu / (2.0 * rho * g * r))


def tidal_w(host_kg: float, a_m: float, e: float, mass: float, radius: float, icy: bool) -> float:
    """Tidal heating of a synchronously rotating world on an eccentric orbit (W)."""
    if e <= 0 or a_m <= 0:
        return 0.0
    r = radius * R_EARTH_M
    n = math.sqrt(G_SI * (host_kg + mass * M_EARTH_KG) / a_m ** 3)
    k2 = love_number(mass, radius, icy)
    return 10.5 * (k2 / TIDAL_Q) * G_SI * host_kg ** 2 * r ** 5 * n * e * e / a_m ** 6


def _viscosity(t: float, laws: Any) -> float:
    L = _laws(laws)
    return ETA_REF * math.exp(min(200.0, CREEP_EA * L.chem / R_GAS * (1.0 / max(1.0, t) - 1.0 / (T_REF * L.chem))))


def _conv_flux(t_hot: float, t_cold: float, g: float, laws: Any, t_layer: Optional[float] = None) -> float:
    """W/m^2 a convecting layer at t_hot passes across a boundary to t_cold (boundary-layer theory; the boundary's
    viscosity at t_layer, the hot side's by default)."""
    dt = max(0.0, t_hot - t_cold)
    if dt <= 0 or g <= 0:
        return 0.0
    eta = _viscosity(t_hot if t_layer is None else t_layer, laws)
    return K_ROCK * dt ** (4.0 / 3.0) * (RHO_ROCK * g * ALPHA_TH / (KAPPA * eta * RA_CRIT)) ** (1.0 / 3.0)


def evolve(mass: float, radius: float, core: float, inv: Dict[str, float], age: float, t_surf: float = 250.0,
           tide: Optional[Any] = None, icy: bool = False, laws: Any = None) -> Dict[str, float]:
    """A world's interior from its birth to an age (Gyr): its mantle's and core's temperatures, the heat flowing out
    through each m^2 of its surface (radiogenic, secular, tidal), its field, and how many times its heat could have
    melted its mantle (what it has degassed). tide(t) gives the tidal heating (W) at t.
    The core loses heat to the mantle through the boundary layer at their interface (the same law, at the hotter
    layer's lower viscosity); it runs a dynamo while it loses more than it can conduct along its adiabat."""
    L = _laws(laws)
    m_kg = mass * M_EARTH_KG
    r_m = radius * R_EARTH_M
    area = 4.0 * math.pi * r_m ** 2
    g = G_SI * m_kg / r_m ** 2
    m_core = m_kg * max(0.0, core)
    mantle = m_kg - m_core
    r_core = (3.0 * m_core / (4.0 * math.pi * RHO_CORE * L.density)) ** (1.0 / 3.0) if m_core > 0 else 0.0
    a_core = 4.0 * math.pi * r_core ** 2
    g_core = G_SI * m_core / r_core ** 2 if r_core > 0 else 0.0
    cap_mantle = mantle * CP_ROCK
    t_melt = LIQUIDUS_K * L.chem * max(0.01, mass) ** LIQUIDUS_MASS
    press = max(1e-4, mass ** 2 / max(1e-3, radius) ** 4)
    t_liq_core = IRON_LIQUIDUS_K * L.chem * press ** IRON_PRESSURE
    # a freezing core gives up its latent heat as it cools: per kelvin, its iron's heat plus the share that freezes
    cap_core = m_core * (CP_IRON + L_IRON / (FREEZE_SPAN * t_liq_core))
    # the mantle's base is hotter than its top by the adiabat across its depth: exp(alpha g D / c_p)
    # (expansion falling with pressure: alpha / (1 + P / K), P the weight of the mantle over its base)
    depth = max(0.0, r_m - r_core)
    adiabat = math.exp(ALPHA_TH / (1.0 + RHO_ROCK * g * depth / BULK_ROCK) * g * depth / CP_ROCK)
    t_int, t_core = t_melt, t_liq_core
    processed, q_cmb = 0.0, 0.0
    n = STEPS * 4
    dt = age / n if age > 0 else 0.0
    for i in range(n):
        t = (i + 0.5) * dt
        h_rad = radiogenic_w_per_kg(inv, t, L) * mantle
        h_tide = tide(t) if tide else 0.0
        q_out = _conv_flux(t_int, t_surf, g, L) * area
        t_base = t_int * adiabat
        q_cmb = _conv_flux(t_core, t_base, g_core, L, (t_core + t_base) / 2.0) * a_core if m_core > 0 else 0.0
        # stepped stably: neither layer cools past the one it gives its heat to
        d_int = (h_rad + h_tide + q_cmb - q_out) * dt * GYR_S / cap_mantle
        t_int = max(t_surf, min(t_melt * 1.2, t_int + max(d_int, -(t_int - t_surf) * 0.5)))
        if m_core > 0:
            d_core = -q_cmb * dt * GYR_S / cap_core
            t_core = max(t_int * adiabat, t_core + max(d_core, -(t_core - t_int * adiabat) * 0.5))
        processed += q_out * dt * GYR_S / max(1.0, mantle * CP_ROCK * max(1.0, t_melt - t_surf))
    h_rad = radiogenic_w_per_kg(inv, age, L) * mantle
    h_tide = tide(age) if tide else 0.0
    q_total = _conv_flux(t_int, t_surf, g, L) * area if age > 0 else 0.0
    q = max(q_total, h_rad + h_tide) / area          # what flows out (a world heated faster than it convects melts)
    q_rad, q_tide = h_rad / area, h_tide / area
    q_sec = max(0.0, q * area - h_rad - h_tide) / area
    # the core's adiabat: what liquid iron conducts down its own temperature gradient (alpha g T / c_p)
    q_ad = K_CORE * ALPHA_CORE * g_core * t_core / CP_IRON
    q_cmb_area = q_cmb / a_core if a_core > 0 else 0.0
    field = 0.0 if m_core <= 0 or q_ad <= 0 else max(0.0, min(1.0, q_cmb_area / q_ad - 1.0))
    return {"t_int": round(t_int, 1), "t_core": round(t_core, 1), "q": q, "q_rad": q_rad, "q_sec": q_sec,
            "q_tide": q_tide, "q_cmb": q_cmb_area, "q_ad": q_ad, "field": round(field, 3), "processed": processed,
            "heat_w": q * area, "flux_units": q / FLUX_UNIT_W}


def shell_km(q: float, t_surf: float, t_melt: float) -> float:
    """The thickness of an ice shell whose base sits at its melting point, conducting q W/m^2 to a surface at t_surf
    (conductivity 567 / T: d = 567 ln(t_melt / t_surf) / q)."""
    if q <= 0:
        return float("inf")
    return K_ICE * math.log(max(1.0, t_melt) / max(1.0, min(t_surf, t_melt))) / q / 1000.0
