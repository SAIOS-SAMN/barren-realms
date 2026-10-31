# 🌌 BARREN REALMS (XYLARIUM)
### *Autonomous Grand Strategy Universe & Galactic Civilization Simulation Engine*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Lineage: TW2002 / BRE / SRE](https://img.shields.io/badge/lineage-TradeWars%202002%20%7C%20BRE%20%7C%20SRE-orange.svg)]()
[![Conserved Arithmetic: Exact Q](https://img.shields.io/badge/arithmetic-Exact%20ℚ%20Conservation-green.svg)]()
[![Architecture: Decoupled Kernel](https://img.shields.io/badge/architecture-Zero--UI%20Kernel%20%7C%20Mesh%20Ready-purple.svg)]()

> **Barren Realms** is a deep, persistent grand strategy game and exact universe simulation blending high-stakes interstellar trade, complex multi-tier logistics, living galactic civilizations, planetary colonization, astrodynamics, and sovereign autonomous AI minds.
>
> Built in the classic lineage of BBS door game legends—**TradeWars 2002**, **Barren Realms Elite (BRE)**, and **Solar Realms Elite (SRE)**—Barren Realms unites retro text-based tactical speed with an exact mathematical simulation engine where every star orbit, gram of ore, colonist life, credit, and sovereign cognitive decision is rigorously conserved.

---

## 📑 Table of Contents

- [🌌 Core Pillars of the Grand Strategy Game](#-core-pillars-of-the-grand-strategy-game)
  - [1. Trade & Macroeconomic Architecture](#1-trade--macroeconomic-architecture)
  - [2. Industrial Supply Chains & Logistics](#2-industrial-supply-chains--logistics)
  - [3. Galactic Civilizations, Polities & Demographics](#3-galactic-civilizations-polities--demographics)
  - [4. Autonomous Sovereign AI Minds](#4-autonomous-sovereign-ai-minds)
  - [5. Astrodynamics, Fleet Warfare & Planetary Sieges](#5-astrodynamics-fleet-warfare--planetary-sieges)
- [🏛️ System Architecture](#️-system-architecture)
  - [Exact Rational Arithmetic ($\mathbb{Q}$) & Seam Conservation](#exact-rational-arithmetic-mathbbq--seam-conservation)
  - [Decoupled Event-Driven Engine](#decoupled-event-driven-engine)
  - [Dual Interface: BBS Terminal & Modern Network Gateway](#dual-interface-bbs-terminal--modern-network-gateway)
- [📂 Repository Layout](#-repository-layout)
- [⚡ Quickstart & Play](#-quickstart--play)
  - [1. Interactive ANSI Terminal Game](#1-interactive-ansi-terminal-game)
  - [2. Multi-Protocol Daemon (Telnet + WebSockets)](#2-multi-protocol-daemon-telnet--websockets)
  - [3. Headless Simulation Pass](#3-headless-simulation-pass)
  - [4. Running the Test Suite](#4-running-the-test-suite)
- [🎮 Complete Command & Career Reference](#-complete-command--career-reference)
- [📜 Scientific & Architectural Documentation](#-scientific--architectural-documentation)
- [🤝 Lineage & Philosophy](#-lineage--philosophy)

---

## 🌌 Core Pillars of the Grand Strategy Game

### 1. Trade & Macroeconomic Architecture

Barren Realms simulates an un-faked, closed-loop macroeconomic system where wealth is not spawned from thin air; it circulates according to dynamic price elasticity and the classic equation of exchange ($M \cdot V = P \cdot Y$):

* **BBS-Style Commodity Markets (`economy.py`, `market.py`)**:
  * Ports across the 100-sector universe buy and sell primary commodities: **Ore** (foundry industrial substrate), **Organics** (food, biomaterials, life support), and **Equipment** (weaponry, engines, electronics).
  * Classic 8-class port typology (e.g., Class 1 `BBS`, Class 2 `BSB`, Class 4 `SSB`, Class 0 `Stardock`).
  * Real-time supply and demand curves: aggressive buying depletes stock and escalates prices; massive cargo dumps saturate the port and crash local margins.
* **Interstellar Stock Exchange (ISSE) & Corporate IPOs (`business.py`, `market.py`)**:
  * Players and NPC factions can incorporate joint-stock enterprises, float them on public exchanges, issue corporate debt, pay dividends, and short over-leveraged competitors.
  * Corporate warfare: hostile takeovers, asset liquidations, and predatory market cornering.
* **Foreign Exchange & Monetary Regimes (`fx.py`, `banking.py`, `regimes.py`, `backing.py`)**:
  * Sovereign polities issue their own currencies backed by diverse asset reserves (Solar bullion, He-3 reserves, debt instruments, or fiat authority).
  * Arbitrage currency routes across interstellar exchange desks with floating exchange rates, central bank interest rate spreads, and debasement penalties.
* **Freight Contracts & Logistics Charters (`transit.py`, `credit.py`)**:
  * Haul high-volume freight under deadline constraints, transport VIP dignitaries across contested sectors, and leverage commercial margin accounts.

---

### 2. Industrial Supply Chains & Logistics

Victory in Barren Realms is rooted in physical logistics—moving mass across deep space under fuel, payload, and planetary capacity constraints:

* **Resource Extraction & Planetary Geology (`geology.py`, `mining`)**:
  * Planetary crusts hold finite mineral reserves renewed through slow tectonic cycles.
  * Solar wind sweeps airless worlds to deposit **Helium-3** for fusion drives; active volcanic worlds outgas volatile compounds; deep mantle deposits hold decaying radioactives.
* **Processing & Industrial Workbenches (`workbenches.py`, `chemistry.py`, `energy.py`)**:
  * Raw ore is smelted into structural composites, crystalline matrices, and advanced hull plating.
  * Planetary refineries produce propulsion fuels, atmosphere scrubbers, and automated planetary defense arrays.
* **Warehousing & Transit Networks (`cargo.py`, `waystations.py`, `routes.py`)**:
  * Establish bonded warehouses and deep-space orbital waystations along major warp corridors.
  * Automated transport routing calculates optimal multi-hop paths, accounting for fuel burn, local pirate hazards, and trade lane congestion.

---

### 3. Galactic Civilizations, Polities & Demographics

Planets are living societal ecosystems that evolve, prosper, or fall into ruin based on governance, culture, and environmental pressure:

* **Planetary Colonization & Citadel Progression (`colony.py`, `settling.py`)**:
  * Claim unsettled worlds across the galaxy and establish planetary colonies.
  * Manage population growth, housing capacity, agricultural yields, and tax collection.
  * Construct and upgrade planetary citadels across four defensive tiers:
    * **Tier 0: Barren Outpost** — Rudimentary colony shelters.
    * **Tier 1: Fortified Redoubt** — Defensive bastions with +50% tax revenue and planetary shield arrays.
    * **Tier 2: Planetary Stronghold** — Industrial fortress world with +120% tax yields and heavy surface batteries.
    * **Tier 3: Imperial Citadel** — Galactic capital redoubt with +250% taxation multiplier, impenetrable planetary shields, and dedicated fighter garrisons.
* **Multispecies Xenobiology & Clades (`clade_nursery.py`, `phylogeny.py`, `xenobiology.py`)**:
  * Distinct galactic clades with unique metabolic and environmental requirements: **Biotic** (carbon-based organics), **Lithic** (silicate mineral life), **Plasmic** (high-energy magnetospheric beings), and **Cryogenic** (liquid-methane cold-world entities).
  * Demographic dynamics: birth rates, biological lifespans, specialized nurseries, genetic drift, and epidemic blights.
* **Polity, Governance & Law (`government.py`, `polity.py`, `realms.py`, `factions.py`)**:
  * 9 distinct planetary polities spanning democratic confederations, autocratic dynasties, corporate cartels, and anarchist border syndicates.
  * Senate elections and legislative lobbying: pass interstellar tariffs, vote on naval appropriations, grant settlement charters, and establish sector quarantine zones.
  * Covert operations (`covert.py`): planetary infiltration, industrial espionage, sabotage of orbital batteries, and inciting colonial insurrections.

---

### 4. Autonomous Sovereign AI Minds

Barren Realms does not rely on scripted state machines or external LLM prompt-wrappers. Non-player captains and imperial governors are autonomous cognitive agents operating on exact mathematical decision manifolds:

* **EventBus Reactive Intelligence (`ai.py`, `sovereign_mind.py`)**:
  * Autonomous captains listen to subspace radio events and react instantaneously to real-time player actions.
  * **Cynthia Voss (Voss Megacorporation)**: Monopolistic corporate governor who aggressively defends territorial borders, issues legal cease-and-desist ultimatums, and deploys privateer strike fleets against encroaching players.
  * **Malakor the Red (Void Corsair King)**: Predatory pirate warlord tracking high-value cargo shipments ($\ge 25$ Equipment or $\ge 10,000$ Credits) through the Borderlands with breadth-first search (BFS) intercept vectors.
  * **Ironclaw Rake (Federal Marshal & Bounty Hunter)**: Law enforcement agent monitoring sector crime; pays cash bounties (+5,000 Credits) to captains who destroy wanted outlaws.
  * **Capt. Jack Vane (Arbitrage Smuggler)**: Master commercial agent continuously calculating dynamic trade loops across the galaxy to exploit market inefficiencies.
* **Sovereign Cognitive Architecture (`cognition.py`, `intellect.py`, `decide.py`)**:
  * Evaluates multi-horizon mental rollouts across Pareto-optimal trade, military, and diplomatic vectors.
  * Incorporates theory-of-mind doctrine classification to anticipate player military strikes and economic embargoes.

---

### 5. Astrodynamics, Fleet Warfare & Planetary Sieges

Combat and spaceflight operate under rigorous physical laws rather than abstract dice rolls:

* **Astrodynamics & Stellar Systems (`physics.py`, `cosmos.py`, `orbits.py`)**:
  * Stellar luminosity scales with mass ($L = m^7$).
  * Planets follow non-intersecting Keplerian orbits ($a = q^2 \text{ AU}$) with exact orbital periods, axial tilts, and seasonal cycles (100 cycles per year, 25 cycles per fiscal quarter).
  * Relativistic propellant burns and fuel-cell efficiency dictate warp feasibility and fleet operational range.
* **Custom Ship Design & Modular Hulls (`shipdesign.py`, `propulsion.py`)**:
  * Design custom vessels on the shipwright workbench: fast reconnaissance Scouts, heavy bulk Merchant Freighters, strike Cruisers, and super-capital Dreadnoughts.
  * Balance hull mass, reactor output, shield generators, cargo hold capacity, and point-defense fighter bays.
* **Tactical Naval Combat & Orbital Sieges (`combat.py`, `surface.py`)**:
  * Real-time space combat featuring energy shield harmonics, kinetic railgun salvos, torpedo strikes, and defensive fighter dogfights.
  * Planetary orbital bombardments: strip planetary shields, breach fortified citadels, destroy surface infrastructure, and land colonial invasion divisions.

---

## 🏛️ System Architecture

### Exact Rational Arithmetic ($\mathbb{Q}$) & Seam Conservation

In traditional simulation games, cumulative floating-point errors ($0.1 + 0.2 \neq 0.3$) corrupt economic ledgers, allow duplicate item exploits, and create infinite money glitches.

In **Barren Realms**, every value crossing an architectural seam is modeled as an exact rational number $\mathbb{Q} \in \text{fractions.Fraction}$:
* Ledgers, banking balances, and tax receipts balance to the exact integer numerator and denominator.
* Physical matter, ore mass, and chemical reagents are strictly conserved across production chains.
* Total currency in circulation is bounded by strict monetary conservation theorems.

### Decoupled Event-Driven Engine

The simulation engine (`xylarium/kernel/`) contains **zero UI code**. It is completely separated from the presentation layer:

```
┌────────────────────────────────────────────────────────┐
│               PRESENTATION & ACCESS LAYERS             │
├──────────────────┬──────────────────┬──────────────────┤
│ Classic ANSI/DOS │ RFC 854 Telnet   │ RFC 6455 WebSock │
│ Terminal (CLI)   │ Server (:2002)   │ Gateway (:8765)  │
└────────┬─────────┴────────┬─────────┴────────┬─────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│            XYLARIUM DECOUPLED GAME KERNEL              │
├────────────────────────────────────────────────────────┤
│ • Action Dispatcher & Turn Engine (engine.py)          │
│ • Subspace Radio EventBus (events.py)                  │
│ • Dynamic BBS Economy & Port Ledger (economy.py)       │
│ • Planetary Colonization & Citadels (colony.py)        │
│ • Keplerian Astrodynamics & Relativity (physics.py)    │
│ • Autonomous Cognitive AI Rivals (sovereign_mind.py)   │
└────────────────────────────────────────────────────────┘
```

### Dual Interface: BBS Terminal & Modern Network Gateway

* **Authentic Terminal MUD**: 16-color high-contrast ANSI art, persistent heads-up display (HUD), and lightning-fast single-keystroke command dispatch.
* **Headless Network Daemon**: Multi-client Telnet server and asynchronous WebSocket gateway enabling integration into modern web frontends, Discord bots, or autonomous AI agent meshes.

---

## 📂 Repository Layout

```
/opt/barren-realms/
├── main.py                         # Unified entrypoint (Interactive, Demo, Daemon)
├── xylarium_save.json              # Persistent universe state (JSON export)
├── launch-galaxy.sh                # Production cluster bootstrap script
│
├── xylarium/                       # Core Package
│   ├── config.py                   # Ship catalogs, universe balance & economic constants
│   ├── kernel/                     # Decoupled Game Kernel (No UI dependencies)
│   │   ├── engine.py               # GameKernel coordinator, turn cycles, action dispatch
│   │   ├── models.py               # Sector, Port, Planet, Ship, Captain, Cargo dataclasses
│   │   ├── economy.py              # Dynamic price curves, stock replenishment, trade
│   │   ├── colony.py               # Planetary settlements, taxation, citadel upgrades
│   │   ├── combat.py               # Tactical space combat and planetary sieges
│   │   ├── ai.py                   # Autonomous rival captains & corporate directors
│   │   ├── sovereign_mind.py       # Exact cognitive decision manifolds & rollouts
│   │   ├── physics.py              # Keplerian astrodynamics & relativistic propellant
│   │   ├── universe.py             # Deterministic 100-sector warp network topology
│   │   └── events.py               # Subspace radio event emitter & pub/sub bus
│   ├── client/                     # Presentation Layer
│   │   ├── cli.py                  # Interactive terminal loop & keyboard dispatcher
│   │   ├── renderer.py             # High-contrast ANSI HUD, sector scans, planet menus
│   │   └── ansi.py                 # Authentic DOS/BBS color codes and ASCII banners
│   └── persistence/
│       └── store.py                # Universe state serialization & atomic save engine
│
├── bridge/                         # Multi-Protocol Network Daemon
│   ├── daemon.py                   # Async background service coordinator
│   ├── telnet_server.py            # RFC 854 classic Telnet gateway (Port 2002)
│   └── websocket_server.py         # RFC 6455 JSON WebSocket gateway (Port 8765)
│
├── docs/                           # Deep Architectural & Scientific Specifications
│   ├── GAME.md                     # Comprehensive player handbook & mechanics Bible
│   ├── STANDARDS.md                # Engineering rules, conservation invariants, DoD
│   ├── UPGRADES.md                 # Physical manifold expansions & non-Euclidean metrics
│   ├── ADVANCED_SOVEREIGN_COGNITION_SCOPE.md
│   └── SOVEREIGN_COGNITION_SPEC.md
│
└── tests/                          # Automated Verification Suite
    ├── test_kernel.py              # Universe topology, trade curves, combat calculations
    ├── test_sovereign_mind.py      # AI decision manifold & theory-of-mind tests
    ├── test_bridge.py              # Telnet & WebSocket network integration tests
    └── test_emergent_economy.py    # Closed-loop monetary conservation tests
```

---

## ⚡ Quickstart & Play

Barren Realms requires standard **Python 3.10+** and has **zero mandatory external C/GUI dependencies**.

### 1. Interactive ANSI Terminal Game

Launch directly into the retro terminal interface:
```bash
python3 main.py
```

Launch with a custom captain name, starting ship, and deterministic universe seed:
```bash
python3 main.py --name "Admiral Vance" --seed 1337
```

### 2. Multi-Protocol Daemon (Telnet + WebSockets)

Start the concurrent background server hosting both Telnet and WebSocket connections:
```bash
python3 main.py --bridge --telnet-port 2002 --ws-port 8765
```

* **Connect via Telnet (Retro BBS Client)**:
  ```bash
  telnet localhost 2002
  ```
* **Connect via WebSockets (Modern Frontends & AI Agents)**:
  ```
  ws://localhost:8765/ws
  ```

### 3. Headless Simulation Pass

Verify universe generation, economy cycles, and AI logic without launching the interactive UI:
```bash
python3 main.py --demo
```

### 4. Running the Test Suite

Run the full regression test suite:
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Run focused kernel tests:
```bash
python3 -m unittest tests/test_kernel.py tests/test_sovereign_mind.py
```

---

## 🎮 Complete Command & Career Reference

### In-Game Command Console

Commands can be invoked by single keystroke or full keyword:

| Command | Key | Description |
|---|---|---|
| `MOVE` | `M` | Warp through wormholes to adjacent sectors. |
| `TRADE` | `T` | Dock at local port to buy/sell Ore, Organics, and Equipment. |
| `PLANET` | `P` | Land on planetary surface: claim world, tax colonists, upgrade citadel. |
| `ATTACK` | `A` | Engage hostile captains, pirate raiders, or orbital defense stations. |
| `SHIPYARD`| `S` | Dock at Stardock (Sector 1): purchase new hulls, recharge shields, hire fighters. |
| `COMPUTER`| `C` | Access Galactic Computer: view universe map, port listings, and market data. |
| `RADIO` | `R` | Tune subspace transceiver to monitor rival AI broadcasts and bounty alerts. |
| `ADVISOR` | `?` | Context-aware advisor analyzing highest-margin trade routes and strategic moves. |
| `QUIT` | `Q` | Save universe state to disk and exit cleanly. |

### Player Career Paths

* **Interstellar Merchant**: Plot high-margin arbitrage runs between complementary ports (e.g. buying Ore at Class 2 and selling at Class 1).
* **Industrial Baron**: Mine asteroid belts, establish planetary refineries, and supply manufacturing hubs.
* **Planetary Governor**: Settle uncolonized worlds, balance natal policy and tax rates, and construct Tier 3 Imperial Citadels.
* **Corporate Financier**: Found enterprises, issue stock on the ISSE, manage debt ratios, and engage in corporate raiding.
* **Void Corsair / Warlord**: Ambush merchant haulers in deep-void anarchy sectors, evade federal authorities, and conquer rival citadels.
* **Federal Marshal**: Hunt down wanted outlaws across the Borderlands to claim substantial central bank bounties.

---

## 📜 Scientific & Architectural Documentation

For deep dives into the theoretical foundations, engineering invariants, and mathematical specifications:

* **[Player Handbook & Game Bible (`docs/GAME.md`)](docs/GAME.md)**: Exhaustive manual detailing careers, commodities, ships, galactic polities, and universal laws.
* **[Engineering Standards & Invariants (`docs/STANDARDS.md`)](docs/STANDARDS.md)**: Rules of the codebase, conservation theorems, and definition of done.
* **[Physical Manifold Upgrades (`docs/UPGRADES.md`)](docs/UPGRADES.md)**: Non-Euclidean geometries, relativistic propellant mechanics, and $SU(2)$ gauge fields.
* **[Sovereign Cognition Specification (`docs/SOVEREIGN_COGNITION_SPEC.md`)](docs/SOVEREIGN_COGNITION_SPEC.md)**: Autonomous agent architectures, decision manifolds, and closed-loop cognition.

---

## 🤝 Lineage & Philosophy

Barren Realms honors the pioneers of text-based grand strategy:
* **TradeWars 2002** (*Gary Martin, MaryAnn Martin*): For the definitive blueprint of space trading, port classes, and contested sector navigation.
* **Barren Realms Elite** (*Mehdi Sotoodeh / Amit Patel*): For planetary colonization, strategic warfare, inter-realm politics, and citadel sieges.
* **Solar Realms Elite** (*Amit Patel*): For planetary ecology, population dynamics, and economic realism.

By combining this legendary heritage with **exact rational arithmetic**, **sovereign AI cognition**, and a **modern decoupled asynchronous architecture**, Barren Realms delivers an uncompromising grand strategy universe built to endure.

---
*Maintained under the [SAIOS-SAMN](https://github.com/SAIOS-SAMN) organization.*
