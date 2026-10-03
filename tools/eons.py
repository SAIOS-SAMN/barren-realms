"""
The eons: every people's history, from the galactic centre outward - its dawn, its ages, its culture, and what is
missing from it.

  python3 tools/eons.py runs/eons/seed7                   # every people, centre outward
  python3 tools/eons.py runs/eons/seed7 --within 2        # the core's peoples only (kpc from the centre)
  python3 tools/eons.py runs/eons/seed7 --gaps            # only what is missing, people by people

It reads a running (or stopped) universe's ledger (history.jsonl, every event) and its latest snapshot (where each
people lives, how far from the centre, its own clock and ledger height). Nothing is changed.

For each people, centre outward:
  DAWN       where and when it woke (cosmic time, Gyr after the Big Bang), how far from the centre, what it is
  EONS       its history grouped by eon of cosmic time and age of its own years: eras, crossings, capabilities,
             postures, strife and falls, kinship, transfer, wars and pacts, worldlines meeting, contact
  CULTURE    its philosophies, myths (each told once, with how many worlds tell it), imagination, art, eminent
             figures and epitaphs
  GAPS       the trajectories its history still lacks: stages never reached or never recorded, long ages with no
             event at all, a culture without a history or a history without a culture, a deep past its ledger
             holds no record of
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

HISTORY = ("EMERGENCE", "DEEP_HISTORY", "ERA", "STATEHOOD", "ASCENT", "FTL_CROSSED", "CAPABILITY", "TURNING",
           "POSTURE", "STRIFE", "FALL", "EPIDEMIC", "HURDLE", "KINSHIP", "KIN_EATEN", "SCHISM", "TRANSFER_FORBIDDEN",
           "TRANSFER_EMBRACED", "DOMINION", "GALACTIC_WAR", "WORLDLINES_MEET", "CONTACT", "SEEDING", "SETTLEMENT",
           "FEDERATION", "EXODUS", "LIFE_ENDED", "WORLD_STRIPPED", "WORLD_SHATTERED", "CHILD_UNIVERSE")
CULTURE = ("PHILOSOPHY", "MYTH", "IMAGINATION", "ART", "EMINENT", "EPITAPH", "COVENANT", "GENESIS_MANIFESTO",
           "RECORDKEEPING", "REDISCOVERY")
STAGES = ("farm", "state", "works", "yards", "crossed")
EON_GYR = 0.001                  # an eon of cosmic time, as printed (a million years)
AGE_YEARS = 25.0                 # an age of a people's own years, as printed


def load(run: str):
    events = []
    with open(os.path.join(run, "history.jsonl")) as f:
        for line in f:
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    from xylarium.persistence.store import StatePersistence
    snap = os.path.join(run, "snapshot.json")
    kernel = StatePersistence.load_from_file(snap) if os.path.exists(snap) else None
    return events, kernel


def peoples_of(kernel: Any) -> Dict[str, Dict[str, Any]]:
    """Each people the snapshot holds: its home, distance from the centre, dawn, ledger height and kind."""
    from xylarium.kernel import annals, clocks, cosmos, memory, relations, technology
    out: Dict[str, Dict[str, Any]] = {}
    if kernel is None:
        return out
    for who, worlds in relations._peoples(kernel).items():
        home = max(worlds, key=lambda p: p.population)
        place = cosmos.stats(kernel)["place"].get(str(home.sector_id), {})
        civ = home.civilization
        arisen = home.society.get("arisen") or {}
        out[who] = {
            "home": home.name, "r_kpc": float(place.get("r", 99.0)), "dawn_gyr": arisen.get("epoch"),
            "worlds": len(worlds), "people": sum(p.population for p in worlds),
            "kind": (getattr(civ, "traits", {}) or {}).get("describe", "?"),
            "alignment": getattr(civ, "alignment", None), "dogma": getattr(civ, "dogma", None),
            "height": clocks.height(kernel, who), "proper_gyr": clocks.now(kernel, who),
            "passed": (annals.stats(kernel)["of"].get(who) or {}).get("passed", []),
            "advanced_years": (annals.stats(kernel)["of"].get(who) or {}).get("advanced", 0.0),
            "capabilities": sorted(technology.stats(kernel)["of"].get(who, {})),
            "seeded": not arisen,
            "media": list(((kernel.state.get("memory") or {}).get("of", {}).get(who) or {}).get("media", ["oral"])),
            "myths": len(memory.myths(kernel, who)),
        }
    return out


def chronicle(who: str, rec: Dict[str, Any], events: List[Dict[str, Any]], show_gaps_only: bool) -> List[str]:
    lines: List[str] = []
    mine = [e for e in events if who in (e.get("actors") or [])]
    name = who.split(":", 1)[-1]
    hist = [e for e in mine if e.get("kind") in HISTORY]
    cult = [e for e in mine if e.get("kind") in CULTURE]
    if not show_gaps_only:
        dawn = rec.get("dawn_gyr")
        lines.append(f"## {name}  -  {rec['r_kpc']:.2f} kpc from the centre"
                     + (f", woke {dawn:.4f} Gyr after the Big Bang" if dawn is not None else ", seeded by another"))
        lines.append(f"   {rec['kind']}; {rec['worlds']} worlds, {rec['people']:,} people; alignment "
                     f"{rec['alignment']}, dogma {rec['dogma']}; ledger height {rec['height']}, own time "
                     f"{rec['proper_gyr']:.6f} Gyr")
        lines.append(f"   stages {', '.join(rec['passed']) or 'none recorded'}; capabilities "
                     f"{', '.join(rec['capabilities']) or 'none'}")
        lines.append(f"   keeps its past in {', '.join(rec.get('media', ['oral']))}; tells {rec.get('myths', 0)} myths")
        by_age: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for e in hist:
            by_age[int(float(e.get("year", 0.0)) // AGE_YEARS)].append(e)
        for age in sorted(by_age):
            lines.append(f"   AGE {age + 1} (clock years {age * AGE_YEARS:.0f}-{(age + 1) * AGE_YEARS:.0f})")
            for e in by_age[age]:
                lines.append(f"     y{e.get('year')}: {e.get('title', '')}" +
                             (f" - {e.get('cause', '')[:110]}" if e.get("cause") else ""))
        if cult:
            lines.append("   CULTURE")
            told = Counter()
            first: Dict[str, Dict[str, Any]] = {}
            for e in cult:
                key = (e.get("kind"), e.get("title"))
                told[key] += 1
                first.setdefault(key, e)
            for (kind, title), n in sorted(told.items(), key=lambda kv: float(first[kv[0]].get("year", 0))):
                e = first[(kind, title)]
                body = (e.get("text") or "")[:140]
                worlds = (e.get("data") or {}).get("worlds", n) if kind == "MYTH" else n
                lines.append(f"     y{e.get('year')} {kind.lower()}: {title}" +
                             (f" (told on {worlds} worlds)" if worlds > 1 else "")
                             + (f" - {body}" if body and kind != "MYTH" else ""))
    gaps = []
    stages_recorded = {e.get("data", {}).get("stage") for e in hist if e.get("kind") in ("ERA", "ASCENT")}
    for st in STAGES:
        if st in rec["passed"] and st not in stages_recorded and not any(
                st in (e.get("title") or "").lower() for e in hist):
            gaps.append(f"stage '{st}' reached but its era was never told")
    years = sorted(float(e.get("year", 0)) for e in hist)
    for a, b in zip(years, years[1:]):
        if b - a > 4 * AGE_YEARS:
            gaps.append(f"no history between clock years {a:.0f} and {b:.0f}")
    if rec.get("advanced_years", 0) > 1000 and not any(e.get("kind") in ("ERA", "DOMINION", "GALACTIC_WAR")
                                                       for e in hist):
        gaps.append(f"{rec['advanced_years']:,.0f} years lived at the level of history with no era, war or "
                    f"dominion recorded")
    if cult and not hist:
        gaps.append("a culture with no history")
    if hist and not cult:
        gaps.append("a history with no culture: no myth, philosophy or art")
    if not any(e.get("kind") == "ART" for e in cult):
        gaps.append("no art")
    if not any(e.get("kind") == "EMINENT" for e in cult):
        gaps.append("no remembered figure")
    if rec.get("media", ["oral"]) == ["oral"]:
        gaps.append("keeps its past only by telling it")
    if gaps:
        lines.append(f"   GAPS{' for ' + name if show_gaps_only else ''}")
        for g in gaps:
            lines.append(f"     - {g}")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", help="a run's seed directory, e.g. runs/eons/seed7")
    ap.add_argument("--within", type=float, default=None, help="only peoples within this many kpc of the centre")
    ap.add_argument("--gaps", action="store_true", help="only what is missing")
    a = ap.parse_args()
    events, kernel = load(a.run)
    peoples = peoples_of(kernel)
    galaxy = [e for e in events if e.get("kind") in ("BIG_BANG", "CHILD_UNIVERSE", "CENTRE_FLARE")]
    if not a.gaps:
        print("# The eons, centre outward")
        for e in galaxy[:12]:
            print(f"   {e.get('kind').lower()}: {e.get('title')} - {e.get('cause', '')[:120]}")
    order = sorted(peoples.items(), key=lambda kv: (kv[1]["r_kpc"], kv[1]["dawn_gyr"] or 99.0))
    for who, rec in order:
        if a.within is not None and rec["r_kpc"] > a.within:
            continue
        for line in chronicle(who, rec, events, a.gaps):
            print(line)
        if not a.gaps:
            print()


if __name__ == "__main__":
    main()
