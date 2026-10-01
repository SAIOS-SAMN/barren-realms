"""
Xylarium relations: hierarchies between peoples, contracted - not decreed.

No empire is placed in the universe. A people becomes another's tributary when protection is worth more to it than
the tribute, and the stronger people takes it under its wing when the tribute is worth more than the defending -
both judged by their own minds (decide.agree). Empires are what such contracts add up to: trees of tributaries
around the peoples whose strength reaches furthest.

  STRENGTH     A people's power at a place: its worlds' troops and fighters, each falling off with distance as
               1/(1 + hops)^2 (the loss-of-strength gradient), and projected only as far as its ships can sail
               (sustenance.reach - a people without yards defends its own system only).
  THREAT       What a people stands to lose in a season: for every foreign world that can reach one of its worlds,
               the chance it raids (certain if that world is pressed for food, else the galaxy's measured rate of
               attacks - hunger and plunder - per world-season) x its odds against the defence (attack / (attack +
               defence)) x the staple it could seize. The strong neighbour is the threat a weak people buys off.
  PROTECTION   A patron's projected strength joins its tributary's defence (sustenance.raid reads shield()). Worth
               to the tributary: the threat it removes. Cost to the patron: the troops it expects to lose standing
               in the line (Lanchester's linear law, a tenth of the attack, in proportion to its share of the
               defence). The tribute splits the surplus between them evenly.
  FAMILY       A people does not raid its patron, its tributaries, or anyone under the same root.
  REVIEW       Every year the terms are re-read; when protection no longer leaves both better off (a grown tributary
               no longer needs it, a costly one is not worth defending) the tie ends, and a tributary that cannot pay
               is let go. A contract does not end on a passing misjudgement.
"""

from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import COMMODITY_CONFIG, PRICE_LEVEL, SURFACE_TROOP_RECRUIT_COST


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "relations")


def ties(kernel: Any) -> Dict[str, Dict[str, Any]]:
    """tributary people -> {patron, tribute_sol (a season), since, paid}"""
    return stats(kernel)["ties"]


def patron_of(kernel: Any, people: Optional[str]) -> Optional[str]:
    if not people or kernel is None or "relations" not in getattr(kernel, "state", {}):
        return None
    t = ties(kernel).get(people)
    return t["patron"] if t else None


def root(kernel: Any, people: Optional[str]) -> Optional[str]:
    seen = set()
    while people and people not in seen:
        seen.add(people)
        up = patron_of(kernel, people)
        if up is None:
            return people
        people = up
    return people


def family(kernel: Any, a: Optional[str], b: Optional[str]) -> bool:
    """Two peoples under one root (or one the other's patron): they do not raid each other."""
    return bool(a and b and root(kernel, a) == root(kernel, b))


# ---------------------------------------------------------------------- strength and threat
def _peoples(kernel: Any) -> Dict[str, List[Any]]:
    from xylarium.kernel import cache, sustenance

    def build() -> Dict[str, List[Any]]:
        out: Dict[str, List[Any]] = {}
        for sec in kernel.sectors.values():
            for p in sec.planets:
                if p.population > 0 and not getattr(p, "natives", None):
                    key = sustenance.people_of(p)
                    if key:
                        out.setdefault(key, []).append(p)
        return out
    return cache.memo(kernel, "relations_peoples", str(kernel.cycle_count), build, max_age=1)


def _reach_map(kernel: Any, w: Any) -> Dict[int, int]:
    from xylarium.kernel import cache, sustenance, topology
    r = sustenance.reach(kernel, w)
    return cache.memo(kernel, "relations_reach", f"{w.id}:{r}",
                      lambda: dict(topology.hops(kernel, w.sector_id, r)) if r > 0 else {w.sector_id: 0},
                      max_age=4 * _quarter())


def projected(kernel: Any, worlds: List[Any], sector_id: int) -> float:
    """A people's strength brought to bear on one system."""
    from xylarium.kernel.sustenance import _strength
    total = 0.0
    for w in worlds:
        h = _reach_map(kernel, w).get(sector_id)
        if h is not None:
            total += _strength(w) / (1.0 + h) ** 2
    return total


def guarded(kernel: Any, sup: str, by: Dict[str, List[Any]]) -> int:
    """How many worlds a patron's strength must already stand behind: its own and its direct tributaries'."""
    return len(by.get(sup, [])) + sum(len(by.get(t, [])) for t, tie in ties(kernel).items() if tie["patron"] == sup)


def shield(kernel: Any, planet: Any) -> float:
    """What a world's patron (and the patron's patron) adds to its defence - its strength shared among every world
    it stands behind (troops guarding one world are not guarding another)."""
    from xylarium.kernel import sustenance
    if kernel is None or "relations" not in getattr(kernel, "state", {}):
        return 0.0
    people = sustenance.people_of(planet)
    by = None
    extra = 0.0
    up = patron_of(kernel, people)
    seen = set()
    while up and up not in seen:
        seen.add(up)
        if by is None:
            by = _peoples(kernel)
        extra += projected(kernel, by.get(up, []), planet.sector_id) / max(1, guarded(kernel, up, by))
        up = patron_of(kernel, up)
    return extra


def _pressed_share(kernel: Any) -> float:
    """The galaxy's measured chance that a world attacks in a season - out of hunger or for plunder."""
    from xylarium.kernel import sustenance
    hist = sustenance.stats(kernel).get("raid_rate_hist") or []
    return sum(hist) / len(hist) if hist else 0.0


def threat(kernel: Any, people: str, worlds: List[Any], by: Dict[str, List[Any]], extra: Dict[int, float],
           base: float) -> Tuple[float, float]:
    """(expected staple value lost in a season, the attacks it would face) - with `extra` defence per system.
    A world's stores can be lost once: its expected loss is what it holds times the chance that at least one of
    the raids that can reach it succeeds."""
    from xylarium.kernel import staples
    from xylarium.kernel.sustenance import _strength
    loss = 0.0
    attacks = 0.0
    for w in worlds:
        d = _strength(w) + extra.get(w.sector_id, 0.0)
        food = staples.of(kernel, w)
        held = staples.surplus(kernel, w, food) * COMMODITY_CONFIG.get(food, {}).get("base_price", 20) * \
            PRICE_LEVEL.get(w.currency, 1.0)
        spared = 1.0
        for h_people, h_worlds in by.items():
            if h_people == people:
                continue
            for h in h_worlds:
                if w.sector_id not in _reach_map(kernel, h):
                    continue
                p = 1.0 if h.society.get("sustenance") in ("pressed", "stranded") else base
                a = _strength(h)
                if p <= 0 or a <= 0:
                    continue
                spared *= 1.0 - p * a / (a + d)
                attacks += p * a
        loss += held * (1.0 - spared)
    return loss, attacks


# ---------------------------------------------------------------------- contracts
def _capital(worlds: List[Any]) -> Any:
    return max(worlds, key=lambda w: (w.population, w.id))


def _terms(kernel: Any, sub: str, sup: str, by: Dict[str, List[Any]], base: float,
           bare: Optional[Tuple[float, float]] = None, existing: bool = False) -> Optional[Dict[str, float]]:
    """What protection is worth to `sub` and costs `sup`, a season, in SOL."""
    worlds, guard = by.get(sub, []), by.get(sup, [])
    if not worlds or not guard:
        return None
    # it would stand behind these too (a tie under review already counts them)
    share_out = max(1, guarded(kernel, sup, by) + (0 if existing else len(worlds)))
    extra = {w.sector_id: projected(kernel, guard, w.sector_id) / share_out for w in worlds}
    if not any(v > 0 for v in extra.values()):
        return None                                        # it cannot reach them: it cannot protect them
    bare, attacks = bare if bare is not None else threat(kernel, sub, worlds, by, {}, base)
    if bare <= 0:
        return None                                        # nothing threatens it: protection is worth nothing
    covered, _ = threat(kernel, sub, worlds, by, extra, base)
    value = bare - covered
    own = sum(projected(kernel, worlds, w.sector_id) for w in worlds) or 1.0
    share = sum(extra.values()) / (sum(extra.values()) + own)
    troop = SURFACE_TROOP_RECRUIT_COST * PRICE_LEVEL.get(_capital(guard).currency, 1.0)
    cost = 0.1 * attacks * share * troop
    if value <= cost:
        return None
    tribute = cost + (value - cost) / 2.0
    payable = _income_sol(kernel, worlds)                     # no more than it earns a season
    if payable < cost:
        return None
    return {"value": value, "cost": cost, "tribute": min(tribute, payable)}


def _income_sol(kernel: Any, worlds: List[Any]) -> float:
    """What a people's councils take in tax in a season (measured), in SOL: tribute is paid from it ahead of
    public services, as tribute always has been."""
    return sum(_to_sol(kernel, w.currency, max(0.0, float(w.society.get("fiscal_q", 0.0)))) for w in worlds)


def _read_fiscal(by: Dict[str, List[Any]]) -> None:
    """Each season: every world's tax take, smoothed (each colony tick adds to its accumulator)."""
    for worlds in by.values():
        for w in worlds:
            soc = w.society
            acc = soc.pop("fiscal_acc", 0)
            soc["fiscal_q"] = round(0.5 * float(soc.get("fiscal_q", acc)) + 0.5 * acc, 2)


def _to_sol(kernel: Any, cur: str, amount: float) -> float:
    return kernel.fx_market.to_sol_value(cur, amount) if cur != "SOL" else float(amount)


def _set_aside(kernel: Any, worlds: List[Any], tribute_sol: float) -> None:
    """Spread a season's tribute over the tributary's worlds, by their tax, as a per-cycle set-aside from services."""
    takes = [(w, _to_sol(kernel, w.currency, max(0.0, float(w.society.get("fiscal_q", 0.0))))) for w in worlds]
    total = sum(v for _, v in takes)
    for w, v in takes:
        share_sol = tribute_sol * (v / total) if total > 0 else 0.0
        rate = kernel.fx_market.rate(w.currency) if w.currency != "SOL" else 1.0
        w.society["tribute_tick"] = round(share_sol * rate / _quarter(), 3)


def _clear_aside(worlds: List[Any]) -> None:
    for w in worlds:
        w.society.pop("tribute_tick", None)


def _pay(kernel: Any, sub_worlds: List[Any], sup_cap: Any, amount_sol: float) -> float:
    """Tribute from the tributary's vaults (each in its own money, in proportion to what it holds) to the patron's
    capital, through the exchange: a transfer. Returns what was paid, in SOL."""
    have = [(w, _to_sol(kernel, w.currency, max(0, w.treasury))) for w in sub_worlds]
    total = sum(v for _, v in have)
    if total <= 0 or amount_sol <= 0:
        return 0.0
    part = min(1.0, amount_sol / total)
    paid = 0.0
    for w, v in have:
        local = int(max(0, w.treasury) * part)
        if local <= 0:
            continue
        w.treasury -= local
        if w.currency == sup_cap.currency:
            sup_cap.treasury += local
        else:
            got, _ = kernel.fx_market.convert(w.currency, sup_cap.currency, local)
            sup_cap.treasury += got
        paid += v * part
    return paid


def _consider(kernel: Any, sub: str, by: Dict[str, List[Any]], base: float) -> Optional[str]:
    from xylarium.kernel import decide
    worlds = by.get(sub)
    if not worlds or sub.startswith("captain:") and not _ai(kernel, sub):
        return None
    cap = _capital(worlds)
    bare = threat(kernel, sub, worlds, by, {}, base)
    if bare[0] <= 0:
        return None
    best = None
    for sup, guard in by.items():
        if sup == sub or root(kernel, sup) == sub or (sup.startswith("captain:") and not _ai(kernel, sup)):
            continue                                       # no one becomes its own vassal's vassal; players by command
        if not any(w.sector_id in _reach_map(kernel, g) for g in guard for w in worlds):
            continue                                       # its ships do not reach them
        t = _terms(kernel, sub, sup, by, base, bare)
        if t is not None and (best is None or t["value"] - t["tribute"] > best[1]["value"] - best[1]["tribute"]):
            best = (sup, t)
    if best is None:
        return None
    return offer(kernel, sub, best[0], by, best[1])


def offer(kernel: Any, sub: str, sup: str, by: Dict[str, List[Any]], t: Optional[Dict[str, float]] = None,
          base: Optional[float] = None) -> Optional[str]:
    """`sup` offers `sub` protection for tribute: both judge their own side - through how well they understand
    each other (contact.misread) - and the tie stands only if both accept."""
    from xylarium.kernel import contact, decide
    if sub in ties(kernel) or sub not in by or sup not in by or root(kernel, sup) == sub:
        return None
    if t is None:
        t = _terms(kernel, sub, sup, by, _pressed_share(kernel) if base is None else base)
        if t is None:
            return None
    cap, patron_cap = _capital(by[sub]), _capital(by[sup])
    understood = contact.intelligibility(kernel, sub, sup, by)
    ms = contact.misread(decide.mind_of_planet(kernel, cap), understood)
    mp = contact.misread(decide.mind_of_planet(kernel, patron_cap), understood)
    sub_side = decide.option("accept_protection", decide.worth(kernel, t["tribute"], ms),
                             decide.worth(kernel, t["value"], ms))
    sup_side = decide.option("extend_protection", decide.worth(kernel, t["cost"], mp),
                             decide.worth(kernel, t["tribute"], mp))
    if not decide.agree(kernel, sub_side, sup_side, ms, mp, sub, sup):
        return None
    ties(kernel)[sub] = {"patron": sup, "tribute_sol": round(t["tribute"], 2), "since": kernel.cycle_count, "paid": 0.0}
    st = stats(kernel)
    st["formed"] += 1
    from xylarium.kernel import primordial
    primordial.first(kernel, "first_tributary", f"{sub} under {sup}")
    if sum(1 for x in ties(kernel).values() if x["patron"] == sup) >= 3:
        primordial.first(kernel, "first_empire", sup)
    return f"[RELATIONS] {_name(kernel, sub)} accepts the protection of {_name(kernel, sup)} for a tribute."


def _review(kernel: Any, sub: str, tie: Dict[str, Any], by: Dict[str, List[Any]], base: float) -> Optional[str]:
    from xylarium.kernel import decide
    sup = tie["patron"]
    if sub not in by or sup not in by:
        ties(kernel).pop(sub, None)
        stats(kernel)["ended"] += 1
        return None
    t = _terms(kernel, sub, sup, by, base, existing=True)
    # a contract is a commitment: it stands while it still leaves both sides better off on expectation - neither
    # walks away on a passing misjudgement
    keep = t is not None
    if keep:
        tie["tribute_sol"] = round(t["tribute"], 2)
        return None
    _clear_aside(by.get(sub, []))
    ties(kernel).pop(sub, None)
    stats(kernel)["ended"] += 1
    stats(kernel)["dissolved"] = stats(kernel).get("dissolved", 0) + 1
    return f"[RELATIONS] {_name(kernel, sub)} and {_name(kernel, sup)} part ways."


def _ai(kernel: Any, people: str) -> bool:
    cap = kernel.captains.get(people.partition(":")[2])
    return cap is not None and getattr(cap, "is_ai", False)


def _name(kernel: Any, people: str) -> str:
    from xylarium.kernel.sustenance import people_name
    return people_name(kernel, people)


def quarter(kernel: Any) -> List[str]:
    logs: List[str] = []
    by = _peoples(kernel)
    _read_fiscal(by)
    # tribute, every season
    for sub, tie in list(ties(kernel).items()):
        sup = tie["patron"]
        if sub not in by or sup not in by:
            continue
        _set_aside(kernel, by[sub], tie.get("tribute_sol", 0.0))
        due = tie.get("tribute_sol", 0.0) + tie.get("arrears", 0.0)
        paid = _pay(kernel, by[sub], _capital(by[sup]), due)
        tie["paid"] += paid
        stats(kernel)["tribute_sol"] += paid
        tie["arrears"] = max(0.0, due - paid)
        if tie["arrears"] > 4 * tie.get("tribute_sol", 0.0):          # a year behind: the patron lets it go
            _clear_aside(by[sub])
            ties(kernel).pop(sub, None)
            stats(kernel)["ended"] += 1
            stats(kernel)["defaulted"] = stats(kernel).get("defaulted", 0) + 1
            logs.append(f"[RELATIONS] {_name(kernel, sub)} cannot pay its tribute and goes its own way.")
    if (kernel.cycle_count // _quarter()) % 4:
        return logs
    base = _pressed_share(kernel)
    for sub, tie in list(ties(kernel).items()):
        log = _review(kernel, sub, tie, by, base)
        if log:
            logs.append(log)
    for sub in sorted(by):
        if sub in ties(kernel):
            continue
        log = _consider(kernel, sub, by, base)
        if log:
            logs.append(log)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    by = _peoples(kernel)
    trees: Dict[str, Dict[str, int]] = {}
    for people, worlds in by.items():
        r = root(kernel, people)
        if r is None:
            continue
        tr = trees.setdefault(r, {"peoples": 0, "worlds": 0, "depth": 0})
        tr["peoples"] += 1
        tr["worlds"] += len(worlds)
        d, up = 0, patron_of(kernel, people)
        while up and d < 20:
            d += 1
            up = patron_of(kernel, up)
        tr["depth"] = max(tr["depth"], d)
    empires = sorted(((r, v) for r, v in trees.items() if v["peoples"] > 1), key=lambda kv: -kv[1]["worlds"])
    ages = sorted((kernel.cycle_count - t["since"]) / 100.0 for t in st["ties"].values())
    return {"ties": len(st["ties"]), "formed": st["formed"], "ended": st["ended"],
            "defaulted": st.get("defaulted", 0), "dissolved": st.get("dissolved", 0),
            "median_tie_years": ages[len(ages) // 2] if ages else 0.0,
            "tribute_sol": round(st["tribute_sol"]), "empires": len(empires),
            "largest": [{"root": r, **v} for r, v in empires[:3]],
            "independent": sum(1 for v in trees.values() if v["peoples"] == 1)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="relations",
    state=lambda: {"ties": {}, "formed": 0, "ended": 0, "tribute_sol": 0.0},
    season=quarter,
    summary=summary,
))
