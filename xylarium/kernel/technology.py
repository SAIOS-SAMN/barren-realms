"""
Xylarium technology: capabilities a people finds in its own world - not a tree handed to every species alike.

A capability is found the way a crystal of thought is (intellect.py): each year a people's mastery of the knowledge
it rests on, times the thought it has to spare, is the chance it is found - but only where its world's physics lets
it work at all. The same knowledge on a heavier world, under ice, or in a colder body yields a different set of
works, or none:

  RADIO        sending and hearing through its sky. Light leaves a world whose people live under open air; a
               people beneath ice or deep in a giant hears only through its ocean (sound) until it reaches orbit.
               Its listening grows by the apertures it can build (signals.py hears it).
  ORBIT        reaching orbit at all. A chemical rocket's exhaust is set by the energy of the bonds it burns -
               v_e ~ sqrt(2 E_bond / m), a covalent bond over a water molecule's mass: ~6 km/s in our laws - and
               the rocket equation asks a mass ratio of e^(dv / v_e) for the dv to orbit (~0.8 v_esc with the
               losses of the climb). Past a ratio no structure carries (STRUCTURE: a ~4% dry share), a people
               cannot reach orbit by chemistry: a heavy world's people waits for the atom (FISSION's exhaust) - or
               never builds yards (sustenance.yards reads it).
  FISSION      the atom's energy, where its ground holds uranium or thorium: an exhaust ~2x chemistry's (nuclear
               thermal), and power.
  COMPUTATION  machines that think: on silicon or germanium where its ground holds them, or on superconductors
               where its bodies are cold enough to live among them; it multiplies the thought a people has (its
               effort: knowledge.py).
  NETWORKS     radio and computation together: its people understand each other and strangers faster (contact's
               familiarity) and hear their councils sooner (federation reach).
  CYBER        networks turned on others' networks: where a neighbour has networks too, its councils' judgement
               can be misled and its stores raided without a ship (strategy.py's model of a neighbour reads it).
  MEDICINE     biology turned on its own bodies: its people live longer (lifespan reads it).

Every capability found is an event in its people's ledger (CAPABILITY), dated: the shape of a civilization's history
is the order its own world let it find these in.
"""

import math
from typing import Any, Dict, List, Optional

from xylarium.kernel import interior

STRUCTURE = 25.0                # the largest mass ratio a rocket's structure carries (a ~4% dry share; declared)
CLIMB = 0.8                     # dv to orbit over escape speed, with the losses of the climb (gravity and drag)
FISSION_GAIN = 2.0              # nuclear-thermal exhaust over chemistry's (hydrogen heated by a reactor)
COMPUTE_GAIN = 1.0              # what thinking machines add to a people's thought (its effort x (1 + this))
NETWORK_GAIN = 1.0              # what networks add to how fast familiarity grows
MEDICINE_GAIN = 0.3             # the share medicine adds to a people's span of life
CAPS = ("radio", "orbit", "fission", "computation", "networks", "cyber", "medicine")
NEEDS = {"radio": "information", "orbit": "energy", "fission": "energy", "computation": "information",
         "networks": "information", "cyber": "information", "medicine": "biology"}
AFTER = {"networks": ("radio", "computation"), "cyber": ("networks",), "orbit": (), "fission": (),
         "radio": (), "computation": (), "medicine": ()}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "technology")


def has(kernel: Any, holder: Optional[str], cap: str) -> bool:
    if not holder or kernel is None or "technology" not in getattr(kernel, "state", {}):
        return False
    return cap in stats(kernel)["of"].get(holder, {})


def chemical_exhaust_kms(laws: Any = None) -> float:
    """A rocket's exhaust from burning its chemistry's bonds: sqrt(2 x a covalent bond / a water molecule's mass)."""
    from xylarium.kernel import worlds
    L = laws if laws is not None else worlds._laws(None)
    e = worlds.BOND_EV["covalent"] * L.chem * 1.602e-19
    m = 18.0 * 1.6726e-27 * L.proton
    return math.sqrt(2.0 * e / m) / 1000.0


def orbit_ratio(planet: Any, exhaust_kms: float) -> float:
    from xylarium.kernel import physics
    b = physics.body(planet)
    m = float(b.get("mass", 1)) * interior.M_EARTH_KG
    r = float(b.get("radius", 1)) * interior.R_EARTH_M
    v_esc = math.sqrt(2.0 * interior.G_SI * m / r) / 1000.0
    return math.exp(CLIMB * v_esc / max(1e-6, exhaust_kms))


def feasible(kernel: Any, holder: str, cap: str, home: Any) -> bool:
    """Does this people's own world let the capability work?"""
    from xylarium.kernel import biosphere, worlds
    held = stats(kernel)["of"].get(holder, {})
    if any(req not in held for req in AFTER.get(cap, ())):
        return False
    if cap == "radio":
        try:
            ms = worlds.of_planet(kernel, home)
            med = worlds.best(ms, biosphere.metabolism_of(kernel, home))
        except Exception:
            med = None
        return med is None or not med.get("dark")             # under ice or deep in a giant: no sky to send through
    if cap == "orbit":
        v = chemical_exhaust_kms() * (FISSION_GAIN if "fission" in held else 1.0)
        return orbit_ratio(home, v) <= STRUCTURE
    if cap == "fission":
        return home.element_deposits.get("U", 0) > 0 or any(
            p.element_deposits.get("U", 0) > 0 for p in _system(kernel, home))
    if cap == "computation":
        cold = (biosphere.body_temperature(home) or 300.0) < 90.0
        return cold or any(p.element_deposits.get("Si", 0) > 0 for p in [home] + _system(kernel, home))
    if cap == "cyber":
        return True
    return True


def _system(kernel: Any, home: Any) -> List[Any]:
    sec = kernel.sectors.get(home.sector_id)
    return [p for p in (sec.planets if sec else []) if p is not home]


def season(kernel: Any) -> List[str]:
    """Once a year each people may find what its knowledge and its world allow."""
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import history, knowledge, laws, scheduler, syntropy
    if (kernel.cycle_count // 25) % 4:
        return []
    st = stats(kernel)
    logs: List[str] = []
    for who, worlds in sorted(syntropy._peoples(kernel).items()):
        home = max(worlds, key=lambda p: p.population)
        held = st["of"].setdefault(who, {})
        stocks = knowledge.stocks(kernel, who)
        thought = 1.0 - math.exp(-sum(knowledge.effort(kernel, p) for p in worlds) / 1000.0)
        rng = scheduler.rng(kernel, "technology", who, kernel.cycle_count)
        for cap in CAPS:
            if cap in held or not feasible(kernel, who, cap, home):
                continue
            chance = laws.mastery(stocks.get(NEEDS[cap], 0.0), KNOWLEDGE_UNIT) * thought
            if rng.random() < chance:
                held[cap] = kernel.cycle_count
                st["found"] += 1
                name = who.split(":", 1)[-1]
                history.event(kernel, "CAPABILITY", f"The {name} find {cap}", actors=[who], planet=home,
                              cause=f"what they knew of {NEEDS[cap]}, on a world that allows it",
                              data={"capability": cap})
                logs.append(f"[TECHNOLOGY] The {name} find {cap}.")
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    count: Dict[str, int] = {}
    for caps in st["of"].values():
        for c in caps:
            count[c] = count.get(c, 0) + 1
    return {"found": st["found"], "by_capability": count}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="technology", state=lambda: {"of": {}, "found": 0}, season=season,
                             summary=summary))
