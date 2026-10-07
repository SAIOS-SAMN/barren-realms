"""
Economy and dynamic market pricing engine for ports and commodities.
Modeled after TradeWars 2002 BBS dynamic supply/demand curves.
"""

from typing import Dict, Tuple, Optional, Any
import hashlib
from xylarium.config import COMMODITY_CONFIG, EMBARGO_TARIFF_BUY_MULT, EMBARGO_TARIFF_SELL_MULT, get_commodity_stack_multiplier
from xylarium.kernel import matter
from xylarium.kernel.models import Port, CommodityType, Captain, ActionResult, ActionType, PortClass
from xylarium.kernel.fx import hub as _hub


_COMM_LOOKUP = {k.upper(): k for k in COMMODITY_CONFIG.keys()}

from xylarium.kernel import fx
from xylarium.config import (
    PRICE_LEVEL,
    GRADIENT_MANUFACTURED_PER_HOP,
    GRADIENT_MANUFACTURED_MAX,
    GRADIENT_RAW_PER_HOP,
    GRADIENT_RAW_MIN,
    PORT_LIQUIDITY_BID_RANGE,
    FX_PRICE_PASS_THROUGH,
    PORT_START_TREASURY,
    STARDOCK_START_TREASURY,
)


class EconomyManager:
    """Manages commodity pricing, trade execution, and port stock replenishment."""

    @classmethod
    def ensure_port_inventory(cls, port: Port) -> None:
        """Ensures that port inventory and buy/sell configurations exist for all commodities. A port's founding
        stock of a commodity it had never carried is declared (the port's charter), so no unit is undeclared."""
        stock = getattr(port, "stock", None)
        if stock is not None and len(stock) >= len(COMMODITY_CONFIG):
            return
        before = dict(stock or {})
        cls._ensure_port_inventory(port)
        for comm, q in port.stock.items():
            added = q - before.get(comm, 0)
            if added > 0 and comm not in before:
                matter.source("port_charter", comm, added)

    @classmethod
    def _ensure_port_inventory(cls, port: Port) -> None:
        if not hasattr(port, "stock") or port.stock is None:
            port.stock = {}
        if not hasattr(port, "max_stock") or port.max_stock is None:
            port.max_stock = {}
        if not hasattr(port, "buys") or port.buys is None:
            port.buys = {}
        if not hasattr(port, "sells") or port.sells is None:
            port.sells = {}

        for comm, cfg in COMMODITY_CONFIG.items():
            if cfg.get("category") == "SYNTHETIC":
                # made only from energy (antimatter): every port trades it, none is chartered with any
                port.max_stock.setdefault(comm, 200)
                port.stock.setdefault(comm, 0)
                port.buys.setdefault(comm, True)
                port.sells.setdefault(comm, True)
            if cfg.get("category") == "LUXURY":
                # Every starport trades luxuries, and none is chartered with any: they are crafted by worlds
                port.max_stock.setdefault(comm, 600)
                port.stock.setdefault(comm, 0)
                port.buys.setdefault(comm, True)
                port.sells.setdefault(comm, True)
        if port.sector_id == 1:
            for comm in COMMODITY_CONFIG:
                if COMMODITY_CONFIG[comm].get("category") == "WASTE":
                    port.max_stock.setdefault(comm, 1000)
                    port.stock.setdefault(comm, 0)
                    port.buys.setdefault(comm, False)
                    port.sells.setdefault(comm, False)
                    continue
                if comm not in port.max_stock:
                    port.max_stock[comm] = 1000
                if comm not in port.stock:
                    port.stock[comm] = 850
                if comm not in port.buys:
                    port.buys[comm] = True
                if comm not in port.sells:
                    port.sells[comm] = True
            return

        from xylarium.kernel import ledger as _ledger, supply as _supply
        k = _ledger.active_kernel()
        physical = k is not None and port.sector_id in getattr(k, "sectors", {})
        for comm, cfg in COMMODITY_CONFIG.items():
            if comm in port.buys and comm in port.sells and comm in port.stock:
                continue

            cat = cfg.get("category", "METALS")
            if physical and cat in _supply.PHYSICAL and comm not in _supply.TRIAD:
                # the galaxy's elements decide: a port sells what its system holds and buys what it lacks
                max_s = 500 if cat == "EXOTICS" else 800
                b, sl, st0 = _supply.charter(k, port, comm, max_s)
                port.max_stock.setdefault(comm, max_s)
                port.buys.setdefault(comm, b)
                port.sells.setdefault(comm, sl)
                port.stock.setdefault(comm, st0)
                continue
            h = int(hashlib.md5(f"port_{port.sector_id}_{comm}".encode()).hexdigest(), 16)

            can_buy = False
            can_sell = False

            if cat == "METALS":
                can_buy = port.buys.get(CommodityType.ORE.value, False)
                can_sell = port.sells.get(CommodityType.ORE.value, False)
                if comm == "AdL" and (port.sector_id < 20 or (h % 100) > 40):
                    can_buy = False
                    can_sell = False
            elif cat == "VOLATILES":
                can_buy = port.buys.get(CommodityType.ORGANICS.value, False)
                can_sell = port.sells.get(CommodityType.ORGANICS.value, False)
                if comm == "Xe" and (h % 100) > 50:
                    can_buy = False
                    can_sell = False
            elif cat == "MANUFACTURED":
                can_buy = port.buys.get(CommodityType.EQUIPMENT.value, False)
                can_sell = port.sells.get(CommodityType.EQUIPMENT.value, False)
                if comm == "M4_WARP_CORE" and (port.sector_id < 25 or (h % 100) > 35):
                    can_buy = False
                    can_sell = False
                elif comm == "M3_ENGINE_MANIFOLD" and (h % 100) > 50:
                    can_buy = False
                    can_sell = False
            elif cat == "EXOTICS":
                is_traded = (h % 100) < 45
                if is_traded:
                    p_val = getattr(port.port_class, "value", str(port.port_class))
                    can_buy = ((h >> 4) % 2 == 0) or ("BBB" in p_val)
                    can_sell = ((h >> 4) % 2 == 1) or ("SSS" in p_val)

            max_s = 500 if cat in ("EXOTICS", "MANUFACTURED") else 800
            if comm not in port.max_stock:
                port.max_stock[comm] = max_s
            if comm not in port.buys:
                port.buys[comm] = can_buy
            if comm not in port.sells:
                port.sells[comm] = can_sell
            if comm not in port.stock:
                if can_sell:
                    port.stock[comm] = int(max_s * (0.40 + (h % 35) / 100.0))
                elif can_buy:
                    port.stock[comm] = int(max_s * (0.15 + (h % 25) / 100.0))
                else:
                    port.stock[comm] = 0

    @classmethod
    def get_unit_prices(cls, port: Port, commodity: str) -> Tuple[int, int]:
        """
        Calculates (buy_from_player_price, sell_to_player_price) for a given port and commodity.
        Returns (0, 0) if not traded.
        """
        cls.ensure_port_inventory(port)

        matched_comm = _COMM_LOOKUP.get(commodity.upper(), commodity)

        cfg = COMMODITY_CONFIG.get(matched_comm)
        if not cfg:
            return (0, 0)

        base = cfg["base_price"]
        min_p = cfg["min_price"]
        max_p = cfg["max_price"]
        volatility = cfg["volatility"]
        land = (getattr(port, "landed", None) or {}).get(matched_comm)
        if land:                                   # brought in: the landed cost is its price, its bounds scale with it
            scale = max(1.0, float(land[0]) / max(1e-9, base))
            base, min_p, max_p = float(land[0]), int(round(min_p * scale)), int(round(max_p * scale))

        max_stock = max(1, port.max_stock.get(matched_comm, 1000))
        current_stock = max(0, min(port.stock.get(matched_comm, 500), max_stock))

        # Stock ratio: 1.0 means full stock, 0.0 means depleted
        stock_ratio = current_stock / max_stock

        # Port SELLS to captain:
        sell_factor = 1.0 + (0.6 - stock_ratio) * volatility * 1.5
        sell_price = int(round(base * sell_factor))
        sell_price = max(min_p, min(max_p, sell_price))

        # Port BUYS from captain:
        buy_factor = 1.0 + (0.5 - stock_ratio) * volatility * 1.2
        buy_price = int(round(base * buy_factor * 0.85))
        buy_price = max(min_p // 2, min(sell_price - 2, buy_price))
        buy_price = max(5, buy_price)

        # Regional economics: quote in the port's currency, with a distance-from-Sol gradient
        factor = cls.regional_factor(port, cfg.get("category", "METALS"), landed=bool(land))
        if factor != 1.0:
            sell_price = max(1, int(round(sell_price * factor)))
            buy_price = max(1, min(sell_price - 1, int(round(buy_price * factor))))
        # Balance sheet: cash-rich ports bid up for goods, cash-poor ports bid down
        buy_price = max(1, min(sell_price - 1, int(round(buy_price * cls.liquidity_factor(port)))))
        if matched_comm.startswith("LUX_"):
            from xylarium.kernel import luxury
            prem = luxury.council_bid_multiplier(port, matched_comm)
            if prem > 1.0:
                buy_price = int(round(buy_price * prem))
                sell_price = max(sell_price, buy_price + 2)
        return (buy_price, sell_price)

    @staticmethod
    def liquidity_factor(port: Port) -> float:
        cur = getattr(port, "currency", _hub())
        base = (STARDOCK_START_TREASURY if port.sector_id == 1 else PORT_START_TREASURY) * PRICE_LEVEL.get(cur, 1.0)
        lo, hi = PORT_LIQUIDITY_BID_RANGE
        ratio = getattr(port, "treasury", base) / max(1.0, base)
        return max(lo, min(hi, lo + (hi - lo) * min(1.0, ratio / 2.0)))

    @staticmethod
    def regional_factor(port: Port, category: str, landed: bool = False) -> float:
        """Price level of the port's currency x remoteness gradient (manufactures dearer, raw goods cheaper) - a good
        priced at its landed cost carries its distance already (supply.py)."""
        cur = getattr(port, "currency", _hub())
        from xylarium.kernel import prices
        level = prices.level(cur)             # MV = PY, sticky (prices.py)
        if landed:
            return level
        hops = getattr(port, "remoteness", 0)
        if category == "MANUFACTURED":
            gradient = min(GRADIENT_MANUFACTURED_MAX, 1.0 + GRADIENT_MANUFACTURED_PER_HOP * hops)
        else:
            gradient = max(GRADIENT_RAW_MIN, 1.0 - GRADIENT_RAW_PER_HOP * hops)
        return level * gradient

    @classmethod
    def get_port_catalog(cls, port: Port, category: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Returns full trade catalog with current prices and stock for a port, optionally filtered by category."""
        cls.ensure_port_inventory(port)
        catalog = {}
        for comm, cfg in COMMODITY_CONFIG.items():
            if category and category != "ALL" and cfg.get("category") != category:
                continue
            buy_price, sell_price = cls.get_unit_prices(port, comm)
            catalog[comm] = {
                "name": cfg["name"],
                "symbol": cfg.get("symbol", comm),
                "category": cfg.get("category", "METALS"),
                "stock": port.stock.get(comm, 0),
                "max_stock": port.max_stock.get(comm, 1000),
                "port_buys": port.buys.get(comm, False),
                "port_sells": port.sells.get(comm, False),
                "buy_price": buy_price if port.buys.get(comm, False) else None,
                "sell_price": sell_price if port.sells.get(comm, False) else None,
                "currency": getattr(port, "currency", _hub()),
            }
        return catalog

    @classmethod
    def execute_buy(cls, captain: Captain, port: Port, commodity: str, amount: int) -> ActionResult:
        """
        Captain buys from the port, paying in the port's currency into the port's treasury.
        A SOL shortfall is converted through the ISSE FX desk automatically.
        """
        cur = getattr(port, "currency", _hub())
        if cur != _hub() and fx.ACTIVE_FX is not None and amount > 0:
            # Convert enough for the real counter price (reputation friction, xeno surcharges, rounding)
            _, unit = cls.get_unit_prices(port, commodity)
            unit = max(1, int(round(unit * cls.counterparty_factor(captain, port, "buy")))) + 1
            from xylarium.kernel import exchanges, ledger as _ledger
            k = _ledger.active_kernel()
            if k is not None and getattr(k, "fx_market", None) is fx.ACTIVE_FX:
                exchanges.ensure_local(k, captain, port.sector_id, cur, unit * amount)   # the place's own exchange
            else:
                fx.ACTIVE_FX.ensure_local(captain, cur, unit * amount)
        before = fx.balance(captain, cur)
        key = commodity.lower()
        cargo = captain.ship.cargo
        units_before = cargo.held(commodity)
        basis_before = cargo.cost_basis.get(key, 0.0)
        with fx.settle_in(captain, cur):
            res = cls._buy_core(captain, port, commodity, amount)
        if res.success:
            paid = before - fx.balance(captain, cur)
            port.treasury += paid
            res.message = cls._in_currency(res.message, cur)
            # Cost basis is kept in SOL so profit is comparable across regional currencies
            bought = cargo.held(commodity) - units_before
            if bought > 0:
                from xylarium.kernel import enterprise, ledger
                enterprise.drawn(ledger.active_kernel(), port, commodity, bought)
                paid_sol = fx.ACTIVE_FX.to_sol_value(cur, paid) if (fx.ACTIVE_FX and cur != _hub()) else paid
                cargo.cost_basis[key] = (units_before * basis_before + paid_sol) / (units_before + bought)
        return res

    @classmethod
    def execute_sell(cls, captain: Captain, port: Port, commodity: str, amount: int) -> ActionResult:
        """
        Captain sells to the port, which pays in its currency out of its own treasury:
        an illiquid port can only buy what it can afford.
        """
        cur = getattr(port, "currency", _hub())
        unit, _ = cls.get_unit_prices(port, commodity)
        if unit > 0 and amount > 0 and unit * amount > port.treasury:
            affordable = port.treasury // unit
            if affordable <= 0:
                return ActionResult(
                    success=False,
                    action=ActionType.TRADE,
                    message=f"Port {port.name} is illiquid: its treasury ({port.treasury:,} {cur}) cannot fund purchases today.",
                )
            amount = int(affordable)
        before = fx.balance(captain, cur)
        basis_sol = float(captain.ship.cargo.cost_basis.get(commodity.lower(), 0.0) or 0.0)
        held_before = captain.ship.cargo.held(commodity)
        with fx.settle_in(captain, cur):
            res = cls._sell_core(captain, port, commodity, amount)
        if res.success:
            got = fx.balance(captain, cur) - before
            port.treasury -= got
            sold = held_before - captain.ship.cargo.held(commodity)
            res.message = cls._in_currency(res.message, cur)
            if basis_sol > 0 and sold > 0:               # profit in the reserve currency, cost and proceeds alike
                got_sol = fx.ACTIVE_FX.to_sol_value(cur, got) if (fx.ACTIVE_FX and cur != _hub()) else got
                profit = got_sol - basis_sol * sold
                import re
                res.message = re.sub(r" \[Net Profit: [^\]]*\]",
                                     f" [Net Profit: {profit:+,.0f} SOL ({profit / sold:+,.1f} SOL/ea)]", res.message)
        return res

    @staticmethod
    def _in_currency(msg: str, cur: str) -> str:
        """A trade's message in the money it was paid in (the port's), not a generic credit."""
        import re
        return msg if cur == _hub() else re.sub(r"(\d) Cr\b", rf"\1 {cur}", msg)

    @staticmethod
    def counterparty_factor(captain: Captain, port: Port, direction: str) -> float:
        from xylarium.kernel.alignment import price_factor
        from xylarium.config import IMPERIAL_XENO_SURCHARGE, IMPERIAL_CLADES
        factor = price_factor(captain, direction)
        if getattr(port, "faction_id", None) == "IMPERIUM" and getattr(captain, "clade", "BIOTIC") not in IMPERIAL_CLADES:
            factor *= (1 + IMPERIAL_XENO_SURCHARGE) if direction == "buy" else (1 - IMPERIAL_XENO_SURCHARGE / 2)
        return factor

    @classmethod
    def _buy_core(
        cls,
        captain: Captain,
        port: Port,
        commodity: str,
        amount: int
    ) -> ActionResult:
        """
        Captain buys `amount` units of `commodity` from `port`.
        """
        cls.ensure_port_inventory(port)
        comm_lookup = {k.upper(): k for k in COMMODITY_CONFIG.keys()}
        matched_comm = comm_lookup.get(commodity.upper())
        if not matched_comm:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Unknown commodity: '{commodity}'.",
            )
        commodity = matched_comm

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

        if not captain.ship.cargo.can_fit(commodity, amount):
            max_units = captain.ship.cargo.available_units_for(commodity)
            mult = get_commodity_stack_multiplier(commodity)
            avail_holds = captain.ship.cargo.available_space
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Insufficient cargo holds! You can only fit {max_units} units of {commodity} ({avail_holds} free holds @ {mult}x density).",
            )

        _, unit_price = cls.get_unit_prices(port, commodity)

        # Corporate Embargo Tariff (Voss Heavy Industries charter space: sectors 11-25)
        embargo_tariff_log = None
        if "ai_voss" in captain.embargoed_by and 11 <= port.sector_id <= 25:
            tariff_price = max(unit_price + 1, int(unit_price * EMBARGO_TARIFF_BUY_MULT))
            embargo_tariff_log = f"[EMBARGO TARIFF] Voss Heavy Industries levied a 50% tariff surcharge (+{tariff_price - unit_price} Cr/ea) due to active corporate blacklist!"
            unit_price = tariff_price

        # Reputation friction: trusted (Luminous+) captains get goodwill; Shadowed ones pay more.
        # Imperial starports gouge xenos. All of it is a transfer to the port, nothing is created.
        unit_price = max(1, int(round(unit_price * cls.counterparty_factor(captain, port, "buy"))))

        total_cost = unit_price * amount

        if captain.credits < total_cost:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Insufficient credits! Requires {total_cost:,} Cr, but you have {captain.credits:,} Cr.",
            )

        # Execute Transaction
        captain.credits -= total_cost
        port.stock[commodity] -= amount

        # Track weighted average cost basis
        comm_key = commodity.lower()
        if not hasattr(captain.ship.cargo, "cost_basis") or captain.ship.cargo.cost_basis is None:
            captain.ship.cargo.cost_basis = {"ore": 0.0, "organics": 0.0, "equipment": 0.0}

        if commodity == CommodityType.ORE.value:
            old_units = captain.ship.cargo.ore
            captain.ship.cargo.ore += amount
        elif commodity == CommodityType.ORGANICS.value:
            old_units = captain.ship.cargo.organics
            captain.ship.cargo.organics += amount
        elif commodity == CommodityType.EQUIPMENT.value:
            old_units = captain.ship.cargo.equipment
            captain.ship.cargo.equipment += amount
        else:
            old_units = captain.ship.cargo.elements.get(commodity, 0)
            captain.ship.cargo.elements[commodity] = old_units + amount

        old_basis = captain.ship.cargo.cost_basis.get(comm_key, 0.0)
        new_units = max(1, old_units + amount)
        new_basis = ((old_units * old_basis) + (amount * unit_price)) / new_units if old_units > 0 else float(unit_price)
        captain.ship.cargo.cost_basis[comm_key] = round(new_basis, 1)

        new_buy, new_sell = cls.get_unit_prices(port, commodity)

        msg = (
            f"Purchased {amount} units of {commodity} for {total_cost:,} Cr "
            f"({unit_price} Cr/ea). New stock: {port.stock[commodity]}."
        )
        logs = [msg]
        if embargo_tariff_log:
            logs.append(embargo_tariff_log)

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
            logs=logs
        )

    @classmethod
    def _sell_core(
        cls,
        captain: Captain,
        port: Port,
        commodity: str,
        amount: int
    ) -> ActionResult:
        """
        Captain sells `amount` units of `commodity` to `port`.
        """
        cls.ensure_port_inventory(port)
        comm_lookup = {k.upper(): k for k in COMMODITY_CONFIG.keys()}
        matched_comm = comm_lookup.get(commodity.upper())
        if not matched_comm:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"Unknown commodity: '{commodity}'.",
            )
        commodity = matched_comm

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
        else:
            held_units = captain.ship.cargo.elements.get(commodity, 0)

        if amount > held_units:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"You only have {held_units} units of {commodity} in your hold.",
            )
        bonded = captain.ship.cargo.bonded_units(commodity)
        if amount > held_units - bonded:
            return ActionResult(
                success=False,
                action=ActionType.TRADE,
                message=f"{bonded} units of {commodity} are bonded freight under contract and cannot be sold.",
            )

        unit_price, _ = cls.get_unit_prices(port, commodity)

        # Corporate Embargo Penalty (Voss Heavy Industries charter space: sectors 11-25)
        embargo_penalty_log = None
        if "ai_voss" in captain.embargoed_by and 11 <= port.sector_id <= 25:
            penalty_price = max(1, int(unit_price * EMBARGO_TARIFF_SELL_MULT))
            embargo_penalty_log = f"[EMBARGO PENALTY] Voss Heavy Industries deducted 30% from payout (-{unit_price - penalty_price} Cr/ea) due to security blacklist!"
            unit_price = penalty_price
        unit_price = max(1, int(unit_price * cls.counterparty_factor(captain, port, "sell")))

        total_payout = unit_price * amount

        # Execute Transaction
        comm_key = commodity.lower()
        if not hasattr(captain.ship.cargo, "cost_basis") or captain.ship.cargo.cost_basis is None:
            captain.ship.cargo.cost_basis = {"ore": 0.0, "organics": 0.0, "equipment": 0.0}
        cost_ea = captain.ship.cargo.cost_basis.get(comm_key, 0.0)
        profit_per_unit = unit_price - int(cost_ea) if cost_ea > 0 else 0

        if commodity == CommodityType.ORE.value:
            captain.ship.cargo.ore -= amount
            if captain.ship.cargo.ore <= 0:
                captain.ship.cargo.cost_basis["ore"] = 0.0
        elif commodity == CommodityType.ORGANICS.value:
            captain.ship.cargo.organics -= amount
            if captain.ship.cargo.organics <= 0:
                captain.ship.cargo.cost_basis["organics"] = 0.0
        elif commodity == CommodityType.EQUIPMENT.value:
            captain.ship.cargo.equipment -= amount
            if captain.ship.cargo.equipment <= 0:
                captain.ship.cargo.cost_basis["equipment"] = 0.0
        else:
            captain.ship.cargo.elements[commodity] = captain.ship.cargo.elements.get(commodity, 0) - amount
            if captain.ship.cargo.elements[commodity] <= 0:
                del captain.ship.cargo.elements[commodity]
                captain.ship.cargo.cost_basis[comm_key] = 0.0

        # (No cap that deletes goods: a glutted warehouse already pays next to nothing for more)
        port.stock[commodity] = port.stock.get(commodity, 0) + amount
        captain.credits += total_payout
        captain.score += max(1, total_payout // 20)

        new_buy, new_sell = cls.get_unit_prices(port, commodity)

        profit_str = ""
        net_profit = (profit_per_unit * amount) if cost_ea > 0 else 0
        if cost_ea > 0:
            diff_sign = "+" if net_profit >= 0 else ""
            unit_sign = "+" if profit_per_unit >= 0 else ""
            profit_str = f" [Net Profit: {diff_sign}{net_profit:,} Cr ({unit_sign}{profit_per_unit}/ea)]"

        msg = (
            f"Sold {amount} units of {commodity} to {port.name} for {total_payout:,} Cr "
            f"({unit_price} Cr/ea).{profit_str} New stock: {port.stock[commodity]}."
        )
        logs = [msg]
        if embargo_penalty_log:
            logs.append(embargo_penalty_log)

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
                "cost_basis": cost_ea,
                "profit_per_unit": profit_per_unit,
                "net_profit": net_profit,
                "total_payout": total_payout,
                "credits_remaining": captain.credits,
                "port_stock_remaining": port.stock[commodity],
                "new_buy_price": new_buy,
            },
            logs=logs
        )

    @classmethod
    def tick_port(cls, port: Port) -> None:
        """
        One cycle of a starport's industry - nothing from nothing:
          * Manufactured goods it sells are fabricated only from inputs its warehouse holds (the commodity's
            recipe); the inputs' mass beyond one unit of product is left as slag.
          * Raw goods it sells arrive from the region's worlds and from captains - never conjured. When its
            stock of anything it sells or needs as an input runs low, it buys to restock (anti-deadlock).
          * Goods it buys are sold on to the region's households and industry (paid for each fiscal quarter).
          * Slag is recycled: two units yield one of ore; the tailings are landfilled (see landfill()).
        """
        cls.ensure_port_inventory(port)
        if not port.base_buys:
            port.base_buys = dict(port.buys)
        needs = cls._needs(port)
        for comm, cfg in COMMODITY_CONFIG.items():
            if cfg.get("category") == "WASTE":
                continue
            max_s = port.max_stock.get(comm, 800)
            curr_s = port.stock.get(comm, 0)
            target = int(max_s * 0.60)
            recipe = cfg.get("recipe")
            if port.sells.get(comm, False):
                if recipe and curr_s < target:
                    cls._fabricate(port, comm, recipe, min(15, target - curr_s))
                # restock: a distributor low on what it sells buys it back in (raw goods only arrive this way)
                restock = (not recipe) and port.stock.get(comm, 0) < target // 2
                port.buys[comm] = bool(port.base_buys.get(comm)) or restock or comm in needs and curr_s < target
            elif port.base_buys.get(comm, False) or comm in needs:
                if comm in needs:
                    port.buys[comm] = curr_s < target or bool(port.base_buys.get(comm))
                if not port.base_buys.get(comm):
                    continue                     # an input it holds for its own works, not for the region
                # Goods bought from captains are sold on to the region's households and industry
                # (the region pays for them each fiscal quarter - see MarketManager._port_retail)
                if curr_s > target // 2:
                    new_s = max(10, curr_s - 10)
                    port.consumed[comm] = port.consumed.get(comm, 0) + (curr_s - new_s)
                    from xylarium.kernel import enterprise, ledger
                    enterprise.drawn(ledger.active_kernel(), port, comm, curr_s - new_s)
                    port.stock[comm] = new_s
                    matter.sink("regional_industry", comm, curr_s - new_s)
        from xylarium.kernel import luxury
        for comm in luxury.LUXURY_TYPES:
            room = luxury.port_room(port, comm)
            port.buys[comm] = (room > 0)
            port.sells[comm] = (port.stock.get(comm, 0) > 0)
        cls._recycle_slag(port)

    @staticmethod
    def _needs(port: Port) -> set:
        """The inputs of everything a port manufactures (cached: what a port sells changes only by charter)."""
        key = tuple(sorted(c for c, v in port.sells.items() if v))
        cache = getattr(port, "_needs_cache", None)
        if cache is not None and cache[0] == key:
            return cache[1]
        needs = set()
        for comm in key:
            needs.update(COMMODITY_CONFIG.get(comm, {}).get("recipe", {}) or {})
        try:
            port._needs_cache = (key, needs)
        except AttributeError:
            pass
        return needs

    @staticmethod
    def _fabricate(port: Port, product: str, recipe: Dict[str, int], want: int) -> int:
        can = min([want] + [port.stock.get(inp, 0) // q for inp, q in recipe.items()])
        if can <= 0:
            return 0
        mass_in = 0
        for inp, q in recipe.items():
            port.stock[inp] = port.stock.get(inp, 0) - q * can
            matter.sink("fabrication", inp, q * can)
            mass_in += q * can
        port.stock[product] = port.stock.get(product, 0) + can
        matter.source("fabrication", product, can)
        slag = mass_in - can
        if slag > 0:
            port.stock["SLAG"] = port.stock.get("SLAG", 0) + slag
            matter.source("fabrication", "SLAG", slag)
        return can

    @staticmethod
    def _recycle_slag(port: Port) -> None:
        slag = port.stock.get("SLAG", 0)
        batches = min(slag // 2, 10)
        if batches <= 0:
            return
        port.stock["SLAG"] = slag - 2 * batches
        matter.sink("recycling", "SLAG", 2 * batches)
        port.stock["ORE"] = port.stock.get("ORE", 0) + batches           # half recovered as ore
        matter.source("recycling", "ORE", batches)
        port.stock["TAILINGS"] = port.stock.get("TAILINGS", 0) + batches  # half left over, awaiting landfill
        matter.source("recycling", "TAILINGS", batches)

