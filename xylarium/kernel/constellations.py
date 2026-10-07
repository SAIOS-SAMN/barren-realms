"""
Xylarium constellations: the stewards' realms - constellations, or groups of them, each kept by one steward a
progenitor line posted there, silently, before the peoples who will live there woke.

A CONSTELLATION is a cell of the disc (cosmos: CELL_KPC on a side, its own stars). Each is posted by the line whose
dominion covers it now (settling.py: the first to settle there) - an ancient's progenitors, or a people that crossed
free and keeps its own line - and where no dominion reaches, by the elders.

A REALM is as many of one line's neighbouring constellations as one steward can keep. What a steward can keep is
its attention over a term: one matter each council season (a quarter of its people's own year) for a generation of
its line. Its duties are the matters its constellations bring it each term: every people
living there (each read once a term), every petition waiting on it, every mind due to wake there within the term.
A realm is gathered from the constellation nearest its line's home outward, constellation by constellation, until
its duties would outgrow its steward; then the next realm begins. Where nothing lives, nothing is owed: an empty
dominion is kept by one steward however vast; where peoples crowd, realms are small. The realms are read again each
year as dominions grow, peoples wake and fall.

ONE STEWARD, MANY VOICES. A realm's steward speaks in the council of every people in its realm (steward.py: a
voice in the council's choosing) and rules on every petition from it (ascendance.py). It serves no people.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

ELDERS = "elders"


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "constellations")


def centre(i: int, j: int, t_gyr: float) -> Tuple[float, float]:
    """Where a constellation's middle is at coordinate epoch t (it turns with its ring)."""
    from xylarium.kernel import cosmos
    r = cosmos.ring_radius(i)
    th = cosmos.cell_theta(i, j) + cosmos.omega(r) * t_gyr * 1000.0
    return r * math.cos(th), r * math.sin(th)


def poster(kernel: Any, cell: Tuple[int, int], t: float) -> str:
    """The line that posts a constellation's steward: whose dominion covers it, else the elders."""
    from xylarium.kernel import settling
    by = settling.settled_at(kernel, centre(cell[0], cell[1], t), t)
    return by or ELDERS


def attention(kernel: Any, line: str) -> float:
    """The matters a line's steward can keep in a term: one each council season (a council sits each quarter of its
    people's own year - the engine's fiscal quarter, on its own clock) over a generation of the line. The elders,
    who have no people, keep the galaxy's standard generation."""
    from xylarium.kernel import fertility, spheres
    gen = spheres.generation(kernel, line) if line != ELDERS else fertility.generation_years()
    return 4.0 * gen


def duties(kernel: Any, t: float, term_gyr: Dict[str, float]) -> Dict[Tuple[int, int], Dict[str, float]]:
    """What each constellation brings its steward each term: its peoples, its petitions, its minds about to wake."""
    from xylarium.kernel import ascendance, cosmos, relations
    out: Dict[Tuple[int, int], Dict[str, float]] = {}
    for who, worlds in relations._peoples(kernel).items():
        home = max(worlds, key=lambda p: (p.population, p.id))
        c = cosmos.cell_of_sector(kernel, home.sector_id)
        if c is None:
            continue
        d = out.setdefault(c, {"peoples": 0, "petitions": 0, "waking": 0})
        d["peoples"] += 1
        if (ascendance.stats(kernel)["of"].get(who) or {}).get("ruling") == "pending":
            d["petitions"] += 1
    horizon = max(term_gyr.values()) if term_gyr else 0.0
    for m in cosmos.stats(kernel).get("minds") or []:
        e = float(m.get("epoch", 0.0))
        if t <= e <= t + horizon and m.get("cell") is not None:
            c = (int(m["cell"][0]), int(m["cell"][1]))
            out.setdefault(c, {"peoples": 0, "petitions": 0, "waking": 0})["waking"] += 1
    return out


def _load(d: Optional[Dict[str, float]]) -> float:
    return float(sum(d.values())) if d else 0.0


def season(kernel: Any) -> List[str]:
    """Once a year (from the annals, which see every people): the realms are read again - each constellation's
    poster, and its line's constellations gathered into realms as far as one steward's attention holds."""
    from xylarium.kernel import cosmos, spheres
    if not cosmos.is_cosmic(kernel):
        return []
    t = cosmos.deep_gyr(kernel)
    by_line: Dict[str, List[Tuple[int, int]]] = {}
    for c in cosmos.cells():
        by_line.setdefault(poster(kernel, c, t), []).append(c)
    terms = {line: (spheres.generation(kernel, line) if line != ELDERS else 0.0) / 1e9 for line in by_line}
    load = duties(kernel, t, terms)
    realms: Dict[str, Dict[str, Any]] = {}
    of_cell: Dict[str, str] = {}
    for line in sorted(by_line):
        cells = set(by_line[line])
        cap = attention(kernel, line)
        home = spheres._home(kernel, line) if line != ELDERS else None
        hc = cosmos.cell_of_sector(kernel, home.sector_id) if home is not None else None
        n = 0
        while cells:
            seed = min(cells, key=lambda c: (abs(c[0] - hc[0]) + abs(c[1] - hc[1]) if hc else 0, c))
            n += 1
            rid = f"{line}#{n}"
            members, owed, frontier = [], 0.0, [seed]
            while frontier:
                c = frontier.pop(0)
                if c not in cells:
                    continue
                w = _load(load.get(c))
                if members and owed + w > cap:
                    continue                                 # past what one steward can keep: the next realm's
                cells.discard(c)
                members.append(c)
                owed += w
                for nb in sorted(cosmos.neighbours(c[0], c[1])):
                    if nb in cells:
                        frontier.append(nb)
            realms[rid] = {"line": line, "cells": len(members), "duties": owed, "attention": round(cap, 3),
                           "seat": members[0]}
            for c in members:
                of_cell[f"{c[0]},{c[1]}"] = rid
    st = stats(kernel)
    st["realms"], st["of_cell"], st["read"] = realms, of_cell, kernel.cycle_count
    return []


def realm_of(kernel: Any, sector_id: int) -> Optional[str]:
    """The stewards' realm a system lies in."""
    from xylarium.kernel import cosmos
    c = cosmos.cell_of_sector(kernel, sector_id)
    return stats(kernel).get("of_cell", {}).get(f"{c[0]},{c[1]}") if c else None


def line_of_realm(kernel: Any, rid: Optional[str]) -> Optional[str]:
    rec = stats(kernel).get("realms", {}).get(rid) if rid else None
    return rec["line"] if rec else None


def summary(kernel: Any) -> Dict[str, Any]:
    rs = stats(kernel).get("realms", {})
    by: Dict[str, int] = {}
    for r in rs.values():
        by[r["line"]] = by.get(r["line"], 0) + 1
    return {"realms": len(rs), "by_line": by}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="constellations", state=lambda: {"realms": {}, "of_cell": {}, "read": None},
                             summary=summary))
