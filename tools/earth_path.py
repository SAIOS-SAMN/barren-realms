#!/usr/bin/env python3
"""
Earth's energy path, a century at a time: the finders' world alone, every other world held still, under the engine's
own laws - the council's choice to burn or go without (energy_path.weigh), the light and heat it builds when it goes
without (harvest.py's own designs, costs and choice), what its burning leaves in its sky (waste.py), its few's take
(rent.py) and its minds' shared swing (decide.mood). Two measured inputs tie it to the present: its burning now
(~10 GtC a year when its whole shortfall is burnt) and the stock still in reach (~1,000 GtC).

Each method changes one thing and leaves every law alone:

  base       as the laws and the snapshot give it
  nofew      its few take nothing (rent 0)
  long       its councils see ten times further
  seer       a hundred times further (the reach of its own world's memory)
  patient    it does not discount what comes after it (its money's price of waiting set to nothing)
  quiet      its minds do not hear each other (no coupling)
  truth      what it tells of itself is its history (no doctrine gap)
  learning   its works grow cheaper as it builds them (Wright's law over what it has built: laws.wright)
  sensitive  its living world feels warmth as a food chain tuned to its seasons does (x300 its people's own)

    python3 tools/earth_path.py base,nofew,long --years 100 --histories 5
"""

import argparse
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SNAP = os.environ.get("EARTH_SNAPSHOT", "runs/saga/2026.json")
BURN_GTC_NOW = 10.0             # the finders' burning now, a year (Global Carbon Project, ~2015-2024)
SENSITIVE = float(os.environ.get("SENSITIVE", "300"))               # a food chain's warmth sensitivity over its people's own (the "sensitive" method)


def _load():
    from xylarium.persistence.store import StatePersistence
    k = StatePersistence.load_from_file(SNAP)
    k.activate()
    return k


def run(k, methods, years, history):
    """One century of the finders' energy path under `methods` (a set), on its own copy of the world."""
    from xylarium.kernel import (biosphere, decide, energy, energy_path, harvest, laws, rent, waste)
    import earth_saga as story
    saga = k.state["saga"]
    finders = saga["roles"]["finders"]
    earth = next(p for s in k.sectors.values() for p in s.planets if p.id == saga["earth"])
    k.state["genesis"]["history"] = history
    saved = {"rate": decide.rate, "h": decide.horizon, "coupling": dict(decide.COUPLING), "alt": energy_path.alternative,
             "room": waste.room, "rent": rent.of}
    try:
        if "long" in methods or "seer" in methods:
            mult = 100.0 if "seer" in methods else 10.0
            decide.horizon = lambda m, f=saved["h"], x=mult: f(m) * (x if m.get("holder") == finders else 1.0)
        if "patient" in methods:                              # it does not discount what comes after it
            decide.rate = lambda kk, cur, f=saved["rate"]: 0.0
        if "quiet" in methods:
            decide.COUPLING.clear()
        if "nofew" in methods:
            rent.of = lambda p, f=saved["rent"]: 0.0 if p is earth else f(p)
        built0 = max(1, (earth.society.get("works") or {}).get("field", 0) + (earth.society.get("works") or {}).get("tap", 0))
        if "learning" in methods:
            def cheaper(kk, p, s, f=saved["alt"]):
                v = f(kk, p, s)
                w = p.society.get("works") or {}
                from xylarium.kernel import sustenance
                done = w.get("field", 0) + w.get("tap", 0) + harvest.stats(kk).get("arrays", {}).get(
                    str(p.sector_id), {}).get(sustenance.people_of(p), 0)
                return None if v is None else v * laws.wright(max(0, done - built0), built0)
            energy_path.alternative = cheaper
        if "sensitive" in methods:
            waste.room = lambda kk, p, t, f=saved["room"]: max(0.0, 1.0 - (1.0 - f(kk, p, t)) * SENSITIVE)
        # the present: what its whole shortfall burnt is, measured; its stock in reach, measured
        short0 = energy_path._short_eu(k, earth)
        units_year = max(1e-9, 4.0 * short0 / energy.CARBON_EU)
        gtc_per_unit = BURN_GTC_NOW / units_year
        earth.element_reserves["C"] = int(story.HUMAN_RESERVE_GTC / gtc_per_unit)
        k0 = biosphere.carrying_capacity(k, earth)
        rows = []
        for year in range(1, years + 1):
            if "truth" in methods:
                c = earth.civilization
                c.told_light, c.told_dark = c.light, c.dark
            k.cycle_count += 100                                      # a year: its seasons, its moods
            rec = energy_path.weigh(k, earth) or {}
            short = energy_path._short_eu(k, earth)
            need = max(1e-9, energy.need_eu(earth, k))
            covered = need - short + (short if earth.society.get("burn", 0) else 0.0)
            earth.society["energy_sufficiency"] = round(min(1.0, covered / need), 4)   # what it ran on
            burnt_gtc = 0.0
            if earth.society.get("burn", 0) and short > 0:
                units = min(4.0 * short / energy.CARBON_EU, earth.element_reserves.get("C", 0))
                earth.element_reserves["C"] -= int(units)
                burnt_gtc = units * gtc_per_unit
                waste.burn(k, earth, burnt_gtc * 1e12)
            else:                                                      # it goes without: its councils build
                budget = earth.population * 4 * _tax_q(earth) * (1.0 - rent.of(earth))
                earth.treasury = max(earth.treasury, 0) + int(budget)
                earth.ore_silo = max(earth.ore_silo or 0, 10 ** 6)
                for _ in range(50):
                    opts = harvest._options(k, earth)
                    pick = decide.choose(k, opts, decide.mind_of_planet(k, earth), earth.id, "harvest") if opts else None
                    if pick is None or energy_path._short_eu(k, earth) <= 0:
                        break
                    harvest.build(k, earth, pick["kind"], pick["design"], pick["cost"])
            from xylarium.kernel import sustenance
            arrays = harvest.stats(k).get("arrays", {}).get(str(earth.sector_id), {}).get(sustenance.people_of(earth), 0)
            a = waste.assess(k, earth)
            lost = k0 * (1.0 - a["room"])
            w = earth.society.get("works") or {}
            rows.append({"year": 2025 + year, "burn": earth.society.get("burn", 0), "short_eu": round(short, 2),
                         "burnt_gtc": round(burnt_gtc, 2),
                         "reserve_gtc": round(earth.element_reserves.get("C", 0) * gtc_per_unit, 1),
                         "fields": w.get("field", 0), "taps": w.get("tap", 0), "arrays": arrays,
                         "warming_k": a["warming_k"],
                         "room": a["room"], "room_lost": round(lost, 1),
                         "mood": round(decide.mood(k, finders), 4), "worth": rec.get("value"), "cost": rec.get("cost"),
                         "rent": rent.of(earth), "path_index": round(energy_path.path_index(earth), 4)})
        return {"methods": sorted(methods), "history": history, "rows": rows}
    finally:
        decide.horizon = saved["h"]
        decide.rate = saved["rate"]
        decide.COUPLING.clear()
        decide.COUPLING.update(saved["coupling"])
        energy_path.alternative = saved["alt"]
        waste.room = saved["room"]
        rent.of = saved["rent"]


def _tax_q(planet) -> float:
    from xylarium.kernel.demography import _tax_per_head_quarter
    return _tax_per_head_quarter(planet)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("methods", help="comma-separated method sets; '+' joins methods in one set")
    ap.add_argument("--years", type=int, default=100)
    ap.add_argument("--histories", type=int, default=5)
    ap.add_argument("--out", default="runs/earth_path.json")
    a = ap.parse_args()
    base = _load()
    results = []
    for spec in a.methods.split(","):
        for h in range(a.histories):
            k = copy.deepcopy(base)
            k.activate()
            r = run(k, set(spec.split("+")), a.years, h)
            r["spec"] = spec
            results.append(r)
            z = r["rows"][-1]
            print(f"{spec:28s} h{h} burnt {sum(x['burnt_gtc'] for x in r['rows']):7.1f} GtC  "
                  f"reserve {z['reserve_gtc']:7.1f}  warming {z['warming_k']:.2f} K  works {z['fields'] + z['taps'] + z['arrays']:5d}  "
                  f"burn-years {sum(x['burn'] for x in r['rows']):3d}  first-abstain "
                  f"{next((x['year'] for x in r['rows'] if not x['burn']), None)}", flush=True)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(results, f, default=str)


if __name__ == "__main__":
    main()
