"""
Xylarium Workbench & In-Game Minigame Tuning Engine.

Provides deep, deterministic, first-principles interactive workbenches across 7 distinct domains:
1. Technology Workbench (Harmonic Resonance & Multi-Parameter Calibration)
2. Stock Markets Workbench (Synthetic Index Basket Construction, Leverage & ISSE Arbitrage)
3. FX Markets Workbench (Reserve Currency Basket Balancing & Peg Corridor Defense)
4. Diplomacies Workbench (SU(2) Epistemic Resonance & 5-Clause Treaty Tailoring)
5. Starcraft Workbench (Subsystem Power Grid Harmonics & Living Bio-Chitin Culturing)
6. Docks & Logistics Workbench (M/M/c Queueing Theory & Spaceport Turnaround Optimization)
7. Satellites & Constellations Workbench (Walker-Delta T/P/F Geometry & Orbital Payloads)

Each workbench features deterministic mathematical validation, technology capability gating,
and live simulation state integration.
"""

import math
import hashlib
from typing import Dict, List, Optional, Any, Tuple

from xylarium.kernel.models import (
    ActionResult,
    ActionType,
    Captain,
    Planet,
    Ship,
    CargoHold,
    CommodityType,
)
from xylarium.kernel.experience import ExperienceManager
from xylarium.config import (
    XP_WORKBENCH_TECH,
    XP_WORKBENCH_MARKET,
    XP_WORKBENCH_FX,
    XP_WORKBENCH_DIPLOMACY,
    XP_WORKBENCH_STARCRAFT,
    XP_WORKBENCH_DOCK,
    XP_WORKBENCH_SATELLITE,
)


def is_capability_unlocked(captain: Captain, capability: str, kernel: Any = None) -> bool:
    """
    Checks whether a captain has discovered or unlocked a specific technology capability.
    Supports captain technologies, colony technologies, kernel technology state, and rank gating.
    """
    cap_lower = capability.strip().lower()

    # 1. Direct captain technologies list
    if any(t.lower() == cap_lower for t in getattr(captain, "technologies", [])):
        return True

    # 2. Planetary colony technologies owned by captain
    if kernel and hasattr(kernel, "sectors"):
        for sec in kernel.sectors.values():
            for p in sec.planets:
                if p.owner_id == captain.id and any(t.lower() == cap_lower for t in getattr(p, "technologies", [])):
                    return True

    # 3. Kernel technology registry
    if kernel and "technology" in getattr(kernel, "state", {}):
        tech_state = kernel.state["technology"].get("of", {})
        if cap_lower in tech_state.get(captain.name, {}) or cap_lower in tech_state.get(captain.id, {}):
            return True

    # 4. Starting capabilities for rank >= 1 (radio and orbit are foundational spacefaring abilities)
    if captain.rank_tier >= 1 and cap_lower in ("radio", "orbit"):
        return True

    # 5. Unlocked secrets or permits
    if cap_lower.upper() in getattr(captain, "unlocked_secrets", []):
        return True

    return False


# -------------------------------------------------------------------------
# 1. TECHNOLOGIES WORKBENCH: Harmonic Resonance Calibration
# -------------------------------------------------------------------------

def calc_tech_resonance(capability: str, frequency: float, flux: float, efficiency: float) -> Dict[str, Any]:
    """
    Calculates deterministic harmonic resonance Q for a technology capability.
    Native resonance parameters (w*, phi*, eta*) are derived from the capability hash.
    """
    seed = int(hashlib.sha256(f"tech_res_{capability.lower()}".encode()).hexdigest(), 16)
    w_target = round(1.0 + (seed % 85) / 10.0, 2)
    phi_target = round(1.0 + ((seed >> 8) % 85) / 10.0, 2)
    eta_target = round(1.0 + ((seed >> 16) % 85) / 10.0, 2)

    sigma = 1.35
    dw = frequency - w_target
    dphi = flux - phi_target
    deta = efficiency - eta_target

    dist_sq = (dw ** 2) / (2.0 * sigma ** 2) + (dphi ** 2) / (2.0 * sigma ** 2) + (deta ** 2) / (2.0 * sigma ** 2)
    q_score = round(math.exp(-dist_sq), 4)

    grade = "DISSONANT"
    if q_score >= 0.95:
        grade = "PERFECT_HARMONIC"
    elif q_score >= 0.85:
        grade = "CONSTRUCTIVE_COHERENCE"
    elif q_score >= 0.70:
        grade = "STABLE_RESONANCE"

    perks: Dict[str, float] = {}
    cap_k = capability.lower()
    if cap_k == "fission":
        perks["reactor_output_bonus"] = round(0.30 * q_score, 3)
        perks["torch_fuel_economy"] = round(0.25 * q_score, 3)
    elif cap_k == "computation":
        perks["research_speed_bonus"] = round(0.35 * q_score, 3)
        perks["market_alpha_boost"] = round(0.20 * q_score, 3)
    elif cap_k == "networks":
        perks["fee_discount"] = round(0.30 * q_score, 3)
        perks["relay_bandwidth"] = round(0.40 * q_score, 3)
    elif cap_k == "genetics":
        perks["metabolic_efficiency"] = round(0.25 * q_score, 3)
        perks["cellular_regeneration"] = round(0.30 * q_score, 3)
    elif cap_k == "synthesis":
        perks["transmutation_yield"] = round(0.25 * q_score, 3)
        perks["refinery_speed"] = round(0.20 * q_score, 3)
    elif cap_k == "robotics":
        perks["dock_turnaround_bonus"] = round(0.30 * q_score, 3)
        perks["drone_repair_rate"] = round(0.25 * q_score, 3)
    elif cap_k == "orbit":
        perks["delta_v_efficiency"] = round(0.30 * q_score, 3)
    elif cap_k == "radio":
        perks["sensor_range_bonus"] = round(0.45 * q_score, 3)
    elif cap_k == "medicine":
        perks["crew_vitality"] = round(0.30 * q_score, 3)
    elif cap_k == "cyber":
        perks["firewall_defense"] = round(0.35 * q_score, 3)
    else:
        perks["generic_efficiency"] = round(0.20 * q_score, 3)

    return {
        "capability": capability,
        "frequency": frequency,
        "flux": flux,
        "efficiency": efficiency,
        "w_target": w_target,
        "phi_target": phi_target,
        "eta_target": eta_target,
        "delta_w": round(dw, 2),
        "delta_phi": round(dphi, 2),
        "delta_eta": round(deta, 2),
        "q_score": q_score,
        "grade": grade,
        "perks": perks,
        "is_locked": q_score >= 0.70,
    }


# -------------------------------------------------------------------------
# 2. STOCK MARKETS WORKBENCH: Index Basket Backtesting & Arbitrage
# -------------------------------------------------------------------------

DEFAULT_ASSET_PROFILES = {
    "ORE": {"mu": 0.20, "vol": 0.12},
    "ORGANICS": {"mu": 0.18, "vol": 0.10},
    "EQUIPMENT": {"mu": 0.28, "vol": 0.15},
    "EXOTICS": {"mu": 0.42, "vol": 0.22},
    "FE": {"mu": 0.19, "vol": 0.11},
    "TI": {"mu": 0.24, "vol": 0.13},
    "U": {"mu": 0.36, "vol": 0.18},
    "CRYOGENITE": {"mu": 0.45, "vol": 0.24},
    "STELALITH": {"mu": 0.48, "vol": 0.25},
}


def calc_market_index(
    basket: List[str],
    weights: List[float],
    leverage: float = 1.0,
    spread_threshold: float = 0.02,
    kernel: Any = None,
) -> Dict[str, Any]:
    """
    Backtests a synthetic ETF / arbitrage basket against interstellar market variance.
    Calculates expected return, portfolio variance, and Sharpe Ratio.
    """
    if not basket:
        basket = ["ORE", "ORGANICS", "EQUIPMENT", "EXOTICS"]
    if not weights or len(weights) != len(basket):
        weights = [1.0 / len(basket)] * len(basket)

    total_w = sum(weights)
    if total_w <= 0.0:
        weights = [1.0 / len(basket)] * len(basket)
    else:
        weights = [w / total_w for w in weights]

    leverage = max(1.0, min(3.0, float(leverage)))
    spread_threshold = max(0.005, min(0.10, float(spread_threshold)))

    # Fetch returns and volatilities
    mus: List[float] = []
    vols: List[float] = []
    for asset in basket:
        prof = DEFAULT_ASSET_PROFILES.get(asset.upper(), {"mu": 0.09, "vol": 0.15})
        mus.append(prof["mu"])
        vols.append(prof["vol"])

    # Portfolio expected return with leverage and execution spread friction
    mu_p = leverage * sum(w * mu for w, mu in zip(weights, mus)) - 0.4 * spread_threshold

    # Portfolio volatility with correlation matrix
    # Assets within same sector have rho ~ 0.35, distinct sectors rho ~ 0.15
    var_p = 0.0
    for i in range(len(basket)):
        for j in range(len(basket)):
            rho = 1.0 if i == j else 0.25
            cov_ij = rho * vols[i] * vols[j]
            var_p += weights[i] * weights[j] * cov_ij

    var_p = (leverage ** 2) * var_p + 0.004 * ((leverage - 1.0) ** 2)
    sigma_p = math.sqrt(max(0.001, var_p))

    risk_free = 0.02
    sharpe = round((mu_p - risk_free) / sigma_p, 2)

    is_listed = sharpe >= 1.20
    cycle_dividend = round(50 * max(0.0, sharpe) * leverage) if is_listed else 0
    trade_fee_rebate_pct = round(min(50.0, 15.0 * max(0.0, sharpe)), 1) if is_listed else 0.0

    return {
        "basket": basket,
        "weights": [round(w, 3) for w in weights],
        "leverage": leverage,
        "spread_threshold": spread_threshold,
        "expected_return": round(mu_p, 4),
        "volatility": round(sigma_p, 4),
        "sharpe_ratio": sharpe,
        "is_listed": is_listed,
        "cycle_dividend": cycle_dividend,
        "trade_fee_rebate_pct": trade_fee_rebate_pct,
    }


# -------------------------------------------------------------------------
# 3. FX MARKETS WORKBENCH: Reserve Corridor Defense & Carry Trade
# -------------------------------------------------------------------------

def calc_fx_corridor(
    anchor_currency: str = "SOL",
    peg_currency: str = "TERRA",
    corridor_min: float = 0.95,
    corridor_max: float = 1.05,
    reserve_allocation_pct: float = 0.30,
    kernel: Any = None,
) -> Dict[str, Any]:
    """
    Evaluates currency peg stability corridor and carry-trade interest yield.
    """
    corridor_min = float(corridor_min)
    corridor_max = float(corridor_max)
    if corridor_min >= corridor_max:
        corridor_max = corridor_min + 0.10

    reserve_allocation_pct = max(0.05, min(0.95, float(reserve_allocation_pct)))

    live_rate = 1.0
    if kernel and hasattr(kernel, "fx_market"):
        try:
            live_rate = float(kernel.fx_market.rate(peg_currency))
        except Exception:
            live_rate = 1.0

    target_mid = (corridor_min + corridor_max) / 2.0
    corridor_half_width = (corridor_max - corridor_min) / 2.0

    # Deviation beyond permitted band
    deviation = abs(live_rate - target_mid)
    breach = max(0.0, deviation - corridor_half_width)

    # Stability score [0.0, 1.0]
    p_stability = round(max(0.0, 1.0 - (breach / (corridor_half_width + 0.15))), 3)

    is_defended = p_stability >= 0.70
    daily_carry_yield = round(45.0 * p_stability * reserve_allocation_pct) if is_defended else 0

    return {
        "anchor_currency": anchor_currency,
        "peg_currency": peg_currency,
        "corridor_min": round(corridor_min, 4),
        "corridor_max": round(corridor_max, 4),
        "live_rate": round(live_rate, 4),
        "target_midpoint": round(target_mid, 4),
        "reserve_allocation_pct": reserve_allocation_pct,
        "stability_score": p_stability,
        "is_defended": is_defended,
        "daily_carry_yield": daily_carry_yield,
        "zero_conversion_fee": is_defended,
    }


# -------------------------------------------------------------------------
# 4. DIPLOMACIES WORKBENCH: SU(2) Epistemic Treaty Tailoring
# -------------------------------------------------------------------------

def calc_diplomatic_resonance(
    civ_name: str,
    tariff_reduction_pct: float,
    escort_wings: int,
    mining_concessions: str,
    scientific_exchange_pct: float,
    migration_quota: int,
    kernel: Any = None,
) -> Dict[str, Any]:
    """
    Evaluates SU(2) epistemic holonomy and mutual harmony of bilateral treaty clauses.
    """
    seed = int(hashlib.sha256(f"diplo_stance_{civ_name.lower()}".encode()).hexdigest(), 16)
    theta_0 = ((seed % 100) / 100.0) * math.pi
    phi_0 = (((seed >> 8) % 100) / 100.0) * math.pi
    psi_0 = (((seed >> 16) % 100) / 100.0) * math.pi

    # Player proposed angles mapped from clause concessions
    t_red = max(0.0, min(50.0, float(tariff_reduction_pct)))
    s_red = max(0.0, min(50.0, float(scientific_exchange_pct)))
    theta = ((t_red + s_red) / 100.0) * math.pi

    e_wings = max(0, min(5, int(escort_wings)))
    phi = (e_wings / 5.0) * math.pi

    conc_up = mining_concessions.strip().upper()
    if conc_up == "SHARED":
        psi = 0.50 * math.pi
    elif conc_up == "EXCLUSIVE":
        psi = 0.15 * math.pi
    else:  # RESERVED
        psi = 0.85 * math.pi

    # SU(2) Trace Overlap: chi = 0.5 * |Tr(U_A * U_B_dagger)|
    # Tr = 2 * (cos(theta)*cos(theta_0)*cos(phi - phi_0) + sin(theta)*sin(theta_0)*cos(psi - psi_0))
    cos_val = math.cos(theta) * math.cos(theta_0) * math.cos(phi - phi_0)
    sin_val = math.sin(theta) * math.sin(theta_0) * math.cos(psi - psi_0)
    chi = abs(cos_val + sin_val)

    # Equitable treaty harmony bonus
    equity = 0.10 * (1.0 - abs(t_red - 25.0) / 25.0) + 0.10 * (1.0 - abs(s_red - 25.0) / 25.0)
    chi_total = round(min(1.0, max(0.0, chi + equity)), 3)

    is_ratified = chi_total >= 0.65

    return {
        "civ_name": civ_name,
        "tariff_reduction_pct": t_red,
        "escort_wings": e_wings,
        "mining_concessions": conc_up,
        "scientific_exchange_pct": s_red,
        "migration_quota": max(0, min(500, int(migration_quota))),
        "su2_resonance": chi_total,
        "is_ratified": is_ratified,
        "perks": {
            "non_aggression_pact": is_ratified,
            "port_tariff_discount": t_red if is_ratified else 0.0,
            "science_sharing_xp_bonus": round(0.25 * chi_total, 2) if is_ratified else 0.0,
        },
    }


# -------------------------------------------------------------------------
# 5. STARCRAFT WORKBENCH: Subsystem Power Harmonics & Living Hull
# -------------------------------------------------------------------------

def calc_starcraft_tuning(
    weapons_pct: float,
    kinetic_pct: float,
    shields_pct: float,
    drives_pct: float,
    living_material: Optional[str] = None,
    captain: Optional[Captain] = None,
) -> Dict[str, Any]:
    """
    Harmonizes starship power grid subsystems and cultures living bio-chitin hull.
    Power percentages must sum to 100%.
    """
    total_power = weapons_pct + kinetic_pct + shields_pct + drives_pct
    is_balanced = abs(total_power - 100.0) <= 1.0

    # Grid harmonic resonance factor
    # Optimal distribution achieves harmonic constructive interference H ~ 1.15 to 1.30
    h_harmonic = 1.0 + 0.20 * math.sin(math.pi * shields_pct / 50.0) * math.cos(math.pi * (drives_pct - weapons_pct) / 100.0)
    h_harmonic = round(max(0.70, min(1.35, h_harmonic)), 3)

    living_active = False
    living_bonus: Dict[str, Any] = {}
    if living_material:
        mat_up = living_material.strip().upper()
        if mat_up in ("BIO_CHITIN", "EXTREMOPHILE_POLYMER", "XENOPROTEIN", "CHITINIUM"):
            living_active = True
            living_bonus = {
                "material": mat_up,
                "passive_shield_regen_per_cycle": 15,
                "combat_damage_mitigation_pct": 25.0,
                "speed_thrust_bonus_pct": 15.0,
            }

    return {
        "weapons_pct": weapons_pct,
        "kinetic_pct": kinetic_pct,
        "shields_pct": shields_pct,
        "drives_pct": drives_pct,
        "total_power": round(total_power, 1),
        "is_balanced": is_balanced,
        "harmonic_factor": h_harmonic,
        "living_hull_active": living_active,
        "living_hull_perks": living_bonus,
    }


# -------------------------------------------------------------------------
# 6. DOCKS & LOGISTICS WORKBENCH: M/M/c Spaceport Turnaround
# -------------------------------------------------------------------------

def calc_dock_logistics(
    planet: Planet,
    crane_automation_berths: int = 3,
    fuel_hydrant_throughput: float = 30.0,
    docking_fee_rate: int = 50,
    express_lane: bool = False,
) -> Dict[str, Any]:
    """
    Simulates spaceport turnaround dynamics using M/M/c queueing theory.
    """
    c = max(1, min(8, int(crane_automation_berths)))
    fuel_rate = max(10.0, min(100.0, float(fuel_hydrant_throughput)))
    fee = max(10, min(500, int(docking_fee_rate)))

    # Service rate per berth mu
    mu = 0.45 * (1.0 + fuel_rate / 60.0)

    # Arrival rate lambda derived from spaceport flight scheduling (logarithmic scaling with population)
    pop_raw = max(10, getattr(planet, "population", 500))
    lam = round(1.0 + 0.5 * math.log(1.0 + pop_raw / 5000.0) + (0.3 if express_lane else 0.0), 2)

    # Traffic intensity rho = lambda / (c * mu)
    rho = lam / (c * mu)

    is_stable = rho < 0.92
    if is_stable:
        # Approximate average waiting time in queue Wq
        wq = round((rho ** c) / (max(0.01, 1.0 - rho) * c * mu), 2)
        turnaround_efficiency = round(max(0.15, min(1.0, 1.0 - (wq / 10.0))), 3)
    else:
        wq = 99.9
        turnaround_efficiency = 0.05

    # Cycle revenue generated from docking fees and port turnover
    port_revenue_per_cycle = round(30 * c * turnaround_efficiency * (fee / 50.0)) if is_stable else 0

    return {
        "planet_id": planet.id,
        "planet_name": planet.name,
        "berths": c,
        "fuel_hydrant_throughput": fuel_rate,
        "docking_fee_rate": fee,
        "express_lane": express_lane,
        "arrival_rate_lambda": lam,
        "service_rate_mu": round(mu, 3),
        "traffic_intensity_rho": round(rho, 3),
        "is_stable": is_stable,
        "queue_wait_time_hours": wq,
        "turnaround_efficiency": turnaround_efficiency,
        "port_revenue_per_cycle": port_revenue_per_cycle,
        "zero_demurrage_hauler_perk": is_stable,
    }


# -------------------------------------------------------------------------
# 7. SATELLITES WORKBENCH: Walker-Delta Constellation Geometry
# -------------------------------------------------------------------------

def calc_satellite_constellation(
    planet: Planet,
    payload_type: str = "RELAY",
    total_satellites: int = 24,
    orbital_planes: int = 4,
    phase_factor: int = 1,
    altitude_km: float = 1200.0,
) -> Dict[str, Any]:
    """
    Computes Walker-Delta (T/P/F) constellation orbital coverage and payload perks.
    """
    t = max(3, min(60, int(total_satellites)))
    p = max(1, min(12, int(orbital_planes)))

    # Satellite planes must evenly divide total satellites
    if t % p != 0:
        # Adjust total satellites to nearest multiple
        t = (t // p) * p
        if t < p:
            t = p

    f = max(0, min(p - 1, int(phase_factor)))
    h = max(300.0, min(20000.0, float(altitude_km)))
    r_planet = 6371.0  # standard celestial radius

    # Minimum elevation angle = 10 degrees = 0.1745 rad
    min_elev = 0.1745
    cos_theta = (r_planet / (r_planet + h)) * math.cos(min_elev)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    theta_cov = max(0.01, math.acos(cos_theta) - min_elev)

    # Footprint fractional surface area
    f1 = (1.0 - math.cos(theta_cov)) / 2.0

    # Phasing dispersion geometry factor
    eta_geom = 1.0 - 0.20 * (abs(f - (p / 2.0)) / (p + 1.0))

    # Global multi-satellite geometric coverage C in [0.0, 1.0] with multi-plane dispersion
    coverage = round(min(1.0, max(0.0, 1.0 - math.pow(max(0.001, 1.0 - f1), t * 2.0 * eta_geom))), 3)

    is_operational = coverage >= 0.75
    payload_up = payload_type.strip().upper()

    perks: Dict[str, Any] = {}
    if payload_up == "RELAY":
        perks["comms_bandwidth_boost_pct"] = round(35.0 * coverage, 1)
        perks["zero_comms_blackout"] = is_operational
    elif payload_up == "SCANNER":
        perks["ore_detection_range_bonus_pct"] = round(40.0 * coverage, 1)
        perks["pirate_ambush_warning"] = is_operational
    elif payload_up == "DEFENSE":
        perks["orbital_kinetic_barrier_shields"] = round(120.0 * coverage)
        perks["auto_intercept_invaders"] = is_operational
    elif payload_up == "GEOENGINEERING":
        perks["terraforming_rate_bonus_pct"] = round(30.0 * coverage, 1)
        perks["climate_temperature_stabilization"] = is_operational

    return {
        "planet_id": planet.id,
        "planet_name": planet.name,
        "payload_type": payload_up,
        "total_satellites": t,
        "orbital_planes": p,
        "sats_per_plane": t // p,
        "phase_factor": f,
        "altitude_km": h,
        "surface_coverage": coverage,
        "is_operational": is_operational,
        "perks": perks,
    }


# -------------------------------------------------------------------------
# MASTER WORKBENCH MANAGER
# -------------------------------------------------------------------------

class WorkbenchManager:
    """
    Central coordinator for all in-game interactive workbenches and minigames.
    Ensures capability unlocking, executes tuning calculations, updates state,
    and advances passive cyclical yields during world simulation ticks.
    """

    def tune_technology(
        self,
        captain: Captain,
        capability: str,
        frequency: float,
        flux: float,
        efficiency: float,
        kernel: Any = None,
    ) -> ActionResult:
        """Harmonic resonance calibration minigame for technology capabilities."""
        cap_clean = capability.strip().lower()
        if not is_capability_unlocked(captain, cap_clean, kernel):
            return ActionResult(
                False,
                ActionType.WORKBENCH_TECH_TUNE,
                f"Capability '{capability}' has not been discovered or unlocked yet.",
            )

        res = calc_tech_resonance(cap_clean, float(frequency), float(flux), float(efficiency))
        captain.workbenches.setdefault("technologies", {})[cap_clean] = res

        if res["is_locked"]:
            ExperienceManager.award(captain, "science", XP_WORKBENCH_TECH, kernel, key=f"tech_tune:{cap_clean}")
            msg = (
                f"HARMONIC RESONANCE LOCKED: {capability.upper()} calibrated at Q={res['q_score']:.1%} [{res['grade']}]. "
                f"Active perks enabled: {list(res['perks'].keys())}."
            )
            return ActionResult(True, ActionType.WORKBENCH_TECH_TUNE, msg, data=res)
        else:
            msg = (
                f"HARMONIC DISSONANCE: Q={res['q_score']:.1%} is below operational threshold (70.0%). "
                f"Offsets: dw={res['delta_w']:+.1f}, dphi={res['delta_phi']:+.1f}, deta={res['delta_eta']:+.1f}."
            )
            return ActionResult(False, ActionType.WORKBENCH_TECH_TUNE, msg, data=res)

    def tune_market_index(
        self,
        captain: Captain,
        index_name: str,
        basket: List[str],
        weights: List[float],
        leverage: float = 1.0,
        spread_threshold: float = 0.02,
        kernel: Any = None,
    ) -> ActionResult:
        """Algorithmic index basket construction & Sharpe ratio backtest minigame."""
        if not (is_capability_unlocked(captain, "computation", kernel) or is_capability_unlocked(captain, "networks", kernel)):
            return ActionResult(
                False,
                ActionType.WORKBENCH_MARKET_TUNE,
                "Requires COMPUTATION or NETWORKS capability to design algorithmic market indices.",
            )

        res = calc_market_index(basket, weights, leverage, spread_threshold, kernel)
        captain.workbenches.setdefault("market_indices", {})[index_name] = res

        if res["is_listed"]:
            ExperienceManager.award(captain, "market", XP_WORKBENCH_MARKET, kernel, key=f"market_tune:{index_name}")
            msg = (
                f"ISSE ETF LISTING APPROVED: Index '{index_name}' achieved Sharpe Ratio {res['sharpe_ratio']:.2f} "
                f"(Return: {res['expected_return']:.1%}, Vol: {res['volatility']:.1%}). "
                f"Dividend yield: +{res['cycle_dividend']} Cr/cycle, Trade fee rebate: -{res['trade_fee_rebate_pct']}%."
            )
            return ActionResult(True, ActionType.WORKBENCH_MARKET_TUNE, msg, data=res)
        else:
            msg = (
                f"INDEX REJECTED: Sharpe Ratio {res['sharpe_ratio']:.2f} failed to meet ISSE threshold (1.20). "
                f"Excess volatility or leverage friction detected."
            )
            return ActionResult(False, ActionType.WORKBENCH_MARKET_TUNE, msg, data=res)

    def tune_fx_reserves(
        self,
        captain: Captain,
        anchor_currency: str = "SOL",
        peg_currency: str = "TERRA",
        corridor_min: float = 0.95,
        corridor_max: float = 1.05,
        reserve_allocation_pct: float = 0.30,
        kernel: Any = None,
    ) -> ActionResult:
        """Reserve currency basket balancing and peg corridor defense minigame."""
        if not (is_capability_unlocked(captain, "networks", kernel) or len(getattr(captain, "fx_wallet", {})) >= 2):
            return ActionResult(
                False,
                ActionType.WORKBENCH_FX_TUNE,
                "Requires NETWORKS capability or active multi-currency FX wallet to manage currency pegs.",
            )

        res = calc_fx_corridor(anchor_currency, peg_currency, corridor_min, corridor_max, reserve_allocation_pct, kernel)
        pair_key = f"{anchor_currency}_{peg_currency}"
        captain.workbenches.setdefault("fx_pegs", {})[pair_key] = res

        if res["is_defended"]:
            ExperienceManager.award(captain, "market", XP_WORKBENCH_FX, kernel, key=f"fx_tune:{pair_key}")
            msg = (
                f"PEG CORRIDOR DEFENDED: {anchor_currency}/{peg_currency} corridor [{corridor_min:.2f}-{corridor_max:.2f}] "
                f"secured with stability {res['stability_score']:.1%}. "
                f"Carry return: +{res['daily_carry_yield']} {peg_currency}/cycle, 0% conversion fees activated."
            )
            return ActionResult(True, ActionType.WORKBENCH_FX_TUNE, msg, data=res)
        else:
            msg = (
                f"CORRIDOR BREACH: Stability score {res['stability_score']:.1%} fell below minimum (70.0%). "
                f"Exchange rate {res['live_rate']:.3f} diverged past corridor bounds."
            )
            return ActionResult(False, ActionType.WORKBENCH_FX_TUNE, msg, data=res)

    def tune_diplomatic_treaty(
        self,
        captain: Captain,
        civ_name: str,
        tariff_reduction_pct: float = 20.0,
        escort_wings: int = 2,
        mining_concessions: str = "SHARED",
        scientific_exchange_pct: float = 25.0,
        migration_quota: int = 100,
        kernel: Any = None,
    ) -> ActionResult:
        """SU(2) epistemic resonance alignment and bilateral treaty tailoring minigame."""
        if not (is_capability_unlocked(captain, "radio", kernel) or is_capability_unlocked(captain, "networks", kernel)):
            return ActionResult(
                False,
                ActionType.WORKBENCH_DIPLOMACY_TUNE,
                "Requires RADIO or NETWORKS capability to negotiate sovereign interstellar treaties.",
            )

        res = calc_diplomatic_resonance(
            civ_name, tariff_reduction_pct, escort_wings, mining_concessions, scientific_exchange_pct, migration_quota, kernel
        )
        captain.workbenches.setdefault("diplomacy_treaties", {})[civ_name] = res

        if res["is_ratified"]:
            ExperienceManager.award(captain, "governance", XP_WORKBENCH_DIPLOMACY, kernel, key=f"diplo_tune:{civ_name}")
            msg = (
                f"DIPLOMATIC CONCORD RATIFIED: SU(2) Epistemic resonance with {civ_name} achieved {res['su2_resonance']:.1%}. "
                f"Non-aggression pact enacted, port tariffs -{res['tariff_reduction_pct']}%, science exchange active."
            )
            return ActionResult(True, ActionType.WORKBENCH_DIPLOMACY_TUNE, msg, data=res)
        else:
            msg = (
                f"TREATY REJECTED: Epistemic trace overlap {res['su2_resonance']:.1%} did not reach consensus threshold (65.0%). "
                f"Clause concessions failed to achieve ideological alignment."
            )
            return ActionResult(False, ActionType.WORKBENCH_DIPLOMACY_TUNE, msg, data=res)

    def tune_starcraft(
        self,
        captain: Captain,
        weapons_pct: float = 25.0,
        kinetic_pct: float = 25.0,
        shields_pct: float = 25.0,
        drives_pct: float = 25.0,
        living_material: Optional[str] = None,
        kernel: Any = None,
    ) -> ActionResult:
        """Starship subsystem power grid harmonization and living bio-chitin culturing."""
        if not (is_capability_unlocked(captain, "orbit", kernel) or captain.rank_tier >= 1):
            return ActionResult(
                False,
                ActionType.WORKBENCH_STARCRAFT_TUNE,
                "Requires ORBIT capability or Rank Tier >= 1 to tune starcraft power grids.",
            )

        # Handle biomaterial consumption for living hull culturing
        consumed_mat = False
        if living_material:
            mat_up = living_material.strip().upper()
            cargo = getattr(captain.ship, "cargo", None)
            if cargo and cargo.held(mat_up) >= 1:
                if mat_up in getattr(cargo, "elements", {}):
                    cargo.elements[mat_up] -= 1
                    if cargo.elements[mat_up] <= 0:
                        del cargo.elements[mat_up]
                elif hasattr(cargo, mat_up.lower()):
                    setattr(cargo, mat_up.lower(), getattr(cargo, mat_up.lower()) - 1)
                consumed_mat = True
            elif not consumed_mat:
                living_material = None  # cannot culture without required sample in cargo

        res = calc_starcraft_tuning(weapons_pct, kinetic_pct, shields_pct, drives_pct, living_material, captain)
        if not res["is_balanced"]:
            return ActionResult(
                False,
                ActionType.WORKBENCH_STARCRAFT_TUNE,
                f"Power distribution must total 100% (currently {res['total_power']:.1f}%).",
                data=res,
            )

        captain.workbenches["starcraft"] = res

        # Apply starship upgrades directly
        if res["harmonic_factor"] > 1.0:
            extra_shields = int(20 * (res["harmonic_factor"] - 1.0))
            captain.ship.max_shields += extra_shields
            captain.ship.shields = min(captain.ship.max_shields, captain.ship.shields + extra_shields)

        ExperienceManager.award(captain, "industry", XP_WORKBENCH_STARCRAFT, kernel, key=f"starcraft_tune:{captain.ship.ship_type}")
        msg = (
            f"STARCRAFT GRID HARMONIZED: Power balanced at {res['harmonic_factor']:.2f}x efficiency. "
            f"W:{weapons_pct:.0f}% K:{kinetic_pct:.0f}% S:{shields_pct:.0f}% D:{drives_pct:.0f}%."
        )
        if res["living_hull_active"]:
            msg += f" Living Hull cultured using {res['living_hull_perks']['material']} (+15 regen/cycle, -25% damage taken)."

        return ActionResult(True, ActionType.WORKBENCH_STARCRAFT_TUNE, msg, data=res)

    def tune_dock_logistics(
        self,
        captain: Captain,
        planet_id: Optional[str] = None,
        crane_automation_berths: int = 3,
        fuel_hydrant_throughput: float = 30.0,
        docking_fee_rate: int = 50,
        express_lane: bool = False,
        kernel: Any = None,
    ) -> ActionResult:
        """Spaceport berth allocation and M/M/c queueing turnaround optimization."""
        if not (is_capability_unlocked(captain, "orbit", kernel) or is_capability_unlocked(captain, "fission", kernel)):
            return ActionResult(
                False,
                ActionType.WORKBENCH_DOCK_TUNE,
                "Requires ORBIT or FISSION capability to optimize orbital dock logistics.",
            )

        planet = None
        if planet_id and kernel:
            planet = kernel.get_planet(planet_id)
        if not planet and kernel:
            sec = kernel.sectors.get(captain.sector_id)
            if sec and sec.planets:
                planet = sec.planets[0]

        if not planet:
            return ActionResult(False, ActionType.WORKBENCH_DOCK_TUNE, "No planet celestial body found to tune dock logistics.")

        res = calc_dock_logistics(planet, crane_automation_berths, fuel_hydrant_throughput, docking_fee_rate, express_lane)
        planet.society.setdefault("workbenches", {})["dock_logistics"] = res
        captain.workbenches.setdefault("dock_logistics", {})[planet.id] = res

        if res["is_stable"]:
            ExperienceManager.award(captain, "industry", XP_WORKBENCH_DOCK, kernel, key=f"dock_tune:{planet.id}")
            msg = (
                f"SPACEPORT LOGISTICS OPTIMIZED: {planet.name} dock queue stable (Traffic Intensity rho={res['traffic_intensity_rho']:.2f}). "
                f"Avg wait: {res['queue_wait_time_hours']:.1f} hrs, Port throughput yield: +{res['port_revenue_per_cycle']} Cr/cycle. "
                f"Hauler demurrage eliminated."
            )
            return ActionResult(True, ActionType.WORKBENCH_DOCK_TUNE, msg, data=res)
        else:
            msg = (
                f"SPACEPORT CONGESTION: Berth capacity exceeded (rho={res['traffic_intensity_rho']:.2f} >= 0.92). "
                f"Severe docking delays detected. Add crane automation berths or upgrade fuel hydrants."
            )
            return ActionResult(False, ActionType.WORKBENCH_DOCK_TUNE, msg, data=res)

    def tune_satellite_constellation(
        self,
        captain: Captain,
        planet_id: Optional[str] = None,
        payload_type: str = "RELAY",
        total_satellites: int = 24,
        orbital_planes: int = 4,
        phase_factor: int = 1,
        altitude_km: float = 1200.0,
        kernel: Any = None,
    ) -> ActionResult:
        """Walker-Delta constellation deployment and orbital payload tuning."""
        if not (is_capability_unlocked(captain, "orbit", kernel) or is_capability_unlocked(captain, "radio", kernel)):
            return ActionResult(
                False,
                ActionType.WORKBENCH_SATELLITE_TUNE,
                "Requires ORBIT or RADIO capability to configure orbital satellite constellations.",
            )

        planet = None
        if planet_id and kernel:
            planet = kernel.get_planet(planet_id)
        if not planet and kernel:
            sec = kernel.sectors.get(captain.sector_id)
            if sec and sec.planets:
                planet = sec.planets[0]

        if not planet:
            return ActionResult(False, ActionType.WORKBENCH_SATELLITE_TUNE, "No celestial body found to deploy constellation around.")

        res = calc_satellite_constellation(planet, payload_type, total_satellites, orbital_planes, phase_factor, altitude_km)
        planet.society.setdefault("workbenches", {}).setdefault("constellations", {})[res["payload_type"]] = res
        captain.workbenches.setdefault("constellations", {})[f"{planet.id}_{res['payload_type']}"] = res

        if res["is_operational"]:
            # Apply defense shields if DEFENSE payload
            if res["payload_type"] == "DEFENSE":
                shield_add = int(res["perks"].get("orbital_kinetic_barrier_shields", 100))
                planet.max_shields += shield_add
                planet.shields = min(planet.max_shields, planet.shields + shield_add)

            ExperienceManager.award(captain, "science", XP_WORKBENCH_SATELLITE, kernel, key=f"satellite_tune:{planet.id}:{res['payload_type']}")
            msg = (
                f"WALKER-DELTA CONSTELLATION DEPLOYED: {res['total_satellites']}/{res['orbital_planes']}/{res['phase_factor']} "
                f"at {res['altitude_km']:.0f} km achieved {res['surface_coverage']:.1%} global surface coverage. "
                f"Payload '{res['payload_type']}' active: {list(res['perks'].keys())}."
            )
            return ActionResult(True, ActionType.WORKBENCH_SATELLITE_TUNE, msg, data=res)
        else:
            msg = (
                f"CONSTELLATION BLIND SPOTS: Surface coverage {res['surface_coverage']:.1%} below operational threshold (75.0%). "
                f"Increase satellite count or optimize plane phasing."
            )
            return ActionResult(False, ActionType.WORKBENCH_SATELLITE_TUNE, msg, data=res)

    def tick(self, kernel: Any) -> None:
        """
        Advances cyclical production dividends, carry trade returns, living hull repairs,
        and logistics revenues across active tuned workbenches.
        """
        # 1. Captain-level cyclical rewards
        for captain in getattr(kernel, "captains", {}).values():
            wb = getattr(captain, "workbenches", {})
            if not wb:
                continue

            # A. Stock index management dividends
            for idx_data in wb.get("market_indices", {}).values():
                if idx_data.get("is_listed") and idx_data.get("cycle_dividend", 0) > 0:
                    captain.credits += idx_data["cycle_dividend"]

            # B. FX carry-trade interest yields
            for fx_data in wb.get("fx_pegs", {}).values():
                if fx_data.get("is_defended") and fx_data.get("daily_carry_yield", 0) > 0:
                    peg = fx_data.get("peg_currency", "TERRA")
                    captain.fx_wallet[peg] = captain.fx_wallet.get(peg, 0) + fx_data["daily_carry_yield"]

            # C. Living bio-chitin hull self-repair
            sc = wb.get("starcraft", {})
            if sc.get("living_hull_active") and getattr(captain, "ship", None):
                regen = sc.get("living_hull_perks", {}).get("passive_shield_regen_per_cycle", 15)
                captain.ship.shields = min(captain.ship.max_shields, captain.ship.shields + regen)

        # 2. Planetary spaceport logistics & constellation perks
        for sec in getattr(kernel, "sectors", {}).values():
            for p in getattr(sec, "planets", []):
                soc_wb = p.society.get("workbenches", {})
                if not soc_wb:
                    continue

                # Dock logistics revenues
                dock_data = soc_wb.get("dock_logistics")
                if dock_data and dock_data.get("is_stable") and dock_data.get("port_revenue_per_cycle", 0) > 0:
                    rev = dock_data["port_revenue_per_cycle"]
                    p.treasury += rev
                    # If owned by a captain, also credit dividends to owner
                    if p.owner_id and p.owner_id in kernel.captains:
                        kernel.captains[p.owner_id].credits += rev // 2

                # Satellite defense shield maintenance
                consts = soc_wb.get("constellations", {})
                if "DEFENSE" in consts and consts["DEFENSE"].get("is_operational"):
                    if p.shields < p.max_shields:
                        p.shields = min(p.max_shields, p.shields + 10)

    def get_view(self, captain: Captain, kernel: Any = None) -> Dict[str, Any]:
        """Provides a complete snapshot of all 7 workbenches and tuning statuses for client UI."""
        unlocked_caps = []
        for cap in ("radio", "orbit", "fission", "computation", "networks", "cyber", "medicine", "genetics", "synthesis", "robotics"):
            if is_capability_unlocked(captain, cap, kernel):
                unlocked_caps.append(cap)

        return {
            "unlocked_capabilities": unlocked_caps,
            "captain_workbenches": dict(getattr(captain, "workbenches", {})),
            "can_tune_tech": len(unlocked_caps) > 0,
            "can_tune_market": is_capability_unlocked(captain, "computation", kernel) or is_capability_unlocked(captain, "networks", kernel),
            "can_tune_fx": is_capability_unlocked(captain, "networks", kernel) or len(getattr(captain, "fx_wallet", {})) >= 2,
            "can_tune_diplomacy": is_capability_unlocked(captain, "radio", kernel) or is_capability_unlocked(captain, "networks", kernel),
            "can_tune_starcraft": is_capability_unlocked(captain, "orbit", kernel) or captain.rank_tier >= 1,
            "can_tune_dock": is_capability_unlocked(captain, "orbit", kernel) or is_capability_unlocked(captain, "fission", kernel),
            "can_tune_satellite": is_capability_unlocked(captain, "orbit", kernel) or is_capability_unlocked(captain, "radio", kernel),
        }
