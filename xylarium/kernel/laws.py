"""
Xylarium laws: the universal physics laid over every world's local physics.

Planetary physics is local - a world's light, temperature, gravity, chemistry and food are its own (physics.py,
biosphere.py). The laws here are the same everywhere and are written once: every system that needs one calls it
rather than carrying its own version. Each is a known law with its source; the only constants are physical ones
or measured empirical rates.

    stefan_boltzmann_temperature   T = T_earth x flux^(1/4)                     radiative equilibrium
    landauer_bits                  bits per unit energy  ~ 1 / T                Landauer's limit (k T ln 2 a bit)
    cognition                      depth ~ 1/sqrt(T), speed and noise ~ sqrt(T) a mind's thermodynamics
    thermal_speed                  reaction / signal speed ~ sqrt(T)            kinetic theory
    thermal_noise                  fluctuation amplitude ~ sqrt(T)              equipartition
    wright                         unit cost x (cumulative)^-b, b = -log2(PR)   Wright's learning curve (PR 0.8)
    depreciate                     knowledge loses DELTA a year                 R&D capital depreciation (~15%/yr)
    final_size                     z = 1 - exp(-R0 z)                           Kermack-McKendrick epidemic
    lanchester_odds                P(win) = A / (A + D), losses ~ the other     Lanchester's linear law
    present_value                  sum of a flow discounted at r over a horizon compound discounting
"""

import math
from typing import Optional

T_EARTH = 278.0                 # K: Earth's radiative equilibrium temperature (flux 1)
T_PLASMA = 1.0e4                # K: hydrogen half-ionised (Saha) - the substrate plasmic minds think in
WRIGHT_PROGRESS_RATIO = 0.8     # unit cost falls to 80% with each doubling of cumulative experience (Wright 1936)
KNOWLEDGE_DEPRECIATION = 0.15   # a year: the measured depreciation of R&D capital (Griliches; Hall 2007)


# ---------------------------------------------------------------------- thermodynamics of a mind
def stefan_boltzmann_temperature(flux: float) -> float:
    return T_EARTH * max(1e-9, flux) ** 0.25


def substrate_temperature(metabolism: str) -> float:
    """The temperature a people's thinking runs at: its world's equilibrium temperature at the light it evolved
    under; plasmic minds run in ionised hydrogen."""
    if metabolism == "plasmic":
        return T_PLASMA
    from xylarium.config import LIGHT_OPTIMUM
    a, _, b = str(LIGHT_OPTIMUM.get(metabolism, "1/1")).partition("/")
    return stefan_boltzmann_temperature(float(a) / float(b or 1))


def landauer_bits(t: float, t_ref: float = T_EARTH) -> float:
    """Bits a unit of energy can erase at temperature t, relative to t_ref (k T ln 2 a bit)."""
    return t_ref / t


def thermal_speed(t: float, t_ref: float = T_EARTH) -> float:
    return math.sqrt(t / t_ref)


def thermal_noise(t: float, t_ref: float = T_EARTH) -> float:
    return math.sqrt(t / t_ref)


def cognition(metabolism: str) -> dict:
    """A people's mind from its substrate temperature. A thought erases bits at Landauer's cost (bits per joule
    ~ 1/T) while the energy it cycles a second follows its kinetics (~ sqrt T), so the knowledge a second of thought
    yields - its depth - goes as 1/sqrt(T); how fast it reacts is kinetic (sqrt T); how noisy its judgements are is
    thermal (sqrt T). Cold minds are deep and slow; hot minds quick, noisy and shallow."""
    t = substrate_temperature(metabolism or "biotic")
    return {"temperature": round(t, 1), "depth": landauer_bits(t) * thermal_speed(t), "speed": thermal_speed(t),
            "noise": thermal_noise(t)}


# ---------------------------------------------------------------------- learning and forgetting
def wright_exponent(progress_ratio: float = WRIGHT_PROGRESS_RATIO) -> float:
    return -math.log2(progress_ratio)


def wright(experience: float, unit: float, progress_ratio: float = WRIGHT_PROGRESS_RATIO) -> float:
    """Cost multiplier after `experience` (in units of `unit`): 1 with none, PR with each doubling after."""
    return (1.0 + max(0.0, experience) / unit) ** (-wright_exponent(progress_ratio))


def mastery(experience: float, unit: float) -> float:
    """How far experience has carried a capability, 0 .. 1: the share of its original cost learned away."""
    return 1.0 - wright(experience, unit)


def depreciate(stock: float, years: float, rate: float = KNOWLEDGE_DEPRECIATION) -> float:
    return stock * (1.0 - rate) ** years


# ---------------------------------------------------------------------- populations
def final_size(r0: float) -> float:
    """The share an epidemic infects: the root of z = 1 - exp(-R0 z) in (0, 1); none below R0 = 1."""
    if r0 <= 1.0:
        return 0.0
    z = 1.0 - 1.0 / r0
    for _ in range(50):
        z = 1.0 - math.exp(-r0 * z)
    return z


def lanchester_odds(attack: float, defend: float) -> float:
    total = max(0.0, attack) + max(0.0, defend)
    return attack / total if total > 0 else 0.0


# ---------------------------------------------------------------------- value over time
def present_value(flow: float, periods: float, rate: float) -> float:
    """A constant flow per period for `periods`, discounted at `rate` a period."""
    if periods <= 0:
        return 0.0
    if rate <= 1e-12:
        return flow * periods
    return flow * (1.0 - (1.0 + rate) ** (-periods)) / rate


def horizon(noise: float, base: float) -> float:
    """How far ahead a mind plans: a noisier mind's forecasts blur sooner (the horizon shrinks as 1/noise)."""
    return base / max(1e-6, noise)


def clamp(x: float, lo: float = 0.0, hi: Optional[float] = 1.0) -> float:
    x = max(lo, x)
    return x if hi is None else min(hi, x)
