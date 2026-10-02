"""
Keep every age of a universe: run a seed's clock from its foragers to the age asked for, saving each age as it is
first reached (runs/eras/seed<N>/<age>.json), so players step into any of them at once.

  python3 tools/eras.py --seed 7 --to lanes
"""

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main() -> None:
    from xylarium.kernel import ages
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--to", default="lanes", choices=ages.ORDER)
    args = ap.parse_args()
    t0 = time.perf_counter()

    def progress(cycle, firsts):
        if cycle % 2500 == 0:
            print(f"year {cycle // 100}: {len(firsts)} firsts, {cycle / (time.perf_counter() - t0):.1f} cycles/s",
                  flush=True)
    k = ages.begin(args.seed, args.to, progress)
    firsts = k.state["genesis"]["firsts"]
    print(f"seed {args.seed} at year {k.cycle_count // 100}; kept: {ages.cached(args.seed)}")
    for key in ages.ORDER[1:]:
        m = ages.age(key)["until"]
        print(f"  {ages.age(key)['name']:<22} {('year %.1f' % firsts[m]['year']) if m in firsts else 'not yet'}")


if __name__ == "__main__":
    main()
