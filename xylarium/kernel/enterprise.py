"""
Xylarium enterprise: firms that make things, founded where making them pays, and let die when it no longer does.

Laid over the corporate machine that already exists (market.py: listed companies, shares, the ISSE, chairmen,
dividends, executives), a PROCESS FIRM is a listed company that runs one of the economy's own manufacturing recipes
(config COMMODITY_CONFIG[...]["recipe"] - equipment from ore, superconductors, biosphere packs, engine manifolds,
warp cores) at its home world's starport:

    each quarter it buys its inputs and a unit of its world's fuel per batch at the port, pays its workers' wages
    into its home world's households, makes as many batches as its plant, its cash and the port's shelves allow,
    and sells them back; its people's mastery of materials cuts the waste in every recipe (the learning curve);
    its plant depreciates 10% a year, paid as maintenance to its contractors

Its books are its own: plant (capacity, in batches a quarter), cash in its home money, and a record of each
quarter's profit. Shareholders - its founder (a council's people, or a captain) and whoever buys its float on the
ISSE - are paid a dividend from profit, in the home money.

THE INCORPORATION HURDLE. A firm is founded where the return on its capital beats the price of waiting: each year,
on every world with a port, its council weighs the best recipe at that port's prices - a quarter's profit per
batch of capacity against the plant it costs - by the one decision rule (decide.py), whose discount is the
money's policy rate. Profitable firms reinvest the same way. Entry is what compresses margins: firms buy ore and
sell equipment until making more no longer pays.

CREATIVE DESTRUCTION. A firm that loses money four quarters running goes into receivership: its plant is
auctioned to a rival running the same recipe in the same money (at what its remaining value is worth to it) or
scrapped, its cash is paid out to its shareholders pro rata, and it is struck from the exchange. Every unit of
money moves between holders; nothing is written off into nowhere.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import COMMODITY_CONFIG, COLONY_TAX_PER_CAPITA, HABITAT_COST, PRICE_LEVEL
from xylarium.kernel import decide, ledger, matter
from xylarium.kernel.fx import hub as _hub

RECIPES = {c: dict(cfg["recipe"]) for c, cfg in COMMODITY_CONFIG.items() if cfg.get("recipe")}
WORKERS_PER_BATCH = 50          # hands a batch takes for a quarter
PLANT_COST_PER_BATCH = 0.1      # of a habitat's price, per batch of quarterly capacity
DEPRECIATION_YEAR = 0.10        # plant wears out at a tenth a year (paid as maintenance)
RECEIVERSHIP_QUARTERS = 4
DIVIDEND_SHARE = 0.3            # of a quarter's profit paid to shareholders
FOUNDER_SHARE = 0.6             # of the shares its founder keeps; the rest float on the ISSE


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "enterprise")


def _port(kernel: Any, planet: Any):
    from xylarium.kernel.colony import ColonyManager
    port = ColonyManager._contractor_port(planet, kernel)
    return port if (port is not None and port.currency == planet.currency) else None


def _prices(port: Any, comm: str) -> Tuple[int, int]:
    from xylarium.kernel.economy import EconomyManager
    return EconomyManager.get_unit_prices(port, comm)       # (port buys at, port sells at)


def _waste(kernel: Any, holder: Optional[str]) -> float:
    """Inputs a batch takes beyond the recipe's own, as a share, falling with materials mastery."""
    from xylarium.kernel import knowledge
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import laws
    return laws.wright(knowledge.experience(kernel, holder, "materials"), KNOWLEDGE_UNIT)


def _wage(planet: Any) -> float:
    return COLONY_TAX_PER_CAPITA * PRICE_LEVEL.get(planet.currency, 1.0) * _quarter() * WORKERS_PER_BATCH


def unit_economics(kernel: Any, planet: Any, port: Any, out: str) -> Optional[Dict[str, float]]:
    """A batch of `out` at this port today: what it sells for, what it costs, and how many the shelves allow."""
    from xylarium.kernel import knowledge, propulsion
    recipe = RECIPES[out]
    sell_out, _ = _prices(port, out)
    if sell_out <= 0 or not port.buys.get(out, True):
        return None
    waste = 1.0 + _waste(kernel, knowledge.holder_of_planet(planet)) * 0.5
    cost, shelves = 0.0, 10 ** 9
    for comm, q in recipe.items():
        _, buy_in = _prices(port, comm)
        if buy_in <= 0:
            return None
        cost += buy_in * q * waste
        shelves = min(shelves, int(available(kernel, planet, port, comm) / (q * waste)))
    fuel = propulsion.world_fuel(kernel, planet)
    _, fuel_price = _prices(port, fuel)
    cost += max(0, fuel_price) + _wage(planet)
    shelves = min(shelves, available(kernel, planet, port, fuel))
    room = port.max_stock.get(out, 500) - port.stock.get(out, 0)
    purse = int(max(0, port.treasury) // max(1, sell_out))        # a buyer cannot take what it cannot pay for
    return {"price": sell_out, "cost": cost, "margin": sell_out - cost, "shelves": max(0, min(shelves, room, purse)),
            "fuel": fuel, "waste": waste}


def available(kernel: Any, planet: Any, port: Any, comm: str) -> int:
    """What a firm can source: its own world's surplus (above the world's reserve), then the port's shelves."""
    from xylarium.kernel import staples
    return max(0, staples.surplus(kernel, planet, comm)) + max(0, port.stock.get(comm, 0))


def _source(kernel: Any, comp: Any, planet: Any, port: Any, comm: str, n: int) -> int:
    """Buy n units: from the home world first (at what the port would pay it), then the port; consumed in the
    work. Returns what it cost."""
    from xylarium.kernel import staples
    paid = 0
    own = min(n, max(0, staples.surplus(kernel, planet, comm)))
    if own > 0:
        price, _ = _prices(port, comm)
        staples.take(planet, comm, own, "manufacture")
        planet.treasury += own * price
        paid += own * price
        n -= own
    n = min(n, port.stock.get(comm, 0))
    if n > 0:
        _, price = _prices(port, comm)
        port.stock[comm] -= n
        matter.sink("manufacture", comm, n)
        port.treasury += n * price
        paid += n * price
    comp.home_cash -= paid
    return paid


def _import(kernel: Any, comp: Any, planet: Any, comm: str, amount: int) -> Optional[str]:
    """A firm short of an input posts an import order to its home world, escrowed from its own cash."""
    from xylarium.config import COLONY_IMPORT_HOP_FEE, COLONY_IMPORT_UNIT_PREMIUM
    from xylarium.kernel import topology
    from xylarium.kernel.market import FreightContract
    mm = kernel.market_manager
    if any(c.status in ("OPEN", "IN_TRANSIT") and c.escrow_source == f"company:{comp.ticker}"
           for c in mm.contracts.values()):
        return None
    dist = topology.distances_to(kernel, planet.sector_id)
    origins = [s for s in kernel.sectors.values() if s.port is not None and s.id != planet.sector_id
               and s.port.sells.get(comm, False) and s.port.stock.get(comm, 0) >= amount and s.id in dist]
    if not origins:
        return None
    origin = min(origins, key=lambda s: dist[s.id])
    base = COMMODITY_CONFIG.get(comm, {}).get("base_price", 20)
    payout = int((base * COLONY_IMPORT_UNIT_PREMIUM * amount + max(1, dist[origin.id]) * COLONY_IMPORT_HOP_FEE)
                 * PRICE_LEVEL.get(planet.currency, 1.0))
    if comp.home_cash < payout * 2:
        return None
    comp.home_cash -= payout
    cid = f"FRT-{mm.next_contract_id}"
    mm.next_contract_id += 1
    sec = kernel.sectors[planet.sector_id]
    mm.contracts[cid] = FreightContract(
        id=cid, company_ticker=comp.ticker, issuer_name=comp.name, origin_sector=origin.id, origin_name=origin.port.name,
        destination_sector=planet.sector_id, destination_planet_id=planet.id, destination_name=planet.name,
        commodity=comm, amount=amount, payout_credits=payout, shares_reward=0, hazard_level=sec.security.value,
        created_cycle=kernel.cycle_count, expiry_cycle=kernel.cycle_count + 60, status="OPEN",
        escrow_source=f"company:{comp.ticker}", escrow_amount=payout, currency=planet.currency)
    stats(kernel)["imports"] = stats(kernel).get("imports", 0) + 1
    return cid


def unit_economics_fuel(kernel: Any, planet: Any) -> str:
    from xylarium.kernel import propulsion
    return propulsion.world_fuel(kernel, planet)


def plant_cost(planet: Any, batches: int) -> float:
    return HABITAT_COST * PRICE_LEVEL.get(planet.currency, 1.0) * PLANT_COST_PER_BATCH * batches


# ---------------------------------------------------------------------- a firm's quarter
def _firm_world(kernel: Any, comp: Any):
    return kernel.get_planet(comp.planet_id) if getattr(comp, "planet_id", None) else None


def operate(kernel: Any, comp: Any, rec: Dict[str, Any]) -> float:
    """One quarter of making, selling, paying; returns the quarter's profit in the home money."""
    from xylarium.kernel.demography import _pay_contractor
    planet = _firm_world(kernel, comp)
    port = _port(kernel, planet) if planet is not None else None
    profit = 0.0
    if port is None:
        return 0.0
    out = rec["process"]
    from xylarium.kernel import chemistry, knowledge
    econ = unit_economics(kernel, planet, port, out) if chemistry.can_make(
        kernel, knowledge.holder_of_planet(planet), out) else None
    # capital raised on the ISSE (SOL) is put to work in the home money when operating cash runs short
    need = (econ["cost"] * rec["plant"]) if econ else 0.0
    if comp.treasury > 0 and comp.home_cash < need:
        sol = min(comp.treasury, int(kernel.fx_market.to_sol_value(planet.currency, need - comp.home_cash)) + 1)
        comp.treasury -= sol
        comp.home_cash += kernel.fx_market.swap_sol_to(planet.currency, sol) if planet.currency != _hub() else sol
    batches = 0
    LOT = 5
    # make in lots, re-pricing as its own buying and selling move the port: stop when the next lot no longer pays
    while econ is not None and econ["margin"] > 0 and batches < int(rec["plant"]):
        lot = min(LOT, int(rec["plant"]) - batches, econ["shelves"], int(comp.home_cash // max(1e-9, econ["cost"])))
        if lot <= 0:
            break
        spent = 0
        for comm, q in RECIPES[out].items():
            spent += _source(kernel, comp, planet, port, comm, int(math.ceil(q * econ["waste"] * lot)))
        spent += _source(kernel, comp, planet, port, econ["fuel"], lot)        # burned to do the work
        wages = min(int(_wage(planet) * lot), max(0, comp.home_cash))
        comp.home_cash -= wages
        planet.household_purse += wages                      # the firm's workers are its world's households
        matter.source("manufacture", out, lot)
        price, _ = _prices(port, out)
        revenue = min(int(price * lot), max(0, int(port.treasury)))
        port.treasury -= revenue
        port.stock[out] = port.stock.get(out, 0) + lot
        comp.home_cash += revenue
        profit += revenue - spent - wages
        batches += lot
        econ = unit_economics(kernel, planet, port, out)
    rec["made"] = rec.get("made", 0) + batches
    if batches < int(rec["plant"]) and (econ is None or econ["shelves"] <= 0):
        short = next((c for c in list(RECIPES[out]) + [unit_economics_fuel(kernel, planet)]
                      if available(kernel, planet, port, c) <= 0), None)
        if short is not None:
            _import(kernel, comp, planet, short, max(10, int(rec["plant"]) * RECIPES[out].get(short, 1)))
    # plant wears: maintenance paid to the contractors, and capacity that is not kept up is lost
    upkeep = int(upkeep_q(planet, rec["plant"]))
    paid = min(upkeep, max(0, comp.home_cash))
    if paid > 0:
        comp.home_cash -= paid
        port.treasury += paid
    if paid < upkeep:
        rec["plant"] = max(0.0, rec["plant"] * (1 - DEPRECIATION_YEAR * _quarter() / 100.0))
    profit -= upkeep
    rec["profit_q"] = round(profit, 1)
    rec["batches_q"] = batches
    why = ("made" if batches > 0 else "no_plant" if int(rec["plant"]) < 1
           else "no_margin" if (econ is None or econ["margin"] <= 0)
           else "no_shelves" if econ["shelves"] <= 0 else "no_cash")
    hist = rec.setdefault("history", [])
    hist.append(why)
    del hist[:-4]
    rec["losses"] = rec.get("losses", 0) + 1 if profit < 0 else 0
    comp.quarterly_revenue += int(max(0, profit))
    return profit


def _holders(kernel: Any, comp: Any) -> List[Tuple[Any, int]]:
    out = []
    for cap in kernel.captains.values():
        n = (getattr(cap, "portfolio", {}) or {}).get(comp.ticker, 0)
        if n > 0:
            out.append((cap, n))
    return out


def _pay_out(kernel: Any, comp: Any, amount: int, rec: Dict[str, Any]) -> int:
    """Pay `amount` of home money pro rata to shareholders: captains' wallets; the founding people's share to its
    world's vault; unsold float stays with the firm."""
    from xylarium.kernel import fx
    if amount <= 0:
        return 0
    total = max(1, comp.total_shares)
    paid = 0
    for cap, n in _holders(kernel, comp):
        share = amount * n // total
        if share > 0:
            if comp.home_currency == _hub():
                cap.credits += share
            else:
                fx.credit(cap, comp.home_currency, share)
            paid += share
    founder = rec.get("founder_shares", 0)
    planet = _firm_world(kernel, comp)
    if founder and planet is not None and rec.get("founder") == "people":
        share = amount * founder // total
        planet.treasury += share
        paid += share
    comp.home_cash -= paid
    return paid


def receivership(kernel: Any, ticker: str, rec: Dict[str, Any]) -> str:
    """Creative destruction: auction the plant to a rival of the same recipe and money, pay out the cash, delist."""
    mm = kernel.market_manager
    comp = mm.companies[ticker]
    st = stats(kernel)
    planet = _firm_world(kernel, comp)
    for c in list(mm.contracts.values()):            # its open orders are cancelled: escrow comes home first
        if c.status in ("OPEN", "IN_TRANSIT") and c.escrow_source == f"company:{ticker}":
            mm.void_contract(c, kernel)
    rivals = [(t, r) for t, r in st["firms"].items() if t != ticker and r["process"] == rec["process"]
              and t in mm.companies and mm.companies[t].home_currency == comp.home_currency]
    sold = None
    port = _port(kernel, planet) if planet is not None else None
    # a rival takes only the plant the port's demand can use beyond what is already there; the rest is scrapped
    useful = min(rec["plant"], max(0.0, demand(kernel, port, rec["process"])
                                   - capacity_at(kernel, port, rec["process"], but=ticker))) if port is not None else 0
    if rivals and planet is not None and useful >= 1:
        price = int(plant_cost(planet, useful) * 0.5)               # half its replacement cost, as it stands
        for t, r in sorted(rivals, key=lambda tr: -mm.companies[tr[0]].home_cash):
            buyer = mm.companies[t]
            if buyer.home_cash >= price:
                buyer.home_cash -= price
                comp.home_cash += price
                r["plant"] += useful
                sold = buyer.name
                break
    from xylarium.kernel import liquidation
    founder = (planet, rec.get("founder_shares", 0)) if (planet is not None and rec.get("founder") == "people") \
        else None
    wound = liquidation.liquidate(kernel, ticker, "receivership", founder=founder,
                                  auction=f"plant to {sold}" if sold else "plant scrapped")
    payout = wound["paid_out_sol"]
    st["firms"].pop(ticker, None)
    st["bankrupt"] += 1
    for why in rec.get("history", []):
        st.setdefault("failure_causes", {})[why] = st.setdefault("failure_causes", {}).get(why, 0) + 1
    chron = getattr(kernel, "chronicle", None)
    if chron is not None:
        chron.record(kernel, "RECEIVERSHIP", ticker, comp.name, f"The Fall of {comp.name}",
                     f"Four quarters it made {rec['process']} at a loss. Its plant went "
                     + (f"to {sold}" if sold else "for scrap") + f"; {payout:,.0f} SOL's worth went back to "
                     f"those who had trusted it.", tags=["enterprise", "receivership"])
    return f"[ENTERPRISE] {comp.name} ({ticker}) is in receivership: plant " + \
        (f"auctioned to {sold}" if sold else "scrapped") + f", {payout:,.0f} SOL's worth paid out."


# ---------------------------------------------------------------------- founding and growth
def best_recipe(kernel: Any, planet: Any, port: Any) -> Optional[Tuple[str, Dict[str, float]]]:
    from xylarium.kernel import chemistry, knowledge
    holder = knowledge.holder_of_planet(planet)
    best = None
    for out in RECIPES:
        if not chemistry.can_make(kernel, holder, out):
            continue                                  # a people makes only what its chemistry reaches
        econ = unit_economics(kernel, planet, port, out)
        if econ is None or econ["margin"] <= 0 or econ["shelves"] <= 0:
            continue
        if best is None or econ["margin"] * econ["shelves"] > best[1]["margin"] * best[1]["shelves"]:
            best = (out, econ)
    return best


def _ticker(mm: Any, planet: Any, out: str) -> str:
    base = "".join(ch for ch in (planet.name[:2] + out[:2]).upper() if ch.isalnum())[:4] or "FIRM"
    t, i = base, 1
    while t in mm.companies:
        t = f"{base[:3]}{i}"
        i += 1
    return t


def found(kernel: Any, planet: Any, out: str, batches: int, founder: str = "people") -> str:
    from xylarium.kernel.demography import _pay_contractor
    from xylarium.kernel.market import Company
    mm = kernel.market_manager
    st = stats(kernel)
    capital = plant_cost(planet, batches)
    working = capital                                   # a quarter of inputs kept in hand
    _pay_contractor(kernel, planet, int(capital))       # the plant is built
    planet.treasury -= int(working)
    ticker = _ticker(mm, planet, out)
    shares = 10000
    name = f"{planet.name} {COMMODITY_CONFIG[out].get('name', out).split()[0]} Works"
    comp = Company(ticker=ticker, name=name, sector_id=planet.sector_id, planet_id=planet.id,
                   planet_name=planet.name, industry="MANUFACTURING", founder_id=founder, level=1,
                   share_price=max(1, int(kernel.fx_market.to_sol_value(planet.currency, capital + working) / shares)),
                   total_shares=shares, available_shares=int(shares * (1 - FOUNDER_SHARE)), treasury=0,
                   dividend_rate=DIVIDEND_SHARE, price_history=[1])
    comp.home_cash, comp.home_currency = int(working), planet.currency
    mm.companies[ticker] = comp
    st["firms"][ticker] = {"process": out, "plant": float(batches), "founder": founder,
                           "founder_shares": int(shares * FOUNDER_SHARE), "since": kernel.cycle_count,
                           "losses": 0}
    st["founded"] += 1
    from xylarium.kernel import primordial
    primordial.first(kernel, "first_firm", name)
    return f"[ENTERPRISE] {name} ({ticker}) incorporated on {planet.name}: {batches} batches of {out} a quarter."


def drawn(kernel: Any, port: Any, comm: str, units: int) -> None:
    """Goods leaving a port's shelves - used up by its region or bought by captains: the demand a maker can sell to."""
    if kernel is None or units <= 0 or port is None:
        return
    d = stats(kernel).setdefault("drawn", {}).setdefault(str(port.sector_id), {})
    d[comm] = d.get(comm, 0) + units


def demand(kernel: Any, port: Any, comm: str) -> float:
    """A port's smoothed offtake of a good, per quarter."""
    return float(stats(kernel).get("demand", {}).get(str(port.sector_id), {}).get(comm, 0.0))


def _smooth_demand(kernel: Any) -> None:
    st = stats(kernel)
    dem = st.setdefault("demand", {})
    drawn_q = st.get("drawn", {})
    for sid in sorted(set(dem) | set(drawn_q)):                # never hash order
        now = drawn_q.get(sid, {})
        old = dem.setdefault(sid, {})
        for comm in sorted(set(old) | set(now)):
            v = 0.7 * old.get(comm, 0.0) + 0.3 * now.get(comm, 0)
            if v < 0.01:
                old.pop(comm, None)
            else:
                old[comm] = round(v, 2)
    st["drawn"] = {}


def capacity_at(kernel: Any, port: Any, out: str, but: Optional[str] = None) -> float:
    """The plant already making `out` for this port (every firm selling there but `but`)."""
    mm = kernel.market_manager
    return sum(r["plant"] for t, r in stats(kernel)["firms"].items()
               if t != but and r["process"] == out and t in mm.companies
               and _port(kernel, _firm_world(kernel, mm.companies[t])) is port)


def residual_demand(kernel: Any, port: Any, out: str, but: Optional[str] = None) -> float:
    """What the port takes off its shelves each quarter beyond what the makers already there can supply."""
    return max(0.0, demand(kernel, port, out) - capacity_at(kernel, port, out, but))


def working_need(kernel: Any, comp: Any) -> int:
    """The home cash a firm must keep to run a quarter: its plant's inputs at today's prices and its upkeep. Zero for
    a company that makes nothing."""
    rec = stats(kernel)["firms"].get(comp.ticker)
    planet = _firm_world(kernel, comp)
    port = _port(kernel, planet) if (rec is not None and planet is not None) else None
    if port is None:
        return 0
    econ = unit_economics(kernel, planet, port, rec["process"])
    cost = econ["cost"] if econ else 0.0
    return int(cost * rec["plant"] + upkeep_q(planet, rec["plant"]))


def upkeep_q(planet: Any, batches: float) -> float:
    """What a plant of this size costs to keep up for a quarter (its depreciation, paid to the contractors)."""
    return plant_cost(planet, batches) * (1 - (1 - DEPRECIATION_YEAR) ** (_quarter() / 100.0))


def convert(kernel: Any, comp: Any) -> Optional[str]:
    """A listed company with no operations puts its own cash to work: the best recipe at its home port, if a
    quarter's profit on the plant, as its world's council discounts it, beats the plant and a quarter's working
    cash. It keeps its ticker and its holders; it becomes a firm like any other."""
    from xylarium.kernel import liquidation
    planet = _firm_world(kernel, comp)
    port = _port(kernel, planet) if planet is not None else None
    if port is None:
        return None
    pick = best_recipe(kernel, planet, port)
    if pick is None:
        return None
    out, econ = pick
    fxm = kernel.fx_market
    rate = fxm.rate(planet.currency) if planet.currency != _hub() else 1.0
    have_sol = max(0, comp.treasury) + (fxm.to_sol_value(comp.home_currency, comp.home_cash)
                                        if (comp.home_currency and comp.home_currency != _hub()) else comp.home_cash)
    unit = plant_cost(planet, 1)
    batches = min(int(residual_demand(kernel, port, out)), int(have_sol * rate // max(1e-9, 2 * unit)))
    if batches < 1:
        return None
    m = decide.mind_of_planet(kernel, planet)
    worth = decide.worth(kernel, econ["margin"] * batches - upkeep_q(planet, batches), m, planet.currency)
    if decide.choose(kernel, [decide.option("convert_firm", 2 * plant_cost(planet, batches), worth,
                                            cash=2 * plant_cost(planet, batches), currency=planet.currency)], m,
                     comp.ticker, "convert") is None:
        return None
    # committed: its cash, all of it in its world's money - what it holds abroad comes home through the exchange
    if comp.home_cash > 0 and comp.home_currency and comp.home_currency != planet.currency:
        comp.home_cash, _ = fxm.convert(comp.home_currency, planet.currency, comp.home_cash)
    comp.home_currency = planet.currency
    if comp.treasury > 0:
        sol = comp.treasury
        comp.treasury = 0
        comp.home_cash += fxm.swap_sol_to(planet.currency, sol) if planet.currency != _hub() else sol
    batches = min(batches, int(comp.home_cash // max(1e-9, 2 * unit)))
    if batches < 1:
        return None                                      # the exchange gave less than it hoped: it tries again
    capital = plant_cost(planet, batches)
    comp.home_cash -= int(capital)
    port.treasury += int(capital)                       # the contractors build it
    comp.industry = "MANUFACTURING"
    stats(kernel)["firms"][comp.ticker] = {"process": out, "plant": float(batches), "founder": "company",
                                           "founder_shares": 0, "since": kernel.cycle_count, "losses": 0,
                                           "converted": True}
    liquidation.stats(kernel)["converted"] += 1
    return f"[ENTERPRISE] {comp.name} ({comp.ticker}) puts its cash to work: {batches} batches of {out} a quarter."


def rescue(kernel: Any, ticker: str, rec: Dict[str, Any]) -> Optional[str]:
    """A distressed firm's way out before the end: a sound rival of the same process and money buys its plant at
    auction value when, by its own council's mind, the plant's margin is worth the price. The seller is then
    wound up with the price in its estate - its holders paid, its loans called, its shorts closed."""
    from xylarium.kernel import liquidation
    mm = kernel.market_manager
    comp = mm.companies.get(ticker)
    planet = _firm_world(kernel, comp) if comp is not None else None
    port = _port(kernel, planet) if planet is not None else None
    if port is None or rec["plant"] < 1:
        return None
    econ = unit_economics(kernel, planet, port, rec["process"])
    if econ is None or econ["margin"] <= 0:
        return None                                      # no one buys a plant that cannot pay where it stands
    useful = min(rec["plant"], max(0.0, demand(kernel, port, rec["process"])
                                   - capacity_at(kernel, port, rec["process"], but=ticker)))
    if useful < 1:
        return None                                      # the market is served without it
    price = int(plant_cost(planet, useful) * 0.5)
    m = decide.mind_of_planet(kernel, planet)
    worth = decide.worth(kernel, econ["margin"] * useful - upkeep_q(planet, useful), m, planet.currency)
    for t, r in sorted(stats(kernel)["firms"].items(), key=lambda tr: -(mm.companies[tr[0]].home_cash
                                                                         if tr[0] in mm.companies else 0)):
        buyer = mm.companies.get(t)
        if (t == ticker or buyer is None or r["process"] != rec["process"] or buyer.home_currency != comp.home_currency
                or liquidation.distressed(kernel, t) or buyer.home_cash < price):
            continue
        if decide.choose(kernel, [decide.option("acquire_plant", price, worth)], m, t, ticker, "rescue") is None:
            return None
        buyer.home_cash -= price
        comp.home_cash += price
        r["plant"] += useful
        rec["plant"] = 0.0
        liquidation.stats(kernel)["rescued"] += 1
        founder = (planet, rec.get("founder_shares", 0)) if rec.get("founder") == "people" else None
        wound = liquidation.liquidate(kernel, ticker, "acquired", founder=founder, auction=f"plant to {buyer.name}")
        stats(kernel)["firms"].pop(ticker, None)
        return (f"[ENTERPRISE] {buyer.name} takes over {comp.name}'s plant; {comp.name} ({ticker}) is wound up "
                f"with {wound['paid_out_sol']:,.0f} SOL's worth to its holders.")
    return None


def _consider_founding(kernel: Any, planet: Any) -> Optional[str]:
    """The incorporation hurdle: found the best recipe at this port if a quarter's profit on its plant, as the
    council's mind discounts it, beats the plant's cost."""
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    if owner is not None and not getattr(owner, "is_ai", False):
        return None
    port = _port(kernel, planet)
    if port is None:
        return None
    pick = best_recipe(kernel, planet, port)
    if pick is None:
        return None
    out, econ = pick
    # an entrepreneur sizes its plant to what the port takes off its shelves each quarter beyond what the makers
    # already there supply: no one builds into a market already served
    batches = int(residual_demand(kernel, port, out))
    if batches < 1:
        return None
    capital = plant_cost(planet, batches) * 2           # plant and a quarter's working cash
    if planet.treasury < capital:
        return None
    m = decide.mind_of_planet(kernel, planet)
    worth = decide.worth(kernel, econ["margin"] * batches - upkeep_q(planet, batches), m, planet.currency)
    if decide.choose(kernel, [decide.option("found_firm", capital, worth, cash=capital, currency=planet.currency)],
                     m, planet.id, "found") is None:
        return None
    return found(kernel, planet, out, batches)


def _consider_growth(kernel: Any, comp: Any, rec: Dict[str, Any]) -> None:
    planet = _firm_world(kernel, comp)
    port = _port(kernel, planet) if planet is not None else None
    if port is None or rec.get("profit_q", 0) <= 0:
        return
    econ = unit_economics(kernel, planet, port, rec["process"])
    if econ is None or econ["margin"] <= 0 or econ["shelves"] <= rec["plant"]:
        return
    add = int(residual_demand(kernel, port, rec["process"], but=comp.ticker) - rec["plant"])
    if add < 1:
        return
    cost = plant_cost(planet, add)
    if comp.home_cash < cost * 2:
        return
    m = decide.mind_of_planet(kernel, planet)
    worth = decide.worth(kernel, econ["margin"] * add - upkeep_q(planet, add), m, planet.currency)
    if decide.choose(kernel, [decide.option("grow_firm", cost, worth, cash=cost, currency=planet.currency)], m,
                     comp.ticker, "grow") is None:
        return
    from xylarium.kernel.colony import ColonyManager
    comp.home_cash -= int(cost)
    port.treasury += int(cost)                          # the contractors build it
    rec["plant"] += add
    comp.level = min(4, 1 + int(math.log2(1 + rec["plant"] / 10)))
    stats(kernel)["expansions"] += 1


def quarter(kernel: Any) -> List[str]:
    st = stats(kernel)
    mm = kernel.market_manager
    logs: List[str] = []
    _smooth_demand(kernel)
    for ticker, rec in list(st["firms"].items()):
        comp = mm.companies.get(ticker)
        if comp is None:
            st["firms"].pop(ticker)
            continue
        profit = operate(kernel, comp, rec)
        from xylarium.kernel import liquidation
        if profit > 0 and not liquidation.distressed(kernel, ticker):     # a distressed firm rebuilds, it does not pay out
            _pay_out(kernel, comp, int(profit * DIVIDEND_SHARE), rec)
            comp.last_dividend = round(int(profit * DIVIDEND_SHARE) / max(1, comp.total_shares), 3)
            _consider_growth(kernel, comp, rec)
        if rec.get("losses", 0) >= RECEIVERSHIP_QUARTERS:
            logs.append(receivership(kernel, ticker, rec))
    if (kernel.cycle_count // _quarter()) % 4 == 0:     # councils weigh incorporating once a year
        have = {mm.companies[t].planet_id for t in st["firms"] if t in mm.companies}
        for sec in kernel.sectors.values():
            for p in sec.planets:
                if p.population > 0 and not getattr(p, "natives", None) and p.id not in have:
                    log = _consider_founding(kernel, p)
                    if log:
                        logs.append(log)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    by: Dict[str, int] = {}
    plant, made = 0.0, 0
    for r in st["firms"].values():
        by[r["process"]] = by.get(r["process"], 0) + 1
        plant += r["plant"]
        made += r.get("made", 0)
    return {"firms": len(st["firms"]), "by_process": by, "plant": round(plant, 1), "made": made,
            "founded": st["founded"], "expansions": st["expansions"], "bankrupt": st["bankrupt"],
            "imports": st.get("imports", 0),
            "failure_causes": dict(st.get("failure_causes", {}))}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="enterprise",
    state=lambda: {"firms": {}, "founded": 0, "expansions": 0, "bankrupt": 0},
    season=quarter,
    summary=summary,
))
