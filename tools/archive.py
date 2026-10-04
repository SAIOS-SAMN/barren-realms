#!/usr/bin/env python3
"""
Write into the annals, archive a universe, and return to the peoples that reached the stars.

    write    the progenitor's own entry, under their name, into a saved universe (xylarium/kernel/progenitor.py):
             python3 tools/archive.py write runs/saga/2026.json --name "NAME" --title "..." --text "..."
                                            [--about civ:People ...]
    archive  a saved universe kept whole under runs/archive/LABEL: the universe itself, its chronicles, the
             progenitor's chronicle, and a manifest of every people that has crossed to the stars (where they
             live, when they crossed, what their history makes of them, what they tell of themselves):
             python3 tools/archive.py archive runs/saga/2026.json --label earth-2026
    return   take up an archived universe again where it was left and follow the star-farers onward: each year,
             each one's numbers, worlds, history and telling - and who has newly crossed:
             python3 tools/archive.py return --label earth-2026 [--years 50] [--wall 20]

Nothing here changes a law or a people's choice: the archive is a copy, the return runs the same universe forward.
"""

import argparse
import json
import os
import shutil
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ARCHIVE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs", "archive")


def _load(path: str) -> Any:
    from xylarium.persistence.store import StatePersistence
    k = StatePersistence.load_from_file(path)
    if k is None:
        raise SystemExit(f"could not load {path}")
    k.activate()
    return k


def _save(k: Any, path: str) -> None:
    from xylarium.persistence.store import StatePersistence
    k.caches.clear()
    if not StatePersistence.save_to_file(k, path):
        raise SystemExit(f"could not save {path}")


def star_farers(k: Any) -> List[Dict[str, Any]]:
    """Every people that has crossed to the stars, as the steward sees it."""
    from xylarium.kernel import alignment, annals, mastery, syntropy
    by = syntropy._peoples(k)
    crossed = dict(mastery.stats(k).get("crossed", {}))
    for who, rec in annals.stats(k).get("of", {}).items():
        if "crossed" in rec.get("passed", []):
            crossed.setdefault(who, None)
    out = []
    for who in sorted(crossed):
        worlds = by.get(who, [])
        home = max(worlds, key=lambda p: p.population) if worlds else None
        civ = getattr(home, "civilization", None) if home is not None else None
        rec = annals.stats(k).get("of", {}).get(who, {})
        out.append({"people": who, "crossed_cycle": crossed[who], "worlds": len(worlds),
                    "dominion": rec.get("dominion"), "population": sum(p.population for p in worlds),
                    "home": {"planet": home.id, "name": home.name, "sector": home.sector_id} if home else None,
                    "alignment": round(alignment.character(civ), 4) if civ is not None else None,
                    "doctrine": round(alignment.doctrine(civ), 4) if civ is not None else None,
                    "rent": round(float(home.society.get("rent", 0.0) or 0.0), 4) if home else None})
    return out


def cmd_write(a: argparse.Namespace) -> None:
    from xylarium.kernel import progenitor
    k = _load(a.snapshot)
    e = progenitor.write(k, a.name, a.title, a.text or "", about=a.about)
    _save(k, a.snapshot)
    print(json.dumps(e, indent=1))


def cmd_archive(a: argparse.Namespace) -> None:
    from xylarium.kernel import cosmos, progenitor
    k = _load(a.snapshot)
    dest = os.path.join(ARCHIVE, a.label)
    if os.path.exists(dest) and not a.force:
        raise SystemExit(f"{dest} exists (use --force to replace it)")
    os.makedirs(dest, exist_ok=True)
    shutil.copy2(a.snapshot, os.path.join(dest, "universe.json"))
    src = os.path.dirname(os.path.abspath(a.snapshot))
    for name in ("chronicle.md", "forward.json"):
        if os.path.exists(os.path.join(src, name)):
            shutil.copy2(os.path.join(src, name), os.path.join(dest, name))
    with open(os.path.join(dest, "PROGENITOR.md"), "w") as f:
        f.write(progenitor.render(k))
    farers = star_farers(k)
    manifest = {"label": a.label, "archived_from": os.path.abspath(a.snapshot),
                "archived_at": time.strftime("%Y-%m-%d %H:%M:%S"), "seed": k.state.get("genesis", {}).get("seed"),
                "cycle": k.cycle_count, "year": round(k.cycle_count / 100.0, 2),
                "epoch_gyr": round(float(cosmos.deep_gyr(k)), 6) if cosmos.is_cosmic(k) else None,
                "star_farers": farers, "progenitor": progenitor.entries(k), "saga": k.state.get("saga")}
    with open(os.path.join(dest, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, default=str)
    print(f"archived to {dest}: {len(farers)} star-faring peoples, {len(manifest['progenitor'])} progenitor entries")


def cmd_return(a: argparse.Namespace) -> None:
    from xylarium.kernel import history
    dest = os.path.join(ARCHIVE, a.label)
    with open(os.path.join(dest, "manifest.json")) as f:
        manifest = json.load(f)
    k = _load(os.path.join(dest, "universe.json"))
    history.sink(k, os.path.join(dest, "return.events.jsonl"))
    known = {s["people"] for s in manifest["star_farers"]}
    rows, t0 = [], time.perf_counter()
    for year in range(1, a.years + 1):
        if time.perf_counter() - t0 > a.wall * 60:
            break
        for _ in range(100):
            k.tick_simulation()
        farers = star_farers(k)
        new = [s["people"] for s in farers if s["people"] not in known]
        known |= set(new)
        rows.append({"year": year, "cycle": k.cycle_count, "star_farers": farers, "newly_crossed": new})
    with open(os.path.join(dest, "return.json"), "w") as f:
        json.dump({"from": manifest["label"], "years": len(rows), "rows": rows}, f, indent=1, default=str)
    lines = [f"# Return to {manifest['label']}", "",
             f"{len(rows)} years on from year {manifest['year']:,}.", ""]
    last = rows[-1]["star_farers"] if rows else manifest["star_farers"]
    lines += ["| people | worlds | population | alignment | doctrine |", "|---|---|---|---|---|"]
    for s in last:
        lines.append(f"| {s['people'].split(':', 1)[-1]} | {s['worlds']} | {s['population']:,} | "
                     f"{s['alignment']} | {s['doctrine']} |")
    crossed = [p for r in rows for p in r["newly_crossed"]]
    lines += ["", "Newly crossed: " + (", ".join(p.split(':', 1)[-1] for p in crossed) if crossed else "none")]
    with open(os.path.join(dest, "return.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("snapshot")
    w.add_argument("--name", required=True)
    w.add_argument("--title", required=True)
    w.add_argument("--text", default="")
    w.add_argument("--about", nargs="*", default=[])
    r = sub.add_parser("archive")
    r.add_argument("snapshot")
    r.add_argument("--label", required=True)
    r.add_argument("--force", action="store_true")
    b = sub.add_parser("return")
    b.add_argument("--label", required=True)
    b.add_argument("--years", type=int, default=50)
    b.add_argument("--wall", type=float, default=20.0, help="minutes of wall time at most")
    a = ap.parse_args()
    {"write": cmd_write, "archive": cmd_archive, "return": cmd_return}[a.cmd](a)


if __name__ == "__main__":
    main()
