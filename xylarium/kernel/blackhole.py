"""
Xylarium galactic centre: an Einstein-Cartan black hole - not a sink but a recycler.

In Einstein-Cartan gravity matter's spin couples to spacetime torsion. At extreme density (the Cartan density) the
torsion term acts as a repulsion: collapse halts and bounces instead of ending in a singularity. The galaxy's central
black hole is therefore modelled as an engine that takes matter in and gives it back:

  CAPTURE   within the bulge (cosmos.R_BULGE_KPC) a dying star's shed matter, and the worlds its death unbinds (a
            supernova's ejected planets, a giant's engulfed ones), fall to the centre instead of drifting into the void:
            their elements enter the centre's reservoir (a declared sink to the matter ledger).
  LIGHT     what falls in shines on the way down: L = eps Mdot c^2 (eps 0.1, the radiative efficiency of accretion),
            so the centre flares when it feeds - extremely luminous - and idles at the measured accretion of a quiet
            nucleus (Sgr A*, ~1e-8 solar masses a year) otherwise.
  RETURN    the bounce sends matter back out as jets and winds: each season the reservoir returns over an active
            episode's e-folding time (AGN episodes last ~1e7-1e8 years: 100 Myr) to the witnessed worlds of the bulge
            (a declared source) - recycled, enriched, never lost.

The centre's reservoir is a stock the matter ledger tracks through its declarations; the audit counts it.
"""

import math
from typing import Any, Dict, List

EFFICIENCY = 0.1                # radiative efficiency of accretion onto a black hole
C2_ERG_PER_SUN = 1.787e54       # a solar mass of energy (M c^2), erg
LSUN_ERG_PER_YEAR = 3.828e33 * 3.156e7
QUIET_MDOT = 1.0e-8             # solar masses a year a quiet nucleus accretes (Sgr A*)
EPISODE_MYR = 100.0             # e-folding time of an active episode: the reservoir's return
UNITS_PER_SUN = 150             # deposit units a solar mass stands for (cosmos.EJECTA_PER_SUN)
MASS0 = 4.0e6                   # the central black hole's mass at the clock's start (Sgr A*), suns


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "blackhole")


def capture(kernel: Any, units: Dict[str, int], what: str, made: bool = False) -> None:
    """Matter falls to the centre. `made`: freshly made in a dying star (not yet in any world): a source and a sink
    at once, booked so the ledger sees it pass through."""
    st = stats(kernel)
    total = 0
    for el, q in units.items():
        q = int(q)
        if q <= 0:
            continue
        if made:
            matter.source("stellar_ejecta", el, q)
        matter.sink("central_engine", el, q)
        st["reservoir"][el] = st["reservoir"].get(el, 0) + q
        total += q
    st["fed_season"] = st.get("fed_season", 0) + total
    st["captured"] += total
    if total:
        st["last_meal"] = what


def luminosity(kernel: Any) -> float:
    """Solar luminosities: eps Mdot c^2, Mdot from what fell in this season (or the quiet floor)."""
    from xylarium.kernel import cosmos
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    st = stats(kernel)
    deep_years = FISCAL_QUARTER_CYCLES / 100.0 * cosmos.ruler(kernel)
    mdot = max(QUIET_MDOT, st.get("fed_last", 0) / UNITS_PER_SUN / max(1.0, deep_years))
    return EFFICIENCY * mdot * C2_ERG_PER_SUN / LSUN_ERG_PER_YEAR


def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import cosmos, history
    if not cosmos.is_cosmic(kernel):
        return []
    st = stats(kernel)
    logs: List[str] = []
    fed = st.pop("fed_season", 0)
    st["fed_last"] = fed
    st["mass"] = st.get("mass", MASS0) + fed / UNITS_PER_SUN * (1 - EFFICIENCY)
    L = luminosity(kernel)
    if fed and L > st.get("brightest", 0.0):
        st["brightest"] = L
        history.event(kernel, "CENTRE_FLARE", f"The galactic centre flares at {L:.1e} suns",
                      cause=f"it fed on {st.get('last_meal', 'the dead')}", magnitude=L,
                      data={"luminosity_lsun": L, "fed_units": fed})
        logs.append(f"[COSMOS] The galactic centre flares at {L:.1e} suns, feeding on {st.get('last_meal')}.")
    # the bounce: jets return the reservoir to the witnessed worlds of the bulge
    worlds = [p for s in kernel.sectors.values() for p in s.planets
              if float(cosmos.stats(kernel)["place"].get(str(s.id), {}).get("r", 99)) < cosmos.R_BULGE_KPC]
    if worlds and st["reservoir"]:
        from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
        deep_myr = FISCAL_QUARTER_CYCLES / 100.0 * cosmos.ruler(kernel) / 1.0e6
        share = 1.0 - math.exp(-deep_myr / EPISODE_MYR)
        for el in sorted(st["reservoir"]):
            out = int(st["reservoir"][el] * share)
            if out <= 0:
                continue
            st["reservoir"][el] -= out
            for j, w in enumerate(worlds):
                part = out // len(worlds) + (1 if j < out % len(worlds) else 0)
                if part:
                    w.element_deposits[el] = w.element_deposits.get(el, 0) + part
                    matter.source("central_engine", el, part)
            st["returned"] += out
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"mass_suns": round(st.get("mass", MASS0), 1), "luminosity_lsun": float(f"{luminosity(kernel):.3g}"),
            "reservoir": sum(st["reservoir"].values()), "captured": st["captured"], "returned": st["returned"]}


from xylarium.kernel import matter, state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="blackhole",
    state=lambda: {"reservoir": {}, "captured": 0, "returned": 0, "mass": MASS0},
    season=quarter,
    summary=summary,
))
