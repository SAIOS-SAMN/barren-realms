# Scales: from the universe down to a world

Largest first. Each tier exists in detail only where it is witnessed; everywhere else it is a formula.

| Tier | What it is | How it is carried | Its clock |
|---|---|---|---|
| **Universe** | a closed 3-sphere of galactic clusters: one seed, one Big Bang, one clock | `creation.py` (the Big Bang's draw, the expansion law), `sphere.py` (the nearest 64 clusters, analytic); lockstep (scheduler.py) | the clock (100 cycles a year); light between clusters on conformal time |
| **Galactic cluster** | the galaxies bound together | `cluster.py`: 40 galaxies, analytic - masses from the galaxy stellar mass function, closed-form orbits about the barycentre, their own minds drawn from the seed (never placed), a merger on the free-fall clock | deep time |
| **Galaxy** | an exponential disc, R_D = 3 kpc, to 5 R_D | `cosmos.py`: rings 0.5 kpc wide cut into ~equal cells (~2,800 cells) | deep time: the universe's pace - lonely 0.1, neighbourly 1 (default), teeming 10 Myr per clock year (`cosmos.PACES`, the one ruler between the tiers, a law chosen at genesis: `genesis="cosmic:teeming"`) |
| **Region** | one cell of the disc | 40 sectors, a pure function of the seed and the cell (`creation.cell`); charted when a ship enters it or a people with yards stands in it (the first witness's region is sectors 1-40, its home system sector 1) | - |
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

## Creation is fixed at the Big Bang (creation.py)

Each universe draws its initial conditions once, about the measured values (Planck 2018): the fluctuation amplitude
sigma8 (lumpier matter collapses sooner: formation epochs scale as (0.811 / sigma8)^1.5), the baryon fraction (stars
per volume, and the supernovae that sterilise), and the curvature - always closed, drawn about the measured flatness.
How lively a universe is follows from these; the pace is only its tempo. Seed 7: sigma8 0.776, f_b 0.148, a
3-sphere 757 Gpc round.

Every cell's 40 sample volumes are a pure function of the seed and the cell's coordinates - never redrawn, the same
whoever charts them in whatever order. A sector holds a star with the Poisson chance 1 - exp(-n), n rising with the
disc's density (0.28 of sectors at R0, the settled galaxy's measured share). Its birth date is drawn from its ring's
star-formation history (gas falling in on Chiappini's inside-out timescale and forming stars as it arrives): the
core is born at once, the rim is still making stars long after today - a charted sector whose star is not yet born
is gas, and lights on its date (STAR_BORN). Its mass is Salpeter's; a third are binaries; it is born with the metals
its ring had made by then (age-metallicity), and giant planets form only as the square of those metals (their
cores; Fischer & Valenti 2005).

## Minds arise on worlds that exist, each biology by its own needs

Every world of every system is a candidate, for every biology that can live on it - if it can feed a viable people
(Franklin's 500 foragers on its living area through its seasons, divided among bodies by what each burns). Each
biology has its own needs: metals (carbon life and lattice minds fully, ice-dwellers half - oxygen came early -
plasmic minds none: they are the Big Bang's hydrogen), its tolerance of sterilising supernovae (plasma none,
molecules fully), its star's window (a rogue's dark life waits on no star). Each passes Carter's four hard steps on
its own dice; the first to finish is the world's mind. There is no single habitable zone.

Seed 7 (measured under the earlier, whole-galaxy schedule): the first mind at 6.02 Gyr - plasmic, in a gas giant 2.7 kpc from the core under a red dwarf; the second
0.31 Gyr later (cryogenic). ~1,850 minds by the 30 Gyr horizon, ~82 by 13.8 Gyr: half plasmic, a third
ice-dwellers, carbon life rare. The schedule is computed once per seed and kept on disk under the digest of the laws
it follows (`runs/creation/`).

## The witnessed and the unobserved

Not every world of the galaxy is worked out. At genesis a share of the cells (one in `creation.WITNESSED` = 8, a
draw the seed's own dice make, every ring alike) is computed world by world: their minds are exact - where, when,
in which chemistry, with every rung of their climb. The whole galaxy's expectation (the curve of minds by each
epoch) is measured from that share and scaled to the whole. The rest is held as that expectation and nothing more:
as the clock runs, the unobserved share of the curve accumulates, and each time it passes the next of the seed's
exponential draws a mind wakes somewhere no one has looked (`creation.potential`, `cosmos._unseen`). Only then are
cells worked out - one by one in the seed's order for that draw, each kept with the chance its worlds have raised a
mind by now - and the mind wakes on the world, around a star still on its main sequence, likeliest to have raised
it; its world is judged as it is that day. What no one observes is never built.

A lit world's window closes as its star leaves the main sequence: the giant branch (`cosmos.AGEING_SHARE`, the last
tenth of its life) boils its seas, in creation as in play. The elders of deep history (`prehistory.homes`) are the
witnessed minds, each standing for as many more of its kind as the witnessed share is short of the whole.

The witnessed schedule costs an eighth of the whole galaxy's (~20 s per universe instead of ~175 s, once, kept on
disk); each unobserved mind costs the few cells looked through to find it (about one cell in four holds a world that
could raise one).

## Charted where they go

A mind that arises is given its own system and nothing more: its sky is description, not map. A cell is charted -
all 40 sectors and its own lanes, as the Big Bang made them - when a ship enters it, or when a people with shipyards
stands in it (it charts its own cell and those facing it now). The map stays tiny until peoples reach the stars, and
then grows only where they go. Lanes and the stars' weather (LANE_OPEN/CLOSE, STAR_BORN, STAR_AGEING, STAR_DEATH)
are told only where a people linked to the interstellar community lives.

## The Big Bang, the pace, and the lives of stars

Deep time is Gyr since the Big Bang: the home galaxy's first stars form 0.3 Gyr after it (the oldest stars
measured are ~13.5 Gyr old), its disc inside-out after that; 13.8 Gyr is today's reading, not an end.

The pace is a law of each universe, chosen once at genesis and kept for its whole run (kept ages are filed under
it). Seed 7's second mind arrives 13,639 clock years after the first when lonely, 1,364 when neighbourly, 136 when
teeming - order and relative spacing are the physics; the pace is how much evolution a year of history stands for.

Every witnessed star lives 10 Gyr x M^-2.5 from its own birth. Over its last tenth it climbs the giant
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

## The closed universe (sphere.py)

The universe is a 3-sphere of comoving radius c / H0 / sqrt(Omega - 1): finite, without edge, its antipode pi R
away. Its groups and clusters (haloes above 1e13 suns, 1e-4 per Mpc^3; Tinker et al. 2008) are drawn nearest first
by inverting the sphere's own volume, so no cluster's place depends on another's; distance is the arc between two
points of the sphere. The expansion is one law, fixed in time (flat Lambda-CDM, measured H0 and Omega_m): comoving
places stand still and distances grow as a(t); light crosses comoving space on conformal time, and beyond the event
horizon light sent now never arrives. Each cluster's first mind is drawn from the home galaxy's expectation scaled by
its stars; its SIGNAL is heard once its light has arrived and a home people has charted the sky beyond its cluster.
Seed 7: the nearest group 5.5 Mpc away, and every one of the nearest 64 woke minds before the home galaxy did - the
home peoples will hear older voices. The black holes at every galaxy's heart bounce what they swallow
(Einstein-Cartan); in that theory each is the seed of a universe of its own - the tier beyond this one.

## Guidance (guidance.py)

Once a year each people among the stars weighs, through its own mind, what it could do for younger peoples it has
met and the empty worlds its fleets reach: UPLIFT (teach the gap in each domain, as far as the two understand each
other; the cost its teachers' passage - a knowledge unit is a thousand minds' year), SEED (set a designed people
down on a world that can feed one), or nothing. Both are valued as the lives they lift, as far as the elder values
strangers (its alignment toward the Light), and move it toward the Light. A people of the Dark never chooses either.

## What a body burns (biosphere.metabolic_factor)

No two species eat alike. Need per head follows the metabolic theory of ecology (Brown et al. 2004): B ~ M^(3/4) x
the kinetic pace of its chemistry at its body's temperature - its homeworld's, from the light it evolved under (its
star's luminosity over its orbit squared, Stefan-Boltzmann); plasmic bodies run at plasma temperature. Body mass
comes from its homeworld's gravity (square-cube: the bodies a world bears scale as g^-3; a plasmic body has no frame)
and its life history (a generation ~ M^(1/4): r-strategists small, K large). The land divides the same yield among
them (Damuth's law): a carbon K-body on an Earth under the Sun eats 1; small r-bodies on a cold, heavy ice world eat
a thirtieth as much and are thirty times as many; plasmic K-bodies at 10^4 K eat six times as much. Meals carry their
fraction of a unit, as harvests do.
