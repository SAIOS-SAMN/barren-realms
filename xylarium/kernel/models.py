"""
Data models and Enums for the Xylarium core kernel.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time
import math
from xylarium.config import CLADE_RANK_MATRIX, RANK_PROMOTION_THRESHOLDS


def _deep_copy(value: Any) -> Any:
    """JSON-shaped deep copy (dicts/lists of scalars) for nested records such as native societies."""
    if isinstance(value, dict):
        return {k: _deep_copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_deep_copy(v) for v in value]
    return value


class CommodityType(str, Enum):
    ORE = "ORE"
    ORGANICS = "ORGANICS"
    EQUIPMENT = "EQUIPMENT"


class SecurityLevel(str, Enum):
    FEDERATION = "FEDERATION"  # Safe, Navy patrols, no combat allowed
    BORDERLAND = "BORDERLAND"  # Contested outer rim, occasional skirmishes
    ANARCHY = "ANARCHY"        # Deep void, lawless, high hazard and reward


class PortClass(str, Enum):
    """
    Classic TradeWars Port Classes:
    B = Buys, S = Sells for (Ore, Organics, Equipment)
    """
    CLASS_1_BBS = "1 (BBS)"  # Buy Ore, Buy Organics, Sell Equipment
    CLASS_2_BSB = "2 (BSB)"  # Buy Ore, Sell Organics, Buy Equipment
    CLASS_3_SBB = "3 (SBB)"  # Sell Ore, Buy Organics, Buy Equipment
    CLASS_4_SSB = "4 (SSB)"  # Sell Ore, Sell Organics, Buy Equipment
    CLASS_5_SBS = "5 (SBS)"  # Sell Ore, Buy Organics, Sell Equipment
    CLASS_6_BSS = "6 (BSS)"  # Buy Ore, Sell Organics, Sell Equipment
    CLASS_7_SSS = "7 (SSS)"  # Sells all three
    CLASS_8_BBB = "8 (BBB)"  # Buys all three
    STARDOCK = "0 (DOCK)"    # Federation Stardock (Buy/Sell all + Shipyard)


class ActionType(str, Enum):
    MOVE = "MOVE"
    TRADE = "TRADE"
    PLANET_CLAIM = "PLANET_CLAIM"
    PLANET_INVEST = "PLANET_INVEST"
    PLANET_TAX = "PLANET_TAX"
    PLANET_BUILD_SHIELD = "PLANET_BUILD_SHIELD"
    PLANET_RECRUIT_FIGHTERS = "PLANET_RECRUIT_FIGHTERS"
    PLANET_UPGRADE_CITADEL = "PLANET_UPGRADE_CITADEL"
    PLANET_CARGO_TRANSFER = "PLANET_CARGO_TRANSFER"
    ATTACK_SHIP = "ATTACK_SHIP"
    ATTACK_PLANET = "ATTACK_PLANET"
    SHIPYARD_PURCHASE = "SHIPYARD_PURCHASE"
    SCAN = "SCAN"
    RADIO_BROADCAST = "RADIO_BROADCAST"
    OPTIMIZE_ROUTES = "OPTIMIZE_ROUTES"
    BANK_TRANSACTION = "BANK_TRANSACTION"
    REST = "REST"
    TACTICAL_COMBAT = "TACTICAL_COMBAT"
    COVERT_OP = "COVERT_OP"
    RECRUIT_OPERATIVES = "RECRUIT_OPERATIVES"
    STATION_SECURITY = "STATION_SECURITY"
    PLANET_CIVIC_CONTRIBUTE = "PLANET_CIVIC_CONTRIBUTE"
    PLANET_ELEMENT_TRANSFER = "PLANET_ELEMENT_TRANSFER"
    STOCK_BUY = "STOCK_BUY"
    STOCK_SELL = "STOCK_SELL"
    COMPANY_IPO = "COMPANY_IPO"
    FREIGHT_ACCEPT = "FREIGHT_ACCEPT"
    FREIGHT_DELIVER = "FREIGHT_DELIVER"
    CORPORATE_TAKEOVER = "CORPORATE_TAKEOVER"
    BOARD_VOTE = "BOARD_VOTE"
    POISON_PILL = "POISON_PILL"
    PROXY_FIGHT = "PROXY_FIGHT"
    STOCK_SHORT = "STOCK_SHORT"
    STOCK_COVER = "STOCK_COVER"
    SET_TARIFF = "SET_TARIFF"
    EXECUTIVE_HIRE = "EXECUTIVE_HIRE"
    EXECUTIVE_MOVE = "EXECUTIVE_MOVE"
    MARKETING_CAMPAIGN = "MARKETING_CAMPAIGN"
    LOBBY_CONTRIBUTE = "LOBBY_CONTRIBUTE"
    COUNCIL_VOTE = "COUNCIL_VOTE"
    HAULER_COMMISSION = "HAULER_COMMISSION"
    HAULER_ASSIGN_ROUTE = "HAULER_ASSIGN_ROUTE"
    HAULER_DECOMMISSION = "HAULER_DECOMMISSION"
    EMPIRE_OVERVIEW = "EMPIRE_OVERVIEW"
    RESEARCH_SELECT = "RESEARCH_SELECT"
    ANOMALY_INVESTIGATE = "ANOMALY_INVESTIGATE"
    JUMP_WARP = "JUMP_WARP"
    VC_APPLY = "VC_APPLY"
    VC_REPAY = "VC_REPAY"
    FLEET_ASSIGN_ESCORT = "FLEET_ASSIGN_ESCORT"
    FLEET_RECALL = "FLEET_RECALL"
    CARTOGRAPHY_SCAN = "CARTOGRAPHY_SCAN"
    CARTOGRAPHY_ROTATE = "CARTOGRAPHY_ROTATE"
    CARTOGRAPHY_BRIDGE = "CARTOGRAPHY_BRIDGE"
    CARTOGRAPHY_SOLVE = "CARTOGRAPHY_SOLVE"
    CARTOGRAPHY_BUY_CHIT = "CARTOGRAPHY_BUY_CHIT"
    CARTOGRAPHY_SALVAGE = "CARTOGRAPHY_SALVAGE"
    CARTOGRAPHY_SELECT = "CARTOGRAPHY_SELECT"
    TOLL_GATE_DEPLOY = "TOLL_GATE_DEPLOY"
    TOLL_GATE_SET_FEE = "TOLL_GATE_SET_FEE"
    CARTOGRAPHY_FORGE_CHIT = "CARTOGRAPHY_FORGE_CHIT"
    CARTOGRAPHY_CATALYZE = "CARTOGRAPHY_CATALYZE"
    SURVEY_PROBE_LAUNCH = "SURVEY_PROBE_LAUNCH"
    SURVEY_PROBE_RECALL = "SURVEY_PROBE_RECALL"
    COGNITIVE_AUTOMATE = "COGNITIVE_AUTOMATE"

    # [1] Ideology & Diplomacy Actions
    IDEOLOGY_TREATY_PROPOSE = "IDEOLOGY_TREATY_PROPOSE"
    IDEOLOGY_TREATY_SIGN = "IDEOLOGY_TREATY_SIGN"
    IDEOLOGY_AID_DISPATCH = "IDEOLOGY_AID_DISPATCH"

    # [2] Precursor Alchemy & Transmutation Actions
    ALCHEMY_TRANSMUTE = "ALCHEMY_TRANSMUTE"

    # [4] Imperial Senate & Governance Actions
    SENATE_CAMPAIGN = "SENATE_CAMPAIGN"
    SENATE_VOTE = "SENATE_VOTE"
    SENATE_ENACT_EDICT = "SENATE_ENACT_EDICT"

    # [5] Surface Grid & Planetary Invasion Actions
    SURFACE_BUILD_DISTRICT = "SURFACE_BUILD_DISTRICT"
    SURFACE_DEMOLISH_DISTRICT = "SURFACE_DEMOLISH_DISTRICT"
    SURFACE_RECRUIT_TROOPS = "SURFACE_RECRUIT_TROOPS"
    SURFACE_INVADE = "SURFACE_INVADE"

    # [6] Rank & Clade Progression Actions
    RANK_PROMOTE = "RANK_PROMOTE"
    PHYLOGENY_ASCEND = "PHYLOGENY_ASCEND"
    CANOPY_OVERRIDE = "CANOPY_OVERRIDE"

    # [7] Null space, industry & monetary actions
    FX_EXCHANGE = "FX_EXCHANGE"
    SCAN_SPACE = "SCAN_SPACE"
    MINE_ASTEROIDS = "MINE_ASTEROIDS"
    SALVAGE_DEBRIS = "SALVAGE_DEBRIS"
    DEPLOY_SENTRIES = "DEPLOY_SENTRIES"
    RECALL_SENTRIES = "RECALL_SENTRIES"
    SURVEY_RUINS = "SURVEY_RUINS"
    SHORE_LEAVE = "SHORE_LEAVE"
    POPULATION_POLICY = "POPULATION_POLICY"
    DRIVE_REFIT = "DRIVE_REFIT"
    BUDGET_SET = "BUDGET_SET"
    GOVERNMENT_GRANT = "GOVERNMENT_GRANT"
    STATION_BUILD = "STATION_BUILD"
    SHIP_DESIGN = "SHIP_DESIGN"
    EXCAVATE = "EXCAVATE"
    SELL_ARTIFACT = "SELL_ARTIFACT"
    STUDY_ARTIFACT = "STUDY_ARTIFACT"

    # [8] Locals, the Prime Directive & the Galactic Library
    RETIRE_LINEAGE = "RETIRE_LINEAGE"
    NATIVE_INTERACT = "NATIVE_INTERACT"
    LIBRARY_BROWSE = "LIBRARY_BROWSE"
    CHRONICLE_WRITE = "CHRONICLE_WRITE"


class AIPersonality(str, Enum):
    TRADER = "trader"
    PIRATE = "pirate"
    INDUSTRIALIST = "industrialist"
    MERCENARY = "mercenary"
    IMPERIAL = "imperial"
    CRUSADER = "crusader"


@dataclass
class CargoHold:
    ore: int = 0
    organics: int = 0
    equipment: int = 0
    elements: Dict[str, int] = field(default_factory=dict)
    capacity: int = 30
    cost_basis: Dict[str, float] = field(default_factory=lambda: {"ore": 0.0, "organics": 0.0, "equipment": 0.0})
    # Units reserved by in-transit freight contracts (canonical commodity key -> units).
    # Bonded units may only leave the hold through contract delivery or forfeiture.
    bonded: Dict[str, int] = field(default_factory=dict)

    @staticmethod
    def bond_key(commodity: str) -> str:
        c = commodity.upper()
        return c if c in ("ORE", "ORGANICS", "EQUIPMENT") else commodity

    def held(self, commodity: str) -> int:
        attr = commodity.lower()
        if attr in ("ore", "organics", "equipment"):
            return int(getattr(self, attr))
        if commodity in self.elements:
            return int(self.elements[commodity])
        for k, v in self.elements.items():
            if k.lower() == attr:
                return int(v)
        return 0

    def bonded_units(self, commodity: str) -> int:
        key = self.bond_key(commodity)
        if key in self.bonded:
            return self.bonded[key]
        return sum(v for k, v in self.bonded.items() if k.lower() == commodity.lower())

    def unbonded(self, commodity: str) -> int:
        """Units of a commodity free to sell, transfer, consume, or jettison."""
        return max(0, self.held(commodity) - self.bonded_units(commodity))

    def bond(self, commodity: str, amount: int) -> None:
        key = self.bond_key(commodity)
        self.bonded[key] = self.bonded.get(key, 0) + amount

    def release_bond(self, commodity: str, amount: int) -> None:
        key = self.bond_key(commodity)
        remaining = self.bonded.get(key, 0) - amount
        if remaining > 0:
            self.bonded[key] = remaining
        else:
            self.bonded.pop(key, None)

    @property
    def total_used(self) -> int:
        """Total raw item count across all commodities and elements."""
        return self.ore + self.organics + self.equipment + sum(self.elements.values())

    @property
    def holds_used(self) -> float:
        """Effective cargo holds consumed based on bulk density stack multipliers."""
        from xylarium.config import get_commodity_stack_multiplier
        used = 0.0
        if self.ore > 0:
            used += self.ore / get_commodity_stack_multiplier("ORE")
        if self.organics > 0:
            used += self.organics / get_commodity_stack_multiplier("ORGANICS")
        if self.equipment > 0:
            used += self.equipment / get_commodity_stack_multiplier("EQUIPMENT")
        for comm, qty in self.elements.items():
            if qty > 0:
                used += qty / get_commodity_stack_multiplier(comm)
        return used

    @property
    def free_holds(self) -> float:
        """Remaining unallocated cargo holds on the vessel."""
        return max(0.0, float(self.capacity) - self.holds_used)

    @property
    def available_space(self) -> int:
        """Returns floor of remaining unallocated cargo holds."""
        return max(0, int(math.floor(self.free_holds + 1e-6)))

    def available_units_for(self, commodity: str) -> int:
        """Returns maximum units of a specific commodity that can fit into remaining cargo space."""
        from xylarium.config import get_commodity_stack_multiplier
        mult = get_commodity_stack_multiplier(commodity)
        return int(math.floor((self.free_holds + 1e-6) * mult))

    def can_fit(self, commodity: str, amount: int) -> bool:
        """Checks if amount units of commodity can fit into available holds."""
        return self.available_units_for(commodity) >= amount

    def stow(self, commodity: str, amount: int) -> int:
        """Adds as many units as fit (up to amount) and returns the quantity actually stowed."""
        qty = max(0, min(amount, self.available_units_for(commodity)))
        if qty:
            attr = commodity.lower()
            if attr in ("ore", "organics", "equipment"):
                setattr(self, attr, getattr(self, attr) + qty)
            else:
                self.elements[commodity] = self.elements.get(commodity, 0) + qty
        return qty

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ore": self.ore,
            "organics": self.organics,
            "equipment": self.equipment,
            "elements": dict(self.elements),
            "capacity": self.capacity,
            "cost_basis": {k: float(v) for k, v in self.cost_basis.items()},
            "used": self.total_used,
            "holds_used": round(self.holds_used, 2),
            "available": self.available_space,
            "free_holds": round(self.free_holds, 2),
            "bonded": dict(self.bonded),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CargoHold":
        cb_raw = data.get("cost_basis", {})
        default_cb = {"ore": 0.0, "organics": 0.0, "equipment": 0.0}
        for k, v in cb_raw.items():
            default_cb[k] = float(v)
        return cls(
            ore=data.get("ore", 0),
            organics=data.get("organics", 0),
            equipment=data.get("equipment", 0),
            elements=dict(data.get("elements", {})),
            capacity=data.get("capacity", 30),
            cost_basis=default_cb,
            bonded={k: int(v) for k, v in data.get("bonded", {}).items()},
        )


@dataclass
class Port:
    sector_id: int
    name: str
    port_class: PortClass
    stock: Dict[str, int]         # "ORE", "ORGANICS", "EQUIPMENT"
    max_stock: Dict[str, int]
    buys: Dict[str, bool]         # True if port buys this commodity from captain
    sells: Dict[str, bool]        # True if port sells this commodity to captain
    # Ports are real balance sheets: they pay for what they buy out of this treasury
    treasury: int = 0
    currency: str = "SOL"         # Settlement currency of the port's region
    remoteness: float = 0         # Fibre distance from Sol (developed lanes count less); drives the price gradient
    faction_id: Optional[str] = None  # Great power operating this starport (Imperial ports gouge xenos)
    consumed: Dict[str, int] = field(default_factory=dict)  # goods consumed this quarter (sold on to the region)
    base_buys: Dict[str, bool] = field(default_factory=dict)  # the charter's buy list (restocking adds to it)
    regional_income: float = 0.0          # smoothed quarterly retail revenue from the region's households
    leisure: Dict[str, Any] = field(default_factory=dict)   # orbital leisure station and tourist traffic (tourism.py)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_id": self.sector_id,
            "name": self.name,
            "port_class": self.port_class.value,
            "stock": dict(self.stock),
            "max_stock": dict(self.max_stock),
            "buys": dict(self.buys),
            "sells": dict(self.sells),
            "treasury": self.treasury,
            "currency": self.currency,
            "remoteness": self.remoteness,
            "faction_id": self.faction_id,
            "regional_income": self.regional_income,
            "base_buys": dict(self.base_buys),
            "leisure": dict(self.leisure),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Port":
        return cls(
            sector_id=data["sector_id"],
            name=data["name"],
            port_class=PortClass(data["port_class"]),
            stock=dict(data["stock"]),
            max_stock=dict(data["max_stock"]),
            buys=dict(data["buys"]),
            sells=dict(data["sells"]),
            treasury=int(data.get("treasury", 0)),
            currency=data.get("currency", "SOL"),
            remoteness=float(data.get("remoteness", 0)),
            faction_id=data.get("faction_id"),
            regional_income=float(data.get("regional_income", 0.0)),
            base_buys=dict(data.get("base_buys", {})),
            leisure=dict(data.get("leisure", {})),
        )


@dataclass
class Planet:
    id: str
    sector_id: int
    name: str
    owner_id: Optional[str] = None
    population: int = 500
    shields: int = 100
    max_shields: int = 200
    fighters: int = 20
    citadel_level: int = 0
    treasury: int = 500
    ore_silo: int = 50
    organics_silo: int = 50
    morale: int = 100
    security_operatives: int = 0
    security_lockout: int = 0
    civilization: Optional[Any] = None
    element_deposits: Dict[str, int] = field(default_factory=dict)
    element_reserves: Dict[str, int] = field(default_factory=dict)
    marketing_hub: bool = False
    sector_tariff_pct: int = 0
    technologies: List[str] = field(default_factory=list)
    grown_basis: List[Dict[str, Any]] = field(default_factory=list)
    orbital_radius: float = 1.0
    orbital_period: int = 36
    orbital_angle: float = 0.0
    garrison_troops: int = 20
    surface_grid: Optional[Dict[str, Any]] = None
    planet_type: str = "TERRESTRIAL"
    currency: str = "SOL"         # Vault currency (the region's money)
    habitability: float = 1.0     # How well the governing population's biology suits this world
    ruins: Optional[Dict[str, Any]] = None  # Archaeological site left by a dead civilization
    last_levy_cycle: int = -10 ** 9          # Governor's last sovereign levy (once per fiscal quarter)
    natives: Optional[Dict[str, Any]] = None # A non-spacefaring local society living on this world
    faction_id: Optional[str] = None         # Great power this world belongs to (IMPERIUM, ZEALOT)
    siege: Optional[Dict[str, Any]] = None   # Ongoing orbital siege record (for the annals)
    tithe_manifest: Dict[str, int] = field(default_factory=dict)  # Imperial tithe awaiting a Goliath hauler
    habitats: int = 0                        # Sub-surface habitats dug by the colony council (housing tech)
    body: Optional[Dict[str, Any]] = None    # exact orbit & body: q (a = q^2 AU), radius, mass, day, tilt (physics.py)
    moon_of: Optional[str] = None            # a moon orbits this planet rather than the star
    works_ready_cycle: int = 0               # The council's current construction completes at this cycle
    harvest_carry: int = 0                   # thousandths of a unit of harvest carried between cycles
    growth_carry: Optional[str] = None       # exact fractional births carried between cycles (biosphere.py)
    household_purse: int = 0                 # What the world's households hold to spend at the starports
    growth_policy: Optional[str] = None      # "expand" (settler fleets) or "steady" (population controls)
    last_daughter_quarter: int = -10 ** 6    # Last fiscal quarter a settler fleet sailed from here
    metropole_id: Optional[str] = None       # The world whose settlers founded this one
    society: Dict[str, Any] = field(default_factory=dict)   # fertility, natal policy, luxury, stresses (fertility.py)
    diaspora_escrow: int = 0                 # Escrow fund dedicated to commissioning expeditionary colony ship
    crowded_cycles: int = 0                  # Consecutive cycles crowded at >= 95% housing cap with food stable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sector_id": self.sector_id,
            "name": self.name,
            "owner_id": self.owner_id,
            "population": self.population,
            "shields": self.shields,
            "max_shields": self.max_shields,
            "fighters": self.fighters,
            "citadel_level": self.citadel_level,
            "citadel_tier": self.citadel_level,
            "treasury": self.treasury,
            "ore_silo": self.ore_silo,
            "organics_silo": self.organics_silo,
            "morale": self.morale,
            "security_operatives": self.security_operatives,
            "security_lockout": self.security_lockout,
            "civilization": self.civilization.to_dict() if self.civilization else None,
            "element_deposits": dict(self.element_deposits),
            "element_reserves": dict(self.element_reserves),
            "marketing_hub": self.marketing_hub,
            "sector_tariff_pct": self.sector_tariff_pct,
            "technologies": list(self.technologies),
            "grown_basis": [dict(b) for b in self.grown_basis],
            "orbital_radius": self.orbital_radius,
            "orbital_period": self.orbital_period,
            "orbital_angle": self.orbital_angle,
            "garrison_troops": self.garrison_troops,
            "surface_grid": dict(self.surface_grid) if self.surface_grid else None,
            "planet_type": self.planet_type,
            "currency": self.currency,
            "habitability": self.habitability,
            "ruins": dict(self.ruins, strata=[dict(x) for x in self.ruins["strata"]]) if self.ruins else None,
            "last_levy_cycle": self.last_levy_cycle,
            "natives": _deep_copy(self.natives),
            "faction_id": self.faction_id,
            "siege": dict(self.siege) if self.siege else None,
            "tithe_manifest": dict(self.tithe_manifest),
            "habitats": self.habitats,
            "household_purse": self.household_purse,
            "growth_carry": self.growth_carry,
            "harvest_carry": self.harvest_carry,
            "works_ready_cycle": self.works_ready_cycle,
            "body": dict(self.body) if self.body else None,
            "moon_of": self.moon_of,
            "growth_policy": self.growth_policy,
            "last_daughter_quarter": self.last_daughter_quarter,
            "metropole_id": self.metropole_id,
            "society": _deep_copy(self.society),
            "diaspora_escrow": self.diaspora_escrow,
            "crowded_cycles": self.crowded_cycles,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Planet":
        civ = None
        if data.get("civilization"):
            from xylarium.kernel.civilization import Civilization
            civ = Civilization.from_dict(data["civilization"])
        return cls(
            id=data["id"],
            sector_id=data["sector_id"],
            name=data["name"],
            owner_id=data.get("owner_id"),
            population=data.get("population", 500),
            shields=data.get("shields", 100),
            max_shields=data.get("max_shields", 200),
            fighters=data.get("fighters", 20),
            citadel_level=data.get("citadel_level", 0),
            treasury=data.get("treasury", 500),
            ore_silo=data.get("ore_silo", 50),
            organics_silo=data.get("organics_silo", 50),
            morale=data.get("morale", 100),
            security_operatives=data.get("security_operatives", 0),
            security_lockout=data.get("security_lockout", 0),
            civilization=civ,
            element_deposits=dict(data.get("element_deposits", {})),
            element_reserves=dict(data.get("element_reserves", {})),
            marketing_hub=data.get("marketing_hub", False),
            sector_tariff_pct=data.get("sector_tariff_pct", 0),
            technologies=list(data.get("technologies", [])),
            grown_basis=list(data.get("grown_basis", [])),
            orbital_radius=float(data.get("orbital_radius", 1.0)),
            orbital_period=int(data.get("orbital_period", 36)),
            orbital_angle=float(data.get("orbital_angle", 0.0)),
            garrison_troops=int(data.get("garrison_troops", 20)),
            surface_grid=data.get("surface_grid"),
            planet_type=data.get("planet_type", "TERRESTRIAL"),
            currency=data.get("currency", "SOL"),
            habitability=float(data.get("habitability", 1.0)),
            ruins=data.get("ruins"),
            last_levy_cycle=int(data.get("last_levy_cycle", -10 ** 9)),
            natives=_deep_copy(data.get("natives")),
            faction_id=data.get("faction_id"),
            siege=data.get("siege"),
            tithe_manifest={k: int(v) for k, v in data.get("tithe_manifest", {}).items()},
            habitats=int(data.get("habitats", 0)),
            household_purse=int(data.get("household_purse", 0)),
            growth_carry=data.get("growth_carry"),
            harvest_carry=int(data.get("harvest_carry", 0)),
            works_ready_cycle=int(data.get("works_ready_cycle", 0)),
            body=dict(data["body"]) if data.get("body") else None,
            moon_of=data.get("moon_of"),
            growth_policy=data.get("growth_policy"),
            last_daughter_quarter=int(data.get("last_daughter_quarter", -10 ** 6)),
            metropole_id=data.get("metropole_id"),
            society=_deep_copy(data.get("society")) or {},
            diaspora_escrow=int(data.get("diaspora_escrow", 0)),
            crowded_cycles=int(data.get("crowded_cycles", 0)),
        )


@dataclass
class Ship:
    ship_type: str
    cargo: CargoHold
    shields: int
    max_shields: int
    fighters: int
    fuel: int = 0            # reaction mass in the drive bunker (not in the cargo holds): H, or He-3 for a He-3 drive
    drive: str = "H"         # "H" fusion torch, "HE3" fusion drive, "WARP" stabilizer (propulsion.py)
    core_wear: int = 0       # jumps on the installed warp core
    design: Optional[Dict[str, Any]] = None   # the hull entry of a drawn design this ship was built to (hulls.py)
    has_cryo_containment: bool = False  # Stasis Pod cryogenic containment reducing transit spoilage by 80%

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ship_type": self.ship_type,
            "cargo": self.cargo.to_dict(),
            "shields": self.shields,
            "max_shields": self.max_shields,
            "fighters": self.fighters,
            "fuel": self.fuel,
            "drive": self.drive,
            "core_wear": self.core_wear,
            "design": dict(self.design) if self.design else None,
            "has_cryo_containment": self.has_cryo_containment,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ship":
        return cls(
            ship_type=data["ship_type"],
            cargo=CargoHold.from_dict(data["cargo"]),
            fuel=int(data.get("fuel", 0)),
            drive=data.get("drive", "H"),
            core_wear=int(data.get("core_wear", 0)),
            design=data.get("design"),
            shields=data["shields"],
            max_shields=data["max_shields"],
            fighters=data["fighters"],
            has_cryo_containment=bool(data.get("has_cryo_containment", False)),
        )


@dataclass
class TradeHauler:
    id: str
    owner_id: str
    name: str
    sector_id: int
    hull_class: str = "BULK_FREIGHTER"  # "STANDARD", "CRYO_TANKER", "BULK_FREIGHTER", "BIOSPHERE_VESSEL", "QUANTUM_SKIFF"
    status: str = "IDLE"  # "IDLE", "IN_TRANSIT", "LOADING", "UNLOADING", "RETREAT", "COMBAT", "UNDER_ATTACK"
    capacity: int = 50
    origin_sector: int = 1
    dest_sector: int = 30
    commodity_outbound: str = "EQUIPMENT"
    commodity_return: str = "ORGANICS"
    cargo: Dict[str, int] = field(default_factory=dict)
    escort_fighters: int = 0
    wear_and_tear: int = 0
    current_path: List[int] = field(default_factory=list)
    multi_legs: List[Dict[str, Any]] = field(default_factory=list)
    lifetime_profit: int = 0
    trips_completed: int = 0
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "sector_id": self.sector_id,
            "hull_class": self.hull_class,
            "status": self.status,
            "capacity": self.capacity,
            "origin_sector": self.origin_sector,
            "dest_sector": self.dest_sector,
            "commodity_outbound": self.commodity_outbound,
            "commodity_return": self.commodity_return,
            "cargo": dict(self.cargo),
            "escort_fighters": self.escort_fighters,
            "wear_and_tear": self.wear_and_tear,
            "current_path": list(self.current_path),
            "multi_legs": [dict(leg) for leg in self.multi_legs],
            "lifetime_profit": self.lifetime_profit,
            "trips_completed": self.trips_completed,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradeHauler":
        return cls(
            id=data["id"],
            owner_id=data["owner_id"],
            name=data.get("name", "Merchant Hauler"),
            sector_id=data.get("sector_id", 1),
            hull_class=data.get("hull_class", "BULK_FREIGHTER"),
            status=data.get("status", "IDLE"),
            capacity=data.get("capacity", 50),
            origin_sector=data.get("origin_sector", 1),
            dest_sector=data.get("dest_sector", 30),
            commodity_outbound=data.get("commodity_outbound", "EQUIPMENT"),
            commodity_return=data.get("commodity_return", "ORGANICS"),
            cargo=dict(data.get("cargo", {})),
            escort_fighters=data.get("escort_fighters", 0),
            wear_and_tear=data.get("wear_and_tear", 0),
            current_path=list(data.get("current_path", [])),
            multi_legs=[dict(leg) for leg in data.get("multi_legs", [])],
            lifetime_profit=data.get("lifetime_profit", 0),
            trips_completed=data.get("trips_completed", 0),
            active=data.get("active", True),
        )


@dataclass
class TollGate:
    id: str
    owner_id: str
    sector_a: int
    sector_b: int
    toll_fee: int = 500
    total_revenue: int = 0
    total_transits: int = 0
    drones: int = 25
    active: bool = True
    created_cycle: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "sector_a": self.sector_a,
            "sector_b": self.sector_b,
            "toll_fee": self.toll_fee,
            "total_revenue": self.total_revenue,
            "total_transits": self.total_transits,
            "drones": self.drones,
            "active": self.active,
            "created_cycle": self.created_cycle,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TollGate":
        return cls(
            id=data["id"],
            owner_id=data["owner_id"],
            sector_a=data["sector_a"],
            sector_b=data["sector_b"],
            toll_fee=data.get("toll_fee", 500),
            total_revenue=data.get("total_revenue", 0),
            total_transits=data.get("total_transits", 0),
            drones=data.get("drones", 25),
            active=data.get("active", True),
            created_cycle=data.get("created_cycle", 1),
        )


@dataclass
class SurveyProbe:
    id: str
    owner_id: str
    current_sector: int
    target_sector: int
    shields: int = 50
    max_shields: int = 50
    status: str = "SCANNING"
    fragments_found: int = 0
    sectors_surveyed: List[int] = field(default_factory=list)
    launched_cycle: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "current_sector": self.current_sector,
            "target_sector": self.target_sector,
            "shields": self.shields,
            "max_shields": self.max_shields,
            "status": self.status,
            "fragments_found": self.fragments_found,
            "sectors_surveyed": list(self.sectors_surveyed),
            "launched_cycle": self.launched_cycle,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SurveyProbe":
        return cls(
            id=data["id"],
            owner_id=data["owner_id"],
            current_sector=data["current_sector"],
            target_sector=data.get("target_sector", data["current_sector"]),
            shields=data.get("shields", 50),
            max_shields=data.get("max_shields", 50),
            status=data.get("status", "SCANNING"),
            fragments_found=data.get("fragments_found", 0),
            sectors_surveyed=list(data.get("sectors_surveyed", [])),
            launched_cycle=data.get("launched_cycle", 1),
        )


@dataclass
class Captain:
    id: str
    name: str
    is_ai: bool
    personality: Optional[AIPersonality]
    ship: Ship
    credits: int
    sector_id: int
    turns_left: int
    home_sector: int = 1
    score: int = 0
    hunt_target_sector: Optional[int] = None
    debt: int = 0
    operatives: int = 0
    bounty: int = 0
    bounty_placed_by: Optional[str] = None
    embargoed_by: List[str] = field(default_factory=list)
    portfolio: Dict[str, int] = field(default_factory=dict)
    active_contracts: List[str] = field(default_factory=list)
    short_positions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    sales_executives: List[str] = field(default_factory=list)
    trade_haulers: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    active_research: Optional[str] = None
    research_progress: int = 0
    vc_active_syndicate: Optional[str] = None
    vc_debt: int = 0
    margin_loans: Dict[str, int] = field(default_factory=dict)   # ticker -> SOL owed to that company's margin desk
    frozen_by: List[str] = field(default_factory=list)   # courts that froze this captain's trade (unpaid judgments)
    charter: Optional[str] = None                        # VIP charter aboard (tourism.py)
    vc_royalty_pct: float = 0.0
    vc_principal_paid: int = 0
    cartography_fragments: List[Dict[str, Any]] = field(default_factory=list)
    unlocked_secrets: List[str] = field(default_factory=list)
    active_cartography_puzzle: Optional[str] = None
    toll_gates: List[str] = field(default_factory=list)
    survey_probes: List[str] = field(default_factory=list)
    species: str = "human-sol"
    metabolism: str = "biotic"
    clade: str = "BIOTIC"
    rank_tier: int = 1
    background: Optional[str] = None
    alignment: str = "Independent"
    forged_transponder: bool = False
    grown_basis: List[Dict[str, Any]] = field(default_factory=list)
    troops: int = 0
    alchemy_reactor: bool = False
    credit_rating: int = 500
    experience_score: int = 100
    faction_reputation: Dict[str, float] = field(default_factory=lambda: {"Federation": 50.0, "Corporate": 50.0, "Pirates": 20.0, "Indigenous": 50.0})
    loan_repayment_history: int = 0
    freight_deliveries_completed: int = 0
    default_history: int = 0
    phylogeny_node_id: Optional[str] = None
    cochain_flux: Dict[str, Any] = field(default_factory=lambda: {"mass": 0.0, "thermodynamic": 0.0, "exotic": 0.0, "entropic": 0.0, "total_cycles_tracked": 0})
    unlocked_phylogeny_nodes: List[str] = field(default_factory=list)
    chimeric_grafts: List[str] = field(default_factory=list)
    active_canopy_override: Optional[str] = None
    # Experience domains (verified outcomes) and anti-farm bookkeeping
    experience_domains: Dict[str, int] = field(default_factory=dict)
    visited_sectors: List[int] = field(default_factory=list)
    zones_entered: List[str] = field(default_factory=list)
    xp_window: Dict[str, Any] = field(default_factory=dict)
    colony_milestones: Dict[str, int] = field(default_factory=dict)
    # Realized revenue ledger [(cycle, credits)] used to size credit facilities
    revenue_history: List[List[int]] = field(default_factory=list)
    # Metabolism & federal insurance
    hunger: int = 0
    insurance_paid_through: int = 0
    # Autonomous cognition state (syntropic seat & failure memory)
    price_memory: Dict[str, Any] = field(default_factory=dict)
    active_plan: Optional[Dict[str, Any]] = None
    deed_cooldowns: Dict[str, int] = field(default_factory=dict)
    deed_failures: Dict[str, int] = field(default_factory=dict)
    # Regional currency balances (credits are SOL, the Federation reserve currency)
    fx_wallet: Dict[str, int] = field(default_factory=dict)
    scanned_belts: List[str] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    permits: List[str] = field(default_factory=list)
    # Cosmic alignment: +1 Light (syntropy) .. -1 Dark (entropy); distinct from the background title above
    cosmic_alignment: float = 0.0
    alignment_record: Dict[str, Any] = field(default_factory=dict)
    faction_id: Optional[str] = None      # Great-power allegiance (IMPERIUM, ZEALOT) for faction fleets
    heresy: int = 0                       # Imperial techno-heresy infractions
    chronicle_stats: Dict[str, Any] = field(default_factory=dict)
    command_mode: str = "FLY"             # Client command mode: FLY (cockpit) or EMPIRE (sovereign dashboard)
    house_id: Optional[str] = None        # NPC lineage (house) this autonomous captain belongs to
    traits: Dict[str, Any] = field(default_factory=dict)   # persona of an autonomous mind (see cognition.temperament)
    persona_memory: Dict[str, Any] = field(default_factory=dict)  # remembered payoff per plan kind
    wages_due: int = 0                    # crew pay accrued at sea, settled at the next port

    def __post_init__(self):
        if not self.phylogeny_node_id:
            try:
                from xylarium.kernel.phylogeny import PHYLOGENY_MANAGER
                root = PHYLOGENY_MANAGER.get_root_node_for_captain(self)
                self.phylogeny_node_id = root.id
                if root.id not in self.unlocked_phylogeny_nodes:
                    self.unlocked_phylogeny_nodes.append(root.id)
            except Exception:
                pass

    @property
    def rank_title(self) -> str:
        """Returns the clade-specific rank title based on current phylogenetic node or rank_tier."""
        if self.phylogeny_node_id:
            try:
                from xylarium.kernel.phylogeny import PHYLOGENY_MANAGER
                node = PHYLOGENY_MANAGER.get_node(self.phylogeny_node_id)
                if node and node.tier == self.rank_tier:
                    return node.name
            except Exception:
                pass
        clade_cfg = CLADE_RANK_MATRIX.get(self.clade.upper(), CLADE_RANK_MATRIX.get("BIOTIC", {}))
        tier_cfg = clade_cfg.get("tiers", {}).get(self.rank_tier, clade_cfg.get("tiers", {}).get(1, {}))
        return tier_cfg.get("title", "Captain")

    @property
    def rank_role(self) -> str:
        """Returns the operational role description for current phylogenetic node or rank tier."""
        if self.phylogeny_node_id:
            try:
                from xylarium.kernel.phylogeny import PHYLOGENY_MANAGER
                node = PHYLOGENY_MANAGER.get_node(self.phylogeny_node_id)
                if node and node.tier == self.rank_tier:
                    return node.role
            except Exception:
                pass
        clade_cfg = CLADE_RANK_MATRIX.get(self.clade.upper(), CLADE_RANK_MATRIX.get("BIOTIC", {}))
        tier_cfg = clade_cfg.get("tiers", {}).get(self.rank_tier, clade_cfg.get("tiers", {}).get(1, {}))
        return tier_cfg.get("role", "Starship Commander")

    @property
    def full_title(self) -> str:
        """Returns fully formatted formal title (e.g. 'Scrap-Apprentice Solo [BIOTIC-T1]')."""
        return f"{self.rank_title} {self.name} [{self.clade}-T{self.rank_tier}]"

    def get_promotion_requirements(self, kernel: Any = None) -> Dict[str, Any]:
        """Calculates exact progression invariants and qualification status for the next rank tier."""
        cur_crystals = len(self.grown_basis)
        cur_exp = self.experience_score
        cur_cr = self.credit_rating

        if kernel and hasattr(kernel, "market_manager"):
            cur_equity = kernel.market_manager.calculate_net_equity(self, kernel)
        else:
            cur_equity = max(1000, self.credits - (self.debt + getattr(self, "vc_debt", 0)))

        cur_debt = self.debt + getattr(self, "vc_debt", 0)
        cur_de = round(cur_debt / max(1.0, float(cur_equity)), 2)

        clade_cfg = CLADE_RANK_MATRIX.get(self.clade.upper(), CLADE_RANK_MATRIX.get("BIOTIC", {}))
        primary_faction = clade_cfg.get("primary_faction", "Federation")
        primary_rep = self.faction_reputation.get(primary_faction, 50.0)
        fallback_rep = self.faction_reputation.get("Federation" if self.clade != "ANARCHY" else "Pirates", 0.0)
        cur_rep = max(primary_rep, fallback_rep)

        if self.rank_tier >= 4:
            return {
                "max_rank": True,
                "current_tier": 4,
                "target_tier": 4,
                "current_title": self.rank_title,
                "target_title": self.rank_title,
                "can_promote": False,
                "reasons": ["Already ascended to Apex Sovereign Tier 4."],
                "checks": {},
                "reward_credits": 0,
                "reward_turns": 0,
            }

        target_tier = self.rank_tier + 1
        thresholds = RANK_PROMOTION_THRESHOLDS.get(target_tier, {})
        target_info = clade_cfg.get("tiers", {}).get(target_tier, {})
        target_title = target_info.get("title", f"Tier {target_tier}")

        min_exp = thresholds.get("min_experience", 250)
        min_cr = thresholds.get("min_credit_rating", 540)
        min_crystals = thresholds.get("min_crystals", 1)
        min_net_equity = thresholds.get("min_net_equity", 0)
        max_de = thresholds.get("max_debt_to_equity", 1.0)
        min_rep = thresholds.get("min_faction_rep", 50.0)

        exp_ok = cur_exp >= min_exp
        cr_ok = cur_cr >= min_cr
        crystals_ok = cur_crystals >= min_crystals
        equity_ok = cur_equity >= min_net_equity
        de_ok = cur_de <= max_de
        rep_ok = cur_rep >= min_rep

        can_advance = exp_ok and cr_ok and crystals_ok and equity_ok and de_ok and rep_ok

        reasons = []
        if not exp_ok:
            reasons.append(f"Experience Seniority (Ξ) {cur_exp} < {min_exp}")
        if not cr_ok:
            reasons.append(f"Credit Rating {cur_cr} < {min_cr}")
        if not crystals_ok:
            reasons.append(f"Grown Basis Crystals {cur_crystals} < {min_crystals}")
        if not equity_ok:
            reasons.append(f"Net Equity {cur_equity:,} Cr < {min_net_equity:,} Cr")
        if not de_ok:
            reasons.append(f"Debt-to-Equity {cur_de:.2f} > {max_de:.2f}")
        if not rep_ok:
            reasons.append(f"Faction Reputation ({primary_faction}) {cur_rep:.1f}% < {min_rep:.1f}%")

        return {
            "max_rank": False,
            "current_tier": self.rank_tier,
            "target_tier": target_tier,
            "current_title": self.rank_title,
            "target_title": target_title,
            "target_role": target_info.get("role", ""),
            "target_perks": target_info.get("perks", ""),
            "can_promote": can_advance,
            "reasons": reasons,
            "checks": {
                "experience": {"required": min_exp, "current": cur_exp, "passed": exp_ok},
                "credit_rating": {"required": min_cr, "current": cur_cr, "passed": cr_ok},
                "crystals": {"required": min_crystals, "current": cur_crystals, "passed": crystals_ok},
                "net_equity": {"required": min_net_equity, "current": cur_equity, "passed": equity_ok},
                "debt_to_equity": {"required": max_de, "current": cur_de, "passed": de_ok},
                "faction_rep": {"required": min_rep, "current": cur_rep, "faction": primary_faction, "passed": rep_ok},
            },
            "reward_credits": thresholds.get("credit_reward", 0),
            "reward_turns": thresholds.get("turns_reward", 0),
        }

    def can_promote(self, kernel: Any = None) -> Tuple[bool, str, Dict[str, Any]]:
        """Evaluates whether the captain meets all invariant thresholds to ascend in rank."""
        info = self.get_promotion_requirements(kernel)
        if info.get("max_rank"):
            return False, "Already achieved Apex Sovereign rank (Tier 4).", info
        if not info.get("can_promote"):
            unmet = "; ".join(info.get("reasons", []))
            return False, f"Promotion to Tier {info['target_tier']} ({info['target_title']}) locked: {unmet}.", info
        return True, f"Eligible for ascension to Tier {info['target_tier']} ({info['target_title']})!", info

    def promote_rank(self, kernel: Any = None) -> Tuple[bool, str]:
        """Ascends captain to the next Rank Tier if all invariants are met."""
        eligible, msg, info = self.can_promote(kernel)
        if not eligible:
            return False, msg

        old_title = self.rank_title
        self.rank_tier += 1

        # Synchronize phylogenetic node
        try:
            from xylarium.kernel.phylogeny import PHYLOGENY_MANAGER
            affinities = PHYLOGENY_MANAGER.compute_branch_affinities(self)
            cur_node = PHYLOGENY_MANAGER.get_node(self.phylogeny_node_id) if self.phylogeny_node_id else None
            if cur_node and affinities:
                best_child_id = max(affinities, key=affinities.get)
                self.phylogeny_node_id = best_child_id
                if not hasattr(self, "unlocked_phylogeny_nodes") or not isinstance(self.unlocked_phylogeny_nodes, list):
                    self.unlocked_phylogeny_nodes = []
                if best_child_id not in self.unlocked_phylogeny_nodes:
                    self.unlocked_phylogeny_nodes.append(best_child_id)
        except Exception:
            pass

        new_title = self.rank_title

        # Apply ascension rewards
        cr_reward = info.get("reward_credits", 0)
        turns_reward = info.get("reward_turns", 0)
        fed = getattr(kernel, "federal_reserve", None) if kernel is not None else None
        cr_reward = min(cr_reward, fed.treasury) if fed is not None else 0
        if fed is not None:
            fed.treasury -= cr_reward
            fed.stats["rank_endowments"] += cr_reward
        self.credits += cr_reward
        self.turns_left = min(500, self.turns_left + turns_reward)
        self.score += 500 * self.rank_tier

        # Positive credit score bump from proving creditworthiness
        self.adjust_credit_rating(15, reason="Rank Ascension")

        success_msg = (
            f"ASCENSION CONFIRMED: Promoted from {old_title} to {new_title} [Tier {self.rank_tier}]! "
            f"Endowment: +{cr_reward:,} Cr, +{turns_reward} Turns. Perks Unlocked: {info.get('target_perks', 'Advanced Privileges')}."
        )
        return True, success_msg

    @property
    def credit_tier(self) -> str:
        """Categorizes captain into standard interstellar credit risk tiers."""
        if self.credit_rating >= 750:
            return "PRIME_ALPHA"
        elif self.credit_rating >= 670:
            return "TIER_1_SECURE"
        elif self.credit_rating >= 580:
            return "TIER_2_FAIR"
        elif self.credit_rating >= 450:
            return "SUBPRIME"
        else:
            return "DISTRESSED"

    def adjust_credit_rating(self, delta: int, reason: str = "") -> int:
        """Adjusts captain credit rating within standard FICO bounds [300, 850]."""
        self.credit_rating = max(300, min(850, self.credit_rating + delta))
        return self.credit_rating

    def adjust_experience(self, delta: int) -> int:
        """Increments experience seniority score (Ξ)."""
        self.experience_score = max(0, self.experience_score + delta)
        return self.experience_score

    def adjust_reputation(self, faction: str, delta: float) -> float:
        """Adjusts social cohesion / reputation score with a specific faction [0.0, 100.0]."""
        cur = self.faction_reputation.get(faction, 50.0)
        new_val = round(max(0.0, min(100.0, cur + delta)), 1)
        self.faction_reputation[faction] = new_val
        return new_val

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "is_ai": self.is_ai,
            "personality": self.personality.value if self.personality else None,
            "ship": self.ship.to_dict(),
            "credits": self.credits,
            "sector_id": self.sector_id,
            "turns_left": self.turns_left,
            "home_sector": self.home_sector,
            "score": self.score,
            "hunt_target_sector": self.hunt_target_sector,
            "debt": self.debt,
            "operatives": self.operatives,
            "bounty": self.bounty,
            "bounty_placed_by": self.bounty_placed_by,
            "embargoed_by": list(self.embargoed_by),
            "portfolio": dict(self.portfolio),
            "active_contracts": list(self.active_contracts),
            "short_positions": {k: dict(v) for k, v in self.short_positions.items()},
            "sales_executives": list(self.sales_executives),
            "trade_haulers": list(self.trade_haulers),
            "technologies": list(self.technologies),
            "active_research": self.active_research,
            "research_progress": self.research_progress,
            "vc_active_syndicate": self.vc_active_syndicate,
            "vc_debt": self.vc_debt,
            "margin_loans": dict(self.margin_loans),
            "frozen_by": list(self.frozen_by),
            "charter": self.charter,
            "vc_royalty_pct": self.vc_royalty_pct,
            "vc_principal_paid": self.vc_principal_paid,
            "cartography_fragments": [dict(f) for f in self.cartography_fragments],
            "unlocked_secrets": list(self.unlocked_secrets),
            "active_cartography_puzzle": self.active_cartography_puzzle,
            "toll_gates": list(self.toll_gates),
            "survey_probes": list(self.survey_probes),
            "species": self.species,
            "metabolism": self.metabolism,
            "clade": self.clade,
            "rank_tier": self.rank_tier,
            "rank_title": self.rank_title,
            "rank_role": self.rank_role,
            "full_title": self.full_title,
            "background": self.background,
            "alignment": self.alignment,
            "forged_transponder": self.forged_transponder or ("FORGED_TRANSPONDER" in self.unlocked_secrets),
            "grown_basis": [dict(b) for b in self.grown_basis],
            "troops": self.troops,
            "alchemy_reactor": self.alchemy_reactor,
            "credit_rating": self.credit_rating,
            "credit_tier": self.credit_tier,
            "experience_score": self.experience_score,
            "faction_reputation": dict(self.faction_reputation),
            "loan_repayment_history": self.loan_repayment_history,
            "freight_deliveries_completed": self.freight_deliveries_completed,
            "default_history": self.default_history,
            "phylogeny_node_id": self.phylogeny_node_id,
            "cochain_flux": dict(self.cochain_flux),
            "unlocked_phylogeny_nodes": list(self.unlocked_phylogeny_nodes),
            "chimeric_grafts": list(self.chimeric_grafts),
            "active_canopy_override": self.active_canopy_override,
            "experience_domains": dict(self.experience_domains),
            "visited_sectors": list(self.visited_sectors),
            "zones_entered": list(self.zones_entered),
            "xp_window": dict(self.xp_window),
            "colony_milestones": dict(self.colony_milestones),
            "revenue_history": [list(r) for r in self.revenue_history],
            "hunger": self.hunger,
            "insurance_paid_through": self.insurance_paid_through,
            "price_memory": dict(self.price_memory),
            "active_plan": dict(self.active_plan) if self.active_plan else None,
            "deed_cooldowns": dict(self.deed_cooldowns),
            "deed_failures": dict(self.deed_failures),
            "fx_wallet": dict(self.fx_wallet),
            "scanned_belts": list(self.scanned_belts),
            "artifacts": [dict(a) for a in self.artifacts],
            "permits": list(self.permits),
            "cosmic_alignment": round(self.cosmic_alignment, 4),
            "alignment_record": dict(self.alignment_record),
            "faction_id": self.faction_id,
            "heresy": self.heresy,
            "chronicle_stats": dict(self.chronicle_stats),
            "command_mode": self.command_mode,
            "house_id": self.house_id,
            "traits": dict(self.traits),
            "persona_memory": dict(self.persona_memory),
            "wages_due": self.wages_due,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Captain":
        pers = AIPersonality(data["personality"]) if data.get("personality") else None
        return cls(
            id=data["id"],
            name=data["name"],
            is_ai=data["is_ai"],
            personality=pers,
            ship=Ship.from_dict(data["ship"]),
            credits=data["credits"],
            sector_id=data["sector_id"],
            turns_left=data["turns_left"],
            home_sector=data.get("home_sector", 1),
            score=data.get("score", 0),
            hunt_target_sector=data.get("hunt_target_sector"),
            debt=data.get("debt", 0),
            operatives=data.get("operatives", 0),
            bounty=data.get("bounty", 0),
            bounty_placed_by=data.get("bounty_placed_by"),
            embargoed_by=list(data.get("embargoed_by", [])),
            portfolio=dict(data.get("portfolio", {})),
            active_contracts=list(data.get("active_contracts", [])),
            short_positions={k: dict(v) for k, v in data.get("short_positions", {}).items()},
            sales_executives=list(data.get("sales_executives", [])),
            trade_haulers=list(data.get("trade_haulers", [])),
            technologies=list(data.get("technologies", [])),
            active_research=data.get("active_research"),
            research_progress=data.get("research_progress", 0),
            vc_active_syndicate=data.get("vc_active_syndicate"),
            vc_debt=data.get("vc_debt", 0),
            margin_loans={k: int(v) for k, v in data.get("margin_loans", {}).items()},
            frozen_by=list(data.get("frozen_by", [])),
            charter=data.get("charter"),
            vc_royalty_pct=data.get("vc_royalty_pct", 0.0),
            vc_principal_paid=data.get("vc_principal_paid", 0),
            cartography_fragments=list(data.get("cartography_fragments", [])),
            unlocked_secrets=list(data.get("unlocked_secrets", [])),
            active_cartography_puzzle=data.get("active_cartography_puzzle"),
            toll_gates=list(data.get("toll_gates", [])),
            survey_probes=list(data.get("survey_probes", [])),
            species=data.get("species", "human-sol"),
            metabolism=data.get("metabolism", "biotic"),
            clade=data.get("clade", "BIOTIC"),
            rank_tier=int(data.get("rank_tier", 1)),
            background=data.get("background"),
            alignment=data.get("alignment", "Independent"),
            forged_transponder=bool(data.get("forged_transponder", False) or "FORGED_TRANSPONDER" in data.get("unlocked_secrets", [])),
            grown_basis=list(data.get("grown_basis", [])),
            troops=int(data.get("troops", 0)),
            alchemy_reactor=bool(data.get("alchemy_reactor", False)),
            credit_rating=int(data.get("credit_rating", 500)),
            experience_score=int(data.get("experience_score", 100)),
            faction_reputation=dict(data.get("faction_reputation", {"Federation": 50.0, "Corporate": 50.0, "Pirates": 20.0, "Indigenous": 50.0})),
            loan_repayment_history=int(data.get("loan_repayment_history", 0)),
            freight_deliveries_completed=int(data.get("freight_deliveries_completed", 0)),
            default_history=int(data.get("default_history", 0)),
            phylogeny_node_id=data.get("phylogeny_node_id"),
            cochain_flux=dict(data.get("cochain_flux", {"mass": 0.0, "thermodynamic": 0.0, "exotic": 0.0, "entropic": 0.0, "total_cycles_tracked": 0})),
            unlocked_phylogeny_nodes=list(data.get("unlocked_phylogeny_nodes", [])),
            chimeric_grafts=list(data.get("chimeric_grafts", [])),
            active_canopy_override=data.get("active_canopy_override"),
            experience_domains=dict(data.get("experience_domains", {})),
            visited_sectors=list(data.get("visited_sectors", [])),
            zones_entered=list(data.get("zones_entered", [])),
            xp_window=dict(data.get("xp_window", {})),
            colony_milestones=dict(data.get("colony_milestones", {})),
            revenue_history=[list(r) for r in data.get("revenue_history", [])],
            hunger=int(data.get("hunger", 0)),
            insurance_paid_through=int(data.get("insurance_paid_through", 0)),
            price_memory=dict(data.get("price_memory", {})),
            active_plan=data.get("active_plan"),
            deed_cooldowns={k: int(v) for k, v in data.get("deed_cooldowns", {}).items()},
            deed_failures={k: int(v) for k, v in data.get("deed_failures", {}).items()},
            fx_wallet={k: int(v) for k, v in data.get("fx_wallet", {}).items()},
            scanned_belts=list(data.get("scanned_belts", [])),
            artifacts=[dict(a) for a in data.get("artifacts", [])],
            permits=list(data.get("permits", [])),
            cosmic_alignment=float(data.get("cosmic_alignment", 0.0)),
            alignment_record=dict(data.get("alignment_record", {})),
            faction_id=data.get("faction_id"),
            heresy=int(data.get("heresy", 0)),
            chronicle_stats=dict(data.get("chronicle_stats", {})),
            command_mode=data.get("command_mode", "FLY"),
            house_id=data.get("house_id"),
            traits=dict(data.get("traits", {})),
            persona_memory=dict(data.get("persona_memory", {})),
            wages_due=int(data.get("wages_due", 0)),
        )


@dataclass
class Sector:
    id: int
    name: str
    security: SecurityLevel
    warps: List[int] = field(default_factory=list)
    port: Optional[Port] = None
    planets: List[Planet] = field(default_factory=list)
    captains: List[str] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)
    cluster_name: str = "Sol Federation Core"
    is_secret: bool = False
    secret_id: Optional[str] = None
    kind: str = "SYSTEM"          # "SYSTEM" (star, ports, planets) or "NULL" (deep space between systems)
    star_type: Optional[str] = None
    star: Optional[Dict[str, str]] = None                        # exact stellar physics: m, mass, luminosity (physics.py)
    belts: List[Dict[str, Any]] = field(default_factory=list)    # asteroid belts (null space)
    debris: List[Dict[str, Any]] = field(default_factory=list)   # salvage fields from destroyed hulls
    sentries: Dict[str, int] = field(default_factory=dict)       # owner_id -> deployed sentry fighters
    gas: int = 0                                                 # drive exhaust (hydrogen) drifting here: scoopable

    @property
    def is_null_space(self) -> bool:
        return self.kind == "NULL"

    @property
    def is_protected_space(self) -> bool:
        """Inside a star system with a starport or an inhabited world: opening fire is a hostile act."""
        if self.kind != "SYSTEM":
            return False
        return self.port is not None or any(p.population > 0 or p.owner_id for p in self.planets)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "security": self.security.value,
            "warps": list(self.warps),
            "port": self.port.to_dict() if self.port else None,
            "planets": [p.to_dict() for p in self.planets],
            "captains": list(self.captains),
            "anomalies": list(self.anomalies),
            "cluster_name": self.cluster_name,
            "is_secret": self.is_secret,
            "secret_id": self.secret_id,
            "kind": self.kind,
            "star_type": self.star_type,
            "star": dict(self.star) if self.star else None,
            "belts": [dict(b, composition=dict(b.get("composition", {}))) for b in self.belts],
            "debris": [dict(d, cargo=dict(d.get("cargo", {}))) for d in self.debris],
            "sentries": dict(self.sentries),
            "gas": self.gas,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Sector":
        port = Port.from_dict(data["port"]) if data.get("port") else None
        planets = [Planet.from_dict(p) for p in data.get("planets", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            security=SecurityLevel(data["security"]),
            warps=list(data.get("warps", [])),
            port=port,
            planets=planets,
            captains=list(data.get("captains", [])),
            anomalies=list(data.get("anomalies", [])),
            cluster_name=data.get("cluster_name", "Sol Federation Core"),
            is_secret=data.get("is_secret", False),
            secret_id=data.get("secret_id"),
            kind=data.get("kind", "SYSTEM"),
            star_type=data.get("star_type"),
            star=dict(data["star"]) if data.get("star") else None,
            belts=[dict(b, composition=dict(b.get("composition", {}))) for b in data.get("belts", [])],
            debris=[dict(d, cargo=dict(d.get("cargo", {}))) for d in data.get("debris", [])],
            sentries={k: int(v) for k, v in data.get("sentries", {}).items()},
            gas=int(data.get("gas", 0)),
        )


@dataclass
class RadioMessage:
    sender: str
    text: str
    channel: str = "COMM-1"
    sector_id: Optional[int] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender": self.sender,
            "text": self.text,
            "channel": self.channel,
            "sector_id": self.sector_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RadioMessage":
        return cls(
            sender=data["sender"],
            text=data["text"],
            channel=data.get("channel", "COMM-1"),
            sector_id=data.get("sector_id"),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class ActionResult:
    success: bool
    action: ActionType = ActionType.MOVE
    message: str = ""
    turns_spent: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)

    def __init__(
        self,
        success: bool,
        action: Optional[ActionType] = None,
        message: str = "",
        turns_spent: int = 0,
        data: Optional[Dict[str, Any]] = None,
        logs: Optional[List[str]] = None,
        action_type: Optional[ActionType] = None,
    ):
        self.success = success
        self.action = action if action is not None else (action_type if action_type is not None else ActionType.MOVE)
        self.message = message
        self.turns_spent = turns_spent
        self.data = data if data is not None else {}
        self.logs = logs if logs is not None else []
