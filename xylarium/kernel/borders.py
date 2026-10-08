"""
Xylarium borders: the steward's border book - a realm keeps its boundaries defended, and a defended realm keeps its
peace.

A realm's BORDER is every system of it that a network outside its web of bonds can reach next: a lane from a system
another, unbonded network holds (a standoff's, a stranger's). Each border has a THREAT - the strongest such
neighbour's arms (its capital's), worn by the hops from that capital to the border, as a war's attack is
(realmwars.weigh) - and a DEFENCE: the fortification built there, and the keeper's own arms, worn by its hops. Where
threat exceeds defence, the border is in deficit; the steward's book leads with the deepest.

The steward RULES TO FORTIFY: its realm's keeper is asked to build the works the deficit wants, at the troops'
price - and builds them as far as its own council judges the border worth it (decide.choose: what the border system
yields and its lanes collect, over its horizon, against the works' price), and as far as its treasury allows.
Fortifications stand where they are built; a war wears them down (realmwars' attrition reaches the works first).
In the war reckoning a fortified border counts its works in full on the defender's side, without the wear of distance:
they are at the front.

EMBARGO. A people that has opened a war of taking (an open realm war, as the taker) is turned back - its ships, its
haulers - on every lane of a people whose doctrine forbids taking (transit.blocks). It may still trade covertly.

STANDOFFS. A hostile border is weighed again each year by the one that arrived: what was not worth a war may become
so if the border falls out of repair, and a well-kept one never does.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import mindcore as mc
from xylarium.kernel.fx import hub as _hub


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "borders")


def fortification(kernel: Any, sector: int) -> float:
    """The works standing at a system, in the strength they add to its defence."""
    if not hasattr(kernel, "state"):
        return 0.0
    return float(stats(kernel)["forts"].get(str(sector), 0.0))


def wear(kernel: Any, sector: int, lost: float) -> float:
    """A war's blows fall on the works first; what they do not absorb, the garrison takes. Returns what is left."""
    f = fortification(kernel, sector)
    take = min(f, max(0.0, lost))
    if take:
        stats(kernel)["forts"][str(sector)] = f - take
    return max(0.0, lost - take)


def _hops(kernel: Any, a: int, b: int) -> int:
    path = kernel.find_path(a, b) or []
    return max(0, len(path) - 1) if path else 10 ** 6


def threats(kernel: Any, realm: str) -> Dict[int, Tuple[float, Optional[str]]]:
    """Each border system of a realm and its threat: the strongest unbonded neighbour network's arms reaching it."""
    from xylarium.kernel import realmwars, spheres
    from xylarium.kernel.sustenance import _strength
    st = spheres.stats(kernel)
    keeper = spheres.presence(kernel, realm)
    r = st["realms"].get(realm)
    if keeper is None or r is None:
        return {}
    web = realmwars._web(kernel, keeper)
    out: Dict[int, Tuple[float, Optional[str]]] = {}
    for sid in r["sectors"]:
        if sid not in kernel.sectors:
            continue
        worst, by = 0.0, None
        for nb in kernel.sectors[sid].warps:
            other = spheres.presence(kernel, spheres.owner(kernel, nb))
            if other is None or other in web:
                continue
            home = spheres._home(kernel, other)
            if home is None:
                continue
            arms = _strength(home) / (1 + _hops(kernel, home.sector_id, sid))
            if arms > worst:
                worst, by = arms, other
        if by is not None:
            out[sid] = (worst, by)
    return out


def book(kernel: Any, realm: str) -> mc.Chain:
    """The border book: threat less defence at each border, signed - a deficit where the border is not held."""
    from xylarium.kernel import spheres
    from xylarium.kernel.sustenance import _strength
    keeper = spheres.presence(kernel, realm)
    home = spheres._home(kernel, keeper) if keeper else None
    out: mc.Chain = {}
    for sid, (threat, _) in threats(kernel, realm).items():
        own = _strength(home) / (1 + _hops(kernel, home.sector_id, sid)) if home is not None else 0.0
        d = mc.q(threat) - mc.q(fortification(kernel, sid) + own)
        if d:
            out[(str(sid), "border")] = d
    return out


def _fortify(kernel: Any, realm: str, sid: int, units: float, logs: List[str]) -> float:
    """The keeper builds works at a border: as far as its council judges the border worth them, and its treasury
    pays. Returns the strength built."""
    from xylarium.config import PRICE_LEVEL, SURFACE_TROOP_RECRUIT_COST
    from xylarium.kernel import decide, history, relations, spheres, stewardship, transit
    keeper = spheres.presence(kernel, realm)
    home = spheres._home(kernel, keeper) if keeper else None
    if home is None or units <= 0:
        return 0.0
    level = PRICE_LEVEL.get(home.currency, 1.0)
    price = SURFACE_TROOP_RECRUIT_COST * level
    afford = max(0.0, float(home.treasury) / price)
    units = min(units, afford)
    if units < 1:
        return 0.0
    worlds = [w for w in kernel.sectors[sid].planets if w.population > 0]
    tolls = float(sum((transit.book(r, "collected") for k, r in transit.stats(kernel)["lanes"].items()
                       if str(sid) in k.split("-")), Fraction(0)))
    m = decide.mind_of_planet(kernel, home)
    worth = decide.worth(kernel, relations._output_sol(kernel, worlds) + tolls / max(1.0, kernel.cycle_count / 25.0),
                         m)
    if decide.choose(kernel, [decide.option("fortify", units * price, worth)], m, realm, sid, "fortify") is None:
        return 0.0
    cost = int(units * price)
    home.treasury -= cost
    _pay_yards(kernel, home, cost)                                    # the works are built by the system's yards
    stats(kernel)["forts"][str(sid)] = fortification(kernel, sid) + units
    stats(kernel)["built"] += units
    history.event(kernel, "FORTIFIED", f"{stewardship.realm_name(realm)} fortifies {kernel.sectors[sid].name}",
                  actors=[keeper], sector_id=sid, cause="its steward's border book: the border was not held",
                  data={"units": round(units, 1)})
    logs.append(f"[BORDERS] {stewardship.realm_name(realm)} fortifies {kernel.sectors[sid].name} ({units:,.0f}).")
    return units


def _pay_yards(kernel: Any, planet: Any, amount: int) -> None:
    """A world's own money to the yards of its system: its port, in its money (through the exchange where the port
    keeps another) - or, with no port, to the services of SOL space."""
    port = getattr(kernel.sectors.get(planet.sector_id), "port", None)
    fx = getattr(kernel, "fx_market", None)
    if port is not None:
        got = amount if port.currency == planet.currency or fx is None else \
            fx.convert(planet.currency, port.currency, amount)[0]
        port.treasury += got
        return
    from xylarium.kernel import ledger
    sol = amount if planet.currency == _hub() or fx is None else fx.convert(planet.currency, _hub(), amount)[0]
    ledger.pay_service(sol, institution="borders")


def _reweigh_standoffs(kernel: Any, logs: List[str]) -> None:
    """A hostile border, weighed again by the one that arrived."""
    from xylarium.kernel import realmwars, spheres
    st = spheres.stats(kernel)
    for key, b in sorted(st["bonds"].items()):
        if b["kind"] != "standoff" or b.get("sector") is None:
            continue
        who, other, sid = b["a"], b["b"], b["sector"]
        if spheres.presence(kernel, spheres.owner(kernel, sid)) != other:
            continue
        if realmwars.weigh(kernel, who, other, sid)["war"]:
            st["bonds"].pop(key)
            w = realmwars.declare(kernel, spheres._realm_for(kernel, who, st["nets"][who], sid),
                                  spheres.owner(kernel, sid), who, sid)
            w["presence_a"], w["presence_b"] = who, other
            logs.append(f"[BORDERS] The standoff between the {who.split(':', 1)[-1]} and the "
                        f"{other.split(':', 1)[-1]} breaks into war.")


def season(kernel: Any) -> List[str]:
    """Once a year: each realm's steward reads its border book and rules to fortify the deepest deficit; standoffs
    are weighed again."""
    from xylarium.kernel import polity, stewardship
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    logs: List[str] = []
    for realm in stewardship.realms(kernel):
        if stewardship.steward_of(kernel, realm):
            continue                                         # a player keeps it: it fortifies by its own orders
        res = book(kernel, realm)
        lead = mc.lead(res, ("border",), deepest=True)
        if lead is not None:
            _fortify(kernel, realm, int(lead[0]), float(res[lead]), logs)
    _reweigh_standoffs(kernel, logs)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"fortified_systems": sum(1 for v in st["forts"].values() if v > 0), "built": round(st["built"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="borders",
    state=lambda: {"forts": {}, "built": 0.0},
    season=season,
    summary=summary,
))
