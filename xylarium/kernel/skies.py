"""
Xylarium skies: atmospheric engineering - holding a world's air, or giving it back - as a choice a people makes.

A world's air is bound by its gravity and lost to its star's wind, to a stalled dynamo (harvest.py), to a strike
(ruin.py). Nothing in physics forbids holding it or replacing it; each is a price in energy and matter:

  SHIELD    a magnetic dipole held between the world and its star stands its wind off (Green et al. 2017's proposal
            for Mars): the field must match the wind's pressure at the standoff, B = sqrt(2 mu0 p_wind), over a
            volume a few of the world's radii across - its energy B^2 / 2 mu0 x that volume, a small price; while it
            stands, the wind takes no air (harvest.py reads it).
  IMPORT    volatiles steered in from the system's belts and comet cloud (creation's belts): each kilogram costs the
            nudge that brings it down, ~ (a tenth of the world's orbital speed)^2 / 2, and the belt's ice and carbon.
  OUTGAS    volatiles released from the world's own rock - carbonates broken to carbon dioxide (~4 MJ/kg, the
            reaction's enthalpy) - where no belt offers ice.

Neither is a requirement of anything. It is offered to a people that reaches the stars (it has yards), and its
council weighs it each year through its own mind (decide.choose): the lives its land would feed again, valued as
this universe values a life and the more for every generation it has lived there (continuity: its history, its dead,
its meaning), against the energy at what that energy is worth to it and the matter it takes. A people with little
to hold it to a failing world lets the air go, its people dwindle and its fleets carry them elsewhere (demography's
diaspora) - a nomad's way; one rooted for generations pays to keep its sky.
"""

import math
from typing import Any, Dict, List, Optional

from xylarium.kernel import interior
from xylarium.kernel.fx import hub as _hub

MU0 = 4.0e-7 * math.pi
WIND_PA_1AU = 1.5e-9            # the solar wind's dynamic pressure at 1 AU (measured; ~ a star's light / a^2)
STANDOFF_RADII = 2.0            # the shield's bubble spans a couple of the world's radii (Green et al. 2017)
OUTGAS_J_PER_KG = 4.0e6         # breaking carbonate rock to carbon dioxide (enthalpy of CaCO3 -> CaO + CO2)
NUDGE_SHARE = 0.1               # steering belt ice down takes ~ a tenth of the world's orbital speed (declared)
MIX_E_FOLD = 1.0 - math.exp(-1.0)   # an atmosphere mixes in about a year: at most one e-fold of repair a year


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "skies")


def air_full_kg(kernel: Any, planet: Any) -> float:
    """The world's air at its natural fullness."""
    from xylarium.kernel import ruin
    a = max(1e-6, float(planet.society.get("atmosphere", 1.0)))
    return ruin.binding(kernel, planet)["air_kg"] / a


def shield_j(kernel: Any, planet: Any) -> float:
    """Energy held in a shield's field: B^2 / 2 mu0 over its bubble, B to stand off the star's wind."""
    from xylarium.kernel import physics
    sec = kernel.sectors.get(planet.sector_id)
    flux = float(physics.planet_flux(sec, planet)) if sec is not None else 1.0
    b_field = math.sqrt(2.0 * MU0 * WIND_PA_1AU * flux)
    r = float(physics.body(planet).get("radius", 1)) * interior.R_EARTH_M * STANDOFF_RADII
    return b_field ** 2 / (2.0 * MU0) * 4.0 / 3.0 * math.pi * r ** 3


def _orbital_speed(kernel: Any, planet: Any) -> float:
    from fractions import Fraction
    from xylarium.kernel import physics
    sec = kernel.sectors.get(planet.sector_id)
    st = physics.star(sec) if sec is not None else {"mass": Fraction(1)}
    a = float(physics.body(planet).get("q", 1)) ** 2 * interior.AU_M
    return math.sqrt(interior.G_SI * float(st["mass"]) * interior.M_SUN_KG / max(1.0, a))


def _volatile_belt(kernel: Any, planet: Any) -> Optional[Dict[str, Any]]:
    sec = kernel.sectors.get(planet.sector_id)
    belts = [b for b in (getattr(sec, "belts", None) or [])
             if b.get("reserve", 0) > 0 and sum(b["composition"].get(e, 0) for e in ("H2O", "C", "cryogenite")) > 0]
    return max(belts, key=lambda b: b["reserve"]) if belts else None


def repair_cost(kernel: Any, planet: Any, share: float) -> Dict[str, Any]:
    """Energy (EU) and matter to give back a share of the world's natural air: steered from a belt if the system
    has volatile ice, else broken out of its own rock."""
    from xylarium.kernel import creation, ruin
    kg = air_full_kg(kernel, planet) * share
    belt = _volatile_belt(kernel, planet)
    if belt is not None:
        j = kg * 0.5 * (NUDGE_SHARE * _orbital_speed(kernel, planet)) ** 2
        frac = sum(belt["composition"].get(e, 0) for e in ("H2O", "C", "cryogenite"))
        units = max(1, int(math.ceil(kg / frac / (interior.M_EARTH_KG / creation.UNITS_PER_EARTH_MASS))))
        return {"kg": kg, "eu": j / ruin.EU_J, "how": "import", "belt": belt, "units": units}
    return {"kg": kg, "eu": kg * OUTGAS_J_PER_KG / ruin.EU_J, "how": "outgas", "belt": None, "units": 0}


def _energy_held(planet: Any) -> float:
    """EU a world can spend: its grid and its antimatter."""
    from xylarium.kernel import energy
    return planet.society.get("grid_meu", 0) / energy.MILLI + planet.element_reserves.get("AM", 0) * energy.ANTIMATTER_EU


def _spend(kernel: Any, planet: Any, eu: float, why: str) -> bool:
    from xylarium.kernel import energy, matter
    if _energy_held(planet) < eu:
        return False
    meu = int(math.ceil(eu * energy.MILLI))
    grid = int(planet.society.get("grid_meu", 0))
    take = min(grid, meu)
    if take:
        planet.society["grid_meu"] = grid - take
        energy.sink(kernel, why, take)
    rest = meu - take
    if rest > 0:
        am = int(math.ceil(rest / energy.MILLI / energy.ANTIMATTER_EU))
        planet.element_reserves["AM"] = planet.element_reserves.get("AM", 0) - am
        matter.sink(why, "AM", am)
    return True


def continuity(kernel: Any, planet: Any) -> float:
    """How much a people holds to its world: 1 + ln(1 + the generations it has lived there) - its history, its dead
    laid in it, what it has made it mean."""
    from xylarium.kernel import fertility
    years = max(0.0, (kernel.cycle_count - int(planet.society.get("founded_cycle", 0) or 0)) / 100.0)
    gen = max(1e-6, fertility.generation_of(kernel, planet))
    return 1.0 + math.log1p(years / gen)


def _options(kernel: Any, planet: Any) -> List[Dict[str, Any]]:
    from xylarium.kernel import alignment, biosphere, decide, energy
    soc = planet.society
    a = float(soc.get("atmosphere", 1.0))
    sc = alignment.scales(kernel)
    life = sc["sol"] / max(1.0, sc["lives"]) * continuity(kernel, planet)
    fx = kernel.fx_market
    # what a unit of energy is worth to it: what it would make of a spare one if its grid runs over, else what a
    # missing one costs its industry
    spare = soc.get("grid_meu", 0) / energy.MILLI > energy.need_eu(planet, kernel)
    per_eu = energy.value_surplus(planet) if spare else energy.value_short(planet)
    per_eu = fx.to_sol_value(planet.currency, per_eu) if planet.currency != _hub() else per_eu
    base = biosphere._profile(kernel, planet, None, None, None)["k"]
    m = decide.mind_of_planet(kernel, planet)
    out = []
    if a < 1.0:
        share = (1.0 - a) * MIX_E_FOLD
        c = repair_cost(kernel, planet, share)
        value = base * share * life                                       # the lives its land feeds again
        out.append(decide.option("repair_sky", c["eu"] * max(per_eu, 1e-9), value, share=share, plan=c, aim="hold"))
    if not soc.get("shield") and float(soc.get("dynamo", 1.0)) < 0.5:
        j = shield_j(kernel, planet)
        from xylarium.kernel import ruin
        loss = (0.5 - float(soc.get("dynamo", 1.0))) * 0.02 * 4.0           # the air the wind takes in a year
        value = decide.worth(kernel, base * loss * a * life / 4.0, m)
        out.append(decide.option("raise_shield", j / ruin.EU_J * max(per_eu, 1e-9), value, eu=j / ruin.EU_J, aim="hold"))
    return out


def season(kernel: Any) -> List[str]:
    """Once a year each people with yards weighs its sky."""
    from xylarium.kernel import decide, sustenance
    if (kernel.cycle_count // 25) % 4:
        return []
    logs: List[str] = []
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population <= 0 or getattr(p, "natives", None) or not sustenance.yards(p):
                continue
            for opt in _options(kernel, p):          # each weighed on its own against doing nothing
                logs += _act(kernel, p, decide.choose(kernel, [opt], decide.mind_of_planet(kernel, p), p.id,
                                                      "skies", opt["name"]))
    return logs


def _act(kernel: Any, p: Any, pick: Optional[Dict[str, Any]]) -> List[str]:
    """Carry out what a people chose for its sky (None: it chose to let it be)."""
    from xylarium.kernel import history, imprint, matter
    st = stats(kernel)
    if pick is None:
        st["declined"] += 1
        return []
    if pick["name"] == "raise_shield":
        if not _spend(kernel, p, pick["eu"], "sky_shield"):
            return []
        imprint.record(kernel, p, "shield", str(p.owner_id or ""), shield=True)
        st["shields"] += 1
        history.event(kernel, "SKY_SHIELD", f"{p.name} raises a shield against its star's wind",
                      sector_id=p.sector_id, actors=[str(p.owner_id or "")],
                      cause="its core no longer turns the wind aside, and its people chose to keep their air")
        return [f"[SKIES] {p.name} raises a magnetic shield between itself and its star."]
    c = pick["plan"]
    if not _spend(kernel, p, c["eu"], "sky_repair"):
        return []
    if c["belt"] is not None:
        take = min(c["units"], int(c["belt"]["reserve"]))
        c["belt"]["reserve"] -= take
        matter.sink("volatiles_imported", "BELT_ROCK", take)
    imprint.record(kernel, p, "air_returned", str(p.owner_id or ""), air_add=round(pick["share"], 9))
    st["repairs"] += 1
    st["air_kg"] += c["kg"]
    how = "steered in from its belt" if c["how"] == "import" else "broken from its rock"
    history.event(kernel, "SKY_REPAIR", f"{p.name} is given back part of its air", sector_id=p.sector_id,
                  actors=[str(p.owner_id or "")], cause=f"{c['kg']:.2e} kg of volatiles {how}",
                  data={"share": round(pick["share"], 4), "eu": round(c["eu"], 1)})
    return [f"[SKIES] {p.name} is given back {pick['share']:.0%} of its air ({how})."]


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {k: st[k] for k in ("shields", "repairs", "declined")} | {"air_kg": float(f"{st['air_kg']:.3g}")}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="skies", state=lambda: {"shields": 0, "repairs": 0, "declined": 0, "air_kg": 0.0},
                             season=season, summary=summary))
