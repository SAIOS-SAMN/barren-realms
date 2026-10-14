"""
JSON Persistence engine for Xylarium game saves.
"""

import json
import os
from typing import Any, Dict, Optional
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import Sector, Captain, RadioMessage
from xylarium.kernel.phylogeny import PHYLOGENY_MANAGER
from xylarium.kernel.federal import FederalReserve


RECORDS_SUFFIX = ".rec.zst"      # a save as its record stream (persistence/records.py), zstd at rest


class StatePersistence:
    """Serializes and deserializes the entire GameKernel to and from JSON."""

    @staticmethod
    def save_to_file(kernel: GameKernel, filepath: str) -> bool:
        """Saves the universe: as its record stream (.rec.zst, the truth) or as JSON (an export)."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            data = StatePersistence.snapshot(kernel)
            if filepath.endswith(RECORDS_SUFFIX):           # the record set itself: exact, the save the ledger hashes
                from xylarium.persistence import records
                StatePersistence.write_records(records.records_of(data), filepath)
                return True
            with open(filepath, "w", encoding="utf-8") as f:   # JSON: a human-readable export, never the truth
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving game state: {e}")
            return False

    @staticmethod
    def write_records(recs: Any, filepath: str) -> None:
        """A record stream to disk, zstd at rest, whole or not at all (a reader never sees half a save)."""
        from compression import zstd
        tmp = filepath + ".tmp"
        with open(tmp, "wb") as f:
            f.write(zstd.compress(b"".join(recs), level=3))
        os.replace(tmp, filepath)

    @staticmethod
    def snapshot(kernel: GameKernel) -> Dict[str, Any]:
        """The universe's state as one value: what is stored (derived values are not, Concordance 1.13)."""
        data = {
            "seed": kernel.seed,
            "cycle_count": kernel.cycle_count,
            "sectors": {s_id: sec.to_dict() for s_id, sec in kernel.sectors.items()},
            "captains": {c_id: cap.to_dict() for c_id, cap in kernel.captains.items()},
            "radio": [m.to_dict() for m in kernel.event_bus.get_recent_radio(50)],
            "logs": list(kernel.action_logs),
            "market": kernel.market_manager.to_dict() if hasattr(kernel, "market_manager") else None,
            "research": kernel.research_manager.to_dict() if hasattr(kernel, "research_manager") else None,
            "cartography": kernel.cartography_manager.to_dict() if hasattr(kernel, "cartography_manager") else None,
            "ideology": kernel.ideology_manager.to_dict() if hasattr(kernel, "ideology_manager") else None,
            "alchemy": kernel.alchemy_manager.to_dict() if hasattr(kernel, "alchemy_manager") else None,
            "astronomy": kernel.astronomy_manager.to_dict() if hasattr(kernel, "astronomy_manager") else None,
            "governance": kernel.governance_manager.to_dict() if hasattr(kernel, "governance_manager") else None,
            "federal": kernel.federal_reserve.to_dict() if hasattr(kernel, "federal_reserve") else None,
            "fx": kernel.fx_market.to_dict() if hasattr(kernel, "fx_market") else None,
            "ledger": kernel.ledger.to_dict() if hasattr(kernel, "ledger") else None,
            "matter": kernel.matter.to_dict() if hasattr(kernel, "matter") else None,
            "monetary_policy": kernel.monetary_policy.to_dict() if hasattr(kernel, "monetary_policy") else None,
            "factions": kernel.factions.to_dict() if hasattr(kernel, "factions") else None,
            "chronicle": kernel.chronicle.to_dict() if hasattr(kernel, "chronicle") else None,
            "native_stats": dict(getattr(kernel, "native_stats", {})),
            "state": getattr(kernel, "state", {}),               # every subsystem's record (state.py)
            "graph_version": getattr(kernel, "graph_version", 0),
            "lineage": getattr(kernel, "lineage", None),
            "single_lineage": bool(getattr(kernel, "single_lineage", False)),
            "npc_lineages": getattr(kernel, "npc_lineages", {}),
            "banking": kernel.banking.to_dict() if hasattr(kernel, "banking") else None,
            "settlement": kernel.settlement.to_dict() if hasattr(kernel, "settlement") else None,
            "crises": kernel.crises_manager.to_dict() if hasattr(kernel, "crises_manager") else None,
            "megastructures": kernel.megastructures_manager.to_dict() if hasattr(kernel, "megastructures_manager") else None,
            "biofleets": kernel.biofleets_manager.to_dict() if hasattr(kernel, "biofleets_manager") else None,
            "biosphere_genesis": kernel.biosphere_genesis_manager.to_dict() if hasattr(kernel, "biosphere_genesis_manager") else None,
            "decoherence": kernel.decoherence_manager.to_dict() if hasattr(kernel, "decoherence_manager") else None,
            "wormhole_engineering": kernel.wormhole_manager.to_dict() if hasattr(kernel, "wormhole_manager") else None,
            "hegemony": kernel.hegemony_manager.to_dict() if hasattr(kernel, "hegemony_manager") else None,
            "stellar_engineering": kernel.stellar_manager.to_dict() if hasattr(kernel, "stellar_manager") else None,
            "shadow_ops": kernel.shadow_manager.to_dict() if hasattr(kernel, "shadow_manager") else None,
            "omega_protocol": kernel.omega_manager.to_dict() if hasattr(kernel, "omega_manager") else None,
            "epochs": kernel.epoch_manager.to_dict() if hasattr(kernel, "epoch_manager") else None,
            "relic_foundry": kernel.relic_foundry_manager.to_dict() if hasattr(kernel, "relic_foundry_manager") else None,
            "clade_nursery": kernel.clade_nursery_manager.to_dict() if hasattr(kernel, "clade_nursery_manager") else None,
            "conclave": kernel.conclave_manager.to_dict() if hasattr(kernel, "conclave_manager") else None,
            "void_bridges": kernel.void_bridge_manager.to_dict() if hasattr(kernel, "void_bridge_manager") else None,
        }
        return data

    # Saves made before subsystem state was kept in kernel.state stored each record as a top-level key
    _LEGACY_KEYS = {
        "credit_stats": ("credit", None), "propulsion_stats": ("propulsion", None), "docket": ("law", None),
        "crime_stats": ("crime", None), "fertility_stats": ("fertility", None), "luxury_stats": ("luxury", None),
        "fibres": ("fibres", None), "geology": ("geology", "stats"), "demography": ("demography", "stats"),
        "frontier": ("demography", "frontier"), "tourism_stats": ("tourism", "stats"),
        "charters": ("tourism", "charters"), "government_stats": ("government", "stats"),
        "offices": ("government", "offices"), "ship_designs": ("workbench", "designs"),
        "design_stats": ("workbench", "stats"), "base_systems": ("populace", "base_systems"),
        "realms": ("realms", "realms"), "realm_claims": ("realms", "claims"), "realm_stats": ("realms", "stats"),
    }

    @staticmethod
    def _migrate_subsystem_keys(kernel: Any, data: Dict[str, Any]) -> None:
        from xylarium.kernel import state
        for key, (name, part) in StatePersistence._LEGACY_KEYS.items():
            if data.get(key) is None or (name in (data.get("state") or {})):
                continue
            if part is None:
                kernel.state[name] = data[key]
            else:
                state.of(kernel, name)[part] = data[key]

    @staticmethod
    def _migrate_legacy_universe(kernel: GameKernel) -> None:
        """
        Saves from before the physical/monetary universe: give ports balance sheets and regional
        currencies, denominate vaults, classify empty sectors as null space, and set supply targets.
        """
        from xylarium.config import PRICE_LEVEL, PORT_START_TREASURY, STARDOCK_START_TREASURY
        from xylarium.kernel.fx import currency_for_security
        from xylarium.kernel.universe import warp_distances
        dist = warp_distances(kernel.sectors, 1)
        for sec in kernel.sectors.values():
            cur = currency_for_security(sec.security)
            if sec.port is None and not sec.planets:
                sec.kind = "NULL"
            if sec.port is not None:
                sec.port.currency = cur
                sec.port.remoteness = dist.get(sec.id, 0)
                if sec.port.treasury <= 0:
                    base = STARDOCK_START_TREASURY if sec.id == 1 else PORT_START_TREASURY
                    sec.port.treasury = int(base * PRICE_LEVEL.get(cur, 1.0))
            for p in sec.planets:
                p.currency = cur
        kernel.monetary_policy.update(kernel)

    @staticmethod
    def load_from_file(filepath: str) -> Optional[GameKernel]:
        """Loads and reconstructs a GameKernel instance from a JSON file."""
        if not os.path.exists(filepath):
            return None
        try:
            if filepath.endswith(RECORDS_SUFFIX):
                from compression import zstd
                from xylarium.persistence import records
                with open(filepath, "rb") as f:
                    data = records.decode(zstd.decompress(f.read()))
            else:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

            kernel = GameKernel.__new__(GameKernel)
            kernel.seed = data.get("seed", 42)
            kernel.cycle_count = data.get("cycle_count", 0)
            kernel.sectors = {
                int(s_id): Sector.from_dict(sec_data)
                for s_id, sec_data in data["sectors"].items()
            }
            # Universes saved before the physics layer get exact stars and orbits derived on load
            from xylarium.kernel import physics
            for sec in kernel.sectors.values():
                physics.ensure_system(sec)
            kernel.captains = {
                c_id: Captain.from_dict(cap_data)
                for c_id, cap_data in data["captains"].items()
            }
            from xylarium.kernel.events import EventBus
            from xylarium.kernel.market import MarketManager
            from xylarium.kernel.research import ResearchManager
            from xylarium.kernel.cartography import CartographyManager
            from xylarium.kernel.ideology import IdeologyManager
            from xylarium.kernel.alchemy import AlchemyManager
            from xylarium.kernel.astronomy import AstronomyManager
            from xylarium.kernel.governance import SenateManager
            from xylarium.kernel.surface import SurfaceManager
            from collections import deque
            kernel.event_bus = EventBus()
            if data.get("market"):
                kernel.market_manager = MarketManager.from_dict(data["market"])
            else:
                kernel.market_manager = MarketManager()
            if data.get("research"):
                kernel.research_manager = ResearchManager.from_dict(data["research"])
            else:
                kernel.research_manager = ResearchManager()
                kernel.research_manager.seed_initial_anomalies(kernel)
            if data.get("cartography"):
                kernel.cartography_manager = CartographyManager.from_dict(data["cartography"])
            else:
                kernel.cartography_manager = CartographyManager()

            if data.get("ideology"):
                kernel.ideology_manager = IdeologyManager.from_dict(data["ideology"])
            else:
                kernel.ideology_manager = IdeologyManager()

            if data.get("alchemy"):
                kernel.alchemy_manager = AlchemyManager.from_dict(data["alchemy"])
            else:
                kernel.alchemy_manager = AlchemyManager()

            if data.get("astronomy"):
                kernel.astronomy_manager = AstronomyManager.from_dict(data["astronomy"])
            else:
                kernel.astronomy_manager = AstronomyManager()

            if data.get("governance"):
                kernel.governance_manager = SenateManager.from_dict(data["governance"])
                kernel.governance_manager.bind(kernel)
            else:
                kernel.governance_manager = SenateManager()
                kernel.governance_manager.bind(kernel)

            kernel.surface_manager = SurfaceManager()
            # Stateless DAG singleton; per-captain phylogeny state is persisted on each Captain
            kernel.phylogeny_manager = PHYLOGENY_MANAGER
            kernel.federal_reserve = (
                FederalReserve.from_dict(data["federal"]) if data.get("federal") else FederalReserve()
            )
            kernel.market_manager._kernel_ref = kernel
            from xylarium.kernel.fx import FXMarket
            from xylarium.kernel.ledger import MoneyLedger
            kernel.fx_market = FXMarket.from_dict(data["fx"]) if data.get("fx") else FXMarket()
            kernel.ledger = MoneyLedger.from_dict(data["ledger"]) if data.get("ledger") else MoneyLedger()
            from xylarium.kernel.matter import MatterLedger
            kernel.matter = MatterLedger.from_dict(data["matter"]) if data.get("matter") else MatterLedger()
            from xylarium.kernel.ledger import MonetaryPolicy
            kernel.monetary_policy = (MonetaryPolicy.from_dict(data["monetary_policy"]) if data.get("monetary_policy")
                                      else MonetaryPolicy())
            from xylarium.kernel.factions import FactionManager
            from xylarium.kernel.chronicle import ChronicleEngine
            kernel.factions = FactionManager.from_dict(data["factions"]) if data.get("factions") else FactionManager()
            kernel.chronicle = ChronicleEngine.from_dict(data["chronicle"]) if data.get("chronicle") else ChronicleEngine()
            kernel.native_stats = dict(data.get("native_stats", {}))
            kernel.state = dict(data.get("state") or {})
            kernel.caches = {}
            kernel.graph_version = int(data.get("graph_version", 0))
            StatePersistence._migrate_subsystem_keys(kernel, data)
            from xylarium.kernel import subsystem
            subsystem.restore_all(kernel)
            kernel.lineage = data.get("lineage")
            kernel.single_lineage = bool(data.get("single_lineage", False))
            kernel.npc_lineages = dict(data.get("npc_lineages", {}))
            from xylarium.kernel.banking import BankingSystem
            from xylarium.kernel.settlement import SettlementChain
            from xylarium.kernel.workbenches import WorkbenchManager
            from xylarium.kernel.crises import CrisesManager
            from xylarium.kernel.megastructures import MegastructuresManager
            from xylarium.kernel.biofleets import BioFleetsManager
            from xylarium.kernel.biosphere_genesis import BiosphereGenesisManager
            from xylarium.kernel.colonial_decoherence import ColonialDecoherenceManager

            kernel.banking = BankingSystem.from_dict(data["banking"]) if data.get("banking") else BankingSystem()
            kernel.settlement = SettlementChain.from_dict(data["settlement"]) if data.get("settlement") else SettlementChain()
            kernel.workbench_manager = WorkbenchManager()

            if data.get("crises"):
                kernel.crises_manager = CrisesManager.from_dict(data["crises"])
            else:
                kernel.crises_manager = CrisesManager()
                kernel.crises_manager.seed_initial_crises(kernel)

            if data.get("megastructures"):
                kernel.megastructures_manager = MegastructuresManager.from_dict(data["megastructures"])
            else:
                kernel.megastructures_manager = MegastructuresManager()
                kernel.megastructures_manager.seed_initial_derelicts(kernel)

            if data.get("biofleets"):
                kernel.biofleets_manager = BioFleetsManager.from_dict(data["biofleets"])
            else:
                kernel.biofleets_manager = BioFleetsManager()

            if data.get("biosphere_genesis"):
                kernel.biosphere_genesis_manager = BiosphereGenesisManager.from_dict(data["biosphere_genesis"])
            else:
                kernel.biosphere_genesis_manager = BiosphereGenesisManager()

            if data.get("decoherence"):
                kernel.decoherence_manager = ColonialDecoherenceManager.from_dict(data["decoherence"])
            else:
                kernel.decoherence_manager = ColonialDecoherenceManager()

            from xylarium.kernel.wormhole_engineering import WormholeEngineeringManager
            from xylarium.kernel.hegemony_ai import HegemonyAIManager
            from xylarium.kernel.stellar_engineering import StellarEngineeringManager
            from xylarium.kernel.shadow_ops import ShadowOpsManager
            from xylarium.kernel.omega_protocol import OmegaProtocolManager
            from xylarium.kernel.civilizational_epochs import CivilizationalEpochManager
            from xylarium.kernel.relic_foundry import RelicFoundryManager
            from xylarium.kernel.clade_nursery import CladeNurseryManager
            from xylarium.kernel.conclave import PanGalacticConclaveManager
            from xylarium.kernel.void_bridges import VoidBridgeManager

            if data.get("wormhole_engineering"):
                kernel.wormhole_manager = WormholeEngineeringManager.from_dict(data["wormhole_engineering"])
            else:
                kernel.wormhole_manager = WormholeEngineeringManager()


            if data.get("hegemony"):
                kernel.hegemony_manager = HegemonyAIManager.from_dict(data["hegemony"])
            else:
                kernel.hegemony_manager = HegemonyAIManager()
                kernel.hegemony_manager.seed_initial_factions(kernel)

            if data.get("stellar_engineering"):
                kernel.stellar_manager = StellarEngineeringManager.from_dict(data["stellar_engineering"])
            else:
                kernel.stellar_manager = StellarEngineeringManager()

            if data.get("shadow_ops"):
                kernel.shadow_manager = ShadowOpsManager.from_dict(data["shadow_ops"])
            else:
                kernel.shadow_manager = ShadowOpsManager()

            if data.get("omega_protocol"):
                kernel.omega_manager = OmegaProtocolManager.from_dict(data["omega_protocol"])
            else:
                kernel.omega_manager = OmegaProtocolManager()

            if data.get("epochs"):
                kernel.epoch_manager = CivilizationalEpochManager.from_dict(data["epochs"])
            else:
                kernel.epoch_manager = CivilizationalEpochManager()

            if data.get("relic_foundry"):
                kernel.relic_foundry_manager = RelicFoundryManager.from_dict(data["relic_foundry"])
            else:
                kernel.relic_foundry_manager = RelicFoundryManager()

            if data.get("clade_nursery"):
                kernel.clade_nursery_manager = CladeNurseryManager.from_dict(data["clade_nursery"])
            else:
                kernel.clade_nursery_manager = CladeNurseryManager()

            if data.get("conclave"):
                kernel.conclave_manager = PanGalacticConclaveManager.from_dict(data["conclave"])
            else:
                kernel.conclave_manager = PanGalacticConclaveManager()

            if data.get("void_bridges"):
                kernel.void_bridge_manager = VoidBridgeManager.from_dict(data["void_bridges"])
            else:
                kernel.void_bridge_manager = VoidBridgeManager()

            kernel.legacy_file = None
            if not data.get("fx"):
                StatePersistence._migrate_legacy_universe(kernel)
            kernel.activate()

            for r_data in data.get("radio", []):
                kernel.event_bus.broadcast_radio(
                    sender=r_data["sender"],
                    text=r_data["text"],
                    channel=r_data.get("channel", "COMM-1"),
                    sector_id=r_data.get("sector_id")
                )
            kernel.action_logs = deque(data.get("logs", []), maxlen=20)
            return kernel
        except Exception as e:
            print(f"Error loading game state: {e}")
            return None
