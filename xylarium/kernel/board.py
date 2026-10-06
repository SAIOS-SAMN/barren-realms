"""
Xylarium board: the minds above the realms - the watcher (T1), who sees across them, and the progenitor (T0), who
folds space and time to settle what no steward can - by the mind core (mindcore.py).

THE WATCHER'S BOOKS (its sites: the realms, and the appeals between them):
  lives    lives taken within each realm, against those its stewards' rulings have stopped
  appeals  lives taken between the parties of each appeal since it went up (what waits on the progenitors)
Once a year the watcher brings the appeal deepest in its books before the progenitors (within one book, the deepest
first) - the order of the progenitors' attention, never a verdict.

THE PROGENITOR'S BOOKS (its sites: the board):
  appeals     what the watcher has brought before it
  minds       the minds the universe was expected to raise by now / those it has raised
  unsheltered lives that died with their suns, or in extinctions, in the span / lives carried to safety
A progenitor seated by a player reads these books and decides. Where none is seated, the ancients' own progenitor
line - the first mind's line, older than every realm - seals what the watcher brings before it: its seal stands for
good and joins the parties' worldlines. What a seal did is read the next year as the lives still taken between the
parties: a crystal if it stopped them, else a wall (the seal itself cannot be undone - the ancients' laws are above).
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from xylarium.kernel import mindcore as mc

WATCHER_BOOKS = ("appeals", "lives")
PROGENITOR_BOOKS = ("appeals", "minds", "unsheltered")
SHELTER_KINDS = ("PERISHED", "EXTINCTION", "ABANDONED")


def stats(kernel: Any) -> Dict[str, Any]:
    return state.of(kernel, "board")


def _line(kernel: Any, key: str, seat: str) -> Dict[str, Any]:
    st = stats(kernel)
    rec = st.get(key)
    if rec is None:
        from xylarium.kernel import scheduler
        from xylarium.kernel.natives import _name
        rec = st[key] = {"name": _name(scheduler.rng(kernel, seat, "line")), "since": kernel.cycle_count,
                         "seat": seat, "mind": mc.new_mind(), "acts": 0}
    return rec


def watcher_books(kernel: Any) -> mc.Chain:
    from xylarium.kernel import stewardship
    need: List[Tuple[str, str, Any]] = []
    have: List[Tuple[str, str, Any]] = []
    for realm in stewardship.realms(kernel):
        span = stewardship.span_cycles(kernel, realm)
        res = stewardship.books(kernel, realm)
        taken = sum((v for (s, b), v in res.items() if b in ("lives", "young") and v > 0), Fraction(0))
        need.append((realm, "lives", taken))
        have.append((realm, "lives", sum(1 for r in stewardship.stats(kernel)["rulings"].values()
                                          if r["realm"] == realm and r["cycle"] >= kernel.cycle_count - span)))
    for r in stewardship.stats(kernel)["appeals"]:
        need.append((r["id"], "appeals", stewardship._stake_since(kernel, r["a"], r["b"], r["cycle"]) + 1))
    return mc.residual(mc.measure(need), mc.measure(have))


def progenitor_books(kernel: Any) -> mc.Chain:
    from xylarium.kernel import cosmos, history, stewardship
    need: List[Tuple[str, str, Any]] = []
    have: List[Tuple[str, str, Any]] = []
    for r in stewardship.stats(kernel)["appeals"]:
        if r.get("before"):
            need.append((r["id"], "appeals", stewardship._stake_since(kernel, r["a"], r["b"], r["cycle"]) + 1))
    for r in stewardship.stats(kernel)["rulings"].values():
        if str(r.get("sealed_by", "")).startswith(("ancients:", "progenitor:")):   # what seals have not stopped
            need.append((r["id"], "sealed", stewardship._stake_since(kernel, r["a"], r["b"], r["sealed_at"])))
    if cosmos.is_cosmic(kernel):
        need.append(("board", "minds", mc.q(cosmos.expected_by(kernel, cosmos.deep_gyr(kernel)))))
        have.append(("board", "minds", cosmos.stats(kernel).get("arisen", 0)))
    since = kernel.cycle_count - stewardship.span_cycles(kernel)
    lost = sum(float(e.get("magnitude") or 0) for e in history.stats(kernel)["recent"]
               if e.get("kind") in SHELTER_KINDS and e.get("cycle", 0) >= since)
    carried = sum(float(e.get("magnitude") or 0) for e in history.stats(kernel)["recent"]
                  if e.get("kind") in ("RESCUE", "EXODUS") and e.get("cycle", 0) >= since)
    need.append(("board", "unsheltered", lost))
    have.append(("board", "unsheltered", carried))
    return mc.residual(mc.measure(need), mc.measure(have))


def seated_progenitor(kernel: Any) -> Optional[str]:
    from xylarium.kernel import roles
    return next((pid for pid, r in roles.stats(kernel).get("of", {}).items() if r == "progenitor"), None)


# ---------------------------------------------------------------------- the progenitors: an ancients' own class
def ancient_peoples(kernel: Any) -> Dict[str, Any]:
    """The living peoples that are ancients (roles.ancients: by age and by place - woke within one core assembly time
    of the galaxy's first mind, on a star of its own ring's first generation). -> {holder: home world}."""
    from xylarium.kernel import cosmos, relations, roles
    if not cosmos.is_cosmic(kernel):
        return {}
    origins = {(tuple(a["cell"]), int(a["k"])) for a in roles.ancients(kernel)}
    out = {}
    for who, worlds in relations._peoples(kernel).items():
        home = max(worlds, key=lambda w: (w.population, w.id))
        g = cosmos.stats(kernel)["place"].get(str(home.sector_id)) or {}
        if "cell" in g and (tuple(g["cell"]), int(g.get("k", 0))) in origins:
            out[who] = home
    return out


def progenitors(kernel: Any) -> Dict[str, Dict[str, Any]]:
    """The progenitor lines: an ancient people that has crossed to the stars - staying near its own worlds, as the
    old do - raises a class of its own to do its bidding across them. Each line's reach is its people's network of
    folded passages (spheres.py: as far as its power has paid for); a line whose people falls ends. A people that is
    not ancient keeps its own line when it crosses: it sends its own stewards to the realms its network holds
    (stewardship.envoys: "sent by the X themselves"), and raises no progenitors. In a settled universe, which has no
    Big Bang of its own, the elders of its prehistory hold the progenitors' place."""
    from xylarium.kernel import annals, mastery, spheres
    st = stats(kernel)
    lines = st.setdefault("progenitors", {})
    anc = ancient_peoples(kernel)
    for who, home in anc.items():
        crossed = mastery.crossed(kernel, who) or "crossed" in (annals.stats(kernel)["of"].get(who) or {}).get("passed", [])
        if crossed and who not in lines:
            from xylarium.kernel import history, scheduler
            from xylarium.kernel.natives import _name
            lines[who] = {"name": _name(scheduler.rng(kernel, "progenitor", who)), "ancient": who,
                          "since": kernel.cycle_count, "mind": mc.new_mind(), "acts": 0, "seat": None}
            history.event(kernel, "PROGENITOR_CLASS", f"The {who.split(':', 1)[-1]} raise their progenitors",
                          actors=[who], planet=home, cause="an ancient people, near its own worlds, sends others out",
                          data={"line": lines[who]["name"]})
    for who, rec in lines.items():
        rec["ended"] = None if who in anc else (rec.get("ended") or kernel.cycle_count)
        rec["reach_kpc"] = spheres.radius(kernel, who)       # its network's reach (spheres.py)
    if not anc and not lines:
        elders = _line(kernel, "progenitor", "progenitor")
        elders.setdefault("ancient", None)
        return {"elders": elders}
    return {w: r for w, r in lines.items() if not r.get("ended")}


def _distance(kernel: Any, a_holder: str, b_sector: int) -> float:
    from xylarium.kernel import cosmos, geometry, relations
    worlds = relations._peoples(kernel).get(a_holder) or []
    if not worlds:
        return float("inf")
    home = max(worlds, key=lambda w: (w.population, w.id))
    pa, pb = cosmos.position(kernel, home.sector_id), cosmos.position(kernel, b_sector)
    if not pa or not pb:
        return 0.0
    return float(geometry.proper_kpc([pa["x"], pa["y"], pa["z"]], [pb["x"], pb["y"], pb["z"]]))


def _home_sector(kernel: Any, holder: str) -> Optional[int]:
    from xylarium.kernel import relations
    worlds = relations._peoples(kernel).get(holder) or []
    return max(worlds, key=lambda w: (w.population, w.id)).sector_id if worlds else None


def answerable(kernel: Any, line: Dict[str, Any], appeal: Dict[str, Any]) -> Optional[float]:
    """Can this progenitor line reach both parties of an appeal? Its distance to the farther, if so."""
    if line.get("ancient") is None:
        return 0.0                                           # the elders of a settled universe reach all of it
    far = 0.0
    for p in (appeal["a"], appeal["b"]):
        sid = _home_sector(kernel, p)
        if sid is None:
            return None
        d = _distance(kernel, line["ancient"], sid)
        if d > line.get("reach_kpc", 0.0):
            return None
        far = max(far, d)
    return far


def season(kernel: Any) -> List[str]:
    """Once a year: the watcher brings the deepest appeal before the progenitors; each progenitor line not held by a
    player seals one appeal it can reach - the nearest of those before it - and reads what its last seal did."""
    from xylarium.kernel import stewardship
    if (kernel.cycle_count // 25) % 4 or "stewardship" not in getattr(kernel, "state", {}):
        return []
    logs: List[str] = []
    w = _line(kernel, "watcher", "watcher")
    wres = watcher_books(kernel)
    entry = mc.lead({k: v for k, v in wres.items() if k[1] == "appeals"}, WATCHER_BOOKS, deepest=True)
    if entry is not None:
        rec = next((r for r in stewardship.stats(kernel)["appeals"] if r["id"] == entry[0]), None)
        if rec is not None and not rec.get("before"):
            rec["before"] = kernel.cycle_count
            w["acts"] += 1
            logs.append(f"[WATCHER] {w['name']} brings {rec['id']} ({rec['kind']}: {rec['a'].split(':', 1)[-1]} / "
                        f"{rec['b'].split(':', 1)[-1]}) before the progenitors.")
    seated = seated_progenitor(kernel)
    seated_people = None
    if seated is not None:
        from xylarium.kernel import ages, knowledge
        home = ages.homeworld(kernel, seated)
        seated_people = knowledge.holder_of_planet(home) if home is not None else None
    for who, p in progenitors(kernel).items():
        if who == seated_people:
            continue                                         # a player's progenitors are its own to command
        pres = progenitor_books(kernel)
        mc.seal(p["mind"], pres)
        before = [r for r in stewardship.stats(kernel)["appeals"] if r.get("before")]
        reach = [(answerable(kernel, p, r), r) for r in before]
        reach = [(d, r) for d, r in reach if d is not None]
        if not reach:
            continue
        d, r = min(reach, key=lambda x: (x[0], x[1]["id"]))  # the nearest of what it can reach
        res = stewardship._seal(kernel, f"progenitor:{p['name']}", r["id"])
        if res.get("ok"):
            mc.intend(p["mind"], (r["id"], "sealed"), pres.get((r["id"], "appeals"), mc.q(1)), "seal", "appeal")
            p["acts"] += 1
            logs.append(f"[PROGENITOR] {p['name']}" + (f" of the {who.split(':', 1)[-1]}" if p.get("ancient") else
                                                      " of the elders") +
                        f" seals the {r['kind']} between the {r['a'].split(':', 1)[-1]} and the {r['b'].split(':', 1)[-1]}.")
    return logs


def render(kernel: Any) -> str:
    """The board as the progenitors read it."""
    lines = ["=== THE BOARD ==="]
    for name, res, order in (("Watcher", watcher_books(kernel), WATCHER_BOOKS),
                             ("Progenitor", progenitor_books(kernel), PROGENITOR_BOOKS)):
        lines.append(f"  {name}'s books:")
        for book in order:
            for (site, b), v in sorted(res.items()):
                if b == book:
                    lines.append(f"    {book:<12} {site:<10} {float(v):>+14,.1f}")
    return "\n".join(lines)


def summary(kernel: Any) -> Dict[str, Any]:
    st = stats(kernel)
    out = {k: {"name": v["name"], "acts": v["acts"]} for k, v in st.items() if isinstance(v, dict) and "name" in v}
    out["progenitors"] = {w: {"name": v["name"], "acts": v["acts"], "ended": v.get("ended")}
                          for w, v in st.get("progenitors", {}).items()}
    return out


from xylarium.kernel import state  # noqa: E402
from xylarium.kernel.subsystem import Subsystem, register as register_subsystem  # noqa: E402

register_subsystem(Subsystem(name="board", state=lambda: {}, season=season, summary=summary))
