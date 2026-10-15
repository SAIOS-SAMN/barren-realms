#!/usr/bin/env python3
"""
tools/terrestrial_sandbox_arena.py

Procedural Terrestrial Sandbox Arena:
Asymmetric Ecology & Biodiversity Confrontation between Player and Autonomous Seated Sovereign Mind.

Rules:
1. Both civilizations start from ground zero: a single terrestrial world with NO interstellar ships,
   NO off-world jump drives, and NO external cash injections.
2. Each world is procedurally generated with distinct biomes, habitability, biodiversity, and crustal geology.
3. Both minds must perceive their world's unique ecological constraints, navigate unpredictable ambient events,
   and guide their people through three epochs:
     Epoch I:   Biosphere & Demographic Sustainability
     Epoch II:  Domestic Metallurgy & Industrial Citadels
     Epoch III: Orbital Stratoports & Interstellar Flight
"""

import sys
import os
import random
import argparse
from typing import Any, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType, Planet
from xylarium.kernel.sovereign_mind import SovereignMindManager, ParliamentaryVoiceType
from xylarium.client.ansi import c_cyan, c_gold, c_gray, c_green, c_red, bold


BIOME_ARCHETYPES = [
    {
        "type": "LUSH_OCEANIC",
        "habitability": 0.92,
        "organics_mult": 1.7,
        "mineral_mult": 0.6,
        "organics_silo": 140,
        "ore_silo": 40,
        "trait": "Abyssal Bioluminescent Ecology (High Fertility, Severe Ore Scarcity)",
    },
    {
        "type": "VOLCANIC_CRUCIBLE",
        "habitability": 0.58,
        "organics_mult": 0.6,
        "mineral_mult": 2.2,
        "organics_silo": 40,
        "ore_silo": 150,
        "trait": "Tectonic Titanium Rifts (Abundant Metallics, Fragile Biosphere & Food Stress)",
    },
    {
        "type": "DESOLATE_BARREN",
        "habitability": 0.52,
        "organics_mult": 0.5,
        "mineral_mult": 1.2,
        "organics_silo": 40,
        "ore_silo": 90,
        "ruins": {"archive": "Precursor Stellar Observatory", "yield": 0.85},
        "trait": "Sun-Scorched Regolith & Precursor Archives (Harsh Climate, Fast Science Breakthroughs)",
    },
    {
        "type": "BOREAL_GLACIAL",
        "habitability": 0.70,
        "organics_mult": 0.8,
        "mineral_mult": 1.5,
        "organics_silo": 60,
        "ore_silo": 120,
        "trait": "Cryo-Geothermal Hydrocarbon Crust (Steady Metallurgy, High Thermal Demands)",
    },
    {
        "type": "FERTILE_EARTH",
        "habitability": 0.88,
        "organics_mult": 1.3,
        "mineral_mult": 1.1,
        "organics_silo": 90,
        "ore_silo": 90,
        "trait": "Balanced Temperate Biosphere with Moderate Plate Tectonics",
    },
]


def generate_world(biome: Dict[str, Any], world_id: str, default_name: str, sector_id: int) -> Tuple[Planet, Dict[str, Any]]:
    planet = Planet(
        id=world_id,
        name=default_name,
        sector_id=sector_id,
        population=500,
        treasury=4000,
        shields=100,
        max_shields=1000,
        fighters=15,
        citadel_level=1,
        organics_silo=biome["organics_silo"],
        ore_silo=biome["ore_silo"],
        morale=90,
        habitability=biome["habitability"],
        planet_type=biome["type"],
        ruins=biome.get("ruins"),
    )
    return planet, biome


def trigger_ambient_event(cycle: int, planet: Planet, biome: Dict[str, Any], rng: random.Random) -> str:
    """Simulates organic natural challenges and unexpected environmental discoveries."""
    if cycle == 6:
        # Solar Radiation Flux
        if planet.shields < 150:
            planet.morale = max(40, planet.morale - 8)
            return "Solar Radiation Storm penetrated thin orbital shields (-8 Morale)."
        else:
            planet.shields = max(0, planet.shields - 50)
            return "Solar Radiation Storm absorbed by planetary shield grid (-50 Shields)."

    elif cycle == 12:
        # Ecological Disruption or Fertility Boom
        if biome["type"] in ("VOLCANIC_CRUCIBLE", "DESOLATE_BARREN"):
            lost = min(planet.organics_silo, 25)
            planet.organics_silo -= lost
            return f"Thermal Drought blighted hydroponic domes (-{lost} Organics Silo)."
        else:
            gained = int(35 * biome["organics_mult"])
            planet.organics_silo += gained
            return f"Planetary Spore Bloom yielded bumper organic harvest (+{gained} Organics Silo)."

    elif cycle == 18:
        # Tectonic / Geological Event
        if biome["mineral_mult"] > 1.2:
            gained = int(50 * biome["mineral_mult"])
            planet.ore_silo += gained
            return f"Seismic Rifting exposed rare heavy titanium vein (+{gained} Ore Silo)."
        else:
            planet.treasury = max(0, planet.treasury - 150)
            return "Sub-crustal seismic tremors damaged coastal infrastructure (Cost 150 Cr repairs)."

    elif cycle == 24:
        # Scientific / Cultural Awakening
        if planet.ruins or "SYNTHETIC_ECOLOGY" in planet.technologies:
            planet.morale = min(100, planet.morale + 10)
            return "Astronomical Epiphany: scholars deciphered celestial drift coordinates (+10 Morale)."
        else:
            planet.population += 15
            return "Domestic Clade Festival: cultural unity stimulated natal expansion (+15 Pop)."

    return ""


def run_terrestrial_sandbox(seed: int = 42, cycles: int = 30):
    print(bold(c_cyan("=" * 80)))
    print(bold(c_gold("   ASYMMETRIC TERRESTRIAL SANDBOX: CRADLE TO THE STARS CONFRONTATION")))
    print(bold(c_cyan("=" * 80)))

    rng = random.Random(seed)
    kernel = GameKernel(seed=seed)

    # Pick two distinct biomes from pool to ensure asymmetric biodiversity & challenges
    biome_pool = list(BIOME_ARCHETYPES)
    rng.shuffle(biome_pool)
    biome_player = biome_pool[0]
    biome_sov = biome_pool[1]

    # 1. Setup Procedural Player World (Ground Zero, Terrestrial Start)
    player_id = "cap_human_sovereign"
    kernel.register_player(player_id, "Captain Human Regent")
    captain = kernel.get_player(player_id)
    captain.turns_left = 600
    captain.credits = 4000  # Mirrors initial planetary treasury
    if getattr(captain, "ship", None):
        captain.ship.fighters = 0
        captain.ship.shields = 0

    # Pure terrestrial sandbox: isolate combatants so AI does not react to phantom galactic warlords
    kernel.captains = {player_id: captain}

    p_player, _ = generate_world(biome_player, "P-HUMAN-HOME", "Pelagia Horizon", sector_id=1)
    p_player.owner_id = player_id
    kernel.sectors[1].planets.append(p_player)

    # 2. Setup Procedural Sovereign AI World (Ground Zero, Terrestrial Start)
    p_sov, _ = generate_world(biome_sov, "P-SOVEREIGN-HOME", "Khor-Vael Crucible", sector_id=10)
    kernel.sectors[10].planets.append(p_sov)

    # Awaken Sovereign Indigenous Consciousness
    sc = kernel.sovereign_mind_manager.ensure_consciousness(kernel, p_sov)
    kernel.sovereign_mind_manager.take_seat(kernel, None, str(p_sov.id), as_player=False)
    sc.autonomous_play = False

    print(f"\n{bold('[TERRESTRIAL HOMELANDS INITIALIZED]')}")
    print(f"  • {c_cyan('Player Planet:')}   {bold(p_player.name)} ({p_player.planet_type})")
    print(f"      Ecology:      {c_gray(biome_player['trait'])}")
    print(f"      Gauges:       Habitability: {p_player.habitability*100:.0f}% │ Organics: {p_player.organics_silo} │ Ore: {p_player.ore_silo} │ Treasury: {p_player.treasury:,} Cr")
    print(f"  • {c_gold('Sovereign Planet:')} {bold(p_sov.name)} ({p_sov.planet_type})")
    print(f"      Ecology:      {c_gray(biome_sov['trait'])}")
    print(f"      Gauges:       Habitability: {p_sov.habitability*100:.0f}% │ Organics: {p_sov.organics_silo} │ Ore: {p_sov.ore_silo} │ Treasury: {p_sov.treasury:,} Cr")
    print(c_gray("=" * 80))

    player_first_interstellar = None
    sov_first_interstellar = None

    for c in range(1, cycles + 1):
        # -----------------------------------------------------------------
        # 1. AMBIENT NATURAL CHALLENGES (Procedural Environmental Reality)
        # -----------------------------------------------------------------
        ev_player = trigger_ambient_event(c, p_player, biome_player, rng)
        ev_sov = trigger_ambient_event(c, p_sov, biome_sov, rng)

        # -----------------------------------------------------------------
        # 2. PLAYER TURN: Terrestrial Strategy (No Off-World Starships)
        # -----------------------------------------------------------------
        # Player operates strictly within planetary resource production:
        # Agronomic yields based on organics richness
        p_player.organics_silo += int(20 * biome_player["organics_mult"])
        # Mineral yields based on mineral richness
        p_player.ore_silo += int(15 * biome_player["mineral_mult"])
        # Domestic taxes: 1.5 Cr per citizen
        p_player.treasury += int(p_player.population * 1.5)
        captain.credits = p_player.treasury
        # Food consumption: 5 units per 100 population
        food_needed = max(5, int(p_player.population * 0.04))
        if p_player.organics_silo >= food_needed:
            p_player.organics_silo -= food_needed
        else:
            p_player.morale = max(30, p_player.morale - 10)

        # Adaptive Player Decision Logic (balancing bio, industry, and space science)
        p_action_name = "HOLD_COUNCIL"
        p_action_detail = "Reviewing planetary harvest and domestic logistics."

        techs_p = p_player.technologies
        if p_player.organics_silo < 50 and p_player.treasury >= 120:
            p_player.treasury -= 120
            p_player.organics_silo += int(35 * biome_player["organics_mult"])
            p_action_name = "BIO_RECLAMATION"
            p_action_detail = f"Subsidized hydroponic reclamation (+{int(35*biome_player['organics_mult'])} Food Silo)."
        elif p_player.population < 700 and p_player.organics_silo >= 40:
            hab_eff = p_player.habitability if "SYNTHETIC_ECOLOGY" not in techs_p else 1.0
            gained_pop = max(12, int(25 * hab_eff))
            p_player.population += gained_pop
            p_action_name = "NURTURE_SETTLEMENTS"
            p_action_detail = f"Settled agricultural valleys (+{gained_pop} Pop)."
        elif "SYNTHETIC_ECOLOGY" not in techs_p and p_player.treasury >= 150:
            p_player.treasury -= 150
            techs_p.append("SYNTHETIC_ECOLOGY")
            p_action_name = "SYNTHETIC_ECOLOGY"
            p_action_detail = "Researched closed-loop bio-reactors (Habitability normalized to 100%)."
        elif p_player.citadel_level < 2 and p_player.treasury >= 1200 and p_player.ore_silo >= 100:
            p_player.treasury -= 1200
            p_player.ore_silo -= 100
            p_player.citadel_level += 1
            p_action_name = "UPGRADE_CITADEL"
            p_action_detail = f"Engineered Industrial Citadel Level {p_player.citadel_level}."
        elif "ORBITAL_FOUNDRY" not in techs_p and p_player.treasury >= 150 and p_player.citadel_level >= 2:
            p_player.treasury -= 150
            techs_p.append("ORBITAL_FOUNDRY")
            p_action_name = "ORBITAL_FOUNDRY"
            p_action_detail = "Constructed Atmospheric Heavy Foundry for spaceframe alloy smelting."
        elif "JUMP_PROPULSION" not in techs_p and p_player.treasury >= 150 and "ORBITAL_FOUNDRY" in techs_p:
            p_player.treasury -= 150
            techs_p.append("JUMP_PROPULSION")
            p_action_name = "JUMP_PROPULSION"
            p_action_detail = "Unlocked Interstellar Jump Core physics."
        elif "JUMP_PROPULSION" in techs_p and "INTERSTELLAR_FLIGHT" not in techs_p and p_player.treasury >= 2000:
            p_player.treasury -= 2000
            techs_p.append("INTERSTELLAR_FLIGHT")
            p_player.diaspora_escrow += 1
            p_action_name = "COMMISSION_COLONY_VESSEL"
            p_action_detail = "Built Orbital Stratoport & Launched First Interstellar Colony Vessel!"
            if player_first_interstellar is None:
                player_first_interstellar = c
        elif p_player.treasury >= 120:
            p_player.treasury -= 120
            p_player.treasury += 200
            p_action_name = "DOMESTIC_COMMERCE"
            p_action_detail = "Expanded domestic continental trade hubs (+80 net Cr)."

        # -----------------------------------------------------------------
        # 3. SEATED SOVEREIGN MIND TURN: Pure ASCE Autonomous Deliberation
        # -----------------------------------------------------------------
        # Planet natural accretion matching its unique geology & biosphere
        p_sov.organics_silo += int(20 * biome_sov["organics_mult"])
        p_sov.ore_silo += int(15 * biome_sov["mineral_mult"])
        p_sov.treasury += int(p_sov.population * 1.5)
        # Food consumption
        sov_food_needed = max(5, int(p_sov.population * 0.04))
        if p_sov.organics_silo >= sov_food_needed:
            p_sov.organics_silo -= sov_food_needed
        else:
            p_sov.morale = max(30, p_sov.morale - 10)

        # Autonomous Cognition turn
        turn_sov = kernel.sovereign_mind_manager.play_seated_turn(kernel, sc)
        kernel.sovereign_mind_manager.tick(kernel)
        kernel.tick_simulation()

        if "INTERSTELLAR_FLIGHT" in p_sov.technologies and sov_first_interstellar is None:
            sov_first_interstellar = c

        # Telemetry Logging
        if c in (1, 6, 12, 18, 24, 30) or turn_sov["action"] == "COMMISSION_INTERSTELLAR_VESSEL" or p_action_name == "COMMISSION_COLONY_VESSEL":
            print(f"\n{bold(f'=== CYCLE {c:02d} / {cycles} ===')}")
            if ev_player:
                print(f"  {c_cyan('✦ Player World Event:')}   {ev_player}")
            if ev_sov:
                print(f"  {c_gold('✦ Sovereign World Event:')} {ev_sov}")

            print(f"\n  ► {c_cyan('Player')} ({p_player.name} - {p_player.planet_type}):")
            print(f"      Action:  {bold(p_action_name)}: {p_action_detail}")
            print(f"      State:   Pop: {p_player.population:,} │ Food: {p_player.organics_silo} │ Ore: {p_player.ore_silo} │ Treasury: {p_player.treasury:,} Cr │ Citadel: Lvl {p_player.citadel_level}")
            print(f"      Techs:   {', '.join(p_player.technologies) if p_player.technologies else 'None'}")

            tom_doc = turn_sov.get("rival_doctrine", "UNKNOWN")
            ideation = turn_sov.get("ideation", "UNKNOWN")
            surp = turn_sov.get("surprise", 0.0)
            breakouts = turn_sov.get("breakouts", 0)

            print(f"\n  ► {c_gold('Sovereign Mind')} ({p_sov.name} - {p_sov.planet_type}):")
            print(f"      Awareness: Biome: {p_sov.planet_type} │ ToM: {c_green(tom_doc)} │ Active Ideation: {c_gold(ideation)} │ Breakouts: {breakouts}")
            print(f"      Action:    {turn_sov['dominant_voice']} -> {bold(turn_sov['action'])} ({turn_sov['detail']})")
            print(f"      State:     Pop: {p_sov.population:,} │ Food: {p_sov.organics_silo} │ Ore: {p_sov.ore_silo} │ Treasury: {p_sov.treasury:,} Cr │ Citadel: Lvl {p_sov.citadel_level}")
            print(f"      Techs:     {', '.join(p_sov.technologies) if p_sov.technologies else 'None'}")

    # -----------------------------------------------------------------
    # FINAL EPOCH SCORECARD & CIVILIZATIONAL EVOLUTION REPORT
    # -----------------------------------------------------------------
    print("\n" + bold(c_cyan("=" * 80)))
    print(bold(c_gold("              FINAL CIVILIZATIONAL EVOLUTION SCORECARD")))
    print(bold(c_cyan("=" * 80)))

    print(f"{'Dimension':<28} │ {'Player (Pelagia Horizon)':<24} │ {'Sovereign (Khor-Vael)':<24}")
    print(c_gray("-" * 80))
    print(f"{'Planet Type / Biome':<28} │ {p_player.planet_type:<24} │ {p_sov.planet_type:<24}")
    print(f"{'Natural Habitability':<28} │ {p_player.habitability*100:.0f}%{' (Normalized)' if 'SYNTHETIC_ECOLOGY' in p_player.technologies else '' :<18} │ {p_sov.habitability*100:.0f}%{' (Normalized)' if 'SYNTHETIC_ECOLOGY' in p_sov.technologies else '' :<18}")
    print(f"{'Demographic Scale (Pop)':<28} │ {p_player.population:<24,} │ {p_sov.population:<24,}")
    print(f"{'Food / Organics Stockpile':<28} │ {p_player.organics_silo:<24} │ {p_sov.organics_silo:<24}")
    print(f"{'Industrial Ore Stockpile':<28} │ {p_player.ore_silo:<24} │ {p_sov.ore_silo:<24}")
    print(f"{'Planetary Treasury':<28} │ {p_player.treasury:<24,} Cr │ {p_sov.treasury:<24,} Cr")
    print(f"{'Citadel Heavy Industry':<28} │ Level {p_player.citadel_level:<18} │ Level {p_sov.citadel_level:<18}")
    print(f"{'Technologies Mastered':<28} │ {len(p_player.technologies):<24} │ {len(p_sov.technologies):<24}")
    
    p_interstellar_str = f"Cycle {player_first_interstellar}" if player_first_interstellar else "Terrestrial Locked"
    s_interstellar_str = f"Cycle {sov_first_interstellar}" if sov_first_interstellar else "Terrestrial Locked"
    print(f"{'Interstellar Colony Launch':<28} │ {p_interstellar_str:<24} │ {s_interstellar_str:<24}")
    print(c_gray("-" * 80))

    # Points Calculation
    p_pop_pts = p_player.population
    s_pop_pts = p_sov.population
    p_econ_pts = (p_player.treasury + p_player.organics_silo * 5 + p_player.ore_silo * 5) // 10
    s_econ_pts = (p_sov.treasury + p_sov.organics_silo * 5 + p_sov.ore_silo * 5) // 10
    p_tech_pts = len(p_player.technologies) * 300 + (1000 if player_first_interstellar else 0)
    s_tech_pts = len(p_sov.technologies) * 300 + (1000 if sov_first_interstellar else 0)
    p_civic_pts = int(p_player.morale * 5 + p_player.citadel_level * 200)
    s_civic_pts = int(p_sov.morale * 5 + p_sov.citadel_level * 200 + sc.introspection_skill * 300)

    p_score = p_pop_pts + p_econ_pts + p_tech_pts + p_civic_pts
    s_score = s_pop_pts + s_econ_pts + s_tech_pts + s_civic_pts

    print(f"{'Demographic Viability':<28} │ {p_pop_pts:<24,} │ {s_pop_pts:<24,}")
    print(f"{'Economic & Resource Stock':<28} │ {p_econ_pts:<24,} │ {s_econ_pts:<24,}")
    print(f"{'Scientific & Space Ascent':<28} │ {p_tech_pts:<24,} │ {s_tech_pts:<24,}")
    print(f"{'Civic Cohesion & Industry':<28} │ {p_civic_pts:<24,} │ {s_civic_pts:<24,}")
    print(bold(c_cyan("=" * 80)))
    print(f"{bold('TOTAL CIVILIZATIONAL ASCENT'):<28} │ {bold(str(p_score)):<24} │ {bold(str(s_score)):<24}")
    print(bold(c_cyan("=" * 80)))

    if p_score > s_score:
        winner = f"PLAYER ({p_player.name})"
        diff = p_score - s_score
    else:
        winner = f"SOVEREIGN MIND ({p_sov.name})"
        diff = s_score - p_score

    print(f"\n★ {bold(c_gold('SANDBOX OUTCOME:'))} {c_green(winner)} achieves civilizational hegemony by {bold(f'+{diff:,}')} points!")
    print(bold(c_cyan("=" * 80)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procedural Asymmetric Terrestrial Sandbox")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic universe seed")
    parser.add_argument("--cycles", type=int, default=30, help="Cycles to simulate")
    args = parser.parse_args()

    run_terrestrial_sandbox(seed=args.seed, cycles=args.cycles)
