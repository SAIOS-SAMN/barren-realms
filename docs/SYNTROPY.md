# The two halves of the board's physics

Thermodynamics alone is only the dissipative half of physics: gradients run down, mixtures mix, structures wear
away. Priced on that half alone, the board came out inverted. The work to take matter apart made dilute things
cheap, so platinum cost less than iron and the superheavies were nearly free. The board needs the other half:
flows that build order against dispersal and hold it while they run. Information is conserved (unitary). Every
process moves order between scales; none only destroys.

| Level | What it does | Where |
|---|---|---|
| Dissipative (homeodynamic) | Gradients run down: diffusion, erosion, mixing, decay, extraction | `waste.py`, `energy.py`, the work terms in `substances.py` |
| Form-building (morphodynamic) | A gradient driven through a fluid builds form: convection, hydrothermal circulation, placer sorting, magmatic differentiation, life's redox | `concentration.py` |
| Hydromagnetic | A conducting fluid builds and holds a field; the field holds off the stellar wind and turns away cosmic rays | `hydromagnetics.py` (from `interior.py`'s dynamo) |
| Self-maintaining (teleodynamic) | Flows that keep their own constraints: life and minds | `life.py`, the syntropy ledger |

## What is derived now

- **One dynamo law.** A core runs a dynamo while q_cmb > q_ad (`interior.py`). The share of its heat a core tap can
  draw before the dynamo stalls is 1 - q_ad / q_cmb (`hydromagnetics.margin`). This replaces
  `harvest.CONDUCTION_SHARE`.
- **Field.** The dipole moment comes from the power-based dynamo scaling: core field ∝ (convective power)^(1/3),
  times core volume. The surface field falls as 1/R³.
- **Magnetopause.** The field and the wind balance where B²/2μ0 = P (Chapman-Ferraro). The share of the sky the
  wind reaches is (R/r_mp)².
- **Surface dose.** The stellar wind's share, plus galactic cosmic rays rising with the stellar density where the
  world circles. The field's cutoff rigidity turns cosmic rays away, and the air's column absorbs both. This is what
  the living's erasure will read.
- **He-3 in regolith.** It is implanted only where the wind reaches the ground.
- **Deposits.** Each element is laid down dispersed, as a fraction x of its host: rock, or ice for what leaves the
  rock as gas.
  - A world's flows each run 0 to 1 from its own physics:
    - magmatic: how many times it has melted its mantle;
    - hydrothermal: liquid anywhere × heat flow;
    - placer: surface liquid × heat flow;
    - biological: life.
  - Which flows gather an element is read from its bonds (Goldschmidt's classes).
  - The standing grade is x^(1 - k/2). With every channel running, a world reaches the x^(1/2) that measured ore
    grades follow. A world without flows holds only x.
- **Crust.** Melting carries what doesn't fit mantle crystals up into a crust, by its measured partition
  coefficient (batch melting: 1/(D + F(1-D))). F is the share the world melts, read from its mantle temperature
  between rock's solidus and liquidus, and is never below the ~1% a melt needs to leave its rock. Uranium rises about
  20× on the unit world; nickel stays below.
- **Radiation and the living.** Each people's repair is tuned to the dose of the world most of its kind live on.
  Each home dose more erases about what a home dose does over a life: the unit world's background, ~1%, linear, no
  threshold. That enters the chance a newborn lives to old age (`lifespan.thr`). A people takes the dose only where it
  lives:
  - nothing under ice or deep, where the overburden shields it;
  - nothing where its medium stands nowhere on the world's surface, because it lives enclosed;
  - otherwise the surface dose, on those under the open sky, while its habitats shield the rest.
- **Renewal.** A taken deposit is rebuilt toward its standing grade at the pace of its flows (`geology._rebuild`).
  Where the flows have stopped, nothing comes back.

## Where the elements come from (`enrichment.py`)

The Big Bang gives hydrogen and helium only. Everything heavier is made by the galaxy's own stars, and it is always
moving:
- Gas falls in inside-out.
- Stars form per orbit above Toomre's threshold, and on their own free-fall time below it.
- Four channels make each element on their own clocks.
- Stars give back 40% of their mass, half of it over gigayears at their birth mix.
- Fountains mix what is made a radial epicycle each way, by weight (Graham: 1/√A).
- Dense star formation lifts winds into the halo, which rains them back over ~1 Gyr where gas is falling in.
- Gas drifts inward at about 1 km/s.
- The centre takes what reaches it: a share passes across the horizon into the child universe, and the rest returns.
- Stars burn hydrogen into helium and metals (dY/dZ ≈ 2).

Mergers are lumpy: a star's birth cloud holds a Poisson count of recent events.

Calibration is to the measured gas near the Sun today (young B stars), one yield scale per channel. The model then
gives:
- gradients steepening by weight: oxygen −0.025, iron −0.069, uranium −0.105 dex/kpc (the Milky Way's are about
  −0.02 to −0.07);
- the core enriched first;
- oxygen-rich early gas;
- a ledger in which everything made is somewhere in the flow.

**The Sun as a prediction.** The radius whose gas 4.57 Gyr ago best matches the Sun's composition is 7.75–8.75 kpc
(rms ≈ 0.06 dex). The migration picture puts it at 5–7 kpc. The model's local gas reaches an equilibrium early, as
infall and inward drift balance what stars make, so its age–metallicity relation at the Sun's radius is nearly flat
over the last 5 Gyr. That matches the observed flat local relation (Casagrande 2011). The evidence for migration (the
Sun being richer than its same-age neighbours) needs stellar populations, which the model does not yet track.

**Worlds from their birth gas.** Every star's worlds are made from the gas at its radius and birth epoch:
- its metallicity sets the disc's solids;
- its elements set the deposits;
- a metal-free star has no worlds.

`creation.analogue` builds a star of any mass at any place and epoch, so a Sun-like star born where the model finds
the Sun can grow its own planets from that gas.

## Still to derive

- **Disc accretion.** Should depend on fields carrying angular momentum, and stellar winds should be sorted by
  first ionisation potential (FIP).
- **Affinity.** The signed affinity (yield − erasure, P3) should read the same dose for every substance's harm.
- **Commodities (P1b).** A good's anchor is the order it embodies (its grade, and the event that made its nuclei)
  times its renewal time, with extraction work as its cost. A market lists goods as civilisations stabilise trade in
  them, not from a table.
- **One star-formation history.** Stars are still drawn from creation's own inside-out curve, not from the
  enrichment run's star formation. Discs read a single metallicity rather than their gas's own iron, silicon and
  oxygen.
- **The centre at parsec scale.** This needs the black hole's mass, the tidal-density limit for forming stars, and
  the young stars that do form there.
- **Planet survival.** Close stellar passes, and discs evaporated by massive neighbours.
- **Clock pace (#149).** Place clocks are still paced by who watches. A folded world's neighbouring star dies at
  another cycle than a stepped one's (test_roles' inverse-compaction test is marked as an expected failure until pace
  comes from galactic position).
- **Interior fidelity.** In the current interior model a Mars-sized world still runs a dynamo at 4.6 Gyr.
