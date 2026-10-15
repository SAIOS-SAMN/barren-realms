#!/usr/bin/env python3
"""
tools/observe_sovereign_daemon.py

Live Observer for Autonomous Seated Sovereign Cognition inside the Universe Daemon.

Runs the continuous universe simulation with seated sovereign minds, displaying
real-time telemetry of their emergent governance, cognitive deliberative cycles,
and technological ascent across cosmic cycles.
"""

import os
import sys
import argparse
import time
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import Planet
from xylarium.persistence.store import StatePersistence
from xylarium.client.ansi import c_cyan, c_gold, c_green, c_red, c_gray, bold


def initialize_seated_minds(kernel: GameKernel, top_n: int = 4) -> List[Planet]:
    """Seats autonomous sovereign minds on primary inhabited homeworlds."""
    candidates = [
        p for s in kernel.sectors.values() for p in s.planets
        if p.population >= 1000 or getattr(p, "civilization", None)
    ]
    # Sort by population descending to select major population centers
    candidates.sort(key=lambda p: getattr(p, "population", 0), reverse=True)
    selected = candidates[:top_n] if candidates else [p for s in kernel.sectors.values() for p in s.planets if p.population > 0][:top_n]

    for p in selected:
        sc = kernel.sovereign_mind_manager.ensure_consciousness(kernel, p)
        kernel.sovereign_mind_manager.take_seat(kernel, None, str(p.id), as_player=False)
        kernel.sovereign_mind_manager.toggle_autonomous_play(kernel, None, str(p.id), enable=True)

    return selected


def render_cycle_observer(cycle: int, kernel: GameKernel, seated_planets: List[Planet]) -> None:
    """Renders comprehensive real-time observer telemetry for the current universal cycle."""
    minds = kernel.sovereign_mind_manager.minds

    print(bold(c_cyan(f"\n╔══════════════════════════════════════════════════════════════════════════════════════════════════════╗")))
    print(bold(c_cyan(f"║ [OBSERVER] UNIVERSAL SIMULATION CYCLE {cycle:05d} │ ACTIVE SEATED MINDS: {len(seated_planets)}                           ║")))
    print(bold(c_cyan(f"╠══════════════════════════════════════════════════════════════════════════════════════════════════════╣")))

    for p in seated_planets:
        sc = minds.get(str(p.id))
        if not sc:
            continue

        t_data = getattr(sc, "last_turn_data", {})
        action = t_data.get("action", sc.last_action_taken)
        detail = t_data.get("detail", "")
        voice = t_data.get("dominant_voice", sc.parliament.dominant_voice.value)
        ideation = t_data.get("ideation", getattr(sc.ideation_space, "last_collapsed_ideation", "NONE"))
        tom = t_data.get("rival_doctrine", getattr(sc.adversarial_tracker, "inferred_doctrine", "UNKNOWN"))
        surprise = t_data.get("surprise", 0.0)
        breakouts = t_data.get("breakouts", 0)

        techs = ", ".join(getattr(p, "technologies", [])) or "None"
        pop = getattr(p, "population", 0)
        treasury = getattr(p, "treasury", 0)
        food = getattr(p, "organics_silo", 0)
        ore = getattr(p, "ore_silo", 0)
        citadel = getattr(p, "citadel_level", 1)
        vessel = "YES (Interstellar)" if "INTERSTELLAR_FLIGHT" in getattr(p, "technologies", []) else "No"

        print(f"║  ► {c_gold(bold(p.name))} ({p.planet_type}, Sec {p.sector_id}) │ {c_cyan('Pop')}: {pop:,} │ {c_cyan('Treasury')}: {treasury:,} Cr │ {c_cyan('Citadel')}: L{citadel}")
        print(f"║      {c_gray('Reserves')}:   Food: {food} │ Ore: {ore} │ {c_gray('Interstellar')}: {c_green(vessel)}")
        print(f"║      {c_gray('Techs')}:      {c_green(techs)}")
        print(f"║      {c_gray('Cognition')}:  ToM: {c_gold(tom)} │ Active Ideation: {c_cyan(ideation)} │ Voice: {voice}")
        print(f"║      {c_gray('Dynamics')}:   Surprise: {surprise:.2f} │ Phase Breakouts: {breakouts}")
        print(f"║      {c_gray('Action')}:     {bold(action)} -> {c_gray(detail)}")
        print(c_cyan("╟──────────────────────────────────────────────────────────────────────────────────────────────╢"))

    print(bold(c_cyan(f"╚══════════════════════════════════════════════════════════════════════════════════════════════════════╝")))


def render_final_scorecard(kernel: GameKernel, seated_planets: List[Planet]) -> None:
    """Renders comparative civilizational scorecard at the conclusion of the observation session."""
    minds = kernel.sovereign_mind_manager.minds

    print("\n" + bold(c_cyan("=" * 100)))
    print(bold(c_gold("              FINAL CIVILIZATIONAL EVOLUTION SCORECARD (EMERGENT SEATED MINDS)")))
    print(bold(c_cyan("=" * 100)))

    header = f"{'Civilization (World)':<28} │ {'Biome':<14} │ {'Pop':<10} │ {'Treasury':<12} │ {'Citadel':<8} │ {'Techs':<6} │ {'Interstellar':<14}"
    print(bold(header))
    print(c_gray("-" * 100))

    for p in seated_planets:
        sc = minds.get(str(p.id))
        tech_cnt = len(getattr(p, "technologies", []))
        has_vessel = "Cycle Launch" if "INTERSTELLAR_FLIGHT" in getattr(p, "technologies", []) else "Terrestrial"
        line = f"{p.name:<28} │ {p.planet_type:<14} │ {p.population:<10,} │ {p.treasury:<9,} Cr │ Lvl {p.citadel_level:<4} │ {tech_cnt:<6} │ {has_vessel:<14}"
        print(line)

    print(bold(c_cyan("=" * 100)))


def run_observer_session(
    cycles: int = 30,
    interval: float = 0.5,
    seed: int = 42,
    top_n: int = 4,
    save_file: str = "runs/observer_universe.json",
):
    print(bold(c_cyan("=" * 100)))
    print(bold(c_gold("   XYLARIUM UNIVERSE DAEMON: LIVE OBSERVER FOR SEATED SOVEREIGN COGNITION")))
    print(bold(c_cyan("=" * 100)))

    os.makedirs(os.path.dirname(os.path.abspath(save_file)), exist_ok=True)
    if os.path.exists(save_file):
        print(f"\n{bold('[RESUMING PERSISTENT UNIVERSE]')}")
        print(f"  • Loading existing universe state from {save_file}...")
        kernel = StatePersistence.load_from_file(save_file)
        seated_pids = list(kernel.sovereign_mind_manager.minds.keys())
        seated_planets = [kernel.get_planet(pid) for pid in seated_pids if kernel.get_planet(pid)]
        if not seated_planets:
            seated_planets = initialize_seated_minds(kernel, top_n=top_n)
    else:
        print(f"\n{bold('[BOOTSTRAPPING NEW UNIVERSE & SEATING MINDS]')}")
        kernel = GameKernel(seed=seed)
        seated_planets = initialize_seated_minds(kernel, top_n=top_n)

    for p in seated_planets:
        print(f"  • {c_gold(bold(p.name))} ({p.planet_type}, Sector {p.sector_id}) - Pop: {p.population:,}, Treasury: {p.treasury:,} Cr")

    print(c_gray("\nBeginning continuous simulation observation loop...\n"))

    for c in range(1, cycles + 1):
        kernel.tick_simulation()
        render_cycle_observer(c, kernel, seated_planets)
        if interval > 0:
            time.sleep(interval)

    render_final_scorecard(kernel, seated_planets)

    # Persist final state
    StatePersistence.save_to_file(kernel, save_file)
    print(c_green(f"\n✔ Universe state cleanly persisted to {save_file}."))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Observer for Seated Sovereign Cognition inside Daemon")
    parser.add_argument("--cycles", type=int, default=30, help="Number of simulation cycles to observe (default: 30)")
    parser.add_argument("--interval", type=float, default=0.2, help="Seconds between cycles (default: 0.2s)")
    parser.add_argument("--seed", type=int, default=42, help="Universe seed (default: 42)")
    parser.add_argument("--top-n", type=int, default=4, help="Number of primary worlds to seat sovereign minds on (default: 4)")
    parser.add_argument("--save", type=str, default="runs/observer_universe.json", help="Save file path")

    args = parser.parse_args()
    run_observer_session(
        cycles=args.cycles,
        interval=args.interval,
        seed=args.seed,
        top_n=args.top_n,
        save_file=args.save,
    )
