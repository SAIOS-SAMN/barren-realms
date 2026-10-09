"""
Xylarium records: the universe's state as the record set its commitment hashes - the save IS the record set
(operator, 2026-10-09; Concordance 1.13 and 9.1; one record per ENTITY, the coordinator's ruling).

  ENTITY   every object and every list in the state is one record, keyed by its path from the root: the JSON array
           of the object keys (text, as JSON writes them) and list indices (integers) that reach it. A nested object
           is its own entity at its own path, never inlined.
  VALUES   put_args: [Count(kind: 0 object, 1 list), Count(parts)] then each child, in its own order (an object's
           order is kept: laws iterate it): an object's child is Bytes(name) first; then Count(type) and its
           payload -
             0 int    Q (n/1), or BigQ past 64 bits
             1 float  its exact rational (a dyadic: Q or BigQ) - it reads back bit for bit
             2 text   Bytes, utf-8
             3 bool   Flag
             4 null, 5 an empty object, 6 an empty list (no payload)
             7 a float that is not a number (inf, -inf, nan): Bytes of its name
             8 a nested entity (no payload): its own record, at its own path
           A record holds at most 255 arguments; an entity with more children continues in PARTS, each its own
           record at its path with a negative last index (-1, -2, ...).
  STREAM   the records in key order, each (key length u16 LE, key, values) - the very bytes a ledger leaf hashes.
"""

import json
import math
import struct
from typing import Any, Dict, Iterator, List, Tuple

Q_, COUNT, FLAG, BIGQ, BYTES = 0, 2, 3, 5, 6          # the wire's ARG tags (seat_wire)
INT, FLOAT, TEXT, BOOL, NULL, EMPTY_OBJ, EMPTY_LIST, ODD_FLOAT, CHILD = range(9)
OBJ, LIST = 0, 1
MAX_ARGS = 255
_C = [bytes([COUNT]) + struct.pack("<Q", t) for t in range(9)]


def _count(n: int) -> bytes:
    return bytes([COUNT]) + struct.pack("<Q", n)


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


def _nested(v: Any) -> bool:
    return isinstance(v, (dict, list, tuple)) and len(v) > 0


def _scalar(v: Any) -> List[bytes]:
    """A child's [Count(type), payload?] arguments."""
    if v is True or v is False:
        return [_C[BOOL], bytes([FLAG, int(v)])]
    if isinstance(v, int):
        return [_C[INT], _q(v, 1)]
    if isinstance(v, float):
        if math.isfinite(v):
            return [_C[FLOAT], _q(*v.as_integer_ratio())]
        return [_C[ODD_FLOAT], _bytes(repr(v).encode())]
    if isinstance(v, str):
        return [_C[TEXT], _bytes(v.encode())]
    if v is None:
        return [_C[NULL]]
    if isinstance(v, dict):
        return [_C[EMPTY_OBJ]]
    if isinstance(v, (list, tuple)):
        return [_C[EMPTY_LIST]]
    from fractions import Fraction
    if isinstance(v, Fraction):
        return [_C[FLOAT], _q(v.numerator, v.denominator)]
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


_dumps = json.JSONEncoder(separators=(",", ":"), ensure_ascii=False).encode


def entities(root: Any) -> Iterator[Tuple[bytes, bytes]]:
    """Every entity the state holds, as (key, values) - an entity past 255 arguments in its parts."""
    stack: List[Tuple[list, Any]] = [([], root)]
    while stack:
        path, v = stack.pop()
        obj = isinstance(v, dict)
        items = [(_jkey(k), x) for k, x in v.items()] if obj else list(enumerate(v))
        children: List[List[bytes]] = []
        for name, x in items:
            head = [_bytes(name.encode())] if obj else []
            if _nested(x):
                stack.append((path + [name], x))
                children.append(head + [_C[CHILD]])
            else:
                children.append(head + _scalar(x))
        parts: List[List[bytes]] = [[]]
        for c in children:
            if len(parts[-1]) + len(c) > MAX_ARGS - 2:
                parts.append([])
            parts[-1].extend(c)
        for i, args in enumerate(parts):
            key = _dumps(path if i == 0 else path + [-i]).encode()
            vals = [_count(OBJ if obj else LIST), _count(len(parts))] + args
            yield key, bytes([len(vals)]) + b"".join(vals)


def records_of(root: Any) -> List[bytes]:
    """The record bytes (key length, key, values), in key order: the leaves."""
    out = []
    for k, v in sorted(entities(root)):
        if len(k) > 0xFFFF:
            raise ValueError(f"a record key of {len(k)} bytes is past u16")
        out.append(struct.pack("<H", len(k)) + k + v)
    return out


def encode(root: Any) -> bytes:
    """The record stream, in key order."""
    if not _nested(root):
        raise ValueError("the state's root is an object or a list")
    return b"".join(records_of(root))


def split(stream: bytes) -> Iterator[Tuple[int, int, bytes]]:
    """Each record's span in the stream (start, end) and its key: the leaf bytes are stream[start:end]."""
    at, n = 0, len(stream)
    while at < n:
        start = at
        (kl,) = struct.unpack_from("<H", stream, at)
        key = stream[at + 2:at + 2 + kl]
        at += 2 + kl
        count = stream[at]
        at += 1
        for _ in range(count):
            at = _skip(stream, at)
        yield start, at, key


def _skip(b: bytes, at: int) -> int:
    tag = b[at]
    at += 1
    if tag == Q_:
        return at + 16
    if tag == COUNT:
        return at + 8
    if tag == FLAG:
        return at + 1
    if tag == BYTES:
        return at + 2 + struct.unpack_from("<H", b, at)[0]
    if tag == BIGQ:
        at += 2 + struct.unpack_from("<H", b, at)[0]
        return at + 2 + struct.unpack_from("<H", b, at)[0]
    raise ValueError(f"no ARG tag {tag} in a record")


def _args(b: bytes, at: int) -> List[Any]:
    """A record's arguments as Python values (Count -> int, Q/BigQ -> (num, den), Flag -> bool, Bytes -> bytes)."""
    n = b[at]
    at += 1
    out: List[Any] = []
    for _ in range(n):
        tag = b[at]
        if tag == COUNT:
            out.append(struct.unpack_from("<Q", b, at + 1)[0])
        elif tag == Q_:
            out.append(struct.unpack_from("<qQ", b, at + 1))
        elif tag == FLAG:
            out.append(bool(b[at + 1]))
        elif tag == BYTES:
            ln = struct.unpack_from("<H", b, at + 1)[0]
            out.append(b[at + 3:at + 3 + ln])
        else:
            ln = struct.unpack_from("<H", b, at + 1)[0]
            num = int.from_bytes(b[at + 3:at + 3 + ln], "little", signed=True)
            ld = struct.unpack_from("<H", b, at + 3 + ln)[0]
            den = int.from_bytes(b[at + 5 + ln:at + 5 + ln + ld], "little")
            out.append((num, den))
        at = _skip(b, at)
    return out


def decode(stream: bytes) -> Any:
    """The state from its record stream: every entity rebuilt with its children in their own order."""
    parts: Dict[str, Dict[int, List[Any]]] = {}
    kinds: Dict[str, int] = {}
    for start, end, key in split(stream):
        path = json.loads(key)
        part = 0
        if path and isinstance(path[-1], int) and path[-1] < 0:
            part, path = -path[-1], path[:-1]
        k = _dumps(path)
        a = _args(stream, start + 2 + len(key))
        kinds[k] = a[0]
        parts.setdefault(k, {})[part] = a[2:]
    built: Dict[str, Any] = {k: ({} if kind == OBJ else []) for k, kind in kinds.items()}
    for k, ps in parts.items():
        node, path, obj = built[k], json.loads(k), kinds[k] == OBJ
        args = [x for i in sorted(ps) for x in ps[i]]
        i, index = 0, 0
        while i < len(args):
            name = args[i].decode() if obj else index
            if obj:
                i += 1
            t = args[i]
            i += 1
            if t in (NULL, EMPTY_OBJ, EMPTY_LIST, CHILD):
                v = None if t == NULL else {} if t == EMPTY_OBJ else [] if t == EMPTY_LIST else \
                    built[_dumps(path + [name])]
            else:
                p = args[i]
                i += 1
                if t == BOOL:
                    v = p
                elif t == TEXT:
                    v = p.decode()
                elif t == ODD_FLOAT:
                    v = float(p.decode())
                elif t == INT:
                    v = p[0]
                else:
                    v = p[0] / p[1] if p[1] != 1 else float(p[0])
            if obj:
                node[name] = v
            else:
                node.append(v)
            index += 1
    return built["[]"]
