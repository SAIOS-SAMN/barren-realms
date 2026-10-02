"""
Xylarium society: what a people believes, how it holds together, how it splits, and what it makes - before and after
it reaches the stars. These are the institutions a people carries into space with it.

GAUGES. Four leanings of a people's common life, each 0..1, read by everything below. A steward sets them; a
people left to its council keeps them where its circumstances push them.

  temple     how much of its common effort goes to rites rather than inquiry
  levy       the share of its adults under arms (they guard; they do not work)
  openness   how much it takes from strangers: their goods, their words, their ideas
  commerce   how free its markets are to make trades of their own (guilds)

BELIEF. A people's dogma (its creed's hold) is pulled toward its temple gauge over a generation; it is raised by
blows it cannot explain - famine, blight, bombardment, a sky that fails - as a generation's experience of them
(a season's blow counts a season against a generation), in proportion to how little it knows of information
(laws.mastery: what it can explain); it is worn down as its knowledge grows (each newly explained thing
takes its share of belief) and by the strangers' ideas its openness lets in (its familiarity with its contacts).
Dogma impedes inquiry (knowledge.impedance) and, past a priesthood's line, brands it heresy. Each first blow of a
kind becomes a MYTH: what the people tells of it, in the terms of its own sky (its star's colour, its moons).

STRESS. Turchin's structural-demographic reading of a state: mass mobilisation potential (immiseration: the share
of its need its harvests do not meet, times how crowded it is against its land), times what fails to legitimise
its order (neither belief nor prosperity holds it), times its fiscal distress (its morale, which falls with
arrears and hunger). The share of a people that would rise is that product. When it exceeds the share under arms,
the people turns on itself: CIVIL STRIFE - those who fight die in proportion to the clash, the treasury is
plundered, the creed is overturned (the temple gauge flips) - and a generation passes before the exhausted can rise
again. On a shared world, two peoples in competition for one niche fight when the host is pressed against its
land: the host's armed share drives the community out of its share of the room.

GUILDS. Adam Smith: the division of labour is limited by the extent of the market. A people's trades number as the
log of its market (its numbers times the surplus its harvests leave, opened by its commerce gauge); every trade is
practised, and practice teaches materials (crafts) as gathering teaches biology (ways.py). The guilds are what a
people takes into the lanes as firms.
"""

import math
from typing import Any, Dict, List, Optional

from xylarium.kernel import laws

GAUGES = ("temple", "levy", "openness", "commerce")
SOLDIERS_PER_TROOP = 100        # a garrison troop counts a hundred under arms (the colony's garrison_troops)


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "society")


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def gauges(planet: Any) -> Dict[str, float]:
    g = planet.society.setdefault("gauges", {})
    for k in GAUGES:
        g.setdefault(k, 0.0 if k in ("temple", "levy") else 0.5)
    return g


def set_gauge(planet: Any, key: str, value: float) -> None:
    """A steward's hand on its people's institutions (the council no longer moves what the steward has set)."""
    if key not in GAUGES:
        raise KeyError(key)
    gauges(planet)[key] = round(max(0.0, min(1.0, float(value))), 3)
    planet.society.setdefault("gauges_set", [])
    if key not in planet.society["gauges_set"]:
        planet.society["gauges_set"].append(key)


def output_factor(planet: Any) -> float:
    """The share of a people's work done by those not under arms."""
    g = (planet.society or {}).get("gauges")
    return 1.0 - float(g.get("levy", 0.0)) if g else 1.0


def openness(planet: Any) -> float:
    g = (getattr(planet, "society", None) or {}).get("gauges")
    return float(g.get("openness", 0.5)) if g else 0.5


def _peoples(kernel: Any) -> List[Any]:
    return [p for s in kernel.sectors.values() for p in s.planets
            if p.population > 0 and getattr(p, "civilization", None) is not None and not getattr(p, "natives", None)]


def _info(kernel: Any, planet: Any) -> float:
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge
    return laws.mastery(knowledge.experience(kernel, knowledge.holder_of_planet(planet), "information"), KNOWLEDGE_UNIT)


# ---------------------------------------------------------------------- belief and myth
SHOCKS = ("famine", "blight", "bombarded")


def _shocks(kernel: Any, planet: Any) -> Dict[str, float]:
    """This season's blows, each as the share of the people it struck."""
    soc = planet.society
    now, q = kernel.cycle_count, _quarter()
    out = {k: 1.0 for k in SHOCKS if now - int(soc.get(f"{k}_cycle", -10 ** 9)) < q}
    ss = float(soc.get("self_sufficiency", 1.0) or 1.0)
    if ss < 1.0:
        out["famine"] = max(out.get("famine", 0.0), 1.0 - ss)
    if float(soc.get("dynamo", 1.0)) < 0.5:
        out["sky"] = 1.0 - float(soc.get("atmosphere", 1.0))      # the sky failing: its air taken by the stars' wind
    return out


def _sky(kernel: Any, planet: Any) -> Dict[str, Any]:
    """What a people sees overhead: its star's colour (from its mass) and how many moons it has."""
    from xylarium.kernel import physics
    sec = kernel.sectors.get(planet.sector_id)
    colour = "pale"
    try:
        m = float(physics.star(sec)["m"])
        colour = "red" if m < 0.6 else ("orange" if m < 0.9 else ("yellow" if m < 1.2 else "white"))
    except Exception:
        pass
    moons = sum(1 for p in (sec.planets if sec else []) if getattr(p, "moon_of", None) == planet.id)
    return {"colour": colour, "moons": moons}


_MYTH = {
    "famine": "the {colour} sun turned its face away, and the fields gave nothing; {moons_say}",
    "blight": "a sickness walked out of the crowded places, and the {colour} sun did not stop it; {moons_say}",
    "bombarded": "fire fell from the dark between the stars, and {moons_say}",
    "sky": "the sky itself thinned, and the {colour} sun's breath reached the ground; {moons_say}",
    "strife": "brother rose against brother under the {colour} sun; {moons_say}",
}


def _myth(kernel: Any, planet: Any, kind: str, told: Optional[str] = None, source: Optional[Dict[str, Any]] = None
          ) -> Optional[Dict[str, Any]]:
    """A people's myth: told in the terms of its own sky, and built on the myth before it (each retelling carries
    the last); written to the ledger with what it remembers (`source`) and what it builds on."""
    soc = planet.society
    myths = soc.setdefault("myths", [])
    if source is None and any(m["kind"] == kind for m in myths):
        return None
    sky = _sky(kernel, planet)
    moons_say = ("the moon looked on and said nothing" if sky["moons"] == 1 else
                 f"its {sky['moons']} moons looked on and said nothing" if sky["moons"] > 1 else
                 "and there was no moon to witness it")
    text = told or _MYTH.get(kind, "something happened that no one could explain; {moons_say}")
    text = text.format(colour=sky["colour"], moons_say=moons_say)
    prev = myths[-1] if myths else None
    if prev is not None:
        text += f" - as it was when {prev['text'].split(';')[0].split(' - ')[0]}"
    people = getattr(planet.civilization, "name", planet.name)
    from xylarium.kernel import history, knowledge, primordial
    refs = [x for x in ((source or {}).get("id"), (prev or {}).get("id")) if x]
    rec = history.event(kernel, "MYTH", f"The {people} tell how {text.split(',')[0]}",
                        actors=[knowledge.holder_of_planet(planet)], planet=planet, refs=refs,
                        text=f"The {people} of {planet.name} say that {text}.", data={"myth": kind})
    myth = {"id": rec.get("id"), "kind": kind, "year": kernel.cycle_count // 100, "text": text,
            "builds_on": (prev or {}).get("id"), "remembers": (source or {}).get("id")}
    myths.append(myth)
    del myths[:-40]
    chron = getattr(kernel, "chronicle", None)
    if chron is not None:
        chron.record(kernel, "MYTH", planet.id, people, f"The {people} tell how {text.split(',')[0]}",
                     f"The {people} of {planet.name} say that {text}.", sector_id=planet.sector_id,
                     tags=["myth", kind])
    primordial.first(kernel, "first_myth", f"{people}: {kind}")
    return myth


LEGENDARY = {"WAR": "the {them} came for their {what} under the {colour} sun, and they fought",
             "STRIFE": "brother rose against brother under the {colour} sun, and the old creed fell",
             "CONQUEST": "strangers from the sky took their world, and the {colour} sun did not stop them",
             "REVOLT": "they threw the strangers back into the sky",
             "CONTACT": "the {them} first came out of the dark, speaking in a tongue no one knew",
             "SUBJUGATION": "the {them} held them by force, and they paid",
             "REBELLION": "they broke the {them}'s hold",
             "FARMING": "the first seed was put into the ground",
             "STATEHOOD": "the first granary was raised and the first tax was taken",
             "EMERGENCE": "they first looked up, and the {colour} sun looked back"}


def _legends(kernel: Any, planet: Any, gen_years: float) -> None:
    """The gravest thing a generation ago that no one has yet made a legend of, becomes one."""
    from xylarium.kernel import history, knowledge
    holder = knowledge.holder_of_planet(planet)
    soc = planet.society
    done = set(soc.setdefault("legended", []))
    horizon = kernel.cycle_count - gen_years * 100
    old = [e for e in history.of_people(kernel, holder)
           if e["kind"] in LEGENDARY and e["cycle"] <= horizon and e["id"] not in done]
    if not old:
        return
    e = max(old, key=lambda x: (float(x.get("magnitude") or 0), -x["cycle"]))
    them = next((a for a in e["actors"] if a != holder), "strangers").split(":", 1)[-1]
    what = (e.get("cause") or "").split(":")[-1].strip().split(" ")[0] or "harvests"
    told = LEGENDARY[e["kind"]].replace("{them}", them).replace("{what}", what) + "; {moons_say}"
    _myth(kernel, planet, f"legend:{e['kind'].lower()}", told=told, source=e)
    soc["legended"] = (list(done) + [e["id"]])[-200:]


def _believe(kernel: Any, planet: Any, gen_years: float) -> None:
    from xylarium.kernel import contact, knowledge
    civ = planet.civilization
    soc = planet.society
    g = gauges(planet)
    years = _quarter() / 100.0
    d = float(getattr(civ, "dogma", 0.0) or 0.0)
    info = _info(kernel, planet)
    explained = max(0.0, info - float(soc.get("info_seen", info)))            # what it newly understands
    soc["info_seen"] = round(info, 6)
    shocks = _shocks(kernel, planet)
    for kind in shocks:
        _myth(kernel, planet, kind)
    unexplained = min(1.0, sum(shocks.values())) * (1.0 - info)
    fam = contact.stats(kernel)["familiarity"]
    holder = knowledge.holder_of_planet(planet)
    mine = [v for k, v in fam.items() if holder and holder in k.split("|")]
    exposure = (sum(mine) / len(mine)) if mine else 0.0
    target = g["temple"] * (1.0 - g["openness"] * exposure)                  # strangers' ideas loosen the creed
    season = min(1.0, years / max(1e-6, gen_years))                          # a season, against a generation
    d += (target - d) * season                                               # rites pull it over a generation
    d += unexplained * season * (1.0 - d)                                    # a generation of blows it cannot explain
    d -= explained * d                                                       # what it comes to understand, it stops believing
    civ.dogma = round(max(0.0, min(1.0, d)), 4)


# ---------------------------------------------------------------------- stress and strife
def stress(kernel: Any, planet: Any) -> Dict[str, float]:
    """Turchin's reading: the share of the people that would rise."""
    from xylarium.kernel import biosphere, ways
    soc = planet.society
    ss = float(soc.get("self_sufficiency", 1.0) or 1.0)
    crowd = min(1.0, planet.population / max(1, biosphere.carrying_capacity(kernel, planet)))
    mmp = max(0.0, 1.0 - ss) * crowd
    dogma = float(getattr(planet.civilization, "dogma", 0.0) or 0.0)
    legitimacy = max(dogma, min(1.0, ss))
    emp = 1.0 - legitimacy
    sfd = 1.0 - max(0.0, min(100.0, float(planet.morale))) / 100.0
    rising = mmp * emp * (0.5 + 0.5 * sfd) if not ways.stateless(planet) else 0.0
    return {"immiseration": round(mmp, 4), "illegitimacy": round(emp, 4), "distress": round(sfd, 4),
            "rising": round(rising, 4)}


def _strife(kernel: Any, planet: Any, s: Dict[str, float], gen_years: float) -> Optional[str]:
    soc = planet.society
    g = gauges(planet)
    if s["rising"] <= g["levy"]:
        return None
    if kernel.cycle_count - int(soc.get("strife_cycle", -10 ** 9)) < gen_years * 100:
        return None                                         # the exhausted generation does not rise again
    from xylarium.kernel import alignment, primordial, sustenance
    clash = min(s["rising"], max(g["levy"], 0.01))
    dead = int(planet.population * clash * 0.5)
    planet.population = max(1, planet.population - dead)
    loot = planet.treasury // 2                             # the vaults are plundered: the coin goes to the mobs'
    planet.treasury -= loot                                 # purses (it stays in the world - conserved)
    planet.household_purse = getattr(planet, "household_purse", 0) + loot
    planet.morale = max(10, planet.morale - 20)
    g["temple"] = round(1.0 - g["temple"], 3)               # the creed is overturned
    soc["strife_cycle"] = kernel.cycle_count
    st = stats(kernel)
    st["strife"] += 1
    if dead:
        sustenance._shift_civ(planet, alignment.measure(kernel, lives_lost=dead))
    people = getattr(planet.civilization, "name", planet.name)
    from xylarium.kernel import history, knowledge
    history.event(kernel, "STRIFE", f"The {people} turn on themselves", actors=[knowledge.holder_of_planet(planet)],
                  planet=planet, magnitude=dead, cause=f"{s['rising']:.0%} would rise, {g['levy']:.0%} under arms "
                  f"(hunger {s['immiseration']:.0%}, unheld order {s['illegitimacy']:.0%})")
    _myth(kernel, planet, "strife")
    primordial.first(kernel, "first_civil_strife", people)
    return (f"[SOCIETY] The {people} of {planet.name} turn on themselves: {dead:,} dead, the vaults plundered, "
            f"the creed overturned.")


def _niche_wars(kernel: Any, planet: Any) -> Optional[str]:
    """A host pressed against its land drives a competing community out of its share of the room."""
    from xylarium.kernel import alignment, biosphere, cohabit, sustenance
    cs = cohabit.communities(planet)
    if not cs:
        return None
    crowd = planet.population / max(1, biosphere.carrying_capacity(kernel, planet))
    if crowd < 1.0:
        return None
    levy = gauges(planet)["levy"]
    lines = []
    for c in cs:
        if c.get("kind") != "competition" or levy <= 0:
            continue
        driven = int(c["pop"] * min(1.0, levy * crowd))
        if driven <= 0:
            continue
        c["pop"] -= driven
        stats(kernel)["driven_out"] += driven
        sustenance._shift_civ(planet, alignment.measure(kernel, lives_lost=driven))
        lines.append(f"[SOCIETY] {planet.name}'s people drive {driven:,} of the {c['people'].split(':')[-1]} "
                     f"out of the {c['niche']} they shared.")
    return "\n".join(lines) or None


# ---------------------------------------------------------------------- guilds
def trades(kernel: Any, planet: Any) -> int:
    from xylarium.kernel import ways
    surplus = ways.surplus(kernel, planet) if "way" in planet.society else 1.0 - ways.TROPHIC_EFFICIENCY
    market = planet.population * surplus * gauges(planet)["commerce"]
    return int(math.log2(1.0 + market / 1000.0))


def _guilds(kernel: Any, planet: Any) -> None:
    """Every trade is practised, and practice teaches crafts (materials), as gathering teaches biology."""
    from xylarium.kernel import biosphere, genome, knowledge
    n = trades(kernel, planet)
    planet.society["trades"] = n
    if n <= 0:
        return
    depth = laws.cognition(biosphere.metabolism_of(kernel, planet), genome.temperature_factor(planet))["depth"]
    share = n / (1.0 + n)                                   # the share of a people in its trades
    units = planet.population / 1000.0 * depth * share * _quarter() / 100.0
    knowledge.learn(kernel, knowledge.holder_of_planet(planet), "materials", units, "crafts")


# ---------------------------------------------------------------------- the council's gauges
def _council(kernel: Any, planet: Any) -> None:
    """What a people left to its council does with its gauges: arms itself as far as it is attacked (a levy that
    decays as the attacks stop), keeps its rites as far as its creed is not yet explained."""
    soc = planet.society
    held = set(soc.get("gauges_set") or [])
    g = gauges(planet)
    now = kernel.cycle_count
    attacked = sum(1 for k in ("bombarded_cycle", "raided_cycle") if now - int(soc.get(k, -10 ** 9)) < _quarter()) \
        + (1 if getattr(planet, "siege", None) else 0)
    if "levy" not in held:                                  # arms answer attacks, not hunger
        g["levy"] = round(min(0.3, 0.8 * g["levy"] + 0.05 * attacked), 3)
    if "temple" not in held:                                # rites as far as its creed is not yet explained
        g["temple"] = round(float(getattr(planet.civilization, "dogma", 0.0) or 0.0) * (1.0 - _info(kernel, planet)), 3)


# ---------------------------------------------------------------------- the season
def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import fertility
    st = stats(kernel)
    logs: List[str] = []
    for p in _peoples(kernel):
        gen = fertility.generation_years(fertility.strategy(kernel, p))
        _council(kernel, p)                                   # moves only what no steward has set
        _believe(kernel, p, gen)
        _legends(kernel, p, gen)
        _guilds(kernel, p)
        s = stress(kernel, p)
        p.society["stress"] = s
        line = _strife(kernel, p, s, gen)
        if line:
            logs.append(line)
        line = _niche_wars(kernel, p)
        if line:
            logs.append(line)
        troops = int(p.population * gauges(p)["levy"] / SOLDIERS_PER_TROOP)
        p.garrison_troops = max(p.garrison_troops, troops) if p.owner_id else troops   # a people's own levy
    st["peoples"] = len(_peoples(kernel))
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    ps = _peoples(kernel)
    dog = [float(getattr(p.civilization, "dogma", 0.0) or 0.0) for p in ps]
    return {"peoples": len(ps), "strife": st["strife"], "driven_out": st["driven_out"],
            "mean_dogma": round(sum(dog) / len(dog), 3) if dog else 0.0,
            "myths": sum(len(p.society.get("myths", [])) for p in ps),
            "mean_trades": round(sum(int(p.society.get("trades", 0)) for p in ps) / len(ps), 2) if ps else 0.0}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="society",
    state=lambda: {"strife": 0, "driven_out": 0, "peoples": 0},
    season=quarter,
    summary=summary,
))
