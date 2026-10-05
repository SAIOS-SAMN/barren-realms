# The universal clock

One time for the whole universe - the cycle, 100 to a standard year - and everything that moves under the same
physics moves in lockstep with it.

## Three clocks, one time

| Clock | What it counts | What runs on it |
|---|---|---|
| **Universal** | the cycle, 100 to a standard year | everything that integrates: food, births, deaths, thought, money - and every life as a physical duration (biology runs on chemical kinetics, not on orbits) |
| **Galactic** | deep time, Gyr since the Big Bang (`cosmos.deep_gyr`): the universal clock times the universe's pace | the stars' births, ageing and deaths, the galaxy's turning, minds arising |
| **Local** | each homeworld's year, its orbit about its own star (`clock.local_years`) | how a people reckons its age, seasons and rites |

Each star's own time also runs slow against the universal clock by its place in the galaxy's gravity and its speed
(geometry.lapse, reported by `cosmos.position`): a clock near the centre loses about a second a week against one at
the rim, parts in a million - computed, and too small to move a game year.

A people's own history and the galaxy's deep time are reconciled by its annals (annals.py): each year every people
is carried, at the level of history, through the deep years that passed since it woke and that it has not lived -
its farming, state, works, yards and crossing as waits in its own generations, its falls, its dominion among the
stars, its pacts and wars - so a people woken a billion years before another is a billion years older in what it
has become, not only in the dates on its ledger. The full engine then lives on from there, year by year.

A people is never aged on the galactic clock. One that is 300 universal years old at the teeming pace has seen 3 Gyr
of the galaxy and is 300 years old - or so many of its own years as its world has gone round its sun
(`clock.age_of_people`). Its lifespan is its species' physics in universal years (lifespan.py); its longevity is
judged on that, never on deep time. Its intelligence ladders are climbed once a universal year, on a year's
thinking - not on its local year, which runs from days to centuries across worlds.

## Keeping the clocks in step (clocks.pace, cycles_of, years_of, lived_span)

In a cosmic universe every peopled place keeps its own proper time, running at its own pace: its own years per clock
year, set by its watchers (tempo, clocks.season). One clock year is twelve own years at one seat and a hundred and
ten at another. Any span stated in a place's or a people's own years - a steward's term (its sender's generation), a
sovereign's memory of who struck it (a generation of its people), a ruling's standing - is converted to the clock
through that place's pace: `cycles = years / pace x 100`. The engine lives every place a frame at a time (a clock
year of seasons), so a span is never shorter than one frame (`lived_span`, the same Courant rule tempo keeps) - and
what turns over within a frame is counted, not dropped: a steward's line succeeds once for every term its seat's
clock ran (`stewardship.term_cycles`). A people's ledger takes one receipt for each of its own years lived
(`clocks.receipts`), not one per clock year. On the settled board one clock serves all (pace 1).

## Three kinds of motion

| Kind | What | How it advances | Where |
|---|---|---|---|
| **Clockwork** | orbits, spins, seasons, local calendars, insolation | closed-form functions of time; never stepped. Any moment of any body costs the same to compute (`clock.ephemeris(kernel, t)`, exact rational phases) | `clock.py`, `physics.orbital_phase` |
| **Integrators** | food, births, taxes, energy, the seasons' books | stepped at their natural cadence: the cycle (colonies, ports, markets) and the fiscal quarter (`subsystem.SEASON`) | `engine.tick_simulation` |
| **Events** | what minds decide | at each mind's own pace, from a persisted priority queue | `scheduler.py` |

## Orbital velocity, measured

`clock.velocity_of(kernel, planet)` gives a body's year (cycles), phase rate (1/year), angular velocity
(deg/cycle), orbital speed (AU per standard year, 2 pi a / P with a = q^2) and spin rate. `clock.measure()` gives the
galaxy's spread of them; it is in every observation (`observations.jsonl` as `clock.orbits`).

## Minds at their own pace

A captain's next turn comes `1/speed` cycles after its last, where speed is its substrate's kinetic pace
(`laws.cognition`): a biotic mind every cycle, a plasmic one ~6 times a cycle, a cryogenic one less often. Minds
first wake at their own phase within their pace (not synchronised). A turn that changes nothing - no move, money,
cargo, turns or research - doubles the wait, up to a fiscal quarter; any turn that does something resets it.
`config.AI_TURN_BUDGET` caps minds per cycle; the overflow is first in line the next cycle. Time within a cycle is
counted in `scheduler.MOMENTS` (1000).

## Determined universe, probabilistic minds

The universe is a function of its seed and its laws. Its initial conditions - every star, orbit, world and the
climb of life on it - are drawn once from the seed, keyed by place (creation.origin, scheduler.rng keyed by cell),
never by when anyone looks; after that, physics is evaluated in closed form at each epoch (orbits from their
elements, a star from its age, a world from its age, the galaxy's turning as an angle). No physical season draws
chance at run time (tests/test_determined.py enforces it). What is probabilistic is what lives: a mind's choices,
a people's history (annals, prehistory), biology among organisms (drift, blight), contests between agents - each
on its own stream.

## Tempo: the camera's speed (tempo.py)

Deep time is the universe's; the clock only films it, and how fast it films changes nothing it films. It runs as
fast as it can without stepping over what the living are in the middle of - an integrator's rule (a Courant
condition): no clock year holds more than 1/FRAMES of the shortest wait any living people has to its next turning
(its next bridge of history, in its own generations at its own minds' pace, or its fall). A people held from the
sky by its world waits only on its fall; a people among the stars holds nothing back. With no people mid-history,
deep time runs at the pace chosen at genesis (cosmos.ceiling): the galaxy turns fast between minds and slows to
watch each one rise. Changes of rate are kept as segments (cosmos.set_rate), so deep_gyr(cycle) is exact and
cycle_at(epoch) inverts it.

## A world: its physics, and what minds did to it (imprint.py)

A world in play is its base - what physics makes it at its age (worlds.state_of_planet, recomputed only when its
age moves) - with the ledger of what minds have done to it folded over it: strikes, shields, air given back or bled
away through a strained core, terraforming. Every act is one ordered entry with its maker; the folded result is kept
on the world for its readers, and `imprint.at(planet, cycle)` refolds it as it stood at any moment. Physics is never
re-simulated to show agency, and no mind writes into physics directly.

## Locked-in chance

Minds stay probabilistic, but every draw is drawn from a stream fixed by (universe seed, what acts, when):
`scheduler.lock(kernel, *parts)` seeds the stream of chance

* at the start of each cycle (`"cycle"`),
* before each mind's turn (`"mind", captain, moment`),
* for the rest of the cycle after the minds (`"world"`),
* before each season (`"season", name, cycle`).

So one mind's choices never shift another's luck, the caller's random state never leaks in, and dictionary or set
order (PYTHONHASHSEED) does not matter. `scheduler.rng(kernel, *parts)` gives a private `random.Random` on the
same streams.

## What is chance, and what is choice

Minds do not roll for what they want. Every decision - a captain's fights (Lanchester odds, prize, warrant), trips
(what each place in reach holds for its calling, over distance), dealings with natives, decoding, shore leave; a
patrol's beat; a people's civic works; a firm's freight orders - is a valued option chosen by `decide.choose`
(`motive.py` prices a captain's). The only randomness in a choice is the mind's misjudgement (its thermal noise).

What stays chance, locked as above: physical uncertainty (battle exchanges, detection, hazards on the lanes),
discovery (what a probe or an excavation turns up), inheritance (an offshoot's mutation), market noise in share
prices, and flavour (names, taunts).

## Velocity

How many cycles pass per wall-second - a throttle on the runner, never on the physics. The same seed makes the same
universe at any velocity.

    python3 tools/live.py --seed 7 --velocity 20      # 20 cycles/s (12 universe-years a minute)
    echo 0 > runs/seed7/velocity                     # change it while it runs: 0 = as fast as the machine allows

The velocity is saved with the universe: a resumed run keeps it until `--velocity` or the file changes it.
The runner prints cycles/s and universe-years per wall-minute at each observation.

## Checking lockstep

    python3 tools/lockstep.py --seed 7 --genesis primordial --cycles 200
    python3 tools/lockstep.py --from runs/seed1337/snapshot.json --cycles 50

runs the universe twice under different PYTHONHASHSEEDs and compares the saved states; it prints the first
diverging paths, or `LOCKSTEP: ... identical`.

## Where the time goes (settled seed 1337, cycle 209000, 172 AI captains)

Seasons ~37% (intellect's crystal reads, tourism, sustenance), AI turns ~27% (`cognition.think`, ~17 ms a turn),
colony ticks ~13%, markets ~10%. Primordial universes run ~10-50 cycles/s early (no captains).
