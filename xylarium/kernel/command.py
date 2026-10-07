"""
Xylarium command: the higher seats' hands on the lower - what a player in each seat may order of the seats beneath
it, and what those seats may answer. The AI seats do the same by their minds (stewardship.py, dynasties.py,
realmwars.py); a player's seat is skipped by them and acts only by these orders.

  PROGENITOR (T0)   send a steward of its line to a realm its reach covers (granted); recall one; in a fold war,
                    fold or yield; handle its throats (open, tolled, guarded, closed); forge a throat from a mouth
                    its network holds to a system (transit.py), paid from its network's banked energy
  STEWARD (T2)      claim another realm (a realm war), withdraw a claim; grant authority to a house of its realm
  SOVEREIGN (T3)    order its house's duty (the book its captains are set to); commission a captain in its systems;
                    dismiss one; found an exchange at a port of its worlds (business.py)
  CAPTAIN (T4-T9)   swear to a house whose system it is in; forswear (ronin); keep a ronin's way - solo, band,
                    pirate

An AI subordinate keeps its agency: a captain commissioned to a duty its own mind has walled refuses (it has learned
that book does not pay it), a raider by calling serves no house, and a steward may not be sent beyond its line's
reach. Every order returns {"ok": bool, "why"/...} and is written in the history.
"""

from typing import Any, Dict, Optional, Tuple

ORDERS = {"progenitor": ("send", "recall", "fold", "handle", "forge"), "steward": ("claim", "withdraw", "grant"),
          "steward_ascent": ("ascend", "quarantine", "fortify"),
          "sovereign": ("order", "commission", "dismiss", "exchange"), "captain": ("swear", "forswear", "way")}


def _no(why: str) -> Dict[str, Any]:
    return {"ok": False, "why": why}


# ---------------------------------------------------------------------- the progenitor
def line_of(kernel: Any, pid: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """A progenitor player's line: its ancient people's (the elders', in a settled universe). The seat is marked so
    the line acts only by its player's orders."""
    from xylarium.kernel import ages, board, roles, sustenance
    if roles.role_of(kernel, pid) != "progenitor":
        return None
    lines = board.progenitors(kernel)
    home = ages.homeworld(kernel, pid) if "ages" in kernel.state else None
    who = sustenance.people_of(home) if home is not None else None
    key = who if who in lines else ("elders" if "elders" in lines else None)
    if key is None:
        return None
    lines[key]["player"] = pid
    return key, lines[key]


def send(kernel: Any, pid: str, realm: str) -> Dict[str, Any]:
    from xylarium.kernel import stewardship
    held = line_of(kernel, pid)
    if held is None:
        return _no("you hold no progenitor line")
    who, line = held
    if realm not in stewardship.realms(kernel):
        return _no(f"no realm {realm}")
    if f"{who}@{realm}" in stewardship.stats(kernel).setdefault("envoys", {}):
        return _no("your line already keeps a steward there")
    if not stewardship.covers(kernel, who, realm):
        return _no("that realm is neither your network's nor a federation partner's")
    rec = stewardship.send(kernel, who, line, realm)
    return {"ok": True, "steward": rec["name"], "realm": realm}


def recall(kernel: Any, pid: str, realm: str) -> Dict[str, Any]:
    from xylarium.kernel import history, realmwars, stewardship
    held = line_of(kernel, pid)
    if held is None:
        return _no("you hold no progenitor line")
    key = f"{held[0]}@{realm}"
    env = stewardship.stats(kernel).setdefault("envoys", {})
    if key not in env:
        return _no("your line keeps no steward there")
    rec = env.pop(key)
    if "realmwars" in kernel.state:
        w = realmwars.war_of(kernel, key)
        if w is not None:
            realmwars._end(kernel, w, "withdrawn", "its steward is recalled")
    history.event(kernel, "STEWARD_RECALLED", f"{rec['name']} is recalled from {stewardship.realm_name(realm)}",
                  cause=f"by {held[1]['name']}", data={"steward": rec["id"]})
    return {"ok": True, "steward": rec["name"]}


def fold(kernel: Any, pid: str, war_id: str, deed: str = "fold") -> Dict[str, Any]:
    from xylarium.kernel import realmwars
    held = line_of(kernel, pid)
    if held is None:
        return _no("you hold no progenitor line")
    w = realmwars.stats(kernel)["wars"].get(war_id)
    if w is None or w["status"] != "open" or not w.get("escalated") or held[0] not in w.get("lines", []):
        return _no("no fold war of yours by that id")
    if deed not in realmwars.FOLD_VOCABULARY:
        return _no(f"a line may {' or '.join(realmwars.FOLD_VOCABULARY)}")
    w.setdefault("player_deeds", {})[held[0]] = deed
    return {"ok": True, "war": war_id, "deed": deed}


def handle(kernel: Any, pid: str, how: str) -> Dict[str, Any]:
    """How a progenitor's people handles its throats - its choice, for all it holds."""
    from xylarium.kernel import transit
    held = line_of(kernel, pid)
    if held is None:
        return _no("you hold no progenitor line")
    if how not in ("open", "tolled", "guarded", "closed"):
        return _no("a throat is open, tolled, guarded or closed")
    transit.stats(kernel)["handling"][held[0]] = how
    for w in transit.stats(kernel)["worms"].values():
        if w["owner"] == held[0]:
            w["handling"] = how
    from xylarium.kernel import fibres
    fibres._bump(kernel)
    return {"ok": True, "handling": how}


def forge(kernel: Any, pid: str, anchor: int, target: int) -> Dict[str, Any]:
    """A progenitor punches a throat from a mouth its network holds to a system - if its banked energy pays."""
    from xylarium.kernel import spheres, transit
    held = line_of(kernel, pid)
    if held is None:
        return _no("you hold no progenitor line")
    who = held[0]
    if who not in transit.stats(kernel)["masters"]:
        return _no("your people has not mastered the bounce")
    mine = set(spheres.stats(kernel)["nets"].get(who, {}).get("held", []))
    if anchor not in transit.mouths(kernel) or (anchor not in mine and anchor != transit.MOUTH_BASE):
        return _no("no mouth of yours there")
    if target not in kernel.sectors:
        return _no("no such system")
    w = transit.forge(kernel, who, anchor, target, [])
    if w is None:
        need = transit.forge_cost_j(kernel, who, anchor, target)
        have = float(spheres.stats(kernel)["nets"].get(who, {}).get("bank_j", 0.0))
        return _no(f"your network has banked {have:.3g} J of the {need:.3g} J it needs")
    return {"ok": True, "throat": w}


# ---------------------------------------------------------------------- the steward
def claim(kernel: Any, pid: str, against: str) -> Dict[str, Any]:
    from xylarium.kernel import realmwars, stewardship
    realm = stewardship.realm_held(kernel, pid)
    if realm is None:
        return _no("you keep no realm")
    if against == realm or against not in stewardship.realms(kernel):
        return _no("claim another realm")
    by = f"seat:{realm}"
    if realmwars.war_of(kernel, by) is not None:
        return _no("you already press a claim")
    from xylarium.kernel import spheres
    taker = spheres.presence(kernel, realm)
    target = spheres.stats(kernel)["realms"].get(against, {})
    if taker is None or spheres.presence(kernel, against) in (None, taker):
        return _no("no people of another network holds that realm")
    w = realmwars.declare(kernel, realm, against, taker, target.get("seat"), by=by, sender=f"seat:{pid}")
    return {"ok": True, "war": w["id"]}


def withdraw(kernel: Any, pid: str) -> Dict[str, Any]:
    from xylarium.kernel import realmwars, stewardship
    realm = stewardship.realm_held(kernel, pid)
    w = realmwars.war_of(kernel, f"seat:{realm}") if realm else None
    if w is None:
        return _no("you press no claim")
    realmwars._end(kernel, w, "withdrawn", "its steward withdraws it")
    return {"ok": True, "war": w["id"]}


def grant(kernel: Any, pid: str, house: str) -> Dict[str, Any]:
    from xylarium.kernel import dynasties, history, stewardship
    realm = stewardship.realm_held(kernel, pid)
    h = _house_named(kernel, house)
    if realm is None:
        return _no("you keep no realm")
    if h is None or h["realm"] != realm:
        return _no("no house of your realm by that name")
    h["grants"] = h.get("grants", 0) + 1
    history.event(kernel, "AUTHORITY_GRANTED", f"The steward of {stewardship.realm_name(realm)} grants the House of "
                  f"{h['name']} its authority", actors=[h["people"]], cause="granted from above",
                  data={"house": h["line"]})
    return {"ok": True, "house": h["name"], "granted": h["grants"]}


def ascend(kernel: Any, pid: str, who: str, verdict: str = "ascended") -> Dict[str, Any]:
    """A player who keeps a realm rules on a people that petitions it: ascended among the stars, or held at home."""
    from xylarium.kernel import ascendance, stewardship
    realm = stewardship.realm_held(kernel, pid)
    rec = ascendance.stats(kernel)["of"].get(who)
    if realm is None or rec is None or rec["realm"] != realm:
        return _no("no people petitions your realm by that name")
    return ascendance.rule(kernel, who, verdict, pid)


def fortify(kernel: Any, pid: str, sector: int, units: float) -> Dict[str, Any]:
    """A player who keeps a realm orders works at one of its borders, paid from its keeper's treasury."""
    from xylarium.kernel import borders, spheres, stewardship
    realm = stewardship.realm_held(kernel, pid)
    if realm is None or spheres.owner(kernel, sector) != realm:
        return _no("that system is not of your realm")
    built = borders._fortify(kernel, realm, sector, units, [])
    return {"ok": built > 0, "built": built} if built > 0 else _no("the keeper would not, or could not, build it")


def _house_named(kernel: Any, name: str) -> Optional[Dict[str, Any]]:
    from xylarium.kernel import dynasties
    if "dynasties" not in kernel.state:
        return None
    for line, h in dynasties.standing(kernel).items():
        if name in (line, h["name"]) or h["name"].lower() == str(name).lower():
            return h
    return None


# ---------------------------------------------------------------------- the sovereign
def house_of(kernel: Any, pid: str) -> Optional[Dict[str, Any]]:
    """The house of a sovereign player's line (its seat is a polity's sovereign record held by the player)."""
    from xylarium.kernel import dynasties, polity
    if "dynasties" not in kernel.state:
        return None
    for s in polity.sovereigns(kernel).values():
        if s.get("player") == pid and not s.get("ended"):
            return dynasties.houses(kernel).get(s["line"])
    return None


def order(kernel: Any, pid: str, book: Optional[str]) -> Dict[str, Any]:
    from xylarium.kernel import polity
    h = house_of(kernel, pid)
    if h is None or h.get("ended"):
        return _no("your line is not yet a house")
    if book is not None and book not in polity.BOOKS:
        return _no(f"a duty is one of {', '.join(polity.BOOKS)}")
    h["ordered"] = book                                       # None: its captains follow your realm's own lead again
    from xylarium.kernel import dynasties
    h["duty"] = dynasties._duty(kernel, h)                     # it reaches its captains at once
    h["work"] = dynasties.family_for(kernel, h)
    return {"ok": True, "house": h["name"], "duty": book}


def commission(kernel: Any, pid: str, captain_id: str) -> Dict[str, Any]:
    from fractions import Fraction
    from xylarium.kernel import dynasties, history, mindcore as mc, offices
    h = house_of(kernel, pid)
    c = kernel.captains.get(captain_id)
    if h is None or h.get("ended"):
        return _no("your line is not yet a house")
    if c is None:
        return _no("no such captain")
    if dynasties._held(kernel).get(c.sector_id) != h["line"]:
        return _no("that captain is not in a system your house holds")
    st = dynasties.stats(kernel)
    if st["serves"].get(captain_id) == h["line"]:
        return _no("it already serves you")
    if c.is_ai:
        book = h.get("work")
        walled = book is not None and book in mc.walls(offices.mind(kernel, c), mc.shape(("self", book), Fraction(1)))
        if dynasties._raider(c) or dynasties._lawless(kernel, c) or walled:
            history.event(kernel, "REFUSAL", f"{c.name} refuses the House of {h['name']}'s commission",
                          actors=[f"captain:{captain_id}", h["people"]],
                          cause="a raider serves no house" if dynasties._raider(c) else "that duty does not pay it",
                          data={"house": h["line"]})
            return _no(f"{c.name} refuses")
    else:
        return _no("a player's captain swears by its own choice")
    st["serves"][captain_id] = h["line"]
    st["ronin"].pop(captain_id, None)
    history.event(kernel, "COMMISSION", f"{c.name} takes the House of {h['name']}'s commission",
                  actors=[f"captain:{captain_id}", h["people"]], cause="commissioned by its sovereign",
                  data={"house": h["line"]})
    return {"ok": True, "captain": c.name, "house": h["name"]}


def dismiss(kernel: Any, pid: str, captain_id: str) -> Dict[str, Any]:
    from xylarium.kernel import dynasties
    h = house_of(kernel, pid)
    st = dynasties.stats(kernel) if "dynasties" in kernel.state else {"serves": {}}
    if h is None or st["serves"].get(captain_id) != h["line"]:
        return _no("that captain does not serve your house")
    st["serves"].pop(captain_id)
    return {"ok": True, "captain": captain_id}


# ---------------------------------------------------------------------- the captain
def swear(kernel: Any, pid: str, house: str) -> Dict[str, Any]:
    from xylarium.kernel import dynasties, history
    h = _house_named(kernel, house)
    me = kernel.get_player(pid)
    if h is None:
        return _no("no standing house by that name")
    if me is None or dynasties._held(kernel).get(me.sector_id) != h["line"]:
        return _no("you must be in a system that house holds to swear to it")
    st = dynasties.stats(kernel)
    st["serves"][pid] = h["line"]
    st["ronin"].pop(pid, None)
    history.event(kernel, "COMMISSION", f"{me.name} swears to the House of {h['name']}",
                  actors=[f"captain:{pid}", h["people"]], cause="by its own choice", data={"house": h["line"]})
    return {"ok": True, "house": h["name"], "duty": h.get("duty")}


def forswear(kernel: Any, pid: str) -> Dict[str, Any]:
    from xylarium.kernel import dynasties
    st = dynasties.stats(kernel)
    if st["serves"].pop(pid, None) is None:
        return _no("you serve no house")
    st["ronin"][pid] = {"way": "solo"}
    return {"ok": True, "way": "solo"}


def way(kernel: Any, pid: str, how: str) -> Dict[str, Any]:
    """A ronin's way: solo; pirate; or band - with another ronin in the same system (its band, or a new one)."""
    from xylarium.kernel import dynasties
    st = dynasties.stats(kernel)
    me = kernel.get_player(pid)
    if pid in st["serves"]:
        return _no("you serve a house: forswear it first")
    if how not in ("solo", "pirate", "band"):
        return _no("a ronin's way is solo, band or pirate")
    for b in st["bands"].values():
        if pid in b["members"]:
            b["members"].remove(pid)
    if how == "band":
        here = [cid for cid, c in kernel.captains.items() if cid != pid and c.sector_id == me.sector_id
                and cid not in st["serves"] and st["ronin"].get(cid, {}).get("way") != "pirate"]
        if not here:
            return _no("no ronin here to band with")
        bid = st["ronin"].get(here[0], {}).get("band")
        if bid not in st["bands"]:
            st["next"] += 1
            bid = f"B-{st['next']:05d}"
            st["bands"][bid] = {"members": [here[0]], "since": kernel.cycle_count, "sector": me.sector_id}
            st["ronin"][here[0]] = {"way": "band", "band": bid}
        st["bands"][bid]["members"].append(pid)
        st["ronin"][pid] = {"way": "band", "band": bid}
        return {"ok": True, "way": "band", "band": bid}
    st["ronin"][pid] = {"way": how}
    return {"ok": True, "way": how}


# ---------------------------------------------------------------------- one door for the bridge and the consoles
def exchange(kernel: Any, pid: str, sector: int) -> Dict[str, Any]:
    """A sovereign player founds an exchange at a port of its people's worlds, paying the capital (business.py)."""
    from xylarium.kernel import business, polity
    seat = next((s for s in polity.sovereigns(kernel).values() if s.get("player") == pid and not s.get("ended")), None)
    if seat is None:
        return _no("you hold no sovereign's seat")
    return business.found_exchange(kernel, seat["people"], int(sector))


def dispatch(kernel: Any, pid: str, name: str, **kw: Any) -> Dict[str, Any]:
    fn = {"send": lambda: send(kernel, pid, str(kw.get("realm", ""))),
          "recall": lambda: recall(kernel, pid, str(kw.get("realm", ""))),
          "fold": lambda: fold(kernel, pid, str(kw.get("war", "")), str(kw.get("deed", "fold"))),
          "handle": lambda: handle(kernel, pid, str(kw.get("how", "tolled"))),
          "forge": lambda: forge(kernel, pid, int(kw.get("anchor", 0) or 0), int(kw.get("target", 0) or 0)),
          "claim": lambda: claim(kernel, pid, str(kw.get("realm", ""))),
          "withdraw": lambda: withdraw(kernel, pid),
          "grant": lambda: grant(kernel, pid, str(kw.get("house", ""))),
          "ascend": lambda: ascend(kernel, pid, str(kw.get("people", "")), "ascended"),
          "quarantine": lambda: ascend(kernel, pid, str(kw.get("people", "")), "quarantine"),
          "fortify": lambda: fortify(kernel, pid, int(kw.get("sector", 0) or 0), float(kw.get("units", 0) or 0)),
          "order": lambda: order(kernel, pid, kw.get("book")),
          "commission": lambda: commission(kernel, pid, str(kw.get("captain", ""))),
          "dismiss": lambda: dismiss(kernel, pid, str(kw.get("captain", ""))),
          "exchange": lambda: exchange(kernel, pid, int(kw.get("sector", 0) or 0)),
          "swear": lambda: swear(kernel, pid, str(kw.get("house", ""))),
          "forswear": lambda: forswear(kernel, pid),
          "way": lambda: way(kernel, pid, str(kw.get("way", "solo")))}.get(name)
    return fn() if fn is not None else _no(f"no order '{name}'")


def standing(kernel: Any, pid: str) -> Dict[str, Any]:
    """Where a player stands in the chain: its house or ronin's way (captain), its house (sovereign)."""
    from xylarium.kernel import dynasties
    if "dynasties" not in kernel.state:
        return {}
    st = dynasties.stats(kernel)
    line = st["serves"].get(pid)
    h = dynasties.houses(kernel).get(line) if line else house_of(kernel, pid)
    return {"house": h["name"] if h else None, "duty": h.get("duty") if h else None,
            "ronin": None if line else st["ronin"].get(pid), "houses_here": sorted(
                dynasties.houses(kernel)[l]["name"] for l in {dynasties._held(kernel).get(
                    getattr(kernel.get_player(pid), "sector_id", None))} if l)}
