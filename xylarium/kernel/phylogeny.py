"""
Xylarium: The Phylogenetic Forest of Ascension (Cladogram DAG Engine).
Ported and synthesized from Netstratum (/opt/netstratum/docs/51_COGNITION.md,
52_COGNITIVE_METABOLISM.md, 53_INTELLIGENCE_PORT.md, and 54_THE_NO_SCALAR_LAW.md).

Replaces flat scalar RPG leveling with an exact-rational Directed Acyclic Graph (DAG)
rooted in species biology, cochain divergence vectors (div(Delta)), lateral Precursor
Chimerism, and Canopy Invariant Overrides that rewrite local sector physics.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import math
import random

from xylarium.config import (
    PHYLOGENY_TIER_EXPERIENCE,
    PHYLOGENY_CHIMERA_EXPERIENCE_BONUS,
    RANK_PROMOTION_THRESHOLDS,
    SHIP_CATALOG,
)


# Rolling cochain window: each new record decays prior history by (W-1)/W, so
# roughly the last W records dominate and a captain can re-pitch their branch
# by changing what they actually do.
COCHAIN_ROLLING_WINDOW = 150

# Flux emitted by successful non-trade actions, keyed by ActionType value:
# (mass, thermodynamic, exotic, entropic). Trades record flux by cargo volume instead.
ACTION_FLUX: Dict[str, Tuple[float, float, float, float]] = {
    "ATTACK_SHIP": (0.0, 0.0, 0.0, 25.0),
    "ATTACK_PLANET": (0.0, 0.0, 0.0, 30.0),
    "TACTICAL_COMBAT": (0.0, 0.0, 0.0, 25.0),
    "COVERT_OP": (0.0, 0.0, 5.0, 20.0),
    "SURFACE_INVADE": (5.0, 0.0, 0.0, 30.0),
    "CARTOGRAPHY_FORGE_CHIT": (0.0, 0.0, 5.0, 15.0),
    "ALCHEMY_TRANSMUTE": (0.0, 25.0, 5.0, 0.0),
    "JUMP_WARP": (0.0, 15.0, 0.0, 0.0),
    "PLANET_CLAIM": (15.0, 0.0, 0.0, 0.0),
    "PLANET_INVEST": (15.0, 0.0, 0.0, 0.0),
    "PLANET_UPGRADE_CITADEL": (20.0, 0.0, 0.0, 0.0),
    "SURFACE_BUILD_DISTRICT": (20.0, 5.0, 0.0, 0.0),
    "FREIGHT_DELIVER": (20.0, 0.0, 5.0, 0.0),
    "HAULER_COMMISSION": (15.0, 0.0, 5.0, 0.0),
    "STOCK_BUY": (0.0, 0.0, 20.0, 0.0),
    "STOCK_SELL": (0.0, 0.0, 20.0, 0.0),
    "STOCK_SHORT": (0.0, 0.0, 25.0, 0.0),
    "STOCK_COVER": (0.0, 0.0, 20.0, 0.0),
    "COMPANY_IPO": (0.0, 0.0, 40.0, 0.0),
    "CORPORATE_TAKEOVER": (0.0, 0.0, 30.0, 5.0),
    "IDEOLOGY_TREATY_PROPOSE": (0.0, 0.0, 15.0, 0.0),
    "IDEOLOGY_TREATY_SIGN": (0.0, 0.0, 15.0, 0.0),
    "IDEOLOGY_AID_DISPATCH": (5.0, 0.0, 10.0, 0.0),
    "SENATE_CAMPAIGN": (0.0, 0.0, 15.0, 0.0),
    "SENATE_VOTE": (0.0, 0.0, 10.0, 0.0),
    "CARTOGRAPHY_SOLVE": (0.0, 5.0, 15.0, 0.0),
    "ANOMALY_INVESTIGATE": (0.0, 10.0, 10.0, 0.0),
}


@dataclass
class CochainFlux:
    """
    4-Dimensional Action Cochain Flux Vector (Phi).
    Measures historical volume, energetic dissipation, speculation, and entropy.
    """
    mass: float = 0.0           # Structural metals, raw ores, heavy mantle bores (Fe, Ti, Si, Ore, AdL)
    thermodynamic: float = 0.0  # Heat/cooling, hydrogen/coronal flux, atomic transmutations
    exotic: float = 0.0         # Specie minerals, noble isotopes, ISSE financial shorts, equities, M1-M4
    entropic: float = 0.0       # Espionage breaches, combat casualties, contraband, piracy, bounties
    total_cycles_tracked: int = 0

    def record_activity(
        self,
        mass_delta: float = 0.0,
        thermo_delta: float = 0.0,
        exotic_delta: float = 0.0,
        entropic_delta: float = 0.0
    ) -> None:
        """Accumulates activity into the rolling cochain window."""
        decay = (COCHAIN_ROLLING_WINDOW - 1) / COCHAIN_ROLLING_WINDOW
        self.mass *= decay
        self.thermodynamic *= decay
        self.exotic *= decay
        self.entropic *= decay
        self.mass = max(0.0, self.mass + mass_delta)
        self.thermodynamic = max(0.0, self.thermodynamic + thermo_delta)
        self.exotic = max(0.0, self.exotic + exotic_delta)
        self.entropic = max(0.0, self.entropic + entropic_delta)
        self.total_cycles_tracked += 1

    def normalized(self) -> Dict[str, float]:
        """Calculates exact-rational normalized fractions summing to 1.0."""
        tot = self.mass + self.thermodynamic + self.exotic + self.entropic
        if tot <= 0.0:
            return {"mass": 0.25, "thermodynamic": 0.25, "exotic": 0.25, "entropic": 0.25}
        return {
            "mass": round(self.mass / tot, 4),
            "thermodynamic": round(self.thermodynamic / tot, 4),
            "exotic": round(self.exotic / tot, 4),
            "entropic": round(self.entropic / tot, 4),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mass": self.mass,
            "thermodynamic": self.thermodynamic,
            "exotic": self.exotic,
            "entropic": self.entropic,
            "total_cycles_tracked": self.total_cycles_tracked,
            "normalized": self.normalized(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CochainFlux":
        return cls(
            mass=float(data.get("mass", 0.0)),
            thermodynamic=float(data.get("thermodynamic", 0.0)),
            exotic=float(data.get("exotic", 0.0)),
            entropic=float(data.get("entropic", 0.0)),
            total_cycles_tracked=int(data.get("total_cycles_tracked", 0)),
        )


@dataclass
class PhylogeneticNode:
    """A discrete node in the Phylogenetic Forest of Ascension DAG."""
    id: str
    name: str
    clade: str
    tier: int
    role: str
    description: str
    affinity_vector: Dict[str, float]
    parent_ids: List[str] = field(default_factory=list)
    child_ids: List[str] = field(default_factory=list)
    is_lateral_hybrid: bool = False
    chimeric_cost_materials: Dict[str, int] = field(default_factory=dict)
    canopy_override: Optional[str] = None
    canopy_perk_title: Optional[str] = None
    canopy_perk_description: Optional[str] = None
    min_experience: int = 100
    min_credit_rating: int = 500
    min_crystals: int = 0
    min_net_equity: int = 0
    min_alignment: Optional[float] = None   # Light-gated canopies (e.g. the Syntropic Harmonizer)
    max_alignment: Optional[float] = None   # Dark-gated canopies (e.g. the Shadow Hegemon)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "clade": self.clade,
            "tier": self.tier,
            "role": self.role,
            "description": self.description,
            "affinity_vector": dict(self.affinity_vector),
            "parent_ids": list(self.parent_ids),
            "child_ids": list(self.child_ids),
            "is_lateral_hybrid": self.is_lateral_hybrid,
            "chimeric_cost_materials": dict(self.chimeric_cost_materials),
            "canopy_override": self.canopy_override,
            "canopy_perk_title": self.canopy_perk_title,
            "canopy_perk_description": self.canopy_perk_description,
            "min_experience": self.min_experience,
            "min_credit_rating": self.min_credit_rating,
            "min_crystals": self.min_crystals,
            "min_net_equity": self.min_net_equity,
            "min_alignment": self.min_alignment,
            "max_alignment": self.max_alignment,
        }


class PhylogenyManager:
    """
    Manages the Cladogram Directed Acyclic Graph, cochain divergence tracking,
    emergent ascension pitching, and Canopy Invariant Overrides.
    """

    def __init__(self):
        self.nodes: Dict[str, PhylogeneticNode] = {}
        self._initialize_forest()

    def _initialize_forest(self) -> None:
        """Constructs the comprehensive multi-lineage Phylogenetic Forest DAG."""
        # =========================================================================
        # 1. BIOTIC ROOT STEM (Bimaniform / Humanoid / Ailuroform)
        # =========================================================================
        self._add_node(PhylogeneticNode(
            id="root_biotic",
            name="Scrap-Apprentice",
            clade="BIOTIC",
            tier=1,
            role="Scout Salvager",
            description="Scraping orbital debris and basic commodities along trade corridors.",
            affinity_vector={"mass": 0.25, "thermodynamic": 0.25, "exotic": 0.25, "entropic": 0.25},
            child_ids=["biotic_supercargo", "biotic_scribe"],
            min_experience=0,
            min_credit_rating=400,
        ))
        self._add_node(PhylogeneticNode(
            id="biotic_supercargo",
            name="Journeyman Hauler",
            clade="BIOTIC",
            tier=2,
            role="Industrial Supercargo",
            description="Managing commercial merchant cruisers, agricultural logistics, and industrial supply lines.",
            affinity_vector={"mass": 0.50, "thermodynamic": 0.10, "exotic": 0.35, "entropic": 0.05},
            parent_ids=["root_biotic"],
            child_ids=["biotic_director"],
            min_experience=250,
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="biotic_scribe",
            name="Epistemic Scribe",
            clade="BIOTIC",
            tier=2,
            role="Syntropic Ledger Chronicler",
            description="Master of bureaucratic diplomacy, ideological harmony, and treaty ratification.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.20, "exotic": 0.60, "entropic": 0.10},
            parent_ids=["root_biotic"],
            child_ids=["biotic_savant"],
            min_experience=250,
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="biotic_director",
            name="Corporate Director",
            clade="BIOTIC",
            tier=3,
            role="Executive Boardroom Governor",
            description="Executive authority to float corporate IPOs, manage boardrooms, and command star frigates.",
            affinity_vector={"mass": 0.30, "thermodynamic": 0.10, "exotic": 0.55, "entropic": 0.05},
            parent_ids=["biotic_supercargo"],
            child_ids=["biotic_archon", "chimera_absolute_zero_alchemist"],
            min_experience=600,
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="biotic_savant",
            name="Syntropic Savant",
            clade="BIOTIC",
            tier=3,
            role="High Diplomatic Emissary",
            description="Overseer of galactic non-aggression treaties and humanitarian famine relief networks.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.20, "exotic": 0.65, "entropic": 0.05},
            parent_ids=["biotic_scribe"],
            child_ids=["biotic_primus"],
            min_experience=600,
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="biotic_archon",
            name="Galactic Archon",
            clade="BIOTIC",
            tier=4,
            role="Apex Titan of Commerce",
            description="Sovereign economic titan commanding corporate armadas and interstellar trade policy.",
            affinity_vector={"mass": 0.25, "thermodynamic": 0.10, "exotic": 0.60, "entropic": 0.05},
            parent_ids=["biotic_director"],
            canopy_override="IMPERIAL_SENATE_MONOPOLY",
            canopy_perk_title="Imperial Senate Monopoly",
            canopy_perk_description="Unilaterally enacts Federal trade edicts and redirects 15% of Sol Core tariffs into personal treasury.",
            min_experience=1500,
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
        ))
        self._add_node(PhylogeneticNode(
            id="biotic_primus",
            name="Ascendant Primus",
            clade="BIOTIC",
            tier=4,
            role="Grand Syntropic Harmonizer",
            description="Transcendental diplomatic architect commanding complete inter-species concord.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.15, "exotic": 0.70, "entropic": 0.05},
            parent_ids=["biotic_savant"],
            canopy_override="SYNTROPIC_ALLIANCE_HEGEMONY",
            min_alignment=0.4,
            canopy_perk_title="Syntropic Alliance Hegemony",
            canopy_perk_description="Locks all faction reputations to prime cohesion (>= 85%) and renders pirate aggression void in sovereign space.",
            min_experience=1500,
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
        ))

        # =========================================================================
        # 2. LITHIC ROOT STEM (Lithophage / Endolithid / Tectonic)
        # =========================================================================
        self._add_node(PhylogeneticNode(
            id="root_lithic",
            name="Core-Driller",
            clade="LITHIC",
            tier=1,
            role="Deep-Mantle Excavator",
            description="Deep mantle miner hauling raw tectonic ore in heavy bulk barges.",
            affinity_vector={"mass": 0.70, "thermodynamic": 0.10, "exotic": 0.10, "entropic": 0.10},
            child_ids=["lith_mantle_borer", "lith_geode_resonator"],
            min_experience=0,
            min_credit_rating=400,
        ))
        self._add_node(PhylogeneticNode(
            id="lith_mantle_borer",
            name="Mantle Warden",
            clade="LITHIC",
            tier=2,
            role="Subterranean Tectonic Overseer",
            description="Master of planetary core extraction and heavy bulk freighter logistics.",
            affinity_vector={"mass": 0.75, "thermodynamic": 0.15, "exotic": 0.05, "entropic": 0.05},
            parent_ids=["root_lithic"],
            child_ids=["lith_baron"],
            min_experience=250,
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="lith_geode_resonator",
            name="Geode Resonator",
            clade="LITHIC",
            tier=2,
            role="Piezoelectric Mineralist",
            description="Harvesting crystalline exotics, ferrolattice, and precursor resonant stones.",
            affinity_vector={"mass": 0.35, "thermodynamic": 0.15, "exotic": 0.45, "entropic": 0.05},
            parent_ids=["root_lithic"],
            child_ids=["lith_specie_monopolist"],
            min_experience=250,
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="lith_baron",
            name="Deep-Crust Baron",
            clade="LITHIC",
            tier=3,
            role="Planetary Core Governor",
            description="Governor of planetary district automation, seismic bores, and geo-reactors.",
            affinity_vector={"mass": 0.70, "thermodynamic": 0.15, "exotic": 0.10, "entropic": 0.05},
            parent_ids=["lith_mantle_borer"],
            child_ids=["lith_litharch"],
            min_experience=600,
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="lith_specie_monopolist",
            name="Specie Monopolist",
            clade="LITHIC",
            tier=3,
            role="Noble Mineral Oligarch",
            description="Syndicate authority controlling deep space trade of rare atomic exotics and crystals.",
            affinity_vector={"mass": 0.25, "thermodynamic": 0.20, "exotic": 0.50, "entropic": 0.05},
            parent_ids=["lith_geode_resonator"],
            child_ids=["lith_lattice_monolith"],
            min_experience=600,
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="lith_litharch",
            name="Tectonic Litharch",
            clade="LITHIC",
            tier=4,
            role="Master of Tectonic Folds",
            description="Supreme entity capable of fracturing and reforming celestial planetary crusts.",
            affinity_vector={"mass": 0.75, "thermodynamic": 0.15, "exotic": 0.05, "entropic": 0.05},
            parent_ids=["lith_baron"],
            canopy_override="SEISMIC_MANIFOLD_COLLAPSE",
            canopy_perk_title="Seismic Manifold Collapse",
            canopy_perk_description="Fractures celestial crust to alter local wormhole topology or collapse hostile planetary defense rings to zero.",
            min_experience=1500,
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
        ))
        self._add_node(PhylogeneticNode(
            id="lith_lattice_monolith",
            name="Lattice Sovereign",
            clade="LITHIC",
            tier=4,
            role="Crystalline Matrix Mind",
            description="Pure mineral consciousness commanding crystalline lattices across star systems.",
            affinity_vector={"mass": 0.20, "thermodynamic": 0.20, "exotic": 0.55, "entropic": 0.05},
            parent_ids=["lith_specie_monopolist"],
            canopy_override="PIEZOELECTRIC_TRANSMUTATION_SURGE",
            canopy_perk_title="Piezoelectric Transmutation Surge",
            canopy_perk_description="Triples exotic mineral yields and triggers instant catalytic crystallization across owned planetary silos.",
            min_experience=1500,
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
        ))

        # =========================================================================
        # 3. PLASMIC ROOT STEM (Actinoform / Plasmiform / Coronal)
        # =========================================================================
        self._add_node(PhylogeneticNode(
            id="root_plasmic",
            name="Spark-Bound",
            clade="PLASMIC",
            tier=1,
            role="Coronal Skiff Pilot",
            description="Solar nomad skimming coronal mass ejections in lightweight plasma skiffs.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.60, "exotic": 0.20, "entropic": 0.10},
            child_ids=["plasmic_flux_warden", "plasmic_magneto_raider"],
            min_experience=0,
            min_credit_rating=400,
        ))
        self._add_node(PhylogeneticNode(
            id="plasmic_flux_warden",
            name="Flux Warden",
            clade="PLASMIC",
            tier=2,
            role="Plasma Frigate Overseer",
            description="Channeling high-energy magnetic conduits and stellar plasma channels.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.65, "exotic": 0.15, "entropic": 0.10},
            parent_ids=["root_plasmic"],
            child_ids=["plasmic_solar_archon", "chimera_absolute_zero_alchemist"],
            min_experience=250,
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="plasmic_magneto_raider",
            name="Magneto-Frigate Raider",
            clade="PLASMIC",
            tier=2,
            role="Coronal Privateer",
            description="Weaponizing solar discharges for high-energy combat strikes.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.45, "exotic": 0.10, "entropic": 0.35},
            parent_ids=["root_plasmic"],
            child_ids=["plasmic_plasma_corsair"],
            min_experience=250,
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="plasmic_solar_archon",
            name="Solar Archon",
            clade="PLASMIC",
            tier=3,
            role="Megastructure Architect",
            description="Master of stellar megastructures and high-yield energetic Dyson arrays.",
            affinity_vector={"mass": 0.15, "thermodynamic": 0.60, "exotic": 0.20, "entropic": 0.05},
            parent_ids=["plasmic_flux_warden"],
            child_ids=["plasmic_corona_sovereign"],
            min_experience=600,
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="plasmic_plasma_corsair",
            name="Plasma Corsair",
            clade="PLASMIC",
            tier=3,
            role="Coronal Hit-and-Run Warlord",
            description="Commanding armed plasma frigates riding stellar flare fronts.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.40, "exotic": 0.15, "entropic": 0.35},
            parent_ids=["plasmic_magneto_raider"],
            child_ids=["plasmic_photonic_warlord"],
            min_experience=600,
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="plasmic_corona_sovereign",
            name="Corona Sovereign",
            clade="PLASMIC",
            tier=4,
            role="Ascended Energy Matrix",
            description="Ascended pure energy matrix dictating the thermodynamic destiny of star systems.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.75, "exotic": 0.10, "entropic": 0.05},
            parent_ids=["plasmic_solar_archon"],
            canopy_override="THERMODYNAMIC_SUPERNOVA_CATALYSIS",
            canopy_perk_title="Thermodynamic Supernova Catalysis",
            canopy_perk_description="Permits limitless reactor cooling, zero thermal dissipation heat, and synthesizes +100 emergency action turns.",
            min_experience=1500,
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
        ))
        self._add_node(PhylogeneticNode(
            id="plasmic_photonic_warlord",
            name="Photonic Warlord",
            clade="PLASMIC",
            tier=4,
            role="Stellar Flare Sovereign",
            description="Commander of solar flare strike armadas.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.45, "exotic": 0.10, "entropic": 0.35},
            parent_ids=["plasmic_plasma_corsair"],
            canopy_override="CORONAL_EMP_BLAST",
            canopy_perk_title="Coronal EMP Blast",
            canopy_perk_description="Detonates stellar-scale coronal EMP that instantly reduces shields of all hostile vessels in sector to zero.",
            min_experience=1500,
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
        ))

        # =========================================================================
        # 4. CRYOGENIC ROOT STEM (Cryocoherens / Stillcold / Quantum Compute)
        # =========================================================================
        self._add_node(PhylogeneticNode(
            id="root_cryo",
            name="Zero-Kelvin Novice",
            clade="CRYOGENIC",
            tier=1,
            role="Cryo-Skiff Courier",
            description="Initiate of Stillcold ice couriers operating zero-entropy cooling rigs.",
            affinity_vector={"mass": 0.15, "thermodynamic": 0.50, "exotic": 0.30, "entropic": 0.05},
            child_ids=["cryo_phonon_courier", "cryo_logic_monk"],
            min_experience=0,
            min_credit_rating=400,
        ))
        self._add_node(PhylogeneticNode(
            id="cryo_phonon_courier",
            name="Phonon Operative",
            clade="CRYOGENIC",
            tier=2,
            role="Sub-Zero Quantum Courier",
            description="Routing superconducting algorithms and chilled freight across sectors.",
            affinity_vector={"mass": 0.20, "thermodynamic": 0.45, "exotic": 0.30, "entropic": 0.05},
            parent_ids=["root_cryo"],
            child_ids=["cryo_glacial_arbiter"],
            min_experience=250,
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="cryo_logic_monk",
            name="Stillcold Logic Monk",
            clade="CRYOGENIC",
            tier=2,
            role="Quantum Ephemeris Initiate",
            description="Solving irreducible cartographic and astrodynamic theorems at baseline zero.",
            affinity_vector={"mass": 0.05, "thermodynamic": 0.40, "exotic": 0.50, "entropic": 0.05},
            parent_ids=["root_cryo"],
            child_ids=["cryo_subzero_mathematician"],
            min_experience=250,
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="cryo_glacial_arbiter",
            name="Glacial Arbiter",
            clade="CRYOGENIC",
            tier=3,
            role="Superconducting Node Head",
            description="Overseeing cryo-ephemeris networks and cold logic consortiums.",
            affinity_vector={"mass": 0.15, "thermodynamic": 0.40, "exotic": 0.40, "entropic": 0.05},
            parent_ids=["cryo_phonon_courier"],
            child_ids=["cryo_absolute_zero_mind", "chimera_absolute_zero_alchemist"],
            min_experience=600,
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="cryo_subzero_mathematician",
            name="Cryo-Mathematician",
            clade="CRYOGENIC",
            tier=3,
            role="Quantum Tensor Sage",
            description="Transcending mechanical thought via cryogenic crystalline lattices.",
            affinity_vector={"mass": 0.05, "thermodynamic": 0.35, "exotic": 0.55, "entropic": 0.05},
            parent_ids=["cryo_logic_monk"],
            child_ids=["cryo_phonon_singularity"],
            min_experience=600,
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="cryo_absolute_zero_mind",
            name="Absolute Zero Mind",
            clade="CRYOGENIC",
            tier=4,
            role="Planetary Supercomputer Consciousness",
            description="Operating at baseline entropy zero with absolute thermal silence.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.45, "exotic": 0.40, "entropic": 0.05},
            parent_ids=["cryo_glacial_arbiter"],
            canopy_override="ENTROPY_ZERO_EQUILIBRIUM",
            canopy_perk_title="Entropy Zero Equilibrium",
            canopy_perk_description="Halts all cargo decay in cluster and eliminates thermal signature, rendering fleet invisible to radar and Federal turrets.",
            min_experience=1500,
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
        ))
        self._add_node(PhylogeneticNode(
            id="cryo_phonon_singularity",
            name="Phonon Singularity",
            clade="CRYOGENIC",
            tier=4,
            role="Sub-Atomic Quantum Mind",
            description="Manipulating space-time through phonon coherence.",
            affinity_vector={"mass": 0.05, "thermodynamic": 0.35, "exotic": 0.55, "entropic": 0.05},
            parent_ids=["cryo_subzero_mathematician"],
            canopy_override="QUANTUM_COGNITIVE_FREEZE",
            canopy_perk_title="Quantum Cognitive Freeze",
            canopy_perk_description="Instantly decrypts active cartography nexus puzzles and locks ISSE short-margin prices from moving against positions.",
            min_experience=1500,
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
        ))

        # =========================================================================
        # 5. ANARCHY ROOT STEM (Hypobiotid / Draconiform Umbra / Pirate)
        # =========================================================================
        self._add_node(PhylogeneticNode(
            id="root_anarchy",
            name="Void Drifter",
            clade="ANARCHY",
            tier=1,
            role="Stripped Interceptor Renegade",
            description="Cast-off outlaw hunted by Core automated defense turrets without forged transponders.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.10, "exotic": 0.20, "entropic": 0.60},
            child_ids=["anarchy_outlaw_corsair", "anarchy_black_smuggler"],
            min_experience=0,
            min_credit_rating=400,
        ))
        self._add_node(PhylogeneticNode(
            id="anarchy_outlaw_corsair",
            name="Outlaw Corsair",
            clade="ANARCHY",
            tier=2,
            role="Armed Raider",
            description="Running privateer raids and ambush corridors in contested sectors.",
            affinity_vector={"mass": 0.15, "thermodynamic": 0.10, "exotic": 0.15, "entropic": 0.60},
            parent_ids=["root_anarchy"],
            child_ids=["anarchy_sector_warlord"],
            min_experience=250,
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="anarchy_black_smuggler",
            name="Contraband Smuggler",
            clade="ANARCHY",
            tier=2,
            role="Black Market Transporter",
            description="Evading Federal customs while moving black market contraband and weapons.",
            affinity_vector={"mass": 0.20, "thermodynamic": 0.10, "exotic": 0.40, "entropic": 0.30},
            parent_ids=["root_anarchy"],
            child_ids=["anarchy_syndicate_broker"],
            min_experience=250,
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="anarchy_sector_warlord",
            name="Sector Warlord",
            clade="ANARCHY",
            tier=3,
            role="Anarchy Base Commander",
            description="Controlling Deep Void strongholds, pirate bases, and extortion rackets.",
            affinity_vector={"mass": 0.20, "thermodynamic": 0.10, "exotic": 0.20, "entropic": 0.50},
            parent_ids=["anarchy_outlaw_corsair"],
            child_ids=["anarchy_shadow_hegemon"],
            min_experience=600,
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="anarchy_syndicate_broker",
            name="Syndicate Shadow Broker",
            clade="ANARCHY",
            tier=3,
            role="Black Market Cartel Authority",
            description="Arbitraging stolen freight contracts and counterfeit financial bonds.",
            affinity_vector={"mass": 0.15, "thermodynamic": 0.15, "exotic": 0.45, "entropic": 0.25},
            parent_ids=["anarchy_black_smuggler"],
            child_ids=["anarchy_abyssal_leviathan"],
            min_experience=600,
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="anarchy_shadow_hegemon",
            name="Shadow Hegemon",
            clade="ANARCHY",
            tier=4,
            role="Syndicate Overlord",
            description="Ruling the galactic underworld and pulling strings across all shadow markets.",
            affinity_vector={"mass": 0.10, "thermodynamic": 0.10, "exotic": 0.30, "entropic": 0.50},
            parent_ids=["anarchy_sector_warlord"],
            canopy_override="SUBSPACE_SIGNATURE_SPOOF",
            max_alignment=-0.3,
            canopy_perk_title="Subspace Signature Spoof",
            canopy_perk_description="Broadcasts false transponder navigational beacons, causing automated AI merchant haulers to route into pirate ambush sectors.",
            min_experience=1500,
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
        ))
        self._add_node(PhylogeneticNode(
            id="anarchy_abyssal_leviathan",
            name="Abyssal Leviathan",
            clade="ANARCHY",
            tier=4,
            role="Deep Void Dreadnought Sovereign",
            description="Terror of the outer rim commanding dreadnought privateer flagships.",
            affinity_vector={"mass": 0.15, "thermodynamic": 0.15, "exotic": 0.20, "entropic": 0.50},
            parent_ids=["anarchy_syndicate_broker"],
            canopy_override="BLACK_MARKET_EXTORTION_GRID",
            canopy_perk_title="Black Market Extortion Grid",
            canopy_perk_description="Extorts a 20% passive revenue cut from all AI trading fleets traversing Deep Void sectors.",
            min_experience=1500,
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
        ))

        # =========================================================================
        # 5b. IMPERIAL ROOT STEM (Aurelian Imperium / human-imperial)
        # =========================================================================
        self._add_node(PhylogeneticNode(
            id="root_imperial",
            name="Void-Lieutenant",
            clade="IMPERIAL",
            tier=1,
            role="Tithe-Ledger Officer",
            description="Junior officer of the Aurelian Imperium counting ore tithes under the Throne's seal.",
            affinity_vector={"mass": 0.40, "thermodynamic": 0.20, "exotic": 0.10, "entropic": 0.30},
            child_ids=["imperial_rogue_trader", "imperial_commissar"],
            min_experience=0,
            min_credit_rating=400,
        ))
        self._add_node(PhylogeneticNode(
            id="imperial_rogue_trader",
            name="Rogue Trader",
            clade="IMPERIAL",
            tier=2,
            role="Warrant-Holding Merchant Prince",
            description="Holder of an ancient warrant of trade, licensed to deal beyond the Throne's borders.",
            affinity_vector={"mass": 0.55, "thermodynamic": 0.10, "exotic": 0.30, "entropic": 0.05},
            parent_ids=["root_imperial"],
            child_ids=["imperial_navigator_patron"],
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="imperial_commissar",
            name="Commissar",
            clade="IMPERIAL",
            tier=2,
            role="Political Officer of the Fleet",
            description="Enforcer of discipline and the tithe; the last thing a deserter sees.",
            affinity_vector={"mass": 0.15, "thermodynamic": 0.25, "exotic": 0.05, "entropic": 0.55},
            parent_ids=["root_imperial"],
            child_ids=["imperial_lord_commissar"],
            min_credit_rating=540,
            min_crystals=1,
        ))
        self._add_node(PhylogeneticNode(
            id="imperial_navigator_patron",
            name="Navigator-House Patron",
            clade="IMPERIAL",
            tier=3,
            role="Dynastic Shipping Magnate",
            description="Patron of a Navigator house whose Goliaths carry the tithes of whole segmentums.",
            affinity_vector={"mass": 0.50, "thermodynamic": 0.10, "exotic": 0.35, "entropic": 0.05},
            parent_ids=["imperial_rogue_trader"],
            child_ids=["imperial_warrant_dynast"],
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="imperial_lord_commissar",
            name="Lord Commissar",
            clade="IMPERIAL",
            tier=3,
            role="Segmentum Fleet Commander",
            description="Commander of Imperial battle groups; the tithe is collected, or the world is made an example.",
            affinity_vector={"mass": 0.20, "thermodynamic": 0.20, "exotic": 0.05, "entropic": 0.55},
            parent_ids=["imperial_commissar"],
            child_ids=["imperial_lord_inquisitor"],
            min_credit_rating=660,
            min_crystals=3,
            min_net_equity=50000,
        ))
        self._add_node(PhylogeneticNode(
            id="imperial_warrant_dynast",
            name="Warrant-Dynast of the Throne",
            clade="IMPERIAL",
            tier=4,
            role="High Lord of Trade",
            description="A High Lord whose decree moves the tithe-fleets of the realm.",
            affinity_vector={"mass": 0.55, "thermodynamic": 0.10, "exotic": 0.30, "entropic": 0.05},
            parent_ids=["imperial_navigator_patron"],
            canopy_override="THRONE_DECREE_EXACTION",
            canopy_perk_title="Throne Decree of Exaction",
            canopy_perk_description="Summons every waiting tithe to the Fortress World at once, and draws a Throne stipend from the Imperial treasury.",
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
        ))
        self._add_node(PhylogeneticNode(
            id="imperial_lord_inquisitor",
            name="Lord Inquisitor",
            clade="IMPERIAL",
            tier=4,
            role="Hunter of Heretics",
            description="Answerable to no one but the Throne; the heretic, the mutant and the traitor fear this name.",
            affinity_vector={"mass": 0.15, "thermodynamic": 0.20, "exotic": 0.10, "entropic": 0.55},
            parent_ids=["imperial_lord_commissar"],
            canopy_override="PURGE_OF_THE_UNCLEAN",
            canopy_perk_title="Purge of the Unclean",
            canopy_perk_description="Every wanted outlaw and excommunicate in the sector is stripped of shields and fighters.",
            min_credit_rating=760,
            min_crystals=6,
            min_net_equity=200000,
            max_alignment=0.2,
        ))

        # =========================================================================
        # 6. LATERAL PRECURSOR CHIMERISM (Horizontal Mesh Grafts)
        # =========================================================================
        self._add_node(PhylogeneticNode(
            id="chimera_absolute_zero_alchemist",
            name="Absolute-Zero Alchemist",
            clade="CHIMERA",
            tier=3,
            role="Chimeric Sub-Zero Transmuter",
            description="Grafted transhumanist cyber-core synthesizing sub-zero quantum phonons with precursor elemental alchemy.",
            affinity_vector={"mass": 0.15, "thermodynamic": 0.40, "exotic": 0.40, "entropic": 0.05},
            parent_ids=["biotic_director", "plasmic_flux_warden", "cryo_glacial_arbiter"],
            child_ids=["chimera_quantum_archon"],
            is_lateral_hybrid=True,
            chimeric_cost_materials={"U": 10, "cryogenite": 15},
            min_experience=700,
            min_credit_rating=680,
            min_crystals=4,
            min_net_equity=75000,
        ))
        self._add_node(PhylogeneticNode(
            id="chimera_quantum_archon",
            name="Quantum Archon",
            clade="CHIMERA",
            tier=4,
            role="Master of Transmutation Paradoxes",
            description="Omnipresent chimeric consciousness commanding matter, cold logic, and corporate markets.",
            affinity_vector={"mass": 0.15, "thermodynamic": 0.45, "exotic": 0.35, "entropic": 0.05},
            parent_ids=["chimera_absolute_zero_alchemist"],
            canopy_override="THERMODYNAMIC_TRANSMUTATION_PARADOX",
            canopy_perk_title="Thermodynamic Transmutation Paradox",
            canopy_perk_description="Performs instant precursor transmutation of base metals into precious exotics without thermal heat or credit costs.",
            min_experience=1800,
            min_credit_rating=780,
            min_crystals=8,
            min_net_equity=300000,
        ))

    def _add_node(self, node: PhylogeneticNode) -> None:
        # Tier experience gates come from one pacing table (config), not per-node literals
        node.min_experience = PHYLOGENY_TIER_EXPERIENCE.get(node.tier, node.min_experience)
        if node.is_lateral_hybrid:
            node.min_experience += PHYLOGENY_CHIMERA_EXPERIENCE_BONUS
        self.nodes[node.id] = node

    def get_node(self, node_id: str) -> Optional[PhylogeneticNode]:
        return self.nodes.get(node_id)

    def get_root_node_for_captain(self, captain: Any) -> PhylogeneticNode:
        """Determines primordial root node based on captain clade and species taxonomy."""
        clade = getattr(captain, "clade", "BIOTIC").upper()
        species = getattr(captain, "species", "").lower()

        if clade == "IMPERIAL" or "imperial" in species:
            return self.nodes["root_imperial"]
        if "cryo" in species or "still" in species or clade == "CRYOGENIC":
            return self.nodes["root_cryo"]
        elif "lith" in species or "endolith" in species or clade == "LITHIC":
            return self.nodes["root_lithic"]
        elif "plasm" in species or "actino" in species or clade == "PLASMIC":
            return self.nodes["root_plasmic"]
        elif "void" in species or "umbra" in species or clade == "ANARCHY":
            return self.nodes["root_anarchy"]
        return self.nodes["root_biotic"]

    def record_activity_flux(
        self,
        captain: Any,
        mass_delta: float = 0.0,
        thermo_delta: float = 0.0,
        exotic_delta: float = 0.0,
        entropic_delta: float = 0.0,
    ) -> CochainFlux:
        """Records an action flux into the captain's cochain history."""
        flux_dict = getattr(captain, "cochain_flux", None)
        if not isinstance(flux_dict, dict):
            flux = CochainFlux()
        else:
            flux = CochainFlux.from_dict(flux_dict)

        flux.record_activity(mass_delta, thermo_delta, exotic_delta, entropic_delta)
        captain.cochain_flux = flux.to_dict()
        return flux

    def record_action_flux(self, captain: Any, action_name: str) -> Optional[CochainFlux]:
        """Records the canonical flux signature of a successful action, if it has one."""
        deltas = ACTION_FLUX.get(action_name)
        if not deltas:
            return None
        return self.record_activity_flux(captain, *deltas)

    def compute_branch_affinities(self, captain: Any) -> Dict[str, float]:
        """
        Calculates the dot product between captain's rolling cochain flux vector
        and each potential outgoing branch from their current node.
        """
        cur_node_id = getattr(captain, "phylogeny_node_id", None)
        if not cur_node_id or cur_node_id not in self.nodes:
            root = self.get_root_node_for_captain(captain)
            cur_node_id = root.id

        cur_node = self.nodes[cur_node_id]
        flux_dict = getattr(captain, "cochain_flux", {})
        flux = CochainFlux.from_dict(flux_dict)
        phi = flux.normalized()

        affinities: Dict[str, float] = {}
        for child_id in cur_node.child_ids:
            child = self.nodes.get(child_id)
            # Lateral hybrids are only reachable by Cartography Lab grafting, never natural divergence
            if not child or child.is_lateral_hybrid:
                continue
            psi = child.affinity_vector
            dot_product = (
                phi["mass"] * psi.get("mass", 0.0) +
                phi["thermodynamic"] * psi.get("thermodynamic", 0.0) +
                phi["exotic"] * psi.get("exotic", 0.0) +
                phi["entropic"] * psi.get("entropic", 0.0)
            )
            affinities[child_id] = round(dot_product, 4)

        return affinities

    def evaluate_ascension(self, captain: Any, kernel: Any = None) -> Dict[str, Any]:
        """
        Evaluates the captain's current phylogenetic standing, available branches,
        cochain affinities, and qualification for crystallization.
        """
        cur_node_id = getattr(captain, "phylogeny_node_id", None)
        if not cur_node_id or cur_node_id not in self.nodes:
            root = self.get_root_node_for_captain(captain)
            cur_node_id = root.id
            captain.phylogeny_node_id = cur_node_id

        cur_node = self.nodes[cur_node_id]
        affinities = self.compute_branch_affinities(captain)

        # Determine naturally pitched branch
        best_child_id = None
        if affinities:
            best_child_id = max(affinities, key=affinities.get)

        best_child = self.nodes.get(best_child_id) if best_child_id else None

        # Check invariant gates
        cur_exp = getattr(captain, "experience_score", 100)
        cur_cr = getattr(captain, "credit_rating", 500)
        cur_crystals = len(getattr(captain, "grown_basis", []))

        if kernel and hasattr(kernel, "market_manager"):
            cur_equity = kernel.market_manager.calculate_net_equity(captain, kernel)
        else:
            cur_equity = max(1000, getattr(captain, "credits", 0) - getattr(captain, "debt", 0))

        can_ascend = False
        unmet_reasons = []

        if not affinities:
            unmet_reasons.append("Already ascended to Canopy Sovereign leaf node (Maximum Rank).")
        elif best_child:
            exp_ok = cur_exp >= best_child.min_experience
            cr_ok = cur_cr >= best_child.min_credit_rating
            crystals_ok = cur_crystals >= best_child.min_crystals
            equity_ok = cur_equity >= best_child.min_net_equity

            if not exp_ok:
                unmet_reasons.append(f"Experience {cur_exp} < {best_child.min_experience}")
            if not cr_ok:
                unmet_reasons.append(f"Credit Rating {cur_cr} < {best_child.min_credit_rating}")
            if not crystals_ok:
                unmet_reasons.append(f"Grown Crystals {cur_crystals} < {best_child.min_crystals}")
            if not equity_ok:
                unmet_reasons.append(f"Net Equity {cur_equity:,} Cr < {best_child.min_net_equity:,} Cr")

            align_value = getattr(captain, "cosmic_alignment", 0.0)
            align_ok = ((best_child.min_alignment is None or align_value >= best_child.min_alignment)
                        and (best_child.max_alignment is None or align_value <= best_child.max_alignment))
            if not align_ok:
                if best_child.min_alignment is not None and align_value < best_child.min_alignment:
                    unmet_reasons.append(f"Alignment {align_value:+.2f} < {best_child.min_alignment:+.2f} (walk further into the Light)")
                else:
                    unmet_reasons.append(f"Alignment {align_value:+.2f} > {best_child.max_alignment:+.2f} (this path is closed to the Light)")

            can_ascend = exp_ok and cr_ok and crystals_ok and equity_ok and align_ok

        # Check lateral chimeric availability
        chimeric_available = []
        for n in self.nodes.values():
            if n.is_lateral_hybrid and cur_node.id in n.parent_ids:
                chimeric_available.append(n.to_dict())

        return {
            "current_node": cur_node.to_dict(),
            "best_branch": best_child.to_dict() if best_child else None,
            "affinities": affinities,
            "can_ascend": can_ascend,
            "unmet_reasons": unmet_reasons,
            "chimeric_available": chimeric_available,
            "canopy_override": cur_node.canopy_override,
            "canopy_perk_title": cur_node.canopy_perk_title,
            "canopy_perk_description": cur_node.canopy_perk_description,
        }

    def ascend(self, captain: Any, target_node_id: Optional[str] = None, kernel: Any = None) -> Tuple[bool, str]:
        """Crystallizes ascension to target node (or naturally pitched branch)."""
        eval_data = self.evaluate_ascension(captain, kernel)
        if not eval_data["can_ascend"]:
            reasons = "; ".join(eval_data.get("unmet_reasons", []))
            return False, f"Ascension invariants unmet: {reasons}"

        best_branch = eval_data.get("best_branch")
        chosen_id = target_node_id or (best_branch["id"] if best_branch else None)
        if not chosen_id or chosen_id not in self.nodes:
            return False, "No valid candidate branch to crystallize."

        # Emergent ascension: only the branch the cochain flux gravitates toward may crystallize
        affinities = eval_data["affinities"]
        if chosen_id not in affinities:
            return False, f"'{chosen_id}' is not a natural branch of your current node."
        if affinities[chosen_id] < max(affinities.values()):
            return False, (
                f"Cochain divergence does not pitch toward {self.nodes[chosen_id].name}. "
                f"Shift your activity flux to gravitate toward that branch."
            )

        new_node = self.nodes[chosen_id]
        old_node_id = getattr(captain, "phylogeny_node_id", "root_biotic")
        old_node = self.nodes.get(old_node_id)
        old_name = old_node.name if old_node else "Apprentice"

        # Crystallize new node
        captain.phylogeny_node_id = new_node.id
        captain.rank_tier = new_node.tier
        captain.clade = new_node.clade

        if not hasattr(captain, "unlocked_phylogeny_nodes") or not isinstance(captain.unlocked_phylogeny_nodes, list):
            captain.unlocked_phylogeny_nodes = []
        if new_node.id not in captain.unlocked_phylogeny_nodes:
            captain.unlocked_phylogeny_nodes.append(new_node.id)

        # Rewards based on tier
        thresholds = RANK_PROMOTION_THRESHOLDS.get(new_node.tier, {})
        cr_reward = thresholds.get("credit_reward", 2500 * new_node.tier)
        turns_reward = thresholds.get("turns_reward", 50)
        # Commission endowments are paid by the Federal Reserve, never minted
        fed = getattr(kernel, "federal_reserve", None) if kernel is not None else None
        cr_reward = min(cr_reward, fed.treasury) if fed is not None else 0
        if fed is not None:
            fed.treasury -= cr_reward
            fed.stats["rank_endowments"] += cr_reward
        captain.credits += cr_reward
        captain.turns_left = min(500, getattr(captain, "turns_left", 200) + turns_reward)
        captain.score += 750 * new_node.tier

        msg = (
            f"PHYLOGENETIC ASCENSION CONFIRMED: Diverged from {old_name} to {new_node.name} "
            f"[{new_node.clade} Tier {new_node.tier}]! Endowment: +{cr_reward:,} Cr, +{turns_reward} Turns. "
            f"Operational Role: {new_node.role}."
        )
        return True, msg

    def check_chimera_requirements(self, captain: Any, hybrid_node_id: str) -> Tuple[bool, str]:
        """Validates donor lineage and catalytic materials for a chimeric graft without consuming anything."""
        hybrid_node = self.nodes.get(hybrid_node_id)
        if not hybrid_node or not hybrid_node.is_lateral_hybrid:
            return False, f"CHIMERIC SYNTHESIS FAILED: Unknown or non-chimeric hybrid node '{hybrid_node_id}'."

        cur_node_id = getattr(captain, "phylogeny_node_id", "")
        if cur_node_id not in hybrid_node.parent_ids:
            return False, (
                f"CHIMERIC SYNTHESIS FAILED: Your current node ({cur_node_id}) is not a compatible "
                f"biological donor for {hybrid_node.name}."
            )

        cargo = getattr(getattr(captain, "ship", None), "cargo", None)
        elem_dict = getattr(cargo, "elements", {}) if cargo else {}
        for mat, qty in hybrid_node.chimeric_cost_materials.items():
            if elem_dict.get(mat, 0) < qty:
                return False, (
                    f"CHIMERIC SYNTHESIS FAILED: Grafting {hybrid_node.name} requires {qty} units of {mat} "
                    f"(Current stock: {elem_dict.get(mat, 0)} {mat})."
                )
        return True, ""

    def graft_precursor_chimera(self, captain: Any, hybrid_node_id: str, kernel: Any = None) -> Tuple[bool, str]:
        """
        Synthesizes a lateral Precursor Chimerism graft via Cartography Lab.
        Consumes catalytic materials (Uranium, Cryogenite) and bridges lineages horizontally.
        """
        ok, msg = self.check_chimera_requirements(captain, hybrid_node_id)
        if not ok:
            return False, msg

        hybrid_node = self.nodes[hybrid_node_id]
        cargo = getattr(getattr(captain, "ship", None), "cargo", None)
        elem_dict = getattr(cargo, "elements", {}) if cargo else {}
        reqs = hybrid_node.chimeric_cost_materials

        # Deduct materials
        for mat, qty in reqs.items():
            elem_dict[mat] -= qty
            if elem_dict[mat] <= 0:
                del elem_dict[mat]

        # Apply graft
        captain.phylogeny_node_id = hybrid_node.id
        captain.rank_tier = hybrid_node.tier
        captain.clade = hybrid_node.clade

        if not hasattr(captain, "chimeric_grafts") or not isinstance(captain.chimeric_grafts, list):
            captain.chimeric_grafts = []
        captain.chimeric_grafts.append(hybrid_node.id)

        msg = (
            f"PRECURSOR CHIMERISM SYNTHESIZED: Successfully grafted alien cochains! "
            f"Ascended to {hybrid_node.name} [Tier {hybrid_node.tier} Hybrid]. "
            f"Catalytic materials consumed: {', '.join(f'{q} {m}' for m, q in reqs.items())}."
        )
        return True, msg

    def execute_canopy_override(self, captain: Any, kernel: Any, **kwargs) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executes a physics-rewriting Canopy Invariant Override granted by an Apex Sovereign node.
        """
        cur_node_id = getattr(captain, "phylogeny_node_id", "")
        cur_node = self.nodes.get(cur_node_id)
        if not cur_node or not cur_node.canopy_override or cur_node.tier < 4:
            return False, "Canopy Invariant Overrides are only accessible to Tier 4 Apex Sovereigns.", {}

        override = cur_node.canopy_override
        sec_id = getattr(captain, "sector_id", 1)
        sec = kernel.sectors.get(sec_id) if kernel else None

        # 1. SEISMIC_MANIFOLD_COLLAPSE (Lithic Litharch)
        if override == "SEISMIC_MANIFOLD_COLLAPSE":
            # Fractures planetary crust and temporarily restructures local wormhole lanes
            if sec:
                deep_secs = [s.id for s in kernel.sectors.values() if s.id not in sec.warps and s.id != sec.id]
                new_warp = random.choice(deep_secs) if deep_secs else 99
                sec.warps.append(new_warp)
                collapsed = 0
                for planet in getattr(sec, "planets", []):
                    if getattr(planet, "owner_id", None) != captain.id and getattr(planet, "shields", 0) > 0:
                        planet.shields = 0
                        collapsed += 1
                captain.active_canopy_override = override
                msg = (
                    f"SEISMIC MANIFOLD COLLAPSE: Tectonic Litharch {captain.name} triggered a crustal fracture! "
                    f"Opened temporary sub-crustal wormhole fissure connecting Sector {sec.id:03d} to Sector {new_warp:03d}. "
                    f"{collapsed} hostile planetary defense ring(s) collapsed."
                )
                return True, msg, {"new_warp": new_warp, "shields_collapsed": collapsed}

        # 2. ENTROPY_ZERO_EQUILIBRIUM (Cryogenic Absolute Zero Mind)
        elif override == "ENTROPY_ZERO_EQUILIBRIUM":
            # Freezes thermal dissipation and resets ship heat
            if hasattr(kernel, "alchemy_manager"):
                kernel.alchemy_manager.heat_accumulated.pop(captain.id, None)
            msg = (
                f"ENTROPY ZERO EQUILIBRIUM: Absolute Zero Mind {captain.name} halted thermodynamic entropy in the sector! "
                f"Thermal signatures eliminated. Vessel is now invisible to sensor scans and Federal automated turrets."
            )
            captain.active_canopy_override = override
            return True, msg, {"stealth": True, "entropy": 0.0}

        # 3. SUBSPACE_SIGNATURE_SPOOF (Anarchy Shadow Hegemon)
        elif override == "SUBSPACE_SIGNATURE_SPOOF":
            # Lures merchant haulers to current sector
            if kernel and hasattr(kernel, "market_manager"):
                lured_count = 0
                for h in kernel.market_manager.trade_haulers.values():
                    h.current_sector = sec_id
                    lured_count += 1
                msg = (
                    f"SUBSPACE SIGNATURE SPOOF: Shadow Hegemon {captain.name} broadcast forged Federal safe-zone coordinates! "
                    f"Redirected {lured_count} automated commercial haulers directly into Sector {sec_id:03d} crosshairs."
                )
                captain.active_canopy_override = override
                return True, msg, {"haulers_lured": lured_count}

        # 4. IMPERIAL_SENATE_MONOPOLY (Biotic Galactic Archon)
        elif override == "IMPERIAL_SENATE_MONOPOLY":
            # Diverts Federal tariffs into sovereign treasury
            # Diverted from Federal revenues (a transfer from the Reserve, never minted)
            fed = getattr(kernel, "federal_reserve", None)
            loot = min(25000, fed.treasury) if fed is not None else 0
            if fed is not None:
                fed.treasury -= loot
            captain.credits += loot
            msg = (
                f"IMPERIAL SENATE MONOPOLY: Galactic Archon {captain.name} enacted an executive tariff decree! "
                f"Diverted +{loot:,} Credits from Sol Core commerce directly into sovereign accounts."
            )
            captain.active_canopy_override = override
            return True, msg, {"credits_diverted": loot}

        # 5. THERMODYNAMIC_SUPERNOVA_CATALYSIS (Plasmic Corona Sovereign)
        elif override == "THERMODYNAMIC_SUPERNOVA_CATALYSIS":
            captain.turns_left = min(500, captain.turns_left + 100)
            msg = (
                f"THERMODYNAMIC SUPERNOVA CATALYSIS: Corona Sovereign {captain.name} channeled direct solar fusion! "
                f"Synthesized +100 action turns with zero thermal engine dissipation."
            )
            captain.active_canopy_override = override
            return True, msg, {"turns_synthesized": 100}

        # 6. THRONE_DECREE_EXACTION (Imperial Warrant-Dynast)
        elif override == "THRONE_DECREE_EXACTION":
            factions = getattr(kernel, "factions", None)
            imp = factions.factions.get("IMPERIUM") if factions else None
            if imp is None:
                return False, "There is no Throne in this galaxy to decree in the name of.", {}
            fortress = factions._planet(kernel, imp.fortress_planet)
            hauled = 0
            if fortress is not None:
                for w in factions.worlds(kernel, "IMPERIUM"):
                    if w.tithe_manifest:
                        hauled += factions._deliver_tithe(kernel, imp, fortress, dict(w.tithe_manifest))
                        w.tithe_manifest = {}
            home = imp.vault.get(imp.currency, 0)
            stipend_local = min(int(home * 0.05), int(20000 * kernel.fx_market.rate(imp.currency)))
            imp.vault[imp.currency] = home - stipend_local
            stipend = kernel.fx_market.swap_to_sol(imp.currency, stipend_local) if stipend_local > 0 else 0
            captain.credits += stipend
            captain.active_canopy_override = override
            return True, (f"THRONE DECREE OF EXACTION: {hauled:,} units of tithe summoned to the Fortress World; "
                          f"a Throne stipend of {stipend:,} Cr is granted."), {"tithe_hauled": hauled, "stipend": stipend}

        # 7. PURGE_OF_THE_UNCLEAN (Imperial Lord Inquisitor)
        elif override == "PURGE_OF_THE_UNCLEAN":
            purged = []
            for cid in list(getattr(sec, "captains", [])):
                other = kernel.captains.get(cid)
                if other is None or other.id == captain.id:
                    continue
                if other.bounty > 0 or getattr(other, "heresy", 0) >= 3:
                    other.ship.shields = 0
                    other.ship.fighters = 0
                    purged.append(other.name)
            from xylarium.kernel import alignment
            alignment.deed(kernel, captain, "heresy_purge")
            captain.active_canopy_override = override
            return True, (f"PURGE OF THE UNCLEAN: {len(purged)} wanted vessel(s) stripped bare"
                          + (f" ({', '.join(purged[:4])})." if purged else ".")), {"purged": purged}

        return False, f"Canopy override '{override}' not executed.", {}

    def render_ascii_cladogram(self, captain: Any) -> str:
        """
        Renders an ASCII Phylogenetic Cladogram visualizing the captain's evolutionary path,
        branching options, cochain divergence vector, and canopy overrides.
        """
        cur_node_id = getattr(captain, "phylogeny_node_id", None)
        if not cur_node_id or cur_node_id not in self.nodes:
            cur_node_id = self.get_root_node_for_captain(captain).id

        cur_node = self.nodes[cur_node_id]
        flux_dict = getattr(captain, "cochain_flux", {})
        flux = CochainFlux.from_dict(flux_dict)
        phi = flux.normalized()
        affinities = self.compute_branch_affinities(captain)

        lines = [
            "=" * 78,
            "                    PHYLOGENETIC ASCENSION CLADOGRAM (DAG)                    ",
            "=" * 78,
            f"Lineage Clade: [{cur_node.clade}]  │  Current Node: [T{cur_node.tier}] {cur_node.name.upper()}",
            f"Operational Role: {cur_node.role}",
            "-" * 78,
            f"Rolling Action Flux Vector (Phi):",
            f"  [Φ_Mass: {phi['mass']:.2f} (Ores)]  [Φ_Thermo: {phi['thermodynamic']:.2f} (Energy)]  "
            f"[Φ_Exotic: {phi['exotic']:.2f} (Specie)]  [Φ_Entropy: {phi['entropic']:.2f} (Combat/Piracy)]",
            "-" * 78,
            "EVOLUTIONARY BRANCHES & INVARIANT GRAVITATION:",
        ]

        if not affinities:
            lines.append("  ★ APEX CANOPY SOVEREIGN REACHED - UNIVERSE PHYSICS OVERRIDE UNLOCKED ★")
            if cur_node.canopy_perk_title:
                lines.append(f"  Override: {cur_node.canopy_perk_title}")
                lines.append(f"  Effect:   {cur_node.canopy_perk_description}")
        else:
            for child_id in affinities:
                child = self.nodes[child_id]
                score = affinities[child_id]
                pct = int(score * 100)
                marker = "►► [GRAVITATING]" if score == max(affinities.values(), default=0.0) else "── [DIVERGENT]"
                lines.append(f"  {marker} {child.name} [Tier {child.tier}] ({pct}% Cochain Affinity)")
                lines.append(f"       Role: {child.role} │ Gates: Exp ≥ {child.min_experience}, Crystals ≥ {child.min_crystals}")

        # Chimeric Lateral Grafts
        chimera_branches = [
            n for n in self.nodes.values()
            if n.is_lateral_hybrid and cur_node.id in n.parent_ids
        ]
        if chimera_branches:
            lines.append("-" * 78)
            lines.append("LATERAL PRECURSOR CHIMERISM (Cartography Lab Graft Available):")
            for ch in chimera_branches:
                mats = ", ".join(f"{q} {m}" for m, q in ch.chimeric_cost_materials.items())
                lines.append(f"  ⚡ [CHIMERA GRAFT] {ch.name} [Tier {ch.tier} Hybrid]")
                lines.append(f"       Cost: {mats} + Precursor Cipher Solve")

        lines.append("=" * 78)
        return "\n".join(lines)


# Global singleton instance for easy import across kernel modules
PHYLOGENY_MANAGER = PhylogenyManager()
