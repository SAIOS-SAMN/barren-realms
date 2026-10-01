"""
The living universe: seeds that run continuously, survive code changes, and stop only when a law breaks.

    python3 tools/live.py --seed 7                 # run (resumes from runs/seed7/snapshot.json if present)
    python3 tools/live.py --seed 7 --fresh         # begin a new universe
    python3 tools/live.py --seed 7 --show 5        # the last 5 observations, readably

Every quarter the money and matter residuals (everything counted minus everything declared) must not move: that
is conservation, the one hard law. If it moves, or anything raises, the runner writes the state and the cause to
runs/seed<N>/crash/ and stops - fix forward from that exact moment. Every --every cycles it saves a snapshot
(atomically) and appends one observation line to runs/seed<N>/observations.jsonl. A code change takes effect by
restarting the runner: the universe resumes from its last snapshot and keeps living through the upgrade.
"""

import argparse
import json
import os
import random
import signal
import sys
import time
import traceback
from collections import Counter
from typing import Any, Dict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from xylarium.kernel import matter, subsystem  # noqa: E402
from xylarium.kernel.engine import GameKernel  # noqa: E402
from xylarium.kernel.ledger import money_supply  # noqa: E402
from xylarium.persistence.store import StatePersistence  # noqa: E402

import simulate_playtest as harness  # noqa: E402

QUARTER = 25


def residual(kernel: Any) -> Dict[str, int]:
    """Everything counted minus everything declared: matter per commodity, money per currency ($)."""
    tt, nn = matter.totals(kernel), kernel.matter.net()
    out = {c: tt.get(c, 0) - nn.get(c, 0) for c in set(tt) | set(nn)}
    ms, ln = money_supply(kernel), harness.ledger_net(kernel)
    for cur in set(ms) | set(ln):
        out["$" + cur] = ms.get(cur, {}).get("total", 0) - ln.get(cur, 0)
    return out


def moved(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
    return {c: v for c in set(a) | set(b) if (v := b.get(c, 0) - a.get(c, 0))}


def gini(xs) -> float:
    xs = sorted(max(0, x) for x in xs)
    n, s = len(xs), sum(xs)
    if n == 0 or s == 0:
        return 0.0
    return round(sum((2 * i - n + 1) * x for i, x in enumerate(xs)) / (n * s), 3)


def observe(kernel: Any, wall: float, rate: float) -> Dict[str, Any]:
    """One line of the universe's vital signs."""
    worlds = [p for s in kernel.sectors.values() for p in s.planets if p.population > 0 and not p.natives]
    sums = subsystem.summaries(kernel)
    pol = kernel.monetary_policy
    supply = {c: b["total"] for c, b in money_supply(kernel).items()}
    obs = {
        "cycle": kernel.cycle_count, "wall_s": round(wall), "cyc_per_s": round(rate, 1),
        "people": sum(p.population for p in worlds), "worlds": len(worlds), "sectors": len(kernel.sectors),
        "captains": len(kernel.captains),
        "gini": gini(harness.net_worth_sol(kernel, c) for c in kernel.captains.values()),
        "fx": {c: round(kernel.fx_market.rate(c), 3) for c in kernel.fx_market.pools},
        "m_over_mstar": {c: round(supply[c] / t, 3) for c, t in pol.current.items() if t and c in supply},
    }
    for name in ("sustenance", "fertility", "nursery", "knowledge", "chemistry", "intellect", "genome", "introspect", "liquidity", "regimes", "enterprise", "liquidation", "waystations", "observation", "realms", "relations", "prices"):
        if name in sums:
            obs[name] = sums[name]
    g = kernel.state.get("genesis") or {}
    obs["genesis"] = g.get("mode", "settled")
    if g.get("firsts") is not None:
        obs["firsts"] = g["firsts"]
    obs["ports"] = sum(1 for s in kernel.sectors.values() if s.port is not None)
    obs["citadels"] = {str(t): sum(1 for p in worlds if p.citadel_level == t) for t in sorted({p.citadel_level for p in worlds})}
    return obs


def show(path: str, n: int) -> None:
    if not os.path.exists(path):
        print("no observations yet")
        return
    with open(path) as f:
        lines = f.readlines()[-n:]
    for line in lines:
        o = json.loads(line)
        su = (o.get("sustenance") or {}).get("by_metabolism", {})
        fed = " ".join(f"{m[:4]}:{v['people'] // 1000}k@{v['self_sufficiency']:.0%}" for m, v in
                       sorted(su.items(), key=lambda kv: -kv[1]["people"]))
        wars = (o.get("sustenance") or {}).get("wars_active", 0)
        print(f"c{o['cycle']:>7} {o['cyc_per_s']:>5}/s  people {o['people']:>10,} worlds {o['worlds']:>4} "
              f"sectors {o['sectors']:>4} gini {o['gini']:.2f}  M/M* {o['m_over_mstar']}  fx {o['fx']}  "
              f"wars {wars}  {fed}")


def save(kernel: Any, path: str) -> None:
    tmp = path + ".tmp"
    StatePersistence.save_to_file(kernel, tmp)
    os.replace(tmp, path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Xylarium living universe")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dir", default=os.path.join(ROOT, "runs"))
    ap.add_argument("--every", type=int, default=500, help="cycles between snapshots and observations")
    ap.add_argument("--cycles", type=int, default=0, help="stop after this many cycles (0: run forever)")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--genesis", default="settled", choices=("settled", "primordial"),
                    help="primordial: every people on its homeworld, nothing spacefaring (no bots)")
    args = ap.parse_args()
    home = os.path.join(args.dir, f"seed{args.seed}")
    os.makedirs(os.path.join(home, "crash"), exist_ok=True)
    snap, obs_path = os.path.join(home, "snapshot.json"), os.path.join(home, "observations.jsonl")
    if args.show:
        show(obs_path, args.show)
        return

    random.seed(args.seed)
    kernel = None
    if os.path.exists(snap) and not args.fresh:
        kernel = StatePersistence.load_from_file(snap)
        print(f"resumed seed {args.seed} at cycle {kernel.cycle_count}", flush=True)
    if kernel is None:
        if args.fresh and os.path.exists(obs_path):
            os.replace(obs_path, obs_path + f".{int(time.time())}")
        kernel = GameKernel(seed=args.seed, genesis=args.genesis)
        print(f"genesis ({args.genesis}) of seed {args.seed}", flush=True)
    kernel.activate()
    # the bots are captains of this universe: a resumed universe already holds them
    real_register = kernel.register_player
    kernel.register_player = lambda pid, *a, **kw: kernel.captains.get(pid) or real_register(pid, *a, **kw)
    rng = random.Random(args.seed * 7919 + kernel.cycle_count)
    random.seed(args.seed * 7919 + kernel.cycle_count)
    primordial = (kernel.state.get("genesis") or {}).get("mode") == "primordial"
    bots = [] if primordial else harness.make_players(kernel, rng)      # nothing to trade with yet: we watch
    kernel.register_player = real_register
    stats = harness.RunStats()
    tick = kernel.tick_simulation
    kernel.tick_simulation = lambda: None

    stop = {"now": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(now=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(now=True))

    base = residual(kernel)
    start_cycle, t0 = kernel.cycle_count, time.perf_counter()
    win_t, win_c = t0, kernel.cycle_count

    def crash(why: str) -> None:
        stamp = os.path.join(home, "crash", f"cycle{kernel.cycle_count}")
        try:
            save(kernel, stamp + ".json")
        except Exception:
            pass
        with open(stamp + ".txt", "w") as f:
            f.write(why)
        print(f"LAW BROKEN at cycle {kernel.cycle_count}: see {stamp}.txt", flush=True)
        sys.exit(2)

    while not stop["now"]:
        try:
            for b in bots:
                b.act(kernel, stats)
            tick()
        except SystemExit:
            raise
        except Exception:
            crash(f"exception at cycle {kernel.cycle_count}\n{traceback.format_exc()}")
        c = kernel.cycle_count
        if c % QUARTER == 0:
            d = moved(base, residual(kernel))
            if d:
                crash(f"conservation broken in the quarter ending cycle {c}: {d}\n"
                      f"(counted minus declared moved; bisect with XYL_AUDIT=1 XYL_AUDIT_FROM={c - QUARTER} "
                      f"in simulate_playtest, or reload this crash snapshot)")
        if c % args.every == 0:
            now = time.perf_counter()
            line = observe(kernel, now - t0, (c - win_c) / max(1e-9, now - win_t))
            win_t, win_c = now, c
            with open(obs_path, "a") as f:
                f.write(json.dumps(line, default=str) + "\n")
            save(kernel, snap)
            base = residual(kernel)            # a save/load round trip may re-baseline declared totals
            print(f"cycle {c}: {line['people']:,} people on {line['worlds']} worlds, {line['cyc_per_s']}/s",
                  flush=True)
        if args.cycles and c - start_cycle >= args.cycles:
            break
    save(kernel, snap)
    print(f"stopped at cycle {kernel.cycle_count}; snapshot saved", flush=True)


if __name__ == "__main__":
    main()
