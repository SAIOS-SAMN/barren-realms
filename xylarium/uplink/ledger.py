"""
Xylarium ledger: this universe's upward ledger on its own axis (operator, coordinator and mycelium, 2026-10-09;
78.156). The universe runs on its own clock, its cycle u, never bound to TUniversal's height; at a committed moment
it makes the hypha's ledger act (anastome.ledger_act, ACT_DOMAIN sub-kind 8): u, the CANONICAL commitment to its
whole state (commitment.of_save: a Merkle root over its exact values, never a file's bytes), the last FINAL point it
read, and its parent entry (a chain per axis), signed by the domain's reserve. Kept, in order, until the act ships
with 78.154 (then re-signed with parent = the court's returned hash).
"""

import hashlib
import json
import os
from typing import Any, Dict, Optional


def entry(u: int, snapshot: str, ledger: str, point: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """One entry, from a snapshot of the save (removed once committed): a commitment takes about a minute, so the
    daemon runs this in its own process and the universe does not wait for it."""
    from xylarium.uplink import anastome as an, commitment, house
    parent = bytes(32)
    if os.path.exists(ledger):
        with open(ledger) as f:
            lines = f.read().splitlines()
        if lines:
            parent = bytes.fromhex(json.loads(lines[-1])["hash"])
    root = commitment.of_save(snapshot)
    act = an.ledger_act(an.key("ancients"), an.vk(an.key("domain")), u, root, point, parent, os.urandom(32))
    body = {"axis": house.genesis(), "u": u, "commitment": root.hex(), "point": an.point_text(point) if point else None,
            "parent": parent.hex(), "point_wire": an.put_point(point).hex(), "hash": hashlib.sha256(act).hexdigest(),
            "act": act.hex(), "posted": False}
    with open(ledger, "a") as f:
        f.write(json.dumps(body) + "\n")
    os.remove(snapshot)
    return body
