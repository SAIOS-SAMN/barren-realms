"""
Precursor Alchemy & Elemental Transmutation Engine for Xylarium.
Ported from Netstratum 34_MATTER_BALANCE and 31_ELEMENT_COMMERCE.
Governs sub-atomic nucleosynthesis and elemental transmutation over the 24-element periodic table.
Transmutes base volatiles and structural metals into high-tier exotics and manufactured gems,
balancing reaction thermal entropy against cryogenic cooling infrastructure.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from xylarium.config import (
    ALCHEMY_ENTROPY_HEAT_PER_REACTION,
    ALCHEMY_CRYO_COOLING_CAPACITY,
    ALCHEMY_BASE_CREDIT_COST,
)
from xylarium.kernel.models import ActionResult, ActionType, Captain, Ship, CargoHold
from xylarium.kernel.elements import PeriodicTable


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
            if not r.required_tech or r.required_tech in getattr(captain, "technologies", []):
                available.append(r)
        return available

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
        if recipe.required_tech and recipe.required_tech not in getattr(captain, "technologies", []):
            return ActionResult(
                False,
                ActionType.ALCHEMY_TRANSMUTE,
                f"LACKING TECHNOLOGY: Recipe requires '{recipe.required_tech}' blueprint unlocked in your Research Mint.",
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

    def tick_alchemy(self, kernel: Any) -> None:
        """Passive reactor cooling each cycle."""
        for cid in list(self.heat_accumulated.keys()):
            self.cool_reactor(cid, amount=5.0)
            if self.heat_accumulated[cid] <= 0:
                del self.heat_accumulated[cid]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heat_accumulated": dict(self.heat_accumulated),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlchemyManager":
        mgr = cls()
        mgr.heat_accumulated = {k: float(v) for k, v in data.get("heat_accumulated", {}).items()}
        return mgr
