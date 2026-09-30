"""
Universe graph generation for Xylarium.
Creates a deterministic 100-sector star network with warp lanes,
ports, planetary bodies, and security classification.
"""

import random
from typing import Any, Dict, List, Optional
from xylarium.config import (
    PLANET_TYPES,
    HABITABILITY,
    CLADE_HOMEWORLD,
    METABOLISM_HOMEWORLD,
    PLANET_TYPE_DEPOSITS,
    SYSTEM_PORT_CHANCE,
    SYSTEM_PLANETS,
    STAR_TYPES,
    BELT_CHANCE,
    BELT_TYPES,
    BELT_RESERVE_RANGE,
    PRICE_LEVEL,
    PORT_START_TREASURY,
    STARDOCK_START_TREASURY,
    TOTAL_SECTORS,
    FEDERATION_SECTOR_START,
    FEDERATION_SECTOR_END,
    BORDER_SECTOR_END,
    ORBIT_MIN_RADIUS_AU,
    ORBIT_MAX_RADIUS_AU,
    FOUNDING_SPACE_RESERVE,
)
from xylarium.kernel.models import (
    Sector,
    Port,
    Planet,
    SecurityLevel,
    PortClass,
    CommodityType,
)
from xylarium.kernel.civilization import FOUNDING_POLITIES, CivilizationIntelligenceEngine
from xylarium.kernel.elements import PeriodicTable
from xylarium.kernel import physics


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

    furnish_sectors(sectors, list(range(1, total_sectors + 1)), rng, seed, found_polities=True)
    return sectors


# ---------------------------------------------------------------------------
# Star systems & null space
# ---------------------------------------------------------------------------

PLANET_LETTERS = ["b", "c", "d", "e", "f"]


def homeworld_type(polity: Dict[str, Any]) -> str:
    """Species arise on worlds suited to their biology: clade first, then metabolism."""
    return CLADE_HOMEWORLD.get(polity.get("clade", ""), METABOLISM_HOMEWORLD.get(polity.get("metabolism", "biotic"), "TERRESTRIAL"))


def habitability(metabolism: str, planet_type: str) -> float:
    return HABITABILITY.get(metabolism, HABITABILITY["biotic"]).get(planet_type, 0.0)


def warp_distances(sectors: Dict[int, Sector], origin: int = 1) -> Dict[int, int]:
    dist = {origin: 0}
    frontier = [origin]
    while frontier:
        nxt = []
        for cur in frontier:
            for w in sectors[cur].warps:
                if w in sectors and w not in dist:
                    dist[w] = dist[cur] + 1
                    nxt.append(w)
        frontier = nxt
    return dist


def _deposits_for(planet_type: str, rng: random.Random) -> Dict[str, int]:
    return {e: rng.randint(60, 240) for e in PLANET_TYPE_DEPOSITS.get(planet_type, ["Fe", "Si"])}


def make_belt(sector_id: int, idx: int, rng: random.Random) -> Dict[str, Any]:
    belt_type = rng.choice(list(BELT_TYPES))
    reserve = rng.randint(*BELT_RESERVE_RANGE)
    return {
        "id": f"BELT-{sector_id:03d}-{idx}",
        "type": belt_type,
        "composition": dict(BELT_TYPES[belt_type]),
        "reserve": reserve,
        "max_reserve": reserve,
    }


def furnish_sectors(
    sectors: Dict[int, Sector],
    sector_ids: List[int],
    rng: random.Random,
    seed: int,
    found_polities: bool = False,
    force_system: Optional[int] = 1,
) -> None:
    """
    Lays out star systems separated by null space among ``sector_ids``.
    Systems form an independent set of the warp graph (no two systems adjacent), so
    every jump between systems crosses null space. Systems host a star, usually a
    starport, and 1-4 planets of varied types; null sectors may hold asteroid belts.
    Founding polities arise on worlds of their homeworld type; every other world starts
    uninhabited and settleable.
    """
    from xylarium.kernel.fx import currency_for_security

    dist = warp_distances(sectors, 1)
    order = list(sector_ids)
    rng.shuffle(order)
    systems: List[int] = []
    chosen = set()
    if force_system in sector_ids:
        order.remove(force_system)
        order.insert(0, force_system)
    for s_id in order:
        if any(w in chosen for w in sectors[s_id].warps):
            continue
        chosen.add(s_id)
        systems.append(s_id)

    for s_id in sector_ids:
        sec = sectors[s_id]
        currency = currency_for_security(sec.security)
        if s_id in chosen:
            sec.kind = "SYSTEM"
            sec.star_type = "G-class yellow dwarf (Sol)" if s_id == 1 else rng.choice(STAR_TYPES)
            sec.star = physics.star_for(sec.star_type)
            if s_id == 1 or rng.random() < SYSTEM_PORT_CHANCE:
                sec.port = build_port(s_id, rng)
                sec.port.currency = currency
                sec.port.remoteness = dist.get(s_id, 0)
                base = STARDOCK_START_TREASURY if s_id == 1 else PORT_START_TREASURY
                sec.port.treasury = int(base * PRICE_LEVEL.get(currency, 1.0))
            if s_id == 1:
                _found_sol_core_worlds(sec)
            if s_id != 1:
                # Worlds sit on exact, non-crossing orbits; each world's type follows from its light and mass
                layout = physics.lay_out_system(sec, rng.randint(*SYSTEM_PLANETS), rng)
                for i, (q, b, ptype) in enumerate(layout):
                    planet = Planet(
                        id=f"planet_{s_id}" if i == 0 else f"planet_{s_id}_{PLANET_LETTERS[i]}",
                        sector_id=s_id,
                        name=f"{sec.name.split()[0]} {s_id:03d}{PLANET_LETTERS[i]}",
                        owner_id=None,
                        population=0,
                        shields=0,
                        max_shields=200,
                        fighters=0,
                        citadel_level=0,
                        treasury=0,
                        ore_silo=0,
                        organics_silo=0,
                        morale=80,
                        element_deposits=_deposits_for(ptype, rng),
                        garrison_troops=0,
                        planet_type=ptype,
                        currency=currency,
                        body=b,
                    )
                    physics.apply_derived(planet, physics.star(sec))
                    planet.orbital_angle = float(physics.orbital_phase(sec, planet, 0)) * 360.0
                    sec.planets.append(planet)
        else:
            sec.kind = "NULL"
            sec.port = None
            sec.planets = []
            if rng.random() < BELT_CHANCE:
                sec.belts = [make_belt(s_id, 1, rng)]
                if rng.random() < 0.25:
                    sec.belts.append(make_belt(s_id, 2, rng))

    # Ancient precursor ruins beneath a share of today's uninhabited worlds
    from xylarium.kernel.archaeology import ArchaeologyManager
    ArchaeologyManager.seed_precursor_ruins({s: sectors[s] for s in sector_ids}, rng)

    # Non-spacefaring locals on a share of the worlds whose type suits some biology
    from xylarium.kernel.natives import NativeManager
    NativeManager.seed({s: sectors[s] for s in sector_ids}, rng)

    if not found_polities:
        return

    # Species genesis: each founding polity arises on a world of its homeworld type
    candidates = [s for s in systems if s != 1 and sectors[s].planets]
    rng.shuffle(candidates)
    used_systems = set()
    for idx, polity in enumerate(FOUNDING_POLITIES):
        if idx >= len(candidates) or idx >= len(PLANET_NAMES):
            break
        want = homeworld_type(polity)
        # Space is kept for those who come later (great powers, settlers): once free systems run short,
        # peoples arise on other worlds of already-inhabited systems instead of claiming every star
        crowded = len(candidates) - len(used_systems) <= len(candidates) * FOUNDING_SPACE_RESERVE
        pool = [sid for sid in candidates if crowded or sid not in used_systems]
        # Species arise where the light and the world suit them: find a world physics already made so
        home = next((p for sid in pool for p in sectors[sid].planets
                     if p.planet_type == want and p.civilization is None), None)
        if home is None:
            # No such world anywhere: a species' world is re-seated on an orbit whose light fits it
            spare = [(sid, p) for sid in pool for p in sectors[sid].planets if p.civilization is None]
            if not spare:
                break
            sid, home = spare[0]
            physics.reseat(sectors[sid], home, want)
        sec = sectors[home.sector_id]
        used_systems.add(sec.id)
        civ = CivilizationIntelligenceEngine.create_civilization(polity)
        deposits = _deposits_for(home.planet_type, rng)
        reserves: Dict[str, int] = {}
        for elem_id in civ.discovered_elements:
            deposits.setdefault(elem_id, rng.randint(120, 300))
            reserves[elem_id] = rng.randint(15, 35)
        for me in PeriodicTable.get_elements_for_metabolism(civ.metabolism):
            deposits.setdefault(me.element_id, rng.randint(80, 200))
        home.name = PLANET_NAMES[idx]
        home.civilization = civ
        home.population = rng.randint(300, 1500)
        home.shields = rng.randint(50, 150)
        home.fighters = rng.randint(10, 40)
        home.treasury = int(rng.randint(200, 1200) * PRICE_LEVEL.get(home.currency, 1.0))
        home.ore_silo = rng.randint(20, 100)
        home.organics_silo = rng.randint(20, 100)
        home.morale = 100
        home.element_deposits = deposits
        home.element_reserves = reserves
        home.garrison_troops = rng.randint(15, 40)
        home.natives = None


def _found_sol_core_worlds(sec: Sector) -> None:
    """Terra and Luna: the Federation's populated core, taxed in SOL and not open to annexation."""
    from xylarium.config import TERRAN_POLITY, SOL_CORE_WORLDS
    for i, spec in enumerate(SOL_CORE_WORLDS):
        civ = CivilizationIntelligenceEngine.create_civilization(dict(TERRAN_POLITY))
        sec.planets.append(Planet(
            id="planet_1" if i == 0 else f"planet_1_{PLANET_LETTERS[i]}",
            sector_id=1,
            name=spec["name"],
            owner_id=None,
            population=spec["population"],
            shields=3000,
            max_shields=3000,
            fighters=1000,
            citadel_level=spec["citadel"],
            treasury=50000,
            ore_silo=2000,
            organics_silo=4000,
            morale=100,
            civilization=civ,
            element_deposits=_deposits_for(spec["type"], random.Random(1 + i)),
            element_reserves={"H2O": 500, "Fe": 300},
            planet_type=spec["type"],
            currency="SOL",
            garrison_troops=5000,
            body=spec.get("body"),
            moon_of=spec.get("moon_of"),
        ))
        physics.apply_derived(sec.planets[-1], physics.star(sec))
