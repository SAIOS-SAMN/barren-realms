"""
Interstellar Securities & Stock Exchange (ISSE) and Galactic Freight Haulage Engine.
Governs corporate enterprise founding by colony populations, stock equity trading,
quarterly dividend distributions, and population-listed star trade freight contracts.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import random
from xylarium.kernel import hulls
from xylarium.kernel import matter, topology
from xylarium.kernel.models import TradeHauler, Captain, Ship, CargoHold, AIPersonality
from xylarium.config import (
    LUXURY_WANT_PER_THOUSAND,
    COMMODITY_CONFIG,
    SPECIALIZED_HULLS,
    VC_SYNDICATES,
    SHIP_CATALOG,
    CORPORATE_ENFORCER_TREASURY,
    CORPORATE_ENFORCER_COST,
    CORPORATE_ENFORCER_COOLDOWN,
    TAKEOVER_MIN_CREDIT,
    TAKEOVER_MIN_EXP,
    SHORT_MIN_CREDIT,
    CREDIT_TIER_THRESHOLDS,
    CITADEL_UPKEEP,
    COLONY_IMPORT_MIN_VAULT,
    COLONY_IMPORT_MAX_OPEN,
    COLONY_IMPORT_UNIT_PREMIUM,
    COLONY_IMPORT_HOP_FEE,
    FREIGHT_ESCROW_MIN_COMPANY_TREASURY,
    EXTRACTION_SEARCH_HOPS,
    EXTRACTION_MAX_OPEN_PER_COLONY,
    EXTRACTION_AMOUNT_RANGE,
    EXTRACTION_UNIT_PREMIUM,
    EXTRACTION_HOP_FEE,
    EXTRACTION_EXPIRY,
    METABOLIC_DEMAND,
    PORT_CONSUMER_SPEND_RATE,
    PORT_CONSUMER_SPEND_CAP,
    COMPANY_OPEX_RATE,
    PORT_OPEX_RATE,
    FX_PRICE_PASS_THROUGH,
    PORT_OPEX_FLOOR,
    PORT_START_TREASURY,
    STARDOCK_START_TREASURY,
    COMPANY_OPEX_RESERVE,
    PRICE_LEVEL,
    COMPANY_COLONY_SALES_RATE,
    COMPANY_COLONY_SALES_CAP,
    TRADE_COUNCIL_SUBSIDY,
    XP_FREIGHT_BASE,
    XP_FREIGHT_MAX,
    VC_EQUITY_MULTIPLE,
    VC_REVENUE_MULTIPLE,
    VC_RANK_CEILING,
    VC_MIN_PRINCIPAL,
    get_commodity_stack_multiplier,
)
from xylarium.kernel.experience import ExperienceManager

# Fiscal quarter interval in universal cycles
FISCAL_QUARTER_CYCLES: int = 25

# Settled (completed/expired) freight contracts are dropped this many cycles after expiry
CONTRACT_RETENTION_CYCLES = 50
# Per-captain automated hauler fleet cap; hauler ticks pathfind every cycle, so fleets must stay bounded
MAX_TRADE_HAULERS_PER_CAPTAIN = 12
PRICE_HISTORY_RETENTION = 100
RESOLUTION_HISTORY_RETENTION = 50


@dataclass
class SalesExecutive:
    """Represents a corporate sales executive dispatched along star trade lanes to capture market share."""
    id: str
    company_ticker: str
    owner_id: str
    name: str
    sector_id: int
    salary: int = 500
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "company_ticker": self.company_ticker,
            "owner_id": self.owner_id,
            "name": self.name,
            "sector_id": self.sector_id,
            "salary": self.salary,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SalesExecutive":
        return cls(
            id=data["id"],
            company_ticker=data["company_ticker"],
            owner_id=data["owner_id"],
            name=data["name"],
            sector_id=data["sector_id"],
            salary=data.get("salary", 500),
            active=data.get("active", True),
        )


@dataclass
class TradeCouncil:
    """Represents the Interstellar Trade Council and regulatory lobbying pool."""
    lobbying_funds: Dict[str, int] = field(default_factory=dict)
    active_resolutions: List[Dict[str, Any]] = field(default_factory=list)
    resolution_history: List[str] = field(default_factory=list)
    session_cycle: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lobbying_funds": dict(self.lobbying_funds),
            "active_resolutions": [dict(r) for r in self.active_resolutions],
            "resolution_history": list(self.resolution_history),
            "session_cycle": self.session_cycle,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradeCouncil":
        return cls(
            lobbying_funds=dict(data.get("lobbying_funds", {})),
            active_resolutions=[dict(r) for r in data.get("active_resolutions", [])],
            resolution_history=list(data.get("resolution_history", [])),
            session_cycle=data.get("session_cycle", 1),
        )


@dataclass
class Company:
    """Represents a publicly listed interstellar corporation or colony enterprise."""
    ticker: str
    name: str
    sector_id: int
    planet_id: str
    planet_name: str
    industry: str          # "MINING", "AGRICULTURE", "MANUFACTURING", "EXOTIC_ELEMENTS", "LOGISTICS"
    founder_id: str
    level: int = 1         # 1: Outpost Workshop, 2: Commercial Firm, 3: Industrial Complex, 4: Megacorp
    share_price: int = 25
    total_shares: int = 10000
    available_shares: int = 4000
    initial_shares: int = 0   # founding share count (caps secondary offerings); 0 = use total at first issue
    treasury: int = 5000
    home_cash: int = 0         # operating books in the home world's money (colony sales in, wages/inputs/dividends out)
    home_currency: str = ""    # that money (set from the home world)
    quarterly_revenue: int = 0
    last_dividend: int = 0
    dividend_rate: float = 0.08  # 8% of quarterly profits paid to shareholders
    price_history: List[int] = field(default_factory=lambda: [25, 25, 25])
    contracts_fulfilled: int = 0
    contracts_failed: int = 0
    chairman_id: Optional[str] = None
    poison_pill_active: bool = False
    poison_pill_uses: int = 1
    embargoed_captains: List[str] = field(default_factory=list)
    special_dividends_paid: int = 0
    market_penetration: Dict[int, float] = field(default_factory=dict)
    consumer_trust: int = 80
    sales_executives: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.chairman_id is None:
            self.chairman_id = self.founder_id
        if not self.market_penetration and self.sector_id:
            self.market_penetration[self.sector_id] = 30.0

    @property
    def market_cap(self) -> int:
        return self.share_price * self.total_shares

    @property
    def level_title(self) -> str:
        titles = {
            1: "Outpost Workshop",
            2: "Commercial Syndicate",
            3: "Industrial Complex",
            4: "Interstellar Megacorp",
        }
        return titles.get(self.level, "Corporate Entity")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "sector_id": self.sector_id,
            "planet_id": self.planet_id,
            "planet_name": self.planet_name,
            "industry": self.industry,
            "founder_id": self.founder_id,
            "chairman_id": self.chairman_id,
            "level": self.level,
            "level_title": self.level_title,
            "share_price": self.share_price,
            "total_shares": self.total_shares,
            "available_shares": self.available_shares,
            "initial_shares": self.initial_shares,
            "treasury": self.treasury,
            "home_cash": self.home_cash,
            "home_currency": self.home_currency,
            "quarterly_revenue": self.quarterly_revenue,
            "last_dividend": self.last_dividend,
            "dividend_rate": self.dividend_rate,
            "price_history": list(self.price_history),
            "contracts_fulfilled": self.contracts_fulfilled,
            "contracts_failed": self.contracts_failed,
            "market_cap": self.market_cap,
            "poison_pill_active": self.poison_pill_active,
            "poison_pill_uses": self.poison_pill_uses,
            "embargoed_captains": list(self.embargoed_captains),
            "special_dividends_paid": self.special_dividends_paid,
            "market_penetration": {str(k): v for k, v in self.market_penetration.items()},
            "consumer_trust": self.consumer_trust,
            "sales_executives": list(self.sales_executives),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Company":
        raw_pen = data.get("market_penetration", {})
        parsed_pen = {int(k): float(v) for k, v in raw_pen.items()}
        return cls(
            ticker=data["ticker"],
            name=data["name"],
            sector_id=data["sector_id"],
            planet_id=data["planet_id"],
            planet_name=data["planet_name"],
            industry=data["industry"],
            founder_id=data["founder_id"],
            level=data.get("level", 1),
            share_price=data.get("share_price", 25),
            total_shares=data.get("total_shares", 10000),
            available_shares=data.get("available_shares", 4000),
            initial_shares=data.get("initial_shares", 0),
            treasury=data.get("treasury", 5000),
            home_cash=int(data.get("home_cash", 0)),
            home_currency=data.get("home_currency", ""),
            quarterly_revenue=data.get("quarterly_revenue", 0),
            last_dividend=data.get("last_dividend", 0),
            dividend_rate=data.get("dividend_rate", 0.08),
            price_history=list(data.get("price_history", [25, 25, 25])),
            contracts_fulfilled=data.get("contracts_fulfilled", 0),
            contracts_failed=data.get("contracts_failed", 0),
            chairman_id=data.get("chairman_id", data["founder_id"]),
            poison_pill_active=data.get("poison_pill_active", False),
            poison_pill_uses=data.get("poison_pill_uses", 1),
            embargoed_captains=list(data.get("embargoed_captains", [])),
            special_dividends_paid=data.get("special_dividends_paid", 0),
            market_penetration=parsed_pen,
            consumer_trust=data.get("consumer_trust", 80),
            sales_executives=list(data.get("sales_executives", [])),
        )


@dataclass
class FreightContract:
    """Represents a trade contract listed by a colony business to transport goods across stars."""
    id: str
    company_ticker: str
    issuer_name: str
    origin_sector: int
    origin_name: str
    destination_sector: int
    destination_planet_id: str
    destination_name: str
    commodity: str            # "ORE", "ORGANICS", "EQUIPMENT", or periodic elements like "STELALITH"
    amount: int
    payout_credits: int
    shares_reward: int        # Bonus company equity granted upon verified delivery
    hazard_level: str         # "FEDERATION", "BORDERLAND", "ANARCHY"
    created_cycle: int
    expiry_cycle: int
    accepted_by: Optional[str] = None
    status: str = "OPEN"      # "OPEN", "IN_TRANSIT", "COMPLETED", "EXPIRED"
    # Payout is escrowed at posting ("company:TICKER" or "planet:ID") and refunded if voided
    escrow_source: Optional[str] = None
    escrow_amount: int = 0
    currency: str = "SOL"     # Payout currency (issuer's money)
    kind: str = "FREIGHT"     # "FREIGHT": load at origin port; "EXTRACTION": mine it in null space yourself

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "company_ticker": self.company_ticker,
            "escrow_source": self.escrow_source,
            "escrow_amount": self.escrow_amount,
            "currency": self.currency,
            "kind": self.kind,
            "issuer_name": self.issuer_name,
            "origin_sector": self.origin_sector,
            "origin_name": self.origin_name,
            "destination_sector": self.destination_sector,
            "destination_planet_id": self.destination_planet_id,
            "destination_name": self.destination_name,
            "commodity": self.commodity,
            "amount": self.amount,
            "payout_credits": self.payout_credits,
            "shares_reward": self.shares_reward,
            "hazard_level": self.hazard_level,
            "created_cycle": self.created_cycle,
            "expiry_cycle": self.expiry_cycle,
            "accepted_by": self.accepted_by,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FreightContract":
        return cls(
            id=data["id"],
            company_ticker=data["company_ticker"],
            issuer_name=data["issuer_name"],
            origin_sector=data["origin_sector"],
            origin_name=data["origin_name"],
            destination_sector=data["destination_sector"],
            destination_planet_id=data["destination_planet_id"],
            destination_name=data["destination_name"],
            commodity=data["commodity"],
            amount=data["amount"],
            payout_credits=data["payout_credits"],
            shares_reward=data.get("shares_reward", 0),
            hazard_level=data.get("hazard_level", "FEDERATION"),
            created_cycle=data.get("created_cycle", 0),
            expiry_cycle=data.get("expiry_cycle", 50),
            accepted_by=data.get("accepted_by"),
            escrow_source=data.get("escrow_source"),
            escrow_amount=int(data.get("escrow_amount", 0)),
            currency=data.get("currency", "SOL"),
            kind=data.get("kind", "FREIGHT"),
            status=data.get("status", "OPEN"),
        )


_STOCK_KEY = {k.upper(): k for k in COMMODITY_CONFIG}       # warehouse keys are the commodity table's spelling


def ledger_pay(amount: int, sector_id: Optional[int] = None, institution: Optional[str] = None) -> None:
    from xylarium.kernel import ledger
    ledger.pay_service(amount, sector_id, institution)


def kernel_sector_port(sector_id: int) -> Any:
    from xylarium.kernel import ledger
    k = ledger.active_kernel()
    sec = k.sectors.get(sector_id) if k is not None else None
    return sec.port if sec is not None else None


def ledger_sol_of(port: Any) -> int:
    from xylarium.kernel import fx
    if port.currency == "SOL" or fx.ACTIVE_FX is None:
        return int(port.treasury)
    return int(fx.ACTIVE_FX.to_sol_value(port.currency, port.treasury))


def ledger_debit_port_sol(port: Any, sol: int) -> None:
    """Take ``sol`` of value from a port's treasury (a regional port sells local money at the exchange)."""
    from xylarium.kernel import fx
    if sol <= 0:
        return
    if port.currency == "SOL" or fx.ACTIVE_FX is None:
        port.treasury -= sol
        return
    local = min(port.treasury, int(sol * fx.ACTIVE_FX.rate(port.currency) * 1.02) + 1)
    port.treasury -= local
    got = fx.ACTIVE_FX.swap_to_sol(port.currency, local)
    if got > sol:                                            # any excess SOL comes back as local money
        port.treasury += fx.ACTIVE_FX.swap_sol_to(port.currency, got - sol)


class MarketManager:
    """
    Authoritative manager for corporate enterprises, the stock exchange,
    and galactic freight trade listings.
    """

    def __init__(self):
        # Set by the kernel so contract settlement can resolve planets, paths and experience windows
        self._kernel_ref: Any = None
        self.companies: Dict[str, Company] = {}
        self.contracts: Dict[str, FreightContract] = {}
        self.executives: Dict[str, SalesExecutive] = {}
        self.trade_haulers: Dict[str, TradeHauler] = {}
        self.trade_council: TradeCouncil = TradeCouncil()
        self.next_contract_id: int = 101
        self.next_exec_id: int = 101
        self.next_hauler_id: int = 101
        self._initialize_flagship_corporations()

    def _initialize_flagship_corporations(self) -> None:
        """Seed founding interstellar corporations."""
        initial_corps = [
            Company(
                ticker="VOSS",
                name="Voss Heavy Industries",
                sector_id=18,
                planet_id="planet_18",
                planet_name="Aetheria Prime",
                industry="MANUFACTURING",
                founder_id="ai_voss",
                level=3,
                share_price=85,
                total_shares=50000,
                available_shares=15000,
                treasury=250000,
                dividend_rate=0.10,
                price_history=[72, 78, 85],
            ),
            Company(
                ticker="ADME",
                name="Avalon Deep Mantle Mining",
                sector_id=30,
                planet_id="planet_30",
                planet_name="Avalon IV",
                industry="MINING",
                founder_id="colony_population",
                level=2,
                share_price=42,
                total_shares=20000,
                available_shares=8000,
                treasury=45000,
                dividend_rate=0.08,
                price_history=[36, 40, 42],
            ),
            Company(
                ticker="SHBI",
                name="Sanctuary Hydro-Biomes",
                sector_id=78,
                planet_id="planet_78",
                planet_name="Sanctuary",
                industry="AGRICULTURE",
                founder_id="colony_population",
                level=2,
                share_price=38,
                total_shares=20000,
                available_shares=9000,
                treasury=38000,
                dividend_rate=0.07,
                price_history=[32, 35, 38],
            ),
            Company(
                ticker="STLC",
                name="Stillcold Cryo-Synthetics",
                sector_id=91,
                planet_id="planet_91",
                planet_name="Aetheria Prime",
                industry="EXOTIC_ELEMENTS",
                founder_id="colony_population",
                level=2,
                share_price=56,
                total_shares=25000,
                available_shares=10000,
                treasury=60000,
                dividend_rate=0.09,
                price_history=[48, 52, 56],
            ),
            Company(
                ticker="FGFB",
                name="Deepforge Heavy Works",
                sector_id=40,
                planet_id="planet_40",
                planet_name="Xylar-IV",
                industry="MANUFACTURING",
                founder_id="colony_population",
                level=2,
                share_price=45,
                total_shares=20000,
                available_shares=7500,
                treasury=52000,
                dividend_rate=0.08,
                price_history=[40, 43, 45],
            ),
            Company(
                ticker="SLAG",
                name="Cinder Vent Extraction",
                sector_id=74,
                planet_id="planet_74",
                planet_name="Genesis Prime",
                industry="MINING",
                founder_id="colony_population",
                level=1,
                share_price=28,
                total_shares=15000,
                available_shares=6000,
                treasury=22000,
                dividend_rate=0.06,
                price_history=[25, 26, 28],
            ),
        ]
        for c in initial_corps:
            self.companies[c.ticker] = c

    def spawn_population_enterprises(self, kernel: Any) -> List[str]:
        """
        Colonists on worlds with population >= 600 organically form commercial businesses
        matching their local civilization taxon and resource profile.
        """
        created = []
        if kernel.cycle_count > 0:
            return created        # after genesis a business is founded only where it pays (enterprise.py)
        for s_id, sec in kernel.sectors.items():
            for planet in sec.planets:
                # Check if planet already has a company headquartered here
                existing = [c for c in self.companies.values() if c.planet_id == planet.id]
                if existing:
                    continue

                if planet.population >= 600:
                    civ = getattr(planet, "civilization", None)
                    meta = civ.metabolism if civ else "mineral"
                    civ_name = civ.name if civ else planet.name

                    # Determine industry and ticker
                    if meta == "biotic":
                        ind = "AGRICULTURE"
                        prefix = "Bio-Synthetics"
                    elif meta == "plasmic":
                        ind = "MANUFACTURING"
                        prefix = "Coronal Dynamics"
                    elif meta == "umbral":
                        ind = "EXOTIC_ELEMENTS"
                        prefix = "Umbral Works"
                    else:
                        ind = "MINING"
                        prefix = "Lithic Extraction"

                    clean_name = f"{planet.name} {prefix}"
                    # Generate 4-letter unique ticker
                    base_tick = (civ_name[:2] + planet.name[:2]).upper()
                    ticker = base_tick
                    idx = 1
                    while ticker in self.companies:
                        ticker = f"{base_tick[:3]}{idx}"
                        idx += 1

                    # Capitalization: at genesis companies exist already; afterwards the colony's own vault
                    # capitalizes the enterprise, clearing local money into SOL through the ISSE FX desk.
                    capital = random.randint(8000, 20000)
                    if kernel.cycle_count > 0:
                        local_capital = int(capital * self._fx_rate(planet.currency))
                        if planet.treasury < local_capital * 1.5:
                            continue
                        planet.treasury -= local_capital
                        from xylarium.kernel.fx import ACTIVE_FX
                        if planet.currency != "SOL" and ACTIVE_FX is not None:
                            capital = ACTIVE_FX.swap_to_sol(planet.currency, local_capital)
                        else:
                            capital = local_capital

                    founder = planet.owner_id if planet.owner_id else "colony_population"
                    comp = Company(
                        ticker=ticker,
                        name=clean_name,
                        sector_id=s_id,
                        planet_id=planet.id,
                        planet_name=planet.name,
                        industry=ind,
                        founder_id=founder,
                        level=1,
                        share_price=random.randint(18, 32),
                        total_shares=10000,
                        available_shares=4000,
                        treasury=capital,
                        dividend_rate=0.06,
                        price_history=[25],
                    )
                    self.companies[ticker] = comp
                    created.append(f"[{ticker}] {clean_name} incorporated on {planet.name} (Sector {s_id})")

        return created

    def generate_freight_contracts(self, kernel: Any) -> List[FreightContract]:
        """
        Autonomous businesses inspect their commodity needs and post freight contracts
        across the star lanes for independent star captains to haul.
        """
        new_contracts = []
        # Keep open contracts capped at 12
        # The freight board has its own cap: industrial extraction orders (capped per colony) must not
        # crowd out ordinary haulage contracts
        open_count = sum(1 for c in self.contracts.values()
                         if c.status == "OPEN" and getattr(c, "kind", "FREIGHT") != "EXTRACTION")
        if open_count >= 12:
            return []

        active_comps = list(self.companies.values())
        if not active_comps:
            return []

        # Find candidate origin ports / Stardock
        ports = [sec.port for sec in kernel.sectors.values() if sec.port is not None]
        if not ports:
            return []

        needed = min(4, 12 - open_count)
        commodities = ["ORE", "ORGANICS", "EQUIPMENT", "STELALITH", "CHITINIUM", "CRYOGENITE"]
        real_planets = [p for s in kernel.sectors.values() for p in s.planets]
        if not real_planets:
            return []

        for _ in range(needed):
            company = random.choice(active_comps)
            dest_sector = company.sector_id
            dest_planet_id = company.planet_id
            dest_name = company.planet_name

            # Verify destination planet exists in dest_sector; if not, bind to an actual world
            target_planet = None
            if dest_sector in kernel.sectors:
                for p in kernel.sectors[dest_sector].planets:
                    if p.id == dest_planet_id or p.name == dest_name:
                        target_planet = p
                        break
            if not target_planet and real_planets:
                target_planet = random.choice(real_planets)
                dest_sector = target_planet.sector_id
                dest_planet_id = target_planet.id
                dest_name = target_planet.name
                company.sector_id = dest_sector
                company.planet_id = dest_planet_id
                company.planet_name = dest_name

            # Match commodity to industry demand
            if company.industry == "MINING":
                comm = random.choice(["EQUIPMENT", "ORGANICS"])
            elif company.industry == "AGRICULTURE":
                comm = random.choice(["ORE", "EQUIPMENT"])
            elif company.industry == "MANUFACTURING":
                comm = random.choice(["ORE", "STELALITH"])
            else:
                comm = random.choice(commodities)

            # The goods are bought where they are: an origin port (not the destination's) that stocks them
            key = _STOCK_KEY.get(comm.upper(), comm)

            def stocked(p: Any) -> int:
                return p.stock.get(key, 0)
            sources = [p for p in ports if p.sector_id != dest_sector and stocked(p) >= 10]
            if not sources:
                continue
            origin_port = random.choice(sources)

            # Distance via BFS path
            path = kernel.find_path(origin_port.sector_id, dest_sector)
            hops = max(1, len(path) - 1)

            # Security level determines hazard multiplier
            dest_sec = kernel.sectors[dest_sector]
            hazard = dest_sec.security.value
            hazard_mult = 1.0
            if hazard == "BORDERLAND":
                hazard_mult = 1.4
            elif hazard == "ANARCHY":
                hazard_mult = 2.0

            amount = random.randint(10, 25)
            # Payout formula: base 100 Cr/hop + 20 Cr/unit * hazard multiplier
            payout = int((hops * 150 + amount * 35) * hazard_mult)
            # The issuing company escrows the payout from its own treasury (no minted freight wages)
            if company.treasury - payout < FREIGHT_ESCROW_MIN_COMPANY_TREASURY:
                continue
            company.treasury -= payout
            # Shares reward: 10-30 shares of the company
            shares_bonus = random.randint(10, 25)

            cid = f"FRT-{self.next_contract_id}"
            self.next_contract_id += 1

            contract = FreightContract(
                id=cid,
                company_ticker=company.ticker,
                issuer_name=company.name,
                origin_sector=origin_port.sector_id,
                origin_name=origin_port.name,
                destination_sector=dest_sector,
                destination_planet_id=dest_planet_id,
                destination_name=dest_name,
                commodity=comm,
                amount=amount,
                payout_credits=payout,
                shares_reward=shares_bonus,
                hazard_level=hazard,
                created_cycle=kernel.cycle_count,
                expiry_cycle=kernel.cycle_count + 60,
                status="OPEN",
                escrow_source=f"company:{company.ticker}",
                escrow_amount=payout,
            )
            self.contracts[cid] = contract
            new_contracts.append(contract)

        return new_contracts

    def generate_colony_imports(self, kernel: Any) -> List[FreightContract]:
        """
        Colonies are customers: a colony short on food or upkeep ore posts an import
        order paid from its own vault (escrowed), creating hauling income for captains.
        """
        created: List[FreightContract] = []
        open_by_planet: Dict[str, int] = {}
        for c in self.contracts.values():
            if c.status in ("OPEN", "IN_TRANSIT") and (c.escrow_source or "").startswith("planet:"):
                pid = c.escrow_source.split(":", 1)[1]
                open_by_planet[pid] = open_by_planet.get(pid, 0) + 1

        port_sectors = [s for s in kernel.sectors.values() if s.port is not None]
        dist_to = None
        for sec in kernel.sectors.values():
            for planet in sec.planets:
                if planet.population <= 0 or planet.treasury < COLONY_IMPORT_MIN_VAULT:
                    continue
                if not planet.owner_id and not getattr(planet, "civilization", None):
                    continue
                if open_by_planet.get(planet.id, 0) >= COLONY_IMPORT_MAX_OPEN:
                    continue
                needs = []
                food_need = max(1, planet.population // 1000)
                from xylarium.kernel import staples          # a world imports what its people eat
                if staples.stores(kernel, planet) < food_need * 20:
                    needs.append((staples.of(kernel, planet), min(60, max(15, food_need * 5))))
                upkeep_ore = CITADEL_UPKEEP.get(planet.citadel_level, {}).get("ore", 0)
                if upkeep_ore and planet.ore_silo < upkeep_ore * 25:
                    needs.append(("ORE", min(60, max(15, upkeep_ore * 10))))
                for t, unmet_q in (planet.society.get("luxury_unmet_quarters") or {}).items():
                    if unmet_q >= 3 and planet.element_reserves.get(t, 0) < 10:
                        # two seasons of the world's want, in a hauler-sized lot
                        lux_amt = min(30, max(10, int(planet.population / 1000.0 * LUXURY_WANT_PER_THOUSAND * 2)))
                        needs.append((t, lux_amt))
                for comm, amount in needs:
                    if open_by_planet.get(planet.id, 0) >= COLONY_IMPORT_MAX_OPEN:
                        break
                    origins = [
                        ps for ps in port_sectors
                        if ps.id != sec.id and ps.port.sells.get(comm, False) and ps.port.stock.get(comm, 0) >= (min(amount, 10) if comm.startswith("LUX_") else amount)
                    ]
                    if not origins:
                        continue
                    # One reverse breadth-first search from the colony gives every origin's warp distance to it
                    if dist_to is None or dist_to[0] != sec.id:
                        dist_to = (sec.id, topology.distances_to(kernel, sec.id))
                    reachable = [ps for ps in origins if ps.id in dist_to[1]]
                    if not reachable:
                        continue
                    origin_sec = min(reachable, key=lambda ps: dist_to[1][ps.id])
                    hops = max(1, dist_to[1][origin_sec.id])
                    hazard_mult = {"BORDERLAND": 1.3, "ANARCHY": 1.8}.get(sec.security.value, 1.0)
                    base = COMMODITY_CONFIG.get(comm, {}).get("base_price", 20)
                    sol_value = (base * COLONY_IMPORT_UNIT_PREMIUM * amount + hops * COLONY_IMPORT_HOP_FEE) * hazard_mult
                    payout = int(sol_value * self._local_price_level(planet.currency))
                    if planet.treasury - payout < COLONY_IMPORT_MIN_VAULT // 2:
                        continue
                    planet.treasury -= payout
                    cid = f"FRT-{self.next_contract_id}"
                    self.next_contract_id += 1
                    contract = FreightContract(
                        id=cid,
                        company_ticker="COLONY",
                        issuer_name=f"{planet.name} Provisioning Office",
                        origin_sector=origin_sec.id,
                        origin_name=origin_sec.port.name,
                        destination_sector=sec.id,
                        destination_planet_id=planet.id,
                        destination_name=planet.name,
                        commodity=comm,
                        amount=amount,
                        payout_credits=payout,
                        shares_reward=0,
                        hazard_level=sec.security.value,
                        created_cycle=kernel.cycle_count,
                        expiry_cycle=kernel.cycle_count + 60,
                        status="OPEN",
                        escrow_source=f"planet:{planet.id}",
                        escrow_amount=payout,
                        currency=planet.currency,
                    )
                    self.contracts[cid] = contract
                    open_by_planet[planet.id] = open_by_planet.get(planet.id, 0) + 1
                    created.append(contract)
        return created

    @staticmethod
    def _colony_consumer_spending(kernel: Any) -> None:
        """Colonies buy consumer goods from their system's starport: vault -> port treasury, goods consumed."""
        from xylarium.kernel.economy import EconomyManager
        for sec in kernel.sectors.values():
            port = sec.port
            if port is None:
                continue
            for planet in sec.planets:
                if planet.population <= 0 or planet.treasury <= 0 or planet.currency != port.currency:
                    continue
                cap = int(PORT_CONSUMER_SPEND_CAP * PRICE_LEVEL.get(port.currency, 1.0))
                spend = min(int(planet.treasury * PORT_CONSUMER_SPEND_RATE), cap)
                if spend <= 0:
                    continue
                planet.treasury -= spend
                port.treasury += spend
                for comm in ("ORGANICS", "EQUIPMENT"):
                    _, unit = EconomyManager.get_unit_prices(port, comm)
                    if unit > 0:
                        port.stock[comm] = max(0, port.stock.get(comm, 0) - (spend // 2) // unit)

    @staticmethod
    def _regional_worlds(kernel: Any, sector_id: int, currency: str, radius: int) -> List[Any]:
        """Populated worlds within ``radius`` warps of a sector that settle in the same currency."""
        dist = topology.hops(kernel, sector_id, radius)
        return [p for sid in dist for p in kernel.sectors[sid].planets
                if p.population > 0 and p.currency == currency]

    @classmethod
    def _port_retail(cls, kernel: Any) -> None:
        """
        Ports resell what they consume: the region's populated worlds (within a few warps, same money)
        buy the quarter's consumed goods at the port's price plus a retail markup. Money flows from
        colony vaults into the port - the return leg of every captain's sale to that port.
        """
        from xylarium.kernel.economy import EconomyManager
        from xylarium.config import PORT_RETAIL_MARKUP, PORT_RETAIL_RADIUS, PORT_RETAIL_VAULT_SHARE
        for sec in kernel.sectors.values():
            port = sec.port
            if port is None:
                continue
            value = 0
            for comm, units in (port.consumed or {}).items():
                buy_p, _ = EconomyManager.get_unit_prices(port, comm)
                value += units * buy_p
            port.consumed = {}
            bill = int(value * PORT_RETAIL_MARKUP)
            buyers = [p for p in cls._regional_worlds(kernel, sec.id, port.currency, PORT_RETAIL_RADIUS)
                      if p.treasury > 0] if bill > 0 else []
            income = 0
            if bill > 0 and buyers:
                pop = sum(p.population for p in buyers) or 1
                for p in buyers:
                    pay = min(int(bill * p.population / pop), int(p.treasury * PORT_RETAIL_VAULT_SHARE))
                    if pay > 0:
                        p.treasury -= pay
                        port.treasury += pay
                        income += pay
            # What the region actually pays this port is its creditworthiness (smoothed)
            port.regional_income = round(0.7 * port.regional_income + 0.3 * income, 2)

    @staticmethod
    def _port_operating_costs(kernel: Any) -> None:
        """
        Starports pay dockhands, power and suppliers: costs proportional to their cash, paid into the
        region's populated worlds (households and suppliers), who buy from the port again. Only a port
        with nobody living in its region burns its costs (imported power and parts).
        """
        from xylarium.kernel import ledger
        from xylarium.config import PORT_RETAIL_RADIUS
        for sec in kernel.sectors.values():
            port = sec.port
            if port is None:
                continue
            base = (STARDOCK_START_TREASURY if sec.id == 1 else PORT_START_TREASURY) * PRICE_LEVEL.get(port.currency, 1.0)
            excess = port.treasury - int(base * PORT_OPEX_FLOOR)
            cost = int(excess * PORT_OPEX_RATE) if excess > 0 else 0
            if cost <= 0:
                continue
            port.treasury -= cost
            # The starport is government property: a share of its seasonal surplus is paid to its government
            # as dues (a syndicate free port in the Deep Void keeps it all for its region)
            from xylarium.kernel import government
            dues = int(cost * government.PORT_DUES_SHARE)
            if government.pay_government(kernel, sec, port.currency, dues, "starport_dues") != "none":
                cost -= dues
            region = [p for p in MarketManager._regional_worlds(kernel, sec.id, port.currency, PORT_RETAIL_RADIUS)] or \
                     [p for p in sec.planets if p.population > 0 and p.currency == port.currency]
            if not region:
                ledger.burn("port_operations", cost, port.currency)
                continue
            # Dockhands' wages go to the region's households; the rest to its suppliers and governments
            from xylarium.config import PORT_PAYROLL_SHARE
            pop = sum(p.population for p in region) or 1
            paid = 0
            for p in region:
                share = int(cost * p.population / pop)
                wages = int(share * PORT_PAYROLL_SHARE)
                p.household_purse += wages
                p.treasury += share - wages
                paid += share
            region[0].treasury += cost - paid
            if ledger.ACTIVE_POLICY is not None:
                ledger.ACTIVE_POLICY.record_income(port.currency, cost)

    def _company_operating_spend(self, kernel: Any) -> None:
        """
        Companies spend operating budgets (inputs, services, wages) at their home system's
        starport - or Sol Stardock if their system has none. SOL clears into the local
        currency through the ISSE FX desk, recirculating corporate cash into the regions.
        """
        from xylarium.kernel.economy import EconomyManager
        from xylarium.kernel.fx import ACTIVE_FX
        from xylarium.kernel.colony import ColonyManager
        from xylarium.kernel import enterprise
        firms = enterprise.stats(kernel)["firms"]
        from xylarium.kernel import liquidation
        for ticker, comp in self.companies.items():
            if ticker in firms or liquidation.distressed(kernel, ticker):
                continue          # a firm buys, pays and keeps its plant up itself; a distressed one keeps its estate
            # Operating books in the home money: last season's takings are spent at the home region's starport
            home = kernel.get_planet(comp.planet_id) if getattr(comp, "planet_id", None) else None
            if comp.home_cash > 0 and home is not None:
                home_port = ColonyManager._contractor_port(home, kernel)
                if home_port is not None and home_port.currency == comp.home_currency:
                    spend = comp.home_cash
                    comp.home_cash = 0
                    home_port.treasury += spend
                    comp.last_outflow_q = int(ACTIVE_FX.to_sol_value(comp.home_currency, spend)) if (
                        ACTIVE_FX and comp.home_currency != "SOL") else spend
                    self._consume_inputs(home_port, spend)
            budget = int(max(0, comp.treasury - COMPANY_OPEX_RESERVE) * COMPANY_OPEX_RATE)
            comp.last_outflow_q = getattr(comp, "last_outflow_q", 0) + max(0, budget)
            if budget <= 0:
                continue
            sec = kernel.sectors.get(comp.sector_id)
            port = sec.port if (sec is not None and sec.port is not None) else kernel.sectors[1].port
            if port is None:
                continue
            comp.treasury -= budget
            local = ACTIVE_FX.swap_sol_to(port.currency, budget) if (port.currency != "SOL" and ACTIVE_FX) else budget
            port.treasury += local
            self._consume_inputs(port, local)

    @staticmethod
    def _consume_inputs(port: Any, local: int) -> None:
        """What a firm's spending buys at a starport is used up in its work (equipment, ore)."""
        from xylarium.kernel.economy import EconomyManager
        for comm in ("EQUIPMENT", "ORE"):
            _, unit = EconomyManager.get_unit_prices(port, comm)
            if unit > 0:
                used = min(port.stock.get(comm, 0), (local // 2) // unit)
                port.stock[comm] = port.stock.get(comm, 0) - used
                matter.sink("company_inputs", comm, used)

    @staticmethod
    def _local_price_level(currency: str) -> float:
        """What goods cost in local money: genesis price level with damped inflation pass-through.
        Contracts are priced here, never at the live rate, so depreciation can't feed on itself."""
        from xylarium.kernel import prices
        return prices.level(currency)         # MV = PY, sticky (prices.py)

    @staticmethod
    def _fx_rate(currency: str) -> float:
        from xylarium.kernel.fx import ACTIVE_FX
        return ACTIVE_FX.rate(currency) if (ACTIVE_FX is not None and currency != "SOL") else 1.0

    def generate_extraction_contracts(self, kernel: Any) -> List[FreightContract]:
        """
        Algorithmic dispersal of industrial work orders. For every colony, demand is what
        its metabolism and citadel upkeep consume from the periodic table; supply is the
        composition of asteroid belts within EXTRACTION_SEARCH_HOPS of its system. The
        best-supplied demanded element becomes an extraction order (mine it in null space,
        return it to the colony's industrial yard), paid from the colony vault in local money.
        """
        created: List[FreightContract] = []
        open_by_planet: Dict[str, int] = {}
        for c in self.contracts.values():
            if c.kind == "EXTRACTION" and c.status in ("OPEN", "IN_TRANSIT"):
                pid = (c.escrow_source or ":").split(":", 1)[1]
                open_by_planet[pid] = open_by_planet.get(pid, 0) + 1

        for sec in kernel.sectors.values():
            for planet in sec.planets:
                if planet.population <= 0 or planet.treasury < COLONY_IMPORT_MIN_VAULT:
                    continue
                if open_by_planet.get(planet.id, 0) >= EXTRACTION_MAX_OPEN_PER_COLONY:
                    continue
                civ = getattr(planet, "civilization", None)
                metabolism = civ.metabolism if civ else "biotic"
                owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
                if owner is not None:
                    metabolism = getattr(owner, "metabolism", metabolism)
                demand = list(METABOLIC_DEMAND.get(metabolism, ["H2O"]))
                if CITADEL_UPKEEP.get(planet.citadel_level, {}).get("ore", 0):
                    demand.append("ORE")
                demand = [e for e in demand if planet.element_reserves.get(e, 0) < 60 or e == "ORE" and planet.ore_silo < 200]
                if not demand:
                    continue

                # Supply: belts within reach, weighted by composition share x remaining reserve / distance
                dist = topology.hops(kernel, sec.id, EXTRACTION_SEARCH_HOPS)
                best = None
                for s_id, d in dist.items():
                    for belt in kernel.sectors[s_id].belts:
                        for elem in demand:
                            share = belt["composition"].get(elem, 0.0)
                            if share <= 0:
                                continue
                            supply = share * belt["reserve"] / (d + 1)
                            if best is None or supply > best[0]:
                                best = (supply, elem, s_id, d)
                if not best:
                    continue
                _, elem, belt_sector, hops = best
                amount = random.randint(*EXTRACTION_AMOUNT_RANGE)
                base = COMMODITY_CONFIG.get(elem, {}).get("base_price", 20)
                hazard_mult = {"BORDERLAND": 1.2, "ANARCHY": 1.6}.get(kernel.sectors[belt_sector].security.value, 1.0)
                payout = int((base * EXTRACTION_UNIT_PREMIUM * amount + hops * EXTRACTION_HOP_FEE) * hazard_mult
                             * self._local_price_level(planet.currency))
                if planet.treasury - payout < COLONY_IMPORT_MIN_VAULT // 2:
                    continue
                planet.treasury -= payout
                cid = f"EXT-{self.next_contract_id}"
                self.next_contract_id += 1
                contract = FreightContract(
                    id=cid, company_ticker="COLONY", issuer_name=f"{planet.name} Industrial Yard",
                    origin_sector=belt_sector, origin_name=f"Null-space belt {belt_sector:03d}",
                    destination_sector=sec.id, destination_planet_id=planet.id, destination_name=planet.name,
                    commodity=elem, amount=amount, payout_credits=payout, shares_reward=0,
                    hazard_level=kernel.sectors[belt_sector].security.value,
                    created_cycle=kernel.cycle_count, expiry_cycle=kernel.cycle_count + EXTRACTION_EXPIRY,
                    status="OPEN", escrow_source=f"planet:{planet.id}", escrow_amount=payout,
                    currency=planet.currency, kind="EXTRACTION",
                )
                self.contracts[cid] = contract
                open_by_planet[planet.id] = open_by_planet.get(planet.id, 0) + 1
                created.append(contract)
        return created

    def _refund_escrow(self, contract: FreightContract, kernel: Any = None) -> None:
        amount, source = contract.escrow_amount, contract.escrow_source or ""
        contract.escrow_amount = 0
        if amount <= 0:
            return
        if source.startswith("company:"):
            comp = self.companies.get(source.split(":", 1)[1])
            cur = getattr(contract, "currency", "SOL") or "SOL"
            if comp and cur != "SOL" and comp.home_currency == cur:
                comp.home_cash += amount              # escrowed in the firm's home money, returned there
                return
            if comp and cur == "SOL":
                comp.treasury += amount
                return
        elif source.startswith("planet:") and kernel is not None:
            planet = kernel.get_planet(source.split(":", 1)[1])
            if planet:
                planet.treasury += amount
                return
        cur = getattr(contract, "currency", "SOL") or "SOL"
        if cur != "SOL" and kernel is not None:
            # unclaimed escrow in a regional money stays in that money: to the world it was bound for, else
            # cleared into SOL through the exchange before it reaches the Reserve
            dest = kernel.get_planet(contract.destination_planet_id) if contract.destination_planet_id else None
            if dest is not None and dest.currency == cur:
                dest.treasury += amount
                return
            from xylarium.kernel.fx import ACTIVE_FX
            amount = ACTIVE_FX.swap_to_sol(cur, amount) if ACTIVE_FX is not None else 0
        fed = getattr(kernel, "federal_reserve", None) if kernel is not None else None
        if fed:
            fed.receive(amount, "unclaimed_escrow")

    @staticmethod
    def _repossess_bonded(captain: Any, contract: FreightContract) -> None:
        """A voided contract's bonded goods belong to the issuer and are unloaded from the courier."""
        cargo = captain.ship.cargo
        comm = contract.commodity.upper()
        if comm in ("ORE", "ORGANICS", "EQUIPMENT"):
            key = comm
        else:
            key = next((k for k in cargo.elements if k.lower() == contract.commodity.lower()), contract.commodity)
        take = min(contract.amount, cargo.held(key), cargo.bonded_units(key))
        cargo.release_bond(key, contract.amount)
        if take <= 0:
            return
        if key in ("ORE", "ORGANICS", "EQUIPMENT"):
            setattr(cargo, key.lower(), getattr(cargo, key.lower()) - take)
        else:
            cargo.elements[key] = cargo.elements.get(key, 0) - take
            if cargo.elements[key] <= 0:
                cargo.elements.pop(key, None)
        # The issuer's goods go back to the warehouse they were loaded from
        from xylarium.kernel import ledger
        k = ledger.active_kernel()
        sec = k.sectors.get(contract.origin_sector) if k is not None else None
        if sec is not None and sec.port is not None:
            sec.port.stock[key] = sec.port.stock.get(key, 0) + take
        else:
            matter.sink("repossessed", key, take)

    def void_contract(self, contract: FreightContract, kernel: Any = None) -> None:
        """Expires a contract: refunds escrow, repossesses bonded goods, clears the courier manifest."""
        was_in_transit = contract.status == "IN_TRANSIT"
        self._refund_escrow(contract, kernel)  # before the status change, so escrow -> issuer is atomic
        contract.status = "EXPIRED"
        comp = self.companies.get(contract.company_ticker)
        if comp:
            comp.contracts_failed += 1
        courier = kernel.captains.get(contract.accepted_by) if (kernel is not None and contract.accepted_by) else None
        if courier:
            if contract.id in getattr(courier, "active_contracts", []):
                courier.active_contracts.remove(contract.id)
            if was_in_transit and contract.kind != "EXTRACTION":
                self._repossess_bonded(courier, contract)

    def buy_shares(self, captain: Any, ticker: str, amount: int) -> Tuple[bool, str, Dict[str, Any]]:
        """Purchase shares of a listed company from the open market."""
        ticker = ticker.upper()
        if ticker not in self.companies:
            return False, f"Ticker '{ticker}' is not listed on the Interstellar Stock Exchange.", {}

        if amount <= 0:
            return False, "Share purchase quantity must be greater than zero.", {}

        company = self.companies[ticker]
        if amount > company.available_shares:
            # Secondary offering: a company whose float is sold out issues new stock to meet demand
            # (dilution: fundamentals are per share, so existing holders' value per share falls)
            from xylarium.config import SHARE_ISSUANCE_MAX_MULTIPLE
            if not company.initial_shares:
                company.initial_shares = company.total_shares
            ceiling = int(company.initial_shares * SHARE_ISSUANCE_MAX_MULTIPLE)
            issue = min(amount - company.available_shares, max(0, ceiling - company.total_shares))
            if issue > 0:
                company.total_shares += issue
                company.available_shares += issue
            if amount > company.available_shares:
                return False, f"Market order exceeds float! Only {company.available_shares:,} shares of {ticker} are available.", {}

        total_cost = company.share_price * amount
        if captain.credits < total_cost:
            return False, f"Insufficient funds! {amount:,} shares of {ticker} cost {total_cost:,} Cr. You have {captain.credits:,} Cr.", {}

        # Execute order
        captain.credits -= total_cost
        company.treasury += total_cost  # the whole price reaches the corporate balance sheet (nothing vanishes)
        company.available_shares -= amount

        # Track portfolio on captain
        port = getattr(captain, "portfolio", {})
        port[ticker] = port.get(ticker, 0) + amount
        captain.portfolio = port

        # Market demand marginally elevates share price (+0.5% per 100 shares bought)
        price_bump = max(0, int(amount * 0.005))
        if price_bump > 0:
            company.share_price += price_bump
            company.price_history.append(company.share_price)

        msg = (
            f"BOUGHT {amount:,} shares of {company.name} ({ticker}) @ {company.share_price} Cr/ea. "
            f"Total Investment: {total_cost:,} Cr. (Portfolio: {port[ticker]:,} shares)"
        )
        return True, msg, {
            "ticker": ticker,
            "shares_bought": amount,
            "total_cost": total_cost,
            "new_balance": captain.credits,
            "owned_shares": port[ticker],
        }

    def sell_shares(self, captain: Any, ticker: str, amount: int) -> Tuple[bool, str, Dict[str, Any]]:
        """Liquidate owned shares on the open stock exchange."""
        ticker = ticker.upper()
        if ticker not in self.companies:
            return False, f"Ticker '{ticker}' is not recognized on the ISSE.", {}

        if amount <= 0:
            return False, "Sell quantity must be greater than zero.", {}

        port = getattr(captain, "portfolio", {})
        owned = port.get(ticker, 0)
        if amount > owned:
            return False, f"You only hold {owned:,} shares of {ticker}.", {}

        company = self.companies[ticker]
        # The company buys its shares back out of its own treasury: no buyer liquidity, no sale
        self._market_maker_sol(company, company.share_price * amount)
        affordable = int(company.treasury // max(1, company.share_price))
        if affordable <= 0:
            return False, f"ISSE: {ticker} has no buyback liquidity today.", {}
        amount = min(amount, affordable)
        gross_proceeds = company.share_price * amount
        # 2% exchange brokerage fee stays with the company
        fee = max(1, int(gross_proceeds * 0.02))
        net_proceeds = gross_proceeds - fee
        company.treasury -= net_proceeds

        # Execute liquidation
        port[ticker] -= amount
        if port[ticker] == 0:
            del port[ticker]
        captain.portfolio = port

        captain.credits += net_proceeds
        company.available_shares += amount

        # Selling pressure marginally eases price (-0.5% per 100 shares)
        price_drop = max(0, int(amount * 0.005))
        if price_drop > 0:
            company.share_price = max(1, company.share_price - price_drop)
            company.price_history.append(company.share_price)

        msg = (
            f"LIQUIDATED {amount:,} shares of {company.name} ({ticker}) for {net_proceeds:,} Cr "
            f"(Fee: {fee:,} Cr). Remaining: {port.get(ticker, 0):,} shares."
        )
        return True, msg, {
            "ticker": ticker,
            "shares_sold": amount,
            "net_proceeds": net_proceeds,
            "remaining_shares": port.get(ticker, 0),
        }

    def float_ipo(
        self,
        captain: Any,
        planet: Any,
        company_name: str,
        ticker: str,
        industry: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Colony Governor floats an Initial Public Offering (IPO) on the ISSE.
        Mints 10,000 shares: founder keeps 6,000 shares (60%), floats 4,000 shares
        to raise liquid capital into planetary vault.
        """
        ticker = ticker.upper().strip()
        if len(ticker) < 3 or len(ticker) > 5:
            return False, "Company ticker must be 3 to 5 capital letters.", {}

        if ticker in self.companies:
            return False, f"Ticker '{ticker}' is already registered on the exchange.", {}

        # Listing requires colony ownership and Citadel Tier 1+
        if planet.owner_id != captain.id:
            return False, f"You must be the sovereign governor of {planet.name} to float an IPO.", {}

        if planet.citadel_level < 1:
            return False, "Floating an IPO requires a fortified colony (Citadel Tier 1+ Redoubt).", {}

        # 3,000 Cr regulatory listing fee
        listing_fee = 3000
        if captain.credits < listing_fee:
            return False, f"IPO listing fee is {listing_fee:,} Cr. You have {captain.credits:,} Cr.", {}

        captain.credits -= listing_fee
        ledger_pay(listing_fee, captain.sector_id)                 # the exchange's listing desk
        initial_price = 25
        raised_capital = initial_price * 4000  # 100,000 Cr valuation, 100k capital

        comp = Company(
            ticker=ticker,
            name=company_name,
            sector_id=planet.sector_id,
            planet_id=planet.id,
            planet_name=planet.name,
            industry=industry.upper(),
            founder_id=captain.id,
            level=2,
            share_price=initial_price,
            total_shares=10000,
            available_shares=4000,
            treasury=raised_capital // 2,
            dividend_rate=0.08,
            price_history=[initial_price],
        )
        self.companies[ticker] = comp

        # Founder keeps 6,000 shares (majority 60% stake)
        port = getattr(captain, "portfolio", {})
        port[ticker] = port.get(ticker, 0) + 6000
        captain.portfolio = port

        # Planet vault receives capital infusion
        # Outside investors capitalize the IPO: new money enters circulation (declared faucet)
        from xylarium.kernel import ledger
        from xylarium.kernel.fx import ACTIVE_FX
        vault_infusion = raised_capital // 2
        if planet.currency != "SOL" and ACTIVE_FX is not None:
            vault_infusion = int(vault_infusion * ACTIVE_FX.rate(planet.currency))
        ledger.mint("ipo_capital", raised_capital // 2, "SOL")
        ledger.mint("ipo_capital", vault_infusion, planet.currency)
        planet.treasury += vault_infusion
        captain.score += 500

        msg = (
            f"INITIAL PUBLIC OFFERING SUCCESS! '{company_name}' ({ticker}) listed on the ISSE. "
            f"Founder retains 6,000 shares (60%). Planetary vault credited +{raised_capital // 2:,} Cr!"
        )
        return True, msg, {
            "ticker": ticker,
            "company_name": company_name,
            "founder_shares": 6000,
            "capital_raised": raised_capital // 2,
        }

    def _purchase_goods_at_origin(self, contract: FreightContract) -> int:
        """Load the contract's goods from the origin warehouse (what it holds, no more) and pay for them out of
        the issuer's escrow. Records what physically left the warehouse in ``self._last_loaded``."""
        kernel = self._kernel_ref
        self._last_loaded = (None, 0)
        if kernel is None:
            return 0
        sec = kernel.sectors.get(contract.origin_sector)
        port = sec.port if sec is not None else None
        if port is None:
            return 0
        from xylarium.kernel.economy import EconomyManager
        from xylarium.kernel.fx import ACTIVE_FX
        comm = contract.commodity.upper()
        key = comm if comm in port.stock else contract.commodity
        units = min(contract.amount, max(0, port.stock.get(key, 0)))
        if units <= 0:
            return 0
        _, unit = EconomyManager.get_unit_prices(port, comm if comm in ("ORE", "ORGANICS", "EQUIPMENT") else contract.commodity)
        port.stock[key] = port.stock.get(key, 0) - units
        self._last_loaded = (key, units)
        goods_local = unit * units                      # in the port's currency
        if goods_local <= 0 or contract.escrow_amount <= 0:
            return 0
        def to_sol(cur, amt):
            return ACTIVE_FX.to_sol_value(cur, amt) if (ACTIVE_FX and cur != "SOL") else amt
        # Cap the goods bill at 60% of the escrow so the courier is always paid for the haul
        max_escrow_spend = int(contract.escrow_amount * 0.6)
        goods_in_escrow_cur = int(to_sol(port.currency, goods_local) * (ACTIVE_FX.rate(contract.currency)
                                  if (ACTIVE_FX and contract.currency != "SOL") else 1))
        spend = min(max_escrow_spend, goods_in_escrow_cur)
        if spend <= 0:
            return 0
        contract.escrow_amount -= spend
        contract.payout_credits = contract.escrow_amount
        if contract.currency == port.currency:
            port.treasury += spend
        elif ACTIVE_FX is not None:
            sol = spend if contract.currency == "SOL" else ACTIVE_FX.swap_to_sol(contract.currency, spend)
            port.treasury += sol if port.currency == "SOL" else ACTIVE_FX.swap_sol_to(port.currency, sol)
        return spend

    def forfeit_freight(self, captain: Any, kernel: Any = None) -> List[str]:
        """Voids a courier's in-transit contracts (e.g. ship destroyed with the bonded cargo)."""
        forfeited = []
        for cid in list(getattr(captain, "active_contracts", [])):
            contract = self.contracts.get(cid)
            if contract and contract.status == "IN_TRANSIT":
                self.void_contract(contract, kernel)
                forfeited.append(cid)
        captain.active_contracts = []
        captain.ship.cargo.bonded.clear()
        return forfeited

    def accept_freight_contract(self, captain: Any, contract_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Accept an open interstellar freight contract from the Galactic Board."""
        contract = self.contracts.get(contract_id)
        if not contract:
            return False, f"Freight contract '{contract_id}' not found.", {}

        if contract.status != "OPEN":
            return False, f"Contract {contract_id} is no longer open (Status: {contract.status}).", {}

        # Check corporate embargo
        company = self.companies.get(contract.company_ticker)
        if company and captain.id in company.embargoed_captains:
            return False, f"Corporate Embargo: You are barred from accepting contracts issued by {company.name} ({company.ticker}).", {}

        active_list = getattr(captain, "active_contracts", [])
        if contract.kind == "EXTRACTION":
            # Work orders are signed at the issuing colony's industrial yard; the ore is mined, not loaded
            if captain.sector_id != contract.destination_sector:
                return False, f"Sign industrial work orders at {contract.destination_name} (Sector {contract.destination_sector:03d}).", {}
            if len(active_list) >= 3:
                return False, "Freight manifest full! You can only manage up to 3 active shipping contracts simultaneously.", {}
            contract.status = "IN_TRANSIT"
            contract.accepted_by = captain.id
            active_list.append(contract.id)
            captain.active_contracts = active_list
            return True, (
                f"WORK ORDER SIGNED: {contract.id} - extract {contract.amount} {contract.commodity} "
                f"(richest nearby belt: Sector {contract.origin_sector:03d}) and return to {contract.destination_name} "
                f"for {contract.payout_credits:,} {contract.currency}."
            ), contract.to_dict()

        # Captain must be in the origin sector to load bonded freight
        if captain.sector_id != contract.origin_sector:
            return False, f"Must be docked at Sector {contract.origin_sector:03d} ({contract.origin_name}) to load freight.", {}

        # Check cargo space
        if captain.ship.cargo.available_space < contract.amount:
            return False, f"Insufficient cargo holds! Contract requires {contract.amount} holds. Free: {captain.ship.cargo.available_space}.", {}

        # Check maximum active contracts (max 3 at once)
        active_list = getattr(captain, "active_contracts", [])
        if len(active_list) >= 3:
            return False, "Freight manifest full! You can only manage up to 3 active shipping contracts simultaneously.", {}

        # The goods are bought from the origin starport out of the issuer's escrow (converted through
        # the ISSE FX desk when currencies differ); the rest of the escrow is the courier's haulage fee.
        self._purchase_goods_at_origin(contract)
        stock_key, loaded = self._last_loaded
        if loaded <= 0:
            return False, f"{contract.origin_name} has no {contract.commodity} to load for this contract.", {}
        contract.amount = loaded                          # only what the warehouse held is carried

        # Load bonded freight
        contract.status = "IN_TRANSIT"
        contract.accepted_by = captain.id
        active_list.append(contract.id)
        captain.active_contracts = active_list

        # Place bonded cargo in hold (uses standard commodity hold or elements)
        comm = contract.commodity.upper()
        if comm == "ORE":
            captain.ship.cargo.ore += contract.amount
        elif comm == "ORGANICS":
            captain.ship.cargo.organics += contract.amount
        elif comm == "EQUIPMENT":
            captain.ship.cargo.equipment += contract.amount
        else:
            # Periodic element cargo, under the element's canonical key (as the warehouse held it)
            elem_id = stock_key
            captain.ship.cargo.elements[elem_id] = captain.ship.cargo.elements.get(elem_id, 0) + contract.amount
        captain.ship.cargo.bond(comm if comm in ("ORE", "ORGANICS", "EQUIPMENT") else stock_key, contract.amount)

        msg = (
            f"FREIGHT MANIFEST SIGNED: {contract.id} accepted! Loaded {contract.amount} units of {contract.commodity}. "
            f"Deliver to {contract.destination_name} (Sector {contract.destination_sector:03d}) for {contract.payout_credits:,} Cr + {contract.shares_reward} Shares!"
        )
        return True, msg, contract.to_dict()

    def deliver_freight_contract(
        self,
        captain: Any,
        contract_id: str,
        planet: Any
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Verify delivery of bonded star cargo at the destination colony."""
        contract = self.contracts.get(contract_id)
        if not contract:
            return False, f"Freight contract '{contract_id}' not found.", {}

        if contract.status != "IN_TRANSIT" or contract.accepted_by != captain.id:
            return False, f"You are not the designated courier for contract {contract_id}.", {}

        if captain.sector_id != contract.destination_sector or planet.id != contract.destination_planet_id:
            return False, f"Wrong delivery port! Must deliver to {contract.destination_name} in Sector {contract.destination_sector:03d}.", {}

        # Check cargo presence in hold
        comm = contract.commodity.upper()
        if contract.kind == "EXTRACTION":
            cargo = captain.ship.cargo
            key = next((k for k in cargo.elements if k.lower() == contract.commodity.lower()), contract.commodity)
            core = contract.commodity.upper() in ("ORE", "ORGANICS", "EQUIPMENT")
            have = cargo.unbonded(contract.commodity)
            if have < contract.amount:
                return False, f"Work order short: hold contains {have}/{contract.amount} unbonded {contract.commodity}.", {}
            if core:
                attr = contract.commodity.lower()
                setattr(cargo, attr, getattr(cargo, attr) - contract.amount)
                if attr == "ore":
                    planet.ore_silo += contract.amount
                elif attr == "organics":
                    planet.organics_silo += contract.amount
                else:
                    matter.sink("colony_equipment", "EQUIPMENT", contract.amount)
            else:
                cargo.elements[key] -= contract.amount
                if cargo.elements[key] <= 0:
                    cargo.elements.pop(key, None)
                planet.element_reserves[contract.commodity] = planet.element_reserves.get(contract.commodity, 0) + contract.amount
            comm = None
        bond_key = comm if comm in ("ORE", "ORGANICS", "EQUIPMENT") else (
            next((k for k in captain.ship.cargo.bonded if k.lower() == comm.lower()), comm) if comm else "")
        if comm and captain.ship.cargo.held(bond_key) >= contract.amount:
            captain.ship.cargo.release_bond(bond_key, contract.amount)
        if comm is None:
            pass
        elif comm == "ORE":
            if captain.ship.cargo.ore < contract.amount:
                return False, f"Missing cargo! Hold only contains {captain.ship.cargo.ore} Ore.", {}
            captain.ship.cargo.ore -= contract.amount
            planet.ore_silo += contract.amount
        elif comm == "ORGANICS":
            if captain.ship.cargo.organics < contract.amount:
                return False, f"Missing cargo! Hold only contains {captain.ship.cargo.organics} Organics.", {}
            captain.ship.cargo.organics -= contract.amount
            planet.organics_silo += contract.amount
        elif comm == "EQUIPMENT":
            if captain.ship.cargo.equipment < contract.amount:
                return False, f"Missing cargo! Hold only contains {captain.ship.cargo.equipment} Equipment.", {}
            captain.ship.cargo.equipment -= contract.amount
            matter.sink("colony_equipment", "EQUIPMENT", contract.amount)   # installed into the colony's works
        else:
            elem_id = next((k for k in captain.ship.cargo.elements if k.lower() == comm.lower()), contract.commodity)
            if captain.ship.cargo.elements.get(elem_id, 0) < contract.amount:
                return False, f"Missing element! Hold contains {captain.ship.cargo.elements.get(elem_id, 0)} {comm}.", {}
            captain.ship.cargo.elements[elem_id] -= contract.amount
            if captain.ship.cargo.elements[elem_id] == 0:
                del captain.ship.cargo.elements[elem_id]
            reserves = getattr(planet, "element_reserves", {})
            reserves[elem_id] = reserves.get(elem_id, 0) + contract.amount

        # Complete contract
        contract.status = "COMPLETED"
        active_list = getattr(captain, "active_contracts", [])
        if contract.id in active_list:
            active_list.remove(contract.id)
            captain.active_contracts = active_list

        # Disburse rewards from escrow (legacy unescrowed contracts are paid by the issuer on delivery)
        contract.escrow_amount = 0
        from xylarium.kernel.fx import credit as fx_credit
        fx_credit(captain, contract.currency, contract.payout_credits)
        captain.score += max(50, contract.payout_credits // 20)
        captain.freight_deliveries_completed = getattr(captain, "freight_deliveries_completed", 0) + 1
        kernel = self._kernel_ref
        hops = abs(contract.destination_sector - contract.origin_sector)
        if kernel is not None:
            path = kernel.find_path(contract.origin_sector, contract.destination_sector)
            hops = max(1, len(path) - 1) if path else hops
        ExperienceManager.award(
            captain, "commerce", min(XP_FREIGHT_MAX, XP_FREIGHT_BASE + hops), kernel,
            key=f"freight:{contract.origin_sector}>{contract.destination_sector}",
        )
        ExperienceManager.record_revenue(captain, contract.payout_credits, kernel)
        if hasattr(captain, "adjust_credit_rating"):
            captain.adjust_credit_rating(5, reason=f"Fulfilled freight contract {contract.id}")
            captain.adjust_reputation("Corporate", 3.0)

        # Grant company shares reward
        company = self.companies.get(contract.company_ticker)
        if company and contract.shares_reward > 0:
            awarded_shares = min(company.available_shares, contract.shares_reward)
            if awarded_shares > 0:
                company.available_shares -= awarded_shares
                port = getattr(captain, "portfolio", {})
                port[company.ticker] = port.get(company.ticker, 0) + awarded_shares
                captain.portfolio = port

            # Company records revenue and bumps stock valuation
            company.quarterly_revenue += contract.payout_credits
            company.contracts_fulfilled += 1
            company.share_price += random.randint(1, 3)
            company.price_history.append(company.share_price)

        msg = (
            f"CARGO DELIVERED! Freight contract {contract.id} fulfilled at {planet.name}. "
            f"Paid: +{contract.payout_credits:,} Cr and awarded +{contract.shares_reward} Shares of {contract.company_ticker}!"
        )
        return True, msg, {
            "payout": contract.payout_credits,
            "shares_awarded": contract.shares_reward,
            "company_ticker": contract.company_ticker,
            "new_credits": captain.credits,
        }

    def execute_takeover(self, captain: Any, ticker: str, kernel: Any = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executes a hostile boardroom takeover if captain owns > 50% of outstanding corporate shares.
        Ousts the incumbent Chairman and assumes executive control of the company.
        """
        ticker = ticker.upper().strip()
        if ticker not in self.companies:
            return False, f"Ticker '{ticker}' is not listed on the ISSE.", {}

        company = self.companies[ticker]
        port = getattr(captain, "portfolio", {})
        owned_shares = port.get(ticker, 0)
        ownership_pct = (owned_shares / company.total_shares) * 100

        if company.chairman_id == captain.id:
            return False, f"You are already the Executive Chairman of {company.name} ({ticker}).", {}

        if ownership_pct <= 50.0:
            return False, (
                f"Hostile takeover rejected! Requires majority stake (>50.0%). "
                f"You hold {owned_shares:,}/{company.total_shares:,} shares ({ownership_pct:.1f}%). "
                f"If you hold between 25% and 50%, you can launch a PROXY_FIGHT instead."
            ), {"owned_shares": owned_shares, "ownership_pct": ownership_pct}

        # Check regulatory standing: Credit rating >= 650 AND Experience >= 500
        # Corporate raiders with accredited institutional capitalization (Net Equity >= 250,000 Cr) qualify
        min_cr = TAKEOVER_MIN_CREDIT
        min_exp = TAKEOVER_MIN_EXP
        cr = getattr(captain, "credit_rating", 500)
        exp = getattr(captain, "experience_score", 100)
        equity = self.calculate_net_equity(captain, kernel)

        is_accredited = (getattr(captain, "credits", 0) >= 250000 or equity >= 500000)
        if not is_accredited and (cr < min_cr or exp < min_exp):
            return False, (
                f"ISSE REGULATORY LOCKOUT: Hostile boardroom takeovers require institutional standing. "
                f"Prerequisites: Credit Rating >= {min_cr} and Experience Score (Ξ) >= {min_exp} (or Accredited Liquid Capitalization >= 250,000 Cr). "
                f"Your Profile: CR {cr}, Experience {exp}, Net Equity {equity:,} Cr."
            ), {"credit_rating": cr, "experience_score": exp, "net_equity": equity}

        old_chairman = company.chairman_id
        company.chairman_id = captain.id
        captain.score += 1500
        if hasattr(captain, "adjust_credit_rating"):
            captain.adjust_credit_rating(50, reason=f"Hostile corporate takeover of {ticker}")
            ExperienceManager.award(captain, "commerce", 30, self._kernel_ref, key=f"takeover:{ticker}")
            captain.adjust_reputation("Corporate", 10.0)
        # Raider absorbs target company's liquid treasury
        looted_treasury = company.treasury
        captain.credits += looted_treasury
        company.treasury = 0
        # The minority shareholders' part of that cash was theirs: embezzlement, where a court is watching
        minority = int(looted_treasury * max(0.0, 1.0 - ownership_pct / 100.0))
        if minority > 0 and self._kernel_ref is not None:
            from xylarium.kernel import law
            law.file(self._kernel_ref, "embezzlement", captain,
                     self._kernel_ref.sectors.get(captain.sector_id), minority)

        # Raider seizes sovereign ownership of target company planetary HQ and outposts
        seized_planets = []
        if kernel and hasattr(kernel, "sectors"):
            for s in kernel.sectors.values():
                for p in s.planets:
                    if p.id == company.planet_id or p.name == company.planet_name or (p.sector_id == company.sector_id and p.name == company.planet_name):
                        p.owner_id = captain.id
                        seized_planets.append(f"{p.name} (Sector {s.id:03d})")

        # Broadcast takeover coup across the galaxy
        if kernel and getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(
                sender="ISSE-REGULATORY",
                text=f"MAJORITY SHAREHOLDER COUP: Captain {captain.name} has seized 51%+ controlling interest in {company.name} ({ticker})! {old_chairman} has been unseated as Executive Chairman!",
                channel="SYSTEM",
                sector_id=company.sector_id,
            )

        # AI Retaliation if ousted chairman is Cynthia Voss
        retaliation_notes = []
        if old_chairman == "ai_voss":
            captain.bounty = getattr(captain, "bounty", 0) + 15000
            retaliation_notes.append("Director Cynthia Voss placed a 15,000 Cr corporate espionage bounty on your head!")
            if kernel and getattr(kernel, "event_bus", None):
                kernel.event_bus.broadcast_radio(
                    sender="Cynthia Voss",
                    text=f"To Captain {captain.name}: You may have bought my board, but you will not survive the fiscal year. Security operatives dispatched.",
                    channel="COMM-1",
                    sector_id=company.sector_id,
                )

        seized_str = f" Sovereign dominion established over {', '.join(seized_planets)}." if seized_planets else ""
        msg = (
            f"HOSTILE TAKEOVER SUCCESSFUL! You now control {ownership_pct:.1f}% of {company.name} ({ticker}). "
            f"You have ousted {old_chairman} and assumed the position of Executive Chairman. "
            f"Absorbed +{looted_treasury:,} Credits corporate treasury.{seized_str} "
            f"Boardroom governance commands (Special Dividends, Asset Stripping, Embargoes) unlocked!"
        )
        if retaliation_notes:
            msg += " " + " ".join(retaliation_notes)

        return True, msg, {
            "ticker": ticker,
            "company_name": company.name,
            "new_chairman": captain.id,
            "old_chairman": old_chairman,
            "ownership_pct": ownership_pct,
            "treasury_absorbed": looted_treasury,
            "treasury": company.treasury,
            "seized_planets": seized_planets,
        }

    def launch_proxy_fight(self, captain: Any, ticker: str, kernel: Any = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Launches a proxy battle for corporate control if holding 25%–50% equity.
        Appeals to institutional and public shareholders to vote against incumbent management.
        """
        ticker = ticker.upper().strip()
        if ticker not in self.companies:
            return False, f"Ticker '{ticker}' is not listed on the ISSE.", {}

        company = self.companies[ticker]
        if company.chairman_id == captain.id:
            return False, f"You are already the Executive Chairman of {company.name}.", {}

        port = getattr(captain, "portfolio", {})
        owned_shares = port.get(ticker, 0)
        ownership_pct = (owned_shares / company.total_shares) * 100

        if ownership_pct < 25.0:
            return False, (
                f"Proxy challenge denied! Minimum 25.0% equity threshold required to file proxy materials. "
                f"You hold {owned_shares:,}/{company.total_shares:,} shares ({ownership_pct:.1f}%)."
            ), {}

        filing_cost = 4000
        if captain.credits < filing_cost:
            return False, f"Filing SEC proxy materials and shareholder solicitation requires {filing_cost:,} Cr. You have {captain.credits:,} Cr.", {}

        captain.credits -= filing_cost
        ledger_pay(filing_cost, captain.sector_id)                 # proxy agents and printers

        # Calculate voting blocks
        challenger_votes = owned_shares

        # Public / Floating shareholder sentiment:
        public_pool = company.available_shares
        sentiment_ratio = 0.35  # baseline 35% public support
        if company.contracts_failed > 0:
            sentiment_ratio += 0.20
        if company.last_dividend <= 1:
            sentiment_ratio += 0.15
        if len(company.price_history) >= 2 and company.price_history[-1] <= company.price_history[-2]:
            sentiment_ratio += 0.15

        public_votes_for_challenger = int(public_pool * min(0.85, sentiment_ratio))
        public_votes_for_incumbent = public_pool - public_votes_for_challenger

        insider_shares = max(0, company.total_shares - company.available_shares - owned_shares)
        incumbent_votes = insider_shares + public_votes_for_incumbent
        total_challenger_tally = challenger_votes + public_votes_for_challenger

        total_voted = total_challenger_tally + incumbent_votes
        challenger_vote_pct = (total_challenger_tally / total_voted) * 100

        if total_challenger_tally > incumbent_votes:
            # Proxy coup succeeds!
            old_chairman = company.chairman_id
            company.chairman_id = captain.id
            captain.score += 2000

            if kernel and getattr(kernel, "event_bus", None):
                kernel.event_bus.broadcast_radio(
                    sender="ISSE-PROXY-BOARD",
                    text=f"PROXY COUP: Institutional and public shareholders voted {challenger_vote_pct:.1f}% to oust {old_chairman}! Captain {captain.name} elected Executive Chairman of {company.name}!",
                    channel="SYSTEM",
                    sector_id=company.sector_id,
                )

            msg = (
                f"PROXY FIGHT VICTORY! Institutional and public shareholders rallied behind your bid ({challenger_vote_pct:.1f}% majority vote). "
                f"You have removed {old_chairman} and been elected Executive Chairman of {company.name} ({ticker})!"
            )
            return True, msg, {
                "won": True,
                "challenger_votes": total_challenger_tally,
                "incumbent_votes": incumbent_votes,
                "vote_pct": challenger_vote_pct,
                "new_chairman": captain.id,
            }
        else:
            msg = (
                f"PROXY FIGHT DEFEATED: Incumbent management mobilized {100 - challenger_vote_pct:.1f}% of shareholder votes. "
                f"Your proxy challenge failed ({total_challenger_tally:,} vs {incumbent_votes:,} votes). "
                f"4,000 Cr proxy filing fee spent."
            )
            return False, msg, {
                "won": False,
                "challenger_votes": total_challenger_tally,
                "incumbent_votes": incumbent_votes,
                "vote_pct": challenger_vote_pct,
            }

    def activate_poison_pill(self, caller_id: str, ticker: str, kernel: Any = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Triggers a defensive Poison Pill (Shareholder Rights Plan).
        Mints 25% new dilutive shares, expanding total shares and diluting any hostile raider.
        """
        ticker = ticker.upper().strip()
        if ticker not in self.companies:
            return False, f"Ticker '{ticker}' is not listed on the ISSE.", {}

        company = self.companies[ticker]
        if company.chairman_id != caller_id and company.founder_id != caller_id:
            return False, "Access Denied: Only the incumbent Chairman or Founder can trigger a Poison Pill defense.", {}

        if company.poison_pill_uses <= 0:
            return False, f"Poison pill defenses for {ticker} have been exhausted.", {}

        # 25% new dilutive shares go into the company's own unissued float: the raider's stake shrinks, and the
        # shares raise money only when they are sold (no cash appears from nowhere - the economy is closed)
        dilution_shares = int(company.total_shares * 0.25)
        company.total_shares += dilution_shares
        company.available_shares += dilution_shares
        company.poison_pill_uses -= 1
        company.poison_pill_active = True

        if kernel and getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(
                sender=company.name,
                text=f"POISON PILL TRIGGERED: {company.name} ({ticker}) has executed a dilutive shareholder rights plan to repel hostile takeovers! +{dilution_shares:,} shares issued.",
                channel="SYSTEM",
                sector_id=company.sector_id,
            )

        msg = (
            f"POISON PILL EXECUTED: Mints {dilution_shares:,} dilutive shares (+25% float expansion). "
            f"Hostile bidder ownership stakes diluted. New Total Shares: {company.total_shares:,}."
        )
        return True, msg, {
            "dilution_shares": dilution_shares,
            "new_total_shares": company.total_shares,
            "poison_pill_uses_left": company.poison_pill_uses,
        }

    def call_board_vote(
        self,
        captain: Any,
        ticker: str,
        mandate: str,
        kernel: Any = None,
        **kwargs
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executes an Executive Chairman Board Mandate:
        - SPECIAL_DIVIDEND: Disburses 30% of company treasury immediately to shareholders.
        - CHANGE_INDUSTRY: Reassigns corporate sector industry.
        - CORPORATE_EMBARGO: Bars target captain from company freight contracts.
        - STRIP_ASSETS: Chairman extracts 25% treasury as executive fees.
        """
        ticker = ticker.upper().strip()
        if ticker not in self.companies:
            return False, f"Ticker '{ticker}' is not listed on the ISSE.", {}

        company = self.companies[ticker]
        if company.chairman_id != captain.id:
            return False, f"Access Denied: Only Executive Chairman {company.chairman_id} can execute board mandates for {company.name}.", {}

        mandate = mandate.upper().strip()

        if mandate == "SPECIAL_DIVIDEND":
            if company.treasury < 1000:
                return False, f"Corporate treasury too low ({company.treasury:,} Cr) to issue special dividend.", {}

            div_pool = int(company.treasury * 0.30)
            company.treasury -= div_pool
            company.special_dividends_paid += div_pool

            # Distribute proportionally to captains holding shares
            port = getattr(captain, "portfolio", {})
            cap_shares = port.get(ticker, 0)
            payout = int((cap_shares / company.total_shares) * div_pool)
            captain.credits += payout

            msg = (
                f"BOARD RESOLUTION: SPECIAL DIVIDEND of {div_pool:,} Cr disbursed from {company.name} treasury! "
                f"Your {cap_shares:,} shares paid out +{payout:,} Credits! (Treasury remaining: {company.treasury:,} Cr)"
            )
            return True, msg, {"payout": payout, "treasury_left": company.treasury, "div_pool": div_pool}

        elif mandate == "CHANGE_INDUSTRY":
            new_ind = kwargs.get("industry", "MANUFACTURING").upper().strip()
            valid_inds = ["MINING", "AGRICULTURE", "MANUFACTURING", "EXOTIC_ELEMENTS"]
            if new_ind not in valid_inds:
                return False, f"Invalid industry. Must be one of: {', '.join(valid_inds)}.", {}

            old_ind = company.industry
            company.industry = new_ind
            msg = f"BOARD RESOLUTION: {company.name} core industry redirected from {old_ind} to {new_ind}."
            return True, msg, {"old_industry": old_ind, "new_industry": new_ind}

        elif mandate == "CORPORATE_EMBARGO":
            target_id = kwargs.get("target_id", "").strip()
            if not target_id:
                return False, "Must specify a target captain ID to embargo.", {}
            if target_id == captain.id:
                return False, "Cannot embargo yourself.", {}

            if target_id not in company.embargoed_captains:
                company.embargoed_captains.append(target_id)

            msg = f"BOARD RESOLUTION: Corporate Embargo declared against Captain {target_id}! They are barred from all {company.name} freight contracts."
            return True, msg, {"target_id": target_id, "embargoed": company.embargoed_captains}

        elif mandate == "STRIP_ASSETS":
            if company.treasury < 2000:
                return False, f"Treasury insufficient ({company.treasury:,} Cr) for executive asset extraction.", {}

            loot = int(company.treasury * 0.25)
            company.treasury -= loot
            captain.credits += loot
            company.share_price = max(1, company.share_price - 2)
            company.price_history.append(company.share_price)

            msg = (
                f"EXECUTIVE ASSET STRIPPING: {loot:,} Credits extracted from {company.name} treasury as Chairman Bonus! "
                f"Treasury balance: {company.treasury:,} Cr. Share price adjusted to {company.share_price} Cr."
            )
            return True, msg, {"credits_looted": loot, "new_treasury": company.treasury, "share_price": company.share_price}

        else:
            return False, f"Unknown board mandate: '{mandate}'. Valid: SPECIAL_DIVIDEND, CHANGE_INDUSTRY, CORPORATE_EMBARGO, STRIP_ASSETS.", {}

    def _market_maker_sol(self, company: Any, need: int) -> None:
        """A company making a market in its own shares pays in SOL; what it holds in its home money beyond what it
        needs to run a quarter comes through the exchange when its SOL falls short (a swap, nothing minted)."""
        from xylarium.kernel import enterprise, ledger
        from xylarium.kernel.fx import ACTIVE_FX
        kernel = getattr(self, "_kernel_ref", None) or ledger.active_kernel()
        spare = company.home_cash - (enterprise.working_need(kernel, company) if kernel is not None else 0)
        short = need - company.treasury
        if short <= 0 or spare <= 0 or ACTIVE_FX is None:
            return
        cur = company.home_currency or "SOL"
        if cur == "SOL":
            move = min(spare, short)
            company.home_cash -= move
            company.treasury += move
            return
        local = min(spare, int(short * ACTIVE_FX.rate(cur) * 1.06) + 1)    # the fee's margin
        company.home_cash -= local
        company.treasury += ACTIVE_FX.swap_to_sol(cur, local)

    def short_sell(self, captain: Any, ticker: str, amount: int, kernel: Any = None) -> Tuple[bool, str, Dict[str, Any]]:
        if kernel is None:
            from xylarium.kernel import ledger
            kernel = ledger.active_kernel()
        """
        Executes a short sale on the ISSE: borrows shares from the market float,
        requires 50% margin collateral, immediately sells shares at market price,
        and applies downward pressure on the stock price.
        """
        ticker = ticker.upper().strip()
        if ticker not in self.companies:
            return False, f"Ticker '{ticker}' is not listed on the ISSE.", {}

        if amount <= 0:
            return False, "Short quantity must be greater than zero.", {}

        cr = getattr(captain, "credit_rating", 500)
        if cr < SHORT_MIN_CREDIT:
            return False, (
                f"ISSE MARGIN DESK LOCKOUT: Short selling requires maintaining a satisfactory credit score (CR >= {SHORT_MIN_CREDIT}). "
                f"Your current rating is {cr} (Distressed). Settle outstanding liabilities and restore your standing before opening short positions."
            ), {"credit_rating": cr}

        company = self.companies[ticker]
        total_value = amount * company.share_price

        # Dynamic margin requirement (50% baseline at CR 500)
        if cr >= 500:
            margin_rate = max(0.25, round(0.50 - (cr - 500.0) / 1000.0, 2))
        else:
            margin_rate = min(0.90, round(0.50 + (500.0 - cr) / 500.0, 2))

        margin_collateral = int(total_value * margin_rate)

        if captain.credits < margin_collateral:
            return False, (
                f"Insufficient margin collateral! Shorting {amount:,} shares of {ticker} requires {margin_collateral:,} Cr "
                f"({int(margin_rate * 100)}% margin). You have {captain.credits:,} Cr."
            ), {}
        # The market maker for a company's shares is its own treasury: it pays for the borrowed shares it takes
        self._market_maker_sol(company, total_value)
        if company.treasury < total_value:
            return False, (f"No buyer: {ticker}'s market maker cannot take {amount:,} shares "
                           f"({total_value:,} Cr) today."), {}

        # Collateral is escrowed at the Federal margin desk; the proceeds come from the market maker
        captain.credits -= margin_collateral
        fed = getattr(kernel, "federal_reserve", None)
        if fed is not None:
            fed.receive(margin_collateral, "margin_escrow")
        company.treasury -= total_value
        captain.credits += total_value

        # Record or update short position
        shorts = getattr(captain, "short_positions", {})
        if ticker in shorts:
            pos = shorts[ticker]
            cur_shares = pos["shares"]
            cur_entry = pos["entry_price"]
            cur_collat = pos["collateral"]
            new_shares = cur_shares + amount
            new_entry = ((cur_shares * cur_entry) + total_value) // new_shares
            new_collat = cur_collat + margin_collateral
            shorts[ticker] = {
                "ticker": ticker,
                "shares": new_shares,
                "entry_price": new_entry,
                "collateral": new_collat,
                "margin_rate": margin_rate,
            }
        else:
            shorts[ticker] = {
                "ticker": ticker,
                "shares": amount,
                "entry_price": company.share_price,
                "collateral": margin_collateral,
                "margin_rate": margin_rate,
            }
        captain.short_positions = shorts

        # Market raid / short downward price pressure
        price_drop = max(1, amount // 200)
        old_price = company.share_price
        company.share_price = max(1, company.share_price - price_drop)
        company.price_history.append(company.share_price)

        msg = (
            f"SHORT ORDER EXECUTED: Borrowed and sold {amount:,} shares of {ticker} at {old_price} Cr/share. "
            f"Gross proceeds +{total_value:,} Cr credited (-{margin_collateral:,} Cr margin held @ {int(margin_rate * 100)}%). "
            f"Stock price slipped to {company.share_price} Cr."
        )
        return True, msg, {
            "ticker": ticker,
            "shares": amount,
            "entry_price": old_price,
            "margin_collateral": margin_collateral,
            "margin_rate": margin_rate,
            "gross_proceeds": total_value,
            "new_share_price": company.share_price,
            "short_position": shorts[ticker],
        }

    def cover_short(self, captain: Any, ticker: str, amount: Optional[int] = None, kernel: Any = None) -> Tuple[bool, str, Dict[str, Any]]:
        if kernel is None:
            from xylarium.kernel import ledger
            kernel = ledger.active_kernel()
        """
        Covers (buys back) an open short position on the ISSE, releases proportional
        margin collateral, settles profit/loss, and exerts upward price pressure.
        """
        ticker = ticker.upper().strip()
        if ticker not in self.companies:
            return False, f"Ticker '{ticker}' is not listed on the ISSE.", {}

        company = self.companies[ticker]
        shorts = getattr(captain, "short_positions", {})
        if ticker not in shorts:
            return False, f"You do not have an open short position in {ticker}.", {}

        pos = shorts[ticker]
        total_open = pos["shares"]
        if amount is None or amount <= 0 or amount > total_open:
            amount = total_open

        buyback_cost = amount * company.share_price
        collat_released = int(pos["collateral"] * (amount / total_open))
        fed = getattr(kernel, "federal_reserve", None)
        if fed is not None:
            collat_released = min(collat_released, fed.treasury)   # the margin desk holds the escrow

        # Check if captain can afford to buy back (with collateral refund factored in)
        if captain.credits + collat_released < buyback_cost:
            deficit = buyback_cost - (captain.credits + collat_released)
            return False, (
                f"Margin Deficit! Buying back {amount:,} shares requires {buyback_cost:,} Cr. "
                f"With collateral refund ({collat_released:,} Cr), you still need {deficit:,} more Credits."
            ), {}

        # Collateral comes back from the margin desk; the buyback pays the market maker
        if fed is not None:
            fed.treasury -= collat_released
            fed.stats["margin_released"] += collat_released
        captain.credits += collat_released
        captain.credits -= buyback_cost
        company.treasury += buyback_cost

        # P&L calculation
        entry_price = pos["entry_price"]
        pnl = (entry_price - company.share_price) * amount
        captain.score += max(0, pnl // 50)
        if pnl > 0 and hasattr(captain, "adjust_experience"):
            captain.adjust_experience(max(5, pnl // 1000))
            captain.adjust_credit_rating(max(1, pnl // 10000), reason="Profitable short cover")

        # Update position
        if amount >= total_open:
            del shorts[ticker]
        else:
            pos["shares"] -= amount
            pos["collateral"] -= collat_released
            shorts[ticker] = pos
        captain.short_positions = shorts

        # Upward price pressure from buyback
        price_bump = max(1, amount // 200)
        company.share_price += price_bump
        company.price_history.append(company.share_price)

        pnl_desc = f"+{pnl:,} Cr Profit" if pnl >= 0 else f"{pnl:,} Cr Loss"
        msg = (
            f"SHORT COVERED: Repurchased {amount:,} shares of {ticker} at {company.share_price - price_bump} Cr/share. "
            f"Cost: -{buyback_cost:,} Cr │ Collateral Released: +{collat_released:,} Cr │ Net P&L: {pnl_desc}. "
            f"Stock price rallied to {company.share_price} Cr."
        )
        return True, msg, {
            "ticker": ticker,
            "shares_covered": amount,
            "buyback_cost": buyback_cost,
            "collateral_released": collat_released,
            "pnl": pnl,
            "new_share_price": company.share_price,
            "remaining_position": shorts.get(ticker),
        }

    def set_sector_tariff(
        self,
        captain: Any,
        sector_id: int,
        tariff_pct: int,
        kernel: Any = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Enacts or adjusts a sovereign sector transit tariff (0% - 50%).
        Requires sovereignty over the sector (ownership of a Citadel Tier 1+ colony
        or Executive Chairmanship of a corporation headquartered in the sector).
        """
        if not (0 <= tariff_pct <= 50):
            return False, "Sector tariff rate must be between 0% and 50%.", {}

        if not kernel or sector_id not in kernel.sectors:
            return False, f"Sector {sector_id} does not exist.", {}

        sector = kernel.sectors[sector_id]
        authorized = False
        target_planet = None

        # Check colony ownership
        for p in sector.planets:
            if p.owner_id == captain.id and p.citadel_level >= 1:
                authorized = True
                target_planet = p
                break

        # Check corporate chairmanship in sector
        if not authorized:
            for comp in self.companies.values():
                if comp.sector_id == sector_id and comp.chairman_id == captain.id:
                    authorized = True
                    if sector.planets:
                        target_planet = sector.planets[0]
                    break

        if not authorized:
            return False, (
                f"Authority Denied! Establishing customs tariffs in Sector {sector_id:03d} requires "
                f"sovereign ownership of a Citadel Tier 1+ colony or Executive Chairmanship of an HQ corporation."
            ), {}

        if target_planet:
            target_planet.sector_tariff_pct = tariff_pct

        if kernel and getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(
                sender="CUSTOMS-AUTHORITY",
                text=f"SOVEREIGN TARIFF UPDATE: Transit tariff in Sector {sector_id:03d} set to {tariff_pct}% by Captain {captain.name}.",
                channel="SYSTEM",
                sector_id=sector_id,
            )

        msg = f"CUSTOMS TARIFF ENACTED: Sector {sector_id:03d} transit tariff set to {tariff_pct}%. Interstellar travelers will pay customs tolls upon arrival."
        return True, msg, {"sector_id": sector_id, "tariff_pct": tariff_pct}

    def hire_sales_executive(
        self,
        captain: Any,
        ticker: str,
        name: Optional[str] = None,
        kernel: Any = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Hires a dedicated corporate Sales Executive to capture regional market penetration.
        Requires captain to be Chairman or Founder of the target company.
        Cost: 2,500 Credits.
        """
        ticker = ticker.upper().strip()
        if ticker not in self.companies:
            return False, f"Ticker '{ticker}' is not listed on the ISSE.", {}

        comp = self.companies[ticker]
        if comp.chairman_id != captain.id and comp.founder_id != captain.id:
            return False, f"Access Denied: Only Chairman or Founder can recruit executives for {comp.name}.", {}

        cost = 2500
        if captain.credits < cost:
            return False, f"Recruiting a Sales Executive requires {cost:,} Credits. You have {captain.credits:,} Cr.", {}

        captain.credits -= cost
        ledger_pay(cost, captain.sector_id)                        # the executive's signing bonus and agency
        exec_id = f"EXEC-{self.next_exec_id}"
        self.next_exec_id += 1

        exec_name = name.strip() if name and name.strip() else f"Director {captain.name.split()[0]} Jr."
        executive = SalesExecutive(
            id=exec_id,
            company_ticker=ticker,
            owner_id=captain.id,
            name=exec_name,
            sector_id=comp.sector_id,
            salary=500,
            active=True,
        )
        self.executives[exec_id] = executive

        # Register to captain and company
        cap_execs = getattr(captain, "sales_executives", [])
        cap_execs.append(exec_id)
        captain.sales_executives = cap_execs

        comp.sales_executives.append(exec_id)

        # Boost penetration in initial sector by +20%
        cur_pen = comp.market_penetration.get(comp.sector_id, 0.0)
        comp.market_penetration[comp.sector_id] = min(100.0, cur_pen + 20.0)

        msg = (
            f"SALES EXECUTIVE CONTRACTED: {exec_name} ({exec_id}) assigned to {comp.name} in Sector {comp.sector_id:03d}! "
            f"Market penetration boosted to {comp.market_penetration[comp.sector_id]:.1f}%."
        )
        return True, msg, {
            "executive": executive.to_dict(),
            "market_penetration": comp.market_penetration[comp.sector_id],
        }

    def move_sales_executive(
        self,
        captain: Any,
        exec_id: str,
        destination_sector: int,
        kernel: Any = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Dispatches an active Sales Executive to an adjacent connected sector along warp corridors.
        Establishes and expands company market penetration in the target sector.
        """
        exec_id = exec_id.upper().strip()
        if exec_id not in self.executives:
            return False, f"Executive '{exec_id}' not found.", {}

        executive = self.executives[exec_id]
        if executive.owner_id != captain.id:
            return False, "Access Denied: You do not employ this executive.", {}

        if not kernel or destination_sector not in kernel.sectors:
            return False, f"Destination Sector {destination_sector} does not exist.", {}

        curr_sec = kernel.sectors[executive.sector_id]
        if destination_sector not in curr_sec.warps and destination_sector != executive.sector_id:
            return False, f"Sector {destination_sector} is not directly connected to Sector {executive.sector_id:03d} via warp lanes.", {}

        old_sec = executive.sector_id
        executive.sector_id = destination_sector

        comp = self.companies.get(executive.company_ticker)
        new_pen = 0.0
        if comp:
            cur_p = comp.market_penetration.get(destination_sector, 0.0)
            comp.market_penetration[destination_sector] = min(100.0, cur_p + 15.0)
            new_pen = comp.market_penetration[destination_sector]

        msg = (
            f"EXECUTIVE DISPATCHED: {executive.name} navigated from Sector {old_sec:03d} to Sector {destination_sector:03d}! "
            f"{comp.name if comp else 'Company'} market penetration established at {new_pen:.1f}%."
        )
        return True, msg, {
            "exec_id": exec_id,
            "old_sector": old_sec,
            "new_sector": destination_sector,
            "market_penetration": new_pen,
        }

    def launch_marketing_campaign(
        self,
        captain: Any,
        ticker: str,
        campaign_type: str,
        target_ticker: Optional[str] = None,
        kernel: Any = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Launches an interstellar media or PR campaign:
        - POSITIVE: Boosts company consumer trust (+20), share price (+4 Cr), and market penetration (+20%). Cost: 3,000 Cr.
        - SMEAR: Discredits a rival corporation, slashing their consumer trust (-25), crashing their stock (-20%),
                 and eroding their market penetration. Cost: 4,500 Cr.
        """
        ticker = ticker.upper().strip()
        campaign_type = campaign_type.upper().strip()

        if ticker not in self.companies:
            return False, f"Ticker '{ticker}' is not listed on the ISSE.", {}

        comp = self.companies[ticker]
        if comp.chairman_id != captain.id and comp.founder_id != captain.id:
            return False, f"Access Denied: Only Chairman or Founder can launch marketing campaigns for {comp.name}.", {}

        if campaign_type == "POSITIVE":
            cost = 3000
            if captain.credits < cost:
                return False, f"Positive PR blitz requires {cost:,} Credits. You have {captain.credits:,} Cr.", {}

            captain.credits -= cost
            ledger_pay(cost, comp.sector_id)                           # the PR firms of the HQ system
            comp.consumer_trust = min(100, comp.consumer_trust + 20)
            price_bump = random.randint(3, 5)
            comp.share_price += price_bump
            comp.price_history.append(comp.share_price)

            hq_sec = comp.sector_id
            comp.market_penetration[hq_sec] = min(100.0, comp.market_penetration.get(hq_sec, 0.0) + 20.0)

            if kernel and getattr(kernel, "event_bus", None):
                kernel.event_bus.broadcast_radio(
                    sender=comp.name,
                    text=f"MEDIA BLITZ: {comp.name} launches galaxy-wide PR campaign! Consumer trust surged to {comp.consumer_trust}%.",
                    channel="COMM-1",
                    sector_id=comp.sector_id,
                )

            msg = (
                f"POSITIVE PR CAMPAIGN SUCCESSFUL: Boosted {comp.name} consumer trust to {comp.consumer_trust}%! "
                f"Stock price rose +{price_bump} Cr to {comp.share_price} Cr. Market penetration at HQ: {comp.market_penetration[hq_sec]:.1f}%."
            )
            return True, msg, {
                "campaign_type": "POSITIVE",
                "consumer_trust": comp.consumer_trust,
                "share_price": comp.share_price,
                "market_penetration": comp.market_penetration[hq_sec],
            }

        elif campaign_type == "SMEAR":
            cost = 4500
            if not target_ticker:
                return False, "Smear campaigns require a target rival company ticker.", {}

            target_ticker = target_ticker.upper().strip()
            if target_ticker not in self.companies:
                return False, f"Target rival ticker '{target_ticker}' not found on the ISSE.", {}

            if target_ticker == ticker:
                return False, "Cannot launch a smear campaign against your own corporation.", {}

            if captain.credits < cost:
                return False, f"Smear campaign requires {cost:,} Credits. You have {captain.credits:,} Cr.", {}

            captain.credits -= cost
            ledger_pay(cost, comp.sector_id)
            rival = self.companies[target_ticker]

            # Damage rival
            rival.consumer_trust = max(10, rival.consumer_trust - 25)
            pct_drop = random.uniform(0.18, 0.25)
            price_drop = max(3, int(rival.share_price * pct_drop))
            rival.share_price = max(1, rival.share_price - price_drop)
            rival.price_history.append(rival.share_price)

            # Erode rival penetration across sectors
            for s_id in list(rival.market_penetration.keys()):
                rival.market_penetration[s_id] = max(0.0, rival.market_penetration[s_id] - 15.0)

            # Backfire risk if attacker's trust is low
            backfired = False
            if comp.consumer_trust < 40 and random.random() < 0.35:
                backfired = True
                comp.consumer_trust = max(10, comp.consumer_trust - 15)

            if kernel and getattr(kernel, "event_bus", None):
                kernel.event_bus.broadcast_radio(
                    sender="ISSE-NEWS",
                    text=f"INVESTIGATIVE SCANDAL: Whistleblowers expose systemic defects in {rival.name} ({target_ticker}) operations! Shares plunge -{price_drop} Cr!",
                    channel="ALERT",
                    sector_id=rival.sector_id,
                )

            msg = (
                f"SMEAR CAMPAIGN EXECUTED: Discredited rival {rival.name} ({target_ticker})! "
                f"Their consumer trust plummeted to {rival.consumer_trust}% and share price crashed -{price_drop} Cr to {rival.share_price} Cr."
            )
            if backfired:
                msg += f" WARNING: Investigative journalists linked smear back to {comp.name}! Your consumer trust dropped to {comp.consumer_trust}%."

            return True, msg, {
                "campaign_type": "SMEAR",
                "target_ticker": target_ticker,
                "rival_trust": rival.consumer_trust,
                "rival_share_price": rival.share_price,
                "backfired": backfired,
            }

        else:
            return False, f"Unknown campaign type: '{campaign_type}'. Options: POSITIVE, SMEAR.", {}

    def contribute_lobbying(
        self,
        captain: Any,
        amount: int,
        corporate_ticker: Optional[str] = None,
        kernel: Any = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Donates credits into the Interstellar Trade Council lobbying pool to build regulatory influence.
        """
        if amount <= 0:
            return False, "Lobbying contribution must be greater than zero.", {}

        if captain.credits < amount:
            return False, f"Insufficient credits! Contribution requires {amount:,} Cr. You have {captain.credits:,} Cr.", {}

        captain.credits -= amount
        ledger_pay(amount, institution="lobbying")                # the Trade Council's pool sits with the Fed
        entity_id = corporate_ticker.upper().strip() if corporate_ticker else captain.id
        self.trade_council.lobbying_funds[entity_id] = self.trade_council.lobbying_funds.get(entity_id, 0) + amount
        total_influence = self.trade_council.lobbying_funds[entity_id]

        msg = (
            f"LOBBYING CONTRIBUTION RECEIVED: Injected +{amount:,} Cr into Interstellar Trade Council! "
            f"Total Regulatory Influence for '{entity_id}': {total_influence:,} Credits."
        )
        return True, msg, {
            "entity_id": entity_id,
            "amount": amount,
            "total_influence": total_influence,
        }

    def enact_council_resolution(
        self,
        captain: Any,
        bill_type: str,
        target_ticker: Optional[str] = None,
        sponsor_ticker: Optional[str] = None,
        kernel: Any = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Introduces and enacts an Interstellar Trade Council regulatory resolution:
        - SUBSIDY: Grants +5,000 Cr quarterly subsidy to sponsor corporation.
        - TARIFF_SANCTIONS: Imposes 30% tariff sanction on competitor's freight & shipments.
        - CORE_EMBARGO: Bars competitor from trade/freight in Federation Core sectors 1-10.
        Requires at least 2,500 Cr in lobbying pool influence.
        """
        bill_type = bill_type.upper().strip()
        sponsor = sponsor_ticker.upper().strip() if sponsor_ticker else captain.id

        influence = self.trade_council.lobbying_funds.get(sponsor, 0)
        # Also check captain personal influence if sponsor is ticker
        if influence < 2500 and sponsor != captain.id:
            influence = max(influence, self.trade_council.lobbying_funds.get(captain.id, 0))

        if influence < 2500:
            return False, (
                f"Regulatory Influence Insufficient! Enacting Senate bill requires at least 2,500 Cr in lobbying pool. "
                f"Current influence: {influence:,} Cr."
            ), {}

        valid_bills = ["SUBSIDY", "TARIFF_SANCTIONS", "CORE_EMBARGO"]
        if bill_type not in valid_bills:
            return False, f"Unknown resolution type: '{bill_type}'. Valid: {', '.join(valid_bills)}.", {}

        target = target_ticker.upper().strip() if target_ticker else ""
        if bill_type in ["TARIFF_SANCTIONS", "CORE_EMBARGO"] and not target:
            return False, f"Resolution '{bill_type}' requires a target competitor ticker.", {}

        resolution = {
            "bill_type": bill_type,
            "sponsor": sponsor,
            "sponsor_captain": captain.id,
            "target": target,
            "enacted_cycle": kernel.cycle_count if kernel else 1,
            "duration": 50,
        }
        self.trade_council.active_resolutions.append(resolution)
        hist_entry = f"Cycle {resolution['enacted_cycle']}: {bill_type} sponsored by {sponsor} (Target: {target or 'None'})"
        self.trade_council.resolution_history.append(hist_entry)

        if kernel and getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(
                sender="TRADE-COUNCIL",
                text=f"LEGISLATION ENACTED: Interstellar Trade Council passed bill '{bill_type}' sponsored by {sponsor}! Target: {target or 'Sector Net'}.",
                channel="SYSTEM",
                sector_id=1,
            )

        msg = f"TRADE COUNCIL BILL PASSED: '{bill_type}' successfully enacted into federal interstellar law for 50 cycles!"
        return True, msg, {"resolution": resolution, "sponsor": sponsor, "target": target}

    def is_commodity_compatible(self, hull_class: str, commodity: str) -> Tuple[bool, str]:
        """Validates if a specialized hull type has containment support for the specified commodity."""
        hull_cfg = SPECIALIZED_HULLS.get(hull_class)
        if not hull_cfg:
            return False, f"Unknown hull class '{hull_class}'."

        comm_upper = commodity.strip().upper()
        comm_lookup = {k.upper(): k for k in COMMODITY_CONFIG.keys()}
        matched_comm = comm_lookup.get(comm_upper, comm_upper)
        comm_cfg = COMMODITY_CONFIG.get(matched_comm)
        if not comm_cfg:
            return False, f"Unknown commodity '{commodity}'."

        allowed_comms = [c.upper() for c in hull_cfg.get("allowed_commodities", [])]
        if matched_comm.upper() in allowed_comms:
            return True, "Compatible"
        comm_cat = comm_cfg.get("category", "")
        if comm_cat in hull_cfg.get("allowed_categories", []):
            return True, "Compatible"

        return False, f"Hull '{hull_cfg['name']}' ({hull_class}) cannot transport {matched_comm} (Requires specialized containment)."

    def calculate_net_equity(self, captain: Any, kernel: Any = None) -> int:
        """
        Calculates mark-to-market dynamic Net Equity across liquid treasury,
        hull market valuation, cargo hold inventory, corporate equities,
        and planetary infrastructure, less outstanding debt liabilities.
        """
        equity = getattr(captain, "credits", 0)

        # Ship hull valuation
        ship = getattr(captain, "ship", None)
        if ship:
            ship_cfg = hulls.spec(ship)
            equity += ship_cfg.get("price", 1000)

            # Cargo inventory valuation
            cargo = getattr(ship, "cargo", None)
            if cargo:
                c_dict = cargo.to_dict()
                for comm, qty in c_dict.items():
                    if comm in ["cost_basis", "holds", "elements"]:
                        continue
                    if isinstance(qty, (int, float)) and qty > 0:
                        cfg = COMMODITY_CONFIG.get(comm.upper(), {})
                        equity += int(qty * cfg.get("base_price", 10))
                elem_dict = getattr(cargo, "elements", {})
                for elem_name, elem_qty in elem_dict.items():
                    equity += int(elem_qty * 50)

        # Corporate portfolio equities
        port = getattr(captain, "portfolio", {})
        for ticker, shares in port.items():
            comp = self.companies.get(ticker)
            if comp:
                equity += int(shares * comp.share_price)

        # Automated trade haulers fleet value
        for h_id in getattr(captain, "trade_haulers", []):
            h = self.trade_haulers.get(h_id)
            if h:
                h_cfg = SPECIALIZED_HULLS.get(h.hull_class, {})
                equity += h_cfg.get("price", 15000)

        # Colony dominions
        if kernel and hasattr(kernel, "sectors"):
            for s in kernel.sectors.values():
                for p in s.planets:
                    if p.owner_id == captain.id:
                        equity += p.treasury + (p.ore_silo * 5) + (p.organics_silo * 10)

        # Liabilities
        liabilities = getattr(captain, "debt", 0) + getattr(captain, "vc_debt", 0)
        net_equity = max(1000, equity - liabilities)
        return net_equity

    def calculate_borrowing_terms(self, captain: Any, syndicate_id: str, kernel: Any = None) -> Dict[str, Any]:
        """
        Dynamically calculates borrowing terms, credit eligibility,
        dynamic risk-adjusted repayment multipliers, and royalty friction.
        """
        syn = VC_SYNDICATES.get(syndicate_id)
        if not syn:
            return {}

        cr = getattr(captain, "credit_rating", 500)
        exp = getattr(captain, "experience_score", 100)
        net_equity = self.calculate_net_equity(captain, kernel)

        min_cr = syn.get("min_credit_rating", 450)
        min_exp = syn.get("min_experience", 50)
        risk_multiplier = syn.get("risk_multiplier", 1.5)

        # Normalized credit factor on [300, 850] FICO scale
        credit_factor = max(0.05, min(1.0, (cr - 300.0) / 550.0))

        # Dynamic max borrowing ceiling
        max_borrowing_power = int(net_equity * credit_factor * risk_multiplier)

        # Benchmark principal
        base_principal = syn.get("base_principal", syn["principal"])

        # Dynamic royalty rate calculation:
        base_roy = syn.get("royalty_pct", 6.0)
        min_roy = syn.get("min_royalty", 4.0)
        corp_rep = getattr(captain, "faction_reputation", {}).get("Corporate", 50.0)

        # Baseline at CR 500 matches base_roy exactly
        if cr >= 500:
            rep_discount = (corp_rep - 50.0) / 250.0
            dynamic_royalty = max(min_roy, round(base_roy * (1.0 - (cr - 500.0) / 1000.0 - rep_discount), 1))
        else:
            default_penalty = getattr(captain, "default_history", 0) * 1.5
            dynamic_royalty = round(base_roy * (1.0 + (500.0 - cr) / 500.0) + default_penalty, 1)

        # Dynamic debt repayment multiplier
        base_mult = syn.get("multiplier", 1.20)
        if cr >= 500:
            dynamic_multiplier = max(1.10, round(base_mult - (cr - 500.0) / 2500.0, 2))
        else:
            dynamic_multiplier = round(base_mult + (500.0 - cr) / 1000.0, 2)

        # Realistic facility ceiling: equity multiple, revenue multiple, and rank authority all bind
        trailing_revenue = ExperienceManager.trailing_revenue(captain, kernel)
        rank_ceiling = VC_RANK_CEILING.get(getattr(captain, "rank_tier", 1), VC_RANK_CEILING[1])
        facility_ceiling = int(min(
            base_principal,
            max(0, net_equity) * VC_EQUITY_MULTIPLE,
            trailing_revenue * VC_REVENUE_MULTIPLE,
            rank_ceiling,
            max_borrowing_power,
        ))

        eligible = (
            cr >= min_cr and
            exp >= min_exp and
            facility_ceiling >= VC_MIN_PRINCIPAL
        )

        return {
            "syndicate_id": syndicate_id,
            "name": syn["name"],
            "eligible": eligible,
            "min_credit_rating": min_cr,
            "min_experience": min_exp,
            "net_equity": net_equity,
            "credit_rating": cr,
            "credit_factor": credit_factor,
            "max_borrowing_power": max_borrowing_power,
            "facility_ceiling": facility_ceiling,
            "trailing_revenue": trailing_revenue,
            "rank_ceiling": rank_ceiling,
            "base_principal": base_principal,
            "royalty_pct": dynamic_royalty,
            "multiplier": dynamic_multiplier,
            "description": syn["description"],
        }

    def apply_vc_funding(
        self,
        captain: Any,
        syndicate_id: str,
        kernel: Any = None,
        amount: Optional[int] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Secures venture debt-equity financing from an interstellar syndicate at Sector 1 Stardock."""
        syn = VC_SYNDICATES.get(syndicate_id)
        if not syn:
            return False, f"Unknown Venture Capital Syndicate: '{syndicate_id}'.", {}

        if getattr(captain, "vc_debt", 0) > 0:
            return False, f"Active venture covenant with {captain.vc_active_syndicate} ({captain.vc_debt:,} Cr outstanding). You must settle all existing venture debt before applying for new financing.", {}

        if kernel and hasattr(captain, "sector_id") and captain.sector_id != 1:
            return False, "Venture Capital syndicates only negotiate funding at the Sector 001 Stardock Investment Desk.", {}

        terms = self.calculate_borrowing_terms(captain, syndicate_id, kernel)
        cr = getattr(captain, "credit_rating", 500)
        exp = getattr(captain, "experience_score", 100)

        # Check Credit Rating prerequisite
        if cr < syn.get("min_credit_rating", 450):
            return False, (
                f"CREDIT APPLICATION REJECTED: {syn['name']} risk model requires a minimum Credit Rating of "
                f"{syn['min_credit_rating']} (Your Rating: {cr} - {getattr(captain, 'credit_tier', 'Subprime')})."
            ), {"terms": terms}

        # Check Experience Score prerequisite
        if exp < syn.get("min_experience", 50):
            return False, (
                f"EXPERIENCE PREREQUISITE UNMET: {syn['name']} requires an established commercial track record "
                f"of at least {syn['min_experience']} Experience (Ξ) (Your Experience: {exp} Ξ)."
            ), {"terms": terms}

        # Check leverage limits
        base_principal = syn["principal"]
        max_power = terms["max_borrowing_power"]

        # Facility is sized to the captain's verified standing, never to the syndicate's headline size
        facility = terms["facility_ceiling"]
        if facility < VC_MIN_PRINCIPAL:
            return False, (
                f"INSUFFICIENT TRACK RECORD: {syn['name']} sizes facilities to verified standing. "
                f"Your ceiling is {facility:,} Cr (equity {terms['net_equity']:,} Cr, trailing revenue "
                f"{terms['trailing_revenue']:,} Cr, rank ceiling {terms['rank_ceiling']:,} Cr); "
                f"minimum allocation is {VC_MIN_PRINCIPAL:,} Cr."
            ), {"terms": terms}
        requested = amount if (amount is not None and amount > 0) else base_principal
        if amount is not None and amount > facility:
            return False, (
                f"EXCESSIVE LEVERAGE REJECTED: Syndicate credit model limits your facility to {facility:,} Cr. "
                f"Requested: {amount:,} Cr."
            ), {"terms": terms}
        principal = min(requested, facility)

        multiplier = terms["multiplier"]
        royalty = terms["royalty_pct"]
        debt_total = int(principal * multiplier)

        captain.credits += principal
        captain.vc_active_syndicate = syndicate_id
        captain.vc_debt = debt_total
        captain.vc_royalty_pct = royalty
        captain.vc_principal_paid = 0

        msg = (
            f"VENTURE CAPITAL SECURED: {syn['name']} injected {principal:,} Cr into your treasury! "
            f"Covenant Terms: {debt_total:,} Cr total debt repayment ({multiplier:.2f}x principal) "
            f"via {royalty:.1f}% automated trade route profit royalties."
        )
        if kernel and hasattr(kernel, "event_bus") and kernel.event_bus:
            kernel.event_bus.broadcast_radio(
                sender="STARDOCK-VC",
                text=f"INVESTMENT DEAL: {captain.name} closed {principal:,} Cr financing round with {syn['name']}!",
                channel="COMM-1",
                sector_id=1,
            )
        return True, msg, {"syndicate": syn, "principal": principal, "debt": debt_total, "terms": terms}

    def repay_vc_debt(self, captain: Any, amount: int, kernel: Any = None) -> Tuple[bool, str, Dict[str, Any]]:
        """Voluntarily repays outstanding Venture Capital debt from captain credits."""
        if getattr(captain, "vc_debt", 0) <= 0:
            return False, "You do not have any active Venture Capital debt.", {}

        if amount <= 0:
            return False, "Repayment amount must be greater than zero.", {}

        actual = min(amount, captain.vc_debt)
        if captain.credits < actual:
            return False, f"Insufficient credits! Requires {actual:,} Cr to make this debt payment, but you have {captain.credits:,} Cr.", {}

        captain.credits -= actual
        captain.vc_debt -= actual
        captain.vc_principal_paid = getattr(captain, "vc_principal_paid", 0) + actual

        if captain.vc_debt <= 0:
            captain.vc_debt = 0
            settled_name = captain.vc_active_syndicate
            captain.vc_active_syndicate = None
            captain.vc_royalty_pct = 0.0
            captain.loan_repayment_history = getattr(captain, "loan_repayment_history", 0) + 1
            if hasattr(captain, "adjust_credit_rating"):
                captain.adjust_credit_rating(35, reason=f"Discharged VC debt with {settled_name}")
                captain.adjust_experience(50)
                captain.adjust_reputation("Corporate", 5.0)
            msg = f"VC DEBT FULLY DISCHARGED: Paid {actual:,} Cr. All debt covenants with {settled_name} have been satisfied in full! (+35 Credit Rating, +50 Experience)"
        else:
            if hasattr(captain, "adjust_credit_rating"):
                captain.adjust_credit_rating(max(1, actual // 10000), reason="VC debt installment")
                captain.adjust_experience(max(10, actual // 2000))
                captain.adjust_reputation("Corporate", 1.0)
            msg = f"VC DEBT PAYMENT: Paid {actual:,} Cr towards {captain.vc_active_syndicate}. Remaining debt balance: {captain.vc_debt:,} Cr."

        return True, msg, {"repaid": actual, "debt_remaining": captain.vc_debt}

    def assign_hauler_escort(
        self,
        captain: Any,
        hauler_id: str,
        count: int,
        mode: str = "assign"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Assigns or recalls combat escort fighter wings to/from a trade hauler."""
        hauler = self.trade_haulers.get(hauler_id)
        if not hauler:
            return False, f"Trade Hauler '{hauler_id}' not found.", {}
        if hauler.owner_id != captain.id:
            return False, "Access Denied: You do not own this trade hauler.", {}
        if count <= 0:
            return False, "Fighter wing count must be greater than zero.", {}

        mode = mode.lower()
        if mode == "assign":
            if captain.ship.fighters < count:
                return False, f"Insufficient shipboard fighters! Flagship has {captain.ship.fighters} fighters, requested {count}.", {}
            captain.ship.fighters -= count
            hauler.escort_fighters += count
            msg = f"ESCORT ASSIGNED: Transferred {count} fighter wings to {hauler.name} (Total escort: {hauler.escort_fighters})."
        elif mode == "recall":
            if hauler.escort_fighters < count:
                return False, f"Hauler only has {hauler.escort_fighters} escort fighters deployed.", {}
            hauler.escort_fighters -= count
            max_f = getattr(captain.ship, "max_fighters", hulls.spec(captain.ship).get("max_fighters", 100))
            captain.ship.fighters = min(max_f, captain.ship.fighters + count)
            msg = f"ESCORT RECALLED: Recovered {count} fighter wings from {hauler.name} to flagship."
        else:
            return False, f"Invalid mode '{mode}'. Choose 'assign' or 'recall'.", {}

        return True, msg, {"escort_fighters": hauler.escort_fighters, "ship_fighters": captain.ship.fighters}

    def recall_hauler(
        self,
        captain: Any,
        hauler_id: str,
        target_sector: int = 1,
        kernel: Any = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Recalls or halts a trade hauler, ordering it to target sector or pausing operation."""
        hauler = self.trade_haulers.get(hauler_id)
        if not hauler:
            return False, f"Trade Hauler '{hauler_id}' not found.", {}
        if hauler.owner_id != captain.id:
            return False, "Access Denied: You do not own this trade hauler.", {}

        if hauler.sector_id == target_sector:
            hauler.status = "IDLE"
            hauler.active = False
            hauler.current_path = []
            msg = f"FLEET STAND-DOWN: {hauler.name} stationed in Sector {target_sector:03d} (Status: IDLE)."
        else:
            hauler.status = "RETREAT"
            hauler.active = False
            if kernel and hasattr(kernel, "find_path"):
                path = kernel.find_path(hauler.sector_id, target_sector)
                hauler.current_path = path[1:] if len(path) > 1 else [target_sector]
            msg = f"FLEET RECALL: {hauler.name} ordered to withdraw to Sector {target_sector:03d} (Status: RETREAT)."

        return True, msg, {"hauler": hauler.to_dict()}

    def commission_trade_hauler(
        self,
        captain: Any,
        name: Optional[str] = None,
        origin: int = 1,
        dest: int = 30,
        outbound: str = "EQUIPMENT",
        return_comm: str = "ORGANICS",
        hull_class: str = "STANDARD",
        kernel: Any = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Commissions an automated merchant trade hauler to run autonomous circular trade routes.
        Supports specialized hull classes (STANDARD, CRYO_TANKER, BULK_FREIGHTER, BIOSPHERE_VESSEL, QUANTUM_SKIFF).
        """
        if hull_class not in SPECIALIZED_HULLS:
            hull_class = "STANDARD"

        hull_info = SPECIALIZED_HULLS[hull_class]
        cost = hull_info["price"]
        capacity = hull_info["holds"]

        if captain.credits < cost:
            return False, f"Commissioning a {hull_info['name']} requires {cost:,} Credits. You have {captain.credits:,} Cr.", {}

        fleet_size = sum(1 for h in self.trade_haulers.values() if h.owner_id == captain.id and h.active)
        if fleet_size >= MAX_TRADE_HAULERS_PER_CAPTAIN:
            return False, f"Fleet registry full: captains may operate at most {MAX_TRADE_HAULERS_PER_CAPTAIN} trade haulers.", {}

        # Cargo compatibility check
        ok_out, reason_out = self.is_commodity_compatible(hull_class, outbound)
        if not ok_out:
            return False, f"Outbound Cargo Incompatible: {reason_out}", {}
        ok_ret, reason_ret = self.is_commodity_compatible(hull_class, return_comm)
        if not ok_ret:
            return False, f"Return Cargo Incompatible: {reason_ret}", {}

        if kernel and hasattr(kernel, "sectors"):
            sec_a = kernel.sectors.get(origin)
            sec_b = kernel.sectors.get(dest)
            if not sec_a or not sec_a.port:
                return False, f"Origin Sector {origin:03d} does not have a commercial spaceport.", {}
            if not sec_b or not sec_b.port:
                return False, f"Destination Sector {dest:03d} does not have a commercial spaceport.", {}
            if origin == dest:
                return False, "Origin and Destination sectors must be different.", {}

        captain.credits -= cost
        ledger_pay(cost, 1)                                        # Sol Stardock's yards build the hull
        hid = f"HAUL-{self.next_hauler_id}"
        self.next_hauler_id += 1

        hauler_name = name.strip() if name and name.strip() else f"{hull_info['name']} {hid}"

        # Calculate initial route path
        path = []
        if kernel and hasattr(kernel, "find_path"):
            calc_path = kernel.find_path(origin, dest)
            if len(calc_path) > 1:
                path = calc_path[1:]

        hauler = TradeHauler(
            id=hid,
            owner_id=captain.id,
            name=hauler_name,
            sector_id=origin,
            hull_class=hull_class,
            status="IN_TRANSIT" if path else "IDLE",
            capacity=capacity,
            origin_sector=origin,
            dest_sector=dest,
            commodity_outbound=outbound.strip(),
            commodity_return=return_comm.strip(),
            cargo={},
            escort_fighters=0,
            wear_and_tear=0,
            current_path=path,
            lifetime_profit=0,
            trips_completed=0,
            active=True,
        )
        self.trade_haulers[hid] = hauler

        cap_haulers = getattr(captain, "trade_haulers", [])
        cap_haulers.append(hid)
        captain.trade_haulers = cap_haulers

        msg = (
            f"AUTOMATED TRADE HAULER COMMISSIONED: '{hauler_name}' ({hid}) launched into service! "
            f"Hull: {hull_info['name']} ({capacity} holds). "
            f"Route: Sector {origin:03d} ◄──► Sector {dest:03d} ({outbound}/{return_comm})."
        )
        return True, msg, {"hauler": hauler.to_dict()}

    def assign_hauler_route(
        self,
        captain: Any,
        hauler_id: str,
        origin: int,
        dest: int,
        outbound: str,
        return_comm: str,
        kernel: Any = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Reassigns a trade hauler's designated circular route and cargo manifest with compatibility check."""
        hauler = self.trade_haulers.get(hauler_id)
        if not hauler:
            return False, f"Trade Hauler '{hauler_id}' not found.", {}

        if hauler.owner_id != captain.id:
            return False, "Access Denied: You do not own this trade hauler.", {}

        # Cargo compatibility check
        ok_out, reason_out = self.is_commodity_compatible(hauler.hull_class, outbound)
        if not ok_out:
            return False, f"Outbound Cargo Incompatible: {reason_out}", {}
        ok_ret, reason_ret = self.is_commodity_compatible(hauler.hull_class, return_comm)
        if not ok_ret:
            return False, f"Return Cargo Incompatible: {reason_ret}", {}

        if kernel and hasattr(kernel, "sectors"):
            sec_a = kernel.sectors.get(origin)
            sec_b = kernel.sectors.get(dest)
            if not sec_a or not sec_a.port:
                return False, f"Origin Sector {origin:03d} has no spaceport.", {}
            if not sec_b or not sec_b.port:
                return False, f"Destination Sector {dest:03d} has no spaceport.", {}
            if origin == dest:
                return False, "Origin and Destination must be distinct sectors.", {}

        hauler.origin_sector = origin
        hauler.dest_sector = dest
        hauler.commodity_outbound = outbound.strip()
        hauler.commodity_return = return_comm.strip()
        hauler.active = True

        if kernel and hasattr(kernel, "find_path"):
            path = kernel.find_path(hauler.sector_id, dest)
            hauler.current_path = path[1:] if len(path) > 1 else [dest]
            hauler.status = "IN_TRANSIT"

        msg = f"ROUTE REASSIGNED: {hauler.name} ({hauler_id}) now flying Sector {origin:03d} ◄──► Sector {dest:03d} ({hauler.commodity_outbound}/{hauler.commodity_return})."
        return True, msg, {"hauler": hauler.to_dict()}

    def decommission_trade_hauler(
        self,
        captain: Any,
        hauler_id: str,
        kernel: Any = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Decommissions and scraps a trade hauler for 50% scrap value."""
        hauler = self.trade_haulers.get(hauler_id)
        if not hauler:
            return False, f"Trade Hauler '{hauler_id}' not found.", {}

        if hauler.owner_id != captain.id:
            return False, "Access Denied: You do not own this trade hauler.", {}

        hull_info = SPECIALIZED_HULLS.get(hauler.hull_class, {})
        base_cost = hull_info.get("price", 4000)
        refund = base_cost // 2

        # Return escort fighters to captain flagship
        if hauler.escort_fighters > 0 and hasattr(captain, "ship"):
            max_f = getattr(captain.ship, "max_fighters", hulls.spec(captain.ship).get("max_fighters", 100))
            captain.ship.fighters = min(max_f, captain.ship.fighters + hauler.escort_fighters)

        # The Stardock buys the hull back out of its own treasury (it cannot pay what it does not have)
        yard = kernel_sector_port(1)
        if yard is not None:
            refund = min(refund, max(0, ledger_sol_of(yard)))
            ledger_debit_port_sol(yard, refund)
        else:
            refund = 0
        captain.credits += refund
        del self.trade_haulers[hauler_id]

        cap_haulers = getattr(captain, "trade_haulers", [])
        if hauler_id in cap_haulers:
            cap_haulers.remove(hauler_id)
            captain.trade_haulers = cap_haulers

        msg = f"HAULER DECOMMISSIONED: {hauler.name} ({hauler_id}) scrapped at orbital dock. Recovered +{refund:,} Credits."
        return True, msg, {"refund": refund}

    @staticmethod
    def _hauler_leg(owner: Any, src: Any, dst: Any, comm: str, capacity: int) -> float:
        """
        One automated trade leg: buy at ``src`` and sell at ``dst``, settling through both
        ports' treasuries in their own currencies. Returns realized profit in SOL value.
        """
        from xylarium.kernel.economy import EconomyManager
        from xylarium.kernel import fx
        if not (src.sells.get(comm, False) and dst.buys.get(comm, False)) or src.stock.get(comm, 0) < 5:
            return 0.0
        _, buy_p = EconomyManager.get_unit_prices(src, comm)
        sell_p, _ = EconomyManager.get_unit_prices(dst, comm)
        market = fx.ACTIVE_FX
        to_sol = (lambda cur, amt: market.to_sol_value(cur, amt)) if market else (lambda cur, amt: amt)
        if to_sol(dst.currency, sell_p) <= to_sol(src.currency, buy_p) or buy_p <= 0 or sell_p <= 0:
            return 0.0
        units = min(capacity * get_commodity_stack_multiplier(comm), src.stock[comm], dst.treasury // sell_p)
        if units <= 0:
            return 0.0
        cost = buy_p * units
        if market and src.currency != "SOL":
            if not market.ensure_local(owner, src.currency, cost):
                return 0.0
        elif owner.credits < cost:
            return 0.0
        fx.debit(owner, src.currency, cost)
        src.treasury += cost
        revenue = sell_p * units
        dst.treasury -= revenue
        fx.credit(owner, dst.currency, revenue)
        src.stock[comm] -= units
        dst.stock[comm] = dst.stock.get(comm, 0) + units
        return to_sol(dst.currency, revenue) - to_sol(src.currency, cost)

    def tick_trade_haulers(self, kernel: Any) -> List[str]:
        """Runs automated commercial circuits for all active trade haulers with waypoint travel, escort combat, and VC royalties."""
        from xylarium.kernel.economy import EconomyManager

        logs = []
        if not kernel or not hasattr(kernel, "sectors"):
            return logs

        for hauler in list(self.trade_haulers.values()):
            if not hauler.active or hauler.status == "IDLE":
                continue

            # Mechanical Wear and Tear (+1 per tick, 500 Cr maintenance every 50 cycles)
            hauler.wear_and_tear += 1
            if hauler.wear_and_tear % 50 == 0:
                owner = kernel.captains.get(hauler.owner_id)
                if owner:
                    if owner.credits >= 500:
                        owner.credits -= 500
                        ledger_pay(500, getattr(hauler, "current_sector", None))   # the yard that did the overhaul
                        logs.append(f"MAINTENANCE OVERHAUL: Deducted 500 Cr for scheduled maintenance on {hauler.name}.")
                    else:
                        hauler.status = "IDLE"
                        hauler.active = False
                        logs.append(f"MAINTENANCE SUSPENSION: {hauler.name} docked IDLE due to insufficient funds (500 Cr needed).")
                        continue

            # Waypoint Navigation along current_path
            if hauler.current_path:
                next_sec = hauler.current_path.pop(0)
                hauler.sector_id = next_sec
                hauler.status = "IN_TRANSIT"

                # Check Pirate Ambush in ANARCHY / BORDERLAND
                sec_obj = kernel.sectors.get(next_sec)
                if sec_obj:
                    sec_type = getattr(sec_obj.security, "value", str(sec_obj.security))
                    is_anarchy = "ANARCHY" in sec_type
                    is_border = "BORDERLAND" in sec_type
                    ambush_chance = 0.20 if is_anarchy else (0.08 if is_border else 0.0)

                    if random.random() < ambush_chance:
                        if hauler.escort_fighters > 0:
                            lost = min(hauler.escort_fighters, random.randint(1, 2))
                            hauler.escort_fighters -= lost
                            hauler.status = "COMBAT"
                            logs.append(f"TACTICAL ESCORT ENGAGED: {hauler.name} repelled pirates in Sector {next_sec:03d}! Lost {lost} fighters ({hauler.escort_fighters} remaining).")
                        else:
                            hauler.wear_and_tear += 5
                            hauler.status = "UNDER_ATTACK"
                            if hauler.cargo:
                                raided_comm = next(iter(hauler.cargo))
                                raided_qty = hauler.cargo.pop(raided_comm)
                                logs.append(f"PIRATE RAID ALERT: Unescorted {hauler.name} was raided in Sector {next_sec:03d}! Lost {raided_qty} units of {raided_comm}!")
                            else:
                                logs.append(f"PIRATE RAID ALERT: Unescorted {hauler.name} sustained hull damage from raiders in Sector {next_sec:03d} (+5 Wear).")

            # Arrived at destination/origin or path finished
            if not hauler.current_path:
                if hauler.status == "RETREAT":
                    hauler.status = "IDLE"
                    logs.append(f"RECALL COMPLETED: {hauler.name} safely arrived at stand-down Sector {hauler.sector_id:03d}.")
                    continue

                sec_a = kernel.sectors.get(hauler.origin_sector)
                sec_b = kernel.sectors.get(hauler.dest_sector)
                if not sec_a or not sec_b or not sec_a.port or not sec_b.port:
                    continue

                port_a = sec_a.port
                port_b = sec_b.port

                owner = kernel.captains.get(hauler.owner_id)
                if owner is None:
                    continue
                # Both legs settle through the ports' treasuries in their own currencies
                profit_ab = self._hauler_leg(owner, port_a, port_b, hauler.commodity_outbound, hauler.capacity)
                profit_ba = self._hauler_leg(owner, port_b, port_a, hauler.commodity_return, hauler.capacity)

                total_profit = profit_ab + profit_ba
                if total_profit > 0:
                    hauler.lifetime_profit += total_profit
                    hauler.trips_completed += 1
                    if owner:
                        # VC Royalty Skim: the syndicate is paid out of the owner's SOL proceeds
                        royalty_cut = 0
                        if getattr(owner, "vc_debt", 0) > 0 and getattr(owner, "vc_royalty_pct", 0) > 0:
                            royalty_cut = int(total_profit * (owner.vc_royalty_pct / 100.0))
                            royalty_cut = max(0, min(royalty_cut, owner.vc_debt, owner.credits))
                            owner.credits -= royalty_cut
                            owner.vc_debt -= royalty_cut
                            owner.vc_principal_paid = getattr(owner, "vc_principal_paid", 0) + royalty_cut
                            if owner.vc_debt == 0:
                                settled_syn = owner.vc_active_syndicate
                                owner.vc_active_syndicate = None
                                owner.vc_royalty_pct = 0.0
                                owner.loan_repayment_history = getattr(owner, "loan_repayment_history", 0) + 1
                                if hasattr(owner, "adjust_credit_rating"):
                                    owner.adjust_credit_rating(35, reason=f"Discharged VC debt with {settled_syn}")
                                    ExperienceManager.award(owner, "commerce", 10, kernel, key=f"vc_settle:{settled_syn}")
                                    owner.adjust_reputation("Corporate", 5.0)
                                logs.append(f"VC DEBT SETTLED: {hauler.name} yield settled all debt covenants with {settled_syn}!")

                        net_profit = int(total_profit - royalty_cut)
                        ExperienceManager.record_revenue(owner, net_profit, kernel)
                        owner.score += max(5, net_profit // 25)
                        owner.freight_deliveries_completed = getattr(owner, "freight_deliveries_completed", 0) + 1
                        ExperienceManager.award(owner, "commerce", 1, kernel, key=f"hauler:{hauler.id}")
                        owner.adjust_credit_rating(1, reason=f"Hauler {hauler.name} profitable trade")

                        royalty_str = f" [VC Royalty Skim: -{royalty_cut:,} Cr]" if royalty_cut > 0 else ""
                        log_text = f"AUTOMATED FLEET YIELD: {hauler.name} completed route {hauler.origin_sector:03d}◄──►{hauler.dest_sector:03d}, generating +{net_profit:,} Cr!{royalty_str}"
                        logs.append(log_text)
                        if hasattr(kernel, "action_logs"):
                            kernel.action_logs.append(log_text)

                # Set next leg path
                if kernel and hasattr(kernel, "find_path"):
                    target_dest = hauler.dest_sector if hauler.sector_id == hauler.origin_sector else hauler.origin_sector
                    path = kernel.find_path(hauler.sector_id, target_dest)
                    hauler.current_path = path[1:] if len(path) > 1 else []
                    hauler.status = "IN_TRANSIT"


    def _revalue_shares(self, kernel: Any = None) -> None:
        from xylarium.config import SHARE_REVERSION
        from xylarium.kernel import liquidation
        for comp in self.companies.values():
            # what it is worth: the greater of its estate and its estate plus its earnings (liquidation.valuation)
            fair = max(1.0, liquidation.fair_price(kernel, comp)) if kernel is not None else float(comp.share_price)
            new_price = max(1, int(round(comp.share_price + SHARE_REVERSION * (fair - comp.share_price))))
            if new_price != comp.share_price:
                comp.share_price = new_price
                comp.price_history.append(comp.share_price)

    def tick_market(self, kernel: Any) -> Dict[str, Any]:
        """
        Advances market cycle:
        1. Checks contract expirations.
        2. Spawns population enterprises on expanding colonies.
        3. Generates new freight listings.
        4. Advances sales executives market penetration & regional revenues.
        5. Runs automated trade fleet haulers.
        6. Advances Trade Council resolutions and subsidies.
        7. Distributes quarterly dividends every FISCAL_QUARTER_CYCLES (25 cycles).
        """
        current_cycle = kernel.cycle_count
        expired_contracts = []
        # Fundamentals: each quarter, share prices revert toward book value plus annualized revenue,
        # so momentum (deliveries, PR, buying pressure) can't inflate a paper-wealth bubble forever
        if current_cycle > 0 and current_cycle % FISCAL_QUARTER_CYCLES == 0:
            self._revalue_shares(kernel)
        fleet_logs = self.tick_trade_haulers(kernel)

        # 1. Contract expiration check
        for cid, contract in list(self.contracts.items()):
            if contract.status in ["OPEN", "IN_TRANSIT"] and current_cycle > contract.expiry_cycle:
                self.void_contract(contract, kernel)
                expired_contracts.append(cid)
                comp = self.companies.get(contract.company_ticker)
                if comp:
                    comp.share_price = max(1, comp.share_price - 1)
                    comp.price_history.append(comp.share_price)

        # Prune settled contracts once past their retention window so the board stays bounded
        for cid, contract in list(self.contracts.items()):
            if contract.status in ("COMPLETED", "EXPIRED") and current_cycle > contract.expiry_cycle + CONTRACT_RETENTION_CYCLES:
                del self.contracts[cid]

        # Bound per-company chart history and council archives (both ship in every player view)
        for comp in self.companies.values():
            if len(comp.price_history) > PRICE_HISTORY_RETENTION:
                del comp.price_history[:-PRICE_HISTORY_RETENTION]
        if len(self.trade_council.resolution_history) > RESOLUTION_HISTORY_RETENTION:
            del self.trade_council.resolution_history[:-RESOLUTION_HISTORY_RETENTION]

        # 2. Spawn population enterprises
        new_enterprises = self.spawn_population_enterprises(kernel)

        # 3. Replenish freight contracts (corporate board + colony import orders)
        self._kernel_ref = kernel
        new_freight = self.generate_freight_contracts(kernel)
        new_freight += self.generate_colony_imports(kernel)
        new_freight += self.generate_extraction_contracts(kernel)

        # 4. Advance sales executives market penetration & regional commercial revenues
        for ex in self.executives.values():
            if ex.active and ex.company_ticker in self.companies:
                comp = self.companies[ex.company_ticker]
                sec_p = comp.market_penetration.get(ex.sector_id, 0.0)
                comp.market_penetration[ex.sector_id] = min(100.0, sec_p + 10.0)
                # Suppress rival corporations in the sector
                for r_ticker, r_comp in self.companies.items():
                    if r_ticker != comp.ticker and ex.sector_id in r_comp.market_penetration:
                        r_comp.market_penetration[ex.sector_id] = max(0.0, r_comp.market_penetration[ex.sector_id] - 5.0)
                # Regional sales penetration boosts corporate revenue
                comp.quarterly_revenue += int(comp.market_penetration[ex.sector_id] * 25)

        # 5. Fiscal Quarter Dividends, Council Subsidies, and Earnings Audit (every 25 cycles)
        dividends_paid = 0
        is_quarter_end = (current_cycle > 0 and current_cycle % FISCAL_QUARTER_CYCLES == 0)

        # Process Trade Council resolutions
        for res in list(self.trade_council.active_resolutions):
            res["duration"] = res.get("duration", 50) - 1
            if res["duration"] <= 0:
                self.trade_council.active_resolutions.remove(res)
                if kernel and getattr(kernel, "event_bus", None):
                    kernel.event_bus.broadcast_radio(
                        sender="TRADE-COUNCIL",
                        text=f"BILL EXPIRED: Regulatory resolution '{res['bill_type']}' (Sponsor: {res['sponsor']}) has reached sunset expiration.",
                        channel="SYSTEM",
                        sector_id=1,
                    )
            elif is_quarter_end and res.get("bill_type") == "SUBSIDY":
                sponsor = res.get("sponsor")
                fed = getattr(kernel, "federal_reserve", None)
                if sponsor in self.companies and fed is not None:
                    subsidy = min(TRADE_COUNCIL_SUBSIDY, fed.treasury)
                    fed.treasury -= subsidy
                    fed.stats["council_subsidies"] += subsidy
                    self.companies[sponsor].treasury += subsidy
                    self.companies[sponsor].quarterly_revenue += subsidy

        if is_quarter_end:
            # (households buy their basket from regional ports in demography.households)
            self._port_retail(kernel)
            self._company_operating_spend(kernel)
            self._port_operating_costs(kernel)
            # (ISSE reserve disorder is now corrected by the federations' central banks - banking.py)
            from xylarium.kernel import enterprise
            firms = enterprise.stats(kernel)["firms"]
            from xylarium.kernel import liquidation
            for ticker, comp in self.companies.items():
                if ticker in firms or liquidation.distressed(kernel, ticker):
                    continue      # a firm earns what it sells; a distressed company receives nothing it has not earned
                # Operating income is real: the home colony buys the company's goods & services
                # (a transfer from the colony vault). quarterly_revenue stays a reporting figure.
                home = kernel.get_planet(comp.planet_id) if getattr(comp, "planet_id", None) else None
                sales = 0
                local = 0
                if home is not None and home.treasury > 0:
                    local = min(int(home.treasury * COMPANY_COLONY_SALES_RATE),
                                int(COMPANY_COLONY_SALES_CAP * self._local_price_level(home.currency)))
                    home.treasury -= local
                    # A firm keeps its operating books in the money it earns: no conversion
                    comp.home_currency = home.currency
                    comp.home_cash += local
                    from xylarium.kernel.fx import ACTIVE_FX
                    sales = int(ACTIVE_FX.to_sol_value(home.currency, local)) if (ACTIVE_FX and home.currency != "SOL") else local
                comp.quarterly_revenue += sales
                div_local = int(local * comp.dividend_rate)
                comp.last_outflow_q = getattr(comp, "last_outflow_q", 0) + int(sales * comp.dividend_rate)
                comp.last_dividend = round(int(sales * comp.dividend_rate) / max(1, comp.total_shares))
                comp.quarterly_revenue = 0  # Reset for next quarter
                # Dividends are paid in the home money, pro rata, into the shareholders' wallets
                if div_local > 0 and comp.home_currency:
                    from xylarium.kernel.fx import credit as fx_credit
                    for cap in kernel.captains.values():
                        shares = getattr(cap, "portfolio", {}).get(ticker, 0)
                        if shares <= 0:
                            continue
                        payout = min(div_local * shares // max(1, comp.total_shares), comp.home_cash)
                        if payout <= 0:
                            break
                        comp.home_cash -= payout
                        fx_credit(cap, comp.home_currency, payout)
                        dividends_paid += int(ACTIVE_FX.to_sol_value(comp.home_currency, payout)) if (ACTIVE_FX and comp.home_currency != "SOL") else payout
                div_pool = 0

                # Disburse the dividend pool pro rata to captains holding shares, out of the company treasury
                if div_pool > 0:
                    for cap in kernel.captains.values():
                        port = getattr(cap, "portfolio", {})
                        shares = port.get(ticker, 0)
                        if shares > 0:
                            payout = min(div_pool * shares // max(1, comp.total_shares), comp.treasury)
                            if payout <= 0:
                                break
                            comp.treasury -= payout
                            cap.credits += payout
                            dividends_paid += payout
                            ExperienceManager.record_revenue(cap, payout, kernel)

                # Company growth: If fulfilled multiple contracts, level up
                if comp.contracts_fulfilled >= comp.level * 3 and comp.level < 4:
                    comp.level += 1
                    comp.share_price += 10
                    comp.price_history.append(comp.share_price)
                    if kernel.event_bus:
                        kernel.event_bus.broadcast_radio(
                            sender=comp.name,
                            text=f"CORPORATE EXPANSION: {comp.name} ({comp.ticker}) has advanced to Tier {comp.level}: {comp.level_title}!",
                            channel="COMM-1",
                            sector_id=comp.sector_id,
                        )

        # 6. Corporate Fleet & Bounty Spawning (Vector 3)
        corp_spawned = self.check_corporate_and_bounty_spawning(kernel)

        return {
            "is_quarter_end": is_quarter_end,
            "dividends_paid": dividends_paid,
            "new_enterprises": new_enterprises,
            "new_freight_count": len(new_freight),
            "expired_contracts": expired_contracts,
            "corporate_spawned": corp_spawned,
        }

    def check_corporate_and_bounty_spawning(self, kernel: Any) -> List[str]:
        """
        Vector 3: Corporate Fleet & Bounty Hunter Spawning.
        - When an ISSE corporation's liquid treasury >= 50,000 Cr, commissions a corporate enforcer / patrol ship.
        - When pirate threat spikes or uncollected bounties mount, Sol Federation commissions independent Bounty Hunters.
        """
        from xylarium.kernel import populace
        if not kernel or not populace.room_for_captain(kernel):
            return []

        spawned_names = []

        # 1. Corporate Enforcers
        for comp in self.companies.values():
            if not populace.room_for_captain(kernel):
                break

            if comp.treasury >= CORPORATE_ENFORCER_TREASURY:
                last_commission = getattr(comp, "last_enforcer_cycle", -999)
                if kernel.cycle_count - last_commission < CORPORATE_ENFORCER_COOLDOWN:
                    continue

                active_id = getattr(comp, "active_enforcer_id", None)
                if active_id and active_id in kernel.captains:
                    continue

                # Deduct commission cost plus the enforcer's operating float (a transfer, not new money)
                comp.treasury -= CORPORATE_ENFORCER_COST + 5000
                ledger_pay(CORPORATE_ENFORCER_COST, comp.sector_id)   # the yard that builds the enforcer
                comp.last_enforcer_cycle = kernel.cycle_count

                sec_id = comp.sector_id if comp.sector_id in kernel.sectors else 1
                enforcer_id = f"corp_{comp.ticker.lower()}_{kernel.cycle_count}"
                comp.active_enforcer_id = enforcer_id

                ship_class = "Star Frigate"
                ship_cfg = SHIP_CATALOG.get(ship_class, SHIP_CATALOG["Scout Ship"])
                cargo = CargoHold(capacity=ship_cfg["holds"])
                cargo.ore = 20
                cargo.elements["Si"] = 15

                personality = AIPersonality.MERCENARY if comp.industry in ["MINING", "MANUFACTURING"] else AIPersonality.TRADER
                enforcer_name = f"{comp.ticker} Enforcer {kernel.cycle_count % 100:02d}"

                corp_cap = Captain(
                    id=enforcer_id,
                    name=enforcer_name,
                    is_ai=True,
                    personality=personality,
                    credits=5000,
                    sector_id=sec_id,
                    species="bimaniform-flatlander",
                    metabolism="mineral",
                    clade="BIOTIC",
                    rank_tier=2,
                    turns_left=200,
                    ship=Ship(
                        ship_type=ship_class,
                        cargo=cargo,
                        shields=ship_cfg["max_shields"],
                        max_shields=ship_cfg["max_shields"],
                        fighters=ship_cfg["max_fighters"],
                    )
                )

                kernel.captains[enforcer_id] = corp_cap
                matter.commission(corp_cap)
                if sec_id in kernel.sectors:
                    kernel.sectors[sec_id].captains.append(enforcer_id)

                if getattr(kernel, "event_bus", None):
                    event_bus = getattr(kernel, "event_bus", None)
                    event_bus.broadcast_radio(
                        sender=comp.name,
                        text=f"CORPORATE SECURITY: {comp.name} [{comp.ticker}] has commissioned heavy security vessel '{enforcer_name}' to patrol Sector {sec_id:03d} shipping lanes!",
                        channel="CORP",
                        sector_id=sec_id,
                    )
                kernel.action_logs.append(
                    f"[CORPORATE] {comp.ticker} commissioned security vessel {enforcer_name} in Sector {sec_id:03d}."
                )
                spawned_names.append(enforcer_name)

        # 2. Federal Bounty Hunter Response to Outlaws
        if kernel.cycle_count > 0 and kernel.cycle_count % 150 == 0 and populace.room_for_ai(kernel):
            pirates = [c for c in kernel.captains.values() if c.is_ai and c.personality == AIPersonality.PIRATE]
            hunters = [c for c in kernel.captains.values() if c.is_ai and ("Marshal" in c.name or "Hunter" in c.name)]
            if len(pirates) > len(hunters):
                bounty_id = f"fed_marshal_{kernel.cycle_count}"
                ship_class = "Star Frigate"
                ship_cfg = SHIP_CATALOG.get(ship_class, SHIP_CATALOG["Scout Ship"])
                cargo = CargoHold(capacity=ship_cfg["holds"])
                cargo.elements["H"] = 25
                cargo.elements["He-3"] = 15

                marshal_name = f"Fed Marshal Vance-{kernel.cycle_count % 100:02d}"
                # Marshals are provisioned by the Federal Reserve
                fed = getattr(kernel, "federal_reserve", None)
                marshal_float = min(6000, fed.treasury) if fed else 0
                if fed:
                    fed.treasury -= marshal_float
                marshal_cap = Captain(
                    id=bounty_id,
                    name=marshal_name,
                    is_ai=True,
                    personality=AIPersonality.MERCENARY,
                    credits=marshal_float,
                    sector_id=1,
                    species="actinoform-vanguard",
                    metabolism="plasmic",
                    clade="BIOTIC",
                    rank_tier=3,
                    turns_left=200,
                    ship=Ship(
                        ship_type=ship_class,
                        cargo=cargo,
                        shields=ship_cfg["max_shields"],
                        max_shields=ship_cfg["max_shields"],
                        fighters=ship_cfg["max_fighters"],
                    )
                )

                kernel.captains[bounty_id] = marshal_cap
                matter.commission(marshal_cap)
                if 1 in kernel.sectors:
                    kernel.sectors[1].captains.append(bounty_id)

                if getattr(kernel, "event_bus", None):
                    kernel.event_bus.broadcast_radio(
                        sender="FED-PATROL",
                        text=f"FED COMMODORE: Federal Bounty Office has commissioned {marshal_name} out of Sol Stardock to neutralize borderland outlaws!",
                        channel="SYSTEM",
                        sector_id=1,
                    )
                kernel.action_logs.append(f"[BOUNTY] Sol Federation commissioned {marshal_name} for frontier patrol.")
                spawned_names.append(marshal_name)

        return spawned_names

    def to_dict(self) -> Dict[str, Any]:
        return {
            "companies": {t: c.to_dict() for t, c in self.companies.items()},
            "contracts": {cid: ct.to_dict() for cid, ct in self.contracts.items()},
            "executives": {eid: ex.to_dict() for eid, ex in self.executives.items()},
            "trade_haulers": {hid: h.to_dict() for hid, h in self.trade_haulers.items()},
            "trade_council": self.trade_council.to_dict(),
            "next_contract_id": self.next_contract_id,
            "next_exec_id": self.next_exec_id,
            "next_hauler_id": self.next_hauler_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketManager":
        mgr = cls.__new__(cls)
        mgr._kernel_ref = None
        mgr.companies = {
            t: Company.from_dict(c_data)
            for t, c_data in data.get("companies", {}).items()
        }
        mgr.contracts = {
            cid: FreightContract.from_dict(ct_data)
            for cid, ct_data in data.get("contracts", {}).items()
        }
        mgr.executives = {
            eid: SalesExecutive.from_dict(ex_data)
            for eid, ex_data in data.get("executives", {}).items()
        }
        mgr.trade_haulers = {
            hid: TradeHauler.from_dict(h_data)
            for hid, h_data in data.get("trade_haulers", {}).items()
        }
        if data.get("trade_council"):
            mgr.trade_council = TradeCouncil.from_dict(data["trade_council"])
        else:
            mgr.trade_council = TradeCouncil()
        mgr.next_contract_id = data.get("next_contract_id", 101)
        mgr.next_exec_id = data.get("next_exec_id", 101)
        mgr.next_hauler_id = data.get("next_hauler_id", 101)
        return mgr
