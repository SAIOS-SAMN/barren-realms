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
    return state.of(kernel, "torsion")


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
            from xylarium.kernel import hypha, board
            ancients = board.ancient_peoples(kernel)
            house = ancients[0] if ancients else None
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


def season(kernel: Any) -> List[str]:
    """Seasonal check: prune ancient attenuated bounces beyond light cone horizons."""
    st = stats(kernel)
    current_cycle = int(getattr(kernel, "cycle_count", 0))
    # Keep last 50 significant bounces
    if len(st["bounces"]) > 50:
        st["bounces"] = st["bounces"][-50:]
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {
        "bounces_recorded": len(st["bounces"]),
        "latest": st["bounces"][-1] if st["bounces"] else None,
    }


register_subsystem(Subsystem(
    name="torsion",
    state=lambda: {"bounces": []},
    season=season,
    summary=summary,
))
