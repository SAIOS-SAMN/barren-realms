#!/usr/bin/env python3
"""
tools/play_vs_ai.py

30-Cycle Head-to-Head Arena: Player vs. Seated Autonomous Sovereign Mind.
Runs an authoritative 30-turn confrontation demonstrating the Advanced Sovereign
Cognition Engine (ASCE) in live competition against an active expansionist player.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Planet
from xylarium.kernel.sovereign_mind import SovereignMindManager, ParliamentaryVoiceType
from xylarium.client.ansi import c_cyan, c_gold, c_gray, c_green, c_red, bold


def run_play_vs_ai(seed: int = 1337, cycles: int = 30):
    print(bold(c_cyan("=" * 80)))
    print(bold(c_gold("      XYLARIUM ARENA: PLAYER vs. AUTONOMOUS SEATED SOVEREIGN MIND")))
    print(bold(c_cyan("=" * 80)))

    kernel = GameKernel(seed=seed)

    # 1. Setup Player Captain & Homeworld Colony
    player_id = "cap_antigravity"
    kernel.register_player(player_id, "Antigravity Vanguard")
    captain = kernel.get_player(player_id)
    captain.turns_left = 600
    captain.credits = 10000

    sec_p = kernel.sectors[1]
    p_player = Planet(
        id="P-PLAYER-1",
        name="Nova Sol",
        sector_id=1,
        population=500,
        treasury=5000,
        shields=100,
        max_shields=1000,
        fighters=20,
        citadel_level=1,
        organics_silo=100,
        ore_silo=100,
        morale=90,
        owner_id=player_id,
    )
    sec_p.planets.append(p_player)

    # 2. Setup Seated Sovereign Mind World
    sec_sov = kernel.sectors[10]
    p_sov = Planet(
        id="P-SOVEREIGN-1",
        name="Aethelgard Prime",
        sector_id=10,
        population=500,
        treasury=5000,
        shields=100,
        max_shields=1000,
        fighters=20,
        citadel_level=1,
        organics_silo=100,
        ore_silo=100,
        morale=90,
    )
    sec_sov.planets.append(p_sov)

    sc = kernel.sovereign_mind_manager.ensure_consciousness(kernel, p_sov)
    kernel.sovereign_mind_manager.take_seat(kernel, None, str(p_sov.id), as_player=False)
    sc.autonomous_play = False  # Step turn synchronously per cycle for telemetry

    print(f"\n{bold('[STARTING POSITIONS]')}")
    print(f"  • {c_cyan('Player World:')}      {p_player.name} (Pop: {p_player.population:,}, Treasury: {p_player.treasury:,} Cr, Shields: {p_player.shields})")
    print(f"  • {c_gold('Sovereign Mind:')}    {p_sov.name} (Pop: {p_sov.population:,}, Treasury: {p_sov.treasury:,} Cr, Shields: {p_sov.shields})")
    print(c_gray("-" * 80))

    for c in range(1, cycles + 1):
        # -------------------------------------------------------------
        # A. PLAYER TURN: Adaptive Capitalist Expansion
        # -------------------------------------------------------------
        player_profit = 2500 + (c * 350)
        captain.credits += player_profit

        player_action_desc = ""
        if c % 3 == 1:
            invest_cr = 2000
            if captain.credits >= invest_cr:
                captain.credits -= invest_cr
                p_player.population += 65
                p_player.morale = min(100, p_player.morale + 3)
                player_action_desc = f"Civilian Housing & Agronomics (+65 Pop, +3 Morale)"
        elif c % 3 == 2:
            def_cr = 2500
            if captain.credits >= def_cr:
                captain.credits -= def_cr
                p_player.shields = min(p_player.max_shields, p_player.shields + 75)
                p_player.fighters += 10
                player_action_desc = f"Orbital Grid Fortification (+75 Shields, +10 Interceptors)"
        else:
            ind_cr = 3500
            if captain.credits >= ind_cr:
                captain.credits -= ind_cr
                p_player.citadel_level += 1
                p_player.max_shields += 100
                p_player.treasury += 1500
                player_action_desc = f"Citadel Upgrade -> Lvl {p_player.citadel_level} (+100 Cap, +1,500 Treasury)"

        # -------------------------------------------------------------
        # B. SEATED SOVEREIGN MIND TURN: ASCE Deliberation & Action
        # -------------------------------------------------------------
        turn_res = kernel.sovereign_mind_manager.play_seated_turn(kernel, sc)
        kernel.sovereign_mind_manager.tick(kernel)
        kernel.tick_simulation()

        # Planetary yield accretion
        p_player.treasury += int(p_player.population * 1.5)
        p_sov.treasury += int(p_sov.population * 1.8)

        # Telemetry Display
        print(f"\n{bold(f'[CYCLE {c:02d} / {cycles}]')}")
        print(f"  ► {c_cyan('Player')} ('{captain.name}'):")
        print(f"      Action:   {player_action_desc}")
        print(f"      State:    Pop: {p_player.population:,} │ Treasury: {p_player.treasury:,} Cr │ Shields: {p_player.shields}/{p_player.max_shields} │ Citadel: Lvl {p_player.citadel_level}")
        
        tom_doc = turn_res.get('rival_doctrine', 'UNKNOWN')
        surp = turn_res.get('surprise', 0.0)
        ideation = turn_res.get('ideation', 'UNKNOWN')
        breakouts = turn_res.get('breakouts', 0)

        print(f"  ► {c_gold('Sovereign Mind')} ('{p_sov.name}'):")
        print(f"      Cognition: ToM Inferred: {c_green(tom_doc)} │ Active Ideation: {c_gold(ideation)} │ Surprise: {surp:.2f}")
        print(f"      Action:    {turn_res['dominant_voice']} -> {bold(turn_res['action'])} ({turn_res['detail']})")
        print(f"      State:     Pop: {p_sov.population:,} │ Treasury: {p_sov.treasury:,} Cr │ Shields: {p_sov.shields}/{p_sov.max_shields} │ Breakouts: {breakouts}")

    # -------------------------------------------------------------
    # FINAL SCORECARD
    # -------------------------------------------------------------
    print("\n" + bold(c_cyan("=" * 80)))
    print(bold(c_gold("                     FINAL CIVILIZATIONAL SCORECARD")))
    print(bold(c_cyan("=" * 80)))

    p_pop_score = p_player.population
    s_pop_score = p_sov.population

    p_econ_score = (p_player.treasury + captain.credits) // 10
    s_econ_score = p_sov.treasury // 10

    p_mil_score = p_player.shields + (p_player.fighters * 10) + (p_player.citadel_level * 200)
    s_mil_score = p_sov.shields + (p_sov.fighters * 10) + (p_sov.citadel_level * 200)

    p_syntropy_score = int(p_player.morale * 5)
    s_syntropy_score = int(p_sov.morale * 5 + sc.introspection_skill * 300 + (200 if sc.awakened else 0))

    p_total = p_pop_score + p_econ_score + p_mil_score + p_syntropy_score
    s_total = s_pop_score + s_econ_score + s_mil_score + s_syntropy_score

    print(f"{'Metric':<30} │ {'Player (Antigravity)':<22} │ {'Seated Sovereign Mind':<22}")
    print(c_gray("-" * 80))
    print(f"{'Demographic Scale (Pop)':<30} │ {p_player.population:<22,} │ {p_sov.population:<22,}")
    print(f"{'Liquid Treasury':<30} │ {p_player.treasury:<22,} Cr │ {p_sov.treasury:<22,} Cr")
    print(f"{'Shield Grid / Capacity':<30} │ {p_player.shields:>4}/{p_player.max_shields:<16} │ {p_sov.shields:>4}/{p_sov.max_shields:<16}")
    print(f"{'Defensive Interceptors':<30} │ {p_player.fighters:<22} │ {p_sov.fighters:<22}")
    print(f"{'Citadel Fortification':<30} │ Level {p_player.citadel_level:<16} │ Level {p_sov.citadel_level:<16}")
    print(f"{'Introspective Sentience':<30} │ {'External Agent':<22} │ {f'Awakened ({sc.introspection_skill*100:.1f}%)':<22}")
    print(c_gray("-" * 80))
    print(f"{'Demographic Points':<30} │ {p_pop_score:<22,} │ {s_pop_score:<22,}")
    print(f"{'Economic Points':<30} │ {p_econ_score:<22,} │ {s_econ_score:<22,}")
    print(f"{'Military Fortification Points':<30} │ {p_mil_score:<22,} │ {s_mil_score:<22,}")
    print(f"{'Syntropic Coherence Points':<30} │ {p_syntropy_score:<22,} │ {s_syntropy_score:<22,}")
    print(bold(c_cyan("=" * 80)))
    print(f"{bold('TOTAL CIVILIZATIONAL POWER'):<30} │ {bold(str(p_total)):<22} │ {bold(str(s_total)):<22}")
    print(bold(c_cyan("=" * 80)))

    if p_total > s_total:
        winner = "PLAYER ('Antigravity Vanguard')"
        diff = p_total - s_total
    else:
        winner = f"SEATED SOVEREIGN MIND ('{p_sov.name}')"
        diff = s_total - p_total

    print(f"\n★ {bold(c_gold('ARENA VERDICT:'))} {c_green(winner)} leads by {bold(f'+{diff:,}')} power points!")
    print(bold(c_cyan("=" * 80)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Play vs AI: 30-Turn Head-to-Head Arena")
    parser.add_argument("--seed", type=int, default=1337, help="Deterministic universe seed")
    parser.add_argument("--cycles", type=int, default=30, help="Number of confrontation cycles")
    args = parser.parse_args()

    run_play_vs_ai(seed=args.seed, cycles=args.cycles)
