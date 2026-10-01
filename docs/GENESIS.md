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
