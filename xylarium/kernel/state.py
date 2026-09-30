"""
Xylarium state: each subsystem's record lives in kernel.state (docs/STANDARDS.md, S2).

`of(kernel, name)` returns the subsystem's record, creating it from the subsystem's registered factory on first
use. Records are JSON-shaped and saved whole by the store; nothing about a subsystem is attached to the kernel as
a loose attribute.
"""

from typing import Any

from xylarium.kernel import subsystem


def of(kernel: Any, name: str) -> Any:
    rec = kernel.state.get(name)
    if rec is None:
        sub = subsystem.get(name)
        if sub is None or sub.state is None:
            raise KeyError(f"no subsystem state registered as '{name}'")
        rec = kernel.state[name] = sub.state()
    return rec
