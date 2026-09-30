#!/usr/bin/env python3
"""
simulate_swarm.py: High-Throughput Extended Swarm Simulation Stress Test for Xylarium.
Executes multi-hundred/thousand-cycle autonomous galaxy simulations to analyze
macroeconomic equilibrium, territorial empire expansion, colony compounding,
trade route dynamics, and AI rival interactions.
"""

import sys
import os
import time
import json
import argparse
from typing import Dict, Any, List

# Ensure barren-realms root is on Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, SecurityLevel
from xylarium.config import TOTAL_SECTORS, COMMODITY_CONFIG
from xylarium.persistence.store import StatePersistence


def run_swarm_simulation(
    cycles: int = 1000,
    seed: int = 1337,
    save_file: str = None,
    player_active: bool = True
) -> Dict[str, Any]:
    print("=" * 76)
    print(f"  XYLARIUM BBS: EXTENDED SWARM SIMULATION ENGINE")
    print(f"  Cycles: {cycles:,} | Universe Seed: {seed} | Sectors: {TOTAL_SECTORS}")
    print("=" * 76)

    kernel = GameKernel(seed=seed)

    player = None
    if player_active:
        player = kernel.register_player("c_voyager", "Captain Archer")
        player.credits = 15000
        player.turns_left = 500
        print(f">> Enrolled Player Participant: {player.name} ({player.id}) with {player.credits:,} Cr.")

    start_time = time.perf_counter()

    # Track metrics over time
    skirmish_count = 0
    radio_events_count = 0
    player_ops_executed = 0

    # Initial snapshot
    init_ai_captains = [c for c in kernel.captains.values() if c.is_ai]
    print(f">> Initialized {len(init_ai_captains)} Autonomous AI Captains:")
    for c in init_ai_captains:
        print(f"   • {c.name.ljust(18)} [{c.personality.value.upper().ljust(13)}] Sector {str(c.sector_id).zfill(3)} | {c.credits:,} Cr | {c.ship.ship_type}")

    print("\nExecuting autonomous simulation ticks...")
    last_print = 0

    for i in range(1, cycles + 1):
        # Optional Player automated behavior during simulation
        if player and i % 25 == 0:
            # Player periodically performs tactical or economic actions
            if player.credits >= 1000 and player.operatives < 10 and player.sector_id == 1:
                kernel.dispatch(player.id, ActionType.RECRUIT_OPERATIVES, amount=2)
                player_ops_executed += 1

            # Player probes for trade opportunities
            routes_res = kernel.dispatch(player.id, ActionType.OPTIMIZE_ROUTES)

            # If player has operatives and detects a rich AI colony, launch covert recon
            if player.operatives >= 2:
                for s in kernel.sectors.values():
                    for p in s.planets:
                        if p.owner_id and p.owner_id != player.id and p.treasury > 5000:
                            op_res = kernel.dispatch(
                                player.id,
                                ActionType.COVERT_OP,
                                target_type="PLANET",
                                target_id=p.id,
                                op_type="recon",
                                operatives=2
                            )
                            if op_res.success:
                                player_ops_executed += 1
                            break
                    if player_ops_executed > 10:
                        break

        # Tick Authoritative Universe Simulation
        kernel.tick_simulation()

        # Progress reporting every 200 cycles
        if i % 200 == 0 or i == cycles:
            elapsed = time.perf_counter() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            print(f"  [Cycle {str(i).rjust(5)}/{cycles}] - {rate:,.0f} cycles/sec | Elapsed: {elapsed:.3f}s")

    total_time = time.perf_counter() - start_time
    throughput = cycles / total_time if total_time > 0 else 0

    # Post-Simulation Analysis
    print("\n" + "=" * 76)
    print("  SIMULATION RESULTS & GALACTIC AUDIT")
    print("=" * 76)

    # 1. Performance
    print(f">> PERFORMANCE:")
    print(f"   Total Cycles:    {cycles:,}")
    print(f"   Wallclock Time:  {total_time:.4f} seconds")
    print(f"   Throughput:      {throughput:,.1f} cycles/second")

    # 2. Macroeconomics
    total_liquid_credits = sum(c.credits for c in kernel.captains.values())
    total_colony_vaults = sum(p.treasury for s in kernel.sectors.values() for p in s.planets)
    total_debt = sum(c.debt for c in kernel.captains.values())
    total_money_supply = total_liquid_credits + total_colony_vaults

    port_stocks = {"ORE": 0, "ORGANICS": 0, "EQUIPMENT": 0}
    port_count = 0
    for s in kernel.sectors.values():
        if s.port:
            port_count += 1
            for comm in port_stocks:
                port_stocks[comm] += s.port.stock.get(comm, 0)

    print(f"\n>> MACROECONOMIC LIQUIDITY:")
    print(f"   Liquid Captain Reserves:  {total_liquid_credits:,} Cr")
    print(f"   Planetary Vault Silos:    {total_colony_vaults:,} Cr")
    print(f"   Galactic M0 Money Supply: {total_money_supply:,} Cr")
    print(f"   Outstanding Federal Debt: {total_debt:,} Cr")
    print(f"   Active Ports:             {port_count}")
    print(f"   Port Warehouses:          Ore: {port_stocks['ORE']:,} | Organics: {port_stocks['ORGANICS']:,} | Equipment: {port_stocks['EQUIPMENT']:,}")

    # 3. Geopolitical Balance
    planets = [p for s in kernel.sectors.values() for p in s.planets]
    total_planets = len(planets)
    claimed_planets = [p for p in planets if p.owner_id is not None]
    unclaimed_planets = [p for p in planets if p.owner_id is None]
    total_pop = sum(p.population for p in planets)
    total_security_ops = sum(p.security_operatives for p in planets)

    ownership: Dict[str, int] = {}
    for p in claimed_planets:
        owner = kernel.captains.get(p.owner_id)
        name = owner.name if owner else p.owner_id
        ownership[name] = ownership.get(name, 0) + 1

    print(f"\n>> GEOPOLITICAL & TERRITORIAL METRICS:")
    print(f"   Planets in Galaxy:        {total_planets}")
    print(f"   Claimed Colonies:         {len(claimed_planets)} ({len(claimed_planets)/total_planets*100:.1f}%)")
    print(f"   Unclaimed Outposts:       {len(unclaimed_planets)}")
    print(f"   Galactic Population:      {total_pop:,} colonists")
    print(f"   Counter-Intel Security:   {total_security_ops:,} stationed operatives")

    print("   Colonial Empire Breakdown:")
    for name, count in sorted(ownership.items(), key=lambda x: x[1], reverse=True):
        print(f"     • {name.ljust(22)}: {count} world(s)")

    # 4. Captains Roster & Financial Standing
    print(f"\n>> CAPTAIN ROSTER & STANDINGS:")
    print(f"   {'Name':<18} {'Type':<14} {'Sector':<8} {'Credits':<14} {'Debt':<10} {'Shields':<10} {'Fighters':<10} {'Agents'}")
    print("   " + "-" * 88)
    for c in sorted(kernel.captains.values(), key=lambda x: x.credits, reverse=True):
        role_label = c.personality.value.upper() if c.is_ai and c.personality else "PLAYER"
        print(
            f"   {c.name:<18} "
            f"{role_label:<14} "
            f"{str(c.sector_id).zfill(3):<8} "
            f"{f'{c.credits:,} Cr':<14} "
            f"{f'{c.debt:,} Cr':<10} "
            f"{f'{c.ship.shields}/{c.ship.max_shields}':<10} "
            f"{str(c.ship.fighters):<10} "
            f"{str(c.operatives)}"
        )

    # 5. Planetary Deep Dive
    print(f"\n>> KEY COLONIAL STRONGHOLDS:")
    print(f"   {'Planet':<18} {'Sector':<8} {'Governor':<18} {'Tier':<8} {'Pop':<10} {'Morale':<8} {'Treasury':<14} {'SecOps'}")
    print("   " + "-" * 90)
    for p in sorted(claimed_planets, key=lambda x: x.treasury, reverse=True)[:6]:
        owner = kernel.captains.get(p.owner_id)
        owner_name = owner.name if owner else "Unknown"
        print(
            f"   {p.name:<18} "
            f"{str(p.sector_id).zfill(3):<8} "
            f"{owner_name:<18} "
            f"{'T' + str(p.citadel_level):<8} "
            f"{f'{p.population:,}':<10} "
            f"{str(p.morale) + '%':<8} "
            f"{f'{p.treasury:,} Cr':<14} "
            f"{p.security_operatives}"
        )

    # 6. Interstellar Securities Exchange (ISSE) & Corporate Audit
    companies = list(kernel.market_manager.companies.values())
    total_market_cap = sum(c.share_price * c.total_shares for c in companies)
    print(f"\n>> INTERSTELLAR SECURITIES EXCHANGE (ISSE) & CORPORATE AUDIT:")
    print(f"   Listed Corporations:      {len(companies)}")
    print(f"   Total Market Cap:         {total_market_cap:,} Credits")
    print(f"   Active Freight Manifests: {len(kernel.market_manager.contracts)} contracts")
    print(f"   Corporate Sales Execs:    {len(kernel.market_manager.executives)} stationed")
    print(f"   Trade Council Bills:      {len(kernel.market_manager.trade_council.active_resolutions)} active resolutions")
    print("\n   " + f"{'Ticker':<8} {'Company Name':<28} {'Price':<10} {'Market Cap':<14} {'Trust':<8} {'Treasury':<12} {'Chairman'}")
    print("   " + "-" * 92)
    for c in sorted(companies, key=lambda x: x.share_price * x.total_shares, reverse=True):
        mcap = f"{c.share_price * c.total_shares:,} Cr"
        chair = kernel.captains.get(c.chairman_id)
        chair_name = chair.name if chair else c.chairman_id
        print(f"   {c.ticker:<8} {c.name[:26]:<28} {str(c.share_price) + ' Cr':<10} {mcap:<14} {str(c.consumer_trust) + '%':<8} {f'{c.treasury:,} Cr':<12} {chair_name}")

    # Active Trade Council Resolutions
    if kernel.market_manager.trade_council.active_resolutions:
        print("\n   Active Interstellar Trade Council Resolutions:")
        for res in kernel.market_manager.trade_council.active_resolutions:
            target_str = f" -> Target: {res['target']}" if res.get("target") else ""
            print(f"     • [{res['bill_type']}] Sponsored by {res['sponsor']}{target_str} (Duration: {res.get('duration', 50)} cycles)")

    # 7. Radio Intercept Log
    recent_radio = kernel.event_bus.get_recent_radio(6)
    print(f"\n>> SUBSPACE RADIO INTERCEPT LOG ({len(recent_radio)} transmissions):")
    for r in recent_radio:
        sec_str = f" [Sec {str(r.sector_id).zfill(3)}]" if r.sector_id else ""
        print(f"   [{r.channel}]{sec_str} <{r.sender}>: {r.text}")

    # 8. Dual-Seat Netstratum Cognition & AI Emergence Audit
    from xylarium.kernel.cognition import SeatSurvive
    print(f"\n>> DUAL-SEAT NETSTRATUM COGNITION & AI EMERGENCE AUDIT:")
    print(f"   {'Name':<22} {'Metabolism':<12} {'Ration Book':<18} {'Grown Basis':<14} {'Tech Unlocks'}")
    print("   " + "-" * 90)
    for c in sorted(kernel.captains.values(), key=lambda x: x.name):
        books = SeatSurvive.peel_books(c, kernel)
        ration = books.get("RATION")
        if ration and ration.is_closed:
            ration_status = "CLOSED (Stable)"
        elif ration:
            acute = ration.get_acute_deficit()
            ration_status = f"DEFICIT ({acute.coordinate}: {acute.deficit:.1f})" if acute else "OPEN"
        else:
            ration_status = "N/A"

        techs = getattr(c, "technologies", [])
        tech_str = ", ".join(techs) if techs else "None"
        metab_str = getattr(c, "metabolism", "biotic").upper()
        grown_count = f"{len(c.grown_basis)} crystal(s)"

        print(f"   {c.name:<22} {metab_str:<12} {ration_status:<18} {grown_count:<14} {tech_str}")

    # Detailed cargo & metabolic verification
    print("\n   Captain Cargo & Metabolic Reserves:")
    for c in sorted(kernel.captains.values(), key=lambda x: x.name):
        cargo = c.ship.cargo
        elems_str = ", ".join(f"{k}:{v}" for k, v in cargo.elements.items() if v > 0)
        cargo_summary = f"Ore: {cargo.ore} | Org: {cargo.organics} | Eqp: {cargo.equipment}"
        if elems_str:
            cargo_summary += f" | Elements: [{elems_str}]"
        print(f"     • {c.name.ljust(22)}: {cargo_summary} (Holds: {cargo.total_used}/{cargo.capacity})")

    # 9. Extended Systems Galactic Audit (The Five Core Pillars)
    print(f"\n>> EXTENDED NETSTRATUM PILLARS AUDIT:")
    # Ideology
    treaties = list(kernel.ideology_manager.treaties.values()) if hasattr(kernel, "ideology_manager") else []
    print(f"   [1] Social Thermodynamics: {len(treaties)} ratified treaty networks | {len(kernel.ideology_manager.ledgers)} recorded cohesion ledgers")
    # Alchemy
    active_heats = [h for h in kernel.alchemy_manager.heat_accumulated.values() if h > 0] if hasattr(kernel, "alchemy_manager") else []
    print(f"   [2] Precursor Alchemy:     {len(kernel.alchemy_manager.recipes)} canonical recipes registered | {len(active_heats)} active thermal reactors")
    # Astronomy
    all_planets = kernel.get_all_planets()
    mean_angle = sum(p.orbital_angle for p in all_planets) / max(1, len(all_planets))
    print(f"   [3] Orbital Ephemeris:     {len(all_planets)} planets in Keplerian motion | Mean Phase Angle: {mean_angle:.1f}°")
    # Senate
    gov = kernel.governance_manager if hasattr(kernel, "governance_manager") else None
    if gov:
        edicts_count = len(gov.active_edicts)
        chancellor_name = gov.offices.get("CHANCELLOR", {}).incumbent_name if gov.offices.get("CHANCELLOR") else "None"
        print(f"   [4] Imperial Senate:       Grand Chancellor: {chancellor_name} | Federal Treasury: {gov.federal_treasury:,} Cr | Active Edicts: {edicts_count}")
    # Surface Grid
    total_districts = 0
    total_garrisons = 0
    for p in all_planets:
        total_garrisons += p.garrison_troops
        if p.surface_grid:
            tiles = p.surface_grid.get("tiles", [])
            total_districts += sum(1 for t in tiles if t.get("district") != "EMPTY")
    print(f"   [5] Surface & Invasion:    {total_districts} zoned surface districts | Total Garrisons: {total_garrisons:,} divisions")

    # 10. Persistence Verification
    if save_file:
        saved = StatePersistence.save_to_file(kernel, save_file)
        print(f"\n>> PERSISTENCE STATUS: Saved post-simulation state to {save_file} (Success: {saved})")

    print("=" * 76)
    print("  SIMULATION COMPLETE")
    print("=" * 76)

    return {
        "cycles": cycles,
        "elapsed_sec": total_time,
        "throughput_cycles_per_sec": throughput,
        "total_money_supply": total_money_supply,
        "total_planets_claimed": len(claimed_planets),
        "total_population": total_pop,
    }


def main():
    parser = argparse.ArgumentParser(description="Xylarium Swarm Simulation Runner")
    parser.add_argument("--cycles", type=int, default=1000, help="Number of simulation cycles to execute")
    parser.add_argument("--seed", type=int, default=1337, help="Universe generation seed")
    parser.add_argument("--save-file", default=None, help="Optional destination file for final state (default: do not save)")
    parser.add_argument("--no-player", action="store_true", help="Run purely autonomous without player agent")
    args = parser.parse_args()

    run_swarm_simulation(
        cycles=args.cycles,
        seed=args.seed,
        save_file=args.save_file,
        player_active=not args.no_player
    )


if __name__ == "__main__":
    main()
