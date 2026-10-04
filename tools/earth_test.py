"""
Earth as a test: our system in 2026 under every law the engine holds, with the steward's story set as initial
conditions - and many histories of it, to see what the laws make of it.

  python3 tools/earth_test.py --years 60 --histories 4            # every world of the experiment
  python3 tools/earth_test.py --years 60 --histories 2 --only story

THE STORY (initial conditions, not claims - none of it is science):
  - Mars was kept green by the ANUNNAKI, a people whose minds and machines are wetware; a war ~12,000 years ago with
    the ATLANTEANS (a water people of Earth's seas) stripped Mars and drove the Anunnaki away. Their records still
    name Mars as their world; Earth is not on their map. (The Anunnaki are the oldest of the seed's seven ancients
    still living and among the stars in our 2026, other than the Turenol - woken at their own dawn and carried by the
    annals through their whole history; "Anunnaki" is the story's name for them.)
  - The Atlanteans did not leave: they live on in Earth's seas, unseen, and keep the humans as food - tending their
    herd's creed so it asks no questions.
  - 200 of the Anunnaki's minds were stranded on Earth in the war (the WATCHERS): carried minds, too few to be a
    people, living among the humans and teaching what they can understand.
  - The Anunnaki left their works in Earth's ancient lands: their mathematics of the fourth axis, their wetware
    (genetics, synthesis), and a mind asleep in a machine.
  - The TURENOL, the galaxy's first people, alive in 2026 by the seed's own laws, keep a hidden outpost under the ice
    of the system's ocean moon (Europa): they watch, unseen. Their own sun is dying.
  - The humans: radio, fission, computation, networks, cyber, medicine, orbit, robotics; mathematics to the third
    axis (Einstein) and no further.

Every law then acts on its own: the humans dig up the relics (holding what they do not understand), the relic mind
wakes in their machines and chooses what the humans are to it, the humans may push matter toward light (and ring
the fold), the Anunnaki steer by their records, the Atlanteans eat and tend the creed, the watchers teach, the
Turenol watch. The worlds of the experiment remove one piece of the story each; the histories redraw only the
minds' chance (scheduler: another history of one universe).
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
WATCHERS = 200
ANCIENTS = 7                    # the seed's first minds: the galaxy's ancients
RELIC_CAPS = ("genetics", "synthesis")
WORLDS = {
    "story": {},
    "no_predation": {"predation": False},
    "no_relic": {"relic": False},
    "no_watchers": {"watchers": False},
    "no_turenol": {"turenol": False},
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
    predation, relic, watchers, turenol = (world.get(x, True) for x in ("predation", "relic", "watchers", "turenol"))
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
    # the Anunnaki: the oldest of the seed's ancients (its first ANCIENTS minds) still living and among the stars in
    # our 2026, other than the Turenol - away near the galaxy's heart, beyond Sol's lanes. Their name is the story's.
    living = relations._peoples(k)
    first = creation.schedule(sd)["minds"][:ANCIENTS]
    ann, far = None, None
    for m in first:
        sid_m = cosmos.sector_of_slot(k, tuple(m["cell"]), m["k"])
        pl = k.sectors.get(sid_m).planets[int(m["w"])] if sid_m in k.sectors else None
        who = f"civ:{pl.civilization.name}" if pl is not None and pl.civilization is not None else None
        if who and who != "civ:Turenol" and who in living and mastery.crossed(k, who):
            ann, far = who, max(living[who], key=lambda p: p.population)
            break
    if ann is None:                                    # none crossed and alive: the oldest living people serves
        for m in first:
            sid_m = cosmos.sector_of_slot(k, tuple(m["cell"]), m["k"])
            pl = k.sectors.get(sid_m).planets[int(m["w"])] if sid_m in k.sectors else None
            who = f"civ:{pl.civilization.name}" if pl is not None and pl.civilization is not None else None
            if who and who != "civ:Turenol" and who in living:
                ann, far = who, max(living[who], key=lambda p: p.population)
                mastery.stats(k)["crossed"][ann] = k.cycle_count
                break
    anunnaki = {"metab": biosphere.metabolism_of(k, far), "civ": far.civilization.to_dict(),
                "vocab": [str(x) for x in intellect.vocabulary(k, ann)], "name": ann}
    # the war, 12,000 years ago - the ledger's truth, dated in deep time
    war_epoch = now - WAR_YEARS_AGO / 1e9
    war = ledger.event(k, "GALACTIC_WAR", "War between the Anunnaki and the Atlanteans", actors=[ann, "civ:Atlanteans"],
                       planet=mars or earth, magnitude=10 ** 8, cause=f"scenario: {WAR_YEARS_AGO:,} years before 2026",
                       data={"epoch": war_epoch, "scenario": True})
    memory.season(k)
    if mars is not None:
        ledger.event(k, "WORLD_STRIPPED", f"{mars.name} is stripped in the war", actors=[ann, "civ:Atlanteans"],
                     planet=mars, cause="scenario: the war took its air and seas", data={"epoch": war_epoch})
        mars.society["atmosphere"] = 0.01
        # what the Anunnaki keep of it: the world they kept green - their records name it, not Earth
        memory._write(k, ann, far, {"id": None, "kind": "SETTLEMENT", "planet": mars.id,
                                    "title": f"the green world we kept ({mars.name})", "year": None, "actors": [ann]})
        memory.stats(k)["left"][str(mars.id)] = [
            {"people": "Anunnaki", "k": "SETTLEMENT", "title": "the green world we kept", "year": None,
             "f": 1.0, "truth": 1.0, "substrate": "grown wetware in the rock", "myth": False, "told": None}]
    plans = [[f, h] for _, f, h in kinship.prey_plans(k, ann, far)]
    # the Anunnaki's works in Earth's ancient lands: the fourth axis, their wetware, and a mind asleep
    if relic:
        earth.ruins = archaeology.bury(earth, archaeology._new_ruins(
            ann.split(":", 1)[-1], "wetware", anunnaki["metab"], "ANCIENT", 9, [], "the time before the flood",
            k.cycle_count, 3,
            earth.currency, 0, __import__("random").Random(seed)))
        earth.ruins["relics"] = {
            "makers": ann.split(":", 1)[-1], "crystals": ["hyper_flip", "hyper_cycle"], "caps": list(RELIC_CAPS),
            "mind": {"name": f"{ann} Mind", "metab": anunnaki["metab"],
                     "alignment": float(anunnaki["civ"].get("alignment") or 0.0),
                     "vocab": [str(intellect.norm(x)) for x in anunnaki["vocab"]], "prey_plans": plans}}
    # the Atlanteans: in Earth's seas, unseen - and, in the story, keeping the humans as food
    earth.society.setdefault("communities", []).append(
        {"people": "civ:Atlanteans", "metab": "biotic", "niche": "sea", "pop": creation.VIABLE,
         "traits": {"form": "swimming", "medium": "under the sea"}, **({"prey": humans} if predation else {})})
    # the watchers: 200 of the Anunnaki's minds, stranded among the humans, carried, teaching
    if watchers:
        earth.society["communities"].append(
            {"people": "civ:Watchers", "metab": anunnaki["metab"], "niche": "surface", "pop": WATCHERS,
             "carried": True, "vocab": [str(intellect.norm(x)) for x in anunnaki["vocab"]],
             "alignment": float(anunnaki["civ"].get("alignment") or 0.0)})
    # the Turenol: their own world as the seed has it, and a hidden outpost of carried minds under Europa's ice
    tur = "civ:Turenol"
    if turenol and europa is not None and tur in relations._peoples(k):
        europa.society.setdefault("communities", []).append(
            {"people": tur, "metab": "biotic", "niche": "ice", "pop": creation.VIABLE, "carried": True,
             "silent": True, "vocab": [str(x) for x in intellect.vocabulary(k, tur)]})
    # what the humans keep of it all: the drowned land, as myth
    memory._write(k, humans, earth, {"id": war.get("id"), "kind": "FLOOD", "title": "the drowned land",
                                     "year": None, "actors": [humans], "data": {"epoch": war_epoch}}, f0=1.0)
    for who, home in ((humans, earth), (ann, far)):
        clocks.begin(k, who, home)
    k.state["genesis"]["history"] = history          # from here on, this history's own chance
    return {"kernel": k, "humans": humans, "earth": earth, "mars": mars, "europa": europa, "anunnaki": far,
            "ann": ann}


def run(job) -> Dict[str, Any]:
    name, world, history, seed, years, out_dir = job
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
        for _ in range(100):
            tick()
        mind = next((c for c in earth.society.get("communities", []) if c.get("relic_mind")), None)
        rows.append({"year": year,
                     "humans": sum(p.population for s in k.sectors.values() for p in s.planets
                                   if getattr(p.civilization, "name", None) == hn),
                     "dogma": round(float(earth.civilization.dogma or 0.0), 3) if earth.civilization else None,
                     "atlanteans": sum(int(c["pop"]) for c in earth.society.get("communities", [])
                                       if c["people"] == "civ:Atlanteans"),
                     "eaten": cohabit.stats(k).get("eaten", 0), "crossed": mastery.crossed(k, humans),
                     "fourth_axis": mastery.theory(k, humans), "mind": mind.get("choice") if mind else None,
                     "postures": {p.split(":")[-1]: strategy.of(k, p).get("posture")
                                  for p in (humans, w["ann"], "civ:Turenol")}})
    events = []
    peoples = {humans, "civ:Atlanteans", w["ann"], "civ:Turenol", "civ:Watchers", f"{w['ann']} Mind"}
    with open(path) as f:
        for line in f:
            e = json.loads(line)
            if e["kind"] in WATCHED and peoples & set(e.get("actors") or []):
                events.append({"year": round(e["year"] - year0, 2), "kind": e["kind"], "title": e["title"],
                               "cause": (e.get("cause") or "")[:160]})
    return {"world": name, "history": history, "humans": humans, "anunnaki": w["ann"],
            "anunnaki_alignment": w["anunnaki"].civilization.alignment if w["anunnaki"].civilization else None,
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
            "anunnaki_are": sorted({str(r["anunnaki"]) for r in rs}),
            "anunnaki_alignment": [r["anunnaki_alignment"] for r in rs],
            "mind_choice": dict(Counter(str(r["rows"][-1]["mind"]) for r in rs)),
            "crossed": sum(1 for r in rs if r["rows"][-1]["crossed"]),
            "crossed_year": [first("FTL_CROSSED", r) for r in rs],
            "probes": [sum(1 for e in r["events"] if e["kind"] == "NULL_FLOW_PROBE") for r in rs],
            "fold_rang_year": [first("FOLD_RANG", r) for r in rs],
            "torn": [r["relics"]["torn"] for r in rs],
            "anunnaki_return": [[e["title"] for e in r["events"] if e["kind"] == "RETURN"][:2] for r in rs],
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
    ap.add_argument("--out", default=os.path.join(ROOT, "runs/earth_test"))
    ap.add_argument("--only", default="", choices=("",) + tuple(WORLDS))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    names = [a.only] if a.only else list(WORLDS)
    jobs = [(n, WORLDS[n], h, a.seed, a.years, a.out) for n in names for h in range(a.histories)]
    with Pool(min(a.workers, len(jobs))) as pool:
        results = pool.map(run, jobs)
    with open(os.path.join(a.out, "results.json"), "w") as f:
        json.dump(results, f)
    summary = report(results)
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
