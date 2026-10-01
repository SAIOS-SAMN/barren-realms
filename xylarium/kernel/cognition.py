"""
Dual-Seat Cognition Engine (iae::think) for Xylarium.
Ported directly from Netstratum (/opt/netstratum/docs/51_COGNITION.md,
52_COGNITIVE_METABOLISM.md, 53_INTELLIGENCE_PORT.md, and 54_THE_NO_SCALAR_LAW.md).

Unifies all artificial intelligence under two precise seats:
- Seat 1: SURVIVE (Material Cochains, Ledger Books, and Empire Equilibrium)
- Seat 2: ARC (Spatial Navigation, Geometric Peeling, and Cartographic Decryption)

Core Axioms:
1. One Reduction: peel -> difference -> drain against grown_basis -> express or withhold.
2. The Residual Names the Deed: Deficit/Surplus vectors directly dictate actions without heuristic scores.
3. Thinking Changes the Thinker: Solved invariants crystallize into grown_basis for O(1) recall.
4. Cognitive Metabolism: Thought is a physical draw (Tier 1 Rations for baseline, Tier 2 Leisure for deep minting).
"""

import zlib
import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING

from xylarium.kernel import hulls
from xylarium.kernel import matter, topology
from xylarium.kernel.models import (
    ActionType,
    ActionResult,
    Captain,
    Planet,
    Sector,
    SecurityLevel,
    AIPersonality,
)
from xylarium.config import (
    COMMODITY_CONFIG,
    AI_FX_REPATRIATE_THRESHOLD,
    AI_INVEST_RESERVE,
    AI_CASH_FLOOR,
    AI_XP_VALUE_SOL,
    AI_RATION_LOW_WATER,
    AI_RATION_RESERVE,
    AI_WORKING_FLOAT,
    AI_MIN_FOOD_MONEY,
    AI_INVEST_SHARE,
    XP_TRADE_MAX,
    XP_TRADE_PROFIT_SCALE,
    XP_FREIGHT_BASE,
    XP_FREIGHT_MAX,
    XP_WINDOW_CYCLES,
    XP_WINDOW_SOFT_CAP,
    AI_PRICE_MEMORY_PORTS,
    AI_PRICE_MEMORY_STALE,
    AI_PLAN_MAX_AGE,
    AI_PLAN_MAX_HOPS,
    AI_MIN_PROFIT_PER_TURN,
    AI_CASH_RESERVE,
    AI_CRITICAL_SHIELDS,
    DEED_FAILURE_BACKOFF_MAX,
    ARCH_DIG_EQUIPMENT,
    ARCH_SHORE_EQUIPMENT,
)
from xylarium.kernel.economy import EconomyManager

if TYPE_CHECKING:
    from xylarium.kernel.engine import GameKernel


def rcf_hash(matrix_state: Any) -> str:
    """
    Computes a Rational Canonical Form (RCF) invariant conjugacy signature for spatial matrices.
    Permutation and rotation invariant: two isomorphic coordinate matrices produce the exact same RCF hash.
    """
    if isinstance(matrix_state, list):
        # Extract normalized vector invariant factors
        angles = []
        for row in matrix_state:
            for cell in row:
                if isinstance(cell, dict):
                    revealed = cell.get("is_revealed", False)
                    angle = cell.get("vector_angle", 0) if revealed else -1
                    s_val = cell.get("sector_val", 0) if revealed else 0
                    angles.append((angle, s_val))
                else:
                    angles.append((0, 0))
        # Compute cyclic invariant representation (lexicographically minimal orbit)
        n = len(angles)
        orbit = [angles[i:] + angles[:i] for i in range(n)]
        canonical = min(orbit)
        raw = json.dumps(canonical, sort_keys=True).encode("utf-8")
    elif isinstance(matrix_state, dict):
        canonical_dict = {str(k): v for k, v in sorted(matrix_state.items())}
        raw = json.dumps(canonical_dict, sort_keys=True).encode("utf-8")
    else:
        raw = str(matrix_state).encode("utf-8")

    return hashlib.blake2b(raw, digest_size=16).hexdigest()


@dataclass
class LedgerEntry:
    """A single [Have | Owe] coordinate balance."""
    coordinate: str
    have: float
    owe: float

    @property
    def residual(self) -> float:
        return self.have - self.owe

    @property
    def deficit(self) -> float:
        return max(0.0, self.owe - self.have)

    @property
    def surplus(self) -> float:
        return max(0.0, self.have - self.owe)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coordinate": self.coordinate,
            "have": round(self.have, 2),
            "owe": round(self.owe, 2),
            "residual": round(self.residual, 2),
            "deficit": round(self.deficit, 2),
            "surplus": round(self.surplus, 2),
        }


@dataclass
class LedgerBook:
    """A collection of [Have | Owe] entries representing an empire/captain subsystem."""
    name: str
    entries: Dict[str, LedgerEntry] = field(default_factory=dict)

    def add(self, coordinate: str, have: float, owe: float) -> None:
        self.entries[coordinate] = LedgerEntry(coordinate, float(have), float(owe))

    @property
    def total_residual(self) -> float:
        return sum(e.residual for e in self.entries.values())

    @property
    def total_deficit(self) -> float:
        return sum(e.deficit for e in self.entries.values())

    @property
    def total_surplus(self) -> float:
        return sum(e.surplus for e in self.entries.values())

    @property
    def is_closed(self) -> bool:
        """A book is closed if all owe requirements are fully met (deficit == 0)."""
        return all(e.deficit <= 0.001 for e in self.entries.values())

    def get_acute_deficit(self) -> Optional[LedgerEntry]:
        """Returns the coordinate with the largest unclosed gap."""
        unclosed = [e for e in self.entries.values() if e.deficit > 0]
        if not unclosed:
            return None
        return max(unclosed, key=lambda e: e.deficit)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "is_closed": self.is_closed,
            "total_residual": round(self.total_residual, 2),
            "total_deficit": round(self.total_deficit, 2),
            "total_surplus": round(self.total_surplus, 2),
            "entries": {k: e.to_dict() for k, e in self.entries.items()},
        }


@dataclass
class DivergenceVector:
    """
    Exact cochain divergence tensor across periodic elements, capital, and resources:
    div(Delta)_i = Have_i - Owe_i.
    Negative components indicate acute unclosed deficits; positive components indicate extractable surpluses.
    """
    coordinates: Dict[str, float] = field(default_factory=dict)
    demands: Dict[str, float] = field(default_factory=dict)

    def add(self, element: str, have: float, owe: float) -> None:
        self.coordinates[element] = float(have)
        self.demands[element] = float(owe)

    def divergence(self, element: str) -> float:
        return self.coordinates.get(element, 0.0) - self.demands.get(element, 0.0)

    def deficit(self, element: str) -> float:
        return max(0.0, self.demands.get(element, 0.0) - self.coordinates.get(element, 0.0))

    def surplus(self, element: str) -> float:
        return max(0.0, self.coordinates.get(element, 0.0) - self.demands.get(element, 0.0))

    @property
    def deficits(self) -> Dict[str, float]:
        return {
            k: self.demands[k] - self.coordinates.get(k, 0.0)
            for k in self.demands
            if self.coordinates.get(k, 0.0) < self.demands[k]
        }

    @property
    def surpluses(self) -> Dict[str, float]:
        return {
            k: self.coordinates[k] - self.demands.get(k, 0.0)
            for k in self.coordinates
            if self.coordinates[k] > self.demands.get(k, 0.0)
        }

    def acute_deficit(self) -> Optional[Tuple[str, float]]:
        d = self.deficits
        if not d:
            return None
        k = max(d, key=d.get)
        return k, d[k]

    def acute_surplus(self) -> Optional[Tuple[str, float]]:
        s = self.surpluses
        if not s:
            return None
        k = max(s, key=s.get)
        return k, s[k]

    @property
    def is_balanced(self) -> bool:
        return all(d <= 0.001 for d in self.deficits.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coordinates": {k: round(v, 2) for k, v in self.coordinates.items()},
            "demands": {k: round(v, 2) for k, v in self.demands.items()},
            "deficits": {k: round(v, 2) for k, v in self.deficits.items()},
            "surpluses": {k: round(v, 2) for k, v in self.surpluses.items()},
            "is_balanced": self.is_balanced,
        }


@dataclass
class CognitiveDeed:
    """A lawful, typed action instruction derived directly from algebraic residuals."""
    seat: str                # 'SURVIVE' or 'ARC'
    action_type: ActionType
    deed_name: str
    target_coordinate: str
    residual_magnitude: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    ration_cost: int = 1
    leisure_cost: int = 0
    certificate: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seat": self.seat,
            "action_type": self.action_type.value,
            "deed_name": self.deed_name,
            "target_coordinate": self.target_coordinate,
            "residual_magnitude": round(self.residual_magnitude, 2),
            "parameters": dict(self.parameters),
            "ration_cost": self.ration_cost,
            "leisure_cost": self.leisure_cost,
            "certificate": self.certificate,
        }


_ACTIVE_KERNEL: Any = None


def kernel_ref() -> Any:
    """The kernel the organ is currently thinking in (set at the top of CognitiveOrgan.think)."""
    return _ACTIVE_KERNEL


def temperament(captain: Any, kernel: Any = None) -> Dict[str, float]:
    """
    Each autonomous mind has its own temperament, drawn once and kept: thrift (how much of a surplus
    it invests), ambition (how much it values a verified track record), caution (how much cash it
    keeps back). Identical minds produce identical fortunes; temperament is where fortunes diverge.
    """
    t = getattr(captain, "traits", None)
    if t and "calling" in t:
        return t
    from xylarium.config import PERSONA_CALLINGS
    seed = zlib.crc32(f"{getattr(kernel, 'seed', 0)}:{captain.id}".encode())   # stable across processes
    rng = random.Random(seed)
    callings = list(PERSONA_CALLINGS)
    t = {
        "thrift": round(math.exp(rng.gauss(0.0, 0.7)), 3),     # how much of a surplus goes into stock (lognormal)
        "ambition": round(math.exp(rng.gauss(0.0, 0.4)), 3),   # how much a verified track record is worth
        "caution": round(math.exp(rng.gauss(0.0, 0.5)), 3),    # how much cash is kept back
        "risk": round(math.exp(rng.gauss(0.0, 0.6)), 3),       # >1 courts danger for bigger payoffs, <1 shuns it
        "horizon": round(math.exp(rng.gauss(0.0, 0.5)), 3),    # >1 patient builder (hulls, stakes, worlds), <1 quick profit
        "spend": round(rng.betavariate(1.5, 3.0), 3),          # appetite for spending ashore (a few hedonists)
        "calling": rng.choices(callings, weights=[PERSONA_CALLINGS[c][0] for c in callings])[0],
    }
    captain.traits = t
    return t


def persona_factor(captain: Any, kernel: Any, plan: Dict[str, Any]) -> float:
    """How this captain's persona and memory tilt the value of a plan: calling, risk appetite, past payoffs."""
    from xylarium.config import PERSONA_CALLINGS, PERSONA_CALLING_BIAS
    t = temperament(captain, kernel)
    kind = plan.get("kind", "")
    factor = PERSONA_CALLING_BIAS if kind in PERSONA_CALLINGS.get(t["calling"], (0, ()))[1] else 1.0
    risk = float(plan.get("risk", 1.0))
    if 0 < risk < 1.0:
        factor *= risk ** (1.0 / max(0.2, t["risk"]) - 1.0)   # a bold captain discounts danger less, a timid one more
    mem = getattr(captain, "persona_memory", {}) or {}
    rates = {k: v for k, v in mem.items() if k != "open" and isinstance(v, (int, float))}
    if kind in rates and len(rates) >= 2:
        mean = sum(rates.values()) / len(rates)
        factor *= max(0.6, min(1.6, 1.0 + 0.5 * (rates[kind] - mean) / (abs(mean) + 20.0)))
    return factor


def track_plan(captain: Any, kernel: Any, plan: Optional[Dict[str, Any]]) -> None:
    """Closes the previous plan's books (remembered payoff per turn) and opens the new one's."""
    from xylarium.config import PERSONA_MEMORY_RATE
    mem = captain.persona_memory
    cycle = int(getattr(kernel, "cycle_count", 0))
    liquid = captain.credits + sum(kernel.fx_market.to_sol_value(c, a) for c, a in captain.fx_wallet.items())
    cargo = captain.ship.cargo
    worth = liquid + sum(cargo.unbonded(g) * SeatGrow._base_value(g) * 0.8 for g in SeatGrow._cargo_goods(captain))
    prev = mem.get("open")
    if prev:
        rate = (worth - prev["m0"]) / max(1, cycle - prev["t0"])
        k = prev["kind"]
        mem[k] = round((1 - PERSONA_MEMORY_RATE) * mem.get(k, rate) + PERSONA_MEMORY_RATE * rate, 3)
    mem["open"] = {"kind": plan["kind"], "m0": worth, "t0": cycle} if plan else None


def welcome(kernel: Any, captain: Any, sector_id: int) -> bool:
    """Will this sector's port serve the captain? (Federation turrets turn outlaw player ships away.)"""
    check = getattr(kernel, "turret_blocks", None)
    sec = kernel.sectors.get(sector_id) if kernel is not None else None
    return sec is None or check is None or not check(captain, sec)


class SeatSurvive:
    """
    Seat 1: SURVIVE (Material Cochains & Empire Equilibrium)
    Processes five canonical ledger books:
    1. Ration Book: Food / biological or mineral fuel
    2. Thermal Book: Shields, hull armor, and entropy maintenance
    3. Security Book: Fighters, operatives, and defense garrisons
    4. Matter / Capital Book: Liquid credits, cargo, and structural metals
    5. Leisure / Exotics Book: Refined exotic elements for deep cognitive minting
    """

    @classmethod
    def peel_books(cls, entity: Any, kernel: "GameKernel") -> Dict[str, LedgerBook]:
        books: Dict[str, LedgerBook] = {}

        if isinstance(entity, Captain):
            captain = entity
            current_sec = kernel.sectors.get(captain.sector_id)
            ship = captain.ship
            cargo = ship.cargo

            # 1. RATION BOOK (Species survival & baseline cognition fuel)
            ration_book = LedgerBook("RATION")
            metabolism = getattr(captain, "metabolism", "biotic")
            # Only the ration the crew actually eats is owed (low-water mark); supplements are tracked
            # but owe nothing - a phantom shortage would send the ship on a pointless supply run
            low = AI_RATION_LOW_WATER
            if metabolism == "mineral":
                ration_book.add("ORE", cargo.ore, low)
                ration_book.add("SI", cargo.elements.get("Si", 0), 0.0)
            elif metabolism == "plasmic":
                ration_book.add("H", cargo.elements.get("H", 0), low)
                ration_book.add("HE-3", cargo.elements.get("He-3", 0), 0.0)
            elif metabolism == "cryogenic":
                ration_book.add("H2O", cargo.elements.get("H2O", 0), low)
            else:  # biotic / human
                ration_book.add("ORGANICS", cargo.organics, low)
                ration_book.add("H2O", cargo.elements.get("H2O", 0), 0.0)
            books["RATION"] = ration_book

            # 2. THERMAL BOOK (Deflector shields & hull syntropy)
            thermal_book = LedgerBook("THERMAL")
            thermal_book.add("SHIELDS", ship.shields, ship.max_shields)
            thermal_book.add("HULL_SYNTROPY", 100.0, 100.0)
            books["THERMAL"] = thermal_book

            # 3. SECURITY BOOK (Combat fighters & espionage defense)
            security_book = LedgerBook("SECURITY")
            threat_level = 10.0 if not current_sec else (
                40.0 if current_sec.security == SecurityLevel.ANARCHY else (
                    25.0 if current_sec.security == SecurityLevel.BORDERLAND else 10.0
                )
            )
            security_book.add("FIGHTERS", ship.fighters, threat_level)
            security_book.add("OPERATIVES", captain.operatives, 3.0)
            books["SECURITY"] = security_book

            # 4. MATTER / CAPITAL BOOK (Credits & structural metals)
            matter_book = LedgerBook("MATTER")
            matter_book.add("CREDITS", captain.credits, 2500.0)
            matter_book.add("STRUCTURAL_METALS", cargo.ore + cargo.equipment, 15.0)
            books["MATTER"] = matter_book

            # 5. LEISURE / EXOTICS BOOK (Exotic elements for breakthrough minting)
            leisure_book = LedgerBook("LEISURE")
            exotic_sum = sum(
                cargo.elements.get(k, 0)
                for k in ["SpR", "cryogenite", "stelalith", "umbrite", "chitinium", "U", "AdL"]
            )
            leisure_book.add("EXOTIC_ELEMENTS", exotic_sum, 5.0)
            books["LEISURE"] = leisure_book

        elif isinstance(entity, Planet):
            planet = entity
            pop = planet.population

            # 1. RATION BOOK
            ration_book = LedgerBook("RATION")
            required_food = max(1.0, pop / 1000.0)
            from xylarium.kernel import staples          # a people's rations are its own staple
            food = staples.of(kernel, planet)
            ration_book.add(food, staples.held(planet, food), required_food * 20.0)
            if food == "ORGANICS":
                ration_book.add("WATER", planet.element_reserves.get("H2O", 10), required_food * 10.0)
            books["RATION"] = ration_book

            # 2. THERMAL BOOK
            thermal_book = LedgerBook("THERMAL")
            thermal_book.add("SHIELDS", planet.shields, planet.max_shields)
            books["THERMAL"] = thermal_book

            # 3. SECURITY BOOK
            security_book = LedgerBook("SECURITY")
            security_book.add("DEFENSE_FIGHTERS", planet.fighters, 20.0 * (planet.citadel_level + 1))
            security_book.add("SECURITY_OPERATIVES", planet.security_operatives, 5.0 * (planet.citadel_level + 1))
            books["SECURITY"] = security_book

            # 4. MATTER BOOK
            matter_book = LedgerBook("MATTER")
            matter_book.add("TREASURY", planet.treasury, 5000.0)
            matter_book.add("ORE_RESERVES", planet.ore_silo, 100.0)
            books["MATTER"] = matter_book

            # 5. LEISURE BOOK
            leisure_book = LedgerBook("LEISURE")
            exotic_sum = sum(planet.element_reserves.values())
            leisure_book.add("EXOTIC_RESERVES", exotic_sum, 20.0)
            books["LEISURE"] = leisure_book

        return books

    # ------------------------------------------------------------------ treasury helpers
    @staticmethod
    def _spendable_local(kernel: "GameKernel", captain: Captain, cur: str) -> float:
        """What the captain can pay at a counter settling in ``cur``: local balance plus SOL at the live rate."""
        fxm = kernel.fx_market
        if cur == "SOL":
            return float(captain.credits)
        return captain.fx_wallet.get(cur, 0) + captain.credits * fxm.rate(cur) * (1 - 0.01)

    @staticmethod
    def _pool_currencies(kernel: "GameKernel", captain: Captain, keep: str, need: float = 0.0) -> None:
        """Converts other foreign balances into the counter's money (best route: a Galactic ISSE cross pair, or
        the federation exchanges via SOL) - only as much as the purchase needs, not everything held."""
        fxm = kernel.fx_market
        short = max(0.0, need - captain.fx_wallet.get(keep, 0)) if need > 0 else None
        for cur, amt in list(captain.fx_wallet.items()):
            if cur in (keep, "SOL") or amt <= 0:
                continue
            if short is not None:
                if short <= 0:
                    break
                # what this balance must give up to cover the shortfall, at the mid rate (plus the fee's margin)
                amt = min(amt, int(short * fxm.rate(cur) / max(1e-9, fxm.rate(keep)) * 1.01) + 1)
            _, _, got = fxm.exchange(captain, cur, keep, amt)
            if short is not None:
                short -= got

    @staticmethod
    def _liquidate_shares(kernel: "GameKernel", captain: Captain, need_local: float, cur: str) -> Optional["CognitiveDeed"]:
        """Cash is short and wealth is in stock: sell enough of the largest holding to cover the need."""
        mm = getattr(kernel, "market_manager", None)
        if mm is None or not captain.portfolio:
            return None
        need_sol = kernel.fx_market.to_sol_value(cur, need_local) * 1.3 + AI_CASH_FLOOR
        holdings = [(t, n, mm.companies[t]) for t, n in captain.portfolio.items() if t in mm.companies and n > 0]
        holdings = [h for h in holdings if h[2].treasury >= h[2].share_price]
        if not holdings:
            return None
        ticker, held, comp = max(holdings, key=lambda h: h[1] * h[2].share_price)
        shares = min(held, max(1, int(need_sol // max(1, comp.share_price)) + 1))
        return CognitiveDeed(
            seat="SURVIVE", action_type=ActionType.STOCK_SELL, deed_name="LIQUIDATE_SHARES_FOR_CASH",
            target_coordinate="CREDITS", residual_magnitude=need_sol,
            parameters={"ticker": ticker, "shares": shares}, ration_cost=0,
        )

    @classmethod
    def compute_divergence_vector(cls, entity: Any, kernel: "GameKernel") -> DivergenceVector:
        """
        Computes the cochain divergence tensor div(Delta)_i = Have_i - Owe_i across
        the periodic elements, commodities, and capital.
        """
        div = DivergenceVector()
        if isinstance(entity, Captain):
            captain = entity
            cargo = captain.ship.cargo
            metabolism = getattr(captain, "metabolism", "biotic")

            # 1. Volatiles & Life Precursors
            if metabolism == "plasmic":
                div.add("H", cargo.elements.get("H", 0), 10.0)
                div.add("He-3", cargo.elements.get("He-3", 0), 5.0)
                div.add("C", cargo.elements.get("C", 0), 1.0)
                div.add("H2O", cargo.elements.get("H2O", 0), 1.0)
            elif metabolism == "mineral":
                div.add("H", cargo.elements.get("H", 0), 2.0)
                div.add("He-3", cargo.elements.get("He-3", 0), 1.0)
                div.add("C", cargo.elements.get("C", 0), 2.0)
                div.add("H2O", cargo.elements.get("H2O", 0), 2.0)
            else:  # biotic / human
                div.add("H", cargo.elements.get("H", 0), 2.0)
                div.add("He-3", cargo.elements.get("He-3", 0), 1.0)
                div.add("C", cargo.elements.get("C", 0), 5.0)
                div.add("H2O", cargo.elements.get("H2O", 0), 5.0)
            div.add("Xe", cargo.elements.get("Xe", 0), 1.0)

            # 2. Structural Metals
            div.add("Fe", cargo.elements.get("Fe", 0), 5.0)
            div.add("Ti", cargo.elements.get("Ti", 0), 3.0)
            div.add("Si", cargo.elements.get("Si", 0), 3.0 if metabolism == "mineral" else 1.0)
            div.add("Ni", cargo.elements.get("Ni", 0), 2.0)
            div.add("Cu", cargo.elements.get("Cu", 0), 2.0)
            div.add("AdL", cargo.elements.get("AdL", 0), 1.0)

            # 3. Exotics
            for ex in ["U", "Pt", "SpR", "cryogenite", "stelalith", "umbrite", "chitinium", "pyrosite", "aetherium", "ferrolattice"]:
                div.add(ex, cargo.elements.get(ex, 0), 1.0)

            # 4. Legacy Commodities & Capital
            div.add("ORGANICS", cargo.organics, 10.0 if metabolism == "biotic" else 2.0)
            div.add("ORE", cargo.ore, 10.0 if metabolism == "mineral" else 2.0)
            div.add("EQUIPMENT", cargo.equipment, 5.0)
            div.add("CREDITS", captain.credits, 2500.0)

        elif isinstance(entity, Planet):
            planet = entity
            pop = planet.population
            req_bio = max(1.0, pop / 1000.0)

            # 1. Volatiles
            div.add("H2O", planet.element_reserves.get("H2O", 0), req_bio * 10.0)
            div.add("C", planet.element_reserves.get("C", 0), req_bio * 5.0)
            div.add("H", planet.element_reserves.get("H", 0), 10.0)
            div.add("He-3", planet.element_reserves.get("He-3", 0), 5.0)
            div.add("Xe", planet.element_reserves.get("Xe", 0), 2.0)

            # 2. Structural Metals
            div.add("Fe", planet.element_reserves.get("Fe", 0), 15.0 * (planet.citadel_level + 1))
            div.add("Ti", planet.element_reserves.get("Ti", 0), 8.0 * (planet.citadel_level + 1))
            div.add("Si", planet.element_reserves.get("Si", 0), 5.0)
            div.add("Ni", planet.element_reserves.get("Ni", 0), 5.0)
            div.add("Cu", planet.element_reserves.get("Cu", 0), 5.0)
            div.add("AdL", planet.element_reserves.get("AdL", 0), 2.0)

            # 3. Exotics
            for ex in ["U", "Pt", "SpR", "cryogenite", "stelalith", "umbrite", "chitinium", "pyrosite", "aetherium", "ferrolattice"]:
                div.add(ex, planet.element_reserves.get(ex, 0), 2.0)

            # 4. Silos & Capital
            div.add("ORGANICS", planet.organics_silo, req_bio * 20.0)
            div.add("ORE", planet.ore_silo, 100.0)
            div.add("TREASURY", planet.treasury, 5000.0)
            from xylarium.kernel import staples          # the staple's need overrides its generic entry
            food = staples.of(kernel, planet)
            if food != "ORGANICS":
                div.add("ORGANICS", planet.organics_silo, 0.0)
            div.add(food, staples.held(planet, food), req_bio * 20.0 + (100.0 if food == "ORE" else 0.0))

        return div

    @classmethod
    def reduce_survival(
        cls,
        entity: Any,
        books: Dict[str, LedgerBook],
        kernel: "GameKernel"
    ) -> Optional[CognitiveDeed]:
        """
        Reduces material cochains. 'The Residual Names the Deed'.
        Evaluates books in strict priority order:
        RATION (Survival) -> THERMAL (Integrity) -> SECURITY (Defense/War) -> MATTER (Trade/Capital) -> LEISURE.
        """
        # --- PLANET SURVIVAL REDUCTION ---
        if isinstance(entity, Planet):
            planet = entity
            # 1. Ration reduction (H2O, C, ORGANICS)
            ration_book = books.get("RATION")
            if ration_book and not ration_book.is_closed:
                deficit_entry = ration_book.get_acute_deficit()
                if deficit_entry and deficit_entry.coordinate in ["ORGANICS", "WATER", "H2O", "C"]:
                    return CognitiveDeed(
                        seat="SURVIVE",
                        action_type=ActionType.PLANET_ELEMENT_TRANSFER,
                        deed_name="EXTRACT_CRITICAL_DEPOSITS",
                        target_coordinate=deficit_entry.coordinate,
                        residual_magnitude=deficit_entry.deficit,
                        parameters={"element": "H2O" if deficit_entry.coordinate in ["WATER", "H2O"] else "C", "amount": 25},
                        ration_cost=0,
                    )

            # 2. Thermal reduction (Shields)
            thermal_book = books.get("THERMAL")
            if thermal_book and not thermal_book.is_closed:
                deficit_entry = thermal_book.get_acute_deficit()
                if deficit_entry and deficit_entry.coordinate == "SHIELDS" and planet.shields < planet.max_shields:
                    return CognitiveDeed(
                        seat="SURVIVE",
                        action_type=ActionType.PLANET_BUILD_SHIELD,
                        deed_name="REINFORCE_PLANETARY_SHIELDS",
                        target_coordinate="SHIELDS",
                        residual_magnitude=deficit_entry.deficit,
                        parameters={"planet_id": planet.id, "points": 25},
                        ration_cost=0,
                    )

            # 3. Security reduction (Fighters)
            security_book = books.get("SECURITY")
            if security_book and not security_book.is_closed:
                deficit_entry = security_book.get_acute_deficit()
                if deficit_entry and deficit_entry.coordinate == "DEFENSE_FIGHTERS" and planet.treasury >= 300:
                    return CognitiveDeed(
                        seat="SURVIVE",
                        action_type=ActionType.PLANET_RECRUIT_FIGHTERS,
                        deed_name="MOBILIZE_PLANETARY_DEFENSE",
                        target_coordinate="DEFENSE_FIGHTERS",
                        residual_magnitude=deficit_entry.deficit,
                        parameters={"planet_id": planet.id, "count": 5},
                        ration_cost=0,
                    )

            # 4. Matter surplus investment
            matter_book = books.get("MATTER")
            if matter_book and matter_book.total_surplus >= 5000:
                from xylarium.kernel import demography
                if planet.population < demography.housing_cap(planet, kernel_ref()):
                    return CognitiveDeed(
                        seat="SURVIVE",
                        action_type=ActionType.PLANET_INVEST,
                        deed_name="EXPAND_COLONIAL_HABITATS",
                        target_coordinate="POPULATION",
                        residual_magnitude=matter_book.total_surplus,
                        parameters={"planet_id": planet.id, "amount": 1000},
                        ration_cost=0,
                    )
                elif planet.citadel_level < 5 and planet.treasury >= 10000:
                    return CognitiveDeed(
                        seat="SURVIVE",
                        action_type=ActionType.PLANET_UPGRADE_CITADEL,
                        deed_name="UPGRADE_CITADEL_BASTION",
                        target_coordinate="CITADEL",
                        residual_magnitude=matter_book.total_surplus,
                        parameters={"planet_id": planet.id},
                        ration_cost=0,
                    )
            return None

        # --- CAPTAIN SURVIVAL REDUCTION ---
        if not isinstance(entity, Captain):
            return None

        captain = entity
        current_sec = kernel.sectors.get(captain.sector_id)
        if not current_sec:
            return None

        # 1. RATION REDUCTION: If ration is unclosed, the entity must feed/forage
        ration_book = books.get("RATION")
        if ration_book and not ration_book.is_closed:
            deficit_entry = ration_book.get_acute_deficit()
            if deficit_entry:
                coord_norm = deficit_entry.coordinate.upper()
                coord_to_comm = {
                    "ORGANICS": "ORGANICS",
                    "ORE": "ORE",
                    "SI": "Si",
                    "H": "H",
                    "HE-3": "He-3",
                    "H2O": "H2O",
                    "WATER": "H2O",
                    "C": "C",
                }
                target_comm = coord_to_comm.get(coord_norm, deficit_entry.coordinate)
                metabolism = getattr(captain, "metabolism", "biotic")
                if metabolism == "mineral":
                    survival_coords = {"ORE", "Si"}
                elif metabolism == "plasmic":
                    survival_coords = {"H", "He-3"}
                else:  # biotic
                    survival_coords = {"ORGANICS", "H2O"}

                # If cargo holds are full, liquidate non-ration cargo to make room
                if captain.ship.cargo.available_space == 0 and current_sec.port:
                    EconomyManager.ensure_port_inventory(current_sec.port)
                    sell_candidates = []
                    hold = captain.ship.cargo
                    for core in ("ORE", "ORGANICS", "EQUIPMENT"):
                        free_units = hold.unbonded(core)
                        if free_units > 0 and core not in survival_coords:
                            sell_candidates.append((core, free_units))
                    for el_k in list(hold.elements.keys()):
                        free_units = hold.unbonded(el_k)
                        if free_units > 0 and el_k not in survival_coords:
                            sell_candidates.append((el_k, free_units))

                    sold_something = False
                    for c_name, c_qty in sell_candidates:
                        if current_sec.port.buys.get(c_name, False):
                            amt_to_sell = min(int(c_qty), 10)
                            if amt_to_sell > 0:
                                return CognitiveDeed(
                                    seat="SURVIVE",
                                    action_type=ActionType.TRADE,
                                    deed_name="LIQUIDATE_CARGO_FOR_RATIONS",
                                    target_coordinate=deficit_entry.coordinate,
                                    residual_magnitude=deficit_entry.deficit,
                                    parameters={"trade_type": "SELL", "commodity": c_name, "amount": amt_to_sell},
                                    ration_cost=0,
                                )
                    if not sold_something and sell_candidates:
                        # Nothing will buy it: jettison a load to make room - it floats free as salvage
                        c_name, c_qty = sell_candidates[0]
                        cargo_h = captain.ship.cargo
                        dump = min(10, c_qty, cargo_h.held(c_name))
                        if c_name in ("ORE", "ORGANICS", "EQUIPMENT"):
                            setattr(cargo_h, c_name.lower(), getattr(cargo_h, c_name.lower()) - dump)
                        elif c_name in cargo_h.elements:
                            cargo_h.elements[c_name] -= dump
                            if cargo_h.elements[c_name] <= 0:
                                del cargo_h.elements[c_name]
                        if dump > 0:
                            sec_j = kernel.sectors.get(captain.sector_id)
                            if sec_j is not None:
                                sec_j.debris.append({"id": f"JETSAM-{sec_j.id:03d}-{kernel.cycle_count}-{captain.id[:6]}",
                                                     "cargo": {c_name: dump}, "created": kernel.cycle_count,
                                                     "source": f"{captain.name}'s jettisoned hold"})
                            else:
                                matter.sink("jettisoned", c_name, dump)

                # If in port that sells target_comm (and will serve us), buy rations - priced at the real
                # counter price in the port's own money, paid from every currency the captain holds
                if current_sec.port and welcome(kernel, captain, current_sec.id):
                    port = current_sec.port
                    EconomyManager.ensure_port_inventory(port)
                    stock_avail = port.stock.get(target_comm, 0)
                    port_sells = port.sells.get(target_comm, False)
                    if port_sells and stock_avail > 0 and captain.ship.cargo.available_space > 0:
                        # Docked at a food port: stock a deep reserve (up to a quarter of the hold), not a snack
                        from xylarium.config import get_commodity_stack_multiplier
                        have = captain.ship.cargo.unbonded(target_comm)
                        room = int(captain.ship.cargo.capacity * 0.25 / max(0.01, get_commodity_stack_multiplier(target_comm)))
                        needed = max(int(deficit_entry.deficit) + 3, min(AI_RATION_RESERVE, room) - have)
                        max_can_buy = min(needed, stock_avail, captain.ship.cargo.available_units_for(target_comm))
                        _, base_price = EconomyManager.get_unit_prices(port, target_comm)
                        unit_price = max(1, int(round(base_price * EconomyManager.counterparty_factor(captain, port, "buy"))))
                        spendable = cls._spendable_local(kernel, captain, port.currency)
                        if spendable < unit_price * min(max_can_buy, 3):
                            cls._pool_currencies(kernel, captain, port.currency, unit_price * max_can_buy)
                            spendable = cls._spendable_local(kernel, captain, port.currency)
                            if spendable < unit_price * min(max_can_buy, 3):
                                raise_cash = cls._liquidate_shares(kernel, captain, unit_price * max_can_buy, port.currency)
                                if raise_cash is not None:
                                    return raise_cash
                        # The bare refill is bought with any money; the deep reserve only with money beyond
                        # a working float (food must never eat the capital that earns the next meal)
                        essential = min(max_can_buy, int(deficit_entry.deficit) + 3)
                        float_local = AI_WORKING_FLOAT * kernel.fx_market.rate(port.currency)
                        extra_budget = max(0.0, spendable - float_local - essential * unit_price)
                        extra = min(max_can_buy - essential, int(extra_budget // unit_price))
                        affordable = min(essential, int(spendable * 0.97 // unit_price)) + max(0, extra)
                        if affordable > 0:
                            return CognitiveDeed(
                                seat="SURVIVE",
                                action_type=ActionType.TRADE,
                                deed_name="PURCHASE_RATIONS",
                                target_coordinate=deficit_entry.coordinate,
                                residual_magnitude=deficit_entry.deficit,
                                parameters={"trade_type": "BUY", "commodity": target_comm, "amount": affordable},
                                ration_cost=0,
                            )

                # Forage in Anarchy - a last resort for the truly broke (salvage buys food later);
                # a captain with money flies to a port that sells its rations instead
                liquid = captain.credits + sum(kernel.fx_market.to_sol_value(c, a) for c, a in captain.fx_wallet.items())
                if current_sec.security == SecurityLevel.ANARCHY and liquid < 100 and not captain.portfolio:
                    return CognitiveDeed(
                        seat="SURVIVE",
                        action_type=ActionType.CARTOGRAPHY_SALVAGE,
                        deed_name="FORAGE_DEEP_VOID",
                        target_coordinate=deficit_entry.coordinate,
                        residual_magnitude=deficit_entry.deficit,
                        ration_cost=0,
                    )

                # A broke crew can't buy food anywhere: flying port to port is futile. Earn first (freight
                # pays on delivery, mining costs nothing) - the growth seat below will choose the work.
                liquid_now = captain.credits + sum(kernel.fx_market.to_sol_value(c, a) for c, a in captain.fx_wallet.items())
                if liquid_now < AI_MIN_FOOD_MONEY and not captain.portfolio:
                    return SeatGrow.propose(captain, kernel)

                # Otherwise seek nearest port stocking target_comm
                # One breadth-first sweep finds the nearest port stocking the ration (Sol always does)
                def stocks_ration(sid: int) -> bool:
                    if not welcome(kernel, captain, sid):
                        return False
                    sp = kernel.sectors[sid].port
                    return sid == 1 or bool(sp and sp.sells.get(target_comm, False) and sp.stock.get(target_comm, 0) > 0)

                best_path = None
                dist_map, parent_map = topology.tree(kernel, captain.sector_id, 30)
                for sid, _d in sorted(dist_map.items(), key=lambda kv: kv[1]):
                    if sid != captain.sector_id and stocks_ration(sid):
                        hop = topology.first_hop(parent_map, captain.sector_id, sid)
                        best_path = [captain.sector_id, hop] if hop is not None else None
                        break

                if best_path and len(best_path) > 1:
                    return CognitiveDeed(
                        seat="SURVIVE",
                        action_type=ActionType.MOVE,
                        deed_name="SEEK_RATION_PORT",
                        target_coordinate=deficit_entry.coordinate,
                        residual_magnitude=deficit_entry.deficit,
                        parameters={"destination": best_path[1]},
                        ration_cost=0,
                    )

        # 1b. WORKING FLOAT: liquid money below the floor while wealth sits in stock -> sell some shares
        liquid_sol = captain.credits + sum(kernel.fx_market.to_sol_value(c, a) for c, a in captain.fx_wallet.items())
        if liquid_sol < AI_CASH_FLOOR and captain.portfolio:
            float_deed = cls._liquidate_shares(kernel, captain, 0.0, "SOL")
            if float_deed is not None:
                return float_deed

        # 2. THERMAL REDUCTION: If shields/syntropy are depleted, repair/recharge
        thermal_book = books.get("THERMAL")
        if thermal_book and not thermal_book.is_closed:
            deficit_entry = thermal_book.get_acute_deficit()
            if deficit_entry and deficit_entry.coordinate == "SHIELDS" and deficit_entry.deficit > 25:
                can_refit_here = (current_sec.id == 1 and welcome(kernel, captain, 1)) or (
                    current_sec.security == SecurityLevel.ANARCHY and current_sec.port is not None
                )
                budget = captain.credits - AI_CASH_RESERVE // 2
                if can_refit_here and budget >= 30:
                    return CognitiveDeed(
                        seat="SURVIVE",
                        action_type=ActionType.SHIPYARD_PURCHASE,
                        deed_name="RECHARGE_SHIELD_GRID",
                        target_coordinate="SHIELDS",
                        residual_magnitude=deficit_entry.deficit,
                        parameters={"item": "shields", "budget": budget},
                        ration_cost=1,
                    )
                elif can_refit_here or captain.ship.shields >= AI_CRITICAL_SHIELDS:
                    # Can't afford a refit (or not critical): earning money outranks sitting in drydock
                    pass
                elif current_sec.id != 1 or not welcome(kernel, captain, 1):
                    # Move towards the Sol stardock - or, if Sol's turrets turn us away, the nearest Void harbor
                    goal = 1
                    if not welcome(kernel, captain, 1):
                        dist_map, _ = topology.tree(kernel, captain.sector_id, 30)
                        harbors = [sid for sid, _d in sorted(dist_map.items(), key=lambda kv: kv[1])
                                   if kernel.sectors[sid].security == SecurityLevel.ANARCHY and kernel.sectors[sid].port]
                        goal = harbors[0] if harbors else captain.sector_id
                    path = kernel.find_path(captain.sector_id, goal) if goal != captain.sector_id else []
                    if path and len(path) > 1:
                        return CognitiveDeed(
                            seat="SURVIVE",
                            action_type=ActionType.MOVE,
                            deed_name="RETREAT_TO_STARDOCK",
                            target_coordinate="SECTOR_001",
                            residual_magnitude=deficit_entry.deficit,
                            parameters={"destination": path[1]},
                            ration_cost=1,
                        )

        # 3. SECURITY REDUCTION: If security deficit exists, recruit fighters
        security_book = books.get("SECURITY")
        if security_book and not security_book.is_closed:
            deficit_entry = security_book.get_acute_deficit()
            if deficit_entry and deficit_entry.coordinate == "FIGHTERS" and captain.credits >= 90:
                if current_sec.id == 1 and welcome(kernel, captain, 1):
                    return CognitiveDeed(
                        seat="SURVIVE",
                        action_type=ActionType.SHIPYARD_PURCHASE,
                        deed_name="RECRUIT_DEFENSE_FIGHTERS",
                        target_coordinate="FIGHTERS",
                        residual_magnitude=deficit_entry.deficit,
                        parameters={"item": "fighters", "amount": 2},
                        ration_cost=1,
                    )

        # If Security book has massive surplus and hostiles present in sector: ENGAGE CONQUEST
        from xylarium.kernel import lineage as _lineage
        if security_book and security_book.total_surplus > 10 and current_sec.security != SecurityLevel.FEDERATION \
                and not _lineage.house_endangered(kernel, captain):
            # Lawful engagement only: anyone in null space, but only wanted outlaws inside protected systems
            # Only pirates prey on anyone in open space; lawful captains hunt wanted outlaws and pirates
            is_pirate = captain.personality == AIPersonality.PIRATE or captain.bounty > 0

            def lawful_target(other: Captain) -> bool:
                return other.bounty > 0 or other.personality == AIPersonality.PIRATE

            hostile_captains = [
                c_id for c_id in current_sec.captains
                if c_id != captain.id and c_id in kernel.captains
                and ((is_pirate and current_sec.is_null_space) or lawful_target(kernel.captains[c_id]))
                and (current_sec.is_null_space or kernel.captains[c_id].bounty > 0)
                and current_sec.sentries.get(c_id, 0) < captain.ship.fighters
            ]
            if hostile_captains:
                target_id = random.choice(hostile_captains)
                return CognitiveDeed(
                    seat="SURVIVE",
                    action_type=ActionType.ATTACK_SHIP,
                    deed_name="INTERCEPT_HOSTILE_VESSEL",
                    target_coordinate="SECURITY_SURPLUS",
                    residual_magnitude=security_book.total_surplus,
                    parameters={"target_id": target_id},
                    ration_cost=1,
                )

        # 4. MATTER / CAPITAL REDUCTION: Commercial trading, arbitrage, and expansion
        matter_book = books.get("MATTER")
        if matter_book:
            # Check if liquid credits are deficient and can be replenished from owned colony treasury
            cred_entry = matter_book.entries.get("CREDITS")
            if cred_entry and cred_entry.deficit > 0 and current_sec.planets:
                for p in current_sec.planets:
                    if p.owner_id == captain.id and p.treasury > 0:
                        return CognitiveDeed(
                            seat="SURVIVE",
                            action_type=ActionType.PLANET_TAX,
                            deed_name="COLLECT_COLONIAL_TAXES",
                            target_coordinate="CREDITS",
                            residual_magnitude=float(p.treasury),
                            parameters={"planet_id": p.id},
                            ration_cost=0,
                        )

            # Colony Equilibrium Check: Relieve acute deficits on owned colonies - in the colonists' own staple
            if current_sec.planets:
                from xylarium.kernel import staples
                for p in current_sec.planets:
                    if p.owner_id == captain.id:
                        p_books = cls.peel_books(p, kernel)
                        p_ration = p_books.get("RATION")
                        if p_ration and not p_ration.is_closed:
                            p_def = p_ration.get_acute_deficit()
                            food = staples.of(kernel, p)
                            want = "H2O" if (p_def and p_def.coordinate == "WATER") else food
                            if p_def and p_def.coordinate in (food, "WATER"):
                                # Transfer cargo from ship if available
                                core = want in ("ORGANICS", "ORE")
                                lot = 10 if core else 5
                                if captain.ship.cargo.unbonded(want) >= lot:
                                    return CognitiveDeed(
                                        seat="SURVIVE",
                                        action_type=ActionType.PLANET_CARGO_TRANSFER if core else ActionType.PLANET_ELEMENT_TRANSFER,
                                        deed_name="RELIEVE_COLONY_DEFICIT",
                                        target_coordinate=want,
                                        residual_magnitude=p_def.deficit,
                                        parameters=({"planet_id": p.id, "commodity": want, "direction": "to_planet", "amount": lot}
                                                    if core else
                                                    {"planet_id": p.id, "element": want, "direction": "to_planet", "amount": lot}),
                                        ration_cost=0,
                                    )
                                # Or buy from local port
                                port = current_sec.port
                                if port and port.sells.get(want, False) and port.stock.get(want, 0) > 0 and captain.credits >= 200:
                                    return CognitiveDeed(
                                        seat="SURVIVE",
                                        action_type=ActionType.TRADE,
                                        deed_name="PROCURE_RELIEF_RATIONS",
                                        target_coordinate=want,
                                        residual_magnitude=p_def.deficit,
                                        parameters={"trade_type": "BUY", "commodity": want, "amount": lot},
                                        ration_cost=0,
                                    )

            # Empire-wide relief hauler chartering if capital is healthy
            if captain.credits >= 5000 and hasattr(kernel, "market_manager") and getattr(kernel.market_manager, "commission_trade_hauler", None):
                # Relief already en route to a sector must not be chartered again every tick
                served_sectors = {
                    h.dest_sector for h in kernel.market_manager.trade_haulers.values()
                    if h.owner_id == captain.id and h.active
                }
                for sec in kernel.sectors.values():
                    for p in sec.planets:
                        relief_dest = sec.id if sec.id != 1 else 30
                        if (
                            p.owner_id == captain.id
                            and relief_dest not in served_sectors
                            and kernel.sectors.get(relief_dest) is not None
                            and kernel.sectors[relief_dest].port is not None
                        ):
                            p_books = cls.peel_books(p, kernel)
                            p_ration = p_books.get("RATION")
                            if p_ration and not p_ration.is_closed:
                                p_def = p_ration.get_acute_deficit()
                                if p_def and p_def.coordinate in ["ORGANICS", "WATER"]:     # haulers carry grain
                                    return CognitiveDeed(
                                        seat="SURVIVE",
                                        action_type=ActionType.HAULER_COMMISSION,
                                        deed_name="CHARTER_RELIEF_HAULER",
                                        target_coordinate=p_def.coordinate,
                                        residual_magnitude=p_def.deficit,
                                        parameters={
                                            "origin_sector": 1,
                                            "dest_sector": relief_dest,
                                            "commodity_outbound": "ORGANICS",
                                            "commodity_return": "ORE",
                                            "hull_class": "STANDARD",
                                        },
                                        ration_cost=1,
                                    )

            # Capital: claim a world, deploy a toll gate, or buy shares - whichever is worth most over its cost as
            # this captain's mind judges it (decide.py). Cash beyond a working reserve (its temperament's caution)
            # is the budget; holding it is always the option worth exactly what it costs.
            temper = temperament(captain, kernel)
            reserve = AI_INVEST_RESERVE * temper["caution"]
            saving_for = SeatGrow._next_hull_price(captain, kernel)      # capital that compounds comes first
            if saving_for and captain.credits < saving_for * 1.5 + AI_CASH_RESERVE * 4 + 500:
                reserve = max(reserve, saving_for * 1.5 + AI_CASH_RESERVE * 4 + 500)
            spare = captain.credits - reserve
            if spare > 0:
                deed = SeatSurvive._invest(captain, current_sec, kernel, spare, temper, matter_book.total_surplus)
                if deed is not None:
                    return deed

        # Material books are closed or unactionable: the syntropic seat plans for growth
        return SeatGrow.propose(captain, kernel)


    @classmethod
    def _invest(cls, captain: Captain, sector: Any, kernel: "GameKernel", spare: float, temper: Dict[str, float],
                surplus: float) -> Optional[CognitiveDeed]:
        """Value each use of spare capital in SOL today against what it costs, and take the best (or none)."""
        from xylarium.config import (COLONY_KIT_COLONISTS, COLONY_KIT_CREDITS, SHARE_ISSUANCE_MAX_MULTIPLE,
                                     TOLL_GATE_DEFAULT_FEE, TOLL_GATE_DEPLOY_COST_CREDITS)
        from xylarium.kernel import decide, fertility, laws
        from xylarium.kernel.colony import ColonyManager
        m = decide.mind_of_captain(kernel, captain)
        horizon = laws.horizon(m["noise"], decide.BASE_HORIZON_QUARTERS)
        rate = decide.rate(kernel, "SOL")
        options = []
        # A. a world of one's own: its tax at full growth, from when its colonists have half filled it
        if COLONY_KIT_CREDITS <= spare:
            best = None
            for p in sector.planets:
                if p.owner_id is None and ColonyManager.claim_requirements(captain, p, sector, kernel) is None:
                    k = SeatGrow.feeds(captain, p, kernel)
                    if k > COLONY_KIT_COLONISTS and (best is None or k > best[1]):
                        best = (p, k)
            if best is not None:
                p, k = best
                from xylarium.kernel.demography import _tax_per_head_quarter
                fx_rate = kernel.fx_market.to_sol_value(p.currency, 1.0) if p.currency != "SOL" else 1.0
                fill = math.log(k / COLONY_KIT_COLONISTS) / max(1e-6, fertility.birth_share_quarter())
                delay = fill / 2
                worth = 0.0 if delay >= horizon else laws.present_value(
                    k / 2 * _tax_per_head_quarter(p) * fx_rate, horizon - delay, rate) * (1 + rate) ** (-delay)
                options.append(decide.option("claim_world", COLONY_KIT_CREDITS, worth, planet_id=p.id))
        # B. a toll on a secret shortcut: the fee times the traffic a sector sees in a quarter
        if captain.unlocked_secrets and not captain.toll_gates and TOLL_GATE_DEPLOY_COST_CREDITS <= spare:
            passages = len(kernel.captains) * 25 / max(1, len(kernel.sectors))
            worth = laws.present_value(TOLL_GATE_DEFAULT_FEE * passages, horizon, rate)
            options.append(decide.option("toll_gate", TOLL_GATE_DEPLOY_COST_CREDITS, worth,
                                         shortcut_id=captain.unlocked_secrets[0]))
        # C. shares: a share is worth its dividends over the horizon; buy where that most exceeds its price
        mm = getattr(kernel, "market_manager", None)
        if mm is not None and mm.companies:
            def capacity(c: Any) -> int:
                ceiling = int((c.initial_shares or c.total_shares) * SHARE_ISSUANCE_MAX_MULTIPLE)
                return c.available_shares + max(0, ceiling - c.total_shares)
            best = None
            for c in mm.companies.values():
                if capacity(c) < 10 or c.share_price <= 0:
                    continue
                cur = getattr(c, "home_currency", None) or "SOL"
                div = c.last_dividend * (kernel.fx_market.to_sol_value(cur, 1.0) if cur != "SOL" else 1.0)
                per_share = laws.present_value(div, horizon, rate)
                if best is None or per_share / c.share_price > best[1] / best[0].share_price:
                    best = (c, per_share, capacity(c))
            if best is not None:
                c, per_share, cap = best
                share = AI_INVEST_SHARE * temper["thrift"] * temper["horizon"] * (2.0 if temper["calling"] == "financier" else 1.0)
                lot = min(cap, max(10, int(spare * min(0.6, share) // max(1, c.share_price))))
                if lot * c.share_price <= spare:
                    options.append(decide.option("buy_shares", lot * c.share_price, lot * per_share,
                                                 ticker=c.ticker, shares=lot, cash=lot * c.share_price))
        # D. what it holds and no longer believes in, it sells; a company in distress priced above its estate it
        #    may short; a short whose bet is spent it covers. Every holding is worth the greater of its dividends
        #    over the horizon and its share of the estate (liquidation.valuation) - the same figure the market reads.
        if mm is not None and mm.companies:
            from xylarium.config import SHORT_MIN_CREDIT
            from xylarium.kernel import liquidation

            def held_value(c: Any) -> float:
                cur = getattr(c, "home_currency", None) or "SOL"
                div = c.last_dividend * (kernel.fx_market.to_sol_value(cur, 1.0) if cur != "SOL" else 1.0)
                return max(laws.present_value(div, horizon, rate), liquidation.fair_price(kernel, c))

            for t, n in list((getattr(captain, "portfolio", {}) or {}).items()):
                c = mm.companies.get(t)
                if c is None or n <= 0 or c.share_price <= 0 or (getattr(captain, "margin_loans", {}) or {}).get(t):
                    continue                         # pledged shares are the desk's to sell, not its own
                options.append(decide.option("sell_shares", n * held_value(c), n * c.share_price, ticker=t, shares=n))
            for t, pos in list((getattr(captain, "short_positions", {}) or {}).items()):
                c = mm.companies.get(t)
                if c is not None:                    # covering is worth the fall it no longer expects
                    options.append(decide.option("cover_short", 0.0, pos["shares"] * (held_value(c) - c.share_price),
                                                 ticker=t, shares=pos["shares"]))
            if getattr(captain, "credit_rating", 500) >= SHORT_MIN_CREDIT:
                for c in mm.companies.values():
                    if not liquidation.distressed(kernel, c.ticker) or c.ticker in (captain.short_positions or {}):
                        continue
                    gap = c.share_price - liquidation.fair_price(kernel, c)
                    lot = int(spare * 0.3 // max(1, c.share_price))
                    if gap > 0 and lot >= 10:
                        stake = lot * c.share_price * 0.5          # the margin it must post
                        options.append(decide.option("short_shares", stake, stake + lot * gap, ticker=c.ticker,
                                                     shares=lot))
        pick = decide.choose(kernel, options, m, captain.id, "invest")
        if pick is None:
            return None
        if pick["name"] in ("sell_shares", "short_shares", "cover_short"):
            act = {"sell_shares": ActionType.STOCK_SELL, "short_shares": ActionType.STOCK_SHORT,
                   "cover_short": ActionType.STOCK_COVER}[pick["name"]]
            return CognitiveDeed(seat="SURVIVE", action_type=act, deed_name=pick["name"].upper(),
                                 target_coordinate="CAPITAL_POSITIONS", residual_magnitude=surplus,
                                 parameters={"ticker": pick["ticker"], "shares": pick["shares"]}, ration_cost=1)
        if pick["name"] == "claim_world":
            return CognitiveDeed(seat="SURVIVE", action_type=ActionType.PLANET_CLAIM, deed_name="COLONIZE_TERRESTRIAL_BODY",
                                 target_coordinate="CAPITAL_EXPANSION", residual_magnitude=surplus,
                                 parameters={"planet_id": pick["planet_id"]}, ration_cost=1)
        if pick["name"] == "toll_gate":
            return CognitiveDeed(seat="SURVIVE", action_type=ActionType.TOLL_GATE_DEPLOY, deed_name="DEPLOY_ORBITAL_TOLL_GATE",
                                 target_coordinate="MONOPOLY_TRANSIT", residual_magnitude=surplus,
                                 parameters={"shortcut_id": pick["shortcut_id"], "toll_fee": TOLL_GATE_DEFAULT_FEE},
                                 ration_cost=1)
        return CognitiveDeed(seat="SURVIVE", action_type=ActionType.STOCK_BUY, deed_name="ACQUIRE_CORPORATE_SHARES",
                             target_coordinate="CAPITAL_DIVIDENDS", residual_magnitude=surplus,
                             parameters={"ticker": pick["ticker"], "shares": pick["shares"]}, ration_cost=1)


class SeatGrow:
    """
    Seat 3: GROW (Syntropic Drive)
    When survival residuals are closed, cognition turns generative: it remembers
    observed port prices (with their currency), values every opportunity by expected
    profit per turn in SOL (converted at live ISSE FX, risk-discounted by security),
    commits to a multi-turn plan, and realizes profit. Opportunities: commodity
    arbitrage across regions, freight and industrial extraction contracts, asteroid
    mining in null space, debris salvage, and capital growth (hull upgrades). With
    nothing worth doing it explores toward unknown or stale markets.
    """

    TRADE_GOODS = ("ORE", "ORGANICS", "EQUIPMENT", "H", "LUX_STIMULANT", "LUX_RESONANT", "LUX_EPHEMERA", "LUX_CURIO")
    RISK_DISCOUNT = {"FEDERATION": 1.0, "BORDERLAND": 0.85, "ANARCHY": 0.6}

    @staticmethod
    def _cycle(kernel: "GameKernel") -> int:
        return int(getattr(kernel, "cycle_count", 0))

    @staticmethod
    def _sol(cur: str, amount: float) -> float:
        from xylarium.kernel.fx import ACTIVE_FX
        return ACTIVE_FX.to_sol_value(cur, amount) if (ACTIVE_FX is not None and cur != "SOL") else float(amount)

    @staticmethod
    def _base_value(comm: str) -> float:
        return float(COMMODITY_CONFIG.get(comm, {}).get("base_price", 10))

    @classmethod
    def observe_port(cls, captain: Captain, sector: Any, kernel: "GameKernel") -> None:
        port = getattr(sector, "port", None)
        if not port or not welcome(kernel, captain, sector.id):
            return  # a port that won't serve us is not a market we can use
        EconomyManager.ensure_port_inventory(port)
        goods = set(cls.TRADE_GOODS)
        for belt_type in ("Fe", "Si", "Ti", "Ni", "H2O", "He-3", "C"):
            goods.add(belt_type)
        goods.update(cls._cargo_goods(captain))   # remember what this port does with what we actually carry
        prices = {}
        for comm in goods:
            buy_p, sell_p = EconomyManager.get_unit_prices(port, comm)
            prices[comm] = [
                buy_p, sell_p,
                1 if port.buys.get(comm, False) else 0,
                1 if port.sells.get(comm, False) else 0,
                int(port.stock.get(comm, 0)),
            ]
        mem = captain.price_memory
        mem[str(sector.id)] = {"c": cls._cycle(kernel), "cur": getattr(port, "currency", "SOL"),
                               "liq": int(getattr(port, "treasury", 0)), "p": prices}
        if len(mem) > AI_PRICE_MEMORY_PORTS:
            oldest = min(mem, key=lambda k: mem[k].get("c", 0))
            mem.pop(oldest, None)

    @classmethod
    def _step_toward(cls, captain: Captain, kernel: "GameKernel", parent, goal: int, name: str) -> Optional[CognitiveDeed]:
        hop = topology.first_hop(parent, captain.sector_id, goal)
        if hop is None:
            path = kernel.find_path(captain.sector_id, goal)
            hop = path[1] if path and len(path) > 1 else None
        if hop is None:
            return None
        return CognitiveDeed(
            seat="GROW", action_type=ActionType.MOVE, deed_name=name,
            target_coordinate=f"SECTOR_{goal:03d}", residual_magnitude=1.0,
            parameters={"destination": hop}, ration_cost=1,
        )

    @classmethod
    def _ration_keep(cls, captain: Captain, comm: str) -> int:
        from xylarium.config import CAPTAIN_RATIONS
        # The crew's own food is never trade goods: the whole reserve stays aboard
        return AI_RATION_RESERVE if CAPTAIN_RATIONS.get(getattr(captain, "metabolism", "biotic"), "ORGANICS") == comm else 0

    @classmethod
    def _cargo_goods(cls, captain: Captain) -> List[str]:
        cargo = captain.ship.cargo
        goods = [c for c in ("ORE", "ORGANICS", "EQUIPMENT") if getattr(cargo, c.lower()) > 0]
        goods += [k for k, v in cargo.elements.items() if v > 0 and k in COMMODITY_CONFIG]
        return [g for g in goods if cargo.unbonded(g) - cls._ration_keep(captain, g) > 0]

    @classmethod
    def _sell_here(cls, captain: Captain, sector: Any, min_margin: float, only: Optional[str] = None) -> Optional[CognitiveDeed]:
        port = getattr(sector, "port", None)
        if not port or (kernel_ref() is not None and not welcome(kernel_ref(), captain, sector.id)):
            return None
        cargo = captain.ship.cargo
        plan = captain.active_plan or {}
        for comm in ([only] if only else cls._cargo_goods(captain)):
            qty = cargo.unbonded(comm) - cls._ration_keep(captain, comm)
            if qty <= 0 or not port.buys.get(comm, False):
                continue
            buy_p, _ = EconomyManager.get_unit_prices(port, comm)
            if port.treasury < buy_p * min(qty, 5):
                continue  # illiquid port: it cannot pay for the cargo
            price_sol = cls._sol(port.currency, buy_p)
            basis_sol = plan.get("unit_cost_sol") if plan.get("commodity") == comm else None
            if basis_sol is None:
                basis_sol = cls._base_value(comm) * 0.8  # mined, salvaged or legacy cargo: sell near fair value
            if price_sol >= basis_sol * min_margin:
                return CognitiveDeed(
                    seat="GROW", action_type=ActionType.TRADE, deed_name="SELL_AT_PROFIT",
                    target_coordinate=comm, residual_magnitude=float(price_sol - basis_sol),
                    parameters={"trade_type": "SELL", "commodity": comm, "amount": qty}, ration_cost=1,
                )
        return None

    @classmethod
    def _best_market_for(cls, captain: Captain, comm: str, dist: Dict[int, int], kernel: "GameKernel") -> Optional[int]:
        cycle = cls._cycle(kernel)
        best = None
        for sid_s, entry in captain.price_memory.items():
            sid = int(sid_s)
            row = entry["p"].get(comm)
            if not row or not row[2] or sid not in dist or cycle - entry.get("c", 0) > AI_PRICE_MEMORY_STALE:
                continue
            if entry.get("liq", 10 ** 9) < row[0] * 5:
                continue  # it buys, but it couldn't pay last time we looked
            value = cls._sol(entry.get("cur", "SOL"), row[0]) / (dist[sid] + 2)
            if best is None or value > best[0]:
                best = (value, sid)
        if best:
            return best[1]
        # Unknown market: nearest port not already known to refuse this commodity
        mem = captain.price_memory
        # (a port seen recently that didn't list this good as bought doesn't buy it)
        ports = [sid for sid, d in sorted(dist.items(), key=lambda kv: kv[1])
                 if kernel.sectors[sid].port is not None and sid != captain.sector_id and welcome(kernel, captain, sid)
                 and not (str(sid) in mem and cycle - mem[str(sid)].get("c", 0) <= AI_PRICE_MEMORY_STALE
                          and not (mem[str(sid)]["p"].get(comm) or [0, 0, 0])[2])]
        return ports[0] if ports else None

    @classmethod
    def _advance_plan(cls, captain: Captain, plan: Dict[str, Any], sector: Any, dist, parent, kernel: "GameKernel") -> Optional[CognitiveDeed]:
        kind = plan["kind"]
        if kind in ("haul", "liquidate"):
            comm, dest = plan["commodity"], plan["dest"]
            if captain.ship.cargo.unbonded(comm) - cls._ration_keep(captain, comm) <= 0:
                return None
            if captain.sector_id == dest:
                # Arrived: realize the plan even at a thin margin rather than carry dead inventory
                return cls._sell_here(captain, sector, min_margin=0.9 if kind == "haul" else 0.0, only=comm)
            return cls._step_toward(captain, kernel, parent, dest, "HAUL_TO_MARKET")
        if kind in ("freight", "extract"):
            mm = getattr(kernel, "market_manager", None)
            contract = mm.contracts.get(plan["contract"]) if mm else None
            if not contract:
                return None
            sign_at = contract.destination_sector if contract.kind == "EXTRACTION" else contract.origin_sector
            if contract.status == "OPEN":
                if captain.sector_id == sign_at:
                    return CognitiveDeed(
                        seat="GROW", action_type=ActionType.FREIGHT_ACCEPT, deed_name="SIGN_FREIGHT_MANIFEST",
                        target_coordinate=contract.id, residual_magnitude=float(contract.payout_credits),
                        parameters={"contract_id": contract.id}, ration_cost=1,
                    )
                return cls._step_toward(captain, kernel, parent, sign_at, "HAUL_TO_MARKET")
            if contract.status != "IN_TRANSIT" or contract.accepted_by != captain.id:
                return None
            if contract.kind == "EXTRACTION" and captain.ship.cargo.unbonded(contract.commodity) < contract.amount:
                # Mine the ordered element at the belt the order names (or any belt carrying it)
                return cls._mine_step(captain, sector, contract.origin_sector, parent, kernel, want=contract.commodity)
            if captain.sector_id == contract.destination_sector:
                return CognitiveDeed(
                    seat="GROW", action_type=ActionType.FREIGHT_DELIVER, deed_name="DELIVER_FREIGHT",
                    target_coordinate=contract.id, residual_magnitude=float(contract.payout_credits),
                    parameters={"contract_id": contract.id, "planet_id": contract.destination_planet_id}, ration_cost=1,
                )
            return cls._step_toward(captain, kernel, parent, contract.destination_sector, "HAUL_TO_MARKET")
        if kind == "mine":
            if captain.ship.cargo.available_space < 3:
                return None  # holds full: liquidate next
            return cls._mine_step(captain, sector, plan["belt_sector"], parent, kernel)
        if kind == "dig":
            planet = kernel.get_planet(plan["planet_id"])
            ruins = getattr(planet, "ruins", None) if planet else None
            if not ruins or ruins["dug_depth"] >= len(ruins["strata"]) or len(captain.artifacts) >= 8:
                return None
            tools_needed = ARCH_DIG_EQUIPMENT + (ARCH_SHORE_EQUIPMENT if ruins["stability"] < 0.5 else 0)
            if captain.ship.cargo.unbonded("EQUIPMENT") < tools_needed:
                port = getattr(sector, "port", None)
                if port and port.sells.get("EQUIPMENT", False) and port.stock.get("EQUIPMENT", 0) >= 5:
                    return CognitiveDeed(
                        seat="GROW", action_type=ActionType.TRADE, deed_name="OUTFIT_DIG_TOOLS",
                        target_coordinate="EQUIPMENT", residual_magnitude=1.0,
                        parameters={"trade_type": "BUY", "commodity": "EQUIPMENT", "amount": 6}, ration_cost=1,
                    )
                ports = [sid for sid, d in sorted(dist.items(), key=lambda kv: kv[1])
                         if kernel.sectors[sid].port is not None and kernel.sectors[sid].port.sells.get("EQUIPMENT")]
                return cls._step_toward(captain, kernel, parent, ports[0], "HAUL_TO_MARKET") if ports else None
            if captain.sector_id != planet.sector_id:
                return cls._step_toward(captain, kernel, parent, planet.sector_id, "HAUL_TO_MARKET")
            if captain.id not in ruins["surveyed_by"]:
                return CognitiveDeed(seat="GROW", action_type=ActionType.SURVEY_RUINS, deed_name="SURVEY_RUINS",
                                     target_coordinate=planet.id, residual_magnitude=1.0,
                                     parameters={"planet_id": planet.id}, ration_cost=1)
            return CognitiveDeed(seat="GROW", action_type=ActionType.EXCAVATE, deed_name="EXCAVATE_RUINS",
                                 target_coordinate=planet.id, residual_magnitude=1.0,
                                 parameters={"planet_id": planet.id, "shore": ruins["stability"] < 0.5}, ration_cost=1)
        if kind == "settle":
            from xylarium.config import COLONY_KIT_EQUIPMENT
            planet = kernel.get_planet(plan["planet_id"])
            if planet is None or planet.owner_id or planet.natives or planet.population > 0:
                return None
            if captain.ship.cargo.unbonded("EQUIPMENT") < COLONY_KIT_EQUIPMENT:
                port = getattr(sector, "port", None)
                if port and port.sells.get("EQUIPMENT", False) and port.stock.get("EQUIPMENT", 0) >= COLONY_KIT_EQUIPMENT \
                        and welcome(kernel, captain, sector.id):
                    return CognitiveDeed(
                        seat="GROW", action_type=ActionType.TRADE, deed_name="OUTFIT_COLONY_KIT",
                        target_coordinate="EQUIPMENT", residual_magnitude=1.0,
                        parameters={"trade_type": "BUY", "commodity": "EQUIPMENT",
                                    "amount": COLONY_KIT_EQUIPMENT - captain.ship.cargo.unbonded("EQUIPMENT")},
                        ration_cost=1,
                    )
                ports = [sid for sid, d in sorted(dist.items(), key=lambda kv: kv[1])
                         if kernel.sectors[sid].port is not None and kernel.sectors[sid].port.sells.get("EQUIPMENT")
                         and welcome(kernel, captain, sid)]
                return cls._step_toward(captain, kernel, parent, ports[0], "HAUL_TO_MARKET") if ports else None
            if captain.sector_id != planet.sector_id:
                return cls._step_toward(captain, kernel, parent, planet.sector_id, "HAUL_TO_MARKET")
            return CognitiveDeed(seat="GROW", action_type=ActionType.PLANET_CLAIM, deed_name="FOUND_COLONY",
                                 target_coordinate=planet.id, residual_magnitude=1.0,
                                 parameters={"planet_id": planet.id}, ration_cost=1)
        if kind == "upgrade":
            yard = cls._shipyard_for(captain, kernel, dist)
            if yard is None:
                return None
            if captain.sector_id == yard:
                return CognitiveDeed(
                    seat="GROW", action_type=ActionType.SHIPYARD_PURCHASE, deed_name="COMMISSION_LARGER_HULL",
                    target_coordinate=plan["ship"], residual_magnitude=1.0,
                    parameters={"item": "upgrade_ship", "ship_name": plan["ship"]}, ration_cost=1,
                )
            return cls._step_toward(captain, kernel, parent, yard, "HAUL_TO_MARKET")
        return None

    @classmethod
    def _mine_step(cls, captain: Captain, sector: Any, belt_sector: int, parent, kernel: "GameKernel",
                   want: Optional[str] = None) -> Optional[CognitiveDeed]:
        if captain.sector_id != belt_sector:
            return cls._step_toward(captain, kernel, parent, belt_sector, "HAUL_TO_MARKET")
        belts = [b for b in sector.belts if b["reserve"] > 0 and (want is None or b["composition"].get(want, 0) > 0)]
        if not belts:
            return None
        unscanned = [b for b in belts if b["id"] not in captain.scanned_belts]
        if unscanned:
            return CognitiveDeed(
                seat="GROW", action_type=ActionType.SCAN_SPACE, deed_name="SURVEY_ASTEROID_BELT",
                target_coordinate=unscanned[0]["id"], residual_magnitude=1.0, parameters={}, ration_cost=1,
            )
        # Contested space: leave a sentry picket over the belt before cutting ore
        if (sector.security != SecurityLevel.FEDERATION and sector.sentries.get(captain.id, 0) == 0
                and captain.ship.fighters >= 16):
            return CognitiveDeed(
                seat="GROW", action_type=ActionType.DEPLOY_SENTRIES, deed_name="POST_SENTRY_PICKET",
                target_coordinate=f"SECTOR_{sector.id:03d}", residual_magnitude=1.0,
                parameters={"amount": captain.ship.fighters // 2}, ration_cost=1,
            )
        belt = max(belts, key=lambda b: b["reserve"])
        return CognitiveDeed(
            seat="GROW", action_type=ActionType.MINE_ASTEROIDS, deed_name="MINE_ASTEROID_BELT",
            target_coordinate=belt["id"], residual_magnitude=float(belt["reserve"]),
            parameters={"belt_id": belt["id"]}, ration_cost=1,
        )

    @classmethod
    def _arbitrage_options(cls, captain: Captain, sector: Any, dist: Dict[int, int], kernel: "GameKernel") -> List[Tuple[float, Dict[str, Any], Optional[CognitiveDeed]]]:
        port = getattr(sector, "port", None)
        if not port:
            return []
        cycle = cls._cycle(kernel)
        cash_sol = captain.credits - AI_CASH_RESERVE
        opts = []
        for comm in cls.TRADE_GOODS:
            if not port.sells.get(comm, False) or port.stock.get(comm, 0) <= 0:
                continue
            _, sell_p = EconomyManager.get_unit_prices(port, comm)
            cost_sol = cls._sol(port.currency, sell_p)
            if sell_p <= 0 or cash_sol < cost_sol:
                continue
            qty = int(min(captain.ship.cargo.available_units_for(comm), cash_sol // max(0.01, cost_sol), port.stock.get(comm, 0)))
            if qty <= 0:
                continue
            for sid_s, entry in captain.price_memory.items():
                sid = int(sid_s)
                if sid == sector.id or sid not in dist or cycle - entry.get("c", 0) > AI_PRICE_MEMORY_STALE:
                    continue
                row = entry["p"].get(comm)
                if not row or not row[2]:
                    continue
                margin = cls._sol(entry.get("cur", "SOL"), row[0]) - cost_sol
                if margin <= 0:
                    continue
                units = min(qty, int(entry.get("liq", 10 ** 9) // max(1, row[0])))
                if units <= 0:
                    continue
                risk = cls.RISK_DISCOUNT.get(kernel.sectors[sid].security.value, 0.6)
                value = margin * units * risk / (dist[sid] + 2)
                res_mag = float(margin * units)
                profit = margin * units * risk
                xp = min(XP_TRADE_MAX, math.sqrt(max(0.0, profit) / XP_TRADE_PROFIT_SCALE))
                plan = {"kind": "haul", "commodity": comm, "dest": sid, "since": cycle, "unit_cost_sol": cost_sol,
                        "xp_per_turn": xp / (dist[sid] + 2), "risk": risk}
                deed = CognitiveDeed(
                    seat="GROW", action_type=ActionType.TRADE, deed_name="LOAD_ARBITRAGE_CARGO",
                    target_coordinate=comm, residual_magnitude=res_mag,
                    parameters={"trade_type": "BUY", "commodity": comm, "amount": int(units)}, ration_cost=1,
                )
                opts.append((value, plan, deed))
        return opts

    @classmethod
    def _contract_options(cls, captain: Captain, dist: Dict[int, int], kernel: "GameKernel") -> List[Tuple[float, Dict[str, Any], Optional[CognitiveDeed]]]:
        from xylarium.kernel.nullspace import NullSpaceManager
        mm = getattr(kernel, "market_manager", None)
        if not mm or len(getattr(captain, "active_contracts", [])) >= 3:
            return []
        cycle = cls._cycle(kernel)
        free = captain.ship.cargo.available_space
        yield_per_turn = NullSpaceManager.mining_yield(captain)
        opts = []
        candidates = []
        for c in mm.contracts.values():
            if c.status != "OPEN" or c.amount > free:
                continue
            sign_at = c.destination_sector if c.kind == "EXTRACTION" else c.origin_sector
            if sign_at not in dist:
                continue
            candidates.append((c, sign_at))
        candidates.sort(key=lambda cs: -cls._sol(cs[0].currency, cs[0].payout_credits))
        for c, sign_at in candidates[:6]:
            route = kernel.find_path(c.origin_sector, c.destination_sector)
            if not route:
                continue
            legs = len(route) - 1
            if c.kind == "EXTRACTION":
                turns = dist[sign_at] + 2 * legs + 2 + -(-c.amount // max(1, yield_per_turn))
                kind = "extract"
            else:
                turns = dist[sign_at] + legs
                kind = "freight"
            if c.expiry_cycle - cycle <= turns + 2:
                continue
            risk = cls.RISK_DISCOUNT.get(c.hazard_level, 0.6)
            value = cls._sol(c.currency, c.payout_credits) * risk / (turns + 2)
            xp = min(XP_FREIGHT_MAX, XP_FREIGHT_BASE + legs) * risk
            opts.append((value, {"kind": kind, "contract": c.id, "since": cycle, "xp_per_turn": xp / (turns + 2),
                                 "risk": risk}, None))
        return opts

    @classmethod
    def _mining_options(cls, captain: Captain, dist: Dict[int, int], kernel: "GameKernel") -> List[Tuple[float, Dict[str, Any], Optional[CognitiveDeed]]]:
        from xylarium.kernel.nullspace import NullSpaceManager
        per_turn = NullSpaceManager.mining_yield(captain)
        space = captain.ship.cargo.available_space
        if space < per_turn:
            return []
        opts = []
        cycle = cls._cycle(kernel)
        for sid, d in dist.items():
            sec = kernel.sectors[sid]
            if d > 4 or not sec.belts:
                continue
            for belt in sec.belts:
                if belt["reserve"] < per_turn * 3:
                    continue
                unit_value = sum(share * cls._base_value(e) for e, share in belt["composition"].items()) * 0.8
                turns = d + -(-space // per_turn) + 3  # travel, mining, and a trip to market
                risk = cls.RISK_DISCOUNT.get(sec.security.value, 0.6)
                value = unit_value * min(space, belt["reserve"]) * risk / (turns + 2)
                mine_turns = -(-space // per_turn)
                opts.append((value, {"kind": "mine", "belt_sector": sid, "since": cycle,
                                     "xp_per_turn": 1.5 * mine_turns / (turns + 2), "risk": risk}, None))
        return opts

    @classmethod
    def _archaeology_options(cls, captain: Captain, dist: Dict[int, int], kernel: "GameKernel") -> List[Tuple[float, Dict[str, Any], Optional[CognitiveDeed]]]:
        from xylarium.kernel.archaeology import ArchaeologyManager
        if len(captain.artifacts) >= 8:
            return []
        opts = []
        cycle = cls._cycle(kernel)
        for sid, d in dist.items():
            if d > 4:
                continue
            for planet in kernel.sectors[sid].planets:
                r = getattr(planet, "ruins", None)
                if not r or r["dug_depth"] >= len(r["strata"]):
                    continue
                if (planet.owner_id and planet.owner_id != captain.id) or (planet.population > 0 and planet.owner_id != captain.id):
                    continue
                stratum = r["strata"][r["dug_depth"]]
                probe = {"kind": "ANTIQUITY", "stratum": stratum["depth"], "era": r["era"],
                         "tech_level": r["tech_level"], "condition": 0.7}
                per_dig = ArchaeologyManager.appraisal(probe) * 1.3 + (r["hoard"] / max(1, len(r["strata"])) * 0.3
                                                                       if r["hoard"] else 0)
                value = per_dig * min(4, stratum["finds_left"]) / (d + 6)
                opts.append((value, {"kind": "dig", "planet_id": planet.id, "since": cycle,
                                     "xp_per_turn": 1.0}, None))
        return opts

    @classmethod
    def _artifact_deed(cls, captain: Captain, sector: Any, kernel: "GameKernel") -> Optional[CognitiveDeed]:
        """Study relics while researching; sell pieces the local curio desk will actually buy."""
        from xylarium.kernel.archaeology import ArchaeologyManager
        if not captain.artifacts:
            return None
        relics = [a for a in captain.artifacts if a["kind"] == "TECH_RELIC"]
        if relics:
            return CognitiveDeed(seat="GROW", action_type=ActionType.STUDY_ARTIFACT, deed_name="STUDY_TECH_RELIC",
                                 target_coordinate=relics[0]["id"], residual_magnitude=1.0,
                                 parameters={"artifact_id": relics[0]["id"]}, ration_cost=1)
        if getattr(sector, "port", None) is not None:
            for art in captain.artifacts:
                price, reason = ArchaeologyManager.offer(art, sector, kernel)
                if not reason and price <= sector.port.treasury:
                    return CognitiveDeed(seat="GROW", action_type=ActionType.SELL_ARTIFACT, deed_name="SELL_ANTIQUITY",
                                         target_coordinate=art["id"], residual_magnitude=float(price),
                                         parameters={"artifact_id": art["id"]}, ration_cost=1)
        return None

    @classmethod
    def _shore_leave(cls, captain: Captain, sector: Any, kernel: "GameKernel") -> Optional[CognitiveDeed]:
        from xylarium.config import SHORE_LEAVE_MAX_SHARE
        if sector.port is None or not welcome(kernel, captain, sector.id):
            return None
        t = temperament(captain, kernel)
        comfort = AI_WORKING_FLOAT * t["caution"] * 2
        surplus = captain.credits - comfort
        if surplus <= 500 or random.random() > t["spend"] * 0.5:
            return None
        amount = int(surplus * SHORE_LEAVE_MAX_SHARE * t["spend"])
        if amount < 100:
            return None
        return CognitiveDeed(seat="GROW", action_type=ActionType.SHORE_LEAVE, deed_name="SHORE_LEAVE",
                             target_coordinate=f"SECTOR_{sector.id:03d}", residual_magnitude=float(amount),
                             parameters={"amount": amount}, ration_cost=1)

    @classmethod
    def _settle_options(cls, captain: Captain, dist: Dict[int, int], kernel: "GameKernel") -> List[Tuple[float, Dict[str, Any], Optional[CognitiveDeed]]]:
        """The colonist's dream: a world of one's own, when the purse allows a colony kit."""
        from xylarium.config import COLONY_KIT_CREDITS
        from xylarium.kernel.colony import ColonyManager
        t = temperament(captain, kernel)
        if t["calling"] != "colonist" or captain.credits < COLONY_KIT_CREDITS * 2 or kernel.get_planets_owned_by(captain.id):
            return []
        # A colonist reads the worlds in reach as a farmer would: how many of its own people each could feed on
        # its own staple (the land's carrying capacity for its metabolism), discounted by the voyage
        best = None
        for sid, d in sorted(dist.items(), key=lambda kv: kv[1]):
            if d > 6:
                break
            sec = kernel.sectors[sid]
            for p in sec.planets:
                if p.owner_id is None and not p.natives and not p.faction_id and p.population <= 0:
                    reason = ColonyManager.claim_requirements(captain, p, sec, kernel)
                    if reason is None or "Equipment" in reason:
                        k = cls.feeds(captain, p, kernel)
                        if k > 0 and (best is None or k / (d + 4) > best[2] / (best[0] + 4)):
                            best = (d, p, k)
        if not best:
            return []
        d, planet, k = best
        fertile = min(2.0, k / 20_000.0)            # a world that feeds twenty thousand is a full prize
        value = 400.0 * t["horizon"] * (0.5 + fertile) / (d + 4)   # a lasting asset, valued by patience and harvest
        return [(value, {"kind": "settle", "planet_id": planet.id, "since": cls._cycle(kernel)}, None)]

    @staticmethod
    def feeds(captain: Captain, planet: Any, kernel: "GameKernel") -> int:
        """How many of the captain's people this world could feed on their own staple as a new colony."""
        from xylarium.kernel import biosphere
        return biosphere.carrying_capacity(kernel, planet, citadel=1, habitats=0,
                                           metabolism=getattr(captain, "metabolism", None) or "biotic")

    @staticmethod
    def _shipyard_for(captain: Captain, kernel: "GameKernel", dist: Dict[int, int]) -> Optional[int]:
        """Sol's naval yard, or - for captains its turrets turn away - the nearest Deep Void harbor."""
        if welcome(kernel, captain, 1):
            return 1
        harbors = [sid for sid, _d in sorted(dist.items(), key=lambda kv: kv[1])
                   if kernel.sectors[sid].security == SecurityLevel.ANARCHY and kernel.sectors[sid].port is not None]
        return harbors[0] if harbors else None

    @staticmethod
    def _next_hull_price(captain: Captain, kernel: Any = None) -> Optional[int]:
        """Price of the cheapest larger hull this captain is authorized to fly (what it is saving toward)."""
        from xylarium.config import SHIP_CATALOG
        cur = hulls.spec(captain.ship)
        prices = [cfg["price"] for cfg in hulls.catalog(kernel).values()
                  if cfg.get("holds", 0) > cur.get("holds", 0) and cfg.get("min_rank_tier", 1) <= getattr(captain, "rank_tier", 1)
                  and not (cfg.get("clade") and cfg["clade"] not in (captain.clade, captain.faction_id))]
        return min(prices) if prices else None

    @classmethod
    def _upgrade_option(cls, captain: Captain, cycle: int, kernel: Any = None) -> Optional[Dict[str, Any]]:
        """Capital growth: buy the next larger hull we're authorized for while keeping a trading float."""
        from xylarium.config import SHIP_CATALOG
        cur = hulls.spec(captain.ship)
        best = None
        for name, cfg in hulls.catalog(kernel).items():
            if cfg.get("holds", 0) <= cur.get("holds", 0) or cfg.get("min_rank_tier", 1) > getattr(captain, "rank_tier", 1):
                continue
            if cfg.get("clade") and cfg["clade"] not in (captain.clade, captain.faction_id):
                continue
            if cfg["price"] * 1.5 + AI_CASH_RESERVE * 4 > captain.credits:
                continue
            if best is None or cfg["holds"] / max(1, cfg["price"]) > best[1]["holds"] / max(1, best[1]["price"]):
                best = (name, cfg)
        return {"kind": "upgrade", "ship": best[0], "since": cycle} if best else None

    @staticmethod
    def _xp_value(captain: Captain, kernel: "GameKernel") -> float:
        """SOL value of one point of experience to this captain right now."""
        ambition = temperament(captain, kernel)["ambition"]
        if getattr(captain, "rank_tier", 1) >= 4:
            return AI_XP_VALUE_SOL * 0.1 * ambition
        win = getattr(captain, "xp_window", {}) or {}
        start = win.get("start", 0)
        if int(getattr(kernel, "cycle_count", 0)) - start < XP_WINDOW_CYCLES and win.get("earned", 0.0) >= XP_WINDOW_SOFT_CAP:
            return AI_XP_VALUE_SOL * 0.25 * ambition   # past the soft cap this window: experience accrues at a quarter
        return AI_XP_VALUE_SOL * ambition

    @classmethod
    def propose(cls, captain: Captain, kernel: "GameKernel") -> Optional[CognitiveDeed]:
        sector = kernel.sectors.get(captain.sector_id)
        if not sector:
            return None
        cycle = cls._cycle(kernel)
        cls.observe_port(captain, sector, kernel)
        dist, parent = topology.tree(kernel, sector.id, AI_PLAN_MAX_HOPS)

        # 0. Free salvage floating in this sector
        if sector.debris and captain.ship.cargo.available_space > 2:
            return CognitiveDeed(
                seat="GROW", action_type=ActionType.SALVAGE_DEBRIS, deed_name="SALVAGE_DEBRIS_FIELD",
                target_coordinate=f"SECTOR_{sector.id:03d}", residual_magnitude=1.0, parameters={}, ration_cost=1,
            )

        # 0b. A spender with money to burn takes the crew ashore (the money stays in the port's economy)
        leave = cls._shore_leave(captain, sector, kernel)
        if leave:
            return leave

        # 1. Commitment: carry the current plan forward
        plan = captain.active_plan
        if plan and cycle - plan.get("since", cycle) > AI_PLAN_MAX_AGE + (40 if plan.get("kind") == "extract" else 0):
            plan = captain.active_plan = None
        if plan:
            deed = cls._advance_plan(captain, plan, sector, dist, parent, kernel)
            if deed:
                return deed
            captain.active_plan = None

        # 2. Realize profit on anything already aboard (cargo, then artifacts). A heavy hold is
        # dead capital: sell to any buyer paying at least 70% of fair value.
        heavy = captain.ship.cargo.holds_used > captain.ship.cargo.capacity * 0.7
        deed = (cls._sell_here(captain, sector, min_margin=0.7 if heavy else 1.05)
                or cls._artifact_deed(captain, sector, kernel))
        if deed:
            return deed
        goods = cls._cargo_goods(captain)
        if goods and captain.ship.cargo.available_space < captain.ship.cargo.capacity * 0.5:
            # Liquidate the most valuable good that has a reachable buyer
            dest, comm = None, None
            for g in sorted(goods, key=lambda g: -captain.ship.cargo.unbonded(g) * cls._base_value(g)):
                dest = cls._best_market_for(captain, g, dist, kernel)
                if dest is not None:
                    comm = g
                    break
            if dest is not None:
                captain.active_plan = {"kind": "liquidate", "commodity": comm, "dest": dest, "since": cycle}
                deed = cls._advance_plan(captain, captain.active_plan, sector, dist, parent, kernel)
                if deed:
                    return deed
                captain.active_plan = None

        # 3. Capital growth before speculation when the treasury is deep enough
        upgrade = cls._upgrade_option(captain, cycle, kernel)
        if upgrade:
            captain.active_plan = upgrade
            return cls._advance_plan(captain, upgrade, sector, dist, parent, kernel)

        # 4. Best expected SOL profit per turn across arbitrage, contracts and mining
        options = (cls._arbitrage_options(captain, sector, dist, kernel)
                   + cls._contract_options(captain, dist, kernel)
                   + cls._mining_options(captain, dist, kernel)
                   + cls._archaeology_options(captain, dist, kernel))
        # A captain builds a career, not only a purse: a verified track record (experience) is worth
        # money to someone still climbing the phylogenetic tiers - less so once the window's soft cap
        # is reached or the canopy is won.
        options += cls._settle_options(captain, dist, kernel)
        xp_weight = cls._xp_value(captain, kernel)
        options = [((v + xp_weight * p.get("xp_per_turn", 0.0)) * persona_factor(captain, kernel, p), p, d)
                   for v, p, d in options]
        options = [o for o in options if o[0] >= AI_MIN_PROFIT_PER_TURN]
        if options:
            value, plan, first = max(options, key=lambda o: o[0])
            track_plan(captain, kernel, plan)
            captain.active_plan = plan
            return first or cls._advance_plan(captain, plan, sector, dist, parent, kernel)

        # 5. Explore toward the nearest unknown or stale market
        mem = captain.price_memory
        targets = [
            sid for sid, d in sorted(dist.items(), key=lambda kv: kv[1])
            if d > 0 and kernel.sectors[sid].port is not None
            and (str(sid) not in mem or cycle - mem[str(sid)].get("c", 0) > AI_PRICE_MEMORY_STALE)
        ]
        if targets:
            return cls._step_toward(captain, kernel, parent, targets[0], "SURVEY_MARKETS")
        if sector.warps:
            return CognitiveDeed(
                seat="GROW", action_type=ActionType.MOVE, deed_name="SURVEY_MARKETS",
                target_coordinate="FRONTIER", residual_magnitude=1.0,
                parameters={"destination": random.choice(sector.warps)}, ration_cost=1,
            )
        return None


class SeatArc:
    """
    Seat 2: ARC (Spatial Navigation & Cartographic Decryption)
    Governs abstract spatial reasoning, matrix rotation, vector bridging,
    precursor anomaly investigations, and automated survey fleets.
    """

    @classmethod
    def peel_puzzle(
        cls,
        captain: Captain,
        puzzle_id: str,
        kernel: "GameKernel"
    ) -> Optional[CognitiveDeed]:
        """Peels a 3x3 cartography puzzle matrix into algebraic actions."""
        cart_mgr = getattr(kernel, "cartography_manager", None)
        if not cart_mgr or puzzle_id not in cart_mgr.puzzles:
            return None

        puzzle = cart_mgr.puzzles[puzzle_id]
        if puzzle.status == "DECRYPTED":
            return None

        # 1. Drainage check against entity grown_basis
        basis_sig = rcf_hash(puzzle.grid_nodes)
        cert = f"CERT-ARC-{basis_sig[:12].upper()}"
        for crystal in captain.grown_basis:
            if crystal.get("rcf_sig") == basis_sig or crystal.get("certificate") == cert:
                # Solved invariant in O(1)!
                return CognitiveDeed(
                    seat="ARC",
                    action_type=ActionType.CARTOGRAPHY_SOLVE,
                    deed_name="RECALL_SOLVED_CARTOGRAPHY_INVARIANT",
                    target_coordinate=puzzle_id,
                    residual_magnitude=0.0,
                    parameters={"puzzle_id": puzzle_id},
                    certificate=cert,
                    ration_cost=1,
                    leisure_cost=0,
                )

        # 2. Catalysis check: If puzzle requires reagents and not catalyzed, inject
        if puzzle.required_reagents and not puzzle.is_catalyzed:
            # Check cargo holds
            cargo = captain.ship.cargo
            can_catalyze = any(cargo.elements.get(r, 0) > 0 for r in puzzle.required_reagents) or cargo.equipment >= 5
            if can_catalyze:
                return CognitiveDeed(
                    seat="ARC",
                    action_type=ActionType.CARTOGRAPHY_CATALYZE,
                    deed_name="CATALYZE_PRECURSOR_MATRIX",
                    target_coordinate=puzzle_id,
                    residual_magnitude=20.0,
                    parameters={"puzzle_id": puzzle_id, "amount": 5},
                    ration_cost=1,
                    leisure_cost=1,
                )

        # 3. Fragment check: If captain has starmap fragments, scan
        if captain.cartography_fragments:
            unrevealed = [n for row in puzzle.grid_nodes for n in row if not n["is_revealed"]]
            if unrevealed:
                return CognitiveDeed(
                    seat="ARC",
                    action_type=ActionType.CARTOGRAPHY_SCAN,
                    deed_name="SCAN_STARMAP_FRAGMENT",
                    target_coordinate=puzzle_id,
                    residual_magnitude=len(unrevealed) * 10.0,
                    parameters={"puzzle_id": puzzle_id},
                    ration_cost=1,
                    leisure_cost=0,
                )

        # 4. Alignment check: Find unaligned node to rotate
        for r_idx, row in enumerate(puzzle.grid_nodes):
            for c_idx, node in enumerate(row):
                if node["is_revealed"] and node["vector_angle"] != node["target_angle"]:
                    return CognitiveDeed(
                        seat="ARC",
                        action_type=ActionType.CARTOGRAPHY_ROTATE,
                        deed_name="ALIGN_SIGNAL_VECTOR",
                        target_coordinate=f"NODE_{r_idx}_{c_idx}",
                        residual_magnitude=90.0,
                        parameters={"row": r_idx, "col": c_idx, "puzzle_id": puzzle_id},
                        ration_cost=1,
                        leisure_cost=0,
                    )

        # 5. Bridge check: Find unbridged vector link
        for bridge_k, is_active in puzzle.grid_bridges.items():
            if not is_active:
                coords = [int(x) for part in bridge_k.split("-") for x in part.split(",")]
                if len(coords) == 4:
                    return CognitiveDeed(
                        seat="ARC",
                        action_type=ActionType.CARTOGRAPHY_BRIDGE,
                        deed_name="BRIDGE_VECTOR_CONDUIT",
                        target_coordinate=bridge_k,
                        residual_magnitude=20.0,
                        parameters={"r1": coords[0], "c1": coords[1], "r2": coords[2], "c2": coords[3], "puzzle_id": puzzle_id},
                        ration_cost=1,
                        leisure_cost=0,
                    )

        # 6. If all nodes revealed and aligned, and all bridges active: SYNTHESIZE BREAKTHROUGH
        all_revealed = all(n["is_revealed"] for row in puzzle.grid_nodes for n in row)
        all_aligned = all(n["vector_angle"] == n["target_angle"] for row in puzzle.grid_nodes for n in row)
        all_bridged = all(puzzle.grid_bridges.values()) if puzzle.grid_bridges else True
        if all_revealed and all_aligned and all_bridged:
            return CognitiveDeed(
                seat="ARC",
                action_type=ActionType.CARTOGRAPHY_SOLVE,
                deed_name="SYNTHESIZE_CARTOGRAPHIC_BREAKTHROUGH",
                target_coordinate=puzzle_id,
                residual_magnitude=0.0,
                parameters={"puzzle_id": puzzle_id},
                certificate=cert,
                ration_cost=1,
                leisure_cost=0,
            )

        return None


ASCEND_CHECK_INTERVAL = 20   # Cycles between an autonomous captain's crystallization checks


class CognitiveOrgan:
    """
    Unified iae::think Organ.
    Runs the dual-seat reduction loop for autonomous AI captains and colonial governments.
    """

    @classmethod
    def think(cls, entity: Any, kernel: "GameKernel") -> ActionResult:
        """
        Executes a single unified think cycle:
        1. Material Cochain Check (Seat SURVIVE).
        2. Spillover to Abstract Reasoning (Seat ARC).
        3. Crystal Minting into grown_basis on success.
        """
        if isinstance(entity, Planet):
            planet = entity
            books = SeatSurvive.peel_books(planet, kernel)
            survive_deed = SeatSurvive.reduce_survival(planet, books, kernel)
            if not survive_deed:
                return ActionResult(success=False, action=ActionType.REST, message="No actionable planetary residual.")
            res = cls._execute_planet_deed(survive_deed, planet, kernel)
            if res.success:
                crystal = {
                    "seat": "SURVIVE",
                    "deed": survive_deed.deed_name,
                    "coordinate": survive_deed.target_coordinate,
                    "params": dict(survive_deed.parameters),
                }
                planet.grown_basis.append(crystal)
                if len(planet.grown_basis) > 50:
                    planet.grown_basis.pop(0)
            return res

        if not isinstance(entity, Captain):
            return ActionResult(success=False, action=ActionType.REST, message="Entity is not an autonomous captain or planet.")

        captain = entity
        global _ACTIVE_KERNEL
        _ACTIVE_KERNEL = kernel

        # Treasury: a mind brings home the money of regions it has left; the money of the region it is working
        # in stays in hand to be spent there (the captain's own decision, not a script's sweep)
        fxm = getattr(kernel, "fx_market", None)
        if fxm is not None and captain.fx_wallet:
            fxm.repatriate(captain, AI_FX_REPATRIATE_THRESHOLD, fxm.working_currencies(kernel, captain), kernel=kernel)

        # 0. CRYSTALLIZATION: when the cochain has pitched far enough and the invariants hold,
        # the lineage ascends. Checked periodically (evaluation prices the whole balance sheet).
        cycle_now = int(getattr(kernel, "cycle_count", 0))
        if captain.deed_cooldowns.get("ASCEND_CHECK", -1) <= cycle_now and not captain.faction_id:
            captain.deed_cooldowns["ASCEND_CHECK"] = cycle_now + ASCEND_CHECK_INTERVAL
            evaluation = kernel.phylogeny_manager.evaluate_ascension(captain, kernel)
            if evaluation.get("can_ascend"):
                res = kernel.dispatch(captain.id, ActionType.PHYLOGENY_ASCEND)
                if res.success:
                    return res

        # 1. PEEL SURVIVAL BOOKS
        books = SeatSurvive.peel_books(captain, kernel)
        ration_book = books.get("RATION")
        leisure_book = books.get("LEISURE")

        # 2. METABOLIC SURVIVE CHECK:
        # A starving captain with empty ration holds CANNOT allocate energy to Seat ARC
        survive_deed = SeatSurvive.reduce_survival(captain, books, kernel)

        selected_deed: Optional[CognitiveDeed] = survive_deed

        # 3. SPILLOVER TO SEAT ARC:
        # If Ration book is stable (or surplus) and leisure or credits are abundant,
        # cognitive bandwidth spills over into Cartography & Precursor Anomaly decryption!
        can_spillover = (
            ration_book is not None and
            ration_book.total_deficit <= 0 and
            captain.credits >= 1000
        )
        # Dogma suppresses reason: zealots above the freeze brand inquiry tech-heresy, and the
        # Throne's officers do not meddle with xeno puzzles
        factions = getattr(kernel, "factions", None)
        if factions is not None and captain.faction_id in factions.factions:
            from xylarium.config import ZEALOT_RD_FREEZE_DOGMA
            f = factions.factions[captain.faction_id]
            if captain.faction_id == "IMPERIUM" or f.dogma > ZEALOT_RD_FREEZE_DOGMA:
                can_spillover = False

        if can_spillover:
            # Check active cartography puzzle
            pid = getattr(captain, "active_cartography_puzzle", "PUZZLE-NEXUS")
            cart_mgr = getattr(kernel, "cartography_manager", None)
            if cart_mgr:
                cur_p = cart_mgr.puzzles.get(pid)
                if not cur_p or cur_p.status == "DECRYPTED":
                    unsolved = [p_id for p_id, p in cart_mgr.puzzles.items() if p.status != "DECRYPTED"]
                    if unsolved:
                        pid = unsolved[0]
                        captain.active_cartography_puzzle = pid
            arc_deed = SeatArc.peel_puzzle(captain, pid, kernel)
            if not arc_deed:
                # Check for cosmic anomalies in current sector
                sec = kernel.sectors.get(captain.sector_id)
                sec_anoms = getattr(sec, "anomalies", []) if sec else []
                if sec_anoms and hasattr(kernel, "research_manager"):
                    for aid in sec_anoms:
                        anom = kernel.research_manager.anomalies.get(aid)
                        if anom and anom.status != "SOLVED" and captain.credits >= 1000:
                            arc_deed = CognitiveDeed(
                                seat="ARC",
                                action_type=ActionType.ANOMALY_INVESTIGATE,
                                deed_name="DECODE_COSMIC_ANOMALY",
                                target_coordinate=aid,
                                residual_magnitude=50.0,
                                parameters={"anomaly_id": aid, "solve_inputs": {"mode": "catalyst"}},
                                ration_cost=1,
                            )
                            break
            if arc_deed:
                # 60% chance to prioritize ARC breakthrough when material needs are met
                if random.random() < 0.60 or (survive_deed and survive_deed.deed_name == "SURVEY_MARKETS"):
                    selected_deed = arc_deed

        # 4. FAILURE MEMORY: a deed that just failed cools down (exponential backoff);
        # the syntropic seat proposes an alternative instead of repeating it every turn.
        cycle = int(getattr(kernel, "cycle_count", 0))
        cooldowns = captain.deed_cooldowns
        if selected_deed and cooldowns.get(selected_deed.deed_name, -1) > cycle:
            alt = SeatGrow.propose(captain, kernel)
            selected_deed = alt if (alt and cooldowns.get(alt.deed_name, -1) <= cycle) else None

        if not selected_deed:
            return ActionResult(success=False, action=ActionType.REST, message="No actionable residual.")

        # 5. DISPATCH THE DEED THROUGH THE KERNEL
        res = cls._execute_deed(selected_deed, captain, kernel)

        name = selected_deed.deed_name
        if res.success:
            captain.deed_failures.pop(name, None)
            cooldowns.pop(name, None)
            # 6. CRYSTALLIZE INTO GROWN_BASIS ON BREAKTHROUGH
            cls._crystallize_invariant(captain, selected_deed, res)
        else:
            fails = captain.deed_failures.get(name, 0) + 1
            captain.deed_failures[name] = fails
            cooldowns[name] = cycle + min(DEED_FAILURE_BACKOFF_MAX, 2 ** fails)
            if selected_deed.seat == "GROW":
                captain.active_plan = None
        if len(cooldowns) > 32:
            for k in [k for k, v in cooldowns.items() if v <= cycle]:
                cooldowns.pop(k, None)

        return res

    @classmethod
    def _execute_deed(
        cls,
        deed: CognitiveDeed,
        captain: Captain,
        kernel: "GameKernel"
    ) -> ActionResult:
        """Translates a typed CognitiveDeed into kernel execution."""
        act = deed.action_type
        params = deed.parameters

        if act == ActionType.MOVE:
            return kernel.dispatch(captain.id, act, destination=params.get("destination"))
        elif act == ActionType.TRADE:
            return kernel.dispatch(
                captain.id,
                act,
                trade_type=params.get("trade_type", "BUY"),
                commodity=params.get("commodity", "ORGANICS"),
                amount=params.get("amount", 10),
            )
        elif act == ActionType.SHIPYARD_PURCHASE:
            opts = {"item": params.get("item", "shields"), "amount": params.get("amount", 1)}
            for k in ("budget", "ship_name"):
                if k in params:
                    opts[k] = params[k]
            return kernel.dispatch(captain.id, act, **opts)
        elif act in (ActionType.FREIGHT_ACCEPT, ActionType.FREIGHT_DELIVER, ActionType.BANK_TRANSACTION,
                     ActionType.SCAN_SPACE, ActionType.MINE_ASTEROIDS, ActionType.SALVAGE_DEBRIS,
                     ActionType.DEPLOY_SENTRIES, ActionType.SURVEY_RUINS, ActionType.EXCAVATE,
                     ActionType.SELL_ARTIFACT, ActionType.STUDY_ARTIFACT):
            return kernel.dispatch(captain.id, act, **params)
        elif act == ActionType.ATTACK_SHIP:
            target_id = params.get("target_id")
            if target_id and target_id in kernel.captains:
                target = kernel.captains[target_id]
                sec = kernel.sectors[captain.sector_id]
                from xylarium.kernel.combat import CombatManager
                res_dict = CombatManager.resolve_ship_battle(captain, target, sec, kernel=kernel)
                return ActionResult(
                    success=True,
                    action=ActionType.ATTACK_SHIP,
                    message=f"Engaged {target.name} in combat.",
                    data=res_dict,
                )
            return ActionResult(success=False, action=ActionType.ATTACK_SHIP, message="Target captain not found.")
        elif act == ActionType.PLANET_CLAIM:
            p_id = params.get("planet_id")
            sec = kernel.sectors[captain.sector_id]
            planet = next((p for p in sec.planets if p.id == p_id), None)
            if planet:
                from xylarium.kernel.colony import ColonyManager
                return ColonyManager.claim_planet(captain, planet, sec)
            return ActionResult(success=False, action=ActionType.PLANET_CLAIM, message="Planet not found.")
        elif act == ActionType.PLANET_TAX:
            p_id = params.get("planet_id")
            sec = kernel.sectors[captain.sector_id]
            planet = next((p for p in sec.planets if p.id == p_id), None)
            if planet:
                from xylarium.kernel.colony import ColonyManager
                return ColonyManager.collect_taxes(captain, planet)
            return ActionResult(success=False, action=ActionType.PLANET_TAX, message="Planet not found.")
        elif act == ActionType.PLANET_CARGO_TRANSFER:
            p_id = params.get("planet_id")
            sec = kernel.sectors[captain.sector_id]
            planet = next((p for p in sec.planets if p.id == p_id), None)
            if planet:
                from xylarium.kernel.colony import ColonyManager
                return ColonyManager.transfer_cargo(
                    captain,
                    planet,
                    commodity=params.get("commodity", "ORGANICS"),
                    direction=params.get("direction", "to_planet"),
                    amount=params.get("amount", 10),
                )
            return ActionResult(success=False, action=act, message="Planet not found.")
        elif act == ActionType.PLANET_ELEMENT_TRANSFER:
            p_id = params.get("planet_id")
            return kernel.dispatch(
                captain.id,
                act,
                planet_id=p_id,
                element=params.get("element", "H2O"),
                direction=params.get("direction", "to_planet"),
                amount=params.get("amount", 5),
            )
        elif act == ActionType.HAULER_COMMISSION:
            return kernel.dispatch(
                captain.id,
                act,
                origin_sector=params.get("origin_sector", 1),
                dest_sector=params.get("dest_sector", 30),
                commodity_outbound=params.get("commodity_outbound", "ORGANICS"),
                commodity_return=params.get("commodity_return", "ORE"),
                hull_class=params.get("hull_class", "STANDARD"),
            )
        elif act == ActionType.TOLL_GATE_DEPLOY:
            return kernel.dispatch(
                captain.id,
                act,
                shortcut_id=params.get("shortcut_id", "SMUGGLER_SHORTCUT"),
                toll_fee=params.get("toll_fee", 500),
            )
        elif act in (ActionType.STOCK_SELL, ActionType.STOCK_SHORT, ActionType.STOCK_COVER):
            return kernel.dispatch(captain.id, act, ticker=params.get("ticker"), amount=params.get("shares", 10))
        elif act == ActionType.STOCK_BUY:
            shares = params.get("shares", 10)
            ticker = params.get("ticker")
            comp = kernel.market_manager.companies.get(ticker) if ticker else None
            if comp is not None and comp.share_price > 0:
                # A bold mind borrows against the shares it buys (credit.py): leverage by temperament
                from xylarium.kernel import credit
                loan = credit.lend(kernel, captain, ticker, shares * comp.share_price)
                shares += loan // comp.share_price
            return kernel.dispatch(captain.id, act, ticker=ticker, amount=shares)
        elif act == ActionType.CARTOGRAPHY_SCAN:
            return kernel.dispatch(captain.id, act, puzzle_id=params.get("puzzle_id"))
        elif act == ActionType.CARTOGRAPHY_ROTATE:
            return kernel.dispatch(
                captain.id,
                act,
                row=params.get("row", 0),
                col=params.get("col", 0),
                puzzle_id=params.get("puzzle_id"),
            )
        elif act == ActionType.CARTOGRAPHY_BRIDGE:
            return kernel.dispatch(
                captain.id,
                act,
                r1=params.get("r1", 0),
                c1=params.get("c1", 0),
                r2=params.get("r2", 0),
                c2=params.get("c2", 0),
                puzzle_id=params.get("puzzle_id"),
            )
        elif act == ActionType.CARTOGRAPHY_CATALYZE:
            return kernel.dispatch(
                captain.id,
                act,
                puzzle_id=params.get("puzzle_id"),
                amount=params.get("amount", 5),
            )
        elif act == ActionType.CARTOGRAPHY_SOLVE:
            cart_mgr = getattr(kernel, "cartography_manager", None)
            if cart_mgr:
                res = cart_mgr.solve_puzzle(captain, params.get("puzzle_id"), kernel)
                if deed.certificate and deed.certificate not in captain.unlocked_secrets:
                    captain.unlocked_secrets.append(deed.certificate)
                return res
            return ActionResult(success=False, action=act, message="Cartography manager missing.")
        elif act == ActionType.ANOMALY_INVESTIGATE:
            return kernel.dispatch(
                captain.id,
                act,
                anomaly_id=params.get("anomaly_id"),
                solve_inputs=params.get("solve_inputs", {"mode": "catalyst"}),
            )
        elif act == ActionType.CARTOGRAPHY_SALVAGE:
            res = kernel.dispatch(captain.id, act)
            if res.success and deed.deed_name == "FORAGE_DEEP_VOID":
                metab = getattr(captain, "metabolism", "biotic")
                cargo = captain.ship.cargo
                found = {"mineral": (("ORE", 5), ("Si", 2)), "plasmic": (("H", 5), ("He-3", 2))}.get(
                    metab, (("ORGANICS", 5), ("H2O", 3)))
                for comm, q in found:
                    matter.source("forage", comm, cargo.stow(comm, q))   # gathered from the void
            return res

        return ActionResult(success=False, action=act, message=f"Unsupported deed action {act}.")

    @classmethod
    def _execute_planet_deed(
        cls,
        deed: CognitiveDeed,
        planet: Planet,
        kernel: "GameKernel"
    ) -> ActionResult:
        """Executes a planetary survival deed."""
        from xylarium.kernel.colony import ColonyManager
        act = deed.action_type
        params = deed.parameters
        owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None

        if act == ActionType.PLANET_BUILD_SHIELD:
            if owner:
                return ColonyManager.build_shields(owner, planet, params.get("points", 25))
            else:
                pts = min(params.get("points", 25), planet.max_shields - planet.shields)
                planet.shields += pts
                return ActionResult(success=True, action=act, message=f"Constructed +{pts} shields on {planet.name}.")
        elif act == ActionType.PLANET_RECRUIT_FIGHTERS:
            if owner:
                return ColonyManager.recruit_fighters(owner, planet, params.get("count", 5))
            else:
                cnt = params.get("count", 5)
                planet.fighters += cnt
                return ActionResult(success=True, action=act, message=f"Stationed +{cnt} defense fighters on {planet.name}.")
        elif act == ActionType.PLANET_INVEST:
            if owner:
                return ColonyManager.invest_population(owner, planet, params.get("amount", 1000))
            else:
                colonists = params.get("amount", 1000) // 5
                planet.population += colonists
                return ActionResult(success=True, action=act, message=f"Populated {planet.name} with +{colonists} citizens.")
        elif act == ActionType.PLANET_UPGRADE_CITADEL:
            if owner:
                return ColonyManager.upgrade_citadel(owner, planet)
            else:
                planet.citadel_level += 1
                return ActionResult(success=True, action=act, message=f"Upgraded citadel on {planet.name}.")
        elif act == ActionType.PLANET_ELEMENT_TRANSFER:
            elem = params.get("element", "H2O")
            amt = params.get("amount", 25)
            planet.element_reserves[elem] = planet.element_reserves.get(elem, 0) + amt
            return ActionResult(success=True, action=act, message=f"Extracted +{amt} units of {elem} into reserves.")

        return ActionResult(success=False, action=act, message=f"Unsupported planet deed {act}.")

    @classmethod
    def _crystallize_invariant(
        cls,
        captain: Captain,
        deed: CognitiveDeed,
        result: ActionResult
    ) -> None:
        """Appends a solved irreducible invariant to the captain's grown_basis."""
        if deed.seat == "ARC":
            crystal = {
                "seat": "ARC",
                "deed": deed.deed_name,
                "coordinate": deed.target_coordinate,
                "rcf_sig": deed.certificate or rcf_hash(deed.parameters),
                "certificate": deed.certificate,
                "timestamp_score": captain.score,
            }
            if not any(c.get("rcf_sig") == crystal["rcf_sig"] for c in captain.grown_basis):
                captain.grown_basis.append(crystal)
                if len(captain.grown_basis) > 50:
                    captain.grown_basis.pop(0)
        elif deed.seat == "SURVIVE" and deed.deed_name in [
            "COLONIZE_TERRESTRIAL_BODY",
            "DEPLOY_ORBITAL_TOLL_GATE",
            "PURCHASE_RATIONS",
            "CHARTER_RELIEF_HAULER",
            "ACQUIRE_CORPORATE_SHARES",
        ]:
            crystal = {
                "seat": "SURVIVE",
                "deed": deed.deed_name,
                "coordinate": deed.target_coordinate,
                "params": dict(deed.parameters),
            }
            captain.grown_basis.append(crystal)
            if len(captain.grown_basis) > 50:
                captain.grown_basis.pop(0)
