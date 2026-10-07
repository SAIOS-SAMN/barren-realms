"""
Xylarium: single-lineage kernels, backup clones, and the Hall of Lineages.

A game kernel (one save file) binds exactly one player lineage for its lifespan. The player
chose a clade and background at Lineage Genesis and is that lineage: its colonies, fleets and
routes are theirs to command; rival dynasties, the great powers and the corporations are run
by the simulation.

A lineage survives hull losses while it has backup clones in the vats at Sol (each loss
decants one; more can be grown at the Sol stardock). Its seat is its home colony: if the home
colony falls, the seat passes to another colony it holds. A flagship lost with no clones left,
or a home colony razed with no other world to retreat to, is a Lineage Extinction Event:
the final record is burned into the Galactic Library and the Hall of Lineages (a legacy file
that outlives kernels), and control ends. A new kernel begins a new lineage.

Kernels that host many human captains (the bridge daemon, the playtest harness) leave
``single_lineage`` off and simply record no binding.
"""

import json
import os
from typing import Any, Dict, List, Optional

from xylarium.kernel import matter
from xylarium.config import LINEAGE_START_CLONES, LINEAGE_LEGACY_FILE


class LineageLocked(Exception):
    """Raised when a second lineage tries to enroll in a single-lineage kernel."""


def found(kernel: Any, captain: Any, background: Optional[str] = None) -> Dict[str, Any]:
    lineage = {
        "id": f"LIN-{kernel.seed}-{kernel.cycle_count}-{captain.id}",
        "player_id": captain.id,
        "founder": captain.name,
        "house": f"House of {captain.name.split()[-1]}",
        "clade": captain.clade,
        "species": captain.species,
        "metabolism": captain.metabolism,
        "background": background,
        "founded_cycle": kernel.cycle_count,
        "status": "ACTIVE",
        "clones": LINEAGE_START_CLONES,
        "home_colony": None,
        "hull_losses": 0,
        "seat_transfers": 0,
        "ended_cycle": None,
        "cause": None,
        "epitaph": None,
    }
    kernel.lineage = lineage
    return lineage


def bound(kernel: Any, captain_id: str) -> Optional[Dict[str, Any]]:
    lin = getattr(kernel, "lineage", None)
    if lin and lin.get("player_id") == captain_id:
        return lin
    return None


def is_extinct(kernel: Any, captain_id: str) -> bool:
    lin = bound(kernel, captain_id)
    return bool(lin and lin["status"] != "ACTIVE")


def on_hull_loss(kernel: Any, captain: Any) -> Optional[str]:
    """Called when a lineage captain's flagship is destroyed (after the escape pod reaches Sol)."""
    lin = bound(kernel, captain.id)
    if lin is None or lin["status"] != "ACTIVE":
        return None
    lin["hull_losses"] += 1
    if lin["clones"] > 0:
        lin["clones"] -= 1
        return (f"CLONE VATS: a backup of {captain.name} is decanted at Sol Central. "
                f"{lin['clones']} backup clone(s) remain in the vats.")
    return extinction(kernel, captain, "flagship lost with no backup clones in the vats")


def on_colony_founded(kernel: Any, captain: Any, planet: Any) -> None:
    lin = bound(kernel, captain.id)
    if lin is not None and lin["status"] == "ACTIVE" and not lin.get("home_colony"):
        lin["home_colony"] = planet.id


def check_seat(kernel: Any) -> Optional[str]:
    """Each tick: has the lineage's home colony fallen? Move the seat, or end the lineage."""
    lin = getattr(kernel, "lineage", None)
    if not lin or lin["status"] != "ACTIVE" or not lin.get("home_colony"):
        return None
    captain = kernel.captains.get(lin["player_id"])
    if captain is None:
        return None
    home = kernel.get_planet(lin["home_colony"])
    if home is not None and home.owner_id == captain.id:
        return None
    others = kernel.get_planets_owned_by(captain.id)
    if others:
        seat = max(others, key=lambda p: p.population)
        lin["home_colony"] = seat.id
        lin["seat_transfers"] += 1
        msg = f"SEAT TRANSFERRED: the {lin['house']} withdraws its seat to {seat.name}."
        if getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(sender="LINEAGE", text=msg, channel="SYSTEM", sector_id=seat.sector_id)
        return msg
    name = home.name if home is not None else lin["home_colony"]
    return extinction(kernel, captain, f"home colony {name} razed, with no world left to hold the seat")


def extinction(kernel: Any, captain: Any, cause: str) -> str:
    """Lineage Extinction Event: the final record is written and control ends."""
    lin = bound(kernel, captain.id)
    if lin is None or lin["status"] != "ACTIVE":
        return ""
    lin["status"] = "EXTINCT" if cause != "retired" else "RETIRED"
    lin["ended_cycle"] = kernel.cycle_count
    lin["cause"] = cause
    lin["final"] = final_record(kernel, captain)
    lin["epitaph"] = _epitaph(lin)
    chron = getattr(kernel, "chronicle", None)
    if chron is not None:
        title = (f"The Retirement of the {lin['house']}" if lin["status"] == "RETIRED"
                 else f"The End of the {lin['house']}")
        chron.record(kernel, "LINEAGE_LEGACY", captain.id, lin["house"], title, lin["epitaph"],
                     sector_id=captain.sector_id, tags=["lineage", "legacy", lin["status"].lower()],
                     alignment=captain.cosmic_alignment, author="Galactic Library")
    _archive(kernel, lin)
    if getattr(kernel, "event_bus", None):
        kernel.event_bus.broadcast_radio(sender="GALACTIC-LIBRARY", text=f"LINEAGE ENDED: {lin['house']} ({cause}).",
                                         channel="SYSTEM", sector_id=1)
    return f"LINEAGE EXTINCTION: the {lin['house']} has ended ({cause}). Its record is sealed in the Galactic Library."


def final_record(kernel: Any, captain: Any) -> Dict[str, Any]:
    from xylarium.kernel.alignment import band
    try:
        net_equity = kernel.market_manager.calculate_net_equity(captain, kernel)
    except Exception:
        net_equity = captain.credits
    colonies = kernel.get_planets_owned_by(captain.id)
    node = kernel.phylogeny_manager.get_node(captain.phylogeny_node_id) if captain.phylogeny_node_id else None
    return {
        "cycles_lived": kernel.cycle_count - (kernel.lineage or {}).get("founded_cycle", 0),
        "net_equity": int(net_equity),
        "credits": captain.credits,
        "colonies": len(colonies),
        "rank_tier": captain.rank_tier,
        "phylogeny_node": node.name if node else None,
        "experience": captain.experience_score,
        "alignment": round(captain.cosmic_alignment, 3),
        "alignment_band": band(captain.cosmic_alignment),
        "jumps": captain.chronicle_stats.get("jumps", 0),
        "freight_delivered": captain.freight_deliveries_completed,
        "sectors_charted": len(captain.visited_sectors),
        "grown_basis": len(captain.grown_basis),
        "cochain_flux": dict(captain.cochain_flux),
    }


def _epitaph(lin: Dict[str, Any]) -> str:
    f = lin["final"]
    return (
        f"HERE ENDS THE {lin['house'].upper()}, a {lin['species']} lineage of the {lin['clade'].title()} clade, founded by "
        f"{lin['founder']} at cycle {lin['founded_cycle']} and ended at cycle {lin['ended_cycle']} ({lin['cause']}). "
        f"Across {f['cycles_lived']:,} cycles it charted {f['sectors_charted']} sectors, made {f['jumps']:,} jumps, delivered "
        f"{f['freight_delivered']} cargoes, and held {f['colonies']} world(s) at the end. It reached Tier {f['rank_tier']}"
        + (f" as {f['phylogeny_node']}" if f["phylogeny_node"] else "")
        + f", with a net equity of {f['net_equity']:,} Cr, and walked as {f['alignment_band']} ({f['alignment']:+.2f}). "
        f"It lost {lin['hull_losses']} hull(s)."
    )


# ---------------------------------------------------------------------- the Hall of Lineages
def legacy_path(kernel: Any) -> Optional[str]:
    return getattr(kernel, "legacy_file", None)


def _archive(kernel: Any, lin: Dict[str, Any]) -> None:
    path = legacy_path(kernel)
    if not path:
        return
    hall = load_hall(path)
    hall.append({k: v for k, v in lin.items()})
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(hall, fh, indent=2)
    except OSError:
        pass


def load_hall(path: Optional[str] = None) -> List[Dict[str, Any]]:
    path = path or LINEAGE_LEGACY_FILE
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def import_hall(kernel: Any, path: Optional[str] = None) -> int:
    """A new kernel's Library remembers the lineages that came before it."""
    chron = getattr(kernel, "chronicle", None)
    if chron is None:
        return 0
    n = 0
    for lin in load_hall(path):
        if not lin.get("epitaph"):
            continue
        chron.record(kernel, "LINEAGE_LEGACY", lin.get("player_id"), lin.get("house", "a lost house"),
                     f"From the Hall of Lineages: the {lin.get('house', 'lost house')}", lin["epitaph"],
                     tags=["lineage", "legacy", "hall"], alignment=(lin.get("final") or {}).get("alignment"),
                     author="Hall of Lineages")
        n += 1
    return n


# =============================================================================
# NPC lineages: the many houses the simulation runs
# =============================================================================
# Every autonomous captain (outside the great powers' fleets) belongs to a house. Houses are
# founded by named captains, by civilizations that reach spaceflight, by corporations (their
# security corps) and by the Federation (its marshals); cleaved offshoots join their parent's
# house as cadet branches. A house shares a pool of backup clones: each hull loss decants one,
# and a member lost with the vats empty dies. The dead captain's estate passes to the house's
# heir (credits, foreign balances, shares, worlds); with no heir, money escheats to the Federal
# Reserve and worlds go free. A house with no living members is extinct: its epitaph is written.

from xylarium.config import NPC_HOUSE_START_CLONES, NPC_HOUSE_MAX_CLONES, LINEAGE_CLONE_PRICE, CAPTAIN_RATIONS


def npc_house_name(kernel: Any, captain: Any) -> str:
    name = captain.name
    if captain.id.startswith("corp_"):
        return f"{name.split()[0]} Security Corps"
    if captain.id.startswith("fed_marshal"):
        return "The Marshals of Sol"
    if captain.id.startswith("indigenous_") and " Emissary" in name:
        return f"The {name.split(' Emissary')[0]} Line"
    last = name.split()[-1]
    if last.isdigit() and len(name.split()) > 1:
        last = name.split()[-2]
    return f"House {last}"


def npc_found(kernel: Any, captain: Any, origin: str = "charter", parent: Optional[Any] = None) -> Dict[str, Any]:
    """Enrolls an autonomous captain in a house: its parent's (a cadet branch), an existing one, or a new one."""
    houses = kernel.npc_lineages
    if parent is not None and getattr(parent, "house_id", None) in houses and houses[parent.house_id]["status"] == "ACTIVE":
        house = houses[parent.house_id]
        house["generation"] = max(house["generation"], house["members"].get(parent.id, {}).get("gen", 1) + 1)
        house["members"][captain.id] = {"name": captain.name, "gen": house["members"].get(parent.id, {}).get("gen", 1) + 1,
                                        "joined": kernel.cycle_count}
        house["clones"] = min(NPC_HOUSE_MAX_CLONES, house["clones"] + 1)
        house["branches"] += 1
        captain.house_id = house["id"]
        return house
    name = npc_house_name(kernel, captain)
    existing = next((h for h in houses.values() if h["name"] == name and h["status"] == "ACTIVE"), None)
    if existing is not None:
        existing["members"][captain.id] = {"name": captain.name, "gen": 1, "joined": kernel.cycle_count}
        captain.house_id = existing["id"]
        return existing
    hid = f"H{len(houses) + 1:03d}"
    house = {
        "id": hid, "name": name, "founder": captain.name, "founded_cycle": kernel.cycle_count, "origin": origin,
        "clade": captain.clade, "species": captain.species, "creed": _creed(captain),
        "members": {captain.id: {"name": captain.name, "gen": 1, "joined": kernel.cycle_count}},
        "fallen": [], "clones": NPC_HOUSE_START_CLONES, "generation": 1, "branches": 0,
        "hull_losses": 0, "status": "ACTIVE", "ended_cycle": None, "cause": None, "epitaph": None,
        "peak_worlds": 0, "peak_equity": 0,
    }
    houses[hid] = house
    captain.house_id = hid
    chron = getattr(kernel, "chronicle", None)
    if chron is not None and kernel.cycle_count > 0:
        chron.record(kernel, "GENESIS_MANIFESTO", hid, name, f"The Founding of {name}",
                     f"GENESIS MANIFESTO. {captain.name} founds {name} ({captain.species}, {captain.clade.title()} clade; "
                     f"creed: {house['creed']}). Let the Library record where it began.",
                     sector_id=captain.sector_id, tags=["genesis", "house", origin], alignment=captain.cosmic_alignment)
    return house


def _creed(captain: Any) -> str:
    p = getattr(captain.personality, "value", "")
    if p == "pirate" or captain.clade == "ANARCHY" and captain.cosmic_alignment < 0:
        return "outlaw"
    if captain.cosmic_alignment >= 0.3:
        return "luminous"
    if p == "mercenary":
        return "sword-for-hire"
    if p == "industrialist":
        return "industrial"
    return "mercantile"


def house_endangered(kernel: Any, captain: Any) -> bool:
    """A house down to its last backup clones turns defensive: no raids, no picked fights, restock first."""
    from xylarium.config import HOUSE_ENDANGERED_CLONES
    house = house_of(kernel, captain)
    return bool(house and house["status"] == "ACTIVE" and house["clones"] < HOUSE_ENDANGERED_CLONES)


def house_of(kernel: Any, captain: Any) -> Optional[Dict[str, Any]]:
    hid = getattr(captain, "house_id", None)
    return getattr(kernel, "npc_lineages", {}).get(hid) if hid else None


def npc_hull_loss(kernel: Any, captain: Any) -> Optional[str]:
    """A house member's hull is lost: decant a clone, or the member dies (processed at the next tick)."""
    house = house_of(kernel, captain)
    if house is None or house["status"] != "ACTIVE":
        return None
    house["hull_losses"] += 1
    if house["clones"] > 0:
        house["clones"] -= 1
        return None
    captain.alignment_record["house_death"] = "flagship lost with the house vats empty"
    return f"{captain.name} of {house['name']} is lost: the house vats were empty."


def npc_tick(kernel: Any) -> List[str]:
    """Enroll new autonomous captains, settle deaths and estates, grow clones, and mark extinctions."""
    logs: List[str] = []
    for cap in list(kernel.captains.values()):
        if not cap.is_ai or cap.faction_id:
            continue
        if not getattr(cap, "house_id", None) or cap.house_id not in kernel.npc_lineages:
            origin = "civiligenesis" if cap.id.startswith("indigenous_") else "charter"
            npc_found(kernel, cap, origin)
        if cap.alignment_record.get("house_death"):
            logs.append(_npc_death(kernel, cap, cap.alignment_record.pop("house_death")))
    if kernel.cycle_count % 25:
        return [l for l in logs if l]
    for house in kernel.npc_lineages.values():
        if house["status"] != "ACTIVE":
            continue
        live = [kernel.captains[m] for m in house["members"] if m in kernel.captains]
        house["peak_worlds"] = max(house["peak_worlds"], sum(len(kernel.get_planets_owned_by(c.id)) for c in live))
        # A house grows backup clones when a member can afford it: at the Sol vats, or - for outlaw
        # houses the Federation's turrets turn away - at a Deep Void black-market vat (paid to that port)
        if house["clones"] < NPC_HOUSE_MAX_CLONES:
            def at_vats(c: Any) -> bool:
                sec = kernel.sectors[c.sector_id]
                if c.sector_id == 1:
                    return True
                return house["creed"] == "outlaw" and sec.port is not None and sec.security.value == "ANARCHY"
            # An endangered house spends more readily on the vats: survival before savings
            from xylarium.config import HOUSE_ENDANGERED_CLONES
            margin = 1.2 if house["clones"] < HOUSE_ENDANGERED_CLONES else 4
            buyer = next((c for c in live if at_vats(c) and c.credits >= LINEAGE_CLONE_PRICE * margin), None)
            if buyer is not None:
                buyer.credits -= LINEAGE_CLONE_PRICE
                kernel._stardock_revenue(kernel.sectors[buyer.sector_id], LINEAGE_CLONE_PRICE)
                house["clones"] += 1
    if kernel.cycle_count % 500 == 0:
        rise = _void_breeds_corsairs(kernel)
        if rise:
            logs.append(rise)
    return [l for l in logs if l]


def _void_breeds_corsairs(kernel: Any) -> Optional[str]:
    """When no outlaw house survives, the Deep Void breeds a new one: a salvaged hull and an empty purse."""
    from xylarium.config import SHIP_CATALOG
    from xylarium.kernel import populace
    from xylarium.kernel.models import AIPersonality, CargoHold, Captain, Ship
    alive_outlaws = [h for h in kernel.npc_lineages.values() if h["status"] == "ACTIVE" and h["creed"] == "outlaw"
                     and any(m in kernel.captains for m in h["members"])]
    if alive_outlaws or not populace.room_for_ai(kernel):
        return None
    lairs = [s for s in kernel.sectors.values() if s.security.value == "ANARCHY" and s.kind == "NULL"
             and not kernel.factions.owner_of(s.id)]
    if not lairs:
        return None
    lair = lairs[kernel.cycle_count % len(lairs)]
    cfg = SHIP_CATALOG["Star Frigate"]
    cargo = CargoHold(capacity=cfg["holds"])
    cargo.organics = 20
    names = ["Red Vesh", "Kaddo the Knife", "Mother Ashgrave", "Sable Quint", "Old Tamber", "Ivo Blacklantern"]
    name = names[(kernel.cycle_count // 500) % len(names)]
    cap = Captain(id=f"corsair_{kernel.cycle_count}", name=name, is_ai=True, personality=AIPersonality.PIRATE,
                  ship=Ship(ship_type="Star Frigate", cargo=cargo, shields=cfg["max_shields"] // 2,
                            max_shields=cfg["max_shields"], fighters=cfg["max_fighters"] // 2),
                  credits=0, sector_id=lair.id, turns_left=200, home_sector=lair.id,
                  species="human-outlaw", metabolism="biotic", clade="ANARCHY", rank_tier=2)
    # a corsair begins with no history, as every captain does: what it does will make it
    kernel.captains[cap.id] = cap
    matter.commission(cap)
    lair.captains.append(cap.id)
    house = npc_found(kernel, cap, "void")
    return f"[HOUSE] The Deep Void breeds a new corsair line: {house['name']} rises at Sector {lair.id:03d}."


def _npc_death(kernel: Any, captain: Any, cause: str) -> str:
    """A house member dies: the estate passes to the heir (or escheats), then the captain leaves the galaxy."""
    house = house_of(kernel, captain)
    heirs = [kernel.captains[m] for m in (house or {}).get("members", {}) if m in kernel.captains and m != captain.id]
    heir = max(heirs, key=lambda c: c.credits) if heirs else None
    fed = getattr(kernel, "federal_reserve", None)
    fxm = kernel.fx_market
    # Money: to the heir, or escheat to the Federal Reserve (never destroyed)
    if heir is not None:
        heir.credits += captain.credits
        for cur, amt in captain.fx_wallet.items():
            heir.fx_wallet[cur] = heir.fx_wallet.get(cur, 0) + amt
        for tkr, sh in captain.portfolio.items():
            heir.portfolio[tkr] = heir.portfolio.get(tkr, 0) + sh
    elif fed is not None:
        banks = getattr(getattr(kernel, "banking", None), "banks", {}) or {}
        escheat = captain.credits
        for cur, amt in captain.fx_wallet.items():
            if amt <= 0:
                continue
            if cur in fxm.pools:
                escheat += fxm.swap_to_sol(cur, amt)
            elif cur in banks:                     # a money no exchange quotes escheats to its own issuer
                banks[cur].reserves += amt
        fed.receive(escheat, "escheat")
    captain.credits = 0
    captain.fx_wallet = {}
    captain.portfolio = {}
    # Worlds: to the heir, or they go free as independent colonies
    from xylarium.kernel.civilization import CivilizationIntelligenceEngine
    for p in kernel.get_planets_owned_by(captain.id):
        if heir is not None:
            p.owner_id = heir.id
        else:
            p.owner_id = None
            if p.civilization is None and p.population > 0:
                p.civilization = CivilizationIntelligenceEngine.create_civilization({
                    "name": f"Free {p.name.split()[0]}", "species_name": captain.species, "class_code": 1, "sigil": "✧",
                    "clade": captain.clade.lower(), "metabolism": captain.metabolism, "disposition": "industry",
                    "motto": "we outlived our founders", "station": "unseated", "tech_level": 2})
    for h in kernel.market_manager.trade_haulers.values():
        if h.owner_id == captain.id:
            if heir is not None:
                h.owner_id = heir.id
                heir.trade_haulers.append(h.id)
            else:
                h.active = False
    kernel.market_manager.forfeit_freight(captain, kernel)
    from xylarium.kernel.nullspace import NullSpaceManager
    NullSpaceManager.abandon_hold(kernel.sectors.get(captain.sector_id), captain, kernel.cycle_count, "derelict")
    for s in kernel.sectors.values():
        s.sentries.pop(captain.id, None)
        if captain.id in s.captains:
            s.captains.remove(captain.id)
    del kernel.captains[captain.id]
    from xylarium.kernel import dynasties
    dynasties.forget(kernel, captain.id)
    msg = f"[HOUSE] {captain.name} of {(house or {}).get('name', 'no house')} has died ({cause})."
    if house is not None:
        house["members"].pop(captain.id, None)
        house["fallen"].append({"name": captain.name, "cycle": kernel.cycle_count, "cause": cause,
                                "heir": heir.name if heir else None})
        chron = getattr(kernel, "chronicle", None)
        if chron is not None:
            chron.record(kernel, "CAPTAINS_LOG", captain.id, captain.name, f"The Death of {captain.name}",
                         f"{captain.name} of {house['name']} is dead ({cause}). "
                         + (f"The estate passes to {heir.name}." if heir else "No heir stood to take the estate."),
                         sector_id=captain.sector_id, tags=["death", "house"], alignment=captain.cosmic_alignment)
        if not any(m in kernel.captains for m in house["members"]):
            msg += " " + _npc_extinction(kernel, house, captain, cause)
    if getattr(kernel, "event_bus", None):
        kernel.event_bus.broadcast_radio(sender="GALACTIC-LIBRARY", text=msg, channel="SYSTEM", sector_id=1)
    return msg


def _npc_extinction(kernel: Any, house: Dict[str, Any], last: Any, cause: str) -> str:
    house["status"] = "EXTINCT"
    house["ended_cycle"] = kernel.cycle_count
    house["cause"] = cause
    house["epitaph"] = (
        f"HERE ENDS {house['name'].upper()}, founded by {house['founder']} at cycle {house['founded_cycle']} "
        f"({house['species']}, {house['clade'].title()} clade, {house['creed']} creed). It ran {house['generation']} "
        f"generation(s) and {house['branches']} cadet branch(es), held as many as {house['peak_worlds']} world(s), lost "
        f"{house['hull_losses']} hull(s), and ended at cycle {kernel.cycle_count} when {last.name} fell ({cause})."
    )
    chron = getattr(kernel, "chronicle", None)
    if chron is not None:
        chron.record(kernel, "LINEAGE_LEGACY", house["id"], house["name"], f"The End of {house['name']}",
                     house["epitaph"], tags=["lineage", "legacy", "npc"], alignment=last.cosmic_alignment,
                     author="Galactic Library")
    return f"{house['name']} is extinct."


def npc_census(kernel: Any) -> Dict[str, Any]:
    houses = list(getattr(kernel, "npc_lineages", {}).values())
    alive = [h for h in houses if h["status"] == "ACTIVE"]
    return {"founded": len(houses), "alive": len(alive), "extinct": len(houses) - len(alive),
            "branches": sum(h["branches"] for h in houses), "deaths": sum(len(h["fallen"]) for h in houses),
            "max_generation": max((h["generation"] for h in houses), default=0)}
