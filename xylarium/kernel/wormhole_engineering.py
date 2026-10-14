"""
xylarium/kernel/wormhole_engineering.py

Project 1: Dynamic Hyperlane & Wormhole Engineering ("The Chasm Bridges")

Allows civilizations and captains to dynamically alter the galactic spatial graph:
  - Construct artificial Jump Gates between distant sectors, altering warp topologies.
  - Collapse unstable wormholes and choke-points to seal borders against hostile armadas.
  - Deploy automated Toll Buoys that tax passing merchant haulers and fleets.
"""

from dataclasses import asdict, dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Sector


@dataclass
class JumpGate:
    id: str
    origin_sector: int
    target_sector: int
    builder_id: str
    integrity: float = 100.0
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JumpGate":
        return cls(**data)


@dataclass
class TollBuoy:
    id: str
    sector_id: int
    owner_id: str
    toll_fee_credits: int
    total_revenue_collected: int = 0
    currency: str = "SOL"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TollBuoy":
        return cls(**data)


class WormholeEngineeringManager:
    """Manages artificial hyperlane creation, wormhole severing, and automated toll networks."""

    def __init__(self) -> None:
        self.jump_gates: Dict[str, JumpGate] = {}
        self.toll_buoys: Dict[int, TollBuoy] = {}  # keyed by sector_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jump_gates": {k: v.to_dict() for k, v in self.jump_gates.items()},
            "toll_buoys": {str(k): v.to_dict() for k, v in self.toll_buoys.items()},
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "WormholeEngineeringManager":
        mgr = cls()
        if not data:
            return mgr
        for k, v in data.get("jump_gates", {}).items():
            mgr.jump_gates[k] = JumpGate.from_dict(v)
        for k, v in data.get("toll_buoys", {}).items():
            mgr.toll_buoys[int(k)] = TollBuoy.from_dict(v)
        return mgr

    def construct_jump_gate(
        self,
        kernel: Any,
        captain: Captain,
        target_sector: int,
    ) -> ActionResult:
        """Constructs an artificial Jump Gate between captain's sector and target sector."""
        origin = captain.sector_id
        if origin == target_sector:
            return ActionResult(
                success=False,
                action=ActionType.GATE_CONSTRUCT,
                message="Cannot link a Jump Gate to the same sector.",
            )
        if target_sector not in kernel.sectors:
            return ActionResult(
                success=False,
                action=ActionType.GATE_CONSTRUCT,
                message=f"Target Sector {target_sector} does not exist in charted galaxy.",
            )

        # Check existing connection
        sec_orig = kernel.sectors[origin]
        sec_targ = kernel.sectors[target_sector]
        if target_sector in sec_orig.warps:
            return ActionResult(
                success=False,
                action=ActionType.GATE_CONSTRUCT,
                message=f"Sector {origin} and Sector {target_sector} are already connected via warp lane.",
            )

        # Costs: 20 Equipment, 15,000 Credits
        sol_cost = 15000
        equip_cost = 20
        if captain.credits < sol_cost:
            return ActionResult(
                success=False,
                action=ActionType.GATE_CONSTRUCT,
                message=f"Constructing a Jump Gate requires {sol_cost:,} credits (you have {captain.credits:,}).",
            )
        if captain.ship.cargo.equipment < equip_cost:
            return ActionResult(
                success=False,
                action=ActionType.GATE_CONSTRUCT,
                message=f"Constructing a Jump Gate requires {equip_cost} Equipment in cargo.",
            )

        captain.credits -= sol_cost
        captain.ship.cargo.equipment -= equip_cost

        gate_id = f"GATE-{min(origin, target_sector):03d}-{max(origin, target_sector):03d}"
        gate = JumpGate(
            id=gate_id,
            origin_sector=origin,
            target_sector=target_sector,
            builder_id=captain.id,
        )
        self.jump_gates[gate_id] = gate

        # Alter topological graph dynamically
        if target_sector not in sec_orig.warps:
            sec_orig.warps.append(target_sector)
        if origin not in sec_targ.warps:
            sec_targ.warps.append(origin)
        kernel.graph_version = getattr(kernel, "graph_version", 0) + 1

        return ActionResult(
            success=True,
            action=ActionType.GATE_CONSTRUCT,
            turns_spent=2,
            message=f"JUMP GATE ONLINE! Engineered artificial hyperlane between Sector {origin} and Sector {target_sector}.",
            data={"gate": gate.to_dict()}
        )

    def collapse_wormhole(
        self,
        kernel: Any,
        captain: Captain,
        target_sector: int,
    ) -> ActionResult:
        """Detonates a gravitational resonance charge to collapse a warp lane connection."""
        origin = captain.sector_id
        sec_orig = kernel.sectors.get(origin)
        sec_targ = kernel.sectors.get(target_sector)

        if not sec_orig or not sec_targ or target_sector not in sec_orig.warps:
            return ActionResult(
                success=False,
                action=ActionType.WORMHOLE_COLLAPSE,
                message=f"No warp lane exists between Sector {origin} and Sector {target_sector}.",
            )

        # Protect Sol Central from being isolated
        if origin == 1 or target_sector == 1:
            return ActionResult(
                success=False,
                action=ActionType.WORMHOLE_COLLAPSE,
                message="Federal Prime Directives prohibit collapsing primary arterial lanes linked to Sector 1 (Sol Central).",
            )

        # Requires 10 Ore, 5,000 Credits for resonance charge
        sol_cost = 5000
        ore_cost = 10
        if captain.credits < sol_cost:
            return ActionResult(
                success=False,
                action=ActionType.WORMHOLE_COLLAPSE,
                message=f"Gravitational collapse charge requires {sol_cost:,} credits.",
            )
        if captain.ship.cargo.ore < ore_cost:
            return ActionResult(
                success=False,
                action=ActionType.WORMHOLE_COLLAPSE,
                message=f"Resonance charge requires {ore_cost} Ore in cargo.",
            )

        captain.credits -= sol_cost
        captain.ship.cargo.ore -= ore_cost

        # Sever lane
        if target_sector in sec_orig.warps:
            sec_orig.warps.remove(target_sector)
        if origin in sec_targ.warps:
            sec_targ.warps.remove(origin)

        # Remove any gate tracking
        gate_id = f"GATE-{min(origin, target_sector):03d}-{max(origin, target_sector):03d}"
        if gate_id in self.jump_gates:
            del self.jump_gates[gate_id]

        kernel.graph_version = getattr(kernel, "graph_version", 0) + 1

        return ActionResult(
            success=True,
            action=ActionType.WORMHOLE_COLLAPSE,
            turns_spent=1,
            message=f"WORMHOLE COLLAPSED! Severed subspace connection between Sector {origin} and Sector {target_sector}.",
        )

    def deploy_toll_buoy(
        self,
        kernel: Any,
        captain: Captain,
        toll_fee: int = 250,
    ) -> ActionResult:
        """Deploys an automated toll gate buoy in current sector to tax traffic."""
        sector_id = captain.sector_id
        if sector_id in self.toll_buoys:
            return ActionResult(
                success=False,
                action=ActionType.TOLL_BUOY_DEPLOY,
                message=f"Sector {sector_id} already has an active Toll Buoy.",
            )

        cost = 8000
        if captain.credits < cost:
            return ActionResult(
                success=False,
                action=ActionType.TOLL_BUOY_DEPLOY,
                message=f"Deploying a Toll Buoy requires {cost:,} credits.",
            )

        captain.credits -= cost
        buoy = TollBuoy(
            id=f"TOLL-SEC-{sector_id:03d}",
            sector_id=sector_id,
            owner_id=captain.id,
            toll_fee_credits=max(50, min(2000, toll_fee)),
        )
        self.toll_buoys[sector_id] = buoy

        return ActionResult(
            success=True,
            action=ActionType.TOLL_BUOY_DEPLOY,
            turns_spent=0,
            message=f"TOLL BUOY DEPLOYED in Sector {sector_id}! Collecting {buoy.toll_fee_credits} Cr from transit traffic.",
            data={"buoy": buoy.to_dict()}
        )

    def collect_transit_toll(self, kernel: Any, sector_id: int, traveller_id: str) -> int:
        """Invoked when a ship moves into a sector with an active toll buoy."""
        buoy = self.toll_buoys.get(sector_id)
        if not buoy or buoy.owner_id == traveller_id:
            return 0
        fee = buoy.toll_fee_credits
        owner = kernel.captains.get(buoy.owner_id)
        if owner:
            owner.credits += fee
            buoy.total_revenue_collected += fee
        return fee

    def tick(self, kernel: Any) -> None:
        """Periodic simulation tick: checks gate integrity and passive dividend collection."""
        pass
