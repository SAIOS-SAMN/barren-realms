"""
Xylarium: Cosmic alignment - the Light (syntropy) and the Dark (entropy).

Every people and every captain carries an alignment in [-1, +1], and it is one law for both: the truth of a whole
history, in lives - what was made and kept, or given and spared (light), against what was taken (dark):
(light - dark) / (light + dark), never faded (see "a people's history" below). It measures intelligence as a
progenitor sees it: order made that lasts, against order destroyed. A captain's honest earnings are order made for
others (the goods are where they are wanted); what it only moves - a cargo taken, a tribute, a gift - is a
transfer, kept on its record and weighing nothing; a hull it wrecks is destroyed; the lives it ends and spares
count one each. What a court finds, an oath kept, a thing observed are
judgements and records, not consequences: they are kept in the record, and weigh nothing in the truth.

What alignment brings is its consequence, not a rule: trusted (Luminous+) captains trade a little cheaper, while
Shadowed captains pay friction on every deal, neglect their hulls and draw Federal warrants; at the poles, vows bind
- a Paragon of Light will not do evil, an Avatar of the Dark will not stoop to charity. Nothing anchors anyone to a
side, and nothing drifts anyone toward one: a captain is what it has done.
"""

import math
import random
from typing import List, Any, Dict, Optional

from xylarium.config import (
    ALIGNMENT_BANDS,
    ALIGNMENT_VOW,
    ALIGNMENT_GOODWILL_MAX,
    ALIGNMENT_FRICTION_MAX,
    ALIGNMENT_HULL_WEAR,
    ALIGNMENT_WARRANT_THRESHOLD,
    ALIGNMENT_WARRANT,
    ALIGNMENT_GENESIS_SHARES,
)

NEUTRAL_EDGE = 0.15


def band(value: float) -> str:
    for lower, title in ALIGNMENT_BANDS:
        if value >= lower:
            return title
    return ALIGNMENT_BANDS[-1][1]


def side(value: float) -> str:
    if value >= NEUTRAL_EDGE:
        return "light"
    if value <= -NEUTRAL_EDGE:
        return "dark"
    return "neutral"


def genesis_value(rng: Optional[random.Random] = None, bias: float = 0.0) -> float:
    """Draws a genesis alignment: ~70% neutral pragmatists, ~15% Light, ~15% Dark (shifted by ``bias``)."""
    rng = rng or random
    roll = rng.random()
    shares = ALIGNMENT_GENESIS_SHARES
    if roll < shares["light"]:
        value = rng.uniform(0.3, 0.7)
    elif roll < shares["light"] + shares["dark"]:
        value = rng.uniform(-0.7, -0.3)
    else:
        value = rng.uniform(-0.12, 0.12)
    return max(-1.0, min(1.0, round(value + bias, 3)))


# ---------------------------------------------------------------------- consequences
ALIGNMENT_ACT_SCALE = 0.12      # the largest shift one act can make (the gravest deed in the old table)
LIVES_PER_FOOD_UNIT = 200       # colony.tick_colony: each unit of a famine's deficit costs this many lives


# ---------------------------------------------------------------------- a people's history
# A people's alignment is the truth of its whole history, kept by the steward's ledger and never faded: of all the
# order that has flowed through it, in lives (a life sustained, taken or spared counts one; a generation of its own
# work sustaining it counts its numbers), the share that was made and shared rather than taken:
#
#     alignment = (light - dark) / (light + dark)
#
#   light   the lives its own work sustains and its many keep (rent.py: what its few do not take), lives spared
#           (medicine, relief)
#   dark    what its few take from its many (rent), lives taken (strife it brings on itself, predation, a food war's
#           seizure, a reset)
#
# It is a ratio of whole histories, so a people is read by what it did over its thousands of years, not its latest
# generation: eighty years of taking are not undone by a turn, only by as many years of making as were spent taking.
# What a people tells of itself (its doctrine, `told`) is another ledger - the same flows, faded as its records fade
# (memory.character_keep: its best medium) - and the gap between the two is the distance between what it says it is
# and what it has been.

def _get(x: Any, key: str, default: Any = 0.0) -> Any:
    return x.get(key, default) if isinstance(x, dict) else getattr(x, key, default)


def _put(x: Any, key: str, value: Any) -> None:
    if isinstance(x, dict):
        x[key] = value
    else:
        setattr(x, key, value)


def _ratio(light: float, dark: float) -> Optional[float]:
    total = light + dark
    return (light - dark) / total if total > 0 else None


def character(x: Any) -> float:
    """What a people's whole history makes of it (light - dark over light + dark); a people with no history yet is
    what it was given."""
    r = _ratio(float(_get(x, "light", 0.0) or 0.0), float(_get(x, "dark", 0.0) or 0.0))
    return float(_get(x, "alignment", 0.0) or 0.0) if r is None else r


def doctrine(x: Any) -> float:
    """What a people tells of itself: its flows as its own records still hold them."""
    r = _ratio(float(_get(x, "told_light", 0.0) or 0.0), float(_get(x, "told_dark", 0.0) or 0.0))
    return character(x) if r is None else r


def gap(x: Any) -> float:
    """How much lighter a people tells itself than it has been (negative: it thinks worse of itself than it is)."""
    return doctrine(x) - character(x)


def flow(x: Any, light: float = 0.0, dark: float = 0.0, why: str = "deeds") -> None:
    """Order through a people, in lives: what it made and kept or spared (light), what it destroyed (dark). Goes into
    its history and into its own telling of it, and is kept by its cause (`why`), so a reading can be explained."""
    light, dark = max(0.0, float(light)), max(0.0, float(dark))
    if light <= 0.0 and dark <= 0.0:
        return
    for key, add in (("light", light), ("dark", dark), ("told_light", light), ("told_dark", dark)):
        _put(x, key, float(_get(x, key, 0.0) or 0.0) + add)
    causes = _get(x, "causes", None)
    if causes is None:
        causes = {}
        _put(x, "causes", causes)
    c = causes.setdefault(why, [0.0, 0.0])
    c[0] += light
    c[1] += dark
    _put(x, "alignment", round(character(x), 4))


def foreseen(kernel: Any, holder: Optional[str], domain: str) -> float:
    """How far a people could have seen a loss coming, 0 .. 1: its mastery of the science that predicts it (what it
    knows of `domain`, laws.mastery). A people that could not know is not answerable for what it did not see."""
    from xylarium.config import KNOWLEDGE_UNIT
    from xylarium.kernel import knowledge, laws
    if not holder:
        return 0.0
    return laws.mastery(knowledge.experience(kernel, holder, domain), KNOWLEDGE_UNIT)


def omitted(planet: Any, lives: float, foreseen_share: float, avoidable_share: float, why: str) -> float:
    """Lives lost to what a people could have seen coming and had the means to prevent, and did not: dark, as far
    as both reach. Returns the lives counted."""
    counted = max(0.0, lives) * max(0.0, min(1.0, foreseen_share)) * max(0.0, min(1.0, avoidable_share))
    civ = getattr(planet, "civilization", None)
    if counted > 0 and civ is not None and getattr(planet, "owner_id", None) is None:
        flow(civ, dark=counted, why=why)
    return counted


def causes(x: Any) -> Dict[str, Dict[str, float]]:
    """A people's history by cause: lives made and destroyed, and each cause's share of all that was destroyed."""
    cs = _get(x, "causes", None) or {}
    dark = sum(v[1] for v in cs.values()) or 1.0
    return {k: {"light": round(v[0], 3), "dark": round(v[1], 3), "share_of_dark": round(v[1] / dark, 4)}
            for k, v in sorted(cs.items(), key=lambda kv: -kv[1][1])}


def lives_of_sol(kernel: Any, sol: float, planet: Any = None) -> float:
    """Wealth in lives: SOL over what one of its people makes in a generation (a head's earnings a cycle, colony.py,
    over its generation). Taking a generation of a person's product is taking that person's life's work."""
    from xylarium.config import COLONY_TAX_PER_CAPITA
    from xylarium.kernel import fertility
    gen = fertility.generation_of(kernel, planet) if planet is not None else fertility.generation_years()
    return max(0.0, float(sol)) / max(1e-12, COLONY_TAX_PER_CAPITA * 100.0 * max(1.0, gen))


def set_people(x: Any, value: float, weight: float = 0.0) -> None:
    """A people given an alignment (a genesis, a founding, a steward's scenario): a history of `weight` lives that
    reads as it - with no weight, what it does from now on is all that counts once it does anything."""
    value = max(-1.0, min(1.0, float(value)))
    w = max(0.0, float(weight))
    for key in ("light", "told_light"):
        _put(x, key, w * (1.0 + value) / 2.0)
    for key in ("dark", "told_dark"):
        _put(x, key, w * (1.0 - value) / 2.0)
    _put(x, "alignment", round(value, 4))


def fade(x: Any, generations: float, keep: Optional[float] = None) -> None:
    """A people's telling of its history fades as its records do: `keep` is what its best medium holds of a record
    over a generation (memory.character_keep; a telling people's by default). The history itself does not fade."""
    from xylarium.kernel import memory
    keep = (1.0 - memory.TELL_ERR) if keep is None else keep
    f = keep ** max(0.0, generations)
    for key in ("told_light", "told_dark"):
        _put(x, key, float(_get(x, key, 0.0) or 0.0) * f)


def standing(kernel: Any, who: str, among: List[str]) -> float:
    """Where a people stands among those it knows, 0 (the darkest of them) .. 1 (the lightest): how peoples read each
    other in a galaxy whatever its lean - by their histories, not against an absolute edge."""
    from xylarium.kernel import relations
    by = relations._peoples(kernel)

    def d(h: str) -> Optional[float]:
        ws = by.get(h)
        civ = getattr(max(ws, key=lambda p: p.population), "civilization", None) if ws else None
        return character(civ) if civ is not None else None
    mine = d(who)
    others = [x for x in (d(h) for h in set(among) - {who}) if x is not None]
    if mine is None or not others:
        return 0.5
    return (sum(1 for x in others if x < mine) + 0.5 * sum(1 for x in others if x == mine)) / len(others)


def scales(kernel: Any) -> Dict[str, float]:
    """What counts as a consequential act in this universe as it is now: a typical world's people, and a typical
    captain's purse (medians, re-read each quarter)."""
    from xylarium.kernel import cache

    def reckon() -> Dict[str, float]:
        pops = sorted(p.population for s in kernel.sectors.values() for p in s.planets if p.population > 0)
        purses = sorted(max(0, c.credits) for c in kernel.captains.values())
        return {"lives": float(pops[len(pops) // 2]) if pops else 1000.0,
                "sol": float(purses[len(purses) // 2]) if purses else 1000.0}
    return cache.memo(kernel, "alignment_scales", "all", reckon, max_age=25)


def measure(kernel: Any, harmed_sol: float = 0.0, helped_sol: float = 0.0, lives_lost: float = 0.0,
            lives_saved: float = 0.0, relative_to: Optional[float] = None) -> float:
    """The shift an act's consequences earn: ALIGNMENT_ACT_SCALE x tanh(net lives / a typical world's people +
    net SOL / a typical captain's purse). Saturating: no act weighs more than the gravest. An act on a whole
    people's wealth (a money's debasement) is weighed against what they held (`relative_to`): taking 1% of
    everyone's purchasing power is a 1% harm, however rich they were."""
    sc = scales(kernel)
    sol_scale = relative_to if relative_to else sc["sol"]
    x = (lives_saved - lives_lost) / max(1.0, sc["lives"]) + (helped_sol - harmed_sol) / max(1.0, sol_scale)
    return ALIGNMENT_ACT_SCALE * math.tanh(x)


def act(kernel: Any, captain: Any, key: str, harmed_sol: float = 0.0, helped_sol: float = 0.0,
        lives_lost: float = 0.0, lives_saved: float = 0.0, note: Optional[str] = None,
        destroyed_sol: float = 0.0, made_sol: float = 0.0) -> float:
    """An act judged by what it did to the order of the world: the lives it ended and spared, and the wealth it
    destroyed (a hull wrecked) or made - in lives (lives_of_sol: a generation of a person's product is a life's
    work). Wealth it only moved (`harmed_sol` taken, `helped_sol` given) is a transfer: it is kept on the record -
    others will remember it - and weighs nothing in the truth."""
    if captain is None:
        return 0.0
    rec = captain.alignment_record
    if harmed_sol:
        rec["taken_sol"] = round(float(rec.get("taken_sol", 0.0)) + float(harmed_sol), 2)
    if helped_sol:
        rec["given_sol"] = round(float(rec.get("given_sol", 0.0)) + float(helped_sol), 2)
    return _apply(kernel, captain, key, light=lives_saved + lives_of_sol(kernel, made_sol),
                  dark=lives_lost + lives_of_sol(kernel, destroyed_sol), note=note)


def deed(kernel: Any, captain: Any, key: str, scale: float = 1.0, note: Optional[str] = None,
         light: float = 0.0, dark: float = 0.0) -> float:
    """A deed on the record (`key`), with what it made (`light`) and took (`dark`) in lives. A deed with neither - a
    conviction, an oath kept, a thing observed - is a judgement or a record: it is kept, and weighs nothing."""
    if captain is None:
        return 0.0
    return _apply(kernel, captain, key, light=light * scale, dark=dark * scale, note=note)


def _apply(kernel: Any, captain: Any, key: str, light: float = 0.0, dark: float = 0.0,
           note: Optional[str] = None) -> float:
    rec = captain.alignment_record
    deeds = rec.setdefault("deeds", {})
    deeds[key] = deeds.get(key, 0) + 1
    if light <= 0 and dark <= 0:
        return captain.cosmic_alignment
    old = captain.cosmic_alignment
    old_band = band(old)
    rec.setdefault("alignment", old)
    flow(rec, light=light, dark=dark)
    captain.cosmic_alignment = round(float(rec["alignment"]), 5)
    if dark > 0:
        rec["dark_q"] = rec.get("dark_q", 0) + 1
    if light > 0:
        rec["light_q"] = rec.get("light_q", 0) + 1
    new_band = band(captain.cosmic_alignment)
    if new_band != old_band:
        rec["band"] = new_band
        chron = getattr(kernel, "chronicle", None) if kernel is not None else None
        if chron is not None:
            from xylarium.kernel import chronicle as chron_mod
            chron_mod.log_turning(kernel, captain, old_band, new_band, note or key)
    _check_warrant(kernel, captain, old)
    return captain.cosmic_alignment


def earned(kernel: Any, captain: Any, key: str, before_credits: Optional[float]) -> float:
    """Honest work: what a captain earned by it (its credits since `before_credits`) is order made for others."""
    if captain is None or before_credits is None:
        return 0.0
    return deed(kernel, captain, key, light=lives_of_sol(kernel, max(0.0, captain.credits - before_credits)))


def _check_warrant(kernel: Any, captain: Any, old: float) -> None:
    rec = captain.alignment_record
    value = captain.cosmic_alignment
    if value <= ALIGNMENT_WARRANT_THRESHOLD < old and not rec.get("warrant"):
        rec["warrant"] = True
        captain.bounty += ALIGNMENT_WARRANT
        captain.bounty_placed_by = captain.bounty_placed_by or "Federal Prosecutor"
        if kernel is not None and getattr(kernel, "event_bus", None):
            kernel.event_bus.broadcast_radio(
                sender="FED-PROSECUTOR",
                text=f"WARRANT: {captain.name} has fallen into Umbral darkness; public bounty +{ALIGNMENT_WARRANT:,} Cr.",
                channel="ALERT", sector_id=1,
            )
    elif value > ALIGNMENT_WARRANT_THRESHOLD + 0.2 and rec.get("warrant"):
        rec["warrant"] = False


def vow_forbids(captain: Any, action: Any, kwargs: Dict[str, Any], kernel: Any) -> Optional[str]:
    """At the poles, vows bind. Returns a refusal message, or None if the deed is allowed."""
    value = getattr(captain, "cosmic_alignment", 0.0)
    if abs(value) < ALIGNMENT_VOW:
        return None
    name = getattr(action, "value", str(action))
    sub = str(kwargs.get("sub_action") or "").lower()
    if value >= ALIGNMENT_VOW:
        if name == "ATTACK_SHIP":
            target = kernel.captains.get(kwargs.get("target_id")) if kernel is not None else None
            lawful_prey = target is not None and (target.bounty > 0 or getattr(target.personality, "value", "")
                                                  in ("pirate", "crusader"))
            if not lawful_prey:
                return "Your oath of Light forbids opening fire on a captain who has done no wrong."
        if name in ("ATTACK_PLANET", "SURFACE_INVADE", "COVERT_OP", "STRIKE_WORLD"):
            return "Your oath of Light forbids war on a living world."
        if name == "NATIVE_INTERACT" and sub in ("exploit", "convert"):
            return "Your oath of Light forbids exploiting a people who cannot yet reach the stars."
        if name == "SELL_ARTIFACT" and kernel is not None:
            art = next((a for a in captain.artifacts if a.get("id") == kwargs.get("artifact_id")), None)
            if art and art.get("provenance") != "licensed":
                return "Your oath of Light forbids fencing looted heritage."
    else:
        if name == "IDEOLOGY_AID_DISPATCH":
            return "The Dark in you will not feed the weak."
        if name == "NATIVE_INTERACT" and sub in ("uplift", "protect"):
            return "The Dark in you will not lift a lesser people."
        if name == "IDEOLOGY_TREATY_PROPOSE":
            return "The Dark in you signs no peace."
    return None


def price_factor(captain: Any, direction: str) -> float:
    """Trade friction from reputation: trusted captains buy cheaper; Shadowed ones pay and are paid worse."""
    value = getattr(captain, "cosmic_alignment", 0.0)
    if direction == "buy":
        if value >= NEUTRAL_EDGE:
            return 1.0 - ALIGNMENT_GOODWILL_MAX * (value - NEUTRAL_EDGE) / (1 - NEUTRAL_EDGE)
        if value <= -NEUTRAL_EDGE:
            return 1.0 + ALIGNMENT_FRICTION_MAX * (-value - NEUTRAL_EDGE) / (1 - NEUTRAL_EDGE)
        return 1.0
    if value <= -NEUTRAL_EDGE:
        return 1.0 - ALIGNMENT_FRICTION_MAX * (-value - NEUTRAL_EDGE) / (1 - NEUTRAL_EDGE)
    return 1.0


def quarterly(kernel: Any) -> None:
    """Fiscal-quarter pass: a captain's own telling of its deeds fades as a telling does (its history does not); Dark
    crews neglect their hulls."""
    from xylarium.kernel import fertility
    from xylarium.kernel.market import FISCAL_QUARTER_CYCLES
    gens = (FISCAL_QUARTER_CYCLES / 100.0) / fertility.generation_years()
    for cap in kernel.captains.values():
        rec = cap.alignment_record
        fade(rec, gens)
        value = cap.cosmic_alignment
        if value <= -NEUTRAL_EDGE:
            wear = int(cap.ship.max_shields * ALIGNMENT_HULL_WEAR * (-value))
            cap.ship.shields = max(0, cap.ship.shields - wear)
        rec["dark_q"] = 0
        rec["light_q"] = 0


def census(kernel: Any) -> Dict[str, Any]:
    """Alignment census of all captains (for the harness and the Library's galactic history)."""
    caps = list(kernel.captains.values())
    if not caps:
        return {"mean": 0.0, "light": 0, "neutral": 0, "dark": 0, "n": 0}
    sides = {"light": 0, "neutral": 0, "dark": 0}
    for c in caps:
        sides[side(c.cosmic_alignment)] += 1
    return {"mean": round(sum(c.cosmic_alignment for c in caps) / len(caps), 4), "n": len(caps), **sides}
