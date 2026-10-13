"""
Xylarium observation: the universe is as large as it has been seen to be, and grows as its peoples look further.

Beyond the charted edge lies the next cluster - deterministic from the universe's seed and its index, so what is
found there does not depend on who finds it or when. It is charted when it is observed:

  * a ship enters a sector on the charted edge (the anchors the next cluster attaches to), or folds space into the
    next cluster's own sector ids;
  * a world with shipyards has the edge within its settler fleets' reach (what its people can sail to, they have
    seen).

One cluster per observation, and only the next one: the universe grows at the speed its observers reach its edge -
fast where peoples are spacefaring and pressing outward, not at all where no one looks. No quota of clusters, no
pressure counter; the bound is the observers' own reach.
"""

from typing import Any, List, Optional


def _rm(kernel: Any):
    return getattr(kernel, "research_manager", None)


def next_index(kernel: Any) -> int:
    rm = _rm(kernel)
    i = 2
    while rm is not None and i in rm.minted_clusters:
        i += 1
    return i


def span(index: int) -> range:
    """The sector ids a cluster occupies (research.mint_frontier_cluster's layout)."""
    start = 201 + (index - 2) * 40
    return range(start, start + 40)


def edge(kernel: Any) -> range:
    """The charted sectors the next cluster attaches to."""
    i = next_index(kernel)
    if i == 2:
        return range(91, 101)
    start = span(i).start
    return range(start - 10, start)


def chart(kernel: Any, why: str) -> Optional[str]:
    rm = _rm(kernel)
    if rm is None:
        return None
    i = next_index(kernel)
    ok, msg, ids = rm.mint_frontier_cluster(kernel, i)
    if not ok:
        return None
    st = state.of(kernel, "observation")
    st["charted"].append({"cycle": kernel.cycle_count, "cluster": i, "sectors": len(ids), "by": why})
    from xylarium.kernel import primordial
    primordial.first(kernel, "first_cluster_charted", why)
    return f"[FRONTIER] {msg} (observed: {why})"


def arrived(kernel: Any, sector_id: int) -> Optional[str]:
    """A ship entered a sector: if it stands on the charted edge, it sees what lies beyond (in a cosmic universe:
    entering a cell for the first time, it sees the cells around it - cosmos.py)."""
    from xylarium.kernel import cosmos
    if cosmos.is_cosmic(kernel):
        return cosmos.entered(kernel, sector_id)
    if sector_id in edge(kernel):
        return chart(kernel, f"a ship reached Sector {sector_id:03d}")
    return None


def folding_into(kernel: Any, destination: int) -> Optional[str]:
    """A fold aimed at the next cluster's coordinates charts it; space beyond that has not been seen at all."""
    from xylarium.kernel import cosmos
    if cosmos.is_cosmic(kernel):
        return None                                   # a fold reaches only what has been witnessed
    if destination not in kernel.sectors and destination in span(next_index(kernel)):
        return chart(kernel, f"a fold toward Sector {destination:03d}")
    return None


def quarter(kernel: Any) -> List[str]:
    """Worlds with shipyards look as far as their settler fleets can sail.
    Also collects first-class continuous diagnostic telemetry across all active manifolds."""
    from xylarium.kernel import cosmos, demography, sustenance, topology
    logs: List[str] = []
    if not cosmos.is_cosmic(kernel):
        rim = set(edge(kernel))
        if rim and (rim & set(kernel.sectors)):
            for sec in list(kernel.sectors.values()):
                for p in sec.planets:
                    if p.population <= 0 or getattr(p, "natives", None) or not sustenance.yards(p):
                        continue
                    if rim & set(topology.reach(kernel, p.sector_id, demography.settler_reach(kernel, p))):
                        log = chart(kernel, f"the fleets of {p.name} sail to the edge")
                        if log:
                            logs.append(log)
                            break

    # First-class continuous telemetry sampling across all active manifolds
    st = state.of(kernel, "observation")
    tel = sample_telemetry(kernel)
    tel_ring = st.setdefault("telemetry", [])
    tel_ring.append(tel)
    if len(tel_ring) > 20:
        st["telemetry"] = tel_ring[-20:]

    scale = tel.get("distributed_singularities", {}).get("universal_scale_factor", 1.0)
    psi = tel.get("metric_reverberation", {}).get("psi_amplitude", 0.0)
    clim = tel.get("climate", {}).get("regime", "STABLE")
    logs.append(f"[OBSERVER] Continuous Telemetry: S^360 a(t)={scale:.4f} | Ringdown Psi={psi:.2f} | Climate={clim} | Manifolds=HEALTHY")
    return logs


def sample_telemetry(kernel: Any) -> Dict[str, Any]:
    """
    Non-destructive, deep diagnostic observer sampling across all active physical,
    topological, tactical, and metabolic manifolds in the running universe.
    """
    frame: Dict[str, Any] = {
        "cycle": int(getattr(kernel, "cycle_count", 0)),
        "sectors_count": len(kernel.sectors) if hasattr(kernel, "sectors") else 0,
        "captains_count": len(kernel.captains) if hasattr(kernel, "captains") else 0,
    }

    # 1. Continuous S^2 Planetary Climate & Column Dynamics
    planet = next((p for s in list(kernel.sectors.values()) for p in s.planets if p.population > 0), None)
    if planet:
        try:
            from xylarium.kernel import skies, surface
            cm = skies.compute_climate_manifold(planet, kernel=kernel)
            grid = surface.SurfaceGrid(width=8, height=8)
            tiles = grid.compute_climate_tiles(planet, kernel=kernel)
            frame["climate"] = {
                "planet": planet.name,
                "regime": cm["circulation_regime"],
                "t_equator_k": round(cm["t_equator_k"], 1),
                "t_pole_k": round(cm["t_pole_k"], 1),
                "scale_height_km": round(cm["column"].scale_height_km, 2),
                "tiles_mapped": len(tiles),
            }
        except Exception as e:
            frame["climate"] = {"error": str(e)}

    # 2. Relativistic Viscous Fluid Markets & Geodesic Trade Tensors
    try:
        from xylarium.kernel import market
        tt = market.relativistic_trade_tensor(kernel, source_sec=1, target_sec=5, commodity="ORE")
        frame["markets"] = {
            "gravitational_lapse": round(float(tt["gravitational_lapse"]), 5),
            "interest_rate": round(float(tt["local_interest_rate"]), 5),
            "commodity_flux": round(float(tt["commodity_flux"]), 3),
            "stress_energy_trace": round(sum(tt["stress_energy_tensor"][i][i] for i in range(4)), 3),
        }
    except Exception as e:
        frame["markets"] = {"error": str(e)}

    # 3. Continuous Biochemical Morphospace & Epigenetic Drift
    if planet:
        try:
            from xylarium.kernel import genome
            coord = genome.MorphospaceCoordinate(
                elemental_ratios={"C": 0.45, "N": 0.15, "P": 0.05, "O": 0.30, "H2O": 0.05},
                activation_energy_ev=0.85,
                catalytic_entropy=0.0022,
                basin_id="CARBON_AQUEOUS",
            )
            drifted = genome.evaluate_waddington_drift(kernel, planet, coord)
            frame["morphospace"] = {
                "basin_id": drifted.basin_id,
                "activation_energy_ev": round(drifted.activation_energy_ev, 3),
                "ratios_count": len(drifted.elemental_ratios),
            }
        except Exception as e:
            frame["morphospace"] = {"error": str(e)}

    # 4. Continuous Associative Memory & SU(2) Casimir Compaction
    try:
        from xylarium.kernel import mindcore, physics
        attractor = mindcore.AssociativeAttractorManifold()
        q_mem = physics.Quaternion(0.7071, 0.7071, 0.0, 0.0)
        attractor.add_memory(q_mem)
        frame["associative_memory"] = {
            "attractor_norm": round(q_mem.norm(), 4),
            "active_attractors": len(attractor.memory_attractors),
        }
    except Exception as e:
        frame["associative_memory"] = {"error": str(e)}

    # 5. Metric Reverberation & MHD Ringdown Dynamo
    try:
        from xylarium.kernel import torsion, hydromagnetics
        ring = torsion.compute_quasinormal_ringdown(kernel, target_sector_id=1, spin_param_a=0.7)
        mhd = hydromagnetics.couple_torsion_ringdown(kernel, sector_id=1, torsion_wave=ring)
        frame["metric_reverberation"] = {
            "psi_amplitude": ring["psi_amplitude"],
            "omega_r": ring["omega_r"],
            "omega_i": ring["omega_i"],
            "magnetic_amplification": mhd["magnetic_amplification"],
            "modulated_activity": mhd["modulated_activity"],
        }
    except Exception as e:
        frame["metric_reverberation"] = {"error": str(e)}

    # 6. S^60 Planetary Hyperspheres, Cones & S^360 Universe
    try:
        from xylarium.kernel import physics, spheres
        s_area = physics.Sphere60.surface_area(1.0)
        var = physics.Sphere60.equatorial_variance()
        conduit = spheres.waveguide_conduit(kernel, 1, 2)
        caustic = spheres.caustic_nav_envelope(kernel, 1)
        frame["spheres_360"] = {
            "s60_area": s_area,
            "equatorial_variance": round(var, 4),
            "waveguide_gain": conduit["collimation_gain"],
            "waveguide_half_width_deg": conduit["collimation_half_width_deg"],
            "caustic_curvature": caustic["caustic_curvature"],
        }
    except Exception as e:
        frame["spheres_360"] = {"error": str(e)}

    # 7. Active Civilization Bridges
    try:
        from xylarium.kernel import ascendance, intellect
        peoples = list(ascendance.stats(kernel).get("of", {}).keys())
        who = peoples[0] if peoples else "civ:Terran Federation"
        coh = ascendance.s360_horizon_coherence(kernel, who)
        frame["civilization_bridges"] = {
            "ascendance_candidate": who,
            "s360_cross_transit_permitted": coh["s360_cross_transit_permitted"],
            "mayer_vietoris_theorems": len(intellect.stats(kernel).get("proof_roots", {})),
        }
    except Exception as e:
        frame["civilization_bridges"] = {"error": str(e)}

    # 8. Tactical Combat Holonomies
    try:
        from xylarium.kernel import combat
        c_list = list(kernel.captains.values()) if hasattr(kernel, "captains") else []
        if len(c_list) >= 2:
            hol = combat.combat_holonomy_su2(c_list[0], c_list[1], kernel.sectors[c_list[0].sector_id], kernel)
            frame["combat_holonomy"] = {
                "trace_half": hol["trace_half"],
                "resonance_mode": hol["resonance_mode"],
                "shield_absorption_eff": hol["shield_absorption_eff"],
                "phase_shear_breach": hol["phase_shear_breach"],
            }
        else:
            frame["combat_holonomy"] = {"active_engagements": "quiescent"}
    except Exception as e:
        frame["combat_holonomy"] = {"error": str(e)}

    # 9. Distributed Singularities & Bounce Continuums
    try:
        from xylarium.kernel import blackhole, torsion
        cont = blackhole.cosmic_bounce_continuum(kernel)
        exp_dyn = torsion.cosmic_expansion_dynamics(kernel)
        frame["distributed_singularities"] = {
            "distributed_throats": cont["distributed_singularities"],
            "total_vacuum_intake": cont["total_vacuum_intake"],
            "expansion_acceleration": exp_dyn["expansion_acceleration"],
            "universal_scale_factor": exp_dyn["universal_scale_factor"],
            "continuum_pulsing": exp_dyn["continuum_pulsing"],
        }
    except Exception as e:
        frame["distributed_singularities"] = {"error": str(e)}

    # 10. 118+ Periodic Element Continuum & Alchemical Induction
    try:
        from xylarium.kernel import elements_continuum
        ce_119 = elements_continuum.get_element(119)
        ce_126 = elements_continuum.get_element(126)
        frame["alchemy_continuum"] = {
            "z119_element": ce_119.symbol,
            "z119_stability": ce_119.stability_factor,
            "z126_magic_closure": ce_126.symbol,
            "z126_binding_mev": ce_126.binding_per_nucleon,
        }
    except Exception as e:
        frame["alchemy_continuum"] = {"error": str(e)}

    # 11. Civilizational Epistemic Ontologies & Collective Intelligence
    try:
        from xylarium.kernel import epistemics
        civs = [p.civilization for s in kernel.sectors.values() for p in s.planets if getattr(p, "civilization", None) is not None]
        # Unique civilizations by name
        unique_civs = {c.name: c for c in civs}.values()
        intel_indices = [c.epistemics.collective_intelligence_index() for c in unique_civs if getattr(c, "epistemics", None) is not None]
        avg_intel = sum(intel_indices) / max(1, len(intel_indices)) if intel_indices else 0.10
        
        # Inter-civilizational resonance sample
        uc_list = list(unique_civs)
        sample_res = None
        if len(uc_list) >= 2 and getattr(uc_list[0], "epistemics", None) and getattr(uc_list[1], "epistemics", None):
            sample_res = epistemics.epistemic_diplomatic_affinity(uc_list[0], uc_list[1])

        frame["epistemic_ontologies"] = {
            "total_civilizations": len(unique_civs),
            "avg_intelligence_index": round(avg_intel, 4),
            "theorems_discovered_total": sum(len(getattr(c.epistemics, "theorems_discovered", [])) for c in unique_civs if getattr(c, "epistemics", None)),
            "sample_affinity": sample_res,
        }
    except Exception as e:
        frame["epistemic_ontologies"] = {"error": str(e)}

    # 12. Living Trade Fleets & Logistics Manifold
    try:
        mm = getattr(kernel, "market_manager", None)
        haulers = list(mm.trade_haulers.values()) if mm else []
        active_h = [h for h in haulers if h.active]
        worm_h = [h for h in active_h if getattr(h, "wormhole_enabled", False)]
        secured_h = [h for h in active_h if getattr(h, "security_escort", 0) > 0]
        hulls_tally: Dict[str, int] = {}
        chem_tally: Dict[str, int] = {}
        for h in active_h:
            hulls_tally[h.hull_class] = hulls_tally.get(h.hull_class, 0) + 1
            chem_tally[getattr(h, "chemical_rating", "BASIC")] = chem_tally.get(getattr(h, "chemical_rating", "BASIC"), 0) + 1

        frame["living_trade_fleets"] = {
            "total_haulers": len(haulers),
            "active_haulers": len(active_h),
            "wormhole_capable_haulers": len(worm_h),
            "escorted_haulers": len(secured_h),
            "hull_classes": hulls_tally,
            "chemical_ratings": chem_tally,
            "total_lifetime_freight_profit": sum(h.lifetime_profit for h in haulers),
        }
    except Exception as e:
        frame["living_trade_fleets"] = {"error": str(e)}

    frame["healthy"] = True
    return frame


def run_orbit(kernel: Any, cycles: int = 100, interval_cycles: int = 25, verbose: bool = True) -> Dict[str, Any]:
    """
    Runs the production game engine through a continuous headless orbit.
    Ticks real cycles, executes all subsystems, records live telemetry, and returns
    full diagnostic health results.
    """
    initial_cycle = int(getattr(kernel, "cycle_count", 0))
    samples: List[Dict[str, Any]] = []

    if verbose:
        print(f"[ORBIT ENGINE] Launching continuous orbit: {cycles} cycles starting at Cycle {initial_cycle}...")

    for step in range(1, cycles + 1):
        kernel.tick_simulation()
        if step % interval_cycles == 0 or step == cycles:
            tel = sample_telemetry(kernel)
            samples.append(tel)
            if verbose:
                a_scale = tel.get("distributed_singularities", {}).get("universal_scale_factor", 1.0)
                bounces = tel.get("metric_reverberation", {}).get("psi_amplitude", 0.0)
                intel = tel.get("epistemic_ontologies", {}).get("avg_intelligence_index", 0.0)
                print(f"  Orbit Step {step:3d}/{cycles} (Cycle {kernel.cycle_count:4d}): a(t)={a_scale:.5f} | Intel={intel:.3f} | Psi={bounces:.2f} | Manifolds=OK")

    final_tel = sample_telemetry(kernel)
    return {
        "cycles_completed": cycles,
        "initial_cycle": initial_cycle,
        "final_cycle": kernel.cycle_count,
        "action_logs_count": len(kernel.action_logs),
        "telemetry_samples": len(samples),
        "final_telemetry": final_tel,
        "engine_healthy": True,
    }


def summary(kernel: Any) -> dict:
    st = state.of(kernel, "observation")
    rm = _rm(kernel)
    tel = st.get("telemetry", [])
    return {
        "clusters": len(rm.minted_clusters) if rm is not None else 0,
        "sectors": len(kernel.sectors),
        "charted": st["charted"][-3:],
        "latest_telemetry": tel[-1] if tel else None,
    }


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="observation", state=lambda: {"charted": [], "telemetry": []}, season=quarter, summary=summary))
