"""
Xylarium hydromagnetics: conducting fluids and fields order one another - the syntropic half of a world's physics
that thermodynamics alone leaves out.

A core convects because it loses heat faster than its iron can conduct along its own adiabat (interior.py). That
convection, in a conductor, builds and holds a field: ordered structure kept by a flow that would otherwise only run
down. The field in turn shapes what reaches the world - its star's wind and the galaxy's cosmic rays - and so what
its surface keeps, and what its living erase or keep.

  DYNAMO       runs while q_cmb > q_ad (interior.py). The share of the core's heat flow that can be drawn off before
               it stalls is 1 - q_ad / q_cmb: a world's own margin, nothing declared.
  FIELD        the power-based scaling of planetary dynamos (Christensen & Aubert 2006): field in the core grows as the
               cube root of the convective power (the excess flux x core radius); the dipole at the surface falls as
               (r_core / R)^3. In units of the unit world's own, computed by the same physics (a ruler, not a target).
  STANDOFF     where the field's pressure meets the star's wind (Chapman-Ferraro): r_mp / R = (B^2 / 2 mu0 P)^(1/6),
               ruled by the unit world's measured ten radii. The wind's pressure at a world: its star's activity now
               over the square of its distance (flux over luminosity).
  EXPOSURE     the share of a world's sky the wind reaches: (R / r_mp)^2 - all of it where there is no field.
  DOSE         particles reaching the surface: the star's (its wind's pressure x exposure) and the galaxy's cosmic rays
               (rising with the stellar density where the world circles: supernovae make them), the field turning
               away the cosmic rays below its cutoff (Stormer: cutoff rises with the moment over r^2; the spectrum
               falls as rigidity^-1.7 above it), the air absorbing both by its column (nuclear attenuation length).
               In units of the unit world's own dose. This is what the living's erasure reads.
"""

import functools
import math
from typing import Any, Dict, Optional

EARTH_STANDOFF_R = 10.1         # the unit world's measured magnetopause, in its radii (subsolar, quiet wind)
HOME_LIFETIME_RISK = 0.0105    # lifetime risk the unit world's own background carries for its people (~3 mSv a year
                                # over a ~70-year life at ~5% per sievert: measured) - the scale of harm per home dose
CR_SPECTRUM = 1.7               # integral cosmic-ray spectrum's fall with rigidity above the cutoff (measured)
EARTH_CUTOFF_GV = 6.0           # the unit world's surface-averaged geomagnetic cutoff rigidity (measured)
CR_MEDIAN_GV = 4.0              # median rigidity of the galactic cosmic rays at a quiet star's distance (measured)
COLUMN_PER_BAR = 1033.0         # g/cm^2 of air over each bar at the unit world's gravity
ATTENUATION = 185.0             # g/cm^2: the cosmic-ray dose's attenuation through air, its cascade included (the
                                # unit world's sea level takes ~1/270 of the dose its field lets into its sky)
SW_POWER = 2.7e-4               # W/m^2: the unit star's wind's kinetic power through the unit orbit (~5 protons per
                                # cm^3 at ~400 km/s: measured)
GCR_POWER = 1.2e-5              # W/m^2: the galaxy's cosmic rays' power through a surface at R0 (their ~1 eV/cm^3
                                # energy density x c/4: measured)
RADIOLYSIS_YIELD = 0.03         # the share of absorbed particle energy water ice stores as fuel (G ~ 2 oxidant
                                # molecules per 100 eV, ~1.5 eV free energy each: measured)
FLUX_UNIT_W = 340.0             # W/m^2: the flux unit worlds.py reckons energy in (the unit world's mean insolation)


def margin(w: Dict[str, Any]) -> float:
    """The share of a core's heat flow that can be drawn off before its dynamo stalls (0 with no dynamo)."""
    q_cmb, q_ad = float(w.get("q_cmb") or 0.0), float(w.get("q_ad") or 0.0)
    if q_cmb <= 0 or q_ad <= 0 or q_cmb <= q_ad:
        return 0.0
    return 1.0 - q_ad / q_cmb


@functools.lru_cache(maxsize=1)
def _unit() -> Dict[str, Any]:
    """The unit world (unit mass and radius at a unit star's distance and age, of the Sun's own metals: z is solar-
    relative, 1) - the rulers' own world."""
    from xylarium.kernel import cosmos, physics, worlds
    return worlds.build(None, dict(physics.star_for("G-class")), 1.0, 1.0, 1.0, False, 1.0, cosmos.R0_KPC, 4.57)


def _power(w: Dict[str, Any]) -> float:
    q_cmb, q_ad, r = float(w.get("q_cmb") or 0.0), float(w.get("q_ad") or 0.0), float(w.get("r_core") or 0.0)
    return max(0.0, q_cmb - q_ad) * r


def moment(w: Dict[str, Any]) -> float:
    """The world's dipole moment, in the unit world's: core field (convective power)^(1/3) x core volume."""
    u = _unit()
    pu, ru = _power(u), float(u.get("r_core") or 0.0)
    p, r = _power(w), float(w.get("r_core") or 0.0)
    if p <= 0 or r <= 0 or pu <= 0 or ru <= 0:
        return 0.0
    return (p / pu) ** (1.0 / 3.0) * (r / ru) ** 3


def surface_field(w: Dict[str, Any]) -> float:
    """Dipole field at the surface, in the unit world's: moment over radius cubed."""
    radius = max(1e-6, float(w.get("radius") or 1.0))
    return moment(w) / radius ** 3


def wind_pressure(w: Dict[str, Any], activity: float = 1.0, luminosity: float = 1.0) -> float:
    """The star's wind pressure at the world, in the unit world's: activity x flux / luminosity (1 / a^2)."""
    return max(0.0, activity) * float(w.get("flux") or 0.0) / max(1e-9, luminosity)


def standoff(w: Dict[str, Any], pressure: float = 1.0) -> float:
    """Where the field holds off the wind, in the world's radii (0: no field, the wind reaches the air)."""
    b = surface_field(w)
    if b <= 0:
        return 0.0
    return EARTH_STANDOFF_R * (b * b / max(1e-12, pressure)) ** (1.0 / 6.0)


def exposure(w: Dict[str, Any], pressure: float = 1.0) -> float:
    """The share of the world's sky its star's wind reaches."""
    r = standoff(w, pressure)
    return 1.0 if r <= 1.0 else 1.0 / (r * r)


def _gcr_through_field(w: Dict[str, Any]) -> float:
    radius = max(1e-6, float(w.get("radius") or 1.0))
    cutoff = EARTH_CUTOFF_GV * moment(w) / radius ** 2
    return (1.0 + cutoff / CR_MEDIAN_GV) ** (-CR_SPECTRUM)


def _through_air(w: Dict[str, Any]) -> float:
    g = max(1e-6, float(w.get("g") or 1.0))
    column = COLUMN_PER_BAR * float(w.get("p_bar") or 0.0) / g
    return math.exp(-column / ATTENUATION)


def _dose_raw(w: Dict[str, Any], pressure: float, galactic: float) -> float:
    stellar = pressure * exposure(w, pressure)
    cosmic = galactic * _gcr_through_field(w)
    return (stellar + cosmic) * _through_air(w)


def particle_power(w: Dict[str, Any]) -> float:
    """The particles' power reaching a world's surface (W/m^2): its star's wind through the share of sky its field
    leaves open, the galaxy's cosmic rays (worlds.build's "cr") above its field's cutoff - both through its air."""
    sw = float(w.get("sw") or 0.0)
    stellar = SW_POWER * sw * exposure(w, sw) if sw > 0 else 0.0
    cosmic = GCR_POWER * float(w.get("cr", 1.0)) * _gcr_through_field(w)
    return (stellar + cosmic) * _through_air(w)


def dose_parts(w: Dict[str, Any]) -> Dict[str, float]:
    """A world's surface dose split by source, each a share of the whole: its star's wind and the galaxy's cosmic rays
    (the part that scales with where it circles: cosmos.cosmic_rays) - and the same split of the particles' power."""
    sw = float(w.get("sw") or 0.0)
    stellar = sw * exposure(w, sw) if sw > 0 else 0.0
    cosmic = float(w.get("cr", 1.0)) * _gcr_through_field(w)
    total = stellar + cosmic
    p_st = SW_POWER * stellar
    p_cr = GCR_POWER * cosmic
    return {"stellar": stellar / total if total > 0 else 0.0, "cosmic": cosmic / total if total > 0 else 0.0,
            "power_cosmic": p_cr / (p_st + p_cr) if p_st + p_cr > 0 else 0.0}


def radiolysis(w: Dict[str, Any]) -> float:
    """The fuel those particles make of a world's surface ices and seas (flux units): radiation as food - a dark sea
    under a shell its star's wind and the galaxy's rays split can live on what they make, more of it where the
    stars crowd (the inner galaxy) or its star is young and near."""
    return RADIOLYSIS_YIELD * particle_power(w) / FLUX_UNIT_W


def dose(w: Dict[str, Any], pressure: float = 1.0, galactic: float = 1.0) -> float:
    """Particles reaching the surface, in the unit world's dose under one bar of its own air. galactic: cosmic-ray
    flux where the world circles (cosmos.density - supernovae make them), 1 at the unit radius."""
    u = _dose_raw(dict(_unit(), p_bar=1.0, g=1.0), 1.0, 1.0)
    return _dose_raw(w, pressure, galactic) / max(1e-12, u)


# ---------------------------------------------------------------------- a world on the board
def of_planet(kernel: Any, planet: Any, cycle: Optional[int] = None, swell: Optional[float] = None) -> Dict[str, float]:
    """A world's hydromagnetic state now - or in the season of a clock cycle, with its star's swelling then: its
    dynamo's margin, surface field, magnetopause, the share of its sky its star's wind reaches, and the dose reaching
    its surface."""
    from xylarium.kernel import cosmos, physics, worlds
    w = worlds.state_of_planet(kernel, planet, cycle, swell)["world"]
    sec = kernel.sectors.get(planet.sector_id) if kernel is not None else None
    star = physics.star(sec) if sec is not None else {"mass": 1, "luminosity": 1}
    lum = float(star.get("luminosity", 1) or 1)
    try:
        act = worlds.activity(float(star.get("mass", 1)), worlds.world_age(kernel, planet, cycle))
        act0 = worlds.activity(1.0, 4.57)
        act = act / max(1e-12, act0)
    except Exception:
        act = 1.0
    p = wind_pressure(w, act, lum)
    galactic = 1.0
    if kernel is not None and cosmos.is_cosmic(kernel):
        g = cosmos.stats(kernel)["place"].get(str(planet.sector_id), {})
        if g.get("r") is not None:
            galactic = cosmos.cosmic_rays(float(g["r"]))
    return {"margin": round(margin(w), 4), "field": round(surface_field(w), 4), "standoff": round(standoff(w, p), 2),
            "exposure": round(exposure(w, p), 4), "dose": round(dose(w, p, galactic), 4)}


def health(kernel: Any, planet: Any) -> float:
    """The share of a people's newborns its world's radiation spares, against the world it arose on: its repair is
    tuned to its home's dose, and each home dose more erases about what a home dose does over a life (linear, no
    threshold). Its people under the open sky take its surface dose; those in its habitats are shielded. 1 at home or
    anywhere gentler; remembered for a clock century (the field changes on deep time)."""
    if kernel is None:
        return 1.0
    soc = planet.society
    key = int(getattr(kernel, "cycle_count", 0)) // 100
    got = soc.get("_rad")
    if got and got[0] == key:
        return float(got[1])
    from xylarium.kernel import biosphere, relations, sustenance, worlds

    def lived(world: Any) -> float:
        """The dose its people live under: none where its medium lies under ice or deep (the overburden shields
        it) or nowhere on the world (it lives in what it has built); else its surface dose on those under the open
        sky (its habitats shield the rest)."""
        try:
            med = worlds.best(worlds.of_planet(kernel, world), biosphere.metabolism_of(kernel, world))
        except Exception:
            med = None
        if med is None or med.get("where") != "surface":
            return 0.0                                  # no medium of its own under this sky: it lives enclosed
        return of_planet(kernel, world)["dose"] * biosphere.open_share(kernel, world)
    here = lived(planet)
    people = sustenance.people_of(planet)
    own = [w for w in (relations._peoples(kernel).get(people) or []) if w.population > 0] if people else []
    home_world = max(own, key=lambda w: w.population) if own else planet     # where most of its kind still live
    base = here if home_world is planet else lived(home_world)
    excess = max(0.0, here / max(1e-9, base) - 1.0)
    # the bell's quantum radiation (field.quantum_flux), by the same law: its repair is tuned to its home's flux,
    # each home flux more erases about what a home dose does - a pressure like any other on whom its world spares
    from xylarium.kernel import field
    q_here, q_home = field.quantum_flux(kernel, planet), field.quantum_flux(kernel, home_world)
    if q_here > 0 and q_home > 0:
        excess += max(0.0, float(q_here / q_home) - 1.0)
    value = math.exp(-excess * HOME_LIFETIME_RISK)
    soc["_rad"] = [key, round(value, 6)]
    return value

