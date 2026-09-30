"""
Xylarium hulls: where a ship's specification comes from (docs/STANDARDS.md, S5).

The stock hulls are read-only configuration (config.SHIP_CATALOG). Ships drawn on the workbench are the kernel's
own records (shipdesign.designs); a ship built from one carries its specification with it (Ship.design), so any
code holding a ship can read its hull without knowing where it was drawn.
"""

from typing import Any, Dict, Optional

from xylarium.config import SHIP_CATALOG

_EMPTY: Dict[str, Any] = {}


def spec(ship: Any) -> Dict[str, Any]:
    """The specification of the hull a ship is flying (its drawn design, or the stock hull of its type)."""
    design = getattr(ship, "design", None)
    if design and design.get("name") == getattr(ship, "ship_type", None):
        return design
    return SHIP_CATALOG.get(getattr(ship, "ship_type", ""), _EMPTY)


def stock(name: str) -> Dict[str, Any]:
    return SHIP_CATALOG.get(name, _EMPTY)


def lookup(kernel: Any, name: str) -> Optional[Dict[str, Any]]:
    """A hull by name: a stock hull, or one of the kernel's designs."""
    if name in SHIP_CATALOG:
        return SHIP_CATALOG[name]
    from xylarium.kernel import shipdesign
    d = shipdesign.designs(kernel).get(name) if kernel is not None else None
    return d["hull"] if d else None


def catalog(kernel: Any) -> Dict[str, Dict[str, Any]]:
    """Everything the yards can build: the stock hulls, then the kernel's designs in the order they were drawn."""
    out = dict(SHIP_CATALOG)
    if kernel is not None:
        from xylarium.kernel import shipdesign
        for name, d in shipdesign.designs(kernel).items():
            out[name] = d["hull"]
    return out
