"""
Xylarium turn: an autonomous captain's turn is one weighed choice, never a first-match script.

Each turn a captain gathers every exclusive action open to it as an OPTION - what it is worth and what it costs, in
its money of account through the exchange's pool (comms.sol), running costs included - and its own mind weighs them
all at once (decide.choose: no thresholds, no scripted priorities):

  GATES        what is not a choice stays a gate: a warship under its faction's orders; a crew short of rations
               (a hungry hold cannot spend its turn on anything else - cognition's ration deeds).
  SIDE WORK    what does not spend the ship's turn happens alongside: refits and repayments at a refit port, the
               house's research and financier's desk, a firm's governance, signing on a charter, idle investment.
  OPTIONS      retreat when crippled, the clone vats when its house is endangered, a charter flown home, the best
               opportunity outside the law, anomalies and the frontier, an outlaw's raid or hunt, dealings with
               natives, and its calling's own work (a trader's contracts, sales, purchases and trips; a pirate's
               prey and colonies; an industrialist's levies and claims; a mercenary's bounties) - each priced.
  REFUSED      a deed the world refuses (a contract with nothing to load, a sale the port cannot pay) does not spend
               the turn: it is struck off and the rest weighed again.
  NOTHING      if nothing is worth its cost, the mind turns over its books (cognition: the deeds no price is put on
               yet weigh nothing, and run only when nothing priced does).
"""

from typing import Any, Dict, List
from xylarium.kernel.fx import hub as _hub

RATION_DEEDS = ("LIQUIDATE_CARGO_FOR_RATIONS", "PURCHASE_RATIONS", "FORAGE_DEEP_VOID", "SEEK_RATION_PORT")
GOODS = ("ORE", "ORGANICS", "EQUIPMENT")
NEWS_RADIUS = 8                  # how far a trader looks when nothing within three warps is worth it (its news)


def _opt(name: str, cost: float, value: float, act: Any, **data: Any) -> Dict[str, Any]:
    from xylarium.kernel import decide
    return decide.option(name, float(cost), float(value), act=act, **data)


def _wage(kernel: Any, captain: Any) -> float:
    return float(kernel.crew_wage(captain)) if hasattr(kernel, "crew_wage") else 1.0


def _in_hub(kernel: Any, cur: str, amount: float) -> float:
    """An amount of a money in the exchange's unit, through the pool."""
    from xylarium.kernel import institutions
    hub = institutions.hub_unit(kernel)
    if cur == hub or amount <= 0:
        return float(amount)
    fx = getattr(kernel, "fx_market", None)
    try:
        return float(fx.quote_via_sol(cur, hub, int(amount))) if fx is not None and fx.can_convert(cur, hub) else 0.0
    except Exception:
        return 0.0


# ---------------------------------------------------------------------- side work (not the ship's turn)
def side_work(kernel: Any, captain: Any, sector: Any) -> None:
    from xylarium.kernel import tourism
    from xylarium.kernel.ai import AIManager
    from xylarium.kernel.models import AIPersonality
    _refit_in_port(kernel, captain, sector)
    if captain.personality == AIPersonality.INDUSTRIALIST:
        AIManager._execute_corporate_industrialist_loop(kernel, captain)
    if not getattr(captain, "active_research", None):
        AIManager._select_ai_research(kernel, captain)
    AIManager._financier_arbitrage(kernel, captain)
    if not captain.charter and not captain.faction_id:
        tourism.accept(kernel, captain, sector)
    _invest(kernel, captain)
    _cover_shorts(kernel, captain)
    _tend_colony(kernel, captain, sector)


def _refit_in_port(kernel: Any, captain: Any, sector: Any) -> None:
    """At a refit port: relief when it cannot pay its crew, fighters and shields within what it does not keep for
    wages, repayment from its surplus, rest when spent (as the old maintenance refit did)."""
    from xylarium.config import REST_COST_CREDITS
    from xylarium.kernel import hulls, motive
    from xylarium.kernel.cognition import temperament
    from xylarium.kernel.models import ActionType, SecurityLevel
    refit_here = sector.id == 1 or (sector.security == SecurityLevel.ANARCHY and sector.port is not None)
    if not refit_here:
        return
    if sector.id == 1 and motive.destitute(kernel, captain):
        kernel.dispatch(captain.id, ActionType.BANK_TRANSACTION, sub_action="loan")
    keep_wages = temperament(captain, kernel)["caution"] * motive.running_cost(kernel, captain)
    disposable = max(0, int(captain.credits - keep_wages))
    max_fighters = hulls.spec(captain.ship).get("max_fighters", 20)
    if captain.ship.fighters < max_fighters and disposable >= 60:
        budget = disposable // 2 if captain.ship.shields < captain.ship.max_shields else disposable
        kernel.dispatch(captain.id, ActionType.SHIPYARD_PURCHASE, item="fighters",
                        amount=min(max_fighters - captain.ship.fighters, max(1, budget // 60)))
        disposable = max(0, int(captain.credits - keep_wages))
    if captain.ship.shields < captain.ship.max_shields and disposable >= 30:
        kernel.dispatch(captain.id, ActionType.SHIPYARD_PURCHASE, item="shields", budget=disposable)
    repay = int(min(captain.debt, motive.surplus(kernel, captain)))
    if sector.id == 1 and captain.debt > 0 and repay > 0:
        kernel.dispatch(captain.id, ActionType.BANK_TRANSACTION, sub_action="repay", amount=repay)
    if sector.id == 1 and captain.turns_left < 50 and motive.affords(kernel, captain, REST_COST_CREDITS):
        kernel.dispatch(captain.id, ActionType.REST)


def _invest(kernel: Any, captain: Any) -> None:
    """Idle money a trader does not need goes into the exchange's best-paying shares (as before)."""
    from xylarium.kernel import motive
    from xylarium.kernel.models import ActionType, AIPersonality
    if captain.personality != AIPersonality.TRADER:
        return
    budget = motive.investable(kernel, captain)
    if budget <= 0:
        return
    best = max(kernel.market_manager.companies.values(),
               key=lambda c: c.dividend_rate if c.available_shares >= 25 else -1, default=None)
    if best and best.available_shares >= 25 and best.share_price * 25 <= budget:
        kernel.dispatch(captain.id, ActionType.STOCK_BUY, ticker=best.ticker, amount=25)


def _cover_shorts(kernel: Any, captain: Any) -> None:
    from xylarium.kernel.models import ActionType
    for ticker, pos in list(getattr(captain, "short_positions", {}).items()):
        comp = kernel.market_manager.companies.get(ticker)
        if comp and comp.share_price < pos.get("entry_price", comp.share_price):
            kernel.dispatch(captain.id, ActionType.STOCK_COVER, ticker=ticker)
            break


def _tend_colony(kernel: Any, captain: Any, sector: Any) -> None:
    """An industrialist at a colony of its own fortifies it as its treasury allows (as before)."""
    from xylarium.config import CITADEL_CONFIG
    from xylarium.kernel import motive
    from xylarium.kernel.colony import ColonyManager
    from xylarium.kernel.models import AIPersonality
    if captain.personality != AIPersonality.INDUSTRIALIST:
        return
    for planet in sector.planets:
        if planet.owner_id != captain.id:
            continue
        if planet.treasury >= 5000 and planet.security_operatives < 5 and motive.affords(kernel, captain, 1000):
            planet.security_operatives += 2
            captain.credits -= 1000
        elif planet.citadel_level < 3 and motive.affords(
                kernel, captain, CITADEL_CONFIG.get(planet.citadel_level + 1, {}).get("upgrade_cost", 10 ** 9)):
            ColonyManager.upgrade_citadel(captain, planet)
        return


# ---------------------------------------------------------------------- options (the ship's turn)
def options(kernel: Any, captain: Any, sector: Any, endangered: bool) -> List[Dict[str, Any]]:
    from xylarium.kernel import crime
    from xylarium.kernel.models import AIPersonality
    out: List[Dict[str, Any]] = []
    out += _retreat(kernel, captain, sector)
    if endangered:
        out += _clones(kernel, captain, sector)
    out += _charter(kernel, captain, sector)
    if not endangered:
        c = crime.offer(kernel, captain, sector)
        if c is not None:
            out.append(c)
        out += _anomalies(kernel, captain, sector)
        out += _outlaw(kernel, captain, sector)
    out += _natives(kernel, captain, sector)
    p = captain.personality
    if p == AIPersonality.TRADER:
        out += _trader(kernel, captain, sector)
    elif p == AIPersonality.PIRATE and not endangered:
        out += _pirate(kernel, captain, sector)
    elif p == AIPersonality.INDUSTRIALIST:
        out += _industrialist(kernel, captain, sector)
    elif p == AIPersonality.MERCENARY:
        out += _mercenary(kernel, captain, sector)
    return out


def _warp(kernel: Any, captain: Any, dest: int) -> Any:
    from xylarium.kernel.ai import AIManager
    return lambda: AIManager._warp_captain(kernel, captain, dest)


def _retreat(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    """Crippled away from a refit port: home to refit - worth what the road would otherwise take of hull and hold."""
    from xylarium.config import AI_CRITICAL_FIGHTERS, AI_CRITICAL_SHIELDS
    from xylarium.kernel import fxroutes, motive
    from xylarium.kernel.models import SecurityLevel
    refit_here = sector.id == 1 or (sector.security == SecurityLevel.ANARCHY and sector.port is not None)
    crippled = captain.ship.shields < AI_CRITICAL_SHIELDS and captain.ship.fighters < AI_CRITICAL_FIGHTERS
    if not crippled or refit_here:
        return []
    path = kernel.find_path(captain.sector_id, 1) or []
    if len(path) < 2:
        return []
    risk = fxroutes.HAZARD.get(getattr(sector.security, "value", "FEDERATION"), 0.0)
    at_stake = motive.hull_value(captain) + motive.cargo_value(captain)
    return [_opt("retreat", _wage(kernel, captain), at_stake * max(risk, 1.0 / len(path)), _warp(kernel, captain, path[1]))]


def _clones(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    """An endangered house sails for the vats when it can afford a backup: worth what a lost captain would take
    with it."""
    from xylarium.config import LINEAGE_CLONE_PRICE
    from xylarium.kernel import motive
    from xylarium.kernel.models import ActionType
    if captain.credits < LINEAGE_CLONE_PRICE * 1.5 or sector.id == 1:
        return []
    path = kernel.find_path(sector.id, 1) or []
    if len(path) < 2:
        return []
    hops = len(path) - 1
    return [_opt("clones", _wage(kernel, captain) * hops + LINEAGE_CLONE_PRICE,
                 motive.hull_value(captain) + captain.credits,
                 lambda: kernel.dispatch(captain.id, ActionType.MOVE, destination=path[1]))]


def _charter(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    from xylarium.kernel import tourism
    from xylarium.kernel.models import ActionType
    if not captain.charter:
        return []
    c = tourism.charters(kernel).get(captain.charter)
    if c is None or c["status"] != "IN_TRANSIT":
        return []
    path = kernel.find_path(sector.id, c["dest_sector"]) or []
    if len(path) < 2:
        return []
    pay = _in_hub(kernel, c.get("currency", _hub()), float(c.get("escrow", 0)))
    return [_opt("charter", _wage(kernel, captain) * (len(path) - 1), pay,
                 lambda: kernel.dispatch(captain.id, ActionType.MOVE, destination=path[1]))]


def _fight_options(kernel: Any, captain: Any, sector: Any, targets: List[str], why: str) -> List[Dict[str, Any]]:
    from xylarium.kernel import motive
    from xylarium.kernel.combat import CombatManager
    out = []
    for t in targets:
        o = motive.fight(kernel, captain, kernel.captains[t], sector)
        target = kernel.captains[t]

        def act(target=target):
            CombatManager.resolve_ship_battle(captain, target, sector, kernel=kernel)
            if getattr(kernel, "event_bus", None):
                kernel.event_bus.broadcast_radio(sender="RADAR-ALERT", channel="COMBAT", sector_id=sector.id,
                                                 text=f"COMBAT: {captain.name} engaged {target.name} in Sector "
                                                      f"{sector.id}!")
        out.append(dict(o, name=f"{why}:{t}", act=act))
    return out


def _anomalies(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    """An unsolved anomaly here to decode (or, for a pirate, the captains digging at it to ambush), and the frontier
    a folding people can jump to."""
    from xylarium.kernel import motive
    from xylarium.kernel.models import ActionType, AIPersonality, SecurityLevel
    out: List[Dict[str, Any]] = []
    rm = getattr(kernel, "research_manager", None)
    if rm is None:
        return out
    unsolved = [rm.anomalies[a] for a in getattr(sector, "anomalies", [])
                if a in rm.anomalies and rm.anomalies[a].status != "SOLVED"]
    if unsolved:
        anom = unsolved[0]
        if captain.personality == AIPersonality.PIRATE and sector.security != SecurityLevel.FEDERATION:
            others = [c for c in sector.captains if c != captain.id and c in kernel.captains]
            out += _fight_options(kernel, captain, sector, others, "ambush")
        if motive.affords(kernel, captain, motive.CATALYST_COST):
            out.append(_opt("decode", motive.CATALYST_COST, motive.anomaly_worth(kernel, anom),
                            lambda: kernel.dispatch(captain.id, ActionType.ANOMALY_INVESTIGATE, anomaly_id=anom.id,
                                                    solve_inputs={"mode": "catalyst"})))
    from xylarium.kernel.research import jump_cost
    fold = jump_cost(kernel, captain)
    if motive.affords(kernel, captain, fold + motive.CATALYST_COST):
        for a in rm.anomalies.values():
            if a.status != "SOLVED" and a.sector_id != captain.sector_id:
                out.append(_opt(f"frontier:{a.id}", fold + motive.CATALYST_COST, motive.anomaly_worth(kernel, a),
                                lambda a=a: kernel.dispatch(captain.id, ActionType.JUMP_WARP, destination=a.sector_id)))
    return out


def _outlaw(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    """An outlaw creed past its line raids: tribute under a port's guns, a fight in null space, or the hunt toward the
    nearest null sector with traffic - each worth its take."""
    from xylarium.config import OUTLAW_CREED_LINE, OUTLAW_SHAKEDOWN_SHARE
    from xylarium.kernel import alignment, lineage, motive, topology
    from xylarium.kernel.models import ActionType, AIPersonality, SecurityLevel
    house = lineage.house_of(kernel, captain)
    outlaw = captain.personality == AIPersonality.PIRATE or (house is not None and house.get("creed") == "outlaw")
    if not outlaw or captain.cosmic_alignment <= OUTLAW_CREED_LINE or sector.security == SecurityLevel.FEDERATION:
        return []
    kin = set((house or {}).get("members", {}))
    prey = [kernel.captains[c] for c in sector.captains if c != captain.id and c in kernel.captains and c not in kin]
    prey = [p for p in prey if not p.faction_id and p.ship.fighters < captain.ship.fighters * 0.8 and p.credits > 300]
    out: List[Dict[str, Any]] = []
    for target in prey:
        if sector.is_protected_space:
            tribute = int(target.credits * OUTLAW_SHAKEDOWN_SHARE)

            def shake(target=target, tribute=tribute):
                target.credits -= tribute
                captain.credits += tribute
                alignment.act(kernel, captain, "tribute_extorted", harmed_sol=tribute)
                if getattr(kernel, "event_bus", None):
                    kernel.event_bus.broadcast_radio(sender=captain.name, channel="ALERT", sector_id=sector.id,
                                                     text=f"SHAKEDOWN: {target.name} pays {tribute:,} Cr to sail on.")
            out.append(_opt(f"shakedown:{target.id}", 0.0, tribute, shake))
        else:
            o = motive.fight(kernel, captain, target, sector)
            out.append(dict(o, name=f"raid:{target.id}",
                            act=lambda t=target: kernel.dispatch(captain.id, ActionType.ATTACK_SHIP, target_id=t.id)))
    dist, parent = topology.tree(kernel, sector.id, 3)
    wage = _wage(kernel, captain)
    for w, h in dist.items():
        ws = kernel.sectors[w]
        if w == sector.id or not ws.is_null_space:
            continue
        there = [kernel.captains[c] for c in ws.captains if c not in kin and c != captain.id and c in kernel.captains
                 and not kernel.captains[c].faction_id]
        if there:
            take = max(motive.prize(t) for t in there)
            out.append(_opt(f"hunt:{w}", wage * h, take / (1.0 + h),
                            lambda w=w: kernel.dispatch(captain.id, ActionType.MOVE,
                                                        destination=topology.first_hop(parent, sector.id, w))))
    return out


def _natives(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    """Dealings with a native people here, each worth what natives.py yields it (AIManager._native_option)."""
    from xylarium.kernel.ai import AIManager
    from xylarium.kernel.models import ActionType
    from xylarium.kernel.natives import NativeManager
    worlds = [p for p in sector.planets if p.natives]
    if not worlds or captain.faction_id:
        return []
    planet = worlds[0]
    n = planet.natives
    value = captain.cosmic_alignment
    choices: List[str] = []
    if value <= -0.3:
        lawful, hand, _ = NativeManager.legality(kernel, captain, sector, n, "exploit")
        if (lawful or hand.get("enforcement") in ("NONE", "WARRANT")) and captain.ship.cargo.available_space > 20:
            choices.append("exploit")
    else:
        for sub in ("contact", "trade", "protect"):
            lawful, _, _ = NativeManager.legality(kernel, captain, sector, n, sub)
            if not lawful:
                continue
            if sub == "contact" and captain.id not in n["contacted_by"]:
                choices.append(sub)
            elif sub == "trade" and captain.id in n["contacted_by"]:
                choices.append(sub)
            elif sub == "protect" and captain.id in n["contacted_by"] and not n.get("protector") and value >= 0.3:
                choices.append(sub)
        if n.get("protector") == captain.id and n.get("tribute"):
            choices.append("collect")
        if not choices:
            choices.append("observe")
    out = []
    for sub in choices:
        o = AIManager._native_option(kernel, captain, planet, sub)
        out.append(dict(o, name=f"natives:{sub}",
                        act=lambda sub=sub: kernel.dispatch(captain.id, ActionType.NATIVE_INTERACT, sub_action=sub,
                                                            planet_id=planet.id)))
    return out


def _trip(kernel: Any, captain: Any, sector: Any, calling: str) -> List[Dict[str, Any]]:
    """The trip its calling most wants (motive.destination_option): within three warps, else as far as its news."""
    from xylarium.kernel import motive
    got = motive.destination_option(kernel, captain, sector, calling, wider=NEWS_RADIUS)
    if got is None:
        return []

    def go(got=got):
        if calling == "trader":
            motive._plan_trip(kernel, captain, got)
        from xylarium.kernel.ai import AIManager
        AIManager._warp_captain(kernel, captain, got["hop"])
    return [_opt(f"trip:{got['sid']}", got["cost"], got["value"], go)]


def _trader(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    """A trader's work, every leg in the exchange's unit through the pool: deliver what it carries under contract,
    take a contract, sell here what fetches more here than anywhere it has heard of within reach (less the wages to
    get there), buy here what sells dearer within reach than it costs here, or make the trip."""
    from xylarium.kernel import comms, motive
    from xylarium.kernel.economy import EconomyManager
    from xylarium.kernel.models import ActionType
    out: List[Dict[str, Any]] = []
    wage = _wage(kernel, captain)
    mm = kernel.market_manager
    active = list(getattr(captain, "active_contracts", []))
    for cid in active:
        c = mm.contracts.get(cid)
        if c is None:
            continue
        pay = _in_hub(kernel, c.currency, c.payout_credits)
        if c.destination_sector == sector.id:
            out.append(_opt(f"deliver:{cid}", 0.0, pay,
                            lambda cid=cid: kernel.dispatch(captain.id, ActionType.FREIGHT_DELIVER, contract_id=cid)))
            continue
        path = kernel.find_path(captain.sector_id, c.destination_sector) or []
        if len(path) > 1:                                        # the haul under contract, a jump nearer
            h = len(path) - 1
            out.append(_opt(f"haul:{cid}", wage * h, pay / (1.0 + h), _warp(kernel, captain, path[1])))
    if len(active) < 2 and captain.ship.cargo.available_space >= 10:
        for c in mm.contracts.values():
            if c.status == "OPEN" and c.origin_sector == sector.id and captain.ship.cargo.available_space >= c.amount:
                hops = max(1, len(kernel.find_path(sector.id, c.destination_sector) or []) - 1)
                out.append(_opt(f"accept:{c.id}", wage * hops, _in_hub(kernel, c.currency, c.payout_credits),
                                lambda cid=c.id: kernel.dispatch(captain.id, ActionType.FREIGHT_ACCEPT,
                                                                 contract_id=cid)))
    port = sector.port
    if port is not None:
        for comm in GOODS:
            held = motive.free_cargo(kernel, captain, comm)
            bid, ask = EconomyManager.get_unit_prices(port, comm)
            if held > 0 and port.buys.get(comm, False) and bid > 0:
                here = comms.sol(kernel, sector.id, bid, held)        # the lot here, against the lot carried on
                out.append(_opt(f"sell:{comm}", max(0.0, motive.carried_on(kernel, captain, sector.id, comm, held, NEWS_RADIUS)),
                                here * held,
                                lambda comm=comm, held=held: EconomyManager.execute_sell(captain, port, comm, held)))
            if captain.ship.cargo.available_space > 0 and port.sells.get(comm, False) and ask > 0 \
                    and port.stock.get(comm, 0) > 0:
                cost_each = comms.sol(kernel, sector.id, ask)
                q = int(min(captain.ship.cargo.available_space, port.stock.get(comm, 0),
                            motive.surplus(kernel, captain) // max(1e-9, cost_each)))
                worth = motive.carried_on(kernel, captain, sector.id, comm, q, NEWS_RADIUS)
                if q > 0 and worth > 0:
                    out.append(_opt(f"buy:{comm}", q * cost_each, worth,
                                    lambda comm=comm, q=q: EconomyManager.execute_buy(captain, port, comm, q)))
    out += _trip(kernel, captain, sector, "trader")
    return out


def _pirate(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    from xylarium.kernel import motive
    from xylarium.kernel.combat import CombatManager
    from xylarium.kernel.models import ActionType, SecurityLevel
    out: List[Dict[str, Any]] = []
    if sector.security != SecurityLevel.FEDERATION:
        prey = [c for c in sector.captains if c != captain.id and c in kernel.captains
                and sector.sentries.get(c, 0) < captain.ship.fighters]
        out += _fight_options(kernel, captain, sector, prey, "prey")
        for planet in sector.planets:
            if planet.owner_id and planet.owner_id != captain.id:
                def bombard(planet=planet):
                    for comp in kernel.market_manager.companies.values():     # short the colony's firm first
                        if comp.planet_id == planet.id or (comp.sector_id == sector.id
                                                           and comp.planet_name == planet.name):
                            if comp.ticker not in getattr(captain, "short_positions", {}) and \
                                    motive.affords(kernel, captain, comp.share_price * 40):
                                kernel.dispatch(captain.id, ActionType.STOCK_SHORT, ticker=comp.ticker, amount=40)
                                break
                    CombatManager.attack_planet(captain, planet, sector, kernel=kernel)
                    if getattr(kernel, "event_bus", None):
                        kernel.event_bus.broadcast_radio(sender="COLONY-ALERT", channel="ALERT", sector_id=sector.id,
                                                         text=f"ALERT: {captain.name} initiated orbital bombardment "
                                                              f"on {planet.name}!")
                out.append(_opt(f"bombard:{planet.id}", _wage(kernel, captain),
                                _in_hub(kernel, planet.currency, planet.treasury), bombard))
    out += _hunt_target(kernel, captain)
    out += _trip(kernel, captain, sector, "pirate")
    return out


def _hunt_target(kernel: Any, captain: Any) -> List[Dict[str, Any]]:
    """A designated hunt (a contract or a grudge): the trip toward it, worth what its quarry there would yield (motive.prize)
    a jump nearer - a stale hunt whose quarry has gone weighs nothing."""
    t = getattr(captain, "hunt_target_sector", None)
    if t is None:
        return []
    if captain.sector_id == t:
        return []                        # it is there: the quarry is weighed as prey; a quarry gone weighs nothing
    path = kernel.find_path(captain.sector_id, t) or []
    if len(path) < 2:
        return []
    from xylarium.kernel import motive
    quarry = [kernel.captains[c] for c in kernel.sectors[t].captains if c != captain.id and c in kernel.captains]
    h = len(path) - 1
    worth = max((motive.prize(q) for q in quarry), default=0.0) / (1.0 + h)   # what it would take there
    return [_opt(f"hunt_target:{t}", _wage(kernel, captain) * h, worth, _warp(kernel, captain, path[1]))]


def _industrialist(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    from xylarium.kernel import motive
    from xylarium.kernel.colony import ColonyManager
    from xylarium.kernel.models import ActionType
    out: List[Dict[str, Any]] = []
    wage = _wage(kernel, captain)
    owned = [(s.id, p) for s in kernel.sectors.values() for p in s.planets
             if p.owner_id == captain.id and p.treasury >= 500]
    for sid, p in owned:
        levy = _in_hub(kernel, p.currency, p.treasury * 0.2)
        if sid == sector.id:
            out.append(_opt(f"levy:{p.id}", 0.0, levy,
                            lambda p=p: kernel.dispatch(captain.id, ActionType.PLANET_TAX, planet_id=p.id)))
        else:
            path = kernel.find_path(captain.sector_id, sid) or []
            if len(path) > 1:
                h = len(path) - 1
                out.append(_opt(f"to_levy:{p.id}", wage * h, levy / (1.0 + h), _warp(kernel, captain, path[1])))
    for planet in sector.planets:
        if planet.owner_id is None:
            def claim(planet=planet):
                ColonyManager.claim_planet(captain, planet, sector)
                if getattr(kernel, "event_bus", None):
                    kernel.event_bus.broadcast_radio(sender=captain.name, channel="CORP", sector_id=sector.id,
                                                     text=f"{planet.name} in Sector {sector.id} is claimed by "
                                                          f"{captain.name}.")
            out.append(_opt(f"claim:{planet.id}", wage, motive._claim_worth(kernel, planet), claim))
    out += _trip(kernel, captain, sector, "industrialist")
    return out


def _mercenary(kernel: Any, captain: Any, sector: Any) -> List[Dict[str, Any]]:
    from xylarium.kernel.models import AIPersonality, SecurityLevel
    out: List[Dict[str, Any]] = []
    if sector.security != SecurityLevel.FEDERATION:
        wanted = [c for c in sector.captains if c != captain.id and c in kernel.captains
                  and (kernel.captains[c].bounty > 0 or kernel.captains[c].personality == AIPersonality.PIRATE)]
        out += _fight_options(kernel, captain, sector, wanted, "bounty")
    out += _hunt_target(kernel, captain)
    out += _trip(kernel, captain, sector, "mercenary")
    return out


# ---------------------------------------------------------------------- the turn
def run(kernel: Any, captain: Any) -> None:
    from xylarium.kernel import lineage, motive
    from xylarium.kernel.ai import AIManager
    from xylarium.kernel.cognition import CognitiveOrgan, SeatSurvive
    sector = kernel.sectors[captain.sector_id]
    if captain.faction_id and getattr(kernel, "factions", None) is not None:
        if kernel.factions.execute_faction_ai(kernel, captain):
            return                                                   # a warship under orders
    deed = SeatSurvive.reduce_survival(captain, SeatSurvive.peel_books(captain, kernel), kernel)
    if deed is not None and getattr(deed, "deed_name", None) in RATION_DEEDS:
        CognitiveOrgan.think(captain, kernel)                        # a hungry hold eats first
        AIManager._maybe_chatter(kernel, captain, sector)
        return
    side_work(kernel, captain, sector)
    sector = kernel.sectors[captain.sector_id]
    endangered = lineage.house_endangered(kernel, captain)
    opts = options(kernel, captain, sector, endangered)
    acted = False
    while opts and not acted:
        best = motive.pick(kernel, captain, opts, "turn")
        if best is None or not best.get("act"):
            break
        res = best["act"]()
        acted = getattr(res, "success", True) is not False        # a refused deed does not spend the turn:
        if not acted:                                              # it is struck off and the rest weighed again
            opts = [o for o in opts if o is not best]
    if not acted:
        CognitiveOrgan.think(captain, kernel)                        # nothing priced is worth it: it reasons
    AIManager.check_cognitive_cleaving(kernel, captain)
    AIManager._maybe_chatter(kernel, captain, kernel.sectors[captain.sector_id])
