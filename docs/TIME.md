# Time: many clocks, meeting when peoples meet

Physics has no universal present. Every place's clock runs at its own rate, and events far apart have no agreed
order until a signal joins them. Xylarium follows that: the universe is a function of its seed and laws evaluated
at any time; what needs a clock is only what lives in it, and each part keeps its own.

## The clocks

| Clock | What it times | How it runs |
|---|---|---|
| Universe and galaxy (`cosmos.deep_gyr`) | stars forming and dying, minds waking, the galaxy's turning | the pace chosen at genesis (`cosmos.ceiling`), slowed only for peoples that share it (`tempo.py`) |
| A people's own (`clocks.py`) | a people no one has yet observed: its history, its world's star, climate and ageing | its own history's pace - a few frames to each of its turnings (`tempo.wait_years / FRAMES`) |
| Orbits | where every body is | closed form at whatever time a clock reads: exact, never stepped |

A place reads the clock of the people that keeps its own there (`cosmos.deep_gyr(kernel, sector_id=...)`):
`worlds.world_age`, a star's phase and years left, the climate's swing. Everywhere else reads the galaxy's.

## When clocks meet

Two clocks must agree only where their peoples interact. A people keeps its own clock until another can see it:

- it hears another people's light or is heard (`signals.py`);
- it meets another people (`contact.py`);
- it crosses to the stars (`mastery.py`).

Then its clock meets the galaxy's (`clocks.sync`, a CLOCKS_MEET event): the years of the galaxy's now that its
history has not yet lived are lived at the level of history (`annals.py`, against the people's own now), and from
then on it shares the galactic now with everyone it can reach - and holds the galactic clock to its own turnings
(`tempo.py`).

So a rising people lives its history in full, year by year, while the galaxy runs on at its own pace; no single
people freezes the galaxy, and nothing observable is out of order: no one could have seen it before its clock met
theirs.

## Stages

1. **Built.** Per-people clocks for peoples no one can observe; places read their people's clock; clocks meet at
   signals, contact and crossing; the galaxy runs at its pace; annals live each people's history against its own
   clock.
2. **Causal windows.** Two peoples a distance d apart can disagree by up to d / c without contradiction - each sees
   the other as it was when its light left. Let peoples in contact keep their own clocks within that window, each
   seeing the other's state as of the light-time ago (signals already date what is heard), and meet only when
   their ships or words actually cross.
3. **Lowest time first.** Advance whichever clock is furthest behind among those that can affect one another
   (conservative parallel discrete-event simulation), so far-apart regions run independently and cost nothing
   until they meet.
4. **Proper time.** Each world's clock also carries its gravitational and kinematic rate (`geometry.lapse`): a
   world deep in its galaxy's well ages slower than one on the rim, by the metric.
5. **A progenitor's law.** Time with more than one dimension, offered as a law a universe can be begun under -
   knowing that it costs predictability, orbits included.
