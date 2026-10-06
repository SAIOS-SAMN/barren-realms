# What goods are for: derived, and still declared

The rule (docs/STANDARDS.md, the user's causal chain): physics defines the planets; the stars define the life and
civilisation that emerge on them; the elements define what they can use, build and trade; their place in the galaxy
gives them their neighbours and alignment. We build the formulas; the peoples write the story. A good is matter. What
it is FOR comes from the people who meet it, never from a table.

## Derived (uses.py)

| What | From |
|---|---|
| A people's body: its solvent and the temperature it keeps | the solvent its mind arose in (cosmos.select), else a world of its own whose media fit its chemistry, else the single solvent its chemistry's region allows (worlds.region inverted; liquid at one bar where its world is unknown) |
| Its medium (what households keep and domes hold) | the good its solvent's matter is laid down as (creation._composition): water to the water-born, ammonia ices to the ammonia-born, rock to the melt-born, hydrogen to the plasma-born; none yet for methane |
| What it builds with (station hulls) | matter solid at its body temperature (measured melting points; the exotics' workable state), the cheapest it holds or can buy: iron for the water-born, water ice for the ammonia-born, nothing at all for the plasma-born |

## Still declared (to be replaced, in this order)

| Declared | Where | What it assumes |
|---|---|---|
| Food and waste by metabolism name | `STAPLES`, `METABOLIC_WASTE`, `CAPTAIN_RATIONS` | what a chemistry eats and leaves, by label rather than from its energy chemistry |
| Comforts by metabolism name | `LUXURY_TYPES`, `LUXURY_AFFINITY`, `LUXURY_WORLD_BIAS` | four fixed luxuries and who craves which |
| Building in rock and metal for everyone | `RESORT_ORE`, `SURFACE_DISTRICT_COST_ORE`, `SURFACE_TROOP_RECRUIT_ORE`, `CITADEL_UPKEEP`, `IMPERIUM_WARSHIP_COST` | structure is ore and iron whatever the people's warmth |
| Quantities | `STATION_HULL_UNITS`, `RESORT_H2O_PER_QUARTER`, `HOUSEHOLD_BASKET` amounts and its `EQUIPMENT` | how much a hull, a dome or a household takes |
| Human industry | `COMMODITY_CONFIG` base prices, categories and manufactured recipes (equipment, superconductors, engine manifolds, warp cores) | what can be made, from what, and what it is worth |
| Invented matter | the exotic minerals (pyrosite, aetherium, ...) | names with only a workable-state class for physics |
| Combustion | `waste.FUELS` | burning carbon needs an oxidiser the world may not have |
| Money | four named currencies and zones, `FX_POOL_SEED`, `PRICE_LEVEL`, SOL as the yardstick | that money exists, who issues it, and what it is measured in |
| Market mechanics | `CLEARING_BAND`, `CROSS_REANCHOR_RATE`, exchange depth (a year's flow), traders committing half a purse, escort hazard shares | the pace and tolerance of markets, not each mind's own horizon and noise |
| Minds' bodies | `cosmos.select`'s choice of hands from a fixed list | the shapes a body may take |
| Settled peoples | the settled board's placed civilisations (the human Terran Federation and the rest) | peoples placed rather than arisen, some on worlds their chemistry could not have arisen on |

Value should end in physical units (energy) or each people's own, with no money privileged. Money, exchanges,
escorts and stations should be inventions of minds meeting a recurring need, not institutions laid down.
