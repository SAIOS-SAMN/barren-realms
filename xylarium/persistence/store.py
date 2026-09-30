"""
JSON Persistence engine for Xylarium game saves.
"""

import json
import os
from typing import Optional
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import Sector, Captain, RadioMessage
from xylarium.kernel.phylogeny import PHYLOGENY_MANAGER
from xylarium.kernel.federal import FederalReserve


class StatePersistence:
    """Serializes and deserializes the entire GameKernel to and from JSON."""

    @staticmethod
    def save_to_file(kernel: GameKernel, filepath: str) -> bool:
        """Serializes current universe and state to a JSON file."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
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
                "demography": getattr(kernel, "demography", None),
                "frontier": getattr(kernel, "frontier", None),
                "fibres": getattr(kernel, "fibres", None),
                "credit_stats": getattr(kernel, "credit_stats", None),
                "geology": getattr(kernel, "geology", None),
                "propulsion_stats": getattr(kernel, "propulsion_stats", None),
                "docket": getattr(kernel, "docket", None),
                "crime_stats": getattr(kernel, "crime_stats", None),
                "fertility_stats": getattr(kernel, "fertility_stats", None),
                "luxury_stats": getattr(kernel, "luxury_stats", None),
                "tourism_stats": getattr(kernel, "tourism_stats", None),
                "charters": getattr(kernel, "charters", None),
                "offices": getattr(kernel, "offices", None),
                "government_stats": getattr(kernel, "government_stats", None),
                "ship_designs": getattr(kernel, "ship_designs", None),
                "design_stats": getattr(kernel, "design_stats", None),
                "base_systems": getattr(kernel, "_base_systems", None),
                "realms": getattr(kernel, "realms", None),
                "realm_claims": getattr(kernel, "realm_claims", None),
                "realm_stats": getattr(kernel, "realm_stats", None),
                "lineage": getattr(kernel, "lineage", None),
                "single_lineage": bool(getattr(kernel, "single_lineage", False)),
                "npc_lineages": getattr(kernel, "npc_lineages", {}),
                "banking": kernel.banking.to_dict() if hasattr(kernel, "banking") else None,
                "settlement": kernel.settlement.to_dict() if hasattr(kernel, "settlement") else None,
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving game state: {e}")
            return False

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
            if data.get("demography"):
                kernel.demography = data["demography"]
            if data.get("frontier"):
                kernel.frontier = data["frontier"]
            if data.get("fibres"):
                kernel.fibres = data["fibres"]
            if data.get("credit_stats"):
                kernel.credit_stats = data["credit_stats"]
            if data.get("geology"):
                kernel.geology = data["geology"]
            if data.get("propulsion_stats"):
                kernel.propulsion_stats = data["propulsion_stats"]
            if data.get("docket"):
                kernel.docket = data["docket"]
            if data.get("crime_stats"):
                kernel.crime_stats = data["crime_stats"]
            for key in ("fertility_stats", "luxury_stats", "tourism_stats", "charters", "offices", "government_stats",
                        "ship_designs", "design_stats"):
                if data.get(key):
                    setattr(kernel, key, data[key])
            from xylarium.kernel import shipdesign
            shipdesign.restore(kernel)
            if data.get("base_systems"):
                kernel._base_systems = data["base_systems"]
            if data.get("realms") is not None:
                kernel.realms = data["realms"]
                kernel.realm_claims = {int(k): v for k, v in (data.get("realm_claims") or {}).items()}
                kernel.realm_stats = data.get("realm_stats") or kernel.realm_stats if hasattr(kernel, "realm_stats") else data.get("realm_stats")
            kernel.lineage = data.get("lineage")
            kernel.single_lineage = bool(data.get("single_lineage", False))
            kernel.npc_lineages = dict(data.get("npc_lineages", {}))
            from xylarium.kernel.banking import BankingSystem
            from xylarium.kernel.settlement import SettlementChain
            kernel.banking = BankingSystem.from_dict(data["banking"]) if data.get("banking") else BankingSystem()
            kernel.settlement = SettlementChain.from_dict(data["settlement"]) if data.get("settlement") else SettlementChain()
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
