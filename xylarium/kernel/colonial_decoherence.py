"""
xylarium/kernel/colonial_decoherence.py

Colonial Decoherence & Imperial Horizon Mechanics.

Simulates the relativistic and network decoherence of multi-world empires.
When worlds span across distant sectors and communication lag breaches the
realm's coordination horizon, colonial divergence occurs:
  - Divergent cultures and local tariff evasion.
  - Secessionist unrest and political drift.
  - Sovereigns must deploy Subspace Coherence Relays, dispatch ennobled envoys,
    or socket Precursor Coherence Shards to preserve realm integrity.
"""

from collections import deque
from dataclasses import asdict, dataclass
import math
from typing import Any, Dict, List, Optional

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector


@dataclass
class ColonialDecoherenceRecord:
    planet_id: str
    planet_name: str
    sector_id: int
    owner_id: str
    distance_hops: int
    decoherence_index: float  # 0.0 (perfect coherence) to 1.0 (total fracture)
    unrest: float             # 0.0 to 100.0
    tariff_leak: float        # 0.0 to 0.50
    status: str               # "STABLE", "STRAINED", "DIVERGENT", "SECESSIONIST"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ColonialDecoherenceRecord":
        return cls(**data)


class ColonialDecoherenceManager:
    """Tracks and simulates colonial decoherence across star systems."""

    def __init__(self) -> None:
        self.records: Dict[str, ColonialDecoherenceRecord] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "records": {k: v.to_dict() for k, v in self.records.items()}
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ColonialDecoherenceManager":
        mgr = cls()
        if not data:
            return mgr
        for k, v in data.get("records", {}).items():
            mgr.records[k] = ColonialDecoherenceRecord.from_dict(v)
        return mgr

    def _shortest_path_hops(self, kernel: Any, start_sector: int, target_sector: int) -> int:
        """Finds hop distance between two sectors via sector warp lanes."""
        if start_sector == target_sector:
            return 0
        queue = deque([(start_sector, 0)])
        visited = {start_sector}
        while queue:
            curr, hops = queue.popleft()
            sec = kernel.sectors.get(curr)
            if not sec:
                continue
            for neighbor in sec.warps:
                if neighbor == target_sector:
                    return hops + 1
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, hops + 1))
        return 999  # unreachable

    def get_owner_seat_sector(self, kernel: Any, owner_id: str) -> int:
        """Determines the primary sovereign seat/homeworld of an owner."""
        # If captain, check their starting or current homeworld sector
        cap = kernel.captains.get(owner_id)
        if cap:
            return 1  # Standard Federation seat / Sol
        # Check first claimed planet
        for s in kernel.sectors.values():
            for p in getattr(s, "planets", []):
                if p.owner_id == owner_id and getattr(p, "citadel_level", 0) >= 1:
                    return s.id
        return 1

    def assess_world(self, kernel: Any, planet: Planet) -> Optional[ColonialDecoherenceRecord]:
        """Calculates current decoherence for a claimed world."""
        if not planet.owner_id:
            return None
        seat_sector = self.get_owner_seat_sector(kernel, planet.owner_id)
        hops = self._shortest_path_hops(kernel, seat_sector, planet.sector_id)
        
        # Base decoherence scales with network distance past 1 hop
        base_deco = max(0.0, min(1.0, (hops - 1) * 0.18)) if hops > 1 else 0.0
        
        rec = self.records.get(planet.id)
        if not rec:
            rec = ColonialDecoherenceRecord(
                planet_id=planet.id,
                planet_name=planet.name,
                sector_id=planet.sector_id,
                owner_id=planet.owner_id,
                distance_hops=hops,
                decoherence_index=base_deco,
                unrest=base_deco * 40.0,
                tariff_leak=base_deco * 0.25,
                status="STABLE" if base_deco < 0.30 else "STRAINED"
            )
            self.records[planet.id] = rec
        else:
            rec.distance_hops = hops
            rec.owner_id = planet.owner_id
            rec.sector_id = planet.sector_id

        return rec

    def stabilize(
        self,
        kernel: Any,
        captain: Captain,
        planet_id: str,
        method: str = "RELAY"
    ) -> ActionResult:
        """Applies stabilization measures to reduce colonial decoherence and unrest."""
        planet = kernel.get_planet(planet_id)
        if not planet:
            return ActionResult(
                success=False,
                action=ActionType.STABILIZE_DECOHERENCE,
                message=f"Planet '{planet_id}' not found.",
            )

        if planet.sector_id != captain.sector_id:
            return ActionResult(
                success=False,
                action=ActionType.STABILIZE_DECOHERENCE,
                message=f"Cannot stabilize {planet.name}: you must be in Sector {planet.sector_id} (currently in Sector {captain.sector_id}).",
            )

        rec = self.assess_world(kernel, planet)
        if not rec:
            return ActionResult(
                success=False,
                action=ActionType.STABILIZE_DECOHERENCE,
                message=f"{planet.name} is not a claimed colony.",
            )

        method = method.upper()
        if method == "RELAY":
            # Deploy Hyper-Relay Beacon: costs 10 Equipment, 2,500 SOL
            equip_cost = 10
            sol_cost = 2500
            if captain.credits < sol_cost:
                return ActionResult(
                    success=False,
                    action=ActionType.STABILIZE_DECOHERENCE,
                    message=f"Insufficient credits. Deploying a Subspace Hyper-Relay requires {sol_cost:,} credits (you have {captain.credits:,}).",
                )
            if captain.ship.cargo.equipment < equip_cost:
                return ActionResult(
                    success=False,
                    action=ActionType.STABILIZE_DECOHERENCE,
                    message=f"Insufficient equipment. Deploying a Hyper-Relay requires {equip_cost} Equipment in cargo.",
                )
            captain.credits -= sol_cost
            captain.ship.cargo.equipment -= equip_cost
            rec.decoherence_index = max(0.0, rec.decoherence_index - 0.40)
            rec.unrest = max(0.0, rec.unrest - 30.0)
            rec.tariff_leak = max(0.0, rec.tariff_leak - 0.15)
            self._update_status(rec)
            return ActionResult(
                success=True,
                action=ActionType.STABILIZE_DECOHERENCE,
                message=f"Deployed Subspace Hyper-Relay over {planet.name}. Decoherence dropped to {rec.decoherence_index:.2f} ({rec.status}).",
                data={"record": rec.to_dict()}
            )

        elif method == "ENVOY":
            # Dispatch Diplomatic Sovereign Envoy: costs 1,200 SOL
            sol_cost = 1200
            if captain.credits < sol_cost:
                return ActionResult(
                    success=False,
                    action=ActionType.STABILIZE_DECOHERENCE,
                    message=f"Dispatching an Imperial Envoy requires {sol_cost:,} credits.",
                )
            captain.credits -= sol_cost
            rec.unrest = max(0.0, rec.unrest - 45.0)
            rec.decoherence_index = max(0.0, rec.decoherence_index - 0.15)
            self._update_status(rec)
            return ActionResult(
                success=True,
                action=ActionType.STABILIZE_DECOHERENCE,
                message=f"Dispatched Imperial Envoy to {planet.name}. Civil unrest reduced to {rec.unrest:.1f}%.",
                data={"record": rec.to_dict()}
            )

        elif method == "PRECURSOR_CORE":
            # Socket Precursor Coherence Engine Shard from relics
            relics = getattr(captain, "relics", []) or []
            has_shard = any("Coherence Engine" in r for r in relics)
            if not has_shard:
                return ActionResult(
                    success=False,
                    action=ActionType.STABILIZE_DECOHERENCE,
                    message="You do not possess a Precursor Coherence Engine Shard. Excavate precursor ruins to find one.",
                )
            # Remove one shard
            for idx, r in enumerate(relics):
                if "Coherence Engine" in r:
                    relics.pop(idx)
                    break
            rec.decoherence_index = 0.0
            rec.unrest = 0.0
            rec.tariff_leak = 0.0
            planet.shields = getattr(planet, "shields", 0) + 200
            self._update_status(rec)
            return ActionResult(
                success=True,
                action=ActionType.STABILIZE_DECOHERENCE,
                message=f"Socketed Precursor Coherence Engine into {planet.name}'s orbital spire! Decoherence collapsed to 0.00 (Perfect Imperial Coherence). Shields +200.",
                data={"record": rec.to_dict()}
            )

        return ActionResult(
            success=False,
            action=ActionType.STABILIZE_DECOHERENCE,
            message=f"Unknown stabilization method '{method}'. Valid: RELAY, ENVOY, PRECURSOR_CORE.",
        )

    def _update_status(self, rec: ColonialDecoherenceRecord) -> None:
        if rec.decoherence_index >= 0.75 or rec.unrest >= 70.0:
            rec.status = "SECESSIONIST"
        elif rec.decoherence_index >= 0.50 or rec.unrest >= 40.0:
            rec.status = "DIVERGENT"
        elif rec.decoherence_index >= 0.25:
            rec.status = "STRAINED"
        else:
            rec.status = "STABLE"

    def tick(self, kernel: Any) -> None:
        """Cycle simulation tick: drifts decoherence on distant colonies."""
        for s in kernel.sectors.values():
            for p in getattr(s, "planets", []):
                if not p.owner_id:
                    continue
                rec = self.assess_world(kernel, p)
                if not rec:
                    continue
                # If distant from seat, slight natural drift
                if rec.distance_hops > 1:
                    drift = (rec.distance_hops - 1) * 0.015
                    rec.decoherence_index = min(1.0, rec.decoherence_index + drift)
                    rec.unrest = min(100.0, rec.unrest + drift * 25.0)
                    rec.tariff_leak = min(0.50, rec.decoherence_index * 0.35)
                    self._update_status(rec)
