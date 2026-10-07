"""
Xylarium descent: who came from whom, and who can still breed with whom.

Every people has a line. One that woke on its own world is a root - its own origin. One that split from another
(genome.speciate: a world gone far enough from its people) carries its parent's root, the generation it split and
the chemistry it inherited. Breeding is a question of that line, never of a label:

  OTHER CHEMISTRY   two peoples whose life runs in different media share no heredity at all: no child, and no
                    engineering bridges them - building something of both would be a new lineage, not a breeding.
  SEPARATE ROOTS    the same chemistry, woken apart: no child. Their bodies may still be read against each other
                    (the light each is tuned to, the warmth each keeps), and a people that edits genomes can build a
                    shared heredity across that gap - at the cost of editing that far (bridge).
  ONE ROOT          kin: they can breed, less as they drift apart. Each substitution one line makes can clash with
                    one the other made, so incompatibilities pile up as the square of the distance between them
                    (Orr's snowball): a hybrid's viability is exp(-(D / SPECIATION_SD)^2), D their genomes'
                    distance in additive deviations - kin at the speciation distance breed at e^-1, and less after.

A plastic people (one that retunes itself within a life: genome.plasticity) is shielded from part of its world's
selection, so its line drifts more slowly from its kin, and stays able to breed with them longer.
"""

import math
from typing import Any, Dict, Optional

from xylarium.kernel import genome


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "descent")


def _home(kernel: Any, holder: str) -> Optional[Any]:
    from xylarium.kernel import relations
    worlds = [w for w in (relations._peoples(kernel).get(holder) or []) if w.population > 0]
    return max(worlds, key=lambda w: (w.population, w.id)) if worlds else None


def line(kernel: Any, holder: str) -> Dict[str, Any]:
    """A people's line: its root, its parent, the generation it split, its chemistry. A people never recorded woke
    on its own world: its own root."""
    of = stats(kernel)["of"]
    rec = of.get(holder)
    if rec is None:
        from xylarium.kernel import biosphere
        home = _home(kernel, holder)
        rec = of[holder] = {"root": holder, "parent": None, "split": None,
                            "chemistry": biosphere.metabolism_of(kernel, home) if home is not None else None}
    return rec


def split(kernel: Any, parent: str, child: str, chemistry: Optional[str]) -> None:
    """A people became another (genome.speciate): the child keeps its parent's root and chemistry."""
    root = line(kernel, parent)["root"]
    stats(kernel)["of"][child] = {"root": root, "parent": parent,
                                 "split": round(float(genome.stats(kernel).get("generations", 0.0)), 3),
                                 "chemistry": chemistry or line(kernel, parent).get("chemistry")}


def _mean(kernel: Any, holder: str) -> Optional[Dict[str, float]]:
    rec = genome._people_means(kernel).get(holder)
    if rec is not None:
        return rec["mean"]
    home = _home(kernel, holder)
    return genome.of(home) if home is not None else None


def _body_distance(kernel: Any, a: str, b: str) -> Optional[float]:
    """How far apart two unrelated peoples' bodies are, in additive deviations: the light each is tuned to and the
    warmth each keeps, as log ratios (the traits their worlds selected: biosphere.home_flux, body_temperature)."""
    from xylarium.kernel import biosphere
    ha, hb = _home(kernel, a), _home(kernel, b)
    if ha is None or hb is None:
        return None
    gaps = []
    for read in (biosphere.home_flux, biosphere.body_temperature):
        x, y = read(ha), read(hb)
        if x and y and x > 0 and y > 0:
            gaps.append(math.log(x / y))
    if not gaps:
        return None
    return math.sqrt(sum(g * g for g in gaps) / genome.VARIANCE)


def kinship(kernel: Any, a: str, b: str) -> Dict[str, Any]:
    """What two peoples are to each other: "self", "kin" (one root: a hybrid's viability by their distance),
    "unrelated" (one chemistry, separate roots: no child; the distance an edit must close) or "alien" (another
    chemistry: nothing to bridge)."""
    if a == b:
        return {"relation": "self", "viability": 1.0, "distance": 0.0}
    la, lb = line(kernel, a), line(kernel, b)
    if la.get("chemistry") and lb.get("chemistry") and la["chemistry"] != lb["chemistry"]:
        return {"relation": "alien", "viability": 0.0, "distance": None}
    if la["root"] == lb["root"]:
        ga, gb = _mean(kernel, a), _mean(kernel, b)
        d = genome.distance(ga, gb) if ga is not None and gb is not None else 0.0
        return {"relation": "kin", "viability": math.exp(-(d / genome.SPECIATION_SD) ** 2), "distance": d}
    return {"relation": "unrelated", "viability": 0.0, "distance": _body_distance(kernel, a, b)}


def bridge(kernel: Any, by: str, a: str, b: str) -> Optional[Dict[str, float]]:
    """What it would take people `by` to give a and b a heredity they can share: editing across the distance between
    them, at its own cost of editing (genome.proposal's terms: the habitat-scale cost per deviation, as its mastery
    of genome editing prices it). None where nothing can bridge them (another chemistry, a distance unread) or `by`
    cannot edit genomes at all; kin who already breed need none."""
    from xylarium.config import HABITAT_COST
    from xylarium.kernel import knowledge
    rel = kinship(kernel, a, b)
    if rel["relation"] in ("self", "alien") or rel["distance"] is None:
        return None
    if knowledge.mastery(kernel, by, "genome_editing") <= 0:
        return None
    if rel["relation"] == "kin" and rel["viability"] >= math.exp(-1.0):
        return {"distance": rel["distance"], "cost": 0.0}
    gap = rel["distance"] if rel["relation"] == "unrelated" else rel["distance"] - genome.SPECIATION_SD
    return {"distance": rel["distance"],
            "cost": HABITAT_COST * max(0.0, gap) * knowledge.cost_multiplier(kernel, by, "genome_editing")}


def summary(kernel: Any) -> Dict[str, Any]:
    of = stats(kernel)["of"]
    roots = {r["root"] for r in of.values()}
    return {"lines": len(of), "roots": len(roots), "splits": sum(1 for r in of.values() if r.get("parent"))}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="descent", state=lambda: {"of": {}}, summary=summary))
