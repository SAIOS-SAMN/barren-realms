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
  INBOUND   a paired universe's white hole may send matter our way (receive): a declared source into the centre's
            reservoir, counted only when it is actually sent - never assumed as an echo of what crossed.

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

from fractions import Fraction
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
            ch = child(kernel)                             # into the far core's engine, across the throat
            ch["reservoir"][el] = ch["reservoir"].get(el, 0) + through
            crossed += through
        # what crossed is the child's; only what the disc's outflow carried off before the horizon is the jets' to
        # return - counted once
        if q - through:
            st["reservoir"][el] = st["reservoir"].get(el, 0) + (q - through)
        total += q
    st["fed_season"] = st.get("fed_season", 0) + total
    st["captured"] += total
    st["crossed"] = st.get("crossed", 0) + crossed
    if total:
        st["last_meal"] = what
        _carry(kernel, what, records or [], crossed)


def receive(kernel: Any, units: Dict[str, int], sender: str) -> int:
    """Matter a universe beyond our own throats actually sends (a paired universe not yet witnessed as a face of
    ours): a declared source into the centre's reservoir (the jets return it like any other). What our own far core
    sends back comes through its engine (_far_engine), already counted. Returns the units received."""
    st = stats(kernel)
    got = 0
    for el, q in sorted(units.items()):
        q = int(q)
        if q <= 0:
            continue
        matter.source("paired_white_hole", el, q)
        matter.sink("central_engine", el, q)               # into the reservoir the ledger tracks
        st["reservoir"][el] = st["reservoir"].get(el, 0) + q
        got += q
    st["inbound"] = st.get("inbound", 0) + got
    if got:
        st["last_inbound"] = sender
    return got


def child(kernel: Any) -> Dict[str, Any]:
    """The far CORE of the centre's throat: the universe beyond the horizon, founded at the first crossing and kept
    from then on - its central engine, its reservoir of what crossed, its own clock, and the records of what fell
    (whole: no information is destroyed). A persisting engine, not a one-time Big Bang."""
    st = stats(kernel)
    ch = st.setdefault("child", {"born": None, "reservoir": {}, "records": [], "seed": None})
    ch.setdefault("reservoir", {})
    if "elements" in ch:                                     # an older save: its crossed matter was a store
        for el, q in ch.pop("elements").items():
            ch["reservoir"][el] = ch["reservoir"].get(el, 0) + int(q)
    ch.setdefault("reservoir", {})
    ch.setdefault("returned", 0)
    ch.setdefault("clock_myr", 0.0)
    ch.setdefault("lapse", 1.0)                              # its own clock, read as ours until the far face is seen
    return ch


def throat(kernel: Any, which: str = "centre") -> Dict[str, Any]:
    """A hole's throat: its two faces and their keepers, its mass, and what each face holds. The centre's near face is
    our galaxy's core; its far face is the core of the universe beyond (child). `parent` is our own Big Bang - the far
    face of a parent universe's core - its far side unwitnessed. No horizon is a dead end."""
    st = stats(kernel)
    thr = st.setdefault("throats", {})
    if which == "parent":
        return thr.setdefault("parent", {"near": "our Big Bang", "far": None, "witnessed": False,
                                         "keepers": {"near": [], "far": []}})
    ch = child(kernel)
    rec = thr.setdefault(which, {"near": "centre", "far": "child", "keepers": {"near": [], "far": []}})
    rec["mass"] = float(st.get("mass", MASS0))
    rec["reservoir_near"] = sum(int(v) for v in st["reservoir"].values())
    rec["reservoir_far"] = sum(int(v) for v in ch["reservoir"].values())
    rec["keepers"]["near"] = _keepers_near(kernel)
    return rec


def _keepers_near(kernel: Any) -> List[str]:
    """The near face's keepers: the hub's keeper and the living ancients (the ancients are reachable on both faces)."""
    out: List[str] = []
    try:
        from xylarium.kernel import board, transit
        keeper = transit.stats(kernel).get("hub")
        if keeper:
            out.append(keeper)
        out += [w for w in sorted(board.ancient_peoples(kernel)) if w not in out]
    except Exception:
        pass
    return out


def ledger(kernel: Any) -> Dict[str, int]:
    """The throat's books: everything that fell in or was sent, against where it is now - the near reservoir, the far
    core's reservoir, or returned by the jets. Conserved: inflow == near + far + returned."""
    st = stats(kernel)
    ch = child(kernel)
    near = sum(int(v) for v in st["reservoir"].values())
    far = sum(int(v) for v in ch["reservoir"].values())
    inflow = int(st.get("captured", 0)) + int(st.get("inbound", 0))
    return {"inflow": inflow, "near": near, "far": far, "returned": int(st.get("returned", 0)),
            "balance": inflow - near - far - int(st.get("returned", 0))}


# ---------------------------------------------------------------------- every other hole: the same law, smaller
def _new_core(t: Optional[float]) -> Dict[str, Any]:
    return {"born": t, "reservoir": {}, "carry": {}, "clock_myr": 0.0, "lapse": 1.0, "returned": 0}


def open_throat(kernel: Any, tid: str, near: Any, mass_suns: float, kind: str,
                keepers: Optional[List[str]] = None) -> Dict[str, Any]:
    """Any black hole is a throat: its near face where it sits, a far core (the universe beyond, small for a small
    hole) persisting on its own clock, keepers on both faces (the ancients reach both), and its own mass. Opened once;
    a second call returns the record."""
    from xylarium.kernel import cosmos
    thr = stats(kernel).setdefault("throats", {})
    if tid in thr:
        return thr[tid]
    k = list(keepers) if keepers is not None else _keepers_near(kernel)
    t = round(cosmos.deep_gyr(kernel), 6)
    thr[tid] = {"near": near, "far": f"{tid}:far", "kind": kind, "mass": float(mass_suns), "opened": t,
                "keepers": {"near": k, "far": list(k)}, "reservoir_near": {}, "core": _new_core(t),
                "inflow": 0, "returned": 0}
    return thr[tid]


def capture_into(kernel: Any, tid: str, units: Dict[str, int], what: str) -> int:
    """Matter falls into a throat other than the centre's: a declared sink; a share crosses to its far core (the
    same horizon law), the rest is its near face's to send back out."""
    rec = stats(kernel)["throats"][tid]
    got = 0
    for el, q in sorted(units.items()):
        q = int(q)
        if q <= 0:
            continue
        matter.sink("central_engine", el, q)
        through = int(q * HORIZON_SHARE)
        core = rec["core"]["reservoir"]
        if through:
            core[el] = core.get(el, 0) + through
        if q - through:
            rec["reservoir_near"][el] = rec["reservoir_near"].get(el, 0) + (q - through)
        got += q
    rec["inflow"] = int(rec["inflow"]) + got
    return got


def _engine(core: Dict[str, Any], into: Dict[str, int], deep_myr: float) -> int:
    """A far core's engine: its reservoir's e-fold share (EPISODE_MYR, read on its own clock) back through the throat,
    the fractional remainder carried, never dropped."""
    if not core["reservoir"]:
        return 0
    dt = deep_myr * float(core.get("lapse", 1.0))
    core["clock_myr"] = float(core.get("clock_myr", 0.0)) + dt
    share = 1.0 - math.exp(-dt / EPISODE_MYR)
    carry = core.setdefault("carry", {})
    moved = 0
    for el in sorted(core["reservoir"]):
        due = core["reservoir"][el] * Fraction(share) + Fraction(carry.get(el, 0))
        out = min(int(due), core["reservoir"][el])
        carry[el] = str(due - out)                         # exact: the remainder crosses seasons as a Fraction
        if out <= 0:
            continue
        core["reservoir"][el] -= out
        into[el] = into.get(el, 0) + out
        moved += out
    core["returned"] = int(core.get("returned", 0)) + moved
    return moved


def _small_throats(kernel: Any, deep_myr: float) -> None:
    """Each season every other throat keeps the centre's law: its far core sends back on its own clock; its near
    face's reservoir goes out to its own system's worlds by the same e-fold (a declared source)."""
    from xylarium.kernel import zones
    share = 1.0 - math.exp(-deep_myr / EPISODE_MYR)
    for tid in sorted(stats(kernel).get("throats", {})):
        rec = stats(kernel)["throats"][tid]
        if tid in ("centre", "parent") or "core" not in rec:
            continue
        _engine(rec["core"], rec["reservoir_near"], deep_myr)
        sec = kernel.sectors.get(rec["near"]) if isinstance(rec["near"], int) else None
        worlds = [p for p in (sec.planets if sec is not None else [])]
        if not worlds or not rec["reservoir_near"]:
            continue
        for el in sorted(rec["reservoir_near"]):
            out = int(rec["reservoir_near"][el] * share)
            if out <= 0:
                continue
            rec["reservoir_near"][el] -= out
            for j, w in enumerate(worlds):
                part = out // len(worlds) + (1 if j < out % len(worlds) else 0)
                if part:
                    zones.touch(kernel, w)
                    w.element_deposits[el] = w.element_deposits.get(el, 0) + part
                    matter.source("central_engine", el, part)
            rec["returned"] = int(rec["returned"]) + out


def throat_ledger(kernel: Any, tid: str) -> Dict[str, int]:
    """A throat's books: inflow == near + far + returned."""
    rec = stats(kernel)["throats"][tid]
    near = sum(int(v) for v in rec["reservoir_near"].values())
    far = sum(int(v) for v in rec["core"]["reservoir"].values())
    inflow = int(rec["inflow"])
    return {"inflow": inflow, "near": near, "far": far, "returned": int(rec["returned"]),
            "balance": inflow - near - far - int(rec["returned"])}


def _far_engine(kernel: Any, deep_myr: float) -> int:
    """The far core runs on its own clock: its engine returns its reservoir through the throat by the same e-fold
    the near jets keep (EPISODE_MYR), read on its clock - into the near face's reservoir (both faces are off the
    board: a transfer between them, nothing declared)."""
    st = stats(kernel)
    ch = child(kernel)
    if not ch["reservoir"]:
        return 0
    dt = deep_myr * float(ch["lapse"])
    ch["clock_myr"] = float(ch["clock_myr"]) + dt
    share = 1.0 - math.exp(-dt / EPISODE_MYR)
    moved = 0
    carry = ch.setdefault("carry", {})                       # the share not yet a whole unit: kept, never dropped
    for el in sorted(ch["reservoir"]):
        due = ch["reservoir"][el] * Fraction(share) + Fraction(carry.get(el, 0))
        out = min(int(due), ch["reservoir"][el])
        carry[el] = str(due - out)                         # exact: the remainder crosses seasons as a Fraction
        if out <= 0:
            continue
        ch["reservoir"][el] -= out
        st["reservoir"][el] = st["reservoir"].get(el, 0) + out
        moved += out
    ch["returned"] = int(ch["returned"]) + moved
    return moved


def _carry(kernel: Any, what: str, records: List[str], crossed: int) -> None:
    from xylarium.kernel import cosmos, history
    if crossed <= 0:
        return
    ch = child(kernel)
    if ch["born"] is None:
        ch["born"] = round(cosmos.deep_gyr(kernel), 6)
        ch["seed"] = f"{cosmos.cosmos_seed(kernel)}:child"
        rec = throat(kernel)
        rec["keepers"]["far"] = list(rec["keepers"]["near"])     # the ancients hold both faces from its founding
        history.event(kernel, "CHILD_UNIVERSE", "Beyond the centre's horizon, the far face of its throat is founded",
                      cause=f"{what} crossed the horizon and bounced at the Cartan density: the white hole on the "
                            f"other side is a universe's core - a persisting engine, the throat's far face",
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
        try:
            from xylarium.kernel import torsion
            sec_id = getattr(kernel, "home_sector", 1)
            torsion.emit_bounce(kernel, origin_sector=sec_id, energy_scale=min(100.0, float(L)), chirality=1, source="galactic_core")
        except Exception:
            pass
    # the throat's far face: its core's engine sends back on its own clock; our own Big Bang's face is on record
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES as _FQ
    _far_engine(kernel, _FQ / 100.0 * cosmos.ruler(kernel) / 1.0e6)
    _small_throats(kernel, _FQ / 100.0 * cosmos.ruler(kernel) / 1.0e6)
    throat(kernel, "parent")
    # the bounce: jets return the reservoir to the witnessed worlds of the bulge
    worlds = [p for s in kernel.sectors.values() for p in s.planets
              if (cosmos.from_centre_kpc(kernel, s.id) or 99) < cosmos.R_BULGE_KPC]      # the bulge is a sphere
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
