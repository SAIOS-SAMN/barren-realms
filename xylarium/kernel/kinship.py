"""
Xylarium kinship: what happens to a people when its food turns out to be - or to become - a mind.

Every people eats the life of its world: the creatures of its homeworld's tree of life, and the native life of the
worlds it lives on. Two things can make that food a question:

  RESEMBLANCE  it meets a mind of its own chemistry built like something it eats - the body plans of its prey are
               its homeworld's (drawn once, with the world's own life; prey_plans), and a stranger shaped like them
               is recognised as kin of its food.
  DESCENT      a mind wakes on a world whose life it once ate (the diet ledger: every world it lived on whose life
               it harvested) - the chicken planet it left, come back sentient.

Nothing decides what a people does about it. Its council weighs it like any choice (decide.choose), through its
own mind:

  ABSTAIN   swear off that food - the share of its diet it was (forsworn: its land feeds fewer), cheaper where it can
            make food to order (synthesis); worth the lives of the mind it spares, as much as it values strangers'
            lives (its alignment toward the Light)
  DENY      "they are not what we ate" - its creed holds the food at no cost to its conscience; worth what its
            dogma makes of keeping its table; its dogma hardens
  CONTINUE  eat on - worth the food, as far as it does not value them; its alignment drifts toward the Dark with
            the lives it treats as food, and the other people remembers (KIN_EATEN: its model of the eater reads it
            as harm - strategy.hostility)
  GUARD     take them under its protection, as repayment - worth their lives and how well it understands them;
            costs the food and a guardian's care

A council divided between its best two choices records its schism. Alignment comes from consequences, not
judgement: eating something before it was a mind costs nothing; what a people does once it knows is what it is.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

PREY_PLANS = 3                  # body plans a people's homeworld feeds it on (declared: a food web's handful of staples)
FORMS = ("walking", "swimming", "low and many-limbed", "tall and slender", "drifting")
HANDS = ("grasping limbs", "tendrils", "mouths and tongues", "jointed palps")
MIND_EATEN = 2.0                # a mind eaten is a life ended and a mind consumed: weighed as two lives lost (the
                                # darkest act a people can do - declared)
SCHISM_SHARE = 0.8              # a second choice this close to the first divides the council (declared)


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "kinship")


def _home(worlds: List[Any]) -> Any:
    return max(worlds, key=lambda p: p.population)


def _traits(planet: Any) -> Dict[str, Any]:
    civ = getattr(planet, "civilization", None)
    return dict(getattr(civ, "traits", None) or {}) if civ is not None else {}


def prey_plans(kernel: Any, holder: str, home: Any) -> List[Tuple[str, str, str]]:
    """The body plans a people's homeworld feeds it on: its own medium's creatures, never its own shape."""
    from xylarium.kernel import scheduler
    t = _traits(home)
    solvent = t.get("solvent", "H2O")
    own = (t.get("form"), t.get("hands"))
    rng = scheduler.rng(kernel, "prey", holder)
    plans = [(f, h) for f in FORMS for h in HANDS if (f, h) != own]
    rng.shuffle(plans)
    return [(solvent, f, h) for f, h in plans[:PREY_PLANS]]


def _record_diet(kernel: Any, peoples: Dict[str, List[Any]]) -> None:
    """Every world a people lives on, other than its home, whose own life it harvests."""
    from xylarium.kernel import creation, cosmos, lifeline
    ate = stats(kernel)["ate"]
    seed = cosmos.cosmos_seed(kernel)
    for who, worlds in peoples.items():
        home = _home(worlds)
        for w in worlds:
            if w is home:
                continue
            loc = lifeline.locate(kernel, w)
            if loc is None:
                continue
            (i, j), k, n = loc
            key = lifeline.key((i, j), k, n)
            if key in ate.get(who, {}):
                continue
            slot = creation.cell(seed, i, j)[k]
            lins = creation.system_life(seed, i, j, k, slot) if "worlds" in slot else []
            lin = lins[n] if n < len(lins) else None
            if lin and lin["steps"] and lin["steps"][0] <= cosmos.deep_gyr(kernel):
                ate.setdefault(who, {})[key] = kernel.cycle_count


def on_arise(kernel: Any, planet: Any) -> None:
    """A mind has woken: did anyone eat its world's life before it did?"""
    from xylarium.kernel import knowledge, lifeline
    if "kinship" not in getattr(kernel, "state", {}):
        return
    loc = lifeline.locate(kernel, planet)
    if loc is None:
        return
    key = lifeline.key(*loc)
    young = knowledge.holder_of_planet(planet)
    for eater, keys in stats(kernel)["ate"].items():
        if key in keys and eater != young:
            stats(kernel)["pending"].append([eater, young, "descent"])


def _resemblances(kernel: Any, peoples: Dict[str, List[Any]]) -> List[List[str]]:
    from xylarium.kernel import contact
    met = contact.contacts(kernel, peoples)
    out = []
    for a, others in met.items():
        if a not in peoples:
            continue
        prey = set(prey_plans(kernel, a, _home(peoples[a])))
        for b in others:
            if b not in peoples:
                continue
            t = _traits(_home(peoples[b]))
            if (t.get("solvent"), t.get("form"), t.get("hands")) in prey:
                out.append([a, b, "resemblance"])
    return out


def _respond(kernel: Any, eater: str, young: str, kind: str, peoples: Dict[str, List[Any]]) -> Optional[str]:
    from xylarium.kernel import alignment, biosphere, contact, decide, history, sustenance, technology
    worlds, theirs = peoples.get(eater), peoples.get(young)
    if not worlds or not theirs:
        return None
    home = _home(worlds)
    civ = getattr(home, "civilization", None)
    if civ is None:
        return None
    sc = alignment.scales(kernel)
    life = sc["sol"] / max(1.0, sc["lives"])
    n_young = sum(p.population for p in theirs)
    k_all = sum(biosphere.carrying_capacity(kernel, p) for p in worlds)
    share = 1.0 / PREY_PLANS if kind == "resemblance" else 0.0       # a staple; a world it has left feeds it no more
    if technology.has(kernel, eater, "synthesis"):
        share /= 1.0 + technology.SYNTHESIS_GAIN                     # food made to order stands in for it
    food = share * k_all * life
    light = max(0.0, float(civ.alignment or 0.0))
    dogma = float(getattr(civ, "dogma", 0.0) or 0.0)
    known = contact.intelligibility(kernel, eater, young, peoples)
    spared = n_young * life
    opts = [decide.option("abstain", food, light * spared, aim="hold"),
            decide.option("deny", 0.0, dogma * food),
            decide.option("continue", 0.0, (1.0 - light) * food),
            decide.option("guard", food + 0.1 * spared, light * spared * (1.0 + known), aim="secure")]
    m = decide.mind_of_planet(kernel, home)
    pick = decide.choose(kernel, opts, m, eater, young, kind, "kin")
    if pick is None:
        pick = opts[2]
    nets = sorted((o["value"] - o["cost"] for o in opts), reverse=True)
    name = pick["name"]
    st = stats(kernel)
    st["responses"][name] = st["responses"].get(name, 0) + 1
    title = {"abstain": "swear off the food that was kin to {y}", "deny": "hold that {y} are not what they ate",
             "continue": "eat on, though {y} are kin of their food", "guard": "take {y} under their protection"}
    e_name, y_name = eater.split(":", 1)[-1], young.split(":", 1)[-1]
    cause = ("a mind of their own chemistry, built like what they eat" if kind == "resemblance"
             else "the world whose life they once ate has raised a mind")
    if name == "abstain":
        home.society["forsworn"] = round(min(0.9, float(home.society.get("forsworn", 0.0)) + share), 4)
        sustenance.flow_civ(home, light=n_young * share)
    elif name == "deny":
        civ.dogma = round(min(1.0, dogma + 0.1 * (1.0 - dogma)), 4)
    elif name == "continue":
        sustenance.flow_civ(home, dark=n_young * max(share, 0.1) * known)
        from xylarium.kernel import reputation
        reputation.witness(kernel, young, eater, dark=n_young * max(share, 0.1) * known)
        history.event(kernel, "KIN_EATEN", f"The {y_name} learn the {e_name} eat their kin", actors=[eater, young],
                      planet=_home(theirs), cause=cause)
    elif name == "guard":
        home.society["forsworn"] = round(min(0.9, float(home.society.get("forsworn", 0.0)) + share), 4)
        sustenance.flow_civ(home, light=n_young)
        from xylarium.kernel import reputation
        reputation.witness(kernel, young, eater, light=n_young)
    history.event(kernel, "KINSHIP", f"The {e_name} {title[name].format(y=y_name)}", actors=[eater, young],
                  planet=home, cause=cause, data={"kind": kind, "choice": name})
    if len(nets) > 1 and nets[0] > 0 and nets[1] >= SCHISM_SHARE * nets[0]:
        st["schisms"] += 1
        history.event(kernel, "SCHISM", f"The {e_name} are divided over the {y_name}", actors=[eater, young],
                      planet=home, cause="their council could not agree what was owed to kin of their food")
    return f"[KINSHIP] The {e_name} {title[name].format(y=y_name)}."


def season(kernel: Any) -> List[str]:
    """Once a year: what each people has eaten, and whom it now recognises."""
    from xylarium.kernel import cosmos, relations
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    peoples = relations._peoples(kernel)
    _record_diet(kernel, peoples)
    todo = st["pending"] + _resemblances(kernel, peoples)
    st["pending"] = []
    logs = []
    for eater, young, kind in todo:
        key = f"{eater}|{young}|{kind}"
        if key in st["recognised"]:
            continue
        st["recognised"][key] = kernel.cycle_count
        line = _respond(kernel, eater, young, kind, peoples)
        if line:
            logs.append(line)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"recognised": len(st["recognised"]), "responses": dict(st["responses"]), "schisms": st["schisms"],
            "worlds_eaten": sum(len(v) for v in st["ate"].values())}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="kinship", state=lambda: {"ate": {}, "pending": [], "recognised": {},
                                                            "responses": {}, "schisms": 0},
                             season=season, summary=summary))
