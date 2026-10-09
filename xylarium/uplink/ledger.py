"""
Xylarium ledger: this universe's upward ledger on its own axis (operator, coordinator and mycelium, 2026-10-09;
78.156). The universe runs on its own clock, its cycle u, never bound to TUniversal's height; at a committed moment
it makes the hypha's ledger act (anastome.ledger_act, ACT_DOMAIN sub-kind 8): u, the CANONICAL commitment to its
whole state (the sparse Merkle root over its entity records, persistence/smt.py), the last FINAL point it
read, and its parent entry (a chain per axis), signed by the domain's reserve. Kept, in order, until the act ships
with 78.154 (then re-signed with parent = the court's returned hash).
"""

import hashlib
import os
import struct
from typing import Any, Dict, List, Optional


ACT_LEN = 320                   # [0x3E][domain 32][0x80 0 8][u 8][commitment 32][events 32][point 84][parent 32][nonce 32][sig 64]


def acts(ledger: str) -> List[bytes]:
    """The ledger as it lies: its acts, in order (each its fixed 320 bytes)."""
    if not os.path.exists(ledger):
        return []
    with open(ledger, "rb") as f:
        b = f.read()
    return [b[i:i + ACT_LEN] for i in range(0, len(b) - len(b) % ACT_LEN, ACT_LEN)]


def read(act: bytes) -> Dict[str, Any]:
    """An entry decoded from its act: u, the commitment, the events digest, the point, its parent, its hash."""
    from xylarium.uplink import anastome as an
    p = an.read_point(act[108:192])
    return {"u": struct.unpack_from("<Q", act, 36)[0], "commitment": act[44:76].hex(), "events": act[76:108].hex(),
            "point": an.point_text(p) if p and any(act[108:192]) else None, "parent": act[192:224].hex(),
            "hash": hashlib.sha256(act).hexdigest()}


def renumber(ledger: str) -> int:
    """Rebuild a ledger whose acts carry an older sub-kind (78.154 moved LEDGER from 8 to 12): each act re-made in
    order with its own u, commitment, events, point and nonce, its parent the new hash of the one before, signed
    again. Returns the acts rebuilt."""
    from xylarium.uplink import anastome as an
    old = acts(ledger)
    if not old or all(a[35] == an.LEDGER_SUB for a in old):
        return 0
    out, parent = [], bytes(32)
    for a in old:
        p = an.read_point(a[108:192]) if any(a[108:192]) else None
        act = an.ledger_act(an.key("ancients"), an.vk(an.key("domain")), struct.unpack_from("<Q", a, 36)[0],
                            a[44:76], a[76:108], p, parent, a[224:256])
        out.append(act)
        parent = hashlib.sha256(act).digest()
    with open(ledger + ".tmp", "wb") as f:
        f.write(b"".join(out))
    os.replace(ledger + ".tmp", ledger)
    return len(out)


def entry(u: int, root: bytes, ledger: str, point: Optional[Dict[str, Any]],
          inputs: Optional[list] = None) -> Dict[str, Any]:
    """One entry: the state's commitment (the SMT root over its records, persistence/smt.py) at its cycle u and the
    digest of the inputs applied since the entry before (kernel/inputs.py), under the last final point read, chained
    to that entry, signed by the domain's reserve - appended to the ledger as the hypha's act, binary; the inputs
    beside it as the bytes their digest hashed."""
    from xylarium.kernel import inputs as _inputs
    from xylarium.uplink import anastome as an
    ev = list(inputs or [])
    prior = acts(ledger)
    parent = hashlib.sha256(prior[-1]).digest() if prior else bytes(32)
    act = an.ledger_act(an.key("ancients"), an.vk(an.key("domain")), u, root, _inputs.digest(ev), point, parent,
                        os.urandom(32))
    assert len(act) == ACT_LEN
    if ev:
        with open(ledger[:-len(".ledger.rec")] + ".inputs.rec", "ab") as f:
            f.write(b"".join(_inputs.event_bytes(e) for e in ev))
    with open(ledger, "ab") as f:
        f.write(act)
    return dict(read(act), inputs=len(ev))
