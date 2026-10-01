"""
Xylarium mirror: Earth measured as one people among many.

Nothing in the engine is calibrated to Earth any more beyond its rulers (the AU, the Earth mass and area, a
person's ruler draw of energy). So the Terrans - the people of Terra - can be measured like any other, and placed
in the galaxy's own distribution: where do they stand on what every people is measured by?

  energy        what a person of theirs draws, in rulers (their industry's share at their efficiency, and the
                thermal gap of the worlds they live on)
  predation     raids their worlds attempt per world-year (hunger and plunder)
  intellect     fluid intelligence proven by work (intellect.py)
  alignment     where their measured consequences have put them, Light to Dark
  horizon       how far ahead they plan: their own generation over their minds' noise (decide.horizon)
  yards         the year they first built shipyards (spaceflight), for those that have

Each is reported with the Terrans' value and their percentile among all peoples (100 = highest of all).
"""

from typing import Any, Dict, List, Optional


def _peoples(kernel: Any) -> Dict[str, List[Any]]:
    from xylarium.kernel import relations
    return relations._peoples(kernel)


def terrans(kernel: Any, by: Dict[str, List[Any]]) -> Optional[str]:
    """The people of Terra: whoever lives on it, else whoever still carries Sol's lineage."""
    from xylarium.kernel import sustenance
    terra = kernel.get_planet("planet_1")
    if terra is not None and terra.population > 0:
        return sustenance.people_of(terra)
    for key, worlds in by.items():
        civ = getattr(worlds[0], "civilization", None)
        if civ is not None and getattr(civ, "species_name", "") == "human-sol":
            return key
    return None


def measures(kernel: Any) -> Dict[str, Dict[str, float]]:
    from xylarium.kernel import decide, energy, intellect, state as st_mod, sustenance
    by = _peoples(kernel)
    raids = sustenance.stats(kernel).get("raids_by", {})
    yards = st_mod.of(kernel, "demography").get("first_yards", {})
    years = max(1e-6, kernel.cycle_count / 100.0)
    out: Dict[str, Dict[str, float]] = {}
    for people, worlds in by.items():
        pop = sum(w.population for w in worlds) or 1
        cap = max(worlds, key=lambda w: w.population)
        rec = {
            "energy": sum(energy.per_capita(w, kernel) * w.population for w in worlds) / pop / energy.PERSON_EU,
            "predation": raids.get(people, 0) / len(worlds) / years,
            "intellect": intellect.fluid(kernel, people),
            "alignment": sustenance._alignment(kernel, cap),
            "horizon": decide.horizon(decide.mind_of_planet(kernel, cap)) / 4.0,
        }
        if people in yards:
            rec["yards"] = yards[people]
        out[people] = rec
    return out


def _percentile(values: List[float], x: float) -> float:
    if not values:
        return 0.0
    below = sum(1 for v in values if v < x)
    equal = sum(1 for v in values if v == x)
    return round(100.0 * (below + 0.5 * equal) / len(values), 1)


def summary(kernel: Any) -> Dict[str, Any]:
    by = _peoples(kernel)
    me = terrans(kernel, by)
    if me is None:
        return {"terrans": None}
    ms = measures(kernel)
    mine = ms.get(me, {})
    out: Dict[str, Any] = {"terrans": me, "peoples": len(ms)}
    for key in ("energy", "predation", "intellect", "alignment", "horizon", "yards"):
        vals = [m[key] for m in ms.values() if key in m]
        if key in mine:
            mean = sum(vals) / len(vals)
            out[key] = {"terran": round(mine[key], 4), "galaxy_mean": round(mean, 4),
                        "percentile": _percentile(vals, mine[key])}
    return out


from xylarium.kernel import state  # noqa: E402,F401
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="mirror", state=lambda: {}, summary=summary))
