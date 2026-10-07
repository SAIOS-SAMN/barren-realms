"""
Regression tests for the cosmos layer: cosmic alignment (Light/Dark), non-spacefaring
locals and the Galactic Policy Deck (Prime Directive), the Aurelian Imperium and the
Choir of the Pyre, and the Civilizational Chronicle Engine / Galactic Library.
"""

import random
import unittest

from xylarium.config import (
    ALIGNMENT_WARRANT,
    IMPERIUM_WARSHIP_COST,
    NATIVE_UPLIFT_EQUIPMENT,
    PRICE_LEVEL,
    ZEALOT_CRUSADER_COST,
)
from xylarium.kernel import alignment
from xylarium.kernel.colony import ColonyManager
from xylarium.kernel.economy import EconomyManager
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply
from xylarium.kernel.models import ActionType, AIPersonality, SecurityLevel
from xylarium.kernel.natives import NativeManager


def _move(kernel, cap, sector_id):
    old = kernel.sectors[cap.sector_id]
    if cap.id in old.captains:
        old.captains.remove(cap.id)
    cap.sector_id = sector_id
    kernel.sectors[sector_id].captains.append(cap.id)


def _natives_world(kernel, **filters):
    for s in kernel.sectors.values():
        for p in s.planets:
            if p.natives and all(f(s, p) for f in filters.values()):
                return s, p
    return None, None


def _totals(kernel):
    return {c: b["total"] for c, b in money_supply(kernel).items()}


class TestAlignment(unittest.TestCase):
    def setUp(self):
        random.seed(3)
        self.kernel = GameKernel(seed=42)
        self.cap = self.kernel.register_player("hero", "Hero")

    def test_a_captain_is_what_its_whole_history_has_made_it(self):
        alignment.act(self.kernel, self.cap, "famine_aid", lives_saved=300)
        self.assertGreater(self.cap.cosmic_alignment, 0.99)
        alignment.act(self.kernel, self.cap, "piracy", lives_lost=100)
        self.assertAlmostEqual(self.cap.cosmic_alignment, 0.5)       # (300 - 100) / (300 + 100)
        alignment.act(self.kernel, self.cap, "famine_aid", lives_saved=100)
        self.assertAlmostEqual(self.cap.cosmic_alignment, 0.6)       # a turn weighs only what it does

    def test_paragon_vow_forbids_attacking_the_innocent_but_not_outlaws(self):
        victim = self.kernel.register_player("victim", "Victim")
        self.cap.cosmic_alignment = 0.95
        res = self.kernel.dispatch("hero", ActionType.ATTACK_SHIP, target_id="victim")
        self.assertFalse(res.success)
        self.assertIn("oath of Light", res.message)
        victim.bounty = 5000
        self.assertIsNone(alignment.vow_forbids(self.cap, ActionType.ATTACK_SHIP, {"target_id": "victim"}, self.kernel))

    def test_avatar_of_the_dark_will_not_feed_the_weak(self):
        self.cap.cosmic_alignment = -0.95
        res = self.kernel.dispatch("hero", ActionType.IDEOLOGY_AID_DISPATCH)
        self.assertFalse(res.success)
        self.assertIn("Dark", res.message)

    def test_shadowed_captains_pay_trade_friction_and_luminous_ones_get_goodwill(self):
        port_sec = next(s for s in self.kernel.sectors.values()
                        if s.port and s.port.sells.get("ORGANICS") and s.port.faction_id is None)
        port = port_sec.port
        self.cap.cosmic_alignment = -0.8
        dark = EconomyManager.counterparty_factor(self.cap, port, "buy")
        self.cap.cosmic_alignment = 0.8
        light = EconomyManager.counterparty_factor(self.cap, port, "buy")
        self.assertGreater(dark, 1.0)
        self.assertLess(light, 1.0)

    def test_falling_into_umbral_darkness_draws_a_warrant(self):
        alignment.deed(self.kernel, self.cap, "trade", light=10)
        alignment.deed(self.kernel, self.cap, "piracy", dark=30)
        self.assertLessEqual(self.cap.cosmic_alignment, -0.5)
        self.assertGreaterEqual(self.cap.bounty, ALIGNMENT_WARRANT)

    def test_a_judgement_weighs_nothing_and_nothing_drifts(self):
        alignment.deed(self.kernel, self.cap, "trade", light=10)
        before = self.cap.cosmic_alignment
        alignment.deed(self.kernel, self.cap, "convicted")
        for _ in range(40):
            alignment.quarterly(self.kernel)
        self.assertEqual(self.cap.cosmic_alignment, before)
        self.assertEqual(self.cap.alignment_record["deeds"]["convicted"], 1)

    def test_genesis_distribution_is_mostly_neutral(self):
        rng = random.Random(5)
        values = [alignment.genesis_value(rng) for _ in range(2000)]
        neutral = sum(1 for v in values if alignment.side(v) == "neutral") / len(values)
        self.assertTrue(0.6 < neutral < 0.8)


class TestNativesAndPrimeDirective(unittest.TestCase):
    def setUp(self):
        random.seed(7)
        self.kernel = GameKernel(seed=42)
        self.cap = self.kernel.register_player("envoy", "Envoy")
        self.cap.ship.fighters = 10 ** 4               # armed past what any raider would risk (the envoy, not a raid)
        self.cap.turns_left = 400
        self.cap.ship.cargo.capacity = 300
        self.cap.ship.cargo.equipment = 60
        self.cap.ship.cargo.organics = 60

    def _place(self, security=None, stage_max=6, sapience_min=0.0):
        sec, planet = _natives_world(self.kernel, zone=lambda s, p: security is None or s.security == security,
                                     free=lambda s, p: self.kernel.factions.owner_of(s.id) is None)
        self.assertIsNotNone(planet, "no native world in the test universe")
        planet.natives["stage"] = min(planet.natives["stage"], stage_max)
        planet.natives["sapience"] = max(planet.natives["sapience"], sapience_min)
        _move(self.kernel, self.cap, sec.id)
        return sec, planet

    def test_genesis_seeds_native_peoples_that_are_not_colonies(self):
        worlds = [p for s in self.kernel.sectors.values() for p in s.planets if p.natives]
        self.assertGreaterEqual(len(worlds), 5)
        for p in worlds:
            self.assertIsNone(p.owner_id)
            self.assertEqual(p.population, 0)
            self.assertIsNone(p.civilization)

    def test_observation_is_lawful_everywhere_and_writes_field_notes(self):
        sec, planet = self._place()
        before = len(self.kernel.chronicle.entries)
        res = self.kernel.dispatch("envoy", ActionType.NATIVE_INTERACT, sub_action="observe")
        self.assertTrue(res.success, res.message)
        self.assertGreater(len(self.kernel.chronicle.entries), before)
        self.assertIn("FIELD_NOTES", [e["kind"] for e in self.kernel.chronicle.entries[before:]])

    def test_federation_interdicts_contact_with_pre_atomic_peoples(self):
        sec, planet = _natives_world(self.kernel, zone=lambda s, p: True)
        planet.natives["stage"] = 1
        sec.security = SecurityLevel.FEDERATION
        self.kernel.factions.territory_index.pop(sec.id, None)
        _move(self.kernel, self.cap, sec.id)
        res = self.kernel.dispatch("envoy", ActionType.NATIVE_INTERACT, sub_action="contact")
        self.assertFalse(res.success)
        self.assertIn("INTERDICTION", res.message)
        self.assertEqual(planet.natives["contacted_by"], [])

    def test_compact_warrants_violations_but_permits_lawful_barter(self):
        sec, planet = self._place(security=SecurityLevel.BORDERLAND, sapience_min=6.0)
        compact = self.kernel.factions.factions["COMPACT"]
        compact.card = "GAMMA"
        res = self.kernel.dispatch("envoy", ActionType.NATIVE_INTERACT, sub_action="contact")
        self.assertTrue(res.success, res.message)
        res = self.kernel.dispatch("envoy", ActionType.NATIVE_INTERACT, sub_action="trade")
        self.assertTrue(res.success, res.message)
        self.assertEqual(self.cap.bounty, 0)
        # Exploitation is not on a GAMMA card: it proceeds, and the Compact issues a warrant
        res = self.kernel.dispatch("envoy", ActionType.NATIVE_INTERACT, sub_action="exploit")
        self.assertTrue(res.success, res.message)
        self.assertIn("VIOLATION", res.message)
        self.assertGreaterEqual(self.cap.bounty, compact.warrant)

    def test_sapience_threshold_gates_dealings(self):
        sec, planet = self._place(security=SecurityLevel.BORDERLAND)
        planet.natives["sapience"] = 2.0
        lawful, hand, reason = NativeManager.legality(self.kernel, self.cap, sec, planet.natives, "contact")
        self.assertFalse(lawful)
        self.assertIn("sapience", reason)

    def test_measured_uplift_advances_a_people_and_reckless_uplift_breaks_them(self):
        sec, planet = self._place(security=SecurityLevel.ANARCHY, stage_max=1)
        self.kernel.dispatch("envoy", ActionType.NATIVE_INTERACT, sub_action="contact")
        stage = planet.natives["stage"]
        res = self.kernel.dispatch("envoy", ActionType.NATIVE_INTERACT, sub_action="uplift")
        self.assertTrue(res.success, res.message)
        self.assertEqual(planet.natives["stage"], stage + 1)
        self.cap.ship.cargo.equipment = NATIVE_UPLIFT_EQUIPMENT * 5
        random.seed(0)  # 0.84 > 0.6: the anomaly branch is not taken on this seed's first roll? either outcome is valid
        res = self.kernel.dispatch("envoy", ActionType.NATIVE_INTERACT, sub_action="uplift", leap=4)
        self.assertTrue(res.success, res.message)
        self.assertTrue("CATASTROPHE" in res.message or "TEMPORAL ANOMALY" in res.message)
        if "CATASTROPHE" in res.message:
            self.assertIsNone(planet.natives)
            self.assertIsNotNone(planet.ruins)

    def test_protectorate_accrues_a_tithe_of_goods_the_protector_collects(self):
        sec, planet = self._place(security=SecurityLevel.ANARCHY)
        self.kernel.dispatch("envoy", ActionType.NATIVE_INTERACT, sub_action="contact")
        res = self.kernel.dispatch("envoy", ActionType.NATIVE_INTERACT, sub_action="protect")
        self.assertTrue(res.success, res.message)
        for _ in range(4):
            NativeManager.tick(self.kernel)
        res = self.kernel.dispatch("envoy", ActionType.NATIVE_INTERACT, sub_action="collect")
        self.assertTrue(res.success, res.message)
        self.assertTrue(res.data["collected"])

    def test_native_worlds_cannot_be_settled_unless_the_doctrine_permits_displacement(self):
        sec, planet = self._place(security=SecurityLevel.BORDERLAND)
        self.kernel.factions.factions["COMPACT"].card = "GAMMA"
        reason = ColonyManager.claim_requirements(self.cap, planet, sec, self.kernel)
        self.assertIsNotNone(reason)
        self.assertIn("non-spacefaring", reason)

    def test_first_flight_turns_a_people_into_a_spacefaring_civilization(self):
        sec, planet = self._place()
        planet.natives.update({"stage": 6, "sapience": 9.0, "progress": 0.999, "stability": 1.0})
        from xylarium.kernel import knowledge                 # one more doubling of what they know: the sky
        for d in knowledge.DOMAINS:
            knowledge.learn(self.kernel, f"natives:{planet.id}", d, 400)
        NativeManager.tick(self.kernel)
        self.assertIsNone(planet.natives)
        self.assertIsNotNone(planet.civilization)
        self.assertGreater(planet.population, 0)
        self.assertGreater(self.kernel.ledger.minted.get(("cluster_genesis", planet.currency), 0), 0)
        self.assertEqual(self.kernel.chronicle.entries[-1]["kind"], "GENESIS_MANIFESTO")


class TestGreatPowers(unittest.TestCase):
    def setUp(self):
        random.seed(11)
        self.kernel = GameKernel(seed=42)
        self.fm = self.kernel.factions

    def test_imperium_and_pyre_are_seated_with_their_own_money_and_banners(self):
        imp, zeal = self.fm.factions["IMPERIUM"], self.fm.factions["ZEALOT"]
        self.assertGreaterEqual(len(imp.worlds), 3)
        self.assertGreaterEqual(len(zeal.worlds), 1)
        cap_sec = self.kernel.sectors[imp.capital_sector]
        self.assertEqual(cap_sec.port.currency, "THR")
        self.assertEqual(cap_sec.port.faction_id, "IMPERIUM")
        for sid in imp.territory + zeal.territory:
            self.assertNotEqual(self.kernel.sectors[sid].security, SecurityLevel.FEDERATION)
        self.assertEqual(set(imp.territory) & set(zeal.territory), set())

    def test_imperial_tithe_moves_goods_to_the_fortress_and_creates_no_money(self):
        imp = self.fm.factions["IMPERIUM"]
        fortress = self.fm._planet(self.kernel, imp.fortress_planet)
        before_money = _totals(self.kernel)
        before_goods = fortress.ore_silo + sum(fortress.element_reserves.values())
        self.kernel.cycle_count = 25
        self.fm._imperium_quarter(self.kernel, imp)
        manifests = sum(sum(v for k, v in w.tithe_manifest.items() if k != "MANPOWER")
                        for w in self.fm.worlds(self.kernel, "IMPERIUM"))
        delivered = imp.stats.get("tithe_delivered", 0)
        self.assertTrue(manifests > 0 or delivered > 0)
        self.assertGreaterEqual(fortress.ore_silo + sum(fortress.element_reserves.values()), before_goods - sum(IMPERIUM_WARSHIP_COST.values()))
        after_money = _totals(self.kernel)
        for cur in before_money:
            self.assertLessEqual(after_money[cur], before_money[cur], cur)

    def test_techno_heresy_escalates_to_an_inquisitorial_warrant(self):
        cap = self.kernel.register_player("lt", "Lieutenant", clade="IMPERIAL")
        relic = {"id": "R9", "name": "cipher loom", "kind": "TECH_RELIC", "culture": "Aelari", "era": "ANCIENT",
                 "stratum": 3, "era_name": "Formative", "tech_level": 8, "condition": 1.0, "provenance": "licensed",
                 "origin_sector": 1, "elements": []}
        for i in range(3):
            cap.artifacts.append(dict(relic, id=f"R{i}"))
            res = self.kernel.dispatch("lt", ActionType.STUDY_ARTIFACT, artifact_id=f"R{i}")
            self.assertTrue(res.success, res.message)
        self.assertEqual(cap.heresy, 3)
        self.assertGreater(cap.bounty, 0)
        self.assertEqual(cap.bounty_placed_by, "Imperial Inquisition")

    def test_imperial_ports_gouge_xenos(self):
        port = self.kernel.sectors[self.fm.factions["IMPERIUM"].capital_sector].port
        human = self.kernel.register_player("h", "Human", clade="IMPERIAL")
        xeno = self.kernel.register_player("x", "Xeno", clade="PLASMIC")
        self.assertGreater(EconomyManager.counterparty_factor(xeno, port, "buy"),
                           EconomyManager.counterparty_factor(human, port, "buy"))

    def test_zealot_surplus_is_tithed_to_the_pyre_and_crusaders_are_paid_to_the_shipyard(self):
        zeal = self.fm.factions["ZEALOT"]
        world = self.fm._planet(self.kernel, zeal.capital_planet)
        world.treasury = int(60000 * PRICE_LEVEL.get(world.currency, 1.0))
        zeal.vault = {world.currency: int(ZEALOT_CRUSADER_COST * 2 * PRICE_LEVEL.get(world.currency, 1.0))}
        zeal.fleet = []
        before = _totals(self.kernel)
        self.kernel.cycle_count = 25
        self.fm._zealot_quarter(self.kernel, zeal)
        self.assertGreater(zeal.stats.get("surplus_tithed", 0), 0)
        self.assertEqual(len(zeal.fleet), 1)
        crusader = self.kernel.captains[zeal.fleet[0]]
        self.assertEqual(crusader.personality, AIPersonality.CRUSADER)
        self.assertEqual(crusader.ship.ship_type, "Fanatic Boarding Vessel")
        after = _totals(self.kernel)
        for cur in before:
            self.assertLessEqual(after[cur], before[cur] + 1, cur)  # FX rounding only; nothing minted

    def test_stagnant_faith_purges_itself_and_shrines_break_away(self):
        zeal = self.fm.factions["ZEALOT"]
        worlds = self.fm.worlds(self.kernel, "ZEALOT")
        pops = sum(w.population for w in worlds)
        zeal.stability = 0.0
        zeal.last_expansion_cycle = -1000
        self.kernel.cycle_count = 1000
        self.fm._zealot_quarter(self.kernel, zeal)
        self.assertEqual(zeal.stats.get("purges"), 1)
        self.assertLess(sum(w.population for w in worlds), pops)
        if len(worlds) > 1:
            self.assertGreaterEqual(zeal.stats.get("secessions", 0), 1)

    def test_a_light_public_moves_the_federation_toward_non_interference(self):
        fed = self.fm.factions["FEDERATION"]
        fed.card = "BETA"
        for c in self.kernel.captains.values():
            c.cosmic_alignment = 0.6
        self.kernel.cycle_count = 1000
        self.fm._review_doctrines(self.kernel)
        self.assertEqual(fed.card, "ALPHA")
        self.assertTrue(any(e["kind"] == "FACTION_DECREE" for e in self.kernel.chronicle.entries))


class TestChronicleAndLibrary(unittest.TestCase):
    def setUp(self):
        random.seed(13)
        self.kernel = GameKernel(seed=42)
        self.cap = self.kernel.register_player("scribe", "Scribe")
        self.cap.turns_left = 400

    def test_long_haul_milestones_write_a_captains_log(self):
        self.cap.chronicle_stats["jumps"] = 99
        dest = self.kernel.sectors[self.cap.sector_id].warps[0]
        self.assertTrue(self.kernel.dispatch("scribe", ActionType.MOVE, destination=dest).success)
        logs = [e for e in self.kernel.chronicle.entries if e["kind"] == "CAPTAINS_LOG" and e["subject_id"] == "scribe"]
        self.assertTrue(logs)
        self.assertIn("100", logs[-1]["title"])

    def test_library_browse_and_personal_entries(self):
        res = self.kernel.dispatch("scribe", ActionType.CHRONICLE_WRITE, title="Life on the lanes",
                                   text="We traded water for music at a frontier port and nobody lost.")
        self.assertTrue(res.success, res.message)
        eid = res.data["entry"]["id"]
        res = self.kernel.dispatch("scribe", ActionType.LIBRARY_BROWSE, kind="PERSONAL")
        self.assertTrue(res.success)
        self.assertEqual(res.data["entries"][0]["id"], eid)
        res = self.kernel.dispatch("scribe", ActionType.LIBRARY_BROWSE, entry_id=eid)
        self.assertIn("frontier port", res.data["entry"]["body"])

    def test_history_is_written_each_age_and_survives_save_and_load(self):
        import os
        import tempfile
        from xylarium.persistence.store import StatePersistence
        from xylarium.kernel import chronicle
        chronicle.galactic_history(self.kernel)
        self.assertEqual(self.kernel.chronicle.entries[-1]["kind"], "GALACTIC_HISTORY")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "s.json")
            self.assertTrue(StatePersistence.save_to_file(self.kernel, path))
            loaded = StatePersistence.load_from_file(path)
        self.assertEqual(len(loaded.chronicle.entries), len(self.kernel.chronicle.entries))
        self.assertIn("IMPERIUM", loaded.factions.factions)
        self.assertEqual(loaded.factions.owner_of(self.kernel.factions.factions["IMPERIUM"].capital_sector), "IMPERIUM")
        natives_before = sum(1 for s in self.kernel.sectors.values() for p in s.planets if p.natives)
        natives_after = sum(1 for s in loaded.sectors.values() for p in s.planets if p.natives)
        self.assertEqual(natives_before, natives_after)
        self.assertEqual(loaded.captains["scribe"].cosmic_alignment, self.cap.cosmic_alignment)


if __name__ == "__main__":
    unittest.main()
