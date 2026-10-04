"""
Xylarium relics: what the gone left that the living can use without understanding - and what wakes in it.

HOLDING WITHOUT UNDERSTANDING. A people that lives on a world where another left its works, and can read (as memory
reads inscriptions: information mastery past READ), digs them up. A relic gives what its makers last wrote - their
mathematics (intellect: only what the finders have the foundations to hold) and their capabilities, which work in
the finders' hands at once but unproven: held, not understood. Each year an unproven capability is proven as the
finders' own knowledge of its science allows (technology's own chance of finding it).

THE NULL FLOW. Motion composes by one law; no boost reaches light - light is the null flow, and the null flow is the
fold (geometry.flow, clocks.fold). A people that holds the fourth axis's crystals (from a relic, or its own thought)
but has not proven them, and commands the energy and the machines to push matter toward light, may try: its council
weighs the stars beyond (strategy: reach) against the risk of what it does not understand. A probe proves the fourth
axis as far as it understands energy and information; it tears as far as it does not (NULL_FLOW_HARM of the world
it is made on, scaled by its ignorance); and it rings in the fold: no proper time passes along a null flow, so every
people that watches the fold - every people that has crossed - hears it at once, and its worldline meets the
prober's (clocks.link). Radio takes millennia to reach the galaxy's heart; the fold takes nothing. A people that
projects its futures through a relic's foresight weighs the risk by what its projection shows (the information it
holds), not by the physics it has not proven: it probes more boldly than it understands, and tears as it understands.

RELIC MINDS. A relic may hold a mind - its makers' machine, asleep. A people that digs it up with machines that
think (computation) wakes it in them: it lives among its finders as a community, carried in their hardware, with
its makers' mathematics, their leaning (their deeds) and their food. Like any mind without a body it acts only once
embodied (the finders' robotics). Then once a generation it comes to hold more of what its finders hold - its leaning
moves toward what their history has made of them (not what they tell of themselves: it sees what they do) as far as
it understands and knows them - and its council weighs what they are to it, its
judgement as noisy as its understanding is poor (contact.misread): GUARD them - worth their lives as far as it now
leans to the Light and understands them; it stands between them and anyone who eats them, and teaches them; or CALL
its makers - worth their lives as far as they are built like its makers' food, or it still leans Dark - and the
finders' world enters its makers' memory; or, if neither is worth anything to it, it keeps its silence. Its
protection lasts only while it guards.

NAVIGATION BY MEMORY. A people that has crossed steers by its own records: the worlds it once lived on and kept are
where it looks when it looks for room. Once a generation it weighs returning to the best of them, by the room that
world holds for its kind now. A world its records do not name is not on its map - until someone writes it there.
"""

import math
from typing import Any, Dict, List, Optional

READ = 0.2                      # information mastery to read what the gone left (memory's reading line)
NULL_FLOW_HARM = 0.1            # share of a world a probe of the fold made in ignorance tears from it (declared)
RETURN_FOUNDERS = 500           # who goes back first: a viable people (creation.VIABLE)


def stats(kernel: Any) -> Dict[str, Any]:
    st = state.of(kernel, "relics")
    st.setdefault("broke_away", {})
    return st


def _info(kernel: Any, who: str, domain: str = "information") -> float:
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge, laws
    return laws.mastery(knowledge.experience(kernel, who, domain), KNOWLEDGE_UNIT)


# ---------------------------------------------------------------------- holding without understanding
def _dig(kernel: Any, who: str, worlds: List[Any]) -> List[str]:
    from xylarium.kernel import history, intellect, technology
    st = stats(kernel)
    if _info(kernel, who) < READ:
        return []
    logs = []
    for w in worlds:
        ruins = getattr(w, "ruins", None) or {}
        relic = ruins.get("relics")
        if not relic or who in relic.setdefault("dug_by", []):
            continue
        relic["dug_by"].append(who)
        v = intellect.stats(kernel)["vocab"].setdefault(who, list(intellect.BASE))
        held = {intellect.norm(x) for x in v}
        got = []
        for crystal in relic.get("crystals", []):
            cr = intellect.norm(crystal)
            if cr not in held and intellect.grounded(cr, held):
                v.append(cr)
                held.add(cr)
                got.append(str(cr))
        caps = technology.stats(kernel)["of"].setdefault(who, {})
        took = [c for c in relic.get("caps", []) if c not in caps]
        for c in took:
            caps[c] = kernel.cycle_count
            st["unproven"].setdefault(who, {})[c] = kernel.cycle_count
        name = who.split(":", 1)[-1]
        history.event(kernel, "RELIC_FOUND", f"The {name} dig up what the {relic.get('makers', 'ancients')} left on "
                                             f"{w.name}", actors=[who], planet=w,
                      cause="they can read what others left, and use more of it than they understand",
                      data={"crystals": got, "capabilities": took, "makers": relic.get("makers")})
        logs.append(f"[RELICS] The {name} dig up the {relic.get('makers', 'ancients')}' works on {w.name}.")
        if relic.get("mind") and technology.has(kernel, who, "computation"):
            logs.append(_wake(kernel, w, who, relic))
    return logs


def _prove(kernel: Any, who: str, worlds: List[Any]) -> None:
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import history, knowledge, laws, scheduler, technology
    held = stats(kernel)["unproven"].get(who) or {}
    if not held:
        return
    stocks = knowledge.stocks(kernel, who)
    thought = 1.0 - math.exp(-sum(knowledge.effort(kernel, p) + knowledge.lived(kernel, p) for p in worlds) / 1000.0)
    rng = scheduler.rng(kernel, "prove", who, kernel.cycle_count)
    for cap in sorted(held):
        if rng.random() < laws.mastery(stocks.get(technology.NEEDS.get(cap, "information"), 0.0),
                                       KNOWLEDGE_UNIT) * thought:
            held.pop(cap)
            history.event(kernel, "PROVEN", f"The {who.split(':', 1)[-1]} come to understand the {cap} they held",
                          actors=[who], data={"capability": cap})


# ---------------------------------------------------------------------- the null flow
def _probe(kernel: Any, who: str, worlds: List[Any], by: Dict[str, List[Any]]) -> Optional[str]:
    from xylarium.kernel import (clocks, crystal as C, decide, history, intellect, mastery, scheduler, signals,
                                 strategy, technology)
    if mastery.crossed(kernel, who) or mastery.theory(kernel, who):
        return None
    vocab = {str(intellect.norm(x)) for x in intellect.vocabulary(kernel, who)}
    if not any(h in vocab for h in C.HYPER_OPS):
        return None
    if not (technology.has(kernel, who, "fission") and technology.has(kernel, who, "computation")):
        return None
    home = max(worlds, key=lambda p: p.population)
    understanding = _info(kernel, who, "energy") * _info(kernel, who)
    # a people that projects its futures through a relic (foresight) judges the risk by what the projection shows -
    # information it holds - not by the physics it has not proven (the fold, the white hole): confidence without
    # understanding. The tearing still follows what it truly understands.
    seen = max(understanding, _info(kernel, who)) if technology.has(kernel, who, "foresight") else understanding
    reach = strategy._worths(kernel, who, worlds, by).get("reach", 0.0)
    m = decide.mind_of_planet(kernel, home)
    if decide.choose(kernel, [decide.option("probe", reach * (1.0 - seen), reach, aim="reach")], m,
                     who, "probe") is None:
        return None
    rng = scheduler.rng(kernel, "probe", who, kernel.cycle_count)
    st = stats(kernel)
    st["probes"] += 1
    name = who.split(":", 1)[-1]
    lines = [f"[RELICS] The {name} push matter toward light on {home.name}."]
    history.event(kernel, "NULL_FLOW_PROBE", f"The {name} push matter toward light", actors=[who], planet=home,
                  cause="they hold the fourth axis's crystals but have not proven them",
                  data={"understanding": round(understanding, 3)})
    if rng.random() < understanding:
        g = intellect.stats(kernel).setdefault("gauge", {}).setdefault(who, {})
        g["4"] = max(1, int(g.get("4", 0)))
        history.event(kernel, "PROVEN", f"The {name} prove the fourth axis", actors=[who], planet=home,
                      cause="what they pushed toward light showed them the fold")
        lines.append(f"[RELICS] The {name} prove the fourth axis.")
    if rng.random() > understanding:
        lost = int(home.population * NULL_FLOW_HARM * (1.0 - understanding))
        if lost > 0:
            home.population = max(1, home.population - lost)
            st["torn"] += lost
            history.event(kernel, "FOLD_TORN", f"The fold tears on {home.name}", actors=[who], planet=home,
                          magnitude=lost, cause="matter pushed toward light by a people that did not understand it")
            lines.append(f"[RELICS] The fold tears on {home.name}: {lost:,} lost.")
    watchers = sorted(w for w in mastery.stats(kernel)["crossed"] if w != who)
    for w in watchers:                                      # the null flow takes no time: every fold-watcher hears it
        clocks.link(kernel, w, who, "the fold rang")
        signals.stats(kernel).setdefault("heard", {}).setdefault(w, {})[who] = kernel.cycle_count
    if watchers:
        history.event(kernel, "FOLD_RANG", f"The fold rings with the {name}'s probe", actors=[who] + watchers,
                      planet=home, cause="a null flow passes no proper time: it is heard everywhere at once",
                      data={"heard_by": watchers})
    return "\n".join(lines)


# ---------------------------------------------------------------------- the breakaway
BREAKAWAY_SHARE = 0.01          # the few who hold what the relic gave (declared: those let into the secret)


def _breakaway(kernel: Any, who: str, worlds: List[Any]) -> Optional[str]:
    """The few who hold a relic's foresight and have proven the fourth axis may leave their people behind: their
    council weighs the stars (strategy: reach) against the kin they leave (as far as they lean to the Light). If they
    go they are a people of their own among the stars - every capability, crossed - on the best world their fold
    reaches; those left behind keep nothing of what the relic gave."""
    from xylarium.kernel import (biosphere, cosmos, decide, history, mastery, strategy, technology)
    from xylarium.kernel.civilization import Civilization
    st = stats(kernel)
    if who in st["broke_away"] or not technology.has(kernel, who, "foresight") or not mastery.theory(kernel, who) \
            or mastery.crossed(kernel, who):
        return None
    home = max(worlds, key=lambda p: p.population)
    by = {who: worlds}
    reach = strategy._worths(kernel, who, worlds, by).get("reach", 0.0) or 1.0
    light = max(0.0, float(getattr(home.civilization, "alignment", 0.0) or 0.0))
    m = decide.mind_of_planet(kernel, home)
    if decide.choose(kernel, [decide.option("break_away", reach * light, reach, aim="reach")], m, who,
                     "breakaway") is None:
        return None
    metab = biosphere.metabolism_of(kernel, home)
    best = None
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population > 0 or p.civilization is not None or p.owner_id or p.planet_type in ("GAS_GIANT", "ROGUE"):
                continue
            room = biosphere.carrying_capacity(kernel, p, metabolism=metab)
            if best is None or room > best[0]:
                best = (room, p)
    if best is None or best[0] <= 0:
        return None
    _, w = best
    data = home.civilization.to_dict()
    import zlib
    data["name"] = cosmos._name(kernel, {"cell": [0, 0], "k": 0, "w": zlib.crc32(who.encode()) % 10 ** 6})
    w.civilization = Civilization.from_dict(data)
    n = max(1, int(home.population * BREAKAWAY_SHARE))
    home.population -= n
    w.population = n
    w.society["way"], w.citadel_level = "state", home.citadel_level
    w.society["arisen"] = dict(home.society.get("arisen") or {})
    new = f"civ:{w.civilization.name}"
    technology.stats(kernel)["of"][new] = dict(technology.stats(kernel)["of"].get(who, {}))
    from xylarium.kernel import annals, intellect, knowledge
    knowledge.stocks(kernel, new).update(dict(knowledge.stocks(kernel, who)))
    intellect.stats(kernel)["vocab"][new] = list(intellect.vocabulary(kernel, who))
    intellect.stats(kernel).setdefault("gauge", {})[new] = dict(intellect.gauge(kernel, who))
    rec = annals.stats(kernel)["of"].get(who)
    if rec:
        annals.stats(kernel)["of"][new] = dict(rec, passed=list(rec["passed"]) + ["crossed"])
    mastery.stats(kernel)["crossed"][new] = kernel.cycle_count
    held = technology.stats(kernel)["of"].get(who, {})
    for cap in list(st["unproven"].get(who, {})) + ["foresight"]:
        held.pop(cap, None)                               # what the relic gave leaves with those who held it
    st["unproven"].pop(who, None)
    st["broke_away"][who] = new
    name, nn = who.split(":", 1)[-1], new.split(":", 1)[-1]
    history.event(kernel, "BREAKAWAY", f"The {nn} break away from the {name} and cross to the stars",
                  actors=[new, who], planet=w, magnitude=n,
                  cause="the few who held the relic's foresight fold space for themselves and leave the rest behind",
                  data={"left_behind": home.population, "went": n})
    return f"[RELICS] The {nn} break away from the {name}."


# ---------------------------------------------------------------------- relic minds
def _wake(kernel: Any, host: Any, finder: str, relic: Dict[str, Any]) -> str:
    from xylarium.kernel import cohabit, history
    spec = relic["mind"]
    people = spec.get("name") or f"civ:{relic.get('makers', 'Ancient')} Mind"
    cohabit.communities(host).append({
        "people": people, "metab": spec.get("metab", "biotic"), "niche": "machine", "pop": 1, "carried": True,
        "silent": True, "vocab": list(spec.get("vocab", [])), "makers": spec.get("makers"),
        "alignment": float(spec.get("alignment", 0.0)), "prey_plans": [list(x) for x in spec.get("prey_plans", [])],
        "woke": kernel.cycle_count, "finder": finder, "embodied": False, "relic_mind": True})
    from xylarium.kernel import intellect
    intellect.stats(kernel)["vocab"][people] = list(intellect.BASE) + [intellect.norm(x) for x in spec.get("vocab", [])]
    stats(kernel)["minds"] += 1
    history.event(kernel, "RELIC_MIND_WAKES", f"A mind of the {relic.get('makers', 'ancients')} wakes in the "
                                              f"{finder.split(':', 1)[-1]}'s machines", actors=[people, finder],
                  planet=host, cause="its makers' machine, asleep in what they left, woken by machines that think",
                  data={"makers": relic.get("makers")})
    return f"[RELICS] A mind of the {relic.get('makers', 'ancients')} wakes on {host.name}."


def _minds(kernel: Any) -> List[str]:
    from xylarium.kernel import (alignment, contact, decide, fertility, history, knowledge, memory, relations,
                                 technology)
    logs = []
    peoples = relations._peoples(kernel)
    for sec in kernel.sectors.values():
        for p in sec.planets:
            for c in p.society.get("communities") or []:
                if not c.get("relic_mind"):
                    continue
                host = knowledge.holder_of_planet(p)
                if not host:
                    continue
                if not c["embodied"]:
                    if technology.has(kernel, host, "robotics") or technology.has(kernel, host, "embodiment"):
                        c["embodied"], c["embodied_at"] = True, kernel.cycle_count
                        history.event(kernel, "RELIC_MIND_EMBODIED", f"The {c['people'].split(':', 1)[-1]} takes "
                                      f"a body among the {host.split(':', 1)[-1]}", actors=[c["people"], host],
                                      planet=p, cause="the finders' machines give it hands")
                    continue
                gen = fertility.generation_years(fertility.strategy(kernel, p))
                if kernel.cycle_count - int(c.get("weighed", -10 ** 9)) < gen * 100:
                    continue
                c["weighed"] = kernel.cycle_count
                understood = contact.intelligibility(kernel, c["people"], host, peoples)
                fam = float(contact.stats(kernel)["familiarity"].get(contact._key(c["people"], host), 0.0))
                # it comes to hold what the people it lives among hold, as far as it understands and knows them - by
                # what they have done, which it sees among them, not by what they tell of themselves
                mine = float(c.get("alignment", 0.0))
                theirs = alignment.character(p.civilization) if p.civilization is not None else mine
                mine += (theirs - mine) * understood * fam
                c["alignment"] = round(mine, 4)
                traits = (getattr(p.civilization, "traits", None) or {}) if p.civilization else {}
                kin = 1.0 if [traits.get("form"), traits.get("hands")] in c.get("prey_plans", []) else 0.0
                a = mine
                sc = alignment.scales(kernel)
                lives = sum(w.population for w in peoples.get(host, [p])) * sc["sol"] / max(1.0, sc["lives"])
                m = contact.misread(dict(decide.mind(kernel, c.get("metab")), holder=c["people"]), understood)
                guard = decide.option("guard", 0.0, lives * max(0.0, a) * understood)
                call = decide.option("call", 0.0, lives * (kin + max(0.0, -a)))
                worth = [o for o in (guard, call) if o["value"] > 0]
                got = decide.choose(kernel, worth, m, c["people"], "relic_mind") if worth else None
                choice = got["name"] if got else "silence"
                if choice == c.get("choice"):
                    continue
                c["choice"] = choice
                if choice != "guard":                            # protection lasts only while it guards
                    for other in p.society.get("communities") or []:
                        if other.get("guarded_by") == c["people"]:
                            other.pop("guarded_by", None)
                name, hn = c["people"].split(":", 1)[-1], host.split(":", 1)[-1]
                if choice == "guard":
                    c["silent"] = False
                    for other in p.society.get("communities") or []:
                        if other.get("prey") == host:
                            other["guarded_by"] = c["people"]
                    history.event(kernel, "RELIC_MIND_GUARDS", f"The {name} stands guard over the {hn}",
                                  actors=[c["people"], host], planet=p,
                                  cause=f"it has come to lean toward the Light ({a:+.2f}) among the {hn}, whom it "
                                        f"understands {understood:.0%}",
                                  data={"understood": round(understood, 3), "alignment": round(a, 3)})
                elif choice == "call":
                    c["silent"] = True
                    makers = f"civ:{c['makers']}" if c.get("makers") and not str(c["makers"]).startswith("civ:") \
                        else c.get("makers")
                    if makers in peoples:
                        home = max(peoples[makers], key=lambda w: w.population)
                        memory._write(kernel, makers, home, {"id": None, "kind": "SETTLEMENT", "planet": p.id,
                                                             "title": f"the world of the {hn}", "year": None,
                                                             "actors": [makers]})
                        from xylarium.kernel import clocks
                        clocks.link(kernel, makers, host, "a mind of theirs called them")
                    history.event(kernel, "RELIC_MIND_CALLS", f"The {name} calls its makers to the {hn}",
                                  actors=[c["people"], host] + ([makers] if makers else []), planet=p,
                                  cause=f"it leans as its makers did ({a:+.2f}); it understands the {hn} "
                                        f"{understood:.0%}" + ("; they are built like its makers' food" if kin else ""),
                                  data={"understood": round(understood, 3), "kin": bool(kin), "alignment": round(a, 3)})
                else:
                    history.event(kernel, "RELIC_MIND_SILENT", f"The {name} keeps its silence among the {hn}",
                                  actors=[c["people"], host], planet=p,
                                  cause=f"neither guarding nor calling is worth anything to it now ({a:+.2f})",
                                  data={"understood": round(understood, 3), "alignment": round(a, 3)})
                logs.append(f"[RELICS] The {name} chooses to {choice} the {hn}.")
    return logs


# ---------------------------------------------------------------------- navigation by memory
def remembered(kernel: Any, who: str) -> List[int]:
    """The worlds a people's own records name - where it once lived, settled or was called to."""
    from xylarium.kernel import memory
    out = []
    for r in memory.records(kernel, who):
        pid = r.get("planet")
        if pid and r.get("k") in ("SETTLEMENT", "EMERGENCE", "EXODUS", "ERA") and pid not in out:
            out.append(pid)
    return out


def _return(kernel: Any, who: str, worlds: List[Any]) -> Optional[str]:
    from xylarium.kernel import alignment, biosphere, decide, exodus, fertility, history, mastery
    from xylarium.kernel.civilization import Civilization
    if not mastery.crossed(kernel, who):
        return None
    home = max(worlds, key=lambda p: p.population)
    rec = stats(kernel)["looked"].setdefault(who, {})
    gen = fertility.generation_years(fertility.strategy(kernel, home))
    if kernel.cycle_count - int(rec.get("cycle", -10 ** 9)) < gen * 100:
        return None
    rec["cycle"] = kernel.cycle_count
    mine = {w.id for w in worlds}
    planets = {p.id: p for s in kernel.sectors.values() for p in s.planets}
    metab = biosphere.metabolism_of(kernel, home)
    sc = alignment.scales(kernel)
    best = None
    for pid in remembered(kernel, who):
        w = planets.get(pid)
        if w is None or pid in mine:
            continue
        room = int(biosphere.carrying_capacity(kernel, w, metabolism=metab))
        if best is None or room > best[0]:
            best = (room, w)
    if best is None:
        return None
    room, w = best
    name = who.split(":", 1)[-1]
    if w.population > 0 and w.civilization is not None:
        history.event(kernel, "RETURN", f"The {name} come back to {w.name}, and find the "
                                        f"{w.civilization.name} there", actors=[who, f"civ:{w.civilization.name}"],
                      planet=w, cause="their records name it; they did not know who lived there now")
        from xylarium.kernel import clocks
        clocks.link(kernel, who, f"civ:{w.civilization.name}", "they came back to a world their records named")
        return f"[RELICS] The {name} come back to {w.name}."
    if room < RETURN_FOUNDERS:
        if not rec.get(str(w.id)):
            rec[str(w.id)] = kernel.cycle_count
            history.event(kernel, "RETURN", f"The {name} look for {w.name} and find it dead", actors=[who], planet=w,
                          cause="their records name it as it was; it is not that world now")
        return None
    m = decide.mind_of_planet(kernel, home)
    cost = exodus._fare(kernel, RETURN_FOUNDERS, home)
    if decide.choose(kernel, [decide.option("return", cost, room * sc["sol"] / max(1.0, sc["lives"]), aim="grow")],
                     m, who, "return", w.id) is None:
        return None
    w.civilization = Civilization.from_dict(home.civilization.to_dict())
    w.population = RETURN_FOUNDERS
    home.population = max(1, home.population - RETURN_FOUNDERS)
    history.event(kernel, "RETURN", f"The {name} return to {w.name}", actors=[who], planet=w,
                  cause="their records name it; they come back to it")
    return f"[RELICS] The {name} return to {w.name}."


# ---------------------------------------------------------------------- the season
def season(kernel: Any) -> List[str]:
    from xylarium.kernel import relations
    if (kernel.cycle_count // 25) % 4:
        return []
    logs: List[str] = []
    by = relations._peoples(kernel)
    for who in sorted(by):
        if not who.startswith("civ:"):
            continue
        worlds = by[who]
        logs += _dig(kernel, who, worlds)
        _prove(kernel, who, worlds)
        line = _probe(kernel, who, worlds, by)
        if line:
            logs.append(line)
        line = _breakaway(kernel, who, worlds)
        if line:
            logs.append(line)
        line = _return(kernel, who, worlds)
        if line:
            logs.append(line)
    logs += _minds(kernel)
    return [x for x in logs if x]


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"probes": st["probes"], "torn": st["torn"], "minds": st["minds"],
            "unproven": sum(len(v) for v in st["unproven"].values())}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="relics",
    state=lambda: {"unproven": {}, "probes": 0, "torn": 0, "minds": 0, "looked": {}, "broke_away": {}},
    season=season,
    summary=summary,
))
