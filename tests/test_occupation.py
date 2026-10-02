"""
A world taken by force keeps its people; holding it costs policing in proportion to how foreign the occupier is, and
an occupation the world cannot pay for ends in revolt. Assaults resolve by Lanchester's square law.
"""

import unittest

from xylarium.kernel import biosphere, occupation
from xylarium.kernel.engine import GameKernel


def _colony_and_rival(k):
    owner, rival = [c for c in k.captains.values() if c.is_ai][:2]
    p = next(p for s in k.sectors.values() for p in s.planets if p.population == 0 and not p.natives)
    p.owner_id, p.population = owner.id, 20000
    owner.metabolism, rival.metabolism = "biotic", "plasmic"
    return owner, rival, p


class TestOccupation(unittest.TestCase):
    def test_lanchester(self):
        r = occupation.lanchester(5, 3)
        self.assertEqual(r["won"], 1.0)
        self.assertAlmostEqual(r["attacker_left"], 4.0)
        self.assertEqual(occupation.lanchester(3, 5)["won"], 0.0)

    def test_the_conquered_keep_their_biology_and_resist_the_foreign(self):
        k = GameKernel(seed=9)
        k.activate()
        owner, rival, p = _colony_and_rival(k)
        occupation.conquer(k, p, rival, "test")
        p.owner_id = rival.id
        self.assertEqual(biosphere.metabolism_of(k, p), "biotic")
        f0 = occupation.foreignness(k, p)
        self.assertGreater(f0, 0.9)                         # a plasmic ruler barely perceives biotic subjects
        self.assertLess(occupation.compliance(k, p), 0.1)
        k.cycle_count += 100 * 200                          # generations later: still themselves, still foreign
        self.assertAlmostEqual(occupation.foreignness(k, p), f0)
        self.assertEqual(biosphere.metabolism_of(k, p), "biotic")
        self.assertLess(occupation.births_factor(k, p), 0.1)    # a demography in controlled decline

    def test_symbiosis_dissolves_resistance(self):
        """In this chemistry no two biologies feed each other both ways (biotic water feeds the Stillcold, their
        hydrogen the plasmic, nothing feeds back) - so the rule is checked on a mutualism that could exist."""
        from unittest import mock
        k = GameKernel(seed=9)
        k.activate()
        owner, rival, p = _colony_and_rival(k)
        occupation.conquer(k, p, rival, "test")
        p.owner_id = rival.id
        self.assertFalse(occupation.symbiotic(k, p))
        with mock.patch("xylarium.kernel.cohabit.effect", return_value=1.0):
            self.assertTrue(occupation.symbiotic(k, p))
            self.assertEqual(occupation.foreignness(k, p), 0.0)
            self.assertEqual(occupation.births_factor(k, p), 1.0)

    def test_unpaid_occupation_ends_in_revolt(self):
        k = GameKernel(seed=9)
        k.activate()
        owner, rival, p = _colony_and_rival(k)
        occupation.conquer(k, p, rival, "test")
        p.owner_id = rival.id
        p.treasury = 0
        for _ in range(4):
            occupation.quarter(k)
            if p.owner_id is None:
                break
        self.assertIsNone(p.owner_id)
        self.assertEqual(biosphere.metabolism_of(k, p), "biotic")    # free, and still themselves

    def test_kin_retaking_their_world_is_liberation(self):
        k = GameKernel(seed=9)
        k.activate()
        owner, rival, p = _colony_and_rival(k)
        occupation.conquer(k, p, rival, "test")
        p.owner_id = rival.id
        occupation.conquer(k, p, owner, "test")
        p.owner_id = owner.id
        self.assertIsNone(occupation.record(p))


if __name__ == "__main__":
    unittest.main()
