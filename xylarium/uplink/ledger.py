"""
Xylarium ledger: this universe's upward ledger on its own axis (operator, coordinator and mycelium, 2026-10-09;
78.156). The universe runs on its own clock, its cycle u, never bound to TUniversal's height; at a committed moment
it makes the hypha's ledger act (anastome.ledger_act, ACT_DOMAIN sub-kind 8): u, the CANONICAL commitment to its
whole state (the sparse Merkle root over its entity records, persistence/smt.py), the last FINAL point it
read, and its parent entry (a chain per axis), signed by the domain's reserve. Kept, in order, until the act ships
with 78.154 (then re-signed with parent = the court's returned hash).
"""

import hashlib
import json
import os
from typing import Any, Dict, Optional


def entry(u: int, root: bytes, ledger: str, point: Optional[Dict[str, Any]],
          inputs: Optional[list] = None) -> Dict[str, Any]:
    """One entry: the state's commitment (the SMT root over its records, persistence/smt.py) at its cycle u and the
    digest of the inputs applied since the entry before (kernel/inputs.py), under the last final point read, chained
    to that entry, signed by the domain's reserve. The inputs themselves are written beside the ledger, for replay."""
    from xylarium.kernel import inputs as _inputs
    ev = list(inputs or [])
    events = _inputs.digest(ev)
    from xylarium.uplink import anastome as an, house
    parent = bytes(32)
    if os.path.exists(ledger):
        with open(ledger) as f:
            lines = f.read().splitlines()
        if lines:
            parent = bytes.fromhex(json.loads(lines[-1])["hash"])
    act = an.ledger_act(an.key("ancients"), an.vk(an.key("domain")), u, root, events, point, parent, os.urandom(32))
    body = {"axis": house.genesis(), "u": u, "commitment": root.hex(), "events": events.hex(), "inputs": len(ev),
            "point": an.point_text(point) if point else None,
            "parent": parent.hex(), "point_wire": an.put_point(point).hex(), "hash": hashlib.sha256(act).hexdigest(),
            "act": act.hex(), "posted": False}
    if ev:
        with open(ledger.replace(".ledger.jsonl", ".inputs.jsonl"), "a") as f:
            f.write(json.dumps({"entry": body["hash"], "u": u, "inputs": ev}) + "\n")
    with open(ledger, "a") as f:
        f.write(json.dumps(body) + "\n")
    return body
