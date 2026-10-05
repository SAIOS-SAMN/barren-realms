"""
Two peoples among the stars whose dominions met and bound themselves by a pact weigh founding common law - however
each of them crossed.
"""

import unittest

from xylarium.kernel import annals, cosmos, federation, mastery, relations, spheres, technology
from xylarium.kernel.engine import GameKernel


class TestFederationForms(unittest.TestCase):
    def test_crossed_peoples_that_meet_can_found_a_federation(self):
        k = GameKernel(seed=7, genesis="cosmic")
        k.activate()
        st = cosmos.stats(k)
        cosmos.set_rate(k, cosmos.ceiling(k))
        k.cycle_count = cosmos.cycle_at(k, st["minds"][1]["epoch"]) + 1
        cosmos._due(k)
        by = relations._peoples(k)
        a, b = sorted(by)[:2]
        for who in (a, b):
            mastery.stats(k)["crossed"][who] = k.cycle_count               # crossed by their own mathematics
            annals.stats(k)["of"].setdefault(who, {"advanced": 0.0, "passed": [], "dominion": 50, "reach": 0.0})
            home = max(by[who], key=lambda p: p.population)
            home.civilization.alignment = 0.6                              # peoples of the Light: their doctrines agree
            home.fighters, home.shields = 200, 200                         # arms enough to make law worth having
        spheres.ensure(k)                                                  # each begins its network at home
        for who in (a, b):
            spheres.stats(k)["nets"][who]["radius"] = 40.0                 # networks grown wide (as if long held)
        spheres._contact(k, a, max(by[b], key=lambda p: p.population).sector_id, [])   # a's passage reaches b
        self.assertIn(spheres.bond(k, a, b)["kind"], spheres.BONDS)       # doctrines agree: they bond
        self.assertEqual(relations.bloc(k, a), relations.bloc(k, b))       # the pact binds them into one bloc
        self.assertGreater(federation._gain(k, a, [a, b], by), 0.0)        # common law is worth something to them
        founded = 0
        for year in range(1, 30):                                          # each council weighs it on its own stream
            k.cycle_count = (k.cycle_count // 100 + 1) * 100
            federation.season(k)
            founded = len(federation.stats(k)["feds"])
            if founded:
                break
        self.assertEqual(founded, 1)


if __name__ == "__main__":
    unittest.main()
