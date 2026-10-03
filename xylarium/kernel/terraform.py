"""
Xylarium terraforming: changing a world to fit a people, instead of a people to fit its world.

genome.py adapts a people to its world: its surface fit closes the gap to a perfect fit as e^-chemistry. Terraforming
is the same law turned around - the world is processed toward the ground some biology evolved on (the planet type it
fits best, universe.habitability), and every biology's fit there moves toward its fit on that ground:

    fit(t) = h* + (fit - h*) e^-t        h*: the biology's fit on the target ground; t: e-folds of processing

so the people it is made for gain what they lacked, and anyone else living there (a co-resident community, natives)
loses what their own biology needed - counted as harm in alignment, life for life (alignment.measure), exactly as a
stalled dynamo's starved are.

  RATE   an atmosphere mixes in about a year (the interhemispheric exchange time); no amount of money processes a
         world faster than one e-fold a year, and a people does it at its mastery of the process (knowledge.py,
         `terraforming`, materials) times that.
  PRICE  per e-fold per Earth-area, what the same land would cost enclosed (HABITAT_COST per HABITAT_AREA of
         habitat), along the people's learning curve (the process's cost multiplier).
  WHO    a council chooses it by the one rule (demography's works: the room it buys against its price), a captain
         by command (TERRAFORM) - its own world, or an empty one it means to seed (designer.py).
"""

import math
from typing import Any, Dict, List, Optional

ROCKY = ("TERRESTRIAL", "OCEANIC", "VOLCANIC", "ICE", "DESERT", "BARREN")
MIXING_YEARS = 1.0             # an atmosphere mixes in about a year: at most one e-fold of change a year


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "terraform")


def record(planet: Any) -> Optional[Dict[str, Any]]:
    return (getattr(planet, "society", None) or {}).get("terraform")


def ideal_ground(metab: str) -> str:
    """The planet type this biology fits best."""
    from xylarium.kernel.universe import habitability
    types = ROCKY                                     # a giant has no ground to process, and none can be made
    return max(types, key=lambda t: (float(habitability(metab, t)), t))


def reshape(fit: float, metab: str, planet: Any) -> float:
    """A biology's surface fit on this world after its terraforming so far."""
    rec = record(planet)
    if not rec or rec.get("t", 0.0) <= 0:
        return fit
    from xylarium.kernel.universe import habitability
    h = float(habitability(metab, rec["ground"]))
    return h + (fit - h) * math.exp(-float(rec["t"]))


def can(planet: Any) -> bool:
    from xylarium.kernel import physics
    return planet.planet_type in ROCKY and not physics.body(planet).get("giant")


def rate(kernel: Any, holder: Optional[str]) -> float:
    """E-folds a quarter this people can process a world."""
    from xylarium.kernel import knowledge
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    from xylarium.kernel import technology
    m = knowledge.mastery(kernel, holder, "terraforming") if holder else 0.0
    if technology.has(kernel, holder, "synthesis"):
        m *= 1.0 + technology.SYNTHESIS_GAIN           # living chemistry designed for the world, not evolved on it
    return m * (FISCAL_QUARTER_CYCLES / 100.0) / MIXING_YEARS


def price(kernel: Any, holder: Optional[str], planet: Any, dt: float) -> float:
    from xylarium.config import HABITAT_AREA, HABITAT_COST, PRICE_LEVEL
    from fractions import Fraction
    from xylarium.kernel import knowledge, physics
    per_area = HABITAT_COST / float(Fraction(HABITAT_AREA))
    area = float(physics.surface_area(planet))
    return per_area * area * dt * PRICE_LEVEL.get(getattr(planet, "currency", "SOL"), 1.0) * \
        knowledge.cost_multiplier(kernel, holder, "terraforming")


def _capacities(kernel: Any, planet: Any) -> Dict[str, int]:
    """Who lives here, and how many of each the world feeds: its people, its communities, its natives."""
    from xylarium.kernel import biosphere, cohabit
    out: Dict[str, int] = {}
    if planet.population > 0:
        out["people"] = biosphere.carrying_capacity(kernel, planet)
    for i, c in enumerate(cohabit.communities(planet)):
        out[f"community:{i}"] = cohabit.capacity(kernel, planet, c["metab"])
    return out


def step(kernel: Any, planet: Any, ground: str, dt: float, actor: Any = None) -> Dict[str, Any]:
    """Process the world dt e-folds toward `ground`. Measures who gained and who lost room (and judges the harm).
    Changing the target ground restarts the work."""
    from xylarium.kernel import alignment, imprint, primordial, sustenance
    soc = planet.society
    rec = soc.get("terraform")
    t0 = float(rec["t"]) if rec and rec.get("ground") == ground else 0.0
    before = _capacities(kernel, planet)
    natives = getattr(planet, "natives", None)
    native_fit = reshape(1.0, natives.get("metabolism", "biotic"), planet) if natives else None
    by = getattr(actor, "name", None) or str(planet.owner_id or "")
    rec = imprint.record(kernel, planet, "terraform", by,
                         terraform={"ground": ground, "t": round(t0 + max(0.0, dt), 6)})["terraform"]
    after = _capacities(kernel, planet)
    lost = sum(max(0, before[k] - after.get(k, 0)) for k in before if k != "people")
    gained = max(0, after.get("people", 0) - before.get("people", 0))
    if natives and native_fit:
        frac = 1.0 - reshape(1.0, natives.get("metabolism", "biotic"), planet) / max(1e-9, native_fit)
        if frac > 0:
            gone = int(natives.get("population", 0) * frac)
            natives["population"] = max(0, natives.get("population", 0) - gone)
            lost += gone
    st = stats(kernel)
    st["e_folds"] = round(st["e_folds"] + dt, 4)
    st["displaced"] += lost
    if lost > 0:
        if actor is not None:
            alignment.act(kernel, actor, "core_harvest", lives_lost=lost)
        elif planet.population > 0:
            sustenance._shift_civ(planet, alignment.measure(kernel, lives_lost=lost))
    primordial.first(kernel, "first_terraforming", f"{planet.name} toward {ground.lower()}")
    return {"t": rec["t"], "gained": gained, "displaced": lost}


# ---------------------------------------------------------------------- the council's option
def option(kernel: Any, planet: Any, m: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """Terraforming as one of a council's works: this season's step toward its own biology's ground, worth the
    room it buys (demography.value_of_room), priced per e-fold."""
    from xylarium.kernel import biosphere, decide, demography, knowledge
    holder = knowledge.holder_of_planet(planet)
    dt = rate(kernel, holder)
    if dt <= 1e-4:
        return None
    metab = biosphere.metabolism_of(kernel, planet)
    ground = ideal_ground(metab)
    if not can(planet) or (ground == planet.planet_type and not record(planet)):
        return None                                   # it already lives on the ground its biology fits best
    soc = planet.society
    saved = soc.get("terraform")
    k_now = biosphere.carrying_capacity(kernel, planet)
    t0 = float(saved["t"]) if saved and saved.get("ground") == ground else 0.0
    soc["terraform"] = {"ground": ground, "t": t0 + dt}
    try:
        k_new = biosphere.carrying_capacity(kernel, planet)
    finally:
        if saved is None:
            soc.pop("terraform", None)
        else:
            soc["terraform"] = saved
    cost = price(kernel, holder, planet, dt)
    if k_new <= k_now or planet.treasury < cost:
        return None
    return decide.option("terraform", cost, demography.value_of_room(kernel, planet, k_new - k_now, m),
                         cash=cost, currency=planet.currency, ground=ground, dt=dt)


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    worlds = [p for s in kernel.sectors.values() for p in s.planets if record(p)]
    return {"worlds": len(worlds), "e_folds": st["e_folds"], "displaced": st["displaced"],
            "deepest": max((round(record(p)["t"], 2) for p in worlds), default=0.0)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="terraform", state=lambda: {"e_folds": 0.0, "displaced": 0}, summary=summary))
