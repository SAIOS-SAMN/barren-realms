"""
The bridges, timed: how long the engine's own laws take to carry life from its first copy to a mind, and a people
from its first band to the stars - in years and in each people's own generations - set beside Earth's one record.

  python3 tools/bridges.py --peoples 12 --years 3000            # live the first minds of seed 7, time their ways
  python3 tools/bridges.py --peoples 8 --years 1500 --out runs/bridges.json

Two clocks are read:
  LIFE      from the seed's schedule: each mind's steps (creation.lineage) - life's first copy, every rung of its
            ladder, the mind - in Gyr, by chemistry;
  PEOPLES   from living them (the full engine, at the slowest pace so the galaxy barely turns): each people's
            farming, its state, each tier of its works, its yards, its crossing - in years and in generations
            (fertility.generation_of), and what held it where it stalled (treasury, ore, the council's choice).
"""

import argparse
import json
import os
import statistics
import sys
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from xylarium.kernel import cosmos, creation  # noqa: E402
from xylarium.kernel.engine import GameKernel  # noqa: E402

EARTH = {                                   # Earth's one record (years before 2026), a test - not a ruler
    "life": 3.8e9, "eukaryotes": 2.0e9, "multicellular": 0.6e9, "dinosaurs": 2.3e8, "hominins": 7.0e6,
    "our_species": 3.0e5, "farming": 1.2e4, "states": 5.5e3, "industry": 250.0, "radio": 120.0,
}


def life_clock(seed: Any) -> Dict[str, Any]:
    by: Dict[str, List[List[float]]] = {}
    for m in creation.schedule(seed)["minds"]:
        st = m["steps"]
        by.setdefault(m["metab"], []).append([b - a for a, b in zip(st, st[1:])] + [st[0]])
    out = {}
    for region, rows in by.items():
        n = len(rows)
        firsts = [r[-1] for r in rows]
        spans = [sum(r[:-1]) for r in rows]
        out[region] = {"minds": n, "rungs_median": statistics.median(len(r) for r in rows),
                       "life_to_mind_gyr_median": round(statistics.median(spans), 4),
                       "crust_to_life_gyr_median": round(statistics.median(firsts), 4)}
    return out


def peoples_clock(seed: int, n: int, years: int, every: int) -> Dict[str, Any]:
    from xylarium.kernel import fertility, ledger, mastery, sustenance
    k = GameKernel(seed=seed, genesis="cosmic:lonely")
    k.activate()
    st = cosmos.stats(k)
    for m in creation.schedule(creation.universe(k))["minds"][:n]:
        k.cycle_count = max(k.cycle_count, int((m["epoch"] - st["epoch0"]) * 1e9 / cosmos.ruler(k) * 100) + 1)
        cosmos._due(k)
    homes = {}
    for s in k.sectors.values():
        for p in s.planets:
            if p.population > 0 and getattr(p, "civilization", None) is not None:
                homes[sustenance.people_of(p)] = p
    start = k.cycle_count
    marks: Dict[str, Dict[str, float]] = {w: {} for w in homes}
    trace: Dict[str, List[Dict[str, Any]]] = {w: [] for w in homes}
    from xylarium.kernel import knowledge
    know: Dict[str, Dict[str, float]] = {w: {} for w in homes}
    for year in range(1, years + 1):
        for _ in range(100):
            k.tick_simulation()
        if year % 100 == 0:
            print(f"year {year}", flush=True, file=sys.stderr)
        for who, p in homes.items():
            mk = marks[who]
            before = dict(mk)
            way = p.society.get("way")
            if way in ("farm", "state") and "farm" not in mk:
                mk["farm"] = year
            if way == "state" and "state" not in mk:
                mk["state"] = year
            for tier in range(1, 6):
                if p.citadel_level >= tier and f"works{tier}" not in mk:
                    mk[f"works{tier}"] = year
            if sustenance.yards(p) and "yards" not in mk:
                mk["yards"] = year
            if mastery.crossed(k, who) and "crossed" not in mk:
                mk["crossed"] = year
            a_now = sum(knowledge.experience(k, who, d) for d in knowledge.DOMAINS)
            for key in mk:
                if key not in before:
                    know[who][key] = round(a_now, 2)
            if year % every == 0:
                trace[who].append({"year": year, "pop": p.population, "way": way, "tier": p.citadel_level,
                                   "treasury": p.treasury, "ore": p.ore_silo})
    out = {}
    for who, p in homes.items():
        gen = fertility.generation_of(k, p)
        out[who] = {"generation_years": round(gen, 1), "metab": p.civilization.metabolism if p.civilization else None,
                    "years": marks[who], "knowledge_at": know[who], "generations": {kk: round(v / max(1e-6, gen), 1) for kk, v in marks[who].items()},
                    "end": trace[who][-1] if trace[who] else None}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--peoples", type=int, default=12)
    ap.add_argument("--years", type=int, default=3000)
    ap.add_argument("--every", type=int, default=250)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    res = {"earth_years_before_2026": EARTH, "life": life_clock(a.seed),
           "peoples": peoples_clock(a.seed, a.peoples, a.years, a.every)}
    text = json.dumps(res, indent=1)
    print(text)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)


if __name__ == "__main__":
    main()
