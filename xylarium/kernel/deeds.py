"""
Xylarium deeds: what an action means once it is done (docs/STANDARDS.md, S6).

Some commands carry moral weight or make history: piracy darkens a captain and is filed at law, a conquest is
written into a world's annals, a licensed dig is honest work. Each such command registers a `before` hook (the
facts needed to judge it, read before it happens) and an `after` hook (its deeds, filings and chronicle entries).
The dispatcher calls them around every successful action; commands without hooks carry no moral weight. Every deed
is then checked against the great powers' heresies.
"""

import random
from typing import Any, Callable, Dict

from xylarium.kernel import alignment as alignment_mod
from xylarium.kernel import chronicle as chronicle_mod
from xylarium.kernel import law as law_mod
from xylarium.kernel import lineage as lineage_mod
from xylarium.kernel.models import ActionResult, ActionType

BEFORE: Dict[ActionType, Callable[..., Dict[str, Any]]] = {}
AFTER: Dict[ActionType, Callable[..., None]] = {}


def before(*kinds: ActionType):
    def deco(fn):
        for k in kinds:
            BEFORE[k] = fn
        return fn
    return deco


def after(*kinds: ActionType):
    def deco(fn):
        for k in kinds:
            AFTER[k] = fn
        return fn
    return deco


def prestate(kernel: Any, captain: Any, sector: Any, action: ActionType, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Facts needed to judge a deed after it happens (the target's standing, a planet's owner, an artifact)."""
    pre: Dict[str, Any] = {}
    hook = BEFORE.get(action)
    if hook is not None:
        hook(kernel, captain, sector, kwargs, pre)
    pre["hull"] = captain.ship.ship_type
    pre["sector_id"] = captain.sector_id
    pre["credits"] = captain.credits
    return pre


def consequences(kernel: Any, captain: Any, sector: Any, action: ActionType, kwargs: Dict[str, Any],
                 result: ActionResult, pre: Dict[str, Any]) -> None:
    hook = AFTER.get(action)
    if hook is not None:
        hook(kernel, captain, sector, action, kwargs, result, pre)
    heresy = kernel.factions.heresy_check(kernel, captain, action, kwargs, result)
    if heresy:
        result.logs = (result.logs or []) + [heresy]
        result.message += " " + heresy


deed = alignment_mod.deed


# ---------------------------------------------------------------------- before
@before(ActionType.ATTACK_SHIP, ActionType.TACTICAL_COMBAT)
def _before_attack(kernel, captain, sector, kwargs, pre):
    target = kernel.captains.get(kwargs.get("target_id"))
    if target is not None:
        from xylarium.kernel import hulls
        pre["target"] = target
        pre["target_hull_value"] = hulls.spec(target.ship).get("price", 0)
        pre["target_wanted"] = target.bounty > 0 or getattr(target.personality, "value", "") in ("pirate", "crusader")
        pre["target_hull"] = target.ship.ship_type
        pre["target_sector"] = target.sector_id
        pre["target_credits"] = target.credits
        pre["target_bounty"] = target.bounty


@before(ActionType.ATTACK_PLANET)
def _before_bombard(kernel, captain, sector, kwargs, pre):
    planet = kernel._find_planet(sector, kwargs.get("planet_id"))
    if planet is not None:
        pre["planet"] = planet
        pre["owner"] = planet.owner_id
        pre["population"] = planet.population
        pre["treasury_sol"] = kernel.fx_market.to_sol_value(planet.currency, planet.treasury) \
            if planet.currency != "SOL" else planet.treasury


@before(ActionType.SELL_ARTIFACT)
def _before_sale(kernel, captain, sector, kwargs, pre):
    art = next((a for a in captain.artifacts if a.get("id") == kwargs.get("artifact_id")), None)
    pre["provenance"] = art.get("provenance") if art else None


@before(ActionType.SCAN_SPACE)
def _before_scan(kernel, captain, sector, kwargs, pre):
    pre["belts_known"] = len(captain.scanned_belts)


# ---------------------------------------------------------------------- after
@after(ActionType.MOVE)
def _jumped(kernel, captain, sector, action, kwargs, result, pre):
    chronicle_mod.note_jump(kernel, captain)
    from xylarium.kernel import waystations
    waystations.arrive(kernel, captain.sector_id)          # traffic is what calls docks into being


@after(ActionType.TRADE)
def _traded(kernel, captain, sector, action, kwargs, result, pre):
    alignment_mod.earned(kernel, captain, "fair_trade", pre.get("credits"))


@after(ActionType.FREIGHT_DELIVER)
def _delivered(kernel, captain, sector, action, kwargs, result, pre):
    kind = "extraction_delivered" if "EXTRACTION" in (result.message or "").upper() else "freight_delivered"
    alignment_mod.earned(kernel, captain, kind, pre.get("credits"))
    chronicle_mod.note_freight(kernel, captain)


@before(ActionType.IDEOLOGY_AID_DISPATCH)
def _before_aid(kernel, captain, sector, kwargs, pre):
    planet = kernel.get_planet(kwargs.get("planet_id")) if kwargs.get("planet_id") else None
    if planet is not None:
        pre["starving"] = bool(planet.society.get("short_q")) or planet.society.get("sustenance") in (
            "expanding", "pressed", "stranded")


@after(ActionType.IDEOLOGY_AID_DISPATCH)
def _aid(kernel, captain, sector, action, kwargs, result, pre):
    if not result.success:
        return
    from xylarium.config import COMMODITY_CONFIG
    units = int(kwargs.get("food_units", 20))
    alignment_mod.act(kernel, captain, "famine_aid", helped_sol=units * COMMODITY_CONFIG["ORGANICS"]["base_price"],
                      lives_saved=units * alignment_mod.LIVES_PER_FOOD_UNIT if pre.get("starving") else 0)


@after(ActionType.STUDY_ARTIFACT, ActionType.ANOMALY_INVESTIGATE, ActionType.CARTOGRAPHY_SOLVE)
def _learned(kernel, captain, sector, action, kwargs, result, pre):
    deed(kernel, captain, "knowledge")
    if action == ActionType.ANOMALY_INVESTIGATE and random.random() < 0.3:
        chronicle_mod.log_discovery(kernel, captain, "a cosmic anomaly's secrets")


@after(ActionType.SCAN_SPACE)
def _charted(kernel, captain, sector, action, kwargs, result, pre):
    if len(captain.scanned_belts) > pre.get("belts_known", 0):
        deed(kernel, captain, "belt_charted")


@after(ActionType.EXCAVATE)
def _dug(kernel, captain, sector, action, kwargs, result, pre):
    finds = result.data.get("finds") or []
    if finds:
        looted = any(f.get("provenance") == "unlicensed" for f in finds)
        deed(kernel, captain, "looted_dig" if looted else "licensed_dig")
        relic = next((f for f in finds if f.get("kind") == "TECH_RELIC"), None)
        if relic and random.random() < 0.5:
            chronicle_mod.log_discovery(kernel, captain, f"the {relic.get('name', 'relic')}")


@after(ActionType.SELL_ARTIFACT)
def _sold(kernel, captain, sector, action, kwargs, result, pre):
    if pre.get("provenance") == "unlicensed":            # a people's heritage, sold: on the record
        deed(kernel, captain, "black_market_sale")


@after(ActionType.BANK_TRANSACTION)
def _banked(kernel, captain, sector, action, kwargs, result, pre):
    if str(kwargs.get("sub_action", "")).lower() == "repay":
        deed(kernel, captain, "loan_repaid")


@after(ActionType.ATTACK_SHIP, ActionType.TACTICAL_COMBAT)
def _fought(kernel, captain, sector, action, kwargs, result, pre):
    if "target" not in pre:
        return
    if pre.get("target_wanted"):                          # what the galaxy put on stopping them: harm it stops
        deed(kernel, captain, "justice", light=alignment_mod.lives_of_sol(kernel, pre.get("target_bounty", 0)))
    else:
        # An attack on one who has done no wrong is judged by what it did - under any banner: what the victim lost,
        # and the hull if it was destroyed
        victim = pre["target"]
        harm = max(0, pre.get("target_credits", 0) - victim.credits)
        lost_hull = pre.get("target_hull_value", 0) if victim.ship.ship_type != pre.get("target_hull") else 0
        alignment_mod.act(kernel, captain, "piracy" if captain.faction_id is None else "crusade",
                          harmed_sol=harm, destroyed_sol=lost_hull)
    if not pre.get("target_wanted") and captain.faction_id is None:
        if any("[HOSTILE ACT]" in line for line in (result.logs or [])):
            deed(kernel, captain, "hostile_act")              # breaking a protected system's peace: a judgement
        law_mod.file(kernel, "piracy", captain, sector, harm, {"kind": "captain", "id": victim.id})
    target = pre["target"]
    if target.ship.ship_type != pre.get("target_hull") or target.sector_id != pre.get("target_sector"):
        if target.sector_id == 1 and pre.get("target_sector") != 1:
            chronicle_mod.log_loss(kernel, target, captain.name, pre.get("target_sector", 1), pre.get("target_hull", "ship"))
            if target.faction_id:
                target.alignment_record["retire"] = True  # faction warships are lost, not respawned


@after(ActionType.ATTACK_PLANET)
def _bombarded(kernel, captain, sector, action, kwargs, result, pre):
    if "planet" not in pre:
        return
    planet = pre["planet"]
    dead = max(0, pre.get("population", 0) - planet.population)
    if planet.owner_id == captain.id and pre.get("owner") != captain.id:
        alignment_mod.act(kernel, captain, "conquest", harmed_sol=pre.get("treasury_sol", 0), lives_lost=dead)
        chronicle_mod.annals_conquest(kernel, planet, str(pre.get("owner")), captain)
        planet.siege = None
    else:
        alignment_mod.act(kernel, captain, "bombardment", lives_lost=dead)
        siege = planet.siege or {"start": kernel.cycle_count, "assaults": 0, "attackers": []}
        siege["assaults"] += 1
        siege["last"] = kernel.cycle_count
        if captain.name not in siege["attackers"]:
            siege["attackers"].append(captain.name)
        planet.siege = siege


@after(ActionType.PLANET_CLAIM)
def _claimed(kernel, captain, sector, action, kwargs, result, pre):
    planet = next((p for p in sector.planets if p.owner_id == captain.id), None)
    if planet is not None:
        chronicle_mod.annals_colony_founded(kernel, planet, captain)
        lineage_mod.on_colony_founded(kernel, captain, planet)


@after(ActionType.PHYLOGENY_ASCEND)
def _ascended(kernel, captain, sector, action, kwargs, result, pre):
    node = kernel.phylogeny_manager.get_node(captain.phylogeny_node_id) if captain.phylogeny_node_id else None
    if node is not None:
        chronicle_mod.log_ascension(kernel, captain, node.name, node.tier)


@after(ActionType.COVERT_OP)
def _intrigue(kernel, captain, sector, action, kwargs, result, pre):
    deed(kernel, captain, "covert_op")           # on the record
