"""
Economy and dynamic market pricing engine for ports and commodities.
Modeled after TradeWars 2002 BBS dynamic supply/demand curves.
"""

from typing import Dict, Tuple, Optional, Any
from xylarium.config import COMMODITY_CONFIG
from xylarium.kernel.models import Port, CommodityType, Captain, ActionResult, ActionType


class EconomyManager:
    """Manages commodity pricing, trade execution, and port stock replenishment."""

    @staticmethod
    def get_unit_prices(port: Port, commodity: str) -> Tuple[int, int]:
        """
        Calculates (buy_from_player_price, sell_to_player_price) for a given port and commodity.
        Returns (0, 0) if not traded.
        """
        cfg = COMMODITY_CONFIG.get(commodity)
        if not cfg:
            return (0, 0)

        base = cfg["base_price"]
        min_p = cfg["min_price"]
        max_p = cfg["max_price"]
        volatility = cfg["volatility"]

        max_stock = max(1, port.max_stock.get(commodity, 1000))
        current_stock = max(0, min(port.stock.get(commodity, 500), max_stock))

        # Stock ratio: 1.0 means full stock, 0.0 means depleted
        stock_ratio = current_stock / max_stock

        # Port SELLS to captain:
        # High stock -> Cheap. Low stock -> Expensive.
        # Scarcity multiplier: when stock is 10%, price is high. When 90%, price is low.
        sell_factor = 1.0 + (0.6 - stock_ratio) * volatility * 1.5
        sell_price = int(round(base * sell_factor))
        sell_price = max(min_p, min(max_p, sell_price))

        # Port BUYS from captain:
        # High port stock -> Port doesn't need more, offers low price.
        # Low port stock -> Port is desperate, offers high price.
        # Ensure buy_price is always strictly lower than sell_price to prevent zero-risk same-port flipping
        buy_factor = 1.0 + (0.5 - stock_ratio) * volatility * 1.2
        buy_price = int(round(base * buy_factor * 0.85))
        buy_price = max(min_p // 2, min(sell_price - 2, buy_price))
        buy_price = max(5, buy_price)

        return (buy_price, sell_price)

    @classmethod
    def get_port_catalog(cls, port: Port) -> Dict[str, Dict[str, Any]]:
        """Returns full trade catalog with current prices and stock for a port."""
        catalog = {}
        for comm in [CommodityType.ORE.value, CommodityType.ORGANICS.value, CommodityType.EQUIPMENT.value]:
            buy_price, sell_price = cls.get_unit_prices(port, comm)
            catalog[comm] = {
                "name": COMMODITY_CONFIG[comm]["name"],
                "stock": port.stock.get(comm, 0),
                "max_stock": port.max_stock.get(comm, 1000),
                "port_buys": port.buys.get(comm, False),
                "port_sells": port.sells.get(comm, False),
                "buy_price": buy_price if port.buys.get(comm, False) else None,
                "sell_price": sell_price if port.sells.get(comm, False) else None,
            }
        return catalog

    @classmethod
    def execute_buy(
        cls,
        captain: Captain,
        port: Port,
        commodity: str,
        amount: int
    ) -> ActionResult:
        """
        Captain buys `amount` units of `commodity` from `port`.
        """
        commodity = commodity.upper()
        if commodity not in COMMODITY_CONFIG:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Unknown commodity: '{commodity}'.",
            )

        if not port.sells.get(commodity, False):
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Port {port.name} does not sell {commodity}.",
            )

        if amount <= 0:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message="Transaction amount must be greater than zero.",
            )

        avail_stock = port.stock.get(commodity, 0)
        if amount > avail_stock:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Port only has {avail_stock} units of {commodity} in stock.",
            )

        avail_holds = captain.ship.cargo.available_space
        if amount > avail_holds:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Insufficient cargo holds! You only have {avail_holds} free holds.",
            )

        _, unit_price = cls.get_unit_prices(port, commodity)
        total_cost = unit_price * amount

        if captain.credits < total_cost:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Insufficient credits! Requires {total_cost} Cr, but you have {captain.credits} Cr.",
            )

        # Execute Transaction
        captain.credits -= total_cost
        port.stock[commodity] -= amount
        if commodity == CommodityType.ORE.value:
            captain.ship.cargo.ore += amount
        elif commodity == CommodityType.ORGANICS.value:
            captain.ship.cargo.organics += amount
        elif commodity == CommodityType.EQUIPMENT.value:
            captain.ship.cargo.equipment += amount

        new_buy, new_sell = cls.get_unit_prices(port, commodity)

        msg = (
            f"Purchased {amount} units of {commodity} for {total_cost:,} Cr "
            f"({unit_price} Cr/ea). New stock: {port.stock[commodity]}."
        )

        return ActionResult(
            success=True,
            action=ActionType.TRADE,
            message=msg,
            turns_spent=1,
            data={
                "type": "BUY",
                "commodity": commodity,
                "amount": amount,
                "unit_price": unit_price,
                "total_cost": total_cost,
                "credits_remaining": captain.credits,
                "port_stock_remaining": port.stock[commodity],
                "new_sell_price": new_sell,
            },
            logs=[msg]
        )

    @classmethod
    def execute_sell(
        cls,
        captain: Captain,
        port: Port,
        commodity: str,
        amount: int
    ) -> ActionResult:
        """
        Captain sells `amount` units of `commodity` to `port`.
        """
        commodity = commodity.upper()
        if commodity not in COMMODITY_CONFIG:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Unknown commodity: '{commodity}'.",
            )

        if not port.buys.get(commodity, False):
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Port {port.name} is not buying {commodity}.",
            )

        if amount <= 0:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message="Transaction amount must be greater than zero.",
            )

        held_units = 0
        if commodity == CommodityType.ORE.value:
            held_units = captain.ship.cargo.ore
        elif commodity == CommodityType.ORGANICS.value:
            held_units = captain.ship.cargo.organics
        elif commodity == CommodityType.EQUIPMENT.value:
            held_units = captain.ship.cargo.equipment

        if amount > held_units:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"You only have {held_units} units of {commodity} in your hold.",
            )

        unit_price, _ = cls.get_unit_prices(port, commodity)
        total_payout = unit_price * amount

        # Execute Transaction
        if commodity == CommodityType.ORE.value:
            captain.ship.cargo.ore -= amount
        elif commodity == CommodityType.ORGANICS.value:
            captain.ship.cargo.organics -= amount
        elif commodity == CommodityType.EQUIPMENT.value:
            captain.ship.cargo.equipment -= amount

        port.stock[commodity] = min(
            port.max_stock.get(commodity, 1000) * 2,
            port.stock.get(commodity, 0) + amount
        )
        captain.credits += total_payout
        captain.score += max(1, total_payout // 20)

        new_buy, new_sell = cls.get_unit_prices(port, commodity)

        msg = (
            f"Sold {amount} units of {commodity} to {port.name} for {total_payout:,} Cr "
            f"({unit_price} Cr/ea). New stock: {port.stock[commodity]}."
        )

        return ActionResult(
            success=True,
            action=ActionType.TRADE,
            message=msg,
            turns_spent=1,
            data={
                "type": "SELL",
                "commodity": commodity,
                "amount": amount,
                "unit_price": unit_price,
                "total_payout": total_payout,
                "credits_remaining": captain.credits,
                "port_stock_remaining": port.stock[commodity],
                "new_buy_price": new_buy,
            },
            logs=[msg]
        )

    @classmethod
    def tick_port(cls, port: Port) -> None:
        """
        Simulate port economic activity over a turn cycle.
        Ports consume goods they buy and manufacture goods they sell,
        slowly trending stock levels back toward equilibrium (~60%).
        """
        for comm in [CommodityType.ORE.value, CommodityType.ORGANICS.value, CommodityType.EQUIPMENT.value]:
            max_s = port.max_stock.get(comm, 1000)
            curr_s = port.stock.get(comm, 500)
            target_equilibrium = int(max_s * 0.60)

            if port.sells.get(comm, False):
                # Production of goods to sell
                if curr_s < target_equilibrium:
                    port.stock[comm] = min(max_s, curr_s + 15)
            elif port.buys.get(comm, False):
                # Consumption of raw materials bought
                if curr_s > target_equilibrium // 2:
                    port.stock[comm] = max(50, curr_s - 10)
