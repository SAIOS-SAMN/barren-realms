"""
Xylarium commitment: a universe's state committed canonically - by its exact decoded values, never by the bytes of a
file (Concordance 9.1; the shared form, coordinator 2026-10-09).

  RECORDS  barren-realms names its record set: EVERY value its save holds, each keyed by its path from the root
           (the JSON array of the keys and indices that reach it). A number is its exact rational (Q, or BigQ where it
           does not fit), read from the save's own text, never through a float; a boolean is a Flag; text is Bytes
           b"s" + utf-8; null is Bytes b"n"; an empty object or list is Bytes b"{}" / b"[]", so the shape is committed.
  LEAF     blake3 under the domain-separation key: 0x00 || key length (u32 LE) || key || the value in ARG encoding.
  ROOT     the leaves sorted by key, hashed pairwise (0x01 || left || right); an odd node rises unpaired.

Two kernels holding the same universe commit the same root however each writes its file.
"""

import json
import struct
from fractions import Fraction
from typing import Any, Iterator, List, Tuple

import blake3

CONTEXT = "barren-realms state commitment v1"


def _h(data: bytes) -> bytes:
    h = blake3.blake3(derive_key_context=CONTEXT)
    h.update(data)
    return h.digest()


def _value(v: Any) -> bytes:
    from xylarium.uplink import seat_wire as w
    if isinstance(v, bool):
        return w.args([(w.FLAG, v)])
    if isinstance(v, (int, Fraction)):
        return w.args([(w.Q_, Fraction(v))])
    if isinstance(v, str):
        return w.args([(w.BYTES, b"s" + v.encode())])
    if v is None:
        return w.args([(w.BYTES, b"n")])
    if isinstance(v, dict):
        return w.args([(w.BYTES, b"{}")])
    return w.args([(w.BYTES, b"[]")])


def records(root: Any) -> Iterator[Tuple[bytes, bytes]]:
    """Every value the state holds, as (key, exact value in ARG encoding)."""
    stack: List[Tuple[list, Any]] = [([], root)]
    while stack:
        path, v = stack.pop()
        if isinstance(v, dict) and v:
            stack.extend((path + [k], x) for k, x in v.items())
        elif isinstance(v, list) and v:
            stack.extend((path + [i], x) for i, x in enumerate(v))
        else:
            yield json.dumps(path, separators=(",", ":")).encode(), _value(v)


def root_of(state: Any) -> bytes:
    """The canonical commitment: the Merkle root over the state's records, sorted by key."""
    level = [_h(b"\x00" + struct.pack("<I", len(k)) + k + v) for k, v in sorted(records(state))]
    if not level:
        return _h(b"\x00")
    while len(level) > 1:
        nxt = [_h(b"\x01" + level[i] + level[i + 1]) for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    return level[0]


def of_save(path: str) -> bytes:
    """A save's commitment, read from its own text: numbers exactly as written (never through a float)."""
    with open(path) as f:
        return root_of(json.load(f, parse_float=Fraction, parse_int=int))
