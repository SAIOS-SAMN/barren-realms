"""
Xylarium records: the universe's state as the record set its commitment hashes - the save IS the record set
(operator, 2026-10-09; Concordance 9.1, the network form of mycelium 78.154).

  STREAM   records in key order, each (key length u16 LE, key, value) - the very bytes a ledger leaf hashes - so a
           save is committed by hashing its records as they lie, never re-encoded. No JSON, no text numbers.
  KEY      the record's path from the root: the JSON array of the object keys (as text, as JSON writes them) and
           list indices (as integers) that reach it - unique, ordered by its bytes.
  VALUE    put_args([Count(type), payload]), exact:
             0 int    Q (n/1), or BigQ past 64 bits
             1 float  its exact rational (a float is a dyadic fraction: Q or BigQ) - it reads back bit for bit
             2 text   Bytes, utf-8
             3 bool   Flag
             4 null, 5 an empty object, 6 an empty list (no payload): the shape is committed
             7 a float that is not a number (inf, -inf, nan): Bytes of its name
"""

import json
import math
import struct
from typing import Any, Iterator, List, Tuple

Q_, COUNT, FLAG, BIGQ, BYTES = 0, 2, 3, 5, 6          # the wire's ARG tags (seat_wire)
INT, FLOAT, TEXT, BOOL, NULL, EMPTY_OBJ, EMPTY_LIST, ODD_FLOAT = range(8)
_COUNT = [bytes([COUNT]) + struct.pack("<Q", t) for t in range(8)]


def _q(num: int, den: int) -> bytes:
    if -(1 << 63) <= num < (1 << 63) and den < (1 << 64):
        return b"\x00" + struct.pack("<qQ", num, den)
    n = num.to_bytes((num.bit_length() + 8) // 8, "little", signed=True)
    d = den.to_bytes((den.bit_length() + 7) // 8, "little")
    return bytes([BIGQ]) + struct.pack("<H", len(n)) + n + struct.pack("<H", len(d)) + d


def _bytes(b: bytes) -> bytes:
    if len(b) > 0xFFFF:
        raise ValueError(f"a text value of {len(b)} bytes is past the wire's u16")
    return bytes([BYTES]) + struct.pack("<H", len(b)) + b


def value(v: Any) -> bytes:
    """A value as put_args([Count(type), payload])."""
    if v is True or v is False:
        return b"\x02" + _COUNT[BOOL] + bytes([FLAG, int(v)])
    if isinstance(v, int):
        return b"\x02" + _COUNT[INT] + _q(v, 1)
    if isinstance(v, float):
        if math.isfinite(v):
            return b"\x02" + _COUNT[FLOAT] + _q(*v.as_integer_ratio())
        return b"\x02" + _COUNT[ODD_FLOAT] + _bytes(repr(v).encode())
    if isinstance(v, str):
        return b"\x02" + _COUNT[TEXT] + _bytes(v.encode())
    if v is None:
        return b"\x01" + _COUNT[NULL]
    if isinstance(v, dict):
        return b"\x01" + _COUNT[EMPTY_OBJ]
    if isinstance(v, (list, tuple)):
        return b"\x01" + _COUNT[EMPTY_LIST]
    from fractions import Fraction
    if isinstance(v, Fraction):
        return b"\x02" + _COUNT[FLOAT] + _q(v.numerator, v.denominator)
    raise TypeError(f"no record form for {type(v).__name__}")


def _jkey(k: Any) -> str:
    """An object key as JSON writes it."""
    if isinstance(k, str):
        return k
    if k is True or k is False:
        return "true" if k else "false"
    if k is None:
        return "null"
    if isinstance(k, float):
        return json.dumps(k)
    return str(k)


def records(root: Any) -> Iterator[Tuple[bytes, bytes]]:
    """Every value the state holds, as (key, value)."""
    stack: List[Tuple[list, Any]] = [([], root)]
    dumps = json.JSONEncoder(separators=(",", ":"), ensure_ascii=False).encode
    while stack:
        path, v = stack.pop()
        if isinstance(v, dict) and v:
            stack.extend((path + [_jkey(k)], x) for k, x in v.items())
        elif isinstance(v, (list, tuple)) and v:
            stack.extend((path + [i], x) for i, x in enumerate(v))
        else:
            yield dumps(path).encode(), value(v)


def encode(root: Any) -> bytes:
    """The record stream, in key order."""
    out = bytearray()
    for k, v in sorted(records(root)):
        if len(k) > 0xFFFF:
            raise ValueError(f"a record key of {len(k)} bytes is past u16")
        out += struct.pack("<H", len(k)) + k + v
    return bytes(out)


def split(stream: bytes) -> Iterator[Tuple[int, int, bytes]]:
    """Each record's span in the stream (start, end) and its key - the leaf bytes are stream[start:end]."""
    at, n = 0, len(stream)
    while at < n:
        start = at
        (kl,) = struct.unpack_from("<H", stream, at)
        key = stream[at + 2:at + 2 + kl]
        at += 2 + kl
        count = stream[at]
        at += 1
        for _ in range(count):
            tag = stream[at]
            at += 1
            if tag == Q_:
                at += 16
            elif tag == COUNT:
                at += 8
            elif tag == FLAG:
                at += 1
            elif tag == BIGQ:
                (ln,) = struct.unpack_from("<H", stream, at)
                at += 2 + ln
                (ln,) = struct.unpack_from("<H", stream, at)
                at += 2 + ln
            elif tag == BYTES:
                (ln,) = struct.unpack_from("<H", stream, at)
                at += 2 + ln
            else:
                raise ValueError(f"no ARG tag {tag} in a record")
        yield start, at, key


def _read_value(stream: bytes, at: int) -> Any:
    count = stream[at]
    at += 1
    (t,) = struct.unpack_from("<Q", stream, at + 1)
    at += 9
    if count == 1:
        return {NULL: None, EMPTY_OBJ: {}, EMPTY_LIST: []}[t]
    tag = stream[at]
    at += 1
    if tag == FLAG:
        return bool(stream[at])
    if tag == BYTES:
        (ln,) = struct.unpack_from("<H", stream, at)
        s = stream[at + 2:at + 2 + ln].decode()
        return float(s) if t == ODD_FLOAT else s
    if tag == Q_:
        num, den = struct.unpack_from("<qQ", stream, at)
    else:
        (ln,) = struct.unpack_from("<H", stream, at)
        num = int.from_bytes(stream[at + 2:at + 2 + ln], "little", signed=True)
        at += 2 + ln
        (ld,) = struct.unpack_from("<H", stream, at)
        den = int.from_bytes(stream[at + 2:at + 2 + ld], "little")
    if t == INT:
        return num
    return num / den if den != 1 else float(num)          # a dyadic: exact back to its float


def decode(stream: bytes) -> Any:
    """The state from its record stream."""
    root: Any = None
    for start, end, key in split(stream):
        path = json.loads(key)
        v = _read_value(stream, start + 2 + len(key))
        if not path:
            return v
        if root is None:
            root = [] if isinstance(path[0], int) else {}
        node = root
        for seg, nxt in zip(path, path[1:]):
            child_kind = list if isinstance(nxt, int) else dict
            if isinstance(node, list):
                while len(node) <= seg:
                    node.append(None)
                if node[seg] is None:
                    node[seg] = child_kind()
                node = node[seg]
            else:
                if seg not in node:
                    node[seg] = child_kind()
                node = node[seg]
        last = path[-1]
        if isinstance(node, list):
            while len(node) <= last:
                node.append(None)
            node[last] = v
        else:
            node[last] = v
    return root
