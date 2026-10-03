"""
Xylarium designer: make a new people, and set it down on a world.

A design is a body and a genome:

  metabolism   what it lives on and where (biotic, mineral, cryogenic, plasmic, umbral - cohabit.niche: which
               worlds, and which part of them, it can live in)
  body plan    a clade (config REPRODUCTIVE_STRATEGY): an r-strategist breeds in clutches and is held back by
               disease; a K-strategist raises few and goes through the demographic transition
  genome       the six heritable axes of genome.py, as log-offsets from its metabolism's founding form: the light
               it is tuned to, how wide that tuning is (wider loses peak - the trade-off is physics, not a rule),
               how far it is adapted to a world's surface, its natural increase, its minds' temperature (deep and
               slow, or quick and noisy), and how well it keeps what it learns

Nothing about a design is balanced. Three laws bound it:

  * what you get is what you know: the genome a designer can build is its mastery of genome editing (knowledge.py)
    times the change it asks for - the same law a council's edits obey (genome.proposal). Ask for a great deal
    knowing little, and you get a little.
  * what you do not understand is mystery: each axis is understood through a science (the light a body is tuned to
    and its minds' temperature through energy, its tolerance and its increase through biology, its fit to a ground
    through materials, its memory through information) and through mathematics (the share of the square's eight
    symmetries the people's crystals can express, and of the higher dimensions' operations - intellect.py).
    Understanding = mastery of the science x mathematics. Below full understanding an edit lands only roughly where
    it was aimed (an error of (1 - u) of the change), and every edit spills into the axes not understood
    (pleiotropy: the edit's size shared equally over the six axes, by what is not understood of each). Previews
    show what is known as values, what is half-known as ranges, and the rest as mystery; the seeding reveals
    it - with this universe's own stream of chance (scheduler.rng), so the same design in the same universe comes out the same.
  * every deviation costs: the price is the edit distance (in additive deviations) at a habitat's price, along the
    designer's learning curve (genome editing's cost multiplier), plus the vats for the founders.

Seeding sets 500 founders down (Franklin's 50/500 rule: the long-term minimum viable population) on a world with no
one on it whose physics gives its metabolism a niche and room. A new species has a body but no culture: it begins
as foragers (ways.py) with nothing learned, and the world selects it from then on (genome.evolve, Lande): a design
that fits thrives; one that does not drifts toward what the world rewards, or dies out. The designer chooses the
body; the people chooses its path.
"""

import math
from typing import Any, Dict, List, Optional

FOUNDERS = 500                  # Franklin (1980) 50/500: the long-term minimum viable population

CLADE_OF = {"biotic": "BIOTIC", "mineral": "LITHIC", "plasmic": "PLASMIC", "umbral": "UMBRAL", "cryogenic": "CRYOGENIC"}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "designer")


def body_plans() -> Dict[str, str]:
    from xylarium.config import REPRODUCTIVE_STRATEGY
    return dict(REPRODUCTIVE_STRATEGY)


def metabolisms() -> List[str]:
    return sorted(CLADE_OF)


def mastery(kernel: Any, holder: Optional[str]) -> float:
    from xylarium.kernel import knowledge
    return knowledge.mastery(kernel, holder, "genome_editing") if holder else 0.0


SCIENCE_OF = {"light": "energy", "temperature": "energy", "tolerance": "biology", "birth": "biology",
              "chemistry": "materials", "aptitude": "information"}


def mathematics(kernel: Any, holder: Optional[str]) -> float:
    """0..1: the share of the square's symmetries its crystals express, and of the higher dimensions' operations."""
    from xylarium.kernel import crystal as C, intellect
    if not holder:
        return 0.0
    vocab = intellect.vocabulary(kernel, holder)
    plane = len(intellect._chart(vocab)) / 8.0
    higher = sum(1 for op in C.STACK_OPS + C.HYPER_OPS if op in vocab) / float(len(C.STACK_OPS + C.HYPER_OPS))
    return min(1.0, 0.5 * plane + 0.5 * higher)


def understanding(kernel: Any, holder: Optional[str]) -> Dict[str, float]:
    """Per axis, 0..1: mastery of its science x mathematics."""
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge, laws
    math_ = mathematics(kernel, holder)
    return {a: round(laws.mastery(knowledge.experience(kernel, holder, d), KNOWLEDGE_UNIT) * math_, 4) if holder
            else 0.0 for a, d in SCIENCE_OF.items()}


def expect(kernel: Any, holder: Optional[str], asked: Dict[str, float], full: bool = False) -> Dict[str, Dict[str, Any]]:
    """What a designer can foresee of each axis: the aim (mastery x the change), the spread around it (its own
    imprecision and the spill of the whole edit into what it does not understand), and how well it knows it."""
    from xylarium.kernel import genome
    m = 1.0 if full else mastery(kernel, holder)
    u = {a: 1.0 for a in genome.AXES} if full else understanding(kernel, holder)
    size = math.sqrt(sum(float(asked.get(a, 0.0)) ** 2 for a in genome.AXES))
    spill = size / math.sqrt(len(genome.AXES))
    out = {}
    for a in genome.AXES:
        aim = m * float(asked.get(a, 0.0))
        sd = (1.0 - u[a]) * (abs(aim) + spill)
        out[a] = {"aim": round(aim, 4), "sd": round(sd, 4), "known": u[a],
                  "seen": "known" if sd <= 0.1 * max(abs(aim), 0.1) else ("range" if sd < max(abs(aim), 0.1) * 1.5
                                                                           else "mystery")}
    return out


def build(kernel: Any, holder: Optional[str], asked: Dict[str, float], full: bool = False,
          rng: Any = None) -> Dict[str, float]:
    """The genome a designer gets: the aim, and - without `rng` - nothing more (the expectation); with this
    universe's stream of chance, what it actually gets (aim + the spread of what it does not understand). The Progenitor's
    hand at genesis (`full`) gets exactly what it asks."""
    exp = expect(kernel, holder, asked, full)
    return {a: round(e["aim"] + (rng.gauss(0.0, e["sd"]) if rng is not None and e["sd"] > 0 else 0.0), 6)
            for a, e in exp.items()}


def cost(kernel: Any, holder: Optional[str], got: Dict[str, float], currency: str = "SOL") -> float:
    from xylarium.config import HABITAT_COST, PRICE_LEVEL
    from xylarium.kernel import genome, knowledge
    step = genome.distance(got, {a: 0.0 for a in genome.AXES})
    level = PRICE_LEVEL.get(currency, 1.0)
    return HABITAT_COST * level * (step * knowledge.cost_multiplier(kernel, holder, "genome_editing") + 1.0)


def preview(kernel: Any, holder: Optional[str], design: Dict[str, Any], planet: Any) -> Dict[str, Any]:
    """What a design would be on a world: its niche, how many foragers the world would feed, its fitness - and
    why it could not be seeded there, if it could not."""
    from xylarium.kernel import biosphere, cohabit, genome, ways
    metab = design.get("metabolism", "biotic")
    got = build(kernel, holder, design.get("genome", {}), design.get("full", False))
    niche = cohabit.niche(planet, metab)
    out = {"genome": got, "foresight": expect(kernel, holder, design.get("genome", {}), design.get("full", False)),
           "mathematics": round(mathematics(kernel, holder), 3), "niche": niche, "cost": round(cost(kernel, holder, got, getattr(planet, "currency", "SOL"))),
           "mastery": round(mastery(kernel, holder) if not design.get("full") else 1.0, 3)}
    saved_genome, saved_civ = planet.society.get("genome"), getattr(planet, "civilization", None)
    planet.society["genome"] = got
    planet.civilization = None
    try:
        k = biosphere.carrying_capacity(kernel, planet, citadel=0, metabolism=metab)
        out["log_fitness"] = round(genome.log_fitness(kernel, planet, got), 3) if metab != "plasmic" else None
    finally:
        if saved_genome is None:
            planet.society.pop("genome", None)
        else:
            planet.society["genome"] = saved_genome
        planet.civilization = saved_civ
    out["foragers_fed"] = int(k * ways.TROPHIC_EFFICIENCY)
    out["why_not"] = why_not(kernel, planet, metab, out["foragers_fed"])
    return out


def why_not(kernel: Any, planet: Any, metab: str, fed: int) -> Optional[str]:
    from xylarium.kernel import cohabit
    if planet.population > 0 or getattr(planet, "natives", None) or getattr(planet, "civilization", None):
        return "someone already lives there"
    if cohabit.niche(planet, metab) is None:
        return f"a {metab} body has no niche on a {planet.planet_type.lower().replace('_', ' ')} world"
    if fed < FOUNDERS:
        return f"its wild land would feed {fed:,} - fewer than the {FOUNDERS} founders a people needs"
    return None


def seed(kernel: Any, holder: Optional[str], design: Dict[str, Any], planet: Any, by: str) -> Dict[str, Any]:
    """Set a designed people down on `planet`. Returns the preview with `seeded` (and the cost to be paid by the
    caller), or with `why_not`."""
    from xylarium.kernel import primordial, ways
    from xylarium.kernel.civilization import CivilizationIntelligenceEngine
    pv = preview(kernel, holder, design, planet)
    if pv["why_not"]:
        return pv
    metab = design.get("metabolism", "biotic")
    plan = design.get("body_plan") or "bimaniform"
    from xylarium.kernel import scheduler                    # the seeding reveals what was mystery
    pv["genome"] = build(kernel, holder, design.get("genome", {}), design.get("full", False),
                         rng=scheduler.rng(kernel, "design", holder, planet.id, kernel.cycle_count))
    name = design.get("name") or f"{plan.title()} of {planet.name}"
    civ = CivilizationIntelligenceEngine.create_civilization({
        "name": name, "species_name": f"{plan}-{name.split()[0].lower()}", "clade": plan, "class_code": 0,
        "sigil": design.get("sigil", "*"), "metabolism": metab, "disposition": design.get("disposition", "industry"),
        "motto": design.get("motto", "we were made, and then we chose"), "station": "seeded", "tech_level": 0})
    planet.civilization = civ
    from xylarium.kernel import biosphere
    biosphere.adapt(kernel, civ, planet)                  # bred for its world's light (its genome tunes from there)
    planet.owner_id = None
    planet.faction_id = None
    planet.citadel_level = 0
    planet.habitats = 0
    planet.treasury = 0
    planet.population = FOUNDERS
    planet.society["genome"] = dict(pv["genome"])
    planet.society["way"] = "forage"
    planet.society["seeded_by"] = by
    planet.society["seeded_cycle"] = kernel.cycle_count
    ways._refresh(kernel, planet)
    # they land at harvest: a season of what the wild land gives them (gathered from the world, not brought)
    from xylarium.config import FOOD_PER_THOUSAND
    from xylarium.kernel import staples
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    staples.add(planet, staples.of(kernel, planet), FOUNDERS * FOOD_PER_THOUSAND * FISCAL_QUARTER_CYCLES // 1000,
                "harvest")
    st = stats(kernel)
    st["seeded"].append({"cycle": kernel.cycle_count, "world": planet.id, "people": name, "by": by,
                         "metabolism": metab, "body_plan": plan})
    del st["seeded"][:-50]
    primordial.first(kernel, "first_seeded_people", f"{name} on {planet.name}, by {by}")
    chron = getattr(kernel, "chronicle", None)
    if chron is not None:
        chron.record(kernel, "SEEDING", planet.id, name, f"The Seeding of {planet.name}",
                     f"{by} set five hundred of a new kind down on {planet.name}: {metab}, a {plan} body, tuned "
                     f"to a light and a ground of its makers' choosing. What they become is theirs.",
                     sector_id=planet.sector_id, tags=["genome", "seeding", "creation"])
    pv["seeded"] = name
    return pv


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    alive = 0
    for rec in st["seeded"]:
        for s in kernel.sectors.values():
            for p in s.planets:
                if p.id == rec["world"] and p.population > 0 and getattr(getattr(p, "civilization", None), "name",
                                                                          None) == rec["people"]:
                    alive += 1
    return {"seeded": len(st["seeded"]), "alive": alive, "recent": st["seeded"][-3:]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="designer", state=lambda: {"seeded": []}, summary=summary))


def describe(foresight: Dict[str, Dict[str, Any]]) -> List[str]:
    """How a designer sees each axis: a value it knows, a range it half-knows, or a mystery."""
    out = []
    for a, e in foresight.items():
        if e["seen"] == "known":
            out.append(f"{a} {e['aim']:+.2f}")
        elif e["seen"] == "range":
            out.append(f"{a} {e['aim'] - e['sd']:+.2f}..{e['aim'] + e['sd']:+.2f}")
        else:
            out.append(f"{a} ???")
    return out
