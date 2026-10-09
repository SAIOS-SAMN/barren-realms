"""Run barren-realms' universe continuously as a hypha client: a Big Bang universe advancing on its own clock,
saved to disk, its ancients' houses meeting the court's tasks (court.py) on the hypha named by XYL_HYPHA.

Listens on no port. Saves every SAVE_EVERY cycles and on SIGTERM/SIGINT, then exits; restarts resume from the save.

  XYL_HYPHA=127.0.0.1:7500 python3 tools/universe_daemon.py [--seed 42] [--save runs/universe_cosmic_42]
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
    for name in ("transit", "commerce", "court", "spheres", "board", "ladder", "phylogeny", "life", "reserve_banks", "field", "leak"):
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


RECORDS = ".rec.zst"            # the save: the universe's record stream (persistence/records.py), zstd at rest
LATTICE = 10                    # cycles between committable states: an entry is made at a lattice cycle


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
    base = a.save or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs",
                                  f"universe_cosmic_{a.seed}")
    base = base[:-len(".json")] if base.endswith(".json") else base[:-len(RECORDS)] if base.endswith(RECORDS) else base
    save, legacy = base + RECORDS, base + ".json"             # the record set is the save; JSON only an export
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.update(now=True))
    src = save if os.path.exists(save) else legacy if os.path.exists(legacy) else None
    k = StatePersistence.load_from_file(src) if src else None
    if k is None:
        log(f"genesis: seed {a.seed}, cosmic:{a.pace}")
        k = GameKernel(seed=a.seed, genesis=f"cosmic:{a.pace}")
    else:
        log(f"resumed at cycle {k.cycle_count} from {src}")
    k.activate()
    log(f"hypha: {court.endpoint() or 'none (no court traffic)'}")
    seen = 0
    obs_path, ledger_path = base + ".obs.jsonl", base + ".ledger.rec"
    t0, c0 = time.time(), k.cycle_count
    last = {"relay": 0.0, "save": time.time()}
    if court.endpoint():                                  # the last final point, read to cite in entries
        import threading
        threading.Thread(target=_clock_reader, args=(court.endpoint(),), daemon=True).start()
    commit_due = False
    from concurrent.futures import ProcessPoolExecutor
    from xylarium.persistence import records as R, smt
    from xylarium.uplink import ledger
    pool = ProcessPoolExecutor(max_workers=1)               # the state's tree, kept off the universe's time
    held: dict = {}                                         # the last committed records, by key: what changed is sent
    pending: list = []                                      # (u, point, root future), committed in order
    while not STOP["now"]:
        k.tick_simulation()                               # its own clock: it runs at its own pace
        rec = court.stats(k)["of"] if "court" in k.state else {}
        met = sum(r["met"] for r in rec.values())
        if met > seen:
            seen = met
            log("court: " + json.dumps({h: {x: r[x] for x in ("met", "closed", "refused", "beyond", "mu")}
                                        for h, r in rec.items()}))
        if k.cycle_count % REPORT_EVERY == 0:
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
            commit_due = True                             # saved and committed at the next lattice cycle
        if commit_due and k.cycle_count % LATTICE == 0:
            commit_due, last["save"] = False, now
            from xylarium.kernel import inputs
            from xylarium.uplink import anastome as an
            applied = inputs.take(k)                          # the inputs this entry commits: their effects are in
            recs = R.records_of(StatePersistence.snapshot(k))  # the state; the save IS the record set it commits
            StatePersistence.write_records(recs, save)
            keyed = {smt._record_key(r): r for r in R.committed(recs)}   # the commitment covers no cache
            if not held:
                fut = pool.submit(smt.worker_build, list(keyed.values()))
            else:
                fut = pool.submit(smt.worker_update, [r for key, r in keyed.items() if held.get(key) != r],
                                  [key for key in held if key not in keyed])
            held = keyed
            pending.append((k.cycle_count, an.LAST_POINT["point"], fut, applied))
        while pending and pending[0][2].done():                # each root, as it lands, becomes an entry - in order
            u, point, fut, ev = pending.pop(0)
            if fut.exception() is not None:
                log(f"ledger: entry not made: {fut.exception()!r}")
                held, pending = {}, []                         # the tree is rebuilt whole at the next commit
                break
            e = ledger.entry(u, fut.result(), ledger_path, point, ev)
            log(f"ledger: u {e['u']} commits {e['commitment'][:16]}, {e['inputs']} inputs, under "
                f"{e['point'] or 'no final point'}")
    StatePersistence.save_to_file(k, save)
    log(f"saved at cycle {k.cycle_count}; stopped")


if __name__ == "__main__":
    main()
