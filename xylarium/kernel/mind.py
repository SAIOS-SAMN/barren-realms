"""
Xylarium mind: what kind of mind a people is - not how much of one.

A mind is not a quantity on one line. The world that raised it chose its senses, its body, its medium and its way
of living together (cosmos.select), and those choose what kind of mind it is. Its profile, each axis 0 .. 1, read
from those traits and from its chemistry's own copying (life.py):

  COLLECTIVE   how far it thinks as one: a superorganism's members share what each learns (social, shape)
  DISTRIBUTED  how far its thinking lives through its body rather than in one seat: a swimmer's many limbs, a
               colony, a mind spread slow through its medium - each part deciding for itself (form, shape)
  PLASTIC      how far it rewrites itself within a life - the octopus edits its own RNA as its sea warms and cools:
               a second channel of information beside the genome. Strong where the medium swings within a life
               and the body is soft and self-made: aquatic, variable worlds, fast-breeding lineages
  LEGIBLE      how readable its own heredity is: a chemistry that copies faithfully (few rungs of error correction)
               keeps an inheritance stable enough to be read; a sloppy one churns (life.fidelity)
  SENSES       which sciences its life touches first: a sky of light opens energy and the heavens (information);
               chemistry and touch open biology and materials; heat and pressure open energy and materials; fields
               open energy and information

What the profile does: a people learns from the day it wakes, in the sciences its life touches (knowledge.lived);
a collective forgets less, its knowledge held by the whole and not by knowers who die (knowledge.forgetting); a
plastic, legible mind comes to its own heredity early - genetics without waiting for machines (technology); and
the order in which a people finds its capabilities follows its kind of mind (technology: affinity), so an aquatic
collective under ice comes to biology and chemistry long before fire and the sky.
"""

import math
from typing import Any, Dict, Optional

from xylarium.kernel.knowledge import DOMAINS

SENSE_DOMAINS = {               # the sciences a life's senses touch first (weights, each row summing to 2)
    "light": {"energy": 0.5, "information": 1.0, "materials": 0.25, "biology": 0.25},
    "chemistry": {"biology": 1.0, "materials": 0.75, "energy": 0.125, "information": 0.125},
    "heat and pressure": {"energy": 0.75, "materials": 0.75, "biology": 0.375, "information": 0.125},
    "heat": {"energy": 1.0, "materials": 0.75, "biology": 0.125, "information": 0.125},
    "fields": {"energy": 1.0, "information": 0.75, "materials": 0.125, "biology": 0.125},
}
AQUATIC_FORMS = ("swimming", "drifting")


def _traits(planet: Any) -> Dict[str, Any]:
    civ = getattr(planet, "civilization", None)
    return dict(getattr(civ, "traits", None) or {}) if civ is not None else {}


def _eps0(kernel: Any, planet: Any) -> Optional[float]:
    from xylarium.kernel import life, worlds
    t = _traits(planet)
    solvent = t.get("solvent")
    body_t = t.get("body_t")
    if not solvent or not body_t:
        return None
    try:
        return life.fidelity(solvent, float(body_t))
    except Exception:
        return None


def profile(kernel: Any, planet: Any) -> Dict[str, Any]:
    """The kind of mind this world's people is."""
    t = _traits(planet)
    social = float(t.get("social", 0.5) or 0.5)
    shape = t.get("shape", "society")
    form = t.get("form", "walking")
    medium = str(t.get("medium", ""))
    aquatic = form in AQUATIC_FORMS or "under ice" in medium or "dark" in medium
    collective = min(1.0, social * (1.5 if shape == "superorganism" else 0.75 if shape == "distributed" else 0.5))
    distributed = min(1.0, (0.6 if shape in ("distributed", "superorganism") else 0.0) +
                      (0.4 if form in AQUATIC_FORMS or form == "low and many-limbed" else 0.0))
    r_line = t.get("strategy") == "r"
    plastic = min(1.0, (0.5 if aquatic else 0.1) + (0.3 if r_line else 0.0) + 0.2 * distributed)
    eps0 = _eps0(kernel, planet)
    from xylarium.kernel import life
    legible = 0.5 if eps0 is None else max(0.0, min(1.0, math.log(life.BITS_PER_MONOMER / eps0) /
                                                     math.log(life.I_MIND)))
    weights = dict(SENSE_DOMAINS.get(t.get("sense", "light"), SENSE_DOMAINS["light"]))
    if aquatic:                                           # no fire under water: the sky and the forge come late
        weights["energy"] *= 0.5
        weights["biology"] += 0.25
    total = sum(weights.values()) or 1.0
    affinity = {d: round(len(DOMAINS) * weights.get(d, 0.0) / total, 4) for d in DOMAINS}
    return {"collective": round(collective, 4), "distributed": round(distributed, 4), "plastic": round(plastic, 4),
            "legible": round(legible, 4), "aquatic": aquatic, "affinity": affinity}


def of_holder(kernel: Any, holder: Optional[str]) -> Optional[Dict[str, Any]]:
    """A people's profile, read at its most populous world."""
    if not holder:
        return None
    from xylarium.kernel import knowledge
    best = None
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population > 0 and knowledge.holder_of_planet(p) == holder and \
                    (best is None or p.population > best.population):
                best = p
    return profile(kernel, best) if best is not None else None
