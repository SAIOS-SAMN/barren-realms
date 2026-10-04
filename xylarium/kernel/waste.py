"""
Xylarium waste: what a people's work leaves in its world, what the world clears, and what it costs the living.

Every process a people runs draws free energy and leaves waste - nothing here is any one world's story; each world
answers by its own physics:

  EMITTED   what a source leaves, by its chemistry: a fuel burnt leaves its oxide (the fuel's mass and the oxidiser
            its biosphere made - FUELS: stoichiometry and heat of combustion, measured chemistry); every unit of energy
            a people uses ends as heat (the energy ledger's own count, energy.py).
  KEPT      a gas stays in the air as far as the world's seas do not take it up: Henry's law between its air column and
            its liquid seas (solubility, measured chemistry; the world's own seas, gravity and air); a product that
            rains or freezes out at the world's temperature never stays in its air at all. What stays is cleared
            on geological time by the world's own cycles (worlds.build's equilibrium, recomputed as the world ages).
  FELT      the world's own greenhouse law (worlds.py: tau ~ sqrt(greenhouse gas) at its air's pressure) gives the
            temperature the kept gas makes; waste heat adds to the light the world absorbs. A temperature shift is the
            same shift its light would make (T ~ F^(1/4)), and the people's own fitness to its light (genome.py: tuned,
            and widened by its tolerance) gives what the world can still carry of it - less, if the shift takes it
            from what it is tuned to; more, if a cold world is warmed toward its tuning.

The room it loses (or gains) is the waste's consequence, written into the history of the people that made it, each
season it lasts (alignment.flow: room destroyed is dark; room made is light). Nothing forbids burning: what it
built is counted where it is built, what it fouls where it fouls - the intelligence of a people is read from both.
"""

import math
from typing import Any, Dict, List, Optional

# what a fuel leaves when it burns: its product, product mass per kg of fuel, and the heat a kg gives (J) - measured
# chemistry (standard enthalpies of combustion), the same on every world where the oxidiser exists
FUELS = {"C": {"product": "CO2", "per_kg": 44.0 / 12.0, "heat_j_per_kg": 3.28e7}}
# solubility in a liquid sea (mol per litre per bar, near 300 K): Henry's law constants, measured chemistry
HENRY = {"CO2": 3.4e-2, "CH4": 1.4e-3, "NH3": 5.9e1, "N2": 6.4e-4, "CO": 9.9e-4, "H2O": 0.0}
MOLAR = {"CO2": 0.044, "CH4": 0.016, "NH3": 0.017, "N2": 0.028, "CO": 0.028, "H2O": 0.018}   # kg/mol
EARTH_R_M = 6.371e6             # the unit radius (m), as the energy unit's ruler is drawn on it
SOLAR_UNIT_W_M2 = 4.0 * 340.0   # the light at 1 AU from a unit star (worlds.py: unit flux 340 W/m^2 over a sphere)
YEAR_S = 3.15576e7


def eu_joules() -> float:
    """The energy unit in joules: a millionth of the light a unit world at 1 AU receives in a season (energy.py)."""
    return 1.0e-6 * SOLAR_UNIT_W_M2 * math.pi * EARTH_R_M ** 2 * 0.25 * YEAR_S


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "waste")


def _area(w: Dict[str, Any]) -> float:
    return 4.0 * math.pi * (float(w.get("radius", 1.0)) * EARTH_R_M) ** 2


def kept_share(w: Dict[str, Any], gas: str) -> float:
    """The share of an emitted gas the world's air keeps against its liquid seas (Henry's law over the column)."""
    from xylarium.kernel import worlds
    g = max(1e-6, float(w.get("g", 1.0))) * worlds.UNIT_G
    t, p = float(w.get("t_surf", 288.0)), max(1e-9, float(w.get("p_bar", 1.0)))
    if gas in worlds.VOLATILES and worlds.phase(gas, t, p) != "gas":
        return 0.0                                          # it rains or freezes out of this sky
    air_mol_per_bar = worlds.BAR / (g * MOLAR.get(gas, 0.03))         # mol/m^2 of the gas per bar of it
    litres = 0.0
    for solvent, amount in (w.get("seas") or {}).items():
        if worlds.phase(solvent, t, p) == "liquid":
            litres += float(amount) * worlds.BAR / g                   # kg/m^2 of sea, about a litre a kg
    dissolved_mol_per_bar = HENRY.get(gas, 0.0) * litres
    return air_mol_per_bar / (air_mol_per_bar + dissolved_mol_per_bar)


def warming(w: Dict[str, Any], added_bar: Dict[str, float], heat_w_m2: float = 0.0) -> float:
    """The world's temperature with the added gas kept in its air and the waste heat absorbed, over its temperature
    now: its own greenhouse law at its own air."""
    from xylarium.kernel import worlds
    L = w.get("laws") or worlds._laws(None)
    air = dict(w.get("air") or {})
    opacity = L.atom ** 2

    def tau(a: Dict[str, float]) -> float:
        gh = sum(v for sp, v in a.items() if worlds.VOLATILES.get(sp, {}).get("greenhouse"))
        return worlds.GREENHOUSE_TAU * math.sqrt(max(0.0, gh) * opacity) * max(1e-9, sum(a.values())) ** worlds.BROADENING
    t0 = float(w.get("t_surf", 288.0))
    p0 = max(1e-9, float(w.get("p_bar", 1.0)))
    absorbed = float(w.get("flux", 1.0)) * 340.0 * (1.0 - float(w.get("albedo", 0.3)))
    heat = (1.0 + heat_w_m2 / absorbed) ** 0.25 if absorbed > 0 and heat_w_m2 > 0 else 1.0
    # a sea of a greenhouse volatile answers the warmth: its vapour over the warmer sea is its saturation there
    # (Clausius-Clapeyron, the world's own), which warms it again - iterated to where the two agree
    feeders = [sp for sp in (w.get("seas") or {}) if worlds.VOLATILES.get(sp, {}).get("greenhouse")
               and worlds.phase(sp, t0, p0) == "liquid" and sp in air]
    ratio = 1.0
    for _ in range(30):
        after = dict(air)
        for sp, v in added_bar.items():
            after[sp] = after.get(sp, 0.0) + v
        t = t0 * ratio
        for sp in feeders:
            after[sp] = air[sp] * worlds.saturation(sp, t, L) / max(1e-12, worlds.saturation(sp, t0, L))
        nxt = ((1.0 + 0.75 * tau(after)) / (1.0 + 0.75 * tau(air))) ** 0.25 * heat
        if abs(nxt - ratio) < 1e-9:
            break
        ratio = nxt
    return ratio


def room(kernel: Any, planet: Any, t_ratio: float) -> float:
    """What the world can carry of its people at a temperature shifted by t_ratio, over what it carries now: the
    shift is the light shift t_ratio^4, read through the people's own fitness to its light (genome.py)."""
    from xylarium.kernel import genome
    if abs(t_ratio - 1.0) < 1e-12:
        return 1.0
    x0 = genome._flux_ratio(kernel, planet)
    if x0 is None:
        return 1.0
    g = genome.of(planet)

    def lf(x: float) -> float:
        return math.log(genome.tuned_fit(4 * x / ((1 + x) ** 2), x, g["tolerance"]))
    x = x0 / math.exp(g["light"])
    return math.exp(lf(x * t_ratio ** 4) - lf(x))


def season(kernel: Any) -> List[str]:
    """A season of the worlds' waste: what each people emitted, what its world kept, and what it cost the living."""
    from xylarium.kernel import biosphere, fertility, sustenance, worlds
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    st = stats(kernel)
    years = FISCAL_QUARTER_CYCLES / 100.0
    for sec in kernel.sectors.values():
        for p in sec.planets:
            soc = p.society
            burned = int(soc.pop("burned_c", 0) or 0)
            used_meu = int(soc.get("energy_used_meu", 0) or 0)
            if p.population <= 0 or (burned <= 0 and used_meu <= 0 and not soc.get("waste")):
                continue
            try:
                w = worlds.state_of_planet(kernel, p)["world"]
            except Exception:
                continue
            area = _area(w)
            g = max(1e-6, float(w.get("g", 1.0))) * worlds.UNIT_G
            rec = soc.setdefault("waste", {"air": {}, "heat_w_m2": 0.0})
            from xylarium.kernel import energy
            if burned > 0:                                          # what the fuel became
                kg = burned * energy.CARBON_EU * eu_joules() / FUELS["C"]["heat_j_per_kg"]
                product = FUELS["C"]["product"]
                kept = kg * FUELS["C"]["per_kg"] * kept_share(w, product)
                rec["air"][product] = rec["air"].get(product, 0.0) + kept * g / area / worlds.BAR   # bar
                st["emitted_kg"] = st.get("emitted_kg", 0.0) + kg * FUELS["C"]["per_kg"]
            from xylarium.kernel.energy import MILLI
            rec["heat_w_m2"] = used_meu / MILLI * eu_joules() / (0.25 * YEAR_S) / area     # this season's heat
            ratio = warming(w, rec["air"], rec["heat_w_m2"])
            factor = room(kernel, p, ratio)
            k_before = biosphere.carrying_capacity(kernel, p)
            soc["waste_k"] = round(factor, 6)
            rec["t_ratio"] = round(ratio, 6)
            gens = years / max(1e-6, fertility.generation_years(fertility.strategy(kernel, p)))
            base = k_before / max(1e-9, soc.get("_waste_k_was", 1.0) or 1.0)    # the room without its waste
            soc["_waste_k_was"] = factor
            change = base * (factor - 1.0) * gens                  # lives of room, this season
            if change < 0:
                sustenance.flow_civ(p, dark=-change)
                st["room_lost"] = st.get("room_lost", 0.0) - change
            elif change > 0:
                sustenance.flow_civ(p, light=change)
                st["room_made"] = st.get("room_made", 0.0) + change
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"emitted_kg": round(st.get("emitted_kg", 0.0), 1), "room_lost": round(st.get("room_lost", 0.0), 1),
            "room_made": round(st.get("room_made", 0.0), 1)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="waste",
    state=lambda: {},
    season=season,
    summary=summary,
))
