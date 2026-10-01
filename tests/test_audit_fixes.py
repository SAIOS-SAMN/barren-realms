"""
What the live universes taught us: firms keep the cash they earn, money set aside for fleets that cannot sail goes
back to the vault, strains are demes of their own, nobody is made from nothing, and the dead stay dead.
"""

import random
import unittest

from xylarium.kernel import demography, enterprise, genome
from xylarium.kernel.archaeology import ArchaeologyManager
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply


def fresh(rseed=41):
    random.seed(rseed)
    k = GameKernel(seed=7)
    k.activate()
    return k


def money(k):
    return {c: b["total"] for c, b in money_supply(k).items()}


def civ_worlds(k):
    return [p for s in k.sectors.values() for p in s.planets
            if p.population > 0 and p.civilization is not None and p.owner_id is None and not p.natives]


class TestAuditFixes(unittest.TestCase):
    def test_a_process_firm_keeps_its_cash_through_the_quarter(self):
        k = fresh()
        for w in civ_worlds(k):
            if enterprise._port(k, w) is not None:
                break
        else:
            self.skipTest("no world with a port of its money")
        w.treasury = 10 ** 6
        enterprise.found(k, w, "EQUIPMENT", 10)
        ticker = next(iter(enterprise.stats(k)["firms"]))
        comp = k.market_manager.companies[ticker]
        comp.home_cash = 50_000
        k.market_manager._company_operating_spend(k)
        self.assertEqual(comp.home_cash, 50_000)

    def test_escrow_for_a_fleet_that_finds_no_world_returns_to_the_vault(self):
        k = fresh()
        w = civ_worlds(k)[0]
        for s in k.sectors.values():                          # nowhere left to go
            for p in s.planets:
                if demography.free_world(p):
                    p.population = 1
        w.diaspora_escrow = 10 ** 7
        w.crowded_cycles = 10 ** 6
        w.population = max(w.population, 50_000)
        w.citadel_level = 3
        w.last_daughter_quarter = -10 ** 6
        from unittest import mock
        from xylarium.kernel import nursery
        m0, t0 = money(k), w.treasury
        with mock.patch.object(nursery, "viable", lambda p: True), \
                mock.patch.object(nursery, "kit_room", lambda kk, p, m, n: n):
            demography.send_settlers(k, w)
        self.assertEqual(demography.stats(k)["no_room"], 1)
        self.assertEqual(w.diaspora_escrow, 0)
        self.assertEqual(w.treasury, t0 + 10 ** 7)
        self.assertEqual(m0, money(k))

    def test_a_strain_is_measured_against_its_own_kind(self):
        k = fresh()
        w = next(p for s in k.sectors.values() for p in s.planets if p.population > 0 and not p.natives)
        w.owner_id = w.owner_id or "someone"
        w.civilization = None
        genome.speciate(k, w, "captain:someone")
        lineage = w.society.get("lineage")
        self.assertTrue(lineage)
        self.assertTrue(genome.deme(k, w).endswith(lineage))
        d = next(p for s in k.sectors.values() for p in s.planets if p is not w)
        genome.inherit(w, d)
        self.assertEqual(d.society.get("lineage"), lineage)
        self.assertEqual(genome.stats(k)["born_of"]["captain:someone"], 1)

    def test_bombs_and_famine_never_make_people(self):
        k = fresh()
        from xylarium.kernel.colony import ColonyManager
        w = civ_worlds(k)[0]
        w.population = 60
        w.society["self_sufficiency"] = None
        before = w.population
        ColonyManager.tick_colony(w, kernel=k)
        self.assertLessEqual(w.population, before + 10)      # births at most, never lifted to a floor

    def test_a_remnant_its_land_cannot_feed_dies(self):
        k = fresh()
        w = civ_worlds(k)[0]
        w.population = 120
        w.faction_id = "ZEALOT"
        self.assertTrue(ArchaeologyManager.check_collapse(w, True, k))
        self.assertEqual(w.population, 0)
        self.assertIsNone(w.faction_id)
        self.assertIsNone(w.civilization)

    def test_a_pirate_bounty_is_paid_from_the_reserve_not_minted(self):
        k = fresh()
        from xylarium.kernel.ai import AIManager
        if "ai_ironclaw" not in k.captains:
            self.skipTest("no bounty office captain")
        hunter = next(c for c in k.captains.values() if c.id != "ai_ironclaw")
        m0, before = money(k), hunter.credits
        AIManager.handle_event(k, {"event": "SHIP_DESTROYED", "data": {
            "attacker_id": hunter.id, "attacker_name": hunter.name, "defender_name": "a pirate",
            "defender_personality": "pirate", "defender_id": "x", "sector_id": 1}})
        self.assertEqual(m0, money(k))
        self.assertGreater(hunter.credits, before)

    def test_a_remembered_port_that_changed_money_is_not_paid_in_the_old_one(self):
        k = fresh()
        from xylarium.kernel.colony import ColonyManager
        from xylarium.kernel import demography
        w = next(p for p in civ_worlds(k) if ColonyManager._contractor_port(p, k) is not None)
        port = ColonyManager._contractor_port(w, k)
        port.currency = next(c for c in ("FRN", "THR", "VOID", "SOL") if c != w.currency)   # the dock rehomed
        again = ColonyManager._contractor_port(w, k)
        self.assertTrue(again is None or again.currency == w.currency)
        self.assertTrue(all(p.currency == w.currency for p in demography._markets(k, w)))

    def test_port_income_decays_when_nothing_is_bought(self):
        k = fresh()
        port = next(s.port for s in k.sectors.values() if s.port is not None)
        port.consumed = {}
        port.regional_income = 1000.0
        type(k.market_manager)._port_retail(k)
        self.assertAlmostEqual(port.regional_income, 700.0)


if __name__ == "__main__":
    unittest.main()
