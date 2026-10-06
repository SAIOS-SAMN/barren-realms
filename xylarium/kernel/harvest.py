"""
Xylarium harvest: how each people captures energy - and what its way of doing it costs the worlds around it.

Three ways, one physics, as many designs as there are peoples:

  FIELDS   collectors on a world's surface, 1e-4 of an Earth's area each: its star's light x the field's area x the
           design's efficiency, halved by night and dimmed by an atmosphere. Clean; bounded by the world's light.
  TAPS     bores into a rocky world's core, each drawing a twentieth of its core-mantle heat flow (scaled by the
           world's mass and volcanism) through a heat engine. Cheap and local - but a core convects, and its dynamo
           runs, only while more heat crosses its boundary than its iron can conduct away unaided. That margin is
           the world's own: conduction's share grows as the core shrinks (~ m^-1/3) and falls as its heat rises, so
           an Earth-sized world can spare ~40% of its flow, a hot volcanic one more, and a Mars-sized one nothing -
           its dynamo is already dead. Divert more than the margin and the dynamo weakens; without its field the
           solar wind strips the air, and the world feeds fewer people every season. The harm is measured - the people the world can no
           longer feed - and alignment follows from it, as from any act (alignment.measure). Nothing forbids it.
  ARRAYS   collector modules in orbit at the star's inner edge (1e-5 of an Earth's area each, at up to fifty times
           Earth's light), beamed to their owners' worlds (energy.py). Costly, and only for a people with yards.
           Every module shades the worlds beyond it by its share of the sphere it sits on - negligible for a swarm,
           decisive for a shell: their light falls (physics.planet_flux), and with it their harvests and climates.

DESIGNS. No people is given a technology. Each builds from the elements it has found (chemistry.py): the most
refractory it knows for a collector or a hot exchanger (condensation temperature), the best conductor near copper's
group, the lightest working fluid for a heat engine (heat capacity ~ 1/A). Its efficiency is the base of the method x
the quality of those materials x what it has mastered of the process (knowledge.py). Peoples of one metabolism on
different worlds dig different crusts and build differently; a people's designs improve as it discovers more.
Councils build where the energy, valued at what it is worth to them (energy.value_short / value_surplus), repays the
works at their policy rate (decide.py) - the same rule as every other choice.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import HABITAT_COST, PRICE_LEVEL

KINDS = ("field", "tap", "array")
PROCESS = {"field": "solar_collectors", "tap": "core_taps", "array": "stellar_arrays"}
BASE_EFF = {"field": 0.15, "tap": 0.25, "array": 0.25}
COST = {"field": 0.5, "tap": 0.3, "array": 5.0}          # of a habitat's works
ROLES = {"field": (("collector", 2), ("conductor", 1)), "array": (("collector", 3), ("conductor", 2)),
         "tap": (("refractory", 3), ("medium", 2))}
ORE_PER = {"field": 2, "tap": 4, "array": 6}
FIELD_AREA = 1e-4                  # of an Earth's surface
ARRAY_MODULE_AREA = 1e-5           # of an Earth's surface
CORE_TAP_SHARE = 0.05              # of the core's heat flow a tap draws
AREA_RATIO = 1.8e-9                # (Earth's radius / 1 AU)^2: an Earth's area as a share of the 1 AU sphere
NOUN = {"field": "sunfields", "tap": "core bores", "array": "orbital array"}
MAKE = {"biotic": "grown", "mineral": "forged", "plasmic": "woven", "cryogenic": "frozen", "umbral": "shadowed"}


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "harvest")


def works(planet: Any) -> Dict[str, float]:
    """{kind: units installed, kind_eff: the sum of their efficiencies as built}."""
    return planet.society.setdefault("harvest", {"field": 0, "tap": 0, "field_eff": 0.0, "tap_eff": 0.0})


def crude(kernel: Any, kind: str, planet: Any) -> Dict[str, Any]:
    """What any industrial people can make with ore alone: iron mirrors, bored rock - a third of the method's yield."""
    from xylarium.kernel import biosphere, knowledge
    holder = knowledge.holder_of_planet(planet)
    m = knowledge.mastery(kernel, holder, PROCESS[kind])
    make = MAKE.get(biosphere.metabolism_of(kernel, planet), "built")
    return {"kind": kind, "eff": BASE_EFF[kind] * 0.35 * (0.5 + 0.5 * m), "inputs": {}, "ore": 2 * ORE_PER[kind],
            "name": f"crude {make} ore {NOUN[kind]}", "cost_mult": knowledge.cost_multiplier(kernel, holder, PROCESS[kind])}


# ---------------------------------------------------------------------- designs
def _quality(sym: str, role: str) -> Optional[float]:
    from xylarium.kernel import chemistry
    e = chemistry.TABLE.get(sym)
    if e is None:
        return None
    fam = e["family"]
    if role in ("collector", "refractory"):
        if fam not in ("metal", "exotic", "fissile") or e["tc"] < 300:
            return None
        return max(0.3, min(1.5, e["tc"] / 1310.0))
    if role == "conductor":
        if fam not in ("metal", "exotic") or e["tc"] < 300:
            return None
        return max(0.2, min(1.0, 1.0 - abs(e["lane"] - 11) / 12.0))
    if role == "medium":
        if fam not in ("ice", "noble", "volatile") and not (fam == "exotic" and e["tc"] < 200):
            return None
        return max(0.3, min(2.0, math.sqrt(18.0 / e["A"])))
    return None


def design(kernel: Any, holder: Optional[str], kind: str, planet: Any,
           stock: Optional[Dict[str, int]] = None) -> Optional[Dict[str, Any]]:
    """This people's way of building `kind`, from what it knows - or None if it knows no material for a part. With
    `stock`, from what it knows *and holds* (an engineer builds with what is in the yard)."""
    from xylarium.kernel import biosphere, chemistry, decide, knowledge
    known = chemistry.known(kernel, holder) if holder else []
    picks = []
    left = dict(stock) if stock is not None else None
    for role, n in ROLES[kind]:
        cands = [(q, sym) for sym in known if (q := _quality(sym, role)) is not None
                 and (left is None or left.get(sym, 0) >= n)]
        best = max(cands, default=None)
        if best is None:
            return None
        if left is not None:
            left[best[1]] -= n
        picks.append((role, best[1], best[0], n))
    quality = math.exp(sum(math.log(q) for _, _, q, _ in picks) / len(picks))
    m = knowledge.mastery(kernel, holder, PROCESS[kind])
    inputs: Dict[str, int] = {}
    for _, sym, _, n in picks:
        inputs[sym] = inputs.get(sym, 0) + n
    mind = decide.mind_of_planet(kernel, planet)
    temper = "patient" if mind["noise"] < 1.0 else "quick"
    make = MAKE.get(biosphere.metabolism_of(kernel, planet), "built")
    mats = list(dict.fromkeys(chemistry.TABLE[sym]["name"] for _, sym, _, _ in picks))
    name = f"{temper} {make} {'-'.join(mats)} {NOUN[kind]}"
    return {"kind": kind, "eff": BASE_EFF[kind] * quality * (0.5 + 0.5 * m), "inputs": inputs, "name": name,
            "cost_mult": knowledge.cost_multiplier(kernel, holder, PROCESS[kind])}


# ---------------------------------------------------------------------- generation
def core_flow(planet: Any) -> float:
    from xylarium.kernel import energy, geology
    return energy.EARTH_CORE_FLOW * geology.heat(planet) if geology.rocky(planet) else 0.0


def field_output(kernel: Any, planet: Any, eff: float) -> float:
    from xylarium.kernel import energy, geology, physics
    sec = kernel.sectors.get(planet.sector_id)
    fl = float(physics.planet_flux(sec, planet)) if sec is not None else 1.0
    day = 0.5 * (1.0 if geology.airless(planet) else 0.7)
    return fl * FIELD_AREA * energy.TERRA_INSOLATION * eff * day


def dynamo_margin(planet: Any, kernel: Any = None) -> float:
    """The share of a rocky world's core heat flow it can lose before its dynamo stalls: 1 - q_ad / q_cmb, its own
    core's (hydromagnetics.py, from interior.py)."""
    from xylarium.kernel import geology, hydromagnetics, ledger, worlds
    if not geology.rocky(planet):
        return 0.0
    k = kernel if kernel is not None else ledger.active_kernel()
    return hydromagnetics.margin(worlds.state_of_planet(k, planet)["world"])


def tap_output(planet: Any, eff: float) -> float:
    return CORE_TAP_SHARE * core_flow(planet) * eff


def generation(kernel: Any, planet: Any) -> Dict[str, float]:
    """EU this season from the world's own installations, each at the efficiency it was built with."""
    w = planet.society.get("harvest") or {}
    out: Dict[str, float] = {}
    if w.get("field"):
        out["field"] = field_output(kernel, planet, float(w.get("field_eff", w["field"] * BASE_EFF["field"])))
    if w.get("tap"):
        out["tap"] = tap_output(planet, float(w.get("tap_eff", w["tap"] * BASE_EFF["tap"])))
    return out


def module_output(kernel: Any, sector: Any, eff: float) -> float:
    """EU a season from one module at the star's inner edge."""
    from xylarium.kernel import energy, physics
    st = physics.star(sector)
    q_min = physics.orbit_limits(st)[0]
    return float(physics.flux(st, q_min)) * ARRAY_MODULE_AREA * energy.TERRA_INSOLATION * eff


def array_output(kernel: Any) -> Dict[Tuple[str, int], int]:
    """(owner people, star's sector) -> mEU its modules captured this season."""
    from xylarium.kernel import energy
    out: Dict[Tuple[str, int], int] = {}
    st = stats(kernel)
    effs = st.setdefault("array_eff", {})
    for sid, owners in st["arrays"].items():
        sec = kernel.sectors.get(int(sid))
        if sec is None:
            continue
        for people, modules in owners.items():
            if modules <= 0:
                continue
            eff = float(effs.get(sid, {}).get(people, modules * BASE_EFF["array"]))
            out[(people, int(sid))] = int(module_output(kernel, sec, eff) * energy.MILLI)
    return out


def _holder(planet: Any) -> Optional[str]:
    from xylarium.kernel import knowledge
    return knowledge.holder_of_planet(planet)


def _representatives(kernel: Any) -> Dict[str, Any]:
    from xylarium.kernel import sustenance
    reps: Dict[str, Any] = {}
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population > 0 and not getattr(p, "natives", None):
                k = sustenance.people_of(p)
                if k and (k not in reps or p.population > reps[k].population):
                    reps[k] = p
    return reps


# ---------------------------------------------------------------------- shading
def shade(sector_id: int) -> float:
    """The share of a star's light its arrays take from the worlds beyond them."""
    from xylarium.kernel import ledger
    k = ledger.active_kernel()
    if k is None or "harvest" not in getattr(k, "state", {}):
        return 0.0
    return float(stats(k)["shade"].get(str(sector_id), 0.0))


def _reshade(kernel: Any) -> None:
    from xylarium.kernel import physics
    st = stats(kernel)
    st["shade"] = {}
    for sid, owners in st["arrays"].items():
        sec = kernel.sectors.get(int(sid))
        if sec is None:
            continue
        q_min = physics.orbit_limits(physics.star(sec))[0]
        a = float(q_min * q_min)                                  # AU
        share = sum(owners.values()) * ARRAY_MODULE_AREA * AREA_RATIO / max(1e-9, a * a)
        if share > 0:
            st["shade"][sid] = min(0.999, share)


# ---------------------------------------------------------------------- building
def _value_per_eu(kernel: Any, planet: Any) -> float:
    from xylarium.kernel import energy
    s = planet.society.get("energy_sufficiency")
    short = s is not None and float(s) < 0.999
    return energy.value_short(planet) if short else energy.value_surplus(planet)


def _options(kernel: Any, planet: Any) -> List[Dict[str, Any]]:
    from xylarium.kernel import decide, geology, sustenance
    level = PRICE_LEVEL.get(planet.currency, 1.0)
    holder = _holder(planet)
    v = _value_per_eu(kernel, planet)
    if v <= 0:
        return []
    m = decide.mind_of_planet(kernel, planet)
    sec = kernel.sectors.get(planet.sector_id)
    out = []
    for kind in KINDS:
        if kind == "tap" and not geology.rocky(planet):
            continue
        if kind == "array" and (not sustenance.yards(planet) or sec is None or getattr(sec, "kind", "SYSTEM") != "SYSTEM"):
            continue
        d = design(kernel, holder, kind, planet, stock=planet.element_reserves) or crude(kernel, kind, planet)
        if (planet.ore_silo or 0) < d.get("ore", ORE_PER[kind]):
            continue                                     # not even the ore to build it
        gain = (field_output(kernel, planet, d["eff"]) if kind == "field" else
                tap_output(planet, d["eff"]) if kind == "tap" else module_output(kernel, sec, d["eff"]))
        cost = HABITAT_COST * level * COST[kind] * d["cost_mult"]
        if planet.treasury < cost:
            continue
        out.append(decide.option(f"build_{kind}", cost, decide.worth(kernel, gain * v, m, planet.currency),
                                 cash=cost, currency=planet.currency, kind=kind, design=d))
    return out


def build(kernel: Any, planet: Any, kind: str, d: Dict[str, Any], cost: float) -> str:
    from xylarium.kernel import matter, sustenance
    from xylarium.kernel.demography import _pay_contractor
    _pay_contractor(kernel, planet, int(cost))
    for sym, n in d["inputs"].items():
        planet.element_reserves[sym] -= n
        matter.sink("construction", sym, n)
    matter.consume(planet, "ore_silo", "ORE", d.get("ore", ORE_PER[kind]), "construction")
    st = stats(kernel)
    if kind == "array":
        sid = str(planet.sector_id)
        owners = st["arrays"].setdefault(sid, {})
        people = sustenance.people_of(planet)
        owners[people] = owners.get(people, 0) + 1
        effs = st.setdefault("array_eff", {}).setdefault(sid, {})
        effs[people] = effs.get(people, 0.0) + d["eff"]
        _reshade(kernel)
    else:
        w = works(planet)
        w[kind] = w.get(kind, 0) + 1
        w[f"{kind}_eff"] = float(w.get(f"{kind}_eff", 0.0)) + d["eff"]
    st["built"][kind] = st["built"].get(kind, 0) + 1
    designs = st["designs"]
    designs[d["name"]] = designs.get(d["name"], 0) + 1
    from xylarium.kernel import primordial
    primordial.first(kernel, f"first_{kind}", f"{planet.name}: {d['name']}")
    return f"[ENERGY] {planet.name} builds {d['name']}."


def _endow(kernel: Any) -> None:
    """A galaxy that began already industrial (the settled genesis, or a save from before energy was counted)
    had been running on something: each industrial world is credited the fields that met its need."""
    from xylarium.kernel import energy, primordial
    st = stats(kernel)
    if st.get("endowed") or primordial.is_primordial(kernel):
        st["endowed"] = True
        return
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population <= 0 or getattr(p, "natives", None) or energy.need_eu(p, kernel) <= 0:
                continue
            one = field_output(kernel, p, BASE_EFF["field"])
            if one <= 0:
                continue
            n = int(math.ceil(energy.need_eu(p, kernel) / one))
            w = works(p)
            if w.get("field", 0) < n:
                w["field_eff"] = float(w.get("field_eff", 0.0)) + (n - w.get("field", 0)) * BASE_EFF["field"]
                w["field"] = n
            st["legacy_fields"] += n
    st["endowed"] = True


# ---------------------------------------------------------------------- what taps do to a world
def _cores(kernel: Any) -> List[str]:
    from xylarium.kernel import alignment, biosphere, geology, sustenance
    logs = []
    st = stats(kernel)
    for s in kernel.sectors.values():
        for p in s.planets:
            taps = (p.society.get("harvest") or {}).get("tap", 0)
            soc = p.society
            if not taps and soc.get("dynamo", 1.0) >= 1.0:
                continue
            margin = dynamo_margin(p, kernel)
            if margin <= 0:
                continue                                     # no dynamo to stall: its core was quiet before anyone bored it
            stress = taps * CORE_TAP_SHARE
            d = float(soc.get("dynamo", 1.0))
            was = d
            if stress > margin:
                d = max(0.0, d - (stress - margin))
            else:
                d = min(1.0, d + 0.02)                       # convection recovers slowly once the bores ease
            soc["dynamo"] = round(d, 4)
            if was >= 0.5 > d:
                st["dynamo_stalls"] += 1
                logs.append(f"[ENERGY] {p.name}'s core falters: its magnetic field fails, and the stars' wind "
                            f"begins to take its air.")
            if d >= 0.5 or geology.airless(p) or soc.get("shield"):   # a shield stands the wind off (skies.py)
                continue
            k0 = biosphere.carrying_capacity(kernel, p) if p.population > 0 else 0
            a = float(soc.get("atmosphere", 1.0))
            from xylarium.kernel import imprint             # its people's taps strained the core that held it
            imprint.record(kernel, p, "core_stress", str(p.owner_id or ""), air_add=-round((0.5 - d) * 0.02, 9))
            st["atmosphere_lost"] += a - soc["atmosphere"]
            if p.population <= 0:
                continue
            lost = max(0, k0 - biosphere.carrying_capacity(kernel, p))
            if lost <= 0:
                continue
            st["people_unfed"] += lost
            owner = kernel.captains.get(p.owner_id) if p.owner_id else None
            if owner is not None:
                alignment.act(kernel, owner, "core_harvest", lives_lost=lost)
            else:
                sustenance.flow_civ(p, dark=lost, why="core harvest")
    return logs


# ---------------------------------------------------------------------- the season
def season(kernel: Any) -> List[str]:
    from xylarium.kernel import decide, demography
    _endow(kernel)
    logs = _cores(kernel)
    if (kernel.cycle_count // _quarter()) % 4:
        return logs
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population <= 0 or getattr(p, "natives", None) or p.citadel_level < 1:
                continue
            if not demography.self_governed(p, kernel) or not demography.governed(p):
                continue
            from xylarium.kernel import energy_path
            energy_path.weigh(kernel, p)                     # burn its stock this year, or go without
            opts = _options(kernel, p)
            pick = decide.choose(kernel, opts, decide.mind_of_planet(kernel, p), p.id, "harvest") if opts else None
            if pick is not None:
                logs.append(build(kernel, p, pick["kind"], pick["design"], pick["cost"]))
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    fields = taps = 0
    stalled = 0
    for s in kernel.sectors.values():
        for p in s.planets:
            w = p.society.get("harvest") or {}
            fields += w.get("field", 0)
            taps += w.get("tap", 0)
            stalled += 1 if float(p.society.get("dynamo", 1.0)) < 0.5 else 0
    top = sorted(st["designs"].items(), key=lambda kv: -kv[1])[:5]
    return {"fields": fields, "taps": taps,
            "array_modules": sum(sum(o.values()) for o in st["arrays"].values()),
            "array_stars": len(st["arrays"]), "max_shade": round(max(st["shade"].values(), default=0.0), 9),
            "built": dict(st["built"]), "designs": len(st["designs"]), "top_designs": top,
            "dynamos_stalled": stalled, "dynamo_stalls": st["dynamo_stalls"],
            "people_unfed": st["people_unfed"], "legacy_fields": st["legacy_fields"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="harvest",
    state=lambda: {"arrays": {}, "shade": {}, "built": {}, "designs": {}, "endowed": False, "legacy_fields": 0,
                   "dynamo_stalls": 0, "atmosphere_lost": 0.0, "people_unfed": 0},
    season=season,
    summary=summary,
))
