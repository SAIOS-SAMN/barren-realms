"""
Core Game Kernel for Xylarium.
Decoupled state management, action dispatching, and universe simulation ticks.
Designed for easy integration with terminal clients, WebSocket servers, or Mycelium mesh nodes.
"""

from typing import Dict, Any, List, Optional
from collections import deque
import random

from xylarium.kernel import hulls
from xylarium.kernel import matter
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
    PLAYER_MAX_TURNS,
    MAINTENANCE_INTERVAL_CYCLES,
    MAINTENANCE_TURNS_GRANTED,
    REST_COST_CREDITS,
    REST_TURNS_RESTORED,
    BANK_LOAN_AMOUNT,
    BANK_DEBT_TOTAL,
    BANK_EMERGENCY_THRESHOLD,
    TURN_COST_COVERT_OP,
    SPECIALIZED_HULLS,
    VC_SYNDICATES,
    CLADE_RANK_MATRIX,
    STARTING_BACKGROUNDS,
    RANK_PROMOTION_THRESHOLDS,
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
    Planet,
)
from xylarium.kernel.universe import generate_universe
from xylarium.kernel.economy import EconomyManager
from xylarium.kernel.colony import ColonyManager
from xylarium.kernel.combat import CombatManager
from xylarium.kernel.ai import AIManager
from xylarium.kernel.events import EventBus
from xylarium.kernel.routes import TradeRouteOptimizer
from xylarium.kernel.espionage import EspionageManager
from xylarium.kernel.market import MarketManager
from xylarium.kernel.research import ResearchManager, jump_cost as research_jump_cost
from xylarium.config import PROCESSES
from xylarium.kernel.cartography import CartographyManager
from xylarium.kernel.ideology import IdeologyManager, TreatyType
from xylarium.kernel.alchemy import AlchemyManager
from xylarium.kernel.astronomy import AstronomyManager
from xylarium.kernel.governance import SenateManager, SenateOffice, SenateEdict
from xylarium.kernel.surface import SurfaceManager, DistrictType, TerrainType
from xylarium.kernel.phylogeny import PHYLOGENY_MANAGER
from xylarium.kernel.federal import FederalReserve
from xylarium.kernel import fx as fx_mod
from xylarium.kernel import ledger as ledger_mod
from xylarium.kernel.fx import FXMarket
from xylarium.kernel.ledger import MoneyLedger
from xylarium.kernel.nullspace import NullSpaceManager
from xylarium.kernel.archaeology import ArchaeologyManager
from xylarium.kernel.experience import ExperienceManager
from xylarium.kernel.factions import FactionManager
from xylarium.kernel.natives import NativeManager
from xylarium.kernel.chronicle import ChronicleEngine
from xylarium.kernel import alignment as alignment_mod
from xylarium.kernel import chronicle as chronicle_mod
from xylarium.kernel import lineage as lineage_mod
from xylarium.kernel.banking import BankingSystem
from xylarium.kernel.settlement import SettlementChain
from xylarium.config import (
    CAPTAIN_RATION_INTERVAL,
    CAPTAIN_RATIONS,
    CLADE_DEFAULT_SPECIES,
    HUNGER_SHIELD_DRAIN,
    BLACK_MARKET_REFIT_MARKUP,
    XP_NEW_SECTOR,
    XP_RISKIER_ZONE,
    XP_TRADE_PROFIT_SCALE,
    XP_TRADE_MAX,
    XP_INDUSTRY_HULL_UPGRADE,
    PERSONALITY_ALIGNMENT,
    CLADE_START_ALIGNMENT,
    CHRONICLE_HUNGER_SURVIVAL,
    CHRONICLE_SIEGE_MIN_ASSAULTS,
    CHRONICLE_SIEGE_LIFT_CYCLES,
    CHRONICLE_ERA_INTERVAL,
    CHRONICLE_PLAYER_ENTRY_MAX,
    IMPERIAL_XENO_SURCHARGE,
)
from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
from xylarium.kernel import demography as demography_mod
from xylarium.kernel import physics as physics_mod
from xylarium.kernel import fibres as fibres_mod
from xylarium.kernel import credit as credit_mod
from xylarium.kernel import matter as matter_mod
from xylarium.kernel import geology as geology_mod
from xylarium.kernel import propulsion as propulsion_mod
from xylarium.kernel import law as law_mod
from xylarium.kernel import crime as crime_mod
from xylarium.kernel import fertility as fertility_mod
from xylarium.kernel import nursery as nursery_mod
from xylarium.kernel import staples as staples_mod
from xylarium.kernel import sustenance as sustenance_mod
from xylarium.kernel import knowledge as knowledge_mod
from xylarium.kernel import decide as decide_mod  # noqa: F401  (registers its state)
from xylarium.kernel import liquidity as liquidity_mod  # noqa: F401  (registers its seasonal hook)
from xylarium.kernel import regimes as regimes_mod  # noqa: F401  (registers its seasonal hook)
from xylarium.kernel import intellect as intellect_mod  # noqa: F401  (registers its seasonal hook)
from xylarium.kernel import genome as genome_mod  # noqa: F401  (registers its seasonal hook)
from xylarium.kernel import introspect as introspect_mod  # noqa: F401  (registers its seasonal hook)
from xylarium.kernel import enterprise as enterprise_mod  # noqa: F401  (registers its seasonal hook)
from xylarium.kernel import chemistry as chemistry_mod  # noqa: F401  (registers its seasonal hook)
from xylarium.kernel import waystations as waystations_mod, liquidation as liquidation_mod  # noqa: F401  (register)
from xylarium.kernel import observation as observation_mod, primordial as primordial_mod, relations as relations_mod, prices as prices_mod  # noqa: F401
from xylarium.kernel import harvest as harvest_mod, energy as energy_mod, mirror as mirror_mod, contact as contact_mod, cohabit as cohabit_mod  # noqa: F401
from xylarium.kernel import clock as clock_mod, scheduler as scheduler_mod, ways as ways_mod, designer as designer_mod, terraform as terraform_mod, occupation as occupation_mod, ages as ages_mod, society as society_mod  # noqa: F401
from xylarium.kernel import cosmos as cosmos_mod, history as history_mod, institutions as institutions_mod  # noqa: F401
from xylarium.kernel import luxury as luxury_mod
from xylarium.kernel import tourism as tourism_mod
from xylarium.kernel import government as government_mod
from xylarium.kernel import shipdesign as shipdesign_mod
from xylarium.kernel import realms as realms_mod
from xylarium.kernel import actions as actions_mod
from xylarium.kernel import deeds as deeds_mod
from xylarium.kernel import subsystem
from xylarium.kernel.subsystem import Subsystem


class GameKernel:
    """
    Independent game state kernel.
    Can be run locally, headless, or wrapped in network protocols.
    """

    def __init__(self, seed: int = 42, genesis: str = "settled"):
        self.seed = seed
        self.sectors: Dict[int, Sector] = {}
        self.captains: Dict[str, Captain] = {}
        self.event_bus = EventBus()
        self.cycle_count: int = 0
        self.action_logs: deque[str] = deque(maxlen=20)
        self.state: Dict[str, Any] = {"genesis": dict(zip(("mode", "pace"), genesis.split(":", 1)))}   # "cosmic:teeming"
        self.caches: Dict[str, Any] = {}         # memoized derived values (cache.py), never saved
        self.graph_version: int = 0              # advances whenever the warp graph changes (topology.py)
        self.market_manager = MarketManager()
        self.research_manager = ResearchManager()
        self.cartography_manager = CartographyManager()
        self.ideology_manager = IdeologyManager()
        self.alchemy_manager = AlchemyManager()
        self.astronomy_manager = AstronomyManager()
        self.governance_manager = SenateManager()
        self.surface_manager = SurfaceManager()
        self.phylogeny_manager = PHYLOGENY_MANAGER
        self.federal_reserve = FederalReserve()
        self.fx_market = FXMarket()
        self.ledger = MoneyLedger()
        self.matter = matter_mod.MatterLedger()          # declared sources and sinks of every commodity
        self.monetary_policy = ledger_mod.MonetaryPolicy()
        self.factions = FactionManager()
        self.chronicle = ChronicleEngine()
        self.native_stats: Dict[str, int] = {}
        self.lineage: Optional[Dict[str, Any]] = None   # the one player lineage this kernel binds
        self.single_lineage: bool = False                # single-player saves lock the kernel to it
        self.legacy_file: Optional[str] = None           # Hall of Lineages archive (set by the client)
        self.npc_lineages: Dict[str, Dict[str, Any]] = {}  # the many houses the simulation runs
        self.banking = BankingSystem()                   # federations' central banks + the clearing union
        self.settlement = SettlementChain()              # chain-shaped quarterly settlement record
        self.activate()
        self.market_manager._kernel_ref = self
        self.initialize_universe(seed)
        self.research_manager.seed_initial_anomalies(self)
        for cap in self.captains.values():     # the genesis fleets leave port fuelled
            cap.ship.fuel = propulsion_mod.bunker_capacity(cap.ship)
        ledger_mod.endow_exchange_depth(self)  # exchanges as deep as the economies they serve
        geology_mod.survey(self)               # every world's crust is counted from the start
        self.monetary_policy.update(self)  # genesis reading sets each currency's supply target

    def activate(self) -> None:
        """Makes this kernel's FX desk and money ledger the ones module-level economics settle against."""
        fx_mod.set_active(getattr(self, "fx_market", None))
        ledger_mod.set_active(getattr(self, "ledger", None))
        matter_mod.set_active(getattr(self, "matter", None))
        if getattr(self, "ledger", None) is not None:
            self.ledger.cycle_hint = self.cycle_count
        ledger_mod.set_active_policy(getattr(self, "monetary_policy", None))
        ledger_mod.set_active_kernel(self)

    def initialize_universe(self, seed: int = 42) -> None:
        """Bootstrap universe sectors, AI rivals, and initial economy."""
        self.sectors = generate_universe(total_sectors=TOTAL_SECTORS, seed=seed)
        primordial = primordial_mod.is_primordial(self)          # every people still on its homeworld
        ai_captains = {} if primordial else AIManager.create_ai_captains()
        if primordial:
            primordial_mod.settle(self)
        else:
            self.market_manager.spawn_population_enterprises(self)
            self.market_manager.generate_freight_contracts(self)

        for c_id, ai_cap in ai_captains.items():
            self.captains[c_id] = ai_cap
            self.sectors[ai_cap.sector_id].captains.append(c_id)

            # Give Voss and Malakor initial colonies
            if ai_cap.personality and ai_cap.personality.value == "industrialist":
                for s in self.sectors.values():
                    if (s.id != 1 and s.planets and s.planets[0].owner_id is None
                            and s.planets[0].civilization is not None):
                        s.planets[0].owner_id = ai_cap.id
                        s.planets[0].citadel_level = 1
                        s.planets[0].shields = 350
                        s.planets[0].fighters = 50
                        s.planets[0].name = "Aetheria Prime"
                        if "VOSS" in self.market_manager.companies:
                            self.market_manager.companies["VOSS"].sector_id = s.id
                            self.market_manager.companies["VOSS"].planet_id = s.planets[0].id
                            self.market_manager.companies["VOSS"].planet_name = s.planets[0].name
                        break
            elif ai_cap.personality and ai_cap.personality.value == "pirate":
                for s_id in range(70, TOTAL_SECTORS + 1):
                    home = self.sectors[s_id].planets[0] if self.sectors[s_id].planets else None
                    if home and home.owner_id is None and home.civilization is not None:
                        self.sectors[s_id].planets[0].owner_id = ai_cap.id
                        self.sectors[s_id].planets[0].citadel_level = 1
                        self.sectors[s_id].planets[0].shields = 200
                        self.sectors[s_id].planets[0].fighters = 60
                        self.sectors[s_id].planets[0].name = "Dread Hollow"
                        break

        # The great powers: the Aurelian Imperium and the Choir of the Pyre take their seats
        if not primordial:
            self.factions.found_great_powers(self, seed)
        self.governance_manager.bind(self, genesis=True)          # the federal treasury is the Federation's vault
        government_mod.enrol_founders(self)
        subsystem.run_genesis(self)                                # the baseline board's realms and their claims
        government_mod.assign_ports(self)                          # every starport is bound to its system
        self._seed_alignments(seed)
        self.banking.found(self)   # founding reserves (genesis, before the money baseline)
        lineage_mod.npc_tick(self)  # the founding houses of the galaxy

        # Broadcast initial welcome radio transmission
        self.event_bus.broadcast_radio(
            sender="FED-NAV",
            text="Welcome to the Frontier. Sol Federation Central Stardock operational.",
            channel="SYSTEM",
            sector_id=1
        )

        # Wire autonomous AI event listeners
        AIManager.bind_event_listeners(self)

    def _seed_alignments(self, seed: int) -> None:
        """Genesis alignment: most civilizations are grey pragmatists, a few walk in the Light or the Dark."""
        rng = random.Random(seed * 131 + 5)
        for cap in self.captains.values():
            if cap.is_ai and cap.faction_id is None:
                bias = PERSONALITY_ALIGNMENT.get(getattr(cap.personality, "value", ""), 0.0)
                cap.cosmic_alignment = round(max(-1.0, min(1.0, bias + rng.uniform(-0.08, 0.08))), 3)
                cap.alignment_record["baseline"] = cap.cosmic_alignment
        for sec in self.sectors.values():
            for p in sec.planets:
                civ = p.civilization
                if civ is not None and civ.faction_id is None:
                    civ.alignment = 0.35 if civ.name == "Terran Federation" else alignment_mod.genesis_value(rng)
                    if civ.alignment >= 0.3 and rng.random() < 0.5:
                        civ.native_policy = "ALPHA"  # a Light people guards its neighbours' childhood

    def register_player(
        self,
        player_id: str,
        player_name: str,
        species: Optional[str] = None,
        clade: Optional[str] = None,
        background: Optional[str] = None,
        alignment: Optional[str] = None,
        bind_lineage: bool = False,
    ) -> Captain:
        """
        Register a human captain in the universe with clade and background attributes.
        In a single-lineage kernel the first captain founds the kernel's lineage; any other
        enrollment is refused (a new lineage needs a new kernel).
        """
        if self.single_lineage and self.lineage is not None and self.lineage.get("player_id") != player_id:
            raise lineage_mod.LineageLocked(
                f"This universe is bound to the {self.lineage['house']} ({self.lineage['status'].lower()}). "
                "Begin a new universe to found a new lineage.")
        bg_data = STARTING_BACKGROUNDS.get(background.lower()) if background else None

        chosen_clade = clade or (bg_data["clade"] if bg_data else "BIOTIC")
        default_species, lineage_metabolism = CLADE_DEFAULT_SPECIES.get(chosen_clade.upper(), ("human-sol", "biotic"))
        chosen_species = species or (bg_data["species"] if bg_data else default_species)
        chosen_alignment = alignment or (bg_data["alignment"] if bg_data else "Independent")

        holds = bg_data["holds"] if bg_data else PLAYER_STARTING_HOLDS
        shields = bg_data["shields"] if bg_data else PLAYER_STARTING_SHIELDS
        fighters = bg_data["fighters"] if bg_data else PLAYER_STARTING_FIGHTERS
        credits = bg_data["credits"] if bg_data else PLAYER_STARTING_CREDITS
        debt = bg_data["debt"] if bg_data else 0
        bounty = bg_data["bounty"] if bg_data else 0
        start_sector = bg_data.get("start_sector", PLAYER_STARTING_SECTOR) if bg_data else PLAYER_STARTING_SECTOR
        imperium = self.factions.factions.get("IMPERIUM")
        if chosen_clade.upper() == "IMPERIAL" and imperium is not None and imperium.capital_sector \
                and start_sector == PLAYER_STARTING_SECTOR:
            start_sector = imperium.capital_sector  # Throne-sworn officers muster at the Throneworld
        ship_class = bg_data.get("ship_class", "Scout Ship") if bg_data else "Scout Ship"

        ship = Ship(
            ship_type=ship_class,
            cargo=CargoHold(capacity=holds),
            shields=shields,
            max_shields=shields,
            fighters=fighters,
        )
        player = Captain(
            id=player_id,
            name=player_name,
            is_ai=False,
            personality=None,
            ship=ship,
            credits=credits,
            sector_id=start_sector,
            turns_left=PLAYER_STARTING_TURNS,
            home_sector=start_sector,
            score=0,
            species=chosen_species,
            clade=chosen_clade,
            rank_tier=1,
            background=background,
            alignment=chosen_alignment,
            debt=debt,
            bounty=bounty,
            metabolism=lineage_metabolism,
        )
        player.cosmic_alignment = CLADE_START_ALIGNMENT.get(chosen_clade.upper(), 0.0)
        player.alignment_record["band"] = alignment_mod.band(player.cosmic_alignment)
        player.alignment_record["baseline"] = player.cosmic_alignment
        self.captains[player_id] = player
        if player.sector_id in self.sectors:
            self.sectors[player.sector_id].captains.append(player_id)
        player.visited_sectors.append(player.sector_id)
        ledger_mod.mint("captain_charter", max(0, player.credits))
        # Crews launch provisioned with ten rations of their lineage's food
        player.ship.cargo.stow(CAPTAIN_RATIONS.get(lineage_metabolism, "ORGANICS"), 10)
        matter_mod.commission(player, "charter")          # a new charter's stores enter the galaxy
        if (bind_lineage or self.single_lineage) and self.lineage is None:
            lineage_mod.found(self, player, background)
        # New charters come with the first maintenance interval of hull cover
        player.insurance_paid_through = self.cycle_count + MAINTENANCE_INTERVAL_CYCLES
        # Each human beyond the galaxy's base company is owed room to explore (populace.py)
        if not player.is_ai:
            from xylarium.kernel import populace
            for log in populace.on_player_joined(self):
                self.action_logs.append(log)
        return player

    def get_player(self, player_id: str) -> Optional[Captain]:
        return self.captains.get(player_id)

    def dispatch(self, player_id: str, action: ActionType, **kwargs) -> ActionResult:
        """
        Unified action dispatcher.
        Validates turn economy, executes command, and triggers simulation tick.
        """
        self.activate()
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

        # An ended lineage commands nothing; its record can still be read in the Library
        if lineage_mod.is_extinct(self, player_id) and action != ActionType.LIBRARY_BROWSE:
            return ActionResult(success=False, action=action,
                                message=f"The {self.lineage['house']} has ended ({self.lineage['cause']}). "
                                        "Begin a new universe to found a new lineage.")

        # At the poles of the alignment axis, vows bind
        refusal = alignment_mod.vow_forbids(captain, action, kwargs, self)
        if refusal:
            return ActionResult(success=False, action=action, message=refusal)
        pre = deeds_mod.prestate(self, captain, current_sector, action, kwargs)

        # Dispatch to the registered command (actions.py)
        registered = actions_mod.entry(action)
        if registered is None:
            result = ActionResult(
                success=False,
                action=action,
                message=f"Unsupported action type: {action}",
            )
        else:
            result = registered.handler(self, captain, current_sector, kwargs, action, player_id)

        if result.success and action != ActionType.TRADE:
            # Trades record flux by cargo volume in _handle_trade
            self.phylogeny_manager.record_action_flux(captain, action.value)

        if result.success and result.turns_spent > 0:
            captain.turns_left = max(0, captain.turns_left - result.turns_spent)
            if not captain.faction_id:
                from xylarium.config import CREW_WAGE_ARREARS_CAP
                # Along a developed fibre the passage is quicker and cheaper for the crew (economies of scale)
                lane = (result.data or {}).get("lane_cost", 1.0) if action == ActionType.MOVE else 1.0
                wage = int(round(self.crew_wage(captain) * result.turns_spent * lane))
                captain.wages_due = min(CREW_WAGE_ARREARS_CAP, captain.wages_due + wage)
            # Advance world simulation tick for player actions
            if not captain.is_ai:
                self.tick_simulation()

        # Crew pay accrued at sea is spent ashore: settled into the docking port's treasury
        if captain.wages_due > 0:
            self._settle_wages(captain)
        # ...and the drive bunker is topped up with the port's hydrogen
        if not captain.faction_id or True:
            dock = self.sectors.get(captain.sector_id)
            if dock is not None and dock.port is not None:
                refit_log = propulsion_mod.consider_refit(self, captain, dock)
                if refit_log:
                    self.action_logs.append(f"[DRIVE] {captain.name}: {refit_log}")
                design_log = shipdesign_mod.consider(self, captain, dock)
                if design_log:
                    self.action_logs.append(f"[WORKBENCH] {design_log}")
                if captain.ship.fuel < propulsion_mod.bunker_capacity(captain.ship):
                    propulsion_mod.bunker(self, captain, dock)

        # A hungry crew eats the moment rations come aboard rather than waiting for the next meal bell
        if result.success and captain.hunger > 0:
            self._feed_crew(captain)

        # Deeds have moral weight; milestones write history
        if result.success:
            deeds_mod.consequences(self, captain, current_sector, action, kwargs, result, pre)

        if result.logs:
            for log in result.logs:
                self.action_logs.append(log)

        return result

    def _get_action_turn_cost(self, action: ActionType) -> int:
        return actions_mod.turn_cost(action)

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
        # The fibre remembers the passage (traffic, and the goods' value on the lane's flow ledger)
        lane_cost = fibres_mod.cost(self, current_sector.id, destination)
        fibres_mod.record(self, captain, current_sector.id, destination)
        # The drive burns reaction mass for the hull and its cargo; exhaust drifts where it was burned
        coast_turns = propulsion_mod.jump(self, captain, current_sector)

        msg = f"Warp drive engaged. Navigated from Sector {current_sector.id} to Sector {destination}."
        logs = [msg]
        charter_log = tourism_mod.arrive(self, captain)
        if charter_log:
            logs.append(charter_log)

        picket = NullSpaceManager.picket_engages_intruder(captain, dest_sector)
        if picket:
            logs.append(picket)

        # Navigation experience: charting new space, not shuttling between known ports
        if destination not in captain.visited_sectors:
            captain.visited_sectors.append(destination)
            ExperienceManager.award(captain, "navigation", XP_NEW_SECTOR, self)
        zone = dest_sector.security.value
        if zone != "FEDERATION" and zone not in captain.zones_entered:
            captain.zones_entered.append(zone)
            ExperienceManager.award(captain, "navigation", XP_RISKIER_ZONE, self)

        # Observation: a ship on the charted edge sees the cluster beyond (observation.py)
        seen = observation_mod.arrived(self, destination)
        if seen:
            logs.append(seen)

        # Check for sovereign sector customs tariff
        tariff_pct = 0
        toll_planet = None
        for p in dest_sector.planets:
            if p.owner_id and p.owner_id != captain.id and p.sector_tariff_pct > 0:
                if p.sector_tariff_pct > tariff_pct:
                    tariff_pct = p.sector_tariff_pct
                    toll_planet = p

        if tariff_pct > 0 and toll_planet and captain.credits > 0:
            base_toll = int(tariff_pct * 15)
            pct_toll = int(captain.credits * (tariff_pct / 100) * 0.05)
            toll = min(captain.credits, max(50, base_toll + pct_toll))
            captain.credits -= toll
            from xylarium.kernel.fx import ACTIVE_FX
            if toll_planet.currency != "SOL" and ACTIVE_FX is not None:
                toll_planet.treasury += ACTIVE_FX.swap_sol_to(toll_planet.currency, toll)
            else:
                toll_planet.treasury += toll
            toll_log = f">> CUSTOMS TRANSIT TARIFF: Paid {toll:,} Cr ({tariff_pct}%) customs toll to sovereign colony on {toll_planet.name}."
            logs.append(toll_log)

        # Check for orbital shortcut toll gate
        if hasattr(self, "cartography_manager"):
            tg_res = self.cartography_manager.check_toll_transit(captain, current_sector.id, destination, kernel=self)
            if tg_res > 0:
                logs.append(f">> TOLL GATE TRANSIT: Paid {tg_res:,} Cr orbital transit toll.")
            elif tg_res == -1:
                logs.append(f">> TOLL GATE INTERCEPTION: Picket defense drones fired warning volleys (-35 shields)!")

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
            turns_spent=hulls.spec(captain.ship).get("move_turns", 1) + coast_turns,
            data={"new_sector": destination, "lane_cost": lane_cost, "coasted": bool(coast_turns)},
            logs=logs
        )

    def turret_blocks(self, captain: Captain, sector: Sector) -> bool:
        """
        Would Federal defense turrets refuse this captain here? Outlaw signatures (Anarchy clade,
        outlaw titles, or a wanted bounty with hostile Federation standing) without a forged
        transponder are denied docking in Federation space. Autonomous captains are exempt.
        """
        if captain.is_ai:
            return False
        if sector.security != SecurityLevel.FEDERATION and sector.id > 10:
            return False
        is_outlaw = (
            getattr(captain, "clade", "BIOTIC") == "ANARCHY"
            or getattr(captain, "rank_title", "") in ["Void Drifter", "Outlaw Corsair"]
            or (captain.bounty > 0 and captain.faction_reputation.get("Federation", 50.0) < 30.0)
        )
        if not is_outlaw or getattr(captain, "active_canopy_override", None) == "ENTROPY_ZERO_EQUILIBRIUM":
            return False
        return not (getattr(captain, "forged_transponder", False)
                    or "FORGED_TRANSPONDER" in getattr(captain, "unlocked_secrets", []))

    def _check_federation_turrets(self, captain: Captain, sector: Sector, action: ActionType) -> Optional[ActionResult]:
        """
        Verifies if automated Federal defense turrets engage outlaw signatures.
        Outlaws (Anarchy clade, outlaw titles, or wanted bounties with hostile Fed rep)
        without a forged transponder are attacked with -25 shields and denied docking/trading.
        """
        if not self.turret_blocks(captain, sector):
            return None

        # Check if captain is an outlaw
        is_outlaw = (
            getattr(captain, "clade", "BIOTIC") == "ANARCHY"
            or getattr(captain, "rank_title", "") in ["Void Drifter", "Outlaw Corsair"]
            or (captain.bounty > 0 and captain.faction_reputation.get("Federation", 50.0) < 30.0)
        )

        if not is_outlaw:
            return None

        # Absolute Zero Mind canopy: zero thermal signature, turrets cannot acquire a lock
        if getattr(captain, "active_canopy_override", None) == "ENTROPY_ZERO_EQUILIBRIUM":
            return None

        # Check if transponder is forged/spoofed
        has_transponder = (
            getattr(captain, "forged_transponder", False)
            or "FORGED_TRANSPONDER" in getattr(captain, "unlocked_secrets", [])
        )
        if has_transponder:
            return None

        # Defense turrets fire!
        damage = 25
        captain.ship.shields = max(0, captain.ship.shields - damage)
        msg = (
            f"SECURITY ALERT: Sector {sector.id:03d} Federal automated defense turrets detected an unauthorized "
            f"outlaw signature! Heavy mass drivers opened fire (-{damage} Shields: {captain.ship.shields}/{captain.ship.max_shields}). "
            f"Docking clearance denied! Forge a spoofed Transponder Chit in the Cartography Lab to bypass Core defenses."
        )
        self.action_logs.append(f"[TURRET INTERCEPTION] Federal automated grid fired on {captain.name} (-{damage} shields)!")
        return ActionResult(
            success=False,
            action=action,
            message=msg,
            turns_spent=0,
            logs=[msg],
            data={"shields": captain.ship.shields, "damage": damage, "turrets_engaged": True}
        )

    def _handle_trade(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        turret_res = self._check_federation_turrets(captain, sector, ActionType.TRADE)
        if turret_res:
            return turret_res
        if not sector.port:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"No trade port exists in Sector {sector.id}.",
            )
        if law_mod.frozen_here(self, captain, sector):
            return ActionResult(success=False, action=ActionType.TRADE,
                                message="ASSETS FROZEN: an unpaid judgment of this jurisdiction's court bars you "
                                        "from its markets until it is settled.")

        trade_type = (kwargs.get("type") or kwargs.get("trade_type") or "BUY").upper()
        commodity = kwargs.get("commodity", "").upper()
        amount = int(kwargs.get("amount", 0))

        port_cur = sector.port.currency
        balance_before = fx_mod.balance(captain, port_cur)
        held_before = captain.ship.cargo.held(commodity)
        basis_before = captain.ship.cargo.cost_basis.get(commodity.lower(), 0.0)  # SOL per unit
        if trade_type == "BUY":
            res = EconomyManager.execute_buy(captain, sector.port, commodity, amount)
            if res.success and commodity.startswith("LUX_"):
                luxury_mod.record_sale(sector.port, commodity, captain.ship.cargo.held(commodity) - held_before)
        elif trade_type == "SELL":
            res = EconomyManager.execute_sell(captain, sector.port, commodity, amount)
            if res.success:
                # Realized profit in SOL: proceeds arrive in the port's currency
                sold = held_before - captain.ship.cargo.held(commodity)
                proceeds = self.fx_market.to_sol_value(port_cur, fx_mod.balance(captain, port_cur) - balance_before)
                profit = int(proceeds - basis_before * sold)
                if profit > 0:
                    ExperienceManager.record_revenue(captain, profit, self)
                    xp = min(XP_TRADE_MAX, (profit / XP_TRADE_PROFIT_SCALE) ** 0.5)
                    ExperienceManager.award(captain, "commerce", xp, self, key=f"sell:{sector.id}:{commodity.upper()}")
        else:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Invalid trade mode '{trade_type}'. Must be 'BUY' or 'SELL'.",
            )

        if res.success:
            # Municipal sales tax: the region's governments share in the commerce passing through their port
            value = int(res.data.get("total_cost", 0) or res.data.get("total_payout", 0) or 0)
            if value > 0:
                tax = self._collect_trade_tax(captain, sector, value)
                if tax:
                    res.data["sales_tax"] = tax
                    res.message += f" (sales tax {tax:,} {port_cur})"
            # Record 4D activity flux in Phylogeny Manager
            comm_u = commodity.upper()
            amt_f = float(amount)
            if comm_u in ["ORE", "FE", "TI", "SI", "NI", "CU", "ADL", "FERROLATTICE"]:
                self.phylogeny_manager.record_activity_flux(captain, mass_delta=amt_f)
            elif comm_u in ["H", "HE-3", "C", "H2O", "XE", "PYROSITE"]:
                self.phylogeny_manager.record_activity_flux(captain, thermo_delta=amt_f)
            elif comm_u in ["EQUIPMENT", "U", "PT", "SPR", "CRYOGENITE", "STELALITH", "UMBRITE", "CHITINIUM", "AETHERIUM", "M1_SUPERCONDUCTOR", "M2_BIOSPHERE_PACK", "M3_ENGINE_MANIFOLD", "M4_WARP_CORE"]:
                self.phylogeny_manager.record_activity_flux(captain, exotic_delta=amt_f)
            else:
                self.phylogeny_manager.record_activity_flux(captain, mass_delta=amt_f * 0.5, exotic_delta=amt_f * 0.5)

            self.event_bus.emit_event("TRADE_EXECUTED", {
                "player_id": captain.id,
                "player_name": captain.name,
                "sector_id": sector.id,
                "credits": captain.credits,
                "cargo": captain.ship.cargo.to_dict(),
                "trade_data": res.data,
            })
        return res

    def _tax_recipients(self, sector: Sector) -> List[Planet]:
        """The populated worlds (same money, within retail range) whose governments tax a port's commerce."""
        from xylarium.config import PORT_RETAIL_RADIUS
        from xylarium.kernel import cache
        pids = cache.memo(self, "tax_region", sector.id,
                          lambda: [p.id for p in self.market_manager._regional_worlds(
                              self, sector.id, sector.port.currency, PORT_RETAIL_RADIUS)], max_age=250)
        return [p for p in (self.get_planet(pid) for pid in pids) if p is not None and p.population > 0]

    def _collect_trade_tax(self, captain: Captain, sector: Sector, value: int) -> int:
        """Transfers the sales tax from the captain (in the port's money) to the region's worlds, or to port dues."""
        from xylarium.config import TRADE_SALES_TAX
        cur = sector.port.currency
        tax = int(value * TRADE_SALES_TAX)
        if tax <= 0:
            return 0
        if cur != "SOL" and fx_mod.balance(captain, cur) < tax:
            self.fx_market.ensure_local(captain, cur, tax)
        tax = min(tax, max(0, fx_mod.balance(captain, cur)))
        if tax <= 0:
            return 0
        fx_mod.debit(captain, cur, tax)
        worlds = self._tax_recipients(sector)
        if not worlds:
            sector.port.treasury += tax          # port dues where no government governs
            return tax
        pop = sum(p.population for p in worlds) or 1
        paid = 0
        for p in worlds:
            share = int(tax * p.population / pop)
            p.treasury += share
            paid += share
        worlds[0].treasury += tax - paid
        return tax

    def _handle_planet_claim(self, captain: Captain, sector: Sector, planet_id: Optional[str]) -> ActionResult:
        planet = self._find_planet(sector, planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_CLAIM,
                message="No target planet found in this sector.",
            )
        res = ColonyManager.claim_planet(captain, planet, sector, kernel=self)
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

    def _handle_planet_civic_contribute(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        planet = self._find_planet(sector, kwargs.get("planet_id"))
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_CIVIC_CONTRIBUTE,
                message="No habitable planet in this sector.",
            )
        work_points = int(kwargs.get("work_points", 10))
        ore_amount = int(kwargs.get("ore_amount", 0))
        return ColonyManager.contribute_civic(captain, planet, work_points, ore_amount)

    def _handle_planet_element_transfer(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        planet = self._find_planet(sector, kwargs.get("planet_id"))
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.PLANET_ELEMENT_TRANSFER,
                message="No habitable planet in this sector.",
            )
        element_id = kwargs.get("element_id", "")
        direction = kwargs.get("direction", "to_ship")
        amount = int(kwargs.get("amount", 1))
        return ColonyManager.transfer_elements(captain, planet, element_id, direction, amount)

    def _handle_stock_buy(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        ticker = kwargs.get("ticker", "")
        amount = int(kwargs.get("amount", 100))
        ok, msg, data = self.market_manager.buy_shares(captain, ticker, amount)
        return ActionResult(
            success=ok,
            action=ActionType.STOCK_BUY,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_stock_sell(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        ticker = kwargs.get("ticker", "")
        amount = int(kwargs.get("amount", 100))
        ok, msg, data = self.market_manager.sell_shares(captain, ticker, amount)
        return ActionResult(
            success=ok,
            action=ActionType.STOCK_SELL,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_company_ipo(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        planet = self._find_planet(sector, kwargs.get("planet_id"))
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.COMPANY_IPO,
                message="Must be docked at your colony to float an IPO.",
            )
        name = kwargs.get("name", f"{planet.name} Corp")
        ticker = kwargs.get("ticker", "CORP")
        industry = kwargs.get("industry", "MINING")
        ok, msg, data = self.market_manager.float_ipo(captain, planet, name, ticker, industry)
        return ActionResult(
            success=ok,
            action=ActionType.COMPANY_IPO,
            message=msg,
            turns_spent=1 if ok else 0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_freight_accept(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        contract_id = kwargs.get("contract_id", "")
        ok, msg, data = self.market_manager.accept_freight_contract(captain, contract_id)
        return ActionResult(
            success=ok,
            action=ActionType.FREIGHT_ACCEPT,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_freight_deliver(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        contract_id = kwargs.get("contract_id", "")
        planet_id = kwargs.get("planet_id")
        planet = self._find_planet(sector, planet_id) if planet_id else None

        # Auto-match with contract destination planet in current sector if not found
        if not planet:
            contract = self.market_manager.contracts.get(contract_id)
            if contract and contract.destination_sector == sector.id:
                for p in sector.planets:
                    if p.id == contract.destination_planet_id or p.name == contract.destination_name:
                        planet = p
                        break
            if not planet and sector.planets:
                planet = sector.planets[0]

        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.FREIGHT_DELIVER,
                message="No target colony in this sector to verify cargo delivery.",
            )
        ok, msg, data = self.market_manager.deliver_freight_contract(captain, contract_id, planet)
        return ActionResult(
            success=ok,
            action=ActionType.FREIGHT_DELIVER,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_corporate_takeover(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        ticker = kwargs.get("ticker", "")
        ok, msg, data = self.market_manager.execute_takeover(captain, ticker, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.CORPORATE_TAKEOVER,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_board_vote(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        ticker = kwargs.get("ticker", "")
        mandate = kwargs.get("mandate", "SPECIAL_DIVIDEND")
        extra_kwargs = {k: v for k, v in kwargs.items() if k not in ["ticker", "mandate"]}
        ok, msg, data = self.market_manager.call_board_vote(captain, ticker, mandate, kernel=self, **extra_kwargs)
        return ActionResult(
            success=ok,
            action=ActionType.BOARD_VOTE,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_poison_pill(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        ticker = kwargs.get("ticker", "")
        ok, msg, data = self.market_manager.activate_poison_pill(captain.id, ticker, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.POISON_PILL,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_proxy_fight(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        ticker = kwargs.get("ticker", "")
        ok, msg, data = self.market_manager.launch_proxy_fight(captain, ticker, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.PROXY_FIGHT,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_stock_short(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        ticker = kwargs.get("ticker", "")
        amount = int(kwargs.get("amount", 100))
        ok, msg, data = self.market_manager.short_sell(captain, ticker, amount, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.STOCK_SHORT,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_stock_cover(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        ticker = kwargs.get("ticker", "")
        amount = kwargs.get("amount")
        amount_int = int(amount) if amount is not None else None
        ok, msg, data = self.market_manager.cover_short(captain, ticker, amount_int, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.STOCK_COVER,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_set_tariff(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        sec_id = int(kwargs.get("sector_id", sector.id))
        tariff_pct = int(kwargs.get("tariff_pct", 0))
        ok, msg, data = self.market_manager.set_sector_tariff(captain, sec_id, tariff_pct, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.SET_TARIFF,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_executive_hire(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        ticker = kwargs.get("ticker", "")
        name = kwargs.get("name")
        ok, msg, data = self.market_manager.hire_sales_executive(captain, ticker, name, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.EXECUTIVE_HIRE,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_executive_move(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        exec_id = kwargs.get("exec_id", "")
        destination = int(kwargs.get("destination", captain.sector_id))
        ok, msg, data = self.market_manager.move_sales_executive(captain, exec_id, destination, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.EXECUTIVE_MOVE,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_marketing_campaign(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        ticker = kwargs.get("ticker", "")
        campaign_type = kwargs.get("campaign_type") or kwargs.get("type", "POSITIVE")
        target_ticker = kwargs.get("target_ticker")
        ok, msg, data = self.market_manager.launch_marketing_campaign(captain, ticker, campaign_type, target_ticker, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.MARKETING_CAMPAIGN,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_lobby_contribute(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        amount = int(kwargs.get("amount", 1000))
        ticker = kwargs.get("ticker") or kwargs.get("corporate_ticker")
        ok, msg, data = self.market_manager.contribute_lobbying(captain, amount, ticker, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.LOBBY_CONTRIBUTE,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_council_vote(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        bill_type = kwargs.get("bill_type", "SUBSIDY")
        target_ticker = kwargs.get("target_ticker")
        sponsor_ticker = kwargs.get("sponsor_ticker")
        ok, msg, data = self.market_manager.enact_council_resolution(captain, bill_type, target_ticker, sponsor_ticker, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.COUNCIL_VOTE,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_hauler_commission(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        name = kwargs.get("name")
        origin = kwargs.get("origin_sector", 1)
        dest = kwargs.get("dest_sector", 30)
        outbound = kwargs.get("commodity_outbound", "EQUIPMENT")
        return_comm = kwargs.get("commodity_return", "ORGANICS")
        hull_class = kwargs.get("hull_class", "STANDARD")
        try:
            origin_int = int(origin)
            dest_int = int(dest)
        except (ValueError, TypeError):
            origin_int = 1
            dest_int = 30
        ok, msg, data = self.market_manager.commission_trade_hauler(
            captain=captain,
            name=name,
            origin=origin_int,
            dest=dest_int,
            outbound=outbound,
            return_comm=return_comm,
            hull_class=hull_class,
            kernel=self,
        )
        return ActionResult(
            success=ok,
            action=ActionType.HAULER_COMMISSION,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_hauler_assign_route(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        hauler_id = kwargs.get("hauler_id", "")
        origin = kwargs.get("origin_sector", 1)
        dest = kwargs.get("dest_sector", 30)
        outbound = kwargs.get("commodity_outbound", "EQUIPMENT")
        return_comm = kwargs.get("commodity_return", "ORGANICS")
        try:
            origin_int = int(origin)
            dest_int = int(dest)
        except (ValueError, TypeError):
            origin_int = 1
            dest_int = 30
        ok, msg, data = self.market_manager.assign_hauler_route(
            captain=captain,
            hauler_id=hauler_id,
            origin=origin_int,
            dest=dest_int,
            outbound=outbound,
            return_comm=return_comm,
            kernel=self,
        )
        return ActionResult(
            success=ok,
            action=ActionType.HAULER_ASSIGN_ROUTE,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_hauler_decommission(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        hauler_id = kwargs.get("hauler_id", "")
        ok, msg, data = self.market_manager.decommission_trade_hauler(
            captain=captain,
            hauler_id=hauler_id,
            kernel=self,
        )
        return ActionResult(
            success=ok,
            action=ActionType.HAULER_DECOMMISSION,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_vc_apply(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        sec = self.sectors.get(captain.sector_id)
        if sec:
            turret_res = self._check_federation_turrets(captain, sec, ActionType.VC_APPLY)
            if turret_res:
                return turret_res
        syndicate_id = kwargs.get("syndicate_id", "")
        ok, msg, data = self.market_manager.apply_vc_funding(
            captain=captain,
            syndicate_id=syndicate_id,
            kernel=self,
        )
        return ActionResult(
            success=ok,
            action=ActionType.VC_APPLY,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_vc_repay(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        try:
            amount = int(kwargs.get("amount", 0))
        except (ValueError, TypeError):
            amount = 0
        ok, msg, data = self.market_manager.repay_vc_debt(
            captain=captain,
            amount=amount,
            kernel=self,
        )
        return ActionResult(
            success=ok,
            action=ActionType.VC_REPAY,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_fleet_assign_escort(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        hauler_id = kwargs.get("hauler_id", "")
        mode = kwargs.get("mode", "assign")
        try:
            count = int(kwargs.get("count", 0))
        except (ValueError, TypeError):
            count = 0
        ok, msg, data = self.market_manager.assign_hauler_escort(
            captain=captain,
            hauler_id=hauler_id,
            count=count,
            mode=mode,
        )
        return ActionResult(
            success=ok,
            action=ActionType.FLEET_ASSIGN_ESCORT,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_fleet_recall(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        hauler_id = kwargs.get("hauler_id", "")
        try:
            target_sector = int(kwargs.get("target_sector", 1))
        except (ValueError, TypeError):
            target_sector = 1
        ok, msg, data = self.market_manager.recall_hauler(
            captain=captain,
            hauler_id=hauler_id,
            target_sector=target_sector,
            kernel=self,
        )
        return ActionResult(
            success=ok,
            action=ActionType.FLEET_RECALL,
            message=msg,
            turns_spent=0,
            data=data,
            logs=[msg] if ok else [],
        )

    def _handle_empire_overview(self, captain: Captain) -> ActionResult:
        owned_planets = []
        for s in self.sectors.values():
            for p in s.planets:
                if p.owner_id == captain.id:
                    p_dict = p.to_dict()
                    p_dict["sector_id"] = s.id
                    p_dict["sector_name"] = s.name
                    owned_planets.append(p_dict)
        haulers = [
            h.to_dict()
            for h in self.market_manager.trade_haulers.values()
            if h.owner_id == captain.id
        ]
        return ActionResult(
            success=True,
            action=ActionType.EMPIRE_OVERVIEW,
            message="Imperial Dominion & Asset Registry retrieved.",
            turns_spent=0,
            data={
                "owned_planets": owned_planets,
                "trade_haulers": haulers,
            },
        )

    def _handle_research_select(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        tech_key = kwargs.get("tech_key", "")
        ok, msg = self.research_manager.select_research(captain, tech_key, kernel=self)
        return ActionResult(
            success=ok,
            action=ActionType.RESEARCH_SELECT,
            message=msg,
            turns_spent=0,
            logs=[msg] if ok else [],
            data={"active_research": getattr(captain, "active_research", None)}
        )

    def _handle_anomaly_investigate(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        anomaly_id = kwargs.get("anomaly_id", "")
        solve_inputs = kwargs.get("solve_inputs", {})
        return self.research_manager.investigate_anomaly(
            captain=captain,
            sector=sector,
            anomaly_id=anomaly_id,
            kernel=self,
            solve_inputs=solve_inputs,
        )

    def _handle_jump_warp(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        destination = int(kwargs.get("destination", 0))
        return self.research_manager.jump_warp(
            captain=captain,
            destination=destination,
            kernel=self,
        )

    def _handle_attack_ship(self, captain: Captain, sector: Sector, target_id_or_kwargs: Any = None, **kwargs) -> ActionResult:
        if isinstance(target_id_or_kwargs, dict):
            params = {**target_id_or_kwargs, **kwargs}
        elif isinstance(target_id_or_kwargs, str):
            params = {"target_id": target_id_or_kwargs, **kwargs}
        else:
            params = kwargs

        target_id = params.get("target_id")
        if not target_id or target_id not in self.captains:
            return ActionResult(
                success=False,
                action=ActionType.ATTACK_SHIP,
                message="Target captain is not present.",
            )
        target = self.captains[target_id]
        tactic = params.get("tactic", "volley")
        if tactic == "volley" and captain.turns_left < TURN_COST_ATTACK:
            return ActionResult(
                success=False,
                action=ActionType.ATTACK_SHIP,
                message=f"Full attack volley requires {TURN_COST_ATTACK} turns. You only have {captain.turns_left}.",
            )

        res = CombatManager.resolve_ship_battle(
            captain,
            target,
            sector,
            fighters_to_commit=params.get("fighters"),
            tactic=tactic,
            bribe_amount=params.get("bribe_amount"),
            escape_sector=params.get("escape_sector"),
            kernel=self,
        )
        if res.success and res.data.get("defender_destroyed"):
            frag = self.cartography_manager.award_pirate_drop(captain, target, sector, kernel=self)
            if frag:
                f_log = f"[SALVAGE] Recovered starmap fragment: {frag['name']} from burning pirate wreckage!"
                if res.logs:
                    res.logs.append(f_log)
                else:
                    res.logs = [f_log]
            if target.bounty > 0:
                # Paid from escrowed public funds, then the Federal Reserve; posted warrants are never minted
                claimed = self.federal_reserve.settle_bounty(target.id, target.bounty)
                target.bounty = 0
                target.bounty_placed_by = None
                captain.credits += claimed
                captain.score += max(100, claimed // 10)
                b_log = f"[BOUNTY COLLECTED] Claimed {claimed:,} Cr contract payout for neutralizing wanted target {target.name}!"
                if res.logs:
                    res.logs.append(b_log)
                else:
                    res.logs = [b_log]
                self.event_bus.broadcast_radio(
                    sender="BOUNTY-OFFICE",
                    text=f"BOUNTY CLAIMED: Captain {captain.name} neutralized wanted fugitive {target.name}! Transferred {claimed:,} Cr reward.",
                    channel="BOUNTY",
                    sector_id=sector.id
                )

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
        return CombatManager.attack_planet(captain, planet, sector, kernel=self)

    # ------------------------------------------------------------------ command modes & the empire dashboard
    def set_command_mode(self, player_id: str, mode: str) -> bool:
        """Fly Ship (cockpit) vs Empire (sovereign dashboard): a client view state, persisted per captain."""
        from xylarium.config import COMMAND_MODES
        captain = self.get_player(player_id)
        mode = str(mode).upper()
        if captain is None or mode not in COMMAND_MODES:
            return False
        captain.command_mode = mode
        return True

    def empire_dashboard(self, player_id: str) -> Dict[str, Any]:
        """
        The BRE sovereign console for one lineage: its worlds, fleets, routes, standing among the
        powers, and treasury - plus the rival lines the simulation runs around it.
        """
        captain = self.get_player(player_id)
        if captain is None:
            return {}
        mm = self.market_manager
        fxm = self.fx_market
        lin = lineage_mod.bound(self, captain.id)
        home = (lin or {}).get("home_colony")
        colonies = []
        for sec in self.sectors.values():
            for p in sec.planets:
                if p.owner_id == captain.id:
                    colonies.append({
                        "id": p.id, "name": p.name, "sector_id": sec.id, "sector_name": sec.name,
                        "planet_type": p.planet_type, "population": p.population, "morale": p.morale,
                        "citadel": p.citadel_level, "shields": p.shields, "fighters": p.fighters,
                        "vault": p.treasury, "currency": p.currency,
                        "vault_sol": int(fxm.to_sol_value(p.currency, p.treasury)),
                        "organics": p.organics_silo, "ore": p.ore_silo, "seat": p.id == home,
                        "staple": staples_mod.of(self, p), "food": staples_mod.stores(self, p),
                        "sustenance": p.society.get("sustenance"),
                        "under_siege": bool(p.siege),
                    })
        colonies.sort(key=lambda c: (not c["seat"], -c["population"]))
        haulers = [h for h in mm.trade_haulers.values() if h.owner_id == captain.id]
        by_class: Dict[str, Dict[str, int]] = {}
        for h in haulers:
            row = by_class.setdefault(h.hull_class, {"count": 0, "capacity": 0, "escorts": 0, "in_transit": 0})
            row["count"] += 1
            row["capacity"] += h.capacity
            row["escorts"] += h.escort_fighters
            row["in_transit"] += 1 if h.status == "IN_TRANSIT" else 0
        routes = [{"id": h.id, "name": h.name, "class": h.hull_class, "origin": h.origin_sector, "dest": h.dest_sector,
                   "outbound": h.commodity_outbound, "return": h.commodity_return, "status": h.status,
                   "trips": h.trips_completed, "profit": h.lifetime_profit, "wear": h.wear_and_tear}
                  for h in haulers]
        gates = [g for g in self.cartography_manager.toll_gates.values() if g.owner_id == captain.id and g.active]
        probes = [pr for pr in self.cartography_manager.survey_probes.values() if pr.owner_id == captain.id]
        sentries = {sid: s.sentries[captain.id] for sid, s in self.sectors.items() if captain.id in s.sentries}
        # Diplomacy: standing, doctrine, the powers
        treaties = []
        for t in self.ideology_manager.treaties.values():
            if t.active and captain.id in (t.signatory_a, t.signatory_b):
                other = t.signatory_b if t.signatory_a == captain.id else t.signatory_a
                treaties.append({"id": t.treaty_id if hasattr(t, "treaty_id") else "", "type": t.treaty_type.value,
                                 "with": self.captains[other].name if other in self.captains else other})
        powers = []
        for f in self.factions.factions.values():
            if f.kind not in ("IMPERIUM", "ZEALOT"):
                continue
            powers.append({
                "id": f.id, "name": f.name, "worlds": sum(1 for s in self.sectors.values() for p in s.planets if p.faction_id == f.id),
                "fleet": len(f.fleet), "dogma": round(f.dogma, 2), "stability": round(f.stability, 2),
                "card": f.card, "tithe_delivered": f.stats.get("tithe_delivered", 0), "purges": f.stats.get("purges", 0),
                "crusaders": f.stats.get("crusaders", 0), "tribute": f.stats.get("tribute", 0),
                "secessions": f.stats.get("secessions", 0), "reclamations": f.stats.get("reclamations", 0),
                "standing": round(captain.faction_reputation.get(f.name.split()[-1], 50.0), 1),
                "heretic": self.factions.is_heretic(captain) if f.id == "ZEALOT" else captain.heresy >= 3,
            })
        # Rival lines: the NPC houses the simulation runs, with their living members' holdings
        rivals = []
        for house in self.npc_lineages.values():
            if house["status"] != "ACTIVE":
                continue
            members = [self.captains[m] for m in house["members"] if m in self.captains]
            if not members:
                continue
            equity = 0
            for c in members:
                try:
                    equity += int(mm.calculate_net_equity(c, self))
                except Exception:
                    equity += c.credits
            head = max(members, key=lambda c: c.rank_tier)
            rivals.append({"id": house["id"], "name": house["name"], "clade": house["clade"], "species": house["species"],
                           "worlds": sum(len(self.get_planets_owned_by(c.id)) for c in members),
                           "net_equity": equity, "alignment": alignment_mod.band(
                               sum(c.cosmic_alignment for c in members) / len(members)),
                           "members": len(members), "generation": house["generation"], "creed": house["creed"],
                           "clones": house["clones"], "ai": True, "tier": head.rank_tier})
        rivals.sort(key=lambda r: (-r["worlds"], -r["net_equity"]))
        # Treasury
        portfolio = []
        for ticker, shares in captain.portfolio.items():
            comp = mm.companies.get(ticker)
            if comp and shares:
                portfolio.append({"ticker": ticker, "shares": shares, "price": comp.share_price, "value": shares * comp.share_price})
        try:
            net_equity = int(mm.calculate_net_equity(captain, self))
        except Exception:
            net_equity = captain.credits
        return {
            "player": {"id": captain.id, "name": captain.name, "clade": captain.clade, "species": captain.species,
                       "tier": captain.rank_tier, "title": getattr(captain, "rank_title", ""),
                       "alignment": round(captain.cosmic_alignment, 3), "band": alignment_mod.band(captain.cosmic_alignment),
                       "sector_id": captain.sector_id, "mode": captain.command_mode},
            "lineage": dict(lin) if lin else None,
            "net_equity": net_equity,
            "colonies": colonies,
            "fleets": {"by_class": by_class, "haulers": len(haulers), "toll_gates": len(gates),
                       "probes": len(probes), "sentries": sentries, "flagship": captain.ship.ship_type,
                       "flagship_fighters": captain.ship.fighters},
            "routes": routes,
            "toll_gates": [{"id": g.id, "a": g.sector_a, "b": g.sector_b, "fee": g.toll_fee, "revenue": g.total_revenue}
                           for g in gates],
            "diplomacy": {"reputation": dict(captain.faction_reputation), "bounty": captain.bounty,
                          "heresy": captain.heresy, "treaties": treaties, "powers": powers,
                          "doctrine": self.factions.hand_for(self.sectors[captain.sector_id]),
                          "authorities": [dict(f.hand) for f in self.factions.factions.values()]},
            "rivals": rivals[:10],
            "treasury": {"credits": captain.credits, "fx_wallet": dict(captain.fx_wallet),
                         "fx_wallet_sol": int(sum(fxm.to_sol_value(c, a) for c, a in captain.fx_wallet.items())),
                         "debt": captain.debt, "vc_syndicate": captain.vc_active_syndicate, "vc_debt": captain.vc_debt,
                         "vc_royalty_pct": captain.vc_royalty_pct, "credit_rating": captain.credit_rating,
                         "portfolio": portfolio, "portfolio_value": sum(p["value"] for p in portfolio),
                         "colony_vaults_sol": sum(c["vault_sol"] for c in colonies),
                         "insured_through": captain.insurance_paid_through,
                         "clones": (lin or {}).get("clones")},
        }

    @staticmethod
    def _local_currency(sector: Sector) -> str:
        if sector.port is not None:
            return sector.port.currency
        if sector.planets:
            return sector.planets[0].currency
        return fx_mod.currency_for_security(sector.security)

    def _cosmos_view(self, captain: Captain) -> Dict[str, Any]:
        """Alignment, the doctrine in force, the locals here, and the great power whose space this is."""
        sector = self.sectors[captain.sector_id]
        hand = self.factions.hand_for(sector)
        owner = self.factions.owner_of(sector.id)
        power = self.factions.factions.get(owner) if owner else None
        natives = []
        for p in sector.planets:
            n = p.natives
            if n:
                from xylarium.kernel.natives import stage_name
                natives.append({
                    "planet_id": p.id, "planet": p.name, "name": n["name"], "species": n["species"],
                    "stage": stage_name(n), "sapience": n["sapience"], "population": n["population"],
                    "temperament": n["temperament"], "awareness": round(n["awareness"], 2),
                    "contamination": round(n["contamination"], 2), "stability": round(n["stability"], 2),
                    "protector": n.get("protector"), "contacted": captain.id in n["contacted_by"],
                    "converted": n.get("converted", False),
                })
        return {
            "alignment": round(captain.cosmic_alignment, 3),
            "band": alignment_mod.band(captain.cosmic_alignment),
            "doctrine": hand,
            "natives": natives,
            "territory_of": power.name if power else None,
            "power": ({"id": power.id, "name": power.name, "dogma": round(power.dogma, 2),
                       "stability": round(power.stability, 2), "worlds": len(power.worlds),
                       "fleet": len(power.fleet)} if power else None),
            "heresy": captain.heresy,
            "library_records": len(self.chronicle.entries),
        }

    # ------------------------------------------------------------------ alignment & chronicles
    def _handle_library(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        """The Galactic Library console: browse the chronicles of captains, worlds, peoples and powers."""
        if sector.port is None and not any(p.population > 0 for p in sector.planets):
            return ActionResult(success=False, action=ActionType.LIBRARY_BROWSE,
                                message="The Galactic Library is reached from any starport or inhabited world's archive.")
        entry_id = kwargs.get("entry_id")
        if entry_id:
            entry = self.chronicle.get(entry_id)
            if entry is None:
                return ActionResult(success=False, action=ActionType.LIBRARY_BROWSE, message=f"No record {entry_id} in the Library.")
            return ActionResult(success=True, action=ActionType.LIBRARY_BROWSE,
                                message=f"{entry['id']} [{entry['kind']}] {entry['title']}", data={"entry": entry})
        rows, total = self.chronicle.query(kind=kwargs.get("kind"), subject=kwargs.get("subject"),
                                           text=kwargs.get("text"), page=int(kwargs.get("page", 0) or 0))
        return ActionResult(success=True, action=ActionType.LIBRARY_BROWSE,
                            message=f"Galactic Library: {total} record(s) match.",
                            data={"entries": rows, "total": total, "page": int(kwargs.get("page", 0) or 0),
                                  "counts": dict(self.chronicle.counts)})

    def _handle_chronicle_write(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        """Captains write their own history into the Library (journeys, life on their worlds, expeditions)."""
        text = str(kwargs.get("text", "")).strip()
        title = str(kwargs.get("title", "")).strip() or f"Log of {captain.name}"
        if len(text) < 10:
            return ActionResult(success=False, action=ActionType.CHRONICLE_WRITE,
                                message="Write at least a sentence for the Library.")
        text = text[:CHRONICLE_PLAYER_ENTRY_MAX]
        entry = self.chronicle.record(self, "PERSONAL_LOG", captain.id, captain.name, title[:80], text,
                                      sector_id=captain.sector_id, tags=["personal"],
                                      alignment=captain.cosmic_alignment, author=captain.name)
        last = captain.chronicle_stats.get("last_written", -10 ** 9)
        if self.cycle_count - last >= 100:
            alignment_mod.deed(self, captain, "chronicle_written")  # sharing knowledge is syntropic
        captain.chronicle_stats["last_written"] = self.cycle_count
        return ActionResult(success=True, action=ActionType.CHRONICLE_WRITE,
                            message=f"Filed {entry['id']} '{entry['title']}' with the Galactic Library.",
                            data={"entry": entry})

    def _tick_sieges(self) -> None:
        for sec in self.sectors.values():
            for p in sec.planets:
                siege = p.siege
                if not siege:
                    continue
                if self.cycle_count - siege.get("last", 0) >= CHRONICLE_SIEGE_LIFT_CYCLES:
                    if siege.get("assaults", 0) >= CHRONICLE_SIEGE_MIN_ASSAULTS and p.population > 0:
                        chronicle_mod.annals_siege_survived(self, p, siege)
                    p.siege = None

    def _retire_faction_ships(self) -> None:
        """Faction warships lost in battle are struck from the rolls; their purse returns to the faction vault."""
        for cid, cap in list(self.captains.items()):
            if not cap.alignment_record.get("retire"):
                continue
            f = self.factions.factions.get(cap.faction_id or "")
            if f is not None and cap.credits > 0:
                f.vault["SOL"] = f.vault.get("SOL", 0) + cap.credits
            for cur, amt in cap.fx_wallet.items():
                if f is not None and amt > 0:
                    f.vault[cur] = f.vault.get(cur, 0) + amt
            cap.credits = 0
            cap.fx_wallet = {}
            sec = self.sectors.get(cap.sector_id)
            if sec is not None and cid in sec.captains:
                sec.captains.remove(cid)
            for s in self.sectors.values():
                s.sentries.pop(cid, None)
            self.market_manager.forfeit_freight(cap, self)
            NullSpaceManager.abandon_hold(sec, cap, self.cycle_count, "decommissioned")
            del self.captains[cid]

    @staticmethod
    def crew_wage(captain: Captain) -> int:
        """Crew pay per active turn, by hull: bigger holds and bays need bigger crews."""
        from xylarium.config import CREW_WAGE_BASE
        cfg = hulls.spec(captain.ship)
        return int(round(CREW_WAGE_BASE + cfg.get("holds", 25) / 25 + cfg.get("max_fighters", 20) / 50))

    def _settle_wages(self, captain: Captain) -> None:
        """Wages are paid (and spent) where the ship docks: the port's treasury, in its own money."""
        sector = self.sectors.get(captain.sector_id)
        if sector is None or sector.port is None or not captain.wages_due:
            return
        pay = min(captain.wages_due, max(0, captain.credits))
        if pay <= 0:
            return
        captain.credits -= pay
        captain.wages_due -= pay
        self._stardock_revenue(sector, pay)

    def _handle_population_policy(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        """Sets a governed world's population policy: EXPAND (settler fleets) or STEADY (population controls),
        or its natal card: NATAL=PROPAGATION / ASCETIC / NONE, raises its nursery (NURSERY=1), or sends its
        garrison to take its staple from the richest holder in reach (RAID=1)."""
        planet = self.get_planet(kwargs.get("planet_id", ""))
        if planet is None:
            return ActionResult(success=False, action=ActionType.POPULATION_POLICY, message="No such world.")
        try:
            msg = demography_mod.population_command(self, captain, planet, kwargs)
        except ValueError as e:
            return ActionResult(success=False, action=ActionType.POPULATION_POLICY, message=str(e))
        return ActionResult(success=True, action=ActionType.POPULATION_POLICY, message=msg, logs=[msg])

    def _handle_polity(self, captain: Captain, sector: Sector, action: ActionType, kwargs: Dict[str, Any]) -> ActionResult:
        """Budget offices (set shares or hand back to the steward), directed grants, and private stations."""
        try:
            if action == ActionType.BUDGET_SET:
                shares = {k: kwargs[k] for k in government_mod.CATEGORIES if k in kwargs}
                msg = government_mod.set_budget(self, captain, kwargs.get("government", ""), shares or None,
                                                auto=bool(kwargs.get("auto")))
            elif action == ActionType.GOVERNMENT_GRANT:
                planet = self.get_planet(kwargs.get("planet_id", ""))
                if planet is None:
                    raise ValueError("No such world.")
                msg = government_mod.direct_grant(self, captain, kwargs.get("government", ""), planet,
                                                  int(kwargs.get("amount", 0)))
            else:
                planet = self.get_planet(kwargs.get("planet_id", ""))
                if planet is None or planet.sector_id != sector.id:
                    raise ValueError("Build a station over a world in the system you are in.")
                msg = tourism_mod.build_station(self, captain, planet)
        except ValueError as e:
            return ActionResult(success=False, action=action, message=str(e))
        return ActionResult(success=True, action=action, message=msg, logs=[msg], turns_spent=1)

    def _handle_shore_leave(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        """The crew goes ashore: taverns, markets, repairs to morale. Money flows into the port."""
        if sector.port is None or self.turret_blocks(captain, sector):
            return ActionResult(success=False, action=ActionType.SHORE_LEAVE, message="No port here will host your crew ashore.")
        amount = int(kwargs.get("amount", 0))
        if amount <= 0 or amount > captain.credits:
            return ActionResult(success=False, action=ActionType.SHORE_LEAVE,
                                message=f"Shore leave spends between 1 and {captain.credits:,} Cr.")
        captain.credits -= amount
        self._stardock_revenue(sector, amount)
        flavour = random.choice(["The crew drank the port dry and paid for the privilege.",
                                 "Tailors, bathhouses and a very expensive opera.",
                                 "The engineers bought everything the chandlery had and called it morale."])
        return ActionResult(success=True, action=ActionType.SHORE_LEAVE, turns_spent=1,
                            message=f"SHORE LEAVE at {sector.port.name}: {amount:,} Cr spent ashore. {flavour}")

    def _stardock_revenue(self, sector: Sector, sol_amount: int) -> None:
        """
        Yards and officer quarters are businesses: what captains pay for hulls, refits and
        rest becomes the hosting starport's revenue (cleared into local money if needed),
        so SOL keeps circulating instead of vanishing.
        """
        port = sector.port if sector is not None else None
        if sol_amount > 0 and port is None:                  # no starport to earn it: the Reserve provides it
            ledger_mod.pay_service(sol_amount, institution="unported_service")
            return
        if port is None or sol_amount <= 0:
            return
        if port.currency != "SOL":
            port.treasury += self.fx_market.swap_sol_to(port.currency, sol_amount)
        else:
            port.treasury += sol_amount

    def _handle_shipyard(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        item = kwargs.get("item", "").lower()
        # Outlaw harbors: Anarchy-space ports refit shields and fighters (no hulls) at a markup, no turrets
        black_market = sector.id != 1 and sector.security == SecurityLevel.ANARCHY and sector.port is not None
        # ...and sell hulls, at a steep markup, to captains Sol's turrets turn away
        outlaw_hull = black_market and item == "upgrade_ship" and self.turret_blocks(captain, self.sectors[1])
        if sector.port is None:                     # no dock has been built here yet (a primordial Sol): no yard
            return ActionResult(success=False, action=ActionType.SHIPYARD_PURCHASE, message="No shipyard: no dock here.")
        if sector.id != 1 and not (black_market and item in ("shields", "fighters")) and not outlaw_hull:
            return ActionResult(
                success=False,
                action=ActionType.SHIPYARD_PURCHASE,
                message=(
                    "The Federation Naval Shipyard is located exclusively at Sol Central (Sector 1). "
                    "Outlaw harbors in Anarchy space refit shields and fighters only."
                ),
            )
        if not black_market:
            turret_res = self._check_federation_turrets(captain, sector, ActionType.SHIPYARD_PURCHASE)
            if turret_res:
                return turret_res
        from xylarium.config import BLACK_MARKET_HULL_MARKUP
        markup = (BLACK_MARKET_HULL_MARKUP if outlaw_hull else BLACK_MARKET_REFIT_MARKUP) if black_market else 1.0
        venue = "black-market harbor" if black_market else "Sol Naval Shipyard"

        if item == "shields":
            # Recharge shields: partial recharges buy as many MW as the budget allows
            needed = captain.ship.max_shields - captain.ship.shields
            if needed <= 0:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message="Shields are already at 100% capacity.",
                )
            unit = 3 * markup
            budget = min(captain.credits, int(kwargs.get("budget", captain.credits)))
            points = min(needed, int(budget // unit))
            if points <= 0:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"Shield recharge costs {unit:.0f} Cr per MW. Available budget: {budget:,} Cr.",
                )
            cost = int(round(points * unit))
            captain.credits -= cost
            self._stardock_revenue(sector, cost)
            captain.ship.shields += points
            msg = f"Shields recharged +{points} MW ({captain.ship.shields}/{captain.ship.max_shields}) for {cost:,} Cr at the {venue}."
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
            ship_cfg = hulls.spec(captain.ship)
            max_fighters = ship_cfg.get("max_fighters", 20)
            if captain.ship.fighters + qty > max_fighters:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"Fighter bay capacity exceeded! Max for {captain.ship.ship_type} is {max_fighters}. Current: {captain.ship.fighters}.",
                )
            cost = int(round(qty * 45 * markup))
            if captain.credits < cost:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"Purchasing {qty} fighters requires {cost:,} Cr at the {venue}. You have {captain.credits:,} Cr.",
                )
            captain.credits -= cost
            self._stardock_revenue(sector, cost)
            captain.ship.fighters += qty
            msg = f"Purchased {qty} shipboard combat fighters for {cost:,} Cr. (Bay: {captain.ship.fighters}/{max_fighters})"
            return ActionResult(
                success=True,
                action=ActionType.SHIPYARD_PURCHASE,
                message=msg,
                turns_spent=0,
                logs=[msg]
            )

        elif item == "clone":
            from xylarium.config import LINEAGE_CLONE_PRICE, LINEAGE_MAX_CLONES
            lin = lineage_mod.bound(self, captain.id)
            if sector.id != 1:
                return ActionResult(success=False, action=ActionType.SHIPYARD_PURCHASE,
                                    message="Clone vats are kept only at Sol Central.")
            if lin is None:
                return ActionResult(success=False, action=ActionType.SHIPYARD_PURCHASE,
                                    message="Only a founded lineage keeps backup clones.")
            if lin["clones"] >= LINEAGE_MAX_CLONES:
                return ActionResult(success=False, action=ActionType.SHIPYARD_PURCHASE,
                                    message=f"The vats hold at most {LINEAGE_MAX_CLONES} backup clones.")
            if captain.credits < LINEAGE_CLONE_PRICE:
                return ActionResult(success=False, action=ActionType.SHIPYARD_PURCHASE,
                                    message=f"Growing a backup clone costs {LINEAGE_CLONE_PRICE:,} Cr.")
            captain.credits -= LINEAGE_CLONE_PRICE
            self._stardock_revenue(sector, LINEAGE_CLONE_PRICE)
            lin["clones"] += 1
            return ActionResult(success=True, action=ActionType.SHIPYARD_PURCHASE,
                                message=f"A backup clone is grown in the Sol vats ({lin['clones']}/{LINEAGE_MAX_CLONES}).")

        elif item in ("stasis_pod", "cryo_hold"):
            from xylarium.config import STASIS_POD_COST
            if getattr(captain.ship, "has_cryo_containment", False):
                return ActionResult(success=False, action=ActionType.SHIPYARD_PURCHASE,
                                    message="Stasis Pod cryogenic containment is already installed.")
            cost = int(round(STASIS_POD_COST * markup))
            if captain.credits < cost:
                return ActionResult(success=False, action=ActionType.SHIPYARD_PURCHASE,
                                    message=f"Installing a Stasis Pod module costs {cost:,} Cr. You have {captain.credits:,} Cr.")
            captain.credits -= cost
            self._stardock_revenue(sector, cost)
            captain.ship.has_cryo_containment = True
            msg = f"Stasis Pod cryogenic containment module installed for {cost:,} Cr (reduces transit spoilage by 80%)."
            return ActionResult(success=True, action=ActionType.SHIPYARD_PURCHASE,
                                message=msg, turns_spent=0, logs=[msg])

        elif item == "upgrade_ship":
            ship_name = kwargs.get("ship_name")
            cfg = hulls.lookup(self, ship_name)
            if cfg is None:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"Unknown hull model: '{ship_name}'.",
                )
            if cfg.get("clade") and cfg["clade"] != getattr(captain, "clade", "") \
                    and cfg["clade"] != getattr(captain, "faction_id", None):
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"The {ship_name} is built only for the {cfg['clade'].title()} lineage.",
                )
            min_rank = cfg.get("min_rank_tier", 1)
            if getattr(captain, "rank_tier", 1) < min_rank:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"Commissioning {ship_name} requires Rank Tier {min_rank} authorization. Your current rank is Tier {getattr(captain, 'rank_tier', 1)} ({getattr(captain, 'rank_title', 'Scrap-Apprentice')}).",
                )
            cost = int(cfg["price"] * markup)
            if captain.ship.cargo.holds_used > int(cfg["holds"] * 0.8):
                # cargo does not vanish at a refit: the new hull (iron-framed at worst) must hold what is aboard
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"{ship_name} holds {cfg['holds']} at most; unload your "
                            f"{captain.ship.cargo.holds_used:g} holds of cargo first.",
                )
            if captain.credits < cost:
                return ActionResult(
                    success=False,
                    action=ActionType.SHIPYARD_PURCHASE,
                    message=f"{ship_name} costs {cost:,} Cr at the {venue}. You have {captain.credits:,} Cr.",
                )
            captain.credits -= cost
            royalty = shipdesign_mod.royalty_on_build(self, captain, ship_name, cost)   # the designer's share
            self._stardock_revenue(sector, cost - royalty)
            iron_frame = propulsion_mod.refit(self, sector, captain.ship.ship_type, ship_name)
            if cfg.get("drive") and cfg.get("designer"):
                # a drawn design comes with the fuel cell it was drawn for; the old bunker goes back to the yard
                old = propulsion_mod.fuel_of(captain.ship)
                if old and captain.ship.fuel > 0:
                    sector.port.stock[old] = sector.port.stock.get(old, 0) + captain.ship.fuel
                captain.ship.fuel = 0
                captain.ship.drive, captain.ship.core_wear = cfg["drive"], 0
            captain.ship.ship_type = ship_name
            captain.ship.design = dict(cfg) if cfg.get("designer") else None    # a drawn hull travels with its ship
            captain.ship.cargo.capacity = int(cfg["holds"] * (0.8 if iron_frame else 1.0))
            captain.ship.max_shields = cfg["max_shields"]
            captain.ship.shields = cfg["max_shields"]
            ExperienceManager.award(captain, "industry", XP_INDUSTRY_HULL_UPGRADE, self, key=f"hull:{ship_name}")
            msg = f"COMMISSIONED NEW FLAGSHIP: {ship_name}! Holds: {captain.ship.cargo.capacity}, Shields: {cfg['max_shields']}."
            if iron_frame:
                msg += " (Iron-frame build: the yard was short of titanium and steel - heavier, less hold space.)"
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

    def _handle_bank(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        if sector.id != 1:
            return ActionResult(
                success=False,
                action=ActionType.BANK_TRANSACTION,
                message="The Federal Bank of Sol is located exclusively at Sol Central (Sector 1).",
            )
        turret_res = self._check_federation_turrets(captain, sector, ActionType.BANK_TRANSACTION)
        if turret_res:
            return turret_res

        sub_action = kwargs.get("sub_action", "status").lower()
        if sub_action in ("antiquities_permit", "permit"):
            return ArchaeologyManager.buy_permit(captain, sector, self)
        if sub_action == "loan":
            # Relief lending is funded by the Federal Reserve (premiums, surtaxes, repayments), never minted
            ok, msg = self.federal_reserve.grant_relief_loan(captain)
            if not ok:
                return ActionResult(success=False, action=ActionType.BANK_TRANSACTION, message=msg)
            self.event_bus.broadcast_radio(
                sender="FED-BANK",
                text=f"Emergency financial relief package of {BANK_LOAN_AMOUNT:,} Cr disbursed to Captain {captain.name}.",
                channel="SYSTEM",
                sector_id=1,
            )
            return ActionResult(
                success=True,
                action=ActionType.BANK_TRANSACTION,
                message=msg,
                turns_spent=0,
                logs=[msg],
                data={"credits": captain.credits, "debt": captain.debt}
            )

        elif sub_action == "repay":
            if captain.debt <= 0:
                return ActionResult(
                    success=False,
                    action=ActionType.BANK_TRANSACTION,
                    message="You have no outstanding federal loan balance.",
                )
            if captain.credits <= 0:
                return ActionResult(
                    success=False,
                    action=ActionType.BANK_TRANSACTION,
                    message="You have no credits available to repay your debt.",
                )
            req_amt = kwargs.get("amount")
            if req_amt is None:
                repay_amt = min(captain.credits, captain.debt)
            else:
                try:
                    repay_amt = min(int(req_amt), captain.credits, captain.debt)
                except (ValueError, TypeError):
                    repay_amt = min(captain.credits, captain.debt)

            if repay_amt <= 0:
                return ActionResult(
                    success=False,
                    action=ActionType.BANK_TRANSACTION,
                    message="Repayment amount must be greater than zero.",
                )

            captain.credits -= repay_amt
            captain.debt -= repay_amt
            self.federal_reserve.receive(repay_amt, "loan_repayments")
            ExperienceManager.award(captain, "commerce", min(10, max(1, repay_amt // 500)), self, key="loan_repay")
            if captain.debt == 0:
                captain.loan_repayment_history = getattr(captain, "loan_repayment_history", 0) + 1
                if hasattr(captain, "adjust_credit_rating"):
                    captain.adjust_credit_rating(25, reason="Settled Federal Bank relief loan")
                    captain.adjust_reputation("Federation", 5.0)
                msg = f"Debt repayment processed: -{repay_amt:,} Cr. Federal loan fully settled! (+25 Credit Rating, +5 Federation Reputation)"
            else:
                if hasattr(captain, "adjust_credit_rating"):
                    captain.adjust_credit_rating(max(1, repay_amt // 1000), reason="Federal Bank loan installment")
                    captain.adjust_reputation("Federation", 1.0)
                msg = f"Debt repayment processed: -{repay_amt:,} Cr. Remaining loan balance: {captain.debt:,} Cr."
            return ActionResult(
                success=True,
                action=ActionType.BANK_TRANSACTION,
                message=msg,
                turns_spent=0,
                logs=[msg],
                data={"credits": captain.credits, "debt": captain.debt}
            )

        elif sub_action in ["restitution", "clear_bounty"]:
            restitution_cost = max(captain.bounty, 5000 if captain.embargoed_by else 0)
            if restitution_cost <= 0:
                return ActionResult(
                    success=False,
                    action=ActionType.BANK_TRANSACTION,
                    message="You have no active corporate embargoes or criminal bounties.",
                )
            if captain.credits < restitution_cost:
                return ActionResult(
                    success=False,
                    action=ActionType.BANK_TRANSACTION,
                    message=f"Clearing corporate embargoes and bounties requires {restitution_cost:,} Credits in restitution. You have {captain.credits:,} Cr.",
                )
            captain.credits -= restitution_cost
            self.federal_reserve.receive(restitution_cost, "restitution")
            self.federal_reserve.release_escrow(captain.id)
            captain.bounty = 0
            captain.bounty_placed_by = None
            captain.embargoed_by.clear()
            msg = f"Paid {restitution_cost:,} Credits in legal restitution. All corporate embargoes and bounties have been cleared!"
            self.event_bus.broadcast_radio(
                sender="CONSULATE",
                text=f"LEGAL RESTITUTION: Captain {captain.name} has settled all corporate damages. Criminal blacklists and bounties expunged.",
                channel="COMM-1",
                sector_id=1
            )
            return ActionResult(
                success=True,
                action=ActionType.BANK_TRANSACTION,
                message=msg,
                turns_spent=0,
                logs=[msg],
                data={"credits": captain.credits, "bounty": 0, "embargoed_by": []}
            )

        return ActionResult(
            success=True,
            action=ActionType.BANK_TRANSACTION,
            message=f"Federal Bank of Sol Account Status: Credits: {captain.credits:,} Cr | Outstanding Debt: {captain.debt:,} Cr | Bounty: {captain.bounty:,} Cr.",
            turns_spent=0,
            data={"credits": captain.credits, "debt": captain.debt, "bounty": captain.bounty, "embargoed_by": captain.embargoed_by}
        )

    def _handle_rest(self, captain: Captain, sector: Sector) -> ActionResult:
        if sector.id != 1:
            return ActionResult(
                success=False,
                action=ActionType.REST,
                message="Officer Quarters for rest and crew replenishment are only available at Sol Central Stardock (Sector 1).",
            )
        if captain.credits < REST_COST_CREDITS:
            return ActionResult(
                success=False,
                action=ActionType.REST,
                message=f"Resting requires {REST_COST_CREDITS:,} Credits. You only have {captain.credits:,} Cr.",
            )
        if captain.turns_left >= PLAYER_MAX_TURNS:
            return ActionResult(
                success=False,
                action=ActionType.REST,
                message=f"Turns are already at maximum capacity ({PLAYER_MAX_TURNS}).",
            )

        captain.credits -= REST_COST_CREDITS
        self._stardock_revenue(sector, REST_COST_CREDITS)
        captain.turns_left = min(PLAYER_MAX_TURNS, captain.turns_left + REST_TURNS_RESTORED)
        msg = f"Rested at Stardock Officer Quarters. Restored +{REST_TURNS_RESTORED} turns for {REST_COST_CREDITS:,} Cr. (Turns: {captain.turns_left}/{PLAYER_MAX_TURNS})"
        return ActionResult(
            success=True,
            action=ActionType.REST,
            message=msg,
            turns_spent=0,
            logs=[msg],
            data={"turns_left": captain.turns_left, "credits": captain.credits}
        )

    def _handle_rank_promote(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        """Processes Captain Rank Ascension across Clade Invariants."""
        ok, msg = captain.promote_rank(kernel=self)
        if ok:
            log_entry = f"[RANK ASCENSION] {captain.name} ascended to Rank Tier {captain.rank_tier} ({captain.rank_title})!"
            self.action_logs.append(log_entry)
            self.event_bus.emit_event("RANK_PROMOTED", {
                "player_id": captain.id,
                "rank_tier": captain.rank_tier,
                "rank_title": captain.rank_title,
                "clade": captain.clade,
            })
            return ActionResult(
                success=True,
                action=ActionType.RANK_PROMOTE,
                message=msg,
                turns_spent=0,
                logs=[msg],
                data={"rank_tier": captain.rank_tier, "rank_title": captain.rank_title}
            )
        return ActionResult(
            success=False,
            action=ActionType.RANK_PROMOTE,
            message=msg,
            turns_spent=0,
        )

    def _handle_phylogeny_ascend(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        """Crystallizes ascension along the phylogenetic cladogram DAG."""
        target_node_id = kwargs.get("target_node_id") or kwargs.get("node_id")
        ok, msg = self.phylogeny_manager.ascend(captain, target_node_id=target_node_id, kernel=self)
        if ok:
            log_entry = f"[PHYLOGENETIC ASCENSION] {captain.name} crystallized node [{captain.phylogeny_node_id}] {captain.rank_title}!"
            self.action_logs.append(log_entry)
            self.event_bus.emit_event("PHYLOGENY_ASCENDED", {
                "player_id": captain.id,
                "node_id": captain.phylogeny_node_id,
                "rank_tier": captain.rank_tier,
                "rank_title": captain.rank_title,
                "clade": captain.clade,
            })
            return ActionResult(
                success=True,
                action=ActionType.PHYLOGENY_ASCEND,
                message=msg,
                turns_spent=0,
                logs=[msg],
                data={
                    "phylogeny_node_id": captain.phylogeny_node_id,
                    "rank_tier": captain.rank_tier,
                    "rank_title": captain.rank_title,
                    "clade": captain.clade,
                }
            )
        return ActionResult(
            success=False,
            action=ActionType.PHYLOGENY_ASCEND,
            message=msg,
            turns_spent=0,
        )

    def _handle_canopy_override(self, captain: Captain, kwargs: Dict[str, Any]) -> ActionResult:
        """Executes physics-rewriting Canopy Invariant Override granted by an Apex Sovereign node."""
        ok, msg, data = self.phylogeny_manager.execute_canopy_override(captain, kernel=self, **kwargs)
        if ok:
            self.action_logs.append(f"[CANOPY OVERRIDE] {msg}")
            self.event_bus.emit_event("CANOPY_OVERRIDE_EXECUTED", {
                "player_id": captain.id,
                "override": captain.active_canopy_override,
                "data": data,
            })
            return ActionResult(
                success=True,
                action=ActionType.CANOPY_OVERRIDE,
                message=msg,
                turns_spent=0,
                logs=[msg],
                data=data,
            )
        return ActionResult(
            success=False,
            action=ActionType.CANOPY_OVERRIDE,
            message=msg,
            turns_spent=0,
        )

    def _handle_covert_op(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        target_type = kwargs.get("target_type", "PLANET")
        target_id = kwargs.get("target_id", "")
        op_type = kwargs.get("op_type", "recon")
        operatives = int(kwargs.get("operatives", kwargs.get("operatives_committed", 1)))
        return EspionageManager.execute_operation(
            kernel=self,
            attacker=captain,
            target_type=target_type,
            target_id=target_id,
            op_type=op_type,
            operatives_committed=operatives
        )

    def _handle_recruit_operatives(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        amount = int(kwargs.get("amount", 1))
        return EspionageManager.recruit_operatives(captain, amount, sector)

    def _handle_station_security(self, captain: Captain, sector: Sector, kwargs: Dict[str, Any]) -> ActionResult:
        planet_id = kwargs.get("planet_id")
        planet = self._find_planet(sector, planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.STATION_SECURITY,
                message="Target planet not found in this sector.",
            )
        mode = kwargs.get("mode", "station")  # 'station' or 'withdraw'
        amount = int(kwargs.get("amount", 1))
        if mode == "withdraw":
            return EspionageManager.withdraw_security(captain, planet, amount)
        return EspionageManager.station_security(captain, planet, amount)

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

    def _feed_crew(self, cap: Captain) -> bool:
        """The crew eats one unit of its metabolic ration from unbonded stores. Returns False if none aboard."""
        ration = CAPTAIN_RATIONS.get(getattr(cap, "metabolism", "biotic"), "ORGANICS")
        cargo = cap.ship.cargo
        if cargo.unbonded(ration) <= 0:
            return False
        if ration in ("ORE", "ORGANICS", "EQUIPMENT"):
            setattr(cargo, ration.lower(), getattr(cargo, ration.lower()) - 1)
        else:
            key = next((k for k in cargo.elements if k.lower() == ration.lower()), ration)
            cargo.elements[key] -= 1
            if cargo.elements[key] <= 0:
                cargo.elements.pop(key, None)
        matter_mod.sink("eaten", ration, 1)
        if cap.hunger >= CHRONICLE_HUNGER_SURVIVAL:
            chronicle_mod.log_hunger(self, cap, cap.hunger)
        cap.hunger = 0
        return True

    def _consume_rations(self) -> None:
        """Each captain's crew consumes one unit of its metabolic ration (never bonded freight)."""
        for cap in self.captains.values():
            if not self._feed_crew(cap):
                # Hungry crews can't maintain the deflector grid and learn nothing until fed
                cap.hunger += 1
                cap.ship.shields = max(0, cap.ship.shields - HUNGER_SHIELD_DRAIN)

    def process_turn_maintenance(self) -> None:
        """Periodic BBS turn replenishment maintenance cycle."""
        for captain in self.captains.values():
            captain.turns_left = min(PLAYER_MAX_TURNS, captain.turns_left + MAINTENANCE_TURNS_GRANTED)
        self.cartography_manager.recharge_energy()
        self.event_bus.broadcast_radio(
            sender="SYSTEM",
            text=f"BBS Turn Maintenance: All active captains restocked +{MAINTENANCE_TURNS_GRANTED} turns.",
            channel="SYSTEM",
            sector_id=1,
        )
        self.action_logs.append(f"[MAINTENANCE] Universal maintenance cycle: +{MAINTENANCE_TURNS_GRANTED} turns allocated.")

    def tick_simulation(self) -> None:
        """Advance world simulation by one tick."""
        self.cycle_count += 1
        self.activate()
        scheduler_mod.lock(self, "cycle", self.cycle_count)      # every roll this cycle is the universe's own
        if getattr(self, "matter_audit", False):
            matter_mod.audit(self)

        # Periodic BBS turn replenishment maintenance cycle (+ hull insurance renewals)
        if self.cycle_count % MAINTENANCE_INTERVAL_CYCLES == 0:
            self.process_turn_maintenance()
            self.federal_reserve.collect_premiums(self)

        # Null space: belts regenerate, debris disperses
        NullSpaceManager.tick(self)

        # Crews eat: ration consumption creates steady demand for food and fuel
        if self.cycle_count % CAPTAIN_RATION_INTERVAL == 0:
            self._consume_rations()

        # Fiscal quarter: monetary authorities set fiscal policy; antitrust and the public bounty board
        if self.cycle_count % FISCAL_QUARTER_CYCLES == 0:
            subsystem.run_season(self)           # the fiscal quarter, in subsystem.SEASON order

        # Great powers: tithes, dogma, crusades, secessions, doctrine reviews
        for log in self.factions.tick(self):
            self.action_logs.append(log)
        self._retire_faction_ships()
        seat = lineage_mod.check_seat(self)
        if seat:
            self.action_logs.append(seat)
        for log in lineage_mod.npc_tick(self):
            self.action_logs.append(log)

        # The Library writes the history of each age
        if self.cycle_count % CHRONICLE_ERA_INTERVAL == 0:
            chronicle_mod.galactic_history(self)

        # 1. AI Rival turns: each mind at its own pace, its dice locked to it (scheduler.py)
        scheduler_mod.minds(self)
        scheduler_mod.lock(self, "world", self.cycle_count)

        # 2. Ports economic drift
        for sec in self.sectors.values():
            if sec.port:
                EconomyManager.tick_port(sec.port)

        # 3. Colony yields & civilization intelligence loop
        for sec in self.sectors.values():
            for p in sec.planets:
                ColonyManager.tick_colony(p, event_bus=self.event_bus, kernel=self)

        # 4. Stock Market, population enterprises, and freight contracts
        self.market_manager.tick_market(self)

        # 5. Cognitive Metabolism & Breakthrough Tech progression
        self.research_manager.tick_cognitive_metabolism(self)

        # 6. Autonomous Survey Probe fleets sweep frontier space
        if hasattr(self, "cartography_manager"):
            self.cartography_manager.tick_survey_probes(self)

        # 7. Surface Grid District Production
        if hasattr(self, "surface_manager"):
            for sec in self.sectors.values():
                for p in sec.planets:
                    if p.owner_id is None and p.population <= 0:
                        continue  # unsettled frontier world
                    self.surface_manager.tick_surface(p)

        # 8. Astronomy Keplerian ephemeris advance
        if hasattr(self, "astronomy_manager"):
            all_planets = self.get_all_planets()
            self.astronomy_manager.tick(all_planets, self.sectors)

        # 9. Imperial Senate & Governance legislative advance
        if hasattr(self, "governance_manager"):
            senate_events = self.governance_manager.tick_senate(list(self.captains.values()))
            for ev in senate_events:
                self.action_logs.append(ev)

        # 9b. Seal the quarter's settlement block (chain-shaped record for the future mesh uplink)
        if self.cycle_count % FISCAL_QUARTER_CYCLES == 0:
            self.settlement.seal(self)

        # 10. Precursor Alchemy cooling ticks
        if hasattr(self, "alchemy_manager"):
            for cap in self.captains.values():
                self.alchemy_manager.tick_cooldown(cap)

    def get_planet(self, planet_id_or_name: Optional[str]) -> Optional[Planet]:
        """Finds planet across all sectors by ID or name."""
        if not planet_id_or_name:
            return None
        for sec in self.sectors.values():
            for p in sec.planets:
                if p.id == planet_id_or_name or p.name.lower() == str(planet_id_or_name).lower():
                    return p
        return None

    def get_all_planets(self) -> List[Planet]:
        """Returns all planetary bodies across all sectors."""
        planets = []
        for sec in self.sectors.values():
            planets.extend(sec.planets)
        return planets

    def get_planets_owned_by(self, owner_id: str) -> List[Planet]:
        """Returns all planets owned by a specific captain."""
        return [p for p in self.get_all_planets() if p.owner_id == owner_id]

    def find_path(self, start: int, goal: int) -> List[int]:
        """The geodesic between two sectors: cheapest under lane development and spacetime curvature."""
        return fibres_mod.geodesic(self, start, goal)

    def find_path_hops(self, start: int, goal: int) -> List[int]:
        """The fewest-jumps warp trajectory (ignores costs)."""
        from xylarium.kernel import topology
        return topology.path(self, start, goal)

    def get_player_view(self, player_id: str) -> Dict[str, Any]:
        """Returns clean data snapshot for client rendering."""
        captain = self.get_player(player_id)
        if not captain:
            return {}

        sector = self.sectors[captain.sector_id]
        radio_msgs = [m.to_dict() for m in self.event_bus.get_recent_radio(5)]

        # Planetary local time
        planetary_time = None
        if sector.planets:
            local_hour = (self.cycle_count * 7 + sector.id * 3) % 24
            planetary_time = {
                "local_sol_hour": f"{local_hour:02d}:00",
                "phase": "Day" if 6 <= local_hour <= 18 else "Night",
            }

        # Market & Freight snapshot
        market_info = {
            "companies": [c.to_dict() for c in self.market_manager.companies.values()],
            "open_contracts": [ct.to_dict() for ct in self.market_manager.contracts.values() if ct.status == "OPEN"],
            "active_contracts": [
                self.market_manager.contracts[cid].to_dict()
                for cid in getattr(captain, "active_contracts", [])
                if cid in self.market_manager.contracts
            ],
            "portfolio": dict(getattr(captain, "portfolio", {})),
            "controlled_companies": [
                c.ticker for c in self.market_manager.companies.values()
                if c.chairman_id == captain.id
            ],
            "fiscal_quarter": (self.cycle_count // 25) + 1,
            "cycles_to_dividend": 25 - (self.cycle_count % 25) if (self.cycle_count % 25) != 0 else 25,
            "short_positions": {k: dict(v) for k, v in getattr(captain, "short_positions", {}).items()},
            "executives": [ex.to_dict() for ex in self.market_manager.executives.values() if ex.owner_id == captain.id],
            "all_executives": [ex.to_dict() for ex in self.market_manager.executives.values()],
            "trade_council": self.market_manager.trade_council.to_dict(),
        }

        # Get port catalog if present
        port_info = None
        if sector.port:
            port_info = {
                "name": sector.port.name,
                "port_class": sector.port.port_class.value,
                "currency": sector.port.currency,
                "treasury": sector.port.treasury,
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
                    "clade": getattr(c, "clade", "BIOTIC"),
                    "rank_tier": getattr(c, "rank_tier", 1),
                    "rank_title": getattr(c, "rank_title", "Captain"),
                })

        # Player-owned colonies
        owned_planets = []
        for s in self.sectors.values():
            for p in s.planets:
                if p.owner_id == player_id:
                    p_dict = p.to_dict()
                    p_dict["sector_id"] = s.id
                    p_dict["sector_name"] = s.name
                    owned_planets.append(p_dict)

        # Player-owned trade haulers
        trade_haulers = [
            h.to_dict()
            for h in self.market_manager.trade_haulers.values()
            if h.owner_id == player_id
        ]

        warps_info = []
        for w in sector.warps:
            w_sec = self.sectors[w]
            my_planets = [p.name for p in w_sec.planets if p.owner_id == player_id]
            warps_info.append({
                "sector_id": w,
                "security": w_sec.security.value,
                "has_port": w_sec.port is not None,
                "has_planet": len(w_sec.planets) > 0,
                "has_my_planet": len(my_planets) > 0,
                "my_planet_name": my_planets[0] if my_planets else None,
                "has_anomaly": len(getattr(w_sec, "anomalies", [])) > 0,
                "kind": w_sec.kind,
                "has_belt": bool(w_sec.belts),
            })

        sector_anomalies = [
            self.research_manager.anomalies[aid].to_dict()
            for aid in getattr(sector, "anomalies", [])
            if aid in self.research_manager.anomalies
        ]

        return {
            "player": captain.to_dict(),
            "credits": captain.credits,
            "turns": captain.turns_left,
            "adjacent_sectors": list(sector.warps),
            "clade": getattr(captain, "clade", "BIOTIC"),
            "rank_tier": getattr(captain, "rank_tier", 1),
            "rank_title": getattr(captain, "rank_title", "Scrap-Apprentice"),
            "rank_role": getattr(captain, "rank_role", "Scout Salvager"),
            "full_title": getattr(captain, "full_title", f"Captain {captain.name}"),
            "background": getattr(captain, "background", None),
            "alignment": getattr(captain, "alignment", "Independent"),
            "forged_transponder": "FORGED_TRANSPONDER" in getattr(captain, "unlocked_secrets", []) or getattr(captain, "forged_transponder", False),
            "promotion_requirements": captain.get_promotion_requirements(self) if hasattr(captain, "get_promotion_requirements") else {},
            "can_promote": captain.can_promote(self)[0] if hasattr(captain, "can_promote") else False,
            "clade_matrix": CLADE_RANK_MATRIX,
            "ship_catalog": hulls.catalog(self),
            "sector": {
                "id": sector.id,
                "name": sector.name,
                "cluster_name": getattr(sector, "cluster_name", "Federation Core"),
                "security": sector.security.value,
                "warps": warps_info,
                "port": port_info,
                "planets": [p.to_dict() for p in sector.planets],
                "captains": other_captains,
                "planetary_time": planetary_time,
                "anomalies": sector_anomalies,
            },
            "owned_planets": owned_planets,
            "trade_haulers": trade_haulers,
            "vc_active_syndicate": getattr(captain, "vc_active_syndicate", None),
            "vc_debt": getattr(captain, "vc_debt", 0),
            "vc_royalty_pct": getattr(captain, "vc_royalty_pct", 0.0),
            "vc_principal_paid": getattr(captain, "vc_principal_paid", 0),
            "vc_syndicates": VC_SYNDICATES,
            "credit_rating": getattr(captain, "credit_rating", 500),
            "credit_tier": getattr(captain, "credit_tier", "SUBPRIME"),
            "experience_score": getattr(captain, "experience_score", 100),
            "faction_reputation": dict(getattr(captain, "faction_reputation", {})),
            "net_equity": self.market_manager.calculate_net_equity(captain, self) if hasattr(self, "market_manager") else captain.credits,
            "vc_terms": {
                syn_id: self.market_manager.calculate_borrowing_terms(captain, syn_id, self)
                for syn_id in VC_SYNDICATES
            } if hasattr(self, "market_manager") else {},
            "specialized_hulls": SPECIALIZED_HULLS,
            "market": market_info,
            "knowledge": knowledge_mod.stocks(self, knowledge_mod.holder_of_captain(captain)),
            "capabilities": {p: {"name": spec["name"], "domain": spec["domain"],
                                 "mastery": round(knowledge_mod.captain_mastery(self, captain, p), 3)}
                             for p, spec in PROCESSES.items()},
            "inquiry": knowledge_mod.stats(self)["focus"].get(knowledge_mod.holder_of_captain(captain)),
            "jump_cost": research_jump_cost(self, captain),
            "anomalies": sector_anomalies,
            "minted_clusters": list(self.research_manager.minted_clusters),
            "cartography": {
                "active_puzzle": (
                    self.cartography_manager.puzzles.get(
                        getattr(captain, "active_cartography_puzzle", None) or self.cartography_manager.active_puzzle_id,
                        self.cartography_manager.puzzles.get("PUZZLE-NEXUS")
                    ).to_dict() if self.cartography_manager.puzzles else None
                ),
                "fragments": list(getattr(captain, "cartography_fragments", [])),
                "fragments_count": len(getattr(captain, "cartography_fragments", [])),
                "unlocked_secrets": list(getattr(captain, "unlocked_secrets", [])),
                "all_puzzles": [
                    {
                        "puzzle_id": p.puzzle_id,
                        "name": p.name,
                        "target_title": p.target_title,
                        "target_sector_hint": p.target_sector_hint,
                        "status": p.status,
                        "progress_pct": p.get_progress_pct(),
                        "is_active": (p.puzzle_id == (getattr(captain, "active_cartography_puzzle", None) or self.cartography_manager.active_puzzle_id)),
                    }
                    for p in self.cartography_manager.puzzles.values()
                ],
                "toll_gates": [
                    tg.to_dict() for tg in self.cartography_manager.toll_gates.values()
                    if tg.owner_id == captain.id
                ],
                "all_toll_gates": [
                    tg.to_dict() for tg in self.cartography_manager.toll_gates.values()
                ],
                "survey_probes": [
                    sp.to_dict() for sp in self.cartography_manager.survey_probes.values()
                    if sp.owner_id == captain.id
                ],
                "all_survey_probes": [
                    sp.to_dict() for sp in self.cartography_manager.survey_probes.values()
                ],
                "can_buy_chit": (sector.port is not None),
                "can_salvage": (sector.security == SecurityLevel.ANARCHY),
            },
            "cognition": {
                "species": getattr(captain, "species", "human-sol"),
                "metabolism": getattr(captain, "metabolism", "biotic"),
                "books": {k: b.to_dict() for k, b in __import__("xylarium.kernel.cognition", fromlist=["SeatSurvive"]).SeatSurvive.peel_books(captain, self).items()},
                "divergence": __import__("xylarium.kernel.cognition", fromlist=["SeatSurvive"]).SeatSurvive.compute_divergence_vector(captain, self).to_dict(),
                "grown_basis": list(getattr(captain, "grown_basis", [])),
                "unlocked_secrets": list(getattr(captain, "unlocked_secrets", [])),
            },
            "ideology": self.ideology_manager.get_summary(captain.id) if hasattr(self, "ideology_manager") else {},
            "alchemy": {
                "recipes": [r.to_dict() for r in self.alchemy_manager.get_available_recipes(captain)] if hasattr(self, "alchemy_manager") else [],
                "all_recipes": [r.to_dict() for r in self.alchemy_manager.recipes.values()] if hasattr(self, "alchemy_manager") else [],
                "reactor": {
                    "installed": bool(getattr(captain, "alchemy_reactor", False)),
                    "heat": self.alchemy_manager.get_heat(captain.id) if hasattr(self, "alchemy_manager") else 0.0,
                },
            },
            "astronomy": {
                "ephemeris": [self.astronomy_manager.compute_position(p).to_dict() for p in sector.planets] if hasattr(self, "astronomy_manager") else [],
                "system_map": self.astronomy_manager.render_ascii_system_map(sector.planets) if hasattr(self, "astronomy_manager") and sector.planets else [],
            },
            "senate": {
                "offices": {k: v.to_dict() for k, v in self.governance_manager.offices.items()} if hasattr(self, "governance_manager") else {},
                "active_edicts": [e.to_dict() for e in self.governance_manager.active_edicts] if hasattr(self, "governance_manager") else [],
                "federal_treasury": getattr(self.governance_manager, "federal_treasury", 100000) if hasattr(self, "governance_manager") else 100000,
                "current_cycle": getattr(self.governance_manager, "current_cycle", 0) if hasattr(self, "governance_manager") else 0,
                "next_election_cycle": getattr(self.governance_manager, "next_election_cycle", 60) if hasattr(self, "governance_manager") else 60,
                "player_voting_weight": self.governance_manager.calculate_voting_weight(captain, self.get_planets_owned_by(captain.id)) if hasattr(self, "governance_manager") else 1.0,
            },
            "surface": {
                "sector_planets": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "owner_id": p.owner_id,
                        "garrison_troops": p.garrison_troops,
                        "yields": self.surface_manager.ensure_surface_grid(p).calculate_yields(p),
                        "map": self.surface_manager.ensure_surface_grid(p).render_map(),
                    }
                    for p in sector.planets
                ] if hasattr(self, "surface_manager") else [],
                "player_troops": getattr(captain, "troops", 0),
            },
            "fx": {
                "wallet": dict(captain.fx_wallet),
                "rates": {cur: round(self.fx_market.rate(cur), 4) for cur in self.fx_market.pools},
                "drift": {cur: round(self.fx_market.price_level_drift(cur), 3) for cur in self.fx_market.pools},
                "local_currency": self._local_currency(self.sectors[captain.sector_id]),
            },
            "cosmos": self._cosmos_view(captain),
            "mode": captain.command_mode,
            "banking": self.banking.summary(self),
            "lineage": dict(self.lineage) if lineage_mod.bound(self, captain.id) else None,
            "space": {
                "kind": self.sectors[captain.sector_id].kind,
                "star_type": self.sectors[captain.sector_id].star_type,
                "protected": self.sectors[captain.sector_id].is_protected_space,
                "belts": [dict(b) for b in self.sectors[captain.sector_id].belts if b["id"] in captain.scanned_belts],
                "unscanned_belts": sum(1 for b in self.sectors[captain.sector_id].belts if b["id"] not in captain.scanned_belts),
                "debris_fields": len(self.sectors[captain.sector_id].debris),
                "sentries": dict(self.sectors[captain.sector_id].sentries),
                "mining_yield": NullSpaceManager.mining_yield(captain),
            },
            "experience_domains": dict(getattr(captain, "experience_domains", {})),
            "hunger": getattr(captain, "hunger", 0),
            "federal": {
                "reserve": self.federal_reserve.treasury,
                "insured": self.federal_reserve.is_insured(captain, self.cycle_count),
                "insurance_paid_through": getattr(captain, "insurance_paid_through", 0),
                "premium": self.federal_reserve.premium_for(captain),
            },
            "phylogeny": {
                "current_node": self.phylogeny_manager.get_node(captain.phylogeny_node_id).to_dict() if getattr(captain, "phylogeny_node_id", None) in self.phylogeny_manager.nodes else None,
                "affinities": self.phylogeny_manager.compute_branch_affinities(captain) if hasattr(self, "phylogeny_manager") else {},
                "ascension_eval": self.phylogeny_manager.evaluate_ascension(captain, self) if hasattr(self, "phylogeny_manager") else {},
                "cochain_flux": getattr(captain, "cochain_flux", {}),
                "unlocked_nodes": list(getattr(captain, "unlocked_phylogeny_nodes", [])),
                "chimeric_grafts": list(getattr(captain, "chimeric_grafts", [])),
                "active_canopy_override": getattr(captain, "active_canopy_override", None),
                "ascii_cladogram": self.phylogeny_manager.render_ascii_cladogram(captain) if hasattr(self, "phylogeny_manager") else "",
            },
            "radio": radio_msgs,
            "logs": list(self.action_logs)[-4:],
            "cycle": self.cycle_count,
        }

    def get_trade_routes(
        self,
        player_id: str,
        mode: str = "circular",
        max_hops: int = 4,
        category: Optional[str] = None,
        commodity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculates commercial arbitrage routes and supply corridors for player."""
        captain = self.get_player(player_id)
        if not captain:
            return {"success": False, "error": "Captain not found"}

        cargo_cap = captain.ship.cargo.capacity
        if mode == "circular":
            routes = TradeRouteOptimizer.find_circular_arbitrage(
                self,
                cargo_capacity=cargo_cap,
                max_hops=max_hops,
                category=category,
                commodity=commodity,
            )
            return {
                "success": True,
                "mode": "circular",
                "routes": [r.to_dict() for r in routes]
            }
        elif mode == "local":
            ops = TradeRouteOptimizer.find_local_opportunities(
                self,
                captain.sector_id,
                cargo_capacity=cargo_cap,
                max_hops=max_hops,
                category=category,
                commodity=commodity,
            )
            return {
                "success": True,
                "mode": "local",
                "opportunities": [o.to_dict() for o in ops]
            }
        elif mode == "colony":
            runs = TradeRouteOptimizer.find_colony_supply_routes(self, captain, max_hops=8)
            return {
                "success": True,
                "mode": "colony",
                "supply_runs": [r.to_dict() for r in runs]
            }
        elif mode == "spreads":
            spreads = TradeRouteOptimizer.get_galactic_spreads(self, category=category)
            return {
                "success": True,
                "mode": "spreads",
                "spreads": [s.to_dict() for s in spreads]
            }
        return {"success": False, "error": f"Unknown mode: {mode}"}


# ---------------------------------------------------------------------- the kernel's own seasonal steps
def _each_system(kernel: "GameKernel") -> None:
    for sec in kernel.sectors.values():
        physics_mod.ensure_system(sec)        # newly charted systems (ghost sectors, frontier clusters) get physics


def _reanchor(kernel: "GameKernel") -> None:
    from xylarium.config import CROSS_REANCHOR_RATE
    kernel.fx_market.reanchor_cross(CROSS_REANCHOR_RATE)


for _sub in (
    Subsystem("monetary_policy", season=lambda k: k.monetary_policy.update(k) and None),
    Subsystem("federal_reserve", season=lambda k: k.federal_reserve.fiscal_quarter(k)),
    Subsystem("banking", season=lambda k: k.banking.quarter(k)),
    Subsystem("fx_reanchor", season=lambda k: _reanchor(k)),
    Subsystem("alignment", season=lambda k: alignment_mod.quarterly(k) and None),
    Subsystem("natives", season=lambda k: NativeManager.tick(k) and None),
    Subsystem("sieges", season=lambda k: k._tick_sieges() and None),
    Subsystem("physics", season=lambda k: _each_system(k)),
):
    subsystem.register(_sub)
