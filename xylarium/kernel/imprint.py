"""
Xylarium imprint: a world in play is what physics makes it at its age, plus what minds have done to it.

The universe is determined (creation.py, worlds.py): a world's air, seas, heat and light at any epoch are a function
of the seed, the laws and its age - evaluated, never stepped, never redrawn. What is not determined is what living
minds do to it, and that is kept apart: an ordered ledger on the world of every act that changed it - who, when,
and what it did - and nothing else. The world as it stands is its base at its age with the ledger folded over it:

  air        a share of its air taken (a strike, the wind through a failed field) or given back (volatiles
             imported, outgassed): scale, add, or set
  shield     a field raised between it and its star's wind
  type       its ground remade (a world broken apart)
  terraform  its ground being reworked toward a people's own (terraform.py)

So physics never has to be re-simulated to show agency, and agency never reaches into physics: the base is
recomputed only when the world's age moves (worlds.world_age), the ledger only when a mind acts. The folded result
is kept on the world (society["atmosphere"], ["shield"], ["terraform"], planet_type) for everything that reads it;
at(planet, cycle) refolds the ledger as it stood at any moment - the world's history of its makers.

Consecutive acts of one kind by one hand are kept as one entry spanning their years (a core's slow bleeding of air
is one line, not a thousand), its effect spread evenly over them when refolded mid-span.
"""

from typing import Any, Dict, List, Optional

PRISTINE = {"atmosphere": 1.0, "shield": None, "type": None, "terraform": None}


def ledger(planet: Any) -> List[Dict[str, Any]]:
    return planet.society.setdefault("imprints", [])


def _apply(state: Dict[str, Any], e: Dict[str, Any], share: float = 1.0) -> None:
    a = state["atmosphere"]
    if "air_set" in e:
        a = e["air_set"]
    if "air_scale" in e:
        a *= float(e["air_scale"]) ** share
    if "air_add" in e:
        a += float(e["air_add"]) * share
    state["atmosphere"] = max(0.0, min(1.0, a))
    if e.get("shield"):
        state["shield"] = e["c0"]
    if e.get("type"):
        state["type"] = e["type"]
    if "terraform" in e:
        state["terraform"] = dict(e["terraform"])


def at(planet: Any, cycle: Optional[int] = None) -> Dict[str, Any]:
    """What minds had done to the world by a cycle (now, if None)."""
    state = dict(PRISTINE)
    for e in ledger(planet):
        if cycle is not None and e["c0"] > cycle:
            break
        share = 1.0
        if cycle is not None and e["c"] > cycle:                 # mid-span: its effect so far
            share = (cycle - e["c0"] + 1) / max(1, e["c"] - e["c0"] + 1)
        _apply(state, e, share)
    return state


def record(kernel: Any, planet: Any, kind: str, by: Optional[str], **effect: Any) -> Dict[str, Any]:
    """A mind changed this world: write it in the world's ledger and fold it into the world as it stands."""
    led = ledger(planet)
    c = int(getattr(kernel, "cycle_count", 0))
    last = led[-1] if led else None
    mergeable = set(effect) <= {"air_add", "air_scale", "terraform"}
    if "terraform" in effect and last is not None and \
            (last.get("terraform") or {}).get("ground") != effect["terraform"].get("ground"):
        mergeable = False                                         # a new ground is a new work
    if last is not None and mergeable and last["kind"] == kind and last.get("by") == by:
        if "terraform" in effect:
            last["terraform"] = dict(effect["terraform"])
        if "air_add" in effect:
            last["air_add"] = round(float(last.get("air_add", 0.0)) + float(effect["air_add"]), 9)
        if "air_scale" in effect:
            last["air_scale"] = round(float(last.get("air_scale", 1.0)) * float(effect["air_scale"]), 9)
        last["c"] = c
    else:
        led.append({"kind": kind, "by": by, "c0": c, "c": c, **effect})
    _fold(planet, effect)
    if hasattr(kernel, "sectors"):
        from xylarium.kernel import lifeline
        lifeline.disturb(kernel, planet, kind)                # its life re-resolved from the world as it now stands
    return led[-1]


def _fold(planet: Any, effect: Dict[str, Any]) -> None:
    """Fold one act into the world as it stands (the same arithmetic as at(), applied once)."""
    soc = planet.society
    state = {"atmosphere": float(soc.get("atmosphere", 1.0)), "shield": soc.get("shield"), "type": None,
             "terraform": soc.get("terraform")}
    _apply(state, dict(effect, c0=0))
    soc["atmosphere"] = round(state["atmosphere"], 9)
    if effect.get("shield"):
        soc["shield"] = ledger(planet)[-1]["c0"]
    if effect.get("type"):
        planet.planet_type = effect["type"]
    if "terraform" in effect:
        soc["terraform"] = dict(effect["terraform"])
    soc.pop("_media", None)                                       # its media are re-read with its new air


def makers(planet: Any) -> Dict[str, int]:
    """Who has changed this world, and how many times."""
    out: Dict[str, int] = {}
    for e in ledger(planet):
        k = str(e.get("by") or "")
        out[k] = out.get(k, 0) + 1
    return out
