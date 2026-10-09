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
        body, point = unframe(head[0], _read(s, n) or b"")
        if point is not None:
            LAST_POINT["point"] = point                        # TUniversal: the last quorum-final point heard
        return body


# ---------------------------------------------------------------------- TUniversal (Concordance 1.11; mycelium 78.152)
POINT_BIT = 0x80                # a frame carrying the hyphae's quorum-final point sets it on its lane byte
POINT_LEN = 84                  # genesis 32, epoch u32 LE, h, S, G, T, H, K u64 LE
LAST_POINT: Dict[str, Any] = {"point": None}


def read_point(b: bytes) -> Optional[Dict[str, Any]]:
    """A TUniversal point: its origin (genesis, epoch), its height h, its lanes S, G, T, H and its K."""
    if len(b) != POINT_LEN:
        return None
    epoch, h, lane_s, lane_g, lane_t, lane_h, k = struct.unpack_from("<IQQQQQQ", b, 32)
    return {"genesis": b[:32], "epoch": epoch, "h": h, "lanes": (lane_s, lane_g, lane_t, lane_h), "k": k}


def point_text(p: Dict[str, Any]) -> str:
    """Its text form: <genesis hex>.<epoch hex>/h:S:G:T:H:K, each field 16 lowercase hex digits."""
    fields = (p["h"],) + tuple(p["lanes"]) + (p["k"],)
    return f"{p['genesis'].hex()}.{p['epoch']:016x}/" + ":".join(f"{x:016x}" for x in fields)


def unframe(lane: int, body: bytes) -> Tuple[bytes, Optional[Dict[str, Any]]]:
    """A frame's body and the point it carries, if its lane byte says it carries one (its last 84 bytes)."""
    if lane & POINT_BIT and len(body) >= POINT_LEN:
        return body[:-POINT_LEN], read_point(body[-POINT_LEN:])
    return body, None


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
    """A registry task (wire v1.2): [citation 32][nt u8][(input, output) grids][nx u8][test grids] - named by its
    32-byte citation. An empty body is no work; a body that does not frame whole is no task (None), never a crash."""
    if len(body) < 34:
        return None
    try:
        at = 32

        def u8() -> int:
            nonlocal at
            v = body[at]
            at += 1
            return v

        def g() -> List[List[int]]:
            nonlocal at
            h, w = struct.unpack_from("<HH", body, at)
            at += 4
            cells = body[at:at + h * w]
            if len(cells) != h * w:
                raise ValueError("short grid")
            at += h * w
            return [list(cells[r * w:(r + 1) * w]) for r in range(h)]
        train = [(g(), g()) for _ in range(u8())]
        test = [g() for _ in range(u8())]
        if at != len(body):
            return None
        return {"id": body[:32], "train": train, "test": test}
    except (struct.error, IndexError, ValueError):
        return None


def solve(voice: SigningKey, task_id: bytes, outputs: List[List[List[int]]], rule: Optional[bytes] = None) -> bytes:
    body = (bytes([ACT_SOLVE]) + vk(voice) + task_id[:32]          # wire v1.2: the task's 32-byte citation
            + bytes([len(outputs)]) + b"".join(grid(o) for o in outputs))
    if rule is not None:
        body += b"RULE" + struct.pack("<I", len(rule)) + rule
    return body + b"SIGN" + voice.sign(SOLVE_TAG + body).signature


def solve_raw(voice: SigningKey, task_id: bytes, outputs: bytes, rule: bytes) -> bytes:
    """A solve whose outputs come already written as ACT_SOLVE writes them ([n u8] then grids) - a seated mind's own."""
    body = bytes([ACT_SOLVE]) + vk(voice) + task_id[:32] + outputs      # wire v1.2: the 32-byte citation
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


RESERVE_TAG = b"mycelium domain reserve v1"
KIND_RESERVE = 1


def reserve(domain: SigningKey, tier: bytes, nonce: bytes) -> bytes:
    """The domain's RESERVE tier designated (mycelium 78.127): the one tier whose mu balance on the court is its reserve
    - barren-realms' ancients' tier, the only species with the uplink. Signed by the domain's key."""
    signed = RESERVE_TAG + vk(domain) + tier + nonce
    return (bytes([ACT_DOMAIN]) + vk(domain) + b"\x80\x00" + bytes([KIND_RESERVE]) + tier + nonce
            + domain.sign(signed).signature)
