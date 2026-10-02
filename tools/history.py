"""
Read a universe's history ledger back (xylarium/kernel/history.py): annals, a book, or a screenplay for a replay.

  python3 tools/history.py runs/seed7/history.jsonl                       # what happened, by age and kind
  python3 tools/history.py runs/seed7/history.jsonl --people Zishamar     # one people's annals
  python3 tools/history.py runs/seed7/history.jsonl --book book.md        # the chronicle as a book: ages, peoples
  python3 tools/history.py runs/seed7/history.jsonl --scenes scenes.json  # scenes in space and time, for a replay
  python3 tools/history.py runs/seed7/history.jsonl --myths Zishamar      # a people's mythology, myth by myth

The ledger is the whole record: every event once, with when (clock year, deep-time epoch, age), where (world,
system, and in a cosmic universe the galactic position at that moment), who, what, why, how much, and the earlier
events it answers. The book and the screenplay are views of it, not summaries: nothing is dropped.
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List

AGES = ["Before Minds", "Age of Foragers", "Age of Fields", "Age of First Flight", "Age of the Lanes"]


def load(path: str) -> List[Dict[str, Any]]:
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _who(e: Dict[str, Any]) -> List[str]:
    return [a.split(":", 1)[-1] for a in e.get("actors", [])]


def about(events: Iterable[Dict[str, Any]], people: str) -> List[Dict[str, Any]]:
    p = people.lower()
    return [e for e in events if any(p == w.lower() or p in w.lower() for w in _who(e))
            or p in (e.get("title", "") + e.get("text", "")).lower()]


def overview(events: List[Dict[str, Any]]) -> str:
    lines = [f"{len(events)} events, years {events[0]['year']} to {events[-1]['year']}" if events else "no events"]
    by_age = defaultdict(Counter)
    for e in events:
        by_age[e.get("age", "?")][e["kind"]] += 1
    for age in AGES + sorted(set(by_age) - set(AGES)):
        if age in by_age:
            kinds = ", ".join(f"{k} {n}" for k, n in by_age[age].most_common(8))
            lines.append(f"  {age}: {kinds}")
    peoples = Counter(w for e in events for w in _who(e))
    lines.append("  most present: " + ", ".join(f"{p} ({n})" for p, n in peoples.most_common(8)))
    return "\n".join(lines)


def book(events: List[Dict[str, Any]], title: str) -> str:
    """The chronicle as a book: a part per age, a chapter per people within it, events in order."""
    out = [f"# {title}", ""]
    by_age: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in events:
        by_age[e.get("age", "?")].append(e)
    for age in AGES + sorted(set(by_age) - set(AGES)):
        if age not in by_age:
            continue
        evs = by_age[age]
        out += [f"## {age}", "", f"*Years {evs[0]['year']:.0f} to {evs[-1]['year']:.0f}*"
                + (f" *- deep time {evs[0]['deep_gyr']:.3f} to {evs[-1]['deep_gyr']:.3f} Gyr*" if "deep_gyr" in evs[0] else ""),
                ""]
        chapters: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for e in evs:
            chapters[(_who(e) or ["The galaxy"])[0]].append(e)
        for who, ces in sorted(chapters.items(), key=lambda kv: kv[1][0]["cycle"]):
            out += [f"### {who}", ""]
            for e in ces:
                where = f" ({e['planet_name']})" if e.get("planet_name") else ""
                text = e.get("text") or e.get("title")
                out.append(f"- **Year {e['year']:.0f}{where} - {e['title']}.** {text}"
                           + (f" *({e['cause']})*" if e.get("cause") else ""))
            out.append("")
    return "\n".join(out)


def scenes(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Scenes for a replay: each event placed in space (galactic kpc, the system, the world) and time (clock year
    and deep-time epoch), with its actors, action, telling and weight - in order, nothing dropped."""
    out = []
    for e in events:
        g = e.get("galactic") or {}
        out.append({"id": e["id"], "t_year": e["year"], "deep_gyr": e.get("deep_gyr"), "age": e.get("age"),
                    "where": {"x_kpc": g.get("x"), "y_kpc": g.get("y"), "r_kpc": g.get("r"), "system": e.get("sector"),
                              "world": e.get("planet_name")},
                    "actors": _who(e), "action": e["kind"], "title": e["title"], "telling": e.get("text", ""),
                    "cause": e.get("cause", ""), "weight": e.get("magnitude", 0), "answers": e.get("refs", [])})
    return out


def mythology(events: List[Dict[str, Any]], people: str) -> str:
    byid = {e["id"]: e for e in events}
    myths = [e for e in about(events, people) if e["kind"] == "MYTH"]
    lines = []
    for m in myths:
        src = [byid[r]["title"] for r in m.get("refs", []) if r in byid and byid[r]["kind"] != "MYTH"]
        lines.append(f"year {m['year']:.0f}: {m['text']}" + (f"  [remembers: {src[0]}]" if src else ""))
    return "\n".join(lines) or "no myths yet"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ledger")
    ap.add_argument("--people", default="")
    ap.add_argument("--kind", default="")
    ap.add_argument("--book", default="")
    ap.add_argument("--scenes", default="")
    ap.add_argument("--myths", default="")
    args = ap.parse_args()
    events = load(args.ledger)
    if args.people:
        events = about(events, args.people)
    if args.kind:
        events = [e for e in events if e["kind"] == args.kind.upper()]
    if args.myths:
        print(mythology(load(args.ledger), args.myths))
        return
    if args.book:
        name = os.path.basename(os.path.dirname(os.path.abspath(args.ledger))) or "the universe"
        with open(args.book, "w") as f:
            f.write(book(events, f"The History of {args.people or name}"))
        print(f"wrote {args.book} ({len(events)} events)")
        return
    if args.scenes:
        with open(args.scenes, "w") as f:
            json.dump(scenes(events), f, indent=1)
        print(f"wrote {args.scenes} ({len(events)} scenes)")
        return
    print(overview(events))
    if args.people or args.kind:
        for e in events[-40:]:
            print(f"  y{e['year']:>8.1f} {e['kind']:<16} {e['title']}")


if __name__ == "__main__":
    sys.exit(main())
