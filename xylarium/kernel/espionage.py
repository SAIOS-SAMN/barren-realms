"""
Espionage and Covert Operations engine for Xylarium.
Modeled after Barren Realms Elite (BRE) and Solar Realms Elite (SRE) intelligence agencies.
Handles:
- Operative recruitment and stationing
- Counter-intelligence grids
- Deep reconnaissance and classified telemetry
- Covert planetary vault siphoning
- Shield matrix sabotage
- Biosphere contamination & morale destabilization
"""

import random
from typing import Dict, Any, Optional, TYPE_CHECKING
from xylarium.config import OPERATIVE_COST_CREDITS, COVERT_OPS_CONFIG, TURN_COST_COVERT_OP
from xylarium.kernel.models import (
    Captain,
    Planet,
    Sector,
    ActionResult,
    ActionType,
)
from xylarium.kernel.fx import hub as _hub

if TYPE_CHECKING:
    from xylarium.kernel.engine import GameKernel


from xylarium.kernel.cartography import stow_fragment


class EspionageManager:
    """Manages secret intelligence agencies, covert black ops, and counter-espionage grids."""

    @classmethod
    def recruit_operatives(cls, captain: Captain, amount: int, sector: Sector) -> ActionResult:
        """
        Recruit secret field operatives.
        Available at Sector 1 Sol Central or at player-owned Citadel Tier 1+ colonies.
        """
        if amount <= 0:
            return ActionResult(
                success=False,
                action=ActionType.RECRUIT_OPERATIVES,
                message="Operative recruitment count must be greater than zero.",
            )

        # Verify location qualification
        can_recruit = False
        if sector.id == 1:
            can_recruit = True
        else:
            for p in sector.planets:
                if p.owner_id == captain.id and p.citadel_level >= 1:
                    can_recruit = True
                    break

        if not can_recruit:
            return ActionResult(
                success=False,
                action=ActionType.RECRUIT_OPERATIVES,
                message="Operative recruitment requires Sol Central Stardock (Sector 1) or an owned Citadel Tier 1+ colony.",
            )

        total_cost = amount * OPERATIVE_COST_CREDITS
        if captain.credits < total_cost:
            return ActionResult(
                success=False,
                action=ActionType.RECRUIT_OPERATIVES,
                message=f"Recruiting {amount} operatives requires {total_cost:,} Cr ({OPERATIVE_COST_CREDITS} Cr/ea). You have {captain.credits:,} Cr.",
            )

        captain.credits -= total_cost
        from xylarium.kernel import ledger
        ledger.pay_service(total_cost, sector.id if sector is not None else None)   # the agency's fixers are paid
        captain.operatives += amount
        msg = f"Contracted {amount} intelligence operatives for {total_cost:,} Cr. (Shipboard Agency: {captain.operatives} agents)"

        return ActionResult(
            success=True,
            action=ActionType.RECRUIT_OPERATIVES,
            message=msg,
            turns_spent=0,
            logs=[msg],
            data={"operatives": captain.operatives, "credits": captain.credits}
        )

    @classmethod
    def station_security(cls, captain: Captain, planet: Planet, amount: int) -> ActionResult:
        """Station shipboard operatives as planetary counter-intelligence agents."""
        if planet.owner_id != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.STATION_SECURITY,
                message=f"You do not govern {planet.name}.",
            )

        if amount <= 0:
            return ActionResult(
                success=False,
                action=ActionType.STATION_SECURITY,
                message="Operative count must be greater than zero.",
            )

        if captain.operatives < amount:
            return ActionResult(
                success=False,
                action=ActionType.STATION_SECURITY,
                message=f"Insufficient shipboard operatives! You have {captain.operatives} agents.",
            )

        captain.operatives -= amount
        planet.security_operatives += amount
        msg = f"Stationed {amount} counter-intelligence operatives on {planet.name}. (Garrison: {planet.security_operatives} agents | Ship: {captain.operatives} agents)"

        return ActionResult(
            success=True,
            action=ActionType.STATION_SECURITY,
            message=msg,
            turns_spent=0,
            logs=[msg],
            data={"planet_security": planet.security_operatives, "ship_operatives": captain.operatives}
        )

    @classmethod
    def withdraw_security(cls, captain: Captain, planet: Planet, amount: int) -> ActionResult:
        """Withdraw planetary counter-intelligence agents back to shipboard agency."""
        if planet.owner_id != captain.id:
            return ActionResult(
                success=False,
                action=ActionType.STATION_SECURITY,
                message=f"You do not govern {planet.name}.",
            )

        if amount <= 0:
            return ActionResult(
                success=False,
                action=ActionType.STATION_SECURITY,
                message="Operative count must be greater than zero.",
            )

        if planet.security_operatives < amount:
            return ActionResult(
                success=False,
                action=ActionType.STATION_SECURITY,
                message=f"Planetary garrison only has {planet.security_operatives} operatives stationed.",
            )

        planet.security_operatives -= amount
        captain.operatives += amount
        msg = f"Transferred {amount} operatives from {planet.name} back to shipboard agency. (Ship: {captain.operatives} agents)"

        return ActionResult(
            success=True,
            action=ActionType.STATION_SECURITY,
            message=msg,
            turns_spent=0,
            logs=[msg],
            data={"planet_security": planet.security_operatives, "ship_operatives": captain.operatives}
        )

    @classmethod
    def execute_operation(
        cls,
        kernel: "GameKernel",
        attacker: Captain,
        target_type: str,  # 'PLANET' or 'SHIP'
        target_id: str,
        op_type: str,      # 'recon', 'siphon', 'sabotage', 'destabilize'
        operatives_committed: int
    ) -> ActionResult:
        """
        Executes a covert black-ops infiltration against a rival planet or starship.
        """
        target_type = target_type.upper()
        op_type = op_type.lower()
        logs = []

        if op_type not in COVERT_OPS_CONFIG:
            return ActionResult(
                success=False,
                action=ActionType.COVERT_OP,
                message=f"Unknown covert operation type: '{op_type}'. Options: recon, siphon, sabotage, destabilize, cartographic_heist.",
            )

        cfg = COVERT_OPS_CONFIG[op_type]
        min_ops = cfg["min_operatives"]

        if operatives_committed < min_ops:
            return ActionResult(
                success=False,
                action=ActionType.COVERT_OP,
                message=f"Operation '{cfg['name']}' requires a minimum of {min_ops} operatives. Committed: {operatives_committed}.",
            )

        if attacker.operatives < operatives_committed:
            return ActionResult(
                success=False,
                action=ActionType.COVERT_OP,
                message=f"Insufficient operatives! You have {attacker.operatives} agents available.",
            )

        # Resolve target
        planet: Optional[Planet] = None
        target_captain: Optional[Captain] = None
        target_name = ""
        defense_score = 0
        target_sec_id = attacker.sector_id

        if target_type == "PLANET":
            # Search in current sector first, then galaxy
            current_sec = kernel.sectors[attacker.sector_id]
            for p in current_sec.planets:
                if p.id == target_id or p.name.lower() == target_id.lower():
                    planet = p
                    break
            if not planet:
                for s in kernel.sectors.values():
                    for p in s.planets:
                        if p.id == target_id or p.name.lower() == target_id.lower():
                            planet = p
                            target_sec_id = s.id
                            break
                    if planet:
                        break

            if not planet:
                return ActionResult(
                    success=False,
                    action=ActionType.COVERT_OP,
                    message=f"Target planet '{target_id}' could not be located.",
                )

            if planet.owner_id == attacker.id:
                return ActionResult(
                    success=False,
                    action=ActionType.COVERT_OP,
                    message=f"You cannot execute hostile covert operations against your own colony ({planet.name})!",
                )

            target_name = planet.name
            target_sec_id = planet.sector_id
            # Defense: security operatives + 2 per citadel level + 4 if under security lockout
            defense_score = planet.security_operatives + (planet.citadel_level * 2) + (4 if planet.security_lockout > 0 else 0)

        elif target_type == "SHIP":
            if op_type == "destabilize":
                return ActionResult(
                    success=False,
                    action=ActionType.COVERT_OP,
                    message="Destabilization ops can only target planetary biospheres and citadels.",
                )

            if target_id not in kernel.captains:
                return ActionResult(
                    success=False,
                    action=ActionType.COVERT_OP,
                    message=f"Target captain '{target_id}' not found.",
                )

            target_captain = kernel.captains[target_id]
            if target_captain.id == attacker.id:
                return ActionResult(
                    success=False,
                    action=ActionType.COVERT_OP,
                    message="You cannot run covert operations against your own vessel!",
                )

            target_name = target_captain.name
            target_sec_id = target_captain.sector_id
            defense_score = target_captain.operatives + (target_captain.ship.shields // 100)

        else:
            return ActionResult(
                success=False,
                action=ActionType.COVERT_OP,
                message=f"Invalid target type: '{target_type}'. Must be 'PLANET' or 'SHIP'.",
            )

        logs.append(f"BLACK OPS: {attacker.name} deploys {operatives_committed} agents on mission '{cfg['name']}' against {target_name}!")

        # Success Probability Calculation
        base_rate = cfg["base_success"]
        bonus = (operatives_committed - min_ops) * 0.05
        defense_penalty = defense_score * 0.05
        success_chance = min(0.92, max(0.15, base_rate + bonus - defense_penalty))

        roll = random.random()
        is_success = (roll <= success_chance)

        data: Dict[str, Any] = {
            "op_type": op_type,
            "target_type": target_type,
            "target_name": target_name,
            "operatives_committed": operatives_committed,
            "success": is_success,
        }

        if is_success:
            logs.append(f">> INFILTRATION SUCCESSFUL! Mission objectives achieved.")

            # Operation Effects
            if op_type == "recon":
                if planet:
                    intel = {
                        "name": planet.name,
                        "owner_id": planet.owner_id,
                        "sector_id": planet.sector_id,
                        "citadel_level": planet.citadel_level,
                        "population": planet.population,
                        "morale": planet.morale,
                        "shields": planet.shields,
                        "max_shields": planet.max_shields,
                        "fighters": planet.fighters,
                        "treasury": planet.treasury,
                        "ore_silo": planet.ore_silo,
                        "organics_silo": planet.organics_silo,
                        "security_operatives": planet.security_operatives,
                        "security_lockout": planet.security_lockout,
                    }
                    data["intel"] = intel
                    lock_str = " [EMERGENCY LOCKOUT]" if planet.security_lockout > 0 else ""
                    logs.append(f">> CLASSIFIED TELEMETRY: Vault: {planet.treasury:,} Cr │ Shields: {planet.shields} MW │ Pop: {planet.population:,} │ Morale: {planet.morale}% │ Security: {planet.security_operatives} agents{lock_str}.")
                elif target_captain:
                    intel = {
                        "name": target_captain.name,
                        "ship_type": target_captain.ship.ship_type,
                        "credits": target_captain.credits,
                        "debt": target_captain.debt,
                        "shields": target_captain.ship.shields,
                        "fighters": target_captain.ship.fighters,
                        "operatives": target_captain.operatives,
                        "cargo": target_captain.ship.cargo.to_dict(),
                    }
                    data["intel"] = intel
                    logs.append(f">> CLASSIFIED TELEMETRY: Credits: {target_captain.credits:,} Cr │ Shields: {target_captain.ship.shields} MW │ Fighters: {target_captain.ship.fighters} │ Secret Agents: {target_captain.operatives}.")

            elif op_type == "siphon":
                if planet:
                    # If under security lockout, siphon yields are halved
                    pct = random.uniform(0.08, 0.18) if planet.security_lockout > 0 else random.uniform(0.15, 0.35)
                    siphoned = int(planet.treasury * pct)
                    if siphoned > 0:
                        planet.treasury -= siphoned
                        from xylarium.kernel.fx import credit
                        credit(attacker, planet.currency, siphoned)
                        attacker.score += max(10, siphoned // 50)
                        if kernel is not None:
                            from xylarium.kernel import law, fx as _fx
                            harm = int(_fx.ACTIVE_FX.to_sol_value(planet.currency, siphoned)) if (_fx.ACTIVE_FX and planet.currency != _hub()) else siphoned
                            law.file(kernel, "theft", attacker, kernel.sectors.get(planet.sector_id), harm,
                                     {"kind": "planet", "id": planet.id})
                        data["siphoned_credits"] = siphoned
                        logs.append(f">> VAULT BREACH: Successfully siphoned {siphoned:,} Credits from {planet.name}'s vaults into your offshore accounts!")
                    else:
                        logs.append(f">> VAULT ACCESS: Planetary treasury vault was already empty!")
                elif target_captain:
                    pct = random.uniform(0.10, 0.25)
                    siphoned = int(target_captain.credits * pct)
                    if siphoned > 0:
                        target_captain.credits -= siphoned
                        attacker.credits += siphoned
                        attacker.score += max(10, siphoned // 50)
                        if kernel is not None:
                            from xylarium.kernel import law
                            law.file(kernel, "theft", attacker, kernel.sectors.get(attacker.sector_id), siphoned,
                                     {"kind": "captain", "id": target_captain.id})
                        data["siphoned_credits"] = siphoned
                        logs.append(f">> CIPHER SIPHON: Embezzled {siphoned:,} Credits from {target_captain.name}'s encrypted account!")
                    else:
                        logs.append(f">> CIPHER ACCESS: Target account held negligible liquid balances.")

            elif op_type == "sabotage":
                if planet:
                    pct = random.uniform(0.40, 0.75)
                    dmg = max(10, int(planet.shields * pct)) if planet.shields > 0 else 0
                    planet.shields = max(0, planet.shields - dmg)
                    data["shield_damage"] = dmg
                    logs.append(f">> GRID OVERLOAD: Detonated EMP charges in {planet.name}'s defense grid! Destroyed {dmg} MW of shielding. (Remaining: {planet.shields} MW)")
                elif target_captain:
                    pct = random.uniform(0.40, 0.75)
                    dmg = max(10, int(target_captain.ship.shields * pct)) if target_captain.ship.shields > 0 else 0
                    target_captain.ship.shields = max(0, target_captain.ship.shields - dmg)
                    data["shield_damage"] = dmg
                    logs.append(f">> GRID OVERLOAD: Sabotaged {target_captain.name}'s shield matrix! Disrupted {dmg} MW of deflectors. (Remaining: {target_captain.ship.shields} MW)")

            elif op_type == "destabilize" and planet:
                from xylarium.kernel import staples          # the people's own food is fouled
                food = staples.of(kernel, planet) if kernel is not None else "ORGANICS"
                lost_org = staples.take(planet, food, max(5, staples.held(planet, food) // 2), "sabotage")
                morale_hit = random.randint(25, 45)
                planet.morale = max(10, planet.morale - morale_hit)
                data["lost_organics"] = lost_org
                data["morale_hit"] = morale_hit
                logs.append(f">> BIOSPHERE TOXICITY: Contaminated {lost_org} units of {food} in its stores! Morale crashed by -{morale_hit}% (Current: {planet.morale}%).")

            elif op_type == "cartographic_heist":
                stolen_frags = []
                target_owner = target_captain or (kernel.captains.get(planet.owner_id) if planet and planet.owner_id else None)
                cart_mgr = getattr(kernel, "cartography_manager", None)

                # 1. Steal starmap fragments
                if target_owner and target_owner.cartography_fragments:
                    to_steal = min(2, len(target_owner.cartography_fragments))
                    for _ in range(to_steal):
                        f = target_owner.cartography_fragments.pop(0)
                        stow_fragment(attacker, f)
                        stolen_frags.append(f["name"])
                elif cart_mgr:
                    from xylarium.kernel.cartography import FRAGMENT_TEMPLATES
                    f = dict(random.choice(FRAGMENT_TEMPLATES))
                    stow_fragment(attacker, f)
                    stolen_frags.append(f["name"])

                # 2. Extract decrypted coordinates or boost active puzzle progress
                copied_secrets = []
                if target_owner and target_owner.unlocked_secrets:
                    for s in target_owner.unlocked_secrets:
                        if s not in attacker.unlocked_secrets:
                            attacker.unlocked_secrets.append(s)
                            copied_secrets.append(s)
                elif cart_mgr and attacker.active_cartography_puzzle:
                    p = cart_mgr.puzzles.get(attacker.active_cartography_puzzle)
                    if p and p.status != "DECRYPTED":
                        unrevealed = [n for row in p.grid_nodes for n in row if not n["is_revealed"]]
                        if unrevealed:
                            target_n = unrevealed[0]
                            target_n["is_revealed"] = True
                            s_val = target_n.get("sector_val", 42)
                            target_n["label"] = f"( {s_val:03d} )"
                            p.fragments_applied += 1

                bounty = random.randint(2500, 5000)
                attacker.credits += bounty
                attacker.score += 75
                data["stolen_fragments"] = stolen_frags
                data["copied_secrets"] = copied_secrets
                data["intel_bounty"] = bounty

                frag_summary = f"stole {len(stolen_frags)} chart fragments ({', '.join(stolen_frags)})" if stolen_frags else "intercepted raw telemetry"
                sec_summary = f" and exfiltrated decrypted coordinates for {', '.join(copied_secrets)}" if copied_secrets else ""
                logs.append(f">> CARTOGRAPHIC HEIST: Infiltrated {target_name}'s star-vault! Successfully {frag_summary}{sec_summary}! (+{bounty:,} Cr bounty)")

            # Weaponized Sabotage & Economic Impact on ISSE
            if op_type in ["siphon", "sabotage", "destabilize", "cartographic_heist"] and hasattr(kernel, "market_manager"):
                mgr = kernel.market_manager
                linked_comp = None
                if planet:
                    for comp in mgr.companies.values():
                        if comp.planet_id == planet.id or (comp.sector_id == planet.sector_id and comp.planet_name == planet.name):
                            linked_comp = comp
                            break
                    if not linked_comp and planet.owner_id:
                        for comp in mgr.companies.values():
                            if comp.chairman_id == planet.owner_id or comp.founder_id == planet.owner_id:
                                linked_comp = comp
                                break
                elif target_captain:
                    for comp in mgr.companies.values():
                        if comp.chairman_id == target_captain.id or comp.founder_id == target_captain.id:
                            linked_comp = comp
                            break

                if linked_comp:
                    pct_drop = random.uniform(0.15, 0.25)
                    price_drop = max(2, int(linked_comp.share_price * pct_drop))
                    linked_comp.share_price = max(5, linked_comp.share_price - price_drop)
                    linked_comp.price_history.append(linked_comp.share_price)
                    linked_comp.consumer_trust = max(10, linked_comp.consumer_trust - 15)
                    data["stock_crash"] = {
                        "ticker": linked_comp.ticker,
                        "company_name": linked_comp.name,
                        "price_drop": price_drop,
                        "pct_drop": int(pct_drop * 100),
                        "new_price": linked_comp.share_price,
                    }
                    crash_msg = (
                        f">> ISSE STOCK CRASH: Hostile black ops caused {linked_comp.name} ({linked_comp.ticker}) shares "
                        f"to plummet by -{price_drop} Cr (-{int(pct_drop * 100)}%) to {linked_comp.share_price} Cr!"
                    )
                    logs.append(crash_msg)
                    if getattr(kernel, "event_bus", None):
                        kernel.event_bus.broadcast_radio(
                            sender="ISSE-REGULATORY",
                            text=f"MARKET VOLATILITY: {linked_comp.name} ({linked_comp.ticker}) plunges -{int(pct_drop * 100)}% following sabotage attack on {target_name}!",
                            channel="ALERT",
                            sector_id=target_sec_id,
                        )

            # Leak / Trace Detection Check
            detection_chance = max(0.10, defense_score * 0.08)
            if random.random() < detection_chance:
                logs.append(f"<< TRACE DETECTED: Target security managed to identify your operative signatures!")
                if planet:
                    planet.security_lockout = 20
                kernel.event_bus.broadcast_radio(
                    sender="INTEL-ALERT",
                    text=f"SECURITY ALERT: Black ops breach on {target_name} traced back to Captain {attacker.name}!",
                    channel="ALERT",
                    sector_id=target_sec_id
                )
                data["detected"] = True

                # Emit reactive kernel event for AI empires
                target_owner = planet.owner_id if planet else (target_captain.id if target_captain else None)
                kernel.event_bus.emit_event("ESPIONAGE_BREACH_DETECTED", {
                    "attacker_id": attacker.id,
                    "attacker_name": attacker.name,
                    "attacker_sector": attacker.sector_id,
                    "target_type": target_type,
                    "target_name": target_name,
                    "target_sector": target_sec_id,
                    "target_owner_id": target_owner,
                    "op_type": op_type,
                    "siphoned_credits": data.get("siphoned_credits", 0),
                    "shield_damage": data.get("shield_damage", 0),
                    "casualties": 0,
                    "success": True,
                })
            else:
                logs.append(f">> Clean extraction: Infiltration left zero forensic footprint.")
                data["detected"] = False

            return ActionResult(
                success=True,
                action=ActionType.COVERT_OP,
                message=f"Covert Operation '{cfg['name']}' succeeded against {target_name}!",
                turns_spent=TURN_COST_COVERT_OP,
                data=data,
                logs=logs
            )

        else:
            # Operation Failed - Operatives intercepted
            casualties = max(1, random.randint(1, operatives_committed))
            attacker.operatives = max(0, attacker.operatives - casualties)
            data["casualties"] = casualties
            if planet:
                planet.security_lockout = 20

            logs.append(f"<< INFILTRATION FAILED! Counter-intelligence operatives ambushed your team!")
            logs.append(f"<< {casualties} operatives were captured or terminated during extraction.")
            logs.append(f"<< INTERROGATION LEAK: Target forces extracted your identity from captured agents!")

            kernel.event_bus.broadcast_radio(
                sender="COUNTER-INTEL",
                text=f"HOSTILE SPY RING NEUTRALIZED: Operatives working for Captain {attacker.name} captured on {target_name}!",
                channel="ALERT",
                sector_id=target_sec_id
            )

            # Emit reactive kernel event for AI empires
            target_owner = planet.owner_id if planet else (target_captain.id if target_captain else None)
            kernel.event_bus.emit_event("ESPIONAGE_BREACH_DETECTED", {
                "attacker_id": attacker.id,
                "attacker_name": attacker.name,
                "attacker_sector": attacker.sector_id,
                "target_type": target_type,
                "target_name": target_name,
                "target_sector": target_sec_id,
                "target_owner_id": target_owner,
                "op_type": op_type,
                "siphoned_credits": 0,
                "shield_damage": 0,
                "casualties": casualties,
                "success": False,
            })

            return ActionResult(
                success=False,
                action=ActionType.COVERT_OP,
                message=f"Covert Operation '{cfg['name']}' failed against {target_name}! Lost {casualties} operatives.",
                turns_spent=TURN_COST_COVERT_OP,
                data=data,
                logs=logs
            )
