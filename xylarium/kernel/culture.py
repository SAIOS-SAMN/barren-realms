"""
Xylarium culture: what a people thinks is out there, the hurdles it meets, what it imagines, and how it makes art -
the record worth keeping of a people not yet among the stars.

A people is LINKED to the interstellar community once it lives on more than one world, harvests its sun's energy
directly (sunfields, orbital arrays: harvest.py), or trades its money on the exchange (institutions.py). Until then
its ledger keeps no banking or currency entries (history.py counts them, no more): what is worth telling about it is
what follows. Everything is derived from the people's own circumstances; nothing is drawn from a list of stories.

COSMOLOGY   what it thinks the sky is. Its sky is physics: how crowded it is (the stellar density where it lives,
            cosmos.density), whether the galaxy's bright heart hangs in it (living within a few kpc of the centre),
            its moons, its sun's colour. What it makes of the sky is its knowledge against its creed (information
            mastery vs dogma, society.py), and whether it has met anyone or heard a signal from another galaxy:
              met or heard        -> we are not alone (and what the others are like)
              creed over knowledge -> the lights are gods, ancestors, the eyes of the dead
              knowledge over creed -> the lights are suns like ours - why does no one answer? (the silence)
              neither              -> the sky is a roof, and the world is all there is
HURDLES     the filters a people must pass, recorded when first faced and again when passed (a generation survived
            after) - the first failed harvest, the sickness of crowds, the war of brothers, the turning from the
            wild, the founding of order, the reach for the sky, the first stranger, the dying sun.
Beliefs, tales and styles are weighed once a generation, or at once when something new comes (a stranger, a signal,
a dying sun); each change is a ledger event.

IMAGINATION what it tells itself about worlds it has not seen, once it has the leisure (a surplus beyond its need):
            the shape of its tales follows its body (swarm-epics for r-strategists, single heroes for K), its
            biology (green worlds, deep stone, the long cold, fire and storm, the dark), its sky (voyages to its
            moon; travellers between suns under a crowded sky) and its fears (arks, for a people whose sun is dying).
ART         once it has artisans (its trades, society.py) or leisure: its medium follows its senses (colour for
            carbon life under a sun, carved and struck stone for lithic minds, slow-grown ice for the Stillcold,
            patterned light for plasmic minds, sound for those who live in the dark), its palette its sun's colour,
            its symmetries the mathematics its crystals can express (intellect.py: turning patterns for a cyclic
            group; turning and mirrored ones for the full symmetries of the square; layered and higher-dimensional
            lattices beyond), its mood its creed and fortune. A new style is a ledger event.
"""

from typing import Any, Dict, List

from xylarium.kernel import laws


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "culture")


# ---------------------------------------------------------------------- linked or not
def linked_peoples(kernel: Any) -> List[str]:
    return list(stats(kernel).get("linked", []))


def is_linked(kernel: Any, actor: str) -> bool:
    """Captains, institutions and peoples among the stars are linked; a people on one world, off the exchange and
    not yet harvesting its sun, is not."""
    if not actor or not actor.startswith("civ:"):
        return True
    return actor in set(stats(kernel).get("linked", []))


def _peoples(kernel: Any) -> Dict[str, List[Any]]:
    from xylarium.kernel import knowledge
    out: Dict[str, List[Any]] = {}
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population > 0 and getattr(p, "civilization", None) is not None and not getattr(p, "natives", None):
                out.setdefault(knowledge.holder_of_planet(p), []).append(p)
    return out


def _linked(kernel: Any, worlds: List[Any]) -> bool:
    from xylarium.kernel import harvest
    if len(worlds) > 1:
        return True
    arrays = harvest.stats(kernel).get("arrays", {})
    for p in worlds:
        if (p.society.get("harvest") or {}).get("field", 0) or arrays.get(str(p.sector_id)):
            return True
        if p.currency in getattr(kernel.fx_market, "pools", {}):
            return True
    return False


# ---------------------------------------------------------------------- what they make
def _info(kernel: Any, holder: str) -> float:
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge
    return laws.mastery(knowledge.experience(kernel, holder, "information"), KNOWLEDGE_UNIT)


def sky(kernel: Any, planet: Any) -> Dict[str, Any]:
    from xylarium.kernel import cosmos, society
    place = cosmos.stats(kernel).get("place", {}).get(str(planet.sector_id)) if cosmos.is_cosmic(kernel) else None
    r = float(place["r"]) if place else cosmos.R0_KPC
    base = society._sky(kernel, planet)
    return {"colour": base["colour"], "moons": base["moons"], "crowded": cosmos.density(r) > 2.0,
            "heart": r < 6.0, "r_kpc": round(r, 2)}


def cosmology(kernel: Any, holder: str, planet: Any) -> Dict[str, Any]:
    from xylarium.kernel import cluster, contact
    fam = contact.stats(kernel)["familiarity"]
    met = sorted({q for k in fam for q in k.split("|") if holder in k.split("|") and q != holder})
    heard = [g["name"] for g in (cluster.stats(kernel).get("galaxies") or [])[1:] if g.get("heard")]
    d = float(getattr(planet.civilization, "dogma", 0.0) or 0.0)
    i = _info(kernel, holder)
    s = sky(kernel, planet)
    if met or heard:
        stance = "plural"
        text = (f"we are not alone: {', '.join(x.split(':')[-1] for x in met[:3]) or 'voices from ' + heard[0]} "
                f"share this sky")
    elif d > i:
        stance = "sacred"
        text = ("the lights above are the eyes of the dead, " +
                ("and the great glowing heart among them is where all souls go" if s["heart"] else
                 "watching from the dark" if not s["crowded"] else "crowding close to judge"))
    elif i > 0.0:
        stance = "silence"
        text = ("the lights are suns like ours, " + ("so many that someone must be there" if s["crowded"] else
                                                      "few and far") + " - and none of them has ever answered")
    else:
        stance = "roof"
        text = "the sky is a roof, and the world beneath it is all there is"
    return {"stance": stance, "text": text, "met": len(met), "heard": len(heard), "dogma": round(d, 3),
            "knowledge": round(i, 3), "sky": s}


HURDLES = {"famine_cycle": "the first failed harvest", "blight_cycle": "the sickness of crowds",
           "strife_cycle": "the war of brothers", "way:farm": "the turning from the wild",
           "way:state": "the founding of order", "yards": "the reach for the sky", "contact": "the first stranger",
           "forecast": "the dying sun"}


def _hurdles_now(kernel: Any, holder: str, worlds: List[Any], met: int) -> List[str]:
    from xylarium.kernel import sustenance
    out = []
    for p in worlds:
        soc = p.society
        for key in ("famine_cycle", "blight_cycle", "strife_cycle", "forecast"):
            if key in soc:
                out.append(key)
        if soc.get("way") in ("farm", "state"):
            out.append("way:farm")
        if soc.get("way") == "state":
            out.append("way:state")
        if sustenance.yards(p):
            out.append("yards")
    if met:
        out.append("contact")
    return sorted(set(out))


def imagined(planet: Any, kernel: Any, cos: Dict[str, Any]) -> List[str]:
    from xylarium.kernel import biosphere, fertility
    metab = biosphere.metabolism_of(kernel, planet)
    strat = fertility.strategy(kernel, planet)
    tales = ["swarm-epics, where the many are the hero" if strat == "r" else "tales of a single hero against the world"]
    tales.append({"biotic": "green worlds beyond the horizon", "mineral": "kingdoms in the deep stone",
                  "cryogenic": "the long cold and what sleeps in it", "plasmic": "fire, storm and the hearts of suns",
                  "umbral": "the dark between, and what lives there"}.get(metab, "worlds unlike their own"))
    s = cos["sky"]
    if s["moons"]:
        tales.append("voyages to the moon" if s["moons"] == 1 else f"voyages among their {s['moons']} moons")
    if s["crowded"]:
        tales.append("travellers between the suns")
    if cos["stance"] == "plural":
        tales.append("the meeting of peoples")
    elif cos["stance"] == "silence":
        tales.append("the first answer from the sky")
    if planet.society.get("forecast"):
        tales.append("arks that carry a people from a dying sun")
    return tales


def art(planet: Any, kernel: Any, holder: str) -> Dict[str, str]:
    from xylarium.kernel import biosphere, crystal as C, intellect
    metab = biosphere.metabolism_of(kernel, planet)
    medium = {"biotic": "painted colour", "mineral": "carved and struck stone", "cryogenic": "ice grown over seasons",
              "plasmic": "patterned light", "umbral": "sound and echo"}.get(metab, "shaped matter")
    colour = sky(kernel, planet)["colour"]
    palette = {"red": "reds and umbers", "orange": "ambers and ochres", "yellow": "the full spectrum",
               "white": "cold whites and blues", "pale": "pale and washed tones"}.get(colour, "its sun's tones")
    vocab = intellect.vocabulary(kernel, holder)
    group = len(intellect._chart(vocab))
    higher = any(op in vocab for op in C.STACK_OPS + C.HYPER_OPS)
    symmetry = ("lattices layered in depth and beyond it" if higher else
                "patterns that turn and mirror" if group >= 8 else
                "patterns that turn but never mirror" if group >= 4 else "unrepeated forms")
    d = float(getattr(planet.civilization, "dogma", 0.0) or 0.0)
    i = _info(kernel, holder)
    recent_strife = planet.society.get("strife_cycle", -10 ** 9) > kernel.cycle_count - 2500
    mood = ("grief" if recent_strife else "the sacred and iconic" if d > max(0.3, i) else
            "the abstract and geometric" if i > 0.3 else "ornament and plenty")
    out = {"medium": medium, "palette": palette, "symmetry": symmetry, "mood": mood}
    from xylarium.kernel import lifespan
    gone = lifespan.remembered(kernel, holder) if "lifespan" in kernel.state else []
    if gone:                                           # the ability to remember someone who is gone
        out["elegy"] = f"{gone[0]['name']}, their {gone[0]['role']}"
    return out


def _capable(kernel: Any, planet: Any) -> bool:
    soc = planet.society
    ss = float(soc.get("self_sufficiency", 1.0) or 1.0)
    return int(soc.get("trades", 0)) > 0 or ss > 1.05


# ---------------------------------------------------------------------- the season
def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import fertility, history
    st = stats(kernel)
    peoples = _peoples(kernel)
    st["linked"] = sorted(h for h, ws in peoples.items() if _linked(kernel, ws))
    logs: List[str] = []
    for holder, worlds in peoples.items():
        cap = max(worlds, key=lambda w: w.population)
        rec = st["peoples"].setdefault(holder, {"hurdles": {}})
        name = getattr(cap.civilization, "name", cap.name)
        gen = fertility.generation_years(fertility.strategy(kernel, cap))
        cos = cosmology(kernel, holder, cap)
        # beliefs and styles change over generations - or at once when something new comes (a stranger, a signal,
        # a dying sun)
        news = (cos["met"], cos["heard"], bool(cap.society.get("forecast")))
        from xylarium.kernel import lifespan
        people = sum(w.population for w in worlds)
        if "lifespan" in kernel.state and lifespan.died(kernel, holder) > 0:
            turned = lifespan.turned_over(kernel, holder, rec.get("weighed_died", -10 ** 12), people)
        else:
            turned = kernel.cycle_count - rec.get("weighed", -10 ** 9) >= gen * 100
        due = turned or list(news) != rec.get("news")     # a new generation of minds, or something new
        if due:
            rec["weighed"], rec["news"] = kernel.cycle_count, list(news)
            rec["weighed_died"] = lifespan.died(kernel, holder)
        if due and cos["stance"] != rec.get("stance"):
            rec["stance"] = cos["stance"]
            history.event(kernel, "PHILOSOPHY", f"The {name} come to believe {cos['text'].split(':')[0].split(',')[0]}",
                          actors=[holder], planet=cap, text=f"The {name} say that {cos['text']}.", data=cos)
        for key in _hurdles_now(kernel, holder, worlds, cos["met"]):
            h = rec["hurdles"].setdefault(key, {})
            if "faced" not in h:
                h["faced"] = kernel.cycle_count
                history.event(kernel, "HURDLE", f"The {name} face {HURDLES[key]}", actors=[holder], planet=cap,
                              data={"hurdle": key, "status": "faced"})
            elif "passed" not in h and kernel.cycle_count - h["faced"] >= gen * 100:
                h["passed"] = kernel.cycle_count
                history.event(kernel, "HURDLE", f"The {name} pass {HURDLES[key]}", actors=[holder], planet=cap,
                              data={"hurdle": key, "status": "passed", "years": round(gen, 1)})
        if not _capable(kernel, cap):
            continue
        tales = imagined(cap, kernel, cos)
        if due and tales != rec.get("tales"):
            rec["tales"] = tales
            history.event(kernel, "IMAGINATION", f"The {name} tell of {tales[1]}", actors=[holder], planet=cap,
                          text=f"The {name} tell " + "; ".join(tales) + ".", data={"tales": tales})
        style = art(cap, kernel, holder)
        sig = "|".join(style[k] for k in ("medium", "palette", "symmetry", "mood"))
        if due and sig != rec.get("art"):
            rec["art"] = sig
            history.event(kernel, "ART", f"The {name} make {style['medium']} of {style['mood']}", actors=[holder],
                          planet=cap, text=f"The {name} work in {style['medium']}, in {style['palette']}, in "
                                           f"{style['symmetry']}, toward {style['mood']}"
                                           + (f" - and in elegy for {style['elegy']}" if style.get("elegy") else "")
                                           + ".", data=style)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    stances: Dict[str, int] = {}
    for rec in st["peoples"].values():
        stances[rec.get("stance", "?")] = stances.get(rec.get("stance", "?"), 0) + 1
    return {"linked": len(st.get("linked", [])), "peoples": len(st["peoples"]), "cosmologies": stances}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="culture",
    state=lambda: {"linked": [], "peoples": {}},
    season=quarter,
    summary=summary,
))
