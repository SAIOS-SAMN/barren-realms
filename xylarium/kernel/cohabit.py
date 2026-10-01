"""
Xylarium cohabitation: more than one people to a world - each in the niche its biology can use.

A world is not one habitat. Where each metabolism can live on it follows from physics:

  gas giants   plasmic life in the depths (the giant's own heat); carbon life only on platforms it builds in
               the cloud-tops (habitats)
  rocky worlds carbon life on the surface; lithotrophs in the crust; Stillcold life in ice and the oceans under
               it (ice and ocean worlds); plasmic life in a volcanic world's magma
  elsewhere    nowhere

The world's own people keeps its niche and its government. Another people may live beside it in a niche it does
not use, as a COMMUNITY: it harvests its own niche (the same carrying-capacity physics, biosphere.py, for its own
metabolism), eats its staple from the world's stores, and gives back its chemistry's waste (staples.excrete) - where
any resident whose staple it is eats it. That is the whole of on-world exchange: shared stores, no freight.

WHAT EACH IS TO THE OTHER is measured, never assigned: for each community and its host, the effect of the other on
how many of it the world can feed - the other's waste that feeds it (in people), less the niche they share and the
staple they both eat. The signs say what they are: (+,+) mutualism, (+,-) one feeds on the other, (-,-)
competition, (0,0) indifference. A carbon people's platforms over a plasmic giant, the plasmic people's helium-3
ash and the carbon people's respired water - whatever the chemistry makes of them.

SETTLING. A people with yards whose world is crowded may ask to settle a free niche on an inhabited
world in its reach. The host accepts or refuses by the one rule (decide.agree), each side judging through how well
it understands the other (contact.misread): the host weighs what the newcomers' waste and presence would bring it
against what they would take; the newcomers weigh the room. Communities make their people and their host each
other's closest contacts (contact.py).
"""

from typing import Any, Dict, List, Optional, Tuple

from xylarium.config import FOOD_PER_THOUSAND, METABOLIC_WASTE, STAPLES


def _quarter() -> int:
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    return FISCAL_QUARTER_CYCLES


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "cohabit")


def _giant(planet: Any) -> bool:
    from xylarium.kernel import physics
    return planet.planet_type == "GAS_GIANT" or bool(physics.body(planet).get("giant"))


def niche(planet: Any, metab: str) -> Optional[str]:
    """Where on this world a metabolism can live, if anywhere."""
    if _giant(planet):
        return {"plasmic": "depths", "biotic": "cloudtops", "umbral": "cloudtops"}.get(metab)
    if metab in ("biotic", "umbral"):
        return "surface"
    if metab == "mineral":
        return "crust"
    if metab == "cryogenic":
        return "ice" if planet.planet_type in ("ICE", "OCEANIC") else None
    if metab == "plasmic":
        return "magma" if planet.planet_type == "VOLCANIC" else None
    return None


def communities(planet: Any) -> List[Dict[str, Any]]:
    return planet.society.setdefault("communities", [])


def host_niche(kernel: Any, planet: Any) -> Optional[str]:
    from xylarium.kernel import biosphere
    return niche(planet, biosphere.metabolism_of(kernel, planet))


def capacity(kernel: Any, planet: Any, metab: str) -> int:
    """How many of a metabolism this world's niche for it can feed (biosphere physics for that metabolism)."""
    n = niche(planet, metab)
    if n is None:
        return 0
    from xylarium.kernel import biosphere
    return int(biosphere.carrying_capacity(kernel, planet, metabolism=metab))


def _need_q(pop: int) -> int:
    return int(pop * FOOD_PER_THOUSAND * _quarter() / 1000)


def _waste_q(pop: int) -> int:
    from xylarium.config import WASTE_SHARE
    a, _, b = WASTE_SHARE.partition("/")
    return int(_need_q(pop) * float(a) / float(b or 1))


def effect(eater_metab: str, eater_niche: Optional[str], eater_k: int, other_metab: str,
           other_niche: Optional[str], other_pop: int) -> float:
    """How many more (or fewer) of the eater the world feeds because the other lives there: the other's waste
    that is the eater's staple (in people a season), less a share of the niche if they share it, less the staple
    they both eat."""
    staple = STAPLES.get(eater_metab, "ORGANICS")
    fed = _waste_q(other_pop) / max(1e-9, _need_q(1000) / 1000.0) if METABOLIC_WASTE.get(other_metab) == staple else 0.0
    crowd = min(other_pop, eater_k) if (eater_niche is not None and eater_niche == other_niche) else 0.0
    rival = other_pop if STAPLES.get(other_metab) == staple else 0.0
    return fed - crowd - 0.5 * rival


def kind_of(a: float, b: float) -> str:
    sa, sb = (a > 0) - (a < 0), (b > 0) - (b < 0)
    if sa > 0 and sb > 0:
        return "mutualism"
    if sa < 0 and sb < 0:
        return "competition"
    if (sa > 0 and sb < 0) or (sa < 0 and sb > 0):
        return "predation"
    if sa == 0 and sb == 0:
        return "neutral"
    return "commensalism" if (sa > 0 or sb > 0) else "amensalism"


# ---------------------------------------------------------------------- the season
def quarter(kernel: Any) -> List[str]:
    from xylarium.kernel import biosphere, fertility, staples
    st = stats(kernel)
    logs: List[str] = []
    kinds: Dict[str, int] = {}
    for sec in kernel.sectors.values():
        for p in sec.planets:
            cs = p.society.get("communities")
            if not cs:
                continue
            host_metab = biosphere.metabolism_of(kernel, p)
            host_n = niche(p, host_metab)
            host_k = max(1, int(biosphere.carrying_capacity(kernel, p)))
            keep = []
            for c in cs:
                m, pop = c["metab"], int(c["pop"])
                k = capacity(kernel, p, m)
                if c["niche"] == host_n:
                    k = max(0, k - p.population)          # a shared niche is shared
                staple = STAPLES.get(m, "ORGANICS")
                need = _need_q(pop)
                grown = staples.add(p, staple, min(need, _need_q(k)), "harvest") if staple != "ORE" else \
                    _graze(p, min(need, _need_q(k)))
                eaten = staples.take(p, staple, need, "eaten")
                staples.excrete(p, m, eaten)
                if eaten >= need:
                    room = k + effect(m, c["niche"], k, host_metab, host_n, p.population)
                    growth = fertility.birth_share_quarter() * pop * max(-1.0, 1.0 - pop / max(1.0, room))
                    pop = max(0, pop + int(growth))
                else:
                    pop = int(pop * eaten / max(1, need))       # what it could not feed, it does not keep
                c["pop"] = pop
                a = effect(m, c["niche"], k, host_metab, host_n, p.population)
                b = effect(host_metab, host_n, host_k, m, c["niche"], pop)
                c["kind"] = kind_of(round(a, 3), round(b, 3))
                kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
                if pop > 0:
                    keep.append(c)
                else:
                    st["vanished"] += 1
            p.society["communities"] = keep
    st["kinds"] = kinds
    if (kernel.cycle_count // _quarter()) % 4 == 0:
        logs += _settle(kernel)
    return logs


def _graze(planet: Any, n: int) -> int:
    from xylarium.kernel import geology
    return geology.mine_crust(planet, n)


# ---------------------------------------------------------------------- settling
def _settle(kernel: Any) -> List[str]:
    """Crowded peoples with yards and no free world look for a free niche on someone else's world in reach."""
    from xylarium.config import DAUGHTER_EMIGRANT_SHARE, DAUGHTER_EMIGRANTS_MAX, DAUGHTER_EMIGRANTS_MIN
    from xylarium.kernel import biosphere, contact, decide, demography, sustenance, topology
    from xylarium.kernel.demography import _tax_per_head_quarter
    logs: List[str] = []
    st = stats(kernel)
    for sec in kernel.sectors.values():
        for src in sec.planets:
            if src.population <= 0 or getattr(src, "natives", None) or not sustenance.yards(src):
                continue
            if src.population < demography.housing_cap(src, kernel) * 0.9:
                continue                                   # it is not pressed for room at home
            me = sustenance.people_of(src)
            m = biosphere.metabolism_of(kernel, src)
            best = None
            for sid in topology.reach(kernel, src.sector_id, demography.settler_reach(kernel, src)):
                for host in kernel.sectors[sid].planets:
                    if host is src or host.population <= 0 or getattr(host, "natives", None):
                        continue
                    hn, n = host_niche(kernel, host), niche(host, m)
                    if n is None or n == hn or sustenance.people_of(host) == me:
                        continue
                    if any(c["people"] == me for c in communities(host)) or any(c["niche"] == n for c in communities(host)):
                        continue
                    k = capacity(kernel, host, m)
                    if k > 0 and (best is None or k > best[1]):
                        best = (host, k, n)
            if best is None:
                continue
            host, k, n = best
            them = sustenance.people_of(host)
            settlers = min(DAUGHTER_EMIGRANTS_MAX, int(src.population * DAUGHTER_EMIGRANT_SHARE), k // 2)
            if settlers < DAUGHTER_EMIGRANTS_MIN:
                continue
            host_metab = biosphere.metabolism_of(kernel, host)
            gain_host = effect(host_metab, host_niche(kernel, host), max(1, demography.housing_cap(host, kernel)),
                               m, n, settlers)
            understood = contact.intelligibility(kernel, me, them)
            ms = contact.misread(decide.mind_of_planet(kernel, src), understood)
            mh = contact.misread(decide.mind_of_planet(kernel, host), understood)
            per_head_src = _tax_per_head_quarter(src)
            per_head_host = _tax_per_head_quarter(host)
            settler_side = decide.option("settle", decide.worth(kernel, 0.0, ms),
                                         decide.worth(kernel, settlers * per_head_src, ms))
            host_side = decide.option("host", decide.worth(kernel, max(0.0, -gain_host) * per_head_host, mh),
                                      decide.worth(kernel, max(0.0, gain_host) * per_head_host, mh))
            if not decide.agree(kernel, settler_side, host_side, ms, mh, me, them, "cohabit"):
                st["refused"] += 1
                continue
            src.population -= settlers
            communities(host).append({"people": me, "metab": m, "pop": settlers, "niche": n,
                                      "since": kernel.cycle_count, "origin": src.id})
            st["founded"] += 1
            from xylarium.kernel import primordial
            primordial.first(kernel, "first_shared_world", f"{me} in the {n} of {host.name}")
            logs.append(f"[COHABIT] {settlers:,} of {src.name}'s people settle the {n} of {host.name}.")
    return logs


def pairs(kernel: Any) -> List[Tuple[str, str, int]]:
    """(community people, host people, community population) for every shared world - for contact.py."""
    from xylarium.kernel import sustenance
    out = []
    for sec in kernel.sectors.values():
        for p in sec.planets:
            for c in p.society.get("communities") or []:
                host = sustenance.people_of(p)
                if host and c["people"] != host:
                    out.append((c["people"], host, int(c["pop"])))
    return out


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    shared = [p for s in kernel.sectors.values() for p in s.planets if p.society.get("communities")]
    return {"shared_worlds": len(shared),
            "communities": sum(len(p.society["communities"]) for p in shared),
            "people_in_communities": sum(int(c["pop"]) for p in shared for c in p.society["communities"]),
            "kinds": dict(st.get("kinds", {})), "founded": st["founded"], "refused": st["refused"],
            "vanished": st["vanished"]}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="cohabit",
    state=lambda: {"founded": 0, "refused": 0, "vanished": 0, "kinds": {}},
    season=quarter,
    summary=summary,
))
