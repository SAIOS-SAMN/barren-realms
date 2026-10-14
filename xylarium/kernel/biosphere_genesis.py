"""
xylarium.kernel.biosphere_genesis: Biosphere Genesis & Deep Planetary Terraforming.

Enables sovereigns and captains to transform dead, airless worlds into living biospheres:
bombarding with volatile comets, deploying orbital equilibrium mirrors, inoculating with
xenobiological taxa, and watching new indigenous sentient species emerge.
"""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


@dataclass
class WorldGenesisRecord:
    planet_id: str
    sector_id: int
    atmospheric_pressure_bar: float = 0.05
    greenhouse_index: float = 0.20
    hydrosphere_pct: float = 0.0
    trophic_biomass: float = 0.0
    habitability_score: float = 0.05
    seeded_taxa: List[str] = field(default_factory=list)
    mirrors_deployed: int = 0
    comets_impacted: int = 0
    indigenous_born: bool = False

    def update_habitability(self) -> float:
        """
        Calculates composite habitability score in [0.0, 1.0] from physical equilibria.
        """
        # Pressure score: ideal ~ 0.8 - 1.2 bar
        p_score = max(0.0, 1.0 - abs(self.atmospheric_pressure_bar - 1.0) / 1.0)
        # Hydro score: ideal ~ 40 - 75%
        h_score = max(0.0, 1.0 - abs(self.hydrosphere_pct - 60.0) / 60.0)
        # Thermal greenhouse score: ideal ~ 0.9 - 1.1
        t_score = max(0.0, 1.0 - abs(self.greenhouse_index - 1.0) / 1.0)
        # Trophic biomass score: reaches 1.0 at 100 biomass
        b_score = min(1.0, self.trophic_biomass / 100.0)

        composite = (0.25 * p_score) + (0.25 * h_score) + (0.20 * t_score) + (0.30 * b_score)
        self.habitability_score = round(min(1.0, max(0.0, composite)), 3)
        return self.habitability_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planet_id": self.planet_id,
            "sector_id": self.sector_id,
            "atmospheric_pressure_bar": round(self.atmospheric_pressure_bar, 3),
            "greenhouse_index": round(self.greenhouse_index, 3),
            "hydrosphere_pct": round(self.hydrosphere_pct, 2),
            "trophic_biomass": round(self.trophic_biomass, 2),
            "habitability_score": self.habitability_score,
            "seeded_taxa": list(self.seeded_taxa),
            "mirrors_deployed": self.mirrors_deployed,
            "comets_impacted": self.comets_impacted,
            "indigenous_born": self.indigenous_born,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldGenesisRecord":
        return cls(**data)


class BiosphereGenesisManager:
    """
    Manages deep terraforming, comet atmospheric engineering, and biosphere emergence.
    """

    def __init__(self):
        self.records: Dict[str, WorldGenesisRecord] = {}

    def get_or_create_record(self, planet: Planet) -> WorldGenesisRecord:
        if planet.id not in self.records:
            is_barren = planet.planet_type in ["BARREN", "ICE", "DESERT", "VOLCANIC"]
            initial_p = 0.02 if is_barren else 0.85
            initial_hydro = 5.0 if is_barren else 65.0
            rec = WorldGenesisRecord(
                planet_id=planet.id,
                sector_id=planet.sector_id,
                atmospheric_pressure_bar=initial_p,
                hydrosphere_pct=initial_hydro,
            )
            rec.update_habitability()
            self.records[planet.id] = rec
        return self.records[planet.id]

    def bombard_comet(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str,
        volatiles_payload: int = 5,
    ) -> ActionResult:
        """
        Directs a redirected volatile ice comet into the target world's upper atmosphere,
        depositing water ice and volatile precursors.
        """
        planet = kernel.get_planet(planet_id)
        if not planet or planet.sector_id != captain.sector_id:
            return ActionResult(
                success=False,
                action=ActionType.TERRAFORM_BOMBARD_COMET,
                message=f"Planet '{planet_id}' not found in current sector.",
            )

        # Requires H2O or H in cargo holds
        comm_use = "H2O" if "H2O" in captain.ship.cargo.elements else ("H" if "H" in captain.ship.cargo.elements else None)
        if comm_use is None or captain.ship.cargo.elements[comm_use] < volatiles_payload:
            return ActionResult(
                success=False,
                action=ActionType.TERRAFORM_BOMBARD_COMET,
                message=f"Requires at least {volatiles_payload}x [H2O] or [H] volatile containment blocks in hold to steer comet payload.",
            )

        captain.ship.cargo.elements[comm_use] -= volatiles_payload
        if captain.ship.cargo.elements[comm_use] <= 0:
            del captain.ship.cargo.elements[comm_use]

        rec = self.get_or_create_record(planet)
        rec.comets_impacted += 1
        rec.atmospheric_pressure_bar += 0.08 * (volatiles_payload / 5.0)
        rec.hydrosphere_pct = min(100.0, rec.hydrosphere_pct + 4.5 * (volatiles_payload / 5.0))
        h_score = rec.update_habitability()

        msg = (
            f"VOLATILE COMET IMPACT: Directed {volatiles_payload}x [{comm_use}] into {planet.name}'s stratosphere! "
            f"Pressure rose to {rec.atmospheric_pressure_bar:.2f} bar, Hydrosphere reached {rec.hydrosphere_pct:.1f}%. "
            f"Habitability: {h_score:.1%}."
        )

        return ActionResult(
            success=True,
            action=ActionType.TERRAFORM_BOMBARD_COMET,
            message=msg,
            data=rec.to_dict(),
        )

    def deploy_orbital_mirror(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str,
    ) -> ActionResult:
        """
        Deploys an orbital photovoltaic mirror array to tune greenhouse thermal equilibrium.
        """
        planet = kernel.get_planet(planet_id)
        if not planet or planet.sector_id != captain.sector_id:
            return ActionResult(
                success=False,
                action=ActionType.TERRAFORM_DEPLOY_MIRROR,
                message=f"Planet '{planet_id}' not found in current sector.",
            )

        cost_cr = 15000
        fe_req = 10
        fe_held = (captain.ship.cargo.elements.get("Fe", 0) +
                   captain.ship.cargo.elements.get("fe", 0) +
                   captain.ship.cargo.equipment +
                   captain.ship.cargo.elements.get("EQUIPMENT", 0))
        if captain.credits < cost_cr or fe_held < fe_req:
            return ActionResult(
                success=False,
                action=ActionType.TERRAFORM_DEPLOY_MIRROR,
                message=f"Requires {cost_cr:,} Cr and {fe_req}x [Fe] or Equipment for orbital mirror array.",
            )

        captain.credits -= cost_cr
        if "Fe" in captain.ship.cargo.elements and captain.ship.cargo.elements["Fe"] >= fe_req:
            captain.ship.cargo.elements["Fe"] -= fe_req
            if captain.ship.cargo.elements["Fe"] <= 0:
                del captain.ship.cargo.elements["Fe"]
        elif "fe" in captain.ship.cargo.elements and captain.ship.cargo.elements["fe"] >= fe_req:
            captain.ship.cargo.elements["fe"] -= fe_req
            if captain.ship.cargo.elements["fe"] <= 0:
                del captain.ship.cargo.elements["fe"]
        elif captain.ship.cargo.equipment >= fe_req:
            captain.ship.cargo.equipment -= fe_req
        elif "EQUIPMENT" in captain.ship.cargo.elements:
            captain.ship.cargo.elements["EQUIPMENT"] -= fe_req
            if captain.ship.cargo.elements["EQUIPMENT"] <= 0:
                del captain.ship.cargo.elements["EQUIPMENT"]

        rec = self.get_or_create_record(planet)
        rec.mirrors_deployed += 1
        rec.greenhouse_index = round(min(1.5, rec.greenhouse_index + 0.15), 3)
        h_score = rec.update_habitability()

        msg = (
            f"ORBITAL MIRROR DEPLOYED: Positioned solar reflector array #{rec.mirrors_deployed} in geostationary orbit of {planet.name}! "
            f"Greenhouse Thermal Index adjusted to {rec.greenhouse_index:.2f}. Habitability: {h_score:.1%}."
        )

        return ActionResult(
            success=True,
            action=ActionType.TERRAFORM_DEPLOY_MIRROR,
            message=msg,
            data=rec.to_dict(),
        )

    def seed_biosphere(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str,
        taxon_sample: str = "Canopy Chlorophyte",
    ) -> ActionResult:
        """
        Inoculates the world with xenobiological culture strains to bootstrap
        the primary trophic food web.
        """
        planet = kernel.get_planet(planet_id)
        if not planet or planet.sector_id != captain.sector_id:
            return ActionResult(
                success=False,
                action=ActionType.TERRAFORM_SEED_BIOSPHERE,
                message=f"Planet '{planet_id}' not found in current sector.",
            )

        rec = self.get_or_create_record(planet)
        if rec.atmospheric_pressure_bar < 0.05 or rec.hydrosphere_pct < 2.0:
            return ActionResult(
                success=False,
                action=ActionType.TERRAFORM_SEED_BIOSPHERE,
                message=f"{planet.name} environment too hostile for life (Atmosphere: {rec.atmospheric_pressure_bar:.2f} bar, Water: {rec.hydrosphere_pct:.1f}%). Must bombard with comets first.",
            )

        # Requires ORGANICS or XENOPROTEIN
        comm_use = None
        if "XENOPROTEIN" in captain.ship.cargo.elements and captain.ship.cargo.elements["XENOPROTEIN"] >= 1:
            comm_use = "XENOPROTEIN"
        elif captain.ship.cargo.organics >= 2:
            comm_use = "ORGANICS"
        elif "ORGANICS" in captain.ship.cargo.elements and captain.ship.cargo.elements["ORGANICS"] >= 2:
            comm_use = "ORGANICS_ELEM"

        if comm_use is None:
            return ActionResult(
                success=False,
                action=ActionType.TERRAFORM_SEED_BIOSPHERE,
                message="Requires at least 1x [XENOPROTEIN] or 2x [ORGANICS] culture media to inoculate biosphere.",
            )

        if comm_use == "XENOPROTEIN":
            captain.ship.cargo.elements["XENOPROTEIN"] -= 1
            if captain.ship.cargo.elements["XENOPROTEIN"] <= 0:
                del captain.ship.cargo.elements["XENOPROTEIN"]
            biomass_gain = 35.0
        elif comm_use == "ORGANICS":
            captain.ship.cargo.organics -= 2
            biomass_gain = 20.0
        else:
            captain.ship.cargo.elements["ORGANICS"] -= 2
            if captain.ship.cargo.elements["ORGANICS"] <= 0:
                del captain.ship.cargo.elements["ORGANICS"]
            biomass_gain = 20.0

        rec.seeded_taxa.append(taxon_sample)
        rec.trophic_biomass += biomass_gain
        h_score = rec.update_habitability()

        msg = (
            f"BIOSPHERE INOCULATED: Introduced {taxon_sample} into {planet.name}'s surface aquifers! "
            f"Trophic biomass expanded to {rec.trophic_biomass:.1f} MT. Habitability: {h_score:.1%}."
        )

        # Emergent Sentinel Life Check
        if h_score >= 0.70 and rec.trophic_biomass >= 80.0 and not rec.indigenous_born:
            rec.indigenous_born = True
            msg += f" SENTIENT EMERGENCE: Indigenous sentient ecosystem has awakened on {planet.name}! Prime Directive stewardship engaged."

        return ActionResult(
            success=True,
            action=ActionType.TERRAFORM_SEED_BIOSPHERE,
            message=msg,
            data=rec.to_dict(),
        )

    def tick(self, kernel: Any) -> None:
        """Natural ecological growth on seeded worlds and emergent sentience check."""
        for rec in self.records.values():
            if rec.trophic_biomass > 0 and rec.habitability_score > 0.30:
                # Biomass natural growth
                growth = min(2.0, 0.05 * rec.trophic_biomass * rec.habitability_score)
                rec.trophic_biomass += growth
                rec.update_habitability()

            if rec.habitability_score >= 0.70 and rec.trophic_biomass >= 80.0 and not rec.indigenous_born:
                rec.indigenous_born = True
                p = kernel.get_planet(rec.planet_id) if kernel else None
                if p and hasattr(kernel, "event_bus"):
                    kernel.event_bus.broadcast_radio(
                        sender="GENESIS/ECOSYSTEM",
                        text=f"SENTIENT EMERGENCE: Indigenous sentient ecosystem has awakened on {p.name}!",
                        channel="GENESIS-WIRE",
                        sector_id=rec.sector_id,
                    )

    def to_dict(self) -> Dict[str, Any]:
        return {"records": {k: v.to_dict() for k, v in self.records.items()}}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BiosphereGenesisManager":
        mgr = cls()
        for k, v in data.get("records", {}).items():
            mgr.records[k] = WorldGenesisRecord.from_dict(v)
        return mgr
