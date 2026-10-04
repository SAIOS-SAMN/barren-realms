"""
Xylarium guidance: what peoples among the stars choose to do for minds younger than themselves.

Nothing obliges an elder people to anything. Once a year each people among the stars (linked to the interstellar
community, with yards to sail from) weighs, through its own mind (decide.choose), what it could do for the younger
peoples it has met and the empty worlds its fleets can reach:

  UPLIFT   send an embassy to a younger people it has met and teach what it knows - its teachers' passage the
           cost (a knowledge unit is a thousand minds' year of thought: so many teachers for a year). What is
           taught is the gap between them in each domain, as far as the two understand each other
           (contact.intelligibility): strangers whose senses and mathematics differ learn little from one visit.
           Its worth is the lives it lifts - the younger people's number, by the share of the elder's knowledge
           it gains - as much as the elder values strangers' lives (its alignment toward the Light).
  SEED     set a designed people down on an empty world its fleets reach that can feed one (designer.seed): its
           own biology or another its designers can build for that world. Worth: the lives that world will hold,
           valued the same way; cost: the voyage and the design.
  NOTHING  always an option, worth nothing.

The consequences come back to the chooser: teaching and seeding are help (alignment.measure: toward the Light), and
the younger people meets the sky differently once it has been visited (culture.py reads its contacts). A people of
the Dark values strangers at nothing and never chooses either; it has other options (occupation.py). No outcome is
imposed: the guidance of later minds by earlier ones happens only where the earlier ones choose it.
"""

from typing import Any, Dict, List, Optional


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "guidance")


def _elders(kernel: Any) -> Dict[str, List[Any]]:
    """Peoples among the stars and their yards worlds."""
    from xylarium.kernel import culture, exodus
    out: Dict[str, List[Any]] = {}
    for holder in culture.linked_peoples(kernel):
        ports = exodus._fleets(kernel, holder)
        if ports:
            out[holder] = ports
    return out


def _light(planet: Any) -> float:
    return max(0.0, float(getattr(getattr(planet, "civilization", None), "alignment", 0.0) or 0.0))


def teaching(kernel: Any, elder: str, young: str) -> Dict[str, float]:
    """What an embassy would teach: the gap in each domain, as far as the two understand each other."""
    from xylarium.kernel import contact, knowledge
    understood = contact.intelligibility(kernel, elder, young)
    a, b = knowledge.stocks(kernel, elder), knowledge.stocks(kernel, young)
    return {d: max(0.0, a.get(d, 0.0) - b.get(d, 0.0)) * understood for d in knowledge.DOMAINS}


def _uplift(kernel: Any, elder: str, port: Any, young: str, worlds: List[Any]) -> Optional[str]:
    from xylarium.kernel import decide, exodus, history, knowledge, sustenance
    lesson = teaching(kernel, elder, young)
    known = sum(knowledge.stocks(kernel, elder).values())
    taught = sum(lesson.values())
    if known <= 0 or taught <= 0:
        return None
    m = decide.mind_of_planet(kernel, port)
    lives = sum(p.population for p in worlds) * taught / known
    teachers = int(1000 * taught) + 1                        # a knowledge unit: a thousand minds' year of thought
    fare = exodus._fare(kernel, teachers, port)
    if decide.choose(kernel, [decide.option("uplift", fare, exodus._worth(kernel, port, int(lives), m) * _light(port))],
                     m, port.id, "uplift", young) is None:
        return None
    for d, u in lesson.items():
        knowledge.learn(kernel, young, d, u, why="taught")
    sustenance.flow_civ(port, light=lives)              # the lives its lesson reaches
    st = stats(kernel)
    st["uplifts"] += 1
    ename, yname = elder.split(":", 1)[-1], young.split(":", 1)[-1]
    history.event(kernel, "UPLIFT", f"The {ename} teach the {yname}", actors=[elder, young], planet=worlds[0],
                  magnitude=int(taught), cause="an embassy among the stars, as far as they understood each other",
                  data={"taught": {d: round(u, 3) for d, u in lesson.items()}})
    return f"[GUIDANCE] The {ename} teach the {yname} ({taught:,.1f} knowledge units)."


def _seed(kernel: Any, elder: str, port: Any) -> Optional[str]:
    from xylarium.config import HABITABILITY
    from xylarium.kernel import biosphere, decide, demography, designer, exodus, sustenance
    from xylarium.kernel import topology
    if _light(port) <= 0:
        return None                                       # it values strangers' lives at nothing: seeding is worth nothing
    m = decide.mind_of_planet(kernel, port)
    own = biosphere.metabolism_of(kernel, port)
    best = None
    # a council weighs only as many worlds as its mind can hold at once (learning.attention): the likeliest first -
    # the worlds of its reach whose kind most suits a kind of life, its own kind first
    from xylarium.kernel import learning
    candidates = []
    for sid in topology.reach(kernel, port.sector_id, max(1, demography.settler_reach(kernel, port))):
        sec = kernel.sectors.get(sid)
        if sec is None:
            continue
        for w in sec.planets:
            if w.population > 0 or getattr(w, "civilization", None) is not None or w.owner_id:
                continue
            for metab in sorted(HABITABILITY, key=lambda x: (x != own, x)):
                fit = HABITABILITY[metab].get(w.planet_type, 0.0)
                if fit > 0:
                    candidates.append((-fit, metab != own, w.id, metab, w))
    for _, _, _, metab, w in sorted(candidates, key=lambda c: c[:4])[:learning.attention(m)]:
        pv = designer.preview(kernel, elder, {"metabolism": metab}, w)
        if pv["why_not"]:
            continue
        if best is None or pv["foragers_fed"] > best[0]["foragers_fed"]:
            best = (pv, w, metab)
    if best is None:
        return None
    pv, w, metab = best
    cost = pv["cost"] + exodus._fare(kernel, designer.FOUNDERS, port)
    value = exodus._worth(kernel, port, pv["foragers_fed"], m) * _light(port)
    if decide.choose(kernel, [decide.option("seed", cost, value)], m, port.id, "seed", w.id) is None:
        return None
    ename = elder.split(":", 1)[-1]
    out = designer.seed(kernel, elder, {"metabolism": metab}, w, ename)
    if out.get("why_not"):
        return None
    sustenance.flow_civ(port, light=pv["foragers_fed"])   # the lives the seeded world will feed
    stats(kernel)["seeded"] += 1
    return f"[GUIDANCE] The {ename} seed a {metab} people on {w.name}."


# ---------------------------------------------------------------------- the season
def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import contact, cosmos, culture, exodus
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // FISCAL_QUARTER_CYCLES) % 4:
        return []                                             # once a year
    elders = _elders(kernel)
    if not elders:
        return []
    fam = contact.stats(kernel)["familiarity"]
    young: Dict[str, List[Any]] = {}
    for s in kernel.sectors.values():
        for p in s.planets:
            h = exodus._holder(p)
            if p.population > 0 and h and h.startswith("civ:") and not culture.is_linked(kernel, h):
                young.setdefault(h, []).append(p)
    logs: List[str] = []
    for elder in sorted(elders):
        port = max(elders[elder], key=lambda p: (p.population, p.id))
        if _light(port) <= 0:
            continue                                          # strangers' lives weigh nothing to it
        from xylarium.kernel import federation
        for y in sorted(young):
            if federation.forbids(kernel, elder, "uplift", y):
                continue                                      # its federation leaves the young to find the stars
            if contact._key(elder, y) in fam:
                line = _uplift(kernel, elder, port, y, young[y])
                if line:
                    logs.append(line)
        line = _seed(kernel, elder, port)
        if line:
            logs.append(line)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"uplifts": st["uplifts"], "seeded": st["seeded"]} if (st["uplifts"] or st["seeded"]) else {}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="guidance",
    state=lambda: {"uplifts": 0, "seeded": 0},
    season=quarter,
    summary=summary,
))
