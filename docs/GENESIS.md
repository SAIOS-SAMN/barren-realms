# Genesis: a universe that starts before spaceflight

`GameKernel(seed, genesis="primordial")` (and `tools/live.py --genesis primordial`) opens a universe in which
**every people lives on the world it evolved on** and nothing is spacefaring:

* every civilization is at citadel 0 on its homeworld, numbering what its world feeds before industry (its
  citadel-0 carrying capacity - not a dice roll), Sol's Terrans included, with the same vault, guns and garrison
  ranges as everyone else (Terra's old 50k vault and 1000 fighters were a gift of the settled board);
* there are no starports, no ships, no companies, no great powers (the Imperium, the Choir), no genesis realms;
* the worlds, stars, crusts, biospheres, natives and ruins are as physics made them; the money institutions (the
  Reserve, the federations' banks, the exchange) exist with their founding stakes.

Everything else has to happen. `state["genesis"]["firsts"]` records when it first does (and `observations.jsonl`
carries it each reading), so a run *is* the baseline.

## What emerges, and from what

| Milestone | What makes it happen (no thresholds) |
|---|---|
| Citadels | a council raises its citadel when the room it buys is worth its cost (demography `_works`, decide.py) |
| Shipyards | citadel tier 2 (sustenance.yards): no yards, no ships - settlers, raiders and captains all need them |
| First starship + first starport | a world with yards commissions a hull when the trade it would carry (surplus out, shortfall in, at the carrier's share import orders pay) beats the hull - and founds the dock it needs (colony.check_planetary_spaceflight) |
| Captains in service | one hull per shipyard world (populace.ai_capacity): the lanes are as busy as the galaxy's industry |
| The charted universe | a cluster is charted when observed: a ship on the edge, or a shipyard world whose fleets reach it (observation.py) - no quota, no cap |
| Firms | founded where a port's measured offtake leaves residual demand that pays (enterprise.py) |
| Daughter worlds | a people with yards past its growth inflection, by policy, temperament and alignment |
| Realms | a people with yards or two worlds |
| Wars | hunger (pressed worlds raid) and plunder (a fed people with ships raids the weak when the take beats the losses) |
| Tributaries and empires | protection-for-tribute contracts both minds accept (relations.py) - see below |

## The baseline (three seeds, primordial genesis)

Years from genesis to each first, per seed (7 / 1337 / 42):

| First | pre-energy kernel | energy era (yards gated by knowledge) |
|---|---|---|
| citadel 1 | 0 / 0 / 0 | 0 / 0 / 0 |
| sunfields, core bores | - | 1 / 1 / 1 |
| shipyards, starship, starport | 9 / 9 / 9 | 13 / 21 / 17 |
| war, first tributary, first empire | 9-10 everywhere | same year as the first starship |
| orbital arrays | - | 14 / 22 / 18 |
| first firm | 17 / 19 / 17 | 16 / 35 / 30 |
| first daughter world | 57 / 69 / 82 | 51 / 35 / 32 |
| first multi-world realm | 230 / 102 / 215 | 329 / 176 / 338 |

* In the pre-energy kernel spaceflight came at year 9 in every universe - set by the citadel build lock and
  fixed costs, not by anything peoples knew. Yards are now orbital construction (cost / mastery): spaceflight
  arrives with materials knowledge, and its date differs from universe to universe.
* The first people with ships becomes the first patron the same year: the threat it poses is what its weak
  neighbours buy off. Empires reach 25-33 peoples and ~60-105 worlds by year 400-500.
* Core boring is chosen freely and costs real worlds: by year 400-500, 5-11 worlds per universe had stalled
  their dynamos, and 0.6-1.7 million people could no longer be fed - each counted as harm in alignment.
* Each universe runs 40-80 distinct harvest designs; crude ore works dominate where peoples hold none of the
  materials they know, element-rich peoples build Stelalith-Ferrolattice and Pyrosite sunfields and arrays.
* What still needs no prepopulation: everything above. What does: worlds, peoples at their pre-industrial
  capacity, natives and ruins, and the money institutions' founding stakes.

## When hierarchies emerge (the answer to "under what circumstances")

Measured, not assumed:

* **No threat, no hierarchy.** In a fed galaxy where only hunger drives raids, 59 peoples with 57 of them in each
  other's reach formed *no* tie in 250 years: the threat every people faced was zero, so protection was worth
  nothing. Contact and strength asymmetry alone do not make empires.
* **Predation makes them.** Once a fed people with ships may raid the weak when the take beats its expected losses,
  the strongest neighbour becomes the threat a weak people buys off - and tributary trees form within years:
  vassals of vassals around the peoples whose strength reaches furthest (feudal depth 4-5).
* **What bounds them** is physics: strength falls off with distance (1/(1+hops)^2) and is projected only as far as
  ships sail; a patron's troops are shared across every world it stands behind, so each new tributary is worth
  less to the next; tribute cannot exceed what a tributary's vaults actually keep; a contract ends when it no
  longer leaves both better off, or when the tributary falls a year behind.
* **What the minds needed**: a two-sided agreement (decide.agree - both judge their own side with their own
  error), and a measured threat (the galaxy's attack rate per world-season, each attacker's odds, a world's stores
  lost at most once). They do not yet anticipate a rival's best response or value reputation: deterrence and
  balancing coalitions are the next layer.

## Further back: the forager genesis

`GameKernel(seed, genesis="forager")` (`tools/live.py --genesis forager`) starts before fields and states (ways.py):

* every people forages: it numbers what its wild land feeds a link up the food chain - a tenth of what the same land
  feeds farmed (Lindeman's ten-percent law); no state, no treasury, no taxes, no money, no works;
* it learns by doing (a season's gathering teaches biology at its minds' depth, a thousand people-years to a unit),
  and harvesting wild stands breeds the crops without meaning to - Lande's equation, `genome.VARIANCE` x its
  mastery x how hard it presses its land, a crop generation a year;
* it takes up farming when the room its half-wild crops would make outweighs the toil of farming unknowingly
  (the population times what it has not learned) - its own elders judging (decide.choose);
* farmers breed on purpose; a state forms when the surplus (1 - wild/farmed yield) can bear a state's share and the
  room a citadel would buy is worth more over its horizon than what the state takes. From then on it is the
  primordial genesis.

Measured (seeds 7 and 42): with peoples of ~1,000 foragers, crop selection runs at ~0.1% of an e-fold a year -
the forager age lasts centuries, longest for the smallest peoples; a hot, noisy mind sometimes farms early by
misjudgement. The largest peoples domesticate first.

## Making peoples, and making worlds for them

* **Designer** (designer.py; `SPECIES_DESIGN` previews, `SPECIES_SEED` sets down): a metabolism, a body plan (its
  reproductive strategy) and the six genome axes. What you get is your genome-editing mastery times what you ask;
  every deviation costs. 500 founders (Franklin's 50/500 rule) on an empty world where the body has a niche and the
  wild land feeds them; they begin as foragers with nothing learned, and the world selects them from then on.
* **Terraforming** (terraform.py; councils choose it among their works, captains by `TERRAFORM`): the world is
  processed toward the ground a biology fits best - every biology's fit moves toward its fit on that ground,
  fit(t) = h* + (fit - h*) e^-t - so whoever else lives there loses room, counted as harm. At most an e-fold a
  year (an atmosphere's mixing time) times mastery; priced per e-fold per Earth-area at what the same land would
  cost enclosed. Giants have no ground to give. Terraform an empty world, then seed it.

## Taking worlds, and holding them (occupation.py)

A world taken by force keeps its people - their biology, staple and genome stay under the new flag. Holding it is a
cost: resistance is what the occupier and occupied do not understand of each other (their minds' channel overlap,
growing over a generation of living together), policing is ~20 per 1000 inhabitants (Quinlivan) x resistance at
what a head of that world produces, paid from its treasury each quarter, and the resisting share withholds its work.
Unpaid policing becomes unrest; unrest that reaches a quarter's whole need throws the occupier out, and the world
is its people's own again. Orbital assaults fire their expected volleys and ground invasions resolve by Lanchester's
square law - no dice in either.

## The human at genesis: from TradeWars console to a people's steward

A primordial start changes what the player *is*. There is no ship to fly for the first two decades - so the human
begins as the **steward of one people on its homeworld**, and the TradeWars console is something that people earns.

**Choosing a people.** The player picks one of the founding peoples (or rolls one). The choice is a difficulty
setting made of physics: the homeworld's light, gravity and crust (what elements it can ever dig - chemistry.py),
its metabolism and staple, its genome (birth strategy, tolerance), its minds' temperature (deep and slow, or quick
and noisy). Nothing is balanced; everything is legible.

**Age 1 - the homeworld (years 0 to ~15-20).** Seasons are the turn. The steward decides what the council would
otherwise decide, with the same numbers in front of them:
* works: raise the citadel, dig habitats, build a nursery (the room each buys, its cost);
* research focus (energy for drives and folding, information for minds, biology for food, materials for crust);
* population policy (expand, or live within the world), taxation, defence;
* the world's own physics shows its limits: famine, blight, the elements its crust withholds.
Most seasons need no decision; the clock runs until something does (a "wake me when" rhythm: works finished,
famine, yards ready). Headless, this age passes in seconds; with a human it is a short city-builder prologue.

**Age 2 - first flight.** When the yards are raised and the council commissions the first hull, the player's people
founds its first dock and the player becomes its **first captain**: the TradeWars console opens - but the player
is not a free trader from nowhere; they fly for their own world, whose surplus is their first cargo and whose
shortfalls are their first contracts. The homeworld stays theirs to steward.

**Age 3 - contact and the frontier.** Ships make contact; the charted universe grows as the player's people (and
everyone else's) look further. Firms, waystations, daughter worlds and realms appear; the player can found them.

**Age 4 - hierarchy.** Neighbours begin to prey and to protect. The steward accepts or refuses protection, offers
it to weaker peoples, pays or collects tribute - the same contracts the AI peoples make, judged by the same rule.
An empire is what a player's contracts add up to; so is a ruined people.

**What this needs in the kernel (not yet built):**
1. a steward registration: a human bound to a people's homeworld with no ship (today `register_player` issues a
   ship at Sol);
2. steward commands for the council's choices (citadel/habitat/nursery already exist as owner commands; research
   focus and population policy exist; *commission ship* and *offer/accept protection* do not);
3. a "wake me when" clock for the homeworld age;
4. multiplayer: several humans are several peoples - their first contact may be decades in;
5. the settled genesis remains the mode for players who want the console from the first minute.
