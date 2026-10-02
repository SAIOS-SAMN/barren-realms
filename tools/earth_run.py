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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--years", type=int, default=2000)
    ap.add_argument("--every", type=int, default=100)
    ap.add_argument("--pace", default="lonely")
    ap.add_argument("--out", default="")
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
