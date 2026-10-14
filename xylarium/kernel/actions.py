"""
Xylarium actions: every player command, registered with its handler and turn cost (docs/STANDARDS.md, S6).

`GameKernel.dispatch` looks a command up here: it checks the captain's turns against the registered cost, runs the
handler, and applies the consequences common to every action (turns, wages, docking, deeds, history). A new
command is added by registering a handler here - not by growing the dispatcher.

Handlers take (kernel, captain, the captain's current sector, the command's arguments, the action, the player id)
and return an ActionResult.
"""

from typing import Any, Callable, Dict, NamedTuple, Optional

from xylarium.config import TURN_COST_COVERT_OP, TURN_COST_MOVE, TURN_COST_PLANET_OP, TURN_COST_TRADE
from xylarium.kernel import lineage as lineage_mod
from xylarium.kernel import propulsion as propulsion_mod
from xylarium.kernel import shipdesign as shipdesign_mod
from xylarium.kernel.archaeology import ArchaeologyManager
from xylarium.kernel.governance import SenateEdict, SenateOffice
from xylarium.kernel.ideology import TreatyType
from xylarium.kernel.models import ActionResult, ActionType
from xylarium.kernel.natives import NativeManager
from xylarium.kernel.nullspace import NullSpaceManager
from xylarium.kernel.surface import DistrictType
from xylarium.kernel.fx import hub as _hub


class Entry(NamedTuple):
    handler: Callable[..., ActionResult]
    turns: int


REGISTRY: Dict[ActionType, Entry] = {}


def action(kind: ActionType, turns: int = 0) -> Callable[[Callable[..., ActionResult]], Callable[..., ActionResult]]:
    """Register a handler for a command, with the turns it costs."""
    def deco(fn: Callable[..., ActionResult]) -> Callable[..., ActionResult]:
        if kind in REGISTRY:
            raise ValueError(f"{kind} is already registered")
        REGISTRY[kind] = Entry(fn, int(turns))
        return fn
    return deco


def entry(kind: ActionType) -> Optional[Entry]:
    return REGISTRY.get(kind)


def turn_cost(kind: ActionType) -> int:
    e = REGISTRY.get(kind)
    return e.turns if e is not None else 0


# ---------------------------------------------------------------------- the commands

@action(ActionType.MOVE, turns=TURN_COST_MOVE)
def _move(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_move(captain, current_sector, kwargs.get("destination"))
    return result


@action(ActionType.TRADE, turns=TURN_COST_TRADE)
def _trade(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_trade(captain, current_sector, kwargs)
    return result


@action(ActionType.PLANET_CLAIM, turns=TURN_COST_PLANET_OP)
def _planet_claim(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_planet_claim(captain, current_sector, kwargs.get("planet_id"))
    return result


@action(ActionType.PLANET_TAX, turns=0)
def _planet_tax(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_planet_tax(captain, current_sector, kwargs.get("planet_id"))
    return result


@action(ActionType.PLANET_INVEST, turns=TURN_COST_PLANET_OP)
def _planet_invest(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_planet_invest(captain, current_sector, kwargs)
    return result


@action(ActionType.PLANET_BUILD_SHIELD, turns=TURN_COST_PLANET_OP)
def _planet_build_shield(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_planet_shield(captain, current_sector, kwargs)
    return result


@action(ActionType.PLANET_RECRUIT_FIGHTERS, turns=TURN_COST_PLANET_OP)
def _planet_recruit_fighters(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_planet_fighters(captain, current_sector, kwargs)
    return result


@action(ActionType.PLANET_UPGRADE_CITADEL, turns=TURN_COST_PLANET_OP)
def _planet_upgrade_citadel(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_planet_citadel(captain, current_sector, kwargs.get("planet_id"))
    return result


@action(ActionType.PLANET_CARGO_TRANSFER, turns=0)
def _planet_cargo_transfer(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_planet_cargo(captain, current_sector, kwargs)
    return result


@action(ActionType.ATTACK_SHIP, turns=1)
@action(ActionType.TACTICAL_COMBAT, turns=1)
def _attack_ship(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_attack_ship(captain, current_sector, kwargs)
    return result


@action(ActionType.ATTACK_PLANET, turns=1)
def _attack_planet(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_attack_planet(captain, current_sector, kwargs.get("planet_id"))
    return result


@action(ActionType.STRIKE_WORLD, turns=1)
def _strike_world(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    """Detonate antimatter from the hold against a world in this sector: its air stripped, or the world broken, by
    as much as the energy delivered against its own binding (ruin.py)."""
    from xylarium.kernel import ruin
    planet = k._find_planet(current_sector, kwargs.get("planet_id"))
    if planet is None:
        return ActionResult(success=False, action=action, message="No such world in this sector.")
    if planet.owner_id == captain.id:
        return ActionResult(success=False, action=action, message=f"{planet.name} is your own world.")
    units = int(kwargs.get("units") or ruin.antimatter_needed(k, planet))
    got = ruin.strike(k, captain, planet, units)
    if not got["ok"]:
        return ActionResult(success=False, action=action, message=got["why"])
    what = "broken apart" if got["kind"] == "WORLD_SHATTERED" else f"stripped of {got['share']:.0%} of its air"
    return ActionResult(success=True, action=action, turns_spent=1,
                        message=f"{planet.name} is {what} ({got['energy_j']:.2e} J delivered).")


@action(ActionType.SHIPYARD_PURCHASE, turns=0)
def _shipyard_purchase(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_shipyard(captain, current_sector, kwargs)
    return result


@action(ActionType.RADIO_BROADCAST, turns=0)
def _radio_broadcast(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_radio(captain, kwargs.get("text", ""))
    return result


@action(ActionType.OPTIMIZE_ROUTES, turns=0)
def _optimize_routes(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    mode = kwargs.get("mode", "circular")
    routes_data = k.get_trade_routes(player_id, mode=mode, max_hops=kwargs.get("max_hops", 4))
    result = ActionResult(
        success=routes_data.get("success", False),
        action=ActionType.OPTIMIZE_ROUTES,
        message=f"Trade route optimization complete ({mode}).",
        turns_spent=0,
        data=routes_data
    )
    return result


@action(ActionType.BANK_TRANSACTION, turns=0)
def _bank_transaction(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_bank(captain, current_sector, kwargs)
    return result


@action(ActionType.REST, turns=0)
def _rest(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_rest(captain, current_sector)
    return result


@action(ActionType.COVERT_OP, turns=TURN_COST_COVERT_OP)
def _covert_op(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_covert_op(captain, current_sector, kwargs)
    return result


@action(ActionType.RECRUIT_OPERATIVES, turns=0)
def _recruit_operatives(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_recruit_operatives(captain, current_sector, kwargs)
    return result


@action(ActionType.STATION_SECURITY, turns=0)
def _station_security(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_station_security(captain, current_sector, kwargs)
    return result


@action(ActionType.PLANET_CIVIC_CONTRIBUTE, turns=TURN_COST_PLANET_OP)
def _planet_civic_contribute(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_planet_civic_contribute(captain, current_sector, kwargs)
    return result


@action(ActionType.PLANET_ELEMENT_TRANSFER, turns=0)
def _planet_element_transfer(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_planet_element_transfer(captain, current_sector, kwargs)
    return result


@action(ActionType.STOCK_BUY, turns=0)
def _stock_buy(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_stock_buy(captain, kwargs)
    return result


@action(ActionType.STOCK_SELL, turns=0)
def _stock_sell(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_stock_sell(captain, kwargs)
    return result


@action(ActionType.COMPANY_IPO, turns=TURN_COST_PLANET_OP)
def _company_ipo(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_company_ipo(captain, current_sector, kwargs)
    return result


@action(ActionType.FREIGHT_ACCEPT, turns=0)
def _freight_accept(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_freight_accept(captain, kwargs)
    return result


@action(ActionType.FREIGHT_DELIVER, turns=0)
def _freight_deliver(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_freight_deliver(captain, current_sector, kwargs)
    return result


@action(ActionType.CORPORATE_TAKEOVER, turns=0)
def _corporate_takeover(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_corporate_takeover(captain, kwargs)
    return result


@action(ActionType.BOARD_VOTE, turns=0)
def _board_vote(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_board_vote(captain, kwargs)
    return result


@action(ActionType.POISON_PILL, turns=0)
def _poison_pill(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_poison_pill(captain, kwargs)
    return result


@action(ActionType.PROXY_FIGHT, turns=0)
def _proxy_fight(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_proxy_fight(captain, kwargs)
    return result


@action(ActionType.STOCK_SHORT, turns=0)
def _stock_short(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_stock_short(captain, kwargs)
    return result


@action(ActionType.STOCK_COVER, turns=0)
def _stock_cover(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_stock_cover(captain, kwargs)
    return result


@action(ActionType.SET_TARIFF, turns=0)
def _set_tariff(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_set_tariff(captain, current_sector, kwargs)
    return result


@action(ActionType.EXECUTIVE_HIRE, turns=0)
def _executive_hire(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_executive_hire(captain, kwargs)
    return result


@action(ActionType.EXECUTIVE_MOVE, turns=0)
def _executive_move(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_executive_move(captain, kwargs)
    return result


@action(ActionType.MARKETING_CAMPAIGN, turns=0)
def _marketing_campaign(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_marketing_campaign(captain, kwargs)
    return result


@action(ActionType.LOBBY_CONTRIBUTE, turns=0)
def _lobby_contribute(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_lobby_contribute(captain, kwargs)
    return result


@action(ActionType.COUNCIL_VOTE, turns=0)
def _council_vote(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_council_vote(captain, kwargs)
    return result


@action(ActionType.HAULER_COMMISSION, turns=0)
def _hauler_commission(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_hauler_commission(captain, kwargs)
    return result


@action(ActionType.HAULER_ASSIGN_ROUTE, turns=0)
def _hauler_assign_route(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_hauler_assign_route(captain, kwargs)
    return result


@action(ActionType.HAULER_DECOMMISSION, turns=0)
def _hauler_decommission(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_hauler_decommission(captain, kwargs)
    return result


@action(ActionType.VC_APPLY, turns=0)
def _vc_apply(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_vc_apply(captain, kwargs)
    return result


@action(ActionType.VC_REPAY, turns=0)
def _vc_repay(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_vc_repay(captain, kwargs)
    return result


@action(ActionType.FLEET_ASSIGN_ESCORT, turns=0)
def _fleet_assign_escort(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_fleet_assign_escort(captain, kwargs)
    return result


@action(ActionType.FLEET_CONTRACT_SECURITY, turns=0)
def _fleet_contract_security(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_fleet_contract_security(captain, kwargs)
    return result


@action(ActionType.HEDGE_DERIVATIVE, turns=0)
def _hedge_derivative(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_hedge_derivative(captain, kwargs)
    return result


@action(ActionType.FORWARD_FREIGHT_CONTRACT, turns=0)
def _forward_freight_contract(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_forward_freight_contract(captain, kwargs)
    return result


@action(ActionType.FLEET_RECALL, turns=0)
def _fleet_recall(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_fleet_recall(captain, kwargs)
    return result


@action(ActionType.EMPIRE_OVERVIEW, turns=0)
def _empire_overview(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_empire_overview(captain)
    return result


@action(ActionType.RESEARCH_SELECT, turns=0)
def _research_select(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_research_select(captain, kwargs)
    return result


@action(ActionType.ANOMALY_INVESTIGATE, turns=1)
def _anomaly_investigate(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_anomaly_investigate(captain, current_sector, kwargs)
    return result


@action(ActionType.JUMP_WARP, turns=1)
def _jump_warp(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_jump_warp(captain, kwargs)
    return result


@action(ActionType.CARTOGRAPHY_SCAN, turns=0)
def _cartography_scan(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k.cartography_manager.scan_fragment(captain, kwargs.get("puzzle_id"), kernel=k)
    return result


@action(ActionType.CARTOGRAPHY_ROTATE, turns=0)
def _cartography_rotate(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k.cartography_manager.rotate_node(
        captain,
        int(kwargs.get("row", 0)),
        int(kwargs.get("col", 0)),
        kwargs.get("puzzle_id"),
        kernel=k,
    )
    return result


@action(ActionType.CARTOGRAPHY_BRIDGE, turns=0)
def _cartography_bridge(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k.cartography_manager.bridge_vector(
        captain,
        int(kwargs.get("r1", 0)),
        int(kwargs.get("c1", 0)),
        int(kwargs.get("r2", 0)),
        int(kwargs.get("c2", 0)),
        kwargs.get("puzzle_id"),
        kernel=k,
    )
    return result


@action(ActionType.CARTOGRAPHY_SOLVE, turns=0)
def _cartography_solve(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k.cartography_manager.solve_puzzle(
        captain,
        kwargs.get("puzzle_id", k.cartography_manager.active_puzzle_id),
        kernel=k,
    )
    return result


@action(ActionType.CARTOGRAPHY_BUY_CHIT, turns=0)
def _cartography_buy_chit(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k.cartography_manager.buy_broker_chit(captain, kernel=k)
    return result


@action(ActionType.CARTOGRAPHY_SALVAGE, turns=0)
def _cartography_salvage(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k.cartography_manager.salvage_deep_space(captain, kernel=k)
    return result


@action(ActionType.CARTOGRAPHY_SELECT, turns=0)
def _cartography_select(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    pid = kwargs.get("puzzle_id", "PUZZLE-NEXUS")
    if pid in k.cartography_manager.puzzles:
        k.cartography_manager.active_puzzle_id = pid
        captain.active_cartography_puzzle = pid
        result = ActionResult(
            success=True,
            action=ActionType.CARTOGRAPHY_SELECT,
            message=f"Active cartography matrix set to '{k.cartography_manager.puzzles[pid].name}'.",
            data=k.cartography_manager.puzzles[pid].to_dict(),
        )
    else:
        result = ActionResult(success=False, action=ActionType.CARTOGRAPHY_SELECT, message=f"Unknown puzzle ID: {pid}")
    return result


@action(ActionType.TOLL_GATE_DEPLOY, turns=0)
def _toll_gate_deploy(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    s_id = kwargs.get("shortcut_id", "SMUGGLER_SHORTCUT")
    fee = int(kwargs.get("toll_fee", 0) or 0)                  # none given: what the shortcut is worth (transit.py)
    result = k.cartography_manager.deploy_toll_gate(captain, shortcut_id=s_id, toll_fee=fee, kernel=k)
    return result


@action(ActionType.TOLL_GATE_SET_FEE, turns=0)
def _toll_gate_set_fee(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    g_id = kwargs.get("gate_id", "")
    fee = int(kwargs.get("toll_fee", 0) or 0)
    result = k.cartography_manager.set_toll_fee(captain, gate_id=g_id, new_fee=fee)
    return result


@action(ActionType.CARTOGRAPHY_FORGE_CHIT, turns=0)
def _cartography_forge_chit(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    mode = kwargs.get("mode", "sell")
    rival = kwargs.get("target_rival_id")
    result = k.cartography_manager.forge_starmap_chit(captain, mode=mode, target_rival_id=rival, kernel=k)
    return result


@action(ActionType.CARTOGRAPHY_CATALYZE, turns=0)
def _cartography_catalyze(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    pid = kwargs.get("puzzle_id")
    elem = kwargs.get("element")
    amt = int(kwargs.get("amount", 5))
    result = k.cartography_manager.catalyze_puzzle(captain, puzzle_id=pid, element=elem, amount=amt, kernel=k)
    return result


@action(ActionType.SURVEY_PROBE_LAUNCH, turns=0)
def _survey_probe_launch(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    t_sec = int(kwargs.get("target_sector", 61))
    result = k.cartography_manager.launch_survey_probe(captain, target_sector=t_sec, kernel=k)
    return result


@action(ActionType.COGNITIVE_AUTOMATE, turns=1)
def _cognitive_automate(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    from xylarium.kernel.cognition import CognitiveOrgan
    turns_before = captain.turns_left
    result = CognitiveOrgan.think(captain, k)
    # Automation is never free: charge 1 turn unless the executed deed already spent turns
    result.turns_spent = 0 if captain.turns_left < turns_before else 1
    return result


@action(ActionType.IDEOLOGY_TREATY_PROPOSE, turns=0)
def _ideology_treaty_propose(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    t_type = kwargs.get("treaty_type", TreatyType.NON_AGGRESSION)
    if isinstance(t_type, str):
        t_type = TreatyType(t_type)
    result = k.ideology_manager.propose_treaty(
        proposer=captain,
        target_id=kwargs.get("target_id", ""),
        treaty_type=t_type,
        duration=int(kwargs.get("duration", 100)),
        captains=list(k.captains.values()),
    )
    return result


@action(ActionType.IDEOLOGY_TREATY_SIGN, turns=0)
def _ideology_treaty_sign(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k.ideology_manager.sign_treaty(
        signer=captain,
        treaty_id=kwargs.get("treaty_id", ""),
    )
    return result


@action(ActionType.IDEOLOGY_AID_DISPATCH, turns=TURN_COST_PLANET_OP)
def _ideology_aid_dispatch(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    p = k.get_planet(kwargs.get("planet_id"))
    if not p and current_sector.planets:
        p = current_sector.planets[0]
    result = k.ideology_manager.dispatch_famine_aid(
        captain=captain,
        target_planet=p,
        food_units=int(kwargs.get("food_units", 20)),
        kernel=k,
    )
    return result


@action(ActionType.TRADE_COMPACT_NEGOTIATE, turns=0)
def _trade_compact_negotiate(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    civ_name = kwargs.get("civilization_name", kwargs.get("target_civ", kwargs.get("target_id", "")))
    return k.ideology_manager.negotiate_civilization_compact(
        proposer_id=captain.id,
        civilization_name=civ_name,
        terms=kwargs,
        kernel=k,
    )


@action(ActionType.ALCHEMY_TRANSMUTE, turns=TURN_COST_PLANET_OP)
def _alchemy_transmute(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k.alchemy_manager.transmute(
        captain=captain,
        recipe_id=kwargs.get("recipe_id", ""),
        iterations=int(kwargs.get("iterations", 1)),
    )
    return result


@action(ActionType.ISRU_REFINE, turns=0)
def _isru_refine(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    recipe_id = kwargs.get("recipe_id", "")
    return k.alchemy_manager.refine_isru(
        captain=captain,
        recipe_id=recipe_id,
        kernel=k,
    )


@action(ActionType.BIOSPHERE_SEED, turns=0)
def _biosphere_seed(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_biosphere_seed(captain, kwargs)


@action(ActionType.XENOBIOLOGY_SURVEY, turns=0)
def _xenobiology_survey(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_xenobiology_survey(captain, kwargs)


@action(ActionType.XENOBIOLOGY_SAMPLE, turns=0)
def _xenobiology_sample(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_xenobiology_sample(captain, kwargs)


@action(ActionType.XENOBIOLOGY_CULTURE, turns=0)
def _xenobiology_culture(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_xenobiology_culture(captain, kwargs)


@action(ActionType.XENOBIOLOGY_GRAFT, turns=0)
def _xenobiology_graft(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_xenobiology_graft(captain, kwargs)


@action(ActionType.WORKBENCH_TECH_TUNE, turns=0)
def _workbench_tech_tune(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_workbench_tech_tune(captain, kwargs)


@action(ActionType.WORKBENCH_MARKET_TUNE, turns=0)
def _workbench_market_tune(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_workbench_market_tune(captain, kwargs)


@action(ActionType.WORKBENCH_FX_TUNE, turns=0)
def _workbench_fx_tune(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_workbench_fx_tune(captain, kwargs)


@action(ActionType.WORKBENCH_DIPLOMACY_TUNE, turns=0)
def _workbench_diplomacy_tune(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_workbench_diplomacy_tune(captain, kwargs)


@action(ActionType.WORKBENCH_STARCRAFT_TUNE, turns=0)
def _workbench_starcraft_tune(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_workbench_starcraft_tune(captain, kwargs)


@action(ActionType.WORKBENCH_DOCK_TUNE, turns=0)
def _workbench_dock_tune(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_workbench_dock_tune(captain, kwargs)


@action(ActionType.WORKBENCH_SATELLITE_TUNE, turns=0)
def _workbench_satellite_tune(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k._handle_workbench_satellite_tune(captain, kwargs)


@action(ActionType.SENATE_CAMPAIGN, turns=0)
def _senate_campaign(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    office = kwargs.get("office", SenateOffice.CHANCELLOR)
    if isinstance(office, str):
        office = SenateOffice(office)
    result = k.governance_manager.register_candidate(
        captain=captain,
        office=office,
    )
    return result


@action(ActionType.SENATE_VOTE, turns=0)
def _senate_vote(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    office = kwargs.get("office", SenateOffice.CHANCELLOR)
    if isinstance(office, str):
        office = SenateOffice(office)
    result = k.governance_manager.cast_vote(
        voter=captain,
        office=office,
        candidate_id=kwargs.get("candidate_id", ""),
        owned_planets=k.get_planets_owned_by(captain.id),
    )
    return result


@action(ActionType.SENATE_ENACT_EDICT, turns=0)
def _senate_enact_edict(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    office = kwargs.get("office", SenateOffice.CHANCELLOR)
    if isinstance(office, str):
        office = SenateOffice(office)
    edict = kwargs.get("edict", SenateEdict.SOL_STIMULUS_REBATE)
    if isinstance(edict, str):
        edict = SenateEdict(edict)
    result = k.governance_manager.enact_edict(
        captain=captain,
        office=office,
        edict=edict,
        captains=list(k.captains.values()),
        planets=k.get_all_planets(),
    )
    return result


@action(ActionType.SURFACE_BUILD_DISTRICT, turns=TURN_COST_PLANET_OP)
def _surface_build_district(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    p = k.get_planet(kwargs.get("planet_id"))
    if not p and current_sector.planets:
        p = current_sector.planets[0]
    if not p:
        result = ActionResult(success=False, action=action, message="No planet found in sector.")
    else:
        dist = kwargs.get("district", DistrictType.HABITATION_DOME)
        if isinstance(dist, str):
            dist = DistrictType(dist)
        result = k.surface_manager.build_district(
            captain=captain,
            planet=p,
            x=int(kwargs.get("x", 0)),
            y=int(kwargs.get("y", 0)),
            district=dist,
        )
    return result


@action(ActionType.SURFACE_DEMOLISH_DISTRICT, turns=TURN_COST_PLANET_OP)
def _surface_demolish_district(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    p = k.get_planet(kwargs.get("planet_id"))
    if not p and current_sector.planets:
        p = current_sector.planets[0]
    if not p:
        result = ActionResult(success=False, action=action, message="No planet found in sector.")
    else:
        result = k.surface_manager.demolish_district(
            captain=captain,
            planet=p,
            x=int(kwargs.get("x", 0)),
            y=int(kwargs.get("y", 0)),
        )
    return result


@action(ActionType.SURFACE_RECRUIT_TROOPS, turns=TURN_COST_PLANET_OP)
def _surface_recruit_troops(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    p = k.get_planet(kwargs.get("planet_id"))
    if not p and current_sector.planets:
        p = current_sector.planets[0]
    if not p:
        result = ActionResult(success=False, action=action, message="No planet found in sector.")
    else:
        result = k.surface_manager.recruit_troops(
            captain=captain,
            planet=p,
            divisions=int(kwargs.get("divisions", 1)),
        )
    return result


@action(ActionType.SURFACE_INVADE, turns=TURN_COST_PLANET_OP)
def _surface_invade(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    p = k.get_planet(kwargs.get("planet_id"))
    if not p and current_sector.planets:
        p = current_sector.planets[0]
    if not p:
        result = ActionResult(success=False, action=action, message="No target planet found to invade.")
    else:
        result = k.surface_manager.invade_planet(
            attacker=captain,
            target_planet=p,
            divisions_to_commit=int(kwargs.get("divisions", 10)),
        )
    return result


@action(ActionType.FX_EXCHANGE, turns=0)
def _fx_exchange(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    from xylarium.kernel import fxroutes
    ok, msg, out = fxroutes.exchange(k, captain, getattr(current_sector, "id", None),
                                     kwargs.get("from_currency", _hub()), kwargs.get("to_currency", "FRN"),
                                     int(kwargs.get("amount", 0)))      # where it is docked: the place's own desk
    result = ActionResult(success=ok, action=action, message=msg, data={"received": out})
    return result


@action(ActionType.HIRE_ESCORT, turns=0)
def _hire_escort(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    from xylarium.kernel import fxroutes
    planet = k.get_planet(kwargs.get("planet_id", ""))
    if planet is None or planet.sector_id != captain.sector_id:
        return ActionResult(success=False, action=action, message="Hire an escort from a world in this system.")
    ok, msg = fxroutes.hire(k, captain, planet, int(kwargs.get("fighters", 10)),
                            k.cycle_count + int(kwargs.get("cycles", 100)), kwargs.get("hazard", "BORDERLAND"))
    return ActionResult(success=ok, action=action, message=msg)


@action(ActionType.SCAN_SPACE, turns=1)
def _scan_space(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = NullSpaceManager.scan(captain, current_sector, k)
    return result


@action(ActionType.MINE_ASTEROIDS, turns=1)
def _mine_asteroids(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = NullSpaceManager.mine(captain, current_sector, kwargs.get("belt_id"), k)
    return result


@action(ActionType.SALVAGE_DEBRIS, turns=1)
def _salvage_debris(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = NullSpaceManager.salvage(captain, current_sector, k)
    return result


@action(ActionType.DEPLOY_SENTRIES, turns=1)
def _deploy_sentries(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = NullSpaceManager.deploy_sentries(captain, current_sector, kwargs.get("amount", 0))
    return result


@action(ActionType.RECALL_SENTRIES, turns=0)
def _recall_sentries(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = NullSpaceManager.recall_sentries(captain, current_sector)
    return result


@action(ActionType.SURVEY_RUINS, turns=1)
def _survey_ruins(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = ArchaeologyManager.survey(captain, current_sector, kwargs.get("planet_id"), k)
    return result


@action(ActionType.EXCAVATE, turns=1)
def _excavate(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = ArchaeologyManager.excavate(captain, current_sector, kwargs.get("planet_id"),
                                         bool(kwargs.get("shore", False)), k)
    return result


@action(ActionType.SELL_ARTIFACT, turns=0)
def _sell_artifact(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = ArchaeologyManager.sell(captain, current_sector, kwargs.get("artifact_id"), k)
    return result


@action(ActionType.STUDY_ARTIFACT, turns=1)
def _study_artifact(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = ArchaeologyManager.study(captain, kwargs.get("artifact_id"), k)
    return result


@action(ActionType.RANK_PROMOTE, turns=0)
def _rank_promote(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_rank_promote(captain, kwargs)
    return result


@action(ActionType.PHYLOGENY_ASCEND, turns=0)
def _phylogeny_ascend(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_phylogeny_ascend(captain, kwargs)
    return result


@action(ActionType.CANOPY_OVERRIDE, turns=0)
def _canopy_override(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_canopy_override(captain, kwargs)
    return result


@action(ActionType.NATIVE_INTERACT, turns=1)
def _native_interact(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = NativeManager.interact(k, captain, current_sector, kwargs)
    return result


@action(ActionType.LIBRARY_BROWSE, turns=0)
def _library_browse(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_library(captain, current_sector, kwargs)
    return result


@action(ActionType.CHRONICLE_WRITE, turns=0)
def _chronicle_write(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_chronicle_write(captain, kwargs)
    return result


@action(ActionType.SHORE_LEAVE, turns=0)
def _shore_leave(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_shore_leave(captain, current_sector, kwargs)
    return result


@action(ActionType.POPULATION_POLICY, turns=0)
def _population_policy(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_population_policy(captain, kwargs)
    return result


@action(ActionType.BUDGET_SET, turns=0)
@action(ActionType.GOVERNMENT_GRANT, turns=0)
@action(ActionType.STATION_BUILD, turns=0)
def _budget_set(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    result = k._handle_polity(captain, current_sector, action, kwargs)
    return result


@action(ActionType.SHIP_DESIGN, turns=0)
def _ship_design(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    try:
        spec = shipdesign_mod.register(k, captain, kwargs.get("name", ""), kwargs.get("frame", ""),
                                       dict(kwargs.get("modules") or {}), kwargs.get("drive"),
                                       float(kwargs.get("royalty", 0.05)), kwargs.get("description", ""))
        msg = (f"Design registered: {spec['name']} - {spec['frame']}, {spec['drive']} cell, holds {spec['holds']}, "
               f"shields {spec['max_shields']}, berths {spec['berths']}, mass {spec['mass']}, "
               f"{spec['price']:,} Cr to build (royalty {spec['royalty']:.0%}).")
        result = ActionResult(success=True, action=ActionType.SHIP_DESIGN, message=msg, data=spec)
    except ValueError as e:
        result = ActionResult(success=False, action=ActionType.SHIP_DESIGN, message=str(e))
    return result


@action(ActionType.DRIVE_REFIT, turns=0)
def _drive_refit(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    try:
        msg = propulsion_mod.refit_drive(k, captain, current_sector, str(kwargs.get("drive", "")).upper())
        result = ActionResult(success=True, action=ActionType.DRIVE_REFIT, message=msg, turns_spent=1)
    except ValueError as e:
        result = ActionResult(success=False, action=ActionType.DRIVE_REFIT, message=str(e))
    return result


@action(ActionType.RETIRE_LINEAGE, turns=0)
def _retire_lineage(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    if lineage_mod.bound(k, captain.id) is None:
        result = ActionResult(success=False, action=action, message="You lead no lineage to retire.")
    elif not kwargs.get("confirm"):
        result = ActionResult(success=False, action=action, message="Retirement ends your lineage. Confirm to proceed.")
    else:
        result = ActionResult(success=True, action=action, message=lineage_mod.extinction(k, captain, "retired"))
    return result


@action(ActionType.CHARTER_ACCEPT, turns=0)
def _charter_accept(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    """Sign on to a VIP charter posted at this system (the party must fit your berths); fly them to be paid."""
    from xylarium.kernel import tourism
    cid = tourism.accept(k, captain, current_sector)
    if cid is None:
        return ActionResult(success=False, action=action,
                            message="No charter here fits your berths (or you already carry guests).")
    c = tourism.charters(k)[cid]
    return ActionResult(success=True, action=action,
                        message=f"CHARTER {cid}: {c['party']} VIPs aboard, bound for {c['dest_name']} "
                                f"(Sector {c['dest_sector']}). The fare is paid on arrival.")


# ---------------------------------------------------------------------- designing and seeding peoples (designer.py)
def _design_target(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any]) -> Any:
    pid = kwargs.get("planet_id")
    return next((p for p in current_sector.planets if p.id == pid or p.name == pid), None) if pid else None


def _design_of(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    return {"name": kwargs.get("name"), "metabolism": kwargs.get("metabolism", "biotic"),
            "body_plan": kwargs.get("body_plan", "bimaniform"), "genome": dict(kwargs.get("genome") or {}),
            "motto": kwargs.get("motto"), "sigil": kwargs.get("sigil", "*")}


@action(ActionType.SPECIES_DESIGN, turns=0)
def _species_design(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any,
                    player_id: str) -> ActionResult:
    from xylarium.kernel import designer, knowledge
    planet = _design_target(k, captain, current_sector, kwargs)
    if planet is None:
        return ActionResult(False, action, "Name a world in this sector to design for (planet_id).")
    pv = designer.preview(k, knowledge.holder_of_captain(captain), _design_of(kwargs), planet)
    msg = (f"DESIGN for {planet.name}: niche {pv['niche'] or 'none'}, its wild land would feed {pv['foragers_fed']:,} "
           f"foragers; editing mastery {pv['mastery']:.0%}, mathematics {pv['mathematics']:.0%}. "
           + "; ".join(designer.describe(pv["foresight"])) + f". Cost {pv['cost']:,} Cr."
           + (f" Cannot seed: {pv['why_not']}." if pv["why_not"] else ""))
    return ActionResult(True, action, msg, data=pv)


@action(ActionType.SPECIES_SEED, turns=2)
def _species_seed(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any,
                  player_id: str) -> ActionResult:
    from xylarium.kernel import designer, knowledge, ledger
    planet = _design_target(k, captain, current_sector, kwargs)
    if planet is None:
        return ActionResult(False, action, "Name a world in this sector to seed (planet_id).")
    holder = knowledge.holder_of_captain(captain)
    design = _design_of(kwargs)
    pv = designer.preview(k, holder, design, planet)
    if pv["why_not"]:
        return ActionResult(False, action, f"Cannot seed {planet.name}: {pv['why_not']}.", data=pv)
    price = int(pv["cost"])
    if captain.credits < price:
        return ActionResult(False, action, f"Seeding costs {price:,} Cr (edits and founders' vats); you have "
                                           f"{captain.credits:,}.", data=pv)
    pv = designer.seed(k, holder, design, planet, captain.name)
    captain.credits -= price
    ledger.pay_service(price, current_sector.id)          # the gene-smiths and vat crews of this system
    return ActionResult(True, action, f"SEEDED: {designer.FOUNDERS} {pv['seeded']} set down on {planet.name}. "
                                      f"They forage now; what they become is theirs.", turns_spent=2, data=pv)


@action(ActionType.TERRAFORM, turns=2)
def _terraform(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any,
               player_id: str) -> ActionResult:
    """Process a world in this sector toward the ground a biology fits best: your own world, or an empty one you
    mean to seed. A season's worth at your mastery (terraform.rate), paid now."""
    from xylarium.kernel import knowledge, ledger, terraform
    planet = _design_target(k, captain, current_sector, kwargs)
    if planet is None:
        return ActionResult(False, action, "Name a world in this sector to terraform (planet_id).")
    if planet.owner_id not in (None, captain.id) or (planet.owner_id is None and planet.population > 0):
        return ActionResult(False, action, f"{planet.name} is not yours to remake.")
    if not terraform.can(planet):
        return ActionResult(False, action, f"{planet.name} has no ground to process (a giant).")
    metab = kwargs.get("metabolism") or getattr(captain, "metabolism", "biotic")
    ground = terraform.ideal_ground(metab)
    holder = knowledge.holder_of_captain(captain)
    dt = terraform.rate(k, holder)
    if dt <= 1e-4:
        return ActionResult(False, action, "Your people know nothing yet of planetary engineering (terraforming).")
    price = int(terraform.price(k, holder, planet, dt))
    if captain.credits < price:
        return ActionResult(False, action, f"A season of processing costs {price:,} Cr; you have {captain.credits:,}.")
    captain.credits -= price
    ledger.pay_service(price, current_sector.id)
    r = terraform.step(k, planet, ground, dt, actor=captain)
    return ActionResult(True, action, f"TERRAFORMING {planet.name} toward {ground.lower()} ground for {metab} life: "
                                      f"{r['t']:.2f} e-folds so far" +
                                      (f"; {r['displaced']:,} of its other life displaced." if r["displaced"] else "."),
                        turns_spent=2, data=r)


# ---------------------------------------------------------------------- [9] GalNet Newsfeed & Systemic Galactic Crises
@action(ActionType.CRISIS_RELIEF_DISPATCH, turns=0)
def _crisis_relief_dispatch(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.crises_manager.deliver_relief(
        kernel=k,
        captain=captain,
        crisis_id=kwargs.get("crisis_id", ""),
        commodity=kwargs.get("commodity", "ORGANICS"),
        amount=int(kwargs.get("amount", 10)),
    )


# ---------------------------------------------------------------------- [10] Megastructures, Derelicts & Relic Physics
@action(ActionType.MEGASTRUCTURE_CONSTRUCT, turns=0)
def _megastructure_construct(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.megastructures_manager.construct_megastructure(
        kernel=k,
        captain=captain,
        structure_type=kwargs.get("structure_type", "DYSON_SWARM"),
        target_id=kwargs.get("target_id"),
    )


@action(ActionType.DERELICT_BOARD_EXPEDITION, turns=1)
def _derelict_board_expedition(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.megastructures_manager.board_derelict(
        kernel=k,
        captain=captain,
        hulk_id=kwargs.get("hulk_id", ""),
    )


# ---------------------------------------------------------------------- [11] Living Bio-Fleet Armadas & Tactical Doctrines
@action(ActionType.BIOFLEET_CULTURE_HULL, turns=0)
def _biofleet_culture_hull(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.biofleets_manager.culture_bio_vessel(
        kernel=k,
        captain=captain,
        vessel_class=kwargs.get("vessel_class", "CHITIN_SWARMER"),
        wing_id=kwargs.get("wing_id"),
    )


@action(ActionType.BIOFLEET_ASSIGN_DOCTRINE, turns=0)
def _biofleet_assign_doctrine(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.biofleets_manager.assign_doctrine(
        kernel=k,
        captain=captain,
        wing_id=kwargs.get("wing_id", ""),
        doctrine=kwargs.get("doctrine", "ORBITAL_PICKET"),
        target_ref=kwargs.get("target_ref"),
    )


# ---------------------------------------------------------------------- [12] Biosphere Genesis & Atmospheric Terraforming
@action(ActionType.TERRAFORM_BOMBARD_COMET, turns=1)
def _terraform_bombard_comet(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.biosphere_genesis_manager.bombard_comet(
        kernel=k,
        captain=captain,
        planet_id=kwargs.get("planet_id", ""),
        volatiles_payload=int(kwargs.get("volatiles_payload", 5)),
    )


@action(ActionType.TERRAFORM_DEPLOY_MIRROR, turns=0)
def _terraform_deploy_mirror(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.biosphere_genesis_manager.deploy_orbital_mirror(
        kernel=k,
        captain=captain,
        planet_id=kwargs.get("planet_id", ""),
    )


@action(ActionType.TERRAFORM_SEED_BIOSPHERE, turns=1)
def _terraform_seed_biosphere(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.biosphere_genesis_manager.seed_biosphere(
        kernel=k,
        captain=captain,
        planet_id=kwargs.get("planet_id", ""),
        taxon_sample=kwargs.get("taxon_sample", "Canopy Chlorophyte"),
    )


# ---------------------------------------------------------------------- [13] Precursor Archaeology & Colonial Decoherence
@action(ActionType.EXCAVATE_PRECURSOR, turns=1)
def _excavate_precursor(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    planet = None
    pid = kwargs.get("planet_id")
    if pid:
        planet = k.get_planet(pid)
    elif current_sector and current_sector.planets:
        planet = current_sector.planets[0]
    if not planet:
        return ActionResult(
            success=False,
            action=ActionType.EXCAVATE_PRECURSOR,
            message="No planet in sector to excavate precursor relics from."
        )
    from xylarium.kernel.archaeology import ArchaeologyManager
    return ArchaeologyManager.excavate_precursor_core(captain=captain, planet=planet, kernel=k)


@action(ActionType.STABILIZE_DECOHERENCE, turns=0)
def _stabilize_decoherence(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    pid = kwargs.get("planet_id")
    if not pid and current_sector and current_sector.planets:
        pid = current_sector.planets[0].id
    if not pid:
        return ActionResult(
            success=False,
            action=ActionType.STABILIZE_DECOHERENCE,
            message="Specify planet_id to stabilize colonial decoherence."
        )
    return k.decoherence_manager.stabilize(
        kernel=k,
        captain=captain,
        planet_id=pid,
        method=kwargs.get("method", "RELAY")
    )


# ---------------------------------------------------------------------- [14] Dynamic Hyperlane & Wormhole Engineering
@action(ActionType.GATE_CONSTRUCT, turns=2)
def _gate_construct(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.wormhole_manager.construct_jump_gate(
        kernel=k,
        captain=captain,
        target_sector=int(kwargs.get("target_sector", 0)),
    )


@action(ActionType.WORMHOLE_COLLAPSE, turns=1)
def _wormhole_collapse(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.wormhole_manager.collapse_wormhole(
        kernel=k,
        captain=captain,
        target_sector=int(kwargs.get("target_sector", 0)),
    )


@action(ActionType.TOLL_BUOY_DEPLOY, turns=0)
def _toll_buoy_deploy(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.wormhole_manager.deploy_toll_buoy(
        kernel=k,
        captain=captain,
        toll_fee=int(kwargs.get("toll_fee", 250)),
    )


# ---------------------------------------------------------------------- [15] Grand Hegemony AI & Galactic Total War
@action(ActionType.HEGEMONY_ENLIST_STRIKE, turns=0)
def _hegemony_enlist_strike(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.hegemony_manager.enlist_mercenary_strike(
        kernel=k,
        captain=captain,
        faction_id=kwargs.get("faction_id", "IMPERIUM"),
        target_sector=int(kwargs.get("target_sector", 0)),
    )


# ---------------------------------------------------------------------- [16] Deep-Space Stellar Engineering & Star-Lifting
@action(ActionType.STELLAR_DEPLOY_LIFTER, turns=1)
def _stellar_deploy_lifter(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.stellar_manager.deploy_star_lifter(
        kernel=k,
        captain=captain,
    )


@action(ActionType.STELLAR_IGNITE_PROTOSTAR, turns=2)
def _stellar_ignite_protostar(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.stellar_manager.ignite_protostar(
        kernel=k,
        captain=captain,
    )


@action(ActionType.STELLAR_CORONAL_BURST, turns=1)
def _stellar_coronal_burst(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.stellar_manager.fire_coronal_burst(
        kernel=k,
        captain=captain,
        target_sector=int(kwargs.get("target_sector", 0)),
    )


# ---------------------------------------------------------------------- [17] Shadow Corporations & Covert Infiltration
@action(ActionType.SHADOW_INCORPORATE_SHELL, turns=0)
def _shadow_incorporate_shell(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.shadow_manager.incorporate_shell_company(
        kernel=k,
        captain=captain,
        company_name=kwargs.get("name", "Obsidian Holdings Anon"),
    )


@action(ActionType.SHADOW_PLANT_SLEEPER, turns=1)
def _shadow_plant_sleeper(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    pid = kwargs.get("planet_id")
    if not pid and current_sector and current_sector.planets:
        pid = current_sector.planets[0].id
    return k.shadow_manager.plant_sleeper_cell(
        kernel=k,
        captain=captain,
        planet_id=pid or "",
    )


@action(ActionType.SHADOW_EXECUTE_SABOTAGE, turns=1)
def _shadow_execute_sabotage(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    pid = kwargs.get("planet_id")
    if not pid and current_sector and current_sector.planets:
        pid = current_sector.planets[0].id
    return k.shadow_manager.execute_sabotage(
        kernel=k,
        captain=captain,
        planet_id=pid or "",
        target_subsystem=kwargs.get("target", "GRID"),
    )


@action(ActionType.SHADOW_FALSE_FLAG_STRIKE, turns=1)
def _shadow_false_flag_strike(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.shadow_manager.stage_false_flag(
        kernel=k,
        captain=captain,
        target_sector=int(kwargs.get("target_sector", current_sector.id if current_sector else 0)),
        framed_faction=kwargs.get("framed_faction", "CHOIR"),
    )


# ---------------------------------------------------------------------- [18] Kardashev Type III Cosmic Ascendance
@action(ActionType.OMEGA_UPLOAD_POPULATION, turns=2)
def _omega_upload_population(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    pid = kwargs.get("planet_id")
    if not pid and current_sector and current_sector.planets:
        pid = current_sector.planets[0].id
    return k.omega_manager.upload_population(
        kernel=k,
        captain=captain,
        planet_id=pid or "",
    )


@action(ActionType.OMEGA_METRIC_TORSION, turns=1)
def _omega_metric_torsion(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.omega_manager.anchor_metric_torsion(
        kernel=k,
        captain=captain,
    )


@action(ActionType.OMEGA_AWAKEN_FILTER, turns=2)
def _omega_awaken_filter(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.omega_manager.awaken_great_filter(
        kernel=k,
        captain=captain,
    )


# ---------------------------------------------------------------------- [19] Civilizational Epochs & Deep-Time Stewardship
@action(ActionType.EPOCH_INITIATE_METAMORPHOSIS, turns=3)
def _epoch_initiate_metamorphosis(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.epoch_manager.initiate_metamorphosis(
        kernel=k,
        captain=captain,
    )


@action(ActionType.STEWARD_SEED_NASCENT_LIFE, turns=2)
def _steward_seed_nascent_life(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    pid = kwargs.get("planet_id")
    if not pid and current_sector and current_sector.planets:
        pid = current_sector.planets[0].id
    return k.epoch_manager.seed_nascent_life(
        kernel=k,
        captain=captain,
        planet_id=pid or "",
        clade_name=kwargs.get("clade_name"),
    )


@action(ActionType.STEWARD_STABILIZE_STAR, turns=2)
def _steward_stabilize_star(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    sid = kwargs.get("sector_id", current_sector.id if current_sector else None)
    return k.epoch_manager.stabilize_stellar_core(
        kernel=k,
        captain=captain,
        sector_id=sid,
    )


@action(ActionType.STEWARD_PLANT_PRECURSOR_BEACON, turns=1)
def _steward_plant_precursor_beacon(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    pid = kwargs.get("planet_id")
    if not pid and current_sector and current_sector.planets:
        pid = current_sector.planets[0].id
    return k.epoch_manager.plant_precursor_beacon(
        kernel=k,
        captain=captain,
        planet_id=pid or "",
        relic_name=kwargs.get("relic_name"),
    )


@action(ActionType.STEWARD_SYNTROPIC_PULSE, turns=1)
def _steward_syntropic_pulse(k: Any, captain: Any, current_sector: Any, kwargs: Dict[str, Any], action: Any, player_id: str) -> ActionResult:
    return k.epoch_manager.syntropic_harmonic_pulse(
        kernel=k,
        captain=captain,
    )



