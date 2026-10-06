"""
Xylarium stewardship: the realms of the 3-sphere, and the stewards (T2) who keep the balance between their peoples.

REALMS. A realm is a shell of a sphere of influence (spheres.py): the systems a people's network of folded passages
reached in one steward's term - founded where its passages first arrive, never laid in advance. Realms emerge where
peoples cross to the stars, and grow as their networks grow; a people no network reaches is kept by no steward.
Each realm's own steward is its network people's (the ancients' are their progenitors'); a federation sends each
partner's steward into the other's realms. A steward's term, and the span a ruling stands, is its sender's generation
read in the realm's own clock (spheres.term_years) - no span is laid down by the architects.

THE HIERARCHY. A sovereign (T3) serves one people, by its people's own lights. A steward (T2) serves no people: it
keeps its realm's balance and adjudicates between the sovereigns of the peoples there. Its rulings are authority:
sovereigns bend to them - the laws that would carry a people across a ruling (a raid, a subjugation, a seated
sovereign's assault) are refused while it stands. A dispute beyond one steward - its parties in two realms, or a ruling
appealed - goes up to the progenitors (T0), who fold space and time to settle it: a sealed ruling stands for good,
and the parties' worldlines are joined by it (clocks.link). Above every seat are the ancients: the laws themselves.
No ruling can order what the laws do not allow.

RULINGS. ceasefire (no raid or assault between the parties), release (a patron's hold on a tributary is ended),
pact (the parties are bound by a pact, relations.py) - each for a span of clock years, or for good once sealed.
"""

import math
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import mindcore as mc

RULINGS = ("ceasefire", "release", "pact")
CONTESTED = ("WAR", "RAID", "CONQUEST", "SUBJUGATION", "REVOLT", "REBELLION",
             "COVERT_EXPOSED")                         # a covert work the watch caught: heard; one unseen is not


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "stewardship")


# ---------------------------------------------------------------------- the realms
def realm_of(kernel: Any, sector_id: int) -> Optional[str]:
    """The realm a system lies in: the first network that reached it (spheres.py) - or none yet."""
    from xylarium.kernel import spheres
    return spheres.owner(kernel, sector_id) if hasattr(kernel, "state") else None


def realm_name(key: Optional[str]) -> str:
    from xylarium.kernel import spheres
    return spheres.realm_name(key) if key else "no realm"


def realms(kernel: Any) -> List[str]:
    from xylarium.kernel import spheres
    return spheres.realms(kernel)


def term_years(kernel: Any, realm: Optional[str]) -> float:
    """A realm's steward's term in its own years (spheres.term_years)."""
    from xylarium.kernel import spheres
    return spheres.term_years(kernel, realm) if realm else 1.0


def _seat(kernel: Any, realm: str) -> Optional[int]:
    from xylarium.kernel import spheres
    r = spheres.stats(kernel)["realms"].get(realm)
    return r["seat"] if r else None


def term_cycles(kernel: Any, realm: str) -> float:
    """A steward's term on the clock: its years, lived at its seat's own pace (clocks.cycles_of) - unfloored, so a
    seat whose clock runs fast sees several terms within one of the engine's frames."""
    from xylarium.kernel import clocks
    return clocks.cycles_of(kernel, term_years(kernel, realm), _seat(kernel, realm))


def span_cycles(kernel: Any, realm: Optional[str] = None) -> int:
    """The span a steward's memory and rulings cover, in clock cycles: its realm's term, lived at its seat's pace and
    never shorter than one of the engine's frames - or, across realms, the longest any keeps (from the beginning,
    before any realm is founded)."""
    from xylarium.kernel import clocks
    if realm is not None:
        return math.ceil(clocks.lived_span(kernel, term_years(kernel, realm), _seat(kernel, realm)))
    rs = realms(kernel)
    return max(span_cycles(kernel, r) for r in rs) if rs else kernel.cycle_count


def peoples_of(kernel: Any, realm: str) -> Dict[str, List[Any]]:
    """The peoples whose capital (largest world) lies in the realm, with their worlds."""
    return dict(_by_realm(kernel).get(realm, {}))


def _by_realm(kernel: Any) -> Dict[Optional[str], Dict[str, List[Any]]]:
    """Every people by the realm its capital lies in, read once a cycle."""
    from xylarium.kernel import cache, relations

    def build() -> Dict[Optional[str], Dict[str, List[Any]]]:
        out: Dict[Optional[str], Dict[str, List[Any]]] = {}
        for who, worlds in relations._peoples(kernel).items():
            home = max(worlds, key=lambda w: (w.population, w.id))
            out.setdefault(realm_of(kernel, home.sector_id), {})[who] = worlds
        return out
    if not hasattr(kernel, "caches"):
        return build()
    return cache.stamped(kernel, "stewardship_by_realm", "all",
                         (kernel.cycle_count, stats_of_spheres(kernel).get("v", 0)), build)


def stats_of_spheres(kernel: Any) -> Dict[str, Any]:
    from xylarium.kernel import spheres
    return spheres.stats(kernel) if hasattr(kernel, "state") else {"owner": {}}


def party(kernel: Any, holder: Optional[str]) -> Optional[str]:
    """Who stands for a holder before a steward: a seated sovereign's holdings stand with its people."""
    if holder and holder.startswith("captain:"):
        from xylarium.kernel import roles
        rec = roles.stats(kernel).get("realms", {}).get(holder.split(":", 1)[1])
        if rec:
            return rec["holder"]
    return holder


def sovereigns_of(kernel: Any, realm: str) -> List[Dict[str, Any]]:
    """The sovereigns of the realm's peoples: seated players (human or AI) by the people they serve, and every other
    people's own councils, which are its sovereign where no seat is."""
    from xylarium.kernel import roles
    seated = {rec["holder"]: pid for pid, rec in roles.stats(kernel).get("realms", {}).items()}
    out = []
    for who, worlds in peoples_of(kernel, realm).items():
        out.append({"people": who, "seat": seated.get(who), "worlds": len(worlds),
                    "population": sum(w.population for w in worlds)})
    return sorted(out, key=lambda s: -s["population"])


def disputes(kernel: Any, realm: str) -> List[Dict[str, Any]]:
    """What is contested in the realm: a patron's hold on a tributary, and the recent raids and assaults between its
    peoples (the history ledger) - each with its parties, as a steward hears them."""
    from xylarium.kernel import history, relations
    mine = set(peoples_of(kernel, realm))
    out = []
    for sub, tie in relations.ties(kernel).items():
        if sub in mine or tie["patron"] in mine:
            out.append({"kind": "hold", "a": tie["patron"], "b": sub, "terms": tie.get("kind"),
                        "tribute_sol": tie.get("tribute_sol")})
    seen: Dict[Tuple[str, str], Dict[str, Any]] = {}
    horizon = kernel.cycle_count - span_cycles(kernel, realm)
    for e in reversed(history.stats(kernel)["recent"]):
        if e.get("cycle", 0) < horizon:
            break
        if e["kind"] not in CONTESTED:
            continue
        ps = sorted({party(kernel, a) for a in e.get("actors", []) if a})
        if len(ps) != 2 or not (ps[0] in mine or ps[1] in mine):
            continue
        key = tuple(ps)
        if key in seen:
            seen[key]["stake"] += float(e.get("magnitude") or 0) + 1.0
            continue
        seen[key] = {"kind": e["kind"].lower(), "a": ps[0], "b": ps[1], "event": e["id"], "title": e["title"],
                     "stake": float(e.get("magnitude") or 0) + 1.0}
        out.append(seen[key])
    return out


# ---------------------------------------------------------------------- the steward's seat
def seat_steward(kernel: Any, player_id: str, name: str, realm: str) -> Dict[str, Any]:
    """A player (human or AI) takes a realm's steward's seat. It holds no worlds; it stands where its realm's
    largest people lives, to hear its sovereigns."""
    from xylarium.kernel import roles
    if realm not in realms(kernel):
        raise ValueError(f"No realm {realm}.")
    cap = kernel.get_player(player_id) or kernel.register_player(player_id, name)
    ps = peoples_of(kernel, realm)
    if ps:
        home = max((w for ws in ps.values() for w in ws), key=lambda w: (w.population, w.id))
        roles.place(kernel, player_id, home.sector_id)
    roles.stats(kernel)["of"][player_id] = "steward"
    stats(kernel)["stewards"][realm] = player_id
    return {"role": "steward", "realm": realm, "name": realm_name(realm), "peoples": len(ps),
            "sector": cap.sector_id}


def steward_of(kernel: Any, realm: str) -> Optional[str]:
    return stats(kernel)["stewards"].get(realm)


def realm_held(kernel: Any, player_id: str) -> Optional[str]:
    return next((r for r, p in stats(kernel)["stewards"].items() if p == player_id), None)


def _key(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


def rule(kernel: Any, player_id: str, kind: str, a: str, b: str) -> Dict[str, Any]:
    """A steward rules between two parties. Within its realm the ruling binds at once; a party beyond it makes the
    dispute one for the progenitors: the ruling waits, appealed, until one seals it."""
    realm = realm_held(kernel, player_id)
    if realm is None:
        return {"ok": False, "why": "You keep no realm."}
    return _rule(kernel, realm, player_id, kind, a, b)


def _rule(kernel: Any, realm: str, player_id: str, kind: str, a: str, b: str) -> Dict[str, Any]:
    from xylarium.kernel import history
    if kind not in RULINGS:
        return {"ok": False, "why": f"A steward rules a {', a '.join(RULINGS)}."}
    a, b = party(kernel, a), party(kernel, b)
    mine = set(peoples_of(kernel, realm))
    st = stats(kernel)
    st["next"] += 1
    rec = {"id": f"R-{st['next']:05d}", "kind": kind, "a": a, "b": b, "by": player_id, "realm": realm,
           "cycle": kernel.cycle_count, "until": kernel.cycle_count + span_cycles(kernel, realm), "sealed": False}
    if a not in mine or b not in mine:
        rec["appealed"] = True                             # beyond one steward: up the chain
        if any({r["a"], r["b"]} == {a, b} and r["kind"] == kind for r in st["appeals"]):
            return {"ok": True, "ruling": rec, "appealed": True}      # already before the progenitors
        st["appeals"].append(rec)
        history.event(kernel, "APPEAL", f"A dispute between the {a.split(':', 1)[-1]} and the {b.split(':', 1)[-1]} "
                      f"goes up to the progenitors", actors=[a, b], cause=f"it reaches beyond {realm_name(realm)}",
                      data={"ruling": rec["id"]})
        return {"ok": True, "ruling": rec, "appealed": True}
    _apply(kernel, rec)
    st["rulings"][_key(a, b) + "|" + kind] = rec
    history.event(kernel, "RULING", f"The steward of {realm_name(realm)} rules a {kind} between the "
                  f"{a.split(':', 1)[-1]} and the {b.split(':', 1)[-1]}", actors=[a, b],
                  cause=f"for {term_years(kernel, realm):.0f} years (its steward's term), binding their sovereigns", data={"ruling": rec["id"]})
    return {"ok": True, "ruling": rec, "appealed": False}


def _apply(kernel: Any, rec: Dict[str, Any]) -> None:
    from xylarium.kernel import relations
    a, b = rec["a"], rec["b"]
    if rec["kind"] == "release":
        for sub, sup in ((a, b), (b, a)):
            tie = relations.ties(kernel).get(sub)
            if tie is not None and tie["patron"] == sup:
                relations.ties(kernel).pop(sub, None)       # the hold is ended
    elif rec["kind"] == "pact":
        relations.pacts(kernel)[relations._pair(a, b)] = {"since": kernel.cycle_count, "by": "ruling",
                                                          "ruling": rec["id"]}


def binds(kernel: Any, a: Optional[str], b: Optional[str], kind: str = "ceasefire") -> Optional[Dict[str, Any]]:
    """The ruling that stands between two parties, if one does: what a raid, a hold or an assault must bend to."""
    if not a or not b or "stewardship" not in getattr(kernel, "state", {}):
        return None
    a, b = party(kernel, a), party(kernel, b)
    rec = stats(kernel)["rulings"].get(_key(a, b) + "|" + kind)
    if rec is None:
        return None
    if not rec["sealed"] and kernel.cycle_count > rec["until"]:
        return None                                        # its span has run
    return rec


def appeals(kernel: Any) -> List[Dict[str, Any]]:
    return list(stats(kernel)["appeals"])


def seal(kernel: Any, progenitor_id: str, ruling_id: str) -> Dict[str, Any]:
    """A progenitor folds space and time to settle a ruling for good: it binds whatever realms its parties live in,
    stands without end, and joins the parties' worldlines (clocks.link)."""
    from xylarium.kernel import roles
    if roles.role_of(kernel, progenitor_id) != "progenitor":
        return {"ok": False, "why": "Only a progenitor seals what is appealed."}
    return _seal(kernel, progenitor_id, ruling_id)


def _seal(kernel: Any, progenitor_id: str, ruling_id: str) -> Dict[str, Any]:
    from xylarium.kernel import clocks, history
    st = stats(kernel)
    rec = next((r for r in st["appeals"] if r["id"] == ruling_id), None) or \
        next((r for r in st["rulings"].values() if r["id"] == ruling_id), None)
    if rec is None:
        return {"ok": False, "why": f"No ruling {ruling_id}."}
    rec["sealed"] = True
    rec["sealed_by"] = progenitor_id
    rec["sealed_at"] = kernel.cycle_count
    st["appeals"] = [r for r in st["appeals"] if r["id"] != ruling_id]
    _apply(kernel, rec)
    st["rulings"][_key(rec["a"], rec["b"]) + "|" + rec["kind"]] = rec
    clocks.link(kernel, rec["a"], rec["b"], f"a {rec['kind']} sealed by a progenitor")
    history.event(kernel, "SEALED", f"A progenitor seals the {rec['kind']} between the {rec['a'].split(':', 1)[-1]} "
                  f"and the {rec['b'].split(':', 1)[-1]}", actors=[rec["a"], rec["b"]],
                  cause="space and time folded: it stands for good", data={"ruling": rec["id"]})
    return {"ok": True, "ruling": rec}


# ---------------------------------------------------------------------- the realm, as its steward reads it
def overview(kernel: Any, realm: str) -> Dict[str, Any]:
    """A realm as its steward reads it: every people at the level of history (its stage, what holds it back), its
    sovereigns, its disputes, its rulings - and its balance: made and destroyed over all its peoples' whole histories."""
    from xylarium.kernel import alignment, annals, dynasties, knowledge, realmwars, relations
    rows = []
    made = destroyed = 0.0
    for who, worlds in peoples_of(kernel, realm).items():
        home = max(worlds, key=lambda w: (w.population, w.id))
        civ = getattr(home, "civilization", None)
        stage = annals._stage(kernel, who, home) if civ is not None else None
        if civ is not None:
            cs = alignment.causes(civ)
            made += sum(v["light"] for v in cs.values())
            destroyed += sum(v["dark"] for v in cs.values())
        rows.append({"people": who, "worlds": len(worlds), "population": sum(w.population for w in worlds),
                     "stage": stage, "alignment": round(alignment.character(civ), 3) if civ is not None else None,
                     "folded": _folded(kernel, who)})
    rows.sort(key=lambda r: -r["population"])
    rulings = [r for r in stats(kernel)["rulings"].values() if r["realm"] == realm or r.get("sealed")]
    sent = [{"name": e["name"], "sender": e["sender"], "line": e["line"], "ruled": e["ruled"],
             "authority": dict(e["authority"]), "alignment": bent(kernel, e)} for e in envoys(kernel, realm)]
    return {"realm": realm, "name": realm_name(realm), "steward": steward_of(kernel, realm), "peoples": rows,
            "envoys": sent, "wars": realmwars.of_realm(kernel, realm) if "realmwars" in kernel.state else [],
            "houses": dynasties.of_realm(kernel, realm) if "dynasties" in kernel.state else [],
            "sovereigns": sovereigns_of(kernel, realm), "disputes": disputes(kernel, realm), "rulings": rulings,
            "balance": round((made - destroyed) / (made + destroyed), 4) if made + destroyed > 0 else None}


def _folded(kernel: Any, who: str) -> bool:
    from xylarium.kernel import zones
    return who in zones.folded_peoples(kernel)


def kernel_ref() -> Any:
    from xylarium.kernel import ledger
    return ledger.active_kernel()


def render(o: Dict[str, Any]) -> str:
    lines = [f"=== {o['name'].upper()} ({o['realm']}) - steward: {o['steward'] or 'none'} ===",
             f"  Balance (made against destroyed, all its peoples): "
             + (f"{o['balance']:+.3f}" if o["balance"] is not None else "-")]
    lines.append(f"  {'People':<22}{'Worlds':>7}{'Population':>14}  {'Stage':<9}{'Align':>7}  held")
    for r in o["peoples"][:20]:
        lines.append(f"  {r['people'].split(':', 1)[-1][:21]:<22}{r['worlds']:>7}{r['population']:>14,}  "
                     f"{(r['stage'] or '-'):<9}{(r['alignment'] if r['alignment'] is not None else 0):>+7.2f}  "
                     f"{'folded' if r['folded'] else 'open'}")
    if o.get("envoys"):
        lines.append("  Stewards sent here (authority: granted / earned / grown / taken):")
        for e in o["envoys"]:
            a = e["authority"]
            lines.append(f"   {e['name']} of {e['line']}"
                         + (f" ({e['alignment']:+.2f})" if e["alignment"] is not None else "")
                         + f": {a['granted']} / {float(Fraction(a['earned'])):.3g} / {float(Fraction(a['grown'])):.3g}"
                         f" / {float(Fraction(a['taken'])):.3g}, {e['ruled']} rulings")
    for w in o.get("wars", []):
        lines.append(f"  Realm war {w['id']} ({w['side']}): {realm_name(w['from'])} claims {realm_name(w['against'])}"
                     f" - {w['status']}" + (", in the progenitors' hands" if w.get("escalated") else "")
                     + f"; taken {float(Fraction(w['taken'])):.3g}")
    if o.get("houses"):
        lines.append("  Houses (authority: granted / earned / grown / taken):")
        for h in o["houses"]:
            a = h["authority"]
            lines.append(f"   House of {h['name']} of the {h['people'].split(':', 1)[-1]}: {a['granted']} / "
                         f"{float(Fraction(a['earned'])):.3g} / {a['grown']} / {a['taken']}; duty {h['duty'] or '-'}, "
                         f"{len(h['captains'])} captains")
    if o["disputes"]:
        lines.append("  Disputes:")
        for i, d in enumerate(o["disputes"], 1):
            lines.append(f"   [{i}] {d['kind']}: {d['a'].split(':', 1)[-1]} / {d['b'].split(':', 1)[-1]}"
                         + (f" - {d['title']}" if d.get("title") else ""))
    if o.get("sovereigns"):
        from xylarium.kernel import polity
        lines.append("  Sovereigns:")
        for s in o["sovereigns"][:12]:
            recs = polity.of_people(kernel_ref(), s["people"]) if kernel_ref() is not None else []
            for r in recs:
                ts = polity.treaties_of(kernel_ref(), r["id"])
                held = ", ".join(sorted({t["kind"] for t in ts})) or "no treaties"
                lines.append(f"   {r['name']} of the {r['polity']} (gen {r['generation']}): {held}"
                             + (" [seated]" if r.get("player") else ""))
    if o["rulings"]:
        lines.append("  Rulings:")
        for r in o["rulings"]:
            lines.append(f"   {r['id']} {r['kind']}: {r['a'].split(':', 1)[-1]} / {r['b'].split(':', 1)[-1]}"
                         + (" (sealed)" if r["sealed"] else f" (until year {r['until'] // 100:,})"))
    return "\n".join(lines)


# ---------------------------------------------------------------------- the stewards' minds
def envoys(kernel: Any, realm: str) -> List[Dict[str, Any]]:
    """The stewards in a realm: its own - sent by the people whose network reached it (the ancients' by their
    progenitor line) - and, for each federation that people has made, its partner's. A player's progenitor line sends
    only whom its player chooses (command.py). A steward whose people has fallen stays, its grant lapsed: it holds only
    the authority it has earned and grown."""
    from xylarium.kernel import board
    st = stats(kernel)
    env = st.setdefault("envoys", {})
    if not isinstance(st["minds"].get(realm, ""), str):
        st["minds"].pop(realm)                               # a save from before envoys: its steward is sent anew
    lines = board.progenitors(kernel)
    for who in senders_of(kernel, realm):
        line = lines.get(who)
        if f"{who}@{realm}" in env or (line is not None and line.get("player")):
            continue
        send(kernel, who, line or {"name": f"the {who.split(':', 1)[-1]}", "ancient": None}, realm)
    out = [r for r in env.values() if r["realm"] == realm]
    for r in out:
        _authority(kernel, r, lines)
    out.sort(key=lambda r: (r["since"], r["id"]))
    if out:
        st["minds"][realm] = next(k for k, v in env.items() if v is out[0])   # the senior envoy: of record
    return out


def senders_of(kernel: Any, realm: str) -> List[str]:
    """Who keeps a steward in a realm by right: its network's people, and that people's federation partners."""
    from xylarium.kernel import spheres
    who = spheres.presence(kernel, realm)
    if who is None:
        return []
    out = [who]
    for b in spheres.stats(kernel)["bonds"].values():
        if b["kind"] == "federation" and who in (b["a"], b["b"]):
            out.append(b["b"] if b["a"] == who else b["a"])
    return out


def covers(kernel: Any, who: str, realm: str) -> bool:
    """May a people's line keep a steward in a realm: its own network's, or a federation partner's."""
    return who in senders_of(kernel, realm)


def send(kernel: Any, who: str, line: Dict[str, Any], realm: str, taken: bool = False) -> Dict[str, Any]:
    """A progenitor line's steward takes a seat in a realm: sent there (granted), or seated by a war (taken)."""
    from xylarium.kernel import history, mindcore as _mc
    st = stats(kernel)
    key = f"{who}@{realm}"
    st["next"] += 1
    rec = st["envoys"][key] = {"id": f"W-{st['next']:05d}", "name": _steward_name(kernel, key, 1), "sender": who,
                               "line": line["name"], "realm": realm, "since": kernel.cycle_count, "generation": 1,
                               "ruled": 0, "mind": _mc.new_mind(), "taken_seat": taken,
                               "authority": {"granted": "0" if taken else "1", "earned": "0", "grown": "0",
                                             "taken": "0"}}
    history.event(kernel, "STEWARD_SEATED" if taken else "STEWARD_SENT",
                  f"{rec['name']} {'takes a seat in' if taken else 'is sent to keep'} {realm_name(realm)}",
                  actors=[who] if who.startswith("civ:") else [],
                  cause=("by war" if taken else f"by {line['name']}, progenitor of the {who.split(':', 1)[-1]}")
                  if line.get("ancient") else ("by war" if taken else "by the elders" if who == "elders"
                                               else f"by the {who.split(':', 1)[-1]} themselves"),
                  data={"steward": rec["id"], "realm": realm})
    return rec


def realm_balance(kernel: Any, realm: str) -> Optional[float]:
    """Made against destroyed, over all the realm's peoples' whole histories."""
    from xylarium.kernel import alignment
    made = destroyed = 0.0
    for worlds in peoples_of(kernel, realm).values():
        civ = getattr(max(worlds, key=lambda w: (w.population, w.id)), "civilization", None)
        if civ is not None:
            for v in alignment.causes(civ).values():
                made += v["light"]
                destroyed += v["dark"]
    return (made - destroyed) / (made + destroyed) if made + destroyed > 0 else None


def bent(kernel: Any, rec: Dict[str, Any]) -> Optional[float]:
    """A steward's alignment: its sender's - the ancient people whose progenitors sent it (whole-history light
    against dark). A steward with no living people behind it (the elders', or a fallen line's) is of the realm it
    keeps: its peoples' balance."""
    from xylarium.kernel import alignment, relations
    worlds = relations._peoples(kernel).get(rec["sender"]) or []
    civ = getattr(max(worlds, key=lambda w: (w.population, w.id)), "civilization", None) if worlds else None
    if civ is not None:
        return round(alignment.character(civ), 3)
    b = realm_balance(kernel, rec["realm"])
    return round(b, 3) if b is not None else None


def _authority(kernel: Any, rec: Dict[str, Any], senders: Dict[str, Any]) -> None:
    """Authority, by where it comes from - never summed: granted (its sender's line stands), earned (what its
    rulings measurably stopped: its crystals' deliveries), grown (years held), taken (in war)."""
    from fractions import Fraction
    from xylarium.kernel import mindcore as _mc
    a = rec.setdefault("authority", {"granted": "1", "earned": "0", "grown": "0", "taken": "0"})
    from xylarium.kernel import relations
    alive = rec["sender"] in senders or rec["sender"] in relations._peoples(kernel)
    a["granted"] = "1" if alive and not rec.get("taken_seat") else "0"
    a["earned"] = str(sum((Fraction(c["delivers"]) for c in _mc.crystals(rec.get("mind") or {}).values()), Fraction(0)))
    a["grown"] = str(Fraction(kernel.cycle_count - rec["since"], 100))


def mind(kernel: Any, realm: str) -> Optional[Dict[str, Any]]:
    """A realm's steward of record: the senior envoy (a player where one keeps the seat)."""
    out = envoys(kernel, realm)
    m = out[0] if out else None
    if m is not None:
        m["player"] = stats(kernel)["stewards"].get(realm)
        _succeed_envoy(kernel, m)
    return m


def _succeed_envoy(kernel: Any, m: Dict[str, Any]) -> None:
    if m.get("player") is None and kernel.cycle_count - m.get("term_since", m["since"]) >= span_cycles(kernel, m["realm"]):
        from xylarium.kernel import history
        old = m["name"]
        terms = (kernel.cycle_count - m.get("term_since", m["since"])) / max(1e-9, term_cycles(kernel, m["realm"]))
        m["generation"] += max(1, int(terms))                 # every term its seat's clock ran, not one per frame
        m["name"] = _steward_name(kernel, m["realm"] + m["sender"], m["generation"])
        m["term_since"] = kernel.cycle_count
        history.event(kernel, "SUCCESSION", f"{m['name']} succeeds {old} as steward of {realm_name(m['realm'])}",
                      cause="a steward's term is over; its sender's line goes on", data={"steward": m["id"]})


def _steward_name(kernel: Any, realm: str, generation: int) -> str:
    from xylarium.kernel import scheduler
    from xylarium.kernel.natives import person_name
    return person_name(scheduler.rng(kernel, "steward", realm, generation))


STEWARD_BOOKS = ("young", "lives", "holds", "power")       # the order a steward attends to them
STEWARD_VOCABULARY = {"young": ("ceasefire", "pact"), "lives": ("pact", "ceasefire"), "holds": ("release",),
                      "power": ("ceasefire",)}


def _pair_site(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


def books(kernel: Any, realm: str) -> mc.Chain:
    """A realm as its steward measures it, exactly, per book (never summed), its sites the realm's peoples and pairs:
      young  lives taken from a people not yet among the stars, by another (per pair)
      lives  lives taken between two peoples (per pair)
      holds  how dark a tributary reads its patron / how bright (per patron and tributary)
      power  a people's arms / its fair share of the realm's arms (per people)
    What a standing ruling already answers is drained: a pair it binds is answered."""
    from xylarium.kernel import annals, relations, reputation, sustenance
    from xylarium.kernel import mindcore as _mc
    mine = peoples_of(kernel, realm)
    need: List[Tuple[str, str, Any]] = []
    have: List[Tuple[str, str, Any]] = []
    for d in disputes(kernel, realm):
        if d["kind"] == "hold" or d["a"] not in mine or d["b"] not in mine:
            continue
        ruled = binds(kernel, d["a"], d["b"]) or binds(kernel, d["a"], d["b"], "pact")
        stake = _stake_since(kernel, d["a"], d["b"], ruled["cycle"]) if ruled else (d.get("stake") or 1)
        if stake:                                              # a ruling answers only what it stops
            young = [p for p in (d["a"], d["b"]) if _young(kernel, p, mine)]
            need.append((_pair_site(d["a"], d["b"]), "young" if young else "lives", stake))
    for sub, tie in relations.ties(kernel).items():
        sup = tie["patron"]
        if sub in mine and sup in mine and not binds(kernel, sub, sup, "release"):
            r = reputation.read(kernel, sub, sup)
            if r is not None:
                need.append((_pair_site(sup, sub), "holds", _mc.q(max(0.0, -r))))
                have.append((_pair_site(sup, sub), "holds", _mc.q(max(0.0, r))))
    arms = {who: sum(sustenance._strength(w) for w in worlds) for who, worlds in mine.items()}
    if arms:
        fair = _mc.q(sum(arms.values())) / len(arms)
        for who, a in arms.items():
            need.append((who, "power", a))
            have.append((who, "power", fair))
    return _mc.residual(_mc.measure(need), _mc.measure(have))


def _stake_since(kernel: Any, a: str, b: str, since: int) -> float:
    """Lives taken between two peoples since a cycle (the ledger): what a ruling has not stopped."""
    from xylarium.kernel import history
    out = 0.0
    for e in history.of_people(kernel, a):
        if e.get("kind") in CONTESTED and e.get("cycle", 0) >= since and \
                b in {party(kernel, x) for x in e.get("actors", [])}:
            out += float(e.get("magnitude") or 0) + 1.0
    return out


def _young(kernel: Any, people: str, worlds_by: Dict[str, List[Any]]) -> bool:
    from xylarium.kernel import mastery
    return people in worlds_by and not mastery.crossed(kernel, people)


def _victim(kernel: Any, hegemon: str, realm: str) -> Optional[str]:
    """The people in its realm a hegemon has most lately struck."""
    from xylarium.kernel import history
    mine = set(peoples_of(kernel, realm))
    for e in reversed(history.of_people(kernel, hegemon)):
        if e.get("kind") in CONTESTED:
            for a in e.get("actors", []):
                p = party(kernel, a)
                if p != hegemon and p in mine:
                    return p
    return None


def season(kernel: Any) -> List[str]:
    """Once a year each realm's steward-mind measures its realm (books), seals what its last ruling delivered,
    and rules on the residual's lead - one ruling a year: a steward's attention is the bound. What reaches beyond
    its realm goes up once. A realm a player keeps is the player's to rule."""
    from xylarium.kernel import mindcore as _mc
    if (kernel.cycle_count // 25) % 4:
        return []
    logs: List[str] = []
    for realm in realms(kernel):
        m0 = mind(kernel, realm)
        if m0 is None or m0.get("player"):
            continue                                         # no steward sent yet - or a player keeps the realm
        for m in envoys(kernel, realm):
            _succeed_envoy(kernel, m)
            _envoy_deed(kernel, realm, m, logs)
        mine = set(peoples_of(kernel, realm))                  # sending up is not a ruling: it is done every year
        pending = {frozenset((r["a"], r["b"])) for r in stats(kernel)["appeals"]}
        beyond = [d for d in disputes(kernel, realm)                # what reaches past its realm goes up, once
                  if not (d["a"] in mine and d["b"] in mine) and frozenset((d["a"], d["b"])) not in pending
                  and not binds(kernel, d["a"], d["b"])]
        if beyond:
            d = max(beyond, key=lambda d: float(d.get("stake") or 0.0))
            _rule(kernel, realm, m0["id"], "ceasefire", d["a"], d["b"])
    return logs


def _envoy_deed(kernel: Any, realm: str, m: Dict[str, Any], logs: List[str]) -> None:
    """One steward's one ruling a year: its realm's books, its own mind."""
    from xylarium.kernel import mindcore as _mc
    mm = m.setdefault("mind", _mc.new_mind())
    res = books(kernel, realm)
    _mc.seal(mm, res)
    left = dict(res)
    entry = _mc.lead(left, STEWARD_BOOKS, deepest=True)
    while entry is not None and entry[1] == "power" and _victim(kernel, entry[0], realm) is None:
        left.pop(entry)                                      # power that has struck no one: no ruling answers it -
        entry = _mc.lead(left, STEWARD_BOOKS, deepest=True)  # carried; the steward attends the next deficit
    if entry is not None:
        site, book = entry
        owed = res[entry]
        role = "people" if book == "power" else "pair"
        recalled = _mc.recall(mm, entry, owed, role)
        barred = _mc.walls(mm, _mc.shape(entry, owed, role))
        order = ([recalled] if recalled else []) + [d for d in STEWARD_VOCABULARY[book] if d != recalled]
        if book == "power":
            victim = _victim(kernel, site, realm)
            a, b = (site, victim) if victim else (None, None)
        else:
            a, b = site.split("|", 1)
        for kind in order:
            if kind in barred or a is None:
                continue
            res_r = _rule(kernel, realm, m["id"], kind, a, b)
            if res_r.get("ok"):
                _mc.intend(mm, entry, owed, kind, role)
                m["ruled"] += 1
                logs.append(f"[STEWARD] {m['name']} of {realm_name(realm)} rules a {kind} between the "
                            f"{a.split(':', 1)[-1]} and the {b.split(':', 1)[-1]} ({book}).")
                break


def appeal(kernel: Any, sovereign: Dict[str, Any], against: str) -> Optional[Dict[str, Any]]:
    """A sovereign whose people's need a ruling blocks takes it up the chain: the ruling stands, appealed, until a
    progenitor seals or the ancients' laws let it lapse (its span runs)."""
    from xylarium.kernel import history
    st = stats(kernel)
    rec = next((r for r in st["rulings"].values() if {r["a"], r["b"]} == {party(kernel, sovereign["people"]),
                                                                          party(kernel, against)}), None)
    if rec is None or rec.get("sealed") or any(r["id"] == rec["id"] for r in st["appeals"]):
        return None
    st["appeals"].append(dict(rec, appealed_by=sovereign["id"]))
    history.event(kernel, "APPEAL", f"{sovereign['name']} of the {sovereign['polity']} appeals the {rec['kind']} "
                  f"to the progenitors", actors=[sovereign["people"], against], cause="its people's need is barred",
                  data={"ruling": rec["id"]})
    return rec


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"stewards": dict(st["stewards"]), "rulings": len(st["rulings"]), "appeals": len(st["appeals"]),
            "minds": {r: st["envoys"][k]["name"] for r, k in st.get("minds", {}).items() if k in st.get("envoys", {})},
            "envoys": {k: {"name": v["name"], "realm": v["realm"], "sender": v["sender"], "ruled": v["ruled"]}
                       for k, v in st.get("envoys", {}).items()}}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="stewardship",
    state=lambda: {"stewards": {}, "rulings": {}, "appeals": [], "next": 0, "minds": {}},
    season=season,
    summary=summary,
))
