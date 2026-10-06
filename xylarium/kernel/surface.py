"""
Planetary Surface Hex/District Grid & Ground Invasion Engine for Xylarium.
Ported from Netstratum 02_COLONY_LOOP and 36_DEFENSE_AXIOMS.
Implements an 8x8 procedural terrain district grid, spatial adjacency synergies,
troop training, and drop-pod ground assault invasion warfare.
"""

from dataclasses import dataclass, field
from enum import Enum
import zlib
import random
import math
from typing import Dict, List, Optional, Tuple, Any

from xylarium.kernel import matter, uses
from xylarium.config import (
    SURFACE_GRID_WIDTH,
    SURFACE_GRID_HEIGHT,
    SURFACE_DISTRICT_UNITS,
    SURFACE_DISTRICT_COST_CREDITS,
    SURFACE_TROOP_RECRUIT_COST,
    SURFACE_TROOP_RECRUIT_ORE,
)
from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet


class TerrainType(str, Enum):
    PLAINS = "PLAINS"                      # Standard land (1.0x baseline)
    MOUNTAINS = "MOUNTAINS"                # Rocky mineral crust (1.5x ore yield)
    GEOTHERMAL_VENT = "GEOTHERMAL_VENT"    # Fissure power source (2.0x energy/shields)
    GLACIAL_LAKE = "GLACIAL_LAKE"          # Volatile ice/water basin (1.5x organics)
    MINERAL_RIDGE = "MINERAL_RIDGE"        # Metalloid spine (1.8x ore yield)
    HYDROCARBON_BASIN = "HYDROCARBON_BASIN"# Deep biological loam (1.8x organics)


class DistrictType(str, Enum):
    EMPTY = "EMPTY"                        # Undeveloped wild terrain
    HABITATION_DOME = "HABITATION_DOME"    # +500 max population, +5% morale
    HYDROPONIC_SPIRE = "HYDROPONIC_SPIRE"  # +15 organics / tick
    MANTLE_BORE = "MANTLE_BORE"            # +15 ore / tick
    GEOTHERMAL_DYNAMO = "GEOTHERMAL_DYNAMO"# +25 planetary shields / tick
    ELEMENT_REFINERY = "ELEMENT_REFINERY"  # +2 refined periodic elements / tick
    CITADEL_FORTRESS = "CITADEL_FORTRESS"  # +30 garrison defense, +50 max shields
    MILITARY_BARRACKS = "MILITARY_BARRACKS"# Allows recruitment of assault divisions
    RESORT_DOME = "RESORT_DOME"            # [RC] Pleasure Dome: hosts tourists, drinks water (tourism.py)


TERRAIN_GLYPHS = {
    TerrainType.PLAINS: ".",
    TerrainType.MOUNTAINS: "^",
    TerrainType.GEOTHERMAL_VENT: "~",
    TerrainType.GLACIAL_LAKE: "*",
    TerrainType.MINERAL_RIDGE: "#",
    TerrainType.HYDROCARBON_BASIN: "%",
}

DISTRICT_GLYPHS = {
    DistrictType.EMPTY: " ",
    DistrictType.HABITATION_DOME: "H",
    DistrictType.HYDROPONIC_SPIRE: "G",
    DistrictType.MANTLE_BORE: "M",
    DistrictType.GEOTHERMAL_DYNAMO: "E",
    DistrictType.ELEMENT_REFINERY: "R",
    DistrictType.CITADEL_FORTRESS: "C",
    DistrictType.MILITARY_BARRACKS: "B",
    DistrictType.RESORT_DOME: "L",
}


def ledger_kernel() -> Any:
    from xylarium.kernel import ledger
    return ledger.active_kernel()


def _built_of(planet: Any) -> Dict[str, Dict[str, int]]:
    """What each district on a world is made of, by tile, so what is pulled down returns as itself."""
    return planet.society.setdefault("built_of", {})


def _district_matter(kernel: Any, planet: Any) -> List[Tuple[str, int]]:
    """A district's matter: the cheapest at the world that holds its shape where it stands (uses.site_t)."""
    if kernel is None:
        return []
    t = uses.site_t(kernel, planet)
    return uses.build_with(kernel, planet, t, SURFACE_DISTRICT_UNITS) if t is not None else []


def _rock_holds(kernel: Any, planet: Any) -> bool:
    t = uses.site_t(kernel, planet) if kernel is not None else None
    return t is None or uses.solid_at(uses.ROCK, t)


@dataclass
class SurfaceTile:
    x: int
    y: int
    terrain: TerrainType
    district: DistrictType = DistrictType.EMPTY
    level: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "terrain": self.terrain.value,
            "district": self.district.value,
            "level": self.level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SurfaceTile":
        return cls(
            x=data["x"],
            y=data["y"],
            terrain=TerrainType(data["terrain"]),
            district=DistrictType(data["district"]),
            level=data.get("level", 1),
        )


class SurfaceGrid:
    """
    8x8 district grid managing terrain, buildings, adjacency bonuses,
    and ground garrison defense on a planetary surface.
    """

    def __init__(
        self,
        width: int = SURFACE_GRID_WIDTH,
        height: int = SURFACE_GRID_HEIGHT,
        tiles: Optional[List[SurfaceTile]] = None,
        seed: Optional[int] = None,
    ):
        self.width = width
        self.height = height
        if tiles is not None:
            self.tiles = tiles
        else:
            self.tiles = self._generate_terrain(seed or random.randint(1, 999999))

    def _generate_terrain(self, seed: int) -> List[SurfaceTile]:
        rng = random.Random(seed)
        terrain_choices = [
            (TerrainType.PLAINS, 40),
            (TerrainType.MOUNTAINS, 18),
            (TerrainType.GEOTHERMAL_VENT, 10),
            (TerrainType.GLACIAL_LAKE, 14),
            (TerrainType.MINERAL_RIDGE, 10),
            (TerrainType.HYDROCARBON_BASIN, 8),
        ]
        types, weights = zip(*terrain_choices)

        grid = []
        for y in range(self.height):
            for x in range(self.width):
                t = rng.choices(types, weights=weights, k=1)[0]
                grid.append(SurfaceTile(x=x, y=y, terrain=t, district=DistrictType.EMPTY))
        return grid

    def get_tile(self, x: int, y: int) -> Optional[SurfaceTile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y * self.width + x]
        return None

    def get_neighbors(self, x: int, y: int) -> List[SurfaceTile]:
        neighbors = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            tile = self.get_tile(nx, ny)
            if tile:
                neighbors.append(tile)
        return neighbors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "tiles": [t.to_dict() for t in self.tiles],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SurfaceGrid":
        tiles = [SurfaceTile.from_dict(t) for t in data.get("tiles", [])]
        return cls(
            width=data.get("width", SURFACE_GRID_WIDTH),
            height=data.get("height", SURFACE_GRID_HEIGHT),
            tiles=tiles,
        )

    def calculate_yields(self, planet: Planet) -> Dict[str, float]:
        """
        Calculates per-cycle net resource generation from districts, terrain multipliers,
        and 4-way orthogonal adjacency synergies.
        """
        net = {
            "ore": 0.0,
            "organics": 0.0,
            "shields": 0.0,
            "max_population_bonus": 0,
            "fortress_defense": 0,
            "refinery_units": 0,
        }

        for tile in self.tiles:
            if tile.district == DistrictType.EMPTY:
                continue

            neighbors = self.get_neighbors(tile.x, tile.y)
            neighbor_districts = [n.district for n in neighbors]

            if tile.district == DistrictType.MANTLE_BORE:
                base_ore = 15.0 * tile.level
                # Terrain multiplier
                if tile.terrain in [TerrainType.MOUNTAINS, TerrainType.MINERAL_RIDGE]:
                    base_ore *= 1.6
                # Adjacency: Mantle Bore adjacent to Element Refinery
                if DistrictType.ELEMENT_REFINERY in neighbor_districts:
                    base_ore *= 1.25
                net["ore"] += base_ore

            elif tile.district == DistrictType.HYDROPONIC_SPIRE:
                base_org = 15.0 * tile.level
                # Terrain multiplier
                if tile.terrain in [TerrainType.GLACIAL_LAKE, TerrainType.HYDROCARBON_BASIN]:
                    base_org *= 1.6
                # Adjacency: Hydroponic Spire adjacent to Habitation Dome
                if DistrictType.HABITATION_DOME in neighbor_districts:
                    base_org *= 1.20
                net["organics"] += base_org

            elif tile.district == DistrictType.GEOTHERMAL_DYNAMO:
                base_pow = 25.0 * tile.level
                if tile.terrain == TerrainType.GEOTHERMAL_VENT:
                    base_pow *= 2.0
                net["shields"] += base_pow

            elif tile.district == DistrictType.HABITATION_DOME:
                net["max_population_bonus"] += 500 * tile.level

            elif tile.district == DistrictType.ELEMENT_REFINERY:
                ref_units = 2 * tile.level
                if DistrictType.MANTLE_BORE in neighbor_districts:
                    ref_units += 1
                net["refinery_units"] += ref_units

            elif tile.district == DistrictType.CITADEL_FORTRESS:
                base_def = 30 * tile.level
                if DistrictType.GEOTHERMAL_DYNAMO in neighbor_districts:
                    base_def += 15
                net["fortress_defense"] += base_def

            elif tile.district == DistrictType.MILITARY_BARRACKS:
                net["fortress_defense"] += 10 * tile.level

        return net

    def render_map(self) -> List[str]:
        """
        Renders a dual ASCII representation: Terrain map side-by-side with District grid.
        """
        lines = []
        lines.append("  [ SURFACE TERRAIN ]             [ ZONED DISTRICTS ]")
        lines.append("  0 1 2 3 4 5 6 7                 0 1 2 3 4 5 6 7")
        lines.append(" +---------------+               +---------------+")

        for y in range(self.height):
            terrain_row = []
            district_row = []
            for x in range(self.width):
                tile = self.get_tile(x, y)
                if tile:
                    terrain_row.append(TERRAIN_GLYPHS.get(tile.terrain, "."))
                    district_row.append(DISTRICT_GLYPHS.get(tile.district, " "))
                else:
                    terrain_row.append(" ")
                    district_row.append(" ")

            t_str = " ".join(terrain_row)
            d_str = " ".join(district_row)
            lines.append(f"{y}|{t_str}|             {y}|{d_str}|")

        lines.append(" +---------------+               +---------------+")
        lines.append(" Terrain: . Plains, ^ Mountain, ~ Geothermal, * Glacial, # Ridge, % Basin")
        lines.append(" Districts: H Hab, G Hydro, M Mine, E Energy, R Refinery, C Citadel, B Barracks")
        return lines


# planet.id -> (surface_grid dict it was parsed from, parsed SurfaceGrid)
_GRID_CACHE: Dict[str, Tuple[Dict[str, Any], "SurfaceGrid"]] = {}


def _pay_builders(planet: Any, amount: int) -> None:
    """A colony governor's district is built by the region's contractors: its cost reaches them."""
    from xylarium.kernel.colony import ColonyManager
    from xylarium.kernel import ledger
    ColonyManager._pay_local(planet, ledger.active_kernel(), amount)


class SurfaceManager:
    """
    Orchestrates planetary surface construction, demolition, troop recruitment,
    ground invasion resolutions, and per-cycle simulation ticks.
    """

    @staticmethod
    def ensure_surface_grid(planet: Planet) -> SurfaceGrid:
        """Ensures the planet has an instantiated SurfaceGrid object."""
        if planet.surface_grid is None:
            grid = SurfaceGrid(seed=zlib.crc32(planet.id.encode()) % 1000000)
            planet.surface_grid = grid.to_dict()
            _GRID_CACHE[planet.id] = (planet.surface_grid, grid)
            return grid
        # Every mutation writes back a fresh dict via grid.to_dict(), so the parsed
        # grid stays valid for as long as planet.surface_grid is the same object.
        cached = _GRID_CACHE.get(planet.id)
        if cached and cached[0] is planet.surface_grid:
            return cached[1]
        grid = SurfaceGrid.from_dict(planet.surface_grid)
        _GRID_CACHE[planet.id] = (planet.surface_grid, grid)
        return grid

    @staticmethod
    def build_district(
        captain: Captain,
        planet: Planet,
        x: int,
        y: int,
        district: DistrictType,
    ) -> ActionResult:
        """
        Zones and constructs a district on the specified planet surface tile.
        """
        if planet.owner_id is not None and planet.owner_id != captain.id:
            return ActionResult(
                success=False,
                message=f"Access denied: Planet {planet.name} is owned by another entity.",
                action_type=ActionType.SURFACE_BUILD_DISTRICT,
            )

        if district == DistrictType.EMPTY:
            return ActionResult(
                success=False,
                message="Cannot build EMPTY district. Use demolish instead.",
                action_type=ActionType.SURFACE_BUILD_DISTRICT,
            )

        grid = SurfaceManager.ensure_surface_grid(planet)
        tile = grid.get_tile(x, y)
        if not tile:
            return ActionResult(
                success=False,
                message=f"Invalid tile coordinates ({x}, {y}). Grid is {grid.width}x{grid.height}.",
                action_type=ActionType.SURFACE_BUILD_DISTRICT,
            )

        if tile.district != DistrictType.EMPTY:
            return ActionResult(
                success=False,
                message=f"Tile ({x}, {y}) already zoned as {tile.district.name}. Demolish first.",
                action_type=ActionType.SURFACE_BUILD_DISTRICT,
            )

        # Check costs: credits, and matter that holds its shape where it stands (uses.py)
        cost_cr = SURFACE_DISTRICT_COST_CREDITS
        kernel = ledger_kernel()
        parts = _district_matter(kernel, planet)

        # Can draw from captain credits or planetary treasury
        if captain.credits < cost_cr and planet.treasury < cost_cr:
            return ActionResult(
                success=False,
                message=f"Insufficient credits to build {district.name} ({cost_cr} Cr required).",
                action_type=ActionType.SURFACE_BUILD_DISTRICT,
            )

        from_hold = not parts and _rock_holds(kernel, planet) and \
            captain.ship.cargo.unbonded("ORE") >= SURFACE_DISTRICT_UNITS
        if not parts and not from_hold:
            return ActionResult(
                success=False,
                message=f"Nothing here holds {district.name}'s shape where it stands "
                        f"({SURFACE_DISTRICT_UNITS} units of matter solid at its site required).",
                action_type=ActionType.SURFACE_BUILD_DISTRICT,
            )

        # Deduct costs: the builders are the region's contractors (paid, not vanished)
        from xylarium.kernel.colony import ColonyManager
        from xylarium.kernel import ledger
        if captain.credits >= cost_cr:
            captain.credits -= cost_cr
            ColonyManager._pay_contractor_sol(planet, cost_cr)
        else:
            planet.treasury -= cost_cr
            ColonyManager._pay_local(planet, ledger.active_kernel(), cost_cr)

        if parts:
            made = uses.draw(kernel, planet, parts, "construction")
        else:
            matter.consume(captain.ship.cargo, "ore", "ORE", SURFACE_DISTRICT_UNITS, "construction")
            made = {"ORE": SURFACE_DISTRICT_UNITS}

        # Build
        tile.district = district
        _built_of(planet)[f"{x},{y}"] = made
        from xylarium.kernel.experience import ExperienceManager
        from xylarium.config import XP_INDUSTRY_DISTRICT
        ExperienceManager.award(captain, "industry", XP_INDUSTRY_DISTRICT, None, key=f"district:{planet.id}")
        planet.surface_grid = grid.to_dict()

        # If Citadel Fortress built, immediately boost planetary defense
        if district == DistrictType.CITADEL_FORTRESS:
            planet.garrison_troops += 15
            planet.max_shields += 50
            planet.shields = min(planet.max_shields, planet.shields + 50)

        return ActionResult(
            success=True,
            message=f"Constructed {district.name} at coordinates ({x}, {y}) on {planet.name}.",
            action_type=ActionType.SURFACE_BUILD_DISTRICT,
            data={"x": x, "y": y, "district": district.value},
        )

    @staticmethod
    def demolish_district(
        captain: Captain,
        planet: Planet,
        x: int,
        y: int,
    ) -> ActionResult:
        """
        Demolishes a district, recovering half of its base material and credit investment.
        """
        if planet.owner_id is not None and planet.owner_id != captain.id:
            return ActionResult(
                success=False,
                message="Access denied: Cannot demolish facilities on a foreign world.",
                action_type=ActionType.SURFACE_DEMOLISH_DISTRICT,
            )

        grid = SurfaceManager.ensure_surface_grid(planet)
        tile = grid.get_tile(x, y)
        if not tile or tile.district == DistrictType.EMPTY:
            return ActionResult(
                success=False,
                message=f"Tile ({x}, {y}) is already empty.",
                action_type=ActionType.SURFACE_DEMOLISH_DISTRICT,
            )

        salvage_cr = SURFACE_DISTRICT_COST_CREDITS // 2
        made = _built_of(planet).pop(f"{x},{y}", None) or {"ORE": SURFACE_DISTRICT_UNITS}   # unrecorded: older rock

        old_district = tile.district
        tile.district = DistrictType.EMPTY
        planet.surface_grid = grid.to_dict()

        # The salvaged fittings are bought by the region's contractors (out of their own treasury)
        from xylarium.kernel.colony import ColonyManager
        from xylarium.kernel import ledger
        from xylarium.kernel.market import ledger_debit_port_sol, ledger_sol_of
        buyer = ColonyManager._contractor_port(planet, ledger.active_kernel())
        salvage_cr = min(salvage_cr, max(0, ledger_sol_of(buyer))) if buyer is not None else 0
        if buyer is not None:
            ledger_debit_port_sol(buyer, salvage_cr)
        captain.credits += salvage_cr
        back = uses.salvage(planet, made, 0.5, "demolition_salvage")
        got = ", ".join(f"{q} {m}" for m, q in back.items()) or "nothing"

        return ActionResult(
            success=True,
            message=f"Demolished {old_district.name} at ({x}, {y}). Salvaged {salvage_cr} Cr and {got}.",
            action_type=ActionType.SURFACE_DEMOLISH_DISTRICT,
            data={"salvage_credits": salvage_cr, "salvage_matter": back, "salvage_ore": back.get("ORE", 0)},
        )

    @staticmethod
    def recruit_troops(
        captain: Captain,
        planet: Planet,
        divisions: int,
    ) -> ActionResult:
        """
        Recruits assault troop divisions from an owned world equipped with Military Barracks.
        """
        if divisions <= 0:
            return ActionResult(
                success=False,
                message="Division recruitment count must be greater than zero.",
                action_type=ActionType.SURFACE_RECRUIT_TROOPS,
            )

        grid = SurfaceManager.ensure_surface_grid(planet)
        has_barracks = any(t.district == DistrictType.MILITARY_BARRACKS for t in grid.tiles)
        if not has_barracks:
            return ActionResult(
                success=False,
                message=f"World {planet.name} lacks a Military Barracks. Construct one before raising assault divisions.",
                action_type=ActionType.SURFACE_RECRUIT_TROOPS,
            )

        cost_cr = divisions * SURFACE_TROOP_RECRUIT_COST
        cost_ore = divisions * SURFACE_TROOP_RECRUIT_ORE

        if captain.credits < cost_cr:
            return ActionResult(
                success=False,
                message=f"Insufficient credits for recruitment ({captain.credits}/{cost_cr} Cr).",
                action_type=ActionType.SURFACE_RECRUIT_TROOPS,
            )

        if planet.ore_silo < cost_ore and captain.ship.cargo.unbonded("ORE") < cost_ore:
            return ActionResult(
                success=False,
                message=f"Insufficient ore for troop armor ({cost_ore} Ore required).",
                action_type=ActionType.SURFACE_RECRUIT_TROOPS,
            )

        captain.credits -= cost_cr
        if planet.ore_silo >= cost_ore:
            matter.consume(planet, "ore_silo", "ORE", cost_ore, "troop_armor")
        else:
            matter.consume(captain.ship.cargo, "ore", "ORE", cost_ore, "troop_armor")

        captain.troops += divisions

        return ActionResult(
            success=True,
            message=f"Muster complete! Commissioned {divisions} assault divisions for Captain {captain.name}. (Total: {captain.troops})",
            action_type=ActionType.SURFACE_RECRUIT_TROOPS,
            data={"divisions": divisions, "total_troops": captain.troops},
        )

    @staticmethod
    def invade_planet(
        attacker: Captain,
        target_planet: Planet,
        divisions_to_commit: int,
    ) -> ActionResult:
        """
        Executes a planetary ground invasion using orbital drop-pods.
        Resolves ground combat rounds against planetary garrison divisions and fortress networks.
        """
        if attacker.sector_id != target_planet.sector_id:
            return ActionResult(
                success=False,
                message=f"Invading ship is in Sector {attacker.sector_id}, but {target_planet.name} is in Sector {target_planet.sector_id}.",
                action_type=ActionType.SURFACE_INVADE,
            )

        if target_planet.owner_id == attacker.id:
            return ActionResult(
                success=False,
                message=f"Captain already owns {target_planet.name}.",
                action_type=ActionType.SURFACE_INVADE,
            )

        if attacker.troops <= 0:
            return ActionResult(
                success=False,
                message="You have no assault troop divisions aboard your ship.",
                action_type=ActionType.SURFACE_INVADE,
            )

        committed = min(attacker.troops, max(1, divisions_to_commit))
        grid = SurfaceManager.ensure_surface_grid(target_planet)
        yields = grid.calculate_yields(target_planet)
        fortress_bonus = yields.get("fortress_defense", 0)

        defender_force = target_planet.garrison_troops + int(fortress_bonus * 0.5)

        # Ground combat simulation
        attacker_losses = 0
        defender_losses = 0

        # Lanchester's square law: the expected outcome of the exchange (occupation.lanchester)
        from xylarium.kernel import occupation
        fight = occupation.lanchester(float(committed), float(defender_force))
        attacker_effective, defender_effective = float(committed), float(defender_force)

        if fight["won"]:
            # Attacker victory: the survivors garrison the world
            defender_losses = target_planet.garrison_troops
            left = int(fight["attacker_left"])
            attacker_losses = committed - left
            target_planet.garrison_troops = max(1, left)
            attacker.troops -= committed

            old_owner = target_planet.owner_id
            from xylarium.kernel import ledger
            if ledger.ACTIVE_KERNEL is not None:
                occupation.conquer(ledger.ACTIVE_KERNEL, target_planet, attacker, "ground invasion")
            target_planet.owner_id = attacker.id

            # Plunder 40% of treasury
            plunder_cr = int(target_planet.treasury * 0.40)
            target_planet.treasury -= plunder_cr
            from xylarium.kernel.fx import credit
            credit(attacker, target_planet.currency, plunder_cr)

            # Possible collateral damage to one district
            demolished_district = None
            occupied_tiles = [t for t in grid.tiles if t.district != DistrictType.EMPTY]
            if occupied_tiles and defender_effective * 2 > attacker_effective:      # a close fight levels a district
                casualty_tile = occupied_tiles[0]
                demolished_district = casualty_tile.district.name
                casualty_tile.district = DistrictType.EMPTY
                target_planet.surface_grid = grid.to_dict()

            msg = (
                f"GROUND INVASION SUCCESSFUL! Assault divisions captured {target_planet.name}. "
                f"Lost {attacker_losses} divisions. Captured {plunder_cr:,} Cr in spoils."
            )
            if demolished_district:
                msg += f" Collateral bombardment collapsed a {demolished_district}."

            return ActionResult(
                success=True,
                message=msg,
                action_type=ActionType.SURFACE_INVADE,
                data={
                    "conquered": True,
                    "attacker_losses": attacker_losses,
                    "plunder_credits": plunder_cr,
                    "new_owner": attacker.id,
                },
            )
        else:
            # Defender repels invasion
            attacker_losses = committed
            attacker.troops -= committed
            defender_losses = min(target_planet.garrison_troops, int(attacker_effective * 0.4))
            target_planet.garrison_troops = max(1, target_planet.garrison_troops - defender_losses)

            return ActionResult(
                success=False,
                message=(
                    f"INVASION REPELLED! Planetary defense forces decimated all {committed} drop divisions. "
                    f"Enemy sustained {defender_losses} garrison casualties."
                ),
                action_type=ActionType.SURFACE_INVADE,
                data={"conquered": False, "attacker_losses": committed, "defender_losses": defender_losses},
            )

    @staticmethod
    def tick_surface(planet: Planet) -> None:
        """
        Advances resource collection on planet surface grid:
        1. Applies ore, organics, shield regeneration, and refined periodic elements.
        2. Catalyzes periodic element reserves: H2O/C boost organics; Fe/Ti boost ore.
        3. Autonomous colony governor zones critical infrastructure when treasury > 10,000 Cr.
        """
        from xylarium.kernel import ledger, zones
        k = ledger.active_kernel()
        if k is not None and zones.is_folded(k, planet):
            return                                        # a folded people's grounds wait with its history
        grid = SurfaceManager.ensure_surface_grid(planet)
        yields = grid.calculate_yields(planet)

        # 1. Base district resource production
        base_ore = int(yields["ore"])
        base_org = int(yields["organics"])

        # 2. Catalytic Periodic Element Consumption:
        # Hydroponic Spires consume H2O or C from planetary reserves to boost food yield
        hydro_count = sum(1 for t in grid.tiles if t.district == DistrictType.HYDROPONIC_SPIRE)
        if hydro_count > 0 and planet.element_reserves:
            catalyst_h2o = min(hydro_count, planet.element_reserves.get("H2O", 0))
            if catalyst_h2o > 0:
                planet.element_reserves["H2O"] -= catalyst_h2o
                matter.sink("hydroponics", "H2O", catalyst_h2o)
                base_org += catalyst_h2o * 10
            else:
                catalyst_c = min(hydro_count, planet.element_reserves.get("C", 0))
                if catalyst_c > 0:
                    planet.element_reserves["C"] -= catalyst_c
                    matter.sink("hydroponics", "C", catalyst_c)
                    base_org += catalyst_c * 10

        # Mantle Bores consume Fe or Ti from planetary reserves to boost ore yield
        bore_count = sum(1 for t in grid.tiles if t.district == DistrictType.MANTLE_BORE)
        if bore_count > 0 and planet.element_reserves:
            catalyst_fe = min(bore_count, planet.element_reserves.get("Fe", 0))
            if catalyst_fe > 0:
                planet.element_reserves["Fe"] -= catalyst_fe
                matter.sink("mantle_bores", "Fe", catalyst_fe)
                base_ore += catalyst_fe * 10
            else:
                catalyst_ti = min(bore_count, planet.element_reserves.get("Ti", 0))
                if catalyst_ti > 0:
                    planet.element_reserves["Ti"] -= catalyst_ti
                    matter.sink("mantle_bores", "Ti", catalyst_ti)
                    base_ore += catalyst_ti * 10

        # Apply final yields to silos
        matter.produce(planet, "ore_silo", "ORE", int(base_ore), "district_mining")
        from xylarium.kernel import ledger, staples
        _k = ledger.active_kernel()
        food = staples.of(_k, planet) if _k is not None else "ORGANICS"
        staples.add(planet, food, int(base_org), "district_farming")      # the spires grow what the people eat

        # Apply Shields
        if planet.shields < planet.max_shields:
            planet.shields = min(planet.max_shields, planet.shields + int(yields["shields"]))

        # Apply Periodic Element Refining
        ref_units = int(yields.get("refinery_units", 0))
        if ref_units > 0 and planet.element_deposits:
            # Find largest deposit and convert to refined reserve
            top_elem = max(planet.element_deposits.keys(), key=lambda e: planet.element_deposits[e])
            available = min(ref_units, planet.element_deposits[top_elem])
            if available > 0:
                planet.element_deposits[top_elem] -= available
                planet.element_reserves[top_elem] = planet.element_reserves.get(top_elem, 0) + available

        # 3. Autonomous Colony Governor:
        # Autonomous infrastructure construction when colony treasury exceeds 10,000 Cr and faces deficits
        if planet.owner_id is not None and planet.treasury >= 10000:
            cost_cr = SURFACE_DISTRICT_COST_CREDITS

            # Unclosed deficits check
            has_ration_deficit = (staples.held(planet, food) == 0)
            has_ore_deficit = (planet.ore_silo == 0)

            if has_ration_deficit or has_ore_deficit:
                empty_tiles = [t for t in grid.tiles if t.district == DistrictType.EMPTY]
                if empty_tiles:
                    target_district = None
                    if has_ration_deficit and planet.treasury >= cost_cr:
                        target_district = DistrictType.HYDROPONIC_SPIRE
                        ideal_tiles = [t for t in empty_tiles if t.terrain in [TerrainType.GLACIAL_LAKE, TerrainType.HYDROCARBON_BASIN]]
                        chosen_tile = ideal_tiles[0] if ideal_tiles else empty_tiles[0]
                        planet.treasury -= cost_cr
                        _pay_builders(planet, cost_cr)
                        parts = _district_matter(ledger_kernel(), planet)
                        if parts:
                            _built_of(planet)[f"{chosen_tile.x},{chosen_tile.y}"] = \
                                uses.draw(ledger_kernel(), planet, parts, "construction")
                    elif has_ore_deficit and planet.treasury >= cost_cr:
                        target_district = DistrictType.MANTLE_BORE
                        ideal_tiles = [t for t in empty_tiles if t.terrain in [TerrainType.MOUNTAINS, TerrainType.MINERAL_RIDGE]]
                        chosen_tile = ideal_tiles[0] if ideal_tiles else empty_tiles[0]
                        planet.treasury -= cost_cr
                        _pay_builders(planet, cost_cr)

                    if target_district:
                        chosen_tile.district = target_district
                        planet.surface_grid = grid.to_dict()
