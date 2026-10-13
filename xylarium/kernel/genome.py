"""
Xylarium genome: what a people inherits, how it drifts, what its world selects, and when it becomes another people.

Every peopled world carries a genome - a deme's mean - as coordinates on five heritable axes, each a log-offset
from its people's founding form:

    light        the light its biology is tuned to (its optimum, x e^light)
    tolerance    how wide that tuning is: a curve widened by tau = e^tolerance loses peak height by 1/sqrt(tau)
                 (the generalist-specialist trade-off at constant area)
    chemistry    how far it has adapted to its world's surface: the gap to a perfect fit closes as e^-chemistry
                 (1 - (1 - fit) e^-c) - a people can become able to live where its ancestors could not
    birth        its natural increase (x e^birth)
    temperature  its minds' substrate temperature (x e^temperature: deeper and slower, or quicker and noisier)
    aptitude     how well it keeps what it learns (crystals forgotten x e^-aptitude)

Each quarter, a generation's share of evolution happens on each world:

    selection    Lande's equation: the change per generation is the additive variance times the gradient of log
                 fitness, and fitness is read from the world's own physics - how well its light fits (light,
                 tolerance) and how much room its people have (birth: r-selected where land is open, K-selected
                 near what it can carry)
    drift        a random walk whose step shrinks as 1/sqrt(people): a great people barely drifts, a small colony
                 wanders

Daughter worlds inherit their parent world's genome, then adapt to their own light. When a world's genome has moved
more than SPECIATION_SD additive deviations from its people's mean, it is no longer the same people: an indigenous
world becomes a new civilization (inheriting its parent's knowledge and crystals), a colony becomes a new strain.
That is ecological speciation - and the root of creativity (introspect.py): novelty that lives.

Engineering is a choice like any other: a people's council may move its genome toward what its world rewards - the
optimum is computed, not searched (the light it lives under, the tolerance its mismatch rewards) - at a cost that
falls with its mastery of the process, when the decision rule finds the people it would sustain worth more.
"""

import math
import random
import zlib
from dataclasses import dataclass
from fractions import Fraction as F
from typing import Any, Dict, List, Optional

AXES = ("light", "tolerance", "chemistry", "birth", "temperature", "aptitude")
VARIANCE = 0.01             # additive genetic variance per axis per generation (log scale; heritable variation)
SPECIATION_SD = 3.0         # a deme this many additive deviations from its people's mean is another people
EPS = 1e-3

# Fundamental constants for metabolic thermodynamics
K_BOLTZMANN_EV = 8.617333262e-5  # eV / K

METABOLIC_BASINS: Dict[str, Dict[str, Any]] = {
    "CARBON_AQUEOUS": {
        "ratios": {"C": 0.50, "N": 0.15, "P": 0.05, "O": 0.25, "H2O": 0.05},
        "delta_h_ev": 0.85,
        "delta_s_ev_k": 0.0022,
    },
    "IRON_SULFUR_LITHOTROPH": {
        "ratios": {"Fe": 0.40, "S": 0.35, "C": 0.15, "Ni": 0.05, "P": 0.05},
        "delta_h_ev": 1.45,
        "delta_s_ev_k": 0.0031,
    },
    "METHANOGENIC_CRYOPHILIC": {
        "ratios": {"C": 0.35, "H": 0.45, "N": 0.10, "Ni": 0.05, "Co": 0.05},
        "delta_h_ev": 0.55,
        "delta_s_ev_k": 0.0018,
    },
    "PLASMIC_HELIUM": {
        "ratios": {"He": 0.60, "H": 0.30, "Ne": 0.08, "e_": 0.02},
        "delta_h_ev": 3.20,
        "delta_s_ev_k": 0.0055,
    },
}


@dataclass
class MorphospaceCoordinate:
    elemental_ratios: Dict[str, float]
    activation_energy_ev: float
    catalytic_entropy: float
    basin_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "elemental_ratios": {k: round(v, 4) for k, v in self.elemental_ratios.items()},
            "activation_energy_ev": round(self.activation_energy_ev, 4),
            "catalytic_entropy": round(self.catalytic_entropy, 5),
            "basin_id": self.basin_id,
        }


def evaluate_waddington_drift(
    kernel: Any,
    planet: Any,
    coord: MorphospaceCoordinate,
) -> MorphospaceCoordinate:
    """Evaluate non-linear metabolic phase transitions driven by starlight and minerals.
    
    Models continuous biochemistry over a thermodynamic Waddington potential landscape
    V(x; Starlight, Elements). Populations drift toward thermodynamic attractors;
    when thermal fluctuations or stellar UV flux exceed catalytic free-energy barriers
    Delta G = Delta H - T * Delta S, demes cross saddle points into new metabolic basins,
    triggering organic speciation without arbitrary threshold checks.
    """
    # 1. Ambient planetary surface temperature
    t_surf = 288.15
    soc = getattr(planet, "society", {}) or {}
    if "surface_t" in soc:
        t_surf = max(10.0, float(soc["surface_t"]))
    elif kernel is not None and getattr(planet, "sector_id", None) in getattr(kernel, "sectors", {}):
        try:
            from xylarium.kernel import skies
            clim = skies.compute_climate_manifold(planet, kernel=kernel)
            t_surf = float(clim.get("t_mean_k", 288.15))
        except Exception:
            pass
            
    # Thermal energy kT in eV
    kt_ev = K_BOLTZMANN_EV * t_surf
    
    # Stellar UV flux factor
    uv_flux = 1.0
    try:
        from xylarium.kernel import physics
        if kernel is not None and getattr(planet, "sector_id", None) in getattr(kernel, "sectors", {}):
            sec = kernel.sectors[planet.sector_id]
            uv_flux = float(physics.planet_flux(sec, planet))
    except Exception:
        pass
    e_uv = 0.20 * max(0.01, min(5.0, uv_flux))
    e_available = kt_ev + e_uv
    
    # 2. Evaluate free-energy landscape across metabolic basins
    current_basin = coord.basin_id if coord.basin_id in METABOLIC_BASINS else "CARBON_AQUEOUS"
    best_basin = current_basin
    min_potential = float("inf")
    
    for basin_name, basin_spec in METABOLIC_BASINS.items():
        delta_h = basin_spec["delta_h_ev"]
        delta_s = basin_spec["delta_s_ev_k"]
        # Free energy barrier Delta G = Delta H - T * Delta S
        delta_g = delta_h - t_surf * delta_s
        
        # Distance from current ratios to basin target
        dist_sq = 0.0
        all_keys = set(coord.elemental_ratios) | set(basin_spec["ratios"])
        for k in all_keys:
            val_c = coord.elemental_ratios.get(k, 0.0)
            val_t = basin_spec["ratios"].get(k, 0.0)
            dist_sq += (val_c - val_t) ** 2
            
        # Effective potential V(x)
        pot = max(0.01, delta_g) * (1.0 + 3.0 * dist_sq)
        
        # If reachable via available energy fluctuation and deeper potential well:
        if delta_g <= e_available * 1.5 and pot < min_potential:
            min_potential = pot
            best_basin = basin_name
            
    # 3. Continuous Langevin drift toward attractor of best_basin
    target_ratios = METABOLIC_BASINS[best_basin]["ratios"]
    eta = 0.20  # relaxation rate
    
    # Deterministic pseudo-random seed from planet id and cycle
    p_id = getattr(planet, "id", 1)
    cycle = getattr(kernel, "cycle_count", 0) if kernel else 0
    seed_val = zlib.crc32(f"{p_id}:{cycle}:{best_basin}".encode()) & 0xFFFFFFFF
    rng = random.Random(seed_val)
    
    new_ratios: Dict[str, float] = {}
    combined_keys = set(coord.elemental_ratios) | set(target_ratios)
    for k in combined_keys:
        curr = coord.elemental_ratios.get(k, 0.0)
        targ = target_ratios.get(k, 0.0)
        drift = eta * (targ - curr)
        noise = (rng.random() - 0.5) * 0.02 * math.sqrt(kt_ev / 0.025)
        new_ratios[k] = max(0.001, curr + drift + noise)
        
    # Normalize ratios to sum to 1.0
    total_r = sum(new_ratios.values())
    if total_r > 0:
        new_ratios = {k: v / total_r for k, v in new_ratios.items()}
        
    spec = METABOLIC_BASINS[best_basin]
    return MorphospaceCoordinate(
        elemental_ratios=new_ratios,
        activation_energy_ev=spec["delta_h_ev"],
        catalytic_entropy=spec["delta_s_ev_k"],
        basin_id=best_basin,
    )



def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "genome")


def of(planet: Any) -> Dict[str, float]:
    g = planet.society.get("genome")
    if not g:
        g = planet.society["genome"] = {a: 0.0 for a in AXES}
    for a in AXES:
        g.setdefault(a, 0.0)
    return g


def value(planet: Any, axis: str) -> float:
    g = (getattr(planet, "society", None) or {}).get("genome")
    return float(g.get(axis, 0.0)) if g else 0.0


def inherit(parent: Any, daughter: Any) -> None:
    daughter.society["genome"] = dict(of(parent))
    if parent.society.get("lineage"):
        daughter.society["lineage"] = parent.society["lineage"]     # a strain's daughters are of its strain


def deme(kernel: Any, planet: Any) -> Optional[str]:
    """The interbreeding population a world belongs to: its people, or the strain of it the world became."""
    from xylarium.kernel import knowledge
    h = knowledge.holder_of_planet(planet)
    lineage = planet.society.get("lineage")
    return f"{h}|{lineage}" if (h and lineage) else h


# ---------------------------------------------------------------------- what the genome changes
def tuned_fit(base_fit: float, x: float, tolerance: float) -> float:
    """A light fit 4x/(1+x)^2, widened by tau = e^tolerance at constant area: fit^(1/tau) / sqrt(tau)."""
    tau = math.exp(tolerance)
    return (max(1e-12, base_fit) ** (1.0 / tau)) / math.sqrt(tau)


def optimum_factor(planet: Any) -> float:
    return math.exp(value(planet, "light"))


def birth_factor(planet: Any) -> float:
    return math.exp(value(planet, "birth"))


def temperature_factor(planet: Any) -> float:
    return math.exp(value(planet, "temperature"))


def aptitude_factor(planet: Any) -> float:
    return math.exp(-value(planet, "aptitude"))


def adapted_chemistry(base: float, planet: Any) -> float:
    return 1.0 - (1.0 - base) * math.exp(-value(planet, "chemistry"))


def fraction(x: float) -> F:
    return F(x).limit_denominator(10 ** 6)


# ---------------------------------------------------------------------- fitness, read from the world
def _flux_ratio(kernel: Any, planet: Any) -> Optional[float]:
    """The world's light over its people's founding optimum (x before the genome tunes it); None for plasmic
    peoples, whose light is their giant's mass."""
    from xylarium.kernel import biosphere, physics
    metab = biosphere.metabolism_of(kernel, planet)
    if metab == "plasmic":
        return None
    sec = kernel.sectors.get(planet.sector_id)
    if sec is None:
        return None
    fl = float(physics.planet_flux(sec, planet))
    civ = getattr(planet, "civilization", None)
    if civ is not None and getattr(civ, "light_optimum", None):
        opt = float(F(civ.light_optimum))
    else:
        from xylarium.config import LIGHT_OPTIMUM
        a, _, b = str(LIGHT_OPTIMUM.get(metab, "1/1")).partition("/")
        opt = float(a) / float(b or 1)
    return fl / opt if opt > 0 else None


def _surface(kernel: Any, planet: Any) -> float:
    """The founding surface fit of its people to this world (1 on the world they evolved on)."""
    from xylarium.kernel import biosphere
    civ = getattr(planet, "civilization", None)
    if civ is not None and getattr(civ, "home_type", None) == planet.planet_type:
        return 1.0
    return float(biosphere._surface_fit(biosphere.metabolism_of(kernel, planet), planet.planet_type))


def log_fitness(kernel: Any, planet: Any, g: Dict[str, float]) -> float:
    """The log of what the world gives a people of genome g: its light fit (tuned and widened) and its surface."""
    x0 = _flux_ratio(kernel, planet)
    lf = 0.0
    if x0 is not None:
        x = x0 / math.exp(g["light"])
        lf = math.log(tuned_fit(4 * x / ((1 + x) ** 2), x, g["tolerance"]))
    base = _surface(kernel, planet)
    chem = 1.0 - (1.0 - base) * math.exp(-g["chemistry"])
    return lf + math.log(max(1e-3, chem))


def gradient(kernel: Any, planet: Any) -> Dict[str, float]:
    """d ln w / d axis, read off the world (central differences on light and tolerance; r/K on birth)."""
    from xylarium.kernel import demography
    g = dict(of(planet))
    out = {a: 0.0 for a in AXES}
    for axis in ("light", "tolerance", "chemistry"):
        hi, lo = dict(g), dict(g)
        hi[axis] += EPS
        lo[axis] -= EPS
        out[axis] = (log_fitness(kernel, planet, hi) - log_fitness(kernel, planet, lo)) / (2 * EPS)
    k = max(1, demography.housing_cap(planet, kernel))
    crowding = min(2.0, planet.population / k)
    out["birth"] = 1.0 - crowding            # r-selected where land is open, K-selected near what it can carry
    return out


def optimum(kernel: Any, planet: Any) -> Dict[str, float]:
    """What the world rewards, in closed form: the light it lives under, and no widening when the light fits."""
    x0 = _flux_ratio(kernel, planet)
    g = dict(of(planet))
    if x0 is not None and x0 > 0:
        g["light"] = math.log(x0)
        g["tolerance"] = 0.0
    base = _surface(kernel, planet)
    if base < 0.9:                                      # adapt until the surface fits nine-tenths
        g["chemistry"] = max(g["chemistry"], math.log((1.0 - base) / 0.1))
    return g


# ---------------------------------------------------------------------- the quarter
def _rng(*parts: Any) -> random.Random:
    return random.Random(zlib.crc32(":".join(str(p) for p in parts).encode()))


def plasticity(kernel: Any, planet: Any) -> float:
    """How far its people retune themselves within a life (>= 1: the factor of its year's swing they meet without
    a change of heredity). A world whose year swings its light and wind - an eccentric orbit, ((1 + e) / (1 - e))^2
    from nearest to farthest - selects for retuning within a life; a sea under ice or in the deep, buffered from its
    sky, does not. Read from the world its people live on."""
    from xylarium.kernel import biosphere, worlds
    try:
        w = worlds.state_of_planet(kernel, planet)["world"]
        med = worlds.best(worlds.of_planet(kernel, planet), biosphere.metabolism_of(kernel, planet))
    except Exception:
        return 1.0
    if med is None or med.get("where") in ("under_ice", "deep"):
        return 1.0
    e = min(0.99, float(w.get("e") or 0.0))
    return ((1.0 + e) / (1.0 - e)) ** 2


def evolve(kernel: Any, planet: Any) -> None:
    from xylarium.kernel import fertility
    generations = (_quarter() / 100.0) / fertility.generation_years()
    g = of(planet)
    grad = gradient(kernel, planet)
    rng = _rng("genome", planet.id, kernel.cycle_count)
    n = max(1, planet.population)
    # a plastic people meets part of its world's mismatch by retuning within a life, so selection on its heredity
    # sees only what is left (the plastic response absorbs the rest): its line moves more slowly
    shield = plasticity(kernel, planet)
    for axis in AXES:
        sel = VARIANCE * grad.get(axis, 0.0) * generations / shield
        drift = rng.gauss(0.0, math.sqrt(VARIANCE * generations / n))
        g[axis] = round(g.get(axis, 0.0) + sel + drift, 6)


def distance(a: Dict[str, float], b: Dict[str, float]) -> float:
    """How far two genomes are, in additive deviations."""
    return math.sqrt(sum((a.get(x, 0.0) - b.get(x, 0.0)) ** 2 for x in AXES) / VARIANCE)


def _people_means(kernel: Any) -> Dict[str, Dict[str, Any]]:
    from xylarium.kernel import knowledge
    out: Dict[str, Dict[str, Any]] = {}
    for sec in kernel.sectors.values():
        for p in sec.planets:
            if p.population <= 0 or getattr(p, "natives", None):
                continue
            h = knowledge.holder_of_planet(p)
            if not h:
                continue
            rec = out.setdefault(deme(kernel, p), {"n": 0, "sum": {a: 0.0 for a in AXES}, "worlds": [], "holder": h})
            g = of(p)
            rec["n"] += p.population
            for a in AXES:
                rec["sum"][a] += g[a] * p.population
            rec["worlds"].append(p)
    for rec in out.values():
        rec["mean"] = {a: rec["sum"][a] / max(1, rec["n"]) for a in AXES}
    return out


def _inherit_ways(kernel: Any, parent: str, child: str) -> None:
    """A people that becomes another does not forget how to farm, write, compute, rewrite itself or fold space: its
    capabilities, the stages its history passed and its crossing are its parent's on the day it becomes itself."""
    from xylarium.kernel import technology
    if "technology" in kernel.state:
        if technology.stats(kernel)["of"].get(parent):
            technology.carry(kernel, parent, child)
    if "annals" in kernel.state:
        from xylarium.kernel import annals
        rec = annals.stats(kernel)["of"].get(parent)
        if rec and rec.get("passed"):
            mine = annals.stats(kernel)["of"].setdefault(child, {"advanced": 0.0, "passed": [], "dominion": 1,
                                                                 "reach": 0.0})
            mine["passed"] = list(dict.fromkeys(list(rec["passed"]) + list(mine.get("passed", []))))
    if "mastery" in kernel.state:
        from xylarium.kernel import mastery
        crossed = mastery.stats(kernel)["crossed"]
        if parent in crossed and child not in crossed:
            crossed[child] = kernel.cycle_count


def speciate(kernel: Any, planet: Any, parent_holder: str) -> Optional[str]:
    """A world gone far enough from its people becomes another people."""
    from xylarium.kernel import intellect, knowledge
    st = stats(kernel)
    civ = getattr(planet, "civilization", None)
    g = of(planet)
    if civ is not None and planet.owner_id is None:
        from xylarium.kernel.civilization import Civilization
        old = civ.name
        data = civ.to_dict()
        data["name"] = f"{old.split(' of ')[0]} of {planet.name}"
        # the new people is born adapted: its tuning becomes its founding form
        if getattr(civ, "light_optimum", None):
            data["light_optimum"] = str(fraction(float(F(civ.light_optimum)) * math.exp(g["light"])))
        new = Civilization.from_dict(data)
        planet.civilization = new
        planet.society.pop("lineage", None)
        planet.society["genome"] = {a: (0.0 if a == "light" else g[a]) for a in AXES}
        new_holder = knowledge.holder_of_planet(planet)
        knowledge.stocks(kernel, new_holder).update(dict(knowledge.stocks(kernel, parent_holder)))  # it remembers
        intellect.stats(kernel)["vocab"][new_holder] = list(intellect.vocabulary(kernel, parent_holder))
        from xylarium.kernel import memory
        memory.inherit(kernel, parent_holder, new_holder)                # and it takes its parent's past with it
        _inherit_ways(kernel, parent_holder, new_holder)                 # and what its people could already do
        who = new.name
    else:
        # a strain under its captain's rule: the same people, but a deme of its own from now on - it is measured
        # against its own kind (its daughters inherit the lineage), not the people it left
        strain = planet.society.get("strain", 0) + 1
        planet.society["strain"] = strain
        planet.society["lineage"] = f"{planet.id}.{strain}"
        who = f"strain {strain} of {planet.name}"
    st["speciations"] += 1
    if civ is not None and planet.owner_id is None:
        from xylarium.kernel import biosphere, descent
        descent.split(kernel, parent_holder, new_holder, biosphere.metabolism_of(kernel, planet))
    born = st.setdefault("born_of", {})
    born[parent_holder] = born.get(parent_holder, 0) + 1
    st["events"].append({"cycle": kernel.cycle_count, "world": planet.id, "from": parent_holder, "as": who})
    del st["events"][:-40]
    chron = getattr(kernel, "chronicle", None)
    if chron is not None:
        chron.record(kernel, "SPECIATION", planet.id, who, f"The Becoming of {who}",
                     f"Generation by generation the people of {planet.name} had grown into their world's light, until "
                     f"they were no longer what their ancestors had been. They are {who} now.",
                     sector_id=planet.sector_id, tags=["genome", "speciation", "creativity"])
    return f"[GENOME] {planet.name}'s people have become {who}."


# ---------------------------------------------------------------------- engineering
def proposal(kernel: Any, planet: Any) -> Optional[Dict[str, Any]]:
    """The edit a people could make this year: toward its world's optimum by as much as it has mastered editing,
    with what it is worth (the people its better fit would sustain) and what it costs."""
    from xylarium.config import HABITAT_COST, PRICE_LEVEL
    from xylarium.kernel import biosphere, decide, demography, knowledge
    holder = knowledge.holder_of_planet(planet)
    m = knowledge.mastery(kernel, holder, "genome_editing")
    if m <= 0:
        return None
    g = of(planet)
    target = optimum(kernel, planet)
    new = {a: g[a] + m * (target[a] - g[a]) for a in AXES}
    step = distance(new, g)
    if step < 0.5:                                    # less than half a deviation: nothing worth editing
        return None
    k_now = demography.housing_cap(planet, kernel)
    saved = dict(g)
    planet.society["genome"] = new
    k_new = biosphere.carrying_capacity(kernel, planet)
    planet.society["genome"] = saved
    mind = decide.mind_of_planet(kernel, planet)
    worth = demography.value_of_room(kernel, planet, k_new - k_now, mind)
    cost = HABITAT_COST * PRICE_LEVEL.get(planet.currency, 1.0) * step * knowledge.cost_multiplier(
        kernel, holder, "genome_editing")
    return {"genome": new, "worth": worth, "cost": cost, "mind": mind, "step": step, "gain": k_new - k_now}


def engineer(kernel: Any, planet: Any, plan: Dict[str, Any]) -> str:
    from xylarium.kernel.demography import _pay_contractor
    _pay_contractor(kernel, planet, int(plan["cost"]))
    planet.society["genome"] = {a: round(v, 6) for a, v in plan["genome"].items()}
    st = stats(kernel)
    st["edits"] += 1
    return (f"[GENOME] {planet.name} edits its people toward its world ({plan['step']:.1f} deviations): "
            f"room for ~{int(plan['gain']):,} more.")


def _consider_editing(kernel: Any, planet: Any) -> Optional[str]:
    from xylarium.kernel import decide
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    if owner is not None and not getattr(owner, "is_ai", False):
        return None                                   # players edit their own worlds by command
    plan = proposal(kernel, planet)
    if plan is None or planet.treasury < plan["cost"]:
        return None
    pick = decide.choose(kernel, [decide.option("edit_genome", plan["cost"], plan["worth"])], plan["mind"],
                         planet.id, "genome")
    return engineer(kernel, planet, plan) if pick is not None else None


def quarter(kernel: Any) -> List[str]:
    logs: List[str] = []
    from xylarium.kernel import fertility
    stats(kernel)["generations"] += (_quarter() / 100.0) / fertility.generation_years()
    peoples = _people_means(kernel)
    for holder, rec in peoples.items():
        for p in rec["worlds"]:
            evolve(kernel, p)
            if (kernel.cycle_count // _quarter()) % 4 == 0:          # councils weigh an edit once a year
                log = _consider_editing(kernel, p)
                if log:
                    logs.append(log)
    for rec in _people_means(kernel).values():
        if len(rec["worlds"]) < 2:
            continue                              # a people of one world is its own mean
        for p in rec["worlds"]:
            if distance(of(p), rec["mean"]) > SPECIATION_SD:
                log = speciate(kernel, p, rec["holder"])
                if log:
                    logs.append(log)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    spread = {a: 0.0 for a in AXES}
    worlds = [p for s in kernel.sectors.values() for p in s.planets if p.population > 0 and not p.natives]
    for a in AXES:
        vals = [value(p, a) for p in worlds]
        if vals:
            m = sum(vals) / len(vals)
            spread[a] = round(math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals)), 4)
    return {"speciations": st["speciations"], "edits": st.get("edits", 0), "spread": spread,
            "recent": st["events"][-3:], "generations": round(st["generations"], 2)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="genome",
    state=lambda: {"speciations": 0, "events": [], "generations": 0.0, "edits": 0},
    season=quarter,
    summary=summary,
))
