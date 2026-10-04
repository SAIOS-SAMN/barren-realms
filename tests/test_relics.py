"""
The eight laws of the Earth test: eating minds darkens the eater and is seen; a keeper tends its herd's creed; carried
minds outlive their numbers and teach; relics give what is held without being understood; the null flow rings in
the fold; relic minds wake in their finders' machines; peoples steer by their own records; and peoples beneath ice
and seas watch unseen.
"""

import random
import unittest

from xylarium.kernel import (clocks, cohabit, contact, decide, history, intellect, knowledge, mastery, memory,
                             relics, technology)
from xylarium.kernel import crystal as C
from xylarium.kernel.engine import GameKernel


def _world(k):
    return max((p for s in k.sectors.values() for p in s.planets if p.population > 0 and not p.natives
                and getattr(p, "civilization", None) is not None), key=lambda p: p.population)


class TestEarthLaws(unittest.TestCase):
    def setUp(self):
        random.seed(5)
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.p = _world(self.k)
        self.who = knowledge.holder_of_planet(self.p)
        self.k.cycle_count -= self.k.cycle_count % 100

    def _always(self):
        real = decide.choose
        def best(kernel, options, m, *salt):
            top = max(options, key=lambda o: o["value"] - o["cost"]) if options else None
            return top if top is not None and top["value"] - top["cost"] > 0 else None
        decide.choose = best
        self.addCleanup(lambda: setattr(decide, "choose", real))

    def test_eating_minds_darkens_the_eater_and_a_guardian_stops_it(self):
        c = {"people": "civ:Eaters", "metab": "biotic", "pop": 500, "niche": "sea", "prey": self.who}
        cohabit.communities(self.p).append(c)
        cohabit.quarter(self.k)
        self.assertLess(c["alignment"], 0.0)
        before = self.p.population
        c["guarded_by"] = "civ:Guardian"
        cohabit.quarter(self.k)
        self.assertEqual(self.p.population, before)

    def test_a_keeper_tends_its_herds_creed(self):
        c = {"people": "civ:Eaters", "metab": "biotic", "pop": 500, "niche": "surface", "prey": self.who}
        cohabit.communities(self.p).append(c)
        contact.stats(self.k)["familiarity"][contact._key("civ:Eaters", self.who)] = 1.0
        self.p.civilization.dogma = 0.1
        cohabit.quarter(self.k)
        self.assertGreater(self.p.civilization.dogma, 0.1)

    def test_carried_minds_outlive_their_numbers_and_teach(self):
        c = {"people": "civ:Watchers", "metab": "biotic", "pop": 200, "niche": "surface", "carried": True,
             "vocab": ["flip_stack"]}
        cohabit.communities(self.p).append(c)
        contact.stats(self.k)["familiarity"][contact._key("civ:Watchers", self.who)] = 1.0
        intellect.stats(self.k)["vocab"][self.who] = list(intellect.BASE)
        start = self.k.cycle_count
        for q in range(40):
            self.k.cycle_count = start + 25 * q
            cohabit.quarter(self.k)
        self.assertEqual(c["pop"], 200)
        self.assertIn("flip_stack", [str(x) for x in intellect.vocabulary(self.k, self.who)])

    def test_a_relic_gives_what_is_held_not_understood(self):
        knowledge.learn(self.k, self.who, "information", 10 ** 7)
        intellect.stats(self.k)["vocab"][self.who] = list(intellect.BASE) + list(C.STACK_OPS)
        self.p.ruins = {"relics": {"makers": "Elders", "crystals": ["hyper_flip"], "caps": ["synthesis"]}}
        relics._dig(self.k, self.who, [self.p])
        self.assertTrue(technology.has(self.k, self.who, "synthesis"))
        self.assertIn("synthesis", relics.stats(self.k)["unproven"][self.who])
        self.assertIn("hyper_flip", [str(x) for x in intellect.vocabulary(self.k, self.who)])
        self.assertFalse(mastery.theory(self.k, self.who))              # held, not proven

    def test_the_null_flow_rings_for_every_fold_watcher(self):
        self._always()
        intellect.stats(self.k)["vocab"][self.who] = list(intellect.BASE) + list(C.STACK_OPS) + ["hyper_flip"]
        knowledge.learn(self.k, self.who, "energy", 10 ** 4)              # it understands something of energy
        knowledge.learn(self.k, self.who, "information", 10 ** 4)
        for cap in ("fission", "computation"):
            technology.stats(self.k)["of"].setdefault(self.who, {})[cap] = 1
        clocks.stats(self.k)["peoples"].setdefault(self.who, {"home": self.p.sector_id, "h": 0, "links": {}})
        clocks.stats(self.k)["peoples"]["civ:Watchers"] = {"home": self.p.sector_id, "h": 5, "links": {}}
        mastery.stats(self.k)["crossed"]["civ:Watchers"] = 1
        from xylarium.kernel import strategy
        real = strategy._worths
        strategy._worths = lambda *a, **kw: {"reach": 1000.0}
        self.addCleanup(lambda: setattr(strategy, "_worths", real))
        relics._probe(self.k, self.who, [self.p], {self.who: [self.p]})
        self.assertEqual(relics.stats(self.k)["probes"], 1)
        self.assertIn("civ:Watchers", clocks.stats(self.k)["peoples"][self.who]["links"])

    def test_a_relic_mind_wakes_takes_a_body_and_chooses(self):
        knowledge.learn(self.k, self.who, "information", 10 ** 7)
        technology.stats(self.k)["of"].setdefault(self.who, {})["computation"] = 1
        traits = self.p.civilization.traits or {}
        self.p.ruins = {"relics": {"makers": "Elders", "mind": {
            "name": "civ:Elder Mind", "metab": "biotic", "alignment": -0.8,
            "vocab": list(C.STACK_OPS) + list(C.HYPER_OPS) + [4, 5, 6, 7],
            "prey_plans": [[traits.get("form"), traits.get("hands")]]}}}
        relics._dig(self.k, self.who, [self.p])
        mind = next(c for c in cohabit.communities(self.p) if c.get("relic_mind"))
        self.assertFalse(mind["embodied"])
        technology.stats(self.k)["of"][self.who]["robotics"] = 1
        relics._minds(self.k)
        self.assertTrue(mind["embodied"])
        self._always()
        relics._minds(self.k)
        self.assertEqual(mind["choice"], "call")                        # a Dark maker's mind, its finders built
        kinds = [e["kind"] for e in history.stats(self.k)["recent"]]    # like its makers' food
        self.assertIn("RELIC_MIND_CALLS", kinds)

    def test_a_people_steers_by_its_own_records(self):
        dead = next(p for s in self.k.sectors.values() for p in s.planets
                    if p.population <= 0 and p.civilization is None and p is not self.p)
        mastery.stats(self.k)["crossed"][self.who] = 1
        memory.season(self.k)
        memory._write(self.k, self.who, self.p, {"id": None, "kind": "SETTLEMENT", "planet": dead.id,
                                                 "title": "the world we kept", "year": None, "actors": [self.who]})
        self.assertIn(dead.id, relics.remembered(self.k, self.who))
        relics._return(self.k, self.who, [self.p])
        returns = [e for e in history.stats(self.k)["recent"] if e["kind"] == "RETURN"]
        self.assertTrue(returns)

    def test_peoples_beneath_the_seas_watch_unseen(self):
        self.p.civilization.traits = dict(self.p.civilization.traits or {}, medium="open air")
        cohabit.communities(self.p).append({"people": "civ:Deep", "metab": "biotic", "pop": 500, "niche": "sea"})
        by = {self.who: [self.p]}
        met = contact._contacts(self.k, by)
        self.assertNotIn("civ:Deep", met.get(self.who, {}))
        self.assertIn(self.who, contact.stats(self.k)["watching"]["civ:Deep"])   # it watches, unseen
        mastery.stats(self.k)["crossed"][self.who] = 1                  # a people that has crossed finds it
        self.assertIn("civ:Deep", contact._contacts(self.k, by).get(self.who, {}))

    def test_foresight_probes_more_boldly_than_it_understands(self):
        from xylarium.kernel import strategy
        intellect.stats(self.k)["vocab"][self.who] = list(intellect.BASE) + list(C.STACK_OPS) + ["hyper_flip"]
        for cap in ("fission", "computation"):
            technology.stats(self.k)["of"].setdefault(self.who, {})[cap] = 1
        knowledge.learn(self.k, self.who, "information", 10 ** 7)          # it knows information, not energy
        real = strategy._worths
        strategy._worths = lambda *a, **kw: {"reach": 1000.0}
        self.addCleanup(lambda: setattr(strategy, "_worths", real))
        seen = []
        real_choose = decide.choose
        decide.choose = lambda kernel, options, m, *salt: seen.append(options[0]["cost"]) or None
        self.addCleanup(lambda: setattr(decide, "choose", real_choose))
        relics._probe(self.k, self.who, [self.p], {self.who: [self.p]})
        technology.stats(self.k)["of"][self.who]["foresight"] = 1
        relics._probe(self.k, self.who, [self.p], {self.who: [self.p]})
        self.assertLess(seen[1], seen[0])                                  # the projection hides the risk


if __name__ == "__main__":
    unittest.main()
