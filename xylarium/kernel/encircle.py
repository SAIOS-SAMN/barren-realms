"""
Xylarium encirclement: a people that crosses inside another's dominion answers it - and is answered.

Nothing here is a trigger. When one people's crossing falls inside another's dominion (settling.meet), each weighs
what it can do by its own mind (decide.choose: the same weighing every choice takes), in the one unit both share - the
worlds it would hold when the encounter has run its course (the time the enclosed front would take to reach the
plane halfway between the two homes: the seam two fronts make when they grow in step).

WHO SPEAKS FIRST    the one whose ledger is lower (clocks.height: causally earlier) proposes; the other answers - not
                    by name or id. On a tie the enclosed speaks: it is the one whose condition changed. The two
                    worldlines are linked by the exchange (h = 1 + max).

THE ENCLOSED MAY    hold an ENCLAVE (keep the worlds its encloser cannot use: as it stands), seek an ALLIANCE (a bond:
                    its arrays bank with the encloser's coalition), JOIN the encloser (absorption: a people transfer,
                    never a deletion), CONTEST (war for the halfway seam), or LEAP (kindle a gateway and settle beyond
                    the encloser's front, paid from its own banked energy).
THE ENCLOSER MAY    TOLERATE (the enclave), OFFER an alliance, DEMAND absorption, or EXPEL (war).
THE ANSWER          the one answering weighs accepting the proposal against its own options; what needs the other's
                    consent and is refused leaves the enclave as it stands, and war is always open to either side.

WAR                 Lanchester's square law at the seam: each side's strength is the worlds it holds where it is fought.
                    The encloser's margin about the enclosed home was settled when its front passed there (tau ago);
                    from one world its colonies have grown as e^(g tau), never past the room there - so a young margin
                    is weak and a developed one is not: war is viable only against undeveloped margins. The truth is
                    the law, not a die: the stronger keeps sqrt(1 - (weaker/stronger)^2) of its strength, the weaker
                    falls there. A mind weighs its odds as A^2 / (A^2 + D^2) - its own estimate, misjudged as minds
                    misjudge (decide.choose).
THE COST OF WAR     its own losses, and the other's dead as its mind counts others' lives (the Light in full, the Dark
                    not at all - as settling.policy weighs erasure); the lives a people ends are booked dark on its
                    history (alignment.flow). Expelling also gains the enclosed's worlds the encloser can live on.
CONSERVED           every death is booked with its cause (stats()["deaths"]); an absorbed people is transferred, its
                    worlds' moneys reformed into its absorber's at a declared rate (institutions.rehome: burned and
                    minted, both declared); a leap's kindling is paid from the people's counted energy bank and the
                    gateway it opens runs both ways (a source/sink pair). A gateway leaving the galaxy is the court's
                    to price (crosses_domain): none does here.
"""

import copy
import math
from typing import Any, Dict, List, Optional, Tuple

SECONDS_PER_GYR = 1e9 * 3.156e7


def stats(kernel: Any) -> Dict[str, Any]:
    from xylarium.kernel import annals
    st = annals.stats(kernel)
    st.setdefault("deaths", {})
    st.setdefault("transfers", [])
    return st.setdefault("encircled", [])


def deaths(kernel: Any) -> Dict[str, Dict[str, int]]:
    """Every death the dominions' encounters caused: {people: {cause: count}}."""
    from xylarium.kernel import annals
    return annals.stats(kernel).setdefault("deaths", {})


def _book_deaths(kernel: Any, who: str, n: float, cause: str) -> int:
    n = int(round(max(0.0, n)))
    if n:
        d = deaths(kernel).setdefault(who, {})
        d[cause] = d.get(cause, 0) + n
    return n


# ---------------------------------------------------------------------- what each side holds
def _held_if(kernel: Any, who: str, t: float, patch: Dict[str, Optional[Dict[str, Any]]],
             extra: Optional[Dict[str, Any]] = None) -> float:
    """What a people would hold at epoch t were its cuts as patched (None removes one) - read, then put back."""
    from xylarium.kernel import settling
    b = settling.stats(kernel)[who]
    saved_cuts, saved_fell, saved_leaps = b["cuts"], b["fell"], b.get("leaps")
    try:
        cuts = copy.deepcopy(saved_cuts)
        for k, v in patch.items():
            if v is None:
                cuts.pop(k, None)
            else:
                cuts[k] = v
        b["cuts"] = cuts
        if extra and "leaps" in extra:
            b["leaps"] = (saved_leaps or []) + extra["leaps"]
        return float(settling.held(kernel, who, t))
    finally:
        b["cuts"], b["fell"] = saved_cuts, saved_fell
        if saved_leaps is None:
            b.pop("leaps", None)
        else:
            b["leaps"] = saved_leaps


def _worlds(kernel: Any, who: str, t: float) -> float:
    """The worlds a people has at t: what the annals last counted, never more than it can hold then."""
    from xylarium.kernel import annals, settling
    w = float(((annals.stats(kernel)["of"].get(who) or {}).get("hist") or {}).get("W", 1.0))
    return max(1.0, min(w, settling.held(kernel, who, t)))


def _capacity(kernel: Any, who: str) -> float:
    """The people a world of its holds: its home's carrying capacity (biosphere)."""
    from xylarium.kernel import biosphere, spheres
    home = spheres._home(kernel, who)
    if home is None:
        return 0.0
    try:
        return float(biosphere.carrying_capacity(kernel, home))
    except Exception:
        return float(max(0, getattr(home, "population", 0)))


def _geometry(kernel: Any, enclosed: str, holder: str, t: float) -> Optional[Dict[str, float]]:
    """The encounter's measures: the homes' distance, the halfway seam, the time the enclosed front takes to reach
    it, and how long ago the encloser's front passed the enclosed home."""
    from xylarium.kernel import settling
    st = settling.stats(kernel)
    be, bh = st[enclosed], st[holder]
    pe, ph = settling.xy(kernel, be["sid"], t), settling.xy(kernel, bh["sid"], t)
    if pe is None or ph is None:
        return None
    d = math.hypot(pe[0] - ph[0], pe[1] - ph[1])
    seam = 0.5 * d
    reach_time = max(0.0, seam - settling.radius(be, t)) / max(1e-12, be["v"])
    passed = bh["t0"] + max(0.0, d - bh["hop"]) / max(1e-12, bh["v"])
    return {"d": d, "seam": seam, "t_ref": t + reach_time, "tau": max(0.0, t - passed), "pe": pe, "ph": ph}


def _strengths(kernel: Any, enclosed: str, holder: str, t: float, g: Dict[str, float]) -> Tuple[float, float]:
    """Lanchester strengths at the seam: the enclosed's worlds; the encloser's worlds in the contested ball (its room
    there, filled from one world as e^(g tau) since its front passed - never past the room)."""
    from xylarium.kernel import settling
    st = settling.stats(kernel)
    be, bh = st[enclosed], st[holder]
    a = _worlds(kernel, enclosed, t)
    room = settling.systems_in(be["r0"], g["seam"], bh.get("band")) * bh["share"]
    grown = math.exp(min(700.0, bh["g"] * g["tau"]))
    return a, max(1.0, min(room, grown))


def _leap(kernel: Any, who: str, holder: str, t: float, g: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """A gateway beyond the encloser's front: when its own arrays will have banked the kindling (gateways: the
    lightest black hole's mass-energy, from the light its dominion's arrays take), and where its far mouth opens -
    just past the encloser's front, on the line from the encloser's home through its own."""
    from xylarium.kernel import cosmos, gateways, settling
    power = gateways.coalition_power_w(kernel, (who,))
    if power <= 0:
        return None
    banked_suns_per_s = power / gateways.SUN_J                 # what its arrays bank, as mass (E / c^2)
    t_open = t + gateways.LIGHTEST_HOLE_SUNS / banked_suns_per_s / SECONDS_PER_GYR   # against the hole's own mass
    bh, be = settling.stats(kernel)[holder], settling.stats(kernel)[who]
    ex, ey = g["pe"][0] - g["ph"][0], g["pe"][1] - g["ph"][1]
    n = math.hypot(ex, ey) or 1.0
    out = settling.radius(bh, t_open) + be["hop"]
    fx, fy = g["ph"][0] + ex / n * out, g["ph"][1] + ey / n * out
    r_far = math.hypot(fx, fy)
    if r_far > cosmos.R_MAX_KPC:
        return None                                           # beyond the encloser lies only the galaxy's edge
    return {"t": t_open, "r0": r_far, "hop": be["hop"], "v": be["v"], "suns": gateways.LIGHTEST_HOLE_SUNS,
            "j": gateways.kindle_cost_j(),
            "mouths": [be["sid"], [round(fx, 6), round(fy, 6)]], "by": who}


def crosses_domain(gateway: Dict[str, Any]) -> bool:
    """Does a gateway leave the galaxy (another galaxy or universe)? Then its traversal is the court's to price, in
    mu at the ancient houses' tier. A leap past an encloser stays within the galaxy."""
    return False


# ---------------------------------------------------------------------- the options
def _cut(holder: str, t: float, a: Optional[float], o: float, style: str) -> Dict[str, Any]:
    return {"by": holder, "a": a, "t": t, "o": o, "style": style}


def _options(kernel: Any, me: str, other: str, enclosed: str, holder: str, t: float,
             g: Dict[str, float]) -> List[Dict[str, Any]]:
    """What `me` can do, each priced in the worlds it would hold at the encounter's end (value) and the worlds' worth
    of its own people it would lose (cost)."""
    from xylarium.kernel import decide, settling
    st = settling.stats(kernel)
    t_ref = g["t_ref"]
    a, dd = _strengths(kernel, enclosed, holder, t, g)
    p_enc = a * a / (a * a + dd * dd)
    cur = st[enclosed]["cuts"].get(holder)
    o = float(cur.get("o", 1.0)) if cur else 1.0
    enclave = _held_if(kernel, me, t_ref, {})
    out = []
    if me == enclosed:
        out.append(decide.option("enclave", 0.0, enclave, kind="enclave"))
        out.append(decide.option("alliance", 0.0, enclave + _bond_room(kernel, holder, t_ref, a),
                                 kind="alliance", needs=True))
        mine = _worlds(kernel, enclosed, t)
        theirs = _worlds(kernel, holder, t)
        out.append(decide.option("join", 0.0, _held_if(kernel, holder, t_ref, {}) * mine / (mine + theirs),
                                 kind="join", needs=True))
        seam = _held_if(kernel, enclosed, t_ref, {holder: _cut(holder, t, g["seam"], o, "war")})
        keep = math.sqrt(max(0.0, 1.0 - (min(a, dd) / max(a, dd)) ** 2))
        theirs_lost = p_enc * dd + (1.0 - p_enc) * dd * (1.0 - keep)        # the encloser's worlds it would empty
        own_lost = p_enc * a * (1.0 - keep) + (1.0 - p_enc) * a
        out.append(decide.option("contest", own_lost + _light(kernel, enclosed) * theirs_lost, p_enc * seam,
                                 kind="war"))
        lp = _leap(kernel, enclosed, holder, t, g)
        if lp is not None and lp["t"] < t_ref:
            far = _held_if(kernel, enclosed, t_ref, {}, {"leaps": [lp]})
            out.append(decide.option("leap", 0.0, far, kind="leap", leap=lp))
    else:
        p_hold = 1.0 - p_enc
        out.append(decide.option("tolerate", 0.0, enclave, kind="enclave"))
        out.append(decide.option("offer_alliance", 0.0, enclave + _bond_room(kernel, holder, t_ref, a),
                                 kind="alliance", needs=True))
        out.append(decide.option("demand_absorption", 0.0, enclave + _worlds(kernel, enclosed, t),
                                 kind="join", needs=True))
        lost = _held_if(kernel, holder, t_ref, {enclosed: _cut(enclosed, t, g["d"] - g["seam"], o, "war")})
        keep = math.sqrt(max(0.0, 1.0 - (min(a, dd) / max(a, dd)) ** 2))
        gained = a * o                                               # the enclosed's worlds it can live on itself
        theirs_lost = p_hold * a + (1.0 - p_hold) * a * (1.0 - keep)        # the enclosed's worlds it would empty
        own_lost = p_hold * dd * (1.0 - keep) + (1.0 - p_hold) * dd
        out.append(decide.option("expel", own_lost + _light(kernel, holder) * theirs_lost,
                                 p_hold * (enclave + gained) + (1.0 - p_hold) * lost, kind="war"))
    return out


def _bond_room(kernel: Any, holder: str, t: float, ally_worlds: float) -> float:
    """What a bond adds to the encloser's coalition: the ally's arrays bank with it, so the room its kindled spheres
    have yet to form comes sooner - the ally's share of it."""
    from xylarium.kernel import settling
    bh = settling.stats(kernel)[holder]
    to_come = settling.room_to_come(kernel, bh, t)
    w = max(1.0, _worlds(kernel, holder, t))
    return to_come * ally_worlds / (ally_worlds + w)


def _light(kernel: Any, who: str) -> float:
    """How fully a mind counts others' lives as its own (alignment.regard - the one measure settling.policy weighs
    erasure by): what another people's deaths cost it in a war."""
    from xylarium.kernel import alignment, spheres
    home = spheres._home(kernel, who)
    return alignment.regard(getattr(home, "civilization", None) if home is not None else None)


def _mind(kernel: Any, who: str) -> Tuple[Dict[str, float], str]:
    from xylarium.kernel import decide, spheres
    home = spheres._home(kernel, who)
    if home is not None:
        return decide.mind_of_planet(kernel, home), home.id
    return {"noise": 1.0}, who


def _choose(kernel: Any, who: str, opts: List[Dict[str, Any]], why: str) -> Optional[Dict[str, Any]]:
    from xylarium.kernel import decide
    m, mid = _mind(kernel, who)
    return decide.choose(kernel, opts, m, mid, why)


# ---------------------------------------------------------------------- the exchange
def respond(kernel: Any, enclosed: str, holder: str, t: float, logs: List[str]) -> Optional[Dict[str, Any]]:
    """The enclosed and its encloser weigh, propose and answer; what they settle on is done and booked."""
    from xylarium.kernel import clocks, spheres
    if not getattr(kernel, "sectors", None) or spheres._home(kernel, enclosed) is None \
            or spheres._home(kernel, holder) is None:
        return None                                           # no world, no mind to weigh it: the enclave stands
    g = _geometry(kernel, enclosed, holder, t)
    if g is None:
        return None
    he, hh = clocks.height(kernel, enclosed), clocks.height(kernel, holder)
    first, second = (holder, enclosed) if hh < he else (enclosed, holder)
    proposal = _choose(kernel, first, _options(kernel, first, second, enclosed, holder, t, g), "encircled")
    if proposal is None:
        proposal = {"name": "enclave" if first == enclosed else "tolerate", "kind": "enclave"}
    outcome = proposal
    answer = None
    if proposal["kind"] != "enclave":
        own = _options(kernel, second, first, enclosed, holder, t, g)
        accept = next((dict(o, name="accept") for o in own if o["kind"] == proposal["kind"]), None)
        pool = ([accept] if accept is not None else []) + [o for o in own if o["kind"] in ("enclave", "war")]
        answer = _choose(kernel, second, pool, "encircled_answer") or {"name": "enclave", "kind": "enclave"}
        if answer["name"] == "accept" or answer["kind"] == "war":
            outcome = proposal if answer["name"] == "accept" else answer
        elif proposal.get("needs"):
            outcome = {"name": "enclave", "kind": "enclave"}         # refused: the enclave stands
        else:
            outcome = proposal                                        # a leap needs no one's leave
    clocks.link(kernel, enclosed, holder, "an enclosure answered")
    rec = {"enclosed": enclosed, "by": holder, "t": round(t, 6), "first": first,
           "proposed": proposal["name"], "answer": (answer or {}).get("name"), "outcome": outcome["kind"]}
    _enact(kernel, enclosed, holder, t, g, outcome, rec, logs)
    stats(kernel).append(rec)
    return rec


def _enact(kernel: Any, enclosed: str, holder: str, t: float, g: Dict[str, float], outcome: Dict[str, Any],
           rec: Dict[str, Any], logs: List[str]) -> None:
    from xylarium.kernel import annals, history, settling
    st = settling.stats(kernel)
    name = lambda w: w.split(":", 1)[-1]                       # noqa: E731
    kind = outcome["kind"]
    cut = st[enclosed]["cuts"][holder]
    if kind == "alliance":
        cut["style"] = "alliance"
        st[holder]["cuts"].setdefault(enclosed, _cut(enclosed, t, g["d"], 0.0, "alliance"))["style"] = "alliance"
        annals.stats(kernel)["pacts"] += 1
        what = f"the {name(enclosed)} and the {name(holder)} are bound in alliance"
    elif kind == "join":
        n = _worlds(kernel, enclosed, t) * _capacity(kernel, enclosed)
        annals.stats(kernel).setdefault("transfers", []).append({"from": enclosed, "to": holder, "t": round(t, 6),
                                                  "people": int(round(n)), "why": "absorbed"})
        st[enclosed]["absorbed_by"] = holder
        settling.fall(kernel, enclosed, t)                     # its dominion ends; its people live on in the other's
        _reform_money(kernel, enclosed, holder)
        rec["transferred"] = int(round(n))
        what = f"the {name(enclosed)} join the {name(holder)} (absorbed, not lost)"
    elif kind == "war":
        a, dd = _strengths(kernel, enclosed, holder, t, g)
        annals.stats(kernel)["wars"] += 1
        rec["deaths"] = {}
        if a > dd:                                             # the enclosed hold the halfway seam
            keep = math.sqrt(1.0 - (dd / a) ** 2)
            rec["deaths"] = {enclosed: _book_deaths(kernel, enclosed, a * (1 - keep) * _capacity(kernel, enclosed),
                                                    "war:encirclement"),
                             holder: _book_deaths(kernel, holder, dd * _capacity(kernel, holder),
                                                  "war:encirclement")}
            o = float(cut.get("o", 1.0))
            st[enclosed]["cuts"][holder] = _cut(holder, t, g["seam"], o, "war")
            st[holder]["cuts"][enclosed] = _cut(enclosed, t, g["d"] - g["seam"], o, "war")
            what = f"the {name(enclosed)} win the war of the seam against the {name(holder)}"
        else:                                                  # the margin holds: the enclosed fall there
            keep = math.sqrt(max(0.0, 1.0 - (a / dd) ** 2))
            rec["deaths"] = {enclosed: _book_deaths(kernel, enclosed, a * _capacity(kernel, enclosed),
                                                    "war:encirclement"),
                             holder: _book_deaths(kernel, holder, dd * (1 - keep) * _capacity(kernel, holder),
                                                  "war:encirclement")}
            settling.fall(kernel, enclosed, t)
            what = f"the {name(enclosed)} fall in the war of the seam against the {name(holder)}"
        _book_dark(kernel, enclosed, rec["deaths"].get(holder, 0))         # each books the lives it ended
        _book_dark(kernel, holder, rec["deaths"].get(enclosed, 0))
    elif kind == "leap":
        lp = outcome["leap"]
        from xylarium.kernel import gateways
        bank = gateways.stats(kernel)["banks"].setdefault(enclosed, {"j": 0.0, "t": t, "spent": 0.0})
        bank["spent"] = float(bank.get("spent", 0.0)) + lp["j"]     # banked from its arrays until lp["t"], spent
        bank["spent_suns"] = float(bank.get("spent_suns", 0.0)) + lp["suns"]
        gw = {"by": enclosed, "t": round(lp["t"], 6), "mouths": lp["mouths"], "j": lp["j"], "two_way": True,
              "court": crosses_domain(lp)}
        gateways.stats(kernel).setdefault("gates", []).append(gw)
        st[enclosed].setdefault("leaps", []).append({k: lp[k] for k in ("t", "r0", "hop", "v")})
        rec["leap_at"] = round(lp["t"], 6)
        what = f"the {name(enclosed)} bank toward a gateway past the {name(holder)}'s front"
    else:
        what = f"the {name(enclosed)} hold an enclave inside the dominion of the {name(holder)}"
    history.event(kernel, "ENCIRCLED", what[0].upper() + what[1:], actors=[enclosed, holder],
                  sector_id=st[enclosed]["sid"],
                  cause=f"the {name(rec['first'])} spoke first ({rec['proposed']})"
                        + (f"; the answer: {rec['answer']}" if rec["answer"] else ""),
                  data={"epoch": rec["t"], "outcome": kind})
    logs.append(f"[ANNALS] {what[0].upper() + what[1:]}.")


def _book_dark(kernel: Any, who: str, killed: int) -> None:
    """The lives a people ended are order destroyed: booked dark on its whole history (alignment.flow)."""
    from xylarium.kernel import alignment, spheres
    home = spheres._home(kernel, who)
    civ = getattr(home, "civilization", None) if home is not None else None
    if civ is not None and killed > 0:
        alignment.flow(civ, dark=float(killed), why="war at the seam")


def _reform_money(kernel: Any, enclosed: str, holder: str) -> None:
    """An absorbed people's worlds come to live in its absorber's money: every holding reformed at a declared rate
    (institutions.rehome: the old burned, the new minted, both declared) - never left to vanish."""
    from xylarium.kernel import institutions, knowledge, spheres
    home = spheres._home(kernel, holder)
    cur = getattr(home, "currency", None) if home is not None else None
    if not cur:
        return
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.population > 0 and knowledge.holder_of_planet(p) == enclosed and p.currency != cur:
                institutions.rehome(kernel, p, cur, why="absorption")
