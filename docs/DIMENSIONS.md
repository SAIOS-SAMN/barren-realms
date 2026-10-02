# Dimensions: what the engine keeps whole, and what it still projects

Every simulation computes a projection of something with more dimensions than it carries. That is legitimate - it
is what physics calls an effective theory - as long as each projection is declared: what the full quantity is,
what the engine uses, and what the difference could change. This ledger is that declaration. A projection that
changes an outcome is a candidate for restoring; one that changes nothing measurable is kept and stated.

## Below everything: the laws as geometry

A universe's laws are four dimensionless numbers (fundamental.py): the strengths of electromagnetism (alpha) and
of gravity (alpha_G), the electron's mass over the proton's (beta), and the share of mass hydrogen gives up fusing
(nuclear). In gauge theory a force's strength is the curvature of a structure attached to every point of space -
electromagnetism is the geometry of a small circle at each point (the fibre-bundle form of Kaluza and Klein's fifth
dimension) - so these numbers can be read as the shape of dimensions too small to see. The engine takes no side
on which shape; it takes the numbers as that shape's measurement and computes everything else from them:

| Scale | Follows from | Ours = 1; elsewhere |
|---|---|---|
| bond energies, boiling and triple points, heats of vaporisation, melting, a body's best temperature | the Rydberg, alpha^2 m_e c^2 / 2 | a^2 b g^1/2 |
| phase-diagram pressures | Rydberg / Bohr radius^3 | a^5 b^4 g^2 |
| rock density (so planet radii) | m_p / Bohr radius^3 | a^3 b^3 g^2 |
| star masses, the IMF's limits, core collapse, remnants | the Chandrasekhar mass, alpha_G^-3/2 m_p | g^-1 (and a^3/2 b^-3/4 for the lightest star) |
| star light, radius, lifetime, surface temperature | opacity, ignition temperature, fuel | b^2 g^1/2 a^-2; g^-1 a^-2; e a^2 b^-2 g^-3/2 |
| the IMF's break | a cloud's Jeans mass at chemistry's cooling temperature | a^3 b^3/2 g^-1/4 |
| alpha-decay half-lives (uranium, thorium) | the Gamow barrier | e^(Gamow x (a - 1)) |
| the light that drives chemistry, and the light that breaks it | Planck's spectrum against bond energies | computed per star |

Holding G, hbar, c and k fixed keeps the engine's units (solar masses, AU, years, kelvin) and Kepler's law; the
particle masses carry the change. Progenitors change a law with a genesis such as `cosmic:teeming:measured:alpha=1.02`
and rebuild the universe from the same dice (creation.dice): one star's mass draw, one orbit, one impact - now under
other physics. `tools/progenitor.py` compares universes so made.

## The ledger

| Quantity | Full form | What the engine uses | Status |
|---|---|---|---|
| Space between galaxies | a 3-sphere of radius c / H0 / sqrt(Omega - 1) | arcs of the 3-sphere (geometry.arc_kpc; sphere, cluster) | **restored** |
| Space within the galaxy | curved by its matter: ds^2 = -(1 + 2 Phi/c^2) c^2 dt^2 + (1 - 2 Phi/c^2) dl^2 | the weak-field metric of disc, halo and central black hole: proper lengths, Shapiro delay, lapse (geometry.py) | **restored** (its effects are parts in a million: computed, not assumed) |
| A star's clock | proper time along its path | lapse x the universal clock (cosmos.position) | **restored**, reported; game time is universal |
| A star's place | 3D: radius, angle, height above the plane | radius, angle, and a vertical oscillation through the plane (geometry.vertical) | **restored**: the plane's crowding sets impacts and supernova exposure |
| The galaxy's cells | 3D volumes in a thick disc | 2D cells of the disc, each carrying its stars' vertical orbits | projected (sampling), declared |
| A world's orbit | six Keplerian elements | semi-major axis, eccentricity (stirred, forced, damped), inclination, node, perihelion (orbits.py) | **restored**; the game's calendar keeps exact rational periods |
| A world's spin | a vector: period and axis | period from birth spin and tidal braking, obliquity (isotropic, upright when locked) | **restored** (precession not yet) |
| Moons | worlds orbiting worlds | a giant's regular moons, each a world with tides from its giant | **restored** |
| A world's heat | radiogenic, primordial, tidal; in a mantle and core | four isotopes from its star's birth, mantle and core convection, tides (interior.py) | **restored** |
| A world's temperature | a field over latitude, season, depth | a mean, and a pole for the cold trap (worlds._cold_trap) | partly restored: latitude for condensation; seasons still a mean |
| Starlight | a spectrum | the share that drives chemistry and the share that breaks it, from the star's own temperature (worlds.band) | **restored** as two bands of a Planck spectrum |
| An atmosphere | a column with structure | one surface pressure, one grey optical depth, broadened by pressure | projected, declared (the greenhouse fit) |
| Life | populations of genomes in space and time | a lineage's information: the rungs its chemistry's fidelity needs and the time to write them (life.py) | projected, declared: no knob says how common life is |
| A mind | a nervous system | I_MIND bits of blueprint; a people's council as one collective mind | projected, declared |
| Time on a world | days, seasons, years | universal cycles; each world's year for its own reckoning | restored for reckoning (CLOCK.md) |
| A world through deep time | a history: its star brightening, its interior cooling, its air gathered and lost | `worlds.history`: the same physics read at ten ages, with the young star fainter (Gough) and the magma ocean's degassing | **restored** for questions about a world's past (`tools/scenarios.py`); creation still reads one settled age |
| A system's small bodies | belts and comet clouds of every size and orbit | belts by where the disc went ungathered, composition by where they condensed; comet clouds by giants and passing stars | **restored** (creation._belts) |
| A world's seasons | sunlight by latitude and day | the share of the year and surface over half its latitude's mean light (physics.growing_share) | **restored** from a linear tilt penalty |
| Travel between stars | sublight, by the rocket equation, or folded space | in-system for every people; between stars once a people crosses (mastery.py) | **restored** as a crossing a people earns |
| Peoples' awareness of each other | light crossing the galaxy | leaked power against instruments and light-time (signals.py) | **restored** |
| A galaxy's prehistory | every people's history over billions of years | a history-level life per mind from declared rates (prehistory.py) | projected, declared: the ranges are the progenitors', the full engine's runs measure them |
| Life's lineages | many clades climbing at once, extinctions pruning some | `life.ERASURE`: "rung" (one lineage, impacts reset its rung) or "clades" (CLADES lineages, each impact killing each with its severity, survivors radiating) | **restored** as a choice of law, compared by the scenarios |

## What is still a number someone chose

Each is stated once, in its module, as **declared**: the disc's normalisation and lifetime, giant-impact growth,
comet composition, the wind's dose (STRIP_RATE) and the fragments' energy (HOT_EV), the heat-transport column
(TRANSPORT_BAR), the weathering scale, the greenhouse fit, the photolysis threshold, the activation-energy scaling
of catalysis (SOLVENT_BARRIER), the bond thresholds, the light that lifts an electron (PHOTO_LOW), the discrimination
share (DISCRIMINATION), the bits of a monomer and of a mind (I_MIND), a cell's body per monomer, the impact and
sterilisation rates at unit density, the Simon-Glatzel exponents, the tidal Q, and the eccentricity stirring.
`tools/progenitor.py --sensitivity` perturbs each and reports how far the universe's outcomes move: an outcome that
swings on one of these is the next to be given better physics.
