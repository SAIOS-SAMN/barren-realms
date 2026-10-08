"""
Xylarium uplink mind: the seam between a mind's program and the court's language - plumbing, never a mind.

A barren-realms mind writes its own program over the crystals its people holds (intellect.decompact; the court meets
it in court.py). Here that program is only translated: each frame crystal is the rigid motion of the grid the court's
rule steps name (the same conventions: a quarter turn sends row r, column c of an R x C grid to row c, column R-1-r),
a recolouring is a hue map naming every hue it moves; and the steps are handed to barren-solve (uplink-rs), which
mints the rule through mycelium's own constructors, judges it at home, and submits it signed.
"""

import json
import os
import subprocess
from typing import Any, List, Optional

BINARY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                      "uplink-rs", "target", "release", "barren-solve")


def steps_of(program: List[Any]) -> Optional[List[dict]]:
    """A planar program as the court's steps; None where an op has no form in its language (stack and volume ops)."""
    from xylarium.kernel import crystal as C
    names = dict(zip(C.FRAME_OPS, ("Rotate90", "Rotate180", "Rotate270", "FlipH", "FlipV", "Transpose")))
    steps: List[dict] = []
    for op in program:
        if op in names:
            steps.append({"motion": names[op]})
        elif isinstance(op, tuple) and len(op) == 2 and op[0] == C.RECOLOR:
            steps.append({"hue": [(h, int(t)) for h, t in enumerate(op[1]) if int(t) != h]})
        else:
            return None
    return steps


def submit(addr: str, key_path: str, task: dict, steps: List[dict], outputs: List[List[List[int]]]) -> dict:
    """Hand a mind's steps to barren-solve: it mints the rule, judges it at home, and submits it signed."""
    req = {"addr": addr, "key": key_path, "task_id": task["id"].hex(),
           "train": [[a, b] for a, b in task["train"]], "outputs": outputs, "steps": steps}
    r = subprocess.run([BINARY], input=json.dumps(req), capture_output=True, text=True, timeout=300)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"error": (r.stderr or r.stdout)[-500:]}
