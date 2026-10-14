"""
xylarium.kernel.epistemics: Civilizational Epistemic Ontologies & Cognitive Interiority.

Models how civilizations understand the four cosmic pillars and economics:
1. Cosmology & Physics: Newtonian flat space vs. Einstein-Cartan metric torsion vs. S^60/S^360 hyperspheres.
2. Chemistry & Nucleosynthesis: Empirical corporeal vs. Weizsäcker SEMF vs. Torsion wavefront induction.
3. Biology & Evolution: Fixed essences vs. Waddington morphospace landscapes vs. Transsomatic cosmic engineering.
4. Economics & Trade: Barter mercantile vs. Relativistic Navier-Stokes fluids vs. Mayer-Vietoris homological synthesis.
5. Cognitive Worldview Manifold: SU(2) unit quaternion belief orientation and inter-civilizational epistemic resonance.

Empowers civilizations to autonomously pursue alchemical transmutation, steer epigenetic adaptation,
and optimize high-dimensional transit based on their subjective model of reality.
"""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.physics import Quaternion


# ==============================================================================
# PARADIGM DEFINITIONS & PROGRESSIONS
# ==============================================================================

COSMOLOGY_PARADIGMS = [
    "NEWTONIAN_FLAT",          # Flat R^3 space, 1/r^2 Newtonian mechanics, unaware of torsion or metric curvature
    "EINSTEIN_CARTAN_RESONANT", # Spacetime torsion Psi != 0, spin-density repulsion, non-singular bounce mechanics
    "HYPERSPHERICAL_S360",     # S^60 compactification, S^360 super-universe, gravitational cone waveguides, caustics
]

CHEMISTRY_PARADIGMS = [
    "EMPIRICAL_CORPOREAL",     # Classical periodic elements (Z <= 82); superheavies dismissed as impossible
    "WEIZSACKER_SEMF",         # Semi-empirical mass formula, nuclear binding energies, Island of Stability magic shells
    "TORSION_INDUCTION",       # High-energy catalytic nucleosynthesis coupled to metric torsion phase resonance (Z >= 119)
]

BIOLOGY_PARADIGMS = [
    "FIXED_ESSENCE",           # Species traits believed immutable; epigenetic drift viewed as degeneration
    "WADDINGTON_ADAPTIVE",     # Continuous morphospace, potential landscapes, active Langevin basin drift
    "TRANSSOMATIC_COSMIC",     # Cross-sector dimensional shear resilience, trans-metabolic cellular stability
]

ECONOMICS_PARADIGMS = [
    "BARTER_MERCANTILE",       # Static local supply/demand; unaware of gravitational time lapse or geodesic tensors
    "RELATIVISTIC_FLUID",      # Navier-Stokes commodity flux J, metric lapse (1+z), trade stress-energy tensor T^munu
    "HOMOLOGICAL_SYNTHESIS",   # Multi-sector tensor routing along Mayer-Vietoris cohomology chains across S^360
]


# ==============================================================================
# EPISTEMIC ONTOLOGY DATA STRUCTURE
# ==============================================================================

@dataclass
class EpistemicOntology:
    """
    The internal epistemic model held by a civilization.
    Represents how the civilization comprehends the universe's physical, chemical, biological,
    and economic laws, and contains its overarching cognitive worldview quaternion Q in SU(2).
    """
    cosmology: str = "NEWTONIAN_FLAT"
    chemistry: str = "EMPIRICAL_CORPOREAL"
    biology: str = "FIXED_ESSENCE"
    economics: str = "BARTER_MERCANTILE"
    worldview_q: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    comprehension: Dict[str, float] = field(default_factory=lambda: {
        "physics": 0.10,
        "chemistry": 0.10,
        "biology": 0.10,
        "economics": 0.10,
    })
    theorems_discovered: List[str] = field(default_factory=list)
    breakthrough_count: int = 0
    paradigm_progress: Dict[str, float] = field(default_factory=lambda: {
        "physics": 0.0,
        "chemistry": 0.0,
        "biology": 0.0,
        "economics": 0.0,
    })

    def quaternion(self) -> Quaternion:
        """Returns the worldview orientation as an SU(2) unit quaternion."""
        if isinstance(self.worldview_q, Quaternion):
            return self.worldview_q.normalized() if self.worldview_q.norm() > 1e-12 else Quaternion(1.0, 0.0, 0.0, 0.0)
        w, x, y, z = self.worldview_q
        q = Quaternion(w, x, y, z)
        norm = q.norm()
        return q.normalized() if norm > 1e-12 else Quaternion(1.0, 0.0, 0.0, 0.0)

    def set_quaternion(self, q: Quaternion) -> None:
        """Sets the worldview orientation from a Quaternion."""
        qn = q.normalized()
        self.worldview_q = (round(qn.w, 6), round(qn.x, 6), round(qn.y, 6), round(qn.z, 6))

    def resonance_with(self, other: "EpistemicOntology") -> float:
        """
        Calculates the Epistemic Resonance (trace of relative SU(2) holonomy) between two civilizations:
        I(Q_A, Q_B) = 1/2 Tr(Q_A^dagger Q_B) = cos(theta_relative / 2) in [-1.0, 1.0].
        Values near +1.0 indicate deep ontological alignment; values near -1.0 indicate severe ideological polarization.
        """
        qa = self.quaternion()
        qb = other.quaternion()
        # Q_rel = Q_A^dagger * Q_B
        q_rel = qa.conjugate() * qb
        # 1/2 Tr(Q_rel) is simply the scalar component w of the unit quaternion
        return max(-1.0, min(1.0, q_rel.w))

    def collective_intelligence_index(self) -> float:
        """
        Computes the civilization's overall Epistemic Intelligence Index (0.0 to 1.0)
        based on comprehension levels and paradigm depths.
        """
        c_depth = COSMOLOGY_PARADIGMS.index(self.cosmology) / (len(COSMOLOGY_PARADIGMS) - 1)
        k_depth = CHEMISTRY_PARADIGMS.index(self.chemistry) / (len(CHEMISTRY_PARADIGMS) - 1)
        b_depth = BIOLOGY_PARADIGMS.index(self.biology) / (len(BIOLOGY_PARADIGMS) - 1)
        e_depth = ECONOMICS_PARADIGMS.index(self.economics) / (len(ECONOMICS_PARADIGMS) - 1)

        avg_comp = sum(self.comprehension.values()) / max(1, len(self.comprehension))
        avg_depth = (c_depth + k_depth + b_depth + e_depth) / 4.0
        return round(0.4 * avg_comp + 0.6 * avg_depth, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cosmology": self.cosmology,
            "chemistry": self.chemistry,
            "biology": self.biology,
            "economics": self.economics,
            "worldview_q": list(self.worldview_q),
            "comprehension": {k: round(v, 4) for k, v in self.comprehension.items()},
            "theorems_discovered": list(self.theorems_discovered),
            "breakthrough_count": self.breakthrough_count,
            "paradigm_progress": {k: round(v, 4) for k, v in self.paradigm_progress.items()},
            "intelligence_index": self.collective_intelligence_index(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpistemicOntology":
        wq = data.get("worldview_q", (1.0, 0.0, 0.0, 0.0))
        return cls(
            cosmology=data.get("cosmology", "NEWTONIAN_FLAT"),
            chemistry=data.get("chemistry", "EMPIRICAL_CORPOREAL"),
            biology=data.get("biology", "FIXED_ESSENCE"),
            economics=data.get("economics", "BARTER_MERCANTILE"),
            worldview_q=tuple(wq) if isinstance(wq, (list, tuple)) and len(wq) == 4 else (1.0, 0.0, 0.0, 0.0),
            comprehension=dict(data.get("comprehension", {"physics": 0.1, "chemistry": 0.1, "biology": 0.1, "economics": 0.1})),
            theorems_discovered=list(data.get("theorems_discovered", [])),
            breakthrough_count=int(data.get("breakthrough_count", 0)),
            paradigm_progress=dict(data.get("paradigm_progress", {"physics": 0.0, "chemistry": 0.0, "biology": 0.0, "economics": 0.0})),
        )


# ==============================================================================
# EPISTEMIC ADVANCEMENT & THEOREM ENGINE
# ==============================================================================

def advance_epistemics(
    kernel: Any,
    civ: Any,
    planet: Any,
    research_surplus: float = 1.0,
    event_bus: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Ticks epistemic progression for a civilization:
    - Channel intellectual surplus into domain comprehension.
    - Check for paradigm transition thresholds.
    - On breakthrough: shift worldview quaternion Q, record theorem, broadcast event.
    """
    if not hasattr(civ, "epistemics") or civ.epistemics is None:
        civ.epistemics = EpistemicOntology()

    ont: EpistemicOntology = civ.epistemics
    breakthroughs: List[Dict[str, str]] = []

    # Factors accelerating research: Orbital Laboratory, tech level, population scale
    lab_bonus = 1.5 if civ.civic_projects.get("Orbital Laboratory", 0) > 0 else 1.0
    tech_mult = 1.0 + (civ.tech_level - 1) * 0.25
    rate = research_surplus * 0.05 * lab_bonus * tech_mult

    # Disposition bias toward domains
    disp = getattr(civ, "disposition", "empiricist")
    weights = {"physics": 1.0, "chemistry": 1.0, "biology": 1.0, "economics": 1.0}
    if disp == "empiricist":
        weights["physics"] += 0.5
        weights["chemistry"] += 0.5
    elif disp == "expansionist":
        weights["economics"] += 0.5
        weights["physics"] += 0.3
    elif disp == "epicurean":
        weights["biology"] += 0.7
    elif disp == "industry":
        weights["chemistry"] += 0.6
        weights["economics"] += 0.4

    for domain, w in weights.items():
        inc = rate * w
        ont.comprehension[domain] = min(1.0, ont.comprehension[domain] + inc * 0.05)
        ont.paradigm_progress[domain] += inc

    # Threshold for advancing paradigm: 1.0 cumulative progress
    THRESHOLD = 1.0

    # 1. Physics Paradigm Evolution
    curr_c_idx = COSMOLOGY_PARADIGMS.index(ont.cosmology)
    if ont.paradigm_progress["physics"] >= THRESHOLD and curr_c_idx < len(COSMOLOGY_PARADIGMS) - 1:
        ont.paradigm_progress["physics"] = 0.0
        ont.cosmology = COSMOLOGY_PARADIGMS[curr_c_idx + 1]
        theorem_name = f"Theorem of {ont.cosmology.title().replace('_', ' ')}"
        ont.theorems_discovered.append(theorem_name)
        ont.breakthrough_count += 1
        _rotate_worldview(ont, axis=(0.0, 1.0, 0.0), angle_rad=0.35)
        breakthroughs.append({"domain": "cosmology", "new_paradigm": ont.cosmology, "theorem": theorem_name})

    # 2. Chemistry Paradigm Evolution
    curr_k_idx = CHEMISTRY_PARADIGMS.index(ont.chemistry)
    if ont.paradigm_progress["chemistry"] >= THRESHOLD and curr_k_idx < len(CHEMISTRY_PARADIGMS) - 1:
        ont.paradigm_progress["chemistry"] = 0.0
        ont.chemistry = CHEMISTRY_PARADIGMS[curr_k_idx + 1]
        theorem_name = f"Alchemical Principle of {ont.chemistry.title().replace('_', ' ')}"
        ont.theorems_discovered.append(theorem_name)
        ont.breakthrough_count += 1
        _rotate_worldview(ont, axis=(1.0, 0.0, 0.0), angle_rad=0.35)
        breakthroughs.append({"domain": "chemistry", "new_paradigm": ont.chemistry, "theorem": theorem_name})

    # 3. Biology Paradigm Evolution
    curr_b_idx = BIOLOGY_PARADIGMS.index(ont.biology)
    if ont.paradigm_progress["biology"] >= THRESHOLD and curr_b_idx < len(BIOLOGY_PARADIGMS) - 1:
        ont.paradigm_progress["biology"] = 0.0
        ont.biology = BIOLOGY_PARADIGMS[curr_b_idx + 1]
        theorem_name = f"Morphogenetic Law of {ont.biology.title().replace('_', ' ')}"
        ont.theorems_discovered.append(theorem_name)
        ont.breakthrough_count += 1
        _rotate_worldview(ont, axis=(0.0, 0.0, 1.0), angle_rad=0.35)
        breakthroughs.append({"domain": "biology", "new_paradigm": ont.biology, "theorem": theorem_name})

    # 4. Economics Paradigm Evolution
    curr_e_idx = ECONOMICS_PARADIGMS.index(ont.economics)
    if ont.paradigm_progress["economics"] >= THRESHOLD and curr_e_idx < len(ECONOMICS_PARADIGMS) - 1:
        ont.paradigm_progress["economics"] = 0.0
        ont.economics = ECONOMICS_PARADIGMS[curr_e_idx + 1]
        theorem_name = f"Trade Dynamic of {ont.economics.title().replace('_', ' ')}"
        ont.theorems_discovered.append(theorem_name)
        ont.breakthrough_count += 1
        _rotate_worldview(ont, axis=(0.7071, 0.7071, 0.0), angle_rad=0.30)
        breakthroughs.append({"domain": "economics", "new_paradigm": ont.economics, "theorem": theorem_name})

    # Broadcast breakthroughs
    if breakthroughs and event_bus:
        for bt in breakthroughs:
            text = f"The {civ.name} of {planet.name} achieved an Epistemic Breakthrough in {bt['domain'].upper()}: Adopted '{bt['new_paradigm']}' ({bt['theorem']})!"
            event_bus.broadcast_radio(
                sender=civ.name,
                text=text,
                channel="COMM-1",
                sector_id=planet.sector_id,
            )

    return {
        "intelligence_index": ont.collective_intelligence_index(),
        "breakthroughs": breakthroughs,
        "cosmology": ont.cosmology,
        "chemistry": ont.chemistry,
        "biology": ont.biology,
        "economics": ont.economics,
    }


def _rotate_worldview(ont: EpistemicOntology, axis: Tuple[float, float, float], angle_rad: float) -> None:
    """Applies an SU(2) rotation to the civilization's worldview quaternion."""
    q_curr = ont.quaternion()
    ax_x, ax_y, ax_z = axis
    norm_ax = math.sqrt(ax_x * ax_x + ax_y * ax_y + ax_z * ax_z) or 1.0
    ux, uy, uz = ax_x / norm_ax, ax_y / norm_ax, ax_z / norm_ax
    
    half = angle_rad / 2.0
    q_rot = Quaternion(math.cos(half), ux * math.sin(half), uy * math.sin(half), uz * math.sin(half))
    q_new = (q_curr * q_rot).normalized()
    ont.set_quaternion(q_new)


# ==============================================================================
# AUTONOMOUS CIVILIZATIONAL AGENCY PRAXIS
# ==============================================================================

def execute_epistemic_agency(
    kernel: Any,
    civ: Any,
    planet: Any,
    event_bus: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Executes autonomous civilizational decisions derived directly from its epistemic comprehension:
    1. Alchemical Induction: If in TORSION_INDUCTION or WEIZSACKER_SEMF, synthesize new continuum superheavies.
    2. Waddington Morphospace Steering: If in WADDINGTON_ADAPTIVE, adapt metabolic basin to planet's S^2 climate.
    3. Waveguide Collimation Tuning: If in HYPERSPHERICAL_S360, align planetary stations with sector waveguide joins.
    """
    if not hasattr(civ, "epistemics") or civ.epistemics is None:
        civ.epistemics = EpistemicOntology()

    ont: EpistemicOntology = civ.epistemics
    actions: Dict[str, Any] = {}

    # --------------------------------------------------------------------------
    # 1. Autonomous Alchemical Induction
    # --------------------------------------------------------------------------
    if ont.chemistry in ("WEIZSACKER_SEMF", "TORSION_INDUCTION"):
        from xylarium.kernel import alchemy, elements_continuum
        # Check planetary mineral inventory
        ore = getattr(planet, "ore", 0)
        if ore >= 50:
            # Determine target superheavy element
            # If Z=114 not discovered, target Fl; else Uue (119) or Ubh (126)
            known = set(civ.discovered_elements)
            target_candidates = ["Fl", "Uue", "Ubn", "Ubu", "Ubh"]
            target = next((sym for sym in target_candidates if sym not in known), None)
            
            if target:
                z_target = elements_continuum.parse_element_z(target)
                elem_info = elements_continuum.get_element(z_target)
                # Deduct resources
                planet.ore = max(0, planet.ore - 30)
                civ.discovered_elements.append(target)
                actions["alchemical_synthesis"] = {
                    "element": target,
                    "atomic_number": z_target,
                    "stability_factor": elem_info.stability_factor,
                    "is_magic_shell": z_target in elements_continuum.MAGIC_Z,
                    "success": True,
                }
                if event_bus:
                    event_bus.broadcast_radio(
                        sender=civ.name,
                        text=f"The {civ.name} state laboratories have synthesized the superheavy element {elem_info.name} ({target}, Z={z_target}) via {ont.chemistry} alchemical induction!",
                        channel="COMM-1",
                        sector_id=planet.sector_id,
                    )

    # --------------------------------------------------------------------------
    # 2. Autonomous Waddington Epigenetic Adaptation
    # --------------------------------------------------------------------------
    if ont.biology in ("WADDINGTON_ADAPTIVE", "TRANSSOMATIC_COSMIC"):
        from xylarium.kernel import skies, genome
        # Read continuous climate on S^2
        try:
            clim = skies.compute_climate_manifold(planet, kernel=kernel)
            t_eq = clim.get("t_equator_k", 288.0)
            
            # Formulate current cellular morphospace
            current_basin = "CARBON_AQUEOUS"
            if t_eq < 230.0:
                target_basin = "METHANOGENIC_CRYOPHILIC"
                opt_activation = 0.55
            elif t_eq > 340.0:
                target_basin = "IRON_SULFUR_LITHOTROPH"
                opt_activation = 1.10
            else:
                target_basin = "CARBON_AQUEOUS"
                opt_activation = 0.85

            coord = genome.MorphospaceCoordinate(
                elemental_ratios={"C": 0.40, "N": 0.15, "P": 0.05, "O": 0.25, "H2O": 0.15},
                activation_energy_ev=opt_activation,
                catalytic_entropy=0.002,
                basin_id=target_basin,
            )
            drifted = genome.evaluate_waddington_drift(kernel, planet, coord)
            # Boost planetary morale and carrying efficiency due to somatic optimization
            planet.morale = min(100, planet.morale + 5)
            actions["somatic_adaptation"] = {
                "target_basin": target_basin,
                "activation_energy_ev": round(drifted.activation_energy_ev, 3),
                "adapted_to_temperature_k": round(t_eq, 1),
            }
        except Exception as e:
            actions["somatic_adaptation"] = {"error": str(e)}

    # --------------------------------------------------------------------------
    # 3. Autonomous Waveguide Collimation Tuning
    # --------------------------------------------------------------------------
    if ont.cosmology == "HYPERSPHERICAL_S360":
        from xylarium.kernel import spheres
        sec_id = planet.sector_id
        adj_id = (sec_id % 60) + 1
        try:
            conduit = spheres.waveguide_conduit(kernel, sec_id, adj_id)
            gain = conduit.get("collimation_gain", 1.0)
            # Higher collimation provides defense shield coherence and trade efficiency
            shield_boost = int(gain * 10)
            planet.max_shields += shield_boost
            planet.shields = min(planet.max_shields, planet.shields + shield_boost)
            actions["waveguide_tuning"] = {
                "target_sector": adj_id,
                "collimation_gain": gain,
                "shield_boost_mw": shield_boost,
            }
        except Exception as e:
            actions["waveguide_tuning"] = {"error": str(e)}

    # --------------------------------------------------------------------------
    # 4. Autonomous Living Trade Fleet Commissioning & Dispatch
    # --------------------------------------------------------------------------
    if ont.economics in ("RELATIVISTIC_FLUID", "HOMOLOGICAL_SYNTHESIS") and kernel and hasattr(kernel, "market_manager"):
        treasury = getattr(planet, "treasury", 0)
        # If planet has treasury and mineral surplus, check if civilization needs trade convoys
        sec_id = planet.sector_id
        mm = kernel.market_manager
        # Check active haulers owned by this civ
        civ_haulers = [h for h in mm.trade_haulers.values() if h.owner_id == f"civ:{civ.name}" and h.active]
        if len(civ_haulers) < 3 and treasury >= 15000:
            # Select hull class based on what the civilization produces and discovers
            known_elems = getattr(civ, "discovered_elements", [])
            has_superheavy = any(e in ("Fl", "Uue", "Ubn", "Ubu", "Ubh", "pyrosite", "umbrite", "AdL") for e in known_elems)
            
            if has_superheavy and ont.chemistry == "TORSION_INDUCTION":
                hull_choice = "SUPERHEAVY_TRANSPORTER"
                out_comm = next((e for e in ("Fl", "Uue", "Ubu", "Ubh", "pyrosite", "umbrite", "AdL") if e in known_elems), "AdL")
                ret_comm = "ORE"
            elif any(e in ("U", "Pt", "SpR") for e in known_elems):
                hull_choice = "ACTINIDE_HAULER"
                out_comm = "U"
                ret_comm = "EQUIPMENT"
            elif civ.metabolism == "biotic":
                hull_choice = "BIOSPHERE_VESSEL"
                out_comm = "ORGANICS"
                ret_comm = "EQUIPMENT"
            elif civ.metabolism == "mineral":
                hull_choice = "BULK_FREIGHTER"
                out_comm = "ORE"
                ret_comm = "ORGANICS"
            else:
                hull_choice = "CRYO_TANKER"
                out_comm = "H"
                ret_comm = "ORGANICS"

            # Destination sector: select reachable commercial spaceport
            ported_secs = [s.id for s in kernel.sectors.values() if s.port and s.id != sec_id]
            target_sec = 1 if (sec_id != 1 and 1 in ported_secs) else (ported_secs[0] if ported_secs else 1)
            # Deduct cost from planet treasury
            from xylarium.config import SPECIALIZED_HULLS
            h_cfg = SPECIALIZED_HULLS.get(hull_choice, {})
            cost = h_cfg.get("price", 10000)
            if treasury >= cost:
                planet.treasury -= cost
                hid = f"CIV-HAUL-{mm.next_hauler_id}"
                mm.next_hauler_id += 1
                
                # Check path
                path = kernel.find_path(sec_id, target_sec)
                p_steps = path[1:] if len(path) > 1 else []
                from xylarium.kernel.models import TradeHauler
                new_h = TradeHauler(
                    id=hid,
                    owner_id=f"civ:{civ.name}",
                    name=f"{civ.name} {h_cfg.get('name', 'Conveyance')} {hid}",
                    sector_id=sec_id,
                    hull_class=hull_choice,
                    status="IN_TRANSIT" if p_steps else "IDLE",
                    capacity=h_cfg.get("holds", 50),
                    origin_sector=sec_id,
                    dest_sector=target_sec,
                    commodity_outbound=out_comm,
                    commodity_return=ret_comm,
                    cargo={},
                    escort_fighters=20,
                    wear_and_tear=0,
                    current_path=p_steps,
                    lifetime_profit=0,
                    trips_completed=0,
                    active=True,
                    wormhole_enabled=bool(h_cfg.get("wormhole_capable", False)),
                    security_escort=2,
                    chemical_rating=h_cfg.get("chemical_rating", "BASIC"),
                )
                mm.trade_haulers[hid] = new_h
                actions["fleet_commissioned"] = {
                    "hauler_id": hid,
                    "hull_class": hull_choice,
                    "origin": sec_id,
                    "destination": target_sec,
                    "chemical_rating": new_h.chemical_rating,
                    "security_escort": 2,
                    "wormhole_enabled": new_h.wormhole_enabled,
                }
                if event_bus:
                    event_bus.broadcast_radio(
                        sender=civ.name,
                        text=f"The {civ.name} state stardocks launched merchant hauler {new_h.name} ({hull_choice}) on trade corridor {sec_id:03d} <-> {target_sec:03d}!",
                        channel="COMM-1",
                        sector_id=sec_id,
                    )

    return actions


# ==============================================================================
# INTER-CIVILIZATIONAL EPISTEMIC DIPLOMACY & RESONANCE
# ==============================================================================

def epistemic_diplomatic_affinity(civ_a: Any, civ_b: Any) -> Dict[str, Any]:
    """
    Evaluates diplomatic and cultural affinity based on the relative SU(2) worldview holonomy
    between two civilizations:
    - Resonance I in [0.7, 1.0]: Deep ideological congruence (alliances, open scientific research sharing).
    - Resonance I in [-0.2, 0.7]: Pragmatic neutral coexistence.
    - Resonance I < -0.2: Ontological polarization (ideological distrust, border disputes).
    """
    ont_a: EpistemicOntology = getattr(civ_a, "epistemics", None) or EpistemicOntology()
    ont_b: EpistemicOntology = getattr(civ_b, "epistemics", None) or EpistemicOntology()

    res = ont_a.resonance_with(ont_b)

    if res >= 0.70:
        regime = "CONGRUENT_RESONANCE"
        trust_bonus = 0.25
        trade_mult = 1.30
    elif res >= 0.20:
        regime = "HARMONIC_ACCORD"
        trust_bonus = 0.10
        trade_mult = 1.10
    elif res >= -0.20:
        regime = "PRAGMATIC_NEUTRAL"
        trust_bonus = 0.0
        trade_mult = 1.00
    elif res >= -0.60:
        regime = "ONTOLOGICAL_DISSONANCE"
        trust_bonus = -0.15
        trade_mult = 0.85
    else:
        regime = "POLARIZED_SHEAR"
        trust_bonus = -0.35
        trade_mult = 0.70

    return {
        "civ_a": getattr(civ_a, "name", "A"),
        "civ_b": getattr(civ_b, "name", "B"),
        "resonance": round(res, 4),
        "regime": regime,
        "trust_bonus": trust_bonus,
        "trade_multiplier": trade_mult,
    }
