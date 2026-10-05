"""
Xylarium press: the annals of the universe, made into books for others to read.

The architects' record is the history ledger (history.py: every event once, as data - when, where, who, what, why,
how much, and what earlier events it answers) and the captains' chronicle (chronicle.py: careers, losses, hauls,
discoveries). The press compiles them into volumes - one for each people, world or captain - and reads each
volume's genre from the shape of its own record, never assigning one:

  TRAGEDY          a rise brought down: its fortune peaks and falls, and the more of the fall its own choices made
                   (strife, the abandoned, the left to die, the foreseen and avoidable), the more it is a tragedy.
  COMEDY           the classical kind: a reversal that ends in restoration or union - from its lowest point it climbs,
                   and its last part holds a rescue, a pact, a meeting, a return.
  SCIENCE FACT     a record of discovery: firsts, capabilities proven, crossings, signals, the deep past read.
  SCIENCE FICTION  what a people told itself - its myths, its imaginings, its relics' voices - set against what the
                   record shows happened.

Every line of a volume cites the event it comes from (H-000123, CHR-00042), so a published story can always be
traced back to the universe's own record. Nothing here changes the universe: the press reads.
"""

import math
import os
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

RISE = {"FARMING", "STATEHOOD", "ERA", "ASCENT", "FTL_CROSSED", "DOMINION", "CAPABILITY", "FIRST", "EMERGENCE",
        "FEDERATION_FOUNDED", "PACT", "RESCUE", "RETURN", "KINSHIP", "UPLIFT", "SALVAGE", "SKY_SHIELD", "SKY_REPAIR",
        "CONTACT", "FIRST_SIGNAL", "WORLDLINES_MEET", "REDISCOVERY", "PROVEN", "TRIBUTARY", "EXODUS"}
FALL = {"FALL", "PERISHED", "EXTINCTION", "STRIFE", "ABANDONED", "EPIDEMIC", "REBELLION", "REVOLT", "SUBJUGATION",
        "WAR", "GALACTIC_WAR", "KIN_EATEN", "LIFE_ENDED", "SCHISM", "BREAKAWAY", "STAR_DEATH", "CONQUEST",
        "TRANSFER_FORBIDDEN"}
SELF_MADE = {"STRIFE", "ABANDONED", "REBELLION", "REVOLT", "KIN_EATEN", "SCHISM", "BREAKAWAY"}
SELF_WORDS = ("could have been carried", "left to die", "turn on themselves", "would rise", "foreseen", "abandon",
              "their own")
UNION = {"PACT", "FEDERATION_FOUNDED", "RESCUE", "RETURN", "KINSHIP", "CONTACT", "WORLDLINES_MEET", "UPLIFT"}
DISCOVERY = {"FIRST", "CAPABILITY", "PROVEN", "FTL_CROSSED", "INTROSPECTION", "FIRST_SIGNAL", "HURDLE", "PHILOSOPHY",
             "RECORDKEEPING", "FORECAST", "NULL_FLOW_PROBE", "CLUSTER_CHARTED", "REDISCOVERY", "RELIC_FOUND"}
SPECULATIVE = {"MYTH", "IMAGINATION", "ART", "DEEP_HISTORY", "FOLD_RANG", "FOLD_TORN", "CHILD_UNIVERSE",
               "TRANSFER_EMBRACED", "TRANSFER_FORBIDDEN", "EPITAPH", "RELIC_MIND_WAKES", "RELIC_MIND_CALLS",
               "RELIC_MIND_GUARDS", "RELIC_MIND_SILENT", "RELIC_MIND_EMBODIED"}
GENRES = ("tragedy", "comedy", "science fact", "science fiction")
MIN_EVENTS = 3                  # a volume needs a story: fewer events are a footnote in the galaxy's own volume


# ---------------------------------------------------------------------- sources
def from_kernel(kernel: Any) -> List[Dict[str, Any]]:
    """The events a running universe still holds (history's recent window) and its captains' chronicle."""
    from xylarium.kernel import history
    events = [dict(e) for e in history.stats(kernel)["recent"]] if "history" in getattr(kernel, "state", {}) else []
    chron = getattr(kernel, "chronicle", None)
    for c in (getattr(chron, "entries", None) or []):
        events.append({"id": c["id"], "cycle": c.get("cycle", 0), "year": round(c.get("cycle", 0) / 100.0, 2),
                       "kind": f"CHRONICLE_{c.get('kind', 'ENTRY')}".upper(), "title": c.get("title", ""),
                       "text": c.get("body", ""), "actors": [f"captain:{c['subject_id']}"] if c.get("subject_id")
                       else [], "subject": c.get("subject"), "sector": c.get("sector_id"), "age": c.get("stardate")})
    return sorted(events, key=lambda e: (e.get("cycle", 0), e["id"]))


def of_kernel(kernel: Any) -> List[Dict[str, Any]]:
    """Everything a running universe can give the press: its whole ledger if a runner gave it a file (history.sink),
    else the events it still holds - and, either way, its captains' chronicle."""
    from xylarium.kernel import history
    path = history._SINKS.get(kernel) if hasattr(history, "_SINKS") else None
    if path and os.path.exists(path):
        held = from_ledger(path)
        chron = [e for e in from_kernel(kernel) if str(e["id"]).startswith("CHR-")]
        return sorted(held + chron, key=lambda e: (e.get("cycle", 0), e["id"]))
    return from_kernel(kernel)


def from_ledger(path: str) -> List[Dict[str, Any]]:
    """A universe's whole ledger, as its runner wrote it (history.sink): one JSON event per line."""
    import json
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# ---------------------------------------------------------------------- volumes and their shapes
def _name(actor: str) -> str:
    return actor.split(":", 1)[-1]


def volumes(events: Iterable[Dict[str, Any]], by: str = "people") -> Dict[str, List[Dict[str, Any]]]:
    """Events grouped into volumes: by people (each actor's events; captains as their own), or by world."""
    out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in events:
        if by == "world":
            if e.get("planet_name"):
                out[e["planet_name"]].append(e)
            continue
        actors = e.get("actors") or []
        if not actors:
            out["The galaxy"].append(e)
        for a in actors:
            out[_name(a) if not str(a).startswith("captain:") else (e.get("subject") or _name(a))].append(e)
    return dict(out)


def _weight(e: Dict[str, Any]) -> float:
    return 1.0 + math.log10(1.0 + max(0.0, float(e.get("magnitude") or 0)))


def _self_made(e: Dict[str, Any]) -> bool:
    cause = (e.get("cause") or "").lower() + " " + (e.get("title") or "").lower()
    return e["kind"] in SELF_MADE or any(w in cause for w in SELF_WORDS)


def shape(evs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """A volume's fortune through its record (each rise up, each fall down, by how much was at stake) and how much
    of it is discovery and how much the telling."""
    f, curve = 0.0, []
    for e in evs:
        if e["kind"] in RISE:
            f += _weight(e)
        elif e["kind"] in FALL:
            f -= _weight(e)
        curve.append(f)
    if not curve:
        return {"curve": [], "peak": 0, "low": 0, "final": 0.0}
    peak = max(range(len(curve)), key=lambda i: (curve[i], -i))
    low = min(range(len(curve)), key=lambda i: (curve[i], -i))
    falls_after = [e for e in evs[peak + 1:] if e["kind"] in FALL]
    return {"curve": curve, "peak": peak, "low": low, "final": curve[-1],
            "range": max(curve) - min(min(curve), 0.0) or 1.0,
            "self_share": (sum(_weight(e) for e in falls_after if _self_made(e))
                           / max(1e-9, sum(_weight(e) for e in falls_after))) if falls_after else 0.0,
            "union_late": any(e["kind"] in UNION for e in evs[len(evs) * 2 // 3:]),
            "fell": any(e["kind"] in FALL for e in evs[:low + 1]),
            "discovery": sum(1 for e in evs if e["kind"] in DISCOVERY) / len(evs),
            "telling": sum(1 for e in evs if e["kind"] in SPECULATIVE) / len(evs)}


def genre(evs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The genre a record's shape makes it - and the other strands that run through it."""
    s = shape(evs)
    if not s["curve"]:
        return {"genre": "science fact", "strands": [], "scores": {}}
    c, rng = s["curve"], s["range"]
    descent = max(0.0, c[s["peak"]] - s["final"]) / rng if s["peak"] < len(c) - 1 else 0.0
    ascent = max(0.0, s["final"] - c[s["low"]]) / rng if s["low"] < len(c) - 1 else 0.0
    scores = {"tragedy": descent * (0.5 + 0.5 * s["self_share"]),
              # a comedy turns: its climb comes after a fall (a rise with no reversal is not one)
              "comedy": ascent * (1.0 if s["union_late"] else 0.5) * (1.0 if s.get("fell") else 0.3),
              "science fact": s["discovery"],
              "science fiction": s["telling"]}
    best = max(GENRES, key=lambda g: (scores[g], -GENRES.index(g)))
    strands = [g for g in GENRES if g != best and scores[g] >= 0.5 * scores[best] and scores[g] > 0]
    return {"genre": best, "strands": strands, "scores": {g: round(v, 3) for g, v in scores.items()}}


# ---------------------------------------------------------------------- the books
def _when(e: Dict[str, Any]) -> str:
    y = f"year {float(e.get('year', 0)):,.0f}"
    return y + (f", {e['deep_gyr']:.4f} Gyr" if isinstance(e.get("deep_gyr"), (int, float)) else "")


def logline(name: str, evs: List[Dict[str, Any]], g: Dict[str, Any]) -> str:
    s = shape(evs)
    if not evs:
        return f"{name}: no record."
    top = evs[s["peak"]]["title"] if s["curve"] else evs[0]["title"]
    end = evs[-1]["title"]
    span = f"{_when(evs[0])} to {_when(evs[-1])}"
    return f"{name}, {span}: at its height, {top.rstrip('.')}; at the last, {end.rstrip('.')}. A {g['genre']}."


def render(name: str, evs: List[Dict[str, Any]], all_events: Optional[List[Dict[str, Any]]] = None) -> str:
    """A volume as a book (Markdown): its genre, its logline, chapters by age, every line cited; for a telling, its
    myths set against what they remember."""
    g = genre(evs)
    out = [f"# {name}", "", f"*{g['genre'].title()}" + (f", with strands of {', '.join(g['strands'])}" if g["strands"]
                                                        else "") + ".*", "", logline(name, evs, g), ""]
    chapters: Dict[str, List[Dict[str, Any]]] = {}
    for e in evs:
        chapters.setdefault(str(e.get("age") or "Undated"), []).append(e)
    for age, ces in chapters.items():
        out += [f"## {age[:1].upper() + age[1:]}", ""]
        for run in _runs(ces):
            e = run[0]
            where = f" ({e['planet_name']})" if e.get("planet_name") else ""
            when = _when(e)
            line = f"- **{when[:1].upper() + when[1:]}{where}: {e['title']}.**"
            if len(run) > 1:
                others = [o for r in run[1:] for o in _others(r, name)]
                line += f" And {len(run) - 1} more like it" + (f": {', '.join(others)}." if others else ".")
            else:
                text = e.get("text") or ""
                if text and text != e["title"]:
                    line += f" {text}"
            if e.get("cause"):
                line += f" *({e['cause']})*"
            out.append(line + (f" [{e['id']}]" if len(run) == 1 else f" [{e['id']} .. {run[-1]['id']}]"))
        out.append("")
    myths = [e for e in evs if e["kind"] == "MYTH"]
    if myths:
        byid = {e["id"]: e for e in (all_events or evs)}
        out += ["## What they told, and what happened", ""]
        for m in myths:
            src = [byid[r] for r in m.get("refs", []) if r in byid and byid[r]["kind"] != "MYTH"]
            out.append(f"- They told, in {_when(m)}: {m.get('text') or m['title']} [{m['id']}]"
                       + (f" - the record: {src[0]['title']} [{src[0]['id']}]" if src else " - the record is silent."))
        out.append("")
    return "\n".join(out)


def _runs(evs: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Consecutive events of one kind, one cause, one year: told once, with the others it involved."""
    runs: List[List[Dict[str, Any]]] = []
    for e in evs:
        last = runs[-1][-1] if runs else None
        if last is not None and last["kind"] == e["kind"] and last.get("cause") == e.get("cause") \
                and int(float(last.get("year", 0))) == int(float(e.get("year", 0))) and e["kind"] not in ("MYTH",):
            runs[-1].append(e)
        else:
            runs.append([e])
    return runs


def _others(e: Dict[str, Any], name: str) -> List[str]:
    return [_name(a) for a in e.get("actors") or [] if _name(a) != name]


def _slug(name: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in name.lower()).strip("-") or "volume"


def publish(events: List[Dict[str, Any]], out_dir: str, title: str = "The Annals", by: str = "people") -> List[Dict[str, Any]]:
    """Write every volume and a catalogue (index.md) under out_dir. Returns the catalogue."""
    os.makedirs(out_dir, exist_ok=True)
    vols = volumes(events, by)
    catalogue = []
    for name, evs in sorted(vols.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(evs) < MIN_EVENTS and name != "The galaxy":
            continue                                  # a footnote, not a book
        g = genre(evs)
        path = f"{_slug(name)}.md"
        with open(os.path.join(out_dir, path), "w") as f:
            f.write(render(name, evs, events))
        catalogue.append({"volume": name, "file": path, "genre": g["genre"], "strands": g["strands"],
                          "events": len(evs), "from": _when(evs[0]), "to": _when(evs[-1]),
                          "logline": logline(name, evs, g)})
    lines = [f"# {title}", "", f"{len(events):,} events in {len(catalogue)} volumes.", ""]
    for gname in GENRES:
        shelf = [c for c in catalogue if c["genre"] == gname]
        if shelf:
            lines += [f"## {gname.title()}", ""]
            lines += [f"- [{c['volume']}]({c['file']}) - {c['events']} events, {c['from']} to {c['to']}. "
                      f"{c['logline']}" for c in shelf]
            lines.append("")
    with open(os.path.join(out_dir, "index.md"), "w") as f:
        f.write("\n".join(lines))
    return catalogue
