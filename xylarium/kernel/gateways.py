"""
Xylarium gateways: every black hole is a bounce - a sink here, a white hole in the sphere beyond (blackhole.py) - and
the bounces are the fabric's long roads. The fold stays local; the gateways carry everything farther.

THE MOUTHS. A star born heavier than cosmos.BLACK_HOLE_SUNS ends as a black hole: a mouth. How many there are where a
system circles is the stars there (encounters.components) times the share of them born that heavy (creation.imf,
with its own place's clouds: top-heavy near the warm, crowded core, so the core is thick with mouths):

    n_BH(r) = n_*(r) * f_BH(r)

THE FOLD STAYS LOCAL. Space is cut into the cells of its black holes. Within a cell a ship folds through the local
fabric; past it, the cell's own black hole is the way on. A fold reaches as far as the nearest black hole lies,
the mean nearest-neighbour distance among randomly placed mouths (Hertz 1909):

    fold reach = 0.554 n_BH^(-1/3)        (~0.9 pc at the core, ~7.5 pc at the Sun's radius, ~13 pc at 12 kpc)

Charted systems lie tens to hundreds of parsecs apart, so between them every road runs through a mouth.

THE WAVE. A bounce rings: what crosses at the centre's horizon sends its wave out through the galaxy, falling off as
1/r^2 from the core. A people's minds evolved under its home's wave (exposure relative to the Sun's radius:
(R0 / r)^2). A stellar throat carries a mass undistorted on the torsion's repulsion: any people that folds space can
ride one. The centre's throat - the hub, and the road to the other galaxies - sits in the deepest wave: only a people
born inside the bulge, or whose minds travel as information, can ride it. The progenitors contest it through the
peoples they steward: the line whose networks carry the most of the galaxy keeps it, through one of its peoples that
bears the wave; others pass as the keeper's handling allows (transit.py).
"""

import functools
import math
from typing import Any, Optional

NEAREST = 0.554                 # the mean nearest-neighbour distance among random points, in units of n^-1/3


@functools.lru_cache(maxsize=4096)
def _bh_share(r_kpc: float) -> float:
    """The share of stars born heavier than a black hole's threshold where a system circles (creation.imf, its own
    place's clouds, solar metallicity)."""
    from xylarium.kernel import cosmos, creation
    if creation.imf(1.0 - 1e-12, 0.02, r=r_kpc) < cosmos.BLACK_HOLE_SUNS:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if creation.imf(mid, 0.02, r=r_kpc) < cosmos.BLACK_HOLE_SUNS else (lo, mid)
    return 1.0 - hi


def black_holes_per_pc3(r_kpc: float) -> float:
    """Stellar black holes per pc^3 at a galactocentric radius."""
    from xylarium.kernel import encounters
    r = round(max(0.0, r_kpc), 3)
    return sum(n for n, _ in encounters.components(r)) * _bh_share(r)


def fold_reach_pc(r_kpc: float) -> float:
    """How far a fold reaches here: the nearest black hole's distance (Hertz)."""
    n = black_holes_per_pc3(r_kpc)
    return NEAREST * n ** (-1.0 / 3.0) if n > 0 else math.inf


def exposure(r_kpc: float) -> float:
    """The centre's bounce wave at a radius, relative to the Sun's radius: (R0 / r)^2."""
    from xylarium.kernel import cosmos
    return (cosmos.R0_KPC / max(1e-3, r_kpc)) ** 2


def _r(kernel: Any, sector_id: int) -> Optional[float]:
    from xylarium.kernel import cosmos
    g = cosmos.stats(kernel)["place"].get(str(sector_id)) if cosmos.is_cosmic(kernel) else None
    return float(g["r"]) if g and g.get("r") is not None else None


def home_exposure(kernel: Any, who: str) -> float:
    """The wave a people's minds evolved under: its home's (0 where it has none on the galaxy's map)."""
    from xylarium.kernel import spheres
    home = spheres._home(kernel, who)
    r = _r(kernel, home.sector_id) if home is not None else None
    return exposure(r) if r is not None else 0.0


def travels_as_information(kernel: Any, who: str) -> bool:
    """Minds that can be copied out of a body and carried (technology: mind transfer) take any wave."""
    from xylarium.kernel import technology
    return technology.has(kernel, who, "transfer")


def within_fold(kernel: Any, a: int, b: int) -> bool:
    """Can a fold carry a ship from a to b: within the fold's reach where it sets out (in a cosmic galaxy; on the
    settled board, every lane is a fold)."""
    from xylarium.kernel import cosmos
    if not cosmos.is_cosmic(kernel):
        return True
    r = _r(kernel, a)
    d = cosmos.distance_kpc(kernel, a, b)
    if r is None or d is None:
        return False
    return d * 1000.0 <= fold_reach_pc(r)


# ---------------------------------------------------------------------- the hub and who passes it
def bears_hub(kernel: Any, who: str) -> bool:
    """Can a people's minds ride the centre's throat: born inside the bulge, where the centre's wave is what its life
    evolved in (cosmos.R_BULGE_KPC), or minds that travel as information."""
    from xylarium.kernel import cosmos, spheres
    if travels_as_information(kernel, who):
        return True
    home = spheres._home(kernel, who)
    r = cosmos.from_centre_kpc(kernel, home.sector_id) if home is not None else None    # the bulge is a sphere
    return r is not None and r <= cosmos.R_BULGE_KPC


def hub_contest(kernel: Any, masters: Any) -> list:
    """The progenitors' first contest, fought through the peoples they steward: each line's networks together
    (its own people's, and every people its stewards keep - steward_ai.line_of), and whether any of them bears the
    hub. -> [(line, systems its networks hold, rider or None)], strongest first."""
    from xylarium.kernel import board, spheres, steward_ai
    lines = board.progenitors(kernel)
    groups: dict = {}
    for m in sorted(masters):
        line = m if m in lines else (steward_ai.line_of(kernel, m) or m)
        groups.setdefault(line, []).append(m)
    out = []
    for line, members in groups.items():
        size = 0
        for m in members:
            net = spheres.stats(kernel)["nets"].get(m) or {}
            size += len(net.get("held", [])) + int(net.get("beyond", 0))
        riders = [m for m in members if bears_hub(kernel, m)]
        rider = max(riders, key=lambda w: (travels_as_information(kernel, w), round(home_exposure(kernel, w), 9), w)) \
            if riders else None
        out.append((line, size, rider))
    out.sort(key=lambda x: (x[2] is None, -x[1], x[0]))
    return out


def hub_keeper(kernel: Any, masters: Any) -> Optional[str]:
    """Who keeps the centre's throat: of the lines one of whose peoples bears its wave, the one whose networks carry
    the most of the galaxy - kept through that people. None while no one can bear it: the long roads stay shut."""
    contest = hub_contest(kernel, masters)
    return contest[0][2] if contest and contest[0][2] is not None else None


def long_range(kernel: Any, who: str) -> bool:
    """May a people's ships go beyond the fold's reach: fold to its own cell's black hole, ride to the centre, ride out
    to another cell's, fold in? Only through the hub - kept by its keeper, as its handling allows (transit.py)."""
    from xylarium.kernel import ascendance, spheres, transit
    if not spheres.crossed(kernel, who):
        return False
    keeper = transit.stats(kernel).get("hub")
    if keeper is None:                                        # unkept: the progenitors' hub lies dormant and open
        return not ascendance.confined(kernel, who, -1, -2)
    if keeper == who:
        return True
    if ascendance.confined(kernel, who, -1, -2) or transit.at_war(kernel, who, keeper):
        return False
    h = transit.handling_of(kernel, keeper)
    if h == "closed":
        return False
    if h == "guarded":
        return spheres.bond(kernel, who, keeper) is not None
    from xylarium.kernel import covert
    return not (transit.aggressor(kernel, who) and transit._abhorrent_to(kernel, keeper)) \
        and not covert.sanctioned(kernel, who, keeper)


def folds_to(kernel: Any, held: Any, target: int, where: Optional[dict] = None) -> bool:
    """Is `target` within a fold of any system in `held`? (`where` caches positions within one reading.)"""
    from xylarium.kernel import cosmos
    if not cosmos.is_cosmic(kernel):
        return True
    where = where if where is not None else {}

    def pos(s: int) -> Optional[tuple]:
        if s not in where:
            p = cosmos.position(kernel, s)
            where[s] = (p["x"], p["y"], p["z"], p["r"]) if p else None
        return where[s]
    t = pos(target)
    if t is None:
        return False
    for h in held:
        p = pos(h)
        if p is None:
            continue
        if math.dist(p[:3], t[:3]) * 1000.0 <= fold_reach_pc(p[3]):
            return True
    return False


# ---------------------------------------------------------------------- kindling a singularity
LIGHTEST_HOLE_SUNS = 3.0        # the lightest black holes known: ~3 suns, the top of the gap above neutron stars
SUN_J = 1.989e30 * 2.998e8 ** 2 # a sun's mass-energy, J
BONDS = ("federation", "alliance", "conglomerate")


def kindle_cost_j() -> float:
    """What it takes to make a black hole whose white hole holds: the lightest one's mass-energy, M c^2 (~5e47 J -
    some centuries of a galaxy's whole starlight)."""
    return LIGHTEST_HOLE_SUNS * SUN_J


def stats(kernel: Any) -> dict:
    from xylarium.kernel import annals
    return annals.stats(kernel).setdefault("gateways", {"banks": {}, "kindled": []})


def coalitions(kernel: Any, t: float) -> list:
    """The standing dominions joined by bonds where they met (settling: each meeting's style) - each a coalition; a
    dominion that met none in a bond stands alone (its realms are many)."""
    from xylarium.kernel import settling
    st = settling.stats(kernel)
    alive = sorted(w for w, b in st.items() if settling.alive(b, t))
    parent = {w: w for w in alive}

    def find(w: str) -> str:
        while parent[w] != w:
            parent[w] = parent[parent[w]]
            w = parent[w]
        return w
    for w in alive:
        for c in st[w]["cuts"].values():
            if c.get("style") in BONDS and c["by"] in parent:
                parent[find(w)] = find(c["by"])
    groups: dict = {}
    for w in alive:
        groups.setdefault(find(w), []).append(w)
    return [tuple(sorted(g)) for g in sorted(groups.values())]


def coalition_power_w(kernel: Any, members: tuple) -> float:
    """What a coalition banking toward a singularity commands: the light its arrays take from every system its
    dominions hold (harvest.py: arrays at a star's inner edge, built where the energy is needed - and room is the need
    here) - each member's systems x its home star's light (the stars it settles are its kind of star) x an array's
    efficiency. The arrays' own building is not yet charged (an upper bound)."""
    from xylarium.kernel import annals, harvest, mastery, relations
    peoples = relations._peoples(kernel)
    total = 0.0
    for w in members:
        worlds = peoples.get(w) or []
        if not worlds:
            continue
        home = max(worlds, key=lambda p: (p.population, p.id))
        held = max(1.0, float(annals.stats(kernel)["of"].get(w, {}).get("dominion", 1)))
        total += held * mastery.star_w(kernel, home) * harvest.BASE_EFF["array"]
    return total


def _full(kernel: Any, who: str, t: float) -> bool:
    """Has a dominion settled all it can reach: its worlds at what its bubble holds?"""
    from xylarium.kernel import annals, settling
    w = float(((annals.stats(kernel)["of"].get(who) or {}).get("hist") or {}).get("W", 1.0))
    b = settling.stats(kernel).get(who)
    if b is not None and settling.forming(kernel, b, t):
        return False                                      # a sphere it kindled is still forming: room is coming
    return w >= 0.999 * settling.held(kernel, who, t)


def approves(kernel: Any, members: tuple) -> bool:
    """The ancients' approval: the hub's keeper among them, or bonded to one of them with its throat not closed - or,
    where no one keeps the hub, a living ancient among them or bonded to one; and every member free among the stars
    by its steward's ruling."""
    from xylarium.kernel import ascendance, spheres, transit
    if not all(ascendance.free(kernel, w) for w in members):
        return False
    keeper = transit.stats(kernel).get("hub")
    if keeper is None:                                    # an unkept hub: the living ancients approve, or no one
        from xylarium.kernel import board
        elders = set(board.ancient_peoples(kernel))
        return any(w in elders or any(spheres.bond(kernel, a, w) is not None for a in elders) for w in members)
    if keeper in members:
        return True
    if transit.handling_of(kernel, keeper) == "closed":
        return False
    return any(spheres.bond(kernel, keeper, w) is not None for w in members)


def kindling(kernel: Any, logs: list) -> None:
    """Once a year: a coalition whose dominions have nowhere left to settle banks its power toward a new singularity;
    when it has the lightest black hole's mass-energy and the ancients' approval, it kindles one - and beyond its
    white hole a sphere opens - a universe at its own Big Bang, whose stars form inside-out on its own clock, a
    galaxy's room as they do, theirs to settle: the universe pivots on their ascension, and nothing around it is
    torn. A coalition with a sphere still forming has somewhere to settle, and kindles no other."""
    from xylarium.kernel import cosmos, history, settling
    t = cosmos.deep_gyr(kernel)
    gst = stats(kernel)
    for members in coalitions(kernel, t):
        key = "|".join(members)
        bank = gst["banks"].setdefault(key, {"j": 0.0, "t": t})
        dt_s = max(0.0, t - float(bank["t"])) * 1e9 * 3.156e7
        bank["t"] = t
        if not all(_full(kernel, w, t) for w in members):
            continue                                         # room enough still in this galaxy: nothing banked
        bank["j"] = float(bank["j"]) + coalition_power_w(kernel, members) * dt_s
        if bank["j"] < kindle_cost_j() or not approves(kernel, members):
            continue
        bank["j"] -= kindle_cost_j()
        n = len(gst["kindled"]) + 1
        room = settling.galaxy_systems()
        rec = {"n": n, "by": list(members), "epoch": round(t, 6), "seed": f"{cosmos.cosmos_seed(kernel)}:kindled:{n}",
               "room": room}
        gst["kindled"].append(rec)
        from xylarium.kernel import blackhole, spheres
        homes = [spheres._home(kernel, w) for w in members]
        near = next((h.sector_id for h in homes if h is not None), None)
        keepers = sorted(set(blackhole._keepers_near(kernel)) | set(members))
        thr = blackhole.open_throat(kernel, f"kindled:{n}", near, LIGHTEST_HOLE_SUNS, "kindled", keepers)
        rec["throat"] = f"kindled:{n}"                     # a far face with its own core, two-way: not a one-way room
        for w in members:
            b = settling.stats(kernel)[w]
            b.setdefault("children", []).append({"n": n, "epoch": t, "room": room / len(members),
                                                 "throat": f"kindled:{n}"})
        del thr
        names = ", ".join(w.split(":", 1)[-1] for w in members)
        history.event(kernel, "SINGULARITY_KINDLED", f"The {names} kindle a singularity", actors=list(members),
                      cause=f"nowhere left to settle, they pooled "
                            f"{kindle_cost_j():.2e} J - the lightest black hole's mass-energy - and the hub's keeper "
                            f"approved; beyond its white hole a sphere opens, a galaxy's room",
                      data={"seed": rec["seed"], "room": room, "epoch": round(t, 6)})
        logs.append(f"[GATEWAYS] The {names} kindle a singularity: a new sphere opens beyond it.")
