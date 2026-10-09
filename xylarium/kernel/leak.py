"""
Xylarium leak: the ancients' air leaks, they replace it from their survival basket, and the mu they hold on a world
dissipates as that world loses its matter (operator rulings, 2026-10-09).

  THE LEAK     every world loses its air to space as its own physics says: the escape and the photochemical
               stripping its star drives, less what its interior outgasses (worlds.build). Its rate now is read off
               the world's own model as it ages: its standing air's mass when last read and now, over the years
               between - kg a year, exact on the grid (the model the world's other laws read: never a build of its
               own). A world gaining air leaks nothing.
  THE BASKET   the ancients hold the air their lineage rose in. Each season an ancients' world takes, from its own
               stores of its medium's good (uses.medium: water for a water people, cryogenite - ammonia - for an
               ammonia people), the mass its air lost since, a hold slot's mass a unit (cargo.unit_kg); and it keeps
               a season's loss in store (keep_units: staples.reserve), the want the trade its line's stewards broker
               fills from the rim - the progenitors' convoys, earning their roads' tolls. What its
               stores cannot cover is air it no longer holds: the share of its native air it stands in falls (the
               world's atmosphere, which bounds what its land can feed). It never falls below what its world would
               hold untended - the model's own air at its age, over the air it held when first read: untended is the
               natural path, however the clock is stepped.
  DEMURRAGE    mu held in a vault on a world dissipates at the rate that world loses its air (the leak over its
               standing air, a share a year): a world that holds its air holds its mu. Dissipation RECYCLES
               (operator, Concordance 5.8): its VALUE goes to the hypha as the connection tax, a transfer from the
               domain reserve (owed here until the hypha's fold flow, 78.154, takes it - never a burn); its MATTER
               stays where it dissipated as INVERSE-MU - mass without mu's value, held at its world with that
               place's coordinate and properties (its star's absorbed quantum flux), for physics to take up as matter;
               it is mu again only by judged work. Mu on the hypha (staked or escrowed) is not here and does not decay.

Only the ancients consume their basket for their air (the ruling), at the worlds they live as ancients: each house's
home (its basket is read at its home) and the world its vault stands on. Every other world's air follows its model.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional

G0 = 9.80665                    # standard gravity, m/s^2 (a world's g is in Earth's)
R_EARTH_M = 6.371e6
BAR_PA = 1.0e5


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "leak")


def _grid(x: float) -> Fraction:
    from xylarium.kernel import field
    return field.grid(x)


def air_kg(world: Dict[str, Any]) -> Dict[str, float]:
    """A world model's standing air by species, in kg: each partial pressure's column (p / g) over the whole sphere."""
    radius = float(world.get("radius") or 1.0)
    g = float(world.get("g") or (float(world.get("mass") or 1.0) / max(1e-9, radius) ** 2)) * G0
    area = 4.0 * 3.141592653589793 * (radius * R_EARTH_M) ** 2
    return {sp: float(pp) * BAR_PA / max(1e-9, g) * area for sp, pp in (world.get("air") or {}).items()}


def rate(kernel: Any, planet: Any) -> Dict[str, Any]:
    """The world's air and how fast it loses it now: {"air_kg", "kg_yr" (net, >= 0), "share_yr"} - read off its own
    model as it ages: the standing air at the age it was last read and at its age now (worlds.state_of_planet, which
    the world's other laws read too - no model is built for this alone), over the years between. Until its model has
    aged a step since first read, it has no rate yet (0)."""
    from xylarium.kernel import worlds
    s = worlds.state_of_planet(kernel, planet)
    age = float(s["args"][8])
    air = sum(air_kg(s["world"]).values())
    got = planet.society.get("_leak")
    if got and got.get("age") == age:
        return got
    out = {"age": age, "air_kg": str(_grid(air)), "kg_yr": "0", "share_yr": "0"}
    if got and float(got["age"]) < age:
        lost = max(0.0, float(Fraction(got["air_kg"])) - air) / ((age - float(got["age"])) * 1e9)
        out.update(kg_yr=str(_grid(lost)), share_yr=str(_grid(lost / air)) if air > 0 else "0")
    elif got:
        out.update(kg_yr=got["kg_yr"], share_yr=got["share_yr"])
    planet.society["_leak"] = out
    return out


def _years(kernel: Any, planet: Any, rec: Dict[str, Any]) -> Fraction:
    """Its own years since it was last read (its place's clock)."""
    from xylarium.kernel import cosmos
    now = Fraction(cosmos.deep_gyr(kernel, sector_id=planet.sector_id)) if cosmos.is_cosmic(kernel) else \
        Fraction(kernel.cycle_count, 100) / 10 ** 9
    last = Fraction(rec.get("t", str(now)))
    rec["t"] = str(now)
    return max(Fraction(0), (now - last) * 10 ** 9)


def hold(kernel: Any, planet: Any) -> Dict[str, Any]:
    """A season of an ancients' world holding its air: the leak since it was last read, replaced from its stores of
    its medium's good as far as they go; what they cannot cover lowers the share of its native air it holds, never
    below its untended path. Returns its record."""
    from xylarium.kernel import cargo, imprint, staples, uses
    soc = planet.society
    rec = soc.setdefault("air_hold", {})
    r = rate(kernel, planet)
    air_now = Fraction(r["air_kg"])
    if "native_kg" not in rec:                                 # the air its lineage holds: as first read
        rec.update(native_kg=r["air_kg"], held_kg=r["air_kg"], consumed_kg="0", short_kg="0")
        _years(kernel, planet, rec)
        return rec
    years = _years(kernel, planet, rec)
    rec["years_last"] = str(years)                             # a season's span, for what it keeps against the next
    native, held = Fraction(rec["native_kg"]), Fraction(rec["held_kg"])
    lost = Fraction(r["kg_yr"]) * years
    want = min(lost, native - held + lost)                    # replace what it lost, up to its native air
    good = uses.medium(kernel, planet)
    each = cargo.unit_kg(good) if good else None
    got_kg = Fraction(0)
    if want > 0 and each:
        carry = Fraction(rec.get("carry_kg", "0"))
        units = int((want - carry) // each) + (1 if (want - carry) % each else 0) if want > carry else 0
        taken = staples.take(planet, good, units, "atmosphere") if units else 0
        got_kg = min(want, carry + taken * each)
        rec["carry_kg"] = str(carry + taken * each - got_kg)    # a slot's remainder held for the next season
    held = held - lost + got_kg
    floor = air_now if native > 0 else Fraction(0)            # untended: the world's own air at its age
    held = min(native, max(floor, held))
    rec["consumed_kg"] = str(Fraction(rec["consumed_kg"]) + got_kg)
    rec["short_kg"] = str(Fraction(rec["short_kg"]) + max(Fraction(0), want - got_kg))
    was = Fraction(rec["held_kg"]) / native if native > 0 else Fraction(1)
    rec["held_kg"] = str(held)
    share = held / native if native > 0 else Fraction(1)
    if share != was:                                           # the air it stands in moved: the world's atmosphere
        imprint.record(kernel, planet, "air_leak", None, air_add=float(share - was))
    return rec


def keep_units(kernel: Any, planet: Any, comm: str) -> int:
    """What an ancients' world keeps of its medium's good against its leak: a season's loss at its rate now, in
    units - its want, which the trade its line's stewards broker brings in from the rim (commerce: the progenitors'
    convoys, paying their roads' tolls). Nothing for any other world or good."""
    from xylarium.kernel import cargo, uses
    rec = (getattr(planet, "society", None) or {}).get("air_hold")
    if not rec or "years_last" not in rec or comm != uses.medium(kernel, planet):
        return 0
    each = cargo.unit_kg(comm)
    r = (planet.society.get("_leak") or {})
    need = Fraction(r.get("kg_yr", "0")) * Fraction(rec["years_last"])
    if not each or need <= 0:
        return 0
    return int(need // each) + (1 if need % each else 0)


def demurrage(kernel: Any, house: str, years: Fraction) -> List[Fraction]:
    """The mu a house's bank holds dissipates at its vault world's air-loss share a year. What dissipates is split
    exactly: its value owed to the hypha as the connection tax, its matter left at the vault world as inverse-mu with
    the place's coordinate and properties. Returns the reserve after."""
    from xylarium.kernel import cosmos, field, reserve_banks
    b = reserve_banks.bank(kernel, house)
    held = reserve_banks.reserve(kernel, house)
    at = next((p for s in kernel.sectors.values() for p in s.planets if p.id == b.get("held_at")), None)
    if at is None or years <= 0 or not any(held):
        return held
    f = Fraction(rate(kernel, at)["share_yr"]) * years
    gone = [x * min(Fraction(1), f) for x in held]
    if not any(gone):
        return held
    b["reserve"] = [str(x - g) for x, g in zip(held, gone)]
    b["tax_owed"] = [str(Fraction(a) + g) for a, g in zip(b.get("tax_owed") or ["0"] * 4, gone)]
    inv = at.society.setdefault("inverse_mu", {"lanes": ["0"] * 4, "from": house})
    inv["lanes"] = [str(Fraction(a) + g) for a, g in zip(inv["lanes"], gone)]
    inv["coordinate"] = {"sector": at.sector_id, "deep_gyr": str(Fraction(cosmos.deep_gyr(kernel)))
                         if cosmos.is_cosmic(kernel) else None}
    inv["quantum_flux"] = str(field.quantum_flux(kernel, at)) if "field" in kernel.state else "0"
    return [x - g for x, g in zip(held, gone)]


def season(kernel: Any) -> List[str]:
    """Once a year: every ancients' world holds its air from its basket, and every house's vault pays its demurrage."""
    from xylarium.kernel import board, polity, relations
    if (kernel.cycle_count // polity._quarter()) % 4:
        return []
    st = stats(kernel)
    by = relations._peoples(kernel)
    consumed = short = Fraction(0)
    from xylarium.kernel import reserve_banks, spheres
    for house in sorted(board.ancient_peoples(kernel)):
        mine = {w.id: w for w in by.get(house) or []}
        home = spheres._home(kernel, house)
        vault = reserve_banks.bank(kernel, house).get("held_at") if "reserve_banks" in kernel.state else None
        for w in [mine[i] for i in sorted({getattr(home, "id", None), vault} & set(mine))]:
            try:
                rec = hold(kernel, w)
            except (KeyError, ValueError, ZeroDivisionError):
                continue                                     # a world with no model to read leaks nothing here
            consumed += Fraction(rec.get("consumed_kg", "0"))
            short += Fraction(rec.get("short_kg", "0"))
        if "reserve_banks" in kernel.state:
            last = st.setdefault("vault_t", {})
            from xylarium.kernel import cosmos
            now = Fraction(cosmos.deep_gyr(kernel)) if cosmos.is_cosmic(kernel) else \
                Fraction(kernel.cycle_count, 10 ** 11)
            t0 = Fraction(last.get(house, str(now)))
            last[house] = str(now)
            demurrage(kernel, house, (now - t0) * 10 ** 9)
    st["consumed_kg"], st["short_kg"] = str(consumed), str(short)
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"consumed_t": round(float(Fraction(st.get("consumed_kg", "0"))) / 1000, 1),
            "short_t": round(float(Fraction(st.get("short_kg", "0"))) / 1000, 1)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="leak", state=lambda: {}, season=season, summary=summary))
