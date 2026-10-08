"""Read the running universe's observations log and say whether the game is alive: minds seeded across the galaxy,
civilizations built, intelligence climbing, species evolving, resources moving, the roads and the court in use.

  python3 tools/universe_watch.py [runs/universe_cosmic_42.obs.jsonl]
"""

import json
import os
import sys


def g(o, *path, default=0):
    for p in path:
        o = (o or {}).get(p) if isinstance(o, dict) else None
    return default if o is None else o


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs", "universe_cosmic_42.obs.jsonl")
    rows = [json.loads(line) for line in open(path)]
    if not rows:
        print("no observations yet")
        return
    a, b = rows[0], rows[-1]
    print(f"cycles {a['cycle']} -> {b['cycle']}   deep time {a.get('deep_gyr')} -> {b.get('deep_gyr')} Gyr   "
          f"{b.get('cyc_per_s')} cycles/s")
    checks = [
        ("minds seeded (arisen / expected by now)", g(b, "cosmos", "minds_arisen"), g(b, "cosmos", "minds_expected_by_now")),
        ("peoples / worlds settled", g(b, "cosmos", "peoples"), b.get("worlds")),
        ("population", a.get("people"), b.get("people")),
        ("intellect: peoples climbing / mean fluid", g(b, "intellect", "peoples"), g(b, "intellect", "mean_fluid", default={})),
        ("crystals: abstractions", g(a, "intellect", "abstractions", default="-"), g(b, "intellect", "abstractions", default="-")),
        ("species: speciations / gene edits", g(b, "genome", "speciations"), g(b, "genome", "edits")),
        ("knowledge", json.dumps(g(a, "knowledge", default={}))[:80], json.dumps(g(b, "knowledge", default={}))[:80]),
        ("trade: traded / last year value", g(b, "commerce", "traded"), g(b, "commerce", "last_year", "value")),
        ("roads: toll paid / tolled lanes / masters", g(b, "transit", "paid_cr"), g(b, "transit", "tolled_lanes")),
        ("civilizations by stage", json.dumps(g(b, "annals", "stages", default=g(b, "annals", default={})))[:120], ""),
        ("court: houses / closed / beyond", g(b, "court", "houses"), f"{g(b, 'court', 'closed')} / {g(b, 'court', 'beyond')}"),
    ]
    for name, x, y in checks:
        print(f"  {name:<44} {x}  {y}")
    stalled = [n for n, x, y in checks if x in (0, None) and y in (0, None, "", {})]
    if stalled:
        print("  NOT MOVING: " + "; ".join(stalled))


if __name__ == "__main__":
    main()
