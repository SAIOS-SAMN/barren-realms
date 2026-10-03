"""
Xylarium memory: what a people keeps of its own past, in the media it can make - and how what it keeps decays,
drifts and becomes myth.

Two records exist and they are never the same. The ledger (history.py) is what happened: the universe's own record,
which the steward reads and no one inside the universe does. A people's memory is what it has kept: the events it
witnessed, written into whatever it can write on, copied by the minds it has, through what befell it. A steward
knows the ledger; a people knows only its memory.

A RECORD is information carried through a medium against erasure - the same physics as life's ladder (life.py).
Each medium has a capacity, a retention (the half-life of a record left alone) and an error per copy:

  ORAL        living memory, told generation to generation; enacted memory where the creed fixes the telling (rite:
              dance and display under a sky of light, scent laid in rites for a chemical mind, resonance for one
              that lives by heat and pressure, patterned fields). Each generation's telling changes it by the
              floating gap's measure (TELL_ERR), spared by a collective's pooling (knowledge.POOLED_KEEP), fixed by
              the creed's hold, loosened by creativity (openness and a plastic mind).
  INSCRIBED   marks on the world itself - cut rock, grown shell and reef, ice laid in layers, fused stone - for a
              people that stays (farming). Long-lived: its half-life is weathering's (Arrhenius, from the world's own
              temperature: a cold world keeps its marks almost forever, a hot one loses them).
  PORTABLE    thin cheap sheets - grown, woven, chemical films, fired tablets - for a people with a state's
              specialists. Roomy, short-lived (organic hydrolysis, from the world's temperature), copied often.
  MACHINE     records in thinking machines (computation): vast and nearly faithful while tended, and lost first when
              a people falls.
  SELF        records written into bodies and minds (genetics, transfer): generations long, nearly faithful.

A tended record is copied before it decays (every half-life halved), each copy adding its medium's error. Below
MYTH_LINE (half of what it says is no longer what happened) a record is told as MYTH: compressed (names fall away to
"strangers", times to "long ago"), its causes become intentions (a sun's will where the creed holds, no one's where
it does not), and its gaps are filled from the people's own imagination (the many as one hero for a collective, a
single hero for the long-lived, the deep, the cold, the fire). Myths of one tale merge: a people tells one story of
brother against brother, however often it has turned on itself. Below LOST_LINE nothing of it is left.

A people that becomes another (genome.speciate) takes its parent's memory with it; from then on each tells its own
variants. A people that falls or dies leaves what it inscribed on the world it last lived on; a people that later
lives there and can read reads it again (REDISCOVERY) - lore, kept at what translation leaves of it. A people's
gaining a new medium is itself history (RECORDKEEPING): the deep past it has not yet lost is copied into it, and its
myths become fixed (canon).
"""

import math
from typing import Any, Dict, List, Optional

TELL_ERR = 0.18                 # meaning changed per generation of tellers: oral tradition's floating gap (detail
                                # thins past three or four generations: Vansina) - half lost in ~3.5 generations
MYTH_LINE = 0.5                 # below this fidelity a record is told as myth
LOST_LINE = 0.05                # below this nothing of it is left
KB_EV = 8.617e-5                # Boltzmann, eV/K
T_REF = 288.0                   # K, where the substrates' half-lives below are measured
MEDIA = {                       # half-life (years, at T_REF, untended), activation energy (eV), error per copy,
    "inscribed": {"half": 1.0e4, "ea": 0.62, "eps": 0.02, "cap": 60},     # capacity (records). Weathering of a
    "portable": {"half": 300.0, "ea": 1.04, "eps": 0.01, "cap": 200},     # cut mark (~60 kJ/mol, worlds.WEATHER_E_K);
    "machine": {"half": 30.0, "ea": 0.0, "eps": 1e-6, "cap": 400},        # organic hydrolysis (~100 kJ/mol);
    "self": {"half": 1.0e3, "ea": 0.0, "eps": 1e-4, "cap": 400},          # media and formats; written heredity
}                                                                         # (self's half-life in generations)
ORAL_CAP = 24                   # what a people's tellers carry (rites hold as many as the creed keeps)
ARCHIVE_BURN = 0.5              # the share of a written archive a people's strife or conquest burns
WITNESSED = ("EMERGENCE", "DEEP_HISTORY", "ERA", "STATEHOOD", "FARMING", "ASCENT", "FTL_CROSSED", "CAPABILITY",
             "TURNING", "STRIFE", "EPIDEMIC", "KINSHIP", "KIN_EATEN", "SCHISM", "TRANSFER_FORBIDDEN",
             "TRANSFER_EMBRACED", "DOMINION", "GALACTIC_WAR", "WAR", "CONQUEST", "REVOLT", "SUBJUGATION",
             "REBELLION", "CONTACT", "SEEDING", "SETTLEMENT", "EXODUS", "WORLD_STRIPPED", "WORLD_SHATTERED")
BURNS = ("STRIFE", "CONQUEST", "SUBJUGATION")
TALES = {                       # what a record keeps once it is told as myth: its core, in the people's own sky
    "STRIFE": "brother rose against brother under the {colour} sun",
    "WAR": "the {them} came for what was theirs, and they fought",
    "GALACTIC_WAR": "the {them} came out of the dark between the suns, and the sky burned",
    "CONQUEST": "strangers from the sky took their world",
    "SUBJUGATION": "the {them} held them by force, and they paid",
    "REVOLT": "they threw the strangers back into the sky",
    "REBELLION": "they broke the {them}'s hold",
    "CONTACT": "the {them} first came out of the dark, speaking in a tongue no one knew",
    "DOMINION": "their worlds and the {them}'s touched among the stars",
    "EMERGENCE": "they first looked up, and the {colour} sun looked back",
    "DEEP_HISTORY": "they lived a long age before anything was remembered",
    "FARMING": "the first seed was put into the ground",
    "STATEHOOD": "the first store was raised and the first share was taken",
    "ERA": "they {did}",
    "ASCENT": "they folded the dark and walked between the suns",
    "FTL_CROSSED": "they folded the dark and walked between the suns",
    "CAPABILITY": "they were given {what}",
    "TURNING": "they turned from one way to another",
    "EPIDEMIC": "a sickness walked out of the crowded places",
    "KINSHIP": "the ones they ate looked back at them and spoke",
    "KIN_EATEN": "they ate those who would have been their kin",
    "SCHISM": "the people was cut in two over its kin",
    "TRANSFER_FORBIDDEN": "they were forbidden to leave their bodies",
    "TRANSFER_EMBRACED": "they left their bodies and lived on",
    "SEEDING": "they sowed life on a world that had none",
    "SETTLEMENT": "the first ones crossed to another world",
    "EXODUS": "they fled a dying sun",
    "WORLD_STRIPPED": "a world was stripped to the bone",
    "WORLD_SHATTERED": "a world was broken",
    "famine": "the {colour} sun turned its face away, and the fields gave nothing",
    "blight": "a sickness walked out of the crowded places, and the {colour} sun did not stop it",
    "bombarded": "fire fell from the dark between the stars",
    "sky": "the sky itself thinned, and the {colour} sun's breath reached the ground",
    "sun": "the {colour} sun grew great and hungry, and burned the fields it had fed",
}
DID = {"farm": "first put seed into the ground", "state": "raised the first store and took the first share",
       "works": "raised the first great works", "yards": "built ships that could reach the sky",
       "crossed": "folded the dark and walked between the suns"}


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "memory")


def _on(kernel: Any) -> bool:
    return kernel is not None and hasattr(kernel, "state")


def _of(kernel: Any, who: str) -> Dict[str, Any]:
    return stats(kernel)["of"].setdefault(who, {"records": [], "media": ["oral"], "years": None, "home": None,
                                                "myths": 0})


# ---------------------------------------------------------------------- the people and its world
def _home(kernel: Any, who: str) -> Optional[Any]:
    from xylarium.kernel import relations
    worlds = relations._peoples(kernel).get(who)
    return max(worlds, key=lambda p: p.population) if worlds else None


def _traits(planet: Any) -> Dict[str, Any]:
    civ = getattr(planet, "civilization", None)
    return dict(getattr(civ, "traits", None) or {}) if civ is not None else {}


def _world_t(planet: Any) -> float:
    """The temperature the people's records sit in: its own body's medium (cosmos.select: body_t)."""
    try:
        return max(20.0, float(_traits(planet).get("body_t") or T_REF))
    except (TypeError, ValueError):
        return T_REF


def half_life(medium: str, temp_k: float, gen_years: float = 25.0) -> float:
    """A medium's half-life, untended, in years at a world's temperature (Arrhenius against T_REF)."""
    m = MEDIA[medium]
    if medium == "self":
        return m["half"] * gen_years
    x = m["ea"] / KB_EV * (1.0 / temp_k - 1.0 / T_REF)
    return m["half"] * math.exp(max(-50.0, min(50.0, x)))


def _years(kernel: Any, who: str) -> float:
    """The people's own years: those lived on the clock and those lived in its annals."""
    lived = kernel.cycle_count / 100.0
    if "annals" in kernel.state:
        from xylarium.kernel import annals
        lived += float((annals.stats(kernel)["of"].get(who) or {}).get("advanced", 0.0))
    return lived


def _gen(kernel: Any, planet: Any) -> float:
    from xylarium.kernel import fertility
    try:
        return max(1.0, fertility.generation_of(kernel, planet))
    except Exception:
        return 25.0


def _passed(kernel: Any, who: str, planet: Any) -> List[str]:
    out = []
    if "annals" in kernel.state:
        from xylarium.kernel import annals
        out = list((annals.stats(kernel)["of"].get(who) or {}).get("passed", []))
    way = (getattr(planet, "society", None) or {}).get("way")
    if way in ("farm", "state"):
        out.append("farm")
    if way == "state":
        out.append("state")
    return out


def media(kernel: Any, who: str, planet: Any, stages: Optional[List[str]] = None) -> List[str]:
    """The media a people can keep its past in, from what it has become: oral from the first day; marks on its world
    once it stays (and has a body to make them: a mind held in fields first needs a vessel); thin sheets once a state
    frees specialists; machines once it computes; its own heredity once it writes it."""
    from xylarium.kernel import technology
    passed = _passed(kernel, who, planet) if stages is None else stages
    has = lambda cap: "technology" in kernel.state and technology.has(kernel, who, cap)   # noqa: E731
    out = ["oral"]
    embodied = True
    try:
        embodied = technology.embodied(kernel, who, planet)
    except Exception:
        pass
    if embodied and any(s in passed for s in ("farm", "state", "works", "yards", "crossed")):
        out.append("inscribed")
    if embodied and any(s in passed for s in ("state", "works", "yards", "crossed")):
        out.append("portable")
    if stages is None and has("computation"):
        out.append("machine")
    if stages is None and (has("genetics") or has("transfer")):
        out.append("self")
    return out


def substrate(planet: Any, medium: str) -> str:
    """What a medium is made of on this world, for this kind of life."""
    t = _traits(planet)
    metab = str(getattr(getattr(planet, "civilization", None), "metabolism", "") or t.get("metab", ""))
    sense = t.get("sense", "light")
    medium_of_life = str(t.get("medium", ""))
    aquatic = t.get("form") in ("swimming", "drifting") or "under ice" in medium_of_life or "dark" in medium_of_life
    if medium == "oral":
        return {"light": "dance and display", "chemistry": "scent laid in rites", "heat and pressure":
                "resonance kept in rites", "heat": "heat rites", "fields": "patterned fields"}.get(sense, "telling")
    if medium == "inscribed":
        return ("grown shell and reef" if aquatic else "ice laid in layers" if metab == "cryogenic" else
                "field patterns frozen in matter" if metab == "plasmic" else "fused and cut stone"
                if metab == "mineral" else "marks cut into rock")
    if medium == "portable":
        return ("chemical films" if aquatic else "frozen threads" if metab == "cryogenic" else
                "charged foils" if metab == "plasmic" else "fired tablets" if metab == "mineral" else
                "grown sheets and woven fibre")
    if medium == "machine":
        return "thinking machines"
    return "its own heredity"


def _creativity(kernel: Any, planet: Any) -> float:
    from xylarium.kernel import mind, society
    prof = mind.profile(kernel, planet)
    return max(0.0, min(1.0, 0.5 * prof["plastic"] + 0.5 * society.openness(planet)))


def oral_err(kernel: Any, planet: Any) -> float:
    """Meaning changed per generation of tellers."""
    from xylarium.kernel import knowledge, mind
    prof = mind.profile(kernel, planet)
    dogma = float(getattr(getattr(planet, "civilization", None), "dogma", 0.0) or 0.0)
    return TELL_ERR * (1.0 - knowledge.POOLED_KEEP * prof["collective"]) * (1.0 - dogma) * \
        (0.5 + _creativity(kernel, planet))


def _rate(rec: Dict[str, Any], planet: Any, gen: float, oral: float) -> float:
    """How fast a record's fidelity falls: its log per year (a myth, compressed, is retold and copied with half the
    error)."""
    m = rec["m"]
    if m == "oral":
        eps, period = oral, gen                                      # one telling per generation
    else:
        eps, period = MEDIA[m]["eps"], 0.5 * half_life(m, _world_t(planet), gen)   # copied before it decays
    if rec.get("myth"):
        eps *= 0.5
    return -math.log(max(1e-12, 1.0 - min(0.999999, eps))) / max(1e-9, period)


def _decay(kernel: Any, rec: Dict[str, Any], years: float, planet: Any, gen: float, oral: float) -> None:
    rec["f"] *= math.exp(-_rate(rec, planet, gen, oral) * years)


def _age(kernel: Any, who: str, home: Any, rec: Dict[str, Any], years: float, gen: float, oral: float) -> None:
    """Age a record by a people's years: if it crosses into myth on the way it is told as myth there, and drifts on
    as a myth for the rest."""
    lam = _rate(rec, home, gen, oral)
    if not rec.get("myth") and rec["f"] >= MYTH_LINE and lam > 0:
        to_line = math.log(rec["f"] / MYTH_LINE) / lam
        if to_line < years:
            rec["f"] = MYTH_LINE * 0.999999
            _mythify(kernel, who, home, rec)
            if rec not in _of(kernel, who)["records"]:
                return                                               # merged into the myth it already tells
            years -= to_line
            lam = _rate(rec, home, gen, oral)
    rec["f"] *= math.exp(-lam * years)


def _best(media_: List[str]) -> str:
    for m in ("machine", "self", "portable", "inscribed"):
        if m in media_:
            return m
    return "oral"


def _cap(media_: List[str]) -> int:
    return max([ORAL_CAP] + [MEDIA[m]["cap"] for m in media_ if m in MEDIA])


def _weight(rec: Dict[str, Any]) -> float:
    return (1.0 + math.log10(1.0 + max(0.0, float(rec.get("mag") or 0)))) * rec["f"]


# ---------------------------------------------------------------------- witnessing
def witness(kernel: Any, ev: Dict[str, Any]) -> None:
    """An event a people lived through becomes a record in its best medium - or none, if it has no one to keep it."""
    if not _on(kernel) or not ev or ev.get("kind") not in WITNESSED:
        return
    for who in ev.get("actors") or []:
        if not str(who).startswith("civ:"):
            continue
        home = _home(kernel, who)
        if home is None:
            continue
        _write(kernel, who, home, ev)


def _write(kernel: Any, who: str, home: Any, ev: Dict[str, Any], f0: float = 1.0) -> Optional[Dict[str, Any]]:
    mem = _of(kernel, who)
    data = ev.get("data") or {}
    them = next((a for a in ev.get("actors") or [] if a != who), None)
    rec = {"id": ev.get("id"), "k": ev.get("kind"), "title": ev.get("title", ""), "year": ev.get("year"),
           "mag": ev.get("magnitude") or 0, "f": f0, "them": them.split(":", 1)[-1] if them else None,
           "stage": data.get("stage"), "cap": data.get("capability") or data.get("cap"), "m": _best(mem["media"])}
    if ev.get("kind") in BURNS:
        _burn(kernel, who, home)
    epoch = data.get("epoch")
    if epoch is not None and "clocks" in kernel.state:      # lived in the annals: it happened long ago
        from xylarium.kernel import clocks
        ago = max(0.0, (clocks.now(kernel, who) - float(epoch)) * 1e9)
        if ago > 0:
            stages = _passed(kernel, who, home)
            if data.get("stage") in stages:
                stages = stages[:stages.index(data["stage"]) + 1]
            then = media(kernel, who, home, stages)
            rec["m"] = _best(then)
            _decay(kernel, rec, ago, home, _gen(kernel, home), oral_err(kernel, home))
            if _best(mem["media"]) != rec["m"] and rec["f"] >= LOST_LINE:
                rec["m"] = _best(mem["media"])                 # what survived has since been copied into the new
    if rec["f"] < LOST_LINE:
        stats(kernel)["lost"] += 1
        return None
    mem["records"].append(rec)
    stats(kernel)["written"] += 1
    _mythify(kernel, who, home, rec)
    _forget(kernel, who)
    return rec


def blow(kernel: Any, planet: Any, kind: str, explained: float) -> None:
    """A blow a people cannot explain is myth from its first telling: it keeps of it only what it understands."""
    from xylarium.kernel import knowledge
    who = knowledge.holder_of_planet(planet)
    if not who or not str(who).startswith("civ:"):
        return
    mem = _of(kernel, who)
    if any(_key(r) == _key({"k": kind}) for r in mem["records"]):
        return                                                       # it already tells of this
    ev = {"id": None, "kind": kind, "title": kind, "year": round(kernel.cycle_count / 100.0, 2), "actors": [who]}
    _write(kernel, who, planet, ev, f0=max(LOST_LINE, min(1.0, explained)))


def _burn(kernel: Any, who: str, home: Any) -> None:
    """Strife and conquest burn the written archive: what burns survives only as far as it is still told."""
    mem = _of(kernel, who)
    written = [r for r in mem["records"] if r["m"] == "portable"]
    written.sort(key=_weight)
    for r in written[:int(len(written) * ARCHIVE_BURN)]:
        r["m"] = "oral"
        stats(kernel)["burned"] += 1


def _forget(kernel: Any, who: str) -> None:
    mem = _of(kernel, who)
    cap = _cap(mem["media"])
    if len(mem["records"]) > cap:
        mem["records"].sort(key=lambda r: -_weight(r))
        stats(kernel)["forgotten"] += len(mem["records"]) - cap
        del mem["records"][cap:]
        mem["records"].sort(key=lambda r: float(r.get("year") or 0))


# ---------------------------------------------------------------------- myth
SAME_TALE = {"blight": "EPIDEMIC", "FTL_CROSSED": "ASCENT"}     # one happening, told one way


def _key(rec: Dict[str, Any]) -> str:
    return f"{SAME_TALE.get(rec['k'], rec['k'])}:{rec.get('stage') or ''}"


def truth(rec: Dict[str, Any]) -> float:
    """How much of what happened a record still says: a myth's truth was fixed when it became one, and it keeps
    only as much of it as the story itself survives."""
    return rec["f"] * rec["truth"] if rec.get("myth") else rec["f"]


def tell(kernel: Any, planet: Any, rec: Dict[str, Any]) -> str:
    """A record told as myth: its core in the people's own sky, compressed, given a will, and filled in by the
    people's imagination."""
    from xylarium.kernel import fertility, mind, society
    sky = society._sky(kernel, planet)
    core = TALES.get(rec["k"], "something happened that no one could explain")
    them = rec.get("them") if truth(rec) >= 0.3 else None              # names are the first thing a story loses
    core = core.format(colour=sky["colour"], them=them or "strangers", did=DID.get(rec.get("stage"), "changed"),
                       what=rec.get("cap") or "a gift")
    core = core.replace("the strangers's", "the strangers'")
    dogma = float(getattr(getattr(planet, "civilization", None), "dogma", 0.0) or 0.0)
    prof = mind.profile(kernel, planet)
    will = ("because the sky willed it" if dogma > 0.5 else "and no one can say why" if dogma < 0.2 else
            "and the old ones knew why")
    strat = fertility.strategy(kernel, planet)
    hero = ("and the many moved as one" if prof["collective"] >= 0.5 else
            "and the swarm bore them through" if strat == "r" else "and one of them stood against it")
    where = ("in the deep" if prof["aquatic"] else "in the long cold" if getattr(planet.civilization, "metabolism", "")
             == "cryogenic" else "")
    when = "in the first days" if truth(rec) < 0.15 else "long ago"
    moons = sky["moons"]
    witness = ("the moon looked on and said nothing" if moons == 1 else
               f"its {moons} moons looked on and said nothing" if moons > 1 else "and there was no moon to see it")
    return f"{when}{' ' + where if where else ''}, {core}, {will}; {hero}; {witness}"


def _mythify(kernel: Any, who: str, home: Any, rec: Dict[str, Any]) -> None:
    """A record that has drifted below the line is told as myth - or merges into the myth the people already tells
    of that tale."""
    if rec.get("myth") or rec["f"] >= MYTH_LINE:
        return
    from xylarium.kernel import history, relations
    mem = _of(kernel, who)
    key = _key(rec)
    same = next((r for r in mem["records"] if r is not rec and r.get("myth") and _key(r) == key), None)
    if same is not None:                                              # one tale, however often it happened
        same["merged"] = int(same.get("merged", 0)) + 1
        same["mag"] = max(float(same.get("mag") or 0), float(rec.get("mag") or 0))
        mem["records"].remove(rec)
        stats(kernel)["merged"] += 1
        return
    rec["told"] = tell(kernel, home, rec)
    rec["myth"] = True
    rec["truth"] = rec["f"]                                           # what it still says of what happened;
    rec["f"] = 1.0                                                    # from now on the story's own survival
    mem["myths"] += 1
    stats(kernel)["myths"] += 1
    people = getattr(home.civilization, "name", home.name)
    worlds = len(relations._peoples(kernel).get(who, [])) or 1
    out = history.event(kernel, "MYTH", f"The {people} tell how {rec['told'].split(',')[1].strip()}",
                        actors=[who], planet=home, refs=[x for x in (rec.get("id"),) if x],
                        text=f"The {people} say that {rec['told']}.",
                        data={"myth": rec["k"], "remembers": rec.get("id"), "fidelity": round(rec["truth"], 3),
                              "medium": substrate(home, rec["m"]), "worlds": worlds,
                              "variant_of": rec.get("of")})
    rec["myth_id"] = out.get("id")
    chron = getattr(kernel, "chronicle", None)
    if chron is not None:
        chron.record(kernel, "MYTH", home.id, people, f"The {people} tell how {rec['told'].split(',')[1].strip()}",
                     f"The {people} say that {rec['told']}.", sector_id=home.sector_id, tags=["myth", rec["k"]])
    from xylarium.kernel import primordial
    primordial.first(kernel, "first_myth", f"{people}: {rec['k']}")


def myths(kernel: Any, who: Optional[str]) -> List[Dict[str, Any]]:
    """The myths a people tells now, oldest first (what its steward hears it say)."""
    if not who or not _on(kernel) or "memory" not in kernel.state:
        return []
    return [{"id": r.get("myth_id"), "kind": r["k"], "year": r.get("year"), "text": r.get("told", ""),
             "fidelity": round(truth(r), 3), "merged": int(r.get("merged", 0)), "remembers": r.get("id")}
            for r in _of(kernel, who)["records"] if r.get("myth")]


def records(kernel: Any, who: Optional[str]) -> List[Dict[str, Any]]:
    if not who or "memory" not in kernel.state:
        return []
    return list(_of(kernel, who)["records"])


# ---------------------------------------------------------------------- inheritance and ruins
def inherit(kernel: Any, parent: Optional[str], child: Optional[str]) -> None:
    """A people that becomes another takes its parent's memory: from now on each tells its own variants."""
    if not parent or not child or parent == child or "memory" not in kernel.state:
        return
    src = stats(kernel)["of"].get(parent)
    if not src:
        return
    dst = _of(kernel, child)
    have = {r.get("id") for r in dst["records"] if r.get("id")}
    for r in src["records"]:
        if r.get("id") in have and r.get("id"):
            continue
        c = dict(r)
        c["of"] = r.get("myth_id") or r.get("id")
        c.pop("myth_id", None)
        dst["records"].append(c)
    dst["media"] = list(dict.fromkeys(dst["media"] + src["media"]))
    dst["myths"] = sum(1 for r in dst["records"] if r.get("myth"))


def _leave(kernel: Any, who: str, mem: Dict[str, Any]) -> None:
    """A people gone leaves what it inscribed on the world it last lived on."""
    st = stats(kernel)
    left = [r for r in mem["records"] if r["m"] == "inscribed"]
    if left and mem.get("home") is not None:
        site = st["left"].setdefault(str(mem["home"]), [])
        for r in left:
            site.append({"people": who.split(":", 1)[-1], "k": r["k"], "title": r.get("title", ""),
                         "year": r.get("year"), "f": r["f"], "truth": r.get("truth", 1.0),
                         "substrate": mem.get("substrate", "marks"),
                         "myth": bool(r.get("myth")), "told": r.get("told")})
        del site[:-40]
    st["peoples_gone"] += 1


def _read_ruins(kernel: Any, who: str, worlds: List[Any]) -> List[str]:
    """A people that can read finds what another left on its worlds."""
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import history, knowledge, laws
    st = stats(kernel)
    info = laws.mastery(knowledge.experience(kernel, who, "information"), KNOWLEDGE_UNIT)
    if info < 0.2:
        return []
    logs = []
    for w in worlds:
        site = st["left"].get(str(w.id))
        if not site:
            continue
        others = [r for r in site if "civ:" + r["people"] != who]
        if not others:
            continue
        st["left"].pop(str(w.id), None)
        gone = sorted({r["people"] for r in others})
        name = getattr(w.civilization, "name", w.name)
        history.event(kernel, "REDISCOVERY", f"The {name} read what the {', '.join(gone)} left on {w.name}",
                      actors=[who], planet=w,
                      text=f"In {others[0]['substrate']} on {w.name} the {name} read of " +
                           "; ".join((r.get("told") or r["title"]) for r in others[:3]) + ".",
                      data={"from": gone, "records": len(others)})
        mem = _of(kernel, who)
        for r in others:                                             # lore: kept at what translation leaves of it
            mem["records"].append({"id": None, "k": r["k"], "title": r["title"], "year": r.get("year"),
                                   "mag": 0, "f": r["f"] * info, "truth": r.get("truth", 1.0),
                                   "them": r["people"], "m": _best(mem["media"]),
                                   "lore": r["people"], "myth": r.get("myth"), "told": r.get("told")})
        _forget(kernel, who)
        st["rediscovered"] += len(others)
        logs.append(f"[MEMORY] The {name} read the records the {', '.join(gone)} left on {w.name}.")
    return logs


# ---------------------------------------------------------------------- the season
def season(kernel: Any) -> List[str]:
    """Once a year: every people's records age by the years it has lived, are copied in its media, drift, become
    myth or are lost; new media are taken up; the gone leave their inscriptions; the living read others'."""
    from xylarium.kernel import history, relations
    if kernel.cycle_count % 100:
        return []
    st = stats(kernel)
    peoples = {w: ws for w, ws in relations._peoples(kernel).items() if str(w).startswith("civ:")}
    logs: List[str] = []
    for who in [w for w in st["of"] if w not in peoples]:
        _leave(kernel, who, st["of"].pop(who))
    for who in sorted(peoples):
        worlds = peoples[who]
        home = max(worlds, key=lambda p: p.population)
        mem = _of(kernel, who)
        mem["home"] = home.id
        now = _years(kernel, who)
        years = 0.0 if mem["years"] is None else max(0.0, now - mem["years"])
        mem["years"] = now
        have = media(kernel, who, home)
        new = [m for m in have if m not in mem["media"]]
        mem["media"] = have
        mem["substrate"] = substrate(home, "inscribed")
        best = _best(have)
        if new:
            name = getattr(home.civilization, "name", home.name)
            for r in mem["records"]:                                  # the past it still holds is copied in
                r["m"] = best
            history.event(kernel, "RECORDKEEPING", f"The {name} begin to keep their past in "
                          f"{' and '.join(substrate(home, m) for m in new)}",
                          actors=[who], planet=home, data={"media": have, "new": new,
                                                          "records": len(mem["records"])})
        if years > 0 and mem["records"]:
            gen, oral = _gen(kernel, home), oral_err(kernel, home)
            for r in list(mem["records"]):
                _age(kernel, who, home, r, years, gen, oral)
                if r not in mem["records"]:
                    continue
                if r["f"] < LOST_LINE:
                    mem["records"].remove(r)
                    st["lost"] += 1
                    continue
                _mythify(kernel, who, home, r)
        logs += _read_ruins(kernel, who, worlds)
    return logs


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    held = [len(m["records"]) for m in st["of"].values()]
    return {"peoples": len(held), "records": sum(held), "myths": st["myths"], "merged": st["merged"],
            "lost": st["lost"], "forgotten": st["forgotten"], "burned": st["burned"],
            "rediscovered": st["rediscovered"], "ruin_sites": len(st["left"])}


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(
    name="memory",
    state=lambda: {"of": {}, "left": {}, "written": 0, "myths": 0, "merged": 0, "lost": 0, "forgotten": 0,
                   "burned": 0, "rediscovered": 0, "peoples_gone": 0},
    season=season,
    summary=summary,
))
