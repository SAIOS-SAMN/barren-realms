"""
Xylarium geology: what a world holds, what renews it, what wears it away - and what we take.

Every in-ground stock is a balance (stock next season = stock + sources - sinks - what is mined), and every
term is derived from the body's physics (physics.py): its mass (internal heat), its surface area, the light
it receives, and how tightly it holds on to gas (escape energy). The few chosen constants are named here.

  * Crust ore. A rocky world's accessible ore scales with its mass; giants have no crust to mine. Colonies
    mine it out of the ground (a transfer to the silo), so a mine face can run dry.
  * Tectonic renewal. Internal heat (mass; volcanic worlds twice over) slowly restores the crust toward its
    capacity - a thousand-year timescale for an Earth, far longer for a small dead rock.
  * Solar-wind helium-3. Airless surfaces soak up He-3 from their star's wind: implantation scales with the
    light received and the surface area, and saturates as the regolith fills.
  * Volatiles. Water, carbon and hydrogen escape from worlds that are hot for their gravity (loss ~ flux /
    escape energy - Jeans escape) and are outgassed by worlds with the internal heat for it (~ mass). Where
    both act, the stock settles at their balance.
  * Radioactive decay. Uranium decays wherever it is - in the ground, in reserves, in holds and warehouses -
    on a half-life. Nothing renews it: a finite stock, like the primordial helium of the giants.
"""

import math
from fractions import Fraction as F
from typing import Any, Dict, List

from xylarium.kernel import matter, physics

CRUST_ORE_PER_EARTH_MASS = 500_000_000   # accessible ore in an Earth-mass crust (a large colony mines it for centuries)
TECTONIC_RENEWAL_PER_YEAR = 0.001        # share of the crust's deficit an Earth's heat restores each year
HE3_REGOLITH_PER_AREA = 2_000            # He-3 a saturated regolith holds, per Earth-area
HE3_IMPLANT_PER_YEAR = 20                # He-3 implanted per Earth-area per year at Earth's light
VOLATILE_ESCAPE_PER_YEAR = 0.0005        # share of volatiles lost per year at flux 1 / escape energy 1
OUTGAS_PER_YEAR = 40                     # volatiles outgassed per Earth-mass per year by an active world...
VOLATILE_RESERVOIR_PER_EARTH_MASS = 20_000   # ...slowing as the surface holds what the mantle had to give
URANIUM_HALF_LIFE_YEARS = 400            # game half-life of the radioactives
TAILINGS_TOLERANCE_PER_AREA = 50_000     # tailings an Earth-area can absorb before it halves its living space
VOLATILES = ("H2O", "C", "H")

_SEASONS_PER_YEAR = 4


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "geology")["stats"]


def rocky(planet: Any) -> bool:
    return not physics.body(planet).get("giant")


def crust_capacity(planet: Any) -> int:
    if not rocky(planet):
        return 0
    return int(CRUST_ORE_PER_EARTH_MASS * float(physics.body(planet).get("mass", F(1))))


def airless(planet: Any) -> bool:
    b = physics.body(planet)
    return rocky(planet) and (planet.planet_type == "BARREN" or b.get("radius", F(1)) < F(2, 5))


def heat(planet: Any) -> float:
    """Internal heat relative to Earth: mass, doubled on volcanic worlds."""
    m = float(physics.body(planet).get("mass", F(1)))
    return m * (2.0 if planet.planet_type == "VOLCANIC" else 1.0)


def survey(kernel: Any) -> None:
    """Worlds whose crust has never been surveyed (genesis, new clusters, legacy saves) get it counted."""
    st = stats(kernel)
    for sec in kernel.sectors.values():
        if getattr(sec, "kind", "SYSTEM") != "SYSTEM":
            continue
        for p in sec.planets:
            if "ORE" in p.element_deposits or not getattr(p, "body", None):
                continue
            cap = crust_capacity(p)
            p.element_deposits["ORE"] = cap
            if cap:
                matter.source("planetary_survey", "ORE", cap)
                st["surveyed"] += cap


def mine_crust(planet: Any, want: int) -> int:
    """Ore out of the ground into the colony's silo (a transfer: the crust is in the census)."""
    if "ORE" not in planet.element_deposits:
        # an unsurveyed world (created mid-cycle): its mine face works as before and is declared
        return matter.produce(planet, "ore_silo", "ORE", want, "mine_face")
    take = max(0, min(want, planet.element_deposits["ORE"]))
    planet.element_deposits["ORE"] -= take
    planet.ore_silo += take
    from xylarium.kernel import ledger
    k = ledger.active_kernel()
    if k is not None:
        stats(k)["crust_mined"] += take
    return take


def landfill(kernel: Any) -> None:
    """Recycling's tailings go into the ground of the port's region (its own system's first world, else the
    nearest world of its money): counted as in-ground TAILINGS, weighing on that world's carrying capacity."""
    from xylarium.kernel.colony import ColonyManager
    st = stats(kernel)
    for sec in kernel.sectors.values():
        port = sec.port
        if port is None or port.stock.get("TAILINGS", 0) <= 0:
            continue
        world = next((p for p in sec.planets if getattr(p, "body", None)), None)
        if world is None:
            continue
        q = port.stock.pop("TAILINGS")
        from xylarium.kernel import biosphere, sustenance
        k0 = biosphere.carrying_capacity(kernel, world) if world.population > 0 else 0
        world.element_deposits["TAILINGS"] = world.element_deposits.get("TAILINGS", 0) + q
        if k0 > 0:                                 # the room for life its waste takes from its world
            sustenance.flow_civ(world, dark=k0 * (1.0 - float(pollution_factor(world)) /
                                                    max(1e-12, float(_pf_without(world, q)))))
        st["landfilled"] = st.get("landfilled", 0) + q


def _pf_without(planet: Any, q: int) -> float:
    """The pollution factor before `q` more tailings were landfilled."""
    t = max(0, planet.element_deposits.get("TAILINGS", 0) - q)
    area = float(physics.surface_area(planet)) or 1.0
    return 1.0 / (1.0 + t / (area * TAILINGS_TOLERANCE_PER_AREA))


def pollution_factor(planet: Any) -> float:
    """Living space left by landfilled tailings: 1 / (1 + tailings / (area x tolerance))."""
    t = planet.element_deposits.get("TAILINGS", 0) if hasattr(planet, "element_deposits") else 0
    if t <= 0:
        return 1.0
    area = float(physics.surface_area(planet)) or 1.0
    return 1.0 / (1.0 + t / (area * TAILINGS_TOLERANCE_PER_AREA))


def quarter(kernel: Any) -> None:
    """One season of the worlds' own processes."""
    st = stats(kernel)
    survey(kernel)
    landfill(kernel)
    decay_share = 1.0 - 0.5 ** (1.0 / (URANIUM_HALF_LIFE_YEARS * _SEASONS_PER_YEAR))
    carry = state.of(kernel, "geology")["decay_carry"]
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if getattr(p, "body", None) and getattr(sec, "kind", "SYSTEM") == "SYSTEM":
                _world_season(kernel, sec, p, st)
            for store, label in ((p.element_deposits, f"g:{p.id}"), (p.element_reserves, f"r:{p.id}")):
                _decay(store, "U", decay_share, carry, label, st)
        if sec.port is not None:
            _decay(sec.port.stock, "U", decay_share, carry, f"p:{sec.id}", st)
    for cap in kernel.captains.values():
        _decay(cap.ship.cargo.elements, "U", decay_share, carry, f"c:{cap.id}", st)


def _world(kernel: Any, sec: Any, p: Any) -> Dict[str, Any]:
    """A world's fixed physics for its season: changed only by its body, its kind, its star's swelling or the
    arrays that shade it."""
    from xylarium.kernel import cache, cosmos, harvest

    def compute() -> Dict[str, Any]:
        return {"cap": crust_capacity(p), "heat": heat(p), "flux": float(physics.planet_flux(sec, p)),
                "area": float(physics.surface_area(p)), "airless": airless(p), "rocky": rocky(p),
                "esc": float(physics.escape_energy(p)) if rocky(p) else 0.0}
    if not hasattr(kernel, "caches"):
        return compute()
    stamp = (p.planet_type, str(getattr(p, "body", None)), cosmos.lum(sec.id), harvest.shade(sec.id))
    return cache.stamped(kernel, "geology_world", p.id, stamp, compute)


def _world_season(kernel: Any, sec: Any, p: Any, st: Dict[str, Any]) -> None:
    deposits = p.element_deposits
    season = 1.0 / _SEASONS_PER_YEAR
    w = _world(kernel, sec, p)
    # Tectonic renewal toward crust capacity
    cap = w["cap"]
    if cap and "ORE" in deposits and deposits["ORE"] < cap:
        grow = int((cap - deposits["ORE"]) * TECTONIC_RENEWAL_PER_YEAR * w["heat"] * season)
        if grow > 0:
            deposits["ORE"] += grow
            matter.source("tectonic_renewal", "ORE", grow)
            st["renewed"] += grow
    flux = w["flux"]
    area = w["area"]
    # Solar-wind He-3 into airless regolith
    if w["airless"]:
        cap3 = HE3_REGOLITH_PER_AREA * area
        have = deposits.get("He-3", 0)
        if have < cap3:
            add = int(HE3_IMPLANT_PER_YEAR * flux * area * season * (1.0 - have / cap3))
            if add > 0:
                deposits["He-3"] = have + add
                matter.source("solar_wind", "He-3", add)
                st["implanted"] += add
    # Volatiles: Jeans escape vs outgassing
    if w["rocky"]:
        esc = w["esc"] or 1e-6
        loss_share = min(1.0, VOLATILE_ESCAPE_PER_YEAR * flux / esc * season)
        outgas = int(OUTGAS_PER_YEAR * w["heat"] * season) if (p.planet_type == "VOLCANIC" or w["heat"] >= 1.0) else 0
        for v in VOLATILES:
            have = deposits.get(v, 0)
            lost = int(have * loss_share)
            if lost > 0:
                deposits[v] = have - lost
                matter.sink("atmospheric_escape", v, lost)
                st["escaped"] += lost
            if outgas > 0 and v in ("H2O", "C"):
                reservoir = VOLATILE_RESERVOIR_PER_EARTH_MASS * w["heat"]
                outgas_v = int(outgas * max(0.0, 1.0 - deposits.get(v, 0) / reservoir))
                if outgas_v <= 0:
                    continue
                deposits[v] = deposits.get(v, 0) + outgas_v
                matter.source("outgassing", v, outgas_v)
                st["outgassed"] += outgas_v


def _decay(store: Dict[str, int], elem: str, share: float, carry: Dict[str, float], label: str,
           st: Dict[str, Any]) -> None:
    q = store.get(elem, 0)
    if q <= 0:
        return
    exact = q * share + carry.get(label, 0.0)
    gone = min(q, int(exact))
    carry[label] = exact - gone
    if gone > 0:
        store[elem] = q - gone
        if store[elem] <= 0:
            store.pop(elem, None)
        matter.sink("radioactive_decay", elem, gone)
        st["decayed"] += gone


def horizons(kernel: Any) -> Dict[str, Any]:
    """Observations: how the worlds' crusts are holding up (years until the mined ones run dry)."""
    st = stats(kernel)
    mined_worlds = []
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population > 0 and "ORE" in p.element_deposits and crust_capacity(p):
                mined_worlds.append(p.element_deposits["ORE"] / crust_capacity(p))
    extraction = st["crust_mined"] or 1
    return {"crust_remaining_mean": round(sum(mined_worlds) / len(mined_worlds), 3) if mined_worlds else None,
            "crust_remaining_min": round(min(mined_worlds), 3) if mined_worlds else None,
            "renewal_to_extraction": round(st["renewed"] / extraction, 4),
            "stats": dict(st)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402


def _season(kernel: Any) -> List[str]:
    quarter(kernel)
    return []


register_subsystem(Subsystem(
    name="geology",
    state=lambda: {"stats": {"crust_mined": 0, "renewed": 0, "implanted": 0, "escaped": 0, "outgassed": 0,
                             "decayed": 0, "surveyed": 0},
                   "decay_carry": {}},
    season=_season,
    summary=lambda kernel: horizons(kernel),
))
