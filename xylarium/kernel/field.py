"""
Xylarium field: what moves through the universe, carried - not walked (docs/FIELD_ENGINE.md).

Every singularity is a BELL: it rings its own pulse (a Source - the bounce, its echo, a dying star, a jet, a word).
What a bell sends reaches a place at the earliest time a physical carrier can bring it (light through ordinary space,
with its Shapiro delay; a throat across its span) - computed ONCE when it rings, and queued in exact deep time. Each
tick the arrivals the cosmic clock has passed are handed to the laws that take them (handlers by kind). The field's
value at a place and time is closed form: every arrived front's strength over its distance, shaped by its pulse's
decay - no walk over worlds. Events are for EXTERNAL arrivals; a people's own dynamics are never frozen waiting for
them. The field is internal physics (floats); arrival times enter the kernel as exact Fractions of deep time.
"""

import heapq
import math
from fractions import Fraction
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

HANDLERS: Dict[str, Callable[[Any, Dict[str, Any], Dict[str, Any]], None]] = {}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "field")


def handles(kind: str) -> Callable:
    """Register the law that takes a kind's arrivals: f(kernel, source, arrival)."""
    def wrap(f: Callable) -> Callable:
        HANDLERS[kind] = f
        return f
    return wrap


def place_of(kernel: Any, sector_id: int, gyr: Optional[float] = None) -> Optional[Tuple[float, float, float]]:
    """A system's galactocentric place (kpc) now - or at a deep time, as its orbit carries it."""
    from xylarium.kernel import cosmos
    p = cosmos.position(kernel, sector_id)
    return (p["x"], p["y"], p["z"]) if p else None


def light_gyr(a: Sequence[float], b: Sequence[float]) -> float:
    from xylarium.kernel import geometry
    return geometry.light_gyr(a, b)


CARRIERS: List[Callable[[Any, Dict[str, Any], int, Sequence[float]], Optional[float]]] = []


def carrier(f: Callable) -> Callable:
    CARRIERS.append(f)
    return f


@carrier
def _light(kernel: Any, src: Dict[str, Any], sector_id: int, at: Sequence[float]) -> Optional[float]:
    """Light through ordinary space: its proper travel time, Shapiro delay and all."""
    return float(src["t"]) + light_gyr(src["at"], at)


def arrival(kernel: Any, src: Dict[str, Any], sector_id: int, at: Sequence[float]) -> Optional[float]:
    """The earliest a physical carrier brings the source's front to a place (deep Gyr), or None."""
    times = [t for t in (c(kernel, src, sector_id, at) for c in CARRIERS) if t is not None]
    return min(times) if times else None


def ring(kernel: Any, src: Dict[str, Any], targets: Iterable[int]) -> int:
    """A bell rings: its arrival at each target system is computed once, by its earliest carrier, and queued in exact
    deep time. Returns the arrivals queued."""
    st = stats(kernel)
    st["next"] += 1
    sid = f"S{st['next']}"
    src = dict(src, id=sid, t=str(Fraction(src["t"])), at=list(src["at"]))
    st["sources"][sid] = src
    n = 0
    for target in targets:
        at = place_of(kernel, target)
        if at is None:
            continue
        t = arrival(kernel, src, target, at)
        if t is None:
            continue
        heapq.heappush(st["queue"], [float(t), str(Fraction(t)), sid, int(target)])    # ordered; exact beside
        n += 1
    return n


def pump(kernel: Any) -> int:
    """Hand every arrival the cosmic clock has passed to the law that takes its kind. Returns arrivals delivered."""
    from xylarium.kernel import cosmos
    st = stats(kernel)
    q = st["queue"]
    if not q:
        return 0
    now = Fraction(cosmos.deep_gyr(kernel))
    done = 0
    while q and Fraction(q[0][1]) <= now:
        _, t, sid, target = heapq.heappop(q)
        src = st["sources"].get(sid)
        if src is None:
            continue
        f = HANDLERS.get(src["kind"])
        if f is not None:
            f(kernel, src, {"t": t, "sector": target})
        done += 1
        src["delivered"] = src.get("delivered", 0) + 1
    st["delivered"] = st.get("delivered", 0) + done
    _forget(st, now)
    return done


FADED = 14.0                    # e-folds after which a pulse is a millionth of itself: gone from the field


def _forget(st: Dict[str, Any], now: Fraction) -> None:
    """A source is dropped once every arrival is delivered and it adds nothing more: an event with no pulse at once,
    a pulse once it has died away (FADED e-folds past its ringing)."""
    live = {e[2] for e in st["queue"]}
    for sid, src in list(st["sources"].items()):
        if sid in live:
            continue
        tau = float(src.get("tau") or 0.0)
        if tau <= 0 or float(now) - float(Fraction(src["t"])) > FADED * tau:
            st["sources"].pop(sid, None)


def value(kernel: Any, at: Sequence[float], t: float) -> float:
    """The field at a place and deep time: the sum over every source whose front has reached it of its strength over
    its distance, shaped by its pulse's decay since its front arrived (e-fold tau, Gyr). Closed form - no walk."""
    st = stats(kernel)
    total = 0.0
    for src in st["sources"].values():
        t0 = float(Fraction(src["t"]))
        d = max(1e-6, math.dist(src["at"], at))
        arrived = t0 + light_gyr(src["at"], at)
        if t < arrived:
            continue
        tau = float(src.get("tau") or 0.0)
        if tau <= 0:
            continue                                     # an event, not a pulse: it adds to no field
        total += float(src.get("strength", 1.0)) / d * math.exp(-(t - arrived) / tau)
    return total


# ---------------------------------------------------------------------- the star absorbs the pulse (field law (2))
# Energy is in the exact unit Earth-mass AU^2 (year / 2 pi)^-2: an orbit's stiffness is then M / a^3 (the 4 pi^2 of
# Kepler's third law absorbed in the unit), and every quantity below is a Fraction - floats never touch an orbit.
NUCLEON_MEV = Fraction("938.272")    # a nucleon's rest energy (MeV): what a fusion step's binding is a share of
WEAK_MEV = Fraction("1.29333") - Fraction("0.51100")    # a proton made a neutron: m_n - m_p + m_e, less 2 m_e back
STEPS = {"main": ({"H": 4}, {"He": 1}), "giant": ({"He": 3}, {"C": 1})}   # the burning a star is on, by its stage


def burn_out_share(kernel: Any, sector_id: int) -> Fraction:
    """The share of what a star burns that burns OUT: the mass defect of the fusion step it is on - its stage's
    reaction, the binding it releases over its inputs' rest energy (substances' binding energies) - its own, never
    hydrogen's for every star. A remnant burns nothing."""
    from xylarium.kernel import cosmos, substances
    sec = kernel.sectors.get(sector_id)
    if sec is None or "remnant" in (getattr(sec, "star_type", "") or "").lower():
        return Fraction(0)
    life = cosmos.star_life(kernel, sector_id) if cosmos.is_cosmic(kernel) else None
    stage = "giant" if life and cosmos.deep_gyr(kernel) > life[1] else "main"
    ins, outs = STEPS[stage]
    released = Fraction(substances.transmutation_mev(ins, outs))
    # protons the step turns to neutrons (beta-plus): each costs m_n - m_p + m_e and its positron's annihilation
    # gives 2 m_e back - net WEAK_MEV each (hydrogen to helium turns two)
    z_in = sum(n * int(substances.element(s)["Z"]) for s, n in ins.items())
    z_out = sum(n * int(substances.element(s)["Z"]) for s, n in outs.items())
    released -= max(0, z_in - z_out) * WEAK_MEV
    nucleons = sum(Fraction(n) * Fraction(substances.element(s)["A"]) for s, n in ins.items())
    return max(Fraction(0), Fraction(released) / (nucleons * NUCLEON_MEV))     # exact: a float never leaks in


GRID = 60                       # bits of the grid every derived length and rate is fixed on before the algebra


def grid(x: Any) -> Fraction:
    """A value put on the exact grid of 2^-60, rounded down (xyl-core certified::down)."""
    f = Fraction(x)
    return Fraction((f * (1 << GRID)).__floor__(), 1 << GRID)


def anchors_of(kernel: Any, sector_id: int) -> List[Dict[str, Any]]:
    """A star's worlds as it holds them: each a 0D anchor at its core, its native place on its orbit of radius a AU
    from the star's G point, where it stands now (sheared by what the star could not re-lock), and its mass."""
    from xylarium.kernel import physics
    sec = kernel.sectors.get(sector_id)
    kept = (stats(kernel).get("anchors") or {}).get(str(sector_id)) or {}
    out = []
    for w in (sec.planets if sec is not None else []):
        b = physics.body(w)
        if "q" not in b:
            continue
        native = (Fraction(b["q"]) ** 2, Fraction(0), Fraction(0))
        at = tuple(Fraction(x) for x in kept[w.id]) if w.id in kept else native
        out.append({"id": w.id, "native": native, "at": at, "mass": Fraction(b.get("mass", 1))})
    return out


def absorb_at(star_mass: Fraction, burn_share: Fraction, anchors: List[Dict[str, Any]], pulse_versor: Any,
              energy: Any) -> Dict[str, Any]:
    """A star absorbs a pulse (field law (2), as xyl-cosmos field::absorb): the pulse carries each world from where
    it stands, relative to the star's G point, which it carries too (the DRIFT, which shears no orbit); the star's
    gravity pulls each back toward its native place by the share of the work it can pay for (1/2 m (M/a^3) |dx|^2,
    all it can of what came in); what it cannot re-lock stays, exact on the grid. The rest it burns: a share burns
    OUT, the rest leaves as LIGHT. In = gravity + light + burned out, exactly."""
    from xylarium.kernel import versor
    e_in = Fraction(energy)
    carry = (lambda x: _screw_move(pulse_versor, x)) if isinstance(pulse_versor, dict) else \
        (lambda x: versor.move(pulse_versor, x))
    drift = carry((0, 0, 0))
    moved, need = [], Fraction(0)
    for w in anchors:
        c = carry(w["at"])
        dx = tuple(c[i] - drift[i] - w["native"][i] for i in range(3))
        a = max(abs(x) for x in w["native"])
        a2 = sum(x * x for x in w["native"])
        if a > 0:
            need += w["mass"] * star_mass / (a2 * a) * sum(x * x for x in dx) / 2
        moved.append(dx)
    gravity = min(e_in, need)
    held = gravity / need if need > 0 else Fraction(1)
    left = 1 - held
    new = [dict(w, at=tuple(w["native"][i] + grid(left * dx[i]) for i in range(3))) for w, dx in zip(anchors, moved)]
    rest = e_in - gravity
    burned = rest * burn_share
    light = rest - burned
    assert gravity + light + burned == e_in                   # the field law's conservation, exactly
    return {"in": e_in, "gravity": gravity, "light": light, "burned_out": burned, "anchors": new, "drift": drift}


def _screw_move(sc: Dict[str, Any], x: Sequence[Fraction]) -> Tuple[Fraction, Fraction, Fraction]:
    """A screw's action on a point, exactly: the rotor 1 + B(b) (b = t x axis) turns it by Rodrigues' rational form -
    the same point the versor sandwich gives (tests hold the two equal) - and the translation along its axis follows."""
    b, al = sc["b"], sc["along"]
    bb = b[0] * b[0] + b[1] * b[1] + b[2] * b[2]
    bx = b[0] * x[0] + b[1] * x[1] + b[2] * x[2]
    cr = (b[1] * x[2] - b[2] * x[1], b[2] * x[0] - b[0] * x[2], b[0] * x[1] - b[1] * x[0])
    return tuple(((1 - bb) * x[i] + 2 * bx * b[i] - 2 * cr[i]) / (1 + bb) + al[i] for i in range(3))


def _book(kernel: Any, sector_id: int, a: Dict[str, Any], k: int = 1) -> Dict[str, str]:
    """A star's books: all it has absorbed since its first pulse, as gravity, light and what burned out."""
    from xylarium.kernel import cosmos
    book = stats(kernel).setdefault("stars", {}).setdefault(str(sector_id), {"in": "0", "gravity": "0", "light": "0",
                                                                            "burned_out": "0"})
    book.setdefault("since", str(Fraction(cosmos.deep_gyr(kernel))))
    for key in ("in", "gravity", "light", "burned_out"):
        book[key] = str(Fraction(book[key]) + a[key] * k)
    book["pulses"] = int(book.get("pulses", 0)) + k
    return book


def _keep(kernel: Any, sector_id: int, anchors: List[Dict[str, Any]], drift: Sequence[Fraction]) -> None:
    st = stats(kernel)
    st.setdefault("anchors", {})[str(sector_id)] = {w["id"]: [str(x) for x in w["at"]] for w in anchors
                                                    if w["at"] != w["native"]}
    if not st["anchors"][str(sector_id)]:
        st["anchors"].pop(str(sector_id))
    st.setdefault("drift", {})[str(sector_id)] = [str(x) for x in drift]


def drift_au(kernel: Any, sector_id: int) -> Tuple[Fraction, Fraction, Fraction]:
    """How far the pulses have carried a star from its galactic orbit (AU)."""
    d = (stats(kernel).get("drift") or {}).get(str(sector_id))
    return tuple(Fraction(x) for x in d) if d else (Fraction(0), Fraction(0), Fraction(0))


def absorb(kernel: Any, sector_id: int, pulse_versor: Any, energy: Any) -> Dict[str, Any]:
    """A star absorbs an arriving pulse where its worlds stand; its books, anchors and drift kept."""
    from xylarium.kernel import physics
    sec = kernel.sectors.get(sector_id)
    if sec is None:
        return {}
    anchors = anchors_of(kernel, sector_id)
    a = absorb_at(Fraction(physics.star(sec)["mass"]), burn_out_share(kernel, sector_id), anchors, pulse_versor,
                  energy)
    _book(kernel, sector_id, a)
    _keep(kernel, sector_id, a["anchors"], tuple(x + y for x, y in zip(drift_au(kernel, sector_id), a["drift"])))
    return {"in": str(a["in"]), "gravity": str(a["gravity"]), "light": str(a["light"]),
            "burned_out": str(a["burned_out"]),
            "unlocked": {w["id"]: str(sum((x - y) ** 2 for x, y in zip(w["at"], w["native"])))
                         for w in a["anchors"] if w["at"] != w["native"]}}


def quantum_flux(kernel: Any, planet: Any) -> Fraction:
    """QUANTUM RADIATION at a world (field law (1)): the bell's pulses its star has absorbed, a year on the mean since
    it first absorbed one, over the square of the world's orbit - measured, exact; strongest where pulses crowd (near
    the cores and their discs). 0 where its star has absorbed none."""
    from xylarium.kernel import cosmos, physics
    book = (stats(kernel).get("stars") or {}).get(str(planet.sector_id)) if "field" in kernel.state else None
    b = physics.body(planet)
    if not book or "q" not in b:
        return Fraction(0)
    years = (Fraction(cosmos.deep_gyr(kernel)) - Fraction(book.get("since", "0"))) * 10 ** 9
    if years <= 0:
        return Fraction(0)
    return Fraction(book["in"]) / years / Fraction(b["q"]) ** 4


# ---------------------------------------------------------------------- the bells (field law; xyl-cosmos field.rs)
# Every hole is a bell: the core, and each hole a heavy star leaves (blackhole.py throats). A BELL'S SCREW is its own:
# its pitch is the core's wavelength (light's round trip to the rim) scaled by the cube root of its mass over the
# core's (the Einstein-Cartan bounce radius at the Cartan density ~ M^(1/3)); its rotor turns about its hole's spin
# axis by its Kerr spin; it rings once a period (its pitch at light speed), each ring carrying its light for a period.
AU_PER_KPC = Fraction("206264806.247")
SUN_YEAR = Fraction("2.28002")          # a sun's light for a year in the energy unit (Earth-mass AU^2 (yr/2pi)^-2)
HOLE_LIGHT_PER_SUN = 32000 * Fraction(1, 10) * Fraction(1, 10)   # Eddington x horizon share x efficiency (centre)
G_KPC = 4.30091e-6                      # G in kpc (km/s)^2 per sun
C_KMS = 299792.0
C_KPC_YR = 299792 * 1.0227e-9           # light in kpc a year
CORE_SPIN = Fraction(7, 10)             # the core's measured Kerr spin
RINGS = 64                              # rings absorbed one by one in a step; past it the last one's books repeat


def wavelength_kpc() -> float:
    from xylarium.kernel import cosmos
    return C_KPC_YR * (2.0 * cosmos.R_MAX_KPC / C_KPC_YR)


def _drawn_spin(seed: int, n: int) -> Fraction:
    """A stellar hole's Kerr spin, drawn from its seed in (0, 1) - never chosen (as xyl-cosmos drawn_spin)."""
    import blake3
    h = blake3.blake3(derive_key_context="xylarium 2026-10-08 stellar hole spin")
    h.update(int(seed).to_bytes(8, "little", signed=False))
    h.update(int(n).to_bytes(8, "little", signed=False))
    x = int.from_bytes(h.digest()[:8], "little") >> 12
    return Fraction(x + 1, (1 << 52) + 2)


def bells(kernel: Any) -> List[Dict[str, Any]]:
    """The bells the field rings from: the core, and every hole a dying star has left (each a throat)."""
    from xylarium.kernel import blackhole, cosmos
    bh = blackhole.stats(kernel)
    core_m = float(bh.get("mass", blackhole.MASS0))
    seed = int(getattr(kernel, "seed", 0) or 0) & ((1 << 64) - 1)
    out = []

    def bell(at: Any, mass: float, axis: Tuple[Fraction, ...], spin: Fraction, born: float, name: str) -> None:
        pitch = wavelength_kpc() * max(1e-30, mass / core_m) ** (1.0 / 3.0)
        m = grid(mass)
        out.append({"name": name, "at": at, "axis": axis, "spin": spin, "pitch_kpc": grid(pitch),
                    "period_yr": grid(pitch / C_KPC_YR), "mass": m, "light": m * HOLE_LIGHT_PER_SUN, "born": born})
    bell(None, core_m, (Fraction(0), Fraction(0), Fraction(1)), CORE_SPIN, 0.0, "centre")
    for tid, rec in sorted((bh.get("throats") or {}).items()):
        if not isinstance(rec, dict) or rec.get("kind") not in ("stellar", "kindled") or rec.get("near") is None:
            continue
        sid = int(rec["near"])
        g = cosmos.stats(kernel)["place"].get(str(sid)) if cosmos.is_cosmic(kernel) else None
        vz = 0.0
        if g and "cell" in g:
            from xylarium.kernel import creation
            vz = float((creation.cell(cosmos.cosmos_seed(kernel), *g["cell"])[g["k"]].get("vertical") or {})
                       .get("vz_kms", 0.0))
        # its progenitor's orbit normal: tilted by its vertical speed against the circular, the line of nodes at
        # its reference azimuth
        v = cosmos.V_FLAT_KMS
        cos_t = v / math.hypot(v, vz)
        sin_t = math.sqrt(max(0.0, 1.0 - cos_t * cos_t))
        node = float(g["theta0"]) if g else 0.0
        axis = (grid(sin_t * math.sin(node)), grid(-sin_t * math.cos(node)), grid(cos_t))
        bell(sid, float(rec.get("mass") or 0.0), axis, _drawn_spin(seed, sid), float(rec.get("opened") or 0.0), tid)
    return out


def arrivals(b: Dict[str, Any], delay_yr: float, from_gyr: float, to_gyr: float) -> int:
    """A bell's rings that reach a place `delay_yr` of light away within (from, to]: ring k sounds at born + k
    periods and arrives a light time later. Closed form."""
    period = float(b["period_yr"])
    if period <= 0 or to_gyr <= from_gyr:
        return 0

    def ring(gyr: float) -> int:
        since = gyr * 1e9 - b["born"] * 1e9 - delay_yr
        return -1 if since < 0 else int(since // period)
    return max(0, ring(to_gyr) - ring(from_gyr))


def received(b: Dict[str, Any], d_kpc: float) -> Any:
    """The pulse as it reaches a place d_kpc away: the bell's screw scaled by the strain it brings there - a turn
    about its axis by 2 atan(t |axis|), t = spin x r_g / d, carrying the place along the axis by the pitch in
    proportion to the turn (AU)."""
    rg = G_KPC * float(b["mass"]) / (C_KMS * C_KMS)
    t = grid(float(b["spin"]) * rg / max(d_kpc, 1e-9))
    x, y, z = b["axis"]
    norm = math.sqrt(float(x * x + y * y + z * z))
    angle = 2.0 * math.atan(float(t) * norm)
    shift = float(b["pitch_kpc"]) * float(AU_PER_KPC) * angle / (2.0 * math.pi) / max(norm, 1e-30)
    along = tuple(grid(shift * float(c)) for c in b["axis"])
    return {"b": (t * x, t * y, t * z), "along": along, "t": t, "axis": b["axis"]}


def screw_versor(sc: Dict[str, Any]) -> Any:
    """A received screw as its Cl(4,1) versor: the translator along its axis after its rotor (the seat wire's Mv)."""
    from xylarium.kernel import versor
    t, (x, y, z) = sc["t"], sc["axis"]
    return versor.translator(sc["along"]) * versor.Mv({0: 1, 6: t * x, 5: -t * y, 3: t * z})


def energy_at(b: Dict[str, Any], d_kpc: float, a_out_au: Fraction) -> Fraction:
    """One ring's energy a system out to a_out AU intercepts d_kpc away: its light over a period, the share of the
    sphere the system's disc covers (a^2 / 4 d^2, exact)."""
    d_au = max(grid(d_kpc * float(AU_PER_KPC)), Fraction(1))
    return b["light"] * b["period_yr"] * SUN_YEAR * (a_out_au * a_out_au) / (4 * d_au * d_au)


def step(kernel: Any, from_gyr: float, to_gyr: float) -> int:
    """Deliver every ring arriving in (from, to] at the stars the peoples live by (a pulse is delivered where it is
    read; its arrivals counted in closed form, never walked over the galaxy). Each star absorbs each ring where its
    worlds stand; each ring's translation drifts it, and its next arrivals are timed from where it stands. Once a
    ring finds the worlds at their native places and leaves them there, every later ring of that bell in the step
    is the same ring: its books are counted, not recomputed. Returns the rings delivered."""
    from xylarium.kernel import geometry, physics
    stars = sorted({p.sector_id for sec in kernel.sectors.values() for p in sec.planets
                    if p.civilization is not None and p.population > 0})
    bs = [b for b in bells(kernel) if b["born"] < to_gyr]
    delivered = 0
    for sid in stars:
        sec = kernel.sectors.get(sid)
        orbit = place_of(kernel, sid)
        anchors = anchors_of(kernel, sid)
        if sec is None or orbit is None or not anchors:
            continue
        a_out = max(w["native"][0] for w in anchors)
        mass = Fraction(physics.star(sec)["mass"])
        share = burn_out_share(kernel, sid)
        drift = list(drift_au(kernel, sid))
        touched = False
        tally = {"in": Fraction(0), "gravity": Fraction(0), "light": Fraction(0), "burned_out": Fraction(0)}
        pulses = 0
        for b in bs:
            src = (0.0, 0.0, 0.0) if b["at"] is None else place_of(kernel, b["at"])
            if src is None:
                continue
            here = tuple(orbit[i] + float(drift[i] / AU_PER_KPC) for i in range(3))
            d = geometry.proper_kpc(src, here)
            k = arrivals(b, d / C_KPC_YR, from_gyr, to_gyr)
            if k == 0:
                continue
            v, e = received(b, d), energy_at(b, d, a_out)
            done, last = 0, None
            while done < min(k, RINGS):
                settled = all(w["at"] == w["native"] for w in anchors)
                last = absorb_at(mass, share, anchors, v, e)
                anchors = last["anchors"]
                drift = [x + y for x, y in zip(drift, last["drift"])]
                for key in tally:
                    tally[key] += last[key]
                done += 1
                if settled and all(w["at"] == w["native"] for w in anchors):
                    break                                    # a fixed point: the rest are this ring again
            if last is not None and k > done:
                rest = k - done
                drift = [x + y * rest for x, y in zip(drift, last["drift"])]
                for key in tally:
                    tally[key] += last[key] * rest
            delivered += k
            pulses += k
            touched = True
        if touched:
            _book(kernel, sid, tally)                          # the books written once a step, exactly
            stats(kernel)["stars"][str(sid)]["pulses"] += pulses - 1
            _keep(kernel, sid, anchors, drift)
    return delivered


@handles("pulse")
def _pulse_arrives(kernel: Any, src: Dict[str, Any], arr: Dict[str, Any]) -> None:
    """A bell's pulse reaches a star: it absorbs it (its versor and its energy, both exact)."""
    from xylarium.kernel import versor
    if src.get("versor") and src.get("energy") is not None:
        absorb(kernel, int(arr["sector"]), versor.from_wire(src["versor"]), src["energy"])


def season(kernel: Any) -> List[str]:
    """Each season the fronts the cosmic clock has passed reach their places (each keeps its exact arrival time),
    and the bells' rings since the last season reach the stars the peoples live by."""
    from xylarium.kernel import cosmos
    pump(kernel)
    if cosmos.is_cosmic(kernel):
        st = stats(kernel)
        now = float(cosmos.deep_gyr(kernel))
        last = st.get("rang_to")
        if last is not None and now > float(last):
            st["rang"] = st.get("rang", 0) + step(kernel, float(last), now)
        st["rang_to"] = now
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"sources": len(st["sources"]), "queued": len(st["queue"]), "delivered": st.get("delivered", 0),
            "rang": st.get("rang", 0), "stars": len(st.get("stars") or {}), "sheared": len(st.get("anchors") or {})}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="field", state=lambda: {"sources": {}, "queue": [], "next": 0, "delivered": 0},
                             season=season, summary=summary))
