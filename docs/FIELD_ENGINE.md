# The field engine

*Operator direction, 2026-10-08, aligned with the coordinator. Python prototype first; the Rust port follows once
these laws settle.*

## Why

The kernel **walks**. About 100 subsystems scan every world each tick, top-down, line by line. Orbits are computed per
star on demand. The bounce returns a reservoir share to a listed set of worlds each season. It ran at 0.7 cycles/s
at 200 worlds, and gets slower as the galaxy fills.

The universe does not walk. The Einstein–Cartan bounce happened everywhere at once. Fields carry what moves.
Something reaches a world when its front arrives. The engine should compute it that way.

## The law

1. **Shared origin, many bells.** The bounce is the shared origin: the field's base state (its phase, its density)
   is known at every point with nothing propagated. Every singularity rings its own bounce pulse and echo, as its
   own **source term**: the centre, each throat's paired cores, each dying star. This is the time-as-bell ruling,
   which `pulse.rs` already models in the port as a Node per singularity, with Hearing and Relay.
2. **Closed-form fields.** A field's value at any place and time is evaluated directly from its sources' histories,
   by the retarded solution of its wave equation. Nothing marches cell by cell. Every point is evaluated
   independently, so the computation is parallel; the GPU field is the port's to build.
3. **Carriers and arrivals.** What a source sends reaches a place at the earliest time any physical carrier can
   bring it:
   - **light**, through ordinary space: the proper light-travel time, with its Shapiro delay
     (`geometry.light_gyr`);
   - **a throat or tube**, across its span: faster than the ordinary-space light cone, by the comms-latency ruling,
     since a word never outruns its fastest physical carrier and there is no light-time floor across lanes. Its
     transit is the tube's own law.

   Unauthorised wormholes are forbidden. Entanglement carries no signal. Inside the universe nothing acts before
   its carrier arrives; the "unison" is in the computation, never in the universe.
4. **Events are for external arrivals.** An arrival is scheduled once, when its source rings. A world takes it when
   the cosmic clock passes its time. A people's **internal** dynamics are never frozen waiting for events: they
   advance each step, or in closed-form spans that agree however coarsely time is stepped (the coordinator's
   span-robustness ruling).
5. **Exact at the seam.** The field is internal physics, and may be float (a legacy float, marked as such; the port's
   float crate awaits an operator ruling under 9.1a). Arrival times and field values entering the kernel are put on
   an exact grid: a Fraction of deep time. Conformance between kernels is by values within a declared tolerance,
   never by bytes.

## The prototype (barren-realms, `xylarium/kernel/field.py`)

- `Source`: a bell. Its kind (`bounce`, `echo`, `death`, `jet`, `word`), its place (galactocentric x, y, z in kpc),
  its time (deep Gyr), its strength, its pulse's e-fold time, and what it carries.
- `ring(kernel, source, targets)`: the source rings. Its arrival at each target place is computed once, by the
  earliest carrier, and queued in exact deep time.
- `pump(kernel)`: each tick, the arrivals whose time the cosmic clock has passed are handed to their kind's handler.
  Handlers are registered by the laws that take them.
- `value(kernel, place, t)`: the field at a place and time, the sum over every source whose front has arrived of
  its strength over distance, shaped by its pulse's decay. Closed form, with no walk over worlds.

## Owed, in order

1. Profile the live tick, and move the heaviest walks onto arrivals and fields first. Candidates are the bounce's
   jets to the bulge, a dying star's light on its neighbours, and the word between peoples.
2. The throat carrier: a tube's transit law (span, owner, handling).
3. The GPU field, in the port, once these laws settle.
