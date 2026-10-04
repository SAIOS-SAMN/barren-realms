"""
Xylarium roles: the three seats a new player - human or AI - can take in a universe.

  PROGENITOR   start from the Big Bang as one of the first minds the universe raises near its galaxy's core: shape
               that ancient people, carry it through what deep time throws at it, seed the young worlds that come
               after it, and write its chronicle.
  STEWARD      rule an established polity on the brink of interstellar travel: say how it is governed, raise its
               defences, make war, settle new worlds (Barren Realms Elite).
  CAPTAIN      a fleet manager in an established civilization, starting at Tradewards - the settled galaxy's
               densest cluster of docks: trade, haul, dodge pirates, answer to the police, hunt bounties.

A role is a starting seat, not a different universe: every seat plays under the same laws. The terminal client
(xylarium/client/roles.py) and the bridge (REGISTER with a role) start a seat through the functions here.
"""

from typing import Any, Dict, List, Optional

ROLES: List[Dict[str, str]] = [
    {"key": "progenitor", "name": "Progenitor",
     "blurb": "Start from the Big Bang as one of the first minds near the galactic core. Shape your ancient people, "
              "carry it through what deep time throws at it, seed young worlds, and write its chronicle."},
    {"key": "steward", "name": "Steward",
     "blurb": "Rule an established polity on the brink of interstellar travel. Choose how it is governed, then build "
              "its planetary defences, make war, and settle new worlds (Barren Realms Elite)."},
    {"key": "captain", "name": "Captain",
     "blurb": "Command a ship in an established civilization, starting at Tradewards, where docks are everywhere. "
              "Trade, haul freight, dodge pirates, answer to the police, and hunt bounties (TradeWars)."},
]
KEYS = tuple(r["key"] for r in ROLES)
TRADEWARDS_REACH = 2            # jumps: the docks a captain can reach from a hub without ranging far


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "roles")


def role_of(kernel: Any, player_id: str) -> Optional[str]:
    return stats(kernel)["of"].get(player_id)


def describe() -> List[Dict[str, str]]:
    return [dict(r) for r in ROLES]


# ---------------------------------------------------------------------- captain: Tradewards
def tradewards(kernel: Any) -> Optional[Dict[str, Any]]:
    """Tradewards: the docked sector with the most docks within TRADEWARDS_REACH jumps (ties: the lower id)."""
    st = stats(kernel)
    if st.get("tradewards"):
        return st["tradewards"]
    from xylarium.kernel import topology
    best = None
    for sid, sec in sorted(kernel.sectors.items()):
        if sec.port is None:
            continue
        near = topology.hops(kernel, sid, TRADEWARDS_REACH)
        docks = sum(1 for s in near if kernel.sectors.get(s) is not None and kernel.sectors[s].port is not None)
        if best is None or docks > best["docks"]:
            best = {"sector": sid, "docks": docks, "port": sec.port.name}
    st["tradewards"] = best
    return best


def place(kernel: Any, player_id: str, sector_id: int) -> None:
    """Move a captain to a sector as its starting berth (its home port)."""
    cap = kernel.get_player(player_id)
    if cap is None or sector_id not in kernel.sectors:
        return
    old = kernel.sectors.get(cap.sector_id)
    if old is not None and player_id in old.captains:
        old.captains.remove(player_id)
    cap.sector_id = sector_id
    cap.home_sector = sector_id
    if player_id not in kernel.sectors[sector_id].captains:
        kernel.sectors[sector_id].captains.append(player_id)


def seat_captain(kernel: Any, player_id: str) -> Dict[str, Any]:
    """A registered captain takes the Captain's seat: berthed at Tradewards, unless its origin musters elsewhere."""
    from xylarium.config import PLAYER_STARTING_SECTOR, STARTING_BACKGROUNDS
    cap = kernel.get_player(player_id)
    stats(kernel)["of"][player_id] = "captain"
    tw = tradewards(kernel)
    bg = STARTING_BACKGROUNDS.get((cap.background or "").lower()) if cap is not None and cap.background else None
    own_muster = bg is not None and bg.get("start_sector", PLAYER_STARTING_SECTOR) != PLAYER_STARTING_SECTOR
    if tw is not None and cap is not None and not own_muster and cap.sector_id == PLAYER_STARTING_SECTOR:
        place(kernel, player_id, tw["sector"])
    return {"role": "captain", "tradewards": tw, "sector": cap.sector_id if cap is not None else None}


def start_captain(seed: int, name: str, clade: Optional[str] = None, background: Optional[str] = None,
                  player_id: str = "player_1") -> Any:
    """A new settled universe with one captain at Tradewards. Returns the kernel."""
    from xylarium.kernel.engine import GameKernel
    k = GameKernel(seed=seed)
    k.single_lineage = True
    k.register_player(player_id, name, clade=clade, background=background, bind_lineage=True)
    seat_captain(k, player_id)
    return k


# ---------------------------------------------------------------------- steward: a polity's ruler
RULE_FORMS = [               # how much of the many's product the polity's few take (rent.py) - the ruler's choice
    {"key": "commonwealth", "name": "Commonwealth", "rent": 0.0,
     "blurb": "No one takes from the many beyond what they give back. Slower to arm; its people think and live best."},
    {"key": "council", "name": "Council of Houses", "rent": 0.25,
     "blurb": "Great houses take a quarter of what the many make. A middle road."},
    {"key": "throne", "name": "Throne", "rent": 0.5,
     "blurb": "The throne takes half. A rich treasury - and a people closer to hunger and to rising."},
]
GREAT_POWERS = ("IMPERIUM", "ZEALOT")


def polities(kernel: Any) -> List[Dict[str, Any]]:
    """Polities a ruler can take: independent peoples of the settled galaxy (not a great power's, not a captain's),
    largest first."""
    from xylarium.kernel import relations
    out = []
    for holder, worlds in relations._peoples(kernel).items():
        if not holder.startswith("civ:"):
            continue
        ws = [w for w in worlds if not w.owner_id and (w.faction_id or None) not in GREAT_POWERS
              and getattr(w, "civilization", None) is not None and not getattr(w, "natives", None)]
        if not ws:
            continue
        cap = max(ws, key=lambda w: (w.population, w.id))
        out.append({"holder": holder, "name": holder.split(":", 1)[-1], "worlds": len(ws),
                    "population": sum(w.population for w in ws), "capital": cap.id, "capital_name": cap.name,
                    "sector": cap.sector_id, "citadel": max(w.citadel_level for w in ws)})
    return sorted(out, key=lambda p: -p["population"])


def seat_ruler(kernel: Any, player_id: str, name: str, holder: str, rule: str = "council",
               gauges: Optional[Dict[str, float]] = None, natal: Optional[str] = None) -> Dict[str, Any]:
    """The player takes the Steward's seat as ruler of `holder`'s polity: it governs (owns) every world the polity
    holds, sets the share its few take (rule), its leanings (society gauges) and, if it chooses, its birth policy.
    It holds court from a ship at its capital."""
    from xylarium.kernel import fertility, relations, society
    worlds = [w for w in relations._peoples(kernel).get(holder, []) if not w.owner_id]
    if not worlds:
        raise ValueError(f"No polity {holder} to rule.")
    form = next((f for f in RULE_FORMS if f["key"] == rule), RULE_FORMS[1])
    cap_world = max(worlds, key=lambda w: (w.population, w.id))
    ruler = kernel.get_player(player_id) or kernel.register_player(player_id, name)
    place(kernel, player_id, cap_world.sector_id)
    for w in worlds:
        w.owner_id = player_id
        w.society["rent"] = form["rent"]
        w.society["rent_set"] = True
        for key, value in (gauges or {}).items():
            society.set_gauge(w, key, value)
        if natal:
            fertility.set_natal(kernel, ruler, w, natal)
    _inherit(kernel, holder, f"captain:{player_id}")
    st = stats(kernel)
    st["of"][player_id] = "steward"
    st.setdefault("realms", {})[player_id] = {"holder": holder, "rule": form["key"], "capital": cap_world.id,
                                              "worlds": [w.id for w in worlds]}
    return {"role": "steward", "polity": holder.split(":", 1)[-1], "rule": form["name"], "worlds": len(worlds),
            "capital": cap_world.name, "sector": cap_world.sector_id}


def rules(kernel: Any, captain: Any, planet: Any) -> bool:
    """Is this captain the ruler (the Steward's seat) of the realm this world belongs to?"""
    realm = stats(kernel).get("realms", {}).get(getattr(captain, "id", None))
    return bool(realm) and planet is not None and planet.owner_id == captain.id and planet.id in realm["worlds"]


from contextlib import contextmanager  # noqa: E402


@contextmanager
def realm_purse(kernel: Any, captain: Any, planet: Any):
    """A ruler's order on its own world is paid from that world's treasury: the treasury is changed into the reserve
    currency through the ISSE for the order, and what the order does not spend is changed back (pool fees both ways;
    nothing is made or lost but what the exchange takes). Anything beyond the treasury comes from the ruler's purse."""
    from xylarium.kernel import fx
    if not rules(kernel, captain, planet) or planet.treasury <= 0:
        yield
        return
    cur = planet.currency
    local = int(planet.treasury)
    planet.treasury = 0
    sol = local if cur == "SOL" or fx.ACTIVE_FX is None else fx.ACTIVE_FX.swap_to_sol(cur, local)
    before = captain.credits
    captain.credits += sol
    try:
        yield
    finally:
        spent = before + sol - captain.credits
        left = max(0, sol - max(0, spent))
        captain.credits = before - max(0, spent - sol)
        if left > 0:
            planet.treasury += left if cur == "SOL" or fx.ACTIVE_FX is None else fx.ACTIVE_FX.swap_sol_to(cur, left)


def _inherit(kernel: Any, people: str, ruler: str) -> None:
    """A ruler governs with what its people knows: their knowledge, their capabilities and their mathematics become
    the ruler's (the worlds it now governs are reckoned under its name)."""
    import copy
    from xylarium.kernel import intellect, knowledge, technology
    mine = knowledge.stocks(kernel, ruler)
    for d, v in knowledge.stocks(kernel, people).items():
        mine[d] = max(float(mine.get(d, 0.0)), float(v))
    held = technology.stats(kernel)["of"].setdefault(ruler, {})
    held.update(copy.deepcopy(technology.stats(kernel)["of"].get(people, {})))
    ist = intellect.stats(kernel)
    if people in ist.get("vocab", {}):
        ist["vocab"][ruler] = list(ist["vocab"][people])
    if people in ist.get("gauge", {}):
        ist.setdefault("gauge", {})[ruler] = dict(ist["gauge"][people])


def realm(kernel: Any, player_id: str) -> Optional[Dict[str, Any]]:
    """The ruler's dashboard, read from the laws: for each world it governs, its people, its treasury (in its own
    money and in the reserve's), its defences, the share its few take against the most they can bear before the many
    rise (rent.bearable), how many would rise now (society.stress), and its people's next threshold of history."""
    from xylarium.kernel import annals, biosphere, fx, knowledge, mastery, rent, society
    rec = stats(kernel).get("realms", {}).get(player_id)
    if not rec:
        return None
    rows = []
    for wid in rec["worlds"]:
        w = kernel.get_planet(wid)
        if w is None or w.owner_id != player_id:
            continue
        cur = getattr(w, "currency", "SOL") or "SOL"
        t = int(w.treasury)
        t_sol = t if cur == "SOL" or fx.ACTIVE_FX is None else int(fx.ACTIVE_FX.to_sol_value(cur, t))
        s = society.stress(kernel, w) if w.civilization is not None else {}
        rows.append({"id": w.id, "name": w.name, "sector": w.sector_id, "population": w.population,
                     "room": int(biosphere.carrying_capacity(kernel, w)),
                     "treasury": t, "currency": cur, "treasury_sol": t_sol, "shields": w.shields,
                     "fighters": w.fighters, "citadel": w.citadel_level, "morale": int(w.morale),
                     "rent": round(rent.of(w), 3), "bearable": round(rent.bearable(kernel, w), 3),
                     "rising": s.get("rising"), "hunger": s.get("immiseration"),
                     "levy": round(society.gauges(w)["levy"], 3),
                     "line": max(society.gauges(w)["levy"], society.MOBILISED)})
    cap = kernel.get_planet(rec["capital"])
    holder = knowledge.holder_of_planet(cap) if cap is not None and cap.civilization is not None else rec["holder"]
    stage = annals._stage(kernel, holder, cap) if cap is not None else None
    nxt = None
    if stage and stage != "crossed":
        nxt = annals.STAGES[annals.STAGES.index(stage) + 1]
    blocked = None
    if nxt == "yards" and not annals._can_reach_orbit(kernel, holder, cap):
        blocked = "its world holds it from the sky: neither its chemistry nor its atom reaches orbit"
    elif nxt == "crossed" and not mastery.genome_ready(kernel, holder, [cap]):
        blocked = "it does not yet know its own genome well enough to live between the stars"
    return {"polity": rec["holder"].split(":", 1)[-1], "rule": rec["rule"], "capital": rec["capital"],
            "stage": stage, "next": nxt, "blocked": blocked, "worlds": rows,
            "treasury_sol": sum(r["treasury_sol"] for r in rows),
            "population": sum(r["population"] for r in rows),
            "at_risk": [r["name"] for r in rows if r["rising"] is not None and r["rising"] > r["line"]],
            "crowded": [r["name"] for r in rows if r["population"] > r["room"]]}


def render_realm(r: Dict[str, Any]) -> str:
    """The realm dashboard, as text."""
    lines = [f"=== REALM OF THE {r['polity'].upper()} ({r['rule']}) ===",
             f"  {r['population']:,} people on {len(r['worlds'])} world(s); treasuries worth {r['treasury_sol']:,} SOL",
             f"  History: {r['stage']}" + (f"  ->  next: {r['next']}" if r["next"] else "  (among the stars)")]
    if r["blocked"]:
        lines.append(f"  Held back: {r['blocked']}")
    lines.append(f"  {'World':<18}{'Sector':>7}{'People':>12}{'Room':>12}{'Treasury':>16}{'Shld':>7}{'Ftr':>6}{'Cit':>4}"
                 f"{'Take':>6}{'Max':>6}{'Rise':>6}{'Levy':>6}")
    for w in r["worlds"]:
        rise = f"{w['rising']:.2f}" if w["rising"] is not None else "-"
        lines.append(f"  {w['name'][:17]:<18}{w['sector']:>7}{w['population']:>12,}{w['room']:>12,}"
                     f"{w['treasury']:>11,} {w['currency']:<4}{w['shields']:>7,}{w['fighters']:>6,}{w['citadel']:>4}"
                     f"{w['rent']:>6.2f}{w['bearable']:>6.2f}{rise:>6}{w['levy']:>6.2f}")
    if r["at_risk"]:
        lines.append("  More would rise than could be held down on: " + ", ".join(r["at_risk"]))
    if r["crowded"]:
        lines.append("  More people than their land can feed (they will starve back to its room unless fed from "
                     "elsewhere): " + ", ".join(r["crowded"]))
    lines.append("  Room = the people its land feeds. Take = the share your few take; Max = the most the many bear before they rise.")
    return "\n".join(lines)


def set_take(kernel: Any, player_id: str, rule: str) -> Optional[str]:
    """The ruler changes how its realm is governed: the share its few take, on every world it holds."""
    rec = stats(kernel).get("realms", {}).get(player_id)
    form = next((f for f in RULE_FORMS if f["key"] == rule), None)
    if not rec or form is None:
        return None
    for wid in rec["worlds"]:
        w = kernel.get_planet(wid)
        if w is not None and w.owner_id == player_id:
            w.society["rent"] = form["rent"]
            w.society["rent_set"] = True
    rec["rule"] = form["key"]
    return f"Your realm is now governed as {form['name']}: the few take {form['rent']:.0%}."


def start_steward(seed: int, name: str, pick: int = 0, rule: str = "council",
                  gauges: Optional[Dict[str, float]] = None, natal: Optional[str] = None,
                  player_id: str = "player_1") -> Any:
    """A new settled universe whose `pick`-th largest independent polity the player rules. Returns the kernel."""
    from xylarium.kernel.engine import GameKernel
    k = GameKernel(seed=seed)
    ps = polities(k)
    if not ps:
        raise ValueError("This universe has no independent polity to rule.")
    seat_ruler(k, player_id, name, ps[min(max(0, pick), len(ps) - 1)]["holder"], rule, gauges, natal)
    return k


# ---------------------------------------------------------------------- progenitor: an ancient
ANCIENTS = 7                    # the first minds the universe raises: the ancient class a progenitor may take


def ancients(kernel: Any) -> List[Dict[str, Any]]:
    """The first minds this universe will raise (cosmos.py's schedule), earliest first: when each wakes (Gyr after
    the Big Bang), what its life is made of, and how far out its home lies (its ring of the galaxy, from the core)."""
    from xylarium.kernel import cosmos
    out = []
    for i, m in enumerate(cosmos.stats(kernel)["minds"][:ANCIENTS]):
        out.append({"index": i, "dawn_gyr": round(float(m["epoch"]), 4), "metabolism": m.get("metab") or "biotic",
                    "ring": int(m["cell"][0]), "cell": list(m["cell"]), "k": int(m["k"]), "w": int(m.get("w", 0)),
                    "star_mass": m.get("mass")})
    return out


def _arisen_world(kernel: Any, rec: Dict[str, Any]) -> Optional[Any]:
    """The world of a scheduled mind, once that mind has woken on it (None before, or if it never wakes)."""
    from xylarium.kernel import cosmos
    try:
        sid = cosmos.sector_of_slot(kernel, tuple(rec["cell"]), int(rec["k"]))
    except Exception:
        return None
    sec = kernel.sectors.get(sid)
    if sec is None or int(rec["w"]) >= len(sec.planets):
        return None
    p = sec.planets[int(rec["w"])]
    return p if p.civilization is not None and p.population > 0 and (p.society or {}).get("arisen") else None


def start_progenitor(seed: int, name: str, pick: int = 0, pace: str = "neighbourly", player_id: str = "player_1",
                     progress: Any = None, max_cycles: int = 2_000_000) -> Any:
    """A Big Bang universe of this seed, run to the dawn of the `pick`-th of its first minds; the player takes that
    ancient people's seat (its steward from its first day). Returns the kernel, or None if the mind never woke (its
    world was taken or its star died first)."""
    from xylarium.kernel import ages
    from xylarium.kernel.engine import GameKernel
    k = GameKernel(seed=seed, genesis=f"cosmic:{pace}")
    k.activate()
    anc = ancients(k)
    if not anc:
        return None
    rec = anc[min(max(0, pick), len(anc) - 1)]
    world = _arisen_world(k, rec)
    start = k.cycle_count
    while world is None and k.cycle_count - start < max_cycles:
        k.tick_simulation()
        if progress is not None and k.cycle_count % 1000 == 0:
            progress(k)
        if k.cycle_count % 25 == 0:
            world = _arisen_world(k, rec)
    if world is None:
        return None
    ages.bind(k, player_id, name, world)
    st = stats(k)
    st["of"][player_id] = "progenitor"
    st.setdefault("ancients", {})[player_id] = {"index": rec["index"], "world": world.id,
                                                "dawn_cycle": k.cycle_count, "dawn_gyr": rec["dawn_gyr"]}
    return k


# ---------------------------------------------------------------------- progress, for every seat
def _ledger(x: Any) -> Dict[str, Any]:
    from xylarium.kernel import alignment
    cs = alignment.causes(x)
    return {"alignment": round(alignment.character(x), 4), "doctrine": round(alignment.doctrine(x), 4),
            "made": round(sum(v["light"] for v in cs.values()), 1), "destroyed": round(sum(v["dark"] for v in cs.values()), 1),
            "top_destroyed": [(k, v["dark"]) for k, v in list(cs.items())[:3] if v["dark"] > 0]}


def _seen_by_others(kernel: Any, holder: str) -> Optional[float]:
    from xylarium.kernel import reputation
    reads = [r for obs in reputation.stats(kernel)["of"] for r in [reputation.read(kernel, obs, holder)] if r is not None]
    return round(sum(reads) / len(reads), 4) if reads else None


def progress(kernel: Any, player_id: str) -> Dict[str, Any]:
    """Where a seat stands, read from what the laws already keep: its history (made and destroyed, by cause), how
    others read it, and the measures of its own seat."""
    from xylarium.kernel import ages, cosmos, mastery, relations, syntropy
    role = role_of(kernel, player_id) or ("steward" if ages.stats(kernel)["stewards"].get(player_id) else "captain")
    out: Dict[str, Any] = {"role": role, "year": kernel.cycle_count // 100}
    cap = kernel.get_player(player_id)
    if role == "captain" and cap is not None:
        out.update(credits=cap.credits, score=cap.score, rank=cap.rank_tier, bounty=cap.bounty,
                   ledger=_ledger(cap.alignment_record), seen_by_others=None, sector=cap.sector_id)
        return out
    if role == "steward" and player_id in stats(kernel).get("realms", {}):
        realm = stats(kernel)["realms"][player_id]
        worlds = [kernel.get_planet(w) for w in realm["worlds"]]
        worlds = [w for w in worlds if w is not None and w.owner_id == player_id]
        holder = f"captain:{player_id}"
        capital = kernel.get_planet(realm["capital"])
        civ = getattr(capital, "civilization", None) if capital is not None else None
        out.update(polity=realm["holder"].split(":", 1)[-1], rule=realm["rule"], worlds=len(worlds),
                   population=sum(w.population for w in worlds), treasury=sum(w.treasury for w in worlds),
                   citadels=[w.citadel_level for w in worlds], shields=sum(w.shields for w in worlds),
                   fighters=sum(w.fighters for w in worlds), strife=sum(1 for w in worlds if w.society.get("strife_cycle")),
                   ledger=_ledger(civ) if civ is not None else (_ledger(cap.alignment_record) if cap is not None else None),
                   seen_by_others=_seen_by_others(kernel, holder))
        return out
    home = ages.homeworld(kernel, player_id)                        # a people the player guides: progenitor or counsel
    if home is not None and home.civilization is not None:
        from xylarium.kernel import knowledge
        holder = knowledge.holder_of_planet(home)
        worlds = relations._peoples(kernel).get(holder, [home])
        s = (syntropy.stats(kernel)["peoples"].get(holder) or {})
        from xylarium.kernel import guidance
        from xylarium.kernel import annals
        held = (annals.stats(kernel)["of"].get(holder) or {}).get("dominion") or 0
        out.update(people=home.civilization.name, worlds=len(worlds), population=sum(w.population for w in worlds),
                   dominion=held if held > len(worlds) else None,
                   crossed=mastery.crossed(kernel, holder), syntropy_slope=s.get("slope"),
                   ledger=_ledger(home.civilization), seen_by_others=_seen_by_others(kernel, holder),
                   galaxy_seeded=guidance.stats(kernel).get("seeded", 0),
                   galaxy_uplifts=guidance.stats(kernel).get("uplifts", 0),
                   minds_arisen=cosmos.stats(kernel).get("arisen", 0))
        if role == "progenitor":
            out["ancient"] = stats(kernel).get("ancients", {}).get(player_id)
            from xylarium.kernel import clocks
            epoch = (home.society.get("arisen") or {}).get("epoch")
            if epoch is not None:
                out["own_years"] = int((clocks.now(kernel, holder) - float(epoch)) * 1e9)
    return out


def render_progress(p: Dict[str, Any]) -> str:
    """The progress screen, as text."""
    lines = [f"=== PROGRESS: {p['role'].upper()} - year {p['year']:,} ==="]
    for key, label in (("polity", "Polity"), ("rule", "Rule"), ("people", "People"), ("worlds", "Worlds"), ("dominion", "Worlds held (history's scale)"),
                       ("own_years", "Years your people has lived"),
                       ("population", "Population"), ("treasury", "Treasury"), ("credits", "Credits"),
                       ("score", "Score"), ("rank", "Rank"), ("bounty", "Bounty on you"), ("citadels", "Citadels"),
                       ("shields", "Shields"), ("fighters", "Fighters"), ("strife", "Worlds that have risen"),
                       ("crossed", "Crossed to the stars"), ("syntropy_slope", "Growing (syntropy a year)"),
                       ("minds_arisen", "Minds the universe has raised"), ("galaxy_seeded", "Worlds seeded"),
                       ("galaxy_uplifts", "Younger minds taught")):
        if p.get(key) is not None:
            v = p[key]
            lines.append(f"  {label:<30} {v:,}" if isinstance(v, int) and not isinstance(v, bool) else
                         f"  {label:<30} {v}")
    led = p.get("ledger")
    if led:
        lines.append(f"  {'History reads':<30} {led['alignment']:+.3f}  (you tell yourself {led['doctrine']:+.3f})")
        lines.append(f"  {'Lives made / destroyed':<30} {led['made']:,.0f} / {led['destroyed']:,.0f}")
        if led["top_destroyed"]:
            lines.append("  Most destroyed by: " + "; ".join(f"{k} ({v:,.0f})" for k, v in led["top_destroyed"]))
    if p.get("seen_by_others") is not None:
        lines.append(f"  {'Others read you':<30} {p['seen_by_others']:+.3f}")
    return "\n".join(lines)


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    by: Dict[str, int] = {}
    for r in st["of"].values():
        by[r] = by.get(r, 0) + 1
    return {"seats": by, "tradewards": (st.get("tradewards") or {}).get("sector")}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="roles",
    state=lambda: {"of": {}, "tradewards": None},
    summary=summary,
))
