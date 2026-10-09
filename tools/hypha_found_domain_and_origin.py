"""Found barren-realms' universe on a hypha (genesis) state its origin (v2), and designate its ancients' tier as its reserve. Court tasks are met in the
world by the ancients' minds (xylarium/kernel/court.py), never by this script.

  python3 tools/hypha_found_domain_and_origin.py [host:port]      (default 127.0.0.1:7500)
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
    r = an.speak(addr, an.reserve(domain, an.vk(an.key("ancients")), os.urandom(32)))
    out["reserve"] = "reserved" if r[:1] == b"\x06" else (r.hex() if r else "silence")   # the ancients' tier
    print(json.dumps(out, indent=2))
    from xylarium.uplink import house                     # the relay reads a new genesis as a recut: it lists anew
    if isinstance(out["genesis"], dict) and out["genesis"].get("receipt"):
        with open(house.GENESIS, "w") as f:
            json.dump({"addr": f"{host}:{port}", "receipt": out["genesis"]["receipt"]}, f)


if __name__ == "__main__":
    main()
