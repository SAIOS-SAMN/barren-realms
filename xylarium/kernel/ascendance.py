"""
Xylarium ascendance: whether a people that has come to the stars inside an established realm may go among them - the
stewards' ruling.

Outside any realm, a people that crosses simply goes out: the frontier has no one to ask. Inside one - its home in a
system another's network already holds - it PETITIONS: the steward of that realm reads it, every term of its own,
and rules. The reading is a set of BOOKS, each the candidate's own measure against the same measure across the realm's
own peoples (the worst it already holds - a candidate need be no worse than those already among it; the realm's
keeper alone where it has no others), signed - a deficit where it falls short of the realm it would join. Need orders: the first book in deficit leads; no book is weighed against another.

  SUFFICIENCY  what it takes of its worlds against what they regrow: its numbers past what its worlds can carry
               (syntropy: crowding above one). A scarcity-only, extractive people overdraws its own ground.
  RESTRAINT    what its few take of its many against what the many will bear (rent over rent.bearable)
  ORDER        its whole history: order destroyed against made (alignment.character)
  SELF         whether it can read its own mind (introspect: self-knowledge)
  HISTORY      whether it remembers its own world truly (memory: the truth of what it keeps - or, where it kept no
               records the engine saw, how much of its past its best medium holds a generation)
  MINDS        the means to make minds (transfer, cyber, robotics) held beyond its self-knowledge: a people that would
               set loose minds it cannot read - or reads its own kind as a stage to be discarded - is not ready
  MONEY        the debasement of its own money - and of the realm's reserve, which tightens every reading: a realm
               whose reserve is inflating takes on no new weight lightly
  COOPERATION  the treaties it has broken against those it has kept (its sovereigns' conduct: integrity)

All books in balance: the steward lets it ASCEND - its network grows, it may bond and trade. Any in deficit:
QUARANTINE - its ships go no further than its own system, its network does not grow, and no one may make war on it
(the steward shields the young). It makes no OPEN CONTACT: no new meeting with any other people, no treaty, no trade
beyond its own kin - whatever reaches it reaches it covertly (covert.py: exploiters of its resources, dark hands that
would keep it down, smugglers - and the steward's counter-watch). Where a book in deficit makes its works a danger to
the realm's order - minds it cannot read (MINDS: transfer, cyber, robotics), a history of destroying (ORDER: the atom,
cyber) - the steward INTERDICTS them: found, but stopped (technology.has reads them as absent) until it has ascended. The steward reads it again every term and rules again: a people earns its way out
book by book, but only a steward's ruling lets it out. A player who keeps the realm rules for it (command.py).

CO-ASCENSION. A people that rises on a world others already hold - natives reaching their First Flight beside
colonists, a herd outgrowing its keepers, a second people of a shared system - ascends on its own books, never on its
hosts'. What the steward settles at the same reading is how they stand to each other (coascend): a host that held it
down is bound by a ceasefire; peoples whose doctrines can live together stand under a shared charter; otherwise each
keeps its own standing, bound by a pact.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional

from xylarium.kernel import mindcore as mc

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


# ---------------------------------------------------------------------- the measures (higher is worse)
def _home(kernel: Any, who: str) -> Optional[Any]:
    from xylarium.kernel import spheres
    return spheres._home(kernel, who)


def measures(kernel: Any, who: str) -> Dict[str, float]:
    """A people's reading in every book, each a shortfall (higher is worse, 0 the best)."""
    from xylarium.kernel import alignment, introspect, memory, rent, relations, syntropy, technology
    home = _home(kernel, who)
    if home is None:
        return {}
    worlds = relations._peoples(kernel).get(who) or [home]
    out: Dict[str, float] = {}
    # taking more of its worlds than they regrow: its numbers past what they can carry (at what they carry, nothing)
    out["sufficiency"] = max(0.0, float(syntropy.index(kernel, who, worlds)["crowding"]) - 1.0)
    try:
        out["restraint"] = max(0.0, rent.of(home) - rent.bearable(kernel, home))
    except Exception:
        out["restraint"] = 0.0
    civ = getattr(home, "civilization", None)
    out["order"] = (1.0 - alignment.character(civ)) / 2.0 if civ is not None else 0.5
    skill = introspect.self_knowledge(kernel, who) if introspect.introspective(kernel, who) else 0.0
    out["self"] = 1.0 - max(0.0, min(1.0, skill))
    # what it remembers truly: its records' truth - or, a people the annals carried with no records kept in the
    # engine, how much of its past its best medium keeps a generation (memory.character_keep): no record is no
    # evidence of a false memory
    recs = memory.records(kernel, who) if "memory" in kernel.state else []
    truth = sum(memory.truth(r) for r in recs) / len(recs) if recs else memory.character_keep(kernel, who, home)
    out["history"] = 1.0 - truth
    held = sum(1 for cap in MIND_MAKING if technology.found(kernel, who, cap))
    out["minds"] = held * out["self"]
    out["money"] = _debasement(kernel, home.currency)
    out["cooperation"] = _broken(kernel, who)
    return out


def _debasement(kernel: Any, cur: str) -> float:
    """The share of a money's supply its debasement has taken (regimes: debased value over the supply held)."""
    from xylarium.kernel import ledger, regimes
    if "regimes" not in kernel.state:
        return 0.0
    debased = float(regimes.stats(kernel).get("debased_sol", {}).get(cur, 0.0))
    total = float((ledger.money_supply(kernel).get(cur) or {}).get("total", 0.0))
    held = kernel.fx_market.to_sol_value(cur, total) if cur != "SOL" and total else total
    return max(0.0, debased / held) if held > 0 else 0.0


def _broken(kernel: Any, who: str) -> float:
    """Treaties broken against kept, as its sovereigns' conduct with every other records it (integrity's dark share)."""
    from xylarium.kernel import polity
    if "polity" not in kernel.state:
        return 0.0
    s = e = Fraction(0)
    for rec in polity.of_people(kernel, who):
        for other, c in (rec.get("books") or {}).items():
            s += Fraction(c["integrity"][0])
            e += Fraction(c["integrity"][1])
    return float(e / (s + e)) if s + e else 0.0


def books(kernel: Any, who: str, realm: str) -> mc.Chain:
    """The candidate's books against the realm's own peoples: signed, a deficit where it falls short of them. The
    realm's reserve debasement tightens the money book for every candidate."""
    from xylarium.kernel import spheres, stewardship, transit
    mine = measures(kernel, who)
    if not mine:
        return {}
    if realm.startswith("line:"):                          # a people a line stewards: read against the line's own
        peers, keeper = [], realm[len("line:"):]
    else:
        peers = [p for p in stewardship.peoples_of(kernel, realm) if p != who]
        keeper = spheres.presence(kernel, realm)
    if not peers and keeper and keeper != who:
        peers = [keeper]
    theirs = [measures(kernel, p) for p in peers]
    theirs = [t for t in theirs if t]
    reserve_strain = max((_debasement(kernel, c) for c in transit.reserves(kernel)), default=0.0)
    out: mc.Chain = {}
    for b in BOOKS:
        bar = max(t[b] for t in theirs) if theirs else 0.0     # no worse than the worst it already holds
        v = mine[b] - bar + (reserve_strain if b == "money" else 0.0)
        if v:
            out[(who, b)] = mc.q(v)
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
    """May this people go among the stars: no realm to ask, or ascended."""
    return ruling(kernel, who) in (None, "ascended")


def isolated(kernel: Any, a: Optional[str], b: Optional[str]) -> bool:
    """No open contact between two peoples: either is held at home (quarantined or still pending) - kin excepted."""
    if not a or not b or a == b:
        return False
    return any(ruling(kernel, x) in ("quarantine", "pending") for x in (a, b))


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
            if Fraction((rec.get("books") or {}).get(book, "0")) > 0:
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
    if ruling(kernel, who) not in ("quarantine", "pending"):
        return False
    home = _home(kernel, who)
    return home is None or b != home.sector_id


def rule(kernel: Any, who: str, verdict: str, by: str, logs: Optional[List[str]] = None) -> Dict[str, Any]:
    """A steward's ruling on a petition: 'ascended' or 'quarantine'."""
    from xylarium.kernel import history, stewardship
    rec = stats(kernel)["of"].get(who)
    if verdict == "chartered":
        verdict = "ascended"                                # the word it was first given
    if rec is None or verdict not in ("ascended", "quarantine"):
        return {"ok": False, "why": "no such petition, or no such ruling"}
    old = rec["ruling"]
    rec.update(ruling=verdict, ruled=kernel.cycle_count, by=by)
    rec["rulings"] += 1
    _interdict(kernel, who, rec, logs)
    name, realm = who.split(":", 1)[-1], stewardship.realm_name(rec["realm"])
    if verdict != old:
        history.event(kernel, "ASCENDED" if verdict == "ascended" else "QUARANTINED",
                      f"The {name} {'ascend among the stars of' if verdict == 'ascended' else 'are held at home by'}"
                      f" {realm}", actors=[who],
                      cause=f"the steward read their books: {rec.get('lead') or 'all in balance'}"
                      if verdict == "quarantine" else "the steward read their books and found them in balance",
                      data={"books": rec.get("books"), "by": by})
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
    """Once a year: each petition due is read by its realm's steward, who rules on it by its books - unless a player
    keeps the realm, who rules for it."""
    from xylarium.kernel import board, polity, stewardship
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    logs: List[str] = []
    st = stats(kernel)
    for who, rec in sorted(st["of"].items()):
        if not _due(kernel, rec) or _home(kernel, who) is None:
            continue
        res = books(kernel, who, rec["realm"])
        mc.seal(rec["mind"], res)                          # what last term's ruling did, read
        lead = mc.lead(res, BOOKS)
        rec["books"] = {b: str(res.get((who, b), 0)) for b in BOOKS}
        rec["lead"] = lead[1] if lead else None
        line = rec["realm"][len("line:"):] if rec["realm"].startswith("line:") else None
        held_line = (board.progenitors(kernel).get(line) or {}) if line is not None else {}
        if (line is None and stewardship.steward_of(kernel, rec["realm"])) or held_line.get("standing") == "by hand":
            rec["ruled"] = kernel.cycle_count              # a player keeps the realm (or rules its line by hand)
            continue
        # a player's line is ruled by its standing policy while its player is away: by the books, unless it chose
        # to rule by hand (command: the progenitor's seat plays asynchronously)
        verdict = "ascended" if lead is None else "quarantine"
        if lead is not None:
            mc.intend(rec["mind"], lead, res[lead], "quarantine", "candidate")
        if line is not None:
            by = (board.progenitors(kernel).get(line) or {}).get("name") or f"the {line.split(':', 1)[-1]}"
            ledger = board.stats(kernel).setdefault("stewarded", {}).setdefault(line, {"ascended": 0, "quarantine": 0})
            ledger[verdict] += 1                               # each line's record: how the peoples it stewards were ruled
        else:
            sent = stewardship.mind(kernel, rec["realm"])
            by = sent["name"] if sent else "the realm"
        was = rec["ruling"]
        rule(kernel, who, verdict, by, logs)
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
