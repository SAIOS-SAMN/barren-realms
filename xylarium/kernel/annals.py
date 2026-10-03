"""
Xylarium annals: a people's long ages, lived at the level of history while the galaxy's deep time runs on.

The engine lives a people year by year on the universal clock, while the galaxy turns on deep time - at the teeming
pace ten million years pass for every clock year. Without the annals a people woken a billion years ago would have
lived only a hundred of its own years: the oldest minds in the galaxy would be its youngest peoples. Each year the
annals close that gap: every people is carried, at the level of history, through the deep years that have passed
since it woke and that it has not yet lived, along the same bridges the full engine carries it across - foraging,
farming, a state, works, yards, the crossing to the stars - each an exponential wait whose mean is that bridge's
span in the people's own generations (measured by tools/bridges.py from the engine itself, scaled by how fast its
minds think: laws.cognition's speed). Peoples also fall: a hazard per generation, measured the same way.

What a people lives in its annals it keeps: its way, its works, its yards, its knowledge, its crossing - and its
people grows to what its world now feeds. Once across, its dominion grows (worlds settled per generation, as far as
its reach), and where two dominions meet, their doctrines (federation.preferred_card of their alignments, which
drift as peoples live) decide between a pact and a war - the GALACTIC_WAR, won by the larger dominion as often as
its share of the two. A fallen people leaves ruins on its homeworld (archaeology.py: the deep strata of an ANCIENT
culture) and its name in the galaxy's chronicle. The galaxy's lore is these annals: every era, crossing, war and
fall, dated in deep time (history.py: ERA, ASCENT, DOMINION, GALACTIC_WAR, FALL).
"""

import math
from typing import Any, Dict, List, Optional

# the bridges' spans in a people's own generations (means of exponential waits), and its hazards per generation
SPANS = {                       # measured by tools/bridges.py on seed 7's first peoples (the engine's own pace),
    "farm": 8.0,                # rounded; crossing beyond its runs is the progenitors' declared expectation
    "state": 4.0,
    "works": 20.0,
    "yards": 60.0,
    "crossed": 400.0,
}
STAGES = ("forage", "farm", "state", "works", "yards", "crossed")
GENETICS_SPAN = 100.0           # generations a people with yards takes to master its own genome (declared: between
                                # yards' 60 and the crossing's 400 - the knowledge of itself it needs to live elsewhere)
EMBODIMENT_SPAN = 200.0         # generations a genome-less people takes to come into a vessel (declared: harder than any
                                # one bridge - it learns the terrestrial dimensions from nothing)
FALL_PER_GENERATION = 2.0e-4    # a one-world people's hazard of falling, per generation (declared: a mean of ~5,000
                                # generations); among the stars it is shared out over the worlds it holds
DOMINION_PER_GENERATION = 0.01  # worlds a crossed people settles per generation, per world it holds (declared)
DOMINION_MAX = 10000            # worlds one dominion can hold together
REACH_KPC_PER_GENERATION = 0.002   # how far a crossed people's reach grows a generation (declared)
WAR_PER_MEETING = 0.5           # chance two dominions of opposed doctrines go to war when they meet
ALIGN_DRIFT = 0.02              # how far a people's alignment wanders a generation, as it lives (declared)
MIN_GENERATIONS = 1.0           # gaps shorter than a generation are left to the full engine


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "annals")


def _stage(kernel: Any, who: str, home: Any) -> str:
    from xylarium.kernel import mastery, sustenance
    if mastery.crossed(kernel, who) and "crossed" in stats(kernel)["of"].get(who, {}).get("passed", []) \
            or who in mastery.stats(kernel).get("crossed", {}):
        return "crossed"
    if sustenance.yards(home):
        return "yards"
    if home.citadel_level >= 1:
        return "works"
    return {"forage": "forage", "farm": "farm"}.get(home.society.get("way"), "state")


def _can_reach_orbit(kernel: Any, who: str, home: Any) -> bool:
    """Whether its world lets it reach orbit at all - by chemistry, or by the atom where its ground has uranium."""
    from xylarium.kernel import technology
    v = technology.chemical_exhaust_kms()
    if technology.orbit_ratio(home, v) <= technology.STRUCTURE:
        return True
    if technology.feasible(kernel, who, "fission", home):
        return technology.orbit_ratio(home, v * technology.FISSION_GAIN) <= technology.STRUCTURE
    return False


def _speed(kernel: Any, home: Any) -> float:
    from xylarium.kernel import decide, knowledge, technology
    who = knowledge.holder_of_planet(home)
    s = max(0.05, float(decide.mind_of_planet(kernel, home).get("speed", 1.0)))
    for cap, gain in (("genetics", technology.GENETIC_GAIN), ("robotics", technology.ROBOTICS_GAIN)):
        if technology.has(kernel, who, cap):
            s *= 1.0 + gain                                  # past the metabolic bound: not waiting on its generations
    return s


CAPS_AT = (("radio", 3), ("computation", 3), ("medicine", 3), ("fission", 4), ("orbit", 4), ("networks", 4),
           ("robotics", 4), ("synthesis", 5))      # genetics is not handed over with yards: it is waited for


def _grant(kernel: Any, who: str, home: Any, idx: int) -> None:
    """What a people finds in its long ages, as its world allows, by the stage it has reached."""
    from xylarium.kernel import technology
    held = technology.stats(kernel)["of"].setdefault(who, {})
    for cap, at in CAPS_AT:
        if idx >= at and cap not in held and technology.feasible(kernel, who, cap, home):
            held[cap] = kernel.cycle_count


def _apply(kernel: Any, who: str, home: Any, stage: str) -> None:
    """Set a people's world to what its annals carried it to."""
    from xylarium.config import DAUGHTER_CITADEL_TIER
    from xylarium.kernel import biosphere, institutions, intellect, mastery, ways
    from xylarium.kernel import crystal as C
    soc = home.society
    idx = STAGES.index(stage)
    if idx >= 1 and soc.get("way") == "forage":
        soc["way"] = "farm"
        soc["crop_z"] = max(float(soc.get("crop_z", 0.0)), math.log(1.0 / ways.TROPHIC_EFFICIENCY))
    if idx >= 2 and soc.get("way") != "state":
        soc["way"] = "state"
        try:
            institutions.found_currency(kernel, home)
        except Exception:
            pass
    if idx >= 3:
        home.citadel_level = max(home.citadel_level, 1 if idx == 3 else home.citadel_level)
    _grant(kernel, who, home, idx)
    if idx >= 4:
        home.citadel_level = max(home.citadel_level, DAUGHTER_CITADEL_TIER)
    if idx >= 5:
        mastery.stats(kernel)["crossed"].setdefault(who, kernel.cycle_count)
        vocab = intellect.stats(kernel)["vocab"].setdefault(who, list(intellect.BASE))
        for c in list(C.STACK_OPS) + list(C.HYPER_OPS):
            if c not in vocab:
                vocab.append(c)
    try:
        ways._refresh(kernel, home)
    except Exception:
        pass
    home.population = max(home.population, int(biosphere.carrying_capacity(kernel, home)))


def _fall(kernel: Any, who: str, worlds: List[Any], epoch: float) -> str:
    from xylarium.kernel import archaeology, history
    import random
    home = max(worlds, key=lambda p: p.population)
    name = who.split(":", 1)[-1]
    rng = random.Random(f"{who}:{epoch}")
    civ = getattr(home, "civilization", None)
    for p in worlds:
        p.ruins = archaeology.bury(p, archaeology._new_ruins(
            name, getattr(civ, "clade", "unknown"), getattr(civ, "metabolism", "biotic"), "ANCIENT",
            6 + STAGES.index(_stage(kernel, who, home)), list(getattr(civ, "discovered_elements", []) or []),
            "the long ages", kernel.cycle_count, 2 + int(rng.random() * 3), p.currency,
            p.treasury + getattr(p, "household_purse", 0), rng))
        p.treasury = 0
        p.household_purse = 0
        p.population = 0
        p.civilization = None
        p.owner_id = None
        p.faction_id = None
    history.event(kernel, "FALL", f"The {name} fall", actors=[who], planet=home,
                  cause=f"{epoch:.3f} Gyr after the Big Bang, at the level of history; its ruins lie on "
                        f"{len(worlds)} world{'s' if len(worlds) != 1 else ''}")
    return f"[ANNALS] The {name} fall; their ruins lie on {home.name}."


def season(kernel: Any) -> List[str]:
    """Once a year every people lives the deep years it has not yet lived."""
    from xylarium.kernel import cosmos, fertility, history, knowledge, scheduler, sustenance, syntropy
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    now = cosmos.deep_gyr(kernel)
    logs: List[str] = []
    peoples = syntropy._peoples(kernel)
    for who in sorted(peoples):
        worlds = peoples[who]
        home = max(worlds, key=lambda p: p.population)
        arisen = home.society.get("arisen") or {}
        if "epoch" not in arisen:
            continue
        rec = st["of"].setdefault(who, {"advanced": 0.0, "passed": [], "dominion": len(worlds), "reach": 0.0})
        lived = (kernel.cycle_count - int(arisen.get("cycle", kernel.cycle_count))) / 100.0
        deficit = (now - float(arisen["epoch"])) * 1e9 - lived - rec["advanced"]
        gen = max(1.0, fertility.generation_of(kernel, home))
        gens = deficit / gen
        if gens < MIN_GENERATIONS:
            continue
        rec["advanced"] += deficit
        rng = scheduler.rng(kernel, "annals", who, kernel.cycle_count)
        speed = _speed(kernel, home)
        stage = _stage(kernel, who, home)
        t = 0.0                                               # generations lived in this stretch
        epoch_of = lambda tt: now - (gens - tt) * gen / 1e9   # noqa: E731
        fell = None
        while t < gens:
            nxt = STAGES.index(stage) + 1
            if nxt >= len(STAGES):
                # among the stars a people falls only if all its worlds do: its hazard is the one-world hazard over
                # its dominion, which grows as it settles - H = f / (W0 g) (1 - e^-g T) over what is left of T
                left = gens - t
                g, w0 = DOMINION_PER_GENERATION, max(1, rec["dominion"])
                hazard = FALL_PER_GENERATION / (w0 * g) * (1.0 - math.exp(-g * left))
                if rng.expovariate(1.0) < hazard:
                    fell = t + left * rng.random()
                break
            from xylarium.kernel import mastery as _mastery, technology as _tech
            if STAGES[nxt] == "works" and not _tech.embodied(kernel, who, home):
                wait_body = rng.expovariate(speed / EMBODIMENT_SPAN)
                wait_fall = rng.expovariate(FALL_PER_GENERATION)
                if wait_fall <= wait_body and t + wait_fall < gens:
                    fell = t + wait_fall
                    break
                if t + wait_body >= gens:
                    break
                t += wait_body
                _tech.stats(kernel)["of"].setdefault(who, {})["embodiment"] = kernel.cycle_count
                continue                                      # it has hands now; its works can begin
            if STAGES[nxt] == "yards" and not _can_reach_orbit(kernel, who, home):
                nxt_blocked = True                            # its gravity holds it: it lives on, on its world
            elif STAGES[nxt] == "crossed" and not _mastery.genome_ready(kernel, who, worlds):
                if _tech.genomeless(kernel, home):
                    nxt_blocked = True                        # its vessel came with its works; nothing else stands
                else:
                    wait_gene = rng.expovariate(speed / GENETICS_SPAN)
                    wait_fall = rng.expovariate(FALL_PER_GENERATION)
                    if wait_fall <= wait_gene and t + wait_fall < gens:
                        fell = t + wait_fall
                        break
                    if t + wait_gene >= gens:
                        break
                    t += wait_gene
                    _tech.stats(kernel)["of"].setdefault(who, {})["genetics"] = kernel.cycle_count
                    continue                                  # it can rewrite itself now; the crossing can come
            else:
                nxt_blocked = False
            wait_up = float("inf") if nxt_blocked else rng.expovariate(speed / SPANS[STAGES[nxt]])
            wait_fall = rng.expovariate(FALL_PER_GENERATION)
            if nxt_blocked and t + wait_fall >= gens:
                break
            if wait_fall <= wait_up and t + wait_fall < gens:
                fell = t + wait_fall
                break
            if t + wait_up >= gens:
                break
            t += wait_up
            stage = STAGES[nxt]
            _grant(kernel, who, home, nxt)                    # what that stage brings, it holds from then on
            rec["passed"].append(stage)
            kind = "ASCENT" if stage == "crossed" else "ERA"
            text = {"farm": "takes up farming", "state": "founds a state", "works": "raises its first great works",
                    "yards": "builds yards that can launch to orbit", "crossed": "folds space and crosses to the stars"}
            history.event(kernel, kind, f"The {who.split(':', 1)[-1]} {text[stage]}", actors=[who], planet=home,
                          cause=f"at the level of history, {epoch_of(t):.4f} Gyr after the Big Bang",
                          data={"epoch": round(epoch_of(t), 6), "stage": stage})
        # alignment wanders as a people lives its ages
        civ = getattr(home, "civilization", None)
        if civ is not None:
            civ.alignment = round(max(-1.0, min(1.0, float(civ.alignment or 0.0)
                                                + rng.gauss(0.0, ALIGN_DRIFT * math.sqrt(min(gens, 1e4))))), 4)
        if fell is not None:
            logs.append(_fall(kernel, who, worlds, epoch_of(fell)))
            st["falls"] += 1
            continue
        if stage == "crossed":
            since = max(0.0, gens - (t if "crossed" in rec["passed"][-1:] else 0.0))
            rec["dominion"] = int(min(DOMINION_MAX, rec["dominion"] * math.exp(min(50.0, DOMINION_PER_GENERATION * since))))
            rec["reach"] = min(40.0, rec["reach"] + REACH_KPC_PER_GENERATION * since)
        _apply(kernel, who, home, stage)
        for d in knowledge.DOMAINS:                           # what it knows has grown with its ages
            have = knowledge.experience(kernel, who, d)
            if have > 0:
                knowledge.learn(kernel, who, d, have * min(10.0, gens / 100.0), why="annals")
    logs += _meetings(kernel, now)
    return logs


def _meetings(kernel: Any, now: float) -> List[str]:
    """Where two crossed dominions' reaches meet: a pact or, between opposed doctrines, a war."""
    from xylarium.config import POLICY_ORDER
    from xylarium.kernel import cosmos, federation, history, scheduler, syntropy
    st = stats(kernel)
    peoples = syntropy._peoples(kernel)
    crossed = [w for w, r in st["of"].items() if w in peoples and "crossed" in r["passed"]]
    logs = []
    for i, a in enumerate(crossed):
        for b in crossed[i + 1:]:
            key = f"{a}|{b}"
            if key in st["met"]:
                continue
            ha = max(peoples[a], key=lambda p: p.population)
            hb = max(peoples[b], key=lambda p: p.population)
            d = cosmos.distance_kpc(kernel, ha.sector_id, hb.sector_id)
            if d is None or d > st["of"][a]["reach"] + st["of"][b]["reach"]:
                continue
            st["met"][key] = kernel.cycle_count
            ca = federation.preferred_card(float(getattr(ha.civilization, "alignment", 0.0) or 0.0))
            cb = federation.preferred_card(float(getattr(hb.civilization, "alignment", 0.0) or 0.0))
            rng = scheduler.rng(kernel, "meeting", a, b)
            opposed = abs(POLICY_ORDER.index(ca) - POLICY_ORDER.index(cb)) >= 2 or "DELTA" in (ca, cb)
            na, nb = a.split(":", 1)[-1], b.split(":", 1)[-1]
            if opposed and rng.random() < WAR_PER_MEETING:
                da, db = st["of"][a]["dominion"], st["of"][b]["dominion"]
                win, lose = (a, b) if rng.random() < da / max(1, da + db) else (b, a)
                st["of"][lose]["dominion"] = max(1, st["of"][lose]["dominion"] // 2)
                st["of"][win]["dominion"] += st["of"][lose]["dominion"] // 2
                st["wars"] += 1
                history.event(kernel, "GALACTIC_WAR", f"War between the {na} and the {nb}", actors=[a, b],
                              cause=f"their dominions met {d * 3261.56:,.0f} light years apart; "
                                    f"{POLICY_CARDS_NAME(ca)} against {POLICY_CARDS_NAME(cb)}",
                              text=f"The {win.split(':', 1)[-1]} prevailed; the {lose.split(':', 1)[-1]} lost half "
                                   f"their dominion.", data={"winner": win, "loser": lose})
                logs.append(f"[ANNALS] War between the {na} and the {nb}: the {win.split(':', 1)[-1]} prevail.")
            elif opposed:
                history.event(kernel, "DOMINION", f"The {na} and the {nb} meet among the stars", actors=[a, b],
                              cause=f"{POLICY_CARDS_NAME(ca)} against {POLICY_CARDS_NAME(cb)}: an uneasy truce, "
                                    f"no pact")
            else:
                # peoples whose doctrines agree make a pact of the ages: the bloc a federation can be founded from
                from xylarium.kernel import relations
                relations.pacts(kernel)[relations._pair(a, b)] = {"since": kernel.cycle_count, "annals": True}
                st["pacts"] += 1
                history.event(kernel, "DOMINION", f"The {na} and the {nb} meet among the stars", actors=[a, b],
                              cause=f"{POLICY_CARDS_NAME(ca)} and {POLICY_CARDS_NAME(cb)}: they keep the peace and "
                                    f"bind themselves by a pact")
    return logs


def POLICY_CARDS_NAME(card: str) -> str:
    from xylarium.config import POLICY_CARDS
    return POLICY_CARDS.get(card, {}).get("name", card)


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    crossed = sum(1 for r in st["of"].values() if "crossed" in r["passed"])
    return {"peoples": len(st["of"]), "crossed": crossed, "falls": st["falls"], "wars": st["wars"],
            "pacts": st.get("pacts", 0),
            "dominion_worlds": sum(r["dominion"] for r in st["of"].values() if "crossed" in r["passed"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="annals", state=lambda: {"of": {}, "met": {}, "falls": 0, "wars": 0, "pacts": 0},
                             season=season, summary=summary))
