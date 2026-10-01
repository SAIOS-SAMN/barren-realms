"""
Civilization Intelligence and Taxon Tier Engine for Xylarium.
Ported from Netstratum (/opt/netstratum/engine/cfe/src/almanac/taxon_table.rs,
/opt/netstratum/engine/conductor/src/polities.rs, and civic.rs).

Implements:
- 13 Class Tiers (archetype words and sigils)
- Clade taxonomy (legacy 1..=20 and expansion)
- Founding Polities from Netstratum Aeon 1 roster
- Homological Economy: Tension Vector δ = Demand - Supply
- Autonomous Civic Projects and Periodic Element Research
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import random
from xylarium.kernel import matter
from xylarium.kernel.elements import PeriodicTable, PeriodicElement

# 13 Class Archetype Sigils and Words
CLASS_ARCHETYPES: Dict[int, Tuple[str, str]] = {
    0: ("∅", "unclassed"),
    1: ("⬡", "biotic-swarm"),
    2: ("◈", "geodic-lithovore"),
    3: ("◐", "metashifter"),
    4: ("≋", "telepathic-resonant"),
    5: ("⊚", "pelagic-aerial"),
    6: ("∿", "plasma-field"),
    7: ("▲", "apex-solitary"),
    8: ("⟺", "corridor-nomad"),
    9: ("▼", "abyssal-pressure"),
    10: ("◆", "crystal-mind"),
    11: ("※", "void-swarm"),
    12: ("❄", "thermal-banker"),
    13: ("☯", "mirror-form"),
}

LEGACY_CLADES: Dict[int, str] = {
    0: "unrecorded",
    1: "ailuroform",
    2: "bimaniform",
    3: "cryocoherens",
    4: "lithophage",
    5: "hypobiotid",
    6: "soniform",
    7: "polybrachia",
    8: "hexasocial",
    9: "amphiform",
    10: "mycotiform",
    11: "cnidiform",
    12: "plasmiform",
    13: "syzygiform",
    14: "endolithid",
    15: "volatiform",
    16: "actinoform",
    17: "revenid",
    18: "heliciform",
    19: "draconiform",
    20: "metamorphid",
}

# Civic Projects Catalog
CIVIC_PROJECTS: Dict[str, Dict[str, Any]] = {
    "Deep Mantle Siphon": {
        "cost_work": 100,
        "cost_ore": 150,
        "description": "Sub-crustal bore expanding lithic extraction yields by +50%.",
        "effect": "ore_bonus",
    },
    "Biome Spire": {
        "cost_work": 100,
        "cost_organics": 150,
        "description": "Vertical atmospheric hydroponic lattice expanding biosphere yields by +50% and pop cap +500.",
        "effect": "organics_bonus",
    },
    "Cryo-Vault": {
        "cost_work": 120,
        "cost_ore": 100,
        "description": "Supercooled subterranean shelter insulating colonists from famine catastrophes and preserving morale.",
        "effect": "famine_immunity",
    },
    "Orbital Laboratory": {
        "cost_work": 150,
        "cost_ore": 120,
        "description": "Zero-gravity refinery array doubling periodic element extraction rate and accelerating research.",
        "effect": "element_research_bonus",
    },
    "Stela Archive": {
        "cost_work": 120,
        "cost_ore": 80,
        "description": "Monolithic stone data matrix preserving civic memories and elevating colony tax returns.",
        "effect": "tax_bonus",
    },
    "Solar Mirror Array": {
        "cost_work": 140,
        "cost_ore": 150,
        "description": "Orbital photovoltaic reflectors granting +100 MW to maximum planetary shield grid.",
        "effect": "shield_bonus",
    },
}

ERA_PROGRESSION = [
    "Progenitor Dawn",
    "Void Settlement",
    "Radiant Ascendant",
    "Cosmic Singularity",
]


@dataclass
class Civilization:
    """
    Autonomous civilization seated on a planetary body.
    Maintains species taxonomy, metabolic tension, civic works, and periodic research.
    """
    name: str
    species_name: str
    class_code: int
    sigil: str
    clade: str
    metabolism: str       # "mineral", "biotic", "plasmic", "umbral"
    disposition: str      # "expansionist", "epicurean", "empiricist", "industry"
    motto: str
    station: Optional[str] = "unseated"  # "progenitor", "watcher", "observer", "sovereign", "unseated"
    era_index: int = 0
    tech_level: int = 1
    discovered_elements: List[str] = field(default_factory=list)
    civic_projects: Dict[str, int] = field(default_factory=dict)
    current_project: Optional[str] = "Deep Mantle Siphon"
    project_progress: int = 0
    tension_vector: Dict[str, float] = field(default_factory=dict)
    trade_urgency: Dict[str, int] = field(default_factory=dict)
    research_points: int = 0
    grown_basis: List[Dict[str, Any]] = field(default_factory=list)
    alignment: float = 0.0                 # Cosmic alignment of the civilization (Light +1 .. Dark -1)
    native_policy: Optional[str] = None    # System-level doctrine for locals (overrides a laxer galactic card)
    dogma: float = 0.0                     # Dogma index for theocracies (Choir of the Pyre)
    faction_id: Optional[str] = None
    home_type: Optional[str] = None        # The world type the species evolved on (biosphere adaptation)
    light_optimum: Optional[str] = None    # The light its biology evolved under (exact flux, Earth = 1)

    @property
    def era_name(self) -> str:
        idx = min(self.era_index, len(ERA_PROGRESSION) - 1)
        return ERA_PROGRESSION[idx]

    @property
    def class_name(self) -> str:
        return CLASS_ARCHETYPES.get(self.class_code, ("?", "unknown"))[1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "species_name": self.species_name,
            "class_code": self.class_code,
            "sigil": self.sigil,
            "clade": self.clade,
            "metabolism": self.metabolism,
            "disposition": self.disposition,
            "motto": self.motto,
            "station": self.station,
            "era_index": self.era_index,
            "era_name": self.era_name,
            "tech_level": self.tech_level,
            "discovered_elements": list(self.discovered_elements),
            "civic_projects": dict(self.civic_projects),
            "current_project": self.current_project,
            "project_progress": self.project_progress,
            "tension_vector": dict(self.tension_vector),
            "trade_urgency": dict(self.trade_urgency),
            "research_points": self.research_points,
            "grown_basis": [dict(b) for b in self.grown_basis],
            "alignment": round(self.alignment, 4),
            "native_policy": self.native_policy,
            "dogma": round(self.dogma, 4),
            "faction_id": self.faction_id,
            "home_type": self.home_type,
            "light_optimum": self.light_optimum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Civilization":
        return cls(
            name=data["name"],
            species_name=data["species_name"],
            class_code=data.get("class_code", 1),
            sigil=data.get("sigil", "⬡"),
            clade=data.get("clade", "hypobiotid"),
            metabolism=data.get("metabolism", "biotic"),
            disposition=data.get("disposition", "empiricist"),
            motto=data.get("motto", ""),
            station=data.get("station", "unseated"),
            era_index=data.get("era_index", 0),
            tech_level=data.get("tech_level", 1),
            discovered_elements=list(data.get("discovered_elements", [])),
            civic_projects=dict(data.get("civic_projects", {})),
            current_project=data.get("current_project", "Deep Mantle Siphon"),
            project_progress=data.get("project_progress", 0),
            tension_vector=dict(data.get("tension_vector", {})),
            trade_urgency=dict(data.get("trade_urgency", {})),
            research_points=data.get("research_points", 0),
            grown_basis=list(data.get("grown_basis", [])),
            alignment=float(data.get("alignment", 0.0)),
            native_policy=data.get("native_policy"),
            dogma=float(data.get("dogma", 0.0)),
            faction_id=data.get("faction_id"),
            home_type=data.get("home_type"),
            light_optimum=data.get("light_optimum"),
        )


# Canonical Founding Polities Roster ported from Netstratum polities.rs
FOUNDING_POLITIES: List[Dict[str, Any]] = [
    {
        "name": "Tunborn",
        "species_name": "hypobiotid-voidsleeper",
        "class_code": 2,
        "sigil": "◈",
        "clade": "hypobiotid",
        "motto": "the dark between stars is a bed, not a wall",
        "disposition": "expansionist",
        "metabolism": "mineral",
        "station": "progenitor",
        "era_index": 1,
        "tech_level": 3,
        "discovered_elements": ["stelalith", "ferrolattice"],
    },
    {
        "name": "Sylvane",
        "species_name": "ailuroform-primus",
        "class_code": 7,
        "sigil": "▲",
        "clade": "ailuroform",
        "motto": "we were first, and we remember why that matters less than you think",
        "disposition": "epicurean",
        "metabolism": "biotic",
        "station": "progenitor",
        "era_index": 2,
        "tech_level": 4,
        "discovered_elements": ["chitinium", "cryogenite"],
    },
    {
        "name": "Forgeborn",
        "species_name": "bimaniform-flatlander",
        "class_code": 2,
        "sigil": "◈",
        "clade": "bimaniform",
        "motto": "we plan in stone and fire; we no longer dig",
        "disposition": "industry",
        "metabolism": "mineral",
        "station": "progenitor",
        "era_index": 1,
        "tech_level": 3,
        "discovered_elements": ["stelalith", "pyrosite"],
    },
    {
        "name": "Corebound",
        "species_name": "lithophage-stonewill",
        "class_code": 2,
        "sigil": "◈",
        "clade": "lithophage",
        "motto": "the surface is weather; we are the world",
        "disposition": "epicurean",
        "metabolism": "mineral",
        "station": "progenitor",
        "era_index": 1,
        "tech_level": 2,
        "discovered_elements": ["stelalith"],
    },
    {
        "name": "Coronal Choir",
        "species_name": "plasmiform-sheet",
        "class_code": 6,
        "sigil": "∿",
        "clade": "plasmiform",
        "motto": "we are the weather of the star",
        "disposition": "expansionist",
        "metabolism": "plasmic",
        "station": "progenitor",
        "era_index": 2,
        "tech_level": 4,
        "discovered_elements": ["sol_plasma", "pyrosite"],
    },
    {
        "name": "Stillcold",
        "species_name": "cryocoherens-still",
        "class_code": 4,
        "sigil": "≋",
        "clade": "cryocoherens",
        "motto": "in the perfect cold, everything can be known",
        "disposition": "empiricist",
        "metabolism": "biotic",
        "station": "watcher",
        "era_index": 1,
        "tech_level": 3,
        "discovered_elements": ["cryogenite"],
    },
    {
        "name": "Thresholder",
        "species_name": "bimaniform-septem",
        "class_code": 4,
        "sigil": "≋",
        "clade": "bimaniform",
        "motto": "we hold the threshold and do not descend",
        "disposition": "empiricist",
        "metabolism": "biotic",
        "station": "watcher",
        "era_index": 1,
        "tech_level": 3,
        "discovered_elements": ["chitinium"],
    },
    {
        "name": "Coralline",
        "species_name": "cnidiform-accrete",
        "class_code": 1,
        "sigil": "⬡",
        "clade": "cnidiform",
        "motto": "we accrete, therefore we are",
        "disposition": "epicurean",
        "metabolism": "biotic",
        "station": "watcher",
        "era_index": 0,
        "tech_level": 2,
        "discovered_elements": ["chitinium"],
    },
    {
        "name": "Umbrid",
        "species_name": "draconiform-umbra",
        "class_code": 4,
        "sigil": "≋",
        "clade": "draconiform",
        "motto": "the union is the evidence; the seat above re-checks it",
        "disposition": "epicurean",
        "metabolism": "umbral",
        "station": "observer",
        "era_index": 1,
        "tech_level": 3,
        "discovered_elements": ["umbrite", "void_resin"],
    },
    {
        "name": "Stelahold",
        "species_name": "bimaniform-flatlander",
        "class_code": 2,
        "sigil": "◈",
        "clade": "bimaniform",
        "motto": "what is written in stone outlives the flood",
        "disposition": "empiricist",
        "metabolism": "mineral",
        "station": "sovereign",
        "era_index": 1,
        "tech_level": 3,
        "discovered_elements": ["stelalith"],
    },
    {
        "name": "Tallykeep",
        "species_name": "bimaniform-calendar",
        "class_code": 4,
        "sigil": "≋",
        "clade": "bimaniform",
        "motto": "the calendar is the spine of the sky",
        "disposition": "empiricist",
        "metabolism": "biotic",
        "station": "sovereign",
        "era_index": 1,
        "tech_level": 3,
        "discovered_elements": ["cryogenite"],
    },
    {
        "name": "Glyphward",
        "species_name": "bimaniform-scribe",
        "class_code": 4,
        "sigil": "≋",
        "clade": "bimaniform",
        "motto": "the record outlives the recorder",
        "disposition": "empiricist",
        "metabolism": "biotic",
        "station": "sovereign",
        "era_index": 1,
        "tech_level": 3,
        "discovered_elements": ["stelalith"],
    },
    {
        "name": "Slagborn",
        "species_name": "hypobiotid-endure",
        "class_code": 2,
        "sigil": "◈",
        "clade": "hypobiotid",
        "motto": "we eat what worlds discard",
        "disposition": "expansionist",
        "metabolism": "mineral",
        "station": "unseated",
        "era_index": 0,
        "tech_level": 2,
        "discovered_elements": ["ferrolattice"],
    },
    {
        "name": "Echowright",
        "species_name": "soniform-songline",
        "class_code": 5,
        "sigil": "⊚",
        "clade": "soniform",
        "motto": "we heard it before you saw it",
        "disposition": "epicurean",
        "metabolism": "biotic",
        "station": "unseated",
        "era_index": 1,
        "tech_level": 2,
        "discovered_elements": ["chitinium"],
    },
    {
        "name": "Vitreous Hex",
        "species_name": "hexasocial-comb",
        "class_code": 1,
        "sigil": "⬡",
        "clade": "hexasocial",
        "motto": "the comb computes",
        "disposition": "empiricist",
        "metabolism": "biotic",
        "station": "unseated",
        "era_index": 1,
        "tech_level": 3,
        "discovered_elements": ["chitinium", "cryogenite"],
    },
    {
        "name": "Brine Cortex",
        "species_name": "polybrachia-cortex",
        "class_code": 5,
        "sigil": "⊚",
        "clade": "polybrachia",
        "motto": "eight arms, one argument",
        "disposition": "epicurean",
        "metabolism": "biotic",
        "station": "unseated",
        "era_index": 1,
        "tech_level": 2,
        "discovered_elements": ["chitinium"],
    },
    {
        "name": "Frostwright",
        "species_name": "amphiform-rime",
        "class_code": 12,
        "sigil": "❄",
        "clade": "amphiform",
        "motto": "we bank what the fire cannot hold",
        "disposition": "empiricist",
        "metabolism": "biotic",
        "station": "unseated",
        "era_index": 1,
        "tech_level": 3,
        "discovered_elements": ["cryogenite"],
    },
    {
        "name": "Mycelial Weft",
        "species_name": "mycotiform-hypha",
        "class_code": 1,
        "sigil": "⬡",
        "clade": "mycotiform",
        "motto": "the network under the soil holds the forest's memory",
        "disposition": "empiricist",
        "metabolism": "biotic",
        "station": "unseated",
        "era_index": 1,
        "tech_level": 3,
        "discovered_elements": ["chitinium"],
    },
    {
        "name": "Syzygy",
        "species_name": "syzygiform-conjunction",
        "class_code": 13,
        "sigil": "☯",
        "clade": "syzygiform",
        "motto": "we exist where the voices agree",
        "disposition": "epicurean",
        "metabolism": "umbral",
        "station": "unseated",
        "era_index": 2,
        "tech_level": 4,
        "discovered_elements": ["umbrite", "mirror_glass"],
    },
    {
        "name": "Deepmat",
        "species_name": "endolithid-understone",
        "class_code": 9,
        "sigil": "▼",
        "clade": "endolithid",
        "motto": "the sky is a rumor we have not confirmed",
        "disposition": "empiricist",
        "metabolism": "mineral",
        "station": "unseated",
        "era_index": 1,
        "tech_level": 2,
        "discovered_elements": ["stelalith"],
    },
]


class CivilizationIntelligenceEngine:
    """
    Executes the homological economy and autonomous intelligence loop for planetary civilizations.
    Translates metabolic tension into production, research, or commercial trade urgency.
    """

    @classmethod
    def create_civilization(cls, pol_data: Dict[str, Any]) -> Civilization:
        return Civilization(
            name=pol_data["name"],
            species_name=pol_data["species_name"],
            class_code=pol_data["class_code"],
            sigil=pol_data["sigil"],
            clade=pol_data["clade"],
            metabolism=pol_data["metabolism"],
            disposition=pol_data["disposition"],
            motto=pol_data["motto"],
            station=pol_data.get("station", "unseated"),
            era_index=pol_data.get("era_index", 0),
            tech_level=pol_data.get("tech_level", 1),
            discovered_elements=list(pol_data.get("discovered_elements", [])),
        )

    @classmethod
    def evaluate_metabolic_loads(cls, civ: Civilization, population: int) -> Dict[str, float]:
        """
        Calculates exact demand loads based on species metabolism and population.
        Demand rates:
          - biotic: requires organics (food) and biotic elements
          - mineral: requires ore (lithic substrate) and deep elements
          - plasmic: requires energy/equipment and furnace elements
          - umbral: requires balanced sustenance and dark elements
        """
        loads: Dict[str, float] = {}
        pop_scale = max(1, population) / 1000.0

        if civ.metabolism == "biotic":
            loads["organics"] = max(1.0, pop_scale * 1.0)
        elif civ.metabolism == "mineral":
            loads["ore"] = max(1.0, pop_scale * 1.0)
        elif civ.metabolism == "plasmic":
            loads["ore"] = max(1.0, pop_scale * 0.5)
        elif civ.metabolism == "umbral":
            loads["organics"] = max(0.5, pop_scale * 0.5)
            loads["ore"] = max(0.5, pop_scale * 0.5)
        else:
            loads["organics"] = max(1.0, pop_scale * 1.0)

        # Periodic element demand: A civilization demands elements it has discovered and cataloged
        meta_elems = [
            e for e in civ.discovered_elements
            if e in [el.element_id for el in PeriodicTable.get_elements_for_metabolism(civ.metabolism)]
        ]
        if meta_elems:
            loads[meta_elems[0]] = round(pop_scale * 0.2, 3)
        elif civ.discovered_elements:
            loads[civ.discovered_elements[0]] = round(pop_scale * 0.2, 3)

        return loads

    @classmethod
    def tick_civilization(
        cls,
        civ: Civilization,
        planet: Any,
        event_bus: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Executes one full cycle of civilization intelligence:
        1. Evaluate metabolic tension δ = Demand - Supply.
        2. Elemental prospecting and extraction.
        3. If tension is covered: Advance civic projects (Production) and periodic research (Research).
        4. If tension is acute: Register trade urgency to charter commerce routes.
        """
        # 1. Evaluate demand vs planetary standing supply
        demand_loads = cls.evaluate_metabolic_loads(civ, planet.population)
        deficit: Dict[str, float] = {}
        has_acute_deficit = False

        # Check primary commodities
        for carrier, rate in demand_loads.items():
            if carrier == "organics":
                avail = planet.organics_silo
            elif carrier == "ore":
                avail = planet.ore_silo
            else:
                # Periodic element check in planetary element reserves
                avail = getattr(planet, "element_reserves", {}).get(carrier, 0)

            gap = rate - avail
            if gap > 0:
                deficit[carrier] = round(gap, 2)
                has_acute_deficit = True
            else:
                deficit[carrier] = 0.0

        civ.tension_vector = deficit

        # 2. Elemental Prospecting and Extraction
        # Civilizations extract elements from planetary deposits if within their refining threshold
        extracted_elements: Dict[str, int] = {}
        deposits = getattr(planet, "element_deposits", {})
        reserves = getattr(planet, "element_reserves", {})

        for elem_id in list(deposits.keys()):
            elem = PeriodicTable.get_element(elem_id)
            if elem:
                # If civ has discovered it or tech level covers refines_at
                max_refine_line = civ.tech_level + 2
                if elem.line <= max_refine_line:
                    if elem_id not in civ.discovered_elements:
                        civ.discovered_elements.append(elem_id)

                    deposit_qty = deposits[elem_id]
                    if deposit_qty > 0:
                        # Extract 1-3 units
                        extract_amount = min(deposit_qty, random.randint(1, 2 + (civ.tech_level // 2)))
                        deposits[elem_id] -= extract_amount
                        reserves[elem_id] = reserves.get(elem_id, 0) + extract_amount
                        extracted_elements[elem_id] = extract_amount

        # 3. Production vs Research Split
        project_advanced = False
        project_completed = None
        new_element_discovered = None
        era_advanced = False

        if not has_acute_deficit:
            # Full metabolic satiety: Labor is directed to civic infrastructure and scientific research
            civ.trade_urgency.clear()

            # A. PRODUCTION: Civic Project Progress
            if civ.current_project:
                cfg = CIVIC_PROJECTS.get(civ.current_project, {})
                progress_step = 10 + (5 if civ.disposition == "industry" else 0) + (civ.tech_level * 3)

                # Check if planetary ore or organics are available to contribute
                needed_ore = cfg.get("cost_ore", 0)
                if needed_ore > 0 and planet.ore_silo >= 5:
                    matter.consume(planet, "ore_silo", "ORE", 5, "civic_works")
                    progress_step += 5

                civ.project_progress += progress_step
                project_advanced = True

                if civ.project_progress >= 100:
                    # Project Completed!
                    civ.civic_projects[civ.current_project] = civ.civic_projects.get(civ.current_project, 0) + 1
                    project_completed = civ.current_project
                    cls._apply_project_effects(civ.current_project, planet)

                    # Select next project
                    all_projects = list(CIVIC_PROJECTS.keys())
                    civ.current_project = random.choice([p for p in all_projects if p != project_completed])
                    civ.project_progress = 0

                    if event_bus:
                        event_bus.broadcast_radio(
                            sender=civ.name,
                            text=f"Civic project '{project_completed}' completed on {planet.name}! ({civ.motto})",
                            channel="COMM-1",
                            sector_id=planet.sector_id,
                        )

            # B. RESEARCH: Periodic Table Discovery
            research_gain = 5 + (5 if civ.disposition == "empiricist" else 0) + (civ.tech_level * 2)
            # Dogma suppresses reason: a zealot priesthood brands inquiry tech-heresy; the Imperium
            # permits only the sanctioned sciences of its ancient rites
            from xylarium.config import ZEALOT_RD_FREEZE_DOGMA
            if civ.dogma > ZEALOT_RD_FREEZE_DOGMA:
                research_gain = 0
            elif civ.faction_id == "IMPERIUM":
                research_gain //= 2
            civ.research_points += research_gain

            # Elements are not handed out here: a people discovers what its worlds actually hold, by digging
            # (chemistry.py). Its era turns as its understanding of the table deepens.
            if True:
                # Era advancement check
                if len(civ.discovered_elements) >= (civ.era_index + 1) * 3:
                    if civ.era_index < len(ERA_PROGRESSION) - 1:
                        civ.era_index += 1
                        civ.tech_level += 1
                        era_advanced = True
                        if event_bus:
                            event_bus.broadcast_radio(
                                sender=civ.name,
                                text=f"The {civ.name} civilization has evolved into the '{civ.era_name}' era! Tech Level: {civ.tech_level}.",
                                channel="COMM-1",
                                sector_id=planet.sector_id,
                            )
        else:
            # Acute tension: Civilization posts trade urgency
            for carrier, gap in deficit.items():
                if gap > 0:
                    civ.trade_urgency[carrier] = int(gap * 10)

        return {
            "civilization": civ.name,
            "metabolism": civ.metabolism,
            "tension_vector": civ.tension_vector,
            "trade_urgency": civ.trade_urgency,
            "extracted_elements": extracted_elements,
            "project_advanced": project_advanced,
            "project_completed": project_completed,
            "new_element_discovered": new_element_discovered,
            "era_advanced": era_advanced,
            "tech_level": civ.tech_level,
            "era_name": civ.era_name,
        }

    @classmethod
    def _apply_project_effects(cls, project_name: str, planet: Any) -> None:
        """Applies persistent systemic improvements from completed civic projects to the planet."""
        cfg = CIVIC_PROJECTS.get(project_name, {})
        effect = cfg.get("effect")

        if effect == "shield_bonus":
            planet.max_shields += 100
            planet.shields = min(planet.max_shields, planet.shields + 100)
        elif effect == "organics_bonus":
            matter.produce(planet, "organics_silo", "ORGANICS", 50, "civic_harvest")
            planet.morale = min(100, planet.morale + 10)
        elif effect == "ore_bonus":
            matter.produce(planet, "ore_silo", "ORE", 50, "civic_mining")
        elif effect == "famine_immunity":
            planet.morale = max(80, planet.morale)
        elif effect == "tax_bonus":
            bonus = max(0, min(500, 500000 - planet.treasury))
            planet.treasury += bonus
            from xylarium.kernel import ledger
            ledger.mint("colony_tax", bonus, getattr(planet, "currency", "SOL"))
