"""
Past the metabolic bound: a people stops waiting on its own generations by genetics (rewriting itself), synthesis
(chemistry built to order) or robotics (bodies built, not bred) - each found on its own knowledge, where its world
allows it.
"""

import unittest

from xylarium.kernel import annals, knowledge, lifespan, technology, terraform
from xylarium.kernel.engine import GameKernel


class TestMultipath(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.p = max((p for s in self.k.sectors.values() for p in s.planets), key=lambda p: p.population)
        self.who = knowledge.holder_of_planet(self.p)
        self.held = technology.stats(self.k)["of"].setdefault(self.who, {})

    def test_paths_rest_on_what_came_before(self):
        self.assertFalse(technology.feasible(self.k, self.who, "genetics", self.p))
        self.held.update(medicine=1, computation=1)
        self.assertTrue(technology.feasible(self.k, self.who, "genetics", self.p))
        self.assertFalse(technology.feasible(self.k, self.who, "synthesis", self.p))

    def test_robotics_needs_metal_in_its_own_system(self):
        self.held["computation"] = 1
        saved = {p.id: dict(p.element_deposits) for p in self.k.sectors[self.p.sector_id].planets}
        for p in self.k.sectors[self.p.sector_id].planets:
            p.element_deposits.pop("Fe", None)
        self.assertFalse(technology.feasible(self.k, self.who, "robotics", self.p))
        self.p.element_deposits["Fe"] = 10
        self.assertTrue(technology.feasible(self.k, self.who, "robotics", self.p))
        for p in self.k.sectors[self.p.sector_id].planets:
            p.element_deposits = saved[p.id]

    def test_each_path_lifts_its_bound(self):
        e0, m0, s0 = knowledge.effort(self.k, self.p), lifespan.medicine(self.k, self.p), annals._speed(self.k, self.p)
        self.held.update(robotics=1, genetics=1)
        if e0 > 0:                                           # a people with thought to spare
            self.assertGreater(knowledge.effort(self.k, self.p), e0)
        self.assertGreater(lifespan.medicine(self.k, self.p), m0)
        self.assertGreater(annals._speed(self.k, self.p), s0)


if __name__ == "__main__":
    unittest.main()
