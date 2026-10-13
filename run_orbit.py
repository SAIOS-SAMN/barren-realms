#!/usr/bin/env python3
"""
run_orbit.py: Continuous production game engine orbit runner with first-class observer telemetry.
Ticks the real Xylarium game engine, executes seasonal subsystems, and monitors all physical manifolds.
"""

import sys
from xylarium.kernel.engine import GameKernel
from xylarium.kernel import observation

def main():
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 100
    kernel = GameKernel(seed=1337)
    kernel.activate()
    result = observation.run_orbit(kernel, cycles=cycles, interval_cycles=20, verbose=True)
    
    print("\n" + "=" * 80)
    print(f"CONTINUOUS ENGINE ORBIT COMPLETE ({result['cycles_completed']} CYCLES EXECUTED)")
    print("=" * 80)
    tel = result["final_telemetry"]
    print(f"Final Universe Cycle: {result['final_cycle']}")
    print(f"Universal Scale Factor a(t): {tel.get('distributed_singularities', {}).get('universal_scale_factor', 1.0):.6f}")
    print(f"Active Sectors: {tel.get('sectors_count')}, Captains: {tel.get('captains_count')}")
    ep_data = tel.get('epistemic_ontologies', {})
    print(f"Civilizational Intelligence Index: {ep_data.get('avg_intelligence_index', 0.0):.4f} across {ep_data.get('total_civilizations', 0)} civilizations")
    fleet_data = tel.get('living_trade_fleets', {})
    print(f"Living Trade Fleets: {fleet_data.get('active_haulers', 0)} active haulers | Wormhole-Capable: {fleet_data.get('wormhole_capable_haulers', 0)} | Escorted: {fleet_data.get('escorted_haulers', 0)}")
    print(f"Physical Manifolds Status: {'HEALTHY' if result['engine_healthy'] else 'DEGRADED'}")
    print("=" * 80)

if __name__ == "__main__":
    main()
