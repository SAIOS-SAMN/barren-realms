"""
Xylarium mind core: the one reduction every intelligence in the realm thinks by - a port of netstratum's
(docs/51_COGNITION, 52_COGNITIVE_METABOLISM, 53_INTELLIGENCE_PORT, 54_THE_NO_SCALAR_LAW, 09_IDEOLOGY).

A mind holds what it has learned - crystals - and decides by laying what it has against what it needs, draining
from the difference everything its crystals already account for, and acting on, or learning from, what is left.
Need orders; observation supplies. There is no score, no threshold and no candidate search:

  MEASUREMENT  what a mind perceives: a sparse map (site, book) -> an exact rational. A site is what it holds or
               faces (its own polity "self", a world, a ship, another sovereign); a book is a concern, in its own
               units (food, matter, a currency, lives). Books are never summed into one number.
  RESIDUAL     need - have, per entry: positive is a deficit, negative a surplus (signed; nothing is folded away).
  CRYSTAL      a sealed shape (the site's role, the book, the sign) with the deed that answered it and what that
               deed delivered, exactly. A mind's crystals are its memory - its grown basis.
  DRAIN        one forward pass over the residual's own entries: each entry whose shape a crystal knows is drained
               by what that crystal delivers - the lesser of the two (captured), the rest carried (vented). Nothing
               is rounded, nothing gated.
  VERDICT      what is left names what happens - a typed reading, never a boolean:
                 ACCOUNTED       nothing is left: the known deeds answer it
                 GENERATION_GAP  a deficit in a shape no crystal knows: act from the layer's vocabulary, then seal
                 COMPOSITION_GAP a deficit in a known shape its crystal did not fully drain: carry it forward
  LEAD         the residual's first deficit in the layer's own order of books (need orders) - the one deed a beat.
  SEAL         after a deed, what it delivered on the entry it named is read: delivered -> a crystal (that shape,
               that deed, that much); nothing delivered -> a wall (that deed is not tried again for that shape).
  HEARING      another mind's utterance (a crystal) is reduced against the hearer's own: known -> understood;
               unknown -> learned, adopted as far as the hearer understands the speaker. The speaker's memory is
               never copied whole.
  CONDUCT      between two entities, two-sided books per axis (compassion, bond, integrity, morality), each split
               syntropic and entropic; read per axis, never totalled; absent where they have never dealt.

Everything is exact (fractions.Fraction) and in a fixed order (sorted keys), so a mind replays the same way.
"""

from fractions import Fraction
from typing import Any, Dict, Iterable, List, Optional, Tuple

Entry = Tuple[str, str]                     # (site, book)
Chain = Dict[Entry, Fraction]

ACCOUNTED, GENERATION_GAP, COMPOSITION_GAP = "accounted", "generation_gap", "composition_gap"
CONDUCT_AXES = ("compassion", "bond", "integrity", "morality")


def q(x: Any) -> Fraction:
    """An exact rational of a measured value (a float's own binary value, never rounded)."""
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x)
    return Fraction(float(x or 0.0))


def measure(entries: Iterable[Tuple[str, str, Any]]) -> Chain:
    """A measurement from (site, book, value) - zero entries are absent (sparse)."""
    out: Chain = {}
    for site, book, v in entries:
        f = q(v)
        if f:
            out[(site, book)] = out.get((site, book), Fraction(0)) + f
    return {k: v for k, v in sorted(out.items()) if v}


def residual(need: Chain, have: Chain) -> Chain:
    """need - have, per entry, signed."""
    out: Chain = {}
    for k in sorted(set(need) | set(have)):
        d = need.get(k, Fraction(0)) - have.get(k, Fraction(0))
        if d:
            out[k] = d
    return out


def shape(entry: Entry, value: Fraction, role: Optional[str] = None) -> str:
    """A crystal's key: the site's role (not its name - so what is learned of one neighbour serves for the next),
    the book, and the sign."""
    site, book = entry
    return f"{role or site}|{book}|{'+' if value > 0 else '-'}"


# ---------------------------------------------------------------------- a mind's memory
def new_mind() -> Dict[str, Any]:
    return {"crystals": {}, "walls": {}, "heard": {}, "last": None}


def crystals(mind: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return mind.setdefault("crystals", {})


def walls(mind: Dict[str, Any], key: str) -> List[str]:
    return mind.setdefault("walls", {}).get(key, [])


def drain(mind: Dict[str, Any], res: Chain, roles: Optional[Dict[str, str]] = None) -> Tuple[Chain, List[str]]:
    """One forward pass: each deficit whose shape a crystal knows is drained by what that crystal delivers (the
    lesser of the two); returns what is left and the crystals that bound."""
    left: Chain = {}
    bound: List[str] = []
    cs = crystals(mind)
    for k, v in res.items():
        key = shape(k, v, (roles or {}).get(k[0]))
        c = cs.get(key)
        if c is not None and v > 0:
            captured = min(v, Fraction(c["delivers"]))
            bound.append(key)
            if v - captured:
                left[k] = v - captured
        elif v:
            left[k] = v
    return left, bound


def verdict(mind: Dict[str, Any], res: Chain, roles: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """What the residual is, once drained: accounted, or the gap it leaves and the entry it leaves first."""
    left, bound = drain(mind, res, roles)
    deficits = [(k, v) for k, v in left.items() if v > 0]
    if not deficits:
        return {"reading": ACCOUNTED, "left": left, "bound": bound, "lead": None}
    known = set(crystals(mind))
    novel = [(k, v) for k, v in deficits if shape(k, v, (roles or {}).get(k[0])) not in known]
    return {"reading": GENERATION_GAP if novel else COMPOSITION_GAP, "left": left, "bound": bound,
            "deficits": deficits}


def lead(res: Chain, order: Tuple[str, ...], sites: Optional[Tuple[str, ...]] = None,
         deepest: bool = False) -> Optional[Entry]:
    """The residual's first deficit in the layer's own order of books: need orders. Within that book, the sites in
    the order given - or, `deepest`, the largest deficit first (an order within one book, never across books)."""
    best: Optional[Entry] = None
    rank = {b: i for i, b in enumerate(order)}
    srank = {s: i for i, s in enumerate(sites or ())}

    def key(e: Entry) -> tuple:
        return (rank[e[1]], -res[e] if deepest else 0, srank.get(e[0], len(srank)), e[0])
    for (site, book), v in res.items():
        if v <= 0 or book not in rank:
            continue
        if best is None or key((site, book)) < key(best):
            best = (site, book)
    return best


def recall(mind: Dict[str, Any], entry: Entry, value: Fraction, role: Optional[str] = None) -> Optional[str]:
    """The deed a crystal names for this shape, if it has one."""
    c = crystals(mind).get(shape(entry, value, role))
    return c["deed"] if c else None


def intend(mind: Dict[str, Any], entry: Entry, value: Fraction, deed: str, role: Optional[str] = None) -> None:
    """Remember what was done for which entry, to be read next beat."""
    mind["last"] = {"site": entry[0], "book": entry[1], "value": str(value), "deed": deed, "role": role}


def seal(mind: Dict[str, Any], now: Chain) -> Optional[str]:
    """Read what last beat's deed delivered on the entry it named: delivered -> a crystal (sealed or deepened);
    nothing -> a wall for that shape. Returns the reading ('crystal' / 'wall') or None."""
    last = mind.get("last")
    if not last or not last.get("deed"):
        return None
    entry = (last["site"], last["book"])
    before = Fraction(last["value"])
    after = now.get(entry, Fraction(0))
    delivered = before - after
    key = shape(entry, before, last.get("role"))
    mind["last"] = None
    if delivered > 0:
        c = crystals(mind).get(key)
        if c is None or c["deed"] != last["deed"]:
            crystals(mind)[key] = {"deed": last["deed"], "delivers": str(delivered)}
        else:
            c["delivers"] = str(max(Fraction(c["delivers"]), delivered))
        return "crystal"
    w = mind.setdefault("walls", {}).setdefault(key, [])
    if last["deed"] not in w:
        w.append(last["deed"])
    return "wall"


def hear(hearer: Dict[str, Any], key: str, crystal: Dict[str, Any], understood: Any) -> str:
    """Another mind's crystal, reduced against the hearer's own: understood if it knows that shape and deed; else
    learned - adopted, delivering as much as the hearer understood of it."""
    mine = crystals(hearer).get(key)
    if mine is not None and mine["deed"] == crystal["deed"]:
        return "understood"
    part = Fraction(crystal["delivers"]) * q(understood)
    if part > 0 and mine is None:
        crystals(hearer)[key] = {"deed": crystal["deed"], "delivers": str(part), "heard": True}
        return "learned"
    return "unheard"


def inherit(mind: Dict[str, Any]) -> Dict[str, Any]:
    """A successor's mind: the crystals and walls of the one before, carried, never edited."""
    return {"crystals": {k: dict(v) for k, v in crystals(mind).items()},
            "walls": {k: list(v) for k, v in mind.get("walls", {}).items()}, "heard": {}, "last": None}


# ---------------------------------------------------------------------- conduct between entities
def conduct(books: Dict[str, Any], other: str) -> Dict[str, List[str]]:
    """Two-sided conduct with one other, per axis: [syntropic, entropic], as exact rationals (strings in state)."""
    return books.setdefault(other, {a: ["0", "0"] for a in CONDUCT_AXES})


def record(books_a: Dict[str, Any], books_b: Dict[str, Any], a: str, b: str, axis: str, syntropic: Any = 0,
           entropic: Any = 0) -> None:
    """a did b a deed on an axis: both write it, each from its side."""
    for books, other in ((books_a, b), (books_b, a)):
        c = conduct(books, other)[axis]
        c[0] = str(Fraction(c[0]) + q(syntropic))
        c[1] = str(Fraction(c[1]) + q(entropic))


def reading(books: Dict[str, Any], other: str) -> Dict[str, Optional[Fraction]]:
    """How one reads its dealings with another, per axis: syntropic over all, or None where nothing has passed."""
    out: Dict[str, Optional[Fraction]] = {}
    c = books.get(other)
    for axis in CONDUCT_AXES:
        if c is None:
            out[axis] = None
            continue
        s, e = Fraction(c[axis][0]), Fraction(c[axis][1])
        out[axis] = s / (s + e) if s + e else None
    return out
