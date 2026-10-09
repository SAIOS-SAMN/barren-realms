"""
Xylarium inputs: the universe's INPUTS - what reached it from outside its own laws (a mind taking a seat, a seated
mind's call, a player's order) - stored as events at their coordinate and re-applied in order from the checkpoint
before (Concordance 1.13). Everything else is derived or path-dependent; inputs are the only thing a replay cannot
compute.

  EVENT    (the final point it was made under, u the cycle it landed at, its coordinate path key, its values)
  LEAF     derive_key("mycelium ledger event v1") over point (84) || u (u64 LE) || key length (u16 LE) || key ||
           put_args(values)
  DIGEST   a positional Merkle root over the events since the parent entry, in the order they were applied: node =
           derive_key("mycelium ledger node v1") over left || right, an odd node carried up; no events, 32 zeros.
           Each ledger entry carries it after the state's commitment (mycelium 78.154).

The events since the last entry are kept in the state (state "inputs"), so a save holds them; the entry that
commits them clears them, and they are appended beside the ledger as binary records (runs/<universe>.inputs.rec,
event_bytes in applied order; each entry says how many are its own) for replay.
"""

import json
import struct
from typing import Any, Dict, List

import blake3

EVENT, NODE = "mycelium ledger event v1", "mycelium ledger node v1"


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "inputs")


def record(kernel: Any, path: List[Any], values: List[Any]) -> None:
    """An input reached the universe: kept at its coordinate - the final point read, the cycle it landed at."""
    from xylarium.uplink import anastome as an
    if not hasattr(kernel, "state"):
        return
    p = an.LAST_POINT["point"]
    stats(kernel)["since"].append({"point": an.put_point(p).hex(), "u": int(kernel.cycle_count),
                                   "key": json.dumps(path, separators=(",", ":"), ensure_ascii=False),
                                   "values": values})


def event_bytes(e: Dict[str, Any]) -> bytes:
    """An event as it is hashed and as it is stored: point (84) || u (u64 LE) || key length (u16 LE) || key ||
    put_args(values) - the replay reads the very bytes the digest committed."""
    from xylarium.persistence import records
    key = e["key"].encode()
    vals = [x for v in e["values"] for x in records._scalar(v)]
    return (bytes.fromhex(e["point"]) + struct.pack("<Q", e["u"]) + struct.pack("<H", len(key)) + key
            + bytes([len(vals)]) + b"".join(vals))


def _leaf(e: Dict[str, Any]) -> bytes:
    h = blake3.blake3(derive_key_context=EVENT)
    h.update(event_bytes(e))
    return h.digest()


def digest(events: List[Dict[str, Any]]) -> bytes:
    """The positional Merkle root over events, in applied order; 32 zeros for none."""
    level = [_leaf(e) for e in events]
    if not level:
        return bytes(32)
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level) - 1, 2):
            h = blake3.blake3(derive_key_context=NODE)
            h.update(level[i] + level[i + 1])
            nxt.append(h.digest())
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    return level[0]


def take(kernel: Any) -> List[Dict[str, Any]]:
    """The events since the last entry, handed to the entry that commits them (and cleared)."""
    st = stats(kernel)
    out, st["since"] = st["since"], []
    return out


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="inputs", state=lambda: {"since": []}))
