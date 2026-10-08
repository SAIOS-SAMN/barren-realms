"""
Xylarium perception: what a species can sense, evolved from where it lives in mass and in space-time - never a human
eye given to every species.

A species' SENSE (cosmos.select: light, heat and pressure, chemistry, fields) says what its world gave its lineage to
read; the CHANNELS it has are what that sense could tell apart there:

  LIGHT        its star's own light, through its medium's window. The star's temperature follows from its mass on
               the main sequence (L = M^3.5 and R ~ M^0.8, so T ~ M^0.475 against the Sun's); its light peaks at
               Wien's wavelength and is emitted over about an octave either side; its medium passes only its own
               window (water passes the blue-green, ammonia and methane their own bands). The usable band is the
               two together, and its channels are the half-octaves that band spans - a red dwarf's people in water
               tell fewer colours apart than a yellow star's.
  HEAT AND     a people in the dark (under ice, in a giant's deep) reads its medium's warmth and its weight: two
  PRESSURE     channels, and no light at all.
  CHEMISTRY    a people in a cold sea of methane, nitrogen or ammonia reads what is dissolved in it: a channel for
               each volatile its medium carries.
  FIELDS       a mind in plasma reads the field itself: its electric and magnetic parts, and their twist.
  THE BELL     near the cores, where its star absorbs the bell's pulses (field.quantum_flux), a sense of the bell's
               own hum - a sense with no human counterpart.

Each channel is named in the people's own tongue (mottos.word), with a gloss of what it reads.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

T_SUN_K = 5772.0
WIEN_UM_K = 2897.77                 # Wien's displacement constant (micrometre kelvin)
HALF_OCTAVE = math.sqrt(2.0)        # a channel: the span of wavelengths one kind of receptor tells from its neighbour
# The windows a medium is transparent in (micrometres): measured absorption edges of the liquid
WINDOW_UM = {"H2O": (0.20, 0.65), "NH3": (0.30, 1.00), "CH4": (0.30, 0.89), "N2": (0.20, 2.00),
             "CO2": (0.25, 1.80), "H2SO4": (0.35, 0.90)}
VOLATILES = {"CH4": ("methane", "ethane", "nitrogen"), "N2": ("nitrogen", "methane"),
             "NH3": ("ammonia", "water", "hydrogen sulfide"), "H2O": ("salt", "oxygen", "carbon dioxide")}


def star_temperature_k(mass_suns: float) -> float:
    """A main-sequence star's surface temperature from its mass: T = T_sun (L / R^2)^(1/4), L = M^3.5, R = M^0.8."""
    return T_SUN_K * max(1e-3, mass_suns) ** ((3.5 - 1.6) / 4.0)


def light_channels(mass_suns: float, solvent: str, surface: bool = True) -> Tuple[int, Optional[Tuple[float, float]]]:
    """How many colours light lets it tell apart, and the band it sees (micrometres) - 0 where no starlight reaches."""
    if not surface:
        return 0, None
    peak = WIEN_UM_K / star_temperature_k(mass_suns)
    lo, hi = peak / 2.0, peak * 2.0
    w = WINDOW_UM.get(solvent)
    if w is not None:
        lo, hi = max(lo, w[0]), min(hi, w[1])
    if hi <= lo:
        return 0, None
    return max(1, math.ceil(math.log(hi / lo) / math.log(HALF_OCTAVE))), (round(lo, 3), round(hi, 3))


def channels(kernel: Any, planet: Any, traits: Dict[str, Any], people: str) -> List[Dict[str, Any]]:
    """The channels a species senses with, each named in its own tongue and glossed."""
    from xylarium.kernel import mottos, physics
    sense = str(traits.get("sense") or "light")
    solvent = str(traits.get("solvent") or "H2O")
    medium = str(traits.get("medium") or "")
    out: List[Dict[str, Any]] = []
    if sense == "light":
        sec = kernel.sectors.get(planet.sector_id) if kernel is not None else None
        try:
            m = float(physics.star(sec)["mass"]) if sec is not None and planet.planet_type != "ROGUE" else 0.0
        except Exception:
            m = 1.0
        n, band = light_channels(m, solvent, surface=m > 0 and "under ice" not in medium and "deep" not in medium)
        if band is not None:
            lo, hi = band
            ratio = (hi / lo) ** (1.0 / n)
            for i in range(n):
                a, b = lo * ratio ** i, lo * ratio ** (i + 1)
                out.append({"kind": "light", "band_um": [round(a, 3), round(b, 3)],
                            "gloss": f"light of {a:.2f} to {b:.2f} micrometres"})
        else:
            sense = "heat and pressure"                      # its lineage reads no starlight here
    if sense == "heat and pressure":
        out += [{"kind": "heat", "gloss": "the warmth of its medium"}, {"kind": "pressure", "gloss": "its weight"}]
    if sense == "chemistry":
        out += [{"kind": "chemistry", "gloss": f"dissolved {v}"} for v in VOLATILES.get(solvent, ("its medium",))]
    if sense == "fields":
        out += [{"kind": "field", "gloss": g} for g in ("the electric field", "the magnetic field", "the field's twist")]
    try:
        from xylarium.kernel import field
        if kernel is not None and "field" in kernel.state and field.quantum_flux(kernel, planet) > 0:
            out.append({"kind": "bell", "gloss": "the bell's hum"})
    except Exception:
        pass
    for i, ch in enumerate(out):
        ch["name"] = mottos.word(people, f"channel:{ch['kind']}:{i}")
    return out


def season(kernel: Any) -> List[str]:
    """Once a year: a species woken without its senses read is given them, from where it lives."""
    from xylarium.kernel import polity
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    for sec in kernel.sectors.values():
        for p in sec.planets:
            civ = getattr(p, "civilization", None)
            traits = getattr(civ, "traits", None) if civ is not None else None
            if not traits or traits.get("perception") is not None:
                continue
            traits["perception"] = channels(kernel, p, traits, f"civ:{civ.name}")
    return []


from xylarium.kernel import state  # noqa: E402,F401
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="perception", state=lambda: {}, season=season))
