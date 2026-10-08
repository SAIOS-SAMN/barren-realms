"""
Xylarium substances: the matter the board is laid with - measured, never invented - and the few formulas every
people, of any chemistry, meets it through.

The ancients lay down matter, not uses. Every good is a substance: an element (a nucleus of Z protons and A
nucleons), a compound (a formula of elements, with the energy its bonds hold), an alloy, or a phase of one of these
(ionised hydrogen). What a substance is FOR is never written here; it is read from the agent that meets it (uses.py,
and the operators built on this table).

ELEMENTS carry measured data: Z, A, melting and boiling points (1 bar), density, cosmic abundance (Lodders 2003,
atoms per million Si), the temperature half of it had condensed at in a cooling nebula (Lodders 2003), and Pauling
electronegativity (how hard its atoms pull on shared electrons - what decides which bonds form and break).

THE SUPERHEAVIES. The almanac's deep exotics are nuclei past uranium, on the predicted islands of stability (closed
shells near Z 114-126, N 184; a second near Z 164). Nothing measured says how they behave, so each takes its
chemical homologue's (the element above it in its group): melting, boiling, condensation, electronegativity, and
the homologue's molar volume (density x A / A_homologue). Their abundance extends the measured fall of the
r-process from platinum to uranium (0.156 dex per proton) past uranium; how long they live is the island's
assumption (stated, not measured). Only an r-process makes them: a neutron-rich lineage (stellar mergers).

COMPOUNDS carry measured standard enthalpy of formation and entropy (NIST-JANAF / CODATA), melting and boiling (or
decomposition) points and density, and their ORIGIN - where in a world physics lays them down: ice (condensed
volatiles), mineral (rock), deep (made only under the pressure of a big world's lower mantle), core (metal that sinks
in a melted world), photochemical (made by starlight from methane in a cold sky), biogenic (made only by living
chemistry). The almanac's named compounds are the real things their descriptions are: cryogenite the nitrogen
ices, stelalith bridgmanite (the deep mantle's perovskite), ferrolattice meteoric iron-nickel, chitinium chitin,
void-resin the tholins of cold skies, sol-plasma ionised hydrogen.

FORMULAS (the same for every agent):
  binding(A, Z)        nuclear binding energy, the semi-empirical mass formula (Weizsaecker; fitted coefficients):
                       what fusion gains up to iron and what transmutation past it costs
  dG(reaction, T)      Delta H - T Delta S of a reaction from the compounds' formation data (Ellingham): whether it
                       runs by itself at a temperature, and how much free energy it gives or takes
  phase(sym, T, P)     solid, liquid, gas or plasma at a temperature and pressure - boiling point moved by pressure
                       through Clausius-Clapeyron with Trouton's rule for the heat of vaporisation
  separation_work(x,T) the least work to take a substance out of a mixture where it is a fraction x: -RT ln x
"""

import math
from typing import Any, Dict, List, Optional, Tuple

R = 8.314462618                 # J/(mol K)
EV_KJ_MOL = 96.485              # one electronvolt per particle, in kJ/mol
MEV_KJ_MOL = 96.485e6
TROUTON = 88.0                  # J/(mol K): entropy of vaporisation of most liquids at their boiling point
IONISE_K = 1.0e4                # hydrogen is mostly ionised above ~10^4 K (Saha, at low density)

# symbol: (Z, A, melt K, boil K, density g/cc, abundance per 1e6 Si, 50% condensation K, Pauling chi)
ELEMENTS: Dict[str, Tuple[int, float, float, float, float, float, float, Optional[float]]] = {
    "H": (1, 1.008, 14.0, 20.3, 0.071, 2.43e10, 5, 2.20),
    "He": (2, 4.003, 0.95, 4.2, 0.125, 2.34e9, 3, None),
    "He-3": (2, 3.016, 0.0, 3.2, 0.059, 4.5e5, 3, None),       # the light isotope: the solar wind's, by its ratio
    "C": (6, 12.011, 3915.0, 4098.0, 2.26, 7.08e6, 40, 2.55),
    "N": (7, 14.007, 63.2, 77.4, 0.81, 1.95e6, 123, 3.04),
    "O": (8, 15.999, 54.4, 90.2, 1.14, 1.41e7, 180, 3.44),
    "Ne": (10, 20.180, 24.6, 27.1, 1.21, 2.36e6, 9, None),
    "Na": (11, 22.990, 371.0, 1156.0, 0.97, 5.75e4, 958, 0.93),
    "Mg": (12, 24.305, 923.0, 1363.0, 1.74, 1.02e6, 1336, 1.31),
    "Al": (13, 26.982, 933.5, 2792.0, 2.70, 8.41e4, 1653, 1.61),
    "Si": (14, 28.085, 1687.0, 3538.0, 2.33, 1.00e6, 1310, 1.90),
    "P": (15, 30.974, 317.3, 553.7, 1.82, 8.37e3, 1229, 2.19),
    "S": (16, 32.06, 388.4, 717.8, 2.07, 4.45e5, 664, 2.58),
    "Cl": (17, 35.45, 171.6, 239.1, 1.56, 5.24e3, 948, 3.16),
    "Ar": (18, 39.948, 83.8, 87.3, 1.40, 1.03e5, 48, None),
    "K": (19, 39.098, 336.5, 1032.0, 0.86, 3.69e3, 1006, 0.82),
    "Ca": (20, 40.078, 1115.0, 1757.0, 1.55, 6.29e4, 1517, 1.00),
    "Ti": (22, 47.867, 1941.0, 3560.0, 4.51, 2.42e3, 1582, 1.54),
    "Cr": (24, 51.996, 2180.0, 2944.0, 7.19, 1.29e4, 1296, 1.66),
    "Mn": (25, 54.938, 1519.0, 2334.0, 7.21, 9.17e3, 1158, 1.55),
    "Fe": (26, 55.845, 1811.0, 3134.0, 7.87, 8.38e5, 1334, 1.83),
    "Ni": (28, 58.693, 1728.0, 3186.0, 8.91, 4.78e4, 1353, 1.91),
    "Cu": (29, 63.546, 1358.0, 2835.0, 8.96, 5.27e2, 1037, 1.90),
    "Zn": (30, 65.38, 692.7, 1180.0, 7.14, 1.23e3, 726, 1.65),
    "Xe": (54, 131.29, 161.4, 165.1, 3.06, 5.39, 68, 2.60),
    "Ba": (56, 137.33, 1000.0, 2170.0, 3.51, 4.4, 1455, 0.89),
    "Pt": (78, 195.08, 2041.0, 4098.0, 21.45, 1.37, 1408, 2.28),
    "Au": (79, 196.97, 1337.0, 3129.0, 19.3, 0.195, 1060, 2.54),
    "Pb": (82, 207.2, 600.6, 2022.0, 11.34, 3.26, 727, 2.33),
    "Rn": (86, 222.0, 202.0, 211.5, 4.4, 0.0, 30, 2.2),           # only ever a decay daughter
    "Ra": (88, 226.0, 973.0, 2010.0, 5.5, 0.0, 1455, 0.9),        # only ever a decay daughter (Ba's condensation)
    "Th": (90, 232.04, 2023.0, 5061.0, 11.7, 0.0335, 1659, 1.30),
    "U": (92, 238.03, 1405.0, 4404.0, 19.1, 0.009, 1610, 1.38),
}

# the r-process's measured fall from its third peak to the actinides: log10(Pt / U) over (92 - 78) protons
R_PROCESS_DEX_PER_Z = math.log10(ELEMENTS["Pt"][5] / ELEMENTS["U"][5]) / (92 - 78)
# good id: (Z, A, homologue). Oganesson (118) has measured mass and published predictions; the rest take homologues
SUPERHEAVY = {
    "pyrosite": (114, 298, "Pb"),       # flerovium on the island (N 184): eka-lead
    "SpR": (118, 294, "Rn"),            # oganesson: the rime of the last noble group
    "umbrite": (120, 304, "Ra"),        # eka-radium
    "aetherium": (122, 306, "Th"),      # the superactinides begin: eka-thorium
    "AdL": (126, 310, "U"),             # the predicted doubly closed shell (Z 126, N 184)
    "mirror_glass": (164, 482, "Pb"),   # the second island: eka-flerovium
}
OGANESSON = {"melt": 325.0, "boil": 450.0, "rho": 7.2}       # relativistic predictions (Smits et al. 2020)

# compounds: formula, Delta Hf (kJ/mol), S (J/mol K), melt K, boil (or decomposition) K, density, origin
COMPOUNDS: Dict[str, Dict[str, Any]] = {
    "H2O": {"f": {"H": 2, "O": 1}, "dH": -285.83, "S": 69.95, "melt": 273.15, "boil": 373.15, "rho": 1.0,
            "origin": "ice", "tc": 182, "gas": (-241.82, 188.84)},
    "NH3": {"f": {"N": 1, "H": 3}, "dH": -45.9, "S": 192.8, "melt": 195.4, "boil": 239.8, "rho": 0.68,
            "origin": "ice", "tc": 131},
    "N2": {"f": {"N": 2}, "dH": 0.0, "S": 191.6, "melt": 63.2, "boil": 77.4, "rho": 0.81, "origin": "ice", "tc": 22},
    "CH4": {"f": {"C": 1, "H": 4}, "dH": -74.6, "S": 186.3, "melt": 90.7, "boil": 111.7, "rho": 0.42,
            "origin": "ice", "tc": 41},
    "CO": {"f": {"C": 1, "O": 1}, "dH": -110.5, "S": 197.7, "melt": 68.1, "boil": 81.6, "rho": 0.79,
           "origin": "ice", "tc": 25},
    "CO2": {"f": {"C": 1, "O": 2}, "dH": -393.5, "S": 213.8, "melt": 216.6, "boil": 194.7, "rho": 1.56,
            "origin": "ice", "tc": 72},
    "O2": {"f": {"O": 2}, "dH": 0.0, "S": 205.2, "melt": 54.4, "boil": 90.2, "rho": 1.14, "origin": "biogenic"},
    "C6H12O6": {"f": {"C": 6, "H": 12, "O": 6}, "dH": -1273.3, "S": 212.1, "melt": 419.0, "boil": 573.0,
                "rho": 1.54, "origin": "biogenic"},          # glucose: what carbon life fixes (NIST)
    "H2": {"f": {"H": 2}, "dH": 0.0, "S": 130.7, "melt": 14.0, "boil": 20.3, "rho": 0.071, "origin": "ice", "tc": 5},
    "NaCl": {"f": {"Na": 1, "Cl": 1}, "dH": -411.2, "S": 72.1, "melt": 1074.0, "boil": 1738.0, "rho": 2.17,
             "origin": "mineral", "tc": 948},
    "MgSiO3": {"f": {"Mg": 1, "Si": 1, "O": 3}, "dH": -1545.0, "S": 67.9, "melt": 1830.0, "boil": 3000.0,
               "rho": 3.2, "origin": "mineral", "tc": 1316},
    "SiO2": {"f": {"Si": 1, "O": 2}, "dH": -910.7, "S": 41.5, "melt": 1986.0, "boil": 2503.0, "rho": 2.65,
             "origin": "mineral", "tc": 1310},
    "MgO": {"f": {"Mg": 1, "O": 1}, "dH": -601.6, "S": 26.9, "melt": 3098.0, "boil": 3870.0, "rho": 3.58,
            "origin": "mineral", "tc": 1336},
    "Al2O3": {"f": {"Al": 2, "O": 3}, "dH": -1675.7, "S": 50.9, "melt": 2345.0, "boil": 3250.0, "rho": 3.95,
              "origin": "mineral", "tc": 1653},
    "CaO": {"f": {"Ca": 1, "O": 1}, "dH": -634.9, "S": 38.1, "melt": 2886.0, "boil": 3123.0, "rho": 3.34,
            "origin": "mineral", "tc": 1517},
    "FeO": {"f": {"Fe": 1, "O": 1}, "dH": -272.0, "S": 60.75, "melt": 1650.0, "boil": 3687.0, "rho": 5.7,
            "origin": "mineral", "tc": 1334},
    "Fe2O3": {"f": {"Fe": 2, "O": 3}, "dH": -824.2, "S": 87.4, "melt": 1838.0, "boil": 1838.0, "rho": 5.24,
              "origin": "mineral", "tc": 1334},
    "FeS": {"f": {"Fe": 1, "S": 1}, "dH": -100.0, "S": 60.3, "melt": 1467.0, "boil": 1467.0, "rho": 4.84,
            "origin": "mineral", "tc": 664},
    "TiO2": {"f": {"Ti": 1, "O": 2}, "dH": -944.0, "S": 50.6, "melt": 2116.0, "boil": 3245.0, "rho": 4.23,
             "origin": "mineral", "tc": 1582},
    "Cu2S": {"f": {"Cu": 2, "S": 1}, "dH": -79.5, "S": 120.9, "melt": 1403.0, "boil": 1403.0, "rho": 5.6,
             "origin": "mineral", "tc": 664},
    "CuO": {"f": {"Cu": 1, "O": 1}, "dH": -157.3, "S": 42.6, "melt": 1599.0, "boil": 1599.0, "rho": 6.31,
            "origin": "mineral", "tc": 1037},
    "NiO": {"f": {"Ni": 1, "O": 1}, "dH": -239.7, "S": 38.0, "melt": 2228.0, "boil": 2228.0, "rho": 6.67,
            "origin": "mineral", "tc": 1353},
    "UO2": {"f": {"U": 1, "O": 2}, "dH": -1085.0, "S": 77.0, "melt": 3138.0, "boil": 3815.0, "rho": 10.97,
            "origin": "mineral", "tc": 1610},
    # the almanac's named compounds, as the real things they describe
    "cryogenite": {"f": {"N": 1, "H": 3}, "dH": -45.9, "S": 192.8, "melt": 195.4, "boil": 239.8, "rho": 0.81,
                   "origin": "ice", "tc": 131, "as": "the nitrogen ices: ammonia with frozen nitrogen"},
    "stelalith": {"f": {"Mg": 1, "Si": 1, "O": 3}, "dH": -1450.0, "S": 57.2, "melt": 2900.0, "boil": 3000.0,
                  "rho": 4.1, "origin": "deep", "tc": 1316, "as": "bridgmanite, the perovskite of a deep mantle"},
    "ferrolattice": {"f": {"Fe": 0.93, "Ni": 0.07}, "dH": 0.0, "S": 27.5, "melt": 1770.0, "boil": 3134.0,
                     "rho": 7.9, "origin": "core", "tc": 1340, "as": "kamacite: meteoric iron-nickel"},
    "chitinium": {"f": {"C": 8, "H": 13, "N": 1, "O": 5}, "dH": -1050.0, "S": 290.0, "melt": 563.0, "boil": 563.0,
                  "rho": 1.43, "origin": "biogenic", "as": "chitin: the polymer carbon-water life armours itself in"},
    "void_resin": {"f": {"C": 1, "H": 2}, "dH": -28.0, "S": 50.0, "melt": 400.0, "boil": 600.0, "rho": 1.0,
                   "origin": "photochemical", "tc": 90, "as": "tholins: the polymers starlight makes from methane"},
    "sol_plasma": {"f": {"H": 1}, "dH": 1312.0, "S": 0.0, "melt": IONISE_K, "boil": IONISE_K, "rho": 1e-4,
                   "origin": "stellar", "as": "ionised hydrogen: a star's own matter"},
}
# the bridgmanite field: a mantle makes it only past this pressure (GPa; the 660 km discontinuity on Earth)
BRIDGMANITE_GPA = 24.0
EARTH_CMB_GPA = 136.0           # Earth's core-mantle boundary pressure (measured, PREM)
# SEMF coefficients (MeV): volume, surface, Coulomb, asymmetry, pairing
A_V, A_S, A_C, A_A, A_P = 15.75, 17.8, 0.711, 23.7, 11.18


# ---------------------------------------------------------------------- reading the table
def _homologue(sym: str) -> Tuple[int, float, float, float, float, float, float, Optional[float]]:
    z, a, h = SUPERHEAVY[sym]
    hz, ha, hm, hb, hr, _, htc, hchi = ELEMENTS[h]
    hb0 = hb
    if sym == "SpR":
        hm, hb, hr = OGANESSON["melt"], OGANESSON["boil"], OGANESSON["rho"] * ha / a
    ab = ELEMENTS["U"][5] * 10 ** (-R_PROCESS_DEX_PER_Z * (z - 92))
    tc = htc * hb / hb0                       # it condenses as much warmer than its homologue as it boils
    return z, float(a), hm, hb, hr * a / ha, ab, tc, hchi


def element(sym: str) -> Optional[Dict[str, Any]]:
    row = ELEMENTS.get(sym) or (_homologue(sym) if sym in SUPERHEAVY else None)
    if row is None:
        return None
    z, a, m, b, rho, ab, tc, chi = row
    return {"Z": z, "A": a, "melt": m, "boil": b, "rho": rho, "abund": ab, "tc": tc, "chi": chi,
            "period": period(z), "group": group(z), "kind": "superheavy" if sym in SUPERHEAVY else "element"}


def compound(sym: str) -> Optional[Dict[str, Any]]:
    c = COMPOUNDS.get(sym)
    return dict(c, kind="compound") if c else None


def get(sym: str) -> Optional[Dict[str, Any]]:
    return element(sym) or compound(sym)


def known_symbols() -> List[str]:
    return list(ELEMENTS) + list(SUPERHEAVY) + list(COMPOUNDS)


def molar_mass(sym: str) -> Optional[float]:
    e = element(sym)
    if e:
        return e["A"]
    c = COMPOUNDS.get(sym)
    if not c:
        return None
    return sum(n * (element(x)["A"]) for x, n in c["f"].items())


def melt(sym: str) -> Optional[float]:
    s = get(sym)
    return float(s["melt"]) if s else None


def boil(sym: str) -> Optional[float]:
    s = get(sym)
    return float(s["boil"]) if s else None


def constituents(sym: str) -> Dict[str, float]:
    if sym in COMPOUNDS:
        return dict(COMPOUNDS[sym]["f"])
    return {sym: 1.0} if element(sym) else {}


def abundance(sym: str) -> float:
    """Atoms (or formula units) per million silicon: an element's measured; a compound's limited by the scarcest of
    what it is made of."""
    e = element(sym)
    if e:
        return float(e["abund"])
    f = constituents(sym)
    return min((element(x)["abund"] / n for x, n in f.items()), default=0.0)


# ---------------------------------------------------------------------- the periodic table, from Z alone
_PERIOD_ENDS = (2, 10, 18, 36, 54, 86, 118, 168)


def period(z: int) -> int:
    for i, end in enumerate(_PERIOD_ENDS):
        if z <= end:
            return i + 1
    return len(_PERIOD_ENDS) + 1


def group(z: int) -> int:
    """Its group (1-18) by where it falls in its period; the f- and g-block rows sit in group 3."""
    if z == 1:
        return 1
    if z == 2:
        return 18
    p = period(z)
    start = _PERIOD_ENDS[p - 2] + 1
    pos = z - start + 1
    if p in (2, 3):
        return pos if pos <= 2 else pos + 10
    if p in (4, 5):
        return pos
    width = _PERIOD_ENDS[p - 1] - _PERIOD_ENDS[p - 2]       # 32 in periods 6 and 7, 50 in period 8
    inner = width - 18                                        # the f (and g) rows
    if pos <= 2:
        return pos
    if pos <= 2 + inner + 1:
        return 3
    return pos - inner


# ---------------------------------------------------------------------- the nucleus
# Measured binding energies (MeV) of the light nuclei, where the semi-empirical formula is known to fail - it
# under-binds the alpha-like nuclei of the light shells (helium-4 most of all), and the burning of stars runs exactly
# there. Nature's own values (atomic mass evaluation), as the table's melting points are; heavier nuclei take the
# formula.
MEASURED_BINDING_MEV = {(2, 1): 2.2246, (3, 1): 8.4818, (3, 2): 7.7180, (4, 2): 28.2957, (6, 3): 31.9940,
                        (7, 3): 39.2446, (9, 4): 58.1650, (12, 6): 92.1622, (14, 7): 104.6587, (16, 8): 127.6193,
                        (20, 10): 160.6448, (24, 12): 198.2569, (28, 14): 236.5368, (32, 16): 271.7807,
                        (56, 26): 492.2579}


def binding(a: float, z: int) -> float:
    """Nuclear binding energy (MeV): measured for the light nuclei and iron (MEASURED_BINDING_MEV), else Weizsaecker's
    semi-empirical mass formula - which tells how energy runs along the table (rising to iron, falling past it)."""
    got = MEASURED_BINDING_MEV.get((int(round(float(a))), int(z)))
    if got is not None:
        return got
    a = float(a)
    if a <= 1:
        return 0.0
    n = a - z
    b = A_V * a - A_S * a ** (2 / 3) - A_C * z * (z - 1) / a ** (1 / 3) - A_A * (n - z) ** 2 / a
    ia, iz = int(round(a)), int(z)
    if ia % 2 == 0:
        b += A_P / math.sqrt(a) if iz % 2 == 0 else -A_P / math.sqrt(a)
    return max(0.0, b)


def binding_per_nucleon(sym: str) -> Optional[float]:
    e = element(sym)
    return binding(e["A"], e["Z"]) / e["A"] if e else None


def transmutation_mev(inputs: Dict[str, float], outputs: Dict[str, float]) -> float:
    """Energy a nuclear change releases (positive) or takes (negative), from binding energies, per reaction."""
    def total(side):
        s = 0.0
        for sym, n in side.items():
            e = element(sym)
            if e is None:
                for x, k in constituents(sym).items():
                    ex = element(x)
                    s += n * k * binding(ex["A"], ex["Z"])
            else:
                s += n * binding(e["A"], e["Z"])
        return s
    return total(outputs) - total(inputs)


# ---------------------------------------------------------------------- bonds
def formation(sym: str, t: Optional[float] = None) -> Tuple[float, float]:
    """(Delta Hf kJ/mol, S J/mol K) of a substance - its gas's where it has boiled at t; an element in its own
    standard state forms from nothing."""
    c = COMPOUNDS.get(sym)
    if c:
        if t is not None and "gas" in c and t >= float(c["boil"]):
            return float(c["gas"][0]), float(c["gas"][1])
        return float(c["dH"]), float(c["S"])
    return 0.0, 0.0


def dG(reactants: Dict[str, float], products: Dict[str, float], t: float) -> float:
    """Free energy (kJ) of a reaction at temperature t: negative runs by itself. Entropies of elements are taken at
    their standard state's (zero difference where they appear on both sides)."""
    dh = sum(n * formation(s, t)[0] for s, n in products.items()) - \
        sum(n * formation(s, t)[0] for s, n in reactants.items())
    ds = sum(n * _entropy(s, t) for s, n in products.items()) - sum(n * _entropy(s, t) for s, n in reactants.items())
    return dh - t * ds / 1000.0


_ELEMENT_S = {"H": 65.3, "O": 102.6, "N": 95.8, "C": 5.74, "Fe": 27.3, "Ti": 30.7, "Cu": 33.2, "Ni": 29.9,
              "Si": 18.8, "Mg": 32.7, "Al": 28.3, "Ca": 41.6, "Na": 51.3, "Cl": 111.5, "S": 32.1, "U": 50.2}
# (per atom: H2, O2, N2 and Cl2 halved - standard molar entropies, CODATA)


def _entropy(sym: str, t: Optional[float] = None) -> float:
    if sym in COMPOUNDS:
        return formation(sym, t)[1]
    return _ELEMENT_S.get(sym, 30.0)


def reduction_t(oxide: str, reductant: str = "C") -> Optional[float]:
    """The lowest temperature (K) at which a reductant frees the metal of an oxide (or sulphide) by itself - where
    the reaction's free energy crosses zero (the Ellingham crossing). None where it never does below 4000 K."""
    f = COMPOUNDS.get(oxide, {}).get("f")
    if not f:
        return None
    o = f.get("O", 0)
    metal = {k: v for k, v in f.items() if k not in ("O", "S")}
    if not o:
        return None
    if reductant == "C":
        reac, prod = {oxide: 1, "C": o}, {**metal, "CO": o}
    elif reductant == "H":
        reac, prod = {oxide: 1, "H2": o}, {**metal, "H2O": o}
    else:                                                     # a more reactive metal taking the oxygen
        ox = next((k for k, c in COMPOUNDS.items() if c["f"] == {reductant: 1, "O": 1}), None)
        if ox is None:
            return None
        reac, prod = {oxide: 1, reductant: o}, {**metal, ox: o}
    for t in range(200, 4001, 25):
        if dG(reac, prod, float(t)) < 0:
            return float(t)
    return None


# ---------------------------------------------------------------------- phase
def boil_at(sym: str, p_bar: float) -> Optional[float]:
    """Boiling point at a pressure: Clausius-Clapeyron, with Trouton's rule for the heat of vaporisation."""
    tb = boil(sym)
    if tb is None or tb <= 0:
        return None
    p = max(p_bar, 1e-12)
    # 1/T = 1/Tb - R ln(P) / dHvap, dHvap = TROUTON x Tb
    inv = 1.0 / tb - R * math.log(p) / (TROUTON * tb)
    return 1.0 / inv if inv > 0 else float("inf")


def phase(sym: str, t: float, p_bar: float = 1.0) -> Optional[str]:
    s = get(sym)
    if s is None:
        return None
    if t >= IONISE_K:
        return "plasma"
    if s.get("origin") == "stellar":
        return "plasma"
    tm = float(s["melt"])
    tb = boil_at(sym, p_bar) or float(s["boil"])
    if t < tm:
        return "solid"
    if t < tb:
        return "liquid"
    return "gas"


def separation_work(x: float, t: float) -> float:
    """Least work (kJ/mol) to take a substance out of a mixture where it is mole fraction x, at temperature t."""
    x = min(1.0, max(x, 1e-30))
    return -R * t * math.log(x) / 1000.0


# ---------------------------------------------------------------------- where a world can hold it
def deep_mantle(mass: float, radius: float) -> bool:
    """Does a world's lower mantle reach bridgmanite's pressure? Central pressure scales as M^2 / R^4 (hydrostatic,
    uniform density), scaled to Earth's measured core-mantle boundary."""
    if radius <= 0:
        return False
    return EARTH_CMB_GPA * mass ** 2 / radius ** 4 >= BRIDGMANITE_GPA
