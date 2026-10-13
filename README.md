# 🌌 XYLARIUM: The Barren Realms

> **A Classic ASCII MUD & BBS Door Game Kernel**  
> *Combining the mechanics of TradeWars 2002, Barren Realms Elite (BRE), and Solar Realms Elite (SRE).*

---

## 🚀 Overview

**Xylarium** returns to the golden era of BBS door games: pure text-based tactical depth, lightning-fast execution, zero bloated 2D rendering dependencies, and a decoupled, event-driven kernel built from the ground up to plug directly into terminal clients, WebSocket servers, or autonomous Mycelium mesh networks.

---

## 📚 Documentation

* **[docs/UPGRADES.md](docs/UPGRADES.md)** - master documentation of physical manifold upgrades: Einstein-Cartan singularity bounces, non-Euclidean Riemannian metrics, non-abelian $SU(2)$ gauge cohomology, Pareto decision manifolds, and sovereign agency.
* **[docs/MANIFOLD_REMEDIATION.md](docs/MANIFOLD_REMEDIATION.md)** - remediation of dimensional collapse across decisions, spherical planetary surfaces, ideology tensors, and potential fields.
* **[docs/NEXT_CYCLE_SCOPE.md](docs/NEXT_CYCLE_SCOPE.md)** - engineering scope specification for the 5 fundamental manifold expansions.
* **[docs/GAME.md](docs/GAME.md)** - the game as it is today: careers, the universe, peoples, money, polity, ships,
  the AI, the laws of the universe and the commands.
* **[docs/STANDARDS.md](docs/STANDARDS.md)** - engineering standards: the principles every change models, the
  architecture rules (subsystems, state, topology, caching, immutable config, action registry) and the definition
  of done.

---

## 📂 Directory Structure

```
/opt/barren-realms/
├── main.py                         # Direct boot script and entrypoint
├── xylarium_save.json              # Automatic JSON state persistence
├── xylarium/
│   ├── __init__.py                 # Package version and metadata
│   ├── config.py                   # Universe, ship catalogs, citadel balance constants
│   ├── kernel/                     # Decoupled Game Kernel (No UI dependencies)
│   │   ├── __init__.py
│   │   ├── models.py               # Sector, Port, Planet, Ship, Captain, CargoHold dataclasses
│   │   ├── universe.py             # Deterministic 100-sector network with guaranteed spanning reachability
│   │   ├── economy.py              # Dynamic BBS supply/demand pricing curve & stock replenishment
│   │   ├── colony.py               # BRE/SRE planetary colonization, taxation, and citadel upgrades
│   │   ├── combat.py               # Tactical ship-to-ship and orbital siege combat engine
│   │   ├── ai.py                   # Heuristic autonomous rival captains (Traders, Pirates, Warlords)
│   │   ├── events.py               # Subspace radio transmission bus & event emitter
│   │   └── engine.py               # GameKernel orchestrator, action dispatching, turn management
│   ├── client/                     # Terminal / ASCII Presentation Layer
│   │   ├── __init__.py
│   │   ├── ansi.py                 # Authentic DOS/BBS ANSI color palette and logo art
│   │   ├── renderer.py             # High-contrast HUD, Sector Scans, Trade terminals, Planet screens
│   │   └── cli.py                  # Interactive command prompt loop with letter/number dispatch
│   └── persistence/
│       ├── __init__.py
│       └── store.py                # JSON export and import for universe & game states
├── bridge/                         # Mycelium Bridge (Async Network Layer)
│   ├── __init__.py
│   ├── websocket_server.py         # RFC 6455 WebSocket Gateway (/ws) for JSON dispatch & views
│   ├── telnet_server.py            # Classic RFC 854 Telnet server on port 2002
│   └── daemon.py                   # Async daemon runner (WebSocket + Telnet listeners)
└── tests/
    ├── __init__.py
    ├── test_kernel.py              # Core mechanics (universe, economy, colonization, combat)
    ├── test_ai_reactions.py        # EventBus reactive AI tests (Voss, Malakor, Ironclaw)
    └── test_bridge.py              # WebSocket and Telnet integration tests
```

---

## ⚖️ Exact at the Seams (prototype note)

This Python kernel is the PROTOTYPE: an example to copy, not the end state. Any value that crosses a SEAM is an exact
`fractions.Fraction` (or an int, or a Fraction's string): ledgers, the reserve and its basket, the steward books (pairs),
anything appended to the hypha or sent to a court, anything exchanged with another node. New code is written exact.

The legacy simulation inside these modules still runs on floats - **do not copy the float pattern**: `fx`, `ledger`
(MonetaryPolicy), `backing` (value_sol, measure, arbitrage), `regimes`, `estates` (output), `transit` (pricing and
routing), `endowments`, `blackhole` (engines), `market`, `economy`, `liquidity`, `luxury`, `energy`, `worlds`, `cosmos`,
`creation`, `settling`, `cognition`, `enrichment`, `substances`, `relations`, `annals`, `alignment`, `geometry`,
`interior`, `phylogeny`, `motive`, `lifespan`, `genome`, `hydromagnetics`, `fertility`, `encircle`, `life`, `society`,
`waste`, `knowledge`, `memory`, `fibres`, `rent`, `natives`, `noble`, `harvest`, `biosphere`, `decide`.

Where an exact book reads one of these float sources, it carries the float's own binary value (`Fraction(float)`),
never a declared quantum or a rounding: `rent.of` (restraint), `alignment.causes` (order), `memory.truth` (history),
`settling` held and reach (expansion), `biosphere.body_mass` / `need_factor` and `lifespan.expectancy_years` (the
reserve basket), `regimes` debasement and `fx` mid rates (money), `decide` (the steward's judgement). These are legacy
floats, marked here; their exact replacements are owed.

## ⚡ Quickstart

### 1. Launch Interactive Terminal Game
Run directly with Python 3 (zero external dependencies required):
```bash
python3 main.py
```
Or launch with a custom captain name and world seed:
```bash
python3 main.py --name "Commander Shepard" --seed 42
```

### 2. Launch the Mycelium Bridge Daemon (WebSocket + Telnet)
Run the concurrent background daemon:
```bash
python3 main.py --bridge
```
*Optional parameters:*
* `--ws-port <port>`: WebSocket Gateway port (default: `8765`)
* `--telnet-port <port>`: Telnet socket port (default: `2002`)

Connect remotely via Telnet:
```bash
telnet localhost 2002
```

Connect remote AI agents or web frontends via WebSocket:
```
ws://localhost:8765/ws
```

### 3. Run Headless Simulation Pass
Verify the simulation kernel without entering the interactive loop:
```bash
python3 main.py --demo
```

### 4. Run Test Suite
Execute the full test suite (26 passing tests across kernel, reactive AI, and network bridges):
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

---

## 🎮 Core Game Mechanics

### 1. High-Contrast Terminal / ASCII Interface
* **Persistent Status HUD**: Displays your Current Sector, Security Status, Turns Remaining, Credits, Ship Class, Cargo Hold meter (`[12/30] (Ore, Org, Eq)`), Energy Shields bar, Combat Fighter count, and Score.
* **Command Dispatch**: Fast letter or number prompt:
  ```
  [M]ove  [T]rade  [P]lanet  [A]ttack  [S]hipyard  [C]omputer  [R]adio  [H]elp  [Q]uit
  ```
* **Direct Navigation**: Type any valid adjacent sector number (e.g. `14`) directly at the prompt to warp instantly.

### 2. Universe Graph & Security Tiers
* **100 Deterministic Sectors**: Connected via bidirectional wormholes. A randomized spanning tree algorithm guarantees that every sector is reachable from Sector 1.
* **Security Classification**:
  * **Sectors 001–010 (Federation Core)**: Heavy Federation Navy patrols. Sector 1 hosts **Sol Central Stardock** (Shipyard, Hull Upgrades, Shield Recharging, Fighter bays). Weapons discharge is strictly forbidden.
  * **Sectors 011–060 (The Borderlands)**: Contested outer rim. Moderate trade activity and occasional pirate incursions.
  * **Sectors 061–100 (Deep Void Anarchy)**: Complete lawlessness. Rich mineral deposits, rogue citadels, and pirate raiders.

### 3. BBS-Style Economy (TradeWars 2002 Model)
* **Commodities**: `Ore` (raw industrial mining), `Organics` (food & biomass), and `Equipment` (high-tech arms & engines).
* **Port Classes**: Classic 8-class system (e.g. Class 1: BBS, Class 2: BSB, Class 4: SSB, Class 0: Stardock).
* **Dynamic Supply & Demand**:
  * Buying goods from a port depletes its stock, driving local prices **UP**.
  * Selling goods to a port creates a surplus, driving buy prices **DOWN**.
  * Ports replenish and consume goods every cycle, creating natural trade waves across the galaxy.

### 4. Planetary Colonization (BRE & SRE Model)
* **Claim Colonies**: Land on unowned planets across the universe to claim sovereignty.
* **Taxation**: Colonists pay turn-based taxes into the planetary vault for the governor to collect.
* **Garrison & Shields**: Construct planetary shields and recruit defense fighters to withstand orbital strikes.
* **Citadel Progression**:
  * **Tier 0**: Barren Outpost
  * **Tier 1**: Fortified Redoubt (+50% tax multiplier, 500 Max Shields, 150 Max Fighters)
  * **Tier 2**: Planetary Stronghold (+120% tax multiplier, 1,200 Max Shields, 400 Max Fighters)
  * **Tier 3**: Imperial Citadel (+250% tax multiplier, 3,000 Max Shields, 1,000 Max Fighters)

### 5. Context-Aware Autonomous AI Captains (EventBus Reactive)
The AI rivals don't just execute static heuristic turns—they actively listen to the `EventBus` and react to the player in real time:
* **Territorial Encroachment (`ai_voss`)**: If a player colonizes an unowned planet or upgrades a citadel within 3 warp hops of Cynthia Voss's territory, she broadcasts a formal corporate cease-and-desist warning over `COMM-1`.
* **Predatory Tracking (`ai_malakor`)**: If a player carries high-value cargo ($\ge 25$ Equipment, $\ge 35$ total cargo) or amasses $\ge 10,000$ Credits in the Borderlands/Anarchy, Malakor locks onto the player's sector coordinates, plots the shortest BFS warp intercept course, and transmits predatory threats.
* **Bounty Recognition & Payouts (`ai_ironclaw`)**: When a player destroys an outlaw pirate ship, Ironclaw Rake sends an open commendation over `BOUNTY` radio and the Federal Bounty Office wires **+5,000 Credits** and **+1,000 Score** directly into the player's account.
* **Arbitrage Master Recognition (`ai_vane`)**: Capt. Jack Vane monitors commercial flows, pathfinding between complementary ports and broadcasting market surges.

---

## 🔌 Decoupled Kernel Architecture & Integration

The core engine in [`xylarium/kernel/engine.py`](file:///opt/barren-realms/xylarium/kernel/engine.py) has **zero UI dependencies**. It exposes clean methods:

```python
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType

# 1. Initialize
kernel = GameKernel(seed=42)
player = kernel.register_player("user_123", "Captain Starbuck")

# 2. Dispatch Action
result = kernel.dispatch("user_123", ActionType.MOVE, destination=14)

# 3. Query State for UI / WebSockets
view = kernel.get_player_view("user_123")  # Returns pure JSON-serializable dict

# 4. Subscribe to Real-Time Subspace Radio & Events
kernel.event_bus.subscribe(lambda event: print(f"Event: {event}"))
```

### Ready for Mycelium Mesh & WebSocket Door Servers:
- **WebSocket Gateway**: Wrap `kernel.dispatch` and `kernel.get_player_view` in an `asyncio` WebSocket loop.
- **Mycelium Mesh**: Bind the `EventBus` to emit and receive P2P radio transmissions and inter-captain combat packets across local nodes.
