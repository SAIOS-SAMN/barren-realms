# Constants: rulers, laws, worlds, peoples

Every number in the engine is one of four kinds. Only the first two may be written down; the last two must be
computed for each world and each people.

| Kind | What it is | Examples | May it be a constant? |
|---|---|---|---|
| **Ruler** | a unit of measure; changing it changes no outcome | the AU, an Earth mass and area, a standard year (100 cycles), a solar luminosity, the energy unit (EU), a person's ruler draw of energy (`energy.PERSON_EU`), the knowledge unit, money units | yes |
| **Universal law** | true everywhere | Stefan-Boltzmann, Kepler, Lanchester, Wright's learning curve (progress ratio), Landauer, conservation, an iron core's conduction share (`harvest.CONDUCTION_SHARE`) | yes |
| **World fact** | follows from one world's physics | its light, temperature, core heat flow, **dynamo margin** (`harvest.dynamo_margin`: conduction against convection, ~ m^-1/3 / heat), atmosphere, crust | no - computed per world |
| **People's outcome** | follows from a people's biology, world and choices | **energy need** (industry share x efficiency at its own energy knowledge + the thermal gap of its worlds), **what it burns** (fire only where a biosphere made an oxidiser), **its generation** (its strategy's fertility ceiling, at its substrate's pace), **its planning horizon** (its generation over its minds' noise), its aggression, its intelligence | no - derived, then measured |

## What was Earth's and is no more

* Energy per person was humanity's oil-era intensity, doubling per tier. It is now the industrial share of a
  people's economy x its own efficiency (falling with what it knows of energy) + life support for the worlds it
  lives on that its biology is not tuned to.
* "Combustion is the first fire" assumed carbon and oxygen. Fire now needs a photosynthetic biosphere under air.
* The 40% dynamo margin was Earth's core. Each world's margin follows from its own core: Earth-sized worlds come out
  near 40%, hot volcanic and larger ones higher, Mars-sized ones at zero (their dynamos were already dead).
* "A mind at Earth's temperature plans a decade" is replaced by each people's own generation over its noise.
* A generation was one galactic constant; it now follows each people's reproductive strategy and its substrate's
  kinetic pace (hot peoples live fast).

## Earth as a data point

`mirror.py` places the Terrans - the people of Terra - in the galaxy's own distribution on energy per person,
predation, fluid intelligence, alignment, planning horizon and the year of their first shipyards, as values and
percentiles (in `observations.jsonl` as `mirror`). Earth is measured; it is no longer the ruler of anything but units.

## The audit: every number that is still Earth's, and where it was measured

Earth is one sample, taken in the backwoods: ~8.2 kpc from its galaxy's centre in a quiet stretch of the disc, in a
sparse group of galaxies (not a rich cluster), around a ~solar-metallicity star 4.6 Gyr old, 13.8 Gyr after the Big
Bang, with no confirmed contact and no direct probe of a black hole's interior. Every Earth number below was measured
there, then, by the one people we know. Each is either kept as a **law** (true across what we can test), kept as a
**unit**, declared as an **assumption** (no evidence either way - stated once, in one place), or **retired**: to be
derived from the funnel (docs/FUNNEL.md), with Earth kept only as a test the engine should be able to reproduce
at Earth's own place and time.

| Number | Where | Provenance | Verdict | Retired by |
|---|---|---|---|---|
| Stefan-Boltzmann, Kepler, Landauer, Jeans escape, condensation temperatures (Lodders 2003), solar abundances | laws, chemistry | physics; meteorites | law | - |
| Kleiber M^(3/4), generation ~ M^(1/4), Damuth density, square-cube gravity | biosphere | all Earth life across ~20 decades of mass | law (declared: tested only on carbon life) | - |
| Trophic efficiency 10% (Lindeman) | ways | Earth ecosystems | law (declared) | - |
| Planck cosmology, Salpeter IMF, Milky Way disc gradients, Chiappini infall | creation, cosmos | our universe and galaxy | law / data drawn about per seed | - |
| Einstein-Cartan bounce at the centre | blackhole | none: a hypothesis that avoids infinite density | **assumption** (exterior effects only ever touch life) | - |
| T_EARTH = 278 K at flux 1 | laws | a unit of flux and its temperature | unit | - |
| AU, Earth mass/radius/area, standard year, EU, knowledge unit | everywhere | units | unit | - |
| LIGHT_OPTIMUM per metabolism, PLASMIC_MASS_OPTIMUM | config, biosphere | invented per metabolism | **retire** | 3 (chemistry from the world) |
| HABITABILITY table (metabolism x world type) | config | invented | **retire** | 2-3 |
| Seven world types as inputs (TERRESTRIAL, ICE ...) | physics.classify | categories | **retire** to labels | 2 |
| HARD_STEPS = 4, STEP_GYR = 10 | creation | Carter/Watson: Earth's single history | **retire** to a per-universe draw + kinetics | 4 |
| REPRODUCTIVE_STRATEGY clade list and names (bimaniform ...) | config | invented, human-flavoured | **retire** | 4 |
| BIRTH_RATE 3%/yr (generation ~28-33 yr) | config | human | **retire** | 5 |
| Life spans 0.6 / 1.7 / 2.5 / 4.3 generations | lifespan | human life history | **retire** | 5 |
| BODY_CYCLES 13 | lifespan | 70 kg human, 1.5 kg food a day | **retire** | 5 |
| PEOPLE_PER_EARTH_AREA 50,000; TECH_YIELD tiers; HABITAT_AREA | config | human agriculture | **retire** | 6 |
| Forage -> farm -> state; temple / levy gauges; "fields" | ways, society | human history | **retire** to chemistry-neutral ways | 6 |
| CRITICAL_COMMUNITY 250,000 (Bartlett) | lifespan | measles in humans | **retire** | 7 |
| CFR_VIRGIN 0.25 (Fiji 1875) | lifespan | one human epidemic | **retire** | 7 |
| KNOWLEDGE_DEPRECIATION 15% at HUMAN_LIFE_YEARS 70 | laws, knowledge | human R&D | keep as the rate of a human-like people (law, declared); its death share already the people's own | 8 checks it |
| Geology per Earth mass (ore, outgassing, tailings, He-3) | geology | scaled to an Earth, per mass | law-by-scaling (declared) | 2 refines outgassing |
| SYSTEMS_SHARE_R0 0.28 | creation | the settled galaxy's own share | unit of sampling | - |

### Progress on the audit (cosmic universes)

Retired: the habitability table and light optima (chemistry and energy from each world's physics); the seven world
types as inputs (labels now); the fixed four hard steps (drawn per universe); the clade list (traits per world);
Bartlett's 250,000 and Fiji's 25% (transmission dynamics: a trough of infected over the host's generation and the
infection's course; the virulence trade-off's 1/2); "fields" for everyone (ways in each chemistry's terms).

Kept as **units** of the simulation, stated as such: the life-history time of a unit body at unit pace (from
BIRTH_RATE), people per unit of captured energy per unit area (PEOPLE_PER_EARTH_AREA), the unit of interior heat
(0.087 W/m^2) and of light (340 W/m^2 over a sphere).

Kept as **declared cross-species invariants**: the life-history ratios (maturity, productive span, life, longest
life as multiples of a generation - Charnov's invariants), the works multipliers of a people's citadel tiers.

Declared **assumptions** of the funnel (worlds.py, creation.py): the disc's normalisation and lifetime, giant-impact
growth, comet composition, stripping rate and shielding, the weathering scale, the greenhouse fit, the photolysis
threshold, the activation-energy scaling, the bond thresholds, plasma's structure, the energy half-saturation,
extinction rate, the hard-step ranges, the trough and infection course.
