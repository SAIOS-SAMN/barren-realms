"""
The galaxy's lore: its chronicle of ages, read from a universe's ledger - who woke, who crossed to the stars, who
went to war with whom, who fell and left their ruins, which peoples bound themselves into federations.

  python3 tools/lore.py runs/annals/seed7/history.jsonl
  python3 tools/lore.py runs/annals/seed7/history.jsonl --md lore.md

Nothing here is written by hand: every line is an event the engine recorded (history.py), most of them lived at the
level of history by the annals (annals.py) while the galaxy's deep time ran on.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

KINDS = ("EMERGENCE", "ERA", "ASCENT", "FTL_CROSSED", "FIRST_SIGNAL", "DOMINION", "GALACTIC_WAR", "FALL",
         "FEDERATION_FOUNDED", "PACT", "WORLD_STRIPPED", "WORLD_SHATTERED", "SKY_SHIELD", "SKY_REPAIR", "STAR_DEATH",
         "EXTINCTION", "UPLIFT")


def _epoch(e):
    data = e.get("data") or {}
    if "epoch" in data:
        return float(data["epoch"])
    m = re.search(r"([0-9]+\.[0-9]+) Gyr", (e.get("cause") or "") + " " + (e.get("text") or ""))
    if m:
        return float(m.group(1))
    return float(e.get("deep_gyr") or e.get("when", {}).get("deep_gyr", 0.0) or 0.0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ledger")
    ap.add_argument("--md", default="")
    ap.add_argument("--limit", type=int, default=400)
    a = ap.parse_args()
    events = []
    with open(a.ledger) as f:
        for line in f:
            line = line.strip()
            if line:
                e = json.loads(line)
                if e.get("kind") in KINDS:
                    events.append(e)
    events.sort(key=_epoch)
    count = Counter(e["kind"] for e in events)
    peoples = defaultdict(list)
    for e in events:
        for who in e.get("actors") or []:
            if str(who).startswith("civ:"):
                peoples[who].append(e["kind"])
    out = ["# The chronicle of the galaxy", "",
           f"{len(events)} events: " + ", ".join(f"{k.lower().replace('_', ' ')} {v}" for k, v in count.most_common()),
           "", "## The ages", ""]
    for e in events[: a.limit]:
        out.append(f"- **{_epoch(e):.4f} Gyr** - {e.get('title')}" + (f": {e['cause']}" if e.get("cause") else ""))
    out += ["", "## The peoples", ""]
    for who, kinds in sorted(peoples.items(), key=lambda kv: -len(kv[1]))[:40]:
        c = Counter(kinds)
        fate = "fell" if c.get("FALL") else "crossed" if c.get("ASCENT") or c.get("FTL_CROSSED") else "lives"
        out.append(f"- **{who.split(':', 1)[-1]}** ({fate}): " + ", ".join(f"{k.lower()} {v}" for k, v in c.most_common()))
    text = "\n".join(out)
    print(text)
    if a.md:
        with open(a.md, "w") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
