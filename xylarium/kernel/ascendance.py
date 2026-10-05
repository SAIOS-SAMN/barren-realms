"""
Xylarium ascendance: whether a people that has come to the stars inside an established realm may go among them - the
stewards' ruling.

Outside any realm, a people that crosses simply goes out: the frontier has no one to ask. Inside one - its home in a
system another's network already holds - it PETITIONS: the steward of that realm reads it, every term of its own,
and rules. The reading is a set of BOOKS, each the candidate's own measure against the same measure across the realm's
own peoples (the worst it already holds - a candidate need be no worse than those already among it; the realm's
keeper alone where it has no others), signed - a deficit where it falls short of the realm it would join. Need orders: the first book in deficit leads; no book is weighed against another.

  SUFFICIENCY  what it takes of its worlds against what they regrow: its numbers over what its worlds can carry
               (syntropy: crowding). A scarcity-only, extractive people overdraws its own ground.
  RESTRAINT    what its few take of its many against what the many will bear (rent over rent.bearable)
  ORDER        its whole history: order destroyed against made (alignment.character)
  SELF         whether it can read its own mind (introspect: self-knowledge)
  HISTORY      whether it remembers its own world truly (memory: the truth of what it keeps)
  MINDS        the means to make minds (transfer, cyber, robotics) held beyond its self-knowledge: a people that would
               set loose minds it cannot read - or reads its own kind as a stage to be discarded - is not ready
  MONEY        the debasement of its own money - and of the realm's reserve, which tightens every reading: a realm
               whose reserve is inflating takes on no new weight lightly
  COOPERATION  the treaties it has broken against those it has kept (its sovereigns' conduct: integrity)

All books in balance: the steward CHARTERS it - it ascends, its network grows, it may bond and trade. Any in deficit:
QUARANTINE - its ships go no further than its own system, its network does not grow, and no one may make war on it
(the steward shields the young). The steward reads it again every term and rules again: a people earns its way out
book by book, but only a steward's ruling lets it out. A player who keeps the realm rules for it (command.py).
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional

from xylarium.kernel import mindcore as mc

BOOKS = ("sufficiency", "restraint", "order", "self", "history", "minds", "money", "cooperation")
MIND_MAKING = ("transfer", "cyber", "robotics")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "ascendance")


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
    out["sufficiency"] = float(syntropy.index(kernel, who, worlds)["crowding"])
    try:
        out["restraint"] = max(0.0, rent.of(home) - rent.bearable(kernel, home))
    except Exception:
        out["restraint"] = 0.0
    civ = getattr(home, "civilization", None)
    out["order"] = (1.0 - alignment.character(civ)) / 2.0 if civ is not None else 0.5
    skill = introspect.self_knowledge(kernel, who) if introspect.introspective(kernel, who) else 0.0
    out["self"] = 1.0 - max(0.0, min(1.0, skill))
    recs = memory.records(kernel, who) if "memory" in kernel.state else []
    out["history"] = 1.0 - (sum(memory.truth(r) for r in recs) / len(recs) if recs else 0.0)
    held = sum(1 for cap in MIND_MAKING if technology.has(kernel, who, cap))
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
                     "rulings": 0, "mind": mc.new_mind()}
    history.event(kernel, "PETITION", f"The {who.split(':', 1)[-1]} ask to go among the stars of "
                  f"{stewardship.realm_name(realm)}", actors=[who],
                  cause="they have crossed inside a realm another keeps; its steward will read them")


def ruling(kernel: Any, who: Optional[str]) -> Optional[str]:
    """'chartered', 'quarantine', 'pending' - or None for a people no realm has to rule on."""
    if not who or "ascendance" not in getattr(kernel, "state", {}):
        return None
    rec = stats(kernel)["of"].get(who)
    return rec["ruling"] if rec else None


def free(kernel: Any, who: Optional[str]) -> bool:
    """May this people go among the stars: no realm to ask, or chartered."""
    return ruling(kernel, who) in (None, "chartered")


def confined(kernel: Any, who: Optional[str], a: int, b: int) -> bool:
    """Is a passage from a to b barred to this people's ships: quarantined, and leaving its own system."""
    if ruling(kernel, who) not in ("quarantine", "pending"):
        return False
    home = _home(kernel, who)
    return home is None or b != home.sector_id


def rule(kernel: Any, who: str, verdict: str, by: str, logs: Optional[List[str]] = None) -> Dict[str, Any]:
    """A steward's ruling on a petition: 'chartered' or 'quarantine'."""
    from xylarium.kernel import history, stewardship
    rec = stats(kernel)["of"].get(who)
    if rec is None or verdict not in ("chartered", "quarantine"):
        return {"ok": False, "why": "no such petition, or no such ruling"}
    old = rec["ruling"]
    rec.update(ruling=verdict, ruled=kernel.cycle_count, by=by)
    rec["rulings"] += 1
    name, realm = who.split(":", 1)[-1], stewardship.realm_name(rec["realm"])
    if verdict != old:
        history.event(kernel, "ASCENDED" if verdict == "chartered" else "QUARANTINED",
                      f"The {name} are {'chartered among the stars of' if verdict == 'chartered' else 'held at home by'}"
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
    return rec["ruled"] is None or kernel.cycle_count - rec["ruled"] >= stewardship.span_cycles(kernel, rec["realm"])


def season(kernel: Any) -> List[str]:
    """Once a year: each petition due is read by its realm's steward, who rules on it by its books - unless a player
    keeps the realm, who rules for it."""
    from xylarium.kernel import polity, stewardship
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
        if stewardship.steward_of(kernel, rec["realm"]):
            rec["ruled"] = kernel.cycle_count              # a player keeps the realm: it rules (command.py)
            continue
        verdict = "chartered" if lead is None else "quarantine"
        if lead is not None:
            mc.intend(rec["mind"], lead, res[lead], "quarantine", "candidate")
        sent = stewardship.mind(kernel, rec["realm"])
        rule(kernel, who, verdict, sent["name"] if sent else "the realm", logs)
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
