"""
Precursor Alchemy & Elemental Transmutation Engine for Xylarium.
Ported from Netstratum 34_MATTER_BALANCE and 31_ELEMENT_COMMERCE.
Governs sub-atomic nucleosynthesis and elemental transmutation over the 24-element periodic table.
Transmutes base volatiles and structural metals into high-tier exotics and manufactured gems,
balancing reaction thermal entropy against cryogenic cooling infrastructure.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from xylarium.config import (
    ALCHEMY_ENTROPY_HEAT_PER_REACTION,
    ALCHEMY_CRYO_COOLING_CAPACITY,
    ALCHEMY_BASE_CREDIT_COST,
)
from xylarium.kernel.models import ActionResult, ActionType, Captain, Ship, CargoHold
from xylarium.kernel.elements import PeriodicTable
from xylarium.kernel import elements_continuum, substances, torsion
from xylarium.kernel.experience import ExperienceManager


@dataclass
class TransmutationRecipe:
    id: str
    name: str
    inputs: Dict[str, int]
    catalyst: str
    output_element: str
    output_qty: int = 1
    thermal_entropy: float = ALCHEMY_ENTROPY_HEAT_PER_REACTION
    required_tech: Optional[str] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "inputs": dict(self.inputs),
            "catalyst": self.catalyst,
            "output_element": self.output_element,
            "output_qty": self.output_qty,
            "thermal_entropy": self.thermal_entropy,
            "required_tech": self.required_tech,
            "description": self.description,
        }


# Canonical Precursor Transmutation Recipes
ALCHEMY_RECIPES: Dict[str, TransmutationRecipe] = {
    "ADAMANT_LODE": TransmutationRecipe(
        id="ADAMANT_LODE",
        name="Adamant Lode Synthesis",
        inputs={"Fe": 3, "Ti": 2},
        catalyst="U",
        output_element="AdL",
        output_qty=1,
        thermal_entropy=25.0,
        required_tech="ORBITAL_FOUNDRY",
        description="Fuses heavy iron and titanium ingots under enriched uranium fission catalysis into ultra-dense Adamant Lode.",
    ),
    "SPIRAL_RIME": TransmutationRecipe(
        id="SPIRAL_RIME",
        name="Spiral Rime Crystallization",
        inputs={"H2O": 3, "Xe": 2},
        catalyst="cryogenite",
        output_element="SpR",
        output_qty=1,
        thermal_entropy=10.0,
        required_tech="NANITE_DRYDOCK",
        description="Sub-Kelvin cryogenic sublimation of xenon gas and glacial ice into quantum-coherent Spiral Rime crystals.",
    ),
    "AETHERIUM": TransmutationRecipe(
        id="AETHERIUM",
        name="Aetherium Nucleosynthesis",
        inputs={"He-3": 2, "Xe": 2},
        catalyst="Pt",
        output_element="aetherium",
        output_qty=1,
        thermal_entropy=30.0,
        required_tech="JUMP_DRIVE",
        description="High-energy coronal confinement uniting helium-3 and noble xenon around a platinum matrix to yield Aetherium.",
    ),
    "STELALITH": TransmutationRecipe(
        id="STELALITH",
        name="Stelalith Fusion",
        inputs={"Si": 2, "C": 2},
        catalyst="Pt",
        output_element="stelalith",
        output_qty=2,
        thermal_entropy=15.0,
        description="Compresses carbon allotropes and silicon wafers into structural lithic crystal matrices.",
    ),
    "PYROSITE": TransmutationRecipe(
        id="PYROSITE",
        name="Pyrosite Ignition",
        inputs={"H": 3, "He-3": 2},
        catalyst="U",
        output_element="pyrosite",
        output_qty=2,
        thermal_entropy=25.0,
        description="Thermonuclear plasma fusion binding primordial hydrogen and helium-3 into incandescent pyrosite slag.",
    ),
    "FERROLATTICE": TransmutationRecipe(
        id="FERROLATTICE",
        name="Ferrolattice Alloy",
        inputs={"Fe": 2, "Ni": 2},
        catalyst="Ti",
        output_element="ferrolattice",
        output_qty=2,
        thermal_entropy=12.0,
        description="Micro-gravity magnetic annealing linking iron and refined nickel into a resilient ferromagnetic lattice.",
    ),
    "CHITINIUM": TransmutationRecipe(
        id="CHITINIUM",
        name="Chitinium Bio-Polymerization",
        inputs={"C": 3, "H2O": 2},
        catalyst="organics",
        output_element="chitinium",
        output_qty=2,
        thermal_entropy=8.0,
        required_tech="BIO_SYNTHESIZER",
        description="Catalytic enzyme synthesis polymerizing organic compounds and liquid water into organic Chitinium carapace.",
    ),
    "UMBRITE": TransmutationRecipe(
        id="UMBRITE",
        name="Umbrite Vacuum Occlusion",
        inputs={"Xe": 2, "C": 2},
        catalyst="U",
        output_element="umbrite",
        output_qty=1,
        thermal_entropy=20.0,
        required_tech="CLOAKING_GRID",
        description="Irradiates xenon and dense carbon in high-vacuum resonance to produce light-absorbing Umbrite ore.",
    ),
    "CRYOGENITE": TransmutationRecipe(
        id="CRYOGENITE",
        name="Cryogenite Condensation",
        inputs={"H2O": 3, "C": 1},
        catalyst="Xe",
        output_element="cryogenite",
        output_qty=2,
        thermal_entropy=10.0,
        description="Flash-freezes volatile hydro-compounds in a xenon gas bath into zero-Kelvin Cryogenite.",
    ),
}


def alchemical_induction(
    kernel: Optional[Any],
    captain: Captain,
    input_elements: Dict[str, int],
    catalyst: str,
    sector_id: Optional[int] = None,
) -> ActionResult:
    """
    Sub-atomic nucleosynthesis and alchemical induction across the 118+ periodic continuum.

    Couples input element nuclear mass/charge conservation with local torsion wavefront resonance:
      - Z_net = sum(Q_i * Z_i), A_net = sum(Q_i * A_i)
      - Nuclear binding energy B(A, Z) derived via Weizsaecker SEMF and magic shell corrections.
      - Torsion wavefront phase resonance (Psi, phase, chirality) from sector torsion flux modulates
        activation entropy and stabilizes synthetic superheavy nuclides.
      - When magic proton shell closures (Z in 114, 120, 126) or Island of Stability conditions are met,
        induces synthesis and discovery of new superheavy elements (e.g. Z=119 Uue, Z=120 Ubn, Z=126 Ubh).
      - Records newly discovered elements in captain.discovered_elements and civilization archives.
    """
    if not input_elements:
        return ActionResult(False, ActionType.ALCHEMY_TRANSMUTE, "No input elements specified for induction.")

    cargo = captain.ship.cargo

    # 1. Validate catalyst
    if catalyst == "organics":
        if cargo.organics < 1:
            return ActionResult(False, ActionType.ALCHEMY_TRANSMUTE, "Missing required catalyst: 1 crate of Organics.")
    else:
        cat_units = cargo.unbonded(catalyst)
        if cat_units < 1:
            return ActionResult(False, ActionType.ALCHEMY_TRANSMUTE, f"Missing required catalyst: 1 unit of [{catalyst}].")

    # 2. Validate input materials
    for sym, qty in input_elements.items():
        if qty <= 0:
            continue
        avail = cargo.unbonded(sym)
        if avail < qty:
            return ActionResult(
                False,
                ActionType.ALCHEMY_TRANSMUTE,
                f"Insufficient raw element [{sym}]: {qty} required, {avail} present in cargo.",
            )

    # 3. Credit fee for high-energy reactor ignition
    if captain.credits < ALCHEMY_BASE_CREDIT_COST:
        return ActionResult(
            False,
            ActionType.ALCHEMY_TRANSMUTE,
            f"Insufficient funds: Alchemical induction requires {ALCHEMY_BASE_CREDIT_COST:,} Credits for ignition.",
        )

    # 4. Resolve net atomic number and nucleon mass
    z_net = 0
    a_net = 0.0
    for sym, qty in input_elements.items():
        if qty <= 0:
            continue
        z_i = elements_continuum.parse_element_z(sym)
        if z_i is not None:
            ce_i = elements_continuum.get_element(z_i)
            z_net += int(qty * z_i)
            a_net += float(qty * ce_i.a)
        else:
            consts = substances.constituents(sym)
            if consts:
                for c_sym, c_q in consts.items():
                    cz = elements_continuum.parse_element_z(c_sym) or 1
                    ce = elements_continuum.get_element(cz)
                    z_net += int(qty * c_q * cz)
                    a_net += float(qty * c_q * ce.a)
            else:
                return ActionResult(False, ActionType.ALCHEMY_TRANSMUTE, f"Unrecognized element or compound [{sym}].")

    if z_net < 1:
        z_net = 1

    # 5. Target continuum element evaluation
    target_ce = elements_continuum.get_element(z_net)
    target_sym = target_ce.symbol
    target_name = target_ce.name

    # Check cargo hold capacity
    total_in = sum(v for v in input_elements.values() if v > 0)
    net_space_delta = 1 - total_in
    if net_space_delta > 0 and cargo.available_space < net_space_delta:
        return ActionResult(
            False,
            ActionType.ALCHEMY_TRANSMUTE,
            f"Cargo hold full! Insufficient capacity for synthesized [{target_sym}].",
        )

    # 6. Torsion wavefront resonance coupling
    sec_id = sector_id if sector_id is not None else getattr(captain, "sector_id", 1)
    amp, phase, chirality = torsion.eval_wavefront(kernel, sec_id) if kernel is not None else (0.0, 0.0, 1)

    cos_phase = math.cos(phase)
    phase_alignment = (1.0 + cos_phase * chirality) * 0.5  # 0.0 to 1.0

    # Shell closure proximity
    dist_magic = min(abs(z_net - m) for m in elements_continuum.MAGIC_Z)
    shell_resonance = max(0.0, 1.0 - (dist_magic * 0.15))

    stability = target_ce.stability_factor * (0.8 + 0.4 * phase_alignment) * (1.0 + shell_resonance * 0.5 * (1.0 + amp))

    # Thermal entropy calculation
    base_entropy = max(8.0, abs(z_net - 26) * 0.5) / max(0.3, stability)

    # Cryogenic cooling check
    coolant_used = False
    if base_entropy > ALCHEMY_CRYO_COOLING_CAPACITY:
        if cargo.unbonded("cryogenite") >= 1:
            cargo.elements["cryogenite"] -= 1
            if cargo.elements["cryogenite"] <= 0:
                del cargo.elements["cryogenite"]
            base_entropy = max(0.0, base_entropy - 25.0)
            coolant_used = True
        elif cargo.unbonded("H2O") >= 2:
            cargo.elements["H2O"] -= 2
            if cargo.elements["H2O"] <= 0:
                del cargo.elements["H2O"]
            base_entropy = max(0.0, base_entropy - 15.0)
            coolant_used = True

    # 7. Deduct costs and input elements
    captain.credits -= ALCHEMY_BASE_CREDIT_COST
    for sym, qty in input_elements.items():
        if qty <= 0:
            continue
        cargo.elements[sym] -= qty
        if cargo.elements[sym] <= 0:
            del cargo.elements[sym]

    # 8. Deposit synthesized output element
    cargo.elements[target_sym] = cargo.elements.get(target_sym, 0) + 1

    # 9. Discovery record
    discovered = getattr(captain, "discovered_elements", [])
    is_new = (z_net >= 114 or target_sym in ("SpR", "pyrosite", "umbrite", "aetherium", "AdL", "mirror_glass") or z_net >= 119) and (target_sym not in discovered)

    disc_msg = ""
    if is_new:
        discovered.append(target_sym)
        captain.score += 500
        if kernel is not None:
            ExperienceManager.award(captain, "intellect", 250, kernel, key=f"discovery:{target_sym}")
            sec = kernel.sectors.get(sec_id) if hasattr(kernel, "sectors") else None
            if sec and sec.planets:
                for p in sec.planets:
                    if p.civilization and hasattr(p.civilization, "discovered_elements"):
                        if target_sym not in p.civilization.discovered_elements:
                            p.civilization.discovered_elements.append(target_sym)
        disc_msg = f" *** BREAKTHROUGH: Discovered New Element [{target_sym}] ({target_name}, Z={z_net})! ***"

    cool_str = " (Cryo-Coolant consumed to stabilize core)" if coolant_used else ""
    msg = (
        f"ALCHEMICAL INDUCTION SUCCESS: Synthesized [{target_sym}] (Z={z_net}, A={target_ce.a:.1f})! "
        f"Phase Alignment: {phase_alignment:.2f} | Stability: {stability:.2f} | Thermal Entropy: {base_entropy:.1f} MW.{cool_str}{disc_msg}"
    )

    if kernel and hasattr(kernel, "action_logs"):
        kernel.action_logs.append(f"[INDUCTION] {captain.name} induced {target_sym} (Z={z_net}).")

    return ActionResult(
        True,
        ActionType.ALCHEMY_TRANSMUTE,
        msg,
        data={
            "target_element": target_sym,
            "target_name": target_name,
            "atomic_number": z_net,
            "mass_number": round(target_ce.a, 3),
            "is_new_discovery": is_new,
            "phase_alignment": round(phase_alignment, 4),
            "stability_factor": round(stability, 4),
            "binding_per_nucleon": round(target_ce.binding_per_nucleon, 4),
            "heat": round(base_entropy, 2),
        },
    )


@dataclass
class ISRURefineryRecipe:
    id: str
    name: str
    inputs: Dict[str, int]
    outputs: Dict[str, int]
    description: str


ISRU_RECIPES: Dict[str, ISRURefineryRecipe] = {
    "RAW_ORE_SMELT": ISRURefineryRecipe(
        id="RAW_ORE_SMELT",
        name="Induction Furnace Ore Smelting",
        inputs={"ORE": 4},
        outputs={"Fe": 2, "Si": 1, "Ti": 1},
        description="Crushes and induction-smelts raw asteroid ore into pure iron, silicon, and titanium ingots.",
    ),
    "VOLATILE_FRACTIONATION": ISRURefineryRecipe(
        id="VOLATILE_FRACTIONATION",
        name="Cryogenic Volatile Fractionation",
        inputs={"H2O": 4},
        outputs={"H": 2, "cryogenite": 1},
        description="Vacuum distillation and flash fractionation of raw ice into liquid hydrogen and cryogenite.",
    ),
    "ACTINIDE_CENTRIFUGE": ISRURefineryRecipe(
        id="ACTINIDE_CENTRIFUGE",
        name="Magnetic Isotope Centrifuge",
        inputs={"U": 3, "Pt": 1},
        outputs={"pyrosite": 2, "AdL": 1},
        description="Enriches radioactive actinides and heavy platinum into high-energy pyrosite and adamant lode.",
    ),
    "HYDROCARBON_CRACK": ISRURefineryRecipe(
        id="HYDROCARBON_CRACK",
        name="Fischer-Tropsch Hydrocarbon Synthesis",
        inputs={"C": 3, "H": 2},
        outputs={"ORGANICS": 2},
        description="Polymerizes carbon and hydrogen gas into bio-compatible organic nutrients and polymers.",
    ),
    "FERROLATTICE_FORGE": ISRURefineryRecipe(
        id="FERROLATTICE_FORGE",
        name="High-Tensile Ferrolattice Forging",
        inputs={"Fe": 3, "C": 2},
        outputs={"ferrolattice": 2},
        description="Anneals iron and carbon matrices into reinforced high-tensile ferrolattice framing.",
    ),
}


def _get_cargo_avail(cargo: Any, item: str) -> int:
    item_u = item.upper()
    if item_u == "ORE":
        return getattr(cargo, "ore", 0) + getattr(cargo, "elements", {}).get("ORE", 0)
    elif item_u in ("ORGANICS", "ORG"):
        return getattr(cargo, "organics", 0) + getattr(cargo, "elements", {}).get("ORGANICS", 0)
    elif item_u in ("EQUIPMENT", "EQP"):
        return getattr(cargo, "equipment", 0) + getattr(cargo, "elements", {}).get("EQUIPMENT", 0)
    return getattr(cargo, "elements", {}).get(item, getattr(cargo, "elements", {}).get(item_u, 0))


def _deduct_cargo(cargo: Any, item: str, qty: int) -> None:
    item_u = item.upper()
    rem = qty
    if item_u == "ORE":
        take = min(cargo.ore, rem)
        cargo.ore -= take
        rem -= take
        if rem > 0 and "ORE" in cargo.elements:
            take_el = min(cargo.elements["ORE"], rem)
            cargo.elements["ORE"] -= take_el
            rem -= take_el
            if cargo.elements["ORE"] <= 0:
                del cargo.elements["ORE"]
    elif item_u in ("ORGANICS", "ORG"):
        take = min(cargo.organics, rem)
        cargo.organics -= take
        rem -= take
        if rem > 0 and "ORGANICS" in cargo.elements:
            take_el = min(cargo.elements["ORGANICS"], rem)
            cargo.elements["ORGANICS"] -= take_el
            rem -= take_el
            if cargo.elements["ORGANICS"] <= 0:
                del cargo.elements["ORGANICS"]
    elif item_u in ("EQUIPMENT", "EQP"):
        take = min(cargo.equipment, rem)
        cargo.equipment -= take
        rem -= take
        if rem > 0 and "EQUIPMENT" in cargo.elements:
            take_el = min(cargo.elements["EQUIPMENT"], rem)
            cargo.elements["EQUIPMENT"] -= take_el
            rem -= take_el
            if cargo.elements["EQUIPMENT"] <= 0:
                del cargo.elements["EQUIPMENT"]
    else:
        k = item if item in cargo.elements else item_u
        if k in cargo.elements:
            cargo.elements[k] = max(0, cargo.elements[k] - rem)
            if cargo.elements[k] <= 0:
                del cargo.elements[k]


def _add_cargo(cargo: Any, item: str, qty: int) -> None:
    item_u = item.upper()
    if item_u == "ORE":
        cargo.ore += qty
    elif item_u in ("ORGANICS", "ORG"):
        cargo.organics += qty
    elif item_u in ("EQUIPMENT", "EQP"):
        cargo.equipment += qty
    else:
        cargo.elements[item] = cargo.elements.get(item, 0) + qty


class AlchemyManager:
    """
    Governs sub-atomic particle synthesizers and transmutations.
    """

    def __init__(self):
        self.heat_accumulated: Dict[str, float] = {}  # captain_id -> current core thermal units

    @property
    def recipes(self) -> Dict[str, TransmutationRecipe]:
        return ALCHEMY_RECIPES

    def get_available_recipes(self, captain: Captain) -> List[TransmutationRecipe]:
        available = []
        for r in ALCHEMY_RECIPES.values():
            if self.mastery(captain, r) > 0 and not self.unknown_elements(captain, r):
                available.append(r)
        return available

    @staticmethod
    def unknown_elements(captain: Captain, recipe: "TransmutationRecipe") -> list:
        """Elements of a recipe (inputs and catalyst) the captain's people has not yet understood (chemistry.py)."""
        from xylarium.kernel import chemistry, knowledge, ledger
        k = ledger.active_kernel()
        if k is None:
            return []
        parts = dict(recipe.inputs)
        if recipe.catalyst:
            parts[recipe.catalyst] = 1
        return chemistry.missing_for(k, knowledge.holder_of_captain(captain), parts)

    @staticmethod
    def mastery(captain: Captain, recipe: "TransmutationRecipe") -> float:
        """How well the captain's people know the process a recipe rests on (1 for recipes that need none)."""
        if not recipe.required_tech:
            return 1.0
        from xylarium.config import LEGACY_TECH_PROCESS
        from xylarium.kernel import knowledge, ledger
        k = ledger.active_kernel()
        proc = LEGACY_TECH_PROCESS.get(recipe.required_tech)
        return knowledge.captain_mastery(k, captain, proc) if (k is not None and proc) else 0.0

    def get_heat(self, captain_id: str) -> float:
        return self.heat_accumulated.get(captain_id, 0.0)

    def cool_reactor(self, captain_id: str, amount: float = 10.0) -> None:
        if captain_id in self.heat_accumulated:
            self.heat_accumulated[captain_id] = max(0.0, self.heat_accumulated[captain_id] - amount)

    def tick_cooldown(self, captain_or_kernel: Any = None) -> None:
        """Passive reactor cooling each cycle."""
        if captain_or_kernel and hasattr(captain_or_kernel, "id"):
            self.cool_reactor(captain_or_kernel.id, amount=5.0)
            if self.heat_accumulated.get(captain_or_kernel.id, 0.0) <= 0:
                self.heat_accumulated.pop(captain_or_kernel.id, None)
        else:
            for cid in list(self.heat_accumulated.keys()):
                self.cool_reactor(cid, amount=5.0)
                if self.heat_accumulated[cid] <= 0:
                    del self.heat_accumulated[cid]

    def transmute(
        self,
        captain_id: Optional[str] = None,
        recipe_id: str = "",
        kernel: Any = None,
        captain: Any = None,
        iterations: int = 1,
    ) -> ActionResult:
        """
        Executes an elemental transmutation recipe:
        1. Verifies reactor power and technology requirements.
        2. Validates inputs, catalyst presence, and cargo hold space.
        3. Checks thermal dissipation against Cryogenite / Water cooling reserves.
        4. Transmutes elements, updates cargo, and vents or contains heat.
        """
        if captain is None and kernel and captain_id:
            captain = kernel.captains.get(captain_id)
        if not captain:
            return ActionResult(False, ActionType.ALCHEMY_TRANSMUTE, "Captain not found.")

        recipe = ALCHEMY_RECIPES.get(recipe_id)
        if not recipe:
            return ActionResult(False, ActionType.ALCHEMY_TRANSMUTE, f"Unknown transmutation recipe '{recipe_id}'.")

        # 1. Tech requirement check
        unknown = self.unknown_elements(captain, recipe)
        if unknown:
            return ActionResult(False, ActionType.ALCHEMY_TRANSMUTE,
                                f"Your people do not yet understand {', '.join(unknown)}: find it, hold it, study it.")
        if self.mastery(captain, recipe) <= 0:
            from xylarium.config import LEGACY_TECH_PROCESS, PROCESSES
            dom = PROCESSES.get(LEGACY_TECH_PROCESS.get(recipe.required_tech, ""), {}).get("domain", "materials")
            return ActionResult(
                False,
                ActionType.ALCHEMY_TRANSMUTE,
                f"Your people know nothing yet of this transmutation: it rests on {dom} knowledge.",
            )

        # 2. Credits cost
        if captain.credits < ALCHEMY_BASE_CREDIT_COST:
            return ActionResult(
                False,
                ActionType.ALCHEMY_TRANSMUTE,
                f"Insufficient funds: Transmutation requires {ALCHEMY_BASE_CREDIT_COST:,} Credits for reactor ignition.",
            )

        cargo = captain.ship.cargo

        # 3. Catalyst check
        if recipe.catalyst == "organics":
            if cargo.organics < 1:
                return ActionResult(False, ActionType.ALCHEMY_TRANSMUTE, "Missing required catalyst: 1 crate of Organics.")
        else:
            cat_elem = cargo.elements.get(recipe.catalyst, 0)
            if cat_elem < 1:
                return ActionResult(False, ActionType.ALCHEMY_TRANSMUTE, f"Missing required catalyst: 1 unit of [{recipe.catalyst}].")

        # 4. Input materials check
        for inp_elem, qty in recipe.inputs.items():
            avail = cargo.unbonded(inp_elem)
            if avail < qty:
                return ActionResult(
                    False,
                    ActionType.ALCHEMY_TRANSMUTE,
                    f"Insufficient raw element [{inp_elem}]: {qty} required, {avail} present in cargo.",
                )

        # 5. Cargo space check
        total_input_units = sum(recipe.inputs.values())
        net_space_delta = recipe.output_qty - total_input_units
        if net_space_delta > 0 and cargo.available_space < net_space_delta:
            return ActionResult(
                False,
                ActionType.ALCHEMY_TRANSMUTE,
                f"Cargo hold full! Insufficient capacity for synthesized [{recipe.output_element}].",
            )

        # 6. Thermal containment and cryo-cooling
        current_heat = self.get_heat(captain.id)
        new_heat = current_heat + recipe.thermal_entropy

        used_coolant = False
        if new_heat > ALCHEMY_CRYO_COOLING_CAPACITY:
            # Check for cryogenic coolant in cargo
            if cargo.unbonded("cryogenite") >= 1:
                cargo.elements["cryogenite"] -= 1
                new_heat = max(0.0, new_heat - 25.0)
                used_coolant = True
            elif cargo.unbonded("H2O") >= 2:
                cargo.elements["H2O"] -= 2
                new_heat = max(0.0, new_heat - 15.0)
                used_coolant = True
            else:
                # Reactor warning: Core overheat vents radiation into sector
                new_heat = ALCHEMY_CRYO_COOLING_CAPACITY
                if kernel and getattr(kernel, "event_bus", None):
                    kernel.event_bus.broadcast_radio(
                        sender=captain.name,
                        text=f"CORE VENT ALERT: Sub-atomic reactor exceeded containment ({recipe.name})! Thermal radiation vented into Sector {captain.sector_id:03d}.",
                        channel="ALERT",
                        sector_id=captain.sector_id,
                    )

        self.heat_accumulated[captain.id] = new_heat

        # 7. Deduct costs and inputs
        captain.credits -= ALCHEMY_BASE_CREDIT_COST
        for inp_elem, qty in recipe.inputs.items():
            cargo.elements[inp_elem] -= qty
            if cargo.elements[inp_elem] <= 0:
                del cargo.elements[inp_elem]

        # 8. Deposit synthesized output
        cargo.elements[recipe.output_element] = cargo.elements.get(recipe.output_element, 0) + recipe.output_qty

        cool_str = " (Cryo-Coolant consumed to stabilize core)" if used_coolant else ""
        msg = f"SYNTHESIS COMPLETE: Transmuted {recipe.name} -> +{recipe.output_qty} [{recipe.output_element}]! Core Heat: {new_heat:.1f} MW.{cool_str}"
        if kernel and hasattr(kernel, "action_logs"):
            kernel.action_logs.append(f"[ALCHEMY] {captain.name} synthesized {recipe.name} (+{recipe.output_qty} {recipe.output_element}).")

        return ActionResult(
            True,
            ActionType.ALCHEMY_TRANSMUTE,
            msg,
            data={
                "recipe_id": recipe.id,
                "output_element": recipe.output_element,
                "output_qty": recipe.output_qty,
                "heat": new_heat,
            },
        )

    def induce_transmutation(
        self,
        captain: Captain,
        input_elements: Dict[str, int],
        catalyst: str,
        kernel: Any = None,
        sector_id: Optional[int] = None,
    ) -> ActionResult:
        """Executes sub-atomic nucleosynthesis and discovery across the 118+ table."""
        res = alchemical_induction(kernel, captain, input_elements, catalyst, sector_id=sector_id)
        if res.success and "heat" in (res.data or {}):
            h = float(res.data["heat"])
            self.heat_accumulated[captain.id] = self.get_heat(captain.id) + h
        return res

    def tick_alchemy(self, kernel: Any) -> None:
        """Passive reactor cooling each cycle."""
        for cid in list(self.heat_accumulated.keys()):
            self.cool_reactor(cid, amount=5.0)
            if self.heat_accumulated[cid] <= 0:
                del self.heat_accumulated[cid]

    def refine_isru(self, captain: Captain, recipe_id: str, kernel: Any = None) -> ActionResult:
        """
        Executes In-Situ Resource Utilization (ISRU) orbital smelting and chemical refining.
        Converts raw asteroid and deep-space extractions into high-value pure commodities and alloys.
        """
        rec_key = recipe_id.strip().upper()
        recipe = ISRU_RECIPES.get(rec_key)
        if not recipe:
            available = ", ".join(ISRU_RECIPES.keys())
            return ActionResult(False, ActionType.ISRU_REFINE, f"Unknown ISRU recipe '{recipe_id}'. Available: {available}")

        cargo = captain.ship.cargo

        # 1. Validate inputs
        for inp, qty in recipe.inputs.items():
            avail = _get_cargo_avail(cargo, inp)
            if avail < qty:
                return ActionResult(False, ActionType.ISRU_REFINE, f"Insufficient input [{inp}]: {qty} units required, {avail} available in hold.")

        # 2. Check hold capacity delta
        input_total = sum(recipe.inputs.values())
        output_total = sum(recipe.outputs.values())
        delta = output_total - input_total
        if delta > 0 and getattr(cargo, "available_space", 30) < delta:
            return ActionResult(False, ActionType.ISRU_REFINE, "Cargo holds full! Insufficient capacity for refined outputs.")

        # 3. Deduct inputs
        for inp, qty in recipe.inputs.items():
            _deduct_cargo(cargo, inp, qty)

        # 4. Deposit outputs
        for out, qty in recipe.outputs.items():
            _add_cargo(cargo, out, qty)

        ExperienceManager.award(captain, "industry", 15, kernel, key=f"isru:{recipe.id}")

        out_summary = ", ".join(f"+{v} [{k}]" for k, v in recipe.outputs.items())
        msg = f"ISRU REFINING COMPLETE: {recipe.name} executed successfully! Yielded {out_summary}."
        if kernel and hasattr(kernel, "action_logs"):
            kernel.action_logs.append(f"[ISRU] {captain.name} refined {recipe.name} ({out_summary}).")

        return ActionResult(
            True,
            ActionType.ISRU_REFINE,
            msg,
            data={"recipe_id": recipe.id, "outputs": dict(recipe.outputs)},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heat_accumulated": dict(self.heat_accumulated),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlchemyManager":
        mgr = cls()
        mgr.heat_accumulated = {k: float(v) for k, v in data.get("heat_accumulated", {}).items()}
        return mgr
