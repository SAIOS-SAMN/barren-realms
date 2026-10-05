"""
Xylarium dynasties: the houses that emerge in a realm, and the captains who serve them - or serve none.

A HOUSE is a sovereign line (polity.py: a seat's successors and the polities born of it) that has become more than one
reign: it emerges when its authority has a source beyond its founding - and authority, here as for the stewards, is
kept by where it comes from, never summed:

  granted  what is given from above: the stewards' rulings that stand over its people
  earned   what its sovereigns' deeds measurably delivered (their minds' crystals)
  grown    reigns held, every polity of the line together
  taken    what it seized: the wars its sovereigns opened, the worlds its captains took

A house is of the realm its first seat lies in. It has one duty a year - its senior sovereign's lead (the first
deficit in that mind's need order) - and it hands that duty to its captains: a captain in its service puts the
office book that answers it before its own (offices.choose). That is the higher tier commanding the lower.

A CAPTAIN who serves no house is RONIN, and has agency. Where a house holds the system a ronin is in, the house offers
it a commission; the ronin takes it unless the duty is one its own mind has walled (it learned that book does not pay
it), or it is a raider by calling. A ronin that does not serve keeps one of three ways:

  band    ronin in one system whose offices differ make common cause (the difference supplies: each is what the
          other lacks)
  pirate  a raider by calling - or one whose every lawful book is walled: what is left to it is taking
  solo    its own ship, its own way

A house whose line ends releases its captains: they are ronin again.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional

from xylarium.kernel import mindcore as mc

DUTY = {"food": "haul", "room": "works", "security": "haul", "wealth": "trade", "standing": "unknown"}
TAKEN = ("CONQUEST", "SUBJUGATION")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "dynasties")


# ---------------------------------------------------------------------- houses
def _lines(kernel: Any) -> Dict[str, List[Dict[str, Any]]]:
    from xylarium.kernel import polity
    out: Dict[str, List[Dict[str, Any]]] = {}
    for s in polity.sovereigns(kernel).values():
        out.setdefault(s["line"], []).append(s)
    return out


def authority(kernel: Any, recs: List[Dict[str, Any]], serving: List[str], grants: int = 0) -> Dict[str, str]:
    """A line's authority by its sources (exact, as strings in state); `grants`: a steward's own grants to it."""
    from xylarium.kernel import history, polity, stewardship
    peoples = {s["people"] for s in recs}
    granted = sum(1 for r in stewardship.stats(kernel)["rulings"].values()
                  if (r["a"] in peoples or r["b"] in peoples) and stewardship.binds(kernel, r["a"], r["b"])) + grants
    earned = sum((Fraction(c["delivers"]) for s in recs for c in mc.crystals(s.get("mind") or {}).values()),
                 Fraction(0))
    grown = sum(s["generation"] for s in recs)
    ids = {s["id"] for s in recs}
    wars = sum(1 for t in polity.stats(kernel)["treaties"].values()
               if t.get("kind") == "war" and t.get("by") in ids)
    took = sum(1 for c in serving for e in history.of_people(kernel, f"captain:{c}") if e.get("kind") in TAKEN)
    return {"granted": str(granted), "earned": str(earned), "grown": str(grown), "taken": str(wars + took)}


def houses(kernel: Any) -> Dict[str, Dict[str, Any]]:
    return stats(kernel)["houses"]


def standing(kernel: Any) -> Dict[str, Dict[str, Any]]:
    return {k: h for k, h in houses(kernel).items() if not h.get("ended")}


def _attend(kernel: Any) -> List[str]:
    """Houses emerge from the lines that have outgrown one reign, are kept in step with them, and end with them."""
    from xylarium.kernel import history, polity, stewardship
    st = stats(kernel)
    logs = []
    lines = _lines(kernel)
    for line, recs in sorted(lines.items()):
        live = [s for s in recs if not s.get("ended")]
        h = st["houses"].get(line)
        serving = [c for c, l in st["serves"].items() if l == line]
        if h is not None:
            if not live and not h.get("ended"):
                h["ended"] = kernel.cycle_count
                for c in serving:
                    st["serves"].pop(c, None)
                history.event(kernel, "HOUSE_FALLS", f"The House of {h['name']} falls", actors=[h["people"]],
                              cause="its line has no seat left", data={"house": line})
                logs.append(f"[DYNASTY] The House of {h['name']} falls; its captains are ronin.")
            if live:
                h["authority"] = authority(kernel, recs, serving, h.get("grants", 0))
                h["polities"] = [s["id"] for s in live]
            continue
        if not live:
            continue
        a = authority(kernel, recs, serving)
        if Fraction(a["grown"]) <= 1 and not Fraction(a["taken"]) and not Fraction(a["granted"]):
            continue                                          # one reign of one seat: not yet a house
        founder = min(recs, key=lambda s: s["id"])
        seat = min(live, key=lambda s: s["id"])
        cap = polity._polities(kernel).get(seat["realm"], {}).get("capital")
        w = kernel.get_planet(cap) if cap is not None else None
        realm = stewardship.realm_of(kernel, w.sector_id) if w is not None else None
        name = polity._name(kernel, "house", line)
        st["houses"][line] = h = {"line": line, "name": name, "people": founder["people"], "realm": realm,
                                  "founded": kernel.cycle_count, "polities": [s["id"] for s in live],
                                  "authority": a, "duty": None, "mind": mc.new_mind()}
        how = max(("grown", "taken", "granted"), key=lambda k: Fraction(a[k]))
        history.event(kernel, "HOUSE_RISES", f"The House of {name} rises among the {founder['people'].split(':', 1)[-1]}",
                      actors=[founder["people"]], cause=f"authority {how}: its line outgrows one reign",
                      data={"house": line, "realm": realm})
        logs.append(f"[DYNASTY] The House of {name} rises ({how}).")
    return logs


def _duty(kernel: Any, h: Dict[str, Any]) -> Optional[str]:
    """A house's duty this year: what its seated sovereign orders (command.py), else its senior sovereign's lead -
    the book its captains are set to."""
    from xylarium.kernel import polity
    if h.get("ordered"):
        return h["ordered"]
    recs = [polity.sovereigns(kernel)[sid] for sid in h["polities"] if sid in polity.sovereigns(kernel)]
    if not recs:
        return None
    senior = min(recs, key=lambda s: (s["since"], s["id"]))
    res = polity.chain(kernel, senior, {senior["id"]: polity.field(kernel, senior)})
    lead = mc.lead(res, polity.BOOKS)
    return lead[1] if lead else None


def duty_of(kernel: Any, captain_id: str) -> Optional[str]:
    """The office book a captain's house sets it to, if it serves one."""
    if "dynasties" not in getattr(kernel, "state", {}):
        return None
    line = stats(kernel)["serves"].get(str(captain_id))
    h = houses(kernel).get(line) if line else None
    return DUTY.get(h["duty"]) if h and h.get("duty") and not h.get("ended") else None


# ---------------------------------------------------------------------- captains: service or the ronin's ways
def _held(kernel: Any) -> Dict[int, str]:
    """The systems each standing house holds (its polities' worlds)."""
    from xylarium.kernel import polity
    out: Dict[int, str] = {}
    pols = polity._polities(kernel)
    for line, h in standing(kernel).items():
        for sid in h["polities"]:
            rec = polity.sovereigns(kernel).get(sid)
            for wid in (pols.get(rec["realm"], {}).get("worlds", []) if rec else []):
                w = kernel.get_planet(wid)
                if w is not None:
                    out.setdefault(w.sector_id, line)
    return out


def _raider(captain: Any) -> bool:
    return str(getattr(getattr(captain, "personality", None), "value", "")) == "pirate"


def _lawless(kernel: Any, captain: Any) -> bool:
    """Every lawful book its office reads has been walled: it has tried them and none paid."""
    from xylarium.kernel import offices
    m = offices.mind(kernel, captain)
    order = offices.ORDER.get(offices.office(kernel, captain), offices.ORDER["trader"])
    return all(b in mc.walls(m, mc.shape(("self", b), Fraction(1))) for b in order)


def _commission(kernel: Any, held: Dict[int, str]) -> List[str]:
    """Each house offers its duty to the ronin in its systems; a ronin takes it, unless walled or a raider."""
    from xylarium.kernel import history, offices
    st = stats(kernel)
    logs = []
    for cid in sorted(kernel.captains):
        c = kernel.captains[cid]
        if not c.is_ai:
            continue                                          # a player's captain serves by its own choice
        line = st["serves"].get(cid)
        if line is not None and line in standing(kernel):
            book = DUTY.get(houses(kernel)[line].get("duty") or "")
            if book is not None and book in mc.walls(offices.mind(kernel, c), mc.shape(("self", book), Fraction(1))):
                st["serves"].pop(cid)                         # it has learned its duty does not pay it: it leaves
                history.event(kernel, "REFUSAL", f"{c.name} leaves the House of {houses(kernel)[line]['name']}",
                              actors=[f"captain:{cid}", houses(kernel)[line]["people"]],
                              cause=f"its duty ({book}) does not pay it", data={"house": line})
                logs.append(f"[DYNASTY] {c.name} leaves the House of {houses(kernel)[line]['name']}: ronin.")
            continue
        st["serves"].pop(cid, None)
        offer = held.get(c.sector_id)
        h = houses(kernel).get(offer) if offer else None
        if h is None or _raider(c) or _lawless(kernel, c):
            continue
        book = DUTY.get(h.get("duty") or "", None)
        m = offices.mind(kernel, c)
        if book is not None and book in mc.walls(m, mc.shape(("self", book), Fraction(1))):
            continue                                          # it knows that duty does not pay it: it declines
        st["serves"][cid] = offer
        st["ronin"].pop(cid, None)
        history.event(kernel, "COMMISSION", f"{c.name} takes the House of {h['name']}'s commission",
                      actors=[f"captain:{cid}", h["people"]], cause=f"its duty: {h.get('duty') or 'to serve'}",
                      data={"house": offer})
        logs.append(f"[DYNASTY] {c.name} serves the House of {h['name']}.")
    return logs


def _ways(kernel: Any) -> None:
    """Each ronin's way: a band where ronin of different offices share a system, a pirate if raiding is what is
    left to it, else solo. Bands are kept while their members stay ronin."""
    from xylarium.kernel import offices
    st = stats(kernel)
    by_sector: Dict[int, List[Any]] = {}
    ronin = []
    for cid in sorted(kernel.captains):
        c = kernel.captains[cid]
        if cid in st["serves"]:
            st["ronin"].pop(cid, None)
            continue
        if not c.is_ai:
            continue                                          # a player's ronin keeps the way it chose
        ronin.append(c)
        by_sector.setdefault(c.sector_id, []).append(c)
    for band_id, b in list(st["bands"].items()):
        b["members"] = [m for m in b["members"] if m in kernel.captains and m not in st["serves"]]
        if len(b["members"]) < 2:
            st["bands"].pop(band_id)
    banded = {m: bid for bid, b in st["bands"].items() for m in b["members"]}
    for c in ronin:
        if _raider(c) or _lawless(kernel, c):
            st["ronin"][c.id] = {"way": "pirate"}
            continue
        if c.id in banded:
            st["ronin"][c.id] = {"way": "band", "band": banded[c.id]}
            continue
        here = [o for o in by_sector.get(c.sector_id, []) if o.id != c.id and o.id not in banded
                and not _raider(o) and offices.office(kernel, o) != offices.office(kernel, c)]
        if here:
            st["next"] += 1
            bid = f"B-{st['next']:05d}"
            st["bands"][bid] = {"members": [c.id, here[0].id], "since": kernel.cycle_count, "sector": c.sector_id}
            for m in (c.id, here[0].id):
                banded[m] = bid
                st["ronin"][m] = {"way": "band", "band": bid}
            continue
        st["ronin"][c.id] = {"way": "solo"}


def season(kernel: Any) -> List[str]:
    """Once a year, after the sovereigns' deeds: houses emerge and fall, each sets its duty, commissions are
    offered and taken, and the ronin keep their ways."""
    from xylarium.kernel import polity
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    logs = _attend(kernel)
    for h in standing(kernel).values():
        h["duty"] = _duty(kernel, h)
    logs += _commission(kernel, _held(kernel))
    _ways(kernel)
    return logs


def of_realm(kernel: Any, realm: str) -> List[Dict[str, Any]]:
    st = stats(kernel)
    out = []
    for line, h in standing(kernel).items():
        if h["realm"] == realm:
            out.append({"name": h["name"], "people": h["people"], "duty": h.get("duty"),
                        "authority": dict(h["authority"]), "polities": len(h["polities"]),
                        "captains": sorted(c for c, l in st["serves"].items() if l == line)})
    return out


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    ways: Dict[str, int] = {}
    for r in st["ronin"].values():
        ways[r["way"]] = ways.get(r["way"], 0) + 1
    return {"houses": len(standing(kernel)), "fallen": len(st["houses"]) - len(standing(kernel)),
            "serving": len(st["serves"]), "ronin": ways, "bands": len(st["bands"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="dynasties",
    state=lambda: {"houses": {}, "serves": {}, "ronin": {}, "bands": {}, "next": 0},
    season=season,
    summary=summary,
))
