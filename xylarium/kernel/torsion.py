"""
Xylarium torsion: Einstein-Cartan singularity bounces, propagating wave pulses, and
the galactic core's hypha-connected torsion ledger (docs/TORSION_CONTINUUM.md).

In Einstein-Cartan gravity, quantum fermion spin density halts singular gravitational
collapse at the Cartan density, producing a nonsingular bounce. Every bounce emits an
expanding torsional shockwave that perturbs spacetime curvature and drives resonant
nucleosynthesis.

When the galactic centre (Sgr A*) or an ancient throat bounces, its event is permanently
witnessed and appended to the hypha banking ledger as an immutable physical receipt.
"""

from fractions import Fraction
import math
import zlib
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import state
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem

def speed_of_torsion(kernel: Any) -> float:
    """Torsion wave speed across the metric, dynamically derived from c and the cosmic clock ratio.
    
    In Einstein-Cartan geometry, torsion shockwaves propagate at the metric velocity c (fundamental.py).
    Scaled dynamically against the universe's clock pace: deep years per cycle (cosmos.py).
    """
    try:
        from xylarium.kernel import cosmos, fundamental
        laws = fundamental.of(cosmos.cosmos_seed(kernel))
        # c in kpc per Gyr is ~306.4 kpc/Myr. Scaled by deep clock ruler per fiscal cycle:
        pace = cosmos.ruler(kernel) if hasattr(cosmos, "ruler") else 1.0e6
        # Dynamic propagation speed in kpc per cycle
        return max(0.01, min(0.5, (pace / 1.0e6) * 0.05 * (1.0 / max(0.1, laws.alpha))))
    except Exception:
        return 0.05


def damping_rate(kernel: Any) -> float:
    """Gravitational and torsional damping through the ISM, derived from gas density and baryonic fraction."""
    try:
        from xylarium.kernel import creation, cosmos
        bb = creation.big_bang(cosmos.cosmos_seed(kernel))
        f_baryon = float(bb.get("f_baryon", 0.15))
        # Denser baryonic environments attenuate metric torsion faster: gamma ~ f_baryon
        return max(0.005, min(0.1, 0.02 * (f_baryon / 0.15)))
    except Exception:
        return 0.02


def coupling_constant(kernel: Any) -> Fraction:
    """Dimensionless gravitational coupling to orbital parameter q, derived from alpha_G."""
    try:
        from xylarium.kernel import cosmos, fundamental
        laws = fundamental.of(cosmos.cosmos_seed(kernel))
        # Coupling scales with fundamental gravitational coupling alpha_G
        ratio = laws.ratios.get("alpha_G", 1.0)
        num = max(1, min(10, int(round(ratio * 1))))
        return Fraction(num, 100000)
    except Exception:
        return Fraction(1, 100000)


def stats(kernel: Any) -> Dict[str, Any]:
    st = state.of(kernel, "torsion")
    st.setdefault("universal_scale_factor", 1.0)
    st.setdefault("vacuum_intake_total", 0.0)
    return st


def emit_bounce(
    kernel: Any,
    origin_sector: int,
    energy_scale: float,
    chirality: int = 1,
    source: str = "galactic_core",
) -> Dict[str, Any]:
    """Emit a new Einstein-Cartan torsion bounce from a singular collapse or core flare.
    
    The bounce is recorded deterministically in the local torsion event log, and if emitted
    by the galactic centre or an ancients' throat, is logged with the hypha ledger.
    """
    st = stats(kernel)
    cycle = int(getattr(kernel, "cycle_count", 0))
    event_id = f"bounce:{origin_sector}:{cycle}:{len(st['bounces']) + 1}"
    
    rec = {
        "id": event_id,
        "sector": origin_sector,
        "cycle": cycle,
        "energy": float(energy_scale),
        "chirality": 1 if chirality >= 0 else -1,
        "source": source,
    }
    st["bounces"].append(rec)
    
    # If emitted by galactic core, link to hypha
    if source in ("galactic_core", "centre", "sgr_a"):
        try:
            from xylarium.kernel import hypha, board, constellations
            ancients = board.ancient_peoples(kernel)
            house = ancients[0] if ancients else constellations.ELDERS
            if house and hypha.uplinked(kernel, house):
                hypha.append(
                    kernel,
                    lane="CORE",
                    kind="pouw",
                    payer=source,
                    payee="hypha",
                    amount=Fraction(int(energy_scale * 1000), 1000),
                    currency="SOL",
                    ref=event_id,
                    house=house,
                )
        except Exception:
            pass
            
    return rec


def eval_wavefront(kernel: Any, target_sector_id: int) -> Tuple[float, float, int]:
    """Evaluate the net active torsion wavefront at a given sector coordinates.
    
    Returns (net_amplitude, net_phase, dominant_chirality).
    Evaluated lazily on-demand: O(N_bounces), zero cost when unobserved.
    """
    st = stats(kernel)
    if not st["bounces"]:
        return (0.0, 0.0, 0)
        
    from xylarium.kernel import cosmos
    current_cycle = int(getattr(kernel, "cycle_count", 0))
    r_target = cosmos.from_centre_kpc(kernel, target_sector_id) or 8.0
    
    net_amp = 0.0
    net_phase = 0.0
    net_chirality = 0
    
    for b in st["bounces"]:
        dt = current_cycle - b["cycle"]
        if dt < 0:
            continue
            
        r_t = cosmos.from_centre_kpc(kernel, target_sector_id)
        r_o = cosmos.from_centre_kpc(kernel, b["sector"])
        if r_t is not None and r_o is not None:
            dist_kpc = abs(float(r_t) - float(r_o))
        else:
            # Fallback planar distance on sector graph
            dist_kpc = abs(target_sector_id - b["sector"]) * 0.1
            
        c_torsion = speed_of_torsion(kernel)
        gamma = damping_rate(kernel)
        prop_distance = dt * c_torsion
        
        # When evaluating locally at origin or when wave has reached target:
        if dist_kpc <= 0.05 or prop_distance >= dist_kpc:
            decay = math.exp(-gamma * dist_kpc) / max(0.5, dist_kpc if dist_kpc > 0.05 else 0.5)
            amp = b["energy"] * decay
            phase = (prop_distance - dist_kpc) * 2.0 * math.pi
            
            net_amp += amp
            net_phase += phase
            net_chirality += b["chirality"]
            
    # Include eternal cosmological background strain from ancient attenuated bounces
    net_amp += float(st.get("background_strain", 0.0))
    dominant_chirality = 1 if net_chirality >= 0 else -1
    return (net_amp, net_phase, dominant_chirality)


def orbital_secular_drift(kernel: Any, sector_id: int, q_initial: Fraction) -> Fraction:
    """Deterministic orbital semi-major axis perturbation a = q^2 from cumulative torsion flux.
    
    Exact rational calculation preserving standard laws: non-crossing and deterministic.
    Coupling is dynamically derived from alpha_G.
    """
    amp, phase, chirality = eval_wavefront(kernel, sector_id)
    if amp <= 1e-9:
        return q_initial
        
    epsilon = coupling_constant(kernel)
    # Rationalized perturbance factor
    # cos(phase) discretized via integer scale
    cos_scaled = int(math.cos(phase) * 1000)
    drift_factor = Fraction(cos_scaled, 1000) * epsilon * Fraction(int(min(amp, 100.0) * 100), 100)
    
    # Delta q is bounded and rational
    delta_q = q_initial * drift_factor
    return q_initial + delta_q


def compute_quasinormal_ringdown(
    kernel: Any,
    target_sector_id: int,
    spin_param_a: float = 0.7,
) -> Dict[str, Any]:
    """Compute Einstein-Cartan damped quasi-normal mode ringdown Psi(r, t).
    
    Singular bounces excite metric reverberation modes:
        Psi(r, t) = sum_n A_n * (exp(-omega_I * t) / r) * cos(omega_R * (t - r/c)) * U_chiral
    where frequency omega_R and damping omega_I are derived from Kerr-Cartan spin a_*.
    """
    st = stats(kernel)
    if not st.get("bounces"):
        return {
            "psi_amplitude": 0.0,
            "phase": 0.0,
            "omega_r": 0.0,
            "omega_i": 0.0,
            "chirality": 1,
            "reverberation_mode": "DORMANT",
        }
        
    current_cycle = int(getattr(kernel, "cycle_count", 0))
    a_star = max(0.0, min(0.99, spin_param_a))
    
    # QNM frequency and damping from Kerr-Cartan metric:
    # omega_R = omega_0 * (1 - 0.63 * (1 - a_*)^0.3)
    # omega_I = (omega_0 / 2) * (1 - a_*)^0.45
    omega_0 = 1.25
    omega_r = omega_0 * (1.0 - 0.63 * ((1.0 - a_star) ** 0.3))
    omega_i = (omega_0 * 0.5) * ((1.0 - a_star) ** 0.45)
    
    from xylarium.kernel import cosmos
    c_torsion = speed_of_torsion(kernel)
    
    total_psi = 0.0
    total_phase = 0.0
    net_chirality = 0
    
    for b in st["bounces"]:
        dt = max(0, current_cycle - b["cycle"])
        r_t = cosmos.from_centre_kpc(kernel, target_sector_id)
        r_o = cosmos.from_centre_kpc(kernel, b["sector"])
        dist_kpc = abs(float(r_t) - float(r_o)) if (r_t is not None and r_o is not None) else abs(target_sector_id - b["sector"]) * 0.1
        
        retarded_time = dt - (dist_kpc / max(0.01, c_torsion))
        if retarded_time >= 0:
            damping = math.exp(-omega_i * (dt * 0.1))
            geometric_decay = 1.0 / max(0.5, dist_kpc)
            oscillation = math.cos(omega_r * retarded_time * 0.2)
            
            mode_amp = b["energy"] * damping * geometric_decay * oscillation
            total_psi += mode_amp
            total_phase += omega_r * retarded_time
            net_chirality += b.get("chirality", 1)
            
    dominant_chirality = 1 if net_chirality >= 0 else -1
    return {
        "psi_amplitude": round(total_psi, 6),
        "phase": round(total_phase, 4),
        "omega_r": round(omega_r, 4),
        "omega_i": round(omega_i, 4),
        "chirality": dominant_chirality,
        "reverberation_mode": "ACTIVE_REVERBERATION" if abs(total_psi) > 1e-4 else "QUIESCENT",
    }



def cosmic_expansion_dynamics(kernel: Any) -> Dict[str, Any]:
    """Evaluate Friedmann-Cartan universal expansion driven by vacuum negative pressure and distributed bounces.
    
    In the presence of distributed singularity fermion spin repulsion, collapse halts at the Cartan
    density, and continuous bounce pulses drive outward conformal cosmological expansion:
        a_ddot / a = (8pi G / 3) * rho_vac - (4pi G / 3) * (rho_m + 3p/c^2) + kappa_torsion * <sigma^2>
    """
    st = stats(kernel)
    bounces = st.get("bounces", [])
    total_energy = sum(float(b.get("energy", 0.0)) for b in bounces)

    # Vacuum parameters
    rho_vac = 0.70
    p_vac = -rho_vac  # Negative vacuum pressure

    # Cumulative spin density from active wavefronts
    spin_density = total_energy * 0.001
    cartan_repulsion = min(10.0, spin_density * 1.5)

    # Universal expansion acceleration
    expansion_accel = (8.0 * math.pi / 3.0) * rho_vac + cartan_repulsion
    current_scale = float(st.get("universal_scale_factor", 1.0))
    new_scale = current_scale * (1.0 + expansion_accel * 0.001)
    st["universal_scale_factor"] = round(new_scale, 6)

    return {
        "bounces_count": len(bounces),
        "total_bounce_energy": round(total_energy, 4),
        "rho_vacuum": rho_vac,
        "p_vacuum": p_vac,
        "cartan_spin_density": round(spin_density, 6),
        "cartan_repulsion": round(cartan_repulsion, 6),
        "expansion_acceleration": round(expansion_accel, 6),
        "universal_scale_factor": round(new_scale, 6),
        "continuum_pulsing": len(bounces) > 0,
    }


def season(kernel: Any) -> List[str]:
    """Seasonal check: prune ancient attenuated bounces into the stochastic cosmological background strain."""
    st = stats(kernel)
    current_cycle = int(getattr(kernel, "cycle_count", 0))
    if len(st["bounces"]) > 50:
        excess = len(st["bounces"]) - 50
        pruned = st["bounces"][:excess]
        st["bounces"] = st["bounces"][excess:]
        bg = float(st.get("background_strain", 0.0))
        for b in pruned:
            bg += float(b.get("energy", 0.0)) * 0.0001
        st["background_strain"] = round(bg, 8)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {
        "bounces_recorded": len(st["bounces"]),
        "latest": st["bounces"][-1] if st["bounces"] else None,
        "universal_scale_factor": round(float(st.get("universal_scale_factor", 1.0)), 6),
    }


register_subsystem(Subsystem(
    name="torsion",
    state=lambda: {"bounces": []},
    season=season,
    summary=summary,
))
