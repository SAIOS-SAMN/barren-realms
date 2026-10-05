"""
Xylarium polity: the sovereigns (T3) - the minds of the peoples' polities - and what happens when they meet.

Every polity (realms.py: a people's capital, its member worlds, the systems it claims) has a sovereign: a seated
player (human or AI) where one has taken it, else the polity's own mind. A people may have many - each polity a
people founds, or that breaks away from it, has its own - and they keep their people's alignment: a sovereign serves
its people, by its people's lights, and treats its kin's sovereigns as its people's character inclines it to.

HOW A SOVEREIGN THINKS - by the mind core (mindcore.py: netstratum's reduction; no score, no gate, no search):

  BOOKS      its dominion measured as need and have, exactly, per book, each in its own units, never summed:
               food      what its worlds lack of their staple / what they hold beyond need
               room      its people / what its lands feed
               security  the arms of those that strike it or are more hostile than it / its own arms
               wealth    what its works and garrisons must keep / its vaults
               standing  how dark the sovereigns it has met read it / how bright
  RESIDUAL   the field less what its treaties deliver, exactly - a trade partner's surplus of what it lacks, an
             ally's arms, the arms a peace takes off those that strike it - the lesser captured, the rest carried.
  LEAD       the first deficit, in the order needs are met (food first, standing last), names the book; a crystal
             of that shape recalls its deed, else the book's vocabulary is taken in order (food: trade, then war;
             security: defense, then peace; ...), and a deed walled for that shape is not taken again.
  CANDIDATE  the difference supplies it: among those it has met, the one whose own field holds a surplus where it
             lacks (the deepest first), who trusts it, and whose own residual the treaty drains too - both are
             served or nothing is made; war only on a weaker holder of what it lacks (arms measured, not dialled).
  SEAL       next year, what the deed delivered on the entry it named seals a crystal (that shape, that deed, that
             much) or a wall. Thinking changes the thinker.
  HEARING    at a first meeting each hears what the other tells of itself as far as it understands it, and one of
             the other's crystals, reduced against its own: understood, or learned in part.
  CONDUCT    two-sided books per axis (compassion, bond, integrity, morality; syntropic and entropic): a treaty kept
             or broken, a war made, written by both; a sovereign that has broken more than it kept is not treated with.

CONTINUITY. A sovereign reigns a generation of its people (fertility.generation_of); its successor takes its seat,
its crystals and its books - a chronicle inherited, never edited. A polity that breaks away is born with its
parent's crystals and its own books; a polity that ends ends its line (an epitaph in the annals). A seated player's
sovereign carries the same record.

ABOVE IT. A realm's steward (stewardship.py) binds it: no war is made across a steward's ruling, and a war it rules
down ends. Treaties are the sovereigns' own; a steward's ruling is the realm's.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import mindcore as mc

BOOKS = ("food", "room", "security", "wealth", "standing")     # the order needs are met: the first in deficit leads
SELF = "self"
TREATIES = ("trade", "defense", "peace", "war")


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
           "mind": mc.inherit(parent["mind"]) if parent and parent.get("mind") else mc.new_mind(),
           "books": {}, "heard": {}}
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
    """The peoples that have struck its people within a generation of its own (the ledger, its people's index)."""
    from xylarium.kernel import history, spheres
    since = kernel.cycle_count - int(100 * spheres.generation(kernel, rec["people"]))
    out = []
    for e in history.of_people(kernel, rec["people"]):
        if e.get("kind") in HURTS and e.get("cycle", 0) >= since:
            for a in e.get("actors", []):
                if a != rec["people"] and a not in out and not str(a).startswith("captain:"):
                    out.append(a)
    return out


def field(kernel: Any, rec: Dict[str, Any]) -> Dict[str, Fraction]:
    """Its dominion as a signed field: each book's need less what it has (positive: a deficit), exactly, in its own
    units - before any treaty is drained from it."""
    return {book: v for (_, book), v in _measure(kernel, rec).items()} | \
        {b: Fraction(0) for b in BOOKS if (SELF, b) not in _measure(kernel, rec)}


def _measure(kernel: Any, rec: Dict[str, Any]) -> mc.Chain:
    from xylarium.kernel import biosphere, reputation, staples, strategy, sustenance
    from xylarium.kernel import cache
    key = f"{rec['id']}:{kernel.cycle_count}"

    def build() -> mc.Chain:
        realm = _polities(kernel).get(rec["realm"])
        worlds = _worlds(kernel, realm) if realm else []
        q = _quarter()
        need: List[Tuple[str, str, Any]] = []
        have: List[Tuple[str, str, Any]] = []
        for w in worlds:
            staple = staples.of(kernel, w)
            ss = mc.q(w.society.get("self_sufficiency", 1.0) or 1.0)
            lack = 1 - ss if ss < 1 else 0
            need.append((SELF, "food", mc.q(biosphere.consumption(w) * q) * lack))
            have.append((SELF, "food", staples.surplus(kernel, w, staple)))
            need.append((SELF, "room", w.population))
            have.append((SELF, "room", biosphere.carrying_capacity(kernel, w)))
            have.append((SELF, "security", sustenance._strength(w)))
            need.append((SELF, "wealth", (w.citadel_level + 1) * q * 100))
            have.append((SELF, "wealth", w.treasury))
        struck = set(attackers(kernel, rec))
        for oid in sorted(rec["heard"]):
            other = sovereigns(kernel).get(oid)
            if other is None or other.get("ended"):
                continue
            if other["people"] in struck or \
                    strategy.hostility(kernel, other["people"]) > strategy.hostility(kernel, rec["people"]):
                need.append((SELF, "security", sum(sustenance._strength(w) for w in _worlds_of(kernel, other))))
            r = reputation.read(kernel, other["people"], rec["people"])
            if r is not None:
                need.append((SELF, "standing", mc.q(max(0.0, -r))))
                have.append((SELF, "standing", mc.q(max(0.0, r))))
        return mc.residual(mc.measure(need), mc.measure(have))
    if not hasattr(kernel, "caches"):
        return build()
    return cache.memo(kernel, "polity_measure", key, build, max_age=1)


def _worlds_of(kernel: Any, rec: Dict[str, Any]) -> List[Any]:
    realm = _polities(kernel).get(rec["realm"])
    return _worlds(kernel, realm) if realm else []


def delivered(kernel: Any, rec: Dict[str, Any], fields: Dict[str, Dict[str, Fraction]]) -> mc.Chain:
    """What its treaties deliver, per book, exactly: a trade partner's surplus of what it lacks, an ally's arms,
    the arms a peace takes off those that strike it. (A war delivers nothing.)"""
    from xylarium.kernel import sustenance
    out: List[Tuple[str, str, Any]] = []
    for t in treaties_of(kernel, rec["id"]):
        oid = t["b"] if t["a"] == rec["id"] else t["a"]
        o = sovereigns(kernel).get(oid)
        if o is None or o.get("ended"):
            continue
        of = fields.get(oid) or field(kernel, o)
        if t["kind"] == "trade":
            for book in ("food", "wealth"):
                if of.get(book, 0) < 0:
                    out.append((SELF, book, -of[book]))
        elif t["kind"] in ("defense", "peace"):
            out.append((SELF, "security", sum(sustenance._strength(w) for w in _worlds_of(kernel, o))))
            if t["kind"] == "peace":
                out.append((SELF, "standing", 1))
    return mc.measure(out)


def chain(kernel: Any, rec: Dict[str, Any], fields: Dict[str, Dict[str, Fraction]]) -> mc.Chain:
    """Its residual: the field, less what its treaties deliver - the lesser captured, the rest carried."""
    f = mc.measure((SELF, b, v) for b, v in fields[rec["id"]].items())
    got = delivered(kernel, rec, fields)
    out: mc.Chain = {}
    for k, v in f.items():
        d = got.get(k, Fraction(0))
        left = v - min(v, d) if v > 0 else v
        if left:
            out[k] = left
    return out


def residual(kernel: Any, rec: Dict[str, Any], f: Optional[Dict[str, Fraction]] = None) -> List[str]:
    """The books still in deficit once its treaties are drained, in the order needs are met."""
    fields = {rec["id"]: f if f is not None else field(kernel, rec)}
    res = chain(kernel, rec, fields)
    return [b for b in BOOKS if res.get((SELF, b), 0) > 0]


# ---------------------------------------------------------------------- treaties and conduct
def _pair(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


def treaties_of(kernel: Any, sid: str) -> List[Dict[str, Any]]:
    return [t for t in stats(kernel)["treaties"].values() if sid in (t["a"], t["b"])]


def treaty(kernel: Any, a: str, b: str) -> Optional[Dict[str, Any]]:
    return stats(kernel)["treaties"].get(_pair(a, b))


CONDUCT_OF = {"trade": (("integrity", 1, 0), ("bond", 1, 0)), "defense": (("bond", 1, 0),),
              "peace": (("compassion", 1, 0),), "war": (("compassion", 0, 1), ("morality", 0, 1)),
              "broken": (("integrity", 0, 1),)}


def _conduct(kernel: Any, a: Dict[str, Any], b: Dict[str, Any], deed: str) -> None:
    """Both write what one did the other, on the axes the deed touches."""
    for axis, syn, ent in CONDUCT_OF.get(deed, ()):
        mc.record(a["books"], b["books"], a["id"], b["id"], axis, syntropic=syn, entropic=ent)


def trusts(o: Dict[str, Any], rec: Dict[str, Any]) -> bool:
    """Would `o` treat with `rec`? Unless what has passed between them shows more broken than kept (its integrity
    read as more entropic than syntropic) - or nothing has passed yet."""
    r = mc.reading(o["books"], rec["id"])["integrity"]
    return r is None or r >= Fraction(1, 2)


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
    if old is not None and old["kind"] in ("peace", "trade", "defense") and kind == "war":
        _conduct(kernel, a, b, "broken")                       # a treaty broken: written against the breaker
    t = {"a": a["id"], "b": b["id"], "kind": kind, "since": kernel.cycle_count, "by": a["id"], "why": why}
    stats(kernel)["treaties"][_pair(a["id"], b["id"])] = t
    _conduct(kernel, a, b, kind)
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
    """A first meeting: it hears what the other tells of itself, as far as it can understand it - and one of the
    other's crystals (the first it holds), reduced against its own."""
    from xylarium.kernel import alignment, contact, reputation
    understood = contact.intelligibility(kernel, rec["people"], other["people"])
    orealm = _polities(kernel).get(other["realm"])
    cap = kernel.get_planet(orealm["capital"]) if orealm else None
    civ = getattr(cap, "civilization", None) if cap is not None else None
    if civ is not None and rec["people"] != other["people"]:
        told = alignment.doctrine(civ)                         # what it tells of itself, heard as far as understood
        reputation.witness(kernel, rec["people"], other["people"], light=max(0.0, told) * understood,
                           dark=max(0.0, -told) * understood)
    rec["heard"][other["id"]] = round(float(understood), 4)
    mc.conduct(rec["books"], other["id"])
    theirs = mc.crystals(other["mind"])
    if theirs:
        key = sorted(theirs)[0]
        return mc.hear(rec["mind"], key, theirs[key], understood)
    return "unheard"


# ---------------------------------------------------------------------- the deed
VOCABULARY = {"food": ("trade", "war"), "room": ("peace", "war"), "security": ("defense", "peace"),
              "wealth": ("trade", "war"), "standing": ("peace",)}


def _mirror(kernel: Any, rec: Dict[str, Any], book: str, deed: str,
            fields: Dict[str, Dict[str, Fraction]]) -> Optional[Dict[str, Any]]:
    """The difference supplies the candidate: among those it has met, the one whose own field holds a surplus where
    it lacks (the deepest first), who trusts it, and whose own residual the treaty drains too (both are served)."""
    best = None
    for oid in sorted(rec["heard"]):
        o = sovereigns(kernel).get(oid)
        if o is None or o.get("ended") or oid not in fields or fields[oid].get(book, 0) >= 0 or not trusts(o, rec):
            continue
        theirs = chain(kernel, o, fields)
        served = [b for (_, b), v in theirs.items() if v > 0 and deed in VOCABULARY.get(b, ())]
        if not served and deed != "trade":
            continue
        if best is None or fields[oid][book] < fields[best["id"]][book]:
            best = o
    return best


def _weaker_holder(kernel: Any, rec: Dict[str, Any], book: str,
                   fields: Dict[str, Dict[str, Fraction]]) -> Optional[Dict[str, Any]]:
    """A sovereign it has met that holds what it lacks and whose arms are less than its own (measured)."""
    from xylarium.kernel import stewardship, sustenance
    mine = sum(sustenance._strength(w) for w in _worlds_of(kernel, rec))
    best = None
    for oid in sorted(rec["heard"]):
        o = sovereigns(kernel).get(oid)
        if o is None or o.get("ended") or oid not in fields or fields[oid].get(book, 0) >= 0:
            continue
        if o["people"] == rec["people"] and _kin_cooperate(kernel, rec):
            continue                                           # a people that leans to the Light does not prey on its own
        if stewardship.binds(kernel, rec["people"], o["people"]) or stewardship.binds(kernel, rec["people"], o["people"], "pact"):
            if book == "food":                                 # its people's hunger, barred: it goes up the chain
                stewardship.appeal(kernel, rec, o["people"])
            continue                                           # a steward's ruling stands between them
        theirs = sum(sustenance._strength(w) for w in _worlds_of(kernel, o))
        if theirs < mine and (best is None or fields[oid][book] < fields[best["id"]][book]):
            best = o
    return best


def _kin_cooperate(kernel: Any, rec: Dict[str, Any]) -> bool:
    """Kin sovereigns stand together as far as their people's character leans to the Light (its whole history)."""
    from xylarium.kernel import alignment
    realm = _polities(kernel).get(rec["realm"])
    cap = kernel.get_planet(realm["capital"]) if realm else None
    civ = getattr(cap, "civilization", None) if cap is not None else None
    return civ is not None and alignment.character(civ) > 0


def think(kernel: Any, rec: Dict[str, Any], fields: Dict[str, Dict[str, Fraction]]) -> Optional[str]:
    """One deed a year, by the mind core: last year's deed is sealed (crystal or wall); the residual (the field less
    what treaties deliver) leads with its first deficit; a crystal recalls its deed, a new shape takes its book's
    vocabulary in order, walls skipped; the difference supplies the partner. A seated player's sovereign is read but
    not thought for: its player chooses."""
    res = chain(kernel, rec, fields)
    mc.seal(rec["mind"], res)
    entry = mc.lead(res, BOOKS)
    if rec.get("player") or entry is None:
        return None
    book, owed = entry[1], res[entry]
    key = mc.shape(entry, owed)
    barred = mc.walls(rec["mind"], key)
    recalled = mc.recall(rec["mind"], entry, owed)
    order = ([recalled] if recalled else []) + [d for d in VOCABULARY[book] if d != recalled]
    for deed in order:
        if deed in barred:
            continue
        done = _deed(kernel, rec, book, deed, fields)
        if done is not None:
            mc.intend(rec["mind"], entry, owed, done)
            return done
    return None


def _deed(kernel: Any, rec: Dict[str, Any], book: str, deed: str,
          fields: Dict[str, Dict[str, Fraction]]) -> Optional[str]:
    if deed == "war":
        prey = _weaker_holder(kernel, rec, book, fields)
        if prey is None:
            return None
        t = treaty(kernel, rec["id"], prey["id"])
        if t is None or t["kind"] != "war":
            _make(kernel, rec, prey, "war", f"its {book} in deficit and no one to answer it: it takes it")
            _wage(kernel, rec, prey)
        return "war"
    if book == "security":
        return _secure(kernel, rec, deed, fields)
    partner = _mirror(kernel, rec, book, deed, fields)
    if partner is None:
        return None
    t = treaty(kernel, rec["id"], partner["id"])
    if t is None or t["kind"] != deed:
        _make(kernel, rec, partner, deed, f"its {book} in deficit, the other's in surplus: both are served")
    return deed


def _secure(kernel: Any, rec: Dict[str, Any], deed: str, fields: Dict[str, Dict[str, Fraction]]) -> Optional[str]:
    """Its security leads: defense beside one struck by the same hand (both served), or peace with the one that
    strikes it, if peace serves that one too (its own standing or security in deficit) and it trusts it."""
    struck_me = set(attackers(kernel, rec))
    for oid in sorted(rec["heard"]):
        o = sovereigns(kernel).get(oid)
        if o is None or o.get("ended") or oid not in fields or not trusts(o, rec):
            continue
        theirs = residual(kernel, o, fields[oid])
        if deed == "defense" and o["people"] not in struck_me:
            shared = struck_me & set(attackers(kernel, o))
            if shared and "security" in theirs:
                t = treaty(kernel, rec["id"], oid)
                if t is None or t["kind"] != "defense":
                    _make(kernel, rec, o, "defense", f"struck by the same hand ({sorted(shared)[0].split(':', 1)[-1]})")
                return "defense"
        if deed == "peace" and o["people"] in struck_me and ("standing" in theirs or "security" in theirs):
            t = treaty(kernel, rec["id"], oid)
            if t is None or t["kind"] != "peace":
                _make(kernel, rec, o, "peace", "the struck and the striker: peace serves them both")
            return "peace"
    return None


def _wage(kernel: Any, rec: Dict[str, Any], prey: Dict[str, Any]) -> None:
    """War is fought by the laws that fight it: the aggressor's capital raises its levy and raids."""
    from xylarium.kernel import society, sustenance
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
    fields = {s["id"]: field(kernel, s) for s in live}         # each read once, exactly
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
