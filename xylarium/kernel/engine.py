"""
Core Game Kernel for Xylarium.
Decoupled state management, action dispatching, and universe simulation ticks.
Designed for easy integration with terminal clients, WebSocket servers, or Mycelium mesh nodes.
"""

from typing import Dict, Any, List, Optional
from collections import deque
import random

from xylarium.config import (
    TOTAL_SECTORS,
    PLAYER_STARTING_SECTOR,
    PLAYER_STARTING_CREDITS,
    PLAYER_STARTING_TURNS,
    PLAYER_STARTING_HOLDS,
    PLAYER_STARTING_SHIELDS,
    PLAYER_STARTING_FIGHTERS,
    SHIP_CATALOG,
    CITADEL_CONFIG,
    TURN_COST_MOVE,
    TURN_COST_TRADE,
    TURN_COST_PLANET_OP,
    TURN_COST_ATTACK,
)
from xylarium.kernel.models import (
    Sector,
    Captain,
    Ship,
    CargoHold,
    ActionResult,
    ActionType,
    SecurityLevel,
    PortClass,
    CommodityType,
)
from xylarium.kernel.universe import generate_universe
from xylarium.kernel.economy import EconomyManager
from xylarium.kernel.colony import ColonyManager
from xylarium.kernel.combat import CombatManager
from xylarium.kernel.ai import AIManager
from xylarium.kernel.events import EventBus


class GameKernel:
    """
    Independent game state kernel.
    Can be run locally, headless, or wrapped in network protocols.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.sectors: Dict[int, Sector] = {}
        self.captains: Dict[str, Captain] = {}
        self.event_bus = EventBus()
        self.cycle_count: int = 0
        self.action_logs: deque[str] = deque(maxlen=20)
        self.initialize_universe(seed)

    def initialize_universe(self, seed: int = 42) -> None:
        """Bootstrap universe sectors, AI rivals, and initial economy."""
        self.sectors = generate_universe(total_sectors=TOTAL_SECTORS, seed=seed)
        ai_captains = AIManager.create_ai_captains()

        for c_id, ai_cap in ai_captains.items():
            self.captains[c_id] = ai_cap
            self.sectors[ai_cap.sector_id].captains.append(c_id)

            # Give Voss and Malakor initial colonies
            if ai_cap.personality and ai_cap.personality.value == "industrialist":
                for s in self.sectors.values():
                    if s.planets and s.planets[0].owner_id is None:
                        s.planets[0].owner_id = ai_cap.id
                        s.planets[0].citadel_level = 1
                        s.planets[0].shields = 350
                        s.planets[0].fighters = 50
                        s.planets[0].name = "Aetheria Prime"
                        break
            elif ai_cap.personality and ai_cap.personality.value == "pirate":
                for s_id in range(70, TOTAL_SECTORS + 1):
                    if self.sectors[s_id].planets and self.sectors[s_id].planets[0].owner_id is None:
                        self.sectors[s_id].planets[0].owner_id = ai_cap.id
                        self.sectors[s_id].planets[0].citadel_level = 1
                        self.sectors[s_id].planets[0].shields = 200
                        self.sectors[s_id].planets[0].fighters = 60
                        self.sectors[s_id].planets[0].name = "Dread Hollow"
                        break

        # Broadcast initial welcome radio transmission
        self.event_bus.broadcast_radio(
            sender="FED-NAV",
            text="Welcome to the Frontier. Sol Federation Central Stardock operational.",
            channel="SYSTEM",
            sector_id=1
        )

        # Wire autonomous AI event listeners
        AIManager.bind_event_listeners(self)

    def register_player(self, player_id: str, player_name: str) -> Captain:
        """Register a human captain in the universe."""
        ship = Ship(
            ship_type="Scout Ship",
            cargo=CargoHold(capacity=PLAYER_STARTING_HOLDS),
            shields=PLAYER_STARTING_SHIELDS,
            max_shields=PLAYER_STARTING_SHIELDS,
            fighters=PLAYER_STARTING_FIGHTERS,
        )
        player = Captain(
            id=player_id,
            name=player_name,
            is_ai=False,
            personality=None,
            ship=ship,
            credits=PLAYER_STARTING_CREDITS,
            sector_id=PLAYER_STARTING_SECTOR,
            turns_left=PLAYER_STARTING_TURNS,
            home_sector=1,
            score=0,
        )
        self.captains[player_id] = player
        self.sectors[player.sector_id].captains.append(player_id)
        return player

    def get_player(self, player_id: str) -> Optional[Captain]:
        return self.captains.get(player_id)

    def dispatch(self, player_id: str, action: ActionType, **kwargs) -> ActionResult:
        """
        Unified action dispatcher.
        Validates turn economy, executes command, and triggers simulation tick.
        """
        captain = self.get_player(player_id)
        if not captain:
            return ActionResult(
                success=False,
                action=action,
                message=f"Player '{player_id}' not found in universe.",
            )

        # Check turn pool
        required_turns = self._get_action_turn_cost(action)
        if captain.turns_left < required_turns:
            return ActionResult(
                success=False,
                action=action,
                message=f"Insufficient turns! Requires {required_turns} turns, but you only have {captain.turns_left}.",
            )

        current_sector = self.sectors[captain.sector_id]
        result: ActionResult

        # Dispatch to sub-engines
        if action == ActionType.MOVE:
            result = self._handle_move(captain, current_sector, kwargs.get("destination"))
        elif action == ActionType.TRADE:
            result = self._handle_trade(captain, current_sector, kwargs)
        elif action == ActionType.PLANET_CLAIM:
            result = self._handle_planet_claim(captain, current_sector, kwargs.get("planet_id"))
        elif action == ActionType.PLANET_TAX:
            result = self._handle_planet_tax(captain, current_sector, kwargs.get("planet_id"))
        elif action == ActionType.PLANET_INVEST:
            result = self._handle_planet_invest(captain, current_sector, kwargs)
        elif action == ActionType.PLANET_BUILD_SHIELD:
            result = self._handle_planet_shield(captain, current_sector, kwargs)
        elif action == ActionType.PLANET_RECRUIT_FIGHTERS:
            result = self._handle_planet_fighters(captain, current_sector, kwargs)
        elif action == ActionType.PLANET_UPGRADE_CITADEL:
            result = self._handle_planet_citadel(captain, current_sector, kwargs.get("planet_id"))
        elif action == ActionType.PLANET_CARGO_TRANSFER:
            result = self._handle_planet_cargo(captain, current_sector, kwargs)
        elif action == ActionType.ATTACK_SHIP:
            result = self._handle_attack_ship(captain, current_sector, kwargs.get("target_id"))
        elif action == ActionType.ATTACK_PLANET:
            result = self._handle_attack_planet(captain, current_sector, kwargs.get("planet_id"))
        elif action == ActionType.SHIPYARD_PURCHASE:
            result = self._handle_shipyard(captain, current_sector, kwargs)
        elif action == ActionType.RADIO_BROADCAST:
            result = self._handle_radio(captain, kwargs.get("text", ""))
        else:
            result = ActionResult(
                success=False,
                action=action,
                message=f"Unsupported action type: {action}",
            )

        if result.success and result.turns_spent > 0:
            captain.turns_left = max(0, captain.turns_left - result.turns_spent)
            # Advance world simulation tick
            self.tick_simulation()

        if result.logs:
            for log in result.logs:
                self.action_logs.append(log)

        return result

    def _get_action_turn_cost(self, action: ActionType) -> int:
        if action == ActionType.MOVE:
            return TURN_COST_MOVE
        elif action == ActionType.TRADE:
            return TURN_COST_TRADE
        elif action in [
            ActionType.PLANET_CLAIM,
            ActionType.PLANET_INVEST,
            ActionType.PLANET_BUILD_SHIELD,
            ActionType.PLANET_RECRUIT_FIGHTERS,
            ActionType.PLANET_UPGRADE_CITADEL,
        ]:
            return TURN_COST_PLANET_OP
        elif action in [ActionType.ATTACK_SHIP, ActionType.ATTACK_PLANET]:
            return TURN_COST_ATTACK
        return 0

    def _handle_move(self, captain: Captain, current_sector: Sector, destination: Optional[int]) -> ActionResult:
        if destination is None or destination not in current_sector.warps:
            return ActionResult(
                success=False,
                action=ActionType.MOVE,
                message=f"Sector {destination} is not directly accessible via wormhole from Sector {current_sector.id}.",
            )

        # Move captain
        if captain.id in current_sector.captains:
            current_sector.captains.remove(captain.id)

        captain.sector_id = destination
        dest_sector = self.sectors[destination]
        if captain.id not in dest_sector.captains:
            dest_sector.captains.append(captain.id)

        msg = f"Warp drive engaged. Navigated from Sector {current_sector.id} to Sector {destination}."
        self.event_bus.emit_event("PLAYER_MOVED", {
            "player_id": captain.id,
            "player_name": captain.name,
            "from_sector": current_sector.id,
            "to_sector": destination,
            "credits": captain.credits,
            "cargo": captain.ship.cargo.to_dict(),
        })
        return ActionResult(
            success=True,
            action=ActionType.MOVE,
            message=msg,
            turns_spent=1,
            data={"new_sector": destination},
            logs=[msg]
        )

    def _handle_trade(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        if not sector.port:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"No trade port exists in Sector {sector.id}.",
            )

        trade_type = kwargs.get("type", "BUY").upper()
        commodity = kwargs.get("commodity", "").upper()
        amount = int(kwargs.get("amount", 0))

        if trade_type == "BUY":
            res = EconomyManager.execute_buy(captain, sector.port, commodity, amount)
        elif trade_type == "SELL":
            res = EconomyManager.execute_sell(captain, sector.port, commodity, amount)
        else:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Invalid trade mode '{trade_type}'. Must be 'BUY' or 'SELL'.",
            )

        if res.success:
            self.event_bus.emit_event("TRADE_EXECUTED", {
                "player_id": captain.id,
                "player_name": captain.name,
                "sector_id": sector.id,
                "credits": captain.credits,
                "cargo": captain.ship.cargo.to_dict(),
                "trade_data": res.data,
            })
        return res

    def _handle_planet_claim(self, captain: Captain, sector: Sector, planet_id: Optional[str]) -> ActionResult:
        planet = self._find_planet(sector, planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_CLAIM,
                message="No target planet found in this sector.",
            )
        res = ColonyManager.claim_planet(captain, planet)
        if res.success:
            self.event_bus.emit_event("PLANET_CLAIMED", {
                "player_id": captain.id,
                "player_name": captain.name,
                "planet_id": planet.id,
                "planet_name": planet.name,
                "sector_id": sector.id,
            })
        return res

    def _handle_planet_tax(self, captain: Captain, sector: Sector, planet_id: Optional[str]) -> ActionResult:
        planet = self._find_planet(sector, planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_TAX,
                message="No target planet found in this sector.",
            )
        return ColonyManager.collect_taxes(captain, planet)

    def _handle_planet_invest(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        planet = self._find_planet(sector, kwargs.get("planet_id"))
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_INVEST,
                message="No target planet found in this sector.",
            )
        credits_to_invest = int(kwargs.get("credits", 0))
        return ColonyManager.invest_population(captain, planet, credits_to_invest)

    def _handle_planet_shield(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        planet = self._find_planet(sector, kwargs.get("planet_id"))
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_BUILD_SHIELD,
                message="No target planet found in this sector.",
            )
        points = int(kwargs.get("points", 0))
        return ColonyManager.build_shields(captain, planet, points)

    def _handle_planet_fighters(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        planet = self._find_planet(sector, kwargs.get("planet_id"))
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_RECRUIT_FIGHTERS,
                message="No target planet found in this sector.",
            )
        count = int(kwargs.get("count", 0))
        return ColonyManager.recruit_fighters(captain, planet, count)

    def _handle_planet_citadel(self, captain: Captain, sector: Sector, planet_id: Optional[str]) -> ActionResult:
        planet = self._find_planet(sector, planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_UPGRADE_CITADEL,
                message="No target planet found in this sector.",
            )
        res = ColonyManager.upgrade_citadel(captain, planet)
        if res.success:
            self.event_bus.emit_event("CITADEL_UPGRADED", {
                "player_id": captain.id,
                "player_name": captain.name,
                "planet_id": planet.id,
                "planet_name": planet.name,
                "sector_id": sector.id,
                "level": res.data.get("citadel_level", 1),
                "level_name": res.data.get("citadel_name", "Fortified Redoubt"),
            })
        return res

    def _handle_planet_cargo(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        planet = self._find_planet(sector, kwargs.get("planet_id"))
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_CARGO_TRANSFER,
                message="No target planet found in this sector.",
            )
        comm = kwargs.get("commodity", "ORE")
        direction = kwargs.get("direction", "to_planet")
        amount = int(kwargs.get("amount", 0))
        return ColonyManager.transfer_cargo(captain, planet, comm, direction, amount)

    def _handle_attack_ship(self, captain: Captain, sector: Sector, target_id: Optional[str]) -> ActionResult:
        if not target_id or target_id not in self.captains:
            return ActionResult(
                success=False,
                action=ActionType.ATTACK_SHIP,
                message="Target captain is not present.",
            )
        target = self.captains[target_id]
        res = CombatManager.resolve_ship_battle(captain, target, sector)
        if res.success and res.data.get("defender_destroyed"):
            self.event_bus.emit_event("SHIP_DESTROYED", {
                "attacker_id": captain.id,
                "attacker_name": captain.name,
                "defender_id": target.id,
                "defender_name": target.name,
                "defender_is_ai": target.is_ai,
                "defender_personality": target.personality.value if target.personality else None,
                "sector_id": sector.id,
            })
        return res

    def _handle_attack_planet(self, captain: Captain, sector: Sector, planet_id: Optional[str]) -> ActionResult:
        planet = self._find_planet(sector, planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.ATTACK_PLANET,
                message="No target planet found in this sector.",
            )
        return CombatManager.attack_planet(captain, planet, sector)

    def _handle_shipyard(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        if sector.id != 1:
            return ActionResult(
                success=False,
                action=ActionType.SHIPYARD_PURCHASE,
                message="The Federation Naval Shipyard is located exclusively at Sol Central (Sector 1).",
            )

        item = kwargs.get("item", "").lower()
        if item == "shields":
            # Recharge shields
            needed = captain.ship.max_shields - captain.ship.shields
            if needed <= 0:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message="Shields are already at 100% capacity.",
                )
            cost = needed * 3
            if captain.credits < cost:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"Shield recharge requires {cost:,} Cr. You have {captain.credits:,} Cr.",
                )
            captain.credits -= cost
            captain.ship.shields = captain.ship.max_shields
            msg = f"Shields recharged to maximum {captain.ship.max_shields} MW for {cost:,} Cr."
            return ActionResult(
                success=True,
                action=ActionType.SHIPYARD_PURCHASE,
                message=msg,
                turns_spent=0,
                logs=[msg]
            )

        elif item == "fighters":
            qty = int(kwargs.get("amount", 10))
            if qty <= 0:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message="Quantity must be greater than zero.",
                )
            cost = qty * 45
            if captain.credits < cost:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"Purchasing {qty} fighters requires {cost:,} Cr.",
                )
            captain.credits -= cost
            captain.ship.fighters += qty
            msg = f"Purchased {qty} shipboard combat fighters for {cost:,} Cr."
            return ActionResult(
                success=True,
                action=ActionType.SHIPYARD_PURCHASE,
                message=msg,
                turns_spent=0,
                logs=[msg]
            )

        elif item == "upgrade_ship":
            ship_name = kwargs.get("ship_name")
            if ship_name not in SHIP_CATALOG:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"Unknown hull model: '{ship_name}'.",
                )
            cfg = SHIP_CATALOG[ship_name]
            cost = cfg["price"]
            if captain.credits < cost:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"{ship_name} costs {cost:,} Cr. You have {captain.credits:,} Cr.",
                )
            captain.credits -= cost
            captain.ship.ship_type = ship_name
            captain.ship.cargo.capacity = cfg["holds"]
            captain.ship.max_shields = cfg["max_shields"]
            captain.ship.shields = cfg["max_shields"]
            msg = f"COMMISSIONED NEW FLAGSHIP: {ship_name}! Holds: {cfg['holds']}, Shields: {cfg['max_shields']}."
            return ActionResult(
                success=True,
                action=ActionType.SHIPYARD_PURCHASE,
                message=msg,
                turns_spent=0,
                logs=[msg]
            )

        return ActionResult(
            success=False,
            action=ActionType.SHIPYARD_PURCHASE,
            message=f"Unknown shipyard order: '{item}'.",
        )

    def _handle_radio(self, captain: Captain, text: str) -> ActionResult:
        if not text.strip():
            return ActionResult(
                success=False,
                action=ActionType.RADIO_BROADCAST,
                message="Broadcast message cannot be empty.",
            )
        self.event_bus.broadcast_radio(
            sender=captain.name,
            text=text.strip(),
            channel="COMM-1",
            sector_id=captain.sector_id
        )
        return ActionResult(
            success=True,
            action=ActionType.RADIO_BROADCAST,
            message="Transmission broadcast across subspace frequency.",
            turns_spent=0
        )

    def _find_planet(self, sector: Sector, planet_id: Optional[str]) -> Optional[Planet]:
        if not sector.planets:
            return None
        if not planet_id:
            return sector.planets[0]
        for p in sector.planets:
            if p.id == planet_id or p.name.lower() == planet_id.lower():
                return p
        return None

    def tick_simulation(self) -> None:
        """Advance world simulation by one tick."""
        self.cycle_count += 1

        # 1. AI Rival turns
        for c_id, ai_cap in list(self.captains.items()):
            if ai_cap.is_ai:
                AIManager.execute_turn(self, ai_cap)

        # 2. Ports economic drift
        for sec in self.sectors.values():
            if sec.port:
                EconomyManager.tick_port(sec.port)

        # 3. Colony yields
        for sec in self.sectors.values():
            for p in sec.planets:
                ColonyManager.tick_colony(p)

    def find_path(self, start: int, goal: int) -> List[int]:
        """Breadth-first search for shortest warp trajectory."""
        if start == goal:
            return [start]
        visited = {start}
        queue = deque([[start]])
        while queue:
            path = queue.popleft()
            node = path[-1]
            for neighbor in self.sectors[node].warps:
                if neighbor == goal:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return []

    def get_player_view(self, player_id: str) -> Dict[str, Any]:
        """Returns clean data snapshot for client rendering."""
        captain = self.get_player(player_id)
        if not captain:
            return {}

        sector = self.sectors[captain.sector_id]
        radio_msgs = [m.to_dict() for m in self.event_bus.get_recent_radio(5)]

        # Get port catalog if present
        port_info = None
        if sector.port:
            port_info = {
                "name": sector.port.name,
                "port_class": sector.port.port_class.value,
                "catalog": EconomyManager.get_port_catalog(sector.port),
            }

        # Other captains in sector
        other_captains = []
        for c_id in sector.captains:
            if c_id != player_id and c_id in self.captains:
                c = self.captains[c_id]
                other_captains.append({
                    "id": c.id,
                    "name": c.name,
                    "is_ai": c.is_ai,
                    "personality": c.personality.value if c.personality else "human",
                    "ship_type": c.ship.ship_type,
                    "shields": c.ship.shields,
                    "fighters": c.ship.fighters,
                })

        return {
            "player": captain.to_dict(),
            "sector": {
                "id": sector.id,
                "name": sector.name,
                "security": sector.security.value,
                "warps": [
                    {
                        "sector_id": w,
                        "security": self.sectors[w].security.value,
                        "has_port": self.sectors[w].port is not None,
                        "has_planet": len(self.sectors[w].planets) > 0,
                    }
                    for w in sector.warps
                ],
                "port": port_info,
                "planets": [p.to_dict() for p in sector.planets],
                "captains": other_captains,
            },
            "radio": radio_msgs,
            "logs": list(self.action_logs)[-4:],
            "cycle": self.cycle_count,
        }
