"""
The workbench: designs are held to volume, power and mass; they register as hulls, are built from yard materials,
earn their designers royalties, and a liner's decks decide how much its guests pay.
"""

import random
import unittest

from xylarium.config import SHIP_CATALOG
from xylarium.kernel import matter, propulsion, shipdesign, tourism
from xylarium.kernel.economy import EconomyManager
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.models import ActionType


def undeclared(kernel, t0, n0):
    t1, n1 = matter.totals(kernel), kernel.matter.net()
    return {c: d for c in set(t0) | set(t1) | set(n1)
            if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}


class TestWorkbench(unittest.TestCase):
    def setUp(self):
        random.seed(141)
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.k.tick_simulation = lambda: None
        self.d = self.k.register_player("draughtsman", "Draughtsman")
        self.d.credits = 10 ** 6
        self.d.rank_tier = 3

    def test_the_laws_of_the_workbench(self):
        self.assertTrue(shipdesign.evaluate("corvette", {"hold": 200, "drive": 1, "tank": 2})["faults"])  # too big
        self.assertTrue(any("Reactors" in f for f in
                            shipdesign.evaluate("corvette", {"shield": 10, "drive": 1, "tank": 2})["faults"]))
        self.assertTrue(shipdesign.evaluate("corvette", {"hold": 10})["faults"])                         # no drive
        ok = shipdesign.evaluate("corvette", {"drive": 1, "reactor": 1, "tank": 4, "hold": 40})
        self.assertEqual(ok["faults"], [])
        heavy = shipdesign.evaluate("cruiser", {"drive": 1, "reactor": 2, "tank": 4, "armor": 100})
        self.assertEqual(heavy["move_turns"], 2)                                   # one drive can't move that mass

    def test_a_design_registers_is_built_and_pays_its_designer(self):
        res = self.k.dispatch("draughtsman", ActionType.SHIP_DESIGN, name="Longhauler", frame="frigate",
                              modules={"drive": 2, "reactor": 1, "tank": 8, "hold": 90}, drive="H", royalty=0.1)
        self.assertTrue(res.success, res.message)
        self.assertEqual(SHIP_CATALOG["Longhauler"]["holds"], 90)
        buyer = self.k.register_player("buyer", "Buyer")
        buyer.credits = 10 ** 6
        buyer.rank_tier = 3
        sol = self.k.sectors[1]
        EconomyManager.ensure_port_inventory(sol.port)
        sol.port.stock.update({"Fe": 1000, "Ti": 1000, "Si": 1000})
        buyer.sector_id = 1
        before = self.d.credits
        t0, n0 = matter.totals(self.k), self.k.matter.net()
        res = self.k.dispatch("buyer", ActionType.SHIPYARD_PURCHASE, item="upgrade_ship", ship_name="Longhauler")
        self.assertTrue(res.success, res.message)
        self.assertEqual(buyer.ship.ship_type, "Longhauler")
        self.assertGreater(self.d.credits, before)                                  # the royalty
        self.assertEqual(undeclared(self.k, t0, n0), {})

    def test_mass_is_what_the_drive_burns(self):
        light = shipdesign.register(self.k, self.d, "Feather", "cruiser", {"drive": 2, "reactor": 1, "tank": 6, "hold": 20})
        heavy = shipdesign.register(self.k, self.d, "Anvil", "cruiser", {"drive": 3, "reactor": 1, "tank": 6, "armor": 150})
        self.assertLess(light["mass"], heavy["mass"])
        ship = self.d.ship
        ship.ship_type = "Feather"
        b_light = propulsion.burn_for(ship)
        ship.ship_type = "Anvil"
        self.assertGreater(propulsion.burn_for(ship), b_light)

    def test_a_liner_is_drawn_for_its_guests_and_they_pay_for_the_fit(self):
        biotic = shipdesign.draft("capital", "liner", "biotic", "H")
        plasmic = shipdesign.draft("capital", "liner", "plasmic", "He-3")
        self.assertIn("water_spa", biotic)
        self.assertIn("plasma_bath", plasmic)
        self.assertNotIn("water_spa", plasmic)
        spec = shipdesign.register(self.k, self.d, "Tidewater", "capital", biotic, "H")
        self.assertGreater(spec["comfort"].get("biotic", 0), 0.9)
        self.assertEqual(spec["comfort"].get("plasmic", 0.0), 0.0)
        # a charter of biotic VIPs pays a fitting liner the full fare, a bare hull only half
        origin = next(p for p in self.k.sectors[1].planets if p.population > 0)
        origin.household_purse = 10 ** 6
        dest = next(s for s in self.k.sectors.values() if s.id != 1)
        c = {"id": "VIP-T", "origin_planet": origin.id, "origin_sector": 1, "guests": "biotic",
             "dest_sector": dest.id, "dest_name": "X", "party": 4, "escrow": 1000, "currency": origin.currency,
             "status": "IN_TRANSIT", "captain": self.d.id, "posted": 0}
        tourism.charters(self.k)[c["id"]] = c
        self.d.charter, self.d.ship.ship_type, self.d.sector_id = c["id"], "Tidewater", dest.id
        wallet = self.d.credits + sum(self.d.fx_wallet.values())
        tourism.arrive(self.k, self.d)
        self.assertEqual(self.d.credits + sum(self.d.fx_wallet.values()) - wallet, 1000)


if __name__ == "__main__":
    unittest.main()
