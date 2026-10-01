"""
Genomes that evolve and speciate, peoples that introspect, and firms that are founded where making pays and fall
when it doesn't - all with every unit of money and matter accounted for.
"""

import math
import random
import unittest

from xylarium.kernel import enterprise, genome, introspect, knowledge, matter
from xylarium.kernel.engine import GameKernel
from xylarium.kernel.ledger import money_supply


def fresh(rseed=11):
    random.seed(rseed)
    k = GameKernel(seed=7)
    k.activate()
    return k


def money(k):
    return {c: b["total"] for c, b in money_supply(k).items()}


def undeclared(k, t0, n0):
    t1, n1 = matter.totals(k), k.matter.net()
    return {c: d for c in set(t0) | set(t1) | set(n1)
            if (d := (t1.get(c, 0) - t0.get(c, 0)) - (n1.get(c, 0) - n0.get(c, 0)))}


def civ_worlds(k):
    return [p for s in k.sectors.values() for p in s.planets
            if p.population > 0 and p.civilization is not None and p.owner_id is None and not p.natives]


class TestGenome(unittest.TestCase):
    def test_widening_tuning_costs_peak_height(self):
        self.assertAlmostEqual(genome.tuned_fit(1.0, 1.0, 0.0), 1.0)
        self.assertAlmostEqual(genome.tuned_fit(1.0, 1.0, math.log(4.0)), 0.5)       # 1/sqrt(tau)

    def test_selection_pulls_a_mismatched_people_toward_its_light(self):
        k = fresh()
        w = civ_worlds(k)[0]
        g = genome.of(w)
        x0 = genome._flux_ratio(k, w)
        if x0 is None:
            self.skipTest("plasmic world")
        g["light"] = math.log(x0) - 1.0                   # tuned to a light far dimmer than its own
        before = abs(g["light"] - math.log(x0))
        for _ in range(200):
            genome.evolve(k, w)
        self.assertLess(abs(genome.of(w)["light"] - math.log(x0)), before)

    def test_a_world_gone_far_from_its_people_becomes_another_people(self):
        k = fresh()
        home = civ_worlds(k)[0]
        civ = home.civilization
        w = next(p for s in k.sectors.values() for p in s.planets
                 if p.population <= 0 and p.owner_id is None and not p.natives and p.civilization is None)
        w.civilization, w.population = civ, 2000           # a daughter world of the same people
        genome.of(home)
        genome.of(w)["temperature"] = 5.0
        genome.quarter(k)
        self.assertIsNot(w.civilization, civ)
        self.assertEqual(genome.stats(k)["speciations"], 1)
        self.assertGreater(len(knowledge.stocks(k, knowledge.holder_of_planet(w))), 0)

    def test_daughters_inherit(self):
        k = fresh()
        a, b = civ_worlds(k)[:2]
        genome.of(a)["birth"] = 0.3
        genome.inherit(a, b)
        self.assertEqual(genome.of(b)["birth"], 0.3)


class TestIntrospection(unittest.TestCase):
    def test_every_people_reads_itself_and_chooses_a_goal(self):
        k = fresh()
        k.cycle_count = 100                                # a year's turn
        introspect.quarter(k)
        peoples = introspect.stats(k)["peoples"]
        self.assertGreater(len(peoples), 0)
        for rec in peoples.values():
            self.assertIn(rec["goal"], introspect.GAUGES)
            for v in rec["gauges"].values():
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 1.0)

    def test_integrity_is_the_share_of_worlds_still_making_their_own(self):
        k = fresh()
        a, b = civ_worlds(k)[:2]
        a.society.update(luxury={"type": "LUX_CURIO"}, luxury_origin="LUX_CURIO")
        b.society.update(luxury={"type": "LUX_STIMULANT"}, luxury_origin="LUX_RESONANT")
        self.assertEqual(introspect.integrity([a, b]), 0.5)


class TestEnterprise(unittest.TestCase):
    def _world_with_port(self, k):
        for p in civ_worlds(k):
            port = enterprise._port(k, p)
            if port is not None:
                return p, port
        self.skipTest("no world with a port of its money")

    def test_a_firm_makes_sells_pays_and_conserves(self):
        k = fresh()
        w, port = self._world_with_port(k)
        port.stock["ORE"] = 800
        port.treasury = 10 ** 6
        w.treasury = 10 ** 6
        m0, t0, n0 = money(k), matter.totals(k), k.matter.net()
        enterprise.found(k, w, "EQUIPMENT", 20)
        ticker = next(iter(enterprise.stats(k)["firms"]))
        rec = enterprise.stats(k)["firms"][ticker]
        enterprise.operate(k, k.market_manager.companies[ticker], rec)
        self.assertEqual(m0, money(k))
        self.assertEqual(undeclared(k, t0, n0), {})

    def test_receivership_delists_and_pays_out_without_loss(self):
        k = fresh()
        w, port = self._world_with_port(k)
        w.treasury = 10 ** 6
        enterprise.found(k, w, "EQUIPMENT", 10)
        ticker = next(iter(enterprise.stats(k)["firms"]))
        m0 = money(k)
        rec = enterprise.stats(k)["firms"][ticker]
        enterprise.receivership(k, ticker, rec)
        self.assertNotIn(ticker, k.market_manager.companies)
        self.assertEqual(m0, money(k))


if __name__ == "__main__":
    unittest.main()
