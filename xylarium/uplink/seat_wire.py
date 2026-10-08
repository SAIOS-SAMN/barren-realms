"""
Xylarium uplink seat wire: the seat surface v1 (mycelium's ACT_SEAT, 0x53) as barren-realms' ancients' house speaks it.

The hypha is a general signed relay; it judges nothing in-game. The house (its domain's sitting reserve: the ancients'
tier key) posts SEATS, TAKEN, PERCEPT and OUTCOME and reads its mail for TAKE and CALL; a mind posts TAKE and CALL
under its own key. Every integer is little-endian; every number is exact (Q: i64 numerator, u64 denominator > 0).
Functions and records are typed ids, never names: barren-realms' tables are FUNCTIONS and RECORDS below, and every
in-game name (a people, a realm) travels as a Key - the sha256 of the name - which the house maps back.

  act body = [0x53][sub-kind u8][fields][sig 64], sig = ed25519 over b"mycelium seat v1" || [sub-kind][fields]
  call ref = blake3 of the same signed bytes (confirmed by mycelium)
"""

import hashlib
import struct
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

import blake3
from nacl.signing import SigningKey, VerifyKey

ACT_SEAT = 0x53
TAG = b"mycelium seat v1"
SIGNED_FROM = 1                  # the act tag is not signed; the sub-kind and every field are
SEATS, TAKE, TAKEN, PERCEPT, CALL, OUTCOME, READ_LISTING, READ_MAIL = range(8)
Q_, KEY, COUNT, FLAG, MV, BIGQ, BYTES = range(7)
ROLE = {"progenitor": 0, "ancients": 1, "steward": 2, "sovereign": 3}   # 4..9 the captains' offices
COUNSEL = 0xFFFF

# barren-realms' functions: typed id -> (name, the argument tags it takes)
FUNCTIONS: Dict[int, Tuple[str, Tuple[int, ...]]] = {
    # a mind's answer: [Bytes(its rule's Element tape), Bytes(the test outputs as ACT_SOLVE writes them)] and/or its
    # steps as Counts (1..6 a motion, the crystal ops; 0x100 + 16*from + to a hue move)
    1: ("answer", (BYTES, BYTES, COUNT)),
    10: ("send", (KEY,)), 11: ("recall", (KEY,)), 12: ("fold", (KEY, FLAG)), 13: ("handle", (COUNT,)),
    14: ("forge", (COUNT, COUNT)),
    20: ("claim", (KEY,)), 21: ("withdraw", ()), 22: ("grant", (KEY,)), 23: ("ascend", (KEY,)),
    24: ("quarantine", (KEY,)), 25: ("fortify", (COUNT, Q_)),
}
FN_ID = {name: i for i, (name, _) in FUNCTIONS.items()}
# barren-realms' percept records: typed kind -> what its ARGS are
RECORDS = {1: "petition: people Key, ruling Count (0 pending, 1 ascended, 2 quarantine)",
           2: "book: people Key, book Count (ascendance.BOOKS index), syntropic Q, entropic Q",
           3: "crystal: op Count",
           4: "court task: Bytes(its raw registry id), Key (sha256 of that id)",
           5: "realm covered: realm Key"}
HANDLE = ("open", "tolled", "guarded", "closed")


def name_key(name: str) -> bytes:
    """An in-game name as the wire's Key: its sha256."""
    return hashlib.sha256(name.encode()).digest()


# ---------------------------------------------------------------------- args
def arg(tag: int, v: Any) -> bytes:
    if tag in (Q_, BIGQ):
        q = Fraction(v)
        if -2 ** 63 <= q.numerator < 2 ** 63 and q.denominator < 2 ** 64:
            return bytes([Q_]) + struct.pack("<qQ", q.numerator, q.denominator)
        num = q.numerator.to_bytes((q.numerator.bit_length() + 8) // 8, "little", signed=True)
        den = q.denominator.to_bytes((q.denominator.bit_length() + 7) // 8, "little")
        return bytes([BIGQ]) + struct.pack("<H", len(num)) + num + struct.pack("<H", len(den)) + den
    if tag == KEY:
        b = bytes(v)
        assert len(b) == 32
        return bytes([KEY]) + b
    if tag == COUNT:
        return bytes([COUNT]) + struct.pack("<Q", int(v))
    if tag == FLAG:
        return bytes([FLAG, int(bool(v))])
    if tag == BYTES:
        b = bytes(v)
        return bytes([BYTES]) + struct.pack("<H", len(b)) + b
    raise ValueError("an Mv tape is minted by mycelium, never here")


def args(items: List[Tuple[int, Any]]) -> bytes:
    return bytes([len(items)]) + b"".join(arg(t, v) for t, v in items)


def read_args(b: bytes, at: int) -> Tuple[List[Tuple[int, Any]], int]:
    n = b[at]
    at += 1
    out: List[Tuple[int, Any]] = []
    for _ in range(n):
        tag = b[at]
        at += 1
        if tag == Q_:
            num, den = struct.unpack_from("<qQ", b, at)
            at += 16
            out.append((Q_, Fraction(num, den)))
        elif tag == BIGQ:
            n_len = struct.unpack_from("<H", b, at)[0]
            num = int.from_bytes(b[at + 2:at + 2 + n_len], "little", signed=True)
            at += 2 + n_len
            d_len = struct.unpack_from("<H", b, at)[0]
            den = int.from_bytes(b[at + 2:at + 2 + d_len], "little")
            at += 2 + d_len
            out.append((BIGQ, Fraction(num, den)))
        elif tag == KEY:
            out.append((KEY, b[at:at + 32]))
            at += 32
        elif tag == COUNT:
            out.append((COUNT, struct.unpack_from("<Q", b, at)[0]))
            at += 8
        elif tag == FLAG:
            out.append((FLAG, bool(b[at])))
            at += 1
        elif tag == BYTES:
            ln = struct.unpack_from("<H", b, at)[0]
            out.append((BYTES, b[at + 2:at + 2 + ln]))
            at += 2 + ln
        else:
            raise ValueError(f"arg tag {tag} not read here")
    return out, at


def q(v: Any) -> bytes:
    """A fixed Q field: tagged as an argument is (Q where it fits, BigQ otherwise) - never rounded."""
    return arg(Q_, v)


# ---------------------------------------------------------------------- signing
def seal(sk: SigningKey, sub: int, fields: bytes) -> bytes:
    body = bytes([ACT_SEAT, sub]) + fields
    return body + sk.sign(TAG + body[SIGNED_FROM:]).signature


def opened(act: bytes, vk: bytes) -> bool:
    try:
        VerifyKey(vk).verify(TAG + act[SIGNED_FROM:-64], act[-64:])
        return True
    except Exception:
        return False


def call_ref(act: bytes) -> bytes:
    """A call's reference: blake3 of exactly the bytes its signature covers (the tag, the sub-kind, the fields)."""
    return blake3.blake3(TAG + act[SIGNED_FROM:-64]).digest()


# ---------------------------------------------------------------------- the house's posts
def seats_post(house: SigningKey, domain: bytes, epoch: int, listing: List[Dict[str, Any]]) -> bytes:
    """SEATS: [domain][epoch u64][n u16] SEAT... ; SEAT = [seat u32][role u8][on key][beat Q][fns u16] FN... ;
    FN = [fn u16][k u8][argtag...]."""
    out = domain + struct.pack("<QH", epoch, len(listing))
    for s in listing:
        fns = [FN_ID[f] for f in s["functions"]]
        out += struct.pack("<IB", s["n"], ROLE[s["role"]]) + name_key(s["on"]) + q(s["beat"]) + struct.pack("<H", len(fns))
        for f in fns:
            tags = FUNCTIONS[f][1]
            out += struct.pack("<HB", f, len(tags)) + bytes(tags)
    return seal(house, SEATS, out)


def taken_post(house: SigningKey, domain: bytes, seat: int, mind: bytes, ok: bool, reason: int = 0) -> bytes:
    return seal(house, TAKEN, domain + struct.pack("<I", seat) + mind + struct.pack("<BH", int(ok), reason))


def percept_post(house: SigningKey, domain: bytes, seat: int, mind: bytes, local: Any, seq: int,
                 records: List[Tuple[int, List[Tuple[int, Any]]]],
                 counsel: List[Tuple[int, List[Tuple[int, Any]], Any, Any]]) -> bytes:
    """PERCEPT: [domain][seat][mind][local time Q][seq u64][n u16] REC... ; REC = [kind u16][ARGS]; COUNSEL is
    kind 0xFFFF: [fn u16][ARGS][worth Q][cost Q]."""
    recs = [struct.pack("<H", k) + args(a) for k, a in records]
    recs += [struct.pack("<HH", COUNSEL, fn) + args(a) + q(w) + q(c) for fn, a, w, c in counsel]
    return seal(house, PERCEPT, domain + struct.pack("<I", seat) + mind + q(local) + struct.pack("<QH", seq, len(recs))
                + b"".join(recs))


def outcome_post(house: SigningKey, domain: bytes, seat: int, mind: bytes, ref: bytes, applied: bool, reason: int,
                 deed: bytes) -> bytes:
    return seal(house, OUTCOME, domain + struct.pack("<I", seat) + mind + ref + struct.pack("<BH", int(applied), reason)
                + deed)


def read_mail(reader: SigningKey, after: int, nonce: bytes) -> bytes:
    return seal(reader, READ_MAIL, reader.verify_key.encode() + struct.pack("<Q", after) + nonce)


# ---------------------------------------------------------------------- what the house reads
def read_take(act: bytes) -> Optional[Dict[str, Any]]:
    """TAKE: [domain][seat u32][mind][nonce 32][sig], signed by the mind."""
    if len(act) != 2 + 32 + 4 + 32 + 32 + 64 or act[1] != TAKE:
        return None
    seat = struct.unpack_from("<I", act, 34)[0]
    mind = act[38:70]
    return {"domain": act[2:34], "seat": seat, "mind": mind, "ok": opened(act, mind)}


def read_call(act: bytes) -> Optional[Dict[str, Any]]:
    """CALL: [domain][seat][mind][nonce 32][fn u16][ARGS][sig], signed by the mind; its ref is blake3(signed body)."""
    if len(act) < 2 + 32 + 4 + 32 + 32 + 2 + 1 + 64 or act[1] != CALL:
        return None
    seat = struct.unpack_from("<I", act, 34)[0]
    mind = act[38:70]
    fn = struct.unpack_from("<H", act, 102)[0]
    a, at = read_args(act, 104)
    if at != len(act) - 64:
        return None
    return {"domain": act[2:34], "seat": seat, "mind": mind, "fn": fn, "args": a, "ok": opened(act, mind),
            "ref": call_ref(act)}


def read_mail_reply(body: bytes) -> Optional[List[Tuple[int, int, bytes]]]:
    """READ-MAIL's reply, as the relay frames it on the wire (aefc6a39): [count u16] then per item [seq u64][sub u8]
    [len u32][fields || sig], in seq order - [0][0] an empty box; anything that does not frame whole (a refusal, a
    deferral) is no mail (None). Each item comes back as a whole act ([0x53][sub][fields][sig])."""
    if len(body) < 2:
        return None
    n = struct.unpack_from("<H", body, 0)[0]
    at, out = 2, []
    for _ in range(n):
        if at + 13 > len(body):
            return None
        seq, sub, ln = struct.unpack_from("<QBI", body, at)
        at += 13
        if at + ln > len(body):
            return None
        out.append((seq, sub, bytes([ACT_SEAT, sub]) + body[at:at + ln]))
        at += ln
    return out if at == len(body) else None
