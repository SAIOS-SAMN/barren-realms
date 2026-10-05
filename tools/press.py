#!/usr/bin/env python3
"""
The press: a universe's annals made into books - a volume per people (or world), each one's genre read from the
shape of its own record, every line cited to the event it tells (xylarium/kernel/press.py).

    python3 tools/press.py runs/x/history.jsonl --out runs/annals/x [--by world] [--title "..."]
    python3 tools/press.py --progenitor 7 --ages 1e8 1e9 --out runs/annals/seed7      # live a universe, then print it

The second form takes a progenitor's seat in a new universe (seed), looks away for each age given, writes the
ledger as it goes, and publishes it.
"""

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xylarium.kernel import press  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ledger", nargs="?")
    ap.add_argument("--out", required=True)
    ap.add_argument("--by", default="people", choices=("people", "world"))
    ap.add_argument("--title", default="The Annals")
    ap.add_argument("--progenitor", type=int, default=None, help="seed: live a progenitor's universe first")
    ap.add_argument("--pick", type=int, default=0)
    ap.add_argument("--ages", type=float, nargs="*", default=[1e8, 1e9])
    a = ap.parse_args()
    if a.progenitor is not None:
        from xylarium.kernel import ages, history, roles
        random.seed(a.progenitor)
        os.makedirs(a.out, exist_ok=True)
        ledger = os.path.join(a.out, "history.jsonl")
        if os.path.exists(ledger):
            os.remove(ledger)
        k = roles.start_progenitor(a.progenitor, "The Architects", pick=a.pick, pace="neighbourly")
        history.sink(k, ledger)
        for span in a.ages:
            for line in ages.sleep(k, "player_1", span)[:1]:
                print(line)
        a.ledger = ledger
    events = press.from_ledger(a.ledger)
    cat = press.publish(events, a.out, a.title, a.by)
    print(f"{len(events):,} events -> {len(cat)} volumes in {a.out}")
    for c in cat[:12]:
        print(f"  {c['genre']:<16} {c['volume']:<28} {c['events']:>5}  {', '.join(c['strands'])}")


if __name__ == "__main__":
    main()
