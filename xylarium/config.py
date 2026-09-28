"""
Xylarium: Classic BBS Door Game & MUD Kernel Configuration
Inspired by TradeWars 2002, Barren Realms Elite (BRE), and Solar Realms Elite (SRE).
"""

from typing import Dict, Any

# Universe Configuration
TOTAL_SECTORS: int = 100
FEDERATION_SECTOR_START: int = 1
FEDERATION_SECTOR_END: int = 10
BORDER_SECTOR_END: int = 60
# Sectors 61-100 are Anarchy / Deep Void

DEFAULT_MAX_WARPS: int = 6
DEFAULT_MIN_WARPS: int = 2

# Player Starting Attributes
PLAYER_STARTING_SECTOR: int = 1
PLAYER_STARTING_CREDITS: int = 1500
PLAYER_STARTING_TURNS: int = 200
PLAYER_MAX_TURNS: int = 500
PLAYER_STARTING_HOLDS: int = 30
PLAYER_STARTING_SHIELDS: int = 100
PLAYER_STARTING_FIGHTERS: int = 15

# Turn Costs
TURN_COST_MOVE: int = 1
TURN_COST_TRADE: int = 1
TURN_COST_PLANET_OP: int = 1
TURN_COST_ATTACK: int = 2
TURN_COST_SHIPYARD: int = 0  # Free inside sector 1

# Commodity Base Prices and Characteristics
COMMODITY_CONFIG = {
    "ORE": {
        "name": "Ore",
        "base_price": 25,
        "min_price": 10,
        "max_price": 75,
        "volatility": 0.45,
    },
    "ORGANICS": {
        "name": "Organics",
        "base_price": 55,
        "min_price": 25,
        "max_price": 130,
        "volatility": 0.50,
    },
    "EQUIPMENT": {
        "name": "Equipment",
        "base_price": 110,
        "min_price": 55,
        "max_price": 260,
        "volatility": 0.60,
    },
}

# Ship Classes Available at Fed Shipyard
SHIP_CATALOG = {
    "Scout Ship": {
        "holds": 25,
        "max_shields": 100,
        "max_fighters": 20,
        "price": 0,
        "description": "Nimble reconnaissance craft. Low cargo, light shielding."
    },
    "Merchant Cruiser": {
        "holds": 60,
        "max_shields": 200,
        "max_fighters": 40,
        "price": 5000,
        "description": "Standard workhorse of interplanetary haulers. Balanced cargo."
    },
    "Star Frigate": {
        "holds": 100,
        "max_shields": 450,
        "max_fighters": 100,
        "price": 15000,
        "description": "Heavy armed transport with robust shields and fighter bays."
    },
    "Dreadnought Battlecruiser": {
        "holds": 180,
        "max_shields": 1000,
        "max_fighters": 300,
        "price": 45000,
        "description": "Military capital ship capable of deep space supremacy."
    }
}

# Colony Citadel Upgrades (BRE / SRE style)
CITADEL_CONFIG = {
    0: {
        "name": "Barren Outpost",
        "tax_multiplier": 1.0,
        "max_shields": 200,
        "max_fighters": 50,
        "upgrade_cost": 0,
        "upgrade_ore": 0,
    },
    1: {
        "name": "Fortified Redoubt",
        "tax_multiplier": 1.5,
        "max_shields": 500,
        "max_fighters": 150,
        "upgrade_cost": 3000,
        "upgrade_ore": 50,
    },
    2: {
        "name": "Planetary Stronghold",
        "tax_multiplier": 2.2,
        "max_shields": 1200,
        "max_fighters": 400,
        "upgrade_cost": 9000,
        "upgrade_ore": 150,
    },
    3: {
        "name": "Imperial Citadel",
        "tax_multiplier": 3.5,
        "max_shields": 3000,
        "max_fighters": 1000,
        "upgrade_cost": 25000,
        "upgrade_ore": 400,
    },
}

# AI Captain Archetypes
AI_CAPTAINS_CONFIG = [
    {
        "id": "ai_vane",
        "name": "Capt. Jack Vane",
        "personality": "trader",
        "ship_class": "Merchant Cruiser",
        "credits": 2500,
        "holds": 50,
        "shields": 150,
        "fighters": 20,
        "start_sector": 4,
    },
    {
        "id": "ai_malakor",
        "name": "Warlord Malakor",
        "personality": "pirate",
        "ship_class": "Star Frigate",
        "credits": 4000,
        "holds": 70,
        "shields": 350,
        "fighters": 80,
        "start_sector": 78,
    },
    {
        "id": "ai_voss",
        "name": "Director Cynthia Voss",
        "personality": "industrialist",
        "ship_class": "Merchant Cruiser",
        "credits": 6000,
        "holds": 80,
        "shields": 250,
        "fighters": 35,
        "start_sector": 18,
    },
    {
        "id": "ai_ironclaw",
        "name": "Ironclaw Rake",
        "personality": "mercenary",
        "ship_class": "Star Frigate",
        "credits": 3000,
        "holds": 40,
        "shields": 400,
        "fighters": 95,
        "start_sector": 45,
    },
]
