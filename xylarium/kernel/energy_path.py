"""
Xylarium energy path: whether a people burns a stock its world laid down, or lives on the light and heat it is given.

Burning is a choice, weighed once a year by a people's council like every other (decide.choose), on what the energy
is worth and what it costs - as that council sees it:

  WORTH     what burning spares it: the works that would carry its shortfall on its own light and heat (harvest.py:
            the best field or core bore it could build, and the water-hydrogen it stores the surplus in) - put off
            for as long as the stock lasts, as far as it understands energy (a people that knows the stock ends
            within its horizon must build them anyway, and burning only puts them off; one that does not, counts on
            the stock forever). Where it can build nothing that would carry it (no ore, no material, no knowing
            how), burning is worth the whole output its shortfall would cost (energy.value_short). And it is worth
            more to the few than to the many: a concentrated stock can be enclosed and held, its yield taken whole;
            light falls on everyone's ground - the few who decide count it x (1 + their rent's share) (rent.py).
  COST      what its waste takes from its world: the room for life one season's burning removes, as its world's
            own physics gives it (waste.py: kept in its sky, warming it, read through its people's tuning), lost
            every season after - priced at what a life yields, over the council's horizon - as far as it
            understands its living world (alignment.foreseen: biology).

Not burning leaves the shortfall standing: its output falls, a missing EU is worth more, and its councils build the
light and heat its world gives (harvest.py: fields and core bores) the sooner. Nothing forbids either path. A people
whose horizon is short, whose few take much, whose minds swing together (decide.mood) and who do not know their world
burns; one that sees far and knows its world lives within it. What either did is written by the laws that measure
it - the waste where it fouls, the room where it is lost (alignment: order made and destroyed).

The path's intelligence, as the progenitor reads it (path_index): of the energy a people used, the share drawn from
what its world renews - the light and heat it is given - over all it drew.
"""

from typing import Any, Dict, Optional


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "energy_path")


def _short_eu(kernel: Any, planet: Any) -> float:
    """EU a season its own works leave it short: its fields and bores, and what its people's orbital arrays in its
    own system beam it (shared over its worlds there)."""
    from xylarium.kernel import energy, harvest, sustenance
    gen = sum(v for v in harvest.generation(kernel, planet).values() if v > 0)
    people = sustenance.people_of(planet)
    beamed = harvest.array_output(kernel).get((people, planet.sector_id), 0) / energy.MILLI
    if beamed:
        mine = [p for p in kernel.sectors[planet.sector_id].planets
                if p.population > 0 and sustenance.people_of(p) == people]
        gen += beamed / max(1, len(mine))
    return max(0.0, energy.need_eu(planet, kernel) - gen)


def weigh(kernel: Any, planet: Any) -> Dict[str, Any]:
    """The council weighs a year of burning against going without; sets society['burn'] and returns its reckoning."""
    from xylarium.kernel import (alignment, biosphere, decide, energy, knowledge, rent, waste)
    from xylarium.kernel.demography import _tax_per_head_quarter
    soc = planet.society
    short = _short_eu(kernel, planet)                        # EU a season its own works leave it short
    carbon = float(planet.element_reserves.get("C", 0) or 0)
    if short <= 0 or carbon <= 0 or not energy.burns(kernel, planet) or energy.tier(planet) < 1:
        soc.pop("burn", None)
        return {}
    holder = knowledge.holder_of_planet(planet)
    m = decide.mind_of_planet(kernel, planet)
    seasons = decide.horizon(m)
    knows_energy = alignment.foreseen(kernel, holder, "energy")
    knows_life = alignment.foreseen(kernel, holder, "biology")
    # worth: the works burning spares, put off while the stock lasts - as far as it knows the stock ends
    burn_units = short / energy.CARBON_EU                      # carbon a season
    lasts = carbon / max(1e-9, burn_units)                     # seasons the stock would last at this rate
    seen = seasons - knows_energy * max(0.0, seasons - lasts)
    alt = alternative(kernel, planet, short)
    if alt is None:                                            # nothing it could build would carry it
        flow = energy.value_short(planet) * short
        value = decide.worth(kernel, flow, dict(m, horizon_q=seen * m["noise"]), planet.currency)
    else:                                                      # the works put off for `seen` seasons
        r = decide.rate(kernel, planet.currency)
        value = alt * (1.0 - (1.0 + r) ** (-max(0.0, seen))) if r > 1e-12 else alt * (1.0 if seen > 0 else 0.0)
    value *= 1.0 + rent.of(planet)
    # cost: the room a season's burning takes, every season after, as far as it knows its living world
    cost = 0.0
    try:
        from xylarium.kernel import worlds
        w = worlds.state_of_planet(kernel, planet)["world"]
        g = max(1e-6, float(w.get("g", 1.0))) * worlds.UNIT_G
        kg = burn_units * energy.CARBON_EU * waste.eu_joules() / waste.FUELS["C"]["heat_j_per_kg"]
        added = kg * waste.FUELS["C"]["per_kg"] * waste.kept_share(w, "CO2") * g / waste._area(w) / worlds.BAR
        rec = soc.get("waste") or {"air": {}, "heat_w_m2": 0.0}
        now = waste.warming(w, rec.get("air", {}), rec.get("heat_w_m2", 0.0))
        air = dict(rec.get("air", {}))
        air["CO2"] = air.get("CO2", 0.0) + added
        after = waste.warming(w, air, rec.get("heat_w_m2", 0.0))
        lost = biosphere.carrying_capacity(kernel, planet) * max(0.0, waste.room(kernel, planet, now)
                                                                - waste.room(kernel, planet, after))
        cost = decide.worth(kernel, lost * _tax_per_head_quarter(planet), m, planet.currency) * knows_life
    except Exception:
        cost = 0.0
    got = decide.choose(kernel, [decide.option("burn", cost, value)], m, planet.id, "burn")
    soc["burn"] = 1 if got is not None else 0
    st = stats(kernel)
    st["weighed"] = st.get("weighed", 0) + 1
    st["burned" if got is not None else "abstained"] = st.get("burned" if got is not None else "abstained", 0) + 1
    out = {"value": round(value, 2), "cost": round(cost, 2), "lasts_years": round(lasts / 4.0, 1),
           "horizon_years": round(seasons / 4.0, 1), "knows_energy": round(knows_energy, 3),
           "knows_life": round(knows_life, 3), "rent": rent.of(planet), "burn": soc["burn"]}
    soc["energy_path"] = out
    return out


def alternative(kernel: Any, planet: Any, short_eu: float) -> Optional[float]:
    """What the works to carry `short_eu` a season on the light and heat it is given would cost (local money): the
    cheapest per EU of all this people could build (harvest.py's own designs and costs: fields, core bores, and - with
    yards - collectors at its star); None if nothing."""
    from xylarium.config import HABITAT_COST, PRICE_LEVEL
    from xylarium.kernel import geology, harvest, knowledge, sustenance
    holder = knowledge.holder_of_planet(planet)
    level = PRICE_LEVEL.get(planet.currency, 1.0)
    sec = kernel.sectors.get(planet.sector_id)
    best = None
    for kind in harvest.KINDS:                                 # all it could build: fields, bores, orbital arrays
        if kind == "tap" and not geology.rocky(planet):
            continue
        if kind == "array" and (not sustenance.yards(planet) or sec is None or getattr(sec, "kind", "SYSTEM") != "SYSTEM"):
            continue
        d = harvest.design(kernel, holder, kind, planet) or harvest.crude(kernel, kind, planet)
        gain = (harvest.field_output(kernel, planet, d["eff"]) if kind == "field" else
                harvest.tap_output(planet, d["eff"]) if kind == "tap" else harvest.module_output(kernel, sec, d["eff"]))
        if gain <= 0:
            continue
        per_eu = HABITAT_COST * level * harvest.COST[kind] * d["cost_mult"] / gain
        best = per_eu if best is None else min(best, per_eu)
    return None if best is None else best * short_eu


def path_index(planet: Any) -> float:
    """Of the energy its people drew, the share its world renews (light, heat) - over a life of seasons."""
    rec = planet.society.get("energy_mix") or {}
    total = sum(rec.values())
    return (total - rec.get("combustion", 0.0)) / total if total > 0 else 1.0


def record_mix(planet: Any, gen: Dict[str, int]) -> None:
    rec = planet.society.setdefault("energy_mix", {})
    for kind, meu in gen.items():
        rec[kind] = round(rec.get(kind, 0.0) + meu, 1)


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    worlds = [p for s in kernel.sectors.values() for p in s.planets if p.population > 0 and p.society.get("energy_mix")]
    idx = [path_index(p) for p in worlds]
    return {"weighed": st.get("weighed", 0), "burned": st.get("burned", 0), "abstained": st.get("abstained", 0),
            "worlds": len(worlds), "mean_path_index": round(sum(idx) / len(idx), 4) if idx else None}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="energy_path",
    state=lambda: {},
    summary=summary,
))
