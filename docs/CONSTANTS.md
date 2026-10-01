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
