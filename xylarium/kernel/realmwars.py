"""
Xylarium realm wars: when a steward does its sender's bidding beyond its realm - and what that can draw in.

A steward keeps its realm's books (stewardship.py). It also carries its sender's will - the ancient people whose
progenitors sent it, Light or Dark as that people's whole history makes it (a steward with no living people behind
it is of the realm it keeps). That will reads the other realms in a book of its own, REACH, by the will's own side:

  Light   a realm darker than its own is a deficit: its own balance less theirs (order made against destroyed)
  Dark    a realm richer than its own is a deficit: their peoples less its own

Its realm comes first: only a steward whose own mind accounts for its realm's books (every deficit there drained by
a deed it has learned answers it) turns to that will - expansion is what a realm in order does, never a reflex.
Then its deepest reach deficit leads, and the deed is a CLAIM: a galactic war between realms, fought by the laws that fight
wars - its realm's senior house (dynasties.py; else its largest people's sovereign) makes war on the claimed realm's
(the darkest people's, for the Light; the richest's, for the Dark), its levies raised and its raids run - once the
two have met (a war cannot reach between peoples that cannot reach each other), and unless a steward's ruling binds
them, which holds it. What the war takes (lives, by the ledger) is the claimant's
authority there, TAKEN: once it has taken any, its sender's steward is seated in the claimed realm by war.

Each year the claim is sealed in the steward's own mind like any deed: if the deficit it named shrank, a crystal;
if not, a wall - and a walled claim is not made again. Expansion ends by learning, not by any cap.

When the claimed realm is kept by a steward sent by another progenitor line, the war goes up: the two lines' wills
contradict, and the PROGENITORS are drawn in. Each folds - seals the war its own way into space and time (the
claim to stand, or to be undone). Two folds over one war cannot both stand; the law that decides is causal: the fold
from the ancients nearer the contested realm reaches it first and is sealed; the farther arrives into a sealed past.
That line's mind reads its fold delivered nothing - a wall - and it yields. A line that ends leaves the other's
will standing. The elders, who have no ancients' home, fight no fold wars.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional

from xylarium.kernel import mindcore as mc

REACH_BOOKS = ("reach",)
FOLD_VOCABULARY = ("fold", "yield")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "realmwars")


def _people(kernel: Any, realm: str) -> int:
    from xylarium.kernel import stewardship
    return sum(w.population for ws in stewardship.peoples_of(kernel, realm).values() for w in ws)


def reach(kernel: Any, envoy: Dict[str, Any]) -> mc.Chain:
    """Its sender's will, read against the other realms: signed, per realm, never summed."""
    from xylarium.kernel import stewardship
    b = stewardship.bent(kernel, envoy)
    if not b:
        return {}
    mine = envoy["realm"]
    out: mc.Chain = {}
    for other in stewardship.realms(kernel):
        if other == mine:
            continue
        if b > 0:
            need, have = stewardship.realm_balance(kernel, mine), stewardship.realm_balance(kernel, other)
            if need is None or have is None:
                continue
        else:
            need, have = _people(kernel, other), _people(kernel, mine)
        d = mc.q(need) - mc.q(have)
        if d:
            out[(other, "reach")] = d
    return out


def settled(kernel: Any, e: Dict[str, Any]) -> bool:
    """Need orders: a steward turns to its sender's will only when its own mind accounts for its realm's books - every
    deficit there drained by a deed it knows answers it."""
    from xylarium.kernel import stewardship
    own = stewardship.books(kernel, e["realm"])
    roles = {site: ("people" if book == "power" else "pair") for site, book in own}
    return mc.verdict(e.get("mind") or mc.new_mind(), own, roles)["reading"] == mc.ACCOUNTED


def war_of(kernel: Any, envoy_key: str) -> Optional[Dict[str, Any]]:
    return next((w for w in stats(kernel)["wars"].values() if w["by"] == envoy_key and w["status"] == "open"), None)


def _end(kernel: Any, war: Dict[str, Any], status: str, why: str) -> None:
    from xylarium.kernel import history, stewardship
    war["status"], war["ended"], war["why"] = status, kernel.cycle_count, why
    history.event(kernel, "GALACTIC_PEACE", f"The war for {stewardship.realm_name(war['against'])} ends",
                  cause=why, data={"war": war["id"]})


def _bidding(kernel: Any, key: str, e: Dict[str, Any], logs: List[str]) -> None:
    """One steward's beat for its sender: last year's claim sealed; the deepest reach deficit claimed."""
    from xylarium.kernel import history, stewardship
    bm = e.setdefault("bidding", mc.new_mind())
    res = reach(kernel, e)
    mc.seal(bm, res)
    open_war = war_of(kernel, key)
    entry = mc.lead(res, REACH_BOOKS, deepest=True)
    if open_war is not None and open_war.get("escalated"):
        return                                               # it is in the progenitors' hands now
    if entry is None or "claim" in mc.walls(bm, mc.shape(entry, res[entry], "realm")):
        if open_war is not None:
            _end(kernel, open_war, "withdrawn", "its claim no longer delivers what its sender wills")
        return
    if open_war is None and not settled(kernel, e):
        return                                               # its realm's own books come first
    if open_war is not None and open_war["against"] != entry[0]:
        _end(kernel, open_war, "withdrawn", "its sender's will turns elsewhere")
        open_war = None
    if open_war is None:
        st = stats(kernel)
        st["next"] += 1
        wid = f"G-{st['next']:05d}"
        side = "light" if (stewardship.bent(kernel, e) or 0) > 0 else "dark"
        st["wars"][wid] = open_war = {"id": wid, "by": key, "sender": e["sender"], "from": e["realm"],
                                      "against": entry[0], "side": side, "since": kernel.cycle_count,
                                      "status": "open", "taken": "0"}
        history.event(kernel, "GALACTIC_WAR", f"{e['name']} of {stewardship.realm_name(e['realm'])} claims "
                      f"{stewardship.realm_name(entry[0])}",
                      cause=(f"its sender's Light: the {stewardship.realm_name(entry[0])} is darker than its own"
                             if side == "light" else
                             f"its sender's Dark: the {stewardship.realm_name(entry[0])} holds more than its own"),
                      data={"war": wid, "from": e["realm"], "against": entry[0]})
        logs.append(f"[GALACTIC WAR] {e['name']} of {stewardship.realm_name(e['realm'])} claims "
                    f"{stewardship.realm_name(entry[0])} ({side}).")
    mc.intend(bm, entry, res[entry], "claim", "realm")


def _champion(kernel: Any, realm: str, pick: str) -> Optional[Dict[str, Any]]:
    """The sovereign a realm fights with: its senior house's senior seat - else, among its peoples' sovereigns, the
    darkest people's (pick 'dark'), the richest's (pick 'rich'), or the largest's."""
    from xylarium.kernel import alignment, dynasties, polity, stewardship
    if pick == "senior" and "dynasties" in kernel.state:
        hs = sorted((h for h in dynasties.standing(kernel).values() if h["realm"] == realm),
                    key=lambda h: (h["founded"], h["line"]))
        for h in hs:
            recs = [polity.sovereigns(kernel)[s] for s in h["polities"] if s in polity.sovereigns(kernel)]
            if recs:
                return min(recs, key=lambda s: (s["since"], s["id"]))
    peoples = stewardship.peoples_of(kernel, realm)

    def key(who: str) -> Any:
        ws = peoples[who]
        if pick == "dark":
            civ = getattr(max(ws, key=lambda w: (w.population, w.id)), "civilization", None)
            return (alignment.character(civ) if civ is not None else 0.0, who)
        return (-sum(w.population for w in ws), who)
    for who in sorted(peoples, key=key):
        recs = polity.of_people(kernel, who)
        if recs:
            return min(recs, key=lambda s: (s["since"], s["id"]))
    return None


def _fight(kernel: Any, war: Dict[str, Any], logs: List[str]) -> None:
    """A year of a realm war: its champions' war, by the sovereigns' own laws - held where a ruling binds them -
    and what it has taken read from the ledger."""
    from xylarium.kernel import board, polity, stewardship
    a = _champion(kernel, war["from"], "senior")
    d = _champion(kernel, war["against"], "dark" if war["side"] == "light" else "rich")
    if a is None or d is None or a["people"] == d["people"]:
        return
    war["champions"] = [a["id"], d["id"]]
    if d["id"] not in a.get("heard", {}):
        return                                               # they have never met: no war can reach between them
    if stewardship.binds(kernel, a["people"], d["people"]):
        return                                               # a steward's ruling holds it
    t = polity.treaty(kernel, a["id"], d["id"])
    if t is None or t["kind"] != "war":
        polity._make(kernel, a, d, "war", f"the realm war for {stewardship.realm_name(war['against'])}")
    polity._wage(kernel, a, d)
    taken = mc.q(stewardship._stake_since(kernel, a["people"], d["people"], war["since"]))
    war["taken"] = str(taken)
    env = stewardship.stats(kernel)["envoys"]
    seat = f"{war['sender']}@{war['against']}"
    if taken > 0 and seat not in env and not war["sender"].startswith("seat:"):
        lines = board.progenitors(kernel)
        line = lines.get(war["sender"]) or {"name": env[war["by"]]["line"], "ancient": None}
        stewardship.send(kernel, war["sender"], line, war["against"], taken=True)
        logs.append(f"[GALACTIC WAR] {env[seat]['name']} is seated in {stewardship.realm_name(war['against'])} by war.")
    if seat in env and env[seat].get("taken_seat"):
        env[seat]["authority"]["taken"] = str(taken)
    _escalate(kernel, war, logs)


def _escalate(kernel: Any, war: Dict[str, Any], logs: List[str]) -> None:
    """Contradicting wills of two progenitor lines: the war goes up to them."""
    from xylarium.kernel import board, history, stewardship
    if war.get("escalated") or war["sender"] == "elders":
        return
    lines = board.progenitors(kernel)
    others = sorted((e for e in stewardship.envoys(kernel, war["against"])
                     if e["sender"] not in (war["sender"], "elders") and e["sender"] in lines
                     and not e.get("taken_seat")), key=lambda e: (e["since"], e["id"]))
    if not others or war["sender"] not in lines:
        return
    war["escalated"] = kernel.cycle_count
    war["lines"] = [war["sender"], others[0]["sender"]]
    war["wills"] = {war["sender"]: "stands", others[0]["sender"]: "undone"}
    a, b = lines[war["lines"][0]], lines[war["lines"][1]]
    history.event(kernel, "PROGENITORS_AT_WAR", f"{a['name']} and {b['name']} are drawn into the war for "
                  f"{stewardship.realm_name(war['against'])}", actors=list(war["lines"]),
                  cause="their stewards' wills contradict: no steward can settle it", data={"war": war["id"]})
    logs.append(f"[FOLD WAR] {a['name']} and {b['name']} are drawn in over {stewardship.realm_name(war['against'])}.")


def _contested(kernel: Any, war: Dict[str, Any]) -> Optional[int]:
    from xylarium.kernel import board, stewardship
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
    """The fold war is over: the winner's will is sealed - the claim stands, or it is undone (the claimant's seat
    taken by war is unseated, and what it took is no one's authority)."""
    from xylarium.kernel import board, stewardship
    will = war["wills"][winner]
    lines = board.progenitors(kernel)
    if winner in lines:
        lines[winner]["taken"] = lines[winner].get("taken", 0) + 1
    if will == "undone":
        stewardship.stats(kernel)["envoys"].pop(f"{war['sender']}@{war['against']}", None)
    _end(kernel, war, "sealed" if will == "stands" else "undone", why)
    war["sealed_by"] = winner
    logs.append(f"[FOLD WAR] The claim on {stewardship.realm_name(war['against'])} is "
                f"{'sealed' if will == 'stands' else 'undone'}: {why}.")


def season(kernel: Any) -> List[str]:
    """Once a year, after the stewards rule: each AI steward does its sender's bidding; each open war is fought;
    each war in the progenitors' hands is folded."""
    from xylarium.kernel import polity, stewardship
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    logs: List[str] = []
    st = stewardship.stats(kernel)
    for key, e in sorted(st.get("envoys", {}).items()):
        if st["stewards"].get(e["realm"]):
            continue                                         # a realm a player keeps: its player claims, or not
        _bidding(kernel, key, e, logs)
    for war in sorted(stats(kernel)["wars"].values(), key=lambda w: w["id"]):
        if war["status"] != "open":
            continue
        if war["by"].startswith("seat:"):
            if st["stewards"].get(war["from"]) != war["sender"].split(":", 1)[1]:
                _end(kernel, war, "withdrawn", "its steward has left the seat")
            else:
                _fight(kernel, war, logs)
        elif war["by"] not in st.get("envoys", {}):
            _end(kernel, war, "withdrawn", "its steward is gone")
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
