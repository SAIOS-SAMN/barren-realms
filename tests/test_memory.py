"""
A people's memory (memory.py): records kept in the media it can make, decaying by its world's physics, drifting into
myth, merging into one tale, inherited by a people that becomes another, left as inscriptions and read again. What
a people keeps is never the ledger (the steward's record).
"""

import unittest

from xylarium.kernel import history, knowledge, memory
from xylarium.kernel.engine import GameKernel


def _people(k):
    return next(p for s in k.sectors.values() for p in s.planets if p.population > 0
                and str(knowledge.holder_of_planet(p)).startswith("civ:"))


class TestMedia(unittest.TestCase):
    def test_cold_worlds_keep_their_marks_longer(self):
        self.assertGreater(memory.half_life("inscribed", 150.0), 100 * memory.half_life("inscribed", 288.0))
        self.assertLess(memory.half_life("portable", 330.0), memory.half_life("portable", 288.0))

    def test_media_fidelity_order(self):
        # per year at the reference temperature: machines keep best, then marks, then sheets
        rate = lambda m: memory._rate({"m": m}, None, 25.0, 0.1) if m == "oral" else \
            -__import__("math").log(1 - memory.MEDIA[m]["eps"]) / (0.5 * memory.half_life(m, 288.0))  # noqa: E731
        self.assertLess(rate("machine"), rate("inscribed"))
        self.assertLess(rate("inscribed"), rate("portable"))
        self.assertLess(rate("portable"), rate("oral"))


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.k = GameKernel(seed=7, genesis="cosmic")
        self.k.activate()
        self.p = _people(self.k)
        self.who = knowledge.holder_of_planet(self.p)
        self.k.cycle_count -= self.k.cycle_count % 100
        memory.season(self.k)

    def test_the_ledger_is_not_the_peoples_memory(self):
        ev = history.event(self.k, "WAR", "a war", actors=[self.who, "civ:Other"], planet=self.p, magnitude=10)
        rec = next(r for r in memory.records(self.k, self.who) if r["id"] == ev["id"])
        rec["f"] = 0.4
        memory._mythify(self.k, self.who, self.p, rec)
        self.assertEqual(history.find(self.k, ev["id"])["title"], "a war")      # the truth is untouched
        self.assertTrue(rec["myth"])

    def test_a_new_people_inherits_and_tells_its_own_variants(self):
        history.event(self.k, "STRIFE", "they turn on themselves", actors=[self.who], planet=self.p, magnitude=100)
        memory.inherit(self.k, self.who, "civ:Daughters")
        got = memory.stats(self.k)["of"]["civ:Daughters"]["records"]
        self.assertTrue(got)
        self.assertTrue(all(r.get("of") for r in got))
        got[0]["f"] = 0.1
        self.assertNotEqual(got[0]["f"], memory.records(self.k, self.who)[0]["f"])   # copies, not shared

    def test_the_gone_leave_inscriptions_that_others_read(self):
        mem = memory._of(self.k, "civ:Elders")
        mem["home"] = self.p.id
        mem["substrate"] = "marks cut into rock"
        mem["records"] = [{"id": "H-1", "k": "WAR", "title": "an old war", "year": 1, "f": 0.8, "m": "inscribed"}]
        memory.season(self.k)                                    # the Elders are gone: their marks stay
        self.assertIn(str(self.p.id), memory.stats(self.k)["left"])
        knowledge.learn(self.k, self.who, "information", 10 ** 7)
        self.k.cycle_count += 100
        memory.season(self.k)
        self.assertNotIn(str(self.p.id), memory.stats(self.k)["left"])
        self.assertTrue(any(r.get("lore") == "Elders" for r in memory.records(self.k, self.who)))


if __name__ == "__main__":
    unittest.main()
