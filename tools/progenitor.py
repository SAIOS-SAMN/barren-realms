"""
The progenitors' bench: rebuild universes under other laws and measure what changes - never one run, always a spread.

  python3 tools/progenitor.py --seeds 1-5                          # an ensemble of our universe's laws
  python3 tools/progenitor.py --seeds 1-5 --laws alpha=1.02         # the same initial conditions under stronger electromagnetism
  python3 tools/progenitor.py --seed 7 --sensitivity                # each law and declared number nudged: how far
                                                                    # the universe's outcomes move
  python3 tools/progenitor.py --earth                               # Earth as a test: its place and time, our laws

What is measured (creation.limits on a sample of the galaxy's cells): the share of worlds with life, how far the
living got, the rungs their chemistries need, minds per thousand worlds, what stopped the rest. A balanced universe
gives a broad, stable spread; an outcome that swings on one declared number is the next to be given better physics
(docs/DIMENSIONS.md).
"""

import argparse
import json
import math
import os
import statistics
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xylarium.kernel import creation, fundamental, interior, life, worlds  # noqa: E402

DECLARED = [                      # (module, name): the declared numbers the sensitivity sweep nudges
    ("life", "DISCRIMINATION"), ("life", "I_MIND"), ("life", "BODY_PER_MONOMER"), ("life", "EXTINCTIONS_PER_GYR"),
    ("life", "STERILISE_AT_R0"), ("worlds", "SOLVENT_BARRIER"), ("worlds", "GREENHOUSE_TAU"), ("worlds", "STRIP_RATE"),
    ("worlds", "HOT_EV"), ("worlds", "DELIVERED"), ("worlds", "PHOTO_LOW"), ("worlds", "WEATHER_SCALE"),
    ("interior", "TIDAL_Q"), ("interior", "CREEP_EA"),
]
MODULES = {"life": life, "worlds": worlds, "interior": interior}


def _seeds(text: str) -> List[int]:
    if "-" in text:
        a, b = text.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in text.split(",")]


def _key(seed: int, kind: str, laws: str) -> Any:
    if not laws and kind == "measured":
        return seed
    return f"{seed}:{kind}" + (f":{laws}" if laws else "")


def _forget() -> None:
    creation._CACHE.clear()


def measure(key: Any, every: int) -> Dict[str, Any]:
    """One universe's outcomes, from a sample of its cells."""
    _forget()
    lim = creation.limits(key, every)
    n = max(1, lim["worlds"])
    return {"key": str(key), "worlds": lim["worlds"], "alive": round(lim["alive"] / n, 4),
            "minds_per_k": round(1000.0 * lim["minds"] / n, 3), "no_solvent": round(lim["no_solvent"] / n, 4),
            "cannot_copy": round(lim["cannot_copy"] / n, 4), "too_slow": round(lim["too_slow"] / n, 4),
            "star_died": round(lim["star_died"] / n, 4), "sterilised": round(lim["sterilised"] / n, 4),
            "unfed": round(lim["unfed"] / n, 4), "by_region": lim["by_region"],
            "rungs": dict(sorted(lim["rungs"].items())), "laws": fundamental.of(key).summary()}


def ensemble(seeds: List[int], kind: str, laws: str, every: int) -> Dict[str, Any]:
    runs = [measure(_key(s, kind, laws), every) for s in seeds]
    out: Dict[str, Any] = {"runs": runs}
    for f in ("alive", "minds_per_k", "no_solvent", "cannot_copy", "too_slow", "sterilised", "unfed"):
        xs = [r[f] for r in runs]
        out[f] = {"mean": round(statistics.mean(xs), 4), "sd": round(statistics.pstdev(xs), 4),
                  "min": min(xs), "max": max(xs)}
    return out


def sensitivity(seed: int, kind: str, every: int, delta: float) -> List[Dict[str, Any]]:
    """Elasticity of each outcome to each law and declared number: d ln(outcome) / d ln(input), by central difference."""
    base = measure(_key(seed, kind, ""), every)
    rows = []
    for name in fundamental.NAMES:
        up = measure(_key(seed, kind, f"{name}={1 + delta:g}"), every)
        down = measure(_key(seed, kind, f"{name}={1 - delta:g}"), every)
        rows.append(_row(f"law {name}", base, up, down, delta))
    for mod, name in DECLARED:
        m = MODULES[mod]
        v0 = getattr(m, name)
        try:
            setattr(m, name, v0 * (1 + delta))
            up = measure(_key(seed, kind, ""), every)
            setattr(m, name, v0 * (1 - delta))
            down = measure(_key(seed, kind, ""), every)
        finally:
            setattr(m, name, v0)
        rows.append(_row(f"{mod}.{name}", base, up, down, delta))
    _forget()
    return rows


def _row(label: str, base: Dict[str, Any], up: Dict[str, Any], down: Dict[str, Any], delta: float) -> Dict[str, Any]:
    span = math.log((1 + delta) / (1 - delta))
    out = {"input": label}
    for f in ("alive", "minds_per_k"):
        a, b = up[f], down[f]
        out[f] = round(math.log(max(1e-9, a) / max(1e-9, b)) / span, 3) if a > 0 and b > 0 else (
            "appears" if a > 0 else "vanishes" if b > 0 else 0.0)
    out["base"] = {"alive": base["alive"], "minds_per_k": base["minds_per_k"]}
    return out


def earth() -> Dict[str, Any]:
    """Earth as a test: a solar-mass star born 9.2 Gyr after the Big Bang at 8 kpc, a unit world at 1 AU, read 4.57
    Gyr later - our laws, no Earth number set anywhere but its place and time. Measured values beside."""
    w = worlds.build(None, {"mass": "1", "luminosity": "1"}, 1.0, 1.0, 1.0, False, 1.0, 8.0, 4.57,
                     born=interior.SUN_BORN_GYR)
    ms = worlds.media(None, {"mass": "1", "luminosity": "1"}, 1.0, 1.0, 1.0, False, 1.0, 8.0, 4.57, world=w)
    bio = worlds.best(ms, "biotic")
    lad = life.ladder(bio, 4 * math.pi * interior.R_EARTH_M ** 2) if bio else None
    means = [s["mean_gyr"] for s in (lad or {}).get("steps", [])]
    return {
        "surface_K": [round(w["t_surf"], 1), 288.0], "pressure_bar": [round(w["p_bar"], 3), 1.013],
        "air": {k: round(v, 5) for k, v in w["air"].items()},
        "heat_flow_W_m2": [round(w["q"], 4), 0.087], "dynamo": [w["field"], "yes (weakly)"],
        "copying_error_per_monomer": [round(lad["eps0"], 6) if lad else None, "1e-4..1e-5 unchecked"],
        "rungs_to_a_mind": [len(means), "~4 hard steps (Carter, Watson)"],
        "mean_gyr_to_life": [round(means[0], 4) if means else None, "<0.8 after the crust settled"],
        "mean_gyr_to_a_mind": [round(sum(means), 3) if means else None, "~4 (one history)"],
        "chance_of_a_mind_within_its_star": [round(life.sum_cdf(means, 10.0 - creation.CRUST_GYR), 3)
                                             if means else 0.0, "1 (we are here)"],
        "light_that_drives_chemistry": [round(worlds.band(5772)["drive"], 3), "~0.45 (400-700 nm)"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", default="7")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--kind", default="measured")
    ap.add_argument("--laws", default="", help="e.g. alpha=1.02,alpha_G=0.9")
    ap.add_argument("--every", type=int, default=25, help="sample every n-th cell")
    ap.add_argument("--sensitivity", action="store_true")
    ap.add_argument("--delta", type=float, default=0.05)
    ap.add_argument("--earth", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.earth:
        res: Any = earth()
    elif a.sensitivity:
        res = sensitivity(a.seed, a.kind, a.every, a.delta)
    else:
        res = ensemble(_seeds(a.seeds), a.kind, a.laws, a.every)
    text = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
