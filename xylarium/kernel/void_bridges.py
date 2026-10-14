"""
xylarium/kernel/void_bridges.py

Project Landing 4: Extragalactic Void Bridges & Multi-Cluster Cosmos.

Spans the intergalactic void beyond the initial 100 sectors of the Local Milky Cluster:
  - Extragalactic Destination Clusters:
    1. CLUSTER_MAGELLANIC (The Magellanic Stream: Tachyon rifts, +50% mining yield, dwarf galaxy).
    2. CLUSTER_GLOBULAR (The Omega Starburst: Hyper-dense stellar packing, +100% star-lifting).
    3. CLUSTER_SEYFERT (The Seyfert Active Core: Accretion disk, extreme radiation, Tier-V Precursor ruins).
  - Megastructural Void Bridge Pylons:
    Anchored in boundary sectors, requiring Void Bridge Capacitors / Inverted Singularities.
  - Multi-Cluster Metric Tunneling:
    Instantaneous extragalactic transit bypassing standard hyperspace limits.
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
import random
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Planet, Sector, SecurityLevel


EXTRAGALACTIC_CLUSTERS: Dict[str, Dict[str, Any]] = {
    "CLUSTER_MAGELLANIC": {
        "name": "The Magellanic Stream",
        "description": "A diffuse dwarf satellite galaxy rich in volatile tachyons and pristine primordial ices.",
        "distance_kpc": 60,
        "sector_range": (201, 230),
        "mining_modifier": 1.5,
        "hazard_type": "TACHYON_FLUX",
        "precursor_density": 0.3,
    },
    "CLUSTER_GLOBULAR": {
        "name": "Omega Starburst Core",
        "description": "An ancient, hyper-dense globular cluster where millions of ancient suns burn within light-months.",
        "distance_kpc": 120,
        "sector_range": (301, 330),
        "mining_modifier": 1.1,
        "hazard_type": "GRAVITATIONAL_TIDES",
        "precursor_density": 0.5,
    },
    "CLUSTER_SEYFERT": {
        "name": "The Seyfert Active Core",
        "description": "The violently energetic core of a distant Seyfert galaxy powered by a supermassive black hole.",
        "distance_kpc": 450,
        "sector_range": (401, 430),
        "mining_modifier": 2.0,
        "hazard_type": "HAWKING_RADIATION",
        "precursor_density": 0.9,
    },
}


@dataclass
class VoidBridgeConduit:
    id: str
    name: str
    origin_sector_id: int
    destination_cluster: str
    target_sector_id: int
    builder_id: str
    cycle_built: int
    coherence_integrity: float = 100.0  # Percentage
    transits_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VoidBridgeConduit:
        return cls(**data)


class VoidBridgeManager:
    """Manages construction of extragalactic void bridges and multi-cluster transit."""

    def __init__(self) -> None:
        self.bridges: Dict[str, VoidBridgeConduit] = {}
        self.initialized_clusters: Dict[str, bool] = {}
        self.counter: int = 1

    def ensure_cluster_instantiated(self, kernel: Any, cluster_id: str) -> None:
        """Instantiates cluster sectors, planets, and anomalous features when bridged."""
        if self.initialized_clusters.get(cluster_id):
            return

        cluster_info = EXTRAGALACTIC_CLUSTERS.get(cluster_id)
        if not cluster_info:
            return

        start_sec, end_sec = cluster_info["sector_range"]
        rng = random.Random(kernel.seed + hash(cluster_id))

        for sec_id in range(start_sec, end_sec + 1):
            if sec_id in kernel.sectors:
                continue

            sec_name = f"{cluster_info['name']} - Sector {sec_id}"
            sec = Sector(
                id=sec_id,
                name=sec_name,
                security=SecurityLevel.ANARCHY,
                cluster_name=cluster_info["name"],
                warps=[],
            )

            # Generate internal cluster warps
            possible_targets = [s for s in range(start_sec, end_sec + 1) if s != sec_id]
            warp_count = min(3, len(possible_targets))
            sec.warps = rng.sample(possible_targets, warp_count)

            # High-tier foreign planets
            if rng.random() > 0.4:
                p_type = "METRIC_CRUCIBLE" if cluster_id == "CLUSTER_SEYFERT" else "TERRESTRIAL"
                planet = Planet(
                    id=f"P-{sec_id}-1",
                    name=f"{cluster_info['name'][:8]}-{sec_id} Alpha",
                    sector_id=sec_id,
                    planet_type=p_type,
                    shields=500 if cluster_id == "CLUSTER_SEYFERT" else 200,
                    citadel_level=0,
                )
                if rng.random() < cluster_info["precursor_density"]:
                    planet.ruins = {
                        "culture": "Extra-Universal Forerunners",
                        "era": "Pre-Inflationary",
                        "cause": "Entropy Inversion",
                        "strata": [
                            {"name": "Super-Dense Relic Core", "depth": 1, "richness": 1.5, "finds_left": 5},
                            {"name": "Tachyon Reservoir", "depth": 2, "richness": 2.0, "finds_left": 6},
                            {"name": "Cosmic Membrane", "depth": 3, "richness": 3.0, "finds_left": 7},
                        ],
                        "dug_depth": 0,
                        "hoard": 150000,
                    }
                sec.planets.append(planet)

            kernel.sectors[sec_id] = sec

        self.initialized_clusters[cluster_id] = True

    def commission_bridge(
        self,
        kernel: Any,
        captain: Captain,
        destination_cluster: str,
    ) -> ActionResult:
        """Constructs an intergalactic Void Bridge Pylon from the current sector."""
        cluster_key = destination_cluster.upper().strip()
        if cluster_key not in EXTRAGALACTIC_CLUSTERS:
            return ActionResult(
                success=False,
                action=ActionType.VOID_BRIDGE_COMMISSION,
                message=f"Unknown extragalactic destination '{destination_cluster}'. Valid: {list(EXTRAGALACTIC_CLUSTERS.keys())}.",
            )

        # Check existing bridge in this sector
        for b in self.bridges.values():
            if b.origin_sector_id == captain.sector_id and b.destination_cluster == cluster_key:
                return ActionResult(
                    success=False,
                    action=ActionType.VOID_BRIDGE_COMMISSION,
                    message=f"A Void Bridge to {cluster_key} is already anchored in Sector {captain.sector_id}.",
                )

        cost_credits = 500000
        # Check capacitor or credits
        has_capacitor = False
        if hasattr(kernel, "relic_foundry_manager"):
            for art in kernel.relic_foundry_manager.artifacts.values():
                if getattr(art, "owner_id", None) == captain.id and getattr(art, "blueprint_key", None) == "VOID_BRIDGE_CAPACITOR":
                    has_capacitor = True
                    break

        if not has_capacitor:
            if captain.credits < cost_credits:
                return ActionResult(
                    success=False,
                    action=ActionType.VOID_BRIDGE_COMMISSION,
                    message=f"Commissioning requires a forged 'VOID_BRIDGE_CAPACITOR' artifact or {cost_credits:,} credits (You have: {captain.credits:,}).",
                )
            captain.credits -= cost_credits

        # Instantiate cluster sectors
        self.ensure_cluster_instantiated(kernel, cluster_key)
        start_sec, _ = EXTRAGALACTIC_CLUSTERS[cluster_key]["sector_range"]

        bridge_id = f"BRIDGE-{self.counter:03d}"
        self.counter += 1

        bridge_name = f"Trans-Void Pylon to {EXTRAGALACTIC_CLUSTERS[cluster_key]['name']}"
        conduit = VoidBridgeConduit(
            id=bridge_id,
            name=bridge_name,
            origin_sector_id=captain.sector_id,
            destination_cluster=cluster_key,
            target_sector_id=start_sec,
            builder_id=captain.id,
            cycle_built=kernel.cycle_count,
        )
        self.bridges[bridge_id] = conduit

        # Connect sector warps bidirectionally to bridge
        origin_sec = kernel.sectors.get(captain.sector_id)
        if origin_sec and start_sec not in origin_sec.warps:
            origin_sec.warps.append(start_sec)
        target_sec = kernel.sectors.get(start_sec)
        if target_sec and captain.sector_id not in target_sec.warps:
            target_sec.warps.append(captain.sector_id)

        kernel.action_logs.append(f"[VOID_BRIDGE] Commissioned {bridge_name} in Sector {captain.sector_id}.")
        if hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender="METRIC_TELEMETRY",
                text=f"MASSIVE GRAVITATIONAL ANOMALY: {captain.name} has anchored an Extragalactic Void Bridge to {cluster_key}!",
                channel="COSMIC_BROADCAST",
            )

        return ActionResult(
            success=True,
            action=ActionType.VOID_BRIDGE_COMMISSION,
            turns_spent=2,
            message=f"VOID BRIDGE ANCHORED: '{bridge_name}' [{bridge_id}] opens wormhole link directly to Sector {start_sec}.",
            data={"conduit": conduit.to_dict()},
        )

    def transit_bridge(
        self,
        kernel: Any,
        captain: Captain,
        bridge_id: str,
    ) -> ActionResult:
        """Traverses the Void Bridge across intergalactic space."""
        conduit = self.bridges.get(bridge_id)
        if not conduit:
            return ActionResult(
                success=False,
                action=ActionType.VOID_BRIDGE_TRANSIT,
                message=f"Void Bridge '{bridge_id}' not found.",
            )

        if captain.sector_id not in [conduit.origin_sector_id, conduit.target_sector_id]:
            return ActionResult(
                success=False,
                action=ActionType.VOID_BRIDGE_TRANSIT,
                message=f"You must be docked at Sector {conduit.origin_sector_id} or Sector {conduit.target_sector_id} to enter this conduit.",
            )

        dest_sector_id = (
            conduit.target_sector_id
            if captain.sector_id == conduit.origin_sector_id
            else conduit.origin_sector_id
        )

        captain.sector_id = dest_sector_id
        conduit.transits_count += 1
        conduit.coherence_integrity = max(10.0, conduit.coherence_integrity - 0.5)

        cluster_info = EXTRAGALACTIC_CLUSTERS.get(conduit.destination_cluster, {})
        c_name = cluster_info.get("name", conduit.destination_cluster)

        # Environmental hazards on entering foreign cluster
        hazard_msg = ""
        if dest_sector_id == conduit.target_sector_id:
            h_type = cluster_info.get("hazard_type")
            if h_type == "HAWKING_RADIATION":
                captain.ship.shields = max(0, captain.ship.shields - 30)
                hazard_msg = " [WARNING: Extreme Hawking radiation drained 30 shields!]"
            elif h_type == "GRAVITATIONAL_TIDES":
                hazard_msg = " [NOTICE: Hyper-dense stellar packing bends your warp drive trajectories.]"

        kernel.action_logs.append(f"[VOID_BRIDGE] Traversed {conduit.id} into Sector {dest_sector_id}.")

        return ActionResult(
            success=True,
            action=ActionType.VOID_BRIDGE_TRANSIT,
            turns_spent=1,
            message=f"TRANS-VOID TUNNEL COMPLETE: Crossed {cluster_info.get('distance_kpc', 50):,} kpc abyss into {c_name} (Sector {dest_sector_id}).{hazard_msg}",
            data={"arrival_sector": dest_sector_id, "transits": conduit.transits_count},
        )

    def survey_cluster(
        self,
        kernel: Any,
        captain: Captain,
        cluster_id: str,
    ) -> ActionResult:
        """Deep cosmic telemetry scan of an extragalactic star cluster."""
        cid = cluster_id.upper().strip()
        info = EXTRAGALACTIC_CLUSTERS.get(cid)
        if not info:
            return ActionResult(
                success=False,
                action=ActionType.VOID_BRIDGE_SURVEY_CLUSTER,
                message=f"Unknown star cluster '{cluster_id}'.",
            )

        self.ensure_cluster_instantiated(kernel, cid)
        start_sec, end_sec = info["sector_range"]
        sectors_in_cluster = [s for s in range(start_sec, end_sec + 1) if s in kernel.sectors]
        planets_count = sum(len(kernel.sectors[s].planets) for s in sectors_in_cluster)

        return ActionResult(
            success=True,
            action=ActionType.VOID_BRIDGE_SURVEY_CLUSTER,
            turns_spent=1,
            message=(
                f"CLUSTER SURVEY [{info['name']}]: Distance {info['distance_kpc']:,} kpc. "
                f"Sectors: {len(sectors_in_cluster)}, Charted Planets: {planets_count}. "
                f"Hazard: {info['hazard_type']} │ Mining Yield: x{info['mining_modifier']:.1f}."
            ),
            data={
                "cluster": cid,
                "distance_kpc": info["distance_kpc"],
                "sectors": len(sectors_in_cluster),
                "planets": planets_count,
            },
        )

    def tick(self, kernel: Any) -> None:
        """Per-cycle maintenance of void conduits."""
        for b in self.bridges.values():
            if b.coherence_integrity < 100.0:
                b.coherence_integrity = min(100.0, b.coherence_integrity + 0.1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bridges": {k: v.to_dict() for k, v in self.bridges.items()},
            "initialized_clusters": self.initialized_clusters,
            "counter": self.counter,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VoidBridgeManager:
        mgr = cls()
        mgr.initialized_clusters = data.get("initialized_clusters", {})
        mgr.counter = int(data.get("counter", 1))
        for k, v in data.get("bridges", {}).items():
            mgr.bridges[k] = VoidBridgeConduit.from_dict(v)
        return mgr
