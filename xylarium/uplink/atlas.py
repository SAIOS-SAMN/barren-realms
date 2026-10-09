"""
Xylarium atlas: barren-realms' throats on the hypha's MAP (mycelium 78.154, record kind 2 LOCAL THROAT; 5.9: every
crossing needs coordinates from the hypha's map, and no private maps).

  A LOCAL THROAT  [2][throat key 32][keeper 32][frame_0 Mv][frame_1 Mv][N u64 LE] - a throat of this universe's
                  own, both ends here. Its mouth id: derive_key("mycelium local throat v1", domain || throat key);
                  sides 0 and 1 are its ends.
  ITS FRAMES      each end's place in this universe's own space, as the GEOMETRY its origin declared (curved, of
                  radius R geometrized megaparsecs) reads a place: a point of the sheet (v^2 = -1, the pole e-), and
                  the frame the transvection carrying the pole to it, R = 1 - v e- (mycelium hyperboloid.rs: even, a
                  versor, fixing e+, carrying the pole to the upper sheet - exact over Q). The galaxy's centre stands
                  at the pole; an end at galactocentric p (kpc) stands at the sheet point whose stereographic
                  coordinate is u = p / 2R (on the grid): v = (2u, 1 + |u|^2) / (1 - |u|^2) - a rational point, so
                  its frame is exact, and its distance from the pole is 2 atanh|u| = |p|/R to the grid.
  THE KEEPER      the progenitor line that keeps it, by a 32-byte id (lines never sign on the court: the reserve
                  carries it inline).
  N               how many final points behind a crossing's point this universe's latest entry may stand at this
                  mouth - the reserve's choice, a design (not a law): FRESHNESS_N.
  THE ACT         MAP 14: [0x3E][domain 32][0x80 0x00][14][point 84][record][nonce 32][sig 64], signed by the reserve
                  over "mycelium domain map v1" || domain || point || record || nonce.
"""

import struct
from fractions import Fraction
from typing import Any, Dict, Optional, Sequence

import blake3

MAP_TAG = b"mycelium domain map v1"
KIND_MAP = 14
LOCAL_THROAT = 2
FRESHNESS_N = 64                # final-point advances: ~2.5 of this universe's commits (each ~25) - a design choice
E1, E2, E3, EP, EM = 1, 2, 4, 8, 16


def _leb(n: int) -> bytes:
    out = bytearray()
    while True:
        b, n = n & 0x7F, n >> 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _mag(x: int) -> bytes:
    return x.to_bytes(max(1, (x.bit_length() + 7) // 8), "little")


def mv_bytes(m: Any) -> bytes:
    """A multivector as mycelium writes it (multivector.rs to_bytes): n - its highest base axis - then the 32
    coefficients of Cl(4,1) in mask order, each [sign: 0 zero, 1 plus, 2 minus][LEB len][numerator LE][LEB len]
    [denominator LE]."""
    n = 0
    for mask, v in m.c.items():
        if v:
            for bit in range(3):
                if mask >> bit & 1:
                    n = max(n, bit + 1)
    out = bytearray([n])
    for mask in range(32):
        v = Fraction(m.c.get(mask, 0))
        sign = 0 if v == 0 else (1 if v > 0 else 2)
        num, den = _mag(abs(v.numerator)), _mag(v.denominator)
        out += bytes([sign]) + _leb(len(num)) + num + _leb(len(den)) + den
    return bytes(out)


def sheet_point(p_kpc: Sequence[float], radius_mpc: Fraction) -> Any:
    """The sheet point an end at galactocentric p (kpc) stands at, exactly: stereographic u = p / 2R on the grid."""
    from xylarium.kernel import field, versor
    u = [field.grid(Fraction(x) / 1000 / (2 * radius_mpc)) for x in p_kpc]
    uu = sum(x * x for x in u)
    if uu >= 1:
        raise ValueError("a place outside the sheet's chart")
    c = {1 << i: 2 * x / (1 - uu) for i, x in enumerate(u)}
    c[EM] = (1 + uu) / (1 - uu)
    return versor.Mv(c)


def frame_to(p_kpc: Sequence[float], radius_mpc: Fraction) -> Any:
    """The frame of an end: the transvection carrying the pole e- to its sheet point, R = 1 - v e- (exact)."""
    from xylarium.kernel import versor
    v = sheet_point(p_kpc, radius_mpc)
    return versor.Mv.scalar(1) - v * versor.Mv({EM: 1})


def place_of(frame: Any) -> Any:
    """Where a frame stands (mycelium frame_base_point): its sandwich of the pole, over its weight F F~."""
    from xylarium.kernel import versor
    w = (frame * frame.reverse()).c.get(0, Fraction(0))
    return (frame * versor.Mv({EM: 1}) * frame.reverse()).scale(1 / w)


def throat_key(key: str) -> bytes:
    return blake3.blake3(b"barren-realms throat " + key.encode()).digest()


def keeper_id(line: Optional[str]) -> bytes:
    return blake3.blake3(b"barren-realms line " + (line or "").encode()).digest() if line else bytes(32)


def mouth_id(domain: bytes, tkey: bytes) -> bytes:
    h = blake3.blake3(derive_key_context="mycelium local throat v1")
    h.update(domain + tkey)
    return h.digest()


def local_throat(tkey: bytes, keeper: bytes, frame0: Any, frame1: Any, n: int = FRESHNESS_N) -> bytes:
    return bytes([LOCAL_THROAT]) + tkey + keeper + mv_bytes(frame0) + mv_bytes(frame1) + struct.pack("<Q", n)


def map_act(reserve: Any, domain: bytes, point: Optional[Dict[str, Any]], record: bytes, nonce: bytes) -> bytes:
    from xylarium.uplink import anastome as an
    pt = an.put_point(point)
    sig = reserve.sign(MAP_TAG + domain + pt + record + nonce).signature
    return bytes([an.ACT_DOMAIN]) + domain + bytes([0x80, 0x00, KIND_MAP]) + pt + record + nonce + sig


MAP_REFUSAL = {14: "a frame is not a versor", 15: "no GEOMETRY declared", 16: "a place does not read in that geometry"}


def state(kernel: Any) -> Dict[str, Any]:
    from xylarium.kernel import state as _state
    return _state.of(kernel, "atlas")


def map_throats(kernel: Any, speak: Any, since_u: int, limit: int = 40) -> Dict[str, Any]:
    """Map this universe's throats on the hypha, a few a turn: each not yet mapped, or mapped before the last
    committed entry (its ends ride the galaxy's turning, so its places are read again at every commit). A refusal is
    named and the throat tried again next turn."""
    import os
    from fractions import Fraction as F
    from xylarium.kernel import cosmos, creation, transit
    from xylarium.uplink import anastome as an
    st = state(kernel)
    done = st.setdefault("mapped", {})
    radius = F(str(creation.big_bang(cosmos.cosmos_seed(kernel))["curvature_mpc"]))
    domain, reserve = an.vk(an.key("domain")), an.key("ancients")
    out: Dict[str, Any] = {"mapped": 0}
    for key, w in sorted(transit.stats(kernel)["worms"].items()):
        if out["mapped"] >= limit:
            break
        if done.get(key, -1) >= since_u:
            continue
        pa, pb = cosmos.position(kernel, w["a"]), cosmos.position(kernel, w["b"])
        if not pa or not pb:
            continue                                      # an end beyond the charted galaxy: no place to read yet
        rec = local_throat(throat_key(key), keeper_id(w.get("builders") or w.get("owner")),
                           frame_to((pa["x"], pa["y"], pa["z"]), radius), frame_to((pb["x"], pb["y"], pb["z"]), radius))
        r = speak(map_act(reserve, domain, an.LAST_POINT["point"], rec, os.urandom(32)))
        if r[:1] == b"\x01":
            done[key] = int(kernel.cycle_count)
            out["mapped"] += 1
        else:
            out["refused"] = MAP_REFUSAL.get(r[1], f"code {r[1]}") if r[:1] == b"\x00" and len(r) > 1 else "silence"
            break
    return out


from xylarium.kernel import state as _st  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="atlas", state=lambda: {"mapped": {}}))
