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
five; hot water more as it warms, until what it stores breaks faster than it can be checked (~800 K); a melt of
silicates never holds enough; plasma never starts.

THE CLIMB. Selection writes what its cost allows: a substitution from one mutant in n costs ln n generations of
selective deaths, paid from the share of each generation the lineage can lose (Haldane 1957; a dividing lineage can
lose half) - b x 1/2 / ln n bits a generation, never more than MacKay's one. A generation is a cell's while the
genome fits one copier's span (copied at kT/h x e^-barrier by corresponding states: life's catalysts are evolved
to their medium, so a cold sea is only as much slower as it is colder) and a body's beyond it, growing as its mass
to the quarter power (metabolic theory) up to a mind-bearing body (M_MIND_KG). Filling a rung is the integral of
generations over the bits it writes - each step an exponential wait of that mean (the luck of the innovations that
open the rung). A lineage with too few members to make the mutations writes slower (N eps L per generation).

DECAY. What a lineage has stored breaks as it waits to be copied: by microscopic reversibility the barrier that
joins a backbone bond also breaks it, uphill by what the bond holds beyond the solvent's cohesion. Hot media copy
fast and forget fast; cold ones copy slowly and keep what they copy. The decay of a generation adds to its error,
so a hot lineage building large, slow bodies can forget faster than it can check - parity between hot and cold.

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
M_MIND_KG = 10.0                # a body that carries a mind (declared anchor: Earth's minded animals span ~0.5-70 kg;
                                # generations scale as its quarter power, so a factor of ten moves them by 1.8)
BOND_MASS_AMU = 12.0            # what a bond builds into a body: a carbon's mass (declared)
AMU_KG = 1.66054e-27
BITS_PER_GENERATION = 1.0       # selection writes at most a bit a generation (MacKay 1999, the asexual bound)
REPRODUCTIVE_EXCESS = 0.5       # the share of each generation selection can remove without the lineage shrinking: a
                                # lineage that divides in two can lose half (binary fission; Haldane's excess)
EJECTA_ORBITS = 1.0e6           # ejecta cross a system in about a million orbits (Gladman et al. 1996)
EXTINCTIONS_PER_GYR = 2.0       # impacts per Gyr beyond what a lineage adapted to (declared, measured at the Sun's
                                # radius; scale-free, so the same relative to any lineage's own background:
                                # creation.chemistries)
STERILISE_AT_R0 = 0.1           # chance a supernova pulse sterilises an open world's surface over 10 Gyr at the Sun's
                                # radius (measured) - an event no adaptation absorbs: it scales with the dying stars
                                # around (sterilise_per_gyr)
MAX_RUNGS = 12                  # a chemistry needing more rungs than this never reaches a mind within any star's life


def sterilise_per_gyr(crowd: float, dark: bool) -> float:
    """How often a world's life is sterilised, per Gyr. Two kinds of disturbance erase a lineage. Those a biosphere can
    be tuned to - impacts, a pulse it meets about once each adaptation time - come in scale-free spectra, so relative
    to its own background the crowding of its stars cancels (EXTINCTIONS_PER_GYR, the same everywhere). One it cannot
    be tuned to is a nearby supernova or burst stripping its sky: no repair outlasts a dead surface, so that rate grows
    with the dying stars around (crowd: cosmos.cosmic_rays, x how much of its orbit it spends among them). A sea under
    ice or in the deep is shielded from it."""
    return 0.0 if dark else STERILISE_AT_R0 / 10.0 * max(0.0, crowd)


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
    """Monomers a copying machine adds per second, scaled by how much of what it builds with is at hand - by
    corresponding states: life's catalysts are evolved to the medium they live in, so its barrier is the same share
    of its own kT everywhere (worlds.SOLVENT_BARRIER), and a copier runs at kT/h x e^-barrier: a cold sea only as much
    slower as it is colder, a hot one only as much faster. What heat costs is paid in fidelity and in decay
    (decay_rate), not in an Arrhenius advantage - parity between cold worlds and hot."""
    from xylarium.kernel import worlds
    return KB_J * max(1.0, t) / H_J * math.exp(-worlds.SOLVENT_BARRIER) * max(0.0, richness)


def decay_rate(solvent: str, t: float, k_copy: float, laws: Any = None) -> float:
    """Per-monomer breakage of what a lineage has stored, per second, by the two ways a bond breaks: back along the
    path that made it (microscopic reversibility - the catalysed barrier that joins a backbone bond also breaks it,
    uphill by what the bond holds beyond the solvent's own cohesion), and on its own, uncatalysed - thermal
    homolysis, (kT/h) e^(-bond/kT), which no evolved catalyst can stop. Hot media copy fast and forget fast; cold
    ones copy slowly and keep what they copy."""
    from xylarium.kernel import worlds
    L = _laws(laws)
    t = max(1.0, t)
    kt = worlds.KB_EV * t
    strong = (worlds.BOND_EV["silicate"] if solvent == "melt" else worlds.BOND_EV["covalent"]) * L.chem
    held = max(0.0, strong - worlds.weak_bond_ev(solvent, L))
    return k_copy * math.exp(-held / kt) + KB_J * t / H_J * math.exp(-strong / kt)


def body_kg(bits: float, bits_cell: float, kg_cell: float) -> float:
    """The body a lineage holding this much information builds: from a cell at the first rung to a mind-bearing body
    at I_MIND, growing as a power of what it holds (log-linear between the two anchors)."""
    if bits <= bits_cell or I_MIND <= bits_cell:
        return kg_cell
    g = math.log(max(1.0, M_MIND_KG / kg_cell)) / math.log(I_MIND / bits_cell)
    return kg_cell * (bits / bits_cell) ** g


def bits_per_generation(n: float, b: float = BITS_PER_MONOMER) -> float:
    """What selection writes a generation in a population of n: a substitution from a single mutant costs ln n
    generations' worth of selective deaths (Haldane 1957), paid from the reproductive excess - b bits for each
    monomer substituted - and never more than MacKay's bit a generation."""
    return min(BITS_PER_GENERATION, b * REPRODUCTIVE_EXCESS / math.log(max(math.e, n)))


def _fill_s(lo: float, hi: float, bits_cell: float, t_cell: float, kg_cell: float, b: float, k: float,
            rate: float = BITS_PER_GENERATION) -> float:
    """Generations x their length, integrated over the bits written from lo to hi at `rate` bits a generation: a genome
    up to one copier's span is copied serially (its generation I / (b k)); beyond it, a generation is a body's
    (metabolic theory: t_cell x (M / M_cell)^(1/4))."""
    out = 0.0
    if lo < bits_cell:
        top = min(hi, bits_cell)
        out += (top * top - lo * lo) / (2.0 * b * k)
        lo = top
    if hi > lo:
        g = math.log(max(1.0, M_MIND_KG / kg_cell)) / math.log(I_MIND / bits_cell) if I_MIND > bits_cell else 0.0
        p = g / 4.0
        out += t_cell * bits_cell / (p + 1.0) * ((hi / bits_cell) ** (p + 1.0) - (lo / bits_cell) ** (p + 1.0))
    return out / rate


def ladder(m: Dict[str, Any], area_m2: float, laws: Any = None) -> Optional[Dict[str, Any]]:
    """The rungs a medium's chemistry must climb to a mind: each step's information target and mean time (Gyr).
    None where nothing can be copied faithfully enough to begin.

    A lineage's error each generation is its copying's (eps0) and what decayed while it waited to be copied (the
    breakage rate x the generation: decay_rate). Each rung of error correction multiplies the fidelity by that
    error again; the rung holds b / err^(s+1) bits. Its generation is a cell's while its genome fits one copier's
    span (b / eps0 bits: the first rung) and a body's beyond it - growing as the body's mass to the quarter power
    (metabolic theory), from a cell to a mind-bearing body (M_MIND_KG) - so a mind's last rungs are written by
    large, slow-breeding bodies, a bit a generation at most."""
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
    r_decay = decay_rate(m["solvent"], m["t"], k, L)
    bits_cell = b / eps0
    t_cell = bits_cell / (b * k)                         # a cell's generation: one copier's span, copied
    kg_cell = bits_cell / b * BODY_PER_MONOMER * BOND_MASS_AMU * AMU_KG * L.proton
    steps, prev = [], 0.0
    for s in range(MAX_RUNGS):
        err = eps0
        for _ in range(3):                               # the decay a generation suffers depends on the body it builds
            cap = b / err ** (s + 1)
            target = min(cap, I_MIND)
            gen_s = target / (b * k) if target <= bits_cell else \
                t_cell * (body_kg(target, bits_cell, kg_cell) / kg_cell) ** 0.25
            err = eps0 + r_decay * gen_s
        if err >= 0.5:                                   # it forgets faster than it can check: no further rung
            return {"eps0": eps0, "steps": steps, "complete": False, "k_copy": k, "decay": r_decay}
        cap = b / err ** (s + 1)
        if cap <= prev:
            return {"eps0": eps0, "steps": steps, "complete": False, "k_copy": k, "decay": r_decay}
        target = min(cap, I_MIND)
        monomers = target / b
        body = body_kg(target, bits_cell, kg_cell)
        # how many it can feed: the power reaching it over the energy to build one body in a generation
        n = power * gen_s / max(1e-300, body / (BOND_MASS_AMU * AMU_KG * L.proton) * strong)
        gain = min(1.0, n * err ** (s + 1) * monomers)  # mutations a generation offers, if fewer than one
        if gain <= 0:
            return {"eps0": eps0, "steps": steps, "complete": False, "k_copy": k, "decay": r_decay}
        mean = _fill_s(prev, target, bits_cell, t_cell, kg_cell, b, k, bits_per_generation(n, b)) / gain / GYR_S
        steps.append({"bits": target, "mean_gyr": mean, "eps": err ** (s + 1), "population": n,
                      "generation_s": gen_s, "body_kg": body})
        prev = target
        if cap >= I_MIND:
            return {"eps0": eps0, "steps": steps, "complete": True, "k_copy": k, "landauer_kt": kt,
                    "decay": r_decay}
    return {"eps0": eps0, "steps": steps, "complete": False, "k_copy": k, "decay": r_decay}


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
