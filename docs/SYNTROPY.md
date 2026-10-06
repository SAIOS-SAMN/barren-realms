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
- **Renewal.** A taken deposit is rebuilt toward its standing grade at the pace of its flows (`geology._rebuild`).
  Where the flows have stopped, nothing comes back.

## Still to derive

- **Magmatic incompatibility.** Uranium, thorium, potassium and the like are enriched into a crust by melting,
  through their measured partition coefficients. Without it, uranium is thinner than on real worlds.
- **Disc accretion.** Should depend on fields carrying angular momentum, and stellar winds should be sorted by
  first ionisation potential (FIP).
- **Erasure.** Affinity and the living's erasure should read `hydromagnetics.dose`.
- **Commodities (P1b).** A good's anchor is the order it embodies (its grade, and the event that made its nuclei)
  times its renewal time, with extraction work as its cost. A market lists goods as civilisations stabilise trade in
  them, not from a table.
- **Interior fidelity.** In the current interior model a Mars-sized world still runs a dynamo at 4.6 Gyr.
