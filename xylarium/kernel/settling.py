"""
Xylarium settling: a crossed people's dominion is the systems it has settled - a bubble around its home that grows
only as fast as its people can fill a world and send the next party, and stops where it meets another's.

How fast. Its front is a travelling wave (Fisher-KPP), set by its own numbers (front_speed): it multiplies at its
intrinsic rate r (biosphere.growth_rate: what a small colony's land lets it add), and each generation its emigrant
share s (DAUGHTER_EMIGRANT_SHARE) moves one step - a hop to the nearest system it can live on, (n s')^(-1/3) (n the
systems per pc^3 where it began, s' the share of systems with a world its metabolism can live on), never further than
its drive carries a cohort (cohort_reach). That random walk spreads it as D = s hop^2 / (6 T) (Newman & Sagan 1981),
and the front runs at

    v = 2 sqrt(r D),   R(t) = hop + v (t - t0)

no faster than its ships (a crossed people's fold: light's speed). Two peoples of different biology and drives make
different fronts; none is tuned.

What it holds. The systems within R (the disc over galactocentric rings, each column no deeper than the disc; the bulge and
nuclear cluster over shells about the centre, the share of each inside the ball) - times s. Never more than the galaxy holds.

Where two meet. Bubbles grow on the one coordinate clock; where two touch, the seam is where their fronts met, and
each holds only its own side from then on (a plane at the distance its front had come). A people that crosses
inside another's bubble is enclosed. Either way, what one takes from the other is only the worlds both can live on
(overlap: by world type, as common as each is): peoples of different niches share systems and take different
worlds, and a people enclosed by one of another niche still settles the worlds its encloser cannot use. A fallen
people's systems are no one's: what it took from its neighbours lapses, and they may settle it.

A world whose mind has not yet woken may be settled by a people that can live on it - allowed by default; a steward
may make it a sanctuary (ascendance.sanctuary). A people that wakes on such a world wakes among its settlements
(mark_wakings, read on the coordinate clock whenever the settlers' annals reach it).

What a people can live on is its metabolism's worlds (universe.habitability) and always the kind it evolved on - until
the board's yield-over-erasure language replaces the table.

Where it can live them is its band (band, fit): radiation is food and harm at once. A people whose seas are fed by
what its sky's particles split (hydromagnetics.radiolysis) has less to eat where the galaxy's cosmic rays are fewer;
one living under an open sky has its repair tuned to its home's dose - widened by how far its year swings it
(plasticity: a variable world selects for retuning within a life) - and loses newborns where the dose runs beyond
that (hydromagnetics.health's law). Each ring of the galaxy counts as the share of a colony there its people keeps.

How it settles is its own choice, and an act like any other (policy). Some of the worlds it can live on already
carry life of its own chemistry - the same media, the same food. Displacing it makes room for its own reproduction
at the cost of a biosphere's climb (erasure: booked dark on its history, as deep as that life had climbed toward a
mind); passing those worlds by keeps its history clean and its dominion smaller. Life of another chemistry eats
other media and is never in its way. A mind that counts others' lives as its own (the Light) weighs that erasure
in full; one that counts nothing (the Dark) does not weigh it at all - decide.choose, as every choice.
"""

import functools
import math
from typing import Any, Dict, List, Optional, Tuple

STARS_PER_SYSTEM = 4.0 / 3.0    # a third of systems are binaries (creation.BINARY_SHARE)
DISC_HALF_THICKNESS_PC = 300.0  # the thin disc's scale height (measured): a reach wider than it settles a slab


def stats(kernel: Any) -> Dict[str, Any]:
    from xylarium.kernel import annals
    return annals.stats(kernel).setdefault("bubbles", {})


# ---------------------------------------------------------------------- the galaxy's systems
@functools.lru_cache(maxsize=1)
def galaxy_systems() -> float:
    """Every star system the galaxy holds, by the same densities a bubble is counted with (encounters.components: the
    disc's stars to its thickness, the bulge and nuclear cluster): a ball about the centre wider than all of them."""
    return _disc_in_ball(0.0, 100.0) + _spheroid_in_ball(0.0, 100.0)


def systems_per_pc3(r_kpc: float) -> float:
    """Star systems per pc^3 at a galactocentric radius (encounters.components: disc, bulge and nucleus)."""
    from xylarium.kernel import encounters
    return sum(n for n, _ in encounters.components(r_kpc)) / STARS_PER_SYSTEM


N_DISC_R, N_DISC_A, N_SHELL = 48, 24, 96    # the rings and arcs a bubble's disc is counted on; its spheroid's shells
Band = Optional[Tuple[float, ...]]


def band(kernel: Any, home: Any) -> List[float]:
    """A people's band, read from its home: [the galaxy's cosmic rays there, the share of its fuel the galaxy's rays
    make, whether it lives under the open sky (1/0), the cosmic share of its dose, its plastic tolerance (the dose
    over its home's it retunes to within a life)]. A people with no medium of its own lives enclosed: no band."""
    from xylarium.kernel import biosphere, cosmos, hydromagnetics, worlds
    g = _place(kernel, home.sector_id) or {}
    cr0 = cosmos.cosmic_rays(float(g.get("r", cosmos.R0_KPC)))
    try:
        w = worlds.state_of_planet(kernel, home)["world"]
        med = worlds.best(worlds.of_planet(kernel, home), biosphere.metabolism_of(kernel, home))
    except Exception:
        return [cr0, 0.0, 0.0, 0.0, 1.0]
    if med is None:
        return [cr0, 0.0, 0.0, 0.0, 1.0]
    parts = hydromagnetics.dose_parts(w)
    food = float(med.get("radiolysis", 0.0)) / max(1e-30, float(med.get("energy", 0.0)))
    open_sky = med.get("where") not in ("under_ice", "deep")
    from xylarium.kernel import genome
    plastic = genome.plasticity(kernel, home)                      # its year's swing of light and wind
    return [round(cr0, 6), round(food * parts["power_cosmic"], 9), 1.0 if open_sky else 0.0,
            round(parts["cosmic"], 6), round(plastic, 6)]


def fit(bd: Band, r_kpc: float) -> float:
    """The share of a colony at radius r a people of this band keeps, 0 .. 1: what it has to eat there (its home's
    fuel, the galaxy's part scaled by the cosmic rays there over home's) x the newborns the dose there spares
    (hydromagnetics.health's law beyond its plastic tolerance). 1 everywhere for a people with no band."""
    if not bd:
        return 1.0
    from xylarium.kernel import cosmos, hydromagnetics
    cr0, food, open_sky, cosmic, plastic = bd
    q = cosmos.cosmic_rays(r_kpc) / max(1e-12, cr0)
    eat = min(1.0, 1.0 - food + food * q)
    if not open_sky:
        return eat
    excess = max(0.0, ((1.0 - cosmic) + cosmic * q) / max(1.0, plastic) - 1.0)
    return eat * math.exp(-excess * hydromagnetics.HOME_LIFETIME_RISK)


def _disc_in_ball(r0: float, reach: float, bd: Band = None) -> float:
    """The disc's systems in a ball of radius `reach` (kpc) about a home at r0: over galactocentric rings, the arc of
    each ring within the ball, each column as deep as the ball is there and no deeper than the disc."""
    from xylarium.kernel import cosmos, encounters
    h = DISC_HALF_THICKNESS_PC / 1000.0
    lo, hi = max(0.0, r0 - reach), r0 + reach
    dr = (hi - lo) / N_DISC_R
    total = 0.0
    for i in range(N_DISC_R):
        r = lo + (i + 0.5) * dr
        if r <= 0:
            continue
        c = (r * r + r0 * r0 - reach * reach) / (2.0 * r * max(1e-12, r0)) if r0 > 0 else -1.0
        th_max = math.pi if c <= -1.0 else (0.0 if c >= 1.0 else math.acos(c))
        if th_max <= 0:
            continue
        n = encounters.DISC_N_R0 * cosmos.density(r) * 1e9 * fit(bd, r)   # per kpc^3, as much as its band keeps
        dth = th_max / N_DISC_A
        col = 0.0
        for j in range(N_DISC_A):
            th = (j + 0.5) * dth
            rho2 = r * r + r0 * r0 - 2.0 * r * r0 * math.cos(th)
            col += 2.0 * min(h, math.sqrt(max(0.0, reach * reach - rho2))) * dth
        total += n * 2.0 * col * r * dr                                # both halves of the ring
    return total / STARS_PER_SYSTEM


def _spheroid_in_ball(r0: float, reach: float, bd: Band = None) -> float:
    """The bulge's and nuclear cluster's systems in the ball: the whole of them within reach - r0 of the centre, and of
    each shell beyond it the share inside the ball, (reach^2 - (r0 - s)^2) / (4 r0 s) - each shell weighted by the
    share its band keeps (fit)."""
    from xylarium.kernel import encounters
    ab, an = encounters.BULGE_A_KPC, encounters.NUCLEUS_A_PC / 1000.0
    mb, mn = encounters.BULGE_M, encounters.NUCLEUS_M
    enc = lambda s: mb * s * s / (s + ab) ** 2 + mn * s ** 3 / (s * s + an * an) ** 1.5           # noqa: E731
    rho = lambda s: mb * ab / (2.0 * math.pi * s * (s + ab) ** 3) \
        + 3.0 * mn / (4.0 * math.pi * an ** 3) * (1.0 + s * s / (an * an)) ** -2.5           # noqa: E731
    def whole(s_out: float) -> float:
        """Every shell within s_out of the centre, as much as its band keeps."""
        if not bd or s_out <= 0:
            return enc(s_out)
        lo_w = min(1e-5, s_out)
        kw = math.log(s_out / lo_w) / N_SHELL
        got = enc(lo_w) * fit(bd, lo_w)
        for i in range(N_SHELL):
            s0, s1 = lo_w * math.exp(i * kw), lo_w * math.exp((i + 1) * kw)
            s = math.sqrt(s0 * s1)
            got += rho(s) * 4.0 * math.pi * s * s * (s1 - s0) * fit(bd, s)
        return got
    if r0 < 1e-9:
        return whole(reach) / encounters.MEAN_STAR / STARS_PER_SYSTEM
    inner = max(0.0, reach - r0)
    total = whole(inner)
    lo, hi = max(abs(r0 - reach), 1e-6), r0 + reach
    k = math.log(hi / lo) / N_SHELL
    for i in range(N_SHELL):
        s0, s1 = lo * math.exp(i * k), lo * math.exp((i + 1) * k)
        s = math.sqrt(s0 * s1)
        frac = max(0.0, min(1.0, (reach * reach - (r0 - s) ** 2) / (4.0 * r0 * s)))
        total += rho(s) * 4.0 * math.pi * s * s * frac * (s1 - s0) * fit(bd, s)
    return total / encounters.MEAN_STAR / STARS_PER_SYSTEM


@functools.lru_cache(maxsize=65536)
def _systems_in(r0_kpc: float, reach_kpc: float, bd: Band = None) -> float:
    """The systems within reach of a home at r0 (both kpc) a people of band bd keeps: disc and spheroid, never more
    than the galaxy holds."""
    return min(galaxy_systems(), _disc_in_ball(r0_kpc, reach_kpc, bd) + _spheroid_in_ball(r0_kpc, reach_kpc, bd))


def systems_in(r0_kpc: float, reach_kpc: float, bd: Any = None) -> float:
    """_systems_in, its arguments rounded so nearby reaches share a count."""
    if reach_kpc <= 0:
        return 0.0
    k = 10 ** (3 - int(math.floor(math.log10(reach_kpc))))
    key = tuple(float(f"{x:.3g}") for x in bd) if bd else None
    return _systems_in(round(r0_kpc, 3), round(reach_kpc * k) / k, key)


# ---------------------------------------------------------------------- a people's pace and reach
def settle_rate(kernel: Any, home: Any) -> float:
    """Worlds each held world settles per generation: one for each time a landed party grows into a world that can
    send its own - g = 1 / ln(K / N0)."""
    from xylarium.config import DAUGHTER_EMIGRANT_SHARE, DAUGHTER_EMIGRANTS_MAX, DAUGHTER_EMIGRANTS_MIN
    from xylarium.kernel import biosphere
    k = max(1.0, float(biosphere.carrying_capacity(kernel, home)))
    n0 = min(float(DAUGHTER_EMIGRANTS_MAX), max(float(DAUGHTER_EMIGRANTS_MIN), DAUGHTER_EMIGRANT_SHARE * k))
    return 1.0 / max(1.0, math.log(max(1.0, k / n0)))


def _world_counts(kernel: Any) -> Dict[str, int]:
    """Charted worlds by type (counted once a cycle)."""
    def count() -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for sec in kernel.sectors.values():
            for p in getattr(sec, "planets", None) or []:
                counts[p.planet_type] = counts.get(p.planet_type, 0) + 1
        return counts
    if not hasattr(kernel, "caches"):
        return count()
    from xylarium.kernel import cache
    return cache.memo(kernel, "settling_worlds", "counts", count, epoch=kernel.cycle_count)


def lives_on(metabolism: str, home_type: Optional[str], kind: str) -> bool:
    """Can a people live on a world of this kind: one its metabolism can (universe.habitability), or the kind it
    evolved on."""
    from xylarium.kernel import universe
    return kind == home_type or universe.habitability(metabolism, kind) > 0


def _life_by_kind(kernel: Any) -> Dict[str, Dict[str, List[float]]]:
    """Of the charted worlds of each kind, the share alive in each chemistry and how far, on average, that life has
    climbed toward a mind (lifeline.life_of: rungs climbed over rungs needed). {kind: {region: [share, depth]}}."""
    def count() -> Dict[str, Dict[str, List[float]]]:
        from xylarium.kernel import lifeline
        n: Dict[str, int] = {}
        alive: Dict[str, Dict[str, List[float]]] = {}
        for sec in kernel.sectors.values():
            for p in getattr(sec, "planets", []) or []:
                n[p.planet_type] = n.get(p.planet_type, 0) + 1
                life = lifeline.life_of(kernel, p)
                if life and life.get("of"):
                    a = alive.setdefault(p.planet_type, {}).setdefault(life["region"], [0.0, 0.0])
                    a[0] += 1.0
                    a[1] += float(life["rung"]) / float(life["of"])
        return {kind: {reg: [c / n[kind], d / c] for reg, (c, d) in regs.items()} for kind, regs in alive.items()}
    if not hasattr(kernel, "caches"):
        return count()
    from xylarium.kernel import cache
    return cache.memo(kernel, "settling_life", "by_kind", count, epoch=kernel.cycle_count)


def living(kernel: Any, metabolism: str, home_type: Optional[str] = None) -> Tuple[float, float]:
    """Of the worlds a people can live on, the share that carry life of its own chemistry, and how far that life has
    climbed (its mean depth, 0 .. 1)."""
    life = _life_by_kind(kernel)
    share = depth = 0.0
    for kind, w in niche(kernel, metabolism, home_type).items():
        s, d = (life.get(kind) or {}).get(metabolism, [0.0, 0.0])
        share += w * s
        depth += w * s * d
    return share, (depth / share if share > 0 else 0.0)


def policy(kernel: Any, who: str, home: Any, metabolism: str, home_type: Optional[str]) -> Dict[str, Any]:
    """How a people settles the living worlds of its chemistry, chosen as it crosses: "displace" (they are worth more
    to it than the erasure costs it, as it counts others' lives) or "pass" (they are not)."""
    from xylarium.kernel import alignment, decide
    share, depth = living(kernel, metabolism, home_type)
    out = {"policy": "pass", "living": round(share, 6), "depth": round(depth, 6)}
    if share <= 0:
        out["policy"] = "displace"                         # nothing of its chemistry lives where it goes
        return out
    civ = getattr(home, "civilization", None)
    light = (1.0 + alignment.character(civ)) / 2.0 if civ is not None else 0.5   # 1 the Light, 0 absolute darkness
    m = decide.mind_of_planet(kernel, home)
    pick = decide.choose(kernel, [decide.option("displace", light * share * depth, share)], m, who, "settle")
    if pick is not None:
        out["policy"] = "displace"
    return out


def niche(kernel: Any, metabolism: str, home_type: Optional[str] = None) -> Dict[str, float]:
    """The worlds a people can live on, by kind, each as its share of them (weighted by how common each kind is
    among charted worlds)."""
    counts = _world_counts(kernel)
    mine = {t: n for t, n in counts.items() if lives_on(metabolism, home_type, t)}
    total = sum(mine.values())
    if not total:                                              # nothing charted: its own kinds of world, alike
        from xylarium.config import HABITABILITY
        kinds = sorted({t for t, h in HABITABILITY.get(metabolism, {}).items() if h > 0} | ({home_type} - {None}))
        return {t: 1.0 / len(kinds) for t in kinds or ["?"]}
    return {t: n / total for t, n in mine.items()}


def livable_share(kernel: Any, metabolism: str, home_type: Optional[str] = None) -> float:
    """The share of charted systems holding a world this people can live on."""
    charted = [s for s in kernel.sectors.values() if getattr(s, "planets", None)]
    if not charted:
        return 1.0
    ok = sum(1 for s in charted if any(lives_on(metabolism, home_type, p.planet_type) for p in s.planets))
    return max(1.0 / len(charted), ok / len(charted))


def overlap(kernel: Any, mine: Dict[str, Any], theirs: Dict[str, Any]) -> float:
    """The share of the worlds `theirs` (a bubble) can live on that `mine` can live on too."""
    return sum(w for t, w in niche(kernel, theirs.get("metab", "biotic"), theirs.get("home_type")).items()
               if lives_on(mine.get("metab", "biotic"), mine.get("home_type"), t))


def _place(kernel: Any, sector_id: int) -> Optional[Dict[str, Any]]:
    from xylarium.kernel import cosmos
    return cosmos.stats(kernel)["place"].get(str(sector_id))


def xy(kernel: Any, sector_id: int, t_gyr: float) -> Optional[Tuple[float, float]]:
    """Where a system is in the disc's plane at a coordinate epoch (cosmos.position's closed-form rotation)."""
    from xylarium.kernel import cosmos
    g = _place(kernel, sector_id)
    if not g:
        return None
    th = g["theta0"] + cosmos.omega(g["r"]) * t_gyr * 1000.0
    return g["r"] * math.cos(th), g["r"] * math.sin(th)


def begin(kernel: Any, who: str, home: Any, t0: float, gen_years: float) -> Dict[str, Any]:
    """A people's bubble from its crossing at coordinate epoch t0."""
    from xylarium.kernel import biosphere, clocks, cosmos
    b = stats(kernel).get(who)
    if b is not None:
        return b
    g = _place(kernel, home.sector_id) or {}
    r0 = float(g.get("r", cosmos.R0_KPC))
    metab = biosphere.metabolism_of(kernel, home)
    share = livable_share(kernel, metab, home.planet_type)
    n = systems_per_pc3(r0)
    hop = (n * share) ** (-1.0 / 3.0) / 1000.0                 # kpc
    gens_per_gyr = 1e9 * clocks.lapse(kernel, home.sector_id) / max(1.0, gen_years)
    b = stats(kernel)[who] = {"sid": home.sector_id, "r0": r0, "crossed": t0, "t0": t0, "metab": metab,
                              "home_type": home.planet_type,
                              "share": share, "hop": hop,
                              "g": settle_rate(kernel, home) * gens_per_gyr, "rmax": r0 + cosmos.R_MAX_KPC,
                              "cuts": {}, "enclosed": None, "fell": None, "band": band(kernel, home)}
    b.update(policy(kernel, who, home, metab, home.planet_type))
    b["v"] = front_speed(kernel, home, hop, gens_per_gyr)       # kpc per Gyr
    sec = kernel.sectors.get(home.sector_id)                   # the worlds of its own system it can live on: what
    b["home_worlds"] = max(1, sum(1 for p in (sec.planets if sec is not None else [])   # no neighbour takes from it
                                  if lives_on(metab, home.planet_type, p.planet_type)))
    return b


C_KPC_PER_GYR = 1e9 / 3261.56          # light's speed: a kiloparsec in 3,261.56 years (signals.LY_PER_KPC)


def cohort_reach(kernel: Any, home: Any) -> Optional[float]:
    """How far one settler cohort's drive carries it on a bunker (kpc): the jumps a laden hauler's bunker holds
    (propulsion: bunker over burn, the same range per hold for every cell) x the galaxy's mean lane. None where the
    galaxy has no charted lanes."""
    import math as _m
    from xylarium.config import FUEL_CELLS, SHIP_CATALOG
    from xylarium.kernel import propulsion, transit
    from xylarium.kernel.propulsion import BURN_MASS_PER_UNIT
    lane = transit._mean_lane_kpc(kernel)
    if not lane:
        return None
    holds = max(int(s.get("holds", 30)) for s in SHIP_CATALOG.values())      # its biggest hauler, laden
    drive = FUEL_CELLS.get(propulsion.world_fuel(kernel, home), FUEL_CELLS["H"])
    v_e = drive.get("v_e")
    if not v_e:                                                               # no reaction mass: its core's life
        return lane * float(drive.get("core_life", 1))
    jumps = (holds / v_e) / max(1, _m.ceil((1 + 2 * holds // BURN_MASS_PER_UNIT) / v_e))
    return lane * jumps


def front_speed(kernel: Any, home: Any, hop: float, gens_per_gyr: float) -> float:
    """How fast its settled front advances (kpc per coordinate Gyr): a Fisher-KPP wave, v = 2 sqrt(r D), from the
    people's own numbers - nothing tuned. r its intrinsic increase (biosphere.growth_rate: the rate a small colony
    multiplies at, before its land fills); D its dispersal, a random walk of its emigrants (Newman & Sagan 1981): each
    generation its emigrant share moves one step - to the nearest system it can live on, as far as its drive
    carries a cohort (cohort_reach) - D = s l^2 / (6 T). Never faster than its ships: a crossed people's fold is a
    null flow, so light's speed. (Light also bounds who can be told where to go: no front outruns its own news.)"""
    from xylarium.config import DAUGHTER_EMIGRANT_SHARE
    from xylarium.kernel import biosphere, clocks
    lapse = clocks.lapse(kernel, home.sector_id)
    r = float(biosphere.growth_rate(kernel, home)) * 1e9 * lapse              # per coordinate Gyr
    reach = cohort_reach(kernel, home)
    step = min(hop, reach) if reach else hop
    d = DAUGHTER_EMIGRANT_SHARE * step * step * gens_per_gyr / 6.0            # kpc^2 per Gyr
    return min(C_KPC_PER_GYR, 2.0 * math.sqrt(max(0.0, r) * d))


def alive(b: Dict[str, Any], t: float) -> bool:
    return t >= b["crossed"] and (b["fell"] is None or t < b["fell"])


def radius(b: Dict[str, Any], t: float) -> float:
    """How far its front has come by coordinate epoch t (kpc)."""
    if t < b["t0"]:
        return 0.0
    end = t if b["fell"] is None else min(t, b["fell"])
    moving = max(0.0, end - b["t0"])
    for a, z in b.get("pauses") or []:                      # held at home by a steward's ruling: the front waits
        moving -= max(0.0, min(z, end) - max(a, b["t0"]))
    return min(b["rmax"], b["hop"] + b["v"] * max(0.0, moving))


def _cut_fraction(a: Optional[float], reach: float) -> float:
    """The share of a bubble beyond a plane at distance a from its centre: a spherical cap, or a circle's segment
    once it is a slab - or the whole of it, for a bubble begun inside another's (a None)."""
    if a is None:
        return 1.0
    if a >= reach:
        return 0.0
    x = max(0.0, a / reach)
    if reach * 1000.0 <= DISC_HALF_THICKNESS_PC:
        return (1.0 - x) ** 2 * (2.0 + x) / 4.0
    return (math.acos(x) - x * math.sqrt(1.0 - x * x)) / math.pi


def _cut_on(kernel: Any, c: Dict[str, Any], t: float) -> bool:
    other = stats(kernel).get(c["by"])
    return t >= c["t"] and (other is None or other["fell"] is None or t < other["fell"])


def held(kernel: Any, who: str, t: float) -> float:
    """The systems a people holds at coordinate epoch t: within its front, less what its neighbours have settled of
    the worlds both can live on - beyond each seam, or all around it where it began inside another's dominion. Kind
    by kind of world, a world is lost once however many neighbours could take it, and only as far as each could keep
    a colony there (its band's fit, read where this people began: the contested worlds lie about it)."""
    b = stats(kernel).get(who)
    if b is None or not alive(b, t):
        return 1.0
    floor = float(b.get("home_worlds", 1))                   # its own system's worlds, shielded: never taken from it
    reach = radius(b, t)
    if reach <= 0:
        return floor
    st = stats(kernel)
    takers = [(st[c["by"]], _cut_fraction(c["a"], reach) * fit(st[c["by"]].get("band"), b["r0"]))
              for c in b["cuts"].values() if _cut_on(kernel, c, t) and c["by"] in st]
    left = 0.0
    for kind, w in niche(kernel, b.get("metab", "biotic"), b.get("home_type")).items():
        free = 1.0
        for other, frac in takers:
            if lives_on(other.get("metab", "biotic"), other.get("home_type"), kind):
                free *= 1.0 - frac
        left += w * free
    if b.get("policy") == "pass":
        left *= 1.0 - float(b.get("living", 0.0))           # the living worlds of its chemistry it passes by
    room = room_formed(kernel, b, t) * b["share"]           # what it has kindled beyond a white hole (gateways)
    return max(floor, systems_in(b["r0"], reach, b.get("band")) * b["share"] * left + room)


def room_formed(kernel: Any, b: Dict[str, Any], t: float) -> float:
    """The systems its kindled spheres hold by epoch t: each begins at its own Big Bang and forms its stars inside-out
    on its own clock, as this galaxy did (creation.formed_share at the Sun's radius, the child's age)."""
    children = b.get("children") or []
    if not children:
        return 0.0
    from xylarium.kernel import cosmos, creation
    seed = cosmos.cosmos_seed(kernel)
    return sum(float(c["room"]) * creation.formed_share(seed, cosmos.R0_KPC, max(0.0, t - float(c["epoch"])))
               for c in children)


def forming(kernel: Any, b: Dict[str, Any], t: float) -> bool:
    """Is a sphere it kindled still in its first e-fold of star formation (creation.infall_gyr at the Sun's radius,
    on the child's own clock) - somewhere still to settle?"""
    children = b.get("children") or []
    if not children:
        return False
    from xylarium.kernel import cosmos, creation
    span = creation.infall_gyr(cosmos.cosmos_seed(kernel), cosmos.R0_KPC)
    return any(t - float(c["epoch"]) < span for c in children)


def room_to_come(kernel: Any, b: Dict[str, Any], t: float) -> float:
    """The room its kindled spheres will hold that has not formed yet: somewhere still to settle."""
    return sum(float(c["room"]) for c in b.get("children") or []) - room_formed(kernel, b, t)


def breaks(kernel: Any, who: str, ta: float, tb: float) -> List[float]:
    """The epochs in (ta, tb) where what a people can hold jumps: its seams and enclosure, and their lapsing."""
    st = stats(kernel)
    b = st[who]
    ts = [c["t"] for c in b["cuts"].values()]
    ts += [st[c["by"]]["fell"] for c in b["cuts"].values() if c["by"] in st and st[c["by"]]["fell"] is not None]
    ts.append(b["t0"])
    return sorted({t for t in ts if ta < t < tb})


# ---------------------------------------------------------------------- meeting
def contact_time(kernel: Any, a: str, b: str) -> Optional[Tuple[float, float, float, Optional[str]]]:
    """When two bubbles' fronts first touch: (epoch, a's seam, b's seam, the one enclosed or None)."""
    st = stats(kernel)
    ba, bb = st[a], st[b]
    t_lo = max(ba["t0"], bb["t0"])
    pa, pb = xy(kernel, ba["sid"], t_lo), xy(kernel, bb["sid"], t_lo)
    if pa is None or pb is None:
        return None
    d = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
    ra, rb = radius(ba, t_lo), radius(bb, t_lo)
    if ra >= d and ba["t0"] <= bb["t0"]:
        return t_lo, d, 0.0, b                                 # b crossed inside a's dominion
    if rb >= d and bb["t0"] <= ba["t0"]:
        return t_lo, 0.0, d, a
    if ra + rb >= d:
        tc = t_lo
    else:
        v = ba["v"] + bb["v"]
        if v <= 0:
            return None
        held = sum(z - a for x in (ba, bb) for a, z in x.get("pauses") or [])
        hi = t_lo + (d - ra - rb) / v + held                    # the latest they can meet, pauses and all
        if radius(ba, hi) + radius(bb, hi) < d:
            return None                                         # one stopped short (fell, or reached its edge)
        lo = t_lo
        for _ in range(80):                                     # the fronts grow monotonically: bisect
            mid = 0.5 * (lo + hi)
            lo, hi = (lo, mid) if radius(ba, mid) + radius(bb, mid) >= d else (mid, hi)
        tc = hi
    ra, rb = radius(ba, tc), radius(bb, tc)
    s = ra / max(1e-12, ra + rb) * d                           # the fronts meet where they have come in step
    return tc, s, d - s, None


def meet(kernel: Any, a: str, b: str, when: Tuple[float, float, float, Optional[str]], logs: List[str]) -> None:
    """Two dominions meet: a seam, or one enclosed; the style of the one arriving names the meeting."""
    from xylarium.kernel import annals, history, spheres
    st = stats(kernel)
    tc, sa, sb, enclosed = when
    name = lambda w: w.split(":", 1)[-1]                       # noqa: E731
    o = lambda mine, theirs: overlap(kernel, st[mine], st[theirs])                   # noqa: E731
    if enclosed is not None:
        holder = a if enclosed == b else b
        share = o(holder, enclosed)
        if st[enclosed].get("enclosed") is None:                # the first whose dominion it crossed into
            st[enclosed]["enclosed"] = {"by": holder, "t": tc}
        try:
            how = spheres.style(kernel, enclosed, holder)
        except Exception:
            how = "standoff"
        st[enclosed]["cuts"][holder] = {"by": holder, "a": None, "t": tc, "o": share, "style": how}
        left = "no world" if share >= 0.999 else ("every world" if share <= 0.001 else f"{1 - share:.0%} of the worlds")
        history.event(kernel, "DOMINION", f"The {name(enclosed)} cross into the dominion of the {name(holder)}",
                      actors=[enclosed, holder], sector_id=st[enclosed]["sid"],
                      cause=f"the {name(holder)} had settled all around their home "
                            f"before they crossed; of the worlds the {name(enclosed)} can live on, {left} is left "
                            f"to them while the {name(holder)} stand",
                      data={"epoch": round(tc, 6), "overlap": round(share, 4)})
        logs.append(f"[ANNALS] The {name(enclosed)} cross inside the dominion of the {name(holder)}.")
        return
    try:
        how = spheres.style(kernel, a, b)
    except Exception:
        how = "standoff"
    st[a]["cuts"][b] = {"by": b, "a": sa, "t": tc, "o": o(b, a), "style": how}
    st[b]["cuts"][a] = {"by": a, "a": sb, "t": tc, "o": o(a, b), "style": how}
    if how == "war":
        annals.stats(kernel)["wars"] += 1
    else:
        annals.stats(kernel)["pacts"] += 1
    history.event(kernel, "GALACTIC_WAR" if how == "war" else "DOMINION",
                  f"The dominions of the {name(a)} and the {name(b)} meet" + (" in war" if how == "war" else ""),
                  actors=[a, b], sector_id=st[a]["sid"],
                  cause=f"their fronts met with their homes {sa + sb:.2f} kpc apart; each holds "
                        f"its own side of the seam ({how})", data={"epoch": round(tc, 6), "style": how})
    logs.append(f"[ANNALS] The dominions of the {name(a)} and the {name(b)} meet ({how}).")


def fall(kernel: Any, who: str, t: float) -> None:
    """A dominion falls: its systems are no one's, and what it took from its neighbours is theirs to settle."""
    stats(kernel)[who]["fell"] = t                            # its cuts on others lapse from today (_cut_on)


def next_contact(kernel: Any, until: float) -> Optional[Tuple[str, str, Tuple[float, float, float, Optional[str]]]]:
    """The earliest meeting not yet made, among dominions standing then, by `until`."""
    st = stats(kernel)
    best = None
    names = sorted(st)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if b in st[a]["cuts"] or a in st[b]["cuts"]:
                continue
            when = contact_time(kernel, a, b)
            if when is None or when[0] > until:
                continue
            tc = when[0]
            if not (alive(st[a], tc) and alive(st[b], tc)):
                continue
            if best is None or tc < best[2][0]:
                best = (a, b, when)
    return best


def settled_by(kernel: Any, sector_id: int, t: float, planet_type: Optional[str] = None,
               alive_with: Optional[str] = None) -> Optional[str]:
    """The people whose dominion has settled this system at coordinate epoch t - one that can live on a world of
    `planet_type`, when given - if any (the first to settle it). alive_with: the chemistry of the life on that world,
    which a people that passes living worlds by leaves alone."""
    p = xy(kernel, sector_id, t)
    if p is None:
        return None
    return settled_at(kernel, p, t, planet_type, home=sector_id, alive_with=alive_with)


def settled_at(kernel: Any, p: Tuple[float, float], t: float, planet_type: Optional[str] = None,
               home: Optional[int] = None, alive_with: Optional[str] = None) -> Optional[str]:
    """The people whose dominion covers a point of the disc (kpc) at coordinate epoch t (the first to settle it);
    a people's own home system (`home`) is never its own. Where its band keeps only a share of a colony (fit), it has
    settled that share of the systems there - which ones, fixed by the seed (the system and the people)."""
    import zlib
    st = stats(kernel)
    r_here = math.hypot(p[0], p[1])
    for who in sorted(st, key=lambda w: st[w]["crossed"]):
        b = st[who]
        if b["sid"] == home or not alive(b, t):
            continue
        if planet_type is not None and not lives_on(b.get("metab", "biotic"), b.get("home_type"), planet_type):
            continue
        if alive_with is not None and b.get("policy") == "pass" and b.get("metab") == alive_with:
            continue                                       # it passes living worlds of its own chemistry by
        c0 = xy(kernel, b["sid"], t)
        if c0 is None or math.hypot(p[0] - c0[0], p[1] - c0[1]) > radius(b, t):
            continue
        kept = fit(b.get("band"), r_here)
        if kept < 1.0 and zlib.crc32(f"{who}|{home if home is not None else p}".encode()) / 2.0 ** 32 >= kept:
            continue                                       # its band keeps no colony on this one
        beyond = False
        for c in b["cuts"].values():
            if not _cut_on(kernel, c, t) or c["a"] is None:
                continue
            o = xy(kernel, st[c["by"]]["sid"], t)
            dx, dy = o[0] - c0[0], o[1] - c0[1]
            norm = math.hypot(dx, dy) or 1.0
            if ((p[0] - c0[0]) * dx + (p[1] - c0[1]) * dy) / norm > c["a"]:
                beyond = True
                break
        if not beyond:
            return who
    return None


def mark_wakings(kernel: Any, peoples: Dict[str, List[Any]]) -> None:
    """A people whose world another's settlers had reached when its minds woke wakes among their settlements - read on
    the one coordinate clock, whenever the settlers' own annals come to it. Allowed unless a steward kept the system
    a sanctuary (ascendance.sanctuary)."""
    from xylarium.kernel import ascendance, biosphere, clocks, history
    for who, worlds in sorted(peoples.items()):
        home = max(worlds, key=lambda p: p.population)
        arisen = home.society.get("arisen") or {}
        if "epoch" not in arisen or arisen.get("under") or ascendance.sanctuary(kernel, home.sector_id):
            continue
        t = float(arisen["epoch"]) / max(1e-12, clocks.lapse(kernel, home.sector_id))
        holder = settled_by(kernel, home.sector_id, t, home.planet_type, biosphere.metabolism_of(kernel, home))
        if holder is None or holder == who:
            continue
        arisen["under"] = holder
        history.event(kernel, "DOMINION", f"The {who.split(':', 1)[-1]} woke among the settlements of the "
                                          f"{holder.split(':', 1)[-1]}", actors=[who, holder], planet=home,
                      cause=f"the {holder.split(':', 1)[-1]} had settled its system before its minds woke",
                      data={"epoch": float(arisen["epoch"])})
