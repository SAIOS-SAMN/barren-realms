"""
Xylarium ruin: what it takes to strip a world of its air or break it apart - priced in its own physics, and done
only by a people that chooses to.

Nothing here decides that any world is ruined. A world's air is bound to it by its gravity: lifting it all to escape
takes its mass x G M / R. A world itself is bound by (3/5) G M^2 / R. A weapon delivers the energy its fuel holds
(antimatter: its whole rest mass), of which a share couples into lifting air rather than heating rock and radiating
away (impact-erosion studies put it at ~a tenth; declared). So a weapon that strips a Mars-sized world's thin air is
within reach of a people that has learned to make antimatter in quantity; one that breaks an Earth is not within
reach of any people the engine knows - the numbers say so, not a rule.

Who strikes is the peoples' and captains' own choice (factions.py, through decide.choose): the worth of denying an
enemy its world against the fuel's price and the lives it costs, as each mind judges them - its alignment weighing
the lives. What follows is the world's physics: with less air, less shelter, less food (biosphere.carrying_capacity
reads it); its people dwindle by famine, not by decree; the act is in the ledger (history: WORLD_STRIPPED,
WORLD_SHATTERED) and on the striker's alignment.
"""

import math
from typing import Any, Dict, Optional

from xylarium.kernel import interior
from xylarium.kernel.fx import hub as _hub

EU_J = 1361.0 * math.pi * interior.R_EARTH_M ** 2 * 0.25 * 3.156e7 / 1.0e6   # one energy unit (energy.py), joules
COUPLING = 0.1                  # share of a weapon's energy that lifts air rather than heating rock (declared)


def binding(kernel: Any, planet: Any) -> Dict[str, float]:
    """A world's air and its binding: the air's mass, the energy to lift it all to escape, the energy to break the
    world apart (J), and those in energy units (EU)."""
    from xylarium.kernel import physics, worlds
    b = physics.body(planet)
    m = float(b.get("mass", 1)) * interior.M_EARTH_KG
    r = float(b.get("radius", 1)) * interior.R_EARTH_M
    g = interior.G_SI * m / r ** 2
    p_bar = 0.0
    if not b.get("giant"):
        try:
            p_bar = float(worlds.state_of_planet(kernel, planet)["world"]["p_bar"])
        except Exception:
            p_bar = 1.0
    air = p_bar * 1.0e5 * 4.0 * math.pi * r * r / g * max(0.0, min(1.0, float(planet.society.get("atmosphere", 1.0))))
    strip = air * interior.G_SI * m / r
    shatter = 0.6 * interior.G_SI * m * m / r
    return {"air_kg": air, "strip_j": strip, "shatter_j": shatter, "strip_eu": strip / EU_J,
            "shatter_eu": shatter / EU_J}


def antimatter_needed(kernel: Any, planet: Any, share: float = 1.0) -> int:
    """Units of antimatter to strip a share of a world's air (energy.ANTIMATTER_EU each)."""
    from xylarium.kernel import energy
    need = binding(kernel, planet)["strip_eu"] * share / COUPLING
    return int(math.ceil(need / energy.ANTIMATTER_EU))


def strike(kernel: Any, captain: Any, planet: Any, units: int) -> Dict[str, Any]:
    """Detonates units of antimatter from the captain's hold against a world: the energy coupled into its air lifts
    that share of it to escape; enough to unbind the world itself shatters it. Returns what happened."""
    from xylarium.kernel import alignment, energy, history, imprint, matter
    cargo = captain.ship.cargo
    held = int(cargo.elements.get("AM", 0))
    units = max(0, min(int(units), held))
    if units <= 0:
        return {"ok": False, "why": "no antimatter in the hold"}
    bind = binding(kernel, planet)
    e = units * energy.ANTIMATTER_EU * EU_J
    cargo.elements["AM"] = held - units
    if cargo.elements["AM"] <= 0:
        cargo.elements.pop("AM", None)
    matter.sink("weapon", "AM", units)                   # annihilated: the fuel is gone as light and heat
    before = planet.population
    soc = planet.society
    if e >= bind["shatter_j"]:
        soc["shattered"] = kernel.cycle_count
        planet.population = 0
        kind, share = "WORLD_SHATTERED", 1.0
        imprint.record(kernel, planet, "shattered", captain.name, air_set=0.0, type="BARREN")
    else:
        share = min(1.0, e * COUPLING / max(1.0, bind["strip_j"])) if bind["strip_j"] > 0 else 0.0
        kind = "WORLD_STRIPPED"
        imprint.record(kernel, planet, "stripped", captain.name, air_scale=round(1.0 - share, 9))
    soc.setdefault("struck", []).append({"cycle": kernel.cycle_count, "by": captain.name, "share": round(share, 4),
                                         "antimatter": units})
    # the lives it costs: those it killed outright and those the land can no longer feed
    lost = (before - planet.population) + planet.population * share
    alignment.act(kernel, captain, "world_strike", lives_lost=lost)
    history.event(kernel, kind, f"{planet.name} is {'broken apart' if kind == 'WORLD_SHATTERED' else 'stripped of its air'}",
                  sector_id=planet.sector_id, actors=[captain.name, str(planet.owner_id or "")],
                  cause=f"{captain.name} detonated {units} units of antimatter ({e:.2e} J; its air was bound by "
                        f"{bind['strip_j']:.2e} J, the world by {bind['shatter_j']:.2e} J)",
                  data={"share": round(share, 4), "antimatter": units, "energy_j": float(f"{e:.4g}")})
    return {"ok": True, "kind": kind, "share": share, "energy_j": e, "lives": lost}


def worth_striking(kernel: Any, captain: Any, planet: Any) -> Optional[Dict[str, Any]]:
    """The strike as an option a mind can weigh (decide.choose): what denying the world's owner its world is worth
    to this captain - the share of the world's wealth and its people's output it takes away - against the fuel's
    price and the lives it costs, which the captain's own alignment prices (a light mind counts them dear, a dark
    one cheap). None if the captain cannot strike at all."""
    from xylarium.kernel import alignment, decide
    from xylarium.config import COMMODITY_CONFIG
    held = int(captain.ship.cargo.elements.get("AM", 0))
    if held <= 0 or not planet.owner_id or planet.owner_id == captain.id:
        return None
    need = antimatter_needed(kernel, planet, 1.0)
    units = min(held, max(1, need))
    share = min(1.0, units / max(1, need))
    fx = kernel.fx_market
    wealth = fx.to_sol_value(planet.currency, planet.treasury) if planet.currency != _hub() else planet.treasury
    sc = alignment.scales(kernel)
    lives = planet.population * share
    weight = max(0.0, 1.0 + float(getattr(captain, "cosmic_alignment", 0.0)))   # how dear a life is to this mind
    value = share * (wealth + planet.population * sc["sol"] / max(1.0, sc["lives"]))
    cost = units * COMMODITY_CONFIG["AM"]["base_price"] + lives * weight * sc["sol"] / max(1.0, sc["lives"])
    from xylarium.kernel import federation, knowledge, sustenance
    me, them = knowledge.holder_of_captain(captain), sustenance.people_of(planet)
    if federation.forbids(kernel, me, "exploit", them):
        cost += federation.sanction_sol(kernel, me)         # its fellows' arm, turned on a member that breaks faith
    return decide.option("strike_world", cost, value, units=units, share=share, aim="secure")
