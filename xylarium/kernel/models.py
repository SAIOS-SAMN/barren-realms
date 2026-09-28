"""
Data models and Enums for the Xylarium core kernel.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time


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


class AIPersonality(str, Enum):
    TRADER = "trader"
    PIRATE = "pirate"
    INDUSTRIALIST = "industrialist"
    MERCENARY = "mercenary"


@dataclass
class CargoHold:
    ore: int = 0
    organics: int = 0
    equipment: int = 0
    capacity: int = 30

    @property
    def total_used(self) -> int:
        return self.ore + self.organics + self.equipment

    @property
    def available_space(self) -> int:
        return max(0, self.capacity - self.total_used)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ore": self.ore,
            "organics": self.organics,
            "equipment": self.equipment,
            "capacity": self.capacity,
            "used": self.total_used,
            "available": self.available_space,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CargoHold":
        return cls(
            ore=data.get("ore", 0),
            organics=data.get("organics", 0),
            equipment=data.get("equipment", 0),
            capacity=data.get("capacity", 30),
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_id": self.sector_id,
            "name": self.name,
            "port_class": self.port_class.value,
            "stock": dict(self.stock),
            "max_stock": dict(self.max_stock),
            "buys": dict(self.buys),
            "sells": dict(self.sells),
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
            "treasury": self.treasury,
            "ore_silo": self.ore_silo,
            "organics_silo": self.organics_silo,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Planet":
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
        )


@dataclass
class Ship:
    ship_type: str
    cargo: CargoHold
    shields: int
    max_shields: int
    fighters: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ship_type": self.ship_type,
            "cargo": self.cargo.to_dict(),
            "shields": self.shields,
            "max_shields": self.max_shields,
            "fighters": self.fighters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ship":
        return cls(
            ship_type=data["ship_type"],
            cargo=CargoHold.from_dict(data["cargo"]),
            shields=data["shields"],
            max_shields=data["max_shields"],
            fighters=data["fighters"],
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "security": self.security.value,
            "warps": list(self.warps),
            "port": self.port.to_dict() if self.port else None,
            "planets": [p.to_dict() for p in self.planets],
            "captains": list(self.captains),
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
    action: ActionType
    message: str
    turns_spent: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
