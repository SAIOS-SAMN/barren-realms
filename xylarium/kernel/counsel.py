"""
Xylarium counsel: the steward's mind - as able as the people it guides, and growing with it.

A steward does not see more than its people can think. Its counsel is the people's own cognition (laws.cognition at
its homeworld's warmth, steadied by its fluid intelligence and its self-knowledge: decide.py, introspect.py), and
what it can offer unlocks as the people climbs:

  foresight     always: its numbers against what its land carries, projected over its council's planning horizon
                (the logistic toward K, the saddle's reading: syntropy.py) - a short, blurred horizon for a young
                people, a long one for a deep mind.
  breadth       the superposition: it holds as many plans at once as the highest rung its people's minds have
                climbed (intellect.py) - the fork's two paths, each weighted by how likely its own mind is to judge
                it best (net worth against its judgement's noise), and the goals it could pursue, by how far each
                falls short of what it wants (introspect.py) - a distribution over futures that collapses only when
                the steward acts. A young people sees one plan; a deep one several, side by side.
  self-model    once the people knows itself (introspect.py: INTROSPECTION): its forecast of itself next year, and
                how far that forecast has proved better than the guess that nothing changes.
  other minds   once it knows itself and has met others: what each people it has met would choose at its own fork,
                read through that people's mind - modelling others follows modelling oneself.
  memory        its turnings, legends and meetings, from the ledger (history.py).

Nothing here acts. The steward chooses; the counsel only sees as far as the people can.
"""

import math
from typing import Any, Dict, List, Optional


def _peoples_worlds(kernel: Any, holder: str) -> List[Any]:
    from xylarium.kernel import knowledge
    return [p for s in kernel.sectors.values() for p in s.planets
            if p.population > 0 and knowledge.holder_of_planet(p) == holder]


def rungs(kernel: Any, holder: Optional[str]) -> int:
    """The highest rung its minds have climbed on any ladder (intellect.py), at least one: the plans it holds."""
    from xylarium.kernel import intellect
    if not holder or "intellect" not in kernel.state:
        return 1
    return max(1, int(max(intellect.gauge(kernel, holder).values() or [0])))


def foresight(kernel: Any, planet: Any) -> Dict[str, Any]:
    """Its numbers over the council's horizon: logistic toward what the land carries."""
    from xylarium.kernel import biosphere, decide, fertility
    m = decide.mind_of_planet(kernel, planet)
    years = decide.horizon(m) / 4.0
    k = max(1, biosphere.carrying_capacity(kernel, planet))
    n0 = max(1, planet.population)
    f = float(planet.society.get("fertility", 1.0) or 1.0)
    r = fertility.birth_share_quarter() * 4 * max(0.05, min(f, 2.0))
    n = k / (1 + (k / n0 - 1) * math.exp(-r * years))
    return {"years": round(years, 1), "population_now": planet.population, "carries": k,
            "population_then": int(n), "crowding_then": round(n / k, 3),
            "noise": round(m["noise"], 3)}


def breadth(kernel: Any, planet: Any, holder: str) -> List[Dict[str, Any]]:
    """The plans and sovereign ideation states it holds at once in non-collapsing superposition."""
    from fractions import Fraction
    from xylarium.config import NATAL_POLICIES, PLANETARY_SPACEFLIGHT_COST, PRICE_LEVEL, DAUGHTER_EMIGRANTS_MAX
    from xylarium.kernel import decide, demography, syntropy, physics, torsion
    m = decide.mind_of_planet(kernel, planet)
    level = PRICE_LEVEL.get(planet.currency, 1.0)
    room = syntropy.room_in_reach(kernel, planet)
    out_value = demography.value_of_room(kernel, planet, room, m)

    # Physical electrodynamic induction from stellar dynamo and planetary spin
    sec_id = getattr(planet, "sector_id", 1)
    b = physics.body(planet)
    sec = kernel.sectors.get(sec_id) if hasattr(kernel, "sectors") else None
    star_dict = physics.star(sec) if sec is not None else {"m": Fraction(1)}
    amp, phase, chir = torsion.eval_wavefront(kernel, sec_id)
    induction = physics.electrodynamic_induction(star_dict, b, amp)

    plans = [
        ("outward", "sail for the room in reach", out_value
         - math.ceil(room / DAUGHTER_EMIGRANTS_MAX) * PLANETARY_SPACEFLIGHT_COST * level if room else -1.0),
        ("enough", "hold your numbers within your world",
         decide.worth(kernel, (NATAL_POLICIES["ascetic"].get("productivity", 1.0) - 1.0) * planet.population
                      * demography._tax_per_head_quarter(planet), m, planet.currency) - (out_value if room else 0.0)),
    ]

    # Non-collapsing harmonic modes added to superposition directly from electrodynamic induction
    harmonic_shift = float(induction)
    if harmonic_shift != 0.0 or amp > 0.001:
        plans.append(("harmonic_resonance", f"align social works to {phase:.2f} rad toroidal pulse",
                      out_value * 0.5 + harmonic_shift * 1000.0))

    plans.sort(key=lambda x: (-x[2], x[0]))
    held = plans[:rungs(kernel, holder)]
    scale = max(abs(v) for _, _, v in held) or 1.0
    spread = max(1e-6, decide.JUDGEMENT_ERROR * m["noise"] * scale)
    weights = [math.exp((v - held[0][2]) / spread) for _, _, v in held]
    total = sum(weights)
    out = [{"plan": k, "what": t, "net": round(v, 1), "chance": round(w / total, 3),
            "holonomy_phase": f"{phase + harmonic_shift:.3f}"}
           for (k, t, v), w in zip(held, weights)]

    # and where to turn its inquiry: the goals it holds, by how far each falls short of what it wants (introspect)
    from xylarium.kernel import introspect
    rec = introspect.stats(kernel)["peoples"].get(holder) or {}
    g, w = rec.get("gauges") or {}, rec.get("aspirations") or {}
    gaps = sorted(((w.get(x, 1.0) * (1.0 - g[x]), x) for x in g), reverse=True)[:max(0, rungs(kernel, holder) - 1)]
    want = sum(v for v, _ in gaps) or 1.0
    out += [{"plan": f"goal:{x}", "what": f"pursue {x} (inquiry: {introspect.LEVERS[x][1] or introspect.LEVERS[x][0]})",
             "net": None, "chance": round(v / want, 3)} for v, x in gaps]
    return out


def self_model(kernel: Any, holder: str) -> Optional[Dict[str, Any]]:
    from xylarium.kernel import introspect
    if not introspect.introspective(kernel, holder):
        return None
    rec = introspect.stats(kernel)["peoples"].get(holder) or {}
    return {"skill": round(float(rec.get("skill", 0.0)), 3),
            "next_year": {k: round(v, 3) for k, v in (rec.get("forecast") or {}).items()}}


def other_minds(kernel: Any, holder: str) -> Optional[List[Dict[str, Any]]]:
    """What each people it has met would choose at its fork, read through that people's own mind."""
    from xylarium.kernel import contact, introspect, knowledge, syntropy
    if not introspect.introspective(kernel, holder):
        return None
    fam = contact.stats(kernel)["familiarity"]
    out = []
    seen = set()
    for s in kernel.sectors.values():
        for p in s.planets:
            h = knowledge.holder_of_planet(p)
            if not h or h == holder or h in seen or p.population <= 0 or contact._key(holder, h) not in fam:
                continue
            seen.add(h)
            ws = _peoples_worlds(kernel, h)
            capital = max(ws, key=lambda w: (w.population, w.id))
            guess = syntropy.fork(kernel, capital, record=False)        # its own mind's choice, as it would make it
            out.append({"people": h.split(":", 1)[-1], "would": guess,
                        "understood": round(contact.intelligibility(kernel, holder, h), 3),
                        "syntropy": syntropy.reading(kernel, h).get("slope")})
    return out


def memory(kernel: Any, holder: str, n: int = 8) -> List[str]:
    from xylarium.kernel import history
    keep = ("TURNING", "INTROSPECTION", "CONTACT", "EMERGENCE", "FORECAST", "EXODUS", "UPLIFT", "SIGNAL",
            "EPITAPH", "EPIDEMIC")
    return [f"y{e['year']:.0f} {e['title']}" for e in history.of_people(kernel, holder) if e["kind"] in keep][-n:]


def counsel(kernel: Any, planet: Any) -> Dict[str, Any]:
    from xylarium.kernel import knowledge, syntropy
    holder = knowledge.holder_of_planet(planet)
    from xylarium.kernel import lifespan
    life = planet.society.get("life") or {}
    return {"rungs": rungs(kernel, holder), "foresight": foresight(kernel, planet),
            "life": {"expectancy_years": life.get("expectancy"), "thr": life.get("thr"),
                     "cohorts": lifespan.cohorts(planet), "dependency": round(
                         (lifespan.cohorts(planet)["youth"] + lifespan.cohorts(planet)["elder"])
                         / max(1e-6, lifespan.cohorts(planet)["prime"]), 3)},
            "syntropy": syntropy.reading(kernel, holder) or None, "plans": breadth(kernel, planet, holder),
            "self": self_model(kernel, holder), "others": other_minds(kernel, holder),
            "memory": memory(kernel, holder)}


def render(c: Dict[str, Any]) -> str:
    """The counsel as the steward reads it."""
    f = c["foresight"]
    lines = [f"Your people's minds have climbed to rung {c['rungs']}; they see {f['years']:.0f} years ahead "
             f"(judgement noise {f['noise']:.2f}).",
             f"Foresight: {f['population_now']:,} now, {f['population_then']:,} then, of the {f['carries']:,} "
             f"the land carries ({f['crowding_then']:.0%} full)."]
    sy = c.get("syntropy") or {}
    if sy:
        lines.append(f"Syntropy: {sy.get('slope', 0.0):+.4f} a year - "
                     + ("growing" if sy.get("slope", 0) > 0 else "declining" if sy.get("slope", 0) < 0 else "still"))
    lf = c.get("life") or {}
    if lf.get("expectancy_years") is not None:
        co = lf["cohorts"]
        lines.append(f"Life: {lf['expectancy_years']:.0f} years expected, health resilience {lf['thr']:.2f}; "
                     f"young {co['youth']:.0%}, prime {co['prime']:.0%}, old {co['elder']:.0%} "
                     f"(dependency {lf['dependency']:.2f}).")
    lines.append("Plans held at once:")
    for p in c["plans"]:
        lines.append(f"  {p['chance']:>5.0%}  {p['what']}" + (f" (net {p['net']:,.0f})" if p["net"] is not None else ""))
    if c.get("self"):
        lines.append(f"They know themselves (self-forecast skill {c['self']['skill']:.2f}).")
    else:
        lines.append("They do not yet know themselves: no self-model.")
    if c.get("others") is not None:
        for o in c["others"] or []:
            lines.append(f"  The {o['people']} would {('sail outward' if o['would'] == 'expand' else 'hold enough')}"
                         f" (understood {o['understood']:.0%}).")
    if c.get("memory"):
        lines.append("They remember: " + "; ".join(c["memory"]))
    return "\n".join(lines)
