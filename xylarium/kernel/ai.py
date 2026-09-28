"""
Autonomous AI Rival Captains engine for Xylarium.
Heuristic decision loops for Traders, Pirates, Industrialists, and Mercenaries.
"""

import random
from typing import Dict, List, Optional, TYPE_CHECKING
from xylarium.config import AI_CAPTAINS_CONFIG, COMMODITY_CONFIG
from xylarium.kernel.models import (
    Captain,
    Sector,
    SecurityLevel,
    AIPersonality,
    Ship,
    CargoHold,
    CommodityType,
)
from xylarium.kernel.economy import EconomyManager
from xylarium.kernel.colony import ColonyManager
from xylarium.kernel.combat import CombatManager

if TYPE_CHECKING:
    from xylarium.kernel.engine import GameKernel


TRADER_TAUNTS = [
    "Just unloaded 40 crates of High-Grade Ore at {port}. The margin was sweet.",
    "Prices on Equipment in Sector {sec} are surging. Haulers, take note.",
    "Fuel cells topped off. Running the southern warp loop for maximum arbitrage.",
    "A clean ledger and full cargo holds. That's the only law out here.",
]

PIRATE_TAUNTS = [
    "All vessels traversing Sector {sec}: submit your tithe or become scrap metal!",
    "Federal patrol pigs can't reach this far out. Fresh plunder for the incinerator!",
    "Another soft merchant vaporized in the Deep Void. Keep your shields charged, whelps.",
    "I smell unescorted cargo passing through the wormhole. Power down your drives!",
]

INDUSTRIALIST_TAUNTS = [
    "Voss Heavy Industries has completed another shield matrix expansion.",
    "Planetary yields are exceeding Q3 projections. Capital always prevails.",
    "Colonial infrastructure reinforced. Anarchists attempting a breach will be vaporized.",
    "Commercial sovereignty established over new planetary sectors.",
]

MERCENARY_TAUNTS = [
    "Ironclaw on patrol in Sector {sec}. Any pirate scum looking for trouble?",
    "Tracking an outlaw drive signature near the borderlands. Weapons hot.",
    "Fighter bays loaded and shields cycling. Stay out of my firing arc.",
    "Federal bounties pay well this cycle. Outlaws, watch your rear sensors.",
]


class AIManager:
    """Instantiates and governs autonomous rival captains."""

    @classmethod
    def create_ai_captains(cls) -> Dict[str, Captain]:
        """Initialize rival AI captains from config."""
        captains: Dict[str, Captain] = {}
        for cfg in AI_CAPTAINS_CONFIG:
            cargo = CargoHold(capacity=cfg["holds"])
            # Give trader and industrialist some starting cargo
            if cfg["personality"] == "trader":
                cargo.ore = 15
            elif cfg["personality"] == "industrialist":
                cargo.organics = 20

            ship = Ship(
                ship_type=cfg["ship_class"],
                cargo=cargo,
                shields=cfg["shields"],
                max_shields=cfg["shields"],
                fighters=cfg["fighters"],
            )
            capt = Captain(
                id=cfg["id"],
                name=cfg["name"],
                is_ai=True,
                personality=AIPersonality(cfg["personality"]),
                ship=ship,
                credits=cfg["credits"],
                sector_id=cfg["start_sector"],
                turns_left=500,
                home_sector=cfg["start_sector"],
                score=1000,
            )
            captains[capt.id] = capt
        return captains

    @classmethod
    def execute_turn(cls, kernel: "GameKernel", captain: Captain) -> None:
        """
        Executes a single heuristic action cycle for an autonomous AI captain.
        """
        current_sector = kernel.sectors[captain.sector_id]

        if captain.personality == AIPersonality.PIRATE:
            cls._execute_pirate_loop(kernel, captain, current_sector)
        elif captain.personality == AIPersonality.TRADER:
            cls._execute_trader_loop(kernel, captain, current_sector)
        elif captain.personality == AIPersonality.INDUSTRIALIST:
            cls._execute_industrialist_loop(kernel, captain, current_sector)
        elif captain.personality == AIPersonality.MERCENARY:
            cls._execute_mercenary_loop(kernel, captain, current_sector)

        # Occasional Radio Transmission
        if random.random() < 0.25:
            cls._broadcast_chatter(kernel, captain, current_sector)

    @classmethod
    def _execute_pirate_loop(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> None:
        """Pirate heuristic: Hunt ships, raid planets, or warp toward Anarchy."""
        # 1. Check if another captain (like the player) is in this sector
        other_captains = [
            c_id for c_id in sector.captains
            if c_id != captain.id and c_id in kernel.captains
        ]

        if other_captains and sector.security != SecurityLevel.FEDERATION:
            target_id = random.choice(other_captains)
            target = kernel.captains[target_id]
            # Engage in combat!
            result = CombatManager.resolve_ship_battle(captain, target, sector)
            kernel.event_bus.broadcast_radio(
                sender="RADAR-ALERT",
                text=f"COMBAT: {captain.name} engaged {target.name} in Sector {sector.id}!",
                channel="COMBAT",
                sector_id=sector.id
            )
            return

        # 2. Check if an enemy/player planet is in sector
        if sector.planets and sector.security != SecurityLevel.FEDERATION:
            for planet in sector.planets:
                if planet.owner_id and planet.owner_id != captain.id:
                    CombatManager.attack_planet(captain, planet, sector)
                    kernel.event_bus.broadcast_radio(
                        sender="COLONY-ALERT",
                        text=f"ALERT: {captain.name} initiated orbital bombardment on {planet.name}!",
                        channel="ALERT",
                        sector_id=sector.id
                    )
                    return

        # 3. If actively hunting a target sector, follow shortest path towards it
        if captain.hunt_target_sector is not None:
            if captain.sector_id == captain.hunt_target_sector:
                captain.hunt_target_sector = None
            else:
                path = kernel.find_path(captain.sector_id, captain.hunt_target_sector)
                if path and len(path) > 1:
                    cls._warp_captain(kernel, captain, path[1])
                    return

        # 4. Otherwise move: favor moving deeper into Anarchy / Borderlands
        if sector.warps:
            # Sort warps to prefer higher sector numbers (Anarchy)
            candidates = sorted(sector.warps, key=lambda s: kernel.sectors[s].security.value != SecurityLevel.ANARCHY.value)
            dest = random.choice(candidates[:2]) if len(candidates) >= 2 else candidates[0]
            cls._warp_captain(kernel, captain, dest)

    @classmethod
    def _execute_trader_loop(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> None:
        """Trader heuristic: Buy low, sell high, navigate along trade loops."""
        port = sector.port
        if port:
            # Check if we have goods to sell
            for comm in ["ORE", "ORGANICS", "EQUIPMENT"]:
                amount_held = getattr(captain.ship.cargo, comm.lower())
                if amount_held > 0 and port.buys.get(comm, False):
                    EconomyManager.execute_sell(captain, port, comm, amount_held)
                    return

            # Check if we can buy goods
            if captain.ship.cargo.available_space > 0:
                for comm in ["ORE", "ORGANICS", "EQUIPMENT"]:
                    if port.sells.get(comm, False) and port.stock.get(comm, 0) > 20:
                        _, sell_p = EconomyManager.get_unit_prices(port, comm)
                        if sell_p <= COMMODITY_CONFIG[comm]["base_price"] * 1.1:
                            buy_amt = min(captain.ship.cargo.available_space, captain.credits // sell_p, 25)
                            if buy_amt > 0:
                                EconomyManager.execute_buy(captain, port, comm, buy_amt)
                                return

        # Otherwise warp to neighboring sector with a port
        if sector.warps:
            port_warps = [w for w in sector.warps if kernel.sectors[w].port is not None]
            dest = random.choice(port_warps) if port_warps else random.choice(sector.warps)
            cls._warp_captain(kernel, captain, dest)

    @classmethod
    def _execute_industrialist_loop(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> None:
        """Industrialist heuristic: Colonize planets, upgrade citadels, fund defenses."""
        # 1. Check for unowned planet in current sector
        for planet in sector.planets:
            if planet.owner_id is None:
                ColonyManager.claim_planet(captain, planet)
                kernel.event_bus.broadcast_radio(
                    sender=captain.name,
                    text=f"By corporate decree, {planet.name} in Sector {sector.id} is now Voss territory.",
                    channel="CORP",
                    sector_id=sector.id
                )
                return
            elif planet.owner_id == captain.id:
                # Upgrade if possible
                if captain.credits >= 3500 and planet.citadel_level < 3:
                    ColonyManager.upgrade_citadel(captain, planet)
                else:
                    ColonyManager.build_shields(captain, planet, 20)
                return

        # 2. Otherwise warp towards sectors with planets or trade ports
        if sector.warps:
            dest = random.choice(sector.warps)
            cls._warp_captain(kernel, captain, dest)

    @classmethod
    def _execute_mercenary_loop(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> None:
        """Mercenary heuristic: Patrol borderlands, intercept hostiles."""
        # Intercept pirate if present
        for c_id in sector.captains:
            if c_id in kernel.captains and kernel.captains[c_id].personality == AIPersonality.PIRATE:
                CombatManager.resolve_ship_battle(captain, kernel.captains[c_id], sector)
                return

        # Warp along borderland sectors
        if sector.warps:
            dest = random.choice(sector.warps)
            cls._warp_captain(kernel, captain, dest)

    @classmethod
    def _warp_captain(cls, kernel: "GameKernel", captain: Captain, destination: int) -> None:
        """Moves captain from current sector to destination."""
        old_sec = kernel.sectors[captain.sector_id]
        if captain.id in old_sec.captains:
            old_sec.captains.remove(captain.id)

        captain.sector_id = destination
        new_sec = kernel.sectors[destination]
        if captain.id not in new_sec.captains:
            new_sec.captains.append(captain.id)

    @classmethod
    def _broadcast_chatter(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> None:
        """Sends a radio broadcast from this captain to the subspace radio log."""
        port_name = sector.port.name if sector.port else "the Deep Space Depot"
        taunt = ""
        if captain.personality == AIPersonality.TRADER:
            taunt = random.choice(TRADER_TAUNTS).format(port=port_name, sec=sector.id)
        elif captain.personality == AIPersonality.PIRATE:
            taunt = random.choice(PIRATE_TAUNTS).format(sec=sector.id)
        elif captain.personality == AIPersonality.INDUSTRIALIST:
            taunt = random.choice(INDUSTRIALIST_TAUNTS)
        elif captain.personality == AIPersonality.MERCENARY:
            taunt = random.choice(MERCENARY_TAUNTS).format(sec=sector.id)

        kernel.event_bus.broadcast_radio(
            sender=captain.name,
            text=taunt,
            channel="COMM-1",
            sector_id=sector.id
        )

    @classmethod
    def bind_event_listeners(cls, kernel: "GameKernel") -> None:
        """Subscribes AI decision engine to reactive kernel events."""
        kernel.event_bus.subscribe(lambda event: cls.handle_event(kernel, event))

    @classmethod
    def handle_event(cls, kernel: "GameKernel", payload: Dict[str, Any]) -> None:
        """Reactive triggers listening to player actions."""
        ev_type = payload.get("event")
        data = payload.get("data", {})

        # 1. Territorial Encroachment (Cynthia Voss reacts to close-range colonization)
        if ev_type in ["PLANET_CLAIMED", "CITADEL_UPGRADED"]:
            voss = kernel.captains.get("ai_voss")
            claimed_sec = data.get("sector_id")
            player_id = data.get("player_id")
            planet_name = data.get("planet_name")
            player_name = data.get("player_name")

            if voss and claimed_sec and player_id != voss.id:
                # Find closest Voss planet or her home sector
                voss_sec = voss.home_sector
                for s in kernel.sectors.values():
                    if any(p.owner_id == voss.id for p in s.planets):
                        voss_sec = s.id
                        break

                path = kernel.find_path(voss_sec, claimed_sec)
                dist = len(path) - 1 if path else 999
                if 1 <= dist <= 3:
                    msg = (
                        f"Attention Captain {player_name}: Colony {planet_name} in Sector {claimed_sec:03d} "
                        f"falls within Voss Heavy Industries charter space. "
                        f"Commercial penalties and orbital interdiction will follow."
                    )
                    kernel.event_bus.broadcast_radio(
                        sender=voss.name,
                        text=msg,
                        channel="CORP",
                        sector_id=claimed_sec
                    )

        # 2. Predatory Tracking (Warlord Malakor hunts rich players in Anarchy/Borderlands)
        elif ev_type in ["PLAYER_MOVED", "TRADE_EXECUTED"]:
            malakor = kernel.captains.get("ai_malakor")
            player_id = data.get("player_id")
            player_name = data.get("player_name")
            target_sec = data.get("to_sector") or data.get("sector_id")
            cargo = data.get("cargo", {})
            credits = data.get("credits", 0)

            if malakor and player_id != malakor.id and target_sec and target_sec > 10:
                eq_count = cargo.get("equipment", 0)
                used_holds = cargo.get("used", 0)
                # Threshold: carrying >=25 equipment or >=35 total cargo or >=10,000 Credits
                if eq_count >= 25 or used_holds >= 35 or credits >= 10000:
                    malakor.hunt_target_sector = target_sec
                    # Send predatory radio transmission
                    msg = (
                        f"Long-range sensors register high-value cargo in Sector {target_sec:03d}. "
                        f"Don't power down your shields, {player_name}... I am closing in."
                    )
                    kernel.event_bus.broadcast_radio(
                        sender=malakor.name,
                        text=msg,
                        channel="COMM-1",
                        sector_id=target_sec
                    )

        # 3. Bounty Recognition (Ironclaw Rake rewards pirate kills)
        elif ev_type == "SHIP_DESTROYED":
            ironclaw = kernel.captains.get("ai_ironclaw")
            attacker_id = data.get("attacker_id")
            attacker_name = data.get("attacker_name")
            defender_name = data.get("defender_name")
            def_pers = data.get("defender_personality")
            def_id = data.get("defender_id")
            sec_id = data.get("sector_id", 1)

            if ironclaw and attacker_id != ironclaw.id:
                if def_pers == "pirate" or def_id == "ai_malakor":
                    attacker = kernel.captains.get(attacker_id)
                    bounty_amount = 5000
                    if attacker:
                        attacker.credits += bounty_amount
                        attacker.score += 1000

                    msg = (
                        f"Confirmed kill on outlaw {defender_name} in Sector {sec_id:03d}! "
                        f"Fine gunnery, Captain {attacker_name}. "
                        f"Federal Bounty Office has authorized a {bounty_amount:,} Credit payout to your account."
                    )
                    kernel.event_bus.broadcast_radio(
                        sender=ironclaw.name,
                        text=msg,
                        channel="BOUNTY",
                        sector_id=sec_id
                    )
                    kernel.action_logs.append(f"[BOUNTY CLAIM] +{bounty_amount:,} Credits awarded for neutralizing {defender_name}!")

