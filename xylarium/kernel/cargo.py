"""
Xylarium cargo: what a unit of a good weighs - one hold slot of it.

A good is carried and priced by the unit (a hold slot), and lived by the kilogram (the survival basket is a mass a
person-year). A unit's mass is a hold slot's volume filled with the good at its measured density (substances: each
good's matter - water ice for H2O, ammonia for cryogenite, the mantle's MgSiO3 for ORE, an element at its own
density). The hold slot is a SHIP'S SPEC, a design and not a law (coordinator, 2026-10-09): the internal volume of a
standard 20-foot container (ISO 668), the box the long-haul trades already move.
"""

from fractions import Fraction
from typing import Optional

HOLD_SLOT_M3 = Fraction("33.2")         # a hold slot: one 20-foot container's inside (ISO 668) - a design, not a law
MATTER_OF = {"H2O": "H2O", "cryogenite": "NH3", "ORE": "MgSiO3", "ORGANICS": "C6H12O6"}


def density_kg_m3(good: str) -> Optional[Fraction]:
    """A good's measured density (kg/m^3): its compound's, or its element's; None where its matter is not known."""
    from xylarium.kernel import substances
    sym = MATTER_OF.get(good, good)
    rec = substances.compound(sym) or substances.element(sym)
    rho = (rec or {}).get("rho", (rec or {}).get("density"))
    return Fraction(str(rho)) * 1000 if rho else None


def unit_kg(good: str) -> Optional[Fraction]:
    """What one unit (a hold slot) of a good weighs, exactly; None where its density is not known."""
    rho = density_kg_m3(good)
    return HOLD_SLOT_M3 * rho if rho else None
