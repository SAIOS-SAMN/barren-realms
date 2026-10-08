"""
Xylarium ascendance: whether a people that has come to the stars inside an established realm may go among them - the
stewards' ruling.

Outside any realm, a people that crosses simply goes out: the frontier has no one to ask. Inside one - its home in a
system another's network already holds - it PETITIONS: the steward of that realm reads it, every term of its own,
and rules. The reading is a set of BOOKS, each a PAIR (Concordance 6.3): a syntropic ledger against an entropic one,
from the candidate's own deeds, read whole and never collapsed to one number. A book is IN DEFICIT where its entropic
side exceeds its syntropic side, in its own unit; beside it, as a lens, how many of the realm's own peoples (its
keeper alone where it has no others) are in deficit in the same book. No threshold is declared; a book never gates.

  SUFFICIENCY  lives its worlds feed (its numbers up to what its worlds carry) against lives past what they carry
  RESTRAINT    the share of the many's product its many keep against the share its few take (rent)
  ORDER        lives and works made against lives and works destroyed, over its whole history (alignment.causes)
  SELF         its self-forecasts that held (beat the naive guess) against those that failed (introspect)
  HISTORY      how much of its records the deed ledger bears out against how much it contradicts (memory.truth) -
               or, where it kept no records the engine saw, what its best medium keeps of a generation against what
               it loses
  MINDS        the means to make minds (transfer, cyber, robotics) it holds within its self-knowledge against beyond it
               (each split by its self-forecasts held against failed)
  MONEY        value its money and the realm's reserves keep against value debased (in the exchange's unit)
  COOPERATION  treaties kept against treaties broken (its sovereigns' conduct: integrity)

The five deed books (deedbooks.py) are read beside them, cited, never gating. The VERDICT is the steward's own choice
(decide.choose), made only where a mind holds the steward's seat (Concordance 3.8: an envoy, or the progenitor line
that stewards the people): it reads the books in need order and, in each, weighs holding the people at home (worth
its entropic side, at the cost of its syntropic side) against letting it go (the reverse) - worth against cost within
one book, never one book against another. Where no mind holds the seat there is no ruling: the petition waits, unread
- and an unread petition (pending) carries no restriction: the people goes free, as on the frontier. Only a seated
steward's cited ruling holds a people at home.
A ruling cites the books it rests on, by name and pair, and is a deed on the steward's own books (6.3).

ASCEND: its network grows, it may bond and trade. QUARANTINE: its ships go no further than its own system, its
network does not grow, and no one may make war on it (the steward shields the young). It makes no OPEN CONTACT: no
new meeting with any other people, no treaty, no trade beyond its own kin - whatever reaches it reaches it covertly
(covert.py: exploiters of its resources, dark hands that would keep it down, smugglers - and the steward's
counter-watch). Where a book in deficit makes its works a danger to the realm's order - minds it cannot read (MINDS:
transfer, cyber, robotics), a history of destroying (ORDER: the atom, cyber) - the steward INTERDICTS them: found, but
stopped (technology.has reads them as absent) until it has ascended. The steward reads it again every term and rules
again: a people earns its way out book by book, but only a steward's ruling lets it out. A player who keeps the realm
rules for it (command.py).

CO-ASCENSION. A people that rises on a world others already hold - natives reaching their First Flight beside
colonists, a herd outgrowing its keepers, a second people of a shared system - ascends on its own books, never on its
hosts'. What the steward settles at the same reading is how they stand to each other (coascend): a host that held it
down is bound by a ceasefire; peoples whose doctrines can live together stand under a shared charter; otherwise each
keeps its own standing, bound by a pact.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import mindcore as mc
from xylarium.kernel.fx import hub as _hub

BOOKS = ("sufficiency", "restraint", "order", "self", "history", "minds", "money", "cooperation")
MIND_MAKING = ("transfer", "cyber", "robotics")
STOPS = {"minds": MIND_MAKING, "order": ("fission", "cyber")}   # the works a book in deficit makes a danger to others


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "ascendance")


def sanctuary(kernel: Any, sector_id: int) -> bool:
    """Has a steward kept this system for the minds that will wake there? Settling a world before its mind wakes is
    allowed unless a steward forbids it (settling.py)."""
    if kernel is None or "ascendance" not in getattr(kernel, "state", {}):
        return False
    return int(sector_id) in (stats(kernel).get("sanctuaries") or {})


def keep_sanctuary(kernel: Any, sector_id: int, by: str) -> None:
    """A steward forbids settling a system before the minds forecast there wake."""
    from xylarium.kernel import history
    stats(kernel).setdefault("sanctuaries", {})[int(sector_id)] = {"by": by, "cycle": kernel.cycle_count}
    history.event(kernel, "SANCTUARY", f"A sanctuary is kept at system {sector_id}", actors=[by], sector_id=sector_id,
                  cause="its steward forbids settling it before the minds that will wake there")


# ---------------------------------------------------------------------- the books (pairs)
def _home(kernel: Any, who: str) -> Optional[Any]:
    from xylarium.kernel import spheres
    return spheres._home(kernel, who)


def _pair(s: Any, e: Any) -> Dict[str, Any]:
    s, e = mc.q(s), mc.q(e)
    return {"syntropic": str(s), "entropic": str(e), "deficit": bool(e > s)}


def _forecasts(kernel: Any, who: str) -> Tuple[Fraction, Fraction]:
    """Its self-forecasts that held against those that failed (introspect scores one a year)."""
    from xylarium.kernel import introspect
    if "introspect" not in getattr(kernel, "state", {}):
        return Fraction(0), Fraction(0)
    rec = introspect.stats(kernel)["peoples"].get(who) or {}
    return Fraction(int(rec.get("held", 0))), Fraction(int(rec.get("failed", 0)))


def pairs(kernel: Any, who: str) -> Dict[str, Tuple[Fraction, Fraction]]:
    """A people's eight books, each (syntropic, entropic) in its own unit."""
    from xylarium.kernel import alignment, memory, rent, relations, syntropy, technology, transit
    home = _home(kernel, who)
    if home is None:
        return {}
    worlds = relations._peoples(kernel).get(who) or [home]
    out: Dict[str, Tuple[Fraction, Fraction]] = {}
    idx = syntropy.index(kernel, who, worlds)
    n, k = Fraction(int(idx["N"])), Fraction(int(idx["K"]))
    out["sufficiency"] = (min(n, k), max(Fraction(0), n - k))
    try:
        taken = mc.q(max(0.0, min(1.0, rent.of(home))))
    except Exception:
        taken = Fraction(0)
    out["restraint"] = (1 - taken, taken)
    civ = getattr(home, "civilization", None)
    made = destroyed = Fraction(0)
    if civ is not None:
        for v in alignment.causes(civ).values():
            made += mc.q(v["light"])
            destroyed += mc.q(v["dark"])
    out["order"] = (made, destroyed)
    held, failed = _forecasts(kernel, who)
    out["self"] = (held, failed)
    recs = memory.records(kernel, who) if "memory" in kernel.state else []
    if recs:
        true = sum((mc.q(memory.truth(r)) for r in recs), Fraction(0))
        out["history"] = (true, len(recs) - true)
    else:                         # no record is no evidence of a false memory: what its best medium keeps of a generation
        keep = mc.q(memory.character_keep(kernel, who, home))
        out["history"] = (keep, 1 - keep)
    caps = sum(1 for cap in MIND_MAKING if technology.found(kernel, who, cap))
    out["minds"] = (caps * held / (held + failed), caps * failed / (held + failed)) if held + failed \
        else (Fraction(0), Fraction(caps))
    kept, debased = _money(kernel, home.currency)
    for c in transit.reserves(kernel):                  # the realm's reserve: its debasement is every candidate's
        if c != home.currency:
            rk, rd = _money(kernel, c)
            kept, debased = kept + rk, debased + rd
    out["money"] = (kept, debased)
    out["cooperation"] = _treaties(kernel, who)
    return out


def _money(kernel: Any, cur: str) -> Tuple[Fraction, Fraction]:
    """The value a money keeps against the value its debasement has taken, in the exchange's unit (regimes)."""
    from xylarium.kernel import ledger, regimes
    if "regimes" not in kernel.state:
        return Fraction(0), Fraction(0)
    debased = max(Fraction(0), Fraction(regimes.stats(kernel).get("debased_sol", {}).get(cur, 0)))
    total = float((ledger.money_supply(kernel).get(cur) or {}).get("total", 0.0))
    held = mc.q(kernel.fx_market.to_sol_value(cur, total) if cur != _hub() and total else total)
    return max(Fraction(0), held - debased), debased


def _treaties(kernel: Any, who: str) -> Tuple[Fraction, Fraction]:
    """Treaties kept against broken, as its sovereigns' conduct with every other records it (integrity)."""
    from xylarium.kernel import polity
    s = e = Fraction(0)
    if "polity" not in kernel.state:
        return s, e
    for rec in polity.of_people(kernel, who):
        for other, c in (rec.get("books") or {}).items():
            s += Fraction(c["integrity"][0])
            e += Fraction(c["integrity"][1])
    return s, e


def books(kernel: Any, who: str, realm: str) -> Dict[str, Dict[str, Any]]:
    """The candidate's eight pairs, each with its lens: how many of the realm's own peoples (its keeper where it has
    no others) are in deficit in the same book."""
    from xylarium.kernel import spheres, stewardship
    mine = pairs(kernel, who)
    if not mine:
        return {}
    if realm.startswith("line:"):                          # a people a line stewards: read against the line's own
        peers, keeper = [], realm[len("line:"):]
    else:
        peers = [p for p in stewardship.peoples_of(kernel, realm) if p != who]
        keeper = spheres.presence(kernel, realm)
    if not peers and keeper and keeper != who:
        peers = [keeper]
    theirs = [t for t in (pairs(kernel, p) for p in peers) if t]
    out: Dict[str, Dict[str, Any]] = {}
    for b in BOOKS:
        out[b] = dict(_pair(*mine[b]), peers=len(theirs), peers_in_deficit=sum(1 for t in theirs if t[b][1] > t[b][0]))
    return out


# ---------------------------------------------------------------------- petitions and rulings
def petition(kernel: Any, who: str, realm: str) -> None:
    """A people crosses inside a realm another keeps: it asks to go among the stars, and waits on the steward."""
    from xylarium.kernel import history, stewardship
    st = stats(kernel)
    if who in st["of"]:
        return
    st["of"][who] = {"realm": realm, "ruling": "pending", "since": kernel.cycle_count, "ruled": None,
                     "rulings": 0, "mind": mc.new_mind(), "hosts": hosts(kernel, who)}
    history.event(kernel, "PETITION", f"The {who.split(':', 1)[-1]} ask to go among the stars of "
                  f"{stewardship.realm_name(realm)}", actors=[who],
                  cause="they have crossed inside a realm another keeps; its steward will read them")


def hosts(kernel: Any, who: str) -> List[str]:
    """Who a newcomer shares its home with: peoples holding worlds in its home system, the colonist owning its
    world, and any community keeping it as a herd - each of whom its ascension unsettles."""
    from xylarium.kernel import cohabit, sustenance
    home = _home(kernel, who)
    if home is None:
        return []
    out = set()
    for w in kernel.sectors[home.sector_id].planets:
        p = sustenance.people_of(w) if w.population > 0 else None
        if p and p != who:
            out.add(p)
    if home.owner_id:
        out.add(f"captain:{home.owner_id}")
    for c in cohabit.communities(home):
        if c.get("prey") == who or c.get("people"):
            out.add(c["people"])
    out.discard(who)
    return sorted(out)


def _suppressed(kernel: Any, who: str, host: str) -> bool:
    """Has a host held a newcomer down: set it back, raided, conquered or exploited it (the record)."""
    from xylarium.kernel import history
    kinds = ("RESET", "RAID", "WAR", "CONQUEST", "SUBJUGATION", "EXPLOITED", "STRIPPED")
    return any(e.get("kind") in kinds and (e.get("actors") or [None])[0] == host
               for e in history.of_people(kernel, who))


def coascend(kernel: Any, who: str, rec: Dict[str, Any], ascended: bool, logs: Optional[List[str]] = None) -> None:
    """The co-ascension hearing: one world, two peoples - each one's ascension is its own; what the steward settles is
    how they stand to each other. A host that held the newcomer down is bound by a ceasefire (protection); peoples
    whose doctrines can live together stand under a shared charter (a federation of the one world); else each has
    its own standing, bound by a pact - so a world's two peoples do not settle it by civil war."""
    from xylarium.config import POLICY_ORDER
    from xylarium.kernel import alignment, federation, history, spheres, stewardship
    out = {}
    for host in rec.get("hosts") or hosts(kernel, who):
        if host.startswith("captain:") and not stewardship.party(kernel, host).startswith("civ:"):
            kind = "protection" if _suppressed(kernel, who, host) else "standing"
        elif _suppressed(kernel, who, host):
            kind = "protection"
        elif not ascended:
            continue
        else:
            def card(p: str) -> str:
                h = spheres._home(kernel, p)
                c = getattr(h, "civilization", None) if h is not None else None
                return federation.preferred_card(alignment.doctrine(c) if c is not None else 0.0)
            far = abs(POLICY_ORDER.index(card(who)) - POLICY_ORDER.index(card(host)))
            kind = "shared" if far < 2 else "standing"
        a, b = stewardship.party(kernel, host), who
        sent = stewardship.mind(kernel, rec["realm"])
        by = sent["id"] if sent else "realm"
        if kind == "protection":
            stewardship._rule(kernel, rec["realm"], by, "ceasefire", a, b)
        elif kind == "standing":
            stewardship._rule(kernel, rec["realm"], by, "pact", a, b)
        else:
            spheres.stats(kernel)["bonds"]["|".join(sorted((a, b)))] = {
                "kind": "federation", "a": a, "b": b, "since": kernel.cycle_count, "sector": None, "charter": True}
        out[host] = kind
        history.event(kernel, "COASCENSION", f"The {who.split(':', 1)[-1]} and the {host.split(':', 1)[-1]}: "
                      f"{ {'protection': 'the newcomer shielded', 'shared': 'a shared charter', 'standing': 'each its own standing, bound by a pact'}[kind]}",
                      actors=[who] + ([a] if a.startswith("civ:") else []),
                      cause="one world, two peoples: the steward settles how they stand to each other")
        if logs is not None:
            logs.append(f"[ASCENDANCE] Co-ascension: the {who.split(':', 1)[-1]} and the {host.split(':', 1)[-1]} - {kind}.")
    rec["coascension"] = out


def ruling(kernel: Any, who: Optional[str]) -> Optional[str]:
    """'ascended', 'quarantine', 'pending' - or None for a people no realm has to rule on."""
    if not who or "ascendance" not in getattr(kernel, "state", {}):
        return None
    rec = stats(kernel)["of"].get(who)
    return rec["ruling"] if rec else None


def free(kernel: Any, who: Optional[str]) -> bool:
    """May this people go among the stars: anything but a seated steward's quarantine - a petition not yet read
    (pending) carries no restriction, as on the frontier."""
    return ruling(kernel, who) != "quarantine"


def isolated(kernel: Any, a: Optional[str], b: Optional[str]) -> bool:
    """No open contact between two peoples: either is held at home by a steward's ruling - kin excepted."""
    if not a or not b or a == b:
        return False
    return any(ruling(kernel, x) == "quarantine" for x in (a, b))


def stopped(kernel: Any, who: Optional[str]) -> List[str]:
    """The works a steward has interdicted for this people: found, but stopped."""
    if not who or "ascendance" not in getattr(kernel, "state", {}):
        return []
    rec = stats(kernel)["of"].get(who)
    return list(rec.get("stopped") or []) if rec else []


def _interdict(kernel: Any, who: str, rec: Dict[str, Any], logs: Optional[List[str]]) -> None:
    """Quarantined: the works its books in deficit make a danger are stopped; ascended: all are free again."""
    from xylarium.kernel import history, technology
    stop: List[str] = []
    if rec["ruling"] == "quarantine":
        for book, caps in STOPS.items():
            if ((rec.get("books") or {}).get(book) or {}).get("deficit"):
                stop += [c for c in caps if technology.found(kernel, who, c) and c not in stop]
    new = sorted(set(stop) - set(rec.get("stopped") or []))
    rec["stopped"] = sorted(stop)
    if new:
        history.event(kernel, "INTERDICTED", f"The {who.split(':', 1)[-1]}'s {', '.join(new)} stopped by their steward",
                      actors=[who], cause="works its own books make a danger to the realm's order")
        if logs is not None:
            logs.append(f"[ASCENDANCE] The {who.split(':', 1)[-1]}: {', '.join(new)} interdicted.")


def confined(kernel: Any, who: Optional[str], a: int, b: int) -> bool:
    """Is a passage from a to b barred to this people's ships: quarantined, and leaving its own system."""
    if ruling(kernel, who) != "quarantine":
        return False
    home = _home(kernel, who)
    return home is None or b != home.sector_id


def _line(realm: str) -> Optional[str]:
    return realm[len("line:"):] if realm.startswith("line:") else None


def seat(kernel: Any, realm: str) -> Optional[Dict[str, Any]]:
    """The mind holding a realm's steward seat (Concordance 3.8): the progenitor line that stewards it, or its
    steward of record (an envoy, a player where one keeps it) - None where no mind holds it."""
    from xylarium.kernel import board, relations, stewardship
    line = _line(realm)
    if line is not None:
        held = board.progenitors(kernel).get(line)
        if held is not None:
            return held
        # a people that is no ancient keeps its own line (stewardship.envoys: "sent by the X themselves"): its
        # COUNCIL's seat rules for it - a people acts through its council (Concordance 3.8), the AI holding the
        # seat where no player does; a people no longer living holds no seat
        if relations._peoples(kernel).get(line):
            council = stats(kernel).setdefault("councils", {})
            return council.setdefault(line, {"id": f"council:{line}", "name": f"the {line.split(':', 1)[-1]} council",
                                             "sender": line})
        return None
    return stewardship.mind(kernel, realm)


def _steward_mind(kernel: Any, realm: str, held: Dict[str, Any]) -> Dict[str, Any]:
    """The steward's own judgement: its sender's people's mind (a line's: its own people's), as a seat of its own."""
    from xylarium.kernel import decide
    sender = _line(realm) or held.get("sender") or ""
    home = _home(kernel, sender) if sender.startswith("civ:") else None
    m = decide.mind_of_planet(kernel, home) if home is not None else decide.mind(kernel, None)
    return dict(m, holder=f"steward:{held.get('id') or held.get('name') or realm}", posture=None)


def judge(kernel: Any, who: str, rec: Dict[str, Any], held: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """The steward reads the books in need order and, in each, weighs holding the people at home (worth its entropic
    side, at the cost of its syntropic side) against letting it go (the reverse): the first book in which it chooses
    to hold it leads; none, and it ascends."""
    from xylarium.kernel import decide
    m = _steward_mind(kernel, rec["realm"], held)
    for b in BOOKS:
        p = (rec.get("books") or {}).get(b)
        if not p:
            continue
        s_, e_ = float(Fraction(p["syntropic"])), float(Fraction(p["entropic"]))
        pick = decide.choose(kernel, [decide.option("quarantine", s_, e_, aim=b), decide.option("ascend", e_, s_, aim=b)],
                             m, "ascendance", who, b)
        if pick is not None and pick["name"] == "quarantine":
            return "quarantine", b
    return "ascended", None


def rule(kernel: Any, who: str, verdict: str, by: str, logs: Optional[List[str]] = None,
         cites: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """A steward's ruling on a petition: 'ascended' or 'quarantine' - citing the books it rests on (by name and pair;
    every book read, where none is named) and kept as a deed on the steward's own books."""
    from xylarium.kernel import history, stewardship
    rec = stats(kernel)["of"].get(who)
    if verdict == "chartered":
        verdict = "ascended"                                # the word it was first given
    if rec is None or verdict not in ("ascended", "quarantine"):
        return {"ok": False, "why": "no such petition, or no such ruling"}
    old = rec["ruling"]
    rec.update(ruling=verdict, ruled=kernel.cycle_count, by=by)
    if cites is None:
        cites = dict(rec.get("books") or {})
    rec.setdefault("deeds", {})["ruling"] = {"verdict": verdict, "by": by, "cycle": kernel.cycle_count,
                                             "cites": cites}
    held = seat(kernel, rec["realm"])
    if held is not None:                                    # a ruling is a deed on the steward's own books
        d = held.setdefault("deeds", {"ascended": 0, "quarantine": 0})
        d[verdict] = d.get(verdict, 0) + 1
        d["last"] = {"people": who, "verdict": verdict, "cycle": kernel.cycle_count, "cites": sorted(cites)}
    if verdict == "ascended" and old != "ascended":
        from xylarium.kernel import endowments
        got = endowments.release(kernel, who)                 # its steward's escrow, at its home
        if got and logs is not None:
            logs.append(got)
    rec["rulings"] += 1
    _interdict(kernel, who, rec, logs)
    name, realm = who.split(":", 1)[-1], stewardship.realm_name(rec["realm"])
    if verdict != old:
        history.event(kernel, "ASCENDED" if verdict == "ascended" else "QUARANTINED",
                      f"The {name} {'ascend among the stars of' if verdict == 'ascended' else 'are held at home by'}"
                      f" {realm}", actors=[who],
                      cause=f"the steward read their books and held them on {rec.get('lead') or ', '.join(cites)}"
                      if verdict == "quarantine" else "the steward read their books and let them go",
                      data={"cites": cites, "by": by})
        if logs is not None:
            logs.append(f"[ASCENDANCE] The {name}: {verdict} by {realm}.")
    return {"ok": True, "ruling": verdict}


def _due(kernel: Any, rec: Dict[str, Any]) -> bool:
    """A petition is read on arrival, then again every term of the realm's steward."""
    from xylarium.kernel import stewardship
    if rec["realm"].startswith("line:"):                  # a line reads its peoples every one of its generations
        from xylarium.kernel import clocks, spheres
        span = clocks.lived_span(kernel, spheres.generation(kernel, rec["realm"][len("line:"):]))
        return rec["ruled"] is None or kernel.cycle_count - rec["ruled"] >= span
    return rec["ruled"] is None or kernel.cycle_count - rec["ruled"] >= stewardship.span_cycles(kernel, rec["realm"])


def season(kernel: Any) -> List[str]:
    """Once a year: each petition due is read by the mind holding its realm's steward seat, who rules on it by its
    own choice, citing the books - or by a player who keeps the realm. No mind in the seat: no ruling, no reading."""
    from xylarium.kernel import board, deedbooks, polity, stewardship
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    logs: List[str] = []
    st = stats(kernel)
    for who, rec in sorted(st["of"].items()):
        if not _due(kernel, rec) or _home(kernel, who) is None:
            continue
        line = _line(rec["realm"])
        player = line is None and bool(stewardship.steward_of(kernel, rec["realm"]))
        held = seat(kernel, rec["realm"])
        if held is None and not player:
            continue                                       # no mind holds the seat: the petition waits, unread
        rec["books"] = books(kernel, who, rec["realm"])
        peers = [p for p in stewardship.peoples_of(kernel, rec["realm"]) if p != who] if line is None else []
        rec["deeds"] = deedbooks.read(kernel, who, peers)  # the five deed books, read whole beside the eight
        if player or (held or {}).get("standing") == "by hand":
            rec["ruled"] = kernel.cycle_count              # a player keeps the realm (or rules its line by hand)
            continue
        # a player's line is ruled by its standing policy while its player is away: by its steward's own reading,
        # unless it chose to rule by hand (command: the progenitor's seat plays asynchronously)
        verdict, lead = judge(kernel, who, rec, held)
        rec["lead"] = lead
        cites = {lead: rec["books"][lead]} if lead is not None else dict(rec["books"])
        if line is not None:
            by = held.get("name") or f"the {line.split(':', 1)[-1]}"
            ledger = board.stats(kernel).setdefault("stewarded", {}).setdefault(line, {"ascended": 0, "quarantine": 0})
            ledger[verdict] += 1                               # each line's record: how the peoples it stewards were ruled
        else:
            by = held["name"]
        was = rec["ruling"]
        rule(kernel, who, verdict, by, logs, cites=cites)
        if (verdict != was or rec.get("coascension") is None) and (rec.get("hosts") or hosts(kernel, who)):
            coascend(kernel, who, rec, verdict == "ascended", logs)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    out: Dict[str, int] = {}
    for rec in stats(kernel)["of"].values():
        out[rec["ruling"]] = out.get(rec["ruling"], 0) + 1
    return {"rulings": out}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="ascendance",
    state=lambda: {"of": {}},
    season=season,
    summary=summary,
))
