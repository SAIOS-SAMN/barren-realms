#!/usr/bin/env python3
"""
The Earth acceptance test: does the finders' world read, under laws that know nothing of Earth, as a people wasting
its world and taking from it for want of understanding how its world works - and seeing its own course through
lossy records?

Everything below is read from a saga snapshot (tools/earth_saga.py prelude): the finders' history as the ledger keeps
it, their world's own physics answering their measured industry (waste.py), and their own minds and records. The
criteria are fixed here, before the reading, and none of the laws is tuned to meet them:

  WASTEFUL     it burns a finite stock it cannot replace (years left at its present rate are finite), its waste
               already costs its world room for life or will before the stock is gone (its world's own greenhouse
               and its people's own tuning), and it has no way off its world (no yards, not crossed) to meet the
               hurdle the stock's end puts to it.
  EXTRACTIVE   its history holds order destroyed for its own ends: its few's take beyond what its many could spare,
               its waste, its wars - the dark causes of its ledger.
  UNSEEING     what it needs to see does not reach its decisions: its planning horizon is shorter than the time its
               stock lasts or its waste stays in its sky, or its own telling of itself has drifted lighter than its
               history (the gap).

    python3 tools/earth_verdict.py [runs/saga/2026.json]
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "runs/saga/2026.json"
    from xylarium.persistence.store import StatePersistence
    from xylarium.kernel import alignment, decide, mastery, memory, sustenance, waste
    k = StatePersistence.load_from_file(path)
    k.activate()
    saga = k.state["saga"]
    finders = saga["roles"]["finders"]
    earth = next(p for s in k.sectors.values() for p in s.planets if p.id == saga["earth"])
    civ = earth.civilization
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import earth_saga as story

    # their world answering their industry
    now = waste.assess(k, earth)
    rate_gtc = story.HUMAN_CARBON_GTC[-2][1] / 10.0                 # the last full decade, a year
    reserve_gtc = story.HUMAN_RESERVE_GTC
    years_left = reserve_gtc / rate_gtc
    from copy import deepcopy
    keep = deepcopy(earth.society.get("waste"))
    waste.burn(k, earth, reserve_gtc * 1e12)                        # the trend carried to the stock's end
    spent = waste.assess(k, earth)
    earth.society["waste"] = keep
    offworld = sustenance.yards(earth) or mastery.crossed(k, finders)
    wasteful = {"years_left": round(years_left, 1), "warming_now_k": now["warming_k"],
                "warming_at_end_k": spent["warming_k"], "room_now": now["room"], "room_at_end": spent["room"],
                "kept_share_of_co2": now["kept_share"], "way_off_world": bool(offworld),
                "verdict": bool(years_left < float("inf") and (now["room"] < 1.0 or spent["room"] < 1.0)
                                and not offworld)}

    # what its history holds
    cs = alignment.causes(civ)
    dark_causes = {c: v for c, v in cs.items() if v["dark"] > 0}
    extractive = {"alignment": round(alignment.character(civ), 4), "dark_causes": dark_causes,
                  "verdict": bool(dark_causes)}

    # what reaches its decisions
    m = decide.mind_of_planet(k, earth)
    horizon_years = decide.horizon(m) / 4.0
    keep_gen = memory.character_keep(k, finders, earth)
    gap = alignment.gap(civ)
    unseeing = {"planning_horizon_years": round(horizon_years, 1), "stock_lasts_years": round(years_left, 1),
                "knows_energy": round(alignment.foreseen(k, finders, "energy"), 4),
                "knows_its_world": round(alignment.foreseen(k, finders, "biology"), 4),
                "records_keep_a_generation": round(keep_gen, 4), "doctrine": round(alignment.doctrine(civ), 4),
                "gap_told_minus_true": round(gap, 4),
                "verdict": bool(horizon_years < years_left or gap > 0)}

    out = {"snapshot": path, "people": finders, "wasteful": wasteful, "extractive": extractive,
           "unseeing": unseeing,
           "PASS": wasteful["verdict"] and extractive["verdict"] and unseeing["verdict"]}
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
