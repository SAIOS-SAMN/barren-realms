# Scales: from the universe down to a world

Largest first. Each tier exists in detail only where it is witnessed; everywhere else it is a formula.

| Tier | What it is | How it is carried | Its clock |
|---|---|---|---|
| **Universe** | the whole run: one seed, one clock | `GameKernel(seed)`; lockstep (scheduler.py) | the clock (100 cycles a year) |
| **Galactic cluster** | the galaxies bound together | the home cluster: a count (`cosmos.GALAXIES_IN_CLUSTER`); only the home galaxy is simulated | - |
| **Galaxy** | an exponential disc, R_D = 3 kpc, to 5 R_D | `cosmos.py`: rings 0.5 kpc wide cut into ~equal cells (~2,800 cells) | deep time: 1 Myr per clock year (`DEEP_YEARS_PER_YEAR`, the one ruler between the tiers) |
| **Region** | one cell of the disc | 40 sectors (sectors 1-100 are the first witness's own cell); materialised when witnessed | - |
| **System** | one sector: a star and its worlds | `physics.py`: exact Keplerian orbits | historical time |

The clocks are tiered: a system's worlds turn on historical time; the galaxy - its rotation (closed form on a flat
rotation curve, 220 km/s: a galactic year at 8 kpc is ~224 Myr, ~224 clock years), its stars' lives, the
evolution of life - turns on deep time. Every tier is clockwork: any moment of any body is computed, never stepped.

## The galaxy, as physics makes it

* **Inside-out:** a radius forms its stars after tau(r) = 1.033 r - 1.267 Gyr (Chiappini, Matteucci & Romano 2001).
* **Elements sorted by gravity:** an element spreads from where stars made it over a length inversely proportional to
  its mass, lambda(A) = lambda_Fe x 56 / A, lambda_Fe from iron's measured gradient (-0.06 dex/kpc, ~7.2 kpc).
  Heavy elements stay near the core (uranium ~1.7 kpc), the light reach furthest (hydrogen ~400 kpc: everywhere).
  A world's deposits are scaled from their values at R0 = 8 kpc (the ruler they were set at).
* **The galactic habitable zone:** metals for rocky worlds fall outward with the gradient; supernova sterilisation
  rises inward with stellar density.

## Minds arise; nothing is placed

Carter's hard steps (4, Watson 2008): each candidate world passes the origin of life, complex cells, multicellular
life and intelligence, each an exponential wait of mean 10 Gyr / (habitability x metals), after its crust settles
(0.6 Gyr), inside its star's main-sequence window (10 Gyr x M^-2.5, a Salpeter star), unless a supernova sterilises
it first. Candidate worlds per region are measured from the materialised map at R0 and scale with stellar density.
Each candidate's dice are fixed by the seed; the expectation is computed alongside (the audit).

The clock's year 0 is the epoch the first mind arises; each later mind arises in its own year, is named, chooses
nothing of its body (a variable world - a tilted axis, a red dwarf - breeds r-strategists; a steady one K), is
given its world's fittest metabolism, witnesses its own region, and begins as foragers.

Seed 7: the first mind at 3.27 Gyr (the Zishamar, 1.8 kpc out, under a 0.4 solar-mass star); the second 1,364
clock years later (the Quaqua). Expected minds in the galaxy: 6 by 5 Gyr, 16 by 6, 68 by 8, ~845 by the present
universe's 13.8 Gyr - tens of peoples over the thousands of clock years a game runs, not thousands of worlds.

## Elastic space

A region is materialised when a mind arises in it, when a ship first enters a neighbouring region, or when a people
with shipyards stands in a neighbouring region (its fleets see the cells around it). Regions join by warp lanes
when they touch. The audit (`cosmos.audit`, in observations) measures the scales every reading: cells charted of
the galaxy's, sectors per people, the share of charted space no people can reach, and minds arisen against minds
expected by now.

## The shear

On a flat rotation curve the inner rings turn faster: at 8 kpc two neighbouring rings slip a cell's width past
each other in ~35-45 clock years. Lanes within a ring stand (its cells turn together); lanes across rings are
re-forged every season from the cells' angles at that deep-time moment - they open as cells come to face each
other and close as they slide apart (ledger events LANE_OPEN / LANE_CLOSE), and while open a lane costs more as
its ends slide apart (1 / the share still facing; fibres.lane_cost). Contact windows across rings open and close
like conjunctions; an empire across two rings is pulled apart; a ship entering a region sees the cells facing it
now.

## History

Everything that happens is written once to the ledger (history.py): when (clock year, deep-time epoch, age), where
(world, system, galactic position at that moment), who, what, why, how much, and what earlier events it answers.
Myths compound: each retells the one before it, and a generation after a war, a strife, a conquest or a first
meeting, the gravest becomes a legend that remembers it. `tools/history.py` reads it back - annals, a book by
age and people, a people's mythology, or scenes in space and time for a replay.
