"""
Scenarios by conditioning, not tuning: what the cosmos looks like if a premise about our own system held.

  python3 tools/scenarios.py --samples 400 --galaxies 6          # all four groups
  python3 tools/scenarios.py --samples 60 --galaxies 2 --every 60 # a quick look

No number is set to make a premise true. The engine's declared numbers (docs/DIMENSIONS.md) are given ranges -
priors - and many universes are drawn from them. Each is first tested on our own system at its own place and time
(a sun born 9.2 Gyr after the Big Bang, 8 kpc out): its Earth's climb to a mind (many rolls of its dice) and its
Mars's history. Each universe is then weighted by how well its own formulas produce the premise:

  baseline   every universe drawn, unweighted
  dinosaurs  a mind arises on Earth in the Mesozoic window (252-66 Myr ago: 4.32-4.51 Gyr after the Sun's birth),
             weighted by the share of the dice that put it there
  green mars Mars is green - liquid water at its surface, life on it - for at least GREEN_MIN at some point
  both       both at once

Universes drawn by weight are then built galaxy-wide (creation.limits on a sample of cells) and measured: how common
life and minds are, when the first arise, how many arose long before us, how many systems were green and stayed
green, and how many peoples were old enough - and near enough - to have reached Mars while it was green with the
energy to strip its air (that energy is physics: its air's mass x its escape energy). Whether any of them would
have chosen to is not physics; the engine's peoples decide that in play.
"""

import argparse
import json
import math
import multiprocessing as mp
import os
import random
import statistics
import sys
import time
from typing import Any, Dict, List, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from xylarium.kernel import creation, geometry, interior, life, worlds  # noqa: E402

SUN = {"mass": "1", "luminosity": "1"}
SUN_BORN = interior.SUN_BORN_GYR
NOW = interior.SOLAR_AGE_GYR                    # Gyr after the Sun's birth
MESOZOIC = (NOW - 0.252, NOW - 0.066)
GREEN_MIN = 0.1                                 # Gyr: long enough to call a world green, not a passing thaw
TRIALS = 300                                    # rolls of Earth's dice per universe

# the priors: (module, name, kind, lo, hi); kind log / lin / choice / int-log
PRIORS = [
    ("worlds", "SOLVENT_BARRIER", "lin", 15.0, 35.0),
    ("life", "I_MIND", "log", 1e8, 1e10),
    ("life", "DISCRIMINATION", "lin", 0.3, 1.0),
    ("life", "EXTINCTIONS_PER_GYR", "log", 0.5, 8.0),
    ("life", "ERASURE", "choice", ("rung", "clades"), None),
    ("life", "CLADES", "intlog", 1, 20),
    ("life", "KILL_SHAPE", "lin", 1.0, 8.0),
    ("worlds", "STRIP_RATE", "log", 2e-7, 2e-5),
    ("worlds", "HOT_EV", "lin", 1.5, 5.0),
    ("worlds", "MAGMA_DEGAS", "lin", 0.5, 1.0),
    ("worlds", "DELIVERED", "log", 3e-5, 3e-4),
    ("scenario", "T_TECH_GYR", "log", 1e-5, 1e-2),          # from a mind to the power to strip a world's air
    ("scenario", "SPEED_C", "log", 1e-3, 1e-1),             # how fast such a people travels, over c
]
MODULES = {"worlds": worlds, "life": life}
C_KPC_PER_GYR = 306.6e3


def draw(rng: random.Random) -> Dict[str, Any]:
    out = {}
    for mod, name, kind, lo, hi in PRIORS:
        if kind == "lin":
            v = lo + (hi - lo) * rng.random()
        elif kind == "log":
            v = math.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * rng.random())
        elif kind == "intlog":
            v = int(round(math.exp(math.log(lo) + (math.log(hi) - math.log(lo)) * rng.random())))
        else:
            v = lo[int(rng.random() * len(lo))]
        out[f"{mod}.{name}"] = v
    return out


def apply(params: Dict[str, Any]) -> None:
    for key, v in params.items():
        mod, name = key.split(".")
        if mod in MODULES:
            setattr(MODULES[mod], name, v)
    creation._CACHE.clear()


# ---------------------------------------------------------------------- our system as the test
def _ladder_means(hist: List[Dict[str, Any]], radius: float) -> Tuple[List[float], bool]:
    at = next(h for h in hist if h["age"] >= creation.SETTLED_GYR)
    med = worlds.best(at["media"], "biotic")
    if med is None:
        return [], False
    lad = life.ladder(med, 4 * math.pi * (radius * interior.R_EARTH_M) ** 2)
    if lad is None:
        return [], False
    return [s["mean_gyr"] for s in lad["steps"]], lad["complete"]


def sol(params: Dict[str, Any]) -> Dict[str, Any]:
    """Our system under a universe's numbers: Earth's climb (TRIALS rolls) and Mars's history."""
    apply(params)
    earth = worlds.history(None, SUN, 1.0, 1.0, 1.0, False, 1.0, 8.0, born=SUN_BORN)
    mars = worlds.history(None, SUN, 1.524, 0.53, 0.107, False, 1.0, 8.0, born=SUN_BORN)
    means, complete = _ladder_means(earth, 1.0)
    vert = geometry.vertical(8.0, NOW, 0.5, 0.0)
    crowd = vert["exposure"]                                     # the Sun's ring: unit density
    mu = life.EXTINCTIONS_PER_GYR * crowd
    green_earth = worlds.windows(earth)
    end = green_earth[-1][1] if green_earth else 0.0             # Earth's own habitable span ends the climb
    minds = []
    if means and complete:
        rng = random.Random(1)
        for _ in range(TRIALS):
            live = math.exp(-life.STERILISE_AT_R0 * crowd * end / 10.0)
            steril = creation.CRUST_GYR + rng.random() * end if rng.random() >= live else float("inf")
            got = life.climb(rng, means, creation.CRUST_GYR, end, steril, mu)
            if len(got["times"]) == len(means):
                minds.append(got["times"][-1])
    spans = worlds.windows(mars)
    green = [s for s in spans if s[1] - s[0] >= GREEN_MIN]
    m_kg, r_m = 0.107 * interior.M_EARTH_KG, 0.53 * interior.R_EARTH_M
    g = interior.G_SI * m_kg / r_m ** 2
    p_max = max(h["p_bar"] for h in mars)
    air_kg = p_max * 1e5 * 4 * math.pi * r_m ** 2 / g
    mars_now = min(mars, key=lambda h: abs(h["age"] - NOW))
    return {
        "params": params,
        "earth_rungs": len(means), "earth_mean_gyr": round(sum(means), 4) if means else None,
        "p_mind_by_now": round(sum(1 for t in minds if t <= NOW) / TRIALS, 4),
        "p_mesozoic": round(sum(1 for t in minds if MESOZOIC[0] <= t <= MESOZOIC[1]) / TRIALS, 4),
        "p_mind_before_mesozoic": round(sum(1 for t in minds if t < MESOZOIC[0]) / TRIALS, 4),
        "earth_green": green_earth, "mars_green": green, "mars_green_now": bool(mars_now["green"]),
        "mars_p_now": round(mars_now["p_bar"], 4), "mars_p_max": round(p_max, 4),
        "strip_energy_j": float(f"{air_kg * interior.G_SI * m_kg / r_m:.3g}"),
    }


# ---------------------------------------------------------------------- the galaxy under a universe's numbers
def galaxy(job: Tuple[Dict[str, Any], int, int, Dict[str, Any]]) -> Dict[str, Any]:
    params, seed, every, sol_rec = job
    apply(params)
    lim = creation.limits(seed, every)
    n = max(1, lim["worlds"])
    epochs = sorted(e[0] for e in lim["epochs"])
    us = SUN_BORN + NOW
    out = {"seed": seed, "worlds": lim["worlds"], "alive": round(lim["alive"] / n, 4),
           "minds_per_k": round(1000.0 * lim["minds"] / n, 3), "minds_sampled": lim["minds"],
           "first_mind_gyr": epochs[0] if epochs else None,
           "median_mind_gyr": statistics.median(epochs) if epochs else None,
           "share_older_than_us_by_1gyr": round(sum(1 for e in epochs if e < us - 1.0) / max(1, len(epochs)), 4),
           "by_region": lim["by_region"]}
    # peoples able to have reached Mars while it was green, with the power to strip it (sampled cells scaled up)
    if sol_rec["mars_green"]:
        g_end = SUN_BORN + sol_rec["mars_green"][-1][1]
        t_tech, v = params["scenario.T_TECH_GYR"], params["scenario.SPEED_C"]
        expected = 0.0
        for e, r, _ in lim["epochs"]:
            avail = g_end - e - t_tech
            if avail <= 0:
                continue
            reach = min(30.0, v * C_KPC_PER_GYR * avail)
            x = (r * r + 64.0 - reach * reach) / (16.0 * max(1e-6, r))
            expected += 1.0 if x <= -1 else 0.0 if x >= 1 else math.acos(x) / math.pi
        out["could_reach_green_mars"] = round(expected * every, 2)
    # how many systems were ever green, and stayed so (a sample of worlds read through their histories)
    rng = random.Random(seed)
    ever = stayed = sampled = 0
    from xylarium.kernel import cosmos
    cells = cosmos.cells()[::every]
    for _ in range(60):
        i, j = cells[int(rng.random() * len(cells))]
        slots = [s for s in creation.cell(seed, i, j) if s.get("worlds")]
        if not slots:
            continue
        sl = slots[int(rng.random() * len(slots))]
        w = sl["worlds"][int(rng.random() * len(sl["worlds"]))]
        if w["body"].get("giant"):
            continue
        from fractions import Fraction
        b, mk = w["body"], w.get("make") or {}
        h = worlds.history(seed, sl["spec"], float(Fraction(str(b["q"]))) ** 2, float(Fraction(str(b["radius"]))),
                           float(Fraction(str(b["mass"]))), False, sl["z"], sl["r"], w.get("ices"),
                           born=mk.get("born"), orbit=mk.get("orbit"), core=mk.get("core"),
                           ages=(0.5, 1.0, 2.0, 3.0, 5.0, 8.0))
        sampled += 1
        if any(x["green"] for x in h):
            ever += 1
            stayed += 1 if h[-1]["green"] else 0
    out["rocky_ever_green"] = round(ever / max(1, sampled), 3)
    out["rocky_green_at_8gyr"] = round(stayed / max(1, sampled), 3)
    return out


def _weights(recs: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    return {
        "baseline": [1.0 for _ in recs],
        "dinosaurs": [r["p_mesozoic"] for r in recs],
        "green_mars": [1.0 if r["mars_green"] else 0.0 for r in recs],
        "both": [r["p_mesozoic"] * (1.0 if r["mars_green"] else 0.0) for r in recs],
    }


def _pick(rng: random.Random, w: List[float], k: int) -> List[int]:
    idx = [i for i, x in enumerate(w) if x > 0]
    out = []
    while idx and len(out) < k:
        total = sum(w[i] for i in idx)
        u, acc = rng.random() * total, 0.0
        for i in idx:
            acc += w[i]
            if acc >= u:
                out.append(i)
                idx.remove(i)
                break
    return out


def _summary(recs: List[Dict[str, Any]], w: List[float]) -> Dict[str, Any]:
    tot = sum(w)
    if tot <= 0:
        return {"accepted": 0}

    def wmean(f):
        return round(sum(x * f(r) for x, r in zip(w, recs)) / tot, 4)
    out = {"accepted": sum(1 for x in w if x > 0), "effective_samples": round(tot * tot / sum(x * x for x in w), 1),
           "earth_rungs": wmean(lambda r: r["earth_rungs"]),
           "p_mind_by_now": wmean(lambda r: r["p_mind_by_now"]),
           "mars_green_now": wmean(lambda r: 1.0 if r["mars_green_now"] else 0.0),
           "mars_p_max_bar": wmean(lambda r: r["mars_p_max"])}
    for key, *_ in [(f"{m}.{n}",) for m, n, *_ in PRIORS]:
        vals = [r["params"][key] for r in recs]
        if isinstance(vals[0], str):
            out[key] = {v: round(sum(x for x, r in zip(w, recs) if r["params"][key] == v) / tot, 3) for v in set(vals)}
        else:
            out[key] = round(math.exp(sum(x * math.log(max(1e-300, float(v))) for x, v in zip(w, vals)) / tot), 6)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", type=int, default=400)
    ap.add_argument("--galaxies", type=int, default=6, help="galaxy builds per group")
    ap.add_argument("--every", type=int, default=30)
    ap.add_argument("--procs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--rng", type=int, default=2026)
    ap.add_argument("--out", default=os.path.join(ROOT, "runs", "scenarios"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = random.Random(a.rng)
    t0 = time.time()
    params = [draw(rng) for _ in range(a.samples)]
    with mp.Pool(a.procs) as pool:
        recs = pool.map(sol, params, chunksize=4)
    print(f"[{time.time() - t0:.0f}s] tested our system in {len(recs)} universes", flush=True)
    weights = _weights(recs)
    groups: Dict[str, Any] = {}
    jobs, owners = [], []
    for name, w in weights.items():
        groups[name] = {"premise": _summary(recs, w), "galaxies": []}
        for n, i in enumerate(_pick(rng, w, a.galaxies)):
            jobs.append((recs[i]["params"], 1 + (n % 8), a.every, recs[i]))
            owners.append(name)
    with mp.Pool(a.procs) as pool:
        for name, res in zip(owners, pool.imap(galaxy, jobs)):
            groups[name]["galaxies"].append(res)
            print(f"[{time.time() - t0:.0f}s] {name}: {json.dumps({k: res.get(k) for k in ('minds_per_k', 'first_mind_gyr', 'could_reach_green_mars')})}",
                  flush=True)
    for name, g in groups.items():
        gs = g["galaxies"]
        if not gs:
            continue
        agg = {}
        for f in ("alive", "minds_per_k", "first_mind_gyr", "median_mind_gyr", "share_older_than_us_by_1gyr",
                  "could_reach_green_mars", "rocky_ever_green", "rocky_green_at_8gyr"):
            xs = [x[f] for x in gs if x.get(f) is not None]
            if xs:
                agg[f] = {"median": round(statistics.median(xs), 4), "min": min(xs), "max": max(xs)}
        g["galaxy"] = agg
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(a.out, f"scenarios-{stamp}.json")
    with open(path, "w") as f:
        json.dump({"samples": a.samples, "every": a.every, "groups": groups, "sol": recs}, f, indent=1)
    print(json.dumps({k: {"premise": v["premise"], "galaxy": v.get("galaxy")} for k, v in groups.items()}, indent=1))
    print("written", path)


if __name__ == "__main__":
    main()
