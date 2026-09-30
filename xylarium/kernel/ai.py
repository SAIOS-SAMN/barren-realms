"""
Autonomous AI Rival Captains engine for Xylarium.
Heuristic decision loops for Traders, Pirates, Industrialists, and Mercenaries.
"""

import random
from typing import Dict, List, Optional, TYPE_CHECKING
from xylarium.kernel import matter
from xylarium.config import (
    AI_CAPTAINS_CONFIG,
    COMMODITY_CONFIG,
    SHIP_CATALOG,
    BANK_EMERGENCY_THRESHOLD,
    REST_COST_CREDITS,
    MAX_AI_CAPTAINS,
    CLEAVE_BASIS_THRESHOLD,
    CLEAVE_ENDOWMENT_CREDITS,
    CLEAVE_MIN_PARENT_CREDITS,
    CLEAVE_COOLDOWN_CYCLES,
    AI_CASH_RESERVE,
    AI_CRITICAL_SHIELDS,
    AI_CRITICAL_FIGHTERS,
)
from xylarium.kernel.models import (
    Captain,
    Sector,
    SecurityLevel,
    AIPersonality,
    Ship,
    CargoHold,
    CommodityType,
    ActionType,
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
            species_map = {
                "trader": ("ailuroform-primus", "biotic", "BIOTIC", 2),
                "pirate": ("hypobiotid-voidsleeper", "mineral", "ANARCHY", 3),
                "industrialist": ("bimaniform-flatlander", "mineral", "BIOTIC", 3),
                "mercenary": ("actinoform-vanguard", "plasmic", "ANARCHY", 2),
            }
            spec, metab, clade_val, rank_val = species_map.get(cfg["personality"], ("human-sol", "biotic", "BIOTIC", 1))
            cargo = CargoHold(capacity=cfg["holds"])

            # Give starting cargo aligned with species metabolism
            if metab == "biotic":
                cargo.organics = 15
                cargo.elements["H2O"] = 10
            elif metab == "mineral":
                cargo.ore = 15
                cargo.elements["Si"] = 10
            elif metab == "plasmic":
                cargo.elements["H"] = 15
                cargo.elements["He-3"] = 10

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
                species=spec,
                metabolism=metab,
                clade=clade_val,
                rank_tier=rank_val,
            )
            captains[capt.id] = capt
        return captains

    @classmethod
    def execute_turn(cls, kernel: "GameKernel", captain: Captain) -> None:
        """
        Executes an action cycle for an autonomous AI captain using the dual-seat
        Netstratum cognitive reduction organ (iae::think).
        """
        current_sector = kernel.sectors[captain.sector_id]

        # Faction warships follow their doctrine (the Ecclesiarchal Directive / the Throne's orders) first
        if captain.faction_id and getattr(kernel, "factions", None) is not None:
            if kernel.factions.execute_faction_ai(kernel, captain):
                return

        # 1. Self-maintenance & re-arming heuristic (P6)
        if cls._handle_ai_maintenance(kernel, captain, current_sector):
            return

        # 2. Corporate Governance for Industrialists (e.g. Cynthia Voss)
        if captain.personality == AIPersonality.INDUSTRIALIST:
            cls._execute_corporate_industrialist_loop(kernel, captain)

        # 3. Cognitive Economy: Pick active research breakthrough project (Mint)
        if not getattr(captain, "active_research", None):
            cls._select_ai_research(kernel, captain)

        # 3b. Financiers scan the Galactic ISSE for triangular mispricings (keeps cross rates honest)
        cls._financier_arbitrage(kernel, captain)

        # Self-preservation: a house down to its last clones stops picking fights and restocks the vats
        from xylarium.kernel import lineage
        endangered = lineage.house_endangered(kernel, captain)
        if endangered and cls._restock_clones(kernel, captain, current_sector):
            return

        # 3c. VIPs aboard are flown straight to their resort; a docked hull with berths signs on (tourism.py)
        from xylarium.kernel import tourism
        if tourism.ai_turn(kernel, captain, current_sector):
            return

        # 3d. Outside the law: pedigree, temperament and the law's presence decide (crime.py)
        from xylarium.kernel import crime
        if not endangered and crime.consider(kernel, captain, current_sector):
            return

        # 4. Anomaly Investigation vs Raid heuristic
        if not endangered and cls._handle_ai_anomaly_or_raid(kernel, captain, current_sector):
            return

        # 4a. Outlaw creed: a pirate house that drifts toward the grey middle goes raiding again
        if not endangered and cls._keep_outlaw_creed(kernel, captain, current_sector):
            return

        # 4b. Locals: the Light observe and befriend; the Dark strip what they can reach
        if cls._handle_ai_natives(kernel, captain, current_sector):
            return

        # 5. Dual-Seat Netstratum iae::think Reduction (SURVIVE + ARC)
        from xylarium.kernel.cognition import CognitiveOrgan
        cog_res = CognitiveOrgan.think(captain, kernel)
        if cog_res.success:
            if random.random() < 0.25:
                cls._broadcast_chatter(kernel, captain, current_sector)
            cls.check_cognitive_cleaving(kernel, captain)
            return

        # Fallback to personality loops if cognitive reduction is satisfied or withheld
        if captain.personality == AIPersonality.PIRATE and endangered:
            pass  # a hunted house lies low
        elif captain.personality == AIPersonality.PIRATE:
            cls._execute_pirate_loop(kernel, captain, current_sector)
        elif captain.personality == AIPersonality.TRADER:
            cls._execute_trader_loop(kernel, captain, current_sector)
        elif captain.personality == AIPersonality.INDUSTRIALIST:
            cls._execute_industrialist_loop(kernel, captain, current_sector)
        elif captain.personality == AIPersonality.MERCENARY:
            cls._execute_mercenary_loop(kernel, captain, current_sector)

        # 6. Cognitive Cleaving check (Vector 1: iae::cleave)
        cls.check_cognitive_cleaving(kernel, captain)

        # Occasional Radio Transmission
        if random.random() < 0.25:
            cls._broadcast_chatter(kernel, captain, current_sector)

    @classmethod
    def _restock_clones(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> bool:
        """Heads for the clone vats (Sol) when the house can afford a backup; the house tick buys it there."""
        from xylarium.config import LINEAGE_CLONE_PRICE
        if captain.credits < LINEAGE_CLONE_PRICE * 1.5 or sector.id == 1:
            return False
        path = kernel.find_path(sector.id, 1)
        if len(path) < 2:
            return False
        res = kernel.dispatch(captain.id, ActionType.MOVE, destination=path[1])
        return bool(res.success)

    @classmethod
    def _financier_arbitrage(cls, kernel: "GameKernel", captain: Captain) -> None:
        """
        A financier's desk: round-trip SOL through a Galactic ISSE cross pair and the two federation
        exchanges when the triangle pays after fees. The trade itself pulls the cross rate back toward
        the rates the SOL hub implies.
        """
        from xylarium.config import FINANCIER_ARBITRAGE_CHANCE, FINANCIER_ARBITRAGE_MIN_EDGE, AI_INVEST_RESERVE
        from xylarium.kernel.cognition import temperament
        if temperament(captain, kernel).get("calling") != "financier" or random.random() > FINANCIER_ARBITRAGE_CHANCE:
            return
        fxm = kernel.fx_market
        budget = captain.credits - AI_INVEST_RESERVE
        if budget < 500:
            return
        best = None
        for key, pool in fxm.cross_pools.items():
            for a, b in ((pool["ca"], pool["cb"]), (pool["cb"], pool["ca"])):
                for frac in (0.005, 0.01, 0.02, 0.05):
                    stake = int(min(budget, fxm.to_sol_value(a, pool["a"] if a == pool["ca"] else pool["b"]) * frac))
                    if stake < 100:
                        continue
                    got = fxm.quote_via_sol("SOL", a, stake)                  # SOL -> a (federation exchange)
                    got = fxm.quote_cross(a, b, got) or 0                      # a -> b (Galactic ISSE)
                    back = fxm.quote_via_sol(b, "SOL", got)                    # b -> SOL (federation exchange)
                    edge = (back - stake) / stake
                    if edge > FINANCIER_ARBITRAGE_MIN_EDGE and (best is None or back - stake > best[0]):
                        best = (back - stake, a, b, stake)
        if best is None:
            return
        _, a, b, stake = best
        captain.credits -= stake
        leg1 = fxm.swap_sol_to(a, stake)
        leg2 = fxm.swap_cross(a, b, leg1)
        leg3 = fxm.swap_to_sol(b, leg2)
        captain.credits += leg3
        stats = getattr(fxm, "arbitrage", None)
        if stats is None:
            stats = fxm.arbitrage = {"trades": 0, "profit_sol": 0}
        stats["trades"] += 1
        stats["profit_sol"] += leg3 - stake

    @classmethod
    def _keep_outlaw_creed(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> bool:
        """
        Pirate Ideology Maintenance: when an outlaw-creed captain's alignment rises above the
        creed's line, its next deed is a raid rather than safe trading. Inside protected systems it
        shakes down weaker ships for tribute (no shots fired under the port's guns); in null space it
        attacks; with no prey in reach it hunts toward the nearest null sector with traffic.
        """
        from xylarium.config import OUTLAW_CREED_LINE, OUTLAW_SHAKEDOWN_SHARE
        from xylarium.kernel import lineage, alignment
        house = lineage.house_of(kernel, captain)
        outlaw = captain.personality == AIPersonality.PIRATE or (house is not None and house.get("creed") == "outlaw")
        if not outlaw or captain.cosmic_alignment <= OUTLAW_CREED_LINE or sector.security == SecurityLevel.FEDERATION:
            return False
        kin = set((house or {}).get("members", {}))
        prey = [kernel.captains[c] for c in sector.captains
                if c != captain.id and c in kernel.captains and c not in kin]
        prey = [p for p in prey if not p.faction_id and p.ship.fighters < captain.ship.fighters * 0.8 and p.credits > 300]
        if prey:
            target = max(prey, key=lambda p: p.credits)
            if sector.is_protected_space:
                tribute = int(target.credits * OUTLAW_SHAKEDOWN_SHARE)
                target.credits -= tribute
                captain.credits += tribute
                alignment.deed(kernel, captain, "tribute_extorted")
                if getattr(kernel, "event_bus", None):
                    kernel.event_bus.broadcast_radio(sender=captain.name, channel="ALERT", sector_id=sector.id,
                                                     text=f"SHAKEDOWN: {target.name} pays {tribute:,} Cr to sail on.")
                return True
            res = kernel.dispatch(captain.id, ActionType.ATTACK_SHIP, target_id=target.id)
            return bool(res.success)
        # Hunt: the nearest null sector (within 3 warps) where a non-kin ship is sailing
        frontier, seen, parent = [sector.id], {sector.id}, {sector.id: None}
        for _ in range(3):
            nxt = []
            for sid in frontier:
                for w in kernel.sectors[sid].warps:
                    if w in seen or w not in kernel.sectors:
                        continue
                    seen.add(w)
                    parent[w] = sid
                    nxt.append(w)
                    ws = kernel.sectors[w]
                    if ws.is_null_space and any(c not in kin and c != captain.id and c in kernel.captains
                                                and not kernel.captains[c].faction_id for c in ws.captains):
                        step = w
                        while parent[step] != sector.id:
                            step = parent[step]
                        res = kernel.dispatch(captain.id, ActionType.MOVE, destination=step)
                        return bool(res.success)
            frontier = nxt
        return False

    @classmethod
    def _handle_ai_natives(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> bool:
        worlds = [p for p in sector.planets if p.natives]
        if not worlds or captain.faction_id or random.random() > 0.2:
            return False
        from xylarium.kernel.natives import NativeManager
        planet = worlds[0]
        n = planet.natives
        value = captain.cosmic_alignment
        choices = []
        if value <= -0.3:
            lawful, hand, _ = NativeManager.legality(kernel, captain, sector, n, "exploit")
            if (lawful or hand.get("enforcement") in ("NONE", "WARRANT")) and captain.ship.cargo.available_space > 20:
                choices.append("exploit")
        else:
            for sub in ("contact", "trade", "protect"):
                lawful, _, _ = NativeManager.legality(kernel, captain, sector, n, sub)
                if not lawful:
                    continue
                if sub == "contact" and captain.id not in n["contacted_by"]:
                    choices.append(sub)
                elif sub == "trade" and captain.id in n["contacted_by"]:
                    choices.append(sub)
                elif sub == "protect" and captain.id in n["contacted_by"] and not n.get("protector") and value >= 0.3:
                    choices.append(sub)
            if n.get("protector") == captain.id and n.get("tribute"):
                choices.append("collect")
            if not choices:
                choices.append("observe")
        if not choices:
            return False
        res = kernel.dispatch(captain.id, ActionType.NATIVE_INTERACT, sub_action=random.choice(choices), planet_id=planet.id)
        return bool(res.success)

    @classmethod
    def check_cognitive_cleaving(cls, kernel: "GameKernel", captain: Captain) -> Optional[Captain]:
        """
        Vector 1: Cognitive Cleaving (iae::cleave).
        When an AI captain's Seat SURVIVE maintains a closed ledger and Seat ARC
        accumulates >= 25 grown basis crystals (or unlocks all 5 tech upgrades),
        the captain reaches a cognitive tipping point, endows seed capital,
        and spawns an offshoot junior captain via manifold divergence.
        """
        if not captain.is_ai or captain.faction_id:
            return None
        if len(kernel.captains) >= MAX_AI_CAPTAINS:
            return None

        grown_count = len(getattr(captain, "grown_basis", []))
        tech_count = len(getattr(captain, "technologies", []))

        # Must meet the cognitive tipping point
        if grown_count < CLEAVE_BASIS_THRESHOLD and tech_count < 5:
            return None

        # Must have adequate surplus capital to endow the offshoot without starving
        if captain.credits < CLEAVE_MIN_PARENT_CREDITS:
            return None

        # Cooldown check
        last_cleaved = getattr(captain, "last_cleaved_cycle", -999)
        if kernel.cycle_count - last_cleaved < CLEAVE_COOLDOWN_CYCLES:
            return None

        # Deduct endowment
        captain.credits -= CLEAVE_ENDOWMENT_CREDITS
        captain.last_cleaved_cycle = kernel.cycle_count
        cleaved_count = getattr(captain, "cleaved_count", 0) + 1
        captain.cleaved_count = cleaved_count

        # Manifold Walk: Mutate personality and metabolism
        p_map = {
            AIPersonality.TRADER: [AIPersonality.INDUSTRIALIST, AIPersonality.TRADER, AIPersonality.MERCENARY],
            AIPersonality.INDUSTRIALIST: [AIPersonality.TRADER, AIPersonality.INDUSTRIALIST],
            AIPersonality.PIRATE: [AIPersonality.MERCENARY, AIPersonality.PIRATE],
            AIPersonality.MERCENARY: [AIPersonality.TRADER, AIPersonality.MERCENARY],
        }
        child_personality = random.choice(p_map.get(captain.personality, [AIPersonality.TRADER]))

        # Metabolism mutation
        parent_metab = getattr(captain, "metabolism", "biotic")
        metabs = ["biotic", "mineral", "plasmic", "umbral"]
        if random.random() < 0.70:
            child_metab = parent_metab
        else:
            other_metabs = [m for m in metabs if m != parent_metab]
            child_metab = random.choice(other_metabs)

        # Clade & species selection
        species_by_metab = {
            "biotic": ["ailuroform-primus", "cryocoherens-still", "cnidiform-accrete", "amphiform-rime"],
            "mineral": ["bimaniform-flatlander", "hypobiotid-voidsleeper", "lithophage-stonewill", "endolithid-understone"],
            "plasmic": ["actinoform-vanguard", "plasmiform-sheet"],
            "umbral": ["draconiform-umbra", "syzygiform-conjunction"],
        }
        child_species = random.choice(species_by_metab.get(child_metab, ["bimaniform-flatlander"]))

        # Thematic naming
        parent_last = captain.name.split()[-1]
        titles = {
            AIPersonality.TRADER: "Pioneer",
            AIPersonality.INDUSTRIALIST: "Prefect",
            AIPersonality.PIRATE: "Corsair",
            AIPersonality.MERCENARY: "Sentinel",
        }
        title = titles.get(child_personality, "Envoy")
        child_name = f"{title} {parent_last} {cleaved_count}"

        # Ship class
        if child_personality == AIPersonality.TRADER:
            ship_class = "Merchant Cruiser" if random.random() < 0.6 else "Scout Ship"
        elif child_personality == AIPersonality.INDUSTRIALIST:
            ship_class = "Merchant Cruiser"
        elif child_personality == AIPersonality.PIRATE:
            ship_class = "Star Frigate" if random.random() < 0.5 else "Scout Ship"
        else:  # MERCENARY
            ship_class = "Star Frigate"

        ship_cfg = SHIP_CATALOG.get(ship_class, SHIP_CATALOG["Scout Ship"])
        cargo = CargoHold(capacity=ship_cfg["holds"])

        # Metabolic starting rations
        if child_metab == "biotic":
            cargo.organics = 15
            cargo.elements["H2O"] = 10
        elif child_metab == "mineral":
            cargo.ore = 15
            cargo.elements["Si"] = 10
        elif child_metab == "plasmic":
            cargo.elements["H"] = 15
            cargo.elements["He-3"] = 10
        elif child_metab == "umbral":
            cargo.organics = 10
            cargo.ore = 10
            cargo.elements["umbrite"] = 5

        child_id = f"offshoot_{captain.id}_{kernel.cycle_count}"
        start_sec = captain.sector_id
        if start_sec not in kernel.sectors:
            start_sec = 1

        child_clade_map = {
            "biotic": "BIOTIC",
            "mineral": "LITHIC",
            "plasmic": "PLASMIC",
            "umbral": "ANARCHY",
        }
        child_clade = child_clade_map.get(child_metab, "BIOTIC")
        if child_personality == AIPersonality.PIRATE:
            child_clade = "ANARCHY"

        child_cap = Captain(
            id=child_id,
            name=child_name,
            is_ai=True,
            personality=child_personality,
            credits=CLEAVE_ENDOWMENT_CREDITS,
            sector_id=start_sec,
            species=child_species,
            metabolism=child_metab,
            clade=child_clade,
            rank_tier=1,
            turns_left=200,
            ship=Ship(
                ship_type=ship_class,
                cargo=cargo,
                shields=ship_cfg["max_shields"],
                max_shields=ship_cfg["max_shields"],
                fighters=ship_cfg["max_fighters"],
            )
        )

        # The offshoot inherits its parent's moral bearing, with a lineage's own drift
        child_cap.cosmic_alignment = round(max(-1.0, min(1.0, captain.cosmic_alignment * 0.8 + random.uniform(-0.15, 0.15))), 3)
        child_cap.alignment_record["baseline"] = child_cap.cosmic_alignment
        kernel.captains[child_id] = child_cap
        matter.commission(child_cap)
        if start_sec in kernel.sectors:
            kernel.sectors[start_sec].captains.append(child_id)
        from xylarium.kernel import chronicle, lineage
        lineage.npc_found(kernel, child_cap, "cleave", parent=captain)   # a cadet branch of the parent's house
        chronicle.genesis_manifesto(kernel, child_cap, captain, "cleave")

        # Radio & logging
        if getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(
                sender=captain.name,
                text=f"COGNITIVE CLEAVE: {captain.name} [{getattr(captain, 'species', 'biotic')}] reached cognitive tipping! Cleaved offshoot '{child_name}' [{child_species}] into Sector {start_sec:03d}.",
                channel="SYSTEM",
                sector_id=start_sec,
            )
        kernel.action_logs.append(
            f"[CLEAVE] {captain.name} endowed offshoot {child_name} ({child_species}) with {CLEAVE_ENDOWMENT_CREDITS:,} Cr."
        )
        return child_cap

    @classmethod
    def _select_ai_research(cls, kernel: "GameKernel", captain: Captain) -> None:
        """Assign active research project aligned with AI personality."""
        unlocked = set(getattr(captain, "technologies", []))
        available = [k for k in ["JUMP_DRIVE", "CLOAKING_GRID", "NANITE_DRYDOCK", "BIO_SYNTHESIZER", "ORBITAL_FOUNDRY"] if k not in unlocked]
        if not available:
            return

        preference_map = {
            AIPersonality.INDUSTRIALIST: ["ORBITAL_FOUNDRY", "BIO_SYNTHESIZER", "NANITE_DRYDOCK"],
            AIPersonality.PIRATE: ["CLOAKING_GRID", "JUMP_DRIVE", "NANITE_DRYDOCK"],
            AIPersonality.TRADER: ["JUMP_DRIVE", "BIO_SYNTHESIZER", "ORBITAL_FOUNDRY"],
            AIPersonality.MERCENARY: ["NANITE_DRYDOCK", "CLOAKING_GRID", "JUMP_DRIVE"],
        }
        prefs = preference_map.get(captain.personality, available)
        chosen = next((t for t in prefs if t in available), available[0])
        kernel.dispatch(captain.id, ActionType.RESEARCH_SELECT, tech_key=chosen)

    @classmethod
    def _handle_ai_anomaly_or_raid(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> bool:
        """
        AI 'Mint vs Raid' Dilemma:
        - When encountering cosmic anomalies or high-tech planetary outposts:
          - Mint: Investigate and decode local precursor anomalies to unlock ancient blueprints.
          - Raid: In anarchy sectors, pirates or predatory captains raid competitors researching relics.
        """
        # Check for unsolved anomalies in current sector
        sec_anoms = getattr(sector, "anomalies", [])
        if sec_anoms:
            unsolved = [
                kernel.research_manager.anomalies[aid]
                for aid in sec_anoms
                if aid in kernel.research_manager.anomalies and kernel.research_manager.anomalies[aid].status != "SOLVED"
            ]
            if unsolved:
                anom = unsolved[0]
                # Pirate Dilemma: Raid other captains present, or if alone, plunder/crack the anomaly
                if captain.personality == AIPersonality.PIRATE:
                    others = [c_id for c_id in sector.captains if c_id != captain.id and c_id in kernel.captains]
                    if others and sector.security != SecurityLevel.FEDERATION:
                        target = kernel.captains[random.choice(others)]
                        CombatManager.resolve_ship_battle(captain, target, sector, kernel=kernel)
                        kernel.event_bus.broadcast_radio(
                            sender="RADAR-ALERT",
                            text=f"AMBUSH: {captain.name} ambushed {target.name} during relic excavation in Sector {sector.id:03d}!",
                            channel="COMBAT",
                            sector_id=sector.id,
                        )
                        return True
                    elif captain.credits >= 1000:
                        kernel.dispatch(captain.id, ActionType.ANOMALY_INVESTIGATE, anomaly_id=anom.id, solve_inputs={"mode": "catalyst"})
                        return True
                else:
                    # Traders, Industrialists, Mercenaries invest into decoding the anomaly
                    if captain.credits >= 1000:
                        kernel.dispatch(captain.id, ActionType.ANOMALY_INVESTIGATE, anomaly_id=anom.id, solve_inputs={"mode": "catalyst"})
                        return True

        # Check if captain has JUMP_DRIVE and wants to explore the frontier
        cap_techs = getattr(captain, "technologies", [])
        if "JUMP_DRIVE" in cap_techs and captain.credits >= 500:
            if random.random() < 0.10:
                all_anoms = [
                    a for a in kernel.research_manager.anomalies.values()
                    if a.status != "SOLVED" and a.sector_id != captain.sector_id
                ]
                if all_anoms:
                    dest = random.choice(all_anoms).sector_id
                    kernel.dispatch(captain.id, ActionType.JUMP_WARP, destination=dest)
                    return True

        return False

    @classmethod
    def _handle_ai_maintenance(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> bool:
        """
        AI maintenance and re-arming heuristic (P6):
        - If captain is at Sector 1 Stardock:
          - If destitute (< 100 Cr) and debt == 0: apply for Federal relief loan.
          - If shields damaged: recharge shields.
          - If fighters below max bay capacity: purchase fighters.
          - If turns low (< 50) and has credits: rest at officer quarters.
          - If has ample credits (> 3000) and debt > 0: repay debt.
        - If captain is critically damaged (shields < 50 or fighters < 10) and not in Sector 1:
          - Route towards Sector 1 to repair and re-arm!
        """
        refit_here = sector.id == 1 or (sector.security == SecurityLevel.ANARCHY and sector.port is not None)
        if refit_here:
            # 1. Emergency relief loan (funded by the Federal Reserve) if destitute
            if sector.id == 1 and captain.credits < BANK_EMERGENCY_THRESHOLD:
                kernel.dispatch(captain.id, ActionType.BANK_TRANSACTION, sub_action="loan")

            # Working capital is protected so the captain can keep trading after refitting
            disposable = max(0, captain.credits - AI_CASH_RESERVE)

            # 2. Re-arm fighters up to the respawn-kit floor first, then toward bay capacity
            ship_cfg = SHIP_CATALOG.get(captain.ship.ship_type, {})
            max_fighters = ship_cfg.get("max_fighters", 20)
            if captain.ship.fighters < max_fighters and disposable >= 60:
                budget = disposable // 2 if captain.ship.shields < captain.ship.max_shields else disposable
                buy_qty = min(max_fighters - captain.ship.fighters, max(1, budget // 60))
                kernel.dispatch(captain.id, ActionType.SHIPYARD_PURCHASE, item="fighters", amount=buy_qty)
                disposable = max(0, captain.credits - AI_CASH_RESERVE)

            # 3. Partial shield recharge within budget
            if captain.ship.shields < captain.ship.max_shields and disposable >= 30:
                kernel.dispatch(captain.id, ActionType.SHIPYARD_PURCHASE, item="shields", budget=disposable)

            # 4. Repay federal debt when flush
            if sector.id == 1 and captain.debt > 0 and captain.credits >= 3000:
                kernel.dispatch(captain.id, ActionType.BANK_TRANSACTION, sub_action="repay",
                                amount=min(captain.debt, captain.credits - 2000))

            # 5. Rest if turns low
            if sector.id == 1 and captain.turns_left < 50 and captain.credits >= REST_COST_CREDITS + AI_CASH_RESERVE:
                kernel.dispatch(captain.id, ActionType.REST)

        # Retreat only when genuinely crippled (below the respawn kit), not merely under-armed
        crippled = captain.ship.shields < AI_CRITICAL_SHIELDS and captain.ship.fighters < AI_CRITICAL_FIGHTERS
        if crippled and not refit_here:
            path = kernel.find_path(captain.sector_id, 1)
            if path and len(path) > 1:
                cls._warp_captain(kernel, captain, path[1])
                return True

        return False

    @classmethod
    def _execute_pirate_loop(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> None:
        """Pirate heuristic: Hunt ships, raid planets, or warp toward Anarchy."""
        # 1. Check if another captain (like the player) is in this sector
        other_captains = [
            c_id for c_id in sector.captains
            if c_id != captain.id and c_id in kernel.captains
        ]

        # Ambush doctrine: null space is lawful hunting ground; protected systems bring warrants.
        # Sentry pickets stronger than the pirate's own wing deter the attack.
        def deterred(t_id: str) -> bool:
            return sector.sentries.get(t_id, 0) >= captain.ship.fighters

        prey = [c for c in other_captains if not deterred(c)]
        engage = bool(prey) and sector.security != SecurityLevel.FEDERATION and (
            sector.is_null_space or random.random() < 0.15
        )
        if engage:
            # Richest-looking hull first: loaded holds make the best prizes
            target_id = max(prey, key=lambda c: kernel.captains[c].ship.cargo.holds_used + random.random())
            target = kernel.captains[target_id]
            # Engage in combat!
            result = CombatManager.resolve_ship_battle(captain, target, sector, kernel=kernel)
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
                    # Weaponized Short Selling: Pirates short victim colony's enterprise before bombarding
                    for comp in kernel.market_manager.companies.values():
                        if comp.planet_id == planet.id or (comp.sector_id == sector.id and comp.planet_name == planet.name):
                            if comp.ticker not in getattr(captain, "short_positions", {}) and captain.credits >= 1500:
                                kernel.dispatch(captain.id, ActionType.STOCK_SHORT, ticker=comp.ticker, amount=40)
                                break
                    CombatManager.attack_planet(captain, planet, sector, kernel=kernel)
                    kernel.event_bus.broadcast_radio(
                        sender="COLONY-ALERT",
                        text=f"ALERT: {captain.name} initiated orbital bombardment on {planet.name}!",
                        channel="ALERT",
                        sector_id=sector.id
                    )
                    return

        # Check if pirate has active short positions to cover
        for ticker, pos in list(getattr(captain, "short_positions", {}).items()):
            comp = kernel.market_manager.companies.get(ticker)
            if comp and comp.share_price < pos.get("entry_price", comp.share_price):
                kernel.dispatch(captain.id, ActionType.STOCK_COVER, ticker=ticker)
                break

        # 3. If actively hunting a target sector, follow shortest path towards it
        if captain.hunt_target_sector is not None:
            if captain.sector_id == captain.hunt_target_sector:
                captain.hunt_target_sector = None
            else:
                path = kernel.find_path(captain.sector_id, captain.hunt_target_sector)
                if path and len(path) > 1:
                    cls._warp_captain(kernel, captain, path[1])
                    return

        # 4. Prowl null-space shipping lanes and mining belts where prey travels unprotected
        lanes = [w for w in sector.warps if kernel.sectors[w].is_null_space
                 and kernel.sectors[w].security != SecurityLevel.FEDERATION
                 and (kernel.sectors[w].captains or kernel.sectors[w].belts)]
        if lanes and random.random() < 0.7:
            cls._warp_captain(kernel, captain, max(lanes, key=lambda w: len(kernel.sectors[w].captains) + random.random()))
            return

        # 5. Otherwise move: favor moving deeper into Anarchy / Borderlands
        if sector.warps:
            # Sort warps to prefer higher sector numbers (Anarchy)
            candidates = sorted(sector.warps, key=lambda s: kernel.sectors[s].security.value != SecurityLevel.ANARCHY.value)
            dest = random.choice(candidates[:2]) if len(candidates) >= 2 else candidates[0]
            cls._warp_captain(kernel, captain, dest)

    @classmethod
    def _execute_trader_loop(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> None:
        """Trader heuristic: Buy low, sell high, fulfill freight contracts, invest in equity."""
        # 1. Deliver completed freight contracts if at destination
        active_cids = list(getattr(captain, "active_contracts", []))
        for cid in active_cids:
            contract = kernel.market_manager.contracts.get(cid)
            if contract and contract.destination_sector == sector.id:
                kernel.dispatch(captain.id, ActionType.FREIGHT_DELIVER, contract_id=cid)
                return

        # 2. Accept open freight contracts in current sector
        if len(active_cids) < 2 and captain.ship.cargo.available_space >= 10:
            for contract in kernel.market_manager.contracts.values():
                if contract.status == "OPEN" and contract.origin_sector == sector.id:
                    if captain.ship.cargo.available_space >= contract.amount:
                        kernel.dispatch(captain.id, ActionType.FREIGHT_ACCEPT, contract_id=contract.id)
                        return

        # 3. Standard port trading: Buy low, sell high
        port = sector.port
        if port:
            metab = getattr(captain, "metabolism", "biotic")
            # Check if we have goods to sell
            for comm in ["ORE", "ORGANICS", "EQUIPMENT"]:
                amount_held = getattr(captain.ship.cargo, comm.lower())
                keep_min = 0
                if (comm == "ORGANICS" and metab == "biotic") or (comm == "ORE" and metab == "mineral"):
                    keep_min = 5
                sellable = amount_held - keep_min
                if sellable > 0 and port.buys.get(comm, False):
                    EconomyManager.execute_sell(captain, port, comm, sellable)
                    return

            # Check if we can buy goods
            if captain.ship.cargo.available_space > 0:
                for comm in ["ORE", "ORGANICS", "EQUIPMENT"]:
                    if port.sells.get(comm, False) and port.stock.get(comm, 0) > 20:
                        _, sell_p = EconomyManager.get_unit_prices(port, comm)
                        if sell_p <= COMMODITY_CONFIG[comm]["base_price"] * 1.1:
                            disposable_cr = max(0, captain.credits - 300)
                            buy_amt = min(captain.ship.cargo.available_space, disposable_cr // sell_p, 25)
                            if buy_amt > 0:
                                EconomyManager.execute_buy(captain, port, comm, buy_amt)
                                return

        # 4. Long-term wealth generation: Invest surplus capital into high-dividend ISSE shares
        if captain.credits >= 6000:
            best_comp = max(
                kernel.market_manager.companies.values(),
                key=lambda c: c.dividend_rate if c.available_shares >= 25 else -1,
                default=None
            )
            if best_comp and best_comp.available_shares >= 25:
                cost = best_comp.share_price * 25
                if cost <= captain.credits // 2:
                    kernel.dispatch(captain.id, ActionType.STOCK_BUY, ticker=best_comp.ticker, amount=25)

        # 5. Route toward freight destination if carrying cargo
        if active_cids:
            contract = kernel.market_manager.contracts.get(active_cids[0])
            if contract:
                path = kernel.find_path(captain.sector_id, contract.destination_sector)
                if path and len(path) > 1:
                    cls._warp_captain(kernel, captain, path[1])
                    return

        # Otherwise warp to neighboring sector with a port
        if sector.warps:
            port_warps = [w for w in sector.warps if kernel.sectors[w].port is not None]
            dest = random.choice(port_warps) if port_warps else random.choice(sector.warps)
            cls._warp_captain(kernel, captain, dest)

    @classmethod
    def _execute_corporate_industrialist_loop(cls, kernel: "GameKernel", captain: Captain) -> None:
        """
        Autonomous corporate AI strategy for industrialist captains (e.g., Cynthia Voss):
        1. Poison Pill Defense against hostile raiders (>30% shares).
        2. Sovereign Sector Customs Tariff enforcement.
        3. Interstellar Trade Council lobbying & regulatory resolutions.
        4. Sales Executive force expansion and regional market penetration.
        5. Media PR & Corporate Warfare.
        """
        controlled = [
            c for c in kernel.market_manager.companies.values()
            if c.chairman_id == captain.id or c.founder_id == captain.id
        ]
        if not controlled:
            return

        for comp in controlled:
            # 1. Poison Pill Defense against hostile raiders
            if comp.poison_pill_uses > 0:
                for c_id, other_cap in kernel.captains.items():
                    if c_id != captain.id:
                        port = getattr(other_cap, "portfolio", {})
                        shares = port.get(comp.ticker, 0)
                        pct = (shares / comp.total_shares) * 100.0 if comp.total_shares > 0 else 0.0
                        if pct >= 30.0:
                            kernel.dispatch(captain.id, ActionType.POISON_PILL, ticker=comp.ticker)
                            break

            # 2. Sovereign Sector Tariff
            if hasattr(kernel, "sectors"):
                sec = kernel.sectors.get(comp.sector_id)
                if sec:
                    for p in sec.planets:
                        if p.owner_id == captain.id and p.sector_tariff_pct == 0 and p.citadel_level >= 1:
                            kernel.dispatch(captain.id, ActionType.SET_TARIFF, sector_id=p.sector_id, tariff_pct=20)
                            break

            # 3. Interstellar Trade Council Lobbying & Resolutions
            tc = kernel.market_manager.trade_council
            influence = tc.lobbying_funds.get(comp.ticker, 0)
            if influence >= 2500:
                has_subsidy = any(
                    r["bill_type"] == "SUBSIDY" and r["sponsor"] == comp.ticker
                    for r in tc.active_resolutions
                )
                if not has_subsidy:
                    kernel.dispatch(
                        captain.id,
                        ActionType.COUNCIL_VOTE,
                        bill_type="SUBSIDY",
                        sponsor_ticker=comp.ticker,
                    )
                else:
                    for other_ticker in kernel.market_manager.companies:
                        if other_ticker != comp.ticker:
                            has_sanction = any(
                                r["bill_type"] == "TARIFF_SANCTIONS" and r.get("target") == other_ticker
                                for r in tc.active_resolutions
                            )
                            if not has_sanction and influence >= 2500:
                                kernel.dispatch(
                                    captain.id,
                                    ActionType.COUNCIL_VOTE,
                                    bill_type="TARIFF_SANCTIONS",
                                    sponsor_ticker=comp.ticker,
                                    target_ticker=other_ticker,
                                )
                                break
            elif captain.credits >= 4000:
                kernel.dispatch(
                    captain.id,
                    ActionType.LOBBY_CONTRIBUTE,
                    amount=1500,
                    ticker=comp.ticker,
                )

            # 4. Sales Executive Recruitment & Mobility
            if len(comp.sales_executives) < 2 and captain.credits >= 3000:
                kernel.dispatch(
                    captain.id,
                    ActionType.EXECUTIVE_HIRE,
                    ticker=comp.ticker,
                    name=f"Voss Operative {random.randint(10, 99)}",
                )
            elif comp.sales_executives:
                for ex_id in comp.sales_executives:
                    ex = kernel.market_manager.executives.get(ex_id)
                    if ex and ex.active:
                        cur_pen = comp.market_penetration.get(ex.sector_id, 0.0)
                        if cur_pen >= 60.0 and ex.sector_id in kernel.sectors:
                            warps = kernel.sectors[ex.sector_id].warps
                            if warps:
                                target_sec = min(warps, key=lambda w: comp.market_penetration.get(w, 0.0))
                                if comp.market_penetration.get(target_sec, 0.0) < 50.0:
                                    kernel.dispatch(
                                        captain.id,
                                        ActionType.EXECUTIVE_MOVE,
                                        exec_id=ex.id,
                                        destination=target_sec,
                                    )
                                    break

            # 5. Media PR & Corporate Warfare
            if comp.consumer_trust < 60 and captain.credits >= 3500:
                kernel.dispatch(
                    captain.id,
                    ActionType.MARKETING_CAMPAIGN,
                    ticker=comp.ticker,
                    campaign_type="POSITIVE",
                )
            elif captain.credits >= 6000:
                for other_ticker, other_comp in kernel.market_manager.companies.items():
                    if other_ticker != comp.ticker:
                        other_pen = other_comp.market_penetration.get(comp.sector_id, 0.0)
                        if other_pen >= 20.0:
                            kernel.dispatch(
                                captain.id,
                                ActionType.MARKETING_CAMPAIGN,
                                ticker=comp.ticker,
                                campaign_type="SMEAR",
                                target_ticker=other_ticker,
                            )
                            break

    @classmethod
    def _execute_industrialist_loop(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> None:
        """Industrialist heuristic: Corporate board management, colonize planets, upgrade citadels, fund defenses, collect taxes."""
        # 0. Corporate Governance & Market Dominance loop
        cls._execute_corporate_industrialist_loop(kernel, captain)

        # 1. Check for uncollected taxes across owned colonies
        owned_planets = [
            (s.id, p)
            for s in kernel.sectors.values()
            for p in s.planets
            if p.owner_id == captain.id and p.treasury >= 500
        ]
        if owned_planets:
            # If in the same sector as an owned planet, collect taxes!
            for s_id, p in owned_planets:
                if s_id == sector.id:
                    kernel.dispatch(captain.id, ActionType.PLANET_TAX, planet_id=p.id)
                    return
            # If low on credits (< 2500), route towards richest colony
            if captain.credits < 2500:
                best_sec = max(owned_planets, key=lambda x: x[1].treasury)[0]
                path = kernel.find_path(captain.sector_id, best_sec)
                if path and len(path) > 1:
                    cls._warp_captain(kernel, captain, path[1])
                    return

        # 2. Check for unowned planet in current sector
        for planet in sector.planets:
            if planet.owner_id is None:
                ColonyManager.claim_planet(captain, planet, sector)
                kernel.event_bus.broadcast_radio(
                    sender=captain.name,
                    text=f"By corporate decree, {planet.name} in Sector {sector.id} is now Voss territory.",
                    channel="CORP",
                    sector_id=sector.id
                )
                return
            elif planet.owner_id == captain.id:
                # Fortify colony with counter-intelligence security operatives if treasury is rich
                if planet.treasury >= 5000 and planet.security_operatives < 5 and captain.credits >= 1000:
                    planet.security_operatives += 2
                    captain.credits -= 1000
                elif captain.credits >= 3500 and planet.citadel_level < 3:
                    ColonyManager.upgrade_citadel(captain, planet)
                else:
                    ColonyManager.build_shields(captain, planet, 20)
                return

        # 3. Otherwise warp towards sectors with planets or trade ports
        if sector.warps:
            dest = random.choice(sector.warps)
            cls._warp_captain(kernel, captain, dest)

    @classmethod
    def _execute_mercenary_loop(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> None:
        """Mercenary heuristic: Patrol borderlands, hunt bounties, and intercept hostiles."""
        # 1. Intercept wanted bounties or pirates in sector (outside Federation space)
        if sector.security != SecurityLevel.FEDERATION:
            for c_id in sector.captains:
                if c_id != captain.id and c_id in kernel.captains:
                    target = kernel.captains[c_id]
                    if target.bounty > 0 or target.personality == AIPersonality.PIRATE:
                        CombatManager.resolve_ship_battle(captain, target, sector, kernel=kernel)
                        kernel.event_bus.broadcast_radio(
                            sender="MERC-ENGAGE",
                            text=f"ENGAGING TARGET: {captain.name} opened fire on wanted vessel {target.name} in Sector {sector.id}!",
                            channel="COMBAT",
                            sector_id=sector.id
                        )
                        return

        # 2. If hunting a designated target sector, navigate towards it
        if captain.hunt_target_sector is not None:
            if captain.sector_id == captain.hunt_target_sector:
                captain.hunt_target_sector = None
            else:
                path = kernel.find_path(captain.sector_id, captain.hunt_target_sector)
                if path and len(path) > 1:
                    cls._warp_captain(kernel, captain, path[1])
                    return

        # 3. Otherwise warp along borderland sectors
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

            target_captain = kernel.captains.get(player_id)
            if malakor and target_captain and not target_captain.is_ai and target_sec and target_sec > 10:
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

        # 4. Counter-Intelligence & Security Wars: Espionage Breach Reactions
        elif ev_type == "ESPIONAGE_BREACH_DETECTED":
            attacker_id = data.get("attacker_id")
            attacker_name = data.get("attacker_name")
            attacker_sec = data.get("attacker_sector", 1)
            target_owner_id = data.get("target_owner_id")
            target_name = data.get("target_name")
            target_sec = data.get("target_sector", 1)
            op_type = data.get("op_type")
            siphoned = data.get("siphoned_credits", 0)

            attacker = kernel.captains.get(attacker_id)
            if not attacker:
                return

            voss = kernel.captains.get("ai_voss")
            malakor = kernel.captains.get("ai_malakor")
            ironclaw = kernel.captains.get("ai_ironclaw")

            # --- Reaction A: Cynthia Voss (Industrialist / Voss Heavy Industries) ---
            if voss and (target_owner_id == voss.id or (target_name and "Voss" in str(target_name)) or (target_name and "Oasis" in str(target_name))):
                # 1. Corporate Trade Embargo
                if voss.id not in attacker.embargoed_by:
                    attacker.embargoed_by.append(voss.id)

                embargo_msg = (
                    f"CRIMINAL EMBARGO: Captain {attacker_name} has committed corporate espionage against {target_name}! "
                    f"Voss Heavy Industries declares an immediate total trade embargo. Corporate transit tariffs apply."
                )
                kernel.event_bus.broadcast_radio(
                    sender=voss.name,
                    text=embargo_msg,
                    channel="CORP",
                    sector_id=target_sec
                )

                # 2. Place Mercenary Bounty & Hire Ironclaw Rake
                bounty_amt = max(5000, siphoned // 2)
                attacker.bounty = max(attacker.bounty, bounty_amt)
                attacker.bounty_placed_by = voss.name

                if ironclaw and attacker_id != ironclaw.id:
                    ironclaw.hunt_target_sector = attacker_sec
                    contract_msg = (
                        f"BOUNTY CONTRACT ACTIVATED: Voss Heavy Industries authorizes a {bounty_amt:,} Credit payout "
                        f"for the neutralization of Captain {attacker_name}. Hunter protocols locked on Sector {attacker_sec:03d}!"
                    )
                    kernel.event_bus.broadcast_radio(
                        sender=ironclaw.name,
                        text=contract_msg,
                        channel="BOUNTY",
                        sector_id=target_sec
                    )

            # --- Reaction B: Warlord Malakor (Pirate / Dread Hollow) ---
            elif malakor and (target_owner_id == malakor.id or (target_name and ("Malakor" in str(target_name) or "Dread" in str(target_name)))):
                malakor.hunt_target_sector = attacker_sec
                pirate_msg = (
                    f"You dare infiltrate my stronghold, {attacker_name}?! "
                    f"The Black Fleet will blast your carcass across Sector {attacker_sec:03d}! No quarter!"
                )
                kernel.event_bus.broadcast_radio(
                    sender=malakor.name,
                    text=pirate_msg,
                    channel="ALERT",
                    sector_id=target_sec
                )

            # --- Reaction C: Ironclaw Rake (Mercenary) ---
            elif ironclaw and target_owner_id == ironclaw.id:
                ironclaw.hunt_target_sector = attacker_sec
                merc_msg = (
                    f"Hostile operative breach traced to Captain {attacker_name}! "
                    f"You made a fatal mistake targeting mercenary command. Closing on Sector {attacker_sec:03d}."
                )
                kernel.event_bus.broadcast_radio(
                    sender=ironclaw.name,
                    text=merc_msg,
                    channel="ALERT",
                    sector_id=target_sec
                )

