"""
Xylarium ways of life: foragers, farmers, states - and what carries a people from one to the next.

A people lives one of three ways, and each is physics plus a choice:

  FORAGE   it eats what its world grows wild, taken a link up the food chain: a forager lives off the animals and
           the few edible plants of a wild ecosystem, and a link of a food chain passes on about a tenth of the
           energy it takes in (Lindeman's ten-percent law). Foragers number a tenth of what the same land feeds
           when farmed. They keep no stores worth taxing, so there is no state and no money among them. They
           learn by doing: a season of gathering teaches biology as thought does (Wright's curve), so the
           larger and denser a forager people, the sooner it knows enough to sow.
  FARM     it directs the land's growth into its own staple. A crop becomes a crop by selection, one crop generation
           (a standard year) at a time - Lande's equation: the change per generation is the additive variance
           times the selection gradient (genome.VARIANCE). Foragers already select without meaning to (every
           harvest of a wild stand favours the plants that keep their seed), as hard as they harvest (their
           pressure on the land) and as well as they know the plants (their biology mastery m); farmers select
           on purpose (m alone). The crop's edible share rises as e^z from the wild tenth, up to all of it.
           Farming feeds more people per acre but costs more work per meal while a people does not know how (the
           Neolithic paradox: the extra toil is the population times what it has not yet learned, 1 - m). A
           people takes up farming when the room its half-wild crops would make, as pressed as it is against its
           wild land, outweighs that toil - its own council of elders judging (decide.choose, its own mind).
           Domesticated crops are capital: they stay bred when the knowledge that bred them fades.
  STATE    stored harvests can be taxed - but only what farmers grow beyond what they eat (their surplus share,
           1 - wild/farmed yield). A farming people founds a state when its surplus can bear a state's share
           (config HOUSEHOLD_INCOME_SHARE: what households keep) and the room the state's first works would buy
           (a citadel - biosphere.py's agricultural technology) is worth, over its horizon, more than what it takes.
           From then on it is what the primordial genesis starts with: a council, a treasury, taxes, money, works.

Peoples whose record has no way (settled and primordial universes) are states, as before.
"""

import math
from typing import Any, Dict, List

from xylarium.kernel import laws

TROPHIC_EFFICIENCY = 0.1        # Lindeman (1942): a link of a food chain passes on ~10% of the energy it takes in
WAYS = ("forage", "farm", "state")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "ways")


def way(planet: Any) -> str:
    soc = getattr(planet, "society", None) or {}
    return soc.get("way", "state")


def stateless(planet: Any) -> bool:
    return way(planet) != "state"


def taxable(planet: Any) -> float:
    return 0.0 if stateless(planet) else 1.0


def domestication(kernel: Any, planet: Any) -> float:
    """0..1: how much of the gap between wild and farmed land this people knows how to close."""
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge
    return laws.mastery(knowledge.experience(kernel, knowledge.holder_of_planet(planet), "biology"), KNOWLEDGE_UNIT)


def k_factor(kernel: Any, planet: Any, how: str = None) -> float:
    """The share of farmed carrying capacity this way of life feeds: the wild tenth for foragers, the crop's
    edible share for farmers and states (TE x e^z, up to all of it)."""
    how = how or way(planet)
    if how == "forage":
        return TROPHIC_EFFICIENCY
    if "way" not in (planet.society or {}):
        return 1.0                                            # a people of an older genesis: farmed land, as before
    return min(1.0, TROPHIC_EFFICIENCY * math.exp(crop_z(planet)))


def crop_z(planet: Any) -> float:
    return float((getattr(planet, "society", None) or {}).get("crop_z", 0.0))


def surplus(kernel: Any, planet: Any) -> float:
    """The share of a farmer's harvest beyond what the same land fed it wild."""
    return max(0.0, 1.0 - TROPHIC_EFFICIENCY / max(1e-9, k_factor(kernel, planet)))


def _breed(kernel: Any, planet: Any, pressure: float = 1.0) -> None:
    """A season of selection on the crops (Lande): VARIANCE x gradient per crop generation (a standard year)."""
    from xylarium.kernel import genome
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    soc = planet.society
    gradient = domestication(kernel, planet) * pressure
    z = crop_z(planet) + genome.VARIANCE * gradient * FISCAL_QUARTER_CYCLES / 100.0
    soc["crop_z"] = round(min(math.log(1.0 / TROPHIC_EFFICIENCY), z), 6)


def _refresh(kernel: Any, planet: Any) -> None:
    planet.society["way_k"] = round(k_factor(kernel, planet), 6)


def _peoples(kernel: Any) -> List[Any]:
    return [p for s in kernel.sectors.values() for p in s.planets
            if p.population > 0 and not getattr(p, "natives", None) and "way" in p.society]


# ---------------------------------------------------------------------- genesis
def forage(kernel: Any) -> None:
    """Every people of a primordial universe goes back to foraging: numbers what its wild land feeds, no state,
    no treasury, no works."""
    from xylarium.kernel import biosphere
    for sec in kernel.sectors.values():
        for p in sec.planets:
            n = getattr(p, "natives", None)
            if n:                                      # the natives too live by gathering, as many as it fed
                n["population"] = max(100, int(n["population"] / 1.6 ** int(n["stage"])))   # (each age x1.6)
                n["stage"], n["progress"], n["crop_z"] = 0, 0.0, 0.0       # and their crops as wild as anyone's
                continue
            if p.population <= 0:
                continue
            p.society["way"] = "forage"
            _refresh(kernel, p)
            p.population = max(100, int(biosphere.carrying_capacity(kernel, p)))
            p.treasury = 0
            p.household_purse = 0
            p.fighters = 0
            p.shields = 0


def _practise(kernel: Any, planet: Any) -> None:
    """Before writing and schools a people's knowledge is its practice: a season of gathering or tending teaches
    biology as thought does (Wright's curve is learning by doing) - every head at its minds' depth, a thousand
    people-years to a unit, as knowledge.effort counts its thinkers. It fades as all knowledge does."""
    from xylarium.kernel import biosphere, knowledge
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    depth = biosphere.cognition_of(kernel, planet)["depth"]
    units = planet.population / 1000.0 * depth * FISCAL_QUARTER_CYCLES / 100.0
    knowledge.learn(kernel, knowledge.holder_of_planet(planet), "biology", units, "practice")


# ---------------------------------------------------------------------- the season
def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import biosphere, decide, primordial
    st = stats(kernel)
    logs: List[str] = []
    counts: Dict[str, int] = {w: 0 for w in WAYS}
    for p in _peoples(kernel):
        _refresh(kernel, p)
        how = way(p)
        counts[how] += 1
        _practise(kernel, p)
        k_now = max(1, biosphere.carrying_capacity(kernel, p))
        pressure = min(1.0, p.population / k_now)
        _breed(kernel, p, pressure if how == "forage" else 1.0)
        if how == "state":
            continue
        from xylarium.kernel import annals, knowledge as _knowledge
        if annals.history_decides(kernel, _knowledge.holder_of_planet(p)):
            continue                                   # an unguided people turns when its history comes to it (annals)
        m = decide.mind_of_planet(kernel, p)
        name = getattr(getattr(p, "civilization", None), "name", p.name)
        if how == "forage":
            # the room its half-wild crops would make, as pressed as it is, against the toil of farming unknowingly
            gain = pressure * k_now * (math.exp(crop_z(p)) - 1.0)
            toil = p.population * (1.0 - domestication(kernel, p))
            if decide.choose(kernel, [decide.option("take_up_farming", toil, gain, aim="deepen")], m, p.id, "farm") is not None:
                p.society["way"] = "farm"
                _refresh(kernel, p)
                st["farmed"] += 1
                primordial.first(kernel, "first_farms", name)
                from xylarium.kernel import history, knowledge
                w = words(p)
                history.event(kernel, "FARMING", f"The {name} {w['tend']}",
                              actors=[knowledge.holder_of_planet(p)], planet=p, magnitude=p.population,
                              cause=f"half-tamed {w['crop']} (x{math.exp(crop_z(p)):.2f}) against the toil")
                logs.append(f"[WAYS] The {name} of {p.name} {w['tend']}.")
        else:
            # the room a state's first works would make, as a flow over its horizon, against what it would tax
            from xylarium.config import HOUSEHOLD_INCOME_SHARE
            if surplus(kernel, p) < 1.0 - HOUSEHOLD_INCOME_SHARE:
                continue                               # its harvests cannot yet bear a state's share
            room = biosphere.carrying_capacity(kernel, p, citadel=p.citadel_level + 1) - k_now
            value = decide.worth(kernel, max(0, room) * pressure / 4.0, m)
            cost = decide.worth(kernel, p.population * (1.0 - HOUSEHOLD_INCOME_SHARE) * (1.0 - pressure) / 4.0, m)
            if decide.choose(kernel, [decide.option("found_state", cost, value, aim="deepen")], m, p.id, "state") is not None:
                p.society["way"] = "state"                 # it taxes in kind; a coin waits on a need (institutions.need)
                st["states"] += 1
                primordial.first(kernel, "first_state", name)
                from xylarium.kernel import history, knowledge
                history.event(kernel, "STATEHOOD", f"The {name} order their surplus", actors=[knowledge.holder_of_planet(p)],
                              planet=p, magnitude=p.population, cause=f"a surplus of {surplus(kernel, p):.0%}",
                              text=f"The {name} raise {words(p)['order']}.")
                logs.append(f"[WAYS] The {name} of {p.name} order their surplus: {words(p)['order']}.")
    st["counts"] = counts
    return logs


def words(planet: Any) -> Dict[str, str]:
    """What a people's ways are called, in its own chemistry's terms (its medium and senses: cosmos.select) - a
    sea of light is sown, a dark sea's warmth is tended, a cold sea's blooms are herded, a giant's plasma is shaped."""
    traits = getattr(getattr(planet, "civilization", None), "traits", None) or {}
    solvent, sense = traits.get("solvent", "H2O"), traits.get("sense", "light")
    if solvent == "plasma":
        return {"tend": "shape their first standing field-swarms", "crop": "field-swarms", "gather": "the drift",
                "order": "a lattice of keepers, a store of charge, a share for the whole", "rule": "the keepers"}
    if solvent in ("melt",) or sense == "heat":
        return {"tend": "cultivate their first mineral beds", "crop": "mineral growths", "gather": "the hot places",
                "order": "a council of the hot places, a hoard, a tithe", "rule": "the hot-place council"}
    if sense == "heat and pressure":
        return {"tend": "tend their first vent-gardens", "crop": "vent-mats", "gather": "the warm springs",
                "order": "a council of the warm springs, a cache, a share", "rule": "the warm-spring council"}
    if solvent in ("CH4", "N2", "NH3") or sense == "chemistry":
        return {"tend": "herd their first cold blooms", "crop": "brine-blooms", "gather": "the shoals",
                "order": "a council of the shoals, a store, a levy", "rule": "the shoal council"}
    return {"tend": "sow their first fields", "crop": "crops", "gather": "the wild", "rule": "the granary",
            "order": "a council, a granary, a tax"}


def era(planet: Any) -> str:
    """A people's age in its own terms - what it lives by, named from its chemistry and senses (words), as its
    species is named from what its world made of it; there is no galaxy-wide calendar of human eras."""
    from xylarium.kernel import sustenance
    w = words(planet)
    if sustenance.yards(planet):
        return "the age of first voyages"
    how = (getattr(planet, "society", None) or {}).get("way", "forage")
    if how == "state":
        return f"the age of {w['rule']}"
    if how == "farm":
        return f"the age of {w['crop']}"
    return f"the age of {w['gather']}"


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    ps = _peoples(kernel)
    return {"counts": dict(st.get("counts", {})), "farmed": st["farmed"], "states": st["states"],
            "mean_domestication": round(sum(domestication(kernel, p) for p in ps) / len(ps), 3) if ps else 0.0,
            "mean_crop_share": round(sum(k_factor(kernel, p) for p in ps) / len(ps), 3) if ps else 0.0}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="ways",
    state=lambda: {"farmed": 0, "states": 0, "counts": {}},
    season=quarter,
    summary=summary,
))
