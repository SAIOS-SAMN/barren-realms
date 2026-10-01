"""
Xylarium contact: whether two peoples can understand each other - and what happens when they cannot.

Nothing here says who may talk to whom. Intelligibility between two peoples follows from what they are and what
they have done together:

  CHANNEL    every people signals in the band its substrate's temperature sets (Wien: a hotter emitter speaks at
             higher frequency) and thinks at that substrate's kinetic pace (~ sqrt T). Two peoples overlap as
             exp(-1.5 |ln(T_a / T_b)|): biotic and lithic minds share most of a band; a cryogenic mind and a plasmic
             one can barely perceive each other, let alone converse.
  MATHEMATICS  the crystals both hold (intellect.py) are transformations both can express - a lingua franca of
             structure. Their overlap (shared / either) is understood from the first meeting.
  FAMILIARITY  grows with contact - peoples whose ships reach each other's worlds - at a rate set by what the pair
             knows of information (interpreters, translation), and fades without contact as all knowledge does.
  STANDARDS  each people keeps a protocol (at first its own). Once a year it adopts the protocol most of its
             contacts use when the misunderstanding that removes is worth the switch (decide.py). Two peoples on one
             protocol understand each other as well as their channel allows.

  intelligibility = channel x (1 - (1 - mathematics)(1 - familiarity)), or channel alone on a shared protocol.

What it does: a mind judging a foreign people's offer or threat errs in inverse proportion to how well it
understands it (misread() raises its noise): two peoples who barely understand each other misread raids as wars and
offers as threats, and their contracts fail. Before a fed people plunders, it may parley - offer protection for
tribute (relations.py) - and the offer is only as credible as the two can understand each other. Energy is bridged
only to peoples one can understand well enough to contract with (energy.py).
"""

import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

from xylarium.kernel import laws


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "contact")


def _key(a: str, b: str) -> str:
    return f"{a}|{b}" if a < b else f"{b}|{a}"


def _temperature(kernel: Any, people: str, worlds: Optional[List[Any]] = None) -> float:
    from xylarium.kernel import biosphere, genome, relations
    worlds = worlds if worlds is not None else relations._peoples(kernel).get(people, [])
    if not worlds:
        return laws.T_EARTH
    cap = max(worlds, key=lambda w: w.population)
    return laws.cognition(biosphere.metabolism_of(kernel, cap), genome.temperature_factor(cap))["temperature"]


def channel(ta: float, tb: float) -> float:
    return math.exp(-1.5 * abs(math.log(max(1e-9, ta) / max(1e-9, tb))))


def mathematics(kernel: Any, a: str, b: str) -> float:
    from xylarium.kernel import intellect
    va = {str(x) for x in intellect.vocabulary(kernel, a)}
    vb = {str(x) for x in intellect.vocabulary(kernel, b)}
    either = va | vb
    return len(va & vb) / len(either) if either else 0.0


def protocol(kernel: Any, people: str) -> str:
    return stats(kernel)["protocol"].get(people, people)


def intelligibility(kernel: Any, a: Optional[str], b: Optional[str], by: Optional[Dict[str, List[Any]]] = None) -> float:
    """0..1: how well peoples a and b understand each other now."""
    if not a or not b or a == b or kernel is None or not hasattr(kernel, "state"):
        return 1.0
    by = by if by is not None else _by(kernel)
    ch = channel(_temperature(kernel, a, by.get(a)), _temperature(kernel, b, by.get(b)))
    if protocol(kernel, a) == protocol(kernel, b):
        return ch
    fam = float(stats(kernel)["familiarity"].get(_key(a, b), 0.0))
    return ch * (1.0 - (1.0 - mathematics(kernel, a, b)) * (1.0 - fam))


def _channel_only(kernel: Any, a: str, b: str, by: Dict[str, List[Any]]) -> float:
    """What two peoples would understand of each other off a shared protocol: channel x their own mathematics and
    familiarity (the standard's help removed)."""
    ch = channel(_temperature(kernel, a, by.get(a)), _temperature(kernel, b, by.get(b)))
    fam = float(stats(kernel)["familiarity"].get(_key(a, b), 0.0))
    return ch * (1.0 - (1.0 - mathematics(kernel, a, b)) * (1.0 - fam))


def misread(m: Dict[str, float], understood: float) -> Dict[str, float]:
    """A mind judging what it barely understands: its judgement's noise over how well it understands."""
    return dict(m, noise=m["noise"] / max(0.05, understood))


def _by(kernel: Any) -> Dict[str, List[Any]]:
    from xylarium.kernel import relations
    return relations._peoples(kernel)


def contacts(kernel: Any, by: Dict[str, List[Any]]) -> Dict[str, Dict[str, int]]:
    """people -> {other people: how many of the other's worlds its ships reach} (either way round counts)."""
    from xylarium.kernel import cache
    return cache.memo(kernel, "contact_map", kernel.cycle_count, lambda: _contacts(kernel, by), max_age=1)


def _contacts(kernel: Any, by: Dict[str, List[Any]]) -> Dict[str, Dict[str, int]]:
    from xylarium.kernel import relations
    where: Dict[int, List[str]] = {}
    for people, worlds in by.items():
        for w in worlds:
            where.setdefault(w.sector_id, []).append(people)
    out: Dict[str, Dict[str, int]] = {}
    for people, worlds in by.items():
        for w in worlds:
            for sid in relations._reach_map(kernel, w):
                for other in where.get(sid, []):
                    if other == people:
                        continue
                    out.setdefault(people, {})[other] = out.setdefault(people, {}).get(other, 0) + 1
                    out.setdefault(other, {})[people] = out.setdefault(other, {}).get(people, 0) + 1
    return out


def _information(kernel: Any, people: str) -> float:
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge
    return laws.mastery(knowledge.experience(kernel, people, "information"), KNOWLEDGE_UNIT)


def quarter(kernel: Any) -> List[str]:
    st = stats(kernel)
    by = _by(kernel)
    met = contacts(kernel, by)
    fam = st["familiarity"]
    years = _quarter() / 100.0
    fade = 1.0 - (1.0 - laws.KNOWLEDGE_DEPRECIATION) ** years
    touched = set()
    for a, others in met.items():
        for b in others:
            k = _key(a, b)
            if k in touched:
                continue
            touched.add(k)
            if k not in fam:
                st["first_contacts"] += 1
                from xylarium.kernel import primordial
                primordial.first(kernel, "first_contact", k)
            learn = 0.5 * (_information(kernel, a) + _information(kernel, b))
            fam[k] = round(fam.get(k, 0.0) + (1.0 - fam.get(k, 0.0)) * learn * years, 5)
    for k in list(fam):
        if k not in touched:
            fam[k] = round(fam[k] * (1.0 - fade), 5)
            if fam[k] < 1e-4:
                fam.pop(k)
    logs: List[str] = []
    if (kernel.cycle_count // _quarter()) % 4 == 0:
        logs += _standards(kernel, by, met)
    return logs


def _standards(kernel: Any, by: Dict[str, List[Any]], met: Dict[str, Dict[str, int]]) -> List[str]:
    """Each people may adopt the protocol most of its contacts use, when the misunderstanding removed is worth more
    to it than the switch (a season of what its own trade with them is worth, as its council judges it)."""
    from xylarium.kernel import decide
    st = stats(kernel)
    logs: List[str] = []
    for a, others in met.items():
        if a not in by:
            continue
        weight: Dict[str, int] = {}
        for b, n in others.items():
            weight[protocol(kernel, b)] = weight.get(protocol(kernel, b), 0) + n
        if not weight:
            continue
        best, w = max(weight.items(), key=lambda kv: (kv[1], kv[0]))
        mine = protocol(kernel, a)
        if best == mine or w <= weight.get(mine, 0):
            continue
        cap = max(by[a], key=lambda p: p.population)
        # what rides on understanding: each contact's share of the people's output (how much of what its ships reach
        # is that contact). Switching gains the understanding it lacks with the new protocol's users and loses
        # what it has with those still on its own (both judged over its horizon), and every one of its people must
        # learn the new one: a year of their output, eased by what it knows of languages.
        total = max(1, sum(others.values()))
        gained = sum((1.0 - intelligibility(kernel, a, b, by)) * others[b] for b in others
                     if protocol(kernel, b) == best) / total
        kept = sum((1.0 - _channel_only(kernel, a, b, by)) * others[b] for b in others
                   if protocol(kernel, b) == mine and b != a) / total
        from xylarium.kernel.demography import _tax_per_head_quarter
        output_q = sum(p.population * _tax_per_head_quarter(p) for p in by[a])
        m = decide.mind_of_planet(kernel, cap)
        retrain = 4.0 * output_q * (1.0 - _information(kernel, a))     # a year of everyone's learning, eased by knowing
        gain = decide.worth(kernel, gained * output_q, m, cap.currency)
        cost = decide.worth(kernel, kept * output_q, m, cap.currency) + retrain
        if decide.choose(kernel, [decide.option("adopt_standard", cost, gain)], m, a, "standard") is None:
            continue
        st["protocol"][a] = best
        st["adoptions"] += 1
        from xylarium.kernel import primordial
        primordial.first(kernel, "first_shared_standard", f"{a} adopts {best}'s protocol")
        logs.append(f"[CONTACT] {a.split(':', 1)[-1]} adopts the protocol of {best.split(':', 1)[-1]}.")
    return logs


def switch_terms(kernel: Any, a: str, new: str, by: Dict[str, List[Any]]) -> Tuple[float, float]:
    """(share of its output whose understanding a people would lose a season by leaving its protocol for `new`,
    a year of everyone's learning in its own money)."""
    from xylarium.kernel.demography import _tax_per_head_quarter
    others = contacts(kernel, by).get(a, {})
    mine = protocol(kernel, a)
    if new == mine or a not in by:
        return 0.0, 0.0
    total = max(1, sum(others.values()))
    kept = sum((1.0 - _channel_only(kernel, a, b, by)) * n for b, n in others.items()
               if protocol(kernel, b) == mine) / total
    output_q = sum(p.population * _tax_per_head_quarter(p) for p in by[a])
    return kept, 4.0 * output_q * (1.0 - _information(kernel, a))


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    by = _by(kernel)
    groups: Dict[str, int] = {}
    for people in by:
        groups[protocol(kernel, people)] = groups.get(protocol(kernel, people), 0) + 1
    fam = st["familiarity"]
    top = sorted(groups.items(), key=lambda kv: -kv[1])[:3]
    return {"pairs_in_contact": len(fam), "first_contacts": st["first_contacts"],
            "mean_familiarity": round(sum(fam.values()) / len(fam), 3) if fam else 0.0,
            "protocols": len(groups), "largest_standards": top, "adoptions": st["adoptions"],
            "parleys": st["parleys"], "misread_raids": st["misread_raids"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="contact",
    state=lambda: {"familiarity": {}, "protocol": {}, "first_contacts": 0, "adoptions": 0, "parleys": 0,
                   "misread_raids": 0},
    season=quarter,
    summary=summary,
))
