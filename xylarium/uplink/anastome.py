"""
Xylarium uplink: barren-realms' own client on the hyphae - mycelium's anastome dialogue, spoken from Python.

Barren-realms sends its own traffic from its own code with its own keys (.keys/, never xylarium's or netstratum's):
it FOUNDS its universe as a domain (genesis: its domain key over its tiers' keys), states its ORIGIN (v2: the
geometry its Big Bang fixed and a commitment to that Big Bang's record), and its minds take the court's registry
TASKS and answer them with SOLVES. Ported, byte for byte, from /opt/mycelium-v0.1.0 (wire.rs, dialogue/domain.rs,
universe.rs, percept.rs); every value on the wire is exact (rationals as u64 numerator and denominator).

One act per connection: dial, write one frame, read one reply frame, close (the server answers once and drops).
"""

import hashlib
import json
import os
import socket
import struct
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from nacl.signing import SigningKey

KEYS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".keys")
TIERS = ("ancients", "progenitors", "stewards", "sovereigns", "captains")   # the seats, highest first

LANE_SPATIAL = 0
BODY_BUDGET = 768 * 1024
ACT_TASK, ACT_SOLVE, ACT_DOMAIN = 0x0B, 0x0C, 0x3E
KIND_ORIGIN = 6
GENESIS_TAG = b"mycelium world genesis v1"
ORIGIN_TAG = b"mycelium universe origin v1"
SOLVE_TAG = b"mycelium solve v1"
BIG_BANG_TAG = b"barren-realms big bang v1"
GENESIS_REPLY = {1: "Unsigned", 2: "Unordered", 3: "AlreadyFounded", 4: "TierHeld", 5: "LineRefused"}
ORIGIN_REPLY = {1: "Unsigned", 5: "LineRefused", 8: "NotFounded", 14: "AlreadyOriginated", 17: "GeometryStated",
                18: "NotACore", 20: "Malformed"}
REFUSAL_KIND = {0: "P", 1: "D", 2: "C", 3: "I", 4: "N", 5: "Unclassified"}


# ---------------------------------------------------------------------- keys
def key(name: str) -> SigningKey:
    with open(os.path.join(KEYS, f"{name}.ed25519"), "rb") as f:
        return SigningKey(f.read())


def vk(sk: SigningKey) -> bytes:
    return sk.verify_key.encode()


# ---------------------------------------------------------------------- the wire
def leb128(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def rational(q: Fraction) -> bytes:
    q = Fraction(q)
    if q.numerator <= 0 or q.denominator <= 0:
        raise ValueError("a positive rational is required")
    return struct.pack("<QQ", q.numerator, q.denominator)


def grid(g: List[List[int]]) -> bytes:
    h, w = len(g), len(g[0]) if g else 0
    return struct.pack("<HH", h, w) + bytes(c for row in g for c in row)


def speak(addr: Tuple[str, int], body: bytes, timeout: float = 30.0) -> bytes:
    """One act: a frame out, one frame back. Silence (the connection closed unanswered) is returned as b''."""
    if len(body) > BODY_BUDGET:
        raise ValueError(f"act body {len(body)} bytes is over the wire budget")
    with socket.create_connection(addr, timeout=timeout) as s:
        s.sendall(bytes([LANE_SPATIAL]) + struct.pack("<I", len(body)) + body)
        head = _read(s, 5)
        if head is None:
            return b""
        (n,) = struct.unpack("<I", head[1:5])
        return _read(s, n) or b""


def _read(s: socket.socket, n: int) -> Optional[bytes]:
    buf = bytearray()
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            return None if not buf else bytes(buf)
        buf += chunk
    return bytes(buf)


def deferred(body: bytes) -> bool:
    return len(body) == 43 and body[0] == 0x02 and body[1:9] == b"\0" * 8 and body[-2:] == b"\0\0"


def stamp(b: bytes) -> Dict[str, Any]:
    h, court, k, i = struct.unpack(">Q32sQQ", b[:56])
    return {"h": h, "court": court.hex(), "k": k, "i": i}


# ---------------------------------------------------------------------- genesis and origin
def genesis(domain: SigningKey, tiers: List[bytes]) -> bytes:
    tiers = sorted(tiers)
    body = vk(domain) + leb128(len(tiers)) + b"".join(tiers)
    return bytes([ACT_DOMAIN]) + body + domain.sign(GENESIS_TAG + body).signature


def read_sealed(reply: bytes, ok: int, refusals: Dict[int, str]) -> Dict[str, Any]:
    if not reply:
        return {"ok": False, "why": "silence"}
    if deferred(reply):
        return {"ok": False, "why": "deferred", "lanes": list(struct.unpack("<4Q", reply[9:41]))}
    if reply[0] == ok and len(reply) == 89:                 # [code][stamp 56: h BE, court 32, k BE, i BE][receipt 32]
        return {"ok": True, "stamp": stamp(reply[1:57]), "receipt": reply[57:89].hex()}
    return {"ok": False, "why": refusals.get(reply[0], f"code {reply[0]}"), "raw": reply.hex()}


def big_bang_record(seed: Any) -> Dict[str, Any]:
    """What this universe's Big Bang fixed, exactly: its seed, the digest of the laws it was drawn under, and each
    drawn parameter as an exact rational's string."""
    from xylarium.kernel import creation
    bb = creation.big_bang(seed)
    return {"seed": str(seed), "laws": creation.laws_digest(),
            "big_bang": {k: str(Fraction(str(v))) for k, v in sorted(bb.items())}}


def commitment(record: Dict[str, Any]) -> bytes:
    """The Big Bang commitment: sha256 over the tag and the record's canonical JSON (sorted keys, no spaces)."""
    return hashlib.sha256(BIG_BANG_TAG + json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).digest()


def origin(domain: SigningKey, record: Dict[str, Any], kind: int = 1) -> bytes:
    """Origin v2: a closed universe - Curved, its radius of curvature in megaparsecs, an exact rational - with no
    witnessed parent."""
    r = Fraction(record["big_bang"]["curvature_mpc"])
    geometry = bytes([0]) + rational(r)
    parent = bytes([0])
    signed = vk(domain) + bytes([kind, 2]) + commitment(record) + geometry + parent
    return (bytes([ACT_DOMAIN]) + vk(domain) + b"\x80\x00" + bytes([KIND_ORIGIN]) + bytes([kind, 2])
            + commitment(record) + geometry + parent + domain.sign(ORIGIN_TAG + signed).signature)


# ---------------------------------------------------------------------- tasks and solves
def task_request(voice: SigningKey) -> bytes:
    return bytes([ACT_TASK]) + vk(voice)


def read_task(body: bytes) -> Optional[Dict[str, Any]]:
    if not body:
        return None
    at = 0

    def u(fmt: str) -> Any:
        nonlocal at
        v = struct.unpack_from(fmt, body, at)
        at += struct.calcsize(fmt)
        return v[0]

    def g() -> List[List[int]]:
        nonlocal at
        h, w = u("<H"), u("<H")
        cells = body[at:at + h * w]
        at += h * w
        return [list(cells[r * w:(r + 1) * w]) for r in range(h)]
    n = u("<H")
    tid = body[at:at + n]
    at += n
    train = [(g(), g()) for _ in range(u("<B"))]
    test = [g() for _ in range(u("<B"))]
    return {"id": tid, "train": train, "test": test}


def solve(voice: SigningKey, task_id: bytes, outputs: List[List[List[int]]], rule: Optional[bytes] = None) -> bytes:
    body = (bytes([ACT_SOLVE]) + vk(voice) + struct.pack("<H", len(task_id)) + task_id
            + bytes([len(outputs)]) + b"".join(grid(o) for o in outputs))
    if rule is not None:
        body += b"RULE" + struct.pack("<I", len(rule)) + rule
    return body + b"SIGN" + voice.sign(SOLVE_TAG + body).signature


def read_verdict(body: bytes) -> Dict[str, Any]:
    if not body:
        return {"code": None, "why": "silence"}
    if deferred(body):
        return {"code": None, "why": "deferred"}
    code = body[0]
    out: Dict[str, Any] = {"code": code, "verdict": {2: "bounty", 1: "floor", 0: "nothing"}.get(code, "?"),
                           "mu": list(struct.unpack_from("<4Q", body, 1)) if len(body) >= 33 else None}
    if len(body) > 33:
        kind, at, n, shift = body[33], 34, 0, 0
        while at < len(body):
            b = body[at]
            at += 1
            n |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                break
        out.update(refusal=REFUSAL_KIND.get(kind, kind), reason=body[at:at + n].decode("utf-8", "replace"))
    return out
