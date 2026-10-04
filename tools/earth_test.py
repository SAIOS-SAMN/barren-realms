"""
Earth as a test: our system in 2026 under every law the engine holds, with the data points the steward gives - and
the ancients of the galaxy's core beside it. What do their councils choose?

  python3 tools/earth_test.py --years 30                       # both worlds of the counterfactual, side by side
  python3 tools/earth_test.py --years 30 --only predation      # one of them

The data points (scenario initial conditions, not claims): Mars was green; Earth was home to a water-dwelling
people before ours (the Atlanteans), who did not leave - they live on in Earth's seas and keep the humans as food;
a war between them and the core's ancients was fought in this sector ~12,000 years ago, which stripped Mars. Our
own people stands where it stands in 2026: radio, fission, computation, networks, cyber, medicine; no genetics yet;
its physics stalled since Einstein (its mathematics holds no fourth axis, so it cannot cross).

The ancients are not invented: they are the seed's own first peoples, taken whole from the live run (their bodies,
creed, alignment, knowledge, capabilities and memory) and set as the war's victors on the worlds they hold in this
sector. Nothing they do is scripted: contact, uplift, kinship, pacts, raids and wars are their councils' choices,
under the same laws as every other people's.

Three worlds are run from the same initial conditions: one where the Atlanteans eat the humans (cohabit.py: a
community that keeps its host as prey takes its diet's share of it), one where they do not, and one where they do
but no ancient holds a world in the sector (the war's victors long gone). What differs is what the predation does,
and what the ancients' presence does.
"""

import argparse
import copy
import json
import os
import sys
import time
from multiprocessing import Pool
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

WAR_YEARS_AGO = 12_000
HUMANS_2026 = 8_000_000_000
HUMAN_CAPS = ("radio", "fission", "computation", "networks", "cyber", "medicine", "orbit")
HUMAN_STAGES = ("forage", "farm", "state", "works", "yards")
ATLANTEANS = None               # the war's remnant in the seas: the fewest that keep a people (creation.VIABLE)
WATCHED = ("CONTACT", "UPLIFT", "SEEDING", "KINSHIP", "KIN_EATEN", "SCHISM", "WAR", "RAID", "CONQUEST",
           "SUBJUGATION", "REBELLION", "REVOLT", "GALACTIC_WAR", "DOMINION", "FEDERATION", "PACT", "FIRST_SIGNAL",
           "WORLDLINES_MEET", "REDISCOVERY", "CAPABILITY", "FTL_CROSSED", "POSTURE", "TRANSFER_FORBIDDEN",
           "TRANSFER_EMBRACED", "MYTH", "PHILOSOPHY", "HURDLE", "EXODUS", "SETTLEMENT", "STRIFE")


def _ancients(snapshot: str) -> Dict[str, Dict[str, Any]]:
    """The seed's first peoples as the live run holds them now."""
    from xylarium.kernel import intellect, knowledge, memory, technology
    from xylarium.persistence.store import StatePersistence
    k = StatePersistence.load_from_file(snapshot)
    out = {}
    for name in ("Turenol", "Umvrine"):
        who = f"civ:{name}"
        worlds = [p for s in k.sectors.values() for p in s.planets
                  if p.population > 0 and getattr(p.civilization, "name", None) == name]
        if not worlds:
            continue
        home = max(worlds, key=lambda p: p.population)
        out[who] = {"civ": home.civilization.to_dict(), "stocks": dict(knowledge.stocks(k, who)),
                    "caps": dict(technology.stats(k)["of"].get(who, {})),
                    "vocab": list(intellect.vocabulary(k, who)), "gauge": dict(intellect.gauge(k, who)),
                    "memory": copy.deepcopy(memory.stats(k)["of"].get(who) or {}),
                    "population": home.population, "worlds": len(worlds), "metab": home.civilization.metabolism}
    return out


def _war_victor(ancients: Dict[str, Dict[str, Any]], history_path: str) -> Optional[str]:
    """The ancient that fought most of the galaxy's wars in the live run is this sector's victor."""
    counts = {w: 0 for w in ancients}
    try:
        with open(history_path) as f:
            for line in f:
                if '"GALACTIC_WAR"' not in line:
                    continue
                e = json.loads(line)
                for a in e.get("actors", []):
                    if a in counts:
                        counts[a] += 1
    except OSError:
        pass
    return max(counts, key=lambda w: (counts[w], w)) if counts else None


def _settle(k: Any, planet: Any, civ_data: Dict[str, Any], population: int) -> str:
    from xylarium.kernel.civilization import Civilization
    planet.civilization = Civilization.from_dict(copy.deepcopy(civ_data))
    planet.population = population
    return f"civ:{planet.civilization.name}"


def _lift(k: Any, who: str, planet: Any, caps, stages, stocks=None, vocab=None, gauge=None) -> None:
    """A people set at where it stands: its capabilities, the stages its history passed, its knowledge."""
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


def build(seed: int, snapshot: str, history_path: str, predation: bool, with_ancients: bool = True) -> Dict[str, Any]:
    """Our system at its 2026, with the steward's data points and the core's ancients."""
    import earth_run
    from xylarium.kernel import (archaeology, clocks, cosmos, creation, history, interior, mastery, memory,
                                 technology)
    from xylarium.kernel.engine import GameKernel
    ancients = _ancients(snapshot)
    victor = _war_victor(ancients, history_path)
    k = GameKernel(seed=seed, genesis="cosmic:neighbourly")
    k.activate()
    sd = creation.universe(k)
    found = earth_run.sol_like(sd)
    now = found["born"] + interior.SOLAR_AGE_GYR
    st = cosmos.stats(k)
    k.cycle_count = int((now - st["epoch0"]) * 1e9 / cosmos.ruler(k) * 100)
    k.cycle_count -= k.cycle_count % 100
    st["minds"], st["next"] = [], 0                       # the galaxy's own later minds wake as the seed has them
    later = [m for m in creation.schedule(sd)["minds"] if m["epoch"] > now]
    st["last"] = None if not later else [now, later[0]["cell"], later[0]["k"], later[0]["w"]]
    line = cosmos.arise(k, {"cell": found["cell"], "k": found["k"], "w": found["w"], "epoch": now,
                            "metab": "biotic", "steps": []})
    sid = cosmos.sector_of_slot(k, tuple(found["cell"]), found["k"])
    sun = k.sectors[sid]
    earth = sun.planets[found["w"]]
    humans = f"civ:{earth.civilization.name}"
    # humans in 2026: a state with works and yards, radio to cyber, no genetics, no fourth axis
    earth.society["way"] = "state"
    earth.citadel_level = max(earth.citadel_level, 4)
    from xylarium.kernel import biosphere
    earth.population = int(min(HUMANS_2026, max(1, biosphere.carrying_capacity(k, earth))))
    from xylarium.kernel import intellect
    einstein = list(intellect.BASE) + [c for c, r in intellect.RANK_OF.items() if r <= 3]   # up to the third axis
    _lift(k, humans, earth, HUMAN_CAPS, HUMAN_STAGES, vocab=einstein)
    earth.society["arisen"] = {"epoch": now, "cycle": k.cycle_count}
    # Mars: the next rocky world out, green once, stripped in the war; the Atlanteans' carved records lie there
    mars = next((p for p in sun.planets[found["w"] + 1:] if p.planet_type not in ("GAS_GIANT", "ROGUE")), None)
    # the ancients: the victor holds a world in the nearest system with one; the other the next
    others = [s for c in [tuple(found["cell"])] for kk in range(creation.SLOTS)
              for s in [cosmos.build_slot(k, c, kk)] if s != sid]
    cosmos._stars(k, others)
    placed = {}
    order = sorted(ancients, key=lambda w: (w != victor, w)) if with_ancients else []
    taken = set()
    for who in order:
        a = ancients[who]
        # the world in this sector that feeds its kind best: its outpost from the war
        fit = [(biosphere.carrying_capacity(k, p, metabolism=a["metab"]), -abs(s - sid), p)
               for s in others for p in k.sectors[s].planets
               if p.population <= 0 and p.id not in taken and p.planet_type not in ("ROGUE",)]
        fit = [f for f in fit if f[0] >= creation.VIABLE]
        if not fit:
            continue
        kk, _, p = max(fit, key=lambda f: (f[0], f[1]))
        taken.add(p.id)
        got = _settle(k, p, a["civ"], int(min(kk, max(creation.VIABLE, a["population"] / max(1, a["worlds"])))))
        _lift(k, got, p, a["caps"], ("forage", "farm", "state", "works", "yards", "crossed"),
              stocks=a["stocks"], vocab=a["vocab"], gauge=a["gauge"])
        p.society["way"] = "state"
        p.citadel_level = max(p.citadel_level, 5)
        p.society["arisen"] = {"epoch": now, "cycle": k.cycle_count}
        mastery.stats(k)["crossed"][got] = k.cycle_count
        if a["memory"]:
            memory.stats(k)["of"][got] = copy.deepcopy(a["memory"])
        placed[got] = p
    victor_now = victor if victor in placed or not with_ancients else next(iter(placed), victor)
    # the war, 12,000 years ago: the ledger's truth, dated in deep time
    war_epoch = now - WAR_YEARS_AGO / 1e9
    war = history.event(k, "GALACTIC_WAR", f"War between the {victor_now.split(':')[-1]} and the Atlanteans",
                        actors=[victor_now, "civ:Atlanteans"], planet=earth,
                        cause=f"scenario: {WAR_YEARS_AGO:,} years before our 2026", magnitude=10 ** 8,
                        data={"epoch": war_epoch, "scenario": True})
    if mars is not None:
        history.event(k, "WORLD_STRIPPED", f"{mars.name} is stripped in the war", actors=[victor_now, "civ:Atlanteans"],
                      planet=mars, cause="scenario: the war took its air and seas", data={"epoch": war_epoch,
                                                                                         "scenario": True})
        mars.society["atmosphere"] = 0.01
        mars.ruins = archaeology.bury(mars, archaeology._new_ruins(
            "Atlanteans", "aquatic", "biotic", "ANCIENT", 7, [], "the green age", k.cycle_count, 3, mars.currency, 0,
            __import__("random").Random(seed)))
        memory.stats(k)["left"][str(mars.id)] = [
            {"people": "Atlanteans", "k": "GALACTIC_WAR", "title": war.get("title", ""), "year": None,
             "f": 1.0, "truth": 1.0, "substrate": "grown shell and reef", "myth": False, "told": None},
            {"people": "Atlanteans", "k": "SETTLEMENT", "title": f"The Atlanteans settle {mars.name}",
             "year": None, "f": 1.0, "truth": 1.0, "substrate": "grown shell and reef", "myth": False, "told": None}]
    # the Atlanteans: alive in Earth's seas, a community beside the humans - their prey, or not
    earth.society.setdefault("communities", []).append(
        {"people": "civ:Atlanteans", "metab": "biotic", "niche": "sea", "pop": ATLANTEANS or creation.VIABLE,
         "traits": {"form": "swimming", "medium": "under the sea", "sense": "heat and pressure"},
         **({"prey": humans} if predation else {})})
    # what the humans keep of it all: the drowned land, as myth
    memory.season(k)
    memory._write(k, humans, earth, {"id": war.get("id"), "kind": "FLOOD", "title": "the drowned land",
                                     "year": None, "actors": [humans], "data": {"epoch": war_epoch}},
                  f0=1.0)
    for who in [humans] + list(placed):
        clocks.begin(k, who, earth if who == humans else placed[who])
    return {"kernel": k, "humans": humans, "earth": earth, "mars": mars, "ancients": placed, "victor": victor_now,
            "arise": line, "found": found}


def run(job) -> Dict[str, Any]:
    name, seed, snapshot, history_path, years, out_dir = job
    from xylarium.kernel import cohabit, contact, guidance, history, kinship, strategy
    w = build(seed, snapshot, history_path, predation=(name != "peace"), with_ancients=(name != "alone"))
    k, humans = w["kernel"], w["humans"]
    path = os.path.join(out_dir, f"{name}.jsonl")
    if os.path.exists(path):
        os.remove(path)
    history.sink(k, path)
    tick = k.tick_simulation
    peoples = {humans, "civ:Atlanteans", *w["ancients"]}
    rows = []
    t0 = time.perf_counter()
    for year in range(1, years + 1):
        for _ in range(100):
            tick()
        fam = contact.stats(k)["familiarity"]
        eaten_now = cohabit.stats(k).get("eaten", 0)
        row = {"year": year, "humans": w["earth"].population,
               "humans_all_worlds": sum(p.population for sec in k.sectors.values() for p in sec.planets
                                        if getattr(p.civilization, "name", None) == humans.split(":", 1)[-1]),
               "eaten_share_per_year": round((eaten_now - (rows[-1]["eaten"] if rows else 0))
                                             / max(1, w["earth"].population), 5),
               "atlanteans": sum(int(c["pop"]) for c in w["earth"].society.get("communities", [])
                                 if c["people"] == "civ:Atlanteans"),
               "eaten": cohabit.stats(k).get("eaten", 0),
               "familiar": {a.split(":")[-1]: round(v, 3) for key, v in fam.items()
                            for a in key.split("|") if humans in key.split("|") and a != humans},
               "postures": {p.split(":")[-1]: strategy.of(k, p).get("posture") for p in [humans, *w["ancients"]]},
               "uplifts": guidance.stats(k)["uplifts"], "wall_s": round(time.perf_counter() - t0)}
        rows.append(row)
    events = []
    with open(path) as f:
        for line in f:
            e = json.loads(line)
            if e["kind"] in WATCHED and peoples & set(e.get("actors") or []):
                events.append({"year": e["year"], "kind": e["kind"], "title": e["title"],
                               "cause": (e.get("cause") or "")[:160], "text": (e.get("text") or "")[:200]})
    return {"world": name, "victor": w["victor"], "ancients": list(w["ancients"]), "humans": humans,
            "arise": w["arise"], "rows": rows, "events": events}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--years", type=int, default=30)
    ap.add_argument("--snapshot", default=os.path.join(ROOT, "runs/eons/seed7/snapshot.json"))
    ap.add_argument("--history", default=os.path.join(ROOT, "runs/eons/seed7/history.jsonl"))
    ap.add_argument("--out", default=os.path.join(ROOT, "runs/earth_test"))
    ap.add_argument("--only", default="", choices=("", "predation", "peace", "alone"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    names = [a.only] if a.only else ["predation", "peace", "alone"]
    jobs = [(n, a.seed, a.snapshot, a.history, a.years, a.out) for n in names]
    with Pool(len(jobs)) as pool:
        results = pool.map(run, jobs)
    for r in results:
        with open(os.path.join(a.out, f"{r['world']}.json"), "w") as f:
            json.dump(r, f, indent=1)
        print(f"== {r['world']}: victor {r['victor']}, ancients {r['ancients']}, humans {r['humans']}")
        print(json.dumps(r["rows"][-1]))
        for e in r["events"]:
            if e["kind"] not in ("MYTH", "PHILOSOPHY", "HURDLE", "POSTURE"):
                print(f"   y{e['year']} {e['kind']}: {e['title']}")


if __name__ == "__main__":
    main()
