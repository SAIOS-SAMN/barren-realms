# The funnel: from the Big Bang to a people

One process, many layers. Each layer is a pure function of the universe's seed, its own place, and the layer above
it: fixed at creation, never redrawn, computed only when something witnesses it. A layer evolves on the galactic clock
until a mind arises; a people then lives on the universal clock and reckons on its local one (docs/CLOCK.md).

| Layer | Made from | Gives | Module |
|---|---|---|---|
| Laws | the progenitors | alpha, beta, alpha_G, fusion yield: every scale below (fundamental.py) | fundamental |
| Big Bang | the seed | sigma8, baryon fraction, curvature | creation.big_bang |
| Galaxy | Big Bang | inside-out star formation, element gradients by mass, rotation, each star's oscillation through the plane, curved space and slowed clocks (geometry.py) | cosmos, creation, geometry |
| Star | its cell, its birth date | mass, light, metals, life, death | creation.cell |
| Planet | its star, its orbit | mass, radius, bulk composition (rock, metal, ices by the snow line); six orbital elements, spin, moons; interior heat from isotopes, cooling and tides | creation.cell, worlds, orbits, interior |
| Atmosphere and ocean | the planet, its star, its environment, deep time | volatiles gathered + outgassed - escaped; pressure; greenhouse; surface temperature; field | worlds |
| Chemistry | atmosphere and ocean | solvent, bond window, richness, energy sources, kinetics; a region of chemistry space | worlds |
| Life | chemistry, deep time, luck | fidelity, the rungs to a mind, the time to write each, impacts that erase, rock that carries microbes within a system | life, creation.lineage |
| Body | traits, world | mass, metabolic power, maturity, lifespan, fecundity | (step 5) |
| People | a mind, its world | capacity from captured energy, ways, culture, disease, history | biosphere, lifespan, culture ... |

## Rules every layer keeps

* **No Earth baseline.** A number is a physical law, a unit, or a declared assumption (docs/CONSTANTS.md). Earth is
  a test the engine should be able to reproduce at Earth's own place and time - a quiet stretch of a disc, 8 kpc out,
  in a sparse group, 13.8 Gyr after the Big Bang - not the ruler of anything.
* **Luck and timing.** Every layer draws its own initial conditions from the seed; nothing is placed. Whether a world gets life,
  complex life, a mind - and when - is the outcome.
* **Singularities are never entered.** The galactic centre bounces at finite density (Einstein-Cartan, a declared
  hypothesis); only what a black hole does outside it - light in its active episodes, jets, tidal disruption,
  recycled matter - ever touches a world.
* **A mind need not become spacefaring.** A people that never leaves its world lives its whole history - its ways,
  beliefs, art, dead and eminent - in the ledger (history.py), to be read and replayed (tools/history.py).

## What is built (cosmic universes)

* **Big Bang** (creation.big_bang): sigma8, baryon fraction, curvature, the number of hard steps (3-6) and their
  timescale - drawn per seed about a chosen kind of universe: `measured` (about our own) or `lush` (lumpier, richer in
  baryons: stars sooner and more of them, metals made faster). Genesis `cosmic:<pace>:<kind>`, e.g.
  `cosmic:teeming:lush`.
* **Stars** (creation.cell): Kroupa's mass function, its break heavier in metal-poor gas; light from mass; lifetime
  fuel over burn; deaths by mass (white dwarf, Type Ia, core collapse to a neutron star or black hole).
* **Planets** (worlds.form): what each orbit gathered of the disc's elements; layers by density; giants where a core
  passed the critical mass before the disc dispersed.
* **Atmospheres and seas** (worlds.build): outgassing, escape, stripping, photolysis, the weathering thermostat,
  vapour feedback, the runaway limit; the Solar System is the test (tests/test_worlds.py).
* **Chemistry** (worlds.media): solvents, bond hierarchy, energy per area, Eyring pace; metabolisms are region names.
* **Life** (creation.lineage): the origin of life by chemistry and time; complexity by chemistry, time and energy;
  extinctions by the neighbourhood's comet flux; deep history to the chronicle; traits and mind shapes per world.
* **Bodies** (biosphere, laws): a minded body holds its chemistry's best temperature; its metabolism, generation and
  thought run at that pace; its size from its world's gravity and its life history.
* **Peoples**: capacity from the energy reaching their chemistry; crowd disease from transmission dynamics;
  ways and art in their own chemistry's terms.

## Since: the laws, the interiors, the geometry, life as information

* **Laws** (fundamental.py): four dimensionless constants set every scale; change one in the genesis key and the
  same initial conditions rebuild the universe under it.
* **Interiors and orbits** (interior.py, orbits.py): radiogenic heat from the isotopes the star was born with,
  mantle and core convection (the core's dynamo while it outruns its adiabat), tides from host stars and giants;
  eccentricities stirred, forced by neighbours and damped; inclinations; spins braked to lock; giants' moons in
  resonant chains. A world around a dim star or a giant can be warmed from below.
* **Geometry** (geometry.py): the universe's 3-sphere, the galaxy's weak-field metric (proper lengths, light delay,
  clock rates), stars' vertical orbits through the plane; the IMF's break warmer near the crowded centre.
* **Light by its colours** (worlds.band): only photons between an electron's lift and a bond's break drive chemistry.
* **Life** (life.py): fidelity from the solvent's cohesion, rungs from the error threshold, time from copying
  kinetics. Earth-as-test (`tools/progenitor.py --earth`, our laws, Earth's place and time): 283 K under 1.2 bar,
  0.052 W/m^2 of heat, three rungs, a mind in ~7.6 Gyr on average (a 71% chance within its star's life) - against
  288 K, 1 bar, 0.087 W/m^2 and one history of ~4 Gyr.

## Scenarios by conditioning (tools/scenarios.py)

No premise is written in as a constant. The declared numbers are given ranges; hundreds of universes are drawn;
each is tested on our own system at its own place and time (Earth's climb by many draws of its chances, Mars's
history); universes are weighted by how well their own formulas produce a premise ("a mind in the Mesozoic",
"Mars green at some time"); and the galaxies of the weighted universes are built and measured. Worlds can be
stripped of air or broken apart (ruin.py) only by peoples and captains who choose it, at the energy each world's own
binding asks.

## From the Big Bang to federations

| Link | Made from | Module |
|---|---|---|
| Belts and comet clouds | the disc's solids no world gathered: inside a giant's orbit, beyond the last world; what the giants fling out | creation._belts |
| Growing seasons | daily sunlight at every latitude through the year, swung by the axial tilt | physics.growing_share |
| Holding a sky | a shield against the star's wind, volatiles steered from belts, gas broken from rock - each priced, each chosen | skies.py |
| Mastery | a people's power (bodies and works) over its world's sunlight and its star's light: Kardashev's types, measured | mastery.py |
| The crossing | sublight within a system; the next star only once a people's mathematics holds the fourth axis and it can raise a passage's energy (a universe may forbid it: `ftl=0`) | mastery.py |
| Hearing | the light a people's works leak, against a listener's instruments and the light-time between | signals.py |
| Federations | blocs of crossed peoples founding common law when it beats its dues; charters and doctrines chosen by members | federation.py |
| Elders | every mind of the galaxy given a life at the level of history - crossing, falling, expanding, settling, doctrine - across declared ranges | prehistory.py, tools/elders.py |
| Earth by our rules | a people woken on a Sun-like system at our place and time, lived year by year; or begun in its Mesozoic, a rung short of a mind (`--mesozoic`) | tools/earth_run.py |
| Annals | every people's deep ages lived at the level of history: bridges in its own generations, falls shared over its dominion, pacts and galactic wars where dominions meet | annals.py |
| Lore | the galaxy's chronicle read from its ledger | tools/lore.py |
| The bridges' clock | life's rungs and peoples' ways timed from the engine beside Earth's record | tools/bridges.py |

## What limits life (creation.limits)

`creation.limits(seed)` sorts a sample of a universe's worlds by the first gate each fails. Seed 7, measured: of
9,023 worlds sampled, 42% have no solvent at all (dry), 49% have one but too little energy reaches it to go beyond
microbes (ice-covered and cold seas, fed by their world's heat alone), a few percent are too slow, sterilised or
outlived by their star. A `lush` Big Bang makes more stars and worlds, but the binding limit is energy reaching
cold seas, not matter: life begins on ~44% of worlds (the cold first rung) and complexity needs the energy of a lit
surface. What would feed the first rung further: tidal heating of moons around giants (not yet modelled), and hotter
interiors as the galaxy's metals rise.
