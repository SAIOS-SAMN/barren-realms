"""
Xylarium realms: territory is claimed by influence, and polities are born, grow, split and die.

  * A realm is a polity: a capital world, its member worlds, and the star systems it claims. Its government is
    its capital's (government.py): claimed systems' starports pay it dues, its stations pay it commercial tax.
  * Claims are influence. Every member world projects its population over the lanes, falling with the square of
    the jumps (pop / (1 + hops)^2, within CLAIM_REACH). A realm claims each system where its influence is the
    strongest and at least CLAIM_MIN_INFLUENCE; where two realms press on the same system the stronger holds it
    and the border is contested. Great powers' territory (factions.py) and the Federation's core are not claimed.
  * Realms emerge. A people becomes a realm when it is spacefaring (the yards of citadel tier DAUGHTER_CITADEL_TIER,
    or daughter worlds of its own); a captain's house becomes one when it holds worlds in two or more systems.
    Members are the worlds of the same people (a civilization's name) or of the same owner.
  * Realms split and die. A member world far from its capital (SECESSION_HOPS or more) whose people stay unhappy
    for SECESSION_SEASONS seasons breaks away and founds its own realm; a realm with no worlds is dissolved.
  * The baseline board is born with its realms established (REALMS_AT_GENESIS): every sovereign civilization is a
    realm from the first day, claiming by the same law. A fresh board (False) starts empty and lets them emerge.
"""

from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import DAUGHTER_CITADEL_TIER
from xylarium.kernel import topology

REALMS_AT_GENESIS = True
CLAIM_REACH = 3                  # jumps a world's influence reaches
CHARTER_REACH = 2                # the baseline board's historical borders: systems this near a capital
CLAIM_MIN_INFLUENCE = 1500       # influence (people / (1+hops)^2) to claim a system
SECESSION_HOPS = 4               # a member this far from its capital can break away...
SECESSION_MORALE = 35            # ...when its people are this unhappy...
SECESSION_SEASONS = 4            # ...for this many seasons running
_STYLE = [(0.3, "Concord"), (-0.1, "Commonwealth"), (-0.4, "Dominion"), (-9.0, "Hegemony")]


def realms(kernel: Any) -> Dict[str, Dict[str, Any]]:
    return state.of(kernel, "realms")["realms"]


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "realms")["stats"]


def claims(kernel: Any) -> Dict[int, str]:
    return state.of(kernel, "realms")["claims"]


def claims_version(kernel: Any) -> int:
    """Advances whenever the claims are redrawn (jurisdiction caches key on it)."""
    return state.of(kernel, "realms")["claims_version"]


def realm_of_sector(kernel: Any, sector_id: int) -> Optional[Dict[str, Any]]:
    rid = claims(kernel).get(sector_id)
    return realms(kernel).get(rid) if rid else None


def capital(kernel: Any, realm: Dict[str, Any]) -> Optional[Any]:
    p = kernel.get_planet(realm["capital"])
    return p if (p is not None and p.population > 0) else None


# ---------------------------------------------------------------------- who belongs
def _people(kernel: Any, planet: Any) -> Optional[Tuple[str, str]]:
    """The polity a world belongs to by birth: ('civ', name) for an unowned people, ('house', owner) for a
    captain's colonies. Great powers' worlds belong to the great powers, not to realms."""
    if planet.population <= 0 or getattr(planet, "natives", None) or getattr(planet, "faction_id", None):
        return None
    civ = getattr(planet, "civilization", None)
    if planet.owner_id:
        return "house", planet.owner_id
    from xylarium.kernel.government import FOUNDING_PEOPLES
    if civ is not None and not getattr(civ, "faction_id", None) and civ.name not in FOUNDING_PEOPLES:
        return "civ", civ.name
    return None


def _members(kernel: Any) -> Dict[Tuple[str, str], List[Any]]:
    groups: Dict[Tuple[str, str], List[Any]] = {}
    for sec in kernel.sectors.values():
        for p in sec.planets:
            key = _people(kernel, p)
            if key is not None:
                groups.setdefault(key, []).append(p)
    return groups


def _eligible(kernel: Any, key: Tuple[str, str], worlds: List[Any], genesis: bool) -> bool:
    if key[0] == "house":
        return len({w.sector_id for w in worlds}) >= 2
    if genesis:
        return True
    return any(w.citadel_level >= DAUGHTER_CITADEL_TIER or w.metropole_id for w in worlds) or len(worlds) >= 2


def _name(kernel: Any, key: Tuple[str, str], seat: Any) -> str:
    civ = getattr(seat, "civilization", None)
    align = float(getattr(civ, "alignment", 0.0) or 0.0) if key[0] == "civ" else \
        float(getattr(kernel.captains.get(key[1]), "cosmic_alignment", 0.0) or 0.0)
    style = next(s for t, s in _STYLE if align >= t)
    base = key[1] if key[0] == "civ" else (getattr(kernel.captains.get(key[1]), "name", key[1]).split()[-1] + " House")
    return f"{base} {style}"


def found(kernel: Any, key: Tuple[str, str], worlds: List[Any], note: str = "") -> Dict[str, Any]:
    seat = max(worlds, key=lambda w: (w.population, w.id))
    rid = f"REALM-{seat.id}"
    realm = {"id": rid, "name": _name(kernel, key, seat), "kind": key[0], "people": key[1], "capital": seat.id,
             "worlds": [w.id for w in worlds], "systems": [], "founded": kernel.cycle_count, "unrest": {}}
    realms(kernel)[rid] = realm
    stats(kernel)["founded"] += 1
    from xylarium.kernel import primordial
    primordial.first(kernel, "first_realm", realm["name"])
    if len(worlds) > 1:
        primordial.first(kernel, "first_multiworld_realm", realm["name"])
    chron = getattr(kernel, "chronicle", None)
    if chron is not None and kernel.cycle_count > 0:
        chron.record(kernel, "REALM", seat.id, realm["name"], f"The Founding of the {realm['name']}",
                     f"From {seat.name} the {realm['name']} declares itself: {len(worlds)} world(s) under one "
                     f"government. {note}".strip(), sector_id=seat.sector_id, tags=["realm", "polity"])
    return realm


# ---------------------------------------------------------------------- the season
def _claim(kernel: Any) -> None:
    """Every system goes to the realm with the strongest influence there - a realm's own worlds' systems at any
    strength, others only where its influence reaches CLAIM_MIN_INFLUENCE."""
    fm = kernel.factions
    inf: Dict[int, Dict[str, float]] = {}
    home: Dict[int, set] = {}
    charters = {sid: rid for rid, r in realms(kernel).items() for sid in r.get("charter", [])}
    for sid, rid in charters.items():
        inf.setdefault(sid, {}).setdefault(rid, 0.0)
    for rid, realm in realms(kernel).items():
        for pid in realm["worlds"]:
            w = kernel.get_planet(pid)
            if w is None or w.population <= 0:
                continue
            home.setdefault(w.sector_id, set()).add(rid)
            for sid, hops in topology.hops(kernel, w.sector_id, CLAIM_REACH).items():
                sec = kernel.sectors[sid]
                if getattr(sec, "kind", "") != "SYSTEM" or fm.owner_of(sid) in ("IMPERIUM", "ZEALOT") \
                        or sec.security.value == "FEDERATION":
                    continue                           # great powers' territory and the Federation's core
                by = inf.setdefault(sid, {})
                by[rid] = by.get(rid, 0.0) + w.population / (1 + hops) ** 2
    new: Dict[int, str] = {}
    contested = 0
    for sid, by in inf.items():
        ranked = sorted(by.items(), key=lambda kv: (-kv[1], kv[0]))
        chartered = charters.get(sid)
        if chartered in realms(kernel) and ranked[0][1] < CLAIM_MIN_INFLUENCE:
            new[sid] = chartered                   # historical borders hold until a rival's influence takes them
            continue
        if ranked[0][1] < CLAIM_MIN_INFLUENCE and ranked[0][0] not in home.get(sid, ()):
            continue
        new[sid] = ranked[0][0]
        if len(ranked) > 1 and ranked[1][1] >= CLAIM_MIN_INFLUENCE:
            contested += 1
    for realm in realms(kernel).values():
        realm["systems"] = sorted(sid for sid, rid in new.items() if rid == realm["id"])
    rec = state.of(kernel, "realms")
    rec["claims"] = new
    rec["claims_version"] += 1
    stats(kernel)["contested"] = contested


def quarter(kernel: Any, genesis: bool = False) -> List[str]:
    """Members are counted, peoples become realms, unhappy far worlds break away, empty realms dissolve, and every
    system is claimed by influence."""
    logs: List[str] = []
    st = stats(kernel)
    groups = _members(kernel)
    by_people = {(r["kind"], r["people"]): rid for rid, r in realms(kernel).items()}
    seceded_worlds = {pid for r in realms(kernel).values() if r.get("seceded_from") for pid in r["worlds"]}
    # 1. members of existing realms; new realms where a people or a house qualifies
    for key, worlds in sorted(groups.items()):
        rid = by_people.get(key)
        if rid is not None:
            realm = realms(kernel)[rid]
            realm["worlds"] = [w.id for w in worlds if w.id not in seceded_worlds or w.id in realm["worlds"]]
            continue
        if _eligible(kernel, key, worlds, genesis):
            realm = found(kernel, key, [w for w in worlds if w.id not in seceded_worlds] or worlds)
            if not genesis:
                logs.append(f"[REALM] The {realm['name']} is founded at {kernel.get_planet(realm['capital']).name}.")
    # breakaway realms keep only their own worlds
    for realm in realms(kernel).values():
        if realm.get("seceded_from"):
            realm["worlds"] = [pid for pid in realm["worlds"] if (kernel.get_planet(pid) is not None
                                                                   and kernel.get_planet(pid).population > 0)]
    # 2. secession: a far, unhappy member world breaks away
    for rid, realm in list(realms(kernel).items()):
        seat = capital(kernel, realm)
        if seat is None or realm["kind"] != "civ":
            continue                                   # a captain's colonies answer to their owner
        dist = topology.hops(kernel, seat.sector_id, 12)
        for pid in list(realm["worlds"]):
            w = kernel.get_planet(pid)
            if w is None or w.id == seat.id:
                continue
            far = dist.get(w.sector_id, 99) >= SECESSION_HOPS
            realm["unrest"][pid] = realm["unrest"].get(pid, 0) + 1 if (far and w.morale < SECESSION_MORALE) else 0
            if realm["unrest"][pid] >= SECESSION_SEASONS:
                realm["worlds"].remove(pid)
                realm["unrest"].pop(pid, None)
                new = found(kernel, (realm["kind"], f"{realm['people']}:{w.id}"), [w],
                            note=f"It has broken away from the {realm['name']}.")
                new["seceded_from"] = rid
                new["name"] = f"Free {w.name} " + new["name"].split()[-1]
                st["seceded"] += 1
                logs.append(f"[REALM] {w.name} broke away from the {realm['name']}: the {new['name']} is born.")
    # 3. dissolution; a capital lost moves to the largest remaining member
    for rid, realm in list(realms(kernel).items()):
        live = [kernel.get_planet(pid) for pid in realm["worlds"]]
        live = [w for w in live if w is not None and w.population > 0]
        if not live:
            del realms(kernel)[rid]
            st["dissolved"] += 1
            logs.append(f"[REALM] The {realm['name']} is no more.")
            continue
        if capital(kernel, realm) is None or realm["capital"] not in [w.id for w in live]:
            realm["capital"] = max(live, key=lambda w: (w.population, w.id)).id
    _claim(kernel)
    return logs


def genesis(kernel: Any) -> None:
    """The baseline board: every sovereign people is a realm from the first day, with historical borders - the
    systems within CHARTER_REACH jumps of its capital (the largest peoples draw theirs first), outside great powers'
    territory and the Federation's core."""
    from xylarium.kernel import primordial
    if not REALMS_AT_GENESIS or primordial.is_primordial(kernel):
        return                                   # a primordial galaxy draws its realms as they arise
    quarter(kernel, genesis=True)
    fm = kernel.factions
    taken = set(claims(kernel))
    for realm in sorted(realms(kernel).values(), key=lambda r: (-sum(
            (kernel.get_planet(p).population if kernel.get_planet(p) else 0) for p in r["worlds"]), r["id"])):
        seat = capital(kernel, realm)
        if seat is None:
            continue
        charter = []
        for sid in sorted(topology.hops(kernel, seat.sector_id, CHARTER_REACH)):
            sec = kernel.sectors[sid]
            if getattr(sec, "kind", "") != "SYSTEM" or fm.owner_of(sid) in ("IMPERIUM", "ZEALOT") \
                    or sec.security.value == "FEDERATION":
                continue
            if sid in taken and claims(kernel).get(sid) != realm["id"]:
                continue
            charter.append(sid)
            taken.add(sid)
        realm["charter"] = charter
    _claim(kernel)


def summary(kernel: Any) -> Dict[str, Any]:
    rs = sorted(realms(kernel).values(), key=lambda r: -len(r["systems"]))
    pop = {r["id"]: sum((kernel.get_planet(p).population if kernel.get_planet(p) else 0) for p in r["worlds"]) for r in rs}
    return {**stats(kernel), "realms": len(rs), "claimed_systems": len(claims(kernel)),
            "houses": sum(1 for r in rs if r["kind"] == "house"),
            "largest": [f"{r['name']} ({len(r['systems'])} systems, {len(r['worlds'])} worlds, {pop[r['id']]:,} people)"
                        for r in rs[:4]]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402


def _restore(kernel: Any) -> None:
    """Saved claims come back with string keys (JSON): sector ids are integers."""
    rec = state.of(kernel, "realms")
    rec["claims"] = {int(k): v for k, v in rec["claims"].items()}


register_subsystem(Subsystem(
    name="realms",
    state=lambda: {"realms": {}, "claims": {}, "claims_version": 0,
                   "stats": {"founded": 0, "seceded": 0, "dissolved": 0, "contested": 0}},
    season=quarter,
    restore=_restore,
    genesis=genesis,
    summary=summary,
))
