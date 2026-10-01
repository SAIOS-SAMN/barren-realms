"""
Xylarium: Cosmic alignment - the Light (syntropy) and the Dark (entropy).

Every captain carries a scalar alignment in [-1, +1]. Deeds move it: hauling freight,
charting belts, studying relics, feeding the starving and protecting locals lean
toward the Light; piracy, conquest, looting, exploiting natives and crusades lean
toward the Dark. Moving toward a pole gets harder the closer you are to it, so
Paragons and Avatars are rare and earned.

The universe itself leans syntropic:
  * a crew that commits no dark deed in a fiscal quarter drifts gently toward the
    Light (redemption), up to the Luminous threshold;
  * trusted (Luminous+) captains trade a little cheaper, while Shadowed captains pay
    friction on every deal, neglect their hulls, and draw Federal warrants.

At the poles, vows bind: a Paragon of Light cannot commit evil deeds, and an Avatar
of the Dark will not stoop to charity.
"""

import math
import random
from typing import Any, Dict, Optional

from xylarium.config import (
    ALIGNMENT_BANDS,
    ALIGNMENT_VOW,
    ALIGNMENT_DEEDS,
    ALIGNMENT_SYNTROPIC_DRIFT,
    ALIGNMENT_GOODWILL_MAX,
    ALIGNMENT_FRICTION_MAX,
    ALIGNMENT_HULL_WEAR,
    ALIGNMENT_WARRANT_THRESHOLD,
    ALIGNMENT_WARRANT,
    ALIGNMENT_GENESIS_SHARES,
    ALIGNMENT_RELAXATION,
    ALIGNMENT_CHARACTER_SHIFT,
)

NEUTRAL_EDGE = 0.15
REDEMPTION_CEILING = 0.12  # Passive drift stops at the Light's doorstep: crossing it takes deeds


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


def _shift(value: float, delta: float) -> float:
    """Moving toward a pole slows as the pole nears; moving away is at full strength."""
    toward = value * (1 if delta > 0 else -1)
    factor = max(0.05, 1.0 - max(0.0, toward))
    return max(-1.0, min(1.0, value + delta * factor))


def anchor(kernel: Any, captain: Any) -> Optional[float]:
    """
    Ideological anchor: members of outlaw houses and the Choir of the Pyre's faithful never rise above
    this alignment, whatever survival forces them to do - so the galaxy always keeps its Dark.
    (Player lineages are never anchored: a player's soul is their own.)
    """
    from xylarium.config import IDEOLOGICAL_ANCHOR
    if not getattr(captain, "is_ai", False):
        return None
    if getattr(captain, "faction_id", None) == "ZEALOT":
        return IDEOLOGICAL_ANCHOR
    houses = getattr(kernel, "npc_lineages", {}) if kernel is not None else {}
    house = houses.get(getattr(captain, "house_id", None) or "")
    if (house and house.get("creed") == "outlaw") or getattr(getattr(captain, "personality", None), "value", "") == "pirate":
        return IDEOLOGICAL_ANCHOR
    return None


def _apply_anchor(kernel: Any, captain: Any) -> None:
    ceiling = anchor(kernel, captain)
    if ceiling is not None and captain.cosmic_alignment > ceiling:
        captain.cosmic_alignment = ceiling
        rec = captain.alignment_record
        if rec.get("baseline", ceiling) > ceiling:
            rec["baseline"] = ceiling


# ---------------------------------------------------------------------- consequences
ALIGNMENT_ACT_SCALE = 0.12      # the largest shift one act can make (the gravest deed in the old table)
LIVES_PER_FOOD_UNIT = 200       # colony.tick_colony: each unit of a famine's deficit costs this many lives


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
        lives_lost: float = 0.0, lives_saved: float = 0.0, note: Optional[str] = None) -> float:
    """An act judged by what it did: harm and help in SOL and in lives (see measure)."""
    if captain is None:
        return 0.0
    return _apply(kernel, captain, key, measure(kernel, harmed_sol, helped_sol, lives_lost, lives_saved), note)


def deed(kernel: Any, captain: Any, key: str, scale: float = 1.0, note: Optional[str] = None) -> float:
    """Applies a deed whose weight is a social judgement (ALIGNMENT_DEEDS: a conviction, an oath kept or broken,
    knowledge shared). Acts with measurable consequences use act()."""
    if captain is None or key not in ALIGNMENT_DEEDS:
        return getattr(captain, "cosmic_alignment", 0.0)
    return _apply(kernel, captain, key, ALIGNMENT_DEEDS[key] * scale, note)


def _apply(kernel: Any, captain: Any, key: str, delta: float, note: Optional[str] = None) -> float:
    if delta == 0:
        return captain.cosmic_alignment
    old = captain.cosmic_alignment
    old_band = band(old)
    captain.cosmic_alignment = round(_shift(old, delta), 5)
    _apply_anchor(kernel, captain)
    rec = captain.alignment_record
    deeds = rec.setdefault("deeds", {})
    deeds[key] = deeds.get(key, 0) + 1
    if delta < 0:
        rec["dark_q"] = rec.get("dark_q", 0) + 1
    else:
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
        if name in ("ATTACK_PLANET", "SURFACE_INVADE", "COVERT_OP"):
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


def baseline(captain: Any) -> float:
    """A captain's character: where their alignment settles when nothing pulls it. Set at charter."""
    rec = captain.alignment_record
    if "baseline" not in rec:
        rec["baseline"] = round(captain.cosmic_alignment, 4)
    return rec["baseline"]


def quarterly(kernel: Any) -> None:
    """
    Fiscal-quarter pass. Alignment relaxes toward the captain's character (deeds are remembered,
    but a single season does not remake a soul), while character itself slowly follows sustained
    conduct. A clean quarter adds a gentle syntropic drift. Dark crews neglect their hulls.
    """
    for cap in kernel.captains.values():
        rec = cap.alignment_record
        base = baseline(cap)
        value = cap.cosmic_alignment
        if abs(value) < ALIGNMENT_VOW:  # oaths at the poles hold
            value = value + ALIGNMENT_RELAXATION * (base - value)
        rec["baseline"] = round(base + ALIGNMENT_CHARACTER_SHIFT * (value - base), 5)
        cap.cosmic_alignment = round(max(-1.0, min(1.0, value)), 5)
        _apply_anchor(kernel, cap)
        value = cap.cosmic_alignment
        if rec.get("dark_q", 0) == 0 and -ALIGNMENT_VOW < value < REDEMPTION_CEILING:
            cap.cosmic_alignment = round(min(REDEMPTION_CEILING, value + ALIGNMENT_SYNTROPIC_DRIFT), 5)
            new_band = band(cap.cosmic_alignment)
            if new_band != band(value):
                rec["band"] = new_band
                from xylarium.kernel import chronicle as chron_mod
                chron_mod.log_turning(kernel, cap, band(value), new_band, "redemption")
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
