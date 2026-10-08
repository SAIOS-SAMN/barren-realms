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
   an exact grid: a Fraction of deep time, or of a value's own float. What crosses the seam is exact and compared
   exactly (Concordance 9.1: the same exact decoded values; never bytes). Floats stay inside a kernel.

## The field law (operator ruling, 2026-10-08; xylarium-kernel docs/FIELD_LAW.md)

The ruling supersedes the scalar field: **a pulse is a versor**, not a strength.

- **The pulse.** Each pulse is an exact versor of Cl(4,1) (`xylarium/kernel/versor.py`, every coefficient a
  Fraction). It can be bent (a translator), rotated (a rotor through a rational point of the circle, never a float
  angle), twisted (a screw, whose pitch is its wavelength) or flipped (a reflection, an odd versor). A loop of pulses
  that fails to close carries its residual translation as **torsion**.
- **The star absorbs it** (`field.absorb`). The pulse's versor shears each of the star's worlds' orbits. Each world is
  anchored at its core, a 0D point at its orbit's radius from the star's G point. The star gives out the **gravity**
  that locks them again: the work to undo each shear, ½ m (M/a³) |dx|², or all it can of what came in. It commits the
  rest to its burning. Of that, a share **burns out** (hydrogen's mass defect to helium, 7/1000) and the rest leaves
  as **light**.
- **Conservation, exact:** energy in = gravity + light + burned out. What the star cannot re-lock stays sheared.
- **The energy unit** is Earth-mass · AU² · (year/2π)⁻². Kepler's 4π² is absorbed in the unit, so an orbit's stiffness
  is M/a³ and everything stays a Fraction.
- **Floats are quarantined.** None touches an orbit.
- **Owed:** quantum radiation, the bell's harmonic, luminal and quantum state, as a factor in species and planet
  evolution, strongest near cores and accretion discs; and how torsion's pitch derives from the Einstein–Cartan
  bounce.

## The prototype (barren-realms, `xylarium/kernel/field.py`)

- `Source`: a bell. Its kind (`bounce`, `echo`, `death`, `jet`, `word`), its place (galactocentric x, y, z in kpc),
  its time (deep Gyr), its strength, its pulse's e-fold time, and what it carries.
- `ring(kernel, source, targets)`: the source rings. Its arrival at each target place is computed once, by the
  earliest carrier, and queued in exact deep time.
- `pump(kernel)`: each tick, the arrivals whose time the cosmic clock has passed are handed to their kind's handler.
  Handlers are registered by the laws that take them.
- `value(kernel, place, t)`: the field at a place and time, the sum over every source whose front has arrived of
  its strength over distance, shaped by its pulse's decay. Closed form, with no walk over worlds.

## Seat readings

A seat's PERCEPT carries the field it hears as typed records in the barren lexicon, all exact Q:

- **kind 6**, an arrival heard: `[Key(bell), Q(arrival, deep Gyr), Q(strength)]`;
- **kind 7**, the field value at the seat's world: `[Q(deep Gyr now), Q(value)]`.

The tube carriage between universes is the court's (mycelium 78.37 transport); a kernel's own throats are its own.

## Owed, in order

1. Profile the live tick, and move the heaviest walks onto arrivals and fields first. Candidates are the bounce's
   jets to the bulge, a dying star's light on its neighbours, and the word between peoples.
2. The throat carrier: a tube's transit law (span, owner, handling).
3. The GPU field, in the port, once these laws settle.
