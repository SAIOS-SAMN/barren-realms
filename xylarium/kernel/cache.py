"""
Xylarium cache: memoized derived values with explicit staleness (docs/STANDARDS.md, S4).

Every cache is a bucket in kernel.caches (never saved). A bucket goes stale as a whole when its `epoch` changes
(`season`, `graph`, or any value the caller derives from its inputs) or when it is older than `max_age` cycles; a
single entry goes stale when its `stamp` changes (`stamped`). Invalidation is always one of these - never a
scattered reset.
"""

from typing import Any, Callable, Hashable, Optional

SEASON_CYCLES = 25


def season(kernel: Any) -> int:
    return kernel.cycle_count // SEASON_CYCLES


def graph(kernel: Any) -> int:
    from xylarium.kernel import topology
    return topology.version(kernel)


def _bucket(kernel: Any, name: str, epoch: Hashable, max_age: Optional[int]) -> dict:
    b = kernel.caches.get(name)
    now = kernel.cycle_count
    if b is None or b["epoch"] != epoch or (max_age is not None and now - b["built"] > max_age):
        b = kernel.caches[name] = {"epoch": epoch, "built": now, "values": {}}
    return b["values"]


def memo(kernel: Any, bucket: str, key: Hashable, compute: Callable[[], Any], epoch: Hashable = None,
         max_age: Optional[int] = None) -> Any:
    """The cached value of ``key`` in ``bucket``, computed once per epoch (or per max_age cycles)."""
    vals = _bucket(kernel, bucket, epoch, max_age)
    if key not in vals:
        vals[key] = compute()
    return vals[key]


def stamped(kernel: Any, bucket: str, key: Hashable, stamp: Hashable, compute: Callable[[], Any]) -> Any:
    """The cached value of ``key``, recomputed whenever its inputs' ``stamp`` changes."""
    vals = kernel.caches.setdefault(bucket, {"epoch": None, "built": kernel.cycle_count, "values": {}})["values"]
    hit = vals.get(key)
    if hit is None or hit[0] != stamp:
        hit = vals[key] = (stamp, compute())
    return hit[1]


def clear(kernel: Any) -> None:
    kernel.caches.clear()
