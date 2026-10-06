"""
Xylarium progenitor: the progenitor's own chronicle - what the one who set the laws writes into the annals, under
their own name.

It is the steward's truth, not a people's knowledge: no people witnesses it, keeps it in any medium, tells it as
myth or forgets it (memory.py hears only what a people lived through). It is never pruned, and it travels with
the universe wherever it is saved or archived (tools/archive.py), dated in the universe's own time - the cycle, the
year and the galaxy's age - beside whatever the progenitor chooses to tie it to (a people, a world).
"""

from typing import Any, Dict, List, Optional


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "progenitor")


def write(kernel: Any, name: str, title: str, text: str, about: Optional[List[str]] = None,
          planet: Any = None) -> Dict[str, Any]:
    """Write an entry into the annals under `name`. `about`: the peoples it concerns (holders, e.g. 'civ:...')."""
    from xylarium.kernel import cosmos, history
    if not name or not title:
        raise ValueError("an entry needs the progenitor's name and a title")
    try:
        epoch = round(float(cosmos.deep_gyr(kernel)), 6) if cosmos.is_cosmic(kernel) else None
    except Exception:
        epoch = None
    entry = {"n": len(stats(kernel)["entries"]) + 1, "name": name, "title": title, "text": text or "",
             "about": list(about or []), "planet": getattr(planet, "id", None), "cycle": int(kernel.cycle_count),
             "year": round(kernel.cycle_count / 100.0, 2), "epoch_gyr": epoch}
    stats(kernel)["entries"].append(entry)
    history.event(kernel, "PROGENITOR", f"{name}: {title}", actors=[f"progenitor:{name}"] + list(about or []),
                  planet=planet, cause="written by the progenitor", text=text or "", data={"entry": entry["n"]})
    return entry


def entries(kernel: Any, name: Optional[str] = None) -> List[Dict[str, Any]]:
    return [e for e in stats(kernel)["entries"] if name is None or e["name"] == name]


def render(kernel: Any) -> str:
    """The progenitor's chronicle as a document, dated in turns of the galaxy (a progenitor has no world)."""
    from xylarium.kernel import history
    lines = ["# The Progenitor's Chronicle", ""]
    for e in stats(kernel)["entries"]:
        when = f"year {e['year']:,}" + (", " + history.tell(kernel, {"deep_gyr": e["epoch_gyr"]})
                                        if e.get("epoch_gyr") else "")
        lines += [f"## {e['n']}. {e['title']}", f"*{e['name']} — {when}*", ""]
        if e.get("about"):
            lines += ["Concerning: " + ", ".join(a.split(":", 1)[-1] for a in e["about"]), ""]
        if e.get("text"):
            lines += [e["text"], ""]
    return "\n".join(lines)


def summary(kernel: Any) -> Dict[str, Any]:
    es = stats(kernel)["entries"]
    return {"entries": len(es), "authors": sorted({e["name"] for e in es})}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="progenitor",
    state=lambda: {"entries": []},
    summary=summary,
))
