"""
Xylarium backing: what stands behind each money - the goods its own holders keep - and what follows when too little
does.

A money is a claim on what its people make and hold. Its BACKING is the market value of the goods its own keep: the
stores of the worlds that keep their books in it (their element reserves, ore and organics) and the shelves of the
ports that trade in it, each good valued in SOL at the ports that price in SOL - never through the money's own rate. Its value per unit is that
backing over the money in existence (ledger.money_supply); its FAIR RATE against SOL is SOL's value per unit over
its own:

    r* (units per SOL) = (backing_SOL / supply_SOL) / (backing_cur / supply_cur)

A money that claims more than its goods is overvalued and falls toward r*; one worth more than the market pays for it
rises. Nobody decrees it:

  THE TRADERS   a money dearer than its goods is sold for SOL and the SOL spent on goods brought home; a money cheaper
                than its goods is bought and its goods carried out. Each quarter that goods route runs (arbitrage): the
                money's own ports pay into the exchange, the other side's ports are paid for goods that move between
                their shelves - as far as their treasuries and shelves allow - moving the rate halfway to its fair
                rate when it strays beyond the band the exchanges keep (CROSS_REANCHOR_RATE, CLEARING_BAND). Swaps and
                moved goods only: nothing is minted.
  THE PLACES    a local exchange's founding council keeps its own pools near the fair rate, moving its own money
                between its pools and its vault (exchanges.py).
  THE WORLDS    a world whose money's own backing keeps thinning - the goods behind each unit falling, beyond the
                noise, over two years (its goods, not a market's panic nor a neighbour's growth) - weighs leaving it
                for its realm's reserve money (its council's own choice, decide.choose): what the
                fall would take from its holdings over its horizon, against what converting costs today. If it goes,
                its vault and its households' purse are converted at the market (nothing minted) and it keeps its books
                in the reserve money from then on. A money all its worlds leave ends with its last holder: that is
                consolidation, and no one ordered it.
"""

from typing import Any, Dict, List, Optional
from xylarium.kernel.fx import hub as _hub


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "backing")


def value_sol(kernel: Any, comm: str) -> float:
    """What a good is worth in SOL, independent of any other money's market (a money's goods must not be valued
    through its own rate - a run would then empty its backing on paper): the mean mid price at the ports that price
    in SOL, or its listed real-output price where none trades it."""
    from xylarium.config import COMMODITY_CONFIG
    from xylarium.kernel import cache
    from xylarium.kernel.economy import EconomyManager

    def build() -> float:
        got = []
        for sec in kernel.sectors.values():
            port = getattr(sec, "port", None)
            if port is None or port.currency != _hub() or len(getattr(port, "stock", None) or {}) < len(COMMODITY_CONFIG):
                continue
            try:
                buy, sell = EconomyManager.get_unit_prices(port, comm)
            except Exception:
                continue
            if buy > 0 and sell > 0:
                got.append((buy + sell) / 2.0)
        return sum(got) / len(got) if got else float(COMMODITY_CONFIG.get(comm, {}).get("base_price", 0) or 0)
    if not hasattr(kernel, "caches"):
        return build()
    return cache.memo(kernel, "backing_value", comm, build, epoch=kernel.cycle_count // 25)


def _goods(holder: Any) -> Dict[str, int]:
    out = dict(getattr(holder, "element_reserves", None) or {})
    if hasattr(holder, "ore_silo"):
        out["ORE"] = out.get("ORE", 0) + int(holder.ore_silo or 0)
        out["ORGANICS"] = out.get("ORGANICS", 0) + int(holder.organics_silo or 0)
    return out


def measure(kernel: Any) -> Dict[str, Dict[str, float]]:
    """Every money's backing (SOL), supply (units), value per unit (SOL) and fair rate (units per SOL)."""
    from xylarium.config import COMMODITY_CONFIG
    from xylarium.kernel import ledger
    goods: Dict[str, float] = {}

    def add(cur: str, held: Dict[str, int]) -> None:
        for comm, q in held.items():
            if q > 0 and comm in COMMODITY_CONFIG:
                goods[cur] = goods.get(cur, 0.0) + q * value_sol(kernel, comm)

    for sec in kernel.sectors.values():
        for w in sec.planets:
            if w.population > 0:
                add(w.currency, _goods(w))
        if sec.port is not None:
            add(sec.port.currency, dict(sec.port.stock or {}))
    supply = {c: float(v.get("total", 0)) for c, v in ledger.money_supply(kernel).items()}
    out: Dict[str, Dict[str, float]] = {}
    for cur in sorted(set(goods) | set(supply)):
        s, g = supply.get(cur, 0.0), goods.get(cur, 0.0)
        out[cur] = {"backing_sol": round(g, 1), "supply": s, "per_unit": g / s if s > 0 else 0.0}
    sol = out.get(_hub(), {}).get("per_unit", 0.0)
    for cur, rec in out.items():
        rec["fair"] = (sol / rec["per_unit"]) if rec["per_unit"] > 0 and sol > 0 else None
    return out


def fair(kernel: Any, cur: str) -> Optional[float]:
    """A money's fair rate (units per SOL) as last measured, or None where nothing backs it yet."""
    if kernel is None or "backing" not in getattr(kernel, "state", {}):
        return None
    rec = stats(kernel)["of"].get(cur)
    return rec.get("fair") if rec else None


# ---------------------------------------------------------------------- worlds leaving a failing money
def _falling(kernel: Any, cur: str) -> Optional[float]:
    """How fast the goods behind each unit of a money have been thinning - the mean log fall a quarter of its own
    backing per unit over the last two years (not its rate against a neighbour that is growing richer) - when that
    fall clears its own standard error (as a governor moves on evidence, regimes.review); None if its goods hold or
    the change is within the noise. A market's fall its goods do not share is a run, not a failure: no one leaves."""
    import math
    from xylarium.kernel import regimes
    hist = [h for h in (stats(kernel)["per_unit"].get(cur) or []) if h and h > 0]
    if len(hist) < 5:
        return None
    steps = [math.log(a / b) for a, b in zip(hist, hist[1:])]      # positive where each unit holds less
    drift = sum(steps) / len(steps)
    return drift if drift > 0 and drift > regimes.stderr(steps) else None


def _reserve_for(kernel: Any, world: Any) -> Optional[str]:
    """The reserve money of the realm a world lies in (transit.reserves: the ancients' own moneys) - SOL where none."""
    from xylarium.kernel import spheres, transit
    res = transit.reserves(kernel)
    if "spheres" in kernel.state:
        keeper = spheres.presence(kernel, spheres.owner(kernel, world.sector_id))
        for cur, who in res.items():
            if who == keeper:
                return cur
    return _hub() if _hub() in res or not res else sorted(res)[0]


def leave(kernel: Any, world: Any, to_cur: str, logs: List[str]) -> bool:
    """A world keeps its books in another money from now on: its vault and its households' purse converted at the
    market."""
    from xylarium.kernel import history
    fx = kernel.fx_market
    old = world.currency
    if old == to_cur or not fx.can_convert(old, to_cur):
        return False
    world.treasury = fx.convert(old, to_cur, int(world.treasury))[0] if world.treasury > 0 else 0
    world.household_purse = fx.convert(old, to_cur, int(world.household_purse))[0] if world.household_purse > 0 else 0
    world.currency = to_cur
    stats(kernel)["left"].setdefault(old, []).append({"world": world.id, "to": to_cur, "cycle": kernel.cycle_count})
    history.event(kernel, "MONEY_LEFT", f"{world.name} leaves the {old} for the {to_cur}",
                  actors=[f"planet:{world.id}"], sector_id=world.sector_id,
                  cause="the goods behind its money kept thinning")
    logs.append(f"[MONEY] {world.name} leaves the {old} for the {to_cur}.")
    return True


def _weigh(kernel: Any, logs: List[str]) -> None:
    """Each year: the worlds of a falling money its bank cannot hold weigh leaving it."""
    from xylarium.kernel import decide
    fx = kernel.fx_market
    for cur in sorted(fx.pools):
        drift = _falling(kernel, cur)
        if drift is None:
            continue                                       # its goods hold: no one leaves
        for sec in kernel.sectors.values():
            for w in sec.planets:
                if w.population <= 0 or w.currency != cur:
                    continue
                to = _reserve_for(kernel, w)
                if not to or to == cur:
                    continue
                held = float(w.treasury + w.household_purse)
                if held <= 0:
                    continue
                m = decide.mind_of_planet(kernel, w)
                held_sol = fx.to_sol_value(cur, held)
                loss_q = held_sol * (1.0 - pow(2.718281828, -drift))     # what the fall takes a quarter
                cost = held_sol * (fx.fee(cur) + (fx.fee(to) if to != _hub() else 0.0))   # converting today
                if decide.choose(kernel, [decide.option("leave", cost, decide.worth(kernel, loss_q, m, cur))],
                                 m, w.id, cur, "leave") is not None:
                    leave(kernel, w, to, logs)


def _ports(kernel: Any, cur: str) -> List[Any]:
    return [s.port for s in kernel.sectors.values() if s.port is not None and s.port.currency == cur]


def _move_goods(kernel: Any, src: List[Any], dst: List[Any], value: float) -> float:
    """Goods worth `value` SOL from the source ports' shelves to the destination ports' (largest holdings first);
    returns the value moved."""
    from xylarium.kernel import supply
    if not src or not dst or value <= 0:
        return 0.0
    moved = 0.0
    lots = sorted(((p.stock.get(c, 0) * value_sol(kernel, c), c, p) for p in src for c in supply.goods()
                   if p.stock.get(c, 0) > 0), key=lambda x: (-x[0], x[1]))
    i = 0
    for worth, comm, p in lots:
        if moved >= value:
            break
        unit = value_sol(kernel, comm)
        if unit <= 0:
            continue
        q = min(p.stock[comm], int((value - moved) / unit) + 1)
        p.stock[comm] -= q
        d = dst[i % len(dst)]
        d.stock[comm] = d.stock.get(comm, 0) + q
        i += 1
        moved += q * unit
    return moved


def arbitrage(kernel: Any) -> Dict[str, float]:
    """The goods route between each money and SOL: where its rate strays beyond the exchanges' band from what its
    goods are worth, its ports and SOL's trade goods for money until the rate has moved halfway back. Returns each
    money's gap (market over fair) before."""
    import math
    from xylarium.config import CLEARING_BAND, CROSS_REANCHOR_RATE
    fx = kernel.fx_market
    gaps: Dict[str, float] = {}
    sol_ports = _ports(kernel, _hub())
    for cur, p in sorted(fx.pools.items()):
        r_star = fair(kernel, cur)
        if not r_star or p["sol"] <= 0 or p["local"] <= 0:
            continue
        r = fx.rate(cur)
        gaps[cur] = round(r / r_star - 1.0, 4)
        if r_star / CLEARING_BAND <= r <= r_star * CLEARING_BAND:
            continue
        own = _ports(kernel, cur)
        target = r * (r_star / r) ** CROSS_REANCHOR_RATE
        k = p["sol"] * p["local"]
        if r < r_star:                                       # dearer than its goods: its holders sell it for SOL
            local_in = int(math.sqrt(k * target) - p["local"])
            local_in = min(local_in, sum(max(0, q.treasury) for q in own))
            if local_in <= 0:
                continue
            got = 0
            for q in sorted(own, key=lambda x: -x.treasury):
                take = min(max(0, q.treasury), local_in - got)
                q.treasury -= take
                got += take
            sol_out = fx.swap_to_sol(cur, got)
            bought = _move_goods(kernel, sol_ports, own, sol_out)          # SOL buys goods; they go home
            for q in sol_ports:
                q.treasury += int(sol_out / max(1, len(sol_ports)))
            rest = sol_out - int(sol_out / max(1, len(sol_ports))) * len(sol_ports)
            if sol_ports:
                sol_ports[0].treasury += rest
            else:                                                          # no SOL port: the SOL stays with them
                own[0].treasury += fx.swap_sol_to(cur, sol_out) if own else 0
            stats(kernel)["routed"][cur] = stats(kernel)["routed"].get(cur, 0.0) + bought
        else:                                                 # cheaper than its goods: SOL buys it, its goods go out
            sol_in = int(math.sqrt(k / target) - p["sol"])
            sol_in = min(sol_in, sum(max(0, q.treasury) for q in sol_ports))
            if sol_in <= 0:
                continue
            got = 0
            for q in sorted(sol_ports, key=lambda x: -x.treasury):
                take = min(max(0, q.treasury), sol_in - got)
                q.treasury -= take
                got += take
            local_out = fx.swap_sol_to(cur, got)
            _move_goods(kernel, own, sol_ports, got)                        # its goods carried out
            for q in own:
                q.treasury += int(local_out / max(1, len(own)))
            rest = local_out - int(local_out / max(1, len(own))) * len(own)
            if own:
                own[0].treasury += rest
            stats(kernel)["routed"][cur] = stats(kernel)["routed"].get(cur, 0.0) - got
    return gaps


def season(kernel: Any) -> List[str]:
    """Every quarter: each money's backing and fair rate measured, its rate noted; once a year, the worlds of a
    falling money its bank cannot hold weigh leaving it."""
    from xylarium.kernel import polity
    fx = getattr(kernel, "fx_market", None)
    if fx is None:
        return []
    st = stats(kernel)
    st["of"] = {c: {k: (round(v, 6) if isinstance(v, float) else v) for k, v in rec.items()}
                for c, rec in measure(kernel).items()}
    for cur in fx.pools:
        hist = st["rates"].setdefault(cur, [])
        hist.append(round(fx.rate(cur), 6))
        del hist[:-8]
        fh = st.setdefault("per_unit", {}).setdefault(cur, [])
        fh.append(st["of"].get(cur, {}).get("per_unit"))
        del fh[:-9]
    st["gaps"] = arbitrage(kernel)
    logs: List[str] = []
    if (kernel.cycle_count // polity._quarter()) % 4 == 0:
        _weigh(kernel, logs)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    fx = getattr(kernel, "fx_market", None)
    out = {}
    for cur, rec in st["of"].items():
        mk = fx.rate(cur) if fx is not None and cur in fx.pools else (1.0 if cur == _hub() else None)
        out[cur] = {"backing_sol": rec.get("backing_sol"), "fair": rec.get("fair"), "market": mk}
    return {"moneys": out, "worlds_left": {c: len(v) for c, v in st["left"].items()},
            "gaps": dict(st.get("gaps", {})), "routed_sol": {c: round(v) for c, v in st.get("routed", {}).items()}}



# ---------------------------------------------------------------------- the reserve basket: survival by mass
KLEIBER_B0 = 3.4                # W per kg^(3/4): Kleiber (1932), measured across bodies - the metabolic ruler
SECONDS_PER_YEAR = 3.15576e7
# what a biosphere fixes, by its food and the solvent its chemistry runs in, and that food's oxidation: carbon fixed
# in water is carbohydrate, (CH2O)n. Every other (food, solvent) is OWED - never assumed to be Earth's food.
FIXED = {("ORGANICS", "H2O"): ("C6H12O6", {"O2": 6}, {"CO2": 6, "H2O": 6})}


def food_energy_j_per_kg(good: str, solvent: Optional[str] = "H2O") -> Optional[float]:
    """The energy a kilogram of a food holds, from its bond enthalpies: what a biosphere of that chemistry fixes in its
    solvent, oxidised (substances' measured formation enthalpies). None where that chemistry is not derived yet."""
    from xylarium.kernel import substances
    got = FIXED.get((good, solvent))
    if got is None:
        return None
    sym, reac, prod = got
    dh = sum(n * substances.formation(x)[0] for x, n in prod.items()) - \
        (substances.formation(sym)[0] + sum(n * substances.formation(x)[0] for x, n in reac.items()))
    m = substances.molar_mass(sym)
    return -dh * 1000.0 / (m / 1000.0) if m and dh < 0 else None      # kJ/mol over kg/mol -> J/kg


def basket(kernel: Any, who: str) -> Optional[Dict[str, Any]]:
    """A people's reserve basket: what one of its people needs to live a year where it lives (its home world - for
    the ancients, the core), by good. The RESERVE UNIT is one person-year of survival there.

      FOOD       its staple (staples.of), FOOD_PER_THOUSAND a thousand a cycle; kg from its metabolism - Kleiber's
                 B0 x its OWN body's mass^(3/4) x its chemistry's pace (biosphere.need_factor: life history, gravity,
                 body temperature) - over the energy density of what its biosphere fixes in its solvent
      BODY       its bodies' turnover: its own body's mass (life.M_MIND_KG x its size: biosphere.body_mass) over a
                 life (lifespan), in its staple
      MEDIUM     the matter its chemistry runs in (uses.MEDIUM_GOOD): OWED (no turnover a head is modelled yet)
      STRUCTURE  its walls' wear a head (citadel upkeep, in the good they are made of: uses.wears)
      SHIELDING  against its home's dose (hydromagnetics): OWED (a dwelling's column from the crust's materials)

    Returns {"units": {good: Fraction a capita-year}, "kg": {good: Fraction or None}, "owed": {term: what would give
    it}, "home": planet id}. kg is the basket's identity; units are how ports price it; owed terms say what is not yet
    measured. None if the people has no living home."""
    from fractions import Fraction as Fr
    from xylarium.config import CITADEL_UPKEEP, FOOD_PER_THOUSAND
    from xylarium.kernel import biosphere, lifespan, spheres, staples, uses
    home = spheres._home(kernel, who)
    if home is None or getattr(home, "population", 0) <= 0:
        return None
    cycles = Fr(100)                                         # cycles a year (the clock's own: 100 to the year)
    units: Dict[str, Fr] = {}
    kg: Dict[str, Optional[Fr]] = {}
    owed: Dict[str, str] = {}
    food = staples.of(kernel, home)
    eat = Fr(FOOD_PER_THOUSAND) / 1000 * cycles
    from xylarium.kernel import life as _life
    rel_mass = Fr(biosphere.body_mass(home, kernel))            # its size over a mind's body (a float's exact value)
    body_kg_each = Fr(_life.M_MIND_KG) * rel_mass                # its own body, kg
    life = Fr(float(lifespan.expectancy_years(kernel, home)))     # exact: a float is a dyadic fraction
    body_u = Fr(FOOD_PER_THOUSAND) / 1000 * lifespan.BODY_CYCLES * rel_mass / life if life > 0 else Fr(0)
    units[food] = eat + body_u
    body = uses.body(kernel, home)
    e = food_energy_j_per_kg(food, body["solvent"] if body else None)
    if e:
        watts = KLEIBER_B0 * _life.M_MIND_KG ** 0.75 * biosphere.need_factor(home, kernel)   # need_factor carries
        # its own size^(3/4) and its chemistry's pace
        eaten_kg = Fr(watts * SECONDS_PER_YEAR / e)          # exact: the float's own value, no declared quantum
        body_kg = body_kg_each / life if life > 0 else Fr(0)
        kg[food] = eaten_kg + body_kg
    else:
        kg[food] = None
        owed["food_energy_density"] = (f"what a {biosphere.metabolism_of(kernel, home)} biosphere fixes in "
                                       f"{(body or {}).get('solvent', 'its solvent')}, oxidised")
    medium = uses.MEDIUM_GOOD.get(body["solvent"]) if body else None
    if medium:
        owed["medium"] = f"{medium}: a body's medium turnover a year (households, domes)"
    wall = uses.wears(kernel, home)
    up = CITADEL_UPKEEP.get(home.citadel_level, CITADEL_UPKEEP[0])
    if wall and up.get("ore"):
        units[wall] = units.get(wall, Fr(0)) + Fr(int(up["ore"])) * cycles / max(1, int(home.population))
        kg.setdefault(wall, None)
        owed["structure_kg"] = f"{wall}: a dwelling's mass from the crust's materials"
    owed["shielding"] = "against its home's dose: a dwelling's shielding column from the crust's materials"
    return {"units": units, "kg": kg, "owed": owed, "home": home.id, "reserve_unit": "one person-year at its home"}


def basket_value(kernel: Any, b: Dict[str, Any], cur: str) -> Optional[Any]:
    """A basket's worth in a money, exact: each good's units at that money's own ports' mean price (never through the
    hub). None where its ports price none of its goods."""
    from fractions import Fraction as Fr
    from xylarium.kernel.economy import EconomyManager
    total, priced = Fr(0), False
    for good, q in b["units"].items():
        prices = [EconomyManager.get_unit_prices(sec.port, good)[1] for sec in kernel.sectors.values()
                  if sec.port is not None and sec.port.currency == cur and sec.port.sells.get(good)]
        prices = [p for p in prices if p > 0]
        if prices:
            total += Fr(q) * Fr(sum(Fr(p) for p in prices), len(prices))
            priced = True
    return total if priced else None

from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="backing",
    state=lambda: {"of": {}, "rates": {}, "per_unit": {}, "left": {}, "gaps": {}, "routed": {}},
    season=season,
    summary=summary,
))
