"""
Xylarium motive: what a captain sees as worth doing - so it can choose instead of rolling dice.

A captain's choices go through the one rule (decide.choose): every option priced in what it costs and what it is
worth, judged through the captain's own mind (its noise: a hot, noisy mind misjudges more; a fluid one less). The
only chance left in a choice is that misjudgement - never a coin deciding what a mind wants.

  a fight     Lanchester's square law: a force of strength A against D wins with odds A^2 / (A^2 + D^2), and a
              winner keeps sqrt(A^2 - D^2) of its strength. Strength is fighters plus shields at the battle's own
              exchange (combat.py: a fighter for 10 MW). Worth: the odds times the prize (half the loser's purse,
              any bounty on it, half its cargo); cost: the hull lost if it loses, the attrition if it wins (at the
              shipyard's prices), and the warrant for opening fire in protected space.
  a place     what a sector holds for this captain's calling (prey, bounties, a port's spread, claimable worlds,
              unsolved anomalies), seen across its reach and discounted by distance as strength is (1/(1+hops)^2),
              less the crew's wages to get there. Nothing worth the trip: it stays and waits (the scheduler lets
              an idle mind look again later).
  knowledge   priced by the market for it: what decoding an anomaly costs over the knowledge it yields.
"""

import math
from typing import Any, Callable, Dict, List, Optional

from xylarium.kernel import decide

FIGHTER_PRICE = 45.0            # Cr a fighter at the shipyard (engine shipyard purchase)
SHIELD_PRICE = 3.0              # Cr a MW of shield recharge
MW_PER_FIGHTER = 10.0           # combat.py: strength = fighters + shields / 10
CATALYST_COST = 1000.0          # research.py: a decoding run


# ---------------------------------------------------------------------- the mind
def mind(kernel: Any, captain: Any) -> Dict[str, float]:
    from xylarium.kernel import cache
    return cache.memo(kernel, f"motive_mind:{captain.id}", kernel.cycle_count,
                      lambda: decide.mind_of_captain(kernel, captain), max_age=25)


def pick(kernel: Any, captain: Any, options: List[Dict[str, Any]], why: str) -> Optional[Dict[str, Any]]:
    """The option this captain finds worth most over its cost (its own misjudgement included); None: nothing."""
    return decide.choose(kernel, options, mind(kernel, captain), "captain", captain.id, why)


# ---------------------------------------------------------------------- fights
def strength(ship: Any, extra_fighters: int = 0) -> float:
    return float(ship.fighters + extra_fighters) + float(ship.shields) / MW_PER_FIGHTER


def odds(a: float, d: float) -> float:
    """Lanchester's square law: the chance a force of strength a beats one of strength d."""
    if a <= 0:
        return 0.0
    return a * a / (a * a + d * d)


def hull_value(captain: Any) -> float:
    return captain.ship.fighters * FIGHTER_PRICE + captain.ship.shields * SHIELD_PRICE


def cargo_value(captain: Any) -> float:
    from xylarium.kernel import fibres
    return fibres.cargo_value(captain)


def prize(target: Any) -> float:
    return target.credits / 2.0 + max(0, int(getattr(target, "bounty", 0) or 0)) + cargo_value(target) / 2.0


def warrant(sector: Any, target: Any) -> float:
    """What opening fire costs before the law (combat.py: hostile acts in protected space draw a bounty)."""
    from xylarium.config import HOSTILE_ACT_BOUNTY
    from xylarium.kernel.models import SecurityLevel
    if sector.security != SecurityLevel.FEDERATION and sector.is_protected_space and \
            int(getattr(target, "bounty", 0) or 0) <= 0:
        return float(HOSTILE_ACT_BOUNTY)
    return 0.0


def fight(kernel: Any, captain: Any, target: Any, sector: Any, name: str = "attack",
          bonus: float = 0.0) -> Dict[str, Any]:
    """The option of attacking `target` here: worth its odds x prize (+ bonus, e.g. a bounty's reward), cost the
    expected losses and the warrant."""
    a = strength(captain.ship)
    d = strength(target.ship, sector.sentries.get(target.id, 0) if hasattr(sector, "sentries") else 0)
    p = odds(a, d)
    keep = math.sqrt(max(0.0, 1.0 - (d / a) ** 2)) if a > d > 0 else (1.0 if d <= 0 else 0.0)
    loss = (1.0 - p) * hull_value(captain) + p * (1.0 - keep) * hull_value(captain)
    return decide.option(name, loss + warrant(sector, target), p * (prize(target) + bonus), target=target.id)


# ---------------------------------------------------------------------- knowledge
def knowledge_price(kernel: Any) -> float:
    """Cr a unit of knowledge: what decoding costs over what an unsolved anomaly teaches (research.py)."""
    from xylarium.config import RESEARCH_POINTS_PER_UNIT
    rm = getattr(kernel, "research_manager", None)
    open_ = [a for a in (rm.anomalies.values() if rm else []) if a.status != "SOLVED"]
    if not open_:
        return CATALYST_COST / 15.0
    units = sum((a.reward_research + 100) / RESEARCH_POINTS_PER_UNIT for a in open_) / len(open_)
    return CATALYST_COST / max(1.0, units)


def anomaly_worth(kernel: Any, anom: Any) -> float:
    from xylarium.config import RESEARCH_POINTS_PER_UNIT
    return anom.reward_credits + (anom.reward_research + 100) / RESEARCH_POINTS_PER_UNIT * knowledge_price(kernel)


# ---------------------------------------------------------------------- places
def _captains_in(kernel: Any, sec: Any, captain: Any) -> List[Any]:
    return [kernel.captains[c] for c in sec.captains if c != captain.id and c in kernel.captains]


def prospects(kernel: Any, captain: Any, sid: int, calling: str) -> float:
    """What sector `sid` holds for a captain of this calling, in Cr."""
    from xylarium.config import COMMODITY_CONFIG
    from xylarium.kernel.models import AIPersonality, SecurityLevel
    sec = kernel.sectors[sid]
    if calling == "pirate":
        if sec.security == SecurityLevel.FEDERATION:
            return 0.0
        nets = [o["value"] - o["cost"] for o in (fight(kernel, captain, t, sec) for t in _captains_in(kernel, sec, captain)
                                                 if not t.faction_id)]
        return max([0.0] + nets)
    if calling == "mercenary":
        if sec.security == SecurityLevel.FEDERATION:
            return 0.0
        nets = [o["value"] - o["cost"] for o in
                (fight(kernel, captain, t, sec, bonus=0.0) for t in _captains_in(kernel, sec, captain)
                 if t.bounty > 0 or t.personality == AIPersonality.PIRATE)]
        return max([0.0] + nets)
    if calling == "trader":
        port = sec.port
        if port is None:
            return 0.0
        from xylarium.kernel.economy import EconomyManager
        cargo = captain.ship.cargo
        v = 0.0
        for comm in ("ORE", "ORGANICS", "EQUIPMENT"):
            base = COMMODITY_CONFIG[comm]["base_price"]
            buy_p, sell_p = EconomyManager.get_unit_prices(port, comm)
            held = getattr(cargo, comm.lower(), 0)
            if held and port.buys.get(comm, False):
                v += held * max(0.0, buy_p - base)                 # selling above what it is worth elsewhere
            if port.sells.get(comm, False) and port.stock.get(comm, 0) > 0:
                room = min(cargo.available_space, port.stock.get(comm, 0))
                v += room * max(0.0, base - sell_p)                # buying below
        return v
    if calling == "industrialist":
        v = 0.0
        for p in sec.planets:
            if p.owner_id is None and not getattr(p, "natives", None) and p.population <= 0:
                v += _claim_worth(kernel, p)
            elif p.owner_id == captain.id:
                v += p.treasury
        return v
    if calling == "explorer":
        rm = getattr(kernel, "research_manager", None)
        return sum(max(0.0, anomaly_worth(kernel, rm.anomalies[a]) - CATALYST_COST) for a in getattr(sec, "anomalies", [])
                   if rm and a in rm.anomalies and rm.anomalies[a].status != "SOLVED")
    return 0.0


def _claim_worth(kernel: Any, planet: Any) -> float:
    """A year of the taxes the world could carry, at its own physics (biosphere carrying capacity)."""
    from xylarium.config import COLONY_TAX_PER_CAPITA
    from xylarium.kernel import biosphere
    try:
        k = biosphere.carrying_capacity(kernel, planet)
    except Exception:
        return 0.0
    return float(k) * COLONY_TAX_PER_CAPITA * 25.0


def calling_of(captain: Any) -> str:
    from xylarium.kernel.models import AIPersonality
    return {AIPersonality.PIRATE: "pirate", AIPersonality.MERCENARY: "mercenary", AIPersonality.TRADER: "trader",
            AIPersonality.INDUSTRIALIST: "industrialist"}.get(captain.personality, "trader")


def destination(kernel: Any, captain: Any, sector: Any, calling: Optional[str] = None, reach: int = 3,
                score: Optional[Callable[[int], float]] = None, here: bool = False) -> Optional[int]:
    """The first jump toward the place most worth going to (or None: nowhere is worth the trip). With
    `here`, staying is weighed too (its prospects at no cost) and returns None when it wins."""
    from xylarium.kernel import topology
    calling = calling or calling_of(captain)
    dist, parent = topology.tree(kernel, sector.id, reach)
    wage = float(kernel.crew_wage(captain)) if hasattr(kernel, "crew_wage") else 1.0
    opts = []
    for sid in sorted(dist):
        h = dist[sid]
        if h == 0 and not here:
            continue
        v = score(sid) if score is not None else prospects(kernel, captain, sid, calling)
        if v <= 0:
            continue
        opts.append(decide.option(f"go:{sid}", wage * h, v / (1.0 + h) ** 2, sid=sid))
    best = pick(kernel, captain, opts, "destination")
    if best is None or best["sid"] == sector.id:
        return None
    return topology.first_hop(parent, sector.id, best["sid"])


# ---------------------------------------------------------------------- money management (its own risk profile)
def _quarter_turns() -> float:
    from xylarium.config import MAINTENANCE_INTERVAL_CYCLES, MAINTENANCE_TURNS_GRANTED
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return MAINTENANCE_TURNS_GRANTED * FISCAL_QUARTER_CYCLES / MAINTENANCE_INTERVAL_CYCLES


def running_cost(kernel: Any, captain: Any) -> float:
    """A quarter of its crew's wages (every turn it is granted, at its hull's wage)."""
    wage = float(kernel.crew_wage(captain)) if hasattr(kernel, "crew_wage") else 1.0
    return wage * _quarter_turns()


def reserve(kernel: Any, captain: Any) -> float:
    """What this captain keeps back, by its own temperament: its crew's wages for as many quarters as its caution
    says, fewer the more danger it courts (a risk-taker sails on a thinner margin). Refits are paid from what it
    keeps for them (refit_budget), not from this."""
    from xylarium.kernel.cognition import temperament
    t = temperament(captain, kernel)
    return t["caution"] * running_cost(kernel, captain) / max(0.1, t["risk"])


def surplus(kernel: Any, captain: Any) -> float:
    return max(0.0, captain.credits - reserve(kernel, captain))


def affords(kernel: Any, captain: Any, cost: float) -> bool:
    """Whether paying `cost` leaves what it keeps back."""
    return cost <= surplus(kernel, captain)


def investable(kernel: Any, captain: Any) -> float:
    """The share of its surplus it puts into stock: its thrift (capped at all of it)."""
    from xylarium.kernel.cognition import temperament
    return surplus(kernel, captain) * min(1.0, temperament(captain, kernel)["thrift"] / 2.0)


def destitute(kernel: Any, captain: Any) -> bool:
    """It cannot pay its crew for the quarter."""
    return captain.credits < running_cost(kernel, captain)


def refit_budget(kernel: Any, captain: Any) -> float:
    """What it may spend re-arming: everything but the crew's wages its caution keeps (a refit spends the refit
    money it kept)."""
    from xylarium.kernel.cognition import temperament
    return max(0.0, captain.credits - temperament(captain, kernel)["caution"] * running_cost(kernel, captain))
