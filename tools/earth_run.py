"""
Earth by our rules: a people wakes on a world like ours, at our place and time, and lives under every law the engine
holds - then is set beside Earth in 2026.

  python3 tools/earth_run.py --years 2000                # seed 7, a Sun-like star on the 8 kpc ring
  python3 tools/earth_run.py --years 5000 --every 250 --out runs/earth_run.json

The world is not built to be Earth. The tool searches the galaxy the seed made for a star of about a sun's mass, born
about when ours was, on our ring, with a world whose own chemistry is water under light at about our warmth - and
wakes a mind there at the epoch ours woke (creation's cell, cosmos.arise), with the universe's clock set to that
epoch and no elder peoples woken around it (the elder question is tools/elders.py's). It then lives, year by year,
and its ways, energy, wars, mathematics, mastery and sky are read back.
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from xylarium.kernel import cosmos, creation, interior  # noqa: E402
from xylarium.kernel.engine import GameKernel  # noqa: E402

EARTH_2026 = {
    "energy": "combustion of stored carbon, the first fire of a carbon biosphere under oxygen",
    "kardashev": 0.73,
    "world_mastery": 1.8e13 / 1.74e17,
    "crossed": False,
    "wars": "frequent, among its own kind",
    "heard_by_others": "leaking ~1e9 W of radio for ~a century: audible to an Earth-like listener within ~12 ly",
}


def sol_like(seed: Any) -> Optional[Dict[str, Any]]:
    """A Sun-like star on the 8 kpc ring, born near 9.2 Gyr, with a lit water world near 280 K."""
    best = None
    for (i, j) in cosmos.cells():
        if abs(cosmos.ring_radius(i) - cosmos.R0_KPC) > 0.5:
            continue
        for slot in creation.cell(seed, i, j):
            if "worlds" not in slot or not (0.85 <= slot["mass"] <= 1.15) or abs(slot["born"] - 9.2) > 1.0:
                continue
            for w, world in enumerate(slot["worlds"]):
                if "host" in world:
                    continue
                for m in world.get("media", []):
                    if m["region"] == "biotic" and m["where"] == "surface" and 265 <= m["t"] <= 305:
                        score = abs(slot["mass"] - 1.0) + abs(slot["born"] - 9.2) / 3 + abs(m["t"] - 288) / 100
                        if best is None or score < best[0]:
                            best = (score, {"cell": [i, j], "k": slot["k"], "w": w, "born": slot["born"],
                                            "mass": slot["mass"], "t": m["t"]})
    return best[1] if best else None


def mesozoic(seed: Any, found: Dict[str, Any], a: Any) -> Optional[float]:
    """Begin at its Mesozoic: 252 Myr before its 2026 its biosphere holds complex life a rung short of a mind; its
    lineages race up that last rung (life.climb, clades by the progenitors' law), the comets of its neighbourhood
    knocking them back, until one holds a mind's blueprint - or none does by its present."""
    import random
    from xylarium.kernel import life
    slot = creation.cell(seed, *found["cell"])[found["k"]]
    world = slot["worlds"][found["w"]]
    ch = next((c for c in creation.chemistries(seed, slot, world) if c["region"] == "biotic"), None)
    if ch is None or not ch["ladder"]["complete"]:
        print("its chemistry cannot climb to a mind")
        return None
    last = ch["ladder"]["steps"][-1]["mean_gyr"]
    now = found["born"] + interior.SOLAR_AGE_GYR
    start = now - 0.252
    life.ERASURE, life.CLADES = a.erasure, a.clades
    rng = random.Random(a.seed)
    tries = []
    for _ in range(a.rolls):                       # its dice rolled many times: the spread, then one history
        got = life.climb(rng, [1e-12, last], start, now + 1.0, float("inf"), ch["mu"])
        tries.append(got["times"][-1] if len(got["times"]) == 2 else None)
    hits = sorted(t for t in tries if t is not None)
    by_now = [t for t in hits if t <= now]
    print(json.dumps({"last_rung_mean_myr": round(last * 1000, 1), "impacts_per_myr": round(ch["mu"] / 1000, 5),
                      "erasure": a.erasure, "clades": a.clades,
                      "mind_by_its_2026": round(len(by_now) / a.rolls, 3),
                      "median_myr_after_mesozoic_began": round((hits[len(hits) // 2] - start) * 1000, 1) if hits else None,
                      "in_the_mesozoic": round(sum(1 for t in hits if t <= now - 0.066) / a.rolls, 3)}))
    one = tries[0]
    if one is None or one > now:
        print("in this history no lineage reached a mind by its present")
        return None
    print(f"in this history a mind arises {(one - start) * 1000:.1f} Myr after the Mesozoic began "
          f"({(now - one) * 1000:.1f} Myr before its 2026)")
    return one


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--years", type=int, default=2000)
    ap.add_argument("--every", type=int, default=100)
    ap.add_argument("--pace", default="lonely")
    ap.add_argument("--out", default="")
    ap.add_argument("--mesozoic", action="store_true", help="begin 252 Myr before its 2026, a rung short of a mind")
    ap.add_argument("--erasure", default="clades", choices=("rung", "clades"))
    ap.add_argument("--clades", type=int, default=6)
    ap.add_argument("--rolls", type=int, default=400)
    a = ap.parse_args()
    k = GameKernel(seed=a.seed, genesis=f"cosmic:{a.pace}")
    k.activate()
    seed = creation.universe(k)
    found = sol_like(seed)
    if found is None:
        print("no Sun-like system with a lit water world on our ring in this universe")
        return
    st = cosmos.stats(k)
    epoch = found["born"] + interior.SOLAR_AGE_GYR - 0.0003       # it wakes ~300,000 years before its 2026
    if a.mesozoic:
        epoch = mesozoic(seed, found, a)
        if epoch is None:
            return
    k.cycle_count = int((epoch - st["epoch0"]) * 1e9 / cosmos.ruler(k) * 100)
    st["minds"], st["next"] = [], 0                               # no elders woken around it
    later = [m for m in creation.schedule(seed)["minds"] if m["epoch"] > epoch]
    st["last"] = None if not later else [epoch, later[0]["cell"], later[0]["k"], later[0]["w"]]
    line = cosmos.arise(k, {"cell": found["cell"], "k": found["k"], "w": found["w"], "epoch": epoch,
                            "metab": "biotic", "steps": []})
    print(line, json.dumps(found))
    sid = cosmos.sector_of_slot(k, tuple(found["cell"]), found["k"])
    planet = k.sectors[sid].planets[found["w"]]
    who = f"civ:{planet.civilization.name}"
    tick = k.tick_simulation
    rows: List[Dict[str, Any]] = []
    t0 = time.perf_counter()
    from xylarium.kernel import energy, history, intellect, mastery, signals, sustenance
    for year in range(1, a.years + 1):
        for _ in range(100):
            tick()
        if year % a.every == 0 or year == a.years:
            worlds = [p for s in k.sectors.values() for p in s.planets if sustenance.people_of(p) == who]
            m = mastery.measure(k, worlds) if worlds else {}
            row = {"year": year, "people": sum(p.population for p in worlds), "worlds": len(worlds),
                   "way": planet.society.get("way"), "citadel": planet.citadel_level,
                   "burns": energy.burns(k, planet), "kardashev": round(m.get("kardashev", 0.0), 3),
                   "world_mastery": float(f"{m.get('world', 0.0):.3g}"),
                   "rank4": intellect.gauge(k, who).get("4", 0), "crossed": mastery.crossed(k, who),
                   "heard": len(signals.heard(k, who)), "wall_s": round(time.perf_counter() - t0)}
            rows.append(row)
            print(json.dumps(row), flush=True)
    kinds: Dict[str, int] = {}
    for e in history.of_people(k, who):
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    out = {"found": found, "people": who, "rows": rows, "events": kinds, "earth_2026": EARTH_2026}
    print(json.dumps({"events": kinds}, indent=1))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
