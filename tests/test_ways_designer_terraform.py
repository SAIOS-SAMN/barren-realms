"""
Foragers, farmers and states; designed peoples seeded on empty worlds; worlds remade for a biology. Each is physics
plus a choice: Lindeman's tenth, Lande's selection on crops, Franklin's 500 founders, an atmosphere's year of mixing.
"""

import math
import unittest

from xylarium.kernel import biosphere, designer, knowledge, terraform, ways
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType


def _peoples(k):
    return [p for s in k.sectors.values() for p in s.planets if p.population > 0 and not p.natives]


class TestWays(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = GameKernel(seed=7, genesis="forager")
        cls.k.activate()

    def test_foragers_live_a_link_up_the_food_chain(self):
        p = _peoples(self.k)[0]
        self.assertEqual(ways.way(p), "forage")
        self.assertAlmostEqual(ways.k_factor(self.k, p), ways.TROPHIC_EFFICIENCY)
        farmed = biosphere.carrying_capacity(self.k, p) / p.society["way_k"]
        self.assertLessEqual(p.population, int(farmed * ways.TROPHIC_EFFICIENCY) + 1)
        self.assertEqual(p.treasury, 0)

    def test_no_state_no_tax(self):
        p = _peoples(self.k)[0]
        self.assertEqual(ways.taxable(p), 0.0)
        before = p.treasury
        for _ in range(5):
            self.k.tick_simulation()
        self.assertEqual(p.treasury, before)

    def test_crops_are_bred_and_stay_bred(self):
        p = _peoples(self.k)[1]
        p.society["way"] = "farm"
        knowledge.learn(self.k, knowledge.holder_of_planet(p), "biology", 200)
        z0 = ways.crop_z(p)
        ways._breed(self.k, p)
        self.assertGreater(ways.crop_z(p), z0)
        self.assertGreater(ways.k_factor(self.k, p), ways.TROPHIC_EFFICIENCY)
        p.society["crop_z"] = 99.0
        ways._breed(self.k, p)
        self.assertAlmostEqual(ways.crop_z(p), math.log(1 / ways.TROPHIC_EFFICIENCY), places=5)
        self.assertAlmostEqual(ways.k_factor(self.k, p), 1.0, places=5)

    def test_older_universes_are_states_as_before(self):
        k = GameKernel(seed=7, genesis="primordial")
        p = _peoples(k)[0]
        self.assertEqual(ways.way(p), "state")
        self.assertEqual(ways.k_factor(k, p), 1.0)


def _captain_at_empty_world(k, types=("TERRESTRIAL", "OCEANIC")):
    pl = k.register_player("maker", "Maker")
    pl.credits = 10 ** 7
    pl.turns_left = 1000
    s, p = next((s, p) for s in k.sectors.values() for p in s.planets
                if p.population == 0 and not p.natives and p.planet_type in types)
    k.sectors[pl.sector_id].captains.remove(pl.id)
    pl.sector_id = s.id
    s.captains.append(pl.id)
    return pl, p


class TestDesigner(unittest.TestCase):
    def test_you_get_what_you_know(self):
        k = GameKernel(seed=5)
        k.activate()
        pl, p = _captain_at_empty_world(k)
        h = knowledge.holder_of_captain(pl)
        asked = {"tolerance": 1.0}
        m = designer.mastery(k, h)
        self.assertAlmostEqual(designer.build(k, h, asked)["tolerance"], round(m, 6))
        self.assertEqual(designer.build(k, h, asked, full=True)["tolerance"], 1.0)
        self.assertGreater(designer.cost(k, h, {"tolerance": 1.0}), designer.cost(k, h, {"tolerance": 0.1}))

    def test_what_is_not_understood_is_mystery(self):
        from xylarium.kernel import crystal as C, intellect, scheduler
        k = GameKernel(seed=5)
        k.activate()
        pl, p = _captain_at_empty_world(k)
        h = knowledge.holder_of_captain(pl)
        asked = {"tolerance": 0.5}
        self.assertTrue(all(x.endswith("???") for x in designer.describe(designer.expect(k, h, asked))))
        full = designer.expect(k, h, asked, full=True)
        self.assertEqual(full["tolerance"]["sd"], 0.0)
        self.assertEqual(designer.describe(full)[1], "tolerance +0.50")
        for d in ("biology", "energy", "materials", "information"):
            knowledge.learn(k, h, d, 10 ** 6)
        intellect.stats(k)["vocab"][h] = [C.ROT90, C.FLIPH] + list(C.STACK_OPS + C.HYPER_OPS)
        self.assertGreater(min(designer.understanding(k, h).values()), 0.95)    # full science and mathematics
        # the same design in the same universe comes out the same; what it was not sure of, it learns by seeding
        a = designer.build(k, None, asked, rng=scheduler.rng(k, "design", "x"))
        b = designer.build(k, None, asked, rng=scheduler.rng(k, "design", "x"))
        self.assertEqual(a, b)

    def test_seeding_a_world_makes_foragers_who_survive(self):
        k = GameKernel(seed=5)
        k.activate()
        pl, p = _captain_at_empty_world(k)
        r = k.dispatch(pl.id, ActionType.SPECIES_SEED, planet_id=p.id, metabolism="biotic", body_plan="mycotiform",
                       name="Sporefolk")
        self.assertTrue(r.success, r.message)
        self.assertEqual(ways.way(p), "forage")
        self.assertEqual(p.civilization.name, "Sporefolk")
        for _ in range(60):
            k.tick_simulation()
        self.assertGreater(p.population, 0)

    def test_no_niche_no_seeding(self):
        k = GameKernel(seed=5)
        k.activate()
        pl, p = _captain_at_empty_world(k)
        pv = designer.preview(k, knowledge.holder_of_captain(pl), {"metabolism": "plasmic"}, p)
        self.assertIsNotNone(pv["why_not"])


class TestTerraform(unittest.TestCase):
    def test_a_world_converges_to_the_target_ground_for_every_biology(self):
        k = GameKernel(seed=5)
        k.activate()
        pl, p = _captain_at_empty_world(k, ("ICE", "DESERT", "BARREN"))
        before = biosphere.carrying_capacity(k, p, metabolism="biotic")
        terraform.step(k, p, terraform.ideal_ground("biotic"), 3.0)
        self.assertGreater(biosphere.carrying_capacity(k, p, metabolism="biotic"), before)
        fit = terraform.reshape(0.0, "biotic", p)          # a biology that could not live here at all
        self.assertGreater(fit, 0.9)

    def test_rate_is_bounded_by_an_atmospheres_mixing(self):
        k = GameKernel(seed=5)
        k.activate()
        pl, p = _captain_at_empty_world(k)
        h = knowledge.holder_of_captain(pl)
        knowledge.learn(k, h, "materials", 10 ** 6)
        self.assertLessEqual(terraform.rate(k, h), 0.25 / terraform.MIXING_YEARS + 1e-9)

    def test_giants_cannot_be_given_ground(self):
        k = GameKernel(seed=5)
        g = next(p for s in k.sectors.values() for p in s.planets if p.planet_type == "GAS_GIANT")
        self.assertFalse(terraform.can(g))


if __name__ == "__main__":
    unittest.main()
