"""
Xylarium mottos: what a people says of itself when it wakes - in its OWN tongue, from what its own waking was.

A TONGUE is a people's own: the sounds its mouths and bodies make are a share of every sound minds make (the
syllables names are made of), drawn by its own seed - so no two peoples speak alike. A WORD is its tongue's: each
thing it names it names in its own sounds, the same thing always the same word for it, never the same word for
another people.

Its MOTTO is said from the facts of its waking, never chosen for it:
  - what it found when it first looked up: its star's colour (from the star's mass), the dark with no sun (a world
    with no star), the ice above it (a people under an ice shell), the storm above the deep (in a giant's depths);
  - how its bodies move toward it (its form: swimming, walking, drifting, rising tall, low and many-limbed);
  - who says it: "we" for a people of many minds, "we who are one" for a colony that thinks as one, "the
    spread of us" for a mind spread through its medium;
  - and where it lives: its medium (its solvent, its depth).
The motto is its tongue's sentence, with a translation beside it - "Nakuro ves telan ('we swam toward the red sun,
out of the warm water')".
"""

import hashlib
import random
from typing import Any, Dict, List, Optional

LEGACY = ("we looked up",)          # the one motto every waking people was once given: said again from its waking


def _rng(*parts: Any) -> random.Random:
    return random.Random(int.from_bytes(hashlib.sha256("|".join(map(str, parts)).encode()).digest()[:8], "big"))


def _root(people: str) -> str:
    """The people its tongue came down from: a daughter ("Renor of Veiled 012d") speaks its parent's, drifted."""
    name = people.split(":", 1)[-1]
    return name.split(" of ", 1)[0]


def tongue(people: str) -> List[str]:
    """Its sounds: its root people's share of all the syllables minds' names are made of - and, for a daughter
    people, that tongue drifted by its own seed (a dialect: one of its sounds gone, another come)."""
    from xylarium.config import NATIVE_SYLLABLES
    pool = list(NATIVE_SYLLABLES)
    root = _root(people)
    n = max(4, len(pool) * 5 // 8)
    sounds = _rng("tongue", root).sample(pool, n)
    if root != people.split(":", 1)[-1]:
        rng = _rng("dialect", people)
        others = [x for x in pool if x not in sounds]
        if others:
            sounds[rng.randrange(len(sounds))] = rng.choice(others)
    return sounds


def word(people: str, thing: str) -> str:
    """Its word for a thing: from its own sounds, always the same for it. A daughter people says its parent's word
    with its drifted sound in place of the one its dialect lost - kin are heard in it."""
    root = _root(people)
    parent = _root_tongue(root)
    rng = _rng("word", root, thing)
    w = [rng.choice(parent) for _ in range(rng.randint(1, 3))]
    mine = tongue(people)
    swap = {a: b for a, b in zip(parent, mine) if a != b}
    return "".join(swap.get(x, x) for x in w)


def _root_tongue(root: str) -> List[str]:
    from xylarium.config import NATIVE_SYLLABLES
    pool = list(NATIVE_SYLLABLES)
    return _rng("tongue", root).sample(pool, max(4, len(pool) * 5 // 8))


def _sky(kernel: Any, planet: Any, med: str) -> str:
    """What it found above it when it first looked up."""
    from xylarium.kernel import physics
    if "under ice" in med or "under_ice" in med:
        return "the ice above us"
    if "deep" in med:
        return "the storm above the deep"
    sec = kernel.sectors.get(planet.sector_id) if kernel is not None else None
    if planet.planet_type == "ROGUE" or sec is None or getattr(sec, "star_type", None) in (None, ""):
        return "the dark that has no sun"
    try:
        m = float(physics.star(sec)["mass"])
    except Exception:
        return "the sun"
    colour = ("red" if m < 0.45 else "orange" if m < 0.8 else "yellow" if m < 1.05 else "white" if m < 1.4
              else "blue")
    return f"the {colour} sun"


def _who(shape: str) -> str:
    return {"superorganism": "we who are one", "distributed": "the spread of us"}.get(shape, "we")


def _toward(form: str) -> str:
    return {"swimming": "swam toward", "drifting": "drifted toward", "walking": "walked toward",
            "tall and slender": "rose toward", "low and many-limbed": "crawled toward"}.get(form, "turned toward")


SOLVENT_WORD = {"H2O": "water", "NH3": "ammonia", "CH4": "methane", "N2": "nitrogen", "plasma": "fire",
                "CO2": "carbon dioxide", "H2SO4": "acid", "HCN": "cyanide", "H2": "hydrogen"}


def _from(traits: Dict[str, Any]) -> str:
    """Where it lives, said plainly: its medium's solvent and where in its world it lies."""
    medium = str(traits.get("medium") or "")
    solvent = str(traits.get("solvent") or "")
    if not solvent:
        return ""
    dark = medium.startswith("a dark ")
    where = medium.split(solvent, 1)[-1].strip().replace("_", " ") if solvent in medium else ""
    place = {"surface": "", "under ice": " under the ice", "deep": " of the deep", "air": " of the air"}.get(
        where, f" {where}" if where else "")
    return f"out of the {'dark ' if dark else ''}{SOLVENT_WORD.get(solvent, solvent)}{place}"


def compose(kernel: Any, people: str, planet: Any, traits: Dict[str, Any]) -> Dict[str, str]:
    """Its motto from its waking: the gloss from what its waking was, said in its own words."""
    med = str(traits.get("medium") or "")
    parts = [_who(str(traits.get("shape") or "society")), _toward(str(traits.get("form") or "")),
             _sky(kernel, planet, med)]
    gloss = " ".join(parts)
    origin = _from(traits)
    if origin:
        gloss = f"{gloss}, {origin}"
    said = " ".join(word(people, p) for p in parts + ([origin] if origin else []))
    name = people.split(":", 1)[-1]
    if " of " in name:                                     # a daughter people: its own waking was its coming here
        place = name.split(" of ", 1)[1]
        gloss = f"{gloss}, and came to {place}"
        said = f"{said} {word(people, 'and came to')} {place}"
    return {"said": said[:1].upper() + said[1:], "gloss": gloss}


def motto(kernel: Any, people: str, planet: Any, traits: Dict[str, Any]) -> str:
    m = compose(kernel, people, planet, traits)
    return f"{m['said']} ('{m['gloss']}')"


def season(kernel: Any) -> List[str]:
    """Once a year: a woken people that still carries the motto every people was once given says its own."""
    from xylarium.kernel import polity
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    for sec in kernel.sectors.values():
        for p in sec.planets:
            civ = getattr(p, "civilization", None)
            if civ is None or getattr(civ, "motto", None) not in LEGACY:
                continue
            traits = getattr(civ, "traits", None) or {}
            civ.motto = motto(kernel, f"civ:{civ.name}", p, traits)
    return []


from xylarium.kernel import state  # noqa: E402,F401
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="mottos", state=lambda: {}, season=season))
