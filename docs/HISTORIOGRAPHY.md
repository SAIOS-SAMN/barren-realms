# Proposal: memory, record and myth - how a people's past survives, decays and is reimagined

Status: proposal, for the steward's ruling. Grounded in the seed-7 run of 2026-10-03 (`runs/eons/seed7`, cycle
20,852) and in the engine as it stands. Nothing here is built yet.

## 1. Why

The run showed a history layer that writes events but has no idea how a people *keeps* them:

- 1,842 myth entries, 1,426 of them "brother rose against brother", one story re-told independently on every
  world (`society._myth` keeps myths per world and tells each from a template);
- 102 civil wars logged as "0% would rise, 0% under arms" - any unrest beats an army of zero (`society._strife`);
- 11 peoples with no art, young colonies with a culture but no history, and old peoples whose deep past has no
  record at all;
- nothing is ever forgotten, misremembered, rediscovered, forged or lost.

A people's past is not its ledger. The ledger (`history.py`) is what happened - the universe's own record, which
no one inside it reads. What a people knows of its past is what survived in the media it could make, copied by the
minds it had, through what befell them. That is the missing layer.

## 2. The principle

**History is information carried through a medium against erasure** - the same physics as life's ladder
(`life.py`): a record is written at a cost, kept by a substrate against the noise of its world, copied with an
error per copy, and lost when it is neither kept nor copied. Myth is what a record becomes when it is carried by
minds alone: re-told, compressed, and filled in by imagination as its fidelity falls.

Nothing is Earth's. Stone, papyrus and ink are one people's answers to a general question - *what can this mind,
with these hands and this knowledge, write on, in this world, and how long will it last?* The answers follow from
the world's physics, the mind's profile (`mind.py`) and its capabilities (`technology.py`).

## 3. Media of record

Every people holds its past in one or more media. Each medium has five measured properties:

| Property | Meaning | Derived from |
|---|---|---|
| write cost | energy and time to record one unit of meaning | the substrate's bond energy x the people's tools (materials mastery) |
| capacity | how much one record holds | the substrate's bits per mass; the mind's own memory for living media |
| retention | half-life of a record left alone | the substrate's bond energy against its world's kT, erosion, ice flow, tectonics, radiation, biology |
| copy fidelity | error per copy (or per retelling) | the medium's own discrimination - the life ladder's `eps`, read for records |
| reach | who can read it | the medium itself and intelligibility (`contact.py`) |

The classes, de-earthed:

1. **Living memory** - carried in minds and nothing else. Capacity: what minds hold. Retention: one lifetime per
   holder (`lifespan.py`), renewed only by being told to the young. Copy error per telling: high, and shaped by
   the mind (§5). A collective (`mind.profile`: collective) pools its memory: retention far longer, error lower.
2. **Enacted memory** - kept by doing it again: rite, song, dance, signal trails, pressure-and-resonance lattices
   for an aquatic people, scent maps for a chemical one. Retention: as long as the rite is kept. Copy error: low
   where the creed is rigid (`dogma`), high where it is loose. Its form follows the senses (`mind.profile` sense:
   light, chemistry, heat and pressure, fields).
3. **Inscribed memory** - marks on the world itself: cut into rock, grown into shell or coral, frozen into ice,
   etched into crystal, magnetised into iron sand. Write cost: high (hands, tools, bond energy). Retention: long
   (bond energy against its world's kT; ice flows, rock weathers, coral dies). Capacity: low.
4. **Portable memory** - thin, cheap substrates: grown sheets, woven fibres, chemical films, strings of knots or
   beads. Opened by materials mastery. Write cost: low. Retention: short (its world's humidity, temperature,
   biology). Capacity: high. Copied easily - and with error each time.
5. **Machine memory** - records in thinking machines (`computation`). Capacity: vast. Retention: short without
   upkeep (decay of the medium, loss of the means to read it) and long with it. A people that falls loses its
   machine memory first.
6. **Self-written memory** - records written into bodies: a plastic mind's edited self, a genetics people's
   written genome, a transfer people's carried minds. Retention: generations. The ancients' way.
7. **Carried beyond** - what crosses the centre's horizon (`blackhole.child`): records kept whole on the far side
   of a white hole. No one in our universe reads them; a child universe's first minds might.

Which media a people has is not a tree. Living and enacted memory exist from the first day. Inscription needs
hands and a world with something to mark (an under-ice superorganism with tendrils may grow memory into shell
long before it could cut rock; a plasma mind has nothing to inscribe until it is embodied). Portable media need
materials mastery; machine memory needs computation; self-written memory needs plasticity, genetics or transfer.
Each opens the way capabilities do now: found on the people's own knowledge, weighted by its kind of mind.

## 4. A record's life

Every event a people witnesses can become a **record**: `{event, medium, fidelity, copies, last kept, variants}`.

- **Written** where the people has the medium and the means. Who writes is the people's own: the collective
  itself, or the specialists a granary frees (`knowledge.effort`). An unwitnessed event leaves no record - the
  ledger knows it; the people never will.
- **Kept or lost** each year by its medium's retention, reduced by what befalls the people: strife and war burn
  archives, a star's death or exodus leaves inscriptions behind, a fall loses machine and portable memory first.
- **Copied** where the people tends its records (a share of its effort, more where it values its past -
  `society` temple gauge). Each copy restores the record and adds the medium's error.
- **Carried** with settlers: a daughter world inherits its parent's records, not new ones, so a myth is one
  myth with variants, not a thousand inventions (this removes the 1,426 duplicates).

Fidelity is a number from 1 (as it happened) toward 0 (nothing of it left). Below a threshold, a record kept only
by living or enacted memory **becomes myth** (§5). Below a lower one, it is **lost** - except as ruins: inscribed
media outlast their makers (`archaeology.py`).

## 5. Myth: memory, compression and imagination

When a record survives only by being told, each telling changes it, and the change is not noise alone:

- **Compression** - detail drops away first: numbers round and swell, many actors become one, centuries collapse
  into "long ago".
- **Agency shifts** - causes become intentions; the sun "turned its face away", a sickness "walked out".
- **Merging** - two records alike enough become one story.
- **Imagination fills the gap** - what is lost is replaced from the people's own culture (`culture.imagined`,
  `mind.profile`): an aquatic collective fills it with swarm-epics where the many are the hero; a solitary
  land-walker with a single hero against the world; a people under a dying star with endings.

How much each telling changes the story is set by the mind: low for a pooled collective with a rigid creed, high
for short-lived, imaginative individuals with a loose one. Creativity is a rate, from fluid intelligence, spare
thought and openness (`society` gauges).

What the people believes about its past is then **historiography**, and it has events of its own:

- **REDISCOVERY** - an inscription or a ruin is read again, and a myth meets its record: corrected, or the record
  is denied (dogma decides);
- **REVISION** - a state rewrites its records (a creed, a conqueror, a federation's doctrine);
- **LOSS** - an archive burns, a medium decays unread, a language is forgotten;
- **TRANSLATION** - another people reads a record across intelligibility (`contact.py`), with that loss;
- **CANON** - a collective or a creed fixes a version, after which it drifts slowly.

Lore, for the galaxy, is what any people can still recover: its own records, others' through contact, the
ancients' through ruins - and, beyond the centre's horizon, what crossed into the child universe.

## 6. Creativity and art

Art comes from the same media as memory, by the same physics: an aquatic people's art is pressure and resonance,
a land people's paint or carving, a machine people's generated forms. It needs a medium the people has, a share
of its thought, and a culture to draw on - not only leisure. Art survives as records do, so the oldest art left in
the galaxy is inscribed art. A people with no art today is a people with no medium for it yet, which is a story,
not a gap.

## 7. Fixes from the run

| # | Fix | Where | How |
|---|---|---|---|
| F1 | Strife fires on nothing | `society._strife` | an uprising needs people to rise: the rising share times the population must reach a viable band (`creation.VIABLE`), and must exceed the levy by more than the levy's own resolution - a world of zero unrest and zero arms is at peace |
| F2 | One myth told a thousand times | `society._myth` | myths become records (§4): held by the people, carried to daughters as variants, told once and retold with drift |
| F3 | Legacy crash in a physics universe | `cartography.solve_puzzle` | the old map's fixed sector numbers (78, 88, 92, 105, 106) are guarded: in a cosmic universe the puzzle's prize is placed in a charted sector, or the puzzle is not offered |
| F4 | The centre may be overfed | `blackhole.capture` | measure the core's stellar death rate against what fell (56 million suns in 0.2 Gyr) before changing anything; if the capture radius or the core's star count is the cause, fix that |
| F5 | Speed falls with worlds | profiler | the hot paths per world per cycle (`tick_colony`, capacity questions, topology distances), with a clean measurement on an unloaded machine |

## 8. Order of work

1. **F1, F3** - small and unblocking: the next run should neither drown in false strife nor crash.
2. **Records and media (§3-4)** - a `memory.py` holding each people's records by medium; media opened by
   capability and world; retention and copy error from the substrate's physics; settlers carry records. **F2 is
   this step.**
3. **Myth as decayed record (§5)** - telling, compression, merging and imagination; the historiography events.
4. **Art from media (§6)** - art follows the media a people has.
5. **F4, F5** - measured, then fixed.
6. **Run again** with the eons tracking: the same seed, read centre outward, and the gap census compared with this
   run's.

## 9. How we will know it works

- A people's myths are few and old, each with variants across its worlds, and each traceable to a record.
- Early peoples' deep pasts survive mainly as inscriptions and ruins; late peoples' as machine memory that a fall
  erases first.
- REDISCOVERY happens: a ruin or an inscription read again changes what a people believes.
- The 102 false civil wars disappear; strife comes with hunger, unheld order and people under arms.
- Cultures differ by medium: an aquatic collective's history is enacted and grown; a land people's carved, then
  written, then stored.
