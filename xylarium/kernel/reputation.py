"""
Xylarium reputation: how peoples read each other - their knowledge of each other, not the steward's truth.

A people's alignment is the truth of its whole history (alignment.py), and only the steward reads it. Every other
people keeps its own record of it, in the same lives-flows and faded by its own memory (memory.character_keep):

  told        at first contact a people hears what the other tells of itself (its doctrine, alignment.told_*), as
              far as it understands it (contact.intelligibility) - a story, kept as any record is kept
  witnessed   each season it sees as much of the other's deeds - what it makes and keeps, what its few take, the
              lives it takes and spares - as it knows the other (contact familiarity)
  suffered    what is done to a people it knows in full: the lives taken from it or given to it (`witness`)

Its reading of the other is that record's (light - dark) / (light + dark): a people that tells itself Light while
taking is believed until it is watched, and remembered by those it took from. Trust follows the reading
(`trust`): what a pact or a protection is worth to a people is what it expects the other to do, and it expects
what it has seen - so a people read as greedy finds fewer to stand beside it (relations.py).
"""

from typing import Any, Dict, List, Optional


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "reputation")


def _rec(kernel: Any, observer: str, subject: str) -> List[float]:
    return stats(kernel)["of"].setdefault(observer, {}).setdefault(subject, [0.0, 0.0])


def witness(kernel: Any, observer: Optional[str], subject: Optional[str], light: float = 0.0,
            dark: float = 0.0) -> None:
    """`observer` has had `light` lives given to it, or `dark` lives taken from it, by `subject`: it keeps it all."""
    if kernel is None or not observer or not subject or observer == subject:
        return
    r = _rec(kernel, observer, subject)
    r[0] += max(0.0, float(light))
    r[1] += max(0.0, float(dark))


def read(kernel: Any, observer: Optional[str], subject: Optional[str]) -> Optional[float]:
    """How `observer` reads `subject`, -1 .. +1; None if it has no record of it at all."""
    if not observer or not subject:
        return None
    r = stats(kernel)["of"].get(observer, {}).get(subject)
    if not r or r[0] + r[1] <= 0:
        return None
    return (r[0] - r[1]) / (r[0] + r[1])


def trust(kernel: Any, observer: Optional[str], subject: Optional[str]) -> float:
    """The share of its word `observer` expects `subject` to keep, 0 .. 1: half, for a stranger it has no record of;
    all of it, for one it has seen only give; none, for one it has seen only take."""
    r = read(kernel, observer, subject)
    return 0.5 if r is None else (1.0 + r) / 2.0


def _civ(worlds: List[Any]) -> Any:
    home = max(worlds, key=lambda p: (p.population, p.id))
    return getattr(home, "civilization", None), home


def season(kernel: Any) -> List[str]:
    """What each people has heard, seen and forgotten of the others this season."""
    from xylarium.kernel import contact, fertility, memory, syntropy
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    st = stats(kernel)
    by = syntropy._peoples(kernel)
    if not by:
        return []
    met = contact.contacts(kernel, by)
    fam = contact.stats(kernel)["familiarity"]
    years = FISCAL_QUARTER_CYCLES / 100.0
    homes = {h: _civ(ws) for h, ws in by.items()}
    # what each has forgotten
    for observer, recs in st["of"].items():
        if observer not in homes:
            continue
        civ, home = homes[observer]
        gen = fertility.generation_of(kernel, home)
        f = memory.character_keep(kernel, observer, home) ** (years / max(1.0, gen))
        for r in recs.values():
            r[0] *= f
            r[1] *= f
    # what each has seen of the others' deeds since last season, and what it was told on meeting them
    seen = st["seen"]
    for subject, (civ, home) in homes.items():
        if civ is None:
            continue
        light, dark = float(getattr(civ, "light", 0.0) or 0.0), float(getattr(civ, "dark", 0.0) or 0.0)
        last = seen.get(subject)
        seen[subject] = [light, dark]
        dl, dd = (max(0.0, light - last[0]), max(0.0, dark - last[1])) if last else (0.0, 0.0)
        for observer in by:
            if observer == subject or subject not in met.get(observer, {}):
                continue
            known = float(fam.get(contact._key(observer, subject), 0.0))
            r = st["of"].setdefault(observer, {}).get(subject)
            if r is None:                                   # first meeting: its story, as far as it is understood
                understood = contact.intelligibility(kernel, observer, subject, by)
                r = st["of"][observer][subject] = [
                    understood * float(getattr(civ, "told_light", 0.0) or 0.0),
                    understood * float(getattr(civ, "told_dark", 0.0) or 0.0)]
            r[0] += known * dl
            r[1] += known * dd
    return []


def summary(kernel: Any) -> Dict[str, Any]:
    """How far the peoples' readings of each other stand from the truth (the steward's view)."""
    from xylarium.kernel import alignment, syntropy
    by = syntropy._peoples(kernel)
    errs = []
    for observer, recs in stats(kernel)["of"].items():
        for subject in recs:
            ws = by.get(subject)
            seen = read(kernel, observer, subject)
            if ws and seen is not None:
                civ, _ = _civ(ws)
                if civ is not None:
                    errs.append(seen - alignment.character(civ))
    n = max(1, len(errs))
    return {"readings": len(errs), "mean_flattery": round(sum(errs) / n, 4),
            "mean_error": round(sum(abs(e) for e in errs) / n, 4)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="reputation",
    state=lambda: {"of": {}, "seen": {}},
    season=season,
    summary=summary,
))
