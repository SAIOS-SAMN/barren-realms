"""
Xylarium energy: every unit of energy comes from somewhere, goes somewhere, and is traded where it is made.

UNITS. One energy unit (EU) is a millionth of the sunlight a world at 1 AU from a solar-luminosity star receives
on an Earth's area in a season - a ruler, as the AU and the Earth mass are rulers. A person is the other ruler: one
person's tools draw PERSON_EU a season before its people has learned anything of energy. Nothing else about Earth
is assumed - not how much energy its peoples use, not what they burn first, not how much heat its core can spare.
The ledger is kept in integer milli-EU (mEU) so that it balances exactly.

THE LEDGER (as matter.py for goods, ledger.py for money). Stocks are the energy held in worlds' grids. Every change
is a declared source (combustion, collected sunlight, core heat drawn, beamed array power) or a declared sink (what
a people uses, what is lost in transmission, what is packed into fuel, what is dissipated as waste heat). For every
world and in total: the change in stored energy equals sources minus sinks. tools/live.py audits it every quarter.

NEED. A pre-industrial people runs on muscle and its biosphere - outside the ledger. What a world needs is what its
own people does, derived from its physics and its knowledge:
  * industry - the industrial share of its economy (1 - 2^-tier: a citadel tier halves the share still worked by
    hand) x a person's ruler draw x its people's efficiency, which improves along the learning curve with what it
    knows of energy (laws.wright): a people that has learned much does the same work on a fraction of the energy;
  * life support - holding its people at the temperature its biology is tuned to on a world that is not: the
    thermal gap |ln(T_world / T_tuned)| (a quarter of the light mismatch its genome has not closed) per person.
    On the world a people evolved for it is nothing; on a hostile colony it can exceed its industry.
A world short of energy loses the share of its industrial output it could not power.

SUPPLY (harvest.py builds the installations, each people to its own design):
  * combustion - the carbon a world has refined (1 EU a unit) - only where a biosphere has made the oxidiser to burn
    it in (carbon life, under air): a cryogenic or lithic people never meets fire, a plasmic one never needs it;
  * surface collectors - fields of 1e-4 of an Earth's surface: light x area x efficiency, halved by night and
    dimmed by air;
  * core taps - each draws a twentieth of the world's core heat flow through a heat engine;
  * stellar arrays - collectors in orbit at the star's inner edge, beamed to their owners' worlds.

MARKETS. Each season energy clears first where it is made: within each system, worlds with surplus sell to worlds
short of it, at the price between what the buyer loses without it and what the seller could make of it otherwise.
What a system cannot use is then bridged - beamed over the lanes to the systems of its own people, its family
(patrons and tributaries, relations.py), and the peoples aligned with it (not at war, alignment within the
galaxy's own spread), losing 1 - 1/(1+hops)^2 on the way. Payment is a transfer between treasuries through the
exchange.

FUEL. What is still left after the markets is packed into fuel: hydrogen by electrolysis of water first (2 EU a
unit, a declared conversion H2O -> H), then antimatter (1000 EU a unit at full mastery of pair production, dearer
the less a people knows; a declared source of AM), the fuel of the deepest drives. Fuel is sold through the ports like any good. The rest is waste
heat.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import COMMODITY_CONFIG, PRICE_LEVEL

MILLI = 1000                       # the ledger counts milli-EU
TERRA_INSOLATION = 1_000_000       # EU a season: the unit's definition
EARTH_CORE_FLOW = TERRA_INSOLATION * 10 / 173_000      # EU a season through an Earth-mass core-mantle boundary
PERSON_EU = 1.05e-3                # the ruler: EU a season one person's tools draw before any mastery of energy
CARBON_EU = 1.0                    # EU a unit of refined carbon burned
ELECTROLYSIS_EU = 2.0              # EU to split a unit of water into a unit of hydrogen fuel
ANTIMATTER_EU = 1000.0             # EU packed into a unit of antimatter
GRID_SEASONS = 1                   # a grid holds a season of its world's need


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "energy")


def _ledger(kernel: Any) -> Dict[str, Dict[str, int]]:
    st = stats(kernel)
    return st["ledger"]


def source(kernel: Any, kind: str, meu: int) -> None:
    if meu:
        led = _ledger(kernel)["sources"]
        led[kind] = led.get(kind, 0) + int(meu)


def sink(kernel: Any, kind: str, meu: int) -> None:
    if meu:
        led = _ledger(kernel)["sinks"]
        led[kind] = led.get(kind, 0) + int(meu)


def stored(kernel: Any) -> int:
    """Every milli-EU held: the worlds' grids and the charge building in their antimatter traps."""
    return sum(int(p.society.get("grid_meu", 0)) + int(p.society.get("am_charge_meu", 0))
               for s in kernel.sectors.values() for p in s.planets)


def declared(kernel: Any) -> int:
    led = _ledger(kernel)
    return sum(led["sources"].values()) - sum(led["sinks"].values())


def residual(kernel: Any) -> int:
    """Stored minus declared: zero while the law holds."""
    if "energy" not in getattr(kernel, "state", {}):
        return 0
    return stored(kernel) - declared(kernel) - stats(kernel)["baseline"]


# ---------------------------------------------------------------------- need and the value of energy
def tier(planet: Any) -> int:
    return int(getattr(planet, "citadel_level", 0) or 0)


def _k(kernel: Any = None) -> Any:
    if kernel is not None:
        return kernel
    from xylarium.kernel import ledger
    return ledger.active_kernel()


def efficiency(kernel: Any, planet: Any) -> float:
    """The share of the ruler draw a person's tools need, at what its people knows of energy (Wright's curve)."""
    from xylarium.kernel import knowledge, laws
    from xylarium.config import KNOWLEDGE_UNIT
    k = _k(kernel)
    if k is None or "knowledge" not in getattr(k, "state", {}):
        return 1.0
    return laws.wright(knowledge.experience(k, knowledge.holder_of_planet(planet), "energy"), KNOWLEDGE_UNIT)


def thermal_gap(kernel: Any, planet: Any) -> float:
    """|ln(T_world / T_tuned)|: a quarter of the light mismatch its people's genome has not closed (T ~ flux^1/4)."""
    from xylarium.kernel import genome
    k = _k(kernel)
    if k is None:
        return 0.0
    x0 = genome._flux_ratio(k, planet)
    if x0 is None or x0 <= 0:
        return 0.0
    return abs(math.log(x0) - genome.value(planet, "light")) / 4.0


def per_capita(planet: Any, kernel: Any = None) -> float:
    t = tier(planet)
    if t <= 0:
        return 0.0
    return PERSON_EU * (industry_share(planet) * efficiency(kernel, planet) + thermal_gap(kernel, planet))


def need_eu(planet: Any, kernel: Any = None) -> float:
    return planet.population * per_capita(planet, kernel)


def industry_share(planet: Any) -> float:
    return 1.0 - 2.0 ** (-tier(planet))


def output_factor(planet: Any) -> float:
    """What share of its economy a world can run on the energy it had last season."""
    s = planet.society.get("energy_sufficiency")
    if s is None:
        return 1.0
    return 1.0 - industry_share(planet) * (1.0 - float(s))


def value_short(planet: Any) -> float:
    """What a missing EU costs this world a season (local money): its industrial output per EU it needs."""
    from xylarium.kernel.demography import _tax_per_head_quarter
    need = need_eu(planet)
    if need <= 0:
        return 0.0
    return industry_share(planet) * planet.population * _tax_per_head_quarter(planet) / need


def value_surplus(planet: Any) -> float:
    """What a spare EU is worth to this world (local money): the hydrogen it could make of it - nothing at the
    margin if it already had energy to throw away last season (its water ran out, or no one would buy)."""
    if planet.society.get("dissipated_meu", 0) > 0 or planet.element_reserves.get("H2O", 0) <= 0:
        return 0.0
    price = COMMODITY_CONFIG.get("H", {}).get("base_price", 12) * PRICE_LEVEL.get(planet.currency, 1.0)
    return price / ELECTROLYSIS_EU


# ---------------------------------------------------------------------- the season
def _peopled(kernel: Any) -> List[Any]:
    return [p for s in kernel.sectors.values() for p in s.planets
            if p.population > 0 and not getattr(p, "natives", None)]


def _people(planet: Any) -> Optional[str]:
    from xylarium.kernel import sustenance
    return sustenance.people_of(planet)


def _alignment(kernel: Any, planet: Any) -> float:
    from xylarium.kernel import sustenance
    return sustenance._alignment(kernel, planet)


def burns(kernel: Any, planet: Any) -> bool:
    """Fire needs an oxidiser, and only a photosynthetic biosphere under air makes one."""
    from xylarium.kernel import biosphere, geology
    return biosphere.metabolism_of(kernel, planet) in ("biotic", "umbral") and not geology.airless(planet)


def supply(kernel: Any, planet: Any) -> Dict[str, int]:
    """This season's generation at a world, in mEU, by source (harvest.py's installations, the world's carbon)."""
    from xylarium.kernel import harvest
    out = {k: int(v * MILLI) for k, v in harvest.generation(kernel, planet).items() if v > 0}
    need = need_eu(planet, kernel)
    short = need - sum(out.values()) / MILLI
    if short > 0 and tier(planet) >= 1 and burns(kernel, planet):
        burn = min(int(math.ceil(short / CARBON_EU)), int(planet.element_reserves.get("C", 0)))
        if burn > 0:
            from xylarium.kernel import matter
            planet.element_reserves["C"] -= burn
            matter.sink("combustion", "C", burn)
            out["combustion"] = int(burn * CARBON_EU * MILLI)
    return out


def season(kernel: Any) -> List[str]:
    st = stats(kernel)
    logs: List[str] = []
    worlds = _peopled(kernel)
    from xylarium.kernel import harvest
    arrays = harvest.array_output(kernel)               # (owner people, sector) -> mEU at the star
    book: Dict[str, Dict[str, float]] = {}
    for p in worlds:
        gen = supply(kernel, p)
        for kind, meu in gen.items():
            source(kernel, kind, meu)
        grid = int(p.society.get("grid_meu", 0)) + sum(gen.values())
        need = int(need_eu(p, kernel) * MILLI)
        book[p.id] = {"planet": p, "grid": grid, "need": need, "used": 0}
    # stellar arrays beam to their owners' worlds in their own systems first (no loss), then over the lanes
    for (owner, sid), meu in arrays.items():
        source(kernel, "stellar_array", meu)
        homes = [b for b in book.values() if _people(b["planet"]) == owner]
        if not homes:
            sink(kernel, "dissipated", meu)
            continue
        local = [b for b in homes if b["planet"].sector_id == sid]
        targets = local or homes
        each = meu // len(targets)
        rest = meu - each * len(targets)
        for b in targets:
            hops = 0 if local else _hops(kernel, sid, b["planet"].sector_id)
            kept = int(each / (1.0 + hops) ** 2)
            sink(kernel, "transmission", each - kept)
            b["grid"] += kept
        sink(kernel, "dissipated", rest)
    # every world uses what it needs from its own grid
    for b in book.values():
        use = min(b["grid"], b["need"])
        b["grid"] -= use
        b["used"] = use
        sink(kernel, "industry", use)
    # markets: local, then bridged to allied and aligned
    _clear_local(kernel, book)
    _bridge(kernel, book)
    # what is left: stored up to a season of need, then packed into fuel, then waste heat
    for b in book.values():
        p = b["planet"]
        cap = max(int(GRID_SEASONS * b["need"]), 0)
        spare = max(0, b["grid"] - cap)
        if spare > 0:
            packed = _pack_fuel(kernel, p, spare)
            b["grid"] -= packed
            spare -= packed
        if spare > 0:
            sink(kernel, "dissipated", spare)
            b["grid"] -= spare
        p.society["dissipated_meu"] = int(max(0, spare))
        p.society["grid_meu"] = int(b["grid"])
        if b["need"] > 0:
            p.society["energy_sufficiency"] = round(min(1.0, (b["used"] + b.get("bought", 0)) / b["need"]), 4)
        else:
            p.society.pop("energy_sufficiency", None)
    st["seasons"] += 1
    return logs


def _hops(kernel: Any, a: int, b: int) -> int:
    from xylarium.kernel import topology
    if a == b:
        return 0
    return topology.hops(kernel, a, 12).get(b, 12)


def _pay(kernel: Any, buyer: Any, seller: Any, amount_local: float) -> int:
    """The buyer's vault pays the seller's in the buyer's money, converted through the exchange: a transfer."""
    amount = int(min(amount_local, max(0, buyer.treasury)))
    if amount <= 0:
        return 0
    buyer.treasury -= amount
    if buyer.currency == seller.currency:
        seller.treasury += amount
    else:
        got, _ = kernel.fx_market.convert(buyer.currency, seller.currency, amount)
        seller.treasury += got
    return amount


def _trade(kernel: Any, sb: Dict[str, Any], bb: Dict[str, Any], meu: int, loss: float, kind: str) -> int:
    """Move up to `meu` from seller's grid to buyer's need, losing `loss` of it on the way; the buyer pays the
    price between its value of the energy and the seller's (each in its own terms, converted at the mid rate)."""
    s, b = sb["planet"], bb["planet"]
    want = bb["need"] - bb["used"] - bb.get("bought", 0)
    if want <= 0 or meu <= 0:
        return 0
    send = min(meu, int(math.ceil(want / max(1e-9, 1.0 - loss))))
    arrive = int(send * (1.0 - loss))
    if arrive <= 0:
        return 0
    v_buy = value_short(b)                                         # buyer's money per EU
    v_sell = value_surplus(s)                                      # seller's money per EU
    fxm = kernel.fx_market
    v_sell_in_buyer = (fxm.to_sol_value(s.currency, v_sell) if s.currency != "SOL" else v_sell) * \
        (fxm.rate(b.currency) if b.currency != "SOL" else 1.0)
    if v_buy * (1.0 - loss) <= v_sell_in_buyer:
        return 0                                                   # after the beam's losses it is worth more where it is
    price = 0.5 * (v_buy + v_sell_in_buyer)
    paid = _pay(kernel, b, s, price * arrive / MILLI)
    if paid <= 0:
        return 0
    arrive = min(arrive, int(paid / max(1e-9, price) * MILLI))
    send = int(math.ceil(arrive / max(1e-9, 1.0 - loss)))
    send = min(send, sb["grid"])
    arrive = min(arrive, int(send * (1.0 - loss)))
    sb["grid"] -= send
    sink(kernel, "transmission", send - arrive)
    bb["bought"] = bb.get("bought", 0) + arrive
    sink(kernel, "industry", arrive)
    st = stats(kernel)
    st["traded"][kind] = st["traded"].get(kind, 0) + arrive
    return arrive


def _clear_local(kernel: Any, book: Dict[str, Dict[str, Any]]) -> None:
    by_sec: Dict[int, List[Dict[str, Any]]] = {}
    for b in book.values():
        by_sec.setdefault(b["planet"].sector_id, []).append(b)
    for books in by_sec.values():
        sellers = [b for b in books if b["grid"] > 0]
        buyers = sorted((b for b in books if b["need"] > b["used"]), key=lambda b: -value_short(b["planet"]))
        for bb in buyers:
            for sb in sellers:
                if sb is bb or sb["grid"] <= 0:
                    continue
                _trade(kernel, sb, bb, sb["grid"], 0.0, "local")


def _aligned(kernel: Any, a: Any, b: Any, spread: float) -> bool:
    from xylarium.kernel import relations, sustenance
    pa, pb = _people(a), _people(b)
    if pa == pb or relations.family(kernel, pa, pb):
        return True
    wars = sustenance.stats(kernel).get("wars", {})
    if f"{pa}>{pb}" in wars or f"{pb}>{pa}" in wars:
        return False
    return abs(_alignment(kernel, a) - _alignment(kernel, b)) <= spread


def _bridge(kernel: Any, book: Dict[str, Dict[str, Any]]) -> None:
    """A system's spare energy is beamed to allied and aligned markets within its sellers' reach."""
    from xylarium.kernel import sustenance
    sellers = [b for b in book.values() if b["grid"] > 0 and sustenance.yards(b["planet"])]
    buyers = [b for b in book.values() if b["need"] > b["used"] + b.get("bought", 0)]
    if not sellers or not buyers:
        return
    aligns = [_alignment(kernel, b["planet"]) for b in book.values()]
    mean = sum(aligns) / len(aligns)
    spread = math.sqrt(sum((x - mean) ** 2 for x in aligns) / len(aligns)) if aligns else 0.0
    for sb in sellers:
        from xylarium.kernel import relations
        reach = relations._reach_map(kernel, sb["planet"])
        options = [(reach[bb["planet"].sector_id], bb) for bb in buyers
                   if bb is not sb and bb["planet"].sector_id in reach
                   and bb["planet"].sector_id != sb["planet"].sector_id
                   and _aligned(kernel, sb["planet"], bb["planet"], spread)]
        for hops, bb in sorted(options, key=lambda t: (t[0], -value_short(t[1]["planet"]))):
            if sb["grid"] <= 0:
                break
            loss = 1.0 - 1.0 / (1.0 + hops) ** 2
            kind = "allied" if relations.family(kernel, _people(sb["planet"]), _people(bb["planet"])) \
                or _people(sb["planet"]) == _people(bb["planet"]) else "aligned"
            _trade(kernel, sb, bb, sb["grid"], loss, kind)


def _pack_fuel(kernel: Any, planet: Any, meu: int) -> int:
    """Spare energy packed into fuel: hydrogen from the world's water first (it is worth more per EU), then what is
    still spare into antimatter - at ANTIMATTER_EU / mastery a unit: any people that has begun to learn pair
    production can make it, the less it knows the dearer."""
    from xylarium.kernel import knowledge, matter
    used = 0
    water = int(planet.element_reserves.get("H2O", 0))
    n = min(int(meu // int(ELECTROLYSIS_EU * MILLI)), water)
    if n > 0:
        planet.element_reserves["H2O"] = water - n
        planet.element_reserves["H"] = planet.element_reserves.get("H", 0) + n
        matter.sink("electrolysis", "H2O", n)
        matter.source("electrolysis", "H", n)
        spend = n * int(ELECTROLYSIS_EU * MILLI)
        sink(kernel, "electrolysis", spend)
        used += spend
        stats(kernel)["hydrogen"] += n
    mastered = knowledge.mastery(kernel, knowledge.holder_of_planet(planet), "antimatter")
    if mastered > 1e-6 and meu - used > 0:
        # the spare builds a charge in the world's trap, season over season, until a unit can be made
        per = int(ANTIMATTER_EU / mastered * MILLI)
        charge = int(planet.society.get("am_charge_meu", 0)) + (meu - used)
        used = meu
        n = charge // per
        if n > 0:
            planet.element_reserves["AM"] = planet.element_reserves.get("AM", 0) + n
            matter.source("pair_production", "AM", n)
            sink(kernel, "antimatter", n * per)
            charge -= n * per
            stats(kernel)["antimatter"] += n
        planet.society["am_charge_meu"] = int(charge)
    return used


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    led = st["ledger"]
    worlds = [p for p in _peopled(kernel) if need_eu(p) > 0]
    suff = [float(p.society.get("energy_sufficiency", 1.0)) for p in worlds]
    return {"stored_eu": round(stored(kernel) / MILLI, 1),
            "sources_eu": {k: round(v / MILLI) for k, v in led["sources"].items()},
            "sinks_eu": {k: round(v / MILLI) for k, v in led["sinks"].items()},
            "traded_eu": {k: round(v / MILLI) for k, v in st["traded"].items()},
            "mean_sufficiency": round(sum(suff) / len(suff), 3) if suff else 1.0,
            "short_worlds": sum(1 for x in suff if x < 0.99),
            "hydrogen": st["hydrogen"], "antimatter": st["antimatter"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="energy",
    state=lambda: {"ledger": {"sources": {}, "sinks": {}}, "baseline": 0, "traded": {}, "seasons": 0,
                   "hydrogen": 0, "antimatter": 0},
    season=season,
    summary=summary,
))
