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
| What it builds with (station hulls) | matter solid at its body temperature (measured melting points; else the universal table's solid point, chemistry.TABLE) that its world holds and it has understood (chemistry.known), the cheapest it holds or can buy: iron for the water-born, water ice for the ammonia-born, nothing at all for the plasma-born. ORE is a world's silicate rock (its mantle's Mg, Si, O) - known to every people standing on it |
| What a ship's hull is made of | at refit the yard melts the old hull back into what it was built of (Ship.hull_matter) and frames the new one from the cheapest matter on its shelves that is solid at the crew's body temperature (its biology's region read warmest-first, uses.captain_body) and that the captain understands - an ice hull for a cold-blooded crew, iron or rock for a water-born one; a short frame where the shelves cannot hold it (propulsion.refit). The Imperium's warships are framed the same way at their fortress, from its own stores and port, at its people's warmth (factions._commission_imperial). The hull's size is still read from the frame's iron and titanium count |
| What its buildings are made of (pleasure domes, surface districts) | matter solid where the building stands - the warmer of its world's surface and its people's own warmth (uses.site_t) - the cheapest the world holds or its port sells that its people understands, drawn from its own stores first (uses.draw). Each district remembers what it is made of, and what is pulled down returns as itself (uses.salvage): an ammonia-born people's ice district gives back ice, not ore |
| What its citadel is made of and mended with | raised like any building (uses.site_t, build_with, draw) and remembered as it is raised (uses.citadel_of); a citadel standing before any record is read once from its site. Its upkeep wears what most of it is made of, held in the world's stores and imported when short (uses.wears): ice walls are mended with ice. Where nothing holds a shape at its site (a plasma-born people's), it is not walls of matter and takes none |
| What it first burns (fuel tradition) | the propellant it understands that its home system held most of (propulsion.tradition) - no longer a table by biology; drives are built only for propellants it understands |
| Whether it can reach orbit | its own propellant: split water its system holds and it understands for chemistry, any volatile it holds for the atom; and a surface to launch from - a people under an ice shell or deep in a giant needs the heat to breach its world (fission) first (technology._can_launch) |

## Still declared (to be replaced, in this order)

| Declared | Where | What it assumes |
|---|---|---|
| Food and waste by metabolism name | `STAPLES`, `METABOLIC_WASTE`, `CAPTAIN_RATIONS` | what a chemistry eats and leaves, by label rather than from its energy chemistry |
| Comforts by metabolism name | `LUXURY_TYPES`, `LUXURY_AFFINITY`, `LUXURY_WORLD_BIAS` | four fixed luxuries and who craves which |
| Building in rock and metal for everyone | `RESORT_SHELL_UNITS`, `SURFACE_DISTRICT_UNITS` (now only how much), `SURFACE_TROOP_RECRUIT_ORE`, `CITADEL_UPKEEP` and `CITADEL_CONFIG` amounts, `IMPERIUM_WARSHIP_COST` (now only how much), `SHIP_FRAMES`/`SHIP_MODULES` iron and titanium (now only a hull's size) | structure is ore and iron whatever the people's warmth and knowledge |
| Drive physics | `FUEL_CELLS` exhaust velocities and tier gates | what each propellant gives, by table rather than from its reaction energy |
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
