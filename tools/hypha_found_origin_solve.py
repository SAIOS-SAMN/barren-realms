"""Found barren-realms' universe on a hypha (genesis), state its origin (v2), and answer one registry task.

  python3 tools/hypha_found_origin_solve.py [host:port]      (default 127.0.0.1:7500)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xylarium.uplink import anastome as an  # noqa: E402


def main() -> None:
    host, port = (sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:7500").split(":")
    addr = (host, int(port))
    domain = an.key("domain")
    tiers = [an.vk(an.key(t)) for t in an.TIERS]
    out = {"domain": an.vk(domain).hex()}
    out["genesis"] = an.read_sealed(an.speak(addr, an.genesis(domain, tiers)), 0, an.GENESIS_REPLY)
    record = an.big_bang_record(42)
    out["commitment"] = an.commitment(record).hex()
    out["origin"] = an.read_sealed(an.speak(addr, an.origin(domain, record)), 15, an.ORIGIN_REPLY)
    voice = an.key("captains")                      # a mind of the captains' seat speaks the solve
    task = an.read_task(an.speak(addr, an.task_request(voice)))
    if task is None:
        out["task"] = None
    else:
        import hashlib
        out["task"] = {"id_bytes": len(task["id"]), "id_sha256": hashlib.sha256(task["id"]).hexdigest(),
                       "train": len(task["train"]), "test": len(task["test"])}
        from xylarium.uplink import mind
        steps = mind.steps_for(task["train"])        # its mind's steps, or none: no rule, nothing sent
        out["steps"] = steps
        if steps is not None:
            out["solve"] = mind.submit(f"{host}:{port}", os.path.join(an.KEYS, "captains.ed25519"), task, steps)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
