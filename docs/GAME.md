# Xylarium: The Barren Realms - the game

Xylarium is a text 4X space game in the lineage of TradeWars 2002, Barren Realms Elite and Solar Realms Elite,
built on a simulation kernel in which the universe runs whether or not anyone is playing. Its rules are physics
and bookkeeping: stars and orbits are exact, food becomes people, money and matter are conserved, and every
outcome - who is rich, which realm holds which star, which peoples reach the sky - is emergent. Human players and
autonomous AI captains live in the same universe under the same rules.

This document describes the game as it is. `docs/STANDARDS.md` describes how it is built.

---

## 1. Ways to play

There is no single way to win; there are careers, and a player can mix them. Type `?` (the **ADVISOR**) at any
prompt to see what is worth doing where you stand - trade runs from this port, contracts and VIP charters you can
sign here, what your fuel cell reckoning prefers, your worlds' alarms, who governs this system - and take any of
it by number. The main prompt shows its best opportunity as a hint line every turn.

| Career | What you do | Where to start |
|---|---|---|
| **Trader** | Buy low, sell high along the lanes; haul freight contracts; carry luxuries to worlds that crave them | `TRADE`, `FREIGHT_ACCEPT` |
| **Industrialist** | Mine asteroid belts, fabricate, found and run companies, float them on the ISSE | `MINE_ASTEROIDS`, `COMPANY_IPO` |
| **Financier** | Trade stocks, short, arbitrage the currency exchanges, lend and borrow on margin | `STOCK_*`, `FX_EXCHANGE` |
| **Colonist / Governor** | Claim worlds, raise citadels, set population and natal policy, grow a house into a realm | `PLANET_CLAIM`, `POPULATION_POLICY` |
| **Politician** | Campaign for the Senate, lobby the Compact, hold a budget office, set budgets and direct grants | `SENATE_*`, `LOBBY_CONTRIBUTE`, `BUDGET_SET` |
| **Shipwright** | Design ships on the workbench and earn royalties whenever others build them | `SHIP_DESIGN` |
| **Tourism magnate** | Build commercial orbital stations; fly VIP charters in liners designed for their guests | `STATION_BUILD`, `CHARTER_ACCEPT` |
| **Explorer / Scholar** | Chart the frontier, solve cartographic puzzles, investigate anomalies, excavate ruins, meet natives | `SCAN_SPACE`, `CARTOGRAPHY_*`, `EXCAVATE`, `NATIVE_INTERACT` |
| **Warlord / Outlaw** | Piracy, covert operations, planetary assault - at the risk of the law, bounties and your own hull | `ATTACK_*`, `COVERT_OP` |

Every captain has a **lineage** (clade and species - biotic, lithic, plasmic, cryogenic, and more), a **rank**
that unlocks hulls and authority, **experience** in domains (commerce, industry, science, navigation, combat), a
**cosmic alignment** from Light to Dark shaped by deeds, and **turns** that actions spend.

---

## 2. The universe

### Stars, orbits and worlds (`physics.py`)
Each star system has a star whose mass sets its luminosity (L = m^7). Planets sit on exact orbits (a = q^2 AU,
spaced so orbits never cross - a law), with Kepler periods, axial tilt, tidal locking, and the flux they receive.
One standard year is 100 cycles; a fiscal quarter (a season) is 25 cycles. World types - terrestrial, oceanic, ice,
volcanic, barren, gas giant, rogue - follow from flux and size.

### Geology (`geology.py`)
Crusts hold finite ore, renewed slowly by tectonic heat; airless worlds gather helium-3 from the stellar wind;
volatiles escape light worlds and outgas from active ones; uranium decays on its half-life; mining leaves tailings
that weigh on a world's living space.

### The warp graph and null space (`universe.py`, `nullspace.py`, `fibres.py`)
Sectors are joined by warp lanes. Star systems are separated by null space, where asteroid belts, gas pockets and
wreck debris drift. Lanes develop with traffic (the galaxy's "fibres"): busy trunks become cheaper to travel,
routes follow geodesics, and violent events leave curvature that relaxes over seasons.

### The frontier (`populace.py`, `research.py`)
The galaxy grows. New star clusters are charted at the edge when the peoples run out of room, when explorers cross
the frontier, and as more human players join (each human beyond the base company is owed ten systems of frontier
and brings two more AI captains). New clusters attach with new sectors and lanes; existing systems never move.
Each new cluster arrives peopled: native societies, the most advanced of them already spacefaring.

---

## 3. Peoples

### Biosphere (`biosphere.py`)
Each metabolism has a light it evolved under. A world's **carrying capacity** follows from its area, surface
chemistry, light fit and growing season, times agricultural technology (citadel tier), plus enclosed habitats. A
people grows logistically toward it, never faster than its farms can feed the newcomers.

### Staples (`staples.py`)
Every people eats its own **staple**: carbon life eats organics, lithotrophs graze ore out of the crust, the
Stillcold drink ice, plasmic life feeds on hydrogen. Food is counted in energy-equivalent units (a thousand people
need the same number of units of their own staple), and real output values every harvest as food at the price of
organics. A world's staple is kept where that commodity lives - the granary, the ore silo, or the element reserves -
so a lithic people's meals and works draw on the same ore, and a plasmic world's food is the hydrogen a refuelling
captain would buy. Famine, rationing, household groceries, import orders, nurseries' reserves, settler kits, raids,
sabotage and famine aid are all in the people's own staple: grain is no relief to a people that drinks ice.

### Sustenance (`sustenance.py`)
Each quarter every world's harvest is read against its need and smoothed into a year's **self-sufficiency**.
A world short of it whose stores would run out within four quarters is hungry, and its state says what it can do:

| State | Meaning | What follows |
|---|---|---|
| secure | it feeds itself | - |
| importer | it does not, but stores and markets carry it | imports its staple |
| expanding | hungry, with yards and open worlds in reach it could eat on | an **exodus** fleet sails, even before the people is otherwise viable |
| pressed | hungry, with yards and nowhere open to go | its council **raids** the richest holder of its staple in reach - a world's stores or a starport (a hydration port, a fuel dock) |
| stranded | hungry, without yards | it can only raid its own system |

A raid is won with the odds of strength (garrison and fighters, or a port's law), both sides bleed, and the first
raid between two peoples opens a **food war** in the chronicle (the Water War of ..., the Hydrogen War of ...),
which ends after eight quarters without one. Necessity still darkens the raider (its civilization's alignment, or
its owner's `food_raid` deed); each pressed quarter hardens a people further. Abundance shared lightens: luminous
peoples with a surplus of the same staple send relief to hungry worlds in reach, and giver and receiver both move
toward the Light. AI colonists read the land as farmers do - they settle the world that would feed the most of
their own people - and ration and relieve their colonies in their staple. Players see the gauge on `POPULATION`
and `PEOPLES`, and choose for themselves (`World # RAID`); their worlds never raid alone.

### Knowledge and minds (`knowledge.py`, `laws.py`, `decide.py`)
There is no tech tree. Each people holds knowledge in four domains - energy, materials, biology, information - in
knowledge units (a thousand minds' year of free thought). A world adds to it each quarter: its people x the labour
its harvest frees (1 - 1/self-sufficiency) x leisure (1 + luxury access) x the **depth** of its minds, directed at
its own troubles (hunger and failing births to biology, a mined-out crust to materials, a degraded grid to energy,
trade to information) over a floor of curiosity, plus its rulers' focus (`RESEARCH <domain>`). Its own society can stand in the way - **impedance**, the product
of dogma (thought falls to nothing as dogma reaches the zealots' threshold), conflict (1 / (1 + wars + siege))
and dark alignment (down to half at -1) - and the Imperium halves it. Every stock depreciates 15% a year. Relics teach materials, anomalies their precursors'
domain, watching natives biology.

A capability is a process mastered along **Wright's learning curve** (cost x 0.8 for each doubling of
experience): the jump drive (a fold costs 250 / mastery), nanite repair, bio-synthesis, alchemy's recipes, every
nursery. Nothing unlocks; things become worth having.

Minds follow their substrate's temperature (radiative equilibrium at the light the people evolved under; plasma
for plasmic life): depth ~ 1/sqrt(T) (Landauer's cost per bit over kinetic energy cycling), reaction speed and
judgement noise ~ sqrt(T). Cold peoples think deep and slow, hot ones quick and noisy. Every agent that chooses -
councils, AI captains, liquidity providers - uses one **decision rule**: the option worth most over its cost, worth
discounted at its money's policy rate over a planning horizon that shrinks with its mind's noise, judged with an
error that grows with it.

### Fluid intelligence and crystals (`crystal.py`, `intellect.py`)
Knowledge is what a people has stored; **fluid intelligence** is what it can do with a problem it has never seen,
measured the way netstratum's proof of useful work measures it. Each quarter, from the settlement chain's last seal,
a task is forged for every people at every rung of two ladders - planar and volumetric (the "in and out" axis),
mirroring netstratum's: a word over the transformation vocabulary (rotations, flips, transpose, recolour; stack
flips and cycles for volumes), applied to forged grids.

There is no search. Every word is a point on a lattice - (stack element, frame element in D4, colour map) - and
reduces to that normal form whatever its length. Solving is **decompaction**: the coordinate is read off the
training pairs by canonical frames and cell alignment, and the people writes it as its address in its own chart -
the table of shortest words over the **crystals** (generators) it holds. A people without a mirror cannot express a
reflection however hard it thinks; one with a richer vocabulary writes shorter programs. It climbs until a coordinate
lies outside its chart or the work (cells x (frame orbit + address)) exceeds its thought this quarter. Every claim
carries its program and a hash-chained certificate that anyone can verify by replay.

A people's gauge is the rung it reaches on each ladder. Solved tasks mint knowledge (difficulty x scarcity); fluid
intelligence carries it further along every learning curve and steadies its decisions (less noise, longer horizons).
Crystals are learned: every mind starts with the quarter turn; reflections come with knowledge of information,
recolouring with biology, the stack operators with energy; a composite written three times becomes one crystal
(abstraction); neighbours teach the less knowing; relics carry their makers' crystals; peoples forget what few of
their worlds hold, less where households have leisure to teach.

**The fourth axis.** A third ladder runs over 4-volumes: hyper flips and cycles act on the order of whole volumes
(a dihedral group of its own), and stack operators can be applied to every volume at once. Peoples think first in
the dimensions they were born into - those of gas giants and oceans find the stack twice as readily, surface-dwellers
the mirror - and no people can conceive, be taught, or read from a relic a hyper operator before it holds both
stack operators; discovering one takes mastery of energy *and* information. Folding space (`JUMP`) needs a hyper
crystal in its people's vocabulary: without one the fold cannot be written, however rich the captain.

### Chemistry (`chemistry.py`)
There is one periodic table for the universe - real elements with their mass, density, condensation temperature,
cosmic abundance and place (period and group), plus the netstratum exotics placed by their own axes. Every world
holds what its formation let it keep, and records why it lacks the rest: elements its star's lineage **never made**
(the ladder of nucleosynthesis climbs with stellar mass - brown dwarfs stop at period 3, remnants reach 7), those
that **escaped** (too light for its gravity at its temperature), those too volatile to condense (**too hot**), and
heavy ones **sunk** into the core (gas giants keep their metals out of reach). Surveyed deposits are declared to
the matter ledger.

No people starts with the table. Each digs into what its own crust holds - thought x mastery of materials at the
element's depth (its period), easier beside an element of the same group already known - and the table it uncovers
is its homeworld's. A recipe (a firm's or an alchemist's) can be made only by a
people that knows every element in it and can hold enough parts at once: two, plus one for every three planar rungs
of its fluid intelligence. What a world lacks must be found elsewhere - and that is what makes trade routes.

### Genomes (`genome.py`)
Every peopled world carries its deme's genome on six heritable axes - light (its tuned optimum), tolerance (how
wide, at the cost of peak height), chemistry (adaptation to its world's surface), birth, temperature (its minds'
substrate) and aptitude (how well it keeps what it learns). Each quarter selection moves it by Lande's equation
(additive variance x the gradient of log fitness read from the world's own physics; r-selection where land is open,
K-selection near what it can carry) and drift jostles it by 1/sqrt(people). Daughter worlds inherit their parent's
genome and adapt to their own light; a world that drifts three additive deviations from its people's mean becomes
another people (a new civilization inheriting knowledge and crystals, or a colony strain). Evolution is slow -
a generation is a third of a century - but a people that has mastered genome editing (biology) may move toward
what its world rewards (the optimum is computed, not searched) when the room it would gain is worth the cost
(`POPULATION` -> `World # EDIT`).

### Introspection, creativity and integrity (`introspect.py`)
Each year every people reads eight gauges - sustenance, vitality, knowledge, intellect, creativity, prosperity,
peace, integrity - weighs them by aspirations that come from its own character (its alignment, its minds, what it
has gone without), and pursues its widest gap with the lever it holds: its rulers' inquiry, restraint from raids,
guarding its art. Whether its goal is reached is **purpose**, a prospect in meaning. **Creativity** is defined by
speciation - novelty that lives: new species of its worlds, crystals no other people knows, luxury signatures
unique to it and its own. **Integrity** is the share of its worlds still crafting the signature their own world
gave them; peoples that value it demand a greater market premium before selling out.

### Enterprise (`enterprise.py`)
Laid over the listed companies, the ISSE and their dividends, **process firms** run the economy's own recipes
(equipment, superconductors, biosphere packs, engine manifolds, warp cores) at their home port: they buy inputs
from their own world's surplus first and the port second, burn a unit of their world's fuel a batch, pay wages
into their world's households, make in lots - stopping when the next lot no longer pays or the port cannot pay for
it - and sell back. Materials knowledge cuts their waste. A council founds one where a quarter's profit on the
plant, as its mind discounts it at the policy rate, beats the plant's cost - sized to its share of the market;
profitable firms reinvest; firms short of inputs post import orders for captains to haul. Four losing quarters
and a firm goes into **receivership**: its orders are cancelled, its plant auctioned to a rival or scrapped, its
cash paid to its shareholders, and it is struck from the exchange - every unit of money moved, none lost.

### Fertility (`fertility.py`)
How many children a people wants depends on its biology:
- **r-strategists** (mycotiforms, hexasocial swarms, hypobiotids): stored food becomes clutches - they boom.
- **K-strategists** (bimaniform Terrans, ailuroforms): security brings replacement; luxury and crowding compress
  fertility below it (the demographic transition), so rich worlds settle below what their land could carry.
- **Lithic** peoples bud from structural metal and tectonic heat; **cryocoherent** peoples fission in the cold and
  are chilled out of it by warmth and wealth; **plasmic** peoples follow their star's flares.
Famine, bombardment and plague cut every people's fertility to a quarter (a law). Dogma multiplies it. Councils and
players play **natal cards**: the Edict of Propagation, the Ascetic Mandate, and the Pyre's Sacred Hatching.

**Meaning** (mu, 0.5 .. 2.0) is a people's momentum against the satiation of comfort, read from its state:
mu = (1 + prospects + catch-up) x (1 - satiation / 2), where prospects are the mean of *room* (the open land in its
reach it could eat on, as a share of all the land in reach) and *progress* (tanh of a generation times its
knowledge's annual growth rate); *catch-up* makes up births a crisis deferred, at up to twice the natural rate; and
*satiation* is comfort with nothing ahead (luxury access x (1 - prospects)). It weighs on births as much as they are
a choice: fully for K peoples, half for the Stillcold, a quarter for lithic and plasmic peoples, not at all for r
clutches.

### Nurseries and blight (`nursery.py`)
Each strategy has a technological leap past its biology - a district built like a habitat. Nothing gates it: it
lifts the people's biology as far as their **mastery** of the process (knowledge.py), and its price and inputs fall
along the same learning curve:

| Strategy | Nursery | What it lifts | Fed each quarter with |
|---|---|---|---|
| K | Fertility Centre (artificial gestation, biology) | the luxury and crowding compression, by mastery | organics |
| Lithic | Foundry Nursery (foundry budding, materials) | metal to bud from, and heat for tectonics | Fe / Ti, or ore at 10:1 |
| Cryo | Deep-Cold Vault (deep refrigeration, energy) | cold, and wealth's warmth | water ice, or the world's fuel |
| Plasmic | Confinement Ring (magnetic confinement, energy) | a star and a well of its own | H / He-3, or the world's fuel |
| r | Sanitation Works (sanitation, biology) | blight transmission, by mastery | equipment, or ore |

A nursery buys its inputs from the world's holdings or its contractor port. Unfed for a quarter it goes dark and
its brood is lost (a quarter's births): high-tech fertility is only as sound as the supply chain behind it.
Councils build theirs by the decision rule (decide.py) when the people it lets the world sustain - or, for r
peoples, the blight deaths it averts - are worth more at their tax value than its price and upkeep; players use
`POPULATION` then `World # NURSERY`.

r peoples breed freely; their ceiling is **blight**. Density sets a pathogen's reproduction number,
R0 = (P/K) / 0.85. Each quarter an introduction takes off with chance 1 - 1/R0, infects the share z solving
z = 1 - exp(-R0 z), kills a tenth of the infected and rots z/2 of the granary.

### Demography (`demography.py`)
Crowded worlds build: citadels (which are also the yards that build settler ships) and sub-surface habitats.
Past the inflection of its growth, a people with yards chooses (once it is **viable** - fertility at least 1.05 for
eight straight quarters; a dying people sends no fleets): **expand** (settler fleets found daughter worlds)
or **enough** (population controls, stewardship, the Covenant of Enough). A settler fleet's reach is its yards'
range times the square root of its fuel cell's exhaust velocity; a fleet that finds no world to feed it in the
open raises domes (enclosed habitats - bigger yards carry bigger kits) on any solid world. Each fleet carries its
clade's **seeding kit** (food for biotic settlers, structural metal for lithic ones, ice or fuel for the Stillcold
and plasmic), and sails no larger than its kit can stock. Worlds crowded for
long divert part of their tax to a diaspora escrow that funds expeditions. Households buy a basket of goods from the
regional starports and export their surplus harvest and ore.

### Luxury and tourism (`luxury.py`, `tourism.py`)
Provided-for worlds craft a **signature luxury** from what they hold - stimulants, resonant artifacts, perishable
exotic ephemera, precursor curios - named for their people and world ("Neth Flarelight Nectar"). Nobody craves
what they make: demand is inverse to local availability, so luxuries travel. Workshops craft to order.
Spacefaring households travel: mass tourism flows along the lanes to **pleasure domes** and **commercial orbital
stations**, steered by novelty, safety, distance and exchange rates, burning the carriers' hydrogen. Rich worlds
post **VIP charters** that captains fly; the fare depends on how well the ship's decks suit the guests' biology,
and a pirate who takes a liner holds its VIPs for ransom.

### Natives (`natives.py`, `archaeology.py`)
Pre-spacefaring societies advance through ages. The galactic **policy deck** (non-interference, observation,
protectorate, exploitation, missionary conversion) governs what captains may lawfully do with them. They can be
protected, traded with, uplifted, exploited - or take first flight on their own. Dead civilizations leave ruins
to excavate.

---

## 4. Money and markets

### Currencies and the exchanges (`fx.py`, `banking.py`, `ledger.py`)
Four currencies - SOL (the Federation), FRN (the Frontier), THR (the Imperium), VOID (the Deep Void) - trade
through constant-product exchange pools and the Galactic ISSE cross pairs. Nobody holds the pools at a target:
what they hold is what traders and liquidity providers leave in them, and each exchange prices its own swaps at
what makes providing its liquidity break even (fee yield = the bank rate + sigma^2/8), between its cost and the
point where traders route around it.

### Monetary regimes (`regimes.py`) - the polities choose; we are agnostic
Each currency's polity runs the regime it chooses: a **central bank** (a discretionary rate, deposit interest,
credit, public works and the output-tracking authority), an **algorithmic** rule (the authority alone, a fixed
rate), a **reserve** board (money as a claim on its ports' main commodity at par, issued and retired as ports
arbitrage against it), or **free** money (nobody steers) - and may impose capital controls. Each year a governor
weighs its regime against the others by what holding each has earned its holders (expected log growth, pooled
across the universe; untried ways expected to do as money typically does), moving only when the gain clears the
comparison's standard error. Nothing labels a path right: money grown beyond what output needs is measured as harm
to the governor, against what its non-exiting holders held (controls make captains non-exiting); restoring it is
help. A failing money may be helped: luminous neighbours holding SOL lend it, the borrower buys its money back and
repays when it recovers.

Regional central banks pay their policy rate on the balances captains hold in their money (from reserves above
their floor), and captains convert regional money to SOL only as far as that rate fails to cover its expected
depreciation (uncovered interest parity, judged with each mind's noise). Anyone holding both sides of a pool - AI
captains and companies - may **provide liquidity** for a share of its fees when its fee yield beats the bank rate
plus its impermanent loss (about sigma^2/8 a quarter) (`liquidity.py`).

### Monetary policy: M V = P Y
Each currency's authority measures money's velocity at genesis and steers the supply toward what real output
needs, closing a quarter of the gap each season. Colony earnings are split between households' purses and
government taxes; public services withdraw what the authority sets. Every mint and burn is declared.

### Ports, prices and goods (`economy.py`, `market.py`)
Starports buy and sell by stock level; prices carry a regional price level and a remoteness gradient. Ports
fabricate from held inputs (fabrication leaves slag, recycled into ore and tailings), restock what they need,
and pay their regions' households. Commodities include ore, organics, equipment, water, hydrogen, helium-3, the
periodic elements, exotic minerals, manufactured components (superconductors, biosphere packs, engine manifolds,
warp cores) and the four luxuries.

### Waystations (`waystations.py`)
Genesis gave most systems a starport; from then on ports are founded by the economy. Every arrival is counted
where it lands. Each year, for every portless system with traffic, the worth of a dock is measured off the docks
that exist (the median retail income per visit) times the traffic it would serve. A council of a peopled world
there, or an AI captain passing through, founds one when that worth, discounted by its own mind at its money's
policy rate, beats the dock's cost. The founder's capital becomes the dock's treasury; its shelves open empty and
fill with what passing captains sell it; half its treasury's growth beyond that capital is paid to the founder each
year. Busier lanes draw more docks, and docks sharing traffic share income - the value of a visit falls as they
multiply.

### Companies, freight and credit (`market.py`, `credit.py`)
Worlds and captains found companies that post freight contracts (escrowed), pay dividends in their home money and
list on the ISSE (buy, sell, short, take over, poison pills, proxy fights). Captains borrow on margin against
their portfolios; defaults are filed at law.

---

## 5. Polity

### Governments and the two engines (`government.py`)
**Starports are government property** - one per star system, bound to its host world and run by the system's
government. **Commercial orbital stations are private property**, built by investors, paying commercial tax. So
money runs through two engines: the public purse (starport dues, commercial tax, membership dues, court fines)
and private commerce (owners' receipts). Each season every government's budget office spends part of its
treasury - on grants, endowment, security (which raises the law's presence) and infrastructure - divided by its
alignment, or by hand if a player holds the office.

### Realms (`realms.py`)
A **realm** is a polity: a capital world, member worlds and claimed star systems, governed from its capital.
Claims follow influence (population over the lanes, falling with the square of distance); a realm always holds
its own worlds' systems; contested borders are counted. The baseline board is born partitioned into realms with
historical borders; on a fresh board realms emerge - a people when it takes to space, a captain's house when it
holds worlds in two systems. Far, unhappy worlds secede and found their own realms.

### The great powers and authorities (`factions.py`, `governance.py`)
- **The Terran Federation** (the core): the Senate elects offices (Chancellor, Fleet Admiral, Master of Coin,
  High Inquisitor) who issue edicts; the Master of Coin holds its budget office.
- **The Frontier Compact** (the borderlands): a confederation; its members' stardocks pay it membership dues; its
  budget office goes to its top lobbyist.
- **The Aurelian Imperium**: a settled heartland (domed outposts on hostile worlds), tithes hauled to its Fortress
  World, techno-heresy, secession of unhappy worlds.
- **The Choir of the Pyre**: zealots whose dogma grows, who purge and crusade and convert.
- **The Deep Void**: no authority; syndicate free ports.

### Law and crime (`law.py`, `crime.py`)
Each jurisdiction's courts see crimes with the probability of the law's presence (warrants, operatives, garrisons,
fleets, security budgets). Convictions recall restitution and double damages from the offender's wallets across
currencies (the Deep Void refuses foreign courts), seize shares, post warrants and bounties, and freeze trade.
Who commits crime is a matter of **pedigree** (a heritable criminal streak per house, with variance per member),
temperament (risk and caution) and conscience: the Light never profits by crime, and the grey middle only with a
strong streak where no law reaches. Piracy weighs the risk to the pirate's own hull.

---

## 6. Ships

### Hulls and the workbench (`shipdesign.py`)
Stock hulls are sold at the yards. Anyone may **design** a ship: a frame (corvette to leviathan) filled with
modules - holds, tanks, drives, reactors, shields, armour, fighter bays, mining lasers, berths and leisure decks
built for a biology (a water spa comforts biotic guests, a plasma bath plasmic ones). Designs must fit the frame's
volume and power budget; mass is what the drive burns fuel to move. A design is built from yard materials, and
whoever builds another's design pays its designer a royalty.

### Propulsion and fuel cells (`propulsion.py`)
A jump burns reaction mass in proportion to the mass moved, divided by the drive's exhaust velocity. Fuel cells:
hydrogen torch, hydrocarbon cell, nuclear-thermal steam, helium-3 fusion, xenon ion (slow), fission pulse, and
the warp stabilizer (no propellant; its core wears out). Which cell a people builds is chosen from what is abundant
in reach against what its biology has always burned, weighted by how clear-sighted (aligned) it is - so misaligned
peoples can build themselves into fuel bottlenecks, and learn out of them by running dry. Gas giants are hydrogen
wells skimmed by the starports in their systems. A world that cannot fuel its defences raises a **DEGRADED**
beacon and is easier to conquer. Hydrogen exhaust drifts in the sector and can be scooped.

### Combat (`combat.py`, `surface.py`)
Ship battles (volleys, evasion, bribes), orbital bombardment and sieges, ground invasion through planetary
district grids. Destroyed hulls leave debris; captains are re-decanted from clone vats if their house keeps them.

---

## 7. The AI

Autonomous captains think with a cognitive loop (`cognition.py`): they observe ports, remember what paid, weigh
plans by temperament (thrift, ambition, caution, risk, horizon, spend) and calling, and act through the same
commands as players. NPC **houses** (`lineage.py`) found dynasties, grow clones, split cadet branches and die out.
Civilizations run their own councils, research and civic works. Great powers run fleets, tithes and crusades.
The AI balances the human company: more humans bring more AI and more frontier.

---

## 8. The record

The **chronicle** (`chronicle.py`) writes the galaxy's history as it happens - captains' logs, planetary annals,
field notes on natives, faction decrees, the founding and fall of realms and houses, galactic histories each age -
into a Library players can browse and add to.

---

## 9. Laws of the universe, and how we check them

`simulate_playtest.py` runs the universe with a company of autopilot players and reports, per run:
- **Laws** (must hold): money conserved per currency (every change declared), matter conserved per commodity,
  monetary churn, the quantity equation M/M* in band, throughput per sector, the clearing union's STAMP balance,
  the settlement chain's integrity, central banks' solvency, the docket's balance, orbits never crossing,
  fertility collapsing under stress, invariant checks, no exceptions, determinism across processes.
- **Observations** (bands of interest): exchange-rate drift, illiquid ports, wealth inequality, alignment balance,
  native survival, crime detection, population growth, daughter-world dispersion, tourism's share of income,
  fertility by strategy, realms and claims, and more.

Run it:

```bash
python3 simulate_playtest.py --cycles 10000 --seed 7
python3 -m unittest discover -s tests
```

**The living universe** (`tools/live.py`) runs seeds continuously instead: it checks money and matter conservation
every quarter (the one hard law), saves a snapshot and appends an observation line every 500 cycles, and stops with
a crash dump when a law breaks. A code change takes effect by restarting it: the universe resumes from its last
snapshot and keeps living through the upgrade.

```bash
python3 tools/live.py --seed 7            # run or resume (runs/seed7/)
python3 tools/live.py --seed 7 --show 10  # the last observations
```

`XYL_AUDIT=1` (optionally `XYL_AUDIT_FROM=<cycle>`) makes the harness name the exact action, AI turn or seasonal
hook that creates or destroys undeclared money or matter. Three of the harness's autopilot captains play careers on
top of making a living (a politician, a shipwright and a tourism magnate), so those paths are played every run.

---

## 10. Commands

Every command is dispatched through `GameKernel.dispatch(captain_id, ActionType.X, **kwargs)`; the terminal client,
the Telnet and WebSocket bridges and the AI all use it. The main groups:

- **Movement and scanning:** `MOVE`, `JUMP_WARP`, `SCAN`, `SCAN_SPACE`, `OPTIMIZE_ROUTES`, `REST`
- **Trade:** `TRADE`, `FX_EXCHANGE`, `FREIGHT_ACCEPT`, `FREIGHT_DELIVER`, `SHORE_LEAVE`
- **Ships:** `SHIPYARD_PURCHASE`, `SHIP_DESIGN`, `DRIVE_REFIT`, `FLEET_ASSIGN_ESCORT`, `FLEET_RECALL`
- **Worlds:** `PLANET_CLAIM`, `PLANET_INVEST`, `PLANET_TAX`, `PLANET_BUILD_SHIELD`, `PLANET_RECRUIT_FIGHTERS`,
  `PLANET_UPGRADE_CITADEL`, `PLANET_CARGO_TRANSFER`, `PLANET_ELEMENT_TRANSFER`, `PLANET_CIVIC_CONTRIBUTE`,
  `SET_TARIFF`, `POPULATION_POLICY` (with `natal=`), `SURFACE_BUILD_DISTRICT`, `SURFACE_DEMOLISH_DISTRICT`,
  `STATION_BUILD`, `CHARTER_ACCEPT`
- **Industry and space:** `MINE_ASTEROIDS`, `SALVAGE_DEBRIS`, `DEPLOY_SENTRIES`, `RECALL_SENTRIES`,
  `HAULER_COMMISSION`, `HAULER_ASSIGN_ROUTE`, `HAULER_DECOMMISSION`, `ALCHEMY_TRANSMUTE`
- **Markets and companies:** `STOCK_BUY`, `STOCK_SELL`, `STOCK_SHORT`, `STOCK_COVER`, `COMPANY_IPO`,
  `CORPORATE_TAKEOVER`, `BOARD_VOTE`, `POISON_PILL`, `PROXY_FIGHT`, `EXECUTIVE_HIRE`, `EXECUTIVE_MOVE`,
  `MARKETING_CAMPAIGN`, `VC_APPLY`, `VC_REPAY`, `BANK_TRANSACTION`
- **Polity:** `SENATE_CAMPAIGN`, `SENATE_VOTE`, `SENATE_ENACT_EDICT`, `LOBBY_CONTRIBUTE`, `COUNCIL_VOTE`,
  `BUDGET_SET`, `GOVERNMENT_GRANT`, `IDEOLOGY_TREATY_PROPOSE`, `IDEOLOGY_TREATY_SIGN`, `IDEOLOGY_AID_DISPATCH`
- **Conflict and intrigue:** `ATTACK_SHIP`, `ATTACK_PLANET`, `TACTICAL_COMBAT`, `SURFACE_INVADE`,
  `SURFACE_RECRUIT_TROOPS`, `COVERT_OP`, `RECRUIT_OPERATIVES`, `STATION_SECURITY`
- **Exploration and knowledge:** `ANOMALY_INVESTIGATE`, `RESEARCH_SELECT`, `CARTOGRAPHY_*`, `TOLL_GATE_*`,
  `SURVEY_PROBE_*`, `SURVEY_RUINS`, `EXCAVATE`, `SELL_ARTIFACT`, `STUDY_ARTIFACT`, `NATIVE_INTERACT`
- **Self and lineage:** `RANK_PROMOTE`, `PHYLOGENY_ASCEND`, `CANOPY_OVERRIDE`, `COGNITIVE_AUTOMATE`,
  `RETIRE_LINEAGE`, `LIBRARY_BROWSE`, `CHRONICLE_WRITE`, `RADIO_BROADCAST`, `EMPIRE_OVERVIEW`

The terminal client's screens for the newer systems (`xylarium/client/screens.py`): `?`/`ADVISOR`, `REALMS`
(government, budget offices, realms and their claims; set budgets and direct grants), `WORKBENCH` (frames and
modules, draft by role for a guest biology or lay out by hand, register, build), `DRIVE` (fuel cells, what is
abundant here, what your people's tradition burns, refit), `STATION` / `CHARTER` (stations over this system's
worlds, VIP charters posted here), `POPULATION` (growth policy, natal cards, nurseries and raids, with each
world's fertility, staple and sustenance) and `PEOPLES` (the known peoples by what they eat, and the food wars).
