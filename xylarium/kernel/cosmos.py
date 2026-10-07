"""
Xylarium cosmos: the scales of the simulated universe, the galaxy's clockwork, and where and when minds arise.

THE BIG BANG. Deep time is counted from the universe's beginning: deep_gyr is Gyr since the Big Bang. The home
galaxy's first stars form 0.3 Gyr after it (the oldest stars measured are ~13.5 Gyr old), its disc inside-out after
that; the present universe is 13.8 Gyr old - a reading on this clock, not where it stops.

THE SCALES (largest first)

  universe          the whole run: one seed, one clock, from the Big Bang (scheduler.py, clock.py)
  galactic cluster  the galaxies bound together; the home cluster - only its home galaxy is simulated, the rest are
                    a count kept for later tiers
  galaxy            an exponential disc (scale length R_D) of rings and cells; a CELL is a region of the disc
                    ~CELL_KPC on a side, carried by 40 sectors (a region) when it is materialised
  region            40 sectors: star systems and the null space between them (sectors 1-100 are the first
                    witness's own region and its neighbourhood)
  system            one sector: a star and its worlds, on exact Keplerian orbits (physics.py)

CREATION IS FIXED AT THE BIG BANG (creation.py): every cell's stars, their birth dates and their worlds are a pure
function of the seed and the cell's coordinates - never redrawn, the same whoever finds them in whatever order.

Nothing is charted until it is witnessed. A mind that arises is given its own system and nothing more: its sky is
description, not map. A cell is charted (all its sectors and lanes) when a ship enters it or a neighbour, or when a
people with shipyards stands in it - the map grows only where peoples that reach the stars actually go. Everywhere
else the galaxy is a formula.

THE GALAXY (Milky Way measurements as rulers and data points, not as a template)

  * inside-out star formation: a radius forms its stars after tau(r) = 1.033 r - 1.267 Gyr (Chiappini, Matteucci &
    Romano 2001); the core first, the rim last.
  * the galaxy makes its own elements (enrichment.py): stars form from infalling gas, four channels make each element
    on their own clocks, fountains carry it a radial epicycle by weight (Graham's 1/sqrt(A)), winds blow some out,
    gas drifts inward, the centre takes what reaches it. Heavy elements stay near the core, the light reach the rim;
    iron's gradient comes out near the measured -0.06 dex/kpc without being put in.
  * clockwork: every system rides a flat rotation curve (V_FLAT) around the centre, theta(t) = theta0 + V t / r -
    closed form, any moment as cheap as any other; each star keeps its own worlds on their own orbits.

THE CLOCKS ARE TIERED. A system's worlds turn on historical time (100 cycles to a year). The galaxy - its rotation,
its stars' lives, the evolution of life - turns on deep time: ruler(kernel) years of it pass for each year of the
clock. That is the one ruler mapping the two, and it is a law of each universe, chosen once at its genesis (PACES:
lonely 0.1 Myr a year - the second mind arrives long after the first has reached the stars; neighbourly 1 Myr;
teeming 10 Myr - minds arise within a lifetime of each other and the galaxy turns visibly); everything else is
physics.

STARS ARE BORN AND AGE. Each star is born on its own date from its ring's star-formation history (creation.py): a
charted sector whose star is not yet born is gas, and lights when its date comes (STAR_BORN). It lives
SUN_MS_GYR x M^-2.5 from its birth. Over its last tenth it brightens toward
the giant phase and its worlds feed fewer and fewer (their carrying capacity falls with what is left of it) - a
people sees its end coming for centuries; then the star dies and its worlds feed no one. A star already dead when
its region is first witnessed is found as a remnant with lifeless worlds.

MINDS ARISE (Carter's hard steps, creation.py). Every world of every system the cells hold is a candidate for every
biology that can live on it, each with its own needs - metals (none for plasmic minds, the Big Bang's hydrogen),
its vulnerability to sterilising supernovae, its star's window - and its own initial conditions, fixed by the seed. There is no
one habitable zone: each biology has its own. The clock's year 0 is the epoch the first mind arises; each later one
arises in its own year on its own world, is named, and begins as foragers (ways.py).
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import matter

SLOTS = 40                      # sectors per cell (creation.SLOTS)

# ---------------------------------------------------------------------- rulers (units and anchors)
R0_KPC = 8.0                    # the Sun's galactocentric radius: where today's deposits were set (a ruler)
R_D_KPC = 3.0                   # the disc's scale length (Milky Way, a data point)
R_MAX_KPC = 5 * R_D_KPC         # the optical disc: five scale lengths
CELL_KPC = 0.5                  # a cell of the disc, carried by one region (40 sectors)
V_FLAT_KMS = 220.0              # flat rotation speed (Milky Way)
PACES = {"lonely": 1.0e5, "neighbourly": 1.0e6, "teeming": 1.0e7}   # deep years per clock year, chosen at genesis
DEEP_YEARS_PER_YEAR = PACES["neighbourly"]                          # the default: the one ruler between the tiers' clocks
GALAXIES_IN_CLUSTER = 40        # the home cluster's galaxies (Local Group scale); only the home galaxy is simulated
# ---------------------------------------------------------------------- laws and measurements
HARD_STEPS = 4                  # Carter (1983); Watson (2008): ~4 hard steps to intelligence (creation.py)
SUN_MS_GYR = 10.0               # main-sequence lifetime of a solar-mass star; tau ~ M^-2.5
KPC_PER_MYR_AT_1KMS = 1.0 / 977.8

# atomic masses (real elements); the exotic elements' lines are their periods
ATOMIC_MASS = {"H": 1.0, "He-3": 3.0, "C": 12.0, "H2O": 18.0, "Si": 28.1, "ORE": 20.0, "Ti": 47.9, "Fe": 55.8,
               "Ni": 58.7, "Cu": 63.5, "Xe": 131.3, "Pt": 195.1, "U": 238.0, "TAILINGS": 20.0, "Na": 23.0,
               "Cl": 35.45, "NaCl": 58.44}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "cosmos")


def cosmos_seed(kernel: Any) -> Any:
    """The key everything the Big Bang fixed is drawn from: the seed, and the kind of universe chosen at genesis."""
    from xylarium.kernel import creation
    return creation.universe(kernel)


def is_cosmic(kernel: Any) -> bool:
    return ((getattr(kernel, "state", None) or {}).get("genesis") or {}).get("mode") == "cosmic"


# ---------------------------------------------------------------------- the disc's cells
def rings() -> int:
    return int(R_MAX_KPC / CELL_KPC)


def ring_radius(i: int) -> float:
    return (i + 0.5) * CELL_KPC


def slots(i: int) -> int:
    return max(1, int(round(2.0 * math.pi * ring_radius(i) / CELL_KPC)))


def cells() -> List[Tuple[int, int]]:
    return [(i, j) for i in range(rings()) for j in range(slots(i))]


def cell_theta(i: int, j: int) -> float:
    return 2.0 * math.pi * (j + 0.5) / slots(i)


def neighbours(i: int, j: int) -> List[Tuple[int, int]]:
    n = slots(i)
    out = [(i, (j - 1) % n), (i, (j + 1) % n)] if n > 1 else []
    a0, a1 = 2 * math.pi * j / n, 2 * math.pi * (j + 1) / n
    for k in (i - 1, i + 1):
        if 0 <= k < rings():
            m = slots(k)
            for jj in range(m):
                b0, b1 = 2 * math.pi * jj / m, 2 * math.pi * (jj + 1) / m
                if b0 < a1 and b1 > a0:
                    out.append((k, jj))
    return sorted(set(out))


def density(r: float) -> float:
    """Stellar surface density relative to R0's."""
    return math.exp((R0_KPC - r) / R_D_KPC)


def cosmic_rays(r: float) -> float:
    """The galaxy's cosmic-ray flux where a system circles, relative to R0's: supernovae make them, and the dying stars
    are the stars there - every component's number density (encounters.components: disc, bulge, nuclear cluster) over
    the disc's at R0. The disc alone (density) misses the bulge, where most of the inner galaxy's stars are."""
    from xylarium.kernel import encounters
    return sum(n for n, _ in encounters.components(r)) / encounters.DISC_N_R0


def formed_gyr(r: float) -> float:
    """Inside-out: a radius's star-formation timescale in our universe, Gyr (Chiappini et al. 2001's infall; at
    least 0.3 Gyr - the age of the oldest stars measured). Each universe scales it (creation.infall_gyr)."""
    return max(0.3, 1.033 * r - 1.267)


def metals(r: float) -> float:
    """Metallicity of the gas at radius r today, relative to the Sun's birth gas (enrichment.py)."""
    from xylarium.kernel import creation, enrichment
    return enrichment.metals(None, r, creation.TODAY_GYR)


def mass_of(element: str) -> float:
    """An element's (or a good's) mass per unit: its atomic or formula mass (substances.py)."""
    a = ATOMIC_MASS.get(element)
    if a is None:
        from xylarium.kernel import substances
        a = substances.molar_mass(element) or 30.0
    return float(a)


def scatter_length(element: str) -> float:
    """kpc an element made at R0 travels before it settles: a fountain's epicycle, by weight (enrichment.py)."""
    from xylarium.kernel import enrichment
    return enrichment.travel_kpc(element, R0_KPC)


def abundance(element: str, r: float) -> float:
    """An element's abundance in today's gas at r relative to R0's (enrichment.py)."""
    from xylarium.kernel import creation, enrichment
    here = enrichment.relative(None, element, r, creation.TODAY_GYR)
    there = enrichment.relative(None, element, R0_KPC, creation.TODAY_GYR)
    return here / there if there > 0 else 0.0


def first_of_its_ring(kernel: Any, cell: Tuple[int, int], k: int) -> bool:
    """Was this slot's star of its own ring's first generation - born within the first e-fold of that ring's star
    formation (its infall timescale after the first stars)? Inside-out: the core's first generation is early, the
    rim's late; where a star stands sets what 'first' means for it."""
    from xylarium.kernel import creation
    r = ring_radius(int(cell[0]))
    s = cosmos_seed(kernel)
    slot = creation.cell(s, int(cell[0]), int(cell[1]))[int(k)]
    if "born" not in slot:
        return False
    return slot["born"] - creation.first_stars(s) <= creation.infall_gyr(s, r)


def ancient_window(kernel: Any) -> float:
    """How long after the galaxy's first mind another still counts among the first: one e-fold of the fastest star
    formation anywhere - the core's own assembly time (Gyr)."""
    from xylarium.kernel import creation
    return creation.infall_gyr(cosmos_seed(kernel), 0.0)


def first_of_the_galaxy(kernel: Any, cell: Tuple[int, int], k: int) -> bool:
    """Was this slot's star of the galaxy's first generation - born within one core assembly time of the galaxy's
    first stars? The galaxy forms inside-out, so only the inner rings had stars that early: age and place at once."""
    from xylarium.kernel import creation
    s = cosmos_seed(kernel)
    slot = creation.cell(s, int(cell[0]), int(cell[1]))[int(k)]
    return "born" in slot and slot["born"] - creation.first_stars(s) <= ancient_window(kernel)


def in_core(mind: Dict[str, Any]) -> bool:
    """Was a mind born in the galaxy's core - its ring inside the bulge (R_BULGE_KPC)?"""
    return ring_radius(int(mind["cell"][0])) <= R_BULGE_KPC


def is_ancient(kernel: Any, mind: Dict[str, Any], first_core_dawn: float) -> bool:
    """An ancient by birth: among the earliest minds of the core - born in the core, waking within one core assembly
    time of the core's first mind. (A people may also become an ancient by its deeds: board.ancient_peoples.)"""
    return in_core(mind) and float(mind["epoch"]) - first_core_dawn <= ancient_window(kernel)


def omega(r: float) -> float:
    """rad per deep Myr on the flat rotation curve."""
    return V_FLAT_KMS * KPC_PER_MYR_AT_1KMS / max(0.05, r)


def pace(kernel: Any) -> str:
    p = ((getattr(kernel, "state", None) or {}).get("genesis") or {}).get("pace") or "neighbourly"
    return p if p in PACES else "neighbourly"


def ceiling(kernel: Any) -> float:
    """The fastest deep time runs (deep years per clock year): the pace chosen at genesis - how fast the galaxy turns
    while no people is in the middle of its history."""
    return PACES[pace(kernel)]


def ruler(kernel: Any) -> float:
    """Deep years per clock year now (tempo.py sets it from the living; the ceiling until it has)."""
    segs = stats(kernel).get("tempo") if "cosmos" in getattr(kernel, "state", {}) else None
    return float(segs[-1][2]) if segs else ceiling(kernel)


def _segment(kernel: Any, c: float) -> List[float]:
    st = stats(kernel)
    segs = st.get("tempo")
    if not segs:
        return [0, float(st.get("epoch0", 0.0)), ceiling(kernel)]
    lo, hi = 0, len(segs) - 1
    if c < segs[0][0]:
        return segs[0]
    while lo < hi:                                        # the last segment begun by cycle c
        mid = (lo + hi + 1) // 2
        if segs[mid][0] <= c:
            lo = mid
        else:
            hi = mid - 1
    return segs[lo]


def deep_gyr(kernel: Any, cycle: Optional[int] = None, sector_id: Optional[int] = None) -> float:
    """The deep-time epoch (Gyr since the Big Bang) at a clock cycle: deep time accumulated through every change of
    the clock's rate (tempo.py) - the camera's speed changes, never what it films. Asked for a place, the place's
    own now: its lapse times cosmic time - fixed by where it stands, nothing else (clocks.py)."""
    c = kernel.cycle_count if cycle is None else cycle
    if sector_id is not None:
        from xylarium.kernel import clocks
        local = clocks.place_now(kernel, sector_id, c)
        if local is not None:
            return local
    return cosmic_gyr(kernel, c)


def cosmic_gyr(kernel: Any, cycle: Optional[int] = None) -> float:
    """Cosmic time (Gyr since the Big Bang) at a clock cycle: the gauge, accumulated through every change of the one
    camera's rate."""
    c = kernel.cycle_count if cycle is None else cycle
    c0, d0, rate = _segment(kernel, c)
    return float(d0) + (c - c0) / 100.0 * float(rate) / 1.0e9


def cycle_at(kernel: Any, epoch: float) -> int:
    """The clock cycle at which deep time reaches an epoch (at the rates set so far; the current rate beyond)."""
    st = stats(kernel)
    segs = st.get("tempo") or [[0, float(st.get("epoch0", 0.0)), ceiling(kernel)]]
    seg = segs[0]
    for s in segs:
        if float(s[1]) <= epoch:
            seg = s
    return int(round(seg[0] + (epoch - float(seg[1])) * 1.0e9 / float(seg[2]) * 100.0))


# ---------------------------------------------------------------------- the two eras
LIVE_YEARS_PER_YEAR = 1.0       # in the live era a clock year IS a standard year (physics.CYCLES_PER_STANDARD_YEAR
                                # cycles): the clock is the captains' - a definition, not a rate chosen


def opened(kernel: Any) -> Optional[Dict[str, Any]]:
    """When the universe was opened to live play, if it has been: the deep era is over."""
    if kernel is None or "cosmos" not in getattr(kernel, "state", {}):
        return None
    return stats(kernel).get("opened")


def live(kernel: Any) -> bool:
    """Is the universe in its live era: one clock, locked to the captains' scale, whoever is watching?"""
    return opened(kernel) is not None


def open_universe(kernel: Any, by: str = "the progenitors") -> Dict[str, Any]:
    """The deep era ends: the architects have laid the board, and from now on deep time runs at the captains' scale -
    a clock year is a standard year - and no seat speeds it up or slows it down. Every seat above the captains acts on
    its own cadence, on this one clock."""
    got = opened(kernel)
    if got is not None:
        return got
    from xylarium.kernel import history
    set_rate(kernel, LIVE_YEARS_PER_YEAR)
    rec = stats(kernel)["opened"] = {"cycle": int(kernel.cycle_count), "epoch": round(deep_gyr(kernel), 9),
                                     "by": by}
    history.event(kernel, "UNIVERSE_OPENED", "The universe opens", actors=[],
                  cause=f"{by} end the deep era: from now on one clock, at the captains' scale, for every seat",
                  data={"epoch": rec["epoch"]})
    return rec


def set_rate(kernel: Any, rate: float) -> None:
    """From this cycle on, deep time runs at `rate` deep years per clock year."""
    st = stats(kernel)
    now = kernel.cycle_count
    d = deep_gyr(kernel, now)
    segs = st.setdefault("tempo", [])
    if not segs:
        segs.append([0, float(st.get("epoch0", 0.0)), ceiling(kernel)])   # the clock ran at the ceiling until now
    if segs and segs[-1][0] == now:
        segs[-1] = [now, d, float(rate)]
    else:
        segs.append([now, d, float(rate)])


# ---------------------------------------------------------------------- minds arise (creation.py)
WINDOW = 64                     # minds kept ahead in the kernel; the rest are the seed's, read when needed
CURVE_STEP = 0.25               # Gyr between points of the expectation curve (creation.CURVE_STEP)


def schedule(kernel: Any) -> Dict[str, Any]:
    """Every mind the home galaxy raises before the horizon, on the worlds its cells hold, with the expectation the
    initial conditions are drawn from (the audit of the scales). A pure function of the seed (creation.schedule)."""
    from xylarium.kernel import creation
    return creation.schedule(cosmos_seed(kernel))


def expected_by(kernel: Any, epoch: float) -> float:
    curve = stats(kernel).get("curve") or [0.0]
    x = max(0.0, epoch) / CURVE_STEP
    i = min(len(curve) - 1, int(x))
    j = min(len(curve) - 1, i + 1)
    return curve[i] + (curve[j] - curve[i]) * (x - i)


def _refill(kernel: Any) -> None:
    """Keep the next WINDOW minds in the kernel."""
    from xylarium.kernel import creation
    st = stats(kernel)
    st["minds"] = creation.after(cosmos_seed(kernel), st.get("last"), WINDOW)
    st["next"] = 0


# ---------------------------------------------------------------------- the map: cells <-> regions
ADJECTIVES = ["Veiled", "Obsidian", "Cosmic", "Tesseract", "Supernova", "Prismatic", "Hyperion", "Eclipse"]
NOUNS = ["Rift", "Spire", "Shoals", "Chasm", "Nexus", "Matrix", "Sanctum", "Abyss"]


def _index(kernel: Any) -> Dict[str, int]:
    return stats(kernel)["region_of"]


def region_of_cell(kernel: Any, cell: Tuple[int, int]) -> int:
    """The region a cell is carried by - a label in the order cells are first witnessed (1 for the first witness's);
    what the cell holds does not depend on it (creation.py)."""
    st = stats(kernel)
    key = f"{cell[0]},{cell[1]}"
    idx = _index(kernel)
    if key not in idx:
        idx[key] = st["next_region"]
        st["next_region"] += 1
    return idx[key]


def cell_of_sector(kernel: Any, sector_id: int) -> Optional[Tuple[int, int]]:
    g = stats(kernel)["place"].get(str(sector_id))
    if g and "cell" in g:
        return int(g["cell"][0]), int(g["cell"][1])
    return None


def sector_of_slot(kernel: Any, cell: Tuple[int, int], k: int) -> int:
    """The sector id carrying a cell's slot: the first witness's region is sectors 1-40, its home slot sector 1."""
    region = region_of_cell(kernel, cell)
    if region == 1:
        return 1 + (k - int(stats(kernel).get("home_slot", 0))) % SLOTS
    return 201 + (region - 2) * SLOTS + k


def _sectors_of_region(region: int) -> List[int]:
    return list(range(1, SLOTS + 1)) if region == 1 else list(range(201 + (region - 2) * SLOTS,
                                                                    201 + (region - 1) * SLOTS))


def materialised(kernel: Any, cell: Tuple[int, int]) -> bool:
    """Charted: all its sectors and lanes on the map."""
    return f"{cell[0]},{cell[1]}" in stats(kernel)["materialised"]


@matter.declared("cluster_genesis")
def build_slot(kernel: Any, cell: Tuple[int, int], k: int) -> int:
    """One sample volume of a cell onto the map (declared: what it brings is new to the census)."""
    return _build_slot(kernel, cell, k)


def _build_slot(kernel: Any, cell: Tuple[int, int], k: int) -> int:
    """One sample volume of a cell onto the map, as the Big Bang made it: a star (lit if born by now, gas until
    then), or the null space between, with its belts."""
    from xylarium.config import BELT_TYPES
    from xylarium.kernel import creation
    from xylarium.kernel.models import Sector, SecurityLevel
    sid = sector_of_slot(kernel, cell, k)
    if sid in kernel.sectors:
        return sid
    slot = creation.cell(cosmos_seed(kernel), *cell)[k]
    sec = Sector(id=sid, name=f"{ADJECTIVES[slot['names'][0]]} {NOUNS[slot['names'][1]]} #{sid}",
                 security=SecurityLevel.ANARCHY, warps=[], port=None, planets=[], captains=[])
    sec.cluster_name = f"Ring {cell[0]}, arc {cell[1]}"
    sec.kind, sec.star_type, sec.star = "NULL", None, None
    kernel.sectors[sid] = sec
    place = {"r": slot["r"], "theta0": slot["theta0"], "cell": [cell[0], cell[1]], "k": k}
    stats(kernel)["place"][str(sid)] = place
    if "star" not in slot:
        sec.belts = [{"id": f"BELT-{sid:03d}-{n + 1}", "type": b[0], "composition": dict(BELT_TYPES[b[0]]),
                      "reserve": b[1], "max_reserve": b[1]} for n, b in enumerate(slot["belts"])]
        return sid
    place["born"] = slot["born"]
    if slot["born"] <= deep_gyr(kernel):
        _light(kernel, sid, slot)
    else:
        stats(kernel)["unborn"][str(sid)] = slot["born"]
    return sid


def _light(kernel: Any, sid: int, slot: Dict[str, Any]) -> None:
    """A star is born and its worlds with it."""
    from xylarium.kernel import physics
    from xylarium.kernel.fx import currency_for_security
    from xylarium.kernel.models import Planet
    from xylarium.kernel.universe import PLANET_LETTERS
    sec = kernel.sectors[sid]
    sec.kind, sec.star_type = "SYSTEM", slot["star"]
    sec.star = dict(slot["spec"]) if slot.get("spec") else physics.star_for(sec.star_type)   # its own mass and light
    from xylarium.config import BELT_TYPES
    sec.belts = [{"id": f"BELT-{sid:03d}-{n + 1}", "type": b[0],
                  "composition": dict(b[2] if len(b) > 2 and b[2] else BELT_TYPES.get(b[0], {})),
                  "reserve": b[1], "max_reserve": b[1]} for n, b in enumerate(slot.get("belts", []))]
    for b in sec.belts:
        matter.source("star_formation", "BELT_ROCK", b["reserve"])      # its belts are born with it
    currency = currency_for_security(sec.security)
    ids: Dict[int, Any] = {}
    letters, moons = 0, {}
    for n, w in enumerate(slot["worlds"]):
        host = ids.get(w["host"]) if "host" in w else None
        if host is None:
            pid = f"planet_{sid}" if letters == 0 else f"planet_{sid}_{PLANET_LETTERS[letters % len(PLANET_LETTERS)]}" \
                + ("" if letters < len(PLANET_LETTERS) else str(letters // len(PLANET_LETTERS)))
            name = f"{sec.name.split()[0]} {sid:03d}{PLANET_LETTERS[letters % len(PLANET_LETTERS)]}"
            letters += 1
        else:                                       # a giant's moon: named for it, numbered outward
            moons[host.id] = moons.get(host.id, 0) + 1
            pid, name = f"{host.id}_m{moons[host.id]}", f"{host.name} {_ROMAN[moons[host.id] - 1]}"
        body = dict(w["body"])
        if host is not None:
            body["parent"] = host.id
        p = Planet(id=pid, sector_id=sid, name=name, owner_id=None, population=0, shields=0,
                   max_shields=200, fighters=0, citadel_level=0, treasury=0, ore_silo=0, organics_silo=0, morale=80,
                   element_deposits=dict(w["deposits"]), garrison_troops=0, planet_type=w["type"],
                   currency=currency, body=body)
        if host is not None:
            p.moon_of = host.id
        ids[n] = p
        physics.apply_derived(p, physics.star(sec))
        p.orbital_angle = float(physics.orbital_phase(sec, p, 0)) * 360.0
        sec.planets.append(p)


_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


def _none_due(kernel: Any) -> bool:
    now = deep_gyr(kernel)
    return not any(born <= now for born in stats(kernel)["unborn"].values())


@matter.declared("star_formation", idle=_none_due)
def _ignite(kernel: Any) -> List[str]:
    """Charted gas whose date has come: its star is born (systems emerge over deep time, each on the date the
    Big Bang fixed for it)."""
    from xylarium.kernel import creation, history
    st = stats(kernel)
    now = deep_gyr(kernel)
    logs = []
    for key, born in sorted(st["unborn"].items(), key=lambda kv: (kv[1], int(kv[0]))):
        if born > now:
            continue
        sid = int(key)
        st["unborn"].pop(key)
        g = st["place"][key]
        slot = creation.cell(cosmos_seed(kernel), *g["cell"])[g["k"]]
        _light(kernel, sid, slot)
        sec = kernel.sectors[sid]
        history.event(kernel, "STAR_BORN", f"A star is born in {sec.name}", sector_id=sid,
                      cause=f"its ring's gas, {born:.3f} Gyr after the Big Bang",
                      data={"star": slot["star"], "worlds": len(slot["worlds"])})
        logs.append(f"[COSMOS] A star is born in {sec.name}: {slot['star']}, {len(slot['worlds'])} worlds.")
    if logs:
        from xylarium.kernel import topology
        topology.changed(kernel)
    return logs


def _lanes_within(kernel: Any, cell: Tuple[int, int]) -> None:
    """A charted cell's own lanes: a chain through its sectors and a cross-stitch, fixed by the cell (not by who
    charted it)."""
    from xylarium.kernel import scheduler
    rng = scheduler.rng(kernel, "lanes", *cell)
    order = list(range(SLOTS))
    rng.shuffle(order)
    edges = set()
    for a, b in zip(order, order[1:]):
        edges.add((min(a, b), max(a, b)))
    deg = {k: 0 for k in range(SLOTS)}
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    for k in range(SLOTS):
        c = rng.randrange(SLOTS)
        if c != k and deg[k] < 4 and (min(k, c), max(k, c)) not in edges:
            edges.add((min(k, c), max(k, c)))
            deg[k] += 1
            deg[c] += 1
    for a, b in sorted(edges):
        sa, sb = sector_of_slot(kernel, cell, a), sector_of_slot(kernel, cell, b)
        kernel.sectors[sa].warps = sorted(set(kernel.sectors[sa].warps) | {sb})
        kernel.sectors[sb].warps = sorted(set(kernel.sectors[sb].warps) | {sa})


@matter.declared("cluster_genesis", idle=lambda kernel, cell, why: materialised(kernel, cell))
def materialise(kernel: Any, cell: Tuple[int, int], why: str) -> Optional[str]:
    """A cell is charted: every sector it carries is laid out as the Big Bang made it, its own lanes drawn, and it
    is joined to whatever neighbours are already charted."""
    key = f"{cell[0]},{cell[1]}"
    st = stats(kernel)
    if key in st["materialised"]:
        return None
    region = region_of_cell(kernel, cell)
    for k in range(SLOTS):
        _build_slot(kernel, cell, k)                      # one census for the whole cell (materialise is declared)
    _lanes_within(kernel, cell)
    _stars(kernel, [sector_of_slot(kernel, cell, k) for k in range(SLOTS)])   # found as its stars are now
    st["materialised"].append(key)
    _join(kernel, cell)
    from xylarium.kernel import topology
    topology.changed(kernel)
    i, j = cell
    return f"[COSMOS] Region {region} (ring {i}, arc {j}, {ring_radius(i):.1f} kpc out) is charted: {why}."


def _gates(region: int) -> List[int]:
    return _sectors_of_region(region)[:3]



def _link(kernel: Any, ra: int, rb: int, on: bool) -> None:
    for a, b in zip(_gates(ra), _gates(rb)):
        if a not in kernel.sectors or b not in kernel.sectors:
            continue
        if on:
            kernel.sectors[a].warps = sorted(set(kernel.sectors[a].warps) | {b})
            kernel.sectors[b].warps = sorted(set(kernel.sectors[b].warps) | {a})
        else:
            kernel.sectors[a].warps = [w for w in kernel.sectors[a].warps if w != b]
            kernel.sectors[b].warps = [w for w in kernel.sectors[b].warps if w != a]


def _join(kernel: Any, cell: Tuple[int, int]) -> None:
    """Lanes to the charted cells beside it on its own ring (they turn together); across rings, the shear decides
    (_shear) who its neighbours are now."""
    mine = region_of_cell(kernel, cell)
    for nb in neighbours(*cell):
        if nb[0] == cell[0] and materialised(kernel, nb):
            _link(kernel, mine, region_of_cell(kernel, nb), True)
    _shear(kernel)


# ---------------------------------------------------------------------- the stars' lives
AGEING_SHARE = 0.1              # the last tenth of a star's main-sequence life: the giant branch
RGB_TIP_LSUN = 2500.0           # luminosity at the red-giant branch tip (solar; measured)
GIANT_REACH_AU = 1.0            # a giant near its tip is ~200 solar radii (~1 AU): what lies inside is engulfed
WD_LSUN = 1.0e-3                # a young white dwarf's light
WD_MASS = 0.6                   # what a white dwarf keeps of its star (solar masses)
EJECTA_PER_SUN = 150            # deposit units a solar mass of shed matter seeds (a world's worth of an element)
CORE_COLLAPSE_SUNS = 8.0        # above this a star's core collapses
BLACK_HOLE_SUNS = 20.0          # above this the collapse leaves a black hole, below a neutron star
R_BULGE_KPC = 2.0               # within it, a dying star's remains fall to the galactic centre (blackhole.py)


def star_life(kernel: Any, sector_id: int) -> Optional[Tuple[float, float]]:
    """(when the star formed, when it leaves the main sequence), in Gyr since the Big Bang."""
    from xylarium.kernel import physics
    g = stats(kernel)["place"].get(str(sector_id))
    sec = kernel.sectors.get(sector_id)
    if not g or sec is None:
        return None
    if "remnant" in (getattr(sec, "star_type", "") or "").lower():
        return (0.0, 0.0)

    def compute() -> Optional[Tuple[float, float]]:
        try:
            st = physics.star(sec)
            m, lum = float(st["mass"]), float(st["luminosity"])
        except Exception:
            return None
        born = float(g.get("born", formed_gyr(g["r"])))
        from xylarium.kernel import fundamental
        nuclear = fundamental.of(cosmos_seed(kernel)).nuclear
        return born, born + SUN_MS_GYR * nuclear * m / max(1e-9, lum)     # its fuel over its burn
    if not hasattr(kernel, "caches"):
        return compute()
    from xylarium.kernel import cache                    # it changes only with its star (a death replaces it)
    stamp = (getattr(sec, "star_type", None), id(getattr(sec, "star", None)), g.get("born"), g.get("r"))
    return cache.stamped(kernel, "star_life", sector_id, stamp, compute)


def death_kind(kernel: Any, sector_id: int) -> str:
    """How it ends: a star above eight suns collapses its core (a core-collapse supernova, leaving a neutron star
    or, above ~20 suns, a black hole); below that a binary's white dwarf takes its companion's matter until it
    detonates (a Type Ia supernova), and a single star sheds its envelope and leaves a white dwarf."""
    from xylarium.kernel import physics
    sec = kernel.sectors.get(sector_id)
    if sec is None:
        return "white_dwarf"
    try:
        m = float(physics.star(sec)["mass"])
    except Exception:
        m = 1.0
    from xylarium.kernel import fundamental
    if m >= CORE_COLLAPSE_SUNS * fundamental.of(cosmos_seed(kernel)).star_mass:     # a share of the Chandrasekhar scale
        return "core_collapse"
    return "supernova" if "binary" in (sec.star_type or "").lower() else "white_dwarf"


def phase(kernel: Any, sector_id: int, at_gyr: Optional[float] = None) -> Tuple[str, float]:
    """('main' | 'giant' | 'dead', how far through the giant branch 0..1)."""
    life = star_life(kernel, sector_id)
    if life is None:
        return "main", 0.0
    born, ends = life
    if ends <= born:
        return "dead", 1.0
    t = deep_gyr(kernel, sector_id=sector_id) if at_gyr is None else at_gyr
    if t >= ends:
        return "dead", 1.0
    span = AGEING_SHARE * (ends - born)
    return ("giant", (t - (ends - span)) / span) if t > ends - span else ("main", 0.0)


def luminosity_factor(kernel: Any, sector_id: int, at_gyr: Optional[float] = None) -> float:
    """The star's light now over its main-sequence light: climbing the giant branch toward the tip as the square of
    its progress (the climb is steepest at the end); after death a remnant's or nothing."""
    from xylarium.kernel import physics
    ph, s = phase(kernel, sector_id, at_gyr)
    if ph == "main":
        return 1.0
    sec = kernel.sectors.get(sector_id)
    try:
        l0 = float(physics.star(sec)["luminosity"])
    except Exception:
        l0 = 1.0
    if ph == "giant":
        return max(1.0, RGB_TIP_LSUN / max(1e-6, l0)) ** (s * s)
    return 1.0                                       # dead: the sector's star is already its remnant (_death)


def lum(sector_id: int) -> float:
    """The luminosity factor this season (physics.planet_flux reads it)."""
    from xylarium.kernel import ledger
    k = ledger.active_kernel()
    if k is None or "cosmos" not in getattr(k, "state", {}):
        return 1.0
    return float(stats(k)["lum"].get(str(sector_id), 1.0))


def star_factor(kernel: Any, sector_id: int, at_gyr: Optional[float] = None) -> float:
    """1 while the star lives (its light, however fierce, is the biology's problem: light fit); 0 once dead."""
    return 0.0 if phase(kernel, sector_id, at_gyr)[0] == "dead" else 1.0


def years_left(kernel: Any, sector_id: int) -> Optional[float]:
    """Clock years until the star dies."""
    life = star_life(kernel, sector_id)
    if life is None:
        return None
    from xylarium.kernel import clocks
    pace = clocks.place_rate(kernel, sector_id) or ruler(kernel)
    return max(0.0, (life[1] - deep_gyr(kernel, sector_id=sector_id)) * 1.0e9 / pace)


def forecasts(kernel: Any, sector_id: int, mastery: float) -> bool:
    """Whether a people that knows this much of stellar physics (its energy mastery) can read its star's end now:
    once the fraction of the star's life still ahead falls to what it knows."""
    life = star_life(kernel, sector_id)
    if life is None or life[1] <= life[0]:
        return False
    ahead = (life[1] - deep_gyr(kernel, sector_id=sector_id)) / (life[1] - life[0])
    return ahead <= mastery or phase(kernel, sector_id)[0] == "giant"


def _stars(kernel: Any, sector_ids: Optional[List[int]] = None) -> List[str]:
    """Each witnessed star's light, its swelling and its death."""
    from xylarium.kernel import history
    st = stats(kernel)
    logs = []
    quiet = sector_ids is not None                   # found as it is when first witnessed: no news
    ids = sector_ids if quiet else [int(s) for s in st["place"]]
    for sid in ids:
        sec = kernel.sectors.get(sid)
        if sec is None or not sec.planets:
            continue
        ph, _ = phase(kernel, sid)
        f = round(luminosity_factor(kernel, sid), 4)
        if f != 1.0:
            st["lum"][str(sid)] = f
        else:
            st["lum"].pop(str(sid), None)
        was = st["phase"].get(str(sid), "main")
        if ph == was:
            continue
        st["phase"][str(sid)] = ph
        peopled = [p for p in sec.planets if p.population > 0]
        who = sorted({f"civ:{p.civilization.name}" for p in peopled if getattr(p, "civilization", None) is not None})
        if ph == "giant" and not quiet:
            history.event(kernel, "STAR_AGEING", f"The star of {sec.name} begins to swell", sector_id=sid, actors=who,
                          cause=f"its giant branch: {years_left(kernel, sid):,.0f} clock years left")
            if peopled:
                logs.append(f"[COSMOS] The star of {sec.name} begins to swell.")
        if ph == "dead":
            line = _death(kernel, sid, quiet)
            if line and not quiet:
                logs.append(line)
    return logs


def _death(kernel: Any, sid: int, quiet: bool) -> Optional[str]:
    """A star dies: a white dwarf (worlds inside the giant engulfed, the rest frozen in its faint light) or a Type Ia
    supernova (every world flung out of the dead system, a rogue). Its shed matter seeds its region - or, inside the
    bulge, falls with what it unbound to the galactic centre (blackhole.py)."""
    from xylarium.kernel import blackhole, history, physics
    sec = kernel.sectors[sid]
    kind = death_kind(kernel, sid)
    r = float(stats(kernel)["place"].get(str(sid), {}).get("r", R0_KPC))
    try:
        m = float(physics.star(sec)["mass"])
    except Exception:
        m = 1.0
    to_centre = r < R_BULGE_KPC
    from xylarium.kernel import zones
    zones.touch_sector(kernel, sid)                           # its worlds are brought to now before their star ends
    lost = 0
    who = sorted({f"civ:{p.civilization.name}" for p in sec.planets
                  if p.population > 0 and getattr(p, "civilization", None) is not None})
    for p in sec.planets:
        if p.population > 0:
            lost += p.population
            _perish(kernel, p, kind)
        p.society["star_k"] = 0.0
        a = float(physics.body(p).get("q", 1) or 1) ** 2
        unbound = kind in ("supernova", "core_collapse") or a < GIANT_REACH_AU
        if unbound:
            if to_centre:
                blackhole.capture(kernel, dict(p.element_deposits), f"the worlds of {sec.name}", records=who,
                                  suns=float(physics.body(p).get("mass", 1) or 1) * blackhole.EARTH_SUNS)
            elif a < GIANT_REACH_AU and kind == "white_dwarf":
                for el, q in p.element_deposits.items():
                    matter.sink("stellar_engulfment", el, q)        # swallowed by its own star
            if to_centre or (a < GIANT_REACH_AU and kind == "white_dwarf"):
                p.element_deposits = {el: 0 for el in p.element_deposits}
            if kind in ("supernova", "core_collapse"):
                p.planet_type = "ROGUE"                              # flung out: dark, drifting
        if hasattr(p, "_orbit_cache"):
            del p._orbit_cache
    from xylarium.kernel import fundamental
    scale = fundamental.of(cosmos_seed(kernel)).star_mass               # remnants are shares of the Chandrasekhar mass
    heavy = m >= BLACK_HOLE_SUNS * scale
    remnant = WD_MASS * scale if kind == "white_dwarf" else 0.0 if kind == "supernova" else \
        (1.4 * scale if not heavy else 0.5 * m)                         # a neutron star, or a black hole
    shed = max(0.0, m - remnant)
    yields = ({"C": 0.5, "H2O": 0.3, "Si": 0.2} if kind == "white_dwarf" else
              {"Fe": 0.6, "Ni": 0.2, "Si": 0.15, "U": 0.05} if kind == "supernova" else
              {"H2O": 0.45, "Si": 0.2, "C": 0.15, "Fe": 0.12, "Ni": 0.03, "U": 0.05})   # what each death makes
    units = {el: int(max(0.0, shed) * EJECTA_PER_SUN * w) for el, w in yields.items()}
    if to_centre:
        blackhole.capture(kernel, units, f"the remains of the star of {sec.name}", made=True, records=who,
                          suns=shed)
    else:
        worlds = [p for s2 in kernel.sectors.values() if s2.id in _region_sectors(kernel, sid) for p in s2.planets]
        for w in worlds:
            zones.touch(kernel, w)                            # brought to now before the ejecta reach them
        for i, (el, q) in enumerate(sorted(units.items())):
            for j, w in enumerate(worlds):
                share = q // max(1, len(worlds)) + (1 if j < q % max(1, len(worlds)) else 0)
                if share:
                    w.element_deposits[el] = w.element_deposits.get(el, 0) + share
                    got = w.society.setdefault("delivered", {})          # delivered: no survey forgets it
                    got[el] = got.get(el, 0) + share
                    matter.source("stellar_ejecta", el, share)          # made in the star, now in the worlds
    sec.star_type = ("White dwarf remnant" if kind == "white_dwarf" else "Supernova remnant" if kind == "supernova"
                     else "Neutron star remnant" if not heavy else "Black hole remnant")
    sec.star = physics.star_for(sec.star_type)
    st = stats(kernel)
    st["deaths"][kind] = st["deaths"].get(kind, 0) + 1
    if quiet:
        return None
    history.event(kernel, "STAR_DEATH", f"The star of {sec.name} dies" + (
                      " in a supernova" if kind == "supernova" else ", leaving a white dwarf" if kind == "white_dwarf"
                      else " as its core collapses"),
                  sector_id=sid, magnitude=lost, actors=who, cause=f"it left the main sequence ({m:.2f} suns)",
                  data={"kind": kind, "to_centre": to_centre, "ejecta": units})
    return f"[COSMOS] The star of {sec.name} dies ({kind.replace('_', ' ')})" + (f": {lost:,} perish." if lost else ".")


def _perish(kernel: Any, planet: Any, kind: str) -> None:
    """Those still on a world when its star dies die with it (the government that could have moved them answers
    for it - exodus.py); a people's ruins remain where a world remains."""
    from xylarium.kernel import exodus
    exodus.perished(kernel, planet, planet.population, kind)
    from xylarium.kernel.archaeology import ArchaeologyManager
    planet.population = 1
    ArchaeologyManager.check_collapse(planet, True, kernel)
    planet.population = 0


def _region_sectors(kernel: Any, sector_id: int) -> List[int]:
    cell = cell_of_sector(kernel, sector_id)
    if cell is None:
        return [sector_id]
    return [s for s in _sectors_of_region(region_of_cell(kernel, cell)) if s in kernel.sectors]


# ---------------------------------------------------------------------- the shear
def _centre(i: int, j: int, t_myr: float) -> float:
    return cell_theta(i, j) + omega(ring_radius(i)) * t_myr


def overlap(a: Tuple[int, int], b: Tuple[int, int], t_myr: float) -> float:
    """How much of the narrower of two cells on neighbouring rings faces the other now (0 when they no longer
    touch): the inner ring turns faster (a flat rotation curve), so cells slide past one another."""
    ha, hb = math.pi / slots(a[0]), math.pi / slots(b[0])
    d = (_centre(*a, t_myr) - _centre(*b, t_myr) + math.pi) % (2 * math.pi) - math.pi
    return max(0.0, min(1.0, (ha + hb - abs(d)) / (2 * min(ha, hb))))


def neighbours_now(kernel: Any, cell: Tuple[int, int]) -> List[Tuple[int, int]]:
    """The cells beside it on its ring, and those facing it now on the rings either side."""
    t = deep_gyr(kernel) * 1000.0
    i, j = cell
    out = [n for n in neighbours(i, j) if n[0] == i]
    for k in (i - 1, i + 1):
        if 0 <= k < rings():
            out += [(k, jj) for jj in range(slots(k)) if overlap(cell, (k, jj), t) > 0]
    return sorted(set(out))


def stretch(kernel: Any, a: int, b: int) -> float:
    """A lane between rings costs more as its ends slide apart (1 / the share of the cells still facing)."""
    if not is_cosmic(kernel):
        return 1.0
    return float(stats(kernel)["stretch"].get(f"{min(a, b)}-{max(a, b)}", 1.0))


def _shear(kernel: Any) -> List[str]:
    """Across rings, lanes open as cells come to face each other and close as they slide apart."""
    st = stats(kernel)
    t = deep_gyr(kernel) * 1000.0
    by_ring: Dict[int, List[Tuple[int, int]]] = {}
    for key in st["materialised"]:
        c = tuple(int(x) for x in key.split(","))
        by_ring.setdefault(c[0], []).append(c)
    pairs = [(a, b) for i in sorted(by_ring) for a in by_ring[i] for b in by_ring.get(i + 1, [])]
    cross, stretches = st["cross"], {}
    logs, changed = [], False
    for a, b in pairs:
        if True:
            ra, rb = region_of_cell(kernel, a), region_of_cell(kernel, b)
            key = f"{min(ra, rb)}-{max(ra, rb)}"
            f = overlap(a, b, t)
            if f > 0 and key not in cross:
                _link(kernel, ra, rb, True)
                cross[key] = kernel.cycle_count
                changed = True
                logs.append(_lane_event(kernel, "LANE_OPEN", ra, rb, "their cells turn to face each other"))
            elif f <= 0 and key in cross:
                _link(kernel, ra, rb, False)
                cross.pop(key)
                changed = True
                logs.append(_lane_event(kernel, "LANE_CLOSE", ra, rb, "the inner ring turns faster: they slide apart"))
            if key in cross:
                for g, h in zip(_gates(ra), _gates(rb)):
                    stretches[f"{min(g, h)}-{max(g, h)}"] = round(1.0 / max(0.05, f), 3)
    st["stretch"] = stretches
    if changed:
        from xylarium.kernel import topology
        topology.changed(kernel)
    return logs


def _lane_event(kernel: Any, kind: str, ra: int, rb: int, cause: str) -> str:
    """Told only where a people among the stars lives at either end (history mutes the rest)."""
    from xylarium.kernel import history, knowledge
    verb = "open" if kind == "LANE_OPEN" else "close"
    who = sorted({knowledge.holder_of_planet(p) or "" for r in (ra, rb) for s in _sectors_of_region(r)
                  if s in kernel.sectors for p in kernel.sectors[s].planets
                  if p.population > 0 and getattr(p, "civilization", None) is not None})
    history.event(kernel, kind, f"The lanes between regions {ra} and {rb} {verb}", sector_id=_gates(ra)[0],
                  actors=who, cause=cause, data={"regions": [ra, rb]})
    return f"[COSMOS] The lanes between regions {ra} and {rb} {verb}: {cause}."


def position(kernel: Any, sector_id: int, cycle: Optional[int] = None) -> Optional[Dict[str, float]]:
    """Where a system is in the galaxy at a clock cycle: closed-form rotation on deep time and its oscillation through
    the plane (x, y, z in kpc), and how fast its own clock runs against the universe's there (geometry.lapse)."""
    from xylarium.kernel import geometry
    g = stats(kernel)["place"].get(str(sector_id))
    if not g:
        return None
    t = deep_gyr(kernel, cycle)
    th = g["theta0"] + omega(g["r"]) * t * 1000.0
    z = 0.0
    if "cell" in g:
        from xylarium.kernel import creation
        v = creation.cell(cosmos_seed(kernel), *g["cell"])[g["k"]].get("vertical")
        if v:
            z = geometry.z_at(v, t, g["r"])
    return {"r": g["r"], "theta": round(th % (2 * math.pi), 6), "x": round(g["r"] * math.cos(th), 4),
            "y": round(g["r"] * math.sin(th), 4), "z": round(z, 4), "deep_gyr": round(t, 6),
            "lapse": geometry.lapse(g["r"], z, V_FLAT_KMS)}


def distance_kpc(kernel: Any, a: int, b: int, cycle: Optional[int] = None) -> Optional[float]:
    """The proper distance between two systems now: through the galaxy's own curved space (geometry.proper_kpc)."""
    from xylarium.kernel import geometry
    pa, pb = position(kernel, a, cycle), position(kernel, b, cycle)
    if not pa or not pb:
        return None
    return geometry.proper_kpc([pa["x"], pa["y"], pa["z"]], [pb["x"], pb["y"], pb["z"]])


# ---------------------------------------------------------------------- genesis and emergence
@matter.declared("cluster_genesis")
def genesis(kernel: Any) -> None:
    """The universe begins its clock when its first mind arises. Everything the settled generator laid out is
    unmade - the galaxy is the Big Bang's (creation.py) - and the first mind's own system becomes sector 1;
    everything else waits to be witnessed."""
    from xylarium.kernel import creation, institutions
    institutions.genesis(kernel)                       # no money, bank, exchange or Reserve until founded
    from xylarium.kernel import history
    history.event(kernel, "BIG_BANG", "The universe begins",
                  cause="the white hole of a black hole in a parent universe: matter that crossed its horizon bounced "
                        "at the Cartan density, and this spacetime is the other side",
                  data={"seed": str(cosmos_seed(kernel))})
    st = stats(kernel)
    sched = schedule(kernel)
    st["curve"], st["ever"] = sched["curve"], len(sched["minds"])
    st["big_bang"] = dict(creation.big_bang(cosmos_seed(kernel)))
    st["minds"] = sched["minds"][:WINDOW]
    if not st["minds"]:
        st["epoch0"] = 0.0
        return
    first = st["minds"][0]
    st["epoch0"] = first["epoch"]
    for sec in list(kernel.sectors.values()):          # the settled galaxy's map is not this universe's
        sec.planets, sec.belts, sec.warps = [], [], []
    kernel.sectors.clear()
    rm = getattr(kernel, "research_manager", None)
    if rm is not None:
        rm.anomalies.clear()                           # no relics before anyone lived to leave them
    from xylarium.kernel import cluster, sphere, topology
    cluster.genesis(kernel)                            # the galaxies around this one, as a formula
    sphere.genesis(kernel)                             # and the clusters around this one, on the closed universe
    home = tuple(first["cell"])
    st["region_of"][f"{home[0]},{home[1]}"] = 1
    st["home_slot"] = int(first["k"])
    topology.changed(kernel)
    _due(kernel)


def _due(kernel: Any) -> List[str]:
    from xylarium.kernel import lifeline
    st = stats(kernel)
    logs = []
    now = deep_gyr(kernel)
    for rec in lifeline.due(kernel, now):                     # lives re-resolved after a mind acted on their world
        line = arise(kernel, rec)
        if line:
            logs.append(line)
    while True:
        if st["next"] >= len(st["minds"]):
            if len(st["minds"]) < WINDOW:
                break                                         # the schedule is exhausted
            _refill(kernel)
            if not st["minds"]:
                break
        rec = st["minds"][st["next"]]
        if rec["epoch"] > now + 1e-12:
            break
        st["next"] += 1
        st["last"] = [rec["epoch"], rec["cell"], rec["k"], rec.get("w", 0)]
        if lifeline.overridden(kernel, rec):
            continue                                          # its world was disturbed: the forecast no longer holds
        line = arise(kernel, rec)
        if line:
            logs.append(line)
    return logs


def _name(kernel: Any, rec: Dict[str, Any]) -> str:
    """A name no other people bears (a people is known by its name: two of one name would be one people)."""
    from xylarium.kernel import scheduler
    from xylarium.kernel.natives import _name as syllables
    taken = set(stats(kernel).setdefault("names", []))
    rng = scheduler.rng(kernel, "name", *rec["cell"], rec["k"], rec.get("w", 0))
    name = syllables(rng)
    while name in taken:
        name = syllables(rng)
    stats(kernel)["names"].append(name)
    return name


def arise(kernel: Any, rec: Dict[str, Any]) -> Optional[str]:
    """A mind arises on the world the Big Bang's initial conditions gave it, in the biology that finished its hard steps first. Its
    own system comes onto the map, nothing more: the rest of its sky is description until someone sails into it.
    Natural selection has given it its body: a variable world (a tilted axis, a flaring red dwarf) breeds
    r-strategists, a steady one K-strategists."""
    from xylarium.kernel import biosphere, history, physics, primordial, scheduler, ways
    from xylarium.kernel.civilization import CivilizationIntelligenceEngine
    cell = tuple(rec["cell"])
    st = stats(kernel)
    sid = build_slot(kernel, cell, int(rec["k"]))
    _stars(kernel, [sid])
    sec = kernel.sectors[sid]
    w = int(rec["w"])
    p = sec.planets[w] if w < len(sec.planets) else None
    if (p is None or p.population > 0 or getattr(p, "civilization", None) is not None or p.owner_id
            or float(p.society.get("star_k", 1.0)) <= 0.0):
        st["silent"] += 1                                   # its world was taken, or its star died, before it woke
        return None
    metab = rec.get("metab") or "biotic"
    rng = scheduler.rng(kernel, "body", *cell, rec["k"], w)
    tilt = float(physics.body(p).get("tilt", 0) or 0)
    try:
        m = float(physics.star(sec)["mass"])
    except Exception:
        m = 1.0
    variable = tilt > 23.0 or m < 0.5
    strategy = "r" if variable else "K"
    traits = select(kernel, p, metab, strategy, rng)
    plan = traits["shape"]
    name = _name(kernel, rec)
    civ = CivilizationIntelligenceEngine.create_civilization({
        "name": name, "species_name": f"{plan}-{name.lower()}", "clade": traits["body"], "class_code": 0,
        "sigil": "*",
        "metabolism": metab, "disposition": "industry", "motto": "we looked up", "station": "arisen", "tech_level": 0})
    civ.traits = traits
    p.civilization = civ
    biosphere.adapt(kernel, civ, p)                       # it evolved under this light, on this ground
    p.owner_id = None
    p.citadel_level = 0
    p.treasury = 0
    p.society["way"] = "forage"
    p.society["crop_z"] = 0.0
    # it wakes at its forecast on the one cosmic clock, however coarsely the camera is stepping: the stretch between
    # its waking and the step that caught it is history it has lived, and the annals carry it there (annals.py)
    p.society["arisen"] = {"epoch": float(rec["epoch"]), "forecast": rec["epoch"], "caught": deep_gyr(kernel),
                           "cell": list(cell), "cycle": kernel.cycle_count}
    ways._refresh(kernel, p)
    p.population = max(500, int(biosphere.carrying_capacity(kernel, p)))
    from xylarium.config import FOOD_PER_THOUSAND
    from xylarium.kernel import staples
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES       # it wakes at harvest: a season the wild gives
    staples.add(p, staples.of(kernel, p), p.population * FOOD_PER_THOUSAND * FISCAL_QUARTER_CYCLES // 1000, "harvest")
    st["arisen"] += 1
    primordial.first(kernel, "first_mind", f"{name} of {p.name}")
    r = float(st["place"][str(sid)]["r"])
    steps = rec.get("steps") or []
    if steps:                                             # the world's deep history, now that someone can read it
        history.event(kernel, "DEEP_HISTORY", f"The deep history of {p.name}", actors=[f"civ:{name}"], planet=p,
                      text=f"Life began on {p.name} {(rec['epoch'] - steps[0]) * 1000:,.0f} million years before "
                           f"the {name}; it passed {len(steps)} hard steps"
                           + (f", thrown back {rec.get('setbacks', 0)} times by the impacts of its sky"
                              if rec.get("setbacks") else "") + ".",
                      data={"steps_gyr": steps, "setbacks": rec.get("setbacks", 0), "medium": traits["medium"]})
    history.event(kernel, "EMERGENCE", f"The {name} look up", actors=[f"civ:{name}"], planet=p,
                  magnitude=p.population, cause=f"after {len(steps) or HARD_STEPS} hard steps",
                  text=f"On {p.name}, {r:.1f} kpc from the galactic centre, under a star of {m:.2f} solar masses, "
                       f"in {traits['medium']}, a people became aware of itself: {traits['describe']} - "
                       f"the {name}.", data={"traits": traits, "epoch": float(rec["epoch"])})
    from xylarium.kernel import clocks, kinship, knowledge, tempo
    clocks.begin(kernel, knowledge.holder_of_planet(p), p)   # it keeps its own clock until others can see it
    tempo.wake(kernel)
    kinship.on_arise(kernel, p)                              # did anyone eat its world's life before it woke?
    return f"[COSMOS] A mind arises: the {name} of {p.name} ({metab}, {plan}), {r:.1f} kpc out."


def select(kernel: Any, planet: Any, metab: str, strategy: str, rng: Any) -> Dict[str, Any]:
    """What a world selected in the lineage that became a mind: its strategy (a variable world breeds r, a steady
    one K), its size (its gravity and strategy: biosphere.body_mass), how it moves (its gravity and medium), what it
    senses (light, or in the dark heat, pressure and chemistry; fields in plasma), how social it is (r lineages and
    energy-poor worlds lean to cooperation) - and so the shape of its mind: a society of individuals, a superorganism
    whose colony is the mind, or a distributed mind spread slow through its medium."""
    from xylarium.kernel import biosphere, fertility, physics, worlds
    ms = worlds.of_planet(kernel, planet)
    med = worlds.best(ms, metab) or {"solvent": "H2O", "where": "surface", "t": 280.0, "energy": 1.0, "pace": 1.0,
                                     "dark": False}
    dark = med.get("where") in ("under_ice", "deep")
    g = float(physics.surface_gravity(planet))
    sense = ("fields" if med["solvent"] == "plasma" else "heat and pressure" if dark else
             "chemistry" if med["solvent"] in ("CH4", "N2", "NH3") else "heat" if med["t"] > 450 else "light")
    form = ("drifting" if med["solvent"] == "plasma" else "swimming" if dark or med["where"] == "under_ice" else
            "low and many-limbed" if g > 1.5 else "tall and slender" if g < 0.5 else "walking")
    social = min(1.0, max(0.0, rng.random() + (0.3 if strategy == "r" else 0.0)
                          + (0.2 if med["energy"] < 0.1 else 0.0) - 0.25))
    shape = ("superorganism" if social > 0.75 and strategy == "r" else
             "distributed" if med["solvent"] == "plasma" or (dark and med["pace"] < 0.05) else "society")
    hands = rng.choice(["grasping limbs", "tendrils", "mouths and tongues", "jointed palps"]) \
        if med["solvent"] != "plasma" else "shaped fields"
    out = {"strategy": strategy, "medium": f"{'a dark ' if dark else ''}{med['solvent']} {med['where'].replace('_', ' ')}",
           "solvent": med["solvent"], "body_t": round(worlds.body_temperature(med["solvent"]), 1),
           "sense": sense, "form": form, "hands": hands, "social": round(social, 3), "shape": shape}
    # its size as the biosphere reckons a body (life history and its world's gravity: biosphere.body_mass)
    size = (fertility.CEILING["K"] / fertility.CEILING.get(strategy, fertility.CEILING["K"])) ** 4
    if med["solvent"] != "plasma":
        size *= max(1e-3, g) ** -biosphere.GRAVITY_MASS_POWER
    word = ("tiny" if size < 0.05 else "small" if size < 0.5 else "middling" if size < 2 else "large" if size < 10
            else "vast")
    kind = {"superorganism": "colony that thinks as one", "distributed": "mind spread through its medium",
            "society": "people of many minds"}[shape]
    out["body"] = f"{word} {form}"
    out["describe"] = f"a {kind}: {word}, {form}, {sense}-sensing, working with {hands}"
    return out


# ---------------------------------------------------------------------- witnessing
def entered(kernel: Any, sector_id: int) -> Optional[str]:
    """A ship enters a cell for the first time: it sees the cells around it."""
    cell = cell_of_sector(kernel, sector_id)
    if cell is None:
        return None
    st = stats(kernel)
    key = f"{cell[0]},{cell[1]}"
    if key in st["entered"]:
        return None
    st["entered"].append(key)
    lines = [materialise(kernel, cell, f"a ship stands in Sector {sector_id:03d}")]
    lines += [materialise(kernel, nb, f"seen from Sector {sector_id:03d}") for nb in neighbours_now(kernel, cell)]
    return "\n".join(x for x in lines if x) or None


def _reach(kernel: Any) -> List[str]:
    """Worlds with shipyards see the cells around their own (as far as their fleets sail)."""
    from xylarium.kernel import sustenance
    lines = []
    for sec in list(kernel.sectors.values()):
        for p in sec.planets:
            if p.population > 0 and sustenance.yards(p):
                line = entered(kernel, p.sector_id)
                if line:
                    lines.append(line)
    return lines


# ---------------------------------------------------------------------- the season, and the audit of scales
def quarter(kernel: Any) -> List[str]:
    if not is_cosmic(kernel):
        return []
    return _due(kernel) + _ignite(kernel) + _reach(kernel) + _shear(kernel) + _stars(kernel)


def audit(kernel: Any) -> Dict[str, Any]:
    """Are the scales right? Charted room against the peoples' reach, and minds arisen against expectation."""
    from xylarium.kernel import demography, topology
    st = stats(kernel)
    peoples = [p for s in kernel.sectors.values() for p in s.planets if p.population > 0 and p.civilization]
    reached = set()
    for p in peoples:
        try:
            reached |= set(topology.reach(kernel, p.sector_id, max(1, demography.settler_reach(kernel, p))))
        except Exception:
            reached.add(p.sector_id)
    charted = len(kernel.sectors)
    now = deep_gyr(kernel)
    return {"cells_charted": len(st["materialised"]), "cells_in_galaxy": len(cells()),
            "sectors_charted": charted, "peoples": len(peoples),
            "sectors_per_people": round(charted / max(1, len(peoples)), 1),
            "unreached_share": round(1.0 - len(reached & set(kernel.sectors)) / max(1, charted), 3),
            "minds_arisen": st["arisen"], "minds_expected_by_now": round(expected_by(kernel, now), 2),
            "minds_by_present_universe": round(expected_by(kernel, 13.8), 1), "minds_by_horizon": st.get("ever", 0),
            "silent": st["silent"],
            "deep_gyr": round(now, 4)}


def summary(kernel: Any) -> Dict[str, Any]:
    return audit(kernel) if is_cosmic(kernel) else {}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="cosmos",
    state=lambda: {"epoch0": 0.0, "minds": [], "next": 0, "arisen": 0, "silent": 0, "curve": [], "ever": 0,
                   "region_of": {}, "next_region": 2, "materialised": [], "entered": [], "unborn": {},
                   "place": {}, "cross": {}, "stretch": {}, "lum": {}, "phase": {}, "deaths": {}},
    season=quarter,
    summary=summary,
))
