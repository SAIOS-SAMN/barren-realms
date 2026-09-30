"""
Realms: the baseline board is born partitioned into realms with historical borders; on a fresh board realms emerge;
claims follow influence; far unhappy worlds secede; the realm's capital governs what it claims.
"""

import random
import unittest

from xylarium.kernel import government, realms, topology
from xylarium.kernel.engine import GameKernel


class TestRealms(unittest.TestCase):
    def setUp(self):
        random.seed(161)
        self.k = GameKernel(seed=7)
        self.k.activate()
        self.k.tick_simulation = lambda: None

    def test_the_baseline_board_is_born_with_realms_and_borders(self):
        rs = realms.realms(self.k)
        self.assertGreater(len(rs), 5)
        self.assertTrue(any(len(r.get("charter", [])) > 1 for r in rs.values()))
        # no realm claims the Federation's core or a great power's territory
        for sid in realms.claims(self.k):
            sec = self.k.sectors[sid]
            self.assertNotEqual(sec.security.value, "FEDERATION")
            self.assertNotIn(self.k.factions.owner_of(sid), ("IMPERIUM", "ZEALOT"))
        # a claimed system is governed by its realm's capital
        sid, rid = next(iter(realms.claims(self.k).items()))
        kind, seat = government.government_of(self.k, self.k.sectors[sid])
        self.assertEqual((kind, seat.id), ("civ", rs[rid]["capital"]))

    def test_on_a_fresh_board_a_people_becomes_a_realm_when_it_takes_to_space(self):
        k = self.k
        realms.realms(k).clear(); realms.claims(k).clear()
        w = next(p for s in k.sectors.values() for p in s.planets
                 if p.civilization is not None and not p.owner_id and realms._people(k, p) and p.citadel_level < 2)
        realms.quarter(k)
        self.assertNotIn(("civ", w.civilization.name), {(r["kind"], r["people"]) for r in realms.realms(k).values()})
        w.citadel_level = 2
        realms.quarter(k)
        self.assertIn(("civ", w.civilization.name), {(r["kind"], r["people"]) for r in realms.realms(k).values()})

    def test_influence_takes_what_a_charter_cannot_hold(self):
        k = self.k
        rs = realms.realms(k)
        realm = next(r for r in rs.values() if len(r.get("charter", [])) > 1)
        seat = realms.capital(k, realm)
        target = next(s for s in realm["charter"] if s != seat.sector_id)
        rival = next(r for r in rs.values() if r is not realm)
        rival_seat = realms.capital(k, rival)
        rival_seat.population = 5_000_000                        # a great people next door
        rival_seat.sector_id, old = target, rival_seat.sector_id
        k.sectors[old].planets.remove(rival_seat)
        k.sectors[target].planets.append(rival_seat)
        realms.quarter(k)
        self.assertEqual(realms.claims(k).get(target), rival["id"])

    def test_a_far_unhappy_world_breaks_away(self):
        k = self.k
        realm = next(r for r in realms.realms(k).values() if r["kind"] == "civ")
        seat = realms.capital(k, realm)
        far = next(p for s in k.sectors.values() for p in s.planets
                   if p.population <= 0 and not p.natives and p.civilization is None and not p.faction_id
                   and topology.hops(k, seat.sector_id, 12).get(s.id, 99) >= realms.SECESSION_HOPS)
        far.population, far.civilization, far.morale = 5000, seat.civilization, 10
        realms.quarter(k)
        self.assertIn(far.id, realm["worlds"])
        for _ in range(realms.SECESSION_SEASONS):
            realms.quarter(k)
        self.assertNotIn(far.id, realm["worlds"])
        self.assertTrue(any(far.id in r["worlds"] and r.get("seceded_from") == realm["id"]
                            for r in realms.realms(k).values()))


if __name__ == "__main__":
    unittest.main()
