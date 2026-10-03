"""
Xylarium federations: founded by peoples that meet among the stars - not seated at the beginning of the world.

In a universe that begins at its Big Bang no federation, compact, imperium or choir is waiting. Peoples that cross
to the stars (mastery.py), meet (contact.py) and bind themselves by protection and pacts (relations.py) form blocs.
A bloc's law is enforced only by its strongest member's arm. A FEDERATION is what a bloc founds when its members
judge common law worth more than going without it:

  WORTH     each member's trade with the others, made as safe as the members' joint strength makes it (the sum of
            their arms where it lives, not the strongest one's) instead of the strongest one's alone - over what its
            bloc's law already gives (relations.enforcement);
  COST      its dues - half of that gain, paid to the common treasury (the surplus split, as tribute is) - and the
            distance between the doctrine the federation keeps and the one it would keep alone (below);
  REACH     a member must hear its federation's decisions within its own planning horizon: a message crosses folded
            space in a jump a hop, light in its own time - so peoples that have not crossed cannot govern together
            across the stars, and the speed of light, not a rule, bounds a sublight federation.

Every member agrees by its own mind or there is no federation (decide.agree). Its CHARTER weighs votes equally, by
people, or by strength - each member votes for the weighting that gives it the most say, and the most votes win.

Its DOCTRINE toward peoples that have not crossed - the galactic policy deck's cards (factions.py), ALPHA strict
non-interference to DELTA unrestricted exploitation - is the weighted median of what its members' alignments would
keep: the Light leaves younger peoples to find the stars on their own or watches unseen; the Dark takes what it
can reach. The doctrine binds its members (guidance.py will not uplift, ruin.py prices the federation's sanction on
a strike) and governs its territory as the old powers' cards did. The old names - Federation Senate, ISSE Frontier
Compact, Aurelian Imperium, Choir of the Pyre - are what such charters have been called; a cosmic universe's
federations name themselves.

THE QUIET SKY. Each year the share of peoples that have not crossed and whose systems no other people's ships or
territory have touched is reported: the Fermi question, measured in this universe.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

CHARTERS = ("equal", "population", "strength")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "federation")


def _alignment(kernel: Any, worlds: List[Any]) -> float:
    from xylarium.kernel import sustenance
    return float(sustenance._alignment(kernel, max(worlds, key=lambda p: p.population)) or 0.0)


def preferred_card(alignment: float) -> str:
    """The doctrine a people would keep alone, by its alignment: the Light leaves the young alone, the Dark takes."""
    if alignment >= 0.5:
        return "ALPHA"
    if alignment >= 0.15:
        return "BETA"
    if alignment >= -0.15:
        return "GAMMA"
    return "DELTA"


def member_of(kernel: Any, people: Optional[str]) -> Optional[str]:
    return stats(kernel)["members"].get(people) if people else None


def card_of(kernel: Any, people: Optional[str]) -> Optional[str]:
    fid = member_of(kernel, people)
    f = kernel.factions.factions.get(fid) if fid else None
    return f.card if f is not None else None


def forbids(kernel: Any, people: Optional[str], act: str, young: Optional[str]) -> bool:
    """Does this people's federation's doctrine forbid an act ('uplift', 'exploit', 'contact') toward a people that
    has not crossed?"""
    from xylarium.config import POLICY_CARDS
    from xylarium.kernel import mastery
    card = card_of(kernel, people)
    if card is None or mastery.crossed(kernel, young):
        return False
    allows = POLICY_CARDS.get(card, {}).get("allows", set())
    if act == "uplift" and "contact_if_ready" in allows:
        return True                                          # it is not ready: it has not crossed
    return act not in allows


def sanction_sol(kernel: Any, people: Optional[str]) -> float:
    """What a member stands to lose for breaking its federation's doctrine: its fellows' joint output over a year."""
    from xylarium.kernel import relations
    fid = member_of(kernel, people)
    if fid is None:
        return 0.0
    by = relations._peoples(kernel)
    return 4.0 * sum(relations._output_sol(kernel, by[m]) for m, f in stats(kernel)["members"].items()
                     if f == fid and m != people and m in by)


def _latency_years(kernel: Any, a: Any, b: Any, both_crossed: bool) -> float:
    from xylarium.kernel import cosmos, topology
    if a.sector_id == b.sector_id:
        return 0.0
    if both_crossed:
        return topology.hops(kernel, a.sector_id, 30).get(b.sector_id, 30) / 100.0   # a jump a hop, a cycle each
    d = cosmos.distance_kpc(kernel, a.sector_id, b.sector_id)
    return float("inf") if d is None else d * 3261.56


def _gain(kernel: Any, people: str, members: List[str], by: Dict[str, List[Any]]) -> float:
    """A member's yearly gain from common law: its trade with its fellows, as safe as their joint arm makes it."""
    from xylarium.kernel import contact, relations
    from xylarium.kernel.sustenance import _strength
    others = contact.contacts(kernel, by).get(people, {})
    total = sum(others.values())
    if total <= 0:
        return 0.0
    where = relations._capital(by[people]).sector_id
    joint = sum(relations.projected(kernel, by[m], where) / max(1, relations.guarded(kernel, m, by))
                for m in members if m in by)
    gain = 0.0
    for b, n in others.items():
        if b not in members or b not in by:
            continue
        rogue = max(_strength(relations._capital(by[people])), _strength(relations._capital(by[b])))
        e_fed = joint / (joint + rogue) if joint + rogue > 0 else 0.0
        gain += n * max(0.0, e_fed - relations.enforcement(kernel, people, b, by))
    return 4.0 * relations._output_sol(kernel, by[people]) * gain / total


def _charter(kernel: Any, members: List[str], by: Dict[str, List[Any]]) -> Tuple[str, Dict[str, float]]:
    from xylarium.kernel.sustenance import _strength
    weights = {
        "equal": {m: 1.0 for m in members},
        "population": {m: float(sum(p.population for p in by[m])) for m in members},
        "strength": {m: float(sum(_strength(p) for p in by[m])) for m in members},
    }
    votes = {c: 0 for c in CHARTERS}
    for m in members:
        share = {c: weights[c][m] / max(1e-9, sum(weights[c].values())) for c in CHARTERS}
        votes[max(CHARTERS, key=lambda c: (share[c], c == "equal"))] += 1
    charter = max(CHARTERS, key=lambda c: (votes[c], c == "equal"))
    return charter, weights[charter]


def _doctrine(kernel: Any, members: List[str], weights: Dict[str, float], by: Dict[str, List[Any]]) -> str:
    """The weighted median of what the members would keep alone."""
    from xylarium.config import POLICY_ORDER
    prefs = sorted((POLICY_ORDER.index(preferred_card(_alignment(kernel, by[m]))), weights.get(m, 0.0))
                   for m in members)
    half, acc = sum(w for _, w in prefs) / 2.0, 0.0
    for idx, w in prefs:
        acc += w
        if acc >= half:
            return POLICY_ORDER[idx]
    return POLICY_ORDER[prefs[-1][0]]


def _name(kernel: Any, fid: int) -> str:
    from xylarium.kernel import scheduler
    from xylarium.kernel.natives import _name as people_name
    rng = scheduler.rng(kernel, "federation", fid)
    form = ["Concord", "Compact", "Union", "League", "Accord", "Covenant", "Assembly", "Commonwealth"]
    return f"The {form[int(rng.random() * len(form))]} of {people_name(rng)}"


def _found(kernel: Any, members: List[str], by: Dict[str, List[Any]]) -> Optional[str]:
    from xylarium.config import POLICY_CARDS
    from xylarium.kernel import history
    from xylarium.kernel.factions import Faction
    st = stats(kernel)
    st["next"] += 1
    fid = f"FED{st['next']}"
    charter, weights = _charter(kernel, members, by)
    card = _doctrine(kernel, members, weights, by)
    cap = max((relations_capital(by[m]) for m in members), key=lambda p: p.population)
    f = Faction(id=fid, name=_name(kernel, st["next"]), kind="FOUNDED", card=card,
                sapience_threshold=0.0, uplift_limit=0 if card == "ALPHA" else 1,
                enforcement="SANCTION", warrant=0,
                alignment=sum(_alignment(kernel, by[m]) for m in members) / len(members),
                capital_sector=cap.sector_id, capital_planet=cap.id)
    kernel.factions.factions[fid] = f
    st["feds"][fid] = {"members": list(members), "charter": charter, "founded": kernel.cycle_count}
    for m in members:
        st["members"][m] = fid
    _territory(kernel, fid, by)
    history.event(kernel, "FEDERATION_FOUNDED", f"{f.name} is founded", sector_id=cap.sector_id,
                  actors=list(members),
                  cause=f"{len(members)} peoples among the stars judged common law worth its dues; votes weighed "
                        f"{'equally' if charter == 'equal' else 'by ' + charter}; doctrine toward the young: "
                        f"{POLICY_CARDS[card]['name']}",
                  data={"charter": charter, "card": card})
    return f"[FEDERATION] {f.name} is founded by {len(members)} peoples ({POLICY_CARDS[card]['name']})."


def relations_capital(worlds: List[Any]) -> Any:
    from xylarium.kernel import relations
    return relations._capital(worlds)


def _territory(kernel: Any, fid: str, by: Dict[str, List[Any]]) -> None:
    fm = kernel.factions
    f = fm.factions[fid]
    systems = sorted({p.sector_id for m, g in stats(kernel)["members"].items() if g == fid and m in by for p in by[m]})
    f.territory = [s for s in systems if fm.territory_index.get(s) in (None, fid)]
    fm.reindex()


def season(kernel: Any) -> List[str]:
    """Once a year: blocs weigh founding, federations admit and lose members, and the sky is measured."""
    from xylarium.kernel import cosmos, decide, mastery, relations
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    by = relations._peoples(kernel)
    logs: List[str] = []
    # members that are gone leave; a federation of fewer than two dissolves
    for m in [m for m in st["members"] if m not in by]:
        st["members"].pop(m)
    for fid, rec in list(st["feds"].items()):
        rec["members"] = [m for m in rec["members"] if st["members"].get(m) == fid]
        if len(rec["members"]) < 2:
            for m in rec["members"]:
                st["members"].pop(m, None)
            f = kernel.factions.factions.pop(fid, None)
            kernel.factions.reindex()
            st["feds"].pop(fid)
            st["dissolved"] += 1
            if f is not None:
                logs.append(f"[FEDERATION] {f.name} dissolves.")
        else:
            _territory(kernel, fid, by)
    # blocs among the crossed weigh common law
    groups: Dict[str, List[str]] = {}
    for p in by:
        if mastery.crossed(kernel, p):
            groups.setdefault(relations.bloc(kernel, p), []).append(p)
    for _, members in sorted(groups.items()):
        loose = [m for m in members if m not in st["members"]]
        if not loose or len(members) < 2:
            continue
        existing = {st["members"][m] for m in members if m in st["members"]}
        candidates = sorted(members) if not existing else sorted(loose)
        cap = max((relations._capital(by[m]) for m in members), key=lambda p: p.population)
        agreed = []
        for m in candidates:
            home = relations._capital(by[m])
            m_mind = decide.mind_of_planet(kernel, home)
            if 2.0 * _latency_years(kernel, home, cap, True) > decide.horizon(m_mind) / 4.0:
                continue                                      # it would hear the federation too late to govern with it
            gain = _gain(kernel, m, members, by)
            card_now = _doctrine(kernel, members, {x: 1.0 for x in members}, by)
            from xylarium.config import POLICY_ORDER
            gap = abs(POLICY_ORDER.index(card_now) - POLICY_ORDER.index(preferred_card(_alignment(kernel, by[m]))))
            # a people of the Light trusts its fellows' word: common law costs it less in dues and in watching
            trust = max(0.0, _alignment(kernel, by[m]))
            cost = gain / 2.0 * (1.0 - trust) + gain * gap / 3.0
            if decide.choose(kernel, [decide.option("join_federation", cost, gain, aim="secure")], m_mind, m, "federation"):
                agreed.append(m)
        if existing:
            fid = sorted(existing)[0]
            for m in agreed:
                st["members"][m] = fid
                st["feds"][fid]["members"].append(m)
            if agreed:
                _territory(kernel, fid, by)
        elif len(agreed) >= 2:
            line = _found(kernel, agreed, by)
            if line:
                logs.append(line)
    # the quiet sky: young peoples whose systems no other people has touched
    young = [p for p in by if not mastery.crossed(kernel, p)]
    touched = 0
    for y in young:
        home = relations._capital(by[y])
        sec = kernel.sectors.get(home.sector_id)
        foreign = any(c in kernel.captains and f"captain:{c}" != y for c in (getattr(sec, "captains", None) or []))
        claimed = kernel.factions.territory_index.get(home.sector_id) not in (None, "NONE")
        touched += 1 if (foreign or claimed) else 0
    st["young"], st["touched"] = len(young), touched
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    out = {"federations": len(st["feds"]), "members": len(st["members"]), "dissolved": st["dissolved"]}
    if st.get("young"):
        out["quiet_sky"] = round(1.0 - st["touched"] / st["young"], 3)
    return out


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="federation", state=lambda: {"feds": {}, "members": {}, "next": 0, "dissolved": 0,
                                                               "young": 0, "touched": 0},
                             season=season, summary=summary))
