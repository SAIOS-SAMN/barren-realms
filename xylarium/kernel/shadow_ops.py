"""
xylarium/kernel/shadow_ops.py

Project 4: Interstellar Espionage & Shadow Corporations ("The Black Ledger")

Enables asymmetric shadow warfare, corporate espionage, and covert operations:
  - Anonymous shell corporations to launder black-market wealth and evade taxes.
  - Infiltration of rival planetary citadels with sleeper cells to execute grid sabotage,
    treasury siphons, and civil insurrection.
  - False-flag military strikes using spoofed transponders to provoke inter-empire wars.
"""

from dataclasses import asdict, dataclass, field
import random
from typing import Any, Dict, List, Optional

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


@dataclass
class ShadowShellCompany:
    id: str
    name: str
    owner_id: str
    laundered_credits: int = 0
    front_sector: int = 65

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShadowShellCompany":
        return cls(**data)


@dataclass
class SleeperCell:
    id: str
    planet_id: str
    owner_id: str
    cover_level: float = 0.90
    compromised: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SleeperCell":
        return cls(**data)


class ShadowOpsManager:
    """Manages shadow shell companies, sleeper cell infiltration, and false-flag operations."""

    def __init__(self) -> None:
        self.shell_companies: Dict[str, ShadowShellCompany] = {}
        self.sleeper_cells: Dict[str, SleeperCell] = {}  # keyed by planet_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shell_companies": {k: v.to_dict() for k, v in self.shell_companies.items()},
            "sleeper_cells": {k: v.to_dict() for k, v in self.sleeper_cells.items()},
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ShadowOpsManager":
        mgr = cls()
        if not data:
            return mgr
        for k, v in data.get("shell_companies", {}).items():
            mgr.shell_companies[k] = ShadowShellCompany.from_dict(v)
        for k, v in data.get("sleeper_cells", {}).items():
            mgr.sleeper_cells[k] = SleeperCell.from_dict(v)
        return mgr

    def incorporate_shell_company(
        self,
        kernel: Any,
        captain: Captain,
        company_name: str
    ) -> ActionResult:
        """Incorporate an anonymous off-the-books shadow company."""
        cid = f"SHELL-{captain.id[:6]}-{random.randint(100, 999)}"
        fee = 10000
        if captain.credits < fee:
            return ActionResult(
                success=False,
                action=ActionType.SHADOW_INCORPORATE_SHELL,
                message=f"Incorporating an anonymous shell company requires {fee:,} credits.",
            )

        captain.credits -= fee
        shell = ShadowShellCompany(
            id=cid,
            name=company_name or "Obsidian Holdings Anon",
            owner_id=captain.id,
            front_sector=captain.sector_id,
        )
        self.shell_companies[cid] = shell

        return ActionResult(
            success=True,
            action=ActionType.SHADOW_INCORPORATE_SHELL,
            turns_spent=0,
            message=f"SHADOW CORPORATION INCORPORATED: '{shell.name}' [{shell.id}]. Untraceable financial channels established.",
            data={"shell": shell.to_dict()}
        )

    def plant_sleeper_cell(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str
    ) -> ActionResult:
        """Infiltrates a target world and plants an embedded sleeper agent."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.SHADOW_PLANT_SLEEPER,
                message=f"Planet '{planet_id}' not found.",
            )

        if planet.id in self.sleeper_cells and not self.sleeper_cells[planet.id].compromised:
            return ActionResult(
                success=False,
                action=ActionType.SHADOW_PLANT_SLEEPER,
                message=f"You already have an active sleeper cell embedded in {planet.name}.",
            )

        cost = 6000
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.SHADOW_PLANT_SLEEPER,
                message=f"Infiltration and sleeper cell embedding requires {cost:,} credits.",
            )

        captain.credits -= cost
        cell = SleeperCell(
            id=f"CELL-{planet.id[:8]}",
            planet_id=planet.id,
            owner_id=captain.id,
        )
        self.sleeper_cells[planet.id] = cell

        return ActionResult(
            success=True,
            action=ActionType.SHADOW_PLANT_SLEEPER,
            turns_spent=1,
            message=f"SLEEPER CELL EMBEDDED on {planet.name}! Cover identity verified. Ready for covert sabotage.",
            data={"cell": cell.to_dict()}
        )

    def execute_sabotage(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str,
        target_subsystem: str = "GRID"
    ) -> ActionResult:
        """Triggers sleeper cell to execute citadel sabotage."""
        cell = self.sleeper_cells.get(planet_id)
        if not cell or cell.compromised:
            return ActionResult(
                success=False,
                action=ActionType.SHADOW_EXECUTE_SABOTAGE,
                message="No active sleeper cell embedded on this planet.",
            )

        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.SHADOW_EXECUTE_SABOTAGE,
                message=f"Planet '{planet_id}' not found.",
            )

        target = target_subsystem.upper()
        if target == "GRID":
            old_shields = getattr(planet, "shields", 0)
            planet.shields = int(old_shields * 0.40)
            diff = old_shields - planet.shields
            return ActionResult(
                success=True,
                action=ActionType.SHADOW_EXECUTE_SABOTAGE,
                turns_spent=1,
                message=f"SABOTAGE SUCCESSFUL: Power conduit overloaded on {planet.name}! Shields dropped by {diff} (-60%).",
            )
        elif target == "TREASURY":
            stolen = min(25000, max(1000, getattr(planet, "treasury", 0) // 2))
            planet.treasury = max(0, getattr(planet, "treasury", 0) - stolen)
            captain.credits += stolen
            return ActionResult(
                success=True,
                action=ActionType.SHADOW_EXECUTE_SABOTAGE,
                turns_spent=1,
                message=f"TREASURY HEIST: Siphoned {stolen:,} Cr from {planet.name}'s vaults into the black ledger!",
            )

        return ActionResult(
            success=False,
            action=ActionType.SHADOW_EXECUTE_SABOTAGE,
            message="Unknown sabotage target. Valid: GRID, TREASURY.",
        )

    def stage_false_flag(
        self,
        kernel: Any,
        captain: Captain,
        target_sector: int,
        framed_faction: str = "CHOIR"
    ) -> ActionResult:
        """Executes a false-flag strike using spoofed transponder frequencies."""
        cost = 18000
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.SHADOW_FALSE_FLAG_STRIKE,
                message=f"Executing a False-Flag operation requires {cost:,} credits for spoofing beacons.",
            )

        captain.credits -= cost
        # Broadcast forged hostile radio transmission
        if hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender=f"{framed_faction}_WAR_COMMAND",
                text=f"Subspace distress! {framed_faction} battlecruisers have conducted an unprovoked raid in Sector {target_sector}!",
                channel="SUBSPACE_EMERGENCY",
            )
        kernel.action_logs.append(
            f"[SHADOW OPS] False-flag operation successful: {framed_faction} framed for sector aggression!"
        )

        return ActionResult(
            success=True,
            action=ActionType.SHADOW_FALSE_FLAG_STRIKE,
            turns_spent=1,
            message=f"FALSE-FLAG OP COMPLETE: Attacked Sector {target_sector} with spoofed transponders. {framed_faction} framed!",
        )

    def tick(self, kernel: Any) -> None:
        """Simulation cycle tick."""
        pass
