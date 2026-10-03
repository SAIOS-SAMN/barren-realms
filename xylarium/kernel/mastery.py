"""
Xylarium mastery: what a people commands of its world and its star - measured, not granted - and the crossing beyond
its own system.

MASTERY is the energy a people puts to work against the energy nature puts through its home (Kardashev 1964):

  world   its power over the starlight its homeworld intercepts - 1 is a people that commands as much as its sky
          gives its world (Kardashev's type I);
  star    its power over its star's whole light - 1 commands a star (type II).

Sagan's continuous form K = (log10 P[W] - 6) / 10 is kept beside them. Nothing is gated on these: they are what a
people is, and what other peoples see of it (federations judge by them: federation.py).

THE CROSSING. Within its own system a people sails sublight: its drives' exhaust (propulsion: the hydrogen torch's
is the unit, c / 30 - an antimatter photon drive's is c) brings its planets and moons within a lifetime; the next
star is centuries to millennia away even at the fastest, and no council sends its people on a voyage longer than it
can plan for. Beyond the neighbouring worlds lies a boundary a people crosses only when it understands enough of
space's own geometry to fold it - when its mathematics holds the fourth axis (intellect.py: the hyper crystals, and a
rank-4 rung proven) - and can raise the energy to open one passage (E_BRIDGE: the mass-energy a metric-engineering
estimate asks, declared). Whether such passages exist at all is a law of the universe (fundamental: ftl=0 forbids
them). A people may never cross: it lives its whole history in its own system, its ways and art in the ledger.
"""

import math
from typing import Any, Dict, List, Optional

from xylarium.kernel import interior

SEASON_S = 0.25 * 3.156e7
L_SUN_W = 3.828e26
E_BRIDGE_J = 700.0 * 2.998e8 ** 2   # opening one passage: ~700 kg of mass-energy (White 2011's revised estimate for
                                    # an Alcubierre-type metric; estimates span to a gas giant's - declared, speculative)
V_E_UNIT_C = 1.0 / 30.0             # the hydrogen torch's exhaust over c (propulsion.FUEL_CELLS: v_e 30 is light)


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "mastery")


def _eu_j() -> float:
    from xylarium.kernel import ruin
    return ruin.EU_J


def peoples(kernel: Any) -> Dict[str, List[Any]]:
    """Each people's peopled worlds."""
    from xylarium.kernel import sustenance
    out: Dict[str, List[Any]] = {}
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population > 0 and not getattr(p, "natives", None):
                who = sustenance.people_of(p)
                if who:
                    out.setdefault(who, []).append(p)
    return out


BODY_W = 100.0                      # a unit body's metabolism (W): the ruler a people's own bodies are counted in


def power_w(kernel: Any, worlds: List[Any]) -> float:
    """The power a people puts to work: its bodies' own (a unit body's metabolism x what its body needs:
    biosphere.need_factor) and what its works use (energy.py), in watts."""
    from xylarium.kernel import biosphere, energy
    eu = sum(energy.need_eu(p, kernel) * float(p.society.get("energy_sufficiency", 1.0)) for p in worlds)
    bodies = sum(p.population * BODY_W * float(biosphere.need_factor(p, kernel)) for p in worlds)
    return eu * _eu_j() / SEASON_S + bodies


def sky_w(kernel: Any, planet: Any) -> float:
    """The starlight a world intercepts (W): its flux over its disc."""
    from xylarium.kernel import physics
    sec = kernel.sectors.get(planet.sector_id)
    flux = float(physics.planet_flux(sec, planet)) if sec is not None else 1.0
    r = float(physics.body(planet).get("radius", 1)) * interior.R_EARTH_M
    return 1361.0 * flux * math.pi * r * r


def star_w(kernel: Any, planet: Any) -> float:
    from xylarium.kernel import physics
    sec = kernel.sectors.get(planet.sector_id)
    return float(physics.star(sec)["luminosity"]) * L_SUN_W if sec is not None else L_SUN_W


def home(worlds: List[Any]) -> Any:
    return max(worlds, key=lambda p: p.population)


def measure(kernel: Any, worlds: List[Any]) -> Dict[str, float]:
    p_w = power_w(kernel, worlds)
    h = home(worlds)
    return {"power_w": p_w, "world": p_w / max(1.0, sky_w(kernel, h)), "star": p_w / max(1.0, star_w(kernel, h)),
            "kardashev": (math.log10(max(1.0, p_w)) - 6.0) / 10.0}


def theory(kernel: Any, holder: str) -> bool:
    """Does a people's mathematics hold the fourth axis - the hyper crystals, and a rank-4 rung proven?"""
    from xylarium.kernel import crystal as C, intellect
    st = intellect.stats(kernel)
    vocab = st.get("vocab", {}).get(holder, [])
    held = any((c if isinstance(c, str) else str(c)) in C.HYPER_OPS for c in vocab)
    return held and int(intellect.gauge(kernel, holder).get("4", 0)) >= 1


def genome_ready(kernel: Any, holder: str, worlds: List[Any]) -> bool:
    """Can this people live beyond its own star? Its bodies are tuned to its home - the star's light, its world's
    gravity, heat, radiation and chemistry (biosphere.adapt) - and only a people that can rewrite its own genome
    (technology: genetics) can retune them for another sun. Life without a genome - information held in fields, not
    copied molecules (plasmic) - has nothing to rewrite, and is not held back by it."""
    from xylarium.kernel import technology
    if not worlds:
        return False
    if technology.genomeless(kernel, home(worlds)):
        return technology.has(kernel, holder, "embodiment")   # its own hurdle: a vessel to move in
    return technology.has(kernel, holder, "genetics") or technology.has(kernel, holder, "transfer")


def ftl_law(kernel: Any) -> bool:
    from xylarium.kernel import creation, fundamental
    return fundamental.of(creation.universe(kernel)).ftl


def crossed(kernel: Any, holder: Optional[str]) -> bool:
    """Has this people crossed into the space between the stars? Outside a cosmic universe every people already sails
    the lanes (the settled board)."""
    from xylarium.kernel import cosmos
    if not cosmos.is_cosmic(kernel):
        return True
    return bool(holder) and holder in stats(kernel)["crossed"]


def energy_held_j(worlds: List[Any]) -> float:
    from xylarium.kernel import energy
    eu = sum(p.society.get("grid_meu", 0) / energy.MILLI + p.element_reserves.get("AM", 0) * energy.ANTIMATTER_EU
             for p in worlds)
    return eu * _eu_j()


def sublight_years(kernel: Any, a: int, b: int, planet: Any) -> Optional[float]:
    """Years a people's fastest settler voyage takes between two systems: half its drive's exhaust as cruise (an e-fold
    of mass burned to speed up and to stop), over the proper distance between them (geometry)."""
    from xylarium.config import FUEL_CELLS
    from xylarium.kernel import cosmos, propulsion
    d = cosmos.distance_kpc(kernel, a, b)
    if d is None:
        return None
    v_e = FUEL_CELLS.get(propulsion.world_fuel(kernel, planet), FUEL_CELLS["H"]).get("v_e") or 1.0
    v = min(0.99, 0.5 * v_e * V_E_UNIT_C)
    return d * 3261.56 / v


def season(kernel: Any) -> List[str]:
    """Once a year: each people's mastery is measured, and a people whose mathematics and energy suffice crosses."""
    from xylarium.kernel import cosmos, history
    if (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    logs: List[str] = []
    law = cosmos.is_cosmic(kernel) and ftl_law(kernel)
    for who, worlds in peoples(kernel).items():
        m = measure(kernel, worlds)
        prev = st["of"].get(who, {})
        st["of"][who] = {k: float(f"{v:.4g}") for k, v in m.items()}
        for key, kind, text in (("world", "WORLD_MASTERED", "commands as much power as its sky gives its world"),
                                ("star", "STAR_HARNESSED", "commands as much power as its star gives")):
            if m[key] >= 1.0 > float(prev.get(key, 0.0)):
                history.event(kernel, kind, f"{who.split(':', 1)[-1]} {text}", sector_id=home(worlds).sector_id, actors=[who],
                              data={"power_w": float(f"{m['power_w']:.3g}")})
        if law and who not in st["crossed"] and theory(kernel, who) and energy_held_j(worlds) >= E_BRIDGE_J \
                and genome_ready(kernel, who, worlds):
            st["crossed"][who] = kernel.cycle_count
            history.event(kernel, "FTL_CROSSED", f"{who.split(':', 1)[-1]} folds space and crosses to the stars",
                          sector_id=home(worlds).sector_id, actors=[who],
                          cause="its mathematics holds the fourth axis, it can raise the energy to open a passage, "
                                "and it can rewrite itself for another sun",
                          data={"kardashev": round(m["kardashev"], 3)})
            logs.append(f"[FRONTIER] {who.split(':', 1)[-1]} crosses the boundary: its ships can now reach other stars.")
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    ks = [v["kardashev"] for v in st["of"].values()]
    return {"peoples": len(st["of"]), "crossed": len(st["crossed"]),
            "kardashev_max": max(ks) if ks else None,
            "world_mastered": sum(1 for v in st["of"].values() if v["world"] >= 1.0)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="mastery", state=lambda: {"of": {}, "crossed": {}}, season=season,
                             summary=summary))
