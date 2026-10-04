"""
Earth as a test: our system in 2026 under every law the engine holds, with the steward's story set as initial
conditions - and many histories of it, to see what the laws make of it.

  python3 tools/earth_test.py --years 60 --histories 4            # every world of the experiment
  python3 tools/earth_test.py --years 60 --histories 2 --only story

THE STORY (initial conditions, not claims - none of it is science). The story's peoples are ROLES; every name is
the seed's own (cosmos._name), so each universe tells its own mythology:
  - the ELDERS: the oldest of the seed's seven ancients still living and among the stars in our 2026 (other than the
    sentinels) - woken at their own dawn and carried by the annals through their whole history. They kept Mars green
    with wetware minds and machines; a war ~12,000 years ago with the KEEPERS stripped Mars and drove them away. Their
    records still name Mars as their world; Earth is not on their map.
  - the KEEPERS: a water people of Earth's seas who did not leave - they live on, unseen, and keep the finders as
    food, tending their herd's creed so it asks no questions.
  - the STRANDED: 200 of the elders' minds left on Earth in the war - carried minds, too few to be a people, living
    among the finders and teaching what they can understand.
  - the elders' works in Earth's ancient lands: their mathematics of the fourth axis, their wetware (genetics,
    synthesis), and a mind asleep in a machine.
  - the SENTINELS: the galaxy's first people, alive in 2026 by the seed's own laws, keeping a hidden outpost under the
    ice of the system's ocean moon: they watch, unseen. Their own sun is dying.
  - the FINDERS (Earth's people): radio, fission, computation, networks, cyber, medicine, orbit, robotics; mathematics
    to the third axis (Einstein) and no further.

Every law then acts on its own: the finders dig up the relics (holding what they do not understand), the relic mind
wakes in their machines and chooses what they are to it, the finders may push matter toward light (and ring the
fold), the elders steer by their records, the keepers eat and tend the creed, the stranded teach, the sentinels
watch. The worlds of the experiment remove one piece of the story each; the histories redraw only the minds' chance
(scheduler: another history of one universe).
"""

import argparse
import copy
import json
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

WAR_YEARS_AGO = 12_000
HUMANS_2026 = 8_000_000_000
HUMAN_CAPS = ("radio", "fission", "computation", "networks", "cyber", "medicine", "orbit", "robotics")
HUMAN_STAGES = ("forage", "farm", "state", "works", "yards")
STRANDED = 200
ANCIENTS = 7                    # the seed's first minds: the galaxy's ancients
RELIC_CAPS = ("genetics", "synthesis")
WORLDS = {
    "story": {},
    "no_predation": {"predation": False},
    "no_relic": {"relic": False},
    "no_stranded": {"stranded": False},
    "no_sentinels": {"sentinels": False},
}
WATCHED = ("CONTACT", "UPLIFT", "KINSHIP", "KIN_EATEN", "WAR", "RAID", "CONQUEST", "SUBJUGATION", "GALACTIC_WAR",
           "DOMINION", "FIRST_SIGNAL", "WORLDLINES_MEET", "REDISCOVERY", "CAPABILITY", "FTL_CROSSED",
           "TRANSFER_EMBRACED", "TRANSFER_FORBIDDEN", "RELIC_FOUND", "RELIC_MIND_WAKES", "RELIC_MIND_EMBODIED",
           "RELIC_MIND_GUARDS", "RELIC_MIND_CALLS", "RELIC_MIND_SILENT", "NULL_FLOW_PROBE", "FOLD_TORN",
           "FOLD_RANG", "PROVEN", "RETURN", "STRIFE", "EPIDEMIC", "EXTINCTION")


def _lift(k: Any, who: str, caps, stages, stocks=None, vocab=None, gauge=None) -> None:
    from xylarium.kernel import annals, intellect, knowledge, technology
    held = technology.stats(k)["of"].setdefault(who, {})
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


def build(seed: int, world: Dict[str, Any], history: int) -> Dict[str, Any]:
    import earth_run
    from xylarium.kernel import (archaeology, biosphere, clocks, cosmos, creation, intellect, interior, kinship,
                                 mastery, memory, relations)
    from xylarium.kernel import history as ledger
    from xylarium.kernel.civilization import Civilization
    from xylarium.kernel.engine import GameKernel
    predation, relic, stranded_on, sentinels_on = (world.get(x, True) for x in
                                                   ("predation", "relic", "stranded", "sentinels"))
    k = GameKernel(seed=seed, genesis="cosmic:neighbourly")
    k.activate()
    sd = creation.universe(k)
    found = earth_run.sol_like(sd)
    now = found["born"] + interior.SOLAR_AGE_GYR
    st = cosmos.stats(k)
    k.cycle_count = int((now - st["epoch0"]) * 1e9 / cosmos.ruler(k) * 100)
    k.cycle_count -= k.cycle_count % 100
    # every mind the seed woke before our 2026 wakes at its own dawn: the annals carry it through its deep history
    # (its eras, its crossing, its falls, its deeds) to our present, under the same laws as everyone
    past = [m for m in creation.schedule(sd)["minds"] if m["epoch"] <= now]
    for m in past:
        if cosmos.arise(k, m):
            sid_m = cosmos.sector_of_slot(k, tuple(m["cell"]), m["k"])
            pl = k.sectors[sid_m].planets[int(m["w"])]
            pl.society["arisen"]["epoch"] = float(m["epoch"])
    st["minds"], st["next"] = [], 0
    later = [m for m in creation.schedule(sd)["minds"] if m["epoch"] > now]
    st["last"] = None if not later else [now, later[0]["cell"], later[0]["k"], later[0]["w"]]
    cosmos.arise(k, {"cell": found["cell"], "k": found["k"], "w": found["w"], "epoch": now, "metab": "biotic",
                     "steps": []})
    sid = cosmos.sector_of_slot(k, tuple(found["cell"]), found["k"])
    sun = k.sectors[sid]
    earth = sun.planets[found["w"]]
    humans = f"civ:{earth.civilization.name}"
    earth.society["way"] = "state"
    earth.citadel_level = max(earth.citadel_level, 4)
    earth.population = int(min(HUMANS_2026, max(1, biosphere.carrying_capacity(k, earth))))
    einstein = list(intellect.BASE) + [c for c, r in intellect.RANK_OF.items() if r <= 3]
    _lift(k, humans, HUMAN_CAPS, HUMAN_STAGES, vocab=einstein)
    earth.society["arisen"] = {"epoch": now, "cycle": k.cycle_count}
    mars = next((p for p in sun.planets[found["w"] + 1:] if p.planet_type not in ("GAS_GIANT", "ROGUE")
                 and getattr(p, "moon_of", None) is None), None)
    europa = next((p for p in sun.planets if p.planet_type in ("ICE", "OCEANIC") and p is not earth), None) or \
        next((p for p in reversed(sun.planets) if p is not earth and p is not mars), None)
    # the deep years: the annals carry every woken people from its dawn to our present
    from xylarium.kernel import annals
    annals.season(k)
    # the sentinels: the seed's first people; the elders: the oldest of its other ancients (its first ANCIENTS
    # minds) still living and among the stars in our 2026 - away near the galaxy's heart, beyond Sol's lanes
    living = relations._peoples(k)
    first = creation.schedule(sd)["minds"][:ANCIENTS]

    def holder_of(m):
        sid_m = cosmos.sector_of_slot(k, tuple(m["cell"]), m["k"])
        pl = k.sectors[sid_m].planets[int(m["w"])] if sid_m in k.sectors else None
        return f"civ:{pl.civilization.name}" if pl is not None and pl.civilization is not None else None
    sentinel = holder_of(first[0])
    ann, far = None, None
    for m in first:
        sid_m = cosmos.sector_of_slot(k, tuple(m["cell"]), m["k"])
        pl = k.sectors.get(sid_m).planets[int(m["w"])] if sid_m in k.sectors else None
        who = f"civ:{pl.civilization.name}" if pl is not None and pl.civilization is not None else None
        if who and who != sentinel and who in living and mastery.crossed(k, who):
            ann, far = who, max(living[who], key=lambda p: p.population)
            break
    if ann is None:                                    # none crossed and alive: the oldest living people serves
        for m in first:
            sid_m = cosmos.sector_of_slot(k, tuple(m["cell"]), m["k"])
            pl = k.sectors.get(sid_m).planets[int(m["w"])] if sid_m in k.sectors else None
            who = f"civ:{pl.civilization.name}" if pl is not None and pl.civilization is not None else None
            if who and who != sentinel and who in living:
                ann, far = who, max(living[who], key=lambda p: p.population)
                mastery.stats(k)["crossed"][ann] = k.cycle_count
                break
    elders = {"metab": biosphere.metabolism_of(k, far), "civ": far.civilization.to_dict(),
                "vocab": [str(x) for x in intellect.vocabulary(k, ann)], "name": ann}
    # the war, 12,000 years ago - the ledger's truth, dated in deep time
    war_epoch = now - WAR_YEARS_AGO / 1e9
    # the keepers and the stranded: named by the seed, as every people is
    keepers = "civ:" + cosmos._name(k, {"cell": found["cell"], "k": found["k"], "w": 1000})
    stranded = "civ:" + cosmos._name(k, {"cell": found["cell"], "k": found["k"], "w": 1001})
    en, kn = ann.split(":", 1)[-1], keepers.split(":", 1)[-1]
    war = ledger.event(k, "GALACTIC_WAR", f"War between the {en} and the {kn}", actors=[ann, keepers],
                       planet=mars or earth, magnitude=10 ** 8, cause=f"scenario: {WAR_YEARS_AGO:,} years before 2026",
                       data={"epoch": war_epoch, "scenario": True})
    memory.season(k)
    if mars is not None:
        ledger.event(k, "WORLD_STRIPPED", f"{mars.name} is stripped in the war", actors=[ann, keepers],
                     planet=mars, cause="scenario: the war took its air and seas", data={"epoch": war_epoch})
        mars.society["atmosphere"] = 0.01
        # what the elders keep of it: the world they kept green - their records name it, not Earth
        memory._write(k, ann, far, {"id": None, "kind": "SETTLEMENT", "planet": mars.id,
                                    "title": f"the green world we kept ({mars.name})", "year": None, "actors": [ann]})
        memory.stats(k)["left"][str(mars.id)] = [
            {"people": en, "k": "SETTLEMENT", "title": "the green world we kept", "year": None,
             "f": 1.0, "truth": 1.0, "substrate": "grown wetware in the rock", "myth": False, "told": None}]
    plans = [[f, h] for _, f, h in kinship.prey_plans(k, ann, far)]
    # the elders' works in Earth's ancient lands: the fourth axis, their wetware, and a mind asleep
    if relic:
        earth.ruins = archaeology.bury(earth, archaeology._new_ruins(
            ann.split(":", 1)[-1], "wetware", elders["metab"], "ANCIENT", 9, [], "the time before the flood",
            k.cycle_count, 3,
            earth.currency, 0, __import__("random").Random(seed)))
        earth.ruins["relics"] = {
            "makers": ann.split(":", 1)[-1], "crystals": ["hyper_flip", "hyper_cycle"], "caps": list(RELIC_CAPS),
            "mind": {"name": f"{ann} Mind", "metab": elders["metab"],
                     "alignment": float(elders["civ"].get("alignment") or 0.0),
                     "vocab": [str(intellect.norm(x)) for x in elders["vocab"]], "prey_plans": plans}}
    # the keepers: in Earth's seas, unseen - and, in the story, keeping the finders as food
    earth.society.setdefault("communities", []).append(
        {"people": keepers, "metab": "biotic", "niche": "sea", "pop": creation.VIABLE,
         "traits": {"form": "swimming", "medium": "under the sea"}, **({"prey": humans} if predation else {})})
    # the stranded: 200 of the elders' minds, left among the finders, carried, teaching
    if stranded_on:
        earth.society["communities"].append(
            {"people": stranded, "metab": elders["metab"], "niche": "surface", "pop": STRANDED,
             "arts": ["materials", "information", "energy"],                 # metal-working, the sky, writing
             "carried": True, "vocab": [str(intellect.norm(x)) for x in elders["vocab"]],
             "alignment": float(elders["civ"].get("alignment") or 0.0)})
    # the sentinels: their own world as the seed has it, and a hidden outpost of carried minds under the moon's ice
    tur = sentinel
    if sentinels_on and tur and europa is not None and tur in relations._peoples(k):
        europa.society.setdefault("communities", []).append(
            {"people": tur, "metab": "biotic", "niche": "ice", "pop": creation.VIABLE, "carried": True,
             "silent": True, "vocab": [str(x) for x in intellect.vocabulary(k, tur)]})
    # what the humans keep of it all: the drowned land, as myth
    memory._write(k, humans, earth, {"id": war.get("id"), "kind": "FLOOD", "title": "the drowned land",
                                     "year": None, "actors": [humans], "data": {"epoch": war_epoch}}, f0=1.0)
    for who, home in ((humans, earth), (ann, far)):
        clocks.begin(k, who, home)
    k.state["genesis"]["history"] = history          # from here on, this history's own chance
    return {"kernel": k, "humans": humans, "earth": earth, "mars": mars, "europa": europa, "elders_world": far,
            "roles": {"finders": humans, "elders": ann, "keepers": keepers, "stranded": stranded,
                      "sentinels": sentinel, "relic_mind": f"{ann} Mind"}}


def run(job) -> Dict[str, Any]:
    name, world, history, seed, years, out_dir, wall = job
    from xylarium.kernel import cohabit, history as ledger, mastery, relics, strategy
    w = build(seed, world, history)
    k, humans, earth = w["kernel"], w["humans"], w["earth"]
    path = os.path.join(out_dir, f"{name}.h{history}.jsonl")
    if os.path.exists(path):
        os.remove(path)
    ledger.sink(k, path)
    tick = k.tick_simulation
    hn = humans.split(":", 1)[-1]
    year0 = k.cycle_count / 100.0
    rows = []
    t0 = time.perf_counter()
    for year in range(1, years + 1):
        if wall and time.perf_counter() - t0 > wall * 60:
            break                                       # the steward's budget of wall time is spent
        for _ in range(100):
            tick()
        mind = next((c for c in earth.society.get("communities", []) if c.get("relic_mind")), None)
        rows.append({"year": year,
                     "humans": sum(p.population for s in k.sectors.values() for p in s.planets
                                   if getattr(p.civilization, "name", None) == hn),
                     "dogma": round(float(earth.civilization.dogma or 0.0), 3) if earth.civilization else None,
                     "atlanteans": sum(int(c["pop"]) for c in earth.society.get("communities", [])
                                       if c["people"] == w["roles"]["keepers"]),
                     "eaten": cohabit.stats(k).get("eaten", 0), "crossed": mastery.crossed(k, humans),
                     "fourth_axis": mastery.theory(k, humans), "mind": mind.get("choice") if mind else None,
                     "postures": {p.split(":")[-1]: strategy.of(k, p).get("posture")
                                  for p in (humans, w["roles"]["elders"], w["roles"]["sentinels"]) if p}})
    events = []
    peoples = {p for p in w["roles"].values() if p}
    with open(path) as f:
        for line in f:
            e = json.loads(line)
            if e["kind"] in WATCHED and peoples & set(e.get("actors") or []):
                events.append({"year": round(e["year"] - year0, 2), "kind": e["kind"], "title": e["title"],
                               "cause": (e.get("cause") or "")[:160]})
    return {"world": name, "history": history, "humans": humans, "roles": w["roles"],
            "elders_alignment": w["elders_world"].civilization.alignment if w["elders_world"].civilization else None,
            "rows": rows, "events": events,
            "relics": relics.summary(k), "wall_s": round(time.perf_counter() - t0)}


def report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = {}
    for name in WORLDS:
        rs = [r for r in results if r["world"] == name]
        if not rs:
            continue

        def first(kind, r):
            return next((e["year"] for e in r["events"] if e["kind"] == kind), None)
        out[name] = {
            "histories": len(rs),
            "roles": rs[0]["roles"],
            "elders_alignment": [r["elders_alignment"] for r in rs],
            "mind_choice": dict(Counter(str(r["rows"][-1]["mind"]) for r in rs)),
            "crossed": sum(1 for r in rs if r["rows"][-1]["crossed"]),
            "crossed_year": [first("FTL_CROSSED", r) for r in rs],
            "probes": [sum(1 for e in r["events"] if e["kind"] == "NULL_FLOW_PROBE") for r in rs],
            "fold_rang_year": [first("FOLD_RANG", r) for r in rs],
            "torn": [r["relics"]["torn"] for r in rs],
            "elders_return": [[e["title"] for e in r["events"] if e["kind"] == "RETURN"][:2] for r in rs],
            "humans_end": [r["rows"][-1]["humans"] for r in rs],
            "dogma_end": [r["rows"][-1]["dogma"] for r in rs],
            "eaten": [r["rows"][-1]["eaten"] for r in rs],
            "atlanteans_end": [r["rows"][-1]["atlanteans"] for r in rs],
            "kinds": dict(sum((Counter(e["kind"] for e in r["events"]) for r in rs), Counter())),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--years", type=int, default=60)
    ap.add_argument("--histories", type=int, default=4)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--wall", type=float, default=0.0, help="minutes of wall time each history may run (0: all years)")
    ap.add_argument("--out", default=os.path.join(ROOT, "runs/earth_test"))
    ap.add_argument("--only", default="", choices=("",) + tuple(WORLDS))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    names = [a.only] if a.only else list(WORLDS)
    jobs = [(n, WORLDS[n], h, a.seed, a.years, a.out, a.wall) for n in names for h in range(a.histories)]
    with Pool(min(a.workers, len(jobs))) as pool:
        results = pool.map(run, jobs)
    with open(os.path.join(a.out, "results.json"), "w") as f:
        json.dump(results, f)
    summary = report(results)
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))
    with open(os.path.join(a.out, "chronicle.md"), "w") as f:
        f.write(chronicle(results))


LORE = {"finders": "humanity", "elders": "the Anunnaki", "keepers": "the Atlanteans", "stranded": "the Watchers",
        "sentinels": "the ancients under Europa's ice", "relic_mind": "the woken machine"}
TOLD = ("RELIC_FOUND", "RELIC_MIND_WAKES", "RELIC_MIND_EMBODIED", "RELIC_MIND_CALLS", "RELIC_MIND_GUARDS",
        "RELIC_MIND_SILENT", "NULL_FLOW_PROBE", "FOLD_TORN", "FOLD_RANG", "PROVEN", "FTL_CROSSED", "RETURN",
        "WORLDLINES_MEET", "CONTACT", "KIN_EATEN", "KINSHIP", "STRIFE", "EPIDEMIC", "GALACTIC_WAR", "DOMINION",
        "CAPABILITY", "TRANSFER_EMBRACED", "TRANSFER_FORBIDDEN")


def chronicle(results: List[Dict[str, Any]]) -> str:
    """Each history told year by year, the seed's names beside the story's roles (2026 is year 1)."""
    out = ["# Chronicles of the Earth test", ""]
    for r in results:
        roles = r["roles"]
        cast = {name: role for role, name in roles.items() if name}
        out.append(f"## {r['world']}, history {r['history']} - {len(r['rows'])} years")
        out.append("Cast: " + "; ".join(f"{LORE.get(role, role)} = {name.split(':', 1)[-1]}"
                                        for role, name in roles.items() if name))
        seen = set()
        for e in r["events"]:
            if e["kind"] not in TOLD:
                continue
            key = (e["kind"], e["title"])
            if key in seen or (e["kind"] in ("CONTACT", "WORLDLINES_MEET", "DOMINION", "EPIDEMIC")
                               and not any(n.split(":", 1)[-1] in e["title"] for n in
                                           (roles["finders"], roles["elders"], roles["keepers"]))):
                continue
            seen.add(key)
            out.append(f"- {2025 + max(1, int(e['year'] + 0.999))}: {e['title']}" +
                       (f" - {e['cause']}" if e["cause"] else ""))
        last = r["rows"][-1] if r["rows"] else {}
        out.append(f"- by {2025 + len(r['rows'])}: {LORE['finders']} number {last.get('humans')}, their creed "
                   f"{last.get('dogma')}, crossed {last.get('crossed')}; the woken machine chose "
                   f"{last.get('mind')}; {last.get('eaten')} eaten")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    main()
