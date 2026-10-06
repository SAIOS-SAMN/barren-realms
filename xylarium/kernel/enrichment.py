"""
Xylarium enrichment: where the galaxy's elements come from, when, and where they go - its chemical evolution.

The Big Bang seeds only hydrogen and helium (and the light isotope of helium). Everything a world is built from is made
later, inside the galaxy, by stars that form from its gas - and it is carried, recycled, and lost:

  GAS        falls in from the cosmic web inside-out: each ring at its own pace (creation.infall_gyr: the core first, the
             rim last), toward the disc's exponential profile (scale length R_D, normalised by the measured surface
             density at the Sun's radius). The thinning web feeds each ring less as the universe expands.
  STARS      form from the gas at a share of it per orbit (Silk-Kennicutt: Sigma_SFR = 0.017 Sigma_gas Omega, Omega =
             V / r, measured): the inner disc, turning faster, makes its stars sooner. A share R of what forms returns at once (the IMF's measured
             return); the rest is locked away in stars, with the elements its gas held.
  CHANNELS   each element is made by channels that run on their own clocks (delay-time distributions, measured):
               ccsn     core-collapse supernovae of massive stars - prompt (within tens of Myr)
               ia       thermonuclear white dwarfs - t^-1 from 40 Myr
               agb      giant stars' slow neutron capture - t^-1 from 0.1 to 10 Gyr
               merger   neutron-star mergers' rapid neutron capture - t^-1 from 10 Myr
             and each element's share by channel is measured (the solar system's origins: Johnson 2019; Kobayashi,
             Karakas & Lugaro 2020): oxygen and magnesium all prompt, iron mostly Ia, nitrogen mostly AGB, platinum
             and uranium and everything past them by mergers.
  WAVEFRONTS what the channels make is thrown up by the blasts and winds that make it and falls back a radial
             epicycle away - v_launch / kappa(r), kappa = sqrt(2) V / r for a flat rotation curve - inward or outward:
             mixing runs down the gradient, from the rich core toward the poor rim. By weight: an element travels
             lambda(A) = that x sqrt(56 / A) (Graham's law: at one temperature a species' speed goes as 1 / sqrt of
             its mass; its length derived, not read off a measured gradient) - the heavy drop near where they were
             made, the light ride out toward the rim. What lands past
             the disc leaves it (outflow); what falls into the bulge goes to the centre.
  INFLOW     the disc's gas drifts inward (~1 km/s: infall arrives with too little angular momentum, and torques take
             more), carrying the poorer gas of the outer disc into the inner - which keeps an inner disc's gas from
             running dry - and what reaches the bulge feeds the centre. At the disc's edge the gas beyond it drifts
             in, unenriched.
  WINDS      where star formation is dense enough (Heckman's threshold, measured) the supernovae blow a wind out of
             the disc: the share of what is made that the excess drives leaves for the halo (outflow) - the early
             inner disc loses much of what it makes; the quiet rim keeps it.
  THE CENTRE what is made inside the bulge falls to the centre (blackhole.py): a share crosses the horizon - lost to
             this universe, the seed of a child one - and the rest returns as the centre's outflow over an active
             episode, enriching the bulge again.

CALIBRATION. The yields are set by one data point: the gas the Sun formed from (at R0, 4.57 Gyr before today) held
the solar abundances. Each channel's yield is fixed so that it alone gives its measured share of each element there.
Every other place and time - the gradient, the core's early enrichment, the rim's late, how far each element reached -
is what the laws give. A universe with other initial conditions runs the same yields through its own history.

THE LEDGER. Nothing here is conserved from the Big Bang: the galaxy's metal mass grows as its stars make it, is
locked in stars, flows out past the disc, falls to the centre, crosses the horizon. budget() books every term.
"""

import functools
import math
from typing import Any, Dict, List, Optional, Tuple

DR_KPC = 0.5                    # ring width
DT_GYR = 0.1                    # time step
SIGMA_R0 = 50.0                 # Msun / pc^2: the disc's surface density at the Sun's radius (measured, Flynn 2006)
PER_ORBIT = 0.017               # Sigma_SFR = 0.017 Sigma_gas Omega: a disc turns this share of its gas into stars per
                                # radian of its orbit (Kennicutt 1998, measured)
RETURNED = 0.4                  # the share of a stellar generation's mass its stars give back (Kroupa IMF, measured):
RETURN_PROMPT = 0.2             # half within ~100 Myr (its massive stars), the rest over the giants' lives - which
SLOW_RETURN = ((0.3, 0.5), (3.0, 0.5))   # spread as t^-1 over 0.1 to 10 Gyr: two decades, an e-folding each (Gyr, share)
FOUNTAIN_KMS = 70.0             # launch speed of supernova-driven fountain gas (intermediate-velocity clouds, measured)
INFLOW_KMS = 1.0                # gas drifts inward through the disc as infall and torques take its angular momentum
                                # (Lacey & Fall 1985; measured and modelled 0.5-3 km/s): ~1 kpc a Gyr
WIND_SFR = 100.0                # Msun / pc^2 / Gyr: star formation this dense drives a galactic wind out of the disc
                                # (Heckman 2002: 0.1 Msun / yr / kpc^2, measured); the excess's share of what is made leaves
RETURN_GYR = 0.1                # the centre's active episode: what it holds returns over ~100 Myr (blackhole.py)
SUN_AGE_GYR = 4.57

CHANNEL_DELAY = {"ccsn": (0.0, 0.04), "ia": (0.04, 14.0), "agb": (0.1, 10.0), "merger": (0.01, 14.0)}
# each element's share by channel (the solar system's origins; the superheavies only by mergers)
ORIGIN: Dict[str, Dict[str, float]] = {
    "C": {"ccsn": 0.5, "agb": 0.5}, "N": {"ccsn": 0.4, "agb": 0.6}, "O": {"ccsn": 1.0},
    "Na": {"ccsn": 0.8, "agb": 0.2}, "Mg": {"ccsn": 1.0}, "Al": {"ccsn": 1.0},
    "Si": {"ccsn": 0.7, "ia": 0.3}, "S": {"ccsn": 0.7, "ia": 0.3}, "Cl": {"ccsn": 0.8, "ia": 0.2},
    "Ca": {"ccsn": 0.7, "ia": 0.3}, "Ti": {"ccsn": 0.7, "ia": 0.3},
    "Fe": {"ccsn": 0.4, "ia": 0.6}, "Ni": {"ccsn": 0.4, "ia": 0.6}, "Cu": {"ccsn": 0.7, "ia": 0.3},
    "Xe": {"merger": 0.5, "agb": 0.5}, "Ba": {"agb": 0.85, "merger": 0.15}, "Pb": {"agb": 0.9, "merger": 0.1},
    "Pt": {"merger": 0.95, "agb": 0.05}, "Au": {"merger": 1.0}, "Th": {"merger": 1.0}, "U": {"merger": 1.0},
    "pyrosite": {"merger": 1.0}, "SpR": {"merger": 1.0}, "umbrite": {"merger": 1.0}, "aetherium": {"merger": 1.0},
    "AdL": {"merger": 1.0}, "mirror_glass": {"merger": 1.0},
}
PRIMORDIAL = ("H", "He", "He-3")


# ---------------------------------------------------------------------- the galaxy's laws, read from cosmos
def _rings() -> List[Tuple[float, float, float]]:
    from xylarium.kernel import cosmos
    n = int(round(cosmos.R_MAX_KPC / DR_KPC))
    return [(i * DR_KPC, (i + 1) * DR_KPC, (i + 0.5) * DR_KPC) for i in range(n)]


def _sigma_total(r: float) -> float:
    from xylarium.kernel import cosmos
    return SIGMA_R0 * math.exp(-(r - cosmos.R0_KPC) / cosmos.R_D_KPC)


def fountain_kpc(r: float) -> float:
    """How far a fountain's arc carries what it lifts at r: an epicycle, v_launch / kappa, kappa = sqrt(2) V / r."""
    from xylarium.kernel import cosmos
    kappa = math.sqrt(2.0) * cosmos.V_FLAT_KMS / max(DR_KPC / 2.0, r)          # km/s per kpc
    return FOUNTAIN_KMS / kappa


def travel_kpc(sym: str, r: float) -> float:
    """lambda(A): how far an element made at r travels before it settles - by weight."""
    from xylarium.kernel import substances
    a = substances.molar_mass(sym) or 56.0
    return fountain_kpc(r) * math.sqrt(56.0 / max(1.0, a))                 # Graham: speed ~ 1 / sqrt(mass)


def _dtd(channel: str, steps: int) -> List[float]:
    """A channel's delay-time distribution on the step grid: the share of its eventual yield given in each step."""
    lo, hi = CHANNEL_DELAY[channel]
    out = []
    for k in range(steps):
        a, b = k * DT_GYR, (k + 1) * DT_GYR
        if channel == "ccsn":
            out.append(1.0 if k == 0 else 0.0)
            continue
        a, b = max(a, lo), min(b, hi)
        out.append(math.log(b / a) if b > a else 0.0)                   # t^-1
    s = sum(out) or 1.0
    return [x / s for x in out]


# ---------------------------------------------------------------------- the run
def _key(seed: Any) -> Tuple[float, float, float]:
    from xylarium.kernel import creation
    if seed is None:
        return (1.0, creation.FIRST_STARS_GYR, 1.0)
    bb = creation.big_bang(seed)
    return (round(float(bb["assembly"]), 6), round(float(creation.first_stars(seed)), 6), round(float(bb["stars"]), 6))


@functools.lru_cache(maxsize=8)
def _run(key: Tuple[float, float, float]) -> Dict[str, Any]:
    """The galaxy's history on the ring-and-step grid from its first stars to well past today, every element made
    with unit yield per channel (scaled to the measured yields afterwards: the history is linear in them). Metal
    masses are kept per ring (Msun/pc^2 x kpc^2); every step is kept, so any epoch is read without running again."""
    from xylarium.kernel import blackhole, cosmos
    assembly, t1, stars = key
    rings = _rings()
    nr = len(rings)
    steps = int(round((cosmos_today() + 6.0) / DT_GYR)) + 1
    area = [math.pi * (o * o - i * i) for i, o, _ in rings]                 # kpc^2
    tau = [max(t1, 1.033 * m - 1.267) * assembly for _, _, m in rings]
    norm = [1.0 - math.exp(-max(1e-9, cosmos_today() - t1) / tau[j]) for j in range(nr)]
    gas = [0.0] * nr
    sfr_hist = [[0.0] * steps for _ in range(nr)]
    dtd = {c: _dtd(c, steps) for c in CHANNEL_DELAY}
    syms = list(ORIGIN)
    lam = {s: [travel_kpc(s, m) for _, _, m in rings] for s in syms}
    bulge = {j for j, (_, _, m) in enumerate(rings) if m < cosmos.R_BULGE_KPC}
    metal = {(s, c): [0.0] * nr for s in syms for c in ORIGIN[s]}
    centre = {(s, c): 0.0 for s in syms for c in ORIGIN[s]}
    pools = {k: [[0.0] * len(SLOW_RETURN) for _ in range(nr)] for k in metal}
    r_edge = rings[-1][1]
    width = r_edge / 2.0                                                    # the extended disc: out to 1.5 x the optical
    r_mid = r_edge + width / 2.0
    tau_b = max(t1, 1.033 * r_mid - 1.267) * assembly
    beyond = {"gas": 0.0, "metal": {k: 0.0 for k in metal}, "area": math.pi * ((r_edge + width) ** 2 - r_edge ** 2),
              "sigma": _sigma_total(r_mid), "tau": tau_b, "width": width,
              "norm": 1.0 - math.exp(-max(1e-9, cosmos_today() - t1) / tau_b)}
    gpool = [[0.0] * len(SLOW_RETURN) for _ in range(nr)]
    book = {"made": 0.0, "locked": 0.0, "outflow": 0.0, "horizon": 0.0, "returned": 0.0}
    hist_gas: List[List[float]] = []
    hist_metal: List[Dict[Tuple[str, str], List[float]]] = []
    for n in range(steps):
        t = n * DT_GYR
        for j in range(nr):
            if t > t1:
                inflow = _sigma_total(rings[j][2]) / tau[j] * math.exp(-(t - t1) / tau[j]) / norm[j]
                gas[j] += inflow * DT_GYR
            omega = cosmos.V_FLAT_KMS / max(DR_KPC / 2.0, rings[j][2]) * 1.0227      # per Gyr (km/s/kpc -> 1/Gyr)
            sfr = PER_ORBIT * stars * gas[j] * omega if gas[j] > 0 else 0.0
            sfr = min(sfr, gas[j] / DT_GYR / (1.0 - RETURN_PROMPT))         # never more than the ring holds
            sfr_hist[j][n] = sfr
            taken = (1.0 - RETURN_PROMPT) * sfr * DT_GYR                   # into stars, net of what returns at once
            if gas[j] > 0 and taken > 0:
                share = min(1.0, taken / gas[j])
                slow = (RETURNED - RETURN_PROMPT) / (1.0 - RETURN_PROMPT)  # what the giants will give back
                for key2, arr in metal.items():
                    gone = arr[j] * share
                    arr[j] -= gone
                    book["locked"] += gone * (1.0 - slow)
                    for p_, (_, w) in enumerate(SLOW_RETURN):
                        pools[key2][j][p_] += gone * slow * w
                for p_, (_, w) in enumerate(SLOW_RETURN):
                    gpool[j][p_] += taken * slow * w
                gas[j] = max(0.0, gas[j] - taken)
            for p_, (tau_p, _) in enumerate(SLOW_RETURN):                    # the giants give back, at birth's mix
                f = 1.0 - math.exp(-DT_GYR / tau_p)
                back = gpool[j][p_] * f
                gpool[j][p_] -= back
                gas[j] += back
                for key2, arr in metal.items():
                    m_ = pools[key2][j][p_] * f
                    pools[key2][j][p_] -= m_
                    arr[j] += m_
        # the disc's gas drifts inward, its metals with it; what reaches the bulge feeds the centre
        drift = min(0.5, INFLOW_KMS * 1.0227 * DT_GYR / DR_KPC)             # share of a ring's gas crossing inward
        edge = len(bulge)
        for j in range(edge, nr):
            moved = gas[j] * drift
            if moved <= 0:
                continue
            gas[j] -= moved
            for key2, arr in metal.items():
                m_ = arr[j] * drift
                arr[j] -= m_
                if j - 1 < edge:
                    book["horizon"] += m_ * blackhole.HORIZON_SHARE
                    centre[key2] += m_ * (1.0 - blackhole.HORIZON_SHARE)
                else:
                    arr[j - 1] += m_
            if j - 1 >= edge:
                gas[j - 1] += moved * area[j] / area[j - 1]
        # the extended gas beyond the disc: infall like the disc's, too thin to form stars, holding what mixing
        # carried past the edge - it drifts in across the edge with its own mix
        if t > t1:
            beyond["gas"] += beyond["sigma"] / beyond["tau"] * math.exp(-(t - t1) / beyond["tau"]) / beyond["norm"] \
                * DT_GYR * beyond["area"]
        cross = min(0.5, INFLOW_KMS * 1.0227 * DT_GYR / beyond["width"])
        moved = beyond["gas"] * cross
        if moved > 0:
            beyond["gas"] -= moved
            gas[nr - 1] += moved / area[nr - 1]
            for key2, arr in metal.items():
                m_ = beyond["metal"][key2] * cross
                beyond["metal"][key2] -= m_
                arr[nr - 1] += m_
        # each channel's output this step in each ring (unit yield per Msun/pc^2 formed), from its delay times
        out = {c: [0.0] * nr for c in CHANNEL_DELAY}
        for c, d in dtd.items():
            for j in range(nr):
                hist = sfr_hist[j]
                made = 0.0
                for m in range(n + 1):
                    if hist[m]:
                        made += hist[m] * d[n - m]
                out[c][j] = made * DT_GYR * area[j]
        wind = [max(0.0, 1.0 - WIND_SFR / sfr_hist[j][n]) if sfr_hist[j][n] > WIND_SFR else 0.0 for j in range(nr)]
        for (s, c), arr in metal.items():
            for j in range(nr):
                made = out[c][j]
                if made <= 0:
                    continue
                book["made"] += made
                if wind[j]:
                    book["outflow"] += made * wind[j]                       # blown out of the disc
                    made *= 1.0 - wind[j]
                _spread(arr, made, j, lam[s][j], book, centre, (s, c), bulge, beyond)
            give = centre[(s, c)] * min(1.0, DT_GYR / RETURN_GYR)          # the centre gives back as its outflow,
            if give > 0:                                                    # out past the bulge it fell into
                centre[(s, c)] -= give
                book["returned"] += give
                edge = len(bulge)
                _spread(arr, give, edge, lam[s][edge], book, centre, (s, c), bulge, beyond)
        hist_gas.append(list(gas))
        hist_metal.append({k: list(v) for k, v in metal.items()})
    book["beyond"] = sum(beyond["metal"].values())
    return {"rings": rings, "area": area, "gas": hist_gas, "metal": hist_metal, "steps": steps, "book": book,
            "centre": centre, "sfr": sfr_hist, "beyond": beyond, "pools": pools}


def _spread(arr: List[float], mass: float, j: int, lam: float, book: Dict[str, float],
            centre: Optional[Dict[Any, float]] = None, ckey: Any = None, bulge: Any = (),
            beyond: Optional[Dict[str, Any]] = None) -> None:
    """Deposit what was made at ring j over its travel length, inward and outward (exp(-|dr| / lambda)): what lands
    in the bulge falls to the centre (a share across the horizon), what lands past the disc joins the extended gas
    beyond it."""
    from xylarium.kernel import blackhole
    nr = len(arr)
    q = math.exp(-DR_KPC / max(1e-6, lam))
    total = (1.0 + q) / (1.0 - q)                                       # the whole two-sided kernel
    inner = q ** (j + 1) / (1.0 - q)                                    # what would fall inside the first ring
    outer = q ** (nr - j) / (1.0 - q)                                   # what would land past the disc
    to_centre = mass * inner / total
    if beyond is not None:
        beyond["metal"][ckey] += mass * outer / total                   # into the extended gas past the edge
    else:
        book["outflow"] += mass * outer / total
    for k in range(nr):
        w = mass * q ** abs(k - j) / total
        if k in bulge:
            to_centre += w
        else:
            arr[k] += w
    if to_centre > 0:
        if centre is None:
            arr[0] += to_centre
            return
        book["horizon"] += to_centre * blackhole.HORIZON_SHARE
        centre[ckey] = centre.get(ckey, 0.0) + to_centre * (1.0 - blackhole.HORIZON_SHARE)


def cosmos_today() -> float:
    from xylarium.kernel import creation
    return creation.TODAY_GYR


def _sun_birth() -> float:
    return cosmos_today() - SUN_AGE_GYR


# ---------------------------------------------------------------------- reading it
def _snapshot(key: Tuple[float, float, float], t: float) -> Dict[str, Any]:
    """The galaxy's gas and its metals at epoch t."""
    run = _run(key)
    n = max(0, min(run["steps"] - 1, int(round(t / DT_GYR))))
    return {"rings": run["rings"], "area": run["area"], "gas": run["gas"][n], "metal": run["metal"][n],
            "book": run["book"]}


@functools.lru_cache(maxsize=1)
def _calibration() -> Dict[Tuple[str, str], float]:
    """Each channel's unit-yield concentration of each element in the Sun's birth gas: what sets the yields."""
    snap = _snapshot(_key(None), _sun_birth())
    j = _ring_of(snap["rings"], _r0())
    out = {}
    for k, arr in snap["metal"].items():
        out[k] = arr[j] / max(1e-30, snap["area"][j] * snap["gas"][j])
    return out


def _r0() -> float:
    from xylarium.kernel import cosmos
    return cosmos.R0_KPC


def _ring_of(rings: List[Tuple[float, float, float]], r: float) -> int:
    return max(0, min(len(rings) - 1, int(r / DR_KPC)))


def relative(seed: Any, sym: str, r: float, t: float) -> float:
    """An element's abundance in the gas at radius r and epoch t, relative to the Sun's birth gas (1 there): what a
    star and its worlds born there and then are made of. Primordial matter is 1 everywhere."""
    base = sym.split("-")[0] if sym not in ORIGIN else sym
    if sym in PRIMORDIAL or base not in ORIGIN:
        return 1.0
    snap = _snapshot(_key(seed), t)
    j = _ring_of(snap["rings"], r)
    cal = _calibration()
    g = snap["gas"][j] * snap["area"][j]
    if g <= 0:
        return 0.0
    tot = 0.0
    for c, f in ORIGIN[base].items():
        conc = snap["metal"][(base, c)][j] / g
        tot += f * conc / max(1e-30, cal[(base, c)])
    return tot


def of_good(seed: Any, sym: str, r: float, t: float) -> float:
    """A good's abundance relative to the Sun's birth gas: an element's own; a compound's, its scarcest constituent's
    (beyond the primordial hydrogen)."""
    from xylarium.kernel import substances
    parts = [x for x in substances.constituents(sym) if x not in PRIMORDIAL]
    if not parts:
        return 1.0
    if sym in ORIGIN:
        return relative(seed, sym, r, t)
    return min(relative(seed, x, r, t) for x in parts)


def metals(seed: Any, r: float, t: float) -> float:
    """Metallicity relative to the Sun's birth gas: the mass-weighted relative abundance of what metals are mostly
    made of (oxygen, carbon, iron, silicon, magnesium, nitrogen at their solar weights)."""
    from xylarium.kernel import substances
    w = {s: substances.molar_mass(s) * substances.abundance(s) for s in ("O", "C", "Fe", "Si", "Mg", "N")}
    tot = sum(w.values())
    return sum(w[s] * relative(seed, s, r, t) for s in w) / tot


def gradient(seed: Any, sym: str, t: float, r_in: float = 4.0, r_out: float = 14.0) -> float:
    """dex per kpc of an element's abundance across the disc (least squares over the rings between r_in and r_out)."""
    xs, ys = [], []
    r = r_in
    while r <= r_out:
        v = relative(seed, sym, r, t)
        if v > 0:
            xs.append(r)
            ys.append(math.log10(v))
        r += DR_KPC
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / max(1e-12, sum((x - mx) ** 2 for x in xs))


def budget(seed: Any) -> Dict[str, float]:
    """Where the metals made over the galaxy's history went, as shares of what was made (unit yields): in its gas,
    in its stars (locked, or in giants still to give back), blown out by winds, across the horizon, held at the
    centre, in the extended gas past the disc. The shares close: nothing is lost that is not booked."""
    run = _run(_key(seed))
    snap = _snapshot(_key(seed), (run["steps"] - 1) * DT_GYR)            # the run's own end: its books are its whole
    made = run["book"]["made"] or 1.0
    in_gas = sum(sum(arr) for arr in snap["metal"].values())
    held = sum(run["centre"].values())
    giving = sum(sum(sum(p_) for p_ in rings_) for rings_ in run["pools"].values())     # in giants, still to return
    return {"made": 1.0, "gas": in_gas / made, "locked": (run["book"]["locked"] + giving) / made,
            "outflow": run["book"]["outflow"] / made, "horizon": run["book"]["horizon"] / made,
            "centre": held / made, "beyond": sum(run["beyond"]["metal"].values()) / made}
