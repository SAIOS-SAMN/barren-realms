"""
Xylarium enrichment: where the galaxy's elements come from, when, and where they go - its chemical evolution.

The Big Bang seeds only hydrogen and helium (and the light isotope of helium). Everything a world is built from is made
later, inside the galaxy, by stars that form from its gas - and it is carried, recycled, and lost:

  GAS        falls in from the cosmic web inside-out: each ring at its own pace (creation.infall_gyr: the core first, the
             rim last), toward the disc's exponential profile (scale length R_D, normalised by the measured surface
             density at the Sun's radius). The thinning web feeds each ring less as the universe expands.
  STARS      form from the gas at a share of it per orbit (Silk-Kennicutt: Sigma_SFR = 0.017 Sigma_gas Omega, Omega =
             V / r, measured) where the gas is dense enough to collapse against the disc's shear (Toomre:
             Sigma_crit = kappa sigma / 3.36 G, at Kennicutt's measured 0.7 of it). Below it the shear no longer
             sets the pace: the gas collapses on its own free-fall time, which at fixed thickness goes as
             Sigma^-1/2 - the Schmidt law Sigma^1.5, joined to the orbital law at the threshold: (Sigma / crit)^1/2.
             The inner disc, turning faster, makes its stars sooner; the outer disc stays gas-rich. A share R of what forms returns at once (the IMF's measured
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
             the disc: the share of what is made that the excess drives rises into the halo - and the halo gives it
             back: it cools and rains onto the disc over ~1 Gyr, where gas is falling in at the time (inside-out). What crosses the
             horizon passes into the paired sphere beyond, and as much comes back through its bounce.
  MODIFIED   matter is not only made but changed: stars burn hydrogen, making about two units of helium for every
             unit of metals (dY/dZ ~ 2, measured), so hydrogen runs down as the metals rise - the Sun's hydrogen,
             0.709 of its mass from the Big Bang's 0.752 (measured 0.715).
  LUMPS      mergers are rare: a star's birth cloud holds the long-mixed share of what they made, and of the recent
             share only what the events that actually struck its patch (~300 pc, ~100 Myr) gave - their number
             Poisson about the expected (the merger rate x the stars its patch formed then), drawn from the seed.
             Early, and at the thin rim, many stars are born with none of the heaviest and a few with a great deal;
             by today the lumps have mixed smooth.
  THE CENTRE what reaches the centre - the gas drifting all the way in, and what mixing carries inside the
             innermost ring - falls into it (blackhole.py): a share crosses the horizon to the paired sphere beyond,
             and its bounce sends as much back - the waves between the spheres feed the core - and all of it returns as
             the centre's outflow over an active episode, out past the bulge.

CALIBRATION. The yields are set by the measured gas at the Sun's radius today (young B stars: the Cosmic Abundance
Standard), one scale per channel from the element it dominates. The Sun itself is not put in: sun_birth() asks the
model where, 4.57 Gyr ago, the gas matched the Sun's composition - and the answer is a finding (stars migrate). Every
other place and time - the gradient, the core's early enrichment, the rim's late, how far each element reached - is
what the laws give. A universe with other initial conditions runs the same yields through its own history.

THE LEDGER. Nothing here is conserved from the Big Bang: the galaxy's metal mass grows as its stars make it, is
locked in stars, flows out past the disc, falls to the centre, crosses the horizon and comes back through the
paired sphere's bounce. budget() books every term.
"""

import functools
import math
from typing import Any, Dict, List, Optional, Tuple

DR_KPC = 0.5                    # ring width
DT_GYR = 0.1                    # time step
SIGMA_R0 = 50.0                 # Msun / pc^2: the disc's surface density at the Sun's radius (measured, Flynn 2006)
GAS_SIGMA_KMS = 6.0             # the cold gas's velocity dispersion (measured)
G_PC = 4.301e-3                 # G in pc Msun^-1 (km/s)^2
TOOMRE_SHARE = 0.7              # gas forms stars per orbit where it holds above ~0.7 of Toomre's critical density
                                # (Kennicutt 1989, measured); below it, on its own free-fall time
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
HALO_RETURN_GYR = 1.0           # what winds lift into the halo cools and rains back over ~1 Gyr (wind recycling in a
                                # galaxy of the Milky Way's mass: Oppenheimer & Dave 2008)
X_PRIMORDIAL = 0.752            # hydrogen's mass share from the Big Bang (Y_p = 0.248, measured)
DY_DZ = 2.0                     # helium made per unit of metals as stars burn hydrogen (measured, ~2)
Z_SUN = 0.0142                  # the Sun's metal share by mass (Asplund 2009)
RETURN_GYR = 0.1                # the centre's active episode: what it holds returns over ~100 Myr (blackhole.py)
SUN_AGE_GYR = 4.57

CHANNEL_DELAY = {"ccsn": (0.0, 0.04), "ia": (0.04, 14.0), "agb": (0.1, 10.0), "merger": (0.01, 14.0)}
# each element's share by channel (the solar system's origins; the superheavies only by mergers)
ORIGIN: Dict[str, Dict[str, float]] = {
    "C": {"ccsn": 0.5, "agb": 0.5}, "N": {"ccsn": 0.4, "agb": 0.6}, "O": {"ccsn": 1.0},
    "Na": {"ccsn": 0.8, "agb": 0.2}, "K": {"ccsn": 1.0}, "Mg": {"ccsn": 1.0}, "Al": {"ccsn": 1.0},
    "Si": {"ccsn": 0.7, "ia": 0.3}, "S": {"ccsn": 0.7, "ia": 0.3}, "Cl": {"ccsn": 0.8, "ia": 0.2},
    "Ca": {"ccsn": 0.7, "ia": 0.3}, "Ti": {"ccsn": 0.7, "ia": 0.3},
    "Fe": {"ccsn": 0.4, "ia": 0.6}, "Ni": {"ccsn": 0.4, "ia": 0.6}, "Cu": {"ccsn": 0.7, "ia": 0.3},
    "Xe": {"merger": 0.5, "agb": 0.5}, "Ba": {"agb": 0.85, "merger": 0.15}, "Pb": {"agb": 0.9, "merger": 0.1},
    "Pt": {"merger": 0.95, "agb": 0.05}, "Au": {"merger": 1.0}, "Th": {"merger": 1.0}, "U": {"merger": 1.0},
    "pyrosite": {"merger": 1.0}, "SpR": {"merger": 1.0}, "umbrite": {"merger": 1.0}, "aetherium": {"merger": 1.0},
    "AdL": {"merger": 1.0}, "mirror_glass": {"merger": 1.0},
}
PRIMORDIAL = ("H", "He", "He-3")
# the gas at the Sun's radius today, measured in the young B stars near it (the Cosmic Abundance Standard: Nieva &
# Przybilla 2012), in dex against the solar values (Asplund 2009); the mergers' share read from the young Cepheids'
# europium (~solar: Luck & Lambert 2011). This is what the yields are set by: the Sun is then a prediction.
ISM_TODAY_DEX = {"C": -0.10, "N": -0.04, "O": 0.07, "Mg": -0.04, "Si": -0.01, "Fe": 0.02, "Eu": 0.0}
CALIBRATION = "ism_today"       # or "sun": the gas the Sun formed from
MERGER_PER_MSUN = 2.0e-5        # neutron-star mergers per solar mass of stars formed (~1 per 5e4: the Galaxy's merger
                                # rate over its star formation rate, measured)
MIX_KPC = 0.3                   # how far turbulence spreads one event's matter before stars form from it (~300 pc
MIX_GYR = 0.1                   # in ~100 Myr, measured)


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
    halo = {k: 0.0 for k in metal}
    r_edge = rings[-1][1]
    width = r_edge / 2.0                                                    # the extended disc: out to 1.5 x the optical
    r_mid = r_edge + width / 2.0
    tau_b = max(t1, 1.033 * r_mid - 1.267) * assembly
    beyond = {"gas": 0.0, "metal": {k: 0.0 for k in metal}, "area": math.pi * ((r_edge + width) ** 2 - r_edge ** 2),
              "sigma": _sigma_total(r_mid), "tau": tau_b, "width": width,
              "norm": 1.0 - math.exp(-max(1e-9, cosmos_today() - t1) / tau_b)}
    gpool = [[0.0] * len(SLOW_RETURN) for _ in range(nr)]
    book = {"made": 0.0, "locked": 0.0, "outflow": 0.0, "horizon": 0.0, "bounced": 0.0, "returned": 0.0}
    hist_gas: List[List[float]] = []
    hist_metal: List[Dict[Tuple[str, str], List[float]]] = []
    hist_merger: List[List[float]] = []
    for n in range(steps):
        t = n * DT_GYR
        for j in range(nr):
            if t > t1:
                inflow = _sigma_total(rings[j][2]) / tau[j] * math.exp(-(t - t1) / tau[j]) / norm[j]
                gas[j] += inflow * DT_GYR
            omega = cosmos.V_FLAT_KMS / max(DR_KPC / 2.0, rings[j][2]) * 1.0227      # per Gyr (km/s/kpc -> 1/Gyr)
            kappa_pc = math.sqrt(2.0) * cosmos.V_FLAT_KMS / max(DR_KPC / 2.0, rings[j][2]) / 1000.0  # km/s per pc
            crit = TOOMRE_SHARE * kappa_pc * GAS_SIGMA_KMS / (3.36 * G_PC)
            unstable = min(1.0, (gas[j] / crit) ** 0.5) if crit > 0 else 1.0     # below: its own free fall
            sfr = PER_ORBIT * stars * gas[j] * omega * unstable if gas[j] > 0 else 0.0
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
        # the disc's gas drifts inward, its metals with it; what drifts out of the innermost ring feeds the centre
        drift = min(0.5, INFLOW_KMS * 1.0227 * DT_GYR / DR_KPC)             # share of a ring's gas crossing inward
        for j in range(0, nr):
            moved = gas[j] * drift
            if moved <= 0:
                continue
            gas[j] -= moved
            for key2, arr in metal.items():
                m_ = arr[j] * drift
                arr[j] -= m_
                if j == 0:
                    book["horizon"] += m_ * blackhole.HORIZON_SHARE      # across, to the paired sphere...
                    book["bounced"] += m_ * blackhole.HORIZON_SHARE      # ...and as much back from its bounce
                    centre[key2] += m_
                else:
                    arr[j - 1] += m_
            if j > 0:
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
                    halo[(s, c)] += made * wind[j]                          # lifted into the halo
                    made *= 1.0 - wind[j]
                _spread(arr, made, j, lam[s][j], book, centre, (s, c), bulge, beyond)
            give = centre[(s, c)] * min(1.0, DT_GYR / RETURN_GYR)          # the centre gives back as its outflow,
            if give > 0:                                                    # out past the bulge it fell into
                centre[(s, c)] -= give
                book["returned"] += give
                b_edge = len(bulge)
                _spread(arr, give, b_edge, lam[s][b_edge], book, centre, (s, c), bulge, beyond)
        rain = min(1.0, DT_GYR / HALO_RETURN_GYR)                           # the halo rains back where gas falls in
        infall_w = [area[j] * _sigma_total(rings[j][2]) / tau[j] * math.exp(-max(0.0, t - t1) / tau[j]) / norm[j]
                    for j in range(nr)]                                     # now: inside-out, as the gas itself
        infall_sum = sum(infall_w) or 1.0
        for key2, arr in metal.items():
            back = halo[key2] * rain
            if back > 0:
                halo[key2] -= back
                book["rained"] = book.get("rained", 0.0) + back
                for j in range(nr):
                    arr[j] += back * infall_w[j] / infall_sum
        hist_merger.append(list(out["merger"]))
        hist_gas.append(list(gas))
        hist_metal.append({k: list(v) for k, v in metal.items()})
    book["beyond"] = sum(beyond["metal"].values())
    return {"rings": rings, "area": area, "gas": hist_gas, "metal": hist_metal, "steps": steps, "book": book,
            "centre": centre, "sfr": sfr_hist, "beyond": beyond, "pools": pools, "merger": hist_merger, "halo": halo}


def _spread(arr: List[float], mass: float, j: int, lam: float, book: Dict[str, float],
            centre: Optional[Dict[Any, float]] = None, ckey: Any = None, bulge: Any = (),
            beyond: Optional[Dict[str, Any]] = None) -> None:
    """Deposit what was made at ring j over its travel length, inward and outward (exp(-|dr| / lambda)): what is
    carried inside the innermost ring falls to the centre (a share across the horizon), what lands past the disc
    joins the extended gas beyond it."""
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
        arr[k] += mass * q ** abs(k - j) / total
    if to_centre > 0:
        if centre is None:
            arr[0] += to_centre
            return
        book["horizon"] += to_centre * blackhole.HORIZON_SHARE          # across, to the paired sphere...
        book["bounced"] += to_centre * blackhole.HORIZON_SHARE          # ...and as much back from its bounce
        centre[ckey] = centre.get(ckey, 0.0) + to_centre


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


@functools.lru_cache(maxsize=4)
def _calibration(mode: str = None) -> Dict[Tuple[str, str], float]:
    """Each (element, channel)'s unit-yield concentration at the calibration point, divided by that channel's yield
    scale: relative() divides by it.
      ism_today  the measured gas at R0 today (ISM_TODAY_DEX). One yield scale per channel, solved from the element
                 it dominates: core-collapse from oxygen, Type Ia from iron (with core-collapse's share), the giants
                 from nitrogen, mergers from europium; carbon, magnesium and silicon are left as checks.
      sun        the gas the Sun formed from, every element at its solar value (the old calibration)."""
    mode = mode or CALIBRATION
    if mode == "sun":
        snap = _snapshot(_key(None), _sun_birth())
        j = _ring_of(snap["rings"], _r0())
        return {k: arr[j] / max(1e-30, snap["area"][j] * snap["gas"][j]) for k, arr in snap["metal"].items()}
    snap = _snapshot(_key(None), cosmos_today())
    j = _ring_of(snap["rings"], _r0())
    g = snap["area"][j] * snap["gas"][j]
    t = {e: 10 ** v for e, v in ISM_TODAY_DEX.items()}
    k = {"ccsn": t["O"]}
    k["ia"] = (t["Fe"] - ORIGIN["Fe"]["ccsn"] * k["ccsn"]) / ORIGIN["Fe"]["ia"]
    k["agb"] = (t["N"] - ORIGIN["N"]["ccsn"] * k["ccsn"]) / ORIGIN["N"]["agb"]
    k["merger"] = t["Eu"]
    return {key: arr[j] / max(1e-30, g) / k[key[1]] for key, arr in snap["metal"].items()}


def _r0() -> float:
    from xylarium.kernel import cosmos
    return cosmos.R0_KPC


def _ring_of(rings: List[Tuple[float, float, float]], r: float) -> int:
    return max(0, min(len(rings) - 1, int(r / DR_KPC)))


def relative(seed: Any, sym: str, r: float, t: float, lump: float = 1.0) -> float:
    """An element's abundance in the gas at radius r and epoch t, relative to the Sun's birth gas (1 there): what a
    star and its worlds born there and then are made of. Primordial matter is 1 everywhere."""
    base = sym.split("-")[0] if sym not in ORIGIN else sym
    if sym in ("H", "He"):                                          # burned and made as the metals rise
        z = metals(seed, r, t) * Z_SUN
        if sym == "H":
            return (X_PRIMORDIAL - (1.0 + DY_DZ) * z) / (X_PRIMORDIAL - (1.0 + DY_DZ) * Z_SUN)
        y0 = 1.0 - X_PRIMORDIAL
        return (y0 + DY_DZ * z) / (y0 + DY_DZ * Z_SUN)
    if sym in PRIMORDIAL or base not in ORIGIN:
        return 1.0
    snap = _snapshot(_key(seed), t)
    j = _ring_of(snap["rings"], r)
    cal = _calibration(CALIBRATION)
    g = snap["gas"][j] * snap["area"][j]
    if g <= 0:
        return 0.0
    tot = 0.0
    for c, f in ORIGIN[base].items():
        conc = snap["metal"][(base, c)][j] / g
        tot += f * conc / max(1e-30, cal[(base, c)]) * (lump if c == "merger" else 1.0)
    return tot


def of_good(seed: Any, sym: str, r: float, t: float, lump: float = 1.0) -> float:
    """A good's abundance relative to the Sun's birth gas: an element's own; a compound's, its scarcest constituent's
    (beyond the primordial hydrogen)."""
    from xylarium.kernel import substances
    parts = [x for x in substances.constituents(sym) if x not in PRIMORDIAL]
    if not parts:
        return 1.0
    if sym in ORIGIN:
        return relative(seed, sym, r, t, lump)
    return min(relative(seed, x, r, t, lump) for x in parts)


def rprocess_lump(seed: Any, r: float, t: float, u: float) -> float:
    """The share of the mergers' smooth expectation a star's birth cloud holds, for its own draw u (0 .. 1): the
    long-mixed part, plus the recent part scaled by how many events actually struck its patch (Poisson)."""
    run = _run(_key(seed))
    n = max(0, min(run["steps"] - 1, int(round(t / DT_GYR))))
    j = _ring_of(run["rings"], r)
    held = run["metal"][n].get(("U", "merger"), [0.0])[j]
    if held <= 0:
        return 0.0 if run["merger"][n][j] <= 0 else 1.0
    recent = min(1.0, run["merger"][n][j] * (MIX_GYR / DT_GYR) / held)
    formed = run["sfr"][j][n] * math.pi * (MIX_KPC * 1000.0) ** 2 * MIX_GYR          # Msun in its patch, then
    expect = MERGER_PER_MSUN * formed
    if expect <= 0:
        return 1.0 - recent
    k, p, cum = 0, math.exp(-expect), math.exp(-expect)
    while u > cum and k < 1000:                                               # Poisson by its inverse
        k += 1
        p *= expect / k
        cum += p
    return (1.0 - recent) + recent * k / expect


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
    """Where the metals made over the galaxy's history are now, as shares of what was made (unit yields): in its
    gas, in its stars (locked, or in giants still to give back), in the halo (lifted by winds, raining back), passed
    across the horizon to the paired sphere (and, negative, what its bounce sent back), held at the centre, in the
    extended gas past the disc. The shares close: everything is somewhere in the flow."""
    run = _run(_key(seed))
    snap = _snapshot(_key(seed), (run["steps"] - 1) * DT_GYR)            # the run's own end: its books are its whole
    made = run["book"]["made"] or 1.0
    in_gas = sum(sum(arr) for arr in snap["metal"].values())
    held = sum(run["centre"].values())
    giving = sum(sum(sum(p_) for p_ in rings_) for rings_ in run["pools"].values())     # in giants, still to return
    return {"made": 1.0, "gas": in_gas / made, "locked": (run["book"]["locked"] + giving) / made,
            "halo": sum(run["halo"].values()) / made, "horizon": run["book"]["horizon"] / made,
            "bounced": -run["book"]["bounced"] / made,
            "centre": held / made, "beyond": sum(run["beyond"]["metal"].values()) / made}


SUN_CHECK = ("C", "N", "O", "Mg", "Si", "Fe", "U")     # the Sun's composition, solar by definition (0 dex)


def sun_birth(seed: Any = None) -> Dict[str, Any]:
    """Where in the disc, 4.57 Gyr before today, the gas matched the Sun's composition: the radius whose gas lies
    nearest to solar across C, N, O, Mg, Si, Fe and the mergers' uranium (rms of the dex differences). Returns the
    best radius, its rms, each element there, and the rms at every radius."""
    t = cosmos_today() - SUN_AGE_GYR
    curve = []
    for _, _, m in _rings():
        dex = {s_: math.log10(max(1e-30, relative(seed, s_, m, t))) for s_ in SUN_CHECK}
        rms = math.sqrt(sum(v * v for v in dex.values()) / len(dex))
        curve.append((m, rms, dex))
    best = min(curve, key=lambda c: c[1])
    return {"r_kpc": best[0], "rms_dex": best[1], "dex": best[2], "curve": [(m, rms) for m, rms, _ in curve]}

