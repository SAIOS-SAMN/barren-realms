"""
Xylarium subsystems: every module that owns state or works on the seasonal clock declares itself here
(docs/STANDARDS.md, S1).

A Subsystem names its state record (created by `state`, kept in kernel.state and saved whole), its seasonal hook
(`season`: kernel -> log lines, run once per fiscal quarter in SEASON order), and optional `restore` (after a
load), `genesis` (when a universe is made) and `summary` (for the playtest report) hooks. The engine runs the
season through `run_season`; the store saves `kernel.state`; the harness reads `summaries`.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# The fiscal quarter, in order. Money settles first (policy, the Reserve, the banks, the exchanges), then the moral
# and native worlds, the courts of arms and credit, the physical world, crime and law, the lanes, the peoples and
# what they make and where they travel, and finally who governs what.
SEASON = [
    "tempo", "clocks", "cosmos", "annals", "climate", "cluster", "sphere", "blackhole", "exodus", "guidance", "monetary_policy", "federal_reserve", "backing", "banking", "fx_reanchor", "prices", "liquidity", "regimes", "alignment", "natives", "sieges",
    "credit", "geology", "propulsion", "crime", "law", "fibres", "physics", "demography",
    "fertility", "lifespan", "contact", "institutions", "sustenance", "relations", "kinship", "federation", "occupation", "society", "memory", "culture", "syntropy", "reputation", "strategy", "steward_ai", "learning", "cohabit", "knowledge", "ways", "chemistry", "harvest", "energy", "waste", "skies", "intellect", "technology", "relics", "mastery", "signals", "genome", "introspect", "luxury", "tourism", "enterprise", "liquidation", "waystations", "observation", "realms", "polity", "dynasties", "spheres", "stewardship", "ascendance", "borders", "supply", "demand", "news", "comms", "exchanges", "fxroutes", "commerce", "covert", "realmwars", "transit", "hypha", "ladder", "board", "court", "reserve_banks", "consciousness", "leak", "inputs", "mottos", "perception", "field", "government",
]


@dataclass
class Subsystem:
    name: str
    state: Optional[Callable[[], Any]] = None
    season: Optional[Callable[[Any], Optional[List[str]]]] = None
    restore: Optional[Callable[[Any], None]] = None
    genesis: Optional[Callable[[Any], None]] = None
    summary: Optional[Callable[[Any], Dict[str, Any]]] = None


REGISTRY: Dict[str, Subsystem] = {}


def register(sub: Subsystem) -> Subsystem:
    if sub.season is not None and sub.name not in SEASON:
        raise ValueError(f"{sub.name} has a seasonal hook but no place in subsystem.SEASON")
    REGISTRY[sub.name] = sub
    return sub


def get(name: str) -> Optional[Subsystem]:
    return REGISTRY.get(name)


def run_season(kernel: Any) -> None:
    """One fiscal quarter: every registered seasonal hook, in SEASON order; their lines go to the action log."""
    from xylarium.kernel import zones
    shut = None                                          # folded worlds are off the map for the engine's own laws
    try:
        for name in SEASON:
            sub = REGISTRY.get(name)
            if sub is None or sub.season is None:
                continue
            if (name in zones.SEES_FOLDED) == (shut is not None):
                if shut is None:
                    shut = zones.hidden(kernel)
                    shut.__enter__()
                else:
                    shut.__exit__(None, None, None)
                    shut = None
            if name == "federal_reserve" and not institutions.reserve_founded(kernel):
                continue                                 # no Reserve has been founded yet (institutions.py)
            scheduler.lock(kernel, "season", name, kernel.cycle_count)    # each season its own stream
            for line in sub.season(kernel) or []:
                kernel.action_logs.append(line)
    finally:
        if shut is not None:
            shut.__exit__(None, None, None)

from xylarium.kernel import institutions, scheduler  # noqa: E402


def run_genesis(kernel: Any) -> None:
    for sub in REGISTRY.values():
        if sub.genesis is not None:
            sub.genesis(kernel)


def restore_all(kernel: Any) -> None:
    for sub in REGISTRY.values():
        if sub.restore is not None:
            sub.restore(kernel)


def summaries(kernel: Any) -> Dict[str, Dict[str, Any]]:
    return {name: sub.summary(kernel) for name, sub in REGISTRY.items() if sub.summary is not None}
