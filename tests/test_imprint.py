"""
A world in play is its physics at its age plus the ledger of what minds have done to it: every act recorded once,
in order, with its maker; the world as it stands is that ledger folded; any past moment can be refolded.
"""

import unittest
from types import SimpleNamespace

from xylarium.kernel import imprint


def _world():
    return SimpleNamespace(society={}, planet_type="TERRESTRIAL")


class TestImprint(unittest.TestCase):
    def test_acts_fold_into_the_world_and_history_refolds(self):
        k, p = SimpleNamespace(cycle_count=100), _world()
        imprint.record(k, p, "stripped", "Raider", air_scale=0.5)
        self.assertAlmostEqual(p.society["atmosphere"], 0.5)
        k.cycle_count = 300
        imprint.record(k, p, "air_returned", "people:A", air_add=0.25)
        self.assertAlmostEqual(p.society["atmosphere"], 0.75)
        self.assertAlmostEqual(imprint.at(p, 200)["atmosphere"], 0.5)          # as it stood between the two
        self.assertAlmostEqual(imprint.at(p)["atmosphere"], p.society["atmosphere"])
        self.assertEqual(imprint.makers(p), {"Raider": 1, "people:A": 1})

    def test_a_slow_loss_is_one_entry_spread_over_its_years(self):
        k, p = SimpleNamespace(cycle_count=0), _world()
        for c in range(0, 100):
            k.cycle_count = c
            imprint.record(k, p, "core_stress", "people:B", air_add=-0.001)
        self.assertEqual(len(imprint.ledger(p)), 1)
        self.assertAlmostEqual(p.society["atmosphere"], 0.9, places=6)
        self.assertAlmostEqual(imprint.at(p, 49)["atmosphere"], 0.95, places=6)

    def test_a_broken_world_is_remade(self):
        k, p = SimpleNamespace(cycle_count=5), _world()
        imprint.record(k, p, "shattered", "Raider", air_set=0.0, type="BARREN")
        self.assertEqual(p.planet_type, "BARREN")
        self.assertEqual(p.society["atmosphere"], 0.0)

    def test_terraforming_is_one_work_per_ground(self):
        k, p = SimpleNamespace(cycle_count=1), _world()
        imprint.record(k, p, "terraform", "people:C", terraform={"ground": "OCEANIC", "t": 0.1})
        imprint.record(k, p, "terraform", "people:C", terraform={"ground": "OCEANIC", "t": 0.2})
        imprint.record(k, p, "terraform", "people:C", terraform={"ground": "ICE", "t": 0.1})
        self.assertEqual(len(imprint.ledger(p)), 2)
        self.assertEqual(p.society["terraform"], {"ground": "ICE", "t": 0.1})


if __name__ == "__main__":
    unittest.main()
