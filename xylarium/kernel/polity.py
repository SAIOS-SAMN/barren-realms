"""
Xylarium polity: the sovereigns (T3) - the minds of the peoples' polities - and what happens when they meet.

Every polity (realms.py: a people's capital, its member worlds, the systems it claims) has a sovereign: a seated
player (human or AI) where one has taken it, else the polity's own mind. A people may have many - each polity a
people founds, or that breaks away from it, has its own - and they keep their people's alignment: a sovereign serves
its people, by its people's lights, and treats its kin's sovereigns as its people's character inclines it to.

HOW A SOVEREIGN THINKS (netstratum's reduction, docs/51-54: no score, no gate, no candidate loop):

  BOOKS      it reads its dominion as a signed field, each book in its own units and never summed:
               food      what its worlds lack of their staple, less what they hold beyond need
               room      its people against what its lands feed
               security  the arms of the hostile it has met, against its own
               wealth    what its works and garrisons must keep, against its vaults
               standing  how dark the sovereigns it has met read it, against how bright
  RESIDUAL   what its treaties already cover is drained from the field; what is left, read in the order needs are
             met (food first, standing last), names the deed. Nothing is chosen by a number weighed against others.
  DEEDS      the residual's book names whom to turn to: the sovereign it has met whose own field is the mirror of
             its own on that book (a surplus where it lacks - mutual interest): a treaty, if the other's own residual
             is drained by it too (both must agree: a treaty serves both or it is not made); failing that, a sovereign
             who is weaker and holds what it lacks: war (taken alone; it is recorded as war); failing that, nothing.
  CRYSTALS   what a deed did is read next year as the change in the field it named: a book it drained is sealed with
             it (that signature -> that deed), recalled at once the next time; a book it did not drain is a wall,
             and that deed is not taken again for that signature. Thinking changes the thinker.
  HEARING    when two sovereigns first meet, each hears what the other tells of itself (its doctrine) through what it
             can understand (contact.intelligibility); their conduct books open - given and taken, per book - and
             every treaty kept or broken is written in them.

CONTINUITY. A sovereign reigns a generation of its people (fertility.generation_of); its successor takes its seat,
its crystals and its books - a chronicle inherited, never edited. A polity that breaks away is born with its
parent's crystals and its own books; a polity that ends ends its line (an epitaph in the annals). A seated player's
sovereign carries the same record.

ABOVE IT. A realm's steward (stewardship.py) binds it: no war is made across a steward's ruling, and a war it rules
down ends. Treaties are the sovereigns' own; a steward's ruling is the realm's.
"""

import random
from typing import Any, Dict, List, Optional, Tuple

BOOKS = ("food", "room", "security", "wealth", "standing")     # the order needs are met: the first in deficit leads
TREATIES = ("trade", "defense", "peace", "war")
SERVES = {"food": "trade", "wealth": "trade", "security": "defense", "standing": "peace", "room": "peace"}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "polity")


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


# ---------------------------------------------------------------------- who the sovereigns are
def _holder(realm: Dict[str, Any]) -> str:
    """The people a polity serves (a breakaway's record names its world after its people: 'Name:world')."""
    if realm.get("holder"):
        return realm["holder"]
    return f"civ:{realm['people'].split(':', 1)[0]}" if realm.get("kind") == "civ" else f"captain:{realm['people']}"


def _polities(kernel: Any) -> Dict[str, Dict[str, Any]]:
    """Every polity with a sovereign: the realms (realms.py), and the powers - peoples whose worlds no realm holds
    (the great powers, and any people not yet a realm) - each one polity of its own worlds."""
    from xylarium.kernel import cache, realms, relations

    def build() -> Dict[str, Dict[str, Any]]:
        out = dict(realms.realms(kernel))
        held = {w for r in out.values() for w in r.get("worlds", [])}
        for who, worlds in relations._peoples(kernel).items():
            free = [w for w in worlds if w.id not in held]
            if not free or not who.startswith("civ:"):
                continue
            seat = max(free, key=lambda w: (w.population, w.id))
            name = who.split(":", 1)[1]
            rid = f"POWER-{name}"
            out[rid] = {"id": rid, "name": name, "kind": "power", "people": name, "holder": who,
                        "capital": seat.id, "worlds": [w.id for w in free]}
        return out
    if not hasattr(kernel, "caches"):
        return build()
    return cache.memo(kernel, "polity_polities", kernel.cycle_count, build, max_age=1)


def _worlds(kernel: Any, realm: Dict[str, Any]) -> List[Any]:
    out = []
    for wid in realm.get("worlds", []):
        w = kernel.get_planet(wid)
        if w is not None and w.population > 0:
            out.append(w)
    return out


def sovereigns(kernel: Any) -> Dict[str, Dict[str, Any]]:
    return stats(kernel)["sovereigns"]


def of_realm(kernel: Any, realm_id: str) -> Optional[Dict[str, Any]]:
    sid = stats(kernel)["by_realm"].get(realm_id)
    return sovereigns(kernel).get(sid) if sid else None


def of_people(kernel: Any, holder: str) -> List[Dict[str, Any]]:
    return [s for s in sovereigns(kernel).values() if s["people"] == holder and not s.get("ended")]


def _name(kernel: Any, *salt: Any) -> str:
    from xylarium.kernel import scheduler
    from xylarium.kernel.natives import _name as syllables
    return syllables(scheduler.rng(kernel, "sovereign", *salt))


def _seat(kernel: Any, realm: Dict[str, Any], parent: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """A polity's sovereign takes its seat: new, or born of the polity it broke from (its parent's crystals)."""
    st = stats(kernel)
    st["next"] += 1
    sid = f"S-{st['next']:05d}"
    holder = _holder(realm)
    seated = None
    from xylarium.kernel import roles
    for pid, rec in roles.stats(kernel).get("realms", {}).items():
        if rec.get("holder") == holder and (rec.get("capital") == realm.get("capital")
                                            or rec.get("capital") in realm.get("worlds", [])):
            seated = pid
    rec = {"id": sid, "name": _name(kernel, sid), "people": holder, "realm": realm["id"], "polity": realm["name"],
           "since": kernel.cycle_count, "line": parent["line"] if parent else sid, "generation": 1,
           "parent": parent["id"] if parent else None, "player": seated,
           "crystals": {k: dict(v) for k, v in (parent or {}).get("crystals", {}).items()},
           "walls": {k: list(v) for k, v in (parent or {}).get("walls", {}).items()},
           "books": {}, "heard": {}, "last": None}
    sovereigns(kernel)[sid] = rec
    st["by_realm"][realm["id"]] = sid
    from xylarium.kernel import history
    history.event(kernel, "SOVEREIGN", f"{rec['name']} takes the seat of the {realm['name']}", actors=[holder],
                  cause=("born of the " + sovereigns(kernel)[parent["id"]]["polity"]) if parent else "a polity's first",
                  data={"sovereign": sid, "line": rec["line"]})
    return rec


def _succeed(kernel: Any, rec: Dict[str, Any]) -> None:
    """A reign ends with its generation: the successor takes the seat, its crystals and its books."""
    from xylarium.kernel import history
    old = rec["name"]
    rec["generation"] += 1
    rec["name"] = _name(kernel, rec["id"], rec["generation"])
    rec["since"] = kernel.cycle_count
    history.event(kernel, "SUCCESSION", f"{rec['name']} succeeds {old} in the {rec['polity']}", actors=[rec["people"]],
                  cause=f"a generation's reign; the line of {rec['line']} goes on", data={"sovereign": rec["id"]})


def _attend(kernel: Any) -> List[Dict[str, Any]]:
    """Keep the seats in step with the polities: seat the new, end the gone, pass the reigns that are over."""
    from xylarium.kernel import fertility, history
    st = stats(kernel)
    live = _polities(kernel)
    for rid, realm in live.items():
        if rid not in st["by_realm"]:
            parent = of_realm(kernel, realm["seceded_from"]) if realm.get("seceded_from") else None
            _seat(kernel, realm, parent)                       # a breakaway is born of the polity it left
    for rid, sid in list(st["by_realm"].items()):
        rec = sovereigns(kernel).get(sid)
        if rid not in live:
            if rec is not None and not rec.get("ended"):
                rec["ended"] = kernel.cycle_count
                history.event(kernel, "EPITAPH", f"The line of {rec['name']} ends with the {rec['polity']}",
                              actors=[rec["people"]], cause="its polity is no more", data={"sovereign": sid})
            st["by_realm"].pop(rid, None)
            continue
        cap = kernel.get_planet(live[rid]["capital"])
        if rec is not None and cap is not None and cap.population > 0:
            reign = max(1.0, fertility.generation_of(kernel, cap)) * 100
            if kernel.cycle_count - rec["since"] >= reign:
                _succeed(kernel, rec)
    return [s for s in sovereigns(kernel).values() if not s.get("ended")]


# ---------------------------------------------------------------------- what a sovereign reads
HURTS = ("WAR", "RAID", "CONQUEST", "SUBJUGATION", "GALACTIC_WAR")


def attackers(kernel: Any, rec: Dict[str, Any]) -> List[str]:
    """The peoples that have struck its people within a steward's ruling span (the ledger, its people's index)."""
    from xylarium.kernel import history, stewardship
    since = kernel.cycle_count - 100 * stewardship.RULING_YEARS
    out = []
    for e in history.of_people(kernel, rec["people"]):
        if e.get("kind") in HURTS and e.get("cycle", 0) >= since:
            for a in e.get("actors", []):
                if a != rec["people"] and a not in out and not str(a).startswith("captain:"):
                    out.append(a)
    return out


def field(kernel: Any, rec: Dict[str, Any]) -> Dict[str, float]:
    """Its dominion as a signed field: each book's need less what it has (positive: a deficit), in its own units."""
    from xylarium.kernel import biosphere, realms, reputation, staples, strategy, sustenance
    realm = _polities(kernel).get(rec["realm"])
    worlds = _worlds(kernel, realm) if realm else []
    q = _quarter()
    food = room = arms = keep = vault = 0.0
    for w in worlds:
        staple = staples.of(kernel, w)
        ss = float(w.society.get("self_sufficiency", 1.0) or 1.0)
        food += biosphere.consumption(w) * q * max(0.0, 1.0 - ss) - staples.surplus(kernel, w, staple)
        room += w.population - biosphere.carrying_capacity(kernel, w)
        arms += sustenance._strength(w)
        keep += float(w.citadel_level + 1) * q * 100.0
        vault += float(w.treasury)
    hostile = 0.0
    dark = bright = 0.0
    struck = set(attackers(kernel, rec))
    for oid in rec["heard"]:
        other = sovereigns(kernel).get(oid)
        if other is None or other.get("ended"):
            continue
        orealm = _polities(kernel).get(other["realm"])
        oworlds = _worlds(kernel, orealm) if orealm else []
        if other["people"] in struck or \
                strategy.hostility(kernel, other["people"]) > strategy.hostility(kernel, rec["people"]):
            hostile += sum(sustenance._strength(w) for w in oworlds)
        r = reputation.read(kernel, other["people"], rec["people"])
        if r is not None:
            dark += max(0.0, -r)
            bright += max(0.0, r)
    return {"food": food, "room": room, "security": hostile - arms, "wealth": keep - vault, "standing": dark - bright}


def covered(kernel: Any, rec: Dict[str, Any], book: str) -> bool:
    """Is this book already served by a treaty it holds?"""
    want = SERVES.get(book)
    return any(t["kind"] == want for t in treaties_of(kernel, rec["id"]))


def residual(kernel: Any, rec: Dict[str, Any], f: Optional[Dict[str, float]] = None) -> List[str]:
    """The books still in deficit once its treaties are drained from the field, in the order needs are met."""
    f = f if f is not None else field(kernel, rec)
    return [b for b in BOOKS if f[b] > 0 and not covered(kernel, rec, b)]


def signature(f: Dict[str, float]) -> str:
    """The field's shape: the sign of each book (what a crystal is keyed by)."""
    return "".join("+" if f[b] > 0 else ("-" if f[b] < 0 else "0") for b in BOOKS)


# ---------------------------------------------------------------------- treaties and conduct
def _pair(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


def treaties_of(kernel: Any, sid: str) -> List[Dict[str, Any]]:
    return [t for t in stats(kernel)["treaties"].values() if sid in (t["a"], t["b"])]


def treaty(kernel: Any, a: str, b: str) -> Optional[Dict[str, Any]]:
    return stats(kernel)["treaties"].get(_pair(a, b))


def _book(rec: Dict[str, Any], other: str) -> Dict[str, List[float]]:
    return rec["books"].setdefault(other, {b: [0.0, 0.0] for b in BOOKS})


def _conduct(kernel: Any, giver: Dict[str, Any], taker: Dict[str, Any], book: str, given: float = 0.0,
             taken: float = 0.0) -> None:
    """Both sides write it: what one gave or took, on which book."""
    g = _book(giver, taker["id"])[book]
    g[0] += given
    g[1] += taken
    t = _book(taker, giver["id"])[book]
    t[0] += taken
    t[1] += given


def at_peace(kernel: Any, a: Optional[str], b: Optional[str]) -> bool:
    """Do two peoples' sovereigns hold a treaty other than war (their peoples do not raid each other)?"""
    if not a or not b or "polity" not in getattr(kernel, "state", {}):
        return False
    for sa in of_people(kernel, a):
        for t in treaties_of(kernel, sa["id"]):
            other = t["b"] if t["a"] == sa["id"] else t["a"]
            o = sovereigns(kernel).get(other)
            if o is not None and o["people"] == b and t["kind"] != "war":
                return True
    return False


def _make(kernel: Any, a: Dict[str, Any], b: Dict[str, Any], kind: str, why: str) -> Dict[str, Any]:
    from xylarium.kernel import history, relations
    old = treaty(kernel, a["id"], b["id"])
    if old is not None and old["kind"] != kind and old["kind"] in ("peace", "trade", "defense") and kind == "war":
        _conduct(kernel, b, a, "standing", taken=1.0)          # a treaty broken: written against the breaker
    t = {"a": a["id"], "b": b["id"], "kind": kind, "since": kernel.cycle_count, "by": a["id"], "why": why}
    stats(kernel)["treaties"][_pair(a["id"], b["id"])] = t
    if kind in ("trade", "defense", "peace") and a["people"] != b["people"]:
        relations.pacts(kernel).setdefault(relations._pair(a["people"], b["people"]),
                                           {"since": kernel.cycle_count, "by": "sovereigns"})
    title = {"trade": "trade", "defense": "stand together", "peace": "make peace", "war": "go to war"}[kind]
    history.event(kernel, "WAR" if kind == "war" else "TREATY",
                  f"{a['name']} of the {a['polity']} and {b['name']} of the {b['polity']} {title}"
                  if kind != "war" else f"{a['name']} of the {a['polity']} makes war on the {b['polity']}",
                  actors=[a["people"], b["people"]], cause=why, data={"sovereigns": [a["id"], b["id"]], "kind": kind})
    return t


def _hears(kernel: Any, rec: Dict[str, Any], other: Dict[str, Any]) -> str:
    """A first meeting: it hears what the other tells of itself, as far as it can understand it."""
    from xylarium.kernel import alignment, contact, realms, reputation
    understood = contact.intelligibility(kernel, rec["people"], other["people"])
    orealm = _polities(kernel).get(other["realm"])
    cap = kernel.get_planet(orealm["capital"]) if orealm else None
    civ = getattr(cap, "civilization", None) if cap is not None else None
    if civ is not None and rec["people"] != other["people"]:
        told = alignment.doctrine(civ)                         # what it tells of itself, heard as far as understood
        reputation.witness(kernel, rec["people"], other["people"], light=max(0.0, told) * understood,
                           dark=max(0.0, -told) * understood)
    rec["heard"][other["id"]] = round(float(understood), 4)
    _book(rec, other["id"])
    return "understood" if understood >= 0.5 else "learned"


# ---------------------------------------------------------------------- the season
def _mirror(kernel: Any, rec: Dict[str, Any], book: str, fields: Dict[str, Dict[str, float]]) -> Optional[Dict[str, Any]]:
    """The sovereign it has met whose field mirrors its own on this book (a surplus where it lacks) and whose own
    residual this book's treaty would drain too: mutual interest. The deepest mirror first (it gives the most)."""
    want = SERVES[book]
    best = None
    for oid in rec["heard"]:
        o = sovereigns(kernel).get(oid)
        if o is None or o.get("ended") or oid not in fields:
            continue
        of = fields[oid]
        if of[book] >= 0:
            continue                                           # it has no surplus of what this one lacks
        theirs = [b for b in BOOKS if of[b] > 0 and SERVES.get(b) == want]
        if not theirs and want != "trade":
            continue                                           # the treaty would serve only one side
        if best is None or of[book] < fields[best["id"]][book]:
            best = o
    return best


def _weaker_holder(kernel: Any, rec: Dict[str, Any], book: str, fields: Dict[str, Dict[str, float]]) -> Optional[Dict[str, Any]]:
    """A sovereign it has met that holds what it lacks and whose arms are less than its own (measured, not dialled)."""
    from xylarium.kernel import realms, stewardship, sustenance
    mine = sum(sustenance._strength(w) for w in _worlds(kernel, _polities(kernel).get(rec["realm"], {"worlds": []})))
    best = None
    for oid in rec["heard"]:
        o = sovereigns(kernel).get(oid)
        if o is None or o.get("ended") or oid not in fields or fields[oid][book] >= 0:
            continue
        if o["people"] == rec["people"] and _kin_cooperate(kernel, rec):
            continue                                           # a people that leans to the Light does not prey on its own
        if stewardship.binds(kernel, rec["people"], o["people"]) or stewardship.binds(kernel, rec["people"], o["people"], "pact"):
            if book == "food":                                 # its people's hunger, barred: it goes up the chain
                stewardship.appeal(kernel, rec, o["people"])
            continue                                           # a steward's ruling stands between them
        theirs = sum(sustenance._strength(w) for w in _worlds(kernel, _polities(kernel).get(o["realm"], {"worlds": []})))
        if theirs < mine and (best is None or fields[oid][book] < fields[best["id"]][book]):
            best = o
    return best


def _kin_cooperate(kernel: Any, rec: Dict[str, Any]) -> bool:
    """Kin sovereigns stand together as far as their people's character leans to the Light (its whole history)."""
    from xylarium.kernel import alignment, realms
    realm = _polities(kernel).get(rec["realm"])
    cap = kernel.get_planet(realm["capital"]) if realm else None
    civ = getattr(cap, "civilization", None) if cap is not None else None
    return civ is not None and alignment.character(civ) > 0


def _learn(kernel: Any, rec: Dict[str, Any], f: Dict[str, float]) -> None:
    """What last year's deed did: the book it named drained (a crystal) or not (a wall for that signature)."""
    last = rec.get("last")
    if not last or not last.get("deed"):
        return
    book, deed, sig = last["book"], last["deed"], last["signature"]
    if f[book] < last["field"][book]:
        rec["crystals"].setdefault(sig, {})[book] = deed
    else:
        walls = rec["walls"].setdefault(sig, [])
        if deed not in walls:
            walls.append(deed)


def think(kernel: Any, rec: Dict[str, Any], fields: Dict[str, Dict[str, float]]) -> Optional[str]:
    """One deed a year: the first book its residual leaves in deficit names it - recalled from a crystal if it has one,
    else the mirror's treaty, else war on a weaker holder, else nothing. A seated player's sovereign is not thought
    for: its player chooses."""
    f = fields[rec["id"]]
    _learn(kernel, rec, f)
    sig = signature(f)
    left = residual(kernel, rec, f)
    rec["last"] = {"field": f, "signature": sig, "deed": None, "book": left[0] if left else None}
    if rec.get("player") or not left:
        return None
    book = left[0]
    recalled = rec["crystals"].get(sig, {}).get(book)
    walls = rec["walls"].get(sig, [])
    want = SERVES[book]
    if recalled is not None:
        want = recalled
    if book == "security" and recalled is None:
        return _secure(kernel, rec, fields, walls)
    partner = _mirror(kernel, rec, book, fields) if want != "war" and want not in walls else None
    if partner is not None:
        t = treaty(kernel, rec["id"], partner["id"])
        if t is None or t["kind"] != want:
            _make(kernel, rec, partner, want, f"its {book} in deficit, the other's in surplus: both are served")
            _conduct(kernel, rec, partner, book, given=1.0)
            rec["last"]["deed"] = want
            return want
    if "war" not in walls and book in ("food", "room", "wealth"):
        prey = _weaker_holder(kernel, rec, book, fields)
        if prey is not None:
            t = treaty(kernel, rec["id"], prey["id"])
            if t is None or t["kind"] != "war":
                _make(kernel, rec, prey, "war", f"its {book} in deficit and no one to trade it: it takes it")
                _conduct(kernel, rec, prey, book, taken=1.0)
                _wage(kernel, rec, prey)
                rec["last"]["deed"] = "war"
                return "war"
    return None


def _secure(kernel: Any, rec: Dict[str, Any], fields: Dict[str, Dict[str, float]], walls: List[str]) -> Optional[str]:
    """Its security leads: stand with one struck by the same hand (a defense treaty - both are served), else make
    peace with the one that strikes it, if peace serves that one too (its own standing or security in deficit).
    Failing both, it bears it - and its steward hears the dispute."""
    struck_me = set(attackers(kernel, rec))
    if "defense" not in walls:
        for oid in rec["heard"]:
            o = sovereigns(kernel).get(oid)
            if o is None or o.get("ended") or oid not in fields or o["people"] in struck_me:
                continue
            shared = struck_me & set(attackers(kernel, o))
            if shared and "security" in residual(kernel, o, fields[oid]):
                t = treaty(kernel, rec["id"], oid)
                if t is None or t["kind"] != "defense":
                    _make(kernel, rec, o, "defense", f"struck by the same hand ({sorted(shared)[0].split(':', 1)[-1]})")
                    _conduct(kernel, rec, o, "security", given=1.0)
                    rec["last"]["deed"] = "defense"
                    return "defense"
    if "peace" not in walls:
        for oid in rec["heard"]:
            o = sovereigns(kernel).get(oid)
            if o is None or o.get("ended") or oid not in fields or o["people"] not in struck_me:
                continue
            theirs = residual(kernel, o, fields[oid])
            if "standing" in theirs or "security" in theirs:
                t = treaty(kernel, rec["id"], oid)
                if t is None or t["kind"] != "peace":
                    _make(kernel, rec, o, "peace", "the struck and the striker: peace serves them both")
                    _conduct(kernel, rec, o, "standing", given=1.0)
                    rec["last"]["deed"] = "peace"
                    return "peace"
    return None


def _wage(kernel: Any, rec: Dict[str, Any], prey: Dict[str, Any]) -> None:
    """War is fought by the laws that fight it: the aggressor's capital raises its levy and raids."""
    from xylarium.kernel import realms, society, sustenance
    realm = _polities(kernel).get(rec["realm"])
    cap = kernel.get_planet(realm["capital"]) if realm else None
    if cap is None or cap.population <= 0:
        return
    g = society.gauges(cap)
    society.set_gauge(cap, "levy", min(1.0, g["levy"] + (1.0 - g["levy"]) / len(BOOKS)))
    try:
        sustenance.raid(kernel, cap, plunder=True)
    except Exception:
        pass


def _meet(kernel: Any, live: List[Dict[str, Any]]) -> List[str]:
    """New meetings, from contact (who the peoples' ships reach) - only the pairs that have just met."""
    from xylarium.kernel import contact, relations
    by = relations._peoples(kernel)
    met = contact.contacts(kernel, by)
    by_people: Dict[str, List[Dict[str, Any]]] = {}
    for s in live:
        by_people.setdefault(s["people"], []).append(s)
    logs = []
    for s in live:
        neighbours = set(met.get(s["people"], {})) | {s["people"]} | set(attackers(kernel, s))
        for people in neighbours:
            for o in by_people.get(people, []):
                if o["id"] != s["id"] and o["id"] not in s["heard"]:
                    heard = _hears(kernel, s, o)
                    if s["id"] not in o["heard"]:
                        _hears(kernel, o, s)
                    from xylarium.kernel import history
                    history.event(kernel, "SOVEREIGNS_MEET", f"{s['name']} of the {s['polity']} meets {o['name']} of "
                                  f"the {o['polity']}", actors=[s["people"], o["people"]],
                                  cause=("kin" if s["people"] == o["people"] else
                                         f"they understand each other {s['heard'][o['id']]:.0%}"),
                                  data={"sovereigns": [s["id"], o["id"]]})
                    logs.append(f"[SOVEREIGNS] {s['name']} of the {s['polity']} meets {o['name']} of the {o['polity']}.")
    return logs


def _bend(kernel: Any) -> None:
    """Sovereigns bend to stewards: a war a steward has ruled down ends."""
    from xylarium.kernel import stewardship
    for key, t in list(stats(kernel)["treaties"].items()):
        if t["kind"] != "war":
            continue
        a, b = sovereigns(kernel).get(t["a"]), sovereigns(kernel).get(t["b"])
        if a is None or b is None or a.get("ended") or b.get("ended"):
            stats(kernel)["treaties"].pop(key, None)
            continue
        if stewardship.binds(kernel, a["people"], b["people"]) or stewardship.binds(kernel, a["people"], b["people"], "pact"):
            t["kind"] = "peace"
            t["since"] = kernel.cycle_count
            t["why"] = "a steward's ruling"


def season(kernel: Any) -> List[str]:
    """Once a year: seats kept, new meetings heard, wars ruled down end, and each sovereign takes its one deed."""
    if (kernel.cycle_count // _quarter()) % 4:
        return []
    live = _attend(kernel)
    logs = _meet(kernel, live)
    _bend(kernel)
    fields = {s["id"]: field(kernel, s) for s in live}
    for s in live:
        deed = think(kernel, s, fields)
        if deed is not None:
            logs.append(f"[SOVEREIGNS] {s['name']} of the {s['polity']}: {deed}.")
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    kinds: Dict[str, int] = {}
    for t in st["treaties"].values():
        kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
    return {"sovereigns": sum(1 for s in st["sovereigns"].values() if not s.get("ended")),
            "lines_ended": sum(1 for s in st["sovereigns"].values() if s.get("ended")), "treaties": kinds}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="polity",
    state=lambda: {"sovereigns": {}, "by_realm": {}, "treaties": {}, "next": 0},
    season=season,
    summary=summary,
))
