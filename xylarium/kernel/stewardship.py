"""
Xylarium stewardship: the realms of the 3-sphere, and the stewards (T2) who keep the balance between their peoples.

REALMS. The universe is a closed 3-sphere (sphere.py); a realm is a quadrant of it - a partition laid by the
architects that needs no knowledge of what lives below. A cluster's quadrant is the angle of its point in the
sphere's first plane (home stands at its pole, quadrant 0); inside the home galaxy each cluster-quadrant is cut again
into the galaxy's own four quadrants (Alpha, Beta, Gamma, Delta) by the angle of the disc cell a system was born in
- fixed in the disc's own frame, so a system never changes realm. A realm is named by both cuts.

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
from typing import Any, Dict, List, Optional, Tuple

QUADRANTS = ("Alpha", "Beta", "Gamma", "Delta")
RULINGS = ("ceasefire", "release", "pact")
CONTESTED = ("WAR", "RAID", "CONQUEST", "SUBJUGATION", "REVOLT", "REBELLION")
FRONTIER_FROM = 201             # where charted frontier clusters' sector ids begin (research.mint_frontier_cluster)
RULING_YEARS = 25                # clock years an unsealed ruling stands (declared: a generation of a steward's term)


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "stewardship")


# ---------------------------------------------------------------------- the realms
def sphere_quadrant(point: List[float]) -> int:
    """A point of the 3-sphere's quadrant: the angle in its first plane, in quarters (home's pole is quadrant 0)."""
    a = math.atan2(float(point[1]), float(point[0])) % (2 * math.pi)
    return int(a // (math.pi / 2)) % 4


def galactic_quadrant(kernel: Any, sector_id: int) -> int:
    """The home galaxy's quadrant a system was born in: the angle of its disc cell (fixed in the disc's frame). A
    settled galaxy, which has no disc, is cut once into four blocks of the systems it was laid with; space charted
    after joins a quadrant by the cluster it came in (forty systems each) - so no system ever changes realm."""
    from xylarium.kernel import cosmos
    cell = cosmos.cell_of_sector(kernel, sector_id) if "cosmos" in getattr(kernel, "state", {}) else None
    if cell is not None:
        return int(cosmos.cell_theta(*cell) // (math.pi / 2)) % 4
    if sector_id < FRONTIER_FROM:                         # the galaxy as laid: its systems cut into four blocks
        laid = [i for i in kernel.sectors if i < FRONTIER_FROM] or [1]
        return min(3, (sector_id - 1) * 4 // max(1, max(laid)))
    return ((sector_id - FRONTIER_FROM) // 40) % 4         # a charted frontier cluster (forty systems each)


def realm_of(kernel: Any, sector_id: int) -> str:
    """The realm a system lies in: '<sphere quadrant>.<galactic quadrant>' (the home galaxy is in sphere quadrant 0)."""
    return f"0.{galactic_quadrant(kernel, sector_id)}"


def realm_name(key: str) -> str:
    s, g = key.split(".")
    return f"the {QUADRANTS[int(g)]} Quadrant" + ("" if s == "0" else f" of the {QUADRANTS[int(s)]} sphere-quadrant")


def realms(kernel: Any) -> List[str]:
    return [f"0.{g}" for g in range(4)]


def peoples_of(kernel: Any, realm: str) -> Dict[str, List[Any]]:
    """The peoples whose capital (largest world) lies in the realm, with their worlds."""
    from xylarium.kernel import relations
    out = {}
    for who, worlds in relations._peoples(kernel).items():
        home = max(worlds, key=lambda w: (w.population, w.id))
        if realm_of(kernel, home.sector_id) == realm:
            out[who] = worlds
    return out


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
    horizon = kernel.cycle_count - 100 * RULING_YEARS
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
           "cycle": kernel.cycle_count, "until": kernel.cycle_count + 100 * RULING_YEARS, "sealed": False}
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
                  cause=f"for {RULING_YEARS} years, binding their sovereigns", data={"ruling": rec["id"]})
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
    from xylarium.kernel import clocks, history, roles
    if roles.role_of(kernel, progenitor_id) != "progenitor":
        return {"ok": False, "why": "Only a progenitor seals what is appealed."}
    st = stats(kernel)
    rec = next((r for r in st["appeals"] if r["id"] == ruling_id), None) or \
        next((r for r in st["rulings"].values() if r["id"] == ruling_id), None)
    if rec is None:
        return {"ok": False, "why": f"No ruling {ruling_id}."}
    rec["sealed"] = True
    rec["sealed_by"] = progenitor_id
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
    from xylarium.kernel import alignment, annals, knowledge, relations
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
    return {"realm": realm, "name": realm_name(realm), "steward": steward_of(kernel, realm), "peoples": rows,
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
def mind(kernel: Any, realm: str) -> Dict[str, Any]:
    """A realm's steward as a line: a player where one keeps the seat (the line's own mind yields to it), else the
    realm's own steward-mind - named, serving a term, succeeded, its rulings its memory."""
    st = stats(kernel)
    m = st["minds"].get(realm)
    if m is None:
        st["next"] += 1
        m = st["minds"][realm] = {"id": f"W-{st['next']:05d}", "name": _steward_name(kernel, realm, 1),
                                  "since": kernel.cycle_count, "generation": 1, "realm": realm, "ruled": 0}
    seated = st["stewards"].get(realm)
    m["player"] = seated
    if seated is None and kernel.cycle_count - m["since"] >= 100 * RULING_YEARS:
        from xylarium.kernel import history
        old = m["name"]
        m["generation"] += 1
        m["name"] = _steward_name(kernel, realm, m["generation"])
        m["since"] = kernel.cycle_count
        history.event(kernel, "SUCCESSION", f"{m['name']} succeeds {old} as steward of {realm_name(realm)}",
                      cause="a steward's term is over; the realm's line goes on", data={"steward": m["id"]})
    return m


def _steward_name(kernel: Any, realm: str, generation: int) -> str:
    from xylarium.kernel import scheduler
    from xylarium.kernel.natives import _name
    return _name(scheduler.rng(kernel, "steward", realm, generation))


def _shape(kernel: Any, d: Dict[str, Any]) -> Optional[str]:
    """What a dispute's own shape names: a hold one side bears as a taking (it reads its patron dark) is released;
    lives taken between two whose books mirror (one has what the other lacks) are bound by a pact; lives taken
    otherwise are stopped by a ceasefire. A hold borne willingly names nothing."""
    from xylarium.kernel import polity, reputation
    if d["kind"] == "hold":
        r = reputation.read(kernel, d["b"], d["a"])
        return "release" if r is not None and r < 0 else None
    sa, sb = polity.of_people(kernel, d["a"]), polity.of_people(kernel, d["b"])
    if sa and sb:
        fa, fb = polity.field(kernel, sa[0]), polity.field(kernel, sb[0])
        if any((fa[k] > 0 > fb[k]) or (fb[k] > 0 > fa[k]) for k in polity.BOOKS):
            return "pact"
    return "ceasefire"


def season(kernel: Any) -> List[str]:
    """Once a year each realm's steward-mind hears its realm: of the disputes no ruling yet stands over, the one where
    the most is at stake (lives taken, holds borne) comes first, and its shape names the ruling. One ruling a year:
    a steward's attention is the bound. A realm a player keeps is the player's to rule."""
    if (kernel.cycle_count // 25) % 4:
        return []
    logs: List[str] = []
    for realm in realms(kernel):
        m = mind(kernel, realm)
        if m.get("player"):
            continue
        mine = set(peoples_of(kernel, realm))
        pending = {frozenset((r["a"], r["b"])) for r in stats(kernel)["appeals"]}
        open_ = [d for d in disputes(kernel, realm)
                 if d["a"] in mine and d["b"] in mine and frozenset((d["a"], d["b"])) not in pending
                 and not binds(kernel, d["a"], d["b"]) and not binds(kernel, d["a"], d["b"], "pact")
                 and not binds(kernel, d["a"], d["b"], "release")]
        beyond = [d for d in disputes(kernel, realm)                # what reaches past its realm goes up, once
                  if not (d["a"] in mine and d["b"] in mine) and frozenset((d["a"], d["b"])) not in pending
                  and not binds(kernel, d["a"], d["b"])]
        if beyond and not open_:
            d = max(beyond, key=lambda d: float(d.get("stake") or 0.0))
            _rule(kernel, realm, m["id"], "ceasefire", d["a"], d["b"])
        open_.sort(key=lambda d: -float(d.get("stake") or d.get("tribute_sol") or 0.0))
        for d in open_:
            kind = _shape(kernel, d)
            if kind is None:
                continue
            res = _rule(kernel, realm, m["id"], kind, d["a"], d["b"])
            if res.get("ok"):
                m["ruled"] += 1
                logs.append(f"[STEWARD] {m['name']} of {realm_name(realm)} rules a {kind} between the "
                            f"{d['a'].split(':', 1)[-1]} and the {d['b'].split(':', 1)[-1]}.")
            break
    return logs


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
            "minds": {r: m["name"] for r, m in st.get("minds", {}).items()}}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="stewardship",
    state=lambda: {"stewards": {}, "rulings": {}, "appeals": [], "next": 0, "minds": {}},
    season=season,
    summary=summary,
))
