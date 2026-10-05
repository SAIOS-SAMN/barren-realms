"""
Xylarium realm wars: what comes of a contact that is not a bond - and what that can draw in.

When one people's network of folded passages reaches a system another's already holds (spheres.py), the style of the
one arriving decides how they meet; when it means to take what it found, it is a REALM WAR. The war is the two
peoples' - fought by the laws that fight wars: the taker's senior house (dynasties.py; else its senior sovereign)
makes war on the holder's, its levies raised and its raids run, unless a steward's ruling binds them, which holds it.
What the war takes (the ledger: each blow's magnitude, by who struck it) is the taker's authority, TAKEN: once it has
taken more than the holder took back, the contested system is its - the system passes into the taker's present realm (spheres.transfer). A war that takes nothing in a full term
of its taker's steward is spent and ends. A steward a player seats may press a claim of its own (command.py), fought
the same way.

When both peoples are ancients - each with a progenitor line - their wills contradict above every steward, and the
PROGENITORS are drawn in. Each folds - seals the war its own way into space and time (the claim to stand, or to be
undone). Two folds over one war cannot both stand; the law that decides is causal: the fold from the ancients nearer
the contested system reaches it first and is sealed; the farther arrives into a sealed past. That line's mind reads its
fold delivered nothing - a wall - and it yields. A line that ends leaves the other's will standing.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional

from xylarium.kernel import mindcore as mc

FOLD_VOCABULARY = ("fold", "yield")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "realmwars")


def war_of(kernel: Any, by: str) -> Optional[Dict[str, Any]]:
    return next((w for w in stats(kernel)["wars"].values() if w["by"] == by and w["status"] == "open"), None)


def _end(kernel: Any, war: Dict[str, Any], status: str, why: str) -> None:
    from xylarium.kernel import history, stewardship
    war["status"], war["ended"], war["why"] = status, kernel.cycle_count, why
    history.event(kernel, "GALACTIC_PEACE", f"The war for {stewardship.realm_name(war['against'])} ends",
                  cause=why, data={"war": war["id"]})


def declare(kernel: Any, from_realm: str, against: str, taker: str, sector: Optional[int],
            by: Optional[str] = None, sender: Optional[str] = None) -> Dict[str, Any]:
    """A realm war: the taker's realm against the holder's, over one system."""
    from xylarium.kernel import alignment, history, polity, spheres, stewardship
    st = stats(kernel)
    st["next"] += 1
    wid = f"G-{st['next']:05d}"
    home = spheres._home(kernel, taker)
    civ = getattr(home, "civilization", None) if home is not None else None
    side = "light" if civ is not None and alignment.character(civ) > 0 else "dark"
    holder = spheres.presence(kernel, against)
    st["wars"][wid] = war = {"id": wid, "by": by or from_realm, "sender": sender or taker, "taker": taker,
                             "holder": holder, "from": from_realm, "against": against, "sector": sector,
                             "side": side, "since": kernel.cycle_count, "status": "open", "taken": "0"}
    a, d = _champion(kernel, taker), _champion(kernel, holder)
    if a is not None and d is not None and d["id"] not in a.get("heard", {}):
        polity._hears(kernel, a, d)                          # they have met: the passage brought them face to face
        polity._hears(kernel, d, a)
    history.event(kernel, "GALACTIC_WAR", f"The {taker.split(':', 1)[-1]} make war for {stewardship.realm_name(against)}",
                  actors=[taker] + ([holder] if holder else []),
                  cause=f"their passages reached a system the {str(holder).split(':', 1)[-1]} hold, and they mean "
                        f"to take it", data={"war": wid, "from": from_realm, "against": against, "sector": sector})
    return war


def _champion(kernel: Any, who: Optional[str]) -> Optional[Dict[str, Any]]:
    """The sovereign a people fights with: its senior house's senior seat, else its own senior sovereign."""
    from xylarium.kernel import dynasties, polity
    if who is None or "polity" not in kernel.state:
        return None
    if "dynasties" in kernel.state:
        hs = sorted((h for h in dynasties.standing(kernel).values() if h["people"] == who),
                    key=lambda h: (h["founded"], h["line"]))
        for h in hs:
            recs = [polity.sovereigns(kernel)[s] for s in h["polities"] if s in polity.sovereigns(kernel)]
            if recs:
                return min(recs, key=lambda s: (s["since"], s["id"]))
    recs = polity.of_people(kernel, who)
    return min(recs, key=lambda s: (s["since"], s["id"])) if recs else None


TAKING = ("WAR", "RAID", "CONQUEST", "SUBJUGATION")


def _took(kernel: Any, by: str, from_: str, since: int) -> Fraction:
    """What one people's own blows took from another since a cycle (the ledger: the striker is the first actor)."""
    from xylarium.kernel import history
    out = Fraction(0)
    for e in history.of_people(kernel, by):
        acts = e.get("actors") or []
        if e.get("kind") in TAKING and e.get("cycle", 0) >= since and acts and acts[0] == by and from_ in acts[1:]:
            out += mc.q(e.get("magnitude") or 0)
    return out


def _fight(kernel: Any, war: Dict[str, Any], logs: List[str]) -> None:
    """A year of a realm war: its champions' war, by the sovereigns' own laws - held where a ruling binds them -
    and what it has taken read from the ledger; taking wins the system, a term of nothing spends the war."""
    from xylarium.kernel import polity, spheres, stewardship
    a, d = _champion(kernel, war["taker"]), _champion(kernel, war.get("holder"))
    if a is None or d is None or a["people"] == d["people"]:
        return
    war["champions"] = [a["id"], d["id"]]
    if not stewardship.binds(kernel, a["people"], d["people"]):
        t = polity.treaty(kernel, a["id"], d["id"])
        if t is None or t["kind"] != "war":
            polity._make(kernel, a, d, "war", f"the realm war for {stewardship.realm_name(war['against'])}")
        polity._wage(kernel, a, d)
    taken = _took(kernel, a["people"], d["people"], war["since"])
    resisted = _took(kernel, d["people"], a["people"], war["since"])
    war["taken"], war["resisted"] = str(taken), str(resisted)
    if taken > resisted:
        mine = stewardship.stats(kernel).get("envoys", {}).get(f"{war['taker']}@{war['from']}")
        if mine is not None:
            mine["authority"]["taken"] = str(Fraction(mine["authority"].get("taken", "0")) + taken)
        if war.get("sector") is not None:
            spheres.transfer(kernel, war["sector"], war["taker"])
        _escalate(kernel, war, logs)
        if not war.get("escalated"):
            _end(kernel, war, "taken", f"the {war['taker'].split(':', 1)[-1]} took what they came for")
            logs.append(f"[GALACTIC WAR] The {war['taker'].split(':', 1)[-1]} take their prize in "
                        f"{stewardship.realm_name(war['against'])}.")
        return
    if kernel.cycle_count - war["since"] >= stewardship.span_cycles(kernel, war["from"]):
        _end(kernel, war, "spent", "a steward's term of war took nothing")


def _escalate(kernel: Any, war: Dict[str, Any], logs: List[str]) -> None:
    """Contradicting wills of two progenitor lines: the war goes up to them."""
    from xylarium.kernel import board, history, stewardship
    if war.get("escalated"):
        return
    lines = board.progenitors(kernel)
    others = [s for s in stewardship.senders_of(kernel, war["against"]) if s != war["taker"] and s in lines
              and lines[s].get("ancient") is not None]
    if war["taker"] not in lines or lines[war["taker"]].get("ancient") is None or not others:
        return
    war["escalated"] = kernel.cycle_count
    war["lines"] = [war["taker"], others[0]]
    war["wills"] = {war["taker"]: "stands", others[0]: "undone"}
    a, b = lines[war["lines"][0]], lines[war["lines"][1]]
    history.event(kernel, "PROGENITORS_AT_WAR", f"{a['name']} and {b['name']} are drawn into the war for "
                  f"{stewardship.realm_name(war['against'])}", actors=list(war["lines"]),
                  cause="their stewards' wills contradict: no steward can settle it", data={"war": war["id"]})
    logs.append(f"[FOLD WAR] {a['name']} and {b['name']} are drawn in over {stewardship.realm_name(war['against'])}.")


def _contested(kernel: Any, war: Dict[str, Any]) -> Optional[int]:
    from xylarium.kernel import board, stewardship
    if war.get("sector") is not None:
        return war["sector"]
    peoples = stewardship.peoples_of(kernel, war["against"])
    if not peoples:
        return None
    who = max(peoples, key=lambda p: (sum(w.population for w in peoples[p]), p))
    return board._home_sector(kernel, who)


def _fold(kernel: Any, war: Dict[str, Any], logs: List[str]) -> None:
    """A year of the progenitors' war over one realm: each line whose will is not sealed folds (or, its fold walled,
    yields); two folds meet and the causally first stands."""
    from xylarium.kernel import board, history, stewardship
    lines = board.progenitors(kernel)
    alive = [w for w in war["lines"] if w in lines]
    if len(alive) < 2:
        if alive:
            _resolve(kernel, war, alive[0], "the other line has ended", logs)
        else:
            _end(kernel, war, "lost", "both lines have ended")
        return
    deeds = {}
    for who in war["lines"]:
        line = lines[who]
        m = line.setdefault("fold_mind", mc.new_mind())   # apart from its sealing of appeals
        entry = (war["id"], "fold")
        res = {entry: Fraction(0 if war.get("stands") == who else 1)}
        res = {k: v for k, v in res.items() if v}
        mc.seal(m, res)
        if not res:
            continue                                         # sealed its way
        if line.get("player"):
            deed = war.get("player_deeds", {}).pop(who, None)   # a player's line does as its player orders
            if deed is not None:
                deeds[who] = deed
                mc.intend(m, entry, Fraction(1), deed, "war")
            continue
        barred = mc.walls(m, mc.shape(entry, Fraction(1), "war"))
        recalled = mc.recall(m, entry, Fraction(1), "war")
        order = ([recalled] if recalled else []) + [d for d in FOLD_VOCABULARY if d != recalled]
        deed = next((d for d in order if d not in barred), None)
        if deed is not None:
            deeds[who] = deed
            mc.intend(m, entry, Fraction(1), deed, "war")
    for who, deed in deeds.items():
        if deed == "yield":
            other = next(w for w in war["lines"] if w != who)
            _resolve(kernel, war, other, f"{lines[who]['name']} yields", logs)
            return
    folding = [w for w, d in deeds.items() if d == "fold"]
    if not folding:
        return
    target = _contested(kernel, war)
    first = min(folding, key=lambda w: (board._distance(kernel, lines[w]["ancient"], target)
                                        if target is not None else float("inf"), w))
    war["stands"] = first
    war["folds"] = war.get("folds", 0) + len(folding)
    if len(folding) > 1:
        late = next(w for w in folding if w != first)
        history.event(kernel, "FOLD_WAR", f"Two folds meet over {stewardship.realm_name(war['against'])}",
                      actors=list(war["lines"]),
                      cause=f"{lines[first]['name']}'s reaches it first; {lines[late]['name']}'s arrives into a sealed "
                            f"past", data={"war": war["id"], "stands": first})
        logs.append(f"[FOLD WAR] {lines[first]['name']}'s fold stands over {stewardship.realm_name(war['against'])}.")


def _resolve(kernel: Any, war: Dict[str, Any], winner: str, why: str, logs: List[str]) -> None:
    """The fold war is over: the winner's will is sealed - the claim stands (the system is the taker's), or it is
    undone (it goes back to the realm it was taken from)."""
    from xylarium.kernel import board, spheres, stewardship
    will = war["wills"][winner]
    lines = board.progenitors(kernel)
    if winner in lines:
        lines[winner]["taken"] = lines[winner].get("taken", 0) + 1
    if war.get("sector") is not None and war.get("holder"):
        spheres.transfer(kernel, war["sector"], war["taker"] if will == "stands" else war["holder"])
    _end(kernel, war, "sealed" if will == "stands" else "undone", why)
    war["sealed_by"] = winner
    logs.append(f"[FOLD WAR] The claim on {stewardship.realm_name(war['against'])} is "
                f"{'sealed' if will == 'stands' else 'undone'}: {why}.")


def season(kernel: Any) -> List[str]:
    """Once a year, after the stewards rule: each open war is fought; each war in the progenitors' hands is folded."""
    from xylarium.kernel import polity, relations, stewardship
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    logs: List[str] = []
    st = stewardship.stats(kernel)
    for war in sorted(stats(kernel)["wars"].values(), key=lambda w: w["id"]):
        if war["status"] != "open":
            continue
        if war["by"].startswith("seat:"):
            if st["stewards"].get(war["from"]) != war["sender"].split(":", 1)[1]:
                _end(kernel, war, "withdrawn", "its steward has left the seat")
            else:
                _fight(kernel, war, logs)
        elif war["taker"] not in relations._peoples(kernel):
            _end(kernel, war, "withdrawn", "its people is gone")
        elif war.get("escalated"):
            _fold(kernel, war, logs)
        else:
            _fight(kernel, war, logs)
    return logs


def of_realm(kernel: Any, realm: str) -> List[Dict[str, Any]]:
    return [w for w in stats(kernel)["wars"].values() if realm in (w["from"], w["against"])]


def summary(kernel: Any) -> Dict[str, Any]:
    by: Dict[str, int] = {}
    for w in stats(kernel)["wars"].values():
        by[w["status"]] = by.get(w["status"], 0) + 1
    return {"wars": by, "fold_wars": sum(1 for w in stats(kernel)["wars"].values() if w.get("escalated"))}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="realmwars",
    state=lambda: {"wars": {}, "next": 0},
    season=season,
    summary=summary,
))
