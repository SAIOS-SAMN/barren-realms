"""
Xylarium: demography - peoples grow on their worlds, and then decide what to become.

  * Housing is technology. A world's housing is its citadel's base x how well it suits its people's
    biology x (1 + 25% per sub-surface habitat). When a population presses on its housing the colony
    council builds - first the citadel (which is also the yard that makes settler ships), then habitats -
    paying the region's starport contractors from the vault. Nothing is minted: construction is a transfer.
  * At the engineering ceiling a people chooses. Expansionists send settler fleets to found daughter
    worlds within reach (the multi-planetary drive). Others adopt population controls: they hold their
    numbers below housing, are content for it, and the Light notices (stewardship). AI houses choose by
    temperament and alignment, indigenous civilizations by their own alignment, players by command.
  * Space : people : resources stay in balance. When the charted galaxy runs short of free worlds, or
    settler fleets keep finding nothing in reach, the frontier opens a new star cluster (declared new
    territory: new worlds, belts, ports and their capital).
  * Households are consumers. Every fiscal quarter each populated world buys a basket of goods from its
    regional starports - organics, water, equipment - from their household purse (their share of what the
    colony earns) to the port treasury, goods out of the warehouse; savings beyond need go to the vault.
    Demand drains stock, stock sets prices, prices send captains hauling: the demand side of the loop.
"""

import math
from typing import Any, Dict, List, Optional

from xylarium.kernel import cache, matter, topology

from xylarium.config import (
    CITADEL_CONFIG,
    DAUGHTER_CITADEL_TIER,
    DAUGHTER_COOLDOWN_QUARTERS,
    DAUGHTER_EMIGRANT_SHARE,
    DAUGHTER_EMIGRANTS_MAX,
    DAUGHTER_EMIGRANTS_MIN,
    DAUGHTER_FOUNDING_TIER,
    DAUGHTER_MIN_HABITABILITY,
    DAUGHTER_RADIUS_BY_TIER,
    DAUGHTER_SETTLER_COST,
    DEMOGRAPHY_COUNCIL_RESERVE,
    DEMOGRAPHY_PRESSURE,
    DIASPORA_CROWDED_CYCLES,
    FRONTIER_FREE_WORLDS_RATIO,
    FRONTIER_MAX_CLUSTERS,
    FRONTIER_MIN_INTERVAL,
    FRONTIER_PRESSURE_QUARTERS,
    CITADEL_BUILD_QUARTERS_PER_TIER,
    HABITAT_BUILD_QUARTERS,
    HABITAT_COST,
    HABITAT_ORE,
    HABITATS_MAX_BY_TIER,
    HOUSEHOLD_BASKET,
    HOUSEHOLD_RADIUS,
    HOUSEHOLD_SHORTAGE_MORALE,
    HOUSEHOLD_PURSE_PER_CAPITA,
    LUXURY_WANT_PER_THOUSAND,
    PRICE_LEVEL,
    STEADY_STATE_MORALE,
    STEADY_STATE_SHARE,
)

POLICIES = ("expand", "steady")
SETTLE_PRESSURE = 0.5           # the logistic inflection: past it, growth slows with every newcomer
ELEMENT_RESERVE_KEPT = 100      # refined units of each element a world keeps for its own works


# ---------------------------------------------------------------------- housing
def housing_cap(planet: Any, kernel: Any = None) -> int:
    """How many people the world can feed: its carrying capacity K, derived from physics (biosphere.py)."""
    from xylarium.kernel import biosphere
    return biosphere.carrying_capacity(kernel, planet)


def equilibrium(planet: Any, kernel: Any = None) -> int:
    """Where this people's numbers settle: housing, or less for a people below replacement (fertility.py).
    Crowding is felt against it - a transitioned people looks outward before its land is full."""
    f = float(planet.society.get("fertility", 1.0)) if getattr(planet, "society", None) else 1.0
    return int(housing_cap(planet, kernel) * min(1.0, f))


def growth_ceiling(planet: Any) -> int:
    """Where natural growth stops: housing, or less for a people that has chosen population controls."""
    cap = housing_cap(planet)
    if getattr(planet, "growth_policy", None) == "steady":
        return int(cap * STEADY_STATE_SHARE)
    return cap


def at_engineering_ceiling(planet: Any) -> bool:
    return (planet.citadel_level >= max(CITADEL_CONFIG)
            and getattr(planet, "habitats", 0) >= HABITATS_MAX_BY_TIER.get(planet.citadel_level, 0))


def building(planet: Any) -> bool:
    """A world crowding its housing that can still build (citadel or habitats) and hasn't chosen to hold steady."""
    if getattr(planet, "growth_policy", None) == "steady" or planet.population <= 0:
        return False
    if planet.population < equilibrium(planet) * DEMOGRAPHY_PRESSURE:
        return False
    if getattr(planet, "habitats", 0) < HABITATS_MAX_BY_TIER.get(planet.citadel_level, 0):
        return True
    return planet.citadel_level + 1 in CITADEL_CONFIG and self_governed(planet)


def self_governed(planet: Any, kernel: Any = None) -> bool:
    """AI and indigenous worlds' councils raise their own citadels; players raise theirs."""
    if kernel is None:
        from xylarium.kernel import ledger
        kernel = ledger.active_kernel()
    owner = kernel.captains.get(planet.owner_id) if (kernel is not None and planet.owner_id) else None
    return owner is None or getattr(owner, "is_ai", False)


def governed(planet: Any) -> bool:
    """Worlds with a government that runs a budget: colonies, and indigenous spacefaring civilizations."""
    return planet.population > 0 and (planet.owner_id is not None or getattr(planet, "civilization", None) is not None)


def metabolism_of(kernel: Any, planet: Any) -> str:
    from xylarium.kernel import biosphere
    return biosphere.metabolism_of(kernel, planet)


# ---------------------------------------------------------------------- stats
def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "demography")["stats"]


# ---------------------------------------------------------------------- quarter
def quarter(kernel: Any) -> List[str]:
    """Runs each fiscal quarter: councils build, peoples choose, settlers sail, households shop, the frontier opens."""
    logs: List[str] = []
    st = stats(kernel)
    for sec in list(kernel.sectors.values()):
        for planet in list(sec.planets):
            if not governed(planet) or getattr(planet, "natives", None):
                continue
            log = develop(kernel, planet)
            if log:
                logs.append(log)
    households(kernel)
    exports(kernel)
    log = frontier(kernel)
    if log:
        logs.append(log)
    return logs


def _pay_contractor(kernel: Any, planet: Any, amount: int, from_escrow: bool = False) -> None:
    from xylarium.kernel.colony import ColonyManager
    from xylarium.kernel import ledger
    if from_escrow:
        paid_escrow = min(amount, getattr(planet, "diaspora_escrow", 0))
        paid_treasury = amount - paid_escrow
        planet.diaspora_escrow = getattr(planet, "diaspora_escrow", 0) - paid_escrow
        planet.treasury -= paid_treasury
    else:
        planet.treasury -= amount
    port = ColonyManager._contractor_port(planet, kernel)
    if port is not None:
        port.treasury += amount
    else:
        ledger.burn("colony_construction", amount, planet.currency)


def develop(kernel: Any, planet: Any) -> Optional[str]:
    """The colony council's quarter: build when crowded, choose at the ceiling, act on the choice."""
    st = stats(kernel)
    level = PRICE_LEVEL.get(planet.currency, 1.0)
    reserve = int(DEMOGRAPHY_COUNCIL_RESERVE * level)
    cap = housing_cap(planet)
    policy = getattr(planet, "growth_policy", None)
    is_diaspora = getattr(planet, "crowded_cycles", 0) > DIASPORA_CROWDED_CYCLES

    if policy == "steady":
        planet.morale = min(100, planet.morale + STEADY_STATE_MORALE)
        _stewardship(kernel, planet)
        if not is_diaspora:
            return None
        log = send_settlers(kernel, planet)
        if log:
            return log
        return None
    settled = equilibrium(planet, kernel)
    exodus = planet.society.get("sustenance") == "expanding"       # hungry, with open worlds in reach
    if planet.population < settled * SETTLE_PRESSURE and not exodus:
        return None

    # 0. Past the inflection of its growth (P = half its equilibrium: each newcomer now adds less than the
    #    last), a people with a yard that builds settler ships chooses what it will become - the stars, or
    #    enough. Expansionists sail while they keep building at home.
    if exodus and planet.citadel_level >= DAUGHTER_CITADEL_TIER:
        log = send_settlers(kernel, planet)        # famine is the oldest reason to emigrate
        if log:
            return log
    if planet.citadel_level >= DAUGHTER_CITADEL_TIER or is_diaspora:
        if policy is None:
            policy = planet.growth_policy = choose_policy(kernel, planet)
            if policy == "steady":
                st["steady"] += 1
                _covenant(kernel, planet)
                if not is_diaspora:
                    return f"[DEMOGRAPHY] {planet.name} adopted population controls: it will live within its world."
        if policy == "expand" or is_diaspora:
            log = send_settlers(kernel, planet)
            if log:
                return log
    # Growth drives technology: past the inflection, a people without the yards works toward them;
    # habitats and higher citadels wait until housing itself presses
    toward_yards = planet.citadel_level < DAUGHTER_CITADEL_TIER
    if planet.population < settled * DEMOGRAPHY_PRESSURE and not toward_yards:
        return None

    if kernel.cycle_count < getattr(planet, "works_ready_cycle", 0):
        return None   # the council's crews are still on the last project

    # 1. Technology first: the citadel is both housing and the yard that builds settler ships.
    #    Players upgrade their own citadels; councils of AI and indigenous worlds do it themselves.
    nxt = planet.citadel_level + 1
    if self_governed(planet, kernel) and nxt in CITADEL_CONFIG:
        cfg = CITADEL_CONFIG[nxt]
        cost = int(cfg["upgrade_cost"] * level)
        if planet.treasury >= cost + reserve and planet.ore_silo >= cfg["upgrade_ore"]:
            _pay_contractor(kernel, planet, cost)
            matter.consume(planet, "ore_silo", "ORE", cfg["upgrade_ore"], "construction")
            planet.citadel_level = nxt
            planet.works_ready_cycle = kernel.cycle_count + CITADEL_BUILD_QUARTERS_PER_TIER * nxt * _quarter_len()
            st["citadels"] += 1
            if getattr(kernel, "event_bus", None):
                civ = getattr(planet, "civilization", None)
                who = civ.name if (civ is not None and planet.owner_id is None) else planet.name
                kernel.event_bus.broadcast_radio(sender=planet.name, channel="COMM-1", sector_id=planet.sector_id,
                                                 text=f"CIVIC ASCENT: {who} on {planet.name} has raised its Citadel to "
                                                      f"Tier {nxt} ({cfg['name']}) to house a growing people.")
            return f"[DEMOGRAPHY] {planet.name} raised its citadel to Tier {nxt} ({cfg['name']}) to house its people."

    # 2. Dig: sub-surface habitats, up to what the citadel's engineering allows
    if planet.population < settled * DEMOGRAPHY_PRESSURE:
        return None
    if getattr(planet, "habitats", 0) < HABITATS_MAX_BY_TIER.get(planet.citadel_level, 0):
        cost = int(HABITAT_COST * level * (1 + planet.habitats))
        if planet.treasury >= cost + reserve and planet.ore_silo >= HABITAT_ORE:
            _pay_contractor(kernel, planet, cost)
            matter.consume(planet, "ore_silo", "ORE", HABITAT_ORE, "construction")
            planet.habitats += 1
            planet.works_ready_cycle = kernel.cycle_count + HABITAT_BUILD_QUARTERS * _quarter_len()
            st["habitats"] += 1
            return None
        return None   # saving for the next habitat

    return None   # no more room to dig: the choice above is all that is left (players: upgrade the citadel)


def choose_policy(kernel: Any, planet: Any) -> str:
    """Expand to the stars, or live within one world? Temperament and alignment decide - unless the world
    cannot feed its people, and then the stars decide (sustenance.py)."""
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    if owner is not None and not getattr(owner, "is_ai", False):
        return "expand"   # players decide for themselves (POPULATION command); the default is the stars
    if planet.society.get("sustenance") in ("expanding", "pressed"):
        return "expand"   # a people that cannot feed itself on its own world cannot choose enough
    if owner is not None:
        from xylarium.kernel.cognition import temperament
        t = temperament(owner, kernel)
        drive = t.get("ambition", 1.0) * t.get("horizon", 1.0) - t.get("caution", 1.0)
        drive -= 0.6 * getattr(owner, "cosmic_alignment", 0.0)     # the Light leans toward enough
        return "expand" if drive > -0.25 else "steady"
    civ = getattr(planet, "civilization", None)
    align = getattr(civ, "alignment", 0.0) or 0.0
    # Indigenous peoples: a steady, luminous people keeps its world; others reach outward
    seed = sum(ord(ch) for ch in planet.id) % 100 / 100.0
    return "steady" if align + 0.3 * seed > 0.35 else "expand"


def _stewardship(kernel: Any, planet: Any) -> None:
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    if owner is not None:
        from xylarium.kernel import alignment
        alignment.deed(kernel, owner, "stewardship")
    else:
        civ = getattr(planet, "civilization", None)
        if civ is not None and hasattr(civ, "alignment"):
            civ.alignment = round(min(1.0, (civ.alignment or 0.0) + 0.002), 4)


def _covenant(kernel: Any, planet: Any) -> None:
    chron = getattr(kernel, "chronicle", None)
    if chron is None:
        return
    civ = getattr(planet, "civilization", None)
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    people = getattr(civ, "name", None) or (owner.name + "'s colonists" if owner else planet.name)
    chron.record(kernel, "COVENANT", planet.id, people, f"The Covenant of Enough on {planet.name}",
                 f"The people of {planet.name} looked at the sky, and at their children, and chose. They will not "
                 f"send fleets. They will be as many as their world can carry, and no more.",
                 sector_id=planet.sector_id, tags=["demography", "stewardship"],
                 alignment=getattr(civ, "alignment", None) if civ else getattr(owner, "cosmic_alignment", None))


# ---------------------------------------------------------------------- settlers
def free_world(planet: Any) -> bool:
    return (planet.owner_id is None and planet.population <= 0 and not getattr(planet, "natives", None)
            and not getattr(planet, "faction_id", None) and getattr(planet, "civilization", None) is None)


def settler_reach(kernel: Any, planet: Any) -> int:
    """How far a world's settler fleets can sail: the reach its yards allow (citadel tier), stretched by its fuel
    cell - reaction mass per jump falls as 1/v_e, so the same tanks carry a fleet sqrt(v_e) times further in the
    time a voyage allows. A hydrogen torch reaches its yards' range; helium-3 twice it; fission about three times."""
    from xylarium.config import FUEL_CELLS
    from xylarium.kernel import propulsion
    base = DAUGHTER_RADIUS_BY_TIER.get(planet.citadel_level, 6 if planet.citadel_level >= 3 else 3)
    v_e = FUEL_CELLS.get(propulsion.world_fuel(kernel, planet), FUEL_CELLS["H"]).get("v_e") or 1.0
    return max(base, int(round(base * math.sqrt(max(1.0, v_e)))))


def send_settlers(kernel: Any, planet: Any) -> Optional[str]:
    from xylarium.kernel.universe import habitability
    st = stats(kernel)
    quarter_now = kernel.cycle_count // max(1, _quarter_len())
    is_diaspora = getattr(planet, "crowded_cycles", 0) > DIASPORA_CROWDED_CYCLES
    cooldown = 4 if is_diaspora else DAUGHTER_COOLDOWN_QUARTERS
    if quarter_now - getattr(planet, "last_daughter_quarter", -10 ** 6) < cooldown:
        return None
    level = PRICE_LEVEL.get(planet.currency, 1.0)
    cost = int(DAUGHTER_SETTLER_COST * level)
    reserve = int(DEMOGRAPHY_COUNCIL_RESERVE * level)
    escrow = getattr(planet, "diaspora_escrow", 0)
    if escrow >= cost:
        pass
    elif escrow + max(0, planet.treasury - reserve) >= cost:
        pass
    else:
        return None
    from xylarium.kernel import biosphere, nursery, sustenance
    exodus = planet.society.get("sustenance") == "expanding"
    if not nursery.viable(planet) and not exodus:
        nursery.stats(kernel)["gated"] += 1      # a people not sustaining itself does not send fleets
        return None
    metab = metabolism_of(kernel, planet)
    emigrants = min(DAUGHTER_EMIGRANTS_MAX, int(planet.population * DAUGHTER_EMIGRANT_SHARE))
    emigrants = nursery.kit_room(kernel, planet, metab, emigrants)    # no more than its seeding kit can stock
    if emigrants < DAUGHTER_EMIGRANTS_MIN:
        return None
    radius = settler_reach(kernel, planet)
    best = None
    # Settlers take the nearest ring that holds a world to feed them; a diaspora (crowded, escrow-funded)
    # expedition presses on to the full reach of its yards and drives before giving up
    search_radii = sorted({min(radius, DAUGHTER_RADIUS_BY_TIER.get(planet.citadel_level, 3)), radius}) \
        if is_diaspora else [radius]
    # A fleet from a world with yards can carry a dome kit: an enclosed, lit habitat that feeds its people on any
    # solid world whatever its light or chemistry (the habitat physics of biosphere.py). It costs a habitat's price
    # and ore, and a world that can feed settlers in the open is always preferred - it feeds far more of them.
    # bigger yards build bigger kits: a Stronghold's fleet carries one dome, each tier above one more
    kit_domes = max(1, planet.citadel_level - DAUGHTER_CITADEL_TIER + 1)
    dome_cost = int(HABITAT_COST * level)
    can_dome = (planet.citadel_level >= DAUGHTER_CITADEL_TIER and planet.ore_silo >= HABITAT_ORE * kit_domes
                and escrow + max(0, planet.treasury - reserve) >= cost + dome_cost * kit_domes)
    for r in search_radii:
        ring_cands = []
        for sid in topology.reach(kernel, planet.sector_id, r):
            for cand in kernel.sectors[sid].planets:
                if not free_world(cand):
                    continue
                if habitability(metab, cand.planet_type) >= DAUGHTER_MIN_HABITABILITY:
                    k = biosphere.carrying_capacity(kernel, cand, citadel=DAUGHTER_FOUNDING_TIER, habitats=0,
                                                    metabolism=metab)
                    if k >= 2 * DAUGHTER_EMIGRANTS_MIN:
                        ring_cands.append((cand, k, 0))
                        continue
                if can_dome and (cand.planet_type != "GAS_GIANT" or metab == "plasmic"):
                    k = biosphere.carrying_capacity(kernel, cand, citadel=DAUGHTER_FOUNDING_TIER,
                                                    habitats=kit_domes, metabolism=metab)
                    if k >= 2 * DAUGHTER_EMIGRANTS_MIN:
                        ring_cands.append((cand, k, kit_domes))
        if ring_cands:
            best = max(ring_cands, key=lambda c: (c[1], -c[2]))
            break
    if best is None:
        st["no_room"] += 1
        frontier_state(kernel)["pressure"] += 1
        return None
    planet.last_daughter_quarter = quarter_now
    daughter, k_daughter, domes = best
    hab = habitability(metab, daughter.planet_type)
    emigrants = min(emigrants, k_daughter // 2)       # a new world is settled at half what it can feed
    _pay_contractor(kernel, planet, cost + domes * dome_cost, from_escrow=True)
    if domes:
        matter.consume(planet, "ore_silo", "ORE", HABITAT_ORE * domes, "construction")
        daughter.habitats = max(daughter.habitats, domes)
        st["domed_daughters"] = st.get("domed_daughters", 0) + 1
    planet.population -= emigrants
    planet.crowded_cycles = 0
    planet.society["emigrated_cycle"] = kernel.cycle_count
    if exodus:
        sustenance.stats(kernel)["exodus"] += 1
    daughter.society["founded_cycle"] = kernel.cycle_count
    daughter.population = emigrants
    daughter.habitability = hab
    daughter.owner_id = planet.owner_id
    nursery.stock_kit(kernel, planet, daughter, metab, emigrants)  # the clade's seeding kit sails with them
    daughter.morale = max(daughter.morale, 80)
    daughter.growth_policy = None
    if planet.owner_id is None and getattr(planet, "civilization", None) is not None:
        daughter.civilization = planet.civilization          # the same people, now on two worlds
    daughter.metropole_id = planet.id
    daughter.citadel_level = max(daughter.citadel_level, DAUGHTER_FOUNDING_TIER)   # the fleet raises a redoubt
    st["daughters"] += 1
    st["emigrants"] += emigrants
    chron = getattr(kernel, "chronicle", None)
    civ = getattr(planet, "civilization", None)
    people = getattr(civ, "name", None) or planet.name
    if chron is not None:
        chron.record(kernel, "SETTLEMENT", daughter.id, people, f"The Settling of {daughter.name}",
                     f"{emigrants:,} of {planet.name}'s people crossed to {daughter.name} in Sector "
                     f"{daughter.sector_id:03d}. Their world had grown too small for them.",
                     sector_id=daughter.sector_id, tags=["demography", "settlement"])
    if getattr(kernel, "event_bus", None):
        kernel.event_bus.broadcast_radio(sender=planet.name,
                                         text=f"SETTLER FLEET: {emigrants:,} colonists from {planet.name} have founded "
                                              f"a daughter world on {daughter.name} (Sector {daughter.sector_id:03d}).",
                                         channel="COMM-1", sector_id=daughter.sector_id)
    return f"[DEMOGRAPHY] {planet.name} founded daughter world {daughter.name} with {emigrants:,} settlers."


def _quarter_len() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


# ---------------------------------------------------------------------- frontier
def frontier_state(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "demography")["frontier"]


def frontier(kernel: Any) -> Optional[str]:
    """Open a new star cluster when the galaxy's peoples run out of room."""
    st = stats(kernel)
    rm = getattr(kernel, "research_manager", None)
    if rm is None:
        return None
    if kernel.cycle_count - st["last_cluster_cycle"] < FRONTIER_MIN_INTERVAL:
        return None
    if len(rm.minted_clusters) >= FRONTIER_MAX_CLUSTERS:
        return None
    from xylarium.kernel.universe import habitability
    populated = free = 0
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population > 0:
                populated += 1
            elif free_world(p) and max(habitability(m, p.planet_type) for m in ("biotic", "mineral", "plasmic", "cryogenic")) >= DAUGHTER_MIN_HABITABILITY:
                free += 1
    fs = frontier_state(kernel)
    crowded = free < FRONTIER_FREE_WORLDS_RATIO * max(1, populated)
    if not crowded and fs["pressure"] < FRONTIER_PRESSURE_QUARTERS:
        return None
    index = 2 if 2 not in rm.minted_clusters else (3 if 3 not in rm.minted_clusters else max(rm.minted_clusters) + 1)
    ok, msg, new_ids = rm.mint_frontier_cluster(kernel, index)
    if not ok:
        return None
    fs["pressure"] = 0
    st["last_cluster_cycle"] = kernel.cycle_count
    st["clusters_opened"].append({"cycle": kernel.cycle_count, "cluster": index, "sectors": len(new_ids),
                                  "reason": "crowded" if crowded else "settler pressure"})
    return f"[FRONTIER] {msg}"


# ---------------------------------------------------------------------- households
def _markets(kernel: Any, planet: Any) -> List[Any]:
    """The starports of a world's money within HOUSEHOLD_RADIUS (re-surveyed every 250 cycles)."""
    def survey() -> List[int]:
        return [sid for sid in topology.reach(kernel, planet.sector_id, HOUSEHOLD_RADIUS)
                if kernel.sectors[sid].port is not None and kernel.sectors[sid].port.currency == planet.currency]
    sids = cache.memo(kernel, "household_markets", planet.id, survey, max_age=250)
    return [kernel.sectors[sid].port for sid in sids if kernel.sectors[sid].port is not None]


def households(kernel: Any) -> None:
    """Every populated world buys its basket from the region's starports: vault -> port, goods consumed."""
    from xylarium.kernel.economy import EconomyManager
    st = stats(kernel)
    for sec in kernel.sectors.values():
        for planet in sec.planets:
            if planet.population <= 0 or getattr(planet, "natives", None):
                continue
            ports = _markets(kernel, planet)
            budget = planet.household_purse
            if not ports or budget <= 0:
                _save(planet)
                continue
            wanted = filled = 0
            prosperity = max(0.3, planet.morale / 100.0)
            from xylarium.kernel import staples
            staple = staples.of(kernel, planet)
            basket: Dict[str, float] = {}
            for comm, per_k in HOUSEHOLD_BASKET.items():         # a household's groceries are its people's staple
                key = staple if comm == "ORGANICS" else comm
                basket[key] = basket.get(key, 0.0) + per_k
            for comm, per_k in basket.items():
                need = int(planet.population / 1000.0 * per_k * prosperity)
                if need <= 0:
                    continue
                wanted += need
                # Shop where the goods are plentiful (and therefore cheapest)
                for port in sorted(ports, key=lambda p: -p.stock.get(comm, 0)):
                    if need <= 0 or budget <= 0:
                        break
                    have = port.stock.get(comm, 0)
                    if have <= 1:
                        continue
                    _, price = EconomyManager.get_unit_prices(port, comm)
                    if price <= 0:
                        continue
                    units = min(need, have - 1, budget // price)
                    if units <= 0:
                        continue
                    bill = units * price
                    planet.household_purse -= bill
                    port.treasury += bill
                    port.stock[comm] = have - units
                    from xylarium.kernel import matter
                    matter.sink("households", comm, units)      # eaten, drunk, worn out at home
                    port.regional_income = round(port.regional_income + 0.3 * bill, 2)
                    budget -= bill
                    need -= units
                    filled += units
                    st["household_spend"][planet.currency] = st["household_spend"].get(planet.currency, 0) + bill
            st["household_units"] += filled
            if wanted and filled < wanted * 0.5:
                st["shortages"] += 1
                planet.morale = max(10, planet.morale - HOUSEHOLD_SHORTAGE_MORALE)
            if wanted:
                planet.society["basket_fill"] = round(filled / wanted, 3)
            # Provided for, households spend part of what is left on the luxuries they cannot make themselves
            from xylarium.kernel import luxury
            luxury.shop(kernel, planet, ports)
            _save(planet)


def _save(planet: Any) -> None:
    """Households keep modest savings; beyond that their money is deposited with (lent to) the colony."""
    cap = int(planet.population * HOUSEHOLD_PURSE_PER_CAPITA * PRICE_LEVEL.get(planet.currency, 1.0))
    if planet.household_purse > cap:
        planet.treasury += planet.household_purse - cap
        planet.household_purse = cap


# ---------------------------------------------------------------------- exports
def exports(kernel: Any) -> None:
    """
    A world sells what it produces beyond its own needs: its farms' and mines' surplus goes to the region's
    starports that buy it, and the producers (households) are paid. Nothing rots in a full silo, the region
    earns from its output, and captains who buy those goods bring money back into the region.
    """
    from xylarium.kernel.economy import EconomyManager
    from xylarium.config import CITADEL_UPKEEP, PORT_OPEX_FLOOR, PORT_START_TREASURY
    from xylarium.kernel import biosphere
    st = stats(kernel)
    season_cycles = _quarter_len()
    for sec in kernel.sectors.values():
        for planet in sec.planets:
            if planet.population <= 0 or getattr(planet, "natives", None):
                continue
            ports = _markets(kernel, planet)
            if not ports:
                continue
            # keep two seasons of the people's staple and of upkeep ore, and enough ore for the council's next works
            from xylarium.kernel import staples
            staple = staples.of(kernel, planet)
            food_keep = 2 * season_cycles * biosphere.consumption(planet)
            keep = {"ORGANICS": food_keep if staple == "ORGANICS" else 0,
                    "ORE": 2 * season_cycles * CITADEL_UPKEEP.get(planet.citadel_level, {"ore": 0})["ore"] + 500
                    + (food_keep if staple == "ORE" else 0)}
            silos = {"ORGANICS": "organics_silo", "ORE": "ore_silo"}
            # refined element reserves beyond what the world's own works use are for sale too
            for elem, have in list(planet.element_reserves.items()):
                kept = ELEMENT_RESERVE_KEPT + (food_keep if elem == staple else 0)
                if elem.startswith("LUX_"):
                    # luxuries are crafted to order: the world keeps a season of its own use and ships the rest
                    kept = int(planet.population / 1000.0 * LUXURY_WANT_PER_THOUSAND * 0.5)
                if have > kept:
                    silos[elem] = None
                    keep[elem] = kept
            for comm, attr in silos.items():
                held = getattr(planet, attr) if attr else planet.element_reserves.get(comm, 0)
                surplus = held - keep[comm]
                if surplus <= 0:
                    continue
                buyers = [p for p in ports if p.buys.get(comm)]
                if not buyers and comm.startswith("LUX_"):
                    from xylarium.kernel import luxury      # luxuries travel further when local shelves are full
                    buyers = [p for p in luxury.export_ports(kernel, planet) if p.buys.get(comm)]
                for port in sorted(buyers, key=lambda p: -EconomyManager.get_unit_prices(p, comm)[0]):
                    if surplus <= 0:
                        break
                    price, _ = EconomyManager.get_unit_prices(port, comm)
                    base = PORT_START_TREASURY * PRICE_LEVEL.get(port.currency, 1.0)
                    budget = int(port.treasury - base * PORT_OPEX_FLOOR)
                    room = port.max_stock.get(comm, 1000) - port.stock.get(comm, 0)
                    if comm.startswith("LUX_"):
                        from xylarium.kernel import luxury
                        room = luxury.port_room(port, comm)          # ports stock luxuries to what they sell
                    if price <= 0 or budget <= 0 or room <= 0:
                        continue
                    units = min(surplus, room, budget // price)
                    if units <= 0:
                        continue
                    bill = units * price
                    port.treasury -= bill
                    planet.household_purse += bill
                    port.stock[comm] = port.stock.get(comm, 0) + units
                    if attr:
                        setattr(planet, attr, getattr(planet, attr) - units)
                    else:
                        planet.element_reserves[comm] -= units
                    surplus -= units
                    ex = st.setdefault("exports", {})
                    ex[planet.currency] = ex.get(planet.currency, 0) + bill
                    from xylarium.kernel import ledger
                    if ledger.ACTIVE_POLICY is not None:
                        ledger.ACTIVE_POLICY.record_income(planet.currency, bill)


# ---------------------------------------------------------------------- player command
def set_policy(kernel: Any, captain: Any, planet: Any, policy: str) -> str:
    if planet.owner_id != captain.id:
        raise ValueError(f"You do not govern {planet.name}.")
    policy = (policy or "").lower()
    if policy not in POLICIES:
        raise ValueError("Population policy is EXPAND (settler fleets) or STEADY (population controls).")
    was = getattr(planet, "growth_policy", None)
    planet.growth_policy = policy
    if policy == "steady" and was != "steady":
        stats(kernel)["steady"] += 1
        _covenant(kernel, planet)
    return (f"{planet.name}: " + ("settler fleets will sail when the world is full." if policy == "expand"
                                 else "population controls adopted; numbers held at 95% of housing."))


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="demography",
    state=lambda: {"stats": {"habitats": 0, "citadels": 0, "daughters": 0, "emigrants": 0, "steady": 0,
                             "no_room": 0, "clusters_opened": [], "last_cluster_cycle": 0,
                             "household_spend": {}, "household_units": 0, "shortages": 0},
                   "frontier": {"pressure": 0}},
    season=quarter,
))
