"""
Xylarium Xenobiology & Alien Trophic Ecosystem Engine.

Governs non-sentient alien life, planetary trophic hierarchies, genetic polymer
architectures, bioprospecting specimen extraction, bioreactor culturing, and
transgenic gene-grafting across habitable and extreme planetary biospheres.

First-Principles Foundations:
1. Genetic Polymers:
   - PHOSPHO_RIBOSE: Aqueous solvent, nucleic acid backbone (260-360 K).
   - SILOXANE_PEPTIDE: Cryogenic methane/ammonia solvent (70-190 K).
   - BORON_NITRIDE_LATTICE: Superheated sulfuric/silicate solvent (360-650 K).
   - FLUOROCARBON_HELIX: Volcanic/halogen-dense acid solvent.
   - MAGNETO_IONIC_PLASMA: Magnetospheric helical solitons in gas giants.

2. Trophic Hierarchies & Lindeman Thermodynamics:
   - Primary Producers (T1): Solar phototrophs, mineral lithotrophs, radiotrophs.
   - Primary Consumers (T2): Grazers, filter-feeders, lithophages.
   - Apex Xenopredators (T3): Kinetic ambushers, chitinous swarms, bioelectric hunters.
   - Decomposers (T0): Mycelial decomposers, bio-catalytic recylers.
   - Trophic efficiency eta ~ 0.10 (Lindeman's thermodynamic trophic transfer).
   - Shannon Biodiversity Index: H = -sum(p_i * ln(p_i)).
"""

import math
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet
from xylarium.config import (
    XP_XENOBIOLOGY_SURVEY,
    XP_XENOBIOLOGY_SAMPLE,
    XP_XENOBIOLOGY_CULTURE,
    XP_XENOBIOLOGY_GRAFT,
)


class PolymerBackbone(str, Enum):
    PHOSPHO_RIBOSE = "PHOSPHO_RIBOSE"
    SILOXANE_PEPTIDE = "SILOXANE_PEPTIDE"
    BORON_NITRIDE_LATTICE = "BORON_NITRIDE_LATTICE"
    FLUOROCARBON_HELIX = "FLUOROCARBON_HELIX"
    MAGNETO_IONIC_PLASMA = "MAGNETO_IONIC_PLASMA"


class TrophicLevel(str, Enum):
    PRODUCER = "PRODUCER"       # T1: Autotrophic solar/lithic synthesis
    GRAZER = "GRAZER"           # T2: Herbivore / lithophage / filter feeder
    PREDATOR = "PREDATOR"       # T3: Apex xenopredator / carnivore
    DECOMPOSER = "DECOMPOSER"   # T0: Mycelial / catalytic recycler


@dataclass
class XenoTaxon:
    id: str
    name: str
    scientific_name: str
    trophic_level: TrophicLevel
    feeding_strategy: str
    backbone: PolymerBackbone
    biomass_share: float          # p_i in Shannon index
    metabolite: str               # Extractable commodity symbol
    metabolite_yield: int         # Yield units per sample run
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "scientific_name": self.scientific_name,
            "trophic_level": self.trophic_level.value,
            "feeding_strategy": self.feeding_strategy,
            "backbone": self.backbone.value,
            "biomass_share": round(self.biomass_share, 4),
            "metabolite": self.metabolite,
            "metabolite_yield": self.metabolite_yield,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "XenoTaxon":
        return cls(
            id=data["id"],
            name=data["name"],
            scientific_name=data["scientific_name"],
            trophic_level=TrophicLevel(data["trophic_level"]),
            feeding_strategy=data["feeding_strategy"],
            backbone=PolymerBackbone(data["backbone"]),
            biomass_share=float(data.get("biomass_share", 0.1)),
            metabolite=data["metabolite"],
            metabolite_yield=int(data.get("metabolite_yield", 2)),
            description=data.get("description", ""),
        )


@dataclass
class XenoEcosystem:
    planet_id: str
    backbone: PolymerBackbone
    taxa: List[XenoTaxon] = field(default_factory=list)
    shannon_entropy: float = 1.5
    trophic_efficiency: float = 0.10
    native_biomass_kg_m2: float = 4.5
    grafted_traits: List[str] = field(default_factory=list)
    surveyed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planet_id": self.planet_id,
            "backbone": self.backbone.value,
            "taxa": [t.to_dict() for t in self.taxa],
            "shannon_entropy": round(self.shannon_entropy, 3),
            "trophic_efficiency": round(self.trophic_efficiency, 3),
            "native_biomass_kg_m2": round(self.native_biomass_kg_m2, 2),
            "grafted_traits": list(self.grafted_traits),
            "surveyed": self.surveyed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "XenoEcosystem":
        return cls(
            planet_id=data["planet_id"],
            backbone=PolymerBackbone(data.get("backbone", PolymerBackbone.PHOSPHO_RIBOSE.value)),
            taxa=[XenoTaxon.from_dict(t) for t in data.get("taxa", [])],
            shannon_entropy=float(data.get("shannon_entropy", 1.5)),
            trophic_efficiency=float(data.get("trophic_efficiency", 0.10)),
            native_biomass_kg_m2=float(data.get("native_biomass_kg_m2", 4.5)),
            grafted_traits=list(data.get("grafted_traits", [])),
            surveyed=bool(data.get("surveyed", False)),
        )


@dataclass
class XenoCultureRecipe:
    id: str
    name: str
    inputs: Dict[str, int]
    outputs: Dict[str, int]
    catalyst_heat: float
    description: str


XENO_CULTURE_RECIPES: Dict[str, XenoCultureRecipe] = {
    "ADAPTIVE_BIOMASS": XenoCultureRecipe(
        id="ADAPTIVE_BIOMASS",
        name="Adaptive Biomass Fermentation",
        inputs={"XENOPROTEIN": 2, "ORGANICS": 2},
        outputs={"ORGANICS": 6},
        catalyst_heat=8.0,
        description="Hydrolyzes dense xenoprotein peptide folds into accelerated organic agricultural nutrients.",
    ),
    "CRYO_STABILIZER": XenoCultureRecipe(
        id="CRYO_STABILIZER",
        name="Cryo-Protective Solenoid Annealing",
        inputs={"CRYOPROTECTANT": 2, "cryogenite": 1},
        outputs={"M1_SUPERCONDUCTOR": 2},
        catalyst_heat=12.0,
        description="Infuses superconducting coils with biological antifreeze enzymes to prevent thermal quench.",
    ),
    "BIO_COMPOSITE_ARMOR": XenoCultureRecipe(
        id="BIO_COMPOSITE_ARMOR",
        name="Self-Healing Chitin-Lattice Sintering",
        inputs={"BIO_CHITIN": 3, "Fe": 1},
        outputs={"ferrolattice": 2},
        catalyst_heat=14.0,
        description="Bio-mineralizes ductile chitin polymers across iron scaffolding into regenerative ferrolattice.",
    ),
    "SYNAPTIC_NEUROGEL": XenoCultureRecipe(
        id="SYNAPTIC_NEUROGEL",
        name="Synaptic Neuro-Spore Warp Matrix",
        inputs={"NEURO_SPORE": 2, "H2O": 1},
        outputs={"M4_WARP_CORE": 1},
        catalyst_heat=18.0,
        description="Cultivates hyper-connected neural mycelia into warp core navigational cognitive matrices.",
    ),
    "RAD_SHIELD_MATRIX": XenoCultureRecipe(
        id="RAD_SHIELD_MATRIX",
        name="Radiotrophic Melanin Neutron Baffle",
        inputs={"RADIOTROPHIC_MELANIN": 2, "U": 1},
        outputs={"M3_ENGINE_MANIFOLD": 2},
        catalyst_heat=15.0,
        description="Stabilizes engine exhaust manifolds with gamma-absorbing radiotrophic biological polymers.",
    ),
    "ENZYME_CATALYSIS": XenoCultureRecipe(
        id="ENZYME_CATALYSIS",
        name="Piezo-Enzymatic Ore Dissolution",
        inputs={"PIEZO_ENZYME": 2, "ORE": 2},
        outputs={"Ti": 3},
        catalyst_heat=10.0,
        description="Utilizes high-pressure barophilic enzymes to leach pure titanium from raw crushed ores.",
    ),
}


# ----------------------------------------------------------------------
# Deterministic Procedural Ecosystem Generator
# ----------------------------------------------------------------------

def _planet_seed_hash(planet_id: str, salt: str = "") -> int:
    h = hashlib.sha256(f"{planet_id}:{salt}".encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _determine_backbone(planet: Planet) -> PolymerBackbone:
    ptype = (planet.planet_type or "").upper()
    soc = getattr(planet, "society", {}) or {}
    t_surf = float(soc.get("surface_t", 288.15))

    if ptype == "GAS_GIANT":
        return PolymerBackbone.MAGNETO_IONIC_PLASMA
    elif ptype == "VOLCANIC" or t_surf > 400.0:
        return PolymerBackbone.BORON_NITRIDE_LATTICE
    elif ptype == "BARREN" or t_surf < 180.0:
        return PolymerBackbone.SILOXANE_PEPTIDE
    elif "HALOGEN" in ptype or "ACID" in ptype:
        return PolymerBackbone.FLUOROCARBON_HELIX
    else:
        return PolymerBackbone.PHOSPHO_RIBOSE


def generate_xeno_ecosystem(planet: Planet, kernel: Any = None) -> XenoEcosystem:
    """
    Deterministically generates the native xenobiological ecosystem for a world
    based on its planetary classification, orbital thermodynamics, and surface geology.
    """
    soc = getattr(planet, "society", None)
    if soc is not None and "xeno_ecosystem" in soc:
        data = soc["xeno_ecosystem"]
        if isinstance(data, dict):
            return XenoEcosystem.from_dict(data)

    backbone = _determine_backbone(planet)
    p_seed = _planet_seed_hash(planet.id, "ecosystem")
    ptype = (planet.planet_type or "TERRESTRIAL").upper()

    taxa: List[XenoTaxon] = []

    if backbone == PolymerBackbone.PHOSPHO_RIBOSE:
        taxa = [
            XenoTaxon(
                id="TAXON-P1",
                name="Canopy Chlorophyte",
                scientific_name=f"Virescens {planet.name[:4]}ia",
                trophic_level=TrophicLevel.PRODUCER,
                feeding_strategy="Stellar Phototropism",
                backbone=backbone,
                biomass_share=0.55,
                metabolite="XENOPROTEIN",
                metabolite_yield=4,
                description="High-albedo leafy autotrophs forming dense continental canopies.",
            ),
            XenoTaxon(
                id="TAXON-G1",
                name="Armored Sylvatherium",
                scientific_name=f"Chitinovore {planet.name[:4]}us",
                trophic_level=TrophicLevel.GRAZER,
                feeding_strategy="Herbivorous Grazing & Bio-Mineral Chewing",
                backbone=backbone,
                biomass_share=0.25,
                metabolite="BIO_CHITIN",
                metabolite_yield=3,
                description="Quadrupedal grazers protected by interlocking biomorphic chitin scales.",
            ),
            XenoTaxon(
                id="TAXON-A1",
                name="Scythe-Stalker",
                scientific_name=f"Apex raptor {planet.name[:4]}ensis",
                trophic_level=TrophicLevel.PREDATOR,
                feeding_strategy="Kinetic Ambush & Neuro-Venom",
                backbone=backbone,
                biomass_share=0.08,
                metabolite="NEURO_SPORE",
                metabolite_yield=2,
                description="Apex pack predators utilizing bio-luminescent synaptic pulses to coordinate ambushes.",
            ),
            XenoTaxon(
                id="TAXON-D1",
                name="Abyssal Mycelial Veil",
                scientific_name=f"Saprophytum {planet.name[:4]}um",
                trophic_level=TrophicLevel.DECOMPOSER,
                feeding_strategy="Cellular Lysis & Nutrient Catalysis",
                backbone=backbone,
                biomass_share=0.12,
                metabolite="PIEZO_ENZYME",
                metabolite_yield=2,
                description="Underground fungal mats spanning planetary crusts, recycling dead biomass.",
            ),
        ]
    elif backbone == PolymerBackbone.SILOXANE_PEPTIDE:
        taxa = [
            XenoTaxon(
                id="TAXON-P1",
                name="Cryo-Methanotrophic Lichen",
                scientific_name=f"Gelidophyta {planet.name[:4]}a",
                trophic_level=TrophicLevel.PRODUCER,
                feeding_strategy="Hydrocarbon Reduction at 110K",
                backbone=backbone,
                biomass_share=0.58,
                metabolite="CRYOPROTECTANT",
                metabolite_yield=4,
                description="Silicon-polyether filaments thriving in sub-zero liquid methane rivers.",
            ),
            XenoTaxon(
                id="TAXON-G1",
                name="Glacial Lithophage",
                scientific_name=f"Silicorunner {planet.name[:4]}i",
                trophic_level=TrophicLevel.GRAZER,
                feeding_strategy="Solid Ammonia Scraping",
                backbone=backbone,
                biomass_share=0.24,
                metabolite="CRYOPROTECTANT",
                metabolite_yield=3,
                description="Low-temperature crustaceans with flexible siloxane carapaces.",
            ),
            XenoTaxon(
                id="TAXON-A1",
                name="Frost-Phantom Stalker",
                scientific_name=f"Cryohunter {planet.name[:4]}is",
                trophic_level=TrophicLevel.PREDATOR,
                feeding_strategy="Thermal Absorption Predation",
                backbone=backbone,
                biomass_share=0.08,
                metabolite="NEURO_SPORE",
                metabolite_yield=2,
                description="Apex predators that absorb heat directly from prey bodies.",
            ),
            XenoTaxon(
                id="TAXON-D1",
                name="Permafrost Silicate Dissolver",
                scientific_name=f"Frigidobacter {planet.name[:4]}",
                trophic_level=TrophicLevel.DECOMPOSER,
                feeding_strategy="Enzymatic Mineral Fracture",
                backbone=backbone,
                biomass_share=0.10,
                metabolite="PIEZO_ENZYME",
                metabolite_yield=2,
                description="Sub-surface extremophile colonies converting glassy silicates into bio-salts.",
            ),
        ]
    elif backbone == PolymerBackbone.BORON_NITRIDE_LATTICE:
        taxa = [
            XenoTaxon(
                id="TAXON-P1",
                name="Pyrosynthetic Basalt Coral",
                scientific_name=f"Ignicorallum {planet.name[:4]}",
                trophic_level=TrophicLevel.PRODUCER,
                feeding_strategy="Geothermal Flux & Magma Chemo-Synthesis",
                backbone=backbone,
                biomass_share=0.54,
                metabolite="RADIOTROPHIC_MELANIN",
                metabolite_yield=4,
                description="Covalent boron-nitride crystalline structures rooted directly in lava fissures.",
            ),
            XenoTaxon(
                id="TAXON-G1",
                name="Slag-Shelled Megapede",
                scientific_name=f"Lavamantis {planet.name[:4]}ii",
                trophic_level=TrophicLevel.GRAZER,
                feeding_strategy="Heavy Metal Ingestion & Sulfur Digestion",
                backbone=backbone,
                biomass_share=0.26,
                metabolite="BIO_CHITIN",
                metabolite_yield=3,
                description="Multi-legged organisms clad in vitrified ceramic slag carapaces.",
            ),
            XenoTaxon(
                id="TAXON-A1",
                name="Infernal Pyrosaur",
                scientific_name=f"Thermovore {planet.name[:4]}us",
                trophic_level=TrophicLevel.PREDATOR,
                feeding_strategy="High-Temperature Bio-Plasma Discharge",
                backbone=backbone,
                biomass_share=0.09,
                metabolite="PIEZO_ENZYME",
                metabolite_yield=2,
                description="Massive apex predators with internal high-temperature combustion chambers.",
            ),
            XenoTaxon(
                id="TAXON-D1",
                name="Thermophilic Sulfur Slime",
                scientific_name=f"Pyromonas {planet.name[:4]}",
                trophic_level=TrophicLevel.DECOMPOSER,
                feeding_strategy="Sulfur & Boron Reduction",
                backbone=backbone,
                biomass_share=0.11,
                metabolite="XENOPROTEIN",
                metabolite_yield=2,
                description="Microscopic bacterial carpets oxidizing sulfur fumes across volcanic vents.",
            ),
        ]
    elif backbone == PolymerBackbone.MAGNETO_IONIC_PLASMA:
        taxa = [
            XenoTaxon(
                id="TAXON-P1",
                name="Stratospheric Aurora Kelp",
                scientific_name=f"Plasmophyta {planet.name[:4]}",
                trophic_level=TrophicLevel.PRODUCER,
                feeding_strategy="Planetary Magnetosphere Induction",
                backbone=backbone,
                biomass_share=0.56,
                metabolite="RADIOTROPHIC_MELANIN",
                metabolite_yield=4,
                description="Vast bio-magnetic sheets floating in gas giant cloud decks, absorbing ion flux.",
            ),
            XenoTaxon(
                id="TAXON-G1",
                name="Helium Siphonophore",
                scientific_name=f"Vorticozoon {planet.name[:4]}",
                trophic_level=TrophicLevel.GRAZER,
                feeding_strategy="Atmospheric Ram-Scooping & Ion Grazing",
                backbone=backbone,
                biomass_share=0.25,
                metabolite="XENOPROTEIN",
                metabolite_yield=3,
                description="Kilometer-long buoyant siphonophores drifting along jet streams.",
            ),
            XenoTaxon(
                id="TAXON-A1",
                name="Thunder-Leviathan",
                scientific_name=f"Electrotyphon {planet.name[:4]}",
                trophic_level=TrophicLevel.PREDATOR,
                feeding_strategy="Megavolt Arc Hunting",
                backbone=backbone,
                biomass_share=0.08,
                metabolite="NEURO_SPORE",
                metabolite_yield=2,
                description="Apex predators that stun aerial herds using supercharged bio-lightning discharges.",
            ),
            XenoTaxon(
                id="TAXON-D1",
                name="Vortex Decomposition Net",
                scientific_name=f"Ionovorus {planet.name[:4]}",
                trophic_level=TrophicLevel.DECOMPOSER,
                feeding_strategy="Charge Neutralization & Radical Dissipation",
                backbone=backbone,
                biomass_share=0.11,
                metabolite="PIEZO_ENZYME",
                metabolite_yield=2,
                description="Electrostatic filaments sweeping falling cellular debris in downdrafts.",
            ),
        ]
    else:  # FLUOROCARBON_HELIX or fallback
        taxa = [
            XenoTaxon(
                id="TAXON-P1",
                name="Fluorine Acid Alga",
                scientific_name=f"Halophyta {planet.name[:4]}",
                trophic_level=TrophicLevel.PRODUCER,
                feeding_strategy="Halogen Phototropism",
                backbone=backbone,
                biomass_share=0.55,
                metabolite="RADIOTROPHIC_MELANIN",
                metabolite_yield=4,
                description="Super-inert fluorinated poly-chains thriving in concentrated planetary acids.",
            ),
            XenoTaxon(
                id="TAXON-G1",
                name="Acid-Skimmer Beetle",
                scientific_name=f"Teflonozoon {planet.name[:4]}",
                trophic_level=TrophicLevel.GRAZER,
                feeding_strategy="Algal Mats Scraping",
                backbone=backbone,
                biomass_share=0.25,
                metabolite="BIO_CHITIN",
                metabolite_yield=3,
                description="Inert polymer-shelled insects that skim surface acid ponds.",
            ),
            XenoTaxon(
                id="TAXON-A1",
                name="Corrosive Hydra",
                scientific_name=f"Caustica {planet.name[:4]}",
                trophic_level=TrophicLevel.PREDATOR,
                feeding_strategy="Enzymatic Dissolution Trapping",
                backbone=backbone,
                biomass_share=0.08,
                metabolite="PIEZO_ENZYME",
                metabolite_yield=2,
                description="Tentacled ambush predators that spray hydrofluoric digestive fluids.",
            ),
            XenoTaxon(
                id="TAXON-D1",
                name="Halogen Recycler Mold",
                scientific_name=f"Halofungus {planet.name[:4]}",
                trophic_level=TrophicLevel.DECOMPOSER,
                feeding_strategy="Acid Salt Mineralization",
                backbone=backbone,
                biomass_share=0.12,
                metabolite="XENOPROTEIN",
                metabolite_yield=2,
                description="Porous molds breaking down fluorocarbon waste into inert sediments.",
            ),
        ]

    # Calculate Shannon Biodiversity Index
    shannon = -sum(t.biomass_share * math.log(max(1e-6, t.biomass_share)) for t in taxa)

    eco = XenoEcosystem(
        planet_id=planet.id,
        backbone=backbone,
        taxa=taxa,
        shannon_entropy=shannon,
        trophic_efficiency=0.10,
        native_biomass_kg_m2=float(4.0 + (p_seed % 30) * 0.1),
        grafted_traits=[],
        surveyed=False,
    )

    if soc is not None:
        soc["xeno_ecosystem"] = eco.to_dict()

    return eco


# ----------------------------------------------------------------------
# Core Actions: Survey, Sample, Culture, Graft
# ----------------------------------------------------------------------

def survey_xenobiology(captain: Captain, planet: Planet, kernel: Any = None) -> ActionResult:
    """
    Executes a planetary xenobiology spectrographic survey, uncovering the native
    food web, polymer backbone, trophic hierarchy, and extractable metabolites.
    """
    eco = generate_xeno_ecosystem(planet, kernel)
    eco.surveyed = True

    if getattr(planet, "society", None) is not None:
        planet.society["xeno_ecosystem"] = eco.to_dict()

    from xylarium.kernel.experience import ExperienceManager
    ExperienceManager.award(captain, "science", XP_XENOBIOLOGY_SURVEY, kernel, key=f"xeno_survey:{planet.id}")

    taxa_summary = ", ".join(f"{t.name} ({t.trophic_level.value})" for t in eco.taxa)
    msg = (
        f"XENOBIOLOGY SURVEY COMPLETE: {planet.name} analyzed! "
        f"Backbone: [{eco.backbone.value}]. Shannon Biodiversity H = {eco.shannon_entropy:.2f}. "
        f"Native Taxa: {taxa_summary}."
    )
    if kernel and hasattr(kernel, "action_logs"):
        kernel.action_logs.append(f"[XENO] {captain.name} surveyed alien ecology on {planet.name}.")

    return ActionResult(
        True,
        ActionType.XENOBIOLOGY_SURVEY,
        msg,
        data={"ecosystem": eco.to_dict()},
    )


def sample_xenobiology(
    captain: Captain,
    planet: Planet,
    taxon_id: Optional[str] = None,
    kernel: Any = None,
) -> ActionResult:
    """
    Dispatches bioprospecting survey drones and scientific landing parties to extract
    viable xenobiological specimens and extremophile metabolites.
    """
    eco = generate_xeno_ecosystem(planet, kernel)
    if not eco.surveyed:
        eco.surveyed = True
        if getattr(planet, "society", None) is not None:
            planet.society["xeno_ecosystem"] = eco.to_dict()

    # Locate chosen taxon or default to primary producer
    chosen_taxon = None
    if taxon_id:
        t_query = taxon_id.strip().upper()
        for t in eco.taxa:
            if t.id.upper() == t_query or t_query in t.name.upper():
                chosen_taxon = t
                break
    if not chosen_taxon:
        chosen_taxon = eco.taxa[0]

    yield_units = chosen_taxon.metabolite_yield

    # Check for Biosphere Vessel or Bio-containment bonus
    ship_hull = getattr(captain.ship, "hull_class", "")
    if ship_hull == "BIOSPHERE_VESSEL":
        yield_units = int(yield_units * 1.5)

    cargo = captain.ship.cargo
    if getattr(cargo, "available_space", 30) < yield_units:
        return ActionResult(
            False,
            ActionType.XENOBIOLOGY_SAMPLE,
            f"Insufficient hold space: Sampling requires {yield_units} free units (Holds free: {cargo.available_space}).",
        )

    # Deposit metabolite commodity into ship hold
    metab = chosen_taxon.metabolite
    if metab in ("ORE", "ORGANICS", "EQUIPMENT"):
        setattr(cargo, metab.lower(), getattr(cargo, metab.lower(), 0) + yield_units)
    else:
        cargo.elements[metab] = cargo.elements.get(metab, 0) + yield_units

    from xylarium.kernel.experience import ExperienceManager
    ExperienceManager.award(captain, "science", XP_XENOBIOLOGY_SAMPLE, kernel, key=f"xeno_sample:{planet.id}:{chosen_taxon.id}")

    msg = (
        f"BIOPROSPECTING SUCCESS: Extracted +{yield_units} [{metab}] specimens from {chosen_taxon.name} "
        f"({chosen_taxon.scientific_name}) in {planet.name}'s biosphere! Loaded into scientific holds."
    )
    if kernel and hasattr(kernel, "action_logs"):
        kernel.action_logs.append(f"[XENO] {captain.name} sampled {chosen_taxon.name} (+{yield_units} {metab}).")

    return ActionResult(
        True,
        ActionType.XENOBIOLOGY_SAMPLE,
        msg,
        data={"taxon": chosen_taxon.to_dict(), "metabolite": metab, "units_yielded": yield_units},
    )


def culture_xenobiology(
    captain: Captain,
    recipe_id: str,
    kernel: Any = None,
) -> ActionResult:
    """
    Cultivates and synthesizes advanced biochemical compounds in ship biological
    containment bays or planetary bioreactors.
    """
    rec_key = recipe_id.strip().upper()
    recipe = XENO_CULTURE_RECIPES.get(rec_key)
    if not recipe:
        available = ", ".join(XENO_CULTURE_RECIPES.keys())
        return ActionResult(
            False,
            ActionType.XENOBIOLOGY_CULTURE,
            f"Unknown xenobiology culture recipe '{recipe_id}'. Available: {available}",
        )

    cargo = captain.ship.cargo

    # 1. Check inputs
    from xylarium.kernel.alchemy import _get_cargo_avail, _deduct_cargo, _add_cargo
    for inp, qty in recipe.inputs.items():
        avail = _get_cargo_avail(cargo, inp)
        if avail < qty:
            return ActionResult(
                False,
                ActionType.XENOBIOLOGY_CULTURE,
                f"Insufficient input [{inp}]: {qty} units required, {avail} available in hold.",
            )

    # 2. Check hold space delta
    in_sum = sum(recipe.inputs.values())
    out_sum = sum(recipe.outputs.values())
    delta = out_sum - in_sum
    if delta > 0 and getattr(cargo, "available_space", 30) < delta:
        return ActionResult(
            False,
            ActionType.XENOBIOLOGY_CULTURE,
            "Holds full! Insufficient capacity for synthesized biochemical products.",
        )

    # 3. Deduct inputs
    for inp, qty in recipe.inputs.items():
        _deduct_cargo(cargo, inp, qty)

    # 4. Add outputs
    for out, qty in recipe.outputs.items():
        _add_cargo(cargo, out, qty)

    from xylarium.kernel.experience import ExperienceManager
    ExperienceManager.award(captain, "industry", XP_XENOBIOLOGY_CULTURE, kernel, key=f"xeno_culture:{recipe.id}")

    out_str = ", ".join(f"+{v} [{k}]" for k, v in recipe.outputs.items())
    msg = f"BIOREACTOR CULTURING SUCCESS: {recipe.name} completed! Yielded {out_str}."
    if kernel and hasattr(kernel, "action_logs"):
        kernel.action_logs.append(f"[XENO] {captain.name} cultured {recipe.name} ({out_str}).")

    return ActionResult(
        True,
        ActionType.XENOBIOLOGY_CULTURE,
        msg,
        data={"recipe_id": recipe.id, "outputs": dict(recipe.outputs)},
    )


def graft_xenobiology(
    captain: Captain,
    planet: Planet,
    metabolite: str,
    kernel: Any = None,
) -> ActionResult:
    """
    Executes transgenic gene grafting of native extremophile metabolites into a
    colonized world's agricultural and ecological stock.
    Permanent boosts:
    - CRYOPROTECTANT: +30% agricultural yield in cold biomes (<260K).
    - RADIOTROPHIC_MELANIN: +0.20 habitability, shields against radiation.
    - PIEZO_ENZYME: +25% mineral extraction rate on high-gravity worlds.
    - XENOPROTEIN: +20% carrying capacity and +10 colony morale.
    - BIO_CHITIN: +50 colony max shields.
    - NEURO_SPORE: +25% planetary research output.
    """
    m_key = metabolite.strip().upper()
    valid_metabolites = {
        "CRYOPROTECTANT": "Cryo-Tolerance Adaptation (+30% sub-zero crop yield)",
        "RADIOTROPHIC_MELANIN": "Radiotrophic Melanin Inoculation (+0.20 Habitability)",
        "PIEZO_ENZYME": "Piezo-Enzymatic Mineral Digestion (+25% mining output)",
        "XENOPROTEIN": "Hyper-Nutrient Xenoprotein Splicing (+20% carrying capacity, +10 morale)",
        "BIO_CHITIN": "Bio-Adaptive Chitin Carapace (+50 colony shields)",
        "NEURO_SPORE": "Synaptic Neuro-Spore Inoculation (+25% research yield)",
    }
    if m_key not in valid_metabolites:
        available = ", ".join(valid_metabolites.keys())
        return ActionResult(
            False,
            ActionType.XENOBIOLOGY_GRAFT,
            f"Invalid metabolite for gene grafting '{metabolite}'. Choose from: {available}",
        )

    cargo = captain.ship.cargo
    from xylarium.kernel.alchemy import _get_cargo_avail, _deduct_cargo
    avail = _get_cargo_avail(cargo, m_key)
    if avail < 2:
        return ActionResult(
            False,
            ActionType.XENOBIOLOGY_GRAFT,
            f"Transgenic grafting requires at least 2 units of [{m_key}] (You have {avail}).",
        )

    eco = generate_xeno_ecosystem(planet, kernel)
    if m_key in eco.grafted_traits:
        return ActionResult(
            False,
            ActionType.XENOBIOLOGY_GRAFT,
            f"{planet.name} has already incorporated the [{m_key}] transgenic trait.",
        )

    # Deduct 2 units of metabolite
    _deduct_cargo(cargo, m_key, 2)

    # Apply permanent benefits
    eco.grafted_traits.append(m_key)
    soc = getattr(planet, "society", {}) or {}
    soc["xeno_ecosystem"] = eco.to_dict()

    if m_key == "CRYOPROTECTANT":
        soc["fertility"] = min(3.0, float(soc.get("fertility", 1.0)) + 0.30)
    elif m_key == "RADIOTROPHIC_MELANIN":
        planet.habitability = min(1.5, float(getattr(planet, "habitability", 1.0)) + 0.20)
    elif m_key == "PIEZO_ENZYME":
        soc["mining_efficiency"] = float(soc.get("mining_efficiency", 1.0)) + 0.25
    elif m_key == "XENOPROTEIN":
        soc["carrying_capacity_mult"] = float(soc.get("carrying_capacity_mult", 1.0)) + 0.20
        planet.morale = min(100, planet.morale + 10)
    elif m_key == "BIO_CHITIN":
        planet.max_shields += 50
        planet.shields += 50
    elif m_key == "NEURO_SPORE":
        soc["research_bonus_pct"] = int(soc.get("research_bonus_pct", 0)) + 25

    from xylarium.kernel.experience import ExperienceManager
    ExperienceManager.award(captain, "science", XP_XENOBIOLOGY_GRAFT, kernel, key=f"xeno_graft:{planet.id}:{m_key}")

    trait_desc = valid_metabolites[m_key]
    msg = (
        f"TRANSGENIC GRAFT RATIFIED: Inoculated {planet.name}'s agricultural biomes with 2x [{m_key}]! "
        f"Benefit conferred: {trait_desc}."
    )
    if kernel and hasattr(kernel, "action_logs"):
        kernel.action_logs.append(f"[XENO] {captain.name} grafted [{m_key}] on {planet.name}.")

    return ActionResult(
        True,
        ActionType.XENOBIOLOGY_GRAFT,
        msg,
        data={"planet_id": planet.id, "trait": m_key, "grafted_traits": list(eco.grafted_traits)},
    )
