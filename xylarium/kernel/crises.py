"""
xylarium.kernel.crises: GalNet Subspace Newsfeed & Systemic Galactic Crises.

Simulates macroeconomic, astrophysical, biological, and political crises that ripple
across the 100-sector cluster, broadcasting GalNet flashes and disrupting trade lanes,
currency pegs, and spaceport quarantines.
"""

from __future__ import annotations
import math
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel.models import ActionResult, ActionType, Captain, Sector


CRISIS_TYPES = [
    "XENOPATHIC_CONTAGION",       # Biosphere virus outbreak: spaceport quarantine, 4x MEDICINE/ORGANICS demand
    "HYPER_LANE_TORSION_PINCH",   # Metric torsion storm: transit cost +200%, forces Einstein-Cartan detour
    "SOVEREIGN_CURRENCY_RUN",     # Speculative currency run: extreme FX volatility, demands corridor peg defense
    "SOLAR_SUPERFLARE",           # Magnetar/CME flare: drains ship shields in sector, halts unshielded asteroid mining
]


@dataclass
class GalNetArticle:
    id: str
    cycle: int
    headline: str
    category: str               # "FINANCE", "EPIDEMIOLOGY", "ASTROPHYSICS", "POLITICS", "WARFARE"
    body: str
    sector_id: Optional[int] = None
    urgency: str = "ROUTINE"    # "ROUTINE", "FLASH", "CRITICAL"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cycle": self.cycle,
            "headline": self.headline,
            "category": self.category,
            "body": self.body,
            "sector_id": self.sector_id,
            "urgency": self.urgency,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GalNetArticle":
        return cls(**data)


@dataclass
class GalacticCrisis:
    id: str
    crisis_type: str
    name: str
    sector_id: int
    start_cycle: int
    duration_cycles: int
    severity: float = 0.5           # 0.1 to 1.0
    status: str = "ACTIVE"          # "ACTIVE", "CONTAINED", "RESOLVED"
    target_lane: Optional[Tuple[int, int]] = None
    target_currency: Optional[str] = None
    relief_delivered: int = 0
    relief_required: int = 20
    description: str = ""
    economic_effects: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "crisis_type": self.crisis_type,
            "name": self.name,
            "sector_id": self.sector_id,
            "start_cycle": self.start_cycle,
            "duration_cycles": self.duration_cycles,
            "severity": self.severity,
            "status": self.status,
            "target_lane": list(self.target_lane) if self.target_lane else None,
            "target_currency": self.target_currency,
            "relief_delivered": self.relief_delivered,
            "relief_required": self.relief_required,
            "description": self.description,
            "economic_effects": dict(self.economic_effects),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GalacticCrisis":
        d = dict(data)
        if d.get("target_lane") and isinstance(d["target_lane"], list):
            d["target_lane"] = tuple(d["target_lane"])
        return cls(**d)


class CrisesManager:
    """
    Simulates cluster-wide systemic crises and publishes the real-time GalNet newsfeed.
    """

    def __init__(self, max_articles: int = 60):
        self.active_crises: Dict[str, GalacticCrisis] = {}
        self.news_history: deque[GalNetArticle] = deque(maxlen=max_articles)
        self.next_crisis_id: int = 101
        self.next_article_id: int = 1001

    def seed_initial_crises(self, kernel: Any) -> None:
        """Seed initial GalNet headlines and one active crisis for cluster immersion."""
        self.publish_article(
            "CLUSTER COMMERCE REPORT: ISSE Clearing Union affirms trade stability",
            "FINANCE",
            "Interstellar Stock & Settlement Exchange reports strong liquidity across central core nodes.",
            cycle=kernel.cycle_count,
            sector_id=1,
            urgency="ROUTINE",
            kernel=kernel,
        )
        self.publish_article(
            "XENOBIOLOGY FLASH: Strange bio-spores drifting from frontier nebulae",
            "EPIDEMIOLOGY",
            "Uncatalogued bio-polymers reported by deep space survey probes near outer rim systems.",
            cycle=kernel.cycle_count,
            urgency="ROUTINE",
            kernel=kernel,
        )
        sec_id = 7 if 7 in kernel.sectors else (list(kernel.sectors.keys())[min(6, len(kernel.sectors)-1)])
        self.spawn_crisis(
            "XENOPATHIC_CONTAGION",
            sector_id=sec_id,
            cycle=kernel.cycle_count,
            severity=0.5,
            duration=40,
            kernel=kernel,
        )

    def publish_article(
        self,
        headline: str,
        category: str,
        body: str,
        cycle: int,
        sector_id: Optional[int] = None,
        urgency: str = "ROUTINE",
        kernel: Any = None,
    ) -> GalNetArticle:
        art_id = f"GN-{self.next_article_id}"
        self.next_article_id += 1
        art = GalNetArticle(
            id=art_id,
            cycle=cycle,
            headline=headline,
            category=category,
            body=body,
            sector_id=sector_id,
            urgency=urgency,
        )
        self.news_history.append(art)
        if kernel and hasattr(kernel, "event_bus"):
            kernel.event_bus.broadcast_radio(
                sender=f"GALNET/{category}",
                text=f"[{urgency}] {headline}",
                channel="GALNET-WIRE",
                sector_id=sector_id,
            )
        return art

    def spawn_crisis(
        self,
        crisis_type: str,
        sector_id: int,
        cycle: int,
        severity: float = 0.5,
        duration: int = 25,
        kernel: Any = None,
    ) -> GalacticCrisis:
        c_id = f"CRISIS-{self.next_crisis_id}"
        self.next_crisis_id += 1

        sec_name = f"Sector {sector_id:03d}"
        if kernel and sector_id in kernel.sectors:
            sec_name = kernel.sectors[sector_id].name

        target_lane = None
        target_currency = None
        economic_effects: Dict[str, Any] = {}

        if crisis_type == "XENOPATHIC_CONTAGION":
            name = f"Outbreak: Phytovirus Strain Zeta on {sec_name}"
            desc = "Mutagenic spore contamination has breached biosphere domes. Spaceport under emergency biological quarantine."
            economic_effects = {"demand_mult": {"ORGANICS": 4.5, "MEDICINE": 5.0}, "quarantine": True}
            relief_req = int(15 * severity + 10)
            self.publish_article(
                f"BIOLOGICAL CRISIS: Quarantine declared in {sec_name}!",
                "EPIDEMIOLOGY",
                f"High-virulence phytovirus outbreak detected in {sec_name}. Port authorities appeal for urgent medical and organic relief.",
                cycle=cycle,
                sector_id=sector_id,
                urgency="CRITICAL",
                kernel=kernel,
            )

        elif crisis_type == "HYPER_LANE_TORSION_PINCH":
            warps = kernel.sectors[sector_id].warps if kernel and sector_id in kernel.sectors else [sector_id + 1]
            dest = warps[0] if warps else sector_id + 1
            target_lane = (sector_id, dest)
            name = f"Torsion Rupture along Lane {sector_id} <-> {dest}"
            desc = "Gravitational spin-torsion waves have created micro-caustics along the jump corridor. Jump transit costs tripled."
            economic_effects = {"lane_drag_multiplier": 3.0, "affected_lane": target_lane}
            relief_req = int(20 * severity + 10)
            self.publish_article(
                f"ASTROPHYSICAL ANOMALY: Hyper-lane pinch in Sector {sector_id}!",
                "ASTROPHYSICS",
                f"Spacetime metric shear has destabilized the wormhole corridor to Sector {dest}. Einstein-Cartan throat routes advised.",
                cycle=cycle,
                sector_id=sector_id,
                urgency="FLASH",
                kernel=kernel,
            )

        elif crisis_type == "SOVEREIGN_CURRENCY_RUN":
            target_currency = "FRN" if sector_id > 10 else "THR"
            name = f"Run on {target_currency} Sovereign Exchange"
            desc = f"Massive capital flight and speculative attacks have depleted {target_currency} reserves at port desks."
            economic_effects = {"fx_volatility": 0.45, "fee_surcharge": 0.05}
            relief_req = int(30 * severity + 20)
            self.publish_article(
                f"MARKET CRISIS: Run on {target_currency} currency desk!",
                "FINANCE",
                f"Speculative outflow detected in {sec_name}. ISSE market makers urge sovereign central banks to defend corridor pegs.",
                cycle=cycle,
                sector_id=sector_id,
                urgency="FLASH",
                kernel=kernel,
            )

        else:  # SOLAR_SUPERFLARE
            name = f"Coronal Mass Superflare across {sec_name}"
            desc = "Class-X magnetar eruptive flare emitting intense gamma-radiation. Unshielded ships suffer capacitor draining."
            economic_effects = {"shield_drain_rate": 15, "mining_halt": True}
            relief_req = int(25 * severity + 15)
            self.publish_article(
                f"SOLAR STORM: Mega-flare sweeps {sec_name}!",
                "ASTROPHYSICS",
                f"Intense electromagnetic radiation storm detected. Asteroid harvesters and unshielded haulers urged to seek stellar shadow.",
                cycle=cycle,
                sector_id=sector_id,
                urgency="CRITICAL",
                kernel=kernel,
            )

        crisis = GalacticCrisis(
            id=c_id,
            crisis_type=crisis_type,
            name=name,
            sector_id=sector_id,
            start_cycle=cycle,
            duration_cycles=duration,
            severity=severity,
            target_lane=target_lane,
            target_currency=target_currency,
            relief_delivered=0,
            relief_required=relief_req,
            description=desc,
            economic_effects=economic_effects,
        )
        self.active_crises[c_id] = crisis
        return crisis

    def deliver_relief(
        self,
        kernel: Any,
        captain: Captain,
        crisis_id: str,
        commodity: str,
        amount: int,
    ) -> ActionResult:
        """
        Dispatches emergency relief cargo to alleviate an active systemic crisis.
        """
        if crisis_id not in self.active_crises:
            return ActionResult(
                success=False,
                action=ActionType.CRISIS_RELIEF_DISPATCH,
                message=f"Crisis ID '{crisis_id}' is not active or has already been resolved.",
            )

        crisis = self.active_crises[crisis_id]
        if captain.sector_id != crisis.sector_id:
            return ActionResult(
                success=False,
                action=ActionType.CRISIS_RELIEF_DISPATCH,
                message=f"Must navigate to crisis ground zero (Sector {crisis.sector_id:03d}) to offload relief supplies.",
            )

        comm_upper = commodity.upper()
        held = captain.ship.cargo.held(comm_upper)
        if held < amount and comm_upper in captain.ship.cargo.elements:
            held = captain.ship.cargo.elements[comm_upper]
        if amount <= 0 or held < amount:
            return ActionResult(
                success=False,
                action=ActionType.CRISIS_RELIEF_DISPATCH,
                message=f"Insufficient {comm_upper} in holds (held: {held}, requested: {amount}).",
            )

        valid_relief = ["ORGANICS", "MEDICINE", "H2O", "EQUIPMENT", "FE", "BIO_CHITIN", "CRYOPROTECTANT"]
        if comm_upper not in valid_relief:
            return ActionResult(
                success=False,
                action=ActionType.CRISIS_RELIEF_DISPATCH,
                message=f"Commodity '{comm_upper}' is not suited for crisis relief. Accepted: {', '.join(valid_relief)}.",
            )

        # Offload cargo
        if comm_upper == "ORGANICS":
            captain.ship.cargo.organics -= amount
        elif comm_upper == "EQUIPMENT":
            captain.ship.cargo.equipment -= amount
        elif comm_upper in captain.ship.cargo.elements:
            captain.ship.cargo.elements[comm_upper] -= amount
            if captain.ship.cargo.elements[comm_upper] <= 0:
                del captain.ship.cargo.elements[comm_upper]
        else:
            captain.ship.cargo.elements[comm_upper] = captain.ship.cargo.elements.get(comm_upper, amount) - amount

        crisis.relief_delivered += amount
        payout = amount * 85  # Humanitarian relief bounty
        captain.credits += payout

        # Reputation & Alignment award
        if hasattr(captain, "adjust_reputation"):
            captain.adjust_reputation("Federation", 3.0)
        if hasattr(captain, "cosmic_alignment"):
            captain.cosmic_alignment = min(1.0, captain.cosmic_alignment + 0.05)

        msg = f"RELIEF DELIVERED: Offloaded {amount}x [{comm_upper}] in Sector {crisis.sector_id:03d}! Bounty: +{payout:,} Cr. Status: {crisis.relief_delivered}/{crisis.relief_required} units."

        if crisis.relief_delivered >= crisis.relief_required:
            crisis.status = "RESOLVED"
            self.publish_article(
                f"CRISIS RESOLVED: {crisis.name} contained!",
                "POLITICS",
                f"Thanks to interstellar relief efforts by {captain.name}, the crisis in Sector {crisis.sector_id:03d} has been neutralized.",
                cycle=kernel.cycle_count,
                sector_id=crisis.sector_id,
                urgency="ROUTINE",
                kernel=kernel,
            )
            del self.active_crises[crisis_id]
            msg += f" {crisis.name} has been formally RESOLVED."

        return ActionResult(
            success=True,
            action=ActionType.CRISIS_RELIEF_DISPATCH,
            message=msg,
            data={"crisis_id": crisis_id, "relief_delivered": amount, "bounty": payout},
        )

    def tick(self, kernel: Any) -> None:
        """
        Advances crisis durations, applies active economic/astrophysical debuffs,
        and triggers periodic emergent events.
        """
        cycle = kernel.cycle_count

        # 1. Tick active crises
        expired = []
        for c_id, crisis in list(self.active_crises.items()):
            if cycle - crisis.start_cycle >= crisis.duration_cycles:
                expired.append(c_id)
            else:
                # Apply live crisis effects
                if crisis.crisis_type == "XENOPATHIC_CONTAGION":
                    sec = kernel.sectors.get(crisis.sector_id)
                    if sec and sec.port:
                        # Drive up port price for organics
                        sec.port.stock["ORGANICS"] = max(5, sec.port.stock.get("ORGANICS", 20) - 2)

                elif crisis.crisis_type == "SOVEREIGN_CURRENCY_RUN" and crisis.target_currency:
                    # Depreciate currency pool rate slightly
                    if hasattr(kernel, "fx_market"):
                        rate = kernel.fx_market.rate(crisis.target_currency)
                        kernel.fx_market.set_rate(crisis.target_currency, max(0.20, rate * 0.98))

        for c_id in expired:
            c = self.active_crises.pop(c_id)
            self.publish_article(
                f"CRISIS SUBSIDED: {c.name} has concluded.",
                "POLITICS",
                f"Emergency conditions in Sector {c.sector_id:03d} have dissipated as local systems stabilize.",
                cycle=cycle,
                sector_id=c.sector_id,
                urgency="ROUTINE",
                kernel=kernel,
            )

        # 2. Emergent Crisis Generation (roughly every 40-50 cycles if fewer than 3 active)
        if len(self.active_crises) < 3 and cycle > 0 and cycle % 45 == 0:
            ctype = random.choice(CRISIS_TYPES)
            sec_id = random.randint(1, len(kernel.sectors))
            self.spawn_crisis(ctype, sec_id, cycle, severity=0.6, duration=35, kernel=kernel)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_crises": {k: v.to_dict() for k, v in self.active_crises.items()},
            "news_history": [a.to_dict() for a in self.news_history],
            "next_crisis_id": self.next_crisis_id,
            "next_article_id": self.next_article_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrisesManager":
        mgr = cls()
        mgr.next_crisis_id = data.get("next_crisis_id", 101)
        mgr.next_article_id = data.get("next_article_id", 1001)
        for k, v in data.get("active_crises", {}).items():
            mgr.active_crises[k] = GalacticCrisis.from_dict(v)
        for a in data.get("news_history", []):
            mgr.news_history.append(GalNetArticle.from_dict(a))
        return mgr
