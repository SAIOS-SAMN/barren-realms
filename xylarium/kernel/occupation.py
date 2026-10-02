"""
Xylarium occupation: taking a world is a battle; holding it is a cost.

When a world is taken by force (an orbital assault that silences its guns, a ground invasion), its people do not
change: every sentient people keeps its own biology (its staple, its light, its genome) under any flag. Nobody is
assimilated. What changes is who rules them, and what that rule costs:

  FOREIGNNESS  how little the occupied and the occupier understand each other: their minds' channel overlap
               (contact.channel - kin share a band, a cryogenic mind barely perceives a plasmic one) times what they
               have learned of each other living together (understanding grows each season at the occupier's
               mastery of information, as contact.py's familiarity does - learning, not becoming). Resistance is what
               is not understood: f = 1 - channel x understanding.
  SYMBIOSIS    the one exception: where the two biologies feed each other (cohabit.effect: each one's waste is the
               other's staple, a mutualism), the occupied are not resisting a ruler but joining a partner - no
               resistance, no decline.
  DEMOGRAPHY   otherwise an occupation is a controlled demolition of the local demography: the occupied bear
               children in proportion to their compliance (births x (1 - f)), and those who can leave do - each
               season a resisting share of a generation's increase emigrates to the nearest world of their own kind
               in reach.
  POLICING     an occupation is held by force in proportion to the people and their resistance: the measured
               ratio of counter-insurgency is about 20 security personnel per 1000 inhabitants (Quinlivan 1995),
               each paid what a head of that world produces - from the world's own treasury, each quarter.
  COMPLIANCE   the resisting share withholds its work: the occupier taxes (1 - f) of what a willing world would give.
  REVOLT       policing the treasury cannot pay is unrest; unrest that reaches the whole of a quarter's need throws
               the occupier out - the world is its people's own again (a free people, or the people it was taken
               from). Paid policing lets unrest fade by half each quarter.

Assault and invasion themselves resolve by Lanchester's square law (expected outcome, no dice): strength against
strength, the winner keeping sqrt(A^2 - D^2).
"""

import math
from typing import Any, Dict, List, Optional

POLICE_PER_HEAD = 0.02           # Quinlivan (1995): ~20 security personnel per 1000 inhabitants to hold a population


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "occupation")


def record(planet: Any) -> Optional[Dict[str, Any]]:
    return (getattr(planet, "society", None) or {}).get("occupation")


def people_metabolism(planet: Any) -> Optional[str]:
    """The biology of the people living on a world taken by force (it does not change with the flag)."""
    rec = record(planet)
    return rec.get("metab") if rec else None


def conquer(kernel: Any, planet: Any, by: Any, how: str) -> None:
    """Record a world taken by force: its people stay who they are."""
    from xylarium.kernel import biosphere, primordial
    soc = planet.society
    old = soc.get("occupation")
    metab = old["metab"] if old else biosphere.metabolism_of(kernel, planet)
    prior = planet.owner_id
    soc["people_metab"] = metab
    soc["occupation"] = {"by": by.id, "from": old["from"] if old else prior, "since": kernel.cycle_count,
                         "metab": metab, "unrest": 0.0, "how": how}
    if old is not None and old.get("from") == by.id:
        soc.pop("occupation", None)                 # a world retaken by its own: liberation, not occupation
    st = stats(kernel)
    st["conquests"] += 1
    primordial.first(kernel, "first_occupation", f"{planet.name} by {by.name}")
    from xylarium.kernel import history
    history.event(kernel, "CONQUEST", f"{by.name} takes {planet.name}", actors=[f"captain:{by.id}", str(prior)],
                  planet=planet, magnitude=planet.population, cause=how)


def _occupier_metab(kernel: Any, planet: Any) -> str:
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    return getattr(owner, "metabolism", None) or "biotic"


def symbiotic(kernel: Any, planet: Any) -> bool:
    """Whether occupier and occupied biologies feed each other (cohabit's measured interaction, both positive)."""
    rec = record(planet)
    if not rec:
        return False
    from xylarium.kernel import cohabit
    occ, pop = _occupier_metab(kernel, planet), rec["metab"]
    if occ == pop:
        return False
    n = max(1, planet.population)
    na, nb = cohabit.niche(planet, pop), cohabit.niche(planet, occ)
    a = cohabit.effect(pop, na, n, occ, nb, n)
    b = cohabit.effect(occ, nb, n, pop, na, n)
    return a > 0 and b > 0


def foreignness(kernel: Any, planet: Any) -> float:
    rec = record(planet)
    if not rec or symbiotic(kernel, planet):
        return 0.0
    from xylarium.kernel import contact, laws
    t_occ = laws.cognition(_occupier_metab(kernel, planet))["temperature"]
    t_pop = laws.cognition(rec["metab"])["temperature"]
    return max(0.0, min(1.0, 1.0 - contact.channel(t_occ, t_pop) * float(rec.get("understood", 0.0))))


def _learn(kernel: Any, planet: Any, rec: Dict[str, Any]) -> None:
    """A season of living together: understanding grows at the occupier's mastery of information."""
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge, laws
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    occ = kernel.captains.get(rec["by"])
    info = laws.mastery(knowledge.experience(kernel, knowledge.holder_of_captain(occ), "information"),
                        KNOWLEDGE_UNIT) if occ is not None else 0.0
    u = float(rec.get("understood", 0.0))
    rec["understood"] = round(u + (1.0 - u) * info * FISCAL_QUARTER_CYCLES / 100.0, 5)


def births_factor(kernel: Any, planet: Any) -> float:
    """The occupied bear children in proportion to their compliance."""
    return compliance(kernel, planet)


def _emigrate(kernel: Any, planet: Any, rec: Dict[str, Any], f: float) -> int:
    """A resisting share of a generation's increase leaves for the nearest world of its own kind in reach."""
    from xylarium.kernel import biosphere, fertility, topology
    n = int(planet.population * f * fertility.birth_share_quarter())
    if n <= 0:
        return 0
    for sid in topology.reach(kernel, planet.sector_id, 3):
        for w in kernel.sectors[sid].planets:
            if w is planet or w.population <= 0 or record(w):
                continue
            if biosphere.metabolism_of(kernel, w) != rec["metab"]:
                continue
            if w.owner_id is not None and w.owner_id != rec.get("from"):
                continue
            n = min(n, planet.population - 1)
            planet.population -= n
            w.population += n
            return n
    return 0


def compliance(kernel: Any, planet: Any) -> float:
    """The share of a willing world's work an occupier gets (1 where nobody resists)."""
    return 1.0 - foreignness(kernel, planet) if record(planet) else 1.0


def policing_need(kernel: Any, planet: Any) -> float:
    """Money a quarter to hold this world: its people x resistance x Quinlivan's ratio x what a head produces."""
    from xylarium.kernel.demography import _tax_per_head_quarter
    return planet.population * foreignness(kernel, planet) * POLICE_PER_HEAD * _tax_per_head_quarter(planet)


def lanchester(a: float, d: float) -> Dict[str, float]:
    """Expected outcome of strength a against d: who wins, and what each keeps."""
    if a > d:
        return {"won": 1.0, "attacker_left": math.sqrt(a * a - d * d), "defender_left": 0.0}
    return {"won": 0.0, "attacker_left": 0.0, "defender_left": math.sqrt(max(0.0, d * d - a * a))}


# ---------------------------------------------------------------------- the season
def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel.demography import _pay_contractor
    st = stats(kernel)
    logs: List[str] = []
    held = 0
    for sec in kernel.sectors.values():
        for p in sec.planets:
            rec = record(p)
            if not rec:
                continue
            if p.population <= 0 or p.owner_id != rec["by"]:
                p.society.pop("occupation", None)           # emptied, or taken again (a new record was made)
                continue
            _learn(kernel, p, rec)
            f = foreignness(kernel, p)
            st["emigrated"] = st.get("emigrated", 0) + _emigrate(kernel, p, rec, f)
            need = policing_need(kernel, p)
            paid = min(max(0, p.treasury), int(need))
            if paid > 0:
                _pay_contractor(kernel, p, paid)            # the garrison's pay is spent where it is posted
            short = (need - paid) / need if need > 0 else 0.0
            rec["unrest"] = round(rec["unrest"] * 0.5 + short, 4)
            rec["foreignness"] = round(foreignness(kernel, p), 4)
            if rec["unrest"] >= 1.0:
                occupier = kernel.captains.get(rec["by"])
                p.owner_id = None
                p.faction_id = None
                p.society.pop("occupation", None)
                st["revolts"] += 1
                from xylarium.kernel import history
                history.event(kernel, "REVOLT", f"{p.name} throws out its occupier", actors=[f"captain:{rec['by']}"],
                              planet=p, magnitude=p.population, cause=f"unrest {rec['unrest']:.2f}: policing unpaid")
                logs.append(f"[OCCUPATION] {p.name} rises and throws out "
                            f"{occupier.name if occupier else 'its occupier'}: it is its people's own again.")
                continue
            held += 1
    st["held"] = held
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"held": st.get("held", 0), "conquests": st["conquests"], "revolts": st["revolts"],
            "emigrated": st.get("emigrated", 0)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="occupation",
    state=lambda: {"conquests": 0, "revolts": 0, "held": 0},
    season=quarter,
    summary=summary,
))
