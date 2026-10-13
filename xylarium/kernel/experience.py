"""
Xylarium: Experience (Xi) domains and realized-revenue ledger.

Experience is a verified track record, not motion. Every award names a domain
(navigation, commerce, industry, combat, science, governance) and optionally a
repeat key; repeating the same keyed deed inside one soft-cap window halves the
award each time, and total earnings past the window's soft cap are quartered.
Starving crews learn nothing. The cochain flux vector (phylogeny.py) measures
*what* a captain does; experience measures *how well* it went. Branch selection
uses flux, branch qualification uses experience.
"""

import math
from typing import Any, Optional

from xylarium.config import (
    XP_DOMAINS,
    XP_WINDOW_CYCLES,
    XP_WINDOW_SOFT_CAP,
    XP_REPEAT_DECAY,
    XP_INDUSTRY_GROWTH_MILESTONE,
    VC_REVENUE_WINDOW,
)

GROWTH_MILESTONE_RATIO = 1.25
REVENUE_PER_CREDIT_POINT = 5000
REVENUE_HISTORY_MAX_ROWS = 200


class ExperienceManager:
    """Stateless helpers; all state lives on the Captain so it persists with saves."""

    @staticmethod
    def _cycle(kernel: Any) -> int:
        return int(getattr(kernel, "cycle_count", 0)) if kernel is not None else 0

    @classmethod
    def award(
        cls,
        captain: Any,
        domain: str,
        amount: float,
        kernel: Any = None,
        key: Optional[str] = None,
    ) -> int:
        """Awards experience in a domain after repeat decay and the window soft cap. Returns Xi granted."""
        if amount <= 0 or domain not in XP_DOMAINS or captain is None:
            return 0
        if getattr(captain, "hunger", 0) > 0:
            return 0

        cycle = cls._cycle(kernel)
        win = captain.xp_window
        if ("keys" not in win or cycle - win.get("start", 0) >= XP_WINDOW_CYCLES
                or cycle < win.get("start", 0)):
            carry = win.get("carry", 0.0) if win else 0.0
            credit_progress = win.get("credit_progress", 0) if win else 0
            win.clear()
            win.update({"start": cycle, "earned": 0.0, "carry": carry, "keys": {}, "credit_progress": credit_progress})

        if key:
            repeats = win["keys"].get(key, 0)
            amount *= XP_REPEAT_DECAY ** repeats
            win["keys"][key] = repeats + 1

        earned = win.get("earned", 0.0)
        if earned >= XP_WINDOW_SOFT_CAP:
            effective = amount * 0.25
        elif earned + amount > XP_WINDOW_SOFT_CAP:
            full = XP_WINDOW_SOFT_CAP - earned
            effective = full + (amount - full) * 0.25
        else:
            effective = amount
        win["earned"] = earned + effective

        # Fractional Xi carries so small repeated deeds are never silently lost
        total = win.get("carry", 0.0) + effective
        granted = int(math.floor(total))
        win["carry"] = total - granted
        if granted <= 0:
            return 0

        domains = captain.experience_domains
        domains[domain] = domains.get(domain, 0) + granted
        captain.adjust_experience(granted)
        return granted

    @classmethod
    def check_colony_growth(cls, captain: Any, planet: Any, kernel: Any = None) -> int:
        """Industry Xi for each +25% population milestone on an owned colony."""
        if captain is None or planet.population <= 0:
            return 0
        base = captain.colony_milestones.get(planet.id)
        if base is None:
            captain.colony_milestones[planet.id] = planet.population
            return 0
        if planet.population >= base * GROWTH_MILESTONE_RATIO:
            captain.colony_milestones[planet.id] = planet.population
            return cls.award(captain, "industry", XP_INDUSTRY_GROWTH_MILESTONE, kernel)
        if planet.population < base:
            # Famine or invasion losses lower the bar; milestones are earned, not banked
            captain.colony_milestones[planet.id] = planet.population
        return 0

    @classmethod
    def record_revenue(cls, captain: Any, amount: int, kernel: Any = None) -> None:
        """Appends realized revenue (profit, freight payouts, dividends, taxes) to the rolling ledger."""
        if amount <= 0 or captain is None:
            return
        # A verified commercial track record builds creditworthiness (+1 per 5,000 SOL realized)
        progress = captain.xp_window.get("credit_progress", 0) + int(amount)
        if progress >= REVENUE_PER_CREDIT_POINT and hasattr(captain, "adjust_credit_rating"):
            captain.adjust_credit_rating(progress // REVENUE_PER_CREDIT_POINT, reason="Realized commercial revenue")
            progress %= REVENUE_PER_CREDIT_POINT
        captain.xp_window["credit_progress"] = progress
        cycle = cls._cycle(kernel)
        hist = captain.revenue_history
        if hist and hist[-1][0] == cycle:
            hist[-1][1] += int(amount)
        else:
            hist.append([cycle, int(amount)])
        cutoff = cycle - VC_REVENUE_WINDOW
        while hist and hist[0][0] < cutoff:
            captain.xp_window["lifetime_revenue"] = captain.xp_window.get("lifetime_revenue", 0) + hist[0][1]
            hist.pop(0)
        if len(hist) > REVENUE_HISTORY_MAX_ROWS:
            # Merge the oldest rows to stay bounded without losing totals
            hist[1][1] += hist[0][1]
            hist.pop(0)

    @classmethod
    def trailing_revenue(cls, captain: Any, kernel: Any = None) -> int:
        cutoff = cls._cycle(kernel) - VC_REVENUE_WINDOW
        return sum(amt for cyc, amt in getattr(captain, "revenue_history", []) if cyc >= cutoff)
