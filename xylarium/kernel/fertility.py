"""
Xylarium fertility: how many children a people wants is biology meeting circumstance.

Fertility f is desired family size relative to replacement (f = 1 replaces the generation). A world grows
logistically toward min(1, f) x K - a people below replacement settles under what its land could carry - and a
people above replacement fills its land faster (speed max(1, f)), never faster than its farms can feed the
newcomers (biosphere.births).

Reproductive strategy is set by clade (config REPRODUCTIVE_STRATEGY), else by metabolism:
  * r-strategists (mycotiforms, hexasocial swarms, hypobiotids): calories become clutches. f rises from 1 toward
    FERTILITY_R_MAX with stored food and household comfort.
  * K-strategists (bimaniform Terrans, ailuroforms): the demographic transition. Security brings replacement or a
    little above (FERTILITY_K_SECURE); luxury access and a crowded world compress it below replacement.
  * Lithic peoples bud from structural metal (Fe/Ti on hand) and tectonic heat (an active, massive world);
    wealth means nothing to them.
  * Cryocoherent (Stillcold) fission wants cold and quiet: warmer light and ambient wealth (thermal entropy)
    depress it.
  * Plasmic peoples shear off in coronal flares: their fertility follows their star's luminosity and the
    hydrogen well they live in, not their purse.

Meaning (mu) is a people's collective momentum against the satiation of comfort, read from its state: the open
land in its reach, how fast its knowledge grows over a generation, births a crisis deferred, and comfort with
nothing ahead of it (meaning()). It weighs on births as much as a strategy's births are a choice
(config MEANING_WEIGHT).

Every strategy collapses under famine, bombardment or plague: f falls to FERTILITY_STRESS of itself for a season.
Each strategy's biological ceiling can be lifted by its nursery (nursery.py) while the nursery is fed.
Dogma (the Pyre's tensor) multiplies it; natal policy cards (config NATAL_POLICIES) shape it:
  * Edict of Propagation: f x 1.4, households taxed less (family subsidies), food eaten x 1.25.
  * Ascetic Mandate: f capped at replacement; +20% productivity, +10% luxury demand, content crowds.
  * Sacred Hatching (the Pyre's worlds): surplus food becomes fanatic recruits for the garrison, at the cost
    of the civilization's research.
Councils of AI and indigenous worlds choose their card each quarter; players choose theirs by command.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import (
    FERTILITY_CRYO_MAX,
    FERTILITY_K_LUXURY_COMPRESSION,
    FERTILITY_K_SECURE,
    FERTILITY_K_URBAN_COMPRESSION,
    FERTILITY_R_MAX,
    FERTILITY_STRESS,
    FERTILITY_STRESS_SEASONS,
    HATCHING_FOOD_PER_RECRUIT,
    LIGHT_OPTIMUM,
    LITHIC_METAL_PER_THOUSAND,
    MEANING_CEIL,
    MEANING_FLOOR,
    MEANING_WEIGHT,
    NURSERIES,
    METABOLISM_STRATEGY,
    NATAL_POLICIES,
    REPRODUCTIVE_STRATEGY,
)
from xylarium.kernel import matter

STRATEGIES = ("r", "K", "lithic", "cryo", "plasmic")


# ---------------------------------------------------------------------- who breeds how
def strategy(kernel: Any, planet: Any) -> str:
    """The reproductive strategy of the people living on this world."""
    civ = getattr(planet, "civilization", None)
    traits = getattr(civ, "traits", None) if civ is not None else None
    if traits and traits.get("strategy"):
        return traits["strategy"]                       # what its own world selected (cosmos.arise)
    clade = (getattr(civ, "clade", None) or "").lower() if civ is not None else ""
    if clade in REPRODUCTIVE_STRATEGY:
        return REPRODUCTIVE_STRATEGY[clade]
    owner = kernel.captains.get(planet.owner_id) if (kernel is not None and planet.owner_id) else None
    species = (getattr(owner, "species", "") or "").lower() if owner is not None else ""
    for token in species.replace("_", "-").split("-"):
        if token in REPRODUCTIVE_STRATEGY:
            return REPRODUCTIVE_STRATEGY[token]
    from xylarium.kernel import biosphere
    return METABOLISM_STRATEGY.get(biosphere.metabolism_of(kernel, planet), "K")


def _season_cycles() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stressed(kernel: Any, planet: Any) -> bool:
    """Famine, bombardment or plague within the last FERTILITY_STRESS_SEASONS seasons."""
    window = FERTILITY_STRESS_SEASONS * _season_cycles()
    return kernel.cycle_count - _last_crisis(planet) <= window


def _last_crisis(planet: Any) -> int:
    soc = planet.society
    return max(soc.get("famine_cycle", -10 ** 9), soc.get("bombarded_cycle", -10 ** 9),
               soc.get("blight_cycle", -10 ** 9))


def mark(planet: Any, what: str, cycle: int) -> None:
    """A blow that stops a people having children: 'famine', 'bombarded' or 'blight'."""
    planet.society[f"{what}_cycle"] = cycle


def discovered(kernel: Any, planet: Any = None, captain: Any = None) -> None:
    """A breakthrough, a new element, a decoded relic: news that lifts a people's meaning. A captain's discovery
    reaches every world it governs."""
    worlds = [planet] if planet is not None else []
    if captain is not None:
        worlds += kernel.get_planets_owned_by(captain.id)
    for p in worlds:
        p.society["discovery_cycle"] = kernel.cycle_count


# ---------------------------------------------------------------------- meaning
CEILING = {"r": FERTILITY_R_MAX, "K": FERTILITY_K_SECURE[1], "lithic": 1.6, "cryo": FERTILITY_CRYO_MAX,
           "plasmic": 1.5}                 # each strategy's own fertility ceiling (natural(): its terms at their best)


def generation_years(strat: Optional[str] = None, speed: float = 1.0) -> float:
    """A generation: the years a people takes to replace itself at its strategy's full natural increase, run at
    its substrate's kinetic pace (laws.cognition speed: a hot people lives fast, a cold one slow). With no people
    named, the galaxy's ruler: 1 / BIRTH_RATE."""
    from xylarium.config import BIRTH_RATE
    base = 1.0 / eval_fraction(BIRTH_RATE)
    if strat is None:
        return base
    return base / max(1e-6, CEILING.get(strat, 1.0)) / max(1e-6, speed)


def generation_of(kernel: Any, planet: Any) -> float:
    from xylarium.kernel import biosphere
    m = biosphere.cognition_of(kernel, planet)
    return generation_years(strategy(kernel, planet), m["speed"])


def birth_share_quarter() -> float:
    from xylarium.config import BIRTH_RATE
    return eval_fraction(BIRTH_RATE) * _season_cycles() / 100.0


def room(kernel: Any, planet: Any) -> float:
    """The open land in this people's reach that it could eat on, as a share of all the land in reach: free worlds'
    carrying capacity for its metabolism (under a dome where its yards can build one) against its own world's."""
    from xylarium.config import DAUGHTER_FOUNDING_TIER
    from xylarium.kernel import biosphere, cache, demography, sustenance, topology

    def reckon() -> float:
        metab = biosphere.metabolism_of(kernel, planet)
        domes = 1 if sustenance.yards(planet) else 0
        open_k = 0
        for sid in topology.reach(kernel, planet.sector_id, sustenance.reach(kernel, planet)):
            for c in kernel.sectors[sid].planets:
                if demography.free_world(c):
                    open_k += biosphere.carrying_capacity(kernel, c, citadel=DAUGHTER_FOUNDING_TIER, habitats=domes,
                                                          metabolism=metab)
        home = max(1, demography.housing_cap(planet, kernel))
        return open_k / (open_k + home)
    return cache.memo(kernel, "room", planet.id, reckon, max_age=4 * _season_cycles())


def progress(kernel: Any, planet: Any) -> float:
    """The people's knowledge growth, felt over a generation: tanh(generation x annual growth rate). Rising, a
    people expects more of its children's world; falling, less."""
    from xylarium.kernel import knowledge
    g = knowledge.stats(kernel).get("growth", {}).get(knowledge.holder_of_planet(planet), 0.0)
    return math.tanh(generation_years() * g)


def meaning(kernel: Any, planet: Any) -> Tuple[float, Dict[str, float]]:
    """mu = (1 + prospects + catch-up) x (1 - satiation / 2), in [MEANING_FLOOR, MEANING_CEIL].

    prospects  the mean of room (open land in reach), progress (knowledge growth over a generation) and purpose
               (whether the goal the people chose for itself is being reached - introspect.py)
    catch-up   births a crisis deferred, made up at up to twice the natural rate until recovered
    satiation  comfort without prospects: luxury access x (1 - prospects); a wholly sated people with nothing
               ahead of it sits at half (the floor)
    """
    soc = planet.society
    from xylarium.kernel import introspect, knowledge
    r, p = room(kernel, planet), progress(kernel, planet)
    aim = introspect.purpose(kernel, knowledge.holder_of_planet(planet))   # living toward what it chose
    prospects = (r + p + aim) / 3.0
    share = birth_share_quarter()
    catch_up = 0.0 if stressed(kernel, planet) else min(1.0, float(soc.get("deferred", 0.0)) / share)
    satiation = laws_clamp(float(soc.get("lux_access", 0.0) or 0.0)) * (1.0 - max(0.0, min(1.0, prospects)))
    mu = (1.0 + prospects + catch_up) * (1.0 - satiation / 2.0)
    mu = min(MEANING_CEIL, max(MEANING_FLOOR, mu))
    return mu, {"room": round(r, 3), "progress": round(p, 3), "purpose": round(aim, 3), "catch_up": round(catch_up, 3),
                "satiation": round(satiation, 3)}


def laws_clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


# ---------------------------------------------------------------------- the biology of each strategy
def natural(kernel: Any, planet: Any, strat: Optional[str] = None) -> Tuple[float, Dict[str, float]]:
    """Fertility before policy, dogma and stress, with the circumstances it was read from."""
    from xylarium.kernel import biosphere, physics, demography
    strat = strat or strategy(kernel, planet)
    soc = planet.society
    comfort = float(soc.get("basket_fill", 1.0))           # share of the household basket bought last season
    lux = float(soc.get("lux_access", 0.0))                # share of luxury wants met last season
    k = max(1, demography.housing_cap(planet, kernel))
    urban = min(1.0, planet.population / k)
    parts: Dict[str, float] = {"comfort": round(comfort, 3), "luxury": round(lux, 3), "urban": round(urban, 3)}
    n = soc.get("nursery")
    lifted = bool(n) and bool(n.get("online")) and n.get("kind") == strat
    m = 0.0
    if lifted and kernel is not None:
        from xylarium.kernel import nursery
        m = nursery.mastery(kernel, planet, strat)          # it lifts as far as the people knows how
        parts["nursery"] = round(m, 3)
    if strat == "r":
        stores = 4 * _season_cycles() * biosphere.consumption(planet)
        from xylarium.kernel import staples
        food = min(1.0, staples.stores(kernel, planet) / max(1, stores))      # its own staple, stored
        f = 1.0 + (FERTILITY_R_MAX - 1.0) * food * (0.5 + 0.5 * comfort)
        parts["food"] = round(food, 3)
    elif strat == "K":
        lo, hi = FERTILITY_K_SECURE
        relief = 1.0 - m                                              # artificial wombs
        f = (lo + (hi - lo) * comfort) * (1.0 - relief * (FERTILITY_K_LUXURY_COMPRESSION * lux
                                                          + FERTILITY_K_URBAN_COMPRESSION * urban))
    elif strat == "lithic":
        res = planet.element_reserves
        metal = res.get("Fe", 0) + res.get("Ti", 0) + planet.ore_silo // 10
        need = max(1.0, planet.population / 1000.0 * LITHIC_METAL_PER_THOUSAND)
        metal_fit = max(m, min(1.0, metal / need))                     # the foundry nursery feeds them metal
        tectonic = max(m, min(1.0, float(physics.body(planet).get("mass", 1))))   # ...and its heat
        f = 0.4 + 0.8 * metal_fit + 0.4 * tectonic
        parts.update(metal=round(metal_fit, 3), tectonic=round(tectonic, 3))
    elif strat == "cryo":
        sec = kernel.sectors.get(planet.sector_id)
        fl = float(physics.planet_flux(sec, planet)) if sec is not None else 1.0
        opt = float(eval_fraction(LIGHT_OPTIMUM.get("cryogenic", "1/8")))
        cold = max(m, min(1.0, 2.0 / (1.0 + fl / opt)))                 # the deep-cold vault
        warmth = (0.5 * comfort + 0.5 * lux) * (1.0 - m / 2)             # ambient wealth is heat to a Stillcold mind
        f = FERTILITY_CRYO_MAX * cold * (1.0 - 0.5 * warmth)
        parts["cold"] = round(cold, 3)
    else:   # plasmic
        sec = kernel.sectors.get(planet.sector_id)
        lum = float(physics.star(sec)["luminosity"]) if sec is not None else 1.0
        flare = min(2.0, lum)
        well = 1.0 if physics.body(planet).get("giant") or planet.planet_type == "GAS_GIANT" else 0.5
        flare, well = max(flare, m), max(well, 0.5 + 0.5 * m)   # the confinement ring: a star and well of its own
        f = 0.5 + 0.5 * flare * well
        parts.update(flare=round(flare, 3), well=well)
    return max(0.0, f), parts


def eval_fraction(s: str) -> float:
    a, _, b = str(s).partition("/")
    return float(a) / float(b or 1)


def fertility(kernel: Any, planet: Any) -> Tuple[float, Dict[str, Any]]:
    """This season's fertility: biology x meaning x dogma x natal policy x stress."""
    strat = strategy(kernel, planet)
    f, parts = natural(kernel, planet, strat)
    mu, why = meaning(kernel, planet)
    f *= 1.0 + MEANING_WEIGHT.get(strat, 1.0) * (mu - 1.0)
    parts.update(meaning=round(mu, 3), meaning_parts=why)
    civ = getattr(planet, "civilization", None)
    dogma = float(getattr(civ, "dogma", 0.0) or 0.0) if civ is not None else 0.0
    if dogma > 0:
        f *= 1.0 + dogma
    natal = planet.society.get("natal")
    card = NATAL_POLICIES.get(natal or "", {})
    if "fertility" in card:
        f *= card["fertility"]
    if "fertility_cap" in card:
        f = min(f, card["fertility_cap"])
    life = planet.society.get("life") or {}
    if "thr" in life:                                   # TFR x total health resilience (lifespan.py)
        f *= float(life["thr"])
    from xylarium.kernel import lifespan
    f *= lifespan.prime_factor(planet)                  # only the prime bear: a youth bulge waits, an old people slows
    unstressed = f
    hit = stressed(kernel, planet)
    if hit:
        f *= FERTILITY_STRESS
    parts.update(strategy=strat, dogma=round(dogma, 3), natal=natal, stressed=hit,
                 unstressed=round(unstressed, 4))
    return f, parts


# ---------------------------------------------------------------------- natal policy
def choose_natal(kernel: Any, planet: Any, f_natural: float) -> Optional[str]:
    """A council's natal card. Players keep the card they played."""
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    if owner is not None and not getattr(owner, "is_ai", False):
        return planet.society.get("natal")
    civ = getattr(planet, "civilization", None)
    if planet.faction_id == "ZEALOT" or (civ is not None and getattr(civ, "faction_id", None) == "ZEALOT"):
        return "hatching"
    from xylarium.kernel import demography
    # its council's fork, if it has weighed one (syntropy.py); a captain's house by temperament
    policy = getattr(planet, "growth_policy", None) or (demography.choose_policy(kernel, planet) if owner else None)
    if policy == "steady":
        return "ascetic"
    dogma = float(getattr(civ, "dogma", 0.0) or 0.0) if civ is not None else 0.0
    if dogma > 0.5:
        return "propagation"          # its creed commands it
    if f_natural < 1.0 and perceives(kernel, planet):
        return "propagation"          # an expansionist people that sees itself falling below replacement pays for its children
    return None


def perceives(kernel: Any, planet: Any) -> bool:
    """Whether a people can see its own fertility fall: it must know itself (introspect.py) or have climbed some way
    up the ladders of abstraction (intellect.py). A people that cannot see it simply dwindles."""
    from xylarium.kernel import intellect, introspect, knowledge
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    if owner is not None:
        return True                   # a captain's colony keeps its census
    holder = knowledge.holder_of_planet(planet)
    return introspect.introspective(kernel, holder) or intellect.fluid(kernel, holder) > 0


def set_natal(kernel: Any, captain: Any, planet: Any, card: str) -> str:
    if planet.owner_id != captain.id:
        raise ValueError(f"You do not govern {planet.name}.")
    card = (card or "").lower()
    if card in ("none", "", "lift"):
        planet.society.pop("natal", None)
        return f"{planet.name}: natal policy lifted."
    if card not in NATAL_POLICIES:
        raise ValueError("Natal policy is PROPAGATION, ASCETIC or NONE.")
    if NATAL_POLICIES[card].get("zealot_only") and planet.faction_id != "ZEALOT":
        raise ValueError("Only the Pyre's worlds practise the Sacred Hatching.")
    planet.society["natal"] = card
    return f"{planet.name}: {NATAL_POLICIES[card]['name']} proclaimed."


def food_factor(planet: Any) -> float:
    return NATAL_POLICIES.get(planet.society.get("natal") or "", {}).get("food", 1.0)


def tax_factor(planet: Any) -> float:
    card = NATAL_POLICIES.get(planet.society.get("natal") or "", {})
    return card.get("tax", 1.0) * card.get("productivity", 1.0)


def luxury_factor(planet: Any) -> float:
    return NATAL_POLICIES.get(planet.society.get("natal") or "", {}).get("luxury_demand", 1.0)


# ---------------------------------------------------------------------- the quarter
def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "fertility")


def quarter(kernel: Any) -> List[str]:
    """Each season: every people reads its circumstances, its council plays a natal card, the Pyre hatches."""
    logs: List[str] = []
    st = stats(kernel)
    by: Dict[str, Dict[str, float]] = {}
    for sec in kernel.sectors.values():
        for planet in sec.planets:
            if planet.population <= 0 or getattr(planet, "natives", None):
                continue
            soc = planet.society
            from xylarium.kernel import nursery
            log = nursery.upkeep(kernel, planet)
            if log:
                logs.append(log)
            if strategy(kernel, planet) == "r":
                log = nursery.blight(kernel, planet)
                if log:
                    logs.append(log)
            if planet.population <= 0:
                continue
            f_nat, _ = natural(kernel, planet)
            card = choose_natal(kernel, planet, f_nat)
            if card != soc.get("natal"):
                if card is None:
                    soc.pop("natal", None)
                else:
                    soc["natal"] = card
                    st["natal_changes"] += 1
                    if card != "hatching":
                        logs.append(f"[NATAL] {planet.name} proclaims the {NATAL_POLICIES[card]['name']}.")
            f, parts = fertility(kernel, planet)
            soc["fertility"] = round(f, 4)
            soc["fertility_parts"] = parts
            share = birth_share_quarter()
            if parts["stressed"]:                           # births the crisis defers, to be made up after it
                soc["deferred"] = round(float(soc.get("deferred", 0.0)) + share * (1.0 - FERTILITY_STRESS), 6)
            elif soc.get("deferred"):
                made_up = share * parts["meaning_parts"]["catch_up"]
                soc["deferred"] = round(max(0.0, float(soc["deferred"]) - made_up), 6)
            nursery.track_viability(planet)
            log = nursery.consider(kernel, planet)
            if log:
                logs.append(log)
            if parts["stressed"]:
                st["stressed_quarters"] += 1
                ratio = f / parts["unstressed"] if parts["unstressed"] > 0 else 0.0
                st["stress_ratio_max"] = max(st["stress_ratio_max"], round(ratio, 4))
            if soc.get("natal") == "ascetic":
                planet.morale = min(100, planet.morale + 2)           # no crowding unrest
            if soc.get("natal") == "hatching":
                _hatch(kernel, planet, st)
            b = by.setdefault(parts["strategy"], {"worlds": 0, "people": 0, "f_sum": 0.0, "mu_sum": 0.0})
            b["worlds"] += 1
            b["people"] += planet.population
            b["f_sum"] += f * planet.population
            b["mu_sum"] += parts["meaning"] * planet.population
    st["by_strategy"] = {k: {"worlds": v["worlds"], "people": v["people"],
                             "fertility": round(v["f_sum"] / max(1, v["people"]), 3),
                             "meaning": round(v["mu_sum"] / max(1, v["people"]), 3)} for k, v in by.items()}
    return logs


def _hatch(kernel: Any, planet: Any, st: Dict[str, Any]) -> None:
    """Sacred Hatching: food beyond two seasons' stores is spent raising fanatics for the garrison."""
    from xylarium.kernel import biosphere
    keep = 2 * _season_cycles() * biosphere.consumption(planet)
    from xylarium.kernel import staples
    staple = staples.of(kernel, planet)
    surplus = staples.held(planet, staple) - keep
    recruits = min(max(0, surplus) // HATCHING_FOOD_PER_RECRUIT, planet.population // 100)
    if recruits <= 0:
        return
    staples.take(planet, staple, recruits * HATCHING_FOOD_PER_RECRUIT, "sacred_hatching")
    planet.garrison_troops += recruits
    civ = getattr(planet, "civilization", None)
    if civ is not None:
        civ.research_points = max(0, civ.research_points - recruits * NATAL_POLICIES["hatching"]["research_cost"])
    st["recruits"] += recruits


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    natal: Dict[str, int] = {}
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population > 0 and p.society.get("natal"):
                natal[p.society["natal"]] = natal.get(p.society["natal"], 0) + 1
    return {**st, "natal_cards": natal}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="fertility",
    state=lambda: {"stressed_quarters": 0, "stress_ratio_max": 0.0, "recruits": 0, "natal_changes": 0,
                   "by_strategy": {}},
    season=quarter,
    summary=summary,
))
