"""
The elders of the galaxy and our own system: what billions of years of older peoples could have done to a Sun born
9.2 Gyr after the Big Bang - at the level of history (xylarium/kernel/prehistory.py), over the progenitors' declared
ranges of the rates the full engine's live runs measure.

  python3 tools/elders.py --seeds 7 --draws 2000
  python3 tools/elders.py --seeds 1-4 --draws 1000 --out runs/elders.json

Reported, over all draws and conditioned on each outcome: how many elders had crossed, reached and settled our
system; whether Mars, while green, was kept green by a people living there, or struck in a war of doctrines; ruins
left by peoples that settled and fell; and whether the sky is quiet when our own mind looks up - with which rates
each outcome leans on.
"""

import argparse
import json
import math
import os
import random
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from xylarium.kernel import interior, prehistory, worlds  # noqa: E402

SUN = {"mass": "1", "luminosity": "1"}


def _seeds(text: str):
    if "-" in text:
        a, b = text.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in text.split(",")]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", default="7")
    ap.add_argument("--draws", type=int, default=2000)
    ap.add_argument("--rng", type=int, default=9)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    born = interior.SUN_BORN_GYR
    now = born + interior.SOLAR_AGE_GYR
    mars = worlds.windows(worlds.history(None, SUN, 1.524, 0.53, 0.107, False, 1.0, 8.0, born=born))
    rng = random.Random(a.rng)
    recs = []
    for seed in _seeds(a.seeds):
        elders = prehistory.homes(seed, now)
        for _ in range(a.draws):
            p = prehistory.draw(rng)
            r = prehistory.sol(seed, p, rng, born, mars, now, elders)
            recs.append({"seed": seed, "p": p, **r})
    n = len(recs)

    def share(key):
        return round(sum(1 for r in recs if r[key]) / n, 4)

    def leans(key):
        """Each rate's median among the draws where the outcome held, against all draws."""
        hit = [r for r in recs if r[key]]
        if not hit:
            return {}
        return {k: {"when": round(statistics.median(r["p"][k] for r in hit), 4),
                    "all": round(statistics.median(r["p"][k] for r in recs), 4)} for k in prehistory.PRIORS}
    summary = {
        "draws": n, "mars_green_window_gyr_after_sun": mars,
        "elders_before_us": {"median": statistics.median(r["elders"] for r in recs)},
        "crossed_before_us": {"median": statistics.median(r["crossed"] for r in recs)},
        "reached_our_system": {"share_any": round(sum(1 for r in recs if r["reached"]) / n, 4),
                               "median": statistics.median(r["reached"] for r in recs)},
        "settled_our_system": round(sum(1 for r in recs if r["settled"]) / n, 4),
        "mars_kept_green": share("mars_kept_green"), "mars_struck": share("mars_struck"),
        "ruins_left": round(sum(1 for r in recs if r["ruins"]) / n, 4),
        "quiet_sky_now": share("quiet_sky"),
        "watched_now": round(sum(1 for r in recs if r["watchers"]) / n, 4),
        "leans": {k: leans(k) for k in ("mars_kept_green", "mars_struck", "quiet_sky")},
    }
    print(json.dumps(summary, indent=1))
    if a.out:
        with open(a.out, "w") as f:
            json.dump({"summary": summary, "draws": recs}, f)


if __name__ == "__main__":
    main()
