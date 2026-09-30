"""
Xylarium crime: who breaks the law is a matter of pedigree, temperament and a reckoning - not a script.

  * Pedigree. Every house carries a heritable criminal streak (0..1): founding houses draw it from their
    creed (an outlaw creed runs hot), and each member inherits it with variance (a deterministic spread per
    member), so families differ and drift. Captains outside any house take theirs from their calling.
  * The reckoning. For an opportunity worth G (SOL value) in a sector whose law has presence p:
        utility = G x (1 - 2 x (p / risk) x caution)  -  G x moral_cost x (1 - streak)  -  D x caution / risk
    A bold mind (risk > 1) underestimates the chance of being caught; a cautious one (caution > 1) weighs the
    double-damages judgment more heavily; conscience costs CONSCIENCE x (alignment - DEEP_DARK) of the gain, discounted by how
    far the streak runs in the blood (never for the Light) - so the Light never profits by crime, the grey middle only with a strong
    streak where no law reaches, and only the deep Dark feels nothing. D is the downside the deed risks beyond
    the law (a pirate can lose its own hull and half its purse), weighed by temperament.
  * Disposition. Even a profitable crime is only considered as often as the streak runs - a clean pedigree
    rarely looks, a dirty one looks often.
  * Actors:
      - autonomous captains: covert siphons from rich vaults and purses, piracy against weaker lawful hulls;
      - colony governments of a dark owner: skimming the vault into the owner's purse (embezzlement);
      - dark civilizations: raiding a neighbouring world's granary in their own system.
    Every crime is filed at law where it happens (law.py) and may or may not be seen; matter and money move
    as transfers, never from nowhere.
"""

from xylarium.kernel import hulls
import random
import zlib
from typing import Any, Dict, List, Optional, Tuple

CONSIDER_CHANCE = 0.2          # an autonomous turn in which a captain even weighs its options outside the law
HONEST_STREAK = 0.2            # the streak an honest house's blood carries on average
DEEP_DARK = -0.6               # at and below this alignment, conscience is silent
# Conscience is scaled so a grey captain of honest blood, where no law reaches, at best breaks even:
#   CONSCIENCE x (0 - DEEP_DARK) x (1 - HONEST_STREAK) = 1
CONSCIENCE = 1.0 / ((0.0 - DEEP_DARK) * (1.0 - HONEST_STREAK))


def _rng(*parts: Any) -> random.Random:
    return random.Random(zlib.crc32(":".join(str(p) for p in parts).encode()))


# ---------------------------------------------------------------------- pedigree
def house_streak(house: Dict[str, Any]) -> float:
    if "criminality" not in house:
        base = 0.75 if house.get("creed") == "outlaw" else HONEST_STREAK
        house["criminality"] = round(min(1.0, max(0.0, base + _rng("house", house["id"]).gauss(0.0, 0.12))), 3)
    return house["criminality"]


def streak(kernel: Any, captain: Any) -> float:
    """This captain's criminal streak: its house's, with its own inherited variance."""
    from xylarium.kernel import lineage
    house = lineage.house_of(kernel, captain)
    if house is not None:
        base = house_streak(house)
    else:
        pers = getattr(getattr(captain, "personality", None), "value", "")
        base = {"pirate": 0.8, "mercenary": 0.35, "crusader": 0.3}.get(pers, 0.15)
    return round(min(1.0, max(0.0, base + _rng("member", captain.id).gauss(0.0, 0.08))), 3)


def moral_cost(alignment: float) -> float:
    return max(0.0, alignment - DEEP_DARK) * CONSCIENCE


def utility(gain: float, presence: float, temper: Dict[str, float], alignment: float, strk: float,
            downside: float = 0.0) -> float:
    risk, caution = max(0.2, temper.get("risk", 1.0)), temper.get("caution", 1.0)
    perceived = min(1.0, presence / risk)
    excused = (1.0 - strk) if alignment <= 0 else 1.0        # blood excuses the grey and the Dark, never the Light
    return (gain * (1.0 - 2.0 * perceived * caution) - gain * moral_cost(alignment) * excused
            - downside * caution / risk)


# ---------------------------------------------------------------------- captains
def consider(kernel: Any, captain: Any, sector: Any) -> bool:
    """An autonomous captain weighs the opportunities outside the law here. Returns True if it acted."""
    if captain.faction_id or not captain.is_ai:
        return False
    rng = _rng("consider", captain.id, kernel.cycle_count)
    if rng.random() > CONSIDER_CHANCE:
        return False
    strk = streak(kernel, captain)
    if rng.random() > strk:
        return False                        # it does not occur to them
    from xylarium.kernel import law
    from xylarium.kernel.cognition import temperament
    temper = temperament(captain, kernel)
    pres = law.presence(kernel, sector)
    best: Optional[Tuple[float, str, Dict[str, Any]]] = None
    for gain, downside, kind, act in _opportunities(kernel, captain, sector):
        u = utility(gain, pres, temper, captain.cosmic_alignment, strk, downside)
        if u > 0 and (best is None or u > best[0]):
            best = (u, kind, act)
    if best is None:
        return False
    _, kind, act = best
    stats = _stats(kernel)
    stats["attempted"][kind] = stats["attempted"].get(kind, 0) + 1
    act = dict(act)
    res = kernel.dispatch(captain.id, act.pop("action"), **act)
    data = getattr(res, "data", None) or {}
    won = data.get("defender_destroyed") if kind == "piracy" else getattr(res, "success", False)
    if won:
        stats["succeeded"][kind] = stats["succeeded"].get(kind, 0) + 1
    return True


def _power(ship: Any) -> float:
    return ship.fighters + ship.shields / 10.0


def _opportunities(kernel: Any, captain: Any, sector: Any) -> List[Tuple[float, float, str, Dict[str, Any]]]:
    """(expected gain, expected downside, kind, action) for each deed within reach."""
    from xylarium.kernel.models import ActionType
    from xylarium.kernel import fx
    from xylarium.config import SHIP_CATALOG
    out: List[Tuple[float, float, str, Dict[str, Any]]] = []
    ops = getattr(captain, "operatives", 0)
    if ops >= 3:
        for p in sector.planets:
            if p.owner_id == captain.id or p.treasury <= 0 or getattr(p, "natives", None):
                continue
            gain = p.treasury * 0.25
            if fx.ACTIVE_FX is not None and p.currency != "SOL":
                gain = fx.ACTIVE_FX.to_sol_value(p.currency, gain)
            out.append((gain, 0.0, "siphon", {"action": ActionType.COVERT_OP, "target_type": "PLANET", "target_id": p.id,
                                         "op_type": "siphon", "operatives": 3}))
    kin = set()
    from xylarium.kernel import lineage
    house = lineage.house_of(kernel, captain)
    if house is not None:
        kin = set(house.get("members", {}))
    for cid in sector.captains:
        other = kernel.captains.get(cid)
        if other is None or other.id == captain.id or other.id in kin or other.faction_id:
            continue
        if ops >= 3 and other.credits > 1000:
            out.append((other.credits * 0.17, 0.0, "siphon", {"action": ActionType.COVERT_OP, "target_type": "SHIP",
                                                         "target_id": other.id, "op_type": "siphon", "operatives": 3}))
        if (other.ship.fighters < captain.ship.fighters * 0.7 and other.bounty <= 0
                and sector.security.value != "FEDERATION"):
            mine, theirs = _power(captain.ship), _power(other.ship)
            p_win = mine / max(1e-9, mine + theirs)
            gain = p_win * (other.credits * 0.5 + (other.ship.cargo.ore + other.ship.cargo.organics) * 5)
            hull = hulls.spec(captain.ship).get("price", 0) * 0.6
            downside = (1.0 - p_win) * (hull + captain.credits * 0.5)
            out.append((gain, downside, "piracy", {"action": ActionType.ATTACK_SHIP, "target_id": other.id}))
    # A would-be thief with no crew recruits one where operatives are for hire (any starport)
    if ops < 3 and sector.port is not None and captain.credits > 5000:
        out.append((captain.credits * 0.02, 0.0, "recruit", {"action": ActionType.RECRUIT_OPERATIVES, "amount": 3}))
    return out


# ---------------------------------------------------------------------- colonies and civilizations
def quarter(kernel: Any) -> List[str]:
    """Governments of dark owners skim; dark civilizations raid their neighbours' granaries."""
    logs: List[str] = []
    from xylarium.kernel import law, fx
    from xylarium.kernel.cognition import temperament
    st = _stats(kernel)
    for sec in kernel.sectors.values():
        pres = law.presence(kernel, sec)
        for p in sec.planets:
            owner = kernel.captains.get(p.owner_id) if p.owner_id else None
            # 1. Skimming: a dark owner's council diverts part of the vault to the owner's purse
            if owner is not None and owner.is_ai and not owner.faction_id and p.treasury > 0:
                strk = streak(kernel, owner)
                rng = _rng("skim", p.id, kernel.cycle_count)
                if rng.random() < strk:
                    share = 0.05 * strk
                    local = int(p.treasury * share)
                    gain = fx.ACTIVE_FX.to_sol_value(p.currency, local) if (fx.ACTIVE_FX and p.currency != "SOL") else local
                    if local > 0 and utility(gain, pres, temperament(owner, kernel), owner.cosmic_alignment, strk) > 0:
                        p.treasury -= local
                        sol = fx.ACTIVE_FX.swap_to_sol(p.currency, local) if (fx.ACTIVE_FX and p.currency != "SOL") else local
                        owner.credits += sol
                        st["skimmed_sol"] += sol
                        law.file(kernel, "embezzlement", owner, sec, sol, {"kind": "planet", "id": p.id})
            # 2. Raids: a dark civilization takes a neighbouring world's grain in its own system
            civ = getattr(p, "civilization", None)
            if civ is not None and p.owner_id is None and p.population > 0 and (civ.alignment or 0.0) < -0.3:
                rng = _rng("raid", p.id, kernel.cycle_count)
                if rng.random() < min(1.0, -civ.alignment):
                    victims = [w for w in sec.planets if w is not p and w.population > 0 and w.organics_silo > 100]
                    if victims:
                        v = max(victims, key=lambda w: w.organics_silo)
                        take = v.organics_silo // 10
                        v.organics_silo -= take
                        p.organics_silo += take                  # a transfer: the grain changes hands
                        v.morale = max(10, v.morale - 5)
                        st["raids"] += 1
                        logs.append(f"[RAID] The {civ.name} of {p.name} raided {v.name}'s granaries ({take} organics).")
    return logs


def _stats(kernel: Any) -> Dict[str, Any]:
    s = getattr(kernel, "crime_stats", None)
    if s is None:
        s = kernel.crime_stats = {"attempted": {}, "succeeded": {}, "skimmed_sol": 0, "raids": 0}
    return s
