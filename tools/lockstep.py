"""
Lockstep check: the same seed must make the same universe, however the machine runs it.

Runs one universe twice in separate processes - by default under different PYTHONHASHSEEDs, so dictionary and set
order differ - for the same number of cycles, saves both, and compares them. Prints the first paths where the two
universes differ, or that they are identical. Also prints the speed (universe-years per wall-minute).

  python3 tools/lockstep.py --seed 7 --genesis primordial --cycles 200
  python3 tools/lockstep.py --from runs/seed1337/snapshot.json --cycles 50
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

VOLATILE = {"logs", "radio"}          # text the universe wrote, not its state


def run_one(args: argparse.Namespace, out: str) -> None:
    import random
    from xylarium.kernel import clock
    from xylarium.kernel.engine import GameKernel
    from xylarium.persistence.store import StatePersistence
    random.seed(args.seed)
    if args.source:
        kernel = StatePersistence.load_from_file(args.source)
    else:
        kernel = GameKernel(seed=args.seed, genesis=args.genesis)
    kernel.activate()
    pace = clock.Pace(kernel)
    for _ in range(args.cycles):
        kernel.tick_simulation()
    print(json.dumps(pace.rate()), flush=True)
    StatePersistence.save_to_file(kernel, out)


def _diff(a, b, path="", out=None, limit=12):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if type(a) is not type(b):
        out.append(f"{path}: {str(a)[:80]} != {str(b)[:80]}")
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                out.append(f"{path}/{k}: only in {'second' if k not in a else 'first'}")
            else:
                _diff(a[k], b[k], f"{path}/{k}", out, limit)
            if len(out) >= limit:
                break
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path}: {len(a)} items != {len(b)} items")
        for i, (x, y) in enumerate(zip(a, b)):
            _diff(x, y, f"{path}[{i}]", out, limit)
            if len(out) >= limit:
                break
    elif a != b:
        out.append(f"{path}: {str(a)[:80]} != {str(b)[:80]}")
    return out


def _load(path: str):
    with open(path) as f:
        data = json.load(f)
    for k in VOLATILE:
        data.pop(k, None)
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--genesis", default="primordial", choices=("settled", "primordial"))
    ap.add_argument("--from", dest="source", default="", help="start from a saved universe instead of a genesis")
    ap.add_argument("--cycles", type=int, default=100)
    ap.add_argument("--hashseeds", default="0,1", help="PYTHONHASHSEED for each run")
    ap.add_argument("--dir", default=os.path.join(ROOT, "runs", "lockstep"))
    ap.add_argument("--one", default="", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.one:
        run_one(args, args.one)
        return
    os.makedirs(args.dir, exist_ok=True)
    outs = []
    for hs in args.hashseeds.split(","):
        out = os.path.join(args.dir, f"seed{args.seed}_h{hs}.json")
        cmd = [sys.executable, __file__, "--seed", str(args.seed), "--genesis", args.genesis, "--cycles",
               str(args.cycles), "--one", out] + (["--from", args.source] if args.source else [])
        t = time.perf_counter()
        r = subprocess.run(cmd, env=dict(os.environ, PYTHONHASHSEED=hs), capture_output=True, text=True)
        if r.returncode:
            print(r.stdout, r.stderr)
            sys.exit(r.returncode)
        print(f"hashseed {hs}: {r.stdout.strip().splitlines()[-1]} ({time.perf_counter() - t:.0f}s wall)")
        outs.append(out)
    first = _load(outs[0])
    digest = hashlib.sha256(json.dumps(first, sort_keys=True).encode()).hexdigest()[:16]
    same = True
    for other in outs[1:]:
        d = _diff(first, _load(other))
        if d:
            same = False
            print(f"DIVERGED ({os.path.basename(outs[0])} vs {os.path.basename(other)}):")
            for line in d:
                print("  " + line)
    if same:
        print(f"LOCKSTEP: {len(outs)} runs identical after {args.cycles} cycles (state {digest})")
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
