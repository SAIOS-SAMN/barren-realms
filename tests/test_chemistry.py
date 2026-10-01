"""
One periodic table for the universe; worlds hold what their formation let them keep; peoples dig their way in;
chemistry follows what they understand; their own society can stand in the way.
"""

import random
import unittest

from xylarium.kernel import chemistry, enterprise, knowledge, matter
from xylarium.kernel.engine import GameKernel


def fresh(rseed=21):
    random.seed(rseed)
    k = GameKernel(seed=7)
    k.activate()
    return k


def worlds(k):
    return [p for s in k.sectors.values() for p in s.planets]


class TestDistribution(unittest.TestCase):
    def test_every_world_is_surveyed_and_knows_why_it_lacks_what_it_lacks(self):
        k = fresh()
        for p in worlds(k):
            if getattr(p, "body", None):
                self.assertTrue(p.society.get("chem_surveyed"))
                for sym in p.society.get("withheld", {}):
                    self.assertNotIn(sym, p.element_deposits)

    def test_giants_hold_gas_and_rocky_worlds_hold_metal(self):
        k = fresh()
        giants = [p for p in worlds(k) if p.planet_type == "GAS_GIANT"]
        rocks = [p for p in worlds(k) if p.planet_type in ("BARREN", "TERRESTRIAL", "VOLCANIC")]
        self.assertTrue(any("H" in p.element_deposits for p in giants))
        self.assertFalse(any("Fe" in p.element_deposits for p in giants))
        self.assertTrue(any("Fe" in p.element_deposits for p in rocks))

    def test_no_world_holds_everything(self):
        k = fresh()
        for p in worlds(k):
            self.assertLess(len([s for s in p.element_deposits if s in chemistry.TABLE]), len(chemistry.TABLE))

    def test_a_small_stars_lineage_never_made_the_deep_elements(self):
        class S:                                          # an M dwarf's system
            id, star_type, star = 5, "M-class", None
        self.assertEqual(chemistry.ladder(S()), 3)


class TestDiscovery(unittest.TestCase):
    def test_peoples_dig_into_what_their_worlds_hold(self):
        k = fresh()
        for _ in range(400):
            k.tick_simulation()
        st = chemistry.stats(k)
        self.assertGreater(st["discoveries"], 0)
        for holder, known in st["known"].items():
            for sym in known:
                self.assertIn(sym, chemistry.TABLE)

    def test_chemistry_needs_every_element_and_enough_parts(self):
        k = fresh()
        holder = "captain:chemist"
        chemistry.known(k, holder)
        self.assertFalse(chemistry.can_make(k, holder, "M3_ENGINE_MANIFOLD"))      # Fe, Ti, U unknown
        chemistry.stats(k)["known"][holder] += ["Fe", "Ti", "U"]
        self.assertFalse(chemistry.can_make(k, holder, "M3_ENGINE_MANIFOLD"))      # three parts: too many to hold
        from xylarium.kernel import intellect
        intellect.stats(k)["gauge"][holder] = {"2": 3, "3": 0}
        self.assertTrue(chemistry.can_make(k, holder, "M3_ENGINE_MANIFOLD"))
        self.assertTrue(chemistry.can_make(k, holder, "EQUIPMENT"))                # ore needs no chemistry

    def test_society_can_stand_in_the_way(self):
        k = fresh()
        w = next(p for p in worlds(k) if p.civilization is not None and p.population > 0 and not p.natives)
        free = knowledge.impedance(k, w)
        w.civilization.alignment = -1.0
        self.assertLess(knowledge.impedance(k, w), free)
        w.civilization.dogma = 10.0
        self.assertEqual(knowledge.impedance(k, w), 0.0)


if __name__ == "__main__":
    unittest.main()
