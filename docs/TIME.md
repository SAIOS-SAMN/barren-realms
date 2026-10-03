# Time: two directions, a clock in every place, and peoples ordered by their ledgers

This is our universe's physics of time, held as true here (fundamental.py, Mycelium's laws 9 and A.7-A.10, the
white-hole source of `physics::source`).

## Two times

Spacetime lives in its conformal embedding with two time directions (Cl(4,2): two-time physics). One is gauge and
one is lived.

| Time | What it is | Who reads it |
|---|---|---|
| Cosmic (`cosmos.deep_gyr`) | the gauge direction: the frontier at which creation happens | star formation and death, minds waking, the galaxy's turning |
| Proper (`clocks.place_now`) | a clock kept by every place where life has woken, paced by the peoples living there, at the galaxy's pace where none do | that place's star, climate and world ageing (`cosmos.deep_gyr(kernel, sector_id=...)`) |

A place's clock never jumps: it keeps its reading through every change of pace. Two places never need to agree on
a now. Orbits are closed-form functions of whatever clock reads them, so they stay exact.

## Peoples are ordered by their ledgers

A people's time is the height of its ledger (`clocks.height`): one receipt for each year it lives, and wherever its
worldline meets another's - ships or words meet (contact), light is heard (signals), space is folded - its next
receipt cites the other's head:

    h = 1 + max(h_own, h_other)

Peoples never linked are concurrent, permanently. No decision waits on an order between them, and nothing is ever
"caught up": the ancients' millions of years and a young people's thousands are never laid on one line. They meet
where their worldlines meet (WORLDLINES_MEET).

## One law of motion; the fold

Motions on one plane compose as `t1 (+) t2 = (t1 + t2) / (1 + k t1 t2)`, `k` the square of the plane
(`geometry.flow`):

- `k < 0`, turns: tangents add, and turns return - orbits are periodic;
- `k > 0`, boosts: Einstein's addition - no voyage reaches light, and boosts never return: the arrow of time;
- `k = 0`, the null flow: amounts simply add. The fold is the null flow: no proper time passes for the one who
  folds, and the passage is written in its ledger (`clocks.fold`).

## Torsion, the black hole and the white hole

Matter's spin couples to torsion (Einstein-Cartan). At the Cartan density torsion repels and collapse bounces.
What crosses a black hole's horizon becomes, on the other side, the white hole that is a child universe's Big Bang
(`blackhole.child`, CHILD_UNIVERSE), carrying the matter and the records of what fell: torsion is never destroyed,
so information never is. The conformal inversion that swaps near and far is what turns the sink into its source.
Our universe began as the white hole of a parent's black hole (BIG_BANG).

## Still to build

- Proper time from the metric as well as from watchers: a place deep in its galaxy's well (`geometry.lapse`) runs
  slower by the metric's own rate.
- The fold's cost and reach as a null flow's geometry, beyond its timing.
- Descending into the child universe: a progenitor seat that begins the universe beyond our centre's horizon from
  what crossed it.
