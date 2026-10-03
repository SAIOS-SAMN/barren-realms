# Minds: what a people is, how it thinks, and how it comes to know itself

## A mind and a population

A **mind** is the moment a species becomes a people. Somewhere a world's biology finishes Carter's four hard steps
- life, complex cells, multicellular life, intelligence - inside its star's window, unsterilised, on a world that can
feed a viable people (creation.py). From then on it is one civilization: a name, a body plan, a metabolism, a
reproductive strategy bred by its world's variability, and the light, gravity and ground it evolved on.

A **population** is how many of that people there are on a world. No individual is simulated or chooses. What every
individual does is a per-head rate, and every rate is the species' own:

* what a body eats: Kleiber's M^(3/4) x the kinetics of its chemistry at its homeworld's temperature; its mass from
  its homeworld's gravity (square-cube) and its life history (biosphere.metabolic_factor). The land divides the
  same food among them (Damuth's law).
* how it thinks: Landauer and kinetics at its homeworld's temperature - cold minds deep and slow, hot ones quick,
  noisy and shallow (laws.cognition, with the homeworld's own light).

What chooses is the people's **council**: one collective mind per world (decide.mind_of_planet) - its depth, speed,
judgement noise and a planning horizon of about one generation, steadied by the intelligence ladders its people has
climbed (intellect.py) and by how well it knows itself (below).

Two peoples of one chemistry and biology on different worlds under different stars are different peoples: a different
body, appetite, density, strategy, pace of thought, sky and culture. Every star now has its own mass and light (no
classes): no two homeworlds are alike.

## The fork: the population-technology saddle (syntropy.py)

    dN/dt = r N (1 - N / K(A)) - emigration - restraint
    dA/dt = thinking(N, free labour, leisure, depth) - 15% of A a year

(Kremer 1993, with Malthus and Boserup inside it.) Where a people sits at its land's capacity and its thinking only
replaces what depreciates, it is at a saddle: pushed toward a surplus, it learns, its capacity grows and its numbers
with it - toward the stars; pushed the other way, depreciation wins - overshoot, strife, famine. Standing still is
not a resting place.

Each people's **syntropy** S = ln K + ln(1 + A) + ln W (capacity, knowledge, worlds) is read every season; its
slope says which way it is moving, and a direction held for a generation is a TURNING in the ledger.

Which way it goes is its own choice. Once a generation a council with yards weighs its **fork** through its own mind:
outward (the room on the empty worlds its fleets reach, against the hulls to carry its daughters) or enough (live
within its world, frugality's productivity, against the room it gives up). Nothing tilts it but what it sees, and it
may misjudge; no covenant is forever.

## Coming to know itself (introspect.py)

A people reads its own gauges every year - sustenance, vitality, knowledge, intellect, creativity, prosperity, peace,
integrity - weighs them by aspirations that come from its own character, and pursues its widest gap.

Sentience in the full sense - a society that can look at itself - is measured, not granted. Each year a people
forecasts its own gauges for the next (its trend, blurred by its judgement), and the forecast is scored against the
guess that nothing changes. When its self-model has beaten that guess for a generation it has come to know itself
(INTROSPECTION); if its skill falls below for a generation, it loses sight of itself. A people that knows itself
judges better: its noise falls by its self-knowledge.

## The steward's counsel (counsel.py)

The steward sees no further than its people can think. Its counsel (the K key in the steward's screen) unlocks with
its people:

| Feature | Unlocks | What it shows |
|---|---|---|
| foresight | always | numbers against capacity over the council's horizon (short and blurred when young) |
| breadth | rungs climbed | as many plans at once as the highest rung reached - the fork's paths with the chance its own mind judges each best, and the goals it could pursue: a superposition that collapses only when the steward acts |
| self-model | INTROSPECTION | its forecast of itself and that forecast's skill |
| other minds | INTROSPECTION and contact | what each people it has met would choose at its own fork, read through that people's mind |
| memory | always | its turnings, coming to self-knowledge, contacts, exoduses and signals |

The counsel changes nothing; it is a lens.

## Learning and attention (learning.py)

Councils and captains choose by one loop (decide.choose): they perceive what their mind can see, value each option
from it, and choose by value over cost through their own judgement's noise. Two things make the guesses judgement:

- **Attention.** A mind weighs only as many options at once as its thought allows: two for a mind that has climbed
  no ladder, one more per quarter of fluid intelligence, one more if it knows itself. Offered more, it weighs those
  it first judges worth most, so a young people overlooks what an elder would see.
- **Lessons.** Each year every mind sets what it chose against how it fared by its own measure (a people by its
  syntropy index, a captain by the log of what it holds), against its own fading baseline. Each kind of choice it
  made is credited with how much better or worse it did than usual, and is valued by exp(that advantage over its
  usual swing) next time, weighted by how sure it is. Memory fades as knowledge does. A captain whose deed has
  failed it turns to what its growing seat proposes, if that has served it better.

A council's model of a neighbour (strategy.py) reads what that neighbour has done (its wars, raids, strikes),
what it can do unseen (cyber) and, as far as the council understands it (contact.intelligibility), what it is now
set on: a neighbour turned to growing is coming for room.

## Stewards (steward.py)

A steward - a player, or an intelligence set to the task - is one more voice in a people's collective mind, never
its hand. It perceives what the people can see (the counsel, its posture, its lessons) and no more. It guides in
three ways, all through the people's own weighing in decide.choose: urging an aim, drawing an option into the
council's attention that its thought would have overlooked, or cautioning against one. How much it is heeded is
learned like any lesson: each time the council chooses as its steward urged, that year is credited to the steward's
voice by how the people fared. In a council attending to n options, an urged option weighs 1 + heed / n: one voice
among the options in mind. The people still chooses on its own stream of chance and may refuse every word.
Progenitors set laws; stewards counsel; peoples choose.

## Steward intelligences and the progenitors' seat (steward_ai.py, client/progenitor.py)

A steward need not be a player. A steward intelligence is held to everything a steward is - it sees only what its
people sees, speaks only through its people's weighing, and is heeded only as far as heeding it has served them -
and brings patience: it weighs the same five aims its people's council weighs over PATIENCE times its people's
horizon with a steadier judgement, urges what that longer view chooses, and brings the exodus before the council
when the counsel shows its sun dying within that horizon. `python3 tools/live.py --ai-stewards` sets one beside
every people as it arises.

The progenitors' seat (`python3 main.py --progenitor`) writes a universe's laws (alpha, beta, alpha_G, the nuclear
yield, whether space folds), its kind of Big Bang and its pace, begins it, and watches: the galaxy's peoples, their
stages, postures, stewards and how far each is heeded, and the turnings of their history as the years run. It may
set steward intelligences beside peoples or withdraw them; it never acts on a people.

## When food becomes kin (kinship.py)

Every people eats its world's life. When it meets a mind of its own chemistry built like something it eats
(resemblance), or a mind wakes on a world whose life it once harvested (descent), its council weighs what it owes:
to abstain (the food sworn off: its land feeds fewer, less so if it can make food to order), to deny ("they are
not what we ate": its creed hardens), to continue (its alignment drifts toward the Dark, and the other people
remembers it - KIN_EATEN, which its model of the eater reads as harm), or to guard them. A council divided between
its best two choices records a schism. Eating something before it was a mind costs nothing; what a people does once
it knows is what it is.

## Coming into a body (technology.py: embodiment)

Life without a genome - minds held in fields - has no hands. Before works, yards or crossing it must come into a
vessel (a body designed from outside, matter built to order, or a machine), learning the terrestrial dimensions
from nothing. It skips genetics; this is its own, harder hurdle. Every genomed people is born in a body, and must
instead master its genome before it can live under another sun (mastery.genome_ready).

## Life and death (lifespan.py)

A people is born, grows, ages and dies by its species' physics. Every span is a multiple of its generation (body
mass^(1/4) over its chemistry's pace), read off Earth's people: maturity 0.6 generations, the end of the productive
span 1.7, adult life expectancy 2.5, the longest lives 4.3 - reached as it masters biology. Its people are three
cohorts: youth (fed, not yet working or bearing), prime (working, bearing, thinking, making) and elders (its memory;
they carry the exit). What the prime do - births, inquiry, work - scales with their share against the people's own
stable share, so a youth bulge waits and an ageing people slows.

**Total health resilience (THR)** is the chance a newborn reaches old age: nutrition x air x its star's light x its
world's cleanliness x how its biome suits it x shelter x what its crowd diseases spare. Mortality before old age is
-ln(THR) over the span to it, and fertility is TFR x THR. Crowd diseases are species living on the people: endemic
only above a critical community (Bartlett's ~250,000 for Earth's generation, scaled by the people's own), milder as
host and pathogen co-evolve, and carried on first meeting to a people of the same chemistry that has never had them
(EPIDEMIC, virgin soil).

A people sees its own fertility fall only if it can see itself: one that knows itself, or has climbed the ladders of
abstraction, plays the propagation card when it drops below replacement; one that cannot simply dwindles.

**The dead** return to the world as their people's staple (declared: decomposition) - or warm it, where its
chemistry burns and it has works to use the heat (a pyre: a declared energy source) - as it believes of its dead: a
people whose sky is a roof, or the eyes of the dead, lays them to rest. **The eminent** - the minds who carried a
turning, a founding, a first field, a coming to self-knowledge - are named (EMINENT), mourned (EPITAPH), sung in
its art's elegies, and forgotten over generations, slower where the dead are laid to rest and elders are many.

**Turnover** is the engine of change: a people has replaced itself when as many have died as now live, and only then
does it weigh its beliefs, art and fork again. What it knows dies with its knowers: Earth's measured 15% a year of
forgetting, its human-mortality share replaced by the people's own - a long-lived people holds what it learns, a
short-lived one must keep relearning.
