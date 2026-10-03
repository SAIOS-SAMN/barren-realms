"""
Xylarium fundamental: the laws a universe is made under - a few dimensionless constants - and every scale that
follows from them.

The progenitors (the people who run this engine) choose a universe's laws; its seed fixes its initial conditions. The laws are
four pure numbers, each the ratio of a force or a mass to another - the only things physics can vary without
changing what its units mean. Everything the engine once wrote down as a fixed temperature, energy, mass or time
is one of our universe's values of a scale derived here, times a pure number: change a constant and every layer
of the funnel moves with it, from the stars' masses to the seas' boiling points to a body's pace of thought.

  alpha      the strength of electromagnetism (1/137.036): every chemical bond, every boiling point, every
             photon a molecule can use.
  beta       the electron's mass over the proton's (1/1836.15): how large atoms are, how dense rock is.
  alpha_G    the strength of gravity between two protons (G m_p^2 / hbar c = 5.9e-39): how massive a star must be
             to ignite, how long it burns.
  nuclear    the share of its rest mass hydrogen gives up fusing to helium (0.0071): a star's fuel.

THE GEOMETRY BEHIND THEM. Gauge theory reads a force's strength as the curvature of a structure attached to every
point of space (a fibre bundle; electromagnetism is the geometry of a small circle at each point - Kaluza and
Klein). In that reading these numbers are the shape of the dimensions too small to see, fixed when a universe
begins. The engine does not claim which shape; it takes the numbers as that shape's measurement, and everything it
computes is the projection of it at the scales a world and a people live at (docs/DIMENSIONS.md).

UNITS. G, hbar, c and k are held fixed (the engine's solar masses, AU, years and kelvin keep their meaning, and
Kepler's law with them); the proton and electron masses carry the change: m_p ~ alpha_G^(1/2), m_e = beta m_p.
Each scale is a ratio to its value in our universe (1 for our laws exactly), with a = alpha / alpha_ours,
b = beta / beta_ours, g = alpha_G / alpha_G_ours, e = nuclear / nuclear_ours:

  chemistry energy and temperature   Rydberg, alpha^2 m_e c^2 / 2                      a^2 b g^(1/2)
  atom size                          Bohr radius, hbar / (alpha m_e c)                 a^-1 b^-1 g^-1/2
  condensed matter density           m_p / a0^3                                        a^3 b^3 g^2
  pressure of condensed matter       Rydberg / a0^3                                    a^5 b^4 g^2
  star mass                          alpha_G^(-3/2) m_p (Chandrasekhar)                g^-1
  star light at a given mass share   L ~ G^4 m_p^5 m_e^2 M^3 / alpha^2 (Thomson opacity) b^2 g^(1/2) a^-2
  star life                          nuclear M c^2 / L (Press & Lightman 1983)         e a^2 b^-2 g^-3/2
  star radius                        ignition kT ~ alpha^2 m_p = G M m_p / R           g^-1 a^-2
  lightest star                      degeneracy halts contraction before ignition      g^-1 a^3/2 b^-3/4
  cloud fragment (Jeans mass)        (k T_chem / G m_p)^(3/2) at fixed density         a^3 b^3/2 g^-1/4
  alpha decay                        half-life ~ e^(Gamow factor ~ alpha)              (per isotope: interior.py)

A star's surface temperature follows (L / R^2)^(1/4) ~ a^1/2 b^1/2 g^5/8, its chemistry's ~ a^2 b g^1/2: whether
starlight can drive a world's chemistry is computed, not given (Carter's coincidence, alpha_G ~ alpha^12 beta^4).
"""

import math
from typing import Any, Dict, Optional

OURS = {"alpha": 1.0 / 137.035999, "beta": 1.0 / 1836.15267, "alpha_G": 5.906e-39, "nuclear": 0.0071}
NAMES = ("alpha", "beta", "alpha_G", "nuclear")
GAMOW_URANIUM = 87.8            # ln(half-life x attempt rate) for uranium-238's alpha decay (1.4e17 s x 1e21 /s):
                                # the barrier term scales with alpha (interior.py)

_CACHE: Dict[Any, "Laws"] = {}


class Laws:
    """A universe's laws as ratios to ours, and the scales they set."""

    def __init__(self, ratios: Optional[Dict[str, float]] = None):
        self.ftl = float((ratios or {}).get("ftl", 1.0)) >= 0.5      # whether space can be folded at all (mastery.py)
        r = {n: 1.0 for n in NAMES}
        r.update({k: float(v) for k, v in (ratios or {}).items() if k in NAMES})
        self.ratios = r
        a, b, g, e = r["alpha"], r["beta"], r["alpha_G"], r["nuclear"]
        self.values = {n: OURS[n] * r[n] for n in NAMES}
        self.chem = a ** 2 * b * g ** 0.5                     # energies and temperatures of chemistry
        self.atom = 1.0 / (a * b * g ** 0.5)                   # sizes of atoms and molecules
        self.density = a ** 3 * b ** 3 * g ** 2                # condensed matter
        self.pressure = a ** 5 * b ** 4 * g ** 2               # condensed matter's own pressures (phase diagrams)
        self.proton = g ** 0.5                                 # m_p (k / m_H scales as its inverse)
        self.star_mass = 1.0 / g
        self.star_lum = b ** 2 * g ** 0.5 / a ** 2
        self.star_life = e * a ** 2 / (b ** 2 * g ** 1.5)
        self.star_radius = 1.0 / (g * a ** 2)
        self.star_min = a ** 1.5 / (g * b ** 0.75)
        self.jeans = a ** 3 * b ** 1.5 / g ** 0.25
        self.nuclear = e
        self.alpha = a
        self.ours = all(abs(v - 1.0) < 1e-12 for v in r.values()) and self.ftl
        self.memo: Dict[Any, Any] = {}                       # derived tables, kept per law (worlds._phase_of)

    def tag(self) -> str:
        """The laws as the creation key carries them ('' for ours)."""
        out = [f"{n}={self.ratios[n]:g}" for n in NAMES if abs(self.ratios[n] - 1.0) > 1e-12]
        return ",".join(out + ([] if self.ftl else ["ftl=0"]))

    def star_teff(self) -> float:
        """A star's surface temperature at a given mass share, over ours."""
        return (self.star_lum / self.star_radius ** 2) ** 0.25

    def coincidence(self) -> float:
        """Starlight's temperature over chemistry's: 1 in our universe. Far above, starlight breaks what it should
        drive; far below, it cannot drive it."""
        return self.star_teff() / self.chem

    def half_life(self, gamow: float) -> float:
        """An alpha decay's half-life over ours: its Gamow barrier ~ alpha (log of the half-life x attempt rate)."""
        return math.exp(gamow * (self.alpha - 1.0))

    def summary(self) -> Dict[str, float]:
        return {"ratios": dict(self.ratios), "chemistry": round(self.chem, 6), "star_mass": round(self.star_mass, 6),
                "star_light": round(self.star_lum, 6), "star_life": round(self.star_life, 6),
                "star_teff": round(self.star_teff(), 6), "coincidence": round(self.coincidence(), 6),
                "rock_density": round(self.density, 6)}


OUR_LAWS = Laws()


def parse(tag: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for part in (tag or "").split(","):
        k, _, v = part.partition("=")
        if (k.strip() in NAMES or k.strip() == "ftl") and v:
            out[k.strip()] = float(v)
    return out


def of(key: Any) -> Laws:
    """The laws of a universe from its creation key ('7', '7:lush', '7:lush:alpha=1.01,alpha_G=0.9')."""
    if key in _CACHE:
        return _CACHE[key]
    parts = str(key).split(":")
    tag = parts[2] if len(parts) > 2 else ""
    laws = Laws(parse(tag)) if tag else OUR_LAWS
    _CACHE[key] = laws
    return laws


def current() -> Laws:
    """The laws of the universe being played (ours when none is)."""
    from xylarium.kernel import ledger
    k = ledger.active_kernel()
    if k is None:
        return OUR_LAWS
    from xylarium.kernel import creation
    return of(creation.universe(k))
