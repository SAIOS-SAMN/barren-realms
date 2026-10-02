"""
Xylarium life: how far a chemistry can climb - information written against its erasure.

Nothing here says life is common or rare, quick or slow. Those are what the formulas give for each world, under
its universe's laws (fundamental.py); a knob that set them would make the universe unmeasurable.

FIDELITY. Life is information that copies itself. A copy goes wrong where thermal noise beats the energy that tells
a right partner from a wrong one: one contact of the solvent's own cohesion, Delta G, so each monomer is miscopied
with probability eps = exp(-Delta G / kT) (Boltzmann). Water at 300 K: ~1e-4, as an unchecked polymerase is.
A cold, weakly bound sea copies better but slower; a hot one faster and worse; ionised matter, with no bonds, not
at all.

THE CEILING (Eigen's error threshold). A lineage cannot hold more than about b / eps bits (b bits per monomer) - past
that, mutation erases it faster than selection writes it. Each rung of the ladder is error correction built from
what the rung below could hold: a check of each copy, at the price of another discrimination, multiplies the
fidelity by eps0 again (Hopfield's kinetic proofreading) - the ceiling of rung s is b / eps0^(s+1). A mind is the
rung whose ceiling holds a mind's blueprint, I_MIND: the number of rungs is the chemistry's, not a universe's draw.
Water near its freezing point needs three (life, its proofreading, its proofreading's proofreading); a methane sea
five; a melt of silicates eight; plasma never starts.

THE CLIMB. Selection writes at most a bit a generation (MacKay 1999), and a generation is the time to copy what the
lineage holds: I / b monomers at the chemistry's own rate (Eyring: kT / h x exp(-barrier / kT), the barrier at the
solvent's own scale - worlds.SOLVENT_BARRIER), slower as fewer of the elements it needs are at hand (its richness).
Filling rung s from rung s-1 takes the integral of a generation over the bits written, (I_s^2 - I_(s-1)^2) /
(2 b k_copy) - each step an exponential wait of that mean (the luck of the innovations that open the rung). A
lineage with too few members to make the mutations writes slower (N eps L per generation, if under one).

ERASURE. An impact large enough to end a world's complex life sends a lineage back to the start of its current
rung (life itself, once begun, is never undone); impacts come as the world's neighbourhood shakes comets loose -
its stars' density, and how much of its orbit it spends in the crowded plane (geometry.vertical). A nearby
supernova sterilises it outright.

TRANSFER. Rock thrown off one world by impacts carries its microbes to its neighbours: within a system, ejecta
diffuse across in about a million orbits (Gladman et al. 1996). Between stars, no rock comes in time.
"""

import math
from typing import Any, Dict, List, Optional

KB_J = 1.380649e-23
H_J = 6.62607e-34
EV_J = 1.602177e-19
GYR_S = 3.156e16
FLUX_W = 340.0

BITS_PER_MONOMER = 2.0          # b: an alphabet of four (declared: the fewest that pair two ways)
DISCRIMINATION = 0.5            # a right partner is told from a wrong one by one contact: half a molecule's cohesion
                                # (each molecule shares its contacts with its neighbours; declared)
I_MIND = 1.0e9                  # bits: a mind's blueprint - a body and a nervous system that models its world (the one
                                # number for "what a mind is"; declared, the progenitors' to change)
BODY_PER_MONOMER = 1.0e3        # bonds a cell builds for each monomer of its genome (its body around it; declared)
EJECTA_ORBITS = 1.0e6           # ejecta cross a system in about a million orbits (Gladman et al. 1996)
EXTINCTIONS_PER_GYR = 2.0       # life-ending impacts per Gyr at unit stellar density in the plane (declared: comet
                                # showers from the Oort cloud, shaken by passing stars and the tide)
STERILISE_AT_R0 = 0.1           # chance a world at R0 is sterilised by a nearby supernova over 10 Gyr in the plane
MAX_RUNGS = 12                  # a chemistry needing more rungs than this never reaches a mind within any star's life


def _laws(laws: Any = None) -> Any:
    from xylarium.kernel import fundamental
    return fundamental.current() if laws is None else laws


def fidelity(solvent: str, t: float, laws: Any = None) -> float:
    """eps0: the chance a monomer is miscopied in this solvent at t (1 where nothing binds)."""
    from xylarium.kernel import worlds
    weak = worlds.weak_bond_ev(solvent, laws)
    if weak <= 0:
        return 1.0
    return math.exp(-DISCRIMINATION * weak / (worlds.KB_EV * max(1.0, t)))


def copy_rate(solvent: str, t: float, richness: float, laws: Any = None) -> float:
    """Monomers a copying machine adds per second (Eyring at the solvent's own barrier), scaled by how much of what it
    builds with is at hand."""
    from xylarium.kernel import worlds
    mid = worlds._mid(solvent, laws)
    return KB_J * t / H_J * math.exp(-worlds.SOLVENT_BARRIER * mid / max(1.0, t)) * max(0.0, richness)


def ladder(m: Dict[str, Any], area_m2: float, laws: Any = None) -> Optional[Dict[str, Any]]:
    """The rungs a medium's chemistry must climb to a mind: each step's information target and mean time (Gyr).
    None where nothing can be copied faithfully enough to begin."""
    from xylarium.kernel import worlds
    L = _laws(laws)
    eps0 = fidelity(m["solvent"], m["t"], L)
    if eps0 >= 0.5:                                      # a copy no better than a coin: no information is kept
        return None
    k = copy_rate(m["solvent"], m["t"], m.get("richness", 1.0), L)
    if k <= 0:
        return None
    b = BITS_PER_MONOMER
    kt = KB_J * max(1.0, m["t"])
    strong = worlds.BOND_EV["covalent"] * L.chem * EV_J
    power = max(0.0, m.get("energy", 0.0)) * FLUX_W * area_m2
    steps, prev = [], 0.0
    for s in range(MAX_RUNGS):
        cap = b / eps0 ** (s + 1)
        target = min(cap, I_MIND)
        monomers = target / b
        gen_s = monomers / k
        # how many it can feed: the power reaching it over the energy to build one in a generation
        n = power * gen_s / max(1e-300, monomers * BODY_PER_MONOMER * strong)
        gain = min(1.0, n * eps0 ** (s + 1) * monomers)  # mutations a generation offers, if fewer than one
        if gain <= 0:
            return {"eps0": eps0, "steps": steps, "complete": False, "k_copy": k}
        mean = (target * target - prev * prev) / (2.0 * b * k) / gain / GYR_S
        steps.append({"bits": target, "mean_gyr": mean, "eps": eps0 ** (s + 1), "population": n})
        prev = target
        if cap >= I_MIND:
            return {"eps0": eps0, "steps": steps, "complete": True, "k_copy": k, "landauer_kt": kt}
    return {"eps0": eps0, "steps": steps, "complete": False, "k_copy": k}


ERASURE = "rung"                # how an impact erases: "rung" - a lineage loses its current rung's progress; "clades"
                                # - a world holds CLADES lineages climbing at once, an impact kills each with the
                                # chance its severity gives, survivors keep what they hold and radiate into the
                                # emptied niches (the progenitors' choice of law; tools/scenarios.py compares them)
CLADES = 1                      # lineages a world's complex life climbs in at once under "clades"
KILL_SHAPE = 3.0                # an impact's severity is u^KILL_SHAPE (u uniform): most impacts kill few, rare ones
                                # most (impactor sizes follow a power law)


def climb(rng: Any, means: List[float], t0: float, horizon: float, steril: float, mu: float,
          arrives: Optional[float] = None) -> Dict[str, Any]:
    """A world's climb up its chemistry's rungs: each step an exponential wait of its mean; life itself (step 0) is
    never undone and may arrive from a neighbour first; impacts at rate mu erase by the universe's ERASURE law.
    Returns the epochs each step was reached by the lineage that got furthest, and how many setbacks it took."""
    t, times, setbacks = t0, [], 0
    for s, mean in enumerate(means):
        need = rng.expovariate(1.0 / max(1e-12, mean))
        if s == 0:
            if arrives is not None:
                need = min(need, max(0.0, arrives - t0))     # or carried here from a neighbour
            t += need
            if t > horizon or t > steril:
                return {"times": times, "setbacks": 0}
            times.append(round(t, 6))
            if ERASURE == "clades" and len(means) > 1:
                return _clades(rng, means, times, horizon, steril, mu)
            continue
        if mu <= 0:
            t += need
        else:
            while t < horizon:
                x = rng.expovariate(mu)
                if x >= need:
                    t += need
                    break
                t += x                               # an impact: this rung's progress is lost
                setbacks += 1
        if t > horizon or t > steril:
            break
        times.append(round(t, 6))
    return {"times": times, "setbacks": setbacks}


def _clades(rng: Any, means: List[float], base: List[float], horizon: float, steril: float,
            mu: float) -> Dict[str, Any]:
    """Several lineages climbing at once above life's first rung. An impact of severity u^KILL_SHAPE kills each with
    that chance; the survivors keep what they have written and radiate to refill the emptied niches (each daughter
    its own luck from there); if none survive, complex life begins again from the first rung above microbes."""
    n = len(means)
    t = base[0]
    end = min(horizon, steril)

    def fresh(done: List[float], s: int) -> Dict[str, Any]:
        return {"done": list(done), "s": s, "left": rng.expovariate(1.0 / max(1e-12, means[s]))}
    clades = [fresh(base, 1) for _ in range(max(1, CLADES))]
    setbacks = 0
    best = clades[0]
    while True:
        c = min(clades, key=lambda x: x["left"])
        t_done = t + c["left"]
        t_hit = t + rng.expovariate(mu) if mu > 0 else float("inf")
        if min(t_done, t_hit) > end:
            break
        if t_done <= t_hit:
            dt = c["left"]
            for x in clades:
                x["left"] -= dt
            t = t_done
            c["done"].append(round(t, 6))
            c["s"] += 1
            if len(c["done"]) > len(best["done"]):
                best = {"done": list(c["done"])}
            if c["s"] >= n:
                return {"times": c["done"], "setbacks": setbacks}
            c["left"] = rng.expovariate(1.0 / max(1e-12, means[c["s"]]))
        else:
            dt = t_hit - t
            for x in clades:
                x["left"] -= dt
            t = t_hit
            severity = rng.random() ** KILL_SHAPE
            alive = [x for x in clades if rng.random() >= severity]
            if len(alive) < len(clades):
                setbacks += 1
            if not alive:
                alive = [fresh(base, 1)]
            while len(alive) < max(1, CLADES):              # survivors radiate into the emptied niches
                parent = alive[int(rng.random() * len(alive))]
                alive.append(fresh(parent["done"], parent["s"]))
            clades = alive
    return {"times": best["done"], "setbacks": setbacks}


def transfer_gyr(a_au: float, star_suns: float) -> float:
    """How long rock thrown off one world takes to reach its neighbours: a million of its orbits."""
    return EJECTA_ORBITS * math.sqrt(max(1e-9, a_au) ** 3 / max(1e-9, star_suns)) / 1.0e9


def sum_cdf(means: List[float], t: float) -> float:
    """P(the sum of independent exponential waits of these means is done by t): the gamma distribution with the
    sum's mean and variance (exact for equal means, close for any)."""
    if not means:
        return 1.0
    if t <= 0:
        return 0.0
    m = sum(means)
    v = sum(x * x for x in means)
    shape, scale = m * m / max(1e-300, v), v / max(1e-300, m)
    return gamma_cdf(shape, t / scale)


def gamma_cdf(k: float, x: float) -> float:
    """The regularised lower incomplete gamma function P(k, x)."""
    if x <= 0:
        return 0.0
    if x > k + 60.0 + 10.0 * math.sqrt(k):
        return 1.0
    term = 1.0 / k
    total = term
    for n in range(1, 4000):
        term *= x / (k + n)
        total += term
        if term < total * 1e-12:
            break
    return max(0.0, min(1.0, math.exp(-x + k * math.log(x) - math.lgamma(k)) * total))
