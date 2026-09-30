# Xylarium engineering standards

These are the rules every change to the kernel follows. They exist because the kernel is built one subsystem at a
time, and without a common shape each new subsystem re-invents storage, wiring, searches and caches. The
architecture tests (`tests/test_architecture.py`) enforce the mechanical ones; review enforces the rest.

## 1. Principles of the universe (what the code must model)

1. **Physics first.** Constants come from physics and biology (orbits, flux, growth rates, escape energy,
   exhaust velocity, MV = PY) and the systems contract and expand under them. Do not tune a number per run to
   make an outcome appear; find the mechanism that produces it. A hand-picked constant is allowed only when it is
   a genuine design choice (a price, a module's size), and it lives in `xylarium/config.py` with a comment saying
   what it means.
2. **A closed economy.** Money only moves between counted stocks. Anything that creates or destroys money is a
   declared `ledger.mint` / `ledger.burn` with a named source. Every stock that holds money is counted in
   `ledger.money_supply`.
3. **Conserved matter.** Every unit of every commodity is somewhere in the census (`matter.census`), and it changes
   only through a declared source or sink (`matter.source` / `matter.sink`, or `matter.produce` / `matter.consume`).
   Moving goods between holders is a transfer and declares nothing.
4. **Determinism.** The same seed gives the same universe in any process. Randomness is seeded from stable values
   (`zlib.crc32` of ids and cycles, or `random.Random(seed)`); never `hash()`, never unseeded `random`, never
   iteration over an unordered set where order affects results.
5. **Laws and observations.** The playtest harness separates *laws* (invariants that must hold: conservation,
   solvency, determinism, the quantity equation, orbits, stress fertility) from *observations* (emergent outcomes
   reported against a band of interest). A law failing blocks a commit; an observation outside its band is a
   finding to discuss.

## 2. Architecture standards

### S1. Every subsystem declares itself (`xylarium/kernel/subsystem.py`)

A subsystem is a module that owns state and does work on the world's clock. It registers once:

```python
from xylarium.kernel.subsystem import Subsystem, register

register(Subsystem(
    name="realms",                 # its key in kernel.state
    order=SEASON_ORDER["realms"],  # where it runs in the seasonal sequence
    state=lambda: {...},           # a fresh, JSON-shaped state record
    season=quarter,                # optional: kernel -> list of log lines, once per fiscal quarter
    genesis=genesis,               # optional: kernel -> None, once when the universe is made
    summary=summary,               # optional: kernel -> dict for the playtest report
))
```

The engine runs every registered `season` hook in `order`; the store saves and loads every subsystem's state;
the harness reads every `summary`. A new subsystem is wired by registering it, not by editing the engine, the
store and the harness.

### S2. Subsystem state lives in `kernel.state` (`xylarium/kernel/state.py`)

A subsystem's state is `state.of(kernel, "name")`: one JSON-shaped record per subsystem, created from the
subsystem's factory on first use, saved and loaded whole. Do not attach attributes to the kernel lazily
(`getattr(kernel, "x", None)` followed by `kernel.x = ...`). World objects (planets, ports, ships, captains) keep
their own fields in their dataclasses; per-object records that belong to one subsystem go in that object's
`society`, `leisure` or equivalent dict and are documented where they are written.

### S3. One topology service (`xylarium/kernel/topology.py`)

All questions about the warp graph go through `topology`: `hops(kernel, origin, radius)` (jump distances within a
radius, in breadth-first order), `reach(kernel, origin, radius)` (the same, as a list nearest first),
`tree(kernel, origin, limit)` (distances and parents), `path(kernel, a, b)`. Do not write a breadth-first search in
a subsystem. Anything that changes the warp graph calls `topology.changed(kernel)`.

### S4. One cache layer (`xylarium/kernel/cache.py`)

Derived values that are expensive and reused are memoized with `cache.memo(kernel, bucket, key, compute,
epoch=...)`. The epoch says when the value goes stale: `cache.season(kernel)`, `cache.cycle(kernel)`,
`cache.graph(kernel)` (the topology version), or an explicit value computed from the inputs. Invalidation is the
epoch changing - never a scattered `kernel._x_cache = None`. Cached values are never saved.

### S5. Configuration is immutable (`xylarium/kernel/hulls.py`)

`xylarium/config.py` is read-only data. Things created at run time (ship designs, realms, contracts) live on the
kernel. Hull specifications are read through `hulls.spec(ship)` (a ship built from a design carries its design)
and `hulls.catalog(kernel)` (stock hulls plus the kernel's designs), never by writing into `SHIP_CATALOG`.

### S6. Player actions register their handlers (`xylarium/kernel/actions.py`)

Each `ActionType` maps to one handler through a registry, with its turn cost declared beside it. The engine's
`dispatch` looks the handler up; it does not grow a branch per command.

### S7. The architecture is tested (`tests/test_architecture.py`)

The suite fails on:
- a breadth-first search over `warps` outside `topology.py`;
- lazy kernel state (`getattr(kernel, "...", None)` followed by assignment) outside `state.py`;
- a write into `SHIP_CATALOG` or any other config table;
- a seasonal hook called from the engine that is not registered;
- `engine.py` growing beyond its line budget.

## 3. Definition of done

A change is done when:
1. the unit suite passes (`python3 -m unittest discover -s tests`);
2. both seeds hold every law at 10,000 cycles (`simulate_playtest.py --cycles 10000 --seed 7` and `--seed 1337`);
3. new behaviour has tests - including conservation of money and matter for anything that moves either;
4. it follows S1-S7 (the architecture tests pass), and it reuses the shared services instead of adding local ones;
5. the playtest report shows the new system (via its `summary`), so its effect on the universe is visible;
6. it is committed to `master` with a message that says what changed in the universe, not only in the code.
   `xylarium_save.json` is never committed.

A refactor (no intended change to the game) additionally proves it changed nothing: a fixed-seed run produces the
same fingerprint before and after (captains, worlds, ports, money, matter, claims, chronicle). This is a tool for
restructuring only; ordinary prototype work is judged by the laws.

## 4. Style

- Match the surrounding code: docstrings that say what a mechanism means in the universe, comments only where a
  line's reason is not obvious, names from the game's vocabulary.
- Integer money, integer matter. Fractions (`fractions.Fraction`) for exact physics; floats only for rates,
  prices and reporting.
- A module's docstring states its mechanism and its laws first; its constants follow, each with a comment.
