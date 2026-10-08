"""Run barren-realms' universe continuously as a hypha client: a Big Bang universe advancing on its own clock,
saved to disk, its ancients' houses meeting the court's tasks (court.py) on the hypha named by XYL_HYPHA.

Listens on no port. Saves every SAVE_EVERY cycles and on SIGTERM/SIGINT, then exits; restarts resume from the save.

  XYL_HYPHA=127.0.0.1:7500 python3 tools/universe_daemon.py [--seed 42] [--save runs/universe_cosmic_42.json]
"""

import argparse
import json
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xylarium.kernel import court, subsystem  # noqa: E402
from xylarium.kernel.engine import GameKernel  # noqa: E402
from xylarium.persistence.store import StatePersistence  # noqa: E402

SAVE_EVERY = 2000
REPORT_EVERY = 500
STOP = {"now": False}


def log(msg: str) -> None:
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--pace", default="neighbourly")
    ap.add_argument("--save", default=None)
    a = ap.parse_args()
    save = a.save or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs",
                                  f"universe_cosmic_{a.seed}.json")
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.update(now=True))
    k = StatePersistence.load_from_file(save) if os.path.exists(save) else None
    if k is None:
        log(f"genesis: seed {a.seed}, cosmic:{a.pace}")
        k = GameKernel(seed=a.seed, genesis=f"cosmic:{a.pace}")
    else:
        log(f"resumed at cycle {k.cycle_count} from {save}")
    k.activate()
    log(f"hypha: {court.endpoint() or 'none (no court traffic)'}")
    seen = 0
    while not STOP["now"]:
        k.tick_simulation()
        rec = court.stats(k)["of"] if "court" in k.state else {}
        met = sum(r["met"] for r in rec.values())
        if met > seen:
            seen = met
            log("court: " + json.dumps({h: {x: r[x] for x in ("met", "closed", "refused", "beyond", "mu")}
                                        for h, r in rec.items()}))
        if k.cycle_count % REPORT_EVERY == 0:
            log(f"cycle {k.cycle_count}: houses {len(court.houses(k))}, " + json.dumps(court.summary(k)))
        if k.cycle_count % SAVE_EVERY == 0:
            StatePersistence.save_to_file(k, save)
    StatePersistence.save_to_file(k, save)
    log(f"saved at cycle {k.cycle_count}; stopped")


if __name__ == "__main__":
    main()
