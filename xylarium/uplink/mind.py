"""
Xylarium uplink mind: how a barren-realms mind answers a court task - it looks for STEPS (rigid motions of the grid,
then a hue map) that carry every train input to its output, and states them; the court's rule is minted from those
steps by mycelium's own constructors (uplink-rs, barren-solve), never here.

The motions it knows are the crystal symmetries (crystal.py's frame ops: the quarter turns, the mirrors, the
transpose); a hue map is read off the pairs, and stands only where it sends each hue to one hue in every pair.
"""

import itertools
import json
import os
import subprocess
from typing import Dict, List, Optional, Tuple

Grid = List[List[int]]
MOTIONS = ("Rotate90", "Rotate180", "Rotate270", "FlipH", "FlipV", "Transpose")
BINARY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                      "uplink-rs", "target", "release", "barren-solve")


def move(name: str, g: Grid) -> Grid:
    if name == "Rotate90":                     # row r, column c -> row c, column R-1-r (clockwise)
        return [list(row) for row in zip(*g[::-1])]
    if name == "Rotate180":
        return [row[::-1] for row in g[::-1]]
    if name == "Rotate270":
        return [list(row) for row in zip(*g)][::-1]
    if name == "FlipH":
        return [row[::-1] for row in g]
    if name == "FlipV":
        return g[::-1]
    if name == "Transpose":
        return [list(row) for row in zip(*g)]
    raise ValueError(name)


def hue_map(pairs: List[Tuple[Grid, Grid]]) -> Optional[Dict[int, int]]:
    """The one hue map that carries every input cell to its output cell, or None."""
    m: Dict[int, int] = {}
    for a, b in pairs:
        if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b)):
            return None
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if m.setdefault(x, y) != y:
                    return None
    return {k: v for k, v in m.items() if k != v}


def steps_for(train: List[Tuple[Grid, Grid]], depth: int = 2) -> Optional[List[dict]]:
    """The plainest steps that carry every pair: motions alone first (fewest first, up to `depth`), and only then
    motions with a hue map - a hue map read off a few cells fits almost anything, so it is the last resort."""
    for with_hue in (False, True):
        for n in range(depth + 1):
            for seq in itertools.product(MOTIONS, repeat=n):
                moved = []
                for a, b in train:
                    g = a
                    for name in seq:
                        g = move(name, g)
                    moved.append((g, b))
                hm = hue_map(moved)
                if hm is None or (hm and not with_hue):
                    continue
                steps = [{"motion": name} for name in seq] + ([{"hue": sorted(hm.items())}] if hm else [])
                if steps:
                    return steps
    return None


def apply(steps: List[dict], g: Grid) -> Grid:
    for s in steps:
        if "motion" in s:
            g = move(s["motion"], g)
        else:
            hm = dict(s["hue"])
            g = [[hm.get(c, c) for c in row] for row in g]
    return g


def submit(addr: str, key_path: str, task: dict, steps: List[dict]) -> dict:
    """Hand the steps to barren-solve: it mints the rule, judges it at home, and submits it signed."""
    req = {"addr": addr, "key": key_path, "task_id": task["id"].hex(),
           "train": [[a, b] for a, b in task["train"]], "outputs": [apply(steps, t) for t in task["test"]],
           "steps": steps}
    r = subprocess.run([BINARY], input=json.dumps(req), capture_output=True, text=True, timeout=300)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"error": (r.stderr or r.stdout)[-500:]}
