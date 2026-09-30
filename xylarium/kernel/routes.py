"""
Trade route analysis and arbitrage optimization engine for Xylarium.
Calculates high-yield circular loops, local departures, colony supply corridors,
and galactic commodity price spreads.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from xylarium.config import COMMODITY_CONFIG, get_commodity_stack_multiplier
from xylarium.kernel.models import CommodityType, SecurityLevel
from xylarium.kernel.economy import EconomyManager

if TYPE_CHECKING:
    from xylarium.kernel.engine import GameKernel
    from xylarium.kernel.models import Captain, Port, Planet


@dataclass
class ArbitrageLeg:
    commodity: str
    buy_price: int
    sell_price: int
    unit_margin: int
    trade_units: int
    est_profit: int
    stack_multiplier: int = 1


@dataclass
class ArbitrageRoute:
    sector_a: int
    port_a_name: str
    sector_b: int
    port_b_name: str
    warp_hops: int
    path: List[int]
    leg_ab: Optional[ArbitrageLeg]
    leg_ba: Optional[ArbitrageLeg]
    round_trip_turns: int
    total_profit: int
    efficiency_cr_per_turn: float
    security_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_a": self.sector_a,
            "port_a_name": self.port_a_name,
            "sector_b": self.sector_b,
            "port_b_name": self.port_b_name,
            "warp_hops": self.warp_hops,
            "path": self.path,
            "leg_ab": self.leg_ab.__dict__ if self.leg_ab else None,
            "leg_ba": self.leg_ba.__dict__ if self.leg_ba else None,
            "round_trip_turns": self.round_trip_turns,
            "total_profit": self.total_profit,
            "efficiency_cr_per_turn": round(self.efficiency_cr_per_turn, 1),
            "security_summary": self.security_summary,
        }


@dataclass
class LocalDepartureOpportunity:
    commodity: str
    origin_sector: int
    buy_price: int
    dest_sector: int
    dest_port_name: str
    sell_price: int
    unit_margin: int
    warp_hops: int
    path: List[int]
    turns: int
    est_profit: int
    efficiency_cr_per_turn: float
    dest_security: str
    trade_units: int = 30
    stack_multiplier: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commodity": self.commodity,
            "origin_sector": self.origin_sector,
            "buy_price": self.buy_price,
            "dest_sector": self.dest_sector,
            "dest_port_name": self.dest_port_name,
            "sell_price": self.sell_price,
            "unit_margin": self.unit_margin,
            "warp_hops": self.warp_hops,
            "path": self.path,
            "turns": self.turns,
            "est_profit": self.est_profit,
            "efficiency_cr_per_turn": round(self.efficiency_cr_per_turn, 1),
            "dest_security": self.dest_security,
            "trade_units": self.trade_units,
            "stack_multiplier": self.stack_multiplier,
        }


@dataclass
class ColonySupplyRun:
    planet_id: str
    planet_name: str
    planet_sector: int
    resource_needed: str
    source_sector: int
    source_port_name: str
    buy_price: int
    available_stock: int
    warp_hops: int
    path: List[int]
    turn_cost: int
    security_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planet_id": self.planet_id,
            "planet_name": self.planet_name,
            "planet_sector": self.planet_sector,
            "resource_needed": self.resource_needed,
            "source_sector": self.source_sector,
            "source_port_name": self.source_port_name,
            "buy_price": self.buy_price,
            "available_stock": self.available_stock,
            "warp_hops": self.warp_hops,
            "path": self.path,
            "turn_cost": self.turn_cost,
            "security_summary": self.security_summary,
        }


@dataclass
class CommodityMarketSummary:
    commodity: str
    lowest_sell_price: int
    lowest_sell_sector: int
    lowest_sell_port: str
    highest_buy_price: int
    highest_buy_sector: int
    highest_buy_port: str
    gross_spread: int
    warp_hops: int
    path: List[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commodity": self.commodity,
            "lowest_sell_price": self.lowest_sell_price,
            "lowest_sell_sector": self.lowest_sell_sector,
            "lowest_sell_port": self.lowest_sell_port,
            "highest_buy_price": self.highest_buy_price,
            "highest_buy_sector": self.highest_buy_sector,
            "highest_buy_port": self.highest_buy_port,
            "gross_spread": self.gross_spread,
            "warp_hops": self.warp_hops,
            "path": self.path,
        }


class TradeRouteOptimizer:
    """Analytical algorithms for identifying and ranking commercial arbitrage circuits."""

    @classmethod
    def _corridor_security(cls, kernel: "GameKernel", path: List[int]) -> str:
        """Determines highest danger classification along a warp corridor."""
        has_anarchy = False
        has_border = False
        for s_id in path:
            sec = kernel.sectors[s_id].security
            if sec == SecurityLevel.ANARCHY:
                has_anarchy = True
            elif sec == SecurityLevel.BORDERLAND:
                has_border = True

        if has_anarchy:
            return "ANARCHY"
        elif has_border:
            return "BORDERLAND"
        return "FEDERATION"

    @classmethod
    def _get_candidate_commodities(
        cls,
        category: Optional[str] = None,
        commodity: Optional[str] = None,
    ) -> List[str]:
        """Resolves target commodities based on category filter or specific commodity/element."""
        if commodity:
            comm_target = commodity.strip()
            for k in COMMODITY_CONFIG.keys():
                if k.upper() == comm_target.upper():
                    return [k]
            return [comm_target]

        if not category or category.upper() in ("ALL", "NONE"):
            return list(COMMODITY_CONFIG.keys())

        cat_upper = category.upper()
        candidates: List[str] = []
        for comm, cfg in COMMODITY_CONFIG.items():
            cfg_cat = cfg.get("category", "").upper()
            if cfg_cat == cat_upper:
                candidates.append(comm)
            elif cat_upper in ("VOLATILES", "GASES", "VOLATILE") and (cfg_cat == "VOLATILES" or comm in ("ORGANICS", "H", "He-3", "C", "H2O", "Xe")):
                if comm not in candidates:
                    candidates.append(comm)
            elif cat_upper in ("METALS", "ORES", "METAL", "ORE") and (cfg_cat == "METALS" or comm in ("ORE", "Fe", "Ti", "Si", "Ni", "Cu", "AdL")):
                if comm not in candidates:
                    candidates.append(comm)
            elif cat_upper in ("EXOTICS", "FISSIONABLES", "EXOTIC") and cfg_cat == "EXOTICS":
                if comm not in candidates:
                    candidates.append(comm)
            elif cat_upper in ("MANUFACTURED", "COMPONENTS", "TECH") and (cfg_cat == "MANUFACTURED" or comm == "EQUIPMENT"):
                if comm not in candidates:
                    candidates.append(comm)

        return candidates if candidates else list(COMMODITY_CONFIG.keys())

    @classmethod
    def find_circular_arbitrage(
        cls,
        kernel: "GameKernel",
        cargo_capacity: int = 30,
        max_hops: int = 4,
        min_efficiency: float = 10.0,
        limit: int = 15,
        category: Optional[str] = None,
        commodity: Optional[str] = None,
    ) -> List[ArbitrageRoute]:
        """
        Scans all port pairs within max_hops to discover complementary trade loops.
        Ranks by efficiency (Net Credits generated per Turn spent).
        Supports full-spectrum 24+ elements and manufactured components with bulk density multipliers.
        """
        port_sectors = [s_id for s_id, s in kernel.sectors.items() if s.port is not None]
        commodities = cls._get_candidate_commodities(category=category, commodity=commodity)
        routes: List[ArbitrageRoute] = []

        for i in range(len(port_sectors)):
            s_a_id = port_sectors[i]
            port_a = kernel.sectors[s_a_id].port
            if not port_a:
                continue
            EconomyManager.ensure_port_inventory(port_a)

            for j in range(i + 1, len(port_sectors)):
                s_b_id = port_sectors[j]
                port_b = kernel.sectors[s_b_id].port
                if not port_b:
                    continue
                EconomyManager.ensure_port_inventory(port_b)

                path = kernel.find_path(s_a_id, s_b_id)
                if not path:
                    continue
                hops = len(path) - 1
                if hops <= 0 or hops > max_hops:
                    continue

                # Leg A -> B (buy at A, sell at B)
                best_leg_ab: Optional[ArbitrageLeg] = None
                best_profit_ab = 0
                for comm in commodities:
                    if port_a.sells.get(comm, False) and port_b.buys.get(comm, False):
                        _, cost_a = EconomyManager.get_unit_prices(port_a, comm)
                        revenue_b, _ = EconomyManager.get_unit_prices(port_b, comm)
                        margin = revenue_b - cost_a
                        if margin > 0 and port_a.stock.get(comm, 0) > 0:
                            mult = get_commodity_stack_multiplier(comm)
                            effective_cap = cargo_capacity * mult
                            units = min(effective_cap, port_a.stock.get(comm, 0))
                            est_profit = margin * units
                            if est_profit > best_profit_ab:
                                best_profit_ab = est_profit
                                best_leg_ab = ArbitrageLeg(
                                    commodity=comm,
                                    buy_price=cost_a,
                                    sell_price=revenue_b,
                                    unit_margin=margin,
                                    trade_units=units,
                                    est_profit=est_profit,
                                    stack_multiplier=mult,
                                )

                # Leg B -> A (buy at B, sell at A)
                best_leg_ba: Optional[ArbitrageLeg] = None
                best_profit_ba = 0
                for comm in commodities:
                    if port_b.sells.get(comm, False) and port_a.buys.get(comm, False):
                        _, cost_b = EconomyManager.get_unit_prices(port_b, comm)
                        revenue_a, _ = EconomyManager.get_unit_prices(port_a, comm)
                        margin = revenue_a - cost_b
                        if margin > 0 and port_b.stock.get(comm, 0) > 0:
                            mult = get_commodity_stack_multiplier(comm)
                            effective_cap = cargo_capacity * mult
                            units = min(effective_cap, port_b.stock.get(comm, 0))
                            est_profit = margin * units
                            if est_profit > best_profit_ba:
                                best_profit_ba = est_profit
                                best_leg_ba = ArbitrageLeg(
                                    commodity=comm,
                                    buy_price=cost_b,
                                    sell_price=revenue_a,
                                    unit_margin=margin,
                                    trade_units=units,
                                    est_profit=est_profit,
                                    stack_multiplier=mult,
                                )

                if not best_leg_ab and not best_leg_ba:
                    continue

                total_profit = (best_leg_ab.est_profit if best_leg_ab else 0) + (best_leg_ba.est_profit if best_leg_ba else 0)
                if total_profit <= 0:
                    continue

                # Round trip turns: 2 * hops (movement) + 1 turn for each trade leg performed
                turn_cost = (hops * 2) + (1 if best_leg_ab else 0) + (1 if best_leg_ba else 0)
                efficiency = total_profit / max(1, turn_cost)

                if efficiency < min_efficiency:
                    continue

                sec_summary = cls._corridor_security(kernel, path)

                route = ArbitrageRoute(
                    sector_a=s_a_id,
                    port_a_name=port_a.name,
                    sector_b=s_b_id,
                    port_b_name=port_b.name,
                    warp_hops=hops,
                    path=path,
                    leg_ab=best_leg_ab,
                    leg_ba=best_leg_ba,
                    round_trip_turns=turn_cost,
                    total_profit=total_profit,
                    efficiency_cr_per_turn=efficiency,
                    security_summary=sec_summary,
                )
                routes.append(route)

        routes.sort(key=lambda r: r.efficiency_cr_per_turn, reverse=True)
        return routes[:limit]

    @classmethod
    def find_local_opportunities(
        cls,
        kernel: "GameKernel",
        origin_sector_id: int,
        cargo_capacity: int = 30,
        max_hops: int = 5,
        category: Optional[str] = None,
        commodity: Optional[str] = None,
        limit: int = 15,
    ) -> List[LocalDepartureOpportunity]:
        """
        Finds immediate trade routes starting from the player's current sector.
        Factors in bulk density multipliers and category filters.
        """
        origin_sector = kernel.sectors.get(origin_sector_id)
        if not origin_sector or not origin_sector.port:
            return []

        port_origin = origin_sector.port
        EconomyManager.ensure_port_inventory(port_origin)
        commodities = cls._get_candidate_commodities(category=category, commodity=commodity)
        opportunities: List[LocalDepartureOpportunity] = []

        port_sectors = [s_id for s_id, s in kernel.sectors.items() if s.port is not None and s_id != origin_sector_id]

        for comm in commodities:
            if not port_origin.sells.get(comm, False):
                continue
            stock_here = port_origin.stock.get(comm, 0)
            if stock_here <= 0:
                continue

            _, cost_here = EconomyManager.get_unit_prices(port_origin, comm)
            mult = get_commodity_stack_multiplier(comm)
            effective_cap = cargo_capacity * mult
            units = min(effective_cap, stock_here)

            for target_id in port_sectors:
                target_port = kernel.sectors[target_id].port
                if not target_port:
                    continue
                EconomyManager.ensure_port_inventory(target_port)
                if not target_port.buys.get(comm, False):
                    continue

                path = kernel.find_path(origin_sector_id, target_id)
                if not path:
                    continue
                hops = len(path) - 1
                if hops <= 0 or hops > max_hops:
                    continue

                revenue_there, _ = EconomyManager.get_unit_prices(target_port, comm)
                margin = revenue_there - cost_here
                if margin <= 0:
                    continue

                est_profit = margin * units
                turns = hops + 1  # hops to travel + 1 turn to sell
                eff = est_profit / max(1, turns)
                sec_level = kernel.sectors[target_id].security.value

                opportunities.append(LocalDepartureOpportunity(
                    commodity=comm,
                    origin_sector=origin_sector_id,
                    buy_price=cost_here,
                    dest_sector=target_id,
                    dest_port_name=target_port.name,
                    sell_price=revenue_there,
                    unit_margin=margin,
                    warp_hops=hops,
                    path=path,
                    turns=turns,
                    est_profit=est_profit,
                    efficiency_cr_per_turn=eff,
                    dest_security=sec_level,
                    trade_units=units,
                    stack_multiplier=mult,
                ))

        opportunities.sort(key=lambda o: o.efficiency_cr_per_turn, reverse=True)
        return opportunities[:limit]

    @classmethod
    def find_element_radar(
        cls,
        kernel: "GameKernel",
        commodity: str,
        cargo_capacity: int = 30,
        max_hops: int = 8,
        limit: int = 15,
    ) -> List[ArbitrageRoute]:
        """Finds high-yield trade corridors specifically for a targeted element or commodity."""
        return cls.find_circular_arbitrage(
            kernel=kernel,
            cargo_capacity=cargo_capacity,
            max_hops=max_hops,
            min_efficiency=1.0,
            limit=limit,
            commodity=commodity,
        )

    @classmethod
    def find_colony_supply_routes(
        cls,
        kernel: "GameKernel",
        captain: "Captain",
        max_hops: int = 8
    ) -> List[ColonySupplyRun]:
        """
        Locates the closest and most cost-effective suppliers of Ore and Organics
        for every colony owned by the captain.
        """
        owned_planets: List[Planet] = []
        for sec in kernel.sectors.values():
            for p in sec.planets:
                if p.owner_id == captain.id:
                    owned_planets.append(p)

        if not owned_planets:
            return []

        runs: List[ColonySupplyRun] = []
        commodities = [CommodityType.ORE.value, CommodityType.ORGANICS.value]

        port_sectors = [s_id for s_id, s in kernel.sectors.items() if s.port is not None]

        for planet in owned_planets:
            colony_sec = planet.sector_id

            for comm in commodities:
                candidate_runs: List[ColonySupplyRun] = []
                for p_sec in port_sectors:
                    port = kernel.sectors[p_sec].port
                    if not port or not port.sells.get(comm, False):
                        continue
                    stock = port.stock.get(comm, 0)
                    if stock <= 10:
                        continue

                    path = kernel.find_path(p_sec, colony_sec)
                    if not path:
                        continue
                    hops = len(path) - 1
                    if hops > max_hops:
                        continue

                    _, buy_p = EconomyManager.get_unit_prices(port, comm)
                    sec_summary = cls._corridor_security(kernel, path)

                    candidate_runs.append(ColonySupplyRun(
                        planet_id=planet.id,
                        planet_name=planet.name,
                        planet_sector=colony_sec,
                        resource_needed=comm,
                        source_sector=p_sec,
                        source_port_name=port.name,
                        buy_price=buy_p,
                        available_stock=stock,
                        warp_hops=hops,
                        path=path,
                        turn_cost=hops + 1,
                        security_summary=sec_summary,
                    ))

                # Sort by warp hops ascending, then buy price ascending
                candidate_runs.sort(key=lambda r: (r.warp_hops, r.buy_price))
                runs.extend(candidate_runs[:3])

        return runs

    @classmethod
    def get_galactic_spreads(
        cls,
        kernel: "GameKernel",
        category: Optional[str] = None
    ) -> List[CommodityMarketSummary]:
        """
        Calculates the absolute lowest selling price and highest buying price across
        the entire galaxy for all commodities/elements, optionally filtered by category.
        """
        commodities = cls._get_candidate_commodities(category=category)
        summaries: List[CommodityMarketSummary] = []

        port_sectors = [s_id for s_id, s in kernel.sectors.items() if s.port is not None]

        for comm in commodities:
            lowest_sell_price = 999999
            lowest_sell_sec = 1
            lowest_sell_name = "None"

            highest_buy_price = 0
            highest_buy_sec = 1
            highest_buy_name = "None"

            for s_id in port_sectors:
                port = kernel.sectors[s_id].port
                if not port:
                    continue
                EconomyManager.ensure_port_inventory(port)

                # Does port sell?
                if port.sells.get(comm, False) and port.stock.get(comm, 0) > 0:
                    _, sell_p = EconomyManager.get_unit_prices(port, comm)
                    if sell_p < lowest_sell_price:
                        lowest_sell_price = sell_p
                        lowest_sell_sec = s_id
                        lowest_sell_name = port.name

                # Does port buy?
                if port.buys.get(comm, False):
                    buy_p, _ = EconomyManager.get_unit_prices(port, comm)
                    if buy_p > highest_buy_price:
                        highest_buy_price = buy_p
                        highest_buy_sec = s_id
                        highest_buy_name = port.name

            if lowest_sell_price < 999999 and highest_buy_price > 0 and highest_buy_price > lowest_sell_price:
                path = kernel.find_path(lowest_sell_sec, highest_buy_sec)
                hops = max(0, len(path) - 1)
                spread = highest_buy_price - lowest_sell_price
                summaries.append(CommodityMarketSummary(
                    commodity=comm,
                    lowest_sell_price=lowest_sell_price,
                    lowest_sell_sector=lowest_sell_sec,
                    lowest_sell_port=lowest_sell_name,
                    highest_buy_price=highest_buy_price,
                    highest_buy_sector=highest_buy_sec,
                    highest_buy_port=highest_buy_name,
                    gross_spread=spread,
                    warp_hops=hops,
                    path=path,
                ))

        summaries.sort(key=lambda s: s.gross_spread, reverse=True)
        return summaries
