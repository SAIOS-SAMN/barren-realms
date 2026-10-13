"""
Xylarium elements continuum: 118+ periodic element evaluation via semi-empirical
nuclear mass equations and observer-gate spectral sampling (docs/TORSION_CONTINUUM.md).

No individual atoms are computed per tick. The properties of elements Z in 1..118+
are computed analytically from nuclear physics equations, shell closures, and homologue
mappings on-demand when sampled by an observer.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import substances as S

# Magic numbers for nuclear shell closures (extra binding stability)
MAGIC_Z = {2, 8, 20, 28, 50, 82, 114, 120, 126}
MAGIC_N = {2, 8, 20, 28, 50, 82, 126, 184}

# Standard IUPAC symbol table up to Z=118
PERIODIC_SYMBOLS: List[str] = [
    "",
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og"
]


@dataclass(frozen=True)
class ContinuumElement:
    z: int
    symbol: str
    name: str
    a: float
    line: int
    lane: int
    binding_per_nucleon: float
    condensation_k: float
    density_g_cm3: float
    stability_factor: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "z": self.z,
            "symbol": self.symbol,
            "name": self.name,
            "a": round(self.a, 3),
            "line": self.line,
            "lane": self.lane,
            "binding_per_nucleon": round(self.binding_per_nucleon, 4),
            "condensation_k": round(self.condensation_k, 1),
            "density": round(self.density_g_cm3, 3),
            "stability_factor": round(self.stability_factor, 4),
        }


def stable_isotope_a(z: int) -> float:
    """Semi-empirical valley of stability approximation for mass number A."""
    if z <= 20:
        return float(2 * z)
    # Valley of stability: N - Z ~ 0.006 * A^(5/3) or empirical curve
    return float(round(2.0 * z + 0.007 * (z ** 1.8)))


def shell_correction_mev(z: int, a: float) -> float:
    """Extra nuclear stability from magic proton/neutron shell closure."""
    n = int(round(a - z))
    bonus = 0.0
    if z in MAGIC_Z:
        bonus += 3.5
    if n in MAGIC_N:
        bonus += 4.5
    return bonus


IUPAC_DIGITS = {
    0: ("nil", "n"),
    1: ("un", "u"),
    2: ("bi", "b"),
    3: ("tri", "t"),
    4: ("quad", "q"),
    5: ("pent", "p"),
    6: ("hex", "h"),
    7: ("sept", "s"),
    8: ("oct", "o"),
    9: ("enn", "e"),
}
IUPAC_CHAR_TO_DIGIT = {v[1]: k for k, v in IUPAC_DIGITS.items()}


def systematic_iupac(z: int) -> Tuple[str, str]:
    """Derive systematic IUPAC 3-letter symbol and Latinate element name for any Z >= 119."""
    digits = [int(d) for d in str(z)]
    sym = "".join(IUPAC_DIGITS[d][1] for d in digits).capitalize()
    roots = [IUPAC_DIGITS[d][0] for d in digits]
    name_root = "".join(roots)
    if name_root.endswith("i"):
        name = (name_root + "um").capitalize()
    else:
        name = (name_root + "ium").capitalize()
    return sym, name


def parse_element_z(element_id: str) -> Optional[int]:
    """Parse atomic number Z from element symbol, IUPAC name, or number."""
    if not element_id or not isinstance(element_id, str):
        return None
    raw = element_id.strip()
    if raw.isdigit():
        return int(raw)

    # Check canonical periodic symbols
    for z, s in enumerate(PERIODIC_SYMBOLS):
        if s and s.lower() == raw.lower():
            return z

    # Check substances.py experimental data
    if raw in S.ELEMENTS:
        return S.ELEMENTS[raw][0]
    for sym, spec in S.ELEMENTS.items():
        if sym.lower() == raw.lower():
            return spec[0]

    # Check precursor superheavies
    if raw in S.SUPERHEAVY:
        return S.SUPERHEAVY[raw][0]
    for sym, spec in S.SUPERHEAVY.items():
        if sym.lower() == raw.lower():
            return spec[0]

    # Check IUPAC systematic symbol (e.g. Uue -> 119, Ubn -> 120, Ubh -> 126)
    low = raw.lower()
    if len(low) == 3 and all(c in IUPAC_CHAR_TO_DIGIT for c in low):
        val = 0
        for c in low:
            val = val * 10 + IUPAC_CHAR_TO_DIGIT[c]
        if val >= 100:
            return val

    return None


def get_element(z: int) -> ContinuumElement:
    """Analytic evaluation of any element Z in 1..118+ on demand."""
    if z < 1:
        z = 1
    if 1 <= z < len(PERIODIC_SYMBOLS) and PERIODIC_SYMBOLS[z]:
        sym = PERIODIC_SYMBOLS[z]
        name = sym
    else:
        sym, name = systematic_iupac(z)

    # Check if substances.py already has measured experimental data
    measured = S.ELEMENTS.get(sym)
    if measured:
        mz, ma, mmelt, mboil, mrho, mabund, mtc, mchi = measured
        line = S.period(z)
        lane = S.group(z)
        bind = S.binding(ma, z) / max(1.0, ma)
        return ContinuumElement(
            z=z, symbol=sym, name=name, a=ma, line=line, lane=lane,
            binding_per_nucleon=bind, condensation_k=float(mtc),
            density_g_cm3=float(mrho), stability_factor=1.0
        )

    # Check if precursor superheavy (e.g. AdL, SpR, pyrosite)
    for sh_sym, sh_spec in S.SUPERHEAVY.items():
        if sh_spec[0] == z:
            sh_data = S.get(sh_sym)
            if sh_data:
                a_sh = float(sh_spec[1])
                line = S.period(z)
                lane = S.group(z)
                bind = S.binding(a_sh, z) / max(1.0, a_sh)
                return ContinuumElement(
                    z=z, symbol=sym, name=name, a=a_sh, line=line, lane=lane,
                    binding_per_nucleon=bind,
                    condensation_k=float(sh_data.get("tc", 1000.0)),
                    density_g_cm3=float(sh_data.get("rho", 15.0)),
                    stability_factor=2.5,
                )

    # Analytic derivation for all other unmeasured/heavy elements
    a = stable_isotope_a(z)
    line = S.period(z)
    lane = S.group(z)

    # Weizsaecker binding energy + shell bonus
    b_total = S.binding(a, z) + shell_correction_mev(z, a)
    b_per_a = b_total / max(1.0, a)

    # Estimated condensation temperature from group homologue
    homologue_z = z - 32 if z > 86 else (z - 18 if z > 36 else z - 8)
    homologue_sym = PERIODIC_SYMBOLS[homologue_z] if 1 <= homologue_z < len(PERIODIC_SYMBOLS) else "Pb"
    homologue = S.ELEMENTS.get(homologue_sym)
    tc = float(homologue[6]) if homologue else 1000.0
    rho = float(homologue[4]) * (a / max(1.0, float(homologue[1]))) if homologue else 10.0

    # Island of stability factor around superheavies
    stability = 1.0 if z <= 82 else (math.exp(-(z - 82) * 0.1) + (1.5 if z in (114, 120, 126) else 0.0))

    return ContinuumElement(
        z=z, symbol=sym, name=name, a=a, line=line, lane=lane,
        binding_per_nucleon=b_per_a, condensation_k=tc,
        density_g_cm3=min(30.0, rho), stability_factor=stability
    )


def sample_spectrum(
    kernel: Any,
    sector_id: int,
    surface_temp_k: float,
    v_esc_relative: float,
) -> Dict[str, float]:
    """Sample the elemental abundance spectrum at an observed planet or orbital body.
    
    Evaluates the 4 gates lazily across the 118-element continuum.
    Torsion wavefronts perturb resonance synthesis of heavy and exotic nuclei.
    """
    from xylarium.kernel import torsion
    wave_amp, wave_phase, chirality = torsion.eval_wavefront(kernel, sector_id)
    
    spectrum: Dict[str, float] = {}
    
    # Sample representative elements across all periods
    for z in range(1, 119):
        el = get_element(z)
        
        # 1. Gate: Resonance & Nucleosynthesis synthesis factor
        # Torsion wave resonance boosts r-process and superheavy creation
        res_factor = 1.0
        if el.line >= 6: # Heavy actinides and superheavies
            res_factor += wave_amp * (1.2 if (z % 2 == 0) else 0.8)
            
        base_abund = (10.0 ** (-(el.z * 0.09))) * el.stability_factor * res_factor
        
        # 2. Gate: Jeans Retention (v_esc^2 * A vs Temperature)
        # Earth escape = 1.0, Earth temp = 300 K
        esc_thermal = (v_esc_relative ** 2) * el.a / max(1.0, surface_temp_k / 300.0)
        if esc_thermal < 0.2:
            continue # Escaped to space
            
        # 3. Gate: Condensation (must freeze out onto planet or be cold volatile)
        if surface_temp_k > el.condensation_k and el.line >= 2 and z not in (1, 2, 7, 8, 10, 18, 36, 54):
            continue # Too hot to condense
            
        # 4. Gate: Differentiation (densest elements sink towards core)
        mantle_density = 4.5
        crust_share = max(0.01, 1.0 - (el.density_g_cm3 / mantle_density) * 0.35)
        
        abundance = base_abund * crust_share
        if abundance > 1e-12:
            spectrum[el.symbol] = abundance
            
    return spectrum
