"""
Xylarium introspection: a people looks at itself, chooses what it is for, and acts on it - with integrity.

We are agnostic about what a civilization should want. Each people decides that itself, from what it is. Once a
year every people reads its own gauges, each 0 .. 1, from the state of its worlds:

    sustenance   it feeds itself                      (self-sufficiency)
    vitality     it renews itself                     (fertility against replacement, and meaning)
    knowledge    it knows                             (its stocks, along the learning curve)
    intellect    it can solve what it has not seen    (its fluid intelligence)
    creativity   it brings new forms into being       (see below)
    prosperity   its households are provided for      (luxury access)
    peace        it is at no war over food            (active food wars)
    integrity    its works are its own                (see below)

It weighs them by its ASPIRATIONS, which come from its own character, not from us: what its alignment leans to
(the luminous weigh peace, integrity and creativity more; the shadowed prosperity and their own sustenance), what
its minds are (deep, cold minds weigh knowledge; quick ones prosperity), and what it has gone without (scarcity is
salient). Its GOAL is its widest weighted gap; it pulls the lever it holds for that goal - its rulers' inquiry
(knowledge.focus), its restraint from raids, its resistance to selling out its art. Whether pursuing its goal
worked is felt next year: the gap's closing is PURPOSE, and purpose is a prospect in meaning (fertility.meaning) -
a people living toward what it chose has more to live for. That is how a civilization builds alignment toward its
own goals without anyone handing it any.

CREATIVITY is defined by speciation: novelty that lives. A people's creative output in a year is what it brought
into being that no other people holds and that holds up - new species born of its worlds (genome.py), crystals
of its own making no other people knows (intellect.py abstractions), and luxury signatures that are both unique
to it and its own (authentic). Its creativity gauge is that output over the last years.

ARTISTIC INTEGRITY is how much of a people's art still expresses what it is: the share of its worlds crafting the
signature their own world and nature gave them (luxury.signature), not the one the market paid more for
(luxury.reconsider). A people that values integrity asks a greater premium before it sells out.
"""

import math
from typing import Any, Dict, List, Optional

GAUGES = ("sustenance", "vitality", "knowledge", "intellect", "creativity", "prosperity", "peace", "integrity")
LEVERS = {                       # the lever a people holds for each goal
    "sustenance": ("focus", "biology"), "vitality": ("focus", "biology"), "knowledge": ("focus", "information"),
    "intellect": ("focus", "information"), "creativity": ("focus", "information"),
    "prosperity": ("focus", "materials"), "peace": ("restraint", None), "integrity": ("integrity", None),
}


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "introspect")


# ---------------------------------------------------------------------- creativity and integrity
def _novel_crystals(kernel: Any, holder: str, vocabs: Dict[str, set]) -> int:
    from xylarium.kernel import intellect
    mine = {c for c in vocabs.get(holder, set()) if isinstance(c, tuple) and c and c[0] == "composite"}
    others = set().union(*(v for h, v in vocabs.items() if h != holder)) if len(vocabs) > 1 else set()
    return len(mine - others)


def _signatures(kernel: Any, worlds: List[Any]) -> Dict[str, Any]:
    out = {}
    for p in worlds:
        lux = p.society.get("luxury")
        if lux:
            out[p.id] = (lux.get("type"), lux.get("name"), p.society.get("luxury_origin") == lux.get("type"))
    return out


def integrity(worlds: List[Any]) -> float:
    crafted = [p for p in worlds if p.society.get("luxury")]
    if not crafted:
        return 1.0
    return sum(1 for p in crafted if p.society.get("luxury_origin", p.society["luxury"].get("type"))
               == p.society["luxury"].get("type")) / len(crafted)


def integrity_weight(kernel: Any, planet: Any) -> float:
    """How much a people values its art staying its own (its aspiration weight on integrity, 0 if unknown)."""
    from xylarium.kernel import knowledge
    if kernel is None or not hasattr(kernel, "state") or "introspect" not in kernel.state:
        return 0.0
    h = knowledge.holder_of_planet(planet)
    return float((stats(kernel)["peoples"].get(h) or {}).get("aspirations", {}).get("integrity", 0.0))


# ---------------------------------------------------------------------- gauges and aspirations
def _peoples(kernel: Any) -> Dict[str, List[Any]]:
    from xylarium.kernel import knowledge
    out: Dict[str, List[Any]] = {}
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population > 0 and not getattr(p, "natives", None):
                h = knowledge.holder_of_planet(p)
                if h:
                    out.setdefault(h, []).append(p)
    return out


def _mean(worlds: List[Any], f) -> float:
    n = sum(p.population for p in worlds) or 1
    return sum(f(p) * p.population for p in worlds) / n


def gauges(kernel: Any, holder: str, worlds: List[Any], creative: float) -> Dict[str, float]:
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import intellect, knowledge, laws, sustenance
    wars = sum(1 for w in sustenance.stats(kernel)["wars"].values() if holder in (w["a"], w["b"]))
    return {
        "sustenance": _mean(worlds, lambda p: min(1.0, float(p.society.get("self_sufficiency", 1.0) or 1.0))),
        "vitality": _mean(worlds, lambda p: min(1.0, float(p.society.get("fertility", 1.0) or 1.0))
                          * min(1.0, float((p.society.get("fertility_parts") or {}).get("meaning", 1.0)))),
        "knowledge": laws.mastery(sum(knowledge.stocks(kernel, holder).values()), 4 * KNOWLEDGE_UNIT),
        "intellect": intellect.fluid(kernel, holder),
        "creativity": creative,
        "prosperity": _mean(worlds, lambda p: min(1.0, float(p.society.get("lux_access", 0.0) or 0.0))),
        "peace": 1.0 / (1.0 + wars),
        "integrity": integrity(worlds),
    }


def aspirations(kernel: Any, holder: str, worlds: List[Any], g: Dict[str, float]) -> Dict[str, float]:
    """What this people wants, from what it is: its alignment, its minds, and what it has gone without."""
    from xylarium.kernel import decide
    p0 = max(worlds, key=lambda p: p.population)
    civ = getattr(p0, "civilization", None)
    owner = kernel.captains.get(p0.owner_id) if p0.owner_id else None
    a = float(getattr(owner, "cosmic_alignment", 0.0) if owner is not None else getattr(civ, "alignment", 0.0) or 0.0)
    mind = decide.mind_of_planet(kernel, p0)
    deep = 1.0 / max(0.1, mind["noise"])              # cold, deep minds weigh what can be known
    w = {x: 1.0 for x in GAUGES}
    w["peace"] += max(0.0, a)
    w["integrity"] += max(0.0, a)
    w["creativity"] += max(0.0, a) / 2
    w["prosperity"] += max(0.0, -a)
    w["sustenance"] += max(0.0, -a) / 2
    w["knowledge"] *= math.sqrt(deep)
    w["intellect"] *= math.sqrt(deep)
    w["prosperity"] *= math.sqrt(mind["noise"])
    for x in GAUGES:                                  # scarcity is salient
        w[x] *= 1.0 + max(0.0, 0.5 - g[x])
    return {x: round(v, 3) for x, v in w.items()}


# ---------------------------------------------------------------------- the year
def _creative_output(kernel: Any, holder: str, worlds: List[Any], vocabs: Dict[str, set],
                     all_sigs: Dict[str, Dict[str, Any]]) -> float:
    from xylarium.kernel import genome
    st = stats(kernel)
    rec = st["peoples"].setdefault(holder, {})
    seen = rec.setdefault("seen", {"species": 0, "crystals": 0, "signatures": []})
    births = genome.stats(kernel).get("born_of", {}).get(holder, 0)
    crystals = _novel_crystals(kernel, holder, vocabs)
    mine = {v[1] for k, v in all_sigs.get(holder, {}).items() if v[2]}            # authentic signatures
    theirs = {v[1] for h, s in all_sigs.items() if h != holder for v in s.values()}
    unique = sorted(mine - theirs)
    new = max(0, births - seen["species"]) + max(0, crystals - seen["crystals"]) + \
        len(set(unique) - set(seen["signatures"]))
    seen.update(species=births, crystals=crystals, signatures=unique)
    hist = rec.setdefault("creations", [])
    hist.append(new)
    del hist[:-4]
    return sum(hist) / max(1, len(hist))


def _act(kernel: Any, holder: str, goal: str) -> None:
    from xylarium.kernel import knowledge
    kind, arg = LEVERS[goal]
    rec = stats(kernel)["peoples"][holder]
    rec["restraint"] = kind == "restraint"
    if kind == "focus":
        if not holder.startswith("captain:") or _ai_holder(kernel, holder):
            knowledge.focus(kernel, holder, arg)


def _ai_holder(kernel: Any, holder: str) -> bool:
    cap = kernel.captains.get(holder.partition(":")[2])
    return cap is not None and getattr(cap, "is_ai", False)


def restrained(kernel: Any, planet: Any) -> bool:
    """A people whose chosen goal is peace holds back its raids."""
    from xylarium.kernel import knowledge
    if kernel is None or "introspect" not in getattr(kernel, "state", {}):
        return False
    return bool((stats(kernel)["peoples"].get(knowledge.holder_of_planet(planet)) or {}).get("restraint"))


def purpose(kernel: Any, holder: Optional[str]) -> float:
    if not holder or kernel is None or "introspect" not in getattr(kernel, "state", {}):
        return 0.0
    return float((stats(kernel)["peoples"].get(holder) or {}).get("purpose", 0.0))


def quarter(kernel: Any) -> List[str]:
    if (kernel.cycle_count // _quarter()) % 4:
        return []
    from xylarium.kernel import intellect
    st = stats(kernel)
    peoples = _peoples(kernel)
    vocabs = {h: set(intellect.vocabulary(kernel, h)) for h in peoples}
    sigs = {h: _signatures(kernel, ws) for h, ws in peoples.items()}
    logs = []
    # creativity is measured against the universe's own rate of novelty: a people creating at the mean rate of
    # all peoples stands at one half, one creating nothing at zero
    outputs = {h: _creative_output(kernel, h, ws, vocabs, sigs) for h, ws in peoples.items()}
    rate = sum(outputs.values()) / max(1, len(outputs))
    for holder, worlds in peoples.items():
        creative = outputs[holder] / (outputs[holder] + rate) if rate > 0 else 0.0
        g = gauges(kernel, holder, worlds, creative)
        w = aspirations(kernel, holder, worlds, g)
        rec = st["peoples"].setdefault(holder, {})
        # purpose: did last year's goal's gap close?
        last_goal, last_gap = rec.get("goal"), rec.get("gap")
        if last_goal in g and last_gap:
            now_gap = 1.0 - g[last_goal]
            rec["purpose"] = round(max(-1.0, min(1.0, (last_gap - now_gap) / max(0.05, last_gap))), 3)
        gaps = {x: w[x] * (1.0 - g[x]) for x in GAUGES}
        goal = max(gaps, key=gaps.get)
        if goal != last_goal:
            st["goal_changes"] += 1
        rec.update(gauges={k: round(v, 3) for k, v in g.items()}, aspirations=w, goal=goal,
                   gap=round(1.0 - g[goal], 4))
        _act(kernel, holder, goal)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    goals: Dict[str, int] = {}
    mean = {x: 0.0 for x in GAUGES}
    n = 0
    for rec in st["peoples"].values():
        if "goal" not in rec:
            continue
        goals[rec["goal"]] = goals.get(rec["goal"], 0) + 1
        for x in GAUGES:
            mean[x] += rec["gauges"].get(x, 0.0)
        n += 1
    return {"goals": goals, "mean_gauges": {x: round(v / max(1, n), 3) for x, v in mean.items()},
            "goal_changes": st["goal_changes"],
            "purposeful": sum(1 for r in st["peoples"].values() if r.get("purpose", 0) > 0)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="introspect",
    state=lambda: {"peoples": {}, "goal_changes": 0},
    season=quarter,
    summary=summary,
))
