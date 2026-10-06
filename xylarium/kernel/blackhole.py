"""
Xylarium galactic centre: an Einstein-Cartan black hole - a sink on this side, a white hole on the other.

Our physics. Matter's spin couples to spacetime torsion (Einstein-Cartan). At the Cartan density the torsion term
repels: collapse halts and bounces, and there is no singularity. What crosses a black hole's horizon does not end:
it bounces into a spacetime of its own on the other side, and that bounce is a white hole - the Big Bang of a child
universe. The conformal inversion that swaps near and far turns the sink into its source (the white hole's null
generator: Mycelium's physics::source); torsion is never destroyed, only promoted, annihilated in a pair or
deposited (A.8), so information is never lost - it is carried through. Our own universe began so: its Big Bang is
the white hole of a black hole in a parent universe.

The galaxy's central black hole therefore takes matter in by two roads:

  HORIZON   a share of what falls crosses the horizon (HORIZON_SHARE; the rest is carried off by the hot disc's own
            outflow before it gets there) - it bounces, and is the matter of the child universe beyond: its elements
            and the RECORDS of what fell (the worlds, the stars, the peoples) are carried whole (child()).
  INBOUND   the bounce runs both ways: the paired sphere's white hole sends back as much as crosses, into the centre's
            reservoir (the waves between the spheres feed the core) - the web of spheres loses nothing at its joins.

  CAPTURE   within the bulge (cosmos.R_BULGE_KPC) a dying star's shed matter, and the worlds its death unbinds (a
            supernova's ejected planets, a giant's engulfed ones), fall to the centre instead of drifting into the void:
            their elements enter the centre's reservoir (a declared sink to the matter ledger).
  LIGHT     what falls in shines on the way down: L = eps Mdot c^2 (eps 0.1, the radiative efficiency of accretion),
            so the centre flares when it feeds - extremely luminous - and idles at the measured accretion of a quiet
            nucleus (Sgr A*, ~1e-8 solar masses a year) otherwise.
  RETURN    the disc's outflow sends the rest back out as jets and winds: each season the reservoir returns over
            an active episode's e-folding time (AGN episodes last ~1e7-1e8 years: 100 Myr) to the witnessed worlds of
            the bulge (a declared source) - recycled, enriched, never lost.

The centre's reservoir is a stock the matter ledger tracks through its declarations; the audit counts it.
"""

import math
from typing import Any, Dict, List, Optional

EFFICIENCY = 0.1                # radiative efficiency of accretion onto a black hole
C2_ERG_PER_SUN = 1.787e54       # a solar mass of energy (M c^2), erg
LSUN_ERG_PER_YEAR = 3.828e33 * 3.156e7
QUIET_MDOT = 1.0e-8             # solar masses a year a quiet nucleus accretes (Sgr A*)
EPISODE_MYR = 100.0             # e-folding time of an active episode: the reservoir's return
EARTH_SUNS = 3.003e-6           # an Earth mass in suns (a world's body mass is in Earth masses)
MASS0 = 4.0e6                   # the central black hole's mass at the clock's start (Sgr A*), suns
HORIZON_SHARE = 0.1             # the share of infalling matter that crosses the horizon: a hot accretion flow loses
                                # most of what falls to its own outflow first (declared; radiatively inefficient
                                # flows: a tenth or less reaches the hole)


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "blackhole")


def capture(kernel: Any, units: Dict[str, int], what: str, made: bool = False,
            records: Optional[List[str]] = None, suns: float = 0.0) -> None:
    """Matter falls to the centre. `made`: freshly made in a dying star (not yet in any world): a source and a sink
    at once, booked so the ledger sees it pass through. A share crosses the horizon into the child universe with
    the records of what fell (`records`: the peoples whose worlds these were); the rest feeds the disc's outflow.
    `suns`: the mass that fell - what the hole grows by and shines with. Element units are a world's workable
    deposits, not its mass: a world's deposits are never weighed as suns (they are enriched by the jets' own return,
    and weighing them again each time they fall would feed the hole on its own outflow)."""
    st = stats(kernel)
    st["fed_suns_season"] = st.get("fed_suns_season", 0.0) + max(0.0, float(suns))
    st["fed_suns"] = st.get("fed_suns", 0.0) + max(0.0, float(suns))
    total = 0
    crossed = 0
    for el, q in units.items():
        q = int(q)
        if q <= 0:
            continue
        if made:
            matter.source("stellar_ejecta", el, q)
        matter.sink("central_engine", el, q)
        through = int(q * HORIZON_SHARE)
        if through:
            ch = child(kernel)
            ch["elements"][el] = ch["elements"].get(el, 0) + through
            crossed += through
        # the bounce runs both ways: the paired sphere's white hole sends back as much as crossed - the waves between
        # the spheres feed the core (its own laws, so its centre's mix is ours)
        st["reservoir"][el] = st["reservoir"].get(el, 0) + q
        st["inbound"] = st.get("inbound", 0) + through
        total += q
    st["fed_season"] = st.get("fed_season", 0) + total
    st["captured"] += total
    st["crossed"] = st.get("crossed", 0) + crossed
    if total:
        st["last_meal"] = what
        _carry(kernel, what, records or [], crossed)


def child(kernel: Any) -> Dict[str, Any]:
    """The universe beyond the centre's horizon: begun at its first bounce, holding what crossed - its matter and
    the records of it, whole (no information is destroyed)."""
    st = stats(kernel)
    return st.setdefault("child", {"born": None, "elements": {}, "records": [], "seed": None})


def _carry(kernel: Any, what: str, records: List[str], crossed: int) -> None:
    from xylarium.kernel import cosmos, history
    if crossed <= 0:
        return
    ch = child(kernel)
    if ch["born"] is None:
        ch["born"] = round(cosmos.deep_gyr(kernel), 6)
        ch["seed"] = f"{cosmos.cosmos_seed(kernel)}:child"
        history.event(kernel, "CHILD_UNIVERSE", "Beyond the centre's horizon, a universe begins",
                      cause=f"{what} crossed the horizon and bounced at the Cartan density: the white hole on the "
                            f"other side is a new universe's Big Bang",
                      data={"seed": ch["seed"], "epoch": ch["born"]})
    ch["records"].append({"what": what, "peoples": list(records), "units": crossed,
                          "epoch": round(cosmos.deep_gyr(kernel), 6)})


def luminosity(kernel: Any) -> float:
    """Solar luminosities: eps Mdot c^2, Mdot from what fell in this season (or the quiet floor)."""
    from xylarium.kernel import cosmos
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    st = stats(kernel)
    deep_years = FISCAL_QUARTER_CYCLES / 100.0 * cosmos.ruler(kernel)
    mdot = max(QUIET_MDOT, st.get("fed_suns_last", 0.0) / max(1.0, deep_years))
    return EFFICIENCY * mdot * C2_ERG_PER_SUN / LSUN_ERG_PER_YEAR


def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import cosmos, history
    if not cosmos.is_cosmic(kernel):
        return []
    st = stats(kernel)
    logs: List[str] = []
    fed = st.pop("fed_season", 0)
    st["fed_last"] = fed
    suns = st.pop("fed_suns_season", 0.0)
    st["fed_suns_last"] = suns
    st["mass"] = st.get("mass", MASS0) + suns * HORIZON_SHARE * (1 - EFFICIENCY)
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
            from xylarium.kernel import zones
            for j, w in enumerate(worlds):
                part = out // len(worlds) + (1 if j < out % len(worlds) else 0)
                if part:
                    zones.touch(kernel, w)                     # a folded world is brought to now before it is given to
                    w.element_deposits[el] = w.element_deposits.get(el, 0) + part
                    matter.source("central_engine", el, part)
            st["returned"] += out
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    ch = st.get("child") or {}
    return {"mass_suns": round(st.get("mass", MASS0), 1), "luminosity_lsun": float(f"{luminosity(kernel):.3g}"),
            "reservoir": sum(st["reservoir"].values()), "captured": st["captured"], "returned": st["returned"],
            "fed_suns": round(st.get("fed_suns", 0.0), 3), "crossed": st.get("crossed", 0),
            "inbound": st.get("inbound", 0), "child_born": ch.get("born"), "child_records": len(ch.get("records", []))}


from xylarium.kernel import matter, state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="blackhole",
    state=lambda: {"reservoir": {}, "captured": 0, "returned": 0, "mass": MASS0},
    season=quarter,
    summary=summary,
))
