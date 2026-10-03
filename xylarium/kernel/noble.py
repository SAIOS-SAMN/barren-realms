"""
Xylarium noble gases: the xenon in a world's air, and what it remembers.

Xenon is too heavy to leave a world by the gentle routes that strip its lighter air, and its isotopes are made by
clocks that ran only in a world's first hundred million years - so the xenon in an air is a record of how the world
was built, when its mantle closed, what it lost young, and what was later done to it:

  PRIMORDIAL   xenon in the solar mix (XE_SOLAR), delivered with the world's volatiles (XE132_PER_KG per kg of
               planet - the one inventory number, Earth's air xenon per kg of Earth: a best guess)
  RADIOGENIC   iodine-129 (half-life 15.7 Myr) decays to xenon-129. What decays while the world is still molten
               joins its first air; what decays after the mantle closes stays in the rock until the mantle's
               convection melts and degasses it (worlds.build: processed). A world built fast - an embryo that
               gathered its feeding zone and stopped (below its isolation mass) - closes while iodine-129 still
               lives, and later breathes out its xenon-129; a world finished by giant impacts closes after
               iodine-129 is nearly gone.
  FISSION      plutonium-244 (80 Myr) splits spontaneously, leaving xenon-131 to 136 - most of all 136, none of 129.
  EARLY LOSS   a young star's ultraviolet drives hydrogen off; escaping hydrogen drags heavier atoms with it up to
               the crossover mass m_c = m_H + kT F_H / (b g x_H) (Hunten et al. 1987). Xenon goes only if m_c passes
               its mass - the world's first air's xenon then leaves, fractionated, and only what is breathed out later
               is left.
  WEAPONS      a fission war adds its yields - xenon-131, 132, 134 and 136 at once, and xenon-129 only as its
               iodine-129 decays over tens of Myr. Even fully decayed, fission xenon holds 129/132 ~ 0.17
               (fission_129_132): a fission war pulls an air's 129/132 down toward that, never up past the solar mix.
               Antimatter adds no xenon at all.

EARLY LOSS, IONS AND IMPACTS: xenon ionises more easily than hydrogen, so in a young world's hydrogen wind its ions
are dragged out by Coulomb collisions far stronger than its atoms' (ION_COULOMB; Zahnle et al. 2019) - the crossover
for ions passes xenon's mass, and the first air's xenon goes in proportion to the hydrogen the world loses then
(worlds.build: air_escaped). A world finished by giant impacts loses part of its magma ocean's air with each
(GIANT_IMPACT_AIR_LOSS). The absolute ratios rest on these declared numbers and on the inventories (best guesses);
the ordering of worlds by how early they closed, and what fission can and cannot do, do not.

So the ratio xenon-129 / xenon-132 in an air says how early the world closed and how much of its first air it
lost; xenon-136 / xenon-132 above the solar mix says plutonium-244 - or fission weapons.
"""

import math
from typing import Any, Dict, List, Optional

XE_SOLAR = {129: 1.04, 131: 0.83, 132: 1.0, 134: 0.37, 136: 0.30}   # per xenon-132 (solar wind; Meshik et al.)
I129_I127_0 = 1.0e-4            # iodine-129 / iodine-127 at the star's birth (meteorites; Hohenberg & Pravdivtseva)
T_I129_MYR = 15.7
T_PU244_MYR = 80.0
PU244_U238_0 = 0.0068           # plutonium-244 / uranium-238 at the star's birth (meteorites)
PU244_SF = 1.23e-3              # share of plutonium-244 decays that are spontaneous fission
PU_XE = {131: 0.014, 132: 0.049, 134: 0.052, 136: 0.056}   # xenon per plutonium-244 fission (Hudson et al. 1989)
U_WEAPON_XE = {131: 0.029, 132: 0.043, 134: 0.079, 136: 0.063}   # cumulative xenon yields of uranium-235 fission
U_WEAPON_I129 = 0.0075          # iodine-129 per fission (cumulative yield): becomes xenon-129 over tens of Myr
MANTLE_I_KG = 1.0e-8            # iodine per kg of mantle (~10 ppb; Earth's mantle estimates: a best guess)
XE132_PER_KG = 4.0e11           # primordial xenon-132 atoms per kg of planet (Earth's air xenon per kg of Earth)
GIANT_IMPACT_MYR = 50.0         # the giant-impact phase at 1 AU (Chambers 2001: tens of Myr), scaling with the year
EMBRYO_MYR = 3.0                # an isolated embryo's growth and its magma ocean's freezing (Mars: ~2-4 Myr; Dauphas &
                                # Pourmand 2011)
FISSION_J = 3.2e-11             # energy per fission (200 MeV)
AMU = 1.66054e-27
EUV_1AU_W = 1.0e-3              # a quiet Sun's extreme ultraviolet at 1 AU (W/m^2)
EUV_HEATING = 0.15              # share of absorbed EUV that lifts gas out (energy-limited escape; Watson et al. 1981)
B_H = 1.9e21                    # binary diffusion parameter of H in heavier gas, m^-1 s^-1 at 300 K (~ T^0.75)
KB = 1.380649e-23
ION_COULOMB = 300.0             # xenon ions' coupling to an escaping proton wind over a neutral's (Coulomb against
                                # neutral collision cross-sections; Zahnle, Gacesa & Catling 2019): xenon ionises more
                                # easily than hydrogen, and its ions are dragged where its atoms would stay
GIANT_IMPACT_AIR_LOSS = 0.5     # share of a magma ocean's air each giant impact blows off (Schlichting et al. 2015:
                                # tens of percent, more over an ocean; declared)


def closure_myr(mass: float, a_au: float, star_mass: float = 1.0, z: float = 1.0) -> float:
    """When a world's mantle closed: an embryo that stopped at its isolation mass closes as it freezes; a world
    finished by giant impacts closes with the last of them (the phase scaling with the orbital period, and with how
    many doublings past isolation it needed)."""
    from xylarium.kernel import worlds
    m_iso = worlds.isolation_mass(star_mass, a_au, z)
    if mass <= 2.0 * m_iso:
        return EMBRYO_MYR
    doublings = math.log(mass / m_iso) / math.log(worlds.GIANT_IMPACT_GROWTH)
    return EMBRYO_MYR + GIANT_IMPACT_MYR * a_au ** 1.5 / max(0.08, star_mass) ** 0.5 * doublings


def crossover_amu(mass: float, radius: float, a_au: float, t_exo: float, activity: float) -> float:
    """The heaviest atom escaping hydrogen drags off (Hunten's crossover), under energy-limited escape driven by the
    star's EUV at the world (activity: the young star's saturation)."""
    from xylarium.kernel import interior
    m_kg, r_m = mass * interior.M_EARTH_KG, radius * interior.R_EARTH_M
    g = interior.G_SI * m_kg / r_m ** 2
    phi = EUV_HEATING * EUV_1AU_W * activity / a_au ** 2 / (4.0 * interior.G_SI * m_kg / r_m)   # kg/m^2/s
    f_h = phi / AMU
    b = B_H * (max(100.0, t_exo) / 300.0) ** 0.75
    return 1.0 + KB * max(100.0, t_exo) * f_h / (b * g * AMU)


def air_xenon(mass: float, radius: float, a_au: float, star_mass: float, history: List[Dict[str, Any]],
              wars: Optional[List[Dict[str, float]]] = None, z: float = 1.0) -> List[Dict[str, Any]]:
    """The xenon in a world's air through its history (history: worlds.build at each age, with degassed/processed/
    t_exo), as ratios to xenon-132 - and the crossover mass its young star drove. wars: [{"age": Gyr, "fission_j":
    energy}] - fission weapons used on it."""
    from xylarium.kernel import interior, worlds
    kg = mass * interior.M_EARTH_KG
    close = closure_myr(mass, a_au, star_mass, z)
    tau_i, tau_pu = T_I129_MYR / math.log(2), T_PU244_MYR / math.log(2)
    i127 = MANTLE_I_KG / (127 * AMU) * kg
    i129_0 = i127 * I129_I127_0
    u238 = 20e-9 * 0.9928 / (238 * AMU) * kg * math.exp(interior.SOLAR_AGE_GYR / 6.446)   # at the star's birth
    pu_0 = u238 * PU244_U238_0
    prim = {iso: XE132_PER_KG * kg * r for iso, r in XE_SOLAR.items()}
    early_129 = i129_0 * (1.0 - math.exp(-close / tau_i))           # decayed while molten: into the first air
    late_129 = i129_0 * math.exp(-close / tau_i)                    # trapped as iodine, decaying in the rock
    early_fis = pu_0 * PU244_SF * (1.0 - math.exp(-close / tau_pu))
    late_fis = pu_0 * PU244_SF * math.exp(-close / tau_pu)
    young = history[0]
    melted = float(young.get("melted", 1.0))
    first = worlds.MAGMA_DEGAS * melted                              # share of the planet's gas its magma ocean gave up
    m_c = crossover_amu(mass, radius, a_au, float(young.get("t_exo", 1000.0)),
                        worlds.activity(star_mass, 0.0))
    m_ion = 1.0 + (m_c - 1.0) * ION_COULOMB                        # its ions, dragged by the proton wind
    h_lost = max((float(h.get("air_escaped", 0.0)) for h in history if float(h["age"]) <= 1.0), default=0.0)
    drag = 0.0 if m_ion <= 132.0 else (m_ion - 132.0) / max(1e-9, m_ion - 1.0)
    doublings = 0.0
    m_iso = worlds.isolation_mass(star_mass, a_au, z)
    if mass > 2.0 * m_iso:
        doublings = math.log(mass / m_iso) / math.log(worlds.GIANT_IMPACT_GROWTH)
    lost = 1.0 - (1.0 - drag * h_lost) * (1.0 - GIANT_IMPACT_AIR_LOSS) ** doublings
    air = {iso: prim[iso] * first * (1.0 - lost) for iso in prim}
    air[129] += early_129 * first * (1.0 - lost)
    for iso, y in PU_XE.items():
        air[iso] += early_fis * y * first * (1.0 - lost)
    rest = {iso: prim[iso] * (1.0 - first) for iso in prim}          # still in the rock after the magma ocean froze
    out = []
    for h in history:
        age_myr = float(h["age"]) * 1000.0
        late = 1.0 - math.exp(-float(h.get("processed", 0.0)))      # the mantle melted and degassed since it closed
        now = {iso: air[iso] + rest[iso] * late for iso in air}
        now[129] += late_129 * (1.0 - math.exp(-max(0.0, age_myr - close) / tau_i)) * late
        for iso, y in PU_XE.items():
            now[iso] += late_fis * (1.0 - math.exp(-max(0.0, age_myr - close) / tau_pu)) * y * late
        for w in wars or []:
            if float(w["age"]) <= float(h["age"]):
                fissions = float(w["fission_j"]) / FISSION_J
                for iso, y in U_WEAPON_XE.items():
                    now[iso] += fissions * y
                since = (float(h["age"]) - float(w["age"])) * 1000.0
                now[129] += fissions * U_WEAPON_I129 * (1.0 - math.exp(-since / tau_i))
        x132 = max(1e-30, now[132])
        out.append({"age": h["age"], "129/132": round(now[129] / x132, 3), "136/132": round(now[136] / x132, 3),
                    "134/132": round(now[134] / x132, 3), "xe132_atoms": float(f"{now[132]:.3g}")})
    return [{"closure_myr": round(close, 1), "crossover_amu": round(m_c, 2), "ion_crossover_amu": round(m_ion, 1),
             "first_air_lost": round(lost, 3)}] + out


def fission_129_132() -> float:
    """Xenon-129 over xenon-132 in fission xenon once all its iodine-129 has decayed: the most a fission war can
    leave in an air (uranium-235 yields)."""
    return U_WEAPON_I129 / U_WEAPON_XE[132]
