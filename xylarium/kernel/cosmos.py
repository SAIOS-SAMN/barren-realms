"""
Xylarium cosmos: the scales of the simulated universe, the galaxy's clockwork, and where and when minds arise.

THE SCALES (largest first)

  universe          the whole run: one seed, one clock (scheduler.py, clock.py)
  galactic cluster  the galaxies bound together; the home cluster - only its home galaxy is simulated, the rest are
                    a count kept for later tiers
  galaxy            an exponential disc (scale length R_D) of rings and cells; a CELL is a region of the disc
                    ~CELL_KPC on a side, carried by 40 sectors (a region) when it is materialised
  region            40 sectors: star systems and the null space between them (sectors 1-100 are the first
                    witness's own region and its neighbourhood)
  system            one sector: a star and its worlds, on exact Keplerian orbits (physics.py)

Nothing is materialised until it is witnessed. The map begins at the first mind that arises and grows outward as
observers arise and reach: a cell is materialised when a new mind arises in it, when a ship enters a neighbouring
cell, or when a people's fleets can reach it. Everywhere else the galaxy is a formula.

THE GALAXY (Milky Way measurements as rulers and data points, not as a template)

  * inside-out star formation: a radius forms its stars after tau(r) = 1.033 r - 1.267 Gyr (Chiappini, Matteucci &
    Romano 2001); the core first, the rim last.
  * elements scatter by mass: what supernovae and winds throw out settles back under gravity, so an element spreads
    outward over a length inversely proportional to its mass: lambda(A) = lambda_Fe x 56 / A, with lambda_Fe from
    iron's measured radial gradient (-0.06 dex/kpc). Heavy elements stay near the core, the lightest reach
    furthest. Deposits are scaled from their values at R0 (the Sun's radius, the ruler they were set at).
  * clockwork: every system rides a flat rotation curve (V_FLAT) around the centre, theta(t) = theta0 + V t / r -
    closed form, any moment as cheap as any other; each star keeps its own worlds on their own orbits.

THE CLOCKS ARE TIERED. A system's worlds turn on historical time (100 cycles to a year). The galaxy - its rotation,
its stars' lives, the evolution of life - turns on deep time: ruler(kernel) years of it pass for each year of the
clock. That is the one ruler mapping the two, and it is a law of each universe, chosen once at its genesis (PACES:
lonely 0.1 Myr a year - the second mind arrives long after the first has reached the stars; neighbourly 1 Myr;
teeming 10 Myr - minds arise within a lifetime of each other and the galaxy turns visibly); everything else is
physics.

STARS AGE. Each star lives SUN_MS_GYR x M^-2.5 from when its ring formed. Over its last tenth it brightens toward
the giant phase and its worlds feed fewer and fewer (their carrying capacity falls with what is left of it) - a
people sees its end coming for centuries; then the star dies and its worlds feed no one. A star already dead when
its region is first witnessed is found as a remnant with lifeless worlds.

MINDS ARISE (Carter's hard steps). A world that can carry life passes HARD_STEPS improbable steps - the origin of
life, complex cells, multicellular life, intelligence - each an exponential wait of mean STEP_GYR / (h x metals),
h its habitability for the biology that fits it best and metals its region's metallicity (no rocky worlds without
metals), after its crust settles. A mind arises only if all the steps finish inside its star's main-sequence window
(10 Gyr x M^-2.5) and no supernova sterilises it first (a hazard rising with the local stellar density: the crowded
core is deadly, the metal-poor rim barren - between lies the galactic habitable zone). Each candidate's dice are its
own (scheduler.rng) and fixed by the universe's seed. The clock's year 0 is the epoch the first mind arises; each
later one arises in its own year, is named, materialises its region, and begins as foragers (ways.py).
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import matter

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
FE_GRADIENT = 0.06              # dex/kpc: iron's radial gradient (Milky Way disc)
LAMBDA_FE = 1.0 / (FE_GRADIENT * math.log(10.0))       # kpc: iron's scatter length
HARD_STEPS = 4                  # Carter (1983); Watson (2008): ~4 hard steps to intelligence
STEP_GYR = 10.0                 # each step's mean wait on an ideal world: a Sun-like star's whole window
SUN_MS_GYR = 10.0               # main-sequence lifetime of a solar-mass star; tau ~ M^-2.5
CRUST_GYR = 0.6                 # a rocky world's crust settles and its bombardment ends (Earth: ~0.5-0.7 Gyr)
STERILISE_AT_R0 = 0.1           # chance a biosphere at R0 is sterilised by a nearby supernova over its window
KPC_PER_MYR_AT_1KMS = 1.0 / 977.8

# atomic masses (real elements); the exotic elements' lines are their periods
ATOMIC_MASS = {"H": 1.0, "He-3": 3.0, "C": 12.0, "H2O": 18.0, "Si": 28.1, "ORE": 20.0, "Ti": 47.9, "Fe": 55.8,
               "Ni": 58.7, "Cu": 63.5, "Xe": 131.3, "Pt": 195.1, "U": 238.0, "TAILINGS": 20.0}
PERIOD_MASS = {1: 2.5, 2: 13.0, 3: 30.0, 4: 60.0, 5: 105.0, 6: 170.0, 7: 250.0}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "cosmos")


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


def formed_gyr(r: float) -> float:
    """Inside-out: when a radius forms its stars (Chiappini et al. 2001)."""
    return max(0.3, 1.033 * r - 1.267)


def metals(r: float) -> float:
    """Metallicity relative to the Sun's: iron's gradient about R0, capped at solar (rocky worlds need metals)."""
    return min(1.0, 10.0 ** (-FE_GRADIENT * (r - R0_KPC)))


def survival(r: float) -> float:
    """The chance a biosphere outlives the supernovae of its neighbourhood (rising with stellar density)."""
    return math.exp(-STERILISE_AT_R0 * density(r))


def scatter_length(element: str) -> float:
    """kpc over which an element spreads from where it was made: inversely as its mass."""
    a = ATOMIC_MASS.get(element)
    if a is None:
        from xylarium.kernel.elements import PeriodicTable
        e = PeriodicTable.get_element(element)
        a = PERIOD_MASS.get(int(getattr(e, "line", 3) or 3), 30.0)
    return LAMBDA_FE * 56.0 / max(1.0, a)


def abundance(element: str, r: float) -> float:
    """An element's abundance at r relative to R0: heavy elements stay near the core, light ones reach furthest."""
    return math.exp(-(r - R0_KPC) / scatter_length(element))


def omega(r: float) -> float:
    """rad per deep Myr on the flat rotation curve."""
    return V_FLAT_KMS * KPC_PER_MYR_AT_1KMS / max(0.05, r)


def pace(kernel: Any) -> str:
    p = ((getattr(kernel, "state", None) or {}).get("genesis") or {}).get("pace") or "neighbourly"
    return p if p in PACES else "neighbourly"


def ruler(kernel: Any) -> float:
    """Deep years per clock year: a law of this universe, chosen once at its genesis."""
    return PACES[pace(kernel)]


def deep_gyr(kernel: Any, cycle: Optional[int] = None) -> float:
    """The deep-time epoch (Gyr since the galaxy began forming) at a clock cycle."""
    st = stats(kernel)
    c = kernel.cycle_count if cycle is None else cycle
    return float(st.get("epoch0", 0.0)) + (c / 100.0) * ruler(kernel) / 1.0e9


# ---------------------------------------------------------------------- minds arise (hard steps)
def _erlang_cdf(t: float, n: int, mean: float) -> float:
    if t <= 0:
        return 0.0
    x = t / mean
    term, total = 1.0, 1.0
    for k in range(1, n):
        term *= x / k
        total += term
    return 1.0 - math.exp(-x) * total


def _candidates_at_r0(kernel: Any) -> Tuple[int, List[float]]:
    """Measured from the materialised region: candidate worlds per 40 sectors at R0, and their habitabilities."""
    from xylarium.kernel.universe import habitability
    from xylarium.kernel import designer
    hs = []
    for s in kernel.sectors.values():
        for p in s.planets:
            h = max(habitability(m, p.planet_type) for m in designer.CLADE_OF)
            if h >= 0.6:
                hs.append(float(h))
    n = max(1, int(round(len(hs) * 40.0 / max(1, len(kernel.sectors)))))
    return n, (hs or [0.8])


HORIZON_GYR = 30.0              # deep time the schedule looks ahead to (red dwarfs outlive it; the clock never gets there)
WINDOW = 64                     # minds kept ahead in the kernel; the rest are recomputed from the seed when needed
CURVE_STEP = 0.25               # Gyr between points of the expectation curve


def schedule(kernel: Any) -> Dict[str, Any]:
    """Every mind the home galaxy raises before HORIZON_GYR: cell, epoch (Gyr), its star's mass and world's fitness
    - with the expectation the dice are drawn from, as a curve over deep time (the audit of the scales)."""
    from xylarium.kernel import scheduler
    per_cell, hs = _candidates_at_r0(kernel)
    out = []
    curve = [0.0] * (int(HORIZON_GYR / CURVE_STEP) + 1)
    for (i, j) in cells():
        r = ring_radius(i)
        n = int(round(per_cell * density(r)))
        t0 = formed_gyr(r) + CRUST_GYR
        z, live = metals(r), survival(r)
        for k in range(n):
            rng = scheduler.rng(kernel, "mind", i, j, k)
            u = rng.random()                                    # Salpeter IMF on [0.1, 2] solar masses
            a, b, g = 0.1, 2.0, -1.35
            m = (a ** g + u * (b ** g - a ** g)) ** (1.0 / g)
            window = SUN_MS_GYR * m ** -2.5
            h = hs[int(rng.random() * len(hs)) % len(hs)]
            mean = STEP_GYR / max(1e-6, h * z)
            end = t0 - CRUST_GYR + window                         # its star leaves the main sequence
            for c in range(len(curve)):
                t = min(c * CURVE_STEP, end) - t0
                if t > 0:
                    curve[c] += _erlang_cdf(t, HARD_STEPS, mean) * live
            steps = sum(rng.expovariate(1.0 / mean) for _ in range(HARD_STEPS))
            if steps <= window - CRUST_GYR and t0 + steps <= HORIZON_GYR and rng.random() < live:
                out.append({"cell": [i, j], "epoch": round(t0 + steps, 6), "mass": round(m, 3), "h": h, "k": k})
    out.sort(key=lambda e: (e["epoch"], e["cell"], e["k"]))
    return {"minds": out, "curve": [round(x, 2) for x in curve], "per_cell_r0": per_cell}


def expected_by(kernel: Any, epoch: float) -> float:
    curve = stats(kernel).get("curve") or [0.0]
    x = max(0.0, epoch) / CURVE_STEP
    i = min(len(curve) - 1, int(x))
    j = min(len(curve) - 1, i + 1)
    return curve[i] + (curve[j] - curve[i]) * (x - i)


def _refill(kernel: Any) -> None:
    """Keep the next WINDOW minds in the kernel (the schedule is the seed's; it is recomputed, never stored whole)."""
    st = stats(kernel)
    last = st.get("last")
    sched = schedule(kernel)
    later = [m for m in sched["minds"] if last is None or (m["epoch"], m["cell"], m["k"]) > tuple(last)]
    st["minds"] = later[:WINDOW]
    st["next"] = 0
    st["ever"] = len(sched["minds"])


# ---------------------------------------------------------------------- the map: cells <-> regions
def _index(kernel: Any) -> Dict[str, int]:
    return stats(kernel)["region_of"]


def region_of_cell(kernel: Any, cell: Tuple[int, int]) -> int:
    """The region (research.mint_frontier_cluster index) a cell is carried by: 1 for the first witness's cell."""
    st = stats(kernel)
    key = f"{cell[0]},{cell[1]}"
    idx = _index(kernel)
    if key not in idx:
        idx[key] = st["next_region"]
        st["next_region"] += 1
    return idx[key]


def cell_of_sector(kernel: Any, sector_id: int) -> Optional[Tuple[int, int]]:
    st = stats(kernel)
    region = 1 if sector_id <= 200 else 2 + (sector_id - 201) // 40
    for key, k in st["region_of"].items():
        if k == region:
            a, _, b = key.partition(",")
            return int(a), int(b)
    return None


def _sectors_of_region(region: int) -> List[int]:
    return list(range(1, 101)) if region == 1 else list(range(201 + (region - 2) * 40, 241 + (region - 2) * 40))


def materialised(kernel: Any, cell: Tuple[int, int]) -> bool:
    return f"{cell[0]},{cell[1]}" in stats(kernel)["materialised"]


@matter.declared("cluster_genesis")
def materialise(kernel: Any, cell: Tuple[int, int], why: str) -> Optional[str]:
    """A cell is witnessed: its region's systems are laid out, its elements scattered by its radius, no mind put
    there (minds arise), and it is joined to whatever neighbours are already charted."""
    key = f"{cell[0]},{cell[1]}"
    st = stats(kernel)
    if key in st["materialised"]:
        return None
    region = region_of_cell(kernel, cell)
    if region != 1:
        rm = kernel.research_manager
        rm.mint_frontier_cluster(kernel, region)
    ids = [s for s in _sectors_of_region(region) if s in kernel.sectors]
    inside = set(ids)
    for s in ids:                                         # a minted region's chain-bridge is not a neighbour here
        for w in [w for w in kernel.sectors[s].warps if w not in inside]:
            kernel.sectors[s].warps.remove(w)
            if s in kernel.sectors[w].warps:
                kernel.sectors[w].warps.remove(s)
    _furnish(kernel, ids, cell)
    _stars(kernel, ids)                                   # found as its stars are now (a dead one, a remnant)
    st["materialised"].append(key)
    _join(kernel, cell)
    from xylarium.kernel import topology
    topology.changed(kernel)
    i, j = cell
    return f"[COSMOS] Region {region} (ring {i}, arc {j}, {ring_radius(i):.1f} kpc out) is witnessed: {why}."


def _furnish(kernel: Any, ids: List[int], cell: Tuple[int, int]) -> None:
    """No minds but those that arise; elements as gravity sorted them at this radius; each sector's place."""
    r = ring_radius(cell[0])
    place = stats(kernel)["place"]
    for s in ids:
        sec = kernel.sectors[s]
        place[str(s)] = {"r": round(r + _jitter(kernel, s, 0) * CELL_KPC * 0.4, 4),
                         "theta0": round(cell_theta(*cell) + _jitter(kernel, s, 1) * 2 * math.pi / slots(cell[0]) * 0.4, 6)}
        for p in sec.planets:
            p.natives = None
            p.ruins = None
            if p.population > 0 and (p.civilization is not None or not p.owner_id):
                p.population, p.civilization = 0, None
            for el in list(p.element_deposits):
                p.element_deposits[el] = int(round(p.element_deposits[el] * abundance(el, r)))


def _jitter(kernel: Any, sector_id: int, axis: int) -> float:
    from xylarium.kernel import scheduler
    return (scheduler.stream(kernel, "place", sector_id, axis) % 10 ** 6) / 10 ** 6 - 0.5


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
AGEING_SHARE = 0.1              # the last tenth of a star's main-sequence life: it brightens toward the giant phase


def star_life(kernel: Any, sector_id: int) -> Optional[Tuple[float, float]]:
    """(when the star formed, when it leaves the main sequence), in deep Gyr: its ring's formation, its mass's life."""
    from xylarium.kernel import physics
    g = stats(kernel)["place"].get(str(sector_id))
    sec = kernel.sectors.get(sector_id)
    if not g or sec is None:
        return None
    if "remnant" in (getattr(sec, "star_type", "") or "").lower():
        return (0.0, 0.0)
    try:
        m = float(physics.star(sec)["mass"])
    except Exception:
        return None
    born = formed_gyr(g["r"])
    return born, born + SUN_MS_GYR * max(0.1, m) ** -2.5


def star_factor(kernel: Any, sector_id: int, at_gyr: Optional[float] = None) -> float:
    """1 on the main sequence; falling to 0 over its last tenth; 0 once it has died."""
    life = star_life(kernel, sector_id)
    if life is None:
        return 1.0
    born, ends = life
    t = deep_gyr(kernel) if at_gyr is None else at_gyr
    if t >= ends:
        return 0.0
    span = AGEING_SHARE * (ends - born)
    return 1.0 if t <= ends - span else max(0.0, (ends - t) / span)


def _stars(kernel: Any, sector_ids: Optional[List[int]] = None) -> List[str]:
    """Each witnessed star's worlds feed what its light still allows; its swelling and its death are history."""
    from xylarium.kernel import history
    logs = []
    ids = sector_ids if sector_ids is not None else [int(s) for s in stats(kernel)["place"]]
    for sid in ids:
        sec = kernel.sectors.get(sid)
        if sec is None or not sec.planets:
            continue
        f = round(star_factor(kernel, sid), 4)
        was = float(sec.planets[0].society.get("star_k", 1.0))
        if f == was:
            continue
        for p in sec.planets:
            p.society["star_k"] = f
        peopled = [p for p in sec.planets if p.population > 0]
        if sector_ids is not None:
            continue                                   # found as it is when first witnessed: no news
        if was >= 1.0 > f:
            history.event(kernel, "STAR_AGEING", f"The star of {sec.name} begins to swell", sector_id=sid,
                          actors=[getattr(getattr(p, "civilization", None), "name", p.name) for p in peopled],
                          cause="the last tenth of its main-sequence life")
            if peopled:
                logs.append(f"[COSMOS] The star of {sec.name} begins to swell: its worlds will feed fewer each year.")
        if was > 0.0 >= f:
            history.event(kernel, "STAR_DEATH", f"The star of {sec.name} dies", sector_id=sid,
                          actors=[getattr(getattr(p, "civilization", None), "name", p.name) for p in peopled],
                          magnitude=sum(p.population for p in peopled), cause="it left the main sequence")
            logs.append(f"[COSMOS] The star of {sec.name} dies.")
    return logs


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
    cells_ = [tuple(int(x) for x in key.split(",")) for key in st["materialised"]]
    cross, stretches = st["cross"], {}
    logs, changed = [], False
    for x in range(len(cells_)):
        for y in range(x + 1, len(cells_)):
            a, b = cells_[x], cells_[y]
            if abs(a[0] - b[0]) != 1:
                continue
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
    from xylarium.kernel import history
    verb = "open" if kind == "LANE_OPEN" else "close"
    history.event(kernel, kind, f"The lanes between regions {ra} and {rb} {verb}", sector_id=_gates(ra)[0],
                  cause=cause, data={"regions": [ra, rb]})
    return f"[COSMOS] The lanes between regions {ra} and {rb} {verb}: {cause}."


def position(kernel: Any, sector_id: int, cycle: Optional[int] = None) -> Optional[Dict[str, float]]:
    """Where a system is in the galaxy at a clock cycle: closed-form rotation on deep time (x, y in kpc)."""
    g = stats(kernel)["place"].get(str(sector_id))
    if not g:
        return None
    t_myr = deep_gyr(kernel, cycle) * 1000.0
    th = g["theta0"] + omega(g["r"]) * t_myr
    return {"r": g["r"], "theta": round(th % (2 * math.pi), 6), "x": round(g["r"] * math.cos(th), 4),
            "y": round(g["r"] * math.sin(th), 4), "deep_gyr": round(deep_gyr(kernel, cycle), 6)}


# ---------------------------------------------------------------------- genesis and emergence
def genesis(kernel: Any) -> None:
    """The universe begins its clock when its first mind arises: the first witness's cell is the region of
    sectors 1-100; everything else waits to be witnessed."""
    from xylarium.kernel import institutions
    institutions.genesis(kernel)                       # no money, bank, exchange or Reserve until founded
    st = stats(kernel)
    sched = schedule(kernel)
    st["curve"], st["per_cell_r0"], st["ever"] = sched["curve"], sched["per_cell_r0"], len(sched["minds"])
    st["minds"] = sched["minds"][:WINDOW]
    if not st["minds"]:
        st["epoch0"] = 0.0
        return
    st["epoch0"] = st["minds"][0]["epoch"]
    from xylarium.kernel import cluster
    cluster.genesis(kernel)                            # the galaxies around this one, as a formula
    first = st["minds"][0]
    st["epoch0"] = first["epoch"]
    home = tuple(first["cell"])
    st["region_of"][f"{home[0]},{home[1]}"] = 1
    materialise(kernel, home, "the first mind looks up")
    _due(kernel)


def _due(kernel: Any) -> List[str]:
    st = stats(kernel)
    logs = []
    now = deep_gyr(kernel)
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
        st["last"] = [rec["epoch"], rec["cell"], rec["k"]]
        line = arise(kernel, rec)
        if line:
            logs.append(line)
    return logs


def _name(kernel: Any, rec: Dict[str, Any]) -> str:
    from xylarium.kernel import scheduler
    from xylarium.kernel.natives import _name as syllables
    return syllables(scheduler.rng(kernel, "name", *rec["cell"], rec["k"]))


def arise(kernel: Any, rec: Dict[str, Any]) -> Optional[str]:
    """A mind arises: its cell is witnessed, its world is the fittest unclaimed one there whose star has lived long
    enough, and natural selection has given it its body: a variable world (a tilted axis, a flaring red dwarf)
    breeds r-strategists, a steady one K-strategists."""
    from xylarium.config import REPRODUCTIVE_STRATEGY
    from xylarium.kernel import biosphere, history, physics, primordial, scheduler, ways
    from xylarium.kernel.civilization import CivilizationIntelligenceEngine
    from xylarium.kernel.universe import habitability
    from xylarium.kernel import designer
    cell = tuple(rec["cell"])
    log = materialise(kernel, cell, "a mind arises there") if not materialised(kernel, cell) else None
    region = region_of_cell(kernel, cell)
    best = None
    for s in _sectors_of_region(region):
        sec = kernel.sectors.get(s)
        if sec is None:
            continue
        for p in sec.planets:
            if p.population > 0 or getattr(p, "civilization", None) is not None or p.owner_id:
                continue
            metab = max(designer.CLADE_OF, key=lambda m: (habitability(m, p.planet_type), m))
            h = habitability(metab, p.planet_type)
            if h < 0.6 or float(p.society.get("star_k", 1.0)) <= 0.0:
                continue
            try:
                lived = SUN_MS_GYR * float(physics.star(sec)["mass"]) ** -2.5 >= rec["epoch"] - formed_gyr(
                    ring_radius(cell[0]))
            except Exception:
                lived = True
            score = (lived, h, p.id)
            if best is None or score > best[0]:
                best = (score, p, metab)
    st = stats(kernel)
    if best is None:
        st["silent"] += 1
        return log
    _, p, metab = best
    rng = scheduler.rng(kernel, "body", *cell, rec["k"])
    tilt = float(physics.body(p).get("tilt", 0) or 0)
    sec = kernel.sectors[p.sector_id]
    try:
        m = float(physics.star(sec)["mass"])
    except Exception:
        m = 1.0
    variable = tilt > 23.0 or m < 0.5
    strategy = "r" if variable else "K"
    plans = sorted(k for k, v in REPRODUCTIVE_STRATEGY.items() if v == strategy) or ["bimaniform"]
    plan = plans[int(rng.random() * len(plans)) % len(plans)]
    name = _name(kernel, rec)
    civ = CivilizationIntelligenceEngine.create_civilization({
        "name": name, "species_name": f"{plan}-{name.lower()}", "clade": plan, "class_code": 0, "sigil": "*",
        "metabolism": metab, "disposition": "industry", "motto": "we looked up", "station": "arisen", "tech_level": 0})
    p.civilization = civ
    p.owner_id = None
    p.citadel_level = 0
    p.treasury = 0
    p.society["way"] = "forage"
    p.society["crop_z"] = 0.0
    p.society["arisen"] = {"epoch": rec["epoch"], "cell": list(cell)}
    ways._refresh(kernel, p)
    p.population = max(500, int(biosphere.carrying_capacity(kernel, p)))
    st["arisen"] += 1
    primordial.first(kernel, "first_mind", f"{name} of {p.name}")
    history.event(kernel, "EMERGENCE", f"The {name} look up", actors=[f"civ:{name}"], planet=p,
                  magnitude=p.population, cause=f"{HARD_STEPS} hard steps, {rec['epoch']:.3f} Gyr into the galaxy",
                  text=f"On {p.name}, {ring_radius(cell[0]):.1f} kpc from the galactic centre, under a star of "
                       f"{m:.2f} solar masses, a {metab} people of {plan} body became aware of itself: the {name}.")
    line = f"[COSMOS] A mind arises: the {name} of {p.name} ({metab}, {plan}), {ring_radius(cell[0]):.1f} kpc out."
    return "\n".join(x for x in (log, line) if x)


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
    lines = [materialise(kernel, nb, f"seen from Sector {sector_id:03d}") for nb in neighbours_now(kernel, cell)]
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
    return _due(kernel) + _reach(kernel) + _shear(kernel) + _stars(kernel)


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
                   "region_of": {}, "next_region": 2, "materialised": [], "entered": [], "per_cell_r0": 0,
                   "place": {}, "cross": {}, "stretch": {}},
    season=quarter,
    summary=summary,
))
