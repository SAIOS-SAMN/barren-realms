"""
Autonomous AI Rival Captains engine for Xylarium.
A captain's turn is one weighed choice (turn.py); this module founds the rivals, keeps their houses' desks (research,
the financier's arbitrage, a firm's governance), cleaves minds and carries their chatter and reactions.
"""

import random
from typing import Any, Dict, Optional, TYPE_CHECKING
from xylarium.kernel import matter
from xylarium.kernel import motive
from xylarium.config import (
    AI_CAPTAINS_CONFIG,
    SHIP_CATALOG,
    CLEAVE_BASIS_THRESHOLD,
    CLEAVE_ENDOWMENT_CREDITS,
    CLEAVE_COOLDOWN_CYCLES,
)
from xylarium.kernel.models import (
    Captain,
    Sector,
    AIPersonality,
    Ship,
    CargoHold,
    ActionType,
)

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
        """An autonomous captain's turn: one weighed choice among everything open to it (turn.py) - gates kept as
        gates, side work alongside, every exclusive action priced and weighed through its own mind."""
        from xylarium.kernel import turn
        turn.run(kernel, captain)

    @classmethod
    def _financier_arbitrage(cls, kernel: "GameKernel", captain: Captain) -> None:
        """
        A financier's desk: round-trip SOL through a Galactic ISSE cross pair and the two federation
        exchanges when the triangle pays after fees. The trade itself pulls the cross rate back toward
        the rates the SOL hub implies.
        """
        from xylarium.config import FINANCIER_ARBITRAGE_MIN_EDGE
        from xylarium.kernel.cognition import temperament
        if temperament(captain, kernel).get("calling") != "financier":
            return
        fxm = kernel.fx_market
        budget = motive.investable(kernel, captain)
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
        """An outlaw creed past its line weighs its raids alone (turn._outlaw: tribute, a fight, the hunt) and takes
        the best, if any is worth its cost. Returns True if it acted."""
        from xylarium.kernel import turn
        best = motive.pick(kernel, captain, turn._outlaw(kernel, captain, sector), "outlaw")
        if best is None:
            return False
        return getattr(best["act"](), "success", True) is not False

    @classmethod
    def _native_option(cls, kernel: "GameKernel", captain: Captain, planet, sub: str) -> Dict:
        """What a dealing with a native people is worth to this captain (natives.py's own yields), in Cr."""
        from xylarium.config import (COMMODITY_CONFIG, NATIVE_EXPLOIT_YIELD, NATIVE_TRADE_UNITS,
                                     RESEARCH_POINTS_PER_UNIT, HOSTILE_ACT_BOUNTY)
        from xylarium.kernel import decide
        n = planet.natives
        price = lambda g: COMMODITY_CONFIG.get(g, {}).get("base_price", 20)
        deposits = {k: v for k, v in planet.element_deposits.items() if v > 0}
        richest = max(deposits, key=deposits.get) if deposits else "ORGANICS"
        wage = float(kernel.crew_wage(captain))
        if sub == "observe":
            units = (3 + n["stage"]) / RESEARCH_POINTS_PER_UNIT
            return decide.option(sub, wage, units * motive.knowledge_price(kernel))
        if sub == "contact":                      # it opens trade: a season of barter, over the captain's horizon
            trade = (NATIVE_TRADE_UNITS + 2 * n["stage"]) * price(richest) - NATIVE_TRADE_UNITS * price("ORGANICS")
            return decide.option(sub, 2 * wage, decide.worth(kernel, max(0.0, trade) / 4.0,
                                                              motive.mind(kernel, captain)))
        if sub == "trade":
            got = (NATIVE_TRADE_UNITS + 2 * n["stage"]) * price(richest)
            return decide.option(sub, wage + NATIVE_TRADE_UNITS * price("ORGANICS"), got)
        if sub == "protect":                      # a tithe each quarter, over its horizon
            tithe = sum(price(g) * q for g, q in (n.get("tribute") or {}).items()) or n["stage"] * price("ORGANICS")
            return decide.option(sub, wage, decide.worth(kernel, tithe, motive.mind(kernel, captain)))
        if sub == "collect":
            return decide.option(sub, wage, sum(price(g) * q for g, q in (n.get("tribute") or {}).items()))
        if sub == "exploit":                      # the ore, less the law's price where it is enforced
            sector = kernel.sectors[planet.sector_id]
            got = min(NATIVE_EXPLOIT_YIELD, sum(deposits.values())) * price(richest)
            return decide.option(sub, wage + (HOSTILE_ACT_BOUNTY if sector.is_protected_space else 0), got)
        return decide.option(sub, wage, 0.0)

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
        from xylarium.kernel import populace
        if not populace.room_for_captain(kernel):
            return None

        grown_count = len(getattr(captain, "grown_basis", []))
        from xylarium.config import PROCESSES
        from xylarium.kernel import knowledge
        learned = sum(knowledge.captain_mastery(kernel, captain, p) for p in PROCESSES)

        # Must meet the cognitive tipping point (about five capabilities half-mastered)
        if grown_count < CLEAVE_BASIS_THRESHOLD and learned < 2.5:
            return None

        # Must be able to endow the offshoot out of what it does not keep back
        if not motive.affords(kernel, captain, CLEAVE_ENDOWMENT_CREDITS):
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

        # Manifold Walk: an offshoot inherits with variation - mutation is chance, not choice (the only chance here)
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
        # Ship class: the hull whose capacity its calling lives by (holds to trade, bays to fight)
        if child_personality in (AIPersonality.TRADER, AIPersonality.INDUSTRIALIST):
            ship_class = "Merchant Cruiser"
        else:
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

        # The offshoot starts from its parent's bearing, until its own deeds outweigh it (no history of its own yet)
        child_cap.cosmic_alignment = captain.cosmic_alignment
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
        """Point the captain's people's inquiry at the domain its calling lives by (its character, not a list)."""
        calling = {
            AIPersonality.INDUSTRIALIST: "materials",      # foundries and repair swarms
            AIPersonality.PIRATE: "information",           # veils and the knowledge of where prey sails
            AIPersonality.TRADER: "energy",                # folding space shortens every route
            AIPersonality.MERCENARY: "materials",
        }
        kernel.dispatch(captain.id, ActionType.RESEARCH_SELECT, tech_key=calling.get(captain.personality, "information"))

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
            elif motive.affords(kernel, captain, 1500):
                kernel.dispatch(
                    captain.id,
                    ActionType.LOBBY_CONTRIBUTE,
                    amount=1500,
                    ticker=comp.ticker,
                )

            # 4. Sales Executive Recruitment & Mobility
            if len(comp.sales_executives) < 2 and motive.affords(kernel, captain, 2500):
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
            if comp.consumer_trust < 60 and motive.affords(kernel, captain, 3000):
                kernel.dispatch(
                    captain.id,
                    ActionType.MARKETING_CAMPAIGN,
                    ticker=comp.ticker,
                    campaign_type="POSITIVE",
                )
            elif motive.affords(kernel, captain, 4500):
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
    def _warp_captain(cls, kernel: "GameKernel", captain: Captain, destination: int) -> None:
        """Moves captain from current sector to destination."""
        old_sec = kernel.sectors[captain.sector_id]
        if captain.id in old_sec.captains:
            old_sec.captains.remove(captain.id)

        captain.sector_id = destination
        new_sec = kernel.sectors[destination]
        if captain.id not in new_sec.captains:
            new_sec.captains.append(captain.id)
        from xylarium.kernel import comms
        comms.arrive(kernel, f"captain:{captain.id}", destination)       # word rides the ship

    @classmethod
    def _maybe_chatter(cls, kernel: "GameKernel", captain: Captain, sector: Sector) -> None:
        """A captain talks on the radio when its credits moved since it last spoke (it has news), no more than
        once a fiscal quarter."""
        from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
        cd = captain.deed_cooldowns
        last = cd.get("CHATTER_CREDITS")
        if cd.get("CHATTER", -1) > kernel.cycle_count or last == captain.credits:
            return
        cd["CHATTER"] = kernel.cycle_count + FISCAL_QUARTER_CYCLES
        cd["CHATTER_CREDITS"] = captain.credits
        if last is not None:
            cls._broadcast_chatter(kernel, captain, sector)

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
                    # the Federal Bounty Office pays out of the Reserve's own funds - a transfer, never minted
                    fed = getattr(kernel, "federal_reserve", None)
                    bounty_amount = min(5000, max(0, fed.treasury)) if (fed is not None and attacker) else 0
                    if attacker and bounty_amount > 0:
                        fed.treasury -= bounty_amount
                        fed.stats["bounties_paid"] = fed.stats.get("bounties_paid", 0) + bounty_amount
                        attacker.credits += bounty_amount
                        attacker.score += 1000
                    if bounty_amount <= 0:
                        return

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

