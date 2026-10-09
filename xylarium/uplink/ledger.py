"""
Xylarium ledger: this universe's upward ledger on its own axis (operator, coordinator and mycelium, 2026-10-09;
78.156). The universe runs on its own clock, its cycle u, never bound to TUniversal's height; at a committed moment
it makes the hypha's ledger act (anastome.ledger_act, ACT_DOMAIN sub-kind 8): u, the CANONICAL commitment to its
whole state (the sparse Merkle root over its entity records, persistence/smt.py), the last FINAL point it
read, and its parent entry (a chain per axis), signed by the domain's reserve. Kept, in order, until the act ships
with 78.154 (then re-signed with parent = the court's returned hash).
"""

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


def entry_hash(act: bytes) -> bytes:
    """An entry's hash - what its successor names as parent (mycelium atlas.rs LedgerEntry::hash): blake3 of exactly
    its signed bytes, the tag, domain, u, commitment, events, point, parent and nonce."""
    import blake3
    from xylarium.uplink import anastome as an
    return blake3.blake3(an.LEDGER_TAG + act[1:33] + act[36:256]).digest()


def read(act: bytes) -> Dict[str, Any]:
    """An entry decoded from its act: u, the commitment, the events digest, the point, its parent, its hash."""
    from xylarium.uplink import anastome as an
    p = an.read_point(act[108:192])
    return {"u": struct.unpack_from("<Q", act, 36)[0], "commitment": act[44:76].hex(), "events": act[76:108].hex(),
            "point": an.point_text(p) if p and any(act[108:192]) else None, "parent": act[192:224].hex(),
            "hash": entry_hash(act).hex()}


def renumber(ledger: str) -> int:
    """Rebuild a ledger whose acts the court would not chain: an older sub-kind (78.154 moved LEDGER from 8 to 12),
    or a parent that is not the hash of the act before it (the court's: blake3 of the signed bytes). Each act is
    re-made in order with its own u, commitment, events, point and nonce, its parent the hash of the one before,
    signed again. Returns the acts rebuilt (0 where the chain already holds)."""
    from xylarium.uplink import anastome as an
    old = acts(ledger)
    expect, sound = bytes(32), True
    for a in old:
        if a[35] != an.LEDGER_SUB or a[192:224] != expect:
            sound = False
            break
        expect = entry_hash(a)
    if not old or sound:
        return 0
    out, parent = [], bytes(32)
    for a in old:
        p = an.read_point(a[108:192]) if any(a[108:192]) else None
        act = an.ledger_act(an.key("ancients"), an.vk(an.key("domain")), struct.unpack_from("<Q", a, 36)[0],
                            a[44:76], a[76:108], p, parent, a[224:256])
        out.append(act)
        parent = entry_hash(act)
    with open(ledger + ".tmp", "wb") as f:
        f.write(b"".join(out))
    os.replace(ledger + ".tmp", ledger)
    return len(out)


def _point_of(act: bytes) -> Optional[Dict[str, Any]]:
    from xylarium.uplink import anastome as an
    return an.read_point(act[108:192]) if any(act[108:192]) else None


def _not_behind(point: Optional[Dict[str, Any]], prev: Optional[bytes]) -> Optional[Dict[str, Any]]:
    """The point an entry cites never stands below its predecessor's (the court: h only rises): where it would -
    none read yet since a restart, or an older one - the predecessor's own final point is cited."""
    before = _point_of(prev) if prev is not None else None
    if before is not None and (point is None or point["h"] < before["h"]):
        return before
    return point


def repair(ledger: str, sealed: int) -> int:
    """Re-make the entries the court has not sealed (index >= sealed) where one cites a point below the one before
    it: each with its own u, commitment, events and nonce, citing the point _not_behind allows, re-chained, signed
    again. Returns the entries re-made."""
    from xylarium.uplink import anastome as an
    old = acts(ledger)
    bad = next((i for i in range(max(1, sealed), len(old))
                if _not_behind(_point_of(old[i]), old[i - 1]) != _point_of(old[i])), None)
    if bad is None:
        return 0
    out = old[:bad]
    for a in old[bad:]:
        prev = out[-1] if out else None
        act = an.ledger_act(an.key("ancients"), an.vk(an.key("domain")), struct.unpack_from("<Q", a, 36)[0],
                            a[44:76], a[76:108], _not_behind(_point_of(a), prev),
                            entry_hash(prev) if prev else bytes(32), a[224:256])
        out.append(act)
    with open(ledger + ".tmp", "wb") as f:
        f.write(b"".join(out))
    os.replace(ledger + ".tmp", ledger)
    return len(old) - bad


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
    parent = entry_hash(prior[-1]) if prior else bytes(32)
    point = _not_behind(point, prior[-1] if prior else None)
    act = an.ledger_act(an.key("ancients"), an.vk(an.key("domain")), u, root, _inputs.digest(ev), point, parent,
                        os.urandom(32))
    assert len(act) == ACT_LEN
    if ev:
        with open(ledger[:-len(".ledger.rec")] + ".inputs.rec", "ab") as f:
            f.write(b"".join(_inputs.event_bytes(e) for e in ev))
    with open(ledger, "ab") as f:
        f.write(act)
    return dict(read(act), inputs=len(ev))


LEDGER_REFUSAL = {1: "not the reserve", 2: "unknown domain", 3: "parent is not the head", 4: "u not above the head",
                  5: "point not final", 6: "unsigned", 7: "point below the head's", 8: "applied crossing invalid",
                  9: "line refused"}


def post(ledger: str, addr: Any, limit: int = 8) -> Dict[str, Any]:
    """Post the entries the court has not sealed yet, in order (up to `limit` a turn): the cursor of how many it
    sealed is kept beside the ledger (binary, u64 LE). A refusal stops the turn and is named; a deferral or silence
    is tried again next turn. The court's returned hash must be ours - the chain is one chain."""
    from xylarium.uplink import anastome as an
    cur_path = ledger[:-len(".ledger.rec")] + ".ledger.posted"
    done = struct.unpack("<Q", open(cur_path, "rb").read(8))[0] if os.path.exists(cur_path) else 0
    repair(ledger, done)                                  # unsealed entries citing a point behind: re-made first
    todo = acts(ledger)[done:done + limit]
    out: Dict[str, Any] = {"sealed": 0, "posted_through": done}
    for a in todo:
        r = an.speak(addr, a, timeout=20)
        if r[:1] == b"\x01" and len(r) >= 33:
            if r[1:33] != entry_hash(a):
                out["refused"] = "the court sealed another hash"
                break
            done += 1
            out["sealed"] += 1
            with open(cur_path + ".tmp", "wb") as f:
                f.write(struct.pack("<Q", done))
            os.replace(cur_path + ".tmp", cur_path)
        elif r[:1] == b"\x00" and len(r) == 2:
            out["refused"] = LEDGER_REFUSAL.get(r[1], f"code {r[1]}")
            break
        else:
            break                                         # deferred or silent: next turn
    out["posted_through"] = done
    return out

