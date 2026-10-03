"""
The baseline: a green Mars, under our own formulas - not Earth as we measure it now.

  python3 tools/green_mars.py                # Mars as our physics makes it, and a Mars that kept its air
  python3 tools/green_mars.py --trials 2000  # more draws of its life's chances

Two worlds, both Mars (0.107 Earth masses, 0.53 Earth radii, 1.524 AU from a sun born 9.2 Gyr after the Big Bang):

  as made     its history as worlds.history gives it - its air outgassed and stripped by its star's youth
  kept green  the same world with its sky never broken (worlds.STRIP_RATE = 0): a counterfactual by conditioning,
              not tuning - what life on a Mars that stayed green would do under our ladder

For each: when it was green, and in each green age its living medium, its ladder rung by rung (bits held, mean
wait, the population it can feed), and the chance its life reaches a mind - by the Sun's age now (4.57 Gyr) and by
the end of its green span - over many draws of its chances (life.climb, impacts at the Sun's ring).
"""

import argparse
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from xylarium.kernel import creation, geometry, interior, life, worlds  # noqa: E402

SUN = {"mass": "1", "luminosity": "1"}
MARS = (1.524, 0.53, 0.107)


def measure(label: str, trials: int) -> None:
    a, r, m = MARS
    hist = worlds.history(None, SUN, a, r, m, False, 1.0, 8.0, born=interior.SUN_BORN_GYR)
    spans = worlds.windows(hist)
    print(f"\n== Mars, {label} ==")
    print("  green spans (Gyr after the Sun's birth):", [[round(x, 2) for x in s] for s in spans] or "never")
    area = 4 * math.pi * (r * interior.R_EARTH_M) ** 2
    crowd = geometry.vertical(8.0, interior.SOLAR_AGE_GYR, 0.5, 0.0)["exposure"]
    mu = life.EXTINCTIONS_PER_GYR * crowd
    first = None
    for h in hist:
        med = worlds.best(h["media"], "biotic")
        if med is None:
            continue
        lad = life.ladder(med, area)
        tag = f"  age {h['age']:5.2f}: {med['solvent']} {med['where']} {med['t']:.0f} K, p {h['p_bar']:.3g} bar,"
        if lad is None:
            print(tag, "cannot copy faithfully")
            continue
        means = [s["mean_gyr"] for s in lad["steps"]]
        print(tag, f"eps0 {lad['eps0']:.2e}, {len(means)} rungs{'' if lad['complete'] else ' (incomplete)'}, "
                   f"mean to a mind {sum(means):.3g} Gyr")
        if first is None and lad["complete"]:
            first = (h, lad, means)
    if first is None:
        print("  no green age holds a ladder to a mind")
        return
    h, lad, means = first
    print(f"  ladder at age {h['age']:.2f}:")
    for n, s in enumerate(lad["steps"]):
        print(f"    rung {n + 1}: {s['bits']:.3g} bits, mean {s['mean_gyr']:.3g} Gyr, eps {s['eps']:.2e}, "
              f"feeds {s['population']:.3g}")
    end = spans[-1][1] if spans else 0.0
    start = max(creation.CRUST_GYR, spans[0][0] if spans else creation.CRUST_GYR)
    rng = random.Random(1)
    now, by_end = 0, 0
    for _ in range(trials):
        got = life.climb(rng, means, start, end, float("inf"), mu)
        if len(got["times"]) == len(means):
            by_end += 1
            if got["times"][-1] <= interior.SOLAR_AGE_GYR:
                now += 1
    print(f"  chance of a mind by now ({interior.SOLAR_AGE_GYR} Gyr): {now / trials:.3f}; "
          f"by the end of its green span ({end:.2f} Gyr): {by_end / trials:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=500)
    a = ap.parse_args()
    measure("as made", a.trials)
    keep = worlds.STRIP_RATE
    worlds.STRIP_RATE = 0.0
    try:
        measure("kept green (its sky never broken)", a.trials)
    finally:
        worlds.STRIP_RATE = keep


if __name__ == "__main__":
    main()
