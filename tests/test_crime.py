"""
Crime: pedigree with variance, the reckoning of gain against presence, temperament and conscience.
"""

import random
import unittest

from xylarium.kernel import crime, law, matter
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply


def totals(kernel):
    return {c: b["total"] for c, b in money_supply(kernel).items()}


class TestPedigree(unittest.TestCase):
    def setUp(self):
        random.seed(95)
        self.kernel = GameKernel(seed=7)
        self.kernel.activate()
        self.kernel.tick_simulation = lambda: None

    def test_outlaw_houses_run_hot_and_members_vary_around_their_house(self):
        outlaw = {"id": "h-out", "creed": "outlaw"}
        honest = {"id": "h-hon", "creed": "mercantile"}
        self.assertGreater(crime.house_streak(outlaw), crime.house_streak(honest))
        self.kernel.npc_lineages = getattr(self.kernel, "npc_lineages", {}) or {}
        self.kernel.npc_lineages["h-out"] = outlaw
        a = self.kernel.register_player("cadet-a", "A")
        b = self.kernel.register_player("cadet-b", "B")
        a.house_id = b.house_id = "h-out"
        sa, sb = crime.streak(self.kernel, a), crime.streak(self.kernel, b)
        self.assertNotEqual(sa, sb)                                         # siblings differ
        self.assertLess(abs(sa - outlaw["criminality"]), 0.35)              # but share the blood
        self.assertEqual(sa, crime.streak(self.kernel, a))                  # and it is stable

    def test_conscience_bold_and_blood_decide(self):
        g = 10_000
        saint = crime.utility(g, 0.8, {"risk": 0.5, "caution": 2.0}, 0.8, 0.1)
        rogue = crime.utility(g, 0.1, {"risk": 2.0, "caution": 0.5}, -0.8, 0.9)
        self.assertLess(saint, 0)
        self.assertGreater(rogue, 0)
        # the same rogue in Sol's shadow thinks again
        self.assertLess(crime.utility(g, 0.9, {"risk": 1.0, "caution": 1.0}, -0.8, 0.9), 0)
        # only the deep Dark pays no moral cost
        self.assertEqual(crime.moral_cost(-0.7), 0.0)
        self.assertGreater(crime.moral_cost(-0.3), 0.0)
        bold = {"risk": 3.0, "caution": 0.3}
        # the Light never profits by crime, even with a dirty streak where no law reaches
        self.assertLess(crime.utility(g, 0.0, bold, 0.3, 0.5), 0)
        # the grey middle: a clean pedigree abstains; a strong streak in a lawless sector may not
        self.assertLess(crime.utility(g, 0.0, bold, 0.0, 0.15), 0)
        self.assertGreater(crime.utility(g, 0.0, bold, 0.0, 0.8), 0)
        # and a deed that risks the hull weighs on a cautious mind
        self.assertLess(crime.utility(g, 0.0, {"risk": 1.0, "caution": 2.0}, -0.8, 0.9, downside=8_000), 0)


class TestCrimeQuarter(unittest.TestCase):
    def setUp(self):
        random.seed(97)
        self.kernel = GameKernel(seed=7)
        self.kernel.activate()
        self.kernel.tick_simulation = lambda: None

    def test_skims_and_raids_move_money_and_matter_without_creating_any(self):
        k = self.kernel
        owner = k.register_player("baron", "Baron")
        owner.is_ai = True
        owner.cosmic_alignment = -1.0
        owner.traits = {"risk": 3.0, "caution": 0.3, "thrift": 1, "ambition": 1, "horizon": 1, "spend": 0.1,
                        "calling": "trader"}
        k.npc_lineages = getattr(k, "npc_lineages", {}) or {}
        k.npc_lineages["h-dark"] = {"id": "h-dark", "criminality": 1.0}
        owner.house_id = "h-dark"
        world = next(p for s in k.sectors.values() for p in s.planets
                     if law.presence(k, s) < 0.5 and p.civilization is None and not p.natives)
        world.owner_id = owner.id
        world.treasury = 1_000_000
        # a dark civilization with a granary-rich neighbour in its system
        raider = next(p for s in k.sectors.values() for p in s.planets
                      if p.civilization is not None and p.owner_id is None and p.population > 0
                      and any(w is not p and w.population > 0 for w in s.planets))
        raider.civilization.alignment = -1.0
        for w in k.sectors[raider.sector_id].planets:
            if w is not raider and w.population > 0:
                w.organics_silo = 50_000
        t0, n0 = matter.totals(k), k.matter.net()
        m0 = totals(k)
        filed = law.docket(k)["stats"]["filed"]
        for _ in range(4):
            crime.quarter(k)
            k.cycle_count += 1
        self.assertGreater(k.crime_stats["skimmed_sol"], 0)
        self.assertGreater(k.crime_stats["raids"], 0)
        self.assertLess(world.treasury, 1_000_000)
        self.assertEqual(m0, totals(k))                                        # transfers only
        self.assertGreater(law.docket(k)["stats"]["filed"], filed)             # every skim goes on the docket
        t1, n1 = matter.totals(k), k.matter.net()
        undeclared = {c: d for c in set(t0) | set(t1) | set(n1)
                      if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}
        self.assertEqual(undeclared, {})


if __name__ == "__main__":
    unittest.main()
