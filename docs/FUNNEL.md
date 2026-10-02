# The funnel: from the Big Bang to a people

One process, many layers. Each layer is a pure function of the universe's seed, its own place, and the layer above
it: fixed at creation, never redrawn, computed only when something witnesses it. A layer evolves on the galactic clock
until a mind arises; a people then lives on the universal clock and reckons on its local one (docs/CLOCK.md).

| Layer | Made from | Gives | Module |
|---|---|---|---|
| Big Bang | the seed | sigma8, baryon fraction, curvature; the number of hard steps to a mind | creation.big_bang |
| Galaxy | Big Bang | inside-out star formation, element gradients by mass, rotation, environment (density, supernovae, the centre's active episodes) | cosmos, creation |
| Star | its cell, its birth date | mass, light, metals, life, death | creation.cell |
| Planet | its star, its orbit | mass, radius, bulk composition (rock, metal, ices by the snow line), interior heat | creation.cell, worlds |
| Atmosphere and ocean | the planet, its star, its environment, deep time | volatiles gathered + outgassed - escaped; pressure; greenhouse; surface temperature; field | worlds |
| Chemistry | atmosphere and ocean | solvent, bond window, richness, energy sources, kinetics; a region of chemistry space | worlds |
| Life | chemistry, deep time, luck | when life starts, the hard steps, impacts and extinctions, lineages and traits, the shape of a mind | (step 4) |
| Body | traits, world | mass, metabolic power, maturity, lifespan, fecundity | (step 5) |
| People | a mind, its world | capacity from captured energy, ways, culture, disease, history | biosphere, lifespan, culture ... |

## Rules every layer keeps

* **No Earth baseline.** A number is a physical law, a unit, or a declared assumption (docs/CONSTANTS.md). Earth is
  a test the engine should be able to reproduce at Earth's own place and time - a quiet stretch of a disc, 8 kpc out,
  in a sparse group, 13.8 Gyr after the Big Bang - not the ruler of anything.
* **Luck and timing.** Every layer draws its own dice from the seed; nothing is placed. Whether a world gets life,
  complex life, a mind - and when - is the outcome.
* **Singularities are never entered.** The galactic centre bounces at finite density (Einstein-Cartan, a declared
  hypothesis); only what a black hole does outside it - light in its active episodes, jets, tidal disruption,
  recycled matter - ever touches a world.
* **A mind need not become spacefaring.** A people that never leaves its world lives its whole history - its ways,
  beliefs, art, dead and eminent - in the ledger (history.py), to be read and replayed (tools/history.py).
EOF
echo ok