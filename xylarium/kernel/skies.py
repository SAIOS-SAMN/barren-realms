"""
Xylarium skies: atmospheric engineering - holding a world's air, or giving it back - as a choice a people makes.

A world's air is bound by its gravity and lost to its star's wind, to a stalled dynamo (harvest.py), to a strike
(ruin.py). Nothing in physics forbids holding it or replacing it; each is a price in energy and matter:

  SHIELD    a magnetic dipole held between the world and its star stands its wind off (Green et al. 2017's proposal
            for Mars): the field must match the wind's pressure at the standoff, B = sqrt(2 mu0 p_wind), over a
            volume a few of the world's radii across - its energy B^2 / 2 mu0 x that volume, a small price; while it
            stands, the wind takes no air (harvest.py reads it).
  IMPORT    volatiles steered in from the system's belts and comet cloud (creation's belts): each kilogram costs the
            nudge that brings it down, ~ (a tenth of the world's orbital speed)^2 / 2, and the belt's ice and carbon.
  OUTGAS    volatiles released from the world's own rock - carbonates broken to carbon dioxide (~4 MJ/kg, the
            reaction's enthalpy) - where no belt offers ice.

Neither is a requirement of anything. It is offered to a people that reaches the stars (it has yards), and its
council weighs it each year through its own mind (decide.choose): the lives its land would feed again, valued as
this universe values a life and the more for every generation it has lived there (continuity: its history, its dead,
its meaning), against the energy at what that energy is worth to it and the matter it takes. A people with little
to hold it to a failing world lets the air go, its people dwindle and its fleets carry them elsewhere (demography's
diaspora) - a nomad's way; one rooted for generations pays to keep its sky.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import interior
from xylarium.kernel.fx import hub as _hub

MU0 = 4.0e-7 * math.pi
WIND_PA_1AU = 1.5e-9            # the solar wind's dynamic pressure at 1 AU (measured; ~ a star's light / a^2)
STANDOFF_RADII = 2.0            # the shield's bubble spans a couple of the world's radii (Green et al. 2017)
OUTGAS_J_PER_KG = 4.0e6         # breaking carbonate rock to carbon dioxide (enthalpy of CaCO3 -> CaO + CO2)
NUDGE_SHARE = 0.1               # steering belt ice down takes ~ a tenth of the world's orbital speed (declared)
MIX_E_FOLD = 1.0 - math.exp(-1.0)   # an atmosphere mixes in about a year: at most one e-fold of repair a year

# Fundamental thermodynamic & atmospheric physical constants
STEFAN_BOLTZMANN = 5.670374419e-8  # W / (m^2 K^4)
SOLAR_CONSTANT_1AU = 1361.0        # W / m^2 (mean solar flux at 1 AU)
GAS_CONSTANT_R = 8.314462618       # J / (mol K)
MOLAR_MASS_AIR = 0.02897           # kg / mol (Earth-like N2/O2 mix)
T_FREEZE_WATER_K = 273.15          # Freezing point of water at 1 atm


@dataclass
class AtmosphericColumn:
    p_surface_bar: float
    scale_height_km: float
    optical_depth_tau: float
    greenhouse_warming_k: float
    albedo: float
    zonal_wind_max_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "p_surface_bar": round(self.p_surface_bar, 4),
            "scale_height_km": round(self.scale_height_km, 3),
            "optical_depth_tau": round(self.optical_depth_tau, 4),
            "greenhouse_warming_k": round(self.greenhouse_warming_k, 2),
            "albedo": round(self.albedo, 4),
            "zonal_wind_max_ms": round(self.zonal_wind_max_ms, 2),
        }


def compute_climate_manifold(
    planet: Any,
    star_dict: Optional[Dict[str, Any]] = None,
    kernel: Any = None,
) -> Dict[str, Any]:
    """Compute continuous S^2 thermal field T(theta) and circulation regime.
    
    Lifts planetary climate from bulk scalar approximations to a continuous
    thermodynamic equilibrium on S^2 with latitude-dependent insolation,
    dynamic ice-albedo phase bifurcations, and Coriolis-balanced thermal wind shear.
    """
    from xylarium.kernel import physics
    
    # Atmospheric surface pressure
    soc = getattr(planet, "society", {}) or {}
    p_bar = max(1e-4, float(soc.get("atmosphere", 1.0)))
    
    # Stellar flux factor relative to 1 AU solar
    if star_dict is not None and "luminosity" in star_dict:
        lum = float(star_dict["luminosity"])
        q = float(getattr(planet, "q", 1.0) or 1.0)
        flux_factor = lum / (q ** 4) if q > 0 else 1.0
    elif kernel is not None and getattr(planet, "sector_id", None) in getattr(kernel, "sectors", {}):
        sec = kernel.sectors[planet.sector_id]
        flux_factor = float(physics.planet_flux(sec, planet))
    else:
        flux_factor = 1.0

    # Planetary dimensions & gravity
    body_data = physics.body(planet) if hasattr(planet, "society") else {}
    r_earth = max(0.1, float(body_data.get("radius", 1.0)))
    m_earth = max(0.01, float(body_data.get("mass", 1.0)))
    g = 9.80665 * (m_earth / (r_earth ** 2))
    r_planet_m = r_earth * interior.R_EARTH_M
    
    # Stellar irradiance at subsolar point
    s_subsolar = SOLAR_CONSTANT_1AU * max(1e-6, flux_factor)
    
    # Obliquity (axial tilt in radians)
    obliquity_rad = math.radians(23.44)
    
    # Rotation rate Omega (rad/s)
    period_hours = float(body_data.get("period_h", 24.0)) if body_data else 24.0
    period_s = max(3600.0, period_hours * 3600.0)
    omega = 2.0 * math.pi / period_s
    
    # Latitude insolation profile over S^2
    # Latitudes theta from -pi/2 to +pi/2 sampled at 9 nodes
    lat_nodes = [-80.0, -60.0, -40.0, -20.0, 0.0, 20.0, 40.0, 60.0, 80.0]
    thermal_profile = []
    absorbed_flux_list = []
    albedo_list = []
    
    # Optical depth tau from pressure column
    tau = 0.84 * (p_bar ** 0.8)
    
    for lat_deg in lat_nodes:
        theta = math.radians(lat_deg)
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        cos_delta = math.cos(obliquity_rad)
        sin_delta = math.sin(obliquity_rad)
        
        f_in = (s_subsolar / math.pi) * max(0.02, cos_theta * cos_delta + 0.5 * abs(sin_theta * sin_delta))
        
        # Estimate bare temperature to test phase bifurcation
        t_est = (f_in * (1.0 - 0.25) / STEFAN_BOLTZMANN) ** 0.25
        
        # Dynamic albedo feedback:
        # Ice bifurcation below freezing point, open ocean/temperate otherwise
        if t_est < T_FREEZE_WATER_K:
            alpha = 0.65  # Glaciated ice-sheet albedo
        elif abs(lat_deg) < 30.0:
            alpha = 0.12  # Equatorial ocean/tropical loam
        else:
            alpha = 0.22  # Temperate land/cloud mixture
            
        f_abs = f_in * (1.0 - alpha)
        absorbed_flux_list.append(f_abs)
        albedo_list.append(alpha)
        
    # Global mean absorbed flux weighted by cos(theta)
    weights = [math.cos(math.radians(deg)) for deg in lat_nodes]
    sum_w = sum(weights)
    f_abs_mean = sum(f * w for f, w in zip(absorbed_flux_list, weights)) / sum_w
    mean_albedo = sum(a * w for a, w in zip(albedo_list, weights)) / sum_w
    
    # Effective radiating temperature and surface equilibrium with greenhouse
    t_eff_global = (f_abs_mean / STEFAN_BOLTZMANN) ** 0.25
    t_surf_global = t_eff_global * ((1.0 + 0.75 * tau) ** 0.25)
    greenhouse_warming = t_surf_global - t_eff_global
    
    # Scale height H = R_gas * T / (mu * g)
    scale_height_km = (GAS_CONSTANT_R * t_surf_global) / (MOLAR_MASS_AIR * g) * 1e-3
    
    # Budyko-Sellers meridional diffusion relaxation
    d_diff = 3.8  # W / (m^2 K) meridional heat transport coefficient
    zonal_winds = []
    
    for i, lat_deg in enumerate(lat_nodes):
        theta = math.radians(lat_deg)
        # Local equilibrium temperature with meridional transport
        transport_q = d_diff * (t_surf_global - t_eff_global) * math.cos(theta)
        f_net = max(1.0, absorbed_flux_list[i] + transport_q)
        t_eff_loc = (f_net / STEFAN_BOLTZMANN) ** 0.25
        t_surf_loc = t_eff_loc * ((1.0 + 0.75 * tau) ** 0.25)
        
        thermal_profile.append({
            "lat_deg": lat_deg,
            "temp_k": round(t_surf_loc, 2),
            "insolation_wm2": round(absorbed_flux_list[i], 1),
            "albedo": round(albedo_list[i], 3),
        })
        
    # Compute Thermal Wind Shear:
    # du / dln(p) = - (R_gas / (f * mu)) * (dT / dy)
    r_specific = GAS_CONSTANT_R / MOLAR_MASS_AIR
    max_zonal_wind = 0.0
    
    for i in range(len(lat_nodes) - 1):
        lat_mid = 0.5 * (lat_nodes[i] + lat_nodes[i+1])
        theta_mid = math.radians(lat_mid)
        # Coriolis parameter f = 2 * Omega * sin(theta)
        f_coriolis = 2.0 * omega * math.sin(theta_mid)
        
        # Temperature gradient dT / dy = (1 / R) * (dT / dtheta)
        d_theta = math.radians(lat_nodes[i+1] - lat_nodes[i])
        dy = r_planet_m * d_theta
        dt = thermal_profile[i+1]["temp_k"] - thermal_profile[i]["temp_k"]
        dt_dy = dt / max(100.0, dy)
        
        # Regularize near equator where f -> 0
        if abs(f_coriolis) > 1e-6:
            # ln(p_surf / p_tropo) ~ ln(1.0 / 0.2) ~ 1.6
            u_wind = - (r_specific / f_coriolis) * dt_dy * 1.6
        else:
            # Equatorial Kelvin/Rossby scale
            u_wind = math.sqrt(max(0.0, r_specific * abs(dt)))
            
        u_wind = min(300.0, max(-300.0, u_wind))
        zonal_winds.append({"lat_deg": round(lat_mid, 1), "wind_ms": round(u_wind, 2)})
        if abs(u_wind) > max_zonal_wind:
            max_zonal_wind = abs(u_wind)
            
    # Determine circulation regime
    if p_bar < 0.01:
        regime = "EXOSPHERE_BALLISTIC"
    elif t_surf_global < 240.0:
        regime = "SNOWBALL_GLACIATED"
    elif t_surf_global > 360.0:
        regime = "RUNAWAY_GREENHOUSE"
    else:
        regime = "3_CELL_HADLEY_FERREL_POLAR"
        
    column = AtmosphericColumn(
        p_surface_bar=p_bar,
        scale_height_km=scale_height_km,
        optical_depth_tau=tau,
        greenhouse_warming_k=greenhouse_warming,
        albedo=mean_albedo,
        zonal_wind_max_ms=max_zonal_wind,
    )
    
    return {
        "column": column,
        "t_mean_k": round(t_surf_global, 2),
        "t_equator_k": thermal_profile[4]["temp_k"],  # lat 0.0
        "t_pole_k": 0.5 * (thermal_profile[0]["temp_k"] + thermal_profile[-1]["temp_k"]),
        "thermal_profile": thermal_profile,
        "zonal_wind_profile": zonal_winds,
        "circulation_regime": regime,
    }


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "skies")


def air_full_kg(kernel: Any, planet: Any) -> float:
    """The world's air at its natural fullness."""
    from xylarium.kernel import ruin
    a = max(1e-6, float(planet.society.get("atmosphere", 1.0)))
    return ruin.binding(kernel, planet)["air_kg"] / a


def shield_j(kernel: Any, planet: Any) -> float:
    """Energy held in a shield's field: B^2 / 2 mu0 over its bubble, B to stand off the star's wind."""
    from xylarium.kernel import physics
    sec = kernel.sectors.get(planet.sector_id)
    flux = float(physics.planet_flux(sec, planet)) if sec is not None else 1.0
    b_field = math.sqrt(2.0 * MU0 * WIND_PA_1AU * flux)
    r = float(physics.body(planet).get("radius", 1)) * interior.R_EARTH_M * STANDOFF_RADII
    return b_field ** 2 / (2.0 * MU0) * 4.0 / 3.0 * math.pi * r ** 3


def _orbital_speed(kernel: Any, planet: Any) -> float:
    from fractions import Fraction
    from xylarium.kernel import physics
    sec = kernel.sectors.get(planet.sector_id)
    st = physics.star(sec) if sec is not None else {"mass": Fraction(1)}
    a = float(physics.body(planet).get("q", 1)) ** 2 * interior.AU_M
    return math.sqrt(interior.G_SI * float(st["mass"]) * interior.M_SUN_KG / max(1.0, a))


def _volatile_belt(kernel: Any, planet: Any) -> Optional[Dict[str, Any]]:
    sec = kernel.sectors.get(planet.sector_id)
    belts = [b for b in (getattr(sec, "belts", None) or [])
             if b.get("reserve", 0) > 0 and sum(b["composition"].get(e, 0) for e in ("H2O", "C", "cryogenite")) > 0]
    return max(belts, key=lambda b: b["reserve"]) if belts else None


def repair_cost(kernel: Any, planet: Any, share: float) -> Dict[str, Any]:
    """Energy (EU) and matter to give back a share of the world's natural air: steered from a belt if the system
    has volatile ice, else broken out of its own rock."""
    from xylarium.kernel import creation, ruin
    kg = air_full_kg(kernel, planet) * share
    belt = _volatile_belt(kernel, planet)
    if belt is not None:
        j = kg * 0.5 * (NUDGE_SHARE * _orbital_speed(kernel, planet)) ** 2
        frac = sum(belt["composition"].get(e, 0) for e in ("H2O", "C", "cryogenite"))
        units = max(1, int(math.ceil(kg / frac / (interior.M_EARTH_KG / creation.UNITS_PER_EARTH_MASS))))
        return {"kg": kg, "eu": j / ruin.EU_J, "how": "import", "belt": belt, "units": units}
    return {"kg": kg, "eu": kg * OUTGAS_J_PER_KG / ruin.EU_J, "how": "outgas", "belt": None, "units": 0}


def _energy_held(planet: Any) -> float:
    """EU a world can spend: its grid and its antimatter."""
    from xylarium.kernel import energy
    return planet.society.get("grid_meu", 0) / energy.MILLI + planet.element_reserves.get("AM", 0) * energy.ANTIMATTER_EU


def _spend(kernel: Any, planet: Any, eu: float, why: str) -> bool:
    from xylarium.kernel import energy, matter
    if _energy_held(planet) < eu:
        return False
    meu = int(math.ceil(eu * energy.MILLI))
    grid = int(planet.society.get("grid_meu", 0))
    take = min(grid, meu)
    if take:
        planet.society["grid_meu"] = grid - take
        energy.sink(kernel, why, take)
    rest = meu - take
    if rest > 0:
        am = int(math.ceil(rest / energy.MILLI / energy.ANTIMATTER_EU))
        planet.element_reserves["AM"] = planet.element_reserves.get("AM", 0) - am
        matter.sink(why, "AM", am)
    return True


def continuity(kernel: Any, planet: Any) -> float:
    """How much a people holds to its world: 1 + ln(1 + the generations it has lived there) - its history, its dead
    laid in it, what it has made it mean."""
    from xylarium.kernel import fertility
    years = max(0.0, (kernel.cycle_count - int(planet.society.get("founded_cycle", 0) or 0)) / 100.0)
    gen = max(1e-6, fertility.generation_of(kernel, planet))
    return 1.0 + math.log1p(years / gen)


def _options(kernel: Any, planet: Any) -> List[Dict[str, Any]]:
    from xylarium.kernel import alignment, biosphere, decide, energy
    soc = planet.society
    a = float(soc.get("atmosphere", 1.0))
    sc = alignment.scales(kernel)
    life = sc["sol"] / max(1.0, sc["lives"]) * continuity(kernel, planet)
    fx = kernel.fx_market
    # what a unit of energy is worth to it: what it would make of a spare one if its grid runs over, else what a
    # missing one costs its industry
    spare = soc.get("grid_meu", 0) / energy.MILLI > energy.need_eu(planet, kernel)
    per_eu = energy.value_surplus(planet) if spare else energy.value_short(planet)
    per_eu = fx.to_sol_value(planet.currency, per_eu) if planet.currency != _hub() else per_eu
    base = biosphere._profile(kernel, planet, None, None, None)["k"]
    m = decide.mind_of_planet(kernel, planet)
    out = []
    if a < 1.0:
        share = (1.0 - a) * MIX_E_FOLD
        c = repair_cost(kernel, planet, share)
        value = base * share * life                                       # the lives its land feeds again
        out.append(decide.option("repair_sky", c["eu"] * max(per_eu, 1e-9), value, share=share, plan=c, aim="hold"))
    if not soc.get("shield") and float(soc.get("dynamo", 1.0)) < 0.5:
        j = shield_j(kernel, planet)
        from xylarium.kernel import ruin
        loss = (0.5 - float(soc.get("dynamo", 1.0))) * 0.02 * 4.0           # the air the wind takes in a year
        value = decide.worth(kernel, base * loss * a * life / 4.0, m)
        out.append(decide.option("raise_shield", j / ruin.EU_J * max(per_eu, 1e-9), value, eu=j / ruin.EU_J, aim="hold"))
    return out


def season(kernel: Any) -> List[str]:
    """Once a year each people with yards weighs its sky."""
    from xylarium.kernel import decide, sustenance
    if (kernel.cycle_count // 25) % 4:
        return []
    logs: List[str] = []
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population <= 0 or getattr(p, "natives", None) or not sustenance.yards(p):
                continue
            for opt in _options(kernel, p):          # each weighed on its own against doing nothing
                logs += _act(kernel, p, decide.choose(kernel, [opt], decide.mind_of_planet(kernel, p), p.id,
                                                      "skies", opt["name"]))
    return logs


def _act(kernel: Any, p: Any, pick: Optional[Dict[str, Any]]) -> List[str]:
    """Carry out what a people chose for its sky (None: it chose to let it be)."""
    from xylarium.kernel import history, imprint, matter
    st = stats(kernel)
    if pick is None:
        st["declined"] += 1
        return []
    if pick["name"] == "raise_shield":
        if not _spend(kernel, p, pick["eu"], "sky_shield"):
            return []
        imprint.record(kernel, p, "shield", str(p.owner_id or ""), shield=True)
        st["shields"] += 1
        history.event(kernel, "SKY_SHIELD", f"{p.name} raises a shield against its star's wind",
                      sector_id=p.sector_id, actors=[str(p.owner_id or "")],
                      cause="its core no longer turns the wind aside, and its people chose to keep their air")
        return [f"[SKIES] {p.name} raises a magnetic shield between itself and its star."]
    c = pick["plan"]
    if not _spend(kernel, p, c["eu"], "sky_repair"):
        return []
    if c["belt"] is not None:
        take = min(c["units"], int(c["belt"]["reserve"]))
        c["belt"]["reserve"] -= take
        matter.sink("volatiles_imported", "BELT_ROCK", take)
    imprint.record(kernel, p, "air_returned", str(p.owner_id or ""), air_add=round(pick["share"], 9))
    st["repairs"] += 1
    st["air_kg"] += c["kg"]
    how = "steered in from its belt" if c["how"] == "import" else "broken from its rock"
    history.event(kernel, "SKY_REPAIR", f"{p.name} is given back part of its air", sector_id=p.sector_id,
                  actors=[str(p.owner_id or "")], cause=f"{c['kg']:.2e} kg of volatiles {how}",
                  data={"share": round(pick["share"], 4), "eu": round(c["eu"], 1)})
    return [f"[SKIES] {p.name} is given back {pick['share']:.0%} of its air ({how})."]


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {k: st[k] for k in ("shields", "repairs", "declined")} | {"air_kg": float(f"{st['air_kg']:.3g}")}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="skies", state=lambda: {"shields": 0, "repairs": 0, "declined": 0, "air_kg": 0.0},
                             season=season, summary=summary))
