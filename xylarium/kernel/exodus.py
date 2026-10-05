"""
Xylarium exodus: what peoples do when their star is dying - and what it says about their governments.

FORECAST. A people reads its own star's end once the share of that star's life still ahead falls to what it knows of
stellar physics (its mastery of energy: knowing everything, it knows from the start; knowing nothing, it learns only
when its sun begins to swell and burn its fields). The forecast is a ledger event, with the years left.

THE DUTY. A government that can move its people must decide to, once the years its sun has left no longer exceed what
the move would take plus its own planning horizon: each season from then, every world of the people with shipyards
can carry a settler fleet (DAUGHTER_EMIGRANTS_MAX people) to a world whose star will outlive the move - one of its
own with room, or an empty one its biology can live on, in its fleets' reach. It weighs the lives (what they would
produce over its horizon) against the fleets' cost, by the one rule (decide.py), each season it knows. Whatever it
could have carried and did not is remembered.

RESCUE. A people with no ships cannot leave. Another people that can reach it and has met it may carry it out - as
far as it values strangers' lives: by its alignment (the Light weighs them; the Dark does not). Rescued peoples keep
their own name, body and way of life on their new world.

SALVAGE. A people with ships that foresees a star's death may strip its doomed worlds first: each season, each of its
yards worlds in reach hauls a season of its own mining (its numbers at the crust's rate, colony.py) times its
mastery of materials from the doomed worlds' deposits into its own reserves - matter moved, not made. (The light a
swelling star pours out is the other windfall: its arrays and fields already take it, physics.planet_flux.)

ACCOUNTING. When the star dies, those still on its worlds die with it. Of them, as many as the government could have
moved and did not are counted against it: harm, life for life (alignment.measure) - toward the Dark - and its
surviving worlds lose faith in their order (morale; the stress that leads to strife, society.py). Peoples with no
ships and no rescuer are mourned, not blamed. A steward may order the exodus (ages.act "exodus"): the council then
moves all it can, whatever the cost.
"""

from typing import Any, Dict, List, Optional, Tuple


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "exodus")


def _holder(planet: Any) -> Optional[str]:
    from xylarium.kernel import knowledge
    return knowledge.holder_of_planet(planet)


def _energy(kernel: Any, holder: Optional[str]) -> float:
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge, laws
    return laws.mastery(knowledge.experience(kernel, holder, "energy"), KNOWLEDGE_UNIT) if holder else 0.0


def _worlds_of(kernel: Any, holder: str) -> List[Any]:
    return [p for s in kernel.sectors.values() for p in s.planets if p.population > 0 and _holder(p) == holder]


def _fleets(kernel: Any, holder: str) -> List[Any]:
    from xylarium.kernel import sustenance
    return [p for p in _worlds_of(kernel, holder) if sustenance.yards(p)]


def _safe(kernel: Any, sector_id: int, years_needed: float) -> bool:
    from xylarium.kernel import cosmos
    left = cosmos.years_left(kernel, sector_id)
    return cosmos.phase(kernel, sector_id)[0] == "main" and (left is None or left > years_needed)


def _destination(kernel: Any, src: Any, port: Any, metab: str) -> Optional[Tuple[Any, bool]]:
    """(world, is_new): one of the people's own worlds with room under a lasting star, else an empty world its biology
    can live on - within the fleets' reach, nearest first."""
    from xylarium.kernel import biosphere, cohabit, demography, topology
    from xylarium.kernel.universe import habitability
    holder = _holder(src)
    reach = topology.reach(kernel, port.sector_id, max(1, demography.settler_reach(kernel, port)))
    for sid in reach:
        if sid == src.sector_id or not _safe(kernel, sid, 100.0):
            continue
        for w in kernel.sectors[sid].planets:
            if w.population > 0 and _holder(w) == holder and biosphere.carrying_capacity(kernel, w) > w.population:
                return w, False
    for sid in reach:
        if sid == src.sector_id or not _safe(kernel, sid, 100.0):
            continue
        for w in kernel.sectors[sid].planets:
            if w.population <= 0 and not w.owner_id and getattr(w, "civilization", None) is None \
                    and cohabit.niche(w, metab) and habitability(metab, w.planet_type) >= 0.3:
                return w, True
    return None


def _carry(kernel: Any, src: Any, dst: Any, n: int, new: bool) -> int:
    from xylarium.kernel import genome, institutions
    n = min(n, src.population)
    if n <= 0:
        return 0
    src.population -= n
    if new:
        dst.civilization = src.civilization
        dst.owner_id = src.owner_id
        dst.population = n
        for key in ("way", "crop_z", "way_k", "gauges"):
            if key in src.society:
                dst.society[key] = src.society[key]
        genome.inherit(src, dst)
        if institutions.founding(kernel):
            institutions.rehome(kernel, dst, src.currency, "settlers_money")   # what the world held is reformed
    else:
        dst.population += n
    return n


def _worth(kernel: Any, planet: Any, lives: int, m: Dict[str, float]) -> float:
    from xylarium.kernel import decide
    from xylarium.kernel.demography import _tax_per_head_quarter
    per_head = max(_tax_per_head_quarter(planet), 1e-6)
    return decide.worth(kernel, lives * per_head, m, planet.currency)


def _fare(kernel: Any, n: int, planet: Any) -> float:
    """A fleet's cost per head: a hull's cost over the people it carries (colony.py's commissioning cost)."""
    from xylarium.config import DAUGHTER_EMIGRANTS_MAX, PLANETARY_SPACEFLIGHT_COST, PRICE_LEVEL
    return n * PLANETARY_SPACEFLIGHT_COST * PRICE_LEVEL.get(planet.currency, 1.0) / DAUGHTER_EMIGRANTS_MAX


# ---------------------------------------------------------------------- the season
def quarter(kernel: Any) -> List[str]:
    from xylarium.config import DAUGHTER_EMIGRANTS_MAX
    from xylarium.kernel import biosphere, contact, cosmos, decide, history, sustenance
    if not cosmos.is_cosmic(kernel):
        return []
    st = stats(kernel)
    logs: List[str] = []
    doomed = [int(s) for s, ph in cosmos.stats(kernel)["phase"].items() if ph == "giant"]
    from xylarium.kernel import zones
    lived = zones.peopled(kernel)                         # a main-sequence star matters here only where people live
    doomed += [int(s) for s in cosmos.stats(kernel)["place"] if int(s) not in doomed and int(s) in lived
               and cosmos.phase(kernel, int(s))[0] == "main"]
    for sid in doomed:
        sec = kernel.sectors.get(sid)
        if sec is None:
            continue
        for p in [w for w in sec.planets if w.population > 0 and getattr(w, "civilization", None) is not None]:
            holder = _holder(p)
            if not cosmos.forecasts(kernel, sid, _energy(kernel, holder)):
                continue
            soc = p.society
            name = getattr(p.civilization, "name", p.name)
            if "forecast" not in soc:
                left = cosmos.years_left(kernel, sid) or 0.0
                soc["forecast"] = {"cycle": kernel.cycle_count, "years_left": round(left, 1)}
                history.event(kernel, "FORECAST", f"The {name} reckon their sun has {left:,.0f} years left",
                              actors=[holder], planet=p, cause="what they know of how stars live and die",
                              data={"years_left": left, "kind": cosmos.death_kind(kernel, sid)})
                logs.append(f"[EXODUS] The {name} of {p.name} reckon their sun has {left:,.0f} years left.")
            fleets = _fleets(kernel, holder)
            metab = biosphere.metabolism_of(kernel, p)
            if fleets:                                       # its own government's duty
                cap = DAUGHTER_EMIGRANTS_MAX * len(fleets)
                m = decide.mind_of_planet(kernel, p)
                # the duty begins when the years left no longer exceed the move itself plus the council's horizon
                move_years = p.population / max(1, cap) / 4.0
                if (cosmos.years_left(kernel, sid) or 0.0) > move_years + decide.horizon(m) / 4.0 \
                        and not soc.get("exodus_ordered"):
                    continue
                could = min(cap, p.population)
                soc["evac_could"] = soc.get("evac_could", 0) + could
                ordered = bool(soc.get("exodus_ordered"))
                go = ordered or decide.choose(kernel, [decide.option("exodus", _fare(kernel, could, p),
                                                                     _worth(kernel, p, could, m))],
                                              m, p.id, "exodus") is not None
                moved = 0
                if go:
                    for port in fleets:
                        dest = _destination(kernel, p, port, metab)
                        if dest is None:
                            continue
                        moved += _carry(kernel, p, dest[0], min(DAUGHTER_EMIGRANTS_MAX, cap - moved), dest[1])
                        if moved >= cap or p.population <= 0:
                            break
                soc["evac_moved"] = soc.get("evac_moved", 0) + moved
                st["moved"] += moved
                if moved:
                    history.event(kernel, "EXODUS", f"The {name} carry {moved:,} from {p.name}", actors=[holder],
                                  planet=p, magnitude=moved, cause="their sun is dying")
                continue
            # no ships of its own: who can reach it, has met it, and values strangers' lives?
            fam = contact.stats(kernel)["familiarity"]
            for port in [w for s2 in kernel.sectors.values() for w in s2.planets
                         if w.population > 0 and sustenance.yards(w) and _holder(w) != holder
                         and contact._key(holder, _holder(w) or "") in fam]:
                civ = getattr(port, "civilization", None)
                light = max(0.0, float(getattr(civ, "alignment", 0.0) or 0.0))
                mr = decide.mind_of_planet(kernel, port)
                n = min(DAUGHTER_EMIGRANTS_MAX, p.population)
                if decide.choose(kernel, [decide.option("rescue", _fare(kernel, n, port),
                                                        _worth(kernel, port, n, mr) * light)],
                                 mr, port.id, "rescue", p.id) is None:
                    continue
                dest = _destination(kernel, p, port, metab)
                if dest is None:
                    continue
                saved = _carry(kernel, p, dest[0], n, dest[1])
                if saved:
                    st["rescued"] += saved
                    sustenance.flow_civ(port, light=saved, why="rescue")
                    rname = getattr(civ, "name", port.name)
                    history.event(kernel, "RESCUE", f"The {rname} carry {saved:,} of the {name} to safety",
                                  actors=[_holder(port), holder], planet=p, magnitude=saved,
                                  cause="their sun is dying and they had no ships")
                    logs.append(f"[EXODUS] The {rname} carry {saved:,} of the {name} from {p.name}.")
                break
    logs += _salvage(kernel, doomed)
    return logs


def _salvage(kernel: Any, sectors: List[int]) -> List[str]:
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import cosmos, demography, history, knowledge, laws, sustenance, topology
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    st = stats(kernel)
    logs: List[str] = []
    dying = [s for s in sectors if cosmos.phase(kernel, s)[0] == "giant"]
    if not dying:
        return logs
    ports = [w for s in kernel.sectors.values() for w in s.planets if w.population > 0 and sustenance.yards(w)]
    for port in ports:
        holder = _holder(port)
        reach = set(topology.reach(kernel, port.sector_id, max(1, demography.settler_reach(kernel, port))))
        m = laws.mastery(knowledge.experience(kernel, holder, "materials"), KNOWLEDGE_UNIT)
        haul = int(port.population * 0.02 * FISCAL_QUARTER_CYCLES * m)
        for sid in dying:
            if sid not in reach or haul <= 0 or not cosmos.forecasts(kernel, sid, _energy(kernel, holder)):
                continue
            taken = 0
            from xylarium.kernel import zones
            zones.touch_sector(kernel, sid)                   # its ground is brought to now before it is stripped
            for w in kernel.sectors[sid].planets:
                if w.population > 0 and _holder(w) != holder:
                    continue                                   # not another people's living world
                for el in sorted(w.element_deposits):
                    q = min(w.element_deposits[el], haul - taken)
                    if q <= 0:
                        continue
                    w.element_deposits[el] -= q
                    port.element_reserves[el] = port.element_reserves.get(el, 0) + q
                    taken += q
                if taken >= haul:
                    break
            if taken:
                st["salvaged"] = st.get("salvaged", 0) + taken
                history.event(kernel, "SALVAGE", f"{getattr(port.civilization, 'name', port.name)} strip the worlds "
                              f"of {kernel.sectors[sid].name} before their sun dies", actors=[holder],
                              sector_id=sid, magnitude=taken, cause="the star is on its giant branch")
    return logs


def perished(kernel: Any, planet: Any, lives: int, kind: str) -> None:
    """A world's people die with their star: count what their government could have saved and did not."""
    from xylarium.kernel import alignment, history, sustenance
    st = stats(kernel)
    soc = planet.society
    holder = _holder(planet)
    failed = max(0, min(lives, int(soc.get("evac_could", 0)) - int(soc.get("evac_moved", 0))))
    st["perished"] += lives
    st["abandoned"] += failed
    name = getattr(getattr(planet, "civilization", None), "name", planet.name)
    history.event(kernel, "PERISHED", f"{lives:,} of the {name} die with their sun", actors=[holder], planet=planet,
                  magnitude=lives, cause=f"{kind.replace('_', ' ')}" + (f"; {failed:,} could have been carried"
                                                                        if failed else ""))
    if failed <= 0:
        return
    owner = kernel.captains.get(planet.owner_id) if planet.owner_id else None
    if owner is not None:
        alignment.act(kernel, owner, "core_harvest", lives_lost=failed)
    for w in _worlds_of(kernel, holder):
        if w is planet:
            continue
        alignment.omitted(w, failed, alignment.foreseen(kernel, holder, "energy"), 1.0, "abandoned")   # it could carry
                                                                 # them; as far as it knew its star, it knew
        w.morale = max(10, w.morale - 25)                        # and its people lose faith in it
    history.event(kernel, "ABANDONED", f"The {name} were left to die", actors=[holder], planet=planet,
                  magnitude=failed, cause="their government could have carried them and did not")


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    return {"moved": st["moved"], "rescued": st["rescued"], "perished": st["perished"], "abandoned": st["abandoned"],
            "salvaged": st.get("salvaged", 0)}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="exodus",
    state=lambda: {"moved": 0, "rescued": 0, "perished": 0, "abandoned": 0},
    season=quarter,
    summary=summary,
))
