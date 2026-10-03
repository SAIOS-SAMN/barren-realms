"""
Xylarium climate: a world's orbit and spin swing slowly, and its climate with them - ice ages and thaws.

A world's orbit and axis are not fixed (orbits.py). Its eccentricity swings between what its birth gave it and what
its neighbours force, over the time the neighbours' pull takes to turn its orbit (Laplace-Lagrange: ~ its year x
its star's mass over its heaviest neighbour's); its axis wobbles, the faster the more its spin bulges it (its
oblateness J2 = w^2 R^3 / 3 G M) - P ~ 2 P_year^2 / (3 J2 P_day) - and the less a large moon steadies it. As they
swing, the sunlight its high latitudes get in summer swings with them (physics.growing_share at the tilt of the
moment), and a world that sits near the freezing of its seas tips into an ice age when its summers fall short
of what its climate needs to stay unfrozen, and thaws when they return.

Nothing here decides which worlds freeze. Each world's own climate (worlds.build) is asked, once a quarter-Gyr,
how much less light it could bear before its seas freeze and its living medium is lost (the freezing ratio), and
what its life would have left in the frozen state; each year the orbit's swing is set against that ratio. A world far
from freezing never notices its wobbles; one on the edge lives through ice ages and thaws - its harvests with them
(biosphere.carrying_capacity reads the climate's share: climate_k), its peoples' councils reading the cold coming
(strategy.py's hold), its ledger telling it (ICE_AGE, THAW).
"""

import math
import zlib
from typing import Any, Dict, List, Optional

from xylarium.kernel import interior

TILT_SWING_DEG = {"moon": 1.3, "none": 6.0}   # how far an axis wobbles: steadied by a large moon (Earth's ~1.3 deg)
                                              # or free to swing (declared; Laskar: moonless worlds can be chaotic)
PRECESSION_SHARE = 1.6                        # an obliquity cycle over its axis's precession (Earth's 41 / 26 kyr)
FREEZE_GRID = (0.80, 0.85, 0.9, 0.93, 0.96, 0.98, 1.0)


def _orbit_terms(kernel: Any, planet: Any) -> Optional[Dict[str, float]]:
    from fractions import Fraction
    from xylarium.kernel import physics, worlds
    sec = kernel.sectors.get(planet.sector_id)
    if sec is None:
        return None
    b = physics.body(planet)
    if b.get("giant"):
        return None
    st = physics.star(sec)
    m_star = float(st["mass"])
    a = float(b.get("q", 1)) ** 2
    year = math.sqrt(a ** 3 / max(1e-6, m_star))                             # years
    others = [physics.body(p) for p in sec.planets if p is not planet and not getattr(p, "moon_of", None)]
    heaviest = max((float(o.get("mass", 0)) for o in others), default=0.0)
    p_ecc = year * m_star * 332946.0 / max(1e-3, heaviest) if heaviest > 0 else float("inf")
    m, r = float(b.get("mass", 1)) * interior.M_EARTH_KG, float(b.get("radius", 1)) * interior.R_EARTH_M
    day_s = float(b.get("day", 1)) * 86400.0
    w = 2 * math.pi / max(1.0, day_s)
    j2 = max(1e-6, w * w * r ** 3 / (3 * interior.G_SI * m))
    p_tilt = 2.0 * (year * 3.156e7) ** 2 / (3.0 * j2 * day_s) / 3.156e7 * PRECESSION_SHARE   # years
    mooned = any(getattr(p, "moon_of", None) == planet.id for p in sec.planets)
    e = float(b.get("e", 0.0) or 0.0)
    return {"p_ecc": p_ecc, "p_tilt": p_tilt, "swing": TILT_SWING_DEG["moon" if mooned else "none"],
            "tilt": float(b.get("tilt", 0) or 0), "e": e, "locked": bool(b.get("locked"))}


def _freezing(kernel: Any, planet: Any) -> Dict[str, float]:
    """Ask the world's own climate how much less light it can bear before its living medium freezes, and what its
    life keeps when it does (cached per quarter-Gyr of the world's age)."""
    from xylarium.kernel import biosphere, worlds
    s = worlds.state_of_planet(kernel, planet)
    key = list(s.get("key", []))
    cache = planet.society.get("_freeze")
    if cache and cache.get("key") == key:
        return cache
    metab = biosphere.metabolism_of(kernel, planet)
    args, mk = s["args"], s.get("make") or {}

    def energy_at(ratio: float) -> float:
        star = dict(args[1])
        from fractions import Fraction
        star["luminosity"] = str(Fraction(star["luminosity"]) * Fraction(ratio).limit_denominator(1000))
        a2 = (args[0], star) + tuple(args[2:])
        w = worlds.build(*a2, born=mk.get("born"), orbit=mk.get("orbit"), core=mk.get("core"))
        med = worlds.best(worlds.media(*a2, world=w), metab)
        return float(med["energy"]) if med else 0.0
    now = energy_at(1.0)
    ratio, kept = 0.0, 1.0
    if now > 0:
        for r in FREEZE_GRID[:-1][::-1]:                      # walk down until its medium's energy collapses
            e = energy_at(r)
            if e < 0.5 * now:
                ratio, kept = r, e / now
                break
    out = {"key": key, "ratio": ratio, "kept": round(kept, 4)}
    planet.society["_freeze"] = out
    return out


def season(kernel: Any) -> List[str]:
    """Once a year the orbits swing; the worlds on the edge of freezing feel it."""
    from xylarium.kernel import cosmos, history, physics
    if not cosmos.is_cosmic(kernel) or (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    logs: List[str] = []
    for sec in kernel.sectors.values():
        t_years = cosmos.deep_gyr(kernel, sector_id=sec.id) * 1e9     # its place's own now (clocks.py)
        for p in sec.planets:
            if p.population <= 0 or getattr(p, "natives", None):
                continue
            o = _orbit_terms(kernel, p)
            if o is None or o["locked"]:
                continue
            phase = (zlib.crc32(p.id.encode()) % 1000) / 1000.0 * 2 * math.pi
            tilt = max(0.0, o["tilt"] + o["swing"] * math.sin(2 * math.pi * t_years / o["p_tilt"] + phase))
            e_now = o["e"] * (1.0 + 0.5 * math.cos(2 * math.pi * t_years / o["p_ecc"] + phase)) \
                if o["p_ecc"] < float("inf") else o["e"]
            # the light its summers get, against what they get at its mean tilt and orbit
            forcing = float(physics.growing_share(tilt)) / max(1e-6, float(physics.growing_share(o["tilt"]))) \
                * (1.0 + e_now ** 2 / 2.0) / (1.0 + o["e"] ** 2 / 2.0)
            frz = _freezing(kernel, p)
            glacial = frz["ratio"] > 0 and forcing < frz["ratio"]   # its summers short of what keeps it unfrozen
            k = forcing * (frz["kept"] if glacial else 1.0)
            soc = p.society
            was = bool(soc.get("glacial"))
            soc["climate_k"] = round(min(1.2, k), 4)
            if glacial != was:
                soc["glacial"] = glacial
                kind = "ICE_AGE" if glacial else "THAW"
                st["ice_ages" if glacial else "thaws"] += 1
                history.event(kernel, kind, f"{'An ice age' if glacial else 'A thaw'} on {p.name}",
                              planet=p, actors=[],
                              cause=f"its axis at {tilt:.1f} degrees and its orbit's swing bring its summers "
                                    f"{forcing:.3f} of their mean light; its seas freeze below {frz['ratio']:.2f}",
                              data={"forcing": round(forcing, 4), "kept": frz["kept"]})
                logs.append(f"[CLIMATE] {'An ice age' if glacial else 'A thaw'} on {p.name}.")
    return logs


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "climate")


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"ice_ages": st["ice_ages"], "thaws": st["thaws"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="climate", state=lambda: {"ice_ages": 0, "thaws": 0}, season=season,
                             summary=summary))
