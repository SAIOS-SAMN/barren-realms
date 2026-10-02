# Scales: from the universe down to a world

Largest first. Each tier exists in detail only where it is witnessed; everywhere else it is a formula.

| Tier | What it is | How it is carried | Its clock |
|---|---|---|---|
| **Universe** | the whole run: one seed, one clock | `GameKernel(seed)`; lockstep (scheduler.py) | the clock (100 cycles a year) |
| **Galactic cluster** | the galaxies bound together | `cluster.py`: 40 galaxies, analytic - masses from the galaxy stellar mass function, closed-form orbits about the barycentre, their own minds drawn from the seed (never placed), a merger on the free-fall clock | deep time |
| **Galaxy** | an exponential disc, R_D = 3 kpc, to 5 R_D | `cosmos.py`: rings 0.5 kpc wide cut into ~equal cells (~2,800 cells) | deep time: the universe's pace - lonely 0.1, neighbourly 1 (default), teeming 10 Myr per clock year (`cosmos.PACES`, the one ruler between the tiers, a law chosen at genesis: `genesis="cosmic:teeming"`) |
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

## The Big Bang, the pace, and the lives of stars

Deep time is Gyr since the Big Bang: the home galaxy's first stars form 0.3 Gyr after it (the oldest stars
measured are ~13.5 Gyr old), its disc inside-out after that; 13.8 Gyr is today's reading, not an end.

The pace is a law of each universe, chosen once at genesis and kept for its whole run (kept ages are filed under
it). Seed 7's second mind arrives 13,639 clock years after the first when lonely, 1,364 when neighbourly, 136 when
teeming - order and relative spacing are the physics; the pace is how much evolution a year of history stands for.

Every witnessed star lives 10 Gyr x M^-2.5 from when its ring formed. Over its last tenth it climbs the giant
branch: its light rises toward the measured tip (~2,500 suns) as the square of its progress - its worlds' biology
burns (light fit collapses: physics.planet_flux), while arrays and fields take a windfall of energy. Then it dies:
a single star sheds its envelope and leaves a white dwarf (a thousandth of the Sun's light: its worlds frozen, those
inside ~1 AU engulfed); a binary's white dwarf detonates as a Type Ia supernova (every world flung out as a rogue).
Its shed matter seeds its region (carbon and water from a white dwarf's envelope, iron, nickel and uranium from a
supernova) - or, inside the bulge (2 kpc), falls to the galactic centre. No star the generator makes exceeds 8 suns,
so there are no core-collapse supernovae yet.

## Dying suns and the duty of governments (exodus.py)

A people reads its star's end once the share of its life still ahead falls to its mastery of energy (FORECAST).
From the moment the years left no longer exceed the move plus its council's horizon, a government with ships must
choose to carry its people away - a settler fleet per yards world per season, to its own worlds with room or to
empty ones under lasting stars - weighing the lives against the fleets. Peoples without ships may be rescued by
peoples that have met them, as far as those value strangers' lives (their alignment toward the Light; rescue moves
them further toward it). When the star dies, those left die with it (PERISHED), and whatever their government could
have carried and did not is harm against it - toward the Dark - and its surviving worlds lose faith in it
(ABANDONED). Peoples with ships may also strip the doomed worlds first (SALVAGE). A steward can order the exodus.

## The galactic centre: an Einstein-Cartan recycler (blackhole.py)

Spin-torsion coupling halts collapse at the Cartan density and bounces it: the central black hole takes matter in
and gives it back. What dies within the bulge - a star's shed matter, the worlds its death unbinds - falls to the
centre, which shines as it feeds (L = 0.1 Mdot c^2: millions of suns for a star's meal; a quiet floor at Sgr A*'s
1e-8 suns a year otherwise; CENTRE_FLARE), and returns its reservoir to the bulge's witnessed worlds as jets over an
active episode's e-folding time (100 Myr). Capture and return are declared to the matter ledger.

## The shear

On a flat rotation curve the inner rings turn faster: at 8 kpc two neighbouring rings slip a cell's width past
each other in ~35-45 clock years. Lanes within a ring stand (its cells turn together); lanes across rings are
re-forged every season from the cells' angles at that deep-time moment - they open as cells come to face each
other and close as they slide apart (ledger events LANE_OPEN / LANE_CLOSE), and while open a lane costs more as
its ends slide apart (1 / the share still facing; fibres.lane_cost). Contact windows across rings open and close
like conjunctions; an empire across two rings is pulled apart; a ship entering a region sees the cells facing it
now.

## The cluster

The home galaxy's cluster is a formula: 40 galaxies with stellar masses from the measured Schechter function
(alpha -1.2, M* 5e10 suns, dwarfs down to 1e8), placed through a Local-Group-sized 1.5 Mpc, each on a circular orbit
at the speed the cluster's mass (stars x a halo of 30) gives it. Each raises minds by the home galaxy's own law,
scaled by its stellar mass and its metals (Z ~ M^0.3): seed 7's cluster raises ~19,000 by the 30 Gyr horizon. The
most massive companion falls toward the home galaxy from rest on its free-fall time (seed 7: 14.5 Gyr - beyond a
game; a closer, heavier companion would meet within one).

When a home people first reaches space it charts the cluster (CLUSTER_CHARTED); a mind elsewhere is heard once its
light has crossed the distance (SIGNAL, the first from each galaxy). The tier-boundary rule, written down: light
between galaxies travels on deep time, at the universe's pace - Andromeda's 2.5 million years of light take ~2.5
clock years at the neighbourly pace. Within a system, light and ships travel on historical time; lanes take their
geometry from deep-time positions and their traffic from historical time. Any later tier (another galaxy
materialised when a people can cross to it) obeys the same contract: each tier's physics on its own clock, and the
boundary translated by the pace.

## What a people is remembered for (culture.py)

A people is linked to the interstellar community once it lives on more than one world, harvests its sun directly,
or trades its money on the exchange. Until then its ledger keeps no banking or currency entries (counted in
`history.muted`, not told), and the galaxy's histories wait for someone to be in it. What is told is its culture,
weighed once a generation or when something new comes: its COSMOLOGY (its sky as physics makes it - crowded or
sparse, the galaxy's heart in it or not, its moons, its sun's colour - read through its knowledge against its creed
and whether it has met anyone or heard a signal), the HURDLES it faces and passes, what it IMAGINES (from its body,
biology, sky and fears) and its ART (medium from its senses, palette from its sun, symmetries from the mathematics
its crystals express, mood from its creed and fortune). Seed 7's Zishamar, 765 years: 25 ledger events - a sky that
was a roof, then "the eyes of the dead, and the great glowing heart among them is where all souls go"; stone art
of turning patterns that grew sacred as their creed rose; the sickness of crowds, the turning from the wild and the
founding of order, each faced and passed.

## History

Everything that happens is written once to the ledger (history.py): when (clock year, deep-time epoch, age), where
(world, system, galactic position at that moment), who, what, why, how much, and what earlier events it answers.
Myths compound: each retells the one before it, and a generation after a war, a strife, a conquest or a first
meeting, the gravest becomes a legend that remembers it. `tools/history.py` reads it back - annals, a book by
age and people, a people's mythology, or scenes in space and time for a replay.
