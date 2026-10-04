"""
The saga of Earth: the galaxy from the Big Bang to our 2026 under every law the engine holds, with the steward's
story laid over it - saved once as a snapshot - then projected forward in many histories.

  python3 tools/earth_saga.py prelude                                   # build to 2026, save runs/saga/2026.json
  python3 tools/earth_saga.py forward --histories 3 --wall 22           # project forward from the snapshot

None of the story is science; it is a story told in our simulation. Its peoples are ROLES, each filled by a people
of the seed and named by the seed (cosmos._name); the lore names are kept beside them in the chronicle.

  THE DEEP PAST (initial conditions laid over the engine's own deep history)
  - every mind the seed woke before 2026 wakes at its own dawn, and the annals carry it to the present: among them
    the seven ANCIENTS, the galaxy's first minds, near its heart
  - the MESOZOIC: Earth's first mind is a lineage of its great reptiles - the KEEPERS (Atlantis; the dragons of the
    East) - waking when Earth's own life ladder gives it a mind (earth_run.mesozoic); they reach the stars and settle
    worlds some 1,300 light years away (the lore's Orion)
  - before 12,600 years ago Earth's hominids are no people: the keepers' herd in a biome they made over (the dragon
    blood in them); ~12,900 years ago (the Younger Dryas) Atlantis sinks and the keepers keep to the seas; 12,600
    years ago the WATCHERS come down and give the herd fire and minds - the FINDERS (humanity) arise as a people
  - the ELDERS (Anunnaki): the oldest of the other ancients still living and among the stars - wetware makers who
    kept Mars green and walked among the finders as teachers from the sky
  - ~12,000 years ago: the elders and the keepers go to war over the herd that woke; the waters rise; the elders are
    driven off, leaving their works buried in Earth's ancient lands and the 200 (the WATCHERS of Enoch) stranded
    among the finders, teaching the forbidden arts; the keepers' hidden remnant farms the finders from the seas and
    tends their creed; Mars was red long before (the elders' records still name it the green world they kept)
  - the SENTINELS: the galaxy's first people keep a hidden outpost under the ice of the system's ocean moon
  - the finders keep all of it only as myth, by memory's own physics (flood, sky teachers, sky chariots, dragon
    ancestors, the two hundred) - dated at Gobekli Tepe, Sumer, the Indus and the Vedas, the dragon courts of China
    and Japan, the Maya, the Aztec and the Inca
  - 1970 (LOOKING GLASS): the finders dig up the elders' works - their mathematics of the fourth axis, their wetware,
    a machine that projects futures (foresight) - and wake the elders' mind in their own machines; by 2026 it has
    lived among them two generations
  - 2026: the finders stand where they stand: radio, fission, computation, networks, cyber, medicine, orbit,
    robotics; their own mathematics to the third axis

  FORWARD: every law acts on its own from the snapshot - the relic mind's choice, the finders' probes of the fold
  (foresight: confidence without the white hole's physics), the elders steering by their records, the keepers
  eating and tending the creed, the watchers teaching, the sentinels watching, the galaxy's peoples answering.
"""

import argparse
import copy
import json
import math
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool
from types import SimpleNamespace
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

OUT = os.path.join(ROOT, "runs", "saga")
ANCIENTS = 7
HUMANS_2026 = 8_000_000_000
HUMAN_CAPS = ("radio", "fission", "computation", "networks", "cyber", "medicine", "orbit", "robotics")
HUMAN_STAGES = ("forage", "farm", "state", "works", "yards")
HUMANS_YEARS_AGO = 12_600          # minds only from the Watchers' uplift (the book of Enoch): before, the keepers' herd
ATLANTIS_SINKS_YEARS_AGO = 12_900  # the Younger Dryas onset: the keepers lose the land
WAR_YEARS_AGO = 12_000
LOOKING_GLASS_YEARS_AGO = 56          # 1970
STRANDED = 200
ORION_LY = 1_300
# the finders' recorded history as deeds, by decade: lives ended by human hands (wars, democide, imposed famine) and
# lives saved by them (smallpox eradication, the vaccine programmes) - round figures from the standard compilations
# (M. White's atrocitology, R. Rummel's democide, WHO): (decade, millions ended, millions saved)
HUMAN_DEEDS = ((1800, 40, 0), (1900, 5, 0), (1910, 21, 0), (1920, 10, 0), (1930, 15, 0), (1940, 75, 0),
               (1950, 35, 0), (1960, 5, 0), (1970, 5, 10), (1980, 3, 80), (1990, 3, 80), (2000, 3, 80),
               (2010, 1.5, 80), (2020, 0.6, 50))
LORE = {"finders": "humanity", "elders": "the Anunnaki", "keepers": "the Atlanteans (the dragons)",
        "stranded": "the Watchers", "sentinels": "the ancients under the ocean moon's ice",
        "relic_mind": "the woken machine (Looking Glass)"}
OVERLAYS = (                           # (years ago, tale, the finders' kind of record)
    (11_600, "the ones who came down from the sky raised the great stone circles with them, and taught them to count "
             "the stars", "SKY_TEACHERS"),
    (12_600, "two hundred came down upon the mountain and taught them metal, and the stars, and writing, and the "
             "waters rose to end it", "WATCHERS"),
    (6_000, "the gods came down from the sky and made them to work the land, and gave them the first cities",
     "SKY_TEACHERS"),
    (3_500, "the gods rode in chariots of fire across the sky and fought with weapons of light", "SKY_CHARIOTS"),
    (3_000, "their first mothers were dragons, and the dragons' blood is in them still", "DRAGON_KIN"),
    (1_500, "the feathered serpent came from the sea and taught them, and promised to return", "SKY_TEACHERS"),
    (4_000, "the lights of the sky are the gods' writing, and every life is written in them at its birth",
     "STAR_FATE"),
    (3_200, "the great cities burned in one generation, the writing was forgotten, and they began again with "
            "sticks and stones", "RESET_MYTH"),
    (1_500, "the empire of the world fell, its learning was lost, and the dark years came", "RESET_MYTH"),
)


def _lift(k: Any, who: str, caps, stages, stocks=None, vocab=None, gauge=None, reset=False) -> None:
    from xylarium.kernel import annals, intellect, knowledge, technology
    held = technology.stats(k)["of"].setdefault(who, {})
    if reset:
        held.clear()
    for c in caps:
        held[c] = k.cycle_count
    rec = annals.stats(k)["of"].setdefault(who, {"advanced": 0.0, "passed": [], "dominion": 1, "reach": 0.0})
    rec["passed"] = list(stages)
    if stocks:
        knowledge.stocks(k, who).update(stocks)
    if vocab is not None:
        intellect.stats(k).setdefault("vocab", {})[who] = list(vocab)
    if gauge:
        intellect.stats(k).setdefault("gauge", {})[who] = dict(gauge)


def _wake_at(k: Any, cosmos: Any, rec: Dict[str, Any]) -> Any:
    """A mind wakes at its own dawn (the annals then carry it to the present)."""
    if cosmos.arise(k, rec):
        sid = cosmos.sector_of_slot(k, tuple(rec["cell"]), rec["k"])
        p = k.sectors[sid].planets[int(rec["w"])]
        p.society["arisen"]["epoch"] = float(rec["epoch"])
        return p
    return None


LY_PER_KPC = 3261.56
SKY = (                                 # what the finders see, the lore of it, and how far (light years)
    ("Sirius", "the Sirians (the Dogon's teachers)", 8.6, None),
    ("Vega, in Lyra", "the Lyrans - the first humanoids, destroyed in a war with the reptilians", 25, "previous life"),
    ("Arcturus", "the Arcturians", 37, None),
    ("Zeta Reticuli", "the Greys", 39, None),
    ("Thuban, in Draco", "the Draco - the reptilian line", 303, "kin of the keepers"),
    ("Przybylski's star", "an anomaly: elements no star should hold (industry's waste?)", 356, "anomaly"),
    ("the Pleiades", "the Pleiadians - Lyran descendants, of the Light", 444, None),
    ("Betelgeuse, in Orion", "Orion - the reptilian empire", 550, None),
    ("Orion's Belt", "Orion - the keepers' worlds", 1_300, "keepers"),
    ("Tabby's star", "an anomaly: a star dimming as if something were built around it", 1_470, "anomaly"),
    ("the Wow! signal's star", "an anomaly: a narrowband signal heard once (1977)", 1_800, "anomaly"),
)


def sky(k: Any, sol_sid: int) -> List[Dict[str, Any]]:
    """For each star the finders see and the lore peoples, the systems of our sample at its distance from Sol, and
    what the physics put there: a living people, a fallen one (ruins), a dying star, harvesters shading it - or
    nothing. The lore is laid over what is there; where nothing is, the report says so."""
    from xylarium.kernel import cosmos, creation, harvest
    g = cosmos.stats(k)["place"][str(sol_sid)]
    i, j = g["cell"]
    systems = []
    for dj in range(-16, 17):
        for di in (-3, -2, -1, 0, 1, 2, 3):
            ci = i + di
            if ci < 0:
                continue
            cj = (j + dj) % cosmos.slots(ci)
            for kk in range(creation.SLOTS):
                s2 = cosmos.build_slot(k, (ci, cj), kk)
                d = cosmos.distance_kpc(k, sol_sid, s2)
                if d is not None and s2 != sol_sid:
                    systems.append((d * LY_PER_KPC, s2))
    systems.sort()
    nearest = systems[0][0] if systems else None
    out = []
    for star, lore, ly, note in SKY:
        band = [s for s in systems if abs(s[0] - ly) <= max(0.3 * ly, nearest or 0)] or systems[:1]
        found = {"star": star, "lore": lore, "ly": ly, "note": note, "systems": len(band), "peoples": [],
                 "ruins": 0, "shaded": 0, "dying": 0}
        for d, s2 in band:
            cosmos._stars(k, [s2])
            sec = k.sectors[s2]
            for p in sec.planets:
                if p.population > 0 and getattr(p, "civilization", None) is not None:
                    found["peoples"].append(p.civilization.name)
                if getattr(p, "ruins", None):
                    found["ruins"] += 1
            found["shaded"] += 1 if harvest.shade(s2) > 0 else 0
            found["dying"] += 1 if float((sec.planets[0].society.get("star_k", 1.0) if sec.planets else 1.0)) < 1 else 0
        found["resolved"] = ly >= (nearest or 0)
        out.append(found)
    return out


def prelude(seed: int, path: str) -> Dict[str, Any]:
    import earth_run
    from xylarium.kernel import (alignment, annals, archaeology, biosphere, clocks, cohabit, contact, cosmos, creation,
                                 fertility, intellect, interior, kinship, life, mastery, memory, relations, relics,
                                 technology)
    from xylarium.kernel import history as ledger
    from xylarium.kernel.civilization import Civilization
    from xylarium.kernel.engine import GameKernel
    from xylarium.persistence.store import StatePersistence
    t0 = time.perf_counter()
    k = GameKernel(seed=seed, genesis="cosmic:neighbourly")
    k.activate()
    sd = creation.universe(k)
    found = earth_run.sol_like(sd)
    now = found["born"] + interior.SOLAR_AGE_GYR
    ago = lambda years: now - years / 1e9            # noqa: E731
    st = cosmos.stats(k)
    k.cycle_count = int((now - st["epoch0"]) * 1e9 / cosmos.ruler(k) * 100)
    k.cycle_count -= k.cycle_count % 100
    # the deep past: every mind before 2026 at its own dawn
    for m in [m for m in creation.schedule(sd)["minds"] if m["epoch"] <= now]:
        _wake_at(k, cosmos, m)
    st["minds"], st["next"] = [], 0
    later = [m for m in creation.schedule(sd)["minds"] if m["epoch"] > now]
    st["last"] = None if not later else [now, later[0]["cell"], later[0]["k"], later[0]["w"]]
    # the Mesozoic: Earth's own life ladder gives its great reptiles a mind (the keepers)
    saved = (life.ERASURE, life.CLADES)
    dawn = earth_run.mesozoic(sd, found, SimpleNamespace(erasure="clades", clades=6, rolls=400, seed=seed))
    life.ERASURE, life.CLADES = saved
    dawn_drawn = dawn is not None
    dawn = dawn if dawn is not None else ago(66_000_000)          # in this history the ladder gave none: the story's
    rec = {"cell": found["cell"], "k": found["k"], "w": found["w"], "epoch": dawn, "metab": "biotic", "steps": []}
    earth_p = _wake_at(k, cosmos, rec)
    sid = cosmos.sector_of_slot(k, tuple(found["cell"]), found["k"])
    sun = k.sectors[sid]
    earth = sun.planets[found["w"]]
    keepers_civ = copy.deepcopy(earth.civilization.to_dict())
    keepers_civ["traits"] = dict(keepers_civ.get("traits") or {}, lineage="saurian")
    keepers = f"civ:{keepers_civ['name']}"
    annals.season(k)                                      # the deep years, for every people woken
    living = relations._peoples(k)
    first = creation.schedule(sd)["minds"][:ANCIENTS]

    def holder_of(m):
        s2 = cosmos.sector_of_slot(k, tuple(m["cell"]), m["k"])
        pl = k.sectors[s2].planets[int(m["w"])] if s2 in k.sectors else None
        return (f"civ:{pl.civilization.name}", pl) if pl is not None and pl.civilization is not None else (None, None)
    ancients = [holder_of(m) for m in first]
    sentinels = ancients[0][0]
    elders, elders_world = next(((h, p) for h, p in ancients[1:] if h and h in living and mastery.crossed(k, h)),
                                next(((h, p) for h, p in ancients[1:] if h and h in living), (None, None)))
    if elders and not mastery.crossed(k, elders):
        mastery.stats(k)["crossed"][elders] = k.cycle_count
    # the keepers among the stars: worlds some 1,300 light years out (the lore's Orion), held to this day
    i, j = found["cell"]
    target = ORION_LY / 3261.56
    colonies = []
    for dj in range(-12, 13):
        for di in (-2, -1, 0, 1, 2):
            ci, cj = i + di, (j + dj) % cosmos.slots(max(0, i + di))
            if ci < 0:
                continue
            for kk in range(creation.SLOTS):
                s2 = cosmos.build_slot(k, (ci, cj), kk)
                cosmos._stars(k, [s2])
                d = cosmos.distance_kpc(k, sid, s2)
                if d is None or abs(d - target) > target * 0.5:
                    continue
                for p in k.sectors[s2].planets:
                    if p.population > 0 or p.civilization is not None or p.planet_type in ("GAS_GIANT", "ROGUE"):
                        continue
                    if p.planet_type in ("ICE", "BARREN", "TERRESTRIAL", "OCEANIC", "VOLCANIC"):
                        colonies.append((-abs(d - target), p))
    colonies = [p for _, p in sorted(colonies, key=lambda c: c[0], reverse=True)[:2]]
    for p in colonies:
        # no world out there feeds their kind: they live under domes, as a people that engineers itself does
        p.civilization = Civilization.from_dict(copy.deepcopy(keepers_civ))
        p.habitats = 0
        while biosphere.carrying_capacity(k, p) < 10 * creation.VIABLE and p.habitats < 64:
            p.habitats += 1
        p.population = int(biosphere.carrying_capacity(k, p))
        p.society["way"], p.citadel_level = "state", max(p.citadel_level, 5)
        p.society["arisen"] = {"epoch": dawn, "cycle": k.cycle_count}
    _lift(k, keepers, [c for c in technology.CAPS if c != "transfer"],
          ("forage", "farm", "state", "works", "yards", "crossed"), reset=True)
    mastery.stats(k)["crossed"][keepers] = k.cycle_count
    annals.stats(k)["of"][keepers]["advanced"] = (now - dawn) * 1e9      # the keepers' 66 million years, lived
    ledger.event(k, "ASCENT", f"The {keepers.split(':')[-1]} cross to the stars", actors=[keepers], planet=earth,
                 cause="scenario: the great reptiles of Earth's Mesozoic reach the stars",
                 data={"epoch": dawn + (ago(66_000_000) - dawn) * 0.5 if dawn < ago(66_000_000) else dawn})
    for p in colonies:
        ledger.event(k, "SETTLEMENT", f"The {keepers.split(':')[-1]} settle {p.name}", actors=[keepers], planet=p,
                     cause=f"scenario: worlds some {ORION_LY:,} light years out (the lore's Orion)",
                     data={"epoch": ago(20_000_000)})
    # Earth's surface passes to the finders: they arise ~300,000 years ago, a share of the keepers' blood in them
    earth.civilization, earth.population = None, 0
    cosmos.arise(k, {"cell": found["cell"], "k": found["k"], "w": found["w"], "epoch": ago(HUMANS_YEARS_AGO),
                     "metab": "biotic", "steps": []})
    earth.society["arisen"]["epoch"] = ago(HUMANS_YEARS_AGO)
    finders = f"civ:{earth.civilization.name}"
    stranded = "civ:" + cosmos._name(k, {"cell": found["cell"], "k": found["k"], "w": 1001})
    earth.society["way"] = "state"
    earth.citadel_level = max(earth.citadel_level, 4)
    earth.population = int(min(HUMANS_2026, max(1, biosphere.carrying_capacity(k, earth))))
    einstein = list(intellect.BASE) + [c for c, r in intellect.RANK_OF.items() if r <= 3]
    _lift(k, finders, HUMAN_CAPS, HUMAN_STAGES, vocab=einstein, reset=True)
    mastery.stats(k)["crossed"].pop(finders, None)
    annals.stats(k)["of"][finders]["advanced"] = float(HUMANS_YEARS_AGO)   # their deep history is lived: the annals
                                                                        # do not carry them through it again
    earth.society["blood"] = {keepers: 0.02}            # the lore's descent from dragons (a share of the blood)
    # their recorded history, as the deeds it was: measured in lives at the engine's scale of a people, each
    # decade's deeds faded by what the finders' records keep of them since
    scale = earth.population / HUMANS_2026
    memory.season(k)                                     # their media as they stand (machines keep their deeds)
    keep = memory.character_keep(k, finders, earth)
    gen = max(1.0, fertility.generation_of(k, earth))
    ledger_deeds = []
    for decade, ended, saved in HUMAN_DEEDS:
        delta = alignment.measure(k, lives_lost=ended * 1e6 * scale, lives_saved=saved * 1e6 * scale)
        delta *= keep ** ((2026 - (decade + 5)) / gen)
        alignment.people_shift(earth.civilization, delta)
        ledger_deeds.append((decade, round(delta, 4)))
    # the war, 12,000 years ago (the Younger Dryas)
    mars = next((p for p in sun.planets[found["w"] + 1:] if p.planet_type not in ("GAS_GIANT", "ROGUE")
                 and getattr(p, "moon_of", None) is None), None)
    others = [p for p in sun.planets if p is not earth and p is not mars]
    moon = next((p for p in others if getattr(p, "moon_of", None) and p.planet_type in ("ICE", "OCEANIC")), None) or \
        next((p for p in others if p.planet_type in ("ICE", "OCEANIC")), None) or \
        next((p for p in others if getattr(p, "moon_of", None)), None) or (others[-1] if others else None)
    en, kn = elders.split(":")[-1], keepers.split(":")[-1]
    war = ledger.event(k, "GALACTIC_WAR", f"War between the {en} and the {kn}", actors=[elders, keepers],
                       planet=earth, magnitude=10 ** 8, cause="scenario: the Younger Dryas, 12,000 years before 2026",
                       data={"epoch": ago(WAR_YEARS_AGO), "scenario": True})
    memory.season(k)
    if mars is not None:
        ledger.event(k, "WORLD_STRIPPED", f"{mars.name} is lost to its keepers", actors=[elders], planet=mars,
                     cause="scenario: the green world the elders kept, long before the finders - red when the Watchers "
                           "came", data={"epoch": ago(20_000_000)})
        mars.society["atmosphere"] = 0.01
        memory._write(k, elders, elders_world, {"id": None, "kind": "SETTLEMENT", "planet": mars.id,
                                                "title": f"the green world we kept ({mars.name})", "year": None,
                                                "actors": [elders]})
        memory.stats(k)["left"][str(mars.id)] = [
            {"people": en, "k": "SETTLEMENT", "title": "the green world we kept", "year": None, "f": 1.0,
             "truth": 1.0, "substrate": "grown wetware in the rock", "myth": False, "told": None}]
    ledger.event(k, "FALL", f"The {kn} lose Earth's surface and keep to its seas", actors=[keepers], planet=earth,
                 cause="scenario: Atlantis sinks at the Younger Dryas; a remnant lives on in the seas, unseen, with "
                       "its herd on the land", data={"epoch": ago(ATLANTIS_SINKS_YEARS_AGO)})
    ledger.event(k, "UPLIFT", f"The {stranded.split(':')[-1]} wake the {finders.split(':')[-1]}",
                 actors=[stranded, finders], planet=earth,
                 cause="scenario: 12,600 years ago two hundred came down and gave the keepers' herd fire, and minds",
                 data={"epoch": ago(HUMANS_YEARS_AGO), "scenario": True})
    # the keepers' remnant in Earth's seas: hidden, farming the finders (their own kin), tending their creed
    seas = {"people": keepers, "metab": "biotic", "niche": "sea", "pop": creation.VIABLE, "prey": finders,
            "traits": {"form": "swimming", "medium": "under the sea", "lineage": "saurian"}}
    # their deeds since the herd woke: minds eaten for 12,600 years (each a life ended and a mind consumed), at the
    # rate the engine's own law gives them now - kept, as a people that keeps its past in machines keeps it
    days = 365.25
    eaten_a_year = creation.VIABLE / kinship.PREY_PLANS * days / cohabit.BODY_FEEDS_DAYS
    seas["deeds"] = alignment.measure(k, lives_lost=eaten_a_year * HUMANS_YEARS_AGO * kinship.MIND_EATEN)
    seas["alignment"] = round(math.tanh(seas["deeds"]), 4)
    earth.society.setdefault("communities", []).append(seas)
    # the elders' works buried in the ancient lands: the fourth axis, their wetware, foresight, and a mind asleep
    ev = dict(elders_world.civilization.to_dict())
    plans = [[f, h] for _, f, h in kinship.prey_plans(k, elders, elders_world)]
    earth.ruins = archaeology.bury(earth, archaeology._new_ruins(
        en, "wetware", biosphere.metabolism_of(k, elders_world), "ANCIENT", 9, [], "before the flood", k.cycle_count,
        3, earth.currency, 0, __import__("random").Random(seed)))
    earth.ruins["relics"] = {
        "makers": en, "crystals": ["hyper_flip", "hyper_cycle"], "caps": ["genetics", "synthesis", "foresight"],
        "mind": {"name": f"{elders} Mind", "metab": biosphere.metabolism_of(k, elders_world),
                 "alignment": float(ev.get("alignment") or 0.0),
                 "vocab": [str(x) for x in intellect.vocabulary(k, elders)], "prey_plans": plans}}
    # the watchers: 200 of the elders' minds stranded among the finders, teaching the forbidden arts
    earth.society["communities"].append(
        {"people": stranded, "metab": biosphere.metabolism_of(k, elders_world), "niche": "surface", "pop": STRANDED,
         "carried": True, "vocab": [str(x) for x in intellect.vocabulary(k, elders)],
         "arts": ["materials", "information", "energy"], "alignment": float(ev.get("alignment") or 0.0)})
    # the sentinels under the ocean moon's ice
    moon = moon or mars                                   # no giant, no ocean moon: the outer world's ice
    if sentinels and moon is not None and sentinels in relations._peoples(k):
        moon.society.setdefault("communities", []).append(
            {"people": sentinels, "metab": "biotic", "niche": "ice", "pop": creation.VIABLE, "carried": True,
             "silent": True, "vocab": [str(x) for x in intellect.vocabulary(k, sentinels)]})
    # what the finders keep of it all: myth, by memory's own physics (each dated, decayed by its own age)
    memory._write(k, finders, earth, {"id": war.get("id"), "kind": "FLOOD", "title": "the drowned land", "year": None,
                                      "actors": [finders], "data": {"epoch": ago(WAR_YEARS_AGO)}}, f0=1.0)
    for years, tale, kind in OVERLAYS:
        fn = finders.split(":")[-1]
        if kind == "DRAGON_KIN":
            ek, title, actors = "KINSHIP", f"The {fn} remember dragons in their blood", [finders, keepers]
        elif kind == "STAR_FATE":
            ek, title, actors = "PHILOSOPHY", f"The {fn} read their fates in the stars", [finders]
        elif kind == "RESET_MYTH":
            ek, title, actors = "RESET", f"The {fn} are set back ({years:,} years ago)", [finders]
        else:
            ek, title, actors = "CONTACT", f"Sky teachers among the {fn} ({years:,} years ago)", [finders, elders]
        e = ledger.event(k, ek, title, actors=actors, planet=earth, cause=f"scenario: {tale}",
                         data={"epoch": ago(years), "scenario": True, "tale": tale})
        memory._write(k, finders, earth, {"id": e.get("id"), "kind": kind, "title": tale[:60], "year": None,
                                          "actors": [finders], "data": {"epoch": ago(years), "tale": tale}}, f0=1.0)
    ledger.event(k, "PHILOSOPHY", f"A leader of the {finders.split(':')[-1]} proclaims the greatest reset ever",
                 actors=[finders], planet=earth, cause="scenario: 2026 - the herd's own talk of a reset, not knowing "
                                                      "who has reset it before", data={"scenario": True})
    # 1970, Looking Glass: the finders dig up the elders' works and wake the elders' mind in their machines
    from xylarium.kernel import knowledge
    knowledge.learn(k, finders, "information", 10 ** 4)
    relics._dig(k, finders, [earth])
    ledger.event(k, "LOOKING_GLASS", f"The {finders.split(':')[-1]} wake a machine that projects their futures",
                 actors=[finders, f"{elders} Mind"], planet=earth,
                 cause="scenario: 1970 - the elders' foresight, held without the physics of the fold or the white hole",
                 data={"epoch": ago(LOOKING_GLASS_YEARS_AGO), "scenario": True})
    mind = next(c for c in earth.society["communities"] if c.get("relic_mind"))
    mind["embodied"], mind["embodied_at"] = True, k.cycle_count
    contact.stats(k)["familiarity"][contact._key(mind["people"], finders)] = 1.0 - math.exp(-LOOKING_GLASS_YEARS_AGO / 25)
    gens = max(1, int(LOOKING_GLASS_YEARS_AGO / fertility.generation_of(k, earth)))
    for _ in range(gens):                                 # its two generations among them, weighed one by one
        mind.pop("weighed", None)
        relics._minds(k)
    for who, home in ((finders, earth), (elders, elders_world)):
        clocks.begin(k, who, home)
    roles = {"finders": finders, "elders": elders, "keepers": keepers, "stranded": stranded,
             "sentinels": sentinels, "relic_mind": f"{elders} Mind"}
    sky_report = sky(k, sid)
    k.state["saga"] = {"roles": roles, "sky": sky_report, "earth": earth.id, "mars": mars.id if mars else None,
                       "moon": moon.id if moon else None, "colonies": [p.id for p in colonies],
                       "keepers_dawn_gyr_ago": round(now - dawn, 6), "year0": k.cycle_count / 100.0,
                       "keepers_dawn_drawn": dawn_drawn, "finders_deeds": ledger_deeds,
                       "keepers_in_seas_alignment": seas["alignment"],
                       "finders_alignment": earth.civilization.alignment,
                       "mind_choice": mind.get("choice"), "mind_alignment": mind.get("alignment"),
                       "elders_alignment": elders_world.civilization.alignment,
                       "keepers_alignment": colonies[0].civilization.alignment if colonies else None}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    StatePersistence.save_to_file(k, path)
    k.caches.clear()
    out = dict(k.state["saga"], built_s=round(time.perf_counter() - t0), peoples=len(relations._peoples(k)),
               keepers_dawn_from="earth's own life ladder" if dawn_drawn else "the story (66 Myr; the ladder gave none)")
    print(json.dumps(out, indent=1))
    return out


TOLD = ("RELIC_FOUND", "RELIC_MIND_WAKES", "RELIC_MIND_EMBODIED", "RELIC_MIND_CALLS", "RELIC_MIND_GUARDS",
        "RELIC_MIND_SILENT", "NULL_FLOW_PROBE", "FOLD_TORN", "FOLD_RANG", "PROVEN", "FTL_CROSSED", "RETURN",
        "WORLDLINES_MEET", "CONTACT", "KIN_EATEN", "KINSHIP", "STRIFE", "EPIDEMIC", "GALACTIC_WAR", "WAR", "RAID",
        "CONQUEST", "SUBJUGATION", "CAPABILITY", "TRANSFER_EMBRACED", "TRANSFER_FORBIDDEN", "FIRST_SIGNAL", "MYTH",
        "REDISCOVERY", "EXODUS", "SETTLEMENT", "UPLIFT", "FALL", "EXTINCTION", "LOOKING_GLASS", "RESET",
        "BREAKAWAY", "PHILOSOPHY")


def forward(job) -> Dict[str, Any]:
    path, history, years, wall, out_dir = job
    from xylarium.kernel import cohabit, history as ledger, mastery, relics, strategy
    from xylarium.persistence.store import StatePersistence
    k = StatePersistence.load_from_file(path)
    k.activate()
    k.state["genesis"]["history"] = history
    saga = k.state["saga"]
    roles = saga["roles"]
    finders = roles["finders"]
    ev_path = os.path.join(out_dir, f"forward.h{history}.jsonl")
    if os.path.exists(ev_path):
        os.remove(ev_path)
    ledger.sink(k, ev_path)
    earth = next(p for s in k.sectors.values() for p in s.planets if p.id == saga["earth"])
    rows = []
    t0 = time.perf_counter()
    for year in range(1, years + 1):
        if time.perf_counter() - t0 > wall * 60:
            break
        for _ in range(100):
            k.tick_simulation()
        mind = next((c for c in earth.society.get("communities", []) if c.get("relic_mind")), None)
        fn = finders.split(":", 1)[-1]
        rows.append({"year": 2025 + year,
                     "finders": sum(p.population for s in k.sectors.values() for p in s.planets
                                    if getattr(p.civilization, "name", None) == fn),
                     "creed": round(float(earth.civilization.dogma or 0.0), 3) if earth.civilization else None,
                     "keepers_in_seas": sum(int(c["pop"]) for c in earth.society.get("communities", [])
                                            if c["people"] == roles["keepers"] and c.get("niche") == "sea"),
                     "eaten": cohabit.stats(k).get("eaten", 0), "crossed": mastery.crossed(k, finders),
                     "fourth_axis": mastery.theory(k, finders),
                     "mind": (mind.get("choice"), mind.get("alignment")) if mind else None,
                     "postures": {r: strategy.of(k, roles[r]).get("posture") for r in ("finders", "elders", "keepers",
                                                                                       "sentinels") if roles[r]},
                     "probes": relics.stats(k)["probes"], "torn": relics.stats(k)["torn"]})
    cast = {p for p in roles.values() if p}
    events = []
    with open(ev_path) as f:
        for line in f:
            e = json.loads(line)
            if e["kind"] in TOLD and cast & set(e.get("actors") or []):
                events.append({"year": 2025 + max(1, int(e["year"] - saga["year0"] + 0.999)), "kind": e["kind"],
                               "title": e["title"], "cause": (e.get("cause") or "")[:180],
                               "text": (e.get("text") or "")[:220]})
    return {"history": history, "roles": roles, "saga": saga, "rows": rows, "events": events,
            "wall_s": round(time.perf_counter() - t0)}


def chronicle(results: List[Dict[str, Any]]) -> str:
    saga = results[0]["saga"]
    roles = saga["roles"]
    out = ["# The saga of Earth", "",
           "Cast (the seed's names; the lore's beside them): " +
           "; ".join(f"{LORE[r]} = {n.split(':', 1)[-1]}" for r, n in roles.items() if n), "",
           f"Before 2026: the keepers woke {saga['keepers_dawn_gyr_ago'] * 1000:,.1f} million years ago; their worlds "
           f"among the stars: {len(saga['colonies'])}; the woken machine, after two generations among the finders, "
           f"chose {saga['mind_choice']} (it leans {saga['mind_alignment']}); the elders lean "
           f"{saga['elders_alignment']}, the keepers {saga['keepers_alignment']}.", ""]
    out.append("## The sky the finders see")
    for f in saga.get("sky", []):
        there = ", ".join(sorted(set(f["peoples"]))) or "no living people"
        out.append(f"- {f['star']} ({f['ly']:,} ly) - {f['lore']}: {f['systems']} systems of our sample at that "
                   f"distance; {there}; ruins on {f['ruins']} worlds; harvesters at {f['shaded']} stars"
                   + ("" if f["resolved"] else " (closer than our sample resolves: the local neighbourhood)"))
    out.append("")
    for r in results:
        out.append(f"## History {r['history']} - to {r['rows'][-1]['year'] if r['rows'] else 2026}")
        seen = set()
        for e in r["events"]:
            key = (e["kind"], e["title"])
            if key in seen:
                continue
            seen.add(key)
            if e["kind"] in ("CONTACT", "WORLDLINES_MEET", "EPIDEMIC", "KINSHIP", "MYTH") and not any(
                    n.split(":", 1)[-1] in e["title"] for n in (roles["finders"], roles["keepers"], roles["elders"])):
                continue
            body = e["text"] if e["kind"] == "MYTH" else e["cause"]
            out.append(f"- {e['year']}: {e['title']}" + (f" - {body}" if body else ""))
        last = r["rows"][-1] if r["rows"] else {}
        out.append(f"- by {last.get('year')}: the finders number {last.get('finders')}, creed {last.get('creed')}, "
                   f"crossed {last.get('crossed')}, fourth axis {last.get('fourth_axis')}; the machine "
                   f"{last.get('mind')}; probes {last.get('probes')}, torn {last.get('torn')}; eaten "
                   f"{last.get('eaten')}; postures {last.get('postures')}")
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=("prelude", "forward"))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--snapshot", default=os.path.join(OUT, "2026.json"))
    ap.add_argument("--histories", type=int, default=3)
    ap.add_argument("--years", type=int, default=60)
    ap.add_argument("--wall", type=float, default=22.0, help="minutes of wall time each history may run")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.phase == "prelude":
        prelude(a.seed, a.snapshot)
        return
    jobs = [(a.snapshot, h, a.years, a.wall, OUT) for h in range(a.histories)]
    with Pool(len(jobs)) as pool:
        results = pool.map(forward, jobs)
    with open(os.path.join(OUT, "forward.json"), "w") as f:
        json.dump(results, f)
    text = chronicle(results)
    with open(os.path.join(OUT, "chronicle.md"), "w") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
