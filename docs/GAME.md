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

### Fertility (`fertility.py`)
How many children a people wants depends on its biology:
- **r-strategists** (mycotiforms, hexasocial swarms, hypobiotids): stored food becomes clutches - they boom.
- **K-strategists** (bimaniform Terrans, ailuroforms): security brings replacement; luxury and crowding compress
  fertility below it (the demographic transition), so rich worlds settle below what their land could carry.
- **Lithic** peoples bud from structural metal and tectonic heat; **cryocoherent** peoples fission in the cold and
  are chilled out of it by warmth and wealth; **plasmic** peoples follow their star's flares.
Famine and bombardment cut every people's fertility to a quarter (a law). Dogma multiplies it. Councils and
players play **natal cards**: the Edict of Propagation, the Ascetic Mandate, and the Pyre's Sacred Hatching.

### Demography (`demography.py`)
Crowded worlds build: citadels (which are also the yards that build settler ships) and sub-surface habitats.
Past the inflection of its growth, a people with yards chooses: **expand** (settler fleets found daughter worlds)
or **enough** (population controls, stewardship, the Covenant of Enough). A settler fleet's reach is its yards'
range times the square root of its fuel cell's exhaust velocity; a fleet that finds no world to feed it in the
open raises domes (enclosed habitats - bigger yards carry bigger kits) on any solid world. Worlds crowded for
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
through constant-product exchange pools and the Galactic ISSE cross pairs. Each region's central bank lends,
absorbs and runs public works; a clearing union settles between them on a sealed settlement chain.

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
worlds, VIP charters posted here), and `POPULATION` (growth policy and natal cards, with each world's fertility).
