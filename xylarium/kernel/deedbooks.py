"""
Xylarium deed books: what a steward reads beside a petition - five readings of a people, each a PAIR (Concordance 6.3):
a syntropic ledger against an entropic one, from receipted deeds, read whole. No ratio, no cosine, no single score: a
book is IN DEFICIT where its entropic side exceeds its syntropic side, in its own unit. A book never gates; a steward
rules, citing the books.

  COHERENCE   per cohesion axis (compassion, bond, integrity, morality): deeds that practise the doctrine the people
              TELLS of itself (alignment.doctrine: a told Light practises constructive deeds, a told Dark destructive
              ones) against deeds that go against it - its sovereigns' conduct books (polity, mindcore), summed over
              every other it has dealt with. THE LOOP, over a steward's term: its doctrine moved toward its deeds
              (the gap between told and lived that closed) against doctrine held against them (the gap that
              remains); kinship's DENY choices are recorded beside it, on the held side.
  GRASP       per other order of intelligence b: the crystal group it shares with b's against the part of b's it
              lacks (|G_a cap G_b|, |G_b minus G_a|); G is the closure of its vocabulary (intellect) under
              composition. Time read both ways - the stack's reversal in its group - recorded beside, as a fact.
  AWARENESS   the same pair summed over the other communities on its own worlds (cohabit), each weighted by its share
              of their carrying capacity - two sums in one unit, never divided.
  EXPANSION   systems it held through a full steward term while self-fed and with its order not in deficit, against
              systems it reached and did not hold so.
  FUTILITY    its war deaths over goods it needed more of than its reach held, against its war deaths over goods its
              reach already held enough of (a war of want against a war of appetite).

The council's own strategy (strategy.py: hold, secure, grow, deepen, reach) is a separate reading, kept beside these.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional, Set, Tuple

AXES = ("compassion", "bond", "integrity", "morality")
STACK_LAYERS = 2                # the stack's symmetries read on two layers: enough to tell a cycle from a reversal


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "deedbooks")


def _pair(s: Any, e: Any) -> Dict[str, str]:
    return {"syntropic": str(Fraction(s)), "entropic": str(Fraction(e)),
            "deficit": bool(Fraction(e) > Fraction(s))}


def _home(kernel: Any, who: str) -> Optional[Any]:
    from xylarium.kernel import spheres
    return spheres._home(kernel, who)


# ---------------------------------------------------------------------- coherence
def _deeds(kernel: Any, who: str) -> Dict[str, Tuple[Fraction, Fraction]]:
    """Its sovereigns' conduct with every other, per axis: (constructive, destructive)."""
    from xylarium.kernel import polity
    out = {a: (Fraction(0), Fraction(0)) for a in AXES}
    if "polity" not in getattr(kernel, "state", {}):
        return out
    for rec in polity.of_people(kernel, who):
        for other, c in (rec.get("books") or {}).items():
            for a in AXES:
                if a in c:
                    s, e = out[a]
                    out[a] = (s + Fraction(c[a][0]), e + Fraction(c[a][1]))
    return out


def coherence(kernel: Any, who: str) -> Dict[str, Dict[str, str]]:
    from xylarium.kernel import alignment
    home = _home(kernel, who)
    civ = getattr(home, "civilization", None) if home is not None else None
    told_light = alignment.doctrine(civ) >= 0 if civ is not None else True
    out = {}
    for a, (s, e) in _deeds(kernel, who).items():
        out[a] = _pair(s, e) if told_light else _pair(e, s)
    return out


def loop(kernel: Any, who: str) -> Dict[str, Any]:
    """Over the steward's term since the last reading: the told-lived gap that closed against the gap that remains
    (alignment.doctrine against alignment.character), with kinship's denials beside it on the held side."""
    from xylarium.kernel import alignment, history
    home = _home(kernel, who)
    civ = getattr(home, "civilization", None) if home is not None else None
    if civ is None:
        return _pair(0, 0)
    gap = abs(Fraction(alignment.character(civ)) - Fraction(alignment.doctrine(civ)))
    rec = stats(kernel).setdefault("loop", {}).setdefault(who, {"gap": str(gap)})
    before = Fraction(rec["gap"])
    rec["gap"] = str(gap)
    denials = sum(1 for e in history.of_people(kernel, who)
                  if e.get("kind") == "KINSHIP" and (e.get("data") or {}).get("choice") == "deny")
    out = _pair(max(Fraction(0), before - gap), gap)
    out["denials"] = denials
    return out


# ---------------------------------------------------------------------- grasp and awareness
def group(vocab: List[Any]) -> Set[Tuple[Any, ...]]:
    """The closure of a vocabulary under composition, as its elements: its frame symmetries (crystal.chart), its stack
    symmetries (crystal.stack_chart on STACK_LAYERS layers), recolouring if held, and the fourth axis's operations."""
    from xylarium.kernel import crystal as C
    flat = [x for x in vocab if not isinstance(x, (list, tuple))]
    frames = list(C.chart(flat))
    stacks = list(C.stack_chart([x for x in flat if x in C.STACK_OPS], STACK_LAYERS))
    colours = [0, 1] if C.RECOLOR in flat else [0]
    hyper = [()] + [(h,) for h in sorted(x for x in flat if x in C.HYPER_OPS)]
    return {(f, s, c, h) for f in frames for s in stacks for c in colours for h in hyper}


def grasp(kernel: Any, who: str, others: List[str]) -> Dict[str, Any]:
    """Per other order b: (|G_a cap G_b| held, |G_b minus G_a| lacked); time read both ways beside."""
    from xylarium.kernel import crystal as C
    from xylarium.kernel import intellect
    mine = intellect.vocabulary(kernel, who)
    ga = group(mine)
    out: Dict[str, Any] = {"two_way_time": C.FLIP_STACK in mine, "of": {}}
    for b in others:
        if b == who:
            continue
        gb = group(intellect.vocabulary(kernel, b))
        out["of"][b] = _pair(len(ga & gb), len(gb - ga))
    return out


def awareness(kernel: Any, who: str) -> Dict[str, str]:
    """Over the other communities on its own worlds, weighted by their share of the worlds' carrying capacity: the
    group it shares with each, against the part of theirs it lacks - two sums in one unit."""
    from xylarium.kernel import cohabit, intellect, relations
    ga = group(intellect.vocabulary(kernel, who))
    held = lacked = Fraction(0)
    for w in relations._peoples(kernel).get(who) or []:
        comms = [c for c in cohabit.communities(w) if c.get("people") != who]
        caps = {id(c): cohabit.capacity(kernel, w, c.get("metab", "biotic")) for c in comms}
        total = sum(caps.values())
        if total <= 0:
            continue
        for c in comms:
            gk = group(list(c.get("vocab") or intellect.vocabulary(kernel, c.get("people") or "")))
            wk = Fraction(caps[id(c)], total)
            held += wk * len(ga & gk)
            lacked += wk * len(gk - ga)
    return _pair(held, lacked)


# ---------------------------------------------------------------------- expansion
def _self_fed(kernel: Any, who: str) -> bool:
    """The sign of its food's own pair: what its worlds harvest against what they need (sustenance's self-sufficiency,
    harvest over need, weighted by their numbers) - fed where harvest is not less than need."""
    from xylarium.kernel import relations
    worlds = relations._peoples(kernel).get(who) or []
    people = sum(int(w.population) for w in worlds)
    if people <= 0:
        return False
    fed = sum(float(w.society.get("self_sufficiency", 1.0)) * int(w.population) for w in worlds)
    return fed >= people


def _order_ok(kernel: Any, who: str) -> bool:
    from xylarium.kernel import alignment
    home = _home(kernel, who)
    civ = getattr(home, "civilization", None) if home is not None else None
    return civ is None or Fraction(alignment.character(civ)) >= 0


def expansion(kernel: Any, who: str) -> Dict[str, str]:
    """Systems held through the term just ended (the least it held over it) while self-fed and its order not in
    deficit, against the systems it reached and did not hold so. A people that has not crossed reaches nothing."""
    from xylarium.kernel import cosmos, settling
    b = settling.stats(kernel).get(who) if "annals" in getattr(kernel, "state", {}) else None
    if b is None:
        return _pair(0, 0)
    t = cosmos.deep_gyr(kernel)
    now = Fraction(float(settling.held(kernel, who, t)))
    reached = Fraction(float(settling.systems_in(b["r0"], settling.radius(b, t), b.get("band")) * b["share"]))
    rec = stats(kernel).setdefault("held", {}).setdefault(who, {"low": str(now)})
    low = min(Fraction(rec["low"]), now)
    rec["low"] = str(now)
    kept = low if (_self_fed(kernel, who) and _order_ok(kernel, who)) else Fraction(0)
    return _pair(kept, max(Fraction(0), reached - kept))


# ---------------------------------------------------------------------- futility
def futility(kernel: Any, who: str) -> Dict[str, Any]:
    """Its war deaths since the last reading, booked by its reach's want: over goods it needed more of than its worlds
    held (want) against over goods its worlds already held enough of (appetite). Need: its reserve basket x its
    numbers (backing.basket); held: its worlds' ground and stores."""
    from xylarium.kernel import backing, encircle, relations
    deaths = sum(int(n) for c, n in (encircle.deaths(kernel).get(who) or {}).items() if c.startswith("war")) \
        if "annals" in getattr(kernel, "state", {}) else 0
    rec = stats(kernel).setdefault("wars", {}).setdefault(who, {"seen": 0, "want": "0", "appetite": "0"})
    new = deaths - int(rec["seen"])
    rec["seen"] = deaths
    if new > 0:
        worlds = relations._peoples(kernel).get(who) or []
        bk = backing.basket(kernel, who)
        people = sum(int(w.population) for w in worlds)
        short = False
        if bk:
            for good, per in bk["units"].items():
                need = per * people
                have = sum(int(w.element_deposits.get(good, 0)) + int((w.element_reserves or {}).get(good, 0))
                           + (int(w.ore_silo or 0) if good == "ORE" else 0)
                           + (int(w.organics_silo or 0) if good == "ORGANICS" else 0) for w in worlds)
                short = short or need > have
        key = "want" if short else "appetite"
        rec[key] = str(Fraction(rec[key]) + new)
    return _pair(rec["want"], rec["appetite"])


# ---------------------------------------------------------------------- the reading
def read(kernel: Any, who: str, peers: List[str]) -> Dict[str, Any]:
    """All five books of a people, read whole - kept beside the steward's ruling, never gating it."""
    from xylarium.kernel import strategy
    out = {"coherence": coherence(kernel, who), "loop": loop(kernel, who),
           "grasp": grasp(kernel, who, peers), "awareness": awareness(kernel, who),
           "expansion": expansion(kernel, who), "futility": futility(kernel, who),
           "strategy": dict(strategy.of(kernel, who)).get("posture")}
    stats(kernel).setdefault("last", {})[who] = out
    return out


def summary(kernel: Any) -> Dict[str, Any]:
    return {"read": len(stats(kernel).get("last") or {})}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="deedbooks", state=lambda: {"loop": {}, "held": {}, "wars": {}, "last": {}},
                             summary=summary))
