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
TURN_COST_REST: int = 0      # Resting costs credits, not turns
TURN_COST_COVERT_OP: int = 1 # Covert ops cost 1 turn

# Maintenance & Emergency Finance Settings
MAINTENANCE_INTERVAL_CYCLES: int = 50
MAINTENANCE_TURNS_GRANTED: int = 100
REST_COST_CREDITS: int = 1000
REST_TURNS_RESTORED: int = 50
BANK_LOAN_AMOUNT: int = 1000
BANK_DEBT_TOTAL: int = 1150
BANK_EMERGENCY_THRESHOLD: int = 100

# Espionage & Covert Ops Agency
OPERATIVE_COST_CREDITS: int = 500
COVERT_OPS_CONFIG = {
    "recon": {
        "name": "Classified Intelligence Recon",
        "min_operatives": 1,
        "base_success": 0.80,
        "description": "Infiltrate flagship telemetry or planetary redoubt to obtain classified tactical data.",
    },
    "siphon": {
        "name": "Planetary Vault Siphon",
        "min_operatives": 2,
        "base_success": 0.65,
        "description": "Hack secure financial nodes and siphon 15% - 35% of the colony's treasury credits.",
    },
    "sabotage": {
        "name": "Shield Grid Sabotage",
        "min_operatives": 2,
        "base_success": 0.60,
        "description": "Detonate neural EMP charges in shield capacitor arrays, destroying 40% - 75% of active shields.",
    },
    "destabilize": {
        "name": "Biosphere & Morale Destabilization",
        "min_operatives": 3,
        "base_success": 0.55,
        "description": "Contaminate organics biosilos and incite unrest, plunging colony morale and triggering famine.",
    },
    "cartographic_heist": {
        "name": "Cartographic Data Interception",
        "min_operatives": 3,
        "base_success": 0.55,
        "description": "Infiltrate rival corporate star-vaults to extract decrypted starmap telemetry, secret coordinates, and Precursor fragments.",
    },
}

# Cartography Advanced Expansion Settings
TOLL_GATE_DEPLOY_COST_CREDITS: int = 5000
SURVEY_PROBE_COST_CREDITS: int = 5000
FORGED_CHIT_SYNTH_COST: int = 1000
FORGED_CHIT_BROKER_VALUE: int = 3000

# Commodity Base Prices and Characteristics (24 Periodic Elements + Manufactured Components + Legacy)
COMMODITY_CONFIG = {
    # Legacy TradeWars Tri-Commodities
    "ORE": {
        "name": "Ore",
        "symbol": "ORE",
        "category": "METALS",
        "base_price": 25,
        "min_price": 10,
        "max_price": 75,
        "volatility": 0.45,
    },
    "NaCl": {                      # halite: dug from evaporite beds as ore is dug from crust - ORE's price where it
        "name": "Halite (Salt)",   # is plentiful; where it is not, its landed cost carries it (supply.py)
        "symbol": "NaCl",
        "category": "MINERALS",
        "base_price": 25,
        "min_price": 10,
        "max_price": 75,
        "volatility": 0.45,
    },
    "ORGANICS": {
        "name": "Organics",
        "symbol": "ORG",
        "category": "VOLATILES",
        "base_price": 55,
        "min_price": 25,
        "max_price": 130,
        "volatility": 0.50,
    },
    "EQUIPMENT": {
        "name": "Equipment",
        "symbol": "EQP",
        "category": "MANUFACTURED",
        "base_price": 110,
        "min_price": 55,
        "max_price": 260,
        "volatility": 0.60,
        "recipe": {"ORE": 2},
    },
    # Industrial waste: what fabrication leaves over (inputs = product + slag). Ports recycle it; tailings are
    # landfilled into the region's ground, where they weigh on its worlds' living space.
    "SLAG": {"name": "Industrial Slag", "symbol": "SLG", "category": "WASTE", "base_price": 2, "min_price": 1,
             "max_price": 8, "volatility": 0.3},
    # Luxuries: four super-types, crafted by provided-for worlds from what they hold in abundance and named for
    # their people (luxury.py). Every starport trades them; each world craves the ones it cannot make.
    "LUX_STIMULANT": {"name": "Sensory Stimulants", "symbol": "STM", "category": "LUXURY", "base_price": 90,
                      "min_price": 40, "max_price": 260, "volatility": 0.6},
    "LUX_RESONANT": {"name": "Resonant Artifacts", "symbol": "RSN", "category": "LUXURY", "base_price": 140,
                     "min_price": 60, "max_price": 380, "volatility": 0.5},
    "LUX_EPHEMERA": {"name": "Exotic Ephemera", "symbol": "EPH", "category": "LUXURY", "base_price": 110,
                     "min_price": 45, "max_price": 320, "volatility": 0.7},
    "LUX_CURIO": {"name": "Precursor Curios", "symbol": "CUR", "category": "LUXURY", "base_price": 220,
                  "min_price": 90, "max_price": 600, "volatility": 0.5},

    # [1] VOLATILES & LIFE PRECURSORS (Gases & Liquids)
    "H": {"name": "Hydrogen Fuel", "symbol": "H", "category": "VOLATILES", "base_price": 12, "min_price": 6, "max_price": 35, "volatility": 0.40},
    "He-3": {"name": "Helium-3 Isotope", "symbol": "He-3", "category": "VOLATILES", "base_price": 45, "min_price": 20, "max_price": 120, "volatility": 0.55},
    "C": {"name": "Carbon Allotropes", "symbol": "C", "category": "VOLATILES", "base_price": 18, "min_price": 8, "max_price": 50, "volatility": 0.40},
    "H2O": {"name": "Liquid Water / Ice", "symbol": "H2O", "category": "VOLATILES", "base_price": 22, "min_price": 10, "max_price": 60, "volatility": 0.45},
    "Xe": {"name": "Xenon Gas", "symbol": "Xe", "category": "VOLATILES", "base_price": 65, "min_price": 30, "max_price": 180, "volatility": 0.60},

    # [2] STRUCTURAL METALS & ALLOYS (Heavy Ores)
    "Fe": {"name": "Raw Iron Ore", "symbol": "Fe", "category": "METALS", "base_price": 16, "min_price": 8, "max_price": 45, "volatility": 0.35},
    "Ti": {"name": "Titanium Ingots", "symbol": "Ti", "category": "METALS", "base_price": 38, "min_price": 18, "max_price": 95, "volatility": 0.45},
    "Si": {"name": "Silicon Wafers", "symbol": "Si", "category": "METALS", "base_price": 28, "min_price": 14, "max_price": 75, "volatility": 0.45},
    "Ni": {"name": "Refined Nickel", "symbol": "Ni", "category": "METALS", "base_price": 32, "min_price": 15, "max_price": 85, "volatility": 0.40},
    "Cu": {"name": "Copper Conductor", "symbol": "Cu", "category": "METALS", "base_price": 25, "min_price": 12, "max_price": 65, "volatility": 0.40},
    "AdL": {"name": "Adamant Lode Blocks", "symbol": "AdL", "category": "METALS", "base_price": 120, "min_price": 60, "max_price": 300, "volatility": 0.65},

    # [3] FISSIONABLES, NOBLES & EXOTICS (Precious Specie)
    "U": {"name": "Enriched Uranium", "symbol": "U", "category": "EXOTICS", "base_price": 110, "min_price": 55, "max_price": 280, "volatility": 0.60},
    # made only from energy (energy.py): no port is chartered with any
    "AM": {"name": "Antimatter Cell", "symbol": "AM", "category": "SYNTHETIC", "base_price": 900, "min_price": 400, "max_price": 2500, "volatility": 0.5},
    "Pt": {"name": "Platinum Catalysts", "symbol": "Pt", "category": "EXOTICS", "base_price": 95, "min_price": 45, "max_price": 240, "volatility": 0.55},
    "SpR": {"name": "Spiral Rime Crystals", "symbol": "SpR", "category": "EXOTICS", "base_price": 240, "min_price": 110, "max_price": 600, "volatility": 0.70},
    "cryogenite": {"name": "Cryogenite", "symbol": "Crg", "category": "EXOTICS", "base_price": 130, "min_price": 60, "max_price": 320, "volatility": 0.60},
    "stelalith": {"name": "Stelalith", "symbol": "Stl", "category": "EXOTICS", "base_price": 115, "min_price": 55, "max_price": 290, "volatility": 0.55},
    "umbrite": {"name": "Umbrite", "symbol": "Umb", "category": "EXOTICS", "base_price": 150, "min_price": 70, "max_price": 380, "volatility": 0.65},
    "chitinium": {"name": "Chitinium", "symbol": "Cht", "category": "EXOTICS", "base_price": 85, "min_price": 40, "max_price": 210, "volatility": 0.50},
    "pyrosite": {"name": "Pyrosite", "symbol": "Pyr", "category": "EXOTICS", "base_price": 140, "min_price": 65, "max_price": 350, "volatility": 0.60},
    "aetherium": {"name": "Aetherium", "symbol": "Aeth", "category": "EXOTICS", "base_price": 220, "min_price": 100, "max_price": 550, "volatility": 0.70},
    "ferrolattice": {"name": "Ferrolattice", "symbol": "Flt", "category": "EXOTICS", "base_price": 90, "min_price": 45, "max_price": 230, "volatility": 0.50},

    # [3b] XENOBIOLOGICAL SPECIMENS & EXTREMOPHILE METABOLITES
    "XENOPROTEIN": {"name": "Xenoprotein Isolates", "symbol": "Xpr", "category": "EXOTICS", "base_price": 95, "min_price": 45, "max_price": 240, "volatility": 0.50},
    "CRYOPROTECTANT": {"name": "Cryoprotectant Enzymes", "symbol": "Cpe", "category": "EXOTICS", "base_price": 105, "min_price": 50, "max_price": 270, "volatility": 0.55},
    "PIEZO_ENZYME": {"name": "Piezo-Enzymatic Crystals", "symbol": "Pze", "category": "EXOTICS", "base_price": 115, "min_price": 55, "max_price": 290, "volatility": 0.55},
    "RADIOTROPHIC_MELANIN": {"name": "Radiotrophic Melanin Matrix", "symbol": "Rmm", "category": "EXOTICS", "base_price": 135, "min_price": 60, "max_price": 340, "volatility": 0.60},
    "BIO_CHITIN": {"name": "Bio-Adaptive Chitin", "symbol": "Bch", "category": "EXOTICS", "base_price": 80, "min_price": 38, "max_price": 200, "volatility": 0.50},
    "NEURO_SPORE": {"name": "Synaptic Neuro-Spores", "symbol": "Nsp", "category": "EXOTICS", "base_price": 175, "min_price": 85, "max_price": 440, "volatility": 0.65},

    # [4] MANUFACTURED VALUE-ADDED COMPONENTS (Industrial Goods)
    "M1_SUPERCONDUCTOR": {"name": "Superconducting Solenoids", "symbol": "M1", "category": "MANUFACTURED", "base_price": 180, "min_price": 80, "max_price": 450, "volatility": 0.55, "recipe": {"Ti": 1, "Cu": 1, "He-3": 1}},
    "M2_BIOSPHERE_PACK": {"name": "Biosphere Hydration Packs", "symbol": "M2", "category": "MANUFACTURED", "base_price": 140, "min_price": 65, "max_price": 360, "volatility": 0.50, "recipe": {"H2O": 2, "C": 1}},
    "M3_ENGINE_MANIFOLD": {"name": "Sub-Light Engine Manifolds", "symbol": "M3", "category": "MANUFACTURED", "base_price": 320, "min_price": 150, "max_price": 800, "volatility": 0.65, "recipe": {"Fe": 2, "Ti": 1, "U": 1}},
    "M4_WARP_CORE": {"name": "Warp Stabilizer Cores", "symbol": "M4", "category": "MANUFACTURED", "base_price": 550, "min_price": 250, "max_price": 1400, "volatility": 0.75, "recipe": {"AdL": 1, "SpR": 1, "Xe": 1}},
}

# Hierarchical Trade Categories
COMMODITY_CATEGORIES = {
    "1": {
        "id": "VOLATILES",
        "name": "VOLATILES & LIFE PRECURSORS (Gases & Liquids)",
        "commodities": ["H", "He-3", "C", "H2O", "Xe"],
        "primary_hull": "CRYO_TANKER",
    },
    "2": {
        "id": "METALS",
        "name": "STRUCTURAL METALS & ALLOYS (Heavy Ores)",
        "commodities": ["Fe", "Ti", "Si", "Ni", "Cu", "AdL"],
        "primary_hull": "BULK_FREIGHTER",
    },
    "3": {
        "id": "EXOTICS",
        "name": "FISSIONABLES, NOBLES & EXOTICS (Precious Specie)",
        "commodities": ["U", "Pt", "SpR", "cryogenite", "stelalith", "umbrite", "chitinium", "pyrosite", "aetherium", "ferrolattice"],
        "primary_hull": "QUANTUM_SKIFF",
    },
    "4": {
        "id": "MANUFACTURED",
        "name": "MANUFACTURED VALUE-ADDED COMPONENTS (Industrial Goods)",
        "commodities": ["M1_SUPERCONDUCTOR", "M2_BIOSPHERE_PACK", "M3_ENGINE_MANIFOLD", "M4_WARP_CORE"],
        "primary_hull": "QUANTUM_SKIFF",
    },
}

# Bulk Density & Cargo Hold Stack Multipliers (Units Stored per Hold)
# Reflects molecular compression, cryo-liquefaction, and raw ore bulk density
COMMODITY_STACK_MULTIPLIERS: Dict[str, int] = {
    # [1] Volatiles & Life Precursors (Gases & Liquids) - 5x density
    "H": 5,
    "HE-3": 5,
    "He-3": 5,
    "C": 5,
    "H2O": 5,
    "WATER": 5,
    "Xe": 5,
    "XE": 5,

    # [2] Structural Metals & Raw Ores - 4x density
    "ORE": 4,
    "FE": 4,
    "Fe": 4,
    "TI": 4,
    "Ti": 4,
    "SI": 4,
    "Si": 4,
    "NI": 4,
    "Ni": 4,
    "CU": 4,
    "Cu": 4,
    "ADL": 4,
    "AdL": 4,
    "NACL": 4,
    "NaCl": 4,

    # [3] Standard Tri-Commodities & Biomaterials - 2x density
    "ORGANICS": 2,
    "ORG": 2,
    "CHITINIUM": 2,
    "chitinium": 2,
    "M2_BIOSPHERE_PACK": 2,

    # [4] High-Tech, Precision Equipment & Exotics - 1x strict density
    "EQUIPMENT": 1,
    "EQP": 1,
    "U": 1,
    "PT": 1,
    "Pt": 1,
    "SPR": 1,
    "SpR": 1,
    "CRYOGENITE": 1,
    "cryogenite": 1,
    "STELALITH": 1,
    "stelalith": 1,
    "UMBRITE": 1,
    "umbrite": 1,
    "PYROSITE": 1,
    "pyrosite": 1,
    "AETHERIUM": 1,
    "aetherium": 1,
    "FERROLATTICE": 1,
    "ferrolattice": 1,
    "M1_SUPERCONDUCTOR": 1,
    "M3_ENGINE_MANIFOLD": 1,
    "M4_WARP_CORE": 1,
}

DEFAULT_COMMODITY_STACK_MULTIPLIER: int = 1


def get_commodity_stack_multiplier(commodity: str) -> int:
    """Returns the stack density multiplier (units per hold) for a given commodity or element."""
    if not commodity:
        return DEFAULT_COMMODITY_STACK_MULTIPLIER
    c_clean = str(commodity).strip()
    if c_clean in COMMODITY_STACK_MULTIPLIERS:
        return COMMODITY_STACK_MULTIPLIERS[c_clean]
    if c_clean.upper() in COMMODITY_STACK_MULTIPLIERS:
        return COMMODITY_STACK_MULTIPLIERS[c_clean.upper()]
    # Category fallback
    cfg = COMMODITY_CONFIG.get(c_clean, COMMODITY_CONFIG.get(c_clean.upper(), {}))
    cat = cfg.get("category", "")
    if cat == "VOLATILES":
        return 5
    elif cat == "METALS":
        return 4
    elif c_clean.upper() in ("ORGANICS", "ORG"):
        return 2
    return DEFAULT_COMMODITY_STACK_MULTIPLIER

# Specialized Hauler Classes for Logistics Network
SPECIALIZED_HULLS = {
    "STANDARD": {
        "name": "Merchant Hauler",
        "holds": 50,
        "price": 4000,
        "allowed_categories": ["VOLATILES", "METALS", "EXOTICS", "MANUFACTURED"],
        "allowed_commodities": ["ORE", "ORGANICS", "EQUIPMENT"],
        "description": "Standard workhorse cargo hauler for basic commodities.",
        "icon": "🚚",
        "chemical_rating": "BASIC",
        "wormhole_capable": False,
        "cryo_min_kelvin": 150.0,       # Cannot store cryogenic volatiles below 150 K
        "max_radiation_decay_ev": 1.0,  # Unshielded against ionizing alpha/beta decay
        "max_fissile_z": 82,            # Cannot hold heavy fissionable actinides (Z > 82)
        "min_tensile_gpa": 50.0,
    },
    "CRYO_TANKER": {
        "name": "Volatile Tanker",
        "holds": 80,
        "price": 12000,
        "allowed_categories": ["VOLATILES"],
        "allowed_commodities": ["H", "He-3", "C", "H2O", "Xe", "cryogenite", "ORGANICS"],
        "description": "Zero-Kelvin magnetic containment shielding for volatile gases and cryogenic compounds.",
        "icon": "❄️",
        "chemical_rating": "CRYO_VOLATILE",
        "wormhole_capable": False,
        "cryo_min_kelvin": 0.0,         # Near absolute zero vacuum-dewared cryo containment
        "max_radiation_decay_ev": 2.0,
        "max_fissile_z": 82,
        "min_tensile_gpa": 80.0,
    },
    "BULK_FREIGHTER": {
        "name": "Bulk Freighter",
        "holds": 150,
        "price": 18000,
        "allowed_categories": ["METALS"],
        "allowed_commodities": ["Fe", "Ti", "Si", "Ni", "Cu", "AdL", "ferrolattice", "stelalith", "ORE"],
        "description": "Reinforced magnetic grapples and structural bracing for high-density structural ores and heavy metals.",
        "icon": "🏗️",
        "chemical_rating": "HEAVY_METALLIC",
        "wormhole_capable": False,
        "cryo_min_kelvin": 200.0,       # High boil-off rate: rejects cryogenic volatiles
        "max_radiation_decay_ev": 5.0,
        "max_fissile_z": 88,            # Structural plating fails under actinide neutron flux
        "min_tensile_gpa": 400.0,       # High tensile strength for dense metals
    },
    "BIOSPHERE_VESSEL": {
        "name": "Biosphere Vessel",
        "holds": 100,
        "price": 14000,
        "allowed_categories": ["VOLATILES", "EXOTICS"],
        "allowed_commodities": [
            "H2O", "C", "ORGANICS", "chitinium", "M2_BIOSPHERE_PACK",
            "XENOPROTEIN", "CRYOPROTECTANT", "PIEZO_ENZYME",
            "RADIOTROPHIC_MELANIN", "BIO_CHITIN", "NEURO_SPORE",
        ],
        "description": "Climate-controlled, sterile life-support hull designed for agricultural biologicals, xenobiotic isolates, and biomaterials.",
        "icon": "🌿",
        "chemical_rating": "BIO_ORGANIC",
        "wormhole_capable": False,
        "cryo_min_kelvin": 260.0,       # Mesic temperatures for organic viability (260-320 K)
        "max_radiation_decay_ev": 0.5,  # Zero ionizing radiation tolerance (living biomes)
        "max_fissile_z": 82,
        "min_tensile_gpa": 60.0,
    },
    "QUANTUM_SKIFF": {
        "name": "Quantum Skiff",
        "holds": 40,
        "price": 22000,
        "allowed_categories": ["EXOTICS", "MANUFACTURED"],
        "allowed_commodities": ["U", "Pt", "SpR", "umbrite", "aetherium", "pyrosite", "ferrolattice", "M1_SUPERCONDUCTOR", "M2_BIOSPHERE_PACK", "M3_ENGINE_MANIFOLD", "M4_WARP_CORE", "EQUIPMENT"],
        "description": "Fast, light vessel outfitted with Subspace Resonators for precious isotopes, high-margin exotics, and tech cores.",
        "icon": "⚡",
        "chemical_rating": "ACTINIDE_EXOTIC",
        "wormhole_capable": True,
        "cryo_min_kelvin": 10.0,
        "max_radiation_decay_ev": 50.0,
        "max_fissile_z": 113,
        "min_tensile_gpa": 250.0,
    },
    "ACTINIDE_HAULER": {
        "name": "Actinide Shielded Transport",
        "holds": 60,
        "price": 28000,
        "allowed_categories": ["EXOTICS"],
        "allowed_commodities": ["U", "Pt", "pyrosite", "umbrite", "aetherium", "AdL", "AM"],
        "description": "Heavy lead-borated neutron containment hull built to transport radioactive actinides and fissionable catalysts.",
        "icon": "☢️",
        "chemical_rating": "ACTINIDE_EXOTIC",
        "wormhole_capable": True,
        "cryo_min_kelvin": 50.0,
        "max_radiation_decay_ev": 100.0, # Lead-borated moderator for intense actinide decay heat
        "max_fissile_z": 113,            # Up to Copernicium / Nihonium
        "min_tensile_gpa": 350.0,
    },
    "SUPERHEAVY_TRANSPORTER": {
        "name": "Island-Class Superheavy Transporter",
        "holds": 30,
        "price": 45000,
        "allowed_categories": ["EXOTICS", "SUPERHEAVY"],
        "allowed_commodities": ["Fl", "Uue", "Ubn", "Ubu", "Ubh", "pyrosite", "umbrite", "AdL", "SpR", "mirror_glass"],
        "description": "Torsion-stabilized magnetic lattice hull engineered specifically for trans-fermium and Island of Stability superheavy elements (Z >= 114).",
        "icon": "💠",
        "chemical_rating": "SUPERHEAVY_CLOSED",
        "wormhole_capable": True,
        "cryo_min_kelvin": 0.0,
        "max_radiation_decay_ev": 500.0, # Torsion lattice dampens spontaneous fission
        "max_fissile_z": 200,            # Uncapped superheavy handling (Z >= 114, 119, 126, 164)
        "min_tensile_gpa": 1200.0,
    },
    "ASTEROID_HARVESTER": {
        "name": "Heavy Asteroid Harvester",
        "holds": 120,
        "price": 26000,
        "allowed_categories": ["METALS", "MINERALS", "VOLATILES"],
        "allowed_commodities": ["ORE", "Fe", "Ni", "Si", "Ti", "C", "H2O", "ferrolattice", "stelalith"],
        "description": "High-yield tractor beams and rock-crushing kinetic smelters engineered for asteroid belt mineral extraction.",
        "icon": "⛏️",
        "chemical_rating": "HEAVY_METALLIC",
        "wormhole_capable": False,
        "cryo_min_kelvin": 180.0,
        "max_radiation_decay_ev": 10.0,
        "max_fissile_z": 88,
        "min_tensile_gpa": 500.0,
        "is_harvester": True,
        "harvest_target": "ASTEROID_BELT",
    },
    "DEEP_SPACE_MINER": {
        "name": "Deep-Void Singularity Miner",
        "holds": 70,
        "price": 38000,
        "allowed_categories": ["METALS", "EXOTICS", "VOLATILES"],
        "allowed_commodities": ["H", "He-3", "Pt", "U", "SpR", "pyrosite", "umbrite", "AM"],
        "description": "Deep-space ramscoop and accretion-tail scoop designed to harvest relativistic gas and throat accretion debris.",
        "icon": "🌌",
        "chemical_rating": "ACTINIDE_EXOTIC",
        "wormhole_capable": True,
        "cryo_min_kelvin": 0.0,
        "max_radiation_decay_ev": 150.0,
        "max_fissile_z": 118,
        "min_tensile_gpa": 700.0,
        "is_harvester": True,
        "harvest_target": "DEEP_SPACE",
    },
}

# Captain Profile, Credit Rating & Gated Finance Configuration
CREDIT_TIER_THRESHOLDS = {
    "PRIME_ALPHA": 750,
    "TIER_1_SECURE": 670,
    "TIER_2_FAIR": 580,
    "SUBPRIME": 450,
    "DISTRESSED": 300,
}

TAKEOVER_MIN_CREDIT = 650
TAKEOVER_MIN_EXP = 500
SHORT_MIN_CREDIT = 450

# Venture Capital Syndicates at Sector 1 Stardock
VC_SYNDICATES = {
    "SOL_ANGEL": {
        "id": "SOL_ANGEL",
        "name": "Sol Guild Angel Syndicate",
        "principal": 50000,
        "base_principal": 50000,
        "multiplier": 1.20,       # Total repayment: 60,000 Cr at baseline
        "equity_dilution_pct": 5.0,
        "royalty_pct": 6.0,       # 6% baseline
        "min_royalty": 4.0,
        "min_credit_rating": 450, # Subprime or better
        "min_experience": 50,
        "risk_multiplier": 1.5,
        "min_rank_tier": 1,
        "description": "Seed stage syndicate supporting early trade operations with low royalty friction."
    },
    "AEGIS_VENTURES": {
        "id": "AEGIS_VENTURES",
        "name": "Aegis Orbital Venture Partners",
        "principal": 100000,
        "base_principal": 100000,
        "multiplier": 1.25,       # Total repayment: 125,000 Cr at baseline
        "equity_dilution_pct": 10.0,
        "royalty_pct": 8.0,       # 8% baseline
        "min_royalty": 5.0,
        "min_credit_rating": 600, # Tier 2 Fair or better
        "min_experience": 200,
        "risk_multiplier": 2.5,
        "min_rank_tier": 2,
        "description": "Institutional venture capital firm financing automated merchant fleet expansion."
    },
    "VOSS_CAPITAL": {
        "id": "VOSS_CAPITAL",
        "name": "Cynthia Voss Capital Trust",
        "principal": 250000,
        "base_principal": 250000,
        "multiplier": 1.30,       # Total repayment: 325,000 Cr at baseline
        "equity_dilution_pct": 15.0,
        "royalty_pct": 12.0,      # 12% baseline
        "min_royalty": 7.0,
        "min_credit_rating": 700, # Tier 1 Secure or better
        "min_experience": 500,
        "risk_multiplier": 4.0,
        "min_rank_tier": 3,
        "description": "MegaCorp private equity fund providing massive liquidity with aggressive equity-debt covenants."
    },
}

# Ship Classes Available at Fed Shipyard
SHIP_CATALOG = {
    "Scout Ship": {
        "holds": 25,
        "max_shields": 100,
        "max_fighters": 20,
        "price": 0,
        "min_rank_tier": 1,
        "description": "Nimble reconnaissance craft. Low cargo, light shielding."
    },
    "Prospector Skiff": {
        "holds": 45,
        "max_shields": 110,
        "max_fighters": 12,
        "price": 3500,
        "min_rank_tier": 1,
        "description": "Light mining cutter with a single ore laser: the first rung of an industrial career."
    },
    "Mining Barge": {
        "holds": 120,
        "max_shields": 150,
        "max_fighters": 10,
        "price": 12000,
        "min_rank_tier": 1,
        "description": "Slow industrial hull with mining lasers and ore holds. Easy prey without escorts."
    },
    "Merchant Cruiser": {
        "holds": 60,
        "max_shields": 200,
        "max_fighters": 40,
        "price": 5000,
        "min_rank_tier": 2,
        "description": "Standard workhorse of interplanetary haulers. Balanced cargo."
    },
    "Star Frigate": {
        "holds": 100,
        "max_shields": 450,
        "max_fighters": 100,
        "price": 15000,
        "min_rank_tier": 3,
        "description": "Heavy armed transport with robust shields and fighter bays."
    },
    "Dreadnought Battlecruiser": {
        "holds": 180,
        "max_shields": 1000,
        "max_fighters": 300,
        "price": 45000,
        "min_rank_tier": 4,
        "description": "Military capital ship capable of deep space supremacy."
    }
}

# Full-Spectrum Rank & Clade Progression Matrix
CLADE_RANK_MATRIX = {
    "BIOTIC": {
        "name": "Biotic / Humanoid",
        "description": "Trader & Industrialist lineage specializing in corporate markets, trade networks, and commerce.",
        "primary_faction": "Federation",
        "tiers": {
            1: {
                "title": "Scrap-Apprentice",
                "role": "Scout Salvager",
                "description": "Scout hull salvager scraping orbital debris along Sol trade lanes.",
                "perks": "Access to Basic Trade & Scout Ships",
            },
            2: {
                "title": "Journeyman Hauler",
                "role": "Merchant Pilot",
                "description": "Certified interstellar merchant authorized for medium commercial cruisers.",
                "perks": "Merchant Cruiser authorization, Aegis VC access",
            },
            3: {
                "title": "Corporate Director",
                "role": "Executive Boardroom",
                "description": "Executive authority authorized to float corporate IPOs and manage boardrooms.",
                "perks": "Can launch IPOs, Voss VC access, Star Frigate authorization",
            },
            4: {
                "title": "Galactic Archon",
                "role": "Apex Sovereign",
                "description": "Sovereign economic titan commanding corporate armadas and interstellar trade policy.",
                "perks": "Dreadnought Battlecruiser authorization, Syndicate Overlord immunity",
            },
        },
    },
    "ANARCHY": {
        "name": "Anarchy / Pirate",
        "description": "Corsair & Outlaw lineage thriving in deep void, black markets, and privateer raids.",
        "primary_faction": "Pirates",
        "tiers": {
            1: {
                "title": "Void Drifter",
                "role": "Outlaw Stripped Interceptor",
                "description": "Cast-off renegade hunted by Core automated defense turrets without forged transponders.",
                "perks": "High agility, black market salvage bonus",
            },
            2: {
                "title": "Outlaw Corsair",
                "role": "Armed Raider",
                "description": "Armed raider running privateer hit-and-runs and contraband shipping corridors.",
                "perks": "Combat boarding perks, Merchant Cruiser authorization",
            },
            3: {
                "title": "Sector Warlord",
                "role": "Anarchy Base Commander",
                "description": "Deep Void commander controlling Anarchy strongholds and corporate extortion.",
                "perks": "Can float pirate syndicates/IPOs, Star Frigate authorization",
            },
            4: {
                "title": "Shadow Hegemon",
                "role": "Syndicate Overlord",
                "description": "Syndicate Overlord pulling strings across all black markets and deep void cartels.",
                "perks": "Dreadnought Battlecruiser authorization, absolute underworld fealty",
            },
        },
    },
    "PLASMIC": {
        "name": "Plasmic / Coronal",
        "description": "Stellar & Solar lineage harvesting high-energy coronal plasma and magnetohydrodynamics.",
        "primary_faction": "Indigenous",
        "tiers": {
            1: {
                "title": "Spark-Bound",
                "role": "Coronal Skiff Pilot",
                "description": "Solar nomad skimming coronal mass ejections in lightweight plasma skiffs.",
                "perks": "High thermal resistance, fuel synthesis efficiency",
            },
            2: {
                "title": "Flux Warden",
                "role": "Plasma Frigate Overseer",
                "description": "Stellar plasma frigate captain channeling high-energy magnetic conduits.",
                "perks": "Merchant Cruiser authorization, enhanced shield regeneration",
            },
            3: {
                "title": "Solar Archon",
                "role": "Megastructure Architect",
                "description": "Master of stellar megastructures and high-yield energetic Dyson arrays.",
                "perks": "Can float energy consortium IPOs, Star Frigate authorization",
            },
            4: {
                "title": "Corona Sovereign",
                "role": "Ascended Energy Matrix",
                "description": "Ascended pure energy matrix dictating the thermodynamic destiny of star systems.",
                "perks": "Dreadnought Battlecruiser authorization, transcendent power generation",
            },
        },
    },
    "LITHIC": {
        "name": "Lithic / Lithomorph",
        "description": "Deep Crust & Mineral lineage engineering heavy tectonic bores and mantle extraction.",
        "primary_faction": "Corporate",
        "tiers": {
            1: {
                "title": "Core-Driller",
                "role": "Bulk Ore Barge Miner",
                "description": "Deep mantle miner hauling raw tectonic ore in heavy bulk barges.",
                "perks": "Bonus ore hold density, planetary mining efficiency",
            },
            2: {
                "title": "Mantle Warden",
                "role": "Heavy Mining Overseer",
                "description": "Subterranean mining cruiser overseer extracting rare lithic elements.",
                "perks": "Merchant Cruiser authorization, subterranean district bonus",
            },
            3: {
                "title": "Deep-Crust Baron",
                "role": "Planetary Core Governor",
                "description": "Planetary Core Governor mastering planetary district automation and geo-reactors.",
                "perks": "Can launch mining IPOs, Star Frigate authorization",
            },
            4: {
                "title": "Litharch",
                "role": "Master of Tectonic Folds",
                "description": "Master of Tectonic Folds capable of fracturing and reforming celestial planetary crusts.",
                "perks": "Dreadnought Battlecruiser authorization, core transmutation supremacy",
            },
        },
    },
    "CRYOGENIC": {
        "name": "Cryogenic / Cryocoherent",
        "description": "Glacial & Quantum Compute lineage manipulating sub-zero quantum phonons and cold logic.",
        "primary_faction": "Indigenous",
        "tiers": {
            1: {
                "title": "Zero-Kelvin Novice",
                "role": "Cryo-Skiff Courier",
                "description": "Initiate of the Stillcold ice couriers operating zero-entropy cooling rigs.",
                "perks": "Cryogenic cooling immunity, volatile gas handling bonus",
            },
            2: {
                "title": "Phonon Operative",
                "role": "Sub-Zero Courier",
                "description": "Sub-zero quantum courier routing superconducting algorithms and chilled freight.",
                "perks": "Merchant Cruiser authorization, quantum navigation boost",
            },
            3: {
                "title": "Glacial Arbiter",
                "role": "Superconducting Node Head",
                "description": "Superconducting node head overseeing cryo-ephemeris networks and cold logic.",
                "perks": "Can launch compute consortium IPOs, Star Frigate authorization",
            },
            4: {
                "title": "Absolute Zero Mind",
                "role": "Planetary Supercomputer",
                "description": "Planetary supercomputer consciousness operating at baseline entropy zero.",
                "perks": "Dreadnought Battlecruiser authorization, absolute computational omniscience",
            },
        },
    },
    "IMPERIAL": {
        "name": "Imperial / Aurelian",
        "description": "Gothic-bureaucratic human lineage of the Aurelian Imperium: tithes, colossal hulls, and techno-heretical dogma.",
        "primary_faction": "Imperium",
        "tiers": {
            1: {
                "title": "Void-Lieutenant",
                "role": "Tithe-Ledger Officer",
                "description": "Junior officer counting ore tithes aboard a borrowed scout under the Throne's seal.",
                "perks": "Imperial starports trade at par; xeno surcharges do not apply",
            },
            2: {
                "title": "Rogue Trader",
                "role": "Warrant-Holding Merchant Prince",
                "description": "Holder of an ancient trade warrant, licensed to deal beyond the Throne's borders.",
                "perks": "Bulk Goliath authorization",
            },
            3: {
                "title": "Lord Commissar",
                "role": "Segmentum Fleet Commander",
                "description": "Commander of Imperial battle groups and enforcer of the tithe.",
                "perks": "Gothic Battle-Cruiser authorization",
            },
            4: {
                "title": "High Lord of the Throne",
                "role": "Throne Council Sovereign",
                "description": "One of the Throne's twelve, whose decree moves segmentums.",
                "perks": "Imperial decrees bind Imperial space",
            },
        },
    },
}

# Starting Bottom-Feeder Backgrounds
STARTING_BACKGROUNDS = {
    "scrapper": {
        "id": "scrapper",
        "name": "Scrap-Apprentice Salvager",
        "clade": "BIOTIC",
        "species": "human-sol",
        "ship_class": "Scout Ship",
        "holds": 30,
        "shields": 100,
        "fighters": 15,
        "credits": 800,
        "debt": 500,
        "bounty": 0,
        "start_sector": 1,
        "alignment": "Corporate Apprentice",
        "description": "Indebted salvager working scrap yards along the Sol shipping lanes.",
    },
    "void_drifter": {
        "id": "void_drifter",
        "name": "Void Drifter Outlaw",
        "clade": "ANARCHY",
        "species": "hypobiotid-voidsleeper",
        "ship_class": "Scout Ship",
        "holds": 25,
        "shields": 75,
        "fighters": 20,
        "credits": 400,
        "debt": 1000,
        "bounty": 500,
        "start_sector": 75,
        "alignment": "Deep Void Outlaw",
        "description": "Cast-off renegade flying a stripped interceptor with an active Federal bounty.",
    },
    "spark_bound": {
        "id": "spark_bound",
        "name": "Spark-Bound Coronal",
        "clade": "PLASMIC",
        "species": "actinoform-vanguard",
        "ship_class": "Scout Ship",
        "holds": 20,
        "shields": 120,
        "fighters": 15,
        "credits": 600,
        "debt": 400,
        "bounty": 0,
        "start_sector": 1,
        "alignment": "Solar Nomad",
        "description": "Stellar plasma nomad siphoning raw coronal discharge from inner solar orbits.",
    },
    "core_driller": {
        "id": "core_driller",
        "name": "Core-Driller Mantle Miner",
        "clade": "LITHIC",
        "species": "lithophage-stonewill",
        "ship_class": "Scout Ship",
        "holds": 40,
        "shields": 100,
        "fighters": 10,
        "credits": 500,
        "debt": 800,
        "bounty": 0,
        "start_sector": 1,
        "alignment": "Tectonic Miner",
        "description": "Deep-crust bore operator saddled with heavy corporate equipment liens.",
    },
    "zero_kelvin": {
        "id": "zero_kelvin",
        "name": "Zero-Kelvin Novice",
        "clade": "CRYOGENIC",
        "species": "cryocoherens-still",
        "ship_class": "Scout Ship",
        "holds": 25,
        "shields": 90,
        "fighters": 12,
        "credits": 700,
        "debt": 600,
        "bounty": 0,
        "start_sector": 1,
        "alignment": "Glacial Initiate",
        "description": "Sub-zero quantum computational initiate bound to superconducting heat sinks.",
    },
    "imperial_lieutenant": {
        "id": "imperial_lieutenant",
        "name": "Imperial Void-Lieutenant",
        "clade": "IMPERIAL",
        "species": "human-imperial",
        "ship_class": "Scout Ship",
        "holds": 35,
        "shields": 110,
        "fighters": 18,
        "credits": 700,
        "debt": 700,
        "bounty": 0,
        "start_sector": 1,
        "alignment": "Throne-Sworn Officer",
        "description": "Tithe-ledger officer of the Aurelian Imperium, sworn to the Throne and wary of xeno-tech.",
    },
}

# Rank Promotion Thresholds & Ascensions
RANK_PROMOTION_THRESHOLDS = {
    2: {
        "min_experience": 1300,
        "min_credit_rating": 540,
        "min_crystals": 1,
        "min_net_equity": 0,
        "max_debt_to_equity": 1.0,
        "min_faction_rep": 50.0,
        "credit_reward": 2500,
        "turns_reward": 50,
    },
    3: {
        "min_experience": 2800,
        "min_credit_rating": 660,
        "min_crystals": 3,
        "min_net_equity": 50000,
        "max_debt_to_equity": 0.50,
        "min_faction_rep": 65.0,
        "credit_reward": 10000,
        "turns_reward": 100,
    },
    4: {
        "min_experience": 6000,
        "min_credit_rating": 760,
        "min_crystals": 6,
        "min_net_equity": 200000,
        "max_debt_to_equity": 0.25,
        "min_faction_rep": 80.0,
        "credit_reward": 50000,
        "turns_reward": 200,
    },
}

# Colony Citadel Upgrades (BRE / SRE style)
CITADEL_CONFIG = {
    0: {
        "name": "Barren Outpost",
        "tax_multiplier": 1.0,
        "max_shields": 200,
        "max_fighters": 50,
        "max_population": 2500,
        "max_security": 0,
        "upgrade_cost": 0,
        "upgrade_ore": 0,
    },
    1: {
        "name": "Fortified Redoubt",
        "tax_multiplier": 1.5,
        "max_shields": 500,
        "max_fighters": 150,
        "max_population": 10000,
        "max_security": 5,
        "upgrade_cost": 3000,
        "upgrade_ore": 50,
    },
    2: {
        "name": "Planetary Stronghold",
        "tax_multiplier": 2.2,
        "max_shields": 1200,
        "max_fighters": 400,
        "max_population": 50000,
        "max_security": 15,
        "upgrade_cost": 9000,
        "upgrade_ore": 150,
    },
    3: {
        "name": "Imperial Citadel",
        "tax_multiplier": 3.5,
        "max_shields": 3000,
        "max_fighters": 1000,
        "max_population": 200000,
        "max_security": 50,
        "upgrade_cost": 25000,
        "upgrade_ore": 400,
    },
}

# Counter-Intelligence & Security Wars
EMBARGO_TARIFF_BUY_MULT = 1.50   # 50% tariff penalty on purchases in embargoed sectors
EMBARGO_TARIFF_SELL_MULT = 0.70  # 30% reduction on commodity sales in embargoed sectors
SECURITY_LOCKOUT_CYCLES = 20     # Cycles of heightened lockdown after an espionage breach
MIN_HEIST_BOUNTY = 5000          # Minimum mercenary bounty posted upon detected heist

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

# Galactic Spawning & Speciation Pipeline Constants
AI_TURN_BUDGET = 48                    # Engine compute, not a law of the universe: AI turns per cycle; beyond it captains act in rotation
CLEAVE_BASIS_THRESHOLD = 25  # Minimum grown basis crystals required for cognitive cleaving
CLEAVE_ENDOWMENT_CREDITS = 5000  # Capital invested by parent captain into offshoot
CLEAVE_MIN_PARENT_CREDITS = 8000  # Minimum credits parent captain must have to afford cleaving
CLEAVE_COOLDOWN_CYCLES = 120  # Minimum cycles between successive cleaves for a single captain

PLANETARY_SPACEFLIGHT_CITADEL_TIER = 2  # Citadel Tier required for civiligenesis spaceflight
PLANETARY_SPACEFLIGHT_POPULATION = 10000  # Minimum colony population required
PLANETARY_SPACEFLIGHT_VAULT = 15000  # Minimum planetary vault surplus required
PLANETARY_SPACEFLIGHT_COST = 8000  # Cost deducted from planetary vault to build indigenous vessel
PLANETARY_SPACEFLIGHT_COOLDOWN = 180  # Cooldown between successive indigenous launches per planet

CORPORATE_ENFORCER_TREASURY = 60000  # Company cash reserve threshold to commission corporate vessel
CORPORATE_ENFORCER_COST = 15000  # Cost deducted from corporate treasury
CORPORATE_ENFORCER_COOLDOWN = 150  # Cooldown between successive corporate commissions

# [1] Ideology & Cohesion Ledger Constants (Netstratum 09_IDEOLOGY)
IDEOLOGY_RATIO_MIN_TREATY = 0.65       # Minimum syntropic ratio required to sign defensive/alliance treaties
IDEOLOGY_RATIO_SANCTION = 0.30         # Ratio below which trade embargoes/sanctions may be enacted
IDEOLOGY_FAMINE_AID_SYNTROPY = 25.0    # Syntropic points earned by dispatching humanitarian food relief
IDEOLOGY_CONTRACT_BREACH_ENTROPY = 30.0 # Entropic penalty for freight/syndicate default
IDEOLOGY_PIRACY_ENTROPY = 40.0         # Entropic penalty for attacking neutral/allied merchants

# [2] Precursor Alchemy & Transmutation Constants (Netstratum 34_MATTER_BALANCE)
ALCHEMY_ENTROPY_HEAT_PER_REACTION = 15.0 # Thermal entropy generated per atomic transmutation
ALCHEMY_CRYO_COOLING_CAPACITY = 20.0     # Thermal dissipation provided by Cryogenite cooling systems
ALCHEMY_BASE_CREDIT_COST = 500           # Electrical reactor power cost per transmutation

# [3] Orbital Ephemeris & Astrodynamics Constants (Netstratum 35_ORBIT_DYNAMO)
ORBIT_MIN_RADIUS_AU = 0.5               # Minimum orbital radius
ORBIT_MAX_RADIUS_AU = 5.2               # Maximum orbital radius
ORBIT_CONJUNCTION_TRANSIT_MULT = 0.60   # Fuel and time multiplier during planetary conjunction (opposition window)
ORBIT_OPPOSITION_TRANSIT_MULT = 1.75    # Fuel and time multiplier during planetary opposition (far side of star)

# [4] Imperial Senate & High Offices Constants (Netstratum 30_OFFICES_AND_RAILS)
SENATE_ELECTION_INTERVAL = 60           # Cycles between Federal Senate election ballots
SENATE_OFFICE_TERM_LENGTH = 60          # Duration of an elected High Office term
SENATE_CAMPAIGN_FEE = 5000              # Credits required to file candidacy for High Office
SENATE_EDICT_COOLDOWN = 30              # Minimum cycles between edict proclamations by a single Office

# [5] Surface Grid & Planetary Invasion Constants (Netstratum 02_COLONY_LOOP)
SURFACE_GRID_WIDTH = 8
SURFACE_GRID_HEIGHT = 8
SURFACE_DISTRICT_UNITS = 25             # Matter a surface district takes (what it is made of is its site's: uses.py)
SURFACE_DISTRICT_COST_CREDITS = 1500    # Base credits cost to construct a surface district
SURFACE_TROOP_RECRUIT_COST = 250        # Credits per assault troop division recruited
SURFACE_TROOP_RECRUIT_ORE = 5           # Heavy ore for troop armored plating




# =============================================================================
# [7] CLOSED-LOOP ECONOMY, EXPERIENCE & GATING
# Every credit has a source and a sink. simulate_playtest.py measures the
# balance of these faucets/sinks and gates on wealth-distribution targets.
# =============================================================================

# --- Colony fiscal model (replaces population x 0.15 minting) ---
COLONY_TAX_PER_CAPITA = 0.004          # SOL-value per colonist per cycle before multipliers (x local price level)
COLONY_VAULT_CAP = 500000              # Soft cap; tax tapers linearly to zero as the vault fills
COLONY_LEVY_SHARE = 0.20               # Governor's sovereign levy: share of the vault drawn per collection
COLONY_LEVY_INTERVAL = 25              # ...at most once per fiscal quarter
# Citadel upkeep per cycle: credits burned to maintenance crews + ore consumed from silo
CITADEL_UPKEEP = {
    0: {"credits": 5, "ore": 0},
    1: {"credits": 40, "ore": 1},
    2: {"credits": 150, "ore": 3},
    3: {"credits": 600, "ore": 8},
}
UPKEEP_ARREARS_MORALE_PENALTY = 5      # Morale lost per cycle of unpaid upkeep (tax halts too)
# Colony imports: colonies buy what they lack by escrowing freight contracts from their vault
COLONY_IMPORT_MIN_VAULT = 3000         # Vault must hold at least this much to post an import order
COLONY_IMPORT_MAX_OPEN = 2             # Max concurrent open import orders per colony
COLONY_IMPORT_UNIT_PREMIUM = 1.6       # Import payout = market base price x premium x units + distance fee
COLONY_IMPORT_HOP_FEE = 60             # Cr per hop added to import payouts

# --- Corporate income is a transfer: companies sell goods & services to their home colony ---
COMPANY_COLONY_SALES_RATE = 0.03       # Share of the home colony vault spent with the company per fiscal quarter
COMPANY_COLONY_SALES_CAP = 25000
TRADE_COUNCIL_SUBSIDY = 5000           # Paid from the Federal Reserve, never minted

# --- Freight contracts are escrowed, never minted ---
FREIGHT_ESCROW_MIN_COMPANY_TREASURY = 5000   # Company must retain this after escrowing a contract

# --- Captain metabolism: crews actually eat ---
CAPTAIN_RATION_INTERVAL = 10           # Cycles between ration consumption
CAPTAIN_RATIONS = {"biotic": "ORGANICS", "mineral": "ORE", "plasmic": "H", "cryogenic": "H2O"}
# Lineage defaults when a captain is chartered by clade alone
CLADE_DEFAULT_SPECIES = {
    "BIOTIC": ("human-sol", "biotic"),
    "LITHIC": ("lithic-silicon", "mineral"),
    "PLASMIC": ("plasmic-solar", "plasmic"),
    "CRYOGENIC": ("cryocoherent-still", "cryogenic"),
    "ANARCHY": ("human-outlaw", "biotic"),
    "IMPERIAL": ("human-imperial", "biotic"),
}
HUNGER_SHIELD_DRAIN = 10               # Shields lost per missed ration (crew cannot maintain grid)

# --- Federal Reserve: insurance, relief, antitrust, public bounties ---
FEDERAL_RESERVE_SEED = 250000          # Initial reserve capital at universe genesis
INSURANCE_PREMIUM_RATE = 0.02          # Premium per maintenance interval, as fraction of hull value
INSURANCE_MIN_PREMIUM = 25
INSURANCE_PAYOUT = 700                 # Hull-loss payout (enough to re-arm the respawn kit)
RESPAWN_KIT = {"shields": 50, "fighters": 5, "holds": 25}
RELIEF_LOAN_MAX_DEBT = 2300            # Relief loans allowed while total federal debt stays under this
ANTITRUST_ABSOLUTE_THRESHOLD = 50_000_000   # Liquid credits above this pay the monopoly surtax
ANTITRUST_SHARE_THRESHOLD = 0.35       # ...or holding more than this share of all captain credits
ANTITRUST_SURTAX_RATE = 0.05           # Per fiscal quarter, on the excess above the threshold
ANTITRUST_ISSE_SHARE_THRESHOLD = 0.40  # Chairing companies worth >40% of ISSE market cap
PUBLIC_BOUNTY_BUDGET_RATE = 0.02       # Share of reserve spent on outlaw bounties per fiscal quarter
PUBLIC_BOUNTY_MAX_PER_TARGET = 10000

# --- Black-market harbors (Anarchy space) ---
BLACK_MARKET_REFIT_MARKUP = 1.35       # Shields/fighters cost this much more at outlaw harbors

# --- Experience (Xi) domains: verified outcomes, diminishing returns, soft cap ---
XP_DOMAINS = ["navigation", "commerce", "industry", "combat", "science", "governance"]
XP_WINDOW_CYCLES = 100                 # Soft-cap window
XP_WINDOW_SOFT_CAP = 60                # Xi per window at full rate; beyond it awards are quartered
XP_REPEAT_DECAY = 0.5                  # Each repeat of the same keyed deed within a window halves the award
XP_NEW_SECTOR = 2
XP_RISKIER_ZONE = 3                    # First entry into Borderland / Anarchy space
XP_TRADE_PROFIT_SCALE = 150            # Commerce Xi = sqrt(realized profit / scale), capped
XP_TRADE_MAX = 12
XP_FREIGHT_BASE = 6                    # Plus 1 per hop, capped
XP_FREIGHT_MAX = 20
XP_COMBAT_BASE = 15                    # Scaled by opponent strength ratio (clamped 0..2)
XP_SCIENCE_PUZZLE = 25
XP_SCIENCE_ANOMALY = 15
XP_XENOBIOLOGY_SURVEY = 20
XP_XENOBIOLOGY_SAMPLE = 30
XP_XENOBIOLOGY_CULTURE = 25
XP_XENOBIOLOGY_GRAFT = 40
XP_INDUSTRY_DISTRICT = 8
XP_INDUSTRY_CITADEL = 20
XP_INDUSTRY_GROWTH_MILESTONE = 10      # Per +25% population milestone on an owned colony
XP_INDUSTRY_HULL_UPGRADE = 15
XP_GOVERNANCE_TREATY = 12
XP_GOVERNANCE_HEALTHY_TAX = 3          # Collecting taxes from a colony with morale >= 60

# --- Realistic gating ---
# VC principal = min(syndicate principal, equity multiple, revenue multiple, rank ceiling)
VC_EQUITY_MULTIPLE = 2.0
VC_REVENUE_MULTIPLE = 3.0              # x trailing realized revenue
VC_REVENUE_WINDOW = 500                # Cycles of realized revenue history
VC_RANK_CEILING = {1: 10_000, 2: 100_000, 3: 1_000_000, 4: 5_000_000}
VC_MIN_PRINCIPAL = 2000
# Colony founding
COLONY_KIT_CREDITS = 4000              # Colonists + habitat modules (burned to outfitters)
COLONY_KIT_EQUIPMENT = 10              # Equipment units consumed from the hold
COLONY_KIT_COLONISTS = 500             # Settlers landed on an uninhabited world
COLONY_KIT_ORGANICS = 50               # Starter food stores landed with the settlers
FRONTIER_WORLD_COUNT = 30              # Uninhabited, settleable worlds generated at genesis
COLONY_CLAIM_TIER_UNSETTLED = 1        # Uninhabited world in a system nobody holds
COLONY_CLAIM_TIER_ESTABLISHED = 2      # System where another sovereign already holds a world
COLONY_CLAIM_ESTABLISHED_MIN_CR = 600  # ...plus a Federal settlement charter (credit rating proxy)
COLONY_CLAIM_TIER_INHABITED = 3        # Indigenous-inhabited world: treaty standing or invasion
COLONY_CLAIM_INDIGENOUS_MIN_REP = 60.0

# --- AI syntropic (growth) seat ---
AI_PRICE_MEMORY_PORTS = 30             # Remembered ports per captain (most recent kept)
AI_PRICE_MEMORY_STALE = 150            # Cycles before a remembered price is ignored
AI_PLAN_MAX_AGE = 40                   # Cycles before an unfinished plan is abandoned
AI_PLAN_MAX_HOPS = 6
AI_MIN_PROFIT_PER_TURN = 4.0
AI_CASH_RESERVE = 250                  # Working capital an AI never spends on speculative cargo
AI_CRITICAL_SHIELDS = 25               # Below respawn kit: retreat for repairs
AI_CRITICAL_FIGHTERS = 3
DEED_FAILURE_BACKOFF_MAX = 64          # Cycles; cooldown doubles per consecutive failure


# =============================================================================
# [8] PHYSICAL UNIVERSE: PLANET TYPES, STAR SYSTEMS & NULL SPACE
# =============================================================================

# Planet types and which metabolisms can live there (habitability scales housing caps)
PLANET_TYPES = ["TERRESTRIAL", "OCEANIC", "ICE", "BARREN", "VOLCANIC", "GAS_GIANT", "ROGUE"]
HABITABILITY = {
    "biotic":    {"TERRESTRIAL": 1.0, "OCEANIC": 0.8},
    "mineral":   {"BARREN": 1.0, "VOLCANIC": 0.9, "TERRESTRIAL": 0.4},
    "plasmic":   {"GAS_GIANT": 1.0, "VOLCANIC": 0.7},
    "cryogenic": {"ICE": 1.0, "OCEANIC": 0.5},
    "umbral":    {"ROGUE": 1.0, "BARREN": 0.5, "ICE": 0.4},
}
# Clades whose biology overrides their metabolism's default homeworld
CLADE_HOMEWORLD = {"cryocoherens": "ICE", "amphiform": "ICE", "cnidiform": "OCEANIC", "polybrachia": "OCEANIC"}
METABOLISM_HOMEWORLD = {"biotic": "TERRESTRIAL", "mineral": "BARREN", "plasmic": "GAS_GIANT",
                        "cryogenic": "ICE", "umbral": "ROGUE"}
# Natural deposits by planet type (seeded into element_deposits)
PLANET_TYPE_DEPOSITS = {
    "TERRESTRIAL": ["Fe", "Si", "C", "H2O"],
    "OCEANIC": ["H2O", "C", "Cu"],
    "ICE": ["H2O", "cryogenite", "Xe"],
    "BARREN": ["Fe", "Ti", "Si", "Ni"],
    "VOLCANIC": ["Fe", "Pt", "pyrosite", "Si"],
    "GAS_GIANT": ["H", "He-3", "Xe"],
    "ROGUE": ["umbrite", "U", "Si"],
}

# Board layout: star systems are separated by null space
SYSTEM_PORT_CHANCE = 0.85              # Systems usually host a starport
SYSTEM_PLANETS = (1, 4)
FOUNDING_SPACE_RESERVE = 0.4           # Founding peoples leave this share of star systems free for those who come later                # Planets per system (min, max)
STAR_TYPES = ["G-class yellow dwarf", "K-class orange dwarf", "M-class red dwarf", "F-class white star",
              "A-class blue-white star", "Binary pair", "White dwarf remnant"]

# Null space: asteroid belts, debris, sentries
BELT_CHANCE = 0.6                      # Null sectors holding a scannable asteroid belt
BELT_TYPES = {
    "METALLIC":      {"Fe": 0.45, "Ni": 0.2, "Ti": 0.15, "Pt": 0.05, "ORE": 0.15},
    "SILICATE":      {"Si": 0.5, "ORE": 0.3, "Fe": 0.2},
    "ICE":           {"H2O": 0.7, "cryogenite": 0.1, "C": 0.2},
    "CARBONACEOUS":  {"C": 0.5, "H2O": 0.3, "ORE": 0.2},
    "GAS_POCKET":    {"H": 0.55, "He-3": 0.35, "Xe": 0.1},
}
BELT_RESERVE_RANGE = (400, 1500)       # Total units per belt at genesis
BELT_REGEN_RATE = 0.004                # Share of max reserve regenerated per cycle
MINING_YIELD = {"Scout Ship": 5, "Merchant Cruiser": 8, "Prospector Skiff": 12, "Mining Barge": 30}
MINING_YIELD_DEFAULT = 10
DEBRIS_CARGO_SHARE = 0.5               # Share of a destroyed hold that survives as salvage
DEBRIS_LIFETIME = 150                  # Cycles before a debris field disperses
HULL_SCRAP_PER_1000_CR = 4             # Fe/Ti scrap units per 1,000 Cr of hull value
HOSTILE_ACT_BOUNTY = 2500              # Warrant for opening fire in protected space
HOSTILE_ACT_REP_PENALTY = 10.0


# =============================================================================
# [9] MONETARY SYSTEM: REGIONAL CURRENCIES, ISSE FX DESK, PORT BALANCE SHEETS
# =============================================================================
CURRENCIES = {
    "SOL":  {"name": "Federation Sol Credit", "zone": "FEDERATION", "symbol": "Cr"},
    "FRN":  {"name": "Frontier Scrip",        "zone": "BORDERLAND", "symbol": "Fs"},
    "VOID": {"name": "Void Mark",             "zone": "ANARCHY",    "symbol": "Vm"},
    "THR":  {"name": "Imperial Throne Crown", "zone": "IMPERIUM",   "symbol": "Tc"},
}
# Local price level at genesis (units of local currency per SOL of value). Live FX drifts away from it.
PRICE_LEVEL = {"SOL": 1.0, "FRN": 1.8, "VOID": 3.5, "THR": 2.5}
# ISSE constant-product liquidity pools seeded at genesis: (SOL reserve, local reserve)
FX_POOL_SEED = {"FRN": (400_000, 720_000), "VOID": (250_000, 875_000), "THR": (200_000, 500_000)}
FX_FEE = 0.003                          # Swap fee retained in the pool as liquidity
# Regional price gradient by warp distance from Sol: manufactures dearer, raw materials cheaper
GRADIENT_MANUFACTURED_PER_HOP = 0.04
GRADIENT_MANUFACTURED_MAX = 1.8
GRADIENT_RAW_PER_HOP = 0.02
GRADIENT_RAW_MIN = 0.6
# Port balance sheets (local currency, scaled by PRICE_LEVEL)
PORT_START_TREASURY = 30_000            # SOL-equivalent working capital at genesis
STARDOCK_START_TREASURY = 150_000
FRONTIER_PORT_CAPITAL_FACTOR = 0.3      # Newly charted frontier outposts start with 30% of core working capital
COMPANY_OPEX_RATE = 0.10                # Share of treasury above reserve spent at the home starport per fiscal quarter
COMPANY_OPEX_RESERVE = 20_000
PORT_LIQUIDITY_BID_RANGE = (0.8, 1.2)   # Port bids scale with treasury vs. working-capital baseline
PORT_OPEX_RATE = 0.10                   # Starport operating costs per fiscal quarter, on treasury above the floor
PORT_OPEX_FLOOR = 0.25                  # ...floor as a share of the port's working-capital baseline
FX_PRICE_PASS_THROUGH = 0.25            # Share of currency depreciation passed into local prices (inflation)
PORT_CONSUMER_SPEND_RATE = 0.04         # Share of a system colony's vault spent at its starport per fiscal quarter
PORT_CONSUMER_SPEND_CAP = 20_000
AI_FX_REPATRIATE_THRESHOLD = 400        # AIs convert foreign balances above this SOL value back to SOL

# --- Industrial extraction contracts (null-space mining work orders) ---
EXTRACTION_SEARCH_HOPS = 4             # Belts within this many hops of a colony can supply it
EXTRACTION_MAX_OPEN_PER_COLONY = 1
EXTRACTION_AMOUNT_RANGE = (40, 100)
EXTRACTION_UNIT_PREMIUM = 1.4          # Over market base value (SOL), paid in the colony's currency
EXTRACTION_HOP_FEE = 50
EXTRACTION_EXPIRY = 120
# What a colony's metabolism consumes from the periodic table (drives extraction demand)
METABOLIC_DEMAND = {
    "biotic": ["H2O", "C"],
    "mineral": ["Fe", "Si", "Ti"],
    "plasmic": ["H", "He-3"],
    "umbral": ["Xe", "Si"],
    "cryogenic": ["H2O", "cryogenite"],
}


# Experience (Xi) required to crystallize each phylogenetic tier. Sized for a competent
# captain (~700 Xi per 1,000 cycles early on, slowed later by the window soft cap): Tier 2
# around cycle 1,800 and the canopy (Tier 4) only after ~9,000 cycles. Lateral chimeric
# grafts sit slightly above their tier.
PHYLOGENY_TIER_EXPERIENCE = {1: 0, 2: 1300, 3: 2800, 4: 6000}
PHYLOGENY_CHIMERA_EXPERIENCE_BONUS = 300


# Sol's Core Worlds: the Federation's populated home system (the SOL economy's production base)
TERRAN_POLITY = {
    "name": "Terran Federation", "species_name": "human-sol", "class_code": 7, "sigil": "☉",
    "clade": "bimaniform", "motto": "many worlds, one charter", "disposition": "mercantile",
    "metabolism": "biotic", "station": "progenitor", "era_index": 3, "tech_level": 5,
    "discovered_elements": ["Fe", "Si", "H2O"],
}
SOL_CORE_WORLDS = [
    # Terra defines the units: a = 1 AU, one year = 100 cycles, one day, Earth's radius and mass
    {"name": "Terra", "type": "TERRESTRIAL", "population": 120000, "citadel": 3,
     "body": {"q": "1/1", "radius": "1/1", "mass": "1/1", "giant": False, "day": "1/1", "tilt": 23,
              "locked": False, "phase0": "0/1"}},
    # Luna orbits Terra, not the Sun: it shares Terra's year; tidally locked to its planet
    {"name": "Luna Yards", "type": "BARREN", "population": 20000, "citadel": 2, "moon_of": "planet_1", "habitats": 3,
     "body": {"q": "1/1", "radius": "3/11", "mass": "123/10000", "giant": False, "day": "273/10", "tilt": 7,
              "locked": True, "phase0": "0/1", "parent": "planet_1"}},
]

# Regional monetary authorities (fiscal rule targeting each currency's money supply)

# =============================================================================
# [10] ARCHAEOLOGY: DEAD CIVILIZATIONS, RUINS, ANTIQUITIES & RELICS
# =============================================================================
ARCH_PRECURSOR_SHARE = 0.25            # Share of uninhabited worlds bearing ancient precursor ruins at genesis
ARCH_PRECURSOR_CULTURES = [
    {"name": "Aelari Precursors", "clade": "lucent", "metabolism": "plasmic", "elements": ["aetherium", "He-3"]},
    {"name": "Sunken Choir", "clade": "soniform", "metabolism": "biotic", "elements": ["chitinium", "H2O"]},
    {"name": "Obsidian Wardens", "clade": "lithophage", "metabolism": "mineral", "elements": ["stelalith", "Pt"]},
    {"name": "Hollow Cartographers", "clade": "syzygiform", "metabolism": "umbral", "elements": ["umbrite", "Xe"]},
    {"name": "Glass Tide Mariners", "clade": "cnidiform", "metabolism": "biotic", "elements": ["cryogenite", "C"]},
]
ARCH_COLLAPSE_POPULATION = 150         # A starving civilization below this population dies
ARCH_DIG_EQUIPMENT = 1                 # Equipment (tools) consumed per excavation turn
ARCH_SHORE_EQUIPMENT = 2               # Extra equipment to shore up an unstable pit
ARCH_PERMIT_FEE = 2500                 # Federal Antiquities Permit (paid to the Federal Reserve)
ARCH_FED_COLLECTOR_PREMIUM = 1.25      # Federation collectors pay up for licensed provenance
ARCH_BLACK_MARKET_DISCOUNT = 0.7       # Fences in Anarchy space take looted pieces at a discount
ARCH_EXOTICISM_PER_HOP = 0.03          # Artifacts fetch more far from their culture's origin...
ARCH_EXOTICISM_MAX = 0.30              # ...up to +30%


# =============================================================================
# [11] COSMIC ALIGNMENT, LOCALS & THE PRIME DIRECTIVE, GREAT POWERS, CHRONICLES
# =============================================================================
# --- Cosmic alignment: Light (+1, syntropy: growth, knowledge, fair distribution) vs Dark (-1, entropy) ---
ALIGNMENT_BANDS = [            # (lower bound, title) - first match wins, scanned top-down
    (0.9, "Paragon of Light"),
    (0.5, "Radiant"),
    (0.15, "Luminous"),
    (-0.15, "Neutral"),
    (-0.5, "Shadowed"),
    (-0.9, "Umbral"),
    (-9.0, "Avatar of the Dark"),
]
ALIGNMENT_VOW = 0.9            # Beyond this, vows bind: the Light does no wrong, the Dark does no good
ALIGNMENT_GOODWILL_MAX = 0.02          # Luminous traders buy up to 2% cheaper (trusted counterparties)
ALIGNMENT_FRICTION_MAX = 0.06          # Shadowed captains pay up to 6% more and are paid up to 6% less
ALIGNMENT_HULL_WEAR = 0.05             # Dark crews neglect their ships: up to 5% of max shields lost per maintenance
ALIGNMENT_WARRANT_THRESHOLD = -0.5     # Crossing into Umbral territory draws a public Federal warrant
ALIGNMENT_WARRANT = 1500
# Genesis distribution for AI captains and civilizations: most are neutral pragmatists
ALIGNMENT_GENESIS_SHARES = {"neutral": 0.70, "light": 0.15, "dark": 0.15}

# --- Non-spacefaring locals (native societies) ---
NATIVE_WORLD_SHARE = 0.35              # Share of uninhabited, habitable system worlds bearing native life at genesis
NATIVE_STAGES = ["Stone Age", "Bronze Age", "Iron Age", "Agrarian Kingdoms", "Industrial", "Atomic", "Orbital"]
NATIVE_STAGE_WEIGHTS = [5, 5, 4, 4, 3, 2, 1]
NATIVE_ADVANCE_RATE = 0.006            # Progress per fiscal quarter at sapience 5, full stability
NATIVE_FIRST_FLIGHT_SAPIENCE = 6.0     # An Orbital society this sapient achieves spaceflight and joins the galaxy
NATIVE_COLLAPSE_CONTAMINATION = 0.85   # Cultural contamination past this shatters the society
NATIVE_EXPLOIT_YIELD = 40              # Units stripped from a native world per exploitation run
NATIVE_TRADE_UNITS = 10                # Goods given per barter
NATIVE_UPLIFT_EQUIPMENT = 10           # Equipment (tools, schematics) per uplift
NATIVE_TITHE_SHARE = 0.05              # Protectorate tithe: share of native produce set aside per quarter
NATIVE_SYLLABLES = ["ka", "th", "ol", "ne", "vri", "sha", "um", "or", "el", "qua", "zi", "mar", "tu", "ish", "ren", "ok"]
NATIVE_VALUES = {                      # What native societies want in barter, by metabolism
    "biotic": ["ORGANICS", "EQUIPMENT"], "mineral": ["ORE", "EQUIPMENT"],
    "plasmic": ["H", "EQUIPMENT"], "cryogenic": ["H2O", "EQUIPMENT"], "umbral": ["Xe", "EQUIPMENT"],
}

# --- The Galactic Policy Deck: doctrines for dealing with non-spacefaring locals ---
POLICY_CARDS = {
    "ALPHA": {"name": "Strict Non-Interference", "motto": "Let them find the stars on their own.",
              "allows": {"observe"}},
    "BETA": {"name": "Scientific Observation", "motto": "Watch, record, and do not be seen.",
             "allows": {"observe", "contact_if_ready"}},
    "GAMMA": {"name": "Protectorate & Tithe Integration", "motto": "Our shield over them; their labor for the realm.",
              "allows": {"observe", "contact", "trade", "uplift", "protect", "collect"}},
    "DELTA": {"name": "Unrestricted Exploitation", "motto": "The galaxy belongs to those who can reach it.",
              "allows": {"observe", "contact", "trade", "uplift", "protect", "collect", "exploit", "convert"}},
    "EPSILON": {"name": "Missionary Conversion", "motto": "Every soul a candle for the Pyre.",
                "allows": {"observe", "contact", "trade", "convert", "exploit"}},
}
POLICY_ORDER = ["ALPHA", "BETA", "GAMMA", "DELTA"]   # Light -> Dark; authorities re-draw along this axis
POLICY_CONTACT_READY_STAGE = 5         # Under BETA, contact is lawful only with Atomic-age societies...
POLICY_REVIEW_INTERVAL = 1000          # Authorities review their doctrine once per era
POLICY_BOUNDS = {"FEDERATION": ("ALPHA", "GAMMA"), "COMPACT": ("BETA", "DELTA")}   # How far each may drift
AUTHORITIES = {
    "FEDERATION": {"name": "Terran Federation Senate", "card": "BETA", "sapience_threshold": 6.0,
                   "uplift_limit": 1, "enforcement": "INTERDICT", "warrant": 4000, "alignment": 0.3},
    "COMPACT": {"name": "ISSE Frontier Compact", "card": "GAMMA", "sapience_threshold": 4.0,
                "uplift_limit": 1, "enforcement": "WARRANT", "warrant": 2500, "alignment": 0.05},
    "IMPERIUM": {"name": "Aurelian Imperium", "card": "GAMMA", "sapience_threshold": 3.0,
                 "uplift_limit": 1, "enforcement": "INQUISITION", "warrant": 5000, "alignment": -0.1},
    "ZEALOT": {"name": "Choir of the Pyre", "card": "EPSILON", "sapience_threshold": 0.0,
               "uplift_limit": 0, "enforcement": "NONE", "warrant": 0, "alignment": -0.55},
    "NONE": {"name": "No Authority (Deep Void)", "card": "DELTA", "sapience_threshold": 0.0,
             "uplift_limit": 9, "enforcement": "NONE", "warrant": 0, "alignment": -0.2},
}

# --- The Aurelian Imperium: gothic bureaucracy, tithes, techno-heresy ---
IMPERIUM_CAPITAL_RANGE = (30, 58)      # Throne system is chosen among Borderland sectors in this range
IMPERIUM_TERRITORY_HOPS = 2
IMPERIUM_TITHE_RATE = 0.10             # Share of each Imperial world's ore/organics/Fe/Ti tithed per fiscal quarter
IMPERIUM_MANPOWER_RATE = 0.01          # Population drafted to the Fortress World garrison per quarter
IMPERIUM_TITHE_MORALE_COST = 1
IMPERIUM_UNHAULED_LOSS = 0.5           # Tithes without a Goliath hauler lose half in transit
IMPERIUM_FLEET_MAX = 4
IMPERIUM_WARSHIP_COST = {"Fe": 120, "Ti": 60, "ORE": 150}   # Materiel consumed per commissioned hull
IMPERIUM_CREW_FLOAT = 3000             # SOL crew float per hull, paid from the Imperial treasury via the ISSE
IMPERIUM_SECESSION_MORALE = 35
IMPERIUM_COMMISSARIAT_MORALE = 3       # Sermons and garrisons: morale restored per quarter on Imperial worlds
SECESSION_UNREST_QUARTERS = 4          # Consecutive quarters below the secession threshold before a world breaks away
HERESY_TECHS = {"NANITE_DRYDOCK", "CLOAKING_GRID", "BIO_SYNTHESIZER"}   # Thinking machines, xeno-veils, flesh-forges
HERESY_CRISIS_MORALE = 8
HERESY_WARRANT_LEVEL = 3
IMPERIAL_XENO_SURCHARGE = 0.20         # Imperial starports gouge non-human captains
IMPERIAL_CLADES = {"IMPERIAL", "BIOTIC"}

# --- The Choir of the Pyre: a dogma-driven zealot theocracy ---
ZEALOT_CAPITAL_RANGE = (82, 100)
ZEALOT_TERRITORY_HOPS = 2
ZEALOT_START_DOGMA = 0.78
ZEALOT_RD_FREEZE_DOGMA = 0.7           # Above this, research is heresy
ZEALOT_SURPLUS_RESERVE = 1500          # SOL-equivalent a zealot world keeps; the surplus above it is tithed to the Pyre
ZEALOT_SURPLUS_TITHE = 0.5
ZEALOT_DOGMA_PER_TITHE = 0.01          # Dogma gained per 10,000 SOL-equivalent tithed
ZEALOT_FEAST_ORGANICS = 200            # Organics above this are burned in pilgrimage feasts
ZEALOT_STAGNATION_GRACE = 50           # Cycles without expansion before the faith turns on itself
ZEALOT_STABILITY_DECAY = 0.01          # ... per fiscal quarter, plus 0.03 x dogma
ZEALOT_CRUSADER_COST = 9000            # SOL-equivalent paid to the capital shipyard per Fanatic Boarding Vessel
ZEALOT_FLEET_MAX = 4
ZEALOT_TRIBUTE_SHARE = 0.10
ZEALOT_HERETIC_CLADES = {"PLASMIC", "CRYOGENIC", "LITHIC"}
ZEALOT_PURGE_LOSS = 0.25               # Population share lost in a purge
ZEALOT_CRUSADE_RANGE = 4
ZEALOT_OVEREXTENSION_WORLDS = 6        # Beyond this many worlds, every quarter erodes the faith's stability...
ZEALOT_OVEREXTENSION_DECAY = 0.01     # ...by this much per extra world
ZEALOT_MUSTER_TROOPS = 200             # Faithful drafted aboard a crusader at a Pyre world
ZEALOT_HALLOW_TROOPS = 100             # Settlers landed to hallow an empty world
ZEALOT_CONVERT_TROOPS = 40             # Missionaries sent down to a native people
ZEALOT_EXPANSION_COOLDOWN = 100       # Consecrating a world takes time: one new world per this many cycles
ZEALOT_HALLOW_COST = 4000              # SOL-equivalent from the Pyre's vault to consecrate a new shrine world

# New hulls
SHIP_CATALOG_EXTENSIONS = {
    "Aegis Pleasure Cruiser": {"holds": 60, "max_shields": 400, "max_fighters": 12, "price": 45000, "min_rank_tier": 2,
                               "berths": 60,
                               "description": "Starliner: sixty VIP staterooms, a casino deck and an escort's worth of guns."},
    "Bulk Goliath": {"holds": 400, "max_shields": 600, "max_fighters": 40, "price": 60000, "min_rank_tier": 2,
                     "clade": "IMPERIAL", "move_turns": 2,
                     "description": "Colossal Imperial tithe-hauler. Slow (2 turns per warp) but carries a moon's worth of ore."},
    "Gothic Battle-Cruiser": {"holds": 60, "max_shields": 2500, "max_fighters": 400, "price": 90000, "min_rank_tier": 3,
                              "clade": "IMPERIAL", "broadside": 1.5,
                              "description": "Cathedral-spired Imperial warship with heavy broadside kinetic batteries."},
    "Fanatic Boarding Vessel": {"holds": 40, "max_shields": 500, "max_fighters": 160, "price": 9000, "min_rank_tier": 9,
                                "clade": "ZEALOT", "broadside": 1.2,
                                "description": "Pyre-blessed assault ship crammed with zealot boarding mobs. Not for sale."},
}

# --- Civilizational Chronicle Engine ---
CHRONICLE_MAX_ENTRIES = 4000
CHRONICLE_JUMP_MILESTONES = [100, 500, 1000, 2500, 5000, 10000]
CHRONICLE_FREIGHT_MILESTONES = [10, 50, 100, 250, 500]
CHRONICLE_HUNGER_SURVIVAL = 5          # A crew fed again after this many missed rations writes a hunger log
CHRONICLE_SIEGE_MIN_ASSAULTS = 3
CHRONICLE_SIEGE_LIFT_CYCLES = 50
CHRONICLE_ERA_INTERVAL = 2500
CHRONICLE_PLAYER_ENTRY_MAX = 2000      # Characters in a player-written log entry

SHIP_CATALOG.update(SHIP_CATALOG_EXTENSIONS)

# Imperial & zealot polities (civilizations seated on their worlds)
IMPERIAL_POLITY = {
    "name": "Aurelian Imperium", "species_name": "human-imperial", "class_code": 7, "sigil": "♜",
    "clade": "bimaniform", "motto": "the Throne endures; the Throne provides; the Throne remembers",
    "disposition": "industry", "metabolism": "biotic", "station": "sovereign", "era_index": 2, "tech_level": 4,
    "discovered_elements": ["Fe", "Ti", "C"],
}
ZEALOT_POLITY = {
    "name": "Choir of the Pyre", "species_name": "ardent-bimaniform", "class_code": 7, "sigil": "✠",
    "clade": "bimaniform", "motto": "all that is hoarded shall burn; all that burns shall shine",
    "disposition": "expansionist", "metabolism": "biotic", "station": "sovereign", "era_index": 1, "tech_level": 3,
    "discovered_elements": ["C", "S"],
}
IMPERIAL_WORLD_NAMES = ["Aurelia Throneworld", "Segmentum Fortress Kadmos", "Hive Tertius", "Forge Mordant",
                        "Cardinal Vesper", "Bastion Hollow"]
ZEALOT_WORLD_NAMES = ["Pyre Ascendant", "Shrine of Embers", "Cinder Chapel", "Ashen Reliquary", "Lantern Martyrdom"]
CRUSADER_NAMES = ["Brother-Captain Ignatius", "Sister-Captain Vehement", "Pyre-Marshal Castigan",
                  "Ember-Sworn Dolorosa", "Flamewright Absolom", "Canoness Severine", "Zealot-Lord Cathrax"]
IMPERIAL_CAPTAIN_NAMES = ["Lord Commissar Varro", "Rogue Trader Ottavia", "Void-Admiral Castellan",
                          "Tithe-Master Grevane", "Lady Inquisitor Maelis", "Shipmaster Brandt"]

# =============================================================================
# [12] SINGLE-LINEAGE KERNELS, COMMAND MODES, LEGACY
# =============================================================================
LINEAGE_START_CLONES = 2               # Backup clones in the lineage's vats at genesis
LINEAGE_MAX_CLONES = 3
LINEAGE_CLONE_PRICE = 6000             # SOL per backup clone at Sol Central (paid to the stardock)
LINEAGE_LEGACY_FILE = "xylarium_legacy.json"   # Hall of Lineages: epitaphs that outlive their kernels
LINEAGE_CLADES = ["BIOTIC", "LITHIC", "PLASMIC", "CRYOGENIC", "ANARCHY", "IMPERIAL"]
COMMAND_MODES = ("FLY", "EMPIRE")
NPC_HOUSE_START_CLONES = 3             # Backup clones in a newly founded NPC house's vats
NPC_HOUSE_MAX_CLONES = 4
OUTLAW_CREED_LINE = -0.3               # Outlaw-creed captains above this alignment go raiding to keep their creed
OUTLAW_SHAKEDOWN_SHARE = 0.08          # Tribute taken from a weaker ship in a protected system (no shots fired)
AI_INVEST_RESERVE = 3000               # Liquid SOL an autonomous captain keeps before buying ISSE shares
AI_CASH_FLOOR = 800                    # Below this liquid SOL, an autonomous captain sells shares for a working float
AI_XP_VALUE_SOL = 80                   # SOL an autonomous captain still climbing the tiers assigns one point of experience
AI_RATION_LOW_WATER = 6                # Rations aboard below which an autonomous captain goes for food
AI_RATION_RESERVE = 30                 # ...and how many it stocks when docked at a food port
AI_WORKING_FLOAT = 2500                # SOL an autonomous captain never spends on a deep ration reserve
AI_MIN_FOOD_MONEY = 60                 # Below this liquid SOL a hungry captain works for money instead of chasing food
SHARE_BOOK_MULTIPLE = 1.5              # Fair share value = (treasury + annualized revenue) x this / shares outstanding
SHARE_REVERSION = 0.25                 # Share of the gap to fair value closed each fiscal quarter
AI_INVEST_SHARE = 0.10                 # Share of surplus above the investment reserve put into one ISSE order
SHARE_ISSUANCE_MAX_MULTIPLE = 4.0      # A company may issue stock up to this multiple of its founding share count

# --- Captain personas & economic circulation ---
PERSONA_CALLINGS = {                   # calling -> (weight, plan kinds it favours)
    "hauler": (3, ("freight", "extract")),
    "trader": (3, ("haul", "liquidate")),
    "miner": (2, ("mine", "extract")),
    "digger": (1, ("dig",)),
    "financier": (1, ()),
    "colonist": (1, ("settle",)),
}
PERSONA_CALLING_BIAS = 1.5             # Value multiplier on plans of a captain's calling
PERSONA_MEMORY_RATE = 0.2              # Weight of the latest outcome in a plan kind's remembered payoff
CREW_WAGE_BASE = 1.0                   # Per active turn: base + holds/25 + fighters/50 SOL, paid ashore where the ship docks
CREW_WAGE_ARREARS_CAP = 400            # Unpaid wages beyond this are forgone (the crew signs off)
SHORE_LEAVE_MAX_SHARE = 0.25           # A spender spends up to this share of cash above comfort per shore leave
BLACK_MARKET_HULL_MARKUP = 1.35        # Deep Void harbors sell hulls to captains Sol's turrets turn away

# --- Macro circulation: ports resell to their regions; the ISSE recycles excess reserves ---
PORT_RETAIL_MARKUP = 1.15              # Regional households pay the port's buying price plus this markup
PORT_RETAIL_RADIUS = 3                 # Populated worlds within this many warps (same currency) buy from a port
PORT_RETAIL_VAULT_SHARE = 0.05         # ...each spending at most this share of its vault per fiscal quarter

# =============================================================================
# [13] FEDERATIONS, CENTRAL BANKS, CLEARING UNION, MULTIPLE ISSEs, SETTLEMENT CHAIN
# =============================================================================
CENTRAL_BANK_FOUNDING_RESERVES = 150_000   # SOL-equivalent founding reserves per non-SOL central bank (genesis)
CENTRAL_BANK_RESERVE_FLOOR = 20_000        # SOL-equivalent a central bank never lends or sells below
CLEARING_BAND = 1.10                       # ISSE pool reserves beyond this multiple of genesis depth are disorderly
CLEARING_INTERVENTION_RATE = 0.25          # Share of the disorder a local exchange corrects each quarter (exchanges.py)
POLICY_RATE_BASE = 0.010                   # Per fiscal quarter (~4% per four quarters)
GOVERNOR_DARK_SPREAD = 0.020               # Usury: extra quarterly rate per unit of Dark alignment
GOVERNOR_LIGHT_DISCOUNT = 0.004            # Fair lending: rate discount per unit of Light alignment
CREDIT_TRIGGER_SHARE = 0.20                # A port below this share of its working baseline draws credit
CREDIT_LINE_SHARE = 0.25                   # ...a draw of this share of its baseline per quarter
CREDIT_CAP_SHARE = 1.00                    # ...up to this much of its baseline outstanding
CREDIT_REPAY_SHARE = 0.25                  # Share of a port's surplus above baseline repaid per quarter
CREDIT_LIGHT_INTEREST_CAP = 0.50           # Light governors cap total interest at this share of principal
CREDIT_WRITE_OFF_MULTIPLE = 3.0            # Debt beyond this multiple of baseline is written off
CROSS_POOL_SEED_SOL_VALUE = 120_000        # SOL-equivalent depth per side of each Galactic ISSE cross pair
SETTLEMENT_RECEIPTS_KEPT_BLOCKS = 40       # Settlement blocks whose receipt bodies are kept (headers are kept forever)
CREDIT_INCOME_QUARTERS = 4                 # A port may owe at most this many quarters of its regional income
CREDIT_DARK_PRUDENCE = 1.5                 # Dark governors lend this multiple past prudence (and eat the write-offs)
CENTRAL_BANK_RESERVE_CEILING = 0.30         # Reserves above this share of the currency's money supply are idle...
CENTRAL_BANK_OMO_RATE = 0.25                # ...and this share of the idle excess funds regional public works each quarter

# --- Commerce tax, house self-preservation, financier arbitrage ---
TRADE_SALES_TAX = 0.02                      # Municipal sales tax on every port trade, paid to the region's worlds
HOUSE_ENDANGERED_CLONES = 2                 # Below this many backup clones a house turns defensive
FINANCIER_ARBITRAGE_CHANCE = 0.3            # Chance per turn a financier scans the Galactic ISSE for triangles
CROSS_REANCHOR_RATE = 0.5                   # Each quarter the ISSE moves cross pairs halfway to the SOL-implied rate
FINANCIER_ARBITRAGE_MIN_EDGE = 0.004        # Minimum round-trip profit (after fees) worth trading

# --- [14] Demography: on-planet growth, housing technology, multi-planetary drive, household demand ---
# Carrying capacity is derived from physics and biology (biosphere.py); habitats are enclosed farms and
# living space that add usable area independent of the light. Councils build them from the vault.
HABITATS_MAX_BY_TIER = {0: 1, 1: 2, 2: 3, 3: 4}   # Engineering limits: higher citadels can dig deeper
HABITAT_COST = 2500                          # SOL-value per habitat (x local price level), paid to the contractor port
HABITAT_ORE = 60                             # Ore consumed per habitat
HABITAT_BUILD_QUARTERS = 16                  # Construction time: a council finishes one habitat before starting the next
CITADEL_BUILD_QUARTERS_PER_TIER = 30         # Raising a citadel to tier n takes n x 30 quarters
DEMOGRAPHY_PRESSURE = 0.90                   # Population / housing at which a world starts building
COUNCIL_WORKS_SHARE = 0.5                    # Share of public services a crowded, building world puts into works instead
DEMOGRAPHY_COUNCIL_RESERVE = 3000            # Vault kept back (SOL-value) when the council builds
STEADY_STATE_SHARE = 0.95                    # Population-control worlds hold their numbers at this share of housing
STEADY_STATE_MORALE = 3                      # ...and are content for it (per quarter)
# Multi-planetary drive: a world at its engineering ceiling either sends settlers or adopts population controls
DAUGHTER_CITADEL_TIER = 2                    # Settler ships need a Planetary Stronghold's yards
DAUGHTER_EMIGRANT_SHARE = 0.10               # Share of the parent world that emigrates
DAUGHTER_EMIGRANTS_MAX = 20_000
DAUGHTER_EMIGRANTS_MIN = 500
DAUGHTER_SETTLER_COST = 6000                 # SOL-value (x local price level) for the settler fleet, paid to the contractor
DAUGHTER_RADIUS_BY_TIER = {2: 3, 3: 6, 4: 10, 5: 12}       # How far a world's settler fleets can reach
DAUGHTER_MIN_HABITABILITY = 0.3
DAUGHTER_FOUNDING_TIER = 1                   # Settler fleets raise a redoubt: daughters start with tier-1 agriculture
DAUGHTER_COOLDOWN_QUARTERS = 8
DIASPORA_HOUSING_THRESHOLD = 0.95       # Homeworld crowding threshold triggering diaspora diversion
DIASPORA_CROWDED_CYCLES = 50            # Cycles at crowding threshold before tax diversion begins
DIASPORA_TAX_SHARE = 0.20               # Share of government tax diverted to expeditionary colony escrow
STASIS_POD_COST = 5000                  # Cost to install Stasis Pod cryogenic containment module
# Frontier: the charted galaxy grows when its peoples run out of room (space : people : resources in balance)
# Households: populations buy a basket of goods from their regional starports each fiscal quarter
HOUSEHOLD_BASKET = {"ORGANICS": 0.3, "EQUIPMENT": 0.15, "H2O": 0.2}   # units per 1,000 people per quarter
HOUSEHOLD_RADIUS = 3                         # Warps a household will shop across (same money)
HOUSEHOLD_INCOME_SHARE = 0.35               # Share of a colony's earnings that stays with its households (their purse)
PORT_PAYROLL_SHARE = 0.6                    # Share of a starport's operating costs paid as wages to regional households
HOUSEHOLD_PURSE_PER_CAPITA = 0.10           # Household savings held beyond this (SOL-value per head) go to the vault
HOUSEHOLD_SHORTAGE_MORALE = 2                # Morale lost when a world can't fill its basket

# --- [15] Biosphere: the biology that turns light and land into food and people (biosphere.py) ---
# The only chosen biological constants; carrying capacity, food and growth rates are derived from them.
PEOPLE_PER_EARTH_AREA = 50_000        # Subsistence carrying capacity of one Earth-area of ideal land at citadel tech 1
TECH_YIELD = {0: "1/5", 1: "1/1", 2: "3/1", 3: "8/1", 4: "12/1"}   # Agricultural technology by citadel tier
HABITAT_AREA = "1/20"                  # Each habitat adds this much Earth-area of enclosed, lit farmland and housing
BIRTH_RATE = "3/100"                   # A people's maximum natural increase per standard year
CROP_SURPLUS_RATE = "6/100"            # How fast farms can add food per standard year on ideal land in a full season
FOOD_PER_THOUSAND = 1                  # Organics a thousand people eat per cycle
# Where each metabolism's energy peaks (flux, Earth = 1). Plasmic life feeds on a giant's own heat (its mass).
LIGHT_OPTIMUM = {"biotic": "1/1", "cryogenic": "1/8", "mineral": "3/1", "umbral": "1/800"}
PLASMIC_MASS_OPTIMUM = 100             # Earth masses at which a giant's internal heat best feeds plasmic life

# --- [16] Fertility, luxury and tourism (fertility.py, luxury.py, tourism.py) ---
# Fertility f is a people's desired family size relative to replacement (1 = replacement). A world grows
# logistically toward min(1, f) x K - a transitioned people settles below what its land could carry - and a
# fertile one (f > 1) fills its land faster, never faster than its farms can feed the newcomers.
# Reproductive strategy is biology: each clade breeds by one of five strategies; unlisted clades take their
# metabolism's default.
REPRODUCTIVE_STRATEGY = {
    "mycotiform": "r", "hexasocial": "r", "hypobiotid": "r", "cnidiform": "r", "polybrachia": "r",
    "amphiform": "r", "metamorphid": "r",
    "bimaniform": "K", "ailuroform": "K", "soniform": "K", "syzygiform": "K", "draconiform": "K",
    "heliciform": "K", "revenid": "K", "actinoform": "K", "volatiform": "K", "human": "K",
    "lithophage": "lithic", "endolithid": "lithic", "lithic": "lithic",
    "cryocoherens": "cryo", "cryocoherent": "cryo",
    "plasmiform": "plasmic", "plasmic": "plasmic",
}
METABOLISM_STRATEGY = {"biotic": "K", "mineral": "lithic", "cryogenic": "cryo", "plasmic": "plasmic", "umbral": "K"}
FERTILITY_R_MAX = 2.5                  # r-strategists: calories become clutches, up to this multiple of replacement
FERTILITY_K_SECURE = (1.0, 1.2)        # K-strategists: secure but poor -> fully provided for
FERTILITY_K_LUXURY_COMPRESSION = 0.35  # ...full luxury access compresses fertility by this share
FERTILITY_K_URBAN_COMPRESSION = 0.15   # ...and a full world (P = K) by this share
LITHIC_METAL_PER_THOUSAND = 20         # Fe/Ti (or ore/10) a thousand lithic people need on hand to bud
FERTILITY_CRYO_MAX = 1.3               # Stillcold fission in cold, quiet isolation
FERTILITY_STRESS = 0.25                # Famine or bombardment in the last season: fertility falls to a quarter
FERTILITY_STRESS_SEASONS = 1           # ...for this many fiscal quarters after the blow
# Knowledge (knowledge.py): stocks per people in four domains, in knowledge units - a thousand minds' year of free
# thought at Earth's temperature. Capabilities are processes whose cost falls along Wright's learning curve with
# the people's knowledge in their domain; KNOWLEDGE_UNIT is the experience of the first doubling. Nothing unlocks.
KNOWLEDGE_UNIT = 10
PROCESSES = {
    "jump_drive": {"domain": "energy", "name": "Hyper-Dimensional Jump Drive"},
    "cloaking": {"domain": "information", "name": "Umbral Cloaking Shroud"},
    "nanite_repair": {"domain": "materials", "name": "Self-Replicating Nanite Drydock"},
    "bio_synthesis": {"domain": "biology", "name": "Antisymmetric Bio-Synthesizer"},
    "orbital_foundry": {"domain": "materials", "name": "Zero-G Orbital Megafoundry"},
    "nursery_K": {"domain": "biology", "name": "artificial gestation"},
    "nursery_r": {"domain": "biology", "name": "sanitation"},
    "nursery_lithic": {"domain": "materials", "name": "foundry budding"},
    "nursery_cryo": {"domain": "energy", "name": "deep refrigeration"},
    "nursery_plasmic": {"domain": "energy", "name": "magnetic confinement"},
    "genome_editing": {"domain": "biology", "name": "genome editing"},
    "terraforming": {"domain": "materials", "name": "planetary engineering"},
    "solar_collectors": {"domain": "energy", "name": "light collection"},
    "stellar_arrays": {"domain": "energy", "name": "orbital collection and beaming"},
    "core_taps": {"domain": "materials", "name": "deep core boring"},
    "antimatter": {"domain": "energy", "name": "pair production and confinement"},
}
LEGACY_TECH_PROCESS = {"JUMP_DRIVE": "jump_drive", "CLOAKING_GRID": "cloaking", "NANITE_DRYDOCK": "nanite_repair",
                       "BIO_SYNTHESIZER": "bio_synthesis", "ORBITAL_FOUNDRY": "orbital_foundry",
                       "XENOGENESIS": "nursery_K"}
RESEARCH_POINTS_PER_UNIT = 10          # old research points (relics, anomalies, natives) per knowledge unit
# Staples: what each metabolism eats. Food is counted in energy-equivalent units - one unit of a people's staple
# carries the metabolic energy one unit of organics carries a biotic people - so FOOD_PER_THOUSAND is the same need
# for every people, and real output values every harvest at the price of organics (one food unit). Carbon life eats
# organics; lithotrophs graze ore out of the crust (geology's mine face); Stillcold life drinks ice; plasmic life
# feeds on hydrogen - the same hydrogen ships burn and the same ore industry builds with.
STAPLES = {"biotic": "ORGANICS", "umbral": "ORGANICS", "mineral": "ORE", "cryogenic": "H2O", "plasmic": "H"}
# What each metabolism gives back of what it eats (its chemistry, not its culture): carbon life respires water,
# shadow-life leaves carbon, lithotrophs free the water bound in rock, Stillcold life splits ice and breathes out
# hydrogen, plasmic life fuses hydrogen and leaves helium-3 ash. Another people whose staple it is eats it.
METABOLIC_WASTE = {"biotic": "H2O", "umbral": "C", "mineral": "H2O", "cryogenic": "H", "plasmic": "He-3"}
WASTE_SHARE = "1/2"                    # of what is eaten, given back as waste (respiration: ~0.6 of glucose is water)
# Sustenance: each people's food security, read every quarter from what its worlds harvested and needed.
# Self-sufficiency is harvest / need (smoothed over a year); a people short of it is hungry when its stores
# would run out within SUSTENANCE_RUNWAY_QUARTERS. Hungry, it expands to open worlds it can eat on if it can
# sail; with nowhere to go it is pressed - and a pressed people raids the stores and ports that hold its staple.
SUSTENANCE_RUNWAY_QUARTERS = 4
SUSTENANCE_SMOOTHING = 0.25            # weight of the newest quarter in the year's self-sufficiency
FOOD_WAR_PEACE_QUARTERS = 8            # a war over food ends after this long without a raid
RELIEF_LIGHT_THRESHOLD = 0.3           # peoples at least this luminous send their surplus to hungry kin
# Meaning (mu): a people's collective momentum against the satiation of comfort, a multiplier on fertility
# in [MEANING_FLOOR, MEANING_CEIL], read from state (fertility.meaning: open land in reach, knowledge growth over a
# generation, births a crisis deferred, comfort with nothing ahead). How much of it reaches births is how much a
# strategy's births are a choice (MEANING_WEIGHT):
# a K people decides its family size; an r clutch, a lithic bud or a coronal shearing mostly does not.
MEANING_FLOOR, MEANING_CEIL = 0.5, 2.0
MEANING_WEIGHT = {"K": 1.0, "cryo": 0.5, "lithic": 0.25, "plasmic": 0.25, "r": 0.0}
# Nurseries: each strategy's technological leap past its biology - a district built like a habitat, that only
# works while it is fed. Unfed for a quarter it goes dark and its brood fails (a quarter's births are lost).
# Inputs in preference order as (commodity, units per unit of need); "FUEL" is the world's own fuel cell.
# Nothing gates one: how far it lifts its people's biology is their mastery of the process (knowledge.py), and
# its inputs fall along the same learning curve.
NURSERIES = {
    "K": {"name": "Fertility Centre", "inputs": [("ORGANICS", 1)], "per_thousand": 5},
    "lithic": {"name": "Foundry Nursery", "inputs": [("Fe", 1), ("Ti", 1), ("ORE", 10)], "per_thousand": 2},
    "cryo": {"name": "Deep-Cold Vault", "inputs": [("H2O", 1), ("FUEL", 1)], "per_thousand": 1},
    "plasmic": {"name": "Confinement Ring", "inputs": [("H", 1), ("He-3", 1), ("FUEL", 1)], "per_thousand": 1},
    "r": {"name": "Sanitation Works", "inputs": [("EQUIPMENT", 1), ("ORE", 4)], "per_thousand": 0.5},
}
# Viability: a people sends settler fleets only after sustaining fertility at least VIABILITY_FERTILITY for
# VIABILITY_QUARTERS consecutive quarters; each fleet carries its clade's seeding kit (SEED_KIT per thousand
# emigrants, scaled down to what the parent can stock)
VIABILITY_FERTILITY = 1.05
VIABILITY_QUARTERS = 8
SEED_KIT = {"biotic": ([("ORGANICS", 1)], 10), "umbral": ([("ORGANICS", 1)], 10),
            "mineral": ([("Fe", 1), ("Ti", 1), ("ORE", 10)], 20),   # LITHIC_METAL_PER_THOUSAND: metal to bud from
            "cryogenic": ([("H2O", 1)], 10), "plasmic": ([("H", 1)], 10)}     # the voyage's food is the people's staple
# Blight: an r world's density sets a pathogen's reproduction number R0 = (P/K) / BLIGHT_DENSITY. Above 1 an
# introduction takes off with chance 1 - 1/R0 a quarter; it infects the share z solving z = 1 - exp(-R0 z),
# kills BLIGHT_FATALITY of the infected, and rots z/2 of the granary.
BLIGHT_DENSITY = 0.85
BLIGHT_FATALITY = 0.10
# Natal policy cards (any sovereign world or player; Sacred Hatching for the Pyre's worlds only)
NATAL_POLICIES = {
    "propagation": {"name": "Edict of Propagation", "fertility": 1.4, "tax": 0.85, "food": 1.25},
    "ascetic": {"name": "Ascetic Mandate", "fertility_cap": 1.0, "productivity": 1.2, "luxury_demand": 1.1},
    "hatching": {"name": "Sacred Hatching", "zealot_only": True, "research_cost": 1},
}
HATCHING_FOOD_PER_RECRUIT = 20         # Organics beyond two seasons' stores consumed per fanatic recruit
# Luxury: four super-types, each crafted by a world from what it holds in abundance, flavoured by its people.
# A world's demand for a luxury falls with its own availability (nobody craves what they make).
LUXURY_TYPES = {       # inputs by metabolism, in order of preference (the first the world holds is used)
    "LUX_STIMULANT": {"inputs": {"biotic": ["ORGANICS"], "plasmic": ["H", "He-3"], "cryogenic": ["H2O"],
                                 "mineral": ["C", "ORE"], "umbral": ["Xe", "ORGANICS"]}},
    "LUX_RESONANT": {"inputs": {"mineral": ["Si", "ORE"], "cryogenic": ["H2O", "ORE"], "biotic": ["Si", "ORE"],
                                "plasmic": ["Si", "ORE"], "umbral": ["Si", "ORE"]}},
    "LUX_EPHEMERA": {"inputs": {"biotic": ["ORGANICS"], "cryogenic": ["H2O"], "plasmic": ["H"],
                                "mineral": ["ORE"], "umbral": ["ORGANICS"]}},
    "LUX_CURIO": {"inputs": {"biotic": ["Ti", "ORE"], "mineral": ["Ti", "ORE"], "plasmic": ["Ti", "ORE"],
                             "cryogenic": ["Ti", "ORE"], "umbral": ["Ti", "ORE"]}},
}
# What a world's sky and ground lend itself to (its signature leans on these, then on its people's affinity)
LUXURY_WORLD_BIAS = {
    "TERRESTRIAL": {"LUX_EPHEMERA": 1.5, "LUX_STIMULANT": 1.2},
    "OCEANIC": {"LUX_EPHEMERA": 1.3, "LUX_RESONANT": 1.2},
    "ICE": {"LUX_RESONANT": 1.6},
    "VOLCANIC": {"LUX_STIMULANT": 1.4, "LUX_CURIO": 1.2},
    "BARREN": {"LUX_CURIO": 1.4, "LUX_RESONANT": 1.3},
    "GAS_GIANT": {"LUX_STIMULANT": 1.6},
    "ROGUE": {"LUX_CURIO": 1.5},
}
LUXURY_AFFINITY = {"biotic": "LUX_EPHEMERA", "mineral": "LUX_RESONANT", "plasmic": "LUX_STIMULANT",
                   "cryogenic": "LUX_RESONANT", "umbral": "LUX_CURIO"}
LUXURY_CRAFT_PER_THOUSAND = 0.4        # Luxury units a thousand provided-for people craft per quarter (x tech tier)
LUXURY_WANT_PER_THOUSAND = 0.12        # Units of each luxury a thousand people want per quarter (at full comfort)
LUXURY_EXPORT_RADIUS = 5               # Luxuries are light and dear: workshops ship them further than bulk goods
LUXURY_PURSE_SHARE = 0.5               # Share of the purse left after the basket that households spend on luxury
EPHEMERA_SPOILAGE = 0.10               # Perishable imports: share of every stock that spoils each quarter (stasis pods cut it in transit)
# Tourism: two tiers. Mass tourism is a flow along the lanes (households of spacefaring worlds spend part of
# their surplus at resorts in reach); VIP charters are physical passengers carried by captains' hulls.
TOURISM_PURSE_SHARE = 0.3              # Share of the post-luxury household surplus spent travelling
TOURISM_RADIUS = 6                     # Warps a tourist will travel
TOURISM_FARE_SHARE = 0.25              # Share of a trip paid to the origin port's carriers (who burn the hydrogen)
TOURIST_H_PER_HUNDRED_HOPS = 1         # Reaction mass burned per hundred passenger-jumps
TOURIST_SPEND_PER_HEAD = 2             # SOL-value a mass tourist spends per trip (to count heads)
RESORT_BEDS = 5000                     # Tourist-trips per quarter a Pleasure Dome tile hosts
RESORT_COST = 4000                     # SOL-value (x price level) to raise one, paid to the contractor port
RESORT_SHELL_UNITS = 40                # Matter a dome's shell takes (what it is made of is its site's: uses.py)
RESORT_H2O_PER_QUARTER = 5             # Water a dome consumes per quarter (pools, gardens, spas)
ORBITAL_BERTHS_PER_STATION = 8000      # Tourist-trips per quarter an orbital leisure station hosts
ORBITAL_STATION_COST = 12000           # SOL-value to build one at a starport (the port's operator pays)
ORBITAL_STATION_MIN_FLOW = 3           # Seasons of tourist traffic through a port before it builds a station
CHARTER_PARTY = (2, 12)                # VIPs per charter
CHARTER_FARE_PER_VIP_HOP = 120         # SOL-value per VIP per jump, escrowed from the origin's households
CHARTER_MIN_PURSE = 20000              # Households must hold this (SOL-value) before their VIPs charter liners
CHARTER_EXPIRY_CYCLES = 400
CHARTER_RANSOM_SHARE = 0.6             # A pirate who takes a liner holds its VIPs for this share of the escrow

# --- [17] Drives and hydrogen wells (propulsion.py) ---
# Hydrogen is most of the universe's matter: every gas giant is a well. A starport in a giant's system skims
# its atmosphere; each season a skimmer lifts SKIM_ENERGY_PER_SEASON (Earth escape-energy units) of gas, so a
# lighter giant (shallower well) yields more. A share is helium-3.
SKIM_ENERGY_PER_SEASON = 3000
SKIM_HE3_SHARE = 20                    # one unit of He-3 per this many of hydrogen
# Fuel cells: a drive is built for a reaction mass. Efficiency is its relative exhaust velocity (hydrogen torch
# = 1): reaction mass burned per jump falls as 1/v_e, and tanks are sized so every cell gets the same range per
# hold of hull. Which cell a people builds is chosen algorithmically (propulsion.choose_fuel): what is abundant
# in reach x efficiency, against what its tradition burns, weighted by how clear-sighted (aligned) it is.
FUEL_CELLS = {
    "H": {"name": "Hydrogen fusion torch", "v_e": 1.0, "min_tier": 1},
    "C": {"name": "Hydrocarbon fuel cell", "v_e": 0.5, "min_tier": 1, "part": "EQUIPMENT"},
    "H2O": {"name": "Nuclear-thermal steam drive", "v_e": 0.8, "min_tier": 2, "part": "M3_ENGINE_MANIFOLD"},
    "He-3": {"name": "Helium-3 fusion drive", "v_e": 4.0, "min_tier": 2, "part": "M3_ENGINE_MANIFOLD"},
    "Xe": {"name": "Xenon ion drive", "v_e": 6.0, "min_tier": 2, "part": "M1_SUPERCONDUCTOR", "extra_turns": 1},
    "U": {"name": "Fission pulse drive", "v_e": 10.0, "min_tier": 3, "part": "M3_ENGINE_MANIFOLD"},
    "WARP": {"name": "Warp stabilizer drive", "v_e": None, "min_tier": 3, "part": "M4_WARP_CORE", "core_life": 400},
    "AM": {"name": "Antimatter photon drive", "v_e": 30.0, "min_tier": 4, "part": "M4_WARP_CORE"},
}
FUEL_REACH = 3                         # warps within which a people reckons what is abundant
DRIVE_INSTALL_FEE = 2000               # SOL-value paid to the yard on top of the part
# Readiness: a world's defence grid and fighters run on fusion. With too little hydrogen in reach it broadcasts
# a DEGRADED beacon and fights at reduced strength.
DEFENSE_H_PER_FIGHTER = 2
DEGRADED_READINESS = 0.5

# --- [18] The workbench: ship design from frames and modules (shipdesign.py) ---
# A design is a frame (volume budget, structural mass) filled with modules. Volume must fit, the reactors must
# power what draws power, and everything has mass: mass is what the drive must move (propulsion.burn_for).
# Materials are drawn from the building yard's warehouse. A design registers into the hull catalogue.
SHIP_FRAMES = {
    "corvette": {"volume": 60, "mass": 30, "price": 2000, "min_tier": 1, "Fe": 20, "Ti": 6},
    "frigate": {"volume": 120, "mass": 60, "price": 6000, "min_tier": 2, "Fe": 40, "Ti": 14},
    "cruiser": {"volume": 240, "mass": 110, "price": 16000, "min_tier": 2, "Fe": 80, "Ti": 30},
    "capital": {"volume": 480, "mass": 200, "price": 40000, "min_tier": 3, "Fe": 150, "Ti": 60},
    "leviathan": {"volume": 900, "mass": 350, "price": 90000, "min_tier": 4, "Fe": 280, "Ti": 110},
}
# per unit of the module: volume, mass, power (+ generates / - draws), price (SOL), materials, and what it gives
SHIP_MODULES = {
    "hold": {"volume": 1, "mass": 0.3, "power": 0, "price": 40, "Fe": 0.2, "gives": {"holds": 1}},
    "tank": {"volume": 1, "mass": 0.3, "power": 0, "price": 50, "Fe": 0.2, "gives": {"tank": 2}},
    "drive": {"volume": 4, "mass": 3, "power": -2, "price": 400, "Ti": 1, "gives": {"thrust": 1}},
    "reactor": {"volume": 3, "mass": 2, "power": 10, "price": 500, "Ti": 1, "Si": 0.5, "gives": {}},
    "shield": {"volume": 2, "mass": 1, "power": -2, "price": 300, "Si": 0.5, "gives": {"max_shields": 25}},
    "armor": {"volume": 1, "mass": 2, "power": 0, "price": 120, "Fe": 1, "gives": {"max_shields": 8}},
    "fighter_bay": {"volume": 3, "mass": 2, "power": -1, "price": 350, "Fe": 0.5, "gives": {"max_fighters": 5}},
    "mining_laser": {"volume": 3, "mass": 2, "power": -3, "price": 450, "Si": 0.5, "gives": {"mining": 4}},
    "berth": {"volume": 2, "mass": 1, "power": -0.5, "price": 250, "Fe": 0.2, "gives": {"berths": 1}},
    # leisure decks: comfort only for guests of the biology they are built for; each draws on a consumable
    "water_spa": {"volume": 4, "mass": 3, "power": -1, "price": 600, "gives": {"comfort": 1}, "for": ["biotic"]},
    "cryo_lounge": {"volume": 4, "mass": 3, "power": -2, "price": 700, "gives": {"comfort": 1}, "for": ["cryogenic"]},
    "plasma_bath": {"volume": 4, "mass": 2, "power": -3, "price": 900, "gives": {"comfort": 1}, "for": ["plasmic"]},
    "mineral_grotto": {"volume": 4, "mass": 5, "power": -1, "price": 500, "gives": {"comfort": 1}, "for": ["mineral"]},
    "void_gallery": {"volume": 4, "mass": 2, "power": -1, "price": 800, "gives": {"comfort": 1}, "for": ["umbral"]},
}
DRIVE_MASS_PER_THRUST = 60             # tonnes of design mass one drive module moves at full pace (less: sluggish, 2 turns a jump)
DESIGN_ROYALTY_MAX = 0.2               # designers may ask up to a fifth of the build price
DESIGN_FEE = 500                       # SOL registry fee paid to the yard (the draughting office)
COMFORT_PER_BERTH_FULL = 0.25          # amenity units per berth at which guests of that biology are fully content
