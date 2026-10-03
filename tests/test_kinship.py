"""
When food turns out to be kin of a mind - one built like it, or one risen on a world whose life a people once ate -
the people's council chooses what that means, and the consequences follow.
"""

import unittest
from unittest import mock

from xylarium.kernel import contact, cosmos, kinship, knowledge, lifeline, relations
from xylarium.kernel.engine import GameKernel


class TestKinship(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        st = cosmos.stats(self.k)
        nxt = st["minds"][1]
        cosmos.set_rate(self.k, cosmos.ceiling(self.k))
        self.k.cycle_count = cosmos.cycle_at(self.k, nxt["epoch"]) + 1
        cosmos._due(self.k)
        self.peoples = relations._peoples(self.k)
        self.assertGreaterEqual(len(self.peoples), 2)
        self.a, self.b = sorted(self.peoples)[:2]
        self.k.cycle_count = (self.k.cycle_count // 100 + 1) * 100      # a year's turn

    def _events(self, kind):
        from xylarium.kernel import history
        return [e for e in history.of_people(self.k, self.a) if e.get("kind") == kind]

    def test_a_stranger_built_like_its_food_is_recognised_and_answered(self):
        home_a = kinship._home(self.peoples[self.a])
        plan = kinship.prey_plans(self.k, self.a, home_a)[0]
        tb = kinship._home(self.peoples[self.b]).civilization.traits
        tb["solvent"], tb["form"], tb["hands"] = plan
        with mock.patch.object(contact, "contacts", lambda k, by: {self.a: {self.b: 1}}):
            kinship.season(self.k)
        self.assertTrue(self._events("KINSHIP"))
        self.assertEqual(sum(kinship.stats(self.k)["responses"].values()), 1)
        with mock.patch.object(contact, "contacts", lambda k, by: {self.a: {self.b: 1}}):
            kinship.season(self.k)                                      # recognised once, not every year
        self.assertEqual(sum(kinship.stats(self.k)["responses"].values()), 1)

    def test_a_mind_risen_on_a_world_it_once_ate(self):
        home_b = kinship._home(self.peoples[self.b])
        kinship.stats(self.k)["ate"][self.a] = {lifeline.key(*lifeline.locate(self.k, home_b)): 0}
        kinship.on_arise(self.k, home_b)
        self.assertEqual(kinship.stats(self.k)["pending"], [[self.a, self.b, "descent"]])
        kinship.season(self.k)
        self.assertTrue(self._events("KINSHIP"))

    def test_prey_plans_never_include_its_own_shape(self):
        home_a = kinship._home(self.peoples[self.a])
        t = home_a.civilization.traits
        own = (t.get("solvent"), t.get("form"), t.get("hands"))
        self.assertNotIn(own, kinship.prey_plans(self.k, self.a, home_a))


if __name__ == "__main__":
    unittest.main()
