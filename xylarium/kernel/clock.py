"""
Xylarium clock: one universal time, and every orbit and spin as a function of it.

The universe keeps a single time - the cycle (100 to a standard year) - and everything that moves under the same
physics moves in lockstep with it. There are three kinds of motion, and only one of them needs stepping:

  CLOCKWORK    orbits, spins, seasons, insolation: closed-form functions of time (physics.orbital_phase is exact
               rational arithmetic). Nothing integrates them; any moment of any body is computed directly, so the
               sky at cycle 10^9 costs what the sky at cycle 1 does (ephemeris()).
  INTEGRATORS  what accumulates - food, births, taxes, energy, the seasons' books - steps at its natural cadence
               (the cycle, the fiscal quarter) in the engine.
  EVENTS       what minds decide happens when a mind gets to it: at its own cadence (scheduler.py), never on a
               timer imposed from outside.

ORBITAL VELOCITY is measured, not assumed: each body's phase rate is 1/its year (Kepler: P^2 = a^3/M), its
angular velocity 360 deg / year, its orbital speed 2 pi a / P, its spin rate the cycle's days over its day.
measure() reports them for every body so orbits can later be automated from the measurements alone.

VELOCITY of the universe is how many cycles pass per wall-second - a throttle on the runner, never on the physics:
the same seed gives the same universe at any velocity (scheduler.lock). 0 means as fast as the machine allows.
"""

import math
import time
from fractions import Fraction as F
from typing import Any, Dict, List, Optional

CYCLES_PER_YEAR = 100


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "clock")


def now(kernel: Any) -> int:
    return int(kernel.cycle_count)


def years(cycles: float) -> float:
    return cycles / CYCLES_PER_YEAR


# ---------------------------------------------------------------------- clockwork
def _sector(kernel: Any, planet: Any) -> Any:
    return kernel.sectors.get(planet.sector_id)


def year_of(kernel: Any, planet: Any) -> F:
    """The body's year, in cycles (exact)."""
    from xylarium.kernel import physics
    return physics.year_cycles(_sector(kernel, planet), planet)


def phase(kernel: Any, planet: Any, t: Optional[int] = None) -> F:
    """Exact fraction of its year the body has completed at time t (now if omitted)."""
    from xylarium.kernel import physics
    return physics.orbital_phase(_sector(kernel, planet), planet, now(kernel) if t is None else int(t))


def velocity_of(kernel: Any, planet: Any) -> Dict[str, float]:
    """The body's measured motion: orbits a cycle (1/year), degrees a cycle, AU a standard year, spins a cycle."""
    from xylarium.kernel import physics
    year = year_of(kernel, planet)
    b = physics.body(planet)
    q = b.get("q")
    a = float(q * q) if q is not None else float(getattr(planet, "orbital_radius", 1.0) or 1.0)   # a = q^2 AU
    day = float(b.get("day", 1) or 1)
    p_years = float(year) / CYCLES_PER_YEAR
    return {"year_cycles": float(year), "phase_rate": float(1 / year), "deg_per_cycle": 360.0 / float(year),
            "au_per_year": 2.0 * math.pi * a / max(1e-9, p_years),
            "spins_per_cycle": float(physics.DAYS_PER_CYCLE) / day}


def ephemeris(kernel: Any, t: int) -> List[Dict[str, Any]]:
    """Where every body is at time t - computed, not stepped (any t costs the same)."""
    from xylarium.kernel import physics
    out = []
    for sec in kernel.sectors.values():
        for p in sec.planets:
            cal = physics.local_calendar(sec, p, t)
            out.append({"planet": p.id, "phase": float(cal["phase"]), "year": cal["year"],
                        "season": cal["season"], "local_day": cal["local_day"],
                        "angle": physics.orbital_angle(sec, p, t)})
    return out


def measure(kernel: Any) -> Dict[str, Any]:
    """The galaxy's orbital clockwork, measured: the spread of years, angular and orbital speeds."""
    v = [velocity_of(kernel, p) for s in kernel.sectors.values() for p in s.planets]
    if not v:
        return {"bodies": 0}

    def spread(key: str) -> Dict[str, float]:
        xs = sorted(x[key] for x in v)
        return {"min": round(xs[0], 4), "median": round(xs[len(xs) // 2], 4), "max": round(xs[-1], 4)}
    return {"bodies": len(v), "year_cycles": spread("year_cycles"), "deg_per_cycle": spread("deg_per_cycle"),
            "au_per_year": spread("au_per_year"), "spins_per_cycle": spread("spins_per_cycle")}


# ---------------------------------------------------------------------- lazy integration
def elapsed(record: Dict[str, Any], key: str, t: int) -> int:
    """Cycles since `record[key]` was last evaluated, and stamp it now: a rate applied for the elapsed time
    replaces a rate applied every cycle (same total, one evaluation)."""
    last = record.get(key)
    record[key] = int(t)
    return 0 if last is None else max(0, int(t) - int(last))


# ---------------------------------------------------------------------- velocity
def velocity(kernel: Any) -> float:
    """Cycles per wall-second the runner is asked for (0: unthrottled)."""
    return float(stats(kernel).get("velocity", 0.0))


def set_velocity(kernel: Any, cycles_per_second: float) -> None:
    stats(kernel)["velocity"] = max(0.0, float(cycles_per_second))


class Pace:
    """Holds a runner to the universe's velocity: call step() after each cycle; it sleeps off any lead over the
    asked velocity, and reports the measured rate."""

    def __init__(self, kernel: Any) -> None:
        self.kernel = kernel
        self.t0, self.c0 = time.perf_counter(), now(kernel)

    def reset(self) -> None:
        self.t0, self.c0 = time.perf_counter(), now(self.kernel)

    def step(self) -> None:
        v = velocity(self.kernel)
        if v <= 0:
            return
        ahead = (now(self.kernel) - self.c0) / v - (time.perf_counter() - self.t0)
        if ahead > 0:
            time.sleep(ahead)

    def rate(self) -> Dict[str, float]:
        dt = max(1e-9, time.perf_counter() - self.t0)
        cps = (now(self.kernel) - self.c0) / dt
        return {"cycles_per_second": round(cps, 2), "years_per_minute": round(cps * 60 / CYCLES_PER_YEAR, 2)}


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"cycle": now(kernel), "year": now(kernel) // CYCLES_PER_YEAR, "velocity": st.get("velocity", 0.0),
            "orbits": measure(kernel)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="clock",
    state=lambda: {"velocity": 0.0},
    summary=summary,
))
