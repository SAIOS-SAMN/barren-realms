#!/usr/bin/env python3
"""
simulate_playtest.py: Long-horizon playtest harness for Xylarium.

Runs the authoritative kernel for N cycles with one scripted bot player per
lineage (BIOTIC, LITHIC, PLASMIC, CRYOGENIC, ANARCHY) alongside the AI swarm, and
reports:

  * Bottlenecks   - wall time per kernel subsystem, throughput per window
                    (degradation over time), optional cProfile hotspots.
  * Growth        - every list/dict/deque on the kernel and its managers is
                    sampled so unbounded collections (leaks) show up.
  * Invariants    - cargo over capacity, negative credits, shields out of
                    range, broken sector membership, NaN flux, bad port stock.
  * Delivery      - does a player actually progress? Bot credits/tier over
                    time, ascension blockers, action failure reasons, turn
                    starvation; AI wealth concentration, broke/stuck AIs.

The bots never touch the save file. Examples:

    python3 simulate_playtest.py --cycles 1000
    python3 simulate_playtest.py --cycles 10000 --out playtest_10k.json
    python3 simulate_playtest.py --cycles 2000 --profile
"""

import argparse
import cProfile
import inspect
import io
import json
import math
import os
import pstats
import random
import sys
import tempfile
import time
import traceback
from collections import Counter, defaultdict, deque
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from xylarium.kernel import hulls
from xylarium.kernel.engine import GameKernel
from xylarium.kernel import subsystem
from xylarium.kernel.models import ActionType
from xylarium.persistence.store import StatePersistence
from xylarium.config import CAPTAIN_RATIONS, COLONY_KIT_CREDITS, COLONY_KIT_EQUIPMENT, PRICE_LEVEL
from xylarium.kernel.ledger import money_supply as ledger_money_supply

BOT_CLADES = ["BIOTIC", "LITHIC", "PLASMIC", "CRYOGENIC", "ANARCHY", "IMPERIAL"]
SNAPSHOT_EVERY = 100


# ---------------------------------------------------------------------------
# Subsystem timing instrumentation
# ---------------------------------------------------------------------------

class Timers:
    def __init__(self):
        self.total: Dict[str, float] = defaultdict(float)
        self.calls: Counter = Counter()

    def wrap(self, owner: Any, name: str, label: str) -> None:
        """Replaces owner.name with a timed wrapper, preserving static/class/instance binding."""
        static_attr = inspect.getattr_static(owner, name, None)
        if static_attr is None:
            return
        timers = self

        if isinstance(static_attr, (staticmethod, classmethod)):
            bound = getattr(owner, name)

            def timed(*a, **k):
                t0 = time.perf_counter()
                try:
                    return bound(*a, **k)
                finally:
                    timers.total[label] += time.perf_counter() - t0
                    timers.calls[label] += 1

            setattr(owner, name, staticmethod(timed))
        else:
            fn = static_attr

            def timed(self_, *a, **k):
                t0 = time.perf_counter()
                try:
                    return fn(self_, *a, **k)
                finally:
                    timers.total[label] += time.perf_counter() - t0
                    timers.calls[label] += 1

            setattr(owner, name, timed)


def instrument(timers: Timers) -> None:
    from xylarium.kernel.ai import AIManager
    from xylarium.kernel.economy import EconomyManager
    from xylarium.kernel.colony import ColonyManager
    from xylarium.kernel.market import MarketManager
    from xylarium.kernel.research import ResearchManager
    from xylarium.kernel.cartography import CartographyManager
    from xylarium.kernel.surface import SurfaceManager
    from xylarium.kernel.astronomy import AstronomyManager
    from xylarium.kernel.governance import SenateManager
    from xylarium.kernel.alchemy import AlchemyManager

    targets = [
        (GameKernel, "tick_simulation", "tick_simulation (total)"),
        (GameKernel, "process_turn_maintenance", "turn_maintenance"),
        (GameKernel, "get_player_view", "get_player_view"),
        (GameKernel, "dispatch", "dispatch (bot actions)"),
        (AIManager, "execute_turn", "ai.execute_turn"),
        (EconomyManager, "tick_port", "economy.tick_port"),
        (ColonyManager, "tick_colony", "colony.tick_colony"),
        (MarketManager, "tick_market", "market.tick_market"),
        (ResearchManager, "tick_cognitive_metabolism", "research.tick_cognitive_metabolism"),
        (CartographyManager, "tick_survey_probes", "cartography.tick_survey_probes"),
        (SurfaceManager, "tick_surface", "surface.tick_surface"),
        (AstronomyManager, "tick", "astronomy.tick"),
        (SenateManager, "tick_senate", "governance.tick_senate"),
        (AlchemyManager, "tick_cooldown", "alchemy.tick_cooldown"),
    ]
    try:
        from xylarium.kernel.cognition import CognitiveOrgan
        targets.append((CognitiveOrgan, "think", "cognition.think (inside ai)"))
    except ImportError:
        pass
    for owner, name, label in targets:
        timers.wrap(owner, name, label)


# ---------------------------------------------------------------------------
# Money-supply accounting (faucets & sinks)
# ---------------------------------------------------------------------------

def money_supply(kernel: GameKernel) -> Dict[str, Any]:
    """
    Every money stock in every currency (see xylarium.kernel.ledger.money_supply), plus
    ``total``: the whole supply valued at *fixed genesis price levels*, so attribution
    isn't polluted by FX revaluation.
    """
    by_cur = ledger_money_supply(kernel)
    out: Dict[str, Any] = {"by_currency": by_cur}
    out["total"] = int(sum(b["total"] / PRICE_LEVEL.get(cur, 1.0) for cur, b in by_cur.items()))
    for stock in ("captains", "planet_vaults", "households", "company_treasuries", "port_treasuries",
                  "federal_reserve", "contract_escrow", "fx_pools"):
        out[stock] = int(sum(b.get(stock, 0) / PRICE_LEVEL.get(cur, 1.0) for cur, b in by_cur.items()))
    return out


def territory_genesis(kernel: GameKernel) -> Dict[str, int]:
    """Money declared at the genesis of newly charted clusters and ghost sectors (expansion, not inflation)."""
    out: Dict[str, int] = defaultdict(int)
    for (src, cur), v in kernel.ledger.minted.items():
        if src in ("cluster_genesis", "ghost_sector_genesis"):
            out[cur] += v
    return dict(out)


def cosmos_census(kernel: GameKernel) -> Dict[str, Any]:
    """Alignment, locals, great powers and the Library at a glance."""
    from xylarium.kernel.alignment import census
    natives = [p.natives for s in kernel.sectors.values() for p in s.planets if p.natives]
    systems = sum(1 for s in kernel.sectors.values() if s.kind == "SYSTEM")
    powers = {}
    for f in kernel.factions.factions.values():
        if f.kind in ("IMPERIUM", "ZEALOT"):
            systems_held = sum(1 for sid in f.territory if kernel.sectors[sid].kind == "SYSTEM")
            powers[f.id] = {"worlds": sum(1 for s in kernel.sectors.values() for p in s.planets if p.faction_id == f.id),
                            "systems_share": round(systems_held / max(1, systems), 3), "fleet": len(f.fleet),
                            "dogma": round(f.dogma, 3), "stability": round(f.stability, 3), "stats": dict(f.stats)}
    doctrines = {k: f.card for k, f in kernel.factions.factions.items()}
    return {
        "alignment": census(kernel),
        "private_alignment": _private_census(kernel),
        "natives": len(natives),
        "native_stage_mean": round(sum(n["stage"] for n in natives) / len(natives), 2) if natives else 0,
        "native_stats": dict(kernel.native_stats),
        "powers": powers,
        "doctrines": doctrines,
        "chronicle_entries": kernel.chronicle.next_id - 1,
        "banking": {
            "clearing_imbalance": kernel.banking.clearing_imbalance(),
            "chain_blocks": len(kernel.settlement.blocks),
            "chain_verify": kernel.settlement.verify(),
            "banks": {b.currency: {"reserves": kernel.banking.reserves(kernel, b), "loans": b.loans_outstanding,
                                   "rate": b.policy_rate, "stamp": round(kernel.banking.stamp.get(b.currency, 0.0)),
                                   "stats": dict(b.stats)} for b in kernel.banking.banks.values()},
            "cross_volume_sol": int(sum(kernel.fx_market.cross_volume.values())),
            "arbitrage": dict(getattr(kernel.fx_market, "arbitrage", {}) or {}),
            "cross_gap_max": round(max((abs((p["b"] / p["a"]) / (kernel.fx_market.rate(p["cb"]) / kernel.fx_market.rate(p["ca"])) - 1)
                                        for p in kernel.fx_market.cross_pools.values()), default=0.0), 3),
        },
        "houses": __import__("xylarium.kernel.lineage", fromlist=["npc_census"]).npc_census(kernel),
        "chronicle_kinds": dict(kernel.chronicle.counts),
        "demography": _demography_census(kernel),
        "physics": __import__("xylarium.kernel.physics", fromlist=["summary"]).summary(kernel.sectors),
        # every registered subsystem's summary (credit, geology, propulsion, law, crime, fibres, fertility, luxury,
        # tourism, realms, government, workbench, ...) - a new subsystem appears here by registering one
        **{k: (dict(v) if isinstance(v, dict) else v) for k, v in subsystem.summaries(kernel).items()},
        "society": _society_census(kernel),
        "industry": {"fabricated": {c: v for (k, c), v in kernel.matter.sources.items() if k == "fabrication"},
                     "recycled_ore": kernel.matter.sources.get(("recycling", "ORE"), 0),
                     "sector_gas": sum(getattr(s, "gas", 0) for s in kernel.sectors.values())},
    }


def _society_census(kernel: GameKernel) -> Dict[str, Any]:
    """Fertility, luxury and tourism, and the output (GDP) they are measured against."""
    from xylarium.kernel import ledger
    from xylarium.kernel.fx import ACTIVE_FX
    pol = ledger.ACTIVE_POLICY
    # GDP by the income approach: what the worlds' households and governments earned - colony earnings, export
    # sales and the starports' payroll and purchases in their regions
    gdp = 0.0
    for cur, v in (getattr(pol, "earnings_total", None) or {}).items():
        gdp += ACTIVE_FX.to_sol_value(cur, v) if (ACTIVE_FX is not None and cur != "SOL") else v
    worlds = [p for s in kernel.sectors.values() for p in s.planets if p.population > 0 and not p.natives]
    total = sum(p.population for p in worlds)
    daughters = sum(p.population for p in worlds if p.metropole_id)
    sums = subsystem.summaries(kernel)
    return {"fertility": sums["fertility"], "luxury": sums["luxury"],
            "tourism": sums["tourism"], "gdp_sol": round(gdp),
            "daughter_share": round(daughters / total, 4) if total else 0.0}


def _demography_census(kernel: GameKernel) -> Dict[str, Any]:
    from xylarium.kernel import demography
    worlds = [p for s in kernel.sectors.values() for p in s.planets if p.population > 0 and not p.natives]
    st = demography.stats(kernel)
    return {
        "worlds": len(worlds),
        "population": sum(p.population for p in worlds),
        "housing": sum(demography.housing_cap(p) for p in worlds),
        "habitats": sum(p.habitats for p in worlds),
        "citadel_tiers": dict(Counter(p.citadel_level for p in worlds)),
        "policies": dict(Counter(p.growth_policy or "undecided" for p in worlds)),
        "sectors": len(kernel.sectors),
        "clusters": list(kernel.research_manager.minted_clusters),
        "stats": {k: v for k, v in st.items()},
    }


def _private_census(kernel: GameKernel) -> Dict[str, Any]:
    from xylarium.kernel.alignment import side
    caps = [c for c in kernel.captains.values() if not c.faction_id]
    sides = {"light": 0, "neutral": 0, "dark": 0}
    for c in caps:
        sides[side(c.cosmic_alignment)] += 1
    mean = sum(c.cosmic_alignment for c in caps) / len(caps) if caps else 0.0
    return {"mean": round(mean, 4), "n": len(caps), **sides}


def _chronicle_samples(kernel: GameKernel) -> List[Dict[str, Any]]:
    """One recent entry of each kind, to read what the galaxy wrote."""
    seen, out = set(), []
    for e in reversed(kernel.chronicle.entries):
        if e["kind"] not in seen:
            seen.add(e["kind"])
            out.append(e)
    return out


def ledger_net(kernel: GameKernel) -> Dict[str, int]:
    """Declared mints minus declared burns so far, per currency."""
    net: Dict[str, int] = defaultdict(int)
    for (_, cur), v in kernel.ledger.minted.items():
        net[cur] += v
    for (_, cur), v in kernel.ledger.burned.items():
        net[cur] -= v
    return dict(net)


class MoneyFlows:
    """
    Attributes net money creation (+) / destruction (-) to instrumented calls with
    *exclusive* accounting: a frame is charged only for its own change, net of any
    instrumented calls nested inside it. Frames are coarse (the world tick, market,
    federal operations, player actions) so accounting stays cheap.
    """

    def __init__(self):
        self.kernel: Optional[GameKernel] = None
        self.net: Counter = Counter()
        self.stack: List[Dict[str, int]] = []

    def wrap(self, owner: Any, name: str, label: Any) -> None:
        static_attr = inspect.getattr_static(owner, name, None)
        if static_attr is None:
            return
        flows = self
        is_static = isinstance(static_attr, (staticmethod, classmethod))
        fn = getattr(owner, name) if is_static else static_attr

        def measured(*a, **k):
            if flows.kernel is None:
                return fn(*a, **k)
            lbl = label(a, k) if callable(label) else label
            if lbl is None:
                return fn(*a, **k)
            frame = {"before": money_supply(flows.kernel)["total"], "children": 0}
            flows.stack.append(frame)
            try:
                return fn(*a, **k)
            finally:
                flows.stack.pop()
                delta = money_supply(flows.kernel)["total"] - frame["before"]
                flows.net[lbl] += delta - frame["children"]
                if flows.stack:
                    flows.stack[-1]["children"] += delta

        setattr(owner, name, staticmethod(measured) if is_static else measured)


ACTIVITY: Counter = Counter()


def instrument_activity() -> None:
    """Counts null-space industry, piracy and contract outcomes (who did what, AI vs player)."""
    from xylarium.kernel.nullspace import NullSpaceManager
    from xylarium.kernel.combat import CombatManager
    from xylarium.kernel.market import MarketManager

    def counted(owner: Any, name: str, label_fn) -> None:
        static_attr = inspect.getattr_static(owner, name)
        is_static = isinstance(static_attr, (staticmethod, classmethod))
        fn = getattr(owner, name) if is_static else static_attr

        def wrapper(*a, **k):
            res = fn(*a, **k)
            for lbl in label_fn(a, res) or []:
                ACTIVITY[lbl] += 1
            return res
        setattr(owner, name, staticmethod(wrapper) if is_static else wrapper)

    def who(cap: Any) -> str:
        return "ai" if getattr(cap, "is_ai", False) else "player"

    counted(NullSpaceManager, "mine", lambda a, r: [f"mining runs ({who(a[0])})"] if r.success else [])
    counted(NullSpaceManager, "scan", lambda a, r: [f"deep-space scans ({who(a[0])})"] if r.success else [])
    counted(NullSpaceManager, "salvage", lambda a, r: [f"salvage recoveries ({who(a[0])})"] if r.success else [])
    counted(NullSpaceManager, "create_debris", lambda a, r: ["hulls destroyed -> debris"])
    counted(NullSpaceManager, "deploy_sentries", lambda a, r: [f"sentry deployments ({who(a[0])})"] if r.success else [])
    counted(CombatManager, "resolve_ship_battle",
            lambda a, r: (["battles in null space" if a[2].is_null_space else "battles in systems"]
                          + (["hostile acts (warrants)"] if any("[HOSTILE ACT]" in l for l in (r.logs or [])) else [])))
    counted(MarketManager, "generate_extraction_contracts", lambda a, r: ["extraction orders posted"] * len(r))
    counted(MarketManager, "generate_colony_imports", lambda a, r: ["colony import orders posted"] * len(r))
    from xylarium.kernel.archaeology import ArchaeologyManager
    counted(ArchaeologyManager, "excavate",
            lambda a, r: ([f"excavations ({who(a[0])})"] + (["cave-ins"] if (r.data or {}).get("cave_in") else [])
                          + [f"artifacts unearthed ({who(a[0])})"] * len((r.data or {}).get("finds", [])))
            if r.success else [])
    counted(ArchaeologyManager, "sell", lambda a, r: [f"artifacts sold ({who(a[0])})"] if r.success else [])
    counted(ArchaeologyManager, "study", lambda a, r: [f"relics studied ({who(a[0])})"] if r.success else [])
    counted(ArchaeologyManager, "check_collapse", lambda a, r: ["civilizations collapsed -> ruins"] if r else [])
    from xylarium.kernel.cognition import CognitiveOrgan
    counted(CognitiveOrgan, "_execute_deed",
            lambda a, r: ([f"deed_fail::{a[1].id}::{a[0].deed_name}"] if not getattr(r, "success", True) else []))
    counted(MarketManager, "deliver_freight_contract",
            lambda a, r: ([f"contracts delivered ({who(a[1])})"] if r[0] else []))


def instrument_money(flows: MoneyFlows) -> None:
    from xylarium.kernel.market import MarketManager
    from xylarium.kernel.federal import FederalReserve
    from xylarium.kernel.nullspace import NullSpaceManager

    def player_action(a, k):
        kernel, pid, action = a[0], a[1], a[2]
        cap = kernel.captains.get(pid)
        return f"player:{getattr(action, 'value', action)}" if cap is not None and not cap.is_ai else None

    for owner, name, label in [
        (GameKernel, "tick_simulation", "world tick: AI turns, colonies (tax - upkeep), other"),
        (MarketManager, "tick_market", "market tick (contracts, corporate, consumer spending)"),
        (FederalReserve, "collect_premiums", "insurance premiums"),
        (FederalReserve, "fiscal_quarter", "antitrust & bounty board"),
        (GameKernel, "process_turn_maintenance", "turn maintenance & AI FX repatriation"),
        (GameKernel, "_consume_rations", "rations"),
        (NullSpaceManager, "tick", "null space (belts, debris)"),
        (GameKernel, "dispatch", player_action),
    ]:
        flows.wrap(owner, name, label)


# ---------------------------------------------------------------------------
# Bot player
# ---------------------------------------------------------------------------

def held_amount(captain: Any, commodity: str) -> int:
    cargo = captain.ship.cargo
    key = commodity.lower()
    if key in ("ore", "organics", "equipment"):
        return int(getattr(cargo, key, 0))
    for k, v in cargo.elements.items():
        if k.lower() == key:
            return int(v)
    return 0


def bfs_path(kernel: GameKernel, start: int, goal: int, limit: int = 12) -> Optional[List[int]]:
    if start == goal:
        return [start]
    prev = {start: None}
    q = deque([(start, 0)])
    while q:
        cur, d = q.popleft()
        if d >= limit:
            continue
        for nxt in kernel.sectors[cur].warps:
            if nxt in prev or nxt not in kernel.sectors:
                continue
            prev[nxt] = cur
            if nxt == goal:
                path = [nxt]
                while prev[path[-1]] is not None:
                    path.append(prev[path[-1]])
                return path[::-1]
            q.append((nxt, d + 1))
    return None


class BotPlayer:
    """
    Scripted baseline player: a greedy arbitrage trader that remembers port prices (the ANARCHY
    one also raids). It is hand-written on purpose - a fixed yardstick that doesn't move when the
    game's AI changes, so a regression in the AI can't hide a regression in the game.
    """

    kind = "scripted"

    def __init__(self, kernel: GameKernel, clade: str, rng: random.Random, pid: Optional[str] = None,
                 label: Optional[str] = None):
        self.id = pid or f"bot_{clade.lower()}"
        self.clade = clade
        self.rng = rng
        self.cap = kernel.register_player(self.id, label or f"Bot {clade.title()}", clade=clade)
        self.known_ports: Dict[int, Dict[str, Any]] = {}
        self.target: Optional[int] = None
        self.carry_age = 0
        self.actions = Counter()
        self.failures: Dict[str, Counter] = defaultdict(Counter)
        self.turn_starved = 0
        self.ascensions: List[Dict[str, Any]] = []
        self.ascend_blockers: Counter = Counter()
        self.timeline: List[Dict[str, Any]] = []
        self.trade_profit = 0
        self.job: Optional[str] = None
        self.jobs_done = 0
        self.cognition_ok = 0
        self.colonies_founded: List[Dict[str, Any]] = []
        self.hungry_samples = 0
        self.refused_ports: Dict[int, int] = {}   # turret-blocked: no trade at all until cycle
        self.illiquid_ports: Dict[int, int] = {}  # can't pay for our cargo until cycle (buying still fine)
        self.fed_dry_until = -1  # Federal Reserve out of relief liquidity until cycle
        self.last_journal = 0
        self.last_ascend_check = -1

    def _do(self, kernel: GameKernel, action: ActionType, stats: "RunStats", **kw):
        node_before = self.cap.phylogeny_node_id
        try:
            res = kernel.dispatch(self.id, action, **kw)
        except Exception as e:
            stats.record_exception(f"dispatch {action.value}", e)
            return None
        # Record every crystallization, whichever action produced it (ascend, or cognition's own check)
        if self.cap.phylogeny_node_id != node_before and node_before is not None:
            self.ascensions.append({"cycle": kernel.cycle_count, "from": node_before, "to": self.cap.phylogeny_node_id})
        self.actions[action.value] += 1
        if not res.success and action == ActionType.TRADE:
            if "SECURITY ALERT" in (res.message or ""):
                self.refused_ports[self.cap.sector_id] = kernel.cycle_count + 300
            elif "illiquid" in (res.message or ""):
                self.illiquid_ports[self.cap.sector_id] = kernel.cycle_count + 150
        if not res.success:
            # Collapse numbers so similar messages group together
            msg = "".join("#" if ch.isdigit() else ch for ch in (res.message or ""))[:110]
            self.failures[action.value][msg] += 1
        return res

    def _snapshot_port(self, sector: Any) -> None:
        if sector.port:
            self.known_ports[sector.id] = {
                k: dict(v) for k, v in sector.port.to_dict().get("catalog", {}).items()
            } if hasattr(sector.port, "to_dict") else {}

    def act(self, kernel: GameKernel, stats: "RunStats") -> None:
        cap = self.cap
        # Treasury: convert foreign-currency earnings home when SOL runs low (FX desk)
        if cap.credits < 400:
            for cur, amt in list(cap.fx_wallet.items()):
                if kernel.fx_market.to_sol_value(cur, amt) > 150:
                    self._do(kernel, ActionType.FX_EXCHANGE, stats, amount=amt, from_currency=cur, to_currency="SOL")
        if cap.turns_left <= 0:
            self.turn_starved += 1
            if cap.sector_id == 1 and cap.credits > 5000:
                self._do(kernel, ActionType.REST, stats)
            return

        # Distress: broke captains dump cargo at any buyer and take the Federal relief loan at Sol
        if self._distress(kernel, stats):
            return

        # Provision first: crews eat every 10 cycles and a hungry crew learns nothing
        if self._provision(kernel, stats):
            return

        # Periodically attempt ascension (every lineage, whatever its trade - miners included)
        if kernel.cycle_count % 20 == 0 and self.last_ascend_check != kernel.cycle_count:
            self.last_ascend_check = kernel.cycle_count
            ev = kernel.phylogeny_manager.evaluate_ascension(cap, kernel)
            if ev["can_ascend"]:
                old = cap.phylogeny_node_id
                res = self._do(kernel, ActionType.PHYLOGENY_ASCEND, stats)
                if res and res.success:
                    return
            else:
                for r in ev["unmet_reasons"]:
                    self.ascend_blockers[r.split(" ")[0] + " " + r.split(" ")[1] if " " in r else r] += 1

        # Curious crews study the locals from orbit now and then (lawful under every doctrine)
        here = kernel.sectors[cap.sector_id]
        if any(p.natives for p in here.planets) and self.rng.random() < 0.08:
            res = self._do(kernel, ActionType.NATIVE_INTERACT, stats, sub_action="observe")
            if res and res.success:
                return
        # The cold-log keeper files a journal entry with the Library every so often
        if self.clade == "CRYOGENIC" and kernel.cycle_count - self.last_journal >= 700:
            self.last_journal = kernel.cycle_count
            self._do(kernel, ActionType.CHRONICLE_WRITE, stats, title=f"Cold-log {kernel.cycle_count}",
                     text=(f"Sector {cap.sector_id:03d}. Holds {int(cap.ship.cargo.holds_used)}/{cap.ship.cargo.capacity}. "
                           f"The crew is {'hungry' if cap.hunger else 'fed'}; the ledger reads {cap.credits:,} Cr. "
                           "We keep going because the cold keeps going."))

        # Cognition organ is the only source of grown-basis crystals for players
        if sum(self.actions.values()) % 10 == 0:
            res = self._do(kernel, ActionType.COGNITIVE_AUTOMATE, stats)
            if res and res.success:
                self.cognition_ok += 1
                return

        # The Lithic lineage bot runs an industrial mining operation in null space
        # (a hungry crew docks to provision first - the ration purchase below handles it)
        ration_short = cap.ship.cargo.unbonded(CAPTAIN_RATIONS.get(cap.metabolism, "ORGANICS")) < 3
        if self.clade == "LITHIC" and not (ration_short and kernel.sectors[cap.sector_id].port) \
                and self._work_mining(kernel, stats):
            return

        # Freight contracts are the main experience source (+25 Exp each)
        if self._work_freight(kernel, stats):
            return

        sector = kernel.sectors[cap.sector_id]
        view_catalog = None
        if sector.port:
            view = kernel.get_player_view(self.id)
            view_catalog = (view.get("sector", {}).get("port") or {}).get("catalog", {})
            self.known_ports[sector.id] = view_catalog

        if self._settle(kernel, stats, sector, view_catalog):
            return

        # Pirate lineage raids AI ships sharing the sector
        # (only in null space: opening fire under a port's guns or over a colony is a hostile act)
        if self.clade == "ANARCHY" and sector.is_null_space and cap.ship.fighters >= 10 and self.rng.random() < 0.3:
            prey = [cid for cid in sector.captains if cid != cap.id and cid in kernel.captains
                    and kernel.captains[cid].is_ai]
            if prey:
                self._do(kernel, ActionType.ATTACK_SHIP, stats, target_id=self.rng.choice(prey))
                return

        if view_catalog:
            # 1. Sell anything this port buys (unless it has recently been unable to pay)
            can_pay = self.illiquid_ports.get(sector.id, -1) < kernel.cycle_count
            for comm, info in (view_catalog.items() if can_pay else ()):
                qty = held_amount(cap, comm) - self._bonded(kernel, comm)
                if qty > 0 and info.get("port_buys"):
                    before = cap.credits
                    res = self._do(kernel, ActionType.TRADE, stats, type="SELL", commodity=comm, amount=qty)
                    if res and res.success:
                        self.trade_profit += cap.credits - before
                        self.carry_age = 0
                        return
            # 2. Buy the commodity with best known spread elsewhere
            if cap.ship.cargo.to_dict().get("available", 0) > 0 and self.carry_age == 0:
                best = None
                for comm, info in view_catalog.items():
                    if not info.get("port_sells") or not info.get("sell_price") or info.get("stock", 0) <= 0:
                        continue
                    for sid, cat in self.known_ports.items():
                        if (sid == sector.id or comm not in cat or self.refused_ports.get(sid, -1) >= kernel.cycle_count
                                or self.illiquid_ports.get(sid, -1) >= kernel.cycle_count):
                            continue
                        dest_port = kernel.sectors[sid].port
                        if dest_port is None or dest_port.treasury < 2000:
                            continue
                        other = cat[comm]
                        if not other.get("port_buys") or not other.get("buy_price"):
                            continue
                        # Compare in SOL at live FX: ports quote in their own regional currency
                        fxm = kernel.fx_market
                        spread = (fxm.to_sol_value(other.get("currency", "SOL"), other["buy_price"])
                                  - fxm.to_sol_value(info.get("currency", "SOL"), info["sell_price"]))
                        if spread > 0 and (best is None or spread > best[0]):
                            best = (spread, comm, info, sid)
                if best:
                    spread, comm, info, sid = best
                    free = int(cap.ship.cargo.to_dict().get("available", 0))
                    unit_sol = kernel.fx_market.to_sol_value(info.get("currency", "SOL"), info["sell_price"])
                    afford = int(max(0, liquid_sol(kernel, cap) - 300) // max(1.0, unit_sol))
                    qty = min(free, afford, int(info.get("stock", 0)))
                    if qty > 0:
                        before = cap.credits
                        res = self._do(kernel, ActionType.TRADE, stats, type="BUY", commodity=comm, amount=qty)
                        if res and res.success:
                            self.trade_profit += cap.credits - before
                            self.target = sid
                            self.carry_age = 1
                            return

        # 4. Move toward target, else explore toward unknown ports
        if self.carry_age:
            self.carry_age += 1
            if self.carry_age > 30:  # give up on stale cargo target
                self.carry_age = 0
                self.target = None
        dest = None
        if self.target is not None and self.target != cap.sector_id:
            path = bfs_path(kernel, cap.sector_id, self.target)
            if path and len(path) > 1:
                dest = path[1]
            else:
                self.target = None
        if dest is None:
            warps = list(sector.warps)
            unknown = [w for w in warps if w not in self.known_ports]
            dest = self.rng.choice(unknown or warps) if warps else None
        if dest is not None:
            self._do(kernel, ActionType.MOVE, stats, destination=dest)

    def _distress(self, kernel: GameKernel, stats: "RunStats") -> bool:
        cap = self.cap
        if liquid_sol(kernel, cap) >= 150:
            return False
        sector = kernel.sectors[cap.sector_id]
        if sector.port is not None and self.refused_ports.get(sector.id, -1) < kernel.cycle_count \
                and self.illiquid_ports.get(sector.id, -1) < kernel.cycle_count:
            ration = CAPTAIN_RATIONS.get(cap.metabolism, "ORGANICS")
            goods = [("ORE", cap.ship.cargo.ore), ("ORGANICS", cap.ship.cargo.organics),
                     ("EQUIPMENT", cap.ship.cargo.equipment)] + list(cap.ship.cargo.elements.items())
            for comm, _ in goods:
                sell = cap.ship.cargo.unbonded(comm) - (10 if comm == ration else 0)
                if sell > 0 and sector.port.buys.get(comm, False):
                    res = self._do(kernel, ActionType.TRADE, stats, type="SELL", commodity=comm, amount=sell)
                    if res and res.success:
                        return True
        # Relief credit only helps if the ceiling allows another loan; otherwise earn it back hauling freight
        from xylarium.config import BANK_DEBT_TOTAL, RELIEF_LOAN_MAX_DEBT
        # Outlaws (turrets at Sol) and captains the Reserve can't lend to must work their way out:
        # null-space mining needs no capital, only a hull and a hold
        no_credit = (cap.debt + BANK_DEBT_TOTAL > RELIEF_LOAN_MAX_DEBT or cap.bounty > 0
                     or self.refused_ports.get(1, -1) >= kernel.cycle_count
                     or self.fed_dry_until >= kernel.cycle_count)
        if no_credit:
            return self._work_mining(kernel, stats)
        if cap.sector_id == 1:
            if cap.credits < 100:
                res = self._do(kernel, ActionType.BANK_TRANSACTION, stats, sub_action="loan")
                if res and not res.success and "liquidity" in res.message:
                    self.fed_dry_until = kernel.cycle_count + 150
                return bool(res and res.success)
            return False
        return self._step_toward(kernel, stats, 1)

    def _provision(self, kernel: GameKernel, stats: "RunStats") -> bool:
        """Keep a deep ration reserve: buy at any port that sells our food, paying from any wallet."""
        cap = self.cap
        ration = CAPTAIN_RATIONS.get(cap.metabolism, "ORGANICS")
        if cap.ship.cargo.unbonded(ration) >= 10:
            return False
        sector = kernel.sectors[cap.sector_id]
        port = sector.port

        def serves_food(sid: int) -> bool:
            sp = kernel.sectors[sid].port
            return bool(sp and sp.sells.get(ration, False) and sp.stock.get(ration, 0) > 0
                        and self.refused_ports.get(sid, -1) < kernel.cycle_count)

        if not serves_food(cap.sector_id):
            if cap.ship.cargo.unbonded(ration) >= 3:
                return False
            # Running out: head for the nearest port that sells our food and will serve us
            best = None
            for sid in kernel.sectors:
                if serves_food(sid):
                    path = bfs_path(kernel, cap.sector_id, sid, limit=8)
                    if path and (best is None or len(path) < len(best)):
                        best = path
            if best and len(best) > 1:
                self._do(kernel, ActionType.MOVE, stats, destination=best[1])
                return True
            return False
        from xylarium.kernel.economy import EconomyManager
        _, unit = EconomyManager.get_unit_prices(port, ration)
        fxm = kernel.fx_market
        spendable = cap.fx_wallet.get(port.currency, 0) + (cap.credits * fxm.rate(port.currency)
                                                          if port.currency != "SOL" else cap.credits)
        qty = min(20 - cap.ship.cargo.unbonded(ration), int(spendable // max(1, unit)),
                  cap.ship.cargo.available_units_for(ration), port.stock.get(ration, 0))
        if qty <= 0:
            return False
        res = self._do(kernel, ActionType.TRADE, stats, type="BUY", commodity=ration, amount=qty)
        return bool(res and res.success)

    def _work_mining(self, kernel: GameKernel, stats: "RunStats") -> bool:
        """Barge up, scan and mine belts, fill extraction work orders, and sell ore where it pays."""
        from xylarium.kernel.nullspace import NullSpaceManager
        cap = self.cap
        sector = kernel.sectors[cap.sector_id]
        mm = kernel.market_manager
        # Industrial career ladder at Sol: Scout -> Prospector Skiff -> Mining Barge
        target_hull = None
        if cap.ship.ship_type == "Scout Ship" and cap.credits >= 5000:
            target_hull = "Prospector Skiff"
        elif cap.ship.ship_type in ("Scout Ship", "Prospector Skiff") and cap.credits >= 15000:
            target_hull = "Mining Barge"
        if target_hull:
            if cap.sector_id == 1:
                res = self._do(kernel, ActionType.SHIPYARD_PURCHASE, stats, item="upgrade_ship", ship_name=target_hull)
                if res and res.success:
                    return True
            else:
                return self._step_toward(kernel, stats, 1)
        # Deliver any extraction order we can already fill
        for cid in list(cap.active_contracts):
            c = mm.contracts.get(cid)
            if c and c.kind == "EXTRACTION" and c.status == "IN_TRANSIT" and cap.ship.cargo.unbonded(c.commodity) >= c.amount:
                if cap.sector_id == c.destination_sector:
                    self._do(kernel, ActionType.FREIGHT_DELIVER, stats, contract_id=c.id, planet_id=c.destination_planet_id)
                    if c.status == "COMPLETED":
                        self.jobs_done += 1
                    return True
                return self._step_toward(kernel, stats, c.destination_sector)
        # Sign an extraction order if one is posted nearby and we're at its colony
        if len(cap.active_contracts) < 3:
            for c in mm.contracts.values():
                if c.kind == "EXTRACTION" and c.status == "OPEN" and c.destination_sector == cap.sector_id \
                        and c.amount <= cap.ship.cargo.available_space:
                    res = self._do(kernel, ActionType.FREIGHT_ACCEPT, stats, contract_id=c.id)
                    if res and res.success:
                        return True
        # Holds mostly full: sell the ore at a port that buys it (never speculate with mining income)
        if cap.ship.cargo.available_space < NullSpaceManager.mining_yield(cap) or \
                cap.ship.cargo.holds_used > cap.ship.cargo.capacity * 0.7:
            if sector.port is not None and self.refused_ports.get(sector.id, -1) < kernel.cycle_count \
                    and self.illiquid_ports.get(sector.id, -1) < kernel.cycle_count:
                ration = CAPTAIN_RATIONS.get(cap.metabolism, "ORGANICS")
                goods = [("ORE", cap.ship.cargo.ore)] + list(cap.ship.cargo.elements.items())
                for comm, qty in goods:
                    keep = 10 if comm == ration else 0
                    sell = cap.ship.cargo.unbonded(comm) - keep
                    if sell > 0 and sector.port.buys.get(comm, False):
                        res = self._do(kernel, ActionType.TRADE, stats, type="SELL", commodity=comm, amount=sell)
                        if res and res.success:
                            return True
                # Nothing sold here: don't bounce back to this port for a while
                self.illiquid_ports[sector.id] = kernel.cycle_count + 150
            ration = CAPTAIN_RATIONS.get(cap.metabolism, "ORGANICS")
            sellable = [c for c in ["ORE"] + list(cap.ship.cargo.elements)
                        if cap.ship.cargo.unbonded(c) - (10 if c == ration else 0) > 0]
            buyers = [sid for sid, sec in kernel.sectors.items() if sec.port is not None
                      and sid != cap.sector_id and self.refused_ports.get(sid, -1) < kernel.cycle_count
                      and self.illiquid_ports.get(sid, -1) < kernel.cycle_count
                      and sec.port.treasury > 3000
                      and any(sec.port.buys.get(c, False) for c in sellable)]
            best = None
            for sid in buyers:
                path = bfs_path(kernel, cap.sector_id, sid, limit=10)
                if path and (best is None or len(path) < len(best)):
                    best = path
            if best and len(best) > 1:
                self._do(kernel, ActionType.MOVE, stats, destination=best[1])
                return True
            return False
        # Provision before heading out: a starving crew mines nothing useful
        ration = CAPTAIN_RATIONS.get(cap.metabolism, "ORGANICS")
        if cap.ship.cargo.unbonded(ration) < 3 and sector.port is None and liquid_sol(kernel, cap) >= 150:
            ports = [sid for sid in kernel.sectors if kernel.sectors[sid].port is not None
                     and kernel.sectors[sid].port.sells.get(ration, False)
                     and self.refused_ports.get(sid, -1) < kernel.cycle_count]
            best = min(ports, key=lambda sid: len(bfs_path(kernel, cap.sector_id, sid, limit=10) or range(99)))
            return self._step_toward(kernel, stats, best)
        # Mine here if there's a belt
        if sector.is_null_space and any(b["reserve"] > 0 for b in sector.belts):
            if any(b["id"] not in cap.scanned_belts for b in sector.belts):
                self._do(kernel, ActionType.SCAN_SPACE, stats)
                return True
            if sector.security.value != "FEDERATION" and not sector.sentries.get(cap.id) and cap.ship.fighters >= 10:
                res = self._do(kernel, ActionType.DEPLOY_SENTRIES, stats, amount=cap.ship.fighters // 2)
                if res and res.success:
                    return True
            res = self._do(kernel, ActionType.MINE_ASTEROIDS, stats)
            return bool(res and res.success)
        # Head for the nearest belt (prefer the one named by an accepted work order)
        targets = [mm.contracts[cid].origin_sector for cid in cap.active_contracts
                   if cid in mm.contracts and mm.contracts[cid].kind == "EXTRACTION"]
        if not targets:
            targets = [sid for sid, sec in kernel.sectors.items() if sec.belts and any(b["reserve"] > 50 for b in sec.belts)]
        best = None
        for sid in targets:
            path = bfs_path(kernel, cap.sector_id, sid, limit=8)
            if path and (best is None or len(path) < len(best)):
                best = path
        if best and len(best) > 1:
            self._do(kernel, ActionType.MOVE, stats, destination=best[1])
            return True
        return False

    def _settle(self, kernel: GameKernel, stats: "RunStats", sector: Any, catalog: Optional[Dict[str, Any]]) -> bool:
        """Founds one colony once the captain can afford a kit: outfit equipment, fly to a legal world, claim."""
        from xylarium.kernel.colony import ColonyManager
        cap = self.cap
        if self.colonies_founded or cap.credits < COLONY_KIT_CREDITS * 2:
            return False
        if cap.ship.cargo.unbonded("EQUIPMENT") < COLONY_KIT_EQUIPMENT:
            if catalog:
                info = catalog.get("EQUIPMENT")
                if info and info.get("port_sells") and info.get("stock", 0) > 0:
                    need = COLONY_KIT_EQUIPMENT - cap.ship.cargo.unbonded("EQUIPMENT")
                    self._do(kernel, ActionType.TRADE, stats, type="BUY", commodity="EQUIPMENT", amount=need)
                    return True
            return False
        for p in sector.planets:
            if p.owner_id is None and ColonyManager.claim_requirements(cap, p, sector, kernel) is None:
                res = self._do(kernel, ActionType.PLANET_CLAIM, stats, planet_id=p.id)
                if res and res.success:
                    self.colonies_founded.append({"cycle": kernel.cycle_count, "planet": p.id, "tier": cap.rank_tier})
                return True
        best = None
        for s in kernel.sectors.values():
            for p in s.planets:
                if p.owner_id is None and ColonyManager.claim_requirements(cap, p, s, kernel) is None:
                    path = bfs_path(kernel, cap.sector_id, s.id, limit=10)
                    if path and (best is None or len(path) < len(best)):
                        best = path
        if best and len(best) > 1:
            self._do(kernel, ActionType.MOVE, stats, destination=best[1])
            return True
        return False

    def _bonded(self, kernel: GameKernel, comm: str) -> int:
        mm = kernel.market_manager
        return sum(mm.contracts[c].amount for c in self.cap.active_contracts
                   if c in mm.contracts and mm.contracts[c].commodity.upper() == comm.upper())

    def _step_toward(self, kernel: GameKernel, stats: "RunStats", goal: int) -> bool:
        path = bfs_path(kernel, self.cap.sector_id, goal)
        if not path or len(path) < 2:
            return False
        self._do(kernel, ActionType.MOVE, stats, destination=path[1])
        return True

    def _work_freight(self, kernel: GameKernel, stats: "RunStats") -> bool:
        cap, mm = self.cap, kernel.market_manager
        if self.job:
            c = mm.contracts.get(self.job)
            if (not c or c.status not in ("OPEN", "IN_TRANSIT")
                    or (c.status == "IN_TRANSIT" and c.accepted_by != cap.id)
                    or (c.status == "OPEN" and kernel.cycle_count >= c.expiry_cycle)):
                self.job = None
                return False
            if c.status == "OPEN":
                if cap.sector_id == c.origin_sector:
                    res = self._do(kernel, ActionType.FREIGHT_ACCEPT, stats, contract_id=c.id)
                    if not (res and res.success):
                        self.job = None
                    return True
                if not self._step_toward(kernel, stats, c.origin_sector):
                    self.job = None
                    return False
                return True
            if cap.sector_id == c.destination_sector:
                res = self._do(kernel, ActionType.FREIGHT_DELIVER, stats, contract_id=c.id)
                if res and res.success:
                    self.jobs_done += 1
                self.job = None
                return True
            if not self._step_toward(kernel, stats, c.destination_sector):
                self.job = None
                return False
            return True
        # Contracts already on our manifest (the cognition organ accepts some for us) come first
        for cid in list(cap.active_contracts):
            c = mm.contracts.get(cid)
            if c and c.status == "IN_TRANSIT" and c.accepted_by == cap.id and c.kind != "EXTRACTION":
                self.job = cid
                return self._work_freight(kernel, stats)
        if len(cap.active_contracts) >= 3:
            return False
        # Pick a new job: nearest open contract whose cargo fits
        free = cap.ship.cargo.available_space
        best = None
        for c in mm.contracts.values():
            if c.status != "OPEN" or c.amount > free or kernel.cycle_count >= c.expiry_cycle or c.kind == "EXTRACTION":
                continue
            p1 = bfs_path(kernel, cap.sector_id, c.origin_sector, limit=6)
            if not p1:
                continue
            if best is None or len(p1) < best[0]:
                best = (len(p1), c.id)
        if best:
            self.job = best[1]
            return self._work_freight(kernel, stats)
        return False

    def sample(self, kernel: GameKernel) -> None:
        cap = self.cap
        self.timeline.append({
            "cycle": kernel.cycle_count,
            "credits": cap.credits,
            "liquid_sol": liquid_sol(kernel, cap),
            "fx_wallet": dict(cap.fx_wallet),
            "tier": cap.rank_tier,
            "node": cap.phylogeny_node_id,
            "turns": cap.turns_left,
            "exp": cap.experience_score,
            "credit_rating": cap.credit_rating,
            "crystals": len(cap.grown_basis),
            "shields": cap.ship.shields,
            "hunger": cap.hunger,
            "xp_domains": dict(cap.experience_domains),
            "ship": cap.ship.ship_type,
        })
        if cap.hunger > 0:
            self.hungry_samples += 1


class CognitionPlayer(BotPlayer):
    """
    A player captain on autopilot: every action is the kernel's own cognition engine choosing a
    deed (COGNITIVE_AUTOMATE) - the same decision-making the NPC houses use - but dispatched through
    the player's path (turn economy, player-only rules, lineage mechanics). No scripted strategy.
    """

    kind = "cognition"

    def __init__(self, kernel: GameKernel, clade: str, rng: random.Random):
        super().__init__(kernel, clade, rng, pid=f"cog_{clade.lower()}", label=f"Autopilot {clade.title()}")
        self.last_node = self.cap.phylogeny_node_id

    def act(self, kernel: GameKernel, stats: "RunStats") -> None:
        cap = self.cap
        if cap.turns_left <= 0:
            self.turn_starved += 1
            return
        res = self._do(kernel, ActionType.COGNITIVE_AUTOMATE, stats)
        if res is not None and res.success:
            self.cognition_ok += 1
        if res is not None and res.action == ActionType.FREIGHT_DELIVER and res.success:
            self.jobs_done += 1


class PersonaPlayer(CognitionPlayer):
    """
    An autopilot captain with a career on top: it earns its living through the kernel's cognition like the
    others, and every PERSONA_EVERY cycles plays its career through the same commands a human would type -
    so the politician's, shipwright's and tourism magnate's paths are exercised under the laws.
    """

    kind = "persona"
    PERSONA_EVERY = 50

    def __init__(self, kernel: GameKernel, clade: str, rng: random.Random, persona: str):
        super().__init__(kernel, clade, rng)
        self.persona = persona
        self.career = Counter()

    def act(self, kernel: GameKernel, stats: "RunStats") -> None:
        if kernel.cycle_count % self.PERSONA_EVERY == 0 and self.cap.turns_left > 0:
            getattr(self, f"_{self.persona}")(kernel, stats)
        super().act(kernel, stats)

    def _record(self, what: str, res: Any) -> None:
        if res is not None and res.success:
            self.career[what] += 1

    # the politician: runs for the Master of Coin, lobbies the Compact, governs by hand when it holds an office
    def _politician(self, kernel: GameKernel, stats: "RunStats") -> None:
        from xylarium.kernel import government
        cap = self.cap
        gm = kernel.governance_manager
        if cap.credits > 8000 and cap.id not in (gm.candidates.get("MASTER_OF_COIN") or []):
            self._record("campaigns", self._do(kernel, ActionType.SENATE_CAMPAIGN, stats, office="MASTER_OF_COIN"))
        if cap.id in (gm.candidates.get("MASTER_OF_COIN") or []):
            self._record("votes", self._do(kernel, ActionType.SENATE_VOTE, stats, office="MASTER_OF_COIN",
                                           candidate_id=cap.id))
        if cap.credits > 20000:
            self._record("lobbying", self._do(kernel, ActionType.LOBBY_CONTRIBUTE, stats, amount=2000))
        for fid, o in government.offices(kernel).items():
            if o.get("holder") == cap.id:
                self.career[f"held_{fid}"] += 1
                if o.get("auto", True):
                    self._record("budgets_set", self._do(kernel, ActionType.BUDGET_SET, stats, government=fid,
                                                          grants=45, endowment=25, security=15, infrastructure=15))
                mine = kernel.get_planets_owned_by(cap.id)
                target = mine[0] if mine else next((p for p in kernel.sectors[cap.sector_id].planets
                                                    if p.population > 0), None)
                if target is not None:
                    self._record("grants", self._do(kernel, ActionType.GOVERNMENT_GRANT, stats, government=fid,
                                                     planet_id=target.id, amount=5000))

    # the shipwright: draws a hauler for its trade once it has the rank and the capital, then builds it at a yard
    def _shipwright(self, kernel: GameKernel, stats: "RunStats") -> None:
        from xylarium.kernel import shipdesign, propulsion
        from xylarium.config import SHIP_FRAMES
        cap = self.cap
        mine = [d for d in shipdesign.designs(kernel).values() if d["designer"] == cap.id]
        if not mine and cap.rank_tier >= 2 and cap.credits > 20000:
            frames = [f for f, spec in SHIP_FRAMES.items() if spec["min_tier"] <= cap.rank_tier]
            frame = max(frames, key=lambda f: SHIP_FRAMES[f]["volume"])
            drive = propulsion.choose_fuel(kernel, cap.sector_id, cap.metabolism or "mineral", cap.rank_tier,
                                           cap.cosmic_alignment)
            mods = shipdesign.draft(frame, "hauler", cap.metabolism or "mineral", drive)
            self._record("designs", self._do(kernel, ActionType.SHIP_DESIGN, stats, name=f"{cap.name} Hauler",
                                             frame=frame, modules=mods, drive=drive, royalty=0.08))
        elif mine and cap.ship.ship_type != mine[0]["name"] and cap.credits > mine[0]["price"] * 1.5 \
                and kernel.sectors[cap.sector_id].port is not None:
            self._record("builds", self._do(kernel, ActionType.SHIPYARD_PURCHASE, stats, item="upgrade_ship",
                                            ship_name=mine[0]["name"]))
        for d in mine:
            self.career["royalty_builds"] = max(self.career["royalty_builds"], d.get("built", 0))

    # the tourism magnate: signs on to VIP charters it can carry, and builds stations where travellers are turned away
    def _magnate(self, kernel: GameKernel, stats: "RunStats") -> None:
        from xylarium.kernel import tourism
        cap = self.cap
        if not cap.charter:
            self._record("charters", self._do(kernel, ActionType.CHARTER_ACCEPT, stats))
        sec = kernel.sectors[cap.sector_id]
        for p in sec.planets:
            if tourism.station(p) is None and p.population > 0 and p.society.get("turned_away", 0) > 0 \
                    and cap.credits > 3 * tourism.station_cost(p):
                self._record("stations", self._do(kernel, ActionType.STATION_BUILD, stats, planet_id=p.id))
                break


PERSONAS = {"BIOTIC": "politician", "LITHIC": "shipwright", "PLASMIC": "magnate"}


def make_players(kernel: GameKernel, rng: random.Random) -> List[BotPlayer]:
    """One autopilot captain per lineage clade (three of them with a career on top), plus one scripted baseline
    trader."""
    players: List[BotPlayer] = [PersonaPlayer(kernel, clade, rng, PERSONAS[clade]) if clade in PERSONAS
                                else CognitionPlayer(kernel, clade, rng) for clade in BOT_CLADES]
    players.append(BotPlayer(kernel, "BIOTIC", rng, pid="bot_baseline", label="Scripted Baseline"))
    return players


# ---------------------------------------------------------------------------
# Run statistics: invariants, growth, exceptions, AI economy
# ---------------------------------------------------------------------------

def liquid_sol(kernel: GameKernel, cap: Any) -> int:
    """Liquid wealth in SOL: credits plus foreign-currency wallets at live ISSE rates."""
    return int(cap.credits + sum(kernel.fx_market.to_sol_value(cur, amt) for cur, amt in cap.fx_wallet.items()))


def net_worth_sol(kernel: GameKernel, cap: Any) -> int:
    """Wealth in SOL: liquid money, cargo at 80% of base value, artifacts, hull resale, and equity."""
    from xylarium.config import COMMODITY_CONFIG
    cargo = cap.ship.cargo
    goods = {"ORE": cargo.ore, "ORGANICS": cargo.organics, "EQUIPMENT": cargo.equipment, **cargo.elements}
    cargo_value = sum(q * COMMODITY_CONFIG.get(k, {}).get("base_price", 10) for k, q in goods.items()) * 0.8
    # Productive capital: hull at 60% resale, equity portfolio at market price
    from xylarium.config import SHIP_CATALOG
    hull = hulls.spec(cap.ship).get("price", 0) * 0.6
    companies = kernel.market_manager.companies
    equity = sum(companies[t].share_price * n for t, n in getattr(cap, "portfolio", {}).items() if t in companies)
    return int(liquid_sol(kernel, cap) + cargo_value + sum(a.get("appraisal_sol", 0) for a in cap.artifacts)
               + hull + equity)


class RunStats:
    def __init__(self):
        self.exceptions: Counter = Counter()
        self.exception_examples: Dict[str, str] = {}
        self.violations: Counter = Counter()
        self.violation_examples: Dict[str, str] = {}
        self.snapshots: List[Dict[str, Any]] = []
        self.growth: Dict[str, List[int]] = defaultdict(list)
        self.window_rates: List[Dict[str, Any]] = []
        self.ai_positions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        self.fail_marks: Dict[str, int] = {}

    def record_exception(self, where: str, e: Exception) -> None:
        tb = traceback.extract_tb(e.__traceback__)
        last = tb[-1] if tb else None
        key = f"{where}: {type(e).__name__} at {os.path.basename(last.filename)}:{last.lineno}" if last else f"{where}: {type(e).__name__}"
        self.exceptions[key] += 1
        self.exception_examples.setdefault(key, f"{e}")

    def violate(self, kind: str, example: str) -> None:
        self.violations[kind] += 1
        self.violation_examples.setdefault(kind, example)

    def check_invariants(self, kernel: GameKernel) -> None:
        from xylarium.config import PLAYER_MAX_TURNS
        for c in kernel.captains.values():
            cargo = c.ship.cargo.to_dict()
            # Density-stacked commodities let raw units exceed holds; the invariant is on holds_used
            if cargo.get("holds_used", 0) > cargo.get("capacity", 0) + 0.01:
                self.violate("cargo_over_capacity", f"{c.name}: {cargo['holds_used']}/{cargo['capacity']} holds @cycle {kernel.cycle_count}")
            if c.credits < 0:
                self.violate("negative_credits", f"{c.name}: {c.credits}")
            if c.ship.shields < 0 or c.ship.shields > c.ship.max_shields:
                self.violate("shields_out_of_range", f"{c.name}: {c.ship.shields}/{c.ship.max_shields}")
            if c.ship.fighters < 0:
                self.violate("negative_fighters", f"{c.name}: {c.ship.fighters}")
            if c.sector_id not in kernel.sectors:
                self.violate("captain_in_missing_sector", f"{c.name}: {c.sector_id}")
            elif c.id not in kernel.sectors[c.sector_id].captains:
                self.violate("captain_not_listed_in_sector", f"{c.name} not in sector {c.sector_id}.captains")
            if not c.is_ai and not (0 <= c.turns_left <= PLAYER_MAX_TURNS):
                self.violate("turns_out_of_range", f"{c.name}: {c.turns_left}")
            for k, v in (c.cochain_flux or {}).items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    self.violate("nan_cochain_flux", f"{c.name}.{k}")
        seen = Counter(cid for s in kernel.sectors.values() for cid in s.captains)
        for cid, n in seen.items():
            if n > 1:
                self.violate("captain_listed_in_multiple_sectors", f"{cid} x{n}")
            if cid not in kernel.captains:
                self.violate("ghost_captain_in_sector", cid)
        for s in kernel.sectors.values():
            if s.port:
                for comm, qty in s.port.stock.items():
                    mx = s.port.max_stock.get(comm, None) if isinstance(getattr(s.port, "max_stock", None), dict) else None
                    if qty < 0:   # a glutted warehouse is allowed (it pays next to nothing); a negative one is not
                        self.violate("port_stock_negative", f"sector {s.id} {comm}={qty} max={mx}")
            for p in s.planets:
                if p.treasury < 0:
                    self.violate("negative_planet_treasury", f"{p.name}: {p.treasury}")
                if p.population < 0:
                    self.violate("negative_population", f"{p.name}: {p.population}")

    def sample_growth(self, kernel: GameKernel) -> None:
        objs = {"kernel": kernel}
        for name, val in vars(kernel).items():
            if name.endswith("_manager") or name == "event_bus":
                objs[name] = val
        for oname, obj in objs.items():
            for attr, val in vars(obj).items():
                if isinstance(val, (list, dict, deque, set)):
                    self.growth[f"{oname}.{attr}"].append(len(val))
                elif oname != "kernel" and hasattr(val, "__dict__") and not callable(val):
                    for sub, sval in vars(val).items():
                        if isinstance(sval, (list, dict, deque, set)):
                            self.growth[f"{oname}.{attr}.{sub}"].append(len(sval))
        # Per-company histories, summed
        companies = getattr(kernel.market_manager, "companies", {})
        self.growth["market_manager.companies[*].price_history"].append(
            sum(len(getattr(c, "price_history", [])) for c in companies.values()))

    @staticmethod
    def gini(values: List[int]) -> float:
        vals = sorted(max(0, v) for v in values)
        n, total = len(vals), sum(vals)
        if not n or not total:
            return 0.0
        return sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(vals)) / (n * total)

    def snapshot(self, kernel: GameKernel, bots: List[BotPlayer]) -> None:
        bot_ids = {b.id for b in bots}
        # Faction warships (Imperial fleet, crusaders) are state vessels, not private wealth
        private = [c for c in kernel.captains.values() if not c.faction_id]
        everyone = [max(0, net_worth_sol(kernel, c)) for c in private]
        money = money_supply(kernel)
        ports = [s.port for s in kernel.sectors.values() if s.port is not None]
        from xylarium.config import PORT_RETAIL_RADIUS
        econ_ports = [s.port for s in kernel.sectors.values() if s.port is not None and
                      kernel.market_manager._regional_worlds(kernel, s.id, s.port.currency, PORT_RETAIL_RADIUS)]
        belts = [b for s in kernel.sectors.values() for b in s.belts]
        # Repeated failures of one deed by one captain within this 100-cycle window
        window_fails = {k: v for k, v in ACTIVITY.items() if k.startswith("deed_fail::")}
        failure_peak = 0
        worst = ""
        for k, v in window_fails.items():
            d = v - self.fail_marks.get(k, 0)
            if d > failure_peak:
                failure_peak, worst = d, k.split("::", 2)[2]
        self.fail_marks = dict(window_fails)
        ais = [c for c in private if c.is_ai]
        credits = sorted(max(0, net_worth_sol(kernel, c)) for c in ais)
        total = sum(credits) or 1
        n = len(credits)
        gini = (sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(credits)) / (n * total)) if n else 0.0
        planets = [p for s in kernel.sectors.values() for p in s.planets]
        for c in ais:
            self.ai_positions[c.id].append(c.sector_id)
        stuck = sum(1 for c in ais if len(self.ai_positions[c.id]) >= 5 and len(set(self.ai_positions[c.id])) == 1)
        self.snapshots.append({
            "cycle": kernel.cycle_count,
            "captains": len(kernel.captains),
            "ai_count": n,
            "ai_money": sum(credits),
            "ai_top_share": round(credits[-1] / total, 3) if n else 0,
            "ai_gini": round(gini, 3),
            "ai_broke_le_250": sum(1 for x in credits if x <= 250),
            "ai_in_sector_1": sum(1 for c in ais if c.sector_id == 1),
            "ai_stuck_5_snapshots": stuck,
            "planet_treasury_total": sum(p.treasury for p in planets),
            "planets_claimed": sum(1 for p in planets if p.owner_id),
            "planets_claimed_by_bots": sum(1 for p in planets if p.owner_id in bot_ids),
            "planets_at_500k_cap": sum(1 for p in planets if p.treasury >= 500000),
            "companies": len(getattr(kernel.market_manager, "companies", {})),
            "money": money,
            "captain_gini": round(self.gini(everyone), 3),
            "captain_top_share": round(max(everyone) / (sum(everyone) or 1), 3),
            "ai_median_credits": credits[n // 2] if n else 0,
            "deed_failure_streak_peak": failure_peak,
            "worst_failing_deed": worst,
            "colonies_founded_by_bots": sum(len(b.colonies_founded) for b in bots),
            "supply_by_currency": {cur: b["total"] for cur, b in money["by_currency"].items()},
            "ledger_net": ledger_net(kernel),
            "territory_genesis": territory_genesis(kernel),
            "fx_rates": {cur: round(kernel.fx_market.rate(cur), 4) for cur in kernel.fx_market.pools},
            "policy": dict(kernel.monetary_policy.factors),
            "policy_targets": dict(getattr(kernel.monetary_policy, "current", {})),
            "ports": len(ports),
            "ports_illiquid": sum(1 for p in ports if p.treasury < 1000 * PRICE_LEVEL.get(p.currency, 1.0)),
            # Ports with an economic loop: populated worlds of their money within retail range
            "ports_economic": len(econ_ports),
            "ports_economic_illiquid": sum(1 for p in econ_ports if p.treasury < 1000 * PRICE_LEVEL.get(p.currency, 1.0)),
            "ports_illiquid_by_currency": dict(Counter(p.currency for p in ports if p.treasury < 1000 * PRICE_LEVEL.get(p.currency, 1.0))),
            "ports_by_currency": dict(Counter(p.currency for p in ports)),
            "belt_reserve_pct": round(sum(b["reserve"] for b in belts) / max(1, sum(b["max_reserve"] for b in belts)), 3),
            "debris_fields": sum(len(s.debris) for s in kernel.sectors.values()),
            "sentries_deployed": sum(sum(s.sentries.values()) for s in kernel.sectors.values()),
            "wanted_captains": sum(1 for c in kernel.captains.values() if c.bounty > 0),
            "ai_foreign_holdings_sol": int(sum(kernel.fx_market.to_sol_value(cur, amt)
                                               for c in kernel.captains.values() if c.is_ai
                                               for cur, amt in c.fx_wallet.items())),
            "cosmos": cosmos_census(kernel),
        })


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

DETERMINISM_PROBE = r"""
import random, sys, hashlib
sys.path.insert(0, {root!r})
import simulate_playtest as sp
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply
seed, cycles = {seed}, {cycles}
random.seed(seed); k = GameKernel(seed=seed); rng = random.Random(seed)
bots = sp.make_players(k, rng); st = sp.RunStats()
real = k.tick_simulation; k.tick_simulation = lambda: None
for _ in range(cycles):
    for b in bots:
        b.act(k, st)
    real()
tip = k.settlement.blocks[-1]["hash"] if k.settlement.blocks else ""
state = hashlib.sha256(repr(sorted((c, b["total"]) for c, b in money_supply(k).items())).encode()).hexdigest()
print(tip, state, sum(p.population for s in k.sectors.values() for p in s.planets))
"""


def determinism_check(seed: int, cycles: int) -> Dict[str, Any]:
    """Runs the same seed in two fresh processes with different string-hash seeds: the universes must match."""
    import subprocess
    code = DETERMINISM_PROBE.format(root=os.path.dirname(os.path.abspath(__file__)), seed=seed, cycles=cycles)
    outs = []
    for hashseed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=hashseed)
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=1800)
        outs.append((res.stdout.strip().splitlines() or [res.stderr.strip()[-300:]])[-1])
    return {"cycles": cycles, "runs": outs, "identical": outs[0] == outs[1]}


def run(cycles: int, seed: int, actions_per_cycle: int, profile: bool, save_state: Optional[str] = None,
        determinism_cycles: int = 0) -> Dict[str, Any]:
    timers = Timers()
    instrument(timers)
    flows = MoneyFlows()
    instrument_money(flows)
    instrument_activity()
    rng = random.Random(seed)
    random.seed(seed)

    t_boot = time.perf_counter()
    kernel = GameKernel(seed=seed)
    money_at_genesis = money_supply(kernel)
    ledger_at_genesis = ledger_net(kernel)
    from xylarium.kernel import matter as matter_mod
    matter_at_genesis = (matter_mod.totals(kernel), kernel.matter.net())
    cosmos_at_genesis = cosmos_census(kernel)
    boot_s = time.perf_counter() - t_boot
    bots = make_players(kernel, rng)
    stats = RunStats()
    flows.kernel = kernel

    # Bots must not advance the world clock themselves; the harness ticks once per cycle
    real_tick = kernel.tick_simulation
    kernel.tick_simulation = lambda: None

    prof = cProfile.Profile() if profile else None
    if prof:
        prof.enable()

    t0 = time.perf_counter()
    window_t0, window_c0 = t0, 0
    window = max(100, cycles // 10)
    # Audit mode (XYL_AUDIT=1, or the older XYL_MATTER_AUDIT=1): a cheap drift check every 100 cycles, and from
    # XYL_AUDIT_FROM on, the exact action, AI turn or seasonal hook that creates or destroys undeclared money or matter
    audit = bool(os.environ.get("XYL_AUDIT") or os.environ.get("XYL_MATTER_AUDIT"))
    leaks_shown = 0
    audit_from = int(os.environ.get("XYL_AUDIT_FROM", "0") or 0)
    drift_base = [None]

    def residual() -> Dict[str, int]:
        """Everything counted minus everything declared: matter per commodity, money per currency ($)."""
        tt, nn = matter_mod.totals(kernel), kernel.matter.net()
        out = {c: tt.get(c, 0) - nn.get(c, 0) for c in set(tt) | set(nn)}
        from xylarium.kernel.ledger import money_supply as supply_by_currency
        ms, ln = supply_by_currency(kernel), ledger_net(kernel)
        for cur in set(ms) | set(ln):
            out["$" + cur] = ms.get(cur, {}).get("total", 0) - ln.get(cur, 0)
        return out

    def changed(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
        return {c: v for c in set(a) | set(b) if (v := b.get(c, 0) - a.get(c, 0))}

    def audited(label, fn):
        nonlocal leaks_shown
        if not audit or leaks_shown >= 8 or kernel.cycle_count < audit_from:
            return fn()
        r0 = residual()
        out = fn()
        d = changed(r0, residual())
        if d:
            leaks_shown += 1
            print(f"  [LEAK] cycle {kernel.cycle_count} in {label}: {d}", flush=True)
        return out

    if audit:
        # Finer labels inside the world tick: each AI turn, each dispatched command and each seasonal hook
        from xylarium.kernel.ai import AIManager
        real_turn = AIManager.execute_turn          # bound (or already wrapped by the timers)

        def turn(k, cap):
            return audited(f"AI turn {cap.id}", lambda: real_turn(k, cap))
        AIManager.execute_turn = staticmethod(turn)
        real_dispatch = kernel.dispatch

        def dispatch(pid, action=None, *a, **kw):
            return audited(f"dispatch {pid} {getattr(action, 'value', action)} {kw}",
                           lambda: real_dispatch(pid, action, *a, **kw))
        kernel.dispatch = dispatch
        for sub in subsystem.REGISTRY.values():
            if sub.season is not None:
                sub.season = (lambda fn, name: (lambda k: audited(f"season:{name}", lambda: fn(k))))(sub.season, sub.name)

    for cycle in range(1, cycles + 1):
        for b in bots:
            for _ in range(actions_per_cycle):
                audited(f"bot {b.id}", lambda: b.act(kernel, stats))
        if audit and cycle % 100 == 0:
            # Coarse drift check (cheap): the first 100-cycle window where the census and the ledger part ways
            now = residual()
            if drift_base[0] is not None:
                d = changed(drift_base[0], now)
                if d:
                    print(f"  [DRIFT] cycles {cycle - 100}-{cycle}: {d}", flush=True)
            drift_base[0] = now
        try:
            audited("world tick", real_tick)
        except Exception as e:
            stats.record_exception("tick_simulation", e)
            kernel.cycle_count = cycle
        if cycle % SNAPSHOT_EVERY == 0 or cycle == cycles:
            stats.check_invariants(kernel)
            stats.sample_growth(kernel)
            stats.snapshot(kernel, bots)
            for b in bots:
                b.sample(kernel)
        if cycle % window == 0 or cycle == cycles:
            now = time.perf_counter()
            stats.window_rates.append({
                "cycles": f"{window_c0 + 1}-{cycle}",
                "cycles_per_sec": round((cycle - window_c0) / max(1e-9, now - window_t0), 1),
                "sectors": len(kernel.sectors),
                "worlds": sum(1 for sec in kernel.sectors.values() for p in sec.planets if p.population > 0),
            })
            print(f"  cycle {cycle:>6}/{cycles}  {stats.window_rates[-1]['cycles_per_sec']:>7} cyc/s  "
                  f"captains={len(kernel.captains)}  exceptions={sum(stats.exceptions.values())}", flush=True)
            window_t0, window_c0 = now, cycle
    wall = time.perf_counter() - t0

    hotspots = ""
    if prof:
        prof.disable()
        buf = io.StringIO()
        pstats.Stats(prof, stream=buf).sort_stats("cumulative").print_stats(30)
        hotspots = buf.getvalue()

    kernel.tick_simulation = real_tick

    # Persistence cost at end state
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "s.json")
        ts = time.perf_counter(); saved = StatePersistence.save_to_file(kernel, path); save_s = time.perf_counter() - ts
        size = os.path.getsize(path) if saved else 0
        tl = time.perf_counter(); loaded = StatePersistence.load_from_file(path); load_s = time.perf_counter() - tl
    if save_state:
        StatePersistence.save_to_file(kernel, save_state)
    view = kernel.get_player_view(bots[0].id)
    view_sections = sorted(((k, len(json.dumps(v, default=str))) for k, v in view.items()), key=lambda kv: -kv[1])[:6]
    tv = time.perf_counter()
    for _ in range(20):
        kernel.get_player_view(bots[0].id)
    view_ms = (time.perf_counter() - tv) / 20 * 1000
    view_bytes = len(json.dumps(kernel.get_player_view(bots[0].id), default=str))

    tick_total = timers.total.get("tick_simulation (total)", 0) or 1e-9
    subsystems = sorted(
        ({"subsystem": k, "seconds": round(v, 3), "calls": timers.calls[k],
          "pct_of_tick": round(100 * v / tick_total, 1), "us_per_call": round(1e6 * v / max(1, timers.calls[k]), 1)}
         for k, v in timers.total.items()),
        key=lambda r: -r["seconds"])

    growth = []
    for key, series in stats.growth.items():
        if len(series) >= 2 and series[-1] > series[0]:
            growth.append({"collection": key, "start": series[0], "end": series[-1],
                           "growth": series[-1] - series[0]})
    growth.sort(key=lambda r: -r["growth"])

    flows.kernel = None
    report = {
        "config": {"cycles": cycles, "seed": seed, "actions_per_cycle": actions_per_cycle, "bots": BOT_CLADES},
        "money": {
            "genesis": money_at_genesis,
            "ledger_genesis": ledger_at_genesis,
            "matter": {"genesis": matter_at_genesis[0], "net_genesis": matter_at_genesis[1],
                       "end": matter_mod.totals(kernel), "net_end": kernel.matter.net(),
                       "sources": sorted(([k, c, v] for (k, c), v in kernel.matter.sources.items()), key=lambda x: -x[2])[:12],
                       "sinks": sorted(([k, c, v] for (k, c), v in kernel.matter.sinks.items()), key=lambda x: -x[2])[:12]},
            "ledger_end": ledger_net(kernel),
            # authority churn: fiscal transfers minted + public services burned (both are the rule's own flows)
            "churn": {cur: kernel.ledger.minted.get(("fiscal_transfer", cur), 0)
                      + kernel.ledger.burned.get(("public_services", cur), 0)
                      for cur in {c for (_, c) in list(kernel.ledger.minted) + list(kernel.ledger.burned)}},
            "end": money_supply(kernel),
            "net_flows": dict(flows.net.most_common()),
            "federal_stats": dict(kernel.federal_reserve.stats),
            "declared_mints": {f"{s} [{c}]": v for (s, c), v in kernel.ledger.minted.most_common()},
            "territory_genesis": territory_genesis(kernel),
            "fx_pools": kernel.fx_market.to_dict(),
        },
        "activity": {k: v for k, v in ACTIVITY.most_common() if not k.startswith("deed_fail::")},
        "cosmos_genesis": cosmos_at_genesis,
        "cosmos_end": cosmos_census(kernel),
        "chronicle_samples": _chronicle_samples(kernel),
        "performance": {
            "boot_seconds": round(boot_s, 3),
            "wall_seconds": round(wall, 2),
            "cycles_per_sec": round(cycles / wall, 1),
            "windows": stats.window_rates,
            "subsystems": subsystems,
            "save_seconds": round(save_s, 3), "load_seconds": round(load_s, 3),
            "save_bytes": size, "load_ok": loaded is not None,
            "player_view_ms": round(view_ms, 2), "player_view_bytes": view_bytes,
            "player_view_largest_sections": view_sections,
        },
        "growth": growth[:25],
        "exceptions": [{"where": k, "count": v, "example": stats.exception_examples[k]} for k, v in stats.exceptions.most_common()],
        "invariant_violations": [{"kind": k, "count": v, "example": stats.violation_examples[k]} for k, v in stats.violations.most_common()],
        "determinism": determinism_check(seed, determinism_cycles) if determinism_cycles else None,
        "world_timeline": stats.snapshots,
        "bots": [{
            "id": b.id, "clade": b.clade, "kind": b.kind,
            "final": b.timeline[-1] if b.timeline else {},
            "ascensions": b.ascensions,
            "ascension_blockers": dict(b.ascend_blockers.most_common(6)),
            "actions": dict(b.actions),
            "top_failures": {a: dict(c.most_common(3)) for a, c in b.failures.items()},
            "turn_starved_actions": b.turn_starved,
            "net_trade_cashflow": b.trade_profit,
            "freight_delivered": b.jobs_done,
            "cognition_successes": b.cognition_ok,
            "persona": getattr(b, "persona", None),
            "career": dict(getattr(b, "career", {}) or {}),
            "colonies_founded": b.colonies_founded,
            "final_net_worth": net_worth_sol(kernel, b.cap),
            "hungry_samples": b.hungry_samples,
            "timeline": b.timeline,
        } for b in bots],
        "hotspots": hotspots,
    }
    report["acceptance"] = evaluate_acceptance(report)
    return report


# ---------------------------------------------------------------------------
# Acceptance gates: the economy is "valid" only if all of these hold
# ---------------------------------------------------------------------------

# Gates whose names start with these are laws (invariants); all others are observations.
LAWS = (
    "money conserved", "matter conserved", "monetary churn", "docket balances", "quantity equation holds", "clearing union conserves", "settlement chain seals",
    "central banks solvent", "orbits never cross", "throughput per unit", "invariant violations",
    "exceptions", "deterministic", "fertility collapses",
)

ACCEPTANCE = {
    "money_growth_per_1k": (-0.25, 0.25),     # per-captain money supply in each currency, per 1,000 cycles
    "undeclared_creation_max": 0,             # money may only enter through declared faucets
    "fx_band": (0.5, 2.0),                    # live rate / genesis price level
    "illiquid_ports_share_max": 0.20,
    "solvent_players_share_min": 0.6,         # of bot players ending with net worth > 1,000 SOL
    "captain_gini": (0.40, 0.70),             # 0.4+: not everyone identical; <= 0.7: no runaway plutocracy
    "chronicle_per_1k_min": 15,
    "chronicle_kinds_min": 5,
    "natives_surviving_min": 0.5,             # of genesis native societies still living (not collapsed/uplifted)
    "zealot_systems_share_max": 0.25,
    "captain_top_share_max": 0.35,
    "broke_ai_share_max": 0.15,                # net worth (money + cargo + artifacts) <= 250 SOL
    "first_tier2_cycle": (1500, 3000),
    "earliest_tier4_cycle_min": 8000,
    "deed_failure_streak_max": 20,             # failures of one deed by one captain per 100 cycles
    "throughput_last_vs_median_min": 0.70,
}


def evaluate_acceptance(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    tl = r["world_timeline"]
    cycles = r["config"]["cycles"]
    gates: List[Dict[str, Any]] = []

    def gate(name: str, target: str, actual: Any, ok: Optional[bool]) -> None:
        # Laws are invariants of the universe's physics and ledgers: they pass or fail. Everything else is an
        # observation of emergent outcomes, reported against a band of interest but never failed.
        law = any(name.startswith(prefix) for prefix in LAWS)
        if ok is None:
            result = "n/a"
        elif law:
            result = "PASS" if ok else "FAIL"
        else:
            result = "ok" if ok else "note"
        gates.append({"gate": name, "target": target, "actual": actual, "result": result, "law": law})

    m = r["money"]
    for cur, end_total in sorted(m["end"]["by_currency"].items()):
        start_total = m["genesis"]["by_currency"].get(cur, {}).get("total", 0)
        declared = m["ledger_end"].get(cur, 0) - m["ledger_genesis"].get(cur, 0)
        undeclared = (end_total["total"] - start_total) - declared
        gate(f"money conserved: every change declared [{cur}]", "== 0", f"{undeclared:+,}", undeclared == 0)

    mt = m.get("matter")
    if mt:
        broken = []
        for comm in sorted(set(mt["end"]) | set(mt["genesis"])):
            change = mt["end"].get(comm, 0) - mt["genesis"].get(comm, 0)
            declared = mt["net_end"].get(comm, 0) - mt["net_genesis"].get(comm, 0)
            if change != declared:
                broken.append(f"{comm} {change - declared:+,}")
        gate("matter conserved: every change declared (all commodities)", "0 undeclared",
             ", ".join(broken[:8]) + (" ..." if len(broken) > 8 else "") if broken else "all exact", not broken)

    if len(tl) >= 2:
        first, last = tl[0], tl[-1]
        span = max(1, last["cycle"] - first["cycle"])
        lo, hi = ACCEPTANCE["money_growth_per_1k"]
        genesis = r["money"].get("territory_genesis", {})
        # Monetary churn: what the authorities mint as transfers and burn as services, per year, relative to the
        # money they govern. A feedback loop between a level-triggered sink and the authority shows up here
        # long before it shows in M / M*.
        years = max(1e-9, span / 100.0)
        for cur in sorted(last["supply_by_currency"]):
            churn = (r["money"].get("churn", {}) or {}).get(cur)
            if churn is None:
                continue
            per_year = churn / years / max(1, last["supply_by_currency"][cur])
            gate(f"monetary churn per year / supply [{cur}]", "<= 2.0", f"{per_year:.2f}", per_year <= 2.0)
        # M V = P Y: with V measured at genesis, the money an economy holds must track what its output needs
        # (M / M*), however much the galaxy has grown. Raw supply growth is reported alongside.
        for cur in sorted(last["supply_by_currency"]):
            start = first["supply_by_currency"].get(cur, 0)
            t1 = last.get("policy_targets", {}).get(cur)
            if t1:
                ratio = last["supply_by_currency"][cur] / t1
                raw = (last["supply_by_currency"][cur] / max(1, start)) ** (1000 / span) - 1
                gate(f"quantity equation holds: M / M* [{cur}]", "0.8 .. 1.25",
                     f"{ratio:.3f} (raw supply {raw:+.1%} / 1k cycles)", 0.8 <= ratio <= 1.25)
                continue
            end = last["supply_by_currency"][cur] - (genesis.get(cur, 0) - first.get("territory_genesis", {}).get(cur, 0))
            rate = (max(1e-9, end) / max(1e-9, start)) ** (1000 / span) - 1 if start > 0 else float("inf")
            gate(f"{cur} supply growth / 1k cycles (net of new territory)", f"{lo:+.0%} .. {hi:+.0%}", f"{rate:+.1%}", lo <= rate <= hi)
        flo, fhi = ACCEPTANCE["fx_band"]
        for cur, rate_now in last["fx_rates"].items():
            drift = rate_now / PRICE_LEVEL.get(cur, 1.0)
            gate(f"{cur} FX rate vs genesis level", f"{flo}x .. {fhi}x", f"{drift:.2f}x", flo <= drift <= fhi)
        # Only ports with an economic loop count: an outpost in an empty cluster may go dry when traffic does
        illiquid = last["ports_economic_illiquid"] / max(1, last["ports_economic"])
        gate("illiquid starports (with a regional economy)", f"<= {ACCEPTANCE['illiquid_ports_share_max']:.0%}",
             f"{illiquid:.0%} ({last['ports_economic_illiquid']}/{last['ports_economic']}; all ports "
             f"{last['ports_illiquid']}/{last['ports']})", illiquid <= ACCEPTANCE["illiquid_ports_share_max"])

        g = last["captain_gini"]
        lo, hi = ACCEPTANCE["captain_gini"]
        gate("captain wealth Gini", f"{lo} .. {hi}", g, lo <= g <= hi)
        top = last["captain_top_share"]
        gate("richest captain share", f"<= {ACCEPTANCE['captain_top_share_max']:.0%}", f"{top:.0%}", top <= ACCEPTANCE["captain_top_share_max"])
        broke = last["ai_broke_le_250"] / max(1, last["ai_count"])
        gate("broke AI share (<= 250 Cr)", f"<= {ACCEPTANCE['broke_ai_share_max']:.0%}", f"{broke:.0%}", broke <= ACCEPTANCE["broke_ai_share_max"])
        q = max(1, len(tl) // 4)
        early = sum(s["ai_median_credits"] for s in tl[:q]) / q
        late = sum(s["ai_median_credits"] for s in tl[-q:]) / q
        # Stable money: median AI net worth should hold (not decay); growth isn't required
        gate("median AI net worth holds (last vs first quarter)", "late >= 75% of early", f"{early:,.0f} -> {late:,.0f}",
             late >= 0.75 * early)
        peak = max(s["deed_failure_streak_peak"] for s in tl)
        worst = max(tl, key=lambda s: s["deed_failure_streak_peak"]).get("worst_failing_deed", "")
        gate("repeated deed failures / 100 cycles", f"<= {ACCEPTANCE['deed_failure_streak_max']}", f"{peak} ({worst})",
             peak <= ACCEPTANCE["deed_failure_streak_max"])

    # Every bot starts at a Tier 1 root, so its first ascension is Tier 2 and its third is Tier 4
    tier2 = [b["ascensions"][0]["cycle"] for b in r["bots"] if b["ascensions"]]
    lo, hi = ACCEPTANCE["first_tier2_cycle"]
    if tier2:
        first_t2 = min(tier2)
        gate("first bot reaches Tier 2 (cycle)", f"{lo} .. {hi}", first_t2, lo <= first_t2 <= hi)
    else:
        gate("first bot reaches Tier 2 (cycle)", f"{lo} .. {hi}", "never", None if cycles < hi else False)
    tier4 = [a["cycle"] for b in r["bots"] for a in b["ascensions"][2:3]]
    floor = ACCEPTANCE["earliest_tier4_cycle_min"]
    gate("no bot reaches Tier 4 before cycle", f">= {floor}", min(tier4) if tier4 else "never", (min(tier4) >= floor) if tier4 else True)

    # Throughput per unit of universe: the galaxy is allowed to grow (the frontier opens clusters, peoples settle new
    # worlds); what must not happen is cost per unit creeping up (a leak). Units are sectors plus peopled worlds
    # (each ticks a colony every cycle). Unit-cycles per second, last window vs median.
    windows = [w["cycles_per_sec"] * (w.get("sectors", 1) + w.get("worlds", 0)) for w in r["performance"]["windows"]]
    if len(windows) >= 3:
        med = sorted(windows)[len(windows) // 2]
        ratio = windows[-1] / med if med else 0
        gate("throughput per unit of universe stable (last window / median)", f">= {ACCEPTANCE['throughput_last_vs_median_min']}",
             round(ratio, 2), ratio >= ACCEPTANCE["throughput_last_vs_median_min"])
    solvent = sum(1 for b in r["bots"] if b.get("final_net_worth", 0) > 1000)
    need = int(round(ACCEPTANCE["solvent_players_share_min"] * len(r["bots"])))
    gate("solvent player captains (net worth > 1,000)", f">= {need} of {len(r['bots'])}", solvent, solvent >= need)

    # --- Cosmos: the universe leans syntropic; locals live; powers are bounded; history is written
    if len(tl) >= 2:
        c0, c1 = tl[0]["cosmos"], tl[-1]["cosmos"]
        a0, a1 = c0["private_alignment"], c1["private_alignment"]
        gate("universe leans syntropic (mean private alignment)", f"end >= start - 0.02 ({a0['mean']:+.3f})",
             f"{a1['mean']:+.3f}", a1["mean"] >= a0["mean"] - 0.02)
        gate("Light captains >= Dark captains (end)", "light >= dark", f"{a1['light']} vs {a1['dark']}", a1["light"] >= a1["dark"])
        # A lean, not a monoculture: the grey middle and the Dark must still exist
        neutral_share = a1["neutral"] / max(1, a1["n"])
        gate("moral diversity survives (end)", ">= 25% neutral and >= 1 dark",
             f"{neutral_share:.0%} neutral, {a1['dark']} dark", neutral_share >= 0.25 and a1["dark"] >= 1)
        span = max(1, tl[-1]["cycle"] - tl[0]["cycle"])
        per_1k = (c1["chronicle_entries"] - c0["chronicle_entries"]) * 1000 / span
        gate("chronicle entries / 1k cycles", f">= {ACCEPTANCE['chronicle_per_1k_min']}", f"{per_1k:.1f}",
             per_1k >= ACCEPTANCE["chronicle_per_1k_min"])
        kinds = sum(1 for v in c1["chronicle_kinds"].values() if v > 0)
        gate("distinct chronicle kinds", f">= {ACCEPTANCE['chronicle_kinds_min']}", kinds, kinds >= ACCEPTANCE["chronicle_kinds_min"])
        ns = c1["native_stats"]
        lost = ns.get("collapses", 0)
        # every native people the galaxy has held (genesis and frontier clusters alike): still living, reached the
        # stars, or collapsed - and the share not destroyed
        ever = c1["natives"] + ns.get("first_flights", 0) + lost
        surviving = 1.0 - lost / max(1, ever)
        gate("native societies not destroyed", f">= {ACCEPTANCE['natives_surviving_min']:.0%}",
             f"{surviving:.0%} ({lost} collapsed, {ns.get('first_flights', 0)} reached the stars, "
             f"{c1['natives']} living)",
             surviving >= ACCEPTANCE["natives_surviving_min"])
        advances = ns.get("advances", 0) + ns.get("first_flights", 0)
        gate("native societies develop (stage advances)", ">= 1 by 5,000 cycles", advances,
             None if cycles < 5000 else advances >= 1)
        bk = c1["banking"]
        gate("clearing union conserves STAMP (accounts net to zero)", "|sum| < 0.01", bk["clearing_imbalance"],
             abs(bk["clearing_imbalance"]) < 0.01)
        gate("settlement chain seals and verifies", "blocks > 0, intact", f"{bk['chain_blocks']} blocks, "
             f"{bk['chain_verify'] or 'intact'}", bk["chain_blocks"] > 0 and not bk["chain_verify"])
        insolvent = [cur for cur, b in bk["banks"].items() if b["reserves"] < 0]
        gate("central banks solvent (reserves >= 0)", "none negative", insolvent or "all solvent", not insolvent)
        if c1.get("law"):
            lw = c1["law"]
            balance = lw["judged_sol"] - (lw["recovered_sol"] + lw["outstanding_sol"] + lw["written_off_sol"])
            gate("docket balances (judged = recovered + outstanding + written off)", "== 0", f"{balance:+,}", balance == 0)
            filed = max(1, lw["filed"])
            gate("crimes brought to court (detected share)", "0.2 .. 0.9", f"{lw['detected'] / filed:.0%} of {lw['filed']} "
                 f"({lw['by_kind']})", 0.2 <= lw["detected"] / filed <= 0.9 if lw["filed"] else None)
            if lw["judged_sol"]:
                gate("judgments recovered (share)", ">= 0.5", f"{lw['recovered_sol'] / lw['judged_sol']:.0%}",
                     lw["recovered_sol"] / lw["judged_sol"] >= 0.5)
        if "physics" in c1:
            ph = c1["physics"]
            gate("orbits never cross (spacing law, every system)", "0 violations",
                 f"{ph['spacing_violations']} of {ph['worlds']} worlds", ph["spacing_violations"] == 0)
        if "demography" in c1:
            tl_c = [snap for snap in r["world_timeline"] if "cosmos" in snap]
            mid = next((snap for snap in tl_c if snap["cycle"] >= cycles * 0.4), None)
            d1 = c1["demography"]
            if mid is not None:
                p_mid = mid["cosmos"]["demography"]["population"]
                gate("population keeps growing after 40% of the run", ">= +20%",
                     f"{p_mid:,} -> {d1['population']:,}", None if cycles < 5000 else d1["population"] >= 1.2 * p_mid)
            spend = sum(d1["stats"]["household_spend"].values())
            gate("households buy from starports", "> 0", f"{spend:,}", spend > 0)
            gate("frontier opens as peoples fill the galaxy", ">= 1 new cluster by 8,000 cycles",
                 len(d1["clusters"]) - 1, None if cycles < 8000 else len(d1["clusters"]) > 1)
        if "society" in c1:
            so = c1["society"]
            fz = so["fertility"]
            gate("fertility collapses under famine and bombardment (stressed / unstressed)", "<= 0.30",
                 f"{fz['stress_ratio_max']:.2f} over {fz['stressed_quarters']} stressed world-seasons",
                 fz["stress_ratio_max"] <= 0.30 if fz["stressed_quarters"] else None)
            gate("daughter-world dispersion (share of people on settled worlds)", "0.25 .. 0.40",
                 f"{so['daughter_share']:.1%}", None if cycles < 8000 else 0.25 <= so["daughter_share"] <= 0.40)
            spent = so["luxury"]["spend_sol"] + so["tourism"]["spend_sol"] + so["tourism"]["charters"]["paid_sol"]
            share = spent / so["gdp_sol"] if so["gdp_sol"] else 0.0
            gate("tourism and luxury share of income (GDP)", "0.05 .. 0.18",
                 f"{share:.1%} ({spent:,.0f} of {so['gdp_sol']:,} SOL)", 0.05 <= share <= 0.18 if so["gdp_sol"] else None)
            tl_s = [snap for snap in r["world_timeline"] if "cosmos" in snap and "society" in snap["cosmos"]]
            last = tl_s[-1] if tl_s else None
            prev = next((snap for snap in reversed(tl_s) if last and snap["cycle"] <= last["cycle"] - 1000), None)
            if last and prev:
                b0 = prev["cosmos"]["society"]["fertility"]["by_strategy"]
                b1 = last["cosmos"]["society"]["fertility"]["by_strategy"]
                growth = {k: round(b1[k]["people"] / b0[k]["people"], 2) for k in b1 if b0.get(k, {}).get("people")}
                gate("species fertility sanity (x population per strategy, last 1,000 cycles)", "0.5x .. 3x",
                     growth, all(0.5 <= g <= 3.0 for g in growth.values()) if growth else None)
        h = c1["houses"]
        gate("NPC lineages alive (end)", ">= 3 houses", f"{h['alive']} alive of {h['founded']} founded "
             f"({h['deaths']} deaths, {h['extinct']} extinct, {h['branches']} cadet branches)", h["alive"] >= 3)
        z = c1["powers"].get("ZEALOT")
        if z:
            gate("zealot territory (share of star systems)", f"<= {ACCEPTANCE['zealot_systems_share_max']:.0%}",
                 f"{z['systems_share']:.0%} (dogma {z['dogma']:.2f}, {z['stats'].get('purges', 0)} purges)",
                 z["systems_share"] <= ACCEPTANCE["zealot_systems_share_max"])
        imp = c1["powers"].get("IMPERIUM")
        if imp:
            gate("Imperial tithe delivered to the Fortress", "> 0", imp["stats"].get("tithe_delivered", 0),
                 imp["stats"].get("tithe_delivered", 0) > 0)
    if r.get("determinism"):
        d = r["determinism"]
        gate("deterministic across processes (same seed, different hash seeds)", "identical",
             f"{'identical' if d['identical'] else 'DIVERGED'} after {d['cycles']} cycles", d["identical"])
    gate("invariant violations", "0", sum(v["count"] for v in r["invariant_violations"]), not r["invariant_violations"])
    gate("exceptions", "0", sum(e["count"] for e in r["exceptions"]), not r["exceptions"])
    return gates


def print_report(r: Dict[str, Any]) -> None:
    p = r["performance"]
    print("\n" + "=" * 78)
    print(f" PLAYTEST REPORT  cycles={r['config']['cycles']:,}  seed={r['config']['seed']}")
    print("=" * 78)
    print(f"\n[PERFORMANCE] {p['cycles_per_sec']} cyc/s overall, wall {p['wall_seconds']}s, boot {p['boot_seconds']}s")
    print("  throughput by window: " + ", ".join(f"{w['cycles']}: {w['cycles_per_sec']}" for w in p["windows"]))
    print(f"  save {p['save_seconds']}s / {p['save_bytes']/1e6:.2f} MB, load {p['load_seconds']}s (ok={p['load_ok']}), "
          f"player view {p['player_view_ms']} ms / {p['player_view_bytes']/1e3:.0f} KB")
    print("  largest player-view sections: " + ", ".join(f"{k} {n/1e3:.0f}KB" for k, n in p.get("player_view_largest_sections", [])))
    print(f"  {'subsystem':<38}{'sec':>8}{'% tick':>8}{'calls':>10}{'us/call':>10}")
    for s in p["subsystems"]:
        print(f"  {s['subsystem']:<38}{s['seconds']:>8}{s['pct_of_tick']:>8}{s['calls']:>10}{s['us_per_call']:>10}")

    print("\n[UNBOUNDED GROWTH] (collections that grew over the run)")
    for g in r["growth"][:12]:
        print(f"  {g['collection']:<48} {g['start']:>7} -> {g['end']:>7}")

    print("\n[EXCEPTIONS]" + (" none" if not r["exceptions"] else ""))
    for e in r["exceptions"][:10]:
        print(f"  x{e['count']:<6} {e['where']}  ({e['example'][:80]})")

    print("\n[INVARIANT VIOLATIONS] (counted per 100-cycle check)" + (" none" if not r["invariant_violations"] else ""))
    for v in r["invariant_violations"]:
        print(f"  x{v['count']:<6} {v['kind']:<34} e.g. {v['example'][:70]}")

    print("\n[WORLD / AI ECONOMY]")
    tl = r["world_timeline"]
    picks = [tl[0]] + [tl[len(tl) * i // 4] for i in (1, 2, 3)] + [tl[-1]] if len(tl) >= 5 else tl
    print(f"  {'cycle':>6}{'captains':>9}{'AI money':>14}{'top%':>6}{'gini':>6}{'broke':>6}{'@sec1':>6}{'stuck':>6}{'claimed':>8}{'@cap':>5}")
    for s in picks:
        print(f"  {s['cycle']:>6}{s['captains']:>9}{s['ai_money']:>14,}{s['ai_top_share']*100:>5.0f}%{s['ai_gini']:>6}"
              f"{s['ai_broke_le_250']:>6}{s['ai_in_sector_1']:>6}{s['ai_stuck_5_snapshots']:>6}{s['planets_claimed']:>8}{s['planets_at_500k_cap']:>5}")

    m = r["money"]
    print("\n[MONEY SUPPLY] by currency, genesis -> end (stocks)")
    for cur, end_b in sorted(m["end"]["by_currency"].items()):
        gen_b = m["genesis"]["by_currency"].get(cur, {})
        print(f"  {cur}: total {gen_b.get('total', 0):>13,} -> {end_b['total']:>13,}   "
              + "  ".join(f"{k} {end_b.get(k, 0):,}" for k in ("captains", "planet_vaults", "port_treasuries",
                                                             "company_treasuries", "federal_reserve", "fx_pools", "contract_escrow")
                          if end_b.get(k)))
    print("  declared faucets (ledger mints): " + ", ".join(f"{k} {v:,}" for k, v in list(m.get("declared_mints", {}).items())[:10]))
    print("  net creation (+) / destruction (-) by source, valued at genesis price levels:")
    for k, v in sorted(m["net_flows"].items(), key=lambda kv: -abs(kv[1]))[:14]:
        print(f"    {k:<48}{v:>+16,}")
    if m.get("federal_stats"):
        print("  federal reserve activity: " + ", ".join(f"{k} {v:,}" for k, v in m["federal_stats"].items()))
    if tl and "ports_illiquid_by_currency" in tl[-1]:
        print(f"  illiquid ports by currency (end): {tl[-1]['ports_illiquid_by_currency']} of {tl[-1]['ports_by_currency']}")
    print("\n[FX & PHYSICAL ECONOMY]")
    print(f"  {'cycle':>6}{'FRN/SOL':>9}{'VOID/SOL':>9}{'policy S/F/V':>16}{'illiquid ports':>16}{'belt reserve':>14}{'debris':>8}{'sentries':>9}{'wanted':>8}{'AI FX (SOL)':>12}")
    for snap in ([tl[0]] + [tl[len(tl) * i // 4] for i in (1, 2, 3)] + [tl[-1]] if len(tl) >= 5 else tl):
        fxr = snap.get("fx_rates", {})
        pol = snap.get("policy", {})
        pol_s = "/".join(f"{pol.get(c, 1.0):.2f}" for c in ("SOL", "FRN", "VOID"))
        print(f"  {snap['cycle']:>6}{fxr.get('FRN', 0):>9.3f}{fxr.get('VOID', 0):>9.3f}{pol_s:>16}"
              f"{str(snap['ports_illiquid']) + '/' + str(snap['ports']):>16}{snap['belt_reserve_pct'] * 100:>13.0f}%"
              f"{snap['debris_fields']:>8}{snap['sentries_deployed']:>9}{snap['wanted_captains']:>8}{snap['ai_foreign_holdings_sol']:>12,}")
    if r.get("activity"):
        print("  activity: " + ", ".join(f"{k} {v:,}" for k, v in r["activity"].items() if not k.startswith("deed_fail::")))
    print(f"\n  {'cycle':>6}{'gini':>7}{'top%':>6}{'AI median':>11}{'fail-streak':>12}{'colonies(bots)':>16}")
    tl = r["world_timeline"]
    picks = [tl[0]] + [tl[len(tl) * i // 4] for i in (1, 2, 3)] + [tl[-1]] if len(tl) >= 5 else tl
    for snap in picks:
        print(f"  {snap['cycle']:>6}{snap['captain_gini']:>7}{snap['captain_top_share']*100:>5.0f}%{snap['ai_median_credits']:>11,}"
              f"{snap['deed_failure_streak_peak']:>12}{snap['colonies_founded_by_bots']:>16}")

    print("\n[PLAYER DELIVERY] (one autopilot captain per lineage, driven by the game's cognition; * = scripted baseline)")
    for b in r["bots"]:
        f = b["final"]
        asc = " -> ".join(a["to"] for a in b["ascensions"]) or "none"
        print(f"  {b['clade'][:4] + ('*' if b.get('kind') == 'scripted' else ''):<6} liquid={f.get('liquid_sol', 0):>9,} SOL (credits {f.get('credits', 0):,}, wallet {f.get('fx_wallet', {})})  tier={f.get('tier')}  node={f.get('node')}  "
              f"exp={f.get('exp')}  CR={f.get('credit_rating')}  crystals={f.get('crystals')}")
        print(f"             ascensions: {asc}   turn-starved actions: {b['turn_starved_actions']}   "
              f"net trade cashflow: {b['net_trade_cashflow']:,}   freight delivered: {b['freight_delivered']}   "
              f"cognition ok: {b['cognition_successes']}")
        dom = f.get("xp_domains", {})
        if dom:
            print("             experience by domain: " + ", ".join(f"{k} {v}" for k, v in sorted(dom.items(), key=lambda kv: -kv[1])))
        if b.get("persona"):
            print(f"             career ({b['persona']}): {b.get('career') or 'nothing yet'}")
        if b.get("colonies_founded"):
            print(f"             colonies founded: {b['colonies_founded']}")
        if b.get("hungry_samples"):
            print(f"             hungry at {b['hungry_samples']} of {len(b['timeline'])} samples")
        if b["ascension_blockers"]:
            print(f"             ascension blocked by: {b['ascension_blockers']}")
        for act, fails in b["top_failures"].items():
            total = b["actions"].get(act, 0)
            nf = sum(fails.values())
            if total and nf / total > 0.2:
                top = next(iter(fails))
                print(f"             {act}: {nf}/{total}+ failed, top: \"{top[:80]}\"")
    ce, cg = r.get("cosmos_end", {}), r.get("cosmos_genesis", {})
    tl_c = [snap for snap in r["world_timeline"] if "cosmos" in snap]
    picks_c = [tl_c[len(tl_c) * i // 5] for i in range(5)] + [tl_c[-1]] if len(tl_c) >= 6 else tl_c
    if ce:
        print("\n[COSMOS] alignment, locals, great powers, the Library")
        for label, key in (("all captains", "alignment"), ("private captains", "private_alignment")):
            a0, a1 = cg[key], ce[key]
            print(f"  {label:<17} mean {a0['mean']:+.3f} -> {a1['mean']:+.3f}   light/neutral/dark "
                  f"{a0['light']}/{a0['neutral']}/{a0['dark']} -> {a1['light']}/{a1['neutral']}/{a1['dark']}")
        print(f"  natives: {cg['natives']} -> {ce['natives']} societies, mean stage {cg['native_stage_mean']} -> "
              f"{ce['native_stage_mean']}, events {ce['native_stats']}")
        print(f"  doctrines: {ce['doctrines']}")
        for fid, pw in ce["powers"].items():
            print(f"  {fid}: worlds {pw['worlds']}, systems {pw['systems_share']:.0%}, fleet {pw['fleet']}, "
                  f"dogma {pw['dogma']}, stability {pw['stability']}, stats {pw['stats']}")
        print(f"  library: {ce['chronicle_entries']} records {ce['chronicle_kinds']}")
        print(f"  NPC houses: {ce['houses']}")
        if "demography" in ce:
            print("\n[PEOPLES] on-planet growth, the multi-planetary drive, households, the frontier")
            print(f"  {'cycle':>6}{'worlds':>8}{'population':>13}{'housing':>13}{'habitats':>10}{'sectors':>9}  policies")
            for snap in picks_c:
                d = snap["cosmos"]["demography"]
                print(f"  {snap['cycle']:>6}{d['worlds']:>8}{d['population']:>13,}{d['housing']:>13,}{d['habitats']:>10}"
                      f"{d['sectors']:>9}  {d['policies']}")
            d = ce["demography"]
            st = d["stats"]
            print(f"  citadels {d['citadel_tiers']}; councils raised {st['citadels']} citadels, dug {st['habitats']} habitats")
            print(f"  settler fleets: {st['daughters']} daughter worlds, {st['emigrants']:,} emigrants, "
                  f"{st['no_room']} found no world in reach; steady-state worlds {st['steady']}")
            print(f"  households: {st['household_units']:,} units bought, spend {st['household_spend']}, shortages {st['shortages']}")
            print(f"  exports: worlds sold their surplus harvest and ore to regional ports for {st.get('exports', {})}")
            print(f"  frontier: clusters {d['clusters']}, opened {st['clusters_opened']}")
        if "physics" in ce:
            ph = ce["physics"]
            print(f"  physics: {ph['worlds']} worlds {ph['types']}, {ph['tidally_locked']} tidally locked, "
                  f"{ph['spacing_violations']} spacing violations")
        if ce.get("credit"):
            cr = ce["credit"]
            print(f"  credit: lent {cr.get('lent', 0):,}, interest {cr.get('interest', 0):,}, margin calls {cr.get('margin_calls', 0)}, "
                  f"defaults {cr.get('defaults', 0)} (written off {cr.get('written_off', 0):,}), corporate levy {cr.get('levied', 0):,}")
        if ce.get("geology"):
            g = ce["geology"]
            print(f"  geology: mined crusts {g['crust_remaining_mean']} remaining on average (lowest {g['crust_remaining_min']}), "
                  f"renewal / extraction {g['renewal_to_extraction']}, {g['stats']}")
        if ce.get("law"):
            lw = ce["law"]
            print(f"  law: {lw['filed']} offences {lw['by_kind']}, {lw['detected']} brought to court, {lw['unsolved']} unsolved "
                  f"({lw['haven']} in havens), {lw['convicted']} convicted; judged {lw['judged_sol']:,}, recovered "
                  f"{lw['recovered_sol']:,}, outstanding {lw['outstanding_sol']:,}; {lw['warrants']} warrants, {lw['freezes']} freezes")
        if ce.get("crime"):
            cr = ce["crime"]
            print(f"  crime: attempted {cr.get('attempted')}, succeeded {cr.get('succeeded')}, "
                  f"skimmed {cr.get('skimmed_sol', 0):,} SOL, civilization raids {cr.get('raids', 0)}")
        if ce.get("society"):
            so = ce["society"]
            fz, lx, tu = so["fertility"], so["luxury"], so["tourism"]
            print(f"  fertility by strategy: {fz['by_strategy']}; natal cards {fz['natal_cards']}; "
                  f"{fz['stressed_quarters']} stressed world-seasons; {fz['recruits']:,} hatched fanatics")
            print(f"  luxury: crafted {lx['crafted']}, bought {lx['bought']}, own use {lx['own_use']:,}, spoiled "
                  f"{lx['spoiled']:,}; wants met {lx['access']:.0%}; signatures {lx['signatures']}")
            if lx["examples"]:
                print(f"    e.g. {'; '.join(lx['examples'])}")
            ch = tu["charters"]
            print(f"  tourism: {tu['trips']:,} trips, spent {tu['spend_sol']:,.0f} SOL (fares {tu['fares_sol']:,.0f}), "
                  f"{tu['domes']} pleasure domes, {tu['stations']} orbital stations, H burned {tu['h_burned']:,}, "
                  f"{tu['h_short_trips']:,} trips grounded for want of hydrogen")
            print(f"  VIP charters: posted {ch['posted']}, flown {ch['flown']} (paid {ch['paid_sol']:,.0f} SOL), ransomed "
                  f"{ch['ransomed']} ({ch['ransom_sol']:,.0f} SOL), expired {ch['expired']}; daughter-world share "
                  f"{so['daughter_share']:.1%}; income (GDP) {so['gdp_sol']:,} SOL")
        if ce.get("realms"):
            rl = ce["realms"]
            print(f"  realms: {rl['realms']} ({rl['houses']} captains' houses) claiming {rl['claimed_systems']} systems, "
                  f"{rl['contested']} contested; founded {rl['founded']}, seceded {rl['seceded']}, dissolved {rl['dissolved']}")
            if rl["largest"]:
                print(f"    largest: {'; '.join(rl['largest'])}")
        if ce.get("workbench"):
            wb = ce["workbench"]
            print(f"  workbench: {wb['designs']} designs ({wb['ai_designs']} by AI draughtsmen), cells {wb['by_drive']}, "
                  f"flying {wb['flying']}, royalties {wb['royalties']:,}")
            if wb["examples"]:
                print(f"    e.g. {'; '.join(wb['examples'])}")
        if ce.get("government"):
            gv = ce["government"]
            print(f"  government: starports run by {gv['port_owners']}; treasuries (SOL) {gv['vaults_sol']}; "
                  f"office holders {gv['holders']}")
            print(f"    revenue {gv['revenue']}; civilizations' port & station revenue {gv['civ_revenue']:,}")
            print(f"    spent {gv['spent']}; stipends {gv['stipends']:,}")
        if ce.get("propulsion"):
            pr, ind = ce["propulsion"], ce.get("industry", {})
            print(f"  propulsion: {pr.get('burned', 0):,} reaction mass burned, {pr.get('bunkered', 0):,} bunkered at ports, "
                  f"{pr.get('coasted', 0):,} jumps coasted dry; drifting gas {ind.get('sector_gas', 0):,}")
            print(f"  wells & drives: skimmed {pr.get('skimmed_h', 0):,} H and {pr.get('skimmed_he3', 0):,} He-3 from gas "
                  f"giants; refits {pr.get('refits', {})} ({pr.get('warp_jumps', 0):,} warp jumps, "
                  f"{pr.get('cores_burned_out', 0)} cores burned out); burned by fuel {pr.get('burned_by_fuel', {})}")
            print(f"  peoples' fuel cells {pr.get('civ_fuels', {})}; degraded worlds {pr.get('degraded_worlds', 0)}")
            print(f"  industry: fabricated {ind.get('fabricated', {})}, recycled to ore {ind.get('recycled_ore', 0):,}")
        if "fibres" in ce:
            fb = ce["fibres"]
            print(f"  fibres: {fb['passages']:,} passages, {fb['developed_lanes']} of {fb['lanes']} lanes developed, "
                  f"top 10% of lanes carry {fb['trunk_share']:.0%} of development, trunks {fb['trunks']}, "
                  f"cheapest transit x{fb['cheapest_cost']}")
        bk = ce.get("banking", {})
        if bk:
            print(f"  clearing union: STAMP imbalance {bk['clearing_imbalance']}, settlement chain {bk['chain_blocks']} blocks "
                  f"(verify: {bk['chain_verify'] or 'ok'}), Galactic ISSE cross volume {bk['cross_volume_sol']:,} SOL, "
                  f"arbitrage {bk.get('arbitrage')}, widest cross-rate gap {bk.get('cross_gap_max', 0):.1%}")
            for cur, b in bk["banks"].items():
                print(f"    {cur}: reserves {b['reserves']:,}  loans {b['loans']:,}  rate/q {b['rate']:.4f}  STAMP {b['stamp']:+,}  {b['stats']}")
        for e in r.get("chronicle_samples", []):
            print(f"    - [{e['kind']}] {e['title']} (cycle {e['cycle']}): {e['body'][:220]}")
    mt = r["money"].get("matter")
    if mt:
        print("\n[MATTER] declared sources and sinks, never netted (largest)")
        print("  sources: " + ", ".join(f"{k}/{c} {v:,}" for k, c, v in mt["sources"][:8]))
        print("  sinks:   " + ", ".join(f"{k}/{c} {v:,}" for k, c, v in mt["sinks"][:8]))
    print("\n[LAWS] invariants of the universe's physics and ledgers")
    for g in r["acceptance"]:
        if g.get("law"):
            print(f"  [{g['result']:>4}] {g['gate']:<52} target {str(g['target']):<14} actual {g['actual']}")
    print("\n[OBSERVATIONS] emergent outcomes against a band of interest (never failed)")
    for g in r["acceptance"]:
        if not g.get("law"):
            print(f"  [{g['result']:>4}] {g['gate']:<52} band {str(g['target']):<16} actual {g['actual']}")
    fails = sum(1 for g in r["acceptance"] if g["result"] == "FAIL")
    notes = sum(1 for g in r["acceptance"] if g["result"] == "note")
    print(f"  => {'ALL LAWS HOLD' if not fails else f'{fails} LAW(S) BROKEN'}; {notes} observation(s) outside their band")
    if r["hotspots"]:
        print("\n[cProfile HOTSPOTS]\n" + "\n".join(r["hotspots"].splitlines()[:45]))


def main() -> None:
    ap = argparse.ArgumentParser(description="Xylarium long-horizon playtest & bottleneck harness")
    ap.add_argument("--cycles", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--actions-per-cycle", type=int, default=1, help="Bot actions per world tick")
    ap.add_argument("--profile", action="store_true", help="Include cProfile hotspots")
    ap.add_argument("--out", default=None, help="Write full JSON report here")
    ap.add_argument("--save-state", default=None, help="Also save the final universe to this path (never the live save)")
    ap.add_argument("--determinism-cycles", type=int, default=300,
                    help="Cycles for the cross-process determinism law (0 to skip)")
    args = ap.parse_args()

    print(f"Xylarium playtest: {args.cycles:,} cycles, seed {args.seed}, bots {BOT_CLADES}")
    report = run(args.cycles, args.seed, args.actions_per_cycle, args.profile, args.save_state,
                 args.determinism_cycles)
    print_report(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nFull JSON report: {args.out}")


if __name__ == "__main__":
    main()
