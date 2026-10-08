"""
Xylarium ledgers: what a people UNDERSTANDS, what it KNOWS, and what it holds UNEARNED - lined up in one reading
(docs/UNDERSTANDING_AND_KNOWLEDGE.md).

  UNDERSTANDING  what it has thought and studied without yet building with it: its knowledge stocks a domain
                 (knowledge.py: lived learning and surplus thought), the crystals its minds think with (intellect.py),
                 and the lessons its choices have taught it (learning.py).
  KNOWLEDGE      understanding it has built with: the capabilities its own understanding found and made work in its
                 world (technology.season), and the proofs its minds have built - its ladders' certificates
                 (intellect) and the court's tasks it closed (court.py).
  UNEARNED       capabilities it holds without understanding them - granted by its history's stage (annals), or dug up
                 and not yet proven (relics). Usable; not extended (nothing that builds on them is found) until its
                 understanding earns them (technology.season, by the finding's own law).

A reading, never a gate: the laws that use each ledger read their own stores; this lines them up for a steward, a
seat's percept, or a person watching.
"""

from typing import Any, Dict, Optional


def read(kernel: Any, who: Optional[str]) -> Dict[str, Any]:
    from xylarium.kernel import intellect, knowledge, technology
    st = getattr(kernel, "state", {}) or {}
    stocks = dict(knowledge.stocks(kernel, who)) if who else {}
    une = technology.unearned(kernel, who)
    held = dict(technology.stats(kernel)["of"].get(who, {})) if "technology" in st and who else {}
    lessons = 0
    if "learning" in st and who:
        from xylarium.kernel import learning
        lessons = sum(1 for o in ((learning.stats(kernel)["of"].get(who) or {}).get("opts") or {}).values()
                      if o.get("n", 0) > 0)
    proofs = len((intellect.stats(kernel).get("proofs") or {}).get(who) or []) if "intellect" in st and who else 0
    gauge = intellect.gauge(kernel, who) if "intellect" in st and who else {}
    closed = 0
    if "court" in st and who:
        from xylarium.kernel import court
        closed = int((court.stats(kernel)["of"].get(who) or {}).get("closed", 0))
    return {
        "understanding": {"domains": stocks, "crystals": len(intellect.vocabulary(kernel, who)) if who else 0,
                          "lessons": lessons},
        "knowledge": {"built": sorted(c for c in held if c not in une), "ladders": gauge, "proofs": proofs,
                      "court_closed": closed},
        "unearned": une,
    }
