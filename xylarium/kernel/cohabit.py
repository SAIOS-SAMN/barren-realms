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
    from xylarium.kernel import biosphere, fertility, knowledge, staples
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
                if c.get("carried"):                    # minds carried in vessels, not fed by the land
                    _teach(kernel, p, c)
                    keep.append(c)
                    continue
                m, pop = c["metab"], int(c["pop"])
                k = capacity(kernel, p, m)
                if c["niche"] == host_n:
                    k = max(0, k - p.population)          # a shared niche is shared
                staple = STAPLES.get(m, "ORGANICS")
                need = whole = _need_q(pop)
                if c.get("prey") and c["prey"] == knowledge.holder_of_planet(p) and p.population > 1:
                    need = _hunt(kernel, p, c, pop, need)          # what it takes of its host, it need not grow
                    _steer(kernel, p, c)                            # and a herd that asks no questions
                    _reset(kernel, p, c)                            # and a herd that learns too much is set back
                _own_work(kernel, c, pop, need / max(1, whole))     # the lives its own work sustains
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


def _own_work(kernel: Any, c: Dict[str, Any], pop: int, share: float) -> None:
    """A community's own work, a season of it, into its history (alignment.flow): the lives it feeds by what it grows
    rather than what it takes."""
    from xylarium.kernel import alignment, decide
    gen_years = max(1e-6, decide.mind(kernel, c.get("metab"))["horizon_q"] / 4.0)
    alignment.flow(c, light=pop * max(0.0, share) * (_quarter() / 100.0) / gen_years)


BODY_FEEDS_DAYS = 50.0          # days a body of like mass feeds an eater (daily intake ~2% of body mass)


def _hunt(kernel: Any, planet: Any, c: Dict[str, Any], pop: int, need: int) -> int:
    """A community that keeps its host's people as prey takes its diet's share of them - one of the handful of
    body plans its world feeds it on (kinship.PREY_PLANS) - a body feeding one of it for BODY_FEEDS_DAYS; what it
    takes it need not harvest. Each year the ledger records the lives taken (KIN_EATEN: a mind eaten by a mind)."""
    from xylarium.kernel import history, knowledge, kinship
    share = 1.0 / kinship.PREY_PLANS
    days = _quarter() / 100.0 * 365.25
    taken = min(planet.population - 1, int(pop * share * days / BODY_FEEDS_DAYS))
    if taken <= 0:
        return need
    if c.get("guarded_by"):
        return need                                      # a guardian stands between it and its prey
    planet.population -= taken
    from xylarium.kernel import alignment
    alignment.flow(c, dark=taken * kinship.MIND_EATEN)  # a life ended and a mind consumed
    c["eaten_year"] = int(c.get("eaten_year", 0)) + taken
    stats(kernel)["eaten"] = stats(kernel).get("eaten", 0) + taken
    if (kernel.cycle_count // _quarter()) % 4 == 3:
        history.event(kernel, "KIN_EATEN", f"The {c['people'].split(':', 1)[-1]} take "
                      f"{c['eaten_year']:,} of the {c['prey'].split(':', 1)[-1]}", actors=[c["people"], c["prey"]],
                      planet=planet, magnitude=c["eaten_year"],
                      cause="they keep the people they share a world with as food")
        c["eaten_year"] = 0
    return int(need * (1.0 - share))


def _steer(kernel: Any, planet: Any, c: Dict[str, Any]) -> None:
    """A people that keeps another as food tends its herd's creed: a herd that asks no questions does not find its
    keepers. Its hold on the creed grows over the herd's generation as far as the keepers are understood (their
    familiarity) - and against it the herd's own knowledge wears belief down (society._believe)."""
    from xylarium.kernel import contact, fertility
    civ = getattr(planet, "civilization", None)
    if civ is None:
        return
    fam = float(contact.stats(kernel)["familiarity"].get(contact._key(c["people"], c["prey"]), 0.0))
    if fam <= 0.0:
        return
    gen = fertility.generation_years(fertility.strategy(kernel, planet))
    season = min(1.0, (_quarter() / 100.0) / max(1e-6, gen))
    d = float(getattr(civ, "dogma", 0.0) or 0.0)
    civ.dogma = round(min(1.0, d + (1.0 - d) * fam * season), 4)
    stats(kernel)["steered"] = stats(kernel).get("steered", 0) + 1


RESET_TOLL = 0.1                # the share of a herd a keeper's setting-back costs it (cities fall, the many die;
                                # the bronze age's end - declared)
RESET_EVERY_GENERATIONS = 10.0  # a keeper cannot set its herd back again before it has grown again (declared)


def _reset(kernel: Any, planet: Any, c: Dict[str, Any]) -> None:
    """A keeper whose herd learns enough to find it sets the herd back: its works fall, its machines and writing are
    lost, its knowledge and its mathematics beyond the second axis go, and its creed is raised in what it lost -
    weighed by the keeper's council (its threat: what the herd knows and does not believe, against what the
    keeper loses of its food; only as far as the keeper leans Dark). The herd regrows; a keeper waits a span of the
    herd's generations before it can do it again."""
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import (alignment, decide, fertility, history, intellect, knowledge, laws, memory,
                                 technology)
    civ = getattr(planet, "civilization", None)
    herd = c.get("prey")
    if civ is None or not herd:
        return
    gen = fertility.generation_years(fertility.strategy(kernel, planet))
    if kernel.cycle_count - int(c.get("reset_cycle", -10 ** 12)) < RESET_EVERY_GENERATIONS * gen * 100:
        return
    dark = max(0.0, -float(c.get("alignment", 0.0)))
    info = laws.mastery(knowledge.experience(kernel, herd, "information"), KNOWLEDGE_UNIT)
    threat = info * (1.0 - float(getattr(civ, "dogma", 0.0) or 0.0))
    if dark <= 0.0 or threat <= 0.0:
        return
    sc = alignment.scales(kernel)
    lives = planet.population * sc["sol"] / max(1.0, sc["lives"])
    m = dict(decide.mind(kernel, c.get("metab")), holder=c["people"])
    if decide.choose(kernel, [decide.option("reset", lives * RESET_TOLL, lives * threat * dark)], m,
                     c["people"], "reset") is None:
        return
    c["reset_cycle"] = kernel.cycle_count
    lost = int(planet.population * RESET_TOLL)
    planet.population -= lost
    held = technology.stats(kernel)["of"].get(herd, {})
    gone = sorted(held)
    held.clear()                                          # back to sticks and stones
    planet.citadel_level = max(0, planet.citadel_level - 2)
    for d, v in list(knowledge.stocks(kernel, herd).items()):
        knowledge.stocks(kernel, herd)[d] = v * (1.0 - threat)
    v = intellect.stats(kernel)["vocab"].get(herd)
    if v is not None:
        intellect.stats(kernel)["vocab"][herd] = [x for x in v if intellect.RANK_OF.get(intellect.norm(x), 2) <= 2]
    memory._burn(kernel, herd, planet)
    civ.dogma = round(min(1.0, float(civ.dogma or 0.0) + threat * (1.0 - float(civ.dogma or 0.0))), 4)
    alignment.flow(c, dark=lost)
    stats(kernel)["resets"] = stats(kernel).get("resets", 0) + 1
    history.event(kernel, "RESET", f"The {herd.split(':', 1)[-1]} are set back to sticks and stones",
                  actors=[herd], planet=planet, magnitude=lost,
                  cause="their cities fall, their writing and their machines are lost; no one among them knows why",
                  data={"lost": gone, "threat": round(threat, 3)})


def _teach(kernel: Any, planet: Any, c: Dict[str, Any]) -> None:
    """Carried minds teach the people they live among what it can understand, as far as they know each other: their
    mathematics (as far as it is grounded) and the sciences they practise (`arts`)."""
    from xylarium.kernel import contact, intellect, knowledge, scheduler
    host = knowledge.holder_of_planet(planet)
    if not host or not (c.get("vocab") or c.get("arts")) or c.get("silent"):
        return
    fam = float(contact.stats(kernel)["familiarity"].get(contact._key(c["people"], host), 0.0))
    if fam <= 0.0:
        return
    years = _quarter() / 100.0
    for domain in c.get("arts") or []:                 # the sciences they practise, taught as far as they are known
        knowledge.learn(kernel, host, domain, int(c["pop"]) / 1000.0 * knowledge.LIVED_SHARE * fam * years,
                        "taught by carried minds")
    v = intellect.stats(kernel)["vocab"].setdefault(host, list(intellect.BASE))
    held = {intellect.norm(x) for x in v}
    rng = scheduler.rng(kernel, "teach", c["people"], host, kernel.cycle_count)
    for crystal in c["vocab"]:
        cr = intellect.norm(crystal)
        if cr in held or not intellect.grounded(cr, held):
            continue
        if rng.random() < fam * (_quarter() / 100.0):
            v.append(cr)
            held.add(cr)
            intellect.stats(kernel)["stats"]["taught"] += 1


def residents(kernel: Any, sector_ids: Optional[set] = None) -> Dict[str, List[Any]]:
    """The peoples living as communities, by the worlds they live on (in the given systems, or anywhere)."""
    out: Dict[str, List[Any]] = {}
    for sec in kernel.sectors.values():
        if sector_ids is not None and sec.id not in sector_ids:
            continue
        for p in sec.planets:
            for c in p.society.get("communities") or []:
                out.setdefault(c["people"], []).append(p)
    return out


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
