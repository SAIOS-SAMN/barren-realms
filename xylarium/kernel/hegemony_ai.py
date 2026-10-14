"""
xylarium/kernel/hegemony_ai.py

Project 2: Grand Hegemony AI & Galactic Total War ("The Sovereigns Engine")

Elevates rival galactic factions into autonomous grand strategy empires:
  - Factions recruit standing armada fleets, mobilize dreadnoughts, and project power.
  - Dynamic orbital sieges of planetary grids, shield collapse, and planetary annexation.
  - Inter-empire diplomacy, non-aggression compacts, and mercenary proxy strikes.
"""

from dataclasses import asdict, dataclass, field
import random
from typing import Any, Dict, List, Optional

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


@dataclass
class ArmadaFleet:
    id: str
    faction_id: str
    sector_id: int
    target_sector: Optional[int]
    fleet_power: int
    ships: int
    siege_progress: float = 0.0
    status: str = "PATROLLING"  # PATROLLING, MARCHING, SIEGING

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArmadaFleet":
        return cls(**data)


@dataclass
class HegemonicFaction:
    id: str
    name: str
    home_sector: int
    treasury: int
    aggression: float  # 0.0 to 1.0
    color: str
    controlled_sectors: List[int] = field(default_factory=list)
    treaties: Dict[str, str] = field(default_factory=dict)  # faction_id -> "PEACE" | "WAR"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HegemonicFaction":
        return cls(**data)


class HegemonyAIManager:
    """Simulates autonomous galactic great powers, fleet maneuvers, and total war."""

    def __init__(self) -> None:
        self.factions: Dict[str, HegemonicFaction] = {}
        self.armadas: Dict[str, ArmadaFleet] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factions": {k: v.to_dict() for k, v in self.factions.items()},
            "armadas": {k: v.to_dict() for k, v in self.armadas.items()},
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "HegemonyAIManager":
        mgr = cls()
        if not data:
            return mgr
        for k, v in data.get("factions", {}).items():
            mgr.factions[k] = HegemonicFaction.from_dict(v)
        for k, v in data.get("armadas", {}).items():
            mgr.armadas[k] = ArmadaFleet.from_dict(v)
        return mgr

    def seed_initial_factions(self, kernel: Any) -> None:
        """Initializes the three great powers if not already created."""
        if self.factions:
            return

        imperium = HegemonicFaction(
            id="IMPERIUM",
            name="Aurelian Imperium",
            home_sector=15,
            treasury=150000,
            aggression=0.75,
            color="GOLD",
            controlled_sectors=[15, 16],
            treaties={"CHOIR": "WAR", "SYNDICATE": "PEACE"}
        )
        choir = HegemonicFaction(
            id="CHOIR",
            name="Choir of the Pyre",
            home_sector=80,
            treasury=120000,
            aggression=0.85,
            color="MAGENTA",
            controlled_sectors=[80, 81],
            treaties={"IMPERIUM": "WAR", "SYNDICATE": "WAR"}
        )
        syndicate = HegemonicFaction(
            id="SYNDICATE",
            name="Obsidian Syndicate",
            home_sector=65,
            treasury=200000,
            aggression=0.50,
            color="RED",
            controlled_sectors=[65],
            treaties={"IMPERIUM": "PEACE", "CHOIR": "WAR"}
        )

        for f in (imperium, choir, syndicate):
            self.factions[f.id] = f

        # Spawn initial armadas
        self.armadas["ARM-IMP-01"] = ArmadaFleet(
            id="ARM-IMP-01",
            faction_id="IMPERIUM",
            sector_id=15,
            target_sector=None,
            fleet_power=650,
            ships=12,
        )
        self.armadas["ARM-CHOIR-01"] = ArmadaFleet(
            id="ARM-CHOIR-01",
            faction_id="CHOIR",
            sector_id=80,
            target_sector=None,
            fleet_power=800,
            ships=16,
        )
        self.armadas["ARM-SYN-01"] = ArmadaFleet(
            id="ARM-SYN-01",
            faction_id="SYNDICATE",
            sector_id=65,
            target_sector=None,
            fleet_power=500,
            ships=8,
        )

    def enlist_mercenary_strike(
        self,
        kernel: Any,
        captain: Captain,
        faction_id: str,
        target_sector: int
    ) -> ActionResult:
        """Hires an imperial or syndicate armada to march on and siege target sector."""
        faction = self.factions.get(faction_id)
        if not faction:
            return ActionResult(
                success=False,
                action=ActionType.HEGEMONY_ENLIST_STRIKE,
                message=f"Faction '{faction_id}' not found. Available: IMPERIUM, CHOIR, SYNDICATE.",
            )
        if target_sector not in kernel.sectors:
            return ActionResult(
                success=False,
                action=ActionType.HEGEMONY_ENLIST_STRIKE,
                message=f"Sector {target_sector} does not exist.",
            )

        fee = 25000
        if captain.credits < fee:
            return ActionResult(
                success=False,
                action=ActionType.HEGEMONY_ENLIST_STRIKE,
                message=f"Hiring a {faction.name} armada requires {fee:,} credits.",
            )

        captain.credits -= fee
        faction.treasury += fee

        # Find an idle armada or commission one
        fleet = None
        for a in self.armadas.values():
            if a.faction_id == faction_id and a.status in ("PATROLLING", "IDLE"):
                fleet = a
                break

        if not fleet:
            fleet_id = f"ARM-{faction_id[:3]}-{random.randint(10, 99)}"
            fleet = ArmadaFleet(
                id=fleet_id,
                faction_id=faction_id,
                sector_id=faction.home_sector,
                target_sector=target_sector,
                fleet_power=600,
                ships=10,
                status="MARCHING",
            )
            self.armadas[fleet_id] = fleet
        else:
            fleet.target_sector = target_sector
            fleet.status = "MARCHING"

        return ActionResult(
            success=True,
            action=ActionType.HEGEMONY_ENLIST_STRIKE,
            turns_spent=0,
            message=f"CONTRACT SIGNED: {faction.name} armada [{fleet.id}] mobilized to assault Sector {target_sector}!",
            data={"armada": fleet.to_dict()}
        )

    def tick(self, kernel: Any) -> None:
        """Cycle tick: moves armadas, conducts sieges, and annexes worlds."""
        for armada in list(self.armadas.values()):
            sec = kernel.sectors.get(armada.sector_id)
            if not sec:
                continue

            # If marching towards a target sector
            if armada.status == "MARCHING" and armada.target_sector:
                if armada.sector_id == armada.target_sector:
                    armada.status = "SIEGING"
                else:
                    # Hop one step closer via warps
                    if sec.warps:
                        # Pick warp closest to target
                        next_sec = random.choice(sec.warps)
                        armada.sector_id = next_sec

            # If sieging planets in sector
            elif armada.status == "SIEGING":
                if sec.planets:
                    target_planet = sec.planets[0]
                    # Orbital bombardment
                    shields = getattr(target_planet, "shields", 0)
                    if shields > 0:
                        target_planet.shields = max(0, shields - 40)
                    else:
                        fighters = getattr(target_planet, "fighters", 0)
                        if fighters > 0:
                            target_planet.fighters = max(0, fighters - 15)
                        else:
                            # Annex world
                            target_planet.owner_id = armada.faction_id
                            target_planet.faction_id = armada.faction_id
                            target_planet.shields = 100
                            armada.status = "PATROLLING"
                            armada.target_sector = None
                            fac = self.factions.get(armada.faction_id)
                            if fac and sec.id not in fac.controlled_sectors:
                                fac.controlled_sectors.append(sec.id)
                            kernel.action_logs.append(
                                f"[HEGEMONY] {fac.name if fac else armada.faction_id} has captured {target_planet.name} in Sector {sec.id}!"
                            )
