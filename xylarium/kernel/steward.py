"""
Xylarium steward: an intelligence that guides a people as one more voice in its collective mind - never its hand.

The universe is determined; a people is not. Its councils choose by their own minds (decide.choose): they weigh
the options they attend to, through their posture and their lessons, and draw their choice on their own stream of
chance. A steward - a player, or an intelligence set to the task - joins that mind. It does not choose, act, or
touch the world. It can do three things, and only through the people's own weighing:

  PERCEIVE   see what the people can see (counsel.py: foresight, the plans its rungs let it hold, its model of
             itself and of others once it knows itself, its memory) and how it stands (strategy's posture,
             learning's lessons) - no further than the people can think.
  GUIDE      speak for an aim (grow, deepen, secure, hold, reach), draw an option into the council's attention
             (consider: it is weighed even when the council's thought would have overlooked it), or caution against
             one. Guidance stands until the steward changes or withdraws it.
  EARN       how much the people heeds its steward is learned, like any lesson (learning.py): every time the council
             chooses as its steward urged, the year is credited to that voice by how the people fared against its
             own usual. A steward whose counsel has served is heard more; one whose counsel failed fades toward
             silence. A voice weighs, in a council attending to n options, 1 + heed / n times what it urges
             (at most e^2 / n more, and never less than nothing): one voice among the options its people holds in
             mind - no constant is chosen for it.

The people still chooses, still errs by its own noise, and may refuse every word. A steward is guidance, not
control: progenitors set laws; stewards counsel; peoples choose.
"""

from typing import Any, Dict, List, Optional

AIMS = ("grow", "deepen", "secure", "hold", "reach")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "steward")


def of(kernel: Any, holder: Optional[str]) -> Optional[Dict[str, Any]]:
    """The guidance standing for a people, if a steward guides it."""
    if not holder or kernel is None or "steward" not in getattr(kernel, "state", {}):
        return None
    return stats(kernel)["guides"].get(holder)


def attach(kernel: Any, holder: str, steward: str) -> Dict[str, Any]:
    """A steward joins a people's mind (one steward per people; a new one replaces the old voice)."""
    g = stats(kernel)["guides"].get(holder)
    if g is None or g["steward"] != steward:
        g = stats(kernel)["guides"][holder] = {"steward": steward, "since": kernel.cycle_count, "aim": None,
                                               "consider": [], "caution": [], "heeded": 0}
    return g


def detach(kernel: Any, holder: str) -> None:
    stats(kernel)["guides"].pop(holder, None)


def guide(kernel: Any, holder: str, steward: str, aim: Optional[str] = None,
          consider: Optional[List[str]] = None, caution: Optional[List[str]] = None) -> Dict[str, Any]:
    """Speak in a people's council: an aim to urge, options to bring to its attention, options to caution against.
    Anything left None stands as it was; an empty list withdraws."""
    if aim is not None and aim not in AIMS and aim != "":
        raise ValueError(f"an aim is one of {AIMS}")
    g = attach(kernel, holder, steward)
    if aim is not None:
        g["aim"] = aim or None
    if consider is not None:
        g["consider"] = list(consider)
    if caution is not None:
        g["caution"] = list(caution)
    return g


def share(kernel: Any, holder: Optional[str]) -> float:
    """How much of a steward's word a people takes up when it is one thing to adopt or not (a focus, a gauge's
    setting): heed / (1 + heed) - half, before it has learned anything of its steward."""
    h = heed(kernel, holder)
    return h / (1.0 + h)


def counsel_more(kernel: Any, holder: str, steward: str, names: List[str]) -> Dict[str, Any]:
    """Add options for the council to weigh (those already urged stay urged)."""
    g = attach(kernel, holder, steward)
    for n in names:
        if n not in g["consider"]:
            g["consider"].append(n)
        if n in g["caution"]:
            g["caution"].remove(n)
    return g


def voice(kernel: Any, holder: Optional[str]) -> str:
    return f"heed:{of(kernel, holder)['steward']}" if of(kernel, holder) else ""


def heed(kernel: Any, holder: Optional[str]) -> float:
    """How much the people has learned to heed its steward (1 before it has any lesson of it)."""
    from xylarium.kernel import learning
    g = of(kernel, holder)
    return learning.multiplier(kernel, holder, voice(kernel, holder)) if g else 0.0


def urges(g: Dict[str, Any], option: Dict[str, Any]) -> int:
    """+1 if the guidance urges this option, -1 if it cautions against it, 0 if silent."""
    if option["name"] in g["caution"]:
        return -1
    if option["name"] in g["consider"] or (g["aim"] and g["aim"] in (option.get("aim"), option["name"])):
        return 1
    return 0


def attend(kernel: Any, holder: Optional[str], options: List[Dict[str, Any]], room: int,
           ranked: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The options a council attends to, with its steward's: what it would weigh by its own thought (ranked[:room]),
    with any option its steward asks it to consider drawn in - in place of the least it would have weighed."""
    g = of(kernel, holder)
    kept = ranked[:room]
    if not g or not g["consider"]:
        return kept
    for o in options:
        if o["name"] in g["consider"] and o not in kept:
            kept = kept[:-1] + [o] if len(kept) >= room else kept + [o]
    return kept


def weight(kernel: Any, holder: Optional[str], option: Dict[str, Any], attending: int) -> float:
    """How much more (or less) the council weighs an option for its steward's word."""
    g = of(kernel, holder)
    if not g:
        return 1.0
    u = urges(g, option)
    if u == 0:
        return 1.0
    v = heed(kernel, holder) / max(1, attending)
    return 1.0 + v if u > 0 else 1.0 / (1.0 + v)


def chosen(kernel: Any, holder: Optional[str], option: Dict[str, Any]) -> None:
    """The council has chosen: if it chose as its steward urged, the year is credited to that voice too."""
    from xylarium.kernel import learning
    g = of(kernel, holder)
    if not g:
        return
    if urges(g, option) > 0:
        g["heeded"] += 1
        learning.record(kernel, holder, voice(kernel, holder))


def perceive(kernel: Any, holder: str) -> Dict[str, Any]:
    """What a steward of this people can see: no more than the people can think."""
    from xylarium.kernel import counsel, learning, strategy, syntropy
    worlds = syntropy._peoples(kernel).get(holder) or []
    out: Dict[str, Any] = {"people": holder, "worlds": len(worlds),
                           "population": sum(p.population for p in worlds)}
    if worlds:
        home = max(worlds, key=lambda p: p.population)
        out["counsel"] = counsel.counsel(kernel, home)
    st = strategy.of(kernel, holder)
    out["posture"] = st.get("posture")
    out["focus"] = st.get("focus")
    rec = learning.stats(kernel)["of"].get(holder) or {}
    out["lessons"] = {k: round(learning.multiplier(kernel, holder, k), 3) for k in (rec.get("opts") or {})}
    g = of(kernel, holder)
    if g:
        out["guidance"] = {k: g[k] for k in ("steward", "aim", "consider", "caution", "heeded")}
        out["heed"] = round(heed(kernel, holder), 3)
    return out


def summary(kernel: Any) -> Dict[str, Any]:
    gs = stats(kernel)["guides"]
    return {"guided": len(gs), "heeded": sum(g["heeded"] for g in gs.values())}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="steward", state=lambda: {"guides": {}}, summary=summary))
