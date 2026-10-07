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
               never builds yards (sustenance.yards reads it). And its rocket burns what its world gives it: split
               water for chemistry (water its system holds and it understands), any volatile it holds for the atom.
               A people beneath an ice shell or deep in a giant has no surface to launch from until it has the heat
               to breach its world (FISSION): its sky is its world's ceiling.
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

Past the metabolic bound - three ways a people stops waiting on its own generations (life.py: a mind's last rungs
were written a bit a generation by slow-breeding bodies; science lets it write faster than its bodies breed):

  GENETICS     biology turned on its own genome: it rewrites itself rather than waiting for selection - it lives
               longer still (lifespan) and passes its history's bridges faster (annals: GENETIC_GAIN).
  SYNTHESIS    chemistry built to order: living matter designed for a world rather than evolved on it - it reshapes
               worlds toward its own life faster (terraform.rate: SYNTHESIS_GAIN).
  ROBOTICS     bodies built, not bred: work and thought no longer bound to how fast its people grow - where its
               system holds the metals to build them (knowledge.effort: ROBOTICS_GAIN; annals).

  TRANSFER     a mind carried from one body to another: copying what it is - about a mind's blueprint of
               information (life.I_MIND bits) - faithfully enough that the copy is still the mind. Its difficulty is
               copying's own physics: a chemistry that copies faithfully keeps a mind legible and stable
               (mind.profile: legible), and a mind that already rewrites itself is nearer (plastic). With it a
               people wears bodies made for each world it goes to - the most robust way across the stars - and
               survives what would end a body. Whether the copy is the same mind is not physics: the people that
               finds it must decide, and a people whose creed forbids it gives it up (TRANSFER_FORBIDDEN).

  RELAYS       word kept moving without a ship sailing for it: posts on lanes that carry what each port has heard,
               a hop a jump-time (comms.py) - reached by any people that has its sky or has crossed, by any path.

  EMBODIMENT   life without a genome - minds held in fields, not in copied molecules (plasmic) - has no hands. Before
               it can build anything it must come into a vessel: a living body designed from outside, matter built
               to order, or a machine. It learns the terrestrial dimensions from nothing, through instruments it
               cannot yet build, so finding it rests on two kinds of knowledge at once (materials and energy) - and
               until it has, it raises no works (demography), no yards and never crosses (mastery.genome_ready).

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
GENETIC_GAIN = 1.0              # how much faster a people that rewrites its genome passes its history's bridges
SYNTHESIS_GAIN = 1.0            # what designed chemistry adds to how fast it reshapes a world
ROBOTICS_GAIN = 1.0             # what built bodies add to a people's work and thought
CAPS = ("radio", "orbit", "fission", "computation", "networks", "cyber", "medicine", "genetics", "synthesis",
        "robotics", "embodiment", "transfer", "relays")
RELIC_ONLY = ("foresight",)     # capabilities no people finds by itself: held only from what others left (relics.py)
NEEDS = {"radio": "information", "orbit": "energy", "fission": "energy", "computation": "information",
         "networks": "information", "cyber": "information", "medicine": "biology", "genetics": "biology",
         "synthesis": "materials", "robotics": "materials", "embodiment": "materials",
         "transfer": "information", "relays": "information"}
AFTER = {"networks": ("radio", "computation"), "cyber": ("networks",), "orbit": (), "fission": (),
         "radio": (), "computation": (), "medicine": (), "genetics": ("medicine", "computation"),
         "synthesis": ("genetics",), "robotics": ("computation",), "embodiment": (),
         "transfer": ("genetics", "synthesis"), "relays": ()}
GENOMELESS = ("plasmic",)       # chemistries whose minds are held in fields, not in a copied genome


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "technology")


def found(kernel: Any, holder: Optional[str], cap: str) -> bool:
    """Has this people found the capability (whether or not it may use it)?"""
    if not holder or kernel is None or "technology" not in getattr(kernel, "state", {}):
        return False
    return cap in stats(kernel)["of"].get(holder, {})


def has(kernel: Any, holder: Optional[str], cap: str) -> bool:
    """Can this people use the capability: found, and not interdicted by a steward (ascendance.stopped)."""
    if not found(kernel, holder, cap):
        return False
    from xylarium.kernel import ascendance
    return cap not in ascendance.stopped(kernel, holder)


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


BREEDING_MASTERY = 0.8          # how much of the wild-to-farmed gap a people must have closed for its breeders to read
                                # heredity's laws (classical genetics; declared)
PLASTIC_GENETICS = 0.5          # a mind this plastic rewrites itself within a life: its heredity is its own to study


def feasible(kernel: Any, holder: str, cap: str, home: Any) -> bool:
    """Does this people's own world let the capability work?"""
    from xylarium.kernel import biosphere, worlds
    held = stats(kernel)["of"].get(holder, {})
    if cap == "genetics":
        # two roads to its own heredity: the laboratory (medicine and machines that think), or the breeder's and the
        # self-rewriter's (medicine, and long breeding - or a mind that edits itself as it lives)
        from xylarium.kernel import mind, ways
        if "medicine" not in held:
            return False
        prof = mind.profile(kernel, home)
        return "computation" in held or prof["plastic"] >= PLASTIC_GENETICS or \
            ways.domestication(kernel, home) >= BREEDING_MASTERY
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
        return _can_launch(kernel, holder, home, "fission" in held)
    if cap == "fission":
        return home.element_deposits.get("U", 0) > 0 or any(
            p.element_deposits.get("U", 0) > 0 for p in _system(kernel, home))
    if cap == "computation":
        cold = (biosphere.body_temperature(home) or 300.0) < 90.0
        return cold or any(p.element_deposits.get("Si", 0) > 0 for p in [home] + _system(kernel, home))
    if cap == "cyber":
        return True
    if cap == "embodiment":
        return genomeless(kernel, home)
    if cap == "robotics":                                 # metal to build bodies from, in its own system
        return any(p.element_deposits.get("Fe", 0) > 0 for p in [home] + _system(kernel, home))
    if cap == "relays":                                   # a post must be put on a lane: it has reached its sky or
        from xylarium.kernel import mastery              # crossed beyond it - by whatever path (no order)
        return "orbit" in held or bool(mastery.crossed(kernel, holder))
    return True


def _can_launch(kernel: Any, holder: str, home: Any, fission: bool) -> bool:
    """Whether a people can lift itself off its world, by what its world gives it: a chemical rocket burns split water
    (the exhaust chemical_exhaust_kms reckons is water's), so it needs water its system holds and it understands; a
    nuclear-thermal one heats any volatile it holds (water, hydrogen, the nitrogen or carbon ices). A people whose
    chemistry runs under an ice shell or deep in a giant has no surface to launch from until it has the heat to
    breach its world (fission) - its sky is its world's ceiling. Then the rocket equation decides, as before."""
    from xylarium.kernel import biosphere, chemistry, worlds
    worlds_here = [home] + _system(kernel, home)
    held = set()
    for p in worlds_here:
        held |= {s for s, n in (p.element_deposits or {}).items() if n > 0}
        held |= {s for s, n in (p.element_reserves or {}).items() if n > 0}

    def has(s: str) -> bool:
        return s in held and chemistry.knows(kernel, holder, s)
    chemical = has("H2O")
    nuclear = fission and any(has(s) for s in ("H2O", "H", "cryogenite", "C"))
    if not chemical and not nuclear:
        return False
    try:
        med = worlds.best(worlds.of_planet(kernel, home), biosphere.metabolism_of(kernel, home))
    except Exception:
        med = None
    if med is not None and med.get("dark") and not fission:
        return False                                          # beneath ice or deep in a giant: no surface yet
    v = chemical_exhaust_kms() * (FISSION_GAIN if nuclear else 1.0)
    return orbit_ratio(home, v) <= STRUCTURE


def genomeless(kernel: Any, home: Any) -> bool:
    from xylarium.kernel import biosphere
    return biosphere.metabolism_of(kernel, home) in GENOMELESS


def embodied(kernel: Any, holder: Optional[str], home: Any) -> bool:
    """Has this people hands to build with? Every genomed people is born in a body; a genome-less one must make one."""
    return not genomeless(kernel, home) or has(kernel, holder, "embodiment")


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
        thought = 1.0 - math.exp(-sum(knowledge.effort(kernel, p) + knowledge.lived(kernel, p) for p in worlds) / 1000.0)
        rng = scheduler.rng(kernel, "technology", who, kernel.cycle_count)
        for cap in CAPS:
            if cap in held or not feasible(kernel, who, cap, home):
                continue
            chance = laws.mastery(stocks.get(NEEDS[cap], 0.0), KNOWLEDGE_UNIT) * thought
            from xylarium.kernel import mind
            prof = mind.profile(kernel, home)
            chance = min(1.0, chance * prof["affinity"].get(NEEDS[cap], 1.0))   # its kind of mind finds its own first
            if cap == "genetics":                    # a legible, self-rewriting heredity is easier to read
                chance = min(1.0, chance * (0.5 + prof["legible"]) * (1.0 + prof["plastic"]))
            if cap == "transfer":                    # a mind copies as faithfully as its chemistry keeps it
                chance = min(1.0, chance * prof["legible"] * (1.0 + prof["plastic"]))
            if who in st.setdefault("forbidden", {}).get(cap, {}):
                continue                             # its creed has forbidden it
            if cap == "embodiment":                          # the terrestrial dimensions, learned from nothing
                chance *= laws.mastery(stocks.get("energy", 0.0), KNOWLEDGE_UNIT)
            if rng.random() < chance:
                held[cap] = kernel.cycle_count
                st["found"] += 1
                name = who.split(":", 1)[-1]
                history.event(kernel, "CAPABILITY", f"The {name} find {cap}", actors=[who], planet=home,
                              cause=f"what they knew of {NEEDS[cap]}, on a world that allows it",
                              data={"capability": cap})
                logs.append(f"[TECHNOLOGY] The {name} find {cap}.")
                if cap == "transfer":
                    line = _weigh_transfer(kernel, who, worlds, home)
                    if line:
                        logs.append(line)
    return logs


def reconsider(kernel: Any, who: str, home: Any, creed: float) -> List[str]:
    """Its creed has fallen: what that creed forbade is weighed again, under the hold the new creed has."""
    from xylarium.kernel import relations
    forbidden = stats(kernel).get("forbidden", {})
    out = []
    for cap, peoples in list(forbidden.items()):
        if who not in peoples:
            continue
        peoples.pop(who)
        stats(kernel)["of"].setdefault(who, {})[cap] = kernel.cycle_count
        if cap == "transfer":
            line = _weigh_transfer(kernel, who, relations._peoples(kernel).get(who) or [home], home, creed)
            out.append(line or f"[TECHNOLOGY] The {who.split(':', 1)[-1]} take up what their old creed forbade.")
    return out


def _weigh_transfer(kernel: Any, who: str, worlds: List[Any], home: Any,
                    creed: Optional[float] = None) -> Optional[str]:
    """A people that can carry a mind into another body must decide whether the one carried is still the one who
    was: its council weighs wearing new bodies (what it would survive, and the worlds it could live on) against
    forbidding it (what its creed holds a mind to be)."""
    from xylarium.kernel import alignment, decide, history
    civ = getattr(home, "civilization", None)
    dogma = float(getattr(civ, "dogma", 0.0) or 0.0) if civ is not None else 0.0
    if creed is not None:
        dogma = creed                                     # weighed under the creed that now holds
    sc = alignment.scales(kernel)
    lives = sum(p.population for p in worlds) * sc["sol"] / max(1.0, sc["lives"])
    opts = [decide.option("embrace_transfer", 0.0, lives * (1.0 - dogma), aim="reach"),
            decide.option("forbid_transfer", 0.0, lives * dogma, aim="hold")]
    pick = decide.choose(kernel, opts, decide.mind_of_planet(kernel, home), who, "transfer")
    name = who.split(":", 1)[-1]
    if pick is not None and pick["name"] == "forbid_transfer":
        stats(kernel)["of"].get(who, {}).pop("transfer", None)
        stats(kernel).setdefault("forbidden", {}).setdefault("transfer", {})[who] = kernel.cycle_count
        history.event(kernel, "TRANSFER_FORBIDDEN", f"The {name} forbid the carrying of minds", actors=[who],
                      planet=home, cause="their creed holds that the one carried is not the one who was")
        return f"[TECHNOLOGY] The {name} forbid it: a mind carried is not the mind that was."
    history.event(kernel, "TRANSFER_EMBRACED", f"The {name} learn to wear new bodies", actors=[who], planet=home,
                  cause="they hold that a mind faithfully carried is still itself")
    return None


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
