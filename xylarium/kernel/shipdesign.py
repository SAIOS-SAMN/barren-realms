"""
Xylarium workbench: anyone can design ships - a frame filled with modules, held to physics.

  * A frame (config SHIP_FRAMES) gives a volume budget and structural mass; modules (SHIP_MODULES) fill it:
    holds, tanks, drives, reactors, shields, armour, fighter bays, mining lasers, berths and leisure decks.
  * The laws of the workbench: modules must fit the frame's volume; reactors must generate what the modules draw;
    and every module has mass. Mass is what the drive burns reaction mass to move (propulsion.burn_for), and a
    design whose drives cannot move its mass at full pace is sluggish (two turns a jump).
  * The fuel cell is part of the design: the drive is built for one propellant (config FUEL_CELLS), and its tanks
    hold that propellant. A designer who does not name one gets the cell its own reckoning prefers where it
    stands (propulsion.choose_fuel) - so a plasmic designer on a helium world and a biotic one on a water world
    draw different ships.
  * Liners: berths carry passengers; leisure decks are built for a biology (a water spa comforts biotic guests, a
    plasma bath plasmic ones). A VIP charter pays more the better the ship's comfort fits its guests (tourism.py).
  * A design is the kernel's record, with a hull entry in the shape every system reads (hulls.py): the yards and the
    AI see it beside the stock hulls, and a ship built from it carries it. Building one draws its materials (Fe,
    Ti, Si) from the yard's warehouse.
  * Designs are property: whoever else builds one pays its designer a royalty out of the price. Designing is a
    career - a player (or an AI draughtsman) may do nothing else.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import (
    COMFORT_PER_BERTH_FULL,
    DESIGN_FEE,
    DESIGN_ROYALTY_MAX,
    DRIVE_MASS_PER_THRUST,
    FUEL_CELLS,
    SHIP_CATALOG,
    SHIP_FRAMES,
    SHIP_MODULES,
)

MATERIALS = ("Fe", "Ti", "Si")


def designs(kernel: Any) -> Dict[str, Dict[str, Any]]:
    return state.of(kernel, "workbench")["designs"]


# ---------------------------------------------------------------------- the laws of the workbench
def evaluate(frame: str, modules: Dict[str, int], drive: str = "H") -> Dict[str, Any]:
    """The derived specification of a design, and whatever breaks the workbench's laws (in 'faults')."""
    faults: List[str] = []
    fr = SHIP_FRAMES.get(frame)
    if fr is None:
        return {"faults": [f"Unknown frame '{frame}' ({', '.join(SHIP_FRAMES)})."]}
    if drive not in FUEL_CELLS:
        faults.append(f"Unknown fuel cell '{drive}' ({', '.join(FUEL_CELLS)}).")
    vol, mass, power, price = 0.0, float(fr["mass"]), 0.0, float(fr["price"])
    mats = {m: float(fr.get(m, 0)) for m in MATERIALS}
    gives: Dict[str, float] = {}
    comfort: Dict[str, float] = {}
    for name, n in modules.items():
        n = int(n)
        spec = SHIP_MODULES.get(name)
        if spec is None:
            faults.append(f"Unknown module '{name}'.")
            continue
        if n <= 0:
            continue
        vol += spec["volume"] * n
        mass += spec["mass"] * n
        power += spec["power"] * n
        price += spec["price"] * n
        for m in MATERIALS:
            mats[m] += spec.get(m, 0) * n
        for k, v in spec["gives"].items():
            if k == "comfort":
                for metab in spec.get("for", []):
                    comfort[metab] = comfort.get(metab, 0.0) + v * n
            else:
                gives[k] = gives.get(k, 0.0) + v * n
    if vol > fr["volume"]:
        faults.append(f"Modules fill {vol:g} of the {frame}'s {fr['volume']} volume.")
    if power < 0:
        faults.append(f"Reactors fall {-power:g} short of what the modules draw (add reactors).")
    thrust = gives.get("thrust", 0.0)
    if thrust <= 0:
        faults.append("A ship needs at least one drive.")
    cell = FUEL_CELLS.get(drive, FUEL_CELLS["H"])
    if cell.get("v_e") and gives.get("tank", 0) <= 0:
        faults.append(f"A {cell['name']} needs tanks for its propellant.")
    berths = int(gives.get("berths", 0))
    fit = {m: round(min(1.0, c / max(1.0, berths * COMFORT_PER_BERTH_FULL)), 3) for m, c in comfort.items()} if berths else {}
    return {
        "frame": frame, "modules": {k: int(v) for k, v in modules.items() if int(v) > 0}, "drive": drive,
        "volume": vol, "mass": round(mass, 1), "power": round(power, 1), "price": int(price),
        "materials": {m: int(math.ceil(v)) for m, v in mats.items() if v > 0},
        "holds": int(gives.get("holds", 0)), "tank": int(gives.get("tank", 0)),
        "max_shields": int(gives.get("max_shields", 0)), "max_fighters": int(gives.get("max_fighters", 0)),
        "mining": int(gives.get("mining", 0)), "berths": berths, "comfort": fit,
        "move_turns": 1 if thrust * DRIVE_MASS_PER_THRUST >= mass else 2,
        "min_rank_tier": max(fr["min_tier"], cell.get("min_tier", 1)),
        "faults": faults,
    }


def register(kernel: Any, designer: Any, name: str, frame: str, modules: Dict[str, int], drive: Optional[str] = None,
             royalty: float = 0.05, description: str = "", fee: bool = True) -> Dict[str, Any]:
    """Draw up a design and enter it in the hull catalogue. Raises ValueError if it breaks the workbench's laws."""
    name = (name or "").strip()
    if not name or len(name) > 40:
        raise ValueError("Name the design (up to 40 characters).")
    if name in SHIP_CATALOG:
        raise ValueError(f"'{name}' is a stock hull.")
    if name in designs(kernel) and designs(kernel)[name]["designer"] != designer.id:
        raise ValueError(f"'{name}' is someone else's design.")
    if drive is None:
        from xylarium.kernel import propulsion
        drive = propulsion.choose_fuel(kernel, designer.sector_id, getattr(designer, "metabolism", "biotic") or "biotic",
                                       getattr(designer, "rank_tier", 1), getattr(designer, "cosmic_alignment", 0.0),
                                       holder=f"captain:{designer.id}")
    spec = evaluate(frame, modules, drive)
    if spec["faults"]:
        raise ValueError(" ".join(spec["faults"]))
    if fee:
        if designer.credits < DESIGN_FEE:
            raise ValueError(f"The draughting office's registry fee is {DESIGN_FEE} Cr.")
        designer.credits -= DESIGN_FEE
        sec = kernel.sectors.get(designer.sector_id)
        if sec is not None and sec.port is not None:
            kernel._stardock_revenue(sec, DESIGN_FEE)
        else:
            kernel._stardock_revenue(kernel.sectors[1], DESIGN_FEE)
    spec.update(name=name, designer=designer.id, designer_name=designer.name,
                royalty=round(max(0.0, min(DESIGN_ROYALTY_MAX, float(royalty))), 3), built=0,
                description=description or f"{frame.title()} drawn by {designer.name}.",
                created=kernel.cycle_count)
    spec["hull"] = _hull(spec)
    designs(kernel)[name] = spec
    _stats(kernel)["designed"] += 1
    return spec


def _hull(spec: Dict[str, Any]) -> Dict[str, Any]:
    """A design's entry in the hull catalogue (the shape every system reads - hulls.py)."""
    return {
        "name": spec["name"],
        "holds": spec["holds"], "max_shields": spec["max_shields"], "max_fighters": spec["max_fighters"],
        "price": spec["price"], "min_rank_tier": spec["min_rank_tier"], "berths": spec["berths"],
        "mass": spec["mass"], "tank": spec["tank"], "drive": spec["drive"], "mining": spec["mining"],
        "comfort": spec["comfort"], "move_turns": spec["move_turns"], "materials": spec["materials"],
        "designer": spec["designer"], "royalty": spec["royalty"], "description": spec["description"],
    }


def restore(kernel: Any) -> None:
    """After a load: designs saved before hull entries were kept get theirs."""
    for spec in designs(kernel).values():
        spec.setdefault("hull", _hull(spec))


def royalty_on_build(kernel: Any, builder: Any, ship_name: str, price_sol: int) -> int:
    """Whoever builds another's design pays its designer the royalty out of the price (the yard gets the rest).
    Returns the royalty paid (to be subtracted from the yard's take)."""
    spec = designs(kernel).get(ship_name)
    if spec is None:
        return 0
    spec["built"] = spec.get("built", 0) + 1
    designer = kernel.captains.get(spec["designer"])
    if designer is None or designer.id == builder.id:
        return 0
    fee = int(price_sol * spec.get("royalty", 0.0))
    if fee > 0:
        designer.credits += fee
        st = _stats(kernel)
        st["royalties"] += fee
    return fee


def comfort_fit(ship: Any, metabolism: str) -> float:
    from xylarium.kernel import hulls
    return float(hulls.spec(ship).get("comfort", {}).get(metabolism, 0.0))


def _stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "workbench")["stats"]


# ---------------------------------------------------------------------- the AI draughtsman
ROLES = ("hauler", "miner", "liner", "warship")


def draft(frame: str, role: str, metabolism: str, drive: str) -> Dict[str, int]:
    """A sensible layout for a role: fill the frame, keep the power positive, carry enough tank."""
    vol = SHIP_FRAMES[frame]["volume"]
    mods: Dict[str, int] = {"drive": max(1, vol // 60), "reactor": 1}
    cell = FUEL_CELLS.get(drive, FUEL_CELLS["H"])
    tanks = max(2, vol // (12 * max(1, int(cell.get("v_e") or 1)))) if cell.get("v_e") else 0
    if tanks:
        mods["tank"] = tanks
    deck = {"biotic": "water_spa", "cryogenic": "cryo_lounge", "plasmic": "plasma_bath",
            "mineral": "mineral_grotto", "umbral": "void_gallery"}.get(metabolism, "water_spa")
    if role == "liner":
        mods.update(berth=vol // 6, shield=vol // 40)
        mods[deck] = max(1, mods["berth"] // 4)
    elif role == "miner":
        mods.update(mining_laser=max(1, vol // 40), shield=vol // 60)
    elif role == "warship":
        mods.update(shield=vol // 12, fighter_bay=vol // 15, armor=vol // 20)
    else:
        mods.update(shield=vol // 50)
    used = sum(SHIP_MODULES[m]["volume"] * n for m, n in mods.items())
    power = sum(SHIP_MODULES[m]["power"] * n for m, n in mods.items())
    while power < 0 and used + SHIP_MODULES["reactor"]["volume"] <= vol:
        mods["reactor"] += 1
        used += SHIP_MODULES["reactor"]["volume"]
        power += SHIP_MODULES["reactor"]["power"]
    mods["hold"] = max(0, int(vol - used))                # the rest is cargo
    if role == "liner":
        mods["hold"] = mods["hold"] // 3
    return mods


def ai_design(kernel: Any, captain: Any, role: str) -> Optional[Dict[str, Any]]:
    """An autonomous captain draws a ship for its own trade: the biggest frame it may fly, the fuel cell its
    reckoning prefers where it stands, the decks its guests' biology wants."""
    tier = getattr(captain, "rank_tier", 1)
    frames = [f for f, s in SHIP_FRAMES.items() if s["min_tier"] <= tier]
    if not frames:
        return None
    frame = max(frames, key=lambda f: SHIP_FRAMES[f]["volume"])
    from xylarium.kernel import propulsion
    metab = getattr(captain, "metabolism", "biotic") or "biotic"
    drive = propulsion.choose_fuel(kernel, captain.sector_id, metab, tier, getattr(captain, "cosmic_alignment", 0.0))
    guests = metab
    if role == "liner":
        guests = _likely_guests(kernel, captain) or metab
    mods = draft(frame, role, guests, drive)
    name = f"{captain.name.split()[-1]} {role.title()} {frame[:3].upper()}-{kernel.cycle_count % 1000:03d}"
    try:
        spec = register(kernel, captain, name, frame, mods, drive, royalty=0.05,
                        description=f"{role.title()} {frame} for {guests} guests on a {FUEL_CELLS[drive]['name']}.")
    except ValueError:
        return None
    _stats(kernel)["ai_designs"] += 1
    return spec


def _likely_guests(kernel: Any, captain: Any) -> Optional[str]:
    """The biology of the charters posted in reach (whose VIPs a liner would carry)."""
    from xylarium.kernel import biosphere, tourism
    counts: Dict[str, int] = {}
    for c in tourism.charters(kernel).values():
        if c["status"] != "OPEN":
            continue
        p = kernel.get_planet(c["origin_planet"])
        if p is not None:
            m = biosphere.metabolism_of(kernel, p)
            counts[m] = counts.get(m, 0) + 1
    return max(counts, key=counts.get) if counts else None


def consider(kernel: Any, captain: Any, sector: Any) -> Optional[str]:
    """Once in a long while a docked, well-off autonomous captain at a yard draws a ship for its trade: a liner if
    charters go unflown in reach, a miner if it mines, else a hauler."""
    if not captain.is_ai or captain.faction_id or sector.port is None or getattr(captain, "rank_tier", 1) < 2:
        return None
    from xylarium.kernel.cognition import temperament
    t = temperament(captain, kernel)
    # a captain who drew a liner builds it once it can afford it twice over: guests pay full fare only for decks
    # drawn for them (tourism.arrive), and an ordinary hull earns half
    liner = next((d for d in designs(kernel).values() if d["designer"] == captain.id and d["berths"] > 0), None)
    if liner is not None and captain.ship.ship_type != liner["name"] and captain.credits >= 2 * liner["price"] \
            and kernel.cycle_count - int(t.get("liner_try", -10 ** 9)) >= 100:
        t["liner_try"] = kernel.cycle_count        # once in a while - and never again from inside its own purchase
        from xylarium.kernel.models import ActionType
        res = kernel.dispatch(captain.id, ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name=liner["name"])
        if getattr(res, "success", False):
            _stats(kernel)["liners_built"] = _stats(kernel).get("liners_built", 0) + 1
            return f"{captain.name} commissioned its liner {liner['name']}."
    if kernel.cycle_count - int(t.get("drafted", -10 ** 9)) < 1500 or captain.credits < 30_000:
        return None
    t["drafted"] = kernel.cycle_count
    from xylarium.kernel import tourism
    unflown = sum(1 for c in tourism.charters(kernel).values() if c["status"] == "OPEN")
    role = "liner" if unflown >= 3 else ("miner" if t.get("calling") == "miner" else "hauler")
    spec = ai_design(kernel, captain, role)
    return f"{captain.name} drew the {spec['name']}." if spec else None


def summary(kernel: Any) -> Dict[str, Any]:
    ds = designs(kernel)
    by_drive: Dict[str, int] = {}
    for s in ds.values():
        by_drive[s["drive"]] = by_drive.get(s["drive"], 0) + 1
    flying: Dict[str, int] = {}
    for c in kernel.captains.values():
        if c.ship.ship_type in ds:
            flying[c.ship.ship_type] = flying.get(c.ship.ship_type, 0) + 1
    return {**_stats(kernel), "designs": len(ds), "by_drive": by_drive, "flying": flying,
            "examples": [f"{s['name']} ({s['frame']}, {s['drive']}, holds {s['holds']}, berths {s['berths']})"
                         for s in list(ds.values())[:4]]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="workbench",
    state=lambda: {"designs": {}, "stats": {"designed": 0, "royalties": 0, "ai_designs": 0}},
    restore=restore,
    summary=summary,
))
