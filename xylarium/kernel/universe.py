"""
Universe graph generation for Xylarium.
Creates a deterministic 100-sector star network with warp lanes,
ports, planetary bodies, and security classification.
"""

import random
from typing import Dict, List, Optional
from xylarium.config import (
    TOTAL_SECTORS,
    FEDERATION_SECTOR_START,
    FEDERATION_SECTOR_END,
    BORDER_SECTOR_END,
)
from xylarium.kernel.models import (
    Sector,
    Port,
    Planet,
    SecurityLevel,
    PortClass,
    CommodityType,
)


PORT_NAMES = [
    "Helios Refinery", "Rigel Agri-Hub", "Aegis Munitions", "Tartarus Deep Mine",
    "Orion Free Haven", "Sirius Hyper-Tech", "Proxima Foundry", "Centauri Bio-Lab",
    "Cygnus Outpost", "Vega Trade Station", "Betelgeuse Silo", "Arcturus Terminal",
    "Aldebaran Complex", "Antares Depository", "Spica Exchange", "Pollux Granary",
    "Castor Ordnance", "Deneb Synthetics", "Altair Heavy Works", "Fomalhaut Harbor"
]

PLANET_NAMES = [
    "Genesis Prime", "Nova Terra", "Xylar-IV", "Iron Bastion", "Sanctuary",
    "Aetheria Prime", "Dread Hollow", "Krynn V", "Elysium-9", "Ceti Alpha",
    "Kepler Redoubt", "Tartarus Prime", "Gorgon's Rest", "Zephyr Station",
    "Oblivion-3", "Hyperion Core", "Vanguard Rock", "Oasis Sector",
    "Nemesis Citadel", "Avalon IV"
]

SECTOR_ADJECTIVES = [
    "Silent", "Nebular", "Radiant", "Void", "Crimson", "Shadow", "Pulsar",
    "Echo", "Starlight", "Obsidian", "Shattered", "Astral", "Quantum",
    "Solar", "Abyssal", "Iron", "Storm", "Vortex", "Infinite", "Ancient"
]

SECTOR_NOUNS = [
    "Reach", "Expanse", "Depths", "Passage", "Gateway", "Corridor", "Haven",
    "Rift", "Sector", "Bastion", "Crossing", "Belt", "Void", "Terminus",
    "Lagoon", "Cluster", "Shoals", "Sanctum", "Spire", "Nexus"
]


def determine_security(sector_id: int) -> SecurityLevel:
    if FEDERATION_SECTOR_START <= sector_id <= FEDERATION_SECTOR_END:
        return SecurityLevel.FEDERATION
    elif sector_id <= BORDER_SECTOR_END:
        return SecurityLevel.BORDERLAND
    return SecurityLevel.ANARCHY


def build_port(sector_id: int, rng: random.Random) -> Port:
    """Builds a trade port suited for the sector."""
    if sector_id == 1:
        # Federation Stardock
        return Port(
            sector_id=1,
            name="Stardock Central",
            port_class=PortClass.STARDOCK,
            stock={"ORE": 950, "ORGANICS": 950, "EQUIPMENT": 950},
            max_stock={"ORE": 1000, "ORGANICS": 1000, "EQUIPMENT": 1000},
            buys={"ORE": True, "ORGANICS": True, "EQUIPMENT": True},
            sells={"ORE": True, "ORGANICS": True, "EQUIPMENT": True},
        )

    # Pick a random TradeWars BBS Port Class (Classes 1-6 are most common, 7 & 8 rarer)
    classes = [
        PortClass.CLASS_1_BBS,
        PortClass.CLASS_2_BSB,
        PortClass.CLASS_3_SBB,
        PortClass.CLASS_4_SSB,
        PortClass.CLASS_5_SBS,
        PortClass.CLASS_6_BSS,
        PortClass.CLASS_7_SSS,
        PortClass.CLASS_8_BBB,
    ]
    weights = [20, 20, 20, 20, 20, 20, 5, 5]
    port_class = rng.choices(classes, weights=weights, k=1)[0]

    # Configure Buys/Sells based on Port Class
    buys = {"ORE": False, "ORGANICS": False, "EQUIPMENT": False}
    sells = {"ORE": False, "ORGANICS": False, "EQUIPMENT": False}

    if port_class == PortClass.CLASS_1_BBS:
        buys["ORE"] = True
        buys["ORGANICS"] = True
        sells["EQUIPMENT"] = True
    elif port_class == PortClass.CLASS_2_BSB:
        buys["ORE"] = True
        sells["ORGANICS"] = True
        buys["EQUIPMENT"] = True
    elif port_class == PortClass.CLASS_3_SBB:
        sells["ORE"] = True
        buys["ORGANICS"] = True
        buys["EQUIPMENT"] = True
    elif port_class == PortClass.CLASS_4_SSB:
        sells["ORE"] = True
        sells["ORGANICS"] = True
        buys["EQUIPMENT"] = True
    elif port_class == PortClass.CLASS_5_SBS:
        sells["ORE"] = True
        buys["ORGANICS"] = True
        sells["EQUIPMENT"] = True
    elif port_class == PortClass.CLASS_6_BSS:
        buys["ORE"] = True
        sells["ORGANICS"] = True
        sells["EQUIPMENT"] = True
    elif port_class == PortClass.CLASS_7_SSS:
        sells["ORE"] = True
        sells["ORGANICS"] = True
        sells["EQUIPMENT"] = True
    elif port_class == PortClass.CLASS_8_BBB:
        buys["ORE"] = True
        buys["ORGANICS"] = True
        buys["EQUIPMENT"] = True

    # Initial stocks
    stock = {}
    max_stock = {}
    for comm in ["ORE", "ORGANICS", "EQUIPMENT"]:
        cap = rng.randint(600, 1200)
        max_stock[comm] = cap
        if sells[comm]:
            stock[comm] = rng.randint(int(cap * 0.45), int(cap * 0.85))
        elif buys[comm]:
            stock[comm] = rng.randint(int(cap * 0.15), int(cap * 0.40))
        else:
            stock[comm] = 0

    p_name = rng.choice(PORT_NAMES) + f" #{sector_id}"
    return Port(
        sector_id=sector_id,
        name=p_name,
        port_class=port_class,
        stock=stock,
        max_stock=max_stock,
        buys=buys,
        sells=sells,
    )


def generate_universe(total_sectors: int = TOTAL_SECTORS, seed: int = 42) -> Dict[int, Sector]:
    """
    Generates a deterministic universe graph with guaranteed connectivity.
    """
    rng = random.Random(seed)
    sectors: Dict[int, Sector] = {}

    # Initialize sector structures
    for s_id in range(1, total_sectors + 1):
        sec_level = determine_security(s_id)
        if s_id == 1:
            name = "Sol Federation Central"
        else:
            adj = rng.choice(SECTOR_ADJECTIVES)
            noun = rng.choice(SECTOR_NOUNS)
            name = f"{adj} {noun}"

        sectors[s_id] = Sector(
            id=s_id,
            name=name,
            security=sec_level,
            warps=[],
            port=None,
            planets=[],
            captains=[]
        )

    # 1. Guarantee complete reachability using a random spanning tree from Sector 1
    connected = [1]
    unconnected = list(range(2, total_sectors + 1))
    rng.shuffle(unconnected)

    while unconnected:
        u = unconnected.pop()
        # Connect to a random node already connected (prefer nearby sector IDs for local clustering)
        # Weight towards closer IDs
        candidates = sorted(connected, key=lambda c: abs(c - u))[:6]
        c = rng.choice(candidates)
        sectors[c].warps.append(u)
        sectors[u].warps.append(c)
        connected.append(u)

    # 2. Add additional random bidirectional warp lanes to create loops and alternate routes
    for s_id in range(1, total_sectors + 1):
        target_warps = rng.randint(3, 5)
        attempts = 0
        while len(sectors[s_id].warps) < target_warps and attempts < 15:
            attempts += 1
            # Prefer sectors within a reasonable numeric range
            neighbor_pool = [
                n for n in range(max(1, s_id - 12), min(total_sectors + 1, s_id + 13))
                if n != s_id and n not in sectors[s_id].warps
            ]
            if not neighbor_pool:
                neighbor_pool = [
                    n for n in range(1, total_sectors + 1)
                    if n != s_id and n not in sectors[s_id].warps
                ]
            if neighbor_pool:
                cand = rng.choice(neighbor_pool)
                if len(sectors[cand].warps) < 6:
                    sectors[s_id].warps.append(cand)
                    sectors[cand].warps.append(s_id)

    # Sort warps for clean presentation
    for s_id in sectors:
        sectors[s_id].warps = sorted(list(set(sectors[s_id].warps)))

    # 3. Distribute Ports (~65% of sectors)
    # Sector 1 ALWAYS has Stardock
    sectors[1].port = build_port(1, rng)
    for s_id in range(2, total_sectors + 1):
        if rng.random() < 0.65:
            sectors[s_id].port = build_port(s_id, rng)

    # 4. Distribute Planets (BRE / SRE style colonization targets)
    planet_sectors = rng.sample(range(2, total_sectors + 1), k=len(PLANET_NAMES))
    for idx, s_id in enumerate(planet_sectors):
        p_name = PLANET_NAMES[idx]
        planet = Planet(
            id=f"planet_{s_id}",
            sector_id=s_id,
            name=p_name,
            owner_id=None,
            population=rng.randint(300, 1500),
            shields=rng.randint(50, 150),
            max_shields=200,
            fighters=rng.randint(10, 40),
            citadel_level=0,
            treasury=rng.randint(200, 1200),
            ore_silo=rng.randint(20, 100),
            organics_silo=rng.randint(20, 100),
        )
        sectors[s_id].planets.append(planet)

    return sectors
