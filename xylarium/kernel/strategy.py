"""
Xylarium strategy: a people's council deduces where it stands and chooses how to stand - and learns from what came
of it.

No posture is assigned and no rule says "if hungry, expand". Each generation a council reads its own situation -
what it can see of itself (introspect.py's gauges, through its own judgement), of its world and star, of its
neighbours - and weighs five ways to stand over its planning horizon (decide.choose: its own mind, its own noise):

  GROW      settle the room in its reach and enlarge its land (worth: the people that room would hold)
  DEEPEN    build works and learn (worth: the room its next works add, and the knowledge it lacks of its next
            bridge - the crossing, if it has not crossed)
  SECURE    pacts, federations and arms against those who could hurt it (worth: the losses its neighbours' raids
            and strikes would cost it, as its model of each neighbour expects - from what that neighbour has done:
            its wars, raids and strikes in the ledger - over the horizon)
  HOLD      keep what it has - its sky, its fields, its people before a dying star (worth: what it would lose: the
            air already gone, the years its star has left against its horizon)
  REACH     everything toward the stars (worth: the room beyond its system, if its mathematics is near the
            crossing - its fourth-axis crystals held - and it has not crossed)

Each worth is then weighed by what the council has learned: every posture it has held is scored by how its own
syntropy index moved while it held it (syntropy.py), against how it moved under the others - so a people whose
growth failed it turns from growing, and one that prospered by securing itself keeps doing so. Its memory fades as
its knowledge does (its depreciation), so old lessons give way to new ones.

What a posture does: every choice its council makes afterwards (decide.choose) weighs the options that serve its
posture - each option says what it serves (its "aim") - by one plus the posture's share of all it judged worth
doing. It does not forbid anything; it is where a people puts its weight.
"""

import math
from typing import Any, Dict, List, Optional

POSTURES = ("grow", "deepen", "secure", "hold", "reach")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "strategy")


def of(kernel: Any, holder: Optional[str]) -> Dict[str, Any]:
    if not holder or kernel is None or "strategy" not in getattr(kernel, "state", {}):
        return {}
    return stats(kernel)["of"].get(holder, {})


def hostility(kernel: Any, other: str) -> float:
    """A council's model of a neighbour: how often it has hurt others - its wars, raids, strikes and conquests in
    the ledger - per year it has lived."""
    from xylarium.kernel import history
    hurt = sum(1 for e in history.of_people(kernel, other)
               if e.get("kind") in ("GALACTIC_WAR", "WAR", "RAID", "WORLD_STRIPPED", "CONQUEST", "STRIFE"))
    return hurt


def _worths(kernel: Any, who: str, worlds: List[Any], by: Dict[str, List[Any]]) -> Dict[str, float]:
    from xylarium.kernel import (alignment, biosphere, cosmos, crystal as C, decide, intellect, mastery,
                                 relations, syntropy)
    home = max(worlds, key=lambda p: p.population)
    m = decide.mind_of_planet(kernel, home)
    horizon_q = decide.horizon(m)
    sc = alignment.scales(kernel)
    life = sc["sol"] / max(1.0, sc["lives"])
    n = sum(p.population for p in worlds)
    out = {}
    # grow: the room in reach, valued as lives
    room = sum(syntropy.room_in_reach(kernel, p) for p in worlds)
    out["grow"] = room * life
    # deepen: the next works' room, and its distance from its next bridge
    nxt = biosphere.carrying_capacity(kernel, home, citadel=home.citadel_level + 1) \
        - biosphere.carrying_capacity(kernel, home)
    out["deepen"] = max(0.0, nxt) * life
    # secure: what the neighbours that can reach it would take, as it reads them
    loss, _ = relations.threat(kernel, who, worlds, by, {}, relations._pressed_share(kernel))
    from xylarium.kernel import technology
    from xylarium.kernel import contact
    feared = 0.0
    for o in by:
        if o == who:
            continue
        # its model of a neighbour: what it has done, what it can do to it unseen, and - as far as it understands
        # that neighbour - what it is now set on (a neighbour turned to growing is coming for room)
        f = math.log1p(hostility(kernel, o)) + (1.0 if technology.has(kernel, o, "cyber") else 0.0)
        theirs = of(kernel, o).get("posture")
        if theirs in ("grow", "secure"):
            f += contact.intelligibility(kernel, who, o, by) * (1.0 if theirs == "grow" else 0.5)
        feared += f
    out["secure"] = decide.worth(kernel, loss, m) * (1.0 + feared)
    # hold: its sky lost, its star's years against its horizon
    air = sum((1.0 - float(p.society.get("atmosphere", 1.0))) * p.population for p in worlds)
    years = cosmos.years_left(kernel, home.sector_id) if cosmos.is_cosmic(kernel) else None
    doom = 0.0 if years is None else math.exp(-years / max(1.0, horizon_q / 4.0))
    out["hold"] = (air + doom * n) * life
    # reach: the room beyond, when its mathematics is near the fold and it has not crossed
    near = 0.0
    if not mastery.crossed(kernel, who):
        vocab = intellect.stats(kernel).get("vocab", {}).get(who, [])
        near = sum(1 for c in vocab if c in C.STACK_OPS or c in C.HYPER_OPS) / max(1, len(C.STACK_OPS) + len(C.HYPER_OPS))
    out["reach"] = near * n * life
    return out


def season(kernel: Any) -> List[str]:
    """Once a year each council reads itself and its neighbours; once a generation it may change how it stands."""
    from xylarium.kernel import decide, fertility, history, laws, relations, syntropy
    if (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    by = relations._peoples(kernel)
    logs: List[str] = []
    for who in sorted(by):
        worlds = by[who]
        home = max(worlds, key=lambda p: p.population)
        rec = st["of"].setdefault(who, {"posture": None, "since": kernel.cycle_count, "learned": {},
                                        "s_then": None})
        s_now = syntropy.index(kernel, who, worlds)["S"]
        # what holding its posture has done for it: its syntropy's change a year, remembered with fading weight
        if rec["posture"] and rec["s_then"] is not None:
            years = max(1e-3, (kernel.cycle_count - rec.get("read_at", rec["since"])) / 100.0)
            slope = (s_now - rec["s_then"]) / years
            keep = 1.0 - laws.KNOWLEDGE_DEPRECIATION
            old = rec["learned"].get(rec["posture"], {"slope": 0.0, "weight": 0.0})
            w = old["weight"] * keep + 1.0
            rec["learned"][rec["posture"]] = {"slope": (old["slope"] * old["weight"] * keep + slope) / w, "weight": w}
        rec["s_then"], rec["read_at"] = s_now, kernel.cycle_count
        gen = max(1.0, fertility.generation_of(kernel, home))
        if rec["posture"] and (kernel.cycle_count - rec["since"]) / 100.0 < gen:
            continue                                          # a council keeps its course a generation
        worths = _worths(kernel, who, worlds, by)
        slopes = [v["slope"] for v in rec["learned"].values()] or [0.0]
        mean = sum(slopes) / len(slopes)
        opts = []
        for p in ("grow", "deepen", "secure", "hold", "reach"):
            learned = rec["learned"].get(p)
            lesson = math.exp(max(-3.0, min(3.0, (learned["slope"] - mean) * gen))) if learned else 1.0
            opts.append(decide.option(p, 0.0, worths[p] * lesson))
        pick = decide.choose(kernel, opts, decide.mind_of_planet(kernel, home), who, "posture")
        if pick is None:
            continue
        total = sum(max(0.0, o["value"]) for o in opts) or 1.0
        if pick["name"] != rec["posture"]:
            was = rec["posture"]
            rec["posture"], rec["since"] = pick["name"], kernel.cycle_count
            st["turns"] += 1
            if was is not None:
                history.event(kernel, "POSTURE", f"The {who.split(':', 1)[-1]} turn to {pick['name']}",
                              actors=[who], planet=home,
                              cause=f"its council read its standing and what {was} had brought it",
                              data={"from": was, "to": pick["name"]})
        rec["focus"] = round(max(0.0, pick["value"]) / total, 4)
    return logs


def weight(m: Dict[str, Any], option: Dict[str, Any]) -> float:
    """How much an option counts for a council's posture (decide.choose reads it)."""
    aim = option.get("aim")
    if not aim or m.get("posture") is None:
        return 1.0
    return 1.0 + float(m.get("focus", 0.0)) if aim == m["posture"] else 1.0


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    held: Dict[str, int] = {}
    for r in st["of"].values():
        if r.get("posture"):
            held[r["posture"]] = held.get(r["posture"], 0) + 1
    return {"postures": held, "turns": st["turns"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="strategy", state=lambda: {"of": {}, "turns": 0}, season=season, summary=summary))
