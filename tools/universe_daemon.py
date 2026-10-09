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
from xylarium.uplink import house  # noqa: E402

SAVE_EVERY_S = 300           # saved on the wall clock: the engine's pace varies with how many worlds it ticks
RELAY_EVERY_S = 15           # the house relay's beat (seat mail), on the wall clock
REPORT_EVERY = 500
STOP = {"now": False}


def log(msg: str) -> None:
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def observe(k, path: str, t0: float, c0: int) -> None:
    """The game's vital signs (tools/live.py's line, with the roads, trade and the court) appended to the
    observations log; a short line to the journal: minds, peoples, crystals, species, trade, roads, the court."""
    from tools.live import observe as vitals
    wall = time.time() - t0
    o = vitals(k, wall, (k.cycle_count - c0) / max(1e-9, wall))
    sums = subsystem.summaries(k)
    for name in ("transit", "commerce", "court", "spheres", "board", "ladder", "phylogeny", "life", "reserve_banks", "field"):
        if name in sums:
            o[name] = sums[name]
    from xylarium.kernel import cosmos
    o["deep_gyr"] = cosmos.deep_gyr(k) if cosmos.is_cosmic(k) else None
    with open(path, "a") as f:
        f.write(json.dumps(o, default=str) + "\n")
    intel = o.get("intellect") or {}
    log(f"c{k.cycle_count} gyr {o['deep_gyr']:.4f} people {o['people']:,} worlds {o['worlds']} "
        f"minds {(o.get('cosmos') or {}).get('minds_arisen', '?')}/{(o.get('cosmos') or {}).get('minds_expected_by_now', '?')} peoples {(o.get('cosmos') or {}).get('peoples', 0)} "
        f"fluid {intel.get('mean_fluid', {})} genome {json.dumps(o.get('genome', {}), default=str)[:120]} "
        f"trade {json.dumps(o.get('commerce', {}), default=str)[:100]} roads {json.dumps(o.get('transit', {}), default=str)[:100]} "
        f"court {json.dumps(o.get('court', {}))}")


LATTICE = 10                    # cycles between committed states: a bound universe advances in whole lattice spans
TUNIVERSAL_ENV = "XYL_TUNIVERSAL"   # "1": the universe's clock is bound to TUniversal (Concordance 1.11)


class Binding:
    """The universe's clock bound to TUniversal (as xyl-kernel tuniversal.rs): a cycle IS a final point's height,
    counted from the height it was bound at. A height below it is a court started afresh: bound again where it
    stands."""

    def __init__(self, h0: int, cycle0: int):
        self.h0, self.cycle0 = h0, cycle0

    def cycle(self, h: int) -> int:
        return self.cycle0 + max(0, h - self.h0)

    def holds(self, h: int) -> bool:
        return h >= self.h0


def next_lattice(cycle: int) -> int:
    return (cycle // LATTICE + 1) * LATTICE


def _clock_reader(addr: str, period_s: float = 1.0) -> None:
    """Read the court's clock once a period; each reply carries the final point (anastome.LAST_POINT). The game
    never waits on it: a tick takes the last point heard."""
    from xylarium.uplink import anastome as an
    host, port = addr.rsplit(":", 1)
    while not STOP["now"]:
        try:
            an.clock((host, int(port)))
        except Exception:
            pass
        time.sleep(period_s)


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
    obs_path = save.replace(".json", ".obs.jsonl")
    t0, c0 = time.time(), k.cycle_count
    last = {"relay": 0.0, "save": time.time()}
    bound = None
    tuniversal = bool(court.endpoint()) and os.environ.get(TUNIVERSAL_ENV) == "1"
    if tuniversal:
        import threading
        threading.Thread(target=_clock_reader, args=(court.endpoint(),), daemon=True).start()
        log("clock: bound to TUniversal (the universe advances only as its final point does)")
    while not STOP["now"]:
        advance = True
        if tuniversal:
            from xylarium.uplink import anastome as an
            p = an.LAST_POINT["point"]
            if p is not None and (bound is None or not bound.holds(p["h"])):
                bound = Binding(p["h"], k.cycle_count)
                log(f"clock: bound to TUniversal: cycle {bound.cycle0} at {an.point_text(p)}")
            # no final point, or caught up to it: time does not advance (the relay and the saves still run)
            advance = p is not None and next_lattice(k.cycle_count) <= bound.cycle(p["h"])
        if not advance:
            time.sleep(0.25)
        else:
            k.tick_simulation()
        rec = court.stats(k)["of"] if "court" in k.state else {}
        met = sum(r["met"] for r in rec.values())
        if advance and met > seen:
            seen = met
            log("court: " + json.dumps({h: {x: r[x] for x in ("met", "closed", "refused", "beyond", "mu")}
                                        for h, r in rec.items()}))
        if advance and k.cycle_count % REPORT_EVERY == 0:
            observe(k, obs_path, t0, c0)
        now = time.time()
        if court.endpoint() and now - last["relay"] >= RELAY_EVERY_S:   # the house relay (seat wire)
            last["relay"] = now
            try:
                did = house.on_hypha(k, court.endpoint())
                if did and any(v for key, v in did.items() if key not in ("held", "ms")):
                    log("seats: " + json.dumps(did))
            except OSError as e:
                log(f"seats: the hypha did not answer: {e}")
            except Exception as e:                        # a relay fault never stops the universe
                log(f"seats: relay fault {type(e).__name__}: {e}")
        if now - last["save"] >= SAVE_EVERY_S:
            last["save"] = now
            StatePersistence.save_to_file(k, save)
    StatePersistence.save_to_file(k, save)
    log(f"saved at cycle {k.cycle_count}; stopped")


if __name__ == "__main__":
    main()
