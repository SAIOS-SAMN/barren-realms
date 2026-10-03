"""
Red Mars and green Mars, by our own physics: which conditions keep it green, which turn it red, and what its xenon
says about why.

  python3 tools/mars.py                 # the conditions sweep and the xenon record
  python3 tools/mars.py --trials 2000   # more draws of its life's chances

Every row changes one physical condition from Mars as our formulas make it (0.107 Earth masses at 1.524 AU around
a sun born 9.2 Gyr after the Big Bang) - conditioning, not tuning - and reports how long it was green, its air and
temperature through time, and the chance its life reached a mind by the Sun's present age.

The xenon record: xenon-129 / xenon-132 and xenon-136 / xenon-132 in its air (noble.py) - natural, and after a
fission war - set against Earth's, built the same way. Mars's air today is measured at 129/132 ~ 2.5; Earth's 0.98;
the solar mix 1.04.
"""

import argparse
import math
import os
import random
import sys
from contextlib import contextmanager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from xylarium.kernel import creation, geometry, interior, life, noble, worlds  # noqa: E402

SUN = {"mass": "1", "luminosity": "1"}
NOW = interior.SOLAR_AGE_GYR
AGES = (0.01, 0.03, 0.1, 0.2, 0.3, 0.45, 0.6, 0.8, 1.0, 1.5, 2.0, 3.0, 4.0, 4.57, 6.0, 8.0, 10.0)
MARS = {"a": 1.524, "mass": 0.107, "radius": 0.53}


@contextmanager
def patched(obj, name, value):
    keep = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, keep)


def history(a, mass, radius):
    out = []
    for age in AGES:
        w = worlds.build(None, SUN, a, radius, mass, False, 1.0, 8.0, age, born=interior.SUN_BORN_GYR)
        ms = worlds.media(None, SUN, a, radius, mass, False, 1.0, 8.0, age, world=w)
        out.append(dict(w, age=age, media=ms, green=any(m["region"] == "biotic" for m in ms)))
    return out


def mind_chance(hist, radius, trials):
    spans = worlds.windows(hist)
    if not spans:
        return 0.0, 0.0
    area = 4 * math.pi * (radius * interior.R_EARTH_M) ** 2
    first = next((h for h in hist if h["green"]), None)
    med = worlds.best(first["media"], "biotic")
    lad = life.ladder(med, area) if med else None
    if not lad or not lad["complete"]:
        return 0.0, 0.0
    means = [s["mean_gyr"] for s in lad["steps"]]
    mu = life.EXTINCTIONS_PER_GYR * geometry.vertical(8.0, NOW, 0.5, 0.0)["exposure"]
    rng = random.Random(1)
    now = total = 0
    start, end = max(creation.CRUST_GYR, spans[0][0]), spans[-1][1]
    for _ in range(trials):
        got = life.climb(rng, means, start, end, float("inf"), mu)
        if len(got["times"]) == len(means):
            total += 1
            now += got["times"][-1] <= NOW
    return now / trials, sum(means)


def row(label, trials, a=MARS["a"], mass=MARS["mass"], radius=MARS["radius"]):
    hist = history(a, mass, radius)
    spans = worlds.windows(hist)
    green = sum(e - s for s, e in spans)
    p_now, mean = mind_chance(hist, radius, trials)
    at = {h["age"]: h for h in hist}
    cells = "  ".join(f"{t}:{at[t]['p_bar']:.2g}b/{at[t]['t_surf']:.0f}K" for t in (0.3, 1.0, 3.0, NOW))
    print(f"{label:<40} green {green:5.2f} Gyr  mind by now {p_now:5.3f}  (climb {mean:.3g} Gyr)  {cells}")
    return hist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=500)
    a = ap.parse_args()
    t = a.trials
    print("== conditions: one physical change at a time ==")
    mars = row("Mars as our physics makes it", t)
    with patched(worlds, "STRIP_RATE", 0.0):
        row("its sky never broken (no escape)", t)

    real_evolve = interior.evolve

    def kept_field(*args, **kw):
        out = real_evolve(*args, **kw)
        return dict(out, field=max(1.0, out["field"]))
    with patched(interior, "evolve", kept_field):
        row("a dynamo that never stops", t)
    for m in (0.2, 0.3, 0.5):
        row(f"heavier: {m} Earth masses", t, mass=m, radius=MARS["radius"] * (m / MARS["mass"]) ** 0.27)
    for d in (1.3, 1.15):
        row(f"closer: {d} AU", t, a=d)
    for f in (3.0, 10.0):
        with patched(worlds, "DELIVERED", worlds.DELIVERED * f):
            row(f"{f:.0f}x the volatiles delivered", t)
    real_act, real_dose = worlds.activity, worlds.dose
    with patched(worlds, "activity", lambda m, age: 1.0 + 2.0 * math.exp(-max(0.0, age) * max(0.05, m) ** 2)), \
            patched(worlds, "dose", lambda m, age: max(0.0, age) + 2.0 * (1.0 - math.exp(-max(0.0, age) *
                                                                                      max(0.05, m) ** 2)) / max(0.05, m) ** 2):
        row("a quieter young Sun (saturation 3x, not 10x)", t)
    for shield_at in (0.3, 0.45):
        with patched(worlds, "dose", lambda m, age, s=shield_at: real_dose(m, min(age, s))):
            row(f"a people shields its sky from {shield_at} Gyr", t)

    print("\n== xenon in the air (ratios to xenon-132) ==")
    earth = history(1.0, 1.0, 1.0)
    for name, hist, mass, radius, a_au in (("Mars", mars, MARS["mass"], MARS["radius"], MARS["a"]),
                                           ("Earth", earth, 1.0, 1.0, 1.0)):
        rec = noble.air_xenon(mass, radius, a_au, 1.0, hist)
        meta, now = rec[0], next(r for r in rec[1:] if r["age"] == NOW)
        print(f"  {name:<6} natural: mantle closed at {meta['closure_myr']} Myr, crossover {meta['crossover_amu']} amu, "
              f"first air lost {meta['first_air_lost']:.0%} -> now 129/132 {now['129/132']}, "
              f"136/132 {now['136/132']}")
    for joules in (1e18, 1e22, 1e26):
        rec = noble.air_xenon(MARS["mass"], MARS["radius"], MARS["a"], 1.0, mars,
                              wars=[{"age": 0.5, "fission_j": joules}])
        now = next(r for r in rec[1:] if r["age"] == NOW)
        print(f"  Mars after an ancient fission war of {joules:.0e} J at 0.5 Gyr: 129/132 {now['129/132']}, "
              f"136/132 {now['136/132']}, 134/132 {now['134/132']}")
    print(f"  fission xenon, its iodine-129 fully decayed, holds 129/132 = {noble.fission_129_132():.2f}: a fission war "
          f"pulls an air toward that - it cannot raise 129/132 past the solar 1.04. Antimatter adds no xenon.")
    print("  (absolute ratios run high: early xenon loss - ions in hydrogen winds, giant impacts - is not yet "
          "modelled; the ordering by mantle closure and the fission bound do not depend on it)")


if __name__ == "__main__":
    main()
