"""
Regression tests for archaeology: dead civilizations become ruins with buried hoards,
precursor ruins at genesis, surveying and stratified excavation, cave-ins, provenance,
curio-desk sales from port treasuries, relic study, permits, and money conservation.
"""

import random
import unittest

from xylarium.config import ARCH_PERMIT_FEE
from xylarium.kernel.archaeology import ArchaeologyManager
from xylarium.kernel.colony import ColonyManager
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.fx import balance
from xylarium.kernel.ledger import money_supply
from xylarium.kernel.models import ActionType, SecurityLevel


def _move(kernel, cap, sector_id):
    old = kernel.sectors[cap.sector_id]
    if cap.id in old.captains:
        old.captains.remove(cap.id)
    cap.sector_id = sector_id
    kernel.sectors[sector_id].captains.append(cap.id)


class TestArchaeology(unittest.TestCase):
    def setUp(self):
        random.seed(11)
        self.kernel = GameKernel(seed=42)
        self.cap = self.kernel.register_player("digger", "Digger")
        self.cap.turns_left = 300
        self.cap.ship.cargo.capacity = 200
        self.cap.ship.cargo.equipment = 40
        self.site = next(p for s in self.kernel.sectors.values() for p in s.planets
                         if p.ruins and p.population == 0 and not p.owner_id)

    def test_precursor_ruins_seeded_at_genesis(self):
        ruins = [p for s in self.kernel.sectors.values() for p in s.planets if p.ruins]
        self.assertGreater(len(ruins), 5)
        for p in ruins:
            self.assertEqual(p.ruins["hoard"], 0)  # precursor money died with them
            self.assertGreaterEqual(len(p.ruins["strata"]), 3)

    def test_famine_collapse_buries_the_vault_without_changing_money_supply(self):
        planet = next(p for s in self.kernel.sectors.values() for p in s.planets
                      if p.civilization is not None and p.owner_id is None and p.sector_id != 1)
        planet.population = 120
        planet.organics_silo = 0
        planet.treasury = 7777
        before = {c: b["total"] for c, b in money_supply(self.kernel).items()}
        res = ColonyManager.tick_colony(planet, kernel=self.kernel)
        self.assertTrue(res.get("collapsed"))
        self.assertIsNone(planet.civilization)
        self.assertEqual(planet.population, 0)
        self.assertEqual(planet.ruins["cause"], "famine")
        self.assertEqual(planet.ruins["hoard"], 7777)
        after = {c: b["total"] for c, b in money_supply(self.kernel).items()}
        self.assertEqual(before, after)  # the treasury is buried, not destroyed

    def test_survey_then_excavate_yields_artifacts_and_consumes_tools(self):
        _move(self.kernel, self.cap, self.site.sector_id)
        self.assertFalse(self.kernel.dispatch("digger", ActionType.EXCAVATE).success)  # unsurveyed
        self.assertTrue(self.kernel.dispatch("digger", ActionType.SURVEY_RUINS).success)
        tools = self.cap.ship.cargo.equipment
        found = 0
        for _ in range(12):
            res = self.kernel.dispatch("digger", ActionType.EXCAVATE, shore=self.site.ruins["stability"] < 0.5)
            if not res.success and "bedrock" in res.message:
                break  # shallow site: every stratum dug
            self.assertTrue(res.success, res.message)
            found = len(self.cap.artifacts)
        self.assertGreater(found, 0)
        self.assertLess(self.cap.ship.cargo.equipment, tools)
        self.assertGreater(self.site.ruins["dug_depth"], 0)

    def test_recent_ruins_hoard_is_recovered_as_a_transfer(self):
        planet = self.site
        planet.ruins.update({"era": "RECENT", "hoard": 5000, "hoard_currency": planet.currency, "stability": 1.0})
        _move(self.kernel, self.cap, planet.sector_id)
        self.kernel.dispatch("digger", ActionType.SURVEY_RUINS)
        import simulate_playtest as sp
        cur = planet.currency
        before = money_supply(self.kernel)[cur]["total"]
        declared_before = sp.ledger_net(self.kernel).get(cur, 0)
        wallet = balance(self.cap, cur)
        for _ in range(6):
            self.kernel.dispatch("digger", ActionType.EXCAVATE)
        self.assertGreater(balance(self.cap, cur), wallet)
        self.assertLess(planet.ruins["hoard"], 5000)
        # Each dig also ticks the world (taxes, spending): the hoard itself must add no undeclared money
        undeclared = (money_supply(self.kernel)[cur]["total"] - before) - (sp.ledger_net(self.kernel).get(cur, 0) - declared_before)
        self.assertLessEqual(undeclared, 0)

    def test_living_cities_forbid_excavation(self):
        planet = self.site
        planet.population = 800
        _move(self.kernel, self.cap, planet.sector_id)
        self.kernel.dispatch("digger", ActionType.SURVEY_RUINS)
        res = self.kernel.dispatch("digger", ActionType.EXCAVATE)
        self.assertFalse(res.success)
        self.assertIn("forbid", res.message)

    def test_provenance_rules_and_curio_desk_pays_from_port_treasury(self):
        looted = {"id": "A1", "name": "idol", "kind": "ANTIQUITY", "culture": "X", "era": "ANCIENT", "stratum": 2,
                  "era_name": "Classical", "tech_level": 7, "condition": 0.9, "provenance": "unlicensed",
                  "origin_sector": self.site.sector_id, "elements": []}
        looted["appraisal_sol"] = ArchaeologyManager.appraisal(looted)
        fed_port = self.kernel.sectors[1]
        price, reason = ArchaeologyManager.offer(looted, fed_port, self.kernel)
        self.assertIsNotNone(reason)  # Federation collectors demand provenance
        anarchy = next(s for s in self.kernel.sectors.values() if s.port and s.security == SecurityLevel.ANARCHY)
        price, reason = ArchaeologyManager.offer(looted, anarchy, self.kernel)
        self.assertIsNone(reason)
        licensed = dict(looted, provenance="licensed", id="A2")
        fed_price, _ = ArchaeologyManager.offer(licensed, fed_port, self.kernel)
        self.assertGreater(fed_price, 0)
        self.cap.artifacts.append(licensed)
        _move(self.kernel, self.cap, 1)
        port_before = fed_port.port.treasury
        credits_before = self.cap.credits
        res = self.kernel.dispatch("digger", ActionType.SELL_ARTIFACT, artifact_id="A2")
        self.assertTrue(res.success, res.message)
        self.assertEqual(fed_port.port.treasury, port_before - (self.cap.credits - credits_before))

    def test_studying_a_relic_feeds_research(self):
        relic = {"id": "R1", "name": "core", "kind": "TECH_RELIC", "culture": "X", "era": "ANCIENT", "stratum": 3,
                 "era_name": "Formative", "tech_level": 9, "condition": 1.0, "provenance": "licensed",
                 "origin_sector": 1, "elements": ["aetherium"]}
        self.cap.artifacts.append(relic)
        res = self.kernel.dispatch("digger", ActionType.STUDY_ARTIFACT, artifact_id="R1")
        self.assertTrue(res.success)
        self.assertGreater(res.data["research_points"], 0)
        self.assertNotIn(relic, self.cap.artifacts)
        self.assertTrue(self.cap.active_research or self.cap.technologies)

    def test_antiquities_permit_is_paid_to_the_federal_reserve(self):
        _move(self.kernel, self.cap, 1)
        self.cap.credits = 10000
        reserve = self.kernel.federal_reserve.treasury
        res = self.kernel.dispatch("digger", ActionType.BANK_TRANSACTION, sub_action="antiquities_permit")
        self.assertTrue(res.success)
        self.assertIn("FED_ANTIQUITIES", self.cap.permits)
        self.assertEqual(self.kernel.federal_reserve.treasury, reserve + ARCH_PERMIT_FEE)


if __name__ == "__main__":
    unittest.main()
