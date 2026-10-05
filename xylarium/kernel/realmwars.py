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
from typing import Any, Dict, List, Optional, Tuple

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


def weigh(kernel: Any, who: str, other: str, sector: int, fighting: bool = False) -> Dict[str, Any]:
    """Whether a people means to take - or, at war, to keep fighting for - a system another holds: what the war would
    gain against all it would cost, as its own council judges it (decide.choose, as a raid is weighed - misread as
    far as it does not understand the other). Nothing here says war; the reckoning does:

      GAIN      the system's yield over the council's horizon - its worlds' output and the tolls its lanes took last
                year - times the odds of taking it (Lanchester's linear law, as a raid: attack over attack and defence)
      POSITION  each side's strength worn by its supply line: the hops from its capital to the front (the defender
                fights on interior lines when the front is at its door)
      FRONTS    a people already at war has its strength split across every front it holds
      ALLIES    the defence is the holder's capital, its patron's shield, and its allies' and federation partners' arms
      UNKNOWN   what it cannot read of the other (contact.intelligibility) it cannot rule out: the defence is weighed
                at its worst, over how well it understands them - strangers are not invaded; the known are reckoned
      LIVES     each side loses a tenth of the other's strength an engagement, over as many engagements as the
                defence outweighs the attack - its own troops at their price, and its own dead, whatever it is
      FUEL      its fleet burns reaction mass every hop to the front, every engagement, at the market's price
      SUPPLY    and pays each lane's toll and tithe on the way
      LEVY      the economy it forgoes while levied, a share a year for the war's expected years
      TRADE     the share of its output riding on its contracts with the other, lost while they are at war
      WEB       inside an established realm war is an outbreak in a shared body: everything it shares with the
                peoples bound up with it (trade, its lanes' tolls) is at stake when the other is inside its web of
                bonds - and, wherever the war is, its trade with every partner whose doctrine forbids taking, who
                will turn from an aggressor; on a frontier, with no web, nothing - so war lives where realms are not
      SURVIVAL  a people whose sun is dying gains, from a system that can hold it, its own people's lives at the odds
      BETRAYAL  a people whose plea for help went unanswered owes the realm nothing: its web is no cost to it
      ORDER     the other side's dead, a life's work each (alignment.lives_of_sol), weighed by its own whole-history
                character: the Light count them as their own loss, the Dark discount them - but no people, however
                dark, fights at no cost: its own dead, its fuel and its position are counted by all
    Returns the reckoning and whether its council chose war."""
    from xylarium.config import PRICE_LEVEL, SURFACE_TROOP_RECRUIT_COST
    from xylarium.kernel import alignment, contact, decide, polity, relations, spheres, transit
    from xylarium.kernel.sustenance import _strength
    by = relations._peoples(kernel)
    mine, theirs = spheres._home(kernel, who), spheres._home(kernel, other)
    if mine is None or theirs is None or sector not in kernel.sectors:
        return {"war": False, "why": "no capital to fight from"}
    from xylarium.kernel import ascendance
    if ascendance.ruling(kernel, other) in ("quarantine", "pending"):
        return {"war": False, "why": "the steward shields a people it holds at home"}
    fronts = (0 if fighting else 1) + sum(1 for w in stats(kernel)["wars"].values() if w["status"] == "open"
                                          and who in (w.get("taker"), w.get("holder")))
    path = kernel.find_path(mine.sector_id, sector) or []
    theirs_path = kernel.find_path(theirs.sector_id, sector) or []
    hops, their_hops = max(0, len(path) - 1), max(0, len(theirs_path) - 1)
    attack = _strength(mine) / max(1, fronts) / (1 + hops)
    allies = [b["b"] if b["a"] == other else b["a"] for b in spheres.stats(kernel)["bonds"].values()
              if other in (b["a"], b["b"]) and b["kind"] in ("alliance", "federation")]
    defend = (_strength(theirs) + relations.shield(kernel, theirs) + sum(
        _strength(spheres._home(kernel, a)) for a in allies if spheres._home(kernel, a) is not None)) / (1 + their_hops)
    from xylarium.kernel import borders                     # the works at the border stand at the front, in full
    defend += borders.fortification(kernel, sector)
    understood = max(0.05, contact.intelligibility(kernel, who, other, by))
    defend = defend / understood                            # what it cannot read, it cannot rule out: the worst case
    if attack <= 0:
        return {"war": False, "why": "nothing to fight with"}
    odds = attack / (attack + defend)
    engagements = max(1.0, defend / attack)
    level = PRICE_LEVEL.get(mine.currency, 1.0)
    m = decide.mind_of_planet(kernel, mine)                 # its own judgement; the unknown is in the defence above
    worlds = [w for w in kernel.sectors[sector].planets if w.population > 0]
    tolls = sum(transit.charge_cr(kernel, x, sector)[1] * (transit.stats(kernel)["lanes"].get(transit.key(x, sector))
                                                           or {}).get("last_year", 0)
                for x in kernel.sectors[sector].warps if x in kernel.sectors) / 4.0
    gain = odds * decide.worth(kernel, relations._output_sol(kernel, worlds) + tolls, m)
    own_lost = 0.1 * defend * engagements                     # its own troops, lost to the other's strength
    their_lost = 0.1 * attack * engagements
    troops = own_lost * SURFACE_TROOP_RECRUIT_COST * level
    hulls = max(1.0, attack * (1 + hops) / max(1.0, _fleet_strength(kernel)))   # the ships its force fills
    fuel = engagements * hops * hulls * transit._typical_hop(kernel)
    supply = engagements * hulls * sum(sum(transit.charge_cr(kernel, x, y)[1:]) for x, y in zip(path, path[1:]))
    out_q = relations._output_sol(kernel, by.get(who, []))
    levy = laws_pv(kernel, out_q / len(polity.BOOKS), 4.0 * engagements, m, mine.currency)
    talks = contact.contacts(kernel, by).get(who, {})
    trade = decide.worth(kernel, out_q * talks.get(other, 0) / max(1, sum(talks.values())), m)
    life = 1.0 / max(1e-12, alignment.lives_of_sol(kernel, 1.0, mine))            # a life's work, in its money
    per = SURFACE_TROOP_RECRUIT_COST * level
    own_dead = alignment.lives_of_sol(kernel, own_lost * per, mine) * life     # every people counts its own dead
    civ = getattr(mine, "civilization", None)
    light = (1.0 + alignment.character(civ)) / 2.0 if civ is not None else 0.5   # 1 the Light, 0 absolute darkness
    order = light * alignment.lives_of_sol(kernel, their_lost * per, mine) * life
    integration, inside = _integration(kernel, who, other, m)
    betrayed = who in _unanswered(kernel)                       # it asked for help and none came: it owes nothing
    if betrayed:
        integration = 0.0
    survival = 0.0
    if (getattr(mine, "society", {}) or {}).get("forecast"):     # its own sun is dying: a world that can hold it
        from xylarium.kernel import biosphere
        room = sum(max(0, int(biosphere.carrying_capacity(kernel, w)) - int(w.population))
                   for w in kernel.sectors[sector].planets)
        survival = odds * min(room, int(mine.population)) * life
    gain += survival
    cost = troops + own_dead + fuel + supply + levy + trade + order + integration
    pick = decide.choose(kernel, [decide.option("war", cost, gain)], m, who, other, "realm_war", int(fighting))
    return {"war": pick is not None, "gain": gain, "odds": odds, "troops": troops, "own_dead": own_dead, "fuel": fuel,
            "integration": integration, "inside": inside, "betrayed": betrayed, "survival": survival,
            "supply": supply, "levy": levy, "trade": trade, "order": order, "fronts": fronts, "hops": hops,
            "their_hops": their_hops, "allies": allies, "attack": attack, "defend": defend}


def _web(kernel: Any, who: str) -> set:
    """The peoples a people is bound up with: every network reachable through bonds of trust (federations,
    conglomerates, alliances - not standoffs), itself included."""
    from xylarium.kernel import spheres
    bonds = [b for b in spheres.stats(kernel)["bonds"].values() if b["kind"] in ("federation", "conglomerate",
                                                                                  "alliance")]
    seen, todo = {who}, [who]
    while todo:
        x = todo.pop()
        for b in bonds:
            if x in (b["a"], b["b"]):
                y = b["b"] if b["a"] == x else b["a"]
                if y not in seen:
                    seen.add(y)
                    todo.append(y)
    return seen


def _integration(kernel: Any, who: str, other: str, m: Dict[str, float]) -> Tuple[float, bool]:
    """What a war would sever of the economy a people shares: its trade with every people bound up with it and the
    tolls its lanes collect, over its horizon. If the other is inside that web, the war is an outbreak inside the
    body it lives in - all of it is at stake; outside, only what it shares with those bound to the other too."""
    from xylarium.kernel import contact, decide, relations, transit
    by = relations._peoples(kernel)
    web = _web(kernel, who)
    inside = other in web
    theirs = _web(kernel, other)
    talks = contact.contacts(kernel, by).get(who, {})
    total = max(1, sum(talks.values()))
    out_q = relations._output_sol(kernel, by.get(who, []))
    at_stake = [p for p in web - {who} if inside or p in theirs or _abhors(kernel, p)]
    trade_q = out_q * sum(talks.get(p, 0) for p in at_stake) / total
    tolls_q = sum(r["collected"] for k, r in transit.stats(kernel)["lanes"].items()
                  if transit.owner(kernel, *map(int, k.split("-"))) == who) / max(1.0, kernel.cycle_count / 25.0) \
        if (inside or at_stake) else 0.0
    return decide.worth(kernel, trade_q + tolls_q, m), inside


def _abhors(kernel: Any, partner: str) -> bool:
    """Would a partner turn from an aggressor: its own doctrine forbids taking from others (its card allows no
    exploiting or collecting) - so a war of taking costs the aggressor its trade with it, wherever the war is."""
    from xylarium.config import POLICY_CARDS
    from xylarium.kernel import alignment, federation, spheres
    home = spheres._home(kernel, partner)
    civ = getattr(home, "civilization", None) if home is not None else None
    if civ is None:
        return False
    allows = POLICY_CARDS.get(federation.preferred_card(alignment.doctrine(civ)), {}).get("allows", set())
    return not ({"exploit", "collect"} & set(allows))


def _unanswered(kernel: Any) -> Dict[str, int]:
    from xylarium.kernel import exodus
    return exodus.stats(kernel).get("unanswered", {}) if "exodus" in kernel.state else {}


def _fleet_strength(kernel: Any) -> float:
    """What one ship carries into a fight, on the mean: the crews' own fighters."""
    ships = [float(getattr(c.ship, "fighters", 0) or 0) for c in kernel.captains.values()]
    ships = [x for x in ships if x > 0]
    return sum(ships) / len(ships) if ships else 1.0


def laws_pv(kernel: Any, flow_q: float, quarters: float, m: Dict[str, float], currency: str) -> float:
    from xylarium.kernel import decide, laws
    return laws.present_value(flow_q, min(quarters, decide.horizon(m)), decide.rate(kernel, currency))


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


def _attrition(kernel: Any, war: Dict[str, Any], r: Dict[str, Any]) -> None:
    """A year's engagement, Lanchester's linear law: each capital loses a tenth of the other's effective strength -
    so a people that fights on every front bleeds out, and its next reckoning is worse."""
    from xylarium.kernel import spheres
    from xylarium.kernel import borders
    for who, lost in ((war["taker"], 0.1 * r.get("defend", 0.0)), (war.get("holder"), 0.1 * r.get("attack", 0.0))):
        if who == war.get("holder") and war.get("sector") is not None:
            lost = borders.wear(kernel, war["sector"], lost)       # the blows fall on the works first
        home = spheres._home(kernel, who) if who else None
        if home is None or lost <= 0:
            continue
        take = int(min(home.garrison_troops or 0, lost))
        home.garrison_troops = max(0, int(home.garrison_troops or 0) - take)
        rest = int(lost) - take
        if rest > 0:
            home.fighters = max(0, int(home.fighters or 0) - rest)
    war["years"] = war.get("years", 0) + 1


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
    if war.get("sector") is not None and war["by"] == war["from"]:      # each year its council weighs it again
        r = weigh(kernel, war["taker"], war["holder"], war["sector"], fighting=True)
        if not r["war"]:
            _end(kernel, war, "exhausted", f"the {war['taker'].split(':', 1)[-1]} sue for peace: the war is no "
                                           f"longer worth its dead, its fuel and its levies")
            logs.append(f"[GALACTIC WAR] The {war['taker'].split(':', 1)[-1]} sue for peace over "
                        f"{stewardship.realm_name(war['against'])}.")
            return
        _attrition(kernel, war, r)
        from xylarium.kernel.sustenance import _strength
        held = spheres._home(kernel, war["holder"]) if war.get("holder") else None
        if held is not None and _strength(held) <= 0:          # no one is left to hold it: it falls
            spheres.transfer(kernel, war["sector"], war["taker"])
            _end(kernel, war, "taken", f"the {war['holder'].split(':', 1)[-1]} had no one left to hold it")
            logs.append(f"[GALACTIC WAR] The {war['taker'].split(':', 1)[-1]} take "
                        f"{stewardship.realm_name(war['against'])}: no one was left to hold it.")
            return
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
