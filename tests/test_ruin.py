"""
Worlds can be stripped of their air or broken apart - by the energy it takes against their own binding, delivered
by a people that chooses to. Nothing strips a world by decree.
"""

import unittest

from xylarium.kernel import energy, matter, ruin
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType


class TestRuin(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.cap = next(c for c in self.k.captains.values())
        self.planet = next(p for s in self.k.sectors.values() for p in s.planets
                           if p.owner_id and p.owner_id != self.cap.id and not (p.body or {}).get("giant")
                           and p.population > 0)
        self.cap.sector_id = self.planet.sector_id

    def test_binding_is_the_worlds_own_physics(self):
        b = ruin.binding(self.k, self.planet)
        self.assertGreater(b["shatter_j"], 1e28)              # breaking a world is far beyond stripping its air
        self.assertGreater(b["shatter_j"], 1e3 * max(1.0, b["strip_j"]))

    def test_a_strike_lifts_air_by_the_energy_delivered_and_the_fuel_is_gone(self):
        self.cap.ship.cargo.elements["AM"] = 10 ** 9
        before = matter.ACTIVE.net().get("AM", 0) if matter.ACTIVE else None
        need = ruin.antimatter_needed(self.k, self.planet, 0.5)
        got = ruin.strike(self.k, self.cap, self.planet, need)
        self.assertTrue(got["ok"])
        if ruin.binding(self.k, self.planet)["air_kg"] > 0 or got["share"] > 0:
            self.assertLess(self.planet.society["atmosphere"], 1.0)
        self.assertEqual(self.cap.ship.cargo.elements["AM"], 10 ** 9 - need)
        if before is not None:
            self.assertEqual(matter.ACTIVE.net().get("AM", 0), before - need)   # declared: annihilated

    def test_no_fuel_no_strike(self):
        self.cap.ship.cargo.elements.pop("AM", None)
        self.assertFalse(ruin.strike(self.k, self.cap, self.planet, 5)["ok"])
        self.assertIsNone(ruin.worth_striking(self.k, self.cap, self.planet))

    def test_a_light_mind_counts_the_lives_dear(self):
        self.cap.ship.cargo.elements["AM"] = 10 ** 6
        self.cap.cosmic_alignment = 0.9
        light = ruin.worth_striking(self.k, self.cap, self.planet)
        self.cap.cosmic_alignment = -0.9
        dark = ruin.worth_striking(self.k, self.cap, self.planet)
        self.assertGreater(light["cost"], dark["cost"])

    def test_the_command_exists(self):
        self.cap.ship.cargo.elements["AM"] = 10 ** 9
        self.cap.cosmic_alignment = 0.0
        self.cap.turns = max(getattr(self.cap, "turns", 0), 10)
        res = self.k.dispatch(self.cap.id, ActionType.STRIKE_WORLD, planet_id=self.planet.id, units=1000)
        self.assertTrue(res.success, res.message)


if __name__ == "__main__":
    unittest.main()
