"""
Worlds keep their stars only where passing stars leave them be; deposits are what a world's flows gathered, none
where too thin to hold a unit; ancients are the first minds by age and by the place their star was born.
"""

import unittest

from xylarium.kernel import encounters as E


class TestEncounters(unittest.TestCase):
    def test_a_close_world_deep_in_the_bulge_is_kept_and_a_wide_one_is_not(self):
        self.assertGreater(E.survival(1.0, 0.17, 3.0), 0.95)              # a 1 AU world at 170 pc: kept
        self.assertLess(E.survival(30.0, 0.17, 3.0), 0.01)                # a 30 AU one: stripped
        self.assertLess(E.survival(1.0, 0.004, 3.0), 0.01)                # inside the nuclear cluster: nothing kept
        self.assertGreater(E.survival(30.0, 8.0, 3.0), 0.99)              # the sparse disc keeps almost every world

    def test_the_stars_crowd_toward_the_centre(self):
        n = lambda r: sum(x for x, _ in E.components(r))
        self.assertGreater(n(0.004), n(0.17))
        self.assertGreater(n(0.17), n(2.0))
        self.assertGreater(n(2.0), n(8.0))
        self.assertAlmostEqual(n(8.0), E.DISC_N_R0, delta=0.01)          # the Sun's neighbourhood: ~0.1 per pc^3


class TestNoFloor(unittest.TestCase):
    def test_a_world_holds_none_of_what_is_too_thin_to_gather(self):
        from xylarium.kernel import chemistry
        from xylarium.kernel.engine import GameKernel
        k = GameKernel(seed=42)
        k.activate()
        worlds = [p for s in k.sectors.values() for p in s.planets if p.society.get("chem_surveyed")]
        heavy = ("mirror_glass", "AdL", "aetherium", "umbrite")
        holders = [p for p in worlds if any(p.element_deposits.get(x, 0) > 0 for x in heavy)]
        self.assertLess(len(holders), len(worlds))                        # not every world shows every superheavy
        why = [w for p in worlds for w in (p.society.get("withheld") or {}).values()]
        self.assertIn("dispersed", why)


class TestAncients(unittest.TestCase):
    def test_the_ancients_are_the_first_minds_by_age_and_by_their_rings_first_stars(self):
        from xylarium.kernel import cosmos, roles
        from xylarium.kernel.engine import GameKernel
        k = GameKernel(seed=7, genesis="cosmic:neighbourly")
        k.activate()
        minds = sorted(cosmos.stats(k)["minds"], key=lambda m: float(m["epoch"]))
        anc = roles.ancients(k)
        self.assertTrue(anc)
        first = float(minds[0]["epoch"])
        for m in minds:
            inside = float(m["epoch"]) - first <= cosmos.ancient_window(k)
            own = cosmos.first_of_its_ring(k, tuple(m["cell"]), int(m["k"]))
            listed = any(a["cell"] == list(m["cell"]) and a["k"] == int(m["k"]) for a in anc)
            self.assertEqual(listed, inside and own)


if __name__ == "__main__":
    unittest.main()
