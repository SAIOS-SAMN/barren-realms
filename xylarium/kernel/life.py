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
